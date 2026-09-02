"""§5 — the part that makes every other number in this suite mean anything.

Corrupt the journal three ways; the checks MUST go red on each.  Green on a corruption is
a failure of the position, and five lines of this would have killed the previous
tautology in a minute: that version compared the journal against a SUM over the very
cells it had read, so it could not have gone red on any corruption at all.
"""

from __future__ import annotations

import pytest

from tools.import_konduit import (
    CORRUPTIONS,
    all_checks,
    corrupt,
    differential,
    oracle_debts,
    oracle_graveyard,
)


@pytest.fixture
def checked(connection, imported, workbook):
    """The synthetic conduit, imported and green, ready to be broken."""
    results = all_checks(connection, workbook)
    assert not any(result.is_red for result in results), \
        "the control is meaningless if the checks are already red before the corruption"
    return results


def test_the_checks_are_green_before_any_corruption(checked):
    assert len(checked) == 7


@pytest.mark.parametrize("which", CORRUPTIONS)
def test_every_corruption_turns_a_check_red(connection, imported, workbook, checked, which):
    corrupt(connection, which)
    after = all_checks(connection, workbook)
    red = [result.name for result in after if result.is_red]
    assert red, "ЗЕЛЁНОЕ НА ПОРЧЕ: %r прошла незамеченной" % which


def test_a_deleted_event_is_caught_by_the_full_grid(connection, imported, workbook, checked):
    """Deleting takes dropping the append-only trigger, which is itself the proof that an
    honest caller cannot do it: the schema refuses DELETE outright."""
    with pytest.raises(Exception, match="append-only"):
        connection.execute("delete from marks where id = 1")

    corrupt(connection, CORRUPTIONS[0])
    assert differential(connection, workbook).is_red


def test_a_flipped_mark_is_caught_by_the_full_grid(connection, imported, workbook, checked):
    with pytest.raises(Exception, match="append-only"):
        connection.execute("update marks set event = 'retract' where id = 1")

    corrupt(connection, CORRUPTIONS[1])
    assert differential(connection, workbook).is_red


def test_two_swapped_students_are_caught_by_a_FULLY_INDEPENDENT_oracle(
    connection, imported, workbook, checked
):
    """The one corruption that matters most, and the one an internal check alone could
    miss: swapping two students permutes the grid without changing any total.

    It is caught by ``гробарий``, whose names were typed by a person and are the only
    numbers in the book not computed from the cells being checked.
    """
    corrupt(connection, CORRUPTIONS[2])
    graveyard = oracle_graveyard(connection, workbook)
    assert graveyard.is_red
    assert graveyard.independence == "НЕЗАВИСИМЫЙ"


def test_zero_checked_against_a_non_empty_source_is_red_not_green(connection, imported,
                                                                  workbook):
    """§4: a negative verdict has to carry its coverage INSIDE it.

    'no divergences' over nothing checked and 'no divergences' over everything checked
    print the same way unless the coverage is part of the verdict, and the first one is
    the failure mode that looks exactly like success.
    """
    result = oracle_debts(connection, workbook)
    assert result.checked > 0 and not result.is_red

    result.checked = 0
    assert result.is_red, "нулевое покрытие при непустом источнике обязано быть КРАСНЫМ"
    assert "сверено 0 из" in result.line()
    assert "КРАСНЫЙ" in result.line()


def test_a_wrong_first_sheet_id_is_caught_by_the_debts_oracle(connection, imported,
                                                              workbook, checked):
    """A fourth corruption, beyond the three §5 names, aimed at the rule §3 exists for.

    Clearing ``first_sheet_id`` makes the late arrival owe the sheets they were never
    there for.  The book carries '✓' for exactly those cells, so the debts oracle has to
    notice -- which is also why those cells are checked rather than skipped.
    """
    connection.execute(
        "update students set first_sheet_id = ("
        "  select id from sheets order by ord limit 1) where surname = 'Позднев'"
    )
    connection.commit()

    assert oracle_debts(connection, workbook).is_red


