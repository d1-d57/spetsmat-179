"""Importing last year's conduit into the schema of the bot, and CHECKING that it landed.

WHAT WENT WRONG BEFORE, WRITTEN AT THE TOP SO IT CANNOT BE REPEATED BY ACCIDENT.
The previous version of this file compared the number of solvers it computed from the
journal against row 2 of each sheet of the workbook.  Row 2 is a ``SUM`` over the very
cells the script had just read.  Agreement "to the unit across all 544 problems" therefore
proved that openpyxl can read a file and nothing whatever beyond it.  ``main()`` returned
``None``, so the exit code was always zero and the check could not fail physically.  It
also threw away, silently, every cell value it did not recognise -- 735 ``x`` marks, 88
problems carrying ``✘``, and two stray values.

Three rules follow from that, and they are the shape of this file:

  1. THE INVENTORY COMES FIRST AND FAILS ON THE UNKNOWN.  Before a single mark is written,
     every distinct value in the source is collected and counted.  A value that is not in
     ``VALUE_REGISTRY`` stops the import with its coordinates printed.  There is no silent
     ``None`` anywhere in this file.

  2. AN ORACLE COUNTS ONLY IF IT WAS PRODUCED INDEPENDENTLY OF THE CELLS IT CHECKS, and
     every check prints WHICH KIND it is.  The independence of each one was measured by
     opening the workbook a second time with ``data_only=False`` and reading the formulas
     -- see ``INDEPENDENCE`` below.  Two of the three sheets that look like oracles are
     the SUM row in a longer form, and saying so is the whole point of this position.

  3. EVERY VERDICT CARRIES ITS OWN COVERAGE.  "no divergences" is not a result;
     "divergences 0, checked 544 of 544" is.  Zero checked against a non-empty source is
     RED, not green.

Run it:

    python3 tools/import_konduit.py --inventar             # what the source actually contains
    python3 tools/import_konduit.py --proverit             # import, then every oracle
    python3 tools/import_konduit.py --negativnyj-kontrol   # corrupt on purpose, demand red
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from core.models import CellState
from core.services.progress import ProgressService
from core.services.seeding import (
    DUPLICATE_LABEL_REPAIRS,
    read_sheets,
    read_students,
    repairs_applied,
    seed_catalogue,
)
from infra.db import apply_migrations, connect
from infra.repositories import SqliteCatalogue, SqliteMarkJournal

# --------------------------------------------------------------------------- constants
#
# These belong to ONE historical import run and not to the behaviour of the bot, which is
# why they are here and not in ``config.py``: config.py holds the constants that decide
# what the bot does, and nothing in this block survives the import.

#: The sheets to import, in issue order, TAKEN FROM THE SEED rather than written out here.
#:
#: The seed is the catalogue and the book supplies events for the sheets the catalogue
#: names, so a hard-coded tuple beside ``seed/sheets.json`` would be a second copy of the
#: same list, free to drift from it -- and it would also pin this file to one particular
#: workbook, which is exactly what made the previous version impossible to test against
#: anything but a book nobody is allowed to commit.  Last season's seed yields the
#: eighteen sheets ('1' .. '15', '1д' .. '4д'); the workbook holds 33, the other fifteen
#: being tests, marks and the three summary sheets the oracles read.
def sheets_to_import(seed_dir=None) -> tuple:
    return tuple(
        sheet["number"]
        for sheet in sorted(read_sheets(seed_dir), key=lambda sheet: sheet["ord"])
    )

#: When the imported check-offs are recorded as having HAPPENED.  The book records no
#: dates at all -- not per mark, not per sheet -- so one honest placeholder for the whole
#: imported season beats fifty-four invented ones.  ``recorded_at`` is the real clock, so
#: the two times still say what they are for: this reached the database today, it happened
#: last season.  Every imported mark carries ``NOTE_IMPORT`` saying so in words.
IMPORT_VALID_AT = "2026-06-30T00:00:00Z"

NOTE_IMPORT = "импорт кондуита 2025/26; дата проставлена условно, книга дат не хранит"

#: The carrier ``assert`` written under every ``x``.  See ``VALUE_REGISTRY``.
NOTE_X_CARRIER = "несущая отметка под снятием 'x': событие не наблюдалось, см. retract ниже"

#: How many cells the hand-check oracle reads out for a human.  §4 of the задание.
HAND_CHECKED_CELLS = 30


# ------------------------------------------------------------------- the value registry
#
# EVERY distinct value the mark region of the workbook contains, and what it means.  The
# whole inventory, measured over all 29 920 cells:
#
#     None   14 824      the cell is empty
#     1.0    14 377      solved
#     'x'       735      withdrawn
#     2.0         1      sheet 9, Фёдоров, problem -4б
#     '`'         1      sheet 15, Искеева, problem 1°д
#
# ``'x'`` BECOMES ``assert`` + ``retract``, LEAVING THE CELL AT ``RETRACTED``.  The schema
# offers exactly three states.  ``x`` has to mean "not credited AND not a debt", because
# the workbook's own arithmetic says so: the ``закрыт`` formula of every sheet reads
# ``NOT(REGEXMATCH(cell, "^(1|x)$"))``, treating ``1`` and ``x`` identically as "does not
# owe this".  ``RETRACTED`` is the only state in this schema carrying that meaning
# ("handed in, not credited; not a debt").  A ``retract`` requires ``reverses_id``, so a
# carrier ``assert`` must precede it -- and that carrier is stamped with ``NOTE_X_CARRIER``
# precisely so that it can never later be read as an observed check-off.
#
# ``2.0`` AND ``'`'`` ARE QUARANTINED: no event is written, and both are printed by name
# with their coordinates.  This is not the old silent ``None``; they are two named entries
# in an explicit registry, and any value outside the registry stops the import.  The
# decision also agrees with the only other authority in the book: neither value matches
# ``^(1|x)$``, so the spreadsheet's own arithmetic counts both as not-closed too.

SOLVED = "solved"
WITHDRAWN = "withdrawn"
QUARANTINE = "quarantine"
EMPTY = "empty"

VALUE_REGISTRY = {
    None: EMPTY,
    1: SOLVED,
    "x": WITHDRAWN,
    2: QUARANTINE,
    "`": QUARANTINE,
}


def normalise(value):
    """The workbook's cell value as a key of ``VALUE_REGISTRY``.

    Only two normalisations happen, and both are spelled out because a normalisation that
    is not is how ``'X'`` and ``'x '`` become an unknown value at three in the morning:
    a float that is a whole number becomes that integer, and a string is stripped and
    lowercased.  Nothing else is coerced -- in particular a string ``'1'`` is NOT turned
    into the integer 1, because the two are different keystrokes and the difference is
    exactly the kind of thing the inventory exists to show.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        return value.strip().lower()
    return value


class UnknownCellValue(Exception):
    """A value in the source that ``VALUE_REGISTRY`` does not describe.

    Raised, never swallowed.  The previous importer returned ``None`` here and discarded
    854 real cells without a word.
    """


