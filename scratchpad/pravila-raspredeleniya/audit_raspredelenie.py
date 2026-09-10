#!/usr/bin/env python3
"""One-shot readiness check for the pravila-raspredeleniya заход: the ceiling and the
day-attendance rule, read straight off the live database -- read-only, no writes.

Prints, per readiness criterion 1 and 5:
  "нарушений потолка X, назначений в день неприхода Y, проверено N пар из M"
N is counted from the live ``teachers`` table times the two lesson slots, not typed in.

WHAT THIS DOES NOT CHECK (criterion 5): a manual edit of ``enrollment`` made outside the
form and outside ``prepodavatel_ne_prihodit`` — this script and the new domain checks both
read the same two tables the form writes, so a change made straight in SQLite by hand,
bypassing both, is invisible to either.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from infra.db import connect
from infra.prepodavatel_den_repo import dni

SLOTS = (1, 2)  # 1 = понедельник, 2 = четверг (migration 003)
OPEN_END_DATE = "9999-12-31"


def main() -> int:
    conn = connect()
    # Active only, matching the form's own "по преподавателям" roster (``_all_teachers``
    # in ``veb/server.py``) -- a deactivated teacher keeps last year's history in
    # ``enrollment`` and would otherwise inflate both counts with a person the form
    # itself no longer offers.
    teachers = {
        row["id"]: row["name"]
        for row in conn.execute(
            "select id, name from teachers where aktiven is null or aktiven = 1"
        )
    }
    attends = dni(conn)

    ceiling_violations = 0
    day_violations = 0
    pairs = 0
    for teacher_id, name in sorted(teachers.items(), key=lambda kv: kv[1]):
        for slot in SLOTS:
            pairs += 1
            count = conn.execute(
                "select count(*) from enrollment "
                "where teacher_id = ? and slot = ? and valid_to = ?",
                (teacher_id, slot, OPEN_END_DATE),
            ).fetchone()[0]
            if count > 5:
                ceiling_violations += 1
                print(f"  потолок: {name} (id {teacher_id}) несёт {count} в слоте {slot}")
            if count > 0 and slot not in attends.get(teacher_id, ()):
                day_violations += 1
                print(
                    f"  день-запрет: {name} (id {teacher_id}) не приходит в слот {slot}, "
                    f"но у него {count} школьник(ов)"
                )

    total_pairs = len(teachers) * len(SLOTS)
    print(
        f"нарушений потолка {ceiling_violations}, "
        f"назначений в день неприхода {day_violations}, "
        f"проверено {pairs} пар из {total_pairs}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
