"""The write path of registration.

P1 left the catalogue READ-ONLY by design (``core/ports.Catalogue`` has no
``insert_student``, no ``update_status``, no ``bind_tg_id``) and that is the
shape this position is allowed to extend -- in its OWN new files, never by
editing ``infra/repositories.py`` (other positions of this wave stand on it).

TWO stores, ONE file.  The reason for the split is given in the brief:

  * The journal is the carrier of ``students`` / ``teachers`` tables.  Their
    schema -- ``tg_id`` UNIQUE, ``status`` check, ``first_sheet_id`` references
    sheets -- is the contract this port upholds when writing.

  * The role of a teacher (HEAD vs TEACHER) and the room they are bound to do
    NOT live in any schema: there is no migration for them, and ``migrations/``
    is outside the zone.  They live in a SECOND SQLite file opened here.

The bot talks to ``RosterRepo`` (one object, two stores behind it).  Tests
substitute a fake.  No aiogram here.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional, Union

from core.services.roster import (
    PendingRegistration,
    Role,
    RosterPort,
    TeacherBinding,
    TelegramIdAlreadyBound,
)

PathLike = Union[str, Path]


#: Schema of the second file.  Kept here (not in a migration) because the role
#: data has no historical value -- the conduit rebuilds it each year from seed.
_SCHEMA = """
create table if not exists teacher_room_role (
  teacher_id integer primary key,
  role       text not null check (role in ('teacher', 'head')),
  room       text
) strict;

create table if not exists pending_registration (
  id             integer primary key,
  tg_id          integer not null,
  surname        text not null,
  name           text not null,
  intended_role  text not null check (intended_role in ('student', 'teacher', 'head')),
  room           text,
  created_at     text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
) strict;

create unique index if not exists pending_registration_tg_id
  on pending_registration (tg_id);
