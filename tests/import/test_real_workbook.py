"""The real conduit, when the machine running the tests happens to have it.

SKIPPED, NOT FAILED, when the book is absent.  It is the personal data of fifty-six
children and it is not in the repository, so a suite that failed without it would be red
on every machine that is doing the right thing.  Everything structural is covered by the
synthetic conduit in ``synthetic.py``; what only the real book can check is that the
numbers this position reports are the numbers the book actually contains.
"""

from __future__ import annotations

import pytest

import config
from tools.import_konduit import (
    CORRUPTIONS,
    all_checks,
    corrupt,
    import_workbook,
    inventory,
    normalise,
    open_workbook,
    read_cells,
    sheets_to_import,
)

pytestmark = pytest.mark.skipif(
    not config.KONDUIT_XLSX.exists(),
    reason="книги кондуита нет на этой машине (%s) — это нормальный исход: "
           "она содержит персональные данные и в репозитории не лежит" % config.KONDUIT_XLSX,
)


@pytest.fixture(scope="module")
def real_workbook():
    return open_workbook()


@pytest.fixture
def real_import(connection, real_workbook):
    return import_workbook(connection, real_workbook)


def test_the_eighteen_sheets_of_the_season():
    assert len(sheets_to_import()) == 18


def test_the_inventory_is_the_five_values_and_nothing_else(real_workbook):
    """The measurement §1 of the задание rests on, re-taken by the code rather than quoted.

    ``read_cells`` raises on anything outside the registry, so reaching this assertion at
    all already proves there is no sixth value; the counts are pinned so that a change in
    the book is a failing test rather than a silent difference in a report nobody reads.
    """
    counts = inventory(read_cells(real_workbook))
    assert dict(counts) == {None: 14824, 1: 14377, "x": 735, 2: 1, "`": 1}


def test_first_sheet_id_is_explicit_for_all_56_and_null_survives_nowhere(
    connection, real_import
):
    assert real_import.first_sheet_set == 56
    assert real_import.first_sheet_null == 0
    assert connection.execute(
        "select count(*) from students where first_sheet_id is null"
    ).fetchone()[0] == 0


def test_the_book_agrees_with_the_seed_about_who_arrived_when(real_import):
    """The two movers of §3, and the rest.  A disagreement here would be a finding."""
    assert real_import.first_sheet_disagreements == []


def test_both_movers_land_where_the_задание_says(connection, real_import):
    rows = dict(
        connection.execute(
            "select st.surname, s.number from students st "
            "  join sheets s on s.id = st.first_sheet_id "
            " where st.surname in ('Пирогов', 'Гамаюнова')"
        ).fetchall()
    )
    assert rows == {"Пирогов": "6", "Гамаюнова": "1"}


def test_the_two_quarantined_cells_are_the_two_the_задание_names(real_import):
    quarantined = {(sheet, surname, label)
                   for sheet, surname, _name, label, _raw in real_import.quarantined}
    assert quarantined == {("9", "Фёдоров", "-4б"), ("15", "Искеева", "1°д")}


def test_the_senior_of_room_203_is_registered(real_import):
    assert [name for name, _why in real_import.teachers_added] == ["НС"]


def test_every_oracle_is_green_over_its_full_coverage(connection, real_import,
                                                      real_workbook, capsys):
    """The готовности criterion, as a test rather than as a command a person must run.

    Each verdict is asserted together with its COVERAGE: 'divergences 0' over nothing
    checked is the failure that looks most like success.
    """
    results = all_checks(connection, real_workbook)
    capsys.readouterr()

    by_name = {result.name: result for result in results}
    assert not any(result.is_red for result in results), \
        [result.line() for result in results if result.is_red]

    assert by_name["полная сетка, задач 544 из 544"].checked == 29938
    assert by_name["тридцать клеток вручную"].checked == 30
    assert by_name["гробарий (имена от руки)"].checked == 20
    assert by_name["лист «зачёт» (имена)"].checked == 55
    assert by_name["лист «долги»"].checked == 770
    for result in results:
        assert result.checked > 0


def test_the_one_known_defect_of_the_book_is_still_the_only_one(connection, real_import,
                                                               real_workbook):
    """Registered, printed on every run, and NOT allowed to hide a second one behind it."""
    graveyard = [result for result in all_checks(connection, real_workbook)
                 if result.name.startswith("гробарий")][0]
    assert graveyard.divergences == []
    assert len(graveyard.known_defects) == 1
    assert "Аникина" in graveyard.known_defects[0]


@pytest.mark.parametrize("which", CORRUPTIONS)
def test_the_negative_control_reddens_on_the_real_book(connection, real_import,
                                                       real_workbook, which, capsys):
    before = all_checks(connection, real_workbook)
    assert not any(result.is_red for result in before)

    corrupt(connection, which)
    after = all_checks(connection, real_workbook)
    capsys.readouterr()
    assert any(result.is_red for result in after), \
        "ЗЕЛЁНОЕ НА ПОРЧЕ %r — провал позиции" % which


def test_every_one_of_the_544_problems_is_reached_by_a_reading(connection, real_import,
                                                               real_workbook):
    """The label repair has to be applied by the READER too, not only by the seed loader.

    While it was applied only in ``core/services/seeding.py``, the two ``12д`` columns of
    sheet ``2д`` both resolved to the single ``12д`` row of the catalogue: one problem of
    the 544 was never reached by any reading, and one column's cells were attributed to
    the other column's problem.  Both columns are empty, so nothing was misattributed in
    fact -- but it was silent, and only the printed coverage showed it (543 of 544).  This
    test is that coverage, pinned.
    """
    from tools.import_konduit import differential

    result = differential(connection, real_workbook)
    assert result.name == "полная сетка, задач 544 из 544"
    assert result.checked == 29938
    assert not result.is_red
