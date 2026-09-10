"""Tests for `veb/priyom.py`: the marking grid and the tap that reaches the journal.

🔴 THE LOAD-BEARING TEST OF THIS FILE IS THAT A RETRACTION ADDS A ROW.  It is not a
style rule: `data/` is outside git, the live journal holds 15 900 events, and a page
that "removes a mark" by deleting the `assert` would corrupt it with nothing left to
restore it from.  So the test asserts the count going UP and the earlier row still being
there — not merely that the cell reads "not credited" afterwards.

The server is booted the way `tests/veb/test_server.py` boots it — a tmp database, a
random localhost port — but with a handler built HERE from `priyom.marshruty()` instead
of `veb.server.Handler`.  That is deliberate and it is what the заход asks for: the
page has to be provable without waiting for the neighbour who owns `veb/server.py` to
wire it into the router.
"""

from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import config
import pytest
from infra.db import apply_migrations, connect

os.environ.setdefault("SPETSMAT_VEB_SECRET", "test-secret-key-32bytes!")

from veb import priyom, vhod


def _handler_klass():
    """A minimal server that serves exactly what `priyom.marshruty()` declares.

    Both methods consult the same declaration, so the write door is reachable by POST
    here even though `veb/server.py:do_POST` does not consult it yet.
    """
    marshruty = priyom.marshruty()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def _obsluzhit(self):
            from urllib.parse import urlparse
            put = urlparse(self.path).path
            if put in marshruty:
                marshruty[put](self)
                return
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()

        do_GET = _obsluzhit
        do_POST = _obsluzhit

    return Handler


@pytest.fixture
def server(tmp_path):
    """Boot the page on a tmp database: one sheet, two problems, two pupils."""
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
    student_ids = [
        connection.execute(
            "insert into students (surname, name, class, status, first_sheet_id) "
            "values (?, ?, '9a', 'active', ?)",
            (surname, "Иван", sheet_id),
        ).lastrowid
        for surname in ("Асеев", "Яшин")
    ]
    # 🔴 СТРОКА НА ОБА СЛОТА. С 10.09 «свой» считается ПО ДНЮ: приём, кондуит и
    # кабинет спрашивают ту же службу, что распределение (требование владельца —
    # «изменение в текущем расписании на сегодня не обновляет кабинет и вкладку в
    # кондуите»). Строка одного слота делала бы тест зависимым от того, на какой день
    # недели пришёлся прогон: в понедельник зелёный, в четверг красный. Проверяется
    # здесь не день, а то, что свои дети идут сверху и помечены.
    for slot in (1, 2):
        connection.execute(
            "insert into enrollment (student_id, teacher_id, room, slot, valid_from, valid_to) "
            "values (?, ?, '203', ?, '2026-09-01', ?)",
            (student_ids[0], teacher_id, slot, config.OPEN_END_DATE),
        )
    connection.commit()

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _handler_klass())
    httpd.db_path = str(db_path)  # type: ignore[attr-defined]
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield {
            "baza": f"http://127.0.0.1:{port}",
            "c": connection,
            "listok": sheet_id,
            "zadachi": problem_ids,
            "deti": student_ids,
            "prepod": teacher_id,
        }
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join()
        connection.close()


def _kuka(teacher_id=None) -> str:
    return f"{vhod.COOKIE_NAME}={vhod._make_cookie('prepod', teacher_id)}"


def _get(url: str, teacher_id=None) -> tuple:
    req = urllib.request.Request(url, headers={"Cookie": _kuka(teacher_id)})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _tap(baza: str, student_id: int, problem_id: int, target: str, teacher_id=None) -> tuple:
    telo = json.dumps({"student": student_id, "problem": problem_id,
                       "target": target}).encode("utf-8")
    req = urllib.request.Request(
        baza + "/api/priyom", data=telo, method="POST",
        headers={"Content-Type": "application/json", "Cookie": _kuka(teacher_id)})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def _ryady(c, student_id: int, problem_id: int) -> list:
    return c.execute(
        "select id, event, reverses_id, source, teacher_id from marks "
        "where student_id = ? and problem_id = ? order by id",
        (student_id, problem_id),
    ).fetchall()


