"""Loading the anonymised seed -- sheets, problems, students, teachers -- into a database.

THE SEED IS THE CATALOGUE, THE WORKBOOK IS THE EVENTS.  ``seed/sheets.json``,
``seed/students.csv`` and ``seed/teachers.csv`` live in git and carry no marks; last
year's conduit lives outside the repository and carries nothing but marks.  Keeping the
two apart is why the personal data of fifty-six children never has to enter the
repository for the importer to be runnable and testable by someone who does not have the
book at all.

Nothing here imports sqlite3-specific behaviour beyond the DB-API connection it is
handed, and nothing here knows about openpyxl: the importer in ``tools/`` is an adapter
BESIDE this service, not a rewrite of it.

IDEMPOTENT BY CONSTRUCTION.  Seeding twice must not double the catalogue -- the importer
is going to be re-run during a season, and a second run that silently produces 1088
problems would be discovered by the projections rather than by the loader.  Every insert
here is keyed on the natural key the schema already declares unique (``sheets.number``,
``problems (sheet_id, label)``) or, where the schema declares none, on the key this
module states out loud (``(surname, name)`` for a student, ``name`` for a teacher).
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import config


class SeedError(Exception):
    """The seed on disk does not say what the schema requires."""


# ------------------------------------------------------- the one repair, stated out loud
#
# ``seed/sheets.json`` -- and the workbook it was derived from -- carries the label ``12д``
# TWICE on sheet ``2д``, at columns 28 and 30.  The schema declares ``unique (sheet_id,
# label)``, so the seed as it stands cannot be loaded at all: the load stops on the second
# insert and the catalogue is left half-built.
#
# The reading is not a guess.  Columns 25..31 are a complete seven-column run whose labels
# should be ``12а 12б 12в 12г 12д 12е 12ж``; what is written is ``12а 12б 12в 12д 12е 12д
# 12ж``.  Exactly one letter of the run -- ``г`` -- is absent, and the run first departs
# from the alphabet at the fourth column.  ``12г`` at column 28 is the only assignment that
# makes the run whole, and anyone can re-check it by reading row 1 of sheet ``2д``.
#
# It costs nothing to be wrong about which of the two columns is which: BOTH columns are
# empty over all 55 students, so no mark can be misattributed by this repair.  That was
# measured, not assumed.
#
# The registry is explicit for the same reason the importer's value registry is: a
# duplicate that is NOT listed here raises.  A silent "keep the first one" would drop a
# problem out of the 544 and would look exactly like a clean load.
DUPLICATE_LABEL_REPAIRS = {
    # (sheet number, duplicated label, 0-based occurrence): the label to use instead
    ("2д", "12д", 0): "12г",
}


@dataclass(frozen=True)
class SeedCounts:
    """What one seeding run put into the database, so a caller can print real numbers.

    ``*_seen`` counts the rows the seed offered; ``*_written`` counts the rows that were
    actually inserted.  On a second run every ``written`` is zero, which is the cheapest
    possible proof that the load is idempotent -- and a caller that printed only "seeded
    56 students" could not tell a fresh load from a doubled one.
    """

    sheets_seen: int = 0
    sheets_written: int = 0
    problems_seen: int = 0
    problems_written: int = 0
    students_seen: int = 0
    students_written: int = 0
    teachers_seen: int = 0
    teachers_written: int = 0

    def __str__(self) -> str:
        return (
            "листков %d (новых %d) · задач %d (новых %d) · "
            "учеников %d (новых %d) · преподавателей %d (новых %d)"
            % (
                self.sheets_seen, self.sheets_written,
                self.problems_seen, self.problems_written,
                self.students_seen, self.students_written,
                self.teachers_seen, self.teachers_written,
            )
        )


# --------------------------------------------------------------------------- reading


def read_sheets(seed_dir: Optional[Path] = None) -> list:
    """``seed/sheets.json`` as a list of dicts, validated against ``config.PROBLEM_KINDS``.

    Validated HERE and not at insert time: the CHECK constraint in the schema would also
    refuse a bad kind, but it would refuse it halfway through a load, leaving the caller
    to reason about a partly-filled catalogue.  A seed file is small enough to be judged
    whole before the first insert.
    """
    path = Path(seed_dir or config.SEED_DIR) / "sheets.json"
    if not path.exists():
        raise SeedError("нет файла засева: %s" % path)
    sheets = json.loads(path.read_text(encoding="utf-8"))

    seen_numbers = set()
    for sheet in sheets:
        for field in ("number", "ord", "tasks"):
            if field not in sheet:
                raise SeedError("листок без поля %r: %r" % (field, sheet))
        if sheet["number"] in seen_numbers:
            raise SeedError("листок %r встречается дважды" % sheet["number"])
        seen_numbers.add(sheet["number"])

        seen_labels = set()
        occurrences = {}
        for task in sheet["tasks"]:
            if task.get("kind") not in config.PROBLEM_KINDS:
                raise SeedError(
                    "неизвестный тип задачи %r на листке %r; известные: %s"
                    % (task.get("kind"), sheet["number"], ", ".join(config.PROBLEM_KINDS))
                )
            raw = task["label"]
            index = occurrences.get(raw, 0)
            occurrences[raw] = index + 1
            key = (sheet["number"], raw, index)
            if key in DUPLICATE_LABEL_REPAIRS:
                task["label"] = DUPLICATE_LABEL_REPAIRS[key]
                task["repaired_from"] = raw
            if task["label"] in seen_labels:
                raise SeedError(
                    "задача %r встречается на листке %r дважды, и это НЕ описано в "
                    "DUPLICATE_LABEL_REPAIRS; схема запрещает unique (sheet_id, label), "
                    "поэтому засев остановлен, а не загружен наполовину"
                    % (task["label"], sheet["number"])
                )
            seen_labels.add(task["label"])
    return sheets


def repairs_applied(sheets: list) -> list:
    """Every label this load rewrote, so the caller can print it instead of hiding it."""
    return [
        (sheet["number"], task["repaired_from"], task["label"])
        for sheet in sheets
        for task in sheet["tasks"]
        if "repaired_from" in task
    ]


def read_students(seed_dir: Optional[Path] = None) -> list:
    """``seed/students.csv`` as a list of dicts.

    The file already carries a ``first_sheet`` column.  It is READ but never used as the
    value written to the database: ``tools/import_konduit.py`` computes ``first_sheet_id``
    from the book itself and compares the two, because a seed column that agrees with
    itself proves nothing and a disagreement is a finding (§7 of the задание).
    """
    return _read_csv(Path(seed_dir or config.SEED_DIR) / "students.csv",
                     required=("surname", "name"))


def read_teachers(seed_dir: Optional[Path] = None) -> list:
    """``seed/teachers.csv`` as a list of dicts."""
    return _read_csv(Path(seed_dir or config.SEED_DIR) / "teachers.csv",
                     required=("name",))


def _read_csv(path: Path, *, required: tuple) -> list:
    if not path.exists():
        raise SeedError("нет файла засева: %s" % path)
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SeedError("пустой файл засева: %s" % path)
    for row in rows:
        for field in required:
            if not (row.get(field) or "").strip():
                raise SeedError("строка без поля %r в %s: %r" % (field, path.name, row))
    return rows


# --------------------------------------------------------------------------- writing


def seed_catalogue(
    connection,
    seed_dir: Optional[Path] = None,
    *,
    issued_at: str = "2025-09-01",
) -> SeedCounts:
    """Put the whole seed into a migrated database and report what was written.

    ``issued_at`` is a column the schema requires and the seed does not carry: last
    year's sheets have no issue dates recorded anywhere in the book.  One honest
    placeholder date for the whole imported season beats fifty-four invented ones, and it
    is a parameter rather than a literal so that a caller who DOES know the dates can
    pass them without editing this file.
    """
    sheets = read_sheets(seed_dir)
    students = read_students(seed_dir)
    teachers = read_teachers(seed_dir)

    counts = {
        "sheets_seen": len(sheets),
        "sheets_written": 0,
        "problems_seen": sum(len(sheet["tasks"]) for sheet in sheets),
        "problems_written": 0,
        "students_seen": len(students),
        "students_written": 0,
        "teachers_seen": len(teachers),
        "teachers_written": 0,
    }

    for sheet in sheets:
        sheet_id = _sheet_id(connection, sheet["number"])
        if sheet_id is None:
            cursor = connection.execute(
                "insert into sheets (number, title, issued_at, ord) values (?, ?, ?, ?)",
                (sheet["number"], sheet.get("title"), issued_at, sheet["ord"]),
            )
            sheet_id = cursor.lastrowid
            counts["sheets_written"] += 1
        for task in sheet["tasks"]:
            standing = connection.execute(
                "select id from problems where sheet_id = ? and label = ?",
                (sheet_id, task["label"]),
            ).fetchone()
            if standing is None:
                connection.execute(
                    "insert into problems (sheet_id, label, kind, ord) values (?, ?, ?, ?)",
                    (sheet_id, task["label"], task["kind"], task["ord"]),
                )
                counts["problems_written"] += 1

    for row in teachers:
        if _teacher_id(connection, row["name"].strip()) is None:
            connection.execute(
                "insert into teachers (name, aka, is_owner) values (?, ?, ?)",
                (row["name"].strip(), (row.get("aka") or "").strip() or None, 0),
            )
            counts["teachers_written"] += 1

    for row in students:
        surname, name = row["surname"].strip(), row["name"].strip()
        if _student_id(connection, surname, name) is None:
            connection.execute(
                # ``status`` is 'active' for an imported student and NOT the schema's
                # 'pending' default: pending means "has not registered in the bot yet",
                # and these fifty-six were in the room all year.  Registration is P3's
                # business and will not be helped by every one of them starting as a
                # stranger.  first_sheet_id is left NULL HERE and filled by the importer
                # from the book -- see read_students.
                "insert into students (surname, name, class, status, first_sheet_id) "
                "values (?, ?, ?, ?, null)",
                (surname, name, (row.get("class") or "").strip() or None, "active"),
            )
            counts["students_written"] += 1

    connection.commit()
    return SeedCounts(**counts)


# ------------------------------------------------------------------------ the lookups
#
# Three one-line queries rather than three inline SQL strings repeated at every call
# site: the importer needs exactly these lookups too, and a second copy of "how a student
# is identified" is how the two halves eventually disagree about who Пирогов is.


def _sheet_id(connection, number: str) -> Optional[int]:
    row = connection.execute("select id from sheets where number = ?", (number,)).fetchone()
    return row[0] if row is not None else None


def _teacher_id(connection, name: str) -> Optional[int]:
    row = connection.execute("select id from teachers where name = ?", (name,)).fetchone()
    return row[0] if row is not None else None


def _student_id(connection, surname: str, name: str) -> Optional[int]:
    row = connection.execute(
        "select id from students where surname = ? and name = ?", (surname, name)
    ).fetchone()
    return row[0] if row is not None else None


#: Public names for the importer, which needs the same identification rules.
sheet_id = _sheet_id
teacher_id = _teacher_id
student_id = _student_id
