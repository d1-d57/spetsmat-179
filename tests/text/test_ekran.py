"""The screen: a typed record in, a table, taps, and one button that reaches the journal.

WHAT EVERY TEST HERE IS REALLY ABOUT.  «Отметка НИКОГДА не пишется в базу без подтверждения
человеком» is the third thing the interview finalised and the most important rule of the
project, and it is a property nobody can see by reading the router -- it is a property of
the JOURNAL after a typed message has been through the whole path.  So these tests drive
real updates through a real dispatcher over the real seed, and then look in the journal.

The second thing they are about is narrower and belongs to this channel alone.  Buttons,
photo and voice are all channels a teacher OPENS: they tap a menu, they send a picture,
they hold the microphone.  Text is the channel they are already in -- the same box they
use to type «спасибо» and «а когда следующее занятие?».  A router that answered every
typed message with a confirmation table would not be a fourth входа, it would be the end
of every other conversation with the bot.  Half of this file is therefore about what this
screen REFUSES to answer.
"""

from __future__ import annotations

import importlib
import pkgutil

import pytest

from aiogram.filters.callback_data import CallbackData

import config
from core.services import bystryj_tekst as tekst
from tests.text.conftest import OWNER_LINES, OWNER_MESSAGE, feed_callback, feed_text


def events_of(marking):
    return marking._journal.events()  # noqa: SLF001 -- the journal is what the rule is about


def table_of(dispatcher):
    """The stored draft of the one teacher these tests use."""
    from aiogram.fsm.storage.base import StorageKey

    from bot.routers.text_input import DRAFT_SLOT

    storage = dispatcher.storage
    key = StorageKey(bot_id=0, chat_id=100500, user_id=100500)
    import asyncio

    data = asyncio.get_event_loop().run_until_complete(storage.get_data(key))
    return data.get(DRAFT_SLOT)


def cell_payloads(recorder):
    """Every ``tc:…`` payload the last drawn keyboard offered, in order."""
    keyboards = recorder.keyboards()
    if not keyboards:
        return []
    return [
        button["callback_data"]
        for row in keyboards[-1]
        for button in row
        if button.get("callback_data", "").startswith("tc:")
    ]


# =============================================================================
#  THE TABLE APPEARS, AND NOTHING IS WRITTEN
# =============================================================================

def test_a_typed_record_becomes_a_table_and_writes_nothing(
    text_dispatcher, bot_instance, recorder, teacher_tg_id, marking
):
    """The whole point of the screen, in one test.

    A record the bot understood perfectly still touches nothing: the table appears, it says
    so in words, and the journal is empty until a human presses a button.
    """
    feed_text(text_dispatcher, bot=bot_instance, from_id=teacher_tg_id,
              text="Катя Долкирева 2а, 2б, 4")

    text = "\n".join(recorder.texts())
    assert "Долгирева" in text
    assert "не записано" in text
    assert events_of(marking) == [], "a draft reached the journal without a confirmation"


def test_the_owners_own_four_lines_become_four_rows_on_one_screen(
    text_dispatcher, bot_instance, recorder, teacher_tg_id, catalogue
):
    """The message the owner will actually paste tomorrow, end to end.

    Four blocks over four lines, each resolving to the child the готовности criterion
    names, all four shown at once.  Shown WHOLE and not paginated: a teacher who has to
    scroll to see what a machine read into their message will confirm without reading it,
    and the confirmation is the only thing standing between a parser and the journal.
    """
    feed_text(text_dispatcher, bot=bot_instance, from_id=teacher_tg_id, text=OWNER_MESSAGE)

    stored = table_of(text_dispatcher)
    assert [row["student_id"] for row in stored["rows"]] == [
        student_id for _, student_id, _, _ in OWNER_LINES
    ]

    shown = "\n".join(recorder.texts())
    for _, _, surname, _ in OWNER_LINES:
        assert surname in shown, "«%s» is in the table but not on the screen" % surname


def test_the_procherk_row_says_in_words_that_the_child_was_here(
    text_dispatcher, bot_instance, recorder, teacher_tg_id
):
    """`Влад Быков —` must READ as a statement, not look like a failure to parse.

    A row that merely came out empty says «ничего не разобрал», which is the opposite of
    what was typed.  The distinction P6 owns in the database has to survive onto the glass,
    otherwise the teacher retypes the line and the явка is lost twice.
    """
    feed_text(text_dispatcher, bot=bot_instance, from_id=teacher_tg_id, text="Влад Быков —")

    shown = "\n".join(recorder.texts())
    assert "не сдал ничего" in shown
    assert "явок: 1" in shown