# ------------------------------------------------------------------- главный тест файла

def test_snyatie_dobavlyaet_stroku_a_ne_udalyaet(server):
    """🔴 `retract` ДОБАВЛЯЕТ строку и оставляет `assert` на месте.

    Three things are asserted together because any one of them alone would pass while
    the journal was being corrupted: the row COUNT goes up, the original `assert` row is
    still there BY ITS ID, and the new row points at it through `reverses_id`.
    """
    c, uch, zad = server["c"], server["deti"][0], server["zadachi"][0]

    status, otvet = _tap(server["baza"], uch, zad, "solved")
    assert status == 200 and otvet["sostoyanie"] == "solved", otvet
    posle_plusa = _ryady(c, uch, zad)
    assert len(posle_plusa) == 1
    assert posle_plusa[0]["event"] == "assert"
    id_plusa = posle_plusa[0]["id"]

    status, otvet = _tap(server["baza"], uch, zad, "retracted")
    assert status == 200 and otvet["sostoyanie"] == "retracted", otvet

    posle_snyatiya = _ryady(c, uch, zad)
    assert len(posle_snyatiya) == 2, "снятие обязано ДОБАВИТЬ строку, а не удалить"
    assert posle_snyatiya[0]["id"] == id_plusa, "исходный `assert` исчез из журнала"
    assert posle_snyatiya[0]["event"] == "assert"
    assert posle_snyatiya[1]["event"] == "retract"
    assert posle_snyatiya[1]["reverses_id"] == id_plusa


def test_stranica_pokazyvaet_snyatuyu_kletku_ne_sdannoj(server):
    """After the retraction the grid draws the cell as not credited."""
    uch, zad = server["deti"][0], server["zadachi"][0]
    _tap(server["baza"], uch, zad, "solved")
    _tap(server["baza"], uch, zad, "retracted")

    status, telo = _get(server["baza"] + f"/priyom?listok={server['listok']}")
    assert status == 200
    stranica = telo.decode("utf-8")
    kletka = f'data-u="{uch}" data-z="{zad}"'
    nachalo = stranica.index(kletka)
    kusok = stranica[nachalo - 120:nachalo]
    assert "kl retracted" in kusok, kusok
    assert "kl solved" not in kusok, kusok


def test_snyatie_galochki_dobavlyaet_erratum_i_ne_udalyaet(server):
    """🔴 Второй тап (цель «пусто») ДОБАВЛЯЕТ строку `erratum`, а не удаляет `assert`.

    Владелец 07.09: «второй тап должен снимать галочку, а не ставить крестик».  Это
    другое событие, чем `retract`, и потому проверяется отдельно: клетка обязана стать
    пустой, обе прежние строки — остаться на месте, а новая — сослаться на ту, которую
    вычёркивает.
    """
    c, uch, zad = server["c"], server["deti"][0], server["zadachi"][0]

    _tap(server["baza"], uch, zad, "solved")
    id_plusa = _ryady(c, uch, zad)[0]["id"]

    status, otvet = _tap(server["baza"], uch, zad, "empty")
    assert status == 200 and otvet["sostoyanie"] == "empty", otvet

    ryady = _ryady(c, uch, zad)
    assert len(ryady) == 2, "снятие галочки обязано ДОБАВИТЬ строку"
    assert ryady[0]["id"] == id_plusa and ryady[0]["event"] == "assert"
    assert ryady[1]["event"] == "erratum"
    assert ryady[1]["reverses_id"] == id_plusa


# ------------------------------------------------------------------------ запись в базу

def test_tap_pishet_svoj_istochnik_i_prepodavatelya(server):
    """The row carries `source='кнопка'` and the teacher out of the cookie."""
    c, uch, zad = server["c"], server["deti"][0], server["zadachi"][0]
    _tap(server["baza"], uch, zad, "solved", teacher_id=server["prepod"])

    ryad = _ryady(c, uch, zad)[0]
    assert ryad["source"] == "кнопка"
    assert ryad["teacher_id"] == server["prepod"]


