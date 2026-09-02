"""Two rooms wanting one child on one evening, and the teacher who holds nobody.

ONE CHILD IS AT ONE LESSON, SO ONE ``attendance`` ROW HOLDS HIM -- ``unique (session_id,
student_id)``.  When 303 takes a child of 304 as a guest, it is 304's row that changes.
Everything in this file is about what the room he came FROM sees afterwards, because that
is the screen on which he can be lost: he is still one of its eighteen, and until this was
fixed he matched no teacher's line in its distribution and was not counted as absent
either -- present in the room's own list and in none of its own rows.

THE OTHER HALF IS THE TEACHER WITH NOBODY.  A room's teachers used to be derived from
«whoever holds a child here tonight», which is empty for exactly the teacher a head most
wants to hand a child to.  They come from ``teacher_room_role`` now -- the same table
``bot/routers/room.py`` reads the head's OWN room from, so the asymmetry is gone.
"""

from __future__ import annotations

from bot.keyboards.room import (
    ELSEWHERE_MARKER,
    OP_AWAY,
    OP_CAME,
    AddGuest,
    Present,
    SetTeacher,
    assignments_header,
    room_header,
    teachers_keyboard,
)
from core.services.room import ElsewhereTonight
from conftest import (
    HEAD_TG_ID,
    NEIGHBOUR_TEACHER_TG_ID,
    OTHER_ROOM,
    ROOM,
    ROOM_SIZE,
    TODAY,
    feed_callback,
    feed_message,
)

#: How many children 303 borrows in these tests.  Three, so that «the borrowed ones» is a
#: set and not a single row whose behaviour could be a coincidence.
BORROWED = 3


def _day(dispatcher, room, host):
    return dispatcher.workflow_data["room_service"].room_day(room, TODAY, host_teacher_id=host)


def _borrow(dispatcher, bot_instance, room_world):
    """304 marks three of its own; 303 then takes those same three as guests."""
    taken = room_world.outsiders[:BORROWED]
    for student_id in taken:
        feed_callback(dispatcher, bot=bot_instance, from_id=NEIGHBOUR_TEACHER_TG_ID,
                      data=Present(student_id=student_id, op=OP_CAME).pack())
    for student_id in taken:
        feed_callback(dispatcher, bot=bot_instance, from_id=HEAD_TG_ID,
                      data=AddGuest(student_id=student_id).pack())
    return taken


def test_a_child_taken_next_door_is_still_on_his_own_rooms_screen_and_says_where_he_is(
    dispatcher, bot_instance, recorder, room_world
):
    room_service = dispatcher.workflow_data["room_service"]
    taken = _borrow(dispatcher, bot_instance, room_world)

    home = _day(dispatcher, OTHER_ROOM, room_world.neighbour_teacher_id)
    assert len(home.members) == ROOM_SIZE, "his own room lost him from its list entirely"
    assert {member.student.id for member in home.elsewhere} == set(taken)
    assert home.came == 0, (
        "the three who are next door are counted as having arrived HERE: «пришли %d из %d» "
        "tells this head that people are in front of him who are not" % (home.came, home.total)
    )

    names = room_service.teacher_names(home)
    header = room_header(home, names)
    assert "сегодня в другой аудитории" in header, header
    # Named, not numbered.  The id of a teacher printed to a person, about a child, is a
    # number nobody in the room can resolve.
    assert "преподаватель %d" % room_world.head_teacher_id not in header, header
    assert "Старший" in header, header


def test_every_child_of_a_room_lands_in_exactly_one_line_of_its_distribution(
    dispatcher, bot_instance, room_world
):
    """The block said «15 из 18» without saying so, which is how a child is forgotten."""
    room_service = dispatcher.workflow_data["room_service"]
    _borrow(dispatcher, bot_instance, room_world)

    home = _day(dispatcher, OTHER_ROOM, room_world.neighbour_teacher_id)
    block = assignments_header(home, room_service.teacher_names(home))

    missing, doubled = [], []
    for member in home.members:
        seen = block.count(member.student.surname)
        if seen == 0:
            missing.append(member.student.surname)
        elif seen > 1:
            doubled.append((member.student.surname, seen))
    assert not missing, "children in no line of the distribution: %r" % (missing,)
    assert not doubled, "children in two lines at once: %r" % (doubled,)


