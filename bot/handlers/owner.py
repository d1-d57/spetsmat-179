"""The owner's moderation surface.

Three buttons per pending row: ``принять`` · ``переименовать`` · ``отклонить``.
The owner's tg_id is the only one whose accept / rename / reject do anything;
the middleware has already refused everyone else by the time this handler runs.

Callback data carries the registration id, not the Telegram id: the brief is
explicit that the privacy boundary is the binding, not the message.
"""

from __future__ import annotations

from typing import Any, Dict

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import bot.config_local as cfg
from bot.fsm import StudentRegistration, TeacherRegistration
from bot.middleware import Identity, require_role
from core.models import Sheet
from core.services.roster import (
    PendingRegistration,
    Role,
    RosterService,
    RosterError,
    TelegramIdAlreadyBound,
)
from infra.repositories import SqliteCatalogue

router = Router()

# Only the owner sees the moderation screen.
router.message.middleware(require_role("owner"))
router.callback_query.middleware(require_role("owner"))


# ----------------------------------------------------------------- helpers

def _pending_keyboard(rows: list) -> InlineKeyboardMarkup:
    """One row per pending registration, three buttons per row."""
    buttons: list = []
    for row in rows:
        label = "%s %s" % (row.surname, row.name)
        suffix = "(%s)" % row.intended_role.value if row.intended_role is not Role.STUDENT else ""
        buttons.append(
            [InlineKeyboardButton(text="%s%s" % (label, suffix),
                                  callback_data="noop")]
        )
        buttons.append([
            InlineKeyboardButton(text="принять", callback_data="accept:%d" % row.id),
            InlineKeyboardButton(text="переименовать", callback_data="rename:%d" % row.id),
            InlineKeyboardButton(text="отклонить", callback_data="reject:%d" % row.id),
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _current_sheet_id(catalogue: SqliteCatalogue) -> int:
    """The 'current sheet' for ``first_sheet_id``.

    The brief: 'the sheet that is CURRENT at the moment of confirmation, never
    NULL and never the first sheet of the year.'  P4 will eventually swap this
    for a real notion of 'today's session'; P3 uses 'max ord among issued
    sheets' as the cheapest definition that has a number to anchor.
    """
    sheets: list = catalogue.sheets()
    if not sheets:
        raise RosterError("no sheets in the catalogue; refuse to register a student against NULL")
    return max(sheets, key=lambda s: s.ord).id


# ----------------------------------------------------------------- commands

@router.message(F.text == "/pending")
async def show_pending(message: Message, roster: RosterService) -> None:
    rows = roster.list_pending()
    if not rows:
        await message.answer("Заявок нет.")
        return
    await message.answer(_render_pending(rows), reply_markup=_pending_keyboard(rows))


@router.callback_query(F.data.startswith("reject:"))
async def on_reject(callback: CallbackQuery, roster: RosterService) -> None:
    registration_id = int(callback.data.split(":", 1)[1])
    roster.reject(registration_id)
    await callback.answer("Отклонено.")
    await _refresh_pending_list(callback.message, roster)


@router.callback_query(F.data.startswith("accept:"))
async def on_accept(
    callback: CallbackQuery,
    roster: RosterService,
    catalogue: SqliteCatalogue,
) -> None:
    registration_id = int(callback.data.split(":", 1)[1])
    pending = roster.list_pending()  # cheap, no separate get_pending in service
    target = next((p for p in pending if p.id == registration_id), None)
    if target is None:
        await callback.answer("Заявка уже закрыта.", show_alert=True)
        return
    try:
        if target.intended_role is Role.STUDENT:
            roster.confirm_student(target)
            await callback.answer("Ученик подтверждён.")
        else:
            # Default role on accept: TEACHER.  Owner can promote later.
            roster.confirm_teacher(target, role=Role.TEACHER, room=target.room)
            await callback.answer("Преподаватель подтверждён как TEACHER.")
    except (RosterError, TelegramIdAlreadyBound) as exc:
        await callback.answer("Не удалось: %s" % exc, show_alert=True)
        return
    roster.accept(registration_id)
    await _refresh_pending_list(callback.message, roster)


@router.callback_query(F.data.startswith("rename:"))
async def on_rename(
    callback: CallbackQuery,
    state: FSMContext,
    roster: RosterService,
) -> None:
    registration_id = int(callback.data.split(":", 1)[1])
    # FSM is reused for both flows -- a rename is just \"edit a pending row\".
    await state.update_data(rename_registration_id=registration_id)
    await state.set_state(StudentRegistration.waiting_for_surname)
    await callback.answer()
    await callback.message.answer("Новая фамилия:")


@router.message(StudentRegistration.waiting_for_surname)
async def rename_surname(message: Message, state: FSMContext, roster: RosterService) -> None:
    surname = (message.text or "").strip()
    if not surname:
        await message.answer("Фамилия пустая, попробуйте ещё раз.")
        return
    data = await state.get_data()
    registration_id = data.get("rename_registration_id")
    if registration_id is None:
        await state.clear()
        return
    await state.update_data(rename_surname=surname)
    await state.set_state(StudentRegistration.waiting_for_name)
    await message.answer("Новое имя:")


@router.message(StudentRegistration.waiting_for_name)
async def rename_name(message: Message, state: FSMContext, roster: RosterService) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("Имя пустое, попробуйте ещё раз.")
        return
    data = await state.get_data()
    registration_id = data.get("rename_registration_id")
    surname = data.get("rename_surname", "")
    if registration_id is None:
        await state.clear()
        return
    roster.rename(registration_id, surname=surname, name=name)
    await state.clear()
    await message.answer("Переименовано.")


async def _refresh_pending_list(message: Message, roster: RosterService) -> None:
    rows = roster.list_pending()
    if not rows:
        try:
            await message.edit_text("Заявок больше нет.")
        except Exception:
            # The callback's message can be InaccessibleMessage in tests and
            # after a long timeout in production; a no-op edit is honest.
            pass
        return
    try:
        await message.edit_text(_render_pending(rows), reply_markup=_pending_keyboard(rows))
    except Exception:
        pass


def _render_pending(rows: list) -> str:
    lines = ["Заявки (%d):" % len(rows)]
    for row in rows:
        suffix = "(%s)" % row.intended_role.value if row.intended_role is not Role.STUDENT else ""
        lines.append("- id=%d: %s %s%s" % (row.id, row.surname, row.name, suffix))
    return "\n".join(lines)