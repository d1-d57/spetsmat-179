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
    if not gejt.BAZA.exists():
        pytest.fail(f"нет живой базы {gejt.BAZA} — гейт судит настоящую страницу, "
                    "а не фикстуру, и без базы ему нечего открывать")
    httpd, conn, t, url = gejt.podnyat_server(gejt.BAZA)
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

@pytest.mark.parametrize("imya,put,radio,roli", [(e[0], e[1], e[2], e[3])
                                                 for e in gejt.EKRANY])
def test_ohvat_ne_nol(server, brauzer, imya, put, radio, roli):
    """Every screen the gate claims to judge must exist, open, and hand the walks
    a non-zero number of nodes.  🔴 This is the test that would have caught the
    second cause on its own: the table named `p-rasp`/`p-start`/`p-kond`, which
    are the SITE radios (`name="str"`), while the tabs inside распределение are
    `t-shk`/`t-prep`/`t-В`/`t-Д`/`t-Н` (`name="vk"`).  The gate opened the same
    default view four times and never reached a group tab at all."""
    rol = roli[0]
    ctx, p = _stranica(brauzer, server, rol, put, radio)
    try:
        z = _zamer(p)
        assert z["vsego"] > 0, f"{imya}: на странице ноль элементов"
        assert z["na_obrezku"] > 0, f"{imya}: проверке ОБРЕЗКИ не досталось узлов"
        assert z["osmotreno"] > 0, f"{imya}: проверке ПЕРЕНОСА не досталось узлов"
        assert z["na_vyhod"] > 0, f"{imya}: проверке ВЫХОДА не досталось узлов"
    finally:
        ctx.close()


def test_ekrany_razlichny(server, brauzer):
    """Two screens of the same page must not be the same screen.  When the radio
    ids were wrong every row of the table measured the identical DOM and the four
    numbers agreed perfectly — which reads exactly like four clean pages."""
    vidy = {}
    for imya, put, radio, roli in gejt.EKRANY:
        if "гость" not in roli:
            continue
        ctx, p = _stranica(brauzer, server, "гость", put, radio)
        try:
            vidy[imya] = _zamer(p)["na_obrezku"]
        finally:
            ctx.close()
    rasp = [v for k, v in vidy.items() if k != "класс"]
    assert len(set(rasp)) == len(rasp), (
        f"разные вкладки распределения дали одинаковый охват {vidy} — "
        "гейт меряет один и тот же экран под разными именами")


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
        assert set(otchet) == {"obrezka", "perenos", "vyhod", "skroll"}, (
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
