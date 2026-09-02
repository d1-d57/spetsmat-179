"""The student screens.

P5 will replace these with real views; P3 ships a minimal ``/me`` so the
middleware has something to gate.  The point of P3 here is that the
CONFIRMED student sees ONLY their own -- and the middleware refuses
``pending_student``, ``stranger`` and anyone who is not in the catalogue.
"""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from bot.middleware import require_role

router = Router()

# Only confirmed students may read these screens.
router.message.middleware(require_role("confirmed_student"))


@router.message(F.text == "/me")
async def show_me(message: Message, identity) -> None:
    """Подтверждённому ученику — то, что он может сделать дальше.

    🔴 ЗДЕСЬ ПЕЧАТАЛОСЬ «Ваш номер в журнале: %d» с `identity.student_id`.
    Это первичный ключ строки в базе, а не номер в журнале: он ничего не
    значит для ребёнка, он ВРЁТ про то, чем является, и он же — внутреннее
    состояние, напечатанное человеку. Экраны года и долгов делает P5, и
    именно их ученику и надо назвать.
    """
    await message.answer(
        "Вы в списке. Ваш год — /god, что нужно сдать — /dolgi."
    )


@router.message(F.text.startswith("/peek"))
async def forbidden_peek(message: Message, identity) -> None:
    """A forged callback that asks for another student's data is answered with
    a refusal here -- NOT in the middleware (the URL is well-formed) and NOT
    silently (the brief requires coverage, not just correctness).
    """
    await message.answer(
        "Вы видите только свои данные. Свой год — /god, свои долги — /dolgi."
    )