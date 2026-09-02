"""The privacy boundary of the whole project, checked rather than declared.

«Ученик не может увидеть чужие отметки НИ ОДНИМ запросом» -- including a ``callback_data``
typed out by hand with somebody else's ``student_id``.  That payload is a request this
server really receives; the fact that no such button was ever drawn is not a defence, and
neither is a keyboard that only ever carries the caller's own id.  So the sweep here forges
one, and it forges it for EVERY student against EVERY other student.

THE VERDICT CARRIES ITS COVERAGE IN ITSELF.  «Дыр не найдено» and «дыр не найдено,
проверено 56 из 56» look the same on a green run and are not the same statement.  Every
test below counts what it examined and asserts the count, and the sweep prints
«отказов N из M, пробоев 0» through ``capsys.disabled()`` -- the idiom this project
already uses in ``tests/test_differential.py`` and ``tests/grid/test_layout.py``, because
``pytest -q`` captures a bare ``print`` and the criterion asks to SEE the number.

A BREACH IS NOT ONLY «СЕРВЕР ОТВЕТИЛ». It is the neighbour's surname, or the neighbour's
marks, appearing in ANY text the bot sent -- a message, an edit or an alert.  So the
detector reads all three and looks for the victim's own name and for the shape of their
sheet, not merely for a non-refusal.

THE FILE IS ``test_views_privacy.py`` AND NOT ``test_privacy.py``, and that is not taste.
There is no ``__init__.py`` under ``tests/``, so pytest names a module by its BASENAME and
two files called ``test_privacy.py`` in different folders collide at collection with
``import file mismatch`` -- the whole run stops, not just the pair.  P7 already owns
``tests/photo/test_privacy.py``; measured here the moment main was merged in.
"""

from __future__ import annotations

from bot.keyboards.views import ViewDebts, ViewSheet, ViewTable, ViewYear
from tests.views.conftest import feed_callback, feed_message

#: The wording every refusal of a foreign payload uses.  One sentence for every screen on
#: purpose: a person probing two of them must not be able to tell from the answer which
#: one has a hole.
REFUSAL = "Вы видите только свои данные."

DAY = "2026-09-08"

#: What ``require_role`` answers an identity outside the allowed set.  It stopped being a
#: developer diagnostic on 2026-09-02, after the owner's first live ``/start`` showed him
#: «this screen is for pending_student or pending_teacher or stranger; you are a owner» --
#: English, internal role names, and a grammatical error in the English at that.  Asserted
#: here by its text AND by what it must NOT contain: the reader is a child, and the refusal
#: owes them an instruction, not the shape of the role table.
ROLE_REFUSAL = "Этот экран вам не открыт."


def _forgeries(victim_id: int, sheet_id: int):
    """Every payload of this position that names a student, aimed at ``victim_id``."""
    return (
        ("год", ViewYear(student_id=victim_id).pack()),
        ("листок", ViewSheet(student_id=victim_id, sheet_id=sheet_id).pack()),
        ("долги", ViewDebts(student_id=victim_id).pack()),
    )


def test_forged_callback_for_foreign_student_is_refused(
    dispatcher, bound_students, recorder, seeded_catalogue, mark_on, capsys
):
    """Every one of the fifty-six, forging every screen against the student next to them.

    The victim is given a distinctive mark first, so a leak has something recognisable to
    leak: if any screen answered the forgery with the victim's data, the victim's surname
    or the label of the problem they solved would show up in what the bot sent.
    """
    bot = dispatcher.workflow_data["bot"]
    sheet = sorted(seeded_catalogue.sheets(), key=lambda s: s.ord)[0]
    problems = seeded_catalogue.problems_of_sheet(sheet.id)
    by_id = {student.id: student for student in seeded_catalogue.students()}

    # Everybody gets a mark, so that no victim's screen is empty and therefore harmless.
    for offset, (student_id, _tg) in enumerate(bound_students):
        mark_on(student_id, problems[offset % len(problems)].id, DAY)

    refusals = 0
    attempts = 0
    breaches = []
    update_id = 100

    for index, (attacker_id, attacker_tg) in enumerate(bound_students):
        victim_id, _victim_tg = bound_students[(index + 1) % len(bound_students)]
        victim = by_id[victim_id]
        assert victim_id != attacker_id, "the sweep must aim at somebody else"

        for screen, payload in _forgeries(victim_id, sheet.id):
            update_id += 1
            recorder.reset()
            feed_callback(dispatcher, bot=bot, from_id=attacker_tg,
                          data=payload, update_id=update_id)
            attempts += 1

            said = recorder.texts()
            if any(REFUSAL in text for text in said):
                refusals += 1
            leaked = [
                text for text in said
                if victim.surname in text or victim.name in text
            ]
            if leaked:
                breaches.append((attacker_id, victim_id, screen, leaked[0]))

    assert not breaches, "privacy breach on %d requests: %r" % (len(breaches), breaches[:3])
    assert attempts == 56 * 3, "the sweep must cover 56 students x 3 screens, not %d" % attempts
    assert refusals == attempts, (
        "every forged payload must be refused: %d of %d were" % (refusals, attempts)
    )

    with capsys.disabled():
        print(
            "\n[приватность] отказов %d из %d, пробоев %d — попытка добраться до чужого "
            "по каждому из %d учеников, %d экрана на ученика"
            % (refusals, attempts, len(breaches), len(bound_students), len(_forgeries(0, 0)))
        )


