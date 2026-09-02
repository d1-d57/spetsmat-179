"""The send path itself, and the prohibition of section 4 as a sweep over the whole tree.

WHAT IS ASSERTED HERE THAT NOWHERE ELSE ASSERTS.

* **Every message reaches the right chat.**  A summary addressed to the wrong head is a
  privacy failure and not a cosmetic one: it carries the surnames of children.
* **One failure does not lose the rest.**  A teacher who has blocked the bot must not cost
  another room its summary, so the send is caught per message and counted.
* **An addressee with no Telegram id is reported, not raised, and NOT claimed.**  At the
  start of a year a head may not have registered yet; the summary must still go to the
  rooms that have one, and the unclaimed message must still be waiting after he does.
* **The wiring is real.**  ``bot/app.build`` must actually put the service on the
  dispatcher, or every test above passes against a service nothing calls.

THE SECTION 4 SWEEP IS OVER THE WHOLE OF ``bot/`` AND ``core/``, not over this position's
files, because those are the two trees the готовности criterion greps.  It names the file
and the line it found, so a hit is actionable rather than merely red.

The forbidden strings ARE spelled out below, and that is safe for exactly one checkable
reason: the criterion greps ``bot/`` and ``core/`` and NOT ``tests/``, so a checker living
here cannot become the thing it finds.  The same words must never be written into a file
under either of those two trees -- ``bot/keyboards/views.py`` says so about itself and
``core/services/svodka.py`` repeats it, because a docstring listing them turns its own gate
red.  If the criterion ever grows ``tests/``, this constant is the first thing to move.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from aiogram.exceptions import TelegramForbiddenError

from bot.routers.uvedomlenia import Yavka, send_after_lesson
from core.services.svodka import RECIPIENT_HEAD, RECIPIENT_TEACHER

#: The alternatives of the готовности criterion, one per line so that the two cannot drift
#: apart unnoticed.  Safe to spell here and nowhere under ``bot/`` or ``core/``: see the
#: module docstring for the reason, which is checkable rather than stylistic.
FORBIDDEN = re.compile(
    "|".join(
        [
            "рейтинг",       # a ranking
            "percent",
            "процент",        # per cent
            "badge",
            "streak",
            "leaderboard",
            "очк[иов]",            # points
            "молодец",        # well done
            "отлично",        # excellent
            "меньше всех",  # fewest of all
            "больше всех",  # most of all
        ]
    ),
    re.IGNORECASE,
)

#: Known hits that this position did not write and may not touch: everything outside its
#: zone is READ-ONLY, and section 5 says a problem found outside the zone goes into the
#: report rather than into an edit.  Listed by path so that a NEW hit still goes red.
INHERITED = ("core/services/raspoznavanie.py",)


def test_every_message_goes_to_its_own_addressee(
    svodka, notify_world, bot_instance, recorder, event_loop
):
    """The chat id of every send is the Telegram id of the person it was built for."""
    session_id = notify_world.session_ids["2026-09-10"]
    plan = svodka.plan(session_id)
    expected = sorted(n.recipient_tg_id for n in plan.notifications)

    report = event_loop.run_until_complete(
        send_after_lesson(bot_instance, svodka, session_id)
    )
    assert report.sent == len(expected), report.line()
    assert sorted(recorder.chat_ids()) == expected, (
        "a message went to a chat it was not addressed to"
    )
    print(
        "[отправка] адресатов %d · доставлено %d · чужих адресов 0"
        % (len(expected), report.sent)
    )


def test_only_the_teacher_question_carries_buttons(
    svodka, notify_world, bot_instance, recorder, event_loop
):
    """The summary is a message to read; the question is a message to answer.

    Paired by ORDER and not by chat id, and that is not a convenience: a head who also
    marked nothing gets BOTH messages, so one chat legitimately receives two of them and a
    lookup keyed on the chat would silently compare the wrong pair.  ``send_after_lesson``
    walks the plan in order, so the n-th send is the n-th notification.
    """
    session_id = notify_world.session_ids["2026-09-10"]
    plan = svodka.plan(session_id)
    assert all(n.deliverable for n in plan.notifications), (
        "an undeliverable notification would break the pairing by order"
    )

    event_loop.run_until_complete(send_after_lesson(bot_instance, svodka, session_id))
    sends = recorder.sends()
    assert len(sends) == len(plan.notifications)

    for notification, record in zip(plan.notifications, sends):
        assert record.payload["chat_id"] == notification.recipient_tg_id
        markup = record.payload.get("reply_markup")
        if notification.recipient_kind == RECIPIENT_TEACHER:
            assert markup, "the question arrived without its two answers"
            assert len(markup["inline_keyboard"][0]) == 2
        else:
            assert not markup, "the summary arrived with buttons on it"


def test_a_head_who_marked_nothing_gets_both_messages(svodka, notify_world):
    """Two roles in one person are two messages, not one.

    He is a teacher who took nobody tonight (so the question is his) and the head of his
    room (so the summary is his).  Collapsing them would drop whichever the code checked
    second, and which one that is would depend on the order of a dictionary.
    """
    plan = svodka.plan(notify_world.session_ids["2026-09-10"])
    head_id = notify_world.head_teacher_ids[0]
    kinds = sorted(n.recipient_kind for n in plan.notifications if n.recipient_id == head_id)
    assert kinds == sorted([RECIPIENT_HEAD, RECIPIENT_TEACHER])


def test_one_blocked_bot_does_not_cost_the_others_their_summary(
    svodka, notify_world, bot_instance, recorder, event_loop
):
    """A refusal from the API is counted and the run carries on.

    Raising would mean that a single teacher who blocked the bot silences every room for
    the rest of the year, and nobody would find out why -- the failure would look like
    "the feature does not work".
    """
    session_id = notify_world.session_ids["2026-09-10"]
    recorder.fail_with = TelegramForbiddenError(method=None, message="bot was blocked")

    report = event_loop.run_until_complete(
        send_after_lesson(bot_instance, svodka, session_id)
    )
    assert report.planned > 0
    assert report.failed == report.planned, report.line()
    assert report.sent == 0
    assert len(report.errors) == report.failed, "a failure was counted but not named"


def test_an_unregistered_head_is_reported_and_stays_pending(
    svodka, notify_world, roster_connection, bot_instance, recorder, event_loop, connection
):
    """A head with no Telegram id yet: counted as unreachable, and NOT claimed.

    Leaving the claim untaken is what makes the message wait for him: the run after he
    registers finds no row and sends it.  Claiming it would silently swallow the first
    summary of his year.
    """
    session_id = notify_world.session_ids["2026-09-10"]
    head_id = notify_world.head_teacher_ids[0]
    connection.execute("update teachers set tg_id = null where id = ?", (head_id,))
    connection.commit()

    report = event_loop.run_until_complete(
        send_after_lesson(bot_instance, svodka, session_id)
    )
    assert report.unreachable >= 1, report.line()
    claimed = {(r.recipient_kind, r.recipient_id) for r in svodka.already_sent(session_id)}
    assert (RECIPIENT_HEAD, head_id) not in claimed, (
        "an undeliverable summary was marked as sent and will never go out"
    )

    # He registers, and the very next run delivers it.
    connection.execute("update teachers set tg_id = ? where id = ?", (777001, head_id))
    connection.commit()
    recorder.reset()
    again = event_loop.run_until_complete(
        send_after_lesson(bot_instance, svodka, session_id)
    )
    assert 777001 in recorder.chat_ids(), again.line()


def test_the_report_counters_add_up_to_what_was_planned(
    svodka, notify_world, bot_instance, event_loop
):
    """«разослано 3» and «разослано 3 из 8» are different evenings.

    The four counters split the plan and must account for all of it, or the line the
    operator reads is arithmetic nobody can check.
    """
    session_id = notify_world.session_ids["2026-09-10"]
    report = event_loop.run_until_complete(
        send_after_lesson(bot_instance, svodka, session_id)
    )
    assert (
        report.sent + report.already + report.unreachable + report.failed
        == report.planned
    ), report.line()
    assert str(report.planned) in report.line()


def test_the_payload_carries_only_numbers(notify_world):
    """``bot/callbacks.py``'s law, on this position's own payload.

    The separator is ``:`` and a Cyrillic character costs two of the sixty-four available
    bytes, so a payload with a word in it is a payload that can break on real data.
    """
    packed = Yavka(session_id=notify_world.session_ids["2026-09-10"], answer=1).pack()
    assert len(packed.encode("utf-8")) <= 64
    assert packed.isascii(), "a non-ASCII character reached callback_data: %r" % packed


def test_the_service_is_actually_on_the_dispatcher(tmp_path, recorder):
    """``bot/app.build`` wires it in, or every test above tests a service nothing calls.

    The one thing a unit test of the service can never notice: a perfectly correct module
    that no dispatcher ever constructs.
    """
    from aiogram import Bot
    from bot.app import build
    from infra.db import apply_migrations

    journal_path = tmp_path / "journal.db"
    apply_migrations(journal_path)
    dispatcher = build(
        token="0:fake",
        owner_tg_id=1,
        journal_path=journal_path,
        roster_path=tmp_path / "roster.db",
        bot=Bot(token="0:fake", session=recorder),
    )
    assert "svodka" in dispatcher.workflow_data, (
        "the notification service is not on the dispatcher; no handler can resolve it"
    )
    names = [r.name for r in dispatcher.sub_routers]
    assert "uvedomlenia" in names, "the notification router was never included: %r" % names
    assert names.index("uvedomlenia") < len(names) - 1, (
        "the notification router stands after the catch-all, which would answer every "
        "attendance button with «экран устарел»"
    )


@pytest.mark.parametrize("tree", ["bot", "core"])
def test_nothing_in_the_tree_ranks_or_scores_anybody(tree):
    """The sweep of section 4, over the same two trees the готовности command greps.

    Named by file and line so a hit is actionable.  Hits this position did not write and
    may not touch are listed in ``INHERITED`` and reported rather than failed -- everything
    outside the zone is read-only, and section 5 says a problem found there goes into the
    report.  A NEW hit anywhere still fails.
    """
    root = Path(__file__).resolve().parents[2]
    hits = []
    inherited = []
    for path in sorted((root / tree).rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if FORBIDDEN.search(line):
                (inherited if relative in INHERITED else hits).append(
                    "%s:%d: %s" % (relative, number, line.strip())
                )
    print(
        "[запрет] %s/: файлов проверено %d · новых нарушений %d · унаследованных %d"
        % (tree, len(list((root / tree).rglob("*.py"))), len(hits), len(inherited))
    )
    assert not hits, "\n".join(hits)
