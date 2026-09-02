"""Projections over the journal: the grid, the debts, the graveyard.

The journal is the truth; everything in this file is a view of it computed on demand.
Nothing is cached and no counter is kept up to date by hand, because a counter that
drifts from the journal is exactly the class of bug the differential test hunts.

THE SEMANTIC FORK, restated where it is used (it also stands in ``core/models.py`` and
in ``migrations/001_init.sql``): the state of a cell is the LAST event for the pair
(student, problem).

    no events   -> EMPTY      not credited; a debt, if the problem is obligatory
    'assert'    -> SOLVED     credited; counts in statistics
    'retract'   -> RETRACTED  not credited, NOT a debt -- it was handed in and not
                              defended; counts in statistics as "handed in, not credited"
    'erratum'   -> EMPTY      struck out of statistics entirely, as if it never was;
                              a debt again, if the problem is obligatory

Reversing an event returns the cell to EMPTY (or to RETRACTED), NEVER to whatever stood
there before the reversed event.  The projection never looks past the last event.
"""

from __future__ import annotations

from typing import Optional

import config
from core.models import CellState, Grid, GraveyardRow, Problem
from core.ports import Catalogue, MarkJournal


class ProgressService:
    def __init__(self, journal: MarkJournal, catalogue: Catalogue) -> None:
        self._journal = journal
        self._catalogue = catalogue

    # ------------------------------------------------------------------------ grid

    def grid(self, student_id: int, sheet_id: int) -> Grid:
        """The plusnik of one student over one sheet: every problem, with its state.

        Problems with no events are present and EMPTY.  A grid that silently omitted them
        would show a short sheet to the teacher, and the missing buttons are precisely
        the ones that still need tapping.
        """
        problems = self._catalogue.problems_of_sheet(sheet_id)
        states = self.states_for(student_id, [p.id for p in problems])
        return Grid(
            student_id=student_id,
            sheet_id=sheet_id,
            cells={p.id: states[p.id] for p in problems},
        )

    def states_for(
        self, student_id: int, problem_ids: list[int]
    ) -> dict[int, CellState]:
        """State of each named problem for one student, EMPTY where nothing was written."""
        states = {problem_id: CellState.EMPTY for problem_id in problem_ids}
        for cell in self._journal.cells(
            student_ids=[student_id], problem_ids=problem_ids
        ):
            if cell.problem_id in states:
                states[cell.problem_id] = cell.state
        return states

    def states_for_many(
        self, student_ids: list[int], problem_ids: list[int]
    ) -> dict[tuple, CellState]:
        """Every (student, problem) pair of the given rectangle, EMPTY where untouched.

        One query for the whole rectangle: the grids of a whole group are drawn together,
        and asking per student turns one round trip into fifty-six.
        """
        states = {
            (student_id, problem_id): CellState.EMPTY
            for student_id in student_ids
            for problem_id in problem_ids
        }
        for cell in self._journal.cells(
            student_ids=student_ids, problem_ids=problem_ids
        ):
            key = (cell.student_id, cell.problem_id)
            if key in states:
                states[key] = cell.state
        return states

    # ----------------------------------------------------------------------- debts

    def debts(self, student_id: int, current_sheet_ord: int) -> list[Problem]:
        """Obligatory problems left standing on sheets OLDER than the current one.

        Counted from the student's ``first_sheet_id``: whoever arrived at sheet 6 does
        not owe sheets 1-5 (evidence: Пирогов appeared from sheet 6 and had no older
        debts -- last year's import disagreed on exactly one student, and that is the
        disagreement that produced this rule).

        A RETRACTED cell is not a debt: the student handed the problem in.  An
        erratum-struck cell is a debt again, because the record should never have
        existed.
        """
        student = self._catalogue.student(student_id)
        if student is None:
            return []

        first_ord = self._first_sheet_ord(student.first_sheet_id)
        if first_ord is None or first_ord >= current_sheet_ord:
            return []

        problems = [
            p
            for p in self._catalogue.problems_between(first_ord, current_sheet_ord - 1)
            if p.is_obligatory
        ]
        if not problems:
            return []

        states = self.states_for(student_id, [p.id for p in problems])
        return [p for p in problems if states[p.id].is_debt_candidate]

    def _first_sheet_ord(self, first_sheet_id: Optional[int]) -> Optional[int]:
        """``ord`` of the student's first sheet; the very first sheet when unknown."""
        if first_sheet_id is not None:
            sheet = self._catalogue.sheet(first_sheet_id)
            if sheet is not None:
                return sheet.ord
        sheets = self._catalogue.sheets()
        return sheets[0].ord if sheets else None

    # ------------------------------------------------------------------- graveyard

    def graveyard(self, sheet_id: int, student_ids: Optional[list[int]] = None) -> list[GraveyardRow]:
        """How many students took each problem of a sheet, and which ones are graveyards.

        "Taken" means credited -- the cell stands at SOLVED.  A RETRACTED cell is a
        hand-in that was not defended, which is exactly the case the graveyard threshold
        is meant to notice, so it does not count as taken.
        """
        problems = self._catalogue.problems_of_sheet(sheet_id)
        if student_ids is None:
            student_ids = [s.id for s in self._catalogue.students()]

        states = self.states_for_many(student_ids, [p.id for p in problems])
        rows = []
        for problem in problems:
            taken = sum(
                1
                for student_id in student_ids
                if states[(student_id, problem.id)].is_credited
            )
            rows.append(GraveyardRow(problem=problem, taken_by=taken))
        return rows

    def graveyard_threshold(self) -> int:
        """The one place the threshold is read from, so it stays in ``config.py``."""
        return config.GRAVEYARD_THRESHOLD
