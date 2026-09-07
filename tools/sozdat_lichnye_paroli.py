#!/usr/bin/env python3
"""Generate one personal password per active teacher, hash it, and write two files.

WHY A SCRIPT AND NOT A LIST.  Who is an administrator is a RULE, not a roster line: an
administrator is the senior of an auditorium, and the база already knows who that is in two
independent places -- ``gruppy.starshij`` and ``teachers.gruppa``.  This script applies the rule
against the live база on every run, so the answer cannot drift out of date the way a hand-typed
list does.  The list is the output; the rule is this code.

WHAT IT WRITES
  secrets/veb-lichnye-paroli.json        salt + PBKDF2 hash + uid + role.  Read by veb/vhod.py.
  secrets/paroli-prepodavatelej-<date>.txt   the plaintext list, for the owner and nobody else.

Both files are created with mode 600 and both live under ``secrets/``, which .gitignore excludes
(line 2).  The hashes deliberately do NOT go into ``data/spetsmat.db``: that file is tracked by git
on purpose (.gitignore line 14 carries an explicit ``!data/spetsmat.db``) and the repository is
public, so the first commit would publish them.

WHAT IT NEVER DOES.  It never prints a password, never passes one on a command line, never writes
one anywhere except the one file named above.  It refuses to overwrite existing files unless
``--perezapisat`` is given: a second run mints NEW passwords, and every password already handed out
would stop working.
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


def main() -> int:
    razbor = argparse.ArgumentParser(description=__doc__)
    razbor.add_argument("--db", default="data/spetsmat.db", help="path to the база")
    razbor.add_argument("--secrets", default="secrets", help="directory the two files go into")
    razbor.add_argument("--data", default=datetime.now(timezone.utc).strftime("%Y%m%d"),
                        help="date suffix of the plaintext list, ГГГГММДД")
    razbor.add_argument("--perezapisat", action="store_true",
                        help="mint new passwords even though files already exist")
    argumenty = razbor.parse_args()

    db_path = Path(argumenty.db).resolve()
    katalog = Path(argumenty.secrets)
    fajl_heshej = katalog / "veb-lichnye-paroli.json"
    fajl_spiska = katalog / ("paroli-prepodavatelej-%s.txt" % argumenty.data)

    for sushchestvuyushchij in (fajl_heshej, fajl_spiska):
        if sushchestvuyushchij.exists() and not argumenty.perezapisat:
            print("REFUSED: %s already exists. A second run mints NEW passwords and every "
                  "password already handed out stops working. Pass --perezapisat if that is "
                  "what you mean." % sushchestvuyushchij, file=sys.stderr)
            return 1

    lyudi = prochitat_lyudej(db_path)

    zapisi = []
    stroki = ["# personal passwords for the site, generated %s -- hand out and delete nothing else"
              % datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
              "# role organizator = senior of an auditorium (sees распределение); prepod = everyone else",
              ""]
    for chelovek in lyudi:
        parol = sgenerirovat_parol()
        sol = secrets.token_bytes(DLINA_SOLI)
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

    soderzhimoe = {
        "shema": SHEMA,
        "parametry": {"hesh": "sha256", "iteracii": ITERACII, "dklen": DKLEN},
        "sozdano": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "istochnik": str(db_path),
        "lyudi": zapisi,
    }
    zapisat_600(fajl_heshej, json.dumps(soderzhimoe, ensure_ascii=False, indent=2) + "\n")
    zapisat_600(fajl_spiska, "\n".join(stroki) + "\n")

    # Counts only.  A password printed here would land in the shell history and in the log of
    # whoever ran this, which is exactly the leak this project has already paid for once.
    print("people: %d (organizator %d, prepod %d)"
          % (len(zapisi),
             sum(1 for z in zapisi if z["rol"] == "organizator"),
             sum(1 for z in zapisi if z["rol"] == "prepod")))
    print("hashes: %s (mode %o)" % (fajl_heshej, fajl_heshej.stat().st_mode & 0o777))
    print("list:   %s (mode %o, %d lines)"
          % (fajl_spiska, fajl_spiska.stat().st_mode & 0o777,
             len(fajl_spiska.read_text(encoding="utf-8").splitlines())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
