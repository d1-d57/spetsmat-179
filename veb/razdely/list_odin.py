#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-code — served by `veb/server.py` on `/listki/<номер>`.
"""The page of ONE sheet: its problems, read out of the database.

WHY THIS PAGE EXISTS.  A link to a sheet used to open a PDF, and a PDF is a picture of a
sheet: the site could not say what was on it, the conduit's columns had to be typed in by
hand beside it, and on 2026-09-07 the two disagreed — sheet `16α` was eleven cells in the
database and fifteen problems in the PDF the same site was handing out.  This page renders
the sheet FROM the database, so "what is on the sheet" has exactly one answer, and the PDF
becomes one of two downloads rather than the sheet itself.

🔴 THIS PAGE INHERITS THE LOOK, IT DOES NOT DECIDE IT (`doc/DIZAJN-ZAKREPLENO.md` §0: new
pages are made FROM the existing design; existing pages are not remade to suit them).  The
stylesheet is not copied here and no colour is written down twice: `_obshchij_stil()` takes
the site's own `<style>` block from the same builder that produces the front page, so the
palette this page uses IS the palette, not a second list of it that would drift.  What is
added below is layout for blocks that do not exist elsewhere on the site, written entirely
in the existing custom properties.
"""
from __future__ import annotations

import re
import sys
import sqlite3

from veb.obshchee.karkas import e

_STIL: str | None = None


def _obshchij_stil(baza=None) -> str:
    """The site's stylesheet, taken from the site.

    Building the front page costs ~10 ms and is cached for the life of the process; the
    alternative — a copy of the palette in this file — is the one thing
    `doc/DIZAJN-ZAKREPLENO.md` §2 forbids outright.
    """
    global _STIL
    if _STIL is None:
        from tools.sobrat_stranicu import sobrat_html
        # Таблица стилей от ДАННЫХ не зависит, но собирается вместе со страницей,
        # а страница читает базу. Значит и здесь базу называет звавший.
        #
        # 🔴 СТРАНИЦА, УПАВШАЯ ИЗ-ЗА СВОЕЙ ЖЕ ТАБЛИЦЫ СТИЛЕЙ, — ХУЖЕ СТРАНИЦЫ БЕЗ
        # ОФОРМЛЕНИЯ, И ЭТО НЕ ПРЕДПОЛОЖЕНИЕ. До 10.09 оболочка собиралась из
        # `data/spetsmat.db`, лежавшей в репозитории; база оттуда ушла по решению
        # владельца, и любая база победнее (свежая, тестовая, только что
        # восстановленная) роняет сборку оболочки на первом же недостающем куске
        # данных — замерено: `KeyError: 'Д'` на базе, где заведена одна группа.
        # Карточка школьника при этом отдавала не «страницу без палитры», а обрыв
        # соединения: 500 без тела. Отказ печатается в `stderr` — молчаливая
        # деградация здесь была бы тем же самым фантомом, только в оформлении.
        try:
            stranica_sajta = sobrat_html("gost", baza=baza)
        except Exception as beda:                       # noqa: BLE001
            print("⚠ таблица стилей сайта не собралась (%s: %s) — страница выйдет "
                  "без палитры сайта; данные это НЕ затрагивает"
                  % (type(beda).__name__, beda), file=sys.stderr)
            stranica_sajta = ""
        soderzhimoe = re.search(r"<style>(.*?)</style>", stranica_sajta, re.S)
        _STIL = soderzhimoe.group(1) if soderzhimoe else ""
    return _STIL


# Layout of the sheet itself.  Only properties already defined by the shared stylesheet
# are used, and every colour is a custom property of the site's palette.
SVOI_STILI = """
/* 🔴 КОЛОНКА ЖИВЁТ В `em`, А КЕГЛЬ — В ШИРИНЕ ОКНА. 46em это и есть «сколько символов в
   строке»: мера в em не меняется, как бы ни рос шрифт. Поэтому чтобы текст занял всю
   страницу, а строка осталась той же длины В СИМВОЛАХ, растить надо кегль, и колонка
   растёт за ним сама. ВСЁ внутри колонки — поля, отступ под номер, зазор — тоже меряется
   в `em`, иначе они остались бы в пикселях, съедали бы всё меньшую долю растущей строки,
   и символов в строке становилось бы больше: замер показал +6 % при кегле 29px. При 20px
   все числа дают ровно прежние пиксели (2.4em = 48px = прежние 3rem), так что вид на
   ноутбуке не сдвинулся ни на пиксель. `calc(100vw/46)` — тот кегль, при котором 46em
   ложатся точно в ширину окна.
   ВЕРХНЕЙ ГРАНИЦЫ НЕТ НАМЕРЕННО. Она была (34px) — и на мониторе 1920 колонка вставала
   в 1564px, оставляя справа 356px пустоты: ровно то, из-за чего страницу и правили.
   Требование владельца дословно: «и на десктопе, и на мобильном телефоне текст задачи
   должен быть во всю ширину экрана». Значит кегль растёт, сколько нужно, а не сколько
   не жалко.
   Нижняя граница 20px — размер шрифта сайта: на телефоне 100vw/46 дало бы нечитаемые 8px,
   а колонка и без роста кегля упирается в оба края экрана, потому что 46em там шире
   экрана. То есть «во всю ширину» держится на ВСЕХ размерах: до 920px — нижней границей,
   выше — самим кеглем. */
.listok{max-width:46em;padding:1.3em 2.4em 2.4em;
  font-size:max(20px, calc(100vw / 46))}
/* Всё внутри колонки меряется в `em`, а не в `rem`: иначе заголовок и подписи остались бы
   прежними, пока текст растёт, и блок расслоился бы на два размера. Числа подобраны так,
   что при кегле 20px вид ровно прежний: 1.2em = 24px = прежние 1.5rem. */
.listok h1{font-family:var(--sans);font-size:1.2em;font-weight:600;margin:0 0 .2rem}
.listok .tema{color:var(--muted);font-family:var(--sans);font-size:.8em;margin:0 0 1.4rem}
.listok .skachat{font-family:var(--sans);font-size:.76em;margin:0 0 2rem}
.listok .skachat a{color:var(--accent);text-decoration:none;margin-right:1.2rem}
.listok .skachat a:hover{text-decoration:underline}
.blok{display:flex;gap:.8em;margin:0 0 .92em;line-height:1.45}
.blok .nom{font-family:var(--sans);font-weight:600;color:var(--faint);
  min-width:1.92em;text-align:right;flex:none}
.blok.proza{color:var(--muted);margin-bottom:1.2em}
.blok.proza .nom{visibility:hidden}
.nazad{font-family:var(--sans);font-size:.95rem;color:var(--muted);text-decoration:none}
.nazad:hover{text-decoration:underline}
@media(max-width:760px){.listok{padding-left:1.1rem;padding-right:1.1rem}}
"""


