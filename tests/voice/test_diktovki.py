"""The corpus: whole dictated lines, resolved into pairs «student — problems».

This is the file the готовности criterion reads.  It prints its own coverage, and the
number it prints is the number of DICTATED LINES parsed, not the number of assertions:
"nothing failed" and "nothing ran" print the same thing otherwise, and a corpus that
quietly shrank to two lines would look exactly like a corpus of twenty-four.

Every line is a sentence a teacher of this conduit would say about a child of this
conduit, over problems that exist on the seeded sheets.  Nothing here is a token stream
invented to fit the parser.
"""

from __future__ import annotations

import pytest

from core.services.golos import parse_dictation


#: (dictated line, [(surname phrase, [labels]), ...]).  Read it as a transcript: this is
#: what the recogniser hands over in verbatim mode, spelled the way it was heard.
DICTATIONS = [
    ("Петров три пять семь бэ", [("петров", ["3", "5", "7б"])]),
    ("Агаркова первую и вторую", [("агаркова", ["1", "2"])]),
    ("Аникина с третьей по шестую", [("аникина", ["3", "4", "5", "6"])]),
    ("Аракелова десять а", [("аракелова", ["10а"])]),
    ("Афанасьева двадцать четыре", [("афанасьева", ["24"])]),
    ("Белеванцева семнадцать", [("белеванцева", ["17"])]),
    ("Бирюков минус один", [("бирюков", ["-1"])]),
    ("Болотин шестнадцать бэ", [("болотин", ["16б"])]),
    ("Борисов девятую", [("борисов", ["9"])]),
    ("Бочарова одиннадцать вэ", [("бочарова", ["11в"])]),
    ("Будылин тринадцать гэ", [("будылин", ["13г"])]),
    ("Быков пять дэ", [("быков", ["5д"])]),
    ("Верхошинский сдал восьмую", [("верхошинский", ["8"])]),
    ("Виляев решил задачи два и три", [("виляев", ["2", "3"])]),
    ("Гамаюнова двенадцать е", [("гамаюнова", ["12е"])]),
    ("Глебова девятнадцать", [("глебова", ["19"])]),
    ("Данилова номер двадцать один", [("данилова", ["21"])]),
    ("Добромыслов с первой по третью", [("добромыслов", ["1", "2", "3"])]),
    ("Долгирева четырнадцать а", [("долгирева", ["14а"])]),
    ("Домра шесть вэ и семь", [("домра", ["6в", "7"])]),
    ("Егоров пятнадцать бэ", [("егоров", ["15б"])]),
    ("Емельянцев три а три бэ три вэ", [("емельянцев", ["3а", "3б", "3в"])]),
    ("Жуков двадцать пять а", [("жуков", ["25а"])]),
    ("Исанин восемнадцать бэ", [("исанин", ["18б"])]),
    ("Фёдоров десятую", [("федоров", ["10"])]),
    ("Тухватулин Йалчын шестую", [("тухватулин йалчын", ["6"])]),
    # Two students in one breath.  A teacher walking the class does not press stop
    # between children, and a parser that took only the first name would drop the rest
    # in silence -- the quietest possible failure on this path.
    ("Кахиани три пять, Искеева вторую", [("кахиани", ["3", "5"]), ("искеева", ["2"])]),
    (
        "Коневник первую Кудишин вторую Кудряшов третью",
        [("коневник", ["1"]), ("кудишин", ["2"]), ("кудряшов", ["3"])],
    ),
]


def test_petrov_tri_pyat_sem_be_resolves_to_petrov_3_5_7b():
    """THE named line of the задание, on its own, as its own test.

    «Петров три пять семь бэ» -> student «Петров», problems 3, 5 and 7б.  It carries all
    three rules at once — a bare numeral, a run of numerals, and the letter suffix that
    is the whole reason a Russian normaliser has to be ours — and it is the line the
    criterion selects by name.
    """
    rows = parse_dictation("Петров три пять семь бэ")

    assert len(rows) == 1, "one student was dictated, %d rows came back" % len(rows)
    assert rows[0].surname_text == "петров"
    assert rows[0].labels == ["3", "5", "7б"]


def test_every_dictated_line_of_the_corpus_parses_into_pairs(capsys):
    """The whole corpus, with the coverage printed.

    Zero lines parsed against a non-empty corpus is RED, not green: an exception swallowed
    somewhere in the walk would otherwise leave a green run over an empty result.
    """
    parsed = 0
    errors = 0
    failures = []

    for said, expected in DICTATIONS:
        rows = parse_dictation(said)
        got = [(row.surname_text, row.labels) for row in rows]
        parsed += 1
        if got != expected:
            errors += 1
            failures.append("%r\n  expected %r\n  got      %r" % (said, expected, got))

    pairs = sum(len(expected) for _said, expected in DICTATIONS)
    with capsys.disabled():
        print(
            "\n[голос] надиктованных строк разобрано %d из %d · пар «ученик — задачи» %d "
            "· ошибок %d" % (parsed, len(DICTATIONS), pairs, errors)
        )

    assert parsed >= 20, "the corpus must carry at least 20 dictated lines, it has %d" % parsed
    assert parsed > 0, "the corpus is not empty and nothing parsed"
    assert errors == 0, "\n".join(failures)


@pytest.mark.parametrize("said, expected", DICTATIONS, ids=[d[0] for d in DICTATIONS])
def test_one_dictated_line(said, expected):
    """The same corpus line by line, so that a failure names the sentence that broke."""
    assert [(row.surname_text, row.labels) for row in parse_dictation(said)] == expected


def test_a_line_with_no_numerals_at_all_yields_a_row_with_no_problems():
    """A teacher who says only a name has said something, and it is not nothing: the row
    reaches the confirmation table empty, where a tap can fill it in."""
    rows = parse_dictation("Симонова")
    assert [(row.surname_text, row.labels) for row in rows] == [("симонова", [])]


def test_an_empty_transcript_yields_no_rows_rather_than_one_empty_row():
    """Silence, or an utterance the recogniser could make nothing of."""
    assert parse_dictation("") == []
    assert parse_dictation("   ...   ") == []


def test_the_original_line_travels_with_every_row():
    """A wrong parse must be diagnosable without replaying the audio, so the transcript
    stays attached to the rows it produced."""
    rows = parse_dictation("Кахиани три пять, Искеева вторую")
    assert all(row.said == "Кахиани три пять, Искеева вторую" for row in rows)
