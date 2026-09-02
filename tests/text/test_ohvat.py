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


# =============================================================================
#  THE BOUNDARY INSIDE A LINE -- found by the §3 verifier, after the parser was written
# =============================================================================
#
# These are REGRESSION tests in the strict sense: every one of them was red when it was
# written.  The parser implemented §1 rule 1 across lines only; inside a line a name that
# followed a label was DROPPED, and the child it belonged to disappeared while their marks
# stayed behind on the child above.  The отчёт carries the numbers.

def test_two_children_on_one_line_are_two_children(students, catalogue):
    """The defect, exactly as the verifier found it, as its own named test.

    «Лёня Санин 7, 9а Катя Долкирева 2а, 2б» used to come back as ONE row: Исанин, holding
    all four labels, with `2а` and `2б` pre-ticked — and Долгирева nowhere on the screen.
    That is «плюс, поставленный чужому ребёнку», the one error the задание forbids by name,
    and it was invisible: the table showed a resolved child and four tidy buttons.
    """
    rows = rows_of("Лёня Санин 7, 9а Катя Долкирева 2а, 2б", students, catalogue)

    assert [row.student_id for row in rows] == [23, 18]
    assert [cell.label for cell in rows[0].cells] == ["7", "9а"]
    assert [cell.label for cell in rows[1].cells] == ["2а", "2б"]


def test_a_whole_evening_typed_on_one_line_still_separates(students, catalogue):
    """The same message as the owner's four lines, pasted with the newlines lost.

    Copying out of a note, out of a chat, off a phone — the newlines are the first thing to
    go, and the format must not depend on them for its most important boundary.
    """
    rows = rows_of(" ".join(line for line, _, _, _ in OWNER_LINES), students, catalogue)

    assert [row.student_id for row in rows] == [
        student_id for _, student_id, _, _ in OWNER_LINES
    ]
    assert rows[2].sheet_marker == "3д"
    assert all(row.sheet_marker is None for row in rows if row.student_id != 9), (
        "the bracket of one block leaked onto another when the line was not broken"
    )
    assert rows[3].present_no_marks is True, "the явка was lost when the newlines were"


@pytest.mark.parametrize("separator", ["; ", ", ", " · ", " "])
def test_the_everyday_separators_a_teacher_types_all_divide(separator, students, catalogue):
    """Semicolon, comma, dot, plain space — a teacher divides children however they like.

    None of these can be the rule, and that is the point: the boundary is the NAME, so it
    holds whatever punctuation happens to be around it.
    """
    text = separator.join(["Санин 7, 9а", "Долкирева 2а, 2б", "Бочарова 5"])
    rows = rows_of(text, students, catalogue)

    assert [row.student_id for row in rows] == [23, 18, 9]
    assert [len(row.cells) for row in rows] == [2, 2, 1]


def test_a_conjunction_after_the_labels_does_not_become_a_child(students, catalogue):
    """«Долгирева 2а, 2б и 4» — «и» is not a name, and задача 4 stays with Долгирева.

    The floor that decides this is a LENGTH: no Russian given name or surname is under
    three letters, and «и», «а», «но», «да» all are.  Without it the cut that fixes the
    test above would hand задача 4 to a child called «и» — a fix that swapped one silent
    loss for another.
    """
    rows = rows_of("Долгирева 2а, 2б и 4", students, catalogue)

    assert len(rows) == 1, [row.said for row in rows]
    assert rows[0].student_id == 18
    assert [cell.label for cell in rows[0].cells] == ["2а", "2б", "4"]


def test_a_bracket_is_never_mistaken_for_the_next_childs_name(students, catalogue):
    """`[3д]` stands between a name and its labels and must not cut the block in two.

    It is neither a name nor a label, and a splitter that read it as a word would break
    every line the owner writes a sheet marker on — which is every line about a доплисток.
    """
    rows = rows_of("Аня Бочарова [3д] 5, 12 Влад Быков —", students, catalogue)

    assert [row.student_id for row in rows] == [9, 11]
    assert rows[0].sheet_marker == "3д"
    assert rows[1].present_no_marks is True


# =============================================================================
#  THE MIRROR IMAGE -- what the mid-line cut cost, and what pays for it
# =============================================================================
#
# The §3 verifier came back a second time and found that the fix above had bought a new
# way to stage a plus on the wrong child: a trailing prose word that happens to resemble a
# roster name now OPENS a block and takes the labels after it, PRE-TICKED.  Measured on
# the live roster: «дома» matches Домра at 89 and «верно» matches Данилова Вера at exactly
# 80.0 — which the strict `<` comparison let through the lone-word floor.
#
# Both errors are the same error, so both are refused the same way: the cut still happens
# (a real next child must never be swallowed), and what it produces is a DOUBTFUL row with
# nothing ticked.

