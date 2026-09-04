"""Tests for the import side of the wave: idempotency, skip rules and source coverage.

The seed world (``tests/conftest.seed_world``) gives five students and two
teachers, which is enough to exercise every branch of the importer without
sharing state with the live database.  The source JSON is built INSIDE the test,
not loaded from disk, so the tests do not depend on the workbook being checked
out.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import config
from infra.db import apply_migrations, connect
from tools.import_raspredelenie import run


def _write_source(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "source.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _seeded_db(tmp_path: Path):
    path = tmp_path / "test.db"
    apply_migrations(path, config.MIGRATIONS_DIR)
    conn = connect(path)
    # Insert ONE sheet so the FK on students.first_sheet_id is satisfied.
    sheet_id = conn.execute(
        "insert into sheets (number, title, issued_at, ord) "
        "values (?, ?, ?, ?)",
        ("1", "sheet 1", "2026-09-01", 1),
    ).lastrowid
    # Five students: surname-0..4, two teachers: teacher-0, teacher-1.
    for i in range(5):
        conn.execute(
            "insert into students (surname, name, class, status, first_sheet_id) "
            "values (?, ?, ?, 'active', ?)",
            (f"surname-{i}", f"name-{i}", "10a", sheet_id),
        )
    for i in range(2):
        conn.execute(
            "insert into teachers (name, aka, is_owner) values (?, ?, 0)",
            (f"teacher-{i}", f"t{i}"),
        )
    conn.commit()
    return conn


def _payload(entries: list[dict], teachers: list[dict] | None = None) -> dict:
    return {
        "prepodavateli": teachers if teachers is not None else [
            {"name": "teacher-0", "room": "203"},
            {"name": "teacher-1", "room": "302"},
            {"name": "teacher-2", "room": "303"},
        ],
        "zakreplenie": entries,
    }


def _open_count(connection, slot: int = 1) -> int:
    return connection.execute(
        "select count(*) from enrollment where slot = ? and valid_to = ?",
        (slot, config.OPEN_END_DATE),
    ).fetchone()[0]


def test_import_assigns_every_resolvable_row(tmp_path):
    conn = _seeded_db(tmp_path)
    try:
        source = _write_source(tmp_path, _payload([
            {"surname": "surname-0", "name": "name-0", "teacher": "teacher-0"},
            {"surname": "surname-1", "name": "name-1", "teacher": "teacher-1"},
            {"surname": "surname-2", "name": "name-2", "teacher": "teacher-0"},
        ]))
        outcomes = run(conn, source, effective_from="2026-09-01")
        assert _open_count(conn) == 3
        assert sum(1 for o in outcomes if o.status == "assigned") == 3
    finally:
        conn.close()


def test_import_is_idempotent(tmp_path):
    conn = _seeded_db(tmp_path)
    try:
        source = _write_source(tmp_path, _payload([
            {"surname": "surname-0", "name": "name-0", "teacher": "teacher-0"},
            {"surname": "surname-1", "name": "name-1", "teacher": "teacher-1"},
        ]))
        run(conn, source, effective_from="2026-09-01")
        first = _open_count(conn)
        # Second pass: nothing should change.
        outcomes = run(conn, source, effective_from="2026-09-01")
        second = _open_count(conn)
        assert first == 2
        assert second == 2
        assert sum(1 for o in outcomes if o.status == "already correct") == 2
    finally:
        conn.close()


def test_import_moves_when_teacher_changes(tmp_path):
    conn = _seeded_db(tmp_path)
    try:
        source = _write_source(tmp_path, _payload([
            {"surname": "surname-0", "name": "name-0", "teacher": "teacher-0"},
        ]))
        run(conn, source, effective_from="2026-09-01")
        # Now change the source: this student is now with teacher-1.
        source2 = _write_source(tmp_path, _payload([
            {"surname": "surname-0", "name": "name-0", "teacher": "teacher-1"},
        ]))
        outcomes = run(conn, source2, effective_from="2026-09-15")
        # Still ONE open row, but the teacher has changed.
        assert _open_count(conn) == 1
        row = conn.execute(
            "select teacher_id from enrollment where valid_to = ?", (config.OPEN_END_DATE,),
        ).fetchone()
        assert row["teacher_id"] == 2  # teacher-1
        assert any(o.status == "moved" for o in outcomes)
        # And there is a closed row too: history must survive the move.
        closed = conn.execute(
            "select count(*) from enrollment where valid_to < ?", (config.OPEN_END_DATE,),
        ).fetchone()[0]
        assert closed == 1
    finally:
        conn.close()


def test_import_splits_composite_teacher_into_two_rows(tmp_path):
    """A name with a slash in the source opens ONE row per PART on a different day.

    The page is the path back: the owner sees both rows and can move either one
    independently.  If the catalogue only knows ONE of the parts, the import
    still opens the row it knows about and names the missing part in the report.
    """
    conn = _seeded_db(tmp_path)
    try:
        # ``_seeded_db`` already created two teachers (id=1, 2).  Add a third so the
        # composite's BOTH halves resolve cleanly.
        conn.execute(
            "insert into teachers (name, aka, is_owner) values (?, ?, 0)",
            ("teacher-2", "t2"),
        )
        conn.commit()

        source = _write_source(tmp_path, _payload([
            {"surname": "surname-0", "name": "name-0",
             "teacher": "teacher-0 / teacher-2"},
        ], teachers=[
            {"name": "teacher-0", "room": "203"},
            {"name": "teacher-1", "room": "302"},
            {"name": "teacher-2", "room": "303"},
        ]))
        outcomes = run(conn, source, effective_from="2026-09-01")

        # Two ASSIGNED outcomes, one per resolved part.
        assigned = [o for o in outcomes if o.status == "assigned"]
        assert len(assigned) == 2, [o.line() for o in outcomes]
        # And the rows live on DIFFERENT slots — Monday (slot 1) AND Thursday (slot 2).
        open_rows = conn.execute(
            "select slot, teacher_id from enrollment "
            "where valid_to = ? order by slot", (config.OPEN_END_DATE,),
        ).fetchall()
        assert len(open_rows) == 2
        slots = sorted(row["slot"] for row in open_rows)
        assert slots == [1, 2]
        teacher_ids = sorted(row["teacher_id"] for row in open_rows)
        # teacher-0 is id=1, teacher-2 is id=3.
        assert teacher_ids == [1, 3]
    finally:
        conn.close()


def test_import_records_missing_part_of_composite(tmp_path):
    """A composite whose one half is unknown: open the known half, name the rest."""
    conn = _seeded_db(tmp_path)
    try:
        # ``_seeded_db`` already has two teachers (id=1, 2).  We don't add a third —
        # "ghost" must NOT resolve.
        source = _write_source(tmp_path, _payload([
            {"surname": "surname-0", "name": "name-0",
             "teacher": "teacher-0 / ghost"},
        ]))
        outcomes = run(conn, source, effective_from="2026-09-01")

        # One row opened (the half we know), one row named as missing.
        assigned = [o for o in outcomes if o.status == "assigned"]
        skipped = [o for o in outcomes if o.status == "skipped"]
        assert len(assigned) == 1
        assert len(skipped) == 1
        assert skipped[0].teacher == "ghost"
        assert conn.execute(
            "select count(*) from enrollment where valid_to = ?", (config.OPEN_END_DATE,),
        ).fetchone()[0] == 1
    finally:
        conn.close()


def test_import_treats_slash_in_catalogue_name_as_single_teacher(tmp_path):
    """A name with a slash that resolves as-is to the catalogue is ONE teacher.

    "Мика/Вася" in the source is the catalogue's "Мика/Вася" — one person, one row.
    A naive split would have invented two non-existent people.
    """
    conn = _seeded_db(tmp_path)
    try:
        # ``_seeded_db`` already has two teachers (id=1, 2).  Add the slash-bearing one
        # as id=3.
        conn.execute(
            "insert into teachers (name, aka, is_owner) values (?, ?, 0)",
            ("mika/vasya", "mv"),
        )
        conn.commit()

        source = _write_source(tmp_path, _payload([
            {"surname": "surname-0", "name": "name-0", "teacher": "mika/vasya"},
        ], teachers=[
            {"name": "teacher-0", "room": "203"},
            {"name": "teacher-1", "room": "302"},
            {"name": "mika/vasya", "room": "302"},
        ]))
        outcomes = run(conn, source, effective_from="2026-09-01")

        # One row, one assigned, on Monday (single-teacher path).
        assigned = [o for o in outcomes if o.status == "assigned"]
        assert len(assigned) == 1
        open_rows = conn.execute(
            "select teacher_id from enrollment where valid_to = ?",
            (config.OPEN_END_DATE,),
        ).fetchall()
        assert len(open_rows) == 1
        # The slash-bearing teacher is the third one we just inserted.
        assert open_rows[0]["teacher_id"] == 3
    finally:
        conn.close()


def test_import_skips_unknown_student(tmp_path):
    conn = _seeded_db(tmp_path)
    try:
        source = _write_source(tmp_path, _payload([
            {"surname": "surname-0", "name": "name-0", "teacher": "teacher-0"},
            {"surname": "no-such-kid", "name": "ghost", "teacher": "teacher-0"},
        ]))
        outcomes = run(conn, source, effective_from="2026-09-01")
        assert _open_count(conn) == 1
        assert sum(1 for o in outcomes if o.status == "assigned") == 1
        assert any(
            o.status == "skipped" and "no student" in o.reason for o in outcomes
        )
    finally:
        conn.close()


def test_import_skips_unknown_teacher(tmp_path):
    conn = _seeded_db(tmp_path)
    try:
        source = _write_source(tmp_path, _payload([
            {"surname": "surname-0", "name": "name-0", "teacher": "ghost-teacher"},
        ]))
        outcomes = run(conn, source, effective_from="2026-09-01")
        assert _open_count(conn) == 0
        assert outcomes[0].status == "skipped"
        assert "no teacher" in outcomes[0].reason
    finally:
        conn.close()


def test_dry_run_writes_nothing(tmp_path):
    conn = _seeded_db(tmp_path)
    try:
        source = _write_source(tmp_path, _payload([
            {"surname": "surname-0", "name": "name-0", "teacher": "teacher-0"},
        ]))
        run(conn, source, effective_from="2026-09-01", dry_run=True)
        assert _open_count(conn) == 0
    finally:
        conn.close()