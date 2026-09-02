"""SQLite implementations of the ports in ``core/ports.py``.

This is the only file that knows SQL about the domain.  The projection in ``cells``
lives here on purpose: ``core/services/progress.py`` asks the database for the last
event of each pair and never folds the journal itself, which is what makes the
differential test in ``tests/test_differential.py`` a comparison of two INDEPENDENT
paths rather than a tautology.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Optional, Sequence

from core.models import (
    STATE_AFTER,
    Cell,
    Mark,
    MarkDraft,
    MarkEvent,
    Problem,
    Sheet,
    Student,
)

_MARK_COLUMNS = (
    "id, student_id, problem_id, session_id, event, reverses_id, teacher_id, "
    "valid_at, recorded_at, source, note, idempotency_key"
)


def _in_clause(column: str, values: Optional[Sequence[int]], params: list) -> str:
    """Render ``and column in (?, ?, ...)`` and push the values onto ``params``.

    ``None`` means "no filter".  An EMPTY sequence means "nothing matches" and must not
    collapse into "no filter" -- that is how a query for zero students quietly turns into
    a query for all of them.
    """
    if values is None:
        return ""
    if len(values) == 0:
        return " and 0"
    params.extend(values)
    return " and %s in (%s)" % (column, ", ".join("?" for _ in values))


def _mark_from_row(row: sqlite3.Row) -> Mark:
    return Mark(
        id=row["id"],
        student_id=row["student_id"],
        problem_id=row["problem_id"],
        session_id=row["session_id"],
        event=MarkEvent(row["event"]),
        reverses_id=row["reverses_id"],
        teacher_id=row["teacher_id"],
        valid_at=row["valid_at"],
        recorded_at=row["recorded_at"],
        source=row["source"],
        note=row["note"],
        idempotency_key=row["idempotency_key"],
    )


class SqliteMarkJournal:
    """The append-only journal.  No update, no delete: the schema refuses both."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    @contextmanager
    def transaction(self):
        """``begin immediate`` around a read-then-write, so two taps cannot interleave.

        IMMEDIATE and not DEFERRED: a deferred transaction takes only a read lock at
        ``begin`` and upgrades on the first write, so two writers both read, both try to
        upgrade, and one gets SQLITE_BUSY that ``busy_timeout`` cannot wait out -- the
        other transaction is still open, so waiting cannot help and SQLite says so
        immediately.  IMMEDIATE takes the write lock up front, which turns the same race
        into a queue: the loser blocks for ``config.BUSY_TIMEOUT_MS`` and then reads the
        winner's row.

        Connections are opened with ``isolation_level=None``, so nothing is implicitly
        open and the BEGIN here is the only one.  A transaction already in progress is
        joined rather than nested -- SQLite refuses a nested BEGIN, and the caller that
        opened the outer one owns the commit.
        """
        if self._connection.in_transaction:
            yield
            return
        self._connection.execute("begin immediate")
        try:
            yield
        except BaseException:
            self._connection.execute("rollback")
            raise
        else:
            self._connection.execute("commit")

    def append(self, draft: MarkDraft) -> Mark:
        cursor = self._connection.execute(
            "insert into marks (student_id, problem_id, session_id, event, reverses_id, "
            "teacher_id, valid_at, recorded_at, source, note, idempotency_key) "
            "values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                draft.student_id,
                draft.problem_id,
                draft.session_id,
                draft.event.value,
                draft.reverses_id,
                draft.teacher_id,
                draft.valid_at,
                draft.recorded_at,
                draft.source,
                draft.note,
                draft.idempotency_key,
            ),
        )
        row = self._connection.execute(
            "select %s from marks where id = ?" % _MARK_COLUMNS, (cursor.lastrowid,)
        ).fetchone()
        return _mark_from_row(row)

    def last_event(self, student_id: int, problem_id: int) -> Optional[Mark]:
        row = self._connection.execute(
            "select %s from marks where student_id = ? and problem_id = ? "
            "order by id desc limit 1" % _MARK_COLUMNS,
            (student_id, problem_id),
        ).fetchone()
        return _mark_from_row(row) if row is not None else None

    def find_by_idempotency_key(self, key: str) -> Optional[Mark]:
        row = self._connection.execute(
            "select %s from marks where idempotency_key = ?" % _MARK_COLUMNS, (key,)
        ).fetchone()
        return _mark_from_row(row) if row is not None else None

    def cells(
        self,
        student_ids: Optional[Sequence[int]] = None,
        problem_ids: Optional[Sequence[int]] = None,
    ) -> list:
        """One Cell per pair that has at least one event, state = last event.

        The grouped subquery rides ``marks_lookup (student_id, problem_id, id)``, so the
        max is read off the tail of the index instead of scanning the journal.
        """
        params: list = []
        where = "where 1" + _in_clause("student_id", student_ids, params)
        where += _in_clause("problem_id", problem_ids, params)
        rows = self._connection.execute(
            "select m.student_id as student_id, m.problem_id as problem_id, "
            "       m.event as event, m.id as last_event_id "
            "  from marks m "
            "  join (select student_id, problem_id, max(id) as last_id "
            "          from marks %s group by student_id, problem_id) last "
            "    on last.last_id = m.id" % where,
            params,
        ).fetchall()
        return [
            Cell(
                student_id=row["student_id"],
                problem_id=row["problem_id"],
                state=STATE_AFTER[MarkEvent(row["event"])],
                last_event_id=row["last_event_id"],
            )
            for row in rows
        ]

    def events(
        self,
        student_ids: Optional[Sequence[int]] = None,
        problem_ids: Optional[Sequence[int]] = None,
    ) -> list:
        params: list = []
        where = "where 1" + _in_clause("student_id", student_ids, params)
        where += _in_clause("problem_id", problem_ids, params)
        rows = self._connection.execute(
            "select %s from marks %s order by id" % (_MARK_COLUMNS, where), params
        ).fetchall()
        return [_mark_from_row(row) for row in rows]


