"""A real room, on a real migrated database, driven through a real dispatcher.

EIGHTEEN CHILDREN IN ROOM 303 AND EIGHTEEN IN 304, because the three things this screen
does are only interesting against a room somebody else's children can walk into.  The
world is built for TODAY, whatever today is: the standing intervals are opened on the
weekday the clock actually reports, so the tests exercise the same
``lesson_day_of`` → ``weekday_of`` path production walks and not a frozen day that would
quietly stop matching it.

A DISPATCHER OF ITS OWN.  ``tests/grid/conftest.py`` is P4's and ``tests/bot/conftest.py``
is P3's; a fixture file is a file, and two positions writing into one file is the single
thing a wave cannot do.  The recording session below is therefore a sibling of theirs
rather than an import, and the duplication is deliberate and named in ``## ОТЧЁТ``.

THE TEACHERS ARE MADE THROUGH ``RosterService`` and not by an insert, because the identity
these tests exercise has to be the identity production builds: the head's room comes from
his own teacher binding, and a binding fabricated by hand would prove nothing about the
path the screen actually takes to find it.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List

import pytest
from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.methods import AnswerCallbackQuery, SendMessage, TelegramMethod
from aiogram.methods.base import TelegramType

from bot.app import build
from core.models import CellState
from core.services.enrollment import EnrollmentService, lesson_day_of, weekday_of
from core.services.marking import MarkingService
from core.services.roster import Role
from infra.db import SystemClock
from infra.enrollment_repo import SqliteEnrollmentRepo
from infra.repositories import SqliteMarkJournal

#: The room the head heads, and the room next door.  Strings, because ``enrollment.room``
#: and ``TeacherBinding.room`` are strings and the screen compares them directly.
ROOM = "303"
OTHER_ROOM = "304"

#: Eighteen, which is the number the готовности criterion counts and the number the head
#: has in front of him.
ROOM_SIZE = 18

#: Real-shaped surnames, and no digits in them.  The screen's own rule is that a button
#: carries a mark, a name and a count and nothing else, and a test asserts that SHAPE
#: rather than a list of forbidden words -- so a fixture surname with a digit in it would
#: break the assertion for a reason that has nothing to do with the screen.
ROOM_SURNAMES = (
    "Агаркова", "Аникина", "Быков", "Жуков", "Искеева", "Кудишин",
    "Лим", "Пирогов", "Романов", "Сафин", "Тихонов", "Ульянов",
    "Фомин", "Хабиров", "Цветков", "Чернов", "Шилов", "Юдин",
)
GUEST_SURNAMES = (
    "Абрамов", "Белов", "Волков", "Гуляев", "Дёмин", "Егоров",
    "Жарова", "Зимин", "Ильина", "Карпов", "Лапин", "Мухин",
    "Носов", "Орлова", "Панин", "Рыжов", "Седов", "Тарасов",
)
assert len(ROOM_SURNAMES) == len(GUEST_SURNAMES) == ROOM_SIZE

#: The day the world is built for.  Taken from the clock through the same call the
#: service uses, so the fixture cannot disagree with the screen about which day it is.
TODAY = lesson_day_of(SystemClock().now_iso())
WEEKDAY = weekday_of(TODAY)

#: Long before any day these tests look at, so every interval is open on TODAY.
VALID_FROM = "2025-09-01"

HEAD_TG_ID = 700001
SECOND_TEACHER_TG_ID = 700002
#: Bound to room 303 in the roster and holding NOBODY today.  He exists so that the one
#: case the screen used to get wrong is in the fixture rather than in a story: the teacher a
#: head most wants to hand a child to is the one with nobody, and a room whose teachers were
#: derived from «whoever holds a child here tonight» could not offer him.
IDLE_TEACHER_TG_ID = 700004
#: The HEAD of the room next door.  He has to be a head and not a plain teacher, because the
#: interesting collision -- two rooms wanting one child on one evening -- needs a second
#: person who can actually open this screen.
NEIGHBOUR_TEACHER_TG_ID = 700003
OWNER_TG_ID = 999999


# ------------------------------------------------------------------ the recording bot

@dataclass
class RecordedCall:
    """One outbound call, in the order it was made.

    The ORDER is what several of these tests are about: «``answer()`` first, redraw
    second» is a property of the sequence, and a test that only checked that both
    happened would pass on the failing arrangement.
    """

    method: str
    payload: Dict[str, Any]


class RecordingSession(BaseSession):
    """Swallows every Telegram call and remembers it."""

    def __init__(self) -> None:
        super().__init__()
        self.records: List[RecordedCall] = []

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[TelegramType],
        timeout: int = None,
    ) -> TelegramType:
        name = method.__class__.__name__
        self.records.append(
            RecordedCall(
                method=name,
                payload=method.model_dump() if hasattr(method, "model_dump") else method.dict(),
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

    # ------------------------------------------------------------------- readers

    def clear(self) -> None:
        self.records.clear()

    def methods(self) -> List[str]:
        return [record.method for record in self.records]

    def alerts(self) -> List[str]:
        return [
            record.payload.get("text") or ""
            for record in self.records
            if record.method == "AnswerCallbackQuery"
        ]

    def texts(self) -> List[str]:
        return [
            record.payload.get("text") or ""
            for record in self.records
            if record.method in ("SendMessage", "EditMessageText")
        ]

    def keyboards(self) -> List[Any]:
        out = []
        for record in self.records:
            markup = record.payload.get("reply_markup")
            if markup:
                out.append(markup)
        return out


@pytest.fixture(scope="session")
def event_loop():
    """One loop for the whole session: a ``Bot`` binds its session to the loop that made
    it, and a fresh loop per call would strand it."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def recorder() -> RecordingSession:
    return RecordingSession()


