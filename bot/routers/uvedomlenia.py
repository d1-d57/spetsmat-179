"""The bot speaking first: the after-lesson send, and the two buttons that answer it.

Every other router in this project is a REPLY -- a person tapped something and the bot
answered.  This one is the other direction, and the difference shows up in the shape:
there is no update to respond to when the summary goes out, so the send is a plain
coroutine anybody can call, and only the ANSWER to the teacher's question comes back
through the dispatcher as an ordinary callback.

WHEN IT IS CALLED IS NOT DECIDED HERE, AND THAT IS THE POINT.  ``send_after_lesson`` takes
the id of a lesson that has CLOSED and sends what ``SvodkaService.plan`` says.  The
scheduling belongs to P10; the exact command and the frequency are named in ``## ВОПРОСЫ``
of ``zhurnal/2026-09-02_spetsmat-bot/kod_P14-uvedomlenia.md``.  Nothing in this file reads
a clock to decide whether a lesson is over -- Telegram inside the school building is
unreliable, so the trigger is the closing of the lesson and never an hour of the day.

THE CLAIM COMES BEFORE THE SEND, AND THAT ORDER IS DELIBERATE.  ``service.claim`` is a
single insert-or-nothing in the database: it answers True once per (lesson, addressee) and
False every time after, whatever process asks.  Claiming first means a crash between the
claim and the Telegram request loses that one message; claiming after sending would mean a
crash between the request and the claim SENDS IT AGAIN on the next run.  A summary that did
not arrive is something a person can ask for; a summary that arrives twice teaches its
reader to stop opening them, and then the feature is worse than absent.

A FAILED SEND IS NOT A FAILED RUN.  One teacher with a blocked bot must not stop the
summaries going to the rooms, so every send is caught individually and counted.  The
result object carries the coverage -- sent, skipped as already-sent, unreachable, failed --
because "разослано 3" and "разослано 3 из 8" are different statements and only the second
one can be acted on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from aiogram import Bot, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from bot.callbacks import ids_are_storable
from bot.middleware import require_role
from core.services.svodka import (
    ABSENT,
    PRESENT,
    RECIPIENT_TEACHER,
    SvodkaError,
    SvodkaService,
)

#: Who may answer the question about their own attendance.  A student never receives it,
#: so a student never has a payload to forge; the gate is here anyway, because "no button
#: was ever drawn for you" is not an access control.
TEACHER_ROLES = ("teacher", "head", "owner")

#: The substring Telegram uses when a redraw would change nothing.  Matched inside the
#: message of ``TelegramBadRequest`` and nowhere else: that exception also carries a
#: deleted message, a bad payload and an expired query, and a bare ``except`` would hide
#: every API failure this screen can have.  Same constant and same reason as
#: ``bot/routers/views.py``.
NOT_MODIFIED = "message is not modified"

#: The two answers, as integers.  ``bot/callbacks.py`` states the law this obeys: only
#: numbers go into a payload, never a string typed by a human -- the separator is ``:``
#: and a Cyrillic character costs two of the sixty-four available bytes.  The router maps
#: these onto ``config.ATTENDANCE_STATUSES``; the payload stays an integer.
ANSWER_ABSENT = 0
ANSWER_PRESENT = 1
ANSWERS = (ANSWER_ABSENT, ANSWER_PRESENT)


class Yavka(CallbackData, prefix="yavka"):
    """«Вы были на занятии?» -- the lesson, and which of the two answers was tapped.

    Its own prefix, so this router claims only its own buttons and nothing else claims
    these; the same arrangement every other screen of the project uses.

    The payload carries the TARGET STATE and never an operation to apply to whatever the
    server finds, so two identical taps in either order leave the same row -- which is
    what makes a double tap harmless by construction rather than by defence.
    """

    session_id: int
    answer: int


def answer_keyboard(session_id: int) -> InlineKeyboardMarkup:
    """The two buttons under the question.  Their labels are the two words the project
    already spells attendance with, so the teacher answers in the same vocabulary the
    register is kept in."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="был",
                    callback_data=Yavka(
                        session_id=session_id, answer=ANSWER_PRESENT
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="не был",
                    callback_data=Yavka(
                        session_id=session_id, answer=ANSWER_ABSENT
                    ).pack(),
                ),
            ]
        ]
    )


# --------------------------------------------------------------------------- the send


@dataclass(frozen=True)
class SendReport:
    """What one run of ``send_after_lesson`` actually did, with its coverage.

    ``planned`` is how many messages the lesson had to say; the four counters below split
    them and always add up to it.  A report that said only "разослано 3" would be
    unreadable: three out of three and three out of eleven are different evenings.
    """

    session_id: int
    planned: int = 0
    sent: int = 0
    #: Already claimed by an earlier run -- the idempotent path, and the normal one on a
    #: second call.  Not an error.
    already: int = 0
    #: Known addressees with no Telegram id yet.  A real state at the start of a year.
    unreachable: int = 0
    #: The API refused.  Counted, never raised: one blocked bot must not stop the rest.
    failed: int = 0
    errors: list = field(default_factory=list)

    def line(self) -> str:
        """One line for a log or a report.  Names every number, including the zeros."""
        return (
            "занятие %d: разослано %d из %d · уже слали %d · без телеграма %d · "
            "не доставлено %d"
            % (
                self.session_id,
                self.sent,
                self.planned,
                self.already,
                self.unreachable,
                self.failed,
            )
        )


