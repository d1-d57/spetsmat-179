"""The four failures that look like «the bot is broken», driven through the real
dispatcher.

Every test here feeds a raw update into the dispatcher that ``bot.app.build`` produces in
production and asserts on what the bot TRIED to send.  Nothing above the Telegram session
is stubbed, so the middleware, the filters, the router ORDER and the services are the
real ones -- which is what makes a green run mean something about the running bot rather
than about a mock of it.

The four, and the test that closes each:

  1. double tap                  -- ``test_two_taps_on_the_same_target_write_one_event``
                                    and ``test_a_redelivered_update_writes_one_event``
  2. the spinner                 -- ``test_a_tap_answers_before_it_redraws``
  3. ``message is not modified`` -- ``test_not_modified_is_swallowed_and_nothing_else_is``
  4. a stale button              -- ``test_a_stale_button_gets_an_answer_and_a_redraw``
"""

from __future__ import annotations

import re

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import TelegramMethod

from bot.callbacks import OP_CLEAR, OP_SOLVE, Done, Mark, Noop, OpenGrid, PickSheet
from core.models import MarkEvent
from infra.repositories import SqliteMarkJournal
from tests.grid.conftest import feed_callback, feed_message

#: A Telegram account bound to nobody.  Used for the "a stranger holds a forwarded
#: button" half of the stale-button test.
STRANGER_TG = 424242


# --------------------------------------------------------------------------- helpers

def _on_the_belt(catalogue) -> list:
    """The students the screen shows: everyone whose status is not ``left``."""
    return [student for student in catalogue.students() if student.status != "left"]


def _first_cell(catalogue):
    """One (student, problem) pair off the current sheet, named the way the bot names it.

    The CURRENT sheet is the one with the largest ``ord`` -- the same rule ``bot/app`` and
    the router use -- so the pair a test taps is a pair a teacher could tap.
    """
    sheet = max(catalogue.sheets(), key=lambda s: s.ord)
    student = _on_the_belt(catalogue)[0]
    problem = catalogue.problems_of_sheet(sheet.id)[0]
    return student, sheet, problem


def _events(connection, student_id: int, problem_id: int) -> list:
    """The raw journal for one cell.  Read on the TEST's connection, not the bot's: a
    write that has not been committed is not a write, and this is where that shows."""
    return SqliteMarkJournal(connection).events(
        student_ids=[student_id], problem_ids=[problem_id]
    )


def _tap(dispatcher, *, bot, tg_id, student_id, problem_id, op, update_id, query_id=None):
    return feed_callback(
        dispatcher,
        bot=bot,
        from_id=tg_id,
        data=Mark(student_id=student_id, task_id=problem_id, op=op).pack(),
        update_id=update_id,
        query_id=query_id,
    )


# ------------------------------------------------------------- 1. the double tap

def test_two_taps_on_the_same_target_write_one_event(
    dispatcher, bot_instance, recorder, seeded_catalogue, seeded_connection, teacher_tg_id
):
    """The button carries the TARGET STATE, so asking twice asks for the same world twice.

    Two DIFFERENT taps -- different query ids, so the transport idempotency key does not
    cover them -- and one journal row.  This is the half that survives a caller with no
    key at all, and it is the reason races are not a subject on this screen.
    """
    student, _sheet, problem = _first_cell(seeded_catalogue)

    for index in (1, 2):
        _tap(
            dispatcher,
            bot=bot_instance,
            tg_id=teacher_tg_id,
            student_id=student.id,
            problem_id=problem.id,
            op=OP_SOLVE,
            update_id=10 + index,
            query_id="tap-%d" % index,
        )

    events = _events(seeded_connection, student.id, problem.id)
    assert [event.event for event in events] == [MarkEvent.ASSERT], (
        "two taps on the same target wrote %d events: %r"
        % (len(events), [event.event for event in events])
    )
    # Both taps still ANSWER: the second one is idempotent in the journal, not silent on
    # the screen.  A silent second tap is the failure this whole screen is built against.
    assert recorder.methods().count("AnswerCallbackQuery") == 2


