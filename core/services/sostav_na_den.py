"""The composition of one lesson day: the standing arrangement plus the deviations.

WHAT THIS FILE IS FOR, IN ONE SENTENCE
--------------------------------------------------------------------------------------

``core/services/room.py`` already composes those two layers **for one room, during the
lesson, for the head standing in it**.  Nothing composed them **for the whole school on a
given date**, and that is the read the distribution screen needs before anybody is in the
building: which lesson is the nearest one, who is with whom on it, and what exactly
differs from the usual.  Composing it a second time inside the web layer would be the
second source of truth this project spends its whole architecture removing, so it is
composed here, in ``core/``, where neither sqlite3 nor a template can reach.

THE MODEL IS NOT RE-DECIDED HERE.  It is the one ``doc/TZ-sloj-zanyatia.md §2`` settled:
**a lesson stores only DEVIATIONS.**  Whatever the lesson does not mention is read from
the standing arrangement on the fly, and "put him back as usual" is the deletion of a row,
not the writing of one.  Every consequence below follows from that and from nothing else.

🔴 THE SLOT OF A DAY IS NOT ITS ISO WEEKDAY, AND THIS IS THE ONE PLACE THAT KNOWS IT
--------------------------------------------------------------------------------------

``migrations/003_slot_vmesto_weekday.sql`` mapped ``weekday=1 -> slot=1`` and
``weekday=4 -> slot=2``, and the live base carries exactly those two values (105 rows in
slot 1, 86 in slot 2, measured 2026-09-07).  ``core.services.enrollment.weekday_of``
returns the ISO weekday and its callers pass that straight in as the slot, so a Monday
resolves by coincidence (1 == 1) and a **Thursday asks for slot 4, which no row has ever
carried**.  A screen built on that would show an empty school every Thursday.

``slot_of`` below is the mapping the migration actually performed.  It is deliberately
NOT a fix applied to ``resolve_many``: that call site is depended on by a dozen green
tests whose fixtures write ``slot=4`` for a Thursday, so correcting it is a change of
behaviour across the project and belongs to its own заход, not to a side effect of this
one.  The defect is reported rather than smuggled.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional, Protocol, Sequence

import config
from core.models import Session

#: ISO weekday → the ``enrollment.slot`` that day is taught in, per migration 003.
#: A day absent from this mapping is not a lesson day at all.
SLOTY_ZANYATIJ = {1: 1, 4: 2}

#: The status an ``attendance`` row carries when the student is not at the lesson.
#: ``config.ATTENDANCE_STATUSES`` is ``('был', 'не был')``; the ТЗ calls this state
#: «отсутствует» in prose, and it is this value on disk — there is no third status,
#: and inventing one would give the same fact two spellings.
OTSUTSTVUET = config.ATTENDANCE_STATUSES[1]
PRISUTSTVUET = config.ATTENDANCE_STATUSES[0]


def slot_of(day: str) -> Optional[int]:
    """The lesson slot of a calendar day, or ``None`` when no lesson is taught on it."""
    return SLOTY_ZANYATIJ.get(date.fromisoformat(day).isoweekday())


def is_lesson_day(day: str) -> bool:
    return slot_of(day) is not None


def nearest_lesson(today: str, *, lesson_over: bool = False) -> str:
    """The date the screen opens on by default.

    Р4 of the ТЗ, in the owner's own words: *on the day of a lesson the nearest lesson is
    TODAY, until the lesson ends* — because correcting the table mid-lesson is a working
    scenario ("a teacher arrived halfway through and I need to know who he should work
    with"), not documentation.  Once it is over, the nearest lesson is the next one.

    ``lesson_over`` is passed in rather than computed here on purpose: the hours live in
    ``ops/raspisanie.py``, whose constants are known stale (it still believes 16:00–19:00
    on Mon/Thu, while the timetable since 2026-09-07 is Mon 14:15–15:55 and Thu
    13:10–15:00).  A pure function that silently trusted them would inherit the lie.
    """
    if is_lesson_day(today) and not lesson_over:
        return today
    moment = date.fromisoformat(today)
    for step in range(1, 8):
        candidate = moment + timedelta(days=step)
        if candidate.isoweekday() in SLOTY_ZANYATIJ:
            return candidate.isoformat()
    raise AssertionError("SLOTY_ZANYATIJ is empty: every week would have no lesson")


# --------------------------------------------------------------------------- ports


class EnrollmentRows(Protocol):
    """The standing layer, read-only.  One method, and the narrowness is the point.

    This service never writes ``enrollment`` — not one row, not a short interval, not a
    "temporary" one.  Writing a today-only fact into the standing table is precisely the
    accident of 2026-09-07 that this заход exists to undo.
    """

    def rows_valid_on(self, day: str, slot: int,
                      student_ids: Optional[Sequence[int]] = None) -> list: ...


class SessionsOfDay(Protocol):
    def for_day(self, held_on: str) -> Optional[Session]: ...


class DeviationRows(Protocol):
    def rows_for_session(self, session_id: int) -> list: ...


# --------------------------------------------------------------------------- read model


@dataclass(frozen=True)
class Mesto:
    """One student on one lesson day, with BOTH layers visible at once.

    ``obychno`` is what ТЗ §3.3 is about and the reason this dataclass carries two teacher
    fields instead of one resolved answer: the screen has to show *«обычно у ‹имя›»* next
    to today's teacher, and a read model that had already collapsed the two could not.
    """

    student_id: int
    obychno: Optional[int]          # the standing teacher — «обычно у него»
    segodnya: Optional[int]         # today's teacher, standing one included
    room: Optional[str]
    otmechen_otsutstvuyushchim: bool
    otklonenie: bool                # is there a row in the lesson layer at all

    @property
    def u_drugogo(self) -> bool:
        """Today with somebody other than usual."""
        return (self.segodnya is not None
                and self.obychno is not None
                and self.segodnya != self.obychno)

    @property
    def nekuda_det(self) -> bool:
        """Red, and the only red on the lesson layer (ТЗ §4).

        Not marked absent and yet with no teacher.  A student who IS marked absent is not
        lost and does not redden: that is the distinction the whole layer exists to make.
        """
        return not self.otmechen_otsutstvuyushchim and self.segodnya is None


@dataclass(frozen=True)
class SostavDnya:
    """The whole school on one date."""

    den: str
    slot: Optional[int]
    session_id: Optional[int]
    mesta: tuple

    @property
    def otkloneniya(self) -> tuple:
        return tuple(m for m in self.mesta if m.otklonenie)

    @property
    def otsutstvuyut(self) -> tuple:
        return tuple(m for m in self.mesta if m.otmechen_otsutstvuyushchim)

    @property
    def krasnye(self) -> tuple:
        return tuple(m for m in self.mesta if m.nekuda_det)

    def po_prepodavatelyam(self) -> dict:
        """``{teacher_id: (Mesto, ...)}`` for today, absences excluded.

        Grouped by TODAY's teacher, because the load a teacher actually carries this
        lesson is what ТЗ §4 counts as overload — «по фактически присутствующим», not by
        the standing list.
        """
        po: dict = {}
        for mesto in self.mesta:
            if mesto.otmechen_otsutstvuyushchim or mesto.segodnya is None:
                continue
            po.setdefault(mesto.segodnya, []).append(mesto)
        return {tid: tuple(v) for tid, v in po.items()}


# --------------------------------------------------------------------------- service


class SostavService:
    """Standing arrangement + lesson deviations, composed on the fly.

    Nothing is copied into the lesson when it is created: a lesson that copied the
    standing arrangement would freeze it, and a later correction of the standing layer
    would never reach the lesson — the two-sources illness again, one table further down.
    """

    def __init__(self, enrollment: EnrollmentRows, sessions: SessionsOfDay,
                 attendance: DeviationRows) -> None:
        self._enrollment = enrollment
        self._sessions = sessions
        self._attendance = attendance

    def sostav(self, den: str) -> SostavDnya:
        slot = slot_of(den)
        if slot is None:
            # Not a lesson day: no standing rows apply and no deviations can exist.
            # Returning an empty composition rather than raising lets a caller ask about
            # any date the owner types, which Р2 says must be possible in both directions.
            return SostavDnya(den=den, slot=None, session_id=None, mesta=())

        standing = {row.student_id: row for row in self._enrollment.rows_valid_on(den, slot)}

        session = self._sessions.for_day(den)
        deviations = {}
        if session is not None:
            for row in self._attendance.rows_for_session(session.id):
                deviations[row.student_id] = row

        mesta = []
        for student_id in sorted(set(standing) | set(deviations)):
            row = standing.get(student_id)
            obychno = row.teacher_id if row is not None else None
            room = row.room if row is not None else None
            otklonenie = deviations.get(student_id)

            if otklonenie is None:
                # No row — «как обычно».  This is the majority branch and it is the whole
                # economy of the deviations model: 45 students, and on a quiet lesson the
                # layer holds nothing at all.
                mesta.append(Mesto(student_id=student_id, obychno=obychno,
                                   segodnya=obychno, room=room,
                                   otmechen_otsutstvuyushchim=False, otklonenie=False))
                continue

            absent = otklonenie.status == OTSUTSTVUET
            # ``teacher_id`` on the deviation row overrides the standing one for THIS
            # session and for nothing else.  It being NULL means "no override", so the
            # standing teacher stands — except for somebody marked absent, who is with
            # nobody by definition.
            segodnya = otklonenie.teacher_id if otklonenie.teacher_id is not None else obychno
            if absent:
                segodnya = None
            mesta.append(Mesto(student_id=student_id, obychno=obychno,
                               segodnya=segodnya, room=room,
                               otmechen_otsutstvuyushchim=absent, otklonenie=True))

        return SostavDnya(den=den, slot=slot,
                          session_id=session.id if session is not None else None,
                          mesta=tuple(mesta))
