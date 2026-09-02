"""Fixtures for the grid tests.

TWO THINGS THIS FILE EXISTS FOR.

**The REAL seed, not a toy world.**  ``tests/conftest.py`` builds a deliberately small
world -- five students, four problems -- because that is where journal bugs live.  The
layout of a keyboard is the opposite kind of question: it breaks on the sheet with 44
problems, on the label that contains the payload separator, on the sheet whose problem
count is not a multiple of four.  So these fixtures load ``seed/sheets.json`` through the
production loader and test against all eighteen sheets and all 544 problems.

**A dispatcher of its own.**  ``tests/bot/conftest.py`` is P3's and stays P3's: a fixture
file is a file, and two positions writing into one file is the single thing a wave cannot
do.  The recording session below is therefore a sibling of P3's, not an import of it --
the duplication is deliberate and is named in ``## ОТЧЁТ``.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List

import pytest
from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.methods import AnswerCallbackQuery, SendMessage, TelegramMethod
from aiogram.methods.base import TelegramType

from bot.app import build
from core.services.seeding import seed_catalogue
from infra.db import connect
from infra.repositories import SqliteCatalogue


# ------------------------------------------------------------------ the real seed

@pytest.fixture
def seeded_connection(connection):
    """A migrated database carrying the whole anonymised seed.

    Loaded through ``core.services.seeding.seed_catalogue`` -- the same code path P2's
    importer uses -- so that a change to the seed format breaks these tests instead of
    quietly making them test a shape nobody ships.
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
    return connection


@pytest.fixture
def seeded_catalogue(seeded_connection) -> SqliteCatalogue:
    return SqliteCatalogue(seeded_connection)


# ---- a session-scoped event loop --------------------------------------------

@pytest.fixture(scope="session")
def event_loop():
    """One loop for the whole session: a ``Bot`` binds its session to the loop that made
    it, and ``asyncio.run`` would strand it by closing a fresh loop each call."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---- a recording session for the Bot ----------------------------------------

@dataclass
class RecordedCall:
    """One outbound call the bot made, in the order it made it.

    The ORDER is what several of these tests are actually about: «``answer()`` first,
    redraw second» is a property of the sequence, and a test that only checked that both
    calls happened would pass on the failing arrangement.
    """

    method: str
    payload: Dict[str, Any]


class RecordingSession(BaseSession):
    """Swallows every Telegram call and remembers it.  Tests assert on what the bot
    TRIED to send, which is the only thing observable without a Telegram server."""

    def __init__(self) -> None:
        super().__init__()
        self.records: List[RecordedCall] = []
        #: Raised by the next ``editMessageText``, then cleared.  This is how the
        #: "message is not modified" path is reached without a real API.
        self.fail_next_edit: Exception = None

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
        if name == "EditMessageText" and self.fail_next_edit is not None:
            error, self.fail_next_edit = self.fail_next_edit, None
            raise error
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

    def methods(self) -> List[str]:
        return [record.method for record in self.records]

    def alerts(self) -> List[str]:
        return [
            record.payload.get("text") or ""
            for record in self.records
            if record.method == "AnswerCallbackQuery"
        ]

    def edits(self) -> List[Dict[str, Any]]:
        return [
            record.payload
            for record in self.records
            if record.method in ("EditMessageText", "EditMessageReplyMarkup")
        ]

    def texts(self) -> List[str]:
        return [
            record.payload.get("text") or ""
            for record in self.records
            if record.method in ("SendMessage", "EditMessageText")
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
    return tmp_path / "roster-grid.db"


@pytest.fixture
def dispatcher(seeded_connection, db_path, roster_path, owner_tg_id, bot_instance):
    """A dispatcher over the SEEDED journal.

    ``seeded_connection`` is requested before ``db_path`` is reopened so that the sheets
    and problems are already in the file the dispatcher opens.  P3's handler routers are
    module globals and remember the dispatcher they were attached to, so they are
    detached here exactly as P3's own fixture does it; P4's routers need no such step,
    because ``marking.build_routers`` hands out a fresh pair per build.
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
def teacher_tg_id(dispatcher, roster_path) -> int:
    """A confirmed TEACHER, bound to a Telegram account, ready to tap.

    Created through ``RosterService`` rather than by an insert, so the identity these
    tests exercise is the identity production builds.
    """
    from core.services.roster import Role

    roster = dispatcher.workflow_data["roster"]
    tg_id = 100500
    roster.confirm_teacher(
        roster.submit_teacher(
            tg_id=tg_id, surname="Учитель", name="Первый", room="каб-1"
        ).id,
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
    query_id: str = None,
):
    """One callback query.

    ``query_id`` is separate from ``update_id`` on purpose: a REDELIVERY is the same
    query id arriving again, and two distinct taps are two query ids.  The idempotency
    key the router derives is built from this value, so the two cases are only
    distinguishable in a test that can set it.
    """
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
                        "text": "grid",
                    },
                    "data": data,
                },
            },
        )
    )
