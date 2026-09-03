"""Import last year's teacher assignments into ``enrollment`` through ``EnrollmentService``.

The source is ``_studio/veb-raspredelenie/baza-2025-26.json``, the workbook the owner
exported from his spreadsheet.  It carries 54 assignments across 17 teachers for the 56
students of his school, and is documented as a DRAFT — the 2026/27 teaching staff has
changed since.  This script is the seed, not the truth: anything it cannot resolve is
named in the report and skipped, never invented.

INTERVAL MODEL.

The store keeps ``enrollment`` as a half-open interval per ``(student_id, weekday)``
with ``valid_to = config.OPEN_END_DATE`` for the open row.  The source has no weekday
column and no explicit start date: last year ran two lesson days (Mon and Thu) per
student.  Three reasons make weekday = Monday (ISO 1) the one interval we open here:

  * the source lists one teacher per child, not two — there is no way to write two
    rows from a single source row;
  * the schema forbids two OPEN rows for the same ``(student_id, weekday)``, so
    opening two of them would either fail or, worse, fail to fail;
  * the page (``veb/``) lets the owner fix the day of the week interactively, which
    is the point of having a web surface instead of a static export.

VALID_FROM defaults to the first business day of the current school year — the
earlier of 1 September of the calendar year or today.  The owner can move it through
the page; ``move`` closes the old interval and opens a new one, so the choice here
only seeds the picture.

IDEMPOTENCY.

A second run on the same database MUST NOT open a second open row for the same
``(student, weekday)``.  For every row of the source the script first reads the open
interval:

  * no open row  -> ``assign``;
  * open row, same teacher  -> nothing happens, counted as "already correct";
  * open row, different teacher  -> ``move`` from today to that teacher, which closes
    the old interval and opens a new one atomically.

``assign`` and ``move`` are the only writers; the partial unique index in the schema
guarantees no duplicate open row sneaks past them.

OUT OF SCOPE.

Composite teachers ("Саша Оревкова / Ольга Александровна" and two more) cannot be
expressed by a single ``teacher_id`` and are skipped with an explicit reason.  Missing
students (a typo in the source, a child who left) are skipped likewise.  Missing
teachers are skipped with a reason — the brief says the staff changed and gaps are
expected.  Nothing here invents a name that was not in ``students`` or ``teachers``
to begin with.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from core.services.enrollment import (
    AlreadyEnrolled,
    EnrollmentError,
    EnrollmentService,
)
from infra.db import connect
from infra.enrollment_repo import SqliteEnrollmentRepo


SOURCE_DEFAULT = Path("_studio/veb-raspredelenie/baza-2025-26.json")

# ISO weekday Monday = 1.  See module docstring for the why.
WEEKDAY_MONDAY = 1


@dataclass(frozen=True)
class Outcome:
    """One row of the final report."""

    surname: str
    name: str
    teacher: str
    status: str
    reason: str = ""

    def line(self) -> str:
        if self.reason:
            return f"  - {self.surname} {self.name} <- {self.teacher}: {self.status} ({self.reason})"
        return f"  - {self.surname} {self.name} <- {self.teacher}: {self.status}"


# --------------------------------------------------------------------- lookups

def _student_index(connection: sqlite3.Connection) -> dict[tuple[str, str], int]:
    """``{(surname, name): student_id}`` for every active catalogue row.

    A student who has LEFT is not a target for an enrolment: the script would open an
    interval for someone who is no longer in the school.  ``active`` and ``pending``
    rows are kept — a pending child may be enrolled ahead of their confirmation.
    """
    rows = connection.execute(
        "select id, surname, name from students "
        "where status is null or status in ('active', 'pending')"
    ).fetchall()
    return {(row["surname"], row["name"]): row["id"] for row in rows}


def _teacher_index(connection: sqlite3.Connection) -> dict[str, tuple[int, str]]:
    """``{teacher name: (teacher_id, room)}``.

    The room comes from the source JSON, not from the database: the database has no
    ``room`` column on ``teachers`` (the role/room split lives in a separate file),
    and the brief says the room is the teacher's room — that is in the source and
    that is where it stays.

    The name lookup is case-insensitive on the first character only: source names are
    written in title case ("Ваня") and database rows in the same case, but a stray
    space or apostrophe would silently miss.  Stripped equality is enough for this
    size of catalogue.
    """
    rows = connection.execute("select id, name from teachers").fetchall()
    out: dict[str, tuple[int, str]] = {}
    for row in rows:
        key = row["name"].strip().lower()
        out[key] = (row["id"], "")  # room is filled by the source lookup below
    return out


def _room_for_teacher(source: dict, teacher_name: str) -> Optional[str]:
    """The room a source teacher entry names.  ``None`` if the source has no such name."""
    for entry in source.get("prepodavateli", []):
        if entry.get("name") == teacher_name:
            return entry.get("room")
    return None


# --------------------------------------------------------------- one-row outcome

def _apply_one(
    service: EnrollmentService,
    *,
    student_id: int,
    teacher_id: int,
    room: str,
    weekday: int,
    effective_from: str,
    open_row,
) -> tuple[str, str]:
    """Decide assign vs move vs skip and call the service.  Returns ``(status, reason)``.

    ``open_row`` is the current open interval for ``(student_id, weekday)`` — the caller
    has already read it, so the service does not have to query twice.  ``None`` means
    there is no open row yet.
    """
    if open_row is None:
        try:
            service.assign(
                student_id=student_id,
                teacher_id=teacher_id,
                room=room,
                weekday=weekday,
                valid_from=effective_from,
            )
        except AlreadyEnrolled:
            # Race: someone else opened between our read and our write.  Re-read and
            # fall through to the move branch by reporting it the same way.
            return ("skipped", "open row appeared between read and write")
        return ("assigned", "")
    if open_row.teacher_id == teacher_id and open_row.room == room:
        return ("already correct", "")
    try:
        service.move(
            student_id=student_id,
            weekday=weekday,
            to_teacher_id=teacher_id,
            effective_from=effective_from,
            room=room,
        )
    except EnrollmentError as exc:
        return ("skipped", f"move refused: {exc}")
    return ("moved", "")


# --------------------------------------------------------------------- driver

def run(
    connection: sqlite3.Connection,
    source_path: Path,
    *,
    effective_from: str,
    dry_run: bool = False,
) -> list[Outcome]:
    """Walk the source once and report one ``Outcome`` per row.

    ``effective_from`` is the date the new or moved intervals open from.  Defaults
    outside this module to "today", so a caller that wants a different anchor can
    pass it explicitly (the test does).
    """
    source = json.loads(source_path.read_text(encoding="utf-8"))

    students = _student_index(connection)
    teachers = _teacher_index(connection)
    repo = SqliteEnrollmentRepo(connection)
    service = EnrollmentService(repo)

    outcomes: list[Outcome] = []
    for row in source.get("zakreplenie", []):
        surname = row.get("surname", "")
        first_name = row.get("name", "")
        teacher_name = row.get("teacher", "")

        if "/" in teacher_name:
            outcomes.append(
                Outcome(surname, first_name, teacher_name,
                        "skipped",
                        "composite teacher, single-id model cannot express it")
            )
            continue

        student_id = students.get((surname, first_name))
        if student_id is None:
            outcomes.append(
                Outcome(surname, first_name, teacher_name,
                        "skipped", "no student with this surname+name in the catalogue")
            )
            continue

        teacher_entry = teachers.get(teacher_name.strip().lower())
        if teacher_entry is None:
            outcomes.append(
                Outcome(surname, first_name, teacher_name,
                        "skipped", "no teacher with this name in the catalogue")
            )
            continue
        teacher_id, _ = teacher_entry

        room = _room_for_teacher(source, teacher_name)
        if not room:
            outcomes.append(
                Outcome(surname, first_name, teacher_name,
                        "skipped", "no room in source for this teacher")
            )
            continue

        open_row = repo.open_row(student_id, WEEKDAY_MONDAY)
        if dry_run:
            if open_row is None:
                outcomes.append(Outcome(surname, first_name, teacher_name, "would assign", ""))
            elif open_row.teacher_id == teacher_id and open_row.room == room:
                outcomes.append(Outcome(surname, first_name, teacher_name, "already correct", ""))
            else:
                outcomes.append(Outcome(surname, first_name, teacher_name, "would move", ""))
            continue

        status, reason = _apply_one(
            service,
            student_id=student_id,
            teacher_id=teacher_id,
            room=room,
            weekday=WEEKDAY_MONDAY,
            effective_from=effective_from,
            open_row=open_row,
        )
        outcomes.append(Outcome(surname, first_name, teacher_name, status, reason))

    return outcomes


def _summarise(outcomes: Iterable[Outcome]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for outcome in outcomes:
        counts[outcome.status] = counts.get(outcome.status, 0) + 1
    return counts


def _print_report(
    outcomes: list[Outcome], *, y_total: int, dry_run: bool
) -> int:
    counts = _summarise(outcomes)
    x_open = counts.get("assigned", 0) + counts.get("already correct", 0) + counts.get("moved", 0)
    print(f"Source rows Y = {y_total}")
    print(f"Net enrolled X = {x_open} (assigned + already correct + moved)")
    print(f"Skipped        = {counts.get('skipped', 0)}")
    if dry_run:
        print(f"Would move     = {counts.get('would move', 0)}")
        print(f"Would assign   = {counts.get('would assign', 0)}")
    print()
    by_status: dict[str, list[Outcome]] = {}
    for outcome in outcomes:
        by_status.setdefault(outcome.status, []).append(outcome)
    for status in sorted(by_status):
        print(f"[{status}]")
        for outcome in by_status[status]:
            print(outcome.line())
        print()
    # X = 0 with non-empty source is the only failure of the readiness gate.
    return 0 if (y_total == 0 or x_open > 0) else 1


def _default_effective_from(today: str) -> str:
    """1 September of the calendar year of ``today`` if that is in the past, else today.

    The seed must open intervals that are already valid when the page goes live, so
    a future date is no good; the page's ``move`` is what adjusts it from there.
    """
    year = today[:4]
    sept_first = f"{year}-09-01"
    return sept_first if sept_first <= today else today


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=SOURCE_DEFAULT)
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would happen, write nothing.")
    parser.add_argument("--effective-from", default=None,
                        help="YYYY-MM-DD the new intervals open from "
                             "(default: 1 Sep of the current year, or today).")
    args = parser.parse_args(argv)

    if not args.source.exists():
        print(f"source not found: {args.source}", file=sys.stderr)
        return 2

    from core.isotime import now_iso

    effective_from = args.effective_from or _default_effective_from(now_iso()[:10])

    connection = connect()
    try:
        # Foreign keys are enforced by ``infra.db.connect`` already.
        source = json.loads(args.source.read_text(encoding="utf-8"))
        y_total = len(source.get("zakreplenie", []))
        outcomes = run(
            connection, args.source,
            effective_from=effective_from, dry_run=args.dry_run,
        )
    finally:
        connection.close()

    return _print_report(outcomes, y_total=y_total, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())