"""The day rule that still refuses, and the ceiling that stopped refusing on 10.09.

The day a teacher does not come is refused in ``core/``, not only on the client, so a
page reload cannot reach the write a stale dropdown would have blocked.

THE CEILING NO LONGER REFUSES, and these tests are the record of that ruling rather than
of the old rule (owner, 10.09, ТЗ-ДОБОР A1; задание §5: «потолок пяти: отказ на записи
снять, остаётся красный признак»).  The live case is why: Вася Филянин really carries six
students on Monday and seven on Thursday against a ceiling of five.  The write goes
through, and ``over_ceiling()`` is what says he is over it — a fact to be shown in red,
not a veto.

Live cases these tests are modelled on (owner, 09.09 and 10.09): Юсуфов assigned to
Ольга Рыжая on a Thursday she is marked absent, and Вася Филянин with his six and seven.
"""

from __future__ import annotations

import pytest

from core.services.enrollment import (
    EnrollmentService,
    TeacherNotAttending,
)

from fakes import MON, THU, THURSDAY

VANYA, YAN, DANYA = 101, 102, 103
KAKHIANI, YUSUFOV, FILIANIN = 1, 2, 3
OLGA_RYZHAYA = 201


# --------------------------------------------------------------- the day prohibition

def test_assigning_on_a_day_the_teacher_does_not_attend_is_refused(store, calendar):
    calendar._not_attending.add((OLGA_RYZHAYA, THU))
    service = EnrollmentService(store, calendar=calendar)

    with pytest.raises(TeacherNotAttending):
        service.assign(YUSUFOV, OLGA_RYZHAYA, room="303", slot=THU,
                        valid_from="2025-09-01")

    assert store.rows == []


def test_moving_a_student_onto_a_day_the_teacher_does_not_attend_is_refused(
    store, calendar
):
    service = EnrollmentService(store, calendar=calendar)
    service.assign(YUSUFOV, VANYA, room="303", slot=THU, valid_from="2025-09-01")
    calendar._not_attending.add((OLGA_RYZHAYA, THU))

    with pytest.raises(TeacherNotAttending):
        service.move(YUSUFOV, slot=THU, to_teacher_id=OLGA_RYZHAYA,
                     effective_from="2025-12-01", room="303")

    # The standing row is untouched -- refused before either half of the move runs.
    assert service.teacher_on(YUSUFOV, THURSDAY).teacher_id == VANYA


def test_a_day_the_teacher_does_attend_is_not_refused(store, calendar):
    service = EnrollmentService(store, calendar=calendar)
    calendar._not_attending.add((OLGA_RYZHAYA, THU))

    opened = service.assign(YUSUFOV, OLGA_RYZHAYA, room="303", slot=MON,
                            valid_from="2025-09-01")
    assert opened.teacher_id == OLGA_RYZHAYA


def test_no_calendar_wired_in_means_the_day_is_never_checked(fake_enrollment):
    """Import and bot call sites construct the service with no ``calendar`` at all
    and must keep writing exactly as before -- this is the off switch, proven."""
    opened = fake_enrollment.assign(YUSUFOV, OLGA_RYZHAYA, room="303", slot=THU,
                                    valid_from="2025-09-01")
    assert opened.teacher_id == OLGA_RYZHAYA


# ----------------------------------------------------------------------- the ceiling

def test_a_sixth_student_is_saved_and_marked(guarded_enrollment):
    """Was ``test_a_sixth_student_in_one_slot_is_refused`` until 10.09.

    Both halves are asserted here, and both are the point: the sixth row EXISTS
    (the write was not refused) and the teacher READS AS OVER the ceiling (the red
    mark has something to be red about).  Asserting only the first would let a
    silent removal of ``over_ceiling`` pass as a fix.
    """
    for student_id in range(1, 6):
        guarded_enrollment.assign(student_id, FILIANIN, room="303", slot=MON,
                                  valid_from="2025-09-01")
    assert not guarded_enrollment.over_ceiling(
        teacher_id=FILIANIN, slot=MON, day="2025-09-01")

    shestoj = guarded_enrollment.assign(6, FILIANIN, room="303", slot=MON,
                                        valid_from="2025-09-01")

    assert shestoj.teacher_id == FILIANIN
    assert guarded_enrollment.teacher_on(6, "2025-09-01").teacher_id == FILIANIN
    assert guarded_enrollment.carrying_in_slot(
        teacher_id=FILIANIN, slot=MON, day="2025-09-01") == 6
    assert guarded_enrollment.over_ceiling(
        teacher_id=FILIANIN, slot=MON, day="2025-09-01")


