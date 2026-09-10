"""The four величины of the кондуит, judged as arithmetic and not as pixels.

WHY THESE ARE TESTED AWAY FROM THE SCREEN.  Every number the кондуит prints — «сдал
столько обязательных из стольких», «столько человек сдало эту задачу», «задача закрыта
классом», «эта задача в гробарии» — is a projection over cells, and a projection is
wrong in ways that a rendered page cannot show you: the ``retract`` counted as a plus,
the листок with no обязательные lighting up every row, the гробарий naming a fourth
solver.  Each of those produces a page that looks entirely healthy.

🔴 THE ГРОБАРИЙ IS TESTED HERE AND NOWHERE ELSE, BECAUSE THE LIVE БАЗА CANNOT TEST IT.
On 2026-09-10 the 9-class листки are 16A, 16α and 16ℵ, all issued 2026-09-03 and all
newest — nothing of that class is historical yet, so the вкладка is legitimately empty
and a check against живая база would be green against nothing.  The rule fires on Monday,
when листок 17 supersedes them.  These tests are what says the rule will fire correctly
when it does, instead of the вкладка being discovered wrong in front of a class.
"""

from __future__ import annotations

import config
from core.models import CellState, Problem
from core.services.progress import (
    obyazatelnyh_sdano,
    skolko_sdalo,
    v_grobarij,
    zakryta_klassom,
    zapisi_grobaria,
)


#: A листок in the shape the real ones have: обязательные (`◦`), письменные (`†`) — which
#: are obligatory too, and that is the half of the owner's «кружки И крестики вместе» that
#: a test with only `обязательная` in it would never notice — звёзды and обычные, which
#: are not.
LISTOK = [
    Problem(id=1, sheet_id=7, label="1", kind="обязательная", ord=1),
    Problem(id=2, sheet_id=7, label="2", kind="письменная", ord=2),
    Problem(id=3, sheet_id=7, label="3", kind="звезда", ord=3),
    Problem(id=4, sheet_id=7, label="4", kind="обычная", ord=4),
    Problem(id=5, sheet_id=7, label="5", kind="обязательная", ord=5),
]


def sost(**pary) -> dict:
    """``{"1:1": "solved"}`` → the states dict the projections take.

    Written out as a literal in every test rather than built by a helper that knows the
    rules: a fixture that computed the states would be the same arithmetic under test.
    """
    return {tuple(int(x) for x in klyuch.split(":")): CellState(znachenie)
            for klyuch, znachenie in pary.items()}


# ----------------------------------------------- величина 1: обязательные у школьника


def test_pismennaya_is_obligatory_too_and_zvezda_never_is():
    """«Крестик тоже обязателен, звёзды не обязательны никогда» — as arithmetic.

    Three of the five problems above are obligatory (`◦`, `†`, `◦`); a реализация that
    read only `обязательная` would say two, and the pupil's row would promise a closure
    he has not reached.
    """
    schyot = obyazatelnyh_sdano(LISTOK, sost(), student_id=1)
    assert schyot.vsego == 3, "обязательные — это ◦ и † вместе"
    assert schyot.sdano == 0
    assert schyot.ostalos == 3
    assert not schyot.zakryl


def test_sdano_counts_only_credited_cells():
    """A ``retract`` is a hand-in that was not defended, and it is not a plus.

    This is the single most expensive mistake available in this file: the pupil is shown
    as having closed his обязательные, the teacher stops asking him, and the problem is
    never defended.
    """
    schyot = obyazatelnyh_sdano(
        LISTOK,
        sost(**{"1:1": "solved", "1:2": "retracted", "1:5": "empty"}),
        student_id=1,
    )
    assert (schyot.sdano, schyot.vsego, schyot.ostalos) == (1, 3, 2)
    assert not schyot.zakryl


def test_zakryl_is_true_only_when_nothing_obligatory_is_left():
    schyot = obyazatelnyh_sdano(
        LISTOK,
        sost(**{"1:1": "solved", "1:2": "solved", "1:5": "solved"}),
        student_id=1,
    )
    assert schyot.zakryl and schyot.ostalos == 0
    # The звезда and the обычная are untaken, and that changes nothing: not obligatory.
    assert schyot.vsego == 3


def test_a_listok_with_no_obligatory_problems_never_glows():
    """Листки ``1д``–``4д`` really are like this on the live база: 0 обязательных of 99.

    Vacuous truth here would light up all fifty-three rows of four листков, and a signal
    that fires for everybody says nothing about anybody.
    """
    tolko_zvyozdy = [p for p in LISTOK if not p.is_obligatory]
    schyot = obyazatelnyh_sdano(tolko_zvyozdy, sost(), student_id=1)
    assert schyot.vsego == 0
    assert not schyot.zakryl, "пустое множество обязательных — это не «сдал все»"


def test_a_pupil_absent_from_the_states_is_counted_as_having_taken_nothing():
    """Not an exception: a pupil who left mid-year legitimately has no cells."""
    schyot = obyazatelnyh_sdano(LISTOK, sost(**{"1:1": "solved"}), student_id=999)
    assert (schyot.sdano, schyot.vsego) == (0, 3)


# ------------------------------------------- величина 3: сколько человек сдало задачу


def test_skolko_sdalo_counts_credited_over_the_pupils_it_was_given():
    sostoyaniya = sost(**{"1:1": "solved", "2:1": "solved",
                          "3:1": "retracted", "4:1": "empty"})
    assert skolko_sdalo(1, [1, 2, 3, 4], sostoyaniya) == 2
    # The same journal, a different list of pupils, a different honest answer.
    assert skolko_sdalo(1, [1], sostoyaniya) == 1




