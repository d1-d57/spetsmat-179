"""The owner hears about a заявка at once, and hears about it once.

Before this: the заявка landed in a queue silently, and the owner found their own only
because they thought to type ``/pending``.  During a lesson that means a child has
registered and the teacher will not learn of it.

Two claims are tested and they are different claims:

  * the message goes out AT REGISTRATION, through the real dispatcher, with the same
    three buttons the ``/pending`` screen draws;
  * one заявка produces exactly one message -- under a repeated fire, and across a
    restarted process, which is what the on-disk claim is for.
"""

from __future__ import annotations

import asyncio

import pytest

from bot.handlers.owner import pending_notifier
from tests.bot.conftest import feed_message, messages_sent

OWNER = 999_999
CHILD_TG = 7_930_004


def _start_dispatcher(dispatcher, bot_instance) -> None:
    """Emit the startup aiogram emits on ``start_polling``.

    ``feed_raw_update`` does not emit it, so a test that skipped this would be testing
    a bot that never came up.  The kwargs are the production ones: ``workflow_data``
    plus the bot.
    """
    data = dict(dispatcher.workflow_data)
    data.pop("bot", None)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        dispatcher.emit_startup(bot=bot_instance, dispatcher=dispatcher, **data)
    )


def _in_loop(call, *args, **kwargs):
    """Run a SYNCHRONOUS service call with a loop running under it.

    In production ``submit_student`` is always called from inside an aiogram handler,
    so a loop is always there for the notifier to schedule the send on.  A test that
    called it from bare test-function scope would be testing the no-loop branch by
    accident and never see a message.
    """
    async def _run():
        return call(*args, **kwargs)

    return asyncio.get_event_loop().run_until_complete(_run())


def _drain(loop=None) -> None:
    """Let the fire-and-forget send actually run before the assertions look."""
    loop = loop or asyncio.get_event_loop()
    for _ in range(4):
        loop.run_until_complete(asyncio.sleep(0))


def test_owner_is_told_the_moment_a_child_registers(
    dispatcher, bot_instance, recorder, full_catalogue
):
    """The child finishes the deep-link flow; the owner's chat gets the message."""
    _start_dispatcher(dispatcher, bot_instance)
    recorder.records.clear()

    feed_message(dispatcher, bot=bot_instance, chat_id=CHILD_TG, from_id=CHILD_TG,
                 text="/start register-student", update_id=11)
    feed_message(dispatcher, bot=bot_instance, chat_id=CHILD_TG, from_id=CHILD_TG,
                 text="Пирогов", update_id=12)
    feed_message(dispatcher, bot=bot_instance, chat_id=CHILD_TG, from_id=CHILD_TG,
                 text="Константин", update_id=13)
    _drain()

    to_owner = [
        record for record in recorder.records
        if record.method == "SendMessage" and record.payload.get("chat_id") == OWNER
    ]
    assert to_owner, (
        "the owner was told nothing; the bot sent %r"
        % ([(r.method, r.payload.get("chat_id")) for r in recorder.records],)
    )
    text = to_owner[0].payload.get("text", "")
    assert "Пирогов" in text and "Константин" in text, text
    assert "ученик" in text, "the message must say in what role: %r" % text

    markup = to_owner[0].payload.get("reply_markup") or {}
    payloads = [
        button.get("callback_data")
        for row in (markup.get("inline_keyboard") or [])
        for button in row
    ]
    assert any((p or "").startswith("accept:") for p in payloads), payloads
    assert any((p or "").startswith("rename:") for p in payloads), payloads
    assert any((p or "").startswith("reject:") for p in payloads), payloads


