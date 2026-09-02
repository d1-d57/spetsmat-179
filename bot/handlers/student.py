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
    """A confirmed student's own id -- the only piece of self a P3 screen knows.

    P5 replaces this with a plusnik and a debt list.
    """
    await message.answer("Ваш номер в журнале: %d" % identity.student_id)


@router.message(F.text.startswith("/peek"))
async def forbidden_peek(message: Message, identity) -> None:
    """A forged callback that asks for another student's data is answered with
    a refusal here -- NOT in the middleware (the URL is well-formed) and NOT
    silently (the brief requires coverage, not just correctness).
    """
    await message.answer("Вы видите только свои данные.")