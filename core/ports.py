"""The seams.  ``core/`` talks to the outside world only through these Protocols.

Nothing here imports sqlite3 and nothing here imports any Telegram library.  ``infra/``
implements them against SQLite; a test implements them against a dict when that is
cheaper.  This is what makes the bot, the importer and the tests adapters BESIDE the
core rather than rewrites of it.

(The name of the forbidden library is deliberately not spelled out anywhere under
``core/``: the готовности gate greps this tree for that literal string, so writing it
even inside a comment turns the gate red.)
"""

from __future__ import annotations

from typing import ContextManager, Optional, Protocol, Sequence

from core.models import Cell, Mark, MarkDraft, Problem, Sheet, Student


class Clock(Protocol):
    """Where ``recorded_at`` comes from.  Injected so that tests can hold time still."""

    def now_iso(self) -> str:
        """Current moment, UTC, in the one wire format of ``core.isotime``."""


class MarkJournal(Protocol):
    """The append-only journal of marks.

    There is no ``update`` and no ``delete`` in this Protocol, and that is not an
    oversight: the schema refuses both with a trigger, so offering them here would be
    offering a method that always raises.
    """

    def transaction(self) -> ContextManager[None]:
        """Serialise a read-then-write of this journal against other writers.

        ``set_state`` decides what to write by reading what already stands, and between
        the read and the write another teacher's tap can land.  Without this seam the two
        taps both see an empty cell and both write an ``assert``: the projected state is
        still right, but the journal has two rows where the service promises one, and
        "a double tap is harmless by construction" stops being true.

        It is a PORT and not a bare SQL statement on purpose -- ``core/`` must not know
        that the store is SQLite.  The SQLite adapter spells it ``begin immediate``, which
        takes the write lock at the start rather than on first write, so the loser waits
        out ``config.BUSY_TIMEOUT_MS`` instead of failing.  A store that does not need it
        may implement it as a no-op.
        """

    def append(self, draft: MarkDraft) -> Mark:
        """Write one event and return it with the id the journal assigned."""

    def last_event(self, student_id: int, problem_id: int) -> Optional[Mark]:
        """The event with the largest id for this pair, or None if the cell is untouched."""

    def find_by_idempotency_key(self, key: str) -> Optional[Mark]:
        """The event already written under this transport key, if any."""

    def cells(
        self,
        student_ids: Optional[Sequence[int]] = None,
        problem_ids: Optional[Sequence[int]] = None,
    ) -> list[Cell]:
        """Project the journal: one Cell per pair that has at least one event.

        Pairs with no events are absent -- the caller knows which pairs exist and fills
        them in as EMPTY.
        """

    def events(
        self,
        student_ids: Optional[Sequence[int]] = None,
        problem_ids: Optional[Sequence[int]] = None,
    ) -> list[Mark]:
        """The raw journal, oldest event first.  For audit, import checks and folds."""


class Catalogue(Protocol):
    """Everything that is not an event: who studies here and what the sheets contain."""

    def student(self, student_id: int) -> Optional[Student]: ...

    def students(self) -> list[Student]: ...

    def sheet(self, sheet_id: int) -> Optional[Sheet]: ...

    def sheets(self) -> list[Sheet]:
        """All sheets, in ``ord`` order."""

    def problems_of_sheet(self, sheet_id: int) -> list[Problem]:
        """The problems of one sheet, in ``ord`` order."""

    def problems_between(self, first_ord: int, last_ord: int) -> list[Problem]:
        """Problems of every sheet whose ``ord`` lies in ``[first_ord, last_ord]``."""
