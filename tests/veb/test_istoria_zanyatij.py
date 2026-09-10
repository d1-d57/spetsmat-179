"""Tests for `veb/razdely/istoria_zanyatij.py` and its route on `veb/server.py`.

Boots the full `veb.server.Handler` the way `tests/veb/test_kartochka.py` does — the
route lives behind the `marshruty()` seam (`RAZDELY_S_MARSHRUTAMI`), so a test that
called `veb.razdely.istoria_zanyatij.marshruty()` directly would never exercise the
registration in `veb/server.py`.
"""

from __future__ import annotations

import os
import threading
import urllib.error
import urllib.request
from datetime import date, timedelta
from html.parser import HTMLParser
from http.server import ThreadingHTTPServer

import config
import pytest
from infra.db import apply_migrations, connect

os.environ.setdefault("SPETSMAT_VEB_SECRET", "test-secret-key-32bytes!")

import veb.server as server
from veb import vhod

#: Two lessons already in the past relative to "today" as this suite runs, so
#: `zanyatie_zaversheno` needs no clock injection: any day before this week's Monday is
#: unambiguously over by every reading of the timetable.
#:
#: 🔴 ЭТО ДОЛЖНЫ БЫТЬ ДНИ ЗАНЯТИЙ, А НЕ ПРОСТО ДНИ, И РАНЬШЕ ИМИ НЕ БЫЛИ. Здесь
#: стояло `date.today() - timedelta(days=14)` под именем `MONDAY` и `-10` под именем
#: `FRIDAY`. Понедельником первое оказывается ровно в те дни, когда сегодня
#: понедельник; в остальные шесть дней недели обе даты попадают куда угодно — при
#: сборке этой правки 11.09 они были ПЯТНИЦЕЙ (28.08) и ВТОРНИКОМ (01.09).
#: `SLOTY_ZANYATIJ` знает только пн и чт, `slot_of` отвечает `None` на любой другой
#: день, `SostavService.sostav` возвращает пустой состав — и в решётке нет НИ ОДНОЙ
#: клетки «был». Два теста из шести падали шесть дней в неделю, и падали на данных
#: фикстуры, а не на коде страницы. Дни считаются от сегодняшнего назад до
#: ближайших пн и чт, то есть остаются днями занятий в любой день прогона.
def _proshedshij(iso_den_nedeli: int, ne_pozzhe_chem_dnej_nazad: int = 7) -> str:
    """Ближайший ПРОШЕДШИЙ день недели `iso_den_nedeli`, не сегодня."""
    d = date.today() - timedelta(days=ne_pozzhe_chem_dnej_nazad)
    while d.isoweekday() != iso_den_nedeli:
        d -= timedelta(days=1)
    return d.isoformat()


MONDAY = _proshedshij(1)          # понедельник — слот 1 в `SLOTY_ZANYATIJ`
FRIDAY = _proshedshij(4)          # четверг — слот 2; имя оставлено прежним


@pytest.fixture
def running_server(tmp_path):
    """Two teachers, two pupils, one standing enrollment each, one absence, one override."""
    db_path = tmp_path / "spetsmat.db"
    apply_migrations(db_path, config.MIGRATIONS_DIR)
    connection = connect(db_path)
    connection.execute("alter table teachers add column aktiven integer not null default 1")

    t1 = connection.execute(
        "insert into teachers (name, aka, aktiven) values ('Иванова Мария', 'ИМ', 1)"
    ).lastrowid
    t2 = connection.execute(
        "insert into teachers (name, aka, aktiven) values ('Петров Олег', 'ПО', 1)"
    ).lastrowid
    connection.execute(
        "insert into teachers (name, aka, aktiven) values ('Сидоров Вне', 'СВ', 0)"
    )  # уволенный: не должен появиться ни строкой, ни в счётчиках

    s1 = connection.execute(
        "insert into students (surname, name, class, status) "
        "values ('Фефелов', 'Иван', '9К', 'active')"
    ).lastrowid
    s2 = connection.execute(
        "insert into students (surname, name, class, status) "
        "values ('Агаркова', 'Ирина', '9К', 'active')"
    ).lastrowid
    connection.execute(
        "insert into students (surname, name, class, status) "
        "values ('Ушедшая', 'Совсем', '9К', 'left')"
    )  # ушедшая: не должна появиться строкой

    connection.execute(
        "insert into enrollment (student_id, teacher_id, room, slot, valid_from, valid_to) "
        "values (?, ?, '301', 1, '2020-01-01', ?)", (s1, t1, config.OPEN_END_DATE))
    connection.execute(
        "insert into enrollment (student_id, teacher_id, room, slot, valid_from, valid_to) "
        "values (?, ?, '302', 2, '2020-01-01', ?)", (s1, t1, config.OPEN_END_DATE))
    connection.execute(
        "insert into enrollment (student_id, teacher_id, room, slot, valid_from, valid_to) "
        "values (?, ?, '301', 1, '2020-01-01', ?)", (s2, t2, config.OPEN_END_DATE))
    connection.execute(
        "insert into enrollment (student_id, teacher_id, room, slot, valid_from, valid_to) "
        "values (?, ?, '302', 2, '2020-01-01', ?)", (s2, t2, config.OPEN_END_DATE))

    sid_mon = connection.execute(
        "insert into sessions (held_on, kind) values (?, 'обычное')", (MONDAY,)).lastrowid
    sid_fri = connection.execute(
        "insert into sessions (held_on, kind) values (?, 'обычное')", (FRIDAY,)).lastrowid
    # Понедельник: Иван (s1) отсутствовал; Ирина (s2) как обычно (нет строки).
    connection.execute(
        "insert into attendance (session_id, student_id, teacher_id, status) "
        "values (?, ?, null, 'не был')", (sid_mon, s1))
    # Пятница: Ивана в этот день принял ДРУГОЙ преподаватель (перевод дня).
    connection.execute(
        "insert into attendance (session_id, student_id, teacher_id, status) "
        "values (?, ?, ?, 'был')", (sid_fri, s1, t2))
    # Пятница: Олег (t2) отмечен отсутствующим целиком -> его клетка крестик, даже
    # притом что у него в этот день формально стоит перевод Ивана.
    connection.execute(
        "insert into teacher_attendance (session_id, teacher_id, status, answered_at) "
        "values (?, ?, 'не был', ?)", (sid_fri, t2, MONDAY + "T10:00:00+03:00"))
    connection.commit()

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    httpd.db_path = str(db_path)  # type: ignore[attr-defined]
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield {"baza": f"http://127.0.0.1:{port}", "s1": s1, "s2": s2, "t1": t1, "t2": t2}
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


