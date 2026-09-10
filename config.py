"""Every constant of the bot lives here, and no constant lives anywhere else.

The owner deployed someone else's bot in 2023 and hit exactly the opposite: the exam
mode and password-free registration were switchable only inside the code, so he turned
buttons off without understanding where they led.  One known file is the cheap insurance.

Rule for anyone editing this project: if you are about to write a bare number or a bare
string that decides behaviour, it belongs in this file first and is imported from here.
"""

from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------- paths

ROOT = Path(__file__).resolve().parent

# ------------------------------------------------------------------ THE DATABASE
#
# 🔴 THE DATABASE HAS AN ADDRESS, NOT A NAME.  Until 2026-09-10 this file said
#
#     DB_PATH = ROOT / "data" / "spetsmat.db"
#
# -- a path relative to the repository.  One name, and on the server and on the owner's
# laptop it pointed at two DIFFERENT files, and it pointed SUCCESSFULLY.  Nothing ever
# failed; a phantom answered quietly instead.  The price was paid on 2026-09-10: four
# false reports to the owner ("problem 14a does not exist", "there is no session on
# 07.09", "the ticks were not entered", "title disagrees with number"), three of them
# read out of a dead local copy that called itself the database.
#
# The project had already learnt this lesson once and had not applied it here.
# ``KONDUIT_XLSX`` below is overridden by the environment and refuses in plain words,
# and its comment spells out the same price: a sandbox path baked into a tool, "a path
# that does not exist on any machine this project runs on".  The database was the last
# piece of state still addressed from the repository root.
#
# So: no default.  The environment names the file, or the tool REFUSES with a non-zero
# exit code and prints the two legal answers.  A refusal is cheap; a phantom is not.

#: The one environment variable that names the database.  There is no second name --
#: a second name would be a second source, which is the very thing being fixed.
BAZA_ENV = "SPETSMAT_BAZA"

#: The live database on the server.  Printed inside the refusal so that the reader is
#: not left guessing what to type.  It is a STRING, not a ``Path``: this machine is not
#: the server and resolving it here would say nothing.
BAZA_NA_SERVERE = "/srv/spetsmat/data/spetsmat.db"


class IstochnikNeNazvan(SystemExit):
    """Refusal: nobody said WHICH database, so there is no honest answer to give.

    🔴 IT INHERITS FROM ``SystemExit`` ON PURPOSE.  Twenty files under ``tools/``,
    ``veb/`` and ``ops/`` reach for the database.  A plain exception would print a
    traceback about ``config`` -- diagnostics for a programmer, not an answer for the
    person holding a paper conduit -- and would need a ``try/except`` bolted onto each
    of the twenty call sites, which is twenty places to forget one.  ``SystemExit``
    carrying a message prints that message to stderr, exits non-zero, and shows no
    traceback, in all twenty at once.
    """


def _tekst_otkaza() -> str:
    """The refusal, with BOTH legal answers spelled out.  A refusal that does not say
    what to do instead is just a failure with better manners."""
    return (
        "🔴 ИСТОЧНИК НЕ НАЗВАН: переменная среды %s не выставлена.\n"
        "   База больше не адресуется путём от корня репозитория: одно имя указывало\n"
        "   на разные файлы на сервере и на этой машине — и указывало успешно.\n"
        "   ДВА ЗАКОННЫХ ОТВЕТА:\n"
        "     1) боевая база живёт на сервере: %s=%s\n"
        "     2) не на сервере — сними копию ШТАТНОЙ ДВЕРЬЮ и укажи её явно:\n"
        "        SPETSMAT_BAZA=<боевая> python3 core/istochnik.py --snyat-kopiyu ~/spetsmat-kopia.db\n"
        "        %s=~/spetsmat-kopia.db\n"
        "   Боевых чисел копия не даёт и на сервере себя не заменяет — она помечена\n"
        "   внутри себя (`род: копия`), и дверь источника это печатает."
        % (BAZA_ENV, BAZA_ENV, BAZA_NA_SERVERE, BAZA_ENV)
    )


def put_bazy() -> Path:
    """The database this process is allowed to open, or a refusal.

    Asked as a FUNCTION and not stored as a constant so that the answer is taken at the
    moment of use: a test that sets the variable for one case, and a shell that exports
    it after this module was imported, both get the truth rather than whatever the
    environment happened to hold at import time.
    """
    syroj = os.environ.get(BAZA_ENV, "").strip()
    if not syroj:
        raise IstochnikNeNazvan(_tekst_otkaza())
    return Path(syroj).expanduser()


