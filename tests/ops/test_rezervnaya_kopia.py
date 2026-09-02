"""Backups: that the snapshot is CONSISTENT, and that rotation cannot eat the wrong file."""

from __future__ import annotations

import gzip
import shutil
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from infra.db import connect
from ops import rezervnaya_kopia


def _code_without_prose(path: Path) -> str:
    """The source with every comment and every string literal removed.

    Tokenising is the only honest way to ask "does this module CALL the network?" -- a
    plain grep answers "does this module MENTION the network?", and the two differ by
    exactly the documentation that forbids it.
    """
    import io
    import tokenize

    kept = []
    with path.open("rb") as handle:
        for token in tokenize.tokenize(handle.readline):
            if token.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            kept.append(token.string)
    return " ".join(kept)


def _unpack(archive: Path, into: Path) -> Path:
    plain = into / "restored.db"
    with gzip.open(archive, "rb") as source, plain.open("wb") as sink:
        shutil.copyfileobj(source, sink)
    return plain


def test_snapshot_is_complete_without_the_wal_side_files(zhivaya_baza, papka_kopij, tmp_path):
    """The failure ``cp`` produces, reproduced deliberately and then shown not to happen.

    A writer connection is left open with data committed but not checkpointed, so the
    newest rows live in ``-wal`` and not yet in the main file.  ``VACUUM INTO`` must still
    produce a file that carries them; a plain copy of the main file alone would not.
    """
    writer = connect(zhivaya_baza)
    writer.execute(
        "insert into students (id, surname, name, class, status) values (999, 'late', 'arrival', '8', 'active')"
    )
    try:
        archive = rezervnaya_kopia.make_backup(zhivaya_baza, papka_kopij, label="pered-zanyatiem")
    finally:
        writer.close()

    plain = _unpack(archive, tmp_path)
    # Opened WITHOUT the -wal/-shm files, which is exactly the situation of a restore onto
    # a different machine.
    restored = sqlite3.connect(str(plain))
    try:
        found = restored.execute("select count(*) from students where id = 999").fetchone()[0]
    finally:
        restored.close()
    assert found == 1, "VACUUM INTO lost a committed row that was still in the WAL"


def test_snapshot_passes_integrity_check(zhivaya_baza, papka_kopij, tmp_path):
    archive = rezervnaya_kopia.make_backup(zhivaya_baza, papka_kopij, label="sutochnyj")
    plain = _unpack(archive, tmp_path)
    restored = sqlite3.connect(str(plain))
    try:
        assert restored.execute("pragma integrity_check").fetchone()[0] == "ok"
    finally:
        restored.close()


def test_a_missing_database_raises_instead_of_producing_an_empty_snapshot(papka_kopij, tmp_path):
    with pytest.raises(FileNotFoundError):
        rezervnaya_kopia.make_backup(tmp_path / "nope.db", papka_kopij)
    assert list(papka_kopij.iterdir()) == []


def test_no_half_written_snapshot_is_left_behind(zhivaya_baza, papka_kopij):
    rezervnaya_kopia.make_backup(zhivaya_baza, papka_kopij, label="posle-zanyatia")
    assert [path.name for path in papka_kopij.iterdir() if path.name.endswith(".part")] == []


def test_an_unknown_label_is_refused(zhivaya_baza, papka_kopij):
    with pytest.raises(ValueError):
        rezervnaya_kopia.make_backup(zhivaya_baza, papka_kopij, label="whatever")


def test_rotation_reads_the_age_from_the_name_and_spares_foreign_files(papka_kopij):
    now = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
    old = papka_kopij / rezervnaya_kopia.snapshot_name(now - timedelta(days=20), "sutochnyj")
    young = papka_kopij / rezervnaya_kopia.snapshot_name(now - timedelta(days=3), "sutochnyj")
    foreign = papka_kopij / "readme.txt"
    for path in (old, young, foreign):
        path.write_bytes(b"x")
    # An mtime that lies in the opposite direction to the name, which is what an rsync or
    # a restore of the backups does.
    import os
    os.utime(old, (now.timestamp(), now.timestamp()))

    removed = rezervnaya_kopia.rotate(papka_kopij, keep_days=14, now=now)

    assert [path.name for path in removed] == [old.name]
    assert young.exists() and foreign.exists() and not old.exists()


def test_latest_snapshot_is_the_newest_by_name(papka_kopij):
    now = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
    older = papka_kopij / rezervnaya_kopia.snapshot_name(now - timedelta(days=2), "sutochnyj")
    newer = papka_kopij / rezervnaya_kopia.snapshot_name(now, "posle-zanyatia")
    for path in (older, newer):
        path.write_bytes(b"x")
    assert rezervnaya_kopia.latest_snapshot(papka_kopij) == newer


def test_latest_snapshot_is_none_on_an_empty_directory(papka_kopij):
    assert rezervnaya_kopia.latest_snapshot(papka_kopij) is None


def test_the_module_offers_no_upload_of_any_kind():
    """The absence of a network path is the feature; a future edit that adds one fails here.

    Backups must not leave the perimeter -- a snapshot carries fifty-six children's names.
    The scan runs over CODE only: comments and docstrings are stripped first, because this
    module talks about Telegram at length in order to say that it never touches it, and a
    grep over prose would fail on the very sentence that states the rule.
    """
    code = _code_without_prose(Path(rezervnaya_kopia.__file__))
    for forbidden in ("requests", "urllib", "http", "telegram", "socket", "subprocess"):
        assert forbidden not in code.lower(), (
            "ops/rezervnaya_kopia.py uses %r in code: backups must stay local" % forbidden
        )
