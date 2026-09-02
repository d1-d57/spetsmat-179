"""The domain, as plain Python objects.  No Telegram library, and no SQL.

Everything above this layer -- the bot, the importer, a future web client -- is an
adapter beside it, which is the whole reason this tree is forbidden to import the bot
framework in even one line.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import config


class MarkEvent(str, Enum):
    """The three kinds of journal event.

    The distinction comes from accounting (сторно) and from FHIR.  A single ``deleted``
    flag destroys it: "the student did not defend this" and "the teacher hit the wrong
    button" are different facts about the world and are counted differently.
    """

    #: The mark was given.
    ASSERT = "assert"
    #: It was there and was taken away -- the student did not defend it.  Counts in
    #: statistics as "handed in, not credited".
    RETRACT = "retract"
    #: The record should never have existed (wrong button).  Struck out of statistics,
    #: still visible in the journal.
    ERRATUM = "erratum"

    @property
    def reverses_something(self) -> bool:
        """True for the events that must name the event they undo."""
        return self in (MarkEvent.RETRACT, MarkEvent.ERRATUM)


class CellState(str, Enum):
    """What one cell of the grid -- one (student, problem) pair -- currently says.

    The state of a cell is the LAST event for the pair.  Reversing an event returns the
    cell to EMPTY or to RETRACTED, NEVER to whatever stood there before the reversed
    event: the projection never looks past the last event.  To put a plus back, the
    teacher taps the target state again and a fresh ``assert`` is written -- which is
    safe precisely because a button carries the target state and never a "toggle".

    This is a real fork and it is written down here on purpose, so that nobody redefines
    it in six months by picking whichever reading feels natural that day.
    """

    #: No events at all, or the last event was an ``erratum``.  Not credited; a debt, if
    #: the problem is obligatory.
    EMPTY = "empty"
    #: The last event was an ``assert``.  Credited.
    SOLVED = "solved"
    #: The last event was a ``retract``.  Not credited -- but NOT a debt either: the
    #: student did hand it in and failed to defend it.
    RETRACTED = "retracted"

    @property
    def is_credited(self) -> bool:
        """Does this cell count as a plus in the student's total?"""
        return self is CellState.SOLVED

    @property
    def counts_in_statistics(self) -> bool:
        """Is there anything here at all, from the statistics' point of view?

        ``erratum`` is struck out entirely, so an EMPTY cell contributes nothing.
        ``retract`` is not struck out: it is a hand-in that was not credited.
        """
        return self in (CellState.SOLVED, CellState.RETRACTED)

    @property
    def is_debt_candidate(self) -> bool:
        """Would this cell be a debt, if the problem were obligatory and old enough?

        Debts are obligatory problems with no ``assert`` and no ``retract`` standing --
        that is exactly EMPTY.
        """
        return self is CellState.EMPTY


#: How a resulting cell state is reached, event by event.  Written once, used by the
#: projection; the naive fold in the differential test deliberately does NOT import it.
STATE_AFTER = {
    MarkEvent.ASSERT: CellState.SOLVED,
    MarkEvent.RETRACT: CellState.RETRACTED,
    MarkEvent.ERRATUM: CellState.EMPTY,
}


@dataclass(frozen=True)
class Sheet:
    id: int
    number: str
    ord: int
    title: Optional[str] = None
    issued_at: str = ""


@dataclass(frozen=True)
class Problem:
    id: int
    sheet_id: int
    label: str
    kind: str
    ord: int

    @property
    def is_obligatory(self) -> bool:
        """Only obligatory problems create a debt.  A starred problem is an invitation."""
        return self.kind in config.OBLIGATORY_KINDS


@dataclass(frozen=True)
class Student:
    id: int
    surname: str
    name: str
    klass: Optional[str] = None
    status: str = "pending"
    #: The first sheet this student was present for.  Debts are counted from it: whoever
    #: arrived at sheet 6 does not owe sheets 1-5.
    first_sheet_id: Optional[int] = None
    tg_id: Optional[int] = None


@dataclass(frozen=True)
class Teacher:
    id: int
    name: str
    aka: Optional[str] = None
    tg_id: Optional[int] = None
    is_owner: bool = False


@dataclass(frozen=True)
class Session:
    id: int
    held_on: str
    kind: str = "обычное"


@dataclass(frozen=True)
class Mark:
    """One event in the append-only journal.  Never updated, never deleted.

    Two times, and they are not the same question:
      * ``valid_at``    -- when the check-off happened;
      * ``recorded_at`` -- when it reached the database.
    A mark entered a day late must stay distinguishable from one entered on the spot.
    """

    id: int
    student_id: int
    problem_id: int
    event: MarkEvent
    valid_at: str
    recorded_at: str
    source: str
    session_id: Optional[int] = None
    reverses_id: Optional[int] = None
    teacher_id: Optional[int] = None
    note: Optional[str] = None
    idempotency_key: Optional[str] = None


@dataclass(frozen=True)
class MarkDraft:
    """A mark on its way into the journal -- everything but the id the journal assigns."""

    student_id: int
    problem_id: int
    event: MarkEvent
    valid_at: str
    recorded_at: str
    source: str
    session_id: Optional[int] = None
    reverses_id: Optional[int] = None
    teacher_id: Optional[int] = None
    note: Optional[str] = None
    idempotency_key: Optional[str] = None


@dataclass(frozen=True)
class Cell:
    """The projection of one (student, problem) pair: its state and the event that set it."""

    student_id: int
    problem_id: int
    state: CellState
    last_event_id: Optional[int] = None


@dataclass(frozen=True)
class Enrollment:
    """Who teaches this student on this lesson day, over the half-open interval
    ``[valid_from, valid_to)``.  The open row carries ``config.OPEN_END_DATE``."""

    id: int
    student_id: int
    teacher_id: int
    room: str
    #: ISO-8601 weekday, Monday = 1.  Part of the key: the same student may have one
    #: teacher on Monday and another on Thursday.
    weekday: int
    valid_from: str
    valid_to: str = config.OPEN_END_DATE

    @property
    def is_open(self) -> bool:
        return self.valid_to == config.OPEN_END_DATE


@dataclass(frozen=True)
class GraveyardRow:
    """One problem, and how many students actually took it."""

    problem: Problem
    taken_by: int

    @property
    def is_graveyard(self) -> bool:
        """Fewer than the threshold means the problem is a graveyard: ✘ at <= 2, ✓ at >= 3."""
        return self.taken_by < config.GRAVEYARD_THRESHOLD


@dataclass(frozen=True)
class Grid:
    """The plusnik of one student over one sheet."""

    student_id: int
    sheet_id: int
    cells: dict = field(default_factory=dict)  # problem_id -> CellState

    @property
    def solved(self) -> int:
        return sum(1 for state in self.cells.values() if state.is_credited)

    @property
    def total(self) -> int:
        return len(self.cells)
