"""Prove the deployment is correctly declared -- on a machine that has no systemd.

There is no server yet and getting one is not this position's job, so every claim the unit
files make has to be checkable HERE.  This module reads ``deploy/`` and asserts, directive
by directive, the things whose absence is invisible until the day they matter:

  * ``systemctl enable`` for every unit that has an ``[Install]`` section -- THE most
    frequent real failure on the owner's list.  A unit that is only started runs until the
    first reboot and then is gone, and nothing anywhere says why;
  * ``WatchdogSec`` together with ``Type=notify``, because a watchdog on a unit that does
    not use the notify protocol is a line of text and nothing more;
  * ``Restart=always``, ``RestartSec=5`` and a burst limit of five per five minutes -- the
    unit must recover from a broken network forever and give up on broken code;
  * ``OnFailure=`` on every unit that can give up, since a stop nobody hears is no stop;
  * ``TZ=UTC`` in the service environment, because the timetable is decided in code;
  * a graceful stop (``SIGTERM`` and a real ``TimeoutStopSec``), because killing the process
    instead of stopping it is one of the only two ways to lose updates;
  * every ``@PLACEHOLDER@`` in the units is one ``deploy/ustanovka.sh`` substitutes.

``--zhivaya`` additionally asks systemd itself (``systemctl is-enabled``).  On a machine
without systemd it says so and skips that part rather than passing silently: a check that
turns green because it could not run is worse than one that fails.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEPLOY = ROOT / "deploy"
INSTALL_SCRIPT = DEPLOY / "ustanovka.sh"

#: The unit that runs the bot -- the one with the watchdog and the restart policy.
MAIN_UNIT = "spetsmat-bot.service"

PLACEHOLDER = re.compile(r"@[A-Z_]+@")


@dataclass(frozen=True)
class OneCheck:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class Verdict:
    checks: tuple[OneCheck, ...]

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(check.passed for check in self.checks)

    @property
    def failed_names(self) -> tuple[str, ...]:
        return tuple(check.name for check in self.checks if not check.passed)

    def report(self) -> str:
        lines = ["  %-22s %s  %s" % (c.name, "PASS" if c.passed else "RED ", c.detail)
                 for c in self.checks]
        lines.append("verdict: %s -- passed %d of %d checks"
                     % ("GREEN" if self.passed else "RED",
                        sum(1 for c in self.checks if c.passed), len(self.checks)))
        if not self.passed:
            lines.append("red checks: %s" % ", ".join(self.failed_names))
        return "\n".join(lines)


def read_units(deploy_dir: Path | str | None = None) -> dict[str, str]:
    directory = Path(deploy_dir) if deploy_dir is not None else DEPLOY
    return {path.name: path.read_text(encoding="utf-8")
            for path in sorted(directory.iterdir())
            if path.suffix in (".service", ".timer")}


def directive(text: str, key: str) -> str | None:
    """The value of ``Key=`` in a unit, ignoring comments and continuation lines."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            continue
        name, _, value = stripped.partition("=")
        if name.strip() == key:
            return value.strip()
    return None


def units_needing_enable(units: dict[str, str]) -> list[str]:
    """Every unit carrying an ``[Install]`` section, i.e. every unit ``enable`` applies to.

    Derived from the files rather than from a list, so a unit added tomorrow is covered
    without anybody remembering to add it here -- which is exactly the kind of remembering
    that fails.
    """
    return [name for name, text in units.items() if "[Install]" in text]


ENABLE_LIST = re.compile(r"ENABLE_UNITS=\((?P<body>[^)]*)\)", re.MULTILINE)


def units_the_script_enables(script_text: str) -> list[str]:
    """The names in ``ENABLE_UNITS=( ... )``, which is the list the script loops over.

    Parsed rather than grepped: a unit name that merely OCCURS somewhere in the script --
    in the template list, in a comment -- would satisfy a grep while never being enabled,
    and that is precisely the failure this check exists for.
    """
    found = ENABLE_LIST.search(script_text)
    if not found:
        return []
    body = found.group("body")
    names = []
    for line in body.splitlines():
        stripped = line.split("#", 1)[0].strip()
        names.extend(part for part in stripped.split() if part)
    return names


def check_enable(units: dict[str, str], script_text: str) -> OneCheck:
    if "systemctl enable" not in script_text:
        return OneCheck("enable", False,
                        "ustanovka.sh never calls systemctl enable -- the bot would live until "
                        "the first reboot")
    wanted = set(units_needing_enable(units))
    enabled = set(units_the_script_enables(script_text))
    missing = sorted(wanted - enabled)
    stale = sorted(enabled - wanted)
    problems = []
    if missing:
        problems.append("has [Install] but is never enabled: %s" % ", ".join(missing))
    if stale:
        problems.append("enabled but has no [Install] (systemctl would refuse): %s" % ", ".join(stale))
    if problems:
        return OneCheck("enable", False, "; ".join(problems))
    return OneCheck("enable", True,
                    "%d unit(s) with [Install], and ustanovka.sh enables exactly those" % len(wanted))


