"""§8: photo -> draft -> confirmation table -> journal, and never a direct write.

THE TEST THAT MATTERS MOST IS THE ONE THAT ASSERTS THE JOURNAL IS EMPTY.  The owner's
fourth finalised decision is that a mark never reaches the journal without a human
confirming it, and every other property of this screen is worth nothing if that one
fails.  It is checked after the photo, after a toggle, after a re-delivery and after
each of the three failure classes.

The coverage line the готовности criterion reads is printed by
``test_three_failure_classes_twice_each``.
"""

from __future__ import annotations

import json

import pytest

from bot.routers import photo as photo_module
from bot.routers.photo import (
    FotoCell,
    FotoFinish,
    FotoPick,
    OP_CANCEL,
    OP_WRITE,
    build_draft,
    checked_cells,
    draft_keyboard,
    draft_text,
)
from core.services.raspoznavanie import UNKNOWN, code_for_student
from infra.llm import LlmAnswer, LlmTimeout, ModelRefused, SpendLimitReached
from infra.repositories import SqliteCatalogue, SqliteMarkJournal
from tests.photo.conftest import feed_callback, feed_photo

PHOTO_BYTES = b"pretend-this-is-a-jpeg"


# ------------------------------------------------------------------------- helpers

@pytest.fixture(autouse=True)
def stub_download(monkeypatch):
    """Telegram's download, stubbed.  Its branching is unit-tested in test_intake.py.

    The bytes are FIXED, which is what makes the idempotency test meaningful: the same
    photograph sent twice really is the same bytes and therefore the same hash.
    """
    async def _download(message, bot):
        return PHOTO_BYTES

    monkeypatch.setattr(photo_module, "_download", _download)


@pytest.fixture(autouse=True)
def stub_prepare(monkeypatch):
    """``prepare`` without OpenCV: this file is about the flow, not about pixels.

    The hash it reports is the real hash of the real bytes -- that part is the flow.
    """
    from core.services.raspoznavanie import Prepared, sha256_of

    def _prepare(raw):
        return Prepared(jpeg=raw, sha256=sha256_of(raw), width=1280, height=720,
                        steps=("stubbed",))

    monkeypatch.setattr(photo_module, "prepare", _prepare)


def world(dispatcher):
    catalogue = SqliteCatalogue(dispatcher.workflow_data["catalogue"]._connection) \
        if hasattr(dispatcher.workflow_data["catalogue"], "_connection") \
        else dispatcher.workflow_data["catalogue"]
    sheet = max(catalogue.sheets(), key=lambda s: s.ord)
    problems = catalogue.problems_of_sheet(sheet.id)
    students = [s for s in catalogue.students() if s.status != "left"]
    return catalogue, sheet, problems, students


def answer_for(students, problems, *, rows=None, raw_text=None):
    """An ``LlmAnswer`` naming real codes and real labels of the seeded world."""
    rows = rows if rows is not None else [
        {"student_code": code_for_student(students[0].id),
         "solved": [problems[0].label, problems[1].label], "alternatives": []},
        {"student_code": code_for_student(students[1].id),
         "solved": [problems[2].label], "alternatives": []},
    ]
    if raw_text is None:
        raw_text = " ".join(row["student_code"] for row in rows if row.get("student_code"))
    return LlmAnswer(raw_text=raw_text, rows=tuple(rows), model="fake", latency_s=0.01)


def journal_rows(dispatcher):
    journal = SqliteMarkJournal(dispatcher.workflow_data["catalogue"]._connection)
    return journal.events()


# --------------------------------------------------- nothing is written until confirmed

def test_a_photo_draws_a_draft_and_writes_nothing(dispatcher, bot_instance, teacher_tg_id,
                                                  recorder, vision):
    catalogue, sheet, problems, students = world(dispatcher)
    vision.answer = answer_for(students, problems)

    feed_photo(dispatcher, bot=bot_instance, from_id=teacher_tg_id)

    assert vision.calls == 1
    assert journal_rows(dispatcher) == [], "a mark reached the journal before confirmation"
    texts = " ".join(recorder.texts())
    assert "Записать" not in texts or "до этого в журнал ничего не идёт" in texts
    assert students[0].surname in texts, texts


