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
