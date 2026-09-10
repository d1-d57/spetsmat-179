"""Web entry point (vhod) — one personal password per teacher, two common ones behind them.

This file is part of zone `veb-vhod-i-obshchee-sostoyanie`.
The two public declarations (`marshruty`, `rol`) are inserted by the
neighbouring server; everything else lives here.

PERSONAL PASSWORDS, added 2026-09-07.  Each active teacher has a password of their own; three
of them — the seniors of the auditoriums — get the role `organizator` from that same password.
The hashes live in a file under `secrets/`, never in `data/spetsmat.db`: that база is tracked by
git on purpose and the repository is public.  See `tools/sozdat_lichnye_paroli.py`, which mints
the passwords and applies the rule "senior of an auditorium = administrator" against the live база.

The two common passwords from the environment KEEP WORKING, unchanged, behind the personal ones.
Losing them would lock all fourteen people out, and one of them is easy to overlook.

PUPILS, added 2026-09-10 (заход `paroli-shkolnikov`).  Fifty-four pupils get a personal password
of their own, minted by the same script.  Their role is `shkolnik`, and the boundary between them
and the fifteen adults is drawn HERE, in this file, by what the three identity functions are
willing to answer:

    rol(headers)       -> 'prepod' | 'organizator' | None      pupils get None
    kto(headers)       -> teachers.id | None                   pupils get None
    shkolnik(headers)  -> students.id | None                   adults get None

🔴 `rol()` ANSWERING `None` FOR A SIGNED-IN PUPIL IS THE WHOLE SAFETY ARGUMENT, AND IT IS AN
ARGUMENT ABOUT CODE THAT WAS NEVER EDITED.  Every gate on this site asks `rol()`: ticking a
problem (`veb/priyom.py:159`), seeing anybody's marks at all (`veb/server.py:893`), editing
(`veb/server.py::_pravka_zapreshchena`), the root page (`veb/server.py::_koren`).  Because a
pupil's cookie makes every one of them answer exactly what a guest's absence of cookie answers,
a pupil cannot tick and cannot read a single mark -- their own included -- and NOT ONE of those
files had to be changed for that to be true.  A boundary that holds because four other files
each remembered to check a role is a boundary that fails the first time a fifth file forgets.

🔴 `kto()` AND `shkolnik()` READ DIFFERENT TABLES AND MUST NEVER BE MERGED.  `uid` means
`teachers.id` under an adult role and `students.id` under `shkolnik`; id 3 is a person in both.
`veb/server.py` builds `"admin:%d" % kto(...)` out of the first one, so a pupil id arriving
there would name a teacher who is not the person who logged in.

🔴 NEITHER FUNCTION TAKES AN IDENTIFIER FROM THE REQUEST.  `shkolnik(headers)` answers for the
cookie's own pupil and has no parameter a caller could pass somebody else's id into.  "Pupil A
asks for pupil B" is therefore not a request this file can be persuaded to answer -- there is no
argument to put B in.
"""

from __future__ import annotations

import base64
import hmac
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ------------------------------------------------------------------ env keys

# READ AT USE, NOT AT IMPORT.  These were module-level constants, and that is what made
# the guard below unfixable on its own: whichever test module imported veb.vhod FIRST
# froze the values, so a later module setting the variables changed nothing.  Import
# order decided whether the suite passed -- and pytest collects alphabetically, so
# test_server.py (no secrets) always froze them before test_vhod.py (which sets them).
# Functions cost one dict lookup per call and remove the ordering entirely.

def _parol_prepod() -> str:
    return os.environ.get("SPETSMAT_VEB_PAROL_PREPOD", "")


def _parol_org() -> str:
    return os.environ.get("SPETSMAT_VEB_PAROL_ORG", "")


def _secret() -> str:
    return os.environ.get("SPETSMAT_VEB_SECRET", "")