class SqliteCatalogue:
    """Sheets, problems and students -- everything that is not an event."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    # ------------------------------------------------------------------- students

    def student(self, student_id: int) -> Optional[Student]:
        row = self._connection.execute(
            "select id, tg_id, surname, name, class, status, first_sheet_id "
            "from students where id = ?",
            (student_id,),
        ).fetchone()
        return self._student_from_row(row) if row is not None else None

    def students(self) -> list:
        rows = self._connection.execute(
            "select id, tg_id, surname, name, class, status, first_sheet_id "
            "from students order by surname, name, id"
        ).fetchall()
        return [self._student_from_row(row) for row in rows]

    @staticmethod
    def _student_from_row(row: sqlite3.Row) -> Student:
        return Student(
            id=row["id"],
            surname=row["surname"],
            name=row["name"],
            klass=row["class"],
            status=row["status"],
            first_sheet_id=row["first_sheet_id"],
            tg_id=row["tg_id"],
        )

    # --------------------------------------------------------------------- sheets

    def sheet(self, sheet_id: int) -> Optional[Sheet]:
        row = self._connection.execute(
            "select id, number, title, issued_at, ord from sheets where id = ?",
            (sheet_id,),
        ).fetchone()
        return self._sheet_from_row(row) if row is not None else None

    def sheets(self) -> list:
        rows = self._connection.execute(
            "select id, number, title, issued_at, ord from sheets order by ord, id"
        ).fetchall()
        return [self._sheet_from_row(row) for row in rows]

    @staticmethod
    def _sheet_from_row(row: sqlite3.Row) -> Sheet:
        return Sheet(
            id=row["id"],
            number=row["number"],
            title=row["title"],
            issued_at=row["issued_at"],
            ord=row["ord"],
        )

    # ------------------------------------------------------------------- problems

    def problems_of_sheet(self, sheet_id: int) -> list:
        rows = self._connection.execute(
            "select id, sheet_id, label, kind, ord from problems "
            "where sheet_id = ? order by ord, id",
            (sheet_id,),
        ).fetchall()
        return [self._problem_from_row(row) for row in rows]

    def problems_between(self, first_ord: int, last_ord: int) -> list:
        """Problems of every sheet whose ``ord`` lies in ``[first_ord, last_ord]``."""
        rows = self._connection.execute(
            "select p.id, p.sheet_id, p.label, p.kind, p.ord "
            "  from problems p join sheets s on s.id = p.sheet_id "
            " where s.ord between ? and ? "
            " order by s.ord, p.ord, p.id",
            (first_ord, last_ord),
        ).fetchall()
        return [self._problem_from_row(row) for row in rows]

    @staticmethod
    def _problem_from_row(row: sqlite3.Row) -> Problem:
        return Problem(
            id=row["id"],
            sheet_id=row["sheet_id"],
            label=row["label"],
            kind=row["kind"],
            ord=row["ord"],
        )