def bloki(conn: sqlite3.Connection, nomer: str) -> tuple[dict | None, list[dict]]:
    """The sheet's row and its blocks in reading order.  Empty list = never imported."""
    conn.row_factory = sqlite3.Row
    listok = conn.execute(
        "select id, number, title from sheets where number = ?", (nomer,)).fetchone()
    if listok is None:
        return None, []
    stroki = conn.execute(
        "select id, kind, num, star, tex from sheet_blocks where sheet_id = ? order by ord",
        (listok["id"],)).fetchall()
    # The markable cells, attached to the block they belong to.  A block with no cells is
    # prose; a block with several is a problem with sub-items.
    yachejki: dict[int, list[str]] = {}
    for stroka in conn.execute(
            "select block_id, label from problems where sheet_id = ? and block_id is not null "
            "order by ord", (listok["id"],)):
        yachejki.setdefault(stroka["block_id"], []).append(stroka["label"])
    out = []
    for stroka in stroki:
        blok = dict(stroka)
        blok["yachejki"] = yachejki.get(stroka["id"], [])
        out.append(blok)
    return dict(listok), out


def zagolovok(nomer: str, tema: str) -> str:
    """«16А. Деревья» — ОДИН раз, каким бы ни был `title` в базе.

    `sheets.title` хранит название ВМЕСТЕ с номером («16А. Деревья»), а страница
    приписывала номер ещё раз и печатала «16А. 16А. Деревья». Чиню на выводе, а не в
    базе: `title` в этой форме читают и другие места, и переписывать 30 строк живой
    таблицы ради заголовка одной страницы — цена, несопоставимая с поводом.

    Номер снимается ТОЛЬКО если он стоит в начале и отделён точкой: «16А. Деревья» → да,
    а название вроде «16 задач про графы» не тронуто — там за числом нет точки.
    """
    tema = (tema or "").strip()
    hvost = tema[len(nomer):].lstrip() if tema.startswith(nomer) else ""
    if hvost.startswith("."):
        tema = hvost[1:].strip()
    return "%s. %s" % (nomer, tema) if tema else nomer


def stranica(listok: dict, bloki_listka: list[dict], baza=None) -> str:
    """The whole page for one sheet."""
    nomer = listok["number"]
    tema = listok["title"] or ""
    imya = zagolovok(nomer, tema)
    telo = []
    for blok in bloki_listka:
        if blok["kind"] == "task":
            zvezda = " ★" if blok["star"] else ""
            # Подписи «отмечается: 1а · 1б» под задачей больше нет: владелец убрал её
            # с этой страницы. Ячейки по-прежнему приезжают из `bloki()` — их читает
            # кондуит, где они и нужны, — но школьнику, читающему условие, они лишние.
            telo.append(
                '<div class="blok"><div class="nom">%s%s</div><div>%s</div></div>'
                % (e(blok["num"] or ""), zvezda, e(blok["tex"])))
        else:
            telo.append(
                '<div class="blok proza"><div class="nom">·</div><div>%s</div></div>'
                % e(blok["tex"]))
    if not telo:
        # An honest empty state beats an empty frame: the sheet exists, its text does not
        # yet, and the PDF below is still the whole sheet.
        telo.append('<div class="blok proza"><div class="nom">·</div><div>'
                    'Задачи этого листка ещё не занесены в базу — пока его целиком '
                    'показывает PDF.</div></div>')
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(imya)} — Ключики</title>
<style>{_obshchij_stil(baza)}{SVOI_STILI}</style></head>
<body>
<div class="menu"><span class="im">Ключики</span><a class="nazad" href="/">ко всем листкам</a></div>
<main class="listok">
  <h1>{e(imya)}</h1>
  <p class="tema">Листок девятого класса</p>
  <p class="skachat"><a href="/listki/{e(nomer)}.pdf">Скачать PDF</a>
     <a href="/listki/{e(nomer)}.tex">Скачать TeX</a></p>
  {"".join(telo)}
</main>
</body></html>"""
