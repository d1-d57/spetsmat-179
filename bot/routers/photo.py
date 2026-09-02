"""Фото бланка -> черновик -> таблица подтверждения -> журнал.  Прямой записи нет никогда.

THE ONE RULE THIS FILE EXISTS TO CARRY (§8, and the owner's fourth finalised decision):
**a mark is NEVER written to the journal without a human confirming it.**  Everything the
model produces is a DRAFT living in this teacher's FSM state; the journal hears nothing
until «Записать» is tapped.  There is no branch in this module that writes on any other
path, and the test that matters most asserts exactly that: after a photo, after a toggle,
after a re-delivery, the journal is still empty.

WHY THE WHOLE TABLE, AND NOT THE DOUBTFUL ROWS.  Showing only what the pipeline is unsure
about trains the teacher to trust the rest, and the rest is where a confident-and-wrong
row hides.  The whole parsed table is drawn, every cell is a button, and a tap toggles it.

THE THIRD EQUAL WAY IN.  Buttons (P4) and this screen and, later, voice (P8) and quick
text (P15) all end at the same place: ``MarkingService.set_state``.  This module does not
own a second write path, it owns a second way to FILL one.  ``source="фото"`` is the only
difference the journal sees.

IDEMPOTENCY, AND WHY IT IS THE HASH OF THE BYTES (§8).  The key of every cell this screen
writes is ``foto:<sha256 of the downloaded bytes>:<student>:<problem>``.  The journal has
a unique index on ``idempotency_key``, so the second confirmation of the same photograph
writes nothing and reports «уже записано» -- which is the «zero rows affected means
already recorded, exit» of the brief, obtained without a second table.  NOT
``file_unique_id``: Telegram words that guarantee «is supposed to be the same», and the
failure it permits is a sheet recorded twice into an append-only journal.  A hash of the
bytes survives a process restart and a re-delivered update alike, because it depends on
nothing this process remembers.

WHY THE PAYLOADS ARE DEFINED HERE AND NOT IN ``bot/callbacks.py``.  That file is P4's and
outside this position's zone; two writers in one file is the single thing a wave cannot
do.  The two LAWS it states are obeyed all the same -- a payload carries the TARGET state
and only numbers -- and ``_button`` enforces the 64-byte limit at the moment a button is
built, exactly as ``bot/keyboards/grid.button`` does.  Moving these payload classes into
``bot/callbacks.py`` is a one-commit tidy for whoever owns that file next.
"""

from __future__ import annotations

import io
from typing import Optional

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import config
from bot.callbacks import ID_MAX, ID_MIN, payload_fits
from bot.middleware import require_role
from bot.routers.marking import MARKING_ROLES, NOT_MODIFIED
from core.models import CellState
from core.services.raspoznavanie import (
    UNKNOWN,
    IntakeRefused,
    choose_photo_size,
    code_for_student,
    prepare,
    rows_from_answer,
)
from infra.llm import LlmError, ModelRefused, SpendLimitReached

#: Where a mark written by this screen came from.  One of ``config.MARK_SOURCES``.
SOURCE = "фото"

#: Telegram refuses a keyboard over a hundred buttons.  Cells past this cap are NOT drawn
#: and are NOT written: the rule of this screen is that nothing reaches the journal that a
#: human has not looked at, and a cell nobody could see is a cell nobody confirmed.
#:
#: The cap is applied in ``build_draft`` and not in the keyboard, which is the correction
#: the §3 verifier's fourth finding forced.  Deciding it at render time meant «Записать 94»
#: on a keyboard showing 80 -- fourteen marks written that the teacher could not inspect or
#: untick -- and an overflow button that carried ``op=0`` and silently discarded the whole
#: draft when tapped.
MAX_CELL_BUTTONS = 90

#: How a cell of the draft is drawn.  A tick or an empty box, and the task label.
CELL_MARK = {True: "✅", False: "☐"}

#: How a row is drawn, by what the confidence said about it (§6).
ROW_MARK = {"confident": "", "doubtful": "⚠️ ", UNKNOWN: "❓ "}