def test_a_label_from_another_sheet_is_shown_with_the_sheet_it_came_from(
    text_dispatcher, bot_instance, recorder, teacher_tg_id, catalogue
):
    """`Аня Бочарова [3д] 5, 12` -- the bracket moves the sheet, and the buttons say so.

    A button reading plain «5» gives the teacher no way to see that the plus is about to
    land on a листок other than the one in their hand, and that is precisely the mistake
    the bracket exists to prevent.
    """
    feed_text(text_dispatcher, bot=bot_instance, from_id=teacher_tg_id,
              text="Аня Бочарова [3д] 5, 12")

    stored = table_of(text_dispatcher)
    row = stored["rows"][0]
    assert row["student_id"] == 9
    assert row["sheet_marker"] == "3д"
    assert all(cell["sheet_number"] == "3д" for cell in row["cells"]), row["cells"]
    assert "3д" in "\n".join(recorder.texts())


# =============================================================================
#  TAPS CHANGE THE TABLE AND NOTHING ELSE
# =============================================================================

def test_a_tap_toggles_a_cell_and_still_writes_nothing(
    text_dispatcher, bot_instance, recorder, teacher_tg_id, marking
):
    feed_text(text_dispatcher, bot=bot_instance, from_id=teacher_tg_id,
              text="Катя Долкирева 2а, 2б, 4")
    payloads = cell_payloads(recorder)
    assert payloads, "the table drew no cell buttons"

    before = table_of(text_dispatcher)["rows"][0]["cells"][0]["checked"]
    feed_callback(text_dispatcher, bot=bot_instance, from_id=teacher_tg_id, data=payloads[0])
    after = table_of(text_dispatcher)["rows"][0]["cells"][0]["checked"]

    assert after is not before
    assert events_of(marking) == [], "a tap on the table reached the journal"


def test_a_tap_after_the_draft_is_gone_is_refused_rather_than_guessed(
    text_dispatcher, bot_instance, recorder, teacher_tg_id
):
    """A stale table's tap must not land on whatever draft is in the slot now.

    The bot restarts, the storage is empty, and the teacher's screen still shows yesterday's
    table with its row indexes.  Positions name rows of the table they were drawn for and
    of no other, so the only safe answer is to refuse.
    """
    feed_callback(text_dispatcher, bot=bot_instance, from_id=teacher_tg_id, data="tc:0:0")
    assert any("устарел" in alert for alert in recorder.alerts()), recorder.alerts()


def test_kto_eto_is_answered_by_a_tap_and_a_forged_id_is_not(
    text_dispatcher, bot_instance, recorder, teacher_tg_id, catalogue
):
    """The row the parser would not guess is resolved by the teacher, and only by them.

    A payload is a string a client sends, so «this row means child 23» is a CLAIM. It is
    checked against the alternatives this server computed when it drew the table, which is
    the difference between trusting the answer and trusting the question.
    """
    feed_text(text_dispatcher, bot=bot_instance, from_id=teacher_tg_id,
              text="Пафнутий Чебышёв 3, 5")
    stored = table_of(text_dispatcher)
    assert stored["rows"][0]["student_id"] is None

    feed_callback(text_dispatcher, bot=bot_instance, from_id=teacher_tg_id, data="tp:0:23")
    assert table_of(text_dispatcher)["rows"][0]["student_id"] is None, (
        "an id this row never offered was accepted from the payload"
    )
    assert any("устарел" in alert for alert in recorder.alerts())

    offered = stored["rows"][0]["alternatives"]
    if not offered:
        pytest.skip("this stranger produced no alternatives; nothing to tap")
    feed_callback(text_dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data="tp:0:%d" % offered[0], update_id=3)
    assert table_of(text_dispatcher)["rows"][0]["student_id"] == offered[0]


# =============================================================================
#  «ЗАПИСАТЬ» -- the one place anything is stored
# =============================================================================

