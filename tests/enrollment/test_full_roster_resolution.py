"""The readiness criterion, on the real roster: 56 students x 2 lesson days = 112.

The world here is not synthetic.  ``seed/students.csv`` and ``seed/teachers.csv`` are the
anonymised catalogue of last year's conduit that lives in git — fifty-six children,
eighteen teachers, three rooms — and the point of running against it rather than against
five invented students is coverage: a resolution that works on a hand-built pair and
falls over on a roster is a resolution nobody has actually asked a hard question.

EVERY STUDENT GETS TWO DIFFERENT TEACHERS, one on Monday and one on Thursday.  That is
the Кахиани shape at full size, and it is what a schema without ``weekday`` in the key
could not express at all.

A NEGATIVE VERDICT MUST CARRY ITS COVERAGE.  "no errors found" and "no errors found,
112 of 112 resolved" look the same and are not: zero resolutions against a non-empty
roster is RED.  So the count is asserted, printed, and printed with its denominator.
"""

from __future__ import annotations

import pytest

import config
from core.services import seeding
from core.services.enrollment import EnrollmentService
from infra.enrollment_repo import SqliteEnrollmentRepo

from fakes import MON, MONDAY, THU, THURSDAY

#: The lesson days of the conduit, and the two dates the roster is resolved on.
LESSON_DAYS = ((MON, MONDAY), (THU, THURSDAY))


@pytest.fixture
def roster(connection):
    """The real seed loaded into a migrated database: 56 students, 18 teachers."""
    counts = seeding.seed_catalogue(connection)
    assert counts.students_written == 56, counts
    assert counts.teachers_written == 18, counts
    return counts


def _real_teachers(connection):
    """The seventeen people, without the technical ``отсутствует`` placeholder.

    That row exists so the importer has somewhere to put a mark whose teacher column was
    blank; enrolling children with it would be inventing a teacher who is by definition
    absent.
    """
    rows = [row for row in seeding.read_teachers() if (row.get("technical") or "0") != "1"]
    return [
        (seeding.teacher_id(connection, row["name"].strip()), row["room"].strip())
        for row in rows
    ]


def _students(connection):
    return [
        seeding.student_id(connection, row["surname"].strip(), row["name"].strip())
        for row in seeding.read_students()
    ]


#: When the season starts for a student who was there from the first sheet.
SEASON_START = "2025-09-01"


def _enroll_whole_roster(service, connection, starts=None):
    """Two open intervals per student, on two lesson days, with two different teachers.

    The teacher of a lesson day is picked round-robin, and the Thursday offset is seven
    against seventeen teachers — coprime, so no student ever draws the same person twice
    and the "one teacher on Monday, another on Thursday" case is exercised by all
    fifty-six of them rather than by one lucky index.

    ``starts`` overrides the first day for named students, which is how a mid-year
    arrival is expressed: his interval simply begins later, and the dates before it
    resolve to nobody because no row covers them.
    """
    starts = starts or {}
    teachers = _real_teachers(connection)
    students = _students(connection)
    expected = {}
    for index, student in enumerate(students):
        for offset, (weekday, _day) in zip((0, 7), LESSON_DAYS):
            teacher, room = teachers[(index + offset) % len(teachers)]
            service.assign(student, teacher, room=room, weekday=weekday,
                           valid_from=starts.get(student, SEASON_START))
            expected[(student, weekday)] = (teacher, room)
    return students, expected


def test_the_whole_roster_resolves_on_both_lesson_days(connection, roster, capsys):
    service = EnrollmentService(SqliteEnrollmentRepo(connection))
    students, expected = _enroll_whole_roster(service, connection)

    asked = resolved = errors = 0
    failures = []
    for weekday, day in LESSON_DAYS:
        answers = service.resolve_many(students, day)
        for student in students:
            asked += 1
            answer = answers[student]
            if answer is None:
                errors += 1
                failures.append("student %s has no teacher on %s" % (student, day))
                continue
            resolved += 1
            if (answer.teacher_id, answer.room, answer.weekday) != (
                expected[(student, weekday)] + (weekday,)
            ):
                errors += 1
                failures.append(
                    "student %s on %s resolved to %s/%s, enrolled with %s"
                    % (student, day, answer.teacher_id, answer.room,
                       expected[(student, weekday)])
                )

    with capsys.disabled():
        print("\nразрешено %d из %d, ошибок %d" % (resolved, asked, errors))

    # Zero resolutions against a non-empty roster is RED, not green.
    assert asked == 112, "expected 56 students x 2 lesson days, asked %d" % asked
    assert resolved > 0, "the roster is not empty and nothing resolved"
    assert (resolved, errors) == (112, 0), "\n".join(failures)


