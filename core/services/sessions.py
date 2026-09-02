"""Lessons and attendance.

A lesson is created by a human, not by a calendar -- the timetable is a school
timetable, twice a week, and there are cancellations and holidays.  Attendance
is recorded separately from marks: a student may come and hand in nothing, and
by pluses that is indistinguishable from truancy, and the difference matters
(it is the difference between "he was not asked" and "he was not there").

A back-dated mark asks for the date and may be spread over several days.  The
``MarkingService`` of P1 already carries ``valid_at`` (when the check-off
happened) and ``recorded_at`` (when it reached the database) on every journal
row, so this service is what USES them: it does not introduce a second clock.

Display goes through ``ZoneInfo(config.TZ_DISPLAY)``, never a hardcoded offset
that is wrong twice a year in any country that still shifts its clock.

NOTHING here imports sqlite3 and NOTHING here imports any Telegram library.
The store lives behind two Protocols (``SessionBook`` and ``AttendanceBook``)
that a SQLite adapter in ``infra/sessions_repo.py`` implements.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, Protocol, Sequence
from zoneinfo import ZoneInfo

import config
from core.isotime import to_iso
from core.models import CellState, Session, Sheet
from core.ports import Catalogue, Clock, MarkJournal
from core.services.marking import MarkingOutcome, MarkingService


def parse_iso_date(text: str) -> date:
    """``YYYY-MM-DD`` → ``date``.  The schema's GLOB guarantees the format."""
    return datetime.strptime(text, "%Y-%m-%d").date()


def _today_in_display_zone(clock: Clock) -> date:
    """The date the service treats as "today", from the injected ``Clock``.

    The wall clock is the wrong thing to read: a test that wants to verify
    "valid_at in the future is refused" cannot freeze the machine, and a
    production system running in a foreign zone would compute today against
    the wrong civil day.  The Clock protocol is the one seam already in the
    service, and the rest of P1 already uses it; the display date is the
    same now() read through ``ZoneInfo(TZ_DISPLAY)``.
    """
    return datetime.fromisoformat(clock.now_iso().replace("Z", "+00:00")) \
        .astimezone(ZoneInfo(config.TZ_DISPLAY)).date()


# --------------------------------------------------------------------------- errors


class SessionsError(Exception):
    """A sessions/attendance request the domain refuses."""


class LessonNotFound(SessionsError):
    """No lesson for the given id (or for the given date)."""


class InvalidLessonDate(SessionsError):
    """A ``held_on`` in the future, or a back-dated mark earlier than the problem's
    sheet was issued, or a ``valid_at`` that is not the date of a real lesson."""


class AttendanceAlreadyStanding(SessionsError):
    """A second tap of the SAME status -- answered by idempotency, not by raising."""


# --------------------------------------------------------------------------- domain


@dataclass(frozen=True)
class AttendanceRow:
    """One row of the ``attendance`` table, as the service sees it.

    The two times from P1's ``Mark`` are not repeated here on purpose: attendance
    is a single fact ("this student on this lesson") and the schema does not
    carry a second clock for it.  ``id`` is the row id, not a status code, so a
    caller can update the existing row without a second SELECT.
    """

    id: int
    session_id: int
    student_id: int
    teacher_id: Optional[int]
    status: str  # 'был' or 'не был'


@dataclass(frozen=True)
class AttendanceOutcome:
    """What ``mark_attendance`` did about one request.

    ``written`` is False on the idempotent path: the same status was already
    standing for this (session, student).  A second tap with a DIFFERENT status
    overwrites the previous one -- a teacher who first tapped ``не был`` and
    then corrected to ``был`` after the student actually arrived has not made
    a mistake, and the service must reflect that.
    """

    row: AttendanceRow
    written: bool
    changed: bool  # True iff the new status differs from the previous one


