"""The world the text tests work against: a REAL migrated database, seeded from ``seed/``.

Not the five-student world of ``tests/conftest.py``, and not a list of dataclasses either.
Two reasons, both of them things that only a real catalogue can go wrong about:

  * **The ids are the assertion.**  The owner named four children and the готовности
    criterion names their ids -- 23, 18, 9, 11.  Those ids exist because ``seed_catalogue``
    inserts ``seed/students.csv`` in file order; a test that invents its own ids would be
    green while the bot resolved «Лёня Санин» to somebody else entirely.
  * **The sheets are the other half.**  `[3д]` has to name листок 17 and the current sheet
    has to be `4д`, and both are facts about ``sheets.json`` as it is actually loaded --
    ``ord``, ``number`` and ``problems_of_sheet`` included.

Every collision this path can have is between two children who are written alike or two
labels that print alike, and a world of five never collides.
"""

from __future__ import annotations

import pytest

import config
from core.services.seeding import seed_catalogue
from infra.db import apply_migrations, connect
from infra.repositories import SqliteCatalogue

#: The four strings the owner actually types, and the children he means by them.  Written
#: down ONCE, here, so that the named tests below and the coverage test cannot drift apart.
OWNER_LINES = (
    ("Лёня Санин 7, 9а, 11б, 12, 13, 15а, 15в, 2б, 4, 6", 23, "Исанин", "Леонид"),
    ("Катя Долкирева 2а, 2б, 4, 5в, 8, 10а", 18, "Долгирева", "Екатерина"),
    ("Аня Бочарова [3д] 5, 12", 9, "Бочарова", "Анна"),
    ("Влад Быков —", 11, "Быков", "Владислав"),
)

#: The four lines as the owner would send them: one message, one block per child.
OWNER_MESSAGE = "\n".join(line for line, _, _, _ in OWNER_LINES)


@pytest.fixture
def live_db_path(tmp_path):
    """The FILE the catalogue lives in, migrated and empty.

    Named separately from the connection because the screen needs both: the services under
    test take a connection, and ``RosterRepo.open`` takes a path.  A second migrated file
    for the screen would be a second catalogue, and the ids the owner's four tests name
    are positions in this one.
    """
    path = tmp_path / "spetsmat-text.db"
    applied = apply_migrations(path, config.MIGRATIONS_DIR)
    assert applied, "no migration was applied: the catalogue under test would be empty"
    return path


@pytest.fixture
def live_db(live_db_path):
    """A migrated database with the whole seed in it -- 56 students, 18 sheets."""
    connection = connect(live_db_path)
    counts = seed_catalogue(connection)
    assert counts.students_written == 56, (
        "the seed no longer carries 56 students (%d written); the ids the owner's four "
        "tests name are positions in that file and would silently mean other children"
        % counts.students_written
    )
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def catalogue(live_db):
    return SqliteCatalogue(live_db)


@pytest.fixture
def students(catalogue):
    return catalogue.students()


@pytest.fixture
def current_sheet(catalogue):
    """The sheet a line with no bracket is about: rule 2, «листок по умолчанию — текущий»."""
    return max(catalogue.sheets(), key=lambda sheet: sheet.ord)


# =============================================================================
#  A DISPATCHER FOR THE TEXT SCREEN
# =============================================================================
#
# ⚠ WIRED HERE RATHER THAN THROUGH ``bot.app.build``, for a fact about this position and
# not a preference: ``bot/app.py`` is outside its zone, so ``text_input`` is included
# nowhere and a dispatcher built by ``build()`` would answer every typed record with the
# stale catch-all.  What this wires is therefore the PROPOSED wiring -- the same
# middleware, the same services, the router in the place its docstring says it must go.
# When the include lands in ``bot/app.py`` this fixture is replaced by ``build()``; that
# is named in the отчёт and is not a licence to leave it here forever.
#
# ``RecordingSession`` below is a SIBLING of the one in ``tests/voice/conftest.py`` rather
# than an import of it.  A conftest is a file, and two positions writing into one file is
# the single thing a wave cannot do; the duplication is deliberate and named in the отчёт.

import asyncio
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.methods import AnswerCallbackQuery, SendMessage, TelegramMethod
from aiogram.methods.base import TelegramType

from bot.middleware import AuthMiddleware
from bot.routers import text_input as text_module
from core.services.marking import MarkingService
from core.services.roster import Role, RosterService
from core.services.sessions import SessionsService
from infra.db import SystemClock
from infra.repositories import SqliteMarkJournal
from infra.roster_repo import RosterRepo
from infra.sessions_repo import SqliteAttendanceBook, SqliteSessionBook

