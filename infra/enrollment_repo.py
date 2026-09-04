"""The SQLite store of enrollment intervals: the adapter behind ``EnrollmentPort``.

THE ONE COLUMN THIS FILE EVER REWRITES ON AN EXISTING ROW IS ``valid_to``.  There is no
method here that sets ``teacher_id`` on a row that already exists, and that absence is
the carrier of this position: an assignment held as a current value is precisely the
defect being removed, and a service can only promise not to rewrite it while a store can
make the rewrite unreachable.  ``close`` shrinks an interval; ``insert`` writes a new
one; there is no third mutation.

The guards stay in the schema and are not re-implemented here:

  * ``enrollment_one_open_row`` — a partial unique index on ``(student_id, slot)``
    over rows whose ``valid_to`` is the open sentinel, so two open rows for one slot
    cannot exist;
  * ``enrollment_no_overlap_insert`` / ``..._update`` — triggers for two CLOSED
    intervals that overlap, which no index can express.

This file only translates their refusals into ``OverlappingHistory`` so that ``core/``
never has to catch a driver exception.  A guard re-implemented in Python would be a
second opinion about the same rule, and the two would eventually disagree.

Intervals are half-open, ``[valid_from, valid_to)``, and the open row carries
``config.OPEN_END_DATE`` — imported by name, never typed as a literal, because the day
the sentinel changes is the day every literal copy of it becomes a silent bug.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Optional, Sequence

import config
from core.models import Enrollment
from core.services.enrollment import EnrollmentError, EnrollmentPort, OverlappingHistory

_COLUMNS = "id, student_id, teacher_id, room, slot, valid_from, valid_to"

#: Fragments SQLite puts in the message when one of the schema's two enrollment guards
#: refuses a row.  Matched so that a foreign key failure — also an ``IntegrityError`` —
#: is re-raised as itself instead of being reported as an overlap it is not.
_OVERLAP_MARKERS = (
    "must not overlap",
    "unique constraint failed: enrollment.student_id",
)


def _enrollment_from_row(row: sqlite3.Row) -> Enrollment:
    return Enrollment(
        id=row["id"],
        student_id=row["student_id"],
        teacher_id=row["teacher_id"],
        room=row["room"],
        slot=row["slot"],
        valid_from=row["valid_from"],
        valid_to=row["valid_to"],
    )


def _as_overlap(exc: sqlite3.IntegrityError) -> Exception:
    """Translate the schema's refusal, or hand back an integrity error that is not one."""
    message = str(exc).lower()
    if any(marker in message for marker in _OVERLAP_MARKERS):
        return OverlappingHistory(str(exc))
    return exc


