"""Every constant of the bot lives here, and no constant lives anywhere else.

The owner deployed someone else's bot in 2023 and hit exactly the opposite: the exam
mode and password-free registration were switchable only inside the code, so he turned
buttons off without understanding where they led.  One known file is the cheap insurance.

Rule for anyone editing this project: if you are about to write a bare number or a bare
string that decides behaviour, it belongs in this file first and is imported from here.
"""

from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------- paths

ROOT = Path(__file__).resolve().parent

#: The live database.  Kept under ``data/`` because ``.gitignore`` already excludes it;
#: overridden per-connection in tests, which use a file in a temp directory.
DB_PATH = ROOT / "data" / "spetsmat.db"

#: Where ``001_init.sql`` and its successors live.  Plain SQL under yoyo-migrations.
MIGRATIONS_DIR = ROOT / "migrations"


# ------------------------------------------------------------------- sqlite runtime

#: Write-Ahead Logging.  A reader never blocks the writer, which matters because the
#: bot writes marks while the progress screens read them.  WAL needs a FILE database:
#: it does not work on ``:memory:`` with more than one connection, and that is why the
#: tests use a temp file too.
WAL = True

#: How long a connection waits on a locked database before giving up.  Two teachers
#: tapping in the same second must queue, not fail.
BUSY_TIMEOUT_MS = 5000

#: ``NORMAL`` is the documented safe pairing with WAL: it can lose the last commits on
#: a power cut but never corrupts the file.  A school bot is not worth ``FULL``.
SYNCHRONOUS = "NORMAL"

#: Foreign keys are OFF by default in SQLite and are a per-connection pragma.  Every
#: connection this project opens turns them on; a connection that forgets silently
#: accepts marks pointing at students who do not exist.
FOREIGN_KEYS = True


# -------------------------------------------------------------------------- domain

#: A problem taken by fewer than this many students is a "graveyard" problem:
#: ✓ at >= 3, ✘ at <= 2.  Measured from last year's tables, not guessed.
GRAVEYARD_THRESHOLD = 3

#: Buttons per row on the problem grid.  At five they fall below the minimum
#: comfortable thumb target (9.2-9.6 mm) on a phone held one-handed.
GRID_COLUMNS = 4

#: "Silent for three sessions running" — the length of the silence that gets noticed.
SILENT_SESSIONS = 3

#: Display timezone.  Storage is UTC, always; conversion goes through
#: ``zoneinfo.ZoneInfo(TZ_DISPLAY)`` and NEVER through ``timedelta(hours=3)``, which is
#: wrong twice a year for every country that still shifts and wrong forever for the
#: historical rows imported from previous seasons.
TZ_DISPLAY = "Europe/Moscow"


# ----------------------------------------------------------------- enumerated values
#
# These sets are the Python-side truth.  The SQL CHECK constraints in
# ``migrations/001_init.sql`` are the carrier — the database refuses a bad value even
# if every line of Python is rewritten.  ``tests/test_schema_matches_config.py`` fails
# if the two ever drift apart.
#
# The VALUES stay in Russian on purpose: they are data, fixed by the base schema and
# already present in ``seed/sheets.json`` and in last year's conduit, so renaming them
# would silently break the importer.  The three event kinds below are new and are named
# in English because they are named that way in the specification.

#: Kinds of problem on a sheet, as they occur in ``seed/sheets.json``.
PROBLEM_KINDS = ("обязательная", "обычная", "звезда", "двойная")

#: Only these kinds create a debt when they are left unsolved.  A starred problem is an
#: invitation, not an obligation.
OBLIGATORY_KINDS = ("обязательная",)

#: The three kinds of journal event.  The distinction comes from accounting (сторно) and
#: from FHIR; a single ``deleted`` flag destroys it.
#:
#:   ``assert``  — the mark was given;
#:   ``retract`` — it was there and was taken away (the student did not defend it);
#:                 counts in statistics as "handed in, not credited";
#:   ``erratum`` — the record should never have existed (wrong button); struck out of
#:                 statistics, still visible in the journal.
MARK_EVENTS = ("assert", "retract", "erratum")

#: Events that reverse an earlier event and therefore must carry ``reverses_id``.
REVERSING_EVENTS = ("retract", "erratum")

#: Where a mark came from.  ``импорт`` is how last year's conduit arrives (P2).
MARK_SOURCES = ("кнопка", "фото", "голос", "импорт")

#: Kinds of session.
SESSION_KINDS = ("обычное", "зачёт", "отменённое")

#: Registration lifecycle of a student.
STUDENT_STATUSES = ("pending", "active", "left")

#: Attendance of one student at one session.
ATTENDANCE_STATUSES = ("был", "не был")


# --------------------------------------------------------- open-ended validity in SCD2

#: ``enrollment`` is a Type 2 slowly-changing dimension: a row is valid over the
#: half-open interval ``[valid_from, valid_to)``.  The still-open row carries this
#: sentinel instead of NULL.  With NULL the partial unique index that forbids two open
#: rows for one (student, weekday) does not fire — NULLs never compare equal — and every
#: query has to grow an ``or valid_to is null`` branch that someone eventually forgets.
OPEN_END_DATE = "9999-12-31"

#: ISO-8601 weekday numbers, Monday = 1.  An enrollment is per LESSON DAY: the same
#: student can have one teacher on Monday and another on Thursday (last year:
#: kakhiani = vanya on mon, yan on thu).
WEEKDAY_MIN = 1
WEEKDAY_MAX = 7