# ------------------------------------------------------------------------- payloads

class FotoCell(CallbackData, prefix="pc"):
    """Toggle one cell of the draft: ``pc:2:5``.

    Indices into the draft, not database ids: the draft is what is on the screen, the
    indices are stable for as long as that message is, and two small integers keep the
    payload far inside the 64-byte limit even beside a long prefix.
    """

    row: int
    cell: int


class FotoPick(CallbackData, prefix="pp"):
    """Resolve an ``UNKNOWN`` row to one of its candidates: ``pp:2:56``.

    The row the model would not commit to gets one button per candidate.  The payload
    carries the candidate's id -- a number, never a name.
    """

    row: int
    student_id: int


class FotoNote(CallbackData, prefix="pn"):
    """The overflow line: «… ещё N клеток не поместилось».

    A REAL payload with a REAL handler that changes nothing.  It used to carry
    ``FotoFinish(op=0)``, so a teacher tapping what reads as a caption cancelled the whole
    draft; and an unhandled payload would fall through to P4's catch-all and be answered
    «экран устарел», which would be a lie about the screen they are looking at.
    """


class FotoFinish(CallbackData, prefix="pf"):
    """``pf:1`` записать · ``pf:0`` отменить.

    The TARGET, as P4's first law requires: ``1`` means «this draft must end up in the
    journal», not «do whatever the opposite of the last thing is».
    """

    op: int


OP_CANCEL, OP_WRITE = 0, 1


def _button(text: str, payload: str) -> InlineKeyboardButton:
    """The 64-byte law, carried in the BUILD and not only in a test.

    Telegram rejects the whole message when one payload is too long and names neither the
    button nor the row; refusing here names both, before anything has been sent.
    """
    if not payload_fits(payload):
        raise ValueError("callback_data %r is over Telegram's limit, on %r" % (payload, text))
    return InlineKeyboardButton(text=text, callback_data=payload)


def _storable(*values: int) -> bool:
    """Can these ids reach SQLite at all?  A wider one raises from inside a query, i.e.
    after the handler started and before it answered -- a spinner that never stops."""
    return all(ID_MIN <= value <= ID_MAX for value in values)


# --------------------------------------------------------------------------- the draft

def build_draft(answer, catalogue, sheet, *, digest: str) -> dict:
    """The model's answer plus the catalogue, as the thing the screen draws and edits.

    A plain dict rather than a dataclass because it goes into the FSM store, which
    serialises; and the ONE piece of state that must not be reconstructible from the
    screen -- the hash of the photograph -- is carried in it rather than re-derived.

    TWO THINGS ARE DECIDED HERE AND NOT LATER, both because deciding them later meant
    writing something nobody saw:

      * the button CAP.  A cell past ``MAX_CELL_BUTTONS`` is marked ``shown: False`` and
        unticked, so ``checked_cells`` cannot return it and «Записать» cannot write it;
      * a label the model returned that is NOT on this sheet is collected into
        ``unknown`` instead of being dropped.  It is the loudest available evidence that
        the paper is a different sheet from the one the bot assumed.
    """
    problems = {problem.label: problem for problem in catalogue.problems_of_sheet(sheet.id)}
    known = {student.id for student in catalogue.students()}

    rows, drawn, unknown = [], 0, []
    for row in rows_from_answer(answer, known):
        cells = []
        for label in row.solved:
            if label not in problems:
                unknown.append(label)
                continue
            shown = drawn < MAX_CELL_BUTTONS
            drawn += 1 if shown else 0
            cells.append(
                {
                    "problem_id": problems[label].id,
                    "label": label,
                    # Not shown means not ticked means not writable.  One rule, one place.
                    "checked": shown,
                    "shown": shown,
                }
            )
        rows.append(
            {
                "student_id": row.student_id,
                "code": row.code,
                "state": row.state,
                "score": round(row.score, 2),
                "alternatives": list(row.alternatives),
                "cells": cells,
            }
        )
    unknown.extend(label for label in getattr(answer, "unknown_labels", ()) or ())
    return {
        "sha256": digest,
        "sheet_id": sheet.id,
        "rows": rows,
        "unknown_labels": list(dict.fromkeys(unknown)),
        "hidden": sum(1 for row in rows for cell in row["cells"] if not cell["shown"]),
    }


