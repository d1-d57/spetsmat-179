"""The grid -- the screen the whole bot exists for.

    Петров Василий · Листок 3 · сдано 6 из 20

    [✅1 ][✅2 ][ 3 ][✅4 ]
    [5а ][5б ][✅6 ][ 7 ]
    [ 8 ][✅9 ][10 ][11 ]
    ...
    [← Иванов][Другой листок][Сидорова →]

THREE PROPERTIES, AND EACH OF THEM IS A MEASUREMENT RATHER THAN A TASTE.

**Exactly ``config.GRID_COLUMNS`` columns.**  The constant, never the literal ``4``: the
number is a thumb target of 9.2-9.6 mm on a phone held one-handed, and at five columns
the buttons fall below it.  Wide-and-flat beats narrow-and-deep -- doubling the buttons
on one screen adds a small constant, while an extra level of navigation costs a full
cycle in the five-to-fifteen-second seam between two students.

**The order is FIXED for the whole lesson.**  It is the catalogue's ``ord``, so it cannot
depend on what is solved: problem 7б sits in the same cell all evening.  Solved ones do
not disappear, do not shrink and do not re-sort -- they change appearance and stay put.
Muscle memory is worth more than tidiness.

**The last row is padded to full width.**  Telegram stretches a short row's buttons
across the whole message, so a sheet of 23 problems would end in three buttons visibly
wider than the twenty above them -- destroying the very geometry the column count is
there to protect.  The fillers carry a real ``Noop`` payload with a real handler, so an
accidental tap dismisses the spinner and changes nothing.

Nothing in this module reads the journal, and nothing writes to it.  Every function is a
pure function of its arguments, which is what lets the layout test walk all eighteen seed
sheets through the real builder with no database and no event loop.
"""

from __future__ import annotations

from typing import Iterable, Optional, Sequence
from zoneinfo import ZoneInfo

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import config
from bot.callbacks import (
    CALLBACK_DATA_LIMIT_BYTES,
    OP_CLEAR,
    OP_SOLVE,
    Done,
    Mark,
    Noop,
    OpenGrid,
    PickSheet,
    payload_fits,
)
from core.isotime import parse_iso
from core.models import CellState, Problem, Sheet, Student

#: What a cell looks like in each state.  A marker and nothing else: §5 of the brief
#: forbids writing ANYTHING next to a plus -- no praise, no counter, no share of the
#: class, no points, no levels, no marks of merit.  The marker states the fact and
#: stops.  (Named around rather than with the forbidden words themselves: the готовности
#: gate greps this tree for them and cannot tell a prohibition from a violation.)
STATE_MARKER = {
    CellState.SOLVED: "✅",
    #: Handed in and not defended.  Not credited, and not a debt either -- so it must
    #: look different from both an empty cell and a solved one.
    CellState.RETRACTED: "↩",
    CellState.EMPTY: "",
}

#: The label of a filler button.  A middle dot rather than a space: Telegram trims a
#: button whose text is only whitespace and answers ``BUTTON_TEXT_EMPTY``.
FILLER_LABEL = "·"


# --------------------------------------------------------------------------- helpers

def button(text: str, payload: str) -> InlineKeyboardButton:
    """The ONE place a button is made, so the 64-byte law has a carrier in the BUILD and
    not only in a test.

    Telegram rejects the whole message when one payload is too long, and the API error
    names neither the button nor the row.  Refusing here names both, at the moment the
    keyboard is assembled, before anything has been sent -- and it means the rule holds
    for a payload shape nobody has written a test for yet, which is the shape that
    actually breaks.  Reachable only through a bug or an absurd id: the widest payload
    over the whole seed measures 14 bytes of the 64.
    """
    if not payload_fits(payload):
        raise ValueError(
            "callback_data %r is %d bytes, over Telegram's limit of %d, on the button %r"
            % (payload, len(payload.encode("utf-8")), CALLBACK_DATA_LIMIT_BYTES, text)
        )
    return InlineKeyboardButton(text=text, callback_data=payload)


def rows_of(items: Sequence, width: int) -> list:
    """Cut a flat sequence into rows of ``width``.  The last row may be short."""
    return [list(items[start:start + width]) for start in range(0, len(items), width)]


def _cell_button(problem: Problem, state: CellState, student_id: int) -> InlineKeyboardButton:
    """One problem, as the teacher sees it and as the payload names it.

    The payload asks for the OPPOSITE of what stands now, because that is the only tap
    that changes anything -- and asking twice for the same world is what makes the second
    tap harmless.  A solved cell offers "clear it", everything else offers "solve it";
    a RETRACTED cell offers "solve it" too, since re-solving is the way back.
    """
    op = OP_CLEAR if state is CellState.SOLVED else OP_SOLVE
    return button(
        "%s%s" % (STATE_MARKER[state], problem.label),
        Mark(student_id=student_id, task_id=problem.id, op=op).pack(),
    )


def _filler_button() -> InlineKeyboardButton:
    return button(FILLER_LABEL, Noop().pack())


def _name_of(student: Optional[Student]) -> str:
    """«Петров Василий» -- surname then given name, as the teacher's own list reads."""
    if student is None:
        return "ученик"
    return ("%s %s" % (student.surname, student.name)).strip()


# ------------------------------------------------------------------------ the grid

