"""What this screen refuses, and what it refuses to break while refusing.

``callback_data`` is client-side data.  A payload naming somebody else's id is a request
the server really receives, and the answer this position gives is that there is nothing in
the payload worth forging: the room comes from the head's own teacher binding and the day
comes from the clock, so a forged id can only name a child who is not in this room
tonight -- and that is answered, not obeyed.

THREE REFUSALS THAT MUST NOT BE FOLDED INTO A NEARBY MEANING, because each of the three
used to be worse than the stale button they look like:

  * an ``op`` outside ``ATTENDANCE_OPS`` folded into «away» would let a payload from no
    schema this bot has ERASE an attendance mark;
  * an id wider than SQLite's 64 bits raises INSIDE the query -- after the handler has
    started and before it has answered -- so the spinner turns until Telegram gives up;
  * an id naming a child of another room, obeyed, would put him on this screen without
    anybody in this room having taken him.

And the role gate, which is the one refusal that matters most: this screen puts eighteen
children side by side, so a student must not reach it at all -- not a plain teacher either,
whose version of it does not exist in this position.
"""

from __future__ import annotations

from bot.callbacks import ID_MAX
from core.services.room import NoLongerHere, UnknownTeacher
from bot.keyboards.room import (
    OP_AWAY,
    OP_CAME,
    AddGuest,
    OpenGuests,
    Present,
    SetTeacher,
)
from conftest import (
    HEAD_TG_ID,
    ROOM,
    ROOM_SIZE,
    SECOND_TEACHER_TG_ID,
    TODAY,
    feed_callback,
    feed_message,
)

STALE = "устарел"


def _attendance_rows(connection) -> list:
    return [tuple(row) for row in connection.execute(
        "select session_id, student_id, teacher_id, status from attendance "
        "order by session_id, student_id"
    )]


def _day(dispatcher, room_world):
    return dispatcher.workflow_data["room_service"].room_day(
        ROOM, TODAY, host_teacher_id=room_world.head_teacher_id
    )


def test_a_confirmed_student_reaches_nothing_on_this_screen(
    connection, dispatcher, bot_instance, recorder, room_world
):
    roster = dispatcher.workflow_data["roster"]
    student_tg_id = 800001
    roster.confirm_student(
        roster.submit_student(tg_id=student_tg_id, surname="Ребёнок", name="Один")
    )

    before = _attendance_rows(connection)
    feed_message(dispatcher, bot=bot_instance, from_id=student_tg_id, text="/auditoria")
    feed_callback(
        dispatcher,
        bot=bot_instance,
        from_id=student_tg_id,
        data=Present(student_id=room_world.students[0], op=OP_CAME).pack(),
    )
    assert _attendance_rows(connection) == before
    assert not any("пришли" in text for text in recorder.texts()), (
        "a student was shown the room: %r" % (recorder.texts(),)
    )


def test_a_plain_teacher_has_no_version_of_this_screen(
    connection, dispatcher, bot_instance, recorder, room_world
):
    """The second teacher of the very same room is refused too.

    He is not a stranger and not a threat; the screen is simply the instrument of the
    person who distributes the room, and a second one that could redistribute it would be
    two people holding the same steering wheel.
    """
    before = _attendance_rows(connection)
    feed_message(dispatcher, bot=bot_instance, from_id=SECOND_TEACHER_TG_ID, text="/auditoria")
    feed_callback(
        dispatcher,
        bot=bot_instance,
        from_id=SECOND_TEACHER_TG_ID,
        data=Present(student_id=room_world.students[0], op=OP_CAME).pack(),
    )
    assert _attendance_rows(connection) == before
    assert not any("пришли" in text for text in recorder.texts())


def test_a_forged_id_naming_a_child_of_another_room_is_answered_and_not_obeyed(
    connection, dispatcher, bot_instance, recorder, room_world
):
    """He is not brought in by a payload: a guest arrives because somebody HERE took him.

    ``AddGuest`` is the tap that does that, and it writes the head's own teacher into the
    row.  ``Present`` on a child nobody took names nobody who is in this room.
    """
    outsider = room_world.outsiders[0]
    before = _attendance_rows(connection)
    recorder.clear()
    feed_callback(
        dispatcher,
        bot=bot_instance,
        from_id=HEAD_TG_ID,
        data=Present(student_id=outsider, op=OP_CAME).pack(),
    )
    assert any(STALE in alert for alert in recorder.alerts()), recorder.alerts()
    assert _attendance_rows(connection) == before
    assert _day(dispatcher, room_world).member(outsider) is None


def test_an_unknown_op_does_not_erase_a_mark_that_stands(
    connection, dispatcher, bot_instance, recorder, room_world
):
    student_id = room_world.students[0]
    feed_callback(
        dispatcher, bot=bot_instance, from_id=HEAD_TG_ID,
        data=Present(student_id=student_id, op=OP_CAME).pack(),
    )
    assert _day(dispatcher, room_world).member(student_id).present

    recorder.clear()
    feed_callback(
        dispatcher, bot=bot_instance, from_id=HEAD_TG_ID,
        data=Present(student_id=student_id, op=7).pack(),
    )
    assert any(STALE in alert for alert in recorder.alerts()), recorder.alerts()
    assert _day(dispatcher, room_world).member(student_id).present, (
        "an op outside the two known ones silently took the mark back"
    )


