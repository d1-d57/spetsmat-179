"""The head's screen: eighteen children, six teachers, ninety minutes.

    Аудитория 303 · четверг, 4 сентября · пришли 14 из 18
    гости сегодня: Кахиани (Даня)
    сегодня иначе: Быков → Ян

    [✅Агаркова 3][Аникина 0 ][✅Быков 7 ][Жуков 2   ]
    [Искеева 1   ][✅Кудишин 4][Лим 0    ][✅Пирогов 5]
    ...
    [+ гость][назначения]

FOUR PROPERTIES, AND EACH IS A CONSEQUENCE RATHER THAN A TASTE.

**The number on a button is the DEBT COUNT, and nothing stands beside it.**  It is a work
item -- it says which child to send a teacher to next -- and the moment anything else is
written there (a share of the room, a colour, a place in an ordering) it stops being a
work item and becomes a statement about one child in front of seventeen others.  This
screen is where that temptation is strongest, because it shows them all at once, and the
prohibition therefore has a carrier here and not only in the brief.

**The order is by SURNAME and can never be by the number.**  It is the order the head
already holds in his head, it does not move when a child hands work in, and a screen
sorted by debts would be an ordering of children by achievement shown to a room.  The
service sorts too; the rule is enforced in BOTH places on purpose, because the keyboard
is where somebody will one day think "it would be handier if the ones who owe most came
first".

**The situation is stated in the TEXT, the buttons stay clean.**  Who is a guest and who
was handed to another teacher tonight are facts the head needs, and hanging a second
glyph on eighteen four-across buttons would cost more legibility than the facts are
worth.  Lines above the grid say them in words; the buttons carry a name, a state and a
number.

**Every button names the state it will produce.**  ``✅Быков 7`` offers to take the mark
back, a plain ``Жуков 2`` offers to set it -- the payload carries the TARGET, exactly as
``bot/callbacks.py`` lays down, so two taps racing each other ask for the same world and
the second writes what the first already wrote.

Nothing here reads a database.  Every function is a pure function of a ``RoomDay``, which
is what lets the tests walk eighteen children through the real builder with no event loop.
"""

from __future__ import annotations

from typing import Iterable, Optional, Sequence

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import config
from bot.callbacks import Noop
from bot.keyboards.grid import FILLER_LABEL, button, rows_of
from core.models import Student
from core.services.room import RoomDay, RoomMember, day_in_words

#: The two target states an attendance button can name.  The same shape as the grid's
#: ``OP_CLEAR`` / ``OP_SOLVE`` and for the same reason: an integer, because a payload
#: carries numbers only, and a TARGET, because a "toggle" is what makes a double tap a
#: race instead of a repetition.
OP_AWAY = 0
OP_CAME = 1

#: The only two values ``Present.op`` may carry.  ``op`` is typed ``int`` and an ``int``
#: field accepts ``7`` and ``-3`` as readily as ``0``; the router refuses anything else
#: rather than folding it into one of the two, because folding an unknown ``op`` into
#: ``OP_AWAY`` would let a payload from no schema this bot has ERASE an attendance mark.
ATTENDANCE_OPS = (OP_AWAY, OP_CAME)

#: ``SetTeacher.teacher_id`` carrying this means «give him back to his standing teacher».
#: Zero and not ``None``: a ``CallbackData`` field of type ``int`` renders ``None`` as an
#: empty segment, and an empty segment is a string shape rather than a number.  No teacher
#: can collide with it -- ``teachers.id`` is an ``integer primary key``, which SQLite
#: assigns from 1 upward.
STANDING_TEACHER = 0

#: What a marked child looks like.  The grid's marker for a credited cell, because it is
#: the same fact in the same bot -- «this is done» -- and a second glyph for it would be a
#: second vocabulary the head has to hold.
PRESENT_MARKER = "✅"

#: A standing child of this room whom another room has taken tonight.  He keeps his place
#: in the list -- a child who quietly dropped off his own room's screen is the child nobody
#: goes looking for -- and the arrow says he is not here to be marked.
ELSEWHERE_MARKER = "→"

#: Surnames do not go four across, so the two screens that are LISTS of people use two
#: columns.  The room screen itself keeps ``config.GRID_COLUMNS``: it shows a surname and
#: one digit, which is what four columns were measured for.
LIST_COLUMNS = 2


# ------------------------------------------------------------------------- payloads
#
# They live here rather than in ``bot/callbacks.py`` because that file belongs to P4 and
# is read-only for this position.  They are the SAME idiom, not a second one: a
# ``CallbackData`` factory, numbers only, a target state and never an operation to apply
# to whatever the server finds, and built through ``bot.keyboards.grid.button``, which is
# where the 64-byte law has its carrier.
#
# NEITHER THE ROOM NOR THE DAY IS IN ANY PAYLOAD, and that is this screen's privacy
# boundary rather than an economy.  The room comes from the head's own teacher binding
# and the day comes from the clock, so a forged ``callback_data`` has nothing in it with
# which to reach another room or another evening.  It is P4's rule -- the decision never
# consults the id -- applied to the two fields that would matter here.

