"""The SQLite connection and the migration runner.

Every pragma that matters is per-CONNECTION, not per-database: foreign keys are OFF by
default in SQLite and stay off for any connection that forgets to turn them on.  So this
module is the only place in the project that opens a connection.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional, Union

import config
from core.isotime import now_iso

PathLike = Union[str, Path]


class SystemClock:
    """The real clock.  Injected into services so that tests can hold time still."""

    def now_iso(self) -> str:
        return now_iso()


def connect(db_path: Optional[PathLike] = None) -> sqlite3.Connection:
    """Open one connection with every pragma this project depends on.

    The database must be a FILE.  ``:memory:`` is not an option: WAL does not work on an
    in-memory database with more than one connection, and the whole point of WAL here is
    that the progress screens read while marks are being written.
    """
    path = Path(db_path) if db_path is not None else config.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(path), isolation_level=None)
    connection.row_factory = sqlite3.Row

    if config.FOREIGN_KEYS:
        connection.execute("pragma foreign_keys = on")
    if config.WAL:
        connection.execute("pragma journal_mode = wal")
    connection.execute("pragma synchronous = %s" % config.SYNCHRONOUS)
    connection.execute("pragma busy_timeout = %d" % config.BUSY_TIMEOUT_MS)
    return connection


def apply_migrations(
    db_path: Optional[PathLike] = None,
    migrations_dir: Optional[PathLike] = None,
) -> list:
    """Apply every pending migration and return the ids that were applied.

    Plain SQL under yoyo-migrations.  yoyo opens its own connection and keeps its own
    bookkeeping table, so this deliberately does not reuse ``connect`` above.
    """
    from yoyo import get_backend, read_migrations

    path = Path(db_path) if db_path is not None else config.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    directory = Path(migrations_dir) if migrations_dir is not None else config.MIGRATIONS_DIR

    backend = get_backend("sqlite:///%s" % path)
    migrations = read_migrations(str(directory))
    with backend.lock():
        pending = backend.to_apply(migrations)
        applied = [migration.id for migration in pending]
        backend.apply_migrations(pending)
    return applied


def open_database(
    db_path: Optional[PathLike] = None,
    migrations_dir: Optional[PathLike] = None,
) -> sqlite3.Connection:
    """Migrate, then connect.  The one call an entry point needs."""
    apply_migrations(db_path, migrations_dir)
    return connect(db_path)
