"""Six teachers, two states each: who gets the question and who must not.

THIS FILE IS THE ГОТОВНОСТИ CRITERION OF THE POSITION, and it is written so that it CAN
fail.  «6 преподавателей × 2 состояния = 12 проверок, ложных отправок 0» -- the twelve are
walked explicitly and the coverage is printed, because "ложных отправок 0" and "ложных
отправок 0, проверено 12 из 12" are different claims and only the second one can be
believed.  A world that quietly shrank to two teachers would turn the first into a lie
without any test going red; the fixture asserts the six, and the count below is computed
from what was actually examined rather than written down as a twelve.

THE TWO STATES, AND WHY THEY ARE THE RIGHT PAIR.

* **marked nothing** -- gets the question.  He may simply have forgotten, and he may
  equally have come and taken nobody; the message does not decide which, it asks.
* **marked something** -- must NOT get it.  This is the false-send the count is about: a
  question sent to somebody who plainly was there reads as a reproach for no reason, and
  section 2 of the задание is entirely about not producing that.
"""

from __future__ import annotations

from core.models import CellState, MarkEvent
from core.services.svodka import PRESENT, ABSENT


def test_six_teachers_two_states_twelve_checks(svodka, notify_world, mark_at, capsys):
    """The whole grid: each of the six teachers, in each of the two states.

    Each teacher is examined twice -- once on a lesson he marked at and once on a lesson he
    did not -- and the two lessons are different days, so the states cannot bleed into each
    other through a shared row.  Twelve checks, and the number printed is counted rather
    than asserted from memory.
    """
    marked_day, quiet_day = "2026-09-07", "2026-09-10"
    marked_session = notify_world.session_ids[marked_day]
    quiet_session = notify_world.session_ids[quiet_day]

    # STATE A: on the first lesson every one of the six wrote a mark.
    for index, teacher_id in enumerate(notify_world.teacher_ids):
        mark_at(
            notify_world.student_ids[index],
            notify_world.problem_ids[index],
            marked_day,
            teacher_id=teacher_id,
        )

    # STATE B: on the second lesson nobody wrote anything at all.

    asked_when_marked = {
        t.id for t in svodka.teachers_without_marks(marked_session)
    }
    asked_when_quiet = {
        t.id for t in svodka.teachers_without_marks(quiet_session)
    }

    checks = 0
    false_sends = 0
    for teacher_id in notify_world.teacher_ids:
        # State A -- he marked, so he must not be asked.  A hit here is a FALSE SEND.
        if teacher_id in asked_when_marked:
            false_sends += 1
        assert teacher_id not in asked_when_marked, (
            "teacher %d wrote a mark at the lesson of %s and was asked anyway"
            % (teacher_id, marked_day)
        )
        checks += 1

        # State B -- he marked nothing, so the question is his.
        assert teacher_id in asked_when_quiet, (
            "teacher %d wrote nothing at the lesson of %s and was not asked"
            % (teacher_id, quiet_day)
        )
        checks += 1

    assert checks == 12, "the criterion is 12 checks; this run made %d" % checks
    print(
        "[уведомления] преподавателей %d × состояний 2 = проверок %d из 12 · "
        "ложных отправок %d"
        % (len(notify_world.teacher_ids), checks, false_sends)
    )
    assert false_sends == 0


def test_the_question_is_about_a_fact_not_about_a_duty(svodka, notify_world):
    """Section 2's red line, checked on the words themselves.

    «Вы были сегодня на занятии?», not «вы забыли поставить отметки».  The bookkeeping was
    started for the sake of preservation and not of control, and the first message that
    reads as control ends the willingness to use it.  So the text may not mention marks at
    all, and may not accuse.
    """
    plan = svodka.plan(notify_world.session_ids["2026-09-10"])
    questions = plan.questions
    assert questions, "nobody marked anything; every teacher should have been asked"

    for notification in questions:
        text = notification.text.lower()
        assert "были" in text and "занятии" in text, notification.text
        for accusation in ("забыл", "не отмет", "должн", "обязан", "почему вы"):
            assert accusation not in text, (
                "the question reads as a reproach (%r): %r" % (accusation, notification.text)
            )
        # It asks about presence, so it must not talk about marks at all.
        assert "отметк" not in text, notification.text