def test_a_redelivered_update_writes_one_event(
    dispatcher, bot_instance, seeded_catalogue, seeded_connection, teacher_tg_id
):
    """Telegram delivers at least once.

    The SAME ``callback_query.id`` arriving twice is one human tap redelivered, and the
    router derives the idempotency key from it, so the second arrival is answered out of
    the journal.  Unlike the test above, this one would still pass if the target-state
    rule were broken -- and that is the point of having both.
    """
    student, _sheet, problem = _first_cell(seeded_catalogue)

    for update_id in (21, 22):
        _tap(
            dispatcher,
            bot=bot_instance,
            tg_id=teacher_tg_id,
            student_id=student.id,
            problem_id=problem.id,
            op=OP_SOLVE,
            update_id=update_id,
            query_id="one-and-the-same",
        )

    events = _events(seeded_connection, student.id, problem.id)
    assert len(events) == 1
    assert events[0].idempotency_key == "cb:one-and-the-same"


def test_a_repeat_tap_clears_the_cell_and_the_cell_can_be_solved_again(
    dispatcher, bot_instance, seeded_catalogue, seeded_connection, teacher_tg_id
):
    """The undo is a repeat tap, and there is no «сохранить» anywhere.

    A solved cell offers ``op=0``; taking it writes an ``erratum`` -- "this record should
    never have existed", which is what a wrong button IS.  It does NOT write a
    ``retract``: that means "handed in and not defended", a different fact about the
    world, and it would drag the cell into the statistics as a hand-in.
    """
    student, _sheet, problem = _first_cell(seeded_catalogue)

    _tap(dispatcher, bot=bot_instance, tg_id=teacher_tg_id, student_id=student.id,
         problem_id=problem.id, op=OP_SOLVE, update_id=31, query_id="q31")
    _tap(dispatcher, bot=bot_instance, tg_id=teacher_tg_id, student_id=student.id,
         problem_id=problem.id, op=OP_CLEAR, update_id=32, query_id="q32")

    events = _events(seeded_connection, student.id, problem.id)
    assert [event.event for event in events] == [MarkEvent.ASSERT, MarkEvent.ERRATUM]
    assert events[1].reverses_id == events[0].id

    # And back again: the way to put a plus back is a fresh assert, never a resurrection
    # of the struck event.
    _tap(dispatcher, bot=bot_instance, tg_id=teacher_tg_id, student_id=student.id,
         problem_id=problem.id, op=OP_SOLVE, update_id=33, query_id="q33")
    events = _events(seeded_connection, student.id, problem.id)
    assert [event.event for event in events] == [
        MarkEvent.ASSERT, MarkEvent.ERRATUM, MarkEvent.ASSERT
    ]


def test_a_second_clear_on_an_empty_cell_is_harmless(
    dispatcher, bot_instance, seeded_catalogue, seeded_connection, teacher_tg_id
):
    """The clear button is idempotent too, and this is why ``op=0`` means EMPTY rather
    than RETRACTED: ``MarkingService.retract`` on an empty cell RAISES ``NothingToReverse``,
    so a double tap on a clear button would be an exception in a handler -- the exact
    opposite of "harmless by construction"."""
    student, _sheet, problem = _first_cell(seeded_catalogue)

    for index in (41, 42):
        _tap(dispatcher, bot=bot_instance, tg_id=teacher_tg_id, student_id=student.id,
             problem_id=problem.id, op=OP_CLEAR, update_id=index, query_id="q%d" % index)

    assert _events(seeded_connection, student.id, problem.id) == []


# ----------------------------------------------------------------- 2. the spinner

