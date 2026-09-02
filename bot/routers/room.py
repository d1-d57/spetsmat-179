"""The head's screen, wired to the dispatcher.

The head opens ``/auditoria`` at the start of a lesson and runs the next ninety minutes
from the one message it draws.  Marking who came, bringing a child in from another room,
handing a child to another teacher for tonight -- all three happen without leaving it,
because an extra level of navigation costs a full cycle of attention and the head is
standing in front of eighteen people while he taps.

WHAT THIS ROUTER GUARANTEES, AND WHERE EACH GUARANTEE ACTUALLY LIVES
--------------------------------------------------------------------------------

1. **The screen is redrawn from the database, never from remembered state.**  Every
   handler ends by asking ``RoomService`` for the day again and drawing what came back.
   Six teachers work in one room and two heads may hold the same room open; a screen
   drawn from a remembered roster would show each of them a different truth and neither
   would have any way to notice.

2. **``answer()`` before the redraw, always.**  The redraw is an API round-trip and the
   callback query expires in fifteen seconds; at 800 ms a person cannot tell whether the
   tap counted and taps again.  The toast states the fact -- «отмечен» -- and never a
   word of praise.

3. **No confirmation dialogs anywhere.**  A confirmation does not catch a slip: it is
   dismissed by the same reflex that produced the slip.  A repeat tap undoes, which is
   why every payload names a TARGET state and not an operation.

4. **A student cannot reach this screen at all.**  The gate admits ``head`` and ``owner``
   and nobody else -- not a plain teacher either, whose version of this screen does not
   exist in this position.  The rule is «students do not reach this screen» rather than
   «refuse when the id is not yours», because the second shape has to be right on every
   handler and is one forgotten call away from leaking.

5. **The room is not in any payload and neither is the day.**  The room comes from the
   head's own teacher binding, the day from the clock.  A forged ``callback_data`` has
   nothing in it with which to reach another room or another evening: there is nothing
   to forge, which is P4's rule applied to the two fields that would matter here.

WHAT THIS ROUTER CANNOT DO, BY CONSTRUCTION.  It holds no enrollment service and imports
none.  Tonight's assignment and the standing arrangement are different facts about the
world, and the standing one is unreachable from this file rather than merely left alone
by it.
"""

from __future__ import annotations

from typing import Optional

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from bot.callbacks import ids_are_storable
from bot.keyboards.room import (
    ATTENDANCE_OPS,
    OP_CAME,
    STANDING_TEACHER,
    AddGuest,
    OpenAssignments,
    OpenGuests,
    OpenRoom,
    PickTeacher,
    Present,
    SetTeacher,
    assignments_header,
    assignments_keyboard,
    attendance_toast,
    guest_toast,
    guests_header,
    guests_keyboard,
    room_header,
    room_keyboard,
    teacher_toast,
    teachers_header,
    teachers_keyboard,
)
from bot.middleware import require_role
# The substring, not a second copy of it.  P4 measured it against the live API and owns
# the constant; spelling it again here would be a second opinion about somebody else's
# measurement, and the two would drift the first time Telegram reworded anything.
from bot.routers.marking import NOT_MODIFIED
from core.services.room import RoomDay, RoomError, RoomService

#: Who may see this screen.  A head, and the owner.  NOT a plain teacher: this screen
#: shows a whole room at once and is the instrument of the person who distributes it.
#: NOT a student, under any circumstance -- it puts eighteen children side by side, and
#: §3 of the brief forbids showing one child a statement about another.
ROOM_ROLES = ("head", "owner")

#: The command that opens it.
ENTRY_COMMAND = "/auditoria"


