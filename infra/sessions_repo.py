"""SQLite adapter for the session/attendance port.

The port lives in ``core/services/sessions.py`` as two Protocols, ``SessionBook`` and
``AttendanceBook``.  This file is the only place that knows SQL about them; the service
does not import sqlite3 and does not import this file either.

THE TWO PROTOCOLS ARE TWO ADAPTERS, not one, on purpose.  A lesson and an attendance row
are different facts about the world (one is a fact about a date, the other about a
(student, lesson) pair), and a single class would force the service to know which table
it is talking to.  That is exactly the leak the rest of ``core/`` avoids.

ATTENDANCE-ON-SECOND-TAP is the only non-trivial part.  The schema has
``unique(session_id, student_id)`` and a raw second INSERT would raise IntegrityError.
The contract is the opposite: the second tap UPDATES the existing row, and a tap that
switches the status overwrites the previous one (a teacher who first tapped ``не был``
and then corrected to ``был`` after the student actually arrived has not made a mistake).
The ``mark`` method does INSERT-or-UPDATE inside one transaction and returns the row id
of the standing row.
"""

from __future__ import annotations

import sqlite3
from typing import Optional

from core.models import Session
from core.services.sessions import AttendanceRow


_SESSION_COLUMNS = "id, held_on, kind"

_ATTENDANCE_COLUMNS = "id, session_id, student_id, teacher_id, status"


def _session_from_row(row: sqlite3.Row) -> Session:
    return Session(id=row["id"], held_on=row["held_on"], kind=row["kind"])


def _attendance_from_row(row: sqlite3.Row) -> AttendanceRow:
    return AttendanceRow(
        id=row["id"],
        session_id=row["session_id"],
        student_id=row["student_id"],
        teacher_id=row["teacher_id"],
        status=row["status"],
    )


class SqliteSessionBook:
    """Persistence for ``sessions`` rows.  No update, no delete in the contract."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def create(self, held_on: str, kind: str) -> Session:
        cursor = self._connection.execute(
            "insert into sessions (held_on, kind) values (?, ?)",
            (held_on, kind),
        )
        row = self._connection.execute(
            "select %s from sessions where id = ?" % _SESSION_COLUMNS,
            (cursor.lastrowid,),
        ).fetchone()
        return _session_from_row(row)

    def find_on(self, held_on: str) -> Optional[Session]:
        row = self._connection.execute(
            "select %s from sessions where held_on = ? order by id desc limit 1"
            % _SESSION_COLUMNS,
            (held_on,),
        ).fetchone()
        return _session_from_row(row) if row is not None else None

    def by_id(self, session_id: int) -> Optional[Session]:
        row = self._connection.execute(
            "select %s from sessions where id = ?" % _SESSION_COLUMNS,
            (session_id,),
        ).fetchone()
        return _session_from_row(row) if row is not None else None

    def recent(self, limit: int) -> list[Session]:
        rows = self._connection.execute(
            "select %s from sessions order by held_on desc, id desc limit ?"
            % _SESSION_COLUMNS,
            (limit,),
        ).fetchall()
        return [_session_from_row(row) for row in rows]


class SqliteAttendanceBook:
    """Persistence for ``attendance`` rows with INSERT-or-UPDATE on the (session, student) key.

    The schema's ``unique(session_id, student_id)`` is the carrier of idempotency on
    insertion.  ``mark`` translates the IntegrityError into an UPDATE of the existing
    row, returning ``(row, written, changed)`` so the service can tell apart a fresh
    tap from a correction.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def mark(
        self,
        session_id: int,
        student_id: int,
        status: str,
        teacher_id: Optional[int],
    ) -> tuple[AttendanceRow, bool, bool]:
        """Insert or update.  Returns ``(row, written, changed)``."""
        existing = self._connection.execute(
            "select %s from attendance where session_id = ? and student_id = ?"
            % _ATTENDANCE_COLUMNS,
            (session_id, student_id),
        ).fetchone()

        if existing is None:
            cursor = self._connection.execute(
                "insert into attendance (session_id, student_id, teacher_id, status) "
                "values (?, ?, ?, ?)",
                (session_id, student_id, teacher_id, status),
            )
            row = self._connection.execute(
                "select %s from attendance where id = ?" % _ATTENDANCE_COLUMNS,
                (cursor.lastrowid,),
            ).fetchone()
            return _attendance_from_row(row), True, True

        changed = existing["status"] != status or existing["teacher_id"] != teacher_id
        if not changed:
            return _attendance_from_row(existing), False, False

        self._connection.execute(
            "update attendance set status = ?, teacher_id = ? where id = ?",
            (status, teacher_id, existing["id"]),
        )
        row = self._connection.execute(
            "select %s from attendance where id = ?" % _ATTENDANCE_COLUMNS,
            (existing["id"],),
        ).fetchone()
        return _attendance_from_row(row), False, True

    def list_for_session(self, session_id: int) -> list[AttendanceRow]:
        rows = self._connection.execute(
            "select %s from attendance where session_id = ? order by id"
            % _ATTENDANCE_COLUMNS,
            (session_id,),
        ).fetchall()
        return [_attendance_from_row(row) for row in rows]
