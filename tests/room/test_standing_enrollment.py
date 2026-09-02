"""THE POINT OF THIS POSITION, as one named test.

A guest brought in for tonight and a child handed to another teacher for tonight must
leave the STANDING arrangement exactly as it was.  P12 built the distinction between «he
is with Даня tonight because the head moved him» and «he is with Даня because he always
is»; a screen that blurred them would make October's marks start reporting under whoever
happened to take the child on one Thursday in March, which is the defect P12 exists to
remove.

THE PROOF IS A SNAPSHOT OF THE WHOLE ``enrollment`` TABLE, every row and every column,
taken before the taps and compared after them.  A per-child assertion would pass while a
neighbour's interval was rewritten, and «the child's teacher is still the same» would pass
while his interval was closed and an identical one opened -- which is a rewrite of history
wearing the right answer.  A table that is byte-for-byte what it was cannot hide either.

The taps go through ``feed_raw_update``, because a service that is never reached cannot
write to a table either, and a green test over an unregistered router would prove exactly
that.
"""

from __future__ import annotations

from bot.keyboards.room import OP_CAME, STANDING_TEACHER, AddGuest, Present, SetTeacher
from core.services.enrollment import EnrollmentService
from infra.enrollment_repo import SqliteEnrollmentRepo
from conftest import HEAD_TG_ID, OTHER_ROOM, ROOM, ROOM_SIZE, TODAY, feed_callback


def _enrollment_snapshot(connection) -> list:
    """Every interval in the store, ordered so that two snapshots are comparable."""
    return [
        tuple(row)
        for row in connection.execute(
            "select id, student_id, teacher_id, room, weekday, valid_from, valid_to "
            "from enrollment order by id"
        )
    ]


def test_a_guest_and_a_move_for_tonight_leave_the_standing_enrollment_untouched(
    connection, dispatcher, bot_instance, recorder, room_world, capsys
):
    room_service = dispatcher.workflow_data["room_service"]
    # A reader of the same table, built here rather than borrowed from the service: the
    # question is what the STORE says after the taps, and asking the service's own object
    # would let a service that cached an answer agree with itself.
    enrollment = EnrollmentService(SqliteEnrollmentRepo(connection))
    head = room_world.head_teacher_id

    before = _enrollment_snapshot(connection)
    assert len(before) == 2 * ROOM_SIZE, (
        "expected %d standing intervals, found %d: a snapshot of an empty table would "
        "compare equal to itself and prove nothing" % (2 * ROOM_SIZE, len(before))
    )

    moved = 0
    guests = 0
    for index in range(ROOM_SIZE):
        student_id = room_world.students[index]
        guest_id = room_world.outsiders[index]

        feed_callback(
            dispatcher,
            bot=bot_instance,
            from_id=HEAD_TG_ID,
            data=Present(student_id=student_id, op=OP_CAME).pack(),
        )
        feed_callback(
            dispatcher,
            bot=bot_instance,
            from_id=HEAD_TG_ID,
            data=SetTeacher(
                student_id=student_id, teacher_id=room_world.other_teacher_of(index)
            ).pack(),
        )
        moved += 1
        feed_callback(
            dispatcher,
            bot=bot_instance,
            from_id=HEAD_TG_ID,
            data=AddGuest(student_id=guest_id).pack(),
        )
        guests += 1

    # The screen really did change: a test in which nothing happened would also find the
    # enrollment table unchanged, and would mean nothing at all.
    day = room_service.room_day(ROOM, TODAY, host_teacher_id=head)
    assert sum(1 for member in day.members if member.is_moved_today) == moved
    assert sum(1 for member in day.members if member.is_guest) == guests

    after = _enrollment_snapshot(connection)
    assert after == before, (
        "the standing enrollment changed under %d moves and %d guests: %r"
        % (moved, guests, [pair for pair in zip(before, after) if pair[0] != pair[1]][:3])
    )

    # And the question P12 is actually asked -- «who works with this child» -- still
    # answers with the standing teacher, on today and on any other day.
    wrong = []
    for index in range(ROOM_SIZE):
        assignment = enrollment.teacher_on(room_world.students[index], TODAY)
        if assignment is None or assignment.teacher_id != room_world.standing_teacher_of(index):
            wrong.append((index, getattr(assignment, "teacher_id", None)))
        guest_assignment = enrollment.teacher_on(room_world.outsiders[index], TODAY)
        if guest_assignment is None or guest_assignment.room != OTHER_ROOM:
            wrong.append((index, getattr(guest_assignment, "room", None)))
    assert not wrong, "standing answers changed: %r" % (wrong[:5],)

    # Giving a child back to his standing teacher is also not a write to enrollment.
    for index in range(ROOM_SIZE):
        feed_callback(
            dispatcher,
            bot=bot_instance,
            from_id=HEAD_TG_ID,
            data=SetTeacher(
                student_id=room_world.students[index], teacher_id=STANDING_TEACHER
            ).pack(),
        )
    assert _enrollment_snapshot(connection) == before

    with capsys.disabled():
        print(
            "\n[постоянное закрепление] интервалов %d из %d не изменилось · "
            "переводов на сегодня %d · гостей %d · возвратов постоянному %d"
            % (len(after), len(before), moved, guests, ROOM_SIZE)
        )


def test_a_guest_never_becomes_a_member_of_this_room_tomorrow(
    connection, dispatcher, bot_instance, room_world
):
    """He is here tonight and he is not here on any other evening.

    The distinction lives in WHERE the row was written, not in a flag: the guest's row is
    an ``attendance`` row keyed by session, so tomorrow's screen reads a different session
    and finds nothing.  There is no rule to forget, because there is no rule.
    """
    room_service = dispatcher.workflow_data["room_service"]
    head = room_world.head_teacher_id
    guest_id = room_world.outsiders[0]

    feed_callback(
        dispatcher,
        bot=bot_instance,
        from_id=HEAD_TG_ID,
        data=AddGuest(student_id=guest_id).pack(),
    )
    assert room_service.room_day(ROOM, TODAY, host_teacher_id=head).member(guest_id) is not None

    # A different lesson day, seven days on, so the weekday and the standing intervals are
    # the same and the ONLY difference is the session.
    from datetime import date, timedelta

    next_week = (date.fromisoformat(TODAY) + timedelta(days=7)).isoformat()
    tomorrow_room = room_service.room_day(ROOM, next_week, host_teacher_id=head)
    assert tomorrow_room.member(guest_id) is None
    assert len(tomorrow_room.members) == ROOM_SIZE
