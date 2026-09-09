"""Tests for ``veb/server.py``: GET endpoints and the POST that closes one row.

The server runs against the same SQLite file the rest of the project uses, on a
random localhost port picked by the OS (``port=0`` to ``ThreadingHTTPServer``).
``urllib`` is enough — the page makes no claim on a real HTTP client.
"""

from __future__ import annotations

import re
import json
import os
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import config
import pytest
from infra.db import apply_migrations, connect

# The entry glue landed after these tests were written: every page below /vhod now
# answers an ANONYMOUS request with the login form, which is correct behaviour and made
# five assertions here fail against the old contract.  So the tests authenticate the
# way a browser does -- a signed cookie in the request -- instead of asserting the
# pre-auth contract.  A signing secret must exist before that cookie can be minted; any
# value does, this is not the production one.
os.environ.setdefault("SPETSMAT_VEB_SECRET", "test-secret-key-32bytes!")

import veb.server as server
from veb import vhod


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
        "insert into enrollment (student_id, teacher_id, room, slot, "
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


def _kuka() -> str:
    """A valid organiser cookie, exactly as /vhod would hand one to a browser."""
    return f"{vhod.COOKIE_NAME}={vhod._make_cookie('organizator')}"


def _http_get(url: str) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"Cookie": _kuka()})
    with urllib.request.urlopen(req) as r:
        return r.status, r.read()


def _http_post(url: str, payload: dict) -> tuple[int, bytes]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json", "Cookie": _kuka()},
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def test_raspredelenie_opens_on_a_dated_lesson_and_not_on_the_standing_one(running_server):
    """The owner's guard: «чтобы ты случайно всё не начинал править постоянное».

    This test used to assert that ``/raspredelenie`` serves the standing-arrangement
    editor.  It now asserts the opposite, and that is the point of the change: after
    2026-09-07, when a one-day move had to be written into the standing table because
    there was nowhere else, opening on that table by default is the defect.
    """
    base, _ = running_server
    status, body = _http_get(base + "/raspredelenie")
    assert status == 200
    telo = body.decode("utf-8")
    assert "<!doctype html>" in telo.lower()
    # A date is on the page: that is what tells the reader which lesson he is editing.
    assert re.search(r"\d{4}-\d{2}-\d{2}", telo), "the lesson screen must carry its date"
    # And the standing editor is reachable, but only through its own address.
    assert "/raspredelenie/postoyannoe" in telo

    # 🔴 THE LESSON SCREEN IS THE SAME SCREEN AS THE STANDING ONE, AND THAT IS THE
    # OWNER'S DECISION OF 2026-09-07: «те же самые пять вкладок должны быть на
    # сегодня… отличие этих двух менюшек минимальное». Before it, this address
    # served a separate document of read-only cards — a shop window with nothing to
    # press, and without the site's own menu; the owner's first question on seeing
    # it was «а где его менять?».
    for vkladka in ("школьникам", "принимающим"):
        assert f">{vkladka}</label>" in telo, f"вкладка «{vkladka}» на месте"
    assert 'class="menu"' in telo, "оглавление сайта на месте"


def test_the_standing_arrangement_keeps_its_own_address_and_is_the_site_s_own_section(
        running_server):
    """The permanent layer stays behind its own address — and it is the SITE's section.

    🔴 THIS ASSERTION IS THE OPPOSITE OF THE ONE IT REPLACES, AND THAT IS THE CHANGE.
    It used to demand ``veb/templates/index.html`` at this address, on the reading that
    the standing editor is that separate page. Measured on 2026-09-07, it is not: that
    file is drawn entirely by the browser and carries ``const SLOT = 1``, i.e. it never
    showed Thursday at all. What the owner calls «постоянное распределение» — and
    describes tab by tab as «школьникам · принимающим · В · Д · Н» — is the ``s-rasp``
    section of the site itself, which is server-rendered from the база and is the only
    surface that ever had a day switch to remove (решение 5 of 2026-09-07).

    ``doc/DIZAJN-ZAKREPLENO.md §0`` still holds and is why ``index.html`` is not
    touched by that change: it keeps standing, as the source of the file mode built by
    ``veb/sobrat_fajl.py``.
    """
    base, _ = running_server
    status, body = _http_get(base + "/raspredelenie/postoyannoe")
    assert status == 200
    telo = body.decode("utf-8")
    assert 'id="s-rasp"' in telo, "постоянное — раздел распределения самого сайта"
    for vkladka in ("школьникам", "принимающим"):
        assert f">{vkladka}</label>" in telo, f"вкладка «{vkladka}» на месте"
    # The tab is opened BY THE ADDRESS: the radio is a CSS tab and cannot be reached
    # by a URL, so the shell carries the three lines that check it.
    assert "/raspredelenie/postoyannoe" in telo, "адрес открывает вкладку сам"


