"""Генератор печатного бланка приёма задач.

WHAT CHANGED HERE, AND WHY IT IS THE WHOLE POINT OF THIS FILE
-------------------------------------------------------------

The previous version printed «Петров В.» down the left-hand column.  A photograph of
that sheet is a photograph of the names of fifty-six children, and sending it to a model
hosted abroad is a cross-border transfer of personal data (§4 of the brief).  **The form
now carries CODES** -- `u17`, never a surname -- so the image has no personal data in it
and there is no object of regulation at all.  Matching a code back to a child happens on
the server, against a catalogue that never leaves it.

That is not a promise made in a docstring.  ``draw_form`` returns every string it drew,
``--proba`` cross-checks that list against the surnames and given names in
``seed/students.csv``, and the command exits **1** if a single one of them reached the
page.  A check that cannot go red is not a check.

THE KEY IS A SEPARATE SHEET, AND IT IS NEVER PHOTOGRAPHED.  A grid of codes is unusable
on its own -- the teacher has to know which row is which child.  ``--kluch`` prints that
mapping on its own sheet, which lives on the desk and is not what the camera is pointed
at.  Two sheets instead of one is the price of the boundary in §4, and it is a small
price: the key is printed once a term, the grid is printed every lesson.

WHY A PRINTED GRID AT ALL (§1).  Surname and sheet number are printed once, at the top;
the task numbers are printed in a header row.  There is nowhere left to confuse a
handwritten 7 with a 5, because the only handwriting on the page is a tick inside a box
whose meaning is fixed by its coordinates.  Most of the recognition problem is removed
before the model sees anything.

    python3 tools/blank.py --proba                 # a probe run + the numbers it reached
    python3 tools/blank.py --sheet 12 --room 302   # the form for a real lesson
    python3 tools/blank.py --kluch                 # the code -> child key, desk copy
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402  -- after the path insert, so a bare checkout works
from core.services.raspoznavanie import code_for_student  # noqa: E402

W, H = 1654, 2339            # A4 при 200 dpi
MARGIN = 70
ROW_H = 46
COL_W = 62

#: The left-hand column holds a code, not a name, so it needs a fraction of the width the
#: old one did.  The space goes back to the grid: more task columns fit on one sheet.
CODE_W = 150

#: One printed sheet holds one teaching group.  Eighteen is the size of a room in this
#: school; more than that and the boxes fall below the size a tick fits in.
ROWS_PER_FORM = 18

#: Where a generated sheet goes when the caller names no ``--out``.  OUTSIDE the
#: repository, and that is the point rather than tidiness.  Two reasons, and the second
#: one is the serious one:
#:
#:   * ``tools/proba/blank.png`` is a sample committed by P0.  A probe run that
#:     overwrites it dirties a tracked file nobody asked this position to change.
#:   * ``--kluch`` draws the key, and the key is the one sheet in this whole design that
#:     DOES carry the names of children.  A default that wrote it under the checkout
#:     would put fifty-six surnames one ``git add -A`` away from a public history --
#:     permanently, because git does not forget.  §4 is a boundary about where personal
#:     data may go, and a repository is one of the places it may not.
OUT_DIR = Path(tempfile.gettempdir())


def font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/System/Library/Fonts/Supplemental/Arial.ttf",
              "/Library/Fonts/Arial.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def draw_form(codes, labels, sheet_no, room, out):
    """Draw the form and return ``(path, drawn)`` where ``drawn`` is every string on it.

    Returning the strings is what makes the «0 surnames» claim checkable from outside:
    the caller compares the list against the roster instead of reading this file and
    believing it.
    """
    drawn = []

    def text(xy, value, fnt, fill="black"):
        drawn.append(str(value))
        d.text(xy, str(value), font=fnt, fill=fill)

    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    f_head, f_cell, f_code = font(38), font(22), font(28)

    text((MARGIN, 40), "Листок %s" % sheet_no, f_head)
    text((W - MARGIN - 420, 48), "кабинет %s    дата ________" % room, f_cell)

    top = 120
    x0 = MARGIN + CODE_W
    for j, lab in enumerate(labels):
        text((x0 + j * COL_W + 10, top - 34), lab, f_cell)

    for i, code in enumerate(codes):
        y = top + i * ROW_H
        text((MARGIN + 8, y + 9), code, f_code)
        d.line([(MARGIN, y), (x0 + len(labels) * COL_W, y)], fill="#999", width=1)
        for j in range(len(labels)):
            d.rectangle([x0 + j * COL_W, y, x0 + (j + 1) * COL_W, y + ROW_H], outline="#999")

    y_end = top + len(codes) * ROW_H
    d.line([(MARGIN, y_end), (x0 + len(labels) * COL_W, y_end)], fill="#999", width=1)
    d.line([(x0, top - 6), (x0, y_end)], fill="#333", width=2)
    text((MARGIN, y_end + 24),
         "Сдал — крестик в клетке. Снято — прочерк. Пусто — не сдавал.", f_cell, "#444")
    text((MARGIN, y_end + 58),
         "Слева — код ученика. Кто под каким кодом — на отдельном листе-ключе, "
         "его не фотографируют.", f_cell, "#444")

    Path(out).parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG")
    return out, drawn


def draw_key(pairs, out):
    """The desk copy: code -> child.  Local paper, never photographed, never uploaded."""
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    f_head, f_row = font(38), font(30)
    d.text((MARGIN, 40), "Ключ: код — ученик", font=f_head, fill="black")
    d.text((MARGIN, 92), "Этот лист НЕ фотографируют.", font=font(24), fill="#a00")
    for i, (code, who) in enumerate(pairs):
        d.text((MARGIN, 150 + i * 52), "%-6s %s" % (code, who), font=f_row, fill="black")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG")
    return out


# --------------------------------------------------------------------- where rows come from

def roster_from_catalogue(db_path):
    """``[(code, "Фамилия И."), ...]`` из живого каталога, если база есть.

    Production path: the code is built from the student's real database id, so a mark
    read off the paper lands on the row the journal knows.
    """
    from infra.db import connect
    from infra.repositories import SqliteCatalogue

    connection = connect(db_path)
    # 🔴 ПЕРВОЙ СТРОКОЙ — ОТКУДА ЧИСЛА (Д1, владелец 10.09). Путь и дата последней
    # ЗАПИСИ внутри базы; красное, если база старше последнего занятия. Дата ФАЙЛА
    # для этого не годится: копирование и rsync её обновляют, не добавив ни строки.
    try:                                  # запуск и модулем, и файлом из tools/
        from core.istochnik import nazvat_i_proverit
    except ModuleNotFoundError:           # прямой запуск: корня репозитория нет в sys.path
        import sys as _s, pathlib as _p
        _s.path.insert(0, str(_p.Path(__file__).resolve().parent.parent))
        from core.istochnik import nazvat_i_proverit
    nazvat_i_proverit(connection)
    try:
        students = [s for s in SqliteCatalogue(connection).students() if s.status != "left"]
    finally:
        connection.close()
    return [
        (code_for_student(s.id), ("%s %s." % (s.surname, s.name[:1])).strip())
        for s in students
    ]


def roster_from_seed(seed_dir):
    """``[(code, "Фамилия И."), ...]`` из ``seed/students.csv`` — для прогона без базы.

    The id here is the CSV position, not a database id, so this source is honest only for
    a probe run: ``--proba`` says so out loud rather than letting the two be confused.
    """
    rows = []
    path = Path(seed_dir) / "students.csv"
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as fh:
        for record in csv.DictReader(fh):
            if str(record.get("technical", "")).strip().lower() in ("1", "true", "да"):
                continue
            rows.append(record)
    return [
        (code_for_student(i + 1), ("%s %s." % (r["surname"], r["name"][:1])).strip())
        for i, r in enumerate(rows)
    ]


def labels_of_sheet(seed_dir, number):
    """The task labels of one sheet, in ``ord`` order, straight out of the seed.

    Read from ``seed/sheets.json`` rather than typed into this file: the labels are data
    (``10а°``, ``5б``, ``10а:)``), they differ per sheet, and a hand-copied list is a
    second source of truth that silently rots.
    """
    path = Path(seed_dir) / "sheets.json"
    if not path.exists():
        return []
    sheets = json.loads(path.read_text(encoding="utf-8"))
    chosen = next((s for s in sheets if str(s.get("number")) == str(number)), None)
    if chosen is None:
        return []
    tasks = sorted(chosen.get("tasks", []), key=lambda t: t.get("ord", 0))
    return [t["label"] for t in tasks]


def personal_words(seed_dir):
    """Every surname and given name in the roster, as the set the form must not contain."""
    words = set()
    path = Path(seed_dir) / "students.csv"
    if not path.exists():
        return words
    with path.open(encoding="utf-8") as fh:
        for record in csv.DictReader(fh):
            for field in ("surname", "name"):
                value = (record.get(field) or "").strip()
                if len(value) > 2:
                    words.add(value.lower())
    return words


def surnames_on_form(drawn, words):
    """Which personal words reached the page.  Empty is the only acceptable answer.

    Substring rather than equality: a name is a leak whether it stands alone in a cell or
    inside «сдал Петров», and the point is to catch the leak, not to be pedantic about
    where it sat.
    """
    haystack = " ".join(drawn).lower()
    return sorted(word for word in words if word in haystack)


# ------------------------------------------------------------------------------- cli

def main(argv=None):
    parser = argparse.ArgumentParser(description="печатный бланк приёма задач")
    parser.add_argument("--proba", action="store_true",
                        help="пробный прогон: собрать бланк и напечатать числа")
    parser.add_argument("--kluch", action="store_true",
                        help="напечатать лист-ключ «код — ученик» (его не фотографируют)")
    parser.add_argument("--sheet", default="1", help="номер листка")
    parser.add_argument("--room", default="302", help="кабинет")
    parser.add_argument("--out", default=None, help="куда сохранить png")
    parser.add_argument("--db", default=None, help="путь к базе; без него — seed/")
    args = parser.parse_args(argv)

    seed_dir = config.SEED_DIR
    db_path = Path(args.db) if args.db else config.DB_PATH
    if db_path.exists():
        roster, source = roster_from_catalogue(db_path), "каталог %s" % db_path
    else:
        roster, source = roster_from_seed(seed_dir), "seed/students.csv (позиции, не id базы)"
    roster = roster[:ROWS_PER_FORM]

    labels = labels_of_sheet(seed_dir, args.sheet)
    if not labels:
        print("нет листка %s в seed/sheets.json — печатать нечего" % args.sheet)
        return 1

    if args.kluch:
        out = args.out or OUT_DIR / "spetsmat-kluch.png"
        print("ключ (НЕ фотографировать):", draw_key(roster, out))
        return 0

    out = args.out or OUT_DIR / "spetsmat-blank.png"
    path, drawn = draw_form([code for code, _ in roster], labels, args.sheet, args.room, out)

    if not args.proba:
        print("бланк:", path)
        return 0

    leaked = surnames_on_form(drawn, personal_words(seed_dir))
    print("бланк: %s" % path)
    print("источник строк: %s" % source)
    print("кодов на бланке: %d" % len(roster))
    print("задач на бланке: %d" % len(labels))
    print("фамилий на бланке: %d" % len(leaked))
    if leaked:
        print("🔴 на бланк попало личное: %s" % ", ".join(leaked))
        return 1
    print("строк текста на бланке проверено: %d из %d" % (len(drawn), len(drawn)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
