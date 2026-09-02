"""The SQLite store behind the head's screen: sessions, attendance and the teacher list.

Three small adapters rather than one, because they answer three unrelated questions and a
single class would let a caller who needs a name reach the writer of attendance.

WHY THIS FILE EXISTS AT ALL, WHEN ``infra/sessions_repo.py`` NAMES THE SAME TABLE.  That
file is P6's zone and currently holds a five-line placeholder that declares itself
deferred; P6 is being redone.  Filling it from here would put two positions in one file
in the middle of a wave, which is the one thing a wave cannot do.  The adapters this
screen needs therefore live in a file of their own.  When P6 lands its own store, the
sessions adapter below is the one that goes and the room service keeps its port unchanged
-- which is exactly what the port is for.

WHAT ``attendance.teacher_id`` MEANS HERE.  Who this student worked with at THIS session,
and nothing beyond it.  The standing arrangement lives in ``enrollment`` as a half-open
interval per lesson day, and nothing in this file touches that table: there is no
statement here that names it.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Optional

import config
from core.models import Session, Teacher
from core.services.room import AttendanceRow

_SESSION_COLUMNS = "id, held_on, kind"
_TEACHER_COLUMNS = "id, tg_id, name, aka, is_owner"


def _session_from_row(row: sqlite3.Row) -> Session:
    return Session(id=row["id"], held_on=row["held_on"], kind=row["kind"])


@contextmanager
def _immediate(connection: sqlite3.Connection):
    """``begin immediate`` around a read-then-write.

    IMMEDIATE and not DEFERRED, for the same reason the mark journal gives: a deferred
    transaction takes only a read lock and upgrades on the first write, so two heads
    opening their screens in the same minute both read «no session today», both try to
    upgrade, and one gets a busy error that ``busy_timeout`` cannot wait out -- the other
    transaction is still open, so waiting cannot help.  IMMEDIATE takes the write lock up
    front and turns the race into a queue: the loser blocks, then reads the winner's row.

    A transaction already in progress is joined rather than nested; SQLite refuses a
    nested BEGIN and whoever opened the outer one owns the commit.
    """
    if connection.in_transaction:
        yield
        return
    connection.execute("begin immediate")
    try:
        yield
    except BaseException:
        connection.execute("rollback")
        raise
    else:
        connection.execute("commit")


class SqliteSessions:
    """The lessons themselves: one row per day the conduit met."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def for_day(self, held_on: str) -> Optional[Session]:
        """The session of that calendar day, SMALLEST id first.

        ``sessions.held_on`` carries no unique index, so a pair of rows for one day is a
        state this store can be in -- written by two screens opened in the same minute
        before the get-or-create existed, or by an import.  Answering with the smallest id
        makes every reader pick the same one of them, which keeps one lesson's attendance
        in one place instead of splitting it in half down two screens that each look
        consistent to whoever is reading.
        """
        row = self._connection.execute(
            "select %s from sessions where held_on = ? order by id limit 1"
            % _SESSION_COLUMNS,
            (held_on,),
        ).fetchone()
        return _session_from_row(row) if row is not None else None

    def create(self, held_on: str, kind: str = config.SESSION_KINDS[0]) -> Session:
        cursor = self._connection.execute(
            "insert into sessions (held_on, kind) values (?, ?)", (held_on, kind)
        )
        row = self._connection.execute(
            "select %s from sessions where id = ?" % _SESSION_COLUMNS,
            (cursor.lastrowid,),
        ).fetchone()
        return _session_from_row(row)


class SqliteAttendance:
    """Who was at a session, and with whom.

    ``unique (session_id, student_id)`` is the schema's, and it is what makes ``set`` an
    upsert rather than a check-then-insert: two taps on one child in the same second both
    ask for the same world, and the second one replaces the first one's row instead of
    adding a second.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def transaction(self):
        return _immediate(self._connection)

    def rows_for_session(self, session_id: int) -> list:
        return [
            AttendanceRow(
                student_id=row["student_id"],
                status=row["status"],
                teacher_id=row["teacher_id"],
            )
            for row in self._connection.execute(
                "select student_id, status, teacher_id from attendance "
                "where session_id = ? order by student_id",
                (session_id,),
            )
        ]

    def row(self, session_id: int, student_id: int) -> Optional[AttendanceRow]:
        row = self._connection.execute(
            "select student_id, status, teacher_id from attendance "
            "where session_id = ? and student_id = ?",
            (session_id, student_id),
        ).fetchone()
        if row is None:
            return None
        return AttendanceRow(
            student_id=row["student_id"],
            status=row["status"],
            teacher_id=row["teacher_id"],
        )

    def set(
        self,
        *,
        session_id: int,
        student_id: int,
        status: str,
        teacher_id: Optional[int],
    ) -> AttendanceRow:
        """Write the row for this (session, student), replacing whatever stood.

        ``on conflict ... do update`` and not a delete-then-insert: the pair is unique, so
        the conflict target is the whole key, and an upsert leaves no window in which the
        child is at the lesson according to nobody.
        """
        self._connection.execute(
            "insert into attendance (session_id, student_id, teacher_id, status) "
            "values (?, ?, ?, ?) "
            "on conflict (session_id, student_id) do update set "
            "teacher_id = excluded.teacher_id, status = excluded.status",
            (session_id, student_id, teacher_id, status),
        )
        return AttendanceRow(
            student_id=student_id, status=status, teacher_id=teacher_id
        )

    def clear(self, session_id: int, student_id: int) -> None:
        """Remove the row entirely.  Removing nothing is not an error.

        A removal and not a negative status: the head who untaps is saying «wrong child»,
        which is an erratum, and «did not come» is a different claim that this screen does
        not make.
        """
        self._connection.execute(
            "delete from attendance where session_id = ? and student_id = ?",
            (session_id, student_id),
        )


class SqliteTeachers:
    """The teacher list, read-only.

    The room screen wants exactly one thing from it -- a name to put above a column -- and
    it is a separate adapter because ``core.ports.Catalogue`` offers no teachers and that
    file belongs to another position.  Reading the whole list once per screen is cheaper
    than eighteen lookups and simpler than a cache that can go stale between two taps.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def teachers(self) -> list:
        return [
            Teacher(
                id=row["id"],
                name=row["name"],
                aka=row["aka"],
                tg_id=row["tg_id"],
                is_owner=bool(row["is_owner"]),
            )
            for row in self._connection.execute(
                "select %s from teachers order by id" % _TEACHER_COLUMNS
            )
        ]
