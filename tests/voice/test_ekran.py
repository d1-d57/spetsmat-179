"""The screen: a voice note in, a table, taps, and one button that reaches the journal.

WHAT EVERY TEST HERE IS REALLY ABOUT.  «There is never a direct write» is the third thing
the interview finalised, and it is a property nobody can see by reading the router — it is
a property of the journal AFTER a dictation has been through the whole path.  So these
tests drive real updates through a real dispatcher over the real seed, and then look in
the journal.
"""

from __future__ import annotations

import hashlib

import pytest

from core.models import CellState
from core.services.golos import normalise_label
from tests.voice.conftest import feed_callback, feed_voice


def surname_of(catalogue, student_id):
    return catalogue.student(student_id).surname


@pytest.fixture
def a_child(catalogue):
    """A real child of the seeded roster, and their surname as the sheet spells it."""
    return next(student for student in catalogue.students() if student.surname == "Кахиани")


@pytest.fixture
def current_labels(catalogue):
    """The problems of the sheet the teacher is working on, as they would be dictated."""
    sheet = max(catalogue.sheets(), key=lambda sheet: sheet.ord)
    return [
        (problem, normalise_label(problem.label))
        for problem in catalogue.problems_of_sheet(sheet.id)
    ]


def dictate(dp, bot, tg_id, transcript_script, said, *, update_id=1):
    """Send one voice note whose scripted transcript is ``said``."""
    file_id = "audio-%d" % update_id
    transcript_script[file_id.encode("utf-8")] = said
    feed_voice(dp, bot=bot, from_id=tg_id, file_id=file_id, update_id=update_id)
    return file_id


# ------------------------------------------------------------------ the table appears

def test_a_voice_note_becomes_a_table_and_writes_nothing(
    voice_dispatcher, bot_instance, recorder, teacher_tg_id, transcript_script,
    a_child, current_labels, marking,
):
    """The whole point of the screen, in one test.

    A dictation the bot understood perfectly still touches nothing: the table appears, it
    says so in words, and the journal is empty until a human presses a button.
    """
    problem, label = current_labels[0]
    dictate(voice_dispatcher, bot_instance, teacher_tg_id, transcript_script,
            "Кахиани %s" % label)

    text = "\n".join(recorder.texts())
    assert "Кахиани" in text
    assert problem.label in text
    assert "не записано" in text

    journal = voice_dispatcher.workflow_data["marking"]._journal  # noqa: SLF001
    assert journal.events() == [], "a draft reached the journal without a confirmation"


def test_the_transcript_is_shown_so_a_wrong_parse_is_diagnosable_without_the_audio(
    voice_dispatcher, bot_instance, recorder, teacher_tg_id, transcript_script,
):
    dictate(voice_dispatcher, bot_instance, teacher_tg_id, transcript_script,
            "Кахиани три пять семь бэ")
    assert "Кахиани три пять семь бэ" in "\n".join(recorder.texts())


def test_a_recogniser_that_heard_nothing_says_so_instead_of_drawing_an_empty_table(
    voice_dispatcher, bot_instance, recorder, teacher_tg_id,
):
    """An empty table is indistinguishable from a dictation the teacher meant to be
    empty, and it would invite a confirmation of nothing."""
    feed_voice(voice_dispatcher, bot=bot_instance, from_id=teacher_tg_id,
               file_id="unscripted", update_id=1)

    text = "\n".join(recorder.texts())
    assert "Не разобрал запись" in text
    assert "кнопками" in text


def test_a_file_over_the_getfile_ceiling_is_refused_before_anything_is_downloaded(
    voice_dispatcher, bot_instance, recorder, teacher_tg_id, transcriber,
):
    feed_voice(voice_dispatcher, bot=bot_instance, from_id=teacher_tg_id,
               file_id="huge", update_id=1, file_size=21 * 1024 * 1024)

    assert "МБ" in "\n".join(recorder.texts())
    assert transcriber.calls == [], "the audio was fetched despite being over the limit"


# ---------------------------------------------------------------- the write path