def test_a_duplicated_event_leaves_every_state_identical_and_is_caught_anyway(
    connection, imported, workbook, checked
):
    """The corruption that all five state checks miss, and why the sixth one exists.

    A mark is an EVENT, and the projection reads only the LAST event of a cell, so
    duplicating an assert moves no state at all.  Every check that judges the projection
    stays green while the journal doubles -- which is exactly what an importer run twice
    would do.  ``journal_cardinality`` judges ROW COUNTS against an identity taken from
    the source inventory, so it sees what the projection cannot.
    """
    from tools.import_konduit import differential, journal_cardinality

    row = connection.execute(
        "select * from marks where event = 'assert' order by id limit 1"
    ).fetchone()
    connection.execute(
        "insert into marks (student_id, problem_id, event, teacher_id, valid_at, "
        "recorded_at, source) values (?, ?, 'assert', ?, ?, ?, 'импорт')",
        (row["student_id"], row["problem_id"], row["teacher_id"],
         row["valid_at"], row["recorded_at"]),
    )
    connection.commit()

    assert not differential(connection, workbook).is_red, \
        "the projection cannot see this, and is not expected to"
    assert journal_cardinality(connection, workbook).is_red


def test_importing_twice_into_one_journal_is_refused(connection, imported, workbook):
    """The catalogue load is idempotent; the journal load cannot be.

    A second import does not overwrite the first -- it says the same thing happened again.
    Refusing is the only honest answer, and it has to be an exception rather than a silent
    skip so that a caller cannot mistake a doubled journal for a fresh one.
    """
    from tools.import_konduit import AlreadyImported, import_workbook

    with pytest.raises(AlreadyImported, match="удвоил бы его молча"):
        import_workbook(connection, workbook)


# ------------------------------------------------- what the §3 verifier found still green
#
# Three of the verifier's six invented corruptions passed every check unnoticed.  Each is
# pinned here, on the SYNTHETIC conduit, so that it is checked on a machine that does not
# have the book -- which was the verifier's Finding 9: the coverage numbers were pinned
# only by test_real_workbook.py, and that file skips without the workbook.


def test_coverage_is_JUDGED_and_not_merely_printed(connection, imported, workbook):
    """Verifier Finding 5, the important one.

    While only ZERO coverage was red, renaming one of the 544 labels dropped the full-grid
    check to '543 of 544' and it still printed [зелёный] and still exited 0.  Printing a
    number is not judging it: the number showed the shortfall to a person, and nothing
    showed it to the exit code.
    """
    from tools.import_konduit import differential

    connection.execute(
        "update problems set label = '___renamed___' where id = (select min(id) from problems)"
    )
    connection.commit()

    result = differential(connection, workbook)
    assert result.divergences == [], "the shortfall is in COVERAGE, not in divergences"
    assert result.checked < result.total
    assert result.is_red, "coverage short of total must be red on its own"


def test_every_check_covers_everything_it_counted(connection, imported, workbook):
    """The same rule stated positively, and the one assertion that runs everywhere."""
    from tools.import_konduit import all_checks

    for result in all_checks(connection, workbook):
        assert result.checked + len(result.skipped) == result.total, result.line()
        assert not result.is_red, result.line()


def test_wiping_teacher_attribution_is_caught(connection, imported, workbook, checked):
    """Verifier Finding 6: no check read ``teacher_id``, so the whole §6 decision --
    860 composite marks, first-named attribution, the ``соавтор:`` tag -- could not fail."""
    from tools.import_konduit import check_attribution

    connection.execute("drop trigger if exists marks_append_only_update")
    connection.execute(
        "update marks set teacher_id = (select min(id) from teachers)")
    connection.commit()

    assert check_attribution(connection, workbook).is_red


def test_stripping_the_carrier_note_is_caught(connection, imported, workbook, checked):
    """Verifier Finding 7: the marker distinguishing a synthetic carrier ``assert`` from a
    real check-off was a free-text note that nothing tested.

    The reversal is the real guard -- a reversed assert can never project as SOLVED -- but
    the note is what stops a later ``group by teacher_id`` from counting the carriers as
    real hand-ins, and it has to be checkable.
    """
    from tools.import_konduit import NOTE_X_CARRIER, check_attribution

    connection.execute("drop trigger if exists marks_append_only_update")
    stripped = connection.execute(
        "update marks set note = 'x' where note like ?", ("%" + NOTE_X_CARRIER + "%",)
    ).rowcount
    connection.commit()

    assert stripped > 0
    assert check_attribution(connection, workbook).is_red


def test_no_carrier_assert_is_ever_left_standing(connection, imported):
    """Every carrier is reversed by its retract; an unreversed one would project as SOLVED
    and turn a withdrawal into a credited hand-in."""
    from tools.import_konduit import NOTE_X_CARRIER

    unreversed = connection.execute(
        "select count(*) from marks m where m.event = 'assert' and m.note like ? "
        "  and not exists (select 1 from marks r where r.reverses_id = m.id)",
        ("%" + NOTE_X_CARRIER + "%",),
    ).fetchone()[0]
    assert unreversed == 0
