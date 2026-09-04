#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-hand — зовётся при выкладке статической страницы.
"""Собирает САМОДОСТАТОЧНУЮ страницу для GitHub Pages: docs/index.html.

ЗАЧЕМ. Страница для всех должна жить БЕЗ ноутбука владельца: Pages отдаёт статику,
и ей не нужен ни сервер, ни база. Поэтому данные вмораживаются в html на момент сборки.

ЧТО ВНУТРИ: распределение (только чтение), листки 9 и 8 класса, место под расписание.
🔴 РАСПИСАНИЕ НЕ ВЫДУМЫВАЕТСЯ: точного времени владелец не помнит. Пока не назовёт —
блока нет вовсе. Пустое место честнее выдуманного часа.
"""
import html
import pathlib
import sqlite3
import sys

KOREN = pathlib.Path(__file__).resolve().parent.parent
DATA = KOREN / "data" / "spetsmat.db"
VYHOD = KOREN / "docs" / "index.html"
MAT = KOREN.parent / "materials" / "spetsmat-2026"
DATA_NA = "5 сентября"

# 🔴 СТАРШИЕ ПО КАБИНЕТАМ. Пусто, пока владелец не назвал, кто из троих какой кабинет
# держит. Ваня сидит в 303, Даня в 302, но на 203 два кандидата (Наталия Павлована и
# Надя), а в 302 есть ещё Наталья Яковлевна — угадывать нельзя, это дети перед занятием.
# Заполняется ОДНОЙ строкой, когда владелец ответит: {"203": "имя", ...}
# Старший берётся из ГРУППЫ преподавателя (постоянная привязка), а кабинет —
# из назначения группы НА ДЕНЬ. Кабинета на дату нет — колонка пустая, и это
# законный случай: владелец ставит привязку накануне вечером.


def e(s):
    return html.escape(str(s if s is not None else ""))