def today_in_display_zone() -> date:
    """The civil day the bot is having, in the zone the bot displays.

    NOT frozen, and that is the deliberate choice.  A прочерк is written against the lesson
    held TODAY, and "today" is derived in exactly one way in this system -- P6's
    ``_today_in_display_zone`` over an injected ``Clock``.  A test that froze the clock to
    a literal date would fix the drift between the router and the service by hiding it: the
    screen would keep reading the wall clock while the service read 2026-09-02, and the
    pair would be green here and wrong in production.  So the screen fixtures run the
    service on ``SystemClock`` -- production's shape -- and the tests build their lesson on
    the day this helper names.  Nothing here goes red at midnight, because nothing here
    names a day.
    """
    return datetime.now(ZoneInfo(config.TZ_DISPLAY)).date()


@dataclass
class RecordedCall:
    method: str
    payload: Dict[str, Any]


class RecordingSession(BaseSession):
    """Swallows every Telegram call and remembers it, in order."""

    def __init__(self) -> None:
        super().__init__()
        self.records: List[RecordedCall] = []

    async def make_request(self, bot, method: TelegramMethod[TelegramType], timeout=None):
        self.records.append(
            RecordedCall(
                method=method.__class__.__name__,
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

    def methods(self) -> list:
        return [record.method for record in self.records]

    def texts(self) -> list:
        return [
            record.payload.get("text") or ""
            for record in self.records
            if record.method in ("SendMessage", "EditMessageText")
        ]

    def alerts(self) -> list:
        return [
            record.payload.get("text") or ""
            for record in self.records
            if record.method == "AnswerCallbackQuery"
        ]

    def keyboards(self) -> list:
        out = []
        for record in self.records:
            markup = record.payload.get("reply_markup")
            if markup:
                out.append(markup.get("inline_keyboard", []))
        return out


@pytest.fixture
def recorder() -> RecordingSession:
    return RecordingSession()


@pytest.fixture
def bot_instance(recorder) -> Bot:
    return Bot(token="0:fake", session=recorder)


@pytest.fixture
def text_dispatcher(live_db, live_db_path, catalogue, tmp_path, bot_instance):
    """The proposed wiring, as a dispatcher: auth, the services, the text router."""
    repo = RosterRepo.open(journal_path=live_db_path, roster_path=tmp_path / "roster-text.db")
    roster = RosterService(
        repo, sheets_for_current=lambda: max(catalogue.sheets(), key=lambda s: s.ord).id
    )
    journal = SqliteMarkJournal(live_db)
    marking = MarkingService(journal, SystemClock())
    sessions = SessionsService(
        SqliteSessionBook(live_db),
        SqliteAttendanceBook(live_db),
        MarkingService(journal, SystemClock()),
        journal,
        catalogue,
        SystemClock(),
    )

    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(AuthMiddleware(roster, owner_tg_id=999999))
    dp.callback_query.middleware(AuthMiddleware(roster, owner_tg_id=999999))
    dp.include_router(text_module.build_router())
    dp.workflow_data.update(
        {
            "catalogue": catalogue,
            "marking": marking,
            "roster": roster,
            "sessions": sessions,
            "bot": bot_instance,
        }
    )
    yield dp
    repo.close()


@pytest.fixture
def teacher_tg_id(text_dispatcher) -> int:
    """A confirmed teacher, made through ``RosterService`` so the identity is production's."""
    roster = text_dispatcher.workflow_data["roster"]
    tg_id = 100500
    roster.confirm_teacher(
        roster.submit_teacher(tg_id=tg_id, surname="Учитель", name="Первый", room="каб-1"),
        role=Role.TEACHER,
    )
    return tg_id


@pytest.fixture
def marking(text_dispatcher):
    return text_dispatcher.workflow_data["marking"]


@pytest.fixture
def lesson_today(screen_sessions):
    """The lesson a прочерк typed right now would land on."""
    return screen_sessions.create_lesson(today_in_display_zone(), config.SESSION_KINDS[0])


@pytest.fixture
def screen_sessions(text_dispatcher):
    """P6's service as the SCREEN sees it -- the same instance the handler will write to."""
    return text_dispatcher.workflow_data["sessions"]


def feed_text(dp, *, bot, from_id: int, text: str, update_id: int = 1):
    """One typed message, through the real dispatcher and the real middleware."""
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


def feed_callback(dp, *, bot, from_id: int, data: str, update_id: int = 2,
                  query_id: str = None):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(
        dp.feed_raw_update(
            bot,
            {
                "update_id": update_id,
                "callback_query": {
                    "id": query_id or "cb-%d" % update_id,
                    "chat_instance": "ci",
                    "from": {"id": from_id, "is_bot": False, "first_name": "x"},
                    "message": {
                        "message_id": 77,
                        "date": 0,
                        "chat": {"id": from_id, "type": "private"},
                        "text": "table",
                    },
                    "data": data,
                },
            },
        )
    )
