"""The layout, over the WHOLE seed and not over a sample.

A negative verdict here carries its own coverage: «превышений 0, проверено 544 из 544»
and «превышений не найдено» read identically to a reader and mean completely different
things.  Zero buttons checked against a non-empty seed is RED, not green, so the counts
are asserted before they are printed.

Three properties, each of which has a way of being wrong that nobody notices by eye:

  * a row that is not ``config.GRID_COLUMNS`` wide -- Telegram stretches it, and the last
    row of a 23-problem sheet ends up visibly wider than the twenty buttons above it;
  * a payload over 64 BYTES -- the Bot API refuses the whole message, and a Cyrillic
    character costs two of them, so a check on characters would pass while production
    fails;
  * a payload built from a human-typed label -- ``seed/sheets.json`` really contains
    ``10а:)``, and ``:`` is the separator ``CallbackData`` packs with.
"""

from __future__ import annotations

import config
from bot.callbacks import CALLBACK_DATA_LIMIT_BYTES, Mark, Noop
from bot.keyboards.grid import grid_keyboard, sheets_keyboard
from core.models import CellState, Student

#: A student whose grid is drawn.  Nothing about the layout depends on which one, and an
#: id far larger than any real one keeps the byte count honest rather than optimistic.
STUDENT = Student(id=999999, surname="Петров", name="Василий")


def _grid_rows(markup) -> list:
    """The PROBLEM rows: everything above the navigation footer and the «Готово» row.

    The footer is allowed to be narrower -- «← Иванов · Другой листок · Сидорова →» is
    three buttons by design -- and counting it as a grid row would make the four-column
    check fail on every screen and therefore mean nothing.
    """
    return markup.inline_keyboard[:-2]


def test_every_seed_sheet_lays_out_four_wide_and_inside_the_byte_limit(
    seeded_catalogue, capsys
):
    sheets = seeded_catalogue.sheets()
    assert sheets, "the seeded catalogue has no sheets: a green run here would prove nothing"

    buttons_checked = 0
    problem_buttons_checked = 0
    over_limit = []
    rows_not_full = []
    fillers = 0

    for sheet in sheets:
        problems = seeded_catalogue.problems_of_sheet(sheet.id)
        assert problems, "sheet %s has no problems" % sheet.number

        # Half the cells solved, alternating, so BOTH branches of the cell button --
        # "offer to clear" and "offer to solve" -- are packed on every sheet.
        states = {
            problem.id: (CellState.SOLVED if index % 2 else CellState.EMPTY)
            for index, problem in enumerate(problems)
        }
        markup = grid_keyboard(
            problems,
            states,
            student_id=STUDENT.id,
            sheet_id=sheet.id,
            previous_student=STUDENT,
            next_student=STUDENT,
        )

        for row in _grid_rows(markup):
            if len(row) != config.GRID_COLUMNS:
                rows_not_full.append((sheet.number, len(row)))
            for button in row:
                buttons_checked += 1
                if len(button.callback_data.encode("utf-8")) > CALLBACK_DATA_LIMIT_BYTES:
                    over_limit.append((sheet.number, button.text, button.callback_data))
                if button.callback_data == Noop().pack():
                    fillers += 1
                else:
                    problem_buttons_checked += 1
                    # Nothing but numbers: unpacking as ``Mark`` is what proves it, since
                    # a label smuggled into the payload would either break the field count
                    # or fail the integer coercion.
                    parsed = Mark.unpack(button.callback_data)
                    assert parsed.student_id == STUDENT.id
                    assert parsed.op in (0, 1)

        # Every button of the footer too: the navigation payloads carry ids as well, and
        # a sheet id that pushed one of them over the limit would break the same message.
        for row in markup.inline_keyboard[-2:]:
            for button in row:
                buttons_checked += 1
                if len(button.callback_data.encode("utf-8")) > CALLBACK_DATA_LIMIT_BYTES:
                    over_limit.append((sheet.number, button.text, button.callback_data))

    total_problems = sum(
        len(seeded_catalogue.problems_of_sheet(sheet.id)) for sheet in sheets
    )
    assert problem_buttons_checked == total_problems == 544, (
        "checked %d problem buttons against %d problems in the catalogue"
        % (problem_buttons_checked, total_problems)
    )
    assert not over_limit, "payloads over %d bytes: %r" % (
        CALLBACK_DATA_LIMIT_BYTES,
        over_limit[:5],
    )
    assert not rows_not_full, "rows not %d wide: %r" % (config.GRID_COLUMNS, rows_not_full)

    with capsys.disabled():
        print(
            "\n[раскладка] листков %d из %d · проверено кнопок задач %d из %d · "
            "всего кнопок проверено %d (из них заполнителей %d) · "
            "превышений %d байт: %d · рядов не по %d: %d"
            % (
                len(sheets), 18,
                problem_buttons_checked, total_problems,
                buttons_checked, fillers,
                CALLBACK_DATA_LIMIT_BYTES, len(over_limit),
                config.GRID_COLUMNS, len(rows_not_full),
            )
        )


