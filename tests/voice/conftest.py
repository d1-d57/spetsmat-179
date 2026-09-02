"""The world the voice tests work against: the REAL roster and the REAL sheets.

Not the five-student world of ``tests/conftest.py``.  Every failure this path has is a
collision between two children who sound alike or two labels that print alike, and a
world of five never collides.  The seed carries fifty-six surnames and 544 problems and
is in git precisely so that a test can be run over all of them.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass

import pytest

import config


@dataclass(frozen=True)
class SeedStudent:
    """Only what the matching channels read: an id and a surname."""

    id: int
    surname: str
    name: str = ""


@dataclass(frozen=True)
class SeedProblem:
    id: int
    label: str
    sheet_ord: int


@pytest.fixture(scope="session")
def roster() -> list:
    """All fifty-six children of the anonymised seed, with stable ids."""
    with open(config.SEED_DIR / "students.csv", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return [
        SeedStudent(id=index + 1, surname=row["surname"], name=row["name"])
        for index, row in enumerate(rows)
    ]


@pytest.fixture(scope="session")
def sheets() -> list:
    with open(config.SEED_DIR / "sheets.json", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="session")
def problems(sheets) -> list:
    """All 544 problems, ids assigned in sheet order exactly as the importer does."""
    out = []
    problem_id = 1
    for sheet in sorted(sheets, key=lambda s: s["ord"]):
        for task in sheet["tasks"]:
            out.append(SeedProblem(id=problem_id, label=task["label"], sheet_ord=sheet["ord"]))
            problem_id += 1
    return out


@pytest.fixture(scope="session")
def last_sheet_problems(problems, sheets) -> list:
    """The problems of the sheet being worked on now -- the largest ``ord``."""
    last = max(sheet["ord"] for sheet in sheets)
    return [problem for problem in problems if problem.sheet_ord == last]


# =============================================================================
#  A DISPATCHER FOR THE VOICE SCREEN
# =============================================================================
#
# ⚠ WIRED HERE RATHER THAN THROUGH ``bot.app.build``, and the reason is a fact about this
# position rather than a preference: ``bot/app.py`` is outside its zone, so the voice
# router is not included there, and a dispatcher built by ``build()`` would answer every
# voice callback with the stale catch-all.  What this file wires is therefore the
# PROPOSED wiring — the same middleware, the same services, the voice router in the place
# the docstring of ``bot/routers/voice.py`` says it must go.  When the include lands in
# ``bot/app.py`` this fixture should be replaced by ``build()``; that is named in the
# report and is not a licence to leave it here forever.

import asyncio
from typing import Any, Dict, List

from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.methods import AnswerCallbackQuery, SendMessage, TelegramMethod
from aiogram.methods.base import TelegramType

from bot.middleware import AuthMiddleware
from bot.routers import voice as voice_module
from core.services.marking import MarkingService
from core.services.roster import Role, RosterService
from core.services.seeding import seed_catalogue
from infra.asr import FakeTranscriber
from infra.db import SystemClock
from infra.repositories import SqliteCatalogue, SqliteMarkJournal
from infra.roster_repo import RosterRepo


@dataclass
class RecordedCall:
    method: str
    payload: Dict[str, Any]


class RecordingSession(BaseSession):
    """Swallows every Telegram call and remembers it, in order.

    A sibling of the ones under ``tests/bot/`` and ``tests/grid/`` rather than an import
    of either: a conftest is a file, and two positions writing into one file is the single
    thing a wave cannot do.  The duplication is deliberate and named in ``## ОТЧЁТ``.
    """

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
def seeded_connection(connection):
    """A migrated database carrying the whole anonymised seed: 18 sheets, 544 problems."""
    counts = seed_catalogue(connection)
    connection.commit()
    assert counts.problems_written == 544, counts
    return connection


@pytest.fixture
def transcript_script() -> dict:
    """What the scripted recogniser answers, keyed by the audio bytes a test sends."""
    return {}


@pytest.fixture
def transcriber(transcript_script) -> FakeTranscriber:
    return FakeTranscriber(transcript_script)


@pytest.fixture
def voice_dispatcher(seeded_connection, db_path, tmp_path, bot_instance, transcriber):
    """The proposed wiring, as a dispatcher: auth, the services, the voice router."""
    repo = RosterRepo.open(journal_path=db_path, roster_path=tmp_path / "roster-voice.db")
    catalogue = SqliteCatalogue(repo._journal)  # noqa: SLF001 -- shared connection
    roster = RosterService(
        repo, sheets_for_current=lambda: max(catalogue.sheets(), key=lambda s: s.ord).id
    )
    marking = MarkingService(SqliteMarkJournal(repo._journal), SystemClock())

    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(AuthMiddleware(roster, owner_tg_id=999999))
    dp.callback_query.middleware(AuthMiddleware(roster, owner_tg_id=999999))
    dp.include_router(voice_module.build_router())
    dp.workflow_data.update(
        {
            "catalogue": catalogue,
            "marking": marking,
            "roster": roster,
            "transcriber": transcriber,
            "download": _download_from_file_id,
            "schema_extractor": None,
            "bot": bot_instance,
        }
    )
    yield dp


async def _download_from_file_id(bot, file_id: str) -> bytes:
    """The download seam, scripted: the test names the audio by putting it in the file id.

    Injected rather than mocked at the aiogram layer, so that the handler's own bytes ->
    digest -> transcript chain is the one under test.
    """
    return file_id.encode("utf-8")


@pytest.fixture
def teacher_tg_id(voice_dispatcher) -> int:
    """A confirmed teacher, made through ``RosterService`` so the identity is production's."""
    roster = voice_dispatcher.workflow_data["roster"]
    tg_id = 100500
    roster.confirm_teacher(
        roster.submit_teacher(tg_id=tg_id, surname="Учитель", name="Первый", room="каб-1"),
        role=Role.TEACHER,
    )
    return tg_id


@pytest.fixture
def catalogue(voice_dispatcher):
    return voice_dispatcher.workflow_data["catalogue"]


@pytest.fixture
def marking(voice_dispatcher):
    return voice_dispatcher.workflow_data["marking"]


def feed_voice(dp, *, bot, from_id: int, file_id: str, update_id: int = 1,
               file_size: int = 4096, duration: int = 5):
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
                    "voice": {
                        "file_id": file_id,
                        "file_unique_id": file_id,
                        "duration": duration,
                        "mime_type": "audio/ogg",
                        "file_size": file_size,
                    },
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