def test_a_tap_answers_before_it_redraws(
    dispatcher, bot_instance, recorder, seeded_catalogue, teacher_tg_id
):
    """Two beats, in this order, and the ORDER is the property.

    The redraw is an API round-trip and the callback query expires in fifteen seconds; a
    silent update with no toast is forbidden outright, because at 800 ms a person cannot
    tell whether the tap counted and taps again.  A test that merely checked both calls
    happened would pass on the broken arrangement.
    """
    student, _sheet, problem = _first_cell(seeded_catalogue)
    _tap(dispatcher, bot=bot_instance, tg_id=teacher_tg_id, student_id=student.id,
         problem_id=problem.id, op=OP_SOLVE, update_id=51, query_id="q51")

    methods = recorder.methods()
    assert "AnswerCallbackQuery" in methods, "the tap was answered by nothing at all"
    assert "EditMessageText" in methods, "the tap changed nothing on the screen"
    assert methods.index("AnswerCallbackQuery") < methods.index("EditMessageText")

    toast = recorder.alerts()[0]
    assert problem.label in toast and student.name in toast, (
        "the toast must name the problem and the student: %r" % toast
    )


def test_the_grid_lives_in_one_message_and_is_redrawn_in_place(
    dispatcher, bot_instance, recorder, seeded_catalogue, teacher_tg_id
):
    """One message for the whole work with a student.

    A new message per tap would push the grid off the screen and cost a scroll in the
    middle of the five-to-fifteen-second seam.  Every redraw therefore edits the SAME
    ``message_id`` and sends nothing.
    """
    student, sheet, problem = _first_cell(seeded_catalogue)
    feed_callback(dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data=OpenGrid(student_id=student.id, sheet_id=sheet.id).pack(),
                  update_id=61, query_id="q61")
    _tap(dispatcher, bot=bot_instance, tg_id=teacher_tg_id, student_id=student.id,
         problem_id=problem.id, op=OP_SOLVE, update_id=62, query_id="q62")

    assert "SendMessage" not in recorder.methods()
    assert {edit["message_id"] for edit in recorder.edits()} == {77}


def test_the_header_counts_what_is_handed_in_and_the_last_action_line_appears(
    dispatcher, bot_instance, recorder, seeded_catalogue, teacher_tg_id
):
    """«Петров Василий · Листок 4д · сдано 1 из 26», and a line naming the last tap.

    The undo lives in that line, not in a «сохранить» button: a confirmation dialog does
    not catch a slip -- it is dismissed by the same reflex that produced the slip.
    """
    student, _sheet, problem = _first_cell(seeded_catalogue)
    _tap(dispatcher, bot=bot_instance, tg_id=teacher_tg_id, student_id=student.id,
         problem_id=problem.id, op=OP_SOLVE, update_id=71, query_id="q71")

    text = recorder.texts()[-1]
    assert student.surname in text and student.name in text
    assert "сдано 1 из" in text, text
    assert "последнее:" in text and problem.label in text, text
    assert re.search(r"\d\d:\d\d", text), "the last-action line must carry a wall clock"


# ---------------------------------------------------- 3. message is not modified

def test_not_modified_is_swallowed_and_nothing_else_is(
    dispatcher, bot_instance, recorder, seeded_catalogue, teacher_tg_id
):
    """Suppressed BY SUBSTRING, never by swallowing ``TelegramBadRequest`` whole.

    "the message was deleted", "the payload is too long" and "the query is too old" all
    arrive as that same class, and a bare ``except TelegramBadRequest`` would hide every
    one of them behind a screen that silently stops updating.
    """
    student, sheet, problem = _first_cell(seeded_catalogue)

    recorder.fail_next_edit = TelegramBadRequest(
        method=_AnyMethod(),
        message="Bad Request: message is not modified: specified new message content "
                "and reply markup are exactly the same",
    )
    _tap(dispatcher, bot=bot_instance, tg_id=teacher_tg_id, student_id=student.id,
         problem_id=problem.id, op=OP_SOLVE, update_id=81, query_id="q81")
    assert "EditMessageText" in recorder.methods()

    recorder.fail_next_edit = TelegramBadRequest(
        method=_AnyMethod(), message="Bad Request: message to edit not found"
    )
    with pytest.raises(TelegramBadRequest, match="message to edit not found"):
        feed_callback(dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                      data=OpenGrid(student_id=student.id, sheet_id=sheet.id).pack(),
                      update_id=82, query_id="q82")


