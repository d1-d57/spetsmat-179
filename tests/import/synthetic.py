"""A SYNTHETIC conduit, so that these tests run on a machine that does not have last
year's workbook.

The real book is the personal data of fifty-six children.  It is not in the repository and
never will be, so a test suite that could only run beside it would be a test suite almost
nobody could run -- including CI, including the next заход, including the acceptance pass.
The fixture below therefore builds a small workbook with openpyxl that reproduces every
STRUCTURAL feature the importer has to cope with:

  * all four column layouts, including the ``1д`` shape where the header IS row 1;
  * every value of ``VALUE_REGISTRY``: 1, 'x', empty, and a quarantined one;
  * a student who arrives late and therefore has no row on the first sheet;
  * a composite receiver, and a senior who is named in the seed and is not a teacher.

``tests/import/test_real_workbook.py`` runs the same checks against the real book when it
happens to be present, and skips when it is not.

This is a PLAIN MODULE and not a package: ``tests/import/`` cannot carry an ``__init__.py``
because ``import`` is a Python keyword and ``tests.import`` is therefore not a name any
import statement can spell.  pytest puts this directory on ``sys.path`` instead, so both
``conftest.py`` and the test modules reach it as ``import synthetic``.
"""

from __future__ import annotations

import csv
import json


import config


SYNTHETIC_SHEETS = [
    {
        "number": "1",
        "title": "1. Первый",
        "ord": 1,
        "layout": "old",
        "tasks": [
            {"label": "1а°", "kind": "обязательная", "ord": 1},
            {"label": "2", "kind": "обычная", "ord": 2},
            {"label": "3*", "kind": "звезда", "ord": 3},
        ],
    },
    {
        "number": "9",
        "title": "9. Второй",
        "ord": 2,
        "layout": "new",
        "tasks": [
            {"label": "1°", "kind": "обязательная", "ord": 1},
            {"label": "2а", "kind": "обычная", "ord": 2},
        ],
    },
    {
        "number": "1д",
        "title": "1д. Третий",
        "ord": 3,
        "layout": "d",
        "tasks": [
            {"label": "1", "kind": "обычная", "ord": 1},
            {"label": "2**", "kind": "двойная", "ord": 2},
        ],
    },
]

#: (surname, name, class, first sheet they have a row on)
SYNTHETIC_STUDENTS = [
    ("Первов", "Пётр", "9К", "1"),
    ("Второва", "Вера", "9К", "1"),
    ("Позднев", "Павел", "9Л", "9"),   # arrives late: no row on sheet '1'
]

SYNTHETIC_TEACHERS = [
    # name, aka, senior_aka
    ("Аня", "АН", "НС"),          # НС is a senior with no teacher row -- hole (a) of §6
    ("Борис Петрович", "БП", "АН"),
    ("Ольга Александровна", "ОР", "АН"),
]

#: Row-by-row marks: (sheet, student index, label) -> raw cell value.
SYNTHETIC_MARKS = {
    ("1", 0, "1а°"): 1.0,
    ("1", 0, "2"): "x",
    ("1", 1, "1а°"): 1.0,
    ("1", 1, "2"): 1.0,
    ("1", 1, "3*"): 1.0,
    ("9", 0, "1°"): 1.0,
    ("9", 1, "1°"): 2.0,          # the quarantined value
    ("9", 2, "1°"): 1.0,
    ("9", 2, "2а"): "x",
    ("1д", 2, "1"): 1.0,
}

#: Who received each student's problems on each sheet.  One composite on purpose.
SYNTHETIC_RECEIVERS = {
    ("1", 0): "Аня",
    ("1", 1): "Борис Петрович/Ольга Александровна",
    ("9", 0): "Аня",
    ("9", 1): "Аня",
    ("9", 2): "Борис Петрович",
}


def _rows_of(sheet_number):
    """Which students have a row on this sheet.  Позднев has none on sheet '1'."""
    return [
        index
        for index, (_surname, _name, _klass, first) in enumerate(SYNTHETIC_STUDENTS)
        if sheet_number != "1" or first == "1"
    ]


