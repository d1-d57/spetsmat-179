"""Fixtures for the viewing screens.

THREE THINGS THIS FILE EXISTS FOR.

**The REAL seed and its fifty-six students.**  The privacy sweep is over the whole roster
by construction -- "проверено 2 из 56" and "проверено 56 из 56" look identical in a green
run, so the fixture loads ``seed/`` through ``core.services.seeding.seed_catalogue``, the
same code path P2's importer uses, and every screen test runs against eighteen sheets,
544 problems and the real fifty-six.

**Lesson days a test can put where it wants them.**  Silence is measured in days, and the
whole point of the rule is what happens across a boundary -- so ``mark_on`` writes one
journal event with an explicit ``valid_at``.  It goes through ``MarkingService`` rather
than through SQL: the service is what production writes with, and a fixture that inserted
rows by hand would be testing a journal nobody produces.

**A dispatcher of its own.**  ``tests/bot/conftest.py`` is P3's and ``tests/grid/conftest.py``
is P4's; a fixture file is a file, and two positions writing into one file is the single
thing a wave cannot do.  The recording session below is therefore a sibling of theirs, not
an import, and the duplication is deliberate and named in ``## ОТЧЁТ``.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, List, Optional

import pytest
from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.methods import AnswerCallbackQuery, SendMessage, TelegramMethod
from aiogram.methods.base import TelegramType

from bot.app import build
from core.isotime import parse_iso, to_iso
from core.models import CellState
from core.services.marking import MarkingService
from core.services.progress import ProgressService
from core.services.seeding import seed_catalogue
from core.services.spiski import SpiskiService
from infra.repositories import SqliteCatalogue, SqliteMarkJournal

#: The first Telegram id handed to a seeded student.  Far away from the owner's and from
#: the teacher's so a mixed-up fixture fails loudly instead of quietly authorising.
STUDENT_TG_BASE = 700000


# ------------------------------------------------------------------ the real seed

@pytest.fixture
def seeded_connection(connection):
    """A migrated database carrying the whole anonymised seed.

    The three assertions are the coverage of every test below: a seed that shrank would
    otherwise turn "проверено 56 из 56" into "проверено 5 из 5" with no test going red.
    """
    counts = seed_catalogue(connection)
    connection.commit()
    assert counts.sheets_written == 18, (
        "the seed is expected to carry 18 sheets; it wrote %d" % counts.sheets_written
    )
    assert counts.problems_written == 544, (
        "the seed is expected to carry 544 problems; it wrote %d"
        % counts.problems_written
    )
    assert counts.students_written == 56, (
        "the seed is expected to carry 56 students; it wrote %d"
        % counts.students_written
    )
    return connection


@pytest.fixture
def seeded_catalogue(seeded_connection) -> SqliteCatalogue:
    return SqliteCatalogue(seeded_connection)


@pytest.fixture
def seeded_journal(seeded_connection) -> SqliteMarkJournal:
    return SqliteMarkJournal(seeded_connection)


@pytest.fixture
def seeded_progress(seeded_journal, seeded_catalogue) -> ProgressService:
    return ProgressService(seeded_journal, seeded_catalogue)


@pytest.fixture
def spiski(seeded_journal, seeded_catalogue, seeded_progress) -> SpiskiService:
    return SpiskiService(seeded_journal, seeded_catalogue, seeded_progress)


class DayClock:
    """A clock the test drives by hand, used for ``recorded_at`` only.

    ``valid_at`` is passed explicitly by ``mark_on`` -- the two times are different
    questions and this project keeps them apart everywhere else too.
    """

    def __init__(self, start: str = "2026-09-02T08:00:00Z") -> None:
        self._now = start

    def now_iso(self) -> str:
        return self._now

    def tick(self, seconds: int = 1) -> str:
        self._now = to_iso(parse_iso(self._now) + timedelta(seconds=seconds))
        return self._now


@pytest.fixture
def mark_on(seeded_journal):
    """``mark_on(student_id, problem_id, day, state=SOLVED)`` -- one event on one day.

    ``day`` is a plain ``YYYY-MM-DD``; the wire format wants a full moment, so the helper
    fixes the hour rather than making every caller spell it.
    """
    clock = DayClock()
    service = MarkingService(seeded_journal, clock)

    def write(student_id: int, problem_id: int, day: str, state: CellState = CellState.SOLVED):
        clock.tick()
        return service.set_state(
            student_id,
            problem_id,
            state,
            source="кнопка",
            valid_at="%sT10:00:00Z" % day,
        )

    return write


# ---- a session-scoped event loop --------------------------------------------

@pytest.fixture(scope="session")
def event_loop():
    """One loop for the whole session: a ``Bot`` binds its session to the loop that made
    it, and ``asyncio.run`` would strand it by closing a fresh loop on every call."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---- a recording session for the Bot ----------------------------------------

