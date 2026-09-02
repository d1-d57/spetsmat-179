"""The raskladka of the head's screen, over every button of every screen of this position.

FOUR PROPERTIES, EACH WITH A WAY OF BEING WRONG THAT NOBODY NOTICES BY EYE.

  * a payload over 64 BYTES -- the Bot API refuses the whole message and names neither the
    button nor the row; a Cyrillic character costs two bytes, so a check on CHARACTERS
    would pass while production failed;
  * a grid row that is not ``config.GRID_COLUMNS`` wide -- Telegram stretches a short row
    across the whole message, so a last row of two ends up visibly wider than the four
    above it and the thumb geometry the column count protects is gone;
  * children ordered by anything but surname -- an ordering by the debt count is an
    ordering of children by achievement, shown to a room of eighteen;
  * anything written beside the debt count -- the count is a work item; the moment it
    acquires a neighbour it becomes a statement about one child in front of the others.

The last one is checked by a REGULAR EXPRESSION over the finished label rather than by a
list of forbidden words.  A list is a list of the words somebody thought of; the shape
«mark, surname, number, nothing else» refuses the ones nobody thought of too -- and the
готовности gate greps this tree for the forbidden vocabulary, so a test could not spell
the words even to forbid them.

The counts are asserted before they are printed: zero buttons checked against a room of
eighteen is RED, not green.
"""

from __future__ import annotations

import re

import config
from bot.callbacks import CALLBACK_DATA_LIMIT_BYTES, ID_MAX
from bot.keyboards.room import (
    FILLER_LABEL,
    LIST_COLUMNS,
    PRESENT_MARKER,
    Present,
    SetTeacher,
    assignments_keyboard,
    guests_keyboard,
    room_keyboard,
    teachers_keyboard,
)
from conftest import ROOM, ROOM_SIZE, TODAY

#: «✅Агаркова 3» and «Аникина 0», and nothing else at all.  The surname may carry a
#: hyphen or a space; the number is a count of obligatory problems and is the last thing
#: on the button.
LABEL = re.compile(r"^(?:%s)?[^\d]+ \d+$" % re.escape(PRESENT_MARKER))


def _all_buttons(markup) -> list:
    return [button for row in markup.inline_keyboard for button in row]


def _over_limit(buttons) -> list:
    return [
        (button.text, button.callback_data)
        for button in buttons
        if len(button.callback_data.encode("utf-8")) > CALLBACK_DATA_LIMIT_BYTES
    ]


def test_every_button_of_every_room_screen_fits_the_byte_limit_and_the_four_columns(
    dispatcher, room_world, capsys
):
    room_service = dispatcher.workflow_data["room_service"]
    head = room_world.head_teacher_id
    day = room_service.room_day(ROOM, TODAY, host_teacher_id=head)
    names = room_service.teacher_names(day)

    screens = {
        "аудитория": room_keyboard(day),
        "гости": guests_keyboard(room_service.candidate_guests(day)),
        "назначения": assignments_keyboard(day),
        "преподаватели": teachers_keyboard(day, day.members[0], names),
    }

    buttons_checked = 0
    over_limit = []
    for markup in screens.values():
        buttons = _all_buttons(markup)
        buttons_checked += len(buttons)
        over_limit.extend(_over_limit(buttons))

    assert buttons_checked > 0, "no buttons were built: a green run here would prove nothing"
    assert not over_limit, "payloads over %d bytes: %r" % (
        CALLBACK_DATA_LIMIT_BYTES,
        over_limit[:5],
    )

    # The widest payload this schema can ever produce, at the widest id the store can
    # hold.  Built through the same factory, so the bound is checked against the shape
    # rather than against the ids that happen to be in the fixture.
    widest = SetTeacher(student_id=ID_MAX, teacher_id=ID_MAX).pack()
    assert len(widest.encode("utf-8")) <= CALLBACK_DATA_LIMIT_BYTES, (
        "the widest payload of this screen is %d bytes" % len(widest.encode("utf-8"))
    )

    # The grid rows of the room screen: everything above the «+ гость · назначения»
    # footer, which is a footer and is allowed to be narrower, exactly as the problem
    # grid's navigation row is.
    grid_rows = room_keyboard(day).inline_keyboard[:-1]
    not_four_wide = [
        [button.text for button in row]
        for row in grid_rows
        if len(row) != config.GRID_COLUMNS
    ]
    assert not not_four_wide, "rows not %d wide: %r" % (config.GRID_COLUMNS, not_four_wide)

    # The two list screens are two across for the same reason the room is four: a full
    # surname does not go four across, and a cut name is worse than a longer list.
    list_rows = guests_keyboard(room_service.candidate_guests(day)).inline_keyboard[:-1]
    assert all(len(row) == LIST_COLUMNS for row in list_rows)

    with capsys.disabled():
        print(
            "\n[раскладка аудитории] экранов %d из %d · кнопок проверено %d · "
            "превышений %d байт: %d · рядов не по %d: %d"
            % (
                len(screens), len(screens),
                buttons_checked,
                CALLBACK_DATA_LIMIT_BYTES, len(over_limit),
                config.GRID_COLUMNS, len(not_four_wide),
            )
        )


