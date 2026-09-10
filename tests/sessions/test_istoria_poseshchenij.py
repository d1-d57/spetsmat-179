"""``core.services.istoria_poseshchenij.IstoriyaService`` against the REAL schema.

Same testing philosophy as ``tests/sostav/test_sostav_na_den.py``: real repositories, not
fakes, for everything that already has a shipped adapter (``SostavService`` and its three
ports). The one port this position adds (``TeacherAbsences``) has no shipped adapter yet --
its real SQLite adapter lives beside the web section
(``veb.razdely.istoria_zanyatij``) and is exercised end to end by ``tests/veb/
test_istoria_zanyatij.py``; here it is a thin real-SQL fake reading the same
``teacher_attendance`` table, so a schema mismatch between the two would show up as a
failure in THIS file too, not go unnoticed because a mock always agrees with itself.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from core.models import Session
from core.services.istoria_poseshchenij import (
    IstoriyaService,
    zanyatie_zaversheno,
)
from core.services.sostav_na_den import SostavService
from infra.enrollment_repo import SqliteEnrollmentRepo
from infra.room_repo import SqliteAttendance, SqliteSessions

MONDAY = "2026-09-07"   # slot 1, past
THURSDAY = "2026-09-10"  # slot 2, "today" in these tests, lesson 13:10-15:00 MSK


class _TeacherAbsencesFake:
    """Reads the real ``teacher_attendance`` table -- see module docstring."""

    def __init__(self, connection) -> None:
        self._c = connection

    def otsutstvuyushchie(self, session_id: int) -> frozenset:
        return frozenset(
            r[0] for r in self._c.execute(
                "select teacher_id from teacher_attendance "
                "where session_id = ? and status = 'не был'", (session_id,)))


def _student(connection, surname: str) -> int:
    return connection.execute(
        "insert into students (surname, name, class, status) values (?, ?, ?, ?)",
        (surname, surname, "9Л", "active"),
    ).lastrowid


def _s_aktiven(connection) -> None:
    # 🔴 `teachers.aktiven` IS SCHEMA DRIFT, LIKE `teachers.gruppa` IN
    # `test_kartochka.py`: no migration declares it (`grep aktiven migrations/` — zero
    # hits), but the live база carries it and `veb/obshchee/karkas.py::sobrat_kontekst`
    # already filters every teacher list by it. Added here by hand, same fix as there.
    try:
        connection.execute("alter table teachers add column aktiven integer not null default 1")
    except Exception:
        pass


def _teacher(connection, name: str, aktiven: int = 1) -> int:
    _s_aktiven(connection)
    return connection.execute(
        "insert into teachers (name, aktiven) values (?, ?)", (name, aktiven),
    ).lastrowid


def _standing(connection, student_id, teacher_id, slot, room="302",
              valid_from="2026-09-01", valid_to="9999-12-31") -> None:
    connection.execute(
        "insert into enrollment (student_id, teacher_id, room, slot, valid_from, valid_to) "
        "values (?, ?, ?, ?, ?, ?)",
        (student_id, teacher_id, room, slot, valid_from, valid_to),
    )


def _session(connection, held_on, kind="обычное") -> int:
    return connection.execute(
        "insert into sessions (held_on, kind) values (?, ?)", (held_on, kind),
    ).lastrowid


def _deviation(connection, session_id, student_id, teacher_id, status) -> None:
    connection.execute(
        "insert into attendance (session_id, student_id, teacher_id, status) "
        "values (?, ?, ?, ?)",
        (session_id, student_id, teacher_id, status),
    )


def _teacher_absent(connection, session_id, teacher_id) -> None:
    connection.execute(
        "insert into teacher_attendance (session_id, teacher_id, status, answered_at) "
        "values (?, ?, 'не был', ?)",
        (session_id, teacher_id, "2026-09-07T10:00:00+03:00"),
    )


#: "Now" for these tests: Thursday 04:15 MSK -- before the lesson starts (13:10), matching
#: the live база state this заход was checked against (§ПЛАН).
SEICHAS = datetime(2026, 9, 10, 1, 15, tzinfo=timezone.utc)


@pytest.fixture
def istoriya(connection):
    """A factory, not a ready service: `teachers.aktiven` (schema drift, see `_s_aktiven`)
    has to exist before it can be filtered on, and it is only added by `_teacher()`/
    `_s_aktiven()` calls a test makes AFTER fixtures resolve. Call this once, last, right
    before `.sostavit(...)`."""
    def _sobrat():
        _s_aktiven(connection)
        sostav = SostavService(
            enrollment=SqliteEnrollmentRepo(connection),
            sessions=SqliteSessions(connection),
            attendance=SqliteAttendance(connection),
        )
        return IstoriyaService(
            sostav=sostav,
            teacher_absences=_TeacherAbsencesFake(connection),
            active_teacher_ids=[r[0] for r in connection.execute(
                "select id from teachers where aktiven = 1")],
        )
    return _sobrat


# --------------------------------------------------------------- "прошедшее" (past)


def test_lesson_over_by_calendar_day_is_past():
    assert zanyatie_zaversheno(MONDAY, seichas=SEICHAS) is True


def test_todays_lesson_not_yet_started_is_not_past():
    """Fri 04:15 MSK, lesson starts 13:10 -- not over."""
    assert zanyatie_zaversheno(THURSDAY, seichas=SEICHAS) is False


def test_todays_lesson_after_it_ends_is_past():
    posle = datetime(2026, 9, 10, 12, 5, tzinfo=timezone.utc)  # 15:05 MSK
    assert zanyatie_zaversheno(THURSDAY, seichas=posle) is True


def test_cancelled_session_does_not_become_a_column(connection, istoriya):
    _session(connection, MONDAY, kind="отменённое")
    result = istoriya().sostavit([], seichas=SEICHAS)
    assert result.dni == ()


# ------------------------------------------------------------------- student grid


def test_no_attendance_row_means_present_with_the_standing_teacher(connection, istoriya):
    """The definition named in ## ПЛАН: no row = «как обычно» = present."""
    child = _student(connection, "Тихий")
    teacher = _teacher(connection, "Обычный")
    _standing(connection, child, teacher, slot=1)
    session = Session(id=_session(connection, MONDAY), held_on=MONDAY, kind="обычное")

    result = istoriya().sostavit([session], seichas=SEICHAS)

    assert result.dni == (MONDAY,)
    yacheika = result.shkolniki[child][MONDAY]
    assert yacheika.prisutstvoval is True
    assert yacheika.prepodavatel_id == teacher
    assert yacheika.nekuda_det is False


