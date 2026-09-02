"""``config.py`` and ``migrations/001_init.sql`` list the same enumerations twice.

That duplication is deliberate: the SQL ``CHECK`` is the CARRIER (the database refuses a
bad value even if every line of Python is rewritten), and the Python tuple is what the
code reads.  Two copies of one truth drift, so this file is the thing that goes red when
they do -- it reads the enumerations back out of the LIVE schema, not out of the file on
disk, so a migration that was edited but never applied does not fool it.

Both ``config.py`` and ``migrations/001_init.sql`` point at this test by name.
"""

from __future__ import annotations

import re
import sqlite3

import pytest

import config

#: table, column, and the tuple in ``config.py`` that must match its CHECK list.
ENUMERATIONS = [
    ("students", "status", config.STUDENT_STATUSES),
    ("problems", "kind", config.PROBLEM_KINDS),
    ("sessions", "kind", config.SESSION_KINDS),
    ("marks", "event", config.MARK_EVENTS),
    ("marks", "source", config.MARK_SOURCES),
    ("attendance", "status", config.ATTENDANCE_STATUSES),
]


def table_sql(connection, table: str) -> str:
    row = connection.execute(
        "select sql from sqlite_master where type = 'table' and name = ?", (table,)
    ).fetchone()
    assert row is not None, "table %r is not in the migrated schema" % table
    return row["sql"]


def check_values(sql: str, column: str) -> set:
    """The set of literals in ``check (<column> in ('a', 'b', ...))``."""
    match = re.search(
        r"check\s*\(\s*%s\s+in\s*\(([^)]*)\)\s*\)" % re.escape(column), sql, re.I
    )
    assert match, "no CHECK ... IN list for column %r in:\n%s" % (column, sql)
    return set(re.findall(r"'([^']*)'", match.group(1)))


@pytest.mark.parametrize(
    "table, column, expected", ENUMERATIONS, ids=[
        "%s.%s" % (table, column) for table, column, _ in ENUMERATIONS
    ]
)
def test_enumeration_matches_config(connection, table, column, expected):
    assert check_values(table_sql(connection, table), column) == set(expected)


def test_obligatory_kinds_are_a_subset_of_problem_kinds():
    """A debt-creating kind that no problem can have would silence debts entirely."""
    assert set(config.OBLIGATORY_KINDS) <= set(config.PROBLEM_KINDS)


def test_reversing_events_are_a_subset_of_the_event_kinds():
    assert set(config.REVERSING_EVENTS) <= set(config.MARK_EVENTS)
    assert "assert" not in config.REVERSING_EVENTS


def test_open_end_date_is_the_default_in_the_schema(connection):
    """The SCD2 sentinel is written in two places and must be the same string in both.

    A mismatch would not raise anywhere: rows would simply be inserted with a ``valid_to``
    the partial unique index does not recognise, and two "open" enrollments for one
    student would become legal.
    """
    sql = table_sql(connection, "enrollment")
    assert "default '%s'" % config.OPEN_END_DATE in sql.lower()

    index = connection.execute(
        "select sql from sqlite_master where type = 'index' and name = ?",
        ("enrollment_one_open_row",),
    ).fetchone()
    assert index is not None, "the partial unique index on the open row is missing"
    assert config.OPEN_END_DATE in index["sql"]


def test_every_domain_table_is_strict(connection):
    """STRICT is what stops a text id or a float weekday from being stored at all."""
    tables = ("sheets", "students", "teachers", "problems", "sessions", "marks",
              "attendance", "enrollment")
    not_strict = [
        table for table in tables if "strict" not in table_sql(connection, table).lower()
    ]
    assert not_strict == [], "not STRICT: %s" % not_strict


def test_foreign_keys_are_on_for_this_connection(connection, world):
    """A per-CONNECTION pragma, off by default: a connection that forgets accepts
    marks pointing at students who do not exist."""
    assert connection.execute("pragma foreign_keys").fetchone()[0] == 1
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "insert into marks (student_id, problem_id, event, valid_at, recorded_at, source) "
            "values (999999, ?, 'assert', ?, ?, 'кнопка')",
            (world.problem_ids[0], "2026-09-02T09:00:00Z", "2026-09-02T09:00:00Z"),
        )


def test_timestamps_must_be_the_one_wire_format(connection, world):
    """The GLOB constraint: a Moscow wall-clock string does not get in quietly."""
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "insert into marks (student_id, problem_id, event, valid_at, recorded_at, source) "
            "values (?, ?, 'assert', '02.09.2026 11:00', ?, 'кнопка')",
            (world.student_ids[0], world.problem_ids[0], "2026-09-02T09:00:00Z"),
        )
