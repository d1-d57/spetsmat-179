"""§6: the confidence the model reports does not exist, so this is the one that does.

The test this file is really about is ``test_containment_is_not_a_match``.  §6 forbids
``token_set_ratio`` for one concrete reason — it returns 100 on containment — and a
project that used it would separate no student from that student's own initial-bearing
neighbour while every score on the screen read «perfect».
"""

from __future__ import annotations

import csv

import pytest

import config
from core.services.raspoznavanie import (
    CONFIDENCE_THRESHOLD,
    UNKNOWN,
    case_forms,
    code_for_student,
    match_person,
    ratio,
    roster_forms,
    rows_from_answer,
    score_code_agreement,
)


class FakeStudent:
    def __init__(self, student_id, surname, name):
        self.id, self.surname, self.name = student_id, surname, name


class FakeAnswer:
    def __init__(self, raw_text, rows):
        self.raw_text, self.rows = raw_text, rows


def seed_students():
    students = []
    with (config.SEED_DIR / "students.csv").open(encoding="utf-8") as handle:
        for index, record in enumerate(csv.DictReader(handle)):
            if str(record.get("technical", "")).strip() in ("1", "true", "да"):
                continue
            students.append(FakeStudent(index + 1, record["surname"], record["name"]))
    return students


# ------------------------------------------------------------------- the metric (§6)

def test_containment_is_not_a_match():
    """🔴 The whole reason §6 names ``ratio`` and forbids ``token_set_ratio``.

    «Иванов И.» is CONTAINED in nothing and CONTAINS «Иванов»; ``token_set_ratio`` scores
    that 100 and a pipeline built on it can never separate two neighbours in a list.  The
    indel ratio scores it 80: similar, not identical, which is the truth.
    """
    score = ratio("Иванов И.", "Иванов")

    assert 70 < score < 100, score
    # 200 * LCS / (len + len) = 200 * 6 / (9 + 6) = 80 -- the definition, not an estimate.
    assert round(score, 1) == 80.0


def test_the_local_metric_agrees_with_rapidfuzz_where_rapidfuzz_exists():
    """The fallback is the SAME metric, not a near-enough substitute."""
    fuzz = pytest.importorskip("rapidfuzz").fuzz
    for left, right in (
        ("Иванов И.", "Иванов"), ("Петрова", "Петровой"), ("", "x"), ("абв", "абв"),
        ("Агаркова", "Аникина"),
    ):
        assert round(ratio(left, right), 6) == round(fuzz.ratio(left.lower(), right.lower()), 6)


def test_identical_and_disjoint_strings_sit_at_the_ends_of_the_scale():
    assert ratio("Петров", "Петров") == 100.0
    assert ratio("", "") == 100.0
    assert ratio("Петров", "") == 0.0


# ---------------------------------------------------------------- the case forms (§6)

def test_the_roster_expands_into_the_number_of_forms_the_brief_measured():
    """§6: 350-670 forms over the roster.  The number is asserted, not asserted about."""
    students = seed_students()
    forms = roster_forms(students)

    print("\n[уверенность] учеников %d · форм имени %d (ожидание §6: 350-670)"
          % (len(students), len(forms)))
    assert 350 <= len(forms) <= 670, "%d forms for %d students" % (len(forms), len(students))
    # Every student is reachable by at least their own nominative.
    reachable = {student_id for student_id in forms.values()}
    assert len(reachable) == len(students)


def test_oblique_cases_resolve_to_the_same_child():
    """«нет Петрова» and «Петров» are the same child; a nominative-only channel is blind
    to every oblique case, and the blindness is silent -- a tap per lesson, forever."""
    students = [FakeStudent(1, "Петров", "Василий"), FakeStudent(2, "Агаркова", "Ирина")]
    forms = roster_forms(students)

    for text, expected in (
        ("Петров", 1), ("Петрова", 1), ("Петрову", 1), ("Петровым", 1),
        ("Агаркова", 2), ("Агарковой", 2), ("Ирина", 2), ("Петров В.", 1),
    ):
        student_id, score = match_person(text, forms)
        assert student_id == expected, (text, student_id, score)
        assert score >= CONFIDENCE_THRESHOLD, (text, score)


