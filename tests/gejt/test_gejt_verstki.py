"""Two-state tests for the layout gate: with the defect it must go RED, without it
GREEN.  Written 2026-09-10, after the gate reported «обрезанных у гостя 48 → 0»
while the owner was looking at a clipped name on the very same page.

🔴 WHY THESE TESTS EXIST AND WHY THEY LOOK LIKE THIS.  A gate is judged by what it
catches, and «I ran it and it was green» proves nothing about a gate that is green
because it looked at nothing.  Every test here therefore runs the gate's own
measuring script -- imported from `tools/gejt_verstki`, never copied, so a test can
never drift into passing against a script the tool no longer uses -- on the REAL
page, in TWO states, and asserts BOTH of them:

    defect present  -> the check reports it
    defect removed  -> the check reports nothing

Only the pair is a test.  The first half alone passes for a gate that reports
everything; the second half alone passes for a gate that reports nothing, and that
is exactly the gate this project had.

The defects are injected in the BROWSER, not in `veb/**`: the page's own CSS is a
neighbour's zone, and a test that edits it would be testing the edit.
"""

from __future__ import annotations

import importlib.util
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

KOREN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOREN))

_spec = importlib.util.spec_from_file_location(
    "gejt_verstki", KOREN / "tools" / "gejt_verstki.py")
gejt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gejt)                      # noqa: E402

pytest.importorskip(
    "playwright.sync_api",
    reason="гейт вёрстки судит РЕНДЕР: без браузера его нечем прогнать. "
           "Поставить: pip install playwright && playwright install chromium")


# ── the page under test, booted once ──────────────────────────────────────────

@pytest.fixture(scope="module")
def server():
    # 🔴 «НЕТ БАЗЫ» — ЭТО ПРОПУСК, А НЕ ПАДЕНИЕ, И ЭТО ИЗМЕНЕНИЕ ПО СУЩЕСТВУ.
    # Пока `data/spetsmat.db` лежала в репозитории, «база есть всегда» было правдой и
    # `pytest.fail` означал настоящую поломку. База ушла из git по решению владельца
    # 10.09, и с тех пор то же падение означает всего лишь «на этой машине источник не
    # назван» — то есть красное, которое ни о чём не говорит и которое перестают читать.
    # Пропуск ЧЕСТНЕЕ: он говорит «не проверено», и он исчезает, стоит назвать источник.
    try:
        put = gejt.baza()
    except SystemExit as otkaz:
        pytest.skip("источник не назван: %s" % str(otkaz).splitlines()[0])
    if not put.exists():
        pytest.skip(f"названной базы {put} нет на диске — гейт судит настоящую "
                    "страницу, а не фикстуру, и открывать ему нечего")
    httpd, conn, t, url = gejt.podnyat_server(put)
    try:
        yield url
    finally:
        httpd.shutdown(); httpd.server_close(); t.join(); conn.close()


@pytest.fixture(scope="module")
def brauzer():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        yield b
        b.close()


def _stranica(brauzer, url, rol, put, radio):
    ctx = brauzer.new_context(viewport=gejt.ETALON)
    if rol == "организатор":
        ctx.add_cookies([{**gejt.kuka(), "url": url}])
    p = ctx.new_page()
    p.goto(url + put, wait_until="networkidle", timeout=20000)
    if radio:
        assert p.query_selector("#" + radio), (
            f"переключателя #{radio} нет на {put}: гейт молча меряет не тот экран")
        p.evaluate("(i)=>document.getElementById(i).checked=true", radio)
        p.wait_for_timeout(200)
    return ctx, p


def _zamer(p):
    return p.evaluate(gejt.ZAMER)


# ── 1. the owner's defect: a clipped surname, guest role ───────────────────────

def test_obrezka_familii_u_gostya(server, brauzer):
    """The cause of «обрезанных у гостя 48 → 0»: the walk kept LEAF elements only,
    and the box that clips (`.kto`) always wraps `<b>SURNAME</b>`, so not one of
    them was ever looked at.  Measured live on 2026-09-10, guest, tab «школьникам»:
    113 `.kto` on the page, 0 of them leaves, 1 of them clipped — and the gate said
    zero.

    🔴 THE DAMAGE IS INJECTED, NOT BORROWED FROM THE PAGE.  The first version of
    this test asserted that the live page still clips «Тухватулин-Йалчын …», and it
    went red the same afternoon — a neighbour widened the column and the defect was
    gone.  A test that needs the page to stay broken is a test that punishes the
    fix; what must be pinned is the GATE's ability to see a clipped non-leaf, not
    the presence of today's bug."""
    ctx, p = _stranica(brauzer, server, "гость", "/raspredelenie", "t-shk")
    try:
        do = _zamer(p)

        # The whole cause, stated as a measurement rather than as an argument.
        pro_kto = p.evaluate("""() => {
            const k = [...document.querySelectorAll('#v-shk .kto')].filter(e => {
                const r = e.getBoundingClientRect(); return r.width > 1; });
            const list = e => ![...e.children].some(
                c => (c.textContent || '').trim().length > 0);
            return {vsego: k.length, listyev: k.filter(list).length};
        }""")
        assert pro_kto["vsego"] > 50, "на странице нет колонки имён — мерить нечего"
        assert pro_kto["listyev"] == 0, (
            "разметка изменилась: `.kto` стал листом. Тогда причина ложно-зелёного "
            "описана неверно и этот тест больше ничего не стережёт")

        p.evaluate("""() => document.querySelectorAll('#v-shk .kto').forEach(e => {
            e.style.maxWidth = '60px'; e.style.overflow = 'hidden';
            e.style.whiteSpace = 'nowrap'; e.style.textOverflow = 'ellipsis'; })""")
        p.wait_for_timeout(200)
        posle = _zamer(p)
        clip = [d for d in posle["obrezka"] if ".kto" in d["put"]]
        assert len(clip) > 10, (
            f"колонка имён раздавлена до 60px, а гейт нашёл {len(clip)} обрезок на "
            "`.kto` — это ровно то ложно-зелёное, ради которого написан этот тест: "
            "обрезающий узел не лист, и обход, оставляющий только листья, его теряет")

        p.evaluate("""() => document.querySelectorAll('#v-shk .kto').forEach(e => {
            e.style.maxWidth = ''; e.style.overflow = '';
            e.style.whiteSpace = ''; e.style.textOverflow = ''; })""")
        p.wait_for_timeout(200)
        chisto = _zamer(p)
        assert len(chisto["obrezka"]) == len(do["obrezka"]), (
            "обрезку сняли, а гейт всё ещё её показывает: "
            f"{len(do['obrezka'])} → {len(chisto['obrezka'])}. Гейт, который не "
            "умеет зеленеть, так же бесполезен, как молчащий")
    finally:
        ctx.close()


# ── 2. the check the gate did not have: content outside its card ──────────────

