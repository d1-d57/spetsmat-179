"""The reconciliation the readiness criterion asks for: a COUNT, printed.

``test_parse_real_sheets.py`` already asserts, sheet by sheet, that the draft
agrees with ``seed/sheets.json``.  It is silent, and that is the hole this file
closes: a silent green pass reads identically whether it compared eighty-one
problems or zero.  «сверено 0 задач из 81» and «сверено 81 задач из 81» are the
same green dot in ``pytest -q``, and the first of the two is the exact defect
this wave has already paid for once -- a parser that quietly compares nothing.

So this test:

  * parses the three real listki of last year (``1``, ``2д``, ``4д``) from the
    labels the seed carries, field by field against the seed;
  * counts what it compared and what disagreed;
  * PRINTS «сверено N задач из M, расхождений 0» through ``capsys.disabled()``,
    so the number survives ``pytest -q`` and lands in the log a human reads;
  * goes RED when N is zero on a non-empty source.

M is read off the seed on disk, never hard-coded: a hard-coded 81 would stay
green on a seed that had lost half its rows, which is the failure the count is
supposed to catch in the first place.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.services.sheets import NO_HEADER_SHEETS, ListokLine, parse_sheet


#: The three real listki of last year the readiness criterion names.  ``1`` is
#: the canonical layout, ``2д`` carries the ``12д`` duplicate repair P2 paid
#: for, ``4д`` is the sheet the seed stores without a header row.
SHEET_NUMBERS = ("1", "2д", "4д")

#: What the wave measured about this oracle before this заход existed, and what
#: an oracle that quietly lost rows would no longer satisfy.  ``compared ==
#: total`` alone cannot see that: both sides are read off the same file, so a
#: seed short of half its rows passes green and merely prints a smaller number.
#: These four numbers come from P2's inventory, are quoted in the задание, and
#: are the only hard-coded counts in this file -- deliberately, because their
#: whole job is to be independent of the file they check.
SEED_SHEET_COUNT = 18
SEED_PROBLEM_COUNT = 544
SEED_KIND_COUNTS = {
    "обязательная": 215,
    "обычная": 288,
    "звезда": 39,
    "двойная": 2,
}


def _seed_sheets():
    return json.loads(Path("seed/sheets.json").read_text(encoding="utf-8"))


def _reconcile(seed_sheet):
    """Parse one seed sheet WITHOUT telling the parser the answer, and diff it.

    ``kind_hint`` is deliberately NOT passed.  Handing the seed's own ``kind``
    column to the parser is what made the first version of this file a
    tautology: 288 of the seed's 544 rows carry no kind-bearing glyph, so on
    those rows ``problem.kind == seed_task["kind"]`` compared the hint with
    itself and could not go red.  The §3 verifier measured the difference --
    stripped of the hint the parser was wrong on 178 of 544 rows -- and the
    parser was fixed to read the kind off the glyphs.  This function is what
    keeps it honest: the parser is told the labels and nothing else.

    Returns ``(compared, [discrepancy, ...])``.
    """
    number = seed_sheet["number"]
    seed_tasks = seed_sheet["tasks"]
    draft = parse_sheet(
        number=number,
        title=seed_sheet["title"],
        ord=seed_sheet["ord"],
        layout=seed_sheet.get("layout", "old"),
        lines=[ListokLine(text=task["label"]) for task in seed_tasks],
        has_header=(number not in NO_HEADER_SHEETS),
    )

    compared = 0
    bad: list = []
    if len(draft.problems) != len(seed_tasks):
        bad.append(
            "листок %s: задач в черновике %d, в seed %d"
            % (number, len(draft.problems), len(seed_tasks))
        )

    for index, seed_task in enumerate(seed_tasks):
        if index >= len(draft.problems):
            bad.append(
                "листок %s, задача %d (%s): в черновике её нет"
                % (number, index + 1, seed_task["label"])
            )
            continue
        problem = draft.problems[index]
        compared += 1

        # Every rewrite the parser performed -- the ``12д`` duplicate repair
        # and the Latin-``a`` fold alike -- has to be reported in
        # ``repaired_from``, and that report is what reconciles against the
        # seed.  A rewrite the parser did NOT report shows up here as a
        # mismatched label, which is exactly what should happen.
        written_label = problem.repaired_from or problem.label
        if written_label != seed_task["label"]:
            bad.append(
                "листок %s, задача %d: метка seed %r, черновик %r"
                % (number, index + 1, seed_task["label"], written_label)
            )
        if problem.kind != seed_task["kind"]:
            bad.append(
                "листок %s, задача %s: тип seed %r, черновик %r"
                % (number, seed_task["label"], seed_task["kind"], problem.kind)
            )
        if problem.ord != seed_task["ord"]:
            bad.append(
                "листок %s, задача %s: ord seed %d, черновик %d"
                % (number, seed_task["label"], seed_task["ord"], problem.ord)
            )
    return compared, bad


def test_the_seed_is_still_the_oracle_the_wave_measured(capsys):
    """The oracle itself is checked, because ``compared == total`` cannot.

    Both sides of that equality are read off ``seed/sheets.json``, so a seed
    that lost half its rows keeps the reconciliation green and only prints a
    smaller number.  The four counts asserted here were measured by P2 against
    seven oracles and are quoted in the задание; they are hard-coded on
    purpose, since a count that came out of the file it checks proves nothing.
    """
    from collections import Counter

    seed_sheets = _seed_sheets()
    kinds = Counter(t["kind"] for s in seed_sheets for t in s["tasks"])
    rows = sum(len(s["tasks"]) for s in seed_sheets)

    with capsys.disabled():
        print(
            "\n[оракул] листков %d, задач %d, типы %s"
            % (len(seed_sheets), rows, dict(sorted(kinds.items())))
        )

    assert len(seed_sheets) == SEED_SHEET_COUNT, (
        "листков в оракуле %d, измерено было %d — оракул изменился"
        % (len(seed_sheets), SEED_SHEET_COUNT)
    )
    assert rows == SEED_PROBLEM_COUNT, (
        "задач в оракуле %d, измерено было %d — оракул изменился"
        % (rows, SEED_PROBLEM_COUNT)
    )
    assert dict(kinds) == SEED_KIND_COUNTS, (
        "распределение типов в оракуле %s, измерено было %s"
        % (dict(kinds), SEED_KIND_COUNTS)
    )


def test_three_real_sheets_reconcile_against_seed_with_a_printed_count(capsys):
    """Compare three real listki against the seed and print the coverage.

    The comparison is field by field -- label, kind, ord -- because a draft
    that recovered every label but shifted every ``ord`` by one would pass a
    set comparison and produce a sheet nobody can hand out.

    One row disagrees LEGITIMATELY: sheet ``2д`` carries ``12д`` twice, and
    ``DUPLICATE_LABEL_REPAIRS`` renames the first occurrence to ``12г``.  That
    row is reconciled against ``repaired_from`` -- the parser is required to
    report what it rewrote, so the repair is visible in the count rather than
    hidden by it.
    """
    seed_sheets = _seed_sheets()

    compared = 0
    total = 0
    mismatches: list = []
    for number in SHEET_NUMBERS:
        seed_sheet = next(s for s in seed_sheets if s["number"] == number)
        total += len(seed_sheet["tasks"])
        sheet_compared, sheet_bad = _reconcile(seed_sheet)
        compared += sheet_compared
        mismatches.extend(sheet_bad)

    # Coverage is printed, not merely asserted: a negative verdict that does
    # not carry its own coverage is unreadable -- "расхождений 0, сверено 2"
    # and "расхождений 0, сверено 81" look the same without the number.
    with capsys.disabled():
        print(
            "\n[сверка листков] сверено %d задач из %d, расхождений %d"
            % (compared, total, len(mismatches))
        )

    # A non-empty source that yielded nothing to compare is RED, never green:
    # that is the shape of every silent-skip defect this parser exists to
    # refuse.
    assert total > 0, "seed/sheets.json пуст — сверять нечего, и это не зелёное"
    assert compared > 0, (
        "источник непустой (%d задач), а сверено 0 — это КРАСНЫЙ" % total
    )
    assert compared == total, (
        "сверено %d задач из %d — часть листка не дошла до сверки"
        % (compared, total)
    )
    assert not mismatches, "расхождений %d:\n%s" % (
        len(mismatches), "\n".join(mismatches),
    )


def test_every_sheet_in_the_oracle_reconciles_with_a_printed_count(capsys):
    """The same reconciliation, widened from three listki to all eighteen.

    Three sheets are what the readiness criterion demands and what the test
    above prints.  All eighteen are what the §3 verifier ran, and it is how
    the one silent rewrite in the whole corpus was found: sheet 7's ``2°a``,
    a single row out of 544, invisible to any sample that did not include
    sheet 7.  A sample chosen before the defect is known cannot be trusted to
    contain it, so the widened pass stays.
    """
    seed_sheets = _seed_sheets()

    compared = 0
    total = 0
    mismatches: list = []
    for seed_sheet in seed_sheets:
        total += len(seed_sheet["tasks"])
        sheet_compared, sheet_bad = _reconcile(seed_sheet)
        compared += sheet_compared
        mismatches.extend(sheet_bad)

    with capsys.disabled():
        print(
            "\n[сверка всех листков] сверено %d задач из %d, расхождений %d"
            % (compared, total, len(mismatches))
        )

    assert total > 0, "seed/sheets.json пуст — сверять нечего, и это не зелёное"
    assert compared > 0, (
        "источник непустой (%d задач), а сверено 0 — это КРАСНЫЙ" % total
    )
    assert compared == total, (
        "сверено %d задач из %d — часть корпуса не дошла до сверки"
        % (compared, total)
    )
    assert not mismatches, "расхождений %d:\n%s" % (
        len(mismatches), "\n".join(mismatches),
    )
