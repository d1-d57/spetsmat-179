#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-hand — the count that says whether the sheets' marks arrived.
"""What kind is every cell of every листок, counted out of the database.

WHY THIS TOOL EXISTS.  `tools/import_listka.py` writes `problems.kind` from the glyph the
sheet prints beside a problem number.  "It ran and said no errors" is not evidence that it
wrote the right thing: the numbers it wrote have to be readable afterwards, by somebody who
did not run it, against the paper.  This is that reading, and it opens the DATABASE — not
the PDF — because the database is what the conduit draws.

    python3 tools/vidy_zadach.py                 # every листок
    python3 tools/vidy_zadach.py 16A 16α 16ℵ     # only these
    python3 tools/vidy_zadach.py --db data/x.db  # against another database

🔴 THE SUM IS THE GATE, AND IT CAN FAIL.  Every cell of a листок has exactly one kind, so
`обязательных + письменных + звёзд + обычных` must equal the number of cells on it.  It
cannot disagree while every kind is counted — which is the point: the tool counts the kinds
it KNOWS, and a value nobody thought of (`двойная` is one, and there are two of them on
sheet 4) lands in `прочие` and breaks the sum on purpose rather than hiding in a bucket.

🔴 IT PRINTS WHAT IT DOES NOT COVER, AND THAT HALF IS NOT DECORATION.  A count of what was
checked is worth nothing without the count of what was not: "проверено 2 из 9" and
"проверено 9 из 9" read identically when only the first half is printed.  Two things are
outside the reach of the import and both are named by number at the end of the run:
  * СТАРЫЕ ЛИСТКИ — the eighteen sheets of last year, whose cells came from
    `seed/sheets.json` (that is, from the workbook) and never from a PDF.  Their kinds are
    the senior's `°` and `*`, imported by `core/services/sheets.py`, and nothing in this
    заход re-reads them.
  * ЯЧЕЙКИ МИМО ИМПОРТА — rows of `problems` with `block_id is null`: a cell that no run of
    `import_listka` has ever matched to a block of a sheet.  Every cell of a sheet that has
    been imported has one; a null therefore means the cell was typed in by hand, or that
    the sheet has not been imported at all.  Its kind is whatever somebody typed, and this
    tool can say nothing about whether that is right.
"""
from __future__ import annotations

import argparse
import pathlib
import sqlite3
import sys

KOREN = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOREN))

import config  # noqa: E402  (after the path is set, which is how every tool here does it)

#: The order the kinds are printed in — obligation first, invitation last.  It is the order
#: the готовности criterion of заход `vidy-zadach` names them in, and printing them in
#: another order would make the two harder to compare than they need to be.
PORYADOK = ("обязательная", "письменная", "звезда", "обычная")

#: The glyph each kind is printed with, the same one the sheet prints and the same one the
#: conduit draws (`veb/razdely/konduit.ZNACHKI`).  Repeated here rather than imported so
#: that this tool opens no web module: it has to run on the server, where it is called from
#: a shell and not from the site.
ZNAK = {"обязательная": "◦", "письменная": "†", "звезда": "⋆", "обычная": " "}


def po_listkam(conn: sqlite3.Connection, nomera: list[str] | None) -> list[dict]:
    """One row per листок: its cells, broken down by kind, in sheet order."""
    listki = conn.execute("select id, number from sheets order by ord").fetchall()
    if nomera:
        izvestnye = {n for _i, n in listki}
        for n in nomera:
            if n not in izvestnye:
                raise SystemExit("листка %s нет в таблице sheets" % n)
        listki = [(i, n) for i, n in listki if n in set(nomera)]

    itog = []
    for sheet_id, nomer in listki:
        vidy = {vid: 0 for vid in PORYADOK}
        prochie: dict[str, int] = {}
        vsego = 0
        bez_bloka = 0
        for vid, skolko, nulevyh in conn.execute(
                "select kind, count(*), sum(block_id is null) "
                "from problems where sheet_id = ? group by kind", (sheet_id,)):
            vsego += skolko
            bez_bloka += nulevyh or 0
            if vid in vidy:
                vidy[vid] = skolko
            else:
                prochie[vid] = skolko
        itog.append({"number": nomer, "vsego": vsego, "vidy": vidy,
                     "прочие": prochie, "мимо импорта": bez_bloka})
    return itog