class _AnyMethod(TelegramMethod):
    """A stand-in for the method a ``TelegramBadRequest`` names.

    ``TelegramBadRequest`` requires one, and the router never reads it -- it reads the
    MESSAGE.  Building a real method here would tie the test to whichever call happened
    to fail.
    """

    __returning__ = bool
    __api_method__ = "any"


# ------------------------------------------------------------- 4. a stale button

def test_a_stale_button_gets_an_answer_and_a_redraw(
    dispatcher, bot_instance, recorder, seeded_catalogue, teacher_tg_id
):
    """A hand-made payload from a message older than the schema.

    Without the catch-all router aiogram drops the update: no handler, no log line, and a
    spinner that turns until Telegram gives up.  With it the teacher gets a sentence and
    a working screen in the same tap.  ``zz:`` is deliberately a prefix no factory in
    ``bot/callbacks.py`` owns -- exactly what a payload from a previous schema looks like.
    """
    feed_callback(dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data="zz:1:2:3", update_id=91, query_id="q91")

    alerts = recorder.alerts()
    assert alerts and "устарел" in alerts[0].lower(), alerts
    assert "EditMessageText" in recorder.methods(), "the stale screen was not redrawn"


def test_a_stale_button_in_a_stranger_hand_stops_the_spinner_and_shows_nothing(
    dispatcher, bot_instance, recorder, seeded_catalogue
):
    """The catch-all has no role gate on purpose -- a forwarded button must be answered
    for whoever holds it -- so the REDRAW is what carries the gate instead."""
    feed_callback(dispatcher, bot=bot_instance, from_id=STRANGER_TG,
                  data="zz:1:2:3", update_id=92, query_id="q92")

    assert any("устарел" in alert.lower() for alert in recorder.alerts())
    assert "EditMessageText" not in recorder.methods(), (
        "a stranger was shown the roster by the stale-button path"
    )


def test_the_filler_of_the_last_row_is_not_a_stale_button(
    dispatcher, bot_instance, recorder, seeded_catalogue, teacher_tg_id
):
    """The padding has a real handler, so a stray tap on it dismisses the spinner and says
    nothing -- rather than telling the teacher their screen is out of date, which would be
    a lie about the row they are looking at."""
    feed_callback(dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data=Noop().pack(), update_id=93, query_id="q93")

    assert recorder.methods() == ["AnswerCallbackQuery"]
    assert recorder.alerts() == [""]


# ------------------------------------------------------------ the privacy boundary

def test_a_forged_callback_for_a_foreign_student_is_refused(
    dispatcher, bot_instance, recorder, seeded_catalogue, seeded_connection, roster_path
):
    """``callback_data`` is CLIENT-side data, so this is a request the server receives.

    A confirmed student hand-forges a payload naming another student's id and taps it.
    Nothing is written, nothing is drawn, and the refusal does not depend on comparing the
    forged id with their own -- the screen is closed to students outright, so there is no
    number in the payload whose value could open it.  This is the privacy boundary of the
    project and it is asserted, not assumed.
    """
    roster = dispatcher.workflow_data["roster"]
    victim, sheet, problem = _first_cell(seeded_catalogue)
    intruder_tg = 313131
    pending = roster.submit_student(tg_id=intruder_tg, surname="Чужой", name="Ученик")
    roster.confirm_student(pending)

    feed_callback(
        dispatcher, bot=bot_instance, from_id=intruder_tg,
        data=Mark(student_id=victim.id, task_id=problem.id, op=OP_SOLVE).pack(),
        update_id=101, query_id="q101",
    )
    feed_callback(
        dispatcher, bot=bot_instance, from_id=intruder_tg,
        data=OpenGrid(student_id=victim.id, sheet_id=sheet.id).pack(),
        update_id=102, query_id="q102",
    )

    assert _events(seeded_connection, victim.id, problem.id) == [], (
        "a forged payload wrote a mark on somebody else's cell"
    )
    assert "EditMessageText" not in recorder.methods(), (
        "a forged payload drew somebody else's grid"
    )
    assert recorder.methods().count("AnswerCallbackQuery") == 2, (
        "the refusal must still stop the spinner"
    )
    for alert in recorder.alerts():
        assert victim.surname not in alert and victim.name not in alert, (
            "the refusal leaked the name it was refusing access to: %r" % alert
        )


