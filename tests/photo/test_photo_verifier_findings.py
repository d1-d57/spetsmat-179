"""The defects the §3 verifier found, each with a test that goes red without its fix.

A finding that is fixed and not pinned is a finding that comes back.  Every test here
fails on the code as it stood before the verifier ran, and the docstring says on which
line, so that a future edit that reintroduces the defect is told what it just undid.

THE FILENAME IS NOT `test_verifier_findings.py`, AND THAT IS NOT A PREFERENCE.  There are
no ``__init__.py`` files under ``tests/``, so pytest imports each test module by its BARE
BASENAME; ``tests/test_verifier_findings.py`` already exists, and a second file of that
name aborts COLLECTION of the whole suite -- `make check` goes red on an import mismatch
that mentions neither test.  ``tests/photo`` alone stayed green, which is exactly how this
gets shipped.
"""

from __future__ import annotations

import io

import pytest

from bot.routers.photo import (
    FotoFinish,
    FotoNote,
    MAX_CELL_BUTTONS,
    OP_WRITE,
    build_draft,
    checked_cells,
    draft_keyboard,
    draft_text,
)
from core.models import CellState
from core.services.raspoznavanie import IntakeRefused, prepare
from infra.llm import _parse_retry_after, build_schema
from infra.repositories import SqliteMarkJournal
from tests.photo.conftest import feed_callback, feed_photo
from tests.photo.test_flow import answer_for, journal_rows, world

pytest.importorskip("cv2")


# ------------------------------------------------------------------------ finding 1

def test_the_warp_never_enlarges_on_either_axis(capsys):
    """The clamp used to compare only ``max(width, height)`` against ``max(frame.shape)``.

    A target shorter on the long side and TALLER on the short one sailed through: the
    verifier drove 1568x1045 -- the shape a real phone photo has after the downscale -- to
    1532x1213, 1,134 times the pixels, and found 1,218 times over random quads.  Enlarging
    is the 34-point operation, and ``INTER_AREA`` degrades to nearest-neighbour when it
    is asked to go up.
    """
    from core.services.raspoznavanie import _crop_to_sheet
    import numpy

    numpy.random.seed(20260902)
    worst = 0.0
    checked = 0
    for _ in range(200):
        height, width = 700, 900
        frame = numpy.full((height, width, 3), 30, dtype=numpy.uint8)
        # A bright quadrilateral with visibly unequal opposite sides: the skewed branch.
        quad = numpy.array([
            [numpy.random.randint(10, 80), numpy.random.randint(10, 80)],
            [width - numpy.random.randint(10, 80), numpy.random.randint(10, 200)],
            [width - numpy.random.randint(10, 200), height - numpy.random.randint(10, 80)],
            [numpy.random.randint(10, 200), height - numpy.random.randint(10, 200)],
        ], dtype=numpy.int32)
        import cv2
        cv2.fillPoly(frame, [quad], (250, 250, 248))

        out, steps = _crop_to_sheet(frame)
        checked += 1
        assert out.shape[0] <= height, (steps, out.shape)
        assert out.shape[1] <= width, (steps, out.shape)
        worst = max(worst, (out.shape[0] * out.shape[1]) / float(height * width))

    with capsys.disabled():
        print("\n[правка-1] квадрилатералов проверено %d из %d · худший рост площади "
              "%.3fx (предел 1.000x)" % (checked, checked, worst))
    assert worst <= 1.0


def test_the_whole_pipeline_never_returns_more_pixels_than_it_was_given():
    """End to end, through ``prepare``: the property, not the branch."""
    from PIL import Image, ImageDraw

    for width, height in ((900, 700), (700, 900), (1568, 1045), (400, 400)):
        image = Image.new("RGB", (width, height), (30, 30, 35))
        draw = ImageDraw.Draw(image)
        draw.polygon(
            [(40, 30), (width - 25, 90), (width - 90, height - 35), (60, height - 100)],
            fill=(250, 250, 248),
        )
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", quality=95)

        prepared = prepare(buffer.getvalue())
        assert prepared.width <= width and prepared.height <= height, (
            (width, height), (prepared.width, prepared.height), prepared.steps
        )


# ------------------------------------------------------------------------ finding 2

def test_a_truncated_upload_is_refused_in_a_sentence_and_not_as_a_bare_oserror():
    """``Image.open`` parses the HEADER and returns; the pixels are read later.

    A 60%-truncated JPEG -- the most ordinary failure a phone on school wifi produces --
    opened cleanly and then threw ``OSError: image file is truncated`` out of
    ``exif_transpose``, past every ``except IntakeRefused`` in the router.
    """
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (1200, 800), (200, 200, 200)).save(buffer, "JPEG", quality=95)
    whole = buffer.getvalue()

    for cut in (0.6, 0.4, 0.9):
        with pytest.raises(IntakeRefused):
            prepare(whole[: int(len(whole) * cut)])

    # And the header-level corruption that already worked keeps working.
    with pytest.raises(IntakeRefused):
        prepare(b"this is not an image")