def test_vyhod_za_konteyner(server, brauzer):
    """Owner's screenshot `13`: the pills «Бирюков», «Аникина», «Белеванцева» stand
    LEFT of the card of the teacher who owns them, and the document does NOT
    scroll — so the three older checks are blind to it by construction."""
    ctx, p = _stranica(brauzer, server, "гость", "/raspredelenie", "t-Д")
    try:
        chisto = _zamer(p)
        assert chisto["na_vyhod"] > 0, (
            "проверке «вышло за контейнер» не досталось ни одного узла — "
            "она зелена потому, что ничего не смотрела")

        p.evaluate("""() => document.querySelectorAll('.kol-pr .para').forEach(pa => {
            pa.style.background = 'rgba(255,255,255,.06)';
            pa.style.borderRadius = '8px';
            pa.querySelectorAll('.deti-ryad span').forEach(
                s => s.style.marginLeft = '-120px'); })""")
        p.wait_for_timeout(150)
        slomano = _zamer(p)

        assert slomano["vyshli"], (
            "таблетки стоят левее своей карточки, а гейт зелёный — это дефект "
            "класса G5, ради которого проверка и добавлена")
        assert all(d["vlevo"] > 1 for d in slomano["vyshli"][:3]), (
            "выход посчитан не в ту сторону: на скриншоте `13` содержимое уходит "
            "ВЛЕВО")
        assert slomano["skroll"] == 0, (
            "подстроен не тот дефект: если появился горизонтальный скролл, его "
            "поймала бы и старая проверка 3, и тест ничего нового не доказывает")

        p.evaluate("""() => document.querySelectorAll('.kol-pr .para').forEach(pa => {
            pa.style.background = ''; pa.style.borderRadius = '';
            pa.querySelectorAll('.deti-ryad span').forEach(
                s => s.style.marginLeft = ''); })""")
        p.wait_for_timeout(150)
        assert len(_zamer(p)["vyshli"]) == len(chisto["vyshli"]), (
            "дефект убрали, а число выходов не вернулось к тому, что было до него")
    finally:
        ctx.close()


# ── 3. the gate must not cry wolf ─────────────────────────────────────────────

@pytest.mark.parametrize("rol,put,radio,ekran", [
    ("гость",       "/raspredelenie", "t-prep", "принимающим"),
    ("гость",       "/glavnaya",      "p-start", "класс"),
    ("организатор", "/raspredelenie", "t-prep", "принимающим"),
])
def test_zdorovyy_ekran_zelyonyy(server, brauzer, rol, put, radio, ekran):
    """Красное на здоровом — ложный гейт, и такой гейт обходят.  These screens
    carry a `<select>` whose widest option is wider than the closed control, a
    `<style>` block inside a section that clips a decoration on purpose, and rows
    separated by a border-BOTTOM.  All three were reported as defects on 10.09 —
    56 clipping lines and 108 escape lines per run — and none of them cuts a
    letter or leaves a card."""
    ctx, p = _stranica(brauzer, server, rol, put, radio)
    try:
        z = _zamer(p)
        assert z["obrezka"] == [], f"{ekran}/{rol}: ложная обрезка {z['obrezka'][:2]}"
        assert z["perenos"] == [], f"{ekran}/{rol}: ложный перенос {z['perenos'][:2]}"
        assert z["vyshli"] == [], f"{ekran}/{rol}: ложный выход {z['vyshli'][:2]}"
        assert z["skroll"] == 0, f"{ekran}/{rol}: горизонтальный скролл {z['skroll']}"
    finally:
        ctx.close()


# ── 4. coverage: a walk that looked at nothing must not read as clean ─────────

# 🔴 ЭКРАНЫ БОЛЬШЕ НЕ КОНСТАНТА, И ЭТО ПРОВЕРЯЕТСЯ ОТДЕЛЬНО ОТ ИХ СОДЕРЖИМОГО.
# `gejt.EKRANY` собирается при импорте из РОУТОВ живого `veb/server.py`; когда
# источник не назван, список законно пуст, и параметризация пустым списком тихо
# не выполняет НИ ОДНОГО теста — то самое «ноль находок значит не смотрел», от
# которого написан весь этот файл.  Поэтому пустой список — отдельный пропуск с
# причиной, а не молчание.
_EKRANY = gejt.EKRANY or [(None, None, None, None)]


@pytest.mark.parametrize("imya,put,radio,roli", _EKRANY)
def test_ohvat_ne_nol(server, brauzer, imya, put, radio, roli):
    """Every screen the gate claims to judge must exist, open, and hand the walks
    a non-zero number of nodes.  🔴 This is the test that would have caught the
    second cause on its own: the table named `p-rasp`/`p-start`/`p-kond`, which
    are the SITE radios (`name="str"`), while the tabs inside распределение are
    `t-shk`/`t-prep`/`t-В`/`t-Д`/`t-Н` (`name="vk"`).  The gate opened the same
    default view four times and never reached a group tab at all.

    🔴 ПРОВЕРКА 4 (ВЫХОД ЗА КОНТЕЙНЕР) ЗДЕСЬ НЕ ТРЕБУЕТСЯ, И ЭТО НЕ ПОБЛАЖКА.
    Её население — элементы, у которых ЕСТЬ видимый контейнер-предок (рамка, фон
    или клип); на странице без карточек (`/vhod`, `/privacy`, карточка школьника
    у гостя) таких нет ни одного законно, и требовать их значило бы красить
    здоровые страницы.  Число печатается гейтом в колонке охвата на каждом
    экране, так что ноль виден и без падения теста."""
    if put is None:
        pytest.skip("источник не назван: `gejt.EKRANY` пуст, строить экраны не из чего")
    rol = roli[0]
    ctx, p = _stranica(brauzer, server, rol, put, radio)
    try:
        z = _zamer(p)
        assert z["vsego"] > 0, f"{imya}: на странице ноль элементов"
        assert z["na_obrezku"] > 0, f"{imya}: проверке ОБРЕЗКИ не досталось узлов"
        assert z["osmotreno"] > 0, f"{imya}: проверке ПЕРЕНОСА не досталось узлов"
        assert z["na_centr"] > 0, f"{imya}: проверке ЦЕНТРА не досталось узлов"
    finally:
        ctx.close()


def test_ekrany_razlichny(server, brauzer):
    """Two TABS of распределение must not be the same screen.  When the radio ids
    were wrong every row of the table measured the identical DOM and the four
    numbers agreed perfectly — which reads exactly like four clean pages."""
    vidy = {}
    for imya, put, radio, roli in gejt.EKRANY:
        if "гость" not in roli or put != "/raspredelenie":
            continue
        ctx, p = _stranica(brauzer, server, "гость", put, radio)
        try:
            vidy[imya] = _zamer(p)["na_obrezku"]
        finally:
            ctx.close()
    assert len(vidy) >= 5, f"вкладок распределения найдено {len(vidy)}, ждали пять"
    assert len(set(vidy.values())) == len(vidy), (
        f"разные вкладки распределения дали одинаковый охват {vidy} — "
        "гейт меряет один и тот же экран под разными именами")


# ── 4.1 the list of screens itself: it is DERIVED, and that is testable ───────

