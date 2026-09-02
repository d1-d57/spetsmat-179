"""The fourth door: a teacher types the sheet, taps the table, and the taps reach P4.

Buttons (P4), photo (P7), voice (P8) and text are EQUAL ways into one journal, and this
screen owns no marking logic of its own.  It builds a draft with
``core/services/bystryj_tekst.py``, shows it, lets a human correct it, and writes through
``MarkingService`` exactly as a tap on the grid does.  If this file were deleted the
journal would lose an input, not a capability.

THERE IS NEVER A DIRECT WRITE.  Nothing typed reaches the journal until a person has
looked at the whole table and pressed «Записать».  Third finalised point of the interview,
no exception -- not for four rows that all resolved, not for a message the bot has seen
before.

WHY THIS IS NOT A SECOND CONFIRMATION TABLE
-------------------------------------------
The задание forbids a second table and a second write path, and the prohibition is obeyed
where it bites:

  * the DRAFT is ``golos.Draft`` / ``DraftRow`` / ``DraftCell`` -- P8's dataclasses, which
    are themselves built on P7's metric and threshold;
  * the STORED SHAPE is the same dict the photo and voice screens store, which is what
    lets ``bot.routers.photo.checked_cells`` stay ONE function deciding what «Записать»
    would write, for all three recognising screens;
  * the WRITE is ``MarkingService.set_state``, the same call a grid tap makes.

What is genuinely this screen's own is the KEYBOARD, and it has to be: a callback payload
names the handler that will receive it, so a button drawn with P8's ``vc:`` prefix would
route a typed table's taps into the voice screen's state slot and be answered «устарело».
The prefixes below are checked against every other prefix in this bot by a test.

Two things this screen shows that the others do not, both measured on the owner's own
lines: the SHEET a label was found on when it was not the block's own sheet, and the
ЯВКА a прочерк asserts.

⚠ **THE ROUTER IS BUILT HERE AND INCLUDED NOWHERE.**  ``bot/app.py`` is outside this
position's zone -- exactly as it was for P7's ``photo.py`` and P8's ``voice.py``, which are
in the same state.  ``text_dependencies()`` below is the whole of the wiring, written so
that adding it is a few lines rather than a reading exercise; the gap is reported in
``## ОТЧЁТ``, not silently closed by an out-of-zone edit.  Where it must go is not a
preference and is stated once, here:

    AFTER  registration / owner / student / teacher  -- they claim plain text while an
           FSM dialogue is open (a surname being typed at registration, and later P14's
           attendance question and P19's rename), and an earlier router wins;
    AFTER  the grid router;
    BEFORE ``marking``'s stale catch-all -- it claims every callback nobody above it
           matched, so a table included after it would never receive one tap.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

import config
from bot.callbacks import ids_are_storable
from bot.keyboards.grid import button, rows_of
from bot.middleware import require_role
from bot.routers.marking import MARKING_ROLES, NOT_MODIFIED
from bot.routers.photo import checked_cells
from core.models import CellState
from core.services import bystryj_tekst as tekst
from core.services.golos import Verdict
from core.services.marking import MarkingError

#: Where one typed table waits for its confirmation, in THIS teacher's FSM store.  Two
#: teachers typing side by side must not see each other's table; the store is already
#: per-chat, so nothing here is keyed by a teacher id.  A slot of its own rather than the
#: voice slot, so that a dictation and a typed line can be in flight at the same time.
DRAFT_SLOT = "text_draft"

#: Toggle buttons per keyboard row.  The same four as the grid, for the same measured
#: reason: at five they fall below the comfortable one-handed thumb target.
COLUMNS = config.GRID_COLUMNS


# =============================================================================
#  PAYLOADS
# =============================================================================
#
# Numbers only, and nothing a human typed -- the two laws of ``bot/callbacks.py``: a
# surname in a payload is a surname leaving the server, and the separator ``:`` occurs
# inside real problem labels (`10а:)`).
#
# ⚠ These belong in ``bot/callbacks.py`` beside every other payload of this bot; that file
# is outside this position's zone, so they live here and the move is named in ``## ВОПРОСЫ``
# -- the same debt P8 recorded for the same reason.

class TextCell(CallbackData, prefix="tc"):
    """Toggle one cell: ``tc:0:2`` -- row 0, cell 2.

    Positions in the table, NOT ids: the table is what this teacher is looking at, it lives
    in their own FSM store, and an index cannot name a row of somebody else's screen.
    """

    row: int
    cell: int


class TextPick(CallbackData, prefix="tp"):
    """Answer «кто это?» with a tap: ``tp:1:23``.

    The id travels because the alternatives were computed server-side when the table was
    drawn.  A forged id buys nothing: the handler accepts it only if this row offered it.
    """

    row: int
    student_id: int


class TextConfirm(CallbackData, prefix="ty"):
    """«Записать» -- the one button that reaches the journal.  ``ty:1``.

    The field exists so that the payload CONTAINS THE SEPARATOR: the stale catch-all reads
    a separator-free token as a decoration of whatever screen is on display and declines to
    redraw over it, and a confirm button must never be mistaken for one.
    """

    ok: int = 1


class TextCancel(CallbackData, prefix="tn"):
    """«Отмена» -- drop the draft.  Nothing was written, so nothing is undone."""

    ok: int = 1


# =============================================================================
#  THE DRAFT, AS IT LIVES IN THE FSM STORE
# =============================================================================

def draft_to_state(draft) -> dict:
    """``golos.Draft`` -> plain dicts and lists, in the shape P7 and P8 already store.

    Plain, because ``MemoryStorage`` keeps whatever it is given and a Redis one keeps only
    what serialises.  ``checked`` and ``shown`` are spelled P7's way ON PURPOSE: that is
    what lets ``checked_cells`` be one function instead of three.  The keys this channel
    adds -- ``present_no_marks`` on a row, ``sheet_number`` and ``on_lead_sheet`` on a
    cell -- are additions to that shape and not a replacement of it, so every reader of
    the old keys keeps working.
    """
    return {
        "transcript": draft.transcript,
        "sha256": draft.audio_sha256,
        "channels": draft.channels,
        "rows": [
            {
                "said": row.said,
                "surname_text": row.surname_text,
                "student_id": row.student_id,
                "verdict": row.verdict.value,
                "alternatives": list(row.alternatives),
                "reason": row.reason,
                "present_no_marks": bool(getattr(row, "present_no_marks", False)),
                "sheet_marker": getattr(row, "sheet_marker", None),
                "cells": [
                    {
                        "label": cell.label,
                        "problem_id": cell.problem_id,
                        "printed_label": cell.printed_label,
                        "checked": bool(cell.ticked),
                        "shown": True,
                        "sheet_number": getattr(cell, "sheet_number", None),
                        "on_lead_sheet": bool(getattr(cell, "on_lead_sheet", True)),
                    }
                    for cell in row.cells
                ],
            }
            for row in draft.rows
        ],
    }


def present_students(stored: dict) -> list:
    """``[student_id, ...]`` the прочерки of this table assert were in the room.

    The stored twin of ``tekst.attendance_intents``, and it applies the same two rules:
    a row with no student resolved contributes nothing, and neither does a row the parser
    marked DOUBTFUL.  Attendance lands on a child the teacher confirmed or it does not
    land -- a plus on a stranger's line is at least a plus somebody may notice missing,
    while an invented явка is a fact about a child nobody will ever go looking for.

    The second rule reads the STORED verdict rather than the parsed one on purpose: a tap
    on «кто это?» rewrites that field to ``certain``, so the teacher's answer is what turns
    a distrusted row into a counted one.
    """
    return [
        row["student_id"]
        for row in stored.get("rows", [])
        if row.get("present_no_marks")
        and row.get("student_id") is not None
        and row.get("verdict") == Verdict.CERTAIN.value
    ]


# =============================================================================
#  DRAWING
# =============================================================================

def _name_of(catalogue, student_id: Optional[int]) -> str:
    if student_id is None:
        return "?"
    student = catalogue.student(student_id)
    if student is None:
        return "ученик %d" % student_id
    return ("%s %s" % (student.surname, student.name)).strip()


def _cell_text(cell: dict) -> str:
    """One button: the state, the label the SHEET prints, and the sheet when it surprises.

    The printed label rather than the typed one, because that is what the teacher will look
    for on the paper in their hand.  The sheet is appended ONLY when the label came from
    somewhere other than the block's own sheet -- on the owner's own line `9а` did exactly
    that, and a button reading plain «9а» gave no way to see that the plus was about to
    land on листок 1 from last autumn.
    """
    label = cell.get("printed_label") or cell.get("label")
    if cell.get("problem_id") is None:
        return "✗ %s" % label
    if not cell.get("on_lead_sheet", True) and cell.get("sheet_number"):
        label = "%s (л.%s)" % (label, cell["sheet_number"])
    return "%s %s" % ("✓" if cell.get("checked") else "·", label)


def render(stored: dict, catalogue) -> tuple:
    """``(text, keyboard)`` for the whole table.

    SHOWN WHOLE.  Not the doubtful rows, not the first five: a teacher who has to scroll to
    see what a machine read into their message will confirm without reading, and the
    confirmation is the only thing standing between a parser and the journal.
    """
    lines = ["✍️ Разобрано из вашего сообщения:"]
    keyboard: list = []
    unresolved = 0

    for index, row in enumerate(stored.get("rows", [])):
        if row.get("student_id") is None:
            unresolved += 1
            lines.append("%d. ❓ «%s» — кто это?" % (index + 1, row.get("surname_text") or "—"))
        else:
            lines.append(
                "%d. %s%s%s"
                % (
                    index + 1,
                    _name_of(catalogue, row["student_id"]),
                    " [л.%s]" % row["sheet_marker"] if row.get("sheet_marker") else "",
                    " ⚠" if row.get("verdict") == Verdict.DOUBTFUL.value else "",
                )
            )

        cells = row.get("cells", [])
        if cells:
            keyboard.extend(
                rows_of(
                    [
                        button(_cell_text(cell), TextCell(row=index, cell=position).pack())
                        for position, cell in enumerate(cells)
                    ],
                    COLUMNS,
                )
            )
        elif row.get("present_no_marks"):
            # The прочерк, said in words on the screen.  It is a statement about the
            # child, not an absence of one, and a row that merely looked empty here would
            # read as «ничего не разобрал» -- the opposite of what was typed.
            lines[-1] += " — был, не сдал ничего"
        else:
            lines[-1] += " — задач не указано"

        if row.get("student_id") is None:
            picks = [
                button(
                    "%s?" % _name_of(catalogue, candidate).split(" ")[0],
                    TextPick(row=index, student_id=candidate).pack(),
                )
                for candidate in row.get("alternatives", [])
            ]
            if picks:
                keyboard.extend(rows_of(picks, COLUMNS))

    pairs = checked_cells(stored)
    present = present_students(stored)
    lines.append("")
    lines.append(
        "В журнал пока не записано ничего. Отметок к записи: %d%s%s"
        % (
            len(pairs),
            "; явок: %d" % len(present) if present else "",
            "; строк без ученика: %d" % unresolved if unresolved else "",
        )
    )

    keyboard.append(
        [
            button("Записать (%d)" % len(pairs), TextConfirm().pack()),
            button("Отмена", TextCancel().pack()),
        ]
    )
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=keyboard)


async def _redraw(message: Message, text: str, markup: InlineKeyboardMarkup) -> None:
    """Redraw the one message the table lives in.

    ``message is not modified`` is matched BY SUBSTRING and swallowed; every other
    ``TelegramBadRequest`` is re-raised, because a deleted message, an over-long payload
    and an expired query all arrive as that one exception type.  The substring is imported
    from the grid router rather than typed again: one home, one truth.
    """
    try:
        await message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as error:
        if NOT_MODIFIED not in str(error).lower():
            raise


def _editable(query: CallbackQuery) -> Optional[Message]:
    message = query.message
    return message if isinstance(message, Message) else None


def _teacher_id(identity) -> Optional[int]:
    """Which teacher goes into the journal row.  None for the owner, who has no binding."""
    teacher = getattr(identity, "teacher", None)
    return teacher.teacher_id if teacher is not None else None


# =============================================================================
#  THE ROUTER
# =============================================================================

async def _is_a_record(message: Message, state: FSMContext) -> bool:
    """The filter, and it is the reason this screen does not swallow the conversation.

    TWO conditions, and both are refusals rather than claims:

      * no FSM dialogue is open -- registration, and later the attendance question and the
        rename, own the teacher's typing while they are waiting for it.  Those handlers
        stand above this router and would win anyway; this is the belt beside that brace,
        so that a dialogue added LATER is safe without anyone remembering to reorder;
      * the message actually looks like a record of a lesson -- a name and then labels or a
        прочерк.  «спасибо» is not a record, and answering it with a confirmation table is
        how a bot stops being usable for anything else.
    """
    if await state.get_state() is not None:
        return False
    return tekst.looks_like_a_record(message.text or "")


def build_router() -> Router:
    """A fresh router per dispatcher, for the reason P4 wrote down: a module-level
    ``Router`` remembers the dispatcher it was attached to and refuses a second one."""
    router = Router(name="text_input")
    router.message.middleware(require_role(*MARKING_ROLES))
    router.callback_query.middleware(require_role(*MARKING_ROLES))
    router.message.register(on_text, F.text, ~F.text.startswith("/"), _is_a_record)
    router.callback_query.register(toggle_cell, TextCell.filter())
    router.callback_query.register(pick_student, TextPick.filter())
    router.callback_query.register(confirm, TextConfirm.filter())
    router.callback_query.register(cancel, TextCancel.filter())
    return router


def text_dependencies(catalogue=None, sessions=None) -> dict:
    """The whole of the wiring ``bot/app.py`` would add, in one place.

    ``sessions`` is P6's ``SessionsService`` and is OPTIONAL: it is not in
    ``workflow_data`` today either, and a прочерк that cannot be written must be reported
    to the teacher rather than dropped.  When it is absent the marks still go through and
    the receipt says the явка did not.
    """
    return {"catalogue": catalogue, "sessions": sessions}


# =============================================================================
#  HANDLERS
# =============================================================================

async def on_text(message: Message, state: FSMContext, catalogue) -> None:
    """A typed record in, a confirmation table out.  Nothing else happens on this path."""
    draft = tekst.build_draft(
        message.text or "",
        students=[s for s in catalogue.students() if s.status != "left"],
        catalogue=catalogue,
    )
    if not draft.rows:  # pragma: no cover -- the filter guarantees at least one block
        return

    stored = draft_to_state(draft)
    await state.update_data(**{DRAFT_SLOT: stored})
    text, markup = render(stored, catalogue)
    await message.answer(text, reply_markup=markup)


async def _stored_draft(state: FSMContext) -> Optional[dict]:
    data = await state.get_data()
    return data.get(DRAFT_SLOT)


async def _refuse_as_stale(query: CallbackQuery) -> None:
    await query.answer("Этот разбор устарел — пришлите запись заново.", show_alert=True)


async def toggle_cell(
    query: CallbackQuery, callback_data: TextCell, state: FSMContext, catalogue
) -> None:
    """One tap on one cell.  Toggles a tick and writes nothing."""
    stored = await _stored_draft(state)
    if stored is None:
        await _refuse_as_stale(query)
        return
    rows = stored.get("rows", [])
    if not (0 <= callback_data.row < len(rows)):
        await _refuse_as_stale(query)
        return
    cells = rows[callback_data.row].get("cells", [])
    if not (0 <= callback_data.cell < len(cells)):
        await _refuse_as_stale(query)
        return

    cell = cells[callback_data.cell]
    if cell.get("problem_id") is None:
        # A label nobody could match is shown so that it is not lost, and it stays
        # untickable: there is no cell in the journal for it to reach.
        await query.answer("«%s» — такой задачи нет на листках." % cell.get("label"))
        return

    cell["checked"] = not cell.get("checked")
    await state.update_data(**{DRAFT_SLOT: stored})
    # The toast BEFORE the redraw, always: the redraw is an API round-trip and the query
    # expires in fifteen seconds; at 800 ms a person cannot tell whether the tap counted.
    await query.answer(
        "%s %s" % ("✓" if cell["checked"] else "снял",
                   cell.get("printed_label") or cell.get("label"))
    )
    message = _editable(query)
    if message is not None:
        text, markup = render(stored, catalogue)
        await _redraw(message, text, markup)


async def pick_student(
    query: CallbackQuery, callback_data: TextPick, state: FSMContext, catalogue
) -> None:
    """«Кто это?» answered by a tap.  The row becomes resolved; still nothing is written."""
    stored = await _stored_draft(state)
    if stored is None:
        await _refuse_as_stale(query)
        return
    rows = stored.get("rows", [])
    if not (0 <= callback_data.row < len(rows)):
        await _refuse_as_stale(query)
        return
    if not ids_are_storable(callback_data.student_id):
        await _refuse_as_stale(query)
        return

    row = rows[callback_data.row]
    # A forged id buys nothing: only a candidate this row actually offered is accepted.
    # The alternatives were computed server-side when the table was drawn, so this checks
    # the payload against our own answer rather than against its claim about itself.
    if callback_data.student_id not in row.get("alternatives", []):
        await _refuse_as_stale(query)
        return

    row["student_id"] = callback_data.student_id
    row["verdict"] = Verdict.CERTAIN.value
    row["reason"] = "выбрано преподавателем"
    await state.update_data(**{DRAFT_SLOT: stored})
    await query.answer(_name_of(catalogue, callback_data.student_id))
    message = _editable(query)
    if message is not None:
        text, markup = render(stored, catalogue)
        await _redraw(message, text, markup)


async def confirm(
    query: CallbackQuery,
    state: FSMContext,
    catalogue,
    marking,
    identity,
    sessions=None,
) -> None:
    """«Записать» -- the ONE place on this path where anything is stored.

    Marks go through ``MarkingService.set_state`` with the target state, exactly as a tap
    on the grid does.  The idempotency key is SHA-256 OF THE TYPED MESSAGE plus the cell it
    is about, so a teacher who taps send twice because the network stalled produces the
    same digest, the same cells and therefore the same keys, and the journal answers the
    second confirmation out of itself instead of writing a second event.

    Явки go through P6's ``SessionsService`` and NEVER through the mark path: «пришёл и не
    сдал ничего» is a fact about attendance, and writing it as a mark would destroy the one
    distinction it exists to make.
    """
    stored = await _stored_draft(state)
    if stored is None:
        await _refuse_as_stale(query)
        return

    written = repeated = failed = 0
    for student_id, problem_id in checked_cells(stored):
        try:
            outcome = marking.set_state(
                student_id,
                problem_id,
                CellState.SOLVED,
                source=tekst.SOURCE,
                teacher_id=_teacher_id(identity),
                note=tekst.NOTE,
                idempotency_key="t:%s:%d:%d"
                % (stored.get("sha256", "")[:16], student_id, problem_id),
            )
        except MarkingError:  # pragma: no cover -- SOLVED never reverses
            failed += 1
            continue
        if outcome.written:
            written += 1
        else:
            repeated += 1

    attended, attendance_note = _write_attendance(sessions, present_students(stored))

    await state.update_data(**{DRAFT_SLOT: None})
    await query.answer("Записано: %d" % written)

    message = _editable(query)
    if message is None:
        return
    receipt = [
        "✍️ Запись принята.",
        "Отметок записано: %d%s%s"
        % (
            written,
            "; уже стояло: %d" % repeated if repeated else "",
            "; не записано: %d" % failed if failed else "",
        ),
    ]
    if attended or attendance_note:
        receipt.append(
            "Явок отмечено: %d%s" % (attended, "; %s" % attendance_note if attendance_note else "")
        )
    await _redraw(message, "\n".join(receipt), InlineKeyboardMarkup(inline_keyboard=[]))


def _write_attendance(sessions, student_ids) -> tuple:
    """``(how many were marked present, what to tell the teacher)``.

    A прочерк that cannot be written is SAID OUT LOUD rather than dropped.  P6's service is
    not in ``workflow_data`` today and there may be no lesson created for today, and in
    either case the teacher has typed a fact the bot did not keep -- which they can only
    act on if they are told.
    """
    if not student_ids:
        return 0, ""
    if sessions is None:
        return 0, "явки не записаны: занятия в этой сборке не подключены"

    today = datetime.now(ZoneInfo(config.TZ_DISPLAY)).date()
    lesson = sessions.lesson_on(today)
    if lesson is None:
        return 0, "явки не записаны: на сегодня занятие не заведено"

    marked = 0
    for student_id in student_ids:
        sessions.mark_attendance(lesson.id, student_id, tekst.PRESENT)
        marked += 1
    return marked, ""


async def cancel(query: CallbackQuery, state: FSMContext) -> None:
    """«Отмена».  Nothing was written, so there is nothing to undo -- and the message says
    exactly that, because «отменено» over an unwritten draft reads as a rollback."""
    await state.update_data(**{DRAFT_SLOT: None})
    await query.answer("Разбор отброшен — в журнал ничего не попало.")
    message = _editable(query)
    if message is not None:
        await _redraw(
            message,
            "Разбор отброшен. В журнал ничего не записано.",
            InlineKeyboardMarkup(inline_keyboard=[]),
        )
