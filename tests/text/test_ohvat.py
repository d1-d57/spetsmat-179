"""ОХВАТ — the whole of a real evening's sheet through the parser, with the number printed.

The готовности criterion of this position asks for a coverage line rather than a pass, and
the reason is stated in the задание in one sentence: **«угаданное считается ОШИБКОЙ, а не
успехом»**.  A parser that resolved three names out of four and shrugged at the fourth
would be green on every test above; what makes it red is counting.

So this file works over a CORPUS written in the owner's real format -- blocks separated by
horizontal rules, about ten problems per child, records that WRAP over several lines -- and
prints how many blocks were read, how many children were resolved, and how many were
guessed.  Guessed means: resolved with a verdict that is not ``certain``.  The number that
must be zero is that one.

⚠ The corpus is the format's stress, not the roster's: every surname in it is a real
surname of ``seed/students.csv``, written the way the owner writes it aloud.
"""

from __future__ import annotations

import pytest

from core.services import bystryj_tekst as tekst
from core.services.golos import Verdict
from tests.text.conftest import OWNER_LINES, OWNER_MESSAGE

#: A sheet as the owner writes it: a name, then about ten problems, wrapping freely.  Each
#: entry is ``(the block as typed, the child it is about, how many problems are in it)``.
#:
#: The wrapping is the point of the corpus and the reason it exists.  §1 rule 1: «перенос
#: строки внутри одного ученика — норма, а не конец блока».  A parser that ended a block at
#: the newline would read every one of these as a child with three problems followed by an
#: unparseable line, and would do it SILENTLY -- half the evening's marks would simply not
#: be there, and nothing would go red.
CORPUS = (
    (
        "Лёня Санин 7, 9а, 11б, 12, 13,\n"
        "15а, 15в, 2б, 4, 6",
        23,
        10,
    ),
    (
        "Катя Долкирева 2а, 2б, 4, 5в, 8, 10а",
        18,
        6,
    ),
    (
        "Аня Бочарова [3д] 5, 12",
        9,
        2,
    ),
    (
        "Влад Быков —",
        11,
        0,
    ),
    (
        "Ира Агаркова 1, 2а, 2в, 3а, 3б,\n"
        "  4, 5а, 5б, 6, 7, 8",
        1,
        11,
    ),
    (
        "Настя Аникина 10а, 10б, 11а,\n"
        "11в, 11г, 12",
        2,
        6,
    ),
    (
        "Вася Бирюков 13, 14, 15а, 15б, 15в",
        6,
        5,
    ),
    (
        "Федя Болотин -",
        7,
        0,
    ),
    (
        "Дима Борисов 2б, 3а, 3б, 4, 5а,\n"
        "5б, 5в, 6, 7, 9",
        8,
        10,
    ),
    (
        "Миша Будылин [2д] 1, 2а, 3б, 4",
        10,
        4,
    ),
)

#: The same corpus as ONE message, the way it is pasted into Telegram: blocks divided by
#: the horizontal rules the paper sheet is divided by.
CORPUS_MESSAGE = "\n---\n".join(block for block, _, _ in CORPUS)


def rows_of(text, students, catalogue):
    return tekst.build_draft(text, students=students, catalogue=catalogue).rows


# =============================================================================
#  THE COVERAGE, PRINTED
# =============================================================================

def test_ohvat_of_the_whole_corpus_with_the_number_printed(students, catalogue, capsys):
    """Every block of the corpus, read in one message, counted out loud.

    Zero blocks read against a non-empty corpus is RED and not green: an exception
    swallowed inside the walk would otherwise leave a green run over an empty result.
    """
    rows = rows_of(CORPUS_MESSAGE, students, catalogue)

    read = len(rows)
    resolved = sum(1 for row in rows if row.student_id is not None)
    guessed = sum(
        1 for row in rows if row.student_id is not None and row.verdict is not Verdict.CERTAIN
    )
    problems = sum(len(row.cells) for row in rows)
    wrong = [
        (block, expected, row.student_id)
        for (block, expected, _), row in zip(CORPUS, rows)
        if row.student_id != expected
    ]

    with capsys.disabled():
        print(
            "\n[текст] разобрано блоков %d из %d · учеников опознано %d · задач %d "
            "· угадано %d" % (read, len(CORPUS), resolved, problems, guessed)
        )

    assert read == len(CORPUS), (
        "%d blocks came back from %d written; a block was lost or split"
        % (read, len(CORPUS))
    )
    assert wrong == [], wrong
    assert guessed == 0, "a child was GUESSED; the задание counts that as an error"


