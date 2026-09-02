"""The four attendance states, in plain tests.

The red-line of the position is that "present with no marks" and "absent" must come out
of the service as DIFFERENT values.  These tests pin that down with the smallest possible
setup -- one lesson, four students, no journal events except where the test name says so.
"""

from __future__ import annotations

import pytest

from core.services.sessions import SessionsError


def _attendance_row(sessions_service, session_id, student_id, status, teacher_id=None):
    return sessions_service.mark_attendance(
        session_id=session_id,
        student_id=student_id,
        status=status,
        teacher_id=teacher_id,
    )


def test_state_a_present_with_marks(
    sessions_service, sessions_world, connection
):
    """(a) Student is marked present AND has at least one journal event.

    The view must say ``status='был'`` and ``has_marks=True``.  ``present_no_marks``
    must be False.
    """
    session_id = sessions_world.session_id_fri
    student = sessions_world.student_present_with_marks
    problem = sessions_world.problem_ids[0]

    _attendance_row(sessions_service, session_id, student, "был")
    sessions_service._marking.give(student, problem, source="кнопка", session_id=session_id)

    views = sessions_service.attendance_for(session_id)
    view = views[student]
    assert view.status == "был"
    assert view.has_marks is True
    assert view.present_no_marks is False
    assert view.is_marked is True


def test_state_b_present_no_marks(sessions_service, sessions_world):
    """(b) Student is marked present but has NO journal events.

    This is the case the position is ABOUT: a student who came and handed in nothing.
    The view must say ``status='был'`` and ``has_marks=False``, and crucially
    ``present_no_marks`` must be True.  Without this the teacher cannot tell the case
    apart from truancy.
    """
    session_id = sessions_world.session_id_fri
    student = sessions_world.student_present_no_marks

    _attendance_row(sessions_service, session_id, student, "был")

    views = sessions_service.attendance_for(session_id)
    view = views[student]
    assert view.status == "был"
    assert view.has_marks is False
    assert view.present_no_marks is True
    assert view.is_marked is True


def test_state_c_absent_marked(sessions_service, sessions_world):
    """(c) Student is marked absent.  No journal events.

    The view must say ``status='не был'`` and ``has_marks=False``; ``present_no_marks``
    must be False.  Together with state (b) this is the red-line: two DIFFERENT views
    for two DIFFERENT real situations that the old system collapsed.
    """
    session_id = sessions_world.session_id_fri
    student = sessions_world.student_absent

    _attendance_row(sessions_service, session_id, student, "не был")

    views = sessions_service.attendance_for(session_id)
    view = views[student]
    assert view.status == "не был"
    assert view.has_marks is False
    assert view.present_no_marks is False
    assert view.is_marked is True


def test_state_d_no_attendance_row(sessions_service, sessions_world):
    """(d) Student has NO attendance row at all and no journal events.

    The view must NOT be in the dictionary at all -- the caller knows the roster and
    fills the gap with a "nothing" view of its own.  This mirrors the contract of
    ``ProgressService.states_for`` for untouched pairs.
    """
    session_id = sessions_world.session_id_fri
    student = sessions_world.student_no_row

    views = sessions_service.attendance_for(session_id)
    assert student not in views


def test_red_line_present_no_marks_differs_from_absent(
    sessions_service, sessions_world
):
    """THE TEST THAT IS THIS POSITION: (b) and (c) must be two DIFFERENT views.

    (b) and (c) are the two real-world situations the old "by pluses" projection
    collapsed.  If this test is green and the two views come out the same, the
    position has failed regardless of how many other tests are green.
    """
    session_id = sessions_world.session_id_fri
    present = sessions_world.student_present_no_marks
    absent = sessions_world.student_absent

    _attendance_row(sessions_service, session_id, present, "был")
    _attendance_row(sessions_service, session_id, absent, "не был")

    views = sessions_service.attendance_for(session_id)
    b = views[present]
    c = views[absent]

    # The two dataclasses must differ on every attribute that distinguishes the case.
    assert b.status == "был"
    assert c.status == "не был"
    assert b.has_marks is False
    assert c.has_marks is False
    assert b.present_no_marks is True
    assert c.present_no_marks is False
    assert b != c, "the position's red-line: (b) and (c) collapsed to the same view"
