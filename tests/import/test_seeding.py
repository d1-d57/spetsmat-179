"""The seed loads, loads once, and refuses what the schema would refuse."""

from __future__ import annotations

import json

import pytest

import config
from core.services.seeding import (
    DUPLICATE_LABEL_REPAIRS,
    SeedError,
    read_sheets,
    read_students,
    read_teachers,
    repairs_applied,
    seed_catalogue,
)


def test_the_seed_lands_whole(connection, seed_dir):
    counts = seed_catalogue(connection)
    assert counts.sheets_written == 3
    assert counts.problems_written == 7
    assert counts.students_written == 3
    assert counts.teachers_written == 3
    assert connection.execute("select count(*) from problems").fetchone()[0] == 7


def test_seeding_twice_writes_nothing_the_second_time(connection, seed_dir):
    """A re-run during a season must not double the catalogue.

    The counts distinguish 'seen' from 'written' precisely so that this is visible: a
    loader that printed only 'seeded 3 students' could not tell a fresh load from a
    doubled one.
    """
    first = seed_catalogue(connection)
    second = seed_catalogue(connection)

    assert first.problems_written == 7
    assert second.problems_written == 0
    assert second.students_written == 0
    assert second.problems_seen == first.problems_seen
    assert connection.execute("select count(*) from problems").fetchone()[0] == 7


def test_an_unknown_problem_kind_is_refused_before_the_first_insert(connection, seed_dir):
    """Judged whole, not halfway through: the CHECK constraint would also refuse this,
    but it would refuse it after some rows had already landed."""
    path = seed_dir / "sheets.json"
    sheets = json.loads(path.read_text(encoding="utf-8"))
    sheets[0]["tasks"][0]["kind"] = "суперзвезда"
    path.write_text(json.dumps(sheets, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(SeedError) as raised:
        seed_catalogue(connection)
    assert "суперзвезда" in str(raised.value)
    assert connection.execute("select count(*) from sheets").fetchone()[0] == 0


def test_a_duplicate_label_not_in_the_registry_is_refused(connection, seed_dir):
    """The schema declares unique (sheet_id, label); a silent 'keep the first' would drop
    a problem out of the count and look exactly like a clean load."""
    path = seed_dir / "sheets.json"
    sheets = json.loads(path.read_text(encoding="utf-8"))
    sheets[0]["tasks"][1]["label"] = sheets[0]["tasks"][0]["label"]
    path.write_text(json.dumps(sheets, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(SeedError) as raised:
        seed_catalogue(connection)
    assert "DUPLICATE_LABEL_REPAIRS" in str(raised.value)


def test_a_missing_seed_file_says_which_one(seed_dir):
    (seed_dir / "students.csv").unlink()
    with pytest.raises(SeedError) as raised:
        read_students()
    assert "students.csv" in str(raised.value)


def test_students_are_active_and_have_no_first_sheet_yet(connection, seed_dir):
    """``first_sheet_id`` is left NULL by the SEED and filled by the IMPORT from the book.

    The seed carries a ``first_sheet`` column, and using it here would make the importer's
    later comparison against that column a comparison of the column with itself.
    """
    seed_catalogue(connection)
    rows = connection.execute("select status, first_sheet_id from students").fetchall()
    assert {row["status"] for row in rows} == {"active"}
    assert all(row["first_sheet_id"] is None for row in rows)


# ------------------------------------------------------- the real seed, which is in git


def test_the_real_seed_is_the_544_problems_the_задание_names():
    """Read from ``seed/`` in the repository, not from the synthetic fixture."""
    sheets = read_sheets(config.ROOT / "seed")
    tasks = [task for sheet in sheets for task in sheet["tasks"]]
    kinds = {kind: sum(1 for task in tasks if task["kind"] == kind)
             for kind in config.PROBLEM_KINDS}

    assert len(sheets) == 18
    assert len(tasks) == 544
    assert kinds == {"обязательная": 215, "обычная": 288, "звезда": 39, "двойная": 2}
    assert len(read_students(config.ROOT / "seed")) == 56
    assert len(read_teachers(config.ROOT / "seed")) == 18


def test_the_one_duplicate_in_the_real_seed_is_the_one_in_the_registry():
    """``2д`` carries ``12д`` twice.  The repair restores the letter the run is missing.

    Both duplicate columns are empty over all 55 students, so the assignment cannot
    misattribute a mark; the check here is that the repair is the ONLY one and that it is
    applied, not that it is harmless -- that was measured separately.

    The SET is asserted and not the ORDER, and that is deliberate.  After the repair the
    seven columns read ``12а 12б 12в 12г 12е 12д 12ж`` -- the letters are all present and
    distinct, but ``12д`` and ``12е`` still stand transposed in the book.  Sorting them
    here would be this file quietly editing the source; the transposition is a fact about
    the workbook, it costs nothing (both columns concerned are empty), and it is recorded
    rather than tidied away.
    """
    sheets = read_sheets(config.ROOT / "seed")
    assert repairs_applied(sheets) == [("2д", "12д", "12г")]
    assert len(DUPLICATE_LABEL_REPAIRS) == 1

    labels = [task["label"] for sheet in sheets if sheet["number"] == "2д"
              for task in sheet["tasks"]]
    assert len(labels) == len(set(labels))
    run = [label for label in labels if label.startswith("12")]
    assert sorted(run) == ["12а", "12б", "12в", "12г", "12д", "12е", "12ж"]
    assert run == ["12а", "12б", "12в", "12г", "12е", "12д", "12ж"]
