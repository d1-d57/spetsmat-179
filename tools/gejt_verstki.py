#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-hand — run before publishing a layout change, and by
# the acceptance of any заход that touched `veb/**`.
"""Layout gate: judges the RENDER of a page, not the lines of its CSS.

Why this file exists.  The column rule of this project was written down three times
and did not hold three times, because it had no lever: nothing turned red when a
page broke it.  A rule without a carrier is a hope (`skills/disciplina-kachestvo`).
This gate is the carrier.  It boots the real server on the real database, opens
every screen in a headless Chromium at the reference viewport, in every role that
can see it, and asks four questions that a human asks by looking:

  1. CLIPPING      -- is there an element whose visible box is narrower than its
                      own text needs, so the text is cut?
  2. NEEDLESS WRAP -- is there a line that took two line-heights where the
                      available width allowed one?
  3. H-SCROLL      -- is the document wider than the window?
  4. ESCAPED       -- is there an element standing OUTSIDE the card that owns it,
                      where nothing clips it and no scrollbar reveals it?

All four zero on every screen -- green.  Anything else -- red, with the offending
selectors printed, because a gate that says only "red" gets ignored.

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
                                                EVERY one of the four checks; the
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

# 🔴 THE RENDER IGNORES THE CONNECTION THIS GATE HANDS THE SERVER.  Every page
# route rebuilds its context through `veb.obshchee.karkas.DATA`, a module-level
# constant pointing at `<repo>/data/spetsmat.db`.  So the base the gate judges is
# ALWAYS the one checked out next to it -- there is no honest way to aim the gate
# elsewhere, and pretending otherwise with a `--baza` flag would be a third way to
# lie.  Stated here so nobody spends an hour finding it again.
BAZA = KOREN / "data" / "spetsmat.db"

# One entry per SCREEN the gate judges: name, path, the radio to select before
# measuring, and the roles that can see it.
#   `name="str"` radios switch the SITE SECTION: p-start · p-rasp · p-lich · p-kond
#   `name="vk"`  radios switch the TAB inside распределение: t-shk · t-prep · t-В/Д/Н
# `None` means the screen is whatever the page shows on arrival.
OBE = ("гость", "организатор")
EKRANY = [
    ("школьникам",   "/raspredelenie", "t-shk",   OBE),
    ("принимающим",  "/raspredelenie", "t-prep",  OBE),
    ("группа В",     "/raspredelenie", "t-В",     OBE),
    ("группа Д",     "/raspredelenie", "t-Д",     OBE),
    ("группа Н",     "/raspredelenie", "t-Н",     OBE),
    ("класс",        "/glavnaya",      "p-start", OBE),
    ("кондуит",      "/glavnaya",      "p-kond",  ("организатор",)),
]

# The measuring script.  It runs inside the page, so it sees the RENDER: computed
# boxes after CSS, fonts and layout, not the source.
ZAMER = r"""
() => {
  const out = {obrezka: [], perenos: [], vyshli: [], skroll: 0,
               osmotreno: 0, vsego: 0, na_obrezku: 0, na_vyhod: 0};

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
  const organ = (el) => ['SELECT','OPTION','TEXTAREA','INPUT','BUTTON'].includes(el.tagName)
      || !!el.querySelector('select, textarea, input, button');

  // Text with the content of <style>/<script>/<option> subtracted, so a report
  // quotes what a reader sees and not a stylesheet.
  const chistyy = (el) => {
    const k = el.cloneNode(true);
    k.querySelectorAll('style, script, option').forEach(n => n.remove());
    return (k.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40);
  };

  const vnutri = (el) => {                    // padding box
    const r = el.getBoundingClientRect(), s = getComputedStyle(el);
    return {l: r.left + parseFloat(s.borderLeftWidth),
            r: r.right - parseFloat(s.borderRightWidth)};
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
    // scrollWidth exceeding clientWidth says the box is too small for SOMETHING.
    if (!(el.scrollWidth > el.clientWidth + 1 && s.overflowX !== 'visible')) continue;
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
    const d = document.createRange();
    d.selectNodeContents(el);
    const rects = [...d.getClientRects()].filter(r => r.width > 0 && r.height > 0);
    if (!rects.length) continue;
    const vylez = Math.max(...rects.map(r => Math.max(r.right - b.r, b.l - r.left)));
    if (vylez <= 1) continue;
    out.obrezka.push({put: put(el), tekst: chistyy(el),
                      nado: el.scrollWidth, est: el.clientWidth});
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
    const diapazon = document.createRange();
    diapazon.selectNodeContents(el);
    const verhi = new Set([...diapazon.getClientRects()]
        .filter(b => b.width > 0 && b.height > 0)
        .map(b => Math.round(b.top)));
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
      const d2 = document.createRange();
      d2.selectNodeContents(el);
      const rr = [...d2.getClientRects()].filter(b => b.width > 0);
      const nuzhno = rr.length ? Math.max(...rr.map(b => b.width)) : 0;
      el.style.whiteSpace = bylo;
      if (nuzhno <= el.clientWidth + 1) {
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
    if (rod.tip === 'клип') continue;   // hidden overflow is check 1's business
    const a = el.getBoundingClientRect(), b = vnutri(rod.el);
    const vlevo = Math.round(b.l - a.left), vpravo = Math.round(a.right - b.r);
    if (vlevo > 1 || vpravo > 1) {
      out.vyshli.push({put: put(el), rod: put(rod.el), tip: rod.tip,
                       vlevo, vpravo, tekst: chistyy(el)});
    }
  }

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

  // 1. CLIPPING -- squeeze a text box shut.  Deliberately a NON-LEAF node
  //    (`.kto` wraps a `<b>`), the exact shape the walk used to drop: if it ever
  //    regresses to leaves only, this stays green and the self-test says so.
  const k = iz('.kto')[0] || iz('td, li, .para')[0];
  if (k) { k.style.width = '8px'; k.style.minWidth = '8px'; k.style.flex = '0 0 8px';
           k.style.overflow = 'hidden'; k.style.whiteSpace = 'nowrap';
           k.style.textOverflow = 'ellipsis'; }

  // 2. NEEDLESS WRAP -- a break where the width did not require one.  The break
  //    is forced with a `<br>` rather than by squeezing the box, and that is on
  //    purpose: squeezing and then widening the box back cannot work, because
  //    CSS re-lays out the moment the width changes and the wrap disappears with
  //    it (tried live 10.09 — the self-test reported «ПЕРЕНОС поймано 0» and was
  //    right to).  A `<br>` reproduces the DEFINITION the check judges by — two
  //    line boxes where one line of text fitted the width the element HAS — and
  //    does not depend on which CSS route produced it in the wild.
  const w = iz('span, td, li, div').find(e => e !== k &&
      ![...e.children].some(c => (c.textContent || '').trim()) &&
      (e.textContent || '').trim().split(/\s+/).length >= 2 &&
      e.scrollWidth <= e.clientWidth + 1);
  if (w) { const slova = w.textContent.trim().split(/\s+/);
           w.textContent = '';
           w.append(document.createTextNode(slova.slice(0, -1).join(' ')),
                    document.createElement('br'),
                    document.createTextNode(slova[slova.length - 1])); }

  // 4. ESCAPED -- pills walk out of the LEFT edge of the card that owns them,
  //    exactly as in the owner's screenshot `13`, and the document does NOT
  //    scroll on that account, so checks 1-3 stay blind to it.
  const cel = iz('.kol-pr .para').length ? iz('.kol-pr .para') : iz('.para');
  cel.forEach(pa => {
      pa.style.background = 'rgba(255,255,255,.06)';
      pa.style.borderRadius = '8px';
      const deti = pa.querySelectorAll('.deti-ryad span, .komu.deti span, .komu');
      (deti.length ? deti : pa.children).forEach(x => {
          x.style.marginLeft = '-120px'; });
  });

  // 3. H-SCROLL -- push the document wider than the window.
  const d = document.createElement('div');
  d.style.width = '2400px'; d.style.height = '1px';
  document.body.appendChild(d);
}"""


def zhivaya_baza() -> Path:
    """The real project database -- every active pupil, not three invented rows."""
    if not BAZA.exists():
        raise SystemExit(f"нет живой базы: {BAZA}")
    return BAZA


def chisla_bazy(db: Path) -> dict:
    """Group sizes read from the live base.  Never hard-code 25 or 27 here:
    the number the gate must survive is whatever the school actually has today."""
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
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


def progon(baza_url: str, slomat: bool, otbor: str | None) -> tuple[list, int]:
    from playwright.sync_api import sync_playwright

    ekrany = [e for e in EKRANY if not otbor or otbor.lower() in e[0].lower()]
    itogi = []
    with sync_playwright() as pw:
        brauzer = pw.chromium.launch()
        for rol in ("гость", "организатор"):
            svoi = [e for e in ekrany if rol in e[3]]
            if not svoi:
                continue
            ctx = brauzer.new_context(viewport=ETALON)
            if rol == "организатор":
                ctx.add_cookies([{**kuka(), "url": baza_url}])
            page = ctx.new_page()
            for imya, put, radio, _roli in svoi:
                try:
                    page.goto(baza_url + put, wait_until="networkidle", timeout=20000)
                    if radio:
                        if not page.query_selector("#" + radio):
                            itogi.append((rol, imya, put, None,
                                          f"переключателя #{radio} нет на странице"))
                            continue
                        page.evaluate("(i)=>document.getElementById(i).checked=true", radio)
                        page.wait_for_timeout(200)
                    if slomat:
                        page.evaluate(LOMKA)
                        page.wait_for_timeout(150)
                    z = page.evaluate(ZAMER)
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

    db = zhivaya_baza()
    chisla = chisla_bazy(db)
    httpd, conn, t, url = podnyat_server(db)
    try:
        itogi, dolzhno_byt = progon(url, args.slomat, args.ekran)
    finally:
        httpd.shutdown(); httpd.server_close(); t.join(); conn.close()

    print(f"ГЕЙТ ВЁРСТКИ · эталон {ETALON['width']}x{ETALON['height']} · "
          f"живая база: {chisla['vsego']} школьников, "
          f"по классам {chisla['po_klassam']}, крупнейший класс {chisla['krupneyshiy']}")
    print(f"база: {db}")
    print()
    print(f"{'роль':<13}{'экран':<15}{'обрезка':>9}{'переносы':>10}"
          f"{'вышли':>8}{'скролл':>8}   охват узлов")
    krasnyh, izmereno, uzlov = 0, 0, 0
    for rol, imya, put, z, oshibka in itogi:
        if z is None:
            print(f"{rol:<13}{imya:<15}{'—':>9}{'—':>10}{'—':>8}{'—':>8}   🔴 {oshibka}")
            krasnyh += 1
            continue
        izmereno += 1
        uzlov += z["vsego"]
        ploho = (len(z["obrezka"]) + len(z["perenos"]) + len(z["vyshli"])
                 + (1 if z["skroll"] else 0))
        if ploho:
            krasnyh += 1
        # 🔴 ZERO NODES ON A LIVE SCREEN IS RED, NOT GREEN.  A walk that looked at
        # nothing reports no defects, and that is indistinguishable from a clean
        # page unless the coverage is printed next to the verdict.
        if z["vsego"] == 0 or z["na_obrezku"] == 0:
            krasnyh += 1
            print(f"{rol:<13}{imya:<15}{'—':>9}{'—':>10}{'—':>8}{'—':>8}   "
                  f"🔴 ОХВАТ НОЛЬ: узлов {z['vsego']}, на обрезку {z['na_obrezku']}")
            continue
        print(f"{rol:<13}{imya:<15}{len(z['obrezka']):>9}{len(z['perenos']):>10}"
              f"{len(z['vyshli']):>8}{z['skroll']:>8}   "
              f"проверено {z['na_obrezku']}/{z['osmotreno']}/{z['na_vyhod']} "
              f"из {z['vsego']}")

    print()
    print(f"ОХВАТ: проверено {izmereno} экранов из {dolzhno_byt}; "
          f"осмотрено элементов {uzlov}")
    print("        три числа в колонке охвата — узлов на ОБРЕЗКУ / на ПЕРЕНОС / "
          "на ВЫХОД ЗА КОНТЕЙНЕР, из общего числа элементов страницы.")
    if izmereno == 0:
        print("🔴 ОХВАТ НОЛЬ при живом сервере — это КРАСНЫЙ, а не зелёный: "
              "гейт ничего не измерил.")
        return 1

    for rol, imya, put, z, oshibka in itogi:
        if not z:
            continue
        for vid, klyuch in (("ОБРЕЗКА", "obrezka"), ("ПЕРЕНОС", "perenos")):
            for d in z[klyuch][:8]:
                print(f"   {vid} · {rol} · {imya} · {d['put']} · «{d['tekst']}» · "
                      f"надо {d.get('nado', d.get('nuzhno'))} есть {d['est']}")
        for d in z["vyshli"][:8]:
            print(f"   ВЫШЛО · {rol} · {imya} · {d['put']} · «{d['tekst']}» · "
                  f"влево {d['vlevo']} вправо {d['vpravo']} · "
                  f"из {d['rod']} ({d['tip']})")

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
          "списки, окно входа, подсказка значка «обычно у». Гейт меряет покой.")

    if args.slomat:
        # 🔴 «КРАСНЫЙ» ЕЩЁ НЕ ЗНАЧИТ «ВСЕ ЧЕТЫРЕ РАБОТАЮТ». Сломано четыре вещи, и
        # проверок четыре: если краснеет только горизонтальный скролл, а три
        # остальные молчат, общий красный это скрывает — ровно тем способом, каким
        # гейт врал до 10.09. Поэтому самопроверка судит КАЖДУЮ проверку отдельно.
        srabotalo = {"ОБРЕЗКА": 0, "ПЕРЕНОС": 0, "ВЫШЛО ЗА КОНТЕЙНЕР": 0,
                     "СКРОЛЛ": 0}
        for _rol, _imya, _put, z, _osh in itogi:
            if not z:
                continue
            srabotalo["ОБРЕЗКА"] += len(z["obrezka"])
            srabotalo["ПЕРЕНОС"] += len(z["perenos"])
            srabotalo["ВЫШЛО ЗА КОНТЕЙНЕР"] += len(z["vyshli"])
            srabotalo["СКРОЛЛ"] += 1 if z["skroll"] else 0
        print()
        for imya_pr, n in srabotalo.items():
            print(f"   САМОПРОВЕРКА · {imya_pr:<20} поймано {n}"
                  + ("" if n else "   🔴 НИ ОДНОГО"))
        molchat = [k for k, n in srabotalo.items() if not n]
        if molchat:
            print("\n🔴 САМОПРОВЕРКА ПРОВАЛЕНА: сломаны все четыре вещи, а молчат "
                  + ", ".join(molchat) + ". Проверка, которая ничего не поймала на "
                  "подстроенном нарушении, не ловит и настоящее.")
            return 1
        print(f"\n✅ САМОПРОВЕРКА: покраснели все четыре проверки, "
              f"{krasnyh} экранов из {izmereno}. Рычаг работает.")
        return 0

    if krasnyh:
        print(f"\n🔴 КРАСНЫЙ: {krasnyh} экранов из {izmereno} нарушают канон "
              f"(измерено {izmereno} из {dolzhno_byt} обещанных).")
        return 1
    print(f"\n✅ ЗЕЛЁНЫЙ: {izmereno} экранов, все четыре числа нули на каждом.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