def test_no_surname_ever_enters_a_payload(
    dispatcher, bot_instance, recorder, seeded_catalogue, teacher_tg_id
):
    """Ids in flight, names on the screen.

    A payload is stored client-side in the message and travels with every forward; a
    surname inside one is a surname that has left the server for good.
    """
    student, sheet, _problem = _first_cell(seeded_catalogue)
    feed_callback(dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data=OpenGrid(student_id=student.id, sheet_id=sheet.id).pack(),
                  update_id=111, query_id="q111")

    surnames = {other.surname for other in _on_the_belt(seeded_catalogue)}
    payloads = [
        button["callback_data"]
        for edit in recorder.edits()
        for row in (edit.get("reply_markup") or {}).get("inline_keyboard", [])
        for button in row
    ]
    assert payloads, "the redraw carried no keyboard at all"
    for payload in payloads:
        assert re.fullmatch(r"[a-z](:-?\d+)*", payload), (
            "a payload that is not purely numeric: %r" % payload
        )
        for surname in surnames:
            assert surname not in payload


# ----------------------------------------------------------------- the conveyor

def test_done_returns_to_the_list_of_students_not_to_a_menu(
    dispatcher, bot_instance, recorder, seeded_catalogue, teacher_tg_id
):
    """«Готово» goes back to the belt.  The next student is one tap away."""
    student, sheet, _problem = _first_cell(seeded_catalogue)
    feed_callback(dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data=Done(sheet_id=sheet.id).pack(), update_id=121, query_id="q121")

    edits = recorder.edits()
    assert edits, "«Готово» redrew nothing"
    payloads = [
        button["callback_data"]
        for row in (edits[-1].get("reply_markup") or {}).get("inline_keyboard", [])
        for button in row
    ]
    opened = [OpenGrid.unpack(payload).student_id for payload in payloads]
    assert opened == [other.id for other in _on_the_belt(seeded_catalogue)]
    assert student.id in opened


def test_the_arrows_carry_the_neighbours_own_id(
    dispatcher, bot_instance, recorder, seeded_catalogue, teacher_tg_id
):
    """A payload names its target, never «the next one».

    A «+1» would be resolved later, against a roster that may have changed since the
    message was drawn -- and would walk from a position the screen no longer shows.
    """
    students = _on_the_belt(seeded_catalogue)
    middle = students[3]
    sheet = max(seeded_catalogue.sheets(), key=lambda s: s.ord)
    feed_callback(dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data=OpenGrid(student_id=middle.id, sheet_id=sheet.id).pack(),
                  update_id=131, query_id="q131")

    keyboard = (recorder.edits()[-1].get("reply_markup") or {})["inline_keyboard"]
    footer = keyboard[-2]
    assert [button["text"].strip("← →") for button in footer] == [
        students[2].surname, "Другой листок", students[4].surname
    ]
    assert OpenGrid.unpack(footer[0]["callback_data"]).student_id == students[2].id
    assert OpenGrid.unpack(footer[2]["callback_data"]).student_id == students[4].id
    assert PickSheet.unpack(footer[1]["callback_data"]).student_id == middle.id


