"""The restore check, and above all the proof that it is ABLE to go red.

Three corruptions x the assertion each one is meant to trip, plus the case that matters
most and is easiest to forget: that the self-test itself notices a FALSE GREEN.  A
self-test that reports success no matter what the check does would hide precisely the
failure it was written to expose.
"""

from __future__ import annotations

import gzip
import shutil
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from ops import proverka_vosstanovlenia as proverka
from ops import rezervnaya_kopia


def _broken_snapshot(healthy_archive: Path, workspace: Path, damage) -> Path:
    plain = workspace / "plain.db"
    with gzip.open(healthy_archive, "rb") as source, plain.open("wb") as sink:
        shutil.copyfileobj(source, sink)
    damage(plain)
    broken = workspace / "broken.db.gz"
    with plain.open("rb") as source, gzip.open(broken, "wb") as sink:
        shutil.copyfileobj(source, sink)
    return broken


@pytest.fixture
def zdorovyj_snimok(zhivaya_baza, papka_kopij) -> Path:
    return rezervnaya_kopia.make_backup(zhivaya_baza, papka_kopij, label="sutochnyj")


def test_a_healthy_snapshot_is_green_on_all_three(zdorovyj_snimok):
    verdict = proverka.check_snapshot(zdorovyj_snimok)
    assert verdict.passed, verdict.report()
    assert tuple(check.name for check in verdict.checks) == proverka.CHECK_NAMES
    assert "passed 3 of 3 checks" in verdict.report()


@pytest.mark.parametrize("title, damage, expected", proverka.DAMAGE,
                         ids=[expected for _, _, expected in proverka.DAMAGE])
def test_each_corruption_is_caught_by_its_own_assertion(title, damage, expected,
                                                        zdorovyj_snimok, tmp_path):
    workspace = tmp_path / "work"
    workspace.mkdir()
    verdict = proverka.check_snapshot(_broken_snapshot(zdorovyj_snimok, workspace, damage))
    assert not verdict.passed, "corruption %r passed the restore check: %s" % (title, verdict.report())
    assert expected in verdict.failed_names, (
        "corruption %r was caught by %s and not by %s" % (title, verdict.failed_names, expected)
    )


def test_the_verdict_carries_its_own_coverage(zdorovyj_snimok):
    """A negative verdict must say how much was checked, not only that nothing was found."""
    report = proverka.check_snapshot(zdorovyj_snimok).report()
    assert "of 3 checks" in report


def test_a_missing_snapshot_is_red_and_not_silently_green(tmp_path):
    verdict = proverka.check_snapshot(tmp_path / "absent.db.gz")
    assert not verdict.passed
    assert verdict.error is not None


def test_a_snapshot_that_is_not_gzip_is_red(tmp_path):
    fake = tmp_path / "spetsmat-20260902T120000Z-sutochnyj.db.gz"
    fake.write_bytes(b"this is not a gzip stream at all")
    verdict = proverka.check_snapshot(fake)
    assert not verdict.passed
    assert verdict.error is not None


def test_a_snapshot_with_no_marks_at_all_is_red(zhivaya_baza, papka_kopij, tmp_path):
    """An empty journal is not "nothing to check" -- it is a bot that never wrote anything."""
    def wipe(plain: Path) -> None:
        connection = sqlite3.connect(str(plain))
        try:
            connection.execute("drop trigger if exists marks_append_only_delete")
            connection.execute("delete from marks")
            connection.commit()
        finally:
            connection.close()

    healthy = rezervnaya_kopia.make_backup(zhivaya_baza, papka_kopij, label="sutochnyj")
    workspace = tmp_path / "empty"
    workspace.mkdir()
    verdict = proverka.check_snapshot(_broken_snapshot(healthy, workspace, wipe))
    assert not verdict.passed
    assert "freshness" in verdict.failed_names


def test_freshness_is_measured_against_the_given_instant_not_the_wall_clock(zdorovyj_snimok):
    """The boundary is asserted from both sides, so 'not older than a week' has a meaning."""
    inside = proverka.check_snapshot(zdorovyj_snimok, now=datetime.now(tz=timezone.utc))
    assert inside.passed
    outside = proverka.check_snapshot(
        zdorovyj_snimok,
        now=datetime.now(tz=timezone.utc) + timedelta(days=proverka.MAX_MARK_AGE_DAYS + 2),
    )
    assert not outside.passed
    assert outside.failed_names == ("freshness",)


def test_self_test_returns_one_when_every_corruption_is_caught(capsys):
    """The готовности criterion's own command, run as a test: rc must be 1, never 0."""
    assert proverka.run_self_test() == 1
    printed = capsys.readouterr().out
    assert "3 of 3 corruptions went red" in printed
    assert "false greens 0" in printed


def test_self_test_returns_two_when_a_corruption_slips_through(monkeypatch, capsys):
    """The check that the self-test is not decoration.

    ``check_snapshot`` is replaced by one that is always green -- the exact shape of a
    broken restore check -- and the self-test must notice rather than report success.
    """
    always_green = proverka.Verdict(
        checks=tuple(proverka.OneCheck(name, True, "stubbed") for name in proverka.CHECK_NAMES),
        snapshot=Path("stub"),
    )
    monkeypatch.setattr(proverka, "check_snapshot", lambda *a, **k: always_green)
    assert proverka.run_self_test() == 2
    printed = capsys.readouterr().out
    assert "FALSE GREEN" in printed
    assert "BROKEN" in printed


def test_self_test_returns_two_when_the_wrong_assertion_catches_it(monkeypatch, capsys):
    """Caught by SOMETHING is not the same as caught by the assertion that exists for it."""
    wrong = proverka.Verdict(
        checks=(
            proverka.OneCheck("integrity", False, "stubbed"),
            proverka.OneCheck("roster", True, "stubbed"),
            proverka.OneCheck("freshness", True, "stubbed"),
        ),
        snapshot=Path("stub"),
    )
    monkeypatch.setattr(proverka, "check_snapshot", lambda *a, **k: wrong)
    assert proverka.run_self_test() == 2
    assert "wrong assertion" in capsys.readouterr().out


def test_cli_with_no_snapshot_at_all_is_red(tmp_path, capsys):
    assert proverka.main(["--kuda", str(tmp_path)]) == 1


def test_cli_on_the_latest_snapshot_is_green(zdorovyj_snimok, papka_kopij, capsys):
    assert proverka.main(["--kuda", str(papka_kopij)]) == 0
    assert "GREEN" in capsys.readouterr().out
