"""The two layers, composed: what the distribution screen reads before anybody arrives.

These tests run against the REAL schema and the REAL repositories, not fakes.  The claim
under test is a claim about SQL semantics as much as about Python — the half-open
interval, the ``unique (session_id, student_id)`` upsert, the slot of a Thursday — and a
fake that answered the way the service expects would prove only that the service agrees
with itself.
"""

from __future__ import annotations

import pytest

from core.services.sostav_na_den import (
    OTSUTSTVUET,
    PRISUTSTVUET,
    SostavService,
    is_lesson_day,
    nearest_lesson,
    slot_of,
)
from infra.enrollment_repo import SqliteEnrollmentRepo
from infra.room_repo import SqliteAttendance, SqliteSessions

MONDAY = "2026-09-07"
THURSDAY = "2026-09-10"
SATURDAY = "2026-09-12"


@pytest.fixture
def sostav(connection):
    return SostavService(
        enrollment=SqliteEnrollmentRepo(connection),
        sessions=SqliteSessions(connection),
        attendance=SqliteAttendance(connection),
    )


def _student(connection, surname: str) -> int:
    cursor = connection.execute(
        "insert into students (surname, name, class, status) values (?, ?, ?, ?)",
        (surname, surname, "9Л", "active"),
    )
    return cursor.lastrowid


def _teacher(connection, name: str) -> int:
    cursor = connection.execute("insert into teachers (name) values (?)", (name,))
    return cursor.lastrowid


def _standing(connection, student_id: int, teacher_id: int, slot: int,
              room: str = "302", valid_from: str = "2026-09-01",
              valid_to: str = "9999-12-31") -> None:
    connection.execute(
        "insert into enrollment (student_id, teacher_id, room, slot, valid_from, valid_to) "
        "values (?, ?, ?, ?, ?, ?)",
        (student_id, teacher_id, room, slot, valid_from, valid_to),
    )


def _session(connection, held_on: str) -> int:
    return connection.execute(
        "insert into sessions (held_on, kind) values (?, 'обычное')", (held_on,)
    ).lastrowid


def _deviation(connection, session_id: int, student_id: int,
               teacher_id, status: str) -> None:
    connection.execute(
        "insert into attendance (session_id, student_id, teacher_id, status) "
        "values (?, ?, ?, ?)",
        (session_id, student_id, teacher_id, status),
    )


# --------------------------------------------------------------------- the slot of a day


def test_thursday_resolves_to_slot_two_and_not_to_iso_weekday_four():
    """The regression this module exists to not repeat.

    ``migrations/003`` mapped weekday 4 to slot 2, and the live base carries only slots 1
    and 2.  Code that passes the ISO weekday in as the slot asks for slot 4 and gets an
    empty school every Thursday — silently, because "nobody is enrolled" and "the query
    asked the wrong question" look identical from above.
    """
    assert slot_of(MONDAY) == 1
    assert slot_of(THURSDAY) == 2
    assert slot_of(SATURDAY) is None
    assert is_lesson_day(MONDAY) and not is_lesson_day(SATURDAY)


def test_the_nearest_lesson_is_today_until_the_lesson_ends_then_the_next_one():
    """Р4 of the ТЗ: mid-lesson correction is a working scenario, not documentation."""
    assert nearest_lesson(MONDAY, lesson_over=False) == MONDAY
    assert nearest_lesson(MONDAY, lesson_over=True) == THURSDAY
    # A day that is not a lesson day at all never resolves to itself.
    assert nearest_lesson(SATURDAY) == "2026-09-14"


# ------------------------------------------------------------------- the composition


def test_a_lesson_with_no_deviations_reads_exactly_the_standing_arrangement(
        connection, sostav):
    """The quiet lesson: the layer is empty and the screen is still fully populated.

    This is the property that makes Р1 work — the system is correct when nobody uses it.
    """
    child = _student(connection, "Тихий")
    teacher = _teacher(connection, "Обычный")
    _standing(connection, child, teacher, slot=1)

    day = sostav.sostav(MONDAY)

    assert day.session_id is None
    assert len(day.mesta) == 1
    mesto = day.mesta[0]
    assert mesto.segodnya == teacher and mesto.obychno == teacher
    assert not mesto.otklonenie and not mesto.u_drugogo and not mesto.nekuda_det
    assert day.otkloneniya == ()


def test_a_child_handed_to_another_teacher_today_keeps_his_standing_teacher_visible(
        connection, sostav):
    """ТЗ §3.3: «обычно у ‹имя›» must survive next to today's answer, not be overwritten."""
    child = _student(connection, "Переехавший")
    usual = _teacher(connection, "Обычный")
    today = _teacher(connection, "Сегодняшний")
    _standing(connection, child, usual, slot=1)
    session_id = _session(connection, MONDAY)
    _deviation(connection, session_id, child, today, PRISUTSTVUET)

    mesto = sostav.sostav(MONDAY).mesta[0]

    assert mesto.obychno == usual, "the standing teacher must still be readable"
    assert mesto.segodnya == today
    assert mesto.u_drugogo and mesto.otklonenie
    assert not mesto.nekuda_det, "he is with somebody: nothing for a human to decide"


