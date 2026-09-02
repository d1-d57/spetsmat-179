"""The import itself: the four layouts, the meaning of every value, and first_sheet_id."""

from __future__ import annotations

import pytest

from core.models import CellState
from core.services.progress import ProgressService
from infra.repositories import SqliteCatalogue, SqliteMarkJournal
from tools.import_konduit import (
    NOTE_X_CARRIER,
    layout_of,
    problem_columns,
    sheets_to_import,
    split_receiver,
    student_rows,
)


def _state(connection, surname, sheet_number, label):
    progress = ProgressService(SqliteMarkJournal(connection), SqliteCatalogue(connection))
    student_id = connection.execute(
        "select id from students where surname = ?", (surname,)
    ).fetchone()[0]
    problem_id = connection.execute(
        "select p.id from problems p join sheets s on s.id = p.sheet_id "
        " where s.number = ? and p.label = ?", (sheet_number, label)
    ).fetchone()[0]
    return progress.states_for(student_id, [problem_id])[problem_id]


# ------------------------------------------------------------------------- the layouts


def test_all_four_layouts_are_found_by_their_headers(seed_dir, workbook):
    """Including the ``1д`` shape, where the header IS row 1 and there is no status row.

    Fifty of last season's 544 problems live on sheets of that shape, and the previous
    importer's layout finder started at row 1 looking for a header row BELOW the labels,
    so it could not see them at all.
    """
    old = layout_of(workbook["1"])
    new = layout_of(workbook["9"])
    d_sheet = layout_of(workbook["1д"])

    assert (old.header_row, old.surname_column, old.receiver_column) == (3, 3, 2)
    assert old.has_status_row
    assert (new.header_row, new.surname_column, new.closed_column) == (3, 1, 3)
    assert new.has_status_row
    assert (d_sheet.header_row, d_sheet.surname_column) == (1, 3)
    assert not d_sheet.has_status_row


def test_the_sheets_to_import_come_from_the_seed_in_issue_order(seed_dir):
    assert sheets_to_import() == ("1", "9", "1д")


def test_problem_columns_skip_the_service_columns_on_the_1d_shape(seed_dir, workbook):
    """On ``1д`` row 1 holds the title, 'принимающий', 'фамилия', 'имя' AND the labels."""
    worksheet = workbook["1д"]
    labels = problem_columns(worksheet, layout_of(worksheet))
    assert list(labels.values()) == ["1", "2**"]


def test_the_late_student_has_no_row_on_the_first_sheet(seed_dir, workbook):
    worksheet = workbook["1"]
    surnames = [surname for _row, surname, _name in student_rows(worksheet, layout_of(worksheet))]
    assert surnames == ["Первов", "Второва"]


# -------------------------------------------------------------------- what a value means


def test_a_one_becomes_a_credited_cell(connection, imported):
    assert _state(connection, "Первов", "1", "1а°") is CellState.SOLVED


def test_an_empty_cell_stays_empty(connection, imported):
    assert _state(connection, "Первов", "1", "3*") is CellState.EMPTY


def test_an_x_lands_the_cell_at_retracted_and_not_at_empty(connection, imported):
    """``x`` has to mean 'not credited AND not a debt'.

    The book's own arithmetic says so: every sheet's ``закрыт`` formula reads
    ``NOT(REGEXMATCH(cell, "^(1|x)$"))`` and so treats ``1`` and ``x`` identically as
    'does not owe this'.  EMPTY would make 735 cells into debts that the book says are
    not debts.
    """
    state = _state(connection, "Первов", "1", "2")
    assert state is CellState.RETRACTED
    assert not state.is_debt_candidate
    assert state.counts_in_statistics
    assert not state.is_credited


def test_the_carrier_assert_under_an_x_is_stamped_so_it_cannot_be_read_as_a_check_off(
    connection, imported
):
    """A ``retract`` needs ``reverses_id``, so a carrier ``assert`` must precede it.

    That carrier is an artefact of the schema and not an observed event, and the note is
    what keeps the two distinguishable for anyone reading the journal later.
    """
    rows = connection.execute(
        "select m.event, m.note from marks m "
        "  join problems p on p.id = m.problem_id "
        "  join sheets s on s.id = p.sheet_id "
        "  join students st on st.id = m.student_id "
        " where st.surname = 'Первов' and s.number = '1' and p.label = '2' order by m.id"
    ).fetchall()

    assert [row["event"] for row in rows] == ["assert", "retract"]
    assert NOTE_X_CARRIER in rows[0]["note"]
    assert NOTE_X_CARRIER not in rows[1]["note"]


