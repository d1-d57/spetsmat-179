"""The deploy script: the refusal, and the two ways updates could be lost.

The two time scenarios are run as real subprocesses -- the script is bash, and asserting on
what bash would do is not the same as running it.  Both scenarios use the schedule's fixed
known moments, so the result does not depend on the day this test suite happens to run.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from ops import proverka_ustanovki as ustanovka

DEPLOY = Path(ustanovka.DEPLOY)
CHECKOUT = DEPLOY.parent
VYKATKA = DEPLOY / "vykatka.sh"

#: The script's own exit code for "refused because a lesson is running".  Distinct from any
#: failure code on purpose: "refused deliberately" and "broke" must not look alike.
RC_REFUSED_LESSON = 3


def _run(*arguments: str, checkout: Path | None = None) -> subprocess.CompletedProcess:
    checkout = checkout or CHECKOUT
    return subprocess.run(
        [shutil.which("bash") or "/bin/bash", str(checkout / "deploy" / "vykatka.sh"), *arguments],
        capture_output=True, text=True, check=False, cwd=str(checkout),
    )


def _miniature_checkout(tmp_path: Path, clean: bool) -> Path:
    """A throwaway checkout carrying only what a dry run touches, with its own git state.

    The live checkout cannot be used for the scenarios below: whether IT is clean depends on
    what the person running the suite happens to have in their tree, and a test whose verdict
    depends on that is not a test of the deploy script.
    """
    target = tmp_path / ("clean" if clean else "dirty")
    (target / "deploy").mkdir(parents=True)
    (target / "ops").mkdir()
    shutil.copy2(VYKATKA, target / "deploy" / "vykatka.sh")
    shutil.copy2(CHECKOUT / "config.py", target / "config.py")
    for name in ("__init__.py", "raspisanie.py", "rezervnaya_kopia.py", "proverka_sredy.py"):
        shutil.copy2(CHECKOUT / "ops" / name, target / "ops" / name)
    subprocess.run(["git", "init", "-q"], cwd=target, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.invalid"], cwd=target, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=target, check=True)
    if clean:
        subprocess.run(["git", "add", "-A"], cwd=target, check=True)
        subprocess.run(["git", "commit", "-qm", "state"], cwd=target, check=True)
    return target


@pytest.fixture
def chistyj_checkout(tmp_path: Path) -> Path:
    return _miniature_checkout(tmp_path, clean=True)


def _shell_without_comments(path: Path) -> str:
    """The script with its comment lines dropped.

    This file explains at length WHY blue-green is impossible and WHY a kill loses updates,
    so a grep over the whole text would trip on the very sentences that state the rules.
    The question is what the script DOES.
    """
    return "\n".join(line for line in path.read_text(encoding="utf-8").splitlines()
                      if not line.lstrip().startswith("#"))


# --------------------------------------------------------- scenario 1: a lesson is running


def test_a_deploy_during_a_lesson_is_refused_and_says_why():
    """ЗЕЛЁНОЕ ЗДЕСЬ ЕСТЬ ПРОВАЛ: a green run in this scenario is the position failing."""
    finished = _run("--proba", "--chas-zanyatia")
    assert finished.returncode == RC_REFUSED_LESSON, (
        "the deploy script did NOT refuse during a lesson (rc=%d)" % finished.returncode
    )
    assert "REFUSED" in finished.stderr
    assert "TelegramConflictError" in finished.stderr, "the refusal must say what it prevents"
    assert "lesson window" in finished.stderr


def test_the_refusal_happens_before_anything_is_changed():
    """A refusal that arrives after `git pull` is a half-deploy, not a refusal."""
    finished = _run("--proba", "--chas-zanyatia")
    combined = finished.stdout + finished.stderr
    for later_step in ("git pull", "apply migrations", "restart spetsmat-bot.service", "snapshot"):
        assert later_step not in combined, (
            "the script reached %r before refusing" % later_step
        )


# ------------------------------------------------------------ scenario 2: no lesson at all


def test_a_deploy_outside_lesson_hours_proceeds_through_every_step(chistyj_checkout):
    finished = _run("--proba", "--svobodnyj-chas", checkout=chistyj_checkout)
    assert finished.returncode == 0, finished.stderr
    for step in ("snapshot before the migration", "git pull", "apply migrations",
                 "environment check", "restart spetsmat-bot.service"):
        assert step in finished.stdout, "the dry run never reached %r" % step
    assert "Nothing was changed." in finished.stdout


def test_the_snapshot_is_taken_before_the_migration_and_not_after(chistyj_checkout):
    """A snapshot taken after a bad migration is a snapshot of the damage."""
    out = _run("--proba", "--svobodnyj-chas", checkout=chistyj_checkout).stdout
    assert out.index("snapshot before the migration") < out.index("apply migrations")


def test_the_environment_is_checked_while_the_old_process_is_still_serving(chistyj_checkout):
    out = _run("--proba", "--svobodnyj-chas", checkout=chistyj_checkout).stdout
    assert out.index("environment check") < out.index("restart spetsmat-bot.service")


def test_an_unknown_argument_is_refused():
    finished = _run("--whatever")
    assert finished.returncode != 0
    assert "unknown argument" in finished.stderr


# ------------------------------------------------ the two ways updates could be lost


def test_the_bot_does_not_drop_pending_updates_at_startup():
    """The first of exactly two ways to lose updates, and it lives in read-only code.

    Telegram keeps undelivered updates for a day and re-delivers them, so a restart loses
    nothing by itself.  ``drop_pending_updates=True`` at ``start_polling`` would throw away
    every tap made during the deploy.  ``bot/`` is read-only to this position, so this test
    does not fix anything -- it makes a future edit that breaks it fail here.
    """
    entry = (CHECKOUT / "bot" / "__main__.py").read_text(encoding="utf-8")
    assert "drop_pending_updates" not in entry, (
        "bot/__main__.py now drops pending updates: every tap made during a deploy is lost"
    )


def test_the_deploy_stops_the_bot_gracefully_and_never_kills_it():
    """The second of the two ways, and this one the deploy script itself can get wrong."""
    code = _shell_without_comments(VYKATKA)
    assert "systemctl restart" in code
    for killer in ("pkill", "kill -9", "SIGKILL", "systemctl kill"):
        assert killer not in code, "deploy/vykatka.sh uses %r instead of a graceful stop" % killer


def test_the_deploy_asks_the_one_schedule_and_does_not_carry_its_own_copy():
    """Two answers to 'is it a lesson now' would eventually disagree."""
    code = _shell_without_comments(VYKATKA)
    assert "ops/raspisanie.py" in code
    for hardcoded in ("Mon", "Thu", "16:00", "19:00"):
        assert hardcoded not in code, (
            "deploy/vykatka.sh hard-codes %r instead of asking ops/raspisanie.py" % hardcoded
        )


def test_blue_green_is_not_attempted():
    """Impossible here, not merely redundant: two pollers on one token is the same conflict."""
    code = _shell_without_comments(VYKATKA).lower()
    for attempt in ("blue", "spetsmat-bot-b", "second instance"):
        assert attempt not in code, "deploy/vykatka.sh attempts %r" % attempt
    assert code.count("systemctl restart") == 1, "more than one unit is being restarted"


def test_a_dirty_checkout_is_refused_before_the_pull(tmp_path):
    """`git pull` onto uncommitted work either refuses or merges over it; stop first instead."""
    dirty = _miniature_checkout(tmp_path, clean=False)
    finished = _run("--proba", "--svobodnyj-chas", checkout=dirty)
    assert finished.returncode == 4, finished.stdout + finished.stderr
    assert "uncommitted changes" in finished.stderr
    assert "git pull" not in finished.stdout
