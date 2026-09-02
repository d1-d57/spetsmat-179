"""ИМЕНА — the owner's own criterion, in his own words, as four named tests.

    «если P15 узнаёт „Лёня Санин“ как Исанина — она узнает что угодно; если нет —
     на занятии я буду набирать имена по паспорту, и вся скорость текстового ввода
     пропадёт»

Each of the four breaks the matching a different way, and the four together are the whole
criterion.  They run against the REAL seeded catalogue, so the id in each assertion is the
id the bot would actually write into the journal.

⚠ THE NEGATIVE HALF IS NOT DECORATION.  Every test that says «this string resolves to this
child» is paired with the check that it did not merely resolve to SOMEBODY.  A matcher that
returned the same student for every input would pass four positive assertions out of four.
"""

from __future__ import annotations

import pytest

from core.services import bystryj_tekst as tekst
from core.services.golos import Verdict

from .conftest import OWNER_LINES


# =============================================================================
#  THE FOUR NAMED TESTS
# =============================================================================

def test_imena_lyonya_sanin_is_isanin_23(students):
    """«Лёня Санин» → Исанин Леонид, id 23.

    Broken THREE ways at once, which is why one fuzzy comparison of surnames cannot do it:
    the first letter of the surname is gone (Исанин → Санин), the given name is a
    hypocorism (Леонид → Лёня), and the two are written given-name-first.  This is the
    string the owner picked as his whole criterion.
    """
    match = tekst.match_student("Лёня Санин", students)
    assert match.student_id == 23, match.reason
    assert match.verdict is Verdict.CERTAIN, match.reason


def test_imena_katya_dolkireva_is_dolgireva_18(students):
    """«Катя Долкирева» → Долгирева Екатерина, id 18.

    A consonant swapped INSIDE the surname (г → к, which is what the ear does to a voiced
    stop before a voiceless one) plus a hypocorism the letters do not reach: «Катя» and
    «Екатерина» share three characters out of nine.
    """
    match = tekst.match_student("Катя Долкирева", students)
    assert match.student_id == 18, match.reason
    assert match.verdict is Verdict.CERTAIN, match.reason


def test_imena_anya_bocharova_is_bocharova_9(students):
    """«Аня Бочарова» → Бочарова Анна, id 9.  Order reversed, surname intact."""
    match = tekst.match_student("Аня Бочарова", students)
    assert match.student_id == 9, match.reason
    assert match.verdict is Verdict.CERTAIN, match.reason


def test_imena_vlad_bykov_is_bykov_11(students):
    """«Влад Быков» → Быков Владислав, id 11.  The given name shortened, not declined."""
    match = tekst.match_student("Влад Быков", students)
    assert match.student_id == 11, match.reason
    assert match.verdict is Verdict.CERTAIN, match.reason


@pytest.mark.parametrize("line,student_id,surname,name", OWNER_LINES)
def test_imena_all_four_owner_lines_resolve_through_the_whole_parser(
    line, student_id, surname, name, students, catalogue
):
    """The same four, reached the way the bot reaches them: a typed line into a draft.

    ``match_student`` being right and ``build_draft`` being right are two claims, and the
    four tests above only make the first one.  A block parser that handed the matcher the
    wrong slice of the line -- the labels glued onto the name, the bracket left in -- would
    leave all four green and the bot broken.
    """
    draft = tekst.build_draft(line, students=students, catalogue=catalogue)
    assert len(draft.rows) == 1, "one line about one child must be exactly one block"
    row = draft.rows[0]
    assert row.student_id == student_id, "%s -> %s (%s)" % (line, row.student_id, row.reason)

    student = catalogue.student(row.student_id)
    assert (student.surname, student.name) == (surname, name)


# =============================================================================
#  THE NEGATIVE HALF -- what must NOT happen
# =============================================================================

def test_imena_the_four_do_not_all_collapse_onto_one_child(students):
    """Four different strings, four DIFFERENT children.

    The cheapest way to pass every positive assertion above is to return the same student
    every time, and this is the test that costs nothing and closes it.
    """
    resolved = [
        tekst.match_student(line.split(" ", 2)[0] + " " + line.split(" ")[1], students).student_id
        for line, _, _, _ in OWNER_LINES
    ]
    assert len(set(resolved)) == 4, resolved
    assert sorted(resolved) == [9, 11, 18, 23]


