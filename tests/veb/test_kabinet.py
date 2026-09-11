"""Tests for `veb/razdely/kabinet.py`, its two routes, and the freeze they arm.

Boots the full `veb.server.Handler` the way `tests/veb/test_istoria_zanyatij.py` does:
both routes live behind the `marshruty()` seam (`RAZDELY_S_MARSHRUTAMI`), so a test that
called `veb.razdely.kabinet.marshruty()` directly would never exercise the registration
in `veb/server.py` — which is the half that has been forgotten before.

The freeze is checked from the OUTSIDE, through the two doors that actually write:
`/api/enrollment` (the standing layer) and `/api/zanyatie` (the lesson layer). Checking
it only on `EnrollmentService` would prove the rule and not prove it is armed, and the
lesson layer does not go through that service at all.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from http.server import ThreadingHTTPServer
from zoneinfo import ZoneInfo

import config
import pytest
from infra.db import apply_migrations, connect

os.environ.setdefault("SPETSMAT_VEB_SECRET", "test-secret-key-32bytes!")

import veb.server as server
from core.services.sostav_na_den import blizhajshie_zanyatiya, slot_of
from veb import vhod


def _sleduyushchie(skolko: int) -> list:
    """The next lesson days from today, asked of the same function the page asks.

    Not a written-down list of dates: a fixture with `2026-09-10` in it passes today and
    fails silently in October, and this suite is meant to survive the school year.
    """
    return blizhajshie_zanyatiya(date.today().isoformat(), skolko)


@pytest.fixture
def running_server(tmp_path):
    """Two teachers with one pupil each, both attending both slots, nothing marked yet."""
    db_path = tmp_path / "spetsmat.db"
    apply_migrations(db_path, config.MIGRATIONS_DIR)
    connection = connect(db_path)
    # 🔴 THREE COLUMNS THE MIGRATIONS DO NOT CREATE AND THE LIVE БАЗА HAS. `teachers` comes
    # out of `migrations/` as `id, tg_id, name, aka, is_owner`; `aktiven`, `gruppa` and
    # `kabinet` are added at runtime by `veb/server.py`. A fixture without them is not a
    # smaller live база but a DIFFERENT one, and `lichnaya.kabinet_na_datu` — which joins
    # `teachers.gruppa` to `kabinet_na_den` — throws `no such column` on it.
    connection.execute("alter table teachers add column aktiven integer not null default 1")
    connection.execute("alter table teachers add column gruppa text")
    connection.execute("alter table teachers add column kabinet text")

    t1 = connection.execute(
        "insert into teachers (name, aka, aktiven, gruppa, kabinet) "
        "values ('Лена Мирошниченко', 'ЕМ', 1, 'В', '203')").lastrowid
    t2 = connection.execute(
        "insert into teachers (name, aka, aktiven, gruppa, kabinet) "
        "values ('Петров Олег', 'ПО', 1, 'В', '203')").lastrowid

    s1 = connection.execute(
        "insert into students (surname, name, class, status) "
        "values ('Фефелов', 'Иван', '9К', 'active')").lastrowid
    s2 = connection.execute(
        "insert into students (surname, name, class, status) "
        "values ('Агаркова', 'Ирина', '9К', 'active')").lastrowid

    for student, teacher in ((s1, t1), (s2, t2)):
        for slot in (1, 2):
            connection.execute(
                "insert into enrollment "
                "(student_id, teacher_id, room, slot, valid_from, valid_to) "
                "values (?, ?, '203', ?, '2020-01-01', ?)",
                (student, teacher, slot, config.OPEN_END_DATE))
    # 🔴 `prepodavatel_ne_prihodit` IS LEFT EMPTY ON PURPOSE, AND EMPTY MEANS «все ходят
    # всегда» (`infra/prepodavatel_den_repo.py` says so in its own docstring: the table
    # stores ABSENCE, not presence). Writing rows here would arm `TeacherNotAttending`,
    # and every freeze test below would then pass for the wrong reason.
    connection.commit()

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    httpd.db_path = str(db_path)  # type: ignore[attr-defined]
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield {"baza": f"http://127.0.0.1:{port}", "put": db_path,
               "s1": s1, "s2": s2, "t1": t1, "t2": t2}
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join()
        connection.close()


def _bez_kommentariev(telo: str) -> str:
    """Страница без того, чего читатель не видит: стилей и всех комментариев.

    🔴 БЕЗ ЭТОГО ПРОВЕРКА НА СЛОВО ЛОВИТ СОБСТВЕННЫЙ РАЗБОР КОДА. `kabinet.py`
    объясняет свои решения прямо в `SVOI_STILI` и в `SKRIPT`, то есть внутри того,
    что уезжает в документ, — и слово «сдач» стоит там в предложении, которое
    рассказывает, почему его больше нет на экране. Проверка «слова нет в теле
    ответа» краснела бы на объяснении, а не на экране.
    """
    telo = re.sub(r"<style\b.*?</style>", "", telo, flags=re.S)
    telo = re.sub(r"<!--.*?-->", "", telo, flags=re.S)
    return re.sub(r"/\*.*?\*/", "", telo, flags=re.S)


def _kuka(rol: str, kto=None) -> str:
    return f"{vhod.COOKIE_NAME}={vhod._make_cookie(rol, kto)}"


def _get(url: str, cookie: str | None = None, sledovat: bool = True):
    headers = {"Cookie": cookie} if cookie else {}
    req = urllib.request.Request(url, headers=headers)
    otkryvatel = urllib.request.build_opener()
    if not sledovat:
        class _Bez(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k):
                return None
        otkryvatel = urllib.request.build_opener(_Bez)
    try:
        with otkryvatel.open(req) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers)


def _post(url: str, telo: dict, cookie: str | None = None):
    headers = {"Content-Type": "application/json"}
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(
        url, data=json.dumps(telo).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


# --------------------------------------------------------------------- the page itself


def test_guest_is_refused(running_server):
    status, _body, _h = _get(f'{running_server["baza"]}/kabinet')
    assert status == 403


def test_common_password_gets_a_page_that_names_nobody(running_server):
    """`uid is None` is a LEGAL entry and must not show one teacher another's children."""
    status, body, _h = _get(f'{running_server["baza"]}/kabinet', _kuka("prepod"))
    assert status == 200
    telo = body.decode("utf-8")
    assert "Фефелов" not in telo and "Агаркова" not in telo
    assert "личный" in telo


