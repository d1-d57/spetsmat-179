"""The inventory comes first and FAILS on the unknown.

This is the rule the previous importer broke most expensively: its ``value()`` returned
``None`` for everything except ``1.0`` and ``"x"`` and silently discarded 854 real cells,
including the ``✘`` mark on 88 problems and a whole third column layout.
"""

from __future__ import annotations

import pytest

from tools.import_konduit import (
    EMPTY,
    QUARANTINE,
    SOLVED,
    UnknownCellValue,
    VALUE_REGISTRY,
    WITHDRAWN,
    inventory,
    normalise,
    read_cells,
)

from synthetic import build_workbook


@pytest.mark.parametrize(
    "raw, expected",
    [
        (None, None),
        (1.0, 1),
        (1, 1),
        ("x", "x"),
        ("X", "x"),
        (" x ", "x"),
        (2.0, 2),
        ("`", "`"),
    ],
)
def test_normalise_only_does_the_two_things_it_documents(raw, expected):
    assert normalise(raw) == expected


def test_a_string_one_is_not_normalised_into_the_integer_one():
    """``'1'`` and ``1`` are different keystrokes, and the inventory exists to show that.

    Coercing them together is how a text-formatted column stops being visible as a
    finding and starts being invisible as a number.
    """
    assert normalise("1") == "1"
    assert normalise("1") not in VALUE_REGISTRY


def test_every_registry_meaning_is_one_of_the_four(seed_dir, workbook):
    assert set(VALUE_REGISTRY.values()) <= {EMPTY, SOLVED, WITHDRAWN, QUARANTINE}


def test_the_inventory_counts_every_cell_of_the_grid(seed_dir, workbook):
    readings = read_cells(workbook)
    counts = inventory(readings)
    assert sum(counts.values()) == len(readings)
    # Three sheets: 3 problems x 2 rows, 2 x 3 rows, 2 x 3 rows.
    assert len(readings) == 3 * 2 + 2 * 3 + 2 * 3


def test_an_unknown_value_stops_the_import_and_names_the_cell(tmp_path, seed_dir):
    """No silent ``None``, ever -- and the failure has to be actionable.

    A refusal that says only "bad value" leaves a person to search 29 920 cells, so the
    message is required to carry the sheet, the student, the problem and the value.
    """
    import openpyxl

    path = build_workbook(tmp_path / "unknown.xlsx", extra_value="✘")
    workbook = openpyxl.load_workbook(path, data_only=True)

    with pytest.raises(UnknownCellValue) as raised:
        read_cells(workbook)

    message = str(raised.value)
    assert "✘" in message
    assert "Первов" in message
    assert "3*" in message
    assert "листке 1" in message


def test_the_two_quarantined_values_are_named_and_not_dropped(seed_dir, workbook):
    """``2.0`` is in the grid; it must arrive classified, not discarded."""
    readings = read_cells(workbook)
    quarantined = [reading for reading in readings if reading.meaning == QUARANTINE]
    assert len(quarantined) == 1
    assert quarantined[0].raw == 2.0
    assert quarantined[0].surname == "Второва"
