"""The alerter: a SECOND bot, deliberately almost without code.

WHY A SECOND BOT
----------------
The thing that must shout when the main bot dies cannot be the main bot.  It also cannot
share the main bot's token: two processes polling Telegram with one token get
``TelegramConflictError``, which is the failure the deploy script exists to avoid.  So the
alerter has its own token, sends and never polls, and consists of one HTTPS POST built out
of the standard library alone -- no aiogram, no framework, no state.  It has nothing of its
own to crash with, which is the entire design.

WHAT IT REFUSES TO SEND
-----------------------
Anything that is not text, and any text carrying a snapshot.  There is no file-sending call
in this module at all: the database holds the names of fifty-six children, and a channel is
a third-party operator outside the perimeter.  ``ops/rezervnaya_kopia.py`` writes locally
for the same reason; this module is the other half of that decision.

SILENCE MEANS ALARM
-------------------
Two kinds of message: ``trevoga`` (something failed) and ``puls`` (the periodic check
passed).  The alarm is the loud one, but the heartbeat is the one that catches the failure
nobody catches otherwise -- a machine that is off, a timer that stopped firing, a check that
died before it could complain.  Whoever watches the channel watches for the MISSING pulse.
A dead-man's switch outside this machine is the next step and is named in ``## ВОПРОСЫ``:
it cannot live here, because a machine cannot notice its own absence.

CONFIGURATION
-------------
``ALERT_TOKEN`` and ``ALERT_CHAT_ID`` (or ``OWNER_ID``) in the environment, never in a file
in git -- the same names ``bot.env.example`` already uses.  The unit reads them from
``secrets/bot.env``, mode 0600, which ``deploy/ustanovka.sh`` creates from the example and
never overwrites.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

#: Telegram's own limit on one message.  Longer text is cut here rather than by the API,
#: so that a truncated alarm is still a delivered alarm.
MAX_TEXT = 4000

KINDS = ("trevoga", "puls")

#: The names are the ones ``bot.env.example`` already declares -- ``ALERT_TOKEN`` for the
#: second bot and ``OWNER_ID`` for the person who reads the alarms.  Inventing a third
#: spelling here would mean the owner fills in one file and the alerter reads another.
TOKEN_VARIABLE = "ALERT_TOKEN"
CHAT_VARIABLE = "ALERT_CHAT_ID"
CHAT_FALLBACK_VARIABLE = "OWNER_ID"

#: Substrings that mean somebody is about to put a snapshot into a message.
FORBIDDEN_IN_TEXT = (".db.gz", ".sqlite", ".db\n", ".db ")


class RefusedToSend(Exception):
    """Raised instead of sending: the caller asked for something that must not leave the machine."""


def guard(text: str) -> None:
    lowered = text.lower()
    for needle in FORBIDDEN_IN_TEXT:
        if needle in lowered:
            raise RefusedToSend(
                "the message mentions %r: a snapshot must never leave the perimeter, "
                "and a path to one is a request to fetch it" % needle
            )


def compose(kind: str, text: str, unit: str | None = None, journal_lines: int = 0) -> str:
    if kind not in KINDS:
        raise ValueError("unknown kind %r, expected one of %s" % (kind, ", ".join(KINDS)))
    prefix = "🔴 spetsmat-bot" if kind == "trevoga" else "🟢 spetsmat-bot"
    parts = ["%s: %s" % (prefix, text)]
    if unit:
        parts.append("unit: %s" % unit)
        if journal_lines:
            parts.append(_journal_tail(unit, journal_lines))
    message = "\n".join(part for part in parts if part)
    return message[:MAX_TEXT]


def _journal_tail(unit: str, lines: int) -> str:
    """The last few journal lines, when journald is there.  Absent journald is not an error.

    The alarm must be sendable from a laptop with no systemd at all, because that is where
    this whole harness is proven before any server exists.
    """
    if shutil.which("journalctl") is None:
        return "(no journalctl on this machine -- log tail omitted)"
    try:
        finished = subprocess.run(
            ["journalctl", "-u", unit, "-n", str(lines), "--no-pager", "--output", "cat"],
            capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.SubprocessError) as failure:
        return "(journalctl failed: %s)" % failure
    tail = (finished.stdout or finished.stderr or "").strip()
    return ("last %d line(s):\n%s" % (lines, tail)) if tail else "(journal empty)"


def send(text: str, kind: str = "trevoga", unit: str | None = None, journal_lines: int = 0,
         token: str | None = None, chat_id: str | None = None, dry_run: bool = False) -> str:
    """Send one message.  Returns what was sent, so the caller can log or assert on it."""
    message = compose(kind, text, unit, journal_lines)
    guard(message)

    if dry_run:
        return message

    token = token or os.environ.get(TOKEN_VARIABLE, "")
    chat_id = chat_id or os.environ.get(CHAT_VARIABLE, "") or os.environ.get(CHAT_FALLBACK_VARIABLE, "")
    if not token or not chat_id:
        raise RefusedToSend(
            "%s and one of %s/%s must be set; the alerter is deliberately unable to fall back "
            "to the main bot's token -- two pollers on one token is TelegramConflictError"
            % (TOKEN_VARIABLE, CHAT_VARIABLE, CHAT_FALLBACK_VARIABLE)
        )

    payload = json.dumps({"chat_id": chat_id, "text": message}).encode("utf-8")
    request = urllib.request.Request(
        "https://api.telegram.org/bot%s/sendMessage" % token,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        response.read()
    return message


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Send one alarm or one heartbeat through the second bot.")
    parser.add_argument("--rod", choices=KINDS, default="trevoga", help="alarm or heartbeat")
    parser.add_argument("--tekst", required=True, help="what happened, in one line")
    parser.add_argument("--edinica", default=None, help="the systemd unit this is about")
    parser.add_argument("--strok-zhurnala", type=int, default=0,
                        help="how many journal lines to attach (0 = none)")
    parser.add_argument("--proba", action="store_true",
                        help="compose and check the message, send nothing -- provable without a token")
    args = parser.parse_args(argv)

    try:
        message = send(args.tekst, args.rod, args.edinica, args.strok_zhurnala, dry_run=args.proba)
    except RefusedToSend as refusal:
        print("not sent: %s" % refusal, file=sys.stderr)
        return 1
    except (urllib.error.URLError, OSError) as failure:
        # The alerter failing is itself a thing to know about, and there is nobody left to
        # tell -- so it goes to stderr, which journald keeps.
        print("alert delivery FAILED: %s" % failure, file=sys.stderr)
        return 2

    print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
