"""The head's summary: three things, from the projections that already compute them.

WHOSE IT IS.  The summary belongs to the head of the room by meaning, not to the teacher
who did the marking: the head is the person who decides what to do about a problem nobody
took and about a child nobody has spoken to for three lessons.  A summary delivered to
somebody who cannot act on it is noise, and the test that fixes that is the one below that
counts who receives it.

WHAT IS IN IT.  Who handed in how much at this lesson; who has been quiet for
``config.SILENT_SESSIONS`` lessons running; which problems almost nobody took.  All three
come from ``core/services/spiski.py`` over ``core/services/progress.py`` -- P5 over P1 --
and the tests below check that the numbers AGREE with those projections rather than
re-deriving them here, because a test that computed the answer a second way would be the
very second-opinion bug P1's differential test exists to close.

WHAT MAY NOT BE IN IT is section 4, and it is checked twice over: once on the vocabulary
and once on the SHAPE, because the vocabulary can be avoided while the shape is violated --
a list of children sorted by how much they handed in is a ranking whatever the words are.
"""

from __future__ import annotations

import config
from core.services.svodka import head_summary


def test_the_summary_goes_to_the_heads_and_only_to_the_heads(svodka, notify_world):
    """One summary per room that has a head, and none to an ordinary teacher.

    The fixture makes the first three teachers the heads of the three rooms and the other
    three ordinary, so «принадлежит СТАРШЕМУ, а не преподавателю» has something to fail on.
    """
    plan = svodka.plan(notify_world.session_ids["2026-09-10"])
    recipients = sorted(n.recipient_id for n in plan.summaries)

    assert recipients == sorted(notify_world.head_teacher_ids)
    assert plan.heads_considered == len(notify_world.head_teacher_ids)

    ordinary = set(notify_world.teacher_ids) - set(notify_world.head_teacher_ids)
    assert not (set(recipients) & ordinary), (
        "an ordinary teacher received the head's summary"
    )
    print(
        "[сводка] старших %d из %d преподавателей · сводок %d"
        % (len(notify_world.head_teacher_ids), plan.teachers_considered, len(plan.summaries))
    )


def test_all_three_blocks_are_present_even_when_empty(svodka, notify_world):
    """An empty block SAYS it is empty rather than disappearing.

    A block that vanishes cannot be told from a block that was never computed, and the
    reader has no way to ask which happened.  On a journal with nothing in it all three are
    empty, which is exactly the run that would hide a missing block.
    """
    plan = svodka.plan(notify_world.session_ids["2026-09-10"])
    text = plan.summaries[0].text

    assert "Сдавали:" in text
    assert "Молчат" in text
    assert "Задачи, которые почти никто не взял:" in text
    assert str(config.SILENT_SESSIONS) in text, (
        "the silence window is named in words so the reader knows what «молчат» measured"
    )


def test_the_numbers_are_the_projections_and_not_a_second_opinion(
    svodka, notify_world, mark_at
):
    """The three blocks agree with ``SpiskiService`` and ``ProgressService``.

    Checked by calling the same projections the service calls and comparing the values, not
    by re-deriving them: two ways of counting one thing is the class of bug this project
    closed once already with a differential test.
    """
    day = "2026-09-10"
    session_id = notify_world.session_ids[day]

    # Two students hand something in; the rest of the room says nothing.
    mark_at(notify_world.student_ids[0], notify_world.problem_ids[0], day,
            teacher_id=notify_world.teacher_ids[0])
    mark_at(notify_world.student_ids[0], notify_world.problem_ids[1], day,
            teacher_id=notify_world.teacher_ids[0])
    mark_at(notify_world.student_ids[1], notify_world.problem_ids[0], day,
            teacher_id=notify_world.teacher_ids[0])

    work = svodka.handed_in(session_id)
    assert work.handed_in == 2, "two students handed in; the fold saw %d" % work.handed_in
    assert work.marks == 3
    assert work.considered == len(notify_world.student_ids)

    counts = {row.student_id: row.count for row in work.students}
    assert counts[notify_world.student_ids[0]] == 2
    assert counts[notify_world.student_ids[1]] == 1

    text = plan_text(svodka, session_id)
    assert "всего сдавали 2 из %d" % len(notify_world.student_ids) in text


def test_marks_of_another_day_are_not_this_lesson(svodka, notify_world, mark_at):
    """The lesson is a day, and a mark from another day belongs to another lesson.

    This is the whole reason the fold cannot be keyed on ``marks.session_id``: production
    writes NULL there, so the day is what ties a mark to a lesson, and a fold that ignored
    it would report the whole term after every evening.
    """
    session_id = notify_world.session_ids["2026-09-10"]
    mark_at(notify_world.student_ids[0], notify_world.problem_ids[0], "2026-09-07",
            teacher_id=notify_world.teacher_ids[0])

    work = svodka.handed_in(session_id)
    assert work.handed_in == 0, (
        "a mark from 2026-09-07 was counted into the lesson of 2026-09-10"
    )
    assert work.considered == len(notify_world.student_ids), (
        "a negative answer must still carry its coverage"
    )


