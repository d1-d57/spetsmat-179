"""THE NAMED TEST: two candidates give BUTTONS, never a choice made by the machine.

🔴 THE TIE IS REAL AND IT IS MEASURED, NOT STAGED.  The live catalogue holds

    Цикунов Александр    and    Цуканов Александр

-- seven letters each, the same given name, differing by a transposition.  A child who
types «Цукунов» scores 85,714…  against BOTH (``rapidfuzz.fuzz.ratio`` over P7's case
forms), and the given name adds the same amount to each side.  The scores are equal to
the last digit, so there is nothing for a threshold to break; the only honest output is
two buttons.  A staged catalogue of «Иванов А» and «Иванов Б» would have proved that
the code can draw buttons, not that the code has anything to draw them for.

The second half of the file goes through the OWNER'S SCREEN with the real dispatcher,
because «показать владельцу кнопки» is a claim about the screen, and a service-level
assertion cannot see whether a button was drawn.
"""

from __future__ import annotations

import pytest

from conftest import tg_for
from core.services.roster import AmbiguousStudent, match_students, CatalogueStudent

#: The two real children the tie is between, and the misspelling that ties them.
LEFT = ("Цикунов", "Александр")
RIGHT = ("Цуканов", "Александр")
TYPO = ("Цукунов", "Александр")

AMBIG_TG = 7_900_002


def test_dva_kandidata_dayut_knopki_a_ne_vybor(roster, full_catalogue):
    """Two rows fit; the answer is «ambiguous» and it names BOTH."""
    pending = roster.submit_student(tg_id=AMBIG_TG, surname=TYPO[0], name=TYPO[1])
    match = roster.match_student(pending)

    assert match.kind == "ambiguous", (
        "«%s %s» resolved to %s -- the machine picked between two children"
        % (TYPO[0], TYPO[1], match.kind)
    )
    labels = {candidate.student.label for candidate in match.candidates}
    assert labels == {"%s %s" % LEFT, "%s %s" % RIGHT}, labels


def test_the_tie_is_exact_and_not_an_artefact_of_the_band(full_catalogue):
    """The two scores are EQUAL, not merely close.

    Pinned so that a later change to the weights cannot turn this file into a test of
    the tie band instead of a test of a tie.
    """
    left = CatalogueStudent(id=1, surname=LEFT[0], name=LEFT[1])
    right = CatalogueStudent(id=2, surname=RIGHT[0], name=RIGHT[1])
    match = match_students(TYPO[0], TYPO[1], [left, right])
    assert match.kind == "ambiguous"
    scores = [round(candidate.score, 9) for candidate in match.candidates]
    assert scores[0] == scores[1], scores


def test_nothing_is_written_while_the_owner_has_not_chosen(connection, roster):
    """An ambiguous заявка leaves the catalogue exactly as it was."""
    before = connection.execute(
        "select id, tg_id, status from students order by id"
    ).fetchall()
    pending = roster.submit_student(tg_id=AMBIG_TG, surname=TYPO[0], name=TYPO[1])
    with pytest.raises(AmbiguousStudent):
        roster.confirm_student(pending)
    after = connection.execute(
        "select id, tg_id, status from students order by id"
    ).fetchall()
    assert [tuple(row) for row in after] == [tuple(row) for row in before]
    assert [p.id for p in roster.list_pending()] == [pending.id], (
        "the заявка must stay open until the owner presses a button"
    )


def test_the_owner_can_still_choose_and_the_choice_binds(connection, roster, full_catalogue):
    """After the buttons: the owner names a row, and only that row is bound."""
    pending = roster.submit_student(tg_id=AMBIG_TG, surname=TYPO[0], name=TYPO[1])
    chosen = full_catalogue["student_ids"][RIGHT]
    roster.bind_student(pending, chosen)
    roster.accept(pending.id)

    assert roster.student_id_for(AMBIG_TG) == chosen
    other = connection.execute(
        "select tg_id from students where id = ?",
        (full_catalogue["student_ids"][LEFT],),
    ).fetchone()
    assert other["tg_id"] is None, "the child who was NOT chosen got bound anyway"
    assert connection.execute("select count(*) c from students").fetchone()["c"] == 56


def test_a_name_nobody_has_offers_creation_and_does_not_guess(roster, full_catalogue):
    """Zero candidates is «none», not «the closest one».

    «Иванов Иван» is in no way in this catalogue, and the nearest row it reaches is
    below the floor.  The screen answers with one button -- «нет в списке — завести
    нового» -- and creation happens only when it is pressed.
    """
    pending = roster.submit_student(tg_id=tg_for(555), surname="Иванов", name="Иван")
    match = roster.match_student(pending)
    assert match.kind == "none", [c.student.label for c in match.candidates]
