"""Fixtures for the after-lesson notifications.

FOUR THINGS THIS FILE EXISTS FOR.

**SIX TEACHERS, BECAUSE THE COVERAGE OF THIS POSITION IS SIX TIMES TWO.**  The готовности
criterion is «6 преподавателей × 2 состояния = 12 проверок, ложных отправок 0», so the
world is built with exactly six of them and the tests walk all six through both states.
The number is asserted in the fixture itself: a world that quietly shrank to two teachers
would turn «проверено 12 из 12» into «проверено 4 из 4» with no test going red, and the
two look identical in a green run.

**THE REAL STORES, NOT FAKES.**  The claim that makes a summary go out once is an
``insert ... on conflict do nothing`` in SQLite, and a fake that returned True-then-False
would be testing the fake.  So every adapter here is the one production uses, over the
migrated FILE database the root ``conftest.py`` builds -- including the second SQLite file
that ``infra/roster_repo.py`` keeps ``teacher_room_role`` in, because the head of a room
is read from there and nowhere else.

**MARKS WRITTEN THE WAY PRODUCTION WRITES THEM.**  ``mark_at`` goes through
``MarkingService`` with an explicit ``valid_at`` and an explicit ``teacher_id``, and
deliberately WITHOUT a ``session_id`` -- because that is the shape of every row the live
bot produces (``grep -rn session_id bot/`` is empty).  A fixture that stamped the session
by hand would be testing a journal nobody writes, and would hide the exact defect
``SvodkaService.handed_in`` is built around.

**A FIXTURE FILE OF ITS OWN.**  ``tests/views/conftest.py`` is P5's and
``tests/sessions/conftest.py`` is P6's; a fixture file is a file, and two positions writing
into one file is the single thing a wave cannot do.  The recording session below is
therefore a sibling of theirs rather than an import, and the duplication is deliberate and
named in ``## ОТЧЁТ``.
"""

from __future__ import annotations

import asyncio
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, List

import pytest
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import AnswerCallbackQuery, SendMessage, TelegramMethod
from aiogram.methods.base import TelegramType

from core.models import CellState
from core.services.marking import MarkingService
from core.services.progress import ProgressService
from core.services.spiski import SpiskiService
from core.services.svodka import SvodkaService
from infra.repositories import SqliteCatalogue, SqliteMarkJournal
from infra.sessions_repo import SqliteSessionBook
from infra.uvedomlenia_repo import (
    SqliteHeadsOfRooms,
    SqliteNotifiableTeachers,
    SqliteSentLog,
    SqliteTeacherAttendance,
    SqliteWorkingTeachers,
)

#: How many teachers the world holds.  The готовности criterion counts twelve checks over
#: six teachers and two states, and the number lives here so the tests can print their own
#: coverage instead of hard-coding it a second time.
TEACHERS = 6

#: The Telegram id of the first teacher.  Far from any student id so a mixed-up fixture
#: fails loudly rather than quietly addressing the wrong person.
TEACHER_TG_BASE = 500000

#: The rooms of the conduit, as ``core/services/roster.py`` names them.
ROOMS = ("203", "302", "303")

#: Three lesson days, which is exactly ``config.SILENT_SESSIONS`` -- the shortest journal
#: on which the silence rule can say anything at all.  Fewer, and every silent list comes
#: back ``enough_days=False``, which is a real state but not the one most tests are about.
DAYS = ("2026-09-07", "2026-09-10", "2026-09-14")


@dataclass
class NotifyWorld:
    """The ids of the seeded world, so a test names rows instead of guessing numbers."""

    teacher_ids: list
    student_ids: list
    problem_ids: list
    sheet_ids: list
    session_ids: dict  # day -> sessions(id)
    head_teacher_ids: list


