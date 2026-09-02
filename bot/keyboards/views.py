"""The viewing screens: payloads and text.  Nothing here reads the journal.

TWO READERS, TWO DIFFERENT SCREENS, AND THE DIFFERENCE BETWEEN THEM IS THE WHOLE POSITION.

The student gets their own year and a SHORT list of what is owed.  The teacher gets, as
the FIRST thing on the screen, the two lists that say where the attention is missing --
and the table of everybody against everything only second.

WHAT MAY NOT APPEAR ON EITHER OF THEM, AND WHY IT IS A MEASUREMENT AND NOT A TASTE.
No ranking, no share of the class, no points, no levels, no run of days, no marks of
merit.  Nothing at all is written beside a plus -- not praise, not a running count.

* Butler, 1988: a grade, and a grade WITH a comment, undermined equally; the number
  swallows the comment.  So "put the plus and write something encouraging next to it"
  does not work -- it is the arrangement that was measured and failed.
* Deci, Koestner and Ryan, 128 experiments: reward for performance undermines intrinsic
  motivation, d = -0.36.  An informing plus is a record of a fact; it turns controlling
  the moment something is given for it.
* An anonymous histogram is NOT neutral.  Schultz's boomerang: shown a norm, people drift
  towards it, downwards included.  In a room of selected children that is permission for
  a strong one to ease off.  The norm that works is the individual one -- not "34th of
  56" but "four problems last week, six this week".

And the sacred one: «уровень взаимопонимания между преподавателем и студентом становится
совершенно иным, когда преподаватель принимает задачи».  These screens do not replace the
conversation.  They say who it has not happened with.

(The forbidden words are named around rather than spelled out: the готовности gate greps
this tree for the literal strings and cannot tell a prohibition from a violation.)

THE HEADER COUNT IS NOT THE FORBIDDEN COUNTER.  «Листок 3 · сдано 6 из 20» stands over a
whole sheet and is the question the reader is already holding in their head; it is not a
rating, not a share of anybody else's result, and it is not written NEXT TO A PLUS.  This
is the same line P4 already draws in ``bot/keyboards/grid.grid_header`` and the same
reasoning; it is repeated here because a rule that lives only in another module's
docstring is a rule the next reader has to go looking for.

Every function below is a pure function of its arguments -- no database, no event loop --
which is what lets the render tests walk all eighteen seed sheets through the real
builders.
"""

from __future__ import annotations

from html import escape
from typing import Iterable, Optional, Sequence

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import config
from bot.callbacks import payload_fits, CALLBACK_DATA_LIMIT_BYTES
from bot.keyboards.grid import rows_of
from core.models import CellState, Problem, Sheet, Student

#: Telegram's hard cap on the text of one message, in CHARACTERS.  Not a style rule and
#: not ours to raise: the Bot API rejects the whole ``sendMessage`` above it, and the
#: sheet table of fifty-six students against forty-four problems is the one screen in this
#: project that can reach it.  A table that silently lost its last rows would be the worst
#: kind of wrong -- it would look complete.
MESSAGE_LIMIT_CHARS = 4096

#: How much of the limit the table is allowed to fill before it starts cutting students.
#: The rest is the header, the legend and the line that says how many rows were dropped;
#: that line is written AFTER the cut and has to fit too.
TABLE_BUDGET_CHARS = 3600

#: What one cell looks like in the whole-class table.  ONE character wide, always: a
#: proportional font cannot hold a table in line, and even inside ``<pre>`` a marker that
#: changes width shifts every column to its right.  ``bot/keyboards/grid.STATE_MARKER``
#: is deliberately NOT reused -- it is built for a button, where an empty label and a
#: two-cell emoji are both fine.
TABLE_MARKER = {
    CellState.SOLVED: "+",
    #: Handed in and not defended.  Not credited, and not a debt either, so it must look
    #: different from both of the others.
    CellState.RETRACTED: "-",
    CellState.EMPTY: "·",
}