def test_explicit_absence_is_a_krestik(connection, istoriya):
    child = _student(connection, "Болеющий")
    teacher = _teacher(connection, "Обычный")
    _standing(connection, child, teacher, slot=1)
    sid = _session(connection, MONDAY)
    _deviation(connection, sid, child, None, "не был")
    session = Session(id=sid, held_on=MONDAY, kind="обычное")

    result = istoriya().sostavit([session], seichas=SEICHAS)

    yacheika = result.shkolniki[child][MONDAY]
    assert yacheika.prisutstvoval is False
    assert yacheika.prepodavatel_id is None


def test_a_days_override_teacher_wins_over_the_standing_one(connection, istoriya):
    child = _student(connection, "Переведённый")
    obychnyj = _teacher(connection, "Обычный")
    segodnyashnij = _teacher(connection, "Замена")
    _standing(connection, child, obychnyj, slot=1)
    sid = _session(connection, MONDAY)
    _deviation(connection, sid, child, segodnyashnij, "был")
    session = Session(id=sid, held_on=MONDAY, kind="обычное")

    result = istoriya().sostavit([session], seichas=SEICHAS)

    yacheika = result.shkolniki[child][MONDAY]
    assert yacheika.prisutstvoval is True
    assert yacheika.prepodavatel_id == segodnyashnij


def test_nekuda_det_is_a_named_defect_not_a_silent_absence(connection, istoriya):
    """Present, group-of-the-day set, but nobody assigned -- ``nekuda_det``.

    Criterion 3 of the ЗАДАЧА: this must not read the same as either галочка (with a
    teacher) or крестик.
    """
    child = _student(connection, "Ничей")
    sid = _session(connection, MONDAY)
    # No standing row at all, no deviation -- but the roster still names him active, and
    # SostavService without a Roster port would drop him silently. Named in ## ВОПРОСЫ:
    # the roster port is not wired at the veb layer's IstoriyaService construction site
    # for this exact reason and stays a documented limitation there, not invented here.
    _deviation(connection, sid, child, None, "был")
    session = Session(id=sid, held_on=MONDAY, kind="обычное")

    result = istoriya().sostavit([session], seichas=SEICHAS)

    yacheika = result.shkolniki[child][MONDAY]
    assert yacheika.prisutstvoval is True
    assert yacheika.prepodavatel_id is None
    assert yacheika.nekuda_det is True
    assert result.nekuda_det_vsego == 1


# ------------------------------------------------------------------ teacher grid


def test_teacher_who_taught_someone_is_present(connection, istoriya):
    child = _student(connection, "Ученик")
    teacher = _teacher(connection, "Принимающий")
    _standing(connection, child, teacher, slot=1)
    sid = _session(connection, MONDAY)
    session = Session(id=sid, held_on=MONDAY, kind="обычное")

    result = istoriya().sostavit([session], seichas=SEICHAS)

    yacheika = result.prepodavateli[teacher][MONDAY]
    assert yacheika.prisutstvoval is True
    assert yacheika.ucheniki == (child,)


def test_teacher_marked_absent_is_a_krestik_even_with_students_standing(
        connection, istoriya):
    child = _student(connection, "Ученик")
    teacher = _teacher(connection, "Заболевший")
    _standing(connection, child, teacher, slot=1)
    sid = _session(connection, MONDAY)
    _teacher_absent(connection, sid, teacher)
    session = Session(id=sid, held_on=MONDAY, kind="обычное")

    result = istoriya().sostavit([session], seichas=SEICHAS)

    yacheika = result.prepodavateli[teacher][MONDAY]
    assert yacheika.prisutstvoval is False
    assert yacheika.ucheniki == ()


def test_teacher_with_nobody_assigned_that_day_is_a_krestik(connection, istoriya):
    """Named limitation (## ПЛАН, criterion 6): indistinguishable from a scheduled day off."""
    teacher = _teacher(connection, "Пустой")
    sid = _session(connection, MONDAY)
    session = Session(id=sid, held_on=MONDAY, kind="обычное")

    result = istoriya().sostavit([session], seichas=SEICHAS)

    assert result.prepodavateli[teacher][MONDAY].prisutstvoval is False


def test_inactive_teacher_is_not_a_row(connection, istoriya):
    _teacher(connection, "Уволенный", aktiven=0)
    sid = _session(connection, MONDAY)
    session = Session(id=sid, held_on=MONDAY, kind="обычное")

    result = istoriya().sostavit([session], seichas=SEICHAS)

    assert len(result.prepodavateli) == 0