def build_router() -> Router:
    """A fresh router per dispatcher, for the reason ``marking.build_routers`` gives.

    A module-level ``Router()`` remembers the dispatcher it was attached to and refuses
    to be attached twice, which is why P3's fixtures have to reach into
    ``module.router._parent_router`` and null it.  A factory costs one line at the call
    site and removes the shared global that caused it.

    ONE router and no catch-all of its own: P4's catch-all already answers every callback
    nobody claimed, and a second one would have to be «last» at the same time as the
    first.
    """
    router = Router(name="room")
    router.message.middleware(require_role(*ROOM_ROLES))
    router.callback_query.middleware(require_role(*ROOM_ROLES))
    router.message.register(open_room, F.text == ENTRY_COMMAND)
    router.callback_query.register(show_room, OpenRoom.filter())
    router.callback_query.register(set_present, Present.filter())
    router.callback_query.register(show_guests, OpenGuests.filter())
    router.callback_query.register(add_guest, AddGuest.filter())
    router.callback_query.register(show_assignments, OpenAssignments.filter())
    router.callback_query.register(pick_teacher, PickTeacher.filter())
    router.callback_query.register(set_teacher, SetTeacher.filter())
    return router


# ------------------------------------------------------------------ who is asking

def _binding(identity, roster):
    """The head's own teacher row: which room he heads, and which teacher he is.

    The middleware short-circuits on the owner's ``tg_id`` and stamps an identity with no
    teacher on it, so the owner's binding is looked up here instead of being assumed
    absent.  An owner who is also bound to a room gets that room; an owner who is bound to
    none is told so in one sentence rather than shown somebody else's room by a guess.
    """
    teacher = getattr(identity, "teacher", None)
    if teacher is not None:
        return teacher
    if identity is not None and identity.kind == "owner":
        return roster.role_of_teacher(identity.tg_id)
    return None


NO_ROOM = (
    "Этот экран открывается для аудитории, а ваша учётная запись ни к одной не привязана."
)


def _room_of(identity, roster) -> Optional[str]:
    binding = _binding(identity, roster)
    return getattr(binding, "room", None) if binding is not None else None


def _host_teacher_id(identity, roster) -> Optional[int]:
    binding = _binding(identity, roster)
    return getattr(binding, "teacher_id", None) if binding is not None else None


# --------------------------------------------------------------------- drawing

def _editable(query: CallbackQuery) -> Optional[Message]:
    """The message to redraw, or ``None`` when Telegram handed us one we cannot edit.

    A callback can arrive attached to an ``InaccessibleMessage`` -- too old, or from a
    chat the bot was re-added to.  It has no ``edit_text``, and reaching for it raises
    inside the handler, i.e. a spinner that never stops.
    """
    message = query.message
    return message if isinstance(message, Message) else None


async def _redraw(message: Message, text: str, markup: InlineKeyboardMarkup) -> None:
    """Redraw the ONE message the head is working in, in place.

    ``message is not modified`` is matched as a SUBSTRING and swallowed; every other
    ``TelegramBadRequest`` is re-raised, because a deleted message, an over-long payload
    and an expired query all arrive as that one exception type and a bare ``except`` would
    hide every API failure this screen can have.
    """
    try:
        await message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as error:
        if NOT_MODIFIED not in str(error).lower():
            raise


def _compose_room(room_service: RoomService, room_day: RoomDay):
    return (
        room_header(room_day, room_service.teacher_names(room_day)),
        room_keyboard(room_day),
    )


def _compose_assignments(room_service: RoomService, room_day: RoomDay):
    return (
        assignments_header(room_day, room_service.teacher_names(room_day)),
        assignments_keyboard(room_day),
    )


async def _draw_room(query: CallbackQuery, room_service: RoomService, room_day: RoomDay) -> None:
    message = _editable(query)
    if message is None:
        return
    text, markup = _compose_room(room_service, room_day)
    await _redraw(message, text, markup)


async def _refuse_as_stale(query: CallbackQuery) -> None:
    """The answer to a payload that parsed but cannot MEAN anything here.

    Three shapes reach this, and all three really are «a button from a schema or a room this
    server does not have»: an ``op`` outside ``ATTENDANCE_OPS``, an id wider than the store
    can hold, and an id naming somebody who is not on this screen at all.  None of them may
    be folded into a nearby meaning: an unknown ``op`` folded into «away» would let a
    payload ERASE an attendance mark, and an id wider than 64 bits raises inside the query,
    after the handler started and before it answered.
    """
    await query.answer(RoomError.told, show_alert=True)