def test_confirming_writes_through_the_marking_service_with_source_golos(
    voice_dispatcher, bot_instance, recorder, teacher_tg_id, transcript_script,
    a_child, current_labels,
):
    """The mark is written by P4's service, not by this screen, and it carries «голос».

    A source column that said «кнопка» for a dictated mark would make the three ways in
    indistinguishable a year later, which is the whole reason the column exists.
    """
    problem, label = current_labels[0]
    dictate(voice_dispatcher, bot_instance, teacher_tg_id, transcript_script,
            "Кахиани %s" % label)

    feed_callback(voice_dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data="vy:1", update_id=2)

    journal = voice_dispatcher.workflow_data["marking"]._journal  # noqa: SLF001
    events = journal.events()
    assert len(events) == 1, events
    assert events[0].student_id == a_child.id
    assert events[0].problem_id == problem.id
    assert events[0].source == "голос"
    assert events[0].event.value == "assert"


def test_the_idempotency_key_is_the_recording_plus_the_cell(
    voice_dispatcher, bot_instance, teacher_tg_id, transcript_script, a_child,
    current_labels,
):
    """SHA-256 of the downloaded bytes plus the confirmed-drafts table, exactly as photo."""
    problem, label = current_labels[0]
    file_id = dictate(voice_dispatcher, bot_instance, teacher_tg_id, transcript_script,
                      "Кахиани %s" % label)
    feed_callback(voice_dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data="vy:1", update_id=2)

    digest = hashlib.sha256(file_id.encode("utf-8")).hexdigest()
    journal = voice_dispatcher.workflow_data["marking"]._journal  # noqa: SLF001
    key = journal.events()[0].idempotency_key

    assert key.startswith("v:%s" % digest[:16])
    assert str(a_child.id) in key and str(problem.id) in key


def test_the_same_recording_sent_twice_writes_one_event(
    voice_dispatcher, bot_instance, teacher_tg_id, transcript_script, current_labels,
):
    """Telegram delivers at least once.  A redelivered voice note has the same bytes, so
    the same digest, so the same table and the same keys — and the journal answers the
    second confirmation out of itself."""
    _problem, label = current_labels[0]
    transcript_script[b"same-audio"] = "Кахиани %s" % label

    for update_id in (1, 3):
        feed_voice(voice_dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                   file_id="same-audio", update_id=update_id)
        feed_callback(voice_dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                      data="vy:1", update_id=update_id + 1,
                      query_id="cb-%d" % update_id)

    journal = voice_dispatcher.workflow_data["marking"]._journal  # noqa: SLF001
    assert len(journal.events()) == 1, journal.events()


def test_cancel_writes_nothing_and_says_that_nothing_was_written(
    voice_dispatcher, bot_instance, recorder, teacher_tg_id, transcript_script,
    current_labels,
):
    """«Отменено» over an unwritten draft reads as a rollback, and there was none."""
    _problem, label = current_labels[0]
    dictate(voice_dispatcher, bot_instance, teacher_tg_id, transcript_script,
            "Кахиани %s" % label)

    feed_callback(voice_dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data="vn:1", update_id=2)

    journal = voice_dispatcher.workflow_data["marking"]._journal  # noqa: SLF001
    assert journal.events() == []
    assert any("ничего не записано" in text.lower() for text in recorder.texts())


# ------------------------------------------------------------------ correcting by tap

def test_untapping_a_cell_keeps_it_out_of_the_journal(
    voice_dispatcher, bot_instance, teacher_tg_id, transcript_script, current_labels,
):
    """A tap toggles, and what is left unticked is what does not get written.  This is
    the only correction mechanism the screen has, and it has to bite."""
    (first, first_label), (second, second_label) = current_labels[0], current_labels[1]
    dictate(voice_dispatcher, bot_instance, teacher_tg_id, transcript_script,
            "Кахиани %s %s" % (first_label, second_label))

    feed_callback(voice_dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data="vc:0:0", update_id=2)
    feed_callback(voice_dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data="vy:1", update_id=3)

    journal = voice_dispatcher.workflow_data["marking"]._journal  # noqa: SLF001
    written = [event.problem_id for event in journal.events()]
    assert written == [second.id], written


