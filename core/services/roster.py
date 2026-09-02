"""Registration and role bookkeeping on top of the read-only catalogue.

Three things live here:

  * the roles of the project (HEAD, TEACHER, STUDENT) -- a closed enumeration, just
    like the ones in ``config.py``;
  * the seam ``RosterService`` uses to read and write, so that ``bot/`` does not know
    there is a second SQLite file behind it;
  * the rules for turning a ``pending`` registration into a confirmed account.

Nothing here imports the bot framework, and nothing here imports sqlite3 -- both are
forbidden in ``core/``.  The owner decides who is a head, never the teacher themselves.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional, Protocol, Sequence

from core.services.raspoznavanie import case_forms, ratio


class Role(str, Enum):
    """What a confirmed account is allowed to do.

    ``STUDENT`` only reads its own pluses and debts.  ``TEACHER`` only marks
    hand-ins.  ``HEAD`` does everything ``TEACHER`` does and, separately, loads
    sheets and edits today's assignment -- a head is bound to a room, not a
    boolean on the teacher.
    """

    STUDENT = "student"
    TEACHER = "teacher"
    HEAD = "head"

    @classmethod
    def from_text(cls, text: str) -> "Role":
        """Parse the wire value.  Raises ``UnknownRole`` on garbage, never returns None."""
        try:
            return cls(text)
        except ValueError as exc:
            raise UnknownRole("unknown role: %r" % (text,)) from exc

    @property
    def can_mark(self) -> bool:
        """``True`` for the two roles that may write marks."""
        return self in (Role.TEACHER, Role.HEAD)

    @property
    def can_upload_sheet(self) -> bool:
        """Only the head of a room loads sheets."""
        return self is Role.HEAD


#: The three rooms the conduit runs in.  P2 closes the seed-data hole for the head
#: of 203; this constant is here so the seam names the rooms a role can attach to.
ROOMS: Sequence[str] = ("203", "302", "303")


# ----------------------------------------------------------- domain errors

class RosterError(Exception):
    """A roster request the domain refuses."""


class UnknownRole(RosterError):
    """The wire value is not one of the closed set in ``Role``."""


class TelegramIdAlreadyBound(RosterError):
    """A second ``tg_id`` would overwrite an existing binding.

    ``tg_id`` is UNIQUE in the schema, and the schema is the carrier -- not the
    service.  The service catches the integrity error here so the bot can show a
    human message instead of letting ``sqlite3.IntegrityError`` escape.
    """


class NoSuchRegistration(RosterError):
    """The owner acted on a registration that has since been resolved."""


class AmbiguousStudent(RosterError):
    """The name on a заявка fits more than one row of the catalogue.

    Raised only by the paths that are asked for ONE row.  The owner-facing path does
    not raise: it reads ``StudentMatch.candidates`` and draws a button per candidate,
    because a machine made to choose between two children will choose, instantly and
    confidently, and be wrong half the time.
    """


# ----------------------------------------------------------- domain shapes

@dataclass(frozen=True)
class PendingRegistration:
    """A registration that has typed its name but not been confirmed by the owner."""

    id: int
    tg_id: int
    surname: str
    name: str
    intended_role: Role
    #: Which room the teacher claims to belong to; only meaningful for HEAD/TEACHER.
    room: Optional[str] = None


@dataclass(frozen=True)
class CatalogueStudent:
    """One row of the read-only catalogue, as the matcher needs to see it.

    Deliberately NOT ``core.models.Student``: the matcher wants four fields and the
    port that produces them lives in ``infra/roster_repo.py``, which reads the journal
    directly.  ``tg_id`` is carried because a row that is already bound must still be
    a candidate -- excluding it would hide the collision and let the owner create the
    duplicate this whole position exists to prevent.
    """

    id: int
    surname: str
    name: str
    tg_id: Optional[int] = None

    @property
    def label(self) -> str:
        return "%s %s" % (self.surname, self.name)


@dataclass(frozen=True)
class ScoredStudent:
    """A catalogue row and how well the заявка fits it, 0..1."""

    student: CatalogueStudent
    score: float


@dataclass(frozen=True)
class StudentMatch:
    """What the catalogue has to say about one заявка.

    ``kind`` is the whole answer and the screen reads nothing else:

      * ``single``    -- exactly one row fits; bind to it, do not create;
      * ``ambiguous`` -- two or more fit within a hair of each other; the owner picks
        from buttons, and the machine does not guess;
      * ``none``      -- nobody fits; a new row may be created, but only after the
        owner presses «нет в списке — завести нового» and never on its own.
    """

    kind: str
    candidates: Sequence[ScoredStudent] = ()

    @property
    def one(self) -> CatalogueStudent:
        """The single fitting row.  Raises unless ``kind`` is ``single``."""
        if self.kind != "single":
            raise AmbiguousStudent(
                "match is %r, not 'single': %d candidates" % (self.kind, len(self.candidates))
            )
        return self.candidates[0].student


@dataclass(frozen=True)
class TeacherBinding:
    """What the middleware needs to know about a teacher: their role and their room."""

    teacher_id: int
    role: Role
    room: Optional[str]


# ----------------------------------------------------------- matching a заявка
#
# 🔴 THIS SECTION WRITES NO INDEX OF ITS OWN.  ``core/services/raspoznavanie.py`` (P7,
# accepted) already expands the fifty-six surnames across the Russian cases and already
# owns the similarity metric; a second expansion here would be a second thing to keep
# right, and the two would drift.  What is added is only the part P7 has no reason to
# have: which of the scored rows counts as an ANSWER and which counts as a TIE.
#
# 🔴 THE METRIC IS ``raspoznavanie.ratio`` AND NOTHING ELSE.  P7 names the alternative
# it forbids and why, at the top of its own §6 -- the containment-tolerant variant of
# the same family scores a perfect match whenever one string sits inside the other, so
# «Пирогов» inside «Пирогов Костя» beats «Пирогов» itself and the comparison this
# section exists to make stops working.  The forbidden name is written out ONCE, in
# ``core/services/raspoznavanie.py`` where the metric lives; repeating the literal here
# would put the same rule in two places and make the grep that guards this module go
# red on its own warning.

#: A surname must fit at least this well before the row is a candidate at all.  Measured
#: floor, not a guess: «Пирогов К.» against «Пирогов» scores 0,82 BEFORE the initial is
#: stripped, and the ё/е and hyphen cases score 1,0 after normalisation.
SURNAME_FLOOR = 0.75

#: The combined score below which a row is not offered even as a button.  «Иванов Иван»
#: against this catalogue reaches 0,71 at its best, and must come back as «nobody».
ACCEPT_FLOOR = 0.80

#: How close the runner-up has to be before the answer stops being an answer.  On the
#: live catalogue «Цукунов Александр» scores 0,90 against BOTH «Цикунов Александр» and
#: «Цуканов Александр» -- an exact tie between two real children -- and that is the case
#: this band exists to catch.  A correctly spelled surname beats its nearest neighbour
#: by more than 0,05 on all fifty-six rows, measured.
TIE_BAND = 0.05

#: The surname carries the identity and the given name breaks the ties between
#: namesakes, which is why the weights are not equal.
_SURNAME_WEIGHT = 0.7
_NAME_WEIGHT = 0.3

#: A lone letter with a full stop: «Пирогов К.» -- an initial, not a name.  The child
#: types the form off the paper header, and the header carries initials.
_INITIAL = re.compile(r"^\w\.$", re.UNICODE)


def normalise_name(text: str) -> str:
    """Fold away the four differences that are NOT a different person.

    ``ё``/``е`` (the school's own lists disagree with themselves -- «Коневник Федор» and
    «Болотин Фёдор» sit in the same file), hyphen versus space, a trailing initial, and
    stray whitespace.  Everything else is left alone: this is a normaliser, not a
    corrector, and a corrector would start deciding who somebody is.
    """
    lowered = (text or "").strip().lower().replace("ё", "е").replace("-", " ")
    words = [word for word in lowered.split() if not _INITIAL.match(word)]
    return " ".join(words)


def _field_score(query: str, catalogue_value: str) -> Optional[float]:
    """0..1 for one field, or ``None`` when the заявка said nothing in that field.

    🔴 ``None`` IS NOT ZERO, AND THE DIFFERENCE IS A DUPLICATE.  «Пирогов» typed with
    «К.» in the given-name box normalises to a given name of nothing at all -- the
    initial is stripped, correctly, because an initial is not a name.  Scoring that as
    a zero drags a perfect surname down to 0,70, below ``ACCEPT_FLOOR``, and the owner
    is shown «в списке не найден» with the create button one press away from a second
    Пирогов.  A field nobody filled in is a field with no evidence in it, and evidence
    that does not exist must not vote.  *Found by the verifier of this position, on
    exactly that заявка.*
    """
    needle = normalise_name(query)
    if not needle:
        return None
    forms = case_forms(catalogue_value) or (catalogue_value,)
    return max(ratio(needle, normalise_name(form)) for form in forms) / 100.0


def _combine(surname_score: Optional[float], name_score: Optional[float]) -> float:
    """Weigh the fields that carry evidence, and only those.

    Both present: the surname carries 0,7 and the given name breaks ties with 0,3.
    Given name absent: the surname carries the whole decision -- the weights are
    renormalised rather than the missing half counted as a mismatch.
    """
    if surname_score is None:
        return 0.0
    if name_score is None:
        return surname_score
    return _SURNAME_WEIGHT * surname_score + _NAME_WEIGHT * name_score


def score_student(surname: str, name: str, student: CatalogueStudent) -> float:
    """How well a заявка fits one catalogue row, 0..1."""
    return _combine(
        _field_score(surname, student.surname), _field_score(name, student.name)
    )


def match_students(
    surname: str,
    name: str,
    catalogue: Sequence[CatalogueStudent],
) -> StudentMatch:
    """Which rows of the catalogue this заявка can be, and whether that is an answer.

    Pure: no port, no database, no bot.  The three outcomes are the three the owner's
    screen draws, and nothing here decides between two children.
    """
    scored: list = []
    for student in catalogue:
        surname_score = _field_score(surname, student.surname)
        if surname_score is None or surname_score < SURNAME_FLOOR:
            continue
        combined = _combine(surname_score, _field_score(name, student.name))
        if combined >= ACCEPT_FLOOR:
            scored.append(ScoredStudent(student=student, score=combined))
    if not scored:
        return StudentMatch(kind="none")
    best = max(row.score for row in scored)
    tied = sorted(
        (row for row in scored if row.score >= best - TIE_BAND),
        key=lambda row: (-row.score, row.student.id),
    )
    return StudentMatch(kind="single" if len(tied) == 1 else "ambiguous", candidates=tuple(tied))


# ----------------------------------------------------------- the port

class RosterPort(Protocol):
    """The seam ``RosterService`` writes through.

    ``bot/`` talks to ``RosterService``, not to this port directly.  The port is
    a Protocol so the service can be tested with an in-memory stub and so the bot
    does not know there is a second SQLite file behind the curtain.
    """

    def create_pending(
        self,
        *,
        tg_id: int,
        surname: str,
        name: str,
        intended_role: Role,
        room: Optional[str] = None,
    ) -> PendingRegistration:
        """Write a pending registration.  Raises ``TelegramIdAlreadyBound``."""

    def list_pending(self) -> list:
        """Every pending registration, oldest first."""

    def get_pending(self, registration_id: int) -> Optional[PendingRegistration]:
        """One pending registration, or None if it has been resolved."""

    def resolve_pending(self, registration_id: int, *, accept: bool) -> None:
        """Accept or reject.  ``accept=False`` simply drops the pending row.

        On accept, the corresponding ``students`` or ``teachers`` row has already
        been promoted by the caller -- the port only deletes the pending record.
        """

    def rename_pending(self, registration_id: int, *, surname: str, name: str) -> None:
        """The owner pressed rename; rewrite the visible fields."""

    def bind_teacher(
        self,
        *,
        teacher_id: int,
        role: Role,
        room: Optional[str] = None,
    ) -> TeacherBinding:
        """Persist the role of one teacher.

        Raises ``TelegramIdAlreadyBound`` if a second ``tg_id`` would overwrite.
        """

    def lookup_teacher(self, tg_id: int) -> Optional[TeacherBinding]:
        """What the middleware needs to know about one teacher, or None."""

    def lookup_teacher_by_id(self, teacher_id: int) -> Optional[TeacherBinding]:
        """The same lookup by primary key -- avoids a join through the journal DB."""

    def bind_student_tg_id(self, *, student_id: int, tg_id: int) -> None:
        """Bind a Telegram id to an already-confirmed student.

        Raises ``TelegramIdAlreadyBound`` on collision.
        """

    def lookup_student(self, tg_id: int) -> Optional[int]:
        """The student id bound to this Telegram id, or None if unbound or pending."""

    def create_confirmed_student(
        self,
        *,
        surname: str,
        name: str,
        klass: Optional[str],
        first_sheet_id: int,
        tg_id: int,
    ) -> int:
        """Insert a confirmed student and bind tg_id, in one operation.

        Returns the new student id.  Raises ``TelegramIdAlreadyBound`` on
        collision with an existing student row's tg_id.  Used by the owner
        when accepting a pending student -- the caller (the bot) has already
        read the current sheet id from the catalogue.
        """

    def create_confirmed_teacher(
        self,
        *,
        name: str,
        aka: Optional[str],
        tg_id: int,
        role: Role,
        room: Optional[str] = None,
    ) -> int:
        """Insert a confirmed teacher and bind tg_id + role, in one operation.

        Returns the new teacher id.  Raises ``TelegramIdAlreadyBound`` on
        collision.  Used by the owner when accepting a pending teacher.
        """

    def catalogue_students(self) -> list:
        """Every row of the catalogue, as ``CatalogueStudent``.

        The read the matcher needs.  It sits on the port rather than on a new
        constructor argument of the service on purpose: ``bot/app.py`` builds the
        service and is read-only for this position, so a new argument there would be
        a change nobody is allowed to make.  The port already holds the journal.
        """

    def attach_student_to_row(self, *, student_id: int, tg_id: int) -> None:
        """Bind a Telegram id to an EXISTING catalogue row and make it ``active``.

        🔴 ``first_sheet_id`` is NOT touched: the imported row already carries the
        sheet the child actually started on, and overwriting it with today's sheet
        would erase every debt the import was loaded to show.

        Raises ``TelegramIdAlreadyBound`` when the row, or the Telegram id, is
        already spoken for -- loudly, never a silent overwrite.
        """

    def claim_notification(self, registration_id: int) -> bool:
        """Claim the right to notify the owner about this заявка.

        ``True`` exactly once per заявка.  The claim is on disk, so a second call --
        from a retry, from a restarted process, from anywhere -- returns ``False``
        and no second message goes out.
        """


# ----------------------------------------------------------- the service

class RosterService:
    """The domain layer over the port.

    The bot calls this.  The port is its dependency; tests substitute a fake.
    """

    def __init__(
        self,
        port: RosterPort,
        *,
        sheets_for_current: Callable[[], Optional[int]],
        on_pending: Optional[Callable[[PendingRegistration], None]] = None,
    ) -> None:
        self._port = port
        self._current_sheet = sheets_for_current
        self._on_pending = on_pending

    # ---------- who is told about a new заявка

    def set_pending_notifier(
        self, notifier: Optional[Callable[[PendingRegistration], None]]
    ) -> None:
        """Install the callback fired once per new заявка.

        A plain callable, because ``core/`` may not import the bot framework.  The bot
        installs one that sends the owner a message; the tests install one that appends
        to a list; nothing here knows the difference.
        """
        self._on_pending = notifier

    def _announce(self, registration: PendingRegistration) -> None:
        """Fire the notifier at most once per заявка, ever.

        The claim is taken BEFORE the call and lives on disk, so the guarantee survives
        a restart, a retry and a second caller.  A notifier that throws must not undo a
        registration that has already been written: the заявка is the thing that
        matters, the message is not.
        """
        if self._on_pending is None:
            return
        if not self._port.claim_notification(registration.id):
            return
        self._on_pending(registration)

    # ---------- registration intake

    def submit_student(self, *, tg_id: int, surname: str, name: str) -> PendingRegistration:
        pending = self._port.create_pending(
            tg_id=tg_id,
            surname=surname,
            name=name,
            intended_role=Role.STUDENT,
        )
        self._announce(pending)
        return pending

    def submit_teacher(
        self,
        *,
        tg_id: int,
        surname: str,
        name: str,
        room: Optional[str] = None,
    ) -> PendingRegistration:
        pending = self._port.create_pending(
            tg_id=tg_id,
            surname=surname,
            name=name,
            intended_role=Role.TEACHER,
            room=room,
        )
        self._announce(pending)
        return pending

    def list_pending(self) -> list:
        return self._port.list_pending()

    # ---------- owner-side confirm

    def match_student(self, registration: PendingRegistration) -> StudentMatch:
        """Which catalogue row this заявка is, if the catalogue can tell.

        The read the owner's screen runs BEFORE it does anything: one hit binds, a tie
        draws buttons, no hit offers to create.  Nothing is written here.
        """
        self._require_student(registration)
        return match_students(
            registration.surname, registration.name, self._port.catalogue_students()
        )

    def bind_student(self, registration: PendingRegistration, student_id: int) -> int:
        """Attach this заявка's Telegram id to an EXISTING catalogue row.

        🔴 The whole point of the position.  ``first_sheet_id`` stays as the import
        left it: Пирогов started at sheet 6 last year, his two hundred and one marks
        hang off that row, and today's sheet written over it would turn every one of
        them into a debt he does not owe.

        Returns the bound student id.  Raises ``TelegramIdAlreadyBound`` when the row
        or the Telegram id is already taken -- the schema's UNIQUE is the carrier and
        this path does not soften it.
        """
        self._require_student(registration)
        self._port.attach_student_to_row(
            student_id=student_id, tg_id=registration.tg_id
        )
        return student_id

    def create_new_student(
        self,
        registration: PendingRegistration,
        *,
        klass: Optional[str] = None,
    ) -> int:
        """Create a row for somebody the catalogue does not have.

        🔴 REACHABLE ONLY FROM AN EXPLICIT OWNER BUTTON.  Until 02.09 this was what
        «принять» did unconditionally, and on the live base it would have produced a
        second Пирогов with an empty year while the real two hundred and one marks
        stayed on a row nobody was bound to.

        ``first_sheet_id`` is the CURRENT sheet -- the Пирогов rule again, read from
        the other side: whoever arrives in November is not charged for September.
        """
        self._require_student(registration)
        current = self._current_sheet()
        if current is None:
            raise RosterError(
                "no current sheet to anchor first_sheet_id: refusing to register a "
                "student against NULL (NULL is the imported-row fallback, not the "
                "registration path)"
            )
        return self._port.create_confirmed_student(
            surname=registration.surname,
            name=registration.name,
            klass=klass,
            first_sheet_id=current,
            tg_id=registration.tg_id,
        )

    def confirm_student(
        self,
        registration: PendingRegistration,
        *,
        klass: Optional[str] = None,
    ) -> int:
        """Resolve a pending student against the catalogue, binding where it can.

        One matching row -> bind to it and return ITS id.  No matching row -> create,
        because a caller that asked for a decision has to get one.  A TIE, however, is
        refused with ``AmbiguousStudent``: this method has no way to draw buttons, and
        guessing here is exactly the failure the position was opened for.  The owner's
        screen does not call this -- it calls ``match_student`` and then one of the two
        explicit halves above.

        Returns the student id, existing or new.
        """
        match = self.match_student(registration)
        if match.kind == "single":
            return self.bind_student(registration, match.one.id)
        if match.kind == "ambiguous":
            raise AmbiguousStudent(
                "registration %d fits %d catalogue rows (%s); the owner must choose"
                % (
                    registration.id,
                    len(match.candidates),
                    ", ".join(row.student.label for row in match.candidates),
                )
            )
        return self.create_new_student(registration, klass=klass)

    def _require_student(self, registration: PendingRegistration) -> None:
        if registration.intended_role is not Role.STUDENT:
            raise RosterError(
                "registration %d is for a %s, not a student"
                % (registration.id, registration.intended_role.value)
            )

    def confirm_teacher(
        self,
        registration: PendingRegistration,
        *,
        role: Role,
        room: Optional[str] = None,
    ) -> TeacherBinding:
        """Promote a pending teacher to a confirmed role.

        On confirmation the teacher starts in ``role`` (HEAD or TEACHER).  P2's
        hole for the head of 203 is closed HERE: the owner can confirm that
        teacher as HEAD even if the seed never had the row.
        """
        if registration.intended_role not in (Role.TEACHER, Role.HEAD):
            raise RosterError(
                "registration %d is for a %s, not a teacher"
                % (registration.id, registration.intended_role.value)
            )
        if role is Role.HEAD and room is None:
            raise RosterError("a HEAD must be bound to a room")
        # The full name the teacher gave is the teacher's ``name``; the
        # shorter surname goes into ``aka`` so a search by either works.
        teacher_id = self._port.create_confirmed_teacher(
            name="%s %s" % (registration.surname, registration.name),
            aka=registration.surname,
            tg_id=registration.tg_id,
            role=role,
            room=room,
        )
        return self._port.lookup_teacher_by_id(teacher_id)

    def reject(self, registration_id: int) -> None:
        self._port.resolve_pending(registration_id, accept=False)

    def accept(self, registration_id: int) -> None:
        self._port.resolve_pending(registration_id, accept=True)

    def rename(self, registration_id: int, *, surname: str, name: str) -> None:
        self._port.rename_pending(registration_id, surname=surname, name=name)

    # ---------- middleware-side lookups

    def role_of_teacher(self, tg_id: int) -> Optional[TeacherBinding]:
        return self._port.lookup_teacher(tg_id)

    def student_id_for(self, tg_id: int) -> Optional[int]:
        return self._port.lookup_student(tg_id)