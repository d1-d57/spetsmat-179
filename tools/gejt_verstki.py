"""Layout gate: judges the RENDER of a page, not the lines of its CSS.

Why this file exists.  The column rule of this project was written down three times
and did not hold three times, because it had no lever: nothing turned red when a
page broke it.  A rule without a carrier is a hope (`skills/disciplina-kachestvo`).
This gate is the carrier.  It boots the real server on the real database, opens
every page in a headless Chromium at the reference viewport and asks three
questions that a human asks by looking:

  1. CLIPPING      -- is there an element whose visible box is narrower than its
                      own text needs, so the text is cut?
  2. NEEDLESS WRAP -- is there a line that took two line-heights where the
                      available width allowed one?
  3. H-SCROLL      -- is the document wider than the window?

All three zero on every page -- green.  Anything else -- red, with the offending
selectors printed, because a gate that says only "red" gets ignored.

🔴 WHAT THIS GATE DOES NOT CHECK, stated out loud so nobody mistakes green here
for "the page is good": colour and contrast, readability, font substitution on a
machine without the project fonts, mobile widths, print, motion, and anything a
screen reader would say.  It judges geometry at one viewport and nothing else.

Run:  python3 tools/gejt_verstki.py            (green -> rc=0, red -> rc=1)
      python3 tools/gejt_verstki.py --slomat   (self-test: forces a violation,
                                                the gate MUST go red; rc=0 when
                                                it correctly caught it)
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

# One entry per page the gate judges.  `vkladka` is the id of the tab radio to
# select before measuring; None means the page has no tabs.  The names are the
# owner's own words for these screens.
STRANICY = [
    ("школьникам",      "/raspredelenie", None),
    ("принимающим",     "/raspredelenie", "p-rasp"),
    ("страница группы", "/glavnaya",      "p-start"),
    ("кондуит",         "/glavnaya",      "p-kond"),
]

# The measuring script.  It runs inside the page, so it sees the RENDER: computed
# boxes after CSS, fonts and layout, not the source.
ZAMER = r"""
() => {
  const out = {obrezka: [], perenos: [], skroll: 0, osmotreno: 0};

  out.skroll = Math.max(0,
      document.documentElement.scrollWidth - document.documentElement.clientWidth);

  const vidim = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return false;
    const s = getComputedStyle(el);
    return s.display !== 'none' && s.visibility !== 'hidden' && s.opacity !== '0';
  };

  // Only LEAF elements carrying their own text: a container is wide because its
  // children are, and blaming it would bury the real offender.
  const list = [...document.querySelectorAll('body *')].filter(el => {
    if (!vidim(el)) return false;
    if (['SCRIPT','STYLE','SVG','PATH','BR','INPUT'].includes(el.tagName)) return false;
    const t = (el.textContent || '').trim();
    if (!t) return false;
    return ![...el.children].some(c => (c.textContent || '').trim().length > 0);
  });

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

  for (const el of list) {
    out.osmotreno++;
    const s = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    const tekst = (el.textContent || '').trim().slice(0, 40);

    // 1. CLIPPING -- the content box cannot hold the text it carries.
    // scrollWidth exceeding clientWidth means the browser had to hide part of it.
    if (el.scrollWidth > el.clientWidth + 1 && s.overflowX !== 'visible') {
      out.obrezka.push({put: put(el), tekst,
                        nado: el.scrollWidth, est: el.clientWidth});
    }

    // 2. NEEDLESS WRAP -- rendered on two or more lines while one would fit.
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
  return out;
}
"""


def zhivaya_baza() -> Path:
    """The real project database -- 54 active pupils, not three invented rows."""
    p = KOREN / "data" / "spetsmat.db"
    if not p.exists():
        raise SystemExit(f"нет живой базы: {p}")
    return p


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
    measuring the page as a guest would silently check an empty screen."""
    from veb import vhod
    return {"name": vhod.COOKIE_NAME, "value": vhod._make_cookie("organizator")}