#: Ten people who do not study at this school, used as a negative control.  The surnames
#: are deliberately Russian and deliberately plausible: a control made of «asdf» measures
#: nothing, because the failure being guarded against is a near-miss against a real child.
#:
#: ⚠ «Софья Ковалевская» is NOT in this list and belongs in neither column: the school has
#: an Искеева Софья, so the given name is a true match and the pair scores 72.  That is an
#: honest partial match rather than an invention, and it is named here so that a later
#: reader does not "fix" it into a refusal.
STRANGERS = (
    "Пафнутий Чебышёв",
    "Андрей Колмогоров",
    "Лев Понтрягин",
    "Николай Лобачевский",
    "Сергей Бернштейн",
    "Павел Александров",
    "Игорь Шафаревич",
    "Юрий Манин",
    "Ольга Ладыженская",
)


@pytest.mark.parametrize("stranger", STRANGERS)
def test_imena_a_stranger_resolves_to_nobody(stranger, students):
    """A name nobody in this school has must come back UNKNOWN, not «closest child».

    This is the rule the whole path is biased around: a plus put on the wrong child is
    noticed only by the child it went missing from.  Buttons, never a guess.

    MEASURED, AND THIS TEST IS WHERE THE MEASUREMENT LIVES.  Under the maximum rule that
    the dictation channel uses, THREE of these nine were accepted as real children with no
    doubt shown -- Чебышёв became Чапышев at 71, Лобачевский became Николаева at 82, Манин
    became Исанин at 73.  Comparing both written words against both fields and ADDING them
    refuses all three, because a stranger collides with one field by accident and never
    with both.  Should this test ever go red, the summed score has been reverted to a
    maximum somewhere and three known false children are back.
    """
    match = tekst.match_student(stranger, students)
    assert match.student_id is None, "invented a child for %r: %s" % (stranger, match.reason)
    assert match.verdict is Verdict.UNKNOWN


def test_imena_every_child_of_the_roster_resolves_to_themselves(students):
    """The sweep: all 56 children, written BOTH WAYS round, must each find themselves.

    Four named tests prove the matcher survives four hard cases; they cannot prove it did
    not break the other fifty-two while doing so.  This is the whole roster in both token
    orders -- 112 strings -- and it is the test that would catch a rule tuned until the
    owner's four passed at everybody else's expense.
    """
    misses = []
    for student in students:
        for written in (
            "%s %s" % (student.surname, student.name),
            "%s %s" % (student.name, student.surname),
        ):
            match = tekst.match_student(written, students)
            if match.student_id != student.id:
                misses.append((written, student.id, match.student_id, match.reason))
    assert not misses, "%d of %d forms resolved elsewhere: %s" % (
        len(misses), 2 * len(students), misses[:5],
    )


def test_imena_an_ambiguous_short_name_asks_instead_of_picking(students):
    """«Саша» alone is three children of this catalogue, so it must ask.

    The catalogue carries three Александры.  A matcher that ranked them and took the top
    one would be right one time in three, and would be wrong silently the other two.
    """
    match = tekst.match_student("Саша", students)
    assert match.student_id is None, match.reason
    assert match.verdict is Verdict.UNKNOWN
    assert match.alternatives, "refused to choose and offered no buttons either"


def test_imena_full_names_still_work(students):
    """The dictionary must not make the ordinary case worse.

    «Бочарова Анна», written out in full and in catalogue order, is what the owner falls
    back to when the short form fails -- and it is exactly what the expansion must leave
    alone, since the original phrase is always tried first.
    """
    match = tekst.match_student("Бочарова Анна", students)
    assert match.student_id == 9, match.reason


# =============================================================================
#  THE DICTIONARY ITSELF
# =============================================================================

def test_imena_diminutive_table_is_data_and_inverts_cleanly(students):
    """Every short name in the table resolves back to the full name it was written under.

    The index is built at import from the table, so this is the test that the building is
    faithful rather than that the table is complete -- completeness is a number, below.
    """
    for full, shorts in tekst.DIMINUTIVES.items():
        for short in shorts:
            assert full in tekst.full_names_for(short), "%s -> %s lost" % (short, full)
        assert full in tekst.full_names_for(full), "%s does not resolve to itself" % full