def test_a_seventh_student_is_saved_too_and_the_count_keeps_counting(guarded_enrollment):
    """Филянин's real Thursday.  The mark says «seven», not «over the limit, stopped»."""
    for student_id in range(1, 8):
        guarded_enrollment.assign(student_id, FILIANIN, room="303", slot=THU,
                                  valid_from="2025-09-01")

    assert guarded_enrollment.carrying_in_slot(
        teacher_id=FILIANIN, slot=THU, day="2025-09-01") == 7
    assert guarded_enrollment.over_ceiling(
        teacher_id=FILIANIN, slot=THU, day="2025-09-01")


def test_the_fifth_student_is_still_inside_the_line(guarded_enrollment):
    """The ceiling stopped refusing; it did not stop being FIVE. Five is not over."""
    for student_id in range(1, 5):
        guarded_enrollment.assign(student_id, FILIANIN, room="303", slot=MON,
                                  valid_from="2025-09-01")

    fifth = guarded_enrollment.assign(5, FILIANIN, room="303", slot=MON,
                                      valid_from="2025-09-01")
    assert fifth.teacher_id == FILIANIN
    assert not guarded_enrollment.over_ceiling(
        teacher_id=FILIANIN, slot=MON, day="2025-09-01")


def test_moving_a_sixth_student_onto_a_full_teacher_goes_through(guarded_enrollment):
    """Was ``..._is_refused``. The move is the very act the organiser performs on
    screen mid-lesson, and it is the one the owner asked to stop blocking."""
    for student_id in range(1, 6):
        guarded_enrollment.assign(student_id, FILIANIN, room="303", slot=MON,
                                  valid_from="2025-09-01")
    guarded_enrollment.assign(6, VANYA, room="303", slot=MON, valid_from="2025-09-01")

    guarded_enrollment.move(6, slot=MON, to_teacher_id=FILIANIN,
                            effective_from="2025-12-01", room="303")

    assert guarded_enrollment.teacher_on(6, "2025-12-08").teacher_id == FILIANIN
    assert guarded_enrollment.over_ceiling(
        teacher_id=FILIANIN, slot=MON, day="2025-12-08")


def test_a_room_only_move_does_not_count_the_students_own_seat_twice(guarded_enrollment):
    """The student already occupies one of the five seats their own move is about to
    keep them in -- excluding their own standing row is what keeps the COUNT honest.

    Kept after 10.09 although nothing refuses any more: ``excluding_enrollment_id`` now
    feeds the red mark instead of a veto, and a mark that counts one person twice is
    just as wrong as a refusal that did."""
    for student_id in range(1, 5):
        guarded_enrollment.assign(student_id, FILIANIN, room="303", slot=MON,
                                  valid_from="2025-09-01")
    guarded_enrollment.assign(5, FILIANIN, room="303", slot=MON, valid_from="2025-09-01")

    move = guarded_enrollment.move(5, slot=MON, to_teacher_id=FILIANIN,
                                   effective_from="2025-12-01", room="302")
    assert move.opened.room == "302"


def test_no_ceiling_wired_in_means_nobody_is_ever_over_it(fake_enrollment):
    """The off switch survives the change of rule, and it now switches off the MARK.

    "Is he over a limit nobody set" has no true answer, and ``False`` is the only one
    that does not invent a limit — the import tools and the bot construct the service
    with no ``ceiling`` at all."""
    for student_id in range(1, 8):
        fake_enrollment.assign(student_id, FILIANIN, room="303", slot=THU,
                               valid_from="2025-09-01")
    assert len(fake_enrollment.history_of(1, THU)) == 1  # got in; no exception raised
    assert fake_enrollment.carrying_in_slot(
        teacher_id=FILIANIN, slot=THU, day="2025-09-01") == 7
    assert not fake_enrollment.over_ceiling(
        teacher_id=FILIANIN, slot=THU, day="2025-09-01")


# ------------------------------------------------------------- the in-place edit path

def test_enforce_is_public_for_the_in_place_edit_path_in_veb_server(guarded_enrollment):
    """``veb/server.py`` writes ``enrollment`` directly for a same-day repeated edit,
    bypassing ``assign``/``move`` entirely -- this is the call it makes first.

    The door is still public and still refuses the DAY rule; what it no longer refuses
    is a full teacher.  That the call passes on a teacher carrying five is the whole
    assertion — before 10.09 this same line raised."""
    for student_id in range(1, 6):
        guarded_enrollment.assign(student_id, FILIANIN, room="303", slot=MON,
                                  valid_from="2025-09-01")

    guarded_enrollment.enforce_calendar_and_ceiling(
        teacher_id=FILIANIN, slot=MON, day="2025-09-01"
    )
    guarded_enrollment.enforce_calendar_and_ceiling(
        teacher_id=FILIANIN, slot=MON, day="2025-09-01", excluding_enrollment_id=1
    )

    # The other half of the same door is untouched: the day rule still refuses.
    guarded_enrollment._calendar._not_attending.add((FILIANIN, MON))
    with pytest.raises(TeacherNotAttending):
        guarded_enrollment.enforce_calendar_and_ceiling(
            teacher_id=FILIANIN, slot=MON, day="2025-09-01"
        )
