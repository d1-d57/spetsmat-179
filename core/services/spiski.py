"""The lists the viewing screens are made of.  Every number here comes from P1.

WHAT THIS FILE IS ALLOWED TO DO.  Shape lists.  Group, order, cut and carry coverage.
It does NOT recompute a plus, a debt or a graveyard: ``core/services/progress.py`` owns
all three, and a second way of counting the same thing is exactly the class of bug the
differential test of P1 was written to close.  ``graveyard`` below is a delegation and a
sort; ``debts`` is a delegation and a split.

THE ONE THING THAT IS GENUINELY NEW HERE IS SILENCE, AND IT NEEDS A SESSION.

The task names ``core/services/sessions.py`` (P6) as the source of attendance.  That file
does not exist in this repository, no port reads the ``sessions`` or ``attendance`` tables
the migration creates, and ``marks.session_id`` is NULL on every row that exists: P2's
importer inserts without it and P4's grid router does not pass it.  A silence rule keyed
on ``session_id`` would therefore report all fifty-six students silent on its first day.

So a LESSON DAY is the date part of ``Mark.valid_at``, and the sequence of lesson days is
taken from the WHOLE journal rather than from the students being looked at.  A day on
which one particular group handed in nothing is still a day that happened, and a
per-group day sequence would quietly hide precisely the group that went quiet.

TWO CONSEQUENCES, WRITTEN DOWN BECAUSE THEY ARE VISIBLE ON THE REAL DATA.

* Last year's import is ONE lesson day.  All 15 847 events share a single ``valid_at``
  because the paper book records no per-session dates anywhere.  Nothing is lost that was
  ever there -- but it means the silent list only starts saying something once the bot
  itself has been writing marks for ``config.SILENT_SESSIONS`` real days.  The result
  object says so through ``enough_days`` rather than returning an empty list, because an
  empty list of silent students reads like good news and would be a lie.
* An ``erratum`` is not activity, AND NEITHER IS THE EVENT IT STRIKES OUT.  It is the
  statement that a record should never have existed, and the record is a separate row:
  discounting only the erratum would leave a teacher's mistyped button standing as this
  student's activity for the day, which takes the one student the screen exists to
  surface straight off the list.  An ``assert`` and a ``retract`` both ARE activity -- a
  retract is a hand-in that was not defended, which is a conversation that happened.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import config
from core.models import GraveyardRow, MarkEvent, Sheet, Student
from core.ports import Catalogue, MarkJournal
from core.services.progress import ProgressService

#: How many of the most recent sheets the graveyard list covers.  The teacher's first
#: screen names problems nobody took on the sheet being handed in now AND on the one
#: before it -- the previous sheet is where a graveyard is already final, and the current
#: one is where it can still be rescued in the room.
#:
#: THIS NUMBER BELONGS IN ``config.py`` and is here instead because ``config.py`` is
#: read-only from the position that wrote this file.  The debt is named in ``## ВОПРОСЫ``
#: of ``zhurnal/2026-09-02_spetsmat-bot/kod_P5-ekrany.md``; it is a named constant rather
#: than a literal so that moving it is one edit and not a search.
RECENT_SHEETS = 2

#: How many sheets of debt are shown problem by problem.  Everything older collapses into
#: a single line with no enumeration: a long list of what you owe is a message about the
#: PERSON, and the door stays open either way -- it is Konstantinov's own rule, you fall
#: out if you do not hand it in and you may come back the moment you do.
#:
#: COUNTED OVER SHEETS THAT ACTUALLY CARRY A DEBT, not over the sheets behind the current
#: one, and that is a measurement rather than a preference: the last four sheets of the
#: seed (``1д``-``4д``) carry no obligatory problems at all, so a window of "the two sheets
#: before the current one" is empty on the real data and the screen would never name a
#: boundary -- which is the one thing the task asks it to do.  «Ближайшая граница» is the
#: nearest sheet where something is in fact owed.
#:
#: Same home as ``RECENT_SHEETS``, same reason, same queue item.
DEBT_HORIZON_SHEETS = 2


# --------------------------------------------------------------------------- results
#
# Every result object below carries its own COVERAGE.  "три молчуна" and "три молчуна из
# пятидесяти шести за три занятия" look the same on a screen and are not the same fact,
# and the one place where that can be guaranteed is the value the screen is drawn from.


@dataclass(frozen=True)
class SilentStudent:
    """One student who handed nothing in, and when they last did."""

    student: Student
    #: The last lesson day this student was active on, or ``None`` if never.
    last_active_day: Optional[str] = None


@dataclass(frozen=True)
class SilentList:
    """Who has been quiet, over which days, out of how many students."""

    students: list = field(default_factory=list)
    #: The lesson days the silence was measured over, ascending.
    days: list = field(default_factory=list)
    #: How many students were examined.  Without it "нашлось ноль" is unreadable.
    considered: int = 0
    #: False when the journal holds fewer lesson days than were asked for.  The list is
    #: then empty NOT because everyone spoke, but because there is nothing to measure.
    enough_days: bool = True

    @property
    def found(self) -> int:
        return len(self.students)


@dataclass(frozen=True)
class GraveyardEntry:
    """One graveyard problem, together with the sheet it came from."""

    sheet: Sheet
    row: GraveyardRow


@dataclass(frozen=True)
class GraveyardList:
    """Problems almost nobody took, over the sheets that were looked at."""

    entries: list = field(default_factory=list)
    sheets: list = field(default_factory=list)
    #: How many students the counts were taken over.
    considered: int = 0
    #: The threshold that decided what counts as a graveyard, so the screen can state it.
    threshold: int = config.GRAVEYARD_THRESHOLD

    @property
    def found(self) -> int:
        return len(self.entries)


@dataclass(frozen=True)
class DebtGroup:
    """The obligatory problems still standing on one sheet."""

    sheet: Sheet
    problems: list = field(default_factory=list)


@dataclass(frozen=True)
class DebtList:
    """The short debt list: the nearest boundary enumerated, everything older collapsed."""

    #: The ``DEBT_HORIZON_SHEETS`` most recent sheets that carry a debt, newest first.
    near: list = field(default_factory=list)
    #: How many obligatory problems stand on sheets older than the horizon.
    older_problems: int = 0
    #: Over how many sheets those older problems are spread.
    older_sheets: int = 0

    @property
    def total(self) -> int:
        return sum(len(group.problems) for group in self.near) + self.older_problems

    @property
    def is_clear(self) -> bool:
        return self.total == 0


@dataclass(frozen=True)
class YearRow:
    """One sheet of the student's own year: how many of its problems are credited."""

    sheet: Sheet
    solved: int
    total: int


