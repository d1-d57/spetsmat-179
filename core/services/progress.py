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

from dataclasses import dataclass
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


# ============================================================ статистика на экране
#
# 🔴 EVERY FUNCTION BELOW IS PURE AND TAKES THE STATES IT NEEDS, INSTEAD OF ASKING THE
# JOURNAL FOR THEM.  The кондуит already fetches the whole rectangle once
# (``states_for_many`` over every pupil × every problem, 31 000 cells) and redraws itself
# after EVERY write to the база (``veb/server.py::_peresobrat``).  Four величины each
# opening their own read of the same journal would be four more passes over it per redraw,
# for an answer already in memory — and, worse, four more places that could disagree with
# the projection about what a plus is.  The states come in; the arithmetic happens here and
# in exactly one place, so the screen, the tests and the SQL check all say the same number.
#
# «Сдал» here always means CREDITED — the cell stands at SOLVED.  A ``retract`` is a hand-in
# that was not defended and does NOT count, which is the same rule ``graveyard`` above
# already carries; a second reading of it here would be the second opinion this whole file
# refuses.


@dataclass(frozen=True)
class SchyotObyazatelnyh:
    """How many obligatory problems one pupil has taken, out of how many there are.

    ``vsego`` is counted over the problems HANDED IN, not over the whole year: the кондуит
    draws one table per листок, and a global number printed on the row of a листок table
    would answer a question that table is not asking.  The caller decides the scope by
    deciding which problems it passes.
    """

    sdano: int
    vsego: int

    @property
    def ostalos(self) -> int:
        """How many are still standing — the second half of what the owner asked to see."""
        return self.vsego - self.sdano

    @property
    def zakryl(self) -> bool:
        """Nothing obligatory left — the row the owner wants to glow.

        🔴 A СЧЁТ WITH ``vsego == 0`` IS NOT «ЗАКРЫЛ», AND THAT IS NOT PEDANTRY.  Листки
        ``1д``–``4д`` carry 18, 32, 23 and 26 problems and NOT ONE обязательная among
        them (counted on the live база 2026-09-10).  Vacuous truth would light up all
        fifty-three rows of four листков at once, and a signal that fires for everybody
        says nothing about anybody.
        """
        return self.vsego > 0 and self.sdano == self.vsego


def obyazatelnyh_sdano(problems, sostoyaniya, student_id: int) -> SchyotObyazatelnyh:
    """«Сдал столько обязательных из стольких» for one pupil over these problems.

    ОБЯЗАТЕЛЬНАЯ IS ASKED OF ``Problem.is_obligatory`` AND NEVER SPELLED OUT HERE.  The
    owner's «кружки И крестики вместе» is already the content of ``config.OBLIGATORY_KINDS``
    (``обязательная`` and ``письменная``, the ``◦`` and the ``†`` the листок prints), and a
    pair of kind names retyped in this file would be the copy that drifts the day a fifth
    kind is added — which is exactly how ``письменная`` cost three edits instead of one
    (``core/services/sheets.ProblemDraft.__post_init__``).

    Pairs missing from ``sostoyaniya`` count as not taken rather than raising: the caller
    that fetched a rectangle of the on-roll pupils and is now drawing one of them cannot
    be missing its own cells, and a pupil who left mid-year legitimately has none.
    """
    obyazatelnye = [p for p in problems if p.is_obligatory]
    sdano = sum(
        1
        for p in obyazatelnye
        if sostoyaniya.get((student_id, p.id), CellState.EMPTY).is_credited
    )
    return SchyotObyazatelnyh(sdano=sdano, vsego=len(obyazatelnye))


def skolko_sdalo(problem_id: int, student_ids, sostoyaniya) -> int:
    """How many of these pupils have this problem credited.

    🔴 THE LIST OF PUPILS IS THE CALLER'S AND IS NOT DEFAULTED HERE.  ``graveyard`` above
    falls back to «everybody in the catalogue» and is right to, because a year a pupil
    solved does not stop having happened when they leave.  The number drawn over a COLUMN
    of the кондуит is a different promise: it has to be checkable by counting the ``✓``
    visible in that column, and the кондуит draws only the pupils on the roll.  Two
    honest answers to two different questions; the difference is in who is passed in.
    """
    return sum(
        1
        for student_id in student_ids
        if sostoyaniya.get((student_id, problem_id), CellState.EMPTY).is_credited
    )


def zakryta_klassom(sdalo: int) -> bool:
    """«Сдало больше трёх людей — всё ок» (владелец 09.09), off the one threshold."""
    return sdalo > config.GRAVEYARD_THRESHOLD


def v_grobarij(sdalo: int) -> bool:
    """«Задача, которую решило меньше трёх людей из класса» (владелец 09.09).

    🔴 THE TWO PREDICATES DO NOT MEET, AND THAT IS THE OWNER'S OWN WORDING RATHER THAN A
    BUG INTRODUCED HERE.  «Закрыта классом» is *больше* трёх and гробарий is *меньше*
    трёх, so a problem taken by EXACTLY three is neither: it is not a гробарий and it is
    not marked closed.  Both read the single constant ``config.GRAVEYARD_THRESHOLD``, so
    the gap cannot widen by one of them being retuned; closing it is a decision for the
    owner and is asked as a question in the заход rather than legislated here.
    """
    return sdalo < config.GRAVEYARD_THRESHOLD


@dataclass(frozen=True)
class ZapisGrobaria:
    """One problem of a листок that has become historical, and who did take it.

    ``pervye`` holds AT MOST ``config.GRAVEYARD_THRESHOLD`` names — «когда три человека
    уже сдало, дальше имена не записывают» (владелец 09.09).  The cap is not merely a
    display limit: a гробарий row exists only while fewer than the threshold have taken
    the problem, so the cap and the rule are the same number and are read from the same
    place.
    """

    problem: Problem
    sdalo: int
    pervye: tuple


def zapisi_grobaria(problems, student_ids, sostoyaniya, kogda, imya) -> list:
    """The гробарий rows of ONE листок: its problems that fewer than three pupils took.

    ``kogda(student_id, problem_id)`` gives a sortable moment for a credited cell (the
    кондуит hands in the LESSON DAY of the standing event, which is what it already
    computes for every cell it draws) and ``imya(student_id)`` gives the name to print.
    Both are handed in rather than looked up: ``core/`` knows no SQL and no HTML, and the
    caller already holds both answers for the whole grid.

    ORDER IS «КТО СДАЛ РАНЬШЕ», TIES BROKEN BY NAME.  The moment available is the lesson
    day, not the second — the кондуит attributes every tick to a lesson (``core/services/
    history.zanyatie_po_iso``) and that is the granularity the screen shows anywhere else.
    Two pupils who took a problem at the same lesson are therefore genuinely tied, and the
    tie is broken by the name so the list is stable between two redraws of the same page
    rather than depending on dictionary order.  A pupil with no date at all sorts last
    rather than first: absence of a date is not evidence of being early.
    """
    zapisi = []
    for problem in problems:
        vzyavshie = [
            student_id
            for student_id in student_ids
            if sostoyaniya.get((student_id, problem.id), CellState.EMPTY).is_credited
        ]
        if not v_grobarij(len(vzyavshie)):
            continue
        vzyavshie.sort(key=lambda s: (kogda(s, problem.id) or "9999-12-31", imya(s)))
        zapisi.append(ZapisGrobaria(
            problem=problem,
            sdalo=len(vzyavshie),
            pervye=tuple(imya(s) for s in vzyavshie[:config.GRAVEYARD_THRESHOLD]),
        ))
    return zapisi