def _fajl_lichnyh() -> Path:
    """Where the personal hashes live.  Read at use, for the same reason as the passwords above.

    Path is relative to the project root, which works both in a checkout and in the deployed
    `/opt/spetsmat-bot` (the unit sets `WorkingDirectory` there, but nothing guarantees the
    process's cwd, so the path is derived from this file instead).
    """
    iz_sredy = os.environ.get("SPETSMAT_VEB_LICHNYE", "")
    if iz_sredy:
        return Path(iz_sredy)
    return Path(__file__).resolve().parent.parent / "secrets" / "veb-lichnye-paroli.json"


def _fajl_smenennyh() -> Path:
    """Where a password somebody CHOSE FOR THEMSELVES lives.  A second file, on purpose.

    `tools/sozdat_lichnye_paroli.py` rewrites the minted file whenever the owner mints a kind of
    person afresh.  A password a pupil chose has to survive that -- «смена пароля на свой, и он
    запоминается навсегда» -- and the only way it survives is by not being in the file that gets
    rewritten.  See `core/services/lichnye_paroli.py`, which owns the writing half.
    """
    iz_sredy = os.environ.get("SPETSMAT_VEB_SMENENNYE", "")
    if iz_sredy:
        return Path(iz_sredy)
    return Path(__file__).resolve().parent.parent / "secrets" / "veb-smenennye-paroli.json"

# ------------------------------------------------------------------ cookie constants

#: The roles that mean "a member of staff": everything this site could already do before pupils
#: existed is gated on one of these two, and `rol()` answers with nothing else.
ROLI_PERSONALA = ("prepod", "organizator")

#: Every role a signed cookie may legitimately carry.  `shkolnik` is here so that a pupil's
#: cookie VERIFIES; it is deliberately absent from `ROLI_PERSONALA` so that verifying gets a
#: pupil precisely nothing beyond being recognised as themselves.
ROLI = ROLI_PERSONALA + ("shkolnik",)

COOKIE_NAME = "spetsmat_veb"
COOKIE_MAX_AGE_DAYS = 30
COOKIE_MAX_AGE_SECONDS = COOKIE_MAX_AGE_DAYS * 24 * 3600


def proverit_okruzhenie() -> None:
    """Refuse to START without the secrets.  Called by the server, not by import.

    The demand this satisfies is "a missing env variable must stop the server with a
    clear message, never default silently".  It says STARTUP -- and importing a module
    is not starting a server.  Calling this at import time made the guard fire for
    every reader of the module: pytest COLLECTING tests/veb/test_server.py has no
    secrets in its environment and never intends to serve a request, so the whole web
    suite stopped being collected (945 passed -> 1 collection error).  A guard that
    takes the test suite down with it protects nothing.

    So the check lives at the one place that actually starts a server -- veb/server.py
    main() -- and the tests that exercise signing pass the secret in explicitly.
    """
    missing: list[str] = []
    if not _secret():
        missing.append("SPETSMAT_VEB_SECRET")
    if missing:
        raise RuntimeError(
            "veb/vhod.py: missing required environment variable(s): "
            + ", ".join(missing)
        )


# ------------------------------------------------------------------ public contract

def marshruty():
    """Paths of the entry page: {path: handler}."""
    return {"/vhod": obrabotchik_vhoda, "/vyhod": obrabotchik_vyhoda}


def _kuka_iz_zagolovkov(headers) -> Optional[str]:
    """Our cookie's raw value out of a request's headers, or None if it is not there."""
    cookie_header = ""
    if hasattr(headers, "get"):
        cookie_header = headers.get("Cookie", "")
    for part in cookie_header.split(";"):
        part = part.strip()
        if part.startswith(COOKIE_NAME + "="):
            return part[len(COOKIE_NAME) + 1:]
    return None