@pytest.fixture
def bot_instance(recorder) -> Bot:
    return Bot(token="0:fake", session=recorder)


@pytest.fixture
def roster_path(tmp_path):
    return tmp_path / "roster-room.db"


@pytest.fixture
def dispatcher(connection, db_path, roster_path, bot_instance):
    """The production dispatcher over the test database.

    ``connection`` is requested first so that the schema and the fixture's own writes are
    already in the file the dispatcher opens.  P3's handler routers are module globals
    that remember the dispatcher they were attached to, so they are detached here exactly
    as P3's own fixture does it; P4's and this position's routers need no such step,
    because both come from a factory.
    """
    from bot.handlers import owner as owner_module
    from bot.handlers import registration as registration_module
    from bot.handlers import student as student_module
    from bot.handlers import teacher as teacher_module

    for module in (owner_module, registration_module, student_module, teacher_module):
        module.router._parent_router = None

    dp = build(
        token="0:fake",
        owner_tg_id=OWNER_TG_ID,
        journal_path=db_path,
        roster_path=roster_path,
        bot=bot_instance,
    )
    dp.workflow_data["bot"] = bot_instance
    yield dp


# ------------------------------------------------------------------------ the world

@dataclass
class Room:
    """The ids of the built world, so that a test names rows instead of guessing them."""

    head_teacher_id: int = 0
    second_teacher_id: int = 0
    neighbour_teacher_id: int = 0
    #: A teacher of THIS room with no standing students today.
    idle_teacher_id: int = 0
    #: The eighteen children of room 303, in surname order.
    students: list = field(default_factory=list)
    #: The eighteen children of room 304 -- the pool a guest is taken from.
    outsiders: list = field(default_factory=list)
    sheet_ids: list = field(default_factory=list)
    problem_ids: list = field(default_factory=list)

    def standing_teacher_of(self, index: int) -> int:
        """Who holds child ``index`` of this room, by the rule the fixture built with."""
        return self.head_teacher_id if index % 2 == 0 else self.second_teacher_id

    def other_teacher_of(self, index: int) -> int:
        """The other teacher of this room -- where a move for tonight sends him."""
        return self.second_teacher_id if index % 2 == 0 else self.head_teacher_id


def _make_teacher(roster, *, tg_id: int, surname: str, room: str, role: Role) -> int:
    binding = roster.confirm_teacher(
        roster.submit_teacher(tg_id=tg_id, surname=surname, name="Т.", room=room),
        role=role,
        room=room,
    )
    return binding.teacher_id