def test_spisok_ekranov_stroitsya_iz_routov():
    """🔴 ГЛАВНАЯ ПРОВЕРКА ЭТОЙ ПРАВКИ, И ОНА НЕ ПРО ВЁРСТКУ.  До 11.09 список
    экранов был десятью рукописными строками, и `/istoria` с `/kabinet` в нём
    отсутствовали ПОЛНОСТЬЮ — ноль вхождений обоих слов в файле гейта.  Так
    страница с 321 строкой кода и 29 зелёными тестами дожила невидимой до
    владельца: гейт был формально прав, его туда не посылали.

    Здесь проверяется не «в списке есть две нужные строки» (это лечится
    дописыванием двух строк и ломается на третьей), а что список ПОРОЖДЁН
    маршрутами: каждый маршрут-страница обязан дать хотя бы один экран."""
    marshruty = gejt.marshruty_sayta()
    assert "/istoria" in marshruty, "маршрут истории не найден в `veb/server.py`"
    assert "/kabinet" in marshruty, "маршрут кабинета не найден в `veb/server.py`"
    assert "/raspredelenie" in marshruty and "/" in marshruty

    try:
        db = gejt.zhivaya_baza()
    except SystemExit as otkaz:
        pytest.skip("источник не назван: %s" % str(otkaz).splitlines()[0])
    ekrany, bedy = gejt.sobrat_ekrany(db)
    assert bedy == [], f"маршруты, не ставшие экраном: {bedy}"

    stranicy = {p for p, rod in marshruty.items() if rod == "stranica"}
    pokryto = {put for _i, put, _r, _rl in ekrany}
    ne_pokryto = stranicy - pokryto
    assert not ne_pokryto, (
        f"маршрут есть, экрана нет: {sorted(ne_pokryto)} — ровно так «список "
        f"отстаёт от сайта», из-за чего мёртвая история дожила до владельца")

    # ...и хвостовые маршруты подставили ЖИВОЙ объект, а не выдуманный.
    for pref in gejt.HVOSTY:
        assert any(put.startswith(pref) and put != pref for put in pokryto), (
            f"маршрут «{pref}» открывается по хвосту, а экрана с живым хвостом нет")


def test_ekran_ushedshiy_s_servera_ne_izmeryaetsya():
    """🔴 ГЕЙТ ОБЯЗАН МЕРИТЬ ТОТ САЙТ, КОТОРЫЙ САМ И ПОДНЯЛ.  Найдено 11.09 первым
    прогоном по роутам: гостю корень отдаёт `docs/index.html`, а это заглушка
    переадресации на `http://math-kluychiki.ru/` (`docs/index.html:13`, `:34`),
    и браузер уходил туда.  Четыре экрана гостя печатали одинаковые
    46/45/72/78 из 2063 — числа настоящие, документ ЧУЖОЙ, и роль гостя завели
    десятого числа именно затем, чтобы смотреть на страницу без пароля.

    Правило испытывается литералами, без сети: доступен ли сегодня чужой хост —
    не то, от чего должен зависеть зелёный цвет теста."""
    baza = "http://127.0.0.1:54321"
    assert gejt.svoy_dom(baza, baza + "/raspredelenie")
    assert gejt.svoy_dom(baza, baza + "/")
    assert not gejt.svoy_dom(baza, "http://math-kluychiki.ru/")
    assert not gejt.svoy_dom(baza, "http://127.0.0.1:54322/")
    # 🔴 И ПРЕФИКС НЕ ОБМАНЫВАЕТСЯ ХОСТОМ, КОТОРЫЙ НАЧИНАЕТСЯ ТАК ЖЕ: порт 54321
    # против 543210 — разные серверы.  Сравнение по началу строки здесь законно
    # ровно потому, что за адресом гейта всегда идёт «/» или конец строки.
    assert not gejt.svoy_dom(baza, "http://127.0.0.1:54321x/")


def test_pereadresaciya_svoditsya_a_ne_schitaetsya_vtorym_ekranom(server, brauzer):
    """`/glavnaya`, `/listki`, `/listki-8` отвечают 302 на `/`.  Раз список
    экранов строится из роутов, они приходят в него сами — и обязаны СВЕСТИСЬ к
    цели, а не дать по второму «зелёному экрану» с тем же числом: раздутый охват
    врёт ровно в ту же сторону, что и охват заниженный.

    Обе половины: правило — на литералах, факт переадресации — на живом сервере.
    (`gejt.progon` здесь позвать нельзя: он открывает СВОЙ `sync_playwright`, а
    в этом модуле один уже открыт фикстурой `brauzer`, и Playwright запрещает
    вложение — ошибка выглядела бы как поломка гейта, а её там нет.)"""
    baza = "http://127.0.0.1:54321"
    assert (gejt.klyuch_ekrana(baza, baza + "/", None)
            == gejt.klyuch_ekrana(baza, baza + "/?den=2026-09-10", None)), (
        "запрос в адресе не делает экран другим экраном")
    assert (gejt.klyuch_ekrana(baza, baza + "/", "p-start")
            != gejt.klyuch_ekrana(baza, baza + "/", "p-kond")), (
        "разные вкладки одной страницы — разные экраны")

    ctx, p = _stranica(brauzer, server, "организатор", "/glavnaya", None)
    try:
        assert p.url == server + "/", (
            f"`/glavnaya` больше не переадресует на корень (стоит {p.url}) — "
            "сведение экранов надо пересмотреть")
        assert (gejt.klyuch_ekrana(server, p.url, None)
                == gejt.klyuch_ekrana(server, server + "/", None))
    finally:
        ctx.close()


def test_spisok_ekranov_ne_perepisan_rukami():
    """Список остаётся ПРОИЗВОДНЫМ.  Тест ловит откат к константе: если завтра
    кто-то снова впишет экраны руками, `marshruty_sayta()` перестанет быть их
    источником, и вот это равенство разойдётся."""
    try:
        db = gejt.zhivaya_baza()
    except SystemExit as otkaz:
        pytest.skip("источник не назван: %s" % str(otkaz).splitlines()[0])
    ekrany, _ = gejt.sobrat_ekrany(db)
    marshruty = gejt.marshruty_sayta()
    for _imya, put, _radio, _roli in ekrany:
        znakom = put in marshruty or any(
            put.startswith(pref) for pref in gejt.HVOSTY)
        assert znakom, (f"экран «{put}» не происходит ни от одного маршрута — "
                        f"список снова пишется руками")


# ── 5. the four holes a fresh verifier walked through on 2026-09-10 ───────────
#
# 🔴 EACH OF THESE WAS A REAL MISS, FOUND BY BREAKING THE PAGE, NOT BY READING THE
# CODE.  They are here so that closing them stays closed: every one is again a
# PAIR — the damage present and caught, the damage removed and quiet.

def _para(brauzer, url, rol, put, radio, lomka, chinka):
    ctx, p = _stranica(brauzer, url, rol, put, radio)
    try:
        do = _zamer(p)
        p.evaluate(lomka); p.wait_for_timeout(200)
        posle = _zamer(p)
        p.evaluate(chinka); p.wait_for_timeout(200)
        return do, posle, _zamer(p)
    finally:
        ctx.close()


