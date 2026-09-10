"""The environment check: the things on the owner's measured list of what actually breaks.

Every assertion here is about the RUNNING machine, not about the source. ``config.py``
already says ``WAL = True`` and ``BUSY_TIMEOUT_MS = 5000``; the question this module asks
is whether a connection opened right now actually got them.  The distinction is the whole
point of the check: the pragmas are per-CONNECTION and default to off, so a future
connection opened somewhere other than ``infra.db.connect`` would be silently missing them
and the symptom would be ``database is locked`` on the one evening several teachers mark at
once -- which is to say, during a lesson.

The four checks, each from the owner's own list of real failures:

  ``pragmas``   WAL, ``busy_timeout``, foreign keys and ``synchronous`` are applied in fact;
  ``disk``      the filesystem under the database has room -- logs left at debug level after
                a debugging session fill a disk, and a full disk is how SQLite starts
                returning errors that look like corruption;
  ``certs``     the trust store has certificates that are not all expired -- on a machine
                that has not been updated for a year, TLS to Telegram stops working and the
                bot looks "silently broken" with no message anywhere;
  ``versions``  the interpreter and the SQLite library are new enough for what the harness
                relies on (``VACUUM INTO``, ``zoneinfo``).

Run it from the deploy script before a restart and from a timer afterwards.  It needs no
server: every check is local.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import ssl
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config  # noqa: E402  -- deliberately after the path bootstrap above

#: Below this the disk is treated as full.  Chosen against what actually happens: the
#: database of fifty-six students is under a megabyte, so anything that eats the disk is
#: the journal, and a journal fills the last gigabyte in hours at debug level.
MIN_FREE_BYTES = 1 * 1024 * 1024 * 1024

#: ``VACUUM INTO`` needs 3.27; ``zoneinfo`` needs Python 3.9.
MIN_SQLITE = (3, 27, 0)
MIN_PYTHON = (3, 9)

CHECK_NAMES = ("pragmas", "disk", "certs", "versions")


@dataclass(frozen=True)
class OneCheck:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class Verdict:
    checks: tuple[OneCheck, ...]

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(check.passed for check in self.checks)

    @property
    def failed_names(self) -> tuple[str, ...]:
        return tuple(check.name for check in self.checks if not check.passed)

    def report(self) -> str:
        lines = ["  %-9s %s  %s" % (c.name, "PASS" if c.passed else "RED ", c.detail) for c in self.checks]
        lines.append("verdict: %s -- passed %d of %d checks"
                     % ("GREEN" if self.passed else "RED",
                        sum(1 for c in self.checks if c.passed), len(self.checks)))
        if not self.passed:
            lines.append("red checks: %s" % ", ".join(self.failed_names))
        return "\n".join(lines)


def check_pragmas(db_path: Path | str | None = None) -> OneCheck:
    """Open a connection the way the application opens one, then interrogate it.

    ``infra.db.connect`` is the thing under test, so it is CALLED here and not reimplemented:
    a copy of its pragma list would keep passing after the original stopped setting them.
    """
    from infra.db import connect

    temporary = db_path is None
    workspace = None
    if temporary:
        # Never open the live database just to ask it a question: on a machine where the
        # bot is running this would be a second writer, and on one where it is not, it
        # would create an empty database in ``data/`` that later looks like a real one.
        workspace = tempfile.TemporaryDirectory(prefix="spetsmat-pragma-")
        db_path = Path(workspace.name) / "probe.db"
    try:
        connection = connect(db_path)
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
            journal = connection.execute("pragma journal_mode").fetchone()[0]
            busy = connection.execute("pragma busy_timeout").fetchone()[0]
            keys = connection.execute("pragma foreign_keys").fetchone()[0]
            synchronous = connection.execute("pragma synchronous").fetchone()[0]
        finally:
            connection.close()
    except sqlite3.Error as failure:
        return OneCheck("pragmas", False, "cannot open a connection: %s" % failure)
    finally:
        if workspace is not None:
            workspace.cleanup()

    wanted_synchronous = {"OFF": 0, "NORMAL": 1, "FULL": 2, "EXTRA": 3}[config.SYNCHRONOUS.upper()]
    problems = []
    if config.WAL and journal.lower() != "wal":
        problems.append("journal_mode is %r, expected 'wal'" % journal)
    if busy != config.BUSY_TIMEOUT_MS:
        problems.append("busy_timeout is %r ms, expected %d" % (busy, config.BUSY_TIMEOUT_MS))
    if config.FOREIGN_KEYS and keys != 1:
        problems.append("foreign_keys is %r, expected 1" % keys)
    if synchronous != wanted_synchronous:
        problems.append("synchronous is %r, expected %d (%s)"
                        % (synchronous, wanted_synchronous, config.SYNCHRONOUS))

    if problems:
        return OneCheck("pragmas", False, "; ".join(problems))
    return OneCheck("pragmas", True,
                    "journal_mode=%s busy_timeout=%d foreign_keys=%d synchronous=%d"
                    % (journal, busy, keys, synchronous))


def check_disk(path: Path | str | None = None, minimum: int = MIN_FREE_BYTES) -> OneCheck:
    target = Path(path) if path is not None else config.DB_PATH.parent
    while not target.exists() and target != target.parent:
        target = target.parent
    usage = shutil.disk_usage(target)
    free_gb = usage.free / (1024 ** 3)
    return OneCheck("disk", usage.free >= minimum,
                    "%.1f GiB free under %s, need >= %.1f GiB"
                    % (free_gb, target, minimum / (1024 ** 3)))


def check_certs(now: datetime | None = None) -> OneCheck:
    """Is there a trust store, and does it still contain certificates that are valid?

    Offline on purpose.  Reaching Telegram would turn a check of the machine into a check
    of the network, and the failure being guarded against -- a system left un-updated until
    its root certificates expired -- is visible in the store itself.
    """
    now = now or datetime.now(tz=timezone.utc)
    try:
        context = ssl.create_default_context()
        certificates = context.get_ca_certs()
    except (ssl.SSLError, OSError) as failure:
        return OneCheck("certs", False, "cannot load the trust store: %s" % failure)

    if not certificates:
        return OneCheck("certs", False, "the trust store is empty -- TLS to Telegram cannot work")

    valid = 0
    for certificate in certificates:
        not_after = certificate.get("notAfter")
        if not not_after:
            continue
        try:
            expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if expiry > now:
            valid += 1

    return OneCheck("certs", valid > 0,
                    "%d of %d root certificates still valid" % (valid, len(certificates)))


def check_versions() -> OneCheck:
    sqlite_version = tuple(int(part) for part in sqlite3.sqlite_version.split("."))[:3]
    problems = []
    if sys.version_info[:2] < MIN_PYTHON:
        problems.append("python %s < %s" % (".".join(map(str, sys.version_info[:2])),
                                            ".".join(map(str, MIN_PYTHON))))
    if sqlite_version < MIN_SQLITE:
        problems.append("sqlite %s < %s (VACUUM INTO)" % (sqlite3.sqlite_version,
                                                          ".".join(map(str, MIN_SQLITE))))
    if problems:
        return OneCheck("versions", False, "; ".join(problems))
    return OneCheck("versions", True, "python %s, sqlite %s"
                    % (".".join(map(str, sys.version_info[:3])), sqlite3.sqlite_version))


def check_all(db_path: Path | str | None = None) -> Verdict:
    return Verdict(checks=(check_pragmas(db_path), check_disk(), check_certs(), check_versions()))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check the running environment, not the source.")
    parser.add_argument("--baza", default=None,
                        help="probe the pragmas on this database (default: a throwaway temp file)")
    args = parser.parse_args(argv)
    verdict = check_all(args.baza)
    print(verdict.report())
    return 0 if verdict.passed else 1


if __name__ == "__main__":
    sys.exit(main())
