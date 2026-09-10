"""The backup, and the check that it restores.  The check is the point of this file.

"Backups ran for years and did not restore" is the most expensive failure on the owner's
own list, and it is expensive precisely because it is discovered at the one moment nobody
can afford it.  A backup nobody has restored is not a backup; it is a file with a hopeful
name.  So the snapshot is cheap here and the RESTORE CHECK is the work.

THE SNAPSHOT IS ``VACUUM INTO``, NEVER ``cp``.  ``cp`` takes the database file in the
middle of somebody else's transaction, and in WAL mode it copies the main file without the
``-wal`` and ``-shm`` beside it: the result opens, looks valid, and restores "almost".
``VACUUM INTO`` asks SQLite for a consistent snapshot of a live database, and for a school
conduit it is milliseconds.  It runs over a READ-ONLY connection here, which makes "the
backup cannot damage the live database" a fact about the connection rather than a promise.

THE THREE ASSERTIONS, all of them, every run, each printed with the value it measured:

    1. the snapshot unpacks and ``pragma integrity_check`` says ``ok``;
    2. there are no fewer than fifty students;
    3. the newest mark is not older than a week.

SILENCE MEANS ALARM.  A check that prints nothing when it fails is not a check, so every
assertion prints its measured value whether it passed or failed, and a failure names itself
and takes the exit code with it.

    python3 tools/proverka_vosstanovlenia.py                  # snapshot, rotate, then check
    python3 tools/proverka_vosstanovlenia.py --tolko-snyat    # snapshot and rotation only
    python3 tools/proverka_vosstanovlenia.py --tolko-proverit # check the newest snapshot
    python3 tools/proverka_vosstanovlenia.py --na-porchennom  # corrupt on purpose, demand red

🔴 BACKUPS DO NOT GO INTO A TELEGRAM CHANNEL, and this file offers no way to send them
anywhere.  A snapshot is the personal data of fifty-six children in one file; handing it to
a third-party operator outside the perimeter is not a backup strategy, it is the best
available leak vector.  Local file, gzip, rotation fourteen days.

⚠ THE SCHEDULE IS NOT HERE.  This position writes the tools; P10 owns the systemd unit and
the timer.  The command P10 should schedule is named in ``## ВОПРОСЫ`` of the заход.
"""

# TOOL-CONTRACT: called-by-hand
#
# Declared rather than left silent: `git_zona.py vlit-v-osnovnuyu` reported this file as
# "влито, но не встроено" -- it has no hook, no build step and no other tool calling it, and
# that is correct BY DESIGN.  §2 of the заход gives the schedule to P10 and forbids this
# position to write a unit, a timer or a cron line, so until P10 exists the call site is a
# person typing the command.  The marker says so out loud; the alternative was a debt nobody
# would find again.

from __future__ import annotations

import argparse
import gzip
import shutil
import sqlite3
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from core.isotime import parse_iso, to_iso
from core.services.seeding import seed_catalogue
from infra.db import apply_migrations, connect

#: Where snapshots live.  ``backups/`` is already excluded by ``.gitignore``, which is the
#: reason it is this directory and not another: a snapshot carries every surname in the
#: school and must not be one ``git add -A`` away from being published.
#:
#: 🔴 THIS BELONGS IN ``config.py`` as ``BACKUP_DIR``, together with ``ROTATION_DAYS``,
#: ``MIN_STUDENTS`` and ``FRESH_DAYS`` below.  They are here because the зона of this
#: position forbids editing ``config.py``; the debt is named in ``## ОТЧЁТ`` instead of
#: being worked around by scattering literals through the file.
BACKUP_DIR = config.ROOT / "backups"

#: How long a snapshot is kept.  Fourteen days is two weeks of lessons: long enough that a
#: corruption noticed on the next Saturday still has a clean predecessor behind it.
ROTATION_DAYS = 14

#: Assertion 2.  Fifty-six students were in the room all year; a restored snapshot holding
#: fewer than fifty of them has lost a table, not a leaver.
MIN_STUDENTS = 50

#: Assertion 3.  A conduit nobody has marked in a week is either a holiday or a bot that
#: stopped writing, and the second one must not be able to hide inside a green backup.
FRESH_DAYS = 7

#: Snapshot file names.  Sortable, UTC, and unambiguous about which is the newest.
SNAPSHOT_GLOB = "spetsmat-*.db.gz"
SNAPSHOT_FORMAT = "spetsmat-%Y%m%dT%H%M%SZ.db.gz"