def test_his_own_head_may_not_act_on_him_while_another_room_holds_him(
    connection, dispatcher, bot_instance, recorder, room_world
):
    """Presence and tonight's teacher are ONE row.

    Marking him from here would overwrite what the head standing next to him wrote, and
    taking the mark back would delete the child off that head's screen -- from a room he is
    not in.  Refused with a sentence that says where he is, and never with «экран устарел»:
    the screen is right, the request is not.
    """
    taken = _borrow(dispatcher, bot_instance, room_world)[0]
    before = [tuple(row) for row in connection.execute(
        "select session_id, student_id, teacher_id, status from attendance order by student_id"
    )]

    for data in (
        Present(student_id=taken, op=OP_AWAY).pack(),
        Present(student_id=taken, op=OP_CAME).pack(),
        SetTeacher(student_id=taken, teacher_id=room_world.neighbour_teacher_id).pack(),
    ):
        recorder.clear()
        feed_callback(dispatcher, bot=bot_instance, from_id=NEIGHBOUR_TEACHER_TG_ID, data=data)
        assert recorder.alerts() == [ElsewhereTonight.told], recorder.alerts()

    after = [tuple(row) for row in connection.execute(
        "select session_id, student_id, teacher_id, status from attendance order by student_id"
    )]
    assert after == before, "his own room wrote over the row of the room that has him"

    # And the head who DOES have him is unaffected: his screen still shows the guest.
    assert _day(dispatcher, ROOM, room_world.head_teacher_id).member(taken) is not None


def test_the_button_of_a_child_who_is_next_door_says_so(dispatcher, bot_instance, room_world):
    from bot.keyboards.room import room_keyboard

    taken = _borrow(dispatcher, bot_instance, room_world)[0]
    home = _day(dispatcher, OTHER_ROOM, room_world.neighbour_teacher_id)
    surname = home.member(taken).student.surname
    labels = [
        button.text
        for row in room_keyboard(home).inline_keyboard[:-1]
        for button in row
        if surname in button.text
    ]
    assert labels and labels[0].startswith(ELSEWHERE_MARKER), labels


# ------------------------------------------------------ the teacher who holds nobody

def test_a_teacher_of_this_room_who_holds_nobody_today_can_still_be_handed_a_child(
    dispatcher, bot_instance, recorder, room_world
):
    """The evening on which a head most wants to hand somebody over.

    The room's teachers come from ``teacher_room_role``, where the binding actually lives.
    Derived from the standing rows instead, this teacher was invisible and the request to
    hand him a child was refused -- on the one evening the feature exists for.
    """
    room_service = dispatcher.workflow_data["room_service"]
    head = room_world.head_teacher_id
    idle = room_world.idle_teacher_id
    student_id = room_world.students[0]

    day = _day(dispatcher, ROOM, head)
    assert idle in day.teacher_ids, (
        "a teacher bound to room %s in the roster is not among its teachers: %r"
        % (ROOM, day.teacher_ids)
    )
    offered = {
        button.callback_data
        for row in teachers_keyboard(day, day.member(student_id),
                                     room_service.teacher_names(day)).inline_keyboard
        for button in row
    }
    assert SetTeacher(student_id=student_id, teacher_id=idle).pack() in offered

    recorder.clear()
    feed_callback(dispatcher, bot=bot_instance, from_id=HEAD_TG_ID,
                  data=SetTeacher(student_id=student_id, teacher_id=idle).pack())
    assert _day(dispatcher, ROOM, head).member(student_id).today_teacher_id == idle
    assert "Свободный" in recorder.alerts()[0], recorder.alerts()


def test_untapping_a_child_who_was_moved_tonight_says_the_move_went_with_it(
    dispatcher, bot_instance, recorder, room_world
):
    """Presence and tonight's teacher are one row, so the undo takes both.

    Nothing here can keep the move -- the row cannot exist without a status, and the
    negative status is one this screen never writes.  So the head is told at the moment it
    happens rather than finding out when the child is at the wrong table.
    """
    head = room_world.head_teacher_id
    student_id = room_world.students[0]
    other = room_world.other_teacher_of(0)

    feed_callback(dispatcher, bot=bot_instance, from_id=HEAD_TG_ID,
                  data=SetTeacher(student_id=student_id, teacher_id=other).pack())
    assert _day(dispatcher, ROOM, head).member(student_id).is_moved_today

    recorder.clear()
    feed_callback(dispatcher, bot=bot_instance, from_id=HEAD_TG_ID,
                  data=Present(student_id=student_id, op=OP_AWAY).pack())
    assert "перевод" in recorder.alerts()[0], recorder.alerts()
    assert _day(dispatcher, ROOM, head).member(student_id).today_teacher_id is None


def test_an_ordinary_undo_does_not_mention_a_move_that_was_never_made(
    dispatcher, bot_instance, recorder, room_world
):
    head = room_world.head_teacher_id
    student_id = room_world.students[1]
    feed_callback(dispatcher, bot=bot_instance, from_id=HEAD_TG_ID,
                  data=Present(student_id=student_id, op=OP_CAME).pack())
    recorder.clear()
    feed_callback(dispatcher, bot=bot_instance, from_id=HEAD_TG_ID,
                  data=Present(student_id=student_id, op=OP_AWAY).pack())
    assert "перевод" not in recorder.alerts()[0], recorder.alerts()
    assert _day(dispatcher, ROOM, head).member(student_id).present is False