def test_a_quarantined_value_writes_no_event_and_is_reported_by_name(connection, imported):
    """``2.0`` is not silently dropped -- it is named, with its coordinates."""
    assert _state(connection, "Второва", "9", "1°") is CellState.EMPTY
    assert [(sheet, surname, label, raw)
            for sheet, surname, _name, label, raw in imported.quarantined] == \
        [("9", "Второва", "1°", 2.0)]


def test_every_written_mark_is_sourced_as_импорт(connection, imported):
    sources = {row[0] for row in connection.execute("select distinct source from marks")}
    assert sources == {"импорт"}


def test_the_two_times_are_not_the_same_question(connection, imported):
    """``valid_at`` is last season; ``recorded_at`` is now.  A single timestamp collapses
    'this happened then' into 'this arrived now'."""
    row = connection.execute("select valid_at, recorded_at from marks limit 1").fetchone()
    assert row["valid_at"].startswith("2026-06-30")
    assert row["recorded_at"] != row["valid_at"]


# ---------------------------------------------------------------------- first_sheet_id


def test_first_sheet_id_is_explicit_for_everyone_and_null_survives_nowhere(
    connection, imported
):
    """§3: NULL must not survive this import.

    P1's fallback -- NULL means 'owes from the very first sheet' -- is right for imported
    rows and wrong for a freshly registered student.  It is not touched here; what is done
    is to make NULL impossible, so it never has to fire for anyone who came from the book.
    """
    assert imported.first_sheet_null == 0
    assert imported.first_sheet_set == 3
    assert connection.execute(
        "select count(*) from students where first_sheet_id is null"
    ).fetchone()[0] == 0


def test_a_student_who_arrives_late_gets_the_sheet_they_arrived_at(connection, imported):
    row = connection.execute(
        "select s.number from students st join sheets s on s.id = st.first_sheet_id "
        " where st.surname = 'Позднев'"
    ).fetchone()
    assert row["number"] == "9"


def test_the_seed_column_is_compared_and_not_copied(connection, seed_dir, workbook):
    """The rule is computed from the BOOK; the seed's own column is an oracle for it.

    Copying the column across would make the comparison a comparison of the column with
    itself, which is the same shape of mistake as checking the grid against its SUM row.
    """
    import csv

    from tools.import_konduit import import_workbook

    path = seed_dir / "students.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows[2]["first_sheet"] = "1"          # the seed now LIES about Позднев
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    counts = import_workbook(connection, workbook)

    assert counts.first_sheet_disagreements == [("Позднев", "Павел", "1", "9")]
    row = connection.execute(
        "select s.number from students st join sheets s on s.id = st.first_sheet_id "
        " where st.surname = 'Позднев'"
    ).fetchone()
    assert row["number"] == "9", "the book wins over the seed, and the difference is reported"


# -------------------------------------------------------------------------- the teachers


@pytest.mark.parametrize(
    "receiver, expected",
    [
        ("Аня", ["Аня"]),
        ("Борис Петрович/Ольга Александровна", ["Борис Петрович", "Ольга Александровна"]),
        ("Мика/Вася", ["Мика/Вася"]),
    ],
)
def test_a_slash_does_not_always_mean_two_people(receiver, expected):
    """'Мика/Вася' is ONE teacher -- a row of seed/teachers.csv with aka 'МН'."""
    assert split_receiver(receiver) == expected


def test_the_senior_who_is_named_but_not_registered_is_registered(connection, imported):
    """Hole (a) of §6: seniors are named by ``senior_aka`` and one of them has no row."""
    added = dict((name, why) for name, why in imported.teachers_added)
    assert "НС" in added
    assert connection.execute(
        "select count(*) from teachers where name = 'НС'"
    ).fetchone()[0] == 1


def test_a_composite_receiver_is_attributed_to_the_first_and_keeps_the_pair(
    connection, imported
):
    """Hole (b) of §6.  ``marks.teacher_id`` is one column, so the pair goes in ``note``.

    Nothing is lost: the second name is machine-readable, so a later migration adding a
    proper ``mark_authors`` table can reconstruct every pair without re-reading the book.
    """
    assert imported.composite_marks > 0
    row = connection.execute(
        "select t.name as teacher, m.note as note from marks m "
        "  join teachers t on t.id = m.teacher_id "
        "  join students st on st.id = m.student_id "
        " where st.surname = 'Второва' limit 1"
    ).fetchone()
    assert row["teacher"] == "Борис Петрович"
    assert "соавтор: Ольга Александровна" in row["note"]