@pytest.fixture
def roster_connection(tmp_path):
    """The SECOND SQLite file, the one ``teacher_room_role`` lives in.

    Not this position's choice: ``infra/roster_repo.py`` says in its own docstring that a
    teacher's role and room are kept beside the journal rather than in it.  The head of a
    room is read from here and the head's name and Telegram id from the ``teachers`` table
    in the journal -- two stores for one person, which is why the adapters are separate.
    """
    connection = sqlite3.connect(str(tmp_path / "roster-test.db"))
    connection.row_factory = sqlite3.Row
    connection.executescript(
        "create table if not exists teacher_room_role ("
        "  teacher_id integer primary key,"
        "  role       text not null check (role in ('teacher', 'head')),"
        "  room       text"
        ") strict;"
    )
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def notify_world(connection, roster_connection) -> NotifyWorld:
    """Six teachers, eight students, two sheets, three lesson days, three rooms.

    Small on purpose, exactly as the root ``conftest.py`` explains: every bug in a journal
    plus a projection lives in collisions between events on the same cell, and large random
    ids almost never collide.  The one thing that is NOT small is the number of teachers,
    because that number is the coverage of this position.
    """
    teacher_ids = []
    for index in range(TEACHERS):
        cursor = connection.execute(
            "insert into teachers (tg_id, name, aka, is_owner) values (?, ?, ?, 0)",
            (TEACHER_TG_BASE + index, "teacher-%d" % index, "t%d" % index),
        )
        teacher_ids.append(cursor.lastrowid)
    assert len(teacher_ids) == TEACHERS, (
        "the criterion of this position is 6 teachers x 2 states = 12 checks; "
        "the world built %d teachers" % len(teacher_ids)
    )

    sheet_ids = []
    problem_ids = []
    for sheet_index in range(2):
        cursor = connection.execute(
            "insert into sheets (number, title, issued_at, ord) values (?, ?, ?, ?)",
            ("%d" % (sheet_index + 1), "sheet %d" % (sheet_index + 1),
             "2026-09-01", sheet_index + 1),
        )
        sheet_id = cursor.lastrowid
        sheet_ids.append(sheet_id)
        for problem_index, kind in enumerate(
            ("обязательная", "обязательная", "обычная", "звезда")
        ):
            problem = connection.execute(
                "insert into problems (sheet_id, label, kind, ord) values (?, ?, ?, ?)",
                (sheet_id, "%d.%d" % (sheet_index + 1, problem_index + 1),
                 kind, problem_index + 1),
            )
            problem_ids.append(problem.lastrowid)

    student_ids = []
    for index in range(8):
        cursor = connection.execute(
            "insert into students (surname, name, class, status, first_sheet_id) "
            "values (?, ?, ?, ?, ?)",
            ("surname-%d" % index, "name-%d" % index, "8a", "active", sheet_ids[0]),
        )
        student_ids.append(cursor.lastrowid)

    session_ids = {}
    for day in DAYS:
        cursor = connection.execute(
            "insert into sessions (held_on, kind) values (?, 'обычное')", (day,)
        )
        session_ids[day] = cursor.lastrowid

    # The first three teachers are the heads of the three rooms; the rest are ordinary.
    head_teacher_ids = []
    for index, teacher_id in enumerate(teacher_ids):
        if index < len(ROOMS):
            role, room = "head", ROOMS[index]
            head_teacher_ids.append(teacher_id)
        else:
            role, room = "teacher", ROOMS[index % len(ROOMS)]
        roster_connection.execute(
            "insert into teacher_room_role (teacher_id, role, room) values (?, ?, ?)",
            (teacher_id, role, room),
        )
    roster_connection.commit()
    connection.commit()

    return NotifyWorld(
        teacher_ids=teacher_ids,
        student_ids=student_ids,
        problem_ids=problem_ids,
        sheet_ids=sheet_ids,
        session_ids=session_ids,
        head_teacher_ids=head_teacher_ids,
    )


@pytest.fixture
def svodka_journal(connection) -> SqliteMarkJournal:
    return SqliteMarkJournal(connection)


@pytest.fixture
def svodka_catalogue(connection) -> SqliteCatalogue:
    return SqliteCatalogue(connection)


@pytest.fixture
def sent_log(connection) -> SqliteSentLog:
    return SqliteSentLog(connection)


@pytest.fixture
def teacher_presence(connection) -> SqliteTeacherAttendance:
    return SqliteTeacherAttendance(connection)


