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

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional, Protocol, Sequence


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
class TeacherBinding:
    """What the middleware needs to know about a teacher: their role and their room."""

    teacher_id: int
    role: Role
    room: Optional[str]


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

    def bind_student_tg_id(self, *, student_id: int, tg_id: int) -> None:
        """Bind a Telegram id to an already-confirmed student.

        Raises ``TelegramIdAlreadyBound`` on collision.
        """

    def lookup_student(self, tg_id: int) -> Optional[int]:
        """The student id bound to this Telegram id, or None if unbound or pending."""


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
    ) -> None:
        self._port = port
        self._current_sheet = sheets_for_current

    # ---------- registration intake

    def submit_student(self, *, tg_id: int, surname: str, name: str) -> PendingRegistration:
        return self._port.create_pending(
            tg_id=tg_id,
            surname=surname,
            name=name,
            intended_role=Role.STUDENT,
        )

    def submit_teacher(
        self,
        *,
        tg_id: int,
        surname: str,
        name: str,
        room: Optional[str] = None,
    ) -> PendingRegistration:
        return self._port.create_pending(
            tg_id=tg_id,
            surname=surname,
            name=name,
            intended_role=Role.TEACHER,
            room=room,
        )

    def list_pending(self) -> list:
        return self._port.list_pending()

    # ---------- owner-side confirm

    def confirm_student(
        self,
        registration: PendingRegistration,
        *,
        student_id: int,
    ) -> int:
        """Promote a pending student to ``active`` and bind their ``tg_id``.

        ``first_sheet_id`` is set to the current sheet -- never NULL, never the
        first sheet of the year.  The schema carries ``tg_id`` as UNIQUE; the
        port raises ``TelegramIdAlreadyBound`` on collision and we re-raise.

        Returns the student id (the same as the one passed in, for chaining).
        """
        if registration.intended_role is not Role.STUDENT:
            raise RosterError(
                "registration %d is for a %s, not a student"
                % (registration.id, registration.intended_role.value)
            )
        current = self._current_sheet()
        if current is None:
            raise RosterError(
                "no current sheet to anchor first_sheet_id: refusing to register a "
                "student against NULL (NULL is the imported-row fallback, not the "
                "registration path)"
            )
        try:
            self._port.bind_student_tg_id(student_id=student_id, tg_id=registration.tg_id)
        except TelegramIdAlreadyBound:
            raise
        # Promotion (status, first_sheet_id) and pending-row removal are done by
        # the bot's transaction wrapper -- this service deliberately does not
        # know about the journal DB.
        return student_id

    def confirm_teacher(
        self,
        registration: PendingRegistration,
        *,
        teacher_id: int,
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
        return self._port.bind_teacher(teacher_id=teacher_id, role=role, room=room)

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