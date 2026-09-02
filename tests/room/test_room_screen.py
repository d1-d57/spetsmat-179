"""The sweep: eighteen children, three actions each, through the real dispatcher.

A NEGATIVE VERDICT HERE CARRIES ITS OWN COVERAGE.  «провалов не найдено» and «провалов 0,
проверено 54 из 54» read identically to a person and mean completely different things,
and a sweep that silently checked two children would look exactly like a sweep that
checked all of them.  So the counts are asserted before they are printed, and zero checks
against a non-empty room is RED rather than green.

EVERY ACTION GOES THROUGH ``feed_raw_update``.  Not through the service and not through
the keyboard: the thing being proved is that a tap on a real button, arriving as the
Telegram update it really arrives as, passes the role gate, reaches a handler, answers
before it redraws, and leaves the database saying what the head believes it says.  A test
that called ``RoomService`` directly would pass with the router unregistered.

THE SWEEP RESTORES WHAT IT CHANGES.  Each child's three actions end with the room in the
state they found it in, so that check 54 is testing the same world as check 1 and a
failure names one child rather than the residue of the seventeen before him.
"""

from __future__ import annotations

from bot.keyboards.room import (
    OP_AWAY,
    OP_CAME,
    STANDING_TEACHER,
    AddGuest,
    Present,
    SetTeacher,
)
from conftest import HEAD_TG_ID, ROOM, ROOM_SIZE, TODAY, feed_callback, feed_message

#: Presence, a guest, tonight's assignment.  The three things the head does at the start
#: of a lesson, and the three the готовности criterion counts.
ACTIONS = ("присутствие", "гость", "сегодняшнее назначение")


def _tap(dispatcher, bot, recorder, data: str) -> list:
    """One tap, and the sequence of outbound calls it produced.

    The recorder is cleared first so that the sequence belongs to THIS tap: «answer before
    redraw» is a property of an order, and an order read across two taps is not one.
    """
    recorder.clear()
    feed_callback(dispatcher, bot=bot, from_id=HEAD_TG_ID, data=data)
    return recorder.methods()


def _answered_before_redrawing(methods: list) -> bool:
    """Did the toast go out before the round-trip that may be slow?

    The callback query expires in fifteen seconds and at 800 ms a person cannot tell
    whether a tap counted, so a redraw standing in front of the answer is the defect this
    checks for -- not the absence of either call.
    """
    if "AnswerCallbackQuery" not in methods:
        return False
    if "EditMessageText" not in methods:
        return True
    return methods.index("AnswerCallbackQuery") < methods.index("EditMessageText")