def test_one_zayavka_one_message_however_many_times_it_is_fired(
    dispatcher, bot_instance, recorder, full_catalogue
):
    """The claim is on disk, so a repeated fire sends nothing more."""
    _start_dispatcher(dispatcher, bot_instance)
    roster = dispatcher.workflow_data["roster"]
    recorder.records.clear()

    pending = _in_loop(roster.submit_student, tg_id=CHILD_TG, surname="Пирогов", name="Константин")
    _drain()
    first = len([r for r in recorder.records if r.payload.get("chat_id") == OWNER])
    assert first == 1, "expected one message, got %d" % first

    # Fire the service's own announcement path again, exactly as a retry would.
    _in_loop(roster._announce, pending)  # noqa: SLF001 -- the retry is the thing under test
    _drain()
    again = len([r for r in recorder.records if r.payload.get("chat_id") == OWNER])
    assert again == 1, "a second message went out for the same заявка (%d total)" % again


def test_a_restarted_process_does_not_send_them_again(
    dispatcher, bot_instance, recorder, tmp_path, db_path, full_catalogue
):
    """Reopen the roster store from disk: the claim is still there, nothing is resent."""
    _start_dispatcher(dispatcher, bot_instance)
    roster = dispatcher.workflow_data["roster"]
    recorder.records.clear()
    pending = _in_loop(roster.submit_student, tg_id=CHILD_TG, surname="Пирогов", name="Константин")
    _drain()
    assert len([r for r in recorder.records if r.payload.get("chat_id") == OWNER]) == 1

    # A NEW process over the SAME two files, wired exactly as ``bot.app.build`` wires it.
    from core.services.roster import RosterService
    from infra.roster_repo import RosterRepo

    restarted_repo = RosterRepo.open(
        journal_path=db_path, roster_path=tmp_path / "roster-screen.db"
    )
    sent: list = []
    restarted = RosterService(
        restarted_repo,
        sheets_for_current=lambda: full_catalogue["sheet_ids"][-1],
        on_pending=sent.append,
    )
    surviving = [p for p in restarted.list_pending() if p.id == pending.id]
    assert surviving, "the заявка did not survive the restart; nothing to test"
    restarted._announce(surviving[0])  # noqa: SLF001
    assert sent == [], "the restarted process announced the заявка a second time"
    restarted_repo.close()


def test_a_notifier_that_throws_does_not_lose_the_zayavka(repo, current_sheet):
    """Telegram is allowed to fail; the registration is not allowed to disappear."""
    from core.services.roster import RosterService

    def explode(_registration):
        raise RuntimeError("telegram is down")

    roster = RosterService(
        repo, sheets_for_current=lambda: current_sheet, on_pending=explode
    )
    with pytest.raises(RuntimeError):
        roster.submit_student(tg_id=CHILD_TG, surname="Иванов", name="Иван")
    assert [p.surname for p in roster.list_pending()] == ["Иванов"], (
        "the заявка was rolled back because a message could not be sent"
    )


def test_a_recycled_registration_id_is_still_announced(repo, current_sheet):
    """SQLite hands the next заявка a deleted id; the claim must not silence it.

    Without dropping the claim in ``resolve_pending`` this is exactly how the owner
    stops hearing about children: заявка 1 is rejected, заявка 1 is issued again to
    somebody else, and the marker from the first swallows the second.
    """
    from core.services.roster import RosterService

    seen: list = []
    roster = RosterService(
        repo, sheets_for_current=lambda: current_sheet, on_pending=seen.append
    )
    first = roster.submit_student(tg_id=CHILD_TG, surname="Иванов", name="Иван")
    roster.reject(first.id)
    second = roster.submit_student(tg_id=CHILD_TG + 1, surname="Петров", name="Пётр")
    assert second.id == first.id, (
        "the id was not recycled, so this test is not testing what it says it is"
    )
    assert [p.surname for p in seen] == ["Иванов", "Петров"], seen


def test_the_notifier_survives_being_called_without_a_loop(bot_instance, caplog):
    """No running loop is a warning, not a crash and not a silent drop."""
    notify = pending_notifier(bot_instance, OWNER)
    from core.services.roster import PendingRegistration, Role

    registration = PendingRegistration(
        id=1, tg_id=CHILD_TG, surname="Иванов", name="Иван",
        intended_role=Role.STUDENT,
    )
    with caplog.at_level("WARNING"):
        notify(registration)
    assert any("was not announced" in record.message for record in caplog.records), (
        [record.message for record in caplog.records]
    )