def progon(baza_url: str, slomat: bool) -> tuple[list, int, int]:
    from playwright.sync_api import sync_playwright

    itogi, osmotreno_vsego = [], 0
    with sync_playwright() as pw:
        brauzer = pw.chromium.launch()
        ctx = brauzer.new_context(viewport=ETALON)
        c = kuka()
        ctx.add_cookies([{**c, "url": baza_url}])
        page = ctx.new_page()

        for imya, put, vkladka in STRANICY:
            try:
                page.goto(baza_url + put, wait_until="networkidle", timeout=20000)
                if vkladka:
                    el = page.query_selector(f"#{vkladka}")
                    if el:
                        page.evaluate(f"document.getElementById('{vkladka}').checked = true")
                        page.wait_for_timeout(150)
                if slomat:
                    # Deliberate breakage for the self-test: right-align every cell
                    # and squeeze one column.  A gate that stays green here is a
                    # gate nobody needs.
                    page.evaluate("""() => {
                        document.querySelectorAll('td, th, .kl, li').forEach(e => {
                            e.style.textAlign = 'right';
                        });
                        const c = document.querySelector('td, li, .kl');
                        if (c) { c.style.width = '8px'; c.style.overflow = 'hidden'; }
                        const b = document.body;
                        const d = document.createElement('div');
                        d.style.width = '2400px'; d.style.height = '1px';
                        b.appendChild(d);
                    }""")
                    page.wait_for_timeout(120)
                z = page.evaluate(ZAMER)
            except Exception as exc:                       # noqa: BLE001
                itogi.append((imya, put, None, str(exc)[:120]))
                continue
            osmotreno_vsego += z["osmotreno"]
            itogi.append((imya, put, z, None))

        brauzer.close()
    return itogi, len(STRANICY), osmotreno_vsego


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slomat", action="store_true",
                    help="self-test: break the pages on purpose; the gate MUST go red")
    args = ap.parse_args()

    db = zhivaya_baza()
    chisla = chisla_bazy(db)
    httpd, conn, t, url = podnyat_server(db)
    try:
        itogi, vsego_stranic, osmotreno = progon(url, args.slomat)
    finally:
        httpd.shutdown(); httpd.server_close(); t.join(); conn.close()

    print(f"ГЕЙТ ВЁРСТКИ · эталон {ETALON['width']}x{ETALON['height']} · "
          f"живая база: {chisla['vsego']} школьников, "
          f"по классам {chisla['po_klassam']}, крупнейший класс {chisla['krupneyshiy']}")
    print()
    print(f"{'страница':<18}{'обрезка':>9}{'переносы':>10}{'скролл, px':>12}   осмотрено")
    krasnyh, izmereno = 0, 0
    for imya, put, z, oshibka in itogi:
        if z is None:
            print(f"{imya:<18}{'—':>9}{'—':>10}{'—':>12}   🔴 {oshibka}")
            krasnyh += 1
            continue
        izmereno += 1
        plohо = len(z["obrezka"]) + len(z["perenos"]) + (1 if z["skroll"] else 0)
        if plohо:
            krasnyh += 1
        print(f"{imya:<18}{len(z['obrezka']):>9}{len(z['perenos']):>10}"
              f"{z['skroll']:>12}   {z['osmotreno']}")

    print()
    print(f"ОХВАТ: проверено {izmereno} страниц из {vsego_stranic}; "
          f"осмотрено элементов {osmotreno}")
    if izmereno == 0:
        print("🔴 ОХВАТ НОЛЬ при живом сервере — это КРАСНЫЙ, а не зелёный: "
              "гейт ничего не измерил.")
        return 1

    for imya, put, z, oshibka in itogi:
        if not z:
            continue
        for vid, klyuch in (("ОБРЕЗКА", "obrezka"), ("ПЕРЕНОС", "perenos")):
            for d in z[klyuch][:8]:
                print(f"   {vid} · {imya} · {d['put']} · «{d['tekst']}» · "
                      f"надо {d.get('nado', d.get('nuzhno'))} есть {d['est']}")

    print()
    print("НЕ ПРОВЕРЯЕТСЯ ЭТИМ ГЕЙТОМ: цвет и контраст, читаемость, подстановка "
          "шрифтов на машине без проектных шрифтов, мобильные ширины, печать, "
          "движение, озвучка экранным диктором. Гейт судит ГЕОМЕТРИЮ на одном "
          "эталоне и больше ничего.\n🔴 И ОТДЕЛЬНО: обрезку, сделанную НА "
          "СЕРВЕРЕ (строка укорочена в Python до отдачи в браузер), этот гейт "
          "увидеть не может в принципе — в разметку приезжает уже короткий "
          "текст, и переполнения нет. Он ловит обрезку РАМКОЙ, а не ножницами "
          "в коде.")

    if args.slomat:
        if krasnyh:
            print("\n✅ САМОПРОВЕРКА: гейт покраснел на подстроенном нарушении — "
                  "рычаг работает.")
            return 0
        print("\n🔴 САМОПРОВЕРКА ПРОВАЛЕНА: страницы сломаны нарочно, а гейт зелёный. "
              "Молчащий гейт хуже отсутствующего.")
        return 1

    if krasnyh:
        print(f"\n🔴 КРАСНЫЙ: {krasnyh} страниц(ы) из {vsego_stranic} нарушают канон.")
        return 1
    print(f"\n✅ ЗЕЛЁНЫЙ: {izmereno} страниц из {vsego_stranic}, все три числа нули.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
