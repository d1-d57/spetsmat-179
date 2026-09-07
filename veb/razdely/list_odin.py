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
import sqlite3

from veb.obshchee.karkas import e

_STIL: str | None = None


def _obshchij_stil() -> str:
    """The site's stylesheet, taken from the site.

    Building the front page costs ~10 ms and is cached for the life of the process; the
    alternative — a copy of the palette in this file — is the one thing
    `doc/DIZAJN-ZAKREPLENO.md` §2 forbids outright.
    """
    global _STIL
    if _STIL is None:
        from tools.sobrat_stranicu import sobrat_html
        soderzhimoe = re.search(r"<style>(.*?)</style>", sobrat_html("gost"), re.S)
        _STIL = soderzhimoe.group(1) if soderzhimoe else ""
    return _STIL


# Layout of the sheet itself.  Only properties already defined by the shared stylesheet
# are used, and every colour is a custom property of the site's palette.
SVOI_STILI = """
.listok{max-width:46em;padding:1.3rem 3rem 3rem}
.listok h1{font-family:var(--sans);font-size:1.5rem;font-weight:600;margin:0 0 .2rem}
.listok .tema{color:var(--muted);font-family:var(--sans);font-size:1rem;margin:0 0 1.4rem}
.listok .skachat{font-family:var(--sans);font-size:.95rem;margin:0 0 2rem}
.listok .skachat a{color:var(--accent);text-decoration:none;margin-right:1.2rem}
.listok .skachat a:hover{text-decoration:underline}
.blok{display:flex;gap:1rem;margin:0 0 1.15rem;line-height:1.45}
.blok .nom{font-family:var(--sans);font-weight:600;color:var(--faint);
  min-width:2.4rem;text-align:right;flex:none}
.blok.proza{color:var(--muted);margin-bottom:1.5rem}
.blok.proza .nom{visibility:hidden}
/* The cells a problem can be checked off by.  They are the sheet's own labels — the
   same strings the conduit uses for its columns — and a pupil needs to see them: on
   16α the sub-items sit on problem 14, and a page that showed only the prose could not
   say so. */
.yachejki{font-family:var(--sans);font-size:.85rem;color:var(--faint);margin-top:.35rem}
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


def stranica(listok: dict, bloki_listka: list[dict]) -> str:
    """The whole page for one sheet."""
    nomer = listok["number"]
    tema = listok["title"] or ""
    telo = []
    for blok in bloki_listka:
        if blok["kind"] == "task":
            zvezda = " ★" if blok["star"] else ""
            metki = blok.get("yachejki") or []
            podpis = ('<div class="yachejki">отмечается: %s</div>'
                      % " · ".join(e(m) for m in metki)) if len(metki) > 1 else ""
            telo.append(
                '<div class="blok"><div class="nom">%s%s</div><div>%s%s</div></div>'
                % (e(blok["num"] or ""), zvezda, e(blok["tex"]), podpis))
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
<title>{e(nomer)}. {e(tema)} — Ключики</title>
<style>{_obshchij_stil()}{SVOI_STILI}</style></head>
<body>
<div class="menu"><span class="im">Ключики</span><a class="nazad" href="/">ко всем листкам</a></div>
<main class="listok">
  <h1>{e(nomer)}. {e(tema)}</h1>
  <p class="tema">Листок девятого класса</p>
  <p class="skachat"><a href="/listki/{e(nomer)}.pdf">Скачать PDF</a>
     <a href="/listki/{e(nomer)}.tex">Скачать TeX</a></p>
  {"".join(telo)}
</main>
</body></html>"""
