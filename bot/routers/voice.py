"""The third way in: a teacher says «Петров три пять семь бэ» and taps once.

Buttons (P4), photo (P7) and voice are EQUAL ways to reach the same journal — that is the
first thing the interview finalised — and «equal» here means literal: this screen owns no
marking logic of its own.  It builds a draft, shows it, lets a human correct it, and then
writes through ``MarkingService`` exactly as a tap on the grid does, with ``source`` set
to «голос» and an idempotency key of its own shape.  If this file were deleted the
journal would lose an input, not a capability.

THERE IS NEVER A DIRECT WRITE.  Nothing recognised reaches the journal until a person has
looked at the whole table and pressed «Записать».  This is the third finalised point of
the interview and it has no exception: not for a confident model, not for a single-row
dictation, not for a re-send of a recording the bot has already seen.

WHAT IS DELIBERATELY NOT IN THIS FILE
-------------------------------------
* **Numeral normalisation and matching.**  ``core/services/golos.py``.  A router that
  parsed Russian numerals would be a router nobody could test without a Telegram update.
* **The schema call.**  P7's, imported through ``golos.load_schema_extractor`` and absent
  on this branch; a forked copy is two homes for one truth.
* **Recognition.**  ``infra/asr.py``, behind a Protocol, injected — so every test below
  drives the real parsing and the real writing with a scripted engine.

⚠ **THE ROUTER IS BUILT HERE AND INCLUDED NOWHERE.**  ``bot/app.py`` is outside this
position's zone, so the ``include_router`` line that would put this screen in front of a
teacher does not exist yet.  ``voice_dependencies()`` below is the whole of the wiring,
written so that adding it is three lines rather than a reading exercise; the gap is
reported, not silently closed by an out-of-zone edit.  It MUST be included AFTER the grid
router and BEFORE the stale catch-all — the catch-all claims every callback nobody above
it matched, so a voice screen included after it would never receive a single tap.
"""

from __future__ import annotations

import asyncio
import hashlib
from io import BytesIO
from typing import Optional

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

import config
from bot.callbacks import ids_are_storable
from bot.keyboards.grid import button, rows_of
from bot.middleware import require_role
from bot.routers.marking import MARKING_ROLES, NOT_MODIFIED
from core.models import CellState
from core.services.golos import (
    Verdict,
    build_draft,
    build_user_dictionary,
    load_schema_extractor,
    normalise_label,
)
from core.services.marking import MarkingError
from infra.asr import (
    TELEGRAM_GETFILE_MAX_BYTES,
    TranscriptionUnavailable,
    build_transcriber,
)

#: Where a mark written by this screen came from.  One of ``config.MARK_SOURCES``, and
#: the reason a mark can be traced back to the way it was made a year later.
SOURCE = "голос"

#: The key under which one draft waits for its confirmation, in THIS teacher's FSM store.
#: Two teachers dictating side by side must not see each other's table, and the store is
#: already per-chat, so nothing here is keyed by a teacher id.
DRAFT_SLOT = "voice_draft"

#: How many toggle buttons stand in one keyboard row.  The same four as the grid, and for
#: the same measured reason: at five they fall below the comfortable thumb target.
COLUMNS = config.GRID_COLUMNS


# =============================================================================
#  PAYLOADS
# =============================================================================
#
# Numbers only, and nothing a human typed — the two laws of ``bot/callbacks.py``, obeyed
# here rather than restated: a surname in a payload is a surname leaving the server, and
# the separator ``:`` occurs inside real problem labels (`10а:)`).
#
# ⚠ These classes belong in ``bot/callbacks.py`` beside every other payload of this bot.
# That file is outside this position's zone, so they live here and the move is named in
# ``## ВОПРОСЫ``.  The prefixes are checked against the existing five by a test, because
# a collision would silently route one screen's taps into another's handler.

class VoiceCell(CallbackData, prefix="vc"):
    """Toggle one cell of the confirmation table: ``vc:0:2`` — row 0, cell 2.

    Positions in the table, NOT ids: the table is what the teacher is looking at, it lives
    in their own FSM store, and an index cannot name a row of somebody else's screen.
    """

    row: int
    cell: int


class VoicePick(CallbackData, prefix="vp"):
    """Choose which child an unresolved row meant: ``vp:1:56``.

    The student id travels because the alternatives were computed server-side when the
    table was drawn, and the button has to name one of them.  A forged id buys nothing:
    the handler accepts it only if it is among the alternatives that row actually offers.
    """

    row: int
    student_id: int


