"""Test 2 of the five: retract and erratum both make the journal LONGER, never shorter.

The two are different facts about the world, and a single ``deleted`` flag destroys the
difference:

  * ``retract`` -- the mark was there and was taken away; the student handed the problem
    in and did not defend it.  It COUNTS in statistics, as "handed in, not credited";
  * ``erratum`` -- the record should never have existed (wrong button).  It is struck out
    of statistics entirely and stays visible in the journal.

Also here: the two times.  ``valid_at`` is when the check-off happened and ``recorded_at``
is when it reached the database, and a mark entered a day late has to stay distinguishable
from one entered on the spot.
"""

from __future__ import annotations

import sqlite3

import pytest

from core.models import CellState, MarkEvent


def journal_length(connection) -> int:
    return connection.execute("select count(*) from marks").fetchone()[0]


def test_retract_appends_and_names_what_it_reverses(connection, marking, world):
    student, problem = world.student_ids[0], world.problem_ids[0]
    given = marking.give(student, problem, source="кнопка")
    taken = marking.retract(student, problem, source="кнопка")

    assert journal_length(connection) == 2, "a retract must lengthen the journal"
    assert taken.mark.event is MarkEvent.RETRACT
    assert taken.mark.reverses_id == given.mark.id
    assert taken.state is CellState.RETRACTED


def test_erratum_appends_and_names_what_it_strikes(connection, marking, world):
    student, problem = world.student_ids[0], world.problem_ids[1]
    given = marking.give(student, problem, source="кнопка")
    struck = marking.erratum(student, problem, source="кнопка")

    assert journal_length(connection) == 2, "an erratum must lengthen the journal"
    assert struck.mark.event is MarkEvent.ERRATUM
    assert struck.mark.reverses_id == given.mark.id
    assert struck.state is CellState.EMPTY


def test_erratum_leaves_statistics_and_retract_does_not(marking, world):
    """The whole reason there are three event kinds and not two."""
    student = world.student_ids[1]
    retracted, struck = world.problem_ids[0], world.problem_ids[1]

    marking.give(student, retracted, source="кнопка")
    marking.retract(student, retracted, source="кнопка")
    marking.give(student, struck, source="кнопка")
    marking.erratum(student, struck, source="кнопка")

    assert CellState.RETRACTED.counts_in_statistics is True
    assert CellState.RETRACTED.is_credited is False
    assert CellState.EMPTY.counts_in_statistics is False


def test_the_struck_event_stays_visible_in_the_journal(journal, marking, world):
    """Struck out of statistics is not struck out of the record."""
    student, problem = world.student_ids[2], world.problem_ids[0]
    given = marking.give(student, problem, source="кнопка")
    marking.erratum(student, problem, source="кнопка")

    events = journal.events(student_ids=[student], problem_ids=[problem])
    assert [event.event for event in events] == [MarkEvent.ASSERT, MarkEvent.ERRATUM]
    assert events[0].id == given.mark.id


def test_two_times_are_stored_separately(connection, marking, clock, world):
    """A mark entered a day late keeps the day it happened and the day it arrived."""
    student, problem = world.student_ids[3], world.problem_ids[0]
    clock.tick(60 * 60 * 24)  # the teacher enters yesterday's check-off today

    outcome = marking.give(
        student, problem, source="кнопка", valid_at="2026-09-02T08:00:00Z"
    )

    assert outcome.mark.valid_at == "2026-09-02T08:00:00Z"
    assert outcome.mark.recorded_at == "2026-09-03T08:00:00Z"
    assert outcome.mark.valid_at != outcome.mark.recorded_at


def test_valid_at_defaults_to_the_moment_of_recording(marking, world):
    """No time given means the check-off is happening now -- the common case."""
    outcome = marking.give(world.student_ids[4], world.problem_ids[0], source="кнопка")
    assert outcome.mark.valid_at == outcome.mark.recorded_at


def test_reversing_event_without_a_target_is_refused_by_the_schema(connection, world):
    """The carrier: a retract with a null ``reverses_id`` cannot be inserted at all."""
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "insert into marks (student_id, problem_id, event, valid_at, recorded_at, source) "
            "values (?, ?, 'retract', ?, ?, 'кнопка')",
            (world.student_ids[0], world.problem_ids[0],
             "2026-09-02T09:00:00Z", "2026-09-02T09:00:00Z"),
        )


def test_reverses_id_must_point_at_the_same_cell(connection, marking, world):
    """A foreign key says "some mark"; only the trigger says "a mark about THIS cell".

    Without it a mistyped id quietly reverses somebody else's plus.
    """
    mine = marking.give(world.student_ids[0], world.problem_ids[0], source="кнопка")

    with pytest.raises(sqlite3.IntegrityError, match="same"):
        connection.execute(
            "insert into marks (student_id, problem_id, event, reverses_id, valid_at, "
            "recorded_at, source) values (?, ?, 'retract', ?, ?, ?, 'кнопка')",
            (world.student_ids[1], world.problem_ids[0], mine.mark.id,
             "2026-09-02T09:00:00Z", "2026-09-02T09:00:00Z"),
        )


def test_an_event_is_reversed_at_most_once(connection, marking, world):
    """Two retracts of one assert are two stories about the same fact."""
    given = marking.give(world.student_ids[0], world.problem_ids[2], source="кнопка")
    marking.retract(world.student_ids[0], world.problem_ids[2], source="кнопка")

    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "insert into marks (student_id, problem_id, event, reverses_id, valid_at, "
            "recorded_at, source) values (?, ?, 'erratum', ?, ?, ?, 'кнопка')",
            (world.student_ids[0], world.problem_ids[2], given.mark.id,
             "2026-09-02T09:00:00Z", "2026-09-02T09:00:00Z"),
        )