class SourceMissing(Exception):
    """The workbook is not where ``config.KONDUIT_XLSX`` says it is."""


class AlreadyImported(Exception):
    """Asked to import into a journal that already holds events."""


# ------------------------------------------------------------------------- the layouts


@dataclass(frozen=True)
class Layout:
    """Where the columns of one sheet are.  FOUR layouts occur, not one and not three.

    * ``1 2 3 4 6 7 8``   header on row 3, ``принимающий`` at column 2, surname at 3;
    * ``9..14 3д 4д``     header on row 3, surname at column 1, ``закрыт`` at column 3;
    * ``15``              as above, but a blank column sits before ``принимающий``;
    * ``1д 2д``           THE HEADER IS ROW 1 -- there is no status row at all, and the
                          data begins on row 2.  Fifty of the 544 problems live here.

    Found by reading the headers rather than by a table of sheet names, so a sheet that
    moves a column does not have to be discovered by a wrong number in a report.
    """

    header_row: int
    surname_column: int
    name_column: int
    first_problem_column: int
    receiver_column: Optional[int]
    closed_column: Optional[int]

    @property
    def has_status_row(self) -> bool:
        """``1д`` and ``2д`` have no row of ``° ● ✓ ✘`` signs under the labels."""
        return self.header_row > 1


def layout_of(worksheet) -> Layout:
    for row in (1, 2, 3, 4):
        headers = {}
        for column in range(1, 12):
            value = worksheet.cell(row, column).value
            if isinstance(value, str):
                headers[value.strip().lower()] = column
        if "фамилия" in headers and "имя" in headers:
            service = [
                column
                for header, column in headers.items()
                if header in ("фамилия", "имя", "закрыт", "принимающий")
            ]
            return Layout(
                header_row=row,
                surname_column=headers["фамилия"],
                name_column=headers["имя"],
                first_problem_column=max(service) + 1,
                receiver_column=headers.get("принимающий"),
                closed_column=headers.get("закрыт"),
            )
    raise ValueError("не нашёл заголовков на листе %r" % worksheet.title)


def problem_columns(worksheet, layout: Layout) -> dict:
    """``column -> label`` for every problem of the sheet, in sheet order.

    Labels come from row 1 in every layout, including ``1д``/``2д`` where row 1 is also
    the header row: the service columns are excluded by starting at
    ``first_problem_column``, not by recognising the header words a second time.

    THE SAME LABEL REPAIR THE SEED LOADER APPLIES IS APPLIED HERE, keyed identically on
    the occurrence index.  Without it the two ``12д`` columns of sheet ``2д`` both resolve
    to the single ``12д`` row of the catalogue, one problem of the 544 is never reached by
    any reading, and the cells of one of the two columns are attributed to the other
    column's problem.  Both columns happen to be empty, so nothing was misattributed in
    fact -- but it was silent, and the coverage line is what showed it: the full-grid check
    reported 543 problems of 544.  That is precisely why the coverage is printed rather
    than described.
    """
    labels = {}
    occurrences: dict = {}
    for column in range(layout.first_problem_column, worksheet.max_column + 1):
        raw = worksheet.cell(1, column).value
        if raw is None:
            continue
        label = str(int(raw)) if isinstance(raw, float) and raw.is_integer() else str(raw).strip()
        if not label:
            continue
        index = occurrences.get(label, 0)
        occurrences[label] = index + 1
        labels[column] = DUPLICATE_LABEL_REPAIRS.get(
            (worksheet.title, label, index), label
        )
    return labels


def student_rows(worksheet, layout: Layout) -> list:
    """``(row, surname, name)`` for every student row of the sheet.

    The leading ``~`` marks the technical student (Аракелова) and is stripped: she is a
    row in ``seed/students.csv`` like everyone else, and dropping her here would make the
    counts disagree with the seed for no reason anybody could later reconstruct.
    """
    rows = []
    for row in range(layout.header_row + 1, worksheet.max_row + 1):
        raw = worksheet.cell(row, layout.surname_column).value
        if not raw or isinstance(raw, (int, float)):
            continue
        surname = str(raw).strip().lstrip("~").strip()
        if not surname:
            continue
        name = str(worksheet.cell(row, layout.name_column).value or "").strip()
        rows.append((row, surname, name))
    return rows


# ------------------------------------------------------------------------- the source


def open_workbook(path: Optional[Path] = None):
    """Load the conduit, or refuse in words a person can act on."""
    import openpyxl

    path = Path(path or config.KONDUIT_XLSX)
    if not path.exists():
        raise SourceMissing(
            "не найдена книга кондуита: %s\n"
            "Она НЕ лежит в репозитории и не будет там лежать: это персональные данные\n"
            "пятидесяти шести детей.  Положите её по этому пути или укажите другой:\n"
            "    KONDUIT_XLSX='/путь/к/Кондуит 8КЛ.xlsx' python3 tools/import_konduit.py ..."
            % path
        )
    return openpyxl.load_workbook(path, data_only=True)


@dataclass
class Reading:
    """One cell of the mark region, already classified."""

    sheet: str
    surname: str
    name: str
    label: str
    raw: object
    meaning: str


def read_cells(workbook) -> list:
    """Every cell of the mark region of all eighteen sheets, classified.

    Raises ``UnknownCellValue`` on the first value the registry does not describe, with
    the sheet, the student and the problem named -- so that the person reading the failure
    can open the book at that cell rather than search 29 920 of them.
    """
    readings = []
    for sheet_number in sheets_to_import():
        worksheet = workbook[sheet_number]
        layout = layout_of(worksheet)
        labels = problem_columns(worksheet, layout)
        for row, surname, name in student_rows(worksheet, layout):
            for column, label in labels.items():
                raw = worksheet.cell(row, column).value
                key = normalise(raw)
                if key not in VALUE_REGISTRY:
                    raise UnknownCellValue(
                        "неизвестное значение %r (нормализовано %r) на листке %s, "
                        "ученик %s %s, задача %s, ячейка R%dC%d.\n"
                        "Известные значения: %s.\n"
                        "Импорт остановлен: молчаливого None в этом файле не бывает."
                        % (raw, key, sheet_number, surname, name, label, row, column,
                           ", ".join(repr(k) for k in VALUE_REGISTRY))
                    )
                readings.append(
                    Reading(sheet_number, surname, name, label, raw, VALUE_REGISTRY[key])
                )
    return readings


def inventory(readings: list) -> Counter:
    """Distinct NORMALISED values with counts.  Printed, and carried into the report."""
    return Counter(normalise(reading.raw) for reading in readings)