"""


def _row_to_pending(row: sqlite3.Row) -> PendingRegistration:
    return PendingRegistration(
        id=row["id"],
        tg_id=row["tg_id"],
        surname=row["surname"],
        name=row["name"],
        intended_role=Role(row["intended_role"]),
        room=row["room"],
    )


def _row_to_teacher(row: sqlite3.Row) -> TeacherBinding:
    return TeacherBinding(
        teacher_id=row["teacher_id"],
        role=Role(row["role"]),
        room=row["room"],
    )


class RosterRepo(RosterPort):
    """The write path of registration.

    ONE object, TWO connections:
      * ``journal``  : the P1 SQLite database, opened the same way P1 opens it
                       (``infra.db.connect``); this port writes ``students`` /
                       ``teachers`` rows here.
      * ``roster``   : a SECOND SQLite file with ``teacher_room_role`` and the
                       pending-registration bookkeeping; opened/created on demand.

    The two stores are NOT in one transaction -- and that is intentional.  The
    journal is the carrier of the ``tg_id`` UNIQUE on ``students``, and that
    guarantee must hold even if the roster file is corrupt.  Collisions on
    ``pending_registration.tg_id`` are caught by an explicit unique index here.
    """

    def __init__(self, journal: sqlite3.Connection, roster: sqlite3.Connection) -> None:
        self._journal = journal
        self._roster = roster
        self._roster.executescript(_SCHEMA)

    @classmethod
    def open(
        cls,
        *,
        journal_path: PathLike,
        roster_path: PathLike,
    ) -> "RosterRepo":
        """Open both files and return the repo.

        No defaults: the position that owns the bot decides where the files live
        and passes both paths in.  ``config.py`` stays untouched -- P1 designed
        it that way and ``config`` is outside this position's zone.
        """
        from infra.db import connect

        Path(roster_path).parent.mkdir(parents=True, exist_ok=True)
        journal = connect(journal_path)
        roster = sqlite3.connect(str(roster_path))
        roster.row_factory = sqlite3.Row
        return cls(journal, roster)

    def close(self) -> None:
        self._roster.close()
        # The journal connection is owned by ``infra.db.connect`` callers in the
        # rest of the project; we close it ONLY if we opened it (which we don't
        # in ``open``, so we don't here either).

    # ----------------------------------------------------------- journal writes

    def _create_student_row(
        self, *, surname: str, name: str, klass: Optional[str], first_sheet_id: int
    ) -> int:
        cursor = self._journal.execute(
            "insert into students (surname, name, class, status, first_sheet_id) "
            "values (?, ?, ?, 'active', ?)",
            (surname, name, klass, first_sheet_id),
        )
        return cursor.lastrowid

    def _bind_student_tg_id(self, *, student_id: int, tg_id: int) -> None:
        # Schema carries ``tg_id`` UNIQUE -- the second bind raises here, and
        # we surface it as the domain exception the brief asked for.
        try:
            self._journal.execute(
                "update students set tg_id = ? where id = ?", (tg_id, student_id)
            )
        except sqlite3.IntegrityError as exc:
            raise TelegramIdAlreadyBound(
                "tg_id %d is already bound to another student" % tg_id
            ) from exc

    def _student_by_tg_id(self, tg_id: int) -> Optional[int]:
        row = self._journal.execute(
            "select id from students where tg_id = ?", (tg_id,)
        ).fetchone()
        return row["id"] if row is not None else None

    def _create_teacher_row(self, *, name: str, aka: Optional[str]) -> int:
        cursor = self._journal.execute(
            "insert into teachers (name, aka, is_owner) values (?, ?, 0)",
            (name, aka),
        )
        return cursor.lastrowid

    def _bind_teacher_tg_id(self, *, teacher_id: int, tg_id: int) -> None:
        try:
            self._journal.execute(
                "update teachers set tg_id = ? where id = ?", (tg_id, teacher_id)
            )
        except sqlite3.IntegrityError as exc:
            raise TelegramIdAlreadyBound(
                "tg_id %d is already bound to another teacher" % tg_id
            ) from exc

    def _teacher_by_tg_id(self, tg_id: int) -> Optional[int]:
        row = self._journal.execute(
            "select id from teachers where tg_id = ?", (tg_id,)
        ).fetchone()
        return row["id"] if row is not None else None

    # ----------------------------------------------------------- roster port impl

    def create_pending(
        self,
        *,
        tg_id: int,
        surname: str,
        name: str,
        intended_role: Role,
        room: Optional[str] = None,
    ) -> PendingRegistration:
        try:
            cursor = self._roster.execute(
                "insert into pending_registration "
                "(tg_id, surname, name, intended_role, room) values (?, ?, ?, ?, ?)",
                (tg_id, surname, name, intended_role.value, room),
            )
        except sqlite3.IntegrityError as exc:
            # Same loudness rule as for students: a second pending for the
            # same Telegram id fails here, never overwrites.
            raise TelegramIdAlreadyBound(
                "tg_id %d already has a pending registration" % tg_id
            ) from exc
        row = self._roster.execute(
            "select id, tg_id, surname, name, intended_role, room "
            "from pending_registration where id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        return _row_to_pending(row)

    def list_pending(self) -> list:
        rows = self._roster.execute(
            "select id, tg_id, surname, name, intended_role, room "
            "from pending_registration order by id"
        ).fetchall()
        return [_row_to_pending(row) for row in rows]

    def get_pending(self, registration_id: int) -> Optional[PendingRegistration]:
        row = self._roster.execute(
            "select id, tg_id, surname, name, intended_role, room "
            "from pending_registration where id = ?",
            (registration_id,),
        ).fetchone()
        return _row_to_pending(row) if row is not None else None

    def resolve_pending(self, registration_id: int, *, accept: bool) -> None:
        # Whether the owner pressed accept or reject, the bookkeeping row
        # disappears: on accept, the corresponding students/teachers row has
        # already been promoted by ``RosterRepo`` BEFORE this call.
        self._roster.execute(
            "delete from pending_registration where id = ?", (registration_id,)
        )

    def rename_pending(self, registration_id: int, *, surname: str, name: str) -> None:
        self._roster.execute(
            "update pending_registration set surname = ?, name = ? where id = ?",
            (surname, name, registration_id),
        )

    def bind_teacher(
        self,
        *,
        teacher_id: int,
        role: Role,
        room: Optional[str] = None,
    ) -> TeacherBinding:
        if role not in (Role.TEACHER, Role.HEAD):
            raise ValueError("bind_teacher: not a teacher role: %r" % (role,))
        self._roster.execute(
            "insert into teacher_room_role (teacher_id, role, room) values (?, ?, ?) "
            "on conflict (teacher_id) do update set role = excluded.role, room = excluded.room",
            (teacher_id, role.value, room),
        )
        return TeacherBinding(teacher_id=teacher_id, role=role, room=room)

    def lookup_teacher(self, tg_id: int) -> Optional[TeacherBinding]:
        teacher_id = self._teacher_by_tg_id(tg_id)
        if teacher_id is None:
            return None
        return self._lookup_teacher_by_id(teacher_id)

    def lookup_teacher_by_id(self, teacher_id: int) -> Optional[TeacherBinding]:
        return self._lookup_teacher_by_id(teacher_id)

    def _lookup_teacher_by_id(self, teacher_id: int) -> Optional[TeacherBinding]:
        row = self._roster.execute(
            "select teacher_id, role, room from teacher_room_role where teacher_id = ?",
            (teacher_id,),
        ).fetchone()
        return _row_to_teacher(row) if row is not None else None

    def bind_student_tg_id(self, *, student_id: int, tg_id: int) -> None:
        self._bind_student_tg_id(student_id=student_id, tg_id=tg_id)

    def lookup_student(self, tg_id: int) -> Optional[int]:
        return self._student_by_tg_id(tg_id)