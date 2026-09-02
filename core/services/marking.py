"""Giving, retracting and striking out a mark.

THE RULE THAT SHAPES THIS FILE: a button carries the TARGET STATE, never a "toggle"
command.  ``set_state`` therefore takes the state the caller wants the cell to be in and
writes whatever event gets it there -- it never flips what it finds.  A double tap is
harmless by construction and the whole subject of races disappears: two identical taps
arriving in either order leave the same cell state and one journal row, not two.

Nothing here imports sqlite3 and nothing here imports any Telegram library.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.models import (
    STATE_AFTER,
    CellState,
    Mark,
    MarkDraft,
    MarkEvent,
)
from core.ports import Clock, MarkJournal


class MarkingError(Exception):
    """A marking request that the domain refuses."""


class NothingToReverse(MarkingError):
    """Asked to retract a cell that has no event standing to be retracted."""


#: Which event moves a cell into the requested target state.
EVENT_FOR_TARGET = {
    CellState.SOLVED: MarkEvent.ASSERT,
    CellState.RETRACTED: MarkEvent.RETRACT,
    CellState.EMPTY: MarkEvent.ERRATUM,
}


@dataclass(frozen=True)
class MarkingOutcome:
    """What the journal did about one request.

    ``written`` is False on both idempotent paths -- the cell was already in the target
    state, or this exact request had already been recorded under the same transport key.
    ``reason`` says which, because "nothing happened" and "nothing happened, again" are
    the two cases a bug in this area looks like.
    """

    state: CellState
    written: bool
    reason: str
    mark: Optional[Mark] = None


class MarkingService:
    def __init__(self, journal: MarkJournal, clock: Clock) -> None:
        self._journal = journal
        self._clock = clock

    # ------------------------------------------------------------------ entry point

    def set_state(
        self,
        student_id: int,
        problem_id: int,
        target: CellState,
        *,
        source: str,
        teacher_id: Optional[int] = None,
        session_id: Optional[int] = None,
        valid_at: Optional[str] = None,
        note: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> MarkingOutcome:
        """Bring one cell into ``target``, writing at most one journal event.

        ``valid_at`` is when the check-off actually happened and may be in the past -- a
        mark entered a day late keeps its own time.  ``recorded_at`` is stamped here and
        is always now.
        """
        if target not in EVENT_FOR_TARGET:
            raise MarkingError("not a target state: %r" % (target,))

        # Transport idempotency first.  Telegram delivers at least once, so the same tap
        # can arrive twice; the caller passes a key derived from the update and the
        # redelivery is answered from the journal instead of being written again.
        if idempotency_key is not None:
            already = self._journal.find_by_idempotency_key(idempotency_key)
            if already is not None:
                return MarkingOutcome(
                    state=STATE_AFTER[already.event],
                    written=False,
                    reason="already recorded under this idempotency key",
                    mark=already,
                )

        last = self._journal.last_event(student_id, problem_id)
        current = STATE_AFTER[last.event] if last is not None else CellState.EMPTY

        # Semantic idempotency.  Re-marking the same target state does not double-write:
        # this is the half that survives a caller who has no key to pass.
        if current is target:
            return MarkingOutcome(
                state=current,
                written=False,
                reason="cell is already in the target state",
                mark=last,
            )

        event = EVENT_FOR_TARGET[target]

        # A reversing event must name exactly which event it undoes.  With nothing
        # standing there is nothing to name.  Only a retract can reach this line with an
        # untouched cell -- an erratum targets EMPTY, and an untouched cell is already
        # EMPTY, so it was answered by the idempotent branch above.  A retract of a cell
        # that was never marked is a bug in the caller, and it raises rather than
        # inventing an event to reverse.
        reverses_id = None
        if event.reverses_something:
            if last is None:
                raise NothingToReverse(
                    "cell (student=%s, problem=%s) has no event to %s"
                    % (student_id, problem_id, event.value)
                )
            reverses_id = last.id

        recorded_at = self._clock.now_iso()
        draft = MarkDraft(
            student_id=student_id,
            problem_id=problem_id,
            event=event,
            valid_at=valid_at or recorded_at,
            recorded_at=recorded_at,
            source=source,
            session_id=session_id,
            reverses_id=reverses_id,
            teacher_id=teacher_id,
            note=note,
            idempotency_key=idempotency_key,
        )
        written = self._journal.append(draft)
        return MarkingOutcome(
            state=STATE_AFTER[written.event],
            written=True,
            reason="event written",
            mark=written,
        )

    # ----------------------------------------------------------- named conveniences

    def give(self, student_id: int, problem_id: int, **kwargs) -> MarkingOutcome:
        """The student solved it: target SOLVED, written as ``assert``."""
        return self.set_state(student_id, problem_id, CellState.SOLVED, **kwargs)

    def retract(self, student_id: int, problem_id: int, **kwargs) -> MarkingOutcome:
        """The student handed it in and did not defend it: target RETRACTED.

        Not a deletion.  The cell stops being credited and stops being a debt, and the
        hand-in stays in the statistics.
        """
        return self.set_state(student_id, problem_id, CellState.RETRACTED, **kwargs)

    def erratum(self, student_id: int, problem_id: int, **kwargs) -> MarkingOutcome:
        """Wrong button: target EMPTY, written as ``erratum``.

        The struck event stays visible in the journal and leaves the statistics entirely,
        as if it had never been recorded.  The cell goes to EMPTY -- NOT back to whatever
        stood there before the struck event.
        """
        return self.set_state(student_id, problem_id, CellState.EMPTY, **kwargs)
