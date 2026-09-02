"""«СНЯТО» — прочерк is the THIRD state of a cell, and the schema was where it was lost.

The form prints its own legend under every grid, and the owner wrote it:

    Сдал — крестик в клетке. Снято — прочерк. Пусто — не сдавал.

The journal has known those three states for a year -- 735 ``retract`` events last season
-- and ``CellState`` names them.  The vision schema named two.  With only ``solved`` on
offer and a prompt asking for a row with any ПОМЕТКА, a dash IS a пометка and there was
nowhere else to put it, so «снято» came back as a hand-in.

🔴 THAT IS WORSE THAN AN EMPTY ANSWER, AND THAT IS WHY THIS FILE EXISTS.  An empty answer
is a refusal the teacher SEES; a plausible wrong value is one they confirm without
looking.  Measured against a live model on 2026-09-02: u5 carried a dash on 1а°,
``raw_text`` read «u5  -» correctly, and ``solved`` came back ``[1а°]``.  The model was
right about the paper.  The schema had no word for what it saw.

WHAT GOES RED IF THE FIX IS REVERTED — measured on 2026-09-02 by actually reverting each
of the three, not estimated: take ``retracted`` out of ``build_schema`` and 3 of these
fail, out of ``parse_answer`` and 7 fail, out of ``DraftRow`` and 3 fail.  Nothing here
can pass by accident, because nothing here asserts that a field is absent.
"""

from __future__ import annotations

import json

import pytest

from core.services.raspoznavanie import rows_from_answer
from infra.llm import CELL_LEGEND, LlmAnswer, build_prompt, build_schema, parse_answer

#: The vocabularies of one real sheet, small enough to read in a failure message.
CODES = ["u1", "u3", "u5", "u7"]
LABELS = ["1а°", "1б°", "1в°", "2", "3°"]


def _row_properties(schema):
    return schema["properties"]["rows"]["items"]["properties"]


def _envelope(row_objects, raw_text="u5  -"):
    """A provider envelope carrying exactly these rows.  No network, no fixture file."""
    return {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "content": json.dumps(
                        {"raw_text": raw_text, "rows": row_objects}, ensure_ascii=False
                    )
                },
            }
        ]
    }


# ===================================================================== the schema

def test_the_schema_gives_a_dash_somewhere_to_go():
    """The whole defect in one assertion: without this field the dash lands in ``solved``.

    A model cannot report a state the schema cannot express.  It will report the closest
    thing it can, and the closest thing to «снято» inside a schema that knows only
    «сдал» is «сдал».
    """
    properties = _row_properties(build_schema(CODES, LABELS))

    assert "retracted" in properties, (
        "the schema names only %s — a dash has nowhere to go but ``solved``"
        % sorted(properties)
    )


def test_retracted_is_the_same_closed_list_as_solved():
    """Same vocabulary, different verb.

    A dash sits on a TASK, exactly as a tick does, so the enum is the same forty-five
    labels.  A second, looser list would let the model answer «снято по задаче 99».
    """
    properties = _row_properties(build_schema(CODES, LABELS))

    assert properties["retracted"]["items"]["enum"] == LABELS
    assert properties["retracted"] == properties["solved"], (
        "solved and retracted must be the same closed list: %r vs %r"
        % (properties["solved"], properties["retracted"])
    )


def test_the_two_states_are_two_fields_and_not_one_with_a_flag():
    """They are separate arrays, and they are both arrays of labels.

    Written down so that «tidying» them into one list of ``{label, state}`` objects goes
    red rather than quietly re-creating the collapse this file is about.
    """
    properties = _row_properties(build_schema(CODES, LABELS))

    for field in ("solved", "retracted"):
        assert properties[field]["type"] == "array", field
        assert properties[field]["items"]["type"] == "string", field
    assert properties["solved"] is not properties["retracted"]


# ===================================================================== the prompt