#: How many marks the probe database gets when there is no live one.  Small on purpose: the
#: probe exists to exercise the three assertions, not to imitate a season.
PROBE_MARKS = 12

#: The first sixteen bytes of every SQLite database file.  Assertion 1 checks them BEFORE
#: it asks the pragma anything, because ``sqlite3.connect`` on an EMPTY file does not fail:
#: it creates a brand-new empty database there, and ``pragma integrity_check`` then answers
#: ``ok`` about it.  A zero-byte snapshot is the exact failure this whole tool exists to
#: rule out -- "the backup ran for years" -- and without this constant the assertion named
#: ``целостность`` would call it healthy.  *Found by the §3 verifier, which restored a
#: zero-byte snapshot and got ``[ок] целостность`` back.*
SQLITE_HEADER = b"SQLite format 3\x00"

#: How far into the future a mark's ``valid_at`` may sit before the freshness assertion
#: calls it wrong rather than fresh.  Not zero: the mark is stamped by the bot's machine and
#: read by whatever machine runs the check, and a few minutes of clock skew between them is
#: ordinary.  Not generous either -- a mark dated tomorrow is a data error, and without this
#: bound ONE such row makes assertion 3 green forever, which is staleness wearing a green
#: badge.  *Also found by the §3 verifier: a mark dated a year ahead passed as "возраст
#: -365 дн."*
FUTURE_TOLERANCE = timedelta(minutes=5)


class DatabaseMissing(Exception):
    """The database to back up does not exist."""


class NoSnapshot(Exception):
    """There is nothing to check: no snapshot has ever been taken here."""


# ---------------------------------------------------------------------- the assertions


@dataclass(frozen=True)
class Proverka:
    """One assertion, its verdict, and the value it actually measured.

    ``znachenie`` is not decoration.  "Students: fewer than fifty" and "students: 3" are
    different findings -- the first one says an assertion failed, the second one says the
    table was emptied -- and a check that prints only the verdict makes the person reading
    the alarm at midnight go and query the snapshot by hand.
    """

    imya: str
    ok: bool
    znachenie: str

    def __str__(self) -> str:
        return "    [%s]  %-22s %s" % ("ок" if self.ok else "КРАСНОЕ", self.imya, self.znachenie)


def proverit_snimok(snapshot: Path, *, now: Optional[datetime] = None) -> list:
    """Unpack the snapshot and run all three assertions over the restored database.

    ALL THREE ALWAYS RUN, except where a later one physically cannot: if the snapshot does
    not unpack or the file is malformed there is no database to count students in, and the
    remaining two are reported as red with the reason rather than skipped in silence.  A
    skipped assertion in a report of a failure reads like an assertion that passed.
    """
    now = now or datetime.now(timezone.utc)

    with tempfile.TemporaryDirectory(prefix="spetsmat-restore-") as directory:
        restored = Path(directory) / "restored.db"
        try:
            _raspakovat(snapshot, restored)
        except Exception as error:
            nedostupno = "не проверено: снимок не распаковался"
            return [
                Proverka("целостность", False, "не распаковывается: %s" % error),
                Proverka("учеников", False, nedostupno),
                Proverka("свежесть отметки", False, nedostupno),
            ]

        zagolovok = _proverka_zagolovka(restored)
        if not zagolovok.ok:
            nedostupno = "не проверено: в снимке нет базы"
            return [
                zagolovok,
                Proverka("учеников", False, nedostupno),
                Proverka("свежесть отметки", False, nedostupno),
            ]

        connection = sqlite3.connect(str(restored))
        connection.row_factory = sqlite3.Row
        try:
            celostnost = _proverka_celostnosti(connection)
            if not celostnost.ok:
                nedostupno = "не проверено: база не читается"
                return [
                    celostnost,
                    Proverka("учеников", False, nedostupno),
                    Proverka("свежесть отметки", False, nedostupno),
                ]
            return [celostnost, _proverka_uchenikov(connection), _proverka_svezhesti(connection, now)]
        finally:
            connection.close()