def test_an_unresolved_row_offers_buttons_and_writes_nothing_until_one_is_tapped(
    voice_dispatcher, bot_instance, recorder, teacher_tg_id, transcript_script,
    current_labels, catalogue,
):
    """«Never make it guess», at the write and not only on the screen."""
    _problem, label = current_labels[0]
    dictate(voice_dispatcher, bot_instance, teacher_tg_id, transcript_script,
            "Сидоров %s" % label)

    assert "кто это?" in "\n".join(recorder.texts())

    feed_callback(voice_dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data="vy:1", update_id=2)
    journal = voice_dispatcher.workflow_data["marking"]._journal  # noqa: SLF001
    assert journal.events() == [], "an unresolved row reached the journal"


def test_tapping_an_offered_candidate_resolves_the_row_and_then_it_writes(
    voice_dispatcher, bot_instance, recorder, teacher_tg_id, transcript_script,
    current_labels, catalogue,
):
    _problem, label = current_labels[0]
    dictate(voice_dispatcher, bot_instance, teacher_tg_id, transcript_script,
            "Сидоров %s" % label)

    offered = [
        button["callback_data"]
        for keyboard in recorder.keyboards()
        for row in keyboard
        for button in row
        if button["callback_data"].startswith("vp:")
    ]
    assert offered, "an unresolved row offered no candidates"

    feed_callback(voice_dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data=offered[0], update_id=2)
    feed_callback(voice_dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data="vy:1", update_id=3)

    journal = voice_dispatcher.workflow_data["marking"]._journal  # noqa: SLF001
    assert len(journal.events()) == 1
    assert journal.events()[0].student_id == int(offered[0].split(":")[2])


def test_a_candidate_the_row_did_not_offer_is_refused(
    voice_dispatcher, bot_instance, recorder, teacher_tg_id, transcript_script,
    current_labels, catalogue,
):
    """``callback_data`` is client-side data, so a payload naming another child is a
    request the server really receives.  It is checked against the alternatives THIS row
    computed, which is a check against our own answer rather than the payload's claim."""
    _problem, label = current_labels[0]
    dictate(voice_dispatcher, bot_instance, teacher_tg_id, transcript_script,
            "Сидоров %s" % label)

    students = catalogue.students()
    outsider = max(student.id for student in students) + 1
    feed_callback(voice_dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data="vp:0:%d" % outsider, update_id=2)
    feed_callback(voice_dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data="vy:1", update_id=3)

    journal = voice_dispatcher.workflow_data["marking"]._journal  # noqa: SLF001
    assert journal.events() == []
    assert any("устарела" in alert for alert in recorder.alerts())


# ------------------------------------------------------------------- stale and absurd

def test_a_tap_with_no_draft_in_the_store_says_the_screen_is_stale(
    voice_dispatcher, bot_instance, recorder, teacher_tg_id,
):
    """A button from a table the bot has forgotten — restarted process, confirmed draft,
    a message scrolled up from last Thursday.  It must answer, or the spinner never stops."""
    feed_callback(voice_dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data="vc:0:0", update_id=2)
    assert any("устарела" in alert for alert in recorder.alerts())


@pytest.mark.parametrize("payload", ["vc:99:0", "vc:0:99", "vp:99:1"])
def test_an_index_outside_the_table_is_answered_rather_than_raising(
    voice_dispatcher, bot_instance, recorder, teacher_tg_id, transcript_script,
    current_labels, payload,
):
    """An index past the end used to be the shape that raised inside a handler, i.e. a
    spinner that turns until Telegram gives up."""
    _problem, label = current_labels[0]
    dictate(voice_dispatcher, bot_instance, teacher_tg_id, transcript_script,
            "Кахиани %s" % label)

    feed_callback(voice_dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data=payload, update_id=2)
    assert any("устарела" in alert for alert in recorder.alerts())


def test_a_heard_label_that_matches_no_problem_is_shown_and_cannot_be_ticked(
    voice_dispatcher, bot_instance, recorder, teacher_tg_id, transcript_script,
):
    """Losing it silently would lose a problem the teacher believes they dictated."""
    dictate(voice_dispatcher, bot_instance, teacher_tg_id, transcript_script,
            "Кахиани девяносто девять")

    # A cell is a BUTTON, so «shown» is checked where a cell is actually shown.
    labels = [
        button["text"]
        for keyboard in recorder.keyboards()
        for row in keyboard
        for button in row
    ]
    assert any(text.startswith("✗") and "99" in text for text in labels), labels

    feed_callback(voice_dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data="vc:0:0", update_id=2)
    assert any("такой задачи нет" in alert for alert in recorder.alerts())

    feed_callback(voice_dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data="vy:1", update_id=3)
    journal = voice_dispatcher.workflow_data["marking"]._journal  # noqa: SLF001
    assert journal.events() == []


