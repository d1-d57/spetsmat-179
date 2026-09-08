"""``ops/vygruzka_bazy.py``: the pure judgment calls, plus the probe path proven network-free.

The Drive API itself is not re-proven here (``google-api-python-client`` is not a test
dependency and the module only imports it lazily, inside ``_credentials``/``_service`` --
same lazy-import shape as ``ops/vygruzka_v_tablicu.py``).  What IS proven here, against tiny
fake service objects that mimic just the ``.files().x().execute()`` chain used:

  * rotation picks the newest ``keep`` archives by name and nothing else (``plan_rotation``,
    ``rotate_drive``);
  * the one-off table move is idempotent and never recreates the sheet (``table_parents_after_move``,
    ``move_table``);
  * the probe path takes a REAL local snapshot but makes ZERO Drive calls -- the one claim
    the module's own docstring makes about dry-run behaviour, checked rather than trusted.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ops import rezervnaya_kopia, vygruzka_bazy


# --------------------------------------------------------------------- pure: rotation choice


def test_plan_rotation_keeps_the_newest_names_by_lexical_order():
    names = ["spetsmat-20260101T000000Z-oblachnyj.db.gz",
             "spetsmat-20260103T000000Z-oblachnyj.db.gz",
             "spetsmat-20260102T000000Z-oblachnyj.db.gz"]
    kept, deleted = vygruzka_bazy.plan_rotation(names, keep=2)
    assert kept == ["spetsmat-20260103T000000Z-oblachnyj.db.gz",
                     "spetsmat-20260102T000000Z-oblachnyj.db.gz"]
    assert deleted == ["spetsmat-20260101T000000Z-oblachnyj.db.gz"]


def test_plan_rotation_deletes_nothing_when_under_the_limit():
    names = ["spetsmat-20260101T000000Z-oblachnyj.db.gz"]
    kept, deleted = vygruzka_bazy.plan_rotation(names, keep=14)
    assert kept == names
    assert deleted == []


class _FakeFiles:
    """Mimics ``service.files().list/get/create/update/delete().execute()`` just enough."""

    def __init__(self, entries=None, get_result=None):
        self.entries = list(entries or [])
        self.get_result = get_result or {}
        self.deleted_ids: list[str] = []
        self.created: list[dict] = []
        self.updated: list[dict] = []

    def list(self, **kwargs):
        return _Exec({"files": self.entries})

    def get(self, **kwargs):
        return _Exec(self.get_result)

    def delete(self, fileId, **kwargs):
        self.deleted_ids.append(fileId)
        return _Exec({})

    def create(self, body, media_body=None, **kwargs):
        self.created.append(body)
        return _Exec({"id": "new-file-id"})

    def update(self, fileId, addParents, removeParents, **kwargs):
        self.updated.append({"fileId": fileId, "addParents": addParents,
                             "removeParents": removeParents})
        return _Exec({"id": fileId})


class _Exec:
    def __init__(self, result):
        self._result = result

    def execute(self):
        return self._result


class _FakeService:
    def __init__(self, entries=None, get_result=None):
        self._files = _FakeFiles(entries, get_result)

    def files(self):
        return self._files


# ------------------------------------------------------------------------ Drive-side rotation


def test_rotate_drive_deletes_only_the_names_beyond_keep():
    entries = [
        {"id": "a", "name": "spetsmat-20260101T000000Z-oblachnyj.db.gz"},
        {"id": "b", "name": "spetsmat-20260102T000000Z-oblachnyj.db.gz"},
        {"id": "c", "name": "spetsmat-20260103T000000Z-oblachnyj.db.gz"},
    ]
    service = _FakeService(entries=entries)

    total_before, kept, deleted = vygruzka_bazy.rotate_drive(service, "folder-x", keep=2)

    assert (total_before, kept, deleted) == (3, 2, 1)
    assert service.files().deleted_ids == ["a"]


def test_rotate_drive_deletes_nothing_when_folder_is_already_within_the_limit():
    entries = [{"id": "a", "name": "spetsmat-20260101T000000Z-oblachnyj.db.gz"}]
    service = _FakeService(entries=entries)

    total_before, kept, deleted = vygruzka_bazy.rotate_drive(service, "folder-x", keep=14)

    assert (total_before, kept, deleted) == (1, 1, 0)
    assert service.files().deleted_ids == []


# -------------------------------------------------------------------- pure: table-move choice


def test_table_parents_after_move_is_a_noop_when_already_in_the_folder():
    assert vygruzka_bazy.table_parents_after_move(["folder-x"], "folder-x") is None


def test_table_parents_after_move_names_the_swap_when_elsewhere():
    add, remove = vygruzka_bazy.table_parents_after_move(["old-parent"], "folder-x")
    assert add == "folder-x"
    assert remove == "old-parent"


def test_move_table_is_a_noop_that_touches_nothing_when_already_parented():
    service = _FakeService(get_result={"parents": ["folder-x"]})
    result = vygruzka_bazy.move_table(service, "sheet-id", "folder-x")
    assert "уже в папке" in result
    assert service.files().updated == []


def test_move_table_moves_the_parent_and_never_recreates_the_sheet():
    service = _FakeService(get_result={"parents": ["old-parent"]})
    vygruzka_bazy.move_table(service, "sheet-id", "folder-x")
    assert service.files().updated == [
        {"fileId": "sheet-id", "addParents": "folder-x", "removeParents": "old-parent"}
    ]
    assert service.files().created == [], "a move must never go through create()"


# ------------------------------------------------------------------- the probe path, for real


def test_probe_takes_a_real_local_snapshot_and_makes_no_drive_call(
    monkeypatch, zhivaya_baza: Path, papka_kopij: Path, tmp_path: Path,
):
    def _must_not_be_called(*args, **kwargs):
        raise AssertionError("probe mode (no --primenit) must not touch the network")

    monkeypatch.setattr(vygruzka_bazy, "_service", _must_not_be_called)

    rc = vygruzka_bazy.main([
        "--baza", str(zhivaya_baza),
        "--kuda", str(papka_kopij),
        "--papka-fajl", str(tmp_path / "nope.txt"),
    ])

    assert rc == 0
    snapshots = list(papka_kopij.glob("spetsmat-*-%s.db.gz" % vygruzka_bazy.LABEL))
    assert len(snapshots) == 1, "the probe must still take one real local snapshot"


def test_the_new_label_is_accepted_by_rezervnaya_kopia():
    assert vygruzka_bazy.LABEL in rezervnaya_kopia.LABELS


def test_stdout_never_names_the_archive_file_even_on_success(
    monkeypatch, zhivaya_baza: Path, papka_kopij: Path, tmp_path: Path, capsys,
):
    """Found live on the production server: ``ops/opoveshchenie.py``'s own perimeter guard
    (``FORBIDDEN_IN_TEXT``) refuses to send ANY alert whose journal tail mentions
    ``.db.gz`` -- correctly, a path is a request to fetch a snapshot. This module's probe
    line named the archive's own path, which lingered in the unit's journal past a LATER,
    real failure (the Drive upload) and silently swallowed the alert that failure should
    have sent. This test would have caught that before it reached the server.
    """
    monkeypatch.setattr(vygruzka_bazy, "_service",
                        lambda key_path: (_ for _ in ()).throw(AssertionError("no network in probe")))

    rc = vygruzka_bazy.main([
        "--baza", str(zhivaya_baza),
        "--kuda", str(papka_kopij),
        "--papka-fajl", str(tmp_path / "nope.txt"),
    ])

    assert rc == 0
    out = capsys.readouterr().out
    for forbidden in (".db.gz", ".sqlite", ".db "):
        assert forbidden not in out.lower(), (
            "stdout must never name the archive file: %r found in %r" % (forbidden, out)
        )


def test_proverit_dostup_makes_no_local_snapshot(monkeypatch, papka_kopij: Path, tmp_path: Path):
    folder_file = tmp_path / "drive_papka.txt"
    folder_file.write_text("folder-x\n", encoding="utf-8")

    monkeypatch.setattr(vygruzka_bazy, "_service",
                        lambda key_path: _FakeService(get_result={"name": "owner-folder",
                                                                  "capabilities": {"canAddChildren": True}}))

    rc = vygruzka_bazy.main(["--proverit-dostup", "--papka-fajl", str(folder_file)])

    assert rc == 0
    assert list(papka_kopij.iterdir()) == [], "--proverit-dostup must not take a snapshot"


def test_a_missing_folder_file_stops_primenit_after_the_local_snapshot(
    monkeypatch, zhivaya_baza: Path, papka_kopij: Path, tmp_path: Path,
):
    def _must_not_be_called(*args, **kwargs):
        raise AssertionError("no Drive credentials should be built when the folder id is missing")

    monkeypatch.setattr(vygruzka_bazy, "_service", _must_not_be_called)

    rc = vygruzka_bazy.main([
        "--primenit",
        "--baza", str(zhivaya_baza),
        "--kuda", str(papka_kopij),
        "--papka-fajl", str(tmp_path / "does-not-exist.txt"),
    ])

    assert rc == 5
    snapshots = list(papka_kopij.glob("spetsmat-*-%s.db.gz" % vygruzka_bazy.LABEL))
    assert len(snapshots) == 1, (
        "the local snapshot ('everything else') is legitimate work and must not be skipped "
        "just because the folder id is missing -- only the upload stops"
    )


def test_the_folder_id_never_reaches_stdout(
    monkeypatch, zhivaya_baza: Path, papka_kopij: Path, tmp_path: Path, capsys,
):
    folder_file = tmp_path / "drive_papka.txt"
    secret_id = "SECRET-FOLDER-ID-MUST-NOT-PRINT"
    folder_file.write_text(secret_id + "\n", encoding="utf-8")

    service = _FakeService(
        entries=[],
        get_result={"name": "owner-folder", "capabilities": {"canAddChildren": True}},
    )
    monkeypatch.setattr(vygruzka_bazy, "_service", lambda key_path: service)
    monkeypatch.setattr(vygruzka_bazy, "upload", lambda service, folder_id, path: "fake-id")

    rc = vygruzka_bazy.main([
        "--primenit",
        "--baza", str(zhivaya_baza),
        "--kuda", str(papka_kopij),
        "--papka-fajl", str(folder_file),
    ])

    assert rc == 0
    out = capsys.readouterr().out
    assert secret_id not in out