def test_eighteen_children_three_actions_each_through_the_dispatcher(
    dispatcher, bot_instance, recorder, room_world, capsys
):
    room_service = dispatcher.workflow_data["room_service"]
    head = room_world.head_teacher_id

    def day():
        return room_service.room_day(ROOM, TODAY, host_teacher_id=head)

    def tap(data):
        return _tap(dispatcher, bot_instance, recorder, data)

    opened = day()
    assert len(opened.members) == ROOM_SIZE, (
        "the room holds %d children, not %d: a sweep over the wrong room proves nothing"
        % (len(opened.members), ROOM_SIZE)
    )

    # The head opens the screen the way he really opens it.
    feed_message(dispatcher, bot=bot_instance, from_id=HEAD_TG_ID, text="/auditoria")
    assert recorder.texts(), "the entry command drew nothing at all"

    failures = []
    checks = 0

    for index in range(ROOM_SIZE):
        student_id = room_world.students[index]
        guest_id = room_world.outsiders[index]
        other_teacher = room_world.other_teacher_of(index)

        # ------------------------------------------------ 1. присутствие
        methods = tap(Present(student_id=student_id, op=OP_CAME).pack())
        member = day().member(student_id)
        if not _answered_before_redrawing(methods):
            failures.append((index, ACTIONS[0], "redraw before answer: %r" % (methods,)))
        elif member is None or not member.present:
            failures.append((index, ACTIONS[0], "tap did not mark him present"))
        else:
            methods = tap(Present(student_id=student_id, op=OP_AWAY).pack())
            back = day().member(student_id)
            if back is None or back.present:
                failures.append((index, ACTIONS[0], "a repeat tap did not take the mark back"))
            elif not _answered_before_redrawing(methods):
                failures.append((index, ACTIONS[0], "redraw before answer on the undo"))
        checks += 1

        # ------------------------------------------------ 2. гость
        methods = tap(AddGuest(student_id=guest_id).pack())
        guest = day().member(guest_id)
        if not _answered_before_redrawing(methods):
            failures.append((index, ACTIONS[1], "redraw before answer: %r" % (methods,)))
        elif guest is None:
            failures.append((index, ACTIONS[1], "the guest did not appear on the screen"))
        elif not guest.is_guest:
            failures.append((index, ACTIONS[1], "he appeared, but not as a guest"))
        elif guest.teacher_id != head:
            failures.append(
                (index, ACTIONS[1], "the guest went to %r, not to the head" % (guest.teacher_id,))
            )
        elif not guest.present:
            failures.append((index, ACTIONS[1], "a guest who is here is not marked here"))
        else:
            # He goes home again: a guest's presence IS his row, so taking the mark back
            # takes him off the screen, and the next child is checked against a clean room.
            tap(Present(student_id=guest_id, op=OP_AWAY).pack())
            if day().member(guest_id) is not None:
                failures.append((index, ACTIONS[1], "the guest would not leave the screen"))
        checks += 1

        # ------------------------------------- 3. сегодняшнее назначение
        methods = tap(SetTeacher(student_id=student_id, teacher_id=other_teacher).pack())
        moved = day().member(student_id)
        if not _answered_before_redrawing(methods):
            failures.append((index, ACTIONS[2], "redraw before answer: %r" % (methods,)))
        elif moved is None or moved.today_teacher_id != other_teacher:
            failures.append(
                (index, ACTIONS[2], "tonight's teacher is %r, expected %r"
                 % (getattr(moved, "today_teacher_id", None), other_teacher))
            )
        elif moved.standing_teacher_id != room_world.standing_teacher_of(index):
            failures.append(
                (index, ACTIONS[2], "the STANDING teacher moved: %r" % (moved.standing_teacher_id,))
            )
        elif not moved.is_moved_today:
            failures.append((index, ACTIONS[2], "the move is not reported as a move for tonight"))
        else:
            tap(SetTeacher(student_id=student_id, teacher_id=STANDING_TEACHER).pack())
            given_back = day().member(student_id)
            if given_back is None or given_back.today_teacher_id is not None:
                failures.append((index, ACTIONS[2], "he was not given back to his standing teacher"))
            else:
                tap(Present(student_id=student_id, op=OP_AWAY).pack())
        checks += 1

    expected = ROOM_SIZE * len(ACTIONS)
    assert checks == expected, "ran %d checks, expected %d" % (checks, expected)
    assert not failures, "failures: %r" % (failures[:5],)

    with capsys.disabled():
        print(
            "\n[аудитория] учеников %d из %d · действий на ученика %d (%s) · "
            "проверок %d из %d · провалов %d"
            % (
                ROOM_SIZE, ROOM_SIZE,
                len(ACTIONS), ", ".join(ACTIONS),
                checks, expected,
                len(failures),
            )
        )


def test_the_header_counts_the_room_and_nothing_else(
    dispatcher, bot_instance, recorder, room_world
):
    """«пришли N из M» is a count of the room in front of the head.

    It compares nobody with anybody: it is the number that tells him whether to start, and
    it is the only number on this screen besides the debt counts on the buttons.
    """
    room_service = dispatcher.workflow_data["room_service"]
    head = room_world.head_teacher_id

    feed_message(dispatcher, bot=bot_instance, from_id=HEAD_TG_ID, text="/auditoria")
    assert "пришли 0 из %d" % ROOM_SIZE in recorder.texts()[0]

    for student_id in room_world.students[:5]:
        _tap(dispatcher, bot_instance, recorder, Present(student_id=student_id, op=OP_CAME).pack())
    assert "пришли 5 из %d" % ROOM_SIZE in recorder.texts()[-1]

    day = room_service.room_day(ROOM, TODAY, host_teacher_id=head)
    assert day.came == 5 and day.total == ROOM_SIZE