def test_the_standing_arrangement_carries_both_days_of_every_pupil(running_server):
    """Решение 5 владельца 07.09: одна таблица на оба дня, у школьника два поля.

    Counted where the pupils are listed — the «школьникам» view. The page carries
    every tab at once, so a pupil is drawn again on his group's tab; a page-wide count
    would therefore be a multiple of the pupils and prove nothing.
    """
    base, _ = running_server
    status, body = _http_get(base + "/raspredelenie/postoyannoe")
    assert status == 200
    telo = body.decode("utf-8")
    vid = re.search(r'<section class="vid" id="v-shk">.*?</section>', telo, re.S)
    assert vid, "вкладка школьников на месте"
    # 🔴 `data-sid` СТОИТ ПОСЛЕ `data-i` НА ТОЙ ЖЕ СТРОКЕ (заход poisk-i-kartochka,
    # подсветка школьника с адреса поиска) — узор больше не кончается на `data-i`
    # сразу закрывающим `>`.
    shkolniki = re.findall(r'<div class="para" data-i="[^"]*" data-sid="\d+">', vid.group(0))
    polya = re.findall(r'data-slot="\d+"', vid.group(0))
    assert shkolniki, "школьники на вкладке есть"
    assert len(polya) == 2 * len(shkolniki), (
        "у каждого школьника ровно два поля — понедельник и четверг: "
        f"{len(polya)} полей на {len(shkolniki)} школьников")
    # And the day is no longer a switch: решение 5, «день недели НЕ переключателем».
    assert 'id="d-pn"' not in telo and 'id="d-cht"' not in telo, "переключателя дней нет"


def test_a_date_that_is_not_a_date_is_refused_rather_than_guessed(running_server):
    base, _ = running_server
    try:
        status, _body = _http_get(base + "/raspredelenie?den=%D0%BD%D0%B5%D1%82")
    except urllib.error.HTTPError as exc:
        status = exc.code
    assert status == 400


def test_get_view_returns_two_cuts(running_server):
    base, _ = running_server
    status, body = _http_get(base + "/api/view?slot=1")
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
        "student_id": 1, "teacher_id": 2, "slot": 1,
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
        "student_id": 1, "teacher_id": 1, "slot": 1,
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
        "student_id": 1, "slot": 99,
    })
    assert status == 400


def test_the_lesson_screen_saves_at_once_and_the_standing_one_waits_for_the_button(
        running_server):
    """Два экрана — два момента записи, и это решение владельца 07.09.

    Дословно: *«распределение на день не нужно писать кнопку „Сохранить“ — там могут
    быть ошибки, это не… как с кондуитом, там просто нужно сразу сохраняться. А
    постоянное распределение не нужно сохранять сразу, потому что там можно долго
    его двигать и в итоге прийти к оптимальному варианту, нажать „Сохранить“, и
    дальше оно влияет»*.

    Кнопка, стоящая там, где ничего не копится, обещает несуществующий шаг: человек
    уходит со страницы, не нажав её, и не знает, сохранилось ли.
    """
    base, _ = running_server
    _status, zanyatie = _http_get(base + "/raspredelenie")
    _status, postoyannoe = _http_get(base + "/raspredelenie/postoyannoe")
    assert 'id="sohranit"' not in zanyatie.decode("utf-8"), "на занятии кнопки нет"
    assert 'id="sohranit"' in postoyannoe.decode("utf-8"), "на постоянном она есть"


