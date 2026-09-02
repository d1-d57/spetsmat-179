"""Test 1 of the five: re-marking the same target state twice does not double-write.

Idempotency here has TWO independent halves and both are needed:

  * semantic -- the cell is already in the target state, so there is nothing to write.
    This is the half that survives a caller with no key to pass, and it is what makes a
    double tap harmless: the button carries the TARGET STATE, never a "toggle";
  * transport -- Telegram delivers at least once, so the same tap can arrive twice as
    two different-looking requests.  The caller passes a key derived from the update and
    the redelivery is answered from the journal.

Only the second half has a carrier in the schema (the partial unique index on
``idempotency_key``); the first is a service rule, so it is tested through the service.
"""

from __future__ import annotations

import sqlite3

import pytest

from core.models import CellState


def journal_length(connection) -> int:
    return connection.execute("select count(*) from marks").fetchone()[0]


def test_same_target_state_twice_writes_one_event(connection, marking, world):
    student = world.student_ids[0]
    problem = world.problem_ids[0]

    first = marking.give(student, problem, source="кнопка")
    second = marking.give(student, problem, source="кнопка")

    assert first.written is True
    assert second.written is False, second.reason
    assert second.state is CellState.SOLVED
    assert journal_length(connection) == 1


def test_repeated_taps_do_not_grow_the_journal(connection, marking, world):
    """Five taps on a button already in its target state stay one row."""
    student = world.student_ids[1]
    problem = world.problem_ids[2]

    for _ in range(5):
        marking.set_state(student, problem, CellState.SOLVED, source="кнопка")

    assert journal_length(connection) == 1


def test_redelivered_update_is_answered_from_the_journal(connection, marking, world):
    """The transport half: the same key twice returns the first mark, unchanged."""
    student = world.student_ids[2]
    problem = world.problem_ids[1]
    key = "update:4815162342"

    first = marking.give(student, problem, source="кнопка", idempotency_key=key)
    second = marking.give(student, problem, source="кнопка", idempotency_key=key)

    assert first.written is True
    assert second.written is False, second.reason
    assert second.mark is not None and second.mark.id == first.mark.id
    assert journal_length(connection) == 1


def test_idempotency_key_is_unique_in_the_schema(connection, marking, world):
    """The carrier, tested directly: the index refuses a duplicate key from any client.

    The service never reaches this line -- it looks the key up first.  The index is what
    protects the journal from an importer or a psql-style session that does not.
    """
    student = world.student_ids[0]
    other_student = world.student_ids[1]
    problem = world.problem_ids[0]
    marking.give(student, problem, source="кнопка", idempotency_key="update:1")

    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "insert into marks (student_id, problem_id, event, valid_at, recorded_at, "
            "source, idempotency_key) values (?, ?, 'assert', ?, ?, 'кнопка', 'update:1')",
            (other_student, problem, "2026-09-02T09:00:00Z", "2026-09-02T09:00:00Z"),
        )


def test_null_idempotency_keys_may_repeat(connection, marking, world):
    """A partial index, not a plain one: marks without a key are the normal case."""
    student = world.student_ids[3]
    marking.give(student, world.problem_ids[0], source="кнопка")
    marking.give(student, world.problem_ids[1], source="кнопка")

    assert journal_length(connection) == 2
    assert connection.execute(
        "select count(*) from marks where idempotency_key is null"
    ).fetchone()[0] == 2