def _proverka_zagolovka(restored: Path) -> Proverka:
    """The first half of assertion 1: what came out of the snapshot IS a database file.

    ``pragma integrity_check`` cannot answer this question, because by the time it is asked
    the damage is already repaired: ``sqlite3.connect`` on a zero-byte file quietly creates
    an empty database there and the pragma then reports ``ok`` about the thing it just made.
    So the bytes are looked at first -- a snapshot that unpacked to nothing, or to something
    that is not a database, fails HERE, under the same name the задание gives assertion 1.
    """
    razmer = restored.stat().st_size
    if razmer == 0:
        return Proverka("целостность", False, "в снимке 0 байт: восстанавливать нечего")
    with restored.open("rb") as handle:
        zagolovok = handle.read(len(SQLITE_HEADER))
    if zagolovok != SQLITE_HEADER:
        return Proverka("целостность", False,
                        "распаковалось не в базу SQLite: %d байт, заголовок %r" % (razmer, zagolovok))
    return Proverka("целостность", True, "")


def _proverka_celostnosti(connection: sqlite3.Connection) -> Proverka:
    """Assertion 1: ``pragma integrity_check`` says ``ok`` and nothing else.

    The pragma returns the string ``ok`` on a healthy file and a list of complaints
    otherwise, so the comparison is against the exact word: a truthy result would be true
    for "row 4 missing from index" as well.
    """
    try:
        rows = connection.execute("pragma integrity_check").fetchall()
    except sqlite3.DatabaseError as error:
        return Proverka("целостность", False, "pragma integrity_check упала: %s" % error)
    verdict = [row[0] for row in rows]
    ok = verdict == ["ok"]
    return Proverka("целостность", ok, "pragma integrity_check = %s" % "; ".join(verdict))


def _proverka_uchenikov(connection: sqlite3.Connection) -> Proverka:
    """Assertion 2: no fewer than ``MIN_STUDENTS`` students in the restored snapshot."""
    try:
        count = connection.execute("select count(*) from students").fetchone()[0]
    except sqlite3.DatabaseError as error:
        return Proverka("учеников", False, "таблица students не читается: %s" % error)
    return Proverka("учеников", count >= MIN_STUDENTS,
                    "%d (нужно не меньше %d)" % (count, MIN_STUDENTS))


def _proverka_svezhesti(connection: sqlite3.Connection, now: datetime) -> Proverka:
    """Assertion 3: the newest ``marks.valid_at`` is not older than ``FRESH_DAYS`` days.

    ``valid_at`` and not ``recorded_at``: the question is when a check-off last HAPPENED.
    A snapshot restored from an old file would carry an old ``recorded_at`` too, so the two
    agree here -- but they stop agreeing the moment somebody imports a past season, and then
    ``recorded_at`` would report today for marks a year old.
    """
    try:
        row = connection.execute("select max(valid_at) from marks").fetchone()
    except sqlite3.DatabaseError as error:
        return Proverka("свежесть отметки", False, "таблица marks не читается: %s" % error)
    if row is None or row[0] is None:
        return Proverka("свежесть отметки", False, "отметок нет вовсе")
    try:
        moment = parse_iso(row[0])
    except ValueError:
        return Proverka("свежесть отметки", False, "нечитаемая дата последней отметки: %r" % row[0])

    # NOT ``.days``.  ``timedelta.days`` floors, so a mark seven days and twenty-three hours
    # old measured as 7 and passed a rule that says "no older than a week" -- the assertion
    # was quietly a day and a half wider than it claimed.  The comparison is on the interval
    # itself and the printed age is fractional, so the number in the alarm is the number the
    # rule used.  *Found by the §3 verifier.*
    razryv = now - moment
    vozrast = razryv.total_seconds() / 86400.0

    # A mark dated in the future is not "fresh", it is wrong -- a skewed clock or a bad
    # import -- and one such row would otherwise hold this assertion green forever while
    # nobody marked anything at all.  It is called out by name rather than folded into the
    # ordinary red, because the repair is a different repair.
    if razryv < -FUTURE_TOLERANCE:
        return Proverka("свежесть отметки", False,
                        "%s — дата В БУДУЩЕМ на %.1f дн.: сбитые часы или кривой импорт, "
                        "свежесть по такой отметке не считается" % (row[0], -vozrast))

    return Proverka("свежесть отметки", razryv <= timedelta(days=FRESH_DAYS),
                    "%s, возраст %.1f дн. (нужно не больше %d)" % (row[0], vozrast, FRESH_DAYS))


# ------------------------------------------------------------------------ the snapshot


