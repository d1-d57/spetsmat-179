"""The domain rules of enrollment, on a dict store: no database in the way.

Everything here is about the two facts the position exists for — the lesson day is part
of the KEY, and a move does not rewrite the past — plus the refusals that keep a caller
from reaching either of them by accident.
"""

from __future__ import annotations

import pytest

import config
from core.services.enrollment import (
    AlreadyEnrolled,
    EnrollmentError,
    MoveChangesNothing,
    MoveNotForward,
    NotEnrolled,
    UnknownSlot,
    lesson_day_of,
    weekday_of,
)

from fakes import MON, MONDAY, THU, THURSDAY

VANYA, YAN, DANYA = 101, 102, 103
KAKHIANI = 1


# ------------------------------------------------------------- the day is in the key

def test_one_student_has_two_teachers_on_two_lesson_days(fake_enrollment):
    """The Кахиани case: Ваня on Monday, Ян on Thursday, both open at once."""
    fake_enrollment.assign(KAKHIANI, VANYA, room="303", slot=MON, valid_from="2025-09-01")
    fake_enrollment.assign(KAKHIANI, YAN, room="303", slot=THU, valid_from="2025-09-01")

    assert fake_enrollment.teacher_on(KAKHIANI, MONDAY).teacher_id == VANYA
    assert fake_enrollment.teacher_on(KAKHIANI, THURSDAY).teacher_id == YAN
    assert fake_enrollment.lesson_days_of(KAKHIANI) == [MON, THU]


def test_the_weekday_comes_from_the_date_and_not_from_the_caller(fake_enrollment):
    """``teacher_on`` takes a DATE.  The key it looks up is derived, never passed in.

    A caller that had to supply the weekday alongside the date could supply a weekday
    that contradicts it, and the answer would be a teacher the student never sat with on
    that day.
    """
    fake_enrollment.assign(KAKHIANI, VANYA, room="303", slot=MON, valid_from="2025-09-01")
    fake_enrollment.assign(KAKHIANI, YAN, room="303", slot=THU, valid_from="2025-09-01")

    for day, expected in (("2025-10-06", VANYA), ("2025-10-13", VANYA),
                          ("2025-10-09", YAN), ("2025-10-16", YAN)):
        assert fake_enrollment.teacher_on(KAKHIANI, day).teacher_id == expected
        assert fake_enrollment.teacher_on(KAKHIANI, day).slot == weekday_of(day)


def test_a_day_the_student_does_not_attend_answers_none_and_is_not_an_error(fake_enrollment):
    """Wednesday is not a lesson day for this student, and that is a fact, not a fault."""
    fake_enrollment.assign(KAKHIANI, VANYA, room="303", slot=MON, valid_from="2025-09-01")
    assert fake_enrollment.teacher_on(KAKHIANI, "2025-10-08") is None


def test_moving_one_lesson_day_leaves_the_other_alone(fake_enrollment):
    """The mutable side is one (student, weekday) pair, never the student as a whole."""
    fake_enrollment.assign(KAKHIANI, VANYA, room="303", slot=MON, valid_from="2025-09-01")
    fake_enrollment.assign(KAKHIANI, YAN, room="303", slot=THU, valid_from="2025-09-01")

    fake_enrollment.move(
        KAKHIANI, slot=MON, to_teacher_id=DANYA, effective_from="2025-12-01", room="302"
    )

    assert fake_enrollment.teacher_on(KAKHIANI, "2025-12-08").teacher_id == DANYA
    assert fake_enrollment.teacher_on(KAKHIANI, "2025-12-11").teacher_id == YAN
    assert fake_enrollment.teacher_on(KAKHIANI, MONDAY).teacher_id == VANYA


# ---------------------------------------------------------- a move does not rewrite

def test_a_move_closes_one_interval_and_opens_one_and_rewrites_nothing(fake_enrollment, store):
    """Two rows afterwards, and the first still names the teacher it always named."""
    fake_enrollment.assign(KAKHIANI, VANYA, room="303", slot=MON, valid_from="2025-09-01")

    move = fake_enrollment.move(
        KAKHIANI, slot=MON, to_teacher_id=DANYA, effective_from="2025-12-01", room="302"
    )

    assert store.closes == 1
    assert move.closed.teacher_id == VANYA
    assert move.opened.teacher_id == DANYA
    history = fake_enrollment.history_of(KAKHIANI, MON)
    assert [(row.teacher_id, row.valid_from, row.valid_to) for row in history] == [
        (VANYA, "2025-09-01", "2025-12-01"),
        (DANYA, "2025-12-01", config.OPEN_END_DATE),
    ]


