"""The teacher screens.

P4 will replace ``/upload_sheet`` with a real sheet-upload flow; P3 ships a
stub so the middleware has a HEAD-only gate to enforce.  The brief is
explicit: a TEACHER cannot upload a sheet, a HEAD can.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from bot.middleware import require_role

router = Router()

#: Как роль НАЗЫВАЕТСЯ ЧЕЛОВЕКУ. `role.value` — это «teacher» и «head»,
#: значения перечисления `Role`; преподаватель читает экран глазами.
ROL_PO_RUSSKI = {
    "teacher": "преподаватель",
    "head": "старший аудитории",
}

# Both TEACHER and HEAD may pass the outer gate; HEAD-only is enforced
# INSIDE the /upload_sheet handler where the rule is OBVIOUS to a reader.
router.message.middleware(require_role("teacher", "head"))


@router.message(F.text == "/me")
async def show_me(message: Message, identity) -> None:
    # 🔴 БЫЛО `identity.teacher.role.value` — и преподаватель читал
    # «Вы — teacher, аудитория 203.»: имя члена перечисления, по-английски.
    await message.answer(
        "Вы — %s%s."
        % (
            ROL_PO_RUSSKI.get(identity.teacher.role.value, "преподаватель"),
            (", аудитория %s" % identity.teacher.room) if identity.teacher.room else "",
        )
    )


@router.message(F.text == "/upload_sheet")
async def upload_sheet_stub(message: Message, identity) -> None:
    """HEAD-only: a TEACHER is refused here, with a one-line denial.

    The brief asks for a HEAD/TEACHER distinction on this exact screen; the
    check is in the handler so the rule is visible at the call site, not
    buried in a stacked middleware.
    """
    if identity.teacher is None or identity.teacher.role.value != "head":
        await message.answer("Загрузка листков — только для старшего аудитории.")
        return
    # 🔴 БЫЛО «Загрузка листка для аудитории %s — P4.» — две беды в одной
    # строке. «P4» — имя позиции волны, внутреннее состояние фабрики, а не
    # бота. И строка ВРЁТ: она читается как подтверждение загрузки, а не
    # загружается ничего — обработчик заглушка и сразу заканчивается.
    await message.answer(
        "Загрузка листков через бота пока не работает — листки заводит владелец. "
        "Отметки ставьте кнопками: /setka."
    )