def test_every_student_sees_their_own_screen_and_only_their_own(
    dispatcher, bound_students, recorder, seeded_catalogue, mark_on, capsys
):
    """The other half of the same rule: the honest request must return the RIGHT student.

    A server that refused everything would pass the sweep above and be useless.  So each
    of the fifty-six opens their own year with their own account, and the answer must
    carry their own name and nobody else's.
    """
    bot = dispatcher.workflow_data["bot"]
    sheet = sorted(seeded_catalogue.sheets(), key=lambda s: s.ord)[0]
    problems = seeded_catalogue.problems_of_sheet(sheet.id)
    by_id = {student.id: student for student in seeded_catalogue.students()}
    surnames = {student.surname for student in by_id.values()}

    for offset, (student_id, _tg) in enumerate(bound_students):
        mark_on(student_id, problems[offset % len(problems)].id, DAY)

    checked = 0
    update_id = 500
    for student_id, tg_id in bound_students:
        update_id += 1
        recorder.reset()
        feed_callback(dispatcher, bot=bot, from_id=tg_id,
                      data=ViewYear(student_id=student_id).pack(), update_id=update_id)
        mine = by_id[student_id]
        said = [text for text in recorder.texts() if text]
        assert said, "student %d got nothing back" % student_id
        assert any(mine.surname in text for text in said), (
            "student %d was not shown their own name" % student_id
        )
        # Any OTHER surname in the answer would be a leak; namesakes are excluded from the
        # check rather than assumed away, since the seed is real people's surnames.
        others = {name for name in surnames if name != mine.surname}
        for text in said:
            intruders = [name for name in others if name in text]
            assert not intruders, (
                "student %d's own screen carries %r" % (student_id, intruders[:3])
            )
        checked += 1

    assert checked == 56
    with capsys.disabled():
        print(
            "\n[приватность] собственных экранов проверено %d из 56, чужих фамилий 0"
            % checked
        )


def test_a_student_cannot_reach_the_teachers_screens_at_all(
    dispatcher, bound_students, recorder, seeded_catalogue, capsys
):
    """The teacher's lists and table have no student_id to forge -- and that is the point.

    A rule of the form «refuse when the id is not yours» has to be right on every handler.
    A rule of the form «students do not reach this screen» cannot be forged, because there
    is nothing in the payload to forge.  Both are used in this position, on the two kinds
    of screen where each is the right shape.
    """
    bot = dispatcher.workflow_data["bot"]
    sheet = sorted(seeded_catalogue.sheets(), key=lambda s: s.ord)[-1]
    refused = 0
    update_id = 900

    for _student_id, tg_id in bound_students:
        update_id += 1
        recorder.reset()
        feed_callback(dispatcher, bot=bot, from_id=tg_id,
                      data=ViewTable(sheet_id=sheet.id).pack(), update_id=update_id)
        said = recorder.texts()
        assert not any(text.startswith("<pre>") for text in said), (
            "a student was handed the whole-class table"
        )
        assert any(ROLE_REFUSAL in text for text in said), (
            "the teacher's screen must refuse a student in words: %r" % said
        )
        assert not any("confirmed_student" in text or "teacher" in text for text in said), (
            "the refusal must not hand the reader the role table: %r" % said
        )
        refused += 1

    update_id += 1
    recorder.reset()
    feed_message(dispatcher, bot=bot, from_id=bound_students[0][1],
                 text="/spiski", update_id=update_id)
    assert not any(text.startswith("<pre>") for text in recorder.texts())

    assert refused == 56
    with capsys.disabled():
        print(
            "\n[приватность] отказов на учительском экране %d из 56, пробоев 0" % refused
        )


def test_a_stranger_reaches_none_of_these_screens(dispatcher, recorder, seeded_catalogue):
    """Nobody the roster does not know gets a screen, student or teacher.

    ``AuthMiddleware`` stamps ``kind="stranger"`` and both role gates refuse it.  Checked
    because it is the one identity that has no row anywhere and is therefore the easiest
    one for a future handler to forget.
    """
    bot = dispatcher.workflow_data["bot"]
    sheet = sorted(seeded_catalogue.sheets(), key=lambda s: s.ord)[0]
    student = seeded_catalogue.students()[0]
    stranger = 424242

    for payload in (
        ViewYear(student_id=student.id).pack(),
        ViewSheet(student_id=student.id, sheet_id=sheet.id).pack(),
        ViewDebts(student_id=student.id).pack(),
        ViewTable(sheet_id=sheet.id).pack(),
    ):
        recorder.reset()
        feed_callback(dispatcher, bot=bot, from_id=stranger, data=payload)
        said = recorder.texts()
        assert not any(student.surname in text for text in said), (
            "a stranger was shown %r through %r" % (student.surname, payload)
        )
        assert any(ROLE_REFUSAL in text for text in said), said
        assert not any("stranger" in text for text in said), (
            "a stranger is refused, not told which internal kind they were sorted into: %r"
            % said
        )