def test_what_the_teacher_typed_arrives_already_ticked(
    text_dispatcher, bot_instance, recorder, teacher_tg_id
):
    """A cell the teacher WROTE starts ticked, and the tap is how they take it back.

    The other way round -- an empty table the teacher fills in by tapping ten times -- would
    make the typed line worth nothing: they would have typed the numbers and then entered
    them again with their thumb.  What the parser found is a proposal, and the confirmation
    is a chance to CORRECT it, not to repeat it.
    """
    feed_text(text_dispatcher, bot=bot_instance, from_id=teacher_tg_id,
              text="Катя Долкирева 2а, 2б, 4")

    cells = table_of(text_dispatcher)["rows"][0]["cells"]
    assert [cell["checked"] for cell in cells] == [True, True, True], cells


def test_zapisat_writes_the_ticked_cells_and_only_those(
    text_dispatcher, bot_instance, recorder, teacher_tg_id, marking
):
    """Three typed, one taken back by a tap -- two written, and the third one is not.

    The tap has to survive all the way into the journal, otherwise the correction is
    theatre: the teacher watches a tick disappear and the mark lands anyway.
    """
    feed_text(text_dispatcher, bot=bot_instance, from_id=teacher_tg_id,
              text="Катя Долкирева 2а, 2б, 4")
    taken_back = cell_payloads(recorder)[-1]
    feed_callback(text_dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data=taken_back, update_id=50)

    expected = [
        (row["student_id"], cell["problem_id"])
        for row in table_of(text_dispatcher)["rows"]
        for cell in row["cells"]
        if cell["checked"] and cell["problem_id"] is not None
    ]
    assert len(expected) == 2, expected

    feed_callback(text_dispatcher, bot=bot_instance, from_id=teacher_tg_id, data="ty:1",
                  update_id=60)

    written = {(event.student_id, event.problem_id) for event in events_of(marking)}
    assert written == set(expected)
    assert all(event.source == tekst.SOURCE for event in events_of(marking))
    assert all(event.note == tekst.NOTE for event in events_of(marking)), (
        "the provenance of a typed mark is lost; today it is the ONLY place the channel "
        "is recorded, because the schema's source vocabulary does not know «текст» yet"
    )


def test_zapisat_writes_everything_the_teacher_left_ticked(
    text_dispatcher, bot_instance, recorder, teacher_tg_id, marking
):
    feed_text(text_dispatcher, bot=bot_instance, from_id=teacher_tg_id,
              text="Катя Долкирева 2а, 2б, 4")
    expected = [
        (row["student_id"], cell["problem_id"])
        for row in table_of(text_dispatcher)["rows"]
        for cell in row["cells"]
        if cell["problem_id"] is not None
    ]
    assert expected, "nothing resolved; this test would pass vacuously"

    feed_callback(text_dispatcher, bot=bot_instance, from_id=teacher_tg_id, data="ty:1")

    written = {(event.student_id, event.problem_id) for event in events_of(marking)}
    assert written == set(expected)
    assert all(event.source == tekst.SOURCE for event in events_of(marking))
    assert all(event.note == tekst.NOTE for event in events_of(marking)), (
        "the provenance of a typed mark is lost; today it is the ONLY place the channel "
        "is recorded, because the schema's source vocabulary does not know «текст» yet"
    )


def test_the_same_message_confirmed_twice_does_not_double_the_marks(
    text_dispatcher, bot_instance, recorder, teacher_tg_id, marking
):
    """Idempotency, stated the way a teacher would hit it: the network stalls, they resend.

    The key is the digest of the TYPED TEXT plus the cell, so the second pass produces the
    same keys and the journal answers out of itself.  This is the one property that cannot
    be checked by reading the code: it is a fact about two runs.
    """
    for update_id in (1, 100):
        feed_text(text_dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  text="Катя Долкирева 2а, 2б, 4", update_id=update_id)
        feed_callback(text_dispatcher, bot=bot_instance, from_id=teacher_tg_id, data="ty:1",
                      update_id=update_id + 10)

    events = events_of(marking)
    assert len(events) == len({(e.student_id, e.problem_id) for e in events}), (
        "the second confirmation wrote a second event for a cell that already had one"
    )


