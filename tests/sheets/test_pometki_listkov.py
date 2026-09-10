"""The marks the sheets of number 16 print beside a problem number, read out of the PDFs.

WHAT THESE TESTS ARE FOR.  `tools/import_listka.py` was carrying exactly one of the three
marks a листок prints — the star — and dropping the circle and the dagger, so a sheet that
distinguished "hand this in", "hand this in in writing" and "this one is hard" arrived on
the site as a row of bare numbers.  These tests are the gate on the repair, and they are
run against the SERVED PDFs in `docs/listki/`, not against a fixture: a fixture would go on
passing if somebody replaced the sheet the site hands the pupil.

🔴 A GREP OVER A PDF PROVES PRESENCE AND NEVER PROVES ABSENCE, which is why the counts
below are asserted as EQUALITIES and not as "at least".  A text layer breaks glyphs across
line wraps and letter-spacing, and the honest failure mode of this parser is not a wrong
dagger but a missing one.  The three numbers `1 · 4 · 0` were read off the PDFs by the
analyst by eye on 2026-09-09, before any of this code existed, and are the fixed point the
parser is checked against rather than the other way round.

For `16A` there is a SECOND, INDEPENDENT SOURCE — `materials/spetsmat-2026/listki/
16-derevya.tex`, where the author wrote `\\nomer{8}{\\dag}` outright — and the last test
compares the two whenever that repository is on the machine.  It is skipped on the server,
where `materials/` does not exist, and that is the honest thing for it to do: the PDF is
the source of record precisely because it is the only one both machines have.
"""

from __future__ import annotations

import pathlib

import pytest

from tools.import_listka import (
    razobrat,
    razobrat_tex,
    vid_po_pometke,
    vidy_yacheek,
    yachejki,
    _tex_istochnik,
)

#: Sheet → the count of every kind on it, and the count of cells they must add up to.
#: Read off the served PDFs; the `письменная` column is the analyst's count of daggers of
#: 2026-09-09 and is the reason this file exists.
OZHIDAEM = {
    "16A": {"обязательная": 17, "письменная": 1, "звезда": 3, "обычная": 0},
    "16α": {"обязательная": 7, "письменная": 4, "звезда": 2, "обычная": 4},
    "16ℵ": {"обязательная": 4, "письменная": 0, "звезда": 1, "обычная": 8},
}

#: The cells whose kind is stated one by one rather than only counted.  These are the ones
#: the заход names by hand, plus both shapes of sub-item inheritance.
IMENNO = {
    "16A": {"1а": "обязательная", "7в": "обязательная", "8": "письменная",
            "12": "звезда", "13б": "звезда"},
    "16α": {"2": "письменная", "3": "письменная", "5": "письменная", "7": "письменная",
            "9": "обычная", "14а": "обязательная", "14б": "обязательная",
            "14в": "звезда", "15": "звезда"},
    "16ℵ": {"-1а": "обязательная", "-1в": "обязательная", "0": "звезда",
            "1": "обычная", "7": "обязательная"},
}


def _vidy(nomer: str) -> dict:
    bloki, _otkuda = razobrat(nomer)
    return dict(vidy_yacheek(bloki))


@pytest.mark.parametrize("nomer", sorted(OZHIDAEM))
def test_kazhdaya_yachejka_lista_imeet_rovno_odin_vid(nomer):
    """Every cell gets a kind, and the kinds add up to the number of cells.

    This is the sum the готовности criterion of заход `vidy-zadach` is checked on, and it
    is asserted here rather than only printed by the tool so that it goes red in CI too.
    """
    bloki, _otkuda = razobrat(nomer)
    metki = yachejki(bloki)
    vidy = vidy_yacheek(bloki)

    assert [m for m, _v in vidy] == metki, "состав и разметка обязаны идти по одним ячейкам"
    schyot = {vid: sum(1 for _m, v in vidy if v == vid) for vid in OZHIDAEM[nomer]}
    assert schyot == OZHIDAEM[nomer]
    assert sum(schyot.values()) == len(metki)


@pytest.mark.parametrize("nomer", sorted(OZHIDAEM))
def test_pismennyh_stolko_zhe_skolko_krestikov_na_bumage(nomer):
    """`16A` → 1, `16α` → 4, `16ℵ` → 0 — counted by eye on 2026-09-09, before the code.

    🔴 THE ZERO IS THE LOAD-BEARING ONE.  A parser that stopped seeing daggers altogether
    would keep both other numbers plausible-looking and would agree with this one, so the
    zero is asserted next to two non-zeros on purpose: the three can only all hold if the
    dagger is genuinely being read.
    """
    vidy = _vidy(nomer)
    krestikov = sum(1 for v in vidy.values() if v == "письменная")
    assert krestikov == OZHIDAEM[nomer]["письменная"]


@pytest.mark.parametrize("nomer", sorted(IMENNO))
def test_nazvannye_yachejki_nesut_imenno_svoj_vid(nomer):
    """The cells named one by one, including both shapes of sub-item inheritance.

    `16A` problem 7 carries `◦` on the NUMBER and bare letters, so `7а 7б 7в` inherit it;
    `16α` problem 14 carries nothing on the number and `а)◦ б)◦ в)⋆` on the sub-items, so
    two of its three cells are obligatory and the third is a star.  A rule that always took
    the problem's mark and a rule that always took the sub-item's each get one of these
    two wrong, and each would leave the other looking correct.
    """
    vidy = _vidy(nomer)
    for metka, ozhidaem in IMENNO[nomer].items():
        assert vidy[metka] == ozhidaem, "%s листка %s" % (metka, nomer)


def test_pustaya_pometka_eto_obychnaya_a_ne_otsutstvie_otveta():
    """The reading of one run of glyphs, and the order of obligation inside it."""
    assert vid_po_pometke("") == "обычная"
    assert vid_po_pometke("◦") == "обязательная"
    assert vid_po_pometke("∘") == "обязательная", "ring operator из текстового слоя PDF"
    assert vid_po_pometke("†") == "письменная"
    assert vid_po_pometke("⋆") == "звезда"
    # Обязательство сильнее приглашения, а письменное обязательство — сильнее устного.
    assert vid_po_pometke("†◦") == "письменная"
    assert vid_po_pometke("◦⋆") == "обязательная"


def test_pdf_i_tex_soglasny_o_listke_16A():
    """Two sources, one answer — where both exist.

    `16-derevya.tex` is in the neighbouring `materials/` repository, which is on the
    laptop and not on the server, so this test SKIPS rather than fails when it is absent.
    A test that failed there would be a test about which machine it is running on.
    """
    put = _tex_istochnik("16A")
    if put is None:
        pytest.skip("materials/spetsmat-2026/listki/16-derevya.tex отсюда не виден")
    iz_tex = dict(vidy_yacheek(razobrat_tex(pathlib.Path(put).read_text(encoding="utf-8"))))
    assert iz_tex == _vidy("16A")
    assert iz_tex["8"] == "письменная"
