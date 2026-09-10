"""ЖИВОЙ ПРОГОН: настоящий сервер, настоящий Chromium, настоящая отключённая сеть.

🔴 ЭТО ЕДИНСТВЕННОЕ МЕСТО, ГДЕ ТРЕБОВАНИЕ ВЛАДЕЛЬЦА ВООБЩЕ ПРОВЕРЯЕМО.  Его слова
10.09: *«если вдруг пропал интернет, ты мог всё равно внести плюсик, поставить галочку,
и она бы вносилась в тот момент, когда интернет появится»*.  Ни один тест на строках
этого не видит: очередь живёт в IndexedDB, отправка — в обработчике `fetch`, а
«интернет пропал» — состояние сетевого стека браузера.  Сеть здесь рвётся по-настоящему
(`context.set_offline`), а не подделкой ответа сервера: подделанный ответ приходит, и
проверялась бы тогда ветка, которой в жизни нет.

КРИТЕРИЙ ГОТОВНОСТИ ЗАХОДА, ДОСЛОВНО, И ОН МОЖЕТ ПРОВАЛИТЬСЯ.  Три состояния сети, у
каждого ДВА числа:

    сеть есть      → отметка уезжает сразу, в очереди 0
    сети нет       → отметка ВИДНА на экране, в очереди N, в базе 0
    сеть вернулась → в очереди 0, в базе N, порядок совпал с порядком нажатий

плюс: заведомо отвергаемая правка → значение вернулось, сообщение ОСТАЛОСЬ и называет
причину.  Каждая из строк ниже — одна из этих проверок, и «в базе» читается из SQLite,
а не со страницы.

⚠ ЧЕСТНЫЙ ПРЕДЕЛ ЭТОГО ФАЙЛА.  База здесь — свежая временная, а не боевая: на машине,
где шёл заход, `SPETSMAT_BAZA` не назван и живой базы на диске нет вовсе (она вне git с
10.09).  Сервер, браузер, IndexedDB и разрыв сети настоящие; данные — нет.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import date
from http.server import ThreadingHTTPServer

import config
import pytest
from infra.db import apply_migrations, connect

os.environ.setdefault("SPETSMAT_VEB_SECRET", "test-secret-key-32bytes!")

sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright

import veb.server as server                                          # noqa: E402
from veb import vhod                                                 # noqa: E402

#: Сколько клеток тапаем при мёртвой сети. Больше одной — потому что проверяется ещё и
#: ПОРЯДОК, а порядок одной записи неотличим от любого другого.
TAPOV = 4


def _nachalo_goda() -> str:
    s = date.today()
    return "%d-09-01" % (s.year if s.month >= 9 else s.year - 1)


@pytest.fixture(scope="module")
def stend(tmp_path_factory):
    """Сервер, браузер и база — один раз на файл: Chromium стоит секунду на запуск."""
    db_path = tmp_path_factory.mktemp("offlajn") / "spetsmat.db"
    apply_migrations(db_path, config.MIGRATIONS_DIR)
    c = connect(db_path)
    # Те же четыре колонки и те же коды групп, что и в `test_offlajn_ochered.py`, и по
    # той же причине: без них страница `/` не собирается вовсе.
    c.execute("alter table teachers add column aktiven integer not null default 1")
    c.execute("alter table teachers add column gruppa text")
    c.execute("alter table teachers add column kabinet text")
    c.execute("alter table students add column gruppa text")
    for kod, starshij in (("В", "Ваня Яковлев"), ("Д", "Даня Макаров"),
                          ("Н", "Наталия Стрелкова")):
        c.execute("insert or ignore into gruppy (kod, starshij) values (?, ?)",
                  (kod, starshij))
    listok = c.execute(
        "insert into sheets (number, title, issued_at, ord) "
        "values ('1', 'листок 1', ?, 1)", (_nachalo_goda(),)).lastrowid
    zadachi = [
        c.execute("insert into problems (sheet_id, label, kind, ord) "
                  "values (?, ?, 'обязательная', ?)", (listok, str(i), i)).lastrowid
        for i in range(1, TAPOV + 2)
    ]
    prepod = c.execute(
        "insert into teachers (name, aka, is_owner, aktiven, gruppa, kabinet) "
        "values ('Пирогов', 'pir', 0, 1, 'В', '203')").lastrowid
    deti = [
        c.execute("insert into students (surname, name, class, status, first_sheet_id) "
                  "values (?, 'Иван', '9a', 'active', ?)",
                  (f"Асеев-{i}", listok)).lastrowid
        for i in range(3)
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
    url = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        with sync_playwright() as pw:
            brauzer = pw.chromium.launch()
            try:
                yield {"url": url, "brauzer": brauzer, "db": db_path,
                       "prepod": prepod, "deti": deti, "zadachi": zadachi}
            finally:
                brauzer.close()
    finally:
        httpd.shutdown()
        httpd.server_close()
        potok.join()
        c.close()


def _v_baze(stend) -> list:
    """Клетки, стоящие в журнале как сданные, в порядке появления строк.

    Читается из SQLite, а не со страницы: экран показывает и то, что ещё только стоит
    в очереди, и вопрос «доехало ли» экраном не отвечается по построению.
    """
    c = sqlite3.connect(f"file:{stend['db']}?mode=ro", uri=True)
    try:
        return [r[0] for r in c.execute(
            "select problem_id from marks where event = 'assert' order by id")]
    finally:
        c.close()


def _sobytia(stend, student_id: int) -> list:
    """Все события журнала этого школьника парами (задача, событие), в порядке строк."""
    c = sqlite3.connect(f"file:{stend['db']}?mode=ro", uri=True)
    try:
        return [(r[0], r[1]) for r in c.execute(
            "select problem_id, event from marks where student_id = ? order by id",
            (student_id,))]
    finally:
        c.close()


def _stranica(stend):
    """Открытый кондуит на вкладке первого листка, с пустой очередью."""
    ctx = stend["brauzer"].new_context(viewport={"width": 1280, "height": 900})
    ctx.add_cookies([{"name": vhod.COOKIE_NAME,
                      "value": vhod._make_cookie("prepod", stend["prepod"]),
                      "url": stend["url"]}])
    page = ctx.new_page()
    page.goto(stend["url"] + "/", wait_until="networkidle", timeout=30000)
    page.evaluate("document.getElementById('p-kond').checked = true")
    page.evaluate("""() => {
      const m = [...document.querySelectorAll('#s-kond .tabbar label')]
        .find(l => !l.getAttribute('for').startsWith('k-vse'));
      if (m) document.getElementById(m.getAttribute('for')).checked = true; }""")
    # Дождаться, пока уляжется стартовая проба связи: пока она в полёте, счётчик ещё
    # не нарисован, и синхронное ожидание ниже читало бы отсутствующий атрибут. На
    # загруженной машине проба доходит не мгновенно — под полным прогоном набора это
    # давало красное на ровном месте.
    page.wait_for_function(
        "() => document.getElementById('och-schyot').hasAttribute('data-n')",
        timeout=30000)
    return ctx, page


def _v_ocheredi(page) -> int:
    """Сколько записей стоит в очереди — спрошено у самой очереди, а не у надписи."""
    return page.evaluate("() => OCHERED.vse().then(z => z.length)")


def _zhdat_ochered(page, n: int, timeout: int = 30000) -> None:
    """Дождаться, пока в очереди станет ровно `n`.

    🔴 ПРЕДИКАТ ОЖИДАНИЯ ОБЯЗАН БЫТЬ СИНХРОННЫМ. `OCHERED.vse()` отдаёт Promise, а
    `wait_for_function` видит его как обычное значение — то есть как истину, и
    просыпается НЕМЕДЛЕННО. Поймано живьём: проверка «отметка уехала» проходила,
    не дождавшись ни одной отправки. Синхронное зеркало длины очереди — атрибут
    `data-n` на счётчике, который очередь и так обновляет для человека.
    """
    page.wait_for_function(
        "n => document.getElementById('och-schyot').getAttribute('data-n') === n",
        arg=str(n), timeout=timeout)


def _tapnut(page, u: int, z: int) -> None:
    page.eval_on_selector(
        f'#s-kond .kond td[data-u="{u}"][data-z="{z}"]', "td => td.click()")


def _znak(page, u: int, z: int) -> str:
    return page.eval_on_selector(
        f'#s-kond .kond td[data-u="{u}"][data-z="{z}"]', "td => td.textContent.trim()")


# ══════════════════════════════════════════ СОСТОЯНИЕ 1: СЕТЬ ЕСТЬ

def test_set_est_otmetka_uezzhaet_srazu_i_ochered_pusta(stend):
    """Сеть есть → отметка уехала, в очереди 0. Два числа, как требует критерий."""
    ctx, page = _stranica(stend)
    try:
        rebyonok, zadacha = stend["deti"][0], stend["zadachi"][0]
        bylo = len(_v_baze(stend))
        _tapnut(page, rebyonok, zadacha)
        _zhdat_ochered(page, 0, timeout=30000)
        assert _v_ocheredi(page) == 0
        assert _znak(page, rebyonok, zadacha) == "✓"
        assert len(_v_baze(stend)) == bylo + 1
        # Пунктир «не подтверждено» снят: сервер ответил.
        assert not page.eval_on_selector(
            f'#s-kond .kond td[data-u="{rebyonok}"][data-z="{zadacha}"]',
            "td => td.classList.contains('v-ocheredi')")
        # Баннера деградации нет: связь жива.
        assert page.eval_on_selector("#och-banner", "el => el.hidden") is True
    finally:
        ctx.close()


# ══════════════════════════════════════════ СОСТОЯНИЯ 2 И 3: СЕТИ НЕТ, СЕТЬ ВЕРНУЛАСЬ

def test_seti_net_galochki_stoyat_v_ocheredi_i_uezzhayut_kogda_set_vernulas(stend):
    """🔴 ГЛАВНАЯ ПРОВЕРКА ЗАХОДА, И ОНА НЕСЁТ ОБА ОСТАВШИХСЯ СОСТОЯНИЯ ПОДРЯД.

    Сети нет  → отметки ВИДНЫ на экране, в очереди N, в базе 0 новых.
    Сеть есть → в очереди 0, в базе N, и порядок строк журнала совпал с порядком
                нажатий.

    Оба состояния меряются в одном сценарии нарочно: «уехало» имеет смысл только про
    то, что до этого стояло в очереди, и разрывать их на два теста значило бы дважды
    проверить половину.
    """
    ctx, page = _stranica(stend)
    try:
        rebyonok = stend["deti"][1]
        zadachi = stend["zadachi"][:TAPOV]
        bylo = _v_baze(stend)

        # ── СЕТИ НЕТ ────────────────────────────────────────────────────────────
        ctx.set_offline(True)
        for z in zadachi:
            _tapnut(page, rebyonok, z)
            page.wait_for_timeout(60)      # порядок нажатий, а не гонка кликов
        _zhdat_ochered(page, TAPOV, timeout=20000)

        # Число 1: в очереди ровно столько, сколько нажали.
        assert _v_ocheredi(page) == TAPOV
        # Число 2: в базе НИЧЕГО не прибавилось.
        assert _v_baze(stend) == bylo
        # И главное, ради чего всё: галочки СТОЯТ на экране.
        for z in zadachi:
            assert _znak(page, rebyonok, z) == "✓", "галочка не загорелась без сети"
            assert page.eval_on_selector(
                f'#s-kond .kond td[data-u="{rebyonok}"][data-z="{z}"]',
                "td => td.classList.contains('v-ocheredi')")

        # ── СЕТЬ ВЕРНУЛАСЬ ──────────────────────────────────────────────────────
        ctx.set_offline(False)
        page.evaluate("() => OCHERED.tolknut()")
        _zhdat_ochered(page, 0, timeout=45000)

        # Число 1: очередь пуста.
        assert _v_ocheredi(page) == 0
        # Число 2: в базе ровно те N, и В ТОМ ЖЕ ПОРЯДКЕ, в каком их нажимали.
        stalo = _v_baze(stend)
        assert stalo[len(bylo):] == zadachi, (
            "порядок в журнале разошёлся с порядком нажатий: %r против %r"
            % (stalo[len(bylo):], zadachi))
        # Пунктир снят со всех: сервер подтвердил каждую.
        assert page.eval_on_selector_all(
            "#s-kond .kond td.v-ocheredi", "tt => tt.length") == 0
    finally:
        ctx.close()


def test_bez_seti_stranica_chitaetsya_iz_snimka_s_bannerom_i_vremenem(stend):
    """Р7, состояние «снимок свежий»: баннер называет время, от которого данные.

    Проверяется ровно то, что обещано владельцу: сети нет — на экране остаётся то, что
    было прочитано, и НАД ним стоит объяснение, а не пустая страница и не ошибка
    браузера. Время берётся из атрибута, который поставил СЕРВЕР.
    """
    ctx, page = _stranica(stend)
    try:
        snyato = page.eval_on_selector("#och-banner", "el => el.dataset.snyato")
        assert snyato and ":" in snyato

        ctx.set_offline(True)
        page.evaluate("() => OCHERED.tolknut()")
        page.wait_for_function("() => !document.getElementById('och-banner').hidden",
                               timeout=20000)

        assert page.evaluate("() => OCHERED.sostoyanie()") == "svezhij"
        tekst = page.eval_on_selector("#och-banner", "el => el.textContent")
        assert "Связи с сервером нет" in tekst
        assert snyato in tekst, "баннер не называет время, от которого данные"
        # Решётка на месте: страница читается, а не заменена заглушкой.
        assert page.eval_on_selector_all(
            "#s-kond .kond td[data-u]", "tt => tt.length") > 0
    finally:
        ctx.close()


def test_staryj_snimok_govorit_drugoe_chem_svezhij(stend):
    """Третье состояние Р7 — то же отсутствие связи, но другой текст.

    Возраст здесь СДВИГАЕТСЯ, а не выжидается пятнадцать минут: тест, который ждёт
    четверть часа, не гоняют, а он ровно тогда и краснеет. Сдвигается монотонный
    отсчёт `performance.now()` — тот самый, по которому состояние и считается.
    """
    ctx, page = _stranica(stend)
    try:
        ctx.set_offline(True)
        page.evaluate("() => OCHERED.tolknut()")
        page.wait_for_function("() => !document.getElementById('och-banner').hidden",
                               timeout=20000)
        assert page.evaluate("() => OCHERED.sostoyanie()") == "svezhij"

        # Двадцать минут «назад»: `performance.now()` подменяется на время вперёд.
        page.evaluate("""() => {
          const bylo = performance.now.bind(performance);
          performance.now = () => bylo() + 20 * 60000;
        }""")
        page.evaluate("() => OCHERED.obnovit()")
        page.wait_for_function(
            "() => document.getElementById('och-banner').classList.contains('staryj')",
            timeout=10000)

        assert page.evaluate("() => OCHERED.sostoyanie()") == "staryj"
        tekst = page.eval_on_selector("#och-banner", "el => el.textContent")
        assert "мог изменить кто-то другой" in tekst
    finally:
        ctx.close()


# ══════════════════════════════════════════ ОТКАЗ: ЗАВЕДОМО ОТВЕРГАЕМАЯ ПРАВКА

def test_otvergnutaya_pravka_vozvrashchaet_znak_i_ostavlyaet_prichinu(stend):
    """🔴 ПОСЛЕДНЯЯ СТРОКА КРИТЕРИЯ ГОТОВНОСТИ, И ОНА ПРО ДОВЕРИЕ, А НЕ ПРО КНОПКУ.

    Заведомо отвергаемая правка — тап человеком, чей вход кончился: кука стёрта, сервер
    отвечает `403 нужно войти`. Случай не выдуманный и не редкий: кука живёт своё время,
    а занятие идёт полтора часа, и кончиться она может ровно посередине.

    Отказ такого рода повтором не чинится, поэтому запись ВЫБРАСЫВАЕТСЯ из очереди —
    иначе она навсегда заткнула бы всё, что стоит за ней, и человек, продолжая тапать,
    копил бы отметки, которые не уедут никогда. Клетка возвращается к тому, что стоит в
    журнале, ПРИЧИНА называется, и сообщение остаётся на экране: ни таймера, ни
    перезагрузки поверх.
    """
    ctx, page = _stranica(stend)
    try:
        rebyonok, zadacha = stend["deti"][0], stend["zadachi"][1]
        znak_do = _znak(page, rebyonok, zadacha)
        v_baze_do = _v_baze(stend)

        ctx.clear_cookies()          # вход кончился, страница об этом ещё не знает
        _tapnut(page, rebyonok, zadacha)

        page.wait_for_function("() => !document.getElementById('och-otkaz').hidden",
                               timeout=20000)
        # Очередь не заткнулась: отказная запись из неё ушла.
        _zhdat_ochered(page, 0, timeout=30000)
        # В журнал при этом не попало ничего.
        assert _v_baze(stend) == v_baze_do
        # Знак вернулся к тому, что стоит в журнале.
        assert _znak(page, rebyonok, zadacha) == znak_do
        # Причина названа и СТОИТ — ни таймера, ни перезагрузки.
        polosa = page.eval_on_selector("#och-otkaz", "el => el.textContent")
        assert "Не сохранилось" in polosa
        assert "войти" in polosa, "полоса отказа не назвала причину: %r" % polosa
        page.wait_for_timeout(2500)
        assert page.eval_on_selector("#och-otkaz", "el => el.hidden") is False, (
            "сообщение об отказе исчезло само — ровно то, что запрещено")
        # И клетка помечена отказом, чтобы вопрос «какая именно» имел ответ.
        assert page.eval_on_selector(
            f'#s-kond .kond td[data-u="{rebyonok}"][data-z="{zadacha}"]',
            "td => td.classList.contains('otkazano')")
    finally:
        ctx.close()


# ══════════════════════════════════════════ СТОЛКНОВЕНИЕ КЛЮЧЕЙ ИДЕМПОТЕНТНОСТИ

def test_odna_kletka_neskolko_raz_podryad_ne_teryaet_ni_odnogo_tapa(stend):
    """🔴 ДЫРА, НАЙДЕННАЯ ВЕРИФИКАТОРОМ §3, И ОНА ТЕРЯЛА ОТМЕТКИ МОЛЧА.

    Ключ идемпотентности мнёт СЕРВЕР (`veb/priyom.py::_klyuch`, вне зоны этой
    позиции), и в нём стоит СЕКУНДА ОБРАБОТКИ. Пока тап шёл прямо из пальца, две
    одинаковые цели по одной клетке в одну секунду были редкой гонкой. Очередь
    укладывает весь вывоз в доли секунды — и «поставил · снял · поставил» приезжало
    тремя запросами в одну секунду: третий ловил ключ первого, служба отвечала
    `200 zapisano:false` и ТЕКУЩИМ состоянием, а клетка на экране переворачивалась в
    пустоту без единого сообщения.

    ЗАМЕР ВЕРИФИКАТОРА: 15 потерь из 15 клеток при мёртвой сети (30 строк вместо 45);
    тот же ритм при живой сети — 1 из 15.

    Здесь берутся ТРИ клетки и по три тапа на каждую: одной было бы мало — потеря
    зависит от того, попали ли два одинаковых запроса в одну секунду, и один прогон
    мог бы случайно разъехаться по границе секунды и позеленеть зря.
    """
    ctx, page = _stranica(stend)
    try:
        rebyonok = stend["deti"][2]
        kletki = stend["zadachi"][:3]
        bylo = _sobytia(stend, rebyonok)

        ctx.set_offline(True)
        for z in kletki:
            for _ in range(3):                 # ✓ → пусто → ✓
                _tapnut(page, rebyonok, z)
                page.wait_for_timeout(60)
        _zhdat_ochered(page, 9, timeout=25000)

        ctx.set_offline(False)
        page.evaluate("() => OCHERED.tolknut()")
        _zhdat_ochered(page, 0, timeout=60000)

        stalo = _sobytia(stend, rebyonok)
        novye = stalo[len(bylo):]
        assert len(novye) == 9, (
            "потерян тап: строк %d вместо 9 — %r" % (len(novye), novye))
        for z in kletki:
            svoi = [e for (p_id, e) in novye if p_id == z]
            assert svoi == ["assert", "erratum", "assert"], (
                "клетка %s кончила не тем, что нажимали: %r" % (z, svoi))
            # И на экране стоит галочка, а не пустота.
            assert _znak(page, rebyonok, z) == "✓", (
                "галочка перевернулась в пустоту после вывоза — клетка %s" % z)
    finally:
        ctx.close()


def test_ochered_perezhivaet_perezagruzku_stranicy(stend):
    """Очередь и галочки переживают `location.reload()`, а не «слетают».

    Точка 4 задания запрещает молчаливую потерю правки на глазах человека, и
    перезагрузка — самый обычный способ её потерять: страница приходит с сервера, а в
    журнале ещё ничего нет. iOS Safari перезагружает вкладку, вернувшуюся из фона, сам
    и без спроса, так что это не редкий случай, а рядовой.
    """
    ctx, page = _stranica(stend)
    try:
        rebyonok, zadacha = stend["deti"][1], stend["zadachi"][TAPOV]
        ctx.set_offline(True)
        _tapnut(page, rebyonok, zadacha)
        _zhdat_ochered(page, 1, timeout=20000)

        # Перезагрузка при мёртвой сети: страница берётся из кеша браузера, поэтому
        # `reload` тут не делается — он бы просто не открылся (сервис-воркера нет, и
        # это объявленный предел). Сеть возвращается, страница перечитывается, и
        # вопрос ровно один: пережила ли ОЧЕРЕДЬ этот перечит.
        ctx.set_offline(False)
        page.reload(wait_until="networkidle", timeout=30000)
        page.evaluate("document.getElementById('p-kond').checked = true")
        page.evaluate("""() => {
          const m = [...document.querySelectorAll('#s-kond .tabbar label')]
            .find(l => !l.getAttribute('for').startsWith('k-vse'));
          if (m) document.getElementById(m.getAttribute('for')).checked = true; }""")

        _zhdat_ochered(page, 0, timeout=45000)
        assert _znak(page, rebyonok, zadacha) == "✓"
        assert zadacha in _v_baze(stend), "отметка не доехала после перезагрузки"
    finally:
        ctx.close()
