"""Backups: ``VACUUM INTO``, gzip, local rotation.  Never ``cp``, never off-perimeter.

WHY NOT ``cp`` (finalised at the interview, and the reason is not style)
------------------------------------------------------------------------
``cp`` copies the main database file at whatever instant it happens to run, which may be
the middle of somebody else's transaction, and in WAL mode the committed data lives partly
in ``-wal`` and ``-shm`` beside it.  The copy is then a torn file plus two orphaned side
files: it opens, it looks valid, it restores "almost".  ``VACUUM INTO`` asks SQLite itself
for a consistent snapshot through a read transaction, so what lands on disk is a single
file that already contains everything committed at that instant.  For fifty-six students
it costs milliseconds.

WHERE THE BACKUPS DO **NOT** GO
-------------------------------
Not into a Telegram channel.  A snapshot carries the names of fifty-six children, and
putting it in a channel is a transfer of their personal data to a third-party operator
outside the perimeter -- and, incidentally, the best leak vector available.  This module
writes to a local directory and offers no upload of any kind; that absence is the feature.

WHEN
----
The schedule is tied to LESSONS, not to days (``ops/raspisanie.py``): one snapshot before
the lesson, one right after, one daily.  The worst loss is then one lesson, not one day.
The timers that call this live in ``deploy/``.
"""

from __future__ import annotations

import argparse
import gzip
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config  # noqa: E402  -- deliberately after the path bootstrap above

#: How long a snapshot is kept locally.
DEFAULT_KEEP_DAYS = 14

#: Where snapshots land by default.  Under ``data/`` next to the database, which
#: ``.gitignore`` already excludes -- a snapshot must never become a commit.
DEFAULT_BACKUP_DIR = config.ROOT / "data" / "backups"

#: The labels a snapshot may carry.  They are the reason the snapshot exists, and they are
#: what makes "we lost at most one lesson" checkable after the fact.  ``oblachnyj`` is the
#: one ``ops/vygruzka_bazy.py`` uses before it uploads the snapshot to Drive -- a name, not
#: a second snapshot mechanism: it goes through the exact same ``make_backup`` below.
LABELS = ("pered-zanyatiem", "posle-zanyatia", "sutochnyj", "ruchnoj", "oblachnyj")

#: ``VACUUM INTO`` arrived in SQLite 3.27 (2019).  Older library, and this module refuses
#: in plain words rather than silently falling back to a copy -- the fallback would be
#: exactly the broken backup this module exists to prevent.
MIN_SQLITE = (3, 27, 0)

SUFFIX = ".db.gz"


def _sqlite_version() -> tuple[int, int, int]:
    return tuple(int(part) for part in sqlite3.sqlite_version.split("."))[:3]


def snapshot_name(moment: datetime, label: str) -> str:
    """UTC in the name, always sortable, never ambiguous.

    The timestamp is UTC because the system clock is UTC; the Moscow reading of it is a
    display concern and belongs nowhere near a filename that gets sorted.
    """
    if label not in LABELS:
        raise ValueError("unknown label %r, expected one of %s" % (label, ", ".join(LABELS)))
    return "spetsmat-%s-%s%s" % (moment.strftime("%Y%m%dT%H%M%SZ"), label, SUFFIX)