def napechatat(stroki: list[dict]) -> int:
    """Print the table and return the number of листков whose sum does not add up."""
    rashozhdenij = 0
    print("%-6s %5s  %s" % ("листок", "ячеек", "  ".join("%s %-13s" % (ZNAK[v], v)
                                                        for v in PORYADOK)))
    for s in stroki:
        summa = sum(s["vidy"].values()) + sum(s["прочие"].values())
        beda = "" if summa == s["vsego"] else "  🔴 сумма %d ≠ %d" % (summa, s["vsego"])
        if beda:
            rashozhdenij += 1
        prochie = ("  прочие: " + ", ".join("%s %d" % (k, v)
                                            for k, v in sorted(s["прочие"].items()))
                   if s["прочие"] else "")
        print("%-6s %5d  %s%s%s" % (
            s["number"], s["vsego"],
            "  ".join("%s %-13d" % (ZNAK[v], s["vidy"][v]) for v in PORYADOK),
            prochie, beda))
    return rashozhdenij


def ohvat(stroki: list[dict]) -> None:
    """The other half of the answer: how much of what was counted the import can vouch for."""
    yacheek = sum(s["vsego"] for s in stroki)
    mimo = sum(s["мимо импорта"] for s in stroki)
    print()
    print("ОХВАТ: размечено импортом %d ячеек из %d" % (yacheek - mimo, yacheek))
    print("ЧЕГО ЭТОТ РАЗБОР НЕ ПРОВЕРЯЕТ:")
    print("  • ячеек мимо импорта (block_id is null): %d — вид у них тот, что вписан "
          "руками или засеян из seed/sheets.json, и сверить его не с чем" % mimo)
    starye = [s["number"] for s in stroki if s["мимо импорта"] == s["vsego"] and s["vsego"]]
    print("  • листков, не тронутых импортом вовсе: %d%s"
          % (len(starye), (" — " + ", ".join(starye)) if starye else ""))
    print("  • правильность самой разметки в PDF: этот разбор сверяет базу с разбором, "
          "а не разбор с бумагой — глазами смотрит человек")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("nomera", nargs="*", help="номера листков; пусто — все")
    parser.add_argument("--db", default=None, help="база (по умолчанию config.DB_PATH)")
    args = parser.parse_args(argv)

    put = pathlib.Path(args.db) if args.db else config.DB_PATH
    if not put.is_file():
        raise SystemExit("базы нет: %s" % put)
    conn = sqlite3.connect("file:%s?mode=ro" % put, uri=True)
    # 🔴 ПЕРВОЙ СТРОКОЙ — ОТКУДА ЧИСЛА (Д1, владелец 10.09). Прежняя строка
    # «база: <путь>» называла путь и молчала о СОДЕРЖИМОМ: копия недельной
    # давности печаталась ровно так же, как живая, и её числа выглядели
    # одинаково убедительно. `nazvat` добавляет дату САМОЙ ПОЗДНЕЙ ЗАПИСИ внутри
    # базы — величину, которую копирование не подделывает, в отличие от даты файла.
    from core.istochnik import nazvat, proverit_svezhest
    nazvat(conn)
    # И проверка, которая КРАСНЕЕТ: печатать источник и не смотреть на него —
    # надежда, а не гейт. Числа мёртвой базы описывают прошлое, и это говорится вслух.
    proverit_svezhest(conn)
    stroki = po_listkam(conn, args.nomera or None)
    rashozhdenij = napechatat(stroki)
    ohvat(stroki)
    if rashozhdenij:
        print("\n🔴 листков с несошедшейся суммой: %d" % rashozhdenij, file=sys.stderr)
    return 1 if rashozhdenij else 0


if __name__ == "__main__":
    raise SystemExit(main())
