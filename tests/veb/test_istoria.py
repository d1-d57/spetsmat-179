"""Двери истории клетки: лента событий и перебивка занятия.

🔴 ГЛАВНЫЙ ТЕСТ ЭТОГО ФАЙЛА — ЧТО ПЕРЕБИВКА НИЧЕГО НЕ ТРОГАЕТ В ЖУРНАЛЕ.  Владелец 09.09
сказал о журнале прямо: «события из журнала не удаляются никогда».  Перебивка занятия
выглядит как правка отметки и по устройству ею не является — это ряд в отдельной
таблице.  Поэтому тест сверяет `marks` побайтово ДО и ПОСЛЕ, а не только то, что панель
после перебивки показывает нужный день: второе проходило бы и на испорченном журнале.

Сервер поднимается так же, как в `tests/veb/test_priyom.py` — временная база, случайный
порт на localhost, обработчик собран из `marshruty()` раздела.  Раздел объявлен в
`veb/server.py::RAZDELY_S_MARSHRUTAMI`, и это проверяется отдельным тестом ниже, потому
что дверь, которую сервер не знает, зелена ровно оттого, что её никто не звал.
"""

from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from zoneinfo import ZoneInfo

import pytest

import config
from core.isotime import to_iso
from infra.db import apply_migrations, connect

os.environ.setdefault("SPETSMAT_VEB_SECRET", "test-secret-key-32bytes!")

from veb import vhod                                            # noqa: E402
from veb.razdely import istoria                                 # noqa: E402

MSK = ZoneInfo(config.TZ_DISPLAY)
CHETVERG = "2026-09-10"


def _handler_klass():
    marshruty = istoria.marshruty()

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
    """Один листок, две задачи, двое детей, один преподаватель."""
    db_path = tmp_path / "spetsmat.db"
    apply_migrations(db_path, config.MIGRATIONS_DIR)
    c = connect(db_path)
    listok = c.execute(
        "insert into sheets (number, title, issued_at, ord) values ('16А', 'листок 16А', '2026-09-01', 1)"
    ).lastrowid
    zadachi = [c.execute(
        "insert into problems (sheet_id, label, kind, ord) values (?, ?, 'обязательная', ?)",
        (listok, label, i)).lastrowid for i, label in enumerate(("1", "2"), start=1)]
    prepod = c.execute(
        "insert into teachers (name, aka, is_owner) values ('Пирогов', 'pir', 0)").lastrowid
    deti = [c.execute(
        "insert into students (surname, name, class, status, first_sheet_id) "
        "values (?, 'Иван', '9a', 'active', ?)", (f, listok)).lastrowid
        for f in ("Асеев", "Яшин")]
    c.commit()

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _handler_klass())
    httpd.db_path = str(db_path)                       # type: ignore[attr-defined]
    port = httpd.server_address[1]
    potok = threading.Thread(target=httpd.serve_forever, daemon=True)
    potok.start()
    try:
        yield {"baza": f"http://127.0.0.1:{port}", "c": c, "listok": listok,
               "zadachi": zadachi, "deti": deti, "prepod": prepod}
    finally:
        httpd.shutdown()
        httpd.server_close()
        potok.join()
        c.close()


def _kuka(teacher_id=None) -> str:
    return f"{vhod.COOKIE_NAME}={vhod._make_cookie('prepod', teacher_id)}"


def _zapros(url: str, telo=None, *, kuka=True, teacher_id=None) -> tuple:
    zagolovki = {"Cookie": _kuka(teacher_id)} if kuka else {}
    dannye = None
    if telo is not None:
        dannye = json.dumps(telo).encode("utf-8")
        zagolovki["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=dannye,
                                 method="POST" if dannye else "GET", headers=zagolovki)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def _sobytie(c, student, problem, event, *, kogda, zapisano=None, prepod=None,
             otmenyaet=None, source="кнопка"):
    return c.execute(
        "insert into marks (student_id, problem_id, event, reverses_id, teacher_id, "
        "valid_at, recorded_at, source) values (?, ?, ?, ?, ?, ?, ?, ?)",
        (student, problem, event, otmenyaet, prepod, kogda, zapisano or kogda, source),
    ).lastrowid


def _snimok_zhurnala(c) -> list:
    return c.execute(
        "select id, student_id, problem_id, event, reverses_id, teacher_id, valid_at, "
        "recorded_at, source, note, idempotency_key from marks order by id").fetchall()


# ------------------------------------------------------------------ дверь объявлена

def test_server_znaet_oba_marshruta():
    """Дверь, о которой сервер не знает, зелена оттого, что её никто не звал."""
    from veb import server

    assert "veb.razdely.istoria" in server.RAZDELY_S_MARSHRUTAMI
    sobrano = server._marshruty_razdelov()
    assert "/api/istoria" in sobrano and "/api/istoria/zanyatie" in sobrano


