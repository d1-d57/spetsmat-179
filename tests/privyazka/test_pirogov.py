"""THE NAMED TEST: Пирогов Константин binds to his own row, and his year is still there.

The брief names this child because the live base names him: two hundred and one marks
from last year, and a ``first_sheet_id`` of 6 rather than 1 -- he joined in the middle
of the season, which is the very rule ``ProgressService.debts`` was written around.

Before this position, «принять» on his заявка created a SECOND Пирогов with an empty
year, bound the telegram to that one, and left the two hundred and one marks on a row
nobody could reach.  Everything below is that sentence, made able to fail.
"""

from __future__ import annotations

import pytest

from conftest import PIROGOV, PIROGOV_MARKS, tg_for
from core.models import CellState

PIROGOV_TG = 7_800_001


def _marks_visible(progress, student_id, problem_ids) -> int:
    states = progress.states_for(student_id, list(problem_ids))
    return sum(1 for state in states.values() if state is not CellState.EMPTY)


def test_pirogov_binds_to_his_existing_row(
    connection, roster, full_catalogue, pirogov_marks, progress
):
    """One заявка, one binding, no new row -- and the 201 marks answer to it."""
    existing_id = pirogov_marks
    surname, name = PIROGOV
    problem_ids = full_catalogue["problem_ids"]

    assert _marks_visible(progress, existing_id, problem_ids) == PIROGOV_MARKS, (
        "the fixture did not load the year the test is about"
    )
    rows_before = connection.execute("select count(*) c from students").fetchone()["c"]

    pending = roster.submit_student(tg_id=PIROGOV_TG, surname=surname, name=name)
    match = roster.match_student(pending)
    assert match.kind == "single", (
        "«Пирогов Константин» must resolve to exactly one row; got %s with %r"
        % (match.kind, [c.student.label for c in match.candidates])
    )
    bound_id = roster.bind_student(pending, match.one.id)
    roster.accept(pending.id)

    # 🔴 The binding landed on the row that HAS the year, not next to it.
    assert bound_id == existing_id
    assert connection.execute("select count(*) c from students").fetchone()["c"] == rows_before, (
        "a second Пирогов was created -- this is the bug the position exists to close"
    )
    assert roster.student_id_for(PIROGOV_TG) == existing_id

    # 🔴 And the year is visible THROUGH the binding: what the child opens the bot and
    # sees is read from the telegram id, so that is where the count is taken from.
    seen_from_telegram = _marks_visible(
        progress, roster.student_id_for(PIROGOV_TG), problem_ids
    )
    assert seen_from_telegram == PIROGOV_MARKS, (
        "after binding the child sees %d marks instead of %d"
        % (seen_from_telegram, PIROGOV_MARKS)
    )


def test_pirogov_keeps_the_sheet_he_actually_started_on(
    connection, roster, full_catalogue, pirogov_marks
):
    """``first_sheet_id`` stays 6.  Rewriting it to today's sheet is the quiet bug.

    He appeared from sheet 6 and owes nothing older; today's sheet written over that
    anchor would erase the fact and hand him back a season of debts he never had.
    """
    surname, name = PIROGOV
    pending = roster.submit_student(tg_id=PIROGOV_TG, surname=surname, name=name)
    roster.bind_student(pending, roster.match_student(pending).one.id)
    row = connection.execute(
        "select first_sheet_id, status from students where id = ?", (pirogov_marks,)
    ).fetchone()
    assert row["first_sheet_id"] == full_catalogue["first_sheet_of_pirogov"]
    assert row["status"] == "active"


@pytest.mark.parametrize(
    "typed_surname, typed_name",
    [
        ("Пирогов", "Константин"),      # exactly as printed
        ("пирогов", "константин"),      # a phone that does not capitalise
        ("  Пирогов  ", " Константин"), # a stray space on either side
        ("Пирогов К.", "Константин"),   # copied off the sheet header, initial and all
        ("Пирогова", "Константина"),    # written in an oblique case
    ],
)
def test_pirogov_is_found_however_he_types_it(
    roster, full_catalogue, typed_surname, typed_name
):
    """Five ways a fifteen-year-old types the same name; one row at the end of each."""
    pending = roster.submit_student(
        tg_id=tg_for(hash((typed_surname, typed_name)) % 1000),
        surname=typed_surname,
        name=typed_name,
    )
    match = roster.match_student(pending)
    assert match.kind == "single", "%r %r -> %s (%r)" % (
        typed_surname, typed_name, match.kind,
        [c.student.label for c in match.candidates],
    )
    assert match.one.id == full_catalogue["student_ids"][PIROGOV]