#: What one cell looks like in a student's own sheet, where there is room for a word.
OWN_MARKER = {
    CellState.SOLVED: "принята",
    CellState.RETRACTED: "сдана, не защищена",
    CellState.EMPTY: "—",
}

#: How wide a surname column is in the table.  Longer surnames are cut with an ellipsis;
#: at fifty-six rows the alternative is a table whose width is set by one long name.
TABLE_SURNAME_WIDTH = 12


# -------------------------------------------------------------------------- payloads
#
# Prefixes: ``m g d s x`` already belong to P4 (``bot/callbacks.py``).  These five are
# new and start with ``v`` so that a payload read out of a log says which screen it came
# from without a lookup.
#
# EVERY STUDENT PAYLOAD CARRIES ``student_id`` ON PURPOSE, and the server refuses it when
# it is not the caller's own.  The field is not what the screen reads -- the handler takes
# the id from the middleware's ``identity`` and never from the payload -- so the refusal
# and the read are two INDEPENDENT carriers of the same rule, and removing either one
# still leaks nothing.  A payload with no id at all would make the forgery untestable
# rather than impossible, and «проверено 0 из 56» is the shape of a green run that proves
# nothing.


class ViewYear(CallbackData, prefix="vy"):
    """The student's own year, sheet by sheet: ``vy:56``."""

    student_id: int


class ViewSheet(CallbackData, prefix="vh"):
    """One sheet of the student's own year: ``vh:56:12``."""

    student_id: int
    sheet_id: int


class ViewDebts(CallbackData, prefix="vd"):
    """The student's own short debt list: ``vd:56``."""

    student_id: int


class ViewLists(CallbackData, prefix="vl"):
    """Back to the teacher's two lists: ``vl:``."""


class ViewTable(CallbackData, prefix="vt"):
    """The whole-class table of one sheet: ``vt:12``."""

    sheet_id: int


# --------------------------------------------------------------------------- helpers

def button(text: str, payload: str) -> InlineKeyboardButton:
    """The ONE place a button of these screens is made.

    Telegram rejects the whole message when one payload is over the limit, and the API
    error names neither the button nor the row.  Refusing here names both, before anything
    has been sent.  Same law and same reason as ``bot/keyboards/grid.button``; it is a
    second function rather than an import of that one only because this module must not
    grow a dependency on the grid's cell semantics.
    """
    if not payload_fits(payload):
        raise ValueError(
            "callback_data %r is %d bytes, over Telegram's limit of %d, on the button %r"
            % (payload, len(payload.encode("utf-8")), CALLBACK_DATA_LIMIT_BYTES, text)
        )
    return InlineKeyboardButton(text=text, callback_data=payload)


def _name_of(student: Optional[Student]) -> str:
    if student is None:
        return "ученик"
    return ("%s %s" % (student.surname, student.name)).strip()


def _clip(text: str, width: int) -> str:
    """Cut to ``width`` characters, marking the cut.  Padding is the caller's business."""
    if len(text) <= width:
        return text
    return text[: width - 1] + "…"


# ------------------------------------------------------------------ student: the year

def year_text(student: Optional[Student], rows: Sequence) -> str:
    """The whole year, one line per sheet.

    This is the screen P2 loaded fifteen thousand events for: a student opens the bot on
    the first of September and sees their entire eighth form, not a running total of it.
    Sheets with nothing on them are printed too -- a year that dropped its empty sheets
    would not be the year that happened.
    """
    lines = ["%s · ваш год" % _name_of(student)]
    if not rows:
        lines.append("листков пока нет")
        return "\n".join(lines)
    for row in rows:
        lines.append(
            "Листок %s · сдано %d из %d" % (row.sheet.number, row.solved, row.total)
        )
    return "\n".join(lines)