# ------------------------------------------------------------------------- чтение

def test_lenta_pokazyvaet_chto_kto_kogda_i_k_kakomu_zanyatiyu(server):
    c, uch, zad, prepod = server["c"], server["deti"][0], server["zadachi"][0], server["prepod"]
    v_chetverg = to_iso(datetime(2026, 9, 10, 13, 40, tzinfo=MSK))
    v_pyatnicu = to_iso(datetime(2026, 9, 11, 19, 0, tzinfo=MSK))
    pervoe = _sobytie(c, uch, zad, "assert", kogda=v_chetverg, prepod=prepod)
    _sobytie(c, uch, zad, "retract", kogda=v_pyatnicu, prepod=prepod, otmenyaet=pervoe)
    c.commit()

    status, otvet = _zapros(f"{server['baza']}/api/istoria?student={uch}&problem={zad}")
    assert status == 200, otvet
    assert otvet["kto"] == "Асеев Иван"
    assert otvet["chto"] == "16А · 1"
    assert otvet["sostoyanie"] == "retracted"
    assert [s["chto"] for s in otvet["sobytia"]] == ["снято", "сдал"], "свежее сверху"
    assert {s["kto"] for s in otvet["sobytia"]} == {"Пирогов"}
    assert [s["zanyatie"] for s in otvet["sobytia"]] == [CHETVERG, CHETVERG], (
        "снятое в пятницу относится к четвергу — правило владельца 09.09")
    assert otvet["sobytia"][0]["kogda"].startswith("11.09"), otvet["sobytia"][0]


def test_lenta_pustoj_kletki_pusta_a_ne_vydumana(server):
    status, otvet = _zapros(
        f"{server['baza']}/api/istoria?student={server['deti'][1]}&problem={server['zadachi'][1]}")
    assert status == 200
    assert otvet["sobytia"] == [] and otvet["sostoyanie"] == "empty"
    assert otvet["vsego"] == 0 and otvet["schyot"] == 0


def test_lenta_pomechaet_tehnicheskuyu_paru_i_ne_schitaet_eyo(server):
    """«Поставил и снял за десять секунд» — обе строки на месте, счёт не растёт."""
    c, uch, zad = server["c"], server["deti"][0], server["zadachi"][0]
    mig = datetime(2026, 9, 10, 13, 40, tzinfo=MSK)
    pervoe = _sobytie(c, uch, zad, "assert", kogda=to_iso(mig))
    _sobytie(c, uch, zad, "erratum", kogda=to_iso(mig + timedelta(seconds=10)),
             otmenyaet=pervoe)
    c.commit()

    _, otvet = _zapros(f"{server['baza']}/api/istoria?student={uch}&problem={zad}")
    assert otvet["vsego"] == 2, "события остаются в журнале — их не удаляют никогда"
    assert all(s["tehnicheskoe"] for s in otvet["sobytia"])
    assert otvet["schyot"] == 0, "тестовое нажатие не идёт в статистику"


def test_lenta_ne_neset_sobytij_sosedney_kletki(server):
    c, uch, zad = server["c"], server["deti"][0], server["zadachi"][0]
    mig = to_iso(datetime(2026, 9, 10, 13, 40, tzinfo=MSK))
    _sobytie(c, uch, zad, "assert", kogda=mig)
    _sobytie(c, uch, server["zadachi"][1], "assert", kogda=mig)
    _sobytie(c, server["deti"][1], zad, "assert", kogda=mig)
    c.commit()

    _, otvet = _zapros(f"{server['baza']}/api/istoria?student={uch}&problem={zad}")
    assert len(otvet["sobytia"]) == 1


def test_bez_kuki_istoriya_ne_otdayotsya(server):
    """На кондуите 56 фамилий: дверь чтения обязана спрашивать роль так же, как приём."""
    status, otvet = _zapros(
        f"{server['baza']}/api/istoria?student={server['deti'][0]}&problem={server['zadachi'][0]}",
        kuka=False)
    assert status == 403 and "войти" in otvet["error"]


def test_bez_adresa_pary_dver_otkazyvaet_a_ne_ugadyvaet(server):
    status, otvet = _zapros(f"{server['baza']}/api/istoria?student=1")
    assert status == 400


# ---------------------------------------------------------------------- перебивка