class Present(CallbackData, prefix="ra"):
    """One tap on one child: «he is here» / «I tapped the wrong child».  ``ra:56:1``.

    ``op`` is the TARGET.  ``1`` means the child must end up marked; ``0`` means the mark
    must be gone -- gone, not replaced by a positive «did not come», because the head who
    untaps is correcting himself, not making a claim about a child who is not in the room.
    """

    student_id: int
    op: int


class OpenRoom(CallbackData, prefix="rb"):
    """«назад» from either second screen, and the redraw after any of them.  ``rb``."""


class OpenGuests(CallbackData, prefix="rl"):
    """«+ гость»: offer the children who are not on this screen yet.  ``rl``."""


class AddGuest(CallbackData, prefix="rg"):
    """Bring this child in for tonight, to the head's own hands.  ``rg:56``.

    One tap and no teacher chooser, because the head is standing in the room and can hand
    the child on with the same «назначения» tap he uses for anybody else.  A chooser here
    would be a second level in the path that is walked when a child is already waiting in
    the doorway.
    """

    student_id: int


class OpenAssignments(CallbackData, prefix="rn"):
    """«назначения»: tonight's distribution, and whom to move.  ``rn``."""


class PickTeacher(CallbackData, prefix="rw"):
    """Whom shall this child work with tonight?  ``rw:56``."""

    student_id: int


class SetTeacher(CallbackData, prefix="rt"):
    """Hand this child to this teacher, for tonight only.  ``rt:56:12``.

    ``teacher_id=STANDING_TEACHER`` gives him back to his standing teacher.  The payload
    names WHOM, never «the next one» or «the other one»: a payload that had to be resolved
    against a distribution which may have changed since the screen was drawn would move a
    child from a position the head is no longer looking at.
    """

    student_id: int
    teacher_id: int


# -------------------------------------------------------------------------- helpers

def _filler() -> InlineKeyboardButton:
    """The padding of a short last row.

    Telegram stretches a short row across the whole message, so a last row of two would
    be visibly wider than the four-wide rows above it -- which destroys the very geometry
    the column count exists to protect.  It carries ``Noop``, a real payload with a real
    handler, so an accidental tap stops the spinner and changes nothing.
    """
    return button(FILLER_LABEL, Noop().pack())


def _padded(buttons: Sequence[InlineKeyboardButton], width: int) -> list:
    rows = []
    for row in rows_of(list(buttons), width):
        while len(row) < width:
            row.append(_filler())
        rows.append(row)
    return rows


def _by_surname(members: Iterable[RoomMember]) -> list:
    """Surname, given name, id -- and NEVER the debt count.

    ``RoomService`` sorts by the same key before it hands the day over.  Sorting again
    here is not distrust of it: this is the module where the ordering would be changed if
    anybody ever changed it, so this is where the rule needs a carrier of its own.
    """
    return sorted(members, key=lambda member: member.sort_key)


def _label(member: RoomMember) -> str:
    """«✅Агаркова 3» -- a mark, a surname and the debt count.

    The number is the count of obligatory problems still owed on older sheets, computed by
    ``core/services/progress.py`` and asked for, never recomputed.  Nothing else is
    written beside it and nothing may be: a count is a work item, and the moment it
    acquires a neighbour it becomes a comparison between children.
    """
    if member.is_elsewhere:
        marker = ELSEWHERE_MARKER
    elif member.present:
        marker = PRESENT_MARKER
    else:
        marker = ""
    return "%s%s %d" % (marker, member.student.surname, member.debts)


def _name_of(student: Optional[Student]) -> str:
    if student is None:
        return "ученик"
    return ("%s %s" % (student.surname, student.name)).strip()


def _teacher_name(teacher_names: dict, teacher_id: Optional[int]) -> str:
    if teacher_id is None:
        return "без преподавателя"
    return teacher_names.get(teacher_id) or ("преподаватель %d" % teacher_id)


# ---------------------------------------------------------------------- the room