def sobrat():
    c = sqlite3.connect(DATA)
    c.row_factory = sqlite3.Row
    STARSHIE = {r[0]: r[1] for r in c.execute(
        "select t.name, g.starshij from teachers t join gruppy g on g.kod = t.gruppa")}
    KABINET_GRUPPY = {r[0]: r[1] for r in c.execute(
        "select gruppa, kabinet from kabinet_na_den where data = date('now','localtime','+1 day')")}
    stroki = c.execute("""
        select s.surname, s.name, s.class, t.name as prep, e.room
        from students s
        left join enrollment e on e.student_id = s.id and e.valid_to = '9999-12-31' and e.slot = 1
        left join teachers t on t.id = e.teacher_id
        where s.status is null or s.status <> 'left'
        order by s.surname, s.name
    """).fetchall()

    po_prepodam = {}
    for r in stroki:
        if r["prep"]:
            po_prepodam.setdefault((r["prep"], r["room"]), []).append(f'{r["surname"]} {r["name"]}')

    l9 = sorted(p.name for p in (MAT / "listki").glob("*.pdf"))
    l8 = sorted(p.name for p in (MAT / "listki-8kl").glob("*.pdf"))

    def tr(r):
        prep = e(r["prep"]) if r["prep"] else '<span class="net">не назначен</span>'
        kab = f'<span class="kab">{e(r["room"])}</span>' if r["room"] else '<span class="net">—</span>'
        return (f'<tr><td><b>{e(r["surname"])}</b> {e(r["name"])} '
                f'<span class="kl">{e(r["class"])}</span></td>'
                f'<td>{prep}</td><td>{kab}</td></tr>')

    def gruppa(k, v):
        # ОДНА СТРОКА, а не блок: преподаватель · школьники · старший · кабинет.
        # Владелец: «зачем его делать большими буквами, ради солидности не надо».
        # Смысл списка в том, что видны ВСЕ сразу.
        prep, kab = k
        deti = ", ".join(sorted(v))
        chip = f'<span class="kab">{e(kab)}</span>' if kab else ""
        star = STARSHIE.get(prep)
        star_html = f'<span class="star">{e(star)}</span>' if star else ""
        return (f'<tr><td class="pr"><b>{e(prep)}</b></td>'
                f'<td class="deti">{e(deti)}</td>'
                f'<td>{star_html}</td><td>{chip}</td></tr>')

    def pdf(spisok, papka):
        if not spisok:
            return '<p class="net">пока нет</p>'
        return "<ul class=\"fajly\">" + "".join(
            f'<li><a href="{papka}/{e(n)}">{e(n[:-4])}</a></li>' for n in spisok) + "</ul>"

    stil = (KOREN / "veb" / "templates" / "index.html").read_text(encoding="utf-8")
    stil = stil[stil.index("<style>"):stil.index("</style>") + 8]

    VYHOD.write_text(f"""<!doctype html>
<html lang="ru">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Спецмат · 9 класс</title>
{stil}
<style>
.oblozhka{{max-width:none;margin:0 0 2.5rem}}
.oblozhka p{{font-size:1.35rem;line-height:1.5;margin:0 0 .8em;max-width:52em}}
.raspisanie{{border:1px solid var(--rule);border-radius:10px;padding:1.1rem 1.4rem;
  margin:1.5rem 0 0;background:var(--panel);max-width:52em}}
.raspisanie .zag2{{font-family:var(--sans);font-size:.85rem;font-weight:600;
  letter-spacing:.09em;text-transform:uppercase;color:var(--faint);margin:0 0 .5em}}
.pr{{white-space:nowrap;font-size:1.05rem}}
.deti{{font-size:1rem;color:var(--muted);line-height:1.45}}
.star{{font-family:var(--sans);font-size:.95rem;color:var(--accent)}}
.fajly{{list-style:none;margin:0;padding:0;columns:2;column-gap:3rem}}
.fajly li{{padding:.45em 0;border-bottom:1px solid var(--rule);break-inside:avoid}}
.fajly a{{color:var(--accent);text-decoration:none;font-size:1.1rem}}
.fajly a:hover{{text-decoration:underline}}
/* Вкладки статики: свои имена, стиль наследуется из страницы распределения. */
#t-rasp:checked~#v-rasp,#t-l9:checked~#v-l9,#t-l8:checked~#v-l8{{display:block}}
#t-rasp:checked~.tabbar label[for=t-rasp],
#t-l9:checked~.tabbar label[for=t-l9],
#t-l8:checked~.tabbar label[for=t-l8]{{color:var(--accent);background:var(--panel);
  border-color:var(--rule) var(--rule) var(--panel)}}
.podskazki{{position:relative;max-width:640px}}
.spisok{{position:absolute;left:0;right:0;top:100%;z-index:20;background:var(--panel);
  border:1px solid var(--rule);border-radius:0 0 9px 9px;max-height:19rem;overflow:auto}}
.spisok div{{padding:.55em .9em;cursor:pointer;font-size:1.05rem}}
.spisok div:hover{{background:var(--accent-soft);color:var(--accent)}}
</style>

<button class="burger" id="burger" aria-label="меню"><span></span><span></span><span></span></button>
<nav class="panel-bok" id="panel">
  <div class="zag">Спецмат · 9 класс</div>
  <a href="#" data-vk="t-rasp">Распределение</a>
  <a href="#" data-vk="t-l9">Листки 9 класса</a>
  <a href="#" data-vk="t-l8">Листки 8 класса</a>
</nav>

<main class="holst" id="holst">
  <div class="oblozhka">
    <h1>Спецмат · 9 класс</h1>
    <p class="data">9К и 9Л · на {DATA_NA}</p>
    <p>Здесь распределение — кто у кого занимается и в каком кабинете, — и все листки:
       этого года и прошлого.</p>
    <div class="raspisanie">
      <div class="zag2">Расписание</div>
      <div class="net">время занятий пока не указано</div>
    </div>
  </div>

  <div class="tabs">
    <input type="radio" name="vk" id="t-rasp" checked>
    <input type="radio" name="vk" id="t-l9">
    <input type="radio" name="vk" id="t-l8">
    <div class="tabbar">
      <label for="t-rasp">Распределение</label>
      <label for="t-l9">Листки 9 класса</label>
      <label for="t-l8">Листки 8 класса</label>
    </div>

    <section class="vid" id="v-rasp">
      <div class="podskazki">
        <input class="poisk" id="poisk" placeholder="Найти себя — фамилия школьника или преподавателя" autocomplete="off">
        <div class="spisok" id="spisok" hidden></div>
      </div>
      <table>
        <thead><tr><th>Школьник</th><th>Принимает</th><th>Кабинет</th></tr></thead>
        <tbody id="telo">{"".join(tr(r) for r in stroki)}</tbody>
      </table>

      <h2>По преподавателям</h2>
      <table>
        <thead><tr><th>Преподаватель</th><th>Школьники</th><th>Старший</th><th>Кабинет</th></tr></thead>
        <tbody id="telo-prep">{"".join(gruppa(k, v) for k, v in sorted(po_prepodam.items()))}</tbody>
      </table>
    </section>

    <section class="vid" id="v-l9">{pdf(l9, "listki")}</section>
    <section class="vid" id="v-l8">{pdf(l8, "listki-8kl")}</section>
  </div>
</main>

<script>
const b=document.getElementById('burger'),p=document.getElementById('panel'),h=document.getElementById('holst');
b.addEventListener('click',()=>{{p.classList.toggle('open');h.classList.toggle('sdvinut');}});
p.querySelectorAll('a[data-vk]').forEach(a=>a.addEventListener('click',ev=>{{
  ev.preventDefault();document.getElementById(a.dataset.vk).checked=true;
  p.classList.remove('open');h.classList.remove('sdvinut');
}}));

// Поиск ищет И школьника, И преподавателя, и подсказывает по мере ввода:
// людей мало, двух букв хватает, чтобы восстановить фамилию.
const poisk=document.getElementById('poisk'),spisok=document.getElementById('spisok');
const telo=document.getElementById('telo'),vseStroki=[...telo.rows];
const teloP=document.getElementById('telo-prep'),vsePrep=[...teloP.rows];
const imena=[...new Set([
  ...vseStroki.map(r=>r.cells[0].textContent.trim().split(/\s+/).slice(0,2).join(' ')),
  ...vsePrep.map(r=>r.cells[0].textContent.trim())
])].sort((a,b)=>a.localeCompare(b,'ru'));

function primenit(f){{
  const q=f.trim().toLowerCase();
  vseStroki.forEach(r=>{{r.style.display=!q||r.textContent.toLowerCase().includes(q)?'':'none';}});
  vsePrep.forEach(r=>{{r.style.display=!q||r.textContent.toLowerCase().includes(q)?'':'none';}});
}}
poisk.addEventListener('input',e=>{{
  const q=e.target.value.trim().toLowerCase();
  primenit(q);
  if(q.length<2){{spisok.hidden=true;return;}}
  const nashli=imena.filter(n=>n.toLowerCase().includes(q)).slice(0,8);
  spisok.innerHTML=nashli.map(n=>'<div>'+n+'</div>').join('');
  spisok.hidden=!nashli.length;
}});
spisok.addEventListener('click',e=>{{
  if(e.target.tagName!=='DIV')return;
  poisk.value=e.target.textContent;primenit(poisk.value);spisok.hidden=true;
}});
document.addEventListener('click',e=>{{if(!e.target.closest('.podskazki'))spisok.hidden=true;}});
</script>
""", encoding="utf-8")
    print(f"собрано: {VYHOD}")
    print(f"  школьников: {len(stroki)} · преподавателей: {len(po_prepodam)}")
    print(f"  листков 9 класса: {len(l9)} · 8 класса: {len(l8)}")
    print("  расписание: блока НЕТ — время занятий не названо владельцем, выдумывать запрещено")
    return 0


if __name__ == "__main__":
    sys.exit(sobrat())
