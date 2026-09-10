"""The dict store the domain tests run on, and the two dates they name.

A separate module rather than ``conftest.py`` so that the test files can import it the
way ``tests/import/`` imports ``synthetic.py`` — pytest puts the test directory on the
path, and importing ``conftest`` by name loads it a second time under a different module
identity.

WHAT THIS FAKE IS AND IS NOT.  It imitates the schema's two guards, because a store that
accepted overlapping intervals would let the service tests pass while the real database
refused, and the service tests would then be testing the fake.  It proves nothing about
the schema itself: the guards are proven against the real migrated database in
``test_repo.py``, which is what the задание asks for — prove the refusal, do not assume it.
"""

from __future__ import annotations

from typing import Optional, Sequence

import config
from core.models import Enrollment
from core.services.enrollment import EnrollmentPort, OverlappingHistory

#: A Monday and a Thursday of the same week of the real season, so that a test naming
#: them does not have to explain which day of the week its literal date happens to be.
MONDAY = "2025-10-06"
THURSDAY = "2025-10-09"
MON, THU = 1, 4


class _NoTransaction:
    def __enter__(self):
        return None

    def __exit__(self, *exc):
        return False


class FakeEnrollmentStore(EnrollmentPort):
    """The enrollment store as a list of rows, with the schema's two guards imitated."""

    def __init__(self) -> None:
        self.rows: list = []
        self._next_id = 1
        #: How many times a row was closed.  A test asserts on it to show that a move
        #: performs exactly one close and exactly one insert, and no rewrite.
        self.closes = 0

    def transaction(self):
        return _NoTransaction()

    def open_row(self, student_id: int, slot: int) -> Optional[Enrollment]:
        for row in self.rows:
            if (row.student_id, row.slot) == (student_id, slot) and row.is_open:
                return row
        return None

    def rows_valid_on(
        self,
        day: str,
        slot: int,
        student_ids: Optional[Sequence[int]] = None,
    ) -> list:
        wanted = None if student_ids is None else set(student_ids)
        return [
            row
            for row in self.rows
            if row.slot == slot
            and row.valid_from <= day < row.valid_to
            and (wanted is None or row.student_id in wanted)
        ]

    def history(self, student_id: int, slot: Optional[int] = None) -> list:
        return sorted(
            (
                row
                for row in self.rows
                if row.student_id == student_id
                and (slot is None or row.slot == slot)
            ),
            key=lambda row: (row.slot, row.valid_from, row.id),
        )

    def insert(
        self,
        *,
        student_id: int,
        teacher_id: int,
        room: str,
        slot: int,
        valid_from: str,
        valid_to: str = config.OPEN_END_DATE,
    ) -> Enrollment:
        # Both guards in one test: the half-open overlap condition is
        # ``a.from < b.to and b.from < a.to``, and two open rows are the special case of
        # it in which both ``to`` are the sentinel.
        for row in self.rows:
            if (row.student_id, row.slot) != (student_id, slot):
                continue
            if row.valid_from < valid_to and valid_from < row.valid_to:
                raise OverlappingHistory(
                    "fake store: [%s, %s) overlaps [%s, %s)"
                    % (valid_from, valid_to, row.valid_from, row.valid_to)
                )
        row = Enrollment(
            id=self._next_id,
            student_id=student_id,
            teacher_id=teacher_id,
            room=room,
            slot=slot,
            valid_from=valid_from,
            valid_to=valid_to,
        )
        self._next_id += 1
        self.rows.append(row)
        return row

    def close(self, enrollment_id: int, *, valid_to: str) -> Enrollment:
        for index, row in enumerate(self.rows):
            if row.id == enrollment_id:
                # ``Enrollment`` is frozen, so the replacement is built explicitly and
                # names every field it carries over -- ``teacher_id`` among them, which
                # is copied from the standing row and never taken from a caller.
                closed = Enrollment(
                    id=row.id,
                    student_id=row.student_id,
                    teacher_id=row.teacher_id,
                    room=row.room,
                    slot=row.slot,
                    valid_from=row.valid_from,
                    valid_to=valid_to,
                )
                self.rows[index] = closed
                self.closes += 1
                return closed
        raise AssertionError("fake store: no row with id %s" % (enrollment_id,))


class FakeCalendar:
    """``TeacherCalendarPort`` over a plain dict: ``{teacher_id: {slots attended}}``.

    A teacher named in ``not_attending`` for a slot is absent from the set for that
    slot; every other (teacher, slot) pair attends, matching
    ``infra.prepodavatel_den_repo`` storing absence rather than presence.
    """

    def __init__(self, not_attending: "set[tuple[int, int]]" = frozenset()) -> None:
        self._not_attending = set(not_attending)

    def attends(self, teacher_id: int, slot: int) -> bool:
        return (teacher_id, slot) not in self._not_attending