def test_imena_diminutive_coverage_over_the_real_roster(students):
    """How many of the 56 children the table actually reaches -- a NUMBER, not a claim.

    Four names of this catalogue are deliberately absent (Арон, Дэвин, Нино, Эльдар): their
    hypocorisms are not something this position knows, and an invented form is worse than a
    missing one -- a missing form costs a tap, an invented one can match the wrong child.
    The assertion is therefore a floor with the gap named, not «all 56».
    """
    covered, total = tekst.covered_names(students)
    assert total == 56
    assert covered == 52, (
        "coverage moved to %d of %d; if that is deliberate, move this number with it "
        "and say in the отчёт which names changed" % (covered, total)
    )

    uncovered = sorted(
        {student.name for student in students if not tekst.full_names_for(student.name)}
    )
    assert uncovered == ["Арон", "Дэвин", "Нино", "Эльдар"], uncovered


def test_imena_expansion_offers_every_reading_of_an_ambiguous_short_name():
    """«Слава» is Владислав, Вячеслав and Ярослав, and all three must be tried.

    Expansion happens on the INPUT, not on the roster, which is what keeps this module from
    adding a second matching channel: an expanded phrase is compared by exactly the metric,
    the declension table and the threshold every other screen uses.
    """
    variants = tekst.expand_diminutives("Слава Быков")
    assert variants[0] == "Слава Быков", "the phrase as written must be tried first"
    assert "Владислав Быков" in variants
    assert "Вячеслав Быков" in variants
    assert "Ярослав Быков" in variants


def test_imena_expansion_of_a_name_the_table_does_not_know_is_a_no_op():
    """A name with no entry produces the phrase and nothing else -- no invented forms."""
    assert tekst.expand_diminutives("Нино Кахиани") == ["Нино Кахиани"]


# =============================================================================
#  ONE WORD IS HALF THE EVIDENCE -- found by the §3 verifier, after the module was written
# =============================================================================

def test_imena_a_lone_surname_of_a_stranger_asks_instead_of_picking(students):
    """«Чебышёв» written alone used to become Чапышев at 71: CERTAIN, and the wrong child.

    Red when written.  The module's own comment claimed the sum-of-both-halves rule refused
    these three, and it does — but only when both halves are written.  All three of the
    strangers it named are ONE word, and one word cannot be added to anything, so the claim
    covered exactly the cases it was measured on and none of the cases it was written for.

    A refusal is not a failure here: the row draws buttons and a tap costs a second.
    """
    for stranger, wrongly in (("Чебышёв", "Чапышев"), ("Манин", "Исанин"),
                              ("Лобачевский", "Николаева")):
        match = tekst.match_student(stranger, students)
        assert match.student_id is None, (
            "«%s» was accepted as %s on one word" % (stranger, wrongly)
        )
        assert match.verdict is Verdict.UNKNOWN
        assert match.alternatives, "a refusal must still offer buttons"


def test_imena_a_lone_surname_of_a_real_child_still_resolves(students):
    """The floor must not cost the owner his own four names written short.

    Measured over both groups and not over the tidy one.  The owner's own spellings score
    88.9 («Долкирева», his `к` for `г`) to 100; eight strangers score 42.9 to 72.7.  The
    floor stands in the middle of that sixteen-point gap.

    ⚠ This case is why the list below includes «Долкирева» as well as «Долгирева».  A
    first floor was placed at 90 on the strength of the correctly-spelled surnames alone,
    and the owner's own misspelling — the entire reason this position exists — fell
    straight through it.
    """
    for lone, expected in (("Санин", 23), ("Быков", 11), ("Бочарова", 9),
                           ("Долгирева", 18), ("Долкирева", 18)):
        match = tekst.match_student(lone, students)
        assert match.student_id == expected, (lone, match.reason)
        assert match.verdict is Verdict.CERTAIN


def test_imena_the_floor_applies_to_one_word_and_not_to_two(students):
    """It is a statement about how much evidence there is, not about how close is close.

    «Пафнутий Чебышёв» is refused by the ordinary threshold on the summed score, and
    «Лёня Санин» is accepted at 95 — neither of them goes anywhere near the floor.  If the
    floor were applied to two-word input it would start refusing the owner's own lines.
    """
    assert tekst.LONE_WORD_FLOOR > 0
    assert tekst.match_student("Пафнутий Чебышёв", students).student_id is None
    two_words = tekst.match_student("Лёня Санин", students)
    assert two_words.student_id == 23
    assert two_words.score < 100, "the score is a real measurement, not a constant"
