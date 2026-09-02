"""Numeral normalisation, rule by rule, each on a line a teacher would actually say.

The §3 rules of the задание are the headings below and there is one test per rule.  Every
input is a dictation, not a synthetic token stream: the failure mode this whole module
exists to prevent is a recogniser writing down what it HEARD, and the only inputs that
exercise that are the words.
"""

from __future__ import annotations

import pytest

from core.services.golos import (
    LETTER_FORMS,
    NUMERAL_FORMS,
    TENS_FORMS,
    fold,
    normalise_label,
    parse_dictation,
)


def labels_of(line: str) -> list:
    """The problems of a one-student line, which is what every rule below is about."""
    rows = parse_dictation(line)
    assert len(rows) == 1, "expected one row out of %r, got %d" % (line, len(rows))
    return rows[0].labels


# ---------------------------------------------------- rule: numerals become digits

@pytest.mark.parametrize(
    "said, expected",
    [
        ("Агаркова три", ["3"]),
        ("Агаркова семнадцать", ["17"]),
        ("Агаркова девятнадцать", ["19"]),
        ("Агаркова двадцать четыре", ["24"]),
        ("Агаркова двадцать", ["20"]),
        ("Агаркова ноль", ["0"]),
    ],
)
def test_spelled_out_numerals_become_digits(said, expected):
    """«три» -> 3, «семнадцать» -> 17, and «двадцать четыре» is ONE problem, not two."""
    assert labels_of(said) == expected


def test_a_bare_ten_word_stays_itself_and_does_not_swallow_the_next_student():
    """«двадцать» alone is problem 20 — the sheet really has one — and the surname that
    follows it opens the next row instead of being eaten by the composition rule."""
    rows = parse_dictation("Агаркова двадцать Аникина три")
    assert [(row.surname_text, row.labels) for row in rows] == [
        ("агаркова", ["20"]),
        ("аникина", ["3"]),
    ]


# --------------------------------------------------------- rule: letter suffixes

@pytest.mark.parametrize(
    "said, expected",
    [
        ("Болотин семь бэ", ["7б"]),
        ("Болотин десять а", ["10а"]),
        ("Болотин шесть вэ", ["6в"]),
        ("Болотин тринадцать гэ", ["13г"]),
        ("Болотин пять дэ", ["5д"]),
        ("Болотин двенадцать е", ["12е"]),
        ("Болотин девять жэ", ["9ж"]),
        ("Болотин десять зэ", ["10з"]),
    ],
)
def test_letter_suffixes_are_where_dictation_actually_lives(said, expected):
    """`7б` is said «семь бэ».  Every letter of ``LETTER_FORMS`` on a real line."""
    assert labels_of(said) == expected


def test_the_conjunction_i_is_never_read_as_the_suffix_letter():
    """«семь и восемь» is TWO problems.

    This is the decision recorded in ``LETTER_FORMS``: `и` is not a suffix name, because
    the conjunction is what a teacher says between two problems and a suffix reading
    would silently merge them into one non-existent `7и`.
    """
    assert labels_of("Лупулешин семь и восемь") == ["7", "8"]


def test_the_particle_zhe_is_not_the_letter_zh_and_does_not_open_a_row():
    """«три же» is problem 3 — not `3ж`, and not a student called «же»."""
    rows = parse_dictation("Лим три же")
    assert [(row.surname_text, row.labels) for row in rows] == [("лим", ["3"])]


def test_a_letter_away_from_a_number_is_dropped_rather_than_attached():
    """«а» and «е» are ordinary words as well as letters.

    A suffix attaches to the number just said and to nothing else, so a stray «а» before
    any number cannot invent a label out of the previous student's last problem.
    """
    assert labels_of("Домра а три") == ["3"]


# ------------------------------------------------------- rule: ordinals and cases

