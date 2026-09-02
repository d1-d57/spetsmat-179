"""The ONE place that knows when a lesson happens.

Everything that must not collide with a lesson reads this module: the deploy script
refuses inside the window, and the backup timers hang their "before" and "after"
snapshots on its edges.  Two answers to "is it a lesson now?" would eventually disagree,
and the disagreement would surface as a deploy during a lesson -- the exact failure this
position exists to prevent.

TIME, ONCE AND FOR ALL (task §5)
--------------------------------
The system clock is UTC.  Moscow is obtained through ``ZoneInfo(config.TZ_DISPLAY)`` and
NEVER through ``timedelta(hours=3)``.  Russia does not shift its clocks and Germany does:
with a Berlin system zone a hard-coded offset moves the whole timetable by an hour twice
a year, and the timetable is what decides whether a deploy is allowed.

WHY A GUARD AROUND THE LESSON
-----------------------------
The forbidden window is wider than the lesson itself.  A deploy that starts one minute
before the bell is a deploy during the lesson: ``git pull`` plus ``yoyo apply`` plus a
restart is not instantaneous, and teachers arrive early and mark late.  The guard turns
"do not deploy during a lesson" into something a script can actually enforce.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# The repository root, on the path before ``import config``.  Running this file directly
# (``python3 ops/raspisanie.py``) puts ``ops/`` on ``sys.path`` and NOT the checkout root,
# so the import below would fail for exactly the caller the готовности criterion uses.
# Under pytest the root is already there via ``pythonpath = ["."]``; the insert is
# idempotent and costs nothing.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config  # noqa: E402  -- deliberately after the path bootstrap above

# --------------------------------------------------------------------------- timetable
#
# ISO-8601 weekday numbers, Monday = 1 -- the same convention as ``enrollment.weekday`` in
# the schema, so the two never need translating.  Two lessons a week: Monday and Thursday.
# The evidence is in the schema itself (``migrations/001_init.sql``: "Кахиани = Ваня on
# Mon, Ян on Thu"), not guessed.
#
# THE OWNER EDITS THESE FOUR CONSTANTS AND NOTHING ELSE when the timetable changes.

#: Lesson days, ISO weekday numbers.
LESSON_WEEKDAYS = (1, 4)

#: When the lesson starts and ends, Moscow wall clock.
LESSON_START = time(16, 0)
LESSON_END = time(19, 0)

#: How far the freeze reaches around the lesson, in minutes.  Before: teachers are already
#: marking attendance.  After: marks are still being entered on the way out.
GUARD_BEFORE_MINUTES = 60
GUARD_AFTER_MINUTES = 60


MOSCOW = ZoneInfo(config.TZ_DISPLAY)


def moscow_now(moment: datetime | None = None) -> datetime:
    """Return ``moment`` (or now) as an aware Moscow datetime.

    A naive ``moment`` is read as UTC, because the system clock of the machine this runs
    on is UTC by unit declaration (``Environment=TZ=UTC``).  Reading it as local time is
    the mistake this function exists to make impossible.
    """
    if moment is None:
        return datetime.now(tz=MOSCOW)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ZoneInfo("UTC"))
    return moment.astimezone(MOSCOW)


def lesson_window(day: date) -> tuple[datetime, datetime] | None:
    """The frozen interval on ``day``, guards included, or ``None`` if it is not a lesson day."""
    if day.isoweekday() not in LESSON_WEEKDAYS:
        return None
    start = datetime.combine(day, LESSON_START, tzinfo=MOSCOW) - timedelta(minutes=GUARD_BEFORE_MINUTES)
    end = datetime.combine(day, LESSON_END, tzinfo=MOSCOW) + timedelta(minutes=GUARD_AFTER_MINUTES)
    return start, end


def is_lesson_time(moment: datetime | None = None) -> tuple[bool, str]:
    """``(frozen, reason)`` -- is a deploy forbidden at ``moment``, and in one sentence why.

    The reason is returned rather than printed because both callers need it in a different
    place: the deploy script prints it to the operator, the tests assert on it.  A refusal
    whose reason is not shown is indistinguishable from a crash.
    """
    now = moscow_now(moment)
    # A lesson that starts late on the previous day cannot reach past midnight with these
    # constants, but the guard is checked on both the current and the previous day anyway:
    # widening GUARD_AFTER_MINUTES must not silently open a hole at midnight.
    for day in (now.date() - timedelta(days=1), now.date()):
        window = lesson_window(day)
        if window is None:
            continue
        start, end = window
        if start <= now <= end:
            return True, (
                "lesson window %s..%s Moscow on %s (guard %d min before / %d min after); "
                "now %s Moscow"
                % (
                    start.strftime("%H:%M"),
                    end.strftime("%H:%M"),
                    day.isoformat(),
                    GUARD_BEFORE_MINUTES,
                    GUARD_AFTER_MINUTES,
                    now.strftime("%Y-%m-%d %H:%M"),
                )
            )
    return False, "no lesson window around %s Moscow" % now.strftime("%Y-%m-%d %H:%M")


def next_lesson_day(day: date) -> date:
    """The first lesson day strictly after ``day``.  Used only by the human-facing message."""
    for ahead in range(1, 8):
        candidate = day + timedelta(days=ahead)
        if candidate.isoweekday() in LESSON_WEEKDAYS:
            return candidate
    raise AssertionError("LESSON_WEEKDAYS is empty -- the timetable has no lessons at all")


# ------------------------------------------------------------------------- known moments
#
# Two fixed moments the deploy script and the tests use to PROVE both branches on a
# machine that has no lessons and no server.  They are UTC, because that is what the
# system clock reads; the Moscow conversion is the thing under test.
#
# 2026-09-07 is a Monday, 2026-09-09 a Wednesday -- both verified by ``date.isoweekday``
# in ``tests/ops/test_raspisanie.py``, never asserted from memory.

#: Monday 2026-09-07, 17:00 Moscow = 14:00 UTC -- inside the lesson.
LESSON_MOMENT_UTC = datetime(2026, 9, 7, 14, 0)

#: Wednesday 2026-09-09, 17:00 Moscow = 14:00 UTC -- not a lesson day at all.
FREE_MOMENT_UTC = datetime(2026, 9, 9, 14, 0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Answer 'is a deploy frozen right now?' -- rc=1 when it is frozen."
    )
    moment_group = parser.add_mutually_exclusive_group()
    moment_group.add_argument(
        "--chas-zanyatia",
        action="store_true",
        help="pretend it is a lesson hour (a fixed known moment), instead of asking the clock",
    )
    moment_group.add_argument(
        "--svobodnyj-chas",
        action="store_true",
        help="pretend it is a free hour (a fixed known moment), instead of asking the clock",
    )
    args = parser.parse_args(argv)

    moment = None
    if args.chas_zanyatia:
        moment = LESSON_MOMENT_UTC
    elif args.svobodnyj_chas:
        moment = FREE_MOMENT_UTC

    frozen, reason = is_lesson_time(moment)
    if frozen:
        print("frozen: %s" % reason)
        return 1
    print("free: %s" % reason)
    return 0


if __name__ == "__main__":
    sys.exit(main())
