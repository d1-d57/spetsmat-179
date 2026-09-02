"""The store against the REAL migrated database, and the schema's guards proved on it.

``test_service.py`` runs the domain over a dict that imitates these guards.  This file is
where the guards themselves are exercised, because an imitation that agrees with the
service proves only that the two were written by the same person: the задание asks for
the refusal to be proved, not assumed.

The two guards cover different cases and both are needed:
  * ``enrollment_one_open_row`` — a partial unique index, so two OPEN rows for one
    (student, lesson day) cannot exist; free at read time;
  * ``enrollment_no_overlap_insert`` / ``..._update`` — triggers, because no index can
    say "these two CLOSED intervals overlap".
"""

from __future__ import annotations

import sqlite3

import pytest

import config
from core.services.enrollment import (
    EnrollmentError,
    NotEnrolled,
    OverlappingHistory,
)

from fakes import MON, MONDAY, THU, THURSDAY


@pytest.fixture
def third_teacher(connection):
    """A third teacher, so a move has somewhere to go that is not the other one."""
    cursor = connection.execute(
        "insert into teachers (name, aka, is_owner) values (?, ?, 0)", ("teacher-2", "t2")
    )
    return cursor.lastrowid


# ------------------------------------------------------------ the day is in the key

def test_the_kakhiani_case_survives_the_real_schema(enrollment, world):
    """One student, two open rows, two teachers — Monday and Thursday, both legal.

    A schema that had forgotten the weekday would call this pair an overlap and refuse
    the reality it exists to record.
    """
    student = world.student_ids[0]
    vanya, yan = world.teacher_ids

    enrollment.assign(student, vanya, room="303", weekday=MON, valid_from="2025-09-01")
    enrollment.assign(student, yan, room="303", weekday=THU, valid_from="2025-09-01")

    assert enrollment.teacher_on(student, MONDAY).teacher_id == vanya
    assert enrollment.teacher_on(student, THURSDAY).teacher_id == yan
    assert enrollment.lesson_days_of(student) == [MON, THU]


def test_a_move_on_the_real_store_writes_two_rows_and_rewrites_neither(
    enrollment, world, third_teacher
):
    student = world.student_ids[1]
    vanya = world.teacher_ids[0]

    enrollment.assign(student, vanya, room="303", weekday=MON, valid_from="2025-09-01")
    enrollment.move(student, weekday=MON, to_teacher_id=third_teacher,
                    effective_from="2025-12-01", room="302")

    history = enrollment.history_of(student, MON)
    assert [(row.teacher_id, row.valid_from, row.valid_to, row.room) for row in history] == [
        (vanya, "2025-09-01", "2025-12-01", "303"),
        (third_teacher, "2025-12-01", config.OPEN_END_DATE, "302"),
    ]


# -------------------------------------------------------------- the schema refuses

def test_two_open_rows_for_one_lesson_day_are_refused(enrollment_repo, world):
    """Both open rows cannot stand, and it is the TRIGGER that says so, not the index.

    Measured rather than assumed, and it is worth writing down: SQLite runs a
    ``before insert`` trigger before it checks the unique index, and two open rows always
    overlap — both intervals run to the same sentinel — so the overlap trigger reaches
    the case first and the index's message is one a caller will not normally see.  The
    partial index is not thereby decoration: it is the read-time-free half of the
    guarantee and the half that would still hold if a trigger were ever dropped.  What
    this test pins is the refusal and its translation into a domain error, not which of
    the two carriers gets there first.
    """
    student = world.student_ids[2]
    vanya, yan = world.teacher_ids

    enrollment_repo.insert(student_id=student, teacher_id=vanya, room="303",
                           weekday=MON, valid_from="2025-09-01")
    with pytest.raises(OverlappingHistory):
        enrollment_repo.insert(student_id=student, teacher_id=yan, room="303",
                               weekday=MON, valid_from="2025-12-01")

    # And the index is live too: ask it directly, so that "the trigger covers this" does
    # not quietly become "the index was never created".
    indexes = {
        row["name"]
        for row in enrollment_repo._connection.execute(  # noqa: SLF001 -- reading schema
            "select name from sqlite_master where type = 'index' and tbl_name = 'enrollment'"
        )
    }
    assert "enrollment_one_open_row" in indexes


def test_two_closed_intervals_that_overlap_are_refused_by_the_trigger(enrollment_repo, world):
    """The expensive guard.  No index can express this, and the message names it."""
    student = world.student_ids[3]
    vanya, yan = world.teacher_ids

    enrollment_repo.insert(student_id=student, teacher_id=vanya, room="303", weekday=MON,
                           valid_from="2025-09-01", valid_to="2025-11-01")
    with pytest.raises(OverlappingHistory, match="must not overlap"):
        enrollment_repo.insert(student_id=student, teacher_id=yan, room="303", weekday=MON,
                               valid_from="2025-10-01", valid_to="2025-12-01")


def test_a_touching_handover_is_not_an_overlap(enrollment_repo, world):
    """``[a, b)`` then ``[b, c)`` is the clean handover the whole convention is for."""
    student = world.student_ids[4]
    vanya, yan = world.teacher_ids

    enrollment_repo.insert(student_id=student, teacher_id=vanya, room="303", weekday=MON,
                           valid_from="2025-09-01", valid_to="2025-12-01")
    enrollment_repo.insert(student_id=student, teacher_id=yan, room="302", weekday=MON,
                           valid_from="2025-12-01", valid_to="2026-01-01")

    assert len(enrollment_repo.history(student, MON)) == 2


