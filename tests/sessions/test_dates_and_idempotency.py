"""Lesson lifecycle, attendance idempotency, and date refusals.

A back-dated mark asks for the date and may be spread across several days.  P1's
journal already carries two times (``valid_at`` and ``recorded_at``); the service for
sessions is what USES them.  These tests pin that down.

The criterion of readiness spells out four cases for back-dated marks that must each
raise ``InvalidLessonDate``:

    (1) ``valid_at`` in the future
    (2) ``valid_at`` earlier than the sheet's ``issued_at``

And the SECOND CLOCK (``recorded_at``) must really be second: a back-dated mark must
stamp ``valid_at`` at the lesson's day and ``recorded_at`` at today, and the two
times must DIFFER.  A service that quietly sets them equal passes a naive test and
destroys the distinction P1 built.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from core.isotime import parse_iso
from core.services.sessions import (
    InvalidLessonDate,
    LessonNotFound,
    SessionsError,
)

from tests.sessions.conftest import LESSON_DAY_FRI, LESSON_DAY_MON, TODAY_ISO


# =========================================================================== lessons


def test_create_lesson_round_trip(sessions_service, connection):
    """A lesson created today is findable by date and by id, and lists in recent."""
    from datetime import date as _date
    today = _date(2026, 9, 4)
    created = sessions_service.create_lesson(today, "обычное")
    assert created.held_on == today.isoformat()
    assert created.kind == "обычное"

    found = sessions_service.lesson_on(today)
    assert found is not None
    assert found.id == created.id

    again = sessions_service.lesson(created.id)
    assert again.id == created.id

    recent = sessions_service.recent_lessons(limit=5)
    assert any(r.id == created.id for r in recent)


def test_create_lesson_refuses_unknown_kind(sessions_service):
    with pytest.raises(SessionsError) as raised:
        sessions_service.create_lesson(date(2026, 9, 4), "митинг")
    assert "kind" in str(raised.value)


def test_create_lesson_refuses_future_date(sessions_service):
    """A lesson cannot be created for a date that has not yet happened.

    The clock is frozen at 2026-09-04; a request for 2026-09-05 is a request from the
    future and is refused.
    """
    with pytest.raises(InvalidLessonDate):
        sessions_service.create_lesson(date(2026, 9, 5), "обычное")


def test_lesson_on_returns_none_when_no_lesson(sessions_service):
    """A date with no lesson is None, not an error."""
    assert sessions_service.lesson_on(date(2026, 1, 1)) is None


def test_lesson_by_unknown_id_raises(sessions_service):
    with pytest.raises(LessonNotFound):
        sessions_service.lesson(99999)


# ======================================================== attendance idempotency


def test_attendance_second_tap_same_status_is_idempotent(
    sessions_service, sessions_world
):
    """A second tap of the SAME status is a no-op: written=False, changed=False."""
    session_id = sessions_world.session_id_fri
    student = sessions_world.student_present_no_marks

    first = sessions_service.mark_attendance(
        session_id=session_id, student_id=student, status="был"
    )
    second = sessions_service.mark_attendance(
        session_id=session_id, student_id=student, status="был"
    )

    assert first.written is True
    assert first.changed is True
    assert second.written is False
    assert second.changed is False
    assert first.row.id == second.row.id


def test_attendance_second_tap_other_status_updates(
    sessions_service, sessions_world, connection
):
    """A second tap of the OTHER status overwrites the row, does not insert another.

    This is the case the contract spells out: a teacher who first tapped ``не был``
    and corrected to ``был`` after the student actually arrived has not made a
    mistake.  The schema's ``unique(session_id, student_id)`` would otherwise raise
    IntegrityError; the adapter does INSERT-or-UPDATE.
    """
    session_id = sessions_world.session_id_fri
    student = sessions_world.student_present_no_marks

    sessions_service.mark_attendance(
        session_id=session_id, student_id=student, status="не был"
    )
    second = sessions_service.mark_attendance(
        session_id=session_id, student_id=student, status="был"
    )

    assert second.written is False
    assert second.changed is True
    assert second.row.status == "был"

    count = connection.execute(
        "select count(*) from attendance where session_id = ? and student_id = ?",
        (session_id, student),
    ).fetchone()[0]
    assert count == 1, "the second tap must UPDATE, not INSERT a second row"


def test_attendance_refuses_unknown_status(sessions_service, sessions_world):
    session_id = sessions_world.session_id_fri
    student = sessions_world.student_present_no_marks
    with pytest.raises(SessionsError):
        sessions_service.mark_attendance(
            session_id=session_id, student_id=student, status="опоздал"
        )


# ======================================================= back-dated marks (Section 3)


def test_back_dated_mark_keeps_two_distinct_times(
    sessions_service, sessions_world, connection
):
    """A back-dated mark stamps ``valid_at`` = lesson's day and ``recorded_at`` = today.

    The two times MUST differ.  A service that quietly sets them equal passes a naive
    test and destroys the distinction P1 built: with both equal, "this mark was
    entered a day late" stops having an answer.
    """
    from core.services.sessions import MarkLessonItem
    from datetime import date as _date

    session_id = sessions_world.session_id_fri  # 2026-09-04
    student = sessions_world.student_present_with_marks
    problem = sessions_world.problem_ids[0]

    # Clock is anchored at 2026-09-04T08:00:00Z.  Use the Monday lesson (2026-09-02)
    # as a back-dated target: "valid_at" lands two days before "recorded_at".
    monday = sessions_world.session_id_mon
    held_on = LESSON_DAY_MON
    outcomes = sessions_service.record_marks_for_lesson(
        monday,
        [MarkLessonItem(student_id=student, problem_id=problem, valid_on=held_on)],
    )
    assert len(outcomes) == 1
    assert outcomes[0].written is True

    row = connection.execute(
        "select valid_at, recorded_at from marks where id = ?",
        (outcomes[0].mark.id,),
    ).fetchone()
    assert row["valid_at"] != row["recorded_at"], (
        "valid_at and recorded_at must differ: the mark was entered for an EARLIER day"
    )
    # valid_at must be the lesson's day at 00:00:00Z, recorded_at must be today.
    assert row["valid_at"].startswith("2026-09-02")
    assert row["recorded_at"].startswith("2026-09-04")


def test_back_dated_mark_refuses_future_date(sessions_service, sessions_world):
    """A ``valid_on`` later than today is refused."""
    from core.services.sessions import MarkLessonItem

    student = sessions_world.student_present_with_marks
    problem = sessions_world.problem_ids[0]

    with pytest.raises(InvalidLessonDate):
        sessions_service.record_marks_for_lesson(
            sessions_world.session_id_fri,
            [MarkLessonItem(student_id=student, problem_id=problem,
                            valid_on=date(2026, 9, 10))],
        )


def test_multi_day_batch_preserves_per_item_valid_at(
    sessions_service, sessions_world, connection
):
    """A batch may be spread over several days: each item carries its own ``valid_at``.

    Monday's mark and Friday's mark must end up with TWO DIFFERENT ``valid_at`` values
    in the journal.  A service that collapses the batch to one date is wrong by
    construction.

    Two different students are used -- one for Monday, one for Friday -- so P1's
    semantic idempotency (a second ``SOLVED`` on the same cell does not double-write)
    does not collapse the rows.
    """
    from core.services.sessions import MarkLessonItem

    student_mon = sessions_world.student_present_with_marks
    student_fri = sessions_world.student_present_no_marks
    problem = sessions_world.problem_ids[0]

    sessions_service.record_marks_for_lesson(
        sessions_world.session_id_mon,
        [MarkLessonItem(student_id=student_mon, problem_id=problem, valid_on=LESSON_DAY_MON)],
    )
    sessions_service.record_marks_for_lesson(
        sessions_world.session_id_fri,
        [MarkLessonItem(student_id=student_fri, problem_id=problem, valid_on=LESSON_DAY_FRI)],
    )

    rows = connection.execute(
        "select student_id, valid_at from marks order by id"
    ).fetchall()
    assert len(rows) == 2
    by_student = {r["student_id"]: r["valid_at"] for r in rows}
    assert by_student[student_mon].startswith("2026-09-02"), by_student
    assert by_student[student_fri].startswith("2026-09-04"), by_student
    assert by_student[student_mon] != by_student[student_fri], (
        "a multi-day batch must keep distinct valid_at per item, not collapse them"
    )


def test_back_dated_mark_refuses_pre_issued_via_sheet(
    sessions_service, sessions_world, connection
):
    """A ``valid_on`` before the sheet's ``issued_at`` is refused, with a lesson in place.

    The sheet was issued on 2026-09-01.  We fabricate a lesson on 2026-08-30, supply
    it as ``session_id``, and ask the service to record a mark for 2026-08-30 against
    a problem on the sheet.  The service must refuse, because the problem did not
    exist on 2026-08-30.
    """
    from core.services.sessions import MarkLessonItem

    pre_issued_day = date(2026, 8, 30)
    cursor = connection.execute(
        "insert into sessions (held_on, kind) values (?, ?)",
        (pre_issued_day.isoformat(), "обычное"),
    )
    pre_issued_session_id = cursor.lastrowid

    student = sessions_world.student_present_with_marks
    problem = sessions_world.problem_ids[0]

    with pytest.raises(InvalidLessonDate) as raised:
        sessions_service.record_marks_for_lesson(
            pre_issued_session_id,
            [MarkLessonItem(student_id=student, problem_id=problem,
                            valid_on=pre_issued_day)],
        )
    assert "issued_at" in str(raised.value) or "sheet" in str(raised.value)