def test_a_named_teacher_sees_his_own_lesson_room_and_children(running_server):
    status, body, _h = _get(
        f'{running_server["baza"]}/kabinet', _kuka("prepod", running_server["t1"]))
    assert status == 200
    telo = body.decode("utf-8")
    assert "Лена Мирошниченко" in telo
    assert "Фефелов" in telo, "свои школьники"
    assert "Агаркова" not in telo, "чужие школьники на этой странице появиться не могут"
    assert "203" in telo, "свой кабинет на эту дату"


def test_the_page_has_the_top_menu_and_none_of_the_three_removed_links(running_server):
    """Owner 10.09 (`TZ-DOBOR-10-09.md` H1.1, H1.4, H1.5, H1.7).

    «Нет верхнего меню, из кабинета некуда уйти» — теперь есть, и это тот же
    `karkas.menyu_ssylkami`, что стоит на остальных страницах. Три кнопки, которые
    здесь стояли, названы поимённо: «Моя история занятий» вела в пустое место и не
    нужна вовсе, «Распределение на занятие» он не просил, «На заглавную» делает меню.
    """
    _status, body, _h = _get(
        f'{running_server["baza"]}/kabinet', _kuka("prepod", running_server["t1"]))
    telo = body.decode("utf-8")
    assert '<nav class="menu">' in telo, "верхнее меню"
    assert 'href="/kabinet"' in telo and "Кабинет" in telo, "своя вкладка отмечена"
    for chuzhoe in ('href="/"', 'href="/raspredelenie"', 'href="/#s-list"'):
        assert chuzhoe in telo, f"уйти можно на {chuzhoe}"
    assert "Моя история занятий" not in telo
    assert "Распределение на занятие" not in telo
    assert "На заглавную" not in telo