async def _refuse(query: CallbackQuery, refusal: RoomError) -> None:
    """The answer to a request the DOMAIN refused, in the domain's own words.

    Not «экран устарел».  The screen is two seconds old, the button was drawn for this very
    room, and the head asked for something the room will not do -- «он сегодня в другой
    аудитории», «этот ученик больше не занимается».  Telling him to reopen a screen that was
    never the problem sends him round a loop that changes nothing and teaches him nothing;
    the long form of the same refusal, with the ids in it, goes on carrying the detail for
    whoever reads the log.
    """
    await query.answer(refusal.told, show_alert=True)


# ------------------------------------------------------------------------ handlers

async def open_room(message: Message, identity, roster, room_service: RoomService) -> None:
    """The entry.  One message, and the head works in it for the whole lesson."""
    room = _room_of(identity, roster)
    if room is None:
        await message.answer(NO_ROOM)
        return
    room_day = room_service.room_day(
        room, host_teacher_id=_host_teacher_id(identity, roster)
    )
    text, markup = _compose_room(room_service, room_day)
    await message.answer(text, reply_markup=markup)


async def show_room(query: CallbackQuery, identity, roster, room_service: RoomService) -> None:
    """«← назад» from either second screen, and the redraw after a guest is brought in."""
    room = _room_of(identity, roster)
    if room is None:
        await query.answer(NO_ROOM, show_alert=True)
        return
    await query.answer()
    await _draw_room(
        query,
        room_service,
        room_service.room_day(room, host_teacher_id=_host_teacher_id(identity, roster)),
    )


async def set_present(
    query: CallbackQuery,
    callback_data: Present,
    identity,
    roster,
    room_service: RoomService,
) -> None:
    """One tap on one child.

    THE ORDER OF THE THREE BEATS IS THE POINT: write, then answer, then redraw.  The write
    is a local transaction measured in microseconds and is what the toast has to be
    truthful about; the toast is the immediate feedback that stops a second tap; the
    redraw is the round-trip that may be slow and must not stand in front of either.
    """
    room = _room_of(identity, roster)
    if room is None:
        await query.answer(NO_ROOM, show_alert=True)
        return
    # Before any read and before the toast: an unknown ``op`` must not become «away».
    if callback_data.op not in ATTENDANCE_OPS:
        await _refuse_as_stale(query)
        return
    if not ids_are_storable(callback_data.student_id):
        await _refuse_as_stale(query)
        return

    host_teacher_id = _host_teacher_id(identity, roster)
    room_day = room_service.room_day(room, host_teacher_id=host_teacher_id)
    member = room_day.member(callback_data.student_id)
    if member is None:
        await _refuse_as_stale(query)
        return

    came = callback_data.op == OP_CAME
    try:
        room_day = room_service.set_present(
            room_day, callback_data.student_id, came, host_teacher_id=host_teacher_id
        )
    except RoomError as refusal:
        await _refuse(query, refusal)
        return

    await query.answer(attendance_toast(member, came=came))
    await _draw_room(query, room_service, room_day)


async def show_guests(
    query: CallbackQuery, identity, roster, room_service: RoomService
) -> None:
    """«+ гость» — the children who are not on this screen yet, by surname."""
    room = _room_of(identity, roster)
    if room is None:
        await query.answer(NO_ROOM, show_alert=True)
        return
    await query.answer()
    message = _editable(query)
    if message is None:
        return
    room_day = room_service.room_day(
        room, host_teacher_id=_host_teacher_id(identity, roster)
    )
    await _redraw(
        message,
        guests_header(room_day),
        guests_keyboard(room_service.candidate_guests(room_day)),
    )


