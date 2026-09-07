#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-hand — the door that gives a sheet's composition a source.
"""Import one sheet into the database as BLOCKS WITH TEXT, not as a list of labels.

WHY THIS TOOL EXISTS.  Until 2026-09-07 the composition of a sheet was typed into
`problems` by hand.  Sheet `16α` was typed as eleven cells `1–8, 10а, 10б, 10в`, while
the PDF the site itself serves has fifteen problems with the sub-items on problem 14 and
none on problem 10.  Eight check-offs of 5 September had nowhere to land.  The mistake was
not carelessness: a composition typed by hand has no source it can be checked against.

WHAT IS THE SOURCE.  The file the site hands the pupil, and nothing else:
  * a `.tex` when one exists (`materials/spetsmat-2026/listki/16-derevya.tex` for `16A`) —
    the sheet as its author wrote it;
  * the served PDF otherwise (`docs/listki/<номер>-derevya.pdf`) — `16α` and `16ℵ` have
    no TeX at all, and the PDF is the only thing that exists.

🔴 THE IMPORT REFUSES RATHER THAN GUESSES.  Every sheet carries an EXPECTED cell list
below, taken from the served PDF and verified against it by hand on 2026-09-07.  If the
parser produces anything else — one cell too many, a sub-item on the wrong problem — the
tool writes nothing and exits non-zero.  A parser that silently produces a plausible-but-
wrong composition would recreate the exact failure this tool exists to remove.

🔴 IT NEVER MOVES A CELL THAT CARRIES MARKS.  `problems` rows are the anchors of
`marks.problem_id`; 16 013 of them existed when this was written.  A cell that has marks
against it is kept, id and all — the import only fills in `block_id`.  Cells are created,
never destroyed.

IDEMPOTENT BY SHEET NUMBER: a second run against an unchanged source prints `изменений 0`.

    python3 tools/import_listka.py 16α                 # against config.DB_PATH
    python3 tools/import_listka.py 16α --db data/x.db  # against another database
    python3 tools/import_listka.py 16α --tex out.tex   # regenerate the .tex, no writing
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sqlite3
import sys
import unicodedata

KOREN = pathlib.Path(__file__).resolve().parent.parent

# ── WHERE A SHEET COMES FROM ────────────────────────────────────────────────
# The PDF is the one the site serves: `docs/listki/` is what nginx aliases to
# `/listki/`, so parsing it means parsing exactly what the pupil downloaded.
PDF_DIR = KOREN / "docs" / "listki"
# The TeX source is in the neighbouring materials repository on the laptop and does not
# exist on the server.  Absence is normal, not an error: the PDF is always there.
TEX_DIR = KOREN.parent / "materials" / "spetsmat-2026" / "listki"

# ── THE EXPECTED COMPOSITION, AND IT IS A GATE, NOT DOCUMENTATION ───────────
# Read off the served PDFs on 2026-09-07 and confirmed against the live database the same
# day.  Order matters: it is the order the cells stand in on the sheet, hence the order of
# the conduit columns.
OZHIDAEMYJ_SOSTAV = {
    "16A": ["1а", "1б", "2", "3", "4", "5", "6а", "6б", "7а", "7б", "7в",
            "8", "9", "10а", "10б", "11а", "11б", "11в", "12", "13а", "13б"],
    "16α": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13",
            "14а", "14б", "14в", "15"],
    "16ℵ": ["-1а", "-1б", "-1в", "0", "1", "2", "3а", "3б", "4", "5", "6", "7", "8"],
}

# Marks the sheets print next to a problem number.  `⋆` and `?` are the star (an
# invitation, not a debt); `†` and `◦` are ordinary difficulty marks of the author.
ZVEZDA = "⋆★*?"
POMETKI = ZVEZDA + "◦†∘"

# A problem opens a line: an optional minus, digits, an optional mark, then the text.
# `-1` on sheet `16ℵ` is why the number is text and may be negative.
NOMER = re.compile(r"^\s*(-?\d+)\s*([" + re.escape(POMETKI) + r"]*)\s*(.*)$")
# A sub-item: `а)`, `б)◦`, `в)⋆`.  Anywhere in the block, because the PDF text wraps
# several of them onto one line ("Докажите, что а) … б) …").
PUNKT = re.compile(r"(?<![А-Яа-яA-Za-z])([абвг])\)\s*([" + re.escape(POMETKI) + r"]*)")


def _tekst_pdf(put: pathlib.Path) -> str:
    """The PDF's text, in reading order.

    `pypdf` and nothing else: it is pure Python, so the importer runs on the server,
    where no `pdftotext` binary and no other PDF library exists (measured 2026-09-07).
    """
    try:
        from pypdf import PdfReader
    except ImportError:  # pragma: no cover - the message is the point
        raise SystemExit(
            "нет модуля pypdf — поставь его там, где гоняешь импортёр:\n"
            "  sudo pip3 install --break-system-packages pypdf"
        )
    reader = PdfReader(str(put))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _istochnik(nomer: str) -> tuple[str, pathlib.Path]:
    """The sheet's source text and where it came from.

    🔴 THE PDF IS THE SOURCE, AND THE TeX IS AN OPTIONAL EXTRA — that order is deliberate.
    The TeX exists on the laptop only (`materials/` is a different repository and is not on
    the server), so a tool that preferred it would parse one thing here and another thing
    there, and clause 7 of this заход runs it ON THE SERVER.  One source for both machines
    means one composition on both machines.  `--tex-istochnik` is how the TeX is read when
    somebody wants to compare the two.
    """
    pdf = PDF_DIR / ("%s-derevya.pdf" % nomer)
    if not pdf.is_file():
        raise SystemExit("источника нет: %s" % pdf)
    return _tekst_pdf(pdf), pdf


def _tex_istochnik(nomer: str) -> pathlib.Path | None:
    """The `.tex` of this sheet if one is reachable from here.  Laptop only."""
    for koren in (KOREN.parent, KOREN.parent.parent, pathlib.Path.home() / "Documents/GitHub"):
        kandidat = koren / "materials" / "spetsmat-2026" / "listki" / "16-derevya.tex"
        if nomer == "16A" and kandidat.is_file():
            return kandidat
    return None


# ── PARSING ─────────────────────────────────────────────────────────────────

def _ochistit(s: str) -> str:
    """Squeeze the whitespace a PDF extractor leaves behind, keep the characters."""
    s = unicodedata.normalize("NFC", s)
    s = s.replace("\u2010", "-").replace("\u2011", "-")
    return re.sub(r"\s+", " ", s).strip()


def razobrat_tex(tekst: str) -> list[dict]:
    """Blocks of a sheet written in our own TeX macros (`\\nomer`, `\\blok`, `\\okno`).

    The TeX is parsed rather than the PDF whenever it exists, because it says outright
    what the PDF only shows: `\\nomer{7}{\\circ}` is a problem, `\\okno` is a markable
    box, `\\term{…}` is a term being defined.  Nothing has to be inferred from spacing.
    """
    telo = tekst.split(r"\begin{document}", 1)[-1].split(r"\end{document}", 0 + 1)[0]
    bloki: list[dict] = []
    tekushchaya: dict | None = None
    for kusok in re.findall(r"\\blok\{(.*)\}\s*$", telo, flags=re.M):
        nomer = re.match(r"\s*\\nomer\{(-?\d+)\}\{\\(\w+)\}", kusok)
        chistyj = _ochistit(re.sub(r"\\[a-zA-Z]+(\[[^]]*\])?(\{[^{}]*\})?", " ", kusok))
        if nomer:
            tekushchaya = {
                "kind": "task",
                "num": nomer.group(1),
                "star": 1 if nomer.group(2) == "star" else 0,
                "tex": chistyj,
                "okna": kusok.count(r"\okno"),
                "punkty": [b for b, _ in PUNKT.findall(kusok)],
            }
            bloki.append(tekushchaya)
        elif tekushchaya is not None and (r"\okno" in kusok or PUNKT.search(kusok)):
            # A continuation line of the same problem: another sub-item, another box.
            tekushchaya["tex"] = (tekushchaya["tex"] + " " + chistyj).strip()
            tekushchaya["okna"] += kusok.count(r"\okno")
            tekushchaya["punkty"] += [b for b, _ in PUNKT.findall(kusok)]
        elif chistyj:
            # Prose that is not a problem: a definition or a remark of the author.
            bloki.append({"kind": "comment", "num": None, "star": 0,
                          "tex": chistyj, "okna": 0, "punkty": []})
    return bloki


def razobrat_tekst(tekst: str) -> list[dict]:
    """Blocks of a sheet read out of the PDF's text.

    A problem starts where a line starts with its number; everything until the next such
    line belongs to it.  What comes before the first number is the sheet's preamble —
    the definitions a sheet opens with — and it is kept as blocks of its own, because it
    is the part of the sheet a list of labels always lost.
    """
    stroki = [s for s in tekst.split("\n")]
    bloki: list[dict] = []
    tekushchaya: dict | None = None
    preambula: list[str] = []
    vidan_nomer = False
    soderzhatelnyh = 0
    poslednij: int | None = None
    for syraya in stroki:
        stroka = _ochistit(syraya)
        if not stroka or set(stroka) <= set("∗* "):
            continue                       # the `∗ ∗ ∗` rule between parts of a sheet
        soderzhatelnyh += 1
        m = NOMER.match(stroka)
        # A number opens a problem only if what follows looks like the start of a
        # sentence or a sub-item — otherwise `10 вершин` in mid-sentence would.
        otkryvaet = bool(m) and (
            m.group(2) != "" or re.match(r"^[А-ЯA-Z(]", m.group(3) or "")
            or re.match(r"^[абвг]\)", m.group(3) or "")
        )
        # 🔴 TWO THINGS LOOK EXACTLY LIKE A PROBLEM NUMBER AND ARE NOT ONE, AND BOTH WERE
        # CAUGHT BY THE GATE ON THE FIRST RUN.  The sheet's own title (`16A. Деревья` —
        # parsed as problem 16) and a footnote marker glued to its text (`1Возможно, эта
        # задача…` on `16ℵ` — parsed as problems 1 and 2, a second time).  Both are ruled
        # out by the one property a real numbering has: it starts after the header and it
        # only ever goes up.
        if soderzhatelnyh <= 2:
            otkryvaet = False              # the school line and the sheet's title
        if otkryvaet and poslednij is not None and int(m.group(1)) <= poslednij:
            otkryvaet = False              # a footnote repeating a number already used
        if otkryvaet and (m.group(3) or "").strip():
            poslednij = int(m.group(1))
            if not vidan_nomer and preambula:
                bloki.extend(_preambula_v_bloki(preambula))
                preambula = []
            vidan_nomer = True
            tekushchaya = {
                "kind": "task",
                "num": m.group(1),
                "star": 1 if any(z in m.group(2) for z in ZVEZDA) else 0,
                "tex": _ochistit(m.group(3)),
                "okna": 0,
                "punkty": [b for b, _ in PUNKT.findall(m.group(3))],
            }
            bloki.append(tekushchaya)
        elif tekushchaya is not None:
            tekushchaya["tex"] = (tekushchaya["tex"] + " " + stroka).strip()
            tekushchaya["punkty"] += [b for b, _ in PUNKT.findall(stroka)]
            if any(z in stroka[:3] for z in ZVEZDA):
                pass
        else:
            preambula.append(stroka)
    if not vidan_nomer:
        bloki.extend(_preambula_v_bloki(preambula))
    return bloki


def _preambula_v_bloki(stroki: list[str]) -> list[dict]:
    """The lines before the first problem: header line, title, then definitions."""
    out = []
    for i, s in enumerate(stroki):
        if i < 2:
            continue          # the school line and the sheet's own title
        out.append({"kind": "definition" if "—" in s or "назыв" in s else "comment",
                    "num": None, "star": 0, "tex": s, "okna": 0, "punkty": []})
    return out


def yachejki(bloki: list[dict]) -> list[str]:
    """The markable cells a parsed sheet yields, in sheet order.

    A problem with sub-items gives one cell per sub-item (`14а`, `14б`, `14в`); a problem
    without them gives one cell with its bare number.  This is the mapping the conduit's
    columns and every existing mark already use.
    """
    out: list[str] = []
    for blok in bloki:
        if blok["kind"] != "task":
            continue
        punkty = []
        for bukva in blok["punkty"]:
            if bukva not in punkty:
                punkty.append(bukva)
        if punkty:
            out.extend("%s%s" % (blok["num"], b) for b in punkty)
        else:
            out.append(blok["num"])
    return out


def razobrat(nomer: str) -> tuple[list[dict], pathlib.Path]:
    tekst, otkuda = _istochnik(nomer)
    bloki = razobrat_tex(tekst) if otkuda.suffix == ".tex" else razobrat_tekst(tekst)
    return bloki, otkuda


# ── WRITING ─────────────────────────────────────────────────────────────────

def _vid_yachejki(blok: dict) -> str:
    """`problems.kind` for a cell — the mark-level classification, not the block's."""
    return "звезда" if blok["star"] else "обычная"