def test_obrezka_po_vysote(server, brauzer):
    """`.kto{height:7px;overflow:hidden}` left twenty names as a seven-pixel smear,
    unreadable on the screenshot, and the gate reported the same number it had
    before the damage: check 1 compared only scrollWidth to clientWidth."""
    do, posle, chisto = _para(
        brauzer, server, "гость", "/raspredelenie", "t-shk",
        "()=>document.querySelectorAll('#v-shk .kto').forEach(e=>{"
        "e.dataset.h=e.style.height;e.style.height='7px';e.style.overflow='hidden';})",
        "()=>document.querySelectorAll('#v-shk .kto').forEach(e=>{"
        "e.style.height=e.dataset.h||'';e.style.overflow='';})")
    assert len(posle["obrezka"]) > len(do["obrezka"]), (
        "текст срезан снизу, а гейт показывает то же число, что до порчи")
    assert any(d.get("storona") == "ввысь" for d in posle["obrezka"]), (
        "обрезка найдена, но не опознана как вертикальная")
    assert len(chisto["obrezka"]) == len(do["obrezka"]), "не зеленеет обратно"


def test_uhod_vlevo_iz_klipayushchey_kartochki(server, brauzer):
    """The mirror of the bug this file was rewritten for.  `scrollWidth` never grows
    leftwards in a left-to-right document, so content walking out of a card's LEFT
    edge is painted nowhere and was counted nowhere: the verifier emptied an entire
    column and the gate stayed at (0,0,0,0), while the SAME shift to the right gave
    a red."""
    do, posle, chisto = _para(
        brauzer, server, "организатор", "/raspredelenie", "t-Д",
        "()=>document.querySelectorAll('.kol-pr .para').forEach(p=>{"
        "p.style.overflow='hidden';"
        "p.querySelectorAll('*').forEach(c=>{"
        "c.style.position='relative';c.style.left='-260px';});})",
        "()=>document.querySelectorAll('.kol-pr .para').forEach(p=>{"
        "p.style.overflow='';"
        "p.querySelectorAll('*').forEach(c=>{"
        "c.style.position='';c.style.left='';});})")
    assert posle["vyshli"], "содержимое ушло за левый край карточки, а гейт зелёный"
    assert any(d["tip"] == "срезано слева" for d in posle["vyshli"])
    assert posle["skroll"] == 0, (
        "подстроен не тот дефект: скролл поймала бы и старая проверка 3")
    # 🔴 СРАВНЕНИЕ С «БЫЛО», А НЕ С НУЛЁМ.  На живой странице у организатора на
    # вкладке группы Д уже стоят два настоящих выхода (таблетки школьников торчат
    # на 6 px вправо за рамку карточки), и требовать здесь ноль значило бы, что
    # тест зелен только пока страница идеальна — ровно та ошибка, из-за которой
    # `test_obrezka_familii_u_gostya` покраснел от чужой ПОЧИНКИ.
    assert len(chisto["vyshli"]) == len(do["vyshli"]), (
        f"порчу убрали, а число выходов не вернулось: "
        f"{len(do['vyshli'])} → {len(chisto['vyshli'])}")


def test_kontrol_ne_oslepljaet_predka(server, brauzer):
    """🔴 THE REGRESSION.  Excluding a form control also excluded every ANCESTOR of
    one — and on the organiser's screens that is nearly every row.  Squeezing the
    left column so that names were visibly cut made the gate GREENER than it was
    on the sound page.  The guest, whose rows carry no controls, saw the same
    damage correctly: that asymmetry is the whole test."""
    lomka = ("()=>document.querySelectorAll('#v-shk .kto').forEach(e=>{"
             "e.style.maxWidth='150px';e.style.overflow='hidden';"
             "e.style.whiteSpace='nowrap';e.style.textOverflow='ellipsis';})")
    chinka = ("()=>document.querySelectorAll('#v-shk .kto').forEach(e=>{"
              "e.style.maxWidth='';e.style.overflow='';"
              "e.style.whiteSpace='';e.style.textOverflow='';})")
    for rol in ("гость", "организатор"):
        do, posle, chisto = _para(
            brauzer, server, rol, "/raspredelenie", "t-shk", lomka, chinka)
        assert len(posle["obrezka"]) > len(do["obrezka"]) + 5, (
            f"{rol}: колонка имён раздавлена до 150px, обрезка "
            f"{len(do['obrezka'])} → {len(posle['obrezka'])} — "
            "у организатора в каждой строке <select>, и он не смеет ослеплять строку")
        assert len(chisto["obrezka"]) == len(do["obrezka"]), f"{rol}: не зеленеет"


def test_samoproverka_chestna_o_svoey_polomke(server, brauzer):
    """`--slomat` announced «13 экранов из 13» while on five of them only the
    h-scroll had fired.  Every breakage must now report whether it actually landed,
    so a self-test can never pass on damage it failed to inflict."""
    ctx, p = _stranica(brauzer, server, "гость", "/raspredelenie", "t-shk")
    try:
        otchet = p.evaluate(gejt.LOMKA)
        assert set(otchet) == {"obrezka", "perenos", "vyhod", "skroll", "centr"}, (
            "поломка не отчитывается о том, села ли она")
        p.wait_for_timeout(200)
        z = _zamer(p)
        for klyuch_lom, klyuch_zam in (("obrezka", "obrezka"), ("perenos", "perenos"),
                                       ("vyhod", "vyshli")):
            if otchet[klyuch_lom]:
                assert z[klyuch_zam], (
                    f"поломка «{klyuch_lom}» отчиталась, что села, а проверка "
                    f"«{klyuch_zam}» ничего не нашла — это ложно-зелёная "
                    "самопроверка, тот же класс, что и ложно-зелёный гейт")
    finally:
        ctx.close()


# ── 6. центрирование: правило канона, которое до сих пор было текстом ─────────
#
# 🔴 «НИКОГДА по центру мы не центрируем» — владелец, 10.09 11:4x, ЧЕТВЁРТЫЙ
# возврат одного и того же дефекта.  Он же назвал причину: правило обязано
# КРАСНЕТЬ, а не жить строкой в документе.  Тесты ниже стерегут ровно это: что
# проверка 5 видит центрирование, что она видит его ПО РЕНДЕРУ (а не по строке в
# разметке), что она называет ОДНО место вместо всего поддерева, и что
# именованное исключение остаётся прощённым.

def test_centr_krasneet_i_zelenet(server, brauzer):
    """Пара, как у обрезки: центрирование поставили — красный, убрали — вернулось
    ТО ЖЕ ЧИСЛО, что было (не ноль: на живой странице центрирования уже есть, и
    требовать здесь ноль значило бы, что тест зелен, только пока страница
    идеальна)."""
    do, posle, chisto = _para(
        brauzer, server, "гость", "/raspredelenie", "t-shk",
        "()=>document.querySelectorAll('#v-shk .para .kto').forEach("
        "e=>e.style.setProperty('text-align','center','important'))",
        "()=>document.querySelectorAll('#v-shk .para .kto').forEach("
        "e=>e.style.removeProperty('text-align'))")
    assert len(posle["centr"]) > len(do["centr"]) + 10, (
        f"колонку имён поставили по центру, а гейт показывает "
        f"{len(do['centr'])} → {len(posle['centr'])}. Это и есть тот дефект, "
        "который возвращался четыре раза, потому что на нём ничего не краснело")
    assert any(".kto" in d["put"] for d in posle["centr"]), (
        "центрирование найдено, но названо не то место — чинить по такому "
        "отчёту нечего")
    assert len(chisto["centr"]) == len(do["centr"]), (
        f"центрирование сняли, а гейт всё ещё его показывает: "
        f"{len(do['centr'])} → {len(chisto['centr'])}")


