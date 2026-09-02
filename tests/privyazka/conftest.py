"""The world these tests run in: the REAL catalogue of fifty-six, not a made-up five.

WHY THE REAL NAMES.  The hole this position closes was found on live data, and the
thing that decides whether it is closed is whether fifty-six real Russian surnames can
each be told apart from the other fifty-five.  A catalogue of «surname-0 … surname-4»
proves nothing about that: those five differ in one digit and any threshold separates
them.  ``seed/students.csv`` is the file the season was loaded from, so the fixtures
read it rather than restating it -- a copy would drift the day a child joins.

The two files are the production two: the migrated journal from ``tests/conftest.py``
and a roster SQLite beside it.  No fake port anywhere in this directory -- a fake would
have let the binding pass while the schema's ``tg_id`` UNIQUE refused it.
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

import pytest

from core.services.progress import ProgressService
from core.services.roster import RosterService
from infra.db import connect
from infra.repositories import SqliteCatalogue, SqliteMarkJournal
from infra.roster_repo import RosterRepo

#: The list the season was loaded from.  Read, never restated.
SEED_CSV = Path(__file__).resolve().parents[2] / "seed" / "students.csv"

#: Sheets and problems per sheet.  18 × 12 = 216 problem cells, which is the smallest
#: grid that can hold Пирогов's two hundred and one marks and still leave some empty.
SHEETS = 18
PROBLEMS_PER_SHEET = 12

#: The child the whole position is named after in the brief.
PIROGOV = ("Пирогов", "Константин")

#: How many marks he carries into this year.  The number is from the live base.
PIROGOV_MARKS = 201


def seed_names() -> list:
    """``[(surname, name), ...]`` for the whole live catalogue, in file order."""
    with SEED_CSV.open(encoding="utf-8") as handle:
        return [(row["surname"], row["name"]) for row in csv.DictReader(handle)]


@pytest.fixture
def names() -> list:
    rows = seed_names()
    assert len(rows) == 56, "the season has 56 students; the seed file has %d" % len(rows)
    return rows


@pytest.fixture
def full_catalogue(connection, names) -> dict:
    """Sheets, problems and all fifty-six students -- ``active``, with NO ``tg_id``.

    ``first_sheet_id`` is the FIRST sheet for everybody except Пирогов, who starts at
    sheet 6.  That is the live shape and it is what makes the «do not touch
    first_sheet_id» assertion able to fail: rewriting it to today's sheet would move
    him from sheet 6 to sheet 18 and the test would see it.
    """
    sheet_ids: list = []
    problem_ids: list = []
    for sheet_index in range(SHEETS):
        cursor = connection.execute(
            "insert into sheets (number, title, issued_at, ord) values (?, ?, ?, ?)",
            ("%d" % (sheet_index + 1), "листок %d" % (sheet_index + 1),
             "2025-%02d-01" % (sheet_index % 12 + 1), sheet_index + 1),
        )
        sheet_ids.append(cursor.lastrowid)
        for problem_index in range(PROBLEMS_PER_SHEET):
            problem = connection.execute(
                "insert into problems (sheet_id, label, kind, ord) values (?, ?, ?, ?)",
                (cursor.lastrowid, "%d.%d" % (sheet_index + 1, problem_index + 1),
                 "обязательная", problem_index + 1),
            )
            problem_ids.append(problem.lastrowid)

    student_ids: dict = {}
    for surname, name in names:
        first_sheet = sheet_ids[5] if (surname, name) == PIROGOV else sheet_ids[0]
        cursor = connection.execute(
            "insert into students (surname, name, class, status, first_sheet_id) "
            "values (?, ?, ?, 'active', ?)",
            (surname, name, None, first_sheet),
        )
        student_ids[(surname, name)] = cursor.lastrowid

    connection.execute(
        "insert into teachers (name, aka, is_owner) values (?, ?, 0)", ("Учитель", "У")
    )
    connection.execute(
        "insert into sessions (held_on, kind) values (?, ?)", ("2026-09-02", "обычное")
    )
    return {
        "sheet_ids": sheet_ids,
        "problem_ids": problem_ids,
        "student_ids": student_ids,
        "first_sheet_of_pirogov": sheet_ids[5],
    }


@pytest.fixture
def pirogov_marks(connection, full_catalogue) -> int:
    """Give Пирогов his two hundred and one marks, on the real journal.

    Written as ``импорт`` rows, which is what last year's load produced -- the whole
    reason the binding has to find HIS row and not make a new one.
    """
    student_id = full_catalogue["student_ids"][PIROGOV]
    problems = full_catalogue["problem_ids"][:PIROGOV_MARKS]
    assert len(problems) == PIROGOV_MARKS
    for index, problem_id in enumerate(problems):
        connection.execute(
            "insert into marks (student_id, problem_id, event, valid_at, recorded_at, source) "
            "values (?, ?, 'assert', ?, ?, 'импорт')",
            (student_id, problem_id,
             "2025-10-01T10:00:%02dZ" % (index % 60),
             "2025-10-01T10:00:%02dZ" % (index % 60)),
        )
    return student_id


@pytest.fixture
def roster_db(tmp_path) -> sqlite3.Connection:
    path = tmp_path / "roster-privyazka.db"
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def repo(connection, roster_db) -> RosterRepo:
    return RosterRepo(connection, roster_db)


@pytest.fixture
def current_sheet(full_catalogue):
    """The sheet a NEWLY created student would be anchored to: the last one issued."""
    return full_catalogue["sheet_ids"][-1]


@pytest.fixture
def roster(repo, current_sheet) -> RosterService:
    return RosterService(repo, sheets_for_current=lambda: current_sheet)


@pytest.fixture
def progress(connection) -> ProgressService:
    return ProgressService(SqliteMarkJournal(connection), SqliteCatalogue(connection))


def tg_for(index: int) -> int:
    """A stable Telegram id per catalogue position, well clear of the real ones."""
    return 7_700_000 + index


# --------------------------------------------------------------- the live screen
#
# «Показать владельцу кнопки» is a claim about a SCREEN, and a service-level assertion
# cannot see whether a button was drawn.  These fixtures build the production
# dispatcher over the same two files the fixtures above seeded, and reuse the recording
# session P3 already wrote rather than a second one that would drift from it.

@pytest.fixture(scope="session")
def event_loop():
    import asyncio

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def owner_tg_id() -> int:
    return 999_999


@pytest.fixture
def recorder():
    from tests.bot.conftest import _RecordingSession

    return _RecordingSession()


@pytest.fixture
def bot_instance(recorder):
    from aiogram import Bot

    return Bot(token="0:fake", session=recorder)


@pytest.fixture
def dispatcher(db_path, tmp_path, owner_tg_id, bot_instance, full_catalogue):
    """The production dispatcher over the seeded journal.

    The routers keep their ``Router`` objects as module globals and were attached to
    the dispatcher of the previous test; detaching them here is what P3's own bot
    conftest does, for the same reason.
    """
    from bot.app import build
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
        roster_path=tmp_path / "roster-screen.db",
        bot=bot_instance,
    )
    dp.workflow_data["bot"] = bot_instance
    yield dp
