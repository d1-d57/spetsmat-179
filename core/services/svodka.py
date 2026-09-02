"""What the bot says on its own after a lesson, and to whom.

Everything before this position was a screen: somebody opened the bot and the bot
answered.  A teacher who forgot to mark therefore learned about it never, and the head of
a room learned nothing at all.  This file is the other direction -- the bot speaks first.

WHY IT SPEAKS AT ALL, AND WHY THAT IS NOT «БЫЛО БЫ ПОЛЕЗНО».  Record-keeping dies down a
cascade of barriers: expensive collection kills reflection, and missing reflection kills
the will to collect.  The paper tables died exactly that way -- filling them in cost a
lot, and the teacher got nothing back the same day.  The after-lesson summary is the cure:
the input turns into a tool for the NEXT lesson rather than into reporting.

THREE RULES THIS FILE IS BUILT ON, EACH ONE MEASURED RATHER THAN PREFERRED.

**AFTER THE LESSON, NEVER DURING IT.**  Telegram inside the school building is unreliable
-- the owner's measurement, not a precaution.  A notification sent in the middle of a
lesson does not arrive, or arrives to the wrong person at the wrong moment.  So nothing in
this module reads a wall clock and nothing here asks "is it seven in the evening yet":
``plan()`` takes the id of a lesson that has CLOSED, and the whole trigger is that closing.
When to call it is P10's question and is deliberately not answerable from here.

**TO THE TEACHER, A QUESTION ABOUT A FACT.  NEVER A REMINDER OF A DUTY.**  «Вы были
сегодня на занятии?», never «вы забыли поставить отметки».  Answering «был» is a
legitimate outcome: he could have come and taken nobody.  The bookkeeping was started for
the sake of preservation, not of control, and the first message that reads as control
kills the willingness to use it -- after which there is nothing left to preserve.

**THE SUMMARY BELONGS TO THE HEAD OF THE ROOM, BY MEANING.**  Not to the teacher who did
the marking.  The head is the person who decides what to do about a problem nobody took
and about a child nobody has spoken to for three lessons, and a summary delivered to
somebody who cannot act on it is noise.

WHAT IS FORBIDDEN HERE ABOVE ALL ELSE.  Nothing that ranks, nothing that scores, nothing
that measures one person against the class, and none of the game furniture that goes with
them -- the задание names the whole vocabulary in its section 4 and this file contains not
one word of it.  No comparison of teachers with one another, neither in a sentence nor in
a table by room.  No comparison of children with one another in a text an adult reads: the
silent list is the list of those NOBODY HAS SPOKEN TO, not the list of the worst.  Wordings
state facts.  And NOTHING is ever written next to a plus.

THE FORBIDDEN WORDS ARE NAMED AROUND HERE RATHER THAN SPELLED OUT, and that is not
squeamishness: the готовности criterion greps ``bot/`` and ``core/`` for the literal
strings and CANNOT TELL A PROHIBITION FROM A VIOLATION.  A docstring that listed them
would turn its own gate red.  ``bot/keyboards/views.py`` already says this about itself,
and the same discipline applies to every file under the gate.

NOTHING HERE IMPORTS sqlite3 AND NOTHING HERE IMPORTS ANY TELEGRAM LIBRARY.  The stores
sit behind Protocols implemented in ``infra/uvedomlenia_repo.py``; the sending sits in
``bot/routers/uvedomlenia.py``.  This file decides WHAT is true and WHAT the words are.

WHERE THE NUMBERS COME FROM.  Silence and the graveyard are ``SpiskiService.silent()`` and
``SpiskiService.graveyard()`` -- P5's projections over P1's, called and not re-spelled.  A
second way of counting the same thing is the class of bug P1's differential test exists to
close.  The one fold this file does itself is "who handed in how much at THIS lesson", and
it is done here because no projection offers it; see ``handed_in`` for the rule it obeys
and for the reason it cannot be keyed on ``session_id``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol

import config
from core.models import MarkEvent, Session, Teacher
from core.services.spiski import IMPORTED_SOURCE, SilentList, GraveyardList, SpiskiService

#: The two kinds of addressee, and the values ``sent_notifications.recipient_kind`` allows.
#: A third kind is a schema change somebody has to read, which is the point: an invented
#: kind would open a second namespace in the sent-log and deliver the same lesson twice.
RECIPIENT_TEACHER = "teacher"
RECIPIENT_HEAD = "head"
RECIPIENT_KINDS = (RECIPIENT_TEACHER, RECIPIENT_HEAD)

#: The two answers to the teacher's question.  They are ``config.ATTENDANCE_STATUSES``
#: and not a private pair, because the answer is attendance and the project spells
#: attendance one way.  Read from config rather than copied, so a rename there cannot
#: leave this file writing a value the CHECK constraint refuses.
PRESENT, ABSENT = config.ATTENDANCE_STATUSES

#: Telegram's own limit on one message is 4096 characters.  A summary is cut at this
#: length rather than by the API, so that a truncated summary is still a delivered one --
#: the same number and the same reason as ``ops/opoveshchenie.py``.
MAX_TEXT = 4000

#: How many graveyard problems the summary names out loud.  A summary is read standing in
#: a corridor, and a list longer than this stops being read at all -- at which point the
#: two lines that mattered are lost together with the rest.  The remainder is counted, not
#: dropped: «и ещё 4» is a fact, silence is not.
#:
#: THIS NUMBER BELONGS IN ``config.py`` and stands here because ``config.py`` is read-only
#: from this position, exactly as ``RECENT_SHEETS`` stands in ``core/services/spiski.py``
#: for the same reason.  The debt is named in ``## ВОПРОСЫ`` of
#: ``zhurnal/2026-09-02_spetsmat-bot/kod_P14-uvedomlenia.md``; a named constant so that
#: moving it is one edit and not a search.
GRAVEYARD_LINES = 5

#: How many silent students the summary names out loud, same rule and same debt.
SILENT_LINES = 10


# --------------------------------------------------------------------------- errors


class SvodkaError(Exception):
    """A notification request the domain refuses."""


class UnknownLesson(SvodkaError):
    """No lesson with that id.  A bad id is a bug in the caller, not "nothing to send"."""


# --------------------------------------------------------------------------- domain


@dataclass(frozen=True)
class SentRecord:
    """One claim standing in the sent-log: this lesson, this addressee, at this moment."""

    session_id: int
    recipient_kind: str
    recipient_id: int
    sent_at: str


@dataclass(frozen=True)
class TeacherPresence:
    """A teacher's own answer about one lesson.  ``status`` is one of
    ``config.ATTENDANCE_STATUSES`` -- the same two values student attendance uses."""

    session_id: int
    teacher_id: int
    status: str
    answered_at: str


@dataclass(frozen=True)
class HandedIn:
    """How much one student handed in at one lesson.

    A count and a name, and deliberately nothing else: no share of the sheet, no position
    relative to anybody.  ``count`` is events that still stand, so a hand-in that was
    retracted is not counted as credited and a mistyped button struck by an ``erratum``
    is not counted at all.
    """

    student_id: int
    surname: str
    name: str
    count: int


@dataclass(frozen=True)
class LessonWork:
    """Who handed in what at one lesson, with the coverage carried inside the value.

    ``considered`` is how many students were examined.  "трое сдали" and "трое сдали из
    пятидесяти шести" look the same on a screen and are not the same fact, and the only
    place that can be guaranteed is the value the text is drawn from -- the same rule
    every result object in ``core/services/spiski.py`` follows.
    """

    session: Session
    students: list = field(default_factory=list)
    considered: int = 0

    @property
    def handed_in(self) -> int:
        """How many students handed in at least one thing."""
        return len(self.students)

    @property
    def marks(self) -> int:
        """How many hand-ins there were in total."""
        return sum(row.count for row in self.students)


@dataclass(frozen=True)
class Uvedomlenie:
    """One message the bot intends to send: to whom, of what kind, and the exact words.

    The text is built here and not in the router, so that the rule about what may not be
    said has ONE home and the tests of §4 can read the words without a Telegram server.
    ``buttons`` is the pair of answers to the teacher's question, empty for a summary;
    it is a list of ``(label, status)`` and carries no aiogram type, because this module
    imports no Telegram library.
    """

    recipient_kind: str
    #: ``teachers(id)`` of the addressee.  Never a ``tg_id``: a person who re-registers
    #: gets a new Telegram id, and a sent-log keyed on it would re-send the whole year.
    recipient_id: int
    #: Where it actually goes.  ``None`` when the teacher has not registered yet -- a real
    #: state, reported as coverage rather than raised, so one unregistered head does not
    #: stop the summaries going to the other rooms.
    recipient_tg_id: Optional[int]
    session_id: int
    text: str
    buttons: list = field(default_factory=list)

    @property
    def deliverable(self) -> bool:
        return self.recipient_tg_id is not None


@dataclass(frozen=True)
class Plan:
    """Everything one closed lesson has to say, plus the coverage of the decision.

    ``teachers_considered`` and ``heads_considered`` are what makes a negative answer
    readable: "никому ничего" and "никому ничего, проверено 6 преподавателей из 6" are
    different statements, and only the second one can be believed.
    """

    session: Session
    notifications: list = field(default_factory=list)
    teachers_considered: int = 0
    heads_considered: int = 0

    @property
    def questions(self) -> list:
        return [n for n in self.notifications if n.recipient_kind == RECIPIENT_TEACHER]

    @property
    def summaries(self) -> list:
        return [n for n in self.notifications if n.recipient_kind == RECIPIENT_HEAD]

    @property
    def undeliverable(self) -> list:
        """Addressees the bot knows about and cannot reach: no Telegram id yet."""
        return [n for n in self.notifications if not n.deliverable]


# --------------------------------------------------------------------------- ports


class SentLog(Protocol):
    """The record of what has already been said.  The carrier of «одна сводка — один раз»."""

    def claim(
        self,
        session_id: int,
        recipient_kind: str,
        recipient_id: int,
        sent_at: str,
    ) -> bool:
        """Try to become the sender of this one message.

        ``True`` iff this caller took the claim; ``False`` iff somebody already had it.
        MUST be a single insert-or-nothing statement: a read followed by a write lets two
        processes both see "not sent yet" and both send.
        """

    def already_sent(self, session_id: int) -> list:
        """Every claim standing for this lesson.  For reports and tests, not for the
        send path -- reading before writing is the race the claim exists to remove."""


class TeacherAttendanceBook(Protocol):
    """Where the teacher's own answer lands.  A separate table from student attendance,
    because ``attendance.student_id`` references ``students(id)`` and a teacher is not a
    student; the two carry the same two status values on purpose."""

    def record(
        self,
        session_id: int,
        teacher_id: int,
        status: str,
        answered_at: str,
    ) -> TeacherPresence: ...

    def for_session(self, session_id: int) -> list: ...


class HeadsBook(Protocol):
    """Which teacher is the head of which room."""

    def heads(self) -> list:
        """``[(room, teacher_id), ...]``, room ascending.  A room with no registered head
        is simply absent -- a real state at the start of a year."""


class TeacherBook(Protocol):
    """The teachers, with the ``tg_id`` the send path cannot do without."""

    def teachers(self) -> list: ...

    def teacher(self, teacher_id: int) -> Optional[Teacher]: ...


class LessonBook(Protocol):
    """Just enough of P6's session store to name the lesson being reported on."""

    def by_id(self, session_id: int) -> Optional[Session]: ...