def year_keyboard(rows: Sequence, *, student_id: int) -> InlineKeyboardMarkup:
    """One button per sheet, in the grid's own width, plus the way to the debt list."""
    buttons = [
        button(
            "Листок %s" % row.sheet.number,
            ViewSheet(student_id=student_id, sheet_id=row.sheet.id).pack(),
        )
        for row in rows
    ]
    keyboard = [list(row) for row in rows_of(buttons, config.GRID_COLUMNS)]
    keyboard.append(
        [button("Что нужно сдать", ViewDebts(student_id=student_id).pack())]
    )
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ----------------------------------------------------------- student: one own sheet

def own_sheet_text(
    student: Optional[Student],
    sheet: Optional[Sheet],
    problems: Sequence[Problem],
    states: dict,
) -> str:
    """One sheet of the student's own year, problem by problem.

    The order is the catalogue's ``ord`` and never «solved first»: the sheet is a paper
    object the student has in front of them, and re-sorting it makes the screen and the
    paper disagree.  Beside a credited problem stands the word «принята» and nothing
    else -- a statement of fact, not of worth.
    """
    solved = sum(1 for problem in problems if states.get(problem.id, CellState.EMPTY).is_credited)
    lines = [
        "%s · Листок %s · сдано %d из %d"
        % (
            _name_of(student),
            sheet.number if sheet is not None else "?",
            solved,
            len(problems),
        )
    ]
    if sheet is not None and sheet.title:
        lines.append(sheet.title)
    for problem in problems:
        state = states.get(problem.id, CellState.EMPTY)
        lines.append("%s — %s" % (problem.label, OWN_MARKER[state]))
    return "\n".join(lines)


def own_sheet_keyboard(*, student_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [button("К году", ViewYear(student_id=student_id).pack())],
            [button("Что нужно сдать", ViewDebts(student_id=student_id).pack())],
        ]
    )


# --------------------------------------------------------------- student: the debts

def debts_text(student: Optional[Student], debts) -> str:
    """The SHORT list: one boundary named, everything older in a single line.

    A long enumeration of what you owe is a message at the level of the PERSON -- «ты
    должник» -- and not at the level of the task.  One nearest boundary is a task.

    THE DOOR IS ALWAYS OPEN, and the last line says so in as many words.  That is
    Konstantinov's own rule: you do not hand it in, you fall out; you may come back the
    moment you do.  A screen that only listed the debt would be carrying half of a rule
    whose other half is the whole point of it.
    """
    lines = ["%s · что нужно сдать" % _name_of(student)]
    if debts.is_clear:
        lines.append("обязательных долгов нет")
        return "\n".join(lines)

    for group in debts.near:
        lines.append(
            "обязательные из листка %s: %s"
            % (group.sheet.number, ", ".join(problem.label for problem in group.problems))
        )
    if debts.older_problems:
        lines.append(
            "и ещё %d с более ранних листков (%d)"
            % (debts.older_problems, debts.older_sheets)
        )
    lines.append("прийти и сдать можно в любой момент")
    return "\n".join(lines)


def debts_keyboard(*, student_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[button("К году", ViewYear(student_id=student_id).pack())]]
    )


# ------------------------------------------------------------ teacher: the two lists