# --------------------------------------------------------------------------- service


class SpiskiService:
    """Lists over the journal and over P1's projections.  Reads only; writes nothing."""

    def __init__(
        self,
        journal: MarkJournal,
        catalogue: Catalogue,
        progress: ProgressService,
    ) -> None:
        self._journal = journal
        self._catalogue = catalogue
        self._progress = progress

    # ------------------------------------------------------------------ catalogue

    def active_students(self) -> list:
        """Everyone on the belt, in the catalogue's own surname order.

        A student whose status is ``left`` stays in the catalogue -- the journal points at
        their rows forever -- but they are not somebody a teacher failed to talk to this
        week, and leaving them in the silent list would put a permanent name at the top
        of the screen the whole feature exists to make readable.
        """
        return [s for s in self._catalogue.students() if s.status != "left"]

    def current_sheet(self) -> Optional[Sheet]:
        """The sheet being worked on now: the largest ``ord``.

        ``None`` on an empty catalogue, which is a real state before the importer has ever
        run and not an error to raise inside a handler.
        """
        sheets = self._catalogue.sheets()
        return max(sheets, key=lambda sheet: sheet.ord) if sheets else None

    def recent_sheets(self, count: int = RECENT_SHEETS) -> list:
        """The last ``count`` sheets by ``ord``, newest first."""
        sheets = sorted(self._catalogue.sheets(), key=lambda sheet: sheet.ord)
        return list(reversed(sheets[-count:])) if count > 0 else []

    # --------------------------------------------------------------------- silence

    def _activity_by_day(self) -> tuple:
        """``(all_days, days_by_student)`` -- one pass over the journal, one query.

        The whole journal is read because the DAY SEQUENCE is a property of the school and
        not of any one group.  Fifteen thousand rows out of SQLite on the connection the
        bot already holds is a few tens of milliseconds, which is inside the budget of a
        screen that opens once per lesson -- and it is named here rather than measured
        again by whoever reads this next.
        """
        events = self._journal.events()

        # An erratum strikes its target OUT, and the target is a separate row that would
        # otherwise still be counted: the erratum says the record should never have
        # existed, so BOTH rows have to go.  Skipping only the erratum itself would leave
        # a teacher's mistyped button standing as this student's activity for the day --
        # which is precisely the student the screen exists to surface.  The schema allows
        # one reversal per event (``marks_reverses_once``), so this set cannot grow a
        # second claim on the same row.
        struck = {
            mark.reverses_id
            for mark in events
            if mark.event is MarkEvent.ERRATUM and mark.reverses_id is not None
        }

        all_days: set = set()
        days_by_student: dict = {}
        for mark in events:
            if mark.event is MarkEvent.ERRATUM or mark.id in struck:
                continue
            day = mark.valid_at[:10]
            all_days.add(day)
            days_by_student.setdefault(mark.student_id, set()).add(day)
        return all_days, days_by_student

    def lesson_days(self) -> list:
        """Every day the journal has activity on, ascending."""
        all_days, _ = self._activity_by_day()
        return sorted(all_days)

    def silent(self, sessions: Optional[int] = None) -> SilentList:
        """Students who handed nothing in over the last ``sessions`` lesson days.

        Default ``sessions`` is ``config.SILENT_SESSIONS`` -- the length of a silence that
        gets noticed, and it is read from ``config.py`` rather than written as a three,
        because the number is the school's and not this screen's.

        Fewer lesson days in the journal than were asked for is NOT an empty answer: the
        list comes back empty with ``enough_days=False``, and the screen says there is
        nothing to measure yet.  An empty silent list reads as "everybody is fine".
        """
        wanted = config.SILENT_SESSIONS if sessions is None else sessions
        all_days, days_by_student = self._activity_by_day()
        ordered = sorted(all_days)
        window = set(ordered[-wanted:]) if wanted > 0 else set()

        students = self.active_students()
        if len(ordered) < wanted or not window:
            return SilentList(
                students=[],
                days=sorted(window),
                considered=len(students),
                enough_days=False,
            )

        quiet = []
        for student in students:
            seen = days_by_student.get(student.id, set())
            if seen & window:
                continue
            quiet.append(
                SilentStudent(
                    student=student,
                    last_active_day=max(seen) if seen else None,
                )
            )
        return SilentList(
            students=quiet,
            days=sorted(window),
            considered=len(students),
            enough_days=True,
        )

    # ------------------------------------------------------------------- graveyard

    def graveyard(self, sheets: Optional[list] = None) -> GraveyardList:
        """Problems almost nobody took, over the most recent sheets.

        The counting is ``ProgressService.graveyard`` and the threshold is
        ``GraveyardRow.is_graveyard``, which reads ``config.GRAVEYARD_THRESHOLD`` in P1's
        single place.  Nothing here re-spells either one.

        Ordered by how few students took the problem, then newest sheet first -- «л.6 №11
        (0), л.6 №14 (1), л.5 №19 (2)» is the order the teacher reads it in, because the
        first line is the one worth saying out loud in the room.
        """
        looked_at = self.recent_sheets() if sheets is None else list(sheets)
        student_ids = [s.id for s in self.active_students()]

        entries = []
        for sheet in looked_at:
            for row in self._progress.graveyard(sheet.id, student_ids=student_ids):
                if row.is_graveyard:
                    entries.append(GraveyardEntry(sheet=sheet, row=row))
        entries.sort(key=lambda e: (e.row.taken_by, -e.sheet.ord, e.row.problem.ord))
        return GraveyardList(
            entries=entries,
            sheets=looked_at,
            considered=len(student_ids),
            threshold=self._progress.graveyard_threshold(),
        )

    # ----------------------------------------------------------------------- debts

    def debts(self, student_id: int) -> DebtList:
        """The student's own debts, cut into "the nearest boundary" and "older".

        ``ProgressService.debts`` decides WHAT is owed -- obligatory, unsolved, on a sheet
        the student was actually present for.  This method only decides how much of it a
        person should be made to read at once.
        """
        current = self.current_sheet()
        if current is None:
            return DebtList()

        owed = self._progress.debts(student_id, current.ord)
        if not owed:
            return DebtList()

        by_sheet: dict = {}
        for problem in owed:
            by_sheet.setdefault(problem.sheet_id, []).append(problem)

        groups = []
        older_problems = 0
        older_sheets = 0
        for sheet_id, problems in by_sheet.items():
            sheet = self._catalogue.sheet(sheet_id)
            if sheet is None:
                # A debt on a sheet the catalogue does not have is not something to drop
                # in silence: it still counts, it just cannot be named.
                older_problems += len(problems)
                older_sheets += 1
                continue
            groups.append(
                DebtGroup(sheet=sheet, problems=sorted(problems, key=lambda p: (p.ord, p.id)))
            )

        groups.sort(key=lambda group: group.sheet.ord, reverse=True)
        near, older = groups[:DEBT_HORIZON_SHEETS], groups[DEBT_HORIZON_SHEETS:]
        for group in older:
            older_problems += len(group.problems)
            older_sheets += 1
        return DebtList(
            near=near,
            older_problems=older_problems,
            older_sheets=older_sheets,
        )

    # ------------------------------------------------------------------ own year

    def year(self, student_id: int) -> list:
        """Every sheet of the year with the student's own credited count.

        ONE ``states_for`` call over every problem of every sheet, not eighteen grids: the
        first screen a student opens on the first of September draws the whole year, and
        eighteen round trips to draw one message is how a screen becomes slow for no
        reason a reader can see.
        """
        sheets = sorted(self._catalogue.sheets(), key=lambda sheet: sheet.ord)
        if not sheets:
            return []

        problems_by_sheet = {
            sheet.id: self._catalogue.problems_of_sheet(sheet.id) for sheet in sheets
        }
        every_problem = [p.id for problems in problems_by_sheet.values() for p in problems]
        states = self._progress.states_for(student_id, every_problem)

        rows = []
        for sheet in sheets:
            problems = problems_by_sheet[sheet.id]
            solved = sum(1 for p in problems if states[p.id].is_credited)
            rows.append(YearRow(sheet=sheet, solved=solved, total=len(problems)))
        return rows

    def sheet_states(self, student_id: int, sheet_id: int) -> tuple:
        """``(problems, states)`` of one sheet for one student, through P1's projection."""
        problems = self._catalogue.problems_of_sheet(sheet_id)
        states = self._progress.states_for(student_id, [p.id for p in problems])
        return problems, states

    def sheet_table(self, sheet_id: int) -> tuple:
        """``(problems, students, states)`` for the whole class over one sheet.

        One rectangle in one query -- ``states_for_many`` exists precisely so that a table
        of fifty-six rows is not fifty-six round trips.
        """
        problems: list = self._catalogue.problems_of_sheet(sheet_id)
        students: list = self.active_students()
        states = self._progress.states_for_many(
            [s.id for s in students], [p.id for p in problems]
        )
        return problems, students, states