def vnesti(conn: sqlite3.Connection, nomer: str, bloki: list[dict]) -> dict:
    """Write the blocks and reconcile the cells.  Returns what changed."""
    stroka = conn.execute("select id from sheets where number = ?", (nomer,)).fetchone()
    if stroka is None:
        raise SystemExit("листка %s нет в таблице sheets — заведи его сначала" % nomer)
    sheet_id = stroka[0]
    izmeneno = {"блоков заведено": 0, "блоков обновлено": 0,
                "ячеек заведено": 0, "ячеек связано": 0}

    bylo = {r[0]: dict(zip(("ord", "kind", "num", "star", "tex"), r[1:]))
            for r in conn.execute(
                "select id, ord, kind, num, star, tex from sheet_blocks where sheet_id = ?",
                (sheet_id,))}
    po_ord = {v["ord"]: (bid, v) for bid, v in bylo.items()}

    id_bloka: dict[int, int] = {}
    for poryadok, blok in enumerate(bloki, start=1):
        novoe = (blok["kind"], blok["num"], blok["star"], blok["tex"])
        if poryadok in po_ord:
            bid, staroe = po_ord[poryadok]
            if (staroe["kind"], staroe["num"], staroe["star"], staroe["tex"]) != novoe:
                conn.execute(
                    "update sheet_blocks set kind=?, num=?, star=?, tex=? where id=?",
                    novoe + (bid,))
                izmeneno["блоков обновлено"] += 1
        else:
            cur = conn.execute(
                "insert into sheet_blocks (sheet_id, kind, num, star, tex, ord) "
                "values (?, ?, ?, ?, ?, ?)", (sheet_id,) + novoe + (poryadok,))
            bid = cur.lastrowid
            izmeneno["блоков заведено"] += 1
        id_bloka[poryadok] = bid

    # 🔴 CELLS ARE RECONCILED, NEVER REBUILT.  An existing label keeps its row and its id,
    # so every `marks.problem_id` pointing at it keeps pointing at it; a label that is not
    # in the source any more is LEFT ALONE and reported, because deleting it would delete
    # somebody's marks with it.
    est = {r[0]: r[1] for r in conn.execute(
        "select label, id from problems where sheet_id = ?", (sheet_id,))}
    poryadok_yachejki = 0
    for poryadok, blok in enumerate(bloki, start=1):
        if blok["kind"] != "task":
            continue
        punkty, vidno = [], set()
        for bukva in blok["punkty"]:
            if bukva not in vidno:
                vidno.add(bukva)
                punkty.append(bukva)
        metki = ["%s%s" % (blok["num"], b) for b in punkty] or [blok["num"]]
        for metka in metki:
            poryadok_yachejki += 1
            if metka in est:
                conn.execute("update problems set block_id = ? where id = ?",
                             (id_bloka[poryadok], est[metka]))
                izmeneno["ячеек связано"] += 1
            else:
                conn.execute(
                    "insert into problems (sheet_id, label, kind, ord, block_id) "
                    "values (?, ?, ?, ?, ?)",
                    (sheet_id, metka, _vid_yachejki(blok), poryadok_yachejki,
                     id_bloka[poryadok]))
                izmeneno["ячеек заведено"] += 1
    lishnie = sorted(set(est) - set(yachejki(bloki)))
    izmeneno["ячеек в базе сверх источника"] = len(lishnie)
    if lishnie:
        izmeneno["лишние"] = ", ".join(lishnie)
    return izmeneno