def check_watchdog(units: dict[str, str]) -> OneCheck:
    text = units.get(MAIN_UNIT)
    if text is None:
        return OneCheck("watchdog", False, "%s is missing from deploy/" % MAIN_UNIT)
    watchdog = directive(text, "WatchdogSec")
    service_type = directive(text, "Type")
    notify_access = directive(text, "NotifyAccess")
    if not watchdog:
        return OneCheck("watchdog", False, "no WatchdogSec in %s" % MAIN_UNIT)
    if service_type != "notify":
        return OneCheck("watchdog", False,
                        "WatchdogSec=%s but Type=%r: without Type=notify the watchdog is "
                        "a line of text and systemd never expects a ping" % (watchdog, service_type))
    return OneCheck("watchdog", True,
                    "WatchdogSec=%s, Type=notify, NotifyAccess=%s" % (watchdog, notify_access))


def check_restart_policy(units: dict[str, str]) -> OneCheck:
    text = units.get(MAIN_UNIT, "")
    problems = []
    if directive(text, "Restart") != "always":
        problems.append("Restart=%r, expected always" % directive(text, "Restart"))
    if directive(text, "RestartSec") != "5":
        problems.append("RestartSec=%r, expected 5" % directive(text, "RestartSec"))
    if directive(text, "StartLimitBurst") != "5":
        problems.append("StartLimitBurst=%r, expected 5" % directive(text, "StartLimitBurst"))
    interval = directive(text, "StartLimitIntervalSec")
    if interval not in ("300", "5min"):
        problems.append("StartLimitIntervalSec=%r, expected five minutes" % interval)
    if problems:
        return OneCheck("restart policy", False, "; ".join(problems))
    return OneCheck("restart policy", True,
                    "Restart=always, RestartSec=5, five starts per five minutes then give up")


def check_onfailure(units: dict[str, str]) -> OneCheck:
    """Every unit that can give up must say so out loud.

    Template units are exempt: ``spetsmat-alert@.service`` is the thing being fired, and an
    alerter that alerts about itself is a loop with nothing underneath it.
    """
    should_alert = [name for name, text in units.items()
                    if name.endswith(".service") and not name.startswith("spetsmat-alert@")]
    missing = [name for name in should_alert if directive(units[name], "OnFailure") is None]
    if missing:
        return OneCheck("onfailure", False, "no OnFailure= in: %s" % ", ".join(sorted(missing)))
    return OneCheck("onfailure", True,
                    "%d service unit(s) fire the alerter when they give up" % len(should_alert))


def check_timezone(units: dict[str, str]) -> OneCheck:
    services = [name for name in units if name.endswith(".service")]
    missing = [name for name in services if "Environment=TZ=UTC" not in units[name]]
    if missing:
        return OneCheck("timezone", False, "no Environment=TZ=UTC in: %s" % ", ".join(sorted(missing)))
    return OneCheck("timezone", True, "TZ=UTC in all %d service unit(s)" % len(services))


def check_graceful_stop(units: dict[str, str]) -> OneCheck:
    text = units.get(MAIN_UNIT, "")
    signal = directive(text, "KillSignal")
    timeout = directive(text, "TimeoutStopSec")
    if signal not in (None, "SIGTERM"):
        return OneCheck("graceful stop", False,
                        "KillSignal=%r: anything but SIGTERM kills the update in flight" % signal)
    if timeout is None:
        return OneCheck("graceful stop", False,
                        "no TimeoutStopSec: systemd's default eventually SIGKILLs the process")
    try:
        seconds = int(str(timeout).rstrip("s"))
    except ValueError:
        return OneCheck("graceful stop", False, "TimeoutStopSec=%r is not a number of seconds" % timeout)
    if seconds < 10:
        return OneCheck("graceful stop", False,
                        "TimeoutStopSec=%s is too short to finish an update in hand" % timeout)
    return OneCheck("graceful stop", True, "SIGTERM and %s to finish the update in hand" % timeout)


def check_placeholders(units: dict[str, str], script_text: str) -> OneCheck:
    """A placeholder that reaches ``/etc`` unsubstituted is a typo with a confusing symptom."""
    used = set()
    for text in units.values():
        used.update(PLACEHOLDER.findall(text))
    substituted = set(PLACEHOLDER.findall(script_text))
    orphans = sorted(used - substituted)
    if orphans:
        return OneCheck("placeholders", False,
                        "%s appear in the units and are never substituted by ustanovka.sh"
                        % ", ".join(orphans))
    return OneCheck("placeholders", True,
                    "%d placeholder(s) in the units, all substituted by ustanovka.sh" % len(used))