@pytest.fixture
def room_world(connection, dispatcher) -> Room:
    """Two sheets, three teachers, thirty-six children, and the standing arrangements.

    Debts vary from child to child on purpose.  A world in which everybody owed the same
    number would let a screen that printed a constant pass, and the debt count is the one
    number this screen exists to carry.
    """
    world = Room()

    for sheet_index in range(2):
        cursor = connection.execute(
            "insert into sheets (number, title, issued_at, ord) values (?, ?, ?, ?)",
            ("%d" % (sheet_index + 1), "листок %d" % (sheet_index + 1),
             "2025-09-%02d" % (sheet_index + 1), sheet_index + 1),
        )
        world.sheet_ids.append(cursor.lastrowid)

    # Three obligatory problems on the OLDER sheet: debts are obligatory problems left
    # standing on sheets older than the current one, so this is the only sheet that can
    # produce one.
    for ordinal, kind in enumerate(("обязательная", "обязательная", "обязательная")):
        cursor = connection.execute(
            "insert into problems (sheet_id, label, kind, ord) values (?, ?, ?, ?)",
            (world.sheet_ids[0], "1.%d" % (ordinal + 1), kind, ordinal + 1),
        )
        world.problem_ids.append(cursor.lastrowid)
    connection.execute(
        "insert into problems (sheet_id, label, kind, ord) values (?, ?, ?, ?)",
        (world.sheet_ids[1], "2.1", "обычная", 1),
    )

    roster = dispatcher.workflow_data["roster"]
    world.head_teacher_id = _make_teacher(
        roster, tg_id=HEAD_TG_ID, surname="Старший", room=ROOM, role=Role.HEAD
    )
    world.second_teacher_id = _make_teacher(
        roster, tg_id=SECOND_TEACHER_TG_ID, surname="Второй", room=ROOM, role=Role.TEACHER
    )
    world.idle_teacher_id = _make_teacher(
        roster, tg_id=IDLE_TEACHER_TG_ID, surname="Свободный", room=ROOM, role=Role.TEACHER
    )
    world.neighbour_teacher_id = _make_teacher(
        roster,
        tg_id=NEIGHBOUR_TEACHER_TG_ID,
        surname="Соседний",
        room=OTHER_ROOM,
        role=Role.HEAD,
    )

    enrollment = EnrollmentService(SqliteEnrollmentRepo(connection))
    marking = MarkingService(SqliteMarkJournal(connection), SystemClock())

    for index in range(ROOM_SIZE):
        # The rows are written in REVERSE alphabetical order, so the id order and the
        # surname order are each other's mirror.  A screen that happened to list children
        # by id would look perfectly sorted on a fixture built the other way round.
        surname_index = ROOM_SIZE - 1 - index
        for room, bucket, surnames in (
            (ROOM, world.students, ROOM_SURNAMES),
            (OTHER_ROOM, world.outsiders, GUEST_SURNAMES),
        ):
            cursor = connection.execute(
                "insert into students (surname, name, class, status, first_sheet_id) "
                "values (?, ?, ?, ?, ?)",
                (surnames[surname_index], "Ученик", "8а", "active", world.sheet_ids[0]),
            )
            student_id = cursor.lastrowid
            bucket.append(student_id)
            enrollment.assign(
                student_id,
                world.standing_teacher_of(index)
                if room == ROOM
                else world.neighbour_teacher_id,
                room=room,
                weekday=WEEKDAY,
                valid_from=VALID_FROM,
            )

        # Between zero and three of the older sheet's obligatory problems handed in, so
        # the eighteen debt counts are not all the same number.
        for problem_id in world.problem_ids[: index % 4]:
            marking.set_state(
                world.students[index],
                problem_id,
                CellState.SOLVED,
                source="кнопка",
                teacher_id=world.head_teacher_id,
                idempotency_key="fixture:%d:%d" % (world.students[index], problem_id),
            )

    connection.commit()
    return world


# ------------------------------------------------------------------ driving updates

def feed_message(dp: Dispatcher, *, bot: Bot, from_id: int, text: str, update_id: int = 1):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(
        dp.feed_raw_update(
            bot,
            {
                "update_id": update_id,
                "message": {
                    "message_id": update_id,
                    "date": 0,
                    "chat": {"id": from_id, "type": "private"},
                    "from": {"id": from_id, "is_bot": False, "first_name": "x"},
                    "text": text,
                },
            },
        )
    )


_next_update_id = [1000]


def feed_callback(dp: Dispatcher, *, bot: Bot, from_id: int, data: str):
    """One callback query.  Ids are unique per call, because a REDELIVERY is the same id
    arriving twice and no test here means to send one by accident."""
    _next_update_id[0] += 1
    update_id = _next_update_id[0]
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(
        dp.feed_raw_update(
            bot,
            {
                "update_id": update_id,
                "callback_query": {
                    "id": "cb-%d" % update_id,
                    "chat_instance": "ci",
                    "from": {"id": from_id, "is_bot": False, "first_name": "x"},
                    "message": {
                        "message_id": 77,
                        "date": 0,
                        "chat": {"id": from_id, "type": "private"},
                        "text": "аудитория",
                    },
                    "data": data,
                },
            },
        )
    )