@pytest.mark.parametrize(
    "said, expected",
    [
        ("Борисов третью и пятую", ["3", "5"]),
        ("Борисов три пять", ["3", "5"]),
        ("Борисов первую", ["1"]),
        ("Борисов девятую", ["9"]),
        ("Борисов четвёртую", ["4"]),
        ("Борисов четвертую", ["4"]),
        ("Борисов двадцать первую", ["21"]),
    ],
)
def test_ordinals_and_cases_mean_the_same_problem(said, expected):
    """«третью и пятую» is the same thing as «три пять» — the задание says so, and the
    only way that is true is if the vocabulary table says so."""
    assert labels_of(said) == expected


# ---------------------------------------------------------------- rule: ranges

def test_a_range_is_expanded_inclusively_on_both_ends():
    """«с третьей по шестую» -> 3, 4, 5, 6.  Supported, and the decision is recorded."""
    assert labels_of("Аникина с третьей по шестую") == ["3", "4", "5", "6"]


def test_a_range_whose_end_carries_a_letter_is_left_as_two_labels():
    """«с седьмой по седьмую вэ» has no defined enumeration — the sheet's letters are not
    a contiguous alphabet — so both ends reach the teacher to be completed by tapping."""
    assert labels_of("Аникина с седьмой по седьмую вэ") == ["7", "7в"]


def test_a_descending_range_is_left_alone_rather_than_silently_emptied():
    """Two numbers were said; an empty list would drop a problem without telling anyone."""
    assert labels_of("Аникина с шестой по третью") == ["6", "3"]


def test_a_range_opener_outside_a_range_is_simply_dropped():
    """«с» is unremarkable Russian and appears constantly away from a range."""
    assert labels_of("Аникина с третьей") == ["3"]


# ----------------------------------------------------- rule: negative-numbered work

def test_the_minus_problems_of_the_sheet_are_dictatable():
    """The seed carries `-1` … `-5`; they are said «минус один»."""
    assert labels_of("Бирюков минус один минус два") == ["-1", "-2"]


# ------------------------------------------------------- rule: the vocabulary is DATA

def test_every_form_written_in_the_tables_is_actually_reachable():
    """The tables are the vocabulary, and this is what makes that claim checkable.

    A form added to ``NUMERAL_FORMS`` and misspelled would otherwise sit there looking
    like coverage while matching nothing a teacher ever says.
    """
    checked = 0
    for value, forms in list(NUMERAL_FORMS.items()) + list(TENS_FORMS.items()):
        for form in forms:
            assert labels_of("Агаркова %s" % form) == [str(value)], form
            checked += 1
    for form, letter in LETTER_FORMS.items():
        assert labels_of("Агаркова три %s" % form) == ["3%s" % letter], form
        checked += 1
    assert checked >= 100, "the vocabulary shrank to %d forms" % checked


def test_the_tables_carry_no_form_that_means_two_different_numbers():
    """One spoken form must not mean two numbers.

    Written as a test rather than trusted, because the tables are meant to be extended by
    hand and a collision there is invisible: whichever entry the inversion visits last
    wins, silently, for every dictation from then on.

    A form listed TWICE for the SAME value is legal and deliberate — «четвёртая» and
    «четвертая» fold together, and both spellings stand in the table so that whoever
    greps it for either one finds it.
    """
    seen = {}
    for value, forms in list(NUMERAL_FORMS.items()) + list(TENS_FORMS.items()):
        for form in forms:
            previous = seen.get(fold(form))
            assert previous in (None, value), "%r means both %s and %s" % (
                form, previous, value,
            )
            seen[fold(form)] = value


# -------------------------------------------------------------- label comparison

@pytest.mark.parametrize(
    "printed, spoken",
    [("7б°", "7б"), ("10а:)", "10а"), ("25а*", "25а"), ("16**", "16"), ("1°", "1")],
)
def test_the_decorations_a_sheet_prints_are_not_pronounceable_and_are_stripped(printed, spoken):
    """The degree sign marks an obligatory problem and the star a hard one.  Neither is
    said out loud, so comparison happens on the stripped form."""
    assert normalise_label(printed) == spoken


def test_yo_is_folded_on_both_sides():
    """``Фёдоров`` is in the roster and no recogniser is reliable about the diaeresis."""
    assert fold("Фёдоров") == fold("Федоров")
