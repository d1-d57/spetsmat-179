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
"""

from __future__ import annotations

import base64
import hmac
import hashlib
import json
import os
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

# ------------------------------------------------------------------ cookie constants

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
    payload = _payload_kuki(cookie_value)
    if payload is None:
        return None
    uid = payload.get("u")
    if isinstance(uid, bool) or not isinstance(uid, int):
        return None
    return uid


def obrabotchik_vhoda() -> bytes:
    """Handler for GET /vhod — entry form.

    The form `action` is the ABSOLUTE `https://` address, deliberately, added
    2026-09-08 (заход profil-bezopasnosti). `marshruty()` hands this function to the
    neighbouring server with zero arguments (`vhod.marshruty()[path]()`), so nothing here
    can see which scheme the current request arrived on — a redirect would need that, an
    absolute action does not. Whatever page served the form, the browser POSTs the
    password to `https://` and never to a bare, unencrypted `http://` origin. A redirect
    was ruled out on purpose: port 443 is filtered on the path, intermittently, and a
    redirect already took the whole site down once (see `deploy/README.md` / the
    `https-i-domen` заход) — an HTML attribute cannot repeat that failure.
    The `hidden` paragraph is shown by inline JS only when `location.protocol` is
    `http:`, so an https visitor never sees an warning that does not apply to them.
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
  <form method="post" action="https://math-kluychiki.ru/vhod">
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
    if role not in ("prepod", "organizator") or ts is None:
        return None
    # 30-day expiry
    if time.time() - ts > COOKIE_MAX_AGE_SECONDS:
        return None
    return payload


def _verify_cookie(raw: str) -> Optional[str]:
    """The ROLE a cookie carries, and nothing beyond it.  The server depends on exactly that."""
    payload = _payload_kuki(raw)
    if payload is None:
        return None
    return payload.get("r")


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


def _shema_hesha() -> tuple:
    """(scheme name, parameters) taken from the file, so that a re-mint with other ones just works.

    The scheme is written down rather than assumed: a file hashed one way and read another way
    would reject every password in it, and the only visible symptom would be "nobody can log in".
    """
    put = _fajl_lichnyh()
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


def _proverit_lichnyj(submitted: str) -> Optional[tuple]:
    """(role, uid) of the person whose personal password this is, or None.

    The salt is per person, so a candidate has to be hashed once per person: fourteen hashes at
    about 62 ms each in the worst case (a password that matches nobody), on a server that runs one
    thread per request.  An unsalted digest of a password a human can read out loud falls to a
    dictionary in minutes; that is the whole reason the cost is paid at all.
    """
    if not submitted:
        return None
    shema, parametry = _shema_hesha()
    for chelovek in _lyudi():
        if not isinstance(chelovek, dict):
            continue
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
        if rol_cheloveka not in ("prepod", "organizator"):
            return None
        uid = chelovek.get("uid")
        return (rol_cheloveka, int(uid) if isinstance(uid, int) else None)
    return None


def proverit_parol(submitted: str) -> Optional[tuple]:
    """Everything the entry knows about a submitted password: (role, uid) or None.

    `uid` is None for the two common passwords — they belong to nobody in particular, and that is
    a legitimate answer, not a missing one.

    🔴 THE PERSONAL CHECK RUNS FIRST, BEFORE THE GUARD ON THE TWO ENVIRONMENT VARIABLES.  Put it
    after, and the fourteen personal passwords stop working, silently, everywhere the environment
    is not set up — which is every developer machine in this project, and any server whose
    EnvironmentFile ever goes missing.

    Nobody calls this yet.  The position that owns `veb/server.py` will; `_check_password` below
    is the same answer with the person dropped, which is what the server asks for today.
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
    """'prepod' | 'organizator' | None — the one line `veb/server.py` calls, unchanged.

    The server must not be able to tell that personal passwords now exist: it is held by a
    neighbouring session and its signature is a contract.
    """
    otvet = proverit_parol(submitted)
    return None if otvet is None else otvet[0]


# ------------------------------------------------------------------ guard
#
# Deliberately NOT called here.  See proverit_okruzhenie() for why an import-time
# guard took the whole web test suite down.  The call site is veb/server.py main().
