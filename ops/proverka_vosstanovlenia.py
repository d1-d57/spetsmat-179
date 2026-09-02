"""The restore check.  A SEPARATE task, never an appendix to the backup.

WHY IT IS SEPARATE (finalised at the interview)
-----------------------------------------------
A backup nobody restored is not a backup.  By the owner's own list this is the most
expensive failure of all, because it is discovered at the only moment when nothing can be
done about it.  The backup script and this script therefore run on different timers, and
this one never calls that one: a check that shares code with the thing it checks agrees
with it by construction.

WHAT IT ASSERTS -- ALL THREE, EVERY TIME
----------------------------------------
1. ``pragma integrity_check`` on the unpacked snapshot says ``ok``;
2. at least fifty students who have not left are in the roster (the cohort is fifty-six --
    a snapshot with twenty is a snapshot of something else);
3. the newest mark is neither older than a week nor in the future (a file that opens and
    restores but stopped receiving marks a month ago is a backup of a dead bot; and a single
    future-dated mark would otherwise satisfy "not older than a week" forever).

WHAT THIS CHECK DELIBERATELY CANNOT DO
--------------------------------------
It cannot tell OUR database from a different one of the same shape and size.  A snapshot of
another school's conduit with fifty-six students and a fresh mark passes all three.  Nothing
here anchors on an installation identity, and adding one would mean writing to the schema,
which is read-only to the position that wrote this.  Named as a limit rather than left to be
discovered: this check answers "is the backup usable?", not "is it ours?".

All three must pass before a ping goes out, and SILENCE MEANS ALARM: the alerting watches
for the heartbeat, so a check that dies before it can report is as loud as one that fails.
This is the reason the ping is the LAST thing that happens here and is never sent early.

``--na-porchennom`` -- THE MODE THAT PROVES THE CHECK CAN GO RED
---------------------------------------------------------------
A check that has never gone red is a hope, not a check.  This mode builds three snapshots,
each broken in the way that one of the three assertions exists to catch, and runs the real
check over them.  Exit codes are deliberately distinct, and NEITHER of them is 0:

    rc=1  every corruption was caught -- the demanded outcome, the check works;
    rc=2  a corruption slipped through (a FALSE GREEN) -- the check is broken.

Green here would mean the check cannot fail, which is the failure this position is about.
"""

from __future__ import annotations

import argparse
import gzip
import os
import shutil
import sqlite3
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config  # noqa: E402  -- deliberately after the path bootstrap above
from ops import rezervnaya_kopia  # noqa: E402

#: The cohort is fifty-six.  Below this the snapshot is of something else.
MIN_STUDENTS = 50

#: How stale the newest mark may be before the snapshot is considered a backup of a bot
#: that has stopped working.  Lessons are twice a week, so a week is two missed lessons.
MAX_MARK_AGE_DAYS = 7

#: How far into the future a mark may legitimately sit.  Not zero: the snapshot is taken at
#: one instant and checked at another, clocks between machines differ by seconds, and a mark
#: recorded during the snapshot may carry a timestamp a hair ahead of the checker's clock.
#: A day is generous for that and still nowhere near a wrong-year date.
FUTURE_TOLERANCE = timedelta(days=1)

#: The three names, used in the output and in the tests.  Order is the order they run in.
CHECK_NAMES = ("integrity", "roster", "freshness")


@dataclass(frozen=True)
class OneCheck:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class Verdict:
    """The result carries its own COVERAGE: how many checks ran, not only how many passed.

    "no problems found" and "no problems found, 3 of 3 checked" look the same and are not.
    """

    checks: tuple[OneCheck, ...]
    snapshot: Path | None
    error: str | None = None

    @property
    def passed(self) -> bool:
        return self.error is None and bool(self.checks) and all(check.passed for check in self.checks)

    @property
    def failed_names(self) -> tuple[str, ...]:
        return tuple(check.name for check in self.checks if not check.passed)

    def report(self) -> str:
        lines = ["snapshot: %s" % (self.snapshot if self.snapshot else "(none)")]
        if self.error:
            lines.append("FAILED before any check could run: %s" % self.error)
        for check in self.checks:
            lines.append("  %-10s %s  %s" % (check.name, "PASS" if check.passed else "RED ", check.detail))
        lines.append(
            "verdict: %s -- passed %d of %d checks"
            % ("GREEN" if self.passed else "RED", sum(1 for c in self.checks if c.passed), len(self.checks))
        )
        if not self.passed and self.failed_names:
            lines.append("red checks: %s" % ", ".join(self.failed_names))
        return "\n".join(lines)


