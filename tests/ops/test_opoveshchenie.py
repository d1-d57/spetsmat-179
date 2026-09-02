"""The alerter: that it can shout, that it refuses to leak, and that it cannot poll.

Nothing here touches the network.  Delivery is proven by asserting on the request the
module builds, not by sending it: a test that needs Telegram to be reachable is a test of
Telegram.
"""

from __future__ import annotations

import tokenize
from pathlib import Path

import pytest

from ops import opoveshchenie


def _code_without_prose(path: Path) -> str:
    kept = []
    with path.open("rb") as handle:
        for token in tokenize.tokenize(handle.readline):
            if token.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            kept.append(token.string)
    return " ".join(kept)


def test_an_alarm_is_marked_as_an_alarm_and_a_heartbeat_as_a_heartbeat():
    assert opoveshchenie.compose("trevoga", "it died").startswith("🔴")
    assert opoveshchenie.compose("puls", "all green").startswith("🟢")


def test_an_unknown_kind_is_refused():
    with pytest.raises(ValueError):
        opoveshchenie.compose("whatever", "text")


def test_the_unit_name_travels_with_the_alarm():
    message = opoveshchenie.compose("trevoga", "failed", unit="spetsmat-bot.service")
    assert "spetsmat-bot.service" in message


@pytest.mark.parametrize("leak", [
    "/var/backups/spetsmat-20260902T120000Z-sutochnyj.db.gz",
    "attached: dump.sqlite",
    "here is spetsmat.db ",
])
def test_a_message_that_carries_a_snapshot_is_refused(leak):
    with pytest.raises(opoveshchenie.RefusedToSend):
        opoveshchenie.send(leak, dry_run=True)


def test_a_dry_run_needs_no_token_and_sends_nothing():
    assert opoveshchenie.send("probe", dry_run=True).endswith("probe")


def test_without_a_token_it_refuses_rather_than_falling_back(monkeypatch):
    """Falling back to the main bot's token would be two pollers on one token."""
    monkeypatch.delenv(opoveshchenie.TOKEN_VARIABLE, raising=False)
    monkeypatch.delenv(opoveshchenie.CHAT_VARIABLE, raising=False)
    with pytest.raises(opoveshchenie.RefusedToSend):
        opoveshchenie.send("something failed")


def test_the_request_is_a_sendmessage_post_and_nothing_else(monkeypatch):
    seen = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return b"{}"

    def fake_urlopen(request, timeout=None):
        seen["url"] = request.full_url
        seen["method"] = request.method
        seen["body"] = request.data.decode("utf-8")
        return FakeResponse()

    monkeypatch.setattr(opoveshchenie.urllib.request, "urlopen", fake_urlopen)
    opoveshchenie.send("it died", token="TOKEN", chat_id="42")

    assert seen["url"] == "https://api.telegram.org/botTOKEN/sendMessage"
    assert seen["method"] == "POST"
    assert '"chat_id": "42"' in seen["body"]
    assert "it died" in seen["body"]


def test_a_very_long_message_is_cut_to_what_telegram_accepts():
    message = opoveshchenie.compose("trevoga", "x" * 10_000)
    assert len(message) == opoveshchenie.MAX_TEXT


def test_the_alerter_never_polls_and_never_sends_files():
    """The two calls that would break the design, absent from the code by construction.

    ``getUpdates`` would make the alerter a second poller -- ``TelegramConflictError`` on the
    main bot.  ``sendDocument`` would make it the leak vector the backups avoid.
    """
    code = _code_without_prose(Path(opoveshchenie.__file__))
    for forbidden in ("getUpdates", "sendDocument", "sendPhoto", "aiogram"):
        assert forbidden not in code, "ops/opoveshchenie.py uses %r" % forbidden


def test_cli_dry_run_is_green_and_a_leaking_cli_call_is_red(capsys):
    assert opoveshchenie.main(["--proba", "--tekst", "restore check green", "--rod", "puls"]) == 0
    assert "🟢" in capsys.readouterr().out
    assert opoveshchenie.main(["--proba", "--tekst", "see backup.db.gz"]) == 1


def test_journal_tail_is_optional_and_never_raises(monkeypatch):
    """A laptop without journald must still be able to compose an alarm."""
    monkeypatch.setattr(opoveshchenie.shutil, "which", lambda name: None)
    message = opoveshchenie.compose("trevoga", "died", unit="spetsmat-bot.service", journal_lines=20)
    assert "no journalctl" in message
