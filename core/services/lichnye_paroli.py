"""Changing a personal password to one you chose yourself, and keeping it forever.

WHY THIS IS A SERVICE AND NOT A SCRIPT.  The owner's decision was «пароль… с возможностью
потом сменить на любой свой», and the person doing the changing is a fourteen-year-old in a
browser, not the owner in a terminal.  So the rule lives here, callable by whatever offers the
form; `tools/smenit_parol.py` is its live call point today.

🔴 A CHANGED PASSWORD GOES IN ITS OWN FILE, NOT INTO THE MINTED ONE.
`tools/sozdat_lichnye_paroli.py` rewrites `secrets/veb-lichnye-paroli.json` for the kind of
person it is minting.  A password somebody chose has to survive that -- «и он запоминается
навсегда» -- and it survives by not living in the file that gets rewritten.  The two files are
read in the right order by `veb/vhod.py::_kandidaty`: a changed entry is checked first, and its
owner's minted entry is dropped from the candidates entirely, so the piece of paper the pupil
was handed stops being a way in the moment they replace it.

🔴 IT NEVER RETURNS, PRINTS OR LOGS A PASSWORD, either one.  The answer is a verdict and, on
refusal, a reason naming what was wrong -- never what was submitted.  The single leak this
project has already paid for was a password reaching a log.

WHAT IT DOES NOT DO.  It does not recover a forgotten password: there is nowhere to send a
reset to (pupils have no address in the база -- `students.tg_id` is null for all fifty-four),
and the owner hands these out on paper in person, which is also how a forgotten one is
replaced.  It does not rate-limit either; see `## ОТЧЁТ` of заход `paroli-shkolnikov` for the
list of what is deliberately not covered.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

#: Same scheme and the same cost as the minted file.  Written down rather than inherited, for
#: the reason `veb/vhod.py::_shema_hesha` gives: a file hashed one way and read another way
#: rejects every password in it, and the only visible symptom is "nobody can log in".
SHEMA = "pbkdf2_hmac_sha256"
ITERACII = 200_000
DKLEN = 32
DLINA_SOLI = 16

#: The shortest password a person may choose.  Four, because the minted one is four (`IA17`)
#: and a floor that forbids what the system itself handed out would be a floor nobody believes.
MIN_DLINA = 4
MAX_DLINA = 128


class OtkazSmeny(Exception):
    """The change did not happen, and the message says why -- without naming any password."""


def fajl_smenennyh(koren: Optional[Path] = None) -> Path:
    """The one path, so that this file and `veb/vhod.py` cannot disagree about where it is.

    🔴 THE ENVIRONMENT VARIABLE IS THE SAME ONE `veb/vhod.py::_fajl_smenennyh` READS.  A test
    or a deployment that redirects one and not the other would write changes into a file
    nothing reads, and the symptom would be "changing the password appears to work and then
    does nothing" -- which is the failure a person is least likely to report.
    """
    iz_sredy = os.environ.get("SPETSMAT_VEB_SMENENNYE", "")
    if iz_sredy:
        return Path(iz_sredy)
    koren = koren or Path(__file__).resolve().parent.parent.parent
    return koren / "secrets" / "veb-smenennye-paroli.json"


def _zapisat_600(put: Path, tekst: str) -> None:
    """Create with mode 600 from the first byte, not chmod-ed afterwards.

    The same helper as in the minting script, and deliberately a copy rather than an import:
    `core/services/` must not depend on `tools/`, and six lines of `os.open` are a smaller
    debt than that dependency.
    """
    put.parent.mkdir(parents=True, exist_ok=True)
    deskriptor = os.open(put, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(deskriptor, "w", encoding="utf-8") as fajl:
        fajl.write(tekst)
    os.chmod(put, stat.S_IRUSR | stat.S_IWUSR)


def _prochitat(put: Path) -> dict:
    """What is in the file, or an empty shell.  A broken file STOPS the change.

    Treating an unparsable file as empty here would silently discard every password already
    changed -- the opposite of «запоминается навсегда».  `veb/vhod.py` treats the same broken
    file as empty on the READING side on purpose: there, falling back to the minted password
    keeps people able to work, and it says so on stderr.
    """
    try:
        raw = put.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {"shema": SHEMA,
                "parametry": {"hesh": "sha256", "iteracii": ITERACII, "dklen": DKLEN},
                "lyudi": []}
    try:
        soderzhimoe = json.loads(raw)
        if not isinstance(soderzhimoe, dict) or not isinstance(soderzhimoe.get("lyudi"), list):
            raise ValueError("no 'lyudi' list")
    except ValueError as oshibka:
        raise OtkazSmeny(
            "%s exists and cannot be read (%s); refusing to write over it -- it holds the "
            "passwords people are logging in with right now" % (put, oshibka))
    return soderzhimoe


def proverit_novyj(novyj: str) -> None:
    """Raise `OtkazSmeny` if this is not something a person may set.  Says nothing else.

    The checks are the ones a person can act on: length, and no leading or trailing space --
    which is the one defect a person cannot see in a `type=password` field and would spend an
    evening on.
    """
    if novyj != novyj.strip():
        raise OtkazSmeny("пароль начинается или кончается пробелом")
    if len(novyj) < MIN_DLINA:
        raise OtkazSmeny("пароль короче %d знаков" % MIN_DLINA)
    if len(novyj) > MAX_DLINA:
        raise OtkazSmeny("пароль длиннее %d знаков" % MAX_DLINA)


def smenit(rol: str, uid: int, staryj: str, novyj: str,
           *, put: Optional[Path] = None, proverka=None) -> None:
    """Replace the password of ONE person, after proving the caller knows the current one.

    `proverka` is the function that answers «чей это пароль» — `veb/vhod.py::proverit_parol`
    in production, injected here so that this module does not import the web layer.

    🔴 THE CURRENT PASSWORD IS CHECKED AGAINST THE PERSON, NOT MERELY AGAINST THE FILE.  The
    check is `proverka(staryj) == (rol, uid)`: a password that belongs to SOMEBODY, just not
    to this person, is refused.  Accepting it would let any pupil who knows any other pupil's
    password rewrite that pupil's password out from under them, which is the same boundary
    failure as reading their card, arriving through the door meant to protect it.
    """
    if proverka is None:
        from veb.vhod import proverit_parol as proverka
    proverit_novyj(novyj)
    if proverka(staryj) != (rol, uid):
        raise OtkazSmeny("текущий пароль не подошёл")

    put = put or fajl_smenennyh()
    soderzhimoe = _prochitat(put)
    sol = secrets.token_bytes(DLINA_SOLI)
    zapis = {
        "rol": rol,
        "uid": int(uid),
        "sol": sol.hex(),
        "hesh": hashlib.pbkdf2_hmac(
            "sha256", novyj.encode("utf-8"), sol, ITERACII, DKLEN).hex(),
        "izmenen": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    # One entry per person: a second change replaces the first rather than adding a second
    # working password beside it.
    soderzhimoe["lyudi"] = [z for z in soderzhimoe["lyudi"]
                            if not (isinstance(z, dict)
                                    and z.get("rol") == rol and z.get("uid") == int(uid))]
    soderzhimoe["lyudi"].append(zapis)
    soderzhimoe["shema"] = SHEMA
    soderzhimoe["parametry"] = {"hesh": "sha256", "iteracii": ITERACII, "dklen": DKLEN}
    _zapisat_600(put, json.dumps(soderzhimoe, ensure_ascii=False, indent=2) + "\n")


def smenil_li(rol: str, uid: int, *, put: Optional[Path] = None) -> bool:
    """Has this person replaced their minted password?  A fact about the file, not a password.

    The page that offers the form uses it to say «пароль свой» rather than «пароль выданный»,
    which is the only thing a person can check without typing the password in.
    """
    put = put or fajl_smenennyh()
    try:
        soderzhimoe = _prochitat(put)
    except OtkazSmeny:
        return False
    return any(isinstance(z, dict) and z.get("rol") == rol and z.get("uid") == int(uid)
               for z in soderzhimoe["lyudi"])


#: Kept so that a caller comparing hashes does not have to reimplement the scheme.  Not used
#: by `smenit` itself, which hashes inline.
def zaheshirovat(parol: str, sol: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", parol.encode("utf-8"), sol, ITERACII, DKLEN).hex()


def sovpadaet(parol: str, sol_hex: str, hesh: str) -> bool:
    """Constant-time comparison, so that a caller cannot accidentally write `==`."""
    return hmac.compare_digest(zaheshirovat(parol, bytes.fromhex(sol_hex)), hesh)
