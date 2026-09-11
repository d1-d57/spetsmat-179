"""Замер /kabinet В БРАУЗЕРЕ, ролью `prepod`, на эталоне 1440x900.

Гейт вёрстки эту роль не меряет вовсе (он сам это и печатает в списке «не
проверяется»), а весь пункт 5 рецензии — про то, помещается ли четверть на экран.
Поэтому измеряется здесь и прямо: горизонтальная прокрутка, число колонок, число
плиток, и раскрытие трёх прошедших до самого кондуита.
"""
import json, os, sys, threading, urllib.request
from http.server import ThreadingHTTPServer

os.environ.setdefault("SPETSMAT_VEB_SECRET", "brauzer-secret-key-32bytes!")
KOPIYA, TEACHER = sys.argv[1], int(sys.argv[2])
os.environ["SPETSMAT_BAZA"] = KOPIYA
import veb.server as server
from veb import vhod

httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
httpd.db_path = KOPIYA
port = httpd.server_address[1]
threading.Thread(target=httpd.serve_forever, daemon=True).start()
kuka = vhod._make_cookie("prepod", TEACHER)

from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    br = pw.chromium.launch()
    ctx = br.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_cookies([{"name": vhod.COOKIE_NAME, "value": kuka,
                      "domain": "127.0.0.1", "path": "/"}])
    p = ctx.new_page()
    p.goto("http://127.0.0.1:%d/kabinet" % port, wait_until="networkidle")

    m = p.evaluate("""() => {
      const d = document.documentElement;
      const otkryt = document.querySelector('.kab-tablica:not([style*="none"])');
      const vidnoe = [...document.querySelectorAll('.kab-tablica')]
        .find(t => t.offsetParent !== null);
      const plitki = vidnoe ? [...vidnoe.children] : [];
      const kolonki = vidnoe ? getComputedStyle(vidnoe).columnCount : null;
      const shirina = d.clientWidth;
      return {
        scrollW: d.scrollWidth, clientW: shirina,
        gorizont: d.scrollWidth > d.clientWidth,
        kolonki: kolonki,
        plitok_vidno: plitki.length,
        plitok_za_ekranom: plitki.filter(x => {
          const r = x.getBoundingClientRect();
          return r.right > shirina + 1 || r.left < -1;
        }).length,
        nizhe_ekrana: plitki.filter(x => x.getBoundingClientRect().bottom > 900).length,
        vsego_details: document.querySelectorAll('details.kab-zanyatie').length,
        raskrytyh_srazu: document.querySelectorAll('details.kab-zanyatie[open]').length,
        vkladok: document.querySelectorAll('.kab-vkladki label').length,
        spisok_v_budushchem: [...document.querySelectorAll('.kab-zanyatie.vperyod')]
          .filter(x => x.querySelector('.kab-spisok')).length,
      };
    }""")
    print("── ЭКРАН 1440×900, роль prepod, преподаватель %d ──" % TEACHER)
    for k, v in m.items():
        print("   %-22s %s" % (k, v))

    # вкладки переключаются
    p.click('.kab-vkladki label[for="kab-p-4"]')
    v4 = p.evaluate("""() => {
      const t = document.querySelector('#kab-ch-4');
      return {vidna: t.offsetParent !== null, plitok: t.children.length,
              pervaya_skryta: document.querySelector('#kab-ch-1').offsetParent === null};
    }""")
    print("   переключение на 4 четверть:", v4)
    p.click('.kab-vkladki label[for="kab-p-1"]')

    # три прошедшие раскрываются, кондуит выводится кнопкой
    dets = p.query_selector_all("details.kab-zanyatie")
    print()
    print("── РАЗВЁРНУТО %d ПРОШЕДШИХ ПЛИТКИ ──" % len(dets))
    for i, d in enumerate(dets):
        d.query_selector("summary").click()
        p.wait_for_timeout(60)
        knopka = d.query_selector(".kab-konduit")
        den = d.get_attribute("data-den")
        print("  %s · раскрылась: %s · кнопка «Кондуит за занятие»: %s"
              % (den, d.get_attribute("open") is not None, knopka is not None))
        knopka.click()
        p.wait_for_timeout(80)
        vid = p.evaluate("""() => {
          const pa = document.getElementById('kab-raskrytie');
          if (pa.hidden) return null;
          return {
            zag: document.getElementById('kab-raskrytie-zag').textContent,
            stroki: [...pa.querySelectorAll('.kab-stroka-listka')].map(s => ({
              listok: s.querySelector('.kab-listok-knopka').textContent,
              adres: s.querySelector('.kab-listok-knopka').getAttribute('href'),
              zadachi: [...s.querySelectorAll('.kab-zadacha')].map(z => z.textContent),
            })),
            imena: [...pa.querySelectorAll('.kab-konduit-imya')].map(x => x.textContent),
            slovo_zadacha: pa.textContent.includes('задача'),
            gorizont_v_paneli: pa.scrollWidth > pa.clientWidth,
          };
        }""")
        print("      панель:", json.dumps(vid, ensure_ascii=False))
    p.screenshot(path=sys.argv[3], full_page=False)
    print()
    print("СКРИНШОТ:", sys.argv[3])
    br.close()
httpd.shutdown()
