"""The SQLite stores behind the after-lesson notifications.

THREE SMALL ADAPTERS RATHER THAN ONE, for the reason ``infra/room_repo.py`` gives about
its own three: they answer unrelated questions, and one class would let a caller who
only wants to know who the head of a room is reach the writer of the sent-log.

WHY A FILE OF ITS OWN AND NOT A METHOD ON ``RosterRepo`` OR ON ``SqliteRoomRoster``.
``SqliteRoomRoster`` in ``infra/room_repo.py`` already reads ``teacher_room_role``, which
is another position's table, and says in its own docstring why it does so through an
adapter of its own instead of editing that position's file: reading somebody's table
through your own adapter is the layering this project already uses; editing their file in
the middle of a wave is the one thing a wave cannot do.  The same reasoning applies twice
over here, so the same shape is used.  ``HeadsOfRooms`` below is NOT a duplicate of
``SqliteRoomRoster``: that one answers "who may be handed a child in room 203" and
deliberately returns BOTH roles; this one answers "who is the head of room 203" and
returns only the head, because the summary of §3 belongs to the head by meaning and
sending it to every teacher in the room is exactly the thing §3 says not to do.

THE CLAIM IS ONE STATEMENT AND THAT IS THE WHOLE DESIGN.  ``SentLog.claim`` is an
``insert ... on conflict do nothing`` whose affected-row count is the answer: one means
"the claim is yours, send it", zero means "somebody already did".  A read followed by a
write would let two processes both read "not sent yet" on the same lesson and both send,
which is the failure the table exists to prevent -- and two processes IS the normal state
here, because a timer and a hand-run can overlap.

NOTHING IN THIS FILE KNOWS WHAT A NOTIFICATION SAYS.  The text lives in
``core/services/svodka.py``, which imports no sqlite3; this file writes rows and reads
rows and has no opinion about either.
"""

from __future__ import annotations

import sqlite3
from typing import Optional

from core.models import Teacher
from core.services.svodka import SentRecord, StoreRefused, TeacherPresence

_TEACHER_COLUMNS = "id, tg_id, name, aka, is_owner"


class SqliteSentLog:
    """The record of what has already been said, one row per (lesson, addressee).

    Lives in the JOURNAL database rather than the roster one: the roster file says of
    itself that its data "has no historical value -- the conduit rebuilds it each year
    from seed", and a sent-log rebuilt from seed would re-send every summary of the year.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def claim(
        self,
        session_id: int,
        recipient_kind: str,
        recipient_id: int,
        sent_at: str,
    ) -> bool:
        """Try to become the sender of this one message.  ``True`` iff the claim is ours.

        One statement, not a select-then-insert: the unique index is the carrier, and
        ``on conflict do nothing`` turns a race into a queue in which exactly one caller
        gets ``rowcount == 1``.

        A claim taken and then not delivered (the process dies between this call and the
        Telegram request) loses that one message.  That is the deliberate side to fail on:
        the alternative -- claim after sending -- loses the guarantee entirely, because a
        crash after sending and before claiming sends the SAME summary again on the next
        run, and a head who receives the evening twice stops reading it.  A message that
        did not arrive is a message somebody can ask for; a message that arrives twice
        teaches the reader to ignore the channel.
        """
        cursor = self._connection.execute(
            "insert into sent_notifications "
            "(session_id, recipient_kind, recipient_id, sent_at) values (?, ?, ?, ?) "
            "on conflict (session_id, recipient_kind, recipient_id) do nothing",
            (session_id, recipient_kind, recipient_id, sent_at),
        )
        return cursor.rowcount == 1

    def already_sent(self, session_id: int) -> list:
        """Every claim standing for this lesson.  For the report and for the tests; the
        send path never reads it, because reading before writing is the race above."""
        return [
            SentRecord(
                session_id=row["session_id"],
                recipient_kind=row["recipient_kind"],
                recipient_id=row["recipient_id"],
                sent_at=row["sent_at"],
            )
            for row in self._connection.execute(
                "select session_id, recipient_kind, recipient_id, sent_at "
                "from sent_notifications where session_id = ? "
                "order by recipient_kind, recipient_id",
                (session_id,),
            )
        ]


class SqliteTeacherAttendance:
    """The teacher's own answer to «вы были сегодня на занятии?».

    A separate table from ``attendance`` because ``attendance.student_id`` references
    ``students(id)`` and a teacher is not a student; see ``migrations/002_uvedomlenia.sql``
    for the whole reason.  The two carry the same two status values on purpose.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def record(
        self,
        session_id: int,
        teacher_id: int,
        status: str,
        answered_at: str,
    ) -> TeacherPresence:
        """Write the answer, overwriting an earlier one for the same lesson.

        A second tap is not an error and not a duplicate: a teacher who answered «не был»
        and then remembers he did look in for ten minutes is correcting himself, and the
        row he corrects is his own.  The unique key makes that an UPDATE rather than a
        second row.
        """
        try:
            self._connection.execute(
                "insert into teacher_attendance "
                "(session_id, teacher_id, status, answered_at) values (?, ?, ?, ?) "
                "on conflict (session_id, teacher_id) do update set "
                "status = excluded.status, answered_at = excluded.answered_at",
                (session_id, teacher_id, status, answered_at),
            )
        except sqlite3.IntegrityError as error:
            # The foreign key is the carrier and it must stay the carrier -- but the
            # EXCEPTION must not travel.  ``core/`` says of itself that it does not know
            # sqlite3, and a raw ``IntegrityError`` reaching the router means the callback
            # handler crashes on a teacher binding that points at a removed row, instead of
            # answering the person who tapped.  Translated here, where sqlite3 belongs.
            # Found by the after-type verifier of this position, finding 9.
            raise StoreRefused(
                "the store refused attendance for teacher %s at lesson %s: %s"
                % (teacher_id, session_id, error)
            ) from error
        return TeacherPresence(
            session_id=session_id,
            teacher_id=teacher_id,
            status=status,
            answered_at=answered_at,
        )

    def for_session(self, session_id: int) -> list:
        """Every answer given about this lesson, teacher id ascending."""
        return [
            TeacherPresence(
                session_id=row["session_id"],
                teacher_id=row["teacher_id"],
                status=row["status"],
                answered_at=row["answered_at"],
            )
            for row in self._connection.execute(
                "select session_id, teacher_id, status, answered_at "
                "from teacher_attendance where session_id = ? order by teacher_id",
                (session_id,),
            )
        ]


