#!/usr/bin/env python3
"""Site watchdog: probes the site over BOTH schemes and names which of two ills it is.

WHY TWO SCHEMES AND NOT ONE. Until 2026-09-07 this watchdog checked a single address and
could say only "жив" / "мёртв" / "не смог проверить". That is one word too few, because
the site has failed in two ways that look identical to a one-address watchdog and call for
OPPOSITE actions:

  * the server is down          -> go and lift the server;
  * port 443 is filtered ON THE PATH between the owner and the machine -> the server is
    fine, touching it makes things worse, and the action is to go to the provider.

The second failure is not hypothetical here.  Measurement of 2026-09-06: probe 1 gave 30
successes out of 30, probe 2 an hour later gave 3 timeouts out of 3; port 8443 carrying the
same certificate answered in 0.10 s while 443 timed out; TCP connected; from inside the
data centre 443 worked the whole time.  The filtering comes and goes, and it lives outside
the server -- so a watchdog that only knows "the site does not answer" sends whoever reads
it to fix the one thing that is not broken.

THE SIGNATURE THAT SEPARATES THEM is exactly what this module now measures: with 443
filtered, HTTP still serves OUR content while HTTPS does not answer at the network level at
all.  With the server down, neither answers.  That is why HTTP is kept alive and unredirected
on this site (owner's decision of 2026-09-07, `sites-enabled/spetsmat`): it is the control
sample.  Without it, "HTTPS is silent" has no interpretation.

A NETWORK-LEVEL silence is required for the filtering verdict, not merely a bad status.
An HTTPS reply of 502 means the server is answering and something behind it broke -- that is
"мёртв", not filtering.  Filtering shows up as a timeout or a refused connection or a TLS
handshake that never completes, i.e. as an exception rather than a response.

State is kept in /tmp/spetsmat-storozh-sajta.state.json.  Alarm only on change.
"""

from __future__ import annotations

import argparse
import json
import socket
import ssl
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# The domain the site is published under.  ADRES.txt beside it is the ROUTE FROM BEFORE the
# server -- a laptop holding an lhr.life tunnel open -- and the URL committed in it is a dead
# tunnel (deploy/README.md says so).  It is read only as a fallback, so that the tunnel-era
# route keeps working for whoever still uses it; it is not where the site lives now.
HOST_FILE = ROOT / "deploy" / "ADRES-SAJTA.txt"
ADRES_FILE = ROOT / "deploy" / "ADRES.txt"
STATE_FILE = Path("/tmp/spetsmat-storozh-sajta.state.json")

# Content marker that must appear on OUR site and cannot appear on provider banners.
# Per correction 1 (2026-09-04 17:41): S1 moves distribution to /raspredelenie.
# We check that path specifically to avoid false-red after S1 merge.
#
# 🔴 MATCHED CASE-INSENSITIVELY, AND OVER MORE THAN THE FIRST 512 BYTES, BECAUSE BOTH
# NARROWINGS HAD ALREADY FIRED FALSELY.  Measured 2026-09-07: the page renders the word in
# its title as "… — распределение", lower-case, and the previous exact-case comparison over
# body[:512] therefore returned "мёртв: content_marker_MISSING" against a site that was
# serving 200 and perfectly alive.  A watchdog whose false alarm looks exactly like its true
# alarm is worse than no watchdog: the reader learns to disbelieve it.
OUR_CONTENT_MARKER = "распределение"
RASPREDELENIE_PATH = "/raspredelenie"

# Enough of the body to contain the marker wherever the page puts it, and far too little to
# matter if the address turns out to serve something enormous.
BODY_BYTES = 65536

TIMEOUT_SECONDS = 15

# The five verdicts.  Kept as module constants because the alarm compares them as strings and
# a typo in a literal would silently mean "state changed" on every single run.
ZHIV = "жив"
MERTV = "мёртв"
OTFILTROVAN = "443 отфильтрован"
SERTIFIKAT = "сертификат не проходит проверку"
HTTP_LEG = "http лёг"
NE_SMOG = "не смог проверить"

# What to do about each -- printed with the verdict, because a watchdog that names a failure
# without naming the action makes the reader guess at 2 a.m.
DEJSTVIE = {
    ZHIV: "ничего не делать",
    MERTV: "поднимать сайт: deploy/podnyat_sajt.sh, затем systemctl status spetsmat-veb",
    OTFILTROVAN: "СЕРВЕР НЕ ТРОГАТЬ — он отвечает по http. Фильтрация на пути: вопрос к провайдеру",
    SERTIFIKAT: "чинить СЕРВЕР: certbot renew, затем systemctl reload nginx. 443 доходит — это не фильтрация",
    HTTP_LEG: "https жив, http молчит — смотреть блок listen 80 в nginx, сайт у владельца работает",
    NE_SMOG: "проверить нечем — смотреть адрес и сеть самой машины-сторожа",
}


