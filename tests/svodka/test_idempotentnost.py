"""ОДНА СВОДКА — ОДИН РАЗ.  The named test of the готовности criterion.

    python3 -m pytest tests/svodka -q -k "idempot or dvazhdy"

Every test in this file is named so that command selects it, and every one of them is
about the same sentence of the задание: «Сводка за одно занятие уходит ОДИН раз.
Перезапуск процесса, повторный вызов, две реплики — всё это не должно рассылать её
дважды. Ключ — занятие плюс адресат, в таблице отправленного; ноль затронутых строк
значит "уже слали, выходим"».

WHY THE CARRIER IS THE DATABASE AND NOT THE CODE.  A flag in memory dies with the process,
and the restart is exactly when the second send would happen.  So the carrier is a UNIQUE
index on (session_id, recipient_kind, recipient_id) and a single insert-or-nothing whose
affected-row count is the answer.  The tests below therefore run against the real SQLite
adapter: a fake that returned True once and False afterwards would be testing the fake, and
the one thing worth testing here is whether the DATABASE refuses the second claim.

THE FOUR WAYS IT CAN HAPPEN, EACH ONE ITS OWN TEST.  A repeated call, a restarted process
(a second adapter over the same file), two replicas racing in one transaction window, and
the send path as a whole run twice end to end.
"""

from __future__ import annotations

from bot.routers.uvedomlenia import send_after_lesson
from core.services.svodka import RECIPIENT_HEAD, RECIPIENT_TEACHER
from infra.uvedomlenia_repo import SqliteSentLog


def test_idempotentnost_vtoroj_vyzov_ne_rassylaet_dvazhdy(svodka, notify_world):
    """A second call to the same lesson claims nothing at all.

    The plan is rebuilt identically -- it is a pure read -- and every claim on it comes
    back False, which is the caller's instruction to stop.
    """
    session_id = notify_world.session_ids["2026-09-10"]

    first = svodka.plan(session_id)
    assert first.notifications, "the lesson has nothing to say; the test proves nothing"
    assert all(svodka.claim(n) for n in first.notifications)

    second = svodka.plan(session_id)
    assert len(second.notifications) == len(first.notifications)
    assert not any(svodka.claim(n) for n in second.notifications), (
        "a second run took a claim that was already standing"
    )
    print(
        "[идемпотентность] адресатов %d · вторых отправок 0 из %d"
        % (len(first.notifications), len(second.notifications))
    )


def test_idempotentnost_perezapusk_processa_ne_rassylaet_dvazhdy(
    svodka, notify_world, connection
):
    """A RESTART, modelled honestly: a brand-new adapter over the same file.

    The claim held in memory would be gone here, and this is the case a memory flag fails.
    The row in the database is not gone, so the second claim is refused.
    """
    session_id = notify_world.session_ids["2026-09-10"]
    plan = svodka.plan(session_id)
    for notification in plan.notifications:
        assert svodka.claim(notification)

    # A different object over the same database: this is what survives a restart.
    after_restart = SqliteSentLog(connection)
    for notification in plan.notifications:
        assert not after_restart.claim(
            notification.session_id,
            notification.recipient_kind,
            notification.recipient_id,
            "2026-09-10T20:00:00Z",
        ), "the sent-log forgot a claim across a restart"


def test_idempotentnost_dve_repliki_odna_pobezhdaet(svodka, notify_world, connection):
    """Two replicas asking at the same moment: exactly one is allowed to send.

    The claim is a single statement, so the loser does not see «not sent yet» -- it sees
    the winner's row.  A select-then-insert would let both read an empty table and both
    send, which is the failure the unique index exists to prevent.
    """
    session_id = notify_world.session_ids["2026-09-10"]
    notification = svodka.plan(session_id).notifications[0]

    replica_a = SqliteSentLog(connection)
    replica_b = SqliteSentLog(connection)
    won = [
        replica.claim(
            notification.session_id,
            notification.recipient_kind,
            notification.recipient_id,
            "2026-09-10T20:0%d:00Z" % index,
        )
        for index, replica in enumerate((replica_a, replica_b))
    ]
    assert won.count(True) == 1, "both replicas believed they were the sender: %r" % won


