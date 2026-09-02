"""Test 4 of the five: reversing an event returns the cell to EMPTY, not to what was there.

THIS IS A REAL FORK and it is the reason the semantics are written down in three places
(``core/models.py``, ``core/services/progress.py``, ``migrations/001_init.sql``): an
assistant reading this project in six months would otherwise define it however it likes
that day, and both readings are defensible in the abstract.

The reading this project commits to: the state of a cell is the LAST event, full stop.
The projection NEVER looks past it.  So a cell that went assert -> retract -> erratum
lands on EMPTY, not back on SOLVED, even though a SOLVED did stand there once.

The alternative reading -- "undo restores the previous state" -- is rejected because it
makes the state of a cell depend on the whole history rather than on its last row, and
because putting a plus back has a cheaper spelling that already exists: tap the target
state again and a fresh ``assert`` is written.  That is safe precisely because a button
carries the target state and never a "toggle".
"""

from __future__ import annotations

import pytest

from core.models import CellState, MarkEvent
from core.services.marking import NothingToReverse


def state_of(progress, student_id, problem_id) -> CellState:
    return progress.states_for(student_id, [problem_id])[problem_id]


def test_erratum_of_an_assert_lands_on_empty(marking, progress, world):
    student, problem = world.student_ids[0], world.problem_ids[0]
    marking.give(student, problem, source="кнопка")
    marking.erratum(student, problem, source="кнопка")

    assert state_of(progress, student, problem) is CellState.EMPTY


def test_erratum_of_a_retract_lands_on_empty_not_back_on_solved(marking, progress, world):
    """The fork itself, spelled out as an assertion.

    assert -> retract -> erratum.  A SOLVED did stand in this cell, and the cell is still
    EMPTY afterwards: the projection does not walk back to it.
    """
    student, problem = world.student_ids[1], world.problem_ids[0]
    marking.give(student, problem, source="кнопка")
    marking.retract(student, problem, source="кнопка")
    marking.erratum(student, problem, source="кнопка")

    assert state_of(progress, student, problem) is CellState.EMPTY
    assert state_of(progress, student, problem) is not CellState.SOLVED


def test_retract_lands_on_retracted_and_not_on_empty(marking, progress, world):
    """The other half of the fork: a retract is not an undo, it is its own state."""
    student, problem = world.student_ids[2], world.problem_ids[0]
    marking.give(student, problem, source="кнопка")
    marking.retract(student, problem, source="кнопка")

    assert state_of(progress, student, problem) is CellState.RETRACTED


def test_putting_the_plus_back_writes_a_fresh_assert(connection, marking, progress, world):
    """The cheap spelling of "undo the undo": tap the target state again."""
    student, problem = world.student_ids[3], world.problem_ids[0]
    marking.give(student, problem, source="кнопка")
    marking.erratum(student, problem, source="кнопка")
    again = marking.give(student, problem, source="кнопка")

    assert again.written is True
    assert again.mark.event is MarkEvent.ASSERT
    assert again.mark.reverses_id is None, "an assert reverses nothing"
    assert state_of(progress, student, problem) is CellState.SOLVED
    assert connection.execute("select count(*) from marks").fetchone()[0] == 3


def test_a_reversal_never_shortens_the_journal(connection, marking, world):
    """Four operations on one cell leave four rows, whatever the states did."""
    student, problem = world.student_ids[4], world.problem_ids[0]
    marking.give(student, problem, source="кнопка")
    marking.retract(student, problem, source="кнопка")
    marking.erratum(student, problem, source="кнопка")
    marking.give(student, problem, source="кнопка")

    assert connection.execute("select count(*) from marks").fetchone()[0] == 4


def test_retract_of_an_untouched_cell_is_refused(marking, world):
    """There is no event to name in ``reverses_id``, so the caller is wrong, not the cell."""
    with pytest.raises(NothingToReverse):
        marking.retract(world.student_ids[0], world.problem_ids[3], source="кнопка")