def test_both_answers_are_offered_and_both_are_legitimate(svodka, notify_world):
    """«был» is a legitimate outcome: he could have come and taken nobody."""
    plan = svodka.plan(notify_world.session_ids["2026-09-10"])
    for notification in plan.questions:
        assert notification.buttons == [(PRESENT, PRESENT), (ABSENT, ABSENT)]


def test_the_answer_lands_in_attendance_and_is_correctable(svodka, notify_world):
    """The answer goes into the register, and a teacher may correct himself.

    Attendance is kept apart from marks exactly for this case, and «не был» followed by
    «был» is a correction rather than a second fact: he tapped, then remembered he had
    looked in for ten minutes.
    """
    session_id = notify_world.session_ids["2026-09-10"]
    teacher_id = notify_world.teacher_ids[0]

    svodka.record_presence(session_id, teacher_id, ABSENT)
    rows = svodka.presence_for(session_id)
    assert [(r.teacher_id, r.status) for r in rows] == [(teacher_id, ABSENT)]

    svodka.record_presence(session_id, teacher_id, PRESENT)
    rows = svodka.presence_for(session_id)
    assert [(r.teacher_id, r.status) for r in rows] == [(teacher_id, PRESENT)], (
        "a correction must overwrite the teacher's own row, not add a second one"
    )


def test_a_teacher_who_answered_is_not_asked_again(svodka, notify_world):
    """The question exists to be answered once.

    A second copy of it after the answer is precisely the reminder-of-a-duty section 2
    forbids -- and «был» is an answer, so answering it must silence the question just as
    firmly as marking would have.
    """
    session_id = notify_world.session_ids["2026-09-10"]
    teacher_id = notify_world.teacher_ids[0]

    assert teacher_id in {t.id for t in svodka.teachers_without_marks(session_id)}
    svodka.record_presence(session_id, teacher_id, PRESENT)
    assert teacher_id not in {t.id for t in svodka.teachers_without_marks(session_id)}


def test_an_imported_mark_is_not_this_evening(svodka, notify_world, mark_at):
    """Last year's book must not answer for a teacher who was not here tonight.

    All of the import shares a single ``valid_at``; if that day collides with a lesson day,
    counting it would silence the question for a teacher who marked nothing this evening.
    The rule is P5's and this test is the carrier of it on the notification path.
    """
    day = "2026-09-10"
    session_id = notify_world.session_ids[day]
    teacher_id = notify_world.teacher_ids[0]

    mark_at(
        notify_world.student_ids[0],
        notify_world.problem_ids[0],
        day,
        teacher_id=teacher_id,
        source="импорт",
    )
    assert teacher_id in {t.id for t in svodka.teachers_without_marks(session_id)}, (
        "an imported row was counted as tonight's work"
    )


def test_a_struck_mark_is_not_work(svodka, notify_world, mark_at):
    """An ``erratum`` says the record should never have existed.

    Leaving the struck row standing would let a mistyped button answer for a teacher who
    in fact wrote nothing -- and it is the same rule ``handed_in`` obeys, so the two halves
    of one lesson cannot disagree about what happened at it.  ``CellState.EMPTY`` is the
    target that writes an ``erratum`` (``core/services/marking.EVENT_FOR_TARGET``), which
    is how a teacher un-does a wrong button in production.
    """
    day = "2026-09-10"
    session_id = notify_world.session_ids[day]
    teacher_id = notify_world.teacher_ids[0]

    mark_at(
        notify_world.student_ids[0], notify_world.problem_ids[0], day,
        teacher_id=teacher_id,
    )
    assert teacher_id not in {t.id for t in svodka.teachers_without_marks(session_id)}

    outcome = mark_at(
        notify_world.student_ids[0], notify_world.problem_ids[0], day,
        teacher_id=teacher_id, state=CellState.EMPTY,
    )
    assert outcome.written and outcome.mark.event is MarkEvent.ERRATUM, (
        "the fixture did not actually write an erratum; the test below would pass vacuously"
    )
    assert teacher_id in {t.id for t in svodka.teachers_without_marks(session_id)}, (
        "a mark struck by an erratum still answered for the teacher"
    )
