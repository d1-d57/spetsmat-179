"""Tests for `veb/razdely/kartochka.py` and its route on `veb/server.py`.

Boots the full `veb.server.Handler`, the way `tests/veb/test_server.py` does — the
card's route lives in `do_GET` itself, not in a `marshruty()` seam, and a test built
against `veb.priyom.marshruty()` directly would never exercise it.
"""

from __future__ import annotations

import json
import os
import re
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import config
import pytest
from infra.db import apply_migrations, connect

os.environ.setdefault("SPETSMAT_VEB_SECRET", "test-secret-key-32bytes!")

import veb.server as server
from veb import vhod


@pytest.fixture
def running_server(tmp_path):
    """One sheet with two problems, one teacher in group В with a room, one pupil."""
    db_path = tmp_path / "spetsmat.db"
    apply_migrations(db_path, config.MIGRATIONS_DIR)
    connection = connect(db_path)
    sheet_id = connection.execute(
        "insert into sheets (number, title, issued_at, ord) values (?, ?, ?, ?)",
        ("1", "листок 1", "2026-09-01", 1),
    ).lastrowid
    problem_ids = [
        connection.execute(
            "insert into problems (sheet_id, label, kind, ord) values (?, ?, 'обязательная', ?)",
            (sheet_id, label, i),
        ).lastrowid
        for i, label in enumerate(("1", "2"), start=1)
    ]
    teacher_id = connection.execute(
        "insert into teachers (name, aka, is_owner) values ('Пирогов', 'pir', 0)"
    ).lastrowid
    # `gruppa` is a lazily-added column on the live база (`pragma table_info` on
    # `data/spetsmat.db` shows it; no migration declares it) — added here the same
    # way, on the tmp база this test owns.
    connection.execute("alter table teachers add column gruppa text")
    connection.execute("update teachers set gruppa = 'В' where id = ?", (teacher_id,))
    student_id = connection.execute(
        "insert into students (surname, name, class, status, first_sheet_id) "
        "values ('Фефелов', 'Иван', '9К', 'active', ?)", (sheet_id,),
    ).lastrowid
    connection.execute(
        "insert into enrollment (student_id, teacher_id, room, slot, valid_from, valid_to) "
        "values (?, ?, '307', 1, '2026-09-01', ?)",
        (student_id, teacher_id, config.OPEN_END_DATE),
    )
    # 🔴 THE ROOM ON THE CARD COMES FROM `kabinet_na_den`, NOT FROM `enrollment.room`.
    # `server._build_views` always overwrites the room with the group's room-for-today
    # (`kabinet_na_den`, possibly empty), even though it read `enrollment.room` first —
    # see `_kabinety_grupp`'s own docstring: "нет строки на дату — кабинета на этот
    # день нет, и это законный случай". Matching that here rather than fighting it.
    # 🔴 `gruppy.kod` ON A FRESH МИГРАЦИЯ IS «ИЯ»/«ДМ»/«НС», NOT «В»/«Д»/«Н» —
    # migration 005 seeds the old initials; the live база carries the letters
    # (`sqlite3 data/spetsmat.db "select * from gruppy"` → В/Д/Н) from a data fix
    # outside `migrations/`, which every other place in this codebase (`server.py`,
    # `shkolniki.py`, `karkas.py`) already assumes. Matched here, not re-litigated.
    connection.execute("update gruppy set kod = 'В' where kod = 'ИЯ'")
    from datetime import date as _date
    connection.execute(
        "insert into kabinet_na_den (data, gruppa, kabinet) values (?, 'В', '307')",
        (_date.today().isoformat(),),
    )
    connection.commit()

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    httpd.db_path = str(db_path)  # type: ignore[attr-defined]
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield {"baza": f"http://127.0.0.1:{port}", "student": student_id,
               "zadachi": problem_ids, "teacher": teacher_id}
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join()
        connection.close()


def _kuka(rol: str, kto=None) -> str:
    return f"{vhod.COOKIE_NAME}={vhod._make_cookie(rol, kto)}"


def _get(url: str, cookie: str | None = None) -> tuple[int, bytes]:
    headers = {"Cookie": cookie} if cookie else {}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _post(url: str, payload: dict, cookie: str) -> tuple[int, bytes]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json", "Cookie": cookie})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def test_guest_sees_only_the_top_of_the_card(running_server):
    """Класс · группа · кабинет · принимающий — и ни одной галочки."""
    base = running_server["baza"]
    status, body = _get(f'{base}/kartochka/{running_server["student"]}')
    assert status == 200
    telo = body.decode("utf-8")
    assert "Фефелов" in telo and "Иван" in telo
    assert "9К" in telo
    assert "В" in telo, "группа принимающего видна гостю"
    assert "307" in telo, "кабинет виден гостю"
    assert "Пирогов" in telo, "принимающий виден гостю"
    # The readiness criterion, verbatim: "гостю НЕ пришло ни одной галочки" — a
    # grep of the body, not an inference from role.
    assert "Задачи" not in telo, "у гостя нет раздела задач вовсе"
    assert "kl solved" not in telo and "kl empty" not in telo and "kl retracted" not in telo
    assert "data-u=" not in telo, "у гостя нет ни одной ставящей отметку кнопки"


@pytest.mark.parametrize("rol,kto", [("organizator", None), ("prepod", 1)])
def test_signed_in_viewer_sees_marks_and_can_tick_them(running_server, rol, kto):
    """Вошедший (организатор или преподаватель) видит задачи и может их отмечать."""
    base = running_server["baza"]
    sid = running_server["student"]
    cookie = _kuka(rol, kto)
    status, body = _get(f"{base}/kartochka/{sid}", cookie)
    assert status == 200
    telo = body.decode("utf-8")
    assert "Задачи" in telo
    assert f'data-u="{sid}"' in telo, "клетки несут id школьника — есть чем тапнуть"

    problem_id = running_server["zadachi"][0]
    status, body = _post(f"{base}/api/priyom",
                         {"student": sid, "problem": problem_id, "target": "solved"},
                         cookie)
    assert status == 200, body
    otvet = json.loads(body)
    assert otvet["sostoyanie"] == "solved"

    # Перечитать карточку: клетка теперь несёт класс `solved` и галочку.
    status, body = _get(f"{base}/kartochka/{sid}", cookie)
    telo = body.decode("utf-8")
    assert re.search(r'class="kl solved"[^>]*data-z="%d"' % problem_id, telo), (
        "после отметки клетка задачи 1 показывает состояние solved")


def test_unknown_pupil_is_a_404(running_server):
    base = running_server["baza"]
    status, _body = _get(f"{base}/kartochka/999999")
    assert status == 404


def test_card_carries_an_exit(running_server):
    """Крестик выхода обязателен — владелец отдельно попросил, чем уйти."""
    base = running_server["baza"]
    status, body = _get(f'{base}/kartochka/{running_server["student"]}')
    assert status == 200
    telo = body.decode("utf-8")
    assert 'class="zakryt"' in telo and 'href="/raspredelenie"' in telo
