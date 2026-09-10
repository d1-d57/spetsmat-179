"""Жест открывает историю клетки — и не ставит при этом отметку.

🔴 ЭТОТ ФАЙЛ СУДИТ РЕНДЕР, А НЕ РАЗМЕТКУ, И ЭТО ЕДИНСТВЕННЫЙ СПОСОБ ЗАКРЫТЬ ТО, ЧТО ОН
ЗАКРЫВАЕТ. Обе беды ниже прошли бы любую проверку строк:

  * ПАНЕЛЬ ПОД МЕНЮ. Меню липкое и рисуется поверх; панель, которой не хватило места ни
    под клеткой, ни над ней, прижималась к восьми пикселям от верха окна — то есть под
    меню, ВМЕСТЕ СО СВОЕЙ ШАПКОЙ: фамилией, задачей и кнопкой «закрыть». В разметке при
    этом всё на месте. Условие «не помещается ни туда, ни туда» даёт длинная лента: на
    боевой базе уже есть клетки с семью событиями, и панель у них выше трёхсот точек.
    Здесь оно воспроизводится НИЗКИМ ОКНОМ, а не подделкой ленты, — это тот же самый
    путь в коде, и он не требует записывать в журнал ряды ради теста.
  * ЗАЖАТИЕ, КОТОРОЕ СТАВИТ ГАЛОЧКУ. Клик по клетке пишет отметку (слушатель каркаса на
    `document`), а долгое зажатие приходит тем же тапом. Не погасить его — значит
    сделать «посмотреть историю» синонимом «отметить сдачу», причём на телефоне, где
    другого способа открыть историю нет вовсе.

База — ЖИВАЯ база проекта, как и у гейта вёрстки (`tools/gejt_verstki.py`): у неё есть
клетки с несколькими событиями, а придуманные три ряда ничего из этого не проверяют.
Записей этот файл не делает: единственный сценарий, который мог бы записать, проверяет
как раз ТО, ЧТО ОН НЕ ЗАПИСАЛ, и сверяет счётчик рядов до и после.
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

os.environ.setdefault("SPETSMAT_VEB_SECRET", "test-secret-key-32bytes!")

sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from tools.gejt_verstki import kuka, podnyat_server, zhivaya_baza      # noqa: E402

#: Первая ВИДИМАЯ клетка с датой. Панели листков лежат в DOM все сразу и скрыты
#: `display:none` до своей радиокнопки, поэтому `querySelector('td[data-d]')` без проверки
#: видимости отдаёт клетку нулевого размера — и меряется тогда не решётка, а ничто.
#: Цена: три красных теста, каждый со своим ложным объяснением.
VIDIMAYA = """() => {
  const td = [...document.querySelectorAll('#s-kond .kond td[data-d]')]
    .find(el => el.getClientRects().length && el.getBoundingClientRect().width > 1);
  return td || null;
}"""

#: Ноутбук владельца и телефон — те же два, на которых мерена решётка кондуита.
EKRANY = {"noutbuk": {"width": 1440, "height": 900},
          "telefon": {"width": 375, "height": 780},
          # Окно, в котором панель не помещается НИ под клеткой, ни над ней. На нём
          # прежняя редакция клала её под меню; на двух других ширинах она проходила
          # зелёной по обеим редакциям, и самопроверка поломкой это показала.
          "nizkoe_okno": {"width": 1200, "height": 260}}


@pytest.fixture(scope="module")
def stend():
    """Один сервер, один браузер, обе ширины: Chromium стоит секунду на запуск."""
    # 🔴 БЕЗ НАЗВАННОГО ИСТОЧНИКА — ПРОПУСК, А НЕ ОШИБКА ФИКСТУРЫ. Эти проверки судят
    # РЕНДЕР живой страницы, а живая страница собирается из живой базы; база ушла из
    # git 10.09 по решению владельца, и на машине, где `SPETSMAT_BAZA` не выставлена,
    # открывать нечего. Отказ источника — `SystemExit`, и ловится он здесь явно.
    try:
        db = zhivaya_baza()
    except SystemExit as otkaz:
        pytest.skip("источник не назван: %s" % str(otkaz).splitlines()[0])
    httpd, conn, potok, url = podnyat_server(db)
    try:
        with sync_playwright() as pw:
            brauzer = pw.chromium.launch()
            try:
                yield {"url": url, "brauzer": brauzer, "db": db}
            finally:
                brauzer.close()
    finally:
        httpd.shutdown()
        httpd.server_close()
        potok.join()
        conn.close()


def _konduit(stend, ekran):
    """Открытый кондуит на вкладке первого листка, с клеткой, у которой есть дата."""
    ctx = stend["brauzer"].new_context(viewport=EKRANY[ekran])
    ctx.add_cookies([{**kuka(), "url": stend["url"]}])
    page = ctx.new_page()
    page.goto(stend["url"] + "/", wait_until="networkidle", timeout=30000)
    page.evaluate("document.getElementById('p-kond').checked = true")
    page.evaluate("""() => {
      const m = [...document.querySelectorAll('#s-kond .tabbar label')]
        .find(l => !l.getAttribute('for').startsWith('k-vse'));
      if (m) document.getElementById(m.getAttribute('for')).checked = true; }""")
    page.wait_for_timeout(300)
    return ctx, page


@pytest.mark.parametrize("ekran", ["noutbuk", "telefon"])
def test_data_stoit_pod_galochkoj_i_ne_lomaet_setku(stend, ekran):
    """Дата видна, стоит внутри своей клетки и не выпихивает решётку за экран."""
    ctx, page = _konduit(stend, ekran)
    try:
        zamer = page.evaluate("""(vidimaya) => {
          const td = eval('(' + vidimaya + ')')();
          if (!td) return null;
          td.scrollIntoView({block: 'center'});
          const r = td.getBoundingClientRect();
          const s = getComputedStyle(td, '::before');
          // Ширину нарисованной даты меряем настоящим измерителем того же шрифта:
          // псевдоэлемент своей ширины не отдаёт, а вопрос ровно о ней.
          const p = document.createElement('span');
          p.style.cssText = 'position:absolute;visibility:hidden;white-space:nowrap;font:'
            + s.font;
          p.textContent = td.getAttribute('data-d');
          document.body.appendChild(p);
          const shirina_daty = p.getBoundingClientRect().width;
          p.remove();
          return {est: true, tekst: s.content, kegl: parseFloat(s.fontSize),
                  vysota_kletki: r.height, shirina_kletki: r.width,
                  shirina_daty: shirina_daty,
                  vsego_s_datoj: document.querySelectorAll('#s-kond td[data-d]').length};
        }""", VIDIMAYA)
        assert zamer and zamer["est"], "ни одной клетки с датой на живой базе"
        assert zamer["vsego_s_datoj"] > 1000, zamer
        assert "." in zamer["tekst"], "дата не нарисована псевдоэлементом: %r" % zamer["tekst"]
        assert zamer["kegl"] >= 8, "кегль даты %r — мельче читаемого" % zamer["kegl"]
        assert zamer["kegl"] < 14, "дата не должна спорить с самой галочкой"
        assert zamer["vysota_kletki"] >= 30, zamer
        assert zamer["shirina_daty"] <= zamer["shirina_kletki"], (
            "дата шире своей клетки на %s и обрежется: %s" % (ekran, zamer))
    finally:
        ctx.close()


@pytest.mark.parametrize("ekran", sorted(EKRANY))
def test_pravyj_klik_otkryvaet_istoriyu_celikom_v_kadre(stend, ekran):
    """🔴 Панель обязана стоять НИЖЕ меню и внутри окна — вместе со своей шапкой."""
    ctx, page = _konduit(stend, ekran)
    try:
        page.evaluate("""(vidimaya) => {
          const td = eval('(' + vidimaya + ')')();
          td.scrollIntoView({block: 'center'});
          td.dispatchEvent(new MouseEvent('contextmenu', {bubbles: true})); }""", VIDIMAYA)
        page.wait_for_timeout(1200)
        # Второй жест — уже с наполненной панелью, чтобы место считалось по её НАСТОЯЩЕЙ
        # высоте: первый вызов ставит её пустой, и тогда «помещается» отвечает не про то.
        page.evaluate("""(vidimaya) => {
          const td = eval('(' + vidimaya + ')')();
          td.dispatchEvent(new MouseEvent('contextmenu', {bubbles: true})); }""", VIDIMAYA)
        page.wait_for_timeout(400)
        zamer = page.evaluate("""() => {
          const p = document.getElementById('kl-ist');
          const m = document.querySelector('.menu');
          const r = p.getBoundingClientRect();
          const mr = m ? m.getBoundingClientRect() : {bottom: 0};
          const shapka = p.querySelector('.kl-ist-verh').getBoundingClientRect();
          return {skryta: p.hidden, verh: r.top, niz: r.bottom, vysota: r.height,
                  niz_menu: mr.bottom, shapka_verh: shapka.top,
                  ryadov: p.querySelectorAll('.kl-ist-ryad').length,
                  imya: p.querySelector('#kl-ist-kto').textContent.trim(),
                  okno: innerHeight};
        }""")
        assert not zamer["skryta"], "правый клик не открыл историю"
        assert zamer["ryadov"] >= 1, "панель открылась пустой: %s" % zamer
        assert zamer["imya"], "в шапке панели нет фамилии: %s" % zamer
        assert zamer["shapka_verh"] >= zamer["niz_menu"], (
            "шапка панели ушла ПОД липкое меню: %s" % zamer)
        assert zamer["verh"] >= 0 and zamer["niz"] <= zamer["okno"] + 1, (
            "панель вышла за кадр: %s" % zamer)
    finally:
        ctx.close()


def test_dolgoe_zazhatie_otkryvaet_istoriyu_i_ne_stavit_otmetku(stend):
    """Тот же жест на телефоне: история открылась, а в журнале не прибавилось ни ряда."""
    c = sqlite3.connect("file:%s?mode=ro" % stend["db"], uri=True)
    do = c.execute("select count(*) from marks").fetchone()[0]
    c.close()

    ctx, page = _konduit(stend, "telefon")
    try:
        koord = page.evaluate("""(vidimaya) => {
          const td = eval('(' + vidimaya + ')')();
          td.scrollIntoView({block: 'center'});
          const r = td.getBoundingClientRect();
          td.id = 'probnaya-kletka';
          return {x: r.left + r.width / 2, y: r.top + r.height / 2,
                  bylo: td.textContent.trim()}; }""", VIDIMAYA)
        page.mouse.move(koord["x"], koord["y"])
        page.mouse.down()
        page.wait_for_timeout(900)              # дольше порога зажатия
        page.mouse.up()
        page.wait_for_timeout(1200)

        itog = page.evaluate("""() => {
          const td = document.getElementById('probnaya-kletka');
          return {panel: !document.getElementById('kl-ist').hidden,
                  ryadov: document.querySelectorAll('#kl-ist .kl-ist-ryad').length,
                  stalo: td ? td.textContent.trim() : null}; }""")
        assert itog["panel"], "зажатие не открыло историю"
        assert itog["ryadov"] >= 1, itog
        assert itog["stalo"] == koord["bylo"], (
            "зажатие перерисовало клетку: %r → %r" % (koord["bylo"], itog["stalo"]))
    finally:
        ctx.close()

    c = sqlite3.connect("file:%s?mode=ro" % stend["db"], uri=True)
    posle = c.execute("select count(*) from marks").fetchone()[0]
    c.close()
    assert posle == do, (
        "долгое зажатие записало отметку: рядов было %d, стало %d" % (do, posle))