# ------------------------------------------------------------------------- the teachers
#
# TWO HOLES IN THE DATA, CLOSED HERE RATHER THAN PAPERED OVER (§6 of the задание).
#
# (a) THE SENIOR OF ROOM 203, INITIALS НС, IS NOT A TEACHER ANYWHERE.  ``seed/teachers.csv``
#     names a ``senior_aka`` for every teacher: ``ДМ`` is Даня, ``ИЯ`` is Ваня -- both are
#     rows of the file -- and ``НС`` is nobody.  He is the only senior of the three who is
#     not registered.  All the book records of him is the pair of initials, so the pair of
#     initials is his name here; inventing a full name would be inventing data.
#
# (b) COMPOSITE RECEIVERS.  Three of the nineteen distinct receiver strings name two people:
#     'Саша Оревкова/Ольга Александровна', 'Наталия Павлована/Ольга Александровна' and
#     'Даня/Ольга Александровна'.  (The задание names two; the third was found by the
#     inventory.  'Мика/Вася' also contains a slash and is NOT composite -- it is one
#     teacher, a row of seed/teachers.csv with aka 'МН'.)
#
#     ``marks.teacher_id`` is one column, so "one author per mark" cannot express a pair.
#     THE DECISION: the mark is attributed to the FIRST-named teacher, and the second is
#     carried in ``note`` as a machine-readable ``соавтор: <name>`` tag.
#
#     First-named is not a coin flip.  ``seed/teachers.csv`` gives Ольга Александровна
#     ``students_actual = 0`` while her ``students_count`` is 3: the seed itself already
#     treats the first name of each pair as the attributed teacher and her as the second.
#     Following the seed keeps per-teacher statistics agreeing with it instead of quietly
#     disagreeing.
#
#     Nothing is lost.  The pairing is preserved verbatim and machine-readably on every
#     affected mark, so a later migration that adds a proper ``mark_authors`` table can
#     reconstruct every pair exactly, with no second reading of the workbook.
#
#     The alternative -- a ``teachers`` row per pair -- was rejected: a pair is not a
#     person, and it would make every per-teacher projection in the project count a
#     phantom colleague alongside the two real ones.

SENIOR_WITHOUT_A_ROW = "НС"

COMPOSITE_SEPARATOR = "/"

#: Receiver strings that contain a separator and are nevertheless ONE person.
NOT_COMPOSITE = ("Мика/Вася",)


def split_receiver(receiver: str) -> list:
    """A receiver string as the list of teachers it names."""
    receiver = receiver.strip()
    if receiver in NOT_COMPOSITE or COMPOSITE_SEPARATOR not in receiver:
        return [receiver]
    return [part.strip() for part in receiver.split(COMPOSITE_SEPARATOR) if part.strip()]


def register_missing_teachers(connection, receivers) -> list:
    """Add the seniors and receivers the seed does not carry.  Returns what was added."""
    added = []

    seniors = {
        row["senior_aka"].strip()
        for row in _teacher_rows(connection)
        if row["senior_aka"] and row["senior_aka"].strip()
    }
    known_akas = {row["aka"].strip() for row in _teacher_rows(connection) if row["aka"]}
    for senior in sorted(seniors - known_akas):
        connection.execute(
            "insert into teachers (name, aka, is_owner) values (?, ?, 0)", (senior, senior)
        )
        added.append((senior, "старший аудитории, не заведён ни в списке, ни на листках"))

    for receiver in sorted(receivers):
        for person in split_receiver(receiver):
            standing = connection.execute(
                "select id from teachers where name = ?", (person,)
            ).fetchone()
            if standing is None:
                connection.execute(
                    "insert into teachers (name, aka, is_owner) values (?, null, 0)",
                    (person,),
                )
                added.append((person, "принимающий из книги, отсутствует в seed/teachers.csv"))
    connection.commit()
    return added


def _teacher_rows(connection) -> list:
    """``seed/teachers.csv`` as dicts.  Read from the seed, not from the database: the
    ``senior_aka`` column is seed metadata and has no column in the schema."""
    import csv

    with (Path(config.SEED_DIR) / "teachers.csv").open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


# ---------------------------------------------------------------------------- the import


@dataclass
class ImportCounts:
    marks_written: int = 0
    asserts: int = 0
    retracts: int = 0
    carriers: int = 0
    quarantined: list = field(default_factory=list)
    students_matched: int = 0
    students_unmatched: list = field(default_factory=list)
    first_sheet_set: int = 0
    first_sheet_null: int = 0
    first_sheet_disagreements: list = field(default_factory=list)
    teachers_added: list = field(default_factory=list)
    composite_marks: int = 0
    repairs: list = field(default_factory=list)


def import_workbook(connection, workbook) -> ImportCounts:
    """Seed the catalogue, then write every mark of the eighteen sheets into the journal."""
    counts = ImportCounts()

    # THE CATALOGUE LOAD IS IDEMPOTENT; THE JOURNAL LOAD IS NOT, AND CANNOT BE.  A mark is
    # an EVENT -- "this happened" -- so a second import does not overwrite the first, it
    # says it happened again, and the journal quietly doubles.  Every state check would
    # stay green while it did, because the projection reads only the LAST event of a cell
    # and a duplicate assert leaves that state identical.  Found by corrupting the journal
    # with a duplicated event and watching all five checks stay green.
    standing = connection.execute("select count(*) from marks").fetchone()[0]
    if standing:
        raise AlreadyImported(
            "в журнале уже %d событий — повторный импорт удвоил бы его молча.\n"
            "Журнал append-only: отметка это СОБЫТИЕ, второй импорт не перезаписывает "
            "первый, а говорит, что это случилось ещё раз.\n"
            "Импортируйте в чистую базу." % standing
        )

    counts.repairs = repairs_applied(read_sheets())
    seed_catalogue(connection)

    readings = read_cells(workbook)
    receivers = _receivers_of(workbook)
    counts.teachers_added = register_missing_teachers(connection, receivers)

    problem_ids = {
        (row["number"], row["label"]): row["id"]
        for row in connection.execute(
            "select s.number as number, p.label as label, p.id as id "
            "  from problems p join sheets s on s.id = p.sheet_id"
        )
    }
    student_ids = {
        (row["surname"], row["name"]): row["id"]
        for row in connection.execute("select id, surname, name from students")
    }
    teacher_ids = {
        row["name"]: row["id"] for row in connection.execute("select id, name from teachers")
    }
    sheet_ids = {
        row["number"]: (row["id"], row["ord"])
        for row in connection.execute("select id, number, ord from sheets")
    }

    receiver_of = _receiver_by_row(workbook)
    unmatched = set()

    connection.execute("begin")
    for reading in readings:
        key = _student_key(reading.surname, reading.name, student_ids)
        if key is None:
            unmatched.add((reading.surname, reading.name))
            continue
        student_id = student_ids[key]
        problem_id = problem_ids.get((reading.sheet, reading.label))
        if problem_id is None:
            raise UnknownCellValue(
                "задача %r листка %r есть в книге и отсутствует в засеве"
                % (reading.label, reading.sheet)
            )

        if reading.meaning == QUARANTINE:
            counts.quarantined.append(
                (reading.sheet, reading.surname, reading.name, reading.label, reading.raw)
            )
            continue
        if reading.meaning == EMPTY:
            continue

        receiver = receiver_of.get((reading.sheet, reading.surname, reading.name))
        teacher_id, note_suffix, composite = _attribute(receiver, teacher_ids)
        if composite:
            counts.composite_marks += 1

        assert_id = _append(
            connection, student_id, problem_id, "assert", None, teacher_id,
            NOTE_IMPORT + note_suffix
            + ("" if reading.meaning == SOLVED else "; " + NOTE_X_CARRIER),
        )
        counts.marks_written += 1
        counts.asserts += 1
        if reading.meaning == WITHDRAWN:
            counts.carriers += 1
            _append(connection, student_id, problem_id, "retract", assert_id, teacher_id,
                    NOTE_IMPORT + note_suffix + "; снятие 'x' из книги")
            counts.marks_written += 1
            counts.retracts += 1
    connection.execute("commit")

    counts.students_unmatched = sorted(unmatched)
    counts.students_matched = len(student_ids) - len(unmatched)
    _set_first_sheets(connection, workbook, sheet_ids, student_ids, counts)
    return counts