class SqliteWorkingTeachers:
    """Which teachers actually teach on a given lesson day, out of ``enrollment``.

    WHY THIS EXISTS, IN ONE MEASUREMENT.  Without it the after-lesson question goes to
    EVERY row of the ``teachers`` table: eighteen teachers, two of whom marked, sixteen
    asked "were you at the lesson?" twice a week -- including people who do not teach that
    weekday at all and people who have never been in the conduit.  A question about a fact
    turns into a nag by sheer volume, which is the one thing section 2 of the задание is
    about.  Found by the after-type verifier of this position, finding 2.

    ``enrollment`` is a Type 2 slowly-changing dimension keyed PER LESSON DAY: a teacher is
    bound to a group for a weekday over the half-open interval ``[valid_from, valid_to)``.
    So "who teaches on Thursday the 10th" is the set of teacher ids with an interval
    covering that date on that weekday, and a Monday teacher is correctly not asked about a
    Thursday lesson.

    Read-only, and an adapter of its own rather than a method on ``infra/enrollment_repo.py``:
    that file belongs to another position, and ``infra/room_repo.py`` states the rule this
    follows -- reading somebody's table through an adapter of one's own is the layering this
    project uses; editing their file mid-wave is the one thing a wave cannot do.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def on_day(self, day: str, weekday: int) -> list:
        """Teacher ids teaching on ``day`` (``YYYY-MM-DD``, ISO weekday ``weekday``).

        An EMPTY answer is meaningful and the caller must handle it rather than treat it as
        "ask nobody": before P2's importer has populated ``enrollment`` -- the real state at
        the start of a year -- nobody would ever be asked anything, and the feature would
        look broken while reporting success.  The caller's fallback is named in
        ``SvodkaService.teachers_without_marks`` and reported as coverage.
        """
        return [
            row["teacher_id"]
            for row in self._connection.execute(
                "select distinct teacher_id from enrollment "
                "where weekday = ? and valid_from <= ? and ? < valid_to "
                "order by teacher_id",
                (weekday, day, day),
            )
        ]


class SqliteHeadsOfRooms:
    """Which teacher is the HEAD of which room, read out of the roster store.

    Read-only, and the second connection is not this position's choice either:
    ``infra/roster_repo.py`` keeps a teacher's role and room in a SQLite file of its own
    beside the journal, and says so in its docstring.  So the head is looked up here and
    the head's NAME and Telegram id come from the ``teachers`` table in the journal --
    two stores for one person, which is why ``SqliteNotifiableTeachers`` below is separate
    again rather than folded in.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def heads(self) -> list:
        """``[(room, teacher_id), ...]`` for every room that has a head, room ascending.

        A room whose head has not registered yet simply does not appear.  That is a real
        state at the start of a year and not an error to raise inside a timer: the summary
        for the other rooms still goes out, and the missing one is visible as coverage
        ("сводок 2 из 3") rather than as an exception that stops the whole send.
        """
        return [
            (row["room"], row["teacher_id"])
            for row in self._connection.execute(
                "select room, teacher_id from teacher_room_role "
                "where role = 'head' and room is not null order by room, teacher_id"
            )
        ]


class SqliteNotifiableTeachers:
    """The teacher list with the one field the send path cannot do without: ``tg_id``.

    ``core.ports.Catalogue`` offers no teachers at all and belongs to another position,
    and ``SqliteTeachers`` in ``infra/room_repo.py`` reads the same rows for a different
    question (a name above a column).  Reading the whole list once per send is cheaper
    than eighteen lookups and simpler than a cache that can go stale between two lessons.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def teachers(self) -> list:
        return [_teacher_from_row(row) for row in self._connection.execute(
            "select %s from teachers order by id" % _TEACHER_COLUMNS
        )]

    def teacher(self, teacher_id: int) -> Optional[Teacher]:
        row = self._connection.execute(
            "select %s from teachers where id = ?" % _TEACHER_COLUMNS, (teacher_id,)
        ).fetchone()
        return _teacher_from_row(row) if row is not None else None


def _teacher_from_row(row: sqlite3.Row) -> Teacher:
    return Teacher(
        id=row["id"],
        name=row["name"],
        aka=row["aka"],
        tg_id=row["tg_id"],
        is_owner=bool(row["is_owner"]),
    )