def unpack(archive: Path, into: Path) -> Path:
    """Gunzip the snapshot into ``into`` and return the plain database path."""
    plain = Path(into) / "restored.db"
    with gzip.open(archive, "rb") as source, plain.open("wb") as sink:
        shutil.copyfileobj(source, sink)
    return plain


def check_snapshot(archive: Path | str, now: datetime | None = None) -> Verdict:
    """Unpack ``archive`` and run all three assertions over it.

    The snapshot is opened as a plain ``sqlite3.connect`` and NOT through ``infra.db``: the
    restore situation is a bare file on a machine that may not have this checkout, and a
    check that needs the application's connection helper is not checking a restore.
    """
    archive = Path(archive)
    now = now or datetime.now(tz=timezone.utc)
    if not archive.exists():
        return Verdict(checks=(), snapshot=archive, error="snapshot %s does not exist" % archive)

    with tempfile.TemporaryDirectory(prefix="spetsmat-restore-") as staging:
        try:
            plain = unpack(archive, Path(staging))
        except (OSError, EOFError, gzip.BadGzipFile) as failure:
            return Verdict(checks=(), snapshot=archive, error="cannot gunzip: %s" % failure)

        try:
            connection = sqlite3.connect(str(plain))
        except sqlite3.Error as failure:
            return Verdict(checks=(), snapshot=archive, error="cannot open: %s" % failure)

        try:
            checks = (
                _check_integrity(connection),
                _check_roster(connection),
                _check_freshness(connection, now),
            )
        finally:
            connection.close()

    return Verdict(checks=checks, snapshot=archive)


def _check_integrity(connection: sqlite3.Connection) -> OneCheck:
    try:
        rows = connection.execute("pragma integrity_check").fetchall()
    except sqlite3.DatabaseError as failure:
        return OneCheck("integrity", False, "pragma failed: %s" % failure)
    answer = rows[0][0] if rows else "(empty)"
    return OneCheck("integrity", answer == "ok", "pragma integrity_check -> %s" % answer)


def _check_roster(connection: sqlite3.Connection) -> OneCheck:
    try:
        count = connection.execute(
            "select count(*) from students where status <> 'left'"
        ).fetchone()[0]
    except sqlite3.DatabaseError as failure:
        return OneCheck("roster", False, "cannot count students: %s" % failure)
    return OneCheck("roster", count >= MIN_STUDENTS,
                    "%d student(s) not left, need >= %d" % (count, MIN_STUDENTS))


