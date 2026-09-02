"""Fixtures for the export and the restore check.

The worlds here are bigger than the five students of ``tests/conftest.py``, and for one
reason: assertion 2 of the restore check is "no fewer than fifty students", so a world of
five could only ever exercise the red branch.  Everything else stays small on purpose --
the bugs in an export live in the mapping of a cell to a sign, and those show up on four
problems as readily as on five hundred.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tests.conftest import seed_world
from core.isotime import to_iso
from core.models import CellState
from core.services.marking import MarkingService
from infra.db import connect
from infra.repositories import SqliteMarkJournal


@pytest.fixture
def malenkiy_mir(connection):
    """Three students, one sheet of four problems -- a grid small enough to read by hand."""
    return seed_world(connection, students=3)


@pytest.fixture
def bolshoy_mir(connection):
    """Fifty-six students, the size the restore check's second assertion is about.

    Built through ``seed_world`` and not through the tool's own probe builder: a check
    verified against the thing that built its input agrees with itself and proves nothing.
    """
    return seed_world(connection, students=56)


@pytest.fixture
def svezhaya_otmetka(connection, bolshoy_mir):
    """One mark dated now, so assertion 3 has something recent to find.

    Written straight into the journal rather than through ``MarkingService``: the service
    stamps ``recorded_at`` from its clock, and what this fixture needs to control is
    ``valid_at`` -- the time the check-off happened, which is the time assertion 3 reads.
    """
    stamp = to_iso(datetime.now(timezone.utc))
    connection.execute(
        "insert into marks (student_id, problem_id, event, valid_at, recorded_at, source) "
        "values (?, ?, 'assert', ?, ?, 'кнопка')",
        (bolshoy_mir.student_ids[0], bolshoy_mir.problem_ids[0], stamp, stamp),
    )
    connection.commit()
    return stamp


@pytest.fixture
def staraya_otmetka(connection, bolshoy_mir):
    """The same, but a month ago -- the state assertion 3 exists to refuse."""
    stamp = to_iso(datetime.now(timezone.utc) - timedelta(days=30))
    connection.execute(
        "insert into marks (student_id, problem_id, event, valid_at, recorded_at, source) "
        "values (?, ?, 'assert', ?, ?, 'импорт')",
        (bolshoy_mir.student_ids[0], bolshoy_mir.problem_ids[0], stamp, stamp),
    )
    connection.commit()
    return stamp


@pytest.fixture
def raznocvetnyy_mir(connection, clock, malenkiy_mir):
    """A world with one cell of every state: SOLVED, RETRACTED and EMPTY.

    All three, because the whole risk of an export is the mapping from state to sign, and
    a fixture that only ever produces pluses cannot tell ``x`` from a blank.
    """
    marking = MarkingService(SqliteMarkJournal(connection), clock)
    students = malenkiy_mir.student_ids
    problems = malenkiy_mir.problem_ids

    marking.set_state(students[0], problems[0], CellState.SOLVED, source="кнопка")
    marking.set_state(students[1], problems[1], CellState.SOLVED, source="кнопка")
    marking.set_state(students[1], problems[1], CellState.RETRACTED, source="кнопка")
    # Given, then struck out as a wrong button: the cell is EMPTY again, and the export
    # must show a blank rather than a leftover plus.
    marking.set_state(students[2], problems[2], CellState.SOLVED, source="кнопка")
    marking.set_state(students[2], problems[2], CellState.EMPTY, source="кнопка")
    return malenkiy_mir


@pytest.fixture
def zakrytaya_baza(connection, db_path):
    """The path to a database whose fixture connection has been closed.

    The tools open their own connections.  Leaving the fixture's write connection open
    would leave a ``-wal`` beside the file and make "the source is byte-identical
    afterwards" a claim about a moving target.
    """
    connection.commit()
    connection.close()
    return db_path


def otkryt(db_path):
    """A fresh connection to a database a tool has just written or read."""
    return connect(db_path)