def room_header(room_day: RoomDay, teacher_names: dict) -> str:
    """The situation, in as many lines as the situation actually has.

    The first line is always there and answers the three questions the head would
    otherwise count out by hand: which room he is looking at, whether it is today, and how
    many of his people have arrived.  «пришли 14 из 18» is a count of the room in front of
    him -- it compares nobody with anybody, and it is the number that tells him whether to
    start.

    The other two lines appear only when there is something to say.  A room with no guests
    and no moves shows one line, which is the common evening and should look calm.
    """
    lines = [
        "Аудитория %s · %s · пришли %d из %d"
        % (room_day.room, day_in_words(room_day.day), room_day.came, room_day.total)
    ]

    guests = [member for member in _by_surname(room_day.members) if member.is_guest]
    if guests:
        lines.append(
            "гости сегодня: %s"
            % ", ".join(
                "%s (%s)" % (member.student.surname, _teacher_name(teacher_names, member.teacher_id))
                for member in guests
            )
        )

    moved = [member for member in _by_surname(room_day.members) if member.is_moved_today]
    if moved:
        lines.append(
            "сегодня иначе: %s"
            % ", ".join(
                "%s → %s" % (member.student.surname, _teacher_name(teacher_names, member.teacher_id))
                for member in moved
            )
        )

    # The children this room has TONIGHT LOST to another one.  Said out loud, with the name
    # of the teacher who has them: without this line they simply stopped appearing in the
    # distribution, which is precisely how a child gets forgotten for ninety minutes.
    elsewhere = _by_surname(room_day.elsewhere)
    if elsewhere:
        lines.append(
            "сегодня в другой аудитории: %s"
            % ", ".join(
                "%s (%s)" % (member.student.surname, _teacher_name(teacher_names, member.teacher_id))
                for member in elsewhere
            )
        )
    return "\n".join(lines)


