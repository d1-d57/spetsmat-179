"""Tests for ``veb/server.py``: GET endpoints and the POST that closes one row.

The server runs against the same SQLite file the rest of the project uses, on a
random localhost port picked by the OS (``port=0`` to ``ThreadingHTTPServer``).
``urllib`` is enough — the page makes no claim on a real HTTP client.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import config
import pytest
from infra.db import apply_migrations, connect

import veb.server as server


@pytest.fixture
def running_server(tmp_path):
    """Boot the server on a tmp database, return its base URL."""
    db_path = tmp_path / "spetsmat.db"
    apply_migrations(db_path, config.MIGRATIONS_DIR)
    connection = connect(db_path)
    sheet_id = connection.execute(
        "insert into sheets (number, title, issued_at, ord) "
        "values (?, ?, ?, ?)",
        ("1", "sheet 1", "2026-09-01", 1),
    ).lastrowid
    # Two teachers, three students, one already enrolled on Monday.
    for i in range(2):
        connection.execute(
            "insert into teachers (name, aka, is_owner) values (?, ?, 0)",
            (f"teacher-{i}", f"t{i}"),
        )
    for i in range(3):
        connection.execute(
            "insert into students (surname, name, class, status, first_sheet_id) "
            "values (?, ?, ?, 'active', ?)",
            (f"surname-{i}", f"name-{i}", "10a", sheet_id),
        )
    # Student 0 is already with teacher-0 on Monday.
    connection.execute(
        "insert into enrollment (student_id, teacher_id, room, weekday, "
        "valid_from, valid_to) values (?, ?, ?, 1, '2026-09-01', ?)",
        (1, 1, "203", config.OPEN_END_DATE),
    )
    connection.commit()

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    httpd.connection = connection  # type: ignore[attr-defined]
    httpd.db_path = str(db_path)   # type: ignore[attr-defined]
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}", connection
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join()
        connection.close()


def _http_get(url: str) -> tuple[int, bytes]:
    with urllib.request.urlopen(url) as r:
        return r.status, r.read()


def _http_post(url: str, payload: dict) -> tuple[int, bytes]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def test_get_root_returns_html(running_server):
    base, _ = running_server
    status, body = _http_get(base + "/")
    assert status == 200
    assert b"<!doctype html>" in body.lower() or b"<html" in body.lower()
    assert b"\xd0\xa8\xd0\xba\xd0\xbe\xd0\xbb\xd1\x8c\xd0\xbd\xd0\xb8\xd0\xba" in body  # «Школьники»


def test_get_view_returns_two_cuts(running_server):
    base, _ = running_server
    status, body = _http_get(base + "/api/view?weekday=1")
    assert status == 200
    payload = json.loads(body)
    assert len(payload["students"]) == 3
    assert len(payload["teachers"]) == 2
    # The two cuts must agree: every assigned student shows up under exactly one teacher.
    teacher_loads = {t["teacher_id"]: t["load"] for t in payload["teachers"]}
    assert teacher_loads[1] == 1  # only student 0 is on teacher-0


def test_post_enrollment_moves_rather_than_overwrites(running_server):
    base, connection = running_server
    status, body = _http_post(base + "/api/enrollment", {
        "student_id": 1, "teacher_id": 2, "weekday": 1,
    })
    assert status == 200, body
    payload = json.loads(body)
    assert "closed" in payload and "opened" in payload

    # The history is the proof: one closed row, one open row, both for student 1.
    rows = connection.execute(
        "select teacher_id, valid_to from enrollment where student_id = 1 order by id"
    ).fetchall()
    assert len(rows) == 2
    assert rows[0]["valid_to"] != config.OPEN_END_DATE  # the old one was closed
    assert rows[1]["valid_to"] == config.OPEN_END_DATE  # the new one is open
    assert rows[0]["teacher_id"] == 1
    assert rows[1]["teacher_id"] == 2


def test_post_enrollment_with_same_teacher_is_a_no_change(running_server):
    base, connection = running_server
    status, body = _http_post(base + "/api/enrollment", {
        "student_id": 1, "teacher_id": 1, "weekday": 1,
    })
    assert status == 200
    payload = json.loads(body)
    assert payload.get("no_change") is True
    # No second row was opened.
    rows = connection.execute(
        "select count(*) from enrollment where student_id = 1"
    ).fetchone()[0]
    assert rows == 1


def test_post_enrollment_validates_input(running_server):
    base, _ = running_server
    status, _ = _http_post(base + "/api/enrollment", {
        "student_id": 1, "weekday": 99,
    })
    assert status == 400