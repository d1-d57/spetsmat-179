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


def e(s):
    return html.escape(str(s if s is not None else ""))


def sobrat():
    c = sqlite3.connect(DATA)
    c.row_factory = sqlite3.Row
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
        prep, kab = k
        deti = "".join(f"<li>{e(d)}</li>" for d in sorted(v))
        chip = f'<span class="kab">{e(kab)}</span>' if kab else ""
        return f'<div class="gr"><h3>{e(prep)} {chip}</h3><ul>{deti}</ul></div>'

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
<title>Спецмат 9 класс</title>
{stil}
<style>
.gr{{margin:0 0 1.8rem}}
.gr h3{{font-family:var(--sans);font-size:1.35rem;font-weight:600;margin:0 0 .3em}}
.gr ul{{list-style:none;margin:0;padding:0;columns:2;column-gap:3rem}}
.gr li{{padding:.3em 0;border-bottom:1px solid var(--rule);break-inside:avoid}}
.fajly{{list-style:none;margin:0;padding:0;columns:2;column-gap:3rem}}
.fajly li{{padding:.4em 0;border-bottom:1px solid var(--rule);break-inside:avoid}}
.fajly a{{color:var(--accent);text-decoration:none;font-size:1.1rem}}
.fajly a:hover{{text-decoration:underline}}
h2{{font-family:var(--sans);font-size:2rem;font-weight:600;margin:3rem 0 1.2rem;
   padding-top:1.5rem;border-top:1px solid var(--rule)}}
h2:first-of-type{{border-top:none;padding-top:0;margin-top:2rem}}
</style>

<button class="burger" id="burger" aria-label="меню"><span></span><span></span><span></span></button>
<nav class="panel-bok" id="panel">
  <div class="zag">Спецмат</div>
  <a href="#raspredelenie">Распределение</a>
  <a href="#listki9">Листки 9 класса</a>
  <a href="#listki8">Листки 8 класса</a>
</nav>

<main class="holst" id="holst">
  <h1>Спецмат</h1>
  <p class="data">9 класс · на {DATA_NA}</p>

  <h2 id="raspredelenie">Распределение</h2>
  <input class="poisk" id="poisk" placeholder="Фамилия" autocomplete="off">
  <table>
    <thead><tr><th>Школьник</th><th>Принимает</th><th>Кабинет</th></tr></thead>
    <tbody id="telo">{"".join(tr(r) for r in stroki)}</tbody>
  </table>

  <h2>По преподавателям</h2>
  {"".join(gruppa(k, v) for k, v in sorted(po_prepodam.items()))}

  <h2 id="listki9">Листки 9 класса</h2>
  {pdf(l9, "listki")}

  <h2 id="listki8">Листки 8 класса</h2>
  {pdf(l8, "listki-8kl")}
</main>

<script>
const b=document.getElementById('burger'),p=document.getElementById('panel'),h=document.getElementById('holst');
b.addEventListener('click',()=>{{p.classList.toggle('open');h.classList.toggle('sdvinut');}});
const poisk=document.getElementById('poisk'),telo=document.getElementById('telo'),vse=[...telo.rows];
poisk.addEventListener('input',e=>{{
  const f=e.target.value.trim().toLowerCase();
  vse.forEach(r=>{{r.style.display=!f||r.cells[0].textContent.trim().toLowerCase().startsWith(f)?'':'none';}});
}});
</script>
""", encoding="utf-8")
    print(f"собрано: {VYHOD}")
    print(f"  школьников: {len(stroki)} · преподавателей: {len(po_prepodam)}")
    print(f"  листков 9 класса: {len(l9)} · 8 класса: {len(l8)}")
    print("  расписание: блока НЕТ — время занятий не названо владельцем, выдумывать запрещено")
    return 0


if __name__ == "__main__":
    sys.exit(sobrat())
