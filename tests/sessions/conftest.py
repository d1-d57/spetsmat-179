"""Fixtures for the session/attendance tests.

Same shape as ``tests/conftest.py`` but local to this subpackage: the default world in
``tests/conftest.py`` is one lesson, and the position's tests need TWO lessons on
DIFFERENT dates (so a multi-day batch can be tested), a FROZEN clock anchored at a date
that lets "today" be a specific day, and a roster large enough for the four
"attendance states" the criterion counts.

Nothing here imports sqlite3 -- the connection comes from the parent ``conftest.py``
via pytest fixture inheritance.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

import pytest

import config
from core.isotime import parse_iso, to_iso
from core.services.marking import MarkingService
from core.services.sessions import SessionsService
from infra.repositories import SqliteCatalogue, SqliteMarkJournal
from infra.sessions_repo import SqliteAttendanceBook, SqliteSessionBook


# The clock is anchored at 2026-09-04 (Friday).  Two lessons sit on 2026-09-02 (Wed)
# and 2026-09-04 (Fri), and the batch test relies on the service resolving both dates
# from the same "now".
TODAY_ISO = "2026-09-04T08:00:00Z"
LESSON_DAY_MON = date(2026, 9, 2)
LESSON_DAY_FRI = date(2026, 9, 4)


class FrozenClock:
    """A clock the test moves by hand.

    Same shape as ``tests.conftest.FrozenClock`` but kept local so this subpackage does
    not depend on the parent's wall clock choice.
    """

    def __init__(self, start: str = TODAY_ISO) -> None:
        self._now = start

    def now_iso(self) -> str:
        return self._now

    def tick_days(self, days: int) -> str:
        from datetime import timedelta
        self._now = to_iso(parse_iso(self._now) + timedelta(days=days))
        return self._now


@dataclass
class SessionWorld:
    """The ids of a seeded world with TWO lessons and a small roster.

    The four attendance states the position's red-line test compares are formed from
    three of these students (a, b, c); the fourth student is unused and exists only to
    prove the absent-from-the-session state (d).
    """

    student_ids: list = field(default_factory=list)
    teacher_ids: list = field(default_factory=list)
    sheet_ids: list = field(default_factory=list)
    problem_ids: list = field(default_factory=list)
    session_id_mon: Optional[int] = None
    session_id_fri: Optional[int] = None

    @property
    def session_id(self) -> int:
        """Back-compat for tests that want a single id; the Friday one."""
        return self.session_id_fri

    @property
    def student_present_with_marks(self) -> int:
        return self.student_ids[0]

    @property
    def student_present_no_marks(self) -> int:
        return self.student_ids[1]

    @property
    def student_absent(self) -> int:
        return self.student_ids[2]

    @property
    def student_no_row(self) -> int:
        return self.student_ids[3]


def seed_sessions_world(connection: sqlite3.Connection) -> SessionWorld:
    """Two teachers, four students, one sheet with one obligatory problem, two lessons.

    The sheet is issued on 2026-09-01, so both lessons are after the sheet was issued
    and the "valid_at before issued_at" refusal has a clean test path.
    """
    world = SessionWorld()

    for teacher_index in range(2):
        cursor = connection.execute(
            "insert into teachers (name, aka, is_owner) values (?, ?, ?)",
            ("teacher-%d" % teacher_index, "t%d" % teacher_index, 0),
        )
        world.teacher_ids.append(cursor.lastrowid)

    cursor = connection.execute(
        "insert into sheets (number, title, issued_at, ord) values (?, ?, ?, ?)",
        ("1", "sheet 1", "2026-09-01", 1),
    )
    sheet_id = cursor.lastrowid
    world.sheet_ids.append(sheet_id)

    cursor = connection.execute(
        "insert into problems (sheet_id, label, kind, ord) values (?, ?, ?, ?)",
        (sheet_id, "1.1", "обязательная", 1),
    )
    world.problem_ids.append(cursor.lastrowid)

    for student_index in range(4):
        cursor = connection.execute(
            "insert into students (surname, name, class, status, first_sheet_id) "
            "values (?, ?, ?, ?, ?)",
            ("surname-%d" % student_index, "name-%d" % student_index, "10a", "active", sheet_id),
        )
        world.student_ids.append(cursor.lastrowid)

    cursor = connection.execute(
        "insert into sessions (held_on, kind) values (?, ?)",
        (LESSON_DAY_MON.isoformat(), "обычное"),
    )
    world.session_id_mon = cursor.lastrowid

    cursor = connection.execute(
        "insert into sessions (held_on, kind) values (?, ?)",
        (LESSON_DAY_FRI.isoformat(), "обычное"),
    )
    world.session_id_fri = cursor.lastrowid

    return world


@pytest.fixture
def sessions_clock():
    return FrozenClock()


@pytest.fixture
def sessions_journal(connection):
    return SqliteMarkJournal(connection)


@pytest.fixture
def sessions_catalogue(connection):
    return SqliteCatalogue(connection)


@pytest.fixture
def session_book(connection):
    return SqliteSessionBook(connection)


@pytest.fixture
def attendance_book(connection):
    return SqliteAttendanceBook(connection)


@pytest.fixture
def sessions_marking(sessions_journal, sessions_clock):
    return MarkingService(sessions_journal, sessions_clock)


@pytest.fixture
def sessions_service(
    session_book,
    attendance_book,
    sessions_marking,
    sessions_journal,
    sessions_catalogue,
    sessions_clock,
):
    return SessionsService(
        session_book=session_book,
        attendance_book=attendance_book,
        marking=sessions_marking,
        journal=sessions_journal,
        catalogue=sessions_catalogue,
        clock=sessions_clock,
    )


@pytest.fixture
def sessions_world(connection):
    return seed_sessions_world(connection)
