"""THE TEST THAT IS THIS POSITION.

A student is marked in October by teacher A.  In December he is moved to teacher B.  The
question is then asked again: who received the October marks?

The answer must still be A.  If it comes back B, the position has failed regardless of
everything else that is green, because that is precisely the defect the position exists
to remove — an assignment held as a CURRENT VALUE means a reassignment silently rewrites
who worked with whom in October, and every statistic about the year rewrites itself along
with it.

The marks here are made through the real ``MarkingService`` and the real journal rather
than inserted by hand, so that the attribution being checked is the one the bot will
actually produce.
"""

from __future__ import annotations

import config
from core.models import CellState

from fakes import MON, MONDAY

#: The four Mondays of October 2025, as the instants a mark carries: 18:30 Moscow.
OCTOBER_LESSONS = (
    "2025-10-06T15:30:00Z",
    "2025-10-13T15:30:00Z",
    "2025-10-20T15:30:00Z",
    "2025-10-27T15:30:00Z",
)
DECEMBER_LESSON = "2025-12-08T15:30:00Z"
MOVED_ON = "2025-12-01"


def test_moving_a_student_in_december_does_not_change_who_marked_him_in_october(
    enrollment, enrollment_repo, marking, journal, world, connection
):
    student = world.student_ids[0]
    teacher_a, teacher_b = world.teacher_ids
    problems = world.problems_by_sheet[world.sheet_ids[0]]

    # September: the student sits with A on Mondays.
    enrollment.assign(student, teacher_a, room="303", slot=MON, valid_from="2025-09-01")

    # October: A marks four problems, one per lesson.
    for lesson, problem in zip(OCTOBER_LESSONS, problems):
        outcome = marking.give(
            student, problem, source="кнопка", teacher_id=teacher_a, valid_at=lesson
        )
        assert outcome.written and outcome.state is CellState.SOLVED

    before = {
        mark.id: enrollment.teacher_at(student, mark.valid_at).teacher_id
        for mark in journal.events([student])
    }
    assert set(before.values()) == {teacher_a}

    # December: the student is moved to B.
    move = enrollment.move(
        student, slot=MON, to_teacher_id=teacher_b, effective_from=MOVED_ON, room="302"
    )
    assert (move.closed.teacher_id, move.opened.teacher_id) == (teacher_a, teacher_b)

    # THE QUESTION, ASKED AGAIN.
    after = {
        mark.id: enrollment.teacher_at(student, mark.valid_at).teacher_id
        for mark in journal.events([student])
    }
    assert after == before, (
        "the October marks changed hands when the student was moved in December: "
        "the assignment is being read as a current value and the past has been rewritten"
    )
    assert set(after.values()) == {teacher_a}

    # NEGATIVE CONTROL.  A resolution that always answered with the first row it found
    # would have passed everything above.  A December lesson must resolve to B.
    assert enrollment.teacher_at(student, DECEMBER_LESSON).teacher_id == teacher_b


def test_the_move_added_a_row_and_did_not_edit_one(enrollment, world, connection):
    """Two rows where there was one, and the first still says what it always said."""
    student = world.student_ids[1]
    teacher_a, teacher_b = world.teacher_ids

    enrollment.assign(student, teacher_a, room="303", slot=MON, valid_from="2025-09-01")
    enrollment.move(student, slot=MON, to_teacher_id=teacher_b,
                    effective_from=MOVED_ON, room="302")

    rows = connection.execute(
        "select teacher_id, room, valid_from, valid_to from enrollment "
        " where student_id = ? and slot = ? order by valid_from",
        (student, MON),
    ).fetchall()
    assert [tuple(row) for row in rows] == [
        (teacher_a, "303", "2025-09-01", MOVED_ON),
        (teacher_b, "302", MOVED_ON, config.OPEN_END_DATE),
    ]


def test_the_journal_itself_is_untouched_by_a_move(
    enrollment, marking, journal, world
):
    """The marks carry ``teacher_id`` too, and a move must not reach it either.

    The journal is append-only by trigger, so an attempt would raise rather than pass
    quietly — this pins that no attempt is made, and that the count and the authorship of
    the October events are the same objects before and after.
    """
    student = world.student_ids[2]
    teacher_a, teacher_b = world.teacher_ids
    problems = world.problems_by_sheet[world.sheet_ids[0]]

    enrollment.assign(student, teacher_a, room="303", slot=MON, valid_from="2025-09-01")
    for lesson, problem in zip(OCTOBER_LESSONS, problems):
        marking.give(student, problem, source="кнопка", teacher_id=teacher_a,
                     valid_at=lesson)
    before = [(mark.id, mark.teacher_id, mark.valid_at) for mark in journal.events([student])]

    enrollment.move(student, slot=MON, to_teacher_id=teacher_b,
                    effective_from=MOVED_ON, room="302")

    after = [(mark.id, mark.teacher_id, mark.valid_at) for mark in journal.events([student])]
    assert after == before
    assert len(after) == len(OCTOBER_LESSONS)


def test_who_taught_in_october_is_a_query_and_never_a_stored_column(connection):
    """There is no "current teacher" anywhere, and this is what says so out loud.

    A stored copy of the answer is the exact bug this position removes, so the absence is
    asserted rather than left to review: no column on ``students``, and nothing on
    ``enrollment`` but the interval itself.
    """
    student_columns = {
        row["name"] for row in connection.execute("pragma table_info(students)")
    }
    assert not {name for name in student_columns if "teacher" in name.lower()}

    enrollment_columns = {
        row["name"] for row in connection.execute("pragma table_info(enrollment)")
    }
    assert enrollment_columns == {
        "id", "student_id", "teacher_id", "room", "slot", "valid_from", "valid_to"
    }


def test_a_student_moved_twice_still_answers_correctly_for_each_stretch(
    enrollment, world, connection
):
    """Three intervals, three answers, and the middle one is the interesting case."""
    student = world.student_ids[3]
    teacher_a, teacher_b = world.teacher_ids
    cursor = connection.execute(
        "insert into teachers (name, aka, is_owner) values ('teacher-2', 't2', 0)"
    )
    teacher_c = cursor.lastrowid

    enrollment.assign(student, teacher_a, room="303", slot=MON, valid_from="2025-09-01")
    enrollment.move(student, slot=MON, to_teacher_id=teacher_b,
                    effective_from="2025-11-03", room="302")
    enrollment.move(student, slot=MON, to_teacher_id=teacher_c,
                    effective_from="2026-02-02", room="203")

    assert enrollment.teacher_on(student, "2025-09-08").teacher_id == teacher_a
    assert enrollment.teacher_on(student, MONDAY).teacher_id == teacher_a
    assert enrollment.teacher_on(student, "2025-11-03").teacher_id == teacher_b
    assert enrollment.teacher_on(student, "2025-12-08").teacher_id == teacher_b
    assert enrollment.teacher_on(student, "2026-02-02").teacher_id == teacher_c
    assert enrollment.teacher_on(student, "2025-08-25") is None