@dataclass(frozen=True)
class AttendanceView:
    """The position's read model: one student, one lesson, BOTH facts together.

    The whole reason P6 exists: ``(status, has_marks)`` is the cell of the
    "who was here and what did they hand in" grid.  ``status`` is the raw value
    on the ``attendance`` row (``'был'``, ``'не был'``, or ``None`` if there is
    no row at all); ``has_marks`` says whether the journal holds at least one
    event for the (student, lesson) pair.  ``present_no_marks`` is the
    red-line derivation: True iff the student is marked present AND has
    nothing in the journal.  The interface code (P4, P13) draws its button off
    this single fact; the test that IS this position asserts that (b) "был, no
    marks" and (c) "не был" are DIFFERENT values of this dataclass.
    """

    student_id: int
    status: Optional[str]
    has_marks: bool

    @property
    def present_no_marks(self) -> bool:
        return self.status == "был" and not self.has_marks

    @property
    def is_marked(self) -> bool:
        return self.status is not None


@dataclass(frozen=True)
class MarkLessonItem:
    """One (student, problem) with its own ``valid_at``.

    A batch may be spread across several days, so the API takes the date with
    the mark, not the date with the batch.  ``valid_at`` is the date of the
    lesson the mark belongs to (``YYYY-MM-DD``), and the service looks up
    the lesson for that date; if there is no lesson that day, the item is
    refused with ``InvalidLessonDate``.
    """

    student_id: int
    problem_id: int
    valid_on: date
    source: str = "кнопка"
    teacher_id: Optional[int] = None
    note: Optional[str] = None


# --------------------------------------------------------------------------- ports


class SessionBook(Protocol):
    """Persistence for ``sessions`` rows.

    A lesson is a row of ``(held_on, kind)``; the only lifecycle is create
    and read.  The service owns the validation (kind, future date) -- the
    port is the thinnest possible seam.
    """

    def create(self, held_on: str, kind: str) -> Session:
        """Write the lesson and return it with the id the store assigned."""

    def find_on(self, held_on: str) -> Optional[Session]:
        """The lesson of this date, or None if there is no lesson that day."""

    def by_id(self, session_id: int) -> Optional[Session]:
        """The lesson of this id, or None if it has been removed."""

    def recent(self, limit: int) -> list[Session]:
        """The most recent lessons, newest first, at most ``limit`` of them."""


class AttendanceBook(Protocol):
    """Persistence for ``attendance`` rows.

    The schema's ``unique(session_id, student_id)`` is the carrier: a raw
    second INSERT would raise ``IntegrityError``.  The port folds that into a
    single ``mark`` call that does INSERT-or-UPDATE atomically, so the
    service can treat every tap as a normal request.
    """

    def mark(
        self,
        session_id: int,
        student_id: int,
        status: str,
        teacher_id: Optional[int],
    ) -> tuple[AttendanceRow, bool, bool]:
        """Record (or update) attendance and return ``(row, written, changed)``.

        ``written`` is True iff a row was inserted (first tap).  ``changed``
        is True iff the new status differs from the previous one (a teacher
        corrected an earlier tap).
        """

    def list_for_session(self, session_id: int) -> list[AttendanceRow]:
        """Every attendance row of this session, in insertion order.  Used
        by the position's read model to distinguish "present, no marks" from
        "absent".
        """


# --------------------------------------------------------------------------- service