def test_the_table_covers_the_school_year_and_colours_only_the_past(running_server):
    """Owner 10.09 (H1.6 + L1.3): занятия с начала года строками, зелёное — был.

    🔴 ГРАНИЦА ПРОВЕРЯЕТСЯ ТА, НА КОТОРОЙ ЗАХОД ЕЁ ПОСТАВИЛ: «занятие завершилось»
    (`zanyatie_zaversheno`), а не «дата уже прошла». Прежний тест сверял вторую и
    поэтому зеленел ровно тогда, когда экран врал: сегодняшнее занятие, которое
    владелец только что провёл, попадало в БУДУЩИЕ (дефект L1.1).
    Флажок остаётся признаком правимости: прошедший блок его не несёт вовсе, то
    есть отметить его нечем даже подделанным запросом со страницы.
    """
    from datetime import datetime, timezone

    from core.services.istoria_poseshchenij import zanyatie_zaversheno
    from veb.razdely.kabinet import chetverti_goda, segodnya, zanyatiya_mezhdu

    _status, body, _h = _get(
        f'{running_server["baza"]}/kabinet', _kuka("prepod", running_server["t1"]))
    telo = body.decode("utf-8")
    seichas = datetime.now(timezone.utc)
    # 🔴 ГОД ЦЕЛИКОМ, А НЕ «ПРОШЛОЕ ПЛЮС ВОСЕМЬ ДНЕЙ». С пунктом 5 рецензии 11.09
    # страница несёт ЧЕТЫРЕ четверти сразу — переключение вкладки ничего не грузит,
    # потому что грузить уже нечего. Ожидаемое число плиток считается тем же
    # календарём, что и у страницы, и никогда не вписывается числом.
    vse = [d for _n, ot, do in chetverti_goda(segodnya())
           for d in zanyatiya_mezhdu(ot, do)]
    proshlo = [d for d in vse if zanyatie_zaversheno(d, seichas=seichas)]
    vperyod = [d for d in vse if not zanyatie_zaversheno(d, seichas=seichas)]

    # Прошедшая плитка — `<details>` (свёрнута по умолчанию, пункт 4 рецензии 11.09),
    # будущая — `<div>`: разворачивать в ней нечего. Считаются обе.
    blokov = (telo.count('<details class="kab-zanyatie ')
              + telo.count('<div class="kab-zanyatie '))
    assert blokov == len(vse), f"блоков {blokov}, а занятий {len(vse)}"
    assert telo.count('kab-zanyatie byl') + telo.count('kab-zanyatie ne-byl') \
        == len(proshlo), "цветом красится ровно завершившееся"
    assert telo.count('kab-zanyatie vperyod') == len(vperyod)
    for den in proshlo:
        assert f'<input type="checkbox" data-den="{den}"' not in telo, (
            f"завершившееся {den} не правится")


def test_a_lesson_that_ended_today_reads_as_past_and_not_as_future(running_server):
    """L1.1, ДЕФЕКТ ФАКТА: владелец провёл занятие 10.09 и не увидел зелёного.

    Причина была в границе `den < segodnya()`: для СЕГОДНЯШНЕГО занятия она ложна,
    и только что проведённый урок рисовался как будущий — без цвета и с флажком
    «меня не будет». Здесь часы переводятся на день занятия, ПОСЛЕ его конца, и
    экран обязан назвать этот день прошедшим.
    """
    import veb.razdely.kabinet as kab
    from core.services.sostav_na_den import KONEC_ZANYATIA, slot_of

    den = date.today().isoformat()
    if slot_of(den) is None:
        pytest.skip("сегодня не день занятия — границу этим прогоном не проверить")
    konec = KONEC_ZANYATIA[date.fromisoformat(den).isoweekday()]
    if (datetime.now(ZoneInfo(config.TZ_DISPLAY)).hour,
            datetime.now(ZoneInfo(config.TZ_DISPLAY)).minute) < konec:
        pytest.skip("занятие сегодня ещё не кончилось — проверять нечего")
    _status, body, _h = _get(
        f'{running_server["baza"]}/kabinet', _kuka("prepod", running_server["t1"]))
    telo = body.decode("utf-8")
    assert f'<input type="checkbox" data-den="{den}"' not in telo, (
        "занятие, которое сегодня уже кончилось, не предлагает флажок «меня не будет»")


def test_the_strip_starts_at_the_first_of_september(running_server):
    """Начало считается от даты, а не вписано: 1 сентября того учебного года."""
    from veb.razdely.kabinet import nachalo_uchebnogo_goda

    assert nachalo_uchebnogo_goda("2026-09-10") == "2026-09-01"
    assert nachalo_uchebnogo_goda("2026-09-01") == "2026-09-01"
    assert nachalo_uchebnogo_goda("2027-02-03") == "2026-09-01"
    assert nachalo_uchebnogo_goda("2026-08-31") == "2025-09-01"