# ------------------------------------------------------------------------ finding 3

def test_a_photograph_of_another_sheet_is_refused_and_not_written_onto_this_one(
    dispatcher, bot_instance, teacher_tg_id, recorder, vision
):
    """Adjacent sheets share between two and eleven labels.

    The verifier photographed листок 12 while 13 was current: nine marks landed on листок
    13's problem ids and thirty-five labels were dropped without a word.  The form prints
    «Листок N» and nothing was reading it back.
    """
    catalogue, sheet, problems, students = world(dispatcher)
    other = [s for s in catalogue.sheets() if s.number != sheet.number][-1]
    vision.answer = answer_for(students, problems, sheet_number=other.number)

    feed_photo(dispatcher, bot=bot_instance, from_id=teacher_tg_id)
    feed_callback(dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data=FotoFinish(op=OP_WRITE).pack(), update_id=3)

    assert journal_rows(dispatcher) == []
    texts = " ".join(recorder.texts())
    assert other.number in texts and sheet.number in texts, texts


def test_the_sheet_the_paper_names_is_asked_for_as_a_closed_list(dispatcher, bot_instance,
                                                                 teacher_tg_id, vision):
    catalogue, sheet, problems, students = world(dispatcher)
    vision.answer = answer_for(students, problems, sheet_number=sheet.number)

    feed_photo(dispatcher, bot=bot_instance, from_id=teacher_tg_id)

    assert vision.sheets_offered == [s.number for s in catalogue.sheets()]
    # A third field, and a small one: neither big enum grows, so §5's ceiling is untouched.
    schema = build_schema(["u1"], ["1"], vision.sheets_offered)
    assert schema["required"] == ["raw_text", "sheet_number", "rows"]
    assert len(schema["properties"]["sheet_number"]["enum"]) == 18
    assert list(schema["properties"])[0] == "raw_text"


def test_a_label_that_is_not_on_this_sheet_is_reported_and_not_dropped(dispatcher, vision):
    catalogue, sheet, problems, students = world(dispatcher)
    answer = answer_for(
        students, problems,
        rows=[{"student_code": "u%d" % students[0].id,
               "solved": [problems[0].label, "нет-такой-задачи"], "alternatives": []}],
    )
    draft = build_draft(answer, catalogue, sheet, digest="d" * 64)

    assert draft["unknown_labels"] == ["нет-такой-задачи"]
    assert "возможно, это фото другого листка" in draft_text(draft, catalogue)
    assert len(checked_cells(draft)) == 1


# ------------------------------------------------------------------------ finding 4

def test_a_cell_that_did_not_fit_on_the_screen_can_never_become_a_mark(
    dispatcher, vision, capsys
):
    """«Записать 94» over a keyboard showing 80 wrote fourteen marks nobody could see.

    The cap now lives in ``build_draft``: a cell past it is ``shown: False``, unticked, and
    invisible to ``checked_cells``.  Nothing reaches the journal that a human did not look at.
    """
    catalogue, sheet, problems, students = world(dispatcher)
    rows = [
        {"student_code": "u%d" % student.id,
         "solved": [problem.label for problem in problems], "alternatives": []}
        for student in students[:8]
    ]
    draft = build_draft(answer_for(students, problems, rows=rows), catalogue, sheet,
                        digest="d" * 64)

    offered = sum(len(row["cells"]) for row in draft["rows"])
    assert offered > MAX_CELL_BUTTONS, offered
    assert draft["hidden"] == offered - MAX_CELL_BUTTONS
    assert len(checked_cells(draft)) == MAX_CELL_BUTTONS
    assert all(not cell["checked"] for row in draft["rows"]
               for cell in row["cells"] if not cell["shown"])

    text = draft_text(draft, catalogue)
    assert "НЕ будут записаны" in text and str(draft["hidden"]) in text
    with capsys.disabled():
        print("\n[правка-4] клеток предложено %d · показано %d · записываемых %d · "
              "скрыто %d" % (offered, MAX_CELL_BUTTONS, len(checked_cells(draft)),
                             draft["hidden"]))


def test_the_overflow_line_is_inert_and_no_longer_cancels_the_draft(dispatcher, vision):
    """It carried ``FotoFinish(op=0)``: a tap on what reads as a caption threw the draft
    away.  It is now its own payload with its own handler that changes nothing."""
    catalogue, sheet, problems, students = world(dispatcher)
    rows = [
        {"student_code": "u%d" % student.id,
         "solved": [problem.label for problem in problems], "alternatives": []}
        for student in students[:8]
    ]
    draft = build_draft(answer_for(students, problems, rows=rows), catalogue, sheet,
                        digest="d" * 64)

    buttons = [b for row in draft_keyboard(draft, catalogue).inline_keyboard for b in row]
    overflow = [b for b in buttons if "не поместилось" in b.text]
    assert len(overflow) == 1
    assert overflow[0].callback_data == FotoNote().pack()
    assert not overflow[0].callback_data.startswith("pf:")
    # Exactly one button in the whole keyboard writes.
    assert sum(1 for b in buttons if b.callback_data == FotoFinish(op=OP_WRITE).pack()) == 1