def test_an_id_wider_than_the_store_is_answered_before_it_can_raise(
    dispatcher, bot_instance, recorder, room_world
):
    """It fits the 64 BYTES, unpacks cleanly and passes every type check.

    Python integers have no 64-bit bound and SQLite's do, so without this refusal the id
    reaches a query and raises there -- inside a handler that has not answered yet.
    """
    recorder.clear()
    for data in (
        Present(student_id=ID_MAX + 1, op=OP_CAME).pack(),
        AddGuest(student_id=ID_MAX + 1).pack(),
        SetTeacher(student_id=ID_MAX + 1, teacher_id=1).pack(),
    ):
        feed_callback(dispatcher, bot=bot_instance, from_id=HEAD_TG_ID, data=data)
    alerts = recorder.alerts()
    assert len(alerts) == 3 and all(STALE in alert for alert in alerts), alerts


def test_a_child_cannot_be_handed_to_a_teacher_of_another_room(
    connection, dispatcher, bot_instance, recorder, room_world
):
    """A teacher is bound to a room for the year.

    Handing a child across rooms would be a standing change wearing a today-only costume,
    and it is refused in the service rather than merely omitted from the keyboard: the
    keyboard is what the head sees, and a payload is what the server gets.

    AND THE REFUSAL SAYS WHAT IT IS.  «Экран устарел» would be a false sentence about a
    screen two seconds old, and it would send the head round a loop that changes nothing:
    reopening the room offers him the same teachers, because the teacher he asked for is not
    one of them and never was.
    """
    student_id = room_world.students[0]
    before = _attendance_rows(connection)
    recorder.clear()
    feed_callback(
        dispatcher, bot=bot_instance, from_id=HEAD_TG_ID,
        data=SetTeacher(
            student_id=student_id, teacher_id=room_world.neighbour_teacher_id
        ).pack(),
    )
    assert recorder.alerts() == [UnknownTeacher.told], recorder.alerts()
    assert not any(STALE in alert for alert in recorder.alerts())
    assert _attendance_rows(connection) == before


def test_the_guest_list_offers_nobody_who_is_already_in_the_room(
    dispatcher, bot_instance, recorder, room_world
):
    room_service = dispatcher.workflow_data["room_service"]
    day = _day(dispatcher, room_world)
    candidates = room_service.candidate_guests(day)
    here = {member.student.id for member in day.members}
    assert here and not (here & {student.id for student in candidates})
    assert len(candidates) == ROOM_SIZE, (
        "expected the eighteen children of the room next door, got %d" % len(candidates)
    )

    recorder.clear()
    feed_callback(dispatcher, bot=bot_instance, from_id=HEAD_TG_ID, data=OpenGuests().pack())
    assert any("останется в своей группе" in text for text in recorder.texts()), (
        "the screen does not say the thing that makes the tap safe to make quickly"
    )


def test_taking_the_mark_back_removes_the_row_rather_than_asserting_absence(
    connection, dispatcher, bot_instance, room_world
):
    """«I tapped the wrong child» is an erratum, not a claim that anybody is absent.

    The negative status still exists in the schema, and a row carrying it -- written later
    by whoever closes the lesson -- reads here as not-present and is turned into «came» by
    one tap.  So the third state is handled without a third tap and without this screen
    ever writing it.
    """
    import config

    student_id = room_world.students[0]
    feed_callback(dispatcher, bot=bot_instance, from_id=HEAD_TG_ID,
                  data=Present(student_id=student_id, op=OP_CAME).pack())
    assert _attendance_rows(connection)

    feed_callback(dispatcher, bot=bot_instance, from_id=HEAD_TG_ID,
                  data=Present(student_id=student_id, op=OP_AWAY).pack())
    assert not [row for row in _attendance_rows(connection) if row[1] == student_id], (
        "the undo left a row behind: this screen must never write the negative status"
    )

    session_id = _day(dispatcher, room_world).session_id
    connection.execute(
        "insert into attendance (session_id, student_id, teacher_id, status) "
        "values (?, ?, ?, ?)",
        (session_id, student_id, None, config.ATTENDANCE_STATUSES[1]),
    )
    connection.commit()
    assert not _day(dispatcher, room_world).member(student_id).present

    feed_callback(dispatcher, bot=bot_instance, from_id=HEAD_TG_ID,
                  data=Present(student_id=student_id, op=OP_CAME).pack())
    assert _day(dispatcher, room_world).member(student_id).present


def test_a_child_who_has_left_is_refused_even_when_the_payload_names_him(
    connection, dispatcher, bot_instance, recorder, room_world
):
    """``candidate_guests`` leaves him out of the LIST; that is not the same as refusing him.

    The list covers the head who is looking at a fresh screen.  A stale screen and a forged
    payload are exactly the two cases a filter in the list cannot reach, and they are the
    two that reach the service.
    """
    room_service = dispatcher.workflow_data["room_service"]
    head = room_world.head_teacher_id
    departed = room_world.outsiders[0]
    connection.execute("update students set status = 'left' where id = ?", (departed,))
    connection.commit()

    day = room_service.room_day(ROOM, TODAY, host_teacher_id=head)
    assert departed not in {student.id for student in room_service.candidate_guests(day)}

    before = _attendance_rows(connection)
    recorder.clear()
    feed_callback(
        dispatcher, bot=bot_instance, from_id=HEAD_TG_ID,
        data=AddGuest(student_id=departed).pack(),
    )
    assert recorder.alerts() == [NoLongerHere.told], recorder.alerts()
    assert _attendance_rows(connection) == before
