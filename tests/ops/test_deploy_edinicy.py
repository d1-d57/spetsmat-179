"""The deployment declaration, checked here because there is no server to check it on.

Two kinds of assertion live in this file.  The first kind reads the real ``deploy/`` and
demands the directives be there.  The second kind BREAKS a copy of ``deploy/`` and demands
that ``ops/proverka_ustanovki.py`` notices -- without it, every green above would only mean
the checker is easy to please.

The third thing asserted here is the one that no single file can state: that the timers and
``ops/raspisanie.py`` still agree about when a lesson is.  Two answers to that question
would show up as a missing snapshot on precisely the day something was lost.
"""

from __future__ import annotations

import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from ops import proverka_ustanovki as ustanovka
from ops import raspisanie

DEPLOY = Path(ustanovka.DEPLOY)


@pytest.fixture
def kopia_deploy(tmp_path: Path) -> Path:
    """A writable copy of ``deploy/``, so a test may break it without touching the real one."""
    target = tmp_path / "deploy"
    shutil.copytree(DEPLOY, target)
    return target


# ------------------------------------------------------------------ the real declaration


def test_the_real_deploy_directory_is_green():
    verdict = ustanovka.check_all(DEPLOY)
    assert verdict.passed, verdict.report()
    assert "of 7 checks" in verdict.report()


def test_every_unit_that_can_be_enabled_is_enabled_by_the_install_script():
    """The most frequent real failure on the owner's list, and the one line that prevents it."""
    units = ustanovka.read_units(DEPLOY)
    script = (DEPLOY / "ustanovka.sh").read_text(encoding="utf-8")
    assert set(ustanovka.units_needing_enable(units)) == set(ustanovka.units_the_script_enables(script))
    assert "systemctl enable" in script


def test_the_bot_unit_declares_a_watchdog_and_the_protocol_that_makes_it_real():
    text = ustanovka.read_units(DEPLOY)[ustanovka.MAIN_UNIT]
    assert ustanovka.directive(text, "WatchdogSec") is not None
    assert ustanovka.directive(text, "Type") == "notify"


def test_five_failed_starts_in_five_minutes_stop_the_unit():
    text = ustanovka.read_units(DEPLOY)[ustanovka.MAIN_UNIT]
    assert ustanovka.directive(text, "StartLimitBurst") == "5"
    assert ustanovka.directive(text, "StartLimitIntervalSec") == "300"
    assert ustanovka.directive(text, "OnFailure") is not None, "a stop nobody hears is no stop"


def test_the_alerter_is_a_different_unit_and_does_not_alert_about_itself():
    units = ustanovka.read_units(DEPLOY)
    alerter = units["spetsmat-alert@.service"]
    assert ustanovka.directive(alerter, "OnFailure") is None, "an alerter that alerts about itself loops"
    assert "opoveshchenie.py" in alerter


def test_the_journal_has_a_cap():
    """A disk filled by logs left at debug level, from the owner's measured list."""
    conf = (DEPLOY / "journald-spetsmat.conf").read_text(encoding="utf-8")
    assert "SystemMaxUse" in conf and "SystemKeepFree" in conf


# ------------------------------------------------- the timers agree with ops/raspisanie.py


def _oncalendar(timer: str) -> str:
    return ustanovka.directive((DEPLOY / timer).read_text(encoding="utf-8"), "OnCalendar")


def _weekday_names(lesson_weekdays) -> set[str]:
    names = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}
    return {names[day] for day in lesson_weekdays}


@pytest.mark.parametrize("timer", [
    "spetsmat-rezervnaya-kopia-pered-zanyatiem.timer",
    "spetsmat-rezervnaya-kopia-posle-zanyatia.timer",
])
def test_the_lesson_timers_fire_on_the_lesson_days_and_nothing_else(timer):
    schedule = _oncalendar(timer)
    days = set(schedule.split()[0].split(","))
    assert days == _weekday_names(raspisanie.LESSON_WEEKDAYS), (
        "%s fires on %s but ops/raspisanie.py says lessons are on %s"
        % (timer, sorted(days), sorted(_weekday_names(raspisanie.LESSON_WEEKDAYS)))
    )


def _utc_time_of(schedule: str) -> tuple[int, int]:
    found = re.search(r"(\d{2}):(\d{2}):\d{2}\s+UTC", schedule)
    assert found, "OnCalendar=%r does not name an explicit UTC time" % schedule
    return int(found.group(1)), int(found.group(2))


def test_the_before_lesson_snapshot_really_lands_before_the_lesson():
    """UTC in the timer, Moscow in the timetable -- and the two must still bracket correctly."""
    hour, minute = _utc_time_of(_oncalendar("spetsmat-rezervnaya-kopia-pered-zanyatiem.timer"))
    fires = datetime(2026, 9, 7, hour, minute, tzinfo=ZoneInfo("UTC")).astimezone(raspisanie.MOSCOW)
    lesson_start = datetime.combine(fires.date(), raspisanie.LESSON_START, tzinfo=raspisanie.MOSCOW)
    assert fires < lesson_start, "the 'before the lesson' snapshot fires at or after the bell"
    assert lesson_start - fires <= timedelta(minutes=30), (
        "the 'before' snapshot is so early that a whole lesson's worth of marks could still "
        "be lost with it"
    )


