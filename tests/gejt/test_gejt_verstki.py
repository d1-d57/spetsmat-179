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
    """«Тухватулин-Йалчын …» on `/raspredelenie`, tab «школьникам», WITHOUT a
    password.  This is the exact screen of the owner's screenshot `11`, and the
    exact number the gate reported as zero."""
    ctx, p = _stranica(brauzer, server, "гость", "/raspredelenie", "t-shk")
    try:
        s_defektom = _zamer(p)
        assert s_defektom["obrezka"], (
            "гейт не видит обрезки там, где она есть на живой странице у гостя — "
            "это ровно то ложно-зелёное, ради которого написан этот тест")

        # 🔴 THE CLIPPED BOX IS NOT A LEAF, and that was the whole cause.  `.kto`
        # wraps `<b>SURNAME</b>`, so a leaf-only walk threw away all of them.
        clip = [d for d in s_defektom["obrezka"] if ".kto" in d["put"]]
        assert clip, ("обрезка найдена, но не на `.kto` — а обрезает именно она "
                      "(`veb/obshchee/karkas.py:1308`)")

        # remove the clipping and NOTHING ELSE: the same page, one property.
        p.evaluate("""() => document.querySelectorAll('.kto').forEach(e => {
            e.style.overflow = 'visible'; e.style.textOverflow = 'clip';
            e.style.whiteSpace = 'normal'; })""")
        p.wait_for_timeout(150)
        bez_defekta = _zamer(p)
        ostalos = [d for d in bez_defekta["obrezka"] if ".kto" in d["put"]]
        assert not ostalos, (
            f"обрезку сняли, а гейт всё ещё её показывает: {ostalos[:2]} — "
            "гейт, который не умеет зеленеть, так же бесполезен, как молчащий")
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
        assert not _zamer(p)["vyshli"], (
            "дефект убрали, а проверка «вышло за контейнер» всё ещё краснеет")
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