def test_ohvat_every_problem_written_survives_into_a_cell(students, catalogue):
    """The other half of the count: not one label written may quietly disappear.

    Losing a NAME is loud -- the row says «кто это?».  Losing a LABEL is silent: the table
    simply has one fewer button, and the teacher who wrote ten numbers has no way to see
    that nine arrived.
    """
    rows = rows_of(CORPUS_MESSAGE, students, catalogue)
    got = [len(row.cells) for row in rows]
    assert got == [count for _, _, count in CORPUS], got


# =============================================================================
#  RULE 1 -- the divergence that would have cost half of every evening
# =============================================================================

def test_a_record_that_wraps_over_lines_is_ONE_child_and_not_two(students, catalogue):
    """§1 rule 1, stated as its own test because it is the rule that fails invisibly.

    «Блок кончается там, где начинается следующее ИМЯ, а не там, где кончается строка.»
    Ten problems do not fit on a phone line, so the continuation is the ordinary case
    rather than the exception, and a parser that ended the block at the newline would drop
    everything after the first line of every child in the room.
    """
    wrapped = "Лёня Санин 7, 9а, 11б, 12, 13,\n15а, 15в, 2б, 4, 6"
    flat = "Лёня Санин 7, 9а, 11б, 12, 13, 15а, 15в, 2б, 4, 6"

    rows = rows_of(wrapped, students, catalogue)
    assert len(rows) == 1, "the wrap started a second block: %r" % [r.said for r in rows]
    assert rows[0].student_id == 23
    assert [cell.label for cell in rows[0].cells] == [
        cell.label for cell in rows_of(flat, students, catalogue)[0].cells
    ]


def test_a_continuation_line_is_told_apart_from_the_next_childs_name(students, catalogue):
    """Two children, the first of them wrapping.  Three blocks would be a lost child.

    This is the pair the previous test cannot catch on its own: a parser that joined
    EVERYTHING would also pass a single-block test, and would then read the whole evening
    as one enormous record for whoever was written first.
    """
    text = (
        "Лёня Санин 7, 9а, 11б, 12,\n"
        "13, 15а, 15в\n"
        "Катя Долкирева 2а, 2б, 4"
    )
    rows = rows_of(text, students, catalogue)

    assert [row.student_id for row in rows] == [23, 18]
    assert len(rows[0].cells) == 7
    assert len(rows[1].cells) == 3


@pytest.mark.parametrize("rule", ["---", "———", "___", "-----"])
def test_a_horizontal_rule_divides_blocks_and_is_not_a_procherk(rule, students, catalogue):
    """The paper is divided by lines, and a line is not a statement about a child.

    ⚠ A single dash IS the прочерк and means the opposite of nothing, so the two cannot be
    told apart by the character -- only by the length.  Reading a rule as a прочерк would
    invent a явка for whichever child happened to be written above it.
    """
    text = "Катя Долкирева 2а, 2б\n%s\nВлад Быков —" % rule
    rows = rows_of(text, students, catalogue)

    assert [row.student_id for row in rows] == [18, 11]
    assert rows[0].present_no_marks is False, "a horizontal rule became a явка"
    assert rows[1].present_no_marks is True


def test_blank_lines_between_blocks_change_nothing(students, catalogue):
    """A teacher pressing enter twice is not saying anything."""
    spaced = "\n\n".join(line for line, _, _, _ in OWNER_LINES)
    assert [row.student_id for row in rows_of(spaced, students, catalogue)] == [
        student_id for _, student_id, _, _ in OWNER_LINES
    ]


# =============================================================================
#  RULE 2 -- the default sheet is the current one
# =============================================================================

def test_a_block_without_a_bracket_is_about_the_current_sheet(
    students, catalogue, current_sheet
):
    """§1 rule 2: «листок по умолчанию — ТЕКУЩИЙ», and the whole class is the usual case.

    The label `4` exists on nearly every sheet of the year.  Resolving it against the wrong
    one is the quietest possible error: a real problem id, a real child, a plus that lands
    on a листок from last autumn.
    """
    row = rows_of("Катя Долкирева 4", students, catalogue)[0]
    cell = row.cells[0]

    assert cell.problem_id is not None
    assert cell.on_lead_sheet is True
    assert cell.sheet_number == current_sheet.number


