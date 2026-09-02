"""The snapshot: consistent, gzipped, rotated, and taken without touching the live file.

``cp`` is the thing this suite is against.  A copy taken mid-transaction, in WAL mode,
without the side files, produces a snapshot that opens and looks valid -- so the tests that
matter here are the ones a ``cp``-based backup would fail: a snapshot taken while another
connection holds an open write transaction, and a source file that is byte-for-byte what it
was before.
"""

from __future__ import annotations

import gzip
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from core.isotime import to_iso
from infra.db import connect
from tools.proverka_vosstanovlenia import (
    ROTATION_DAYS,
    SNAPSHOT_FORMAT,
    DatabaseMissing,
    NoSnapshot,
    _stamp_of,
    main,
    posledniy_snimok,
    rotaciya,
    snyat_snimok,
)


def _raspakovannyj(snapshot: Path, tmp_path: Path) -> sqlite3.Connection:
    """Unpack a snapshot and open it, so a test can ask what actually got copied."""
    restored = tmp_path / ("restored-%s.db" % snapshot.name)
    with gzip.open(snapshot, "rb") as source:
        restored.write_bytes(source.read())
    connection = sqlite3.connect(str(restored))
    connection.row_factory = sqlite3.Row
    return connection


# ------------------------------------------------------------------------ the snapshot


def test_snimok_szhat_i_vosstanavlivaetsya(bolshoy_mir, svezhaya_otmetka, zakrytaya_baza, tmp_path):
    """The file on disk is gzip, and what comes out of it is the database that went in."""
    snapshot = snyat_snimok(zakrytaya_baza, tmp_path / "backups")

    assert snapshot.exists()
    assert snapshot.read_bytes()[:2] == b"\x1f\x8b", "снимок обязан быть gzip"

    connection = _raspakovannyj(snapshot, tmp_path)
    try:
        assert connection.execute("select count(*) from students").fetchone()[0] == 56
        assert connection.execute("select max(valid_at) from marks").fetchone()[0] == svezhaya_otmetka
        assert [r[0] for r in connection.execute("pragma integrity_check")] == ["ok"]
    finally:
        connection.close()


def test_snimok_ne_menyaet_bajty_zhivoy_bazy(bolshoy_mir, svezhaya_otmetka, zakrytaya_baza, tmp_path):
    """The database being protected is byte-identical after being backed up.

    ``VACUUM INTO`` runs over a read-only connection, so this is not a hope about the
    implementation -- it is what the connection permits.
    """
    do = zakrytaya_baza.read_bytes()
    snyat_snimok(zakrytaya_baza, tmp_path / "backups")
    assert zakrytaya_baza.read_bytes() == do


def test_snimok_posredi_chuzhoy_tranzakcii_soglasovan(
    bolshoy_mir, svezhaya_otmetka, zakrytaya_baza, tmp_path
):
    """A snapshot taken while another writer holds an open transaction is consistent.

    🔴 THIS IS THE TEST ``cp`` FAILS.  ``cp`` copies the main file as it stands, half-way
    through somebody's transaction and without the ``-wal`` beside it; the result opens and
    looks valid.  ``VACUUM INTO`` asks SQLite for a snapshot, so what lands in the file is
    the last COMMITTED state: the uncommitted row is absent and the file is intact.
    """
    pisatel = connect(zakrytaya_baza)
    try:
        pisatel.execute("begin immediate")
        pisatel.execute(
            "insert into students (surname, name, class, status) "
            "values ('Незакоммиченный', 'Ученик', '9К', 'active')"
        )
        snapshot = snyat_snimok(zakrytaya_baza, tmp_path / "backups")
        # Rolled back on purpose: the transaction never happened, and a snapshot that
        # carried its row would be a snapshot of a state the database was never in.
        pisatel.execute("rollback")
    finally:
        pisatel.close()

    connection = _raspakovannyj(snapshot, tmp_path)
    try:
        assert [r[0] for r in connection.execute("pragma integrity_check")] == ["ok"]
        assert connection.execute("select count(*) from students").fetchone()[0] == 56
        assert connection.execute(
            "select count(*) from students where surname = 'Незакоммиченный'"
        ).fetchone()[0] == 0
    finally:
        connection.close()


def test_bez_bazy_govorit_slovami(tmp_path):
    with pytest.raises(DatabaseMissing, match="нет базы"):
        snyat_snimok(tmp_path / "нет-такой.db", tmp_path / "backups")


# ------------------------------------------------------------------------- the rotation