def test_a_label_carrying_the_separator_never_reaches_the_payload(seeded_catalogue):
    """The concrete case, named, so that it fails loudly if anyone «simplifies» the
    payload back into a readable string.

    ``seed/sheets.json`` contains the problem label ``10а:)``.  Packing it into
    ``callback_data`` would raise ``ValueError`` from ``CallbackData.pack`` -- for exactly
    one sheet out of eighteen, in production, at the moment a teacher opens it.
    """
    labels = [
        problem.label
        for sheet in seeded_catalogue.sheets()
        for problem in seeded_catalogue.problems_of_sheet(sheet.id)
    ]
    with_separator = [label for label in labels if ":" in label]
    assert with_separator, (
        "the seed no longer contains a label with a ':' -- this test guarded a real case "
        "and now guards nothing; either restore the case or delete the test knowingly"
    )

    for sheet in seeded_catalogue.sheets():
        problems = seeded_catalogue.problems_of_sheet(sheet.id)
        markup = grid_keyboard(
            problems, {}, student_id=STUDENT.id, sheet_id=sheet.id
        )
        for row in _grid_rows(markup):
            for button in row:
                assert ":)" not in button.callback_data
                for label in with_separator:
                    assert label not in button.callback_data


def test_the_order_of_cells_does_not_depend_on_what_is_solved(seeded_catalogue):
    """The grid is FIXED for the whole lesson.

    Solved problems do not disappear, do not shrink and do not re-sort.  The test builds
    the same sheet twice -- once untouched, once with everything solved -- and compares
    the payloads cell by cell: the TEXT changes, the position does not.
    """
    sheet = seeded_catalogue.sheets()[6]
    problems = seeded_catalogue.problems_of_sheet(sheet.id)

    empty = grid_keyboard(problems, {}, student_id=STUDENT.id, sheet_id=sheet.id)
    solved = grid_keyboard(
        problems,
        {problem.id: CellState.SOLVED for problem in problems},
        student_id=STUDENT.id,
        sheet_id=sheet.id,
    )

    def task_ids(markup):
        return [
            Mark.unpack(button.callback_data).task_id
            for row in _grid_rows(markup)
            for button in row
            if button.callback_data != Noop().pack()
        ]

    assert task_ids(empty) == task_ids(solved) == [problem.id for problem in problems]
    assert [len(row) for row in _grid_rows(empty)] == [len(row) for row in _grid_rows(solved)]


def test_five_columns_would_break_the_thumb_target_so_the_constant_is_the_source(
    seeded_catalogue,
):
    """``config.GRID_COLUMNS`` is what drives the shape -- not a literal 4 in the builder.

    Proved by asking for a different width and getting it: a hardcoded 4 would ignore the
    argument and keep returning rows of four.  ``config.GRID_COLUMNS`` stays 4 in
    production for a measured reason (9.2-9.6 mm thumb target); this test is about WHERE
    the number comes from, not about changing it.
    """
    sheet = seeded_catalogue.sheets()[0]
    problems = seeded_catalogue.problems_of_sheet(sheet.id)

    assert config.GRID_COLUMNS == 4
    for width in (2, 3, 5):
        markup = grid_keyboard(
            problems, {}, student_id=STUDENT.id, sheet_id=sheet.id, columns=width
        )
        assert {len(row) for row in _grid_rows(markup)} == {width}


def test_the_sheet_chooser_is_one_tap_deep_and_fits_the_limit(seeded_catalogue):
    """«Другой листок» offers every sheet at once: an extra LEVEL of navigation costs a
    full cycle of the five-to-fifteen-second seam, while more buttons on one screen cost
    a small constant."""
    sheets = seeded_catalogue.sheets()
    markup = sheets_keyboard(sheets, student_id=STUDENT.id)

    offered = [
        button
        for row in markup.inline_keyboard
        for button in row
        if button.callback_data != Noop().pack()
    ]
    assert len(offered) == len(sheets) == 18
    assert {len(row) for row in markup.inline_keyboard} == {config.GRID_COLUMNS}
    for button in offered:
        assert len(button.callback_data.encode("utf-8")) <= CALLBACK_DATA_LIMIT_BYTES