async def send_after_lesson(
    bot: Bot,
    service: SvodkaService,
    session_id: int,
) -> SendReport:
    """Send everything one CLOSED lesson has to say.  Safe to call again: it will send
    nothing the second time.

    The order inside the loop is claim → send, for the reason in the module docstring.
    Every failure is caught per message: the summary for room 302 must not be lost because
    the teacher of 203 has blocked the bot.
    """
    plan = service.plan(session_id)
    sent = already = unreachable = failed = 0
    errors: list = []

    for notification in plan.notifications:
        if not notification.deliverable:
            # Nothing to claim: an unclaimed row leaves the message pending for the run
            # that happens after this person registers, which is the useful behaviour.
            unreachable += 1
            continue
        if not service.claim(notification):
            already += 1
            continue
        markup = (
            answer_keyboard(notification.session_id)
            if notification.recipient_kind == RECIPIENT_TEACHER
            else None
        )
        try:
            await bot.send_message(
                chat_id=notification.recipient_tg_id,
                text=notification.text,
                reply_markup=markup,
            )
        except TelegramAPIError as error:
            # The claim stays taken.  Re-sending on the next run would mean re-sending to
            # everyone whose delivery merely raced a network blip, and a blocked bot stays
            # blocked -- so the failure is REPORTED rather than retried in a loop nobody
            # is watching.
            failed += 1
            errors.append(
                "%s %d: %s" % (notification.recipient_kind, notification.recipient_id, error)
            )
            continue
        sent += 1

    return SendReport(
        session_id=session_id,
        planned=len(plan.notifications),
        sent=sent,
        already=already,
        unreachable=unreachable,
        failed=failed,
        errors=errors,
    )


# ------------------------------------------------------------------------ the answer


def build_router() -> Router:
    """One role-gated router, so ``bot/app.build`` gains one include.

    Built per dispatcher rather than kept as a module global: a ``Router`` remembers the
    dispatcher it was attached to and refuses to be attached twice.  Same choice, and the
    same reason, as ``bot/routers/views.build_router``.
    """
    router = Router(name="uvedomlenia")
    router.callback_query.middleware(require_role(*TEACHER_ROLES))
    router.callback_query.register(answer_attendance, Yavka.filter())
    return router


async def answer_attendance(
    query: CallbackQuery,
    callback_data: Yavka,
    identity,
    svodka: SvodkaService,
) -> None:
    """Record the teacher's own answer and say so, once.

    THE TEACHER IS TAKEN FROM THE IDENTITY, NEVER FROM THE PAYLOAD.  ``callback_data`` is
    client-side data: a payload naming somebody else's teacher id, typed out of a
    screenshot, is a request this server really receives, and the fact that no such button
    was drawn is not a defence.  The payload therefore carries only the lesson and the
    answer, and whose answer it is comes from the account that sent it.

    The reply is a fact and a thank-you, never an instruction to go and mark things: the
    question was about presence and the answer «не был» closes it completely.
    """
    teacher_id = _teacher_id_of(identity)
    if teacher_id is None:
        await query.answer(
            "Не вижу вас в списке преподавателей. Если вы отправляли заявку — "
            "дождитесь, пока владелец её подтвердит.",
            show_alert=True,
        )
        return
    if callback_data.answer not in ANSWERS:
        # A payload from a schema this bot does not have.  Refused rather than folded
        # into one of the two -- ``answer`` is typed ``int`` and an int field accepts 7
        # as readily as 0.
        await query.answer(
            "Кнопка из старой версии бота — она больше не работает. Отметить "
            "эту явку самому больше нечем: скажите о ней владельцу.",
            show_alert=True,
        )
        return
    if not ids_are_storable(callback_data.session_id, teacher_id):
        await query.answer(
            "Кнопка из старой версии бота — она больше не работает. Отметить "
            "эту явку самому больше нечем: скажите о ней владельцу.",
            show_alert=True,
        )
        return

    status = PRESENT if callback_data.answer == ANSWER_PRESENT else ABSENT
    try:
        svodka.record_presence(callback_data.session_id, teacher_id, status)
    except SvodkaError:
        await query.answer(
            "Это занятие уже не найти — записи о нём в журнале нет. Отметить "
            "явку по нему нельзя: скажите о ней владельцу.",
            show_alert=True,
        )
        return

    await _replace(query, "Записали: %s. Спасибо." % status)
    await query.answer()


def _teacher_id_of(identity) -> Optional[int]:
    """The teacher id behind the account, or ``None`` if this account is not a teacher.

    The owner reaches this handler through ``TEACHER_ROLES`` and may have no teacher
    binding at all; that is a legitimate state and is answered rather than raised.
    """
    binding = getattr(identity, "teacher", None)
    return getattr(binding, "teacher_id", None) if binding is not None else None


async def _replace(query: CallbackQuery, text: str) -> None:
    """Redraw the question as its own answer, so the buttons cannot be tapped again.

    Editing rather than sending a second message is what makes the exchange one message
    long: the teacher's chat keeps a single line saying what was recorded, instead of a
    question and a reply he has to read in order.
    """
    message = query.message
    if message is None:
        return
    try:
        await message.edit_text(text, reply_markup=None)
    except TelegramBadRequest as error:
        # A redraw that changes nothing is the double-tap path and is not a failure.
        if NOT_MODIFIED not in str(error):
            raise
