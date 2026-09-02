"""Shared fixtures for bot tests.

A migrated FILE journal DB (from P1's ``tests/conftest.py``) plus a roster DB
in the same temp directory.  The dispatcher is built with both paths so the
production wiring is the test wiring -- no fake repo here.

The Bot is given a recording session that swallows every Telegram API call
and stores the outbound request -- tests assert on what the bot TRIED to
send, not on what Telegram would have answered.  This is what the brief
meant by \"through ``dp.feed_raw_update`` with a substituted session\": the
session is what makes the bot addressable without an actual Telegram server.
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

import config
from bot.app import build
from infra.db import connect
from infra.roster_repo import RosterRepo


# ---- a session-scoped event loop --------------------------------------------

@pytest.fixture(scope="session")
def event_loop():
    """One event loop for the whole test session.

    aiogram's Bot opens an aiohttp session, which is bound to the loop that
    created it.  ``asyncio.run`` creates a NEW loop per call and closes it
    afterwards, which strands the bot's session.  We use a single loop and
    drive every test on it, so the bot lives across tests.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---- a recording session for the Bot ----------------------------------------

@dataclass
class RecordedCall:
    """One outbound call the bot made."""

    method: str
    payload: Dict[str, Any]


class _RecordingSession(BaseSession):
    """A session that records what the bot tried to send and replies with an
    empty Telegram response.  Enough for the middleware and handlers to run
    in-process without a network round-trip.
    """

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
        # Each method has its own response type; we return True for booleans
        # and an empty Message for SendMessage so the bot does not crash on
        # the response.  Aiogram coerces through the method's __call__.
        if isinstance(method, AnswerCallbackQuery):
            return True
        if isinstance(method, SendMessage):
            # Return a minimal Message-like dict -- tests don't read it.
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


@pytest.fixture
def recorder() -> _RecordingSession:
    return _RecordingSession()


@pytest.fixture
def roster_path(tmp_path):
    return tmp_path / "roster-test.db"


@pytest.fixture
def catalogue(dispatcher):
    return dispatcher.workflow_data["catalogue"]


@pytest.fixture
def seeded_catalogue(catalogue):
    """Insert one sheet so first_sheet_id has a non-NULL value to anchor on.

    The brief requires ``first_sheet_id`` to be the CURRENT sheet at
    confirmation time, never NULL.  P3 uses max(ord) as the current sheet;
    with one sheet inserted the max is unambiguous.
    """
    catalogue._connection.execute(
        "insert into sheets (number, title, issued_at, ord) values (?, ?, ?, ?)",
        ("1", "sheet 1", "2026-09-01", 1),
    )
    catalogue._connection.commit()
    return catalogue


@pytest.fixture
def owner_tg_id() -> int:
    return 999999


@pytest.fixture
def bot_instance(recorder):
    """The Bot that the dispatcher will drive.

    Stored as a workflow_data entry so the dispatcher and the tests both
    reach the same object -- ``feed_raw_update`` takes a Bot as the first
    positional argument, and the recorder has to read its records off the
    same session this bot uses.
    """
    bot = Bot(token="0:fake", session=recorder)
    return bot


@pytest.fixture
def dispatcher(db_path, roster_path, owner_tg_id, recorder, bot_instance):
    """A dispatcher wired against the two file DBs and the recording session.

    ``db_path`` and ``journal_path`` are the SAME file: P1's conftest already
    migrated the journal, and our ``RosterRepo.open`` reopens it.  Two
    ``connect`` calls on one file give the two connections the bot needs.

    The handler modules keep their ``Router`` objects as module globals -- they
    were attached to the dispatcher of the previous test.  Detach them here
    so a fresh build can re-attach without a "Router is already attached"
    error.
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
    # Stash the bot so tests can pass it to ``feed_raw_update``.
    dp.workflow_data["bot"] = bot_instance
    yield dp


# ---- helpers to drive updates through the dispatcher --------------------------

def feed_message(
    dp: Dispatcher,
    *,
    bot: Bot,
    chat_id: int,
    from_id: int,
    text: str,
    update_id: int = 1,
) -> None:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        dp.feed_raw_update(
            bot,
            {
                "update_id": update_id,
                "message": {
                    "message_id": update_id,
                    "date": 0,
                    "chat": {"id": chat_id, "type": "private"},
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
) -> None:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        dp.feed_raw_update(
            bot,
            {
                "update_id": update_id,
                "callback_query": {
                    "id": "cb-%d" % update_id,
                    "chat_instance": "ci",
                    "from": {"id": from_id, "is_bot": False, "first_name": "x"},
                    "message": {
                        "message_id": update_id,
                        "date": 0,
                        "chat": {"id": from_id, "type": "private"},
                    },
                    "data": data,
                },
            },
        )
    )


def messages_sent(recorder: _RecordingSession) -> List[str]:
    """The texts the bot sent, in order.  Empty list if it sent nothing."""
    return [
        record.payload.get("text", "")
        for record in recorder.records
        if record.method == "SendMessage"
    ]


def callback_alerts(recorder: _RecordingSession) -> List[str]:
    """The show_alert texts of AnswerCallbackQuery calls."""
    return [
        record.payload.get("text", "") or ""
        for record in recorder.records
        if record.method == "AnswerCallbackQuery"
    ]