def checked_cells(draft: dict):
    """``[(student_id, problem_id), ...]`` — exactly what «Записать» would write.

    A row with no student resolved contributes NOTHING, however many of its cells are
    ticked: a mark has to land on a child, and «probably Petya» is not a child.
    """
    pairs = []
    for row in draft.get("rows", []):
        student_id = row.get("student_id")
        if student_id is None:
            continue
        for cell in row.get("cells", []):
            # ``shown`` is belt AND braces beside ``checked``: a cell the teacher never
            # saw must not become a mark even if something else ticks it.
            if cell.get("checked") and cell.get("shown", True):
                pairs.append((student_id, cell["problem_id"]))
    return pairs


# ------------------------------------------------------------------------- rendering

def _name_of(catalogue, row) -> str:
    """How the row is labelled ON THE SCREEN, which is this machine and nowhere else.

    The child's name is drawn here and travels no further: it was never in the image, is
    not in any payload, and does not reach the model.  §4 is about what leaves the
    server, not about what a teacher may read on their own phone.
    """
    student_id = row.get("student_id")
    if student_id is None:
        return "строка %s" % (row.get("code") or "?")
    student = catalogue.student(student_id)
    if student is None:
        return "ученик %d" % student_id
    return ("%s %s." % (student.surname, (student.name or "")[:1])).strip()


def draft_text(draft: dict, catalogue) -> str:
    sheet = catalogue.sheet(draft["sheet_id"])
    lines = [
        "Фото · листок %s · строк %d · отметок %d"
        % (sheet.number if sheet else "?", len(draft["rows"]), len(checked_cells(draft))),
        "Проверьте и нажмите «Записать» — до этого в журнал ничего не идёт.",
    ]
    if draft.get("hidden"):
        lines.append(
            "⚠️ %d клеток не поместилось на экран — они НЕ будут записаны. "
            "Отметьте их кнопками: /setka." % draft["hidden"]
        )
    if draft.get("unknown_labels"):
        lines.append(
            "⚠️ на листке %s нет задач %s — возможно, это фото другого листка."
            % (sheet.number if sheet else "?", ", ".join(draft["unknown_labels"][:8]))
        )
    for row in draft["rows"]:
        marks = ", ".join(cell["label"] for cell in row["cells"] if cell["checked"])
        lines.append(
            "%s%s — %s" % (ROW_MARK.get(row["state"], ""), _name_of(catalogue, row),
                           marks or "ничего")
        )
        if row["state"] == "doubtful":
            lines.append("    код сошёлся на %.0f%% — проверьте строку" % (row["score"] * 100))
        if row["state"] == UNKNOWN:
            lines.append("    кто это? выберите ниже" if row["alternatives"]
                         else "    строку не удалось опознать — отметки не запишутся")
    return "\n".join(lines)


