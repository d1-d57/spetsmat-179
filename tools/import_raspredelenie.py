"""Import last year's teacher assignments into ``enrollment`` through ``EnrollmentService``.

The source is ``_studio/veb-raspredelenie/baza-2025-26.json``, the workbook the owner
exported from his spreadsheet.  It carries 54 assignments across 17 teachers for the 56
students of his school, and is documented as a DRAFT — the 2026/27 teaching staff has
changed since.  This script is the seed, not the truth: anything it cannot resolve is
named in the report and skipped, never invented.

INTERVAL MODEL.

The store keeps ``enrollment`` as a half-open interval per ``(student_id, slot)``
with ``valid_to = config.OPEN_END_DATE`` for the open row.  The source has no slot
column and no explicit start date: last year ran two lesson days (Mon and Thu) per
student.  A composite teacher ("Саша Оревкова / Ольга Александровна" and two more)
becomes TWO intervals, one per lesson day, with the same ``valid_from``:

  * the source names two people behind one slash — each one IS a lesson day, and the
    school runs two days a week;
  * the schema forbids two OPEN rows for the same ``(student_id, slot)``, so
    opening two of them on DIFFERENT slots does not collide;
  * the page (``veb/``) lets the owner fix the day of the week interactively, which
    is the point of having a web surface instead of a static export.

VALID_FROM defaults to the first business day of the current school year — the
earlier of 1 September of the calendar year or today.  The owner can move it through
the page; ``move`` closes the old interval and opens a new one, so the choice here
only seeds the picture.

One source trap to disarm before the slash test: "Мика/Вася" is ONE teacher's name in
``teachers``, and the source writes it with a slash because the owner writes it that
way.  A naive split would invent two non-existent people.  The script looks up the
full string in the catalogue FIRST; only if it does not resolve does it split on
``/``.

IDEMPOTENCY.

A second run on the same database MUST NOT open a second open row for the same
``(student, slot)``.  For every row of the source the script first reads the open
interval:

  * no open row  -> ``assign``;
  * open row, same teacher  -> nothing happens, counted as "already correct";
  * open row, different teacher  -> ``move`` from today to that teacher, which closes
    the old interval and opens a new one atomically.

``assign`` and ``move`` are the only writers; the partial unique index in the schema
guarantees no duplicate open row sneaks past them.

OUT OF SCOPE.

Missing students (a typo in the source, a child who left) are skipped with a reason.
Missing teachers are skipped with a reason — the brief says the staff changed and
gaps are expected.  A composite name where NONE of the parts resolve to a teacher is
also skipped: the FK would refuse the row, and inventing a placeholder would not help
the owner — the gap is named and the page is the path back.  Nothing here invents a
name that was not in ``students`` or ``teachers`` to begin with.
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
# The school runs two lesson days a week.  A composite teacher in the source is
# mapped to the same person on each day; the owner splits them through the page.
WEEKDAY_THURSDAY = 4

# Mapping from ISO weekday to slot (migration 003_slot_vmesto_weekday).
# weekday 1 (Mon) → slot 1, weekday 4 (Thu) → slot 2.
WEEKDAY_TO_SLOT = {1: 1, 4: 2}

# A composite teacher is written with this separator.  The catalogue has ONE name
# with a slash in it ("Мика/Вася"); see module docstring for the disarm.
COMPOSITE_SEP = "/"

# Status strings printed in the report.  Kept module-level so the test can match.
STATUS_ASSIGNED = "assigned"
STATUS_ALREADY = "already correct"
STATUS_MOVED = "moved"
STATUS_SKIPPED = "skipped"
STATUS_WOULD_ASSIGN = "would assign"
STATUS_WOULD_MOVE = "would move"


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


# --------------------------------------------------------- composite-teacher parsing

def _resolve_teacher_name(
    raw_name: str,
    teachers: dict[str, tuple[int, str]],
    source: dict,
) -> tuple[list[tuple[str, int, str]], list[str]]:
    """Split a slash-bearing source name into ``(part, teacher_id, room)`` triples.

    Returns ``(resolved, missing_parts)``:

    * ``resolved``  -- every part that mapped to a catalogue teacher, with its id and
      room from the source.  The caller opens one interval per entry.
    * ``missing_parts`` -- names from the slash split that did NOT resolve to a
      catalogue teacher; the report names each one so the owner can fix the source or
      the catalogue.

    Disarming: "Мика/Вася" IS one teacher's name in ``teachers`` and the source writes
    it with a slash.  If the full string resolves, it is treated as a SINGLE teacher,
    not as a composite.
    """
    def _room_for(name: str) -> str:
        return _room_for_teacher(source, name) or ""

    if COMPOSITE_SEP not in raw_name:
        entry = teachers.get(raw_name.strip().lower())
        if entry is None:
            return ([], [])
        teacher_id, _ = entry
        return ([(raw_name, teacher_id, _room_for(raw_name))], [])

    full = teachers.get(raw_name.strip().lower())
    if full is not None:
        teacher_id, _ = full
        return ([(raw_name, teacher_id, _room_for(raw_name))], [])

    parts = [p.strip() for p in raw_name.split(COMPOSITE_SEP) if p.strip()]
    resolved: list[tuple[str, int, str]] = []
    missing: list[str] = []
    for part in parts:
        entry = teachers.get(part.strip().lower())
        if entry is None:
            missing.append(part)
            continue
        teacher_id, _ = entry
        resolved.append((part, teacher_id, _room_for(part)))
    return resolved, missing


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

    ``open_row`` is the current open interval for ``(student_id, slot)`` — the caller
    has already read it, so the service does not have to query twice.  ``None`` means
    there is no open row yet.
    """
    slot = WEEKDAY_TO_SLOT[weekday]
    if open_row is None:
        try:
            service.assign(
                student_id=student_id,
                teacher_id=teacher_id,
                room=room,
                slot=slot,
                valid_from=effective_from,
            )
        except AlreadyEnrolled:
            return (STATUS_SKIPPED, "open row appeared between read and write")
        return (STATUS_ASSIGNED, "")
    if open_row.teacher_id == teacher_id and open_row.room == room:
        return (STATUS_ALREADY, "")
    try:
        service.move(
            student_id=student_id,
            slot=slot,
            to_teacher_id=teacher_id,
            effective_from=effective_from,
            room=room,
        )
    except EnrollmentError as exc:
        return (STATUS_SKIPPED, f"move refused: {exc}")
    return (STATUS_MOVED, "")


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

        student_id = students.get((surname, first_name))
        if student_id is None:
            outcomes.append(
                Outcome(surname, first_name, teacher_name,
                        STATUS_SKIPPED, "no student with this surname+name in the catalogue")
            )
            continue

        resolved, missing = _resolve_teacher_name(teacher_name, teachers, source)
        if not resolved:
            outcomes.append(
                Outcome(surname, first_name, teacher_name,
                        STATUS_SKIPPED,
                        "no teacher with this name in the catalogue")
            )
            continue

        # Decide the weekday(s): one entry → Monday; two entries → Monday AND Thursday.
        # The page lets the owner fix the day later; the seed opens both so the owner
        # does not start from a half-distribution.
        weekdays = [WEEKDAY_MONDAY]
        if len(resolved) > 1:
            weekdays.append(WEEKDAY_THURSDAY)

        first_outcome: Optional[Outcome] = None
        # Pair each resolved slot with its weekday; the order in ``weekdays`` matches
        # the order in ``resolved`` by construction (Monday first).
        for weekday, teacher_info in zip(weekdays, resolved):
            slot_name, teacher_id, room = teacher_info
            if not room:
                outcomes.append(
                    Outcome(surname, first_name, teacher_name,
                            STATUS_SKIPPED, "no room in source for this teacher")
                )
                continue

            open_row = repo.open_row(student_id, WEEKDAY_TO_SLOT[weekday])
            if dry_run:
                if open_row is None:
                    outcome = Outcome(surname, first_name, slot_name, STATUS_WOULD_ASSIGN, "")
                elif open_row.teacher_id == teacher_id and open_row.room == room:
                    outcome = Outcome(surname, first_name, slot_name, STATUS_ALREADY, "")
                else:
                    outcome = Outcome(surname, first_name, slot_name, STATUS_WOULD_MOVE, "")
                if first_outcome is None:
                    first_outcome = outcome
                outcomes.append(outcome)
                continue

            status, reason = _apply_one(
                service,
                student_id=student_id,
                teacher_id=teacher_id,
                room=room,
                weekday=weekday,
                effective_from=effective_from,
                open_row=open_row,
            )
            outcome = Outcome(surname, first_name, slot_name, status, reason)
            if first_outcome is None:
                first_outcome = outcome
            outcomes.append(outcome)

        if missing:
            # One row per missing part so the owner can fix each one independently.
            for part in missing:
                outcomes.append(
                    Outcome(surname, first_name, part,
                            STATUS_SKIPPED,
                            "composite teacher, part not in catalogue; assign through the page")
                )

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
    x_open = (
        counts.get(STATUS_ASSIGNED, 0)
        + counts.get(STATUS_ALREADY, 0)
        + counts.get(STATUS_MOVED, 0)
    )
    print(f"Source rows Y = {y_total}")
    print(f"Net enrolled X = {x_open} (assigned + already correct + moved)")
    print(f"Skipped        = {counts.get(STATUS_SKIPPED, 0)}")
    if dry_run:
        print(f"Would move     = {counts.get(STATUS_WOULD_MOVE, 0)}")
        print(f"Would assign   = {counts.get(STATUS_WOULD_ASSIGN, 0)}")
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