def test_centr_viden_po_nasledstvu(server, brauzer):
    """🔴 РЕНДЕР, А НЕ РАЗМЕТКА.  `text-align` наследуется, и центрирование
    приезжает на элемент, у которого в его собственных стилях нет ни слова про
    выключку.  Проверка, ищущая строку `text-align` у самого узла (или, тем
    более, `grep` по шаблону), этот случай не видит вовсе — а на живом сайте он
    и есть основной: правило пишется на карточке, а видно его на именах."""
    do, posle, chisto = _para(
        brauzer, server, "гость", "/raspredelenie", "t-shk",
        "()=>document.querySelectorAll('#v-shk .kol').forEach("
        "e=>e.style.setProperty('text-align','center','important'))",
        "()=>document.querySelectorAll('#v-shk .kol').forEach("
        "e=>e.style.removeProperty('text-align'))")
    assert len(posle["centr"]) > len(do["centr"]), (
        "центрирование объявлено на колонке, а видно его на каждой строке "
        "внутри — гейт обязан покраснеть, читая РЕНДЕР")
    assert len(chisto["centr"]) == len(do["centr"]), "не зеленеет обратно"


def test_centr_nazyvaet_koren_a_ne_vsyo_poddevo(server, brauzer):
    """🔴 ОДНО ПРАВИЛО — ОДНА НАХОДКА.  `text-align` наследуется, поэтому одна
    строка CSS на карточке делает центрированным КАЖДОГО её потомка.  Замерено
    живьём 10.09 на кондуите: 1199 центрированных узлов при 42 настоящих местах.
    Отчёт на тысячу строк не читает никто, и чинить по нему нечего — чинится
    корень.  Тест сравнивает число находок с числом центрированных узлов и
    требует, чтобы первое было в разы меньше."""
    ctx, p = _stranica(brauzer, server, "гость", "/raspredelenie", "t-shk")
    try:
        p.evaluate("()=>document.querySelectorAll('#v-shk .kol').forEach("
                   "e=>e.style.setProperty('text-align','center','important'))")
        p.wait_for_timeout(200)
        z = _zamer(p)
        vsego_centrirovano = p.evaluate("""() => [...document.querySelectorAll('body *')]
            .filter(e => { const r = e.getBoundingClientRect();
                           return r.width > 1 && r.height > 1; })
            .filter(e => getComputedStyle(e).textAlign === 'center').length""")
        assert vsego_centrirovano > 100, (
            "порча не села: центрированных узлов на странице почти нет, "
            "и сравнивать не с чем")
        assert len(z["centr"]) * 5 < vsego_centrirovano, (
            f"центрированных узлов {vsego_centrirovano}, находок "
            f"{len(z['centr'])} — гейт перечисляет поддерево вместо его корня, "
            "и такой отчёт нечитаем ровно там, где он нужнее всего")
    finally:
        ctx.close()


def test_centr_vidit_body_celikom(server, brauzer):
    """🔴 САМОЕ КРУПНОЕ НАРУШЕНИЕ — САМОЕ ЛЁГКОЕ ДЛЯ ПРОПУСКА.  Обход идёт по
    `body *`, и `body{text-align:center}` не дал бы НИ ОДНОГО корня: у каждого
    потомка родитель тоже центрирован, а сам `body` в обход не входит.  Гейт
    молчал бы на центрированной целиком странице."""
    do, posle, chisto = _para(
        brauzer, server, "гость", "/raspredelenie", "t-shk",
        "()=>document.body.style.setProperty('text-align','center','important')",
        "()=>document.body.style.removeProperty('text-align')")
    assert posle["centr"], (
        "страница центрирована ЦЕЛИКОМ, а гейт зелёный — обход не включал "
        "`body`, и корня центрированного поддерева на странице не нашлось")
    assert any(d["put"].endswith("body") or "body" in d["put"]
               for d in posle["centr"]), (
        f"названо не `body`, а {[d['put'] for d in posle['centr']][:3]}")
    assert len(chisto["centr"]) == len(do["centr"]), "не зеленеет обратно"


def test_centr_lovit_text_align_last(server, brauzer):
    """`text-align-last:center` центрирует ту же строку другим свойством.
    Проверка, знающая только `text-align`, оставляла бы законную дорогу, по
    которой запрещённое центрирование возвращается на сайт молча."""
    do, posle, chisto = _para(
        brauzer, server, "гость", "/raspredelenie", "t-shk",
        "()=>document.querySelectorAll('#v-shk .para .kto').forEach("
        "e=>e.style.setProperty('text-align-last','center','important'))",
        "()=>document.querySelectorAll('#v-shk .para .kto').forEach("
        "e=>e.style.removeProperty('text-align-last'))")
    assert len(posle["centr"]) > len(do["centr"]) + 10, (
        "центрирование через `text-align-last` гейт не увидел")
    assert any(d["chem"] == "text-align-last:center" for d in posle["centr"]), (
        "нашли, но не назвали, ЧЕМ центрировано — чинить нечего")
    assert len(chisto["centr"]) == len(do["centr"]), "не зеленеет обратно"


def test_isklyuchenie_konduita_proshcheno_i_schitaetsya(server, brauzer):
    """Единственное исключение, названное владельцем вслух: номер задачи в клетке
    кондуита (H4.6), принято 10.09 11:3x дословно «мне всё нравится».  Тест
    держит обе половины: исключение ПРОЩЕНО (в находках его нет) и оно ПОСЧИТАНО
    (гейт печатает, сколько центрирований простил) — молчаливое исключение
    неотличимо от дырки в проверке."""
    ctx, p = _stranica(brauzer, server, "организатор", "/glavnaya", "p-kond")
    try:
        z = _zamer(p)
        assert z["isklyucheno"] > 0, (
            "на кондуите не нашлось ни одного `th.zn` — либо разметка изменилась, "
            "либо экран открыт не тот; тогда это исключение ничего не стережёт")
        assert not any("th.zn" in d["put"] for d in z["centr"]), (
            f"номер задачи в клетке кондуита назван находкой: "
            f"{[d['put'] for d in z['centr'] if 'th.zn' in d['put']][:2]} — "
            "владелец принял его явно, и красное на нём выключает гейт")
    finally:
        ctx.close()