@dataclass(frozen=True)
class OneCheck:
    """One probe of one scheme.

    ``otvetil_seteviy`` is the field the whole diagnosis turns on: it says whether anything
    came back over the wire at all, regardless of what status it carried.  ``passed`` (our
    content, 2xx) is a stricter thing and cannot stand in for it.
    """

    name: str
    passed: bool
    otvetil_seteviy: bool
    detail: str
    # TLS дошёл до сервера, но предъявленному сертификату верить нельзя.  Держится
    # отдельным полем, а не выводится из текста detail: разбирать сообщение об ошибке
    # строкой — значит поставить диагноз в зависимость от формулировок OpenSSL.
    sertifikat_krasnyj: bool = False


@dataclass(frozen=True)
class Verdict:
    checks: tuple[OneCheck, ...]
    outcome: str
    alarm: bool = False
    alarm_text: str = ""

    @property
    def passed(self) -> bool:
        return self.outcome == ZHIV

    @property
    def failed_names(self) -> tuple[str, ...]:
        return tuple(c.name for c in self.checks if not c.passed)

    def report(self) -> str:
        lines = [
            "  %-9s %s  %s" % (c.name, "PASS" if c.passed else "RED ", c.detail)
            for c in self.checks
        ]
        lines.append(
            "verdict: %s -- %s -- passed %d of %d checks"
            % (
                self.outcome.upper(),
                self.alarm_text or ("OK" if self.passed else "failure"),
                sum(1 for c in self.checks if c.passed),
                len(self.checks),
            )
        )
        lines.append("action: %s" % DEJSTVIE.get(self.outcome, "—"))
        if self.alarm:
            lines.append("ALARM: %s" % self.alarm_text)
        if not self.passed:
            lines.append("red checks: %s" % ", ".join(self.failed_names))
        return "\n".join(lines)


def read_host() -> str | None:
    """The bare host to probe over both schemes.

    ADRES-SAJTA.txt holds a host (``math-kluychiki.ru``); ADRES.txt, from the tunnel era,
    holds a full URL.  Either is accepted and reduced to a host, so that the fallback is a
    real fallback and not a second code path with its own bugs.
    """
    for f in (HOST_FILE, ADRES_FILE):
        if not f.exists():
            continue
        try:
            raw = f.read_text(encoding="utf-8").strip()
        except Exception:
            continue
        if not raw:
            continue
        return raw.split("://", 1)[-1].strip("/")
    return None