def test_zapisat_sends_the_procherk_to_attendance_and_never_to_the_marks(
    text_dispatcher, bot_instance, recorder, teacher_tg_id, marking,
    screen_sessions, lesson_today,
):
    """The rule of §1.4, checked where it is decidable: in the two books, after the button.

    The явка must be in P6's attendance and the mark journal must be untouched -- writing
    «пришёл и не сдал» as a mark would destroy the very distinction it exists to make.
    """
    feed_text(text_dispatcher, bot=bot_instance, from_id=teacher_tg_id, text="Влад Быков —")
    feed_callback(text_dispatcher, bot=bot_instance, from_id=teacher_tg_id, data="ty:1")

    views = screen_sessions.attendance_for(lesson_today.id)
    assert 11 in views and views[11].present_no_marks is True
    assert events_of(marking) == [], "a прочерк reached the mark journal"
    assert "Явок отмечено: 1" in "\n".join(recorder.texts())


def test_a_procherk_that_cannot_be_written_is_said_out_loud_rather_than_dropped(
    text_dispatcher, bot_instance, recorder, teacher_tg_id
):
    """No lesson today -- the teacher typed a fact the bot did not keep, and must be told.

    A silent drop is the worst available outcome: the teacher believes the явка is in, and
    the child reads as never having come.  The receipt says which half landed.
    """
    feed_text(text_dispatcher, bot=bot_instance, from_id=teacher_tg_id, text="Влад Быков —")
    feed_callback(text_dispatcher, bot=bot_instance, from_id=teacher_tg_id, data="ty:1")

    shown = "\n".join(recorder.texts())
    assert "явки не записаны" in shown
    assert "занятие не заведено" in shown


def test_otmena_writes_nothing_and_says_so_without_claiming_a_rollback(
    text_dispatcher, bot_instance, recorder, teacher_tg_id, marking
):
    feed_text(text_dispatcher, bot=bot_instance, from_id=teacher_tg_id,
              text="Катя Долкирева 2а, 2б, 4")
    feed_callback(text_dispatcher, bot=bot_instance, from_id=teacher_tg_id, data="tn:1")

    assert events_of(marking) == []
    assert table_of(text_dispatcher) is None
    assert "ничего не записано" in "\n".join(recorder.texts()).lower()


# =============================================================================
#  WHAT THIS SCREEN REFUSES TO ANSWER
# =============================================================================

@pytest.mark.parametrize(
    "message",
    [
        "спасибо",
        "а когда следующее занятие?",
        "Петров",
        "ок",
        "Долгирева заболела, будет на следующей неделе",
    ],
)
def test_an_ordinary_sentence_is_not_answered_with_a_confirmation_table(
    text_dispatcher, bot_instance, recorder, teacher_tg_id, message
):
    """The refusal that keeps the bot usable for anything other than this screen.

    Each of these is something a teacher types into the same box, and none of them is a
    record of a lesson.  A table drawn over «спасибо» is not a cosmetic annoyance: it is
    the bot answering a sentence with a form, every time, forever.
    """
    feed_text(text_dispatcher, bot=bot_instance, from_id=teacher_tg_id, text=message)
    assert recorder.records == [], "«%s» was answered by this screen" % message


def test_a_command_is_left_to_the_router_that_owns_it(
    text_dispatcher, bot_instance, recorder, teacher_tg_id
):
    """`/start` starts with a slash, and every command belongs to somebody else."""
    feed_text(text_dispatcher, bot=bot_instance, from_id=teacher_tg_id, text="/start")
    assert recorder.records == []


def test_an_open_dialogue_keeps_the_teachers_typing(
    text_dispatcher, bot_instance, recorder, teacher_tg_id
):
    """While an FSM dialogue is open, the typing belongs to THAT dialogue.

    Registration takes a surname, P14 takes an answer about attendance, P19 takes a new
    name -- and «Быков» typed into any of them is a valid answer that happens to look like
    a record.  Those handlers stand above this router and would win on order alone; this is
    the belt beside that brace, so that a dialogue added LATER is safe without anybody
    remembering to reorder.
    """
    from aiogram.fsm.storage.base import StorageKey

    import asyncio

    key = StorageKey(bot_id=0, chat_id=teacher_tg_id, user_id=teacher_tg_id)
    asyncio.get_event_loop().run_until_complete(
        text_dispatcher.storage.set_state(key, "SomeDialogue:waiting")
    )

    feed_text(text_dispatcher, bot=bot_instance, from_id=teacher_tg_id, text="Влад Быков —")
    assert recorder.records == [], "an open dialogue's answer was eaten by this screen"