def test_pustaya_kletka_ne_nahodka(server, brauzer):
    """Граница измерения, объявленная вслух: у элемента без собственного видимого
    текста центрировать нечего и процитировать в отчёте нечего.  Ею отсекаются
    1095 ПУСТЫХ клеток решётки кондуита — не милостью к кондуиту, а тем же
    правилом, что и всюду.  Тест держит границу с обеих сторон: пустая клетка
    молчит, та же клетка с текстом — находка."""
    ctx, p = _stranica(brauzer, server, "организатор", "/glavnaya", "p-kond")
    try:
        pusto = p.evaluate("""() => [...document.querySelectorAll(
            '#s-kond .kond tbody td + td')].filter(e => {
                const r = e.getBoundingClientRect();
                return r.width > 1 && !(e.textContent || '').trim(); }).length""")
        assert pusto > 100, ("на кондуите нет пустых клеток — граница, ради "
                             "которой написан тест, ничего не отсекает")
        do = _zamer(p)

        # 🔴 ТЕ ЖЕ КЛЕТКИ, ЧТО СЧИТАЛИ, А НЕ ПЕРВЫЕ ТРИДЦАТЬ В ДОКУМЕНТЕ.  Решёток
        # на кондуите двадцать две, и видна одна: без фильтра по видимости текст
        # ложится в СКРЫТУЮ таблицу, гейт честно её не смотрит, и тест «не
        # увидел» ровно то, чего на экране нет.
        p.evaluate("""() => [...document.querySelectorAll(
            '#s-kond .kond tbody td + td')].filter(e => {
                const r = e.getBoundingClientRect();
                return r.width > 1 && r.height > 1
                       && !(e.textContent || '').trim(); }).slice(0, 30)
            .forEach(e => e.textContent = 'ы')""")
        p.wait_for_timeout(200)
        posle = _zamer(p)
        assert len(posle["centr"]) >= len(do["centr"]) + 25, (
            f"в тридцать пустых клеток положили текст, и он центрирован тем же "
            f"правилом — гейт обязан их увидеть: "
            f"{len(do['centr'])} → {len(posle['centr'])}. Иначе «без текста не "
            "судим» — не граница измерения, а тихая амнистия всей решётке")
    finally:
        ctx.close()


def test_samoproverka_lomaet_i_centr(server, brauzer):
    """`--slomat` обязан испытать и пятую проверку, и честно сказать, села ли
    поломка: самопроверка, отчитавшаяся об ущербе, которого не нанесла, — та же
    ложь, что и гейт, отчитавшийся об узлах, на которые не смотрел."""
    ctx, p = _stranica(brauzer, server, "гость", "/raspredelenie", "t-shk")
    try:
        otchet = p.evaluate(gejt.LOMKA)
        assert "centr" in otchet, (
            "поломка не отчитывается о центрировании — проверка 5 не испытана")
        p.wait_for_timeout(200)
        z = _zamer(p)
        if otchet["centr"]:
            assert z["centr"], (
                "поломка «centr» отчиталась, что села, а проверка ничего не "
                "нашла — это ложно-зелёная самопроверка")
    finally:
        ctx.close()


# ── 7. шесть дыр, через которые прошёл свежий верификатор 10.09 ───────────────
#
# 🔴 КАЖДАЯ НАЙДЕНА ПОРЧЕЙ ЖИВОЙ СТРАНИЦЫ, А НЕ ЧТЕНИЕМ КОДА, и две из них —
# ЛОЖНО-КРАСНЫЕ, то есть противоположного знака: гейт объявлял нарушением канона
# пиксели, которых нет.  Тесты держат обе стороны, чтобы починка осталась
# починенной.

def test_centr_v_kontrole_nahodka(server, brauzer):
    """🔴 ПРОПУСК ВЕРИФИКАТОРА №1 И №2.  `INPUT` был выброшен из обхода целиком
    (`sluzhebnyy`), а у `<select>` `chistyy()` вычитает `<option>` и оставляет
    пустоту — и 198 центрированных селектов, и живое поле кабинета («чт 303»,
    `veb/obshchee/karkas.py:1644`) гейт не называл ни на одном из 13 экранов.
    Коробку контрола рисует браузер, и в проверках 1-2 его не судят по этой
    причине; но ВЫКЛЮЧКА текста внутри коробки — наша, и правило канона про неё."""
    ctx, p = _stranica(brauzer, server, "организатор", "/raspredelenie", "t-В")
    try:
        do = _zamer(p)
        est = p.evaluate("""() => ({
            inp: document.querySelectorAll('.kab-pole input').length,
            sel: document.querySelectorAll('select').length})""")
        assert est["inp"] > 0 and est["sel"] > 0, (
            f"на экране нет контролов ({est}) — тесту нечего центрировать")

        p.evaluate("""() => document.querySelectorAll('select').forEach(
            e => e.style.setProperty('text-align','center','important'))""")
        p.wait_for_timeout(200)
        posle = _zamer(p)
        assert any("select" in d["put"].lower() for d in posle["centr"]), (
            f"198 селектов поставлены по центру — у закрытого селекта видна "
            f"выбранная строка, и она уехала в середину, — а гейт нашёл "
            f"{len(posle['centr'])} против {len(do['centr'])} и ни одного select")

        p.evaluate("""() => document.querySelectorAll('select').forEach(
            e => e.style.removeProperty('text-align'))""")
        p.wait_for_timeout(200)
        assert len(_zamer(p)["centr"]) == len(do["centr"]), "не зеленеет обратно"
    finally:
        ctx.close()


def test_centr_zhivogo_polya_kabineta(server, brauzer):
    """Второй половиной того же пропуска: поле кабинета центрировано НА ЖИВОМ
    САЙТЕ, ничего ломать не надо.  Тест держит, что гейт его называет."""
    ctx, p = _stranica(brauzer, server, "организатор", "/raspredelenie", "t-В")
    try:
        z = _zamer(p)
        assert any("kab-inp" in d["put"] for d in z["centr"]), (
            f"поле кабинета центрировано на живой странице, а среди находок его "
            f"нет: {[d['put'] for d in z['centr']][:4]}")
    finally:
        ctx.close()


def test_centr_v_psevdoelemente(server, brauzer):
    """🔴 ПРОПУСК ВЕРИФИКАТОРА №3.  Текст псевдоэлемента не входит в
    `textContent`, поэтому центрированный `::before` с настоящей надписью
    оставлял `chistyy()` пустым, узел отсекался границей «нет своего текста», и
    строка уезжала в середину при нулях по всем пяти проверкам."""
    lomka = """()=>{const s=document.createElement('style');s.id='psev';
        s.textContent='#v-shk .kol::before{content:"ЗАГОЛОВОК КОЛОНКИ";'
        + 'display:block;text-align:center}';document.head.appendChild(s);}"""
    chinka = "()=>document.getElementById('psev').remove()"
    do, posle, chisto = _para(
        brauzer, server, "гость", "/raspredelenie", "t-shk", lomka, chinka)
    assert len(posle["centr"]) > len(do["centr"]), (
        "надпись псевдоэлемента стоит по центру, а гейт показывает то же число, "
        "что до порчи")
    assert len(chisto["centr"]) == len(do["centr"]), "не зеленеет обратно"