def test_the_overflow_button_explains_itself_and_leaves_the_draft_alone(
    dispatcher, bot_instance, teacher_tg_id, recorder, vision
):
    catalogue, sheet, problems, students = world(dispatcher)
    rows = [
        {"student_code": "u%d" % student.id,
         "solved": [problem.label for problem in problems], "alternatives": []}
        for student in students[:8]
    ]
    vision.answer = answer_for(students, problems, rows=rows)
    feed_photo(dispatcher, bot=bot_instance, from_id=teacher_tg_id)

    feed_callback(dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data=FotoNote().pack(), update_id=3)
    assert any("не поместились" in text for text in recorder.texts())

    # The draft survived the tap: confirming still writes what was on the screen.
    feed_callback(dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data=FotoFinish(op=OP_WRITE).pack(), update_id=4)
    assert len(journal_rows(dispatcher)) == MAX_CELL_BUTTONS


# ------------------------------------------------------------------------ finding 5

def test_an_http_date_retry_after_is_not_read_as_the_money_running_out():
    """Both forms of ``retry-after`` are legal, and only one of them was parsed.

    Reading the date as «no header» sent an ordinary rate limit down the spend-limit
    branch, and the teacher was told the money ran out over something that would have
    cleared in a minute.
    """
    assert _parse_retry_after("5") == 5.0
    assert _parse_retry_after(None) is None
    assert _parse_retry_after("nonsense") is None

    from datetime import datetime, timedelta, timezone
    from email.utils import format_datetime

    soon = datetime.now(timezone.utc) + timedelta(seconds=30)
    parsed = _parse_retry_after(format_datetime(soon))
    assert parsed is not None and 20 <= parsed <= 40, parsed

    # A date in the past is zero seconds, not a negative wait and not a spend limit.
    past = datetime.now(timezone.utc) - timedelta(seconds=60)
    assert _parse_retry_after(format_datetime(past)) == 0.0


def test_a_429_with_a_date_header_is_still_bounded():
    """It must not become an eternal retry on the way to being classified correctly."""
    import urllib.error
    from datetime import datetime, timedelta, timezone
    from email.utils import format_datetime

    from infra.llm import MAX_ATTEMPTS, LlmError, VisionModel

    calls = []
    header = {"retry-after": format_datetime(datetime.now(timezone.utc) + timedelta(seconds=2))}

    def post(body):
        calls.append(1)
        raise urllib.error.HTTPError("u", 429, "e", header, io.BytesIO(b"slow down"))

    with pytest.raises(LlmError):
        VisionModel(api_key="k", post=post, sleep=lambda _s: None).read_sheet(
            b"j", ["u1"], ["1"]
        )
    assert len(calls) <= MAX_ATTEMPTS == 3


# ------------------------------------------------------------------------ finding 6

def test_a_cell_struck_since_the_first_confirmation_is_not_reported_as_standing(
    dispatcher, bot_instance, teacher_tg_id, recorder, vision
):
    """``written=False`` does not mean «уже стоит».

    The key is spent by the first confirmation; if the cell has since been struck, the
    journal answers from the key and the cell stays EMPTY.  Calling that «уже было» tells
    the teacher a mark is standing when none is -- and this photograph can never put it
    back, because its key is used.
    """
    catalogue, sheet, problems, students = world(dispatcher)
    vision.answer = answer_for(students, problems)

    feed_photo(dispatcher, bot=bot_instance, from_id=teacher_tg_id, update_id=1)
    feed_callback(dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data=FotoFinish(op=OP_WRITE).pack(), update_id=2, query_id="q1")

    # The teacher strikes one of those marks out through P4's screen.
    marking = dispatcher.workflow_data["marking"]
    struck = checked_cells(
        build_draft(vision.answer, catalogue, sheet, digest="x")
    )[0]
    marking.set_state(struck[0], struck[1], CellState.EMPTY, source="кнопка")

    recorder.records.clear()
    feed_photo(dispatcher, bot=bot_instance, from_id=teacher_tg_id, update_id=3)
    feed_callback(dispatcher, bot=bot_instance, from_id=teacher_tg_id,
                  data=FotoFinish(op=OP_WRITE).pack(), update_id=4, query_id="q2")

    summary = " ".join(recorder.texts())
    assert "Снято раньше" in summary, summary
    assert "Уже стояло: 2" in summary, summary

    journal = SqliteMarkJournal(dispatcher.workflow_data["catalogue"]._connection)
    standing = journal.last_event(struck[0], struck[1])
    assert standing.event.value == "erratum", "the cell was silently refilled"
