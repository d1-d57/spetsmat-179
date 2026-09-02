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
def live_db(tmp_path):
    """A migrated database with the whole seed in it -- 56 students, 18 sheets."""
    path = tmp_path / "spetsmat-text.db"
    applied = apply_migrations(path, config.MIGRATIONS_DIR)
    assert applied, "no migration was applied: the catalogue under test would be empty"
    connection = connect(path)
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