def test_idempotentnost_klyuch_eto_zanyatie_plyus_adresat(svodka, notify_world):
    """The key is the lesson PLUS the addressee, and both halves matter.

    Same addressee at a different lesson is a different message and must go out.  Different
    addressee at the same lesson is a different message and must go out too.  A key on only
    one half would silence one of the two, and the whole feature is two kinds of message to
    two kinds of person about a series of lessons.
    """
    monday = notify_world.session_ids["2026-09-07"]
    thursday = notify_world.session_ids["2026-09-10"]

    monday_plan = svodka.plan(monday)
    for notification in monday_plan.notifications:
        assert svodka.claim(notification)

    # Same people, the NEXT lesson: every claim is fresh.
    thursday_plan = svodka.plan(thursday)
    assert all(svodka.claim(n) for n in thursday_plan.notifications), (
        "a claim on Monday's lesson silenced Thursday's"
    )

    # And the two kinds of message to ONE person are two claims, not one: a head who also
    # marked nothing gets both the question and the summary.
    head_id = notify_world.head_teacher_ids[0]
    kinds = {
        n.recipient_kind for n in thursday_plan.notifications if n.recipient_id == head_id
    }
    assert kinds == {RECIPIENT_TEACHER, RECIPIENT_HEAD}, (
        "the head marked nothing, so he is owed both the question and the summary; got %r"
        % (kinds,)
    )


def test_dvazhdy_ne_otpravlyaetsya_cherez_ves_put_otpravki(
    svodka, notify_world, bot_instance, recorder, event_loop
):
    """The whole send path, run twice: the second run sends nothing.

    End to end through ``send_after_lesson``, with a recording Telegram session, because
    the claim being refused is only half the guarantee -- the other half is that the send
    path actually obeys the refusal.
    """
    session_id = notify_world.session_ids["2026-09-10"]

    first = event_loop.run_until_complete(
        send_after_lesson(bot_instance, svodka, session_id)
    )
    assert first.sent == first.planned and first.planned > 0, first.line()
    assert len(recorder.sends()) == first.sent

    recorder.reset()
    second = event_loop.run_until_complete(
        send_after_lesson(bot_instance, svodka, session_id)
    )
    assert second.sent == 0, second.line()
    assert second.already == second.planned
    assert recorder.sends() == [], "the second run put %d messages on the wire" % len(
        recorder.sends()
    )
    print("[идемпотентность] %s · повтор: %s" % (first.line(), second.line()))


def test_idempotentnost_nol_zatronutyh_strok_znachit_uzhe_slali(sent_log, notify_world):
    """The rule spelled out at the level it is actually enforced.

    ``claim`` returns True exactly once per (lesson, kind, addressee); "zero affected rows"
    is what False means, and ``already_sent`` shows the row that caused it.
    """
    session_id = notify_world.session_ids["2026-09-10"]
    teacher_id = notify_world.teacher_ids[0]

    assert sent_log.claim(session_id, RECIPIENT_TEACHER, teacher_id, "2026-09-10T20:00:00Z")
    assert not sent_log.claim(session_id, RECIPIENT_TEACHER, teacher_id, "2026-09-10T21:00:00Z")

    standing = sent_log.already_sent(session_id)
    assert [(r.recipient_kind, r.recipient_id) for r in standing] == [
        (RECIPIENT_TEACHER, teacher_id)
    ]
    assert standing[0].sent_at == "2026-09-10T20:00:00Z", (
        "the refused second claim overwrote the moment of the first one"
    )


def test_idempotentnost_ne_meshaet_pervoj_otpravke_drugogo_zanyatia(
    svodka, notify_world, bot_instance, recorder, event_loop
):
    """Monday's send does not silence Thursday's, through the whole path."""
    monday = notify_world.session_ids["2026-09-07"]
    thursday = notify_world.session_ids["2026-09-10"]

    event_loop.run_until_complete(send_after_lesson(bot_instance, svodka, monday))
    recorder.reset()
    report = event_loop.run_until_complete(
        send_after_lesson(bot_instance, svodka, thursday)
    )
    assert report.sent == report.planned and report.sent > 0, report.line()
