# TOOL-CONTRACT: called-by-hand — замер прогона захода `kod_kabinet-plitki.md`,
# зовётся рукой и только рукой: точки вызова у него нет и быть не должно, он
# ходит в КОПИЮ боевой базы, которую снимают отдельно. Команда — в `## ОТЧЁТ`
# того же захода.
"""Живой прогон /kabinet по КОПИИ боевой базы. Только чтение, POST не делается."""
import json, os, re, sys, threading, urllib.parse, urllib.request
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer

os.environ.setdefault("SPETSMAT_VEB_SECRET", "progon-secret-key-32bytes!!")
KOPIYA = sys.argv[1]
os.environ["SPETSMAT_BAZA"] = KOPIYA

import veb.server as server
from veb import vhod
from veb.razdely.kabinet import (chetverti_goda, otkrytaya_chetvert, segodnya,
                                 zanyatiya_mezhdu)
from core.services.istoria_poseshchenij import zanyatie_zaversheno

TEACHER = int(sys.argv[2])

httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
httpd.db_path = KOPIYA
port = httpd.server_address[1]
threading.Thread(target=httpd.serve_forever, daemon=True).start()

kuka = "%s=%s" % (vhod.COOKIE_NAME, vhod._make_cookie("prepod", TEACHER))
req = urllib.request.Request("http://127.0.0.1:%d/kabinet" % port, headers={"Cookie": kuka})
import time
t0 = time.time()
with urllib.request.urlopen(req) as r:
    telo = r.read().decode("utf-8")
    status = r.status
sekund = time.time() - t0

def bez(t):
    t = re.sub(r"<style\b.*?</style>", "", t, flags=re.S)
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    return re.sub(r"/\*.*?\*/", "", t, flags=re.S)

vidimoe = bez(telo)
god = chetverti_goda(segodnya())
otkryta = otkrytaya_chetvert(segodnya(), god)
seichas = datetime.now(timezone.utc)

# тело открытой четверти
granicy = [(n, telo.index('<div class="kab-tablica" id="kab-ch-%d">' % n)) for n, _o, _d in god]
granicy.append((None, telo.index('<p class="kab-beda"')))
tela = {granicy[i][0]: telo[granicy[i][1]:granicy[i+1][1]] for i in range(len(granicy)-1)}

print("СТАТУС                          :", status)
print("ВРЕМЯ СБОРКИ СТРАНИЦЫ, с        : %.2f" % sekund)
print("РАЗМЕР, байт                    :", len(telo.encode()))
print("СЕГОДНЯ                         :", segodnya(), "· открыта четверть", otkryta)
print()
for n, ot, do in god:
    dni = zanyatiya_mezhdu(ot, do)
    svoi = tela[n]
    est = sum(1 for d in dni if 'data-den="%s"' % d in svoi)
    print("четверть %d (%s … %s): занятий %2d, плиток на экране %2d %s"
          % (n, ot, do, len(dni), est, "✅" if est == len(dni) else "❌"))
print()
dni_otkrytoj = zanyatiya_mezhdu(*[ (o,d) for n,o,d in god if n==otkryta ][0])
svoi = tela[otkryta]
print("ПЛИТОК В ОТКРЫТОЙ ЧЕТВЕРТИ      : %d из %d"
      % (sum(1 for d in dni_otkrytoj if 'data-den="%s"' % d in svoi), len(dni_otkrytoj)))
print("КОЛОНОК (из таблицы стилей)     :",
      re.search(r"\.kab-tablica\{columns:(\d)", telo).group(1))
print("СВЁРНУТЫ ВСЕ ПЛИТКИ             :",
      "✅ да" if "<details open" not in telo and 'kab-zanyatie" open' not in telo else "❌")
print("СВОДНАЯ ФРАЗА «2 из 3»          :",
      "✅ нет" if "с начала года: занятий с вашими школьниками" not in telo else "❌ ЕСТЬ")
print("СЛОВО «сдач» НА ЭКРАНЕ          :",
      "✅ 0" if "сдач" not in vidimoe else "❌ %d" % vidimoe.count("сдач"))
print("ГЕНДЕРНЫЕ ГЛАГОЛЫ НА ЭКРАНЕ     :",
      "✅ 0" if not any(g in vidimoe for g in ("сдал", "сдала", "принял", "приняла"))
      else "❌ есть")

# будущие плитки со списком школьников
budushchie = re.findall(r'<div class="kab-zanyatie vperyod[^"]*" data-den="([^"]*)">(.*?)</label></div>',
                        telo, re.S)
s_spiskom = [d for d, p in budushchie if "kab-spisok" in p]
print("БУДУЩИХ ПЛИТОК                  :", len(budushchie),
      "· из них со списком школьников:", len(s_spiskom),
      "✅" if not s_spiskom else "❌")
print("КНОПОК «Кондуит за занятие»     :", telo.count('class="kab-konduit"'))

blok = re.search(r'<script type="application/json" id="kab-dannye">(.*?)</script>', telo, re.S)
dannye = json.loads(blok.group(1))
proshlo = [d for d in dni_otkrytoj if zanyatie_zaversheno(d, seichas=seichas)]
print("ЗАВЕРШИВШИХСЯ ЗАНЯТИЙ ЧЕТВЕРТИ  :", len(proshlo))
print()
print("── РАЗВЁРНУТО ТРИ ПРОШЕДШИЕ ПЛИТКИ (формат кондуита, пункт 8) ──")
for den in proshlo[-3:]:
    d = dannye.get(den)
    print("  %s · кнопка кондуита: %s · школьников %d"
          % (den,
             "есть" if ('data-den="%s">Кондуит за занятие' % den) in telo else "НЕТ",
             len(d["deti"]) if d else 0))
    for r in (d["deti"] if d else []):
        po_listkam = {}
        poryadok = []
        for z in r["sdal"]:
            if z["listok"] not in po_listkam:
                po_listkam[z["listok"]] = []
                poryadok.append(z["listok"])
            po_listkam[z["listok"]].append(z["zadacha"])
        if poryadok:
            print("      %-28s %s" % (r["kto"], " | ".join(
                "[%s] %s" % (l, " ".join(po_listkam[l])) for l in poryadok)))
# адреса листков отвечают?
listki = sorted({z["listok"] for k, v in dannye.items() if "|" in k for z in v["sdal"]})
print()
print("ЛИСТКОВ В КОНДУИТЕ              :", len(listki), listki[:10])
for nom in listki[:10]:
    a = "http://127.0.0.1:%d/listki/%s" % (port, urllib.parse.quote(nom))
    try:
        with urllib.request.urlopen(a) as rr:
            print("   /listki/%-6s → %s" % (nom, rr.status))
    except Exception as ex:
        print("   /listki/%-6s → %s" % (nom, ex))
httpd.shutdown()
