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

# Both TEACHER and HEAD may pass the outer gate; HEAD-only is enforced
# INSIDE the /upload_sheet handler where the rule is OBVIOUS to a reader.
router.message.middleware(require_role("teacher", "head"))


@router.message(F.text == "/me")
async def show_me(message: Message, identity) -> None:
    await message.answer(
        "Вы — %s%s."
        % (
            identity.teacher.role.value,
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
    await message.answer(
        "Загрузка листка для аудитории %s — P4." % identity.teacher.room
    )