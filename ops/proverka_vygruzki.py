"""Verifies a ``--primenit`` run of ``ops/vygruzka_v_tablicu.py`` -- run AFTER it, by a
fresh process, never by the writer checking its own work.

WHAT "INDEPENDENT" MEANS HERE, PRECISELY.  This file does not import
``ops.vygruzka_v_tablicu`` and does not trust a word it printed.  It computes what the
table OUGHT to hold straight from the database, through ``ProgressService`` -- the one
projection every check-off in this project answers to, and re-deriving a second opinion
of what a plus means would be exactly the mistake ``tools/export_xlsx.py`` and
``tools/import_konduit.py`` both refuse in their own docstrings.  What is independent is
the READ: the actual spreadsheet is fetched back through the Sheets API, in a separate
call, and compared against that expectation cell-count by cell-count.  ``academic_year_start``
is imported, not re-guessed, for the same reason -- the boundary is a fact about the
catalogue, not a trick of the writer worth re-deriving badly.

Three things are checked, each printing both numbers side by side:

  1. sheet count: how many worksheets exist in the table vs. how many листков this
     academic year the database has;
  2. per sheet, non-empty cells: what the table holds vs. what the database implies;
  3. cell A1 of every sheet: does it carry today's UTC date.

    python3 ops/proverka_vygruzki.py                       # against the live table & db
    python3 ops/proverka_vygruzki.py --tablica <bad-id>     # forced-failure check (§6)
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from core.models import CellState
from core.services.progress import ProgressService
from infra.repositories import SqliteCatalogue, SqliteMarkJournal
from ops.vygruzka_v_tablicu import (
    DEFAULT_KEY_PATH,
    SCOPES,
    SPREADSHEET_ID,
    _tab_title,
    academic_year_start,
)
from tools.export_xlsx import DatabaseMissing, open_read_only


def expected_from_database(connection) -> dict[str, int]:
    """``{sheet_number: non_empty_cell_count}``, for this academic year's sheets only,
    computed straight from the journal through ``ProgressService`` -- nothing here reads
    or reuses anything ``vygruzka_v_tablicu.py`` built."""
    catalogue = SqliteCatalogue(connection)
    journal = SqliteMarkJournal(connection)
    progress = ProgressService(journal, catalogue)

    cutoff = academic_year_start()
    students = catalogue.students()
    student_ids = [s.id for s in students]

    counts = {}
    for sheet in catalogue.sheets():
        if sheet.issued_at < cutoff:
            continue
        problems = catalogue.problems_of_sheet(sheet.id)
        states = progress.states_for_many(student_ids, [p.id for p in problems])
        counts[sheet.number] = sum(1 for state in states.values() if state is not CellState.EMPTY)
    return counts


def read_actual_from_sheet(key_path: Path, spreadsheet_id: str, titles: list[str]) -> dict:
    """``{title: {"a1": str, "non_empty": int}}``, read straight from the Sheets API."""
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    credentials = Credentials.from_service_account_file(str(key_path), scopes=SCOPES)
    service = build("sheets", "v4", credentials=credentials, cache_discovery=False)

    actual = {}
    for title in titles:
        response = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range="'%s'!A1:ZZ" % title
        ).execute()
        rows = response.get("values", [])
        a1 = rows[0][0] if rows and rows[0] else ""
        data_rows = rows[2:] if len(rows) > 2 else []
        non_empty = sum(1 for row in data_rows for cell in row[1:] if cell)
        actual[title] = {"a1": a1, "non_empty": non_empty}
    return actual


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--baza", type=Path, default=None,
                        help="путь к базе; по умолчанию config.DB_PATH")
    parser.add_argument("--klyuch", type=Path, default=DEFAULT_KEY_PATH,
                        help="путь к ключу сервисного аккаунта")
    parser.add_argument("--tablica", default=SPREADSHEET_ID, help="id таблицы")
    arguments = parser.parse_args(argv)

    try:
        connection = open_read_only(arguments.baza)
    except DatabaseMissing as error:
        print(error, file=sys.stderr)
        return 3

    try:
        expected = expected_from_database(connection)
    finally:
        connection.close()

    titles = [_tab_title(number) for number in expected]
    try:
        actual = read_actual_from_sheet(arguments.klyuch, arguments.tablica, titles)
    except Exception as error:  # the forced-failure run (§6): any API error is a real red
        print("ОШИБКА ЧТЕНИЯ ТАБЛИЦЫ: %s" % error, file=sys.stderr)
        return 5

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    red = False

    if set(titles) != set(actual):
        red = True
    print("листов: в базе (текущий год) %d, в таблице %d" % (len(expected), len(actual)))

    for number, title in zip(expected, titles):
        want = expected[number]
        got = actual.get(title, {}).get("non_empty", -1)
        a1 = actual.get(title, {}).get("a1", "")
        a1_ok = a1.startswith("обновлено: %s" % today)
        if got != want or not a1_ok:
            red = True
        print(
            "лист %-6s: клеток в базе %d, в таблице %d%s; A1 %r%s"
            % (title, want, got, "" if got == want else " ≠≠",
               a1, "" if a1_ok else " (не сегодняшняя дата!)")
        )

    print("ВЕРДИКТ: %s" % ("КРАСНЫЙ" if red else "зелёный"))
    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main())