#: What the bot must contain for ``Type=notify`` plus ``WatchdogSec`` to mean anything.
#: ``READY=1`` is what systemd waits for at start; ``WATCHDOG=1`` is the periodic proof of
#: life.  Either one alone is not enough: without READY the unit never finishes starting,
#: without WATCHDOG it is killed at the first interval.
NOTIFY_MARKERS = ("READY=1", "WATCHDOG=1")


def watchdog_is_wired(root: Path | str | None = None) -> tuple[bool, str]:
    """Does ``bot/`` actually send the notifications the unit declares it expects?

    THE UNIT IS AHEAD OF THE CODE ON PURPOSE.  The ping must come from inside the polling
    loop, which lives in ``bot/`` -- read-only to the position that wrote this harness -- so
    the declaration is here and the hook is a named debt (``deploy/README.md``).  Shipping a
    ``Type=notify`` unit against a bot that never notifies would give a unit that never
    finishes starting and is then killed every interval, so ``ustanovka.sh`` asks this
    function first and installs the watchdog only once the answer is yes.
    """
    bot_dir = (Path(root) if root is not None else ROOT) / "bot"
    if not bot_dir.exists():
        return False, "no bot/ directory at %s" % bot_dir
    text = "\n".join(path.read_text(encoding="utf-8", errors="replace")
                     for path in sorted(bot_dir.rglob("*.py")))
    missing = [marker for marker in NOTIFY_MARKERS if marker not in text]
    if missing:
        return False, ("bot/ never sends %s -- the watchdog is declared and NOT wired; "
                       "deploy/README.md names the exact line, and ustanovka.sh installs the "
                       "unit with WatchdogSec and Type=notify neutralised until it is there"
                       % " or ".join(missing))
    return True, "bot/ sends %s" % " and ".join(NOTIFY_MARKERS)


def check_watchdog_wired(root: Path | str | None = None) -> OneCheck:
    wired, detail = watchdog_is_wired(root)
    return OneCheck("watchdog wired", wired, detail)


def check_live(units: dict[str, str]) -> OneCheck:
    """Ask systemd.  Absent systemd is reported as SKIPPED and never as green."""
    if shutil.which("systemctl") is None:
        return OneCheck("live systemd", False,
                        "SKIPPED: no systemctl on this machine -- the declaration was checked, "
                        "the running state was not; re-run this on the server after ustanovka.sh")
    wanted = units_needing_enable(units)
    not_enabled = []
    for name in wanted:
        finished = subprocess.run(["systemctl", "is-enabled", name],
                                  capture_output=True, text=True, check=False)
        if finished.stdout.strip() != "enabled":
            not_enabled.append("%s=%s" % (name, finished.stdout.strip() or finished.stderr.strip()))
    if not_enabled:
        return OneCheck("live systemd", False, "not enabled: %s" % ", ".join(not_enabled))
    return OneCheck("live systemd", True, "%d unit(s) reported enabled by systemd" % len(wanted))


def check_all(deploy_dir: Path | str | None = None, live: bool = False,
              wiring: bool = False, root: Path | str | None = None) -> Verdict:
    """The declaration checks.  ``wiring`` adds the one check that is RED today by design.

    It is off by default so that ``check_all`` answers "is deploy/ sound?", which is a
    question about this position's own work.  Whether ``bot/`` has caught up is a different
    question with a different owner, asked by ``--storozh`` and by ``ustanovka.sh``.
    """
    units = read_units(deploy_dir)
    script_path = (Path(deploy_dir) / "ustanovka.sh") if deploy_dir is not None else INSTALL_SCRIPT
    script_text = script_path.read_text(encoding="utf-8") if script_path.exists() else ""
    checks = [
        check_enable(units, script_text),
        check_watchdog(units),
        check_restart_policy(units),
        check_onfailure(units),
        check_timezone(units),
        check_graceful_stop(units),
        check_placeholders(units, script_text),
    ]
    if wiring:
        checks.append(check_watchdog_wired(root))
    if live:
        checks.append(check_live(units))
    return Verdict(checks=tuple(checks))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check the deployment declaration; --zhivaya also asks systemd itself."
    )
    parser.add_argument("--zhivaya", action="store_true",
                        help="additionally ask systemd whether the units are really enabled")
    parser.add_argument("--storozh", action="store_true",
                        help="additionally check that bot/ actually sends READY=1 and WATCHDOG=1")
    parser.add_argument("--deploy", default=None, help="directory of unit files")
    args = parser.parse_args(argv)
    verdict = check_all(args.deploy, live=args.zhivaya, wiring=args.storozh)
    print(verdict.report())
    return 0 if verdict.passed else 1


if __name__ == "__main__":
    sys.exit(main())
