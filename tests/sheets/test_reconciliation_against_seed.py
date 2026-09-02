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

from core.services.sheets import ListokLine, parse_sheet


#: The three real listki of last year.  ``1`` is the canonical layout, ``2д``
#: carries the ``12д`` duplicate repair P2 paid for, ``4д`` is the sheet whose
#: every problem is graveyard-marked.
SHEET_NUMBERS = ("1", "2д", "4д")


def _seed_sheets():
    return json.loads(Path("seed/sheets.json").read_text(encoding="utf-8"))


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
        seed_tasks = seed_sheet["tasks"]
        total += len(seed_tasks)

        draft = parse_sheet(
            number=seed_sheet["number"],
            title=seed_sheet["title"],
            ord=seed_sheet["ord"],
            layout=seed_sheet.get("layout", "old"),
            lines=[
                ListokLine(text=task["label"], kind_hint=task["kind"])
                for task in seed_tasks
            ],
            has_header=(number not in {"1д", "2д"}),
        )

        if len(draft.problems) != len(seed_tasks):
            mismatches.append(
                "листок %s: задач в черновике %d, в seed %d"
                % (number, len(draft.problems), len(seed_tasks))
            )

        for index, seed_task in enumerate(seed_tasks):
            if index >= len(draft.problems):
                mismatches.append(
                    "листок %s, задача %d (%s): в черновике её нет"
                    % (number, index + 1, seed_task["label"])
                )
                continue
            problem = draft.problems[index]
            compared += 1

            # A repaired row reports the label the senior actually wrote in
            # ``repaired_from``; that is what reconciles against the seed.
            written_label = problem.repaired_from or problem.label
            if written_label != seed_task["label"]:
                mismatches.append(
                    "листок %s, задача %d: метка seed %r, черновик %r"
                    % (number, index + 1, seed_task["label"], written_label)
                )
            if problem.kind != seed_task["kind"]:
                mismatches.append(
                    "листок %s, задача %s: тип seed %r, черновик %r"
                    % (number, seed_task["label"], seed_task["kind"], problem.kind)
                )
            if problem.ord != seed_task["ord"]:
                mismatches.append(
                    "листок %s, задача %s: ord seed %d, черновик %d"
                    % (number, seed_task["label"], seed_task["ord"], problem.ord)
                )

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