# --------------------------------------------------------------------------- service


class SvodkaService:
    """The after-lesson notifications: what is true, and what the words are.

    Writes nothing except the sent-log claim and the teacher's own answer.  Every number
    it reports comes from P1 through P5; the one fold of its own is ``handed_in``.
    """

    def __init__(
        self,
        *,
        lessons: LessonBook,
        spiski: SpiskiService,
        journal,
        catalogue,
        teachers: TeacherBook,
        heads: HeadsBook,
        sent_log: SentLog,
        teacher_attendance: TeacherAttendanceBook,
        clock,
    ) -> None:
        self._lessons = lessons
        self._spiski = spiski
        self._journal = journal
        self._catalogue = catalogue
        self._teachers = teachers
        self._heads = heads
        self._sent = sent_log
        self._presence = teacher_attendance
        self._clock = clock

    # ------------------------------------------------------------------- the lesson

    def lesson(self, session_id: int) -> Session:
        """The lesson being reported on.  A bad id is a bug, not an empty answer."""
        lesson = self._lessons.by_id(session_id)
        if lesson is None:
            raise UnknownLesson("no lesson with id %s" % session_id)
        return lesson

    # ------------------------------------------------------- who handed in (§3.1)

    def handed_in(self, session_id: int) -> LessonWork:
        """Who handed in how much at this lesson.

        THE ROWS CANNOT BE FOUND BY ``session_id`` ALONE, AND THAT IS MEASURED RATHER THAN
        ASSUMED.  ``grep -rn session_id bot/`` comes back empty: nothing under ``bot/``
        passes a session to ``MarkingService``, so every mark production has ever written
        carries ``session_id`` NULL.  A fold keyed on it would report "сдали 0" after every
        lesson forever, which is the same shape of failure ``core/services/spiski.py``
        documents for the silence window.  So a row belongs to this lesson if it names the
        session OR -- when it names none -- if the day part of its ``valid_at`` is the
        lesson's ``held_on``.  The moment something starts stamping ``session_id``, the
        first branch takes over on its own and this docstring is the thing to re-read.

        THE VALIDITY RULE IS P5's, NOT A SECOND ONE.  Imported rows are out: last year's
        book is one lump under a single ``valid_at`` and none of it happened at this
        lesson.  An ``erratum`` is out and so is the row it strikes, because an erratum
        says the record should never have existed; leaving the struck row in would let a
        mistyped button stand as this student's work for the evening.  An ``assert`` and a
        ``retract`` both count -- a retract is a hand-in that was not defended, which is a
        conversation that happened.
        """
        lesson = self.lesson(session_id)
        day = lesson.held_on[:10]

        events = [
            mark for mark in self._journal.events() if mark.source != IMPORTED_SOURCE
        ]
        struck = {
            mark.reverses_id
            for mark in events
            if mark.event is MarkEvent.ERRATUM and mark.reverses_id is not None
        }

        counts: dict = {}
        for mark in events:
            if mark.event is MarkEvent.ERRATUM or mark.id in struck:
                continue
            belongs = (
                mark.session_id == session_id
                if mark.session_id is not None
                else mark.valid_at[:10] == day
            )
            if not belongs:
                continue
            counts[mark.student_id] = counts.get(mark.student_id, 0) + 1

        students = self._spiski.active_students()
        by_id = {student.id: student for student in students}
        rows = []
        for student_id, count in counts.items():
            student = by_id.get(student_id) or self._catalogue.student(student_id)
            if student is None:
                # A mark pointing at a student the catalogue no longer knows is a broken
                # foreign key, which the schema forbids; skipping is the honest answer
                # rather than putting an id in front of a human as if it were a name.
                continue
            rows.append(
                HandedIn(
                    student_id=student_id,
                    surname=student.surname,
                    name=student.name,
                    count=count,
                )
            )
        # Surname order, NOT count order.  Ordering by count turns the list into a ranking
        # of children, which §4 forbids in a text an adult reads; the alphabet ranks nobody.
        rows.sort(key=lambda row: (row.surname, row.name, row.student_id))
        return LessonWork(session=lesson, students=rows, considered=len(students))

    # -------------------------------------------------- the teacher's question (§2)

    def teachers_without_marks(self, session_id: int) -> list:
        """Teachers who wrote NOT ONE mark at this lesson, teacher id ascending.

        "Wrote a mark" is read off the journal by the same rule ``handed_in`` uses, so the
        two halves of one lesson cannot disagree about what happened at it.  A teacher who
        has already answered the question for this lesson is left out: the question exists
        to be answered once, and a second copy of it after the answer is exactly the
        reminder-of-a-duty §2 forbids.
        """
        lesson = self.lesson(session_id)
        day = lesson.held_on[:10]

        marked: set = set()
        events = [
            mark for mark in self._journal.events() if mark.source != IMPORTED_SOURCE
        ]
        struck = {
            mark.reverses_id
            for mark in events
            if mark.event is MarkEvent.ERRATUM and mark.reverses_id is not None
        }
        for mark in events:
            if mark.event is MarkEvent.ERRATUM or mark.id in struck:
                continue
            if mark.teacher_id is None:
                continue
            belongs = (
                mark.session_id == session_id
                if mark.session_id is not None
                else mark.valid_at[:10] == day
            )
            if belongs:
                marked.add(mark.teacher_id)

        answered = {row.teacher_id for row in self._presence.for_session(session_id)}
        return [
            teacher
            for teacher in sorted(self._teachers.teachers(), key=lambda t: t.id)
            if teacher.id not in marked and teacher.id not in answered
        ]

    def record_presence(self, session_id: int, teacher_id: int, status: str) -> TeacherPresence:
        """Record a teacher's answer to the question.  Idempotent on the same answer and
        correctable to the other one -- a teacher who taps «не был» and then remembers he
        looked in for ten minutes has not made a mistake."""
        if status not in config.ATTENDANCE_STATUSES:
            raise SvodkaError(
                "status %r is not one of %s" % (status, config.ATTENDANCE_STATUSES)
            )
        self.lesson(session_id)
        return self._presence.record(
            session_id, teacher_id, status, self._clock.now_iso()
        )

    def presence_for(self, session_id: int) -> list:
        """Every teacher answer about this lesson."""
        return self._presence.for_session(session_id)

    # ------------------------------------------------------------- the plan (§1, §3)

    def plan(self, session_id: int) -> Plan:
        """Everything this CLOSED lesson has to say, and to whom.

        Pure: it reads and builds text and claims nothing.  The claim is ``claim()`` and it
        happens at the moment of sending, so that a plan built and never sent leaves no
        trace saying it was.

        No clock is consulted about whether the lesson is over.  The trigger is the lesson
        closing (P6 knows when that was) and never the hour, because §1 is a measurement
        about the building's reception and not a preference about times of day.
        """
        lesson = self.lesson(session_id)
        notifications = []

        silent = self._spiski.silent()
        graveyard = self._spiski.graveyard()
        work = self.handed_in(session_id)

        quiet_teachers = self.teachers_without_marks(session_id)
        for teacher in quiet_teachers:
            notifications.append(
                Uvedomlenie(
                    recipient_kind=RECIPIENT_TEACHER,
                    recipient_id=teacher.id,
                    recipient_tg_id=teacher.tg_id,
                    session_id=lesson.id,
                    text=teacher_question(lesson),
                    buttons=[(PRESENT, PRESENT), (ABSENT, ABSENT)],
                )
            )

        heads = self._heads.heads()
        summary = head_summary(lesson, work, silent, graveyard)
        for _room, teacher_id in heads:
            head = self._teachers.teacher(teacher_id)
            notifications.append(
                Uvedomlenie(
                    recipient_kind=RECIPIENT_HEAD,
                    recipient_id=teacher_id,
                    recipient_tg_id=head.tg_id if head is not None else None,
                    session_id=lesson.id,
                    text=summary,
                )
            )

        return Plan(
            session=lesson,
            notifications=notifications,
            teachers_considered=len(self._teachers.teachers()),
            heads_considered=len(heads),
        )

    # --------------------------------------------------------------- idempotency

    def claim(self, notification: Uvedomlenie) -> bool:
        """Take the right to send this one message, or find that somebody already did.

        ``True`` means send it.  ``False`` means the row was already there -- a restart, a
        second replica, a hand-run of the same command, a timer that fired twice: zero rows
        affected, and the caller stops.  One statement in the store, never a read followed
        by a write.
        """
        if notification.recipient_kind not in RECIPIENT_KINDS:
            raise SvodkaError(
                "recipient_kind %r is not one of %s"
                % (notification.recipient_kind, RECIPIENT_KINDS)
            )
        return self._sent.claim(
            notification.session_id,
            notification.recipient_kind,
            notification.recipient_id,
            self._clock.now_iso(),
        )

    def already_sent(self, session_id: int) -> list:
        return self._sent.already_sent(session_id)


