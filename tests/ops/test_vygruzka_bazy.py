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


class _FakeAbout:
    """``about().get(fields="user")`` -- the call that answers "as whom", which is the one
    question a wrong-account run cannot be caught by any other way."""

    def __init__(self, akkaunt):
        self._akkaunt = akkaunt

    def get(self, fields=None):
        return self

    def execute(self):
        return {"user": {"emailAddress": self._akkaunt}}


class _FakeService:
    def __init__(self, entries=None, get_result=None,
                 akkaunt="ye.mathclub@gmail.com"):
        self._files = _FakeFiles(entries, get_result)
        self._about = _FakeAbout(akkaunt)

    def files(self):
        return self._files

    def about(self):
        return self._about


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

    monkeypatch.setattr(
        vygruzka_bazy, "_service",
        lambda token_path: _FakeService(
            get_result={"owners": [{"emailAddress": "ye.mathclub@gmail.com"}]}))
    monkeypatch.setattr(vygruzka_bazy, "_media_proby", lambda: None)

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


# --------------------------------------------------- whose Drive the archive actually lands in
#
# 🔴 Clause 2 of the заход, expressed as tests rather than as a check someone ran once by hand.
# Authorizing as the Cloud project's account (matfak57@gmail.com) instead of the folder's owner
# (ye.mathclub@gmail.com) produces a run that is successful in every observable way: rc=0, a
# file created, rotation performed.  Nothing but an explicit identity check can tell them apart,
# and the check has to live in the NIGHTLY path -- a one-off verification proves only that one
# night went well.


def test_proverit_akkaunt_passes_on_the_folder_owner():
    service = _FakeService(akkaunt="ye.mathclub@gmail.com")
    assert vygruzka_bazy.proverit_akkaunt(service) == "ye.mathclub@gmail.com"


def test_proverit_akkaunt_refuses_the_cloud_project_account_and_names_both():
    service = _FakeService(akkaunt="matfak57@gmail.com")
    with pytest.raises(vygruzka_bazy.NeTotAkkaunt) as otkaz:
        vygruzka_bazy.proverit_akkaunt(service)
    tekst = str(otkaz.value)
    assert "matfak57@gmail.com" in tekst, "must say which account it got"
    assert "ye.mathclub@gmail.com" in tekst, "must say which account it wanted"
    assert "avtorizacia_drive.py" in tekst, "must say how to fix it"


def test_a_wrong_account_uploads_absolutely_nothing(
    monkeypatch, zhivaya_baza: Path, papka_kopij: Path, tmp_path: Path,
):
    """The refusal must come BEFORE files().create, not after.

    A file created under the wrong account is already sitting in the wrong Drive, and deleting
    it needs that same wrong account -- so 'upload, then notice' is not a recoverable order.
    """
    folder_file = tmp_path / "drive_papka.txt"
    folder_file.write_text("folder-x\n", encoding="utf-8")
    service = _FakeService(entries=[], akkaunt="matfak57@gmail.com")
    def _upload_must_not_run(*args, **kwargs):
        raise AssertionError("the account was wrong -- nothing may be created in any Drive")

    monkeypatch.setattr(vygruzka_bazy, "_service", lambda token_path: service)
    monkeypatch.setattr(vygruzka_bazy, "upload", _upload_must_not_run)

    rc = vygruzka_bazy.main([
        "--primenit",
        "--baza", str(zhivaya_baza),
        "--kuda", str(papka_kopij),
        "--papka-fajl", str(folder_file),
    ])

    assert rc == 5
    assert service.files().deleted_ids == [], "rotation must not run either"


def test_proverit_dostup_is_red_on_the_wrong_account_even_when_writable(
    monkeypatch, papka_kopij: Path, tmp_path: Path, capsys,
):
    """`canAddChildren: true` is a PERMISSION answer and says nothing about identity: the wrong
    account can be perfectly able to write -- into the wrong Drive."""
    folder_file = tmp_path / "drive_papka.txt"
    folder_file.write_text("folder-x\n", encoding="utf-8")
    service = _FakeService(
        get_result={"owners": [{"emailAddress": "matfak57@gmail.com"}]},
        akkaunt="matfak57@gmail.com",
    )
    monkeypatch.setattr(vygruzka_bazy, "_service", lambda token_path: service)
    monkeypatch.setattr(vygruzka_bazy, "_media_proby", lambda: None)

    rc = vygruzka_bazy.main(["--proverit-dostup", "--papka-fajl", str(folder_file)])

    assert rc == 5
    out = capsys.readouterr().out
    assert "matfak57@gmail.com" in out, "the account must be printed, not merely judged"


def test_a_missing_consent_file_names_the_one_command_that_creates_it(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="avtorizacia_drive.py"):
        vygruzka_bazy._credentials(tmp_path / "net-takogo-fajla.json")


def test_the_access_probe_always_removes_what_it_created(monkeypatch, tmp_path: Path):
    """A diagnostic that leaves litter in the owner's folder every time it runs is worse than
    no diagnostic -- and the cleanup must survive a failure of the ownership read, which is why
    the delete sits in a ``finally``."""
    folder_file = tmp_path / "drive_papka.txt"
    folder_file.write_text("folder-x\n", encoding="utf-8")
    service = _FakeService(get_result={"owners": [{"emailAddress": "ye.mathclub@gmail.com"}]})
    monkeypatch.setattr(vygruzka_bazy, "_media_proby", lambda: None)

    can_write, detail = vygruzka_bazy.check_access(service, "folder-x")

    assert can_write
    assert service.files().created == [
        {"name": vygruzka_bazy.PROBNYJ_FAJL, "parents": ["folder-x"]}]
    assert service.files().deleted_ids == ["new-file-id"], "the probe must clean up after itself"
    assert "ye.mathclub@gmail.com" in detail


def test_the_access_probe_cleans_up_even_when_the_ownership_read_fails(monkeypatch):
    """The ``finally`` is the point of the test: without it a failed read leaves the probe file
    sitting in the owner's folder for good."""
    class _SlomannyjGet(_FakeFiles):
        def get(self, **kwargs):
            raise RuntimeError("ownership read failed")

    class _Service(_FakeService):
        def __init__(self):
            super().__init__()
            self._files = _SlomannyjGet()

    service = _Service()
    monkeypatch.setattr(vygruzka_bazy, "_media_proby", lambda: None)

    with pytest.raises(RuntimeError):
        vygruzka_bazy.check_access(service, "folder-x")

    assert service.files().deleted_ids == ["new-file-id"]
