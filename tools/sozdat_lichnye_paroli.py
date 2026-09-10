#!/usr/bin/env python3
"""Generate one personal password per active teacher AND per active pupil, hash it, write files.

WHY A SCRIPT AND NOT A LIST.  Who is an administrator is a RULE, not a roster line: an
administrator is the senior of an auditorium, and the база already knows who that is in two
independent places -- ``gruppy.starshij`` and ``teachers.gruppa``.  This script applies the rule
against the live база on every run, so the answer cannot drift out of date the way a hand-typed
list does.  The list is the output; the rule is this code.

WHAT IT WRITES
  secrets/veb-lichnye-paroli.json        salt + PBKDF2 hash + uid + role.  Read by veb/vhod.py.
  secrets/paroli-prepodavatelej-<date>.txt   the plaintext list, for the owner and nobody else.
  secrets/paroli-shkolnikov-<date>.txt       the same, for pupils, and a SEPARATE file on purpose:
                                             the two lists are handed out to different people on
                                             different days, and one file would mean handing a
                                             pupil the sheet that carries every teacher password.

PUPILS, added 2026-09-10 (заход `paroli-shkolnikov`).  The pupil password is NOT the twelve
random characters a teacher gets.  The owner chose its shape himself: Latin initials, ИМЯ first
and ФАМИЛИЯ second, plus a two-digit number -- his own example is `ИФ17` -- because he hands
these out on paper, in person, to fifty-four teenagers who will type them on a phone.

🔴 THE NUMBER IS RANDOM AND MUST STAY RANDOM.  `students.id` would have been the obvious
reading of "инициалы плюс номер", and it is the one reading that must not be used: the roster
of names is on the public half of the site, so an id-derived password is derivable by anyone
who can read the site, i.e. it is not a password at all.  Random keeps a guesser at about ninety
tries per named pupil -- weak, and named as weak in the заход's own list of what is not covered
(перебор паролей), but not zero.

🔴 THE INITIALS ARE STORED IN CLEAR, NEXT TO THE HASH, AND THAT IS DELIBERATE.  They are the
lookup key `veb/vhod.py` buckets by, and without them a login has to hash the submitted password
once per person -- fifty-four PBKDF2 rounds at about 62 ms is 3.3 s of a single-threaded server
for every wrong password.  Storing them leaks nothing: the same initials are already printed on
the public roster.  The secret is the two digits, and only they are hashed-and-hidden.

Both files are created with mode 600 and both live under ``secrets/``, which .gitignore excludes
(line 2).  The hashes deliberately do NOT go into ``data/spetsmat.db``: that file is tracked by git
on purpose (.gitignore line 14 carries an explicit ``!data/spetsmat.db``) and the repository is
public, so the first commit would publish them.

WHAT IT NEVER DOES.  It never prints a password, never passes one on a command line, never writes
one anywhere except the one file named above.  It refuses to overwrite existing files unless
``--perezapisat`` is given: a second run mints NEW passwords, and every password already handed out
would stop working.

🔴 IT MERGES INTO THE HASH FILE, IT DOES NOT REPLACE IT.  ``--kogo shkolniki`` mints pupils and
leaves every teacher entry in ``veb-lichnye-paroli.json`` byte-for-byte as it was.  Writing the
file whole would have logged all fourteen teachers out on the run that gave pupils their first
password -- silently, and on the morning the pupils were meant to try it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import sqlite3
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

# Alphabet without look-alike characters: no 0 O 1 l I.  These passwords get dictated by voice
# and typed by hand on a phone, so a character that has to be spelled out twice is a defect.
ALFAVIT = "abcdefghjkmnpqrstuvwxyz23456789"
DLINA = 12          # 31**12 is about 2**59 -- far beyond anything a dictionary reaches
GRUPPA_ZNAKOV = 4   # printed as 3 groups of 4, joined by "-", for dictation

# HASHING SCHEME, named rather than left to a default.
#
# 🔴 NOT scrypt, and the reason is measured, not assumed: the owner's Mac runs Python 3.9.6 against
# LibreSSL 2.8.3, where `hashlib.scrypt` DOES NOT EXIST (`hasattr(hashlib, "scrypt")` is False).
# The production server has it (Python 3.12 / OpenSSL 3), but the passwords are minted here, on the
# Mac, and a generator that only runs on the production machine is a generator nobody will re-run.
# So the named fallback is used: PBKDF2-HMAC-SHA256 at 200 000 iterations, which is the floor the
# заход sets.  More iterations buy nothing here: the passwords are machine-generated with about
# 2**59 of entropy, so the dictionary attack that stretching defends against does not apply, while
# every extra iteration is paid FOURTEEN times on every wrong password (the salt is per person, so
# the candidate has to be hashed once per person).  Measured on the server: 61.6 ms per hash at
# 200 000, i.e. 0.86 s for a login that matches nobody, on a server that runs one thread per request.
SHEMA = "pbkdf2_hmac_sha256"
ITERACII = 200_000
DKLEN = 32
DLINA_SOLI = 16


def sgenerirovat_parol() -> str:
    """One password: DLINA random characters, printed in groups for dictation."""
    znaki = "".join(secrets.choice(ALFAVIT) for _ in range(DLINA))
    return "-".join(znaki[i:i + GRUPPA_ZNAKOV] for i in range(0, DLINA, GRUPPA_ZNAKOV))


def zaheshirovat(parol: str, sol: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", parol.encode("utf-8"), sol, ITERACII, DKLEN).hex()


# ------------------------------------------------------------------ pupil passwords
#
# The owner's shape, in his own words and his own example: «инициалы плюс номер, сначала имя
# потом фамилия (ИФ17)».  Two Latin initials and two digits.

CIFR_V_PAROLE = 2
MIN_CHISLO = 10 ** (CIFR_V_PAROLE - 1)
MAX_CHISLO = 10 ** CIFR_V_PAROLE - 1

#: Cyrillic initial -> its Latin form.  Digraphs where a single letter would be a different
#: sound (Ж vs З, Ч vs Ц, Ш vs С); everything is uppercased, because these are read off paper
#: and typed on a phone, and mixed case on paper is a defect nobody would notice until a pupil
#: could not get in.
LATINICA = {
    "А": "A", "Б": "B", "В": "V", "Г": "G", "Д": "D", "Е": "E", "Ё": "E", "Ж": "ZH",
    "З": "Z", "И": "I", "Й": "I", "К": "K", "Л": "L", "М": "M", "Н": "N", "О": "O",
    "П": "P", "Р": "R", "С": "S", "Т": "T", "У": "U", "Ф": "F", "Х": "H", "Ц": "C",
    "Ч": "CH", "Ш": "SH", "Щ": "SCH", "Ы": "Y", "Э": "E", "Ю": "YU", "Я": "YA",
}


def initsialy(imya: str, familiya: str) -> str:
    """`Ирина Агаркова` -> `IA`.  ИМЯ first, ФАМИЛИЯ second -- the owner said which way round.

    A letter this table does not know (a Latin name in the roster, a hyphen, a stray space)
    is passed through uppercased rather than dropped: dropping it would silently give two
    different pupils the same initials, and the collision would surface as one of them being
    unable to log in.
    """
    def bukva(slovo: str) -> str:
        znak = (slovo or "").strip()[:1].upper()
        return LATINICA.get(znak, znak)
    return bukva(imya) + bukva(familiya)


def sgenerirovat_parol_shkolnika(nachalo: str, zanyato: set) -> str:
    """`IA` -> `IA17`, with a RANDOM number and never one already handed to somebody else.

    `zanyato` holds every password string minted in this run and every one already in the
    file, so two pupils can never end up sharing a password -- a shared password would let
    `veb/vhod.py` answer the login with whichever of them it reached first, and the pupil who
    lost the race would see somebody else's page while being certain they typed their own.

    Two digits give ninety candidates.  When a set of initials is that crowded (it takes about
    a dozen pupils sharing two initials before it bites) the number grows by one digit for that
    pupil rather than the run failing: a longer password for one person beats no password.
    """
    for cifr in range(CIFR_V_PAROLE, CIFR_V_PAROLE + 3):
        nizhnyaya, verhnyaya = 10 ** (cifr - 1), 10 ** cifr - 1
        svobodnye = [n for n in range(nizhnyaya, verhnyaya + 1)
                     if "%s%d" % (nachalo, n) not in zanyato]
        if svobodnye:
            return "%s%d" % (nachalo, secrets.choice(svobodnye))
    raise SystemExit("initials %r are exhausted -- no free number of any length" % nachalo)


def prochitat_shkolnikov(db_path: Path) -> list:
    """Active pupils, in the same shape `prochitat_lyudej` returns for teachers.

    Read-only URI for the same reason as there: this script must not be able to write to a live
    production база even by accident.

    🔴 `uid` HERE IS `students.id`, NOT `teachers.id`.  The two namespaces overlap -- id 3 is a
    person in both tables -- and the only thing that keeps them apart is the role beside them.
    `veb/vhod.py` is where that separation is enforced (`kto()` answers for teachers only,
    `shkolnik()` for pupils only); this comment exists so that the next person to widen this
    file knows the field is not a single global id.
    """
    connection = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
    # 🔴 ПЕРВОЙ СТРОКОЙ — ОТКУДА ЧИСЛА (Д1, владелец 10.09): путь и дата последней
    # ЗАПИСИ внутри базы, красное — если база старше последнего занятия.
    try:                                  # запуск и модулем, и файлом из tools/
        from core.istochnik import nazvat_i_proverit
    except ModuleNotFoundError:           # прямой запуск: корня репозитория нет в sys.path
        import sys as _s, pathlib as _p
        _s.path.insert(0, str(_p.Path(__file__).resolve().parent.parent))
        from core.istochnik import nazvat_i_proverit
    nazvat_i_proverit(connection)
    connection.row_factory = sqlite3.Row
    lyudi = []
    for row in connection.execute(
        "select id, surname, name, class from students where status = 'active' order by id"
    ):
        lyudi.append({
            "uid": row["id"],
            "imya": row["name"],
            "familiya": row["surname"],
            "klass": row["class"],
            "rol": "shkolnik",
        })
    connection.close()
    if not lyudi:
        raise SystemExit("no active pupils in %s -- refusing to write empty files" % db_path)
    return lyudi


def prochitat_fajl_heshej(put: Path) -> dict:
    """What is already in the hash file, or an empty shell when there is none.

    Read before writing, because a mint of one kind of person must leave the other kind's
    entries exactly as they were.  A file that exists but cannot be parsed STOPS the run: the
    alternative is overwriting fourteen working teacher passwords with an empty list.
    """
    try:
        raw = put.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    try:
        soderzhimoe = json.loads(raw)
        if not isinstance(soderzhimoe, dict) or not isinstance(soderzhimoe.get("lyudi"), list):
            raise ValueError("no 'lyudi' list")
    except ValueError as oshibka:
        raise SystemExit(
            "REFUSED: %s exists and cannot be read (%s). Refusing to write over it: it holds "
            "the passwords people are logging in with right now." % (put, oshibka))
    return soderzhimoe


def prochitat_lyudej(db_path: Path) -> list[dict]:
    """Active teachers plus the rule that says which of them are administrators.

    Read-only URI: this script must not be able to write to a live production база even by
    accident, and it must not create a WAL beside it either.
    """
    connection = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
    connection.row_factory = sqlite3.Row
    starshie = {row["starshij"] for row in connection.execute("select starshij from gruppy")}
    lyudi = []
    for row in connection.execute(
        "select id, name, aka, gruppa from teachers where aktiven = 1 order by id"
    ):
        lyudi.append({
            "uid": row["id"],
            "imya": row["name"],
            "aka": row["aka"],
            "gruppa": row["gruppa"],
            "rol": "organizator" if row["name"] in starshie else "prepod",
        })
    connection.close()
    if not lyudi:
        raise SystemExit("no active teachers in %s -- refusing to write empty files" % db_path)
    return lyudi


def zapisat_600(put: Path, tekst: str) -> None:
    """Create the file with mode 600 from the very first byte, not chmod-ed afterwards."""
    put.parent.mkdir(parents=True, exist_ok=True)
    deskriptor = os.open(put, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(deskriptor, "w", encoding="utf-8") as fajl:
        fajl.write(tekst)
    os.chmod(put, stat.S_IRUSR | stat.S_IWUSR)


ROLI_PREPODAVATELEJ = ("organizator", "prepod")


def main() -> int:
    razbor = argparse.ArgumentParser(description=__doc__)
    # 🔴 БЕЗ УМОЛЧАНИЯ-ПУТИ: см. `doc/ISTOCHNIK-BAZY.md`. Умолчание от корня
    # репозитория — второе имя базы мимо `config`, которое среда не перебивает.
    razbor.add_argument("--db", default=None,
                        help="база; без него — та, что назвала переменная SPETSMAT_BAZA")
    razbor.add_argument("--secrets", default="secrets", help="directory the files go into")
    razbor.add_argument("--data", default=datetime.now(timezone.utc).strftime("%Y%m%d"),
                        help="date suffix of the plaintext list, ГГГГММДД")
    razbor.add_argument("--perezapisat", action="store_true",
                        help="mint new passwords even though files already exist")
    # 🔴 THE DEFAULT IS `prepodavateli`, NOT `vse`, AND THAT IS NOT TIMIDITY.  Whoever runs this
    # script bare today gets exactly what it did before pupils existed.  A default of `vse`
    # would mean that the next bare run -- by a person reaching for the teacher list -- mints
    # fifty-four new pupil passwords and invalidates every one already handed out on paper.
    razbor.add_argument("--kogo", choices=("prepodavateli", "shkolniki", "vse"),
                        default="prepodavateli",
                        help="whose passwords to mint; the others are left untouched")
    argumenty = razbor.parse_args()

    # Назвали базу флагом — источник не спрашиваем вовсе: у вызывающего адрес уже
    # есть. Не назвали — спрашиваем, и корень репозитория кладём в `sys.path` сами:
    # файл запускают из `tools/`, и своим корнем он видит `tools/`.
    if argumenty.db:
        db_path = Path(argumenty.db).resolve()
    else:
        koren = str(Path(__file__).resolve().parent.parent)
        if koren not in sys.path:
            sys.path.insert(0, koren)
        import config
        db_path = config.DB_PATH.resolve()
    katalog = Path(argumenty.secrets)
    fajl_heshej = katalog / "veb-lichnye-paroli.json"
    spiski = {
        "prepodavateli": katalog / ("paroli-prepodavatelej-%s.txt" % argumenty.data),
        "shkolniki": katalog / ("paroli-shkolnikov-%s.txt" % argumenty.data),
    }
    chinim = (("prepodavateli", "shkolniki") if argumenty.kogo == "vse"
              else (argumenty.kogo,))

    bylo = prochitat_fajl_heshej(fajl_heshej)
    prezhnie = bylo.get("lyudi") or []

    # REFUSAL IS PER KIND, because the mint is now per kind.  Existing pupil entries block a
    # pupil mint and say nothing about a teacher one, and the other way round.
    for rod in chinim:
        est_v_heshah = any(
            (z.get("rol") == "shkolnik") == (rod == "shkolniki")
            for z in prezhnie if isinstance(z, dict))
        prichina = ("entries for %s are already in %s" % (rod, fajl_heshej) if est_v_heshah
                    else "%s already exists" % spiski[rod] if spiski[rod].exists() else "")
        if prichina and not argumenty.perezapisat:
            print("REFUSED: %s. A second run mints NEW passwords and every password already "
                  "handed out stops working. Pass --perezapisat if that is what you mean."
                  % prichina, file=sys.stderr)
            return 1

    # Every password string that must not be reused: the ones surviving from the kinds we are
    # NOT minting, and everything this run has already produced.
    zanyato = set()

    zapisi = [z for z in prezhnie if isinstance(z, dict)
              and ((z.get("rol") == "shkolnik") != ("shkolniki" in chinim))]
    otchet = []

    if "prepodavateli" in chinim:
        lyudi = prochitat_lyudej(db_path)
        stroki = ["# personal passwords for the site, generated %s -- hand out and delete nothing else"
                  % datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                  "# role organizator = senior of an auditorium (sees распределение); prepod = everyone else",
                  ""]
        for chelovek in lyudi:
            parol = sgenerirovat_parol()
            sol = secrets.token_bytes(DLINA_SOLI)
            zanyato.add(parol)
            zapisi.append({
                "uid": chelovek["uid"],
                "imya": chelovek["imya"],
                "gruppa": chelovek["gruppa"],
                "rol": chelovek["rol"],
                "sol": sol.hex(),
                "hesh": zaheshirovat(parol, sol),
            })
            stroki.append("%-20s  аудитория %-2s  %-12s  %s"
                          % (chelovek["imya"], chelovek["gruppa"] or "-", chelovek["rol"], parol))
        zapisat_600(spiski["prepodavateli"], "\n".join(stroki) + "\n")
        otchet.append(("prepodavateli", len(lyudi), spiski["prepodavateli"]))

    if "shkolniki" in chinim:
        deti = prochitat_shkolnikov(db_path)
        stroki = ["# personal passwords for the site, pupils, generated %s"
                  % datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                  "# hand each line to its own pupil on paper; a pupil may change the password afterwards",
                  ""]
        for rebyonok in deti:
            nachalo = initsialy(rebyonok["imya"], rebyonok["familiya"])
            parol = sgenerirovat_parol_shkolnika(nachalo, zanyato)
            sol = secrets.token_bytes(DLINA_SOLI)
            zanyato.add(parol)
            zapisi.append({
                "uid": rebyonok["uid"],
                "imya": rebyonok["imya"],
                "familiya": rebyonok["familiya"],
                "klass": rebyonok["klass"],
                "rol": "shkolnik",
                # The bucket key `veb/vhod.py` looks a submitted password up by.  Public
                # information; see the module docstring for why storing it leaks nothing.
                "nachalo": nachalo,
                "sol": sol.hex(),
                "hesh": zaheshirovat(parol, sol),
            })
            stroki.append("%-16s %-14s %-4s  %s"
                          % (rebyonok["familiya"], rebyonok["imya"],
                             rebyonok["klass"] or "-", parol))
        zapisat_600(spiski["shkolniki"], "\n".join(stroki) + "\n")
        otchet.append(("shkolniki", len(deti), spiski["shkolniki"]))

    soderzhimoe = {
        "shema": SHEMA,
        "parametry": {"hesh": "sha256", "iteracii": ITERACII, "dklen": DKLEN},
        "sozdano": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "istochnik": str(db_path),
        "lyudi": zapisi,
    }
    zapisat_600(fajl_heshej, json.dumps(soderzhimoe, ensure_ascii=False, indent=2) + "\n")

    # Counts only.  A password printed here would land in the shell history and in the log of
    # whoever ran this, which is exactly the leak this project has already paid for once.
    prepody = [z for z in zapisi if z.get("rol") in ROLI_PREPODAVATELEJ]
    print("teachers: %d (organizator %d, prepod %d), pupils: %d -- %d entries in the file"
          % (len(prepody),
             sum(1 for z in prepody if z["rol"] == "organizator"),
             sum(1 for z in prepody if z["rol"] == "prepod"),
             sum(1 for z in zapisi if z.get("rol") == "shkolnik"),
             len(zapisi)))
    print("minted this run: %s" % (", ".join("%s %d" % (rod, n) for rod, n, _ in otchet) or "nobody"))
    print("hashes: %s (mode %o)" % (fajl_heshej, fajl_heshej.stat().st_mode & 0o777))
    for rod, _, put in otchet:
        print("list %-14s %s (mode %o, %d lines)"
              % (rod, put, put.stat().st_mode & 0o777,
                 len(put.read_text(encoding="utf-8").splitlines())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
