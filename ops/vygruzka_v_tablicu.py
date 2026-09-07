"""Nightly conduit -> the owner's Google Sheet, through the SAME projection as export_xlsx.py.

WHY THIS EXISTS.  ``ops/rezervnaya_kopia.py`` snapshots the database locally and, by design,
sends nothing out (see that file's own docstring: "that absence is the feature").  Every copy
of the conduit therefore lives on one machine, and that machine dying loses a school year of
check-offs -- it has happened once already, and there was nothing to restore from.  This tool
is the one door that leaves: it writes the conduit into a spreadsheet in the owner's own
Google account, readable by every teacher, so "is this year's version still moving, are there
new pluses" is a question anyone can answer from a browser tab, not a question that needs this
server.

IT DOES NOT RECOMPUTE THE PROJECTION OR INVENT THE ALPHABET.  Both come from
``tools.export_xlsx``: the same ``open_read_only`` connection, the same ``SIGN`` mapping of
``VALUE_REGISTRY`` (``tools/import_konduit.py``), the same ``ProgressService.states_for_many``
call the screen and the xlsx export both go through.  A second implementation of either is a
second opinion about what a plus means, and the day the two disagree the teacher believes the
screen while the spreadsheet believes something else.

CELL A1 OF EVERY SHEET CARRIES TODAY'S DATE.  Without it a stopped export and a running one
render identically, and the whole point of the exercise -- "any worried person can look and
see whether anything moved" -- silently stops meaning anything.

ONLY THIS YEAR'S LISTKI GO TO THE TABLE, not the full catalogue -- see
``academic_year_start`` below for exactly where the line is drawn and why.

DRY-RUN BY DEFAULT.  Without ``--primenit`` this reads the live database, prints what it would
write to every sheet, and does not touch the network. ``--primenit`` performs the real writes.

    python3 ops/vygruzka_v_tablicu.py                      # probe against the live database
    python3 ops/vygruzka_v_tablicu.py --primenit            # write for real
"""

# TOOL-CONTRACT: called-by-hand
#
# Declared rather than left silent: `git_zona.py vlit-v-osnovnuyu` reports this file as
# "влито, но не встроено" -- its cross-repo `has_live_trigger` scan only greps disciplina's
# own `_generator/tools` and `.githooks`, so it cannot see this repo's `deploy/*.service`
# ExecStart lines. The real live call point IS one: `deploy/spetsmat-vygruzka-v-tablicu.service`
# runs `--primenit` nightly, and a person types the bare form for the probe.

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from core.services.progress import ProgressService
from infra.repositories import SqliteCatalogue, SqliteMarkJournal
from tools.export_xlsx import DatabaseMissing, NAME_HEADER, SIGN, open_read_only

#: Where the real secret sits.  Named by the owner at the interview (2026-09-07); this
#: constant is a coordinate, not the secret itself, and the file it names never comes
#: near git (``secrets/`` is .gitignore line 2).
DEFAULT_KEY_PATH = config.ROOT / "secrets" / "psychic-heading-495410-u7-e4d4bd56d890.json"

#: The owner's spreadsheet, already shared with the service account as Editor (07.09).
#: Overridable with ``--tablica`` so a forced-failure test can point at a bad id without
#: editing this file.
SPREADSHEET_ID = "1ZQzvk0r-_oojZTcub--md7wpyPLxVq8mb9AihdCg0lw"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

#: Row 1, column 1 of every sheet.  See the module docstring: this is the whole reason a
#: stopped export is distinguishable from a running one.
UPDATED_LABEL = "обновлено"


class KeyMissing(Exception):
    """The service-account key is not where it was told to be.  Said in words."""


def academic_year_start(today: Optional[date] = None) -> str:
    """The ISO date the current school year began: this Sept 1 from September onward,
    last Sept 1 the rest of the year.

    ONLY THIS YEAR'S SHEETS GO TO THE TABLE -- named twice by the owner (07.09), both
    times anchored to a concrete count (3 of 21 at assembly): a `sheets` table older than
    a year is frozen (the school year is over, nothing about it will move again), and the
    whole point of the export is "are there new pluses, new листки" -- a question about
    what is still moving, not the full archive. ``tools.export_xlsx`` remains the place
    that exports everything; this tool exports the slice that changes.
    """
    today = today or datetime.now(timezone.utc).date()
    year = today.year if today.month >= 9 else today.year - 1
    return date(year, 9, 1).isoformat()


def _tab_title(number: str) -> str:
    """Sheets forbids ``[]:*?/\\`` too and truncates further than Excel does; keeping the
    tighter Excel limit from ``tools.export_xlsx._tab_title`` here means one naming rule
    works for both destinations instead of two that can drift apart."""
    title = str(number)
    for forbidden in "[]:*?/\\":
        title = title.replace(forbidden, "-")
    return title[:31] or "?"