def test_perebivka_menyaet_zanyatie_i_ostavlyaet_sled(server):
    c, uch, zad, prepod = server["c"], server["deti"][0], server["zadachi"][0], server["prepod"]
    otmetka = _sobytie(c, uch, zad, "assert",
                       kogda=to_iso(datetime(2026, 9, 11, 19, 0, tzinfo=MSK)))
    c.commit()

    _, do = _zapros(f"{server['baza']}/api/istoria?student={uch}&problem={zad}")
    assert do["sobytia"][0]["zanyatie"] == CHETVERG
    assert do["sobytia"][0]["perebito"] is False

    ranshe = "2026-09-03"
    status, posle = _zapros(f"{server['baza']}/api/istoria/zanyatie",
                            {"mark": otmetka, "zanyatie": ranshe}, teacher_id=prepod)
    assert status == 200, posle
    assert posle["sobytia"][0]["zanyatie"] == ranshe
    assert posle["sobytia"][0]["perebito"] is True, (
        "перебивка обязана быть ВИДНА, а не подменять запись молча")

    sled = c.execute("select mark_id, valid_at, teacher_id from mark_lesson_override").fetchall()
    assert len(sled) == 1
    assert sled[0]["mark_id"] == otmetka and sled[0]["teacher_id"] == prepod
    assert sled[0]["valid_at"].startswith(ranshe)


def test_perebivka_ne_trogaet_zhurnal_ni_odnim_baytom(server):
    c, uch, zad = server["c"], server["deti"][0], server["zadachi"][0]
    otmetka = _sobytie(c, uch, zad, "assert",
                       kogda=to_iso(datetime(2026, 9, 11, 19, 0, tzinfo=MSK)))
    c.commit()
    do = [tuple(r) for r in _snimok_zhurnala(c)]

    status, _ = _zapros(f"{server['baza']}/api/istoria/zanyatie",
                        {"mark": otmetka, "zanyatie": "2026-09-03"})
    assert status == 200
    assert [tuple(r) for r in _snimok_zhurnala(c)] == do


def test_deystvuet_poslednyaya_perebivka_a_predydushchaya_ostayotsya_ryadom(server):
    c, uch, zad = server["c"], server["deti"][0], server["zadachi"][0]
    otmetka = _sobytie(c, uch, zad, "assert",
                       kogda=to_iso(datetime(2026, 9, 11, 19, 0, tzinfo=MSK)))
    c.commit()

    _zapros(f"{server['baza']}/api/istoria/zanyatie", {"mark": otmetka, "zanyatie": "2026-09-03"})
    _, posle = _zapros(f"{server['baza']}/api/istoria/zanyatie",
                       {"mark": otmetka, "zanyatie": "2026-09-07"})
    assert posle["sobytia"][0]["zanyatie"] == "2026-09-07"
    assert c.execute("select count(*) from mark_lesson_override").fetchone()[0] == 2, (
        "первая перебивка остаётся на месте: таблица тоже append-only")


def test_perebivka_na_den_bez_zanyatia_otklonyaetsya(server):
    c, uch, zad = server["c"], server["deti"][0], server["zadachi"][0]
    otmetka = _sobytie(c, uch, zad, "assert",
                       kogda=to_iso(datetime(2026, 9, 10, 13, 40, tzinfo=MSK)))
    c.commit()

    status, otvet = _zapros(f"{server['baza']}/api/istoria/zanyatie",
                            {"mark": otmetka, "zanyatie": "2026-09-11"})   # пятница
    assert status == 400 and "не учебный день" in otvet["error"]
    assert c.execute("select count(*) from mark_lesson_override").fetchone()[0] == 0


def test_perebivka_nesushchestvuyushchey_otmetki_ne_zavodit_ryada(server):
    status, otvet = _zapros(f"{server['baza']}/api/istoria/zanyatie",
                            {"mark": 999999, "zanyatie": CHETVERG})
    assert status == 404
    assert server["c"].execute(
        "select count(*) from mark_lesson_override").fetchone()[0] == 0


def test_bez_kuki_perebit_nelzya(server):
    c, uch, zad = server["c"], server["deti"][0], server["zadachi"][0]
    otmetka = _sobytie(c, uch, zad, "assert",
                       kogda=to_iso(datetime(2026, 9, 10, 13, 40, tzinfo=MSK)))
    c.commit()
    status, _ = _zapros(f"{server['baza']}/api/istoria/zanyatie",
                        {"mark": otmetka, "zanyatie": "2026-09-03"}, kuka=False)
    assert status == 403
    assert c.execute("select count(*) from mark_lesson_override").fetchone()[0] == 0


# --------------------------------------------------------------- список для выбора

def test_spisok_zanyatij_soderzhit_tolko_uchebnye_dni_i_idyot_vspyat():
    dni = istoria.zanyatiya_do(date(2026, 9, 10), skolko=5)
    assert dni == ["2026-09-10", "2026-09-07", "2026-09-03", "2026-08-31", "2026-08-27"]
    assert all(date.fromisoformat(d).isoweekday() in (1, 4) for d in dni)


def test_spisok_nachinaetsya_s_predydushchego_zanyatia_esli_segodnya_ne_uchebnyj():
    assert istoria.zanyatiya_do(date(2026, 9, 12), skolko=2) == ["2026-09-10", "2026-09-07"]