def test_the_after_lesson_snapshot_really_lands_after_the_lesson():
    hour, minute = _utc_time_of(_oncalendar("spetsmat-rezervnaya-kopia-posle-zanyatia.timer"))
    fires = datetime(2026, 9, 7, hour, minute, tzinfo=ZoneInfo("UTC")).astimezone(raspisanie.MOSCOW)
    lesson_end = datetime.combine(fires.date(), raspisanie.LESSON_END, tzinfo=raspisanie.MOSCOW)
    assert fires > lesson_end, "the 'after the lesson' snapshot fires before the lesson ends"


def test_the_daily_snapshot_is_far_from_any_lesson():
    hour, minute = _utc_time_of(_oncalendar("spetsmat-rezervnaya-kopia-sutochnyj.timer"))
    moment = datetime(2026, 9, 7, hour, minute)
    frozen, reason = raspisanie.is_lesson_time(moment)
    assert not frozen, "the daily snapshot fires inside the lesson window: %s" % reason


def test_every_backup_label_a_timer_asks_for_is_a_label_the_backup_module_accepts():
    """A typo here produces a timer that fires and a snapshot that is never taken."""
    from ops import rezervnaya_kopia

    for timer in DEPLOY.glob("spetsmat-rezervnaya-kopia-*.timer"):
        unit = ustanovka.directive(timer.read_text(encoding="utf-8"), "Unit")
        label = unit.split("@", 1)[1].rsplit(".service", 1)[0]
        assert label in rezervnaya_kopia.LABELS, "%s asks for label %r" % (timer.name, label)


def test_every_timer_that_can_be_missed_is_persistent():
    """A machine that was off must take the snapshot late, not skip the day in silence."""
    for timer in DEPLOY.glob("*.timer"):
        text = timer.read_text(encoding="utf-8")
        assert ustanovka.directive(text, "Persistent") == "true", timer.name


# ---------------------------------------------------- and now: the checker can go red


def test_a_forgotten_systemctl_enable_is_caught(kopia_deploy):
    script = kopia_deploy / "ustanovka.sh"
    text = script.read_text(encoding="utf-8")
    script.write_text(text.replace("  spetsmat-bot.service\n", "", 1), encoding="utf-8")
    verdict = ustanovka.check_all(kopia_deploy)
    assert not verdict.passed
    assert "enable" in verdict.failed_names


def test_a_watchdog_without_type_notify_is_caught(kopia_deploy):
    unit = kopia_deploy / ustanovka.MAIN_UNIT
    unit.write_text(unit.read_text(encoding="utf-8").replace("Type=notify", "Type=simple"),
                    encoding="utf-8")
    verdict = ustanovka.check_all(kopia_deploy)
    assert not verdict.passed
    assert "watchdog" in verdict.failed_names


def test_a_missing_watchdog_is_caught(kopia_deploy):
    unit = kopia_deploy / ustanovka.MAIN_UNIT
    unit.write_text(unit.read_text(encoding="utf-8").replace("WatchdogSec=120", "#WatchdogSec=120"),
                    encoding="utf-8")
    assert "watchdog" in ustanovka.check_all(kopia_deploy).failed_names


def test_a_missing_onfailure_is_caught(kopia_deploy):
    unit = kopia_deploy / ustanovka.MAIN_UNIT
    unit.write_text(unit.read_text(encoding="utf-8").replace("OnFailure=", "#OnFailure="),
                    encoding="utf-8")
    assert "onfailure" in ustanovka.check_all(kopia_deploy).failed_names


def test_a_local_system_timezone_is_caught(kopia_deploy):
    unit = kopia_deploy / ustanovka.MAIN_UNIT
    unit.write_text(unit.read_text(encoding="utf-8").replace("Environment=TZ=UTC",
                                                             "Environment=TZ=Europe/Berlin"),
                    encoding="utf-8")
    assert "timezone" in ustanovka.check_all(kopia_deploy).failed_names


def test_a_kill_instead_of_a_stop_is_caught(kopia_deploy):
    """One of exactly two ways to lose updates, and the only one the unit can prevent."""
    unit = kopia_deploy / ustanovka.MAIN_UNIT
    unit.write_text(unit.read_text(encoding="utf-8").replace("KillSignal=SIGTERM",
                                                             "KillSignal=SIGKILL"),
                    encoding="utf-8")
    assert "graceful stop" in ustanovka.check_all(kopia_deploy).failed_names


def test_a_stop_timeout_too_short_to_finish_an_update_is_caught(kopia_deploy):
    unit = kopia_deploy / ustanovka.MAIN_UNIT
    unit.write_text(unit.read_text(encoding="utf-8").replace("TimeoutStopSec=30",
                                                             "TimeoutStopSec=1"),
                    encoding="utf-8")
    assert "graceful stop" in ustanovka.check_all(kopia_deploy).failed_names