def test_a_prose_word_mid_line_does_not_arrive_pre_ticked(students, catalogue):
    """«Санин 7, 9а дома 11б» — «дома» is Домра at 89, and задача 11б must not be staged.

    The row is still SHOWN: swallowing the word is how the first bug worked, and a parser
    that hides what it did not understand is the thing this whole position exists against.
    What it may not do is arrive ready to write.
    """
    from bot.routers.photo import checked_cells
    from bot.routers.text_input import draft_to_state

    draft = tekst.build_draft("Санин 7, 9а дома 11б", students=students, catalogue=catalogue)
    rows = draft.rows

    assert len(rows) == 2, [row.said for row in rows]
    assert rows[1].verdict is Verdict.DOUBTFUL, rows[1].reason
    assert all(not cell.ticked for cell in rows[1].cells)
    assert all(
        student_id == rows[0].student_id
        for student_id, _ in checked_cells(draft_to_state(draft))
    ), "a plus was staged on a child the teacher never wrote"


def test_a_two_word_name_mid_line_is_trusted_as_written(students, catalogue):
    """«Катя Долкирева» after Санин's labels is a NAME and is treated as one.

    Two words is the owner's format and is strong evidence; one word mid-line is the
    parser choosing where a child begins.  The distinction is what keeps the guard from
    costing the ordinary case its pre-ticks.
    """
    rows = rows_of("Лёня Санин 7, 9а Катя Долкирева 2а, 2б", students, catalogue)

    assert rows[1].student_id == 18
    assert rows[1].verdict is Verdict.CERTAIN
    assert all(cell.ticked for cell in rows[1].cells)


def test_a_one_word_child_mid_line_is_shown_but_asks_for_the_tap(students, catalogue):
    """The cost of the guard, stated as a test rather than left to be discovered.

    «Санин 7, 9а; Долкирева 2а, 2б» resolves both children correctly and marks the second
    doubtful, so the teacher taps twice.  That is a real cost on a real input, and it is
    the price of «дома» not arriving ticked — the owner writes one child per line, so it
    is paid on the recovery path and not on his own.
    """
    rows = rows_of("Санин 7, 9а; Долкирева 2а, 2б", students, catalogue)

    assert [row.student_id for row in rows] == [23, 18]
    assert rows[1].verdict is Verdict.DOUBTFUL
    assert [cell.ticked for cell in rows[1].cells] == [False, False]


def test_a_score_exactly_on_the_lone_word_floor_is_not_above_it(students, catalogue):
    """«верно» scores exactly 80.0 against Данилова Вера — the floor's own value.

    An off-by-one in a comparison is not a rounding question here: it is the difference
    between a prose word naming a child and not naming one.
    """
    match = tekst.match_student("верно", students)
    assert match.score == pytest.approx(tekst.LONE_WORD_FLOOR)
    assert match.student_id is None, "a score ON the floor was treated as clear of it"


# =============================================================================
#  THE DASHES A REAL KEYBOARD PRODUCES
# =============================================================================

@pytest.mark.parametrize("dash", ["—", "-", "–", "--", "---", "−", "––"])
def test_every_dash_a_keyboard_makes_is_read_as_the_procherk(dash, students, catalogue):
    """`--` is what a laptop gives most often, and it used to be read as part of the NAME.

    The damage was worse than a failed match: «Быков --» went unresolved AND
    ``present_no_marks`` stayed False, so even after the teacher tapped the right child
    the явка was never recorded — the fact was gone, not merely unattributed.

    ⚠ A whole LINE of three or more dashes is a different thing — the paper's own divider —
    and it is removed before tokenising.  The test below holds that half.
    """
    draft = tekst.build_draft("Влад Быков %s" % dash, students=students, catalogue=catalogue)
    row = draft.rows[0]

    assert row.student_id == 11, row.reason
    assert row.present_no_marks is True
    assert row.cells == []
    assert tekst.attendance_intents(draft) == [11]


def test_a_line_of_dashes_is_still_a_divider_and_not_a_procherk(students, catalogue):
    """The two readings of `---` stay apart: alone on its line it divides, after a name it
    is the прочерк.  Collapsing them would either invent a явка or lose one."""
    rows = rows_of("Катя Долкирева 2а\n---\nВлад Быков —", students, catalogue)

    assert [row.student_id for row in rows] == [18, 11]
    assert [row.present_no_marks for row in rows] == [False, True]


# =============================================================================
#  THE BRACKET BELONGS TO THE NAME IT STANDS BEFORE
# =============================================================================

