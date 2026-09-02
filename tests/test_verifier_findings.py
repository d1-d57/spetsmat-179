"""Regression tests for the seven defects the §3 verifier found.

The verifier ran an INDEPENDENT differential (800 pairs, 0 mismatches) and attacked the
schema fourteen ways (all fourteen raised), so the journal, the fold semantics and the
migration came back clean.  Every defect it found was in the marking SERVICE, and every
one of them was invisible to the differential for the same reason: the projection stayed
self-consistent with the journal in each case: the journal simply had a row it should not
have had, or the service returned an answer that was true a moment ago.

That is precisely why a differential is not sufficient on its own, and why each finding
gets a test here that fails on the old behaviour.
"""

from __future__ import annotations

import sqlite3
import threading

import pytest

import config
from core.models import CellState
from core.services.marking import (
    IdempotencyKeyReused,
    MarkingService,
    NothingToReverse,
)
from core.services.progress import ProgressService
from infra.db import connect
from infra.repositories import SqliteCatalogue, SqliteMarkJournal
from tests.conftest import FrozenClock, seed_world


def journal_length(connection) -> int:
    return connection.execute("select count(*) from marks").fetchone()[0]


# ---------------------------------------------------------------------- finding 1

def test_a_plain_string_target_is_refused_at_the_door(connection, marking, world):
    """``CellState`` is a ``str`` Enum, so "solved" would have sailed past the lookup.

    It then failed the identity test against the current state -- a raw string is never
    the same OBJECT as an enum member -- and every repeated tap wrote another event.  The
    verifier measured it: two ``assert`` rows on one already-solved cell.  This is the
    exact path a caller takes when it parses a target out of a button payload.
    """
    student, problem = world.student_ids[0], world.problem_ids[0]
    marking.give(student, problem, source="кнопка")

    with pytest.raises(Exception) as raised:
        marking.set_state(student, problem, "solved", source="кнопка")
    assert "CellState" in str(raised.value)
    assert journal_length(connection) == 1, "a string target double-wrote the journal"


def test_repeating_a_proper_target_state_still_does_not_write(connection, marking, world):
    """The type check must not have broken the idempotency it was protecting."""
    student, problem = world.student_ids[0], world.problem_ids[1]
    marking.set_state(student, problem, CellState.SOLVED, source="кнопка")
    outcome = marking.set_state(student, problem, CellState.SOLVED, source="кнопка")

    assert outcome.written is False
    assert journal_length(connection) == 1


# ---------------------------------------------------------------------- finding 2

def test_retracting_a_struck_out_cell_is_refused(connection, marking, world):
    """"Nothing to reverse" means nothing STANDING, not merely no row in the journal.

    assert -> erratum leaves the cell EMPTY.  Retracting it used to succeed, because the
    guard asked "is there a row?" instead of "is anything standing?" -- and the result was
    a record that "should never have existed" re-entering the statistics as "handed in,
    not credited".
    """
    student, problem = world.student_ids[1], world.problem_ids[0]
    marking.give(student, problem, source="кнопка")
    marking.erratum(student, problem, source="кнопка")

    with pytest.raises(NothingToReverse):
        marking.retract(student, problem, source="кнопка")
    assert journal_length(connection) == 2, "the refused retract must not have been written"


def test_retracting_a_standing_assert_still_works(marking, world):
    """The guard tightened; it must not have closed the legitimate path."""
    student, problem = world.student_ids[1], world.problem_ids[1]
    marking.give(student, problem, source="кнопка")
    outcome = marking.retract(student, problem, source="кнопка")
    assert outcome.written is True
    assert outcome.state is CellState.RETRACTED


# ---------------------------------------------------------------------- finding 3

def test_one_key_cannot_answer_for_another_cell(connection, marking, world):
    """The key is unique across the whole journal, so it must be checked against the cell.

    Before: a key written for (3,1) swallowed a request for (3,2) -- ``written=False``, no
    write, no error, and the cell stayed EMPTY.  The quietest possible failure: a button
    that does nothing.
    """
    student = world.student_ids[2]
    first, second = world.problem_ids[0], world.problem_ids[1]
    marking.give(student, first, source="кнопка", idempotency_key="update:77")

    with pytest.raises(IdempotencyKeyReused):
        marking.give(student, second, source="кнопка", idempotency_key="update:77")

    assert connection.execute(
        "select count(*) from marks where problem_id = ?", (second,)
    ).fetchone()[0] == 0


# ---------------------------------------------------------------------- finding 4