def build_workbook(path, *, extra_value=None):
    """Write the synthetic conduit to ``path``.

    ``extra_value`` puts one unregistered value into the grid, which is how the test for
    "the inventory fails on the unknown" gets an unknown to fail on.
    """
    import openpyxl

    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)

    for sheet in SYNTHETIC_SHEETS:
        worksheet = workbook.create_sheet(sheet["number"])
        labels = [task["label"] for task in sheet["tasks"]]

        if sheet["layout"] == "old":
            header_row, surname_column, name_column = 3, 3, 4
            first_column = 5
            worksheet.cell(1, 1, sheet["title"])
            worksheet.cell(header_row, 2, "принимающий")
            receiver_column = 2
        elif sheet["layout"] == "new":
            header_row, surname_column, name_column = 3, 1, 2
            first_column = 5
            worksheet.cell(1, 1, sheet["title"])
            worksheet.cell(header_row, 3, "закрыт")
            worksheet.cell(header_row, 4, "принимающий")
            receiver_column = 4
        else:  # the '1д' shape: THE HEADER IS ROW 1
            header_row, surname_column, name_column = 1, 3, 4
            first_column = 5
            worksheet.cell(1, 1, sheet["title"])
            worksheet.cell(1, 2, "принимающий")
            receiver_column = 2

        worksheet.cell(header_row, surname_column, "фамилия")
        worksheet.cell(header_row, name_column, "имя")
        for offset, label in enumerate(labels):
            worksheet.cell(1, first_column + offset, label)
            if header_row > 1:
                worksheet.cell(header_row, first_column + offset,
                               "°" if "°" in label else "✓")

        row = header_row + 1
        for index in _rows_of(sheet["number"]):
            surname, name, _klass, _first = SYNTHETIC_STUDENTS[index]
            worksheet.cell(row, surname_column, surname)
            worksheet.cell(row, name_column, name)
            receiver = SYNTHETIC_RECEIVERS.get((sheet["number"], index))
            if receiver:
                worksheet.cell(row, receiver_column, receiver)
            for offset, label in enumerate(labels):
                value = SYNTHETIC_MARKS.get((sheet["number"], index, label))
                if value is not None:
                    worksheet.cell(row, first_column + offset, value)
            row += 1

        if extra_value is not None and sheet["number"] == "1":
            worksheet.cell(header_row + 1, first_column + 2, extra_value)

    # The three summary sheets the oracles read.
    graveyard = workbook.create_sheet("гробарий")
    graveyard.cell(1, 1, "листок")
    graveyard.cell(1, 2, "задача")
    # '3*' on sheet 1 was solved by exactly one student: Второва.
    graveyard.cell(2, 1, "[1]")
    graveyard.cell(2, 2, "3*")
    graveyard.cell(2, 3, "✘")
    graveyard.cell(2, 4, "Второва")

    debts = workbook.create_sheet("долги")
    debts.cell(1, 5, 1.0)
    debts.cell(1, 6, 9.0)
    for offset, (surname, _name, _klass, _first) in enumerate(SYNTHETIC_STUDENTS):
        debts.cell(2 + offset, 1, surname)
    # sheet '1' has one obligatory problem, 1а°: solved by Первов and Второва.
    debts.cell(2, 5, "✓")
    debts.cell(3, 5, "✓")
    debts.cell(4, 5, "✓")   # Позднев arrives later and is not charged sheet '1'
    # sheet '9' has one obligatory problem, 1°: Первов solved, Второва quarantined, Позднев solved
    debts.cell(2, 6, "✓")
    debts.cell(3, 6, 1)
    debts.cell(4, 6, "✓")

    credit = workbook.create_sheet("зачёт")
    for offset, (surname, name, _klass, _first) in enumerate(SYNTHETIC_STUDENTS):
        credit.cell(2 + offset, 2, surname)
        credit.cell(2 + offset, 3, name)

    workbook.save(path)
    return path


def build_seed(directory):
    """Write the synthetic seed beside the synthetic workbook."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "sheets.json").write_text(
        json.dumps(SYNTHETIC_SHEETS, ensure_ascii=False), encoding="utf-8"
    )
    with (directory / "students.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["surname", "name", "class", "technical", "first_sheet",
                         "sheets_present"])
        for surname, name, klass, first in SYNTHETIC_STUDENTS:
            writer.writerow([surname, name, klass, 0, first, 3 if first == "1" else 2])
    with (directory / "teachers.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["name", "aka", "students_count", "students_actual", "senior_aka",
                         "room", "technical"])
        for name, aka, senior in SYNTHETIC_TEACHERS:
            writer.writerow([name, aka, 3, 3, senior, "302", 0])
    return directory