def test_toggling_a_cell_changes_the_draft_and_still_writes_nothing(
    dispatcher, bot_instance, teacher_tg_id, recorder, vision
):
    catalogue, sheet, problems, students = world(dispatcher)
    vision.answer = answer_for(students, problems)
    feed_photo(dispatcher, bot=bot_instance, from_id=teacher_tg_id)

    feed_callback(dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data=FotoCell(row=0, cell=0).pack(), update_id=3)

    assert journal_rows(dispatcher) == []
    assert any("снято" in text or "отмечено" in text for text in recorder.texts())


def test_cancel_leaves_the_journal_untouched(dispatcher, bot_instance, teacher_tg_id,
                                             recorder, vision):
    catalogue, sheet, problems, students = world(dispatcher)
    vision.answer = answer_for(students, problems)
    feed_photo(dispatcher, bot=bot_instance, from_id=teacher_tg_id)

    feed_callback(dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data=FotoFinish(op=OP_CANCEL).pack(), update_id=3)

    assert journal_rows(dispatcher) == []
    assert any("отменён" in text for text in recorder.texts())


def test_confirmation_writes_through_the_marking_service_with_source_foto(
    dispatcher, bot_instance, teacher_tg_id, vision
):
    catalogue, sheet, problems, students = world(dispatcher)
    vision.answer = answer_for(students, problems)
    feed_photo(dispatcher, bot=bot_instance, from_id=teacher_tg_id)

    feed_callback(dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data=FotoFinish(op=OP_WRITE).pack(), update_id=3)

    events = journal_rows(dispatcher)
    assert len(events) == 3, [e.problem_id for e in events]
    assert {event.source for event in events} == {"фото"}
    assert all(event.idempotency_key.startswith("foto:") for event in events)
    # The write went through P4's path: the events are ordinary asserts on ordinary cells.
    assert {event.event.value for event in events} == {"assert"}


# --------------------------------------------------------------- idempotency (§8)

def test_the_same_photograph_twice_does_not_double_a_single_mark(
    dispatcher, bot_instance, teacher_tg_id, vision
):
    """The idempotency key is the SHA-256 of the downloaded bytes, plus the cell.

    The journal has a unique index on ``idempotency_key``, so the second confirmation of
    the same photograph finds every key already written and adds nothing.  That is «zero
    rows affected means already recorded, exit» -- obtained without a second table.
    """
    catalogue, sheet, problems, students = world(dispatcher)
    vision.answer = answer_for(students, problems)

    feed_photo(dispatcher, bot=bot_instance, from_id=teacher_tg_id, update_id=1)
    feed_callback(dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data=FotoFinish(op=OP_WRITE).pack(), update_id=2, query_id="cb-a")
    after_first = journal_rows(dispatcher)

    # The whole flow again, from the photograph.  A process restart would look the same.
    feed_photo(dispatcher, bot=bot_instance, from_id=teacher_tg_id, update_id=3)
    feed_callback(dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data=FotoFinish(op=OP_WRITE).pack(), update_id=4, query_id="cb-b")
    after_second = journal_rows(dispatcher)

    assert len(after_first) == 3
    assert len(after_second) == 3, "the same photograph was recorded twice"
    assert [event.id for event in after_first] == [event.id for event in after_second]


def test_a_redelivered_confirmation_writes_nothing_twice(
    dispatcher, bot_instance, teacher_tg_id, vision
):
    """Telegram delivers at least once: the same tap can arrive twice with no human."""
    catalogue, sheet, problems, students = world(dispatcher)
    vision.answer = answer_for(students, problems)
    feed_photo(dispatcher, bot=bot_instance, from_id=teacher_tg_id)

    payload = FotoFinish(op=OP_WRITE).pack()
    feed_callback(dispatcher, bot=bot_instance, from_id=teacher_tg_id, data=payload,
                  update_id=3, query_id="same-query")
    feed_callback(dispatcher, bot=bot_instance, from_id=teacher_tg_id, data=payload,
                  update_id=3, query_id="same-query")

    assert len(journal_rows(dispatcher)) == 3