def build_sheet_rows(connection) -> dict[str, list[list[str]]]:
    """``{sheet_number: rows}`` -- row 0 the date stamp, row 1 the header, the rest data.

    One sheet per листок, students down, problems across -- identical layout to
    ``tools.export_xlsx.export``, offset by the one extra row the date stamp needs.
    """
    catalogue = SqliteCatalogue(connection)
    journal = SqliteMarkJournal(connection)
    progress = ProgressService(journal, catalogue)

    students = catalogue.students()
    student_ids = [student.id for student in students]
    stamp = "%s: %s" % (
        UPDATED_LABEL, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    )

    cutoff = academic_year_start()
    grids = {}
    for sheet in catalogue.sheets():
        if sheet.issued_at < cutoff:
            continue
        problems = catalogue.problems_of_sheet(sheet.id)
        header = [NAME_HEADER] + [problem.label for problem in problems]
        rows = [[stamp], header]

        states = progress.states_for_many(student_ids, [p.id for p in problems])
        for student in students:
            row = ["%s %s" % (student.surname, student.name)]
            for problem in problems:
                row.append(SIGN[states[(student.id, problem.id)]])
            rows.append(row)
        grids[sheet.number] = rows
    return grids


def describe(grids: dict) -> list[str]:
    """One line per sheet -- the probe's entire output, and what ``--primenit`` also prints
    before it writes."""
    lines = []
    for number, rows in grids.items():
        data_rows = rows[2:]
        non_empty = sum(1 for row in data_rows for cell in row[1:] if cell)
        width = len(rows[1])
        lines.append(
            "лист %-6s: строк %d, столбцов %d, непустых клеток %d"
            % (_tab_title(number), len(data_rows), width, non_empty)
        )
    return lines


def _credentials(key_path: Path):
    from google.oauth2.service_account import Credentials

    if not key_path.exists():
        raise KeyMissing(
            "нет ключа сервисного аккаунта: %s\n"
            "ключ живёт вне git (secrets/ в .gitignore) и не появляется в свежем "
            "checkout сам -- его кладут на сервер отдельно, по ssh." % key_path
        )
    return Credentials.from_service_account_file(str(key_path), scopes=SCOPES)


def _service(key_path: Path):
    from googleapiclient.discovery import build

    return build("sheets", "v4", credentials=_credentials(key_path), cache_discovery=False)


def _existing_titles(service, spreadsheet_id: str) -> set[str]:
    metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    return {sheet["properties"]["title"] for sheet in metadata.get("sheets", [])}


def _ensure_sheets(service, spreadsheet_id: str, titles: list[str]) -> None:
    """Add any worksheet the spreadsheet does not have yet.  Never removes one: a листок
    that leaves the catalogue should not silently vanish from the audit trail too."""
    have = _existing_titles(service, spreadsheet_id)
    missing = [title for title in titles if title not in have]
    if not missing:
        return
    requests = [{"addSheet": {"properties": {"title": title}}} for title in missing]
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"requests": requests}
    ).execute()


def write_sheets(service, spreadsheet_id: str, grids: dict) -> None:
    """Clear each sheet, then write its grid in one batch.

    Cleared first: a листок that shrank overnight (fewer problems, fewer students) must
    not leave last night's cells stranded past the new grid's edge, where they would read
    as marks nobody actually made.
    """
    titles = [_tab_title(number) for number in grids]
    _ensure_sheets(service, spreadsheet_id, titles)

    for number in grids:
        title = _tab_title(number)
        service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id, range="'%s'!A1:ZZ" % title
        ).execute()

    data = [
        {"range": "'%s'!A1" % _tab_title(number), "values": rows}
        for number, rows in grids.items()
    ]
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"valueInputOption": "RAW", "data": data},
    ).execute()


def main(argv=None) -> int:
    """Returns an exit code, ALWAYS -- see tools/export_xlsx.py and tools/import_konduit.py
    for why that is stated rather than assumed in this codebase."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--primenit", action="store_true",
                        help="писать в таблицу по-настоящему; без флага -- только проба")
    parser.add_argument("--baza", type=Path, default=None,
                        help="путь к базе; по умолчанию config.DB_PATH")
    parser.add_argument("--klyuch", type=Path, default=DEFAULT_KEY_PATH,
                        help="путь к ключу сервисного аккаунта")
    parser.add_argument("--tablica", default=SPREADSHEET_ID,
                        help="id таблицы; по умолчанию таблица владельца "
                             "(перекрывается для теста принудительного провала)")
    arguments = parser.parse_args(argv)

    try:
        connection = open_read_only(arguments.baza)
    except DatabaseMissing as error:
        print(error, file=sys.stderr)
        return 3

    try:
        grids = build_sheet_rows(connection)
    finally:
        connection.close()

    for line in describe(grids):
        print(line)

    if not arguments.primenit:
        print("ПРОБА: в таблицу ничего не записано; для записи -- --primenit")
        return 0

    try:
        service = _service(arguments.klyuch)
        write_sheets(service, arguments.tablica, grids)
    except KeyMissing as error:
        print(error, file=sys.stderr)
        return 4

    print("записано в таблицу %s" % arguments.tablica)
    return 0


if __name__ == "__main__":
    sys.exit(main())