def test_the_two_thresholds_do_not_meet_and_three_is_neither():
    """Both are the owner's own words and both read one constant.

    «Сдало больше трёх — всё ок» and «решило меньше трёх — в гробарий» leave exactly
    three in between.  The test states the gap so that closing it is a decision somebody
    makes on purpose rather than a silent drift of one predicate towards the other.
    """
    assert config.GRAVEYARD_THRESHOLD == 3
    assert [zakryta_klassom(n) for n in range(6)] == [
        False, False, False, False, True, True]
    assert [v_grobarij(n) for n in range(6)] == [
        True, True, True, False, False, False]
    assert not zakryta_klassom(3) and not v_grobarij(3), "тройка — ни то, ни другое"


# --------------------------------------------------------------- величина 5: гробарий


def kogda_pusto(_student_id, _problem_id):
    """No dates at all — the case where order can only come from the name."""
    return None


IMENA = {1: "Ада", 2: "Боря", 3: "Витя", 4: "Гриша", 5: "Дина"}


def test_a_problem_taken_by_three_or_more_stays_out_of_the_graveyard():
    sostoyaniya = sost(**{"1:1": "solved", "2:1": "solved", "3:1": "solved"})
    zapisi = zapisi_grobaria(LISTOK[:1], [1, 2, 3, 4, 5], sostoyaniya,
                             kogda_pusto, IMENA.get)
    assert zapisi == [], "трое сдали — задача не в гробарии"


def test_a_problem_taken_by_two_falls_in_with_both_names():
    sostoyaniya = sost(**{"1:1": "solved", "2:1": "solved", "3:1": "retracted"})
    zapisi = zapisi_grobaria(LISTOK[:1], [1, 2, 3, 4, 5], sostoyaniya,
                             kogda_pusto, IMENA.get)
    assert len(zapisi) == 1
    assert zapisi[0].sdalo == 2
    assert zapisi[0].pervye == ("Ада", "Боря")
    assert zapisi[0].problem.label == "1"


def test_nobody_took_it_means_a_graveyard_row_with_no_names():
    """The row still exists.  «Никто не сдал» is the strongest thing a гробарий says, and
    a rule that only listed problems with at least one solver would drop it."""
    zapisi = zapisi_grobaria(LISTOK[:1], [1, 2, 3], sost(), kogda_pusto, IMENA.get)
    assert len(zapisi) == 1 and zapisi[0].sdalo == 0 and zapisi[0].pervye == ()


def test_names_are_the_first_solvers_in_order_and_are_capped_at_the_threshold():
    """«Когда три человека уже сдало, дальше имена не записывают».

    Reached here through a problem that only just misses the graveyard cap in the OTHER
    direction: the cap on names and the cap on membership are the same number, so the
    only way to see the name cap alone is to ask the assembler for a row it would not
    itself keep.  The chronology is deliberately REVERSED against the names: sorting
    alphabetically would give the same two names in the other order, and a test that did
    not reverse them could not tell the two rules apart.
    """
    poryadok = {1: "2026-09-08", 2: "2026-09-01", 3: "2026-09-04"}
    zapisi = zapisi_grobaria(
        LISTOK[:1], [1, 2, 3],
        sost(**{"1:1": "solved", "2:1": "solved", "3:1": "solved"}),
        lambda s, _p: poryadok[s], IMENA.get)
    # Three is not a гробарий at all -- no row -- and that IS the cap on the name list.
    assert zapisi == []
    # Two is a гробарий, and the order is the chronological one.
    zapisi = zapisi_grobaria(
        LISTOK[:1], [1, 2, 3],
        sost(**{"1:1": "solved", "3:1": "solved"}),
        lambda s, _p: poryadok[s], IMENA.get)
    assert zapisi[0].pervye == ("Витя", "Ада"), "раньше сдал — раньше в списке"


def test_a_solver_with_no_date_sorts_after_one_with_a_date():
    """Absence of a date is not evidence of being early.

    The live журнал has 15 847 events written under one imported ``recorded_at`` and cells
    whose lesson day cannot be derived at all; letting those jump to the head of the list
    would name the wrong pupil as the first to take a problem.
    """
    daty = {1: None, 2: "2026-09-01"}
    zapisi = zapisi_grobaria(
        LISTOK[:1], [1, 2],
        sost(**{"1:1": "solved", "2:1": "solved"}),
        lambda s, _p: daty[s], IMENA.get)
    assert zapisi[0].pervye == ("Боря", "Ада")


def test_every_problem_of_the_listok_is_judged_including_the_stars():
    """Гробарий is about the листок, not about its obligatory half.

    «Про каждую задачу необязательную тоже» — the owner asked for the count on the
    optional ones by name, and a гробарий that quietly skipped звёзды would lose exactly
    the problems most likely to be taken by fewer than three.
    """
    sostoyaniya = sost(**{"%d:%d" % (u, p.id): "solved"
                          for p in LISTOK for u in (1, 2, 3, 4)
                          if p.kind != "звезда"})
    zapisi = zapisi_grobaria(LISTOK, [1, 2, 3, 4], sostoyaniya,
                             kogda_pusto, IMENA.get)
    assert [z.problem.label for z in zapisi] == ["3"], "в гробарий попала только звезда"