def test_an_indeclinable_name_is_not_expanded_into_five_copies_of_itself():
    assert case_forms("Черных") == ("Черных",)
    assert case_forms("Живаго") == ("Живаго",)
    assert len(case_forms("Петров")) == 5


def test_a_stranger_does_not_resolve_to_anybody():
    forms = roster_forms([FakeStudent(1, "Петров", "Василий")])
    _, score = match_person("Хачатурян", forms)
    assert score < CONFIDENCE_THRESHOLD, score


# ----------------------------------------------- the two channels disagreeing (§6)

def test_the_transcription_is_a_second_channel_and_disagreement_is_the_doubt_signal():
    """``raw_text`` is produced BEFORE the structured answer — that is what putting it
    first in the schema buys — so the two are as close to independent as one call gives.
    """
    assert score_code_agreement("u17", "u17 x x u18") == 1.0
    assert score_code_agreement("u17", "") == 0.0
    assert score_code_agreement("u17", "здесь нет ни одного кода") == 0.0
    # A near miss scores high but not perfect: u17 against a transcribed u1.
    assert 0 < score_code_agreement("u17", "u1 x") < 1.0


def test_a_row_the_transcription_does_not_support_comes_back_doubtful():
    answer = FakeAnswer(
        raw_text="u3 x x",   # the transcription never mentions u17
        rows=[{"student_code": "u17", "solved": ["1", "2"], "alternatives": []}],
    )
    row, = rows_from_answer(answer, known_student_ids=[3, 17])

    assert row.student_id == 17
    assert row.state == "doubtful", (row.state, row.score)
    assert row.needs_a_human
    assert row.solved == ("1", "2")


def test_a_row_both_channels_agree_about_is_confident():
    answer = FakeAnswer(
        raw_text="u17 x . x",
        rows=[{"student_code": "u17", "solved": ["1"], "alternatives": []}],
    )
    row, = rows_from_answer(answer, known_student_ids=[17])

    assert row.state == "confident" and not row.needs_a_human
    assert row.score >= CONFIDENCE_THRESHOLD


def test_two_petyas_come_back_unknown_with_candidates_and_never_a_guess():
    """Never make a model choose between two similar rows: asked to, it will, at once.

    The row arrives with no student and a list of candidates, and the bot draws one
    button per candidate.
    """
    answer = FakeAnswer(
        raw_text="u4 x   u5 x",
        rows=[{"student_code": "u4", "solved": ["1"], "alternatives": ["u4", "u5"]}],
    )
    row, = rows_from_answer(answer, known_student_ids=[4, 5])

    assert row.state == UNKNOWN
    assert row.alternatives == (4, 5)
    assert row.needs_a_human


def test_a_code_outside_the_catalogue_cannot_become_a_mark():
    """The closed list makes this nearly unreachable — and «nearly» is why it is handled."""
    answer = FakeAnswer(
        raw_text="u999 x",
        rows=[{"student_code": "u999", "solved": ["1"], "alternatives": []}],
    )
    row, = rows_from_answer(answer, known_student_ids=[1, 2, 3])

    assert row.state == UNKNOWN and row.student_id is None


def test_the_code_the_form_prints_is_the_code_the_pipeline_reads():
    """One codec, two callers.  A drift here puts every mark on the wrong child."""
    answer = FakeAnswer(
        raw_text=" ".join(code_for_student(n) for n in (7, 8, 9)),
        rows=[{"student_code": code_for_student(8), "solved": [], "alternatives": []}],
    )
    row, = rows_from_answer(answer, known_student_ids=[7, 8, 9])
    assert row.student_id == 8 and row.state == "confident"