def _append(connection, student_id, problem_id, event, reverses_id, teacher_id, note) -> int:
    """One journal row.  Written through SQL rather than through ``MarkingService``.

    The service exists to decide WHAT event a tap should produce and to keep two taps from
    racing; an import has neither question -- it knows the target exactly and it is the
    only writer.  Going through the service would also mean 15 000 separate ``begin
    immediate`` transactions.  What the service guarantees is still guaranteed here: the
    schema's own triggers and CHECK constraints are the carrier, and they are the same for
    both writers.
    """
    cursor = connection.execute(
        "insert into marks (student_id, problem_id, event, reverses_id, teacher_id, "
        "valid_at, recorded_at, source, note) values (?, ?, ?, ?, ?, ?, ?, 'импорт', ?)",
        (student_id, problem_id, event, reverses_id, teacher_id,
         IMPORT_VALID_AT, _now(), note),
    )
    return cursor.lastrowid


def _now() -> str:
    from core.isotime import now_iso

    return now_iso()


def _attribute(receiver, teacher_ids):
    """``(teacher_id, note suffix, is_composite)`` for one receiver string."""
    if not receiver:
        return None, "", False
    people = split_receiver(receiver)
    teacher_id = teacher_ids.get(people[0])
    if len(people) == 1:
        return teacher_id, "", False
    return teacher_id, "; соавтор: " + ", ".join(people[1:]), True


def _student_key(surname, name, student_ids):
    """Match a book row to a seed student: exact pair first, then surname alone.

    The fallback is needed and is narrow: the book writes 'Дарья ' with a trailing space
    on one sheet and short forms in the ``долги`` sheet.  It is used only when the surname
    is unambiguous in the seed, so it can never silently merge two people.
    """
    if (surname, name) in student_ids:
        return (surname, name)
    candidates = [key for key in student_ids if key[0] == surname]
    return candidates[0] if len(candidates) == 1 else None


def _receivers_of(workbook) -> set:
    receivers = set()
    for sheet_number in sheets_to_import():
        worksheet = workbook[sheet_number]
        layout = layout_of(worksheet)
        if layout.receiver_column is None:
            continue
        for row, _surname, _name in student_rows(worksheet, layout):
            value = worksheet.cell(row, layout.receiver_column).value
            if value:
                receivers.add(str(value).strip())
    return receivers


def _receiver_by_row(workbook) -> dict:
    """``(sheet, surname, name) -> receiver string``."""
    by_row = {}
    for sheet_number in sheets_to_import():
        worksheet = workbook[sheet_number]
        layout = layout_of(worksheet)
        if layout.receiver_column is None:
            continue
        for row, surname, name in student_rows(worksheet, layout):
            value = worksheet.cell(row, layout.receiver_column).value
            if value:
                by_row[(sheet_number, surname, name)] = str(value).strip()
    return by_row


# --------------------------------------------------------------------- first_sheet_id
#
# §3 of the задание, and the reason the field exists at all: exactly two students moved
# during the year -- Гамаюнова left, Пирогов arrived -- and whoever arrives later is not
# charged the sheets that came before them.
#
# ON IMPORT THE FIELD IS SET EXPLICITLY FOR EVERY STUDENT and NULL must not survive: the
# rule is the earliest sheet, by ``ord``, in which the student has a ROW.  That rule was
# checked against the seed rather than assumed -- it reproduces both movers exactly
# (Гамаюнова: rows in 7 sheets, first is '1'; Пирогов: rows in 12 sheets, first is '6'),
# and gives sheet '1' and 18 sheets for the other 54.
#
# P1's fallback ("NULL means owes from the very first sheet") is NOT touched: it is out of
# this zone, it is pinned by
# ``tests/test_verifier_findings.py::test_a_student_with_no_first_sheet_owes_from_the_very_first_sheet``,
# and it is right for imported rows.  It is wrong for a freshly registered student, who
# would open the bot to a wall of debts on day one -- but that is registration's default
# and belongs to P3.  What this import does is make NULL impossible, so the fallback never
# has to fire for a student who came from the book.


def _set_first_sheets(connection, workbook, sheet_ids, student_ids, counts) -> None:
    present = defaultdict(set)
    for sheet_number in sheets_to_import():
        worksheet = workbook[sheet_number]
        layout = layout_of(worksheet)
        for _row, surname, name in student_rows(worksheet, layout):
            key = _student_key(surname, name, student_ids)
            if key is not None:
                present[key].add(sheet_number)

    seed_first = {
        (row["surname"].strip(), row["name"].strip()): (row.get("first_sheet") or "").strip()
        for row in read_students()
    }

    for key, sheet_numbers in present.items():
        first = min(sheet_numbers, key=lambda number: sheet_ids[number][1])
        connection.execute(
            "update students set first_sheet_id = ? where id = ?",
            (sheet_ids[first][0], student_ids[key]),
        )
        counts.first_sheet_set += 1
        expected = seed_first.get(key)
        if expected and expected != first:
            counts.first_sheet_disagreements.append((key[0], key[1], expected, first))
    connection.commit()

    counts.first_sheet_null = connection.execute(
        "select count(*) from students where first_sheet_id is null"
    ).fetchone()[0]


# ------------------------------------------------------------------------- the oracles
#
# INDEPENDENCE, MEASURED AND NOT ASSUMED.  The workbook was opened a second time with
# ``data_only=False`` and the formulas were read.  This is the finding that reshapes §4 of
# the задание, and every check below prints its class so that no reader can mistake one
# for another:
#
#   НЕЗАВИСИМЫЙ    the numbers were produced by a person, by hand, not from these cells.
#                  'гробарий' -- 20 rows, and every student surname in them is typed by
#                  hand: 0 formula cells in the name columns.  'зачёт' -- 55 rows,
#                  columns D and E hand-entered, 0 formulas.  And the thirty cells a human
#                  re-reads.
#
#   ПОЛУЗАВИСИМЫЙ  a DIFFERENT computation over the SAME cells.  The 'долги' sheet is
#                  exactly this and the задание's premise that it is independent is false:
#                  every per-sheet column of it is
#                      =INDEX(INDIRECT(<лист>&"!A:A"), MATCH($A<row>, INDIRECT(<лист>&"!C:C"), 0))
#                  -- a VLOOKUP of that sheet's 'закрыт' column, which is itself
#                      =IF(SUMPRODUCT(REGEXMATCH(labels,"[°˚]") * NOT(REGEXMATCH(cells,"^(1|x)$")))=0,"✓",<count>)
#                  over the very mark cells.  It is the SUM row with two extra hops.
#                  It is still worth running, and it is run: it encodes a DIFFERENT
#                  definition (obligatory by label regex rather than by seed/sheets.json,
#                  and 'x' closing a debt), so a disagreement still finds a real defect.
#                  It simply is not proof, and it is not sold as proof.
#
#   ВНУТРЕННИЙ     the full-grid differential: an independent SECOND read of the workbook
#                  against the journal projected through core/services/progress.py.  It
#                  checks a different thing -- that nothing was lost or displaced between
#                  reading and projecting -- and it is the only check that spans all
#                  29 920 cells, which is what makes the negative control below bite
#                  everywhere rather than only on the covered rows.