def probe(url: str) -> OneCheck:
    """One GET.  Distinguishes "answered with something" from "nothing came back"."""
    name = "https" if url.startswith("https://") else "http"
    check_url = url.rstrip("/") + RASPREDELENIE_PATH
    try:
        req = urllib.request.Request(check_url, method="GET")
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            status = resp.getcode()
            body = resp.read(BODY_BYTES).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        # A status code came back: the server IS reachable over this scheme.  Whatever is
        # wrong is behind it, and this is never the filtering signature.
        return OneCheck(name, False, True, "мёртв: status=%d" % exc.code)
    except (urllib.error.URLError, socket.timeout, ssl.SSLError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        # 🔴 ПРОВАЛЕННАЯ ПРОВЕРКА СЕРТИФИКАТА — ЭТО ДОКАЗАТЕЛЬСТВО, ЧТО 443 ДОХОДИТ, а не
        # опровержение.  Рукопожатие зашло достаточно далеко, чтобы сервер успел предъявить
        # сертификат; фильтрация на пути такого не допускает.  Без этой ветки просроченный
        # сертификат сваливался в «443 отфильтрован» — то есть сторож печатал «СЕРВЕР НЕ
        # ТРОГАТЬ, вопрос к провайдеру» ровно в том случае, когда чинить надо именно сервер.
        # Найдено верификатором захода на живом эталоне expired.badssl.com; текущий
        # сертификат годен до 05.12.2026, так что случай наступит сам, если продление
        # однажды не сработает.
        if isinstance(reason, ssl.SSLCertVerificationError) or isinstance(exc, ssl.SSLCertVerificationError):
            return OneCheck(name, False, True, "сертификат не проходит проверку: %s" % reason,
                            sertifikat_krasnyj=True)
        return OneCheck(name, False, False, "молчит на уровне сети: %s" % reason)
    if not 200 <= status < 300:
        return OneCheck(name, False, True, "мёртв: status=%d" % status)
    if OUR_CONTENT_MARKER not in body.lower():
        # 200 without our content is a provider banner standing where the site should be
        # (console.serveo.net did exactly this).  Reachable, but not us.
        return OneCheck(name, False, True, "мёртв: status=%d content_marker_MISSING body=%r" % (status, body[:200]))
    return OneCheck(name, True, True, "жив: status=%d content_marker_found" % status)


def postavit_diagnoz(po_http: OneCheck, po_https: OneCheck) -> str:
    """The whole point of the module: two probes in, one of five words out.

    The certificate branch stands BEFORE the filtering one on purpose: a certificate we do
    not trust is proof that 443 arrives, and it sends the reader to the server, not to the
    provider.  The order of the remaining branches is the order of how bad the news is, and
    the filtering branch is deliberately NARROW.  It fires only when http carries our content while https produced
    no network answer at all -- because that, and nothing weaker, is what the 2026-09-06
    measurement looked like.  Anything else that merely "does not work over https" is left as
    мёртв, so that the filtering verdict keeps meaning what it says.
    """
    if po_http.passed and po_https.passed:
        return ZHIV
    if po_https.sertifikat_krasnyj:
        return SERTIFIKAT
    if po_http.passed and not po_https.otvetil_seteviy:
        return OTFILTROVAN
    if po_https.passed and not po_http.otvetil_seteviy:
        return HTTP_LEG
    return MERTV


def load_state() -> str:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            return data.get("last_verdict", "")
        except Exception:
            return ""
    return ""


def save_state(verdict_str: str) -> None:
    try:
        STATE_FILE.write_text(json.dumps({"last_verdict": verdict_str}, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _report_first_healthy_run(outcome: str) -> str:
    """No saved state means no PREVIOUS run to compare against -- and "жив" never fails, so
    it never reaches `OnFailure=` either.  Without this, a watchdog that has watched
    faithfully since install can go its whole life without once telling anyone it exists.

    Only for the healthy case: an UNHEALTHY first run already exits non-zero below, and that
    is exactly what `OnFailure=spetsmat-alert@%n.service` (deploy/spetsmat-storozh-sajta.service)
    is for -- sending here too would be the same fact delivered twice through two channels.
    """
    try:
        # Two contexts, two import styles.  systemd runs this file directly
        # (`python3 @CHECKOUT@/ops/storozh_sajta.py`, matching every other unit in
        # deploy/), which puts ops/ itself -- not its parent -- on sys.path[0], so
        # `from ops import opoveshchenie` fails there with a real ImportError (found
        # live, 08.09: journalctl showed exactly that on the server's first real run).
        # Tests and any in-process caller import this module AS ``ops.storozh_sajta``,
        # where the reverse is true.  Try the direct-script shape first since that is
        # how production actually invokes it.
        import opoveshchenie
    except ImportError:
        try:
            from ops import opoveshchenie
        except ImportError:
            return "first run: %s, but opoveshchenie is not importable -- heartbeat not sent" % outcome
    try:
        opoveshchenie.send("сторож сайта поднялся впервые на этой машине, сайт %s" % outcome, kind="puls")
    except Exception as failure:  # a heartbeat must never crash the probe it is reporting on
        return "first run: %s, heartbeat FAILED to send: %s" % (outcome, failure)
    return "first run: %s, heartbeat sent" % outcome


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check the site over http AND https and name which ill it is.")
    parser.add_argument("--tiho", action="store_true", help="Silence alarm on first run even if state file exists.")
    args = parser.parse_args(argv)

    host = read_host()
    if host is None:
        checks: tuple[OneCheck, ...] = (OneCheck("adres", False, False, "не смог проверить: ни ADRES-SAJTA.txt, ни ADRES.txt"),)
        outcome = NE_SMOG
    else:
        print("адрес: %s" % host)
        po_http = probe("http://" + host)
        po_https = probe("https://" + host)
        checks = (po_http, po_https)
        outcome = postavit_diagnoz(po_http, po_https)

    prev = load_state()
    alarm = False
    if prev and prev != outcome:
        alarm_text = "%s -> %s" % (prev, outcome)
        alarm = not args.tiho
    elif not prev:
        if outcome == ZHIV and not args.tiho:
            alarm_text = _report_first_healthy_run(outcome)
        else:
            alarm_text = "first run (recorded, no alarm; unhealthy first runs alert via OnFailure=)"
    elif args.tiho:
        alarm_text = "silenced by --tiho"
    else:
        alarm_text = ""

    verdict = Verdict(checks=checks, outcome=outcome, alarm=alarm, alarm_text=alarm_text)
    print(verdict.report())
    save_state(outcome)

    return 0 if verdict.passed else 1


if __name__ == "__main__":
    sys.exit(main())
