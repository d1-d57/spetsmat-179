"""The two independent channels, and the disagreement that is the only source of doubt.

The sweep over the whole roster is the test that matters here and it prints its coverage:
fifty-six children, every case form of every surname, resolved back to the child who was
said.  A threshold tuned against five names is a threshold tuned against nothing.
"""

from __future__ import annotations

import json

import pytest

from core.services.golos import (
    AMBIGUITY_MARGIN,
    FUZZY_THRESHOLD,
    Verdict,
    build_draft,
    case_forms,
    load_schema_extractor,
    match_surname,
    normalise_label,
    parse_model_rows,
    resolve_labels,
    score_against_roster,
    strip_code_fence,
)


# ------------------------------------------------- the sweep over the whole roster

def test_every_surname_of_the_roster_resolves_in_every_case_it_declines_into(
    roster, capsys
):
    """Fifty-six children x every case form, back to the child who was said.

    Zero resolutions against a non-empty roster is RED, not green.  The negative verdict
    carries its coverage in itself: «errors 0, resolved N of N», never «no problems
    found».
    """
    asked = resolved = errors = 0
    failures = []

    for student in roster:
        for form in case_forms(student.surname):
            asked += 1
            match = match_surname(form, roster)
            if match.student_id == student.id:
                resolved += 1
            else:
                errors += 1
                failures.append(
                    "%r (case form of %s) -> %s, %s"
                    % (form, student.surname, match.student_id, match.reason)
                )

    with capsys.disabled():
        print(
            "\n[голос] фамилий %d · падежных форм разрешено %d из %d · ошибок %d"
            % (len(roster), resolved, asked, errors)
        )

    assert len(roster) == 56, "the seed carries 56 children, this run saw %d" % len(roster)
    assert resolved > 0, "the roster is not empty and nothing resolved"
    assert errors == 0, "\n".join(failures)


def test_a_surname_that_is_not_on_the_roster_is_unknown_and_offers_buttons(roster):
    """«Петров» is the задание's example line and is NOT a child of this conduit.

    The right answer is «I do not know, here are the three closest» — never the nearest
    surname pre-ticked, which is a mark on the wrong child's row.
    """
    match = match_surname("Петров", roster)

    assert match.student_id is None
    assert match.verdict is Verdict.UNKNOWN
    assert 1 <= len(match.alternatives) <= 3


def test_two_children_who_sound_alike_are_both_offered_rather_than_one_guessed(roster):
    """A lead inside the margin is a guess, and the rule is «never make it guess»."""
    match = match_surname("Сидоров", roster)

    assert match.verdict is Verdict.UNKNOWN
    assert str(int(AMBIGUITY_MARGIN)) in match.reason
    assert len(match.alternatives) > 1


def test_a_transcription_slip_of_one_letter_still_finds_the_child(roster):
    """This is what the threshold is FOR: a recogniser hears «кудишен» for Кудишин."""
    match = match_surname("кудишен", roster)

    assert match.verdict is Verdict.CERTAIN
    assert match.score >= FUZZY_THRESHOLD
    assert next(s.surname for s in roster if s.id == match.student_id) == "Кудишин"


def test_the_diaeresis_is_not_a_condition_of_being_found(roster):
    """``Фёдоров`` is in the roster and no recogniser is reliable about ``ё``."""
    for said in ("Федоров", "Фёдоров", "Фёдорову", "Федорову"):
        match = match_surname(said, roster)
        assert next(s.surname for s in roster if s.id == match.student_id) == "Фёдоров", said


def test_a_full_name_still_names_one_child(roster):
    """A teacher who says «Кахиани Дмитрий» has named one child, not a phrase."""
    match = match_surname("кахиани дмитрий", roster)
    assert next(s.surname for s in roster if s.id == match.student_id) == "Кахиани"


# --------------------------------------------------- the ratio that is NOT used

def test_containment_does_not_score_a_perfect_match(roster):
    """``token_set_ratio`` returns 100 on containment, and a perfect score is exactly
    what stops the alternatives from being offered.  ``ratio`` is what this uses, and the
    proof is that a contained name does NOT come back perfect."""
    scored = {candidate.surname: candidate.score for candidate in score_against_roster("лим", roster)}

    assert scored["Лим"] == 100.0
    assert scored["Лупулешин"] < 100.0
    assert scored["Могилевский"] < 100.0


def test_the_source_does_not_contain_the_containment_ratio_even_in_a_comment():
    """The готовности criterion is a bare ``grep -c`` over the source and must print 0.

    So the check here is the same bare grep, not a cleverer one that would pass while the
    criterion failed: a mention inside a docstring costs exactly as much as a call.
    """
    from pathlib import Path

    forbidden = "token_" + "set_ratio"
    source = Path(__file__).resolve().parents[2] / "core" / "services" / "golos.py"

    assert forbidden not in source.read_text(encoding="utf-8")


# ---------------------------------------------- channel one, when it is there at all

def test_the_schema_call_is_absent_on_this_branch_and_says_so_rather_than_being_forked():
    """P7 owns ``core/services/raspoznavanie.py`` and it is not on this branch.

    A forked copy of the schema call is two homes for one truth and they diverge in
    silence, so the second channel is simply absent and the reason is a sentence.
    """
    extractor, reason = load_schema_extractor()

    assert extractor is None
    assert "core.services.raspoznavanie" in reason