def test_the_hand_in_list_is_alphabetical_and_never_a_ranking(
    svodka, notify_world, mark_at
):
    """Section 4 on the SHAPE, not on the words.

    Ordering children by how much they handed in is a ranking of children in a text an
    adult reads, whatever vocabulary it uses.  The alphabet ranks nobody, so the order is
    by surname -- and the test makes the two orders differ, otherwise it proves nothing.
    """
    day = "2026-09-10"
    session_id = notify_world.session_ids[day]

    # The LAST student by surname hands in the most, so count-order and surname-order
    # disagree; a fold that sorted by count would put him first.
    last = notify_world.student_ids[-1]
    first = notify_world.student_ids[0]
    for problem_id in notify_world.problem_ids[:3]:
        mark_at(last, problem_id, day, teacher_id=notify_world.teacher_ids[0])
    mark_at(first, notify_world.problem_ids[0], day, teacher_id=notify_world.teacher_ids[0])

    work = svodka.handed_in(session_id)
    assert [row.student_id for row in work.students] == [first, last], (
        "the list is ordered by hand-in count, which ranks the children"
    )


def test_the_summary_names_the_silent_and_says_what_the_list_means(
    svodka, notify_world, mark_at
):
    """Silence is the point of the whole feature, and the wording is half of it.

    The list of the silent is the list of those NOBODY HAS SPOKEN TO -- not the list of the
    worst -- and the summary says so in words every time, because it is read by a tired
    adult in a corridor and the wrong reading is the one thing this feature can break.
    """
    # Three lesson days, which is exactly config.SILENT_SESSIONS: below that the silent
    # list is honestly unmeasurable and says so instead of naming anybody.
    speaker = notify_world.student_ids[0]
    for index, day in enumerate(("2026-09-07", "2026-09-10", "2026-09-14")):
        mark_at(speaker, notify_world.problem_ids[index], day,
                teacher_id=notify_world.teacher_ids[0])

    session_id = notify_world.session_ids["2026-09-14"]
    silent = svodka._spiski.silent()  # noqa: SLF001 -- comparing against P5 is the point
    assert silent.enough_days, "three lesson days should be enough to measure silence"
    assert silent.found == len(notify_world.student_ids) - 1

    text = plan_text(svodka, session_id)
    assert "Это те, с кем не поговорили." in text
    assert "всего %d из %d" % (silent.found, silent.considered) in text


def test_the_silent_block_says_when_it_cannot_measure_yet(svodka, notify_world, mark_at):
    """Fewer lesson days than the window is NOT «никто не молчит».

    An empty silent list reads as "everybody is fine", which on the second evening of the
    year is the exact opposite of the truth.  P5 answers ``enough_days=False`` and the
    summary has to say so rather than print an empty list.
    """
    mark_at(notify_world.student_ids[0], notify_world.problem_ids[0], "2026-09-10",
            teacher_id=notify_world.teacher_ids[0])
    text = plan_text(svodka, notify_world.session_ids["2026-09-10"])
    assert "пока нечего мерить" in text


def test_the_graveyard_block_carries_its_threshold(svodka, notify_world):
    """«почти никто не взял» is meaningless without the number that decided it."""
    text = plan_text(svodka, notify_world.session_ids["2026-09-10"])
    assert "порог %d" % config.GRAVEYARD_THRESHOLD in text


def test_the_summary_fits_in_one_telegram_message(svodka, notify_world, mark_at):
    """A summary longer than the API allows is a summary that does not arrive.

    Cut here rather than by Telegram, so a truncated summary is still a delivered one --
    the same rule and the same number ``ops/opoveshchenie.py`` uses for an alarm.
    """
    from core.services.svodka import MAX_TEXT

    day = "2026-09-14"
    for student_id in notify_world.student_ids:
        for problem_id in notify_world.problem_ids:
            mark_at(student_id, problem_id, day, teacher_id=notify_world.teacher_ids[0])

    text = plan_text(svodka, notify_world.session_ids[day])
    assert len(text) <= MAX_TEXT


def test_head_summary_is_a_pure_function_of_its_arguments(svodka, notify_world):
    """The words are built without a database, which is what lets them be checked at all.

    ``head_summary`` takes the four values and returns the text; nothing in it reads a
    store.  A wording rule that could only be tested through SQLite would be tested rarely.
    """
    session_id = notify_world.session_ids["2026-09-10"]
    lesson = svodka.lesson(session_id)
    text = head_summary(
        lesson,
        svodka.handed_in(session_id),
        svodka._spiski.silent(),  # noqa: SLF001
        svodka._spiski.graveyard(),  # noqa: SLF001
    )
    assert text == plan_text(svodka, session_id)


def plan_text(svodka, session_id: int) -> str:
    """The summary as the head actually receives it."""
    plan = svodka.plan(session_id)
    assert plan.summaries, "the world has no head; there is no summary to read"
    return plan.summaries[0].text
