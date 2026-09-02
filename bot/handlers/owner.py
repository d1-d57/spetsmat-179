"""The owner's moderation surface.

Three buttons per pending row: ``принять`` · ``переименовать`` · ``отклонить``.
The owner's tg_id is the only one whose accept / rename / reject do anything;
the middleware has already refused everyone else by the time this handler runs.

Callback data carries the registration id, not the Telegram id: the brief is
explicit that the privacy boundary is the binding, not the message.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from aiogram import Bot, F, Router
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
    StudentMatch,
    TelegramIdAlreadyBound,
)
from infra.repositories import SqliteCatalogue

router = Router()

log = logging.getLogger(__name__)

# Only the owner sees the moderation screen.
router.message.middleware(require_role("owner"))
router.callback_query.middleware(require_role("owner"))

#: Buttons that resolve a заявка into a NAMED catalogue row: ``bindstud:<reg>:<student>``.
BIND_PREFIX = "bindstud:"
#: The one button that is allowed to create a row: ``newstud:<reg>``.
NEW_PREFIX = "newstud:"


# ----------------------------------------------------------------- helpers

def _pending_keyboard(rows: list) -> InlineKeyboardMarkup:
    """One row per pending registration, three buttons per row."""
    buttons: list = []
    for row in rows:
        label = "%s %s" % (row.surname, row.name)
        suffix = (
            " — %s" % _rol_po_russki(row.intended_role)
            if row.intended_role is not Role.STUDENT
            else ""
        )
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


# ------------------------------------------------- the owner hears about a заявка
#
# 🔴 WHY THIS LIVES IN owner.py AND NOT WHERE THE ЗАЯВКА IS CREATED.  The заявка is
# written by ``bot/handlers/registration.py`` and the service is built by
# ``bot/app.py``; both are outside this position's zone and neither may be edited.  The
# seam that stays inside it is aiogram's own ``startup`` event: ``dp.start_polling``
# emits it with ``bot``, ``roster`` and ``owner_tg_id`` already in ``workflow_data``, so
# the notifier can be installed on the live service without a line changing anywhere
# else.  What ``registration.py`` calls is unchanged -- ``roster.submit_student`` -- and
# the service fires the callback it was handed.
#
# ⚠ Idempotency is NOT in this file and deliberately so: the claim is a row in the
# roster database (``RosterRepo.claim_notification``), taken before the message is
# built.  A retry, a second caller and a restarted process all lose to the primary key,
# and one заявка produces exactly one message.

#: Tasks in flight.  ``asyncio`` keeps only a weak reference to a task, so a message
#: sent fire-and-forget can be garbage-collected mid-send; holding it here until it is
#: done is the documented way to stop that.
_in_flight: set = set()

#: Как роль НАЗЫВАЕТСЯ ЧЕЛОВЕКУ. `Role.value` — это «teacher» и «head»: член
#: перечисления, слово из кода. Владелец читает список заявок глазами, и там
#: обязано стоять русское слово, а не значение поля.
ROL_PO_RUSSKI = {
    Role.STUDENT: "ученик",
    Role.TEACHER: "преподаватель",
    Role.HEAD: "старший аудитории",
}


def _rol_po_russki(role: Role) -> str:
    """Русское имя роли; неизвестную роль называем нейтрально, а не её кодом."""
    return ROL_PO_RUSSKI.get(role, "преподаватель")


def _pochemu_ne_vyshlo(exc: Exception) -> str:
    """Что владелец читает вместо текста исключения.

    🔴 ЗДЕСЬ СТОЯЛО `"Не удалось: %s" % exc`, и `exc` — это внутренняя
    диагностика по-английски: «no current sheet to anchor first_sheet_id:
    refusing to register a student against NULL…». Тот же класс, что
    английский отказ, который владелец увидел от бота в 14:3x. Диагностика не
    теряется — она уходит в журнал бота, туда, где её читает разработчик.
    """
    if isinstance(exc, TelegramIdAlreadyBound):
        return (
            "Этот Telegram уже привязан к другому человеку из списка. "
            "Отклоните заявку или снимите старую привязку и попробуйте снова."
        )
    return (
        "Не получилось записать — заявка осталась открытой. "
        "Причина записана в журнал бота."
    )


def _pending_announcement(registration: PendingRegistration) -> str:
    role = "ученик" if registration.intended_role is Role.STUDENT else "преподаватель"
    line = "Новая заявка: %s %s — %s" % (
        registration.surname, registration.name, role,
    )
    if registration.room:
        line += ", кабинет %s" % registration.room
    return line


def pending_notifier(bot: Bot, owner_tg_id: int) -> Any:
    """A callback the roster service fires once per new заявка.

    Synchronous, because ``core/`` may not know what a coroutine of the bot framework
    is.  The send is scheduled on the loop the handler is already running on; a failure
    to deliver is logged and never propagated, because the заявка is the thing that
    matters and a Telegram hiccup must not roll back a registration that is already
    written.
    """

    def notify(registration: PendingRegistration) -> None:
        coroutine = bot.send_message(
            chat_id=owner_tg_id,
            text=_pending_announcement(registration),
            reply_markup=_pending_keyboard([registration]),
        )
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No loop: nothing can be sent from here.  Close the coroutine rather than
            # leaving it un-awaited, and say so -- a warning in the log is the honest
            # outcome, a silent drop is not.
            coroutine.close()
            log.warning(
                "no running loop: заявка %d was not announced to the owner",
                registration.id,
            )
            return
        task = loop.create_task(coroutine)
        _in_flight.add(task)

        def _done(finished) -> None:
            _in_flight.discard(finished)
            error = finished.exception() if not finished.cancelled() else None
            if error is not None:
                log.warning(
                    "could not announce заявка %d to the owner: %s",
                    registration.id, error,
                )

        task.add_done_callback(_done)

    return notify


@router.startup()
async def install_pending_notifier(
    roster: RosterService,
    bot: Bot,
    owner_tg_id: int,
    **_: Any,
) -> None:
    """Hand the live service the notifier, once, when the bot comes up."""
    roster.set_pending_notifier(pending_notifier(bot, owner_tg_id))


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


def _find_pending(roster: RosterService, registration_id: int):
    """The pending row by id, or None if the owner acted on a closed заявка."""
    return next(
        (p for p in roster.list_pending() if p.id == registration_id), None
    )


def _choice_keyboard(
    registration: PendingRegistration, match: StudentMatch
) -> InlineKeyboardMarkup:
    """One button per catalogue row that fits, plus the create button.

    🔴 The create button is drawn on EVERY one of these screens, and it is the only
    door to creating a row.  On a tie the owner picks a child; on no match at all this
    button is the whole screen.  What is never drawn is a guess.
    """
    buttons: list = []
    for candidate in match.candidates:
        student = candidate.student
        buttons.append([
            InlineKeyboardButton(
                text="%s — %d%%" % (student.label, round(candidate.score * 100)),
                callback_data="%s%d:%d" % (BIND_PREFIX, registration.id, student.id),
            )
        ])
    buttons.append([
        InlineKeyboardButton(
            text="нет в списке — завести нового",
            callback_data="%s%d" % (NEW_PREFIX, registration.id),
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _choice_text(registration: PendingRegistration, match: StudentMatch) -> str:
    who = "%s %s" % (registration.surname, registration.name)
    if match.kind == "ambiguous":
        return (
            "«%s» подходит сразу к нескольким в списке (%d). "
            "Выберите, кто это, — угадывать бот не будет."
            % (who, len(match.candidates))
        )
    return (
        "«%s» в списке не найден. Завести нового? "
        "Прошлогодних отметок у него не будет." % who
    )


@router.callback_query(F.data.startswith("accept:"))
async def on_accept(
    callback: CallbackQuery,
    roster: RosterService,
    catalogue: SqliteCatalogue,
) -> None:
    """«принять» — for a student this now BINDS, and only binds.

    🔴 What this handler used to do, and why it was the most expensive line in the
    project: it called ``confirm_student``, which INSERTED a row.  On the live base
    accepting Пирогов Константин would have made a second Пирогов with an empty year,
    bound the telegram to that one, and left the real two hundred and one marks on a
    row nobody could reach -- cancelling the import of 15 847 marks that P2 loaded so
    that a child would open the bot on the first of September and see his own year.
    """
    registration_id = int(callback.data.split(":", 1)[1])
    target = _find_pending(roster, registration_id)
    if target is None:
        await callback.answer(
            "Эта заявка уже закрыта — список ниже обновится сам.",
            show_alert=True,
        )
        return

    if target.intended_role is not Role.STUDENT:
        try:
            # Default role on accept: TEACHER.  Owner can promote later.
            roster.confirm_teacher(target, role=Role.TEACHER, room=target.room)
        except (RosterError, TelegramIdAlreadyBound) as exc:
            log.warning("confirm_teacher отказал: %s", exc)
            await callback.answer(_pochemu_ne_vyshlo(exc), show_alert=True)
            return
        # 🔴 ВНУТРЕННЕЕ ИМЯ РОЛИ ЧЕЛОВЕКУ НЕ ПОКАЗЫВАЕМ. `TEACHER` — это член
        # перечисления Role, а читает строку живой человек. Тот же класс, что
        # английская диагностика, которую владелец увидел от бота в 14:3x.
        await callback.answer("Преподаватель подтверждён.")
        roster.accept(registration_id)
        await _refresh_pending_list(callback.message, roster)
        return

    try:
        match = roster.match_student(target)
    except RosterError as exc:
        log.warning("match_student отказал: %s", exc)
        await callback.answer(_pochemu_ne_vyshlo(exc), show_alert=True)
        return

    if match.kind != "single":
        # Two or more, or none at all: the owner decides, on buttons.  Nothing is
        # written and the заявка stays open until they press one.
        await callback.answer()
        await callback.message.answer(
            _choice_text(target, match),
            reply_markup=_choice_keyboard(target, match),
        )
        return

    student = match.one
    try:
        roster.bind_student(target, student.id)
    except (RosterError, TelegramIdAlreadyBound) as exc:
        log.warning("bind_student отказал: %s", exc)
        await callback.answer(_pochemu_ne_vyshlo(exc), show_alert=True)
        return
    await callback.answer("Привязан к «%s» из списка." % student.label)
    roster.accept(registration_id)
    await _refresh_pending_list(callback.message, roster)


@router.callback_query(F.data.startswith(BIND_PREFIX))
async def on_bind_chosen(callback: CallbackQuery, roster: RosterService) -> None:
    """The owner picked which child a tied заявка is."""
    payload = callback.data[len(BIND_PREFIX):]
    registration_id, student_id = (int(part) for part in payload.split(":", 1))
    target = _find_pending(roster, registration_id)
    if target is None:
        await callback.answer(
            "Эта заявка уже закрыта — список ниже обновится сам.",
            show_alert=True,
        )
        return
    try:
        roster.bind_student(target, student_id)
    except (RosterError, TelegramIdAlreadyBound) as exc:
        log.warning("bind_student (выбор владельца) отказал: %s", exc)
        await callback.answer(_pochemu_ne_vyshlo(exc), show_alert=True)
        return
    roster.accept(registration_id)
    await callback.answer("Привязано.")
    await _refresh_pending_list(callback.message, roster)


@router.callback_query(F.data.startswith(NEW_PREFIX))
async def on_create_new(callback: CallbackQuery, roster: RosterService) -> None:
    """The only door to a NEW catalogue row, and the owner is standing in it."""
    registration_id = int(callback.data[len(NEW_PREFIX):])
    target = _find_pending(roster, registration_id)
    if target is None:
        await callback.answer(
            "Эта заявка уже закрыта — список ниже обновится сам.",
            show_alert=True,
        )
        return
    try:
        roster.create_new_student(target)
    except (RosterError, TelegramIdAlreadyBound) as exc:
        log.warning("create_new_student отказал: %s", exc)
        await callback.answer(_pochemu_ne_vyshlo(exc), show_alert=True)
        return
    roster.accept(registration_id)
    await callback.answer("Заведён новый ученик.")
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
    """Список заявок глазами владельца.

    🔴 БЕЗ `id=`. Номер заявки — поле базы, и владельцу он не нужен: заявку он
    закрывает КНОПКОЙ под этим же сообщением, а номер уезжает в её
    `callback_data`, куда человек не смотрит.
    """
    lines = ["Заявки (%d):" % len(rows)]
    for row in rows:
        suffix = (
            " — %s" % _rol_po_russki(row.intended_role)
            if row.intended_role is not Role.STUDENT
            else ""
        )
        lines.append("- %s %s%s" % (row.surname, row.name, suffix))
    return "\n".join(lines)