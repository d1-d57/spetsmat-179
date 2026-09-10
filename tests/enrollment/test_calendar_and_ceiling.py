"""The two rules the form's hole let through: a day the teacher does not come, and a
sixth student in one slot.  Both are refused in ``core/``, not only on the client, so a
page reload cannot reach the write a stale dropdown would have blocked.

Live cases these tests are modelled on (owner, 09.09): Юсуфов assigned to Ольга Рыжая
on a Thursday she is marked absent, and Вася Филянин carrying six students on Monday and
seven on Thursday against the ceiling of five.
"""

from __future__ import annotations

import pytest

from core.services.enrollment import (
    CeilingExceeded,
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

def test_a_sixth_student_in_one_slot_is_refused(guarded_enrollment):
    for student_id in range(1, 6):
        guarded_enrollment.assign(student_id, FILIANIN, room="303", slot=MON,
                                  valid_from="2025-09-01")

    with pytest.raises(CeilingExceeded):
        guarded_enrollment.assign(6, FILIANIN, room="303", slot=MON,
                                  valid_from="2025-09-01")


def test_the_fifth_student_is_the_last_one_accepted(guarded_enrollment):
    for student_id in range(1, 5):
        guarded_enrollment.assign(student_id, FILIANIN, room="303", slot=MON,
                                  valid_from="2025-09-01")

    fifth = guarded_enrollment.assign(5, FILIANIN, room="303", slot=MON,
                                      valid_from="2025-09-01")
    assert fifth.teacher_id == FILIANIN


def test_moving_a_sixth_student_onto_a_full_teacher_is_refused(guarded_enrollment):
    for student_id in range(1, 6):
        guarded_enrollment.assign(student_id, FILIANIN, room="303", slot=MON,
                                  valid_from="2025-09-01")
    guarded_enrollment.assign(6, VANYA, room="303", slot=MON, valid_from="2025-09-01")

    with pytest.raises(CeilingExceeded):
        guarded_enrollment.move(6, slot=MON, to_teacher_id=FILIANIN,
                                effective_from="2025-12-01", room="303")
    # Refused before either half of the move ran: the sixth student is still with VANYA.
    assert guarded_enrollment.teacher_on(6, "2025-12-08").teacher_id == VANYA


def test_a_room_only_move_does_not_count_the_students_own_seat_twice(guarded_enrollment):
    """The student already occupies one of the five seats their own move is about to
    keep them in -- excluding their own standing row is what makes a room correction on
    an already-full teacher possible at all."""
    for student_id in range(1, 5):
        guarded_enrollment.assign(student_id, FILIANIN, room="303", slot=MON,
                                  valid_from="2025-09-01")
    guarded_enrollment.assign(5, FILIANIN, room="303", slot=MON, valid_from="2025-09-01")

    move = guarded_enrollment.move(5, slot=MON, to_teacher_id=FILIANIN,
                                   effective_from="2025-12-01", room="302")
    assert move.opened.room == "302"


def test_no_ceiling_wired_in_means_the_count_is_never_checked(fake_enrollment):
    for student_id in range(1, 8):
        fake_enrollment.assign(student_id, FILIANIN, room="303", slot=THU,
                               valid_from="2025-09-01")
    assert len(fake_enrollment.history_of(1, THU)) == 1  # got in; no exception raised


# ------------------------------------------------------------- the in-place edit path

def test_enforce_is_public_for_the_in_place_edit_path_in_veb_server(guarded_enrollment):
    """``veb/server.py`` writes ``enrollment`` directly for a same-day repeated edit,
    bypassing ``assign``/``move`` entirely -- this is the call it makes first."""
    for student_id in range(1, 6):
        guarded_enrollment.assign(student_id, FILIANIN, room="303", slot=MON,
                                  valid_from="2025-09-01")

    with pytest.raises(CeilingExceeded):
        guarded_enrollment.enforce_calendar_and_ceiling(
            teacher_id=FILIANIN, slot=MON, day="2025-09-01"
        )

    # The student's own row is excluded, so re-confirming it in place is not refused.
    guarded_enrollment.enforce_calendar_and_ceiling(
        teacher_id=FILIANIN, slot=MON, day="2025-09-01", excluding_enrollment_id=1
    )