def test_a_valid_answer_inside_a_markdown_fence_is_read_rather_than_rejected():
    """Measured on this project on 02.09: a valid ``{"rows": []}`` came back fenced and
    the naive parser rejected it, which reads downstream as «the model failed»."""
    fenced = '```json\n{"rows": [{"raw_text": "петров", "student_id": 7}]}\n```'

    assert json.loads(strip_code_fence(fenced))["rows"][0]["student_id"] == 7
    assert parse_model_rows(fenced) == [
        {"raw_text": "петров", "student_id": 7, "alternatives": [], "problem_ids": []}
    ]


@pytest.mark.parametrize(
    "answer",
    [
        '{"rows": []}',
        '```\n{"rows": []}\n```',
        '```json\n{"rows": []}\n```',
        '  ```JSON\n{"rows": []}\n```  ',
    ],
)
def test_the_fence_is_optional_and_its_language_tag_is_irrelevant(answer):
    assert parse_model_rows(answer) == []


def test_a_numeric_confidence_is_not_carried_forward_even_when_volunteered():
    """It collapses to 0,9/1,0 and stays high while accuracy falls.  Nothing reads one,
    so nothing may quietly start to."""
    rows = parse_model_rows('{"rows": [{"raw_text": "x", "student_id": 1, "confidence": 0.99}]}')

    assert "confidence" not in rows[0]


# ------------------------------------------------------- the disagreement rule

def test_two_channels_that_disagree_make_the_row_doubtful_and_offer_both(roster):
    """This is the whole reason there are two channels."""
    lim = next(student for student in roster if student.surname == "Лим")
    other = next(student for student in roster if student.surname == "Егоров")

    draft = build_draft(
        "Лим три",
        students=roster,
        problems=[],
        model_rows=[{"raw_text": "лим", "student_id": other.id, "alternatives": [], "problem_ids": []}],
        channels="both",
    )

    row = draft.rows[0]
    assert row.verdict is Verdict.DOUBTFUL
    assert row.student_id == lim.id, "the inspectable channel keeps the row"
    assert other.id in row.alternatives and lim.id in row.alternatives
    assert "disagree" in row.reason


def test_two_channels_that_agree_say_so_and_leave_the_row_certain(roster):
    lim = next(student for student in roster if student.surname == "Лим")

    draft = build_draft(
        "Лим три",
        students=roster,
        problems=[],
        model_rows=[{"raw_text": "лим", "student_id": lim.id, "alternatives": [], "problem_ids": []}],
    )

    assert draft.rows[0].verdict is Verdict.CERTAIN
    assert "agree" in draft.rows[0].reason


def test_with_no_schema_call_the_draft_says_it_ran_on_one_channel(roster):
    """One channel must never be read as two channels that agreed."""
    draft = build_draft("Лим три", students=roster, problems=[])

    assert "one channel" in draft.channels or "only" in draft.channels


# ---------------------------------------------------------------- labels to problems

def test_a_spoken_label_finds_the_decorated_problem_the_sheet_prints(last_sheet_problems):
    """«семь бэ» names `7б°` when that is what the sheet carries: the degree sign marks an
    obligatory problem and is not pronounceable."""
    printed = {normalise_label(problem.label): problem.label for problem in last_sheet_problems}
    spoken = next(iter(sorted(printed)))

    cells = resolve_labels([spoken], last_sheet_problems)

    assert cells[0].problem_id is not None
    assert cells[0].printed_label == printed[spoken]
    assert cells[0].ticked is True


def test_a_label_that_matches_nothing_is_shown_unticked_rather_than_dropped(
    last_sheet_problems,
):
    """Dropping it silently would lose a problem the teacher believes they dictated."""
    cells = resolve_labels(["999я"], last_sheet_problems)

    assert len(cells) == 1
    assert cells[0].problem_id is None
    assert cells[0].ticked is False
    assert cells[0].is_writable is False


def test_the_whole_current_sheet_is_dictatable(last_sheet_problems, capsys):
    """Every label of the sheet in view, said as the sheet prints it minus its
    decorations, resolves back to its own problem."""
    asked = resolved = 0
    for problem in last_sheet_problems:
        spoken = normalise_label(problem.label)
        if not spoken:
            continue
        asked += 1
        cells = resolve_labels([spoken], last_sheet_problems)
        if cells[0].problem_id == problem.id:
            resolved += 1

    with capsys.disabled():
        print("\n[голос] задач текущего листка разрешено %d из %d" % (resolved, asked))

    assert asked > 0, "the current sheet has no problems"
    assert resolved == asked


# ------------------------------------------------------------- the draft as a whole

def test_a_draft_carries_the_digest_that_will_key_every_mark_it_writes(roster):
    draft = build_draft("Лим три", students=roster, problems=[], audio_sha256="abc123")
    assert draft.audio_sha256 == "abc123"


def test_an_unresolved_row_writes_nothing_even_with_every_cell_resolved(
    roster, last_sheet_problems
):
    """«Never make it guess» has to hold at the write, not only on the screen."""
    label = normalise_label(last_sheet_problems[0].label)
    draft = build_draft(
        "Сидоров %s" % label, students=roster, problems=last_sheet_problems
    )

    assert draft.rows[0].verdict is Verdict.UNKNOWN
    assert draft.rows[0].is_resolved is False
    assert draft.writable_cells == 0