def room_keyboard(room_day: RoomDay, *, columns: Optional[int] = None) -> InlineKeyboardMarkup:
    """The children, four across, then the two things the head does without leaving.

    ``columns`` exists so the layout test can prove that the WIDTH drives the shape;
    production passes ``None`` and gets ``config.GRID_COLUMNS``, which is a thumb target
    of 9.2-9.6 mm on a phone held one-handed and not a number anybody may retype here.
    """
    width = config.GRID_COLUMNS if columns is None else columns
    cells = [
        button(
            _label(member),
            Present(
                student_id=member.student.id,
                # The OPPOSITE of what stands now: the only tap that changes anything.
                op=OP_AWAY if member.present else OP_CAME,
            ).pack(),
        )
        for member in _by_surname(room_day.members)
    ]
    keyboard = _padded(cells, width)
    # A FOOTER, not a row of the grid: it is allowed to be narrower, exactly as the
    # navigation row of the problem grid is, and the layout test checks the grid rows.
    keyboard.append(
        [
            button("+ гость", OpenGuests().pack()),
            button("назначения", OpenAssignments().pack()),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# --------------------------------------------------------------------- the guests

def guests_header(room_day: RoomDay) -> str:
    """Says the thing the head is actually worried about before he taps.

    «Он останется в своей группе» is not reassurance: it is the fact that makes the tap
    safe to make quickly, and a head who does not know it will avoid the button and write
    the child down on paper instead.
    """
    return (
        "Аудитория %s · %s · кого добавить на сегодня?\n"
        "Он останется в своей группе — постоянное закрепление не меняется."
        % (room_day.room, day_in_words(room_day.day))
    )


def guests_keyboard(students: Iterable[Student]) -> InlineKeyboardMarkup:
    """Everybody who is not on the room screen yet, by surname, two across.

    Two columns rather than four: these buttons carry a full surname and a given name's
    initial is not enough to tell two Ивановых apart, so the room's width would cut the
    names instead of the list.
    """
    cells = [
        button(
            _name_of(student),
            AddGuest(student_id=student.id).pack(),
        )
        for student in students
    ]
    keyboard = _padded(cells, LIST_COLUMNS)
    keyboard.append([button("← назад", OpenRoom().pack())])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ---------------------------------------------------------------- the assignments

def assignments_header(room_day: RoomDay, teacher_names: dict) -> str:
    """Tonight's distribution, read as the head thinks of it: by teacher, not by child.

    He is deciding where to put the next child, and the question he is answering is «who
    has room» -- which a list ordered by child does not answer at any glance.  Children
    inside a teacher's line stay in surname order, and the teachers are in the order the
    room reports them, so the block does not reshuffle itself between two taps.
    """
    lines = [
        "Аудитория %s · %s · назначения на сегодня"
        % (room_day.room, day_in_words(room_day.day))
    ]
    for teacher_id in room_day.teacher_ids:
        held = [
            member.student.surname
            for member in _by_surname(room_day.members)
            if member.teacher_id == teacher_id and not member.is_elsewhere
        ]
        lines.append(
            "%s: %s" % (_teacher_name(teacher_names, teacher_id), ", ".join(held) or "—")
        )
    # EVERY child of the room lands in exactly one line of this block, and the two lines
    # below are what make that true.  A child whose today-teacher works in another room used
    # to match no teacher's line and not the «без преподавателя» line either, so the block
    # said «15 из 18» without saying so -- three children present in the room's own list and
    # in none of its own rows.
    elsewhere = _by_surname(room_day.elsewhere)
    if elsewhere:
        lines.append(
            "сегодня в другой аудитории: %s"
            % ", ".join(
                "%s (%s)" % (member.student.surname, _teacher_name(teacher_names, member.teacher_id))
                for member in elsewhere
            )
        )
    orphans = [
        member.student.surname
        for member in _by_surname(room_day.members)
        if member.teacher_id is None
    ]
    if orphans:
        # Not silently folded into somebody's line.  A child the room cannot name a
        # teacher for is exactly the child who will be forgotten for ninety minutes.
        lines.append("без преподавателя: %s" % ", ".join(orphans))
    lines.append("Кого передать другому преподавателю на сегодня?")
    return "\n".join(lines)


def assignments_keyboard(
    room_day: RoomDay, *, columns: Optional[int] = None
) -> InlineKeyboardMarkup:
    """The same children in the same places as on the room screen.

    Deliberately the same order and the same width: the head has just been looking at that
    arrangement, and a second screen that re-sorted the same eighteen people would cost
    him the position of every one of them.
    """
    width = config.GRID_COLUMNS if columns is None else columns
    cells = [
        button(member.student.surname, PickTeacher(student_id=member.student.id).pack())
        for member in _by_surname(room_day.members)
    ]
    keyboard = _padded(cells, width)
    keyboard.append([button("← назад", OpenRoom().pack())])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def teachers_header(member: RoomMember, teacher_names: dict) -> str:
    """«Быков · сейчас у Ян · кому на сегодня?»"""
    return "%s · сейчас у %s · кому на сегодня?" % (
        _name_of(member.student),
        _teacher_name(teacher_names, member.teacher_id),
    )


def teachers_keyboard(
    room_day: RoomDay, member: RoomMember, teacher_names: dict
) -> InlineKeyboardMarkup:
    """The teachers of THIS room, and nobody else.

    A teacher is bound to a room for the whole year, so a chooser offering the teachers of
    another room would be offering a standing change wearing a today-only costume.  The
    one he is with now is marked and still tappable: tapping it asks for the world that
    already stands, which writes nothing -- the same law as every other button here.
    """
    cells = [
        button(
            "%s%s"
            % (
                PRESENT_MARKER if teacher_id == member.teacher_id else "",
                _teacher_name(teacher_names, teacher_id),
            ),
            SetTeacher(student_id=member.student.id, teacher_id=teacher_id).pack(),
        )
        for teacher_id in room_day.teacher_ids
    ]
    keyboard = _padded(cells, LIST_COLUMNS)
    if member.is_moved_today:
        # Offered only when there is something to undo, and never to a guest: his standing
        # arrangement is in another room, so «вернуть постоянному» would leave a child on
        # this screen belonging to nobody in it.
        keyboard.append(
            [
                button(
                    "вернуть постоянному",
                    SetTeacher(
                        student_id=member.student.id, teacher_id=STANDING_TEACHER
                    ).pack(),
                )
            ]
        )
    keyboard.append([button("← назад", OpenAssignments().pack())])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# --------------------------------------------------------------------- the toasts

def attendance_toast(member: RoomMember, *, came: bool) -> str:
    """The immediate answer to the tap: «Быков — отмечен».

    It fires BEFORE the redraw and it is not optional: at 800 ms a person cannot tell
    whether a tap counted and taps again.  It states the FACT and not a word of praise --
    the same prohibition as on the problem grid, and it bites harder here, because this
    screen is about children rather than about problems.

    TAKING THE MARK BACK ALSO DROPS TONIGHT'S MOVE, AND THE TOAST SAYS SO.  Presence and
    tonight's teacher are one row and the undo removes the row, so a head who untaps a child
    he moved five minutes ago loses the move -- silently, until this sentence.  He is told
    at the moment it happens rather than left to find out when the child is at the wrong
    table.
    """
    if came:
        return "%s — отмечен" % member.student.surname
    if member.is_moved_today:
        return "%s — отметка снята; сегодняшний перевод снят вместе с ней" % (
            member.student.surname,
        )
    return "%s — отметка снята" % member.student.surname


def guest_toast(student: Optional[Student]) -> str:
    return "%s — на сегодня в этой аудитории" % _name_of(student)


def teacher_toast(member: RoomMember, teacher_names: dict, teacher_id: Optional[int]) -> str:
    """«Быков — сегодня у Ян; постоянное закрепление не тронуто».

    The second half is said out loud on every single move, not once in a manual: the whole
    value of the feature is that it is safe to use, and a head who is not sure of that
    will not use it twice.
    """
    if teacher_id is None:
        return "%s — снова у постоянного преподавателя" % member.student.surname
    return "%s — сегодня у %s; постоянное закрепление не тронуто" % (
        member.student.surname,
        _teacher_name(teacher_names, teacher_id),
    )