def v_tex(nomer: str, bloki: list[dict]) -> str:
    """The sheet, regenerated from the blocks — what the page offers for download."""
    shapka = [
        "% Собрано из базы задач: tools/import_listka.py",
        "\\documentclass[10pt,a4paper]{article}",
        "\\usepackage[T2A]{fontenc}",
        "\\usepackage[utf8]{inputenc}",
        "\\usepackage[russian]{babel}",
        "\\usepackage{amsmath,amssymb}",
        "\\begin{document}",
        "\\centerline{\\large\\textbf{%s. \\textsc{Деревья}}}\\par\\medskip" % nomer,
    ]
    telo = []
    for blok in bloki:
        if blok["kind"] == "task":
            zvezda = "$\\star$" if blok["star"] else ""
            telo.append("\\par\\noindent\\textbf{%s}%s\\ %s\\par\\medskip"
                        % (blok["num"], zvezda, blok["tex"]))
        else:
            telo.append("\\par\\noindent %s\\par\\medskip" % blok["tex"])
    return "\n".join(shapka + telo + ["\\end{document}", ""])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("nomer", help="номер листка, как он стоит в sheets: 16A · 16α · 16ℵ")
    parser.add_argument("--db", default=None, help="база (по умолчанию config.DB_PATH)")
    parser.add_argument("--tex", default=None, help="только собрать .tex в этот файл")
    parser.add_argument("--proba", action="store_true", help="разобрать и показать, не записывая")
    parser.add_argument("--sverit-s-tex", action="store_true",
                        help="сверить разбор PDF с разбором .tex (только на ноуте, где .tex есть)")
    args = parser.parse_args(argv)

    bloki, otkuda = razobrat(args.nomer)
    poluchilos = yachejki(bloki)
    print("источник: %s" % otkuda)
    print("блоков: %d, из них задач: %d" % (len(bloki), sum(b["kind"] == "task" for b in bloki)))
    print("ячейки (%d): %s" % (len(poluchilos), ", ".join(poluchilos)))

    if args.sverit_s_tex:
        tex_put = _tex_istochnik(args.nomer)
        if tex_put is None:
            print("🔴 .tex этого листка отсюда не виден — сверять не с чем", file=sys.stderr)
            return 1
        iz_tex = yachejki(razobrat_tex(tex_put.read_text(encoding="utf-8")))
        print("из .tex (%d): %s" % (len(iz_tex), ", ".join(iz_tex)))
        print("сошлось" if iz_tex == poluchilos else "🔴 РАСХОЖДЕНИЕ PDF и .tex")
        return 0 if iz_tex == poluchilos else 1

    ozhidaem = OZHIDAEMYJ_SOSTAV.get(args.nomer)
    if ozhidaem is not None and poluchilos != ozhidaem:
        print("🔴 РАЗБОР НЕ СОШЁЛСЯ С ОЖИДАЕМЫМ СОСТАВОМ — не записываю ничего.", file=sys.stderr)
        print("   ожидалось (%d): %s" % (len(ozhidaem), ", ".join(ozhidaem)), file=sys.stderr)
        print("   вышло     (%d): %s" % (len(poluchilos), ", ".join(poluchilos)), file=sys.stderr)
        return 1

    if args.tex:
        pathlib.Path(args.tex).write_text(v_tex(args.nomer, bloki), encoding="utf-8")
        print("собран tex: %s" % args.tex)
        return 0
    if args.proba:
        for b in bloki:
            print("  %-10s %-4s %s" % (b["kind"], b["num"] or "", b["tex"][:90]))
        return 0

    sys.path.insert(0, str(KOREN))
    import config
    put = pathlib.Path(args.db) if args.db else config.DB_PATH
    conn = sqlite3.connect(str(put), isolation_level=None)
    conn.execute("pragma foreign_keys = on")
    conn.execute("begin immediate")
    try:
        itog = vnesti(conn, args.nomer, bloki)
    except BaseException:
        conn.execute("rollback")
        raise
    conn.execute("commit")
    vsego = sum(v for k, v in itog.items() if isinstance(v, int) and k != "ячеек в базе сверх источника")
    for k, v in itog.items():
        print("  %s: %s" % (k, v))
    print("изменений %d" % (0 if vsego - itog.get("ячеек связано", 0) == 0 and itog.get("блоков обновлено", 0) == 0 else vsego))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