# ------------------------------------------------------- defects found IN THE SOURCE
#
# A divergence an oracle reports is a FINDING, and a finding that has been run to ground
# and shown to be a defect of the BOOK rather than of the import belongs here -- named,
# with its evidence -- instead of quietly turning every future run red or, far worse,
# being suppressed by loosening the comparison.
#
# The registry works exactly like VALUE_REGISTRY and DUPLICATE_LABEL_REPAIRS: what is
# listed is printed on every run and does not fail the check; ANYTHING NOT LISTED IS RED.
# A new divergence can therefore never hide behind an old one.
#
# гробарий · листок 3 · задача 16б*
#   The гробарий names one student, Цуканов.  The grid has two: Аникина (row 5) and
#   Цуканов (row 54).  The book contradicts ITSELF here, and the tie is broken by a third
#   artefact of the book: the sheet's own counter for that column says 2, which is the
#   number this import produces.  So the hand-written name list is short by one name --
#   somebody forgot to copy Аникина across -- and the import is right.
#   Nothing changes in the data because of this: the гробарий's own sign is
#   =IF(COUNTA(D:ZZ) <= 2, "✘", "✓"), and at one name or at two the sign is ✘ either way.
KNOWN_SOURCE_DEFECTS = {
    ("гробарий", "3", "16б*"): (
        "в гробарии не выписана Аникина; счётчик самого листка даёт 2 — столько же, "
        "сколько журнал, значит недосчитан гробарий, а не импорт"
    ),
}


@dataclass
class OracleResult:
    name: str
    independence: str
    checked: int
    total: int
    divergences: list = field(default_factory=list)
    #: Divergences traced to a defect of the BOOK and listed in KNOWN_SOURCE_DEFECTS.
    #: Printed on every run; they do not turn the check red.
    known_defects: list = field(default_factory=list)

    @property
    def is_red(self) -> bool:
        """Zero checked against a non-empty source is RED, not green (§4 of the задание)."""
        return bool(self.divergences) or (self.total > 0 and self.checked == 0)

    def line(self) -> str:
        return "[%s] %-28s сверено %d из %d, расхождений %d%s%s" % (
            "КРАСНЫЙ" if self.is_red else "зелёный",
            self.name,
            self.checked,
            self.total,
            len(self.divergences),
            (", известных дефектов книги %d" % len(self.known_defects))
            if self.known_defects else "",
            "   (%s)" % self.independence,
        )


def _cell_states(connection) -> dict:
    """``(student_id, problem_id) -> CellState`` through the project's own projection."""
    progress = ProgressService(SqliteMarkJournal(connection), SqliteCatalogue(connection))
    students = [row[0] for row in connection.execute("select id from students")]
    problems = [row[0] for row in connection.execute("select id from problems")]
    return progress.states_for_many(students, problems)


def _lookups(connection):
    problem_ids = {
        (row["number"], row["label"]): row["id"]
        for row in connection.execute(
            "select s.number as number, p.label as label, p.id as id "
            "  from problems p join sheets s on s.id = p.sheet_id"
        )
    }
    student_ids = {
        (row["surname"], row["name"]): row["id"]
        for row in connection.execute("select id, surname, name from students")
    }
    return problem_ids, student_ids


def oracle_graveyard(connection, workbook) -> OracleResult:
    """The 'гробарий' sheet: who, by name and in a human's handwriting, took each problem.

    THE ONLY FULLY-INDEPENDENT ORACLE IN THE BOOK, and it is not in the задание's list.
    Columns D onward hold student surnames typed by a person; nothing in them is computed
    from the grid.  A row is checked by comparing that set of surnames against the set of
    students whose cell for that problem stands at SOLVED.
    """
    worksheet = workbook["гробарий"]
    problem_ids, student_ids = _lookups(connection)
    states = _cell_states(connection)
    surname_to_id = defaultdict(list)
    for (surname, _name), student_id in student_ids.items():
        surname_to_id[surname].append(student_id)

    checked = 0
    total = 0
    divergences = []
    known_defects = []
    for row in range(2, worksheet.max_row + 1):
        sheet_raw = worksheet.cell(row, 1).value
        label_raw = worksheet.cell(row, 2).value
        if not sheet_raw or label_raw is None:
            continue
        total += 1
        sheet_number = str(sheet_raw).strip("[] ")
        label = (str(int(label_raw)) if isinstance(label_raw, float) and label_raw.is_integer()
                 else str(label_raw).strip())
        problem_id = problem_ids.get((sheet_number, label))
        if problem_id is None:
            divergences.append(
                "гробарий строка %d: задача %s листка %s отсутствует в засеве"
                % (row, label, sheet_number)
            )
            continue

        named = set()
        for column in range(4, worksheet.max_column + 1):
            value = worksheet.cell(row, column).value
            if value:
                named.add(str(value).strip())
        solved = {
            surname
            for (surname, _name), student_id in student_ids.items()
            if states.get((student_id, problem_id)) is CellState.SOLVED
        }
        checked += 1
        if named != solved:
            message = ("листок %s задача %s: в гробарии %s, в журнале %s"
                       % (sheet_number, label, sorted(named) or "никого",
                          sorted(solved) or "никого"))
            known = KNOWN_SOURCE_DEFECTS.get(("гробарий", sheet_number, label))
            if known:
                known_defects.append(message + " — " + known)
            else:
                divergences.append(message)
    return OracleResult("гробарий (имена от руки)", "НЕЗАВИСИМЫЙ", checked, total,
                        divergences, known_defects)


def _row_of(workbook, reading) -> int:
    """The workbook row of a reading, so a printed line names a cell a person can open."""
    worksheet = workbook[reading.sheet]
    layout = layout_of(worksheet)
    for row, surname, name in student_rows(worksheet, layout):
        if (surname, name) == (reading.surname, reading.name):
            return row
    return 0


def _column_of(workbook, reading) -> int:
    worksheet = workbook[reading.sheet]
    layout = layout_of(worksheet)
    for column, label in problem_columns(worksheet, layout).items():
        if label == reading.label:
            return column
    return 0


