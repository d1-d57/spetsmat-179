"""Fixtures shared by every test: a migrated FILE database and the services over it.

THE TEST DATABASE IS A FILE, never ``:memory:``.  WAL is the whole reason this project
uses SQLite the way it does, and WAL does not work on an in-memory database once more
than one connection is open -- an in-memory test would therefore be testing a different
database from the one that runs in production, which is the least useful kind of green.

The world these fixtures build is deliberately SMALL (five students, four problems on a
sheet).  All the bugs in a journal-plus-projection live in collisions between events on
the same cell, and random large ids almost never collide.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Optional, Sequence

import pytest

import config
from core.isotime import parse_iso, to_iso
from core.services.marking import MarkingService
from core.services.progress import ProgressService
from infra.db import apply_migrations, connect
from infra.repositories import SqliteCatalogue, SqliteMarkJournal


class FrozenClock:
    """A clock the test moves by hand.

    ``recorded_at`` is injected rather than read from the machine so that a test can
    say "this mark reached the database a day after it happened" and have the two times
    actually differ.  With the real clock they differ by microseconds and the assertion
    that distinguishes them is not testing anything.
    """

    def __init__(self, start: str = "2026-09-02T08:00:00Z") -> None:
        self._now = start

    def now_iso(self) -> str:
        return self._now

    def tick(self, seconds: int = 1) -> str:
        self._now = to_iso(parse_iso(self._now) + timedelta(seconds=seconds))
        return self._now


@dataclass
class World:
    """The ids of a seeded world, so that tests name rows instead of guessing ids."""

    student_ids: list = field(default_factory=list)
    sheet_ids: list = field(default_factory=list)
    #: sheet_id -> [problem_id, ...] in sheet order
    problems_by_sheet: dict = field(default_factory=dict)
    teacher_ids: list = field(default_factory=list)
    session_id: Optional[int] = None

    @property
    def problem_ids(self) -> list:
        return [pid for sheet_id in self.sheet_ids for pid in self.problems_by_sheet[sheet_id]]


def seed_world(
    connection: sqlite3.Connection,
    *,
    students: int = 5,
    sheets: Sequence[Sequence[str]] = (("обязательная", "обязательная", "обычная", "звезда"),),
    first_sheet_of: Optional[dict] = None,
) -> World:
    """Insert sheets, their problems, teachers, students and one session.

    ``sheets`` is one tuple of problem kinds per sheet, in issue order.  ``first_sheet_of``
    maps a student index onto the index of the sheet they first appeared at -- the rule
    that whoever arrived at sheet 6 does not owe sheets 1-5 has no other way to be tested.
    """
    world = World()

    for teacher_index in range(2):
        cursor = connection.execute(
            "insert into teachers (name, aka, is_owner) values (?, ?, ?)",
            ("teacher-%d" % teacher_index, "t%d" % teacher_index, 0),
        )
        world.teacher_ids.append(cursor.lastrowid)

    for sheet_index, kinds in enumerate(sheets):
        cursor = connection.execute(
            "insert into sheets (number, title, issued_at, ord) values (?, ?, ?, ?)",
            ("%d" % (sheet_index + 1), "sheet %d" % (sheet_index + 1),
             "2026-09-%02d" % (sheet_index + 1), sheet_index + 1),
        )
        sheet_id = cursor.lastrowid
        world.sheet_ids.append(sheet_id)
        world.problems_by_sheet[sheet_id] = []
        for problem_index, kind in enumerate(kinds):
            problem = connection.execute(
                "insert into problems (sheet_id, label, kind, ord) values (?, ?, ?, ?)",
                (sheet_id, "%d.%d" % (sheet_index + 1, problem_index + 1), kind, problem_index + 1),
            )
            world.problems_by_sheet[sheet_id].append(problem.lastrowid)

    first_sheet_of = first_sheet_of or {}
    for student_index in range(students):
        sheet_index = first_sheet_of.get(student_index, 0)
        cursor = connection.execute(
            "insert into students (surname, name, class, status, first_sheet_id) "
            "values (?, ?, ?, ?, ?)",
            ("surname-%d" % student_index, "name-%d" % student_index, "10a", "active",
             world.sheet_ids[sheet_index]),
        )
        world.student_ids.append(cursor.lastrowid)

    cursor = connection.execute(
        "insert into sessions (held_on, kind) values (?, ?)", ("2026-09-02", "обычное")
    )
    world.session_id = cursor.lastrowid
    return world


@pytest.fixture
def db_path(tmp_path):
    """Path to a fresh, migrated database file.  One per test, in pytest's temp dir."""
    path = tmp_path / "spetsmat-test.db"
    applied = apply_migrations(path, config.MIGRATIONS_DIR)
    assert applied, "no migration was applied: the schema under test would be empty"
    return path


@pytest.fixture
def connection(db_path):
    """A connection with every pragma this project depends on -- foreign keys included."""
    conn = connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def clock():
    return FrozenClock()


@pytest.fixture
def journal(connection):
    return SqliteMarkJournal(connection)


@pytest.fixture
def catalogue(connection):
    return SqliteCatalogue(connection)


@pytest.fixture
def marking(journal, clock):
    return MarkingService(journal, clock)


@pytest.fixture
def progress(journal, catalogue):
    return ProgressService(journal, catalogue)


@pytest.fixture
def world(connection):
    """The default small world: five students, one sheet of four problems."""
    return seed_world(connection)
