#!/usr/bin/env python3
"""Site watchdog: checks the HTTPS tunnel URL and reports one of three outcomes.

State is kept in /tmp/spetsmat-storozh-sajta.state.json.  Alarm only on change.
"""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import urllib.request
import urllib.error
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADRES_FILE = ROOT / "deploy" / "ADRES.txt"
STATE_FILE = Path("/tmp/spetsmat-storozh-sajta.state.json")

CHECK_NAMES = ("site",)


@dataclass(frozen=True)
class OneCheck:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class Verdict:
    checks: tuple[OneCheck, ...]
    alarm: bool = False
    alarm_text: str = ""

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(c.passed for c in self.checks)

    @property
    def failed_names(self) -> tuple[str, ...]:
        return tuple(c.name for c in self.checks if not c.passed)

    def report(self) -> str:
        lines = [
            "  %-9s %s  %s" % (c.name, "PASS" if c.passed else "RED ", c.detail)
            for c in self.checks
        ]
        # Determine outcome from the first check's detail string.
        detail0 = self.checks[0].detail if self.checks else ""
        outcome = detail0.split(":", 1)[0].strip() if detail0 else ("жив" if self.passed else "мёртв")
        # If the detail indicates unknown, override to "не смог проверить".
        if "не смог проверить" in detail0:
            outcome = "не смог проверить"
        lines.append(
            "verdict: %s -- %s -- passed %d of %d checks"
            % (outcome.upper(), self.alarm_text or ("OK" if self.passed else "failure"),
               sum(1 for c in self.checks if c.passed), len(self.checks))
        )
        if self.alarm:
            lines.append("ALARM: %s" % self.alarm_text)
        if not self.passed:
            lines.append("red checks: %s" % ", ".join(self.failed_names))
        return "\n".join(lines)


def read_url() -> str | None:
    if not ADRES_FILE.exists():
        return None
    try:
        return ADRES_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        return None


def check_site(url: str | None) -> tuple[OneCheck, str, bool]:
    if url is None:
        return OneCheck("site", False, "ADRES.txt missing"), "не смог проверить: ADRES.txt missing", False
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.getcode()
            body = resp.read(512).decode("utf-8", errors="replace")
        if 200 <= status < 300:
            return OneCheck("site", True, "жив: status=%d" % status), "жив: status=%d" % status, True
        else:
            return OneCheck("site", False, "мёртв: status=%d" % status), "мёртв: status=%d body=%r" % (status, body[:200]), False
    except urllib.error.HTTPError as exc:
        return OneCheck("site", False, "мёртв: status=%d" % exc.code), "мёртв: status=%d body=%r" % (exc.code, exc.read(512).decode("utf-8", errors="replace")[:200]), False
    except Exception as exc:
        return OneCheck("site", False, "не смог проверить: %s" % exc), "не смог проверить: %s" % exc, False


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check the site through its tunnel URL.")
    parser.add_argument("--tiho", action="store_true", help="Silence alarm on first run even if state file exists.")
    args = parser.parse_args(argv)

    url = read_url()
    check, detail, is_alive = check_site(url)
    passed = is_alive
    verdict_str = detail.split(":", 1)[0].strip()

    prev = load_state()
    alarm = False
    alarm_text = ""

    outcome_str = detail.split(":", 1)[0].strip()

    if prev and prev != outcome_str:
        alarm_text = "%s -> %s" % (prev, outcome_str)
        alarm = True
    elif not args.tiho and not prev:
        alarm_text = "first run (recorded, no alarm)"
        alarm = False
    elif args.tiho and prev:
        alarm_text = "silenced by --tiho"
        alarm = False
    else:
        alarm_text = ""
        alarm = False

    verdict = Verdict(
        checks=(check,),
        alarm=alarm,
        alarm_text=alarm_text,
    )

    # Replace alarm_text for alarm case with the change string for clarity.
    if alarm:
        alarm_text = "%s -> %s" % (prev, outcome_str)

    verdict = Verdict(
        checks=(check,),
        alarm=alarm,
        alarm_text=alarm_text,
    )

    print(verdict.report())
    save_state(outcome_str)

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