def test_the_grid_is_the_next_lessons_and_carries_no_written_down_date(running_server):
    status, body, _h = _get(
        f'{running_server["baza"]}/kabinet', _kuka("prepod", running_server["t1"]))
    telo = body.decode("utf-8")
    for den in _sleduyushchie(8):
        assert f'data-den="{den}"' in telo, f"{den} должен стоять в сетке"
    vchera = (date.today() - timedelta(days=1)).isoformat()
    assert f'<input type="checkbox" data-den="{vchera}"' not in telo, (
        "вчерашнее занятие правиться не может")


def test_login_with_a_personal_password_lands_in_the_cabinet(running_server, monkeypatch):
    """Owner 09.09: «когда я нажимаю Вход, я попадаю … в свой личный кабинет».

    The password store lives in `secrets/` and is not part of this fixture, so the door
    is opened by replacing the ONE function that answers «кто это» — the redirect under
    test is the line that reads its answer, and nothing else about the entry is faked.
    """
    monkeypatch.setattr(vhod, "proverit_parol",
                        lambda _p: ("prepod", running_server["t1"]))
    status, _body, headers = _get_vhod(running_server["baza"], "чей-угодно")
    assert status == 302
    assert headers["Location"] == "/kabinet"


def test_login_with_a_COMMON_password_still_lands_on_the_site(running_server, monkeypatch):
    """`uid is None` names nobody, and a cabinet with nobody in it is not a landing."""
    monkeypatch.setattr(vhod, "proverit_parol", lambda _p: ("prepod", None))
    status, _body, headers = _get_vhod(running_server["baza"], "общий")
    assert status == 302
    assert headers["Location"] == "/"


def test_a_senior_entering_as_organizator_lands_there_too(running_server, monkeypatch):
    """Three of the fifteen are seniors and enter as `organizator` WITH a uid."""
    monkeypatch.setattr(vhod, "proverit_parol",
                        lambda _p: ("organizator", running_server["t1"]))
    status, _body, headers = _get_vhod(running_server["baza"], "старший")
    assert status == 302
    assert headers["Location"] == "/kabinet"