def test_the_children_stand_in_surname_order_and_never_in_debt_order(dispatcher, room_world):
    room_service = dispatcher.workflow_data["room_service"]
    day = room_service.room_day(
        ROOM, TODAY, host_teacher_id=room_world.head_teacher_id
    )

    labels = [
        button.text
        for row in room_keyboard(day).inline_keyboard[:-1]
        for button in row
        if button.text != FILLER_LABEL
    ]
    assert len(labels) == ROOM_SIZE

    surnames = [label.rsplit(" ", 1)[0].lstrip(PRESENT_MARKER) for label in labels]
    assert surnames == sorted(surnames), "the room is not in surname order: %r" % (surnames[:6],)

    # And the fixture's debts really do disagree with that order, so the assertion above
    # is not passing by accident on a room where the two orders coincide.
    debts = [int(label.rsplit(" ", 1)[1]) for label in labels]
    assert debts != sorted(debts) and debts != sorted(debts, reverse=True), (
        "every child owes the same or the two orders coincide: this test cannot tell "
        "surname order from debt order on such a room"
    )


def test_nothing_at_all_stands_beside_the_debt_count(dispatcher, room_world):
    """The button carries a mark, a surname and a number.  That is the whole vocabulary.

    Checked as a SHAPE and not as a list of forbidden words: a list forbids the words
    somebody thought of, and this screen is the one where somebody will think of a new one.
    """
    room_service = dispatcher.workflow_data["room_service"]
    day = room_service.room_day(
        ROOM, TODAY, host_teacher_id=room_world.head_teacher_id
    )
    offending = [
        button.text
        for row in room_keyboard(day).inline_keyboard[:-1]
        for button in row
        if button.text != FILLER_LABEL and not LABEL.match(button.text)
    ]
    assert not offending, "labels carrying more than a name and a count: %r" % (offending[:5],)


def test_the_button_names_the_state_it_will_produce(dispatcher, bot_instance, room_world):
    """A target, never a toggle -- which is what makes two taps in one second harmless.

    An unmarked child's button asks for «came»; once he is marked, the same cell asks for
    «the mark goes».  Two identical payloads arriving in either order therefore ask for the
    same world, and the second writes what the first already wrote.
    """
    from bot.keyboards.room import OP_AWAY, OP_CAME
    from conftest import HEAD_TG_ID, feed_callback

    room_service = dispatcher.workflow_data["room_service"]
    head = room_world.head_teacher_id
    student_id = room_world.students[0]

    def payload_for(sid):
        day = room_service.room_day(ROOM, TODAY, host_teacher_id=head)
        for row in room_keyboard(day).inline_keyboard[:-1]:
            for button in row:
                if button.callback_data.startswith("ra:%d:" % sid):
                    return Present.unpack(button.callback_data)
        raise AssertionError("no button for student %d" % sid)

    assert payload_for(student_id).op == OP_CAME
    feed_callback(dispatcher, bot=bot_instance, from_id=HEAD_TG_ID,
                  data=Present(student_id=student_id, op=OP_CAME).pack())
    assert payload_for(student_id).op == OP_AWAY

    # The same payload again: it asks for the world that already stands.
    feed_callback(dispatcher, bot=bot_instance, from_id=HEAD_TG_ID,
                  data=Present(student_id=student_id, op=OP_CAME).pack())
    day = room_service.room_day(ROOM, TODAY, host_teacher_id=head)
    assert day.member(student_id).present
    assert day.came == 1