def test_the_prompt_states_all_three_states_verbatim_from_the_legend():
    """The paper and the instruction must say the same sentence, not two paraphrases.

    ``tools/blank.py`` prints the legend under the grid; ``CELL_LEGEND`` is quoted into
    the prompt.  A paraphrase would be a second source of truth for a rule the form
    already states, and the two would drift the first time either was edited.
    """
    prompt = build_prompt(CODES, LABELS)

    assert CELL_LEGEND in prompt, prompt
    assert "retracted" in prompt, "the prompt never names the field the dash goes into"
    assert "прочерк" in prompt.lower()


def test_the_prompt_forbids_putting_a_dash_into_solved_in_so_many_words():
    """The instruction that closes the defect, not merely the field that permits it.

    A schema is a request.  The prompt has to say, out loud, that a dash is not a
    hand-in -- because the previous prompt said the opposite («любая пометка») and the
    model obeyed it.
    """
    prompt = build_prompt(CODES, LABELS)

    assert "не сдача" in prompt.lower() or "не сдачa" in prompt.lower(), prompt
    assert "в solved не кладут" in prompt.lower() or "solved не кладут" in prompt.lower(), (
        prompt
    )
    # And the old wording, which is the wording that produced the defect, is gone.
    assert "список номеров задач с пометкой" not in prompt


def test_the_legend_in_the_prompt_is_the_legend_printed_on_the_paper():
    """🔴 THE LINK BETWEEN TWO FILES, CARRIED BY A TEST BECAUSE IT CANNOT BE AN IMPORT.

    ``tools/blank.py`` is outside this position's zone, so ``CELL_LEGEND`` cannot be
    imported into it.  What CAN be done is to make the two copies compared on every run:
    change the sentence on the paper without changing the prompt, and this goes red.
    """
    import config
    from tools.blank import ROWS_PER_FORM, draw_form, labels_of_sheet, roster_from_seed
    import tempfile
    import pathlib

    roster = roster_from_seed(config.SEED_DIR)[:ROWS_PER_FORM]
    labels = labels_of_sheet(config.SEED_DIR, "1")
    assert roster and labels, "seed/ is the oracle of this test and it is empty"

    with tempfile.TemporaryDirectory() as folder:
        _, drawn = draw_form(
            [code for code, _ in roster], labels, "1", "302",
            pathlib.Path(folder) / "blank.png",
        )

    assert CELL_LEGEND in drawn, (
        "the prompt quotes %r, which is not printed on the form: %r"
        % (CELL_LEGEND, [line for line in drawn if "Сдал" in line or "Снято" in line])
    )


# ===================================================================== the parse

def test_a_dash_parses_into_retracted_and_never_into_solved():
    """The measured failure, replayed through the parser with the field in place."""
    payload = _envelope(
        [{"student_code": "u5", "solved": ["1а°"], "retracted": ["1в°"]}]
    )

    answer = parse_answer(payload, LABELS, model="m", latency_s=0.1)
    row = answer.rows[0]

    assert row["solved"] == ["1а°"]
    assert row["retracted"] == ["1в°"]
    assert "1в°" not in row["solved"], "«снято» arrived as a hand-in — the whole defect"


def test_a_row_that_is_only_dashes_still_comes_back():
    """A student who had everything taken back is a row, not a silence.

    ``solved`` empty and ``retracted`` full is a perfectly ordinary answer, and a parser
    that treated «no ticks» as «no row» would drop the very rows this заход is about.
    """
    payload = _envelope([{"student_code": "u7", "solved": [], "retracted": ["2", "3°"]}])

    answer = parse_answer(payload, LABELS, model="m", latency_s=0.1)

    assert len(answer.rows) == 1
    assert answer.rows[0]["solved"] == []
    assert answer.rows[0]["retracted"] == ["2", "3°"]


def test_a_retracted_label_outside_the_closed_list_is_reported_and_not_dropped():
    """A schema is a request, not a guarantee — and that holds for the new field too.

    A label that is not on this sheet is evidence about WHICH sheet the paper is, so it
    is reported exactly as a stray ``solved`` label is.  Dropping it silently is how a
    photograph of last week's form looks like a correct read of this week's.
    """
    payload = _envelope(
        [{"student_code": "u1", "solved": ["2"], "retracted": ["99", "3°"]}]
    )

    answer = parse_answer(payload, LABELS, model="m", latency_s=0.1)

    assert answer.rows[0]["retracted"] == ["3°"]
    assert "99" in answer.rejected_labels, answer.rejected_labels
    assert "99" in answer.unknown_labels, answer.unknown_labels