def test_centr_pod_nevidimym_kornem(server, brauzer):
    """🔴 ПРОПУСК ВЕРИФИКАТОРА №4, и он структурный, а не про одно свойство.
    `<div style="display:contents;text-align:center">` имеет НУЛЕВОЙ
    прямоугольник: в кандидаты он не попадает и находкой стать не может, а всех
    своих потомков глушил правилом «родитель центрирован — значит не корень».
    Двенадцать блоков уехали в середину, гейт показал 0 → 0.  Подъём к корню
    теперь ПРОПУСКАЕТ невидимых предков вместо того, чтобы на них
    останавливаться."""
    lomka = """()=>{document.querySelectorAll('#v-shk .para').forEach(pa=>{
        const o=document.createElement('div');o.className='obyortka-testa';
        o.style.display='contents';o.style.textAlign='center';
        while(pa.firstChild) o.appendChild(pa.firstChild);
        pa.appendChild(o);});}"""
    ctx, p = _stranica(brauzer, server, "гость", "/raspredelenie", "t-shk")
    try:
        do = _zamer(p)
        p.evaluate(lomka); p.wait_for_timeout(200)
        posle = _zamer(p)
        assert len(posle["centr"]) > len(do["centr"]), (
            f"строки уехали в середину под обёрткой `display:contents`, а гейт "
            f"показывает {len(do['centr'])} → {len(posle['centr'])}: обёртка "
            "невидима, находкой стать не может, и потомков она глушила")
        # Обёртка законно стоит в ПУТИ как предок — путь на то и путь; она не
        # должна быть НАЗВАННЫМ узлом, то есть последним звеном.
        assert not any(d["put"].split(" > ")[-1].startswith("div.obyortka-testa")
                       for d in posle["centr"]), (
            "названа сама невидимая обёртка — по такому адресу в разметке "
            "чинить нечего")
    finally:
        ctx.close()


def test_centr_bez_sdviga_ne_nahodka_no_poschitan(server, brauzer):
    """🔴 ЛОЖНО-КРАСНОЕ ВЕРИФИКАТОРА №5 И №6, знак противоположный.  Кнопки
    `#sohranit`/`#sbrosit` центрированы UA-стилем браузера (в `veb/**` правила
    `button{text-align…}` нет вовсе) и сжаты по тексту: зазор [0,0] с обеих
    сторон.  На экране «класс» ОБЕ находки были такими — целый экран объявлялся
    нарушителем канона на пикселях, которых нет, а гейт, кричащий волком,
    выключают.  Обе половины тут: находкой не считается И посчитан отдельно."""
    ctx, p = _stranica(brauzer, server, "организатор", "/glavnaya", "p-start")
    try:
        z = _zamer(p)
        knopok = p.evaluate("""() => [...document.querySelectorAll(
            '#panel-pravok button')].filter(e => {
                const r = e.getBoundingClientRect();
                return r.width > 1 &&
                       getComputedStyle(e).textAlign === 'center'; }).length""")
        assert knopok >= 2, (
            f"на экране «класс» не нашлось центрированных кнопок ({knopok}) — "
            "ложно-красное, ради которого написан тест, воспроизвести нечем")
        assert not any("sohranit" in d["put"] or "sbrosit" in d["put"]
                       for d in z["centr"]), (
            f"кнопка названа нарушением канона, хотя не сдвигает ни пикселя: "
            f"{[d['put'] for d in z['centr']][:3]}")
        assert z["bez_sdviga"] >= knopok, (
            f"прощено молча: центрирований без сдвига насчитано "
            f"{z['bez_sdviga']} при {knopok} кнопках. Молчаливое прощение "
            "снаружи неотличимо от дырки в проверке")
    finally:
        ctx.close()


def test_centr_sdvinutyy_ostayotsya_nahodkoy(server, brauzer):
    """Вторая сторона того же правила: смягчение обязано касаться ТОЛЬКО
    несдвинутого.  Тот же узел, которому дали ширину и которому теперь есть куда
    двигать текст, обязан снова стать находкой — иначе «без сдвига не судим»
    превращается в тихую амнистию всему центрированию сразу."""
    lomka = """()=>document.querySelectorAll('#panel-pravok button').forEach(
        b=>{b.style.setProperty('width','420px','important');
            b.style.setProperty('text-align','center','important');})"""
    chinka = """()=>document.querySelectorAll('#panel-pravok button').forEach(
        b=>{b.style.removeProperty('width');
            b.style.removeProperty('text-align');})"""
    do, posle, chisto = _para(
        brauzer, server, "организатор", "/glavnaya", "p-start", lomka, chinka)
    assert len(posle["centr"]) > len(do["centr"]), (
        f"кнопкам дали 420px, текст встал ровно посередине пустой полосы — "
        f"а гейт показывает {len(do['centr'])} → {len(posle['centr'])}")
    assert len(chisto["centr"]) == len(do["centr"]), "не зеленеет обратно"


def test_centr_boksom_flexom(server, brauzer):
    """Верификатор замерил: текст, лежащий прямо во флекс-контейнере с
    `justify-content:center`, встаёт ровно туда же, куда его поставил бы
    запрещённый `text-align:center` — зазор [0,120] → [60,60], пиксель в пиксель.
    Одна другая строка CSS, и запрет обойдён легально."""
    lomka = """()=>document.querySelectorAll('#v-shk .para .kto').forEach(e=>{
        e.style.setProperty('display','flex','important');
        e.style.setProperty('justify-content','center','important');})"""
    chinka = """()=>document.querySelectorAll('#v-shk .para .kto').forEach(e=>{
        e.style.removeProperty('display');
        e.style.removeProperty('justify-content');})"""
    do, posle, chisto = _para(
        brauzer, server, "гость", "/raspredelenie", "t-shk", lomka, chinka)
    assert len(posle["centr"]) > len(do["centr"]), (
        "текст центрирован флексом — глазом неотличимо от `text-align:center`, "
        "а гейт молчит")
    assert any(d["chem"] == "justify-content:center" for d in posle["centr"]), (
        "нашли, но не назвали, ЧЕМ центрировано — чинить нечего")
    assert len(chisto["centr"]) == len(do["centr"]), "не зеленеет обратно"


# ── 6. правило CSS, не совпавшее ни с одним узлом ─────────────────────────────
#
# 🔴 ЭТО ТОТ САМЫЙ ДЕФЕКТ, ОТ КОТОРОГО УМЕРЛА `/istoria`, И ОН ПРОВЕРЯЕТСЯ ПАРОЙ:
# правило внесено — гейт называет его; правило убрано — молчит.

def _pravila(p):
    z = _zamer(p)
    return ({s for s in z["pravila_zhivye"]},
            {s: bool(n) for s, n in z["pravila_pustye"]})


