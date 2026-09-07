"""``ops/vygruzka_v_tablicu.py``: the one non-obvious judgment call this tool makes.

Everything about *how* a cell becomes a sign is already proven by ``tests/export`` --
this tool goes through the same ``SIGN`` and the same ``ProgressService`` on purpose, so
re-proving that here would be a second, redundant opinion. What is NOT already proven
anywhere is the one thing this tool adds on top of ``tools/export_xlsx.py``: that only
THIS academic year's sheets go to the table, and exactly where that boundary falls.
"""

from __future__ import annotations

from datetime import date

from core.models import CellState
from ops.vygruzka_v_tablicu import SIGN, academic_year_start, build_sheet_rows


# --------------------------------------------------------------- the academic-year cutoff


def test_the_cutoff_is_this_september_from_september_onward():
    assert academic_year_start(date(2026, 9, 1)) == "2026-09-01"
    assert academic_year_start(date(2026, 12, 20)) == "2026-09-01"


def test_the_cutoff_stays_at_last_september_before_that():
    assert academic_year_start(date(2026, 8, 31)) == "2025-09-01"
    assert academic_year_start(date(2027, 1, 5)) == "2026-09-01"


# ------------------------------------------------------------- what actually reaches a sheet


def test_a_sheet_from_a_year_ago_is_left_out(connection, world):
    """``world`` seeds its one sheet at 2026-09-01 (see ``seed_world`` in
    ``tests/conftest.py``).  Backdating it by a year here, directly through SQL, is the
    same technique the ``tests/export`` fixtures use to control a field the seeding
    helper does not expose a parameter for."""
    connection.execute(
        "update sheets set issued_at = '2025-06-01' where id = ?",
        (world.sheet_ids[0],),
    )
    connection.commit()

    grids = build_sheet_rows(connection)
    assert grids == {}, "a sheet issued before this academic year must not reach the table"


def test_a_current_sheet_carries_the_stamp_and_the_right_signs(connection, marking, world):
    students = world.student_ids
    problems = world.problems_by_sheet[world.sheet_ids[0]]
    marking.set_state(students[0], problems[0], CellState.SOLVED, source="кнопка")
    marking.set_state(students[1], problems[1], CellState.SOLVED, source="кнопка")
    marking.set_state(students[1], problems[1], CellState.RETRACTED, source="кнопка")

    grids = build_sheet_rows(connection)
    assert len(grids) == 1, "the one seeded sheet is issued this academic year"
    rows = next(iter(grids.values()))

    assert rows[0][0].startswith("обновлено: "), "A1 must carry the update stamp"
    header, data_rows = rows[1], rows[2:]
    assert len(data_rows) == len(students)

    by_row = {row[0].split(" ")[0]: row for row in data_rows}
    # student 0's first problem is SOLVED, student 1's second is RETRACTED (asserted then
    # taken back) -- the two non-empty signs this fixture actually produces.
    assert by_row["surname-0"][1] == SIGN[CellState.SOLVED]
    assert by_row["surname-1"][2] == SIGN[CellState.RETRACTED]