class VoiceConfirm(CallbackData, prefix="vy"):
    """«Записать» — the one button that reaches the journal.  ``vy:1``.

    The field is there so the payload CONTAINS THE SEPARATOR: the stale catch-all treats
    a separator-free token as a decoration belonging to whatever screen is on display and
    declines to redraw over it, and a confirm button must never be mistaken for one.
    """

    ok: int = 1


class VoiceCancel(CallbackData, prefix="vn"):
    """«Отмена» — drop the draft.  Nothing was written, so nothing is undone.  ``vn:1``."""

    ok: int = 1


# =============================================================================
#  THE DRAFT, AS IT LIVES IN THE FSM STORE
# =============================================================================
#
# Plain dicts and lists, because a MemoryStorage keeps whatever it is given and a Redis
# one keeps only what serialises.  The dataclasses of ``core`` are the working shape; this
# is the stored shape, and the two conversions are in one place each.

def _draft_to_state(draft) -> dict:
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
                "cells": [
                    {
                        "label": cell.label,
                        "problem_id": cell.problem_id,
                        "printed_label": cell.printed_label,
                        "ticked": bool(cell.ticked),
                    }
                    for cell in row.cells
                ],
            }
            for row in draft.rows
        ],
    }


def _writable(stored: dict) -> list:
    """Every ``(student_id, problem_id)`` this draft would write if confirmed now."""
    pairs = []
    for row in stored.get("rows", []):
        if row.get("student_id") is None:
            continue
        for cell in row.get("cells", []):
            if cell.get("ticked") and cell.get("problem_id") is not None:
                pairs.append((row["student_id"], cell["problem_id"]))
    return pairs


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
    """What one cell says: the label the SHEET prints, with its state in front.

    The printed label rather than the spoken one, because that is what the teacher will
    look for on the paper in their hand — «7б°» and not «7б».
    """
    label = cell.get("printed_label") or cell.get("label")
    if cell.get("problem_id") is None:
        return "✗ %s" % label
    return "%s %s" % ("✓" if cell.get("ticked") else "·", label)


def render(stored: dict, catalogue) -> tuple:
    """``(text, keyboard)`` for the whole confirmation table.

    SHOWN WHOLE.  Not the doubtful rows, not the first five — a teacher who has to scroll
    or page to see what a machine heard about their class will confirm without reading,
    and the confirmation is the only thing standing between a recogniser and the journal.
    """
    lines = ["🎤 «%s»" % (stored.get("transcript") or "").strip()]
    keyboard = []
    unresolved = 0

    for index, row in enumerate(stored.get("rows", [])):
        if row.get("student_id") is None:
            unresolved += 1
            heard = row.get("surname_text") or "—"
            lines.append("%d. ❓ «%s» — кто это?" % (index + 1, heard))
        else:
            lines.append(
                "%d. %s%s"
                % (
                    index + 1,
                    _name_of(catalogue, row["student_id"]),
                    " ⚠" if row.get("verdict") == Verdict.DOUBTFUL.value else "",
                )
            )

        cells = row.get("cells", [])
        if cells:
            buttons = [
                button(_cell_text(cell), VoiceCell(row=index, cell=position).pack())
                for position, cell in enumerate(cells)
            ]
            keyboard.extend(rows_of(buttons, COLUMNS))
        else:
            lines[-1] += " — задач не расслышано"

        if row.get("student_id") is None:
            picks = [
                button(
                    "%s?" % _name_of(catalogue, candidate).split(" ")[0],
                    VoicePick(row=index, student_id=candidate).pack(),
                )
                for candidate in row.get("alternatives", [])
            ]
            if picks:
                keyboard.extend(rows_of(picks, COLUMNS))

    pairs = _writable(stored)
    lines.append("")
    lines.append(
        "В журнал пока не записано ничего. Отметок к записи: %d%s"
        % (len(pairs), "; строк без ученика: %d" % unresolved if unresolved else "")
    )

    keyboard.append(
        [
            button("Записать (%d)" % len(pairs), VoiceConfirm().pack()),
            button("Отмена", VoiceCancel().pack()),
        ]
    )
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=keyboard)


async def _redraw(message: Message, text: str, markup: InlineKeyboardMarkup) -> None:
    """Redraw the one message the table lives in.

    ``message is not modified`` is matched BY SUBSTRING and swallowed; every other
    ``TelegramBadRequest`` is re-raised, because a deleted message, an over-long payload
    and an expired query all arrive as that same exception type.  The substring itself is
    imported from the grid router rather than typed again: one home, one truth.
    """
    try:
        await message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as error:
        if NOT_MODIFIED not in str(error).lower():
            raise


