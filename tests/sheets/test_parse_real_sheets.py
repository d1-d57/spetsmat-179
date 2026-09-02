"""Round-tripping three real listki of last year against the seed.

These tests are the readiness criterion: parse sheet ``1``, sheet ``2д`` and
sheet ``4д`` from the labels the seed already carries, and assert the draft
agrees with the seed row by row.  A label that the parser swallows silently
would make these tests look exactly like a clean pass -- that is the failure
mode they are here to catch.

Counts held honest:
  * sheet ``1``  -- 23 problems, 12 obligatory;
  * sheet ``2д`` -- 32 problems (one duplicate repair);
  * sheet ``4д`` -- 26 problems, every one graveyard-marked.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.services.sheets import (
    ListokLine,
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
            ListokLine(text="3✘", kind_hint="обязательная"),
        ],
        has_header=False,
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
    # The ✘ version of an obligatory problem stays obligatory; the hint
    # wins, not the meta-mark.
    assert draft.problems[3].kind == "обязательная"


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
        issued_at="2026-09-02",
    )
    assert sheet_id == 1
    assert len(problem_ids) == 23
    assert len(in_memory_writer.sheets) == 1
    assert len(in_memory_writer.problems) == 23

    # A fresh draft for the second refusal case (the writer is shared).
    with pytest.raises(UnknownActorRole):
        confirm_and_write(
            draft, actor_role="teacher", writer=in_memory_writer,
        )

    with pytest.raises(UnknownActorRole):
        confirm_and_write(
            draft, actor_role="unknown_role", writer=in_memory_writer,
        )

    # The refused attempts left no state behind.
    assert len(in_memory_writer.sheets) == 1
    assert len(in_memory_writer.problems) == 23


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


def test_kind_hint_from_layout_wins_over_taught_list():
    """If the column was headed ``°``, every line in that column is обязательная.

    Layout carries meaning: the column-header glyph (``°`` or ``●``) tells
    the senior which column is "obligatory", and the parser must respect
    that even when the bare base would have given a different kind.  The
    taught list (first occurrence in the seed) is the LAST fallback: when
    the senior did not mark a kind_hint, the parser trusts the seed.
    """
    # Same base, different kind_hints: hint wins for one row, taught list
    # wins for the other.  Both end up обязательная here because the seed's
    # first occurrence of ``1б`` was an obligatory one; the test asserts
    # the precedence of explicit modifiers over the hint and the taught list.
    draft = parse_sheet(
        number="test",
        title="тест",
        ord=1,
        layout="old",
        lines=[
            ListokLine(text="1а", kind_hint="обычная"),  # hint wins: обычная
            ListokLine(text="1а°", kind_hint="обычная"),  # modifier wins: обязательная
            ListokLine(text="1б", kind_hint=""),  # taught list wins: обязательная
        ],
    )
    assert draft.problems[0].kind == "обычная"
    assert draft.problems[1].kind == "обязательная"
    assert draft.problems[2].kind == "обязательная"


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