def test_the_first_and_the_last_student_have_no_arrow_into_nothing(
    dispatcher, bot_instance, recorder, seeded_catalogue, teacher_tg_id
):
    students = _on_the_belt(seeded_catalogue)
    sheet = max(seeded_catalogue.sheets(), key=lambda s: s.ord)

    for index, expected in ((0, "→"), (len(students) - 1, "←")):
        recorder.records.clear()
        feed_callback(dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                      data=OpenGrid(student_id=students[index].id, sheet_id=sheet.id).pack(),
                      update_id=141 + index, query_id="q%d" % (141 + index))
        footer = (recorder.edits()[-1].get("reply_markup") or {})["inline_keyboard"][-2]
        assert len(footer) == 2, [button["text"] for button in footer]
        assert any(expected in button["text"] for button in footer)


# ------------------------------------------------------ what may never be written

#: Straight from the mandate, and the same expression the готовности criterion greps for.
FORBIDDEN = re.compile(
    r"рейтинг|percent|процент|badge|streak|leaderboard|очк[иов]|молодец|отлично",
    re.IGNORECASE,
)


def test_nothing_is_written_next_to_a_plus(
    dispatcher, bot_instance, recorder, seeded_catalogue, teacher_tg_id
):
    """No praise, no counter beside the cell, no rating, share, points, level, streak or
    badge -- anywhere in the text or on any button this screen produces.

    Checked on what the bot SENT rather than by grepping the source: a word assembled at
    run time out of two halves would pass the grep and reach the child.
    """
    student, sheet, problem = _first_cell(seeded_catalogue)
    feed_callback(dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data=OpenGrid(student_id=student.id, sheet_id=sheet.id).pack(),
                  update_id=151, query_id="q151")
    _tap(dispatcher, bot=bot_instance, tg_id=teacher_tg_id, student_id=student.id,
         problem_id=problem.id, op=OP_SOLVE, update_id=152, query_id="q152")
    feed_callback(dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data=PickSheet(student_id=student.id).pack(),
                  update_id=153, query_id="q153")

    produced = recorder.texts() + recorder.alerts()
    produced += [
        button["text"]
        for edit in recorder.edits()
        for row in (edit.get("reply_markup") or {}).get("inline_keyboard", [])
        for button in row
    ]
    assert produced, "the screen produced no text at all"
    offenders = [line for line in produced if FORBIDDEN.search(line)]
    assert not offenders, offenders
    assert not any("%" in line for line in produced), produced


def test_a_teacher_opens_the_screen_and_a_stranger_does_not(
    dispatcher, bot_instance, recorder, seeded_catalogue, teacher_tg_id
):
    """The entry point, and the gate on it."""
    feed_message(dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                 text="/setka", update_id=161)
    assert "SendMessage" in recorder.methods()
    first = recorder.texts()[0]
    assert "Листок" in first and "учеников" in first, first

    recorder.records.clear()
    feed_message(dispatcher, bot=bot_instance, from_id=STRANGER_TG,
                 text="/setka", update_id=162)
    for text in recorder.texts():
        assert "учеников" not in text, "a stranger was shown the roster: %r" % text


