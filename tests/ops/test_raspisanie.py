"""The timetable, and in particular the two things a hard-coded offset would break.

The interesting assertion here is not "Monday is a lesson day" -- it is that the Moscow
answer is obtained through the zone database.  A machine whose system zone is Berlin and
a machine whose system zone is UTC must give the SAME verdict for the same instant, and
with ``timedelta(hours=3)`` they do not, twice a year.
"""

from __future__ import annotations

import time as time_module
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from ops import raspisanie


def test_the_fixed_moments_really_are_the_days_they_claim():
    """The two known moments are asserted, never taken on trust from a comment."""
    assert raspisanie.LESSON_MOMENT_UTC.date().isoweekday() == 1, "LESSON_MOMENT_UTC must be a Monday"
    assert raspisanie.FREE_MOMENT_UTC.date().isoweekday() == 3, "FREE_MOMENT_UTC must be a Wednesday"
    assert 1 in raspisanie.LESSON_WEEKDAYS
    assert 3 not in raspisanie.LESSON_WEEKDAYS


def test_lesson_hour_is_frozen_and_says_why():
    frozen, reason = raspisanie.is_lesson_time(raspisanie.LESSON_MOMENT_UTC)
    assert frozen is True
    assert "lesson window" in reason
    # A refusal without a reason is indistinguishable from a crash, so the reason must
    # actually carry the numbers a human needs to argue with it.
    assert "2026-09-07" in reason


def test_free_hour_is_not_frozen():
    frozen, reason = raspisanie.is_lesson_time(raspisanie.FREE_MOMENT_UTC)
    assert frozen is False
    assert "no lesson window" in reason


def test_guard_edges_are_inclusive_and_one_minute_outside_is_free():
    start, end = raspisanie.lesson_window(date(2026, 9, 7))
    assert raspisanie.is_lesson_time(start.astimezone(ZoneInfo("UTC")).replace(tzinfo=None))[0] is True
    assert raspisanie.is_lesson_time(end.astimezone(ZoneInfo("UTC")).replace(tzinfo=None))[0] is True
    just_before = (start - timedelta(minutes=1)).astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
    assert raspisanie.is_lesson_time(just_before)[0] is False


def test_no_lesson_window_on_a_non_lesson_day():
    assert raspisanie.lesson_window(date(2026, 9, 9)) is None


@pytest.mark.parametrize("system_zone", ["UTC", "Europe/Berlin", "Europe/Moscow"])
def test_verdict_does_not_depend_on_the_system_zone(system_zone, monkeypatch):
    """The whole point of §5: the answer is a property of the instant, not of the machine.

    Berlin is in the list on purpose -- it is the zone that shifts while Moscow does not,
    and it is the zone under which a ``timedelta(hours=3)`` implementation gives a
    different verdict for the same instant in summer and in winter.
    """
    monkeypatch.setenv("TZ", system_zone)
    if hasattr(time_module, "tzset"):
        time_module.tzset()
    try:
        assert raspisanie.is_lesson_time(raspisanie.LESSON_MOMENT_UTC)[0] is True
        assert raspisanie.is_lesson_time(raspisanie.FREE_MOMENT_UTC)[0] is False
    finally:
        monkeypatch.undo()
        if hasattr(time_module, "tzset"):
            time_module.tzset()


def test_naive_moments_are_read_as_utc_not_as_local_time():
    """A naive datetime is the system clock, and the system clock is UTC by unit declaration."""
    naive = datetime(2026, 9, 7, 14, 0)
    aware = datetime(2026, 9, 7, 14, 0, tzinfo=ZoneInfo("UTC"))
    assert raspisanie.moscow_now(naive) == raspisanie.moscow_now(aware)
    assert raspisanie.moscow_now(naive).hour == 17


def test_cli_returns_one_on_a_lesson_hour_and_zero_on_a_free_hour(capsys):
    assert raspisanie.main(["--chas-zanyatia"]) == 1
    assert "frozen" in capsys.readouterr().out
    assert raspisanie.main(["--svobodnyj-chas"]) == 0
    assert "free" in capsys.readouterr().out


def test_next_lesson_day_is_a_lesson_day():
    assert raspisanie.next_lesson_day(date(2026, 9, 9)).isoweekday() in raspisanie.LESSON_WEEKDAYS