# ---------------------------------------------------------------- the payload laws

def test_no_payload_of_this_screen_carries_a_surname_or_exceeds_the_byte_limit(
    voice_dispatcher, bot_instance, recorder, teacher_tg_id, transcript_script,
    current_labels, catalogue,
):
    """Telegram counts ``callback_data`` in BYTES, capped at 64, and a Cyrillic character
    costs two.  A surname in a payload is also a surname leaving the server."""
    _problem, label = current_labels[0]
    dictate(voice_dispatcher, bot_instance, teacher_tg_id, transcript_script,
            "Сидоров %s" % label)

    surnames = {student.surname.lower() for student in catalogue.students()}
    checked = 0
    for keyboard in recorder.keyboards():
        for row in keyboard:
            for button in row:
                payload = button["callback_data"]
                checked += 1
                assert len(payload.encode("utf-8")) <= 64, payload
                assert not any(surname in payload.lower() for surname in surnames), payload
    assert checked > 0, "no keyboard was drawn"


def test_the_prefixes_do_not_collide_with_any_other_screen_of_this_bot():
    """A collision would silently route one screen's taps into another's handler."""
    from bot import callbacks
    from bot.routers import voice

    theirs = {
        cls.__prefix__
        for cls in (callbacks.Mark, callbacks.OpenGrid, callbacks.Done,
                    callbacks.PickSheet, callbacks.Noop)
    }
    mine = {
        cls.__prefix__
        for cls in (voice.VoiceCell, voice.VoicePick, voice.VoiceConfirm, voice.VoiceCancel)
    }

    assert len(mine) == 4, mine
    assert theirs & mine == set(), theirs & mine


def test_the_source_this_screen_writes_is_one_the_schema_accepts():
    """A source outside ``config.MARK_SOURCES`` is refused by a CHECK constraint at the
    database, i.e. at the moment a real teacher confirms a real dictation."""
    import config
    from bot.routers.voice import SOURCE

    assert SOURCE in config.MARK_SOURCES


# ------------------------------------------------------- reuse rather than rebuild

def test_what_would_be_written_is_p7s_function_and_not_a_second_copy():
    """One rule, one home: «a row with no student writes nothing, however many of its
    cells are ticked».  It has to hold on the photo screen and on this one, and two
    implementations of it is one implementation and one accident."""
    from bot.routers import photo, voice

    assert voice._writable is photo.checked_cells  # noqa: SLF001


def test_the_draft_this_screen_stores_has_the_shape_p7s_table_reads(
    voice_dispatcher, bot_instance, teacher_tg_id, transcript_script, current_labels,
):
    """The reuse above is only legal because the two drafts are the same shape.  Asserted
    on a draft that really went through the handler, not on a hand-built dict."""
    from bot.routers.photo import checked_cells

    _problem, label = current_labels[0]
    dictate(voice_dispatcher, bot_instance, teacher_tg_id, transcript_script,
            "Кахиани %s" % label)

    loop = __import__("asyncio").get_event_loop()
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.storage.base import StorageKey

    key = StorageKey(bot_id=bot_instance.id, chat_id=teacher_tg_id, user_id=teacher_tg_id)
    context = FSMContext(storage=voice_dispatcher.storage, key=key)
    stored = loop.run_until_complete(context.get_data())["voice_draft"]

    assert stored["rows"][0]["cells"][0].keys() >= {"problem_id", "checked", "shown"}
    assert len(checked_cells(stored)) == 1


def test_the_matching_metric_reaches_this_screen_from_p7_and_not_from_a_local_table():
    """The screen must not acquire its own idea of how close two surnames are."""
    from core.services import golos, raspoznavanie

    assert golos.case_forms is raspoznavanie.case_forms
