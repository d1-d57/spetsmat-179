"""The pure renderers, walked over the whole seed with no database and no event loop.

Two questions are asked here and nowhere else, because they are properties of the TEXT
rather than of a handler:

* does every payload these screens build fit Telegram's 64 bytes, over all eighteen sheets
  and all 544 problems -- and over the widest student id the seed has;
* does the whole-class table fit in one Telegram message, and does it SAY SO when it
  cannot rather than losing its tail in silence.
"""

from __future__ import annotations

from dataclasses import replace

import config
from bot.callbacks import payload_fits
from bot.keyboards.views import (
    MESSAGE_LIMIT_CHARS,
    TABLE_SURNAME_WIDTH,
    ViewDebts,
    ViewLists,
    ViewSheet,
    ViewTable,
    ViewYear,
    debts_text,
    lists_text,
    own_sheet_text,
    table_text,
    year_keyboard,
    year_text,
)
from core.models import CellState
from core.services.spiski import DebtGroup, DebtList, GraveyardList, SilentList


def _payloads(markup):
    return [
        button.callback_data
        for row in markup.inline_keyboard
        for button in row
        if button.callback_data is not None
    ]


# -------------------------------------------------------------------------- payloads

def test_every_payload_of_every_seed_sheet_fits_telegram(spiski, seeded_catalogue, capsys):
    """The 64-byte law, over the whole seed rather than over one hand-picked sheet."""
    students = seeded_catalogue.students()
    checked = 0
    for student in students:
        for sheet in seeded_catalogue.sheets():
            for payload in (
                ViewYear(student_id=student.id).pack(),
                ViewSheet(student_id=student.id, sheet_id=sheet.id).pack(),
                ViewDebts(student_id=student.id).pack(),
                ViewTable(sheet_id=sheet.id).pack(),
                ViewLists().pack(),
            ):
                assert payload_fits(payload), "payload over the limit: %r" % payload
                checked += 1
    assert checked == len(students) * len(seeded_catalogue.sheets()) * 5
    with capsys.disabled():
        print(
            "\n[просмотр] payload'ов проверено %d · учеников %d из 56 · листков %d из 18 "
            "· превышений 64 байт: 0" % (checked, len(students), len(seeded_catalogue.sheets()))
        )


def test_the_year_keyboard_is_the_grid_width_and_carries_the_way_to_the_debts(
    spiski, seeded_catalogue
):
    student = seeded_catalogue.students()[0]
    rows = spiski.year(student.id)
    markup = year_keyboard(rows, student_id=student.id)

    sheet_rows = markup.inline_keyboard[:-1]
    assert all(len(row) <= config.GRID_COLUMNS for row in sheet_rows)
    assert sum(len(row) for row in sheet_rows) == 18
    assert _payloads(markup)[-1] == ViewDebts(student_id=student.id).pack()


# ---------------------------------------------------------------------------- text

def test_the_year_names_every_sheet_including_the_empty_ones(spiski, seeded_catalogue):
    student = seeded_catalogue.students()[0]
    text = year_text(student, spiski.year(student.id))
    for sheet in seeded_catalogue.sheets():
        assert "Листок %s ·" % sheet.number in text
    assert text.count("сдано") == 18


def test_a_clear_debt_list_says_so_instead_of_printing_nothing(seeded_catalogue):
    student = seeded_catalogue.students()[0]
    text = debts_text(student, DebtList())
    assert "обязательных долгов нет" in text


def test_the_debt_list_names_one_boundary_and_collapses_the_rest(spiski, seeded_catalogue):
    """«обязательные из листка 6: №4, №11» plus one line for everything older.

    The collapsed line must NOT enumerate: a long list of what you owe is a message about
    the person, and this screen is deliberately a message about a task.
    """
    student = seeded_catalogue.students()[0]
    debts = spiski.debts(student.id)
    text = debts_text(student, debts)

    assert "обязательные из листка" in text
    assert "и ещё %d с более ранних листков" % debts.older_problems in text
    assert "прийти и сдать можно в любой момент" in text, "the door stays open, in words"

    enumerated = sum(len(group.problems) for group in debts.near)
    assert text.count(",") < enumerated + debts.older_problems, (
        "the older debts must be collapsed, not listed"
    )