class SessionsService:
    """The whole surface that P4 and P13 will call.

    The service owns the rule that a lesson is created by a human, that an
    attendance tap is idempotent on the same status, and that a back-dated
    mark's ``valid_at`` cannot be earlier than the problem's sheet was issued.
    The store does the SQL.
    """

    def __init__(
        self,
        session_book: SessionBook,
        attendance_book: AttendanceBook,
        marking: MarkingService,
        journal: MarkJournal,
        catalogue: Catalogue,
        clock: Clock,
    ) -> None:
        self._lessons = session_book
        self._attendance = attendance_book
        self._marking = marking
        self._journal = journal
        self._catalogue = catalogue
        self._clock = clock

    # --------------------------------------------------------- lessons (Section 1)

    def create_lesson(self, held_on: date, kind: str) -> Session:
        """Create a lesson on a date with a kind.  Refuses a kind outside
        ``config.SESSION_KINDS`` and a ``held_on`` in the future.

        Display of ``held_on`` goes through ``ZoneInfo(config.TZ_DISPLAY)`` so
        a Moscow user and a Berlin server agree on which day the lesson was
        on; the display offset is never hardcoded, since any country that
        still shifts its clock would be wrong twice a year.  "Today" is taken
        from the injected ``Clock``, not from ``datetime.now()``, so a test
        can hold the day still without freezing the whole machine.
        """
        if kind not in config.SESSION_KINDS:
            raise SessionsError(
                "kind %r is not one of %s" % (kind, config.SESSION_KINDS)
            )
        if not isinstance(held_on, date):
            raise SessionsError("held_on must be a datetime.date, not %s" % type(held_on).__name__)
        today_local = _today_in_display_zone(self._clock)
        if held_on > today_local:
            raise InvalidLessonDate(
                "held_on %s is in the future (today in %s is %s)"
                % (held_on, config.TZ_DISPLAY, today_local)
            )
        return self._lessons.create(held_on.isoformat(), kind)

    def lesson_on(self, held_on: date) -> Optional[Session]:
        """The lesson of this date, or None if no lesson was held."""
        if not isinstance(held_on, date):
            raise SessionsError("held_on must be a datetime.date")
        return self._lessons.find_on(held_on.isoformat())

    def lesson(self, session_id: int) -> Session:
        """The lesson of this id.  Raises ``LessonNotFound`` if the id is unknown."""
        lesson = self._lessons.by_id(session_id)
        if lesson is None:
            raise LessonNotFound("no lesson with id %s" % session_id)
        return lesson

    def recent_lessons(self, limit: int = 10) -> list[Session]:
        """The most recent lessons, newest first, at most ``limit`` of them."""
        if limit <= 0:
            raise SessionsError("limit must be positive, not %d" % limit)
        return self._lessons.recent(limit)

    # --------------------------------------------------------- attendance (Section 2)

    def mark_attendance(
        self,
        session_id: int,
        student_id: int,
        status: str,
        *,
        teacher_id: Optional[int] = None,
    ) -> AttendanceOutcome:
        """Record attendance of one student at one lesson.  Idempotent on
        the same status: a second tap with the SAME status returns
        ``written=False, changed=False``; a second tap with the OTHER status
        updates the existing row and returns ``written=False, changed=True``.

        The first tap of either kind returns ``written=True``.
        """
        if status not in config.ATTENDANCE_STATUSES:
            raise SessionsError(
                "status %r is not one of %s" % (status, config.ATTENDANCE_STATUSES)
            )
        # Look the lesson up here, not in the port, so the error is ours.
        self.lesson(session_id)
        row, written, changed = self._attendance.mark(
            session_id, student_id, status, teacher_id
        )
        return AttendanceOutcome(row=row, written=written, changed=changed)

    # -------------------------------------------------- marks on a lesson (Section 3)

    def record_marks_for_lesson(
        self,
        session_id: int,
        items: Sequence[MarkLessonItem],
    ) -> list[MarkingOutcome]:
        """Record a batch of marks, possibly spanning several days, against
        one lesson.

        Each item carries its own ``valid_on``; the service looks up the
        lesson for that date and uses its ``held_on`` as the mark's
        ``valid_at``.  If a date names no lesson the item is refused with
        ``InvalidLessonDate``; if a ``valid_on`` is earlier than the
        problem's sheet was issued the item is refused with
        ``InvalidLessonDate`` too.  The batch is processed in a single
        ``MarkingService`` transaction so a partial failure leaves the
        journal untouched.
        """
        if not items:
            return []
        outcomes: list[MarkingOutcome] = []
        for item in items:
            self._validate_mark_item(item)
            lesson = self._lessons.find_on(item.valid_on.isoformat())
            if lesson is None:
                raise InvalidLessonDate(
                    "no lesson on %s for item (student=%s, problem=%s)"
                    % (item.valid_on, item.student_id, item.problem_id)
                )
            # `record_marks_for_lesson` uses the journal directly: each item
            # has its OWN `valid_at`, and the service does not collapse them.
            # The transaction is held by the MarkingService.
            outcome = self._marking.set_state(
                item.student_id,
                item.problem_id,
                CellState.SOLVED,
                source=item.source,
                teacher_id=item.teacher_id,
                session_id=lesson.id,
                valid_at=self._date_to_iso(lesson.held_on),
                note=item.note,
            )
            outcomes.append(outcome)
        return outcomes

    def _validate_mark_item(self, item: MarkLessonItem) -> None:
        """A back-dated mark must not be earlier than the sheet of its problem.

        The mark's ``valid_on`` is the day the problem was checked off.  If
        that day is before the sheet that owns the problem was issued, the
        student could not have solved the problem -- the problem did not yet
        exist.  Both refusals (``valid_on`` in the future, ``valid_on`` before
        ``issued_at``) raise ``InvalidLessonDate``.  "Today" is read from the
        injected ``Clock`` so a test can hold the day still.
        """
        today_local = _today_in_display_zone(self._clock)
        if item.valid_on > today_local:
            raise InvalidLessonDate(
                "valid_on %s is in the future (today in %s is %s)"
                % (item.valid_on, config.TZ_DISPLAY, today_local)
            )
        sheet = self._find_sheet_of_problem(item.problem_id)
        if sheet is not None and item.valid_on < parse_iso_date(sheet.issued_at):
            raise InvalidLessonDate(
                "valid_on %s is before the sheet's issued_at %s"
                % (item.valid_on, sheet.issued_at)
            )

    def _find_sheet_of_problem(self, problem_id: int):
        """The sheet that owns this problem, by walking all sheets.

        The catalogue port does not expose a "problem -> sheet" lookup, and
        the заход's zone forbids editing the catalogue.  Walking all sheets
        is fine for a school of 56 students and ~30 sheets; it is the cost of
        keeping the port minimal.
        """
        for sheet in self._catalogue.sheets():
            for problem in self._catalogue.problems_of_sheet(sheet.id):
                if problem.id == problem_id:
                    return sheet
        return None

    def _sheet_id_of_problem(self, problem_id: int) -> int:
        sheet = self._find_sheet_of_problem(problem_id)
        if sheet is None:
            raise SessionsError("unknown problem id %s" % problem_id)
        return sheet.id

    # ----------------------------------------- the position's read model (Section 2)

    def attendance_for(self, session_id: int) -> dict[int, AttendanceView]:
        """The position's read model: one ``AttendanceView`` per student who
        appears in either the ``attendance`` rows or the journal of this
        lesson, mapped by ``student_id``.

        A student with no attendance row and no journal events is absent from
        the dictionary -- the caller knows the roster and fills the gap with
        a "nothing" view.  This matches the contract of ``ProgressService``'s
        ``states_for`` and is what the test of the position (b) vs (c) reads.
        """
        # 1. Make sure the lesson exists.  A bad id is a bug, not "empty".
        self.lesson(session_id)

        views: dict[int, AttendanceView] = {}

        # 2. Walk the journal for this lesson.  P1's MarkJournal.events() does
        # not filter by session_id, so the service buckets them itself.  This
        # is fine: a school writes a few hundred marks per lesson, not
        # millions, and the test that IS this position runs on a handful of
        # rows.  The shape of the read is fixed by the Protocol; the cost is
        # the port's problem, not the service's.
        events = [
            event
            for event in self._journal.events()
            if event.session_id == session_id
        ]
        students_with_marks = {event.student_id for event in events}
        for student_id in students_with_marks:
            views[student_id] = AttendanceView(
                student_id=student_id, status=None, has_marks=True
            )

        # 3. Walk the attendance rows.  Without a read method the (b) vs (c)
        # position test cannot run, so the port exposes one.
        for row in self._attendance.list_for_session(session_id):
            existing = views.get(row.student_id)
            views[row.student_id] = AttendanceView(
                student_id=row.student_id,
                status=row.status,
                has_marks=(existing.has_marks if existing is not None else False),
            )
        return views

    # --------------------------------------------------------- helpers

    @staticmethod
    def _date_to_iso(date_str: str) -> str:
        """Render ``YYYY-MM-DD`` as a UTC ISO timestamp at midnight.

        The schema's CHECK on ``valid_at`` is the GLOB for ``YYYY-MM-DDT...Z``,
        so a DATE alone would not be accepted.  The service stamps the day at
        midnight UTC; display goes through ``ZoneInfo(TZ_DISPLAY)`` and shows
        the right wall-clock date in Moscow.
        """
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=ZoneInfo("UTC"))
        return to_iso(dt)
