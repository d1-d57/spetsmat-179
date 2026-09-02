"""The deep-link registration flows.

Two entry points:
  * ``/start register-student`` -- a stranger becomes a pending student;
  * ``/start register-teacher`` -- a stranger becomes a pending teacher.

The owner separately confirms each pending row through ``bot/handlers/owner.py``.
A row in the catalogue is only ``active`` after the owner's accept button,
and the schema's ``tg_id`` UNIQUE is what stops a second binding.
"""

from __future__ import annotations

from typing import Any, Dict

from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import bot.config_local as cfg
from bot.fsm import StudentRegistration, TeacherRegistration
from bot.middleware import Identity, require_role
from core.services.roster import Role, RosterService, TelegramIdAlreadyBound

router = Router()


# Both roles may start a registration -- the deep-link is the door.
# 🔴 ВЛАДЕЛЕЦ ТОЖЕ ПРОХОДИТ СЮДА. Без него `/start` для владельца упирался в отказ
# роли: он единственный человек, который обязан иметь возможность потыкать бота
# руками, и он же первый, кто это сделал (живой прогон 02.09 14:24). Регистрацию
# владельцу это не открывает — дальше по коду его ведёт deep link, как и всех.
router.message.middleware(
    require_role("stranger", "pending_student", "pending_teacher", "owner")
)


@router.message(CommandStart(deep_link=True))
async def on_start(message: Message, command: CommandObject, state: FSMContext) -> None:
    """Route the deep-link code to the matching flow."""
    args = (command.args or "").strip()
    if args == cfg.DEEPLINK_CODE_STUDENT:
        await state.set_state(StudentRegistration.waiting_for_surname)
        await message.answer("Введите вашу фамилию.")
        return
    if args == cfg.DEEPLINK_CODE_TEACHER:
        await state.set_state(TeacherRegistration.waiting_for_surname)
        await message.answer("Введите вашу фамилию.")
        return
    await message.answer(
        "Эта ссылка не открывает регистрацию. Используйте ссылку из чата класса."
    )


@router.message(CommandStart())
async def on_start_no_link(message: Message) -> None:
    """``/start`` with no deep-link args: a no-op welcome, never a door."""
    await message.answer(
        "Этот бот работает только по ссылке из чата класса. "
        "Попросите у владельца ссылку для регистрации."
    )


# ---- student flow ------------------------------------------------------------

@router.message(StudentRegistration.waiting_for_surname, F.text)
async def student_surname(
    message: Message, state: FSMContext, roster: RosterService
) -> None:
    surname = _clean_text(message.text)
    if not surname:
        await message.answer("Фамилия пустая, попробуйте ещё раз.")
        return
    await state.update_data(surname=surname)
    await state.set_state(StudentRegistration.waiting_for_name)
    await message.answer("Теперь имя.")


@router.message(StudentRegistration.waiting_for_name, F.text)
async def student_name(
    message: Message, state: FSMContext, roster: RosterService
) -> None:
    name = _clean_text(message.text)
    if not name:
        await message.answer("Имя пустое, попробуйте ещё раз.")
        return
    data = await state.get_data()
    surname = data.get("surname", "")
    tg_id = message.from_user.id
    try:
        roster.submit_student(tg_id=tg_id, surname=surname, name=name)
    except TelegramIdAlreadyBound:
        await message.answer(
            "У вас уже есть заявка. Владелец подтверждает их вручную; "
            "отправлять её второй раз не нужно."
        )
        await state.clear()
        return
    await state.clear()
    # 🔴 ЗДЕСЬ СТРОКА ВРАЛА, И ЭТО НАШЁЛ САМ ВЛАДЕЛЕЦ: «он подтвердит её — и
    # тогда вы сможете открыть бот». Бот так не открывается. Подтверждение —
    # ручное нажатие владельца в /pending, и оно НЕ ШЛЁТ ученику ничего:
    # уведомление в `pending_notifier` идёт только владельцу и только о новой
    # заявке. Ребёнок, поверивший этой строке, ждёт сообщения, которого нет.
    await message.answer(
        "Заявка отправлена. Владелец подтверждает такие заявки вручную, и отдельного "
        "сообщения об этом не придёт — просто отправьте боту /god чуть позже: как "
        "только заявку подтвердят, команда откроется."
    )


# ---- teacher flow -----------------------------------------------------------

@router.message(TeacherRegistration.waiting_for_surname, F.text)
async def teacher_surname(
    message: Message, state: FSMContext, roster: RosterService
) -> None:
    surname = _clean_text(message.text)
    if not surname:
        await message.answer("Фамилия пустая, попробуйте ещё раз.")
        return
    await state.update_data(surname=surname)
    await state.set_state(TeacherRegistration.waiting_for_name)
    await message.answer("Теперь имя.")


@router.message(TeacherRegistration.waiting_for_name, F.text)
async def teacher_name(
    message: Message, state: FSMContext, roster: RosterService
) -> None:
    name = _clean_text(message.text)
    if not name:
        await message.answer("Имя пустое, попробуйте ещё раз.")
        return
    await state.update_data(name=name)
    await state.set_state(TeacherRegistration.waiting_for_room)
    await message.answer(
        "Введите номер аудитории (" + ", ".join(cfg.ROOMS) + "), "
        "в которой вы ведёте занятия."
    )


@router.message(TeacherRegistration.waiting_for_room, F.text)
async def teacher_room(
    message: Message, state: FSMContext, roster: RosterService
) -> None:
    room = _clean_text(message.text)
    if room not in cfg.ROOMS:
        await message.answer("Аудитория должна быть одной из: " + ", ".join(cfg.ROOMS))
        return
    data = await state.get_data()
    surname = data.get("surname", "")
    name = data.get("name", "")
    tg_id = message.from_user.id
    try:
        roster.submit_teacher(tg_id=tg_id, surname=surname, name=name, room=room)
    except TelegramIdAlreadyBound:
        await message.answer(
            "У вас уже есть заявка. Владелец подтверждает их вручную; "
            "отправлять её второй раз не нужно."
        )
        await state.clear()
        return
    await state.clear()
    # Тот же разбор, что у ученической ветки выше: подтверждения ждать
    # молча нечего, бот о нём не сообщает. И «назначит роль» — слово из
    # кода; преподавателю важно, ЧТО у него откроется, а не как это
    # называется внутри.
    await message.answer(
        "Заявка отправлена. Владелец подтверждает такие заявки вручную, и отдельного "
        "сообщения об этом не придёт — просто отправьте боту /setka чуть позже: как "
        "только заявку подтвердят, экран отметок откроется."
    )


# ---- helpers -----------------------------------------------------------------

def _clean_text(text: str) -> str:
    """Strip whitespace and cap to NAME_MAX_LEN.  Empty after stripping -> ''."""
    cleaned = (text or "").strip()
    return cleaned[: cfg.NAME_MAX_LEN]