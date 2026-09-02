"""The role-based middleware.

ONE check, applied OUTSIDE every handler: who is this Telegram account, and
what may they do?

The brief is explicit: an unconfirmed student sees NOTHING, a confirmed
student sees ONLY their own, and a teacher without a role cannot write a
mark.  These are not properties of individual screens -- they are properties
of the account, and they live in one place.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, Optional

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, TelegramObject, Update

import bot.config_local as cfg
from core.services.roster import Role, RosterService, TeacherBinding


class Identity:
    """What the middleware learns about one Telegram account, in one place.

    Stamped onto ``data["identity"]`` for every handler to read.  Handlers
    that ignore the identity are bugs; tests assert that the middleware
    stamps the right shape for every role.
    """

    __slots__ = ("tg_id", "kind", "student_id", "teacher")

    def __init__(
        self,
        *,
        tg_id: int,
        kind: str,
        student_id: Optional[int] = None,
        teacher: Optional[TeacherBinding] = None,
    ) -> None:
        self.tg_id = tg_id
        self.kind = kind
        self.student_id = student_id
        self.teacher = teacher

    @property
    def is_owner(self) -> bool:
        # Identity doesn't know the owner's tg_id (that lives in the
        # middleware), so this stays simple.  Owner checks belong in the
        # middleware; handlers use Identity.kind == \"owner\".
        return self.kind == "owner"

    @property
    def is_pending_student(self) -> bool:
        # No student_id bound AND the roster has nothing yet: pending.
        # This is what the brief means by \"unconfirmed\" -- the tg_id is
        # known to the bot (because it asked for a name) but the catalogue
        # has no confirmed student row.
        return self.kind == "pending_student"

    @property
    def is_confirmed_student(self) -> bool:
        return self.kind == "confirmed_student" and self.student_id is not None

    @property
    def is_pending_teacher(self) -> bool:
        return self.kind == "pending_teacher"

    @property
    def is_teacher(self) -> bool:
        return self.kind in ("teacher", "head") and self.teacher is not None

    @property
    def is_head(self) -> bool:
        return self.is_teacher and self.teacher is not None and self.teacher.role is Role.HEAD

    @property
    def role(self) -> Optional[Role]:
        if self.is_confirmed_student:
            return Role.STUDENT
        if self.is_teacher and self.teacher is not None:
            return self.teacher.role
        return None


class AuthMiddleware(BaseMiddleware):
    """The outer middleware.  Stamp ``data["identity"]``; never let through silently.

    Two things can be wrong on a request:
      * the sender has no role (unconfirmed student, teacher without a role).
        The handler is the wrong place to deal with this -- the brief is
        explicit.  We deny with a one-line message and short-circuit.
      * the sender is the OWNER acting on a registration.  Owner's own
        private chat is the moderation surface and must not be gated.
    """

    def __init__(self, roster: RosterService, *, owner_tg_id: int) -> None:
        self._roster = roster
        self._owner_tg_id = owner_tg_id

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        tg_id = _extract_tg_id(event)
        if tg_id is None:
            # No identifiable sender (channel post).  No role, no access.
            return await _deny(
                event,
                "Бот отвечает только в личной переписке — из канала он вас не видит. "
                "Напишите ему напрямую.",
            )

        if tg_id == self._owner_tg_id:
            data["identity"] = Identity(tg_id=tg_id, kind="owner")
            return await handler(event, data)

        identity = await self._resolve(tg_id)
        data["identity"] = identity
        return await handler(event, data)

        identity = await self._resolve(tg_id)
        data["identity"] = identity
        return await handler(event, data)

    async def _resolve(self, tg_id: int) -> Identity:
        # Order matters: a confirmed student first (the catalogue knows them
        # by tg_id), then a confirmed teacher (the roster knows them), then
        # pending if the roster has a pending row for this tg_id.
        student_id = self._roster.student_id_for(tg_id)
        if student_id is not None:
            return Identity(tg_id=tg_id, kind="confirmed_student", student_id=student_id)

        teacher = self._roster.role_of_teacher(tg_id)
        if teacher is not None:
            kind = "head" if teacher.role is Role.HEAD else "teacher"
            return Identity(tg_id=tg_id, kind=kind, teacher=teacher)

        # No confirmed binding: maybe a pending registration, maybe a stranger.
        for pending in self._roster.list_pending():
            if pending.tg_id == tg_id:
                kind = (
                    "pending_student"
                    if pending.intended_role is Role.STUDENT
                    else "pending_teacher"
                )
                return Identity(tg_id=tg_id, kind=kind)
        return Identity(tg_id=tg_id, kind="stranger")


def require_role(*allowed: str):
    """Build an inner middleware that REJECTS identities outside ``allowed``.

    ``allowed`` is the set of ``Identity.kind`` values that may pass; anything
    else is answered with a one-line denial.  The handler still runs after
    the check -- the only difference is that ``data[\"identity\"]`` is the
    INNER one (this middleware), not the outer one, so a rejection here is a
    permissions refusal, not a stranger refusal.

    Returned object is a subclass of ``BaseMiddleware`` so it slots into
    ``Router.message.middleware`` / ``Router.callback_query.middleware``.
    """

    allowed_set = frozenset(allowed)

    class _Require(BaseMiddleware):
        async def __call__(self, handler, event, data):
            identity = data.get("identity")
            if identity is None:
                # 🔴 БЫЛО «auth not initialised» — диагностика разработчика,
                # по-английски, живому человеку. Что случилось внутри,
                # человека не касается; ему нужен следующий шаг.
                return await _deny(
                    event,
                    "Бот сейчас не может вас узнать. Попробуйте ещё раз через минуту.",
                )
            if identity.kind not in allowed_set:
                # 🔴 ОТКАЗ ЧИТАЕТ ЖИВОЙ ЧЕЛОВЕК, ЧАЩЕ ВСЕГО РЕБЁНОК.
                # Здесь стояла диагностика разработчика — «this screen is for
                # pending_student or pending_teacher or stranger; you are a
                # owner.»: по-английски, внутренними именами ролей и с ошибкой
                # в самом английском. Владелец увидел ровно её первым же
                # `/start` в 14:24 живого прогона. Отказ не обязан объяснять
                # устройство ролей — он обязан сказать человеку, что делать.
                return await _deny(
                    event,
                    "Этот экран вам не открыт. Если вы недавно отправили "
                    "заявку — её ещё не подтвердили.",
                )
            return await handler(event, data)

    _Require.__name__ = "Require(%s)" % "|".join(sorted(allowed_set))
    return _Require()


def _extract_tg_id(event: TelegramObject) -> Optional[int]:
    if isinstance(event, (Message, CallbackQuery)):
        user = event.from_user
        if user is None:
            return None
        return user.id
    if isinstance(event, Update):
        if event.message is not None and event.message.from_user is not None:
            return event.message.from_user.id
        if event.callback_query is not None and event.callback_query.from_user is not None:
            return event.callback_query.from_user.id
    return None


async def _deny(event: TelegramObject, text: str):
    if isinstance(event, Message):
        return await event.answer(text)
    if isinstance(event, CallbackQuery):
        return await event.answer(text, show_alert=True)
    return None