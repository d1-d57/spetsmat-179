"""§1 and §4: the printed form carries codes, and «0 surnames» is a claim that can fail.

The interesting test in this file is not the green one.  ``--proba`` printing «фамилий на
бланке: 0» is worth exactly as much as the check behind it is capable of printing
something else, so the negative control feeds the checker a page that DOES carry a name
and asserts that it says so and exits 1.
"""

from __future__ import annotations

import subprocess
import sys

import config
from core.services.raspoznavanie import code_for_student, student_id_from_code
from tools.blank import (
    ROWS_PER_FORM,
    draw_form,
    labels_of_sheet,
    personal_words,
    roster_from_seed,
    surnames_on_form,
)


def test_code_round_trips_and_refuses_everything_else():
    """The form generator and the bot must agree, or every mark lands on a wrong child.

    The refusals matter more than the round trip: ``u17.``, «строка u17» and ``u017``
    come back as ``None`` rather than being trimmed into 17, because a silent trim is the
    shape of the failure that nobody notices -- every row is a real student, so nothing
    looks wrong afterwards.
    """
    for student_id in (1, 17, 56, 999):
        assert student_id_from_code(code_for_student(student_id)) == student_id

    for rubbish in ("u17.", "строка u17", "u0", "u", "17", "U17", "", "u-3", None, "u 17"):
        assert student_id_from_code(rubbish) is None, rubbish


def test_form_carries_codes_and_not_one_surname(tmp_path):
    roster = roster_from_seed(config.SEED_DIR)[:ROWS_PER_FORM]
    assert roster, "seed/students.csv is the oracle of this test and it is empty"
    labels = labels_of_sheet(config.SEED_DIR, "1")
    assert labels, "sheet 1 has no tasks in seed/sheets.json"

    _, drawn = draw_form(
        [code for code, _ in roster], labels, "1", "302", tmp_path / "blank.png"
    )

    leaked = surnames_on_form(drawn, personal_words(config.SEED_DIR))
    assert leaked == [], "personal data reached the printed form: %s" % leaked

    # Every row label is a code, and every code names a student -- the page is readable
    # by the pipeline, not merely free of names.
    for code, _ in roster:
        assert code in drawn
        assert student_id_from_code(code) is not None


def test_the_zero_surnames_check_can_go_red():
    """The negative control.  A checker that always answers «0» proves nothing."""
    words = personal_words(config.SEED_DIR)
    assert words, "the roster of personal words is empty; the check would be vacuous"
    a_surname = sorted(words)[0]

    assert surnames_on_form(["u1", "u2", "Листок 1"], words) == []
    assert surnames_on_form(["u1", a_surname.capitalize()], words) == [a_surname]
    # And inside a longer string, because a leak is a leak wherever it sits.
    assert surnames_on_form(["сдал %s вчера" % a_surname], words) == [a_surname]


def test_proba_prints_the_three_numbers_and_exits_zero():
    """The готовности criterion runs this exact command; the test runs it the same way."""
    done = subprocess.run(
        [sys.executable, "tools/blank.py", "--proba"],
        cwd=str(config.ROOT),
        capture_output=True,
        text=True,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert "кодов на бланке:" in done.stdout
    assert "задач на бланке:" in done.stdout
    assert "фамилий на бланке: 0" in done.stdout