@dataclass
class RecordedCall:
    """One outbound call the bot made, in the order it made it."""

    method: str
    payload: Dict[str, Any]


class RecordingSession(BaseSession):
    """Swallows every Telegram call and remembers it.  Tests assert on what the bot TRIED
    to send, which is the only thing observable without a Telegram server."""

    def __init__(self) -> None:
        super().__init__()
        self.records: List[RecordedCall] = []

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[TelegramType],
        timeout: int = None,
    ) -> TelegramType:
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

    # ------------------------------------------------------------------ readers

    def reset(self) -> None:
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
        """Everything the bot put in front of a person: sends, edits and alerts alike.

        A privacy sweep that read only ``SendMessage`` would miss a leak delivered by
        ``editMessageText``, which is how every callback screen of this project answers.
        """
        return [
            record.payload.get("text") or ""
            for record in self.records
            if record.method in ("SendMessage", "EditMessageText", "AnswerCallbackQuery")
        ]


@pytest.fixture
def recorder() -> RecordingSession:
    return RecordingSession()


@pytest.fixture
def owner_tg_id() -> int:
    return 999999


@pytest.fixture
def bot_instance(recorder) -> Bot:
    return Bot(token="0:fake", session=recorder)


@pytest.fixture
def roster_path(tmp_path):
    return tmp_path / "roster-views.db"


@pytest.fixture
def dispatcher(seeded_connection, db_path, roster_path, owner_tg_id, bot_instance):
    """A dispatcher over the SEEDED journal.

    ``seeded_connection`` is requested before ``db_path`` is reopened so that the sheets,
    problems and students are already in the file the dispatcher opens.  P3's handler
    routers are module globals that remember the dispatcher they were attached to, so they
    are detached here exactly as P3's own fixture does it; P4's and P5's routers need no
    such step, because both hand out a fresh router per build.
    """
    from bot.handlers import owner as owner_module
    from bot.handlers import registration as registration_module
    from bot.handlers import student as student_module
    from bot.handlers import teacher as teacher_module

    for module in (owner_module, registration_module, student_module, teacher_module):
        module.router._parent_router = None

    dp = build(
        token="0:fake",
        owner_tg_id=owner_tg_id,
        journal_path=db_path,
        roster_path=roster_path,
        bot=bot_instance,
    )
    dp.workflow_data["bot"] = bot_instance
    yield dp


@pytest.fixture
def bound_students(dispatcher, seeded_connection):
    """Every seeded student bound to a Telegram account: ``[(student_id, tg_id), ...]``.

    Bound through ``RosterPort.bind_student_tg_id`` -- the production seam the middleware
    later reads through ``student_id_for`` -- and not by an UPDATE of our own, so the
    identity the privacy sweep forges against is the identity production builds.
    """
    roster = dispatcher.workflow_data["roster"]
    catalogue = dispatcher.workflow_data["catalogue"]
    pairs = []
    for offset, student in enumerate(catalogue.students()):
        tg_id = STUDENT_TG_BASE + offset
        roster._port.bind_student_tg_id(student_id=student.id, tg_id=tg_id)
        pairs.append((student.id, tg_id))
    assert len(pairs) == 56, "the sweep must cover all 56 students; it covers %d" % len(pairs)
    return pairs


@pytest.fixture
def teacher_tg_id(dispatcher) -> int:
    """A confirmed TEACHER, bound to a Telegram account.

    Created through ``RosterService`` rather than by an insert, so the identity these
    tests exercise is the identity production builds.
    """
    from core.services.roster import Role

    roster = dispatcher.workflow_data["roster"]
    tg_id = 100500
    roster.confirm_teacher(
        roster.submit_teacher(tg_id=tg_id, surname="Учитель", name="Первый", room="каб-1"),
        role=Role.TEACHER,
    )
    return tg_id


# ---- driving updates ---------------------------------------------------------

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


def feed_callback(
    dp: Dispatcher,
    *,
    bot: Bot,
    from_id: int,
    data: str,
    update_id: int = 2,
    query_id: Optional[str] = None,
):
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
                        "text": "view",
                    },
                    "data": data,
                },
            },
        )
    )
