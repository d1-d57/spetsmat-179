"""Test 3 of the five: append-only is carried BY THE SCHEMA, not by convention.

The service layer offers no update and no delete, but a rule held only by the service
layer is a hope: an importer, a migration, or a person with ``sqlite3`` open on the
production file goes straight past it.  So these tests hit the TABLE directly and expect
the trigger to raise -- the service is not the carrier and is deliberately not used here.
"""

from __future__ import annotations

import sqlite3

import pytest


@pytest.fixture
def one_mark(connection, marking, world):
    """A single ``assert`` standing in the journal, for the raw SQL below to attack."""
    outcome = marking.give(world.student_ids[0], world.problem_ids[0], source="кнопка")
    return outcome.mark


def test_direct_update_raises(connection, one_mark):
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        connection.execute(
            "update marks set event = 'erratum' where id = ?", (one_mark.id,)
        )


def test_direct_delete_raises(connection, one_mark):
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        connection.execute("delete from marks where id = ?", (one_mark.id,))


def test_a_blanket_delete_raises_too(connection, one_mark):
    """``delete from marks`` with no WHERE is the shape a panicking operator types."""
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        connection.execute("delete from marks")


def test_the_row_survives_both_attempts_unchanged(connection, one_mark):
    """A trigger that raised but let the write through would be worse than none."""
    for statement, params in (
        ("update marks set note = 'tampered' where id = ?", (one_mark.id,)),
        ("delete from marks where id = ?", (one_mark.id,)),
    ):
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(statement, params)

    row = connection.execute(
        "select event, note from marks where id = ?", (one_mark.id,)
    ).fetchone()
    assert row is not None, "the row was deleted despite the trigger"
    assert row["event"] == "assert"
    assert row["note"] is None


def test_append_still_works(connection, marking, world, one_mark):
    """Append-only forbids exactly two verbs and must not have forbidden the third."""
    marking.retract(world.student_ids[0], world.problem_ids[0], source="кнопка")
    assert connection.execute("select count(*) from marks").fetchone()[0] == 2