def test_povtornyj_tap_v_to_zhe_sostoyanie_nichego_ne_pishet(server):
    """Two identical taps leave one row: the service takes a target, not a toggle."""
    c, uch, zad = server["c"], server["deti"][0], server["zadachi"][0]
    _tap(server["baza"], uch, zad, "solved")
    status, otvet = _tap(server["baza"], uch, zad, "solved")

    assert status == 200
    assert otvet["zapisano"] is False
    assert len(_ryady(c, uch, zad)) == 1


def test_snyatie_pustoj_kletki_ne_padaet(server):
    """Nothing to take back is answered with the cell as it stands, not with a 500."""
    c, uch, zad = server["c"], server["deti"][1], server["zadachi"][1]
    status, otvet = _tap(server["baza"], uch, zad, "retracted")

    assert status == 200
    assert otvet["sostoyanie"] == "empty"
    assert otvet["zapisano"] is False
    assert _ryady(c, uch, zad) == []


def test_zapis_cherez_get_toy_zhe_dveryu(server):
    """The write door answers GET too — the fallback the page uses until `do_POST`
    consults the section registry."""
    c, uch, zad = server["c"], server["deti"][1], server["zadachi"][0]
    status, telo = _get(
        server["baza"] + f"/api/priyom?student={uch}&problem={zad}&target=solved")

    assert status == 200
    assert json.loads(telo)["sostoyanie"] == "solved"
    assert len(_ryady(c, uch, zad)) == 1


# ---------------------------------------------------------------------- страница и вход

def test_dolg_i_prepodavatel_stoyat_v_odnoj_stroke_s_uchenikom(server):
    """🔴 Условие мандата: фамилия, принимающий и долг — одна строка, не три места."""
    status, telo = _get(server["baza"] + f"/priyom?listok={server['listok']}",
                        teacher_id=server["prepod"])
    assert status == 200
    stranica = telo.decode("utf-8")

    stroki = [s for s in stranica.split("<tr") if "Асеев" in s]
    assert len(stroki) == 1, "ученик обязан стоять ровно в одной строке решётки"
    stroka = stroki[0]
    assert "Асеев" in stroka
    assert "Пирогов" in stroka, "принимающий не на строке ученика"
    assert 'class="dolg"' in stroka, "долг не на строке ученика"


def test_svoi_deti_sverhu_i_vydeleny(server):
    """One's own pupils sort to the top and carry the class; others stay on the page."""
    status, telo = _get(server["baza"] + f"/priyom?listok={server['listok']}",
                        teacher_id=server["prepod"])
    stranica = telo.decode("utf-8")

    assert stranica.index("Асеев") < stranica.index("Яшин")
    svoya = stranica[stranica.index("Асеев") - 400:stranica.index("Асеев")]
    assert 'class="moi"' in svoya, svoya
    assert "Яшин" in stranica, "чужие дети доступны, а не спрятаны"


def test_bez_kuki_stranica_ne_pokazyvaet_nikogo(server):
    """No cookie: the entry invitation, and not one pupil's name."""
    req = urllib.request.Request(server["baza"] + "/priyom")
    with urllib.request.urlopen(req) as r:
        telo = r.read().decode("utf-8")
    assert "Асеев" not in telo and "Яшин" not in telo
    assert "/vhod" in telo


def test_bez_kuki_zapis_otkazana(server):
    """No cookie, no write: 403 and an empty journal."""
    c, uch, zad = server["c"], server["deti"][0], server["zadachi"][0]
    telo = json.dumps({"student": uch, "problem": zad, "target": "solved"}).encode("utf-8")
    req = urllib.request.Request(
        server["baza"] + "/api/priyom", data=telo, method="POST",
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            status = r.status
    except urllib.error.HTTPError as exc:
        status = exc.code

    assert status == 403
    assert _ryady(c, uch, zad) == []


def test_marshruty_obyavleny_kontraktom(server):
    """The declaration the server collects: `{путь: обработчик}`, handlers taking `h`."""
    marshruty = priyom.marshruty()
    assert set(marshruty) == {"/priyom", "/api/priyom"}
    assert all(callable(o) for o in marshruty.values())