def test_a_restart_policy_that_loops_forever_on_broken_code_is_caught(kopia_deploy):
    unit = kopia_deploy / ustanovka.MAIN_UNIT
    unit.write_text(unit.read_text(encoding="utf-8").replace("StartLimitBurst=5",
                                                             "StartLimitBurst=0"),
                    encoding="utf-8")
    assert "restart policy" in ustanovka.check_all(kopia_deploy).failed_names


def test_an_unsubstituted_placeholder_is_caught(kopia_deploy):
    unit = kopia_deploy / ustanovka.MAIN_UNIT
    unit.write_text(unit.read_text(encoding="utf-8").replace("WorkingDirectory=@CHECKOUT@",
                                                             "WorkingDirectory=@PREFIX@"),
                    encoding="utf-8")
    verdict = ustanovka.check_all(kopia_deploy)
    assert not verdict.passed
    assert "placeholders" in verdict.failed_names


def test_the_live_check_is_skipped_loudly_and_never_silently_green(monkeypatch):
    """A check that turns green because it could not run is worse than one that fails."""
    monkeypatch.setattr(ustanovka.shutil, "which", lambda name: None)
    check = ustanovka.check_live(ustanovka.read_units(DEPLOY))
    assert check.passed is False
    assert "SKIPPED" in check.detail


def test_the_live_check_reports_a_unit_that_systemd_says_is_not_enabled(monkeypatch):
    class Finished:
        stdout = "disabled"
        stderr = ""

    monkeypatch.setattr(ustanovka.shutil, "which", lambda name: "/bin/systemctl")
    monkeypatch.setattr(ustanovka.subprocess, "run", lambda *a, **k: Finished())
    check = ustanovka.check_live(ustanovka.read_units(DEPLOY))
    assert not check.passed
    assert "not enabled" in check.detail


def test_the_install_script_dry_run_changes_nothing_and_is_readable_without_a_server(tmp_path):
    """``--proba`` is how this script is provable on a laptop that has no systemd at all.

    It is run for real here -- a dry run that is only claimed to be safe is not a dry run --
    and then the machine is checked for the two things it could have created behind our back.
    """
    import subprocess

    checkout = DEPLOY.parent
    before = sorted(path.name for path in checkout.iterdir())

    finished = subprocess.run(
        [shutil.which("bash") or "/bin/bash", str(DEPLOY / "ustanovka.sh"), "--proba"],
        capture_output=True, text=True, check=False,
    )

    assert finished.returncode == 0, finished.stderr
    assert "DRY RUN" in finished.stdout
    assert "would run: systemctl enable --now spetsmat-bot.service" in finished.stdout
    assert "Nothing was changed." in finished.stdout
    assert sorted(path.name for path in checkout.iterdir()) == before, (
        "the dry run created or removed something in the checkout"
    )


def test_the_install_script_refuses_an_argument_it_does_not_know():
    import subprocess

    finished = subprocess.run(
        [shutil.which("bash") or "/bin/bash", str(DEPLOY / "ustanovka.sh"), "--whatever"],
        capture_output=True, text=True, check=False,
    )
    assert finished.returncode != 0
    assert "unknown argument" in finished.stderr


# ------------------------------------------------- the watchdog debt, made machine-visible


def test_the_watchdog_is_declared_but_honestly_reported_as_not_wired_yet():
    """The unit is ahead of the code on purpose, and the gap is a check rather than a comment.

    The ping must come from inside the polling loop, which is in ``bot/`` -- read-only to
    this position.  So the declaration lives here and the hook is a named debt.  This test
    passes in BOTH states: it demands that the checker's answer match the code, not that the
    answer be "no".  The day ``bot/`` sends ``READY=1`` and ``WATCHDOG=1``, it keeps passing.
    """
    wired, detail = ustanovka.watchdog_is_wired()
    bot_source = "\n".join(path.read_text(encoding="utf-8")
                           for path in sorted((DEPLOY.parent / "bot").rglob("*.py")))
    really_wired = all(marker in bot_source for marker in ustanovka.NOTIFY_MARKERS)
    assert wired == really_wired, detail
    if not wired:
        assert "deploy/README.md" in detail, "the debt must say where the hook is written down"


def test_the_install_script_refuses_to_ship_a_watchdog_that_nothing_pings():
    """A Type=notify unit against a bot that never notifies never finishes starting.

    That would be a harness breaking the thing it exists to keep alive, so the script asks
    and neutralises rather than assuming.
    """
    script = (DEPLOY / "ustanovka.sh").read_text(encoding="utf-8")
    assert "proverka_ustanovki.py --storozh" in script
    assert "s|^Type=notify|Type=simple|" in script
    assert "s|^WatchdogSec=|#WatchdogSec=|" in script


def test_the_readme_names_the_exact_line_the_next_position_must_add():
    readme = (DEPLOY / "README.md").read_text(encoding="utf-8")
    for marker in ustanovka.NOTIFY_MARKERS:
        assert marker in readme, "deploy/README.md does not name %s" % marker
    assert "start_polling" in readme, "the README must say WHERE the hook goes, not only what it is"