def _get_vhod(baza: str, parol: str):
    """POST the entry form the way a BROWSER does it, and do not follow the 302."""
    class _Bez(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None

    telo = urllib.parse.urlencode({"parol": parol}).encode("utf-8")
    req = urllib.request.Request(
        baza + "/vhod", data=telo, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.build_opener(_Bez).open(req) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers)


# ------------------------------------------------------------------- marking an absence


def test_a_teacher_marks_himself_absent_and_it_lands_in_teacher_attendance(running_server):
    den = _sleduyushchie(3)[2]
    status, body = _post(f'{running_server["baza"]}/api/kabinet/otsutstvie',
                         {"den": den, "net": 1},
                         _kuka("prepod", running_server["t1"]))
    assert status == 200, body
    c = connect(running_server["put"])
    ryad = c.execute(
        "select ta.status from teacher_attendance ta join sessions s on s.id = ta.session_id "
        "where s.held_on = ? and ta.teacher_id = ?", (den, running_server["t1"])).fetchone()
    c.close()
    assert ryad is not None and ryad["status"] == "не был"


def test_unticking_deletes_the_row_rather_than_writing_present(running_server):
    den = _sleduyushchie(3)[2]
    cookie = _kuka("prepod", running_server["t1"])
    _post(f'{running_server["baza"]}/api/kabinet/otsutstvie', {"den": den, "net": 1}, cookie)
    status, body = _post(f'{running_server["baza"]}/api/kabinet/otsutstvie',
                         {"den": den, "net": 0}, cookie)
    assert status == 200, body
    c = connect(running_server["put"])
    n = c.execute(
        "select count(*) as n from teacher_attendance ta "
        "join sessions s on s.id = ta.session_id "
        "where s.held_on = ? and ta.teacher_id = ?",
        (den, running_server["t1"])).fetchone()["n"]
    c.close()
    assert n == 0, "«как обычно» это ОТСУТСТВИЕ строки, а не строка «был»"


def test_a_past_lesson_cannot_be_marked(running_server):
    proshloe = (date.today() - timedelta(days=7)).isoformat()
    while slot_of(proshloe) is None:
        proshloe = (date.fromisoformat(proshloe) - timedelta(days=1)).isoformat()
    status, _body = _post(f'{running_server["baza"]}/api/kabinet/otsutstvie',
                          {"den": proshloe, "net": 1},
                          _kuka("prepod", running_server["t1"]))
    assert status == 400


def test_a_non_lesson_day_cannot_be_marked(running_server):
    den = date.today().isoformat()
    while slot_of(den) is not None:
        den = (date.fromisoformat(den) + timedelta(days=1)).isoformat()
    status, _body = _post(f'{running_server["baza"]}/api/kabinet/otsutstvie',
                          {"den": den, "net": 1},
                          _kuka("prepod", running_server["t1"]))
    assert status == 400


def test_the_body_carries_no_teacher_id_so_a_colleague_cannot_be_marked(running_server):
    """The person is the cookie. A `teacher_id` in the body must change nothing."""
    den = _sleduyushchie(2)[1]
    status, body = _post(
        f'{running_server["baza"]}/api/kabinet/otsutstvie',
        {"den": den, "net": 1, "teacher_id": running_server["t2"]},
        _kuka("prepod", running_server["t1"]))
    assert status == 200, body
    c = connect(running_server["put"])
    kto = [r["teacher_id"] for r in c.execute(
        "select ta.teacher_id from teacher_attendance ta "
        "join sessions s on s.id = ta.session_id where s.held_on = ?", (den,)).fetchall()]
    c.close()
    assert kto == [running_server["t1"]], "отмечен тот, кто вошёл, и только он"


# ------------------------------------------------------------------------- the freeze


def test_the_lesson_layer_refuses_a_student_for_an_absent_teacher(running_server):
    """Owner 09.09: «это будет уже заморожено, потому что это человек сказал»."""
    den = _sleduyushchie(1)[0]
    _post(f'{running_server["baza"]}/api/kabinet/otsutstvie', {"den": den, "net": 1},
          _kuka("prepod", running_server["t1"]))
    status, body = _post(
        f'{running_server["baza"]}/api/zanyatie',
        {"den": den, "student_id": running_server["s2"],
         "teacher_id": running_server["t1"]},
        _kuka("organizator"))
    assert status == 409, body
    assert "заморожено" in body.decode("utf-8")


def test_taking_a_student_AWAY_from_an_absent_teacher_is_never_refused(running_server):
    """The refusal exists to empty him out, so it must not lock his children in."""
    den = _sleduyushchie(1)[0]
    _post(f'{running_server["baza"]}/api/kabinet/otsutstvie', {"den": den, "net": 1},
          _kuka("prepod", running_server["t1"]))
    status, body = _post(
        f'{running_server["baza"]}/api/zanyatie',
        {"den": den, "student_id": running_server["s1"],
         "teacher_id": running_server["t2"]},
        _kuka("organizator"))
    assert status == 200, body


def test_the_standing_layer_refuses_a_move_onto_a_teacher_absent_TODAY(running_server):
    """The standing door can only ever be frozen for TODAY, and that is not a shortfall.

    🔴 `/api/enrollment` COMPUTES `effective_from` ITSELF, AS TODAY, AND IGNORES THE FIELD
    IN THE BODY (`veb/server.py:1590`). Measured live on the боевой server on 2026-09-10:
    a request naming `effective_from: 2026-10-01` opened the new interval on 2026-09-10.
    So a standing row is never «назначение на 1 октября» — it is «с сегодняшнего дня и
    впредь», and the only date its freeze can be asked about is today. A single future
    date is frozen where a single date lives: the lesson layer, `/api/zanyatie`, tested
    above. On 1 October the teacher marked absent still shows «отсутствует» there and his
    children go red as unassigned, which is what `SostavService` was built to do.

    Skipped when today is not a lesson day: the mark itself refuses a non-lesson date, so
    on a Tuesday there is no date on which BOTH doors can be asked about the same day.
    """
    segodnya = date.today().isoformat()
    if slot_of(segodnya) is None:
        pytest.skip("сегодня не день занятия: замораживать постоянный слой нечем")
    _post(f'{running_server["baza"]}/api/kabinet/otsutstvie', {"den": segodnya, "net": 1},
          _kuka("prepod", running_server["t1"]))
    status, body = _post(
        f'{running_server["baza"]}/api/enrollment',
        {"student_id": running_server["s2"], "teacher_id": running_server["t1"],
         "slot": slot_of(segodnya)},
        _kuka("organizator"))
    assert status == 409, body


def test_a_future_lesson_is_frozen_even_though_it_is_weeks_away(running_server):
    """The owner's own scenario: a cross put in a cell far ahead, not in today's."""
    daleko = _sleduyushchie(6)[5]
    _post(f'{running_server["baza"]}/api/kabinet/otsutstvie', {"den": daleko, "net": 1},
          _kuka("prepod", running_server["t1"]))
    status, body = _post(
        f'{running_server["baza"]}/api/zanyatie',
        {"den": daleko, "student_id": running_server["s2"],
         "teacher_id": running_server["t1"]},
        _kuka("organizator"))
    assert status == 409, body
    # ...and the lesson right before it is untouched: one date is one date.
    blizhe = _sleduyushchie(6)[4]
    status, body = _post(
        f'{running_server["baza"]}/api/zanyatie',
        {"den": blizhe, "student_id": running_server["s2"],
         "teacher_id": running_server["t1"]},
        _kuka("organizator"))
    assert status == 200, body


def test_without_the_mark_the_same_write_goes_through(running_server):
    """The negative half: the refusal must come from the MARK, not from the fixture."""
    den = _sleduyushchie(1)[0]
    status, body = _post(
        f'{running_server["baza"]}/api/zanyatie',
        {"den": den, "student_id": running_server["s2"],
         "teacher_id": running_server["t1"]},
        _kuka("organizator"))
    assert status == 200, body


# --------------------------------------------- L1.2 и L1.3: таблица занятий и раскрытие


def test_the_strip_of_chips_is_now_a_table_of_lessons_with_their_pupils(running_server):
    """L1.3, владелец 10.09: «строки — занятия, в каждой список школьников».

    Полоса плашек называла только дату; кто был на занятии, жило во всплывающей
    подсказке, то есть на экране не стояло. Проверяется, что список школьников
    ЕСТЬ в разметке блока, а не только в `title`.
    """
    _status, body, _h = _get(
        f'{running_server["baza"]}/kabinet', _kuka("prepod", running_server["t1"]))
    telo = body.decode("utf-8")
    assert '<div class="kab-tablica" id="kab-ch-1">' in telo, (
        "занятия строками, а не полосой плашек")
    assert 'class="kab-polosa"' not in telo, "полоса плашек снята"
    assert 'class="kab-spisok"' in telo, "в блоке занятия стоит список школьников"


def test_clicking_a_lesson_and_a_pupil_has_something_to_open(running_server):
    """L1.2: «клик по прошлому занятию раскрывает своё — кто был и что поставлено».

    Раскрытие содержится в блоке данных страницы, а не собирается запросом: тест
    проверяет, что для каждого ЗАВЕРШИВШЕГОСЯ занятия ключ есть, и что у школьника
    этого дня есть свой ключ. Пустой блок данных — красное: кликать было бы не по
    чему, и это ровно то состояние, в котором раскрытие «как бы сделано».
    """
    import re
    from datetime import datetime, timezone

    from core.services.istoria_poseshchenij import zanyatie_zaversheno
    from veb.razdely.kabinet import proshedshie_zanyatiya, segodnya

    _status, body, _h = _get(
        f'{running_server["baza"]}/kabinet', _kuka("prepod", running_server["t1"]))
    telo = body.decode("utf-8")
    blok = re.search(r'<script type="application/json" id="kab-dannye">(.*?)</script>',
                     telo, re.S)
    assert blok is not None, "страница обязана нести данные раскрытия"
    dannye = json.loads(blok.group(1))
    seichas = datetime.now(timezone.utc)
    proshlo = [d for d in proshedshie_zanyatiya(segodnya())
               if zanyatie_zaversheno(d, seichas=seichas)]
    assert proshlo, "фикстура обязана иметь хотя бы одно завершившееся занятие"
    for den in proshlo:
        assert den in dannye, f"клик по занятию {den} должен что-то раскрывать"
        assert "deti" in dannye[den]
    kluchi_shkolnikov = [k for k in dannye if "|" in k]
    assert kluchi_shkolnikov, "клик по школьнику должен что-то раскрывать"
    for k in kluchi_shkolnikov:
        assert "sdal" in dannye[k], f"раскрытие школьника {k} обязано называть сдачу"


def test_the_made_up_summary_line_is_gone(running_server):
    """Пункт 1 рецензии владельца 11.09, дословно: *«я не понял, что значит занятия с
    вашими школьниками 2 из 3… это какая-то фраза вставлена, которую можно удалить
    вообще. Фразы от себя лучше удалять»*.

    Здесь стояли ДВЕ проверки, и обе требовали ровно того, что владелец теперь велел
    убрать: `test_the_cabinet_sums_itself_up_in_one_line` требовала подстроку «с начала
    года: занятий с вашими школьниками», а `test_the_summary_does_not_count_a_lesson_
    the_teacher_did_not_teach` — что первое число считает свои дни, а не календарные.
    Они удалены вместе со строкой: тест, стерегущий удалённое поведение, это не
    страховка, а запрет на выполнение просьбы. Их содержательная находка (сводка
    складывала календарь с работой) не теряется — она записана у места, где сводка
    считалась, в `veb/razdely/kabinet.py`.

    Проверяется ОТСУТСТВИЕ: и текста, и класса, которым он был размечен.
    """
    _status, body, _h = _get(
        f'{running_server["baza"]}/kabinet', _kuka("prepod", running_server["t1"]))
    telo = body.decode("utf-8")
    assert "с начала года: занятий с вашими школьниками" not in telo
    assert 'class="kab-svodka"' not in telo, "класс сводки снят вместе с ней"
    assert "принято сдач" not in telo
    assert "работал со школьниками" not in telo


def test_the_screen_says_zadach_and_never_sdach(running_server):
    """Пункт 2 рецензии 11.09: *«слово „сдач“ очень странное. Лучше пиши „задач“»*.

    Проверяется по ВИДИМОМУ тексту, а не по исходнику: слово живёт в шапке плитки
    занятия, и именно там владелец на него и наткнулся. Формат — его собственный,
    `задач: N`.
    """
    _status, body, _h = _get(
        f'{running_server["baza"]}/kabinet', _kuka("prepod", running_server["t1"]))
    telo = _bez_kommentariev(body.decode("utf-8"))
    assert "сдач" not in telo, "слова «сдач» на экране быть не должно"
    assert re.search(r"задач: \d+", telo), "шапка плитки называет число задач"


def test_no_gendered_verb_is_printed_for_a_person_whose_sex_is_not_in_the_baza(
        running_server):
    """Пункт 3 рецензии 11.09: *«Бочарова Анна — она СДАЛА, а не сдал»*.

    🔴 ПРОВЕРЯЕТСЯ ДВА ФАКТА СРАЗУ, И ВТОРОЙ — ПРИЧИНА ПЕРВОГО. Пола в базе нет:
    здесь это утверждается не словами, а `pragma table_info` по тем же двум таблицам,
    из которых страница берёт людей. Пока столбца нет, единственный способ не
    напечатать неверный род — не печатать род вовсе, и экран проверяется именно на
    это: ни «сдал», ни «сдала», ни «сдали».

    Тест переживёт появление пола: в тот день первая половина покраснеет, и это
    ровно то место, куда надо прийти и вернуть глагол.
    """
    conn = sqlite3.connect(str(running_server["put"]))
    try:
        for tablica in ("students", "teachers"):
            stolbcy = {r[1] for r in conn.execute(f"pragma table_info({tablica})")}
            assert not (stolbcy & {"pol", "gender", "sex", "otchestvo", "patronymic"}), (
                f"в {tablica} появился пол — глагол можно и нужно вернуть")
    finally:
        conn.close()

    _status, body, _h = _get(
        f'{running_server["baza"]}/kabinet', _kuka("prepod", running_server["t1"]))
    telo = _bez_kommentariev(body.decode("utf-8"))
    for glagol in ("сдал", "сдала", "сдали", "принял", "приняла"):
        assert glagol not in telo, f"род глагола угадан: «{glagol}»"
    assert "задач нет" in telo, "вместо глагола — безличное «задач нет»"


def test_every_past_lesson_tile_is_collapsed_until_it_is_clicked(running_server):
    """Пункт 4 рецензии 11.09: *«удобнее, если у тебя будет свёрнуто… потом я нажимаю,
    оно разворачивается»*.

    Свёрнутость проверяется по разметке, а не по картинке: `<details>` без атрибута
    `open` браузер рисует свёрнутым. Красное здесь значит, что плитка приехала
    раскрытой — то есть ровно тот экран, на который владелец и пожаловался.
    """
    from datetime import datetime, timezone

    from core.services.istoria_poseshchenij import zanyatie_zaversheno
    from veb.razdely.kabinet import proshedshie_zanyatiya, segodnya

    _status, body, _h = _get(
        f'{running_server["baza"]}/kabinet', _kuka("prepod", running_server["t1"]))
    telo = body.decode("utf-8")
    seichas = datetime.now(timezone.utc)
    proshlo = [d for d in proshedshie_zanyatiya(segodnya())
               if zanyatie_zaversheno(d, seichas=seichas)]
    assert proshlo, "фикстура обязана иметь хотя бы одно завершившееся занятие"
    assert telo.count('<details class="kab-zanyatie ') == len(proshlo)
    assert "<details open" not in telo and 'kab-zanyatie" open' not in telo, (
        "ни одна плитка не приезжает раскрытой")
    assert "<summary class=\"kab-zag\"" in telo, "шапка плитки — сама себе выключатель"


def test_the_year_is_laid_out_as_four_quarter_tabs_of_five_columns(running_server):
    """Пункт 5 рецензии 11.09: *«нужно, чтобы 5 было колонок, чтобы на всю четверть ты
    прям видел… у нас будет вкладка четверть 1, потом четверть 2, 3, 4»*.

    Проверяются три вещи, и каждая может провалиться отдельно: вкладок ровно четыре;
    все занятия четверти лежат в ЕЁ теле, а не размазаны по соседним; открыта та
    вкладка, в которую попадает сегодняшний день. Число колонок — в таблице стилей,
    и оно проверяется там же, потому что больше ему негде быть.
    """
    from veb.razdely.kabinet import (chetverti_goda, otkrytaya_chetvert, segodnya,
                                     zanyatiya_mezhdu)

    _status, body, _h = _get(
        f'{running_server["baza"]}/kabinet', _kuka("prepod", running_server["t1"]))
    telo = body.decode("utf-8")
    god = chetverti_goda(segodnya())
    assert len(god) == 4

    for nomer, _ot, _do in god:
        assert f'<label for="kab-p-{nomer}">{nomer} четверть</label>' in telo
        assert f'<div class="kab-tablica" id="kab-ch-{nomer}">' in telo

    otkryta = otkrytaya_chetvert(segodnya(), god)
    assert f'id="kab-p-{otkryta}" checked' in telo, "открыта четверть сегодняшнего дня"
    assert telo.count(" checked>") >= 1
    assert len(re.findall(r'id="kab-p-\d" checked', telo)) == 1, "отмечена ровно одна"

    # 🔴 КАЖДОЕ ЗАНЯТИЕ — В ТЕЛЕ СВОЕЙ ВКЛАДКИ, А НЕ ПРОСТО ГДЕ-ТО НА СТРАНИЦЕ.
    # Проверка «дата есть в документе» прошла бы и на прежней одной ленте, то есть
    # не отличала бы сделанное от несделанного. Документ режется по меткам вкладок:
    # кусок от `id="kab-ch-N"` до следующей такой метки и есть тело N-й четверти.
    granicy = [(nomer, telo.index(f'<div class="kab-tablica" id="kab-ch-{nomer}">'))
               for nomer, _ot, _do in god]
    granicy.append((None, telo.index('<p class="kab-beda"')))
    tela = {granicy[i][0]: telo[granicy[i][1]:granicy[i + 1][1]]
            for i in range(len(granicy) - 1)}
    for nomer, ot, do in god:
        dni = zanyatiya_mezhdu(ot, do)
        assert dni, f"четверть {nomer} обязана содержать дни занятий"
        svoi = tela[nomer]
        for den in dni:
            assert f'data-den="{den}"' in svoi, (
                f"{den} обязан лежать в теле четверти {nomer}")
        chuzhie = [d for n, o, dd in god if n != nomer
                   for d in zanyatiya_mezhdu(o, dd)]
        for den in chuzhie:
            assert f'data-den="{den}"' not in svoi, (
                f"{den} не из четверти {nomer}, а лежит в ней")

    assert ".kab-tablica{columns:5" in telo, "пять колонок — число, названное владельцем"