def test_a_departed_student_is_off_the_belt_and_out_of_the_arrows(
    dispatcher, bot_instance, recorder, seeded_catalogue, seeded_connection, teacher_tg_id
):
    """A student whose status is ``left`` stays in the catalogue and leaves the conveyor.

    Their journal rows point at them and always will, so the row cannot be deleted -- but
    they are not somebody the teacher walks past on a Thursday, and one extra name in the
    list is one extra tap per lesson for the rest of the year.  Both the list and the
    arrows are checked, because the two reading different rosters is exactly how «next»
    starts skipping people.
    """
    belt = _on_the_belt(seeded_catalogue)
    gone = belt[1]
    seeded_connection.execute(
        "update students set status = 'left' where id = ?", (gone.id,)
    )
    seeded_connection.commit()

    sheet = max(seeded_catalogue.sheets(), key=lambda s: s.ord)
    feed_callback(dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data=Done(sheet_id=sheet.id).pack(), update_id=171, query_id="q171")
    listed = [
        OpenGrid.unpack(button["callback_data"]).student_id
        for row in (recorder.edits()[-1].get("reply_markup") or {})["inline_keyboard"]
        for button in row
    ]
    assert gone.id not in listed
    assert listed == [student.id for student in belt if student.id != gone.id]

    recorder.records.clear()
    feed_callback(dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data=OpenGrid(student_id=belt[0].id, sheet_id=sheet.id).pack(),
                  update_id=172, query_id="q172")
    footer = (recorder.edits()[-1].get("reply_markup") or {})["inline_keyboard"][-2]
    forward = [button for button in footer if "→" in button["text"]]
    assert len(forward) == 1
    assert OpenGrid.unpack(forward[0]["callback_data"]).student_id == belt[2].id, (
        "the arrow still points at the student who left"
    )


def test_a_decoration_button_is_answered_but_not_redrawn_over(
    dispatcher, bot_instance, recorder, seeded_catalogue, owner_tg_id
):
    """A label button on somebody ELSE's live screen must not be treated as stale.

    ``bot/handlers/owner.py`` draws one button per pending registration carrying
    ``callback_data="noop"`` -- a caption, not a control -- and no handler claims it.  It
    therefore reaches this catch-all.  Answering it is right: before P4 it was an eternal
    spinner.  REDRAWING over it would replace the owner's moderation list with the grid's
    roster, which is a worse failure than the one being fixed.  The line between the two
    is whether the payload carries fields at all.
    """
    feed_callback(dispatcher, bot=bot_instance, from_id=owner_tg_id,
                  data="noop", update_id=181, query_id="q181")

    assert recorder.methods() == ["AnswerCallbackQuery"], recorder.methods()

    # ...while a payload that DOES carry fields is a stale screen and is redrawn.
    recorder.records.clear()
    feed_callback(dispatcher, bot=bot_instance, from_id=owner_tg_id,
                  data="zz:1:2:3", update_id=182, query_id="q182")
    assert "EditMessageText" in recorder.methods()


def test_two_teachers_on_the_same_student_do_not_share_a_last_action_line(
    dispatcher, bot_instance, recorder, seeded_catalogue, teacher_tg_id
):
    """«последнее: …» is a property of ONE teacher's screen, not of the cell.

    Three teachers share a room and a student can be sent to whoever is free.  If the
    line were read out of the journal, the second teacher would see the first one's tap
    described as their own — and the undo it offers would undo somebody else's work.  It
    lives in the FSM store, which is keyed by chat and user, so this is a property of
    WHERE the line is kept rather than of how it is worded.
    """
    from core.services.roster import Role

    roster = dispatcher.workflow_data["roster"]
    second_tg = 100600
    roster.confirm_teacher(
        roster.submit_teacher(tg_id=second_tg, surname="Учитель", name="Второй",
                              room="каб-1"),
        role=Role.TEACHER,
    )

    student, sheet, problem = _first_cell(seeded_catalogue)
    _tap(dispatcher, bot=bot_instance, tg_id=teacher_tg_id, student_id=student.id,
         problem_id=problem.id, op=OP_SOLVE, update_id=191, query_id="q191")
    assert "последнее:" in recorder.texts()[-1]

    recorder.records.clear()
    feed_callback(dispatcher, bot=bot_instance, from_id=second_tg,
                  data=OpenGrid(student_id=student.id, sheet_id=sheet.id).pack(),
                  update_id=192, query_id="q192")
    text = recorder.texts()[-1]
    assert "последнее:" not in text, (
        "the second teacher was shown the first one's tap as their own: %r" % text
    )
    # The MARK itself is shared, of course -- it is a fact about the student.
    assert "сдано 1 из" in text, text