def _polozhit(backup_dir: Path, vozrast_dney: int) -> Path:
    """Put a snapshot-shaped file dated ``vozrast_dney`` days ago into the directory."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc) - timedelta(days=vozrast_dney)
    path = backup_dir / stamp.strftime(SNAPSHOT_FORMAT)
    path.write_bytes(b"\x1f\x8b" + b"0" * 16)
    return path


def test_rotaciya_udalyaet_starshe_chetyrnadcati_dney(tmp_path):
    backup_dir = tmp_path / "backups"
    svezhiy = _polozhit(backup_dir, 1)
    granica = _polozhit(backup_dir, ROTATION_DAYS - 1)
    staryy = _polozhit(backup_dir, ROTATION_DAYS + 1)
    ochen_staryy = _polozhit(backup_dir, 400)

    udaleno = rotaciya(backup_dir)

    assert sorted(udaleno) == sorted([staryy.name, ochen_staryy.name])
    assert svezhiy.exists() and granica.exists()
    assert not staryy.exists() and not ochen_staryy.exists()


def test_rotaciya_ne_trogaet_chuzhie_fajly(tmp_path):
    """Anything that is not one of our snapshots survives, however old it looks.

    Rotation is the one destructive operation in the tool, and the directory it runs in is
    a directory a person keeps things in.
    """
    backup_dir = tmp_path / "backups"
    _polozhit(backup_dir, 400)
    chuzhoy = backup_dir / "заметка.txt"
    chuzhoy.write_text("не снимок", encoding="utf-8")
    tozhe_chuzhoy = backup_dir / "spetsmat-vchera.db.gz"
    tozhe_chuzhoy.write_bytes(b"\x1f\x8b")

    rotaciya(backup_dir)

    assert chuzhoy.exists()
    assert tozhe_chuzhoy.exists(), "имя без даты не разобрано — значит, не наше, значит, не трогаем"


def test_vozrast_chitaetsya_iz_imeni_a_ne_iz_mtime(tmp_path):
    """The timestamp comes from the file's NAME.

    Copying a backup directory to a new disk rewrites every mtime; a rotation driven by
    mtime would then either keep everything forever or delete everything at once.
    """
    backup_dir = tmp_path / "backups"
    staryy = _polozhit(backup_dir, 400)
    # Freshly touched, and still four hundred days old by its name.
    staryy.touch()

    assert _stamp_of(staryy) is not None
    assert _stamp_of(backup_dir / "не-наш-файл.db.gz") is None
    assert rotaciya(backup_dir) == [staryy.name]


def test_posledniy_snimok_eto_samyj_novyj(tmp_path):
    backup_dir = tmp_path / "backups"
    _polozhit(backup_dir, 5)
    noveyshiy = _polozhit(backup_dir, 0)
    _polozhit(backup_dir, 12)
    assert posledniy_snimok(backup_dir) == noveyshiy


def test_bez_snimkov_govorit_slovami(tmp_path):
    (tmp_path / "backups").mkdir()
    with pytest.raises(NoSnapshot, match="нет ни одного снимка"):
        posledniy_snimok(tmp_path / "backups")


# -------------------------------------------------------------------------------- CLI


def test_cli_snyat_i_proverit_zelyonyj(bolshoy_mir, svezhaya_otmetka, zakrytaya_baza, tmp_path, capsys):
    """The command P10 will schedule: snapshot, rotate, check -- rc=0 on a whole base."""
    backup_dir = tmp_path / "backups"
    kod = main(["--baza", str(zakrytaya_baza), "--snimki", str(backup_dir)])

    vyvod = capsys.readouterr().out
    assert kod == 0
    assert "VACUUM INTO" in vyvod
    assert "проверок 3, покраснело 0" in vyvod
    assert "учеников               56" in vyvod
    assert len(list(backup_dir.glob("spetsmat-*.db.gz"))) == 1


def test_cli_staraya_otmetka_krasnaya(bolshoy_mir, staraya_otmetka, zakrytaya_baza, tmp_path, capsys):
    """The scheduled command goes RED when nobody has marked in a week.

    Silence is the failure mode this whole position is about: a check that reported success
    here would be a backup nobody looks at, on a bot that stopped writing.
    """
    kod = main(["--baza", str(zakrytaya_baza), "--snimki", str(tmp_path / "backups")])
    vyvod = capsys.readouterr().out

    assert kod != 0
    assert "ПРОВАЛ: свежесть отметки" in vyvod


def test_cli_tolko_snyat_ne_proveryaet(bolshoy_mir, staraya_otmetka, zakrytaya_baza, tmp_path, capsys):
    """The snapshot is a separate task from the check, and it succeeds on its own terms."""
    kod = main(["--baza", str(zakrytaya_baza), "--snimki", str(tmp_path / "backups"), "--tolko-snyat"])
    assert kod == 0
    assert "проверок" not in capsys.readouterr().out


def test_cli_tolko_proverit_beryot_posledniy(bolshoy_mir, svezhaya_otmetka, zakrytaya_baza, tmp_path, capsys):
    backup_dir = tmp_path / "backups"
    snapshot = snyat_snimok(zakrytaya_baza, backup_dir)
    capsys.readouterr()

    kod = main(["--snimki", str(backup_dir), "--tolko-proverit"])
    vyvod = capsys.readouterr().out

    assert kod == 0
    assert snapshot.name in vyvod
    assert len(list(backup_dir.glob("spetsmat-*.db.gz"))) == 1, "нового снимка быть не должно"


def test_cli_bez_snimkov_vozvrashchaet_3(tmp_path, capsys):
    (tmp_path / "backups").mkdir()
    assert main(["--snimki", str(tmp_path / "backups"), "--tolko-proverit"]) == 3
    assert "нет ни одного снимка" in capsys.readouterr().err


def test_data_v_imeni_sortiruetsya(tmp_path):
    """Snapshot names sort chronologically as strings -- that is why the format is this one."""
    imena = [
        (datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc) + timedelta(days=d)).strftime(
            SNAPSHOT_FORMAT
        )
        for d in (0, 40, 400)
    ]
    assert imena == sorted(imena)
    assert to_iso(_stamp_of(Path(imena[0]))) == "2026-01-02T03:04:05Z"