def make_backup(
    db_path: Path | str | None = None,
    backup_dir: Path | str | None = None,
    label: str = "ruchnoj",
    moment: datetime | None = None,
) -> Path:
    """Take one consistent snapshot and return the path of the gzipped file.

    Raises rather than returning a bad path: a backup routine that reports success on a
    failure is worse than no backup routine, because it also removes the alarm.
    """
    if _sqlite_version() < MIN_SQLITE:
        raise RuntimeError(
            "sqlite %s is too old for VACUUM INTO (need >= %s); refusing to fall back to a "
            "file copy, which loses the WAL side files"
            % (sqlite3.sqlite_version, ".".join(str(part) for part in MIN_SQLITE))
        )

    database = Path(db_path) if db_path is not None else config.DB_PATH
    if not database.exists():
        raise FileNotFoundError("database %s does not exist -- nothing to back up" % database)

    directory = Path(backup_dir) if backup_dir is not None else DEFAULT_BACKUP_DIR
    directory.mkdir(parents=True, exist_ok=True)
    moment = moment or datetime.now(tz=timezone.utc)
    target = directory / snapshot_name(moment, label)

    with tempfile.TemporaryDirectory(prefix="spetsmat-vacuum-") as staging:
        plain = Path(staging) / "snapshot.db"
        connection = sqlite3.connect(str(database))
        # 🔴 ПЕРВОЙ СТРОКОЙ — ОТКУДА ЧИСЛА (Д1, владелец 10.09). Путь и дата последней
        # ЗАПИСИ внутри базы; красное, если база старше последнего занятия. Дата ФАЙЛА
        # для этого не годится: копирование и rsync её обновляют, не добавив ни строки.
        try:                                  # запуск и модулем, и файлом из tools/
            from core.istochnik import nazvat_i_proverit
        except ModuleNotFoundError:           # прямой запуск: корня репозитория нет в sys.path
            import sys as _s, pathlib as _p
            _s.path.insert(0, str(_p.Path(__file__).resolve().parent.parent))
            from core.istochnik import nazvat_i_proverit
        nazvat_i_proverit(connection)
        try:
            # The parameter cannot be bound: VACUUM INTO takes a literal.  The path is one
            # this process just built inside its own temp directory, so there is nothing
            # user-supplied to quote; the doubled quote is belt and braces.
            connection.execute("vacuum into '%s'" % str(plain).replace("'", "''"))
        finally:
            connection.close()

        # Gzip from the staging file into a ``.part`` and rename only on success.  A
        # half-written snapshot that already carries the final name is a snapshot the
        # restore check will pick as "the latest" and then fail on -- an alarm about the
        # wrong thing.
        partial = target.with_suffix(target.suffix + ".part")
        with plain.open("rb") as source, gzip.open(partial, "wb") as sink:
            shutil.copyfileobj(source, sink)
        partial.replace(target)

    return target


def rotate(backup_dir: Path | str | None = None, keep_days: int = DEFAULT_KEEP_DAYS,
           now: datetime | None = None) -> list[Path]:
    """Delete snapshots older than ``keep_days``; return what was deleted.

    Rotation reads the timestamp out of the NAME, not out of the filesystem mtime: a
    restore, an rsync or a backup of the backups rewrites mtime and would then either keep
    everything forever or delete a snapshot that is younger than it looks.
    """
    directory = Path(backup_dir) if backup_dir is not None else DEFAULT_BACKUP_DIR
    if not directory.exists():
        return []
    now = now or datetime.now(tz=timezone.utc)
    cutoff = now - timedelta(days=keep_days)

    removed = []
    for path in sorted(directory.glob("spetsmat-*" + SUFFIX)):
        stamp = _stamp_of(path)
        if stamp is None:
            # Not ours, or a name we cannot read: leave it alone.  Deleting a file whose
            # age is unknown is the one irreversible thing this module could do wrong.
            continue
        if stamp < cutoff:
            path.unlink()
            removed.append(path)
    return removed


def _stamp_of(path: Path) -> datetime | None:
    name = path.name
    if not name.startswith("spetsmat-") or not name.endswith(SUFFIX):
        return None
    parts = name[len("spetsmat-"):-len(SUFFIX)].split("-", 1)
    if len(parts) != 2:
        return None
    try:
        return datetime.strptime(parts[0], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def latest_snapshot(backup_dir: Path | str | None = None) -> Path | None:
    """The newest snapshot by the timestamp in its name, or ``None`` if there is none."""
    directory = Path(backup_dir) if backup_dir is not None else DEFAULT_BACKUP_DIR
    if not directory.exists():
        return None
    dated = [(stamp, path) for path in directory.glob("spetsmat-*" + SUFFIX)
             if (stamp := _stamp_of(path)) is not None]
    if not dated:
        return None
    return max(dated)[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Take one snapshot and rotate the old ones.")
    parser.add_argument("--metka", choices=LABELS, default="ruchnoj",
                        help="why this snapshot is being taken")
    parser.add_argument("--baza", default=None, help="database to snapshot (default: config.DB_PATH)")
    parser.add_argument("--kuda", default=None, help="directory for snapshots")
    parser.add_argument("--srok-dnej", type=int, default=DEFAULT_KEEP_DAYS,
                        help="how many days of snapshots to keep locally")
    parser.add_argument("--bez-rotacii", action="store_true", help="take the snapshot, keep everything")
    args = parser.parse_args(argv)

    try:
        target = make_backup(args.baza, args.kuda, args.metka)
    except (RuntimeError, FileNotFoundError, sqlite3.Error) as failure:
        print("backup FAILED: %s" % failure, file=sys.stderr)
        return 1

    print("backup: %s (%d bytes)" % (target, target.stat().st_size))
    if not args.bez_rotacii:
        removed = rotate(args.kuda, args.srok_dnej)
        print("rotate: removed %d snapshot(s) older than %d days" % (len(removed), args.srok_dnej))
    return 0


if __name__ == "__main__":
    sys.exit(main())
