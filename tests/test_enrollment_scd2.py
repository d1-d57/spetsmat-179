"""``enrollment`` as a Type 2 slowly-changing dimension, and the two guards on it.

A student's teacher changes during the year.  Stored as a CURRENT value, a reassignment
rewrites the past: every mark the previous teacher ever gave starts reporting under the
new one.  Stored as history over half-open intervals ``[valid_from, valid_to)``, the past
stays put.

THE KEY IS PER LESSON DAY.  The same student may have one teacher on Monday and another
on Thursday -- last year Кахиани was with Ваня on Monday and with Ян on Thursday -- so
``weekday`` is part of the key and not an attribute.  A schema that forgot this would
make that pair of rows an "overlap" and refuse the reality it is supposed to record.

Two guards, and the test exercises both because they cover different cases:
  * the partial unique index catches two OPEN rows -- cheap, read-time-free;
  * the trigger catches two CLOSED intervals that overlap, which no index can express.
"""

from __future__ import annotations

import sqlite3

import pytest

import config


@pytest.fixture
def people(connection, world):
    return world


def enroll(connection, student_id, teacher_id, weekday, valid_from,
           valid_to=config.OPEN_END_DATE, room="301"):
    return connection.execute(
        "insert into enrollment (student_id, teacher_id, room, weekday, valid_from, valid_to) "
        "values (?, ?, ?, ?, ?, ?)",
        (student_id, teacher_id, room, weekday, valid_from, valid_to),
    )


def test_one_student_may_have_two_teachers_on_two_lesson_days(connection, people):
    """The Кахиани case.  Both rows are open at once and both are legal."""
    student = people.student_ids[0]
    monday, thursday = 1, 4
    enroll(connection, student, people.teacher_ids[0], monday, "2026-09-01")
    enroll(connection, student, people.teacher_ids[1], thursday, "2026-09-01")

    rows = connection.execute(
        "select weekday, teacher_id from enrollment where student_id = ? order by weekday",
        (student,),
    ).fetchall()
    assert [(row["weekday"], row["teacher_id"]) for row in rows] == [
        (monday, people.teacher_ids[0]),
        (thursday, people.teacher_ids[1]),
    ]


def test_two_open_rows_for_one_lesson_day_are_refused(connection, people):
    """The cheap guard: the partial unique index on the open row."""
    student = people.student_ids[1]
    enroll(connection, student, people.teacher_ids[0], 1, "2026-09-01")

    with pytest.raises(sqlite3.IntegrityError):
        enroll(connection, student, people.teacher_ids[1], 1, "2026-10-01")


def test_a_reassignment_closes_the_old_row_and_opens_a_new_one(connection, people):
    """The whole point of Type 2: the past keeps the teacher it actually had."""
    student = people.student_ids[2]
    enroll(connection, student, people.teacher_ids[0], 1, "2026-09-01")
    connection.execute(
        "update enrollment set valid_to = '2026-10-01' "
        " where student_id = ? and weekday = 1 and valid_to = ?",
        (student, config.OPEN_END_DATE),
    )
    enroll(connection, student, people.teacher_ids[1], 1, "2026-10-01")

    rows = connection.execute(
        "select teacher_id, valid_from, valid_to from enrollment "
        " where student_id = ? and weekday = 1 order by valid_from",
        (student,),
    ).fetchall()
    assert [(row["valid_from"], row["valid_to"]) for row in rows] == [
        ("2026-09-01", "2026-10-01"),
        ("2026-10-01", config.OPEN_END_DATE),
    ]
    assert rows[0]["teacher_id"] == people.teacher_ids[0]
    assert rows[1]["teacher_id"] == people.teacher_ids[1]


def test_half_open_intervals_touch_without_overlapping(connection, people):
    """``[a, b)`` then ``[b, c)`` is a clean handover and must not trip the trigger.

    Closed-closed intervals would call this an overlap, which is precisely why the
    convention is written down instead of being left to whoever adds the next row.
    """
    student = people.student_ids[3]
    enroll(connection, student, people.teacher_ids[0], 2, "2026-09-01", "2026-10-01")
    enroll(connection, student, people.teacher_ids[1], 2, "2026-10-01", "2026-11-01")

    assert connection.execute(
        "select count(*) from enrollment where student_id = ? and weekday = 2", (student,)
    ).fetchone()[0] == 2


def test_two_closed_intervals_that_overlap_are_refused(connection, people):
    """The expensive guard: no index can express this, so a trigger does."""
    student = people.student_ids[4]
    enroll(connection, student, people.teacher_ids[0], 3, "2026-09-01", "2026-11-01")

    with pytest.raises(sqlite3.IntegrityError, match="overlap"):
        enroll(connection, student, people.teacher_ids[1], 3, "2026-10-01", "2026-12-01")


def test_an_update_cannot_create_an_overlap_either(connection, people):
    """Closing a row is an UPDATE, so the guard has to cover UPDATE as well as INSERT."""
    student = people.student_ids[0]
    enroll(connection, student, people.teacher_ids[0], 5, "2026-09-01", "2026-10-01")
    enroll(connection, student, people.teacher_ids[1], 5, "2026-10-01", "2026-11-01")

    with pytest.raises(sqlite3.IntegrityError, match="overlap"):
        connection.execute(
            "update enrollment set valid_to = '2026-10-15' "
            " where student_id = ? and weekday = 5 and valid_from = '2026-09-01'",
            (student,),
        )


def test_an_inverted_interval_is_refused(connection, people):
    """``valid_from >= valid_to`` is a typo that would otherwise sit there silently."""
    with pytest.raises(sqlite3.IntegrityError):
        enroll(connection, people.student_ids[1], people.teacher_ids[0], 6,
               "2026-11-01", "2026-09-01")


def test_weekday_is_an_iso_weekday(connection, people):
    """Monday = 1 .. Sunday = 7.  A zero-based caller is caught at the door."""
    with pytest.raises(sqlite3.IntegrityError):
        enroll(connection, people.student_ids[1], people.teacher_ids[0], 0, "2026-09-01")
    assert (config.WEEKDAY_MIN, config.WEEKDAY_MAX) == (1, 7)
