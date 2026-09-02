"""Who teaches this student, on which lesson day, in which room — and how that changes
during the year without rewriting the past.

TWO RULES SHAPE THIS FILE, AND EVERYTHING ELSE HERE FOLLOWS FROM THEM.

**The key is per LESSON DAY.**  Some teachers come once a week, so the same student may
have one teacher on Monday and another on Thursday (last year: Кахиани = Ваня on Mon, Ян
on Thu).  The resolution question is therefore ``(student, calendar day) -> teacher``, and
the weekday is derived from the asked-for day and passed INTO the lookup as part of the
key.  It is never a filter applied to rows that were fetched without it: a lookup that
ignored the weekday would find two legal open rows for one student and would have to pick
one of them, which is a coin toss dressed as an answer.

**Moving a student must not rewrite history.**  An assignment stored as a CURRENT VALUE
means a reassignment silently rewrites who worked with whom in October: every mark the
previous teacher ever gave starts reporting under the new one.  So a move CLOSES the open
interval and OPENS a new one, and no method here ever writes ``teacher_id`` onto a row
that already exists.  "Who teaches this student now" is a query over intervals asked with
today's date — there is no stored answer to it anywhere, on purpose.

Intervals are HALF-OPEN, ``[valid_from, valid_to)``, and the open row carries
``config.OPEN_END_DATE`` rather than NULL.  Both conventions come from the schema, which
is their carrier: the partial unique index that forbids two open rows for one
(student, weekday) never fires against NULLs, and the overlap triggers are written for
half-open arithmetic.  This service must not fight either of them.

Nothing here imports sqlite3 and nothing here imports the bot framework.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import ContextManager, Iterable, Optional, Protocol, Sequence
from zoneinfo import ZoneInfo

import config
from core.isotime import parse_iso
from core.models import Enrollment


# ------------------------------------------------------------------- domain errors

class EnrollmentError(Exception):
    """An enrollment request the domain refuses."""


class NotEnrolled(EnrollmentError):
    """Asked to move a student who has no open row on that lesson day.

    Distinct from "the student does not exist": a student can be perfectly real and
    simply not attend on Thursdays.  Answering a move with silence would create the
    first Thursday row out of a request that said "change the existing one".
    """


class AlreadyEnrolled(EnrollmentError):
    """Asked to assign a student who already has an open row on that lesson day.

    The schema refuses this too — ``enrollment_one_open_row`` — but refusing it here
    names the repair: what the caller wants is ``move``, which keeps the history.
    """


class MoveChangesNothing(EnrollmentError):
    """A move to the teacher and room the student already has on that day.

    Not harmless: it would split one interval into two identical halves, and "who taught
    him in October" would start answering with two rows where the world had one fact.
    """


class MoveNotForward(EnrollmentError):
    """The effective day does not lie strictly inside the open interval.

    ``valid_from < valid_to`` is a CHECK in the schema, so closing an interval at or
    before its own start is refused there as well; caught here because the caller can be
    told which two dates disagree instead of reading an integrity error.
    """


class OverlappingHistory(EnrollmentError):
    """The store refused the row because it would overlap an existing interval.

    The guard lives in the schema (a partial unique index for the open row, triggers for
    two closed intervals) and stays there — this is only the domain-shaped translation of
    its refusal, so that a caller does not have to catch a driver exception.
    """


class UnknownWeekday(EnrollmentError):
    """A weekday outside ``config.WEEKDAY_MIN..config.WEEKDAY_MAX``.

    Monday is 1, ISO-8601.  A zero-based caller is the whole reason this exists: with
    Monday = 0 every lookup silently shifts by one day and answers with the wrong
    teacher rather than with nothing.
    """


# ------------------------------------------------------------------ day arithmetic
#
# The three functions below are the ONLY place a calendar is consulted.  Everything else
# passes ``YYYY-MM-DD`` strings around, which is what the schema stores and what makes
# ``valid_from <= day and day < valid_to`` a correct interval test as plain string
# comparison — ISO dates sort lexicographically iff they are zero-padded to ten
# characters, which is exactly what ``as_day`` enforces at the door.


def as_day(value: str) -> str:
    """Validate one calendar day and hand back its canonical ``YYYY-MM-DD`` text.

    A day written ``2026-9-1`` parses fine and then compares WRONG: ``'2026-9-1' <
    '2026-10-01'`` is false as strings although it is true as dates, so an interval test
    would quietly answer with the previous teacher.  The shape is therefore checked here
    rather than trusted, and the schema's GLOB constraint is the carrier behind it.
    """
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise EnrollmentError("not a calendar day: %r" % (value,)) from exc
    if parsed.isoformat() != value:
        raise EnrollmentError(
            "a day must be written as YYYY-MM-DD, got %r: the interval test compares "
            "these as strings and an unpadded date compares wrong" % (value,)
        )
    return value


def as_start_day(value: str) -> str:
    """A caller-supplied day that OPENS an interval or closes one.

    The same shape check as ``as_day``, plus one refusal: the open sentinel.
    ``config.OPEN_END_DATE`` is a perfectly good ``valid_to`` and is never a good
    ``valid_from`` or effective day, and the two ways it gets in fail differently and
    both badly.

      * ``assign(valid_from=OPEN_END_DATE)`` and ``move(effective_from=OPEN_END_DATE)``
        build an interval with ``valid_from == valid_to``, which the schema's
        ``check (valid_from < valid_to)`` refuses — as a driver exception crossing the
        seam that ``core/`` exists to keep sqlite3 behind.
      * ``end(effective_from=OPEN_END_DATE)`` is worse, because it succeeds: it sets
        ``valid_to`` to exactly the value that MEANS still open, so a report that a
        student left leaves him enrolled and returns a row that looks closed.

    Found by the verifier of this position, on a probe no test had made.
    """
    day = as_day(value)
    if day >= config.OPEN_END_DATE:
        raise EnrollmentError(
            "%r is the open-end sentinel (or past it) and cannot open or close an "
            "interval: as a start it makes valid_from == valid_to, which the schema "
            "refuses, and as an end it sets valid_to to the value that means STILL OPEN"
            % (value,)
        )
    return day


def weekday_of(day: str) -> int:
    """The ISO weekday of a calendar day, Monday = 1.

    This single call is what makes the lesson day part of the KEY.  ``teacher_on`` runs
    it on the date it was asked about and passes the result into the lookup; nothing
    downstream ever sees rows for the other days of the week.
    """
    return date.fromisoformat(as_day(day)).isoweekday()


def lesson_day_of(moment: str) -> str:
    """The calendar day a stored UTC instant belongs to, in the school's own timezone.

    Marks carry ``valid_at`` as a UTC instant; enrollment intervals are calendar days in
    Moscow, where the lessons happen.  Converting through ``ZoneInfo(config.TZ_DISPLAY)``
    and never through ``timedelta(hours=3)`` is the project's standing rule: the fixed
    offset is wrong twice a year and wrong forever for rows imported from earlier
    seasons, and an evening lesson is exactly where a three-hour error changes the day.
    """
    return parse_iso(moment).astimezone(ZoneInfo(config.TZ_DISPLAY)).date().isoformat()


def check_weekday(weekday: int) -> int:
    if not isinstance(weekday, int) or isinstance(weekday, bool):
        raise UnknownWeekday("weekday must be an int, got %r" % (weekday,))
    if not config.WEEKDAY_MIN <= weekday <= config.WEEKDAY_MAX:
        raise UnknownWeekday(
            "weekday %r is outside ISO %d..%d (Monday = %d)"
            % (weekday, config.WEEKDAY_MIN, config.WEEKDAY_MAX, config.WEEKDAY_MIN)
        )
    return weekday


# ------------------------------------------------------------------------ the seam

class EnrollmentPort(Protocol):
    """The store of enrollment intervals, as ``core/`` is allowed to see it.

    There is no ``set_teacher`` and no ``update`` in this Protocol, and that is the
    point: the only mutation offered is ``close``, which moves ``valid_to`` on an open
    row.  A port that offered "change this row's teacher" would make the defect this
    position removes reachable again in one line, however carefully the service above it
    were written.
    """

    def transaction(self) -> ContextManager[None]:
        """Serialise close-then-insert against other writers.

        A move reads the open row, closes it and inserts its successor.  Between the read
        and the insert another writer can close the same row, and the two moves would
        produce three intervals for two facts.  A store that does not need the seam may
        implement it as a no-op.
        """

    def open_row(self, student_id: int, weekday: int) -> Optional[Enrollment]:
        """The still-open interval for this (student, lesson day), or None."""

    def rows_valid_on(
        self,
        day: str,
        weekday: int,
        student_ids: Optional[Sequence[int]] = None,
    ) -> list:
        """Every interval covering ``day`` on that lesson day: ``[valid_from, valid_to)``.

        Bulk on purpose.  The readiness criterion resolves 112 pairs at once and the room
        screen that stands on this position resolves a whole room; a port shaped for one
        student at a time would bake an N+1 into every caller.
        """

    def insert(
        self,
        *,
        student_id: int,
        teacher_id: int,
        room: str,
        weekday: int,
        valid_from: str,
        valid_to: str = config.OPEN_END_DATE,
    ) -> Enrollment:
        """Write one interval and return it with the id the store assigned."""

    def close(self, enrollment_id: int, *, valid_to: str) -> Enrollment:
        """Move ``valid_to`` on one row.  The ONLY mutation this port offers."""

    def history(self, student_id: int, weekday: Optional[int] = None) -> list:
        """Every interval of one student, oldest first; one lesson day if asked."""


# ---------------------------------------------------------------------- the answers

@dataclass(frozen=True)
class Assignment:
    """The answer to ``(student, day) -> who, where``.

    It carries the interval it came from, because the interesting follow-up question is
    always "since when" — and because an answer that cannot say which row produced it
    cannot be checked against the history.
    """

    student_id: int
    teacher_id: int
    room: str
    #: ISO weekday of ``day``, Monday = 1.  Part of the key, not a decoration.
    weekday: int
    #: The day that was asked about.
    day: str
    valid_from: str
    valid_to: str
    enrollment_id: int

    @property
    def is_open(self) -> bool:
        """Is the arrangement that answered still the current one?"""
        return self.valid_to == config.OPEN_END_DATE


@dataclass(frozen=True)
class Move:
    """What one move did: exactly one interval closed, exactly one opened.

    Both halves are returned so that a caller — and a test — can assert on the pair
    rather than re-reading the store and hoping it looks right.
    """

    closed: Enrollment
    opened: Enrollment

    @property
    def effective_from(self) -> str:
        return self.opened.valid_from


# ----------------------------------------------------------------------- the service

class EnrollmentService:
    """Assignment, movement and resolution over half-open intervals per lesson day."""

    def __init__(self, rows: EnrollmentPort) -> None:
        self._rows = rows

    # ------------------------------------------------------------------- resolution

    def teacher_on(self, student_id: int, day: str) -> Optional[Assignment]:
        """Who worked with this student on this calendar day, and where.

        ``None`` is a legitimate answer and is NOT an error: it means the student had no
        lesson on that weekday, or the day lies outside every interval recorded for him
        (before he arrived, after he left).  Callers distinguish "no lesson" from "no
        such student" by asking the catalogue, which is not this service's business.
        """
        weekday = weekday_of(day)
        rows = self._rows.rows_valid_on(as_day(day), weekday, [student_id])
        if not rows:
            return None
        # The schema forbids two intervals covering one (student, weekday, day): the
        # partial unique index covers the open pair and the triggers cover the closed
        # ones.  If two ever arrive the guard has been bypassed, and answering with an
        # arbitrary one of them would hide that -- so it is said out loud.
        if len(rows) > 1:
            raise OverlappingHistory(
                "student %s has %d intervals covering %s (weekday %d): the schema's "
                "overlap guard was bypassed and no single answer is honest"
                % (student_id, len(rows), day, weekday)
            )
        return self._as_assignment(rows[0], day, weekday)

    def teacher_at(self, student_id: int, moment: str) -> Optional[Assignment]:
        """Who worked with this student at the instant a mark was made.

        This is the attribution question — "who received the October marks" — and it
        goes through ``lesson_day_of`` because marks are stored as UTC instants and
        enrollment is recorded in school days.
        """
        return self.teacher_on(student_id, lesson_day_of(moment))

    def resolve_many(self, student_ids: Iterable[int], day: str) -> dict:
        """``{student_id: Assignment or None}`` for every student asked about, in ONE read.

        Students with no lesson on that weekday are present with ``None`` rather than
        absent: a caller counting coverage must be able to tell "resolved to nobody" from
        "was never asked", and a dict that silently drops the misses makes
        ``len(resolved)`` look like a full house.
        """
        asked = list(dict.fromkeys(student_ids))
        weekday = weekday_of(day)
        day = as_day(day)
        found = {}
        if asked:
            for row in self._rows.rows_valid_on(day, weekday, asked):
                if row.student_id in found:
                    raise OverlappingHistory(
                        "student %s has more than one interval covering %s (weekday %d)"
                        % (row.student_id, day, weekday)
                    )
                found[row.student_id] = self._as_assignment(row, day, weekday)
        return {student_id: found.get(student_id) for student_id in asked}

    def history_of(self, student_id: int, weekday: Optional[int] = None) -> list:
        """Every interval ever recorded for this student, oldest first.

        This is the audit answer, and it is the reason a move is not an update: the row
        that said "teacher A from September" is still here after the move to B, saying
        the same thing about the same September.
        """
        if weekday is not None:
            check_weekday(weekday)
        return self._rows.history(student_id, weekday)

    def lesson_days_of(self, student_id: int) -> list:
        """The ISO weekdays this student currently attends, ascending.

        Read off the OPEN rows: a weekday whose interval has been closed and not
        reopened is a day the student no longer comes.
        """
        return sorted(
            row.weekday
            for row in self._rows.history(student_id)
            if row.valid_to == config.OPEN_END_DATE
        )

    # ---------------------------------------------------------------------- writing

    def assign(
        self,
        student_id: int,
        teacher_id: int,
        *,
        room: str,
        weekday: int,
        valid_from: str,
    ) -> Enrollment:
        """Open the FIRST interval for this (student, lesson day).

        Refuses when an open interval already stands: what that caller wants is ``move``,
        and the difference between the two is the whole subject of this position.  A
        student who left and came back has closed history and no open row, so he is
        assigned again here rather than moved — and the schema's overlap trigger is what
        checks that the new interval does not reach back into the old one.
        """
        check_weekday(weekday)
        valid_from = as_start_day(valid_from)
        with self._rows.transaction():
            standing = self._rows.open_row(student_id, weekday)
            if standing is not None:
                raise AlreadyEnrolled(
                    "student %s already has an open row on weekday %d (teacher %s since "
                    "%s): use move(), which keeps the history"
                    % (student_id, weekday, standing.teacher_id, standing.valid_from)
                )
            return self._insert(
                student_id=student_id,
                teacher_id=teacher_id,
                room=room,
                weekday=weekday,
                valid_from=valid_from,
            )

    def move(
        self,
        student_id: int,
        *,
        weekday: int,
        to_teacher_id: int,
        effective_from: str,
        room: Optional[str] = None,
    ) -> Move:
        """Move a student to another teacher on one lesson day, from ``effective_from``.

        Two writes and no third: the open interval is closed AT ``effective_from`` and a
        new one is opened FROM ``effective_from``.  Under half-open intervals those two
        dates being equal is the clean handover — the old row covers through the day
        before and the new row starts on the day itself, with no gap and no overlap.
        (The задание words this as "``valid_to`` = the day before"; writing the literal
        previous date into ``valid_to`` would leave that day covered by nobody, because
        ``valid_to`` is EXCLUSIVE here and in the schema's triggers alike.)

        ``teacher_id`` is never written onto the existing row.  That is not a promise
        made by this method — the port it calls has no way to do it.

        ``room`` defaults to the room the student already sat in: a teacher is bound to a
        group hard for the whole year, so a caller who moves a student into another
        teacher's group normally passes that teacher's room, and a caller who is only
        correcting the room passes it with the same teacher.
        """
        check_weekday(weekday)
        effective_from = as_start_day(effective_from)
        with self._rows.transaction():
            standing = self._rows.open_row(student_id, weekday)
            if standing is None:
                raise NotEnrolled(
                    "student %s has no open row on weekday %d: there is nothing to move, "
                    "and creating one here would turn a correction into an enrolment"
                    % (student_id, weekday)
                )
            if effective_from <= standing.valid_from:
                raise MoveNotForward(
                    "the move is effective %s but the standing interval opened %s: an "
                    "interval must satisfy valid_from < valid_to, and the schema checks it"
                    % (effective_from, standing.valid_from)
                )
            room = standing.room if room is None else room
            if (to_teacher_id, room) == (standing.teacher_id, standing.room):
                raise MoveChangesNothing(
                    "student %s is already with teacher %s in room %s on weekday %d: "
                    "splitting the interval would make one fact answer as two"
                    % (student_id, to_teacher_id, room, weekday)
                )
            closed = self._rows.close(standing.id, valid_to=effective_from)
            opened = self._insert(
                student_id=student_id,
                teacher_id=to_teacher_id,
                room=room,
                weekday=weekday,
                valid_from=effective_from,
            )
            return Move(closed=closed, opened=opened)

    def end(self, student_id: int, *, weekday: int, effective_from: str) -> Enrollment:
        """Close the open interval and open no successor: the student stopped attending.

        Гамаюнова left after sheet 6 and no row should claim she sat with anybody in
        May.  Deleting her interval would be the same defect from the other side — the
        marks she made in October would lose their teacher — so the interval is closed,
        not removed.
        """
        check_weekday(weekday)
        effective_from = as_start_day(effective_from)
        with self._rows.transaction():
            standing = self._rows.open_row(student_id, weekday)
            if standing is None:
                raise NotEnrolled(
                    "student %s has no open row on weekday %d: nothing to close"
                    % (student_id, weekday)
                )
            if effective_from <= standing.valid_from:
                raise MoveNotForward(
                    "cannot close at %s an interval that opened %s"
                    % (effective_from, standing.valid_from)
                )
            return self._rows.close(standing.id, valid_to=effective_from)

    # ---------------------------------------------------------------------- private

    def _insert(self, **row) -> Enrollment:
        if not (row["room"] or "").strip():
            raise EnrollmentError(
                "room is part of the enrollment row: 'who worked with him' and 'where he "
                "sat' are one question at a lesson, and the schema declares it not null"
            )
        return self._rows.insert(**row)

    @staticmethod
    def _as_assignment(row: Enrollment, day: str, weekday: int) -> Assignment:
        return Assignment(
            student_id=row.student_id,
            teacher_id=row.teacher_id,
            room=row.room,
            weekday=weekday,
            day=day,
            valid_from=row.valid_from,
            valid_to=row.valid_to,
            enrollment_id=row.id,
        )