def _editable(query: CallbackQuery) -> Optional[Message]:
    """The message to redraw, or None when Telegram handed us one that cannot be edited."""
    message = query.message
    return message if isinstance(message, Message) else None


# =============================================================================
#  THE SEAMS THIS SCREEN IS GIVEN
# =============================================================================

async def telegram_download(bot: Bot, file_id: str) -> bytes:
    """The voice note's bytes.  The same ``getFile`` door the photo path goes through."""
    buffer = BytesIO()
    await bot.download(file_id, destination=buffer)
    return buffer.getvalue()


def voice_dependencies(catalogue=None, *, environ=None) -> dict:
    """Everything ``bot/app.py`` has to add to ``workflow_data`` for this screen. THREE KEYS.

    Called with the catalogue, the recogniser is built carrying the user dictionary of
    this conduit — 56 surnames and the labels in view — rather than a generic model.  The
    second element of ``build_transcriber`` is returned as ``asr_note`` so that the
    process that starts the bot can LOG whether recognition is real: a fake that installed
    itself in silence answers every dictation with the same canned line and looks exactly
    like a working bot.
    """
    phrases = []
    if catalogue is not None:
        surnames = [student.surname for student in catalogue.students()]
        labels = sorted({normalise_label(problem.label) for sheet in catalogue.sheets()
                         for problem in catalogue.problems_of_sheet(sheet.id)})
        phrases = build_user_dictionary(surnames, labels)
    transcriber, note = build_transcriber(phrases=phrases, environ=environ)
    extractor, extractor_note = load_schema_extractor()
    return {
        "transcriber": transcriber,
        "download": telegram_download,
        "asr_note": "%s; схема: %s" % (note, extractor_note),
        "schema_extractor": extractor,
    }


def build_router() -> Router:
    """A fresh router per dispatcher, for the reason P4 wrote down: a module-level
    ``Router`` remembers the dispatcher it was attached to and refuses a second one."""
    router = Router(name="voice")
    router.message.middleware(require_role(*MARKING_ROLES))
    router.callback_query.middleware(require_role(*MARKING_ROLES))
    router.message.register(on_voice, F.voice)
    router.callback_query.register(toggle_cell, VoiceCell.filter())
    router.callback_query.register(pick_student, VoicePick.filter())
    router.callback_query.register(confirm, VoiceConfirm.filter())
    router.callback_query.register(cancel, VoiceCancel.filter())
    return router


# =============================================================================
#  HANDLERS
# =============================================================================

