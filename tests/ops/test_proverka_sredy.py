"""The environment check -- and, as everywhere in this position, that it can go red.

``config.py`` declaring ``WAL = True`` proves nothing about the process that is running.
These tests therefore move the DECLARED value away from the applied one and demand that
the check notices; a check that only ever sees agreement has never been tested at all.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ops import proverka_sredy


def test_the_running_connection_really_has_the_pragmas(tmp_path):
    check = proverka_sredy.check_pragmas(tmp_path / "probe.db")
    assert check.passed, check.detail
    assert "journal_mode=wal" in check.detail
    assert "busy_timeout=5000" in check.detail


def _connect_that_forgets(pragma: str):
    """A ``connect`` that sets everything and then quietly drops one pragma.

    This is the real failure shape, and it is why the check cannot be written against
    ``config``: a connection opened somewhere other than ``infra.db.connect`` -- or by a
    future edit of it -- keeps the DECLARED value in ``config.py`` and loses the applied
    one.  Patching ``config`` instead would move both sides at once and prove nothing.
    """
    import infra.db

    real_connect = infra.db.connect

    def connect(db_path=None):
        connection = real_connect(db_path)
        connection.execute(pragma)
        return connection

    return infra.db, connect


def test_a_busy_timeout_that_is_only_declared_goes_red(tmp_path, monkeypatch):
    module, forgetful = _connect_that_forgets("pragma busy_timeout = 0")
    monkeypatch.setattr(module, "connect", forgetful)
    check = proverka_sredy.check_pragmas(tmp_path / "probe.db")
    assert not check.passed
    assert "busy_timeout" in check.detail


def test_wal_that_is_only_declared_goes_red(tmp_path, monkeypatch):
    module, forgetful = _connect_that_forgets("pragma journal_mode = delete")
    monkeypatch.setattr(module, "connect", forgetful)
    check = proverka_sredy.check_pragmas(tmp_path / "probe.db")
    assert not check.passed
    assert "journal_mode" in check.detail


def test_foreign_keys_that_are_only_declared_go_red(tmp_path, monkeypatch):
    """The pragma whose absence silently accepts marks pointing at students who do not exist."""
    module, forgetful = _connect_that_forgets("pragma foreign_keys = off")
    monkeypatch.setattr(module, "connect", forgetful)
    check = proverka_sredy.check_pragmas(tmp_path / "probe.db")
    assert not check.passed
    assert "foreign_keys" in check.detail


def test_the_probe_does_not_touch_the_live_database(monkeypatch, tmp_path):
    """A check that opens the live database is a second writer during a lesson."""
    live = tmp_path / "data" / "spetsmat.db"
    # 🔴 ЧЕРЕЗ СРЕДУ, А НЕ ЧЕРЕЗ `setattr`. `config.DB_PATH` больше не хранимая
    # константа, а вопрос, на который отвечает окружение (PEP 562 `__getattr__`), и
    # подмена атрибутом обошла бы ровно тот механизм, который тут и проверяется.
    monkeypatch.setenv("SPETSMAT_BAZA", str(live))
    assert proverka_sredy.check_pragmas().passed
    assert not live.exists(), "the environment check created or opened the live database"


def test_disk_check_goes_red_when_the_threshold_is_absurd(tmp_path):
    assert proverka_sredy.check_disk(tmp_path, minimum=10 ** 18).passed is False
    assert proverka_sredy.check_disk(tmp_path, minimum=1).passed is True


def test_disk_check_walks_up_to_an_existing_directory(tmp_path):
    """The database directory may not exist yet on a fresh machine; the check must not crash."""
    assert proverka_sredy.check_disk(tmp_path / "not" / "there" / "yet", minimum=1).passed


def test_certs_are_read_offline_and_go_red_once_everything_has_expired():
    assert proverka_sredy.check_certs().passed
    far_future = datetime(9998, 1, 1, tzinfo=timezone.utc)
    expired = proverka_sredy.check_certs(now=far_future)
    assert not expired.passed
    assert "still valid" in expired.detail


def test_versions_are_adequate_on_this_machine():
    check = proverka_sredy.check_versions()
    assert check.passed, check.detail


def test_the_whole_verdict_carries_its_coverage(tmp_path):
    verdict = proverka_sredy.check_all(tmp_path / "probe.db")
    assert tuple(check.name for check in verdict.checks) == proverka_sredy.CHECK_NAMES
    assert "of 4 checks" in verdict.report()


def test_cli_is_green_here(tmp_path, capsys):
    assert proverka_sredy.main(["--baza", str(tmp_path / "probe.db")]) == 0
    assert "GREEN" in capsys.readouterr().out