async def add_guest(
    query: CallbackQuery,
    callback_data: AddGuest,
    identity,
    roster,
    catalogue,
    room_service: RoomService,
) -> None:
    """Bring a child of another room in for tonight, and go straight back to the room.

    To the HEAD's own hands, in one tap.  He is standing in the room with the child in
    front of him; choosing a teacher is the «назначения» tap he already knows, and putting
    a chooser here would put a second level in the one path that is walked while somebody
    waits in the doorway.
    """
    room = _room_of(identity, roster)
    if room is None:
        await query.answer(NO_ROOM, show_alert=True)
        return
    if not ids_are_storable(callback_data.student_id):
        await _refuse_as_stale(query)
        return
    host_teacher_id = _host_teacher_id(identity, roster)
    if host_teacher_id is None:
        # A head with no teacher row of his own has nobody to hand the guest to, and
        # inventing one of his teachers would be the screen deciding something the head
        # did not.  Said out loud rather than failing silently on the tap.
        await query.answer(
            "Гостя некому передать: за вами не закреплён преподавательский профиль.",
            show_alert=True,
        )
        return

    room_day = room_service.room_day(room, host_teacher_id=host_teacher_id)
    try:
        room_day = room_service.add_guest(
            room_day,
            callback_data.student_id,
            host_teacher_id,
            host_teacher_id=host_teacher_id,
        )
    except RoomError as refusal:
        await _refuse(query, refusal)
        return

    await query.answer(guest_toast(catalogue.student(callback_data.student_id)))
    await _draw_room(query, room_service, room_day)


async def show_assignments(
    query: CallbackQuery, identity, roster, room_service: RoomService
) -> None:
    """«назначения» — tonight's distribution, read by teacher rather than by child."""
    room = _room_of(identity, roster)
    if room is None:
        await query.answer(NO_ROOM, show_alert=True)
        return
    await query.answer()
    message = _editable(query)
    if message is None:
        return
    room_day = room_service.room_day(
        room, host_teacher_id=_host_teacher_id(identity, roster)
    )
    text, markup = _compose_assignments(room_service, room_day)
    await _redraw(message, text, markup)


async def pick_teacher(
    query: CallbackQuery,
    callback_data: PickTeacher,
    identity,
    roster,
    room_service: RoomService,
) -> None:
    """Whom shall this child work with tonight?  The teachers of THIS room, and no others."""
    room = _room_of(identity, roster)
    if room is None:
        await query.answer(NO_ROOM, show_alert=True)
        return
    if not ids_are_storable(callback_data.student_id):
        await _refuse_as_stale(query)
        return
    room_day = room_service.room_day(
        room, host_teacher_id=_host_teacher_id(identity, roster)
    )
    member = room_day.member(callback_data.student_id)
    if member is None:
        await _refuse_as_stale(query)
        return
    await query.answer()
    message = _editable(query)
    if message is None:
        return
    names = room_service.teacher_names(room_day)
    await _redraw(
        message,
        teachers_header(member, names),
        teachers_keyboard(room_day, member, names),
    )


async def set_teacher(
    query: CallbackQuery,
    callback_data: SetTeacher,
    identity,
    roster,
    room_service: RoomService,
) -> None:
    """Hand a child to another teacher of this room, for tonight only.

    ``teacher_id == STANDING_TEACHER`` gives him back.  Not one line of ``enrollment`` is
    written on either path -- there is no port on the service that could -- so «who taught
    him in October» still answers with the teacher who actually did.

    Back to the ROOM afterwards and not to the distribution, because the move is over: the
    head made it in order to carry on running the lesson, and returning him to the list he
    just used would cost him a tap to get out of it.
    """
    room = _room_of(identity, roster)
    if room is None:
        await query.answer(NO_ROOM, show_alert=True)
        return
    if not ids_are_storable(callback_data.student_id, callback_data.teacher_id):
        await _refuse_as_stale(query)
        return

    host_teacher_id = _host_teacher_id(identity, roster)
    room_day = room_service.room_day(room, host_teacher_id=host_teacher_id)
    member = room_day.member(callback_data.student_id)
    if member is None:
        await _refuse_as_stale(query)
        return

    teacher_id = None if callback_data.teacher_id == STANDING_TEACHER else callback_data.teacher_id
    names = room_service.teacher_names(room_day)
    try:
        room_day = room_service.set_today_teacher(
            room_day,
            callback_data.student_id,
            teacher_id,
            host_teacher_id=host_teacher_id,
        )
    except RoomError as refusal:
        await _refuse(query, refusal)
        return

    await query.answer(teacher_toast(member, names, teacher_id))
    await _draw_room(query, room_service, room_day)