def test_the_bracket_moves_only_the_block_it_stands_in(students, catalogue, current_sheet):
    """`[3д]` is a fact about Бочарова's line and about nothing else in the message.

    A sheet marker that leaked forward would silently move every child written below onto
    an old листок -- and the teacher, who wrote the bracket once and on purpose, would have
    no reason to look.
    """
    text = "\n".join(line for line, _, _, _ in OWNER_LINES)
    rows = rows_of(text, students, catalogue)
    by_id = {row.student_id: row for row in rows}

    assert by_id[9].sheet_marker == "3д"
    assert all(cell.sheet_number == "3д" for cell in by_id[9].cells)

    for student_id in (23, 18):
        assert by_id[student_id].sheet_marker is None
        assert not any(cell.sheet_number == "3д" for cell in by_id[student_id].cells), (
            "the bracket of another block leaked into this one"
        )


def test_a_label_the_current_sheet_does_not_have_is_found_but_FLAGGED(
    students, catalogue, current_sheet
):
    """`9а` on a line with no bracket: листок 4д has `9`, and it has no `9а`.

    Found by counting the owner's own first line rather than by invention -- eight of its
    ten labels are on the current sheet and two are not.  Two answers are wrong here.
    Refusing the label loses a mark the teacher really made; taking it silently puts a plus
    on a листок from another month.  So it resolves AND says which sheet it resolved on,
    and the screen prints that sheet on the button.  The teacher decides; the parser does
    not.
    """
    row = rows_of(OWNER_LINES[0][0], students, catalogue)[0]
    elsewhere = [cell for cell in row.cells if not cell.on_lead_sheet]

    assert elsewhere, "the whole line fell on the current sheet; this test proves nothing"
    for cell in elsewhere:
        assert cell.problem_id is not None, (
            "«%s» was dropped instead of being offered with its sheet" % cell.label
        )
        assert cell.sheet_number and cell.sheet_number != current_sheet.number

    on_the_sheet = [cell for cell in row.cells if cell.on_lead_sheet]
    assert len(on_the_sheet) > len(elsewhere), (
        "most of a bracket-less line must land on the CURRENT sheet (rule 2); "
        "%d of %d did" % (len(on_the_sheet), len(row.cells))
    )


# =============================================================================
#  IDEMPOTENCY -- the same text twice is the same work twice, not twice the work
# =============================================================================

def test_the_same_message_digests_the_same_and_a_changed_one_does_not(
    students, catalogue
):
    """The idempotency key is built on this digest, so the property belongs to it.

    Sending the identical text again must produce the identical key -- that is what lets
    the journal answer the second confirmation out of itself.  Sending a CHANGED text must
    not, or a correction would be swallowed as a repeat, which is the same bug with the
    damage reversed.
    """
    assert tekst.digest_of(OWNER_MESSAGE) == tekst.digest_of(OWNER_MESSAGE)
    assert tekst.digest_of(OWNER_MESSAGE) != tekst.digest_of(OWNER_MESSAGE + "\nАня Бочарова 5")


def test_parsing_the_same_message_twice_yields_the_same_cells(students, catalogue):
    """The parse is a pure function of the text and the catalogue, and nothing else.

    If it were not -- if a dictionary iterated in a different order, or a tie between two
    children broke differently -- then «тот же текст, посланный дважды» would produce two
    different tables, and the idempotency the screen relies on would be built on sand.
    """
    def shape(text):
        return [
            (row.student_id, row.present_no_marks, [c.problem_id for c in row.cells])
            for row in rows_of(text, students, catalogue)
        ]

    assert shape(CORPUS_MESSAGE) == shape(CORPUS_MESSAGE)


def test_an_empty_message_produces_no_rows_rather_than_one_empty_one(students, catalogue):
    """Nothing typed is nothing to confirm.  One empty row would be a table over nothing,
    and a «Записать (0)» button is an invitation to press it."""
    for nothing in ("", "   ", "\n\n", "---"):
        assert rows_of(nothing, students, catalogue) == [], nothing
