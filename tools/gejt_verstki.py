#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-hand — run before publishing a layout change, and by
# the acceptance of any заход that touched `veb/**`.
"""Layout gate: judges the RENDER of a page, not the lines of its CSS.

Why this file exists.  The column rule of this project was written down three times
and did not hold three times, because it had no lever: nothing turned red when a
page broke it.  A rule without a carrier is a hope (`skills/disciplina-kachestvo`).
This gate is the carrier.  It boots the real server on the real database, opens
every screen in a headless Chromium at the reference viewport, in every role that
can see it, and asks five questions that a human asks by looking:

  1. CLIPPING      -- is there an element whose visible box is narrower than its
                      own text needs, so the text is cut?
  2. NEEDLESS WRAP -- is there a line that took two line-heights where the
                      available width allowed one?
  3. H-SCROLL      -- is the document wider than the window?
  4. ESCAPED       -- is there an element standing OUTSIDE the card that owns it,
                      where nothing clips it and no scrollbar reveals it?
  5. CENTRED       -- is there text set centred?  «НИКОГДА по центру мы не
                      центрируем» is a rule of this project's canon, and this is
                      the check that carries it.

All five zero on every screen -- green.  Anything else -- red, with the offending
selectors printed, because a gate that says only "red" gets ignored.

🔴 WHY CHECK 5 EXISTS (owner, 2026-09-10 11:4x).  Centring came back for the
FOURTH time, and the owner named the cause himself: «центрирование на нашем сайте
надо прям где-то вставить в какой-то стандартный канон.  НИКОГДА по центру мы не
центрируем».  A rule that lives as a sentence in a document has been re-broken
three times; a rule that turns a gate red cannot come back silently.  It is
measured on the RENDER like everything else here -- centring arrives from a class
and from inheritance alike, and grepping the markup for `text-align` would miss
both.  The exceptions are a single named list inside the measuring script, one
name and one reason each, and only what the owner called an exception out loud.

🔴 WHY THIS FILE WAS REWRITTEN ON 2026-09-10.  The gate reported «обрезанных у
гостя 48 → 0» while the owner was looking at «Тухватулин-Йалчын …» clipped on the
very same page, guest role, tab «школьникам».  Three things were wrong at once and
each one alone was enough to produce that zero:

  * THE WALK DROPPED THE CLIPPED NODE.  The node walk kept only LEAF elements --
    an element was discarded when any child carried text.  The clipped node is
    `<span class="kto"><b>SURNAME</b> Name</span>` (`veb/razdely/shkolniki.py:356`)
    and the `text-overflow:ellipsis` lives on `.kto` (`veb/obshchee/karkas.py:1308`,
    `:1591`).  `.kto` has a `<b>` child with text, so every single one of them was
    thrown away.  Measured live 10.09: 113 `.kto` on the guest page, 0 of them
    leaves, 1 of them clipped -- and the leaf walk reported 0.
  * THE GUEST WAS NEVER MEASURED.  The gate authenticated as `organizator` always,
    and the screen the owner photographed is the one WITHOUT a password.
  * THE TAB IDS WERE THE WRONG ONES.  The table selected `p-rasp` / `p-start` /
    `p-kond` -- those are the SITE-level radios (`name="str"`).  The tabs inside
    распределение are `t-shk` / `t-prep` / `t-В` / `t-Д` / `t-Н` (`name="vk"`,
    `veb/obshchee/karkas.py:1084`).  The gate therefore measured the same default
    view four times and never opened a group tab at all -- which is exactly where
    the escaped-content defect of the owner's screenshot `13` lives.

Run:  python3 tools/gejt_verstki.py            (green -> rc=0, red -> rc=1)
      python3 tools/gejt_verstki.py --slomat   (self-test: forces a violation of
                                                EVERY one of the five checks; the
                                                gate MUST go red; rc=0 when it
                                                correctly caught them all)
      python3 tools/gejt_verstki.py --ekran Д  (one screen, by name substring)
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

KOREN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOREN))

os.environ.setdefault("SPETSMAT_VEB_SECRET", "gate-secret-key-32bytes-long!!")

ETALON = {"width": 1440, "height": 900}

# Метка строки отчёта, которая НЕ красная: экран свёлся к другому, а не упал.
# Отдельный знак, а не разбор текста сообщения: сообщение читает человек,
# а решение «красное или нет» принимает машина, и им нужен разный носитель.
SVEDENO = "\u21a6"

# 🔴 THE RENDER IGNORES THE CONNECTION THIS GATE HANDS THE SERVER.  Every page
# route rebuilds its context through `veb.obshchee.karkas.DATA`, a module-level
# constant pointing at `<repo>/data/spetsmat.db`.  So the base the gate judges is
# ALWAYS the one checked out next to it -- there is no honest way to aim the gate
# elsewhere, and pretending otherwise with a `--baza` flag would be a third way to
# lie.  Stated here so nobody spends an hour finding it again.
# 🔴 АДРЕС, А НЕ ИМЯ. Здесь стоял путь от корня репозитория — то самое второе
# имя, из-за которого одна строка указывала на разные файлы на сервере и на
# машине владельца, и указывала успешно. Источник называет переменная среды
# `SPETSMAT_BAZA`; не названа — отказ с двумя законными адресами, а не фантом.
# Разбор — `doc/ISTOCHNIK-BAZY.md`.
def baza() -> Path:
    import config
    return config.DB_PATH

# ── THE LIST OF SCREENS IS DERIVED FROM THE ROUTES, NEVER TYPED OUT ──────────
# 🔴 WHY.  Until 2026-09-11 `EKRANY` was ten hand-written lines, and `/istoria`
# and `/kabinet` were not among them -- zero occurrences of either word in this
# file.  That is how a page with 321 lines of code and 29 green tests could stay
# invisible on screen until the owner found it himself: the gate was formally
# right, it had never been sent there.  A hand-written list falls behind the site
# BY CONSTRUCTION, and the fix is not to add two more lines but to stop writing
# the list.  Route exists -> screen is judged.
#
# `veb/server.py` is not this position's zone and declares its page routes as
# inline `if path == "..."` branches rather than as a table, so they are READ out
# of it instead of copied: the AST of `Handler.do_GET` is walked for every string
# compared against `path` (`==`, `in (...)`, `.startswith(...)`).  A route added
# there tomorrow arrives here by itself, with nobody editing this file.  The two
# registries the same method consults -- `server._marshruty_razdelov()` and
# `vhod.marshruty()` -- are ASKED, not parsed: they already are tables.
OBE = ("гость", "организатор")

# Not screens, and each says why.  Everything else that is discovered IS a screen.
NE_EKRANY = {
    "/api/":       "машинная дверь: отдаёт JSON, вёрстки у неё нет",
    "/static/":    "файлы, а не страница",
    "/materials/": "выдача PDF, а не страница",
}

# 🔴 РОЛЬ СУЖАЕТСЯ ТОЛЬКО ИМЕНЕМ И ТОЛЬКО С ПРИЧИНОЙ.  По умолчанию экран мерится
# в ОБЕИХ ролях: гость -- это тот, кого владелец фотографирует.  Страница, которая
# вошедшему показывает раздел, а гостю -- приглашение «Войти», в роли гостя не
# экран, а заглушка, и мерить её значило бы объявлять пустым то, что пусто нарочно.
ROLI_MARSHRUTA = {
    "/istoria": (("организатор",), "у гостя -- заглушка «Войти» "
                 "(`veb/razdely/istoria_zanyatij.py:314`), а не раздел"),
    "/kabinet": (("организатор",), "у гостя -- заглушка со ссылкой на вход "
                 "(`veb/razdely/kabinet.py:484`)"),
    "/priyom":  (("организатор",), "у гостя -- «Войти» "
                 "(`veb/priyom.py:404`)"),
    "/vnesti":  (("организатор",), "страница открыта преподавателям "
                 "(`veb/razdely/vnesenie.py:546`)"),
}

# Tabs are an OVERLAY on a route, never the source of the list: a route with no
# entry here is still measured, once, as it opens.  Roles here narrow the route's
# own roles and never widen them.
#   `name="str"` radios switch the SITE SECTION: p-start · p-rasp · p-lich · p-kond
#   `name="vk"`  radios switch the TAB inside распределение: t-shk · t-prep · t-В/Д/Н
VKLADKI = {
    "/": [("класс", "p-start", None),
          ("кондуит", "p-kond", ("организатор",))],
    "/raspredelenie": [("школьникам", "t-shk", None),
                       ("принимающим", "t-prep", None),
                       ("группа В", "t-В", None),
                       ("группа Д", "t-Д", None),
                       ("группа Н", "t-Н", None)],
    # 🔴 ПОСТОЯННОЕ РАСПРЕДЕЛЕНИЕ ДОБАВЛЕНО 10.09 (Д4). Его здесь НЕ БЫЛО ВОВСЕ --
    # целый раздел сайта, обе вкладки, не измерялся гейтом ни разу. При этом
    # владелец жаловался на обрезку фамилий именно там ТРИЖДЫ (G3.2, G3.4, J2.3),
    # а гейт в это же время печатал «обрезка 0» и был формально прав: он туда не
    # ходил. Четвёртое лицо одного класса за волну -- «ноль находок» означало
    # «не смотрел», а читалось как «чисто» (G0 -- не видел узла, J1 -- не знал
    # правила, здесь -- не ходил на экран).
    "/raspredelenie/postoyannoe": [("постоянное · школьникам", "t-shk", None),
                                   ("постоянное · принимающим", "t-prep", None)],
}


def _hvost_kartochki(db) -> str:
    """A LIVE pupil, not an invented id: the card of a pupil who is not in the base
    renders «не найдено», and measuring that would be measuring the 404."""
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        r = c.execute("select id from students where status='active' "
                      "order by id limit 1").fetchone()
    finally:
        c.close()
    return str(r[0]) if r else ""


def _hvost_listka(_db) -> str:
    """A sheet that is really published, taken from `docs/listki`."""
    papka = KOREN / "docs" / "listki"
    if not papka.is_dir():
        return ""
    for f in sorted(papka.glob("*.pdf")):
        return f.stem.split("-")[0]
    return ""


# A route whose tail names an object.  The supplier hands the gate a LIVE tail out
# of the base or the disk.  🔴 A discovered prefix route with no supplier here is
# RED, not skipped: «не знаю, что подставить» and «здесь нечего проверять» are the
# same silence, and this file exists because that silence was read as «чисто».
HVOSTY = {
    "/kartochka/": (_hvost_kartochki, "карточка школьника открывается по id"),
    "/listki/":    (_hvost_listka,    "страница листка открывается по номеру"),
    "/listok/":    (_hvost_listka,    "второе имя того же адреса, которое не "
                                      "перехватывает nginx (`veb/server.py:729`)"),
}


def marshruty_sayta() -> dict:
    """`{путь: род}` -- every route the live server answers a GET on.

    Род: `stranica` (a screen), `hvost` (a prefix that needs an object id),
    `ne-ekran` (a machine door or a file).  Nothing is dropped silently: a route
    the gate cannot turn into a screen still comes back, with its род saying why.
    """
    import ast

    najdeno: dict = {}

    def rod(put: str) -> str:
        for pref, _ in NE_EKRANY.items():
            if put.startswith(pref):
                return "ne-ekran"
        return "stranica"

    # 1. the branches of `Handler.do_GET`, read out of the source
    derevo = ast.parse((KOREN / "veb" / "server.py").read_text(encoding="utf-8"))
    for uzel in ast.walk(derevo):
        if not (isinstance(uzel, ast.FunctionDef) and uzel.name == "do_GET"):
            continue
        for n in ast.walk(uzel):
            if (isinstance(n, ast.Compare) and isinstance(n.left, ast.Name)
                    and n.left.id == "path"):
                for op, cmp in zip(n.ops, n.comparators):
                    esli = []
                    if isinstance(op, ast.Eq) and isinstance(cmp, ast.Constant):
                        esli = [cmp.value]
                    elif isinstance(op, ast.In) and isinstance(cmp, (ast.Tuple, ast.List)):
                        esli = [e.value for e in cmp.elts if isinstance(e, ast.Constant)]
                    for p in esli:
                        if isinstance(p, str) and p.startswith("/"):
                            najdeno.setdefault(p, rod(p))
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "startswith"
                    and isinstance(n.func.value, ast.Name) and n.func.value.id == "path"):
                for a in n.args:
                    if isinstance(a, ast.Constant) and isinstance(a.value, str):
                        najdeno[a.value] = ("ne-ekran" if rod(a.value) == "ne-ekran"
                                            else "hvost")

    # 2. the registries, asked rather than parsed
    import veb.server as server
    from veb import vhod
    for p in list(server._marshruty_razdelov()) + list(vhod.marshruty()):
        najdeno.setdefault(p, rod(p))
    return najdeno


def sobrat_ekrany(db) -> tuple[list, list]:
    """`(экраны, беды)`.  Экран -- `(имя, путь, радио, роли)`, ровно тот кортеж,
    которым была рукописная константа: всё, что ниже, не заметило подмены.

    Беды -- строки о маршрутах, которые НЕ стали экраном.  Пустой список беды
    здесь не значит «всё хорошо»: он значит «каждый найденный маршрут стал
    экраном», и число экранов печатается рядом с числом маршрутов.
    """
    ekrany, bedy = [], []
    for put, rod_ in sorted(marshruty_sayta().items()):
        if rod_ == "ne-ekran":
            continue
        if rod_ == "hvost":
            postavshchik = HVOSTY.get(put)
            if not postavshchik:
                bedy.append(f"маршрут «{put}» открывается по хвосту, а подставить "
                            f"нечего: допиши поставщика в `HVOSTY`")
                continue
            hvost = postavshchik[0](db)
            if not hvost:
                bedy.append(f"маршрут «{put}»: поставщик хвоста ничего не вернул "
                            f"({postavshchik[1]})")
                continue
            put = put + hvost
        roli = OBE
        suzheno = ROLI_MARSHRUTA.get(put.rstrip("/") or "/")
        if suzheno:
            roli = suzheno[0]
        vkl = VKLADKI.get(put)
        if not vkl:
            ekrany.append((put, put, None, roli))
            continue
        for imya, radio, svoi_roli in vkl:
            ekrany.append((imya, put, radio, svoi_roli or roli))
    return ekrany, bedy


# The measuring script.  It runs inside the page, so it sees the RENDER: computed
# boxes after CSS, fonts and layout, not the source.
ZAMER = r"""
() => {
  const out = {obrezka: [], perenos: [], vyshli: [], centr: [], skroll: 0,
               osmotreno: 0, vsego: 0, na_obrezku: 0, na_vyhod: 0,
               na_centr: 0, isklyucheno: 0, bez_sdviga: 0};

  out.skroll = Math.max(0,
      document.documentElement.scrollWidth - document.documentElement.clientWidth);

  const vidim = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return false;
    const s = getComputedStyle(el);
    return s.display !== 'none' && s.visibility !== 'hidden' && s.opacity !== '0';
  };

  const sluzhebnyy = (el) =>
      ['SCRIPT','STYLE','SVG','PATH','BR','INPUT'].includes(el.tagName);

  const vse = [...document.querySelectorAll('body *')];
  out.vsego = vse.length;

  const vidimye = vse.filter(el => !sluzhebnyy(el) && vidim(el));
  const s_tekstom = vidimye.filter(el => (el.textContent || '').trim().length > 0);

  // A LEAF carries its own text: none of its children carries any.
  const list = (el) => ![...el.children].some(c => (c.textContent || '').trim().length > 0);

  // A form control is drawn by the browser, not laid out from its text: a
  // <select> shows one option and hides the rest BY DESIGN, and an <input> has no
  // text nodes at all.  Judging either for clipping or wrapping is crying wolf.
  //
  // 🔴 THE CONTROL ITSELF, NEVER ITS ANCESTORS.  The first version of this rule
  // also threw out every element CONTAINING a control — and on the organiser's
  // screens that is almost every row and every card, because each row carries a
  // <select>.  Found by the verifier, and it was worse than the bug being fixed:
  // squeezing the left column of «школьникам» to 150px, so that «Аникина Анастас…»
  // and «Афанасьева Пол…» were cut on the screenshot, moved the gate from
  // (1,0,18,0) to (1,0,10,0) — the page was destroyed and the gate got GREENER.
  // The <select> is kept out of the measurement instead: the text walk below skips
  // text that lives inside a control, so an ancestor is judged on its own text and
  // nothing else.
  const organ = (el) => ['SELECT','OPTION','TEXTAREA','INPUT','BUTTON'].includes(el.tagName);

  const VNE_TEKSTA = ['SELECT','OPTION','TEXTAREA','INPUT','BUTTON','STYLE','SCRIPT'];

  // Rectangles of the element's OWN text: what a reader actually sees painted.
  // A <select>'s option list, a <style>'s source and an <input>'s value are drawn
  // by the browser rather than laid out from this element's text, so they are not
  // this element's text and cannot be evidence that this element is cut.
  const rects_teksta = (el) => {
    const out = [];
    const hod = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, {
      acceptNode(n) {
        if (!(n.nodeValue || '').trim()) return NodeFilter.FILTER_REJECT;
        for (let p = n.parentElement; p && p !== el.parentElement; p = p.parentElement)
          if (VNE_TEKSTA.includes(p.tagName)) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    for (let n = hod.nextNode(); n; n = hod.nextNode()) {
      const d = document.createRange();
      d.selectNodeContents(n);
      for (const b of d.getClientRects())
        if (b.width > 0 && b.height > 0) out.push(b);
    }
    return out;
  };

  // Text with the content of <style>/<script>/<option> subtracted, so a report
  // quotes what a reader sees and not a stylesheet.
  const chistyy = (el) => {
    const k = el.cloneNode(true);
    k.querySelectorAll('style, script, option').forEach(n => n.remove());
    return (k.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40);
  };

  // 🔴 AN INLINE BOX HAS `clientWidth === 0` BY SPECIFICATION -- it is not narrow,
  // it simply has no client box.  Every numeric comparison against it is therefore
  // false, and the wrap check could not judge a single inline `<span>` -- which on
  // this site is most of the text there is.  Found by the self-test refusing to
  // catch its own breakage on «кондуит»: `span.iz`, two line boxes, 233px needed,
  // `clientWidth` 0.
  // The width an inline box really had is the content width of the block that
  // contains it -- but only when it is that block's ONLY text: sharing a line with
  // siblings is a perfectly good reason to wrap, and reporting it would be the
  // gate crying wolf.  When it shares, the element is left unjudged, and that is
  // said out loud in the list of what the gate does not check.
  const dostupno = (el) => {
    if (el.clientWidth > 0) return el.clientWidth;
    let n = el.parentElement;
    while (n && n !== document.body && n.clientWidth === 0) n = n.parentElement;
    if (!n || n === document.body) return 0;
    const sosedi = [...n.childNodes].filter(k =>
        (k.nodeType === 3 ? (k.nodeValue || '').trim()
                          : k !== el && (k.textContent || '').trim()));
    return sosedi.length ? 0 : n.clientWidth;
  };

  const vnutri = (el) => {                    // padding box
    const r = el.getBoundingClientRect(), s = getComputedStyle(el);
    return {l: r.left + parseFloat(s.borderLeftWidth),
            r: r.right - parseFloat(s.borderRightWidth),
            t: r.top + parseFloat(s.borderTopWidth),
            b: r.bottom - parseFloat(s.borderBottomWidth)};
  };

  const put = (el) => {
    const parts = [];
    let n = el;
    for (let i = 0; i < 3 && n && n.tagName; i++) {
      let s = n.tagName.toLowerCase();
      if (n.id) s += '#' + n.id;
      else if (n.className && typeof n.className === 'string')
        s += '.' + n.className.trim().split(/\s+/).slice(0,2).join('.');
      parts.unshift(s);
      n = n.parentElement;
    }
    return parts.join(' > ');
  };

  // ── 1. CLIPPING ────────────────────────────────────────────────────────────
  // 🔴 NOT LEAVES ONLY, AND THAT IS THE WHOLE POINT OF THE 10.09 REWRITE.  The box
  // that clips is the one carrying `overflow:hidden` + `text-overflow:ellipsis`,
  // and on this site that box (`.kto`) always wraps a `<b>` with the surname in
  // it -- so a leaf-only walk misses every clipped name there is.  An element is
  // judged for clipping when it carries text AND establishes its own clipping
  // context; leaves are kept too, so nothing the old walk caught is lost.
  const na_obrezku = s_tekstom.filter(el => {
    if (organ(el)) return false;
    const s = getComputedStyle(el);
    return (s.overflowX !== 'visible' || s.overflowY !== 'visible') || list(el);
  });
  out.na_obrezku = na_obrezku.length;

  for (const el of na_obrezku) {
    const s = getComputedStyle(el);
    // scrollWidth/scrollHeight exceeding the client box says the box is too small
    // for SOMETHING.  🔴 HEIGHT TOO, and that was a hole the verifier walked
    // straight through: `.kto{height:7px;overflow:hidden}` on twenty rows left the
    // left column unreadable on the screenshot and the gate reported the same
    // number it had before the damage. Text cut from BELOW is cut.
    const uzko = el.scrollWidth > el.clientWidth + 1 && s.overflowX !== 'visible';
    const nizko = el.scrollHeight > el.clientHeight + 1 && s.overflowY !== 'visible';
    if (!uzko && !nizko) continue;
    // 🔴 ...AND THE SOMETHING MUST BE TEXT.  `scrollWidth` alone is not enough:
    // measured live 10.09, it reported `section#s-start` (1478 vs 1440, an SVG
    // decoration the section clips ON PURPOSE) and every `.prep-imya` of the
    // organiser (233 vs 208 — a <select> whose widest OPTION is wider than the
    // closed control, which is how every select on earth behaves).  Neither cuts
    // a letter, and 56 such lines per run is precisely how a gate gets switched
    // off.  So the text's OWN line boxes are asked whether any of them reaches
    // past the padding box: `<style>` has no boxes, `<option>` has no boxes, an
    // SVG is not text — all three fall out by themselves, no list of exceptions.
    const b = vnutri(el);
    const rects = rects_teksta(el);
    if (!rects.length) continue;
    const vbok = Math.max(...rects.map(r => Math.max(r.right - b.r, b.l - r.left)));
    const vniz = Math.max(...rects.map(r => Math.max(r.bottom - b.b, b.t - r.top)));
    if (vbok <= 1 && vniz <= 1) continue;
    out.obrezka.push({
        put: put(el), tekst: chistyy(el),
        storona: vbok > 1 ? 'вширь' : 'ввысь',
        nado: vbok > 1 ? el.scrollWidth : el.scrollHeight,
        est: vbok > 1 ? el.clientWidth : el.clientHeight});
  }

  // ── 2. NEEDLESS WRAP ───────────────────────────────────────────────────────
  // Leaves only, and here the leaf rule earns its place: a container wraps
  // because its children do, and blaming the container buries the real offender.
  const listya = s_tekstom.filter(list);
  out.osmotreno = listya.length;

  for (const el of listya) {
    const s = getComputedStyle(el);
    // 🔴 FLEX AND GRID HAVE NO LINE BOXES TO COUNT.  Their children sit on rows
    // the layout chose, and `align-items:center` alone puts two of them at two
    // different tops without a single wrap.  Measured live 10.09: `label.kab-pole`
    // («чт» plus a 5rem input, `display:inline-flex`) was reported on all three
    // group tabs as «two lines where 80px of 109 were needed» — nothing had
    // wrapped.  Same reason a form control is skipped: its box is drawn by the
    // browser, not laid out from the text.
    if (['flex','inline-flex','grid','inline-grid'].includes(s.display)) continue;
    if (organ(el)) continue;
    const tekst = chistyy(el);
    // 🔴 Line count is taken from the TEXT's own line boxes, never from the
    // element's height.  Height includes padding and border, so a tab button
    // with 10px of vertical padding measures two line-heights while carrying a
    // single word.  Measured live 10.09 02:15: the height test reported 28
    // needless wraps across four pages, of which 21 were padded labels («В»,
    // «Д», «16A», arrows) that never wrapped at all -- a gate crying wolf, and
    // a gate crying wolf is a gate that gets switched off.
    const verhi = new Set(rects_teksta(el).map(b => Math.round(b.top)));
    const strok = verhi.size;
    if (strok >= 2 && s.whiteSpace !== 'pre') {
      // 🔴 NOT a detached clone.  A clone appended to <body> loses everything it
      // inherited in place -- measured live 10.09 02:30: a 36px table cell was
      // measured at 291px natural width while the text really needs 484px, so a
      // LEGITIMATE wrap (474px available, 484px needed) was reported as a defect.
      // Красное на здоровом — ложный гейт, и такой гейт обходят.
      // Instead the element itself is switched to nowrap in place, measured, and
      // switched back: all inherited font, spacing and context are preserved.
      const bylo = el.style.whiteSpace;
      el.style.whiteSpace = 'nowrap';
      const rr = rects_teksta(el);
      const nuzhno = rr.length ? Math.max(...rr.map(b => b.width)) : 0;
      el.style.whiteSpace = bylo;
      if (nuzhno <= dostupno(el) + 1) {
        out.perenos.push({put: put(el), tekst, strok,
                          nuzhno: Math.round(nuzhno), est: el.clientWidth});
      }
    }
  }

  // ── 4. ESCAPED THE CONTAINER ───────────────────────────────────────────────
  // 🔴 THE CHECK THE GATE DID NOT HAVE AT ALL, added 10.09.  Owner's screenshot
  // `13`: the pills «Бирюков», «Аникина», «Белеванцева» stand LEFT of the card of
  // the teacher who owns them.  None of the three older checks can see it -- the
  // text is not cut, the line did not wrap, and the DOCUMENT does not scroll,
  // because the pills escape into space the page already has.
  //
  // A VISUAL CONTAINER is what the eye reads as an edge: it clips, or it paints a
  // border, or it paints a background of its own.  An element is a defect when
  // its border box sticks out of the padding box of its nearest visual container
  // AND that container does NOT clip -- if it clipped, the overflow would be
  // hidden and that is check 1's business, not this one.
  const prozr = (c) => !c || c === 'transparent' || c === 'rgba(0, 0, 0, 0)';
  const konteyner = (el) => {
    const s = getComputedStyle(el);
    if (s.overflowX !== 'visible' || s.overflowY !== 'visible') return 'клип';
    // 🔴 A BOX, NOT A RULE.  A border on ONE side is a horizontal rule between
    // rows — the eye reads it as a separator, not as the edge of a card, and
    // nothing «escapes» it.  Measured live 10.09: `.para` carries only
    // `border-bottom`, and calling it a container produced 108 «escaped» lines on
    // the organiser's tab «школьникам» for controls that sit in the row exactly
    // where they were put.  A container is a box: borders on BOTH sides, or a
    // rounded corner, or a background of its own.
    if ((parseFloat(s.borderLeftWidth) && parseFloat(s.borderRightWidth)) ||
        parseFloat(s.borderTopLeftRadius)) return 'рамка';
    if (!prozr(s.backgroundColor)) return 'фон';
    return null;
  };
  for (const el of vidimye) {
    const s = getComputedStyle(el);
    // Deliberate escapes -- dropdowns, tooltips, the login modal -- are taken out
    // of flow ON PURPOSE, and reporting them would be the gate crying wolf.
    if (s.position === 'fixed' || s.position === 'absolute') continue;
    let n = el.parentElement, rod = null;
    while (n && n !== document.body) {
      const tip = konteyner(n);
      if (tip) { rod = {el: n, tip}; break; }
      n = n.parentElement;
    }
    if (!rod) continue;                 // nothing owns it but the page itself
    out.na_vyhod++;
    const a = el.getBoundingClientRect(), b = vnutri(rod.el);
    const vlevo = Math.round(b.l - a.left), vpravo = Math.round(a.right - b.r);
    if (rod.tip === 'клип') {
      // 🔴 A CLIPPING CONTAINER HIDES WHAT LEAVES IT TO THE RIGHT, and check 1
      // catches that through scrollWidth.  To the LEFT it catches nothing:
      // `scrollWidth` in a left-to-right document NEVER grows leftwards, so
      // content that walks out of the left edge is painted nowhere and counted
      // nowhere.  The verifier proved it as an A/B: shifting a card's children
      // `left:-260px` emptied the whole right-hand column on the screenshot and
      // left the gate at (0,0,0,0), while `+260px` on the same nodes gave
      // (4,0,0,0).  This is the very defect this file was rewritten for, mirrored.
      if (vlevo > 1) {
        out.vyshli.push({put: put(el), rod: put(rod.el), tip: 'срезано слева',
                         vlevo, vpravo: 0, tekst: chistyy(el)});
      }
      continue;
    }
    if (vlevo > 1 || vpravo > 1) {
      out.vyshli.push({put: put(el), rod: put(rod.el), tip: rod.tip,
                       vlevo, vpravo, tekst: chistyy(el)});
    }
  }

  // ── 5. ЦЕНТРИРОВАНИЕ ───────────────────────────────────────────────────────
  // 🔴 ПРАВИЛО КАНОНА, А НЕ ГЕОМЕТРИЯ: «НИКОГДА по центру мы не центрируем»
  // (владелец, 10.09 11:4x).  Дефект возвращался ЧЕТЫРЕЖДЫ, пока правило жило
  // текстом в документе, — поэтому оно здесь, рядом с четырьмя, которые краснеют.
  //
  // МЕРИТСЯ РЕНДЕР, А НЕ РАЗМЕТКА.  Центрирование приходит и из класса, и по
  // наследству от предка, и строка `text-align` в исходнике может не иметь к
  // ЭТОМУ элементу никакого отношения — а у кнопок её нет вовсе, центр приезжает
  // из стилей самого браузера.  `getComputedStyle` знает правду обо всех случаях.
  //
  // 🔴 НАЗЫВАЕТСЯ КОРЕНЬ ЦЕНТРИРОВАННОГО ПОДДЕРЕВА, А НЕ ВСЁ ПОДДЕРЕВО.
  // `text-align` наследуется: одна строка CSS на карточке красит центром каждого
  // её потомка.  Замерено живьём 10.09 на кондуите — 1199 центрированных узлов
  // при 42 настоящих местах.  Список на тысячу строк никто не читает, и чинить
  // по нему нечего: чинится ОДНО правило, у корня.
  const ISKLYUCHENIYA = [
    // 🔴 ОДНО МЕСТО, ИМЯ И ПРИЧИНА НА КАЖДОЕ, И В СПИСОК ПОПАДАЕТ ТОЛЬКО ТО, ЧТО
    // ВЛАДЕЛЕЦ НАЗВАЛ ЯВНЫМ ИСКЛЮЧЕНИЕМ ВСЛУХ.  Сомневаешься — НЕ вноси, пусть
    // краснеет: лишнее красное стоит одной строки в отчёте, а лишнее исключение
    // возвращает дефект молча, и ровно так правило умирало трижды до этого гейта.
    // ⚠ Исключение СЕЛЕКТОРНОЕ: под ним прощается любой текст, оказавшийся в
    // клетке номера кондуита, а не только сам номер. Названо в списке
    // «НЕ ПРОВЕРЯЕТСЯ», найдено верификатором подменой текста в `th.zn`.
    {imya: 'номер задачи в клетке кондуита (H4.6)',
     sel: '#s-kond .kond th.zn',
     dom: 'veb/razdely/konduit.py:988',
     prichina: 'принято владельцем 10.09 11:3x дословно «мне всё нравится»: '
             + 'номер задачи стоит в клетке решётки, и клетка читается столбцом '
             + 'сверху вниз, а не строкой слева направо'},
  ];

  // Центрирование ТЕКСТА — наследуется, поэтому у него бывает корень поддерева.
  const centr_teksta = (s) =>
      s.textAlign === 'center' || s.textAlign === '-webkit-center' ||
      // 🔴 И `text-align-last` ТОЖЕ.  Он центрирует ту же строку другим
      // свойством, и проверка, знающая только `text-align`, оставляла бы дырку,
      // через которую то же самое центрирование возвращается легально.
      s.textAlignLast === 'center';

  // 🔴 ЦЕНТРИРОВАНИЕ БОКСОМ — ТА ЖЕ ВЫКЛЮЧКА ОДНОЙ ДРУГОЙ СТРОКОЙ CSS.  Текст,
  // лежащий прямо во флекс-контейнере с `justify-content:center`, встаёт ровно
  // туда же, куда его поставил бы `text-align:center`: верификатор замерил зазор
  // [0,120] → [60,60] — пиксель в пиксель как у запрещённого способа.  Правило
  // владельца про то, что видно глазом, а не про имя свойства.  НЕ наследуется:
  // такой элемент всегда сам себе корень.
  const centr_boksa = (s) =>
      ['flex','inline-flex','grid','inline-grid'].includes(s.display) &&
      (s.justifyContent === 'center' || s.placeContent === 'center');

  // 🔴 КОНТРОЛЫ ОСТАЮТСЯ В ОБХОДЕ ЭТОЙ ПРОВЕРКИ, в отличие от проверок 1-2.
  // Там их выбрасывают потому, что их КОРОБКУ рисует браузер; здесь судится не
  // коробка, а выключка текста внутри неё, и она наша.  Найдено верификатором:
  // поле кабинета («чт 303», `veb/obshchee/karkas.py:1644`) стоит по центру на
  // живом сайте, а `INPUT` был выброшен из обхода целиком — собственное
  // нарушение канона гейт не называл ни на одном из тринадцати экранов.
  const ne_dlya_centra = (el) =>
      ['SCRIPT','STYLE','SVG','PATH','BR'].includes(el.tagName);

  // 🔴 `<html>` И `<body>` — В СПИСКЕ КАНДИДАТОВ.  Обход идёт по `body *`, и
  // `body{text-align:center}` центрировал бы ВСЮ страницу, не дав ни одного
  // корня: у каждого потомка родитель тоже центрирован, и проверка молчала бы
  // ровно на самом большом нарушении, какое бывает.
  const kandidaty = [document.documentElement, document.body,
                     ...vse.filter(el => !ne_dlya_centra(el) && vidim(el))];
  out.na_centr = kandidaty.length;

  // Текст, который рисует САМ этот элемент, — то, на чём центрирование видно.
  // Три источника, и два из них `textContent` не знает:
  //   * контрол рисует своё ЗНАЧЕНИЕ (закрытый `<select>` показывает выбранный
  //     пункт, `<input>` — value); `chistyy()` вычитает `<option>` и оставляет
  //     пустоту, и 198 центрированных селектов оставались невидимыми;
  //   * псевдоэлемент рисует свой `content`, которого в DOM нет вовсе.
  // Оба найдены верификатором, оба — настоящее центрирование на настоящей
  // странице, которое гейт не называл.
  const svoy_tekst = (el) => {
    if (el.tagName === 'INPUT')
      return (el.value || el.placeholder || '').trim();
    if (el.tagName === 'SELECT')
      return (el.selectedOptions[0] ? el.selectedOptions[0].textContent : '').trim();
    if (el.tagName === 'TEXTAREA') return (el.value || '').trim();
    for (const k of el.childNodes)
      if (k.nodeType === 3 && (k.nodeValue || '').trim()) return k.nodeValue.trim();
    for (const p of ['::before', '::after']) {
      const c = getComputedStyle(el, p).content;
      if (c && c !== 'none' && c !== 'normal' && /^["']/.test(c))
        return c.slice(1, -1).trim();
    }
    return '';
  };

  // 🔴 У ПСЕВДОЭЛЕМЕНТА СВОЯ ВЫКЛЮЧКА, И ОН БЫВАЕТ ЦЕНТРИРОВАН ТАМ, ГДЕ САМ
  // ЭЛЕМЕНТ — НЕТ.  `#x::before{content:"…";text-align:center}` центрирует
  // надпись, которой в DOM не существует вовсе: `textContent` пуст, узел
  // отсекался границей «нет своего текста», и строка уезжала в середину при
  // нулях по всем пяти проверкам. Найдено верификатором порчей живой страницы.
  const psevdo_centr = (el) => {
    for (const p of ['::before', '::after']) {
      const s = getComputedStyle(el, p);
      const c = s.content;
      if (!c || c === 'none' || c === 'normal' || !/^["']/.test(c)) continue;
      if (centr_teksta(s)) return {p, tekst: c.slice(1, -1).trim()};
    }
    return null;
  };

  // Content box: `text-align` раздаёт свободное место ВНУТРИ него, за вычетом и
  // рамки, и внутренних отступов.  Считать от padding box нельзя — padding кнопки
  // выглядел бы сдвигом текста, которого нет.
  const soderzhimoe = (el) => {
    const r = el.getBoundingClientRect(), s = getComputedStyle(el);
    return {l: r.left + parseFloat(s.borderLeftWidth) + parseFloat(s.paddingLeft),
            r: r.right - parseFloat(s.borderRightWidth) - parseFloat(s.paddingRight)};
  };

  // 🔴 ЦЕНТРИРОВАНИЕ, НЕ СДВИГАЮЩЕЕ НИ ПИКСЕЛЯ, — НЕ НАХОДКА, А КРИК ВОЛКОМ.
  // Замерено верификатором: кнопки `#sohranit`/`#sbrosit` (центр из UA-стиля
  // браузера, своего правила в `veb/**` нет) и восемь однобуквенных клеток
  // `td.tg` («Н», «Д») сжаты по тексту — зазор [0,0] с обеих сторон, текст не
  // сдвинут никуда.  На экране «класс» ОБЕ находки были такими: целый экран
  // объявлялся нарушителем канона на пикселях, которых нет, а гейт, кричащий
  // волком, выключают.  Такие узлы СЧИТАЮТСЯ отдельным числом и печатаются —
  // молчаливое прощение неотличимо от дырки в проверке.
  const sdvig = (el) => {
    const d = document.createRange();
    d.selectNodeContents(el);
    const rects = [...d.getClientRects()].filter(r => r.width > 0 && r.height > 0);
    if (!rects.length) return null;      // нечем мерить: контрол, псевдоэлемент
    const b = soderzhimoe(el);
    return {sleva: Math.round(Math.min(...rects.map(r => r.left - b.l))),
            sprava: Math.round(Math.min(...rects.map(r => b.r - r.right)))};
  };

  // Корень поддерева: самый верхний ВИДИМЫЙ центрированный предок, выше которого
  // центрирования уже нет.  🔴 НЕВИДИМЫЕ ПРЕДКИ ПРОПУСКАЮТСЯ, А НЕ ОСТАНАВЛИВАЮТ
  // ПОДЪЁМ.  Верификатор обернул текст в `<div style="display:contents;
  // text-align:center">`: у такой обёртки нулевой прямоугольник, в кандидаты она
  // не попадает и находкой стать не может, а всех потомков глушило правило
  // «родитель центрирован — значит не корень».  Двенадцать блоков уехали в
  // середину, гейт показал 0 → 0.
  const koren = (el) => {
    let k = el;
    for (let n = el.parentElement; n; n = n.parentElement) {
      if (!centr_teksta(getComputedStyle(n))) break;
      if (vidim(n) && !ne_dlya_centra(n)) k = n;
    }
    return k;
  };

  const proshcheno = (el) => ISKLYUCHENIYA.some(i => el.matches(i.sel));

  const nayden = new Map();
  for (const el of kandidaty) {
    const s = getComputedStyle(el);
    const tekstom = centr_teksta(s), boksom = centr_boksa(s);
    if (!tekstom && !boksom) {
      const ps = psevdo_centr(el);
      if (!ps || !ps.tekst) continue;
      if (proshcheno(el)) { out.isklyucheno++; continue; }
      if (!nayden.has(el))
        nayden.set(el, {put: put(el), tekst: ps.tekst.slice(0, 40),
                        chem: `text-align:center (${ps.p})`,
                        sdvig: 'сдвиг не измерим (псевдоэлемент)', gde: ''});
      continue;
    }
    // 🔴 ГРАНИЦА ИЗМЕРЕНИЯ, А НЕ ПОБЛАЖКА: у элемента, который сам не рисует
    // текста, центрировать нечего и процитировать в отчёте нечего.  Это, а не
    // милость к кондуиту, отсекает 1095 ПУСТЫХ клеток решётки; правило одно и то
    // же на всех экранах.  Названо вслух в списке «НЕ ПРОВЕРЯЕТСЯ».
    const t = svoy_tekst(el);
    if (!t) continue;
    if (proshcheno(el)) { out.isklyucheno++; continue; }
    const d = sdvig(el);
    if (d && !(d.sleva > 1 && d.sprava > 1)) { out.bez_sdviga++; continue; }
    const k = tekstom ? koren(el) : el;
    if (proshcheno(k)) { out.isklyucheno++; continue; }
    if (nayden.has(k)) continue;
    nayden.set(k, {
        put: put(k), tekst: t.replace(/\s+/g, ' ').slice(0, 40),
        chem: boksom ? 'justify-content:center'
            : (s.textAlign === 'center' || s.textAlign === '-webkit-center')
              ? 'text-align:center' : 'text-align-last:center',
        sdvig: d ? `сдвиг слева ${d.sleva} справа ${d.sprava}`
                 : 'сдвиг не измерим (контрол или псевдоэлемент)',
        gde: k === el ? '' : put(el)});
  }
  out.centr = [...nayden.values()];

  return out;
}
"""

# Deliberate breakage for the self-test.  Every one of the four checks must have
# something to catch AND BE SEEN TO CATCH IT: a gate that goes red on three of
# four while the fourth quietly does nothing is the very failure this file exists
# to end.  🔴 Everything below is applied to the elements that are VISIBLE ON THE
# SCREEN BEING MEASURED.  Measured live 10.09: breaking `document.querySelector(
# '.kto')` broke the first `.kto` in the DOCUMENT, which on every tab but
# «школьникам» sits on a hidden tab — the gate never looks at it, the self-test
# reported a triumphant red, and that red came entirely from the h-scroll.
LOMKA = r"""() => {
  const vidno = (el) => { const r = el.getBoundingClientRect();
      return r.width > 1 && r.height > 1; };
  const iz = (sel) => [...document.querySelectorAll(sel)].filter(vidno);
  const otchet = {obrezka: false, perenos: false, vyhod: false, skroll: false,
                  centr: false};

  // 🔴 EVERY BREAKAGE VERIFIES THAT IT LANDED, AND TRIES AGAIN WHEN IT DID NOT.
  // The verifier caught the previous version rapporting a triumphant red on all
  // thirteen screens while on five of them ONLY the h-scroll had fired: the
  // clipping breakage set `width:8px` on a `td.kto` inside a `table-layout:auto`
  // table, where the browser ignores it (measured: 311px -> 303px), and the
  // self-test never asked whether the damage had any effect. A self-test that
  // reports on damage it failed to inflict is the same lie as a gate reporting on
  // nodes it failed to look at.

  // 1. CLIPPING -- squeeze a text box shut. Deliberately prefers a NON-LEAF node
  //    (`.kto` wraps a `<b>`), the exact shape the walk used to drop.
  // 🔴 ЦЕЛЬ ОБЯЗАНА ИМЕТЬ СОБСТВЕННЫЙ ТЕКСТ ВНЕ КОНТРОЛА.  Проверка 1 судит по
  // прямоугольникам ТЕКСТА элемента и вычитает содержимое `<select>`/`<option>`/
  // `<input>` (`rects_teksta`), поэтому строка распределения, весь текст которой
  // лежит в селектах, для неё пуста — сжать её можно, а поймать нечего.  Пока
  // этой границы здесь не было, самопроверка ставила `🔴 ПРОПУСТИЛА 1` на
  // «постоянное · принимающим» и обвиняла зрение гейта в собственном промахе.
  // Прямоугольники СОБСТВЕННОГО текста, минус то, что рисует браузер, — та же
  // граница, что у `rects_teksta` в `ZAMER`, повторённая здесь нарочно: это
  // другой контекст исполнения, общей функции у них нет, и расхождение обязано
  // быть видно как расхождение.
  const rezhet_bukvu = (el) => {
    const VNE = ['SELECT','OPTION','TEXTAREA','INPUT','BUTTON','STYLE','SCRIPT'];
    const rects = [];
    const hod = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, {
      acceptNode(n) {
        if (!(n.nodeValue || '').trim()) return NodeFilter.FILTER_REJECT;
        for (let p = n.parentElement; p && p !== el.parentElement; p = p.parentElement)
          if (VNE.includes(p.tagName)) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    for (let n = hod.nextNode(); n; n = hod.nextNode()) {
      const d = document.createRange(); d.selectNodeContents(n);
      for (const b of d.getClientRects()) if (b.width > 0 && b.height > 0) rects.push(b);
    }
    if (!rects.length) return false;
    const r = el.getBoundingClientRect(), s = getComputedStyle(el);
    const l = r.left + parseFloat(s.borderLeftWidth);
    const pr = r.right - parseFloat(s.borderRightWidth);
    const tp = r.top + parseFloat(s.borderTopWidth);
    const bt = r.bottom - parseFloat(s.borderBottomWidth);
    return rects.some(b => b.right - pr > 1 || l - b.left > 1
                        || b.bottom - bt > 1 || tp - b.top > 1);
  };

  const svoy_tekst_est = (el) => {
    const k = el.cloneNode(true);
    k.querySelectorAll('select, option, input, textarea, button, style, script')
     .forEach(n => n.remove());
    return (k.textContent || '').trim().length > 0;
  };
  for (const k of iz('.kto, td, th, li, .para').slice(0, 40)) {
    if (!svoy_tekst_est(k)) continue;
    k.style.setProperty('max-width', '8px', 'important');
    k.style.setProperty('overflow', 'hidden', 'important');
    k.style.whiteSpace = 'nowrap'; k.style.textOverflow = 'ellipsis';
    k.style.display = k.tagName === 'TD' || k.tagName === 'TH' ? 'block' : k.style.display;
    // 🔴 «КОРОБКА ПЕРЕПОЛНЕНА» — ЕЩЁ НЕ «ТЕКСТ ОБРЕЗАН», и разница ровно та, из-за
    // которой проверка 1 не считает находкой ни `<option>`, ни декорацию в SVG:
    // `scrollWidth` растёт от чего угодно, а режется БУКВА.  Замерено 11.09 на
    // «постоянное · принимающим»: сжатая `td.td-deti` дала scrollWidth 63 при
    // clientWidth 32, а собственный текст клетки («пн») спокойно уместился в
    // 32px — гейт молчал совершенно правильно, а самопроверка засчитывала это
    // себе в пропуск.  Условие приземления теперь ДОСЛОВНО то же, по которому
    // судит `ZAMER`: прямоугольники СВОЕГО текста выходят за padding box.
    if (k.scrollWidth > k.clientWidth + 1 && rezhet_bukvu(k)) { otchet.obrezka = true; break; }
    k.style.removeProperty('max-width'); k.style.removeProperty('overflow');
    k.style.whiteSpace = ''; k.style.textOverflow = ''; k.style.display = '';
  }

  // 2. NEEDLESS WRAP -- a break where the width did not require one. Forced with
  //    a `<br>` rather than by squeezing: squeezing and widening back cannot work,
  //    because CSS re-lays out the moment the width changes and the wrap goes with
  //    it. A `<br>` reproduces the DEFINITION the check judges by.
  for (const w of iz('span, td, li, div, p').slice(0, 300)) {
    if ([...w.children].some(c => (c.textContent || '').trim())) continue;
    // 🔴 THE DAMAGE MUST LAND ON THE POPULATION THE CHECK JUDGES, or the self-test
    // measures the gate's blind spots instead of its sight. The wrap check skips
    // flex/grid boxes (no line boxes to count) and form controls; a breakage aimed
    // at those is a breakage nobody promised to catch. Found by this very block
    // going red on «кондуит»: it had broken a box the check never looks at.
    const st = getComputedStyle(w);
    if (['flex','inline-flex','grid','inline-grid'].includes(st.display)) continue;
    if (st.whiteSpace === 'pre') continue;
    if (['SELECT','OPTION','TEXTAREA','INPUT','BUTTON'].includes(w.tagName)) continue;
    // ...and it must be a box whose available width the check can name at all: an
    // inline span sharing its line with siblings is left unjudged on purpose (see
    // `dostupno`), so breaking one would be testing a declared blind spot and
    // calling the result a miss.
    if (w.clientWidth <= 0) continue;
    const slova = (w.textContent || '').trim().split(/\s+/);
    if (slova.length < 2 || w.scrollWidth > w.clientWidth + 1) continue;
    // 🔴 И ЭЛЕМЕНТ ОБЯЗАН СТОЯТЬ В ОДНУ СТРОКУ ДО ПОЛОМКИ.  Иначе `<br>` ставится
    // туда, где перенос УЖЕ был законным (ширина его потребовала), проверка 2
    // молчит совершенно правильно, а самопроверка засчитывает это себе в
    // пропуск.  Найдено 11.09 на `/istoria`, где текстовых узлов всего четыре и
    // промах стал видно сразу; на широких экранах он просто прятался за
    // множеством других целей.
    const do_r = document.createRange(); do_r.selectNodeContents(w);
    const do_verhi = new Set([...do_r.getClientRects()]
        .filter(b => b.width > 0 && b.height > 0).map(b => Math.round(b.top)));
    if (do_verhi.size !== 1) continue;
    w.textContent = '';
    w.append(document.createTextNode(slova.slice(0, -1).join(' ')),
             document.createElement('br'),
             document.createTextNode(slova[slova.length - 1]));
    // verify it actually took two line boxes, and undo if it did not
    const d = document.createRange(); d.selectNodeContents(w);
    const verhi = new Set([...d.getClientRects()]
        .filter(b => b.width > 0 && b.height > 0).map(b => Math.round(b.top)));
    if (verhi.size >= 2) { otchet.perenos = true; break; }
    w.textContent = slova.join(' ');
  }

  // 4. ESCAPED -- pills walk out of the LEFT edge of the card that owns them,
  //    exactly as in the owner's screenshot `13`, and the document does NOT
  //    scroll on that account, so checks 1-3 stay blind to it.
  // 🔴 БЛИЖАЙШИЙ ВИДИМЫЙ КОНТЕЙНЕР СДВИНУТОГО УЗЛА ОБЯЗАН БЫТЬ ИМЕННО `pa`.
  // Проверка 4 поднимается от элемента до ПЕРВОГО предка, который клипует,
  // красит рамку с двух сторон или свой фон, — и судит по НЕМУ.  Сдвигая `<b>`
  // внутри `.kto` (а `.kto` клипует), поломка выводила узел за `.kto`, а не за
  // карточку, и попадала в объявленную границу проверки; самопроверка при этом
  // писала «ПРОПУСТИЛА 1» на «постоянное · школьникам».  Та же логика, что в
  // `ZAMER`, повторена здесь нарочно: это ДРУГОЙ контекст исполнения, общей
  // функции у них нет, и расхождение обязано быть видно как расхождение.
  const prozr_l = (c) => !c || c === 'transparent' || c === 'rgba(0, 0, 0, 0)';
  const konteyner_l = (el) => {
    const s = getComputedStyle(el);
    if (s.overflowX !== 'visible' || s.overflowY !== 'visible') return true;
    if ((parseFloat(s.borderLeftWidth) && parseFloat(s.borderRightWidth)) ||
        parseFloat(s.borderTopLeftRadius)) return true;
    return !prozr_l(s.backgroundColor);
  };
  const blizhayshiy = (el) => {
    for (let n = el.parentElement; n && n !== document.body; n = n.parentElement)
      if (konteyner_l(n)) return n;
    return null;
  };
  const cel = iz('.kol-pr .para').length ? iz('.kol-pr .para') : iz('.para');
  for (const pa of cel) {
    pa.style.background = 'rgba(255,255,255,.06)';
    pa.style.borderRadius = '8px';
    const deti = pa.querySelectorAll('.deti-ryad span, .komu.deti span, .komu, b');
    // 🔴 И СДВИНУТЫЙ УЗЕЛ ОБЯЗАН ОСТАТЬСЯ ВИДИМЫМ.  Поломки применяются к одной
    // и той же странице одна за другой, и сжатие из пункта 1 успевает схлопнуть
    // строку до 8px: `span.komu` внутри неё получает нулевую ширину, `vidim()`
    // в `ZAMER` считает такой узел невидимым (и правильно — читать там нечего),
    // а самопроверка писала «ПРОПУСТИЛА 1» на «постоянное · школьникам».
    const zhivoy = (x) => { const r = x.getBoundingClientRect();
        return r.width > 1 && r.height > 1; };
    const kogo = [...(deti.length ? deti : pa.children)]
        .filter(x => zhivoy(x) && blizhayshiy(x) === pa);
    if (!kogo.length) { pa.style.background = ''; pa.style.borderRadius = ''; continue; }
    const rod = pa.getBoundingClientRect();
    kogo.forEach(x => { x.style.position = 'relative'; x.style.left = '-120px'; });
    if (kogo.some(x => zhivoy(x) && x.getBoundingClientRect().left < rod.left - 1)) {
      otchet.vyhod = true; break;
    }
  }

  // 5. ЦЕНТРИРОВАНИЕ -- поставить `center` там, где его не было.  Ломается ИМЕННО
  //    КОРЕНЬ: проверка называет элемент, чей родитель не центрирован, поэтому
  //    поломка, посаженная внутрь уже центрированного поддерева, была бы поломкой
  //    того, о чём проверка молчит нарочно, — и самопроверка мерила бы объявленное
  //    слепое пятно вместо зрения.
  // 🔴 И СПИСОК ЦЕЛЕЙ КОНЧАЕТСЯ ОБЩИМ `body *`, А НЕ ИМЕНАМИ КЛАССОВ ЭТОГО САЙТА.
  //    С одними `.kto/.para/li/p` поломка не села на «принимающим» и «классе» —
  //    там таких узлов нет, — и самопроверка честно писала «сломано на 11 из 13»
  //    вместо того, чтобы испытать проверку на всех тринадцати.
  const centr = (e) => e && ['center', '-webkit-center']
      .includes(getComputedStyle(e).textAlign);
  for (const c of [...iz('.kto, .para, li, p, td.kto, .komu'),
                   ...iz('body *')].slice(0, 600)) {
    if (centr(c) || centr(c.parentElement)) continue;
    if (!(c.textContent || '').trim()) continue;
    // Внутри <style>/<script> текста для читателя нет, и проверка 5 такой узел
    // не назовёт: `chistyy()` вычитает их содержимое и оставляет пустую строку.
    if (c.querySelector('style, script') || ['STYLE','SCRIPT'].includes(c.tagName))
      continue;
    // Исключение из запрета — не поломка: проверка обязана его ПРОСТИТЬ, и
    // ломать его значило бы объявить провалом ровно то поведение, ради которого
    // список исключений и заведён.
    if (c.matches('#s-kond .kond th.zn')) continue;
    c.style.setProperty('text-align', 'center', 'important');
    // 🔴 И ПОЛОМКА ОБЯЗАНА БЫТЬ ТОГО РОДА, КОТОРЫЙ ПРОВЕРКА НАЗЫВАЕТ.  Проверка 5
    // не считает находкой центрирование, не сдвинувшее текста ни на пиксель
    // (бокс сжат по тексту — двигать нечего), поэтому `text-align:center`,
    // посаженный на такой бокс, — это поломка объявленного слепого пятна, а её
    // «непойманность» была бы враньём о зрении гейта. Смещение проверяется тут же.
    const r = document.createRange(); r.selectNodeContents(c);
    const kor = [...r.getClientRects()].filter(b => b.width > 0 && b.height > 0);
    const st = getComputedStyle(c), box = c.getBoundingClientRect();
    const l = box.left + parseFloat(st.borderLeftWidth) + parseFloat(st.paddingLeft);
    const rr = box.right - parseFloat(st.borderRightWidth) - parseFloat(st.paddingRight);
    const sdvinut = kor.length &&
        Math.min(...kor.map(b => b.left - l)) > 1 &&
        Math.min(...kor.map(b => rr - b.right)) > 1;
    if (centr(c) && sdvinut) { otchet.centr = true; break; }
    c.style.removeProperty('text-align');
  }

  // 3. H-SCROLL -- push the document wider than the window.
  const d = document.createElement('div');
  d.style.width = '2400px'; d.style.height = '1px';
  document.body.appendChild(d);
  otchet.skroll = document.documentElement.scrollWidth >
                  document.documentElement.clientWidth;
  return otchet;
}"""


def zhivaya_baza() -> Path:
    """The real project database -- every active pupil, not three invented rows."""
    put = baza()
    if not put.exists():
        raise SystemExit(f"нет живой базы: {put}")
    return put


def chisla_bazy(db: Path) -> dict:
    """Group sizes read from the live base.  Never hard-code 25 or 27 here:
    the number the gate must survive is whatever the school actually has today."""
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    # 🔴 ПЕРВОЙ СТРОКОЙ — ОТКУДА ЧИСЛА (Д1, владелец 10.09). Путь и дата последней
    # ЗАПИСИ внутри базы; красное, если база старше последнего занятия. Дата ФАЙЛА
    # для этого не годится: копирование и rsync её обновляют, не добавив ни строки.
    try:                                  # запуск и модулем, и файлом из tools/
        from core.istochnik import nazvat_i_proverit
    except ModuleNotFoundError:           # прямой запуск: корня репозитория нет в sys.path
        import sys as _s, pathlib as _p
        _s.path.insert(0, str(_p.Path(__file__).resolve().parent.parent))
        from core.istochnik import nazvat_i_proverit
    nazvat_i_proverit(c)
    try:
        klassy = dict(c.execute(
            "select class, count(*) from students where status='active' "
            "group by class").fetchall())
        return {"po_klassam": klassy,
                "krupneyshiy": max(klassy.values()) if klassy else 0,
                "vsego": sum(klassy.values())}
    finally:
        c.close()


def podnyat_server(db: Path):
    import config  # noqa: F401  (imported for its side effects on paths)
    import veb.server as server
    from infra.db import connect

    conn = connect(db)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    httpd.connection = conn          # type: ignore[attr-defined]
    httpd.db_path = str(db)          # type: ignore[attr-defined]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd, conn, t, f"http://127.0.0.1:{httpd.server_address[1]}"


def kuka() -> dict:
    """An organiser cookie, exactly as /vhod hands one to a browser.  The conduit
    tab is gated on the capability `videt-konduit`, which a guest does not have --
    measuring that page as a guest would silently check an empty screen.
    🔴 The GUEST is measured too, and without this the gate is blind to the only
    screen the owner ever photographs: the site as everyone else sees it."""
    from veb import vhod
    return {"name": vhod.COOKIE_NAME, "value": vhod._make_cookie("organizator")}


def svoy_dom(baza_url: str, adres: str) -> bool:
    """Осталась ли страница на сервере, который поднял гейт.

    Отдельной функцией, а не строкой внутри прогона, ровно потому, что это
    ПРАВИЛО, а не подробность: его можно испытать литералами, без сети и без
    браузера, и оно не зависит от того, отвечает ли сегодня чужой хост.

    🔴 НЕ ГОЛЫЙ `startswith`: `http://127.0.0.1:54321x/` начинается с адреса
    гейта и сервером гейта не является. Хвост обязан быть пустым или начинаться
    с разделителя пути. Найдено собственным тестом на литералах, не рассуждением.
    """
    if not adres.startswith(baza_url):
        return False
    hvost = adres[len(baza_url):]
    return hvost == "" or hvost[0] in "/?#"


def klyuch_ekrana(baza_url: str, adres: str, radio: str | None) -> tuple:
    """Чем один измеренный экран отличается от другого: путь, на котором браузер
    ОСТАНОВИЛСЯ, плюс выбранная вкладка.

    По этому ключу переадресация сводится к своей цели: `/glavnaya` отвечает 302
    на `/` (`veb/server.py:718`), и мерить её отдельно значит написать то же
    число второй раз. Раздутый охват врёт в ту же сторону, что и заниженный.
    """
    put = (adres[len(baza_url):] or "/") if svoy_dom(baza_url, adres) else adres
    return (put.split("?")[0], radio)


def progon(baza_url: str, slomat: bool, otbor: str | None,
           vse_ekrany: list) -> tuple[list, int]:
    from playwright.sync_api import sync_playwright

    ekrany = [e for e in vse_ekrany if not otbor or otbor.lower() in e[0].lower()]
    itogi = []
    with sync_playwright() as pw:
        brauzer = pw.chromium.launch()
        for rol in ("гость", "организатор"):
            svoi = [e for e in ekrany if rol in e[3]]
            if not svoi:
                continue
            ctx = brauzer.new_context(viewport=ETALON)
            page = ctx.new_page()
            vidennoe: dict = {}
            for imya, put, radio, _roli in svoi:
                try:
                    # 🔴 КУКА ОБНОВЛЯЕТСЯ ПЕРЕД КАЖДЫМ ПЕРЕХОДОМ, А НЕ ОДИН РАЗ НА
                    # КОНТЕКСТ.  Список экранов теперь строится из роутов, и среди
                    # роутов есть `/vyhod`, который СТИРАЕТ куку (`veb/server.py:691`):
                    # один заход на него — и все следующие экраны организатора
                    # молча меряются глазами гостя, с честными числами и не тем
                    # содержимым.  Пока список был рукописным, такого роута в нём
                    # быть не могло, и одна `add_cookies` на контекст была верна.
                    if rol == "организатор":
                        ctx.add_cookies([{**kuka(), "url": baza_url}])
                    page.goto(baza_url + put, wait_until="networkidle", timeout=20000)
                    # 🔴 ПЕРЕАДРЕСАЦИЯ СВОДИТСЯ К ЦЕЛИ, А НЕ СЧИТАЕТСЯ ВТОРЫМ
                    # ЭКРАНОМ.  `/glavnaya`, `/listki`, `/listki-8` отвечают 302 на
                    # `/` — измерять их отдельно значит трижды написать одно и то же
                    # число и раздуть охват работой, которой не было.  Куда именно
                    # ведёт роут, спрашивается У БРАУЗЕРА после перехода: таблицы
                    # переадресаций здесь нет и устареть нечему.
                    # 🔴 ЭКРАН, УШЕДШИЙ С СЕРВЕРА ГЕЙТА, — КРАСНОЕ, А НЕ ЭКРАН.
                    # Найдено 11.09 первым же прогоном по роутам: гостю корень
                    # отдаёт `docs/index.html`, а это заглушка-переадресация —
                    # `<meta refresh>` плюс `location.replace("http://math-
                    # kluychiki.ru/")` (`docs/index.html:13`, `:34`). Браузер
                    # уходил на ЧУЖОЙ САЙТ, и гейт честно мерил его: четыре
                    # экрана гостя («класс», «/glavnaya», обе вкладки постоянного)
                    # давали одни и те же 46/45/72/78 из 2063 — числа настоящие,
                    # страница не та. Роль гостя завели 10.09 именно потому, что
                    # владелец фотографирует сайт БЕЗ пароля; ровно этот экран и
                    # не измерялся ни разу.
                    if not svoy_dom(baza_url, page.url):
                        itogi.append((rol, imya, put, None,
                                      f"экран ушёл с сервера гейта на {page.url} "
                                      f"— измерен был бы ЧУЖОЙ документ"))
                        continue
                    kuda = page.url[len(baza_url):] or "/"
                    klyuch = klyuch_ekrana(baza_url, page.url, radio)
                    if klyuch in vidennoe:
                        itogi.append((rol, imya, put, None,
                                      f"{SVEDENO} переадресация на {kuda} — уже "
                                      f"измерено как «{vidennoe[klyuch]}»"))
                        continue
                    vidennoe[klyuch] = imya
                    if radio:
                        if not page.query_selector("#" + radio):
                            itogi.append((rol, imya, put, None,
                                          f"переключателя #{radio} нет на странице"))
                            continue
                        page.evaluate("(i)=>document.getElementById(i).checked=true", radio)
                        page.wait_for_timeout(200)
                    lomka_otchet = None
                    if slomat:
                        lomka_otchet = page.evaluate(LOMKA)
                        page.wait_for_timeout(150)
                    z = page.evaluate(ZAMER)
                    if lomka_otchet is not None:
                        z["lomka"] = lomka_otchet
                except Exception as exc:                       # noqa: BLE001
                    itogi.append((rol, imya, put, None, str(exc).splitlines()[0][:90]))
                    continue
                itogi.append((rol, imya, put, z, None))
            ctx.close()
        brauzer.close()
    # How many measurements this run OWED: one per screen per role that can see
    # it.  Never a formula over the screen count — «проверено 6 экранов из 5» is
    # the arithmetic of a gate that does not know what it set out to do.
    return itogi, sum(len(e[3]) for e in ekrany)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slomat", action="store_true",
                    help="self-test: break the screens on purpose; the gate MUST go red")
    ap.add_argument("--ekran", default=None,
                    help="run one screen only, by substring of its name")
    args = ap.parse_args()

    # 🔴 «ПОЗВАЛИ НЕВЕРНО» — ОТДЕЛЬНЫЙ КОД ВОЗВРАТА, А НЕ «ЧИСТО».  `--ekran` с
    # именем, которого нет, отбирал ноль экранов, и гейт возвращал 1 — то же, что
    # «нашёл дефект», так что опечатка в имени экрана выглядела снаружи как
    # находка.  Второй такой же исход — argparse на неизвестном флаге, он и так
    # отдаёт 2.  Найдено `check_tool_contract.py`, не рассуждением.
    db = zhivaya_baza()
    # 🔴 СПИСОК ЭКРАНОВ СТРОИТСЯ ЗДЕСЬ, ИЗ РОУТОВ, И ПРОВЕРКА ИМЕНИ ЭКРАНА ИДЁТ
    # ПОСЛЕ: пока список был константой, опечатку в `--ekran` можно было отловить
    # до всего, а маршруты живут в `veb/server.py` и в реестрах разделов, которые
    # надо сперва спросить.
    marshrutov = len([p for p, r in marshruty_sayta().items() if r != "ne-ekran"])
    ekrany_sayta, bedy_marshrutov = sobrat_ekrany(db)

    if args.ekran and not [e for e in ekrany_sayta if args.ekran.lower() in e[0].lower()]:
        print(f"позвали неверно: экрана «{args.ekran}» нет. Есть: "
              + ", ".join(e[0] for e in ekrany_sayta), file=sys.stderr)
        return 2

    chisla = chisla_bazy(db)
    httpd, conn, t, url = podnyat_server(db)
    try:
        itogi, dolzhno_byt = progon(url, args.slomat, args.ekran, ekrany_sayta)
    finally:
        httpd.shutdown(); httpd.server_close(); t.join(); conn.close()

    print(f"ГЕЙТ ВЁРСТКИ · эталон {ETALON['width']}x{ETALON['height']} · "
          f"живая база: {chisla['vsego']} школьников, "
          f"по классам {chisla['po_klassam']}, крупнейший класс {chisla['krupneyshiy']}")
    print(f"база: {db}")
    print(f"экраны построены из РОУТОВ, не из списка: маршрутов-страниц "
          f"{marshrutov} → экранов {len(ekrany_sayta)} "
          f"(вкладки — надстройка над маршрутом, `VKLADKI`)")
    for beda in bedy_marshrutov:
        print(f"   🔴 МАРШРУТ БЕЗ ЭКРАНА: {beda}")
    print()
    print(f"{'роль':<13}{'экран':<15}{'обрезка':>9}{'переносы':>10}"
          f"{'вышли':>8}{'центр':>7}{'скролл':>8}   охват узлов")
    krasnyh, izmereno, uzlov, svedeno = len(bedy_marshrutov), 0, 0, 0
    for rol, imya, put, z, oshibka in itogi:
        if z is None:
            if (oshibka or "").startswith(SVEDENO):
                svedeno += 1
                print(f"{rol:<13}{imya:<15}{'·':>9}{'·':>10}{'·':>8}{'·':>7}"
                      f"{'·':>8}   {oshibka}")
                continue
            print(f"{rol:<13}{imya:<15}{'—':>9}{'—':>10}{'—':>8}{'—':>7}"
                  f"{'—':>8}   🔴 {oshibka}")
            krasnyh += 1
            continue
        izmereno += 1
        uzlov += z["vsego"]
        ploho = (len(z["obrezka"]) + len(z["perenos"]) + len(z["vyshli"])
                 + len(z["centr"]) + (1 if z["skroll"] else 0))
        if ploho:
            krasnyh += 1
        # 🔴 ZERO NODES ON A LIVE SCREEN IS RED, NOT GREEN.  A walk that looked at
        # nothing reports no defects, and that is indistinguishable from a clean
        # page unless the coverage is printed next to the verdict.
        if z["vsego"] == 0 or z["na_obrezku"] == 0 or z["na_centr"] == 0:
            krasnyh += 1
            print(f"{rol:<13}{imya:<15}{'—':>9}{'—':>10}{'—':>8}{'—':>7}{'—':>8}   "
                  f"🔴 ОХВАТ НОЛЬ: узлов {z['vsego']}, на обрезку "
                  f"{z['na_obrezku']}, на центр {z['na_centr']}")
            continue
        print(f"{rol:<13}{imya:<15}{len(z['obrezka']):>9}{len(z['perenos']):>10}"
              f"{len(z['vyshli']):>8}{len(z['centr']):>7}{z['skroll']:>8}   "
              f"проверено {z['na_obrezku']}/{z['osmotreno']}/{z['na_vyhod']}/"
              f"{z['na_centr']} из {z['vsego']}")

    print()
    print(f"ОХВАТ: проверено {izmereno} экранов из {dolzhno_byt} обещанных "
          f"(+{svedeno} сведено к другим переадресацией); "
          f"осмотрено элементов {uzlov}")
    print("        четыре числа в колонке охвата — узлов на ОБРЕЗКУ / на ПЕРЕНОС / "
          "на ВЫХОД ЗА КОНТЕЙНЕР / на ЦЕНТР, из общего числа элементов страницы.")
    isk = sum(z["isklyucheno"] for _r, _i, _p, z, _o in itogi if z)
    bez = sum(z["bez_sdviga"] for _r, _i, _p, z, _o in itogi if z)
    if isk:
        print(f"        центрирований прощено по именованному списку исключений: "
              f"{isk}. Список — в `ZAMER`, константа `ISKLYUCHENIYA`: имя, "
              f"селектор, дом в разметке и причина на каждое.")
    if bez:
        print(f"        центрирований, не сдвинувших текста ни на пиксель: {bez} "
              f"(бокс сжат по тексту — двигать нечего). Находкой не считаются, но "
              f"напечатаны: молчаливое прощение неотличимо от дырки в проверке.")
    if izmereno == 0:
        print("🔴 ОХВАТ НОЛЬ при живом сервере — это КРАСНЫЙ, а не зелёный: "
              "гейт ничего не измерил.")
        return 1

    for rol, imya, put, z, oshibka in itogi:
        if not z:
            continue
        for vid, klyuch in (("ОБРЕЗКА", "obrezka"), ("ПЕРЕНОС", "perenos")):
            for d in z[klyuch][:8]:
                storona = f" {d['storona']}" if d.get("storona") else ""
                print(f"   {vid}{storona} · {rol} · {imya} · {d['put']} · "
                      f"«{d['tekst']}» · надо {d.get('nado', d.get('nuzhno'))} "
                      f"есть {d['est']}")
        for d in z["vyshli"][:8]:
            print(f"   ВЫШЛО · {rol} · {imya} · {d['put']} · «{d['tekst']}» · "
                  f"влево {d['vlevo']} вправо {d['vpravo']} · "
                  f"из {d['rod']} ({d['tip']})")
        for d in z["centr"][:8]:
            gde = f" · видно на {d['gde']}" if d["gde"] else ""
            print(f"   ЦЕНТР · {rol} · {imya} · {d['put']} · «{d['tekst']}» · "
                  f"{d['chem']} · {d['sdvig']}{gde}")
        if len(z["centr"]) > 8:
            print(f"   ЦЕНТР · {rol} · {imya} · …и ещё {len(z['centr']) - 8} — "
                  f"напечатаны первые восемь")

    print()
    print("НЕ ПРОВЕРЯЕТСЯ ЭТИМ ГЕЙТОМ: цвет и контраст, читаемость, подстановка "
          "шрифтов на машине без проектных шрифтов, мобильные ширины, печать, "
          "движение, озвучка экранным диктором. Гейт судит ГЕОМЕТРИЮ на одном "
          "эталоне и больше ничего."
          "\n🔴 И ОТДЕЛЬНО, ПОИМЁННО:"
          "\n · обрезку, сделанную НА СЕРВЕРЕ (строка укорочена в Python до отдачи "
          "в браузер) — в разметку приезжает уже короткий текст, переполнения нет. "
          "Гейт ловит обрезку РАМКОЙ, а не ножницами в коде."
          "\n · ВЕРТИКАЛЬНЫЙ выход за контейнер: проверка 4 сравнивает только левый "
          "и правый край. Таблетка, уехавшая ВНИЗ из карточки, не поймана."
          "\n · выход из контейнера, который НЕ красит ни рамки, ни фона и не режет: "
          "такой контейнер глазом не читается как край, и границы у него для гейта "
          "нет. Карточка без фона и рамки — слепое пятно."
          "\n · элементы `position:absolute` и `fixed` — они выходят за родителя "
          "НАРОЧНО (выпадающие списки, подсказки, окно входа), и проверка 4 их "
          "пропускает целиком. Сломанный выпадающий список гейт не увидит."
          "\n · роль `prepod`: гейт меряет ГОСТЯ и ОРГАНИЗАТОРА. Третья роль есть "
          "в `veb/vhod.py`, и её экраны не измерены ни разу."
          "\n · состояния, в которые страница приходит только по клику: раскрытые "
          "списки, окно входа, подсказка значка «обычно у». Гейт меряет покой."
          "\n · НАЛОЖЕНИЕ элементов друг на друга. Класса «перекрытие» среди "
          "четырёх проверок нет вовсе: строку можно положить поверх соседней, и "
          "все четыре числа останутся нулями, хотя читать нельзя. Замерено "
          "верификатором на «принимающим» у гостя."
          "\n · КОЛОНКА, В КОТОРОЙ ТЕКСТ РВЁТСЯ ПО БУКВАМ, но никуда не выходит: "
          "проверка 2 по определению прощает перенос, которого ширина "
          "«потребовала», проверка 1 не видит переполнения — имя, вставшее "
          "лесенкой по две буквы, для гейта здоровое. Дыра МЕЖДУ проверками."
          "\n · встроенный (`display:inline`) элемент, делящий строку с соседями: "
          "его доступную ширину назвать нечем (`clientWidth` встроенного бокса "
          "равен нулю по спецификации), а брать ширину блока нельзя — перенос "
          "из-за соседа законен. Такой элемент на перенос НЕ судится."
          "\n · текст внутри `<svg><text>`: `SVG` и `PATH` выброшены из обхода "
          "целиком, надписи на схемах не судятся."
          "\n · элемент, схлопнутый в ноль (высота или ширина меньше пикселя): "
          "`vidim()` считает его невидимым, а не сломанным."
          "\n · экраны, где `--slomat` не сумел нанести поломку: он теперь "
          "называет их сам отдельной строкой — на них испытаны не все пять "
          "проверок."
          "\n · центрирование БОКСА, внутри которого нет собственного текста: "
          "`justify-content:center` проверка 5 ловит только там, где текст лежит "
          "в самом флекс-контейнере. Ряд ТАБЛЕТОК, поставленный по середине "
          "карточки, и блок, центрированный `margin:0 auto`, ей не видны."
          "\n · центрирование элемента БЕЗ собственного видимого текста: "
          "центрировать в нём нечего и процитировать в отчёте нечего. Это "
          "граница измерения, а не исключение, и она одна и та же на всех "
          "экранах: ею же отсеиваются 1095 пустых клеток решётки кондуита."
          "\n · центрирование, НЕ СДВИНУВШЕЕ текста ни на пиксель (бокс сжат по "
          "тексту): считается отдельным числом и печатается, но находкой не "
          "является — красное на пикселях, которых нет, выключает гейт."
          "\n · подменённый текст внутри `#s-kond .kond th.zn`: исключение "
          "СЕЛЕКТОРНОЕ, и под ним прощается любой текст, оказавшийся в клетке "
          "номера кондуита, а не только сам номер."
          "\n · ЧИСЛО в колонке «центр» — это число МЕСТ (корней поддеревьев), а "
          "не число центрированных элементов. Центрирование, поднятое на предка, "
          "даёт ОДНУ находку вместо пятидесяти: замерено верификатором — 41 → 3 "
          "при том, что уехал весь экран. Падение числа не значит починки, "
          "починку показывает НОЛЬ."
          "\n · центрирование, приходящее ТОЛЬКО в состоянии, которого нет в "
          "покое (`:hover`, раскрытый список, окно входа): гейт меряет покой.")

    if args.slomat:
        # 🔴 «КРАСНЫЙ» ЕЩЁ НЕ ЗНАЧИТ «ВСЕ ЧЕТЫРЕ РАБОТАЮТ», А «13 ИЗ 13» НЕ ЗНАЧИТ
        # «ВЕЗДЕ ИСПЫТАНЫ ЧЕТЫРЕ». Общий красный скрывает и то, что краснеет одна
        # проверка из четырёх, и то, что на пяти экранах поломка вовсе не села, —
        # ровно тем способом, каким гейт врал до 10.09. Поэтому здесь считается
        # ДВОЕ: сколько раз поломку удалось нанести, и сколько раз её поймали.
        PROV = (("ОБРЕЗКА", "obrezka", "obrezka"),
                ("ПЕРЕНОС", "perenos", "perenos"),
                ("ВЫШЛО ЗА КОНТЕЙНЕР", "vyshli", "vyhod"),
                ("ЦЕНТР", "centr", "centr"),
                ("СКРОЛЛ", "skroll", "skroll"))
        nanesli = {imya: 0 for imya, _, _ in PROV}
        poymali = {imya: 0 for imya, _, _ in PROV}
        for _rol, _imya, _put, z, _osh in itogi:
            if not z:
                continue
            lom = z.get("lomka", {})
            for imya_pr, klyuch, klyuch_lom in PROV:
                if not lom.get(klyuch_lom):
                    continue
                nanesli[imya_pr] += 1
                nashli = z[klyuch] if klyuch != "skroll" else z["skroll"]
                if (len(nashli) if isinstance(nashli, list) else nashli):
                    poymali[imya_pr] += 1
        print()
        bеda = []
        for imya_pr, _, _ in PROV:
            n, p_ = nanesli[imya_pr], poymali[imya_pr]
            hvost = ""
            if n == 0:
                hvost = "   🔴 ПОЛОМКУ НЕ УДАЛОСЬ НАНЕСТИ НИ РАЗУ — проверка не испытана"
                bеda.append(f"{imya_pr}: нечем было сломать")
            elif p_ < n:
                hvost = f"   🔴 ПРОПУСТИЛА {n - p_}"
                bеda.append(f"{imya_pr}: пропустила {n - p_} из {n}")
            print(f"   САМОПРОВЕРКА · {imya_pr:<20} сломано на {n:>2} экранах, "
                  f"поймано на {p_:>2}{hvost}")
        ne_seli = [f"{rol}/{imya}" for rol, imya, _p, z, _o in itogi if z
                   and not all(z.get("lomka", {}).get(k) for _n, _kk, k in PROV)]
        if ne_seli:
            print("   ⚠ поломка села НЕ ЦЕЛИКОМ на экранах: " + ", ".join(ne_seli)
                  + " — там испытаны не все пять проверок, и общий красный это"
                    " скрывает.")
        if bеda:
            print("\n🔴 САМОПРОВЕРКА ПРОВАЛЕНА: " + "; ".join(bеda)
                  + ". Проверка, которая ничего не поймала на подстроенном "
                    "нарушении, не ловит и настоящее.")
            return 1
        print(f"\n✅ САМОПРОВЕРКА: каждая из пяти проверок поймала КАЖДУЮ "
              f"нанесённую ей поломку. Красных экранов {krasnyh} из {izmereno}.")
        return 0

    # 🔴 ОХВАТ ПЕЧАТАЕТСЯ РЯДОМ С ЧИСЛОМ НАХОДОК, ВСЕГДА И ОБОИМИ ИСХОДАМИ (Д4).
    # «Ноль находок» без охвата не отличить от «никто не звал»: этот гейт печатал
    # «обрезка 0» ровно тогда, когда не ходил на постоянное распределение, и был
    # формально прав. Число экранов, число ролей и число осмотренных узлов делают
    # зелёное проверяемым: зелёное на двух экранах и зелёное на семнадцати — разные
    # утверждения, и теперь их видно не читая исходник.
    roli = sorted({r for _, _, _, rr in ekrany_sayta for r in rr})
    # Замер лежит четвёртым в кортеже `(роль, экран, путь, замер, беда)`;
    # у экранов, упавших до замера, он `None` — их узлы не считаются, и это верно:
    # неосмотренный экран не должен раздувать охват.
    uzlov = sum((z or {}).get("osmotreno", 0) for _, _, _, z, _ in itogi)
    ohvat = (f"ОХВАТ: экранов {izmereno} из {dolzhno_byt} обещанных "
             f"(+{svedeno} сведено переадресацией) · маршрутов-страниц "
             f"{marshrutov} · ролей {len(roli)} ({', '.join(roli)}) · "
             f"осмотрено узлов {uzlov}")
    if krasnyh:
        print(f"\n🔴 КРАСНЫЙ: {krasnyh} экранов из {izmereno} нарушают канон.")
        print(f"   {ohvat}")
        return 1
    print(f"\n✅ ЗЕЛЁНЫЙ: {izmereno} экранов, все пять чисел нули на каждом.")
    print(f"   {ohvat}")
    return 0




# 🔴 ГОТОВЫЙ СПИСОК ДЛЯ ТЕХ, КТО ЗОВЁТ ЭТОТ МОДУЛЬ КАК БИБЛИОТЕКУ (тесты гейта
# параметризуются им на СБОРЕ, когда базы может не быть вовсе).  Пустой список
# здесь значит «источник не назван» и ничего больше: сам гейт этой переменной не
# пользуется — `main()` строит список заново и падает громко, если не смог.
def _ekrany_pri_importe() -> list:
    try:
        return sobrat_ekrany(zhivaya_baza())[0]
    except Exception:
        return []


EKRANY = _ekrany_pri_importe()


if __name__ == "__main__":
    raise SystemExit(main())