def __getattr__(imya: str):
    """``config.DB_PATH`` still exists as a name -- and now it can REFUSE.

    Twenty files already say ``config.DB_PATH``; renaming the attribute in all of them
    would be a large edit whose only effect is churn.  PEP 562 lets the name stay and
    the meaning change: the attribute is no longer a stored constant but a question,
    and a question asked with no environment set answers "I refuse, here is where the
    database actually is".
    """
    if imya == "DB_PATH":
        return put_bazy()
    raise AttributeError("module %r has no attribute %r" % (__name__, imya))

#: Where ``001_init.sql`` and its successors live.  Plain SQL under yoyo-migrations.
MIGRATIONS_DIR = ROOT / "migrations"

#: Last year's conduit, the workbook the importer reads.  It lives OUTSIDE the repository
#: and is never copied into it: it carries the names of fifty-six children, and only the
#: anonymised derived seed under ``seed/`` is allowed into git.
#:
#: The path that stood in ``tools/import_konduit.py`` before this position was
#: ``/sessions/funny-eager-bell/mnt/uploads/...`` -- a sandbox path that does not exist on
#: any machine this project runs on, so the importer could not have been run by anyone who
#: read the report that claimed it had been.  Overridable by the environment for a machine
#: that keeps the book elsewhere; the importer refuses in plain words when the file is
#: absent rather than raising a traceback about ``openpyxl``.
KONDUIT_XLSX = Path(
    os.environ.get("KONDUIT_XLSX", Path.home() / "Downloads" / "Кондуит 8КЛ.xlsx")
).expanduser()

#: The seed the importer loads before it reads a single mark: the anonymised catalogue
#: that DOES live in git.
SEED_DIR = ROOT / "seed"


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

#: Kinds of problem on a sheet.  Four of them occur in ``seed/sheets.json``; the fifth,
#: ``письменная``, comes from the sheets themselves and was added by
#: ``migrations/009_vid_pismennaya.sql``.  The sheet prints one glyph per kind: ``◦``
#: обязательная, ``†`` письменная, ``⋆`` звезда, nothing обычная.  ``двойная`` has no
#: glyph and no known meaning -- two rows carry it and it is left alone on purpose.
PROBLEM_KINDS = ("обязательная", "обычная", "звезда", "двойная", "письменная")

#: Only these kinds create a debt when they are left unsolved.  A starred problem is an
#: invitation, not an obligation.  ``письменная`` is an obligation like ``обязательная``
#: and differs from it only in HOW it is handed in -- leaving it out here would silently
#: cancel the debt on every problem the sheet marks with a dagger.
OBLIGATORY_KINDS = ("обязательная", "письменная")

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


# ------------------------------------------------------ deployment and bot identity
#
# These arrived in this file from ``bot/config_local.py``, where P3 had to leave them
# because ``config.py`` was outside her zone; her docstring said so honestly.  The home
# is single again.  ``bot/config_local.py`` stays as a re-export until its call sites
# are edited.
#
# 🔴 A SECRET NEVER TRAVELS IN GIT.  What lives here is the NAME of the environment
# variable and an empty default -- never a value.  The values live in ``secrets/bot.env``,
# which ``.gitignore`` already excludes, and reach the process through the deployment
# (systemd ``EnvironmentFile=``), not through code reading that file.

#: The token used by ``bot/__main__.py``.  Comes from the deployment env, not from
#: version control.  Empty by default so a missing env var crashes the bot at startup
#: rather than silently disabling it.
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

#: Telegram id of the owner -- the only account that sees the pending list and the only
#: one whose accept / rename / reject buttons do anything.  It is the id of a living
#: person, so it comes from the environment (``OWNER_ID``) too and not as a literal.
#: Zero by default, which matches no Telegram account and therefore grants nothing.
OWNER_TG_ID = int(os.environ.get("OWNER_ID", "") or 0)

#: Two deep-link codes that start the registration flow.  ``/start <code>`` in a private
#: chat routes to the matching handler.  Anything else lands on the no-code welcome.
DEEPLINK_CODE_STUDENT = "register-student"
DEEPLINK_CODE_TEACHER = "register-teacher"

#: The three rooms the conduit runs in.  Duplicates ``core.services.roster.ROOMS`` so
#: handlers can validate a room the user typed without importing core -- but the source
#: of truth remains the core constant.
ROOMS = ("203", "302", "303")

#: Length cap on a typed name.  ``Сергеевич`` is the realistic ceiling in Russian --
#: anything longer is almost certainly a typo, not a name.
NAME_MAX_LEN = 40
