"""REGISTERED, AND STILL UNREACHABLE -- the third way a written screen does nothing.

The dependency gates in this directory answer «can this handler be SERVED».  They cannot
answer «can it be REACHED», and the two failures share one symptom: a screen that was
written, tested, accepted, and that does nothing in the field.

aiogram tries routers in include order and stops at the first handler whose filters match.
Two screens claiming the same trigger therefore do not both work and do not raise -- the
earlier wins in silence, and where its role gate refuses the caller, the later screen is
simply dead.

WHY THIS GATE HAS A LEDGER INSTEAD OF BEING RED.  Both collisions below are defects in
files this position may not touch (``bot/routers/``, ``bot/handlers/`` and
``bot/keyboards/`` are read-only for it, and the fix is a one-word rename in each).
Leaving the gate plainly red would have made every future run of the suite red for a
reason nobody in this directory can fix, and a permanently red gate is read as noise
within a week.  So the known two are written down WITH THEIR FIX, printed loudly on every
run, and anything NEW goes red.  Removing a line from the ledger is the last step of
fixing the defect it names.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dependency_scan as scanner  # noqa: E402

#: trigger -> (who claims it, in resolution order · what the fix is).  Every entry is a
#: LIVE DEFECT, not an exemption: the second claimant of each is unreachable right now.
KNOWN = {
    "callback:vy": (
        "bot.routers.views.open_year_callback (ViewYear, bot/keyboards/views.py) "
        "shadows bot.routers.voice.confirm (VoiceConfirm, bot/routers/voice.py:119) -- "
        "VoiceConfirm().pack() == ViewYear(student_id=1).pack() == 'vy:1' byte for byte, "
        "so «Записать» on a dictation reaches views-student, whose require_role refuses a "
        "teacher: a voice draft cannot be written to the journal by anyone. "
        "FIX: one word -- give VoiceConfirm a prefix of its own (e.g. prefix='vgo'). "
        "Include order cannot fix it: whichever router goes first, the other screen dies."
    ),
    "text:/me": (
        "bot.handlers.student.show_me shadows bot.handlers.teacher.show_me -- the student "
        "router is included first and claims /me for everybody, then refuses a teacher by "
        "role, so a teacher's /me answers «Этот экран вам не открыт». "
        "FIX: one filter -- the student handler should not claim the command for callers "
        "it will refuse."
    ),
}


def test_no_two_screens_claim_the_same_trigger(dispatcher, capsys):
    found = scanner.collisions(dispatcher)
    claims = scanner.trigger_claims(dispatcher)
    fresh = {trigger: who for trigger, who in found.items() if trigger not in KNOWN}
    stale = [trigger for trigger in KNOWN if trigger not in found]

    with capsys.disabled():
        print(
            "\n[достижимость] триггеров прочитано %d · столкновений %d "
            "(известных %d, новых %d)"
            % (len(claims), len(found), len(found) - len(fresh), len(fresh))
        )
        for trigger in sorted(set(found) & set(KNOWN)):
            print("  🔴 ИЗВЕСТНЫЙ ДЕФЕКТ %s — %s" % (trigger, ", ".join(found[trigger])))
            print("     %s" % KNOWN[trigger])

    assert claims, "ни одного триггера не прочитано — гейт ничего не проверил"
    assert not fresh, (
        "%d нов(ое/ых) столкновени(е/й) триггеров: экран зарегистрирован и недостижим, "
        "потому что более ранний роутер забирает то же обновление:\n%s"
        % (
            len(fresh),
            "\n".join("  %s — %s" % (trigger, ", ".join(who)) for trigger, who in sorted(fresh.items())),
        )
    )
    assert not stale, (
        "в ведомости KNOWN есть записи, которых больше нет в коде — дефект починен, "
        "удалите строку: %s" % ", ".join(stale)
    )
