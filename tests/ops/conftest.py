"""A realistic database for the harness tests: fifty-six students and a fresh mark.

The harness tests are not unit tests over a five-student toy world like ``tests/conftest.py``
builds -- they assert the very thresholds the restore check asserts in production ("no
fewer than fifty students", "the latest mark is not older than a week").  A world of five
students could not tell a working check from a check that always passes.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from infra.db import apply_migrations, connect

#: The real cohort, so that the ">= 50 students" threshold is exercised near its edge and
#: not two orders of magnitude away from it.
STUDENT_COUNT = 56


def _iso(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.fixture
def zhivaya_baza(tmp_path: Path) -> Path:
    """A migrated FILE database in WAL mode, populated the way the live one is.

    A FILE and not ``:memory:``: WAL is the whole point, and the backup path under test
    depends on WAL behaving the way it behaves in production.
    """
    database = tmp_path / "spetsmat.db"
    apply_migrations(database)
    connection = connect(database)
    now = datetime.now(tz=timezone.utc)
    try:
        connection.execute(
            "insert into sheets (id, number, title, issued_at, ord) values (1, '1', 'sheet one', ?, 1)",
            (_iso(now - timedelta(days=30)),),
        )
        connection.execute(
            "insert into problems (id, sheet_id, label, kind, ord) values (1, 1, '1', 'обязательная', 1)"
        )
        connection.execute("insert into teachers (id, name, is_owner) values (1, 'teacher', 1)")
        for number in range(1, STUDENT_COUNT + 1):
            connection.execute(
                "insert into students (id, surname, name, class, status, first_sheet_id) "
                "values (?, ?, ?, '8', 'active', 1)",
                (number, "surname%02d" % number, "name%02d" % number),
            )
        # One mark, yesterday: inside the "not older than a week" window by a wide margin,
        # so a test that moves it out of the window moves it deliberately.
        connection.execute(
            "insert into marks (student_id, problem_id, event, teacher_id, valid_at, recorded_at, source) "
            "values (1, 1, 'assert', 1, ?, ?, 'кнопка')",
            (_iso(now - timedelta(days=1)), _iso(now - timedelta(days=1))),
        )
    finally:
        connection.close()
    return database


@pytest.fixture
def papka_kopij(tmp_path: Path) -> Path:
    directory = tmp_path / "backups"
    directory.mkdir()
    return directory