# --------------------------------------------------------------------------- the words
#
# The text lives in module functions and not in the router, so that §4 has one home and
# the tests can read the words without a Telegram server.  Every wording below states a
# fact.  Nothing here ranks, scores, or measures one person against the class, and none of
# the game furniture section 4 forbids appears in any string below; no teacher is set
# beside another and no child is set beside another.  NOTHING is written next to a plus --
# a count stands alone.  (Named around, not spelled out: see the module docstring.)


def day_in_words(held_on: str) -> str:
    """``2026-09-08`` → ``8 сентября``.  The date a person says out loud.

    Falls back to the raw ISO string on anything unparseable rather than raising: a
    malformed date must not stop a summary that is otherwise correct, and the raw string
    is still readable by the human who gets it.
    """
    months = (
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря",
    )
    try:
        year, month, day = held_on[:10].split("-")
        return "%d %s" % (int(day), months[int(month) - 1])
    except (ValueError, IndexError):
        return held_on


def teacher_question(lesson: Session) -> str:
    """The whole message a teacher who marked nothing receives.

    A QUESTION ABOUT A FACT.  It does not say he forgot, it does not say what he owes, and
    it does not mention marks at all: «был» is a legitimate answer and the wording has to
    leave it legitimate.  The bookkeeping exists for preservation, not for control, and
    the first message that reads as control ends the willingness to use it.
    """
    return (
        "Вы были %s на занятии?\n"
        "\n"
        "Спрашиваем, чтобы отметить явку — она хранится отдельно от отметок."
        % day_in_words(lesson.held_on)
    )


