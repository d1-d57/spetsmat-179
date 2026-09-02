"""The room, as the head of it sees it at the start of a lesson.

Eighteen children in front of him, six teachers, ninety minutes.  This module answers the
three questions that hold him up, and nothing else: who is in this room today, who has
arrived, and who works with whom for the next ninety minutes.

THE ONE DECISION THIS FILE TURNS ON: WHERE A TODAY-ONLY ROW LIVES
------------------------------------------------------------------------------------

A student's teacher is a STANDING arrangement, recorded by ``core/services/enrollment.py``
as a half-open interval per lesson day.  Moving him for one evening is a different fact
about the world, and writing it into that interval would be the very defect the enrollment
position exists to remove: October's marks would start reporting under whoever happened to
take him on one Thursday in March.

It cannot go into ``enrollment`` even as a short interval.  ``[today, tomorrow)`` overlaps
the standing open row, and ``enrollment_no_overlap_insert`` aborts -- correctly, because
two rows covering one (student, weekday, day) is exactly the state that makes "who taught
him" a coin toss.

So the today-only row is a row in the table that is already keyed per session::

    attendance (session_id, student_id, teacher_id, status)   unique (session_id, student_id)

``attendance.teacher_id`` is *who this student worked with at THIS session*.  That IS the
today-only assignment, and two of the head's three actions fall out of the one mechanism:

  * **today's assignment** -- the attendance row's ``teacher_id`` overrides the standing
    one for this session and for nothing else.  ``enrollment`` is never written from this
    module; there is no method here that could, and the port it would need is not imported.
  * **a guest from another room** -- a student whose standing room is not this one, given
    an attendance row whose today-teacher belongs to a teacher of this room.  He shows up
    on this screen for this lesson.  His standing enrollment is untouched BY CONSTRUCTION
    rather than by care: nothing in this file can reach it.

TWO ATTENDANCE STATES ON THIS SCREEN, NOT THREE
------------------------------------------------------------------------------------

Untouched, and ``config.ATTENDANCE_STATUSES[0]`` -- "came".  A repeat tap DELETES the row
instead of writing the negative status: untapping is "I tapped the wrong child", which is
the erratum semantics of the journal, not a claim that anybody is absent.  «пришли N из M»
counts rows, so an unmarked child is simply not counted yet, which is the truth at 18:05.

The negative status still exists in the schema and a row carrying it is read here as
not-present; a tap on such a child marks him present in one tap.  So the third state is
handled without a third tap and without this screen ever writing it.

THE SESSION OF A DAY IS GET-OR-CREATE, AND READS TAKE THE SMALLEST ID
------------------------------------------------------------------------------------

``sessions.held_on`` carries no unique index, and three heads open their screens inside the
same minute.  Two session rows for one day would split one lesson's attendance in half and
the halves would never be noticed, because each screen would look consistent to the head
reading it.  The get-or-create therefore runs inside the store's transaction, and every
read takes ``min(id)`` so that a pair created before this rule existed still resolves to
one lesson.

Nothing here imports the database driver and nothing here imports the bot framework.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import ContextManager, Optional, Protocol

import config
from core.models import Session, Student
from core.services.enrollment import EnrollmentService, lesson_day_of, weekday_of

#: The status this screen writes.  Read from ``config`` rather than spelled here, so the
#: string that the schema's CHECK constraint enforces has one home.
PRESENT = config.ATTENDANCE_STATUSES[0]

#: The status this screen never writes but must read correctly: a positive assertion that
#: a child did not come, which some later position records when it closes a lesson.
ABSENT = config.ATTENDANCE_STATUSES[1]


# ------------------------------------------------------------------- domain errors

class RoomError(Exception):
    """A request about a room that the domain refuses."""


class NotInThisRoom(RoomError):
    """The student named is neither a standing member of this room today nor its guest.

    Distinct from "no such student".  A head may only act on the children in front of him,
    and this is the refusal that makes a forged payload naming a foreign id do nothing: the
    room is not in the payload, so the id is checked against the room the head actually
    heads.
    """


class UnknownTeacher(RoomError):
    """Asked to hand a student to somebody who does not teach in this room today.

    A teacher is bound to a room hard for the whole year.  Handing a child to a teacher of
    another room would be a standing change wearing a today-only costume.
    """


# ----------------------------------------------------------------------- the seams

@dataclass(frozen=True)
class AttendanceRow:
    """What one session records about one student: was he here, and with whom.

    ``teacher_id`` is the TODAY-ONLY assignment and is ``None`` when the standing one
    stands.  The two are deliberately not merged in storage: "he is with Даня today
    because I moved him" and "he is with Даня because he always is" answer different
    questions in March.
    """

    student_id: int
    status: str
    teacher_id: Optional[int] = None

    @property
    def is_present(self) -> bool:
        return self.status == PRESENT


class SessionPort(Protocol):
    """The lessons themselves: one row per day the conduit met."""

    def for_day(self, held_on: str) -> Optional[Session]:
        """The session of that calendar day, smallest id first, or ``None``."""

    def create(self, held_on: str, kind: str = config.SESSION_KINDS[0]) -> Session:
        """Write one session row and return it with the id the store assigned."""


class AttendancePort(Protocol):
    """Who was at a session, and with whom.

    There is no ``set_teacher`` separate from ``set``: the row carries both facts and a
    port that let them be written apart would let a caller record a today-only teacher for
    a child nobody said had arrived.
    """

    def transaction(self) -> ContextManager[None]:
        """Serialise read-then-write against the other two rooms' heads.

        The get-or-create of a session and the upsert of a row both read before they
        write.  A store that does not need the seam may implement it as a no-op.
        """

    def rows_for_session(self, session_id: int) -> list:
        """Every ``AttendanceRow`` of one session."""

    def row(self, session_id: int, student_id: int) -> Optional[AttendanceRow]:
        """One row, or ``None`` when this child has not been touched today."""

    def set(
        self,
        *,
        session_id: int,
        student_id: int,
        status: str,
        teacher_id: Optional[int],
    ) -> AttendanceRow:
        """Write the row for this (session, student), replacing whatever stood."""

    def clear(self, session_id: int, student_id: int) -> None:
        """Remove the row entirely.  Idempotent: removing nothing is not an error."""


class DebtsPort(Protocol):
    """Debts, as this screen is allowed to ask for them.

    ``core/services/progress.py`` owns the rule -- obligatory problems on sheets older
    than the current one, counted from the student's ``first_sheet_id``.  This screen does
    not reimplement one line of it, and the Protocol offers no way to: it can ask, not
    compute.
    """

    def debts(self, student_id: int, current_sheet_ord: int) -> list:
        """The obligatory problems this student still owes."""


class TeacherDirectory(Protocol):
    """The teachers of the conduit, by id.

    A separate seam rather than a method on the catalogue, because ``core.ports.Catalogue``
    does not offer one and that file is not this position's to change.  The screen needs
    exactly one thing from it -- a name to put on a button -- and asking for the whole list
    once per screen is cheaper than eighteen lookups and simpler than a cache that can go
    stale between two taps.
    """

    def teachers(self) -> list:
        """Every teacher row, in whatever order the store keeps them."""


class RoomCatalogue(Protocol):
    """The slice of ``core.ports.Catalogue`` this screen reads.

    Narrower than the real one on purpose: a room screen has no business asking for the
    problems of a sheet, and a Protocol that offered it would invite somebody to draw a
    grid here instead of handing over to P4's screen.
    """

    def students(self) -> list: ...

    def student(self, student_id: int) -> Optional[Student]: ...

    def sheets(self) -> list: ...


# ---------------------------------------------------------------------- the answers

@dataclass(frozen=True)
class RoomMember:
    """One child on the head's screen: who he is, what he owes, where he stands.

    ``debts`` is a COUNT and the screen shows nothing beside it.  It is a work item -- it
    says where to send a teacher next -- and the moment anything is written next to it
    (a share of the room, a colour, a place in a list) it stops being a work item and
    becomes a statement about a child, in front of seventeen others.
    """

    student: Student
    debts: int
    present: bool
    #: True when this child's standing room for today is not this room.
    is_guest: bool
    #: From P12.  ``None`` for a guest, whose standing arrangement is in another room and
    #: is none of this screen's business.
    standing_teacher_id: Optional[int]
    #: From the attendance row.  ``None`` means the standing arrangement stands.
    today_teacher_id: Optional[int] = None

    @property
    def teacher_id(self) -> Optional[int]:
        """Who works with him for the next ninety minutes."""
        return self.today_teacher_id if self.today_teacher_id is not None else self.standing_teacher_id

    @property
    def is_moved_today(self) -> bool:
        """Has the head moved him for this lesson only?

        A guest is not "moved": he was brought in, which the screen says differently.
        """
        return (
            not self.is_guest
            and self.today_teacher_id is not None
            and self.today_teacher_id != self.standing_teacher_id
        )

    #: Surname first, then given name, then id.  The order the head already has in his
    #: head, and the one thing on this screen that must NEVER depend on the debt count.
    @property
    def sort_key(self) -> tuple:
        return (self.student.surname, self.student.name, self.student.id)


@dataclass(frozen=True)
class RoomDay:
    """The whole screen, as data: one room, one day, one session.

    Assembled in one place so that the keyboard, the header and the tests all read the
    same object.  A screen redrawn from THIS is a screen redrawn from the database, which
    is what lets six teachers work in one room without two of them holding different
    truths.
    """

    room: str
    day: str
    weekday: int
    session_id: int
    #: In surname order, guests included, sorted once here so no caller has to remember.
    members: tuple
    #: The teachers who hold students in this room today, ascending.  These are the
    #: only teachers a today-only assignment on this screen may name.
    teacher_ids: tuple

    @property
    def came(self) -> int:
        return sum(1 for member in self.members if member.present)

    @property
    def total(self) -> int:
        return len(self.members)

    def member(self, student_id: int) -> Optional[RoomMember]:
        for member in self.members:
            if member.student.id == student_id:
                return member
        return None


# ----------------------------------------------------------------------- the service

class RoomService:
    """Everything the head of a room does at the start of a lesson.

    The room is a CONSTRUCTOR-LEVEL argument of every method rather than something the
    service remembers, because three heads share one process and a service holding "the
    current room" would be one shared mutable field between them.
    """

    def __init__(
        self,
        *,
        catalogue: RoomCatalogue,
        enrollment: EnrollmentService,
        progress: DebtsPort,
        attendance: AttendancePort,
        sessions: SessionPort,
        teachers: TeacherDirectory,
        clock,
    ) -> None:
        self._catalogue = catalogue
        self._enrollment = enrollment
        self._progress = progress
        self._attendance = attendance
        self._sessions = sessions
        self._teachers = teachers
        self._clock = clock

    # ------------------------------------------------------------------------ today

    def today(self) -> str:
        """The calendar day of the lesson happening now, in the school's own timezone.

        Through ``lesson_day_of`` and never through a subtraction of hours: an evening
        lesson is exactly where a fixed offset moves the day, and a day that slipped would
        put the whole room on yesterday's session with yesterday's attendance already on it.
        """
        return lesson_day_of(self._clock.now_iso())

    def session_for(self, day: str) -> Session:
        """The session of that day, created if this is the first screen opened on it.

        Inside the store's transaction, and re-reading after taking it: the losing head of
        the second room must find the row the winner wrote, not write a second one.
        """
        existing = self._sessions.for_day(day)
        if existing is not None:
            return existing
        with self._attendance.transaction():
            existing = self._sessions.for_day(day)
            if existing is not None:
                return existing
            return self._sessions.create(day)

    # ------------------------------------------------------------------- the roster

    def room_day(
        self,
        room: str,
        day: Optional[str] = None,
        *,
        host_teacher_id: Optional[int] = None,
    ) -> RoomDay:
        """The whole screen for one room on one day.

        ONE read of the standing arrangements for the entire conduit and one read of the
        session's attendance; the debts are the only per-child question, and they are
        asked of P1's service rather than answered here.

        ``host_teacher_id`` is the head's own binding.  He counts as a teacher of his room
        even on an evening when no standing row happens to name him -- a room whose head
        holds nobody today is still his room, and without this he could not take a guest
        himself on the one evening he has nobody of his own.
        """
        day = day or self.today()
        weekday = weekday_of(day)
        session = self.session_for(day)

        students = {student.id: student for student in self._catalogue.students()}
        standing = self._enrollment.resolve_many(list(students), day)

        # Who stands in this room today, and which teachers hold them.  A teacher is bound
        # to a room hard for the whole year, so the room's teachers ARE the teachers of its
        # standing rows -- there is no separate table saying so, and inventing one would be
        # a second truth to drift.
        room_students = {
            student_id
            for student_id, assignment in standing.items()
            if assignment is not None and assignment.room == room
        }
        teacher_ids = {
            standing[student_id].teacher_id for student_id in room_students
        }
        if host_teacher_id is not None:
            teacher_ids.add(host_teacher_id)

        rows = {row.student_id: row for row in self._attendance.rows_for_session(session.id)}

        # A guest is an attendee of THIS session whose today-teacher is one of this room's
        # teachers and whose standing room is somewhere else.  He is here because somebody
        # in this room took him, which is a fact this session's own row already carries.
        guests = {
            student_id
            for student_id, row in rows.items()
            if student_id not in room_students
            and row.teacher_id is not None
            and row.teacher_id in teacher_ids
            and student_id in students
        }

        current_ord = self._current_sheet_ord()
        members = []
        for student_id in sorted(room_students | guests):
            student = students[student_id]
            row = rows.get(student_id)
            assignment = standing.get(student_id)
            members.append(
                RoomMember(
                    student=student,
                    debts=self._debt_count(student_id, current_ord),
                    present=row is not None and row.is_present,
                    is_guest=student_id in guests,
                    standing_teacher_id=(
                        assignment.teacher_id
                        if assignment is not None and assignment.room == room
                        else None
                    ),
                    today_teacher_id=row.teacher_id if row is not None else None,
                )
            )
        members.sort(key=lambda member: member.sort_key)

        return RoomDay(
            room=room,
            day=day,
            weekday=weekday,
            session_id=session.id,
            members=tuple(members),
            teacher_ids=tuple(sorted(teacher_ids)),
        )

    def candidate_guests(self, room_day: RoomDay) -> list:
        """The children the head may bring in: everybody active who is not already here.

        Sorted by surname, like the room itself.  A student whose status is ``left`` is
        not offered -- he is kept in the catalogue because the journal points at his rows
        and always will, but he is not somebody who walks into a room on a Thursday.
        """
        here = {member.student.id for member in room_day.members}
        return sorted(
            (
                student
                for student in self._catalogue.students()
                if student.id not in here and student.status != "left"
            ),
            key=lambda student: (student.surname, student.name, student.id),
        )

    # ------------------------------------------------------------------- attendance

    def set_present(
        self,
        room_day: RoomDay,
        student_id: int,
        present: bool,
        *,
        host_teacher_id: Optional[int] = None,
    ) -> RoomDay:
        """Mark a child of THIS room as arrived, or take the mark back.

        ``present`` is the TARGET state and never a toggle, which is P4's law and the
        reason two taps racing each other are harmless: both ask for the same world, and
        the second one writes what the first one already wrote.

        Taking the mark back removes the row rather than asserting that the child did not
        come.  The head who untaps is saying "wrong child", not "he is absent"; the
        distinction is the same one the journal draws between a retraction and an erratum,
        and this screen only ever has the erratum to make.
        """
        member = self._require_member(room_day, student_id)
        with self._attendance.transaction():
            if present:
                self._attendance.set(
                    session_id=room_day.session_id,
                    student_id=student_id,
                    status=PRESENT,
                    # Whatever today-only teacher already stood is carried over: marking
                    # a child present must not silently undo a move made a minute ago.
                    teacher_id=member.today_teacher_id,
                )
            else:
                # The row goes, and for a guest that also takes him off the screen -- his
                # presence IS his row here, and a guest with no presence would be a child
                # standing in the room whom nobody said had arrived.
                self._attendance.clear(room_day.session_id, student_id)
        return self.room_day(room_day.room, room_day.day, host_teacher_id=host_teacher_id)

    # ----------------------------------------------------------------------- guests

    def add_guest(
        self,
        room_day: RoomDay,
        student_id: int,
        teacher_id: int,
        *,
        host_teacher_id: Optional[int] = None,
    ) -> RoomDay:
        """Bring a child of another room into this one, for this lesson only.

        The whole guarantee of this method is what it does NOT call.  There is no
        enrollment port on this service and no import that could reach one: the standing
        interval of this child cannot be written from here even by a caller who wanted to.
        ``tests/room/test_standing_enrollment.py`` proves it from the other side, by
        reading his history before and after.
        """
        student = self._catalogue.student(student_id)
        if student is None:
            raise NotInThisRoom("student %s is not in the catalogue" % (student_id,))
        if room_day.member(student_id) is not None:
            raise NotInThisRoom(
                "student %s is already on this screen: bringing him in again would be a "
                "second row for one child at one session" % (student_id,)
            )
        self._require_teacher(room_day, teacher_id)
        with self._attendance.transaction():
            self._attendance.set(
                session_id=room_day.session_id,
                student_id=student_id,
                status=PRESENT,
                teacher_id=teacher_id,
            )
        return self.room_day(room_day.room, room_day.day, host_teacher_id=host_teacher_id)

    # ------------------------------------------------------------ today's assignment

    def set_today_teacher(
        self,
        room_day: RoomDay,
        student_id: int,
        teacher_id: Optional[int],
        *,
        host_teacher_id: Optional[int] = None,
    ) -> RoomDay:
        """Hand a child to another teacher of this room, for this lesson only.

        ``teacher_id=None`` gives him back to his standing teacher: the today-only row
        keeps its presence and drops its override.  For a guest that is refused -- his
        standing arrangement is in another room, and dropping the override would leave a
        child on this screen belonging to nobody in it.

        Not one line of ``enrollment`` is written.  The child's interval says the same
        thing tomorrow that it said this morning, and "who taught him in October" answers
        with the teacher who actually did.
        """
        member = self._require_member(room_day, student_id)
        if teacher_id is not None:
            self._require_teacher(room_day, teacher_id)
        elif member.is_guest:
            raise UnknownTeacher(
                "student %s is a guest in room %s: he has no standing teacher here to "
                "give him back to" % (student_id, room_day.room)
            )
        with self._attendance.transaction():
            self._attendance.set(
                session_id=room_day.session_id,
                student_id=student_id,
                # Handing a child to a teacher is a statement that he is here: the head is
                # looking at him.  This is the one place presence is written as a
                # consequence, and it is written UP (to present), never down.
                status=PRESENT,
                teacher_id=teacher_id,
            )
        return self.room_day(room_day.room, room_day.day, host_teacher_id=host_teacher_id)

    def teacher_names(self, room_day: RoomDay) -> dict:
        """``{teacher_id: name}`` for the teachers of this room today.

        A teacher the directory does not know is still offered, under his id: the head can
        see WHICH teacher is missing from the directory and hand the child over anyway,
        which beats a room whose distribution silently loses a column.
        """
        known = {teacher.id: teacher.name for teacher in self._teachers.teachers()}
        return {
            teacher_id: known.get(teacher_id) or ("преподаватель %d" % teacher_id)
            for teacher_id in room_day.teacher_ids
        }

    def teachers_for(self, room_day: RoomDay) -> tuple:
        """The teachers a today-only assignment in this room may name."""
        return room_day.teacher_ids

    # ---------------------------------------------------------------------- private

    def _require_member(self, room_day: RoomDay, student_id: int) -> RoomMember:
        member = room_day.member(student_id)
        if member is None:
            raise NotInThisRoom(
                "student %s is not in room %s on %s: the room comes from the head's own "
                "binding and never from the payload, so an id that names somebody else "
                "reaches nothing" % (student_id, room_day.room, room_day.day)
            )
        return member

    def _require_teacher(self, room_day: RoomDay, teacher_id: int) -> int:
        if teacher_id not in room_day.teacher_ids:
            raise UnknownTeacher(
                "teacher %s holds nobody in room %s on %s: a teacher is bound to a room "
                "for the year, so handing a child across rooms would be a standing change "
                "wearing a today-only costume" % (teacher_id, room_day.room, room_day.day)
            )
        return teacher_id

    def _current_sheet_ord(self) -> int:
        """``ord`` of the sheet being worked on now: the largest one.

        Debts are the obligatory problems of sheets OLDER than this, so an empty catalogue
        answers zero debts for everybody rather than raising -- a real state before the
        importer has ever run, and not one the head should meet as a traceback.
        """
        sheets = self._catalogue.sheets()
        return max((sheet.ord for sheet in sheets), default=0)

    def _debt_count(self, student_id: int, current_ord: int) -> int:
        if current_ord <= 0:
            return 0
        return len(self._progress.debts(student_id, current_ord))


# --------------------------------------------------------------------- day arithmetic

#: Russian weekday names in the nominative, Monday = 1, so that ``WEEKDAY_NAMES[weekday]``
#: needs no offset.  Index 0 is unused and holds a marker rather than a name, because a
#: zero-based caller is exactly the mistake ``check_weekday`` exists to catch.
WEEKDAY_NAMES = (
    "—",
    "понедельник",
    "вторник",
    "среда",
    "четверг",
    "пятница",
    "суббота",
    "воскресенье",
)

#: Month names in the GENITIVE: the header reads «4 сентября», not «4 сентябрь».
MONTH_NAMES = (
    "—",
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)


def day_in_words(day: str) -> str:
    """«четверг, 4 сентября».

    The head reads the header to check he is looking at today rather than at a screen he
    left open since Monday, and «2026-09-04» does not answer that question at a glance.
    """
    parsed = date.fromisoformat(day)
    return "%s, %d %s" % (
        WEEKDAY_NAMES[parsed.isoweekday()],
        parsed.day,
        MONTH_NAMES[parsed.month],
    )