def test_guest_is_refused(running_server):
    status, _body = _get(f'{running_server["baza"]}/istoria')
    assert status == 403


def test_signed_in_organizer_sees_the_page(running_server):
    status, body = _get(f'{running_server["baza"]}/istoria', _kuka("organizator"))
    assert status == 200
    telo = body.decode("utf-8")
    assert "История" in telo
    assert "Фефелов" in telo and "Агаркова" in telo
    assert "Иванова" in telo or "ИМ" in telo
    assert "Сидоров" not in telo, "уволенный преподаватель не должен появиться"
    assert "Ушедшая" not in telo, "ушедший школьник не должен появиться"


def test_absence_is_a_krestik_and_default_is_a_present_checkmark(running_server):
    status, body = _get(f'{running_server["baza"]}/istoria', _kuka("organizator"))
    assert status == 200
    telo = body.decode("utf-8")
    # Иван отсутствовал в понедельник: хотя бы один крестик в его строке.
    assert 'class="ist-net"' in telo
    # Ирина ни разу явно не отмечена, но стоит в enrollment -- должна получить инициалы.
    assert 'class="ist-byl"' in telo
    assert "ИМ" in telo or "ПО" in telo


def test_days_override_teacher_shows_up_not_the_standing_one(running_server):
    status, body = _get(f'{running_server["baza"]}/istoria', _kuka("organizator"))
    assert status == 200
    telo = body.decode("utf-8")
    # Пятница: Иван (s1) принят Олегом (t2, «ПО»), а не своим обычным ИМ, в клетке пятницы.
    assert "ПО" in telo


def test_column_count_matches_a_direct_database_count(running_server, tmp_path):
    """Criterion 1 of the ЗАДАЧА: columns == a count taken independently from the база."""
    status, body = _get(f'{running_server["baza"]}/istoria', _kuka("organizator"))
    assert status == 200
    telo = body.decode("utf-8")
    assert "занятий: 2" in telo


def test_teacher_marked_absent_reads_as_absent_even_with_a_students_override(running_server):
    status, body = _get(f'{running_server["baza"]}/istoria', _kuka("prepod"))
    assert status == 200
    telo = body.decode("utf-8")
    assert 'class="ist-net"' in telo


# --------------------------------------------------------------------------- родство


class _Rodstvo(HTMLParser):
    """Кто чей ребёнок: минимальный разбор, отвечающий на один вопрос.

    🔴 ВОПРОС РОВНО ОДИН И ОН НЕ ПРО ОФОРМЛЕНИЕ: сёстры ли переключатели вкладок и
    панели, которые они показывают. Правило `#iv-shk:checked~#is-shk` — комбинатор
    СЕСТРЫ; пока переключатели лежали в `<body>`, а панели в `<main>`, оно не
    совпадало никогда, и обе таблицы были невидимы при любой отметке. Это и есть
    «кнопки не нажимаются, я ничего не вижу» владельца.
    """

    def __init__(self) -> None:
        super().__init__()
        self.stek: list = []
        self.roditel: dict = {}

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if d.get("id"):
            self.roditel[d["id"]] = self.stek[-1] if self.stek else None
        if tag not in ("input", "br", "img", "meta", "link", "hr"):
            self.stek.append(d.get("id") or tag)

    def handle_endtag(self, tag):
        if self.stek:
            self.stek.pop()


def _roditeli(telo: str) -> dict:
    p = _Rodstvo()
    p.feed(telo)
    return p.roditel


def test_the_tab_switches_and_the_panels_are_siblings(running_server):
    """Селектор `~` требует сестру: переключатель и панель — один родитель."""
    status, body = _get(f'{running_server["baza"]}/istoria', _kuka("organizator"))
    assert status == 200
    rod = _roditeli(body.decode("utf-8"))
    for pereklyuchatel, panel in (("iv-shk", "is-shk"), ("iv-prep", "is-prep")):
        assert rod[pereklyuchatel] == rod[panel], (
            f"{pereklyuchatel} и {panel} должны быть сёстрами, а лежат в "
            f"{rod[pereklyuchatel]} и {rod[panel]}: правило `~` не совпадёт никогда")
    # И метки тоже: подсветка выбранной кнопки — тот же комбинатор.
    assert rod["iv-shk"] == rod.get("ist-vkladki"), "метки вкладок — тоже сёстры"
