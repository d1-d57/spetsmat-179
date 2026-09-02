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


class IdempotencyKeyReused(MarkingError):
    """One transport key arrived for two different cells.

    The key identifies a delivery, not a cell, so a caller that derives it from
    something coarser than the update -- a message id, a session, a date -- collides.
    Answering such a request from the journal would report somebody else's mark as this
    request's outcome and leave the requested cell silently untouched, which is the
    quietest possible failure: no write, no error, a button that does nothing.
    """


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
        # ``CellState`` is a ``str`` Enum, so a plain string like "solved" hashes equal to
        # its member and sails through the lookup below.  It would then fail the identity
        # test against ``current`` -- a raw string is never the same OBJECT as an enum
        # member -- and every repeated tap would write another event.  That is exactly the
        # path a caller takes when it parses a target out of a button payload, so the type
        # is checked at the door rather than trusted.
        if not isinstance(target, CellState):
            raise MarkingError(
                "target must be a CellState, not %s: %r" % (type(target).__name__, target)
            )
        if target not in EVENT_FOR_TARGET:
            raise MarkingError("not a target state: %r" % (target,))

        # Everything from here to the write is ONE transaction.  The decision of what to
        # write is made by reading what already stands, and between that read and the
        # write another teacher's tap can land: both would see an empty cell and both
        # would write an ``assert``.  The projected state survives that (it is still the
        # last event), but the journal grows a row the service promised not to write.
        with self._journal.transaction():
            return self._set_state_locked(
                student_id,
                problem_id,
                target,
                source=source,
                teacher_id=teacher_id,
                session_id=session_id,
                valid_at=valid_at,
                note=note,
                idempotency_key=idempotency_key,
            )

    def _set_state_locked(
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
        """The body of ``set_state``, running with the journal's write lock held."""
        # Transport idempotency first.  Telegram delivers at least once, so the same tap
        # can arrive twice; the caller passes a key derived from the update and the
        # redelivery is answered from the journal instead of being written again.
        if idempotency_key is not None:
            already = self._journal.find_by_idempotency_key(idempotency_key)
            if already is not None:
                # The key is unique across the whole journal, so a key that was written
                # for another cell must not answer for this one.
                if (already.student_id, already.problem_id) != (student_id, problem_id):
                    raise IdempotencyKeyReused(
                        "key %r was written for (student=%s, problem=%s) and cannot answer "
                        "for (student=%s, problem=%s)"
                        % (idempotency_key, already.student_id, already.problem_id,
                           student_id, problem_id)
                    )
                # Report the cell as it stands NOW, not as it stood when the key was
                # written: the mark may since have been retracted, and a redelivered
                # update must not make the bot redraw a button that is no longer true.
                standing = self._journal.last_event(student_id, problem_id)
                return MarkingOutcome(
                    state=STATE_AFTER[standing.event] if standing else CellState.EMPTY,
                    written=False,
                    reason="already recorded under this idempotency key",
                    mark=already,
                )

        last = self._journal.last_event(student_id, problem_id)
        current = STATE_AFTER[last.event] if last is not None else CellState.EMPTY

        # Semantic idempotency.  Re-marking the same target state does not double-write:
        # this is the half that survives a caller who has no key to pass.
        if current == target:
            return MarkingOutcome(
                state=current,
                written=False,
                reason="cell is already in the target state",
                mark=last,
            )

        event = EVENT_FOR_TARGET[target]

        # A reversing event must name exactly which event it undoes, and "nothing to
        # reverse" means nothing STANDING -- not merely no row in the journal.  An EMPTY
        # cell is empty whether it was never touched or was struck out by an erratum, and
        # in both cases there is no hand-in to take away.  Retracting a strike-out would
        # otherwise succeed and drag a record that "should never have existed" back into
        # the statistics as "handed in, not credited".
        #
        # Only a retract can reach this line with an EMPTY cell: an erratum targets EMPTY,
        # and an EMPTY cell is already in that target, so it was answered by the idempotent
        # branch above.
        reverses_id = None
        if event.reverses_something:
            if last is None or current is CellState.EMPTY:
                raise NothingToReverse(
                    "cell (student=%s, problem=%s) stands at %s: no event to %s"
                    % (student_id, problem_id, current.value, event.value)
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