def test_a_child_marked_absent_is_with_nobody_and_does_not_redden(connection, sostav):
    """ТЗ §4, and it is the whole point of the third state: absent is not lost."""
    child = _student(connection, "Болеющий")
    usual = _teacher(connection, "Обычный")
    _standing(connection, child, usual, slot=1)
    session_id = _session(connection, MONDAY)
    _deviation(connection, session_id, child, None, OTSUTSTVUET)

    mesto = sostav.sostav(MONDAY).mesta[0]

    assert mesto.otmechen_otsutstvuyushchim
    assert mesto.segodnya is None
    assert mesto.obychno == usual
    assert not mesto.nekuda_det, "a child marked absent must NOT be red"
    assert sostav.sostav(MONDAY).krasnye == ()


def test_a_child_with_no_standing_teacher_and_no_absence_is_the_only_red(
        connection, sostav):
    """«Некуда деть» — the one state that requires a human, and it is not invented here.

    It is what 2026-09-07 produced in the live base: a standing row closed with no
    replacement written.
    """
    child = _student(connection, "Осиротевший")
    teacher = _teacher(connection, "Бывший")
    # Closed this very morning, half-open interval: it does not cover MONDAY.
    _standing(connection, child, teacher, slot=1, valid_to=MONDAY)
    session_id = _session(connection, MONDAY)
    _deviation(connection, session_id, child, None, PRISUTSTVUET)

    day = sostav.sostav(MONDAY)

    assert len(day.krasnye) == 1
    assert day.krasnye[0].student_id == child
    assert day.krasnye[0].obychno is None


def test_returning_a_child_to_normal_is_the_deletion_of_a_row(connection, sostav):
    """ТЗ §2, consequence 2.  Nobody has to remember whom he belonged to."""
    child = _student(connection, "Выздоровевший")
    usual = _teacher(connection, "Обычный")
    other = _teacher(connection, "Сегодняшний")
    _standing(connection, child, usual, slot=1)
    session_id = _session(connection, MONDAY)
    _deviation(connection, session_id, child, other, PRISUTSTVUET)
    assert sostav.sostav(MONDAY).mesta[0].segodnya == other

    connection.execute("delete from attendance where session_id = ? and student_id = ?",
                       (session_id, child))

    mesto = sostav.sostav(MONDAY).mesta[0]
    assert mesto.segodnya == usual, "he returns to his standing teacher by himself"
    assert not mesto.otklonenie


def test_a_correction_of_the_standing_layer_reaches_the_lesson_by_itself(
        connection, sostav):
    """ТЗ §2, consequence 3: divergence of the layers is impossible by construction."""
    child = _student(connection, "Никем не тронутый")
    before = _teacher(connection, "Прежний")
    after = _teacher(connection, "Новый")
    _standing(connection, child, before, slot=1, valid_to="2026-09-05")
    _standing(connection, child, after, slot=1, valid_from="2026-09-05")
    _session(connection, MONDAY)              # a lesson exists, and it says nothing

    assert sostav.sostav(MONDAY).mesta[0].segodnya == after


def test_the_lesson_layer_never_touches_the_standing_table(connection, sostav):
    """The defect of 2026-09-07, stated as a test rather than as a promise."""
    child = _student(connection, "Гость")
    usual = _teacher(connection, "Обычный")
    today = _teacher(connection, "Сегодняшний")
    _standing(connection, child, usual, slot=1)
    before = connection.execute("select * from enrollment").fetchall()

    session_id = _session(connection, MONDAY)
    _deviation(connection, session_id, child, today, PRISUTSTVUET)
    sostav.sostav(MONDAY)

    after = connection.execute("select * from enrollment").fetchall()
    assert [tuple(r) for r in after] == [tuple(r) for r in before]


def test_load_is_counted_by_who_is_actually_here(connection, sostav):
    """ТЗ §4: overload on a lesson counts the present, not the standing list."""
    teacher = _teacher(connection, "Загруженный")
    other = _teacher(connection, "Свободный")
    present, absent, moved = (_student(connection, n)
                              for n in ("Пришёл", "Заболел", "Ушёл"))
    for child in (present, absent, moved):
        _standing(connection, child, teacher, slot=1)
    session_id = _session(connection, MONDAY)
    _deviation(connection, session_id, absent, None, OTSUTSTVUET)
    _deviation(connection, session_id, moved, other, PRISUTSTVUET)

    po = sostav.sostav(MONDAY).po_prepodavatelyam()

    assert len(po[teacher]) == 1, "three on the standing list, one actually here"
    assert len(po[other]) == 1


def test_a_day_that_is_not_a_lesson_day_composes_to_nothing(connection, sostav):
    """Р2 says any date may be opened; a Saturday is simply empty, not an error."""
    child = _student(connection, "Кто угодно")
    teacher = _teacher(connection, "Кто угодно")
    _standing(connection, child, teacher, slot=1)

    day = sostav.sostav(SATURDAY)

    assert day.slot is None and day.mesta == ()
