#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-hand — зовётся при выкладке статики на GitHub Pages.
"""Собирает САМОДОСТАТОЧНУЮ статику по ТЗ 07_TZ-SAJT.md.

Три страницы, меню из трёх пунктов строкой сверху (§1: «может быть, наверху, чтобы
ничего не выезжало»). Текст занимает весь экран.

Данные вмораживаются на момент сборки: Pages отдаёт статику, ей не нужен ни сервер,
ни база, и чтение переживает выключенный ноутбук — в этом смысл разделения (§7).
"""
import html
import pathlib
import sqlite3
import sys

KOREN = pathlib.Path(__file__).resolve().parent.parent
DATA = KOREN / "data" / "spetsmat.db"
VYHOD = KOREN / "docs" / "index.html"
MAT = KOREN.parent / "materials" / "spetsmat-2026"
DATA_NA = "2026-09-05"
DATA_SLOVAMI = "5 сентября"


def e(s):
    return html.escape(str(s if s is not None else ""))


def sobrat():
    c = sqlite3.connect(DATA)
    c.row_factory = sqlite3.Row

    kabinety = {r["gruppa"]: r["kabinet"] for r in c.execute(
        "select gruppa, kabinet from kabinet_na_den where data = ?", (DATA_NA,))}
    gruppy = {r["kod"]: r["starshij"] for r in c.execute(
        "select kod, starshij from gruppy order by kod")}
    prep = {r["id"]: dict(r) for r in c.execute(
        "select id, name, gruppa from teachers where aktiven = 1")}

    shk = c.execute("""
        select s.id, s.surname, s.name, s.class, e.teacher_id
        from students s
        left join enrollment e
          on e.student_id = s.id and e.valid_to = '9999-12-31' and e.slot = 1
        where s.status is null or s.status <> 'left'
        order by s.surname, s.name
    """).fetchall()

    def gr_shk(r):
        t = prep.get(r["teacher_id"])
        return t["gruppa"] if t else None

    def kab_shk(r):
        return kabinety.get(gr_shk(r))

    # ── строки таблиц ────────────────────────────────────────────────────────
    def stroka_shk(r):
        t = prep.get(r["teacher_id"])
        g = gr_shk(r)
        return (f'<tr><td><b>{e(r["surname"])}</b> {e(r["name"])} '
                f'<span class="kl">{e(r["class"])}</span></td>'
                f'<td>{f"<span class=gr>{e(g)}</span>" if g else "<span class=net>—</span>"}</td>'
                f'<td>{e(t["name"]) if t else "<span class=net>ждёт назначения</span>"}</td>'
                f'<td>{f"<span class=kab>{e(kab_shk(r))}</span>" if kab_shk(r) else "<span class=net>—</span>"}</td></tr>')

    def stroka_prep(t):
        deti = sorted(f'{r["surname"]} {r["name"]}' for r in shk if r["teacher_id"] == t["id"])
        kab = kabinety.get(t["gruppa"])
        return (f'<tr><td class="pr"><b>{e(t["name"])}</b></td>'
                f'<td><span class="gr">{e(t["gruppa"])}</span></td>'
                f'<td class="deti">{e(", ".join(deti)) or "<span class=net>никого</span>"}</td>'
                f'<td class="ch">{len(deti)}</td>'
                f'<td>{f"<span class=kab>{e(kab)}</span>" if kab else "<span class=net>—</span>"}</td></tr>')

    def vkladka_gruppy(kod):
        star = gruppy[kod]
        kab = kabinety.get(kod)
        svoi = sorted((t for t in prep.values() if t["gruppa"] == kod), key=lambda t: t["name"])
        deti = [r for r in shk if gr_shk(r) == kod]
        ryady_prep = "".join(
            f'<tr><td class="pr"><b>{e(t["name"])}</b>'
            f'{" <span class=redko>приходит не всегда</span>" if t["name"] == "Ольга Рыжая" else ""}</td>'
            f'<td class="ch">{sum(1 for r in shk if r["teacher_id"] == t["id"])}</td></tr>'
            for t in svoi)
        ryady_deti = "".join(
            f'<tr><td><b>{e(r["surname"])}</b> {e(r["name"])} '
            f'<span class="kl">{e(r["class"])}</span></td>'
            f'<td>{e(prep[r["teacher_id"]]["name"]) if r["teacher_id"] in prep else "<span class=net>ждёт назначения</span>"}</td></tr>'
            for r in deti)
        return f"""<section class="vid" id="v-{kod}">
  <p class="shapka">{e(star)} · {f'кабинет <span class="kab">{e(kab)}</span>' if kab else '<span class="net">кабинет не назначен</span>'} ·
     преподавателей {len(svoi)} · школьников {len(deti)}</p>
  <table><thead><tr><th>Преподаватель</th><th>Школьников</th></tr></thead><tbody>{ryady_prep}</tbody></table>
  <table style="margin-top:2rem"><thead><tr><th>Школьник</th><th>Принимает</th></tr></thead><tbody>{ryady_deti}</tbody></table>
</section>"""

    l9 = sorted(p.name for p in (MAT / "listki").glob("*.pdf"))
    l8 = sorted(p.name for p in (MAT / "listki-8kl").glob("*.pdf"))

    def pdf(spisok, papka):
        if not spisok:
            return '<p class="net">пока нет</p>'
        return '<ul class="fajly">' + "".join(
            f'<li><a href="{papka}/{e(n)}">{e(n[:-4])}</a></li>' for n in spisok) + "</ul>"

    zhdut = [r for r in shk if r["teacher_id"] not in prep]

    VYHOD.write_text(f"""<!doctype html>
<html lang="ru">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Спецмат · 9 класс</title>
<style>
:root{{--bg:#fbfaf6;--panel:#fffdf8;--text:#211f1b;--muted:#726c60;--rule:#e7e2d6;
  --accent:#2f6e8e;--accent-soft:#e8f0f4;--warm:#c9743a;--faint:#b7ae9c;--chip:#e7e0d2;
  --sans:"Source Sans 3",system-ui,-apple-system,"Helvetica Neue",Arial,sans-serif;
  --serif:"Source Serif 4",Georgia,"Times New Roman",serif}}
@media(prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#1b1e22;--panel:#23272c;
  --text:#dcd8d0;--muted:#9a948a;--rule:#343a41;--accent:#7fb6d2;--accent-soft:#22333d;
  --warm:#e0946a;--faint:#6b6f75;--chip:#333a41}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--text);font-family:var(--serif);font-size:20px}}
/* Меню — строка сверху: три пункта помещаются, ничего выезжать не должно (§1). */
.menu{{position:sticky;top:0;z-index:40;display:flex;gap:.3rem;align-items:baseline;
  padding:.9rem 3rem;background:var(--panel);border-bottom:1px solid var(--rule);
  font-family:var(--sans);flex-wrap:wrap}}
.menu .im{{font-weight:600;font-size:1.05rem;margin-right:1.6rem;white-space:nowrap}}
.menu label{{cursor:pointer;font-weight:600;font-size:1.05rem;color:var(--muted);
  padding:.35em 1rem;border-radius:8px}}
.menu label:hover{{color:var(--text);background:var(--accent-soft)}}
.holst{{padding:2.2rem 3rem 4rem;max-width:none}}
h1{{font-family:var(--sans);font-size:2.5rem;font-weight:600;letter-spacing:-.02em;margin:0 0 .1em}}
.data{{color:var(--muted);font-family:var(--sans);font-size:1rem;margin:0 0 1.6rem}}
.oblozhka p{{font-size:1.3rem;line-height:1.5;max-width:52em;margin:0 0 .8em}}
.raspisanie{{border:1px solid var(--rule);border-radius:10px;padding:1.1rem 1.4rem;
  margin:1.6rem 0 0;background:var(--panel);max-width:52em}}
.zag2{{font-family:var(--sans);font-size:.85rem;font-weight:600;letter-spacing:.09em;
  text-transform:uppercase;color:var(--faint);margin:0 0 .5em}}
.str,.vid{{display:none}}
#p-start:checked~#s-start,#p-list:checked~#s-list,#p-rasp:checked~#s-rasp{{display:block}}
#p-start:checked~.menu label[for=p-start],#p-list:checked~.menu label[for=p-list],
#p-rasp:checked~.menu label[for=p-rasp]{{color:var(--accent);background:var(--accent-soft)}}
input.rd{{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none}}
.tabbar{{display:flex;gap:.25rem;border-bottom:2px solid var(--rule);margin:0 0 1.8rem;flex-wrap:wrap}}
.tabbar label{{cursor:pointer;font-family:var(--sans);font-weight:600;font-size:1.1rem;
  color:var(--muted);padding:.5rem 1.2rem;border:2px solid transparent;border-bottom:none;
  border-radius:10px 10px 0 0;margin-bottom:-2px}}
.tabbar label:hover{{color:var(--text)}}
{"".join(f"#t-{k}:checked~#v-{k}{{display:block}}#t-{k}:checked~.tabbar label[for=t-{k}]"
         "{color:var(--accent);background:var(--panel);border-color:var(--rule) var(--rule) var(--panel)}"
         for k in ("shk","prep","В","Д","Н"))}
{"".join(f"#l-{k}:checked~#w-{k}{{display:block}}#l-{k}:checked~.tabbar label[for=l-{k}]"
         "{color:var(--accent);background:var(--panel);border-color:var(--rule) var(--rule) var(--panel)}"
         for k in ("9","8"))}
table{{border-collapse:collapse;width:100%;font-size:1.05rem}}
th{{font-family:var(--sans);font-size:.8rem;font-weight:600;letter-spacing:.09em;
  text-transform:uppercase;color:var(--faint);text-align:left;padding:0 1.1rem .55rem 0;
  border-bottom:1px solid var(--rule)}}
td{{padding:.5rem 1.1rem .5rem 0;border-bottom:1px solid var(--rule);vertical-align:baseline}}
tr:hover td{{background:var(--accent-soft)}}
.kl{{color:var(--muted);font-family:var(--sans);font-size:.9rem}}
.kab{{font-family:var(--sans);font-weight:600;background:var(--chip);border-radius:7px;
  padding:.1em .55em;white-space:nowrap}}
.gr{{font-family:var(--sans);font-weight:600;color:var(--accent)}}
.pr{{white-space:nowrap}}
.deti{{font-size:.95rem;color:var(--muted);line-height:1.45}}
.ch{{font-family:var(--sans);color:var(--muted);text-align:right;white-space:nowrap}}
.net{{color:var(--warm);font-family:var(--sans);font-size:.95rem}}
.redko{{font-family:var(--sans);font-size:.85rem;color:var(--warm)}}
.shapka{{font-family:var(--sans);font-size:1.15rem;color:var(--muted);margin:0 0 1.4rem}}
.zhdut{{border:1px solid var(--warm);border-radius:10px;padding:1rem 1.3rem;margin:0 0 1.8rem}}
.zhdut .zag2{{color:var(--warm)}}
.poisk{{width:100%;max-width:640px;padding:.65em .9em;font:inherit;font-size:1.1rem;
  border:1px solid var(--rule);border-radius:9px;background:var(--panel);color:var(--text);margin:0 0 1.5rem}}
.poisk:focus{{outline:none;border-color:var(--accent)}}
.podskazki{{position:relative;max-width:640px}}
.spisok{{position:absolute;left:0;right:0;top:3.1rem;z-index:20;background:var(--panel);
  border:1px solid var(--rule);border-radius:0 0 9px 9px;max-height:18rem;overflow:auto}}
.spisok div{{padding:.5em .9em;cursor:pointer}}
.spisok div:hover{{background:var(--accent-soft);color:var(--accent)}}
.fajly{{list-style:none;margin:0;padding:0;columns:2;column-gap:3rem}}
.fajly li{{padding:.4em 0;border-bottom:1px solid var(--rule);break-inside:avoid}}
.fajly a{{color:var(--accent);text-decoration:none;font-size:1.05rem}}
@media(max-width:760px){{.menu,.holst{{padding-left:1.1rem;padding-right:1.1rem}}.fajly{{columns:1}}}}
</style>

<input class="rd" type="radio" name="str" id="p-start" checked>
<input class="rd" type="radio" name="str" id="p-list">
<input class="rd" type="radio" name="str" id="p-rasp">
<nav class="menu">
  <span class="im">Спецмат · 9 класс</span>
  <label for="p-start">Стартовая</label>
  <label for="p-list">Листки</label>
  <label for="p-rasp">Распределение</label>
</nav>

<section class="str holst" id="s-start">
  <div class="oblozhka">
    <h1>Спецмат · 9 класс</h1>
    <p class="data">9К и 9Л · распределение на {DATA_SLOVAMI}</p>
    <p>Кто у кого занимается и в каком кабинете, и все листки — этого года и прошлого.</p>
    <div class="raspisanie">
      <div class="zag2">Расписание</div>
      <div>Занятия по понедельникам и четвергам. <span class="net">время пока не указано</span></div>
    </div>
    <div class="podskazki" style="margin-top:2rem">
      <input class="poisk" id="poisk" placeholder="Найти себя — фамилия школьника или имя преподавателя" autocomplete="off">
      <div class="spisok" id="spisok" hidden></div>
      <div id="nashli"></div>
    </div>
  </div>
</section>

<section class="str holst" id="s-list">
  <h1>Листки</h1>
  <input class="rd" type="radio" name="lst" id="l-9" checked>
  <input class="rd" type="radio" name="lst" id="l-8">
  <div class="tabbar"><label for="l-9">9 класс</label><label for="l-8">8 класс</label></div>
  <section class="vid" id="w-9" style="display:block">{pdf(l9, "listki")}</section>
  <section class="vid" id="w-8">{pdf(l8, "listki-8kl")}</section>
</section>

<section class="str holst" id="s-rasp">
  <h1>Распределение</h1>
  <p class="data">на {DATA_SLOVAMI}</p>
  {'<div class="zhdut"><div class="zag2">ждут назначения — ' + str(len(zhdut)) + '</div>'
   + ", ".join(e(f'{r["surname"]} {r["name"]}') for r in zhdut) + '</div>' if zhdut else ''}
  <input class="rd" type="radio" name="vk" id="t-shk" checked>
  <input class="rd" type="radio" name="vk" id="t-prep">
  <input class="rd" type="radio" name="vk" id="t-В">
  <input class="rd" type="radio" name="vk" id="t-Д">
  <input class="rd" type="radio" name="vk" id="t-Н">
  <div class="tabbar">
    <label for="t-shk">школьникам</label><label for="t-prep">преподавателям</label>
    <label for="t-В">В</label><label for="t-Д">Д</label><label for="t-Н">Н</label>
  </div>
  <section class="vid" id="v-shk">
    <table><thead><tr><th>Школьник</th><th>Группа</th><th>Принимает</th><th>Кабинет</th></tr></thead>
    <tbody>{"".join(stroka_shk(r) for r in shk)}</tbody></table>
  </section>
  <section class="vid" id="v-prep">
    <table><thead><tr><th>Преподаватель</th><th>Группа</th><th>Школьники</th><th>#</th><th>Кабинет</th></tr></thead>
    <tbody>{"".join(stroka_prep(t) for t in sorted(prep.values(), key=lambda x: x["name"]))}</tbody></table>
  </section>
  {"".join(vkladka_gruppy(k) for k in ("В", "Д", "Н"))}
</section>

<script>
// Поиск ищет и школьника, и преподавателя, подсказывает от двух букв: людей мало.
const IMENA = {[e(f'{r["surname"]} {r["name"]}') for r in shk] + [e(t["name"]) for t in prep.values()]!r};
const KOMU = {{{",".join(f'"{e(r["surname"])} {e(r["name"])}":"{e(prep[r["teacher_id"]]["name"]) if r["teacher_id"] in prep else "ждёт назначения"} · {e(kab_shk(r) or "кабинет не назначен")}"' for r in shk)}}};
const poisk=document.getElementById('poisk'),spisok=document.getElementById('spisok'),nashli=document.getElementById('nashli');
poisk.addEventListener('input',e=>{{
  const q=e.target.value.trim().toLowerCase(); nashli.innerHTML='';
  if(q.length<2){{spisok.hidden=true;return;}}
  const r=IMENA.filter(n=>n.toLowerCase().includes(q)).slice(0,8);
  spisok.innerHTML=r.map(n=>'<div>'+n+'</div>').join(''); spisok.hidden=!r.length;
}});
spisok.addEventListener('click',e=>{{
  if(e.target.tagName!=='DIV')return;
  const n=e.target.textContent; poisk.value=n; spisok.hidden=true;
  nashli.innerHTML = KOMU[n] ? '<p class="shapka" style="margin-top:1rem">'+n+' → '+KOMU[n]+'</p>' : '';
}});
document.addEventListener('click',e=>{{if(!e.target.closest('.podskazki'))spisok.hidden=true;}});
</script>
""", encoding="utf-8")
    print(f"собрано: {VYHOD}")
    print(f"  школьников {len(shk)} · преподавателей {len(prep)} · ждут назначения {len(zhdut)}")
    print(f"  группы: " + " · ".join(f"{k}→{kabinety.get(k,'—')}" for k in ("В","Д","Н")))
    print(f"  листки: 9кл {len(l9)} · 8кл {len(l8)}")
    return 0


if __name__ == "__main__":
    sys.exit(sobrat())