def lists_text(silent, graveyard) -> str:
    """The teacher's FIRST screen, and the order of the two lists is the position itself.

    Kovaldzhi and Kanel-Belov's account of the sheet system names defect no. 7: «проверяющие
    зачастую уделяют больше времени сильным учащимся».  A table of everybody against
    everything does not fix that -- it shows the teacher what the teacher already sees.
    The list of who has said nothing DOES fix it: without a record, a teacher simply does
    not know who they have not talked to.

    Both lists carry their coverage in the line itself.  «Молчат: трое» and «молчат 3 из
    56 за 3 занятия» are different facts, and only the second one can be acted on.
    """
    lines = []

    if not silent.enough_days:
        lines.append(
            "Не сдавал ничего %d занятия подряд: занятий в журнале пока меньше %d — "
            "считать не из чего (учеников %d)"
            % (config.SILENT_SESSIONS, config.SILENT_SESSIONS, silent.considered)
        )
    elif not silent.students:
        lines.append(
            "Не сдавал ничего %d занятия подряд: никто, проверено %d из %d"
            % (config.SILENT_SESSIONS, silent.considered, silent.considered)
        )
    else:
        lines.append(
            "Не сдавал ничего %d занятия подряд (%s): %s"
            % (
                config.SILENT_SESSIONS,
                ", ".join(silent.days),
                ", ".join(entry.student.surname for entry in silent.students),
            )
        )
        lines.append("— всего %d из %d" % (silent.found, silent.considered))

    lines.append("")

    covered = ", ".join("л.%s" % sheet.number for sheet in graveyard.sheets) or "нет листков"
    if not graveyard.entries:
        lines.append(
            "Задачи, которые не взял почти никто (%s): таких нет, порог %d, учеников %d"
            % (covered, graveyard.threshold, graveyard.considered)
        )
    else:
        lines.append(
            "Задачи, которые не взял почти никто (%s): %s"
            % (
                covered,
                ", ".join(
                    "л.%s %s (%d)" % (entry.sheet.number, entry.row.problem.label, entry.row.taken_by)
                    for entry in graveyard.entries
                ),
            )
        )
        lines.append(
            "— всего %d, порог %d, учеников %d"
            % (graveyard.found, graveyard.threshold, graveyard.considered)
        )
    return "\n".join(lines)


def lists_keyboard(sheets: Iterable[Sheet]) -> InlineKeyboardMarkup:
    """The way to the table, which is the SECOND screen and never the first."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [button("Таблица листка %s" % sheet.number, ViewTable(sheet_id=sheet.id).pack())]
            for sheet in sheets
        ]
    )


# ------------------------------------------------------------- teacher: the table

def table_text(
    sheet: Optional[Sheet],
    problems: Sequence[Problem],
    students: Sequence[Student],
    states: dict,
) -> str:
    """Everybody against everything, on one sheet, inside ``<pre>``.

    HTML, and the only place in these screens that uses it.  The bot's default parse mode
    is ``None`` (``bot/app.build``), so a proportional font would put every column in a
    different place; ``<pre>`` is what makes fifty-six rows of markers readable at all.
    Every piece of text that goes in is escaped -- a surname is data, and the seed
    contains labels like ``10а:)``.

    IT REFUSES TO LIE ABOUT ITS OWN LENGTH.  Fifty-six students against forty-four
    problems can pass Telegram's message limit; when it does, rows are dropped from the
    END and the last line says how many.  A table that silently lost its tail would look
    complete, which is worse than a short one.
    """
    header = "Листок %s · учеников %d · задач %d" % (
        sheet.number if sheet is not None else "?",
        len(students),
        len(problems),
    )
    legend = "столбцы: %s" % ", ".join(
        "%d=%s" % (index + 1, problem.label) for index, problem in enumerate(problems)
    )
    key = "+ принята · сдана, не защищена: - · не сдана: ·"

    rows = []
    for student in students:
        markers = "".join(
            TABLE_MARKER[states.get((student.id, problem.id), CellState.EMPTY)]
            for problem in problems
        )
        rows.append("%-*s %s" % (TABLE_SURNAME_WIDTH, _clip(student.surname, TABLE_SURNAME_WIDTH), markers))

    head = "\n".join([header, legend, key])
    shown = len(rows)
    while shown and len(head) + 1 + sum(len(row) + 1 for row in rows[:shown]) > TABLE_BUDGET_CHARS:
        shown -= 1

    body = rows[:shown]
    tail = []
    if shown < len(rows):
        tail.append("показано %d из %d учеников — не помещается в одно сообщение"
                    % (shown, len(rows)))

    text = "<pre>%s</pre>" % escape("\n".join([head] + body + tail))
    return text


def table_keyboard() -> InlineKeyboardMarkup:
    """Back to the two lists.  The first screen is the lists, so the way back is to them."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[button("К спискам", ViewLists().pack())]]
    )