@pytest.fixture
def svodka(
    connection,
    roster_connection,
    notify_world,
    svodka_journal,
    svodka_catalogue,
    sent_log,
    teacher_presence,
    clock,
) -> SvodkaService:
    """The service over the REAL adapters, wired exactly as ``bot/app.build`` wires it."""
    progress = ProgressService(svodka_journal, svodka_catalogue)
    return SvodkaService(
        lessons=SqliteSessionBook(connection),
        spiski=SpiskiService(svodka_journal, svodka_catalogue, progress),
        journal=svodka_journal,
        catalogue=svodka_catalogue,
        teachers=SqliteNotifiableTeachers(connection),
        heads=SqliteHeadsOfRooms(roster_connection),
        sent_log=sent_log,
        teacher_attendance=teacher_presence,
        clock=clock,
        # Who actually teaches on the lesson day.  Empty in most tests -- the fixture does
        # not populate ``enrollment`` -- so the service falls back to the whole teacher
        # list, which is the behaviour the twelve checks are counted over.
        roll=SqliteWorkingTeachers(connection),
    )


@pytest.fixture
def mark_at(svodka_journal, clock):
    """``mark_at(student_id, problem_id, day, teacher_id=...)`` -- one event on one day.

    NO ``session_id`` IS PASSED, and that is the whole point of the fixture: every row the
    live bot writes carries NULL there, so a test that stamped it would be testing a
    journal nobody produces and would hide the defect ``handed_in`` is built around.  The
    day part of ``valid_at`` is what ties the mark to the lesson, exactly as in production.
    """
    service = MarkingService(svodka_journal, clock)

    def write(
        student_id: int,
        problem_id: int,
        day: str,
        teacher_id=None,
        state: CellState = CellState.SOLVED,
        source: str = "кнопка",
    ):
        clock.tick()
        return service.set_state(
            student_id,
            problem_id,
            state,
            source=source,
            teacher_id=teacher_id,
            valid_at="%sT16:30:00Z" % day,
        )

    return write


# ---- a recording session for the Bot ----------------------------------------


@dataclass
class RecordedCall:
    """One outbound call the bot made, in the order it made it."""

    method: str
    payload: Dict[str, Any]


class RecordingSession(BaseSession):
    """Swallows every Telegram call and remembers it.

    Tests assert on what the bot TRIED to send, which is the only thing observable without
    a Telegram server -- and for this position it is also exactly the right question: the
    whole subject is «сколько сообщений ушло и кому».
    """

    def __init__(self) -> None:
        super().__init__()
        self.records: List[RecordedCall] = []
        #: Set to an exception to make the next send fail; the send path must count the
        #: failure and carry on rather than lose the other addressees.
        self.fail_with = None

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[TelegramType],
        timeout: int = None,
    ) -> TelegramType:
        if self.fail_with is not None and isinstance(method, SendMessage):
            raise self.fail_with
        self.records.append(
            RecordedCall(
                method=method.__class__.__name__,
                payload=method.model_dump()
                if hasattr(method, "model_dump")
                else method.dict(),
            )
        )
        if isinstance(method, AnswerCallbackQuery):
            return True
        if isinstance(method, SendMessage):
            return {
                "message_id": 1,
                "date": 0,
                "chat": {"id": method.chat_id, "type": "private"},
                "from": {"id": method.chat_id, "is_bot": True, "first_name": "bot"},
            }
        return True

    async def stream_content(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError("test bot does not stream")

    async def close(self) -> None:  # pragma: no cover
        pass

    # ------------------------------------------------------------------ readers

    def reset(self) -> None:
        self.records.clear()

    def sends(self) -> List[RecordedCall]:
        return [r for r in self.records if r.method == "SendMessage"]

    def chat_ids(self) -> List[int]:
        return [r.payload.get("chat_id") for r in self.sends()]

    def texts(self) -> List[str]:
        return [r.payload.get("text") or "" for r in self.sends()]


@pytest.fixture(scope="session")
def event_loop():
    """One loop for the whole test session.

    A ``Bot`` binds its session to the loop that created it, and ``asyncio.run`` would
    strand it by closing a fresh loop on every call.  Same fixture and same reason as
    ``tests/views/conftest.py``; it stands here rather than being imported because two
    positions cannot write into one fixture file.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def recorder() -> RecordingSession:
    return RecordingSession()


@pytest.fixture
def bot_instance(recorder) -> Bot:
    return Bot(token="0:fake", session=recorder)