def test_an_integrity_error_that_is_not_an_overlap_is_not_reported_as_one(
    enrollment_repo, world
):
    """A foreign key failure is an ``IntegrityError`` too and must keep its own name.

    Translating every integrity error into ``OverlappingHistory`` would tell the owner
    that a student's history overlaps when what actually happened is that the teacher id
    does not exist.
    """
    with pytest.raises(sqlite3.IntegrityError) as raised:
        enrollment_repo.insert(student_id=world.student_ids[0], teacher_id=10 ** 6,
                               room="303", weekday=MON, valid_from="2025-09-01")
    assert not isinstance(raised.value, OverlappingHistory)
    assert "FOREIGN KEY" in str(raised.value)


# ------------------------------------------------------------------- the seam works

def test_a_failed_move_leaves_the_standing_interval_open(enrollment, enrollment_repo, world):
    """The close and the insert of a move are ONE unit of work, and here it fails.

    Without the transaction the student would be left with a closed interval and no
    successor: he would resolve to nobody from December onwards, and the failure would
    look exactly like a student who had left.
    """
    student = world.student_ids[0]
    vanya = world.teacher_ids[0]
    enrollment.assign(student, vanya, room="303", weekday=MON, valid_from="2025-09-01")

    with pytest.raises(sqlite3.IntegrityError):
        enrollment.move(student, weekday=MON, to_teacher_id=10 ** 6,
                        effective_from="2025-12-01", room="302")

    standing = enrollment_repo.open_row(student, MON)
    assert standing is not None
    assert (standing.teacher_id, standing.valid_from, standing.valid_to) == (
        vanya, "2025-09-01", config.OPEN_END_DATE
    )
    assert enrollment.teacher_on(student, "2025-12-08").teacher_id == vanya


def test_the_open_sentinel_is_refused_on_the_real_store_too(
    enrollment, enrollment_repo, world, third_teacher
):
    """The same three refusals, against the database that would otherwise show the damage.

    Two of them leaked a raw ``sqlite3.IntegrityError`` across the seam ``core/`` exists
    to keep sqlite3 behind; the third — ``end`` — succeeded and left the row open.  This
    pins that none of the three reaches the store at all.
    """
    student = world.student_ids[0]
    vanya = world.teacher_ids[0]
    enrollment.assign(student, vanya, room="303", weekday=MON, valid_from="2025-09-01")

    with pytest.raises(EnrollmentError):
        enrollment.assign(world.student_ids[1], vanya, room="303", weekday=MON,
                          valid_from=config.OPEN_END_DATE)
    with pytest.raises(EnrollmentError):
        enrollment.move(student, weekday=MON, to_teacher_id=third_teacher,
                        effective_from=config.OPEN_END_DATE, room="302")
    with pytest.raises(EnrollmentError):
        enrollment.end(student, weekday=MON, effective_from=config.OPEN_END_DATE)

    standing = enrollment_repo.open_row(student, MON)
    assert (standing.teacher_id, standing.valid_from, standing.valid_to) == (
        vanya, "2025-09-01", config.OPEN_END_DATE
    )
    assert len(enrollment_repo.history(student, MON)) == 1
    assert enrollment.teacher_on(student, "2026-05-04").teacher_id == vanya


def test_closing_a_row_that_does_not_exist_is_loud(enrollment_repo):
    """Silence here would leave a caller opening a successor to a still-open interval."""
    with pytest.raises(EnrollmentError, match="nothing was closed"):
        enrollment_repo.close(10 ** 6, valid_to="2025-12-01")


def test_an_empty_student_filter_matches_nobody_rather_than_everybody(
    enrollment_repo, world
):
    """The classic: an empty ``in`` list collapsing into "no filter" and reporting a full house."""
    enrollment_repo.insert(student_id=world.student_ids[0], teacher_id=world.teacher_ids[0],
                           room="303", weekday=MON, valid_from="2025-09-01")
    assert enrollment_repo.rows_valid_on(MONDAY, MON, []) == []
    assert len(enrollment_repo.rows_valid_on(MONDAY, MON, None)) == 1


# ---------------------------------------------------------------- leaving, returning

def test_a_student_who_left_and_came_back_is_assigned_again_not_moved(
    enrollment, world, third_teacher
):
    """Гамаюнова left, and a returning student has closed history and no open row.

    ``move`` refuses him — there is nothing to move — and ``assign`` opens the new
    interval, with the schema's trigger checking that it does not reach back into the old
    one.
    """
    student = world.student_ids[1]
    vanya = world.teacher_ids[0]

    enrollment.assign(student, vanya, room="303", weekday=MON, valid_from="2025-09-01")
    enrollment.end(student, weekday=MON, effective_from="2025-12-01")

    with pytest.raises(NotEnrolled):
        enrollment.move(student, weekday=MON, to_teacher_id=third_teacher,
                        effective_from="2026-02-01")

    enrollment.assign(student, third_teacher, room="302", weekday=MON,
                      valid_from="2026-02-01")

    assert enrollment.teacher_on(student, MONDAY).teacher_id == vanya       # October
    assert enrollment.teacher_on(student, "2026-01-05") is None             # away
    assert enrollment.teacher_on(student, "2026-02-02").teacher_id == third_teacher


def test_a_returning_interval_that_reaches_back_into_the_old_one_is_refused(
    enrollment, world, third_teacher
):
    student = world.student_ids[2]
    enrollment.assign(student, world.teacher_ids[0], room="303", weekday=MON,
                      valid_from="2025-09-01")
    enrollment.end(student, weekday=MON, effective_from="2025-12-01")

    with pytest.raises(OverlappingHistory):
        enrollment.assign(student, third_teacher, room="302", weekday=MON,
                          valid_from="2025-10-01")