def test_a_bracket_after_the_labels_belongs_to_the_next_child(students, catalogue):
    """`Санин 7 [3д]Бочарова 5` — the bracket is Бочарова's, and it used to be Санин's.

    §1 rule 3 puts the marker after the NAME and before the LABELS, so a bracket that turns
    up after the labels cannot be about the block being read.  Attached to the wrong block
    it moved Санин's задача 7 off the current листок and onto 3д — a real problem id on a
    real child, from another month.
    """
    rows = rows_of("Санин 7 [3д]Бочарова 5", students, catalogue)

    assert [row.student_id for row in rows] == [23, 9]
    assert rows[0].sheet_marker is None
    assert rows[0].cells[0].on_lead_sheet is True, "задача 7 was moved onto листок 3д"
    assert rows[1].sheet_marker == "3д"


# =============================================================================
#  THE LAST TWO, AND WHERE THE PARSER STOPS
# =============================================================================
#
# The third verifier pass found that the guard above was keyed on the wrong thing and that
# a comma without a space still lost задачи silently.  Both are closed here; the third
# thing it found is not closable and is stated as a test of what the parser DOES do.

def test_the_guard_does_not_depend_on_where_the_line_happened_to_break(
    students, catalogue
):
    """«Санин 7 дома 11б» and «Санин 7\\ndома 11б» must be judged the same way.

    They were not.  The guard keyed on ``mid_line``, so the newline decided whether задача
    11б arrived staged on Домра Евгений — the same word, the same score of 89, the same
    plus.  A property of the EVIDENCE cannot turn on where a phone wrapped the text.
    """
    from bot.routers.photo import checked_cells
    from bot.routers.text_input import draft_to_state

    for text in ("Санин 7, 9а дома 11б", "Санин 7, 9а\nдома 11б"):
        draft = tekst.build_draft(text, students=students, catalogue=catalogue)
        stray = draft.rows[1]
        assert stray.verdict is Verdict.DOUBTFUL, (text, stray.reason)
        assert all(not cell.ticked for cell in stray.cells), text
        assert all(
            student_id != stray.student_id
            for student_id, _ in checked_cells(draft_to_state(draft))
        ), text


def test_a_lone_surname_that_matches_exactly_costs_the_teacher_nothing(
    students, catalogue
):
    """The guard must not tax the ordinary shorthand.

    «Бочарова» and «Быков» written alone match a child EXACTLY — there is no question of
    who is meant — so they stay CERTAIN and their cells stay pre-ticked.  Only a lone word
    that had to be GUESSED at asks for the tap.
    """
    for lone in ("Бочарова 12", "Быков 12"):
        row = rows_of(lone, students, catalogue)[0]
        assert row.verdict is Verdict.CERTAIN, (lone, row.reason)
        assert [cell.ticked for cell in row.cells] == [True], lone


def test_a_comma_without_a_space_does_not_swallow_the_problems_after_it(
    students, catalogue
):
    """«7, 9а, 11б,12» — a phone's ordinary typing, and it used to lose два номера.

    `11б,12` came back as ONE token, which is not a label, so it was read as a NAME: the
    table showed Исанин with two problems instead of four and a «кто это?» row underneath
    that the teacher could not even tap into.  Silent, and on the channel tomorrow's lesson
    runs on.
    """
    row = rows_of("Лёня Санин 7, 9а, 11б,12", students, catalogue)[0]

    assert row.student_id == 23
    assert [cell.label for cell in row.cells] == ["7", "9а", "11б", "12"]


@pytest.mark.parametrize("separator", [",", ";", "·"])
def test_every_unspaced_separator_divides_the_labels(separator, students, catalogue):
    row = rows_of("Катя Долкирева 2а%s2б%s4" % (separator, separator), students, catalogue)[0]
    assert [cell.label for cell in row.cells] == ["2а", "2б", "4"]


def test_a_prose_word_that_IS_a_childs_name_is_read_as_that_child(students, catalogue):
    """Where this parser stops, written down rather than left to be discovered.

    «вера 2а» resolves to Данилова Вера, CERTAIN and pre-ticked — because «Вера» IS her
    name, exactly, and nothing in the text distinguishes the word from the name.  No rule
    can separate them without also refusing a teacher who really did write «Вера 2а», and
    refusing that is the worse error.

    This is the boundary the confirmation table exists for: the row is drawn with the
    child's full name on it, nothing is written until a person has looked at it, and the
    отчёт names the limit instead of implying it is not there.
    """
    row = rows_of("вера 2а", students, catalogue)[0]

    assert row.student_id is not None
    assert catalogue.student(row.student_id).name == "Вера"