def test_an_answer_without_the_field_still_parses():
    """Older stored answers and every existing fixture must survive the schema growing.

    ``retracted`` is read with a default, not required: a draft parked in an FSM store
    before this change must not become a traceback in front of a teacher.
    """
    payload = _envelope([{"student_code": "u1", "solved": ["2"]}])

    answer = parse_answer(payload, LABELS, model="m", latency_s=0.1)

    assert answer.rows[0]["retracted"] == []
    assert answer.rows[0]["solved"] == ["2"]


# ================================================================== the draft row

def test_the_draft_row_carries_the_dash_separately_from_the_tick():
    """The last step inside this position's zone: ``rows_from_answer``.

    The tuples stay two.  Anything that adds them together here re-creates the defect one
    layer further down, where it is harder to see.
    """
    answer = LlmAnswer(
        raw_text="u5  x1а°  -1в°",
        rows=({"student_code": "u5", "solved": ["1а°"], "retracted": ["1в°"]},),
        model="m",
        latency_s=0.1,
    )

    row = rows_from_answer(answer, known_student_ids={5})[0]

    assert row.student_id == 5
    assert row.solved == ("1а°",)
    assert row.retracted == ("1в°",)
    assert "1в°" not in row.solved


def test_an_unresolved_row_keeps_its_dashes_too():
    """A row whose code did not resolve still carries the fact, only not its subject.

    Same rule the text channel settled on for a прочерк after an unrecognised name: the
    FACT survives, and it is the student that is missing.  Dropping the dashes here would
    hide the state from the screen that is supposed to let the teacher fix the row.
    """
    answer = LlmAnswer(
        raw_text="??  -2",
        rows=({"student_code": "u99", "solved": [], "retracted": ["2"]},),
        model="m",
        latency_s=0.1,
    )

    row = rows_from_answer(answer, known_student_ids={5})[0]

    assert row.student_id is None
    assert row.retracted == ("2",)


def test_a_draft_row_built_the_old_way_still_works():
    """``retracted`` defaults to empty, so no existing caller has to be edited at once.

    This is what lets the fix land inside the zone: the router builds its dict from the
    fields it knows and is not broken by a field it does not.
    """
    answer = LlmAnswer(
        raw_text="u1  x2",
        rows=({"student_code": "u1", "solved": ["2"]},),
        model="m",
        latency_s=0.1,
    )

    row = rows_from_answer(answer, known_student_ids={1})[0]

    assert row.retracted == ()
    assert row.solved == ("2",)


@pytest.mark.parametrize("label", ["1а°", "3°", "2"])
def test_no_label_can_be_in_both_lists_after_a_parse_of_the_same_cell(label):
    """A cell is in ONE state.  If a model answers both, the two lists disagree loudly.

    Nothing here silently resolves the contradiction: the parser keeps what the model
    said, and hands both lists on, which is the correct behaviour for a paper that really
    does carry a tick struck through by a dash -- the contradiction is the teacher's to
    settle, and a parser that picked a side would settle it invisibly.

    🔴 AND THE TEACHER DOES NOT SEE IT YET, WHICH IS WHY THIS IS SAID HERE RATHER THAN
    IMPLIED.  An earlier version of this docstring claimed the screen «shows a row that
    is visibly odd»; it does not.  ``build_draft`` (``bot/routers/photo.py``) still reads
    only ``row.solved``, so a cell in both lists reaches the screen as a plain hand-in.
    Carrying the field this far is the half that fits in this заход's zone; the last leg
    is written out address by address in the ``## ВОПРОСЫ`` of ``kod_R1-foto.md``.  Found
    by the §3 verifier, which read the claim and went looking for the screen.
    """
    payload = _envelope(
        [{"student_code": "u1", "solved": [label], "retracted": [label]}]
    )

    answer = parse_answer(payload, LABELS, model="m", latency_s=0.1)

    assert answer.rows[0]["solved"] == [label]
    assert answer.rows[0]["retracted"] == [label]
