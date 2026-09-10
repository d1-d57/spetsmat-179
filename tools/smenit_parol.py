#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-human — the owner runs it when somebody asks for their password to
# be changed and the browser form is not yet there (`veb/server.py`, outside this заход's zone).
"""Change one person's personal password to one they chose, from the terminal.

WHY THIS EXISTS AND WHAT IT IS NOT.  The mechanism belongs to
`core/services/lichnye_paroli.py`; this file is its live call point, and the reason it is a
call point at all is that the browser half — a form on the pupil's own page — needs a route in
`veb/server.py`, which заход `paroli-shkolnikov` was not given.  Until that route exists, this
is how a changed password gets into the system, and it is the same code path the form will use.

🔴 THE PASSWORDS ARE NEVER ARGUMENTS.  Both are read from a terminal prompt with echo off
(`getpass`).  A password on a command line lands in the shell history, in `ps` output for
every user on the machine, and in the log of whoever ran it — the leak this project has
already paid for once.  There is deliberately no flag to pass one.

USAGE
    python3 tools/smenit_parol.py --rol shkolnik --uid 17
    python3 tools/smenit_parol.py --rol prepod   --uid 4

`--uid` is `students.id` under `--rol shkolnik` and `teachers.id` under the two staff roles.
They are different tables and id 3 is a person in both; `--rol` is what tells them apart, and
this script refuses to guess.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

KOREN = Path(__file__).resolve().parent.parent
if str(KOREN) not in sys.path:
    sys.path.insert(0, str(KOREN))

from core.services.lichnye_paroli import OtkazSmeny, fajl_smenennyh, smenit, smenil_li  # noqa: E402


def main() -> int:
    razbor = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    razbor.add_argument("--rol", required=True, choices=("shkolnik", "prepod", "organizator"),
                        help="which table --uid names: shkolnik -> students, else teachers")
    razbor.add_argument("--uid", required=True, type=int, help="the person's id in that table")
    argumenty = razbor.parse_args()

    if not sys.stdin.isatty():
        print("REFUSED: this script reads both passwords from the terminal with echo off and "
              "has no flag to pass one. Run it interactively.", file=sys.stderr)
        return 1

    staryj = getpass.getpass("текущий пароль: ")
    novyj = getpass.getpass("новый пароль: ")
    povtor = getpass.getpass("новый пароль ещё раз: ")
    if novyj != povtor:
        print("REFUSED: два ввода нового пароля не совпали", file=sys.stderr)
        return 1

    try:
        smenit(argumenty.rol, argumenty.uid, staryj, novyj)
    except OtkazSmeny as otkaz:
        # The reason names what was wrong, never what was typed.
        print("REFUSED: %s" % otkaz, file=sys.stderr)
        return 1

    put = fajl_smenennyh()
    print("changed: %s uid %d" % (argumenty.rol, argumenty.uid))
    print("file:    %s (mode %o)" % (put, put.stat().st_mode & 0o777))
    print("in file: %s" % smenil_li(argumenty.rol, argumenty.uid))
    print("the previous password for this person no longer works.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
