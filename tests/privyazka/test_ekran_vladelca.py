"""The owner's screen, driven through the real dispatcher.

Everything else in this directory tests the DECISION.  This file tests what the owner
actually sees when they press «принять», because «показать владельцу КНОПКИ» is a claim
about a screen and a service assertion cannot see a button.

The dispatcher is the production one (``bot.app.build``); only the Telegram session is
substituted, so the routers, the middleware and the callback payloads are the real ones.
"""

from __future__ import annotations

from conftest import PIROGOV, PIROGOV_MARKS, tg_for
from tests.bot.conftest import callback_alerts, feed_callback, feed_message, messages_sent

TYPO = ("Цукунов", "Александр")
STRANGER = ("Иванов", "Иван")
OWNER = 999_999


def _buttons(recorder) -> list:
    """Every inline button the bot drew, as ``(text, callback_data)``."""
    out: list = []
    for record in recorder.records:
        markup = record.payload.get("reply_markup") or {}
        for row in (markup.get("inline_keyboard") or []):
            for button in row:
                out.append((button.get("text"), button.get("callback_data")))
    return out


def _submit(dispatcher, roster_of_dispatcher, tg_id, surname, name):
    return roster_of_dispatcher.submit_student(tg_id=tg_id, surname=surname, name=name)


def test_accept_binds_pirogov_and_creates_nothing(
    dispatcher, bot_instance, recorder, connection, full_catalogue, pirogov_marks
):
    """The live path end to end: «принять» on Пирогов binds, and the row count holds."""
    roster = dispatcher.workflow_data["roster"]
    pending = _submit(dispatcher, roster, 7_810_001, *PIROGOV)
    before = connection.execute("select count(*) c from students").fetchone()["c"]

    recorder.records.clear()
    feed_callback(dispatcher, bot=bot_instance, from_id=OWNER, data="accept:%d" % pending.id)

    after = connection.execute("select count(*) c from students").fetchone()["c"]
    assert after == before, "«принять» created a row instead of binding"
    assert roster.student_id_for(7_810_001) == pirogov_marks
    assert roster.list_pending() == []
    assert any("Привязан" in alert for alert in callback_alerts(recorder)), (
        "the owner was not told which row the child was attached to: %r"
        % (callback_alerts(recorder),)
    )


def test_two_candidates_draw_one_button_each_and_change_nothing(
    dispatcher, bot_instance, recorder, connection, full_catalogue
):
    """🔴 The named case: «Цукунов Александр» draws buttons, and writes nothing."""
    roster = dispatcher.workflow_data["roster"]
    pending = _submit(dispatcher, roster, 7_910_002, *TYPO)
    before = connection.execute(
        "select id, tg_id, status from students order by id"
    ).fetchall()

    recorder.records.clear()
    feed_callback(dispatcher, bot=bot_instance, from_id=OWNER, data="accept:%d" % pending.id)

    drawn = _buttons(recorder)
    payloads = [data for _, data in drawn if (data or "").startswith("bindstud:")]
    assert len(payloads) == 2, "expected one button per candidate, drew %r" % (drawn,)
    texts = " ".join(text for text, _ in drawn)
    assert "Цикунов" in texts and "Цуканов" in texts, texts
    assert any((data or "").startswith("newstud:") for _, data in drawn), (
        "«нет в списке — завести нового» must be on the same screen: %r" % (drawn,)
    )

    after = connection.execute(
        "select id, tg_id, status from students order by id"
    ).fetchall()
    assert [tuple(r) for r in after] == [tuple(r) for r in before], (
        "the screen wrote to the catalogue before the owner chose"
    )
    assert [p.id for p in roster.list_pending()] == [pending.id]

    # The owner presses one of the two, and exactly that one is bound.
    chosen = payloads[0]
    recorder.records.clear()
    feed_callback(dispatcher, bot=bot_instance, from_id=OWNER, data=chosen)
    chosen_student_id = int(chosen.split(":")[2])
    assert roster.student_id_for(7_910_002) == chosen_student_id
    assert roster.list_pending() == []
    assert connection.execute("select count(*) c from students").fetchone()["c"] == 56


def test_a_stranger_is_not_created_until_the_owner_presses_the_button(
    dispatcher, bot_instance, recorder, connection, full_catalogue
):
    """Zero matches: one explicit button, and nothing at all before it is pressed."""
    roster = dispatcher.workflow_data["roster"]
    pending = _submit(dispatcher, roster, 7_920_003, *STRANGER)

    recorder.records.clear()
    feed_callback(dispatcher, bot=bot_instance, from_id=OWNER, data="accept:%d" % pending.id)

    drawn = _buttons(recorder)
    new_buttons = [data for _, data in drawn if (data or "").startswith("newstud:")]
    assert new_buttons == ["newstud:%d" % pending.id], drawn
    assert not [data for _, data in drawn if (data or "").startswith("bindstud:")], (
        "a child nobody matches was offered as a candidate anyway: %r" % (drawn,)
    )
    assert connection.execute("select count(*) c from students").fetchone()["c"] == 56, (
        "«принять» created the row silently -- the button exists precisely so it does not"
    )
    assert roster.student_id_for(7_920_003) is None

    recorder.records.clear()
    feed_callback(dispatcher, bot=bot_instance, from_id=OWNER, data=new_buttons[0])
    assert connection.execute("select count(*) c from students").fetchone()["c"] == 57
    new_id = roster.student_id_for(7_920_003)
    assert new_id is not None
    row = connection.execute(
        "select surname, name, status, first_sheet_id from students where id = ?", (new_id,)
    ).fetchone()
    assert (row["surname"], row["name"]) == STRANGER
    assert row["status"] == "active"
    # The Пирогов rule from the other side: a newcomer is anchored to TODAY's sheet and
    # is not charged for the seventeen listki they were never present for.
    assert row["first_sheet_id"] == full_catalogue["sheet_ids"][-1]