def test_the_handover_is_half_open_and_leaves_no_uncovered_day(fake_enrollment):
    """``valid_to`` is EXCLUSIVE, so the effective day belongs to the incoming teacher.

    This is the point the задание words as "``valid_to`` = the day before": the outgoing
    teacher covers through 30 November, the incoming one from 1 December, and writing the
    literal 30th into ``valid_to`` would leave the 30th covered by nobody.
    """
    fake_enrollment.assign(KAKHIANI, VANYA, room="303", slot=MON, valid_from="2025-09-01")
    fake_enrollment.move(
        KAKHIANI, slot=MON, to_teacher_id=DANYA, effective_from="2025-12-01", room="302"
    )

    # 24 November and 1 December are the last Monday before and the first Monday on or
    # after the handover; both resolve, to different people, with nothing in between.
    assert fake_enrollment.teacher_on(KAKHIANI, "2025-11-24").teacher_id == VANYA
    assert fake_enrollment.teacher_on(KAKHIANI, "2025-12-01").teacher_id == DANYA


def test_the_past_keeps_its_teacher_after_the_move(fake_enrollment):
    """Ask about October again after moving in December: the answer must not have moved."""
    fake_enrollment.assign(KAKHIANI, VANYA, room="303", slot=MON, valid_from="2025-09-01")
    october = fake_enrollment.teacher_on(KAKHIANI, MONDAY).teacher_id

    fake_enrollment.move(
        KAKHIANI, slot=MON, to_teacher_id=DANYA, effective_from="2025-12-01", room="302"
    )

    assert october == VANYA
    assert fake_enrollment.teacher_on(KAKHIANI, MONDAY).teacher_id == VANYA


def test_a_move_carries_the_room_over_when_the_caller_does_not_name_one(fake_enrollment):
    fake_enrollment.assign(KAKHIANI, VANYA, room="303", slot=MON, valid_from="2025-09-01")
    move = fake_enrollment.move(
        KAKHIANI, slot=MON, to_teacher_id=YAN, effective_from="2025-12-01"
    )
    assert move.opened.room == "303"


def test_ending_an_enrollment_closes_it_without_a_successor(fake_enrollment):
    """Гамаюнова left after sheet 6, and October still knows who taught her."""
    gamayunova = 2
    fake_enrollment.assign(gamayunova, VANYA, room="303", slot=MON, valid_from="2025-09-01")
    fake_enrollment.end(gamayunova, slot=MON, effective_from="2025-12-01")

    assert fake_enrollment.teacher_on(gamayunova, MONDAY).teacher_id == VANYA
    assert fake_enrollment.teacher_on(gamayunova, "2025-12-08") is None
    assert fake_enrollment.lesson_days_of(gamayunova) == []


# -------------------------------------------------------------------- the refusals

def test_assigning_over_an_open_row_is_refused_and_names_the_repair(fake_enrollment):
    fake_enrollment.assign(KAKHIANI, VANYA, room="303", slot=MON, valid_from="2025-09-01")
    with pytest.raises(AlreadyEnrolled, match="move"):
        fake_enrollment.assign(KAKHIANI, DANYA, room="302", slot=MON,
                               valid_from="2025-12-01")


def test_moving_a_student_who_has_no_open_row_is_refused(fake_enrollment):
    """Not silently promoted into a first enrolment: the caller said "change", not "add"."""
    with pytest.raises(NotEnrolled):
        fake_enrollment.move(KAKHIANI, slot=THU, to_teacher_id=YAN,
                             effective_from="2025-12-01")


def test_a_move_effective_before_the_interval_opened_is_refused(fake_enrollment):
    fake_enrollment.assign(KAKHIANI, VANYA, room="303", slot=MON, valid_from="2025-09-01")
    for day in ("2025-09-01", "2025-08-25"):
        with pytest.raises(MoveNotForward):
            fake_enrollment.move(KAKHIANI, slot=MON, to_teacher_id=DANYA,
                                 effective_from=day, room="302")


def test_a_move_that_changes_nothing_is_refused(fake_enrollment):
    """Splitting an interval into two identical halves makes one fact answer as two."""
    fake_enrollment.assign(KAKHIANI, VANYA, room="303", slot=MON, valid_from="2025-09-01")
    with pytest.raises(MoveChangesNothing):
        fake_enrollment.move(KAKHIANI, slot=MON, to_teacher_id=VANYA,
                             effective_from="2025-12-01", room="303")


def test_a_room_change_with_the_same_teacher_is_a_real_move(fake_enrollment):
    """"Who worked with him" and "where he sat" are one question, so the room moves too."""
    fake_enrollment.assign(KAKHIANI, VANYA, room="303", slot=MON, valid_from="2025-09-01")
    move = fake_enrollment.move(KAKHIANI, slot=MON, to_teacher_id=VANYA,
                                effective_from="2025-12-01", room="302")
    assert (move.closed.room, move.opened.room) == ("303", "302")


def test_a_zero_based_weekday_is_caught_at_the_door(fake_enrollment):
    """Monday = 1.  With Monday = 0 every lookup shifts a day and answers wrongly."""
    for bad in (0, 8, -1, True):
        with pytest.raises(UnknownSlot):
            fake_enrollment.assign(KAKHIANI, VANYA, room="303", slot=bad,
                                   valid_from="2025-09-01")