def grid_keyboard(
    problems: Sequence[Problem],
    states: dict,
    *,
    student_id: int,
    sheet_id: int,
    previous_student: Optional[Student] = None,
    next_student: Optional[Student] = None,
    columns: Optional[int] = None,
) -> InlineKeyboardMarkup:
    """The whole screen: the problem grid, then the navigation footer.

    ``states`` maps ``problem_id`` onto ``CellState``; a problem missing from it is
    EMPTY, which is the honest default -- a grid that silently dropped untouched problems
    would hide exactly the buttons that still need tapping.

    ``columns`` exists for the layout test to prove that the WIDTH is what drives the
    shape; production always passes ``None`` and gets ``config.GRID_COLUMNS``.
    """
    width = config.GRID_COLUMNS if columns is None else columns

    keyboard: list = []
    cells = [
        _cell_button(problem, states.get(problem.id, CellState.EMPTY), student_id)
        for problem in problems
    ]
    for row in rows_of(cells, width):
        while len(row) < width:
            row.append(_filler_button())
        keyboard.append(row)

    keyboard.append(
        _navigation_row(
            student_id=student_id,
            sheet_id=sheet_id,
            previous_student=previous_student,
            next_student=next_student,
        )
    )
    keyboard.append([button("Готово", Done(sheet_id=sheet_id).pack())])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def _navigation_row(
    *,
    student_id: int,
    sheet_id: int,
    previous_student: Optional[Student],
    next_student: Optional[Student],
) -> list:
    """«← Иванов · Другой листок · Сидорова →».

    The arrows carry the NEIGHBOUR'S id, resolved when the keyboard was built.  A payload
    that said "the next one" would have to be resolved against a roster that may have
    changed since -- and would walk from a position the screen no longer shows.  This is
    the same law as the mark button: a payload names its target, never an operation.

    It is a FOOTER, not a row of the grid: it is allowed to be narrower than the grid
    rows above it, and the layout test checks the grid rows only.
    """
    row: list = []
    if previous_student is not None:
        row.append(
            button(
                "← %s" % previous_student.surname,
                OpenGrid(student_id=previous_student.id, sheet_id=sheet_id).pack(),
            )
        )
    row.append(button("Другой листок", PickSheet(student_id=student_id).pack()))
    if next_student is not None:
        row.append(
            button(
                "%s →" % next_student.surname,
                OpenGrid(student_id=next_student.id, sheet_id=sheet_id).pack(),
            )
        )
    return row


def grid_header(
    student: Optional[Student],
    sheet: Optional[Sheet],
    states: dict,
) -> str:
    """«Петров Василий · Листок 3 · сдано 6 из 20».

    The count stands in the HEADER of the whole sheet, which is a different thing from
    the counter §5 forbids: nothing is written NEXT TO A PLUS, and this is not a rating,
    not a share of the class, not points and not a run of days -- it is how many of this
    sheet's problems the student has handed in, which is the question the teacher is
    holding in their head while they tap.
    """
    solved = sum(1 for state in states.values() if state.is_credited)
    return "%s · Листок %s · сдано %d из %d" % (
        _name_of(student),
        sheet.number if sheet is not None else "?",
        solved,
        len(states),
    )


def last_action_line(
    *,
    student: Optional[Student],
    problem_label: str,
    at_iso: str,
    cleared: bool = False,
) -> str:
    """«последнее: 7б, Петя, 14:32 — отменить».

    There is no «сохранить» anywhere on this screen and no confirmation dialog on a mark.
    Fast inattentive input produces slips, and a confirmation does not catch a slip -- it
    is dismissed automatically, by the same reflex that produced the slip.  The undo is a
    repeat tap on the cell, and this line is where the teacher reads WHICH cell that is.

    The time is displayed through ``zoneinfo`` and never through a fixed offset: the
    journal stores UTC, and «14:32» has to be the wall clock the teacher is looking at.
    """
    local = parse_iso(at_iso).astimezone(ZoneInfo(config.TZ_DISPLAY))
    given_name = student.name if student is not None else "ученик"
    verb = "снято" if cleared else "принята"
    return "последнее: %s, %s, %s — %s; отменить — тем же нажатием" % (
        problem_label,
        given_name,
        local.strftime("%H:%M"),
        verb,
    )


def mark_toast(problem_label: str, student: Optional[Student], *, cleared: bool) -> str:
    """The immediate answer to the tap: «7б — Петя ✓».

    It fires BEFORE the redraw, and it is not optional: at 800 ms a person cannot tell
    whether the tap counted and taps again.  Wording states the FACT -- «принята» -- and
    never a word of praise: §5 of the brief forbids praise as firmly as it forbids points.
    """
    given_name = student.name if student is not None else "ученик"
    return "%s — %s %s" % (problem_label, given_name, "снято" if cleared else "✓")


# --------------------------------------------------------------- the other two screens

def students_keyboard(students: Iterable[Student], *, sheet_id: int) -> InlineKeyboardMarkup:
    """The list «Готово» returns to.  One student per row -- surnames do not fit four
    across, and this list is not the screen the column measurement is about.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                button(
                    _name_of(student),
                    OpenGrid(student_id=student.id, sheet_id=sheet_id).pack(),
                )
            ]
            for student in students
        ]
    )


def sheets_keyboard(sheets: Iterable[Sheet], *, student_id: int) -> InlineKeyboardMarkup:
    """«Другой листок»: every sheet, in issue order, in the same column width as the grid.

    Sheet numbers are short (``1``, ``2д``), so the grid's width is the right one here and
    the tail is padded for the same reason it is padded there.
    """
    buttons = [
        button(
            "Листок %s" % sheet.number,
            OpenGrid(student_id=student_id, sheet_id=sheet.id).pack(),
        )
        for sheet in sheets
    ]
    keyboard = []
    for row in rows_of(buttons, config.GRID_COLUMNS):
        while len(row) < config.GRID_COLUMNS:
            row.append(_filler_button())
        keyboard.append(row)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