def test_every_student_of_the_roster_has_two_different_teachers(connection, roster):
    """The Кахиани property at full size: 56 students, Monday teacher != Thursday teacher."""
    service = EnrollmentService(SqliteEnrollmentRepo(connection))
    students, _expected = _enroll_whole_roster(service, connection)

    monday = service.resolve_many(students, MONDAY)
    thursday = service.resolve_many(students, THURSDAY)

    same = [
        student
        for student in students
        if monday[student].teacher_id == thursday[student].teacher_id
    ]
    assert same == [], "%d of %d students drew the same teacher twice" % (
        len(same), len(students)
    )
    assert all(service.lesson_days_of(student) == [MON, THU] for student in students)


def test_a_wednesday_resolves_to_nobody_for_the_whole_roster(connection, roster):
    """There are two lessons a week.  A day that is not one of them is not an error."""
    service = EnrollmentService(SqliteEnrollmentRepo(connection))
    students, _expected = _enroll_whole_roster(service, connection)

    wednesday = service.resolve_many(students, "2025-10-08")
    assert set(wednesday) == set(students)
    assert all(answer is None for answer in wednesday.values())


def test_the_two_real_movements_of_last_year(connection, roster):
    """Гамаюнова left after sheet 6, Пирогов arrived from sheet 6 — the whole year's churn.

    Both are named in the задание and both are in the seed (``first_sheet`` 1 and 6).
    They are the two shapes this service has to get right on real data: an interval that
    ends without a successor, and one that begins in the middle of the year.  Neither is
    a deletion — deleting Гамаюнова's row would lose the teacher of every mark she made
    in October, which is the same defect seen from the other side.
    """
    service = EnrollmentService(SqliteEnrollmentRepo(connection))
    pirogov = seeding.student_id(connection, "Пирогов", "Константин")
    gamayunova = seeding.student_id(connection, "Гамаюнова", "Софья")
    assert gamayunova is not None and pirogov is not None

    # Пирогов joined at sheet 6, in November; everybody else was there from September.
    _students, _expected = _enroll_whole_roster(
        service, connection, starts={pirogov: "2025-11-03"}
    )

    # HE ARRIVED MID-YEAR.  October has no row for him and answers with nobody, which is
    # not the same as an error and not the same as "some teacher".
    assert service.teacher_on(pirogov, MONDAY) is None
    assert service.teacher_on(pirogov, THURSDAY) is None
    assert service.teacher_on(pirogov, "2025-11-03") is not None
    assert service.teacher_on(pirogov, "2025-11-06") is not None
    assert service.lesson_days_of(pirogov) == [MON, THU]

    # SHE LEFT.  The intervals are closed, not removed, so October still knows who taught
    # her while May correctly knows nobody did.
    octobers_teacher = service.teacher_on(gamayunova, MONDAY).teacher_id
    service.end(gamayunova, weekday=MON, effective_from="2025-12-01")
    service.end(gamayunova, weekday=THU, effective_from="2025-12-01")

    assert service.teacher_on(gamayunova, MONDAY).teacher_id == octobers_teacher
    assert service.teacher_on(gamayunova, "2025-12-08") is None
    assert service.teacher_on(gamayunova, "2026-05-04") is None
    assert service.lesson_days_of(gamayunova) == []
    assert len(service.history_of(gamayunova)) == 2


def test_a_move_inside_the_full_roster_touches_exactly_one_pair(connection, roster):
    """One (student, lesson day) moves; the other fifty-five students do not shift."""
    service = EnrollmentService(SqliteEnrollmentRepo(connection))
    students, _expected = _enroll_whole_roster(service, connection)

    before = {
        student: service.resolve_many(students, day)[student]
        for _weekday, day in LESSON_DAYS
        for student in students
    }
    mover = students[0]
    elsewhere = [row for row in _real_teachers(connection)
                 if row[0] != service.teacher_on(mover, MONDAY).teacher_id][0]
    service.move(mover, weekday=MON, to_teacher_id=elsewhere[0],
                 effective_from="2025-12-01", room=elsewhere[1])

    # October: nothing anywhere has changed, the mover included.
    assert {
        student: service.resolve_many(students, day)[student]
        for _weekday, day in LESSON_DAYS
        for student in students
    } == before
    # December: exactly the mover's Monday is different.
    assert service.teacher_on(mover, "2025-12-08").teacher_id == elsewhere[0]
    assert service.teacher_on(mover, "2025-12-11").teacher_id == before[mover].teacher_id