def test_a_date_that_is_not_a_padded_iso_day_is_refused(fake_enrollment):
    """``'2025-9-1' < '2025-10-01'`` is false as strings and true as dates.

    Both spellings below are refused, but not always by the same branch, and that is why
    ``as_day`` has two.  ``date.fromisoformat`` is strict on Python 3.9 and rejects both
    outright; from 3.11 it accepts ``20250901`` and ``2025-09-01T00:00:00`` happily, and
    the canonical-form check is the only thing standing between such a value and a
    column whose interval test is string comparison.
    """
    for bad in ("2025-9-1", "20250901", "2025-09-01T00:00:00", "not a date", ""):
        with pytest.raises(EnrollmentError):
            fake_enrollment.assign(KAKHIANI, VANYA, room="303", slot=MON,
                                   valid_from=bad)
        with pytest.raises(EnrollmentError):
            fake_enrollment.teacher_on(KAKHIANI, bad)


def test_the_open_sentinel_cannot_open_or_close_an_interval(fake_enrollment):
    """``9999-12-31`` supplied as a start day, on all three write paths.

    Found by this position's verifier, not by the author.  It fails three different ways
    and the worst of them is silent: ``end`` at the sentinel sets ``valid_to`` to the
    value that MEANS still open, so a student reported as having left stays enrolled and
    the call returns a row that reads as closed.
    """
    fake_enrollment.assign(KAKHIANI, VANYA, room="303", slot=MON, valid_from="2025-09-01")

    with pytest.raises(EnrollmentError, match="sentinel"):
        fake_enrollment.assign(2, VANYA, room="303", slot=MON,
                               valid_from=config.OPEN_END_DATE)
    with pytest.raises(EnrollmentError, match="sentinel"):
        fake_enrollment.move(KAKHIANI, slot=MON, to_teacher_id=DANYA,
                             effective_from=config.OPEN_END_DATE, room="302")
    with pytest.raises(EnrollmentError, match="sentinel"):
        fake_enrollment.end(KAKHIANI, slot=MON, effective_from=config.OPEN_END_DATE)

    # And the refusal changed nothing: the student is still with the teacher he had.
    standing = fake_enrollment.history_of(KAKHIANI, MON)
    assert len(standing) == 1
    assert standing[0].valid_to == config.OPEN_END_DATE
    assert fake_enrollment.lesson_days_of(KAKHIANI) == [MON]


def test_a_row_without_a_room_is_refused(fake_enrollment):
    with pytest.raises(EnrollmentError, match="room"):
        fake_enrollment.assign(KAKHIANI, VANYA, room="  ", slot=MON,
                               valid_from="2025-09-01")


# ------------------------------------------------------------------- bulk and time

def test_resolve_many_answers_for_every_student_asked_including_the_misses(fake_enrollment):
    """A dict that dropped the misses would make ``len(resolved)`` look like a full house."""
    fake_enrollment.assign(1, VANYA, room="303", slot=MON, valid_from="2025-09-01")
    fake_enrollment.assign(2, YAN, room="303", slot=MON, valid_from="2025-09-01")

    resolved = fake_enrollment.resolve_many([1, 2, 3], MONDAY)

    assert set(resolved) == {1, 2, 3}
    assert resolved[1].teacher_id == VANYA
    assert resolved[2].teacher_id == YAN
    assert resolved[3] is None


def test_resolve_many_agrees_with_asking_one_at_a_time(fake_enrollment):
    """The bulk read exists for the room screen; it must not be a second opinion."""
    fake_enrollment.assign(1, VANYA, room="303", slot=MON, valid_from="2025-09-01")
    fake_enrollment.assign(2, YAN, room="303", slot=MON, valid_from="2025-09-01")
    fake_enrollment.move(2, slot=MON, to_teacher_id=DANYA,
                         effective_from="2025-10-01", room="302")

    for day in ("2025-09-08", MONDAY, "2025-12-01"):
        bulk = fake_enrollment.resolve_many([1, 2], day)
        assert bulk == {sid: fake_enrollment.teacher_on(sid, day) for sid in (1, 2)}


def test_a_mark_is_attributed_through_the_school_timezone(fake_enrollment):
    """An evening lesson in Moscow is the same UTC day here — and it is checked, not assumed.

    ``teacher_at`` takes the instant a mark carries and asks about the day that instant
    fell on in ``config.TZ_DISPLAY``.  A fixed three-hour offset would be wrong twice a
    year; the conversion goes through the timezone database.
    """
    fake_enrollment.assign(KAKHIANI, VANYA, room="303", slot=MON, valid_from="2025-09-01")

    # 18:30 Moscow on Monday 6 October is 15:30Z the same day.
    assert lesson_day_of("2025-10-06T15:30:00Z") == MONDAY
    assert fake_enrollment.teacher_at(KAKHIANI, "2025-10-06T15:30:00Z").teacher_id == VANYA

    # 00:30 Moscow on Tuesday 7 October is 21:30Z on the Monday -- the UTC date and the
    # school date disagree, and the school date is the one enrollment is written in.
    assert lesson_day_of("2025-10-06T21:30:00Z") == "2025-10-07"
    assert fake_enrollment.teacher_at(KAKHIANI, "2025-10-06T21:30:00Z") is None
