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
    assert len(checked) == 6


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