def draft_keyboard(draft: dict, catalogue) -> InlineKeyboardMarkup:
    """The whole parsed table, one button per cell, plus the two closing buttons."""
    rows = []
    for row_index, row in enumerate(draft["rows"]):
        if row["state"] == UNKNOWN and row["alternatives"]:
            rows.append([
                _button(
                    "%s?" % _name_of(catalogue, {"student_id": candidate}),
                    FotoPick(row=row_index, student_id=candidate).pack(),
                )
                for candidate in row["alternatives"][:config.GRID_COLUMNS]
            ])
        line = []
        for cell_index, cell in enumerate(row["cells"]):
            if not cell.get("shown", True):
                continue
            line.append(
                _button(
                    "%s%s" % (CELL_MARK[bool(cell["checked"])], cell["label"]),
                    FotoCell(row=row_index, cell=cell_index).pack(),
                )
            )
            if len(line) == config.GRID_COLUMNS:
                rows.append(line)
                line = []
        if line:
            rows.append(line)

    if draft.get("hidden"):
        # Named out loud, and INERT: a silent cap reads as «that is all there was», and a
        # cancel hiding behind a caption throws away the draft the teacher just checked.
        rows.append([_button("… ещё %d клеток не поместилось" % draft["hidden"],
                             FotoNote().pack())])

    rows.append([
        _button("Записать %d" % len(checked_cells(draft)), FotoFinish(op=OP_WRITE).pack()),
        _button("Отменить", FotoFinish(op=OP_CANCEL).pack()),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _redraw(message: Message, text: str, markup: InlineKeyboardMarkup) -> None:
    """P4's rule, and for P4's reason: «message is not modified» is matched BY SUBSTRING.

    Swallowing ``TelegramBadRequest`` whole would hide a deleted message, an over-long
    payload and an expired query -- every API failure this screen can have.
    """
    try:
        await message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as error:
        if NOT_MODIFIED not in str(error).lower():
            raise


def _editable(query: CallbackQuery) -> Optional[Message]:
    message = query.message
    return message if isinstance(message, Message) else None


# -------------------------------------------------------------------------- handlers

async def receive_photo(message: Message, **data) -> None:
    """A photograph of a form.  Ends at a DRAFT on the screen, never at the journal."""
    catalogue = data["catalogue"]
    state: FSMContext = data["state"]
    vision = data.get("vision")

    sheet = _current_sheet(catalogue)
    if sheet is None:
        await message.answer("В каталоге ещё нет листков — бланк не к чему привязать.")
        return
    if vision is None:
        await message.answer(
            "Разбор фото не настроен: нет ключа модели. Отметьте кнопками — /setka."
        )
        return

    try:
        raw = await _download(message, data["bot"])
    except IntakeRefused as refusal:
        await message.answer(str(refusal))
        return

    try:
        prepared = prepare(raw)
    except IntakeRefused as refusal:
        await message.answer(str(refusal))
        return

    students = [s for s in catalogue.students() if s.status != "left"]
    codes = [code_for_student(student.id) for student in students]
    labels = [problem.label for problem in catalogue.problems_of_sheet(sheet.id)]
    sheet_numbers = [existing.number for existing in catalogue.sheets()]

    waiting = await message.answer("Разбираю бланк…")
    try:
        answer = vision.read_sheet(prepared.jpeg, codes, labels, sheet_numbers)
    except SpendLimitReached:
        await _redraw_message(waiting, "Кончился лимит модели. Отметьте кнопками — /setka.")
        return
    except ModelRefused:
        await _redraw_message(
            waiting, "Модель не стала разбирать этот снимок. Переснимите или /setka."
        )
        return
    except LlmError as error:
        await _redraw_message(waiting, "Не получилось разобрать фото: %s" % error)
        return

    # 🔴 WHICH SHEET IS ON THE PAPER, before a single mark is drafted.
    #
    # This screen used to assume the newest sheet unconditionally.  The §3 verifier
    # photographed листок 12 while 13 was current: nine marks landed on листок 13's
    # problem ids -- adjacent sheets share between two and eleven labels -- and
    # thirty-five labels were dropped without a word.  ``tools/blank.py`` prints «Листок N»
    # at the top of every form, and nothing was reading it back.
    #
    # Refusing is the whole fix, and it is deliberately not «switch to the sheet the model
    # read»: the closed list of task labels sent with the request was built for the CURRENT
    # sheet, so an answer about another one was produced against the wrong vocabulary and
    # is not trustworthy at any confidence.  Photographing an older sheet is named in
    # ## ВОПРОСЫ as the next заход's work.
    read_number = (getattr(answer, "sheet_number", "") or "").strip()
    if read_number and read_number != sheet.number:
        await _redraw_message(
            waiting,
            "На бланке напечатан листок %s, а сейчас идёт листок %s. "
            "Фото пока разбирается только для текущего листка — отметьте кнопками /setka."
            % (read_number, sheet.number),
        )
        return

    draft = build_draft(answer, catalogue, sheet, digest=prepared.sha256)
    if not draft["rows"]:
        await _redraw_message(waiting, "На бланке не нашлось ни одной отметки.")
        return

    await state.update_data(photo_draft=draft)
    await _redraw(waiting, draft_text(draft, catalogue), draft_keyboard(draft, catalogue))


async def toggle_cell(query: CallbackQuery, callback_data: FotoCell, **data) -> None:
    """One tap on one cell of the DRAFT.  Nothing is written; nothing is even attempted."""
    state: FSMContext = data["state"]
    catalogue = data["catalogue"]
    draft = (await state.get_data()).get("photo_draft")
    if draft is None:
        await query.answer("Черновик устарел — пришлите фото заново.", show_alert=True)
        return
    row = _row_at(draft, callback_data.row)
    if row is None or not 0 <= callback_data.cell < len(row["cells"]):
        await query.answer("Экран устарел — пришлите фото заново.", show_alert=True)
        return

    cell = row["cells"][callback_data.cell]
    cell["checked"] = not cell["checked"]
    await state.update_data(photo_draft=draft)

    # P4's beat order: the toast BEFORE the redraw, always.  The redraw is a round trip,
    # the query expires in fifteen seconds, and at 800 ms a person taps again.
    await query.answer("%s %s" % ("отмечено" if cell["checked"] else "снято", cell["label"]))
    message = _editable(query)
    if message is not None:
        await _redraw(message, draft_text(draft, catalogue), draft_keyboard(draft, catalogue))


async def pick_student(query: CallbackQuery, callback_data: FotoPick, **data) -> None:
    """«Кто это?» on a row the model refused to guess about."""
    state: FSMContext = data["state"]
    catalogue = data["catalogue"]
    draft = (await state.get_data()).get("photo_draft")
    row = _row_at(draft, callback_data.row) if draft else None
    if row is None or not _storable(callback_data.student_id):
        await query.answer("Экран устарел — пришлите фото заново.", show_alert=True)
        return
    if callback_data.student_id not in row.get("alternatives", []):
        await query.answer("Этого варианта здесь не было.", show_alert=True)
        return

    row["student_id"] = callback_data.student_id
    row["state"] = "confident"
    row["alternatives"] = []
    await state.update_data(photo_draft=draft)

    await query.answer(_name_of(catalogue, row))
    message = _editable(query)
    if message is not None:
        await _redraw(message, draft_text(draft, catalogue), draft_keyboard(draft, catalogue))


async def note(query: CallbackQuery, **data) -> None:
    """A tap on the overflow line.  Dismiss the spinner, change nothing, explain."""
    await query.answer(
        "Эти клетки не поместились на экран и не будут записаны — отметьте их через /setka.",
        show_alert=True,
    )


async def finish(query: CallbackQuery, callback_data: FotoFinish, **data) -> None:
    """«Записать» or «Отменить».  The ONLY place in this module that touches the journal.

    The write goes through P4's ``MarkingService`` -- there is not a second write path in
    this project and this screen does not add one.  Every cell carries an idempotency key
    derived from the hash of the PHOTOGRAPH, so confirming the same picture twice writes
    nothing the second time and says so.
    """
    state: FSMContext = data["state"]
    catalogue = data["catalogue"]
    marking = data["marking"]
    identity = data.get("identity")

    draft = (await state.get_data()).get("photo_draft")
    if draft is None:
        await query.answer("Черновик устарел — пришлите фото заново.", show_alert=True)
        return
    if callback_data.op == OP_CANCEL:
        await state.update_data(photo_draft=None)
        await query.answer("Черновик отменён — в журнал ничего не ушло.")
        message = _editable(query)
        if message is not None:
            await _redraw(message, "Черновик отменён. В журнал ничего не записано.",
                          InlineKeyboardMarkup(inline_keyboard=[]))
        return
    if callback_data.op != OP_WRITE:
        await query.answer("Экран устарел — пришлите фото заново.", show_alert=True)
        return

    written, already, spent = 0, 0, 0
    for student_id, problem_id in checked_cells(draft):
        outcome = marking.set_state(
            student_id,
            problem_id,
            CellState.SOLVED,
            source=SOURCE,
            teacher_id=_teacher_id(identity),
            # THE KEY OF THE WHOLE FLOW.  The hash of the downloaded BYTES, plus the cell
            # it lands on: the second confirmation of the same photograph finds every key
            # already in the journal and writes nothing.
            idempotency_key="foto:%s:%d:%d" % (draft["sha256"], student_id, problem_id),
        )
        if outcome.written:
            written += 1
        elif outcome.state is CellState.SOLVED:
            already += 1
        else:
            # WRITTEN=FALSE DOES NOT MEAN «уже стоит».  The key was spent by an earlier
            # confirmation of THIS photograph and the cell has since been struck or
            # retracted, so the answer comes back from the journal and the cell stays
            # empty.  Reporting that as «уже было» tells the teacher a mark is standing
            # when none is -- found by the §3 verifier, sixth finding.
            spent += 1

    await state.update_data(photo_draft=None)
    summary = "Записано отметок: %d." % written
    if already:
        summary += " Уже стояло: %d." % already
    if spent:
        summary += (
            " Снято раньше и этим фото не вернуть: %d — отметьте кнопками /setka." % spent
        )
    await query.answer(summary)
    message = _editable(query)
    if message is not None:
        await _redraw(message, summary, InlineKeyboardMarkup(inline_keyboard=[]))


# --------------------------------------------------------------------------- helpers

def _row_at(draft, index):
    rows = (draft or {}).get("rows") or []
    return rows[index] if 0 <= index < len(rows) else None


def _current_sheet(catalogue):
    sheets = catalogue.sheets()
    return max(sheets, key=lambda sheet: sheet.ord) if sheets else None


def _teacher_id(identity):
    teacher = getattr(identity, "teacher", None)
    return teacher.teacher_id if teacher is not None else None


async def _download(message: Message, bot) -> bytes:
    """The bytes, and the 20 MB ceiling, for both the photo path and the document path.

    A photo arrives as an ARRAY of sizes; the largest one ``getFile`` can actually fetch
    is taken.  A document is asked for only when the sheet was shot from far away -- the
    gain is not resolution (the pipeline downscales anyway) but the absence of a second
    JPEG generation.
    """
    from core.services.raspoznavanie import refuse_if_too_large

    if message.photo:
        chosen = choose_photo_size(message.photo)
        if chosen is None:
            raise IntakeRefused("снимок слишком большой — Telegram отдаёт боту до 20 МБ")
        file_id = chosen.file_id
    elif message.document is not None:
        refuse_if_too_large(message.document.file_size or 0)
        file_id = message.document.file_id
    else:  # pragma: no cover -- the filter admits nothing else
        raise IntakeRefused("это не изображение")

    buffer = io.BytesIO()
    await bot.download(file_id, destination=buffer)
    return buffer.getvalue()


async def _redraw_message(message: Message, text: str) -> None:
    await _redraw(message, text, InlineKeyboardMarkup(inline_keyboard=[]))


# --------------------------------------------------------------------------- factory

def build_routers() -> tuple:
    """A fresh router per dispatcher, exactly as ``marking.build_routers`` hands one out.

    A module-level ``router = Router()`` remembers the dispatcher it was attached to and
    refuses to be attached twice, which is why P3's fixture has to null
    ``module.router._parent_router`` before every build.  A factory costs one line at the
    call site and removes the shared global.

    Returns a 1-tuple so that the call site reads the same as P4's and so that a second
    router (a catch-all, say) can be added later without changing every caller.
    """
    screen = Router(name="photo")
    screen.message.middleware(require_role(*MARKING_ROLES))
    screen.callback_query.middleware(require_role(*MARKING_ROLES))
    screen.message.register(receive_photo, F.photo)
    screen.message.register(receive_photo, F.document.mime_type.startswith("image/"))
    screen.callback_query.register(toggle_cell, FotoCell.filter())
    screen.callback_query.register(pick_student, FotoPick.filter())
    screen.callback_query.register(note, FotoNote.filter())
    screen.callback_query.register(finish, FotoFinish.filter())
    return (screen,)