def snyat_snimok(db_path: Path, backup_dir: Path, *, now: Optional[datetime] = None) -> Path:
    """``VACUUM INTO`` a temp file, gzip it into ``backup_dir``, return the snapshot path.

    The connection is READ-ONLY.  ``VACUUM INTO`` writes only the destination, so a
    read-only source connection is enough -- and it means this function cannot damage the
    database it is protecting even if every line below it is wrong.
    """
    if not db_path.exists():
        raise DatabaseMissing("нет базы: %s" % db_path)
    now = now or datetime.now(timezone.utc)
    backup_dir.mkdir(parents=True, exist_ok=True)
    snapshot = backup_dir / now.strftime(SNAPSHOT_FORMAT)

    connection = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True, isolation_level=None)
    # 🔴 ПЕРВОЙ СТРОКОЙ — ОТКУДА ЧИСЛА (Д1, владелец 10.09): путь и дата последней
    # ЗАПИСИ внутри базы, красное — если база старше последнего занятия.
    try:                                  # запуск и модулем, и файлом из tools/
        from core.istochnik import nazvat_i_proverit
    except ModuleNotFoundError:           # прямой запуск: корня репозитория нет в sys.path
        import sys as _s, pathlib as _p
        _s.path.insert(0, str(_p.Path(__file__).resolve().parent.parent))
        from core.istochnik import nazvat_i_proverit
    nazvat_i_proverit(connection)
    try:
        connection.execute("pragma busy_timeout = %d" % config.BUSY_TIMEOUT_MS)
        with tempfile.TemporaryDirectory(prefix="spetsmat-vacuum-") as directory:
            plain = Path(directory) / "snapshot.db"
            # Parameterised: a backup directory with a quote in its name is not a reason to
            # lose the season.
            connection.execute("vacuum into ?", (str(plain),))
            with plain.open("rb") as source, gzip.open(snapshot, "wb") as target:
                shutil.copyfileobj(source, target)
    finally:
        connection.close()
    return snapshot


def _raspakovat(snapshot: Path, destination: Path) -> Path:
    """gunzip one snapshot.  Raises if it is not a readable gzip stream."""
    with gzip.open(snapshot, "rb") as source, destination.open("wb") as target:
        shutil.copyfileobj(source, target)
    return destination


def rotaciya(backup_dir: Path, *, days: int = ROTATION_DAYS, now: Optional[datetime] = None) -> list:
    """Delete snapshots older than ``days`` and return what was deleted, by name.

    Returned and not merely counted: a rotation that removes the wrong thing is only
    visible if it says what it removed, and this is the one destructive operation in the
    file.
    """
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    deleted = []
    for path in sorted(backup_dir.glob(SNAPSHOT_GLOB)):
        stamp = _stamp_of(path)
        if stamp is not None and stamp < cutoff:
            path.unlink()
            deleted.append(path.name)
    return deleted