def test_a_deviation_of_one_lesson_is_written_and_taken_back_by_deletion(running_server):
    """«Отсутствует» пишется сразу, а снятие отметки УДАЛЯЕТ строку.

    Слово именно это, и оно поправлено владельцем 07.09: *«болеет — неправильная
    кнопка… должна быть возможность установить статус „отсутствует“. И всё»*.
    «Болеет» называет причину, которой на занятии никто не знает.

    🔴 ЗАНЯТИЕ ХРАНИТ ТОЛЬКО ОТКЛОНЕНИЯ (`doc/TZ-sloj-zanyatia.md §2`): чего оно не
    упоминает, то читается из постоянного на лету. Поэтому «вернуть как обычно» —
    это удаление строки, а не запись «был» поверх: иначе занятие потихоньку
    зарастало бы копией постоянного, и правка шаблона перестала бы доезжать.
    """
    base, connection = running_server
    den = "2026-09-10"          # четверг

    status, _ = _http_post(base + "/api/zanyatie",
                           {"den": den, "student_id": 1, "net": True})
    assert status == 200
    ryad = connection.execute(
        "select status from attendance a join sessions s on s.id = a.session_id "
        "where s.held_on = ? and a.student_id = 1", (den,)).fetchone()
    assert ryad is not None and ryad["status"] == "не был"

    status, _ = _http_post(base + "/api/zanyatie",
                           {"den": den, "student_id": 1, "net": False})
    assert status == 200
    ostalos = connection.execute(
        "select count(*) from attendance a join sessions s on s.id = a.session_id "
        "where s.held_on = ?", (den,)).fetchone()[0]
    assert ostalos == 0, "«как обычно» — это отсутствие строки, а не строка «был»"


def test_the_standing_layer_is_untouched_by_a_move_for_one_lesson(running_server):
    """Перевод на один раз не трогает постоянное. Ни одной строки.

    Ровно этого владелец и хотел от слоя занятия: *«я должен править распределение
    во время занятия… но должно быть ещё базовое распределение, чтобы на следующее
    занятие я пришёл не с исправленным, а с базовым»*.
    """
    base, connection = running_server
    do = connection.execute(
        "select teacher_id from enrollment where student_id = 1 and slot = 2 "
        "and valid_to = '9999-12-31'").fetchall()

    status, _ = _http_post(base + "/api/zanyatie",
                           {"den": "2026-09-10", "student_id": 1, "teacher_id": 2})
    assert status == 200

    posle = connection.execute(
        "select teacher_id from enrollment where student_id = 1 and slot = 2 "
        "and valid_to = '9999-12-31'").fetchall()
    assert [r["teacher_id"] for r in do] == [r["teacher_id"] for r in posle]


def test_the_address_of_the_distribution_beats_the_remembered_tab(running_server):
    """Страница распределения открыта на распределении — что бы ни помнил браузер.

    🔴 ЦЕНА, ЗАМЕРЕННАЯ ВЛАДЕЛЬЦЕМ НА БОЕВОМ САЙТЕ: ПУСТОЙ ЭКРАН. `PRAVKA_SKRIPT`
    восстанавливает последнюю открытую вкладку из `sessionStorage`, а на странице
    занятия разделов «Класс» и «Листки» нет вовсе — их расписание читает `kt.DNI`,
    а он там из одного дня. Отмеченная радиокнопка без своей секции показывает
    меню и НИЧЕГО под ним; владелец: «нажимаю распределение, у меня моргает
    распределение, но я остаюсь на вкладке кондуит… я ничего не вижу».

    Проверяется то, что можно проверить без браузера: страница сама несёт оба
    замка — разметочный (`checked` на `p-rasp`) и скриптовый, который ставит его
    по АДРЕСУ и стоит после восстановления.
    """
    base, _ = running_server
    for adres in ("/raspredelenie", "/raspredelenie/postoyannoe"):
        _status, body = _http_get(base + adres)
        telo = body.decode("utf-8")
        # Скриптовый замок — на обеих страницах: он ставит вкладку по АДРЕСУ и
        # стоит ПОСЛЕ восстановления, поэтому память браузера его не перебивает.
        assert "location.pathname" in telo and "p-rasp" in telo, (
            f"{adres}: скрипт, ставящий вкладку по адресу, на месте")

    # 🔴 РАЗМЕТОЧНЫЙ ЗАМОК НУЖЕН ТОЛЬКО НА ЗАНЯТИИ, И ИМЕННО ТАМ ОН И СТОИТ. На
    # постоянном собраны ВСЕ разделы, и восстановленная вкладка показала бы хоть
    # что-то; на занятии разделов «Класс» и «Листки» нет, и без `checked` в самой
    # разметке страница без JavaScript оказалась бы пустой.
    _status, body = _http_get(base + "/raspredelenie")
    telo = body.decode("utf-8")
    assert re.search(r'id="p-rasp"[^>]*\schecked', telo), (
        "вкладка распределения отмечена в самой разметке страницы занятия")

    # И раздел, который эта вкладка показывает, на странице ЕСТЬ — иначе отметка
    # ведёт в пустоту, что и было дефектом.
    _status, body = _http_get(base + "/raspredelenie")
    assert 'id="s-rasp"' in body.decode("utf-8")
