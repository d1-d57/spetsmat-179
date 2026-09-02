"""Round-tripping three real listki of last year against the seed.

These tests are the readiness criterion: parse sheet ``1``, sheet ``2д`` and
sheet ``4д`` from the labels the seed already carries, and assert the draft
agrees with the seed row by row.  A label that the parser swallows silently
would make these tests look exactly like a clean pass -- that is the failure
mode they are here to catch.

Counts held honest:
  * sheet ``1``  -- 23 problems, 12 obligatory;
  * sheet ``2д`` -- 32 problems (one duplicate repair);
  * sheet ``4д`` -- 26 problems, stored by the seed WITHOUT a header row and
    WITHOUT the ``✘`` glyph (``grep -c '✘' seed/sheets.json`` is 0); the
    graveyard path is covered synthetically, not by this sheet.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.services import sheets as parser
from core.services.sheets import (
    ListokLine,
    NotConfirmed,
    UnknownActorRole,
    UnknownLabelShape,
    confirm_and_write,
    parse_sheet,
    register_known_label_shapes,
)


SHEET_NUMBERS = ("1", "2д", "4д")


def _seed_sheets():
    return json.loads(Path("seed/sheets.json").read_text(encoding="utf-8"))


def _lines_for_seed_sheet(seed_sheet):
    """Convert one seed entry into the ListokLines the parser takes.

    The seed's ``kind`` field is carried as a ``kind_hint``; the modifier run
    in the label is what really decides, and the parser must agree with the
    seed on every row.
    """
    return [
        ListokLine(text=task["label"], kind_hint=task["kind"])
        for task in seed_sheet["tasks"]
    ]


@pytest.mark.parametrize("number", SHEET_NUMBERS)
def test_three_real_sheets_round_trip_against_seed(number):
    """Parse a listok the seed already carries; the draft must agree row by row.

    The criterion the parser holds itself to: every label recovered, every kind
    matched, every order preserved.  ``2д`` exercises the duplicate repair,
    ``4д`` exercises the graveyard meta-mark, ``1`` exercises the canonical
    case.
    """
    seed_sheet = next(s for s in _seed_sheets() if s["number"] == number)
    draft = parse_sheet(
        number=seed_sheet["number"],
        title=seed_sheet["title"],
        ord=seed_sheet["ord"],
        layout=seed_sheet.get("layout", "old"),
        lines=_lines_for_seed_sheet(seed_sheet),
        has_header=(number not in {"1д", "2д"}),
    )

    assert draft.number == seed_sheet["number"]
    assert draft.title == seed_sheet["title"]
    assert draft.ord == seed_sheet["ord"]
    assert len(draft.problems) == len(seed_sheet["tasks"]), (
        "раскладка %r: получено %d задач, в seed %d"
        % (number, len(draft.problems), len(seed_sheet["tasks"]))
    )

    seed_by_label = {task["label"]: task for task in seed_sheet["tasks"]}
    # The duplicate repair in 2д changes the FIRST occurrence of ``12д`` to
    # ``12г`` -- the same rule as ``core/services/seeding.py``: the repair
    # is keyed on the 0-based occurrence, not the duplicate-detection. After
    # the repair the column reads ``12а 12б 12в 12д 12е 12г 12ж`` (P2's
    # reading), so the seed positions and the draft positions no longer
    # align one-to-one: we compare the whole draft against the seed
    # row-by-row via the ``repaired_from`` note.
    for index, problem in enumerate(draft.problems):
        seed_task = seed_sheet["tasks"][index]
        # The first ``12д`` in the seed (sheet 2д, ord=24) gets repaired:
        if number == "2д" and seed_task["label"] == "12д" and index == 23:
            assert problem.label == "12г", (
                "ремонт должен был переименовать 12д в 12г; получено %r"
                % problem.label
            )
            assert problem.repaired_from == "12д"
            assert problem.kind == seed_task["kind"]
        else:
            assert problem.label == seed_task["label"], (
                "раскладка %r, задача %d: ожидалось %r, получено %r"
                % (number, index + 1, seed_task["label"], problem.label)
            )
            assert problem.kind == seed_task["kind"], (
                "раскладка %r, задача %r: ожидался тип %r, получен %r"
                % (number, problem.label, seed_task["kind"], problem.kind)
            )
            assert problem.ord == index + 1


def test_4d_carries_graveyard_marks_as_meta():
    """``✘`` on a label is a meta-mark the parser carries but never folds in.

    ``✘`` is NOT a kind.  A parser that folded it into ``kind`` would lose
    the graveyard distinction and make the "did anyone take this?" projection
    unanswerable.  The seed itself does not carry ``✘`` (the workbook does);
    this test parses labels WITH ``✘`` and asserts the parser keeps the kind
    intact and the meta-mark in ``notes``.
    """
    draft = parse_sheet(
        number="4д",
        title="4д. Фибоначчи",
        ord=18,
        layout="old",
        lines=[
            ListokLine(text="1✘", kind_hint="обычная"),
            ListokLine(text="2а✘", kind_hint="обычная"),
            ListokLine(text="2б✘", kind_hint="обычная"),
            # ``°`` is what makes this one obligatory -- the GLYPH, not the
            # hint.  The hint agrees with it, which is now the only thing a
            # hint is allowed to do.
            ListokLine(text="3°✘", kind_hint="обязательная"),
        ],
        # ``4д`` HAS a header.  It used to be listed in ``NO_HEADER_SHEETS``
        # and declared here without one; nobody noticed because the flag did
        # nothing.  The задание's measured fact is that ``1д`` and ``2д``
        # carry the 50 header-less problems between them -- 18 + 32 = 50 --
        # and ``4д``'s 26 are not part of that number.
        has_header=True,
    )
    assert len(draft.problems) == 4
    for problem in draft.problems:
        assert problem.notes == "✘", (
            "задача %r должна нести ✘ в notes; получено %r"
            % (problem.label, problem.notes)
        )
        assert problem.kind in ("обычная", "обязательная"), (
            "✘ не должен менять kind; получено %r" % problem.kind
        )
    # The ✘ version of an obligatory problem stays obligatory: ``°`` decides
    # the kind and ``✘`` never touches it.
    assert draft.problems[3].kind == "обязательная"
    assert draft.problems[3].label == "3°", (
        "✘ снимается с хранимой метки, ° остаётся; получено %r"
        % draft.problems[3].label
    )


def test_unknown_label_shape_raises():
    """A glyph the parser has not been taught raises with the offending line.

    Silent skips are the failure mode P2 paid for.  An unknown character in a
    label is the test of the rule.
    """
    with pytest.raises(UnknownLabelShape) as info:
        parse_sheet(
            number="X",
            title="test",
            ord=1,
            layout="old",
            lines=[ListokLine(text="1x°", kind_hint="")],  # 'x' is not a Russian letter
        )
    assert "1x" in str(info.value) or "x" in str(info.value).lower()


def test_teacher_is_refused_at_confirm_gate(in_memory_writer):
    """A teacher cannot upload a listok; the gate raises the same way for an
    unknown role, so the screen cannot tell the two apart.

    The test uses ``confirm_and_write`` directly because that is the gate the
    bot will call.  Calling it as a senior works; calling it as a teacher
    raises; the writer records nothing in the refused case.
    """
    seed_sheet = next(s for s in _seed_sheets() if s["number"] == "1")
    draft = parse_sheet(
        number=seed_sheet["number"],
        title=seed_sheet["title"],
        ord=seed_sheet["ord"],
        layout=seed_sheet.get("layout", "old"),
        lines=_lines_for_seed_sheet(seed_sheet),
        has_header=True,
    )

    sheet_id, problem_ids = confirm_and_write(
        draft, actor_role="senior", writer=in_memory_writer,
        confirmed=True, issued_at="2026-09-02",
    )
    assert sheet_id == 1
    assert len(problem_ids) == 23
    assert len(in_memory_writer.sheets) == 1
    assert len(in_memory_writer.problems) == 23

    # A fresh draft for the second refusal case (the writer is shared).
    with pytest.raises(UnknownActorRole):
        confirm_and_write(
            draft, actor_role="teacher", writer=in_memory_writer,
            confirmed=True,
        )

    with pytest.raises(UnknownActorRole):
        confirm_and_write(
            draft, actor_role="unknown_role", writer=in_memory_writer,
            confirmed=True,
        )

    # The refused attempts left no state behind.
    assert len(in_memory_writer.sheets) == 1
    assert len(in_memory_writer.problems) == 23


def test_nothing_is_written_without_an_explicit_confirm(in_memory_writer):
    """The senior's YES is a parameter that can be missing, not a convention.

    Before this test the "no write without confirmation" rule was carried by
    the NAME ``confirm_and_write`` and by nothing else -- the §3 verifier
    pointed out that a rule which cannot go red is not a rule.  ``confirmed``
    defaults to ``False``, so a caller who forgets it is REFUSED rather than
    writing a whole listok nobody looked at.

    A senior who is genuinely a senior is still refused without the YES: the
    role and the confirmation are two independent gates, and this test proves
    they are independent by passing the strongest possible role.
    """
    seed_sheet = next(s for s in _seed_sheets() if s["number"] == "1")
    draft = parse_sheet(
        number=seed_sheet["number"],
        title=seed_sheet["title"],
        ord=seed_sheet["ord"],
        layout=seed_sheet.get("layout", "old"),
        lines=_lines_for_seed_sheet(seed_sheet),
        has_header=True,
    )

    with pytest.raises(NotConfirmed):
        confirm_and_write(draft, actor_role="senior", writer=in_memory_writer)
    with pytest.raises(NotConfirmed):
        confirm_and_write(
            draft, actor_role="senior", writer=in_memory_writer, confirmed=False,
        )

    assert in_memory_writer.sheets == [], "неподтверждённый черновик записал листок"
    assert in_memory_writer.problems == [], "неподтверждённый черновик записал задачи"


def test_only_literal_true_confirms(in_memory_writer):
    """``confirmed`` is a bool, and truthy is not the same thing as ``True``.

    The gate used to read ``if not confirmed``, so the strings ``"no"`` and
    ``"false"``, the number ``-1``, a non-empty list and a bare ``object()``
    all counted as a human saying yes -- the §3 verifier wrote nine listki
    that way in a single probe.  A screen that forwards a form field or a JSON
    value verbatim hands this gate a string, and the string ``"false"`` is
    truthy.  This is the project's single most important rule; it does not get
    to be decided by Python's truth table.
    """
    seed_sheet = next(s for s in _seed_sheets() if s["number"] == "1")
    draft = parse_sheet(
        number=seed_sheet["number"],
        title=seed_sheet["title"],
        ord=seed_sheet["ord"],
        layout=seed_sheet.get("layout", "old"),
        lines=_lines_for_seed_sheet(seed_sheet),
        has_header=True,
    )

    for truthy in ("yes", "no", "false", "False", -1, 0.1, [0], {"a": 1}, object(), 1):
        with pytest.raises(NotConfirmed):
            confirm_and_write(
                draft, actor_role="senior", writer=in_memory_writer,
                confirmed=truthy,
            )
    assert in_memory_writer.sheets == [], (
        "нечто похожее на True записало листок: %r" % (in_memory_writer.sheets,)
    )
    assert in_memory_writer.problems == []

    # And the one value that IS the human's yes.
    sheet_id, problem_ids = confirm_and_write(
        draft, actor_role="senior", writer=in_memory_writer, confirmed=True,
    )
    assert sheet_id == 1 and len(problem_ids) == 23


def test_a_parser_that_was_never_taught_refuses_everything():
    """Never taught and taught-nothing-on-purpose are different states.

    They used to be the same one, and both meant "accept whatever the grammar
    lets through": a freshly imported module had ZERO strictness, and the
    verifier got ``999999ж**`` back as ``двойная`` out of a parser that had
    been taught nothing at all.  The loose mode is legitimate -- a caller who
    does not know last year's data yet wants it -- but it has to be asked for
    by name, not arrived at by doing nothing.
    """
    saved_registered = parser._SHAPES_REGISTERED
    saved_base_re = parser._KNOWN_BASE_RE
    try:
        parser._SHAPES_REGISTERED = False
        parser._KNOWN_BASE_RE = None
        with pytest.raises(UnknownLabelShape) as info:
            parse_sheet(
                number="test", title="тест", ord=1, layout="old",
                lines=[ListokLine(text="999999ж**")],
            )
        assert "register_known_label_shapes" in str(info.value), (
            "отказ обязан сказать, ЧТО позвать; получено %s" % info.value
        )

        # Asked for by name: the grammar-only mode, and it accepts.
        parser.register_known_label_shapes([])
        draft = parse_sheet(
            number="test", title="тест", ord=1, layout="old",
            lines=[ListokLine(text="999999ж**")],
        )
        assert draft.problems[0].kind == "двойная"
    finally:
        parser._SHAPES_REGISTERED = saved_registered
        parser._KNOWN_BASE_RE = saved_base_re


def test_a_repair_landing_on_a_folded_label_still_names_what_she_typed():
    """Two rewrites on one row must report the EARLIER one, not the later.

    The Latin-``a`` fold happens first, the duplicate repair second, and
    ``repaired_from`` used to be overwritten by the repair with the already
    folded form -- reporting back a label the senior never wrote.  Not
    reachable through the seed (sheet 7's ``2°a`` is not a duplicate);
    reachable on a real listok, which is what this parser is for.
    """
    # The repair registry is keyed on the BASE -- number plus letter, with the
    # infix ``°`` and the modifier run stripped -- so ``2°a`` is keyed ``2а``.
    key = ("складка", "2а", 0)
    parser.DUPLICATE_LABEL_REPAIRS[key] = "3"
    try:
        draft = parse_sheet(
            number="складка", title="тест", ord=1, layout="old",
            lines=[ListokLine(text="2°a")],
        )
    finally:
        del parser.DUPLICATE_LABEL_REPAIRS[key]

    assert draft.problems[0].label == "3"
    assert draft.problems[0].repaired_from == "2°a", (
        "названо %r — это форма ПОСЛЕ свёртки, старший писал '2°a'"
        % draft.problems[0].repaired_from
    )


def test_duplicate_label_without_repair_raises():
    """A duplicated label not in the repair table is refused with a clear reason.

    Same rule as ``core/services/seeding.py``: silent "keep the first one"
    drops a problem from the catalogue and looks like a clean pass.
    """
    # Build a listok with a deliberately duplicated label; the registry is
    # cleared by the parser module-level dict, so we patch it for the test.
    from core.services import sheets as parser_mod
    saved = dict(parser_mod.DUPLICATE_LABEL_REPAIRS)
    parser_mod.DUPLICATE_LABEL_REPAIRS.clear()
    try:
        with pytest.raises(UnknownLabelShape) as info:
            parse_sheet(
                number="99",
                title="тест",
                ord=99,
                layout="old",
                lines=[
                    ListokLine(text="1а", kind_hint=""),
                    ListokLine(text="1а", kind_hint=""),
                ],
            )
        assert "1а" in str(info.value)
    finally:
        parser_mod.DUPLICATE_LABEL_REPAIRS.update(saved)


def test_repaired_label_carries_the_original():
    """The repair is reported back on the draft, not hidden.

    A silent rename would make the seed and the draft disagree; the test
    catches that by asking the draft what it repaired.
    """
    seed_sheet = next(s for s in _seed_sheets() if s["number"] == "2д")
    draft = parse_sheet(
        number="2д",
        title=seed_sheet["title"],
        ord=seed_sheet["ord"],
        layout=seed_sheet.get("layout", "old"),
        lines=_lines_for_seed_sheet(seed_sheet),
        has_header=False,
    )
    repaired = [p for p in draft.problems if p.repaired_from]
    assert len(repaired) == 1
    assert repaired[0].repaired_from == "12д"
    assert repaired[0].label == "12г"


def test_kind_hint_is_a_cross_check_and_disagreement_raises():
    """The kind comes from the glyphs; the hint may only agree with them.

    This test replaces one that asserted the opposite -- that a ``kind_hint``
    from the layout OUTRANKED the taught list, and so decided the kind for
    every label with no kind-bearing glyph.  The §3 verifier showed what that
    precedence bought: the reconciliation fed the seed's own ``kind`` column
    back in as the hint, and 288 of the seed's 544 rows carry no glyph, so on
    those rows the assertion compared the answer with itself.  Strip the hint
    and the parser was wrong on 178 of 544 rows.

    The law that replaced it is a MEASUREMENT over the whole oracle, not a
    preference: across all 544 rows the modifier run fixes the kind with zero
    ambiguity.  So the parser reads the glyphs, and a hint that disagrees with
    them is an ambiguity it refuses out loud instead of resolving behind the
    senior's back.
    """
    draft = parse_sheet(
        number="test",
        title="тест",
        ord=1,
        layout="old",
        lines=[
            ListokLine(text="1а", kind_hint="обычная"),  # agrees
            ListokLine(text="1а°", kind_hint="обязательная"),  # agrees
            ListokLine(text="1б", kind_hint=""),  # no hint at all
        ],
    )
    assert draft.problems[0].kind == "обычная"
    assert draft.problems[1].kind == "обязательная"
    # No glyph, no hint: обычная.  The taught list no longer votes on kind --
    # ``1б`` appears in the seed only as ``1б°``, and a bare ``1б`` really is
    # an ordinary problem.
    assert draft.problems[2].kind == "обычная"

    # A hint that contradicts the glyph is refused, in both directions.
    with pytest.raises(UnknownLabelShape) as info:
        parse_sheet(
            number="test", title="тест", ord=1, layout="old",
            lines=[ListokLine(text="1а°", kind_hint="обычная")],
        )
    assert "1а°" in str(info.value)

    with pytest.raises(UnknownLabelShape):
        parse_sheet(
            number="test", title="тест", ord=1, layout="old",
            lines=[ListokLine(text="1а", kind_hint="звезда")],
        )


def test_taught_list_is_not_switched_off_by_a_modifier():
    """An untaught base raises even when it carries a glyph or a hint.

    The strictness gate used to stand down whenever the label bore any
    modifier or the caller passed any hint, which is to say on nearly every
    real line.  The verifier walked in with ``99*``, ``777°`` and
    ``12345ж**`` and the parser -- taught only last year's 136 bases --
    accepted all three.  A gate ordinary input switches off is not a gate.
    """
    for text, hint in (
        ("999", ""),
        ("999*", ""),
        ("999°", ""),
        ("999ж**", ""),
        ("999", "обычная"),
    ):
        with pytest.raises(UnknownLabelShape) as info:
            parse_sheet(
                number="test", title="тест", ord=1, layout="old",
                lines=[ListokLine(text=text, kind_hint=hint)],
            )
        assert "999" in str(info.value), (
            "отказ обязан назвать метку %r; получено %s" % (text, info.value)
        )


def test_a_blank_cell_costs_no_ordinal():
    """``ord`` counts problems, not spreadsheet rows.

    A listok with a blank cell in the middle used to come out numbered
    1, 3, 4 -- the parser took ``ord`` from the line index and the skipped
    row kept its number.  The seed hides this (every seed label is
    non-empty); a real listok, which is what this parser is for, does not.
    """
    draft = parse_sheet(
        number="test",
        title="тест",
        ord=1,
        layout="old",
        lines=[
            ListokLine(text="1", kind_hint=""),
            ListokLine(text="   ", kind_hint=""),
            ListokLine(text="2а", kind_hint=""),
        ],
    )
    assert [(p.label, p.ord) for p in draft.problems] == [("1", 1), ("2а", 2)]


def test_the_latin_a_fold_is_reported_not_silent():
    """Sheet 7 carries ``2°a`` with a LATIN ``a``; the fold must be visible.

    The module promised in its own docstring that the fold is reported
    through ``repaired_from``; it was not, and the §3 verifier found the row
    by feeding all 544 seed rows through the parser -- ``2°a`` came back as
    ``2°а`` with ``repaired_from=''``.  A rewrite the caller is never told
    about is a silent rewrite, whatever the docstring says.
    """
    draft = parse_sheet(
        number="test",
        title="тест",
        ord=1,
        layout="old",
        lines=[ListokLine(text="2°a", kind_hint="обязательная")],
    )
    problem = draft.problems[0]
    assert problem.label == "2°а", "латинская a должна свернуться в русскую"
    assert problem.repaired_from == "2°a", (
        "свёртка обязана быть названа в repaired_from; получено %r"
        % problem.repaired_from
    )
    assert problem.kind == "обязательная"


def test_no_header_sheet_refused_unless_listed(in_memory_writer):
    """Sheets without a header must be in NO_HEADER_SHEETS, otherwise refuse.

    The parser does not guess.  A senior who forgets to declare ``has_header``
    for a fresh listok without a header row would otherwise get a clean pass
    that drops every problem -- the failure mode the readiness criterion
    forbids.
    """
    with pytest.raises(ValueError):
        parse_sheet(
            number="3",  # not in NO_HEADER_SHEETS
            title="тест",
            ord=1,
            layout="old",
            lines=[ListokLine(text="1", kind_hint="")],
            has_header=False,
        )

    # And the other direction, which used not to be checked at all: a listok
    # this module KNOWS is header-less, declared with a header.  One of the
    # two sides is wrong and the parser refuses to pick which.
    with pytest.raises(ValueError):
        parse_sheet(
            number="1д",  # in NO_HEADER_SHEETS
            title="тест",
            ord=1,
            layout="old",
            lines=[ListokLine(text="1", kind_hint="")],
            has_header=True,
        )


def test_modifier_double_star_wins_over_single_star():
    """``**`` is double; a single ``*`` is starred.  Order in the run is
    irrelevant.

    A senior may put the stars in any order; the parser collapses both to
    ``двойная``.  This is a property of the modifier grammar, not of the
    listok.
    """
    draft = parse_sheet(
        number="test",
        title="тест",
        ord=1,
        layout="old",
        lines=[ListokLine(text="16**", kind_hint="")],
    )
    assert draft.problems[0].kind == "двойная"

    # And the starred case is still starred, not double.
    draft = parse_sheet(
        number="test",
        title="тест",
        ord=2,
        layout="old",
        lines=[ListokLine(text="16*", kind_hint="")],
    )
    assert draft.problems[0].kind == "звезда"


def test_two_real_sheets_kinds_match_seed_counts():
    """The kind counts of three real listki must match the seed's counts.

    The kind-distribution rule of the project: ``обязательная`` and
    ``обычная`` are the bulk, ``звезда`` is the invitation, ``двойная`` is
    rare.  Parsing that produces a different distribution is parsing wrong.
    """
    from collections import Counter
    for number in ("1", "2д", "4д"):
        seed_sheet = next(s for s in _seed_sheets() if s["number"] == number)
        draft = parse_sheet(
            number=number,
            title=seed_sheet["title"],
            ord=seed_sheet["ord"],
            layout=seed_sheet.get("layout", "old"),
            lines=_lines_for_seed_sheet(seed_sheet),
            has_header=(number not in {"1д", "2д"}),
        )
        seed_kinds = Counter(t["kind"] for t in seed_sheet["tasks"])
        draft_kinds = Counter(p.kind for p in draft.problems)
        assert seed_kinds == draft_kinds, (
            "раскладка %r: типы разошлись; seed=%s draft=%s"
            % (number, dict(seed_kinds), dict(draft_kinds))
        )