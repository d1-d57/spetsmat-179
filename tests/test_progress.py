"""The projections: the grid, the debts, the graveyard.

Three rules are under test here and each one was paid for by a disagreement with last
year's real conduit rather than reasoned out in the abstract:

  * DEBTS ARE COUNTED FROM ``first_sheet_id``.  Пирогов appeared at sheet 6 and has no
    older debts; a projection that counted from sheet 1 handed him five debts on his
    first day;
  * A RETRACTED CELL IS NOT A DEBT.  The student handed the problem in and did not
    defend it -- that is a different fact from never having handed it in, and only the
    second one is an outstanding obligation;
  * "TAKEN BY" MEANS CREDITED.  A hand-in that was not defended is exactly the case the
    graveyard threshold exists to notice, so it does not count towards it.
"""

from __future__ import annotations

import config
from core.models import CellState
from tests.conftest import seed_world

#: Three sheets, each with two obligatory problems, one ordinary and one starred.
THREE_SHEETS = (
    ("обязательная", "обязательная", "обычная", "звезда"),
    ("обязательная", "обязательная", "обычная", "звезда"),
    ("обязательная", "обязательная", "обычная", "звезда"),
)


# --------------------------------------------------------------------------- grid

def test_grid_shows_every_problem_including_the_untouched_ones(progress, marking, world):
    """The missing buttons are precisely the ones that still need tapping."""
    student = world.student_ids[0]
    sheet = world.sheet_ids[0]
    marking.give(student, world.problem_ids[0], source="кнопка")

    grid = progress.grid(student, sheet)

    assert grid.total == 4, "a short sheet hides the buttons that still need pressing"
    assert grid.solved == 1
    assert grid.cells[world.problem_ids[0]] is CellState.SOLVED
    assert grid.cells[world.problem_ids[3]] is CellState.EMPTY


def test_grid_counts_only_credited_cells_as_solved(progress, marking, world):
    student = world.student_ids[1]
    marking.give(student, world.problem_ids[0], source="кнопка")
    marking.give(student, world.problem_ids[1], source="кнопка")
    marking.retract(student, world.problem_ids[1], source="кнопка")

    grid = progress.grid(student, world.sheet_ids[0])
    assert grid.solved == 1
    assert grid.cells[world.problem_ids[1]] is CellState.RETRACTED


# -------------------------------------------------------------------------- debts

def test_debts_are_counted_from_the_students_first_sheet(connection, journal, catalogue):
    """The Пирогов rule: whoever arrived at sheet 3 does not owe sheets 1-2."""
    from core.services.progress import ProgressService

    world = seed_world(connection, students=2, sheets=THREE_SHEETS,
                       first_sheet_of={1: 2})
    progress = ProgressService(journal, catalogue)
    from_the_start, latecomer = world.student_ids

    # Current sheet is the third; debts come from the sheets strictly older than it.
    assert len(progress.debts(from_the_start, current_sheet_ord=3)) == 4, (
        "two sheets x two obligatory problems, none of them solved"
    )
    assert progress.debts(latecomer, current_sheet_ord=3) == [], (
        "a student who arrived at sheet 3 owes nothing older"
    )


def test_only_obligatory_problems_become_debts(connection, journal, catalogue):
    """A starred problem is an invitation, not an obligation."""
    from core.services.progress import ProgressService

    world = seed_world(connection, students=1, sheets=THREE_SHEETS)
    progress = ProgressService(journal, catalogue)
    debts = progress.debts(world.student_ids[0], current_sheet_ord=3)

    assert all(problem.is_obligatory for problem in debts)
    assert all(problem.kind in config.OBLIGATORY_KINDS for problem in debts)


def test_a_solved_problem_is_not_a_debt(connection, journal, catalogue, clock):
    from core.services.marking import MarkingService
    from core.services.progress import ProgressService

    world = seed_world(connection, students=1, sheets=THREE_SHEETS)
    marking = MarkingService(journal, clock)
    progress = ProgressService(journal, catalogue)
    student = world.student_ids[0]
    first_sheet = world.sheet_ids[0]
    marking.give(student, world.problems_by_sheet[first_sheet][0], source="кнопка")

    debts = progress.debts(student, current_sheet_ord=3)
    assert len(debts) == 3
    assert world.problems_by_sheet[first_sheet][0] not in [p.id for p in debts]


def test_a_retracted_problem_is_not_a_debt_and_an_erratum_one_is(
    connection, journal, catalogue, clock
):
    """The fork, seen from the debts side.

    RETRACTED: handed in, not defended -- not outstanding.
    EMPTY after an erratum: the record should never have existed, so the obligation is
    back exactly where it was.
    """
    from core.services.marking import MarkingService
    from core.services.progress import ProgressService

    world = seed_world(connection, students=1, sheets=THREE_SHEETS)
    marking = MarkingService(journal, clock)
    progress = ProgressService(journal, catalogue)
    student = world.student_ids[0]
    first_sheet = world.sheet_ids[0]
    handed_in, mistyped = world.problems_by_sheet[first_sheet][:2]

    marking.give(student, handed_in, source="кнопка")
    marking.retract(student, handed_in, source="кнопка")
    marking.give(student, mistyped, source="кнопка")
    marking.erratum(student, mistyped, source="кнопка")

    debt_ids = [problem.id for problem in progress.debts(student, current_sheet_ord=3)]
    assert handed_in not in debt_ids, "a hand-in that was not defended is not a debt"
    assert mistyped in debt_ids, "an erratum puts the obligation back"


def test_the_current_sheet_is_not_yet_a_debt(connection, journal, catalogue):
    """Debts are OLDER sheets: the sheet being worked on today is not overdue."""
    from core.services.progress import ProgressService

    world = seed_world(connection, students=1, sheets=THREE_SHEETS)
    progress = ProgressService(journal, catalogue)
    debts = progress.debts(world.student_ids[0], current_sheet_ord=1)
    assert debts == []


# ---------------------------------------------------------------------- graveyard

def test_graveyard_counts_credited_cells_only(progress, marking, world):
    """A retracted hand-in is exactly what the threshold is meant to notice."""
    problem = world.problem_ids[0]
    for student in world.student_ids[:3]:
        marking.give(student, problem, source="кнопка")
    marking.retract(world.student_ids[2], problem, source="кнопка")

    row = next(row for row in progress.graveyard(world.sheet_ids[0])
               if row.problem.id == problem)
    assert row.taken_by == 2
    assert row.is_graveyard is True, "two takers is below the threshold of three"


def test_graveyard_threshold_is_read_from_config(progress, marking, world):
    """✓ at >= 3, ✘ at <= 2 -- and the number lives in ``config.py``, nowhere else."""
    problem = world.problem_ids[1]
    for student in world.student_ids[:config.GRAVEYARD_THRESHOLD]:
        marking.give(student, problem, source="кнопка")

    row = next(row for row in progress.graveyard(world.sheet_ids[0])
               if row.problem.id == problem)
    assert row.taken_by == config.GRAVEYARD_THRESHOLD
    assert row.is_graveyard is False
    assert progress.graveyard_threshold() == config.GRAVEYARD_THRESHOLD


def test_an_untouched_problem_is_a_graveyard_with_zero_takers(progress, world):
    rows = progress.graveyard(world.sheet_ids[0])
    assert len(rows) == 4
    assert all(row.taken_by == 0 and row.is_graveyard for row in rows)