def oracle_hand_cells(connection, workbook) -> OracleResult:
    """Thirty cells re-read straight out of the book and printed for a human.

    Spread deliberately, and the spread has TWO jobs.  A strided walk puts every one of
    the eighteen sheets into the sample and takes students and problems from all over each
    one, so a systematic displacement of a row or a column cannot hide.  But a stride alone
    picks almost nothing but ``1.0`` and empty cells -- the two commonest values -- and a
    hand-check that never once looks at an ``x`` would not be checking the single decision
    in this file most likely to be wrong.  So the sample is then TOPPED UP until every
    meaning in ``VALUE_REGISTRY`` that occurs in the book is represented, both quarantined
    cells included, before it is cut back to thirty.

    Each is written out as ``sheet · student · problem · expected · got`` so that any of
    the thirty can be re-checked by opening the workbook, without running anything.
    """
    problem_ids, student_ids = _lookups(connection)
    states = _cell_states(connection)

    def cell_at(sheet_number, row_index, column_index):
        worksheet = workbook[sheet_number]
        layout = layout_of(worksheet)
        labels = list(problem_columns(worksheet, layout).items())
        rows = student_rows(worksheet, layout)
        if not labels or not rows:
            return None
        row, surname, name = rows[row_index % len(rows)]
        column, label = labels[column_index % len(labels)]
        return (sheet_number, surname, name, label,
                worksheet.cell(row, column).value, row, column)

    # The rare meanings are RESERVED FIRST, before the strided walk fills the rest.  Done
    # the other way round the walk fills all thirty slots with the two commonest values and
    # the top-up is cut off by the very truncation that keeps the sample at thirty -- which
    # is what happened on the first run of this function.
    by_meaning = defaultdict(list)
    for reading in read_cells(workbook):
        by_meaning[reading.meaning].append(reading)

    order = sheets_to_import()
    picked = []
    seen = set()
    for meaning in sorted(by_meaning):
        readings = by_meaning[meaning]
        wanted = min(4, len(readings))
        stride = max(1, len(readings) // 97)
        for reading in readings[::stride]:
            if wanted <= 0:
                break
            key = (reading.sheet, reading.surname, reading.name, reading.label)
            if key in seen:
                continue
            seen.add(key)
            picked.append((reading.sheet, reading.surname, reading.name, reading.label,
                           reading.raw, _row_of(workbook, reading), _column_of(workbook, reading)))
            wanted -= 1

    step = 0
    index = 0
    while len(picked) < HAND_CHECKED_CELLS and index < HAND_CHECKED_CELLS * 4:
        cell = cell_at(order[index % len(order)],
                       index * 7 + step, index * 5 + step)
        step += 3
        index += 1
        if cell is not None and cell[:4] not in seen:
            seen.add(cell[:4])
            picked.append(cell)
    picked.sort(key=lambda cell: (order.index(cell[0]), cell[1]))

    checked = 0
    divergences = []
    print("    тридцать клеток, прочитанных из книги отдельно (листок · ученик · задача · "
          "в книге · в журнале):")
    for sheet_number, surname, name, label, raw, row, column in picked:
        key = _student_key(surname, name, student_ids)
        problem_id = problem_ids.get((sheet_number, label))
        expected = {SOLVED: CellState.SOLVED,
                    WITHDRAWN: CellState.RETRACTED,
                    EMPTY: CellState.EMPTY,
                    QUARANTINE: CellState.EMPTY}[VALUE_REGISTRY[normalise(raw)]]
        got = states.get((student_ids[key], problem_id)) if key and problem_id else None
        checked += 1
        mark = "  " if got is expected else "≠≠"
        print("      %s %-4s R%-4d C%-3d %-16s %-8s %-7r %s → %s"
              % (mark, sheet_number, row, column, surname[:16], label[:8], raw,
                 expected.value, got.value if got else "НЕТ"))
        if got is not expected:
            divergences.append(
                "%s · %s %s · %s · в книге %r (%s) · в журнале %s"
                % (sheet_number, surname, name, label, raw, expected.value,
                   got.value if got else "НЕТ")
            )
    return OracleResult("тридцать клеток вручную", "НЕЗАВИСИМЫЙ",
                        checked, len(picked), divergences)


def oracle_debts(connection, workbook) -> OracleResult:
    """The 'долги' sheet, honouring ``first_sheet_id``.

    ПОЛУЗАВИСИМЫЙ, and the header of this section says why in full.  What it really tests
    is the pair of definitions: obligatory-by-``seed/sheets.json`` against
    obligatory-by-label-regex, and whether 'x' closes a debt.  A student who arrived later
    is not charged the older sheets, which is the rule Пирогов produced.
    """
    worksheet = workbook["долги"]
    _problem_ids, student_ids = _lookups(connection)
    states = _cell_states(connection)

    sheet_ord = {row["number"]: row["ord"] for row in connection.execute("select number, ord from sheets")}
    first_ord = {}
    for row in connection.execute(
        "select st.id as id, s.ord as ord from students st "
        "  left join sheets s on s.id = st.first_sheet_id"
    ):
        first_ord[row["id"]] = row["ord"]

    obligatory = defaultdict(list)
    for row in connection.execute(
        "select s.number as number, p.id as id from problems p "
        "  join sheets s on s.id = p.sheet_id where p.kind in (%s)"
        % ", ".join("?" for _ in config.OBLIGATORY_KINDS),
        config.OBLIGATORY_KINDS,
    ):
        obligatory[row["number"]].append(row["id"])

    columns = {}
    for column in range(5, worksheet.max_column + 1):
        raw = worksheet.cell(1, column).value
        if raw is None:
            continue
        columns[column] = (str(int(raw)) if isinstance(raw, float) and raw.is_integer()
                           else str(raw).strip())

    checked = 0
    total = 0
    divergences = []
    for row in range(2, worksheet.max_row + 1):
        raw_surname = worksheet.cell(row, 1).value
        if not raw_surname:
            continue
        surname = str(raw_surname).strip().lstrip("~").strip()
        key = _student_key(surname, "", student_ids)
        for column, sheet_number in columns.items():
            cell = worksheet.cell(row, column).value
            if cell is None:
                continue
            total += 1
            if key is None or sheet_number not in obligatory:
                continue
            expected = 0 if cell == "✓" else (int(cell) if isinstance(cell, (int, float)) else None)
            if expected is None:
                continue
            student_id = student_ids[key]
            # Whoever arrived later is not charged the older sheets.  Those cells are
            # CHECKED and not skipped: the book carries '✓' for them (Пирогов, sheets
            # 1-4), so comparing them TESTS the rule instead of excusing the oracle from
            # it -- a wrong first_sheet_id would produce debts here against the book's
            # '✓' and turn this check red, which is exactly what should happen.
            if first_ord.get(student_id) is not None and \
                    sheet_ord[sheet_number] < first_ord[student_id]:
                got = 0
            else:
                got = sum(
                    1
                    for problem_id in obligatory[sheet_number]
                    if states.get((student_id, problem_id), CellState.EMPTY).is_debt_candidate
                )
            checked += 1
            if got != expected:
                divergences.append(
                    "%s листок %s: в листе «долги» %d, в журнале %d"
                    % (surname, sheet_number, expected, got)
                )
    return OracleResult("лист «долги»", "ПОЛУЗАВИСИМЫЙ", checked, total, divergences)


def oracle_credit(connection, workbook) -> OracleResult:
    """The 'зачёт' sheet: the year's credit, awarded by a person.

    НЕЗАВИСИМЫЙ -- columns D and E are hand-entered, 0 formulas -- and it answers a
    DIFFERENT question than the grid does, so it is reported as a measurement rather than
    as an equality that must hold.  What is checked is the one thing that must be true:
    every name on the credit sheet is a student this import knows.  Whether the credit was
    deserved by the journal's arithmetic is a decision a teacher made in a room, and a
    disagreement there is not an import defect.
    """
    worksheet = workbook["зачёт"]
    _problem_ids, student_ids = _lookups(connection)
    checked = 0
    total = 0
    divergences = []
    for row in range(2, worksheet.max_row + 1):
        surname = worksheet.cell(row, 2).value
        if not surname:
            continue
        total += 1
        key = _student_key(str(surname).strip(), str(worksheet.cell(row, 3).value or "").strip(),
                           student_ids)
        checked += 1
        if key is None:
            divergences.append("лист «зачёт» строка %d: ученик %s не найден среди импортированных"
                               % (row, surname))
    return OracleResult("лист «зачёт» (имена)", "НЕЗАВИСИМЫЙ", checked, total, divergences)


def journal_cardinality(connection, workbook) -> OracleResult:
    """How many ROWS the journal holds, against an arithmetic identity from the source.

    Every other check in this file judges the PROJECTION -- the state of a cell, which is
    its last event.  That leaves one whole class of damage invisible: duplicate an event
    and the state does not move, so all five of the other checks stay green while the
    journal doubles.  That is not hypothetical, it is how an importer run twice fails.

    The identity is exact and comes from the inventory rather than from the journal:

        asserts  = (cells reading '1') + (cells reading 'x')   -- each 'x' needs a carrier
        retracts = (cells reading 'x')

    so ``asserts - retracts`` must equal the number of '1' cells to the unit.  Nothing
    here is derived from ``marks``, which is what makes it a check and not a restatement.
    """
    counts = inventory(read_cells(workbook))
    solved = sum(count for value, count in counts.items()
                 if VALUE_REGISTRY[value] == SOLVED)
    withdrawn = sum(count for value, count in counts.items()
                    if VALUE_REGISTRY[value] == WITHDRAWN)

    rows = dict(connection.execute("select event, count(*) from marks group by event").fetchall())
    expected = {"assert": solved + withdrawn, "retract": withdrawn, "erratum": 0}

    divergences = []
    for event, want in expected.items():
        got = rows.get(event, 0)
        if got != want:
            divergences.append("событий %r: ожидается %d, в журнале %d" % (event, want, got))
    if not divergences and rows.get("assert", 0) - rows.get("retract", 0) != solved:
        divergences.append("assert минус retract не равно числу клеток '1'")

    return OracleResult("журнал: число событий", "НЕЗАВИСИМЫЙ",
                        sum(rows.values()), solved + 2 * withdrawn, divergences)


def differential(connection, workbook) -> OracleResult:
    """A second, independent read of the workbook against the projected journal.

    ВНУТРЕННИЙ: both sides descend from the same cells, so this cannot catch a systematic
    misreading of the book -- that is what the three oracles above are for.  What it does
    catch is anything lost, doubled or displaced between reading and projecting, and it is
    the only check that covers all 544 problems and all 29 920 cells.  It is also what
    makes the negative control bite: a corruption anywhere in the journal lands here.

    The read is genuinely second: it walks the workbook again from scratch rather than
    reusing the list ``import_workbook`` built, and the state it expects is derived from
    ``VALUE_REGISTRY`` while the state it compares against comes out of SQL through
    ``ProgressService``.
    """
    problem_ids, student_ids = _lookups(connection)
    states = _cell_states(connection)
    expected_state = {SOLVED: CellState.SOLVED, WITHDRAWN: CellState.RETRACTED,
                      EMPTY: CellState.EMPTY, QUARANTINE: CellState.EMPTY}

    checked = 0
    total = 0
    problems_seen = set()
    divergences = []
    for reading in read_cells(workbook):
        total += 1
        key = _student_key(reading.surname, reading.name, student_ids)
        problem_id = problem_ids.get((reading.sheet, reading.label))
        if key is None or problem_id is None:
            continue
        problems_seen.add(problem_id)
        checked += 1
        expected = expected_state[reading.meaning]
        got = states.get((student_ids[key], problem_id), CellState.EMPTY)
        if got is not expected:
            if len(divergences) < 40:
                divergences.append(
                    "%s · %s %s · %s · в книге %r → %s · в журнале %s"
                    % (reading.sheet, reading.surname, reading.name, reading.label,
                       reading.raw, expected.value, got.value)
                )
    return OracleResult(
        "полная сетка, задач %d из %d" % (len(problems_seen), len(problem_ids)),
        "ВНУТРЕННИЙ", checked, total, divergences,
    )


# ------------------------------------------------------------------- the negative control
#
# §5 of the задание, and the part that makes every number above mean anything.  Corrupt the
# journal three ways; the checks MUST go red on each.  A green on a corruption is a failure
# of this position, and the exit code says so.
#
# The corruptions run against a THROWAWAY copy of the database, and two of the three have
# to drop the append-only triggers to happen at all -- which is itself a small proof that
# the triggers are doing their job: a deletion cannot be performed by an honest caller.
# The triggers are put back immediately afterwards.

CORRUPTIONS = ("удалить событие из журнала", "перевернуть отметку (assert → retract)",
               "поменять местами двух учеников")


def _drop_append_only(connection) -> None:
    connection.execute("drop trigger if exists marks_append_only_update")
    connection.execute("drop trigger if exists marks_append_only_delete")


def corrupt(connection, which: str) -> str:
    """Break the journal one named way.  Returns what was broken, in words."""
    if which == CORRUPTIONS[0]:
        row = connection.execute(
            "select m.id, m.student_id, m.problem_id from marks m "
            "  where m.event = 'assert' and not exists "
            "        (select 1 from marks r where r.reverses_id = m.id) "
            "  order by m.id limit 1"
        ).fetchone()
        _drop_append_only(connection)
        connection.execute("delete from marks where id = ?", (row["id"],))
        connection.commit()
        return "удалено событие id=%d (ученик %d, задача %d)" % (
            row["id"], row["student_id"], row["problem_id"])

    if which == CORRUPTIONS[1]:
        row = connection.execute(
            "select m.id, m.student_id, m.problem_id from marks m "
            "  where m.event = 'assert' and not exists "
            "        (select 1 from marks r where r.reverses_id = m.id) "
            "  order by m.id limit 1"
        ).fetchone()
        _drop_append_only(connection)
        connection.execute(
            "update marks set event = 'retract', reverses_id = ? where id = ?",
            (row["id"], row["id"]),
        )
        connection.commit()
        return "отметка id=%d перевёрнута assert → retract" % row["id"]

    if which == CORRUPTIONS[2]:
        first, second = connection.execute(
            "select id, surname, name from students order by id limit 2"
        ).fetchall()
        connection.execute("update students set surname = ?, name = ? where id = ?",
                           ("__swap__", "__swap__", first["id"]))
        connection.execute("update students set surname = ?, name = ? where id = ?",
                           (first["surname"], first["name"], second["id"]))
        connection.execute("update students set surname = ?, name = ? where id = ?",
                           (second["surname"], second["name"], first["id"]))
        connection.commit()
        return "%s %s и %s %s поменялись местами" % (
            first["surname"], first["name"], second["surname"], second["name"])

    raise ValueError("неизвестная порча: %r" % which)


# ------------------------------------------------------------------------------- driving


def build(db_path, workbook) -> sqlite3.Connection:
    apply_migrations(db_path, config.MIGRATIONS_DIR)
    connection = connect(db_path)
    import_workbook(connection, workbook)
    return connection


def all_checks(connection, workbook) -> list:
    return [
        oracle_graveyard(connection, workbook),
        oracle_hand_cells(connection, workbook),
        oracle_debts(connection, workbook),
        oracle_credit(connection, workbook),
        journal_cardinality(connection, workbook),
        differential(connection, workbook),
    ]


def _print_import(counts: ImportCounts) -> None:
    print("ИМПОРТ")
    print("    отметок записано %d (assert %d, retract %d; из них несущих под 'x' %d)"
          % (counts.marks_written, counts.asserts, counts.retracts, counts.carriers))
    print("    учеников сопоставлено %d, не сопоставлено %d"
          % (counts.students_matched, len(counts.students_unmatched)))
    for surname, name in counts.students_unmatched:
        print("        НЕ СОПОСТАВЛЕН: %s %s" % (surname, name))
    print("    first_sheet_id проставлен явно у %d, осталось NULL: %d"
          % (counts.first_sheet_set, counts.first_sheet_null))
    if counts.first_sheet_disagreements:
        for surname, name, expected, got in counts.first_sheet_disagreements:
            print("        РАСХОЖДЕНИЕ с seed/students.csv: %s %s — в засеве %s, по книге %s"
                  % (surname, name, expected, got))
    else:
        print("        расхождений с колонкой first_sheet в seed/students.csv нет, "
              "сверено %d из %d" % (counts.first_sheet_set, counts.first_sheet_set))
    print("    карантин (значения без домена в модели), %d:" % len(counts.quarantined))
    for sheet, surname, name, label, raw in counts.quarantined:
        print("        листок %s · %s %s · задача %s · значение %r — события не записано"
              % (sheet, surname, name, label, raw))
    print("    отметок с составным принимающим: %d" % counts.composite_marks)
    print("    преподавателей дозаведено %d:" % len(counts.teachers_added))
    for name, why in counts.teachers_added:
        print("        %s — %s" % (name, why))
    for sheet_number, was, now in counts.repairs:
        print("    метка починена: листок %s, %r → %r (дубль, запрещённый схемой)"
              % (sheet_number, was, now))


def command_inventory(workbook) -> int:
    print("ИНВЕНТАРЬ ИСТОЧНИКА — все различные значения области отметок")
    readings = read_cells(workbook)
    counts = inventory(readings)
    for value, count in counts.most_common():
        print("    %8d  %-8r → %s" % (count, value, VALUE_REGISTRY[value]))
    print("    ИТОГО клеток %d" % sum(counts.values()))
    print("    известных значений в реестре: %d; на незнакомом импорт падает"
          % len(VALUE_REGISTRY))
    return 0


def command_check(workbook) -> int:
    with tempfile.TemporaryDirectory() as directory:
        db_path = Path(directory) / "import.db"
        apply_migrations(db_path, config.MIGRATIONS_DIR)
        connection = connect(db_path)
        _print_import(import_workbook(connection, workbook))
        results = _report(connection, workbook)
        connection.close()
    return 0 if not any(result.is_red for result in results) else 1


def _report(connection, workbook) -> list:
    print()
    print("ПРОВЕРКА")
    results = all_checks(connection, workbook)
    print()
    for result in results:
        print("    " + result.line())
        for divergence in result.divergences[:12]:
            print("        РАСХОЖДЕНИЕ: %s" % divergence)
        if len(result.divergences) > 12:
            print("        … и ещё %d" % (len(result.divergences) - 12))
        for known in result.known_defects:
            print("        ДЕФЕКТ КНИГИ (разобран, в реестре): %s" % known)
    return results


def command_negative_control(workbook) -> int:
    """Corrupt three ways; demand red on each.  Green on a corruption fails the position."""
    print("НЕГАТИВНЫЙ КОНТРОЛЬ — порчу вносим нарочно, проверка ОБЯЗАНА покраснеть")
    reddened = 0
    for which in CORRUPTIONS:
        with tempfile.TemporaryDirectory() as directory:
            connection = build(Path(directory) / "negative.db", workbook)
            before = all_checks(connection, workbook)
            if any(result.is_red for result in before):
                print("    [ПРОВАЛ] до порчи уже красное — контроль бессмыслен")
                connection.close()
                return 1
            what = corrupt(connection, which)
            after = all_checks(connection, workbook)
            red = [result.name for result in after if result.is_red]
            connection.close()
        if red:
            reddened += 1
            print("    [покраснело] %-42s %s" % (which, what))
            print("                 поймали: %s" % ", ".join(red))
        else:
            print("    [ПРОВАЛ · ЗЕЛЁНОЕ НА ПОРЧЕ] %-30s %s" % (which, what))
    print()
    print("    порч %d из %d, покраснело %d" % (len(CORRUPTIONS), len(CORRUPTIONS), reddened))
    return 0 if reddened == len(CORRUPTIONS) else 1


def main(argv=None) -> int:
    """Returns an exit code, ALWAYS.  The previous version returned None -- so the test
    could not fail physically, whatever it found."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--inventar", action="store_true",
                        help="показать все различные значения источника и выйти")
    parser.add_argument("--proverit", action="store_true",
                        help="импортировать и прогнать все оракулы")
    parser.add_argument("--negativnyj-kontrol", action="store_true",
                        help="внести три порчи; проверка обязана покраснеть на каждой")
    parser.add_argument("--kniga", type=Path, default=None,
                        help="путь к книге; по умолчанию config.KONDUIT_XLSX")
    arguments = parser.parse_args(argv)

    if not (arguments.inventar or arguments.proverit or arguments.negativnyj_kontrol):
        parser.print_help()
        return 2

    try:
        workbook = open_workbook(arguments.kniga)
    except SourceMissing as error:
        print(error, file=sys.stderr)
        return 3

    if arguments.inventar:
        return command_inventory(workbook)
    if arguments.negativnyj_kontrol:
        return command_negative_control(workbook)
    return command_check(workbook)


if __name__ == "__main__":
    sys.exit(main())