def test_the_own_sheet_states_the_fact_and_not_a_judgement(spiski, seeded_catalogue, mark_on):
    student = seeded_catalogue.students()[0]
    sheet = sorted(seeded_catalogue.sheets(), key=lambda s: s.ord)[0]
    problems, states = spiski.sheet_states(student.id, sheet.id)
    states = dict(states)
    states[problems[0].id] = CellState.SOLVED
    states[problems[1].id] = CellState.RETRACTED

    text = own_sheet_text(student, sheet, problems, states)
    assert "%s — принята" % problems[0].label in text
    assert "%s — сдана, не защищена" % problems[1].label in text
    assert "%s — —" % problems[2].label in text
    assert "сдано 1 из %d" % len(problems) in text


def test_the_two_lists_carry_their_own_coverage(spiski, seeded_catalogue, mark_on):
    """«молчат трое» and «молчат 3 из 56 за 3 занятия» are not the same fact."""
    students = seeded_catalogue.students()
    for index, day in enumerate(("2026-09-08", "2026-09-15", "2026-09-22")):
        problems = seeded_catalogue.problems_of_sheet(seeded_catalogue.sheets()[0].id)
        mark_on(students[0].id, problems[index].id, day)

    text = lists_text(spiski.silent(), spiski.graveyard())
    assert "Не сдавал ничего %d занятия подряд" % config.SILENT_SESSIONS in text
    assert "всего 55 из 56" in text
    assert "Задачи, которые не взял почти никто" in text
    assert "учеников 56" in text
    assert text.index("Не сдавал") < text.index("Задачи, которые"), (
        "the silent list comes first: it is the one that fixes defect no. 7"
    )


def test_not_enough_lesson_days_is_not_reported_as_everybody_is_fine(spiski):
    text = lists_text(SilentList(considered=56, enough_days=False), GraveyardList(considered=56))
    assert "считать не из чего" in text
    assert "учеников 56" in text


# --------------------------------------------------------------------------- table

def test_the_whole_class_table_fits_one_telegram_message_on_every_seed_sheet(
    spiski, seeded_catalogue, capsys
):
    """Fifty-six students against up to forty-four problems, eighteen times over."""
    widest = 0
    for sheet in seeded_catalogue.sheets():
        problems, students, states = spiski.sheet_table(sheet.id)
        text = table_text(sheet, problems, students, states)
        assert len(text) <= MESSAGE_LIMIT_CHARS, (
            "sheet %s renders %d characters, over Telegram's %d"
            % (sheet.number, len(text), MESSAGE_LIMIT_CHARS)
        )
        assert text.startswith("<pre>") and text.endswith("</pre>")
        widest = max(widest, len(text))
    with capsys.disabled():
        print(
            "\n[таблица] листков 18 из 18 · самая длинная %d символов из %d · обрезаний 0"
            % (widest, MESSAGE_LIMIT_CHARS)
        )


def test_a_table_that_does_not_fit_says_how_many_rows_it_dropped(spiski, seeded_catalogue):
    """A table that silently lost its tail would look complete, which is worse than short."""
    sheet = max(seeded_catalogue.sheets(), key=lambda s: len(seeded_catalogue.problems_of_sheet(s.id)))
    problems, students, states = spiski.sheet_table(sheet.id)
    # Ten times the roster, with the same states: the cut is a property of the length.
    many = [replace(student, id=student.id) for student in students] * 10

    text = table_text(sheet, problems, many, states)
    assert len(text) <= MESSAGE_LIMIT_CHARS
    assert "показано" in text and "из %d учеников" % len(many) in text


def test_a_surname_wider_than_the_column_is_cut_and_the_table_stays_square(
    spiski, seeded_catalogue
):
    sheet = sorted(seeded_catalogue.sheets(), key=lambda s: s.ord)[0]
    problems, students, states = spiski.sheet_table(sheet.id)
    long_name = replace(students[0], surname="Длиннофамильевская")
    text = table_text(sheet, problems, [long_name] + list(students[1:]), states)

    body = text[len("<pre>") : -len("</pre>")].split("\n")[3:]
    widths = {len(line) for line in body if line and not line.startswith("показано")}
    assert len(widths) == 1, "every row of the table is the same width: %r" % sorted(widths)
    assert "…" in body[0]
    assert len(body[0].split(" ")[0]) <= TABLE_SURNAME_WIDTH