def _check_freshness(connection: sqlite3.Connection, now: datetime) -> OneCheck:
    try:
        newest = connection.execute("select max(valid_at) from marks").fetchone()[0]
    except sqlite3.DatabaseError as failure:
        return OneCheck("freshness", False, "cannot read marks: %s" % failure)
    if newest is None:
        return OneCheck("freshness", False, "no marks at all in the snapshot")
    try:
        moment = datetime.strptime(newest[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return OneCheck("freshness", False, "newest valid_at %r is not an ISO instant" % newest)
    age = now - moment
    # BOTH ENDS.  An upper bound alone is a check that any single future-dated mark disarms
    # FOREVER: `max(valid_at)` then stays in the future, the age stays negative, and
    # "not older than a week" is satisfied by a journal that stopped months ago.  One
    # teacher's phone with a wrong clock, or one import with a bad date, is enough -- and the
    # schema cannot stop it, since the CHECK on `valid_at` is a glob over the ISO shape and
    # a well-formed 2027 passes it.  Found by the §3 verifier on a snapshot whose real
    # activity ended 45 days ago and which was reported GREEN, age -400 days.
    if age < -FUTURE_TOLERANCE:
        return OneCheck("freshness", False,
                        "newest mark %s is %d day(s) in the FUTURE -- a clock is wrong somewhere, "
                        "and until it is fixed this check cannot see a journal that stopped"
                        % (newest, -age.days))
    return OneCheck("freshness", age <= timedelta(days=MAX_MARK_AGE_DAYS),
                    "newest mark %s, age %d day(s), limit %d" % (newest, age.days, MAX_MARK_AGE_DAYS))


# ------------------------------------------------------------------- deliberate damage
#
# Three corruptions, one per assertion.  They live here and not in the tests because the
# готовности criterion runs ``--na-porchennom`` from the command line: the proof that the
# check can go red must be available to the owner without pytest.


def corrupt_pages(plain: Path) -> str:
    """Byte rot inside the b-tree -- the failure ``pragma integrity_check`` exists for."""
    size = plain.stat().st_size
    with plain.open("r+b") as handle:
        # Past the 100-byte file header and the first page, so the file still OPENS and the
        # damage is only found by walking the tree.  A file that fails to open would be
        # caught by any check at all and would prove nothing about this one.
        handle.seek(min(4096, max(size // 2, 100)))
        handle.write(os.urandom(min(2048, max(size // 4, 64))))
    return "random bytes written over page data"


def corrupt_roster(plain: Path) -> str:
    """A truncated roster -- the snapshot of a different, smaller world."""
    connection = sqlite3.connect(str(plain))
    try:
        connection.execute("pragma foreign_keys = off")
        connection.execute("delete from students where id > 10")
        connection.commit()
        left = connection.execute("select count(*) from students").fetchone()[0]
    finally:
        connection.close()
    return "students reduced to %d" % left


def corrupt_future(plain: Path) -> str:
    """One mark dated far in the future -- the corruption that USED TO disarm the check.

    Added after the §3 verifier built exactly this snapshot and got GREEN out of it.  The
    fix without this corruption in the self-test would be a hope: nothing would go red if
    somebody restored the old comparison.
    """
    connection = sqlite3.connect(str(plain))
    try:
        connection.execute("drop trigger if exists marks_append_only_update")
        stale = (datetime.now(tz=timezone.utc) - timedelta(days=45)).strftime("%Y-%m-%dT%H:%M:%SZ")
        connection.execute("update marks set valid_at = ?", (stale,))
        ahead = (datetime.now(tz=timezone.utc) + timedelta(days=400)).strftime("%Y-%m-%dT%H:%M:%SZ")
        connection.execute(
            "insert into marks (student_id, problem_id, event, teacher_id, valid_at, "
            "recorded_at, source) values (1, 1, 'assert', 1, ?, ?, 'импорт')",
            (ahead, ahead),
        )
        connection.commit()
    finally:
        connection.close()
    return "activity stopped 45 days ago, one mark dated 400 days ahead"


def corrupt_freshness(plain: Path) -> str:
    """A journal that stopped -- the file restores, and the bot behind it died a month ago.

    ``marks`` is append-only by trigger, which is exactly right for the application and in
    the way here, so the trigger is dropped in this THROWAWAY copy first.  The copy is
    deleted with the temp directory; the live database is never opened by this function.
    """
    connection = sqlite3.connect(str(plain))
    try:
        connection.execute("drop trigger if exists marks_append_only_update")
        stale = (datetime.now(tz=timezone.utc) - timedelta(days=40)).strftime("%Y-%m-%dT%H:%M:%SZ")
        connection.execute("update marks set valid_at = ?", (stale,))
        connection.commit()
    finally:
        connection.close()
    return "every mark pushed back to 40 days ago"


#: Corruption -> the check that MUST catch it.  The mapping is the coverage claim: three
#: corruptions, three assertions, one each.
DAMAGE = (
    ("page rot", corrupt_pages, "integrity"),
    ("truncated roster", corrupt_roster, "roster"),
    ("stale journal", corrupt_freshness, "freshness"),
    ("journal stopped, one mark dated in the future", corrupt_future, "freshness"),
)


def run_self_test(source_db: Path | None = None) -> int:
    """Build a broken snapshot per corruption and demand that the check goes red on each.

    Returns 1 when every corruption was caught (the demanded outcome) and 2 when any of
    them slipped through.  It never returns 0: a green here would mean the check cannot
    fail, which is the failure this whole position exists to prevent.
    """
    with tempfile.TemporaryDirectory(prefix="spetsmat-selftest-") as staging:
        workspace = Path(staging)
        try:
            database = _build_reference_database(workspace / "reference.db") if source_db is None \
                else Path(source_db)
        except Exception as failure:  # noqa: BLE001 -- the reason must reach the operator verbatim
            print("self-test could not even build a database to break: %s" % failure, file=sys.stderr)
            return 2

        caught = 0
        wrong_check = 0
        for title, damage, expected in DAMAGE:
            archive = _snapshot_of(database, workspace, title)
            plain = workspace / ("broken-%s.db" % expected)
            with gzip.open(archive, "rb") as source, plain.open("wb") as sink:
                shutil.copyfileobj(source, sink)
            what = damage(plain)
            broken_archive = workspace / ("broken-%s.db.gz" % expected)
            with plain.open("rb") as source, gzip.open(broken_archive, "wb") as sink:
                shutil.copyfileobj(source, sink)

            verdict = check_snapshot(broken_archive)
            print("-- corruption: %s (%s)" % (title, what))
            print(verdict.report())
            if verdict.passed:
                print("   FALSE GREEN: %r was not caught by anything" % title)
                continue
            caught += 1
            if expected not in verdict.failed_names:
                wrong_check += 1
                print("   caught, but by %s and not by the expected %s"
                      % (", ".join(verdict.failed_names), expected))

    total = len(DAMAGE)
    print()
    print("self-test: %d of %d corruptions went red; false greens %d" % (caught, total, total - caught))
    if caught < total:
        print("VERDICT: the restore check is BROKEN -- a corrupted snapshot passed it.")
        return 2
    if wrong_check:
        print("VERDICT: every corruption went red, but %d was caught by the wrong assertion; "
              "coverage of the individual checks is not proven." % wrong_check)
        return 2
    print("VERDICT: the restore check can go red, proven on %d of %d corruptions, "
          "each by its own assertion." % (total, total))
    return 1


def _build_reference_database(path: Path) -> Path:
    """A healthy database with the real cohort, built from this repository's migrations."""
    from infra.db import apply_migrations, connect

    apply_migrations(path)
    connection = connect(path)
    now = datetime.now(tz=timezone.utc)
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        connection.execute(
            "insert into sheets (id, number, title, issued_at, ord) values (1, '1', 'sheet one', ?, 1)",
            (stamp,),
        )
        connection.execute(
            "insert into problems (id, sheet_id, label, kind, ord) values (1, 1, '1', 'обязательная', 1)"
        )
        connection.execute("insert into teachers (id, name, is_owner) values (1, 'teacher', 1)")
        for number in range(1, 57):
            connection.execute(
                "insert into students (id, surname, name, class, status, first_sheet_id) "
                "values (?, ?, ?, '8', 'active', 1)",
                (number, "surname%02d" % number, "name%02d" % number),
            )
        connection.execute(
            "insert into marks (student_id, problem_id, event, teacher_id, valid_at, recorded_at, source) "
            "values (1, 1, 'assert', 1, ?, ?, 'кнопка')",
            (stamp, stamp),
        )
        # A healthy reference must actually be healthy, or the self-test proves nothing.
        assert check_snapshot_of_plain(path).passed, "the reference database is not green"
    finally:
        connection.close()
    return path


def check_snapshot_of_plain(plain: Path) -> Verdict:
    """Run the three assertions over an UNPACKED database, for the reference sanity check."""
    connection = sqlite3.connect(str(plain))
    try:
        checks = (
            _check_integrity(connection),
            _check_roster(connection),
            _check_freshness(connection, datetime.now(tz=timezone.utc)),
        )
    finally:
        connection.close()
    return Verdict(checks=checks, snapshot=plain)


def _snapshot_of(database: Path, workspace: Path, title: str) -> Path:
    return rezervnaya_kopia.make_backup(database, workspace / "snapshots", label="ruchnoj")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Restore check: unpack the latest snapshot and assert it is usable."
    )
    parser.add_argument("--na-porchennom", action="store_true",
                        help="prove the check can go red: break a snapshot three ways and run it "
                             "(rc=1 every corruption caught, rc=2 something slipped through)")
    parser.add_argument("--kopia", default=None, help="check this snapshot instead of the latest")
    parser.add_argument("--kuda", default=None, help="directory of snapshots")
    args = parser.parse_args(argv)

    if args.na_porchennom:
        return run_self_test()

    archive = Path(args.kopia) if args.kopia else rezervnaya_kopia.latest_snapshot(args.kuda)
    if archive is None:
        # No snapshot at all is an ALARM, not a green: it is the state the machine is in
        # the moment the backup timer stops firing.
        print("restore check RED: no snapshot found in %s"
              % (args.kuda or rezervnaya_kopia.DEFAULT_BACKUP_DIR), file=sys.stderr)
        return 1

    verdict = check_snapshot(archive)
    print(verdict.report())
    return 0 if verdict.passed else 1


if __name__ == "__main__":
    sys.exit(main())