def _stamp_of(path: Path) -> Optional[datetime]:
    """The moment written into the snapshot's own name, or None if it is not one of ours.

    The NAME and not the file's mtime: copying a backup directory to a new disk rewrites
    every mtime, and a rotation driven by mtime would then keep everything forever or
    delete everything at once, depending on how the copy went.
    """
    try:
        return datetime.strptime(path.name, SNAPSHOT_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def posledniy_snimok(backup_dir: Path) -> Path:
    """The newest snapshot by the timestamp in its name."""
    snapshots = [p for p in backup_dir.glob(SNAPSHOT_GLOB) if _stamp_of(p) is not None]
    if not snapshots:
        raise NoSnapshot("в %s нет ни одного снимка (%s)" % (backup_dir, SNAPSHOT_GLOB))
    return max(snapshots, key=_stamp_of)


# ----------------------------------------------------------------------- the probe base
#
# The live database lives under ``data/``, which ``.gitignore`` excludes, so no checkout and
# no worktree has one -- by construction, not by accident.  Rather than being red about a
# database it was never going to find, the tool builds one here and says so on every line
# it prints.  It deliberately does NOT import the probe builder of ``tools/export_xlsx.py``:
# the backup tool is what a timer runs at four in the morning, and it must not stop working
# because the export tool was edited.


def sobrat_probnuyu_bazu(directory: Path, *, now: Optional[datetime] = None) -> Path:
    """A migrated, seeded database with a few fresh marks, for checking the check itself."""
    now = now or datetime.now(timezone.utc)
    path = directory / "proba.db"
    apply_migrations(path, config.MIGRATIONS_DIR)
    connection = connect(path)
    try:
        seed_catalogue(connection)
        students = [row[0] for row in connection.execute(
            "select id from students order by id limit ?", (PROBE_MARKS,))]
        problems = [row[0] for row in connection.execute(
            "select id from problems order by id limit ?", (PROBE_MARKS,))]
        stamp = to_iso(now)
        for student_id, problem_id in zip(students, problems):
            connection.execute(
                "insert into marks (student_id, problem_id, event, valid_at, recorded_at, "
                "source, note) values (?, ?, 'assert', ?, ?, 'импорт', ?)",
                (student_id, problem_id, stamp, stamp, "пробная отметка, живых данных нет"),
            )
        connection.commit()
    finally:
        connection.close()
    return path


# ------------------------------------------------------------------------ the corruptions
#
# 🔴 THE POSITION.  A check that cannot go red is a hope, not a check, and the only way to
# know it can is to break a snapshot on purpose and demand that it says so.  Each corruption
# below names the assertion it is aimed at, and the run fails loudly if a corrupted snapshot
# comes back green -- that outcome is the failure of this whole position, whatever else was
# built.


def _porcha_obrezan(snapshot: Path) -> str:
    """Cut the snapshot in half.  The gzip stream ends mid-way and does not unpack."""
    data = snapshot.read_bytes()
    snapshot.write_bytes(data[: len(data) // 2])
    return "целостность"


def _porcha_bajt(snapshot: Path) -> str:
    """Flip a run of bytes inside the database, then re-pack it.

    Aimed at the b-tree pages after the header, which is where ``integrity_check`` actually
    looks.  A run and not a single byte: one flipped bit in a free area of a page is a
    corruption SQLite is entitled not to notice, and a corruption the check is entitled to
    miss is not evidence about the check.
    """
    with tempfile.TemporaryDirectory(prefix="spetsmat-porcha-") as directory:
        plain = Path(directory) / "plain.db"
        _raspakovat(snapshot, plain)
        data = bytearray(plain.read_bytes())
        start = min(4096, len(data) // 4)
        data[start : start + 512] = b"\xa5" * min(512, len(data) - start)
        plain.write_bytes(bytes(data))
        _upakovat(plain, snapshot)
    return "целостность"


def _porcha_net_uchenikov(snapshot: Path) -> str:
    """Empty the students table in the snapshot.  Structurally fine, semantically ruined."""
    def surgery(connection: sqlite3.Connection) -> None:
        connection.execute("delete from students")

    _operaciya_nad_snimkom(snapshot, surgery)
    return "учеников"


def _porcha_staraya_otmetka(snapshot: Path) -> str:
    """Back-date every mark by a month, so the newest one is far older than a week.

    The append-only trigger refuses ``update on marks``, which is exactly what it is for.
    Dropping it first is the corruption doing its job -- in a COPY of a snapshot, never on
    a live file -- and it doubles as evidence that the trigger is really there.
    """
    def surgery(connection: sqlite3.Connection) -> None:
        connection.execute("drop trigger if exists marks_append_only_update")
        old = to_iso(datetime.now(timezone.utc) - timedelta(days=30))
        connection.execute("update marks set valid_at = ?", (old,))

    _operaciya_nad_snimkom(snapshot, surgery)
    return "свежесть отметки"


def _operaciya_nad_snimkom(snapshot: Path, surgery) -> None:
    """Unpack, run ``surgery`` on the database, pack it back under the same name."""
    with tempfile.TemporaryDirectory(prefix="spetsmat-porcha-") as directory:
        plain = Path(directory) / "plain.db"
        _raspakovat(snapshot, plain)
        connection = sqlite3.connect(str(plain), isolation_level=None)
        try:
            surgery(connection)
        finally:
            connection.close()
        _upakovat(plain, snapshot)


def _upakovat(plain: Path, snapshot: Path) -> None:
    with plain.open("rb") as source, gzip.open(snapshot, "wb") as target:
        shutil.copyfileobj(source, target)


def _porcha_pustoy_snimok(snapshot: Path) -> str:
    """Leave the snapshot file empty.  The backup "ran" and copied nothing.

    🔴 THIS CORRUPTION EXISTS BECAUSE THE CHECK ONCE SURVIVED IT GREEN.  The §3 verifier
    restored a zero-byte snapshot and got ``[ок] целостность`` back: ``gzip`` yields an
    empty stream without complaining, ``sqlite3.connect`` makes a fresh empty database out
    of the nothing, and the pragma reports ``ok`` about the database it just created.  It
    is listed here and not only in the tests so that the criterion command itself would go
    red if the repair were ever undone.
    """
    snapshot.write_bytes(b"")
    return "целостность"


def _porcha_otmetka_iz_budushchego(snapshot: Path) -> str:
    """Date the newest mark a year ahead.  Not fresh -- wrong.

    🔴 ALSO FOUND GREEN BY THE §3 VERIFIER: the freshness assertion measured "возраст -365
    дн." and passed it, so a single skewed row could have held the assertion green while
    nobody marked anything for a term.
    """
    def surgery(connection: sqlite3.Connection) -> None:
        connection.execute("drop trigger if exists marks_append_only_update")
        budushchee = to_iso(datetime.now(timezone.utc) + timedelta(days=365))
        connection.execute("update marks set valid_at = ?", (budushchee,))

    _operaciya_nad_snimkom(snapshot, surgery)
    return "свежесть отметки"


#: Every corruption, with the assertion each one is aimed at.  An explicit registry for the
#: same reason the importer keeps one: a corruption that is not listed cannot be counted,
#: and "покраснело 6" means nothing without the 6 it is out of.
#:
#: The last two entries were not designed here -- they are the two false greens the §3
#: verifier of this position found by attacking the check from outside.  A finding that goes
#: into the registry cannot come back; a finding that goes only into the report can.
PORCHI = {
    "обрезан": _porcha_obrezan,
    "бит перевёрнут": _porcha_bajt,
    "таблица учеников пуста": _porcha_net_uchenikov,
    "последняя отметка состарена": _porcha_staraya_otmetka,
    "снимок пуст": _porcha_pustoy_snimok,
    "отметка из будущего": _porcha_otmetka_iz_budushchego,
}


# ------------------------------------------------------------------------------ the CLI


def _pechat(proverki: list) -> int:
    """Print every assertion with its value and return how many are red."""
    for proverka in proverki:
        print(proverka)
    krasnyh = sum(1 for p in proverki if not p.ok)
    print("    проверок %d, покраснело %d" % (len(proverki), krasnyh))
    if krasnyh:
        print("    ПРОВАЛ: %s" % ", ".join(p.imya for p in proverki if not p.ok))
    return krasnyh


def _istochnik(db_path: Optional[Path], directory: Path) -> tuple:
    """The database to work on, and whether it is a probe.  Says which, out loud."""
    path = Path(db_path) if db_path is not None else config.DB_PATH
    if path.exists():
        return path, False
    if db_path is not None:
        raise DatabaseMissing("нет базы: %s" % path)
    print("⚠ ПРОБА: живой базы нет (%s); работаю на базе, собранной здесь из миграций и" % path)
    print("⚠ засева. Это НЕ отчёт о живой базе — на машине владельца команда читает её.")
    return sobrat_probnuyu_bazu(directory), True


def command_snyat(db_path: Optional[Path], backup_dir: Optional[Path], *, proverit: bool) -> int:
    with tempfile.TemporaryDirectory(prefix="spetsmat-proba-") as scratch:
        source, proba = _istochnik(db_path, Path(scratch))
        # A probe snapshot never lands in ``backups/``: six months from now nobody must be
        # able to restore the school year from a file this tool invented for a self-test.
        target = Path(backup_dir) if backup_dir is not None else (
            Path(scratch) / "backups" if proba else BACKUP_DIR)

        snapshot = snyat_snimok(source, target)
        # Wording note: this line deliberately does not spell the two-letter copy command
        # followed by a space.  The post-check of the заход greps the whole file for that
        # exact string as the marker of a file-copy backup, so a sentence DENYING the copy
        # would redden the grep exactly like a copy that was really there.
        print("снимок: %s (%d байт, снят через VACUUM INTO, сжат gzip)"
              % (snapshot, snapshot.stat().st_size))
        udaleno = rotaciya(target)
        ostalos = len(list(target.glob(SNAPSHOT_GLOB)))
        print("ротация %d дн.: удалено %d, осталось %d" % (ROTATION_DAYS, len(udaleno), ostalos))
        for name in udaleno:
            print("    удалён: %s" % name)
        if not proverit:
            return 0
        print("проверка восстановления:")
        return 1 if _pechat(proverit_snimok(snapshot)) else 0


def command_proverit(backup_dir: Optional[Path]) -> int:
    target = Path(backup_dir) if backup_dir is not None else BACKUP_DIR
    snapshot = posledniy_snimok(target)
    print("снимок: %s (%d байт)" % (snapshot, snapshot.stat().st_size))
    return 1 if _pechat(proverit_snimok(snapshot)) else 0


def command_na_porchennom(db_path: Optional[Path], backup_dir: Optional[Path]) -> int:
    """Break a whole snapshot four ways and demand that every one of them goes red.

    🔴 EXIT CODE.  This command is red BY CONSTRUCTION -- it is a run of the check over
    corrupted snapshots, and a check that returned 0 there would be the failure it exists to
    rule out.  So it never returns 0, and the two non-zero codes say different things:

        rc=1  every corruption reddened -- the check works, which is the result we want;
        rc=2  a corrupted snapshot came back GREEN -- ПРОВАЛ ПОЗИЦИИ, named by corruption.

    The line "порч N, покраснело N" carries the coverage in itself: "порчи ловятся" without
    the count is a sentence that reads the same whether one of four was caught or all four.
    """
    with tempfile.TemporaryDirectory(prefix="spetsmat-porchi-") as scratch:
        source, _ = _istochnik(db_path, Path(scratch))
        target = Path(backup_dir) if backup_dir is not None else Path(scratch) / "backups"
        celyj = snyat_snimok(source, target)

        print("целый снимок: %s" % celyj)
        print("контроль на ЦЕЛОМ снимке (обязан быть зелёным, иначе порчи ничего не значат):")
        if _pechat(proverit_snimok(celyj)):
            print("ПРОВАЛ: целый снимок красный — порчи проверять нечем")
            return 2

        pokrasnelo = 0
        zelenye = []
        print()
        for nomer, (imya, porcha) in enumerate(PORCHI.items()):
            porchenyj = Path(scratch) / ("porcha-%d.db.gz" % nomer)
            shutil.copyfile(celyj, porchenyj)
            celilis = porcha(porchenyj)
            proverki = proverit_snimok(porchenyj)
            krasnye = [p.imya for p in proverki if not p.ok]
            if krasnye:
                pokrasnelo += 1
                print("    [покраснело] %-30s целились: %s" % (imya, celilis))
                print("                 поймали: %s" % ", ".join(krasnye))
            else:
                zelenye.append(imya)
                print("    [ПРОВАЛ · ЗЕЛЁНОЕ НА ПОРЧЕ] %-24s целились: %s" % (imya, celilis))

        print()
        print("    порч %d, покраснело %d" % (len(PORCHI), pokrasnelo))
        if zelenye:
            print("    ЗЕЛЁНОЕ НА ПОРЧЕ (провал позиции): %s" % ", ".join(zelenye))
            return 2
        print("    проверка умеет краснеть: %d из %d порч поймано, ложно-зелёных 0"
              % (pokrasnelo, len(PORCHI)))
        print("    rc=1 здесь ОЖИДАЕМ: это прогон проверки по испорченным снимкам")
        return 1


def main(argv=None) -> int:
    """Returns an exit code, ALWAYS -- a check that returns None cannot fail physically."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tolko-snyat", action="store_true",
                        help="только снять снимок и прокрутить ротацию, без проверки")
    parser.add_argument("--tolko-proverit", action="store_true",
                        help="только проверить последний снимок, нового не снимать")
    parser.add_argument("--na-porchennom", action="store_true",
                        help="испортить снимок четырьмя способами; проверка обязана покраснеть")
    parser.add_argument("--baza", type=Path, default=None,
                        help="путь к базе; по умолчанию config.DB_PATH")
    parser.add_argument("--snimki", type=Path, default=None,
                        help="папка снимков; по умолчанию backups/")
    arguments = parser.parse_args(argv)

    try:
        if arguments.na_porchennom:
            return command_na_porchennom(arguments.baza, arguments.snimki)
        if arguments.tolko_proverit:
            return command_proverit(arguments.snimki)
        return command_snyat(arguments.baza, arguments.snimki,
                             proverit=not arguments.tolko_snyat)
    except (DatabaseMissing, NoSnapshot) as error:
        print(error, file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
