"""Fixtures for the photo screen: a real dispatcher, a fake model, no network.

TWO THINGS THIS FILE EXISTS FOR.

**A REAL dispatcher.**  The handlers are driven through ``dp.feed_raw_update`` over a
dispatcher built by ``bot.app.build``, so the middleware, the role gate and the payload
filters are the production ones.  ``bot/app.py`` is outside this position's zone and is
therefore not edited: the photo router is included by this fixture instead, and the exact
two lines ``bot/app.build`` needs are named in ``## ВОПРОСЫ`` of the заход.

🔴 **AND IT IS INCLUDED BEFORE P4's CATCH-ALL, WHICH IS NOT A DETAIL.**  ``build`` ends
with ``dp.include_router(stale_router)``, a router that claims every callback nobody
above it matched.  A photo router included after it would have every one of its buttons
answered «экран устарел» -- a screen that looks broken while every line of it is correct.
The same ordering is the first line of the patch this position hands over.

**A model that never leaves the machine.**  ``FakeVision`` returns whatever the test puts
in it, including the three failures of §7, which is the only way to produce a
200-that-is-a-refusal or a 429-with-the-money-gone on demand.
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
from aiogram.types import Message

from bot.app import build
from bot.routers import photo as photo_module
from core.services.seeding import seed_catalogue
from infra.llm import LlmAnswer


#: The bytes every flow test "downloads".  FIXED, which is what makes the idempotency
#: tests mean anything: the same photograph sent twice really is the same bytes and
#: therefore the same hash.
PHOTO_BYTES = b"pretend-this-is-a-jpeg"


@pytest.fixture(autouse=True)
def stub_download(monkeypatch):
    """Telegram's file API, stubbed.  Its branching is unit-tested in ``test_intake.py``.

    Autouse and in the CONFTEST rather than in one test file: every file that drives a
    real dispatcher needs it, and a fixture that lives in one of them silently does not
    apply to the next one somebody writes -- which shows up as an ``AttributeError`` from
    inside aiogram rather than as a missing fixture.
    """
    from bot.routers import photo as photo_module

    async def _download(message, bot):
        return PHOTO_BYTES

    monkeypatch.setattr(photo_module, "_download", _download)


@pytest.fixture(autouse=True)
def stub_prepare(monkeypatch):
    """``prepare`` without OpenCV: the flow tests are about the flow, not about pixels.

    The hash it reports is the REAL hash of the REAL bytes -- that part IS the flow.  Only
    ``bot.routers.photo.prepare`` is patched, so anything calling
    ``core.services.raspoznavanie.prepare`` directly still exercises the real pipeline.
    """
    from bot.routers import photo as photo_module
    from core.services.raspoznavanie import Prepared, sha256_of

    def _prepare(raw):
        return Prepared(jpeg=raw, sha256=sha256_of(raw), width=1280, height=720,
                        steps=("stubbed",))

    monkeypatch.setattr(photo_module, "prepare", _prepare)


# --------------------------------------------------------------------- the seeded world

@pytest.fixture
def seeded_connection(connection):
    counts = seed_catalogue(connection)
    connection.commit()
    assert counts.sheets_written == 18 and counts.problems_written == 544
    return connection


# ---------------------------------------------------------------- a recording session

@dataclass
class RecordedCall:
    method: str
    payload: Dict[str, Any]


class RecordingSession(BaseSession):
    """Swallows every Telegram call and remembers it, in order.

    A sibling of ``tests/grid/conftest.py``'s rather than an import of it: a fixture file
    is a file, and two positions writing into one file is the single thing a wave cannot
    do.  The duplication is deliberate and is named in ``## ОТЧЁТ``.
    """

    def __init__(self) -> None:
        super().__init__()
        self.records: List[RecordedCall] = []

    async def make_request(self, bot: Bot, method: TelegramMethod[TelegramType], timeout: int = None):
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
            # A REAL ``Message``, bound to the bot, and not the bare dict P4's sibling
            # fixture returns.  This screen sends «Разбираю бланк…» and then EDITS that
            # message in place, so ``answer()`` has to hand back something with
            # ``edit_text`` on it -- a dict gives an ``AttributeError`` inside the
            # handler, i.e. exactly the shape of failure the real bot would show.
            return Message.model_validate(
                {
                    "message_id": len(self.records),
                    "date": 0,
                    "chat": {"id": method.chat_id, "type": "private"},
                    "from": {"id": method.chat_id, "is_bot": True, "first_name": "bot"},
                    "text": method.text,
                }
            ).as_(bot)
        return True

    async def stream_content(self, *args, **kwargs):  # pragma: no cover
        raise NotImplementedError("the download is stubbed; see _download in the tests")

    async def close(self) -> None:  # pragma: no cover
        pass

    def methods(self) -> List[str]:
        return [record.method for record in self.records]

    def texts(self) -> List[str]:
        return [
            record.payload.get("text") or ""
            for record in self.records
            if record.method in ("SendMessage", "EditMessageText", "AnswerCallbackQuery")
        ]

    def last_markup(self):
        for record in reversed(self.records):
            markup = record.payload.get("reply_markup")
            if markup:
                return markup
        return None


# ------------------------------------------------------------------------- the model

class FakeVision:
    """The vision model, without a network.

    ``answer`` is what ``read_sheet`` returns; ``error`` is what it raises instead.  Both
    are settable per test, which is how the three §7 failures -- a refusal wearing an
    HTTP 200, a 429 with the money gone, a timeout -- are produced on demand.
    """

    def __init__(self, answer=None, error=None) -> None:
        self.answer = answer
        self.error = error
        self.calls = 0
        self.sheets_offered = []

    def read_sheet(self, jpeg, codes, labels, sheets=None):
        self.calls += 1
        self.sheets_offered = list(sheets or [])
        #: The one assertion that belongs in the double: what leaves this machine.
        assert all(code.startswith("u") and code[1:].isdigit() for code in codes), codes
        if self.error is not None:
            raise self.error
        return self.answer or LlmAnswer(raw_text="", rows=(), model="fake", latency_s=0.0)


@pytest.fixture
def vision() -> FakeVision:
    return FakeVision()


# --------------------------------------------------------------------- the dispatcher

@pytest.fixture(scope="session")
def event_loop():
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
def owner_tg_id() -> int:
    return 999999


@pytest.fixture
def roster_path(tmp_path):
    return tmp_path / "roster-photo.db"


@pytest.fixture
def dispatcher(seeded_connection, db_path, roster_path, owner_tg_id, bot_instance, vision):
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

    photo_router, = photo_module.build_routers()
    dp.include_router(photo_router)
    # 🔴 BEFORE the catch-all.  ``build`` includes ``stale-callbacks`` last precisely so
    # that it claims what nobody else matched; a photo router left after it would have
    # every button answered «экран устарел».
    _move_before_catch_all(dp, photo_router)

    dp.workflow_data["bot"] = bot_instance
    dp.workflow_data["vision"] = vision
    yield dp


def _move_before_catch_all(dp: Dispatcher, router) -> None:
    routers = dp.sub_routers
    routers.remove(router)
    index = next(
        (i for i, existing in enumerate(routers) if existing.name == "stale-callbacks"),
        len(routers),
    )
    routers.insert(index, router)


@pytest.fixture
def teacher_tg_id(dispatcher) -> int:
    from core.services.roster import Role

    roster = dispatcher.workflow_data["roster"]
    tg_id = 100500
    roster.confirm_teacher(
        roster.submit_teacher(tg_id=tg_id, surname="Учитель", name="Первый", room="каб-1"),
        role=Role.TEACHER,
    )
    return tg_id


# ---------------------------------------------------------------------- driving updates

def feed_photo(dp, *, bot, from_id, update_id=1, file_id="ph-1", file_size=120_000):
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
                    "photo": [
                        {"file_id": file_id + "-s", "file_unique_id": "s",
                         "width": 320, "height": 180, "file_size": 9_000},
                        {"file_id": file_id, "file_unique_id": "l",
                         "width": 1280, "height": 720, "file_size": file_size},
                    ],
                },
            },
        )
    )


def feed_callback(dp, *, bot, from_id, data, update_id=2, query_id=None):
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
                        "text": "draft",
                    },
                    "data": data,
                },
            },
        )
    )