def rol(headers) -> Optional[str]:
    """Role from cookie in request headers: 'prepod' | 'organizator' | None.

    None means "not allowed": the caller must redirect to /vhod.

    🔴 A PUPIL'S COOKIE ANSWERS `None` HERE, AND EVERY CALLER IS MEANT TO BELIEVE IT.  It is a
    perfectly valid, correctly signed, unexpired cookie; it just does not name anybody who may
    do anything.  This is the single line that keeps a signed-in pupil from ticking a problem
    and from reading a mark -- see the module docstring for why the answer is given here rather
    than by asking four other files to remember a new role.
    """
    cookie_value = _kuka_iz_zagolovkov(headers)
    if cookie_value is None:
        return None
    return _verify_cookie(cookie_value)


def kto(headers) -> Optional[int]:
    """Which person the cookie belongs to: `teachers.id`, or None when it does not say.

    None is the ordinary answer for two different situations that the caller must treat the same
    way: a cookie signed before personal passwords existed (it carries a role and no person), and
    an entry by one of the two common passwords (nobody in particular).  Identity is therefore an
    ADDITION to the role, never a replacement: `rol()` keeps answering for both.

    Nobody calls this yet.  The position that owns `veb/server.py` will.
    """
    cookie_value = _kuka_iz_zagolovkov(headers)
    if cookie_value is None:
        return None
    return _uid_pri_roli(cookie_value, ROLI_PERSONALA)


def shkolnik(headers) -> Optional[int]:
    """Which PUPIL the cookie belongs to: `students.id`, or None when it is not a pupil's.

    🔴 THIS IS THE ONLY WAY A PUPIL'S IDENTITY IS READABLE, AND IT TAKES NO IDENTIFIER.  The
    answer comes out of the signed cookie and nowhere else, so the request cannot name whose
    card it wants: an attempt by pupil A to be served pupil B has no field to carry B in, and
    a cookie edited to say B fails the HMAC before this function ever sees a number.

    An adult's cookie answers None here, exactly as a pupil's answers None in `kto()`.  The two
    ids live in different tables and the roles beside them are the only thing telling them apart.

    Nobody calls this yet: the page a pupil lands on is `veb/razdely/kartochka.py` and the route
    to it is in `veb/server.py`, both outside this заход's zone.  It is the door they will use.
    """
    cookie_value = _kuka_iz_zagolovkov(headers)
    if cookie_value is None:
        return None
    return _uid_pri_roli(cookie_value, ("shkolnik",))


def _uid_pri_roli(cookie_value: str, roli: tuple) -> Optional[int]:
    """The `u` a valid cookie carries, but only when its role is one of `roli`.

    One body for `kto` and `shkolnik` so that the two cannot drift apart: an id accepted under
    the wrong role is exactly the defect both of them exist to prevent, and two copies of this
    test would be two chances to fix only one.
    """
    payload = _payload_kuki(cookie_value)
    if payload is None:
        return None
    if payload.get("r") not in roli:
        return None
    uid = payload.get("u")
    if isinstance(uid, bool) or not isinstance(uid, int):
        return None
    return uid


def obrabotchik_vhoda() -> bytes:
    """Handler for GET /vhod — entry form.

    The form `action` is RELATIVE (`/vhod`), and that is the whole point of it.
    It was an absolute `https://…` address between 2026-09-08 05:40 and 2026-09-08
    (заход profil-bezopasnosti -> заход bystro-i-bezopasno), and that one attribute
    silently moved the owner's entire session onto port 443: the POST went to the https
    origin, the 302 that answers it carries a RELATIVE `Location`, so every click after
    the login stayed on https too. Measured on the owner's laptop before this change:
    20 submissions out of 20 landed on `https://`, median 1.271 s against 0.089 s for
    the page before the login. Port 443 on this path is filtered INTERMITTENTLY (probe of
    2026-09-06: 30 successes out of 30, an hour later 3 timeouts out of 3; the analyst's
    connection did not come up at 13:20 on 2026-09-08 while the owner complained), so the
    absolute action made a working site depend on the one thing here known to come and go.
    A relative action leaves the visitor on whichever scheme they arrived by.

    Forcing https was never a Google requirement: `ZAMYSEL-profil-bezopasnosti.md` §4 names
    the VISIBLE WARNING LINE below as the maximum that is legitimate here, and all seven
    clauses of that заход are closed by nginx, not by this attribute. A redirect and HSTS
    stay ruled out for the same reason as before (`https-i-domen`): a redirect already took
    the whole site down once. `marshruty()` hands this function to the neighbouring server
    with zero arguments (`vhod.marshruty()[path]()`), so nothing here can see which scheme
    the request arrived on — which is exactly why the answer must be scheme-neutral.
    The `hidden` paragraph is shown by inline JS only when `location.protocol` is
    `http:`, so an https visitor never sees a warning that does not apply to them; the
    link in it stays, so the owner can still choose https deliberately.
    """
    # The page is served as static HTML with embedded CSS reference.
    # See veb/static/vhod.css for styling.
    html_str = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Вход — Спецмат</title>
<link rel="stylesheet" href="/static/vhod.css">
</head>
<body>
<header>
  <h1>Спецмат — вход</h1>
  <p>Преподаватель или организатор. Без имён пользователей.</p>
</header>
<main>
  <p id="http-predupr" class="note" hidden>
    Этот адрес открыт без шифрования. Откройте
    <a href="https://math-kluychiki.ru/vhod">https://math-kluychiki.ru/vhod</a>.
  </p>
  <form method="post" action="/vhod">
    <label for="parol">Пароль</label>
    <input type="password" id="parol" name="parol" required autocomplete="current-password">
    <button type="submit">Войти</button>
  </form>
  <p class="note">Два уровня: преподаватель и организатор. Общие пароли из окружения.</p>
  <p class="stale">Данные обновляются при перезагрузке страницы; у других могло измениться — обновите страницу.</p>
</main>
<script>
if (location.protocol === "http:") {
  document.getElementById("http-predupr").hidden = false;
}
</script>
</body>
</html>"""
    return html_str.encode("utf-8")


def obrabotchik_vyhoda() -> bytes:
    """Handler for GET /vyhod — clears cookie and redirects back."""
    return "<!doctype html><html><head><meta http-equiv=\"refresh\" content=\"0;url=/vhod\"></head><body>Выход выполнен.</body></html>".encode("utf-8")


# ------------------------------------------------------------------ cookie helpers

def _sign(value: str) -> str:
    if not _secret():
        raise RuntimeError("SPETSMAT_VEB_SECRET is not set: cookie signature impossible")
    sig = hmac.new(
        _secret().encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{value}.{sig}"


def _payload_kuki(raw: str) -> Optional[dict]:
    """Signature, decoding and expiry in ONE place: everything a valid cookie says, or None.

    Extracted so that `rol` and `kto` cannot drift apart — a cookie accepted for its role and
    rejected for its person (or the other way round) would be a defect nobody would notice until
    it mattered.  The checks themselves are the ones that were here before, unchanged.
    """
    if "." not in raw:
        return None
    value, sig = raw.rsplit(".", 1)
    expected = hmac.new(
        _secret().encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    # Decode payload: base64url (padding restored) then JSON
    try:
        padding = "=" * (-len(value) % 4)
        payload_str = base64.urlsafe_b64decode(value + padding).decode("utf-8")
        payload = json.loads(payload_str)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    role = payload.get("r")
    ts = payload.get("t")
    # 🔴 `ROLI`, NOT `ROLI_PERSONALA`: a pupil's cookie has to VERIFY here, or `shkolnik()`
    # could never recognise anybody.  What it does not do is escape this function as a role —
    # `_verify_cookie` below narrows it back down, and that is what `rol()` returns.
    if role not in ROLI or ts is None:
        return None
    # 30-day expiry
    if time.time() - ts > COOKIE_MAX_AGE_SECONDS:
        return None
    return payload


def _verify_cookie(raw: str) -> Optional[str]:
    """The STAFF role a cookie carries, and nothing beyond it.  The server depends on that.

    🔴 THE NARROWING IS HERE ON PURPOSE AND MUST NOT BE MOVED UP INTO `_payload_kuki`.  A pupil's
    cookie is valid and `_payload_kuki` says so; it is this function — the one `rol()` answers
    out of — that declines to hand a pupil's role to code written when only adults existed.
    """
    payload = _payload_kuki(raw)
    if payload is None:
        return None
    role = payload.get("r")
    return role if role in ROLI_PERSONALA else None


def _make_cookie(role: str, uid: Optional[int] = None) -> str:
    """Sign a cookie for `role`, optionally naming the person it belongs to.

    🔴 `uid` IS OPTIONAL AND MUST STAY OPTIONAL.  `veb/server.py` calls `_make_cookie(role)` with
    one positional argument, and the cookies already in people's browsers carry `{"r","t"}` and
    nothing else — they must keep verifying for their whole thirty days.  Neither `_sign` nor the
    secret is touched here for the same reason: a change to either logs everybody out at once.
    """
    telo = {"r": role, "t": int(time.time())}
    if uid is not None:
        telo["u"] = int(uid)
    payload = json.dumps(telo)
    encoded = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    return _sign(encoded)


# ------------------------------------------------------------------ personal passwords

def _lyudi() -> list:
    """The personal entries from the secrets file, or an empty list when there are none.

    An unreadable or broken file must NOT take the entry down: the two common passwords are the
    fallback that keeps fourteen people able to work.  It is not silent either — a file that
    exists but cannot be parsed says so on stderr, and journald keeps that.
    """
    put = _fajl_lichnyh()
    try:
        raw = put.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    except OSError as oshibka:
        print("veb/vhod.py: personal passwords file %s unreadable: %s" % (put, oshibka),
              file=sys.stderr)
        return []
    try:
        soderzhimoe = json.loads(raw)
        lyudi = soderzhimoe["lyudi"]
        if not isinstance(lyudi, list):
            raise ValueError("'lyudi' is not a list")
    except (ValueError, KeyError, TypeError) as oshibka:
        print("veb/vhod.py: personal passwords file %s is malformed: %s" % (put, oshibka),
              file=sys.stderr)
        return []
    return lyudi


def _smenennye() -> list:
    """Entries from `secrets/veb-smenennye-paroli.json` — passwords people chose for themselves.

    Same failure policy as `_lyudi()`: an absent file is the ordinary state (nobody has changed
    anything yet), and a broken one says so on stderr and is treated as empty rather than taking
    the entry down.  The cost of treating it as empty is that whoever changed their password
    falls back to the minted one; the cost of raising would be that nobody can log in at all.
    """
    put = _fajl_smenennyh()
    try:
        raw = put.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    except OSError as oshibka:
        print("veb/vhod.py: changed passwords file %s unreadable: %s" % (put, oshibka),
              file=sys.stderr)
        return []
    try:
        soderzhimoe = json.loads(raw)
        lyudi = soderzhimoe["lyudi"]
        if not isinstance(lyudi, list):
            raise ValueError("'lyudi' is not a list")
    except (ValueError, KeyError, TypeError) as oshibka:
        print("veb/vhod.py: changed passwords file %s is malformed: %s" % (put, oshibka),
              file=sys.stderr)
        return []
    return lyudi


def _shema_hesha(put: Optional[Path] = None) -> tuple:
    """(scheme name, parameters) taken from the file, so that a re-mint with other ones just works.

    The scheme is written down rather than assumed: a file hashed one way and read another way
    would reject every password in it, and the only visible symptom would be "nobody can log in".
    """
    put = _fajl_lichnyh() if put is None else put
    try:
        soderzhimoe = json.loads(put.read_text(encoding="utf-8"))
        shema = str(soderzhimoe.get("shema") or "pbkdf2_hmac_sha256")
        parametry = soderzhimoe.get("parametry") or {}
    except (OSError, ValueError):
        shema, parametry = "pbkdf2_hmac_sha256", {}
    return shema, parametry


def _hesh_kandidata(submitted: str, sol: bytes, shema: str, parametry: dict) -> Optional[str]:
    """Hash a submitted password the way the file says it was hashed, or None for a scheme we
    cannot compute.  PBKDF2 is what `tools/sozdat_lichnye_paroli.py` writes today (`hashlib.scrypt`
    does not exist on the Mac the passwords are minted on); scrypt is accepted here anyway, so that
    switching the generator over on a machine that has it needs no change on this side."""
    if shema == "pbkdf2_hmac_sha256":
        return hashlib.pbkdf2_hmac(
            "sha256",
            submitted.encode("utf-8"),
            sol,
            int(parametry.get("iteracii", 200_000)),
            int(parametry.get("dklen", 32)),
        ).hex()
    if shema == "scrypt" and hasattr(hashlib, "scrypt"):
        return hashlib.scrypt(
            submitted.encode("utf-8"),
            salt=sol,
            n=int(parametry.get("n", 2 ** 14)),
            r=int(parametry.get("r", 8)),
            p=int(parametry.get("p", 1)),
            dklen=int(parametry.get("dklen", 32)),
        ).hex()
    return None


#: What a pupil password looks like: Latin initials then digits, e.g. `IA17`.  Used ONLY to pick
#: which entries are worth hashing against, never to decide whether a password is right.
_FORMA_SHKOLNIKA = re.compile(r"^([A-Za-z]{1,8})([0-9]{1,4})$")


def _kandidaty(submitted: str) -> list:
    """`[(запись, схема, параметры)]` — every entry this password could belong to, in order.

    🔴 THIS FUNCTION EXISTS BECAUSE THE COST IS LINEAR IN PEOPLE AND THE PEOPLE JUST QUADRUPLED.
    The salt is per person, so a submitted password has to be hashed once per entry it is
    checked against: fourteen teachers cost about 0.86 s for a password matching nobody
    (measured on the server, 61.6 ms per PBKDF2 round at 200 000 iterations).  Adding
    fifty-four pupils would have made that 4.2 s, on a server that runs one thread per request
    — i.e. a wrong password from one pupil freezes the site for everybody for four seconds.

    So the pupil entries are BUCKETED by their initials, which the minting script stores in
    clear beside the hash.  A password of the pupil shape is checked against the pupils sharing
    its letters — typically one to three — and then against the adults.  Worst case is about
    seventeen rounds, i.e. no worse than the site was before pupils existed.  The initials leak
    nothing: the same names are printed on the public half of the site.  The secret is the
    number, and the number is still hashed.

    🔴 A CHANGED PASSWORD COMES FIRST AND ITS OWNER'S MINTED ONE IS DROPPED.  «Смена пароля на
    свой — и он запоминается навсегда»: if the old minted password kept working beside the new
    one, changing it would add a password rather than replace it, and the piece of paper the
    pupil was handed would go on being a way in for whoever picked it up.
    """
    shema_m, parametry_m = _shema_hesha()
    shema_s, parametry_s = _shema_hesha(_fajl_smenennyh())

    smenennye = [z for z in _smenennye() if isinstance(z, dict)]
    zamenili = {(z.get("rol"), z.get("uid")) for z in smenennye}

    otchekanennye = [z for z in _lyudi() if isinstance(z, dict)
                     and (z.get("rol"), z.get("uid")) not in zamenili]

    sovpadenie = _FORMA_SHKOLNIKA.match(submitted or "")
    nachalo = sovpadenie.group(1).upper() if sovpadenie else None

    deti = [z for z in otchekanennye if z.get("rol") == "shkolnik"]
    vzroslye = [z for z in otchekanennye if z.get("rol") != "shkolnik"]
    v_vedre = [z for z in deti if nachalo and str(z.get("nachalo", "")).upper() == nachalo]
    # An entry minted before `nachalo` existed cannot be bucketed and must not become
    # unreachable because of it: it goes in the tail, hashed like an adult's.
    bez_klyucha = [z for z in deti if not z.get("nachalo")]

    poryadok = [(z, shema_s, parametry_s) for z in smenennye]
    poryadok += [(z, shema_m, parametry_m) for z in v_vedre + vzroslye + bez_klyucha]
    return poryadok


def _proverit_lichnyj(submitted: str) -> Optional[tuple]:
    """(role, uid) of the person whose personal password this is, or None.

    An unsalted digest of a password a human can read out loud falls to a dictionary in
    minutes; that is the whole reason the per-person salt, and the cost `_kandidaty` bounds,
    are paid at all.
    """
    if not submitted:
        return None
    for chelovek, shema, parametry in _kandidaty(submitted):
        try:
            sol = bytes.fromhex(chelovek["sol"])
            ozhidaemyj = str(chelovek["hesh"])
        except (KeyError, TypeError, ValueError):
            continue
        poluchennyj = _hesh_kandidata(submitted, sol, shema, parametry)
        if poluchennyj is None:
            print("veb/vhod.py: personal passwords file names hashing scheme %r, which this "
                  "build cannot compute -- personal passwords are OFF" % shema, file=sys.stderr)
            return None
        if not hmac.compare_digest(poluchennyj, ozhidaemyj):
            continue
        rol_cheloveka = chelovek.get("rol")
        if rol_cheloveka not in ROLI:
            return None
        uid = chelovek.get("uid")
        return (rol_cheloveka, int(uid) if isinstance(uid, int) else None)
    return None


def proverit_parol(submitted: str) -> Optional[tuple]:
    """Everything the entry knows about a submitted password: (role, uid) or None.

    The role is `prepod`, `organizator` or — since 2026-09-10 — `shkolnik`; `uid` is
    `teachers.id` under the first two and `students.id` under the third, and the caller has to
    keep them apart the way `kto()` and `shkolnik()` do.

    `uid` is None for the two common passwords — they belong to nobody in particular, and that is
    a legitimate answer, not a missing one.

    🔴 THE PERSONAL CHECK RUNS FIRST, BEFORE THE GUARD ON THE TWO ENVIRONMENT VARIABLES.  Put it
    after, and the fourteen personal passwords stop working, silently, everywhere the environment
    is not set up — which is every developer machine in this project, and any server whose
    EnvironmentFile ever goes missing.

    `veb/server.py::_post_vhod` is the caller: it signs the cookie out of this answer, so this
    is where a pupil becomes a signed-in pupil rather than nobody.
    """
    lichnyj = _proverit_lichnyj(submitted)
    if lichnyj is not None:
        return lichnyj
    if not _parol_prepod() or not _parol_org():
        # If env passwords are missing, the server must refuse startup clearly,
        # but we must not expose which is which in error messages.
        return None
    if submitted == _parol_prepod():
        return ("prepod", None)
    if submitted == _parol_org():
        return ("organizator", None)
    return None


def _check_password(submitted: str) -> Optional[str]:
    """'prepod' | 'organizator' | None — the older, narrower answer, kept for its callers.

    🔴 A PUPIL'S PASSWORD ANSWERS `None` HERE, AND THAT IS THE SAFE ANSWER RATHER THAN A GAP.
    This function returns a role to be gated on, and every gate that reads one understands only
    the two staff roles; handing it `shkolnik` would mean each of those gates has to remember
    to reject a role it has never heard of.  A caller that wants to let a pupil in asks
    `proverit_parol` and gets the person as well — which is what `veb/server.py::_post_vhod`
    already does.
    """
    otvet = proverit_parol(submitted)
    if otvet is None or otvet[0] not in ROLI_PERSONALA:
        return None
    return otvet[0]


# ------------------------------------------------------------------ guard
#
# Deliberately NOT called here.  See proverit_okruzhenie() for why an import-time
# guard took the whole web test suite down.  The call site is veb/server.py main().