class SqliteEnrollmentRepo(EnrollmentPort):
    """``enrollment`` over SQLite.  One connection, no ownership of it."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    # ------------------------------------------------------------------ the seam

    @contextmanager
    def transaction(self):
        """``begin immediate`` around the close-then-insert of a move.

        IMMEDIATE and not DEFERRED, for the same reason as the mark journal: a deferred
        transaction takes only a read lock and upgrades on first write, so two movers
        both read the open row, both try to upgrade, and one gets a busy error that
        ``busy_timeout`` cannot wait out.  IMMEDIATE turns the race into a queue.

        A transaction already in progress is joined rather than nested — SQLite refuses a
        nested BEGIN, and whoever opened the outer one owns the commit.  That is what
        lets a caller wrap a move and a mark in one unit of work.
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

    # -------------------------------------------------------------------- reading

    def open_row(self, student_id: int, slot: int) -> Optional[Enrollment]:
        """The still-open interval for this (student, slot), or None.

        Keyed on the sentinel rather than on ``max(valid_to)``: the partial unique index
        is defined over exactly this predicate, so this lookup rides it and there is at
        most one row to find.
        """
        row = self._connection.execute(
            "select %s from enrollment "
            " where student_id = ? and slot = ? and valid_to = ?" % _COLUMNS,
            (student_id, slot, config.OPEN_END_DATE),
        ).fetchone()
        return _enrollment_from_row(row) if row is not None else None

    def rows_valid_on(
        self,
        day: str,
        slot: int,
        student_ids: Optional[Sequence[int]] = None,
    ) -> list:
        """Intervals covering ``day`` in that slot, in ONE query.

        The interval test is ``valid_from <= day and day < valid_to`` — half-open, so a
        handover on ``day`` itself belongs to the incoming teacher and to nobody else.
        The dates compare as strings, which is correct because every one of them is a
        zero-padded ISO day: the schema GLOBs that shape on write and
        ``core.services.enrollment.as_day`` checks it on the way in.
        """
        sql = (
            "select %s from enrollment "
            " where slot = ? and valid_from <= ? and ? < valid_to" % _COLUMNS
        )
        params: list = [slot, day, day]
        if student_ids is not None:
            # An EMPTY sequence means "nothing matches" and must NOT collapse into "no
            # filter": that is how a query about zero students quietly becomes a query
            # about all of them and a coverage count comes back full.
            if len(student_ids) == 0:
                return []
            sql += " and student_id in (%s)" % ", ".join("?" for _ in student_ids)
            params.extend(student_ids)
        rows = self._connection.execute(sql + " order by student_id, id", params).fetchall()
        return [_enrollment_from_row(row) for row in rows]

    def history(self, student_id: int, slot: Optional[int] = None) -> list:
        """Every interval of one student, oldest first; one slot if asked."""
        sql = "select %s from enrollment where student_id = ?" % _COLUMNS
        params: list = [student_id]
        if slot is not None:
            sql += " and slot = ?"
            params.append(slot)
        rows = self._connection.execute(
            sql + " order by slot, valid_from, id", params
        ).fetchall()
        return [_enrollment_from_row(row) for row in rows]

    # -------------------------------------------------------------------- writing

    def insert(
        self,
        *,
        student_id: int,
        teacher_id: int,
        room: str,
        slot: int,
        valid_from: str,
        valid_to: str = config.OPEN_END_DATE,
    ) -> Enrollment:
        """Write one interval and return it with the id the store assigned."""
        try:
            cursor = self._connection.execute(
                "insert into enrollment "
                "(student_id, teacher_id, room, slot, valid_from, valid_to) "
                "values (?, ?, ?, ?, ?, ?)",
                (student_id, teacher_id, room, slot, valid_from, valid_to),
            )
        except sqlite3.IntegrityError as exc:
            raise _as_overlap(exc) from exc
        return self._by_id(cursor.lastrowid)

    def close(self, enrollment_id: int, *, valid_to: str) -> Enrollment:
        """Move ``valid_to`` on one row — the only mutation this store offers.

        The statement names ``valid_to`` and nothing else, so a move cannot reach
        ``teacher_id`` even by accident.  The schema's second trigger covers this
        statement as well: shrinking an interval cannot create an overlap, but growing
        one can, and the same guard is what refuses it.
        """
        try:
            cursor = self._connection.execute(
                "update enrollment set valid_to = ? where id = ?",
                (valid_to, enrollment_id),
            )
        except sqlite3.IntegrityError as exc:
            raise _as_overlap(exc) from exc
        if cursor.rowcount != 1:
            raise EnrollmentError(
                "no enrollment row with id %s: nothing was closed, and reporting success "
                "here would leave the caller opening a successor to an interval that "
                "still runs to the open sentinel" % (enrollment_id,)
            )
        return self._by_id(enrollment_id)

    # -------------------------------------------------------------------- private

    def _by_id(self, enrollment_id: int) -> Enrollment:
        row = self._connection.execute(
            "select %s from enrollment where id = ?" % _COLUMNS, (enrollment_id,)
        ).fetchone()
        if row is None:
            raise EnrollmentError("enrollment row %s disappeared" % (enrollment_id,))
        return _enrollment_from_row(row)
