"""Оффлайн-очередь записи: то, что доказывается без браузера.

The browser half — the tap that survives a dead network — is
`tests/veb/test_offlajn_brauzer.py`, because it cannot be proved anywhere else.  This
file holds the three things that CAN be proved from Python, and each of them is a way
the mechanism has already been observed to break:

  * **The probe.** `/api/zhiv` is what the banner asks "is the server there".  If it
    404s, every page turns the banner on the moment it loads — the failure is silent,
    universal, and looks exactly like a network outage.
  * **The order of the scripts.** `KONDUIT_SKRIPT` calls `OCHERED.podpisatsya` while the
    page is being parsed.  Standing first, it dies on `OCHERED is not defined` and takes
    its whole IIFE with it — the tap, the cell history, the sticky header.  Nothing on
    the page looks wrong; it just stops working.
  * **Р5, сериализация записи.**  `NADEZHNOST-zakaz-na-resyorch.md` asks whether
    `stdlib http.server` plus SQLite survives eighteen teachers tapping at once, and
    says materials for exactly this stack were not found.  The answer is not a document:
    it is this test, and it fails if the pragmas ever come off the connection.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer

import config
import pytest
from infra.db import apply_migrations, connect

os.environ.setdefault("SPETSMAT_VEB_SECRET", "test-secret-key-32bytes!")

import veb.server as server                                          # noqa: E402
from veb import vhod                                                 # noqa: E402
from veb.razdely import ochered                                      # noqa: E402

#: Eighteen is the owner's number, not a round one: that is how many teachers stand in
#: the room on a lesson day, and Р5 asks about exactly that load.
PREPODAVATELEJ = 18


def _nachalo_goda() -> str:
    """Первое сентября ТЕКУЩЕГО учебного года — тем же правилом, что и страница приёма.

    Дата, вписанная числом, делает листок прошлогодним в сентябре следующего года, и
    решётка кондуита пустеет молча: `veb/priyom.py::_listki_goda` отбирает по ней.
    """
    from datetime import date
    s = date.today()
    return "%d-09-01" % (s.year if s.month >= 9 else s.year - 1)


@pytest.fixture
def stend(tmp_path):
    """Живой сервер на временной базе: один листок, задачи, школьники, преподаватель."""
    db_path = tmp_path / "spetsmat.db"
    apply_migrations(db_path, config.MIGRATIONS_DIR)
    c = connect(db_path)
    # 🔴 ЧЕТЫРЕ КОЛОНКИ, КОТОРЫХ НЕТ В `migrations/` И КОТОРЫЕ ЕСТЬ В ЖИВОЙ БАЗЕ.
    # `teachers` выходит из миграций как `id, tg_id, name, aka, is_owner`; `aktiven`,
    # `gruppa`, `kabinet` и `students.gruppa` заводит код на ходу
    # (`veb/server.py::_obespechit_*`). База без них — не уменьшенная живая, а ДРУГАЯ,
    # и страница `/` падает на ней `no such column: gruppa`. Тот же приём, что в
    # `tests/veb/test_kabinet.py`: он там записан вместе с этой же причиной.
    c.execute("alter table teachers add column aktiven integer not null default 1")
    c.execute("alter table teachers add column gruppa text")
    c.execute("alter table teachers add column kabinet text")
    c.execute("alter table students add column gruppa text")
    # 🔴 КОДЫ ГРУПП — ТЕ, КОТОРЫЕ РИСУЕТ КАРКАС, А НЕ ТЕ, КОТОРЫЕ СЕЕТ МИГРАЦИЯ.
    # `migrations/005` кладёт `ИЯ · ДМ · НС`, а `razdel_raspredeleniya` держит вкладки
    # `В · Д · Н` и спрашивает у `kt.gruppy` каждую из них по имени. На живой базе
    # коды переименованы; база без них падает `KeyError: 'В'` на сборке страницы `/`,
    # то есть ещё до всего, что этот файл собирается проверять.
    for kod, starshij in (("В", "Ваня Яковлев"), ("Д", "Даня Макаров"),
                          ("Н", "Наталия Стрелкова")):
        c.execute("insert or ignore into gruppy (kod, starshij) values (?, ?)",
                  (kod, starshij))
    listok = c.execute(
        "insert into sheets (number, title, issued_at, ord) "
        "values ('1', 'листок 1', ?, 1)", (_nachalo_goda(),),
    ).lastrowid
    zadachi = [
        c.execute("insert into problems (sheet_id, label, kind, ord) "
                  "values (?, ?, 'обязательная', ?)", (listok, str(i), i)).lastrowid
        for i in range(1, PREPODAVATELEJ + 1)
    ]
    prepod = c.execute(
        "insert into teachers (name, aka, is_owner, aktiven, gruppa, kabinet) "
        "values ('Пирогов', 'pir', 0, 1, 'В', '203')").lastrowid
    deti = [
        c.execute("insert into students (surname, name, class, status, first_sheet_id) "
                  "values (?, 'Иван', '9a', 'active', ?)", (f"Асеев-{i}", listok)).lastrowid
        for i in range(2)
    ]
    for slot in (1, 2):
        c.execute("insert into enrollment (student_id, teacher_id, room, slot, "
                  "valid_from, valid_to) values (?, ?, '203', ?, '2026-09-01', ?)",
                  (deti[0], prepod, slot, config.OPEN_END_DATE))
    c.commit()

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    httpd.connection = c            # type: ignore[attr-defined]
    httpd.db_path = str(db_path)    # type: ignore[attr-defined]
    potok = threading.Thread(target=httpd.serve_forever, daemon=True)
    potok.start()
    try:
        yield {"url": f"http://127.0.0.1:{httpd.server_address[1]}", "db": db_path,
               "c": c, "deti": deti, "zadachi": zadachi, "prepod": prepod}
    finally:
        httpd.shutdown()
        httpd.server_close()
        potok.join()
        c.close()


def _kuka(teacher_id=None) -> str:
    return f"{vhod.COOKIE_NAME}={vhod._make_cookie('prepod', teacher_id)}"


def _get(url: str, kuka: str | None = None):
    zagolovki = {"Cookie": kuka} if kuka else {}
    req = urllib.request.Request(url, headers=zagolovki)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers)


def _tap(url: str, student: int, problem: int, target: str, kuka: str):
    telo = json.dumps({"student": student, "problem": problem,
                       "target": target}).encode("utf-8")
    req = urllib.request.Request(url + "/api/priyom", data=telo, method="POST",
                                 headers={"Content-Type": "application/json",
                                          "Cookie": kuka})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")


# ------------------------------------------------------------------------ проба связи

def test_proba_svyazi_otvechaet_bez_kuki_i_bez_bazy(stend):
    """`/api/zhiv` — самый дешёвый ответ сервера, и он отвечает КОМУ УГОДНО.

    Куки у пробы быть не обязано: она задаётся, когда связь уже потеряна, и требовать
    на ней вход значило бы отвечать `403` человеку, который вошёл десять минут назад,
    — то есть говорить «связи нет» ровно тогда, когда связь ЕСТЬ.
    """
    status, telo, _ = _get(stend["url"] + "/api/zhiv")
    assert status == 200
    assert json.loads(telo) == {"zhiv": True}


def test_proba_zapreshchena_k_keshirovaniyu(stend):
    """🔴 БЕЗ `no-store` ПРОБА ЛЖЁТ ИМЕННО ТОГДА, КОГДА ОНА НУЖНА.

    Ответ, положенный в кеш браузера или промежуточного узла (VPN, школьный прокси),
    вернётся `200` при мёртвой сети — и баннер «связи нет» не появится никогда.
    """
    _, _, zagolovki = _get(stend["url"] + "/api/zhiv")
    assert "no-store" in zagolovki.get("Cache-Control", "")


# ------------------------------------------------------- очередь доехала на страницу

def test_konduit_nesyot_ochered_i_oba_eyo_organa(stend):
    """Скрипт очереди, счётчик, баннер и полоса отказов — все на странице кондуита."""
    _, telo, _ = _get(stend["url"] + "/", _kuka(stend["prepod"]))
    stranica = telo.decode("utf-8")
    assert "window.OCHERED" in stranica
    assert 'id="och-schyot"' in stranica
    assert 'id="och-banner"' in stranica
    assert 'id="och-otkaz"' in stranica


def test_vremya_snimka_stavit_server_a_ne_brauzer(stend):
    """«Данные от такого-то времени» приезжает атрибутом, посчитанным на сервере.

    `NADEZHNOST-zakaz-na-resyorch.md` §2: настенные часы телефона в это не
    закладываются. Проверяется не значение (оно меняется каждую минуту), а то, что
    оно ПРИШЛО и имеет вид времени.
    """
    _, telo, _ = _get(stend["url"] + "/", _kuka(stend["prepod"]))
    najdeno = re.search(r'id="och-banner"[^>]*data-snyato="(\d\d:\d\d)"',
                        telo.decode("utf-8"))
    assert najdeno, "у баннера нет серверного времени снимка"


def test_ochered_obyavlena_ranshe_konduita(stend):
    """🔴 ПОРЯДОК СКРИПТОВ НЕСУЩИЙ, И ЕГО ПОЛОМКА НЕ ВИДНА ГЛАЗОМ.

    `KONDUIT_SKRIPT` зовёт `OCHERED.podpisatsya` в теле своей IIFE, то есть при
    разборе страницы. Стоя первым, он падает на `OCHERED is not defined` и уносит с
    собой ВЕСЬ свой скрипт: тап, историю клетки, липкую шапку. Страница при этом
    выглядит целой.
    """
    _, telo, _ = _get(stend["url"] + "/", _kuka(stend["prepod"]))
    stranica = telo.decode("utf-8")
    # Ищем ОБЪЯВЛЕНИЕ и ВЫЗОВ, а не имена: имя `OCHERED.podpisatsya` стоит ещё и в
    # шапке самого транспорта, где перечислен его интерфейс, — то есть РАНЬШЕ
    # объявления, и проверка по голому имени была бы красной всегда.
    assert (stranica.index("window.OCHERED = (function")
            < stranica.index("OCHERED.podpisatsya(function"))


def test_tap_konduita_idyot_cherez_ochered_a_ne_svoim_fetch(stend):
    """В кондуите не осталось собственного `fetch` к двери записи.

    Тап, который сам зовёт сеть, — это тап, который снова умеет зависнуть: ровно то,
    что владелец увидел 10.09. Дверь одна и та же (`/api/priyom`), но зовёт её теперь
    транспорт, и только он.
    """
    from veb.obshchee.karkas import KONDUIT_SKRIPT
    assert "OCHERED.postavit" in KONDUIT_SKRIPT
    assert "fetch(" not in KONDUIT_SKRIPT


def test_chisla_modulya_doehali_v_skript():
    """Порог «свежий / старый» и таймаут живут в Python и подставляются в JS.

    Копия числа внутри JavaScript разошлась бы и с документом, и с этим тестом молча.
    """
    js = ochered.skript()
    assert "@TAJMAUT@" not in js and "@STARYJ@" not in js
    assert "var TAJMAUT = %d;" % ochered.TAJMAUT_MS in js
    assert "var STARYJ = %d *" % ochered.STARYJ_CHEREZ_MINUT in js


# ------------------------------------------------ escape-последовательности в скриптах

def test_skripty_stranicy_kompiliruyutsya_bez_predupreghdenij_ob_escape():
    """🔴 ОДИНОЧНАЯ ОБРАТНАЯ КОСАЯ В НЕ-СЫРОЙ СТРОКЕ СО СКРИПТОМ — ЭТО ПОЛОМКА САЙТА.

    `KONDUIT_SKRIPT` в `veb/obshchee/karkas.py` — обычная питоновская строка, и
    JavaScript внутри неё полон регулярных выражений. `\\b` в такой строке становится
    символом ЗАБОЯ, `\\s` — недопустимой escape-последовательностью; в одних версиях
    Python это предупреждение, в других отказ импорта, и тогда страница не собирается
    ВООБЩЕ.

    ЦЕНА, ОПЛАЧЕННАЯ ЖИВЬЁМ В ЭТОМ ЖЕ ЗАХОДЕ: пост-проверка из ГЛАВНОЙ папки после
    влития упала на `SyntaxError: invalid escape sequence`. В рабочей папке ровно тот
    же код был зелёным на всех прогонах — там лежал уже скомпилированный `.pyc`, и
    предупреждение компиляции просто не повторялось. То есть тест на «работает ли»
    этого класса поломок не видит по построению; видит только компиляция начисто.
    """
    import py_compile
    import shutil
    import subprocess
    import sys
    from pathlib import Path

    koren = Path(__file__).resolve().parents[2]
    for fajl in ("veb/obshchee/karkas.py", "veb/razdely/konduit.py",
                 "veb/razdely/ochered.py", "veb/razdely/kartochka.py"):
        put = koren / fajl
        shutil.rmtree(put.parent / "__pycache__", ignore_errors=True)
        itog = subprocess.run(
            [sys.executable, "-W", "error::DeprecationWarning",
             "-W", "error::SyntaxWarning", "-c",
             "import py_compile,sys; py_compile.compile(%r, doraise=True)" % str(put)],
            capture_output=True, text=True)
        assert itog.returncode == 0, (
            "%s не компилируется начисто: %s" % (fajl, itog.stderr.strip()[-500:]))
    assert py_compile  # использован выше через подпроцесс


def test_v_skriptah_stranicy_net_upravlyayushchih_simvolov(stend):
    """Ни одного управляющего символа в том, что уезжает в браузер.

    Вторая половина той же проверки, и она смотрит не на исходник, а на ОТДАННУЮ
    страницу: `\\b`, ставший забоем, компиляции не мешает вовсе — он просто молча
    уезжает в регулярное выражение, которое после этого не совпадает ни с чем.
    Разрешены только те управляющие, которые в тексте законны: перевод строки,
    возврат каретки и табуляция.
    """
    _, telo, _ = _get(stend["url"] + "/", _kuka(stend["prepod"]))
    stranica = telo.decode("utf-8")
    plohie = sorted({c for c in stranica if ord(c) < 32 and c not in "\n\r\t"})
    assert not plohie, "управляющие символы на странице: %r" % [hex(ord(c))
                                                                for c in plohie]


# ------------------------------------------------------------------- Р5: запись при 18

def test_r5_vosemnadcat_odnovremennyh_zapisej_dohodyat_vse(stend):
    """🔴 Р5 ИЗ ЗАКАЗА НА РЕСЁРЧ, ЗАКРЫТЫЙ ЗАМЕРОМ, А НЕ ДОКУМЕНТОМ.

    Вопрос дословно: «Сериализация записи: `stdlib http.server` + SQLite при 18
    преподавателях, тапающих одновременно» — «у SQLite один писатель, нужен
    `busy_timeout` или очередь на стороне сервера, материалов ровно под этот стек не
    нашлось».

    Ответ: очередь на стороне сервера НЕ нужна, потому что она уже есть — WAL плюс
    `busy_timeout` на соединении каждого запроса (`veb/server.py::_connection`). Тест
    бьёт восемнадцатью одновременными записями по РАЗНЫМ клеткам (то есть без
    семантической идемпотентности, которая иначе съела бы половину) и требует, чтобы
    доехали все до одной. Снимите любую из двух прагм — он покраснеет.

    🔴 Он же сторожит и обратное: очередь В БРАУЗЕРЕ отправляет строго по одному, но
    браузеров на занятии восемнадцать, и параллельность никуда не девается.
    """
    kuka = _kuka(stend["prepod"])
    rebyonok = stend["deti"][0]
    zadachi = stend["zadachi"][:PREPODAVATELEJ]
    assert len(zadachi) == PREPODAVATELEJ

    with ThreadPoolExecutor(max_workers=PREPODAVATELEJ) as pul:
        itogi = list(pul.map(
            lambda z: _tap(stend["url"], rebyonok, z, "solved", kuka), zadachi))

    kody = [k for k, _ in itogi]
    assert kody == [200] * PREPODAVATELEJ, "не все записи ответили 200: %r" % kody
    assert all(o.get("sostoyanie") == "solved" for _, o in itogi)

    c = sqlite3.connect(f"file:{stend['db']}?mode=ro", uri=True)
    try:
        dosheli = {r[0] for r in c.execute(
            "select problem_id from marks where student_id = ? and event = 'assert'",
            (rebyonok,))}
    finally:
        c.close()
    assert dosheli == set(zadachi), "в журнале не хватает клеток: %r" % (
        set(zadachi) - dosheli)


def test_povtornaya_dostavka_togo_zhe_tapa_ne_pishet_vtoruyu_stroku(stend):
    """🔴 ПОЧЕМУ КЛИЕНТУ НЕ НУЖЕН СВОЙ КЛЮЧ ИДЕМПОТЕНТНОСТИ.

    Очередь пересылает запись, если ответ на неё потерялся в пути, — и второй раз она
    приходит с другим ключом, потому что ключ мнёт сервер (`veb/priyom.py::_klyuch`,
    вне зоны этой позиции). Дублем это не становится: `MarkingService` несёт
    СЕМАНТИЧЕСКУЮ идемпотентность — клетка, уже стоящая в целевом состоянии, не
    пишется второй раз. Это и есть допущение A2 из `## ПЛАН`, проверенное через живую
    дверь, а не вычитанное из кода службы.
    """
    kuka = _kuka(stend["prepod"])
    rebyonok, zadacha = stend["deti"][0], stend["zadachi"][0]

    pervyj = _tap(stend["url"], rebyonok, zadacha, "solved", kuka)
    vtoroj = _tap(stend["url"], rebyonok, zadacha, "solved", kuka)
    assert pervyj[0] == vtoroj[0] == 200
    assert pervyj[1]["zapisano"] is True
    assert vtoroj[1]["zapisano"] is False        # ответ честный, строки нет
    assert vtoroj[1]["sostoyanie"] == "solved"

    c = sqlite3.connect(f"file:{stend['db']}?mode=ro", uri=True)
    try:
        skolko = c.execute(
            "select count(*) from marks where student_id = ? and problem_id = ?",
            (rebyonok, zadacha)).fetchone()[0]
    finally:
        c.close()
    assert skolko == 1, "повторная доставка написала вторую строку"


def test_poryadok_tapov_po_odnoj_kletke_reshaet_poslednij(stend):
    """Две записи по одной клетке в порядке очереди дают состояние ПОСЛЕДНЕЙ.

    Очередь отправляет строго по одному, поэтому «поставил — снял» приезжает именно в
    этом порядке, и клетка остаётся пустой. Это то самое свойство, ради которого
    очередь не распараллеливается.
    """
    kuka = _kuka(stend["prepod"])
    rebyonok, zadacha = stend["deti"][1], stend["zadachi"][0]

    assert _tap(stend["url"], rebyonok, zadacha, "solved", kuka)[0] == 200
    posledniy = _tap(stend["url"], rebyonok, zadacha, "empty", kuka)
    assert posledniy[0] == 200
    assert posledniy[1]["sostoyanie"] == "empty"

    c = sqlite3.connect(f"file:{stend['db']}?mode=ro", uri=True)
    try:
        sobytia = [r[0] for r in c.execute(
            "select event from marks where student_id = ? and problem_id = ? "
            "order by id", (rebyonok, zadacha))]
    finally:
        c.close()
    # 🔴 Журнал только ДОПИСЫВАЕТСЯ: снятие — это вторая строка, а не удаление первой.
    assert sobytia == ["assert", "erratum"]