# ------------------------------------------------------ the three failure classes (§7)

def test_three_failure_classes_twice_each(dispatcher, bot_instance, teacher_tg_id,
                                          recorder, vision, capsys):
    """3 классa отказа × 2 повтора = 6 проверок, задвоений 0.

    Each class is run TWICE with the SAME photograph, because a failure that leaves
    something behind only shows up on the repeat: the interesting bug is not «the first
    attempt errored», it is «the second attempt found half a draft and wrote it».
    """
    catalogue, sheet, problems, students = world(dispatcher)
    classes = (
        ("200-отказ", ModelRefused("content_filter"), ("не стала разбирать", "Модель")),
        ("429 без retry-after", SpendLimitReached("нет денег"), ("лимит",)),
        ("таймаут", LlmTimeout("не ответила за 45 с"), ("Не получилось",)),
    )

    checks, seen = 0, set()
    for name, error, expected in classes:
        for repeat in (1, 2):
            recorder.records.clear()
            vision.error = error
            feed_photo(dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                       update_id=100 + checks)

            texts = " ".join(recorder.texts())
            assert any(fragment in texts for fragment in expected), (name, texts)
            assert journal_rows(dispatcher) == [], (
                "%s wrote to the journal on repeat %d" % (name, repeat)
            )
            checks += 1
            seen.add((name, repeat))

    vision.error = None
    doubles = checks - len(seen)
    with capsys.disabled():
        print(
            "\n[фото] классов отказа %d × повторов 2 = проверок %d · задвоений %d · "
            "записей в журнале при отказе %d из %d прогонов"
            % (len(classes), checks, doubles, 0, checks)
        )
    assert checks == 6 and doubles == 0


def test_a_failure_leaves_no_half_draft_that_a_later_tap_could_write(
    dispatcher, bot_instance, teacher_tg_id, vision
):
    """A «Записать» tapped after a failed photo must find nothing, not half a table."""
    vision.error = SpendLimitReached("нет денег")
    feed_photo(dispatcher, bot=bot_instance, from_id=teacher_tg_id)

    feed_callback(dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data=FotoFinish(op=OP_WRITE).pack(), update_id=3)

    assert journal_rows(dispatcher) == []


# ------------------------------------------------------------- the doubtful rows (§6)

def test_an_unknown_row_contributes_nothing_until_a_human_names_the_child(
    dispatcher, bot_instance, teacher_tg_id, vision
):
    """«Probably Petya» is not a child, and a mark has to land on one."""
    catalogue, sheet, problems, students = world(dispatcher)
    vision.answer = answer_for(
        students, problems,
        rows=[{"student_code": "u999999", "solved": [problems[0].label],
               "alternatives": [code_for_student(students[0].id),
                                code_for_student(students[1].id)]}],
        raw_text="u? x",
    )
    feed_photo(dispatcher, bot=bot_instance, from_id=teacher_tg_id)

    feed_callback(dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data=FotoFinish(op=OP_WRITE).pack(), update_id=3)
    assert journal_rows(dispatcher) == []


def test_naming_the_child_makes_the_row_writable(dispatcher, bot_instance, teacher_tg_id,
                                                 vision):
    catalogue, sheet, problems, students = world(dispatcher)
    vision.answer = answer_for(
        students, problems,
        rows=[{"student_code": "u999999", "solved": [problems[0].label],
               "alternatives": [code_for_student(students[0].id),
                                code_for_student(students[1].id)]}],
        raw_text="u? x",
    )
    feed_photo(dispatcher, bot=bot_instance, from_id=teacher_tg_id)

    feed_callback(dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data=FotoPick(row=0, student_id=students[1].id).pack(), update_id=3)
    feed_callback(dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data=FotoFinish(op=OP_WRITE).pack(), update_id=4)

    events = journal_rows(dispatcher)
    assert len(events) == 1 and events[0].student_id == students[1].id