def test_nesobiraemoe_pravilo_krasneet_i_zeleneet(server, brauzer):
    """Дефект истории, воспроизведённый дословно: радиокнопка и панель существуют
    обе, а правило требует, чтобы панель была СЕСТРОЙ радио, тогда как она
    племянница.  Правило не совпадает ни с чем НИКОГДА, и до 11.09 это было
    неотличимо от правила верного."""
    ctx, p = _stranica(brauzer, server, "гость", "/raspredelenie", "t-shk")
    try:
        _zhivye, do = _pravila(p)
        p.evaluate("""() => {
            const rodit = document.createElement('div');
            rodit.id = 'proba-rodit';
            const dyadya = document.createElement('input');
            dyadya.type = 'radio'; dyadya.id = 'proba-radio';
            const plem = document.createElement('span');
            plem.id = 'proba-panel'; plem.textContent = 'панель';
            rodit.append(plem);
            document.body.append(dyadya, rodit);
            const st = document.createElement('style');
            st.id = 'proba-stil';
            // племянница, а не сестра: связь невозможна при живых обеих частях
            st.textContent = '#proba-radio:checked ~ #proba-panel{display:block}';
            document.head.append(st);
        }""")
        _zh, s_porchey = _pravila(p)
        klyuch = "#proba-radio:checked ~ #proba-panel"
        assert klyuch in s_porchey, (
            f"несобираемое правило не названо; пустых стало "
            f"{len(s_porchey) - len(do)}")
        assert s_porchey[klyuch] is True, (
            "правило названо пустым, но НЕ несобираемым — а обе его части на "
            "странице есть, и именно это отличает «не подключено» от «ждёт "
            "своего состояния»")

        p.evaluate("""() => {
            document.getElementById('proba-stil').remove();
            document.getElementById('proba-radio').remove();
            document.getElementById('proba-rodit').remove();
        }""")
        _zh2, posle = _pravila(p)
        assert klyuch not in posle, "правило убрано, а гейт всё ещё его называет"
    finally:
        ctx.close()


def test_pravilo_zhdushchee_sostoyaniya_ne_nazyvaetsya_nesobiraemym(server, brauzer):
    """🔴 ГРАНИЦА, БЕЗ КОТОРОЙ ПРОВЕРКА КРИЧАЛА БЫ ВОЛКОМ НА СТО ТРИДЦАТЬ СТРОК.
    `:checked`, `:hover` и прочее описывают МОМЕНТ, а гейт меряет покой: правило,
    ждущее своего состояния, обязано судиться по СТРУКТУРЕ — снимаем состояние и
    спрашиваем, бывает ли такая связь вообще.  Здесь связь законная, и правило
    не должно попасть ни в пустые, ни тем более в несобираемые."""
    ctx, p = _stranica(brauzer, server, "гость", "/raspredelenie", "t-shk")
    try:
        p.evaluate("""() => {
            const a = document.createElement('input');
            a.type = 'checkbox'; a.id = 'proba-fl';
            const b = document.createElement('span');
            b.id = 'proba-ryadom'; b.textContent = 'сосед';
            document.body.append(a, b);          // настоящие СЁСТРЫ, не выключено
            const st = document.createElement('style');
            st.id = 'proba-stil2';
            st.textContent = '#proba-fl:checked ~ #proba-ryadom{color:red}';
            document.head.append(st);
        }""")
        zhivye, pustye = _pravila(p)
        klyuch = "#proba-fl:checked ~ #proba-ryadom"
        assert klyuch in zhivye, (
            "правило, которое ждёт `:checked`, объявлено пустым — так проверка "
            "объявит мёртвым весь сайт, и её выключат")
        assert klyuch not in pustye
    finally:
        p.evaluate("""() => { for (const i of ['proba-stil2','proba-fl','proba-ryadom'])
            { const e = document.getElementById(i); if (e) e.remove(); } }""")
        ctx.close()


def test_pravilo_zhivoe_na_sosednem_ekrane_ne_mertvoe(server, brauzer):
    """🔴 РЕШЕНИЕ ПРИНИМАЕТСЯ ПО ВСЕМ ЭКРАНАМ, А НЕ ПО ОДНОМУ, И ЭТО ИЗМЕРИМО.
    Лист стилей один на весь сайт, поэтому «ноль совпадений на ЭТОМ экране» не
    значит ничего.  Здесь показано живьём: есть селекторы, пустые на
    распределении и ожившие на кондуите.  Проверка, судящая по одному экрану,
    объявила бы их мёртвыми — и была бы неправа ровно столько раз, сколько на
    сайте разделов."""
    ctx, p = _stranica(brauzer, server, "организатор", "/raspredelenie", "t-shk")
    try:
        zh_rasp, pu_rasp = _pravila(p)
    finally:
        ctx.close()
    ctx, p = _stranica(brauzer, server, "организатор", "/glavnaya", "p-kond")
    try:
        zh_kond, _pu_kond = _pravila(p)
    finally:
        ctx.close()
    voskresli = set(pu_rasp) & zh_kond
    assert voskresli, (
        "не нашлось ни одного правила, пустого на распределении и живого на "
        "кондуите — значит эта проверка испытана не была")
    assert not (zh_rasp & set(pu_rasp)), (
        "один экран объявил селектор и живым, и пустым одновременно")


# ── 7. пустой экран при непустых данных ───────────────────────────────────────

def test_pustoy_ekran_krasneet_i_zeleneet(server, brauzer):
    """🔴 ПЯТЬ НУЛЕЙ НА ПУСТОМ ЭКРАНЕ ЧИТАЮТСЯ КАК ЧИСТАЯ СТРАНИЦА.  Все проверки
    гейта судят НАРИСОВАННОЕ: где не нарисовано ничего, у каждой ноль находок —
    и `/istoria` печатала ровно такие нули, будучи невидимой целиком.  Пара:
    главная область спрятана — экран объявлен пустым; возвращена — молчит."""
    ctx, p = _stranica(brauzer, server, "гость", "/raspredelenie", "t-shk")
    try:
        do = _zamer(p)
        assert do["vidno_uzlov"] > 0, "здоровый экран объявлен пустым"
        assert not gejt.pustoy_ekran(do, 54)

        p.evaluate("""() => {
            const m = document.querySelector('main') || document.body;
            m.setAttribute('data-bylo', m.getAttribute('style') || '');
            m.style.setProperty('visibility', 'hidden', 'important');
        }""")
        posle = _zamer(p)
        assert posle["vidno_uzlov"] == 0, (
            f"главная область спрятана, а гейт видит {posle['vidno_uzlov']} узлов")
        assert gejt.pustoy_ekran(posle, 54), "пустой экран не объявлен пустым"
        # 🔴 И ЭТО ИМЕННО «НАПИСАНО, НО НЕ ПОКАЗАНО», А НЕ «ПУСТАЯ СТРАНИЦА»:
        # разметка на месте, и второе число это говорит.
        assert posle["skryto_simvolov"] > 0

        p.evaluate("""() => {
            const m = document.querySelector('main') || document.body;
            m.setAttribute('style', m.getAttribute('data-bylo') || '');
        }""")
        vernuli = _zamer(p)
        assert vernuli["vidno_uzlov"] > 0
        assert not gejt.pustoy_ekran(vernuli, 54)
    finally:
        ctx.close()


def test_pustoy_ekran_na_pustoy_baze_ne_nahodka():
    """Граница, названная вслух: пустой экран на ПУСТОЙ базе — честный пустой
    экран.  Красное на нём значило бы красное на свежей установке, где показывать
    ещё нечего, и такой гейт выключают в первый же день."""
    pusto = {"vidno_uzlov": 0, "skryto_simvolov": 0}
    assert gejt.pustoy_ekran(pusto, 54)
    assert not gejt.pustoy_ekran(pusto, 0)
    assert not gejt.pustoy_ekran({"vidno_uzlov": 3}, 54)