def test_a_replay_reports_the_cell_as_it_stands_now(marking, world):
    """A redelivered update must not make the bot redraw a button that is no longer true.

    Before: the replay returned the state at the moment the key was written.  Mark, then
    retract, then let the original update arrive again -- it answered SOLVED while the
    cell actually stood at RETRACTED.
    """
    student, problem = world.student_ids[3], world.problem_ids[0]
    marking.give(student, problem, source="кнопка", idempotency_key="update:88")
    marking.retract(student, problem, source="кнопка")

    replay = marking.give(student, problem, source="кнопка", idempotency_key="update:88")

    assert replay.written is False
    assert replay.state is CellState.RETRACTED, "the replay reported a stale state"


# ------------------------------------------------------------------ findings 5 & 6

def _tap(db_path, student_id, problem_id, target, barrier, results, errors):
    """One teacher's tap, on its own connection, released with the others."""
    connection = connect(db_path)
    try:
        service = MarkingService(SqliteMarkJournal(connection), FrozenClock())
        barrier.wait(timeout=10)
        results.append(service.set_state(student_id, problem_id, target, source="кнопка"))
    except BaseException as error:  # collected, then asserted on in the test thread
        errors.append(error)
    finally:
        connection.close()


def _run_concurrently(db_path, student_id, problem_id, target, workers=8):
    barrier = threading.Barrier(workers)
    results, errors = [], []
    threads = [
        threading.Thread(
            target=_tap,
            args=(db_path, student_id, problem_id, target, barrier, results, errors),
        )
        for _ in range(workers)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    return results, errors


def test_eight_simultaneous_taps_write_one_row(db_path, connection, world):
    """The claim at the top of ``marking.py``, made true.

    ``set_state`` decides what to write by reading what stands.  Without a transaction
    around the pair, two taps both read EMPTY and both write an ``assert``: the projected
    state is still SOLVED, so the differential cannot see it, but the journal has two rows
    where the service promises one.  ``begin immediate`` turns the race into a queue.
    """
    student, problem = world.student_ids[0], world.problem_ids[2]
    results, errors = _run_concurrently(db_path, student, problem, CellState.SOLVED)

    assert errors == [], "a tap failed: %r" % (errors[:1],)
    assert journal_length(connection) == 1, (
        "%d rows for one cell: the read-then-write interleaved" % journal_length(connection)
    )
    assert sum(1 for outcome in results if outcome.written) == 1
    assert all(outcome.state is CellState.SOLVED for outcome in results)


def test_a_concurrent_reversal_does_not_leak_a_store_exception(db_path, connection, marking, world):
    """``core/`` must not hand its caller a ``sqlite3`` exception to catch.

    Two simultaneous retracts of one assert used to reach the schema together, where
    ``unique(reverses_id)`` correctly refused the second -- but the raw IntegrityError
    then crossed the port boundary that ``core/ports.py`` exists to seal.  Serialised, the
    loser re-reads inside its own transaction, finds the cell already RETRACTED, and
    answers idempotently.
    """
    student, problem = world.student_ids[1], world.problem_ids[2]
    marking.give(student, problem, source="кнопка")

    results, errors = _run_concurrently(db_path, student, problem, CellState.RETRACTED)

    assert not any(isinstance(error, sqlite3.Error) for error in errors), (
        "a store exception crossed the port boundary: %r" % (errors[:1],)
    )
    assert errors == [], "unexpected failure: %r" % (errors[:1],)
    assert journal_length(connection) == 2, "one assert and exactly one retract"
    assert sum(1 for outcome in results if outcome.written) == 1


# ---------------------------------------------------------------------- finding 7

def test_a_student_with_no_first_sheet_owes_from_the_very_first_sheet(
    connection, journal, catalogue
):
    """Pinned, not fixed -- and named in ``## ВОПРОСЫ`` because it is the owner's call.

    ``_first_sheet_ord`` falls back to the earliest sheet when ``first_sheet_id`` is NULL,
    so a student who never attended shows every obligatory problem as owed.  For last
    year's imported rows that fallback is right (they predate the field).  For a freshly
    registered ``pending`` student it is the opposite of the Пирогов rule this very field
    exists to serve.  P2 decides which case is real when it fills ``first_sheet_id`` on
    import; until then the behaviour is at least no longer accidental.
    """
    world = seed_world(
        connection,
        students=1,
        sheets=(("обязательная", "обычная"), ("обязательная", "обычная")),
    )
    connection.execute(
        "update students set first_sheet_id = null, status = 'pending' where id = ?",
        (world.student_ids[0],),
    )
    progress = ProgressService(journal, catalogue)

    debts = progress.debts(world.student_ids[0], current_sheet_ord=2)
    assert [problem.kind for problem in debts] == ["обязательная"], (
        "the documented fallback changed: a student with no first sheet owes from sheet 1"
    )
    assert all(kind in config.OBLIGATORY_KINDS for kind in [p.kind for p in debts])