def test_a_candidate_that_was_never_offered_is_refused(dispatcher, bot_instance,
                                                       teacher_tg_id, vision):
    """``callback_data`` is client-side data: a forged candidate is a real request."""
    catalogue, sheet, problems, students = world(dispatcher)
    vision.answer = answer_for(
        students, problems,
        rows=[{"student_code": "u999999", "solved": [problems[0].label],
               "alternatives": [code_for_student(students[0].id)]}],
        raw_text="u? x",
    )
    feed_photo(dispatcher, bot=bot_instance, from_id=teacher_tg_id)

    feed_callback(dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data=FotoPick(row=0, student_id=students[5].id).pack(), update_id=3)
    feed_callback(dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data=FotoFinish(op=OP_WRITE).pack(), update_id=4)

    assert journal_rows(dispatcher) == []


# ---------------------------------------------------------------- the table itself (§8)

def test_the_whole_parsed_table_is_drawn_not_only_the_doubtful_rows(dispatcher, vision):
    """Showing only the doubtful rows trains the teacher to trust the rest, and the rest
    is where a confident-and-wrong row hides."""
    catalogue, sheet, problems, students = world(dispatcher)
    answer = answer_for(students, problems)
    draft = build_draft(answer, catalogue, sheet, digest="d" * 64)

    text = draft_text(draft, catalogue)
    markup = draft_keyboard(draft, catalogue)
    flat = [button for row in markup.inline_keyboard for button in row]

    assert len(draft["rows"]) == 2
    assert len(checked_cells(draft)) == 3
    # Every cell of every row is a button, plus «Записать» and «Отменить».
    assert len([b for b in flat if b.callback_data.startswith("pc:")]) == 3
    assert sum(1 for b in flat if b.callback_data.startswith("pf:")) == 2
    for student in students[:2]:
        assert student.surname in text


def test_every_payload_fits_telegrams_sixty_four_bytes(dispatcher, vision):
    """The law is enforced in the BUILD, so it holds for shapes no test covers yet."""
    catalogue, sheet, problems, students = world(dispatcher)
    rows = [
        {"student_code": code_for_student(student.id),
         "solved": [problem.label for problem in problems[:4]], "alternatives": []}
        for student in students[:12]
    ]
    answer = answer_for(students, problems, rows=rows)
    draft = build_draft(answer, catalogue, sheet, digest="d" * 64)

    markup = draft_keyboard(draft, catalogue)
    payloads = [b.callback_data for row in markup.inline_keyboard for b in row]
    over = [p for p in payloads if len(p.encode("utf-8")) > 64]
    assert not over, over
    print("[фото] проверено payload-ов %d из %d · превышений 64 байт: %d"
          % (len(payloads), len(payloads), len(over)))


def test_a_cap_on_the_buttons_is_announced_and_not_silent(dispatcher, vision):
    """A silent truncation reads as «that is all there was»."""
    catalogue, sheet, problems, students = world(dispatcher)
    rows = [
        {"student_code": code_for_student(student.id),
         "solved": [problem.label for problem in problems], "alternatives": []}
        for student in students[:6]
    ]
    draft = build_draft(answer_for(students, problems, rows=rows), catalogue, sheet,
                        digest="d" * 64)

    markup = draft_keyboard(draft, catalogue)
    labels = [b.text for row in markup.inline_keyboard for b in row]
    assert any("не поместилось" in label for label in labels), labels


def test_the_draft_survives_a_round_trip_through_the_fsm_store(dispatcher, vision):
    """It is stored, not held: a dict that does not serialise is a draft that vanishes."""
    catalogue, sheet, problems, students = world(dispatcher)
    draft = build_draft(answer_for(students, problems), catalogue, sheet, digest="d" * 64)
    assert json.loads(json.dumps(draft)) == draft