def test_looks_like_a_record_agrees_with_what_the_screen_actually_does():
    """The filter and the parser must not drift: whatever the filter admits, the parser
    must produce a block for, and whatever it refuses must produce none worth showing."""
    for line, _, _, _ in OWNER_LINES:
        assert tekst.looks_like_a_record(line), line
    assert tekst.looks_like_a_record(OWNER_MESSAGE)
    for sentence in ("спасибо", "", "   ", "а когда следующее занятие?"):
        assert not tekst.looks_like_a_record(sentence), sentence


# =============================================================================
#  ONE TABLE, ONE WRITE PATH -- reuse rather than rebuild
# =============================================================================

def test_what_would_be_written_is_p7s_function_and_not_a_second_copy():
    """One rule, one home: «a row with no student writes nothing, however many of its
    cells are ticked».  It holds on the photo screen, the voice screen and this one, and
    three implementations of it is one implementation and two accidents."""
    from bot.routers import photo, text_input

    assert text_input.checked_cells is photo.checked_cells


def test_the_draft_this_screen_stores_is_the_shape_the_other_screens_store(
    catalogue, students
):
    """``checked_cells`` reads ``checked`` and ``shown``; a draft spelled otherwise would
    make it silently return nothing, i.e. «Записать (0)» over a full table."""
    from bot.routers.text_input import draft_to_state

    stored = draft_to_state(
        tekst.build_draft("Катя Долкирева 2а", students=students, catalogue=catalogue)
    )
    assert set(stored) >= {"rows", "transcript"}
    for row in stored["rows"]:
        assert {"student_id", "verdict", "alternatives", "cells"} <= set(row)
        for cell in row["cells"]:
            assert {"label", "problem_id", "checked", "shown"} <= set(cell)


def test_the_prefixes_do_not_collide_with_any_other_screen_of_this_bot():
    """A collision would silently route this screen's taps into another's handler.

    Discovered by walking ``bot/`` rather than by listing the prefixes by hand: a list
    written today is a list that stops being true the first time somebody adds a screen,
    and the failure it would miss is invisible -- the tap simply reaches the wrong module
    and is answered «устарело».
    """
    from bot.routers import text_input

    mine, theirs = set(), set()
    package = importlib.import_module("bot")
    for info in pkgutil.walk_packages(package.__path__, prefix="bot."):
        module = importlib.import_module(info.name)
        for value in vars(module).values():
            if not (isinstance(value, type) and issubclass(value, CallbackData)):
                continue
            prefix = getattr(value, "__prefix__", None)
            if prefix is None:
                continue
            (mine if value.__module__ == text_input.__name__ else theirs).add(prefix)

    assert mine == {"tc", "tp", "ty", "tn"}, mine
    assert mine & theirs == set(), mine & theirs


def test_no_payload_this_screen_draws_carries_a_childs_name(
    text_dispatcher, bot_instance, recorder, teacher_tg_id, catalogue
):
    """A surname in a payload is a surname leaving the server, and the payload cap is 64
    bytes -- a limit a Cyrillic surname reaches at eleven letters."""
    feed_text(text_dispatcher, bot=bot_instance, from_id=teacher_tg_id, text=OWNER_MESSAGE)

    surnames = [student.surname.lower() for student in catalogue.students()]
    checked = 0
    for keyboard in recorder.keyboards():
        for row in keyboard:
            for button in row:
                payload = button.get("callback_data")
                if payload is None:
                    continue
                checked += 1
                assert len(payload.encode("utf-8")) <= 64, payload
                assert not any(surname in payload.lower() for surname in surnames), payload
    assert checked > 0, "no keyboard was drawn"


def test_the_source_this_screen_writes_is_one_the_schema_accepts():
    """A source outside ``config.MARK_SOURCES`` is refused by a CHECK constraint at the
    database -- i.e. at the moment a real teacher confirms a real record.

    ⚠ «текст» is the CORRECT value and the schema does not know it yet: both
    ``migrations/001_init.sql`` and ``config.MARK_SOURCES`` are outside this position's
    zone.  The module falls back to a value the constraint accepts and keeps the
    provenance in ``note``; the day the value is added, this test keeps passing and the
    fallback disappears by itself.  Named in ``## ВОПРОСЫ``.
    """
    assert tekst.SOURCE in config.MARK_SOURCES