async def on_voice(
    message: Message,
    state: FSMContext,
    catalogue,
    transcriber,
    download,
    schema_extractor=None,
) -> None:
    """A voice note in, a confirmation table out.  Nothing else happens on this path."""
    voice = message.voice
    if voice is None:  # pragma: no cover -- the filter guarantees it
        return

    if (voice.file_size or 0) > TELEGRAM_GETFILE_MAX_BYTES:
        await message.answer(
            "Файл больше %d МБ — Telegram не отдаёт такие боту. Продиктуйте короче."
            % (TELEGRAM_GETFILE_MAX_BYTES // (1024 * 1024))
        )
        return

    audio = await download(message.bot, voice.file_id)
    digest = hashlib.sha256(audio).hexdigest()

    try:
        # OFF THE EVENT LOOP.  Recognition is a network round-trip of seconds; run inline
        # it would freeze every other teacher's taps for the length of one dictation.
        transcript = await asyncio.to_thread(
            transcriber.transcribe, audio, mime_type=voice.mime_type or "audio/ogg"
        )
    except TranscriptionUnavailable as refusal:
        # Said out loud, never turned into an empty draft: an empty table is
        # indistinguishable from a dictation the teacher meant to be empty.
        await message.answer("Не разобрал запись: %s\nОтметьте кнопками." % refusal)
        return

    problems = _problems_in_view(catalogue)
    model_rows = None
    channels = "только нечёткое сопоставление — схемного разбора на этой ветке нет"
    if schema_extractor is not None:  # pragma: no cover -- P7 is not on this branch
        model_rows = schema_extractor.extract(
            transcript, students=catalogue.students(), problems=problems
        )
        channels = "схемный разбор + нечёткое сопоставление"

    draft = build_draft(
        transcript,
        students=[s for s in catalogue.students() if s.status != "left"],
        problems=problems,
        model_rows=model_rows,
        audio_sha256=digest,
        channels=channels,
    )
    stored = _draft_to_state(draft)
    await state.update_data(**{DRAFT_SLOT: stored})

    text, markup = render(stored, catalogue)
    await message.answer(text, reply_markup=markup)


def _problems_in_view(catalogue) -> list:
    """The problems a dictation may name, CURRENT SHEET FIRST.

    Older sheets stay reachable — a debt handed in today was set weeks ago — but when two
    sheets print the same stripped label, the one the teacher is working on wins.  That
    ordering is the whole disambiguation rule and it lives here, once.
    """
    sheets = catalogue.sheets()
    if not sheets:
        return []
    current = max(sheets, key=lambda sheet: sheet.ord)
    ordered = [current] + [sheet for sheet in sheets if sheet.id != current.id]
    return [
        problem for sheet in ordered for problem in catalogue.problems_of_sheet(sheet.id)
    ]


async def _stored_draft(state: FSMContext) -> Optional[dict]:
    data = await state.get_data()
    return data.get(DRAFT_SLOT)


async def _refuse_as_stale(query: CallbackQuery) -> None:
    await query.answer("Эта расшифровка устарела — продиктуйте заново.", show_alert=True)


async def toggle_cell(
    query: CallbackQuery, callback_data: VoiceCell, state: FSMContext, catalogue
) -> None:
    """One tap on one cell of the table.  Toggles a tick and writes nothing."""
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

    cell["ticked"] = not cell.get("ticked")
    await state.update_data(**{DRAFT_SLOT: stored})
    # The toast BEFORE the redraw, always: the redraw is an API round-trip and the query
    # expires in fifteen seconds; at 800 ms a person cannot tell whether the tap counted.
    await query.answer("%s %s" % ("✓" if cell["ticked"] else "снял",
                                  cell.get("printed_label") or cell.get("label")))
    message = _editable(query)
    if message is not None:
        text, markup = render(stored, catalogue)
        await _redraw(message, text, markup)


async def pick_student(
    query: CallbackQuery, callback_data: VoicePick, state: FSMContext, catalogue
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
    # The alternatives were computed server-side when the table was drawn, so this is a
    # check against our own answer rather than against the payload's claim about itself.
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
    query: CallbackQuery, state: FSMContext, catalogue, marking, identity
) -> None:
    """«Записать» — the ONE place on this path where the journal is touched.

    Every cell goes through ``MarkingService.set_state`` with the target state, exactly as
    a tap on the grid does.  The idempotency key is SHA-256 OF THE RECORDING plus the cell
    it is about: a voice note Telegram delivers twice produces the same digest, the same
    table and therefore the same keys, and the second confirmation is answered out of the
    journal instead of writing a second event.
    """
    stored = await _stored_draft(state)
    if stored is None:
        await _refuse_as_stale(query)
        return

    written = repeated = failed = 0
    problems = []
    for student_id, problem_id in _writable(stored):
        try:
            outcome = marking.set_state(
                student_id,
                problem_id,
                CellState.SOLVED,
                source=SOURCE,
                teacher_id=_teacher_id(identity),
                idempotency_key="v:%s:%d:%d" % (stored.get("sha256", "")[:16],
                                                student_id, problem_id),
            )
        except MarkingError as error:  # pragma: no cover -- SOLVED never reverses
            failed += 1
            problems.append(str(error))
            continue
        if outcome.written:
            written += 1
        else:
            repeated += 1

    await state.update_data(**{DRAFT_SLOT: None})
    await query.answer("Записано: %d" % written)

    message = _editable(query)
    if message is None:
        return
    receipt = [
        "🎤 «%s»" % (stored.get("transcript") or "").strip(),
        "Записано отметок: %d%s%s"
        % (
            written,
            "; уже стояло: %d" % repeated if repeated else "",
            "; не записано: %d" % failed if failed else "",
        ),
    ]
    await _redraw(message, "\n".join(receipt), InlineKeyboardMarkup(inline_keyboard=[]))


async def cancel(query: CallbackQuery, state: FSMContext) -> None:
    """«Отмена».  Nothing was written, so there is nothing to undo — and the message says
    exactly that, because «отменено» over an unwritten draft reads as a rollback."""
    await state.update_data(**{DRAFT_SLOT: None})
    await query.answer("Черновик отброшен — в журнал ничего не попало.")
    message = _editable(query)
    if message is not None:
        await _redraw(
            message,
            "Черновик отброшен. В журнал ничего не записано.",
            InlineKeyboardMarkup(inline_keyboard=[]),
        )


def _teacher_id(identity) -> Optional[int]:
    """Which teacher goes into the journal row.  None for the owner, who has no binding."""
    teacher = getattr(identity, "teacher", None)
    return teacher.teacher_id if teacher is not None else None