def head_summary(
    lesson: Session,
    work: LessonWork,
    silent: SilentList,
    graveyard: GraveyardList,
) -> str:
    """The head's summary of one lesson: three things, in the order §3 names them.

    Each block carries its own coverage, because a number without one cannot be believed:
    «сдали трое» and «сдали трое из пятидесяти шести» are different statements.  An empty
    block says so in words rather than disappearing -- a block that vanishes is
    indistinguishable from a block that was never computed.
    """
    lines = ["Занятие %s. Сводка." % day_in_words(lesson.held_on), ""]

    # 1 -- who handed in how much.
    lines.append("Сдавали:")
    if not work.students:
        lines.append("  за это занятие записей нет — проверено %d из %d"
                     % (work.considered, work.considered))
    else:
        for row in work.students[:SILENT_LINES]:
            lines.append("  %s %s — %d" % (row.surname, row.name, row.count))
        if len(work.students) > SILENT_LINES:
            lines.append("  и ещё %d" % (len(work.students) - SILENT_LINES))
        lines.append(
            "  всего сдавали %d из %d" % (work.handed_in, work.considered)
        )
    lines.append("")

    # 2 -- who has been quiet for SILENT_SESSIONS lessons running.
    lines.append("Молчат %d занятия подряд:" % silent.sessions)
    if not silent.enough_days:
        lines.append(
            "  пока нечего мерить: занятий в журнале меньше %d" % silent.sessions
        )
    elif not silent.students:
        lines.append("  никого — проверено %d из %d"
                     % (silent.considered, silent.considered))
    else:
        for entry in silent.students[:SILENT_LINES]:
            student = entry.student
            if entry.last_active_day:
                lines.append(
                    "  %s %s — последний раз %s"
                    % (student.surname, student.name, day_in_words(entry.last_active_day))
                )
            else:
                lines.append("  %s %s" % (student.surname, student.name))
        if len(silent.students) > SILENT_LINES:
            lines.append("  и ещё %d" % (len(silent.students) - SILENT_LINES))
        lines.append(
            "  всего %d из %d" % (silent.found, silent.considered)
        )
        # Said in words, every time, because the list is read by a tired adult and the
        # wrong reading of it is the one thing this feature can actually break.
        lines.append("  Это те, с кем не поговорили.")
    lines.append("")

    # 3 -- problems almost nobody took.  A signal to work one at the board, not a report.
    lines.append("Задачи, которые почти никто не взял:")
    if not graveyard.entries:
        lines.append("  таких нет — порог %d, листков просмотрено %d"
                     % (graveyard.threshold, len(graveyard.sheets)))
    else:
        for entry in graveyard.entries[:GRAVEYARD_LINES]:
            lines.append(
                "  л.%s №%s — взяли %d"
                % (entry.sheet.number, entry.row.problem.label, entry.row.taken_by)
            )
        if len(graveyard.entries) > GRAVEYARD_LINES:
            lines.append("  и ещё %d" % (len(graveyard.entries) - GRAVEYARD_LINES))
        lines.append(
            "  порог %d, учеников %d" % (graveyard.threshold, graveyard.considered)
        )
        lines.append("  Такую стоит разобрать у доски.")

    text = "\n".join(lines).rstrip()
    if len(text) > MAX_TEXT:
        # Cut here rather than at the API, so a truncated summary is still a delivered
        # one; the same number and the same reason as ``ops/opoveshchenie.py``.
        text = text[: MAX_TEXT - 1].rstrip() + "…"
    return text
