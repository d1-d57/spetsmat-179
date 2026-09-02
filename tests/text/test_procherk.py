"""ПРОЧЕРК — `Влад Быков —` is a statement, and the statement is about ATTENDANCE.

Rule 4 of the задание, and it is the rule most easily lost, because losing it looks like
nothing:

    🔴 ПРОЧЕРК `—` = ПРИШЁЛ И НЕ СДАЛ НИЧЕГО.  Это явка, а НЕ отсутствие записи.

By pluses alone «came and handed in nothing» and «was not here» are the same emptiness,
and the difference between them is the difference between «его не спросили» and «его не
было».  P6 already owns that distinction: ``AttendanceView`` carries ``(status, has_marks)``
and derives ``present_no_marks`` from the pair.  These tests check that the text channel
FEEDS that derivation and never builds a second one — and, just as importantly, that the
dash never reaches ``MarkingService``.
"""

from __future__ import annotations

from datetime import date

import pytest

import config
from core.services import bystryj_tekst as tekst
from core.services.marking import MarkingService
from core.services.sessions import SessionsService
from core.services.golos import Verdict
from infra.repositories import SqliteCatalogue, SqliteMarkJournal
from infra.sessions_repo import SqliteAttendanceBook, SqliteSessionBook


class FrozenClock:
    """A clock the test sets, so «сегодня» is a date this test chose."""

    def __init__(self, now: str = "2026-09-02T08:00:00Z") -> None:
        self._now = now

    def now_iso(self) -> str:
        return self._now


@pytest.fixture
def sessions(live_db, catalogue):
    """P6's service over the same live catalogue the rest of these tests use."""
    journal = SqliteMarkJournal(live_db)
    return SessionsService(
        SqliteSessionBook(live_db),
        SqliteAttendanceBook(live_db),
        MarkingService(journal, FrozenClock()),
        journal,
        catalogue,
        FrozenClock(),
    )


# =============================================================================
#  THE PARSER'S HALF: the dash survives as a fact
# =============================================================================

@pytest.mark.parametrize("dash", ["—", "-", "–"])
def test_procherk_all_three_dashes_mean_the_same_fact(dash, students, catalogue):
    """`—`, `-` and `–` are one statement written by three keyboards.

    The em dash is what the owner types, the hyphen is what a laptop gives without a
    compose key, and the en dash is what an autocorrect turns either into.  Accepting only
    the first would silently drop the явка of every child recorded on the wrong device.
    """
    draft = tekst.build_draft("Влад Быков %s" % dash, students=students, catalogue=catalogue)
    row = draft.rows[0]
    assert row.student_id == 11, row.reason
    assert row.present_no_marks is True
    assert row.cells == [], "a прочерк must produce no problem cells at all"


def test_procherk_goes_to_attendance_and_not_to_marks(students, catalogue):
    """The dash produces an attendance intent and NOTHING the mark path can write.

    This is the whole rule in one assertion: ``checked_cells`` — the one function that
    decides what «Записать» would write — must find nothing here, while the attendance
    side must find the child.
    """
    from bot.routers.photo import checked_cells
    from bot.routers.text_input import draft_to_state

    draft = tekst.build_draft("Влад Быков —", students=students, catalogue=catalogue)
    assert tekst.attendance_intents(draft) == [11]
    assert checked_cells(draft_to_state(draft)) == [], (
        "a прочерк reached the mark path; it must reach attendance only"
    )


def test_procherk_is_not_a_dash_used_as_a_separator(students, catalogue):
    """`Влад Быков — 3, 5` is a teacher punctuating, not a teacher reporting an empty hand.

    Reading the dash as «не сдал ничего» here would contradict the two problems written on
    the same line.  The dash counts ONLY when nothing else was written.
    """
    draft = tekst.build_draft("Влад Быков — 3, 5", students=students, catalogue=catalogue)
    row = draft.rows[0]
    assert row.present_no_marks is False
    assert [cell.label for cell in row.cells] == ["3", "5"]
    assert tekst.attendance_intents(draft) == []


def test_procherk_of_an_unresolved_name_claims_nobody(students, catalogue):
    """A dash after a name nobody recognises must not put anybody in the room.

    Attendance lands on a child or it does not land — the same rule ``checked_cells``
    applies to marks, and for the same reason: «probably Petya was here» is not a fact
    about anybody.  The teacher answers «кто это?» with a tap and the row counts then.
    """
    draft = tekst.build_draft("Пафнутий Чебышёв —", students=students, catalogue=catalogue)
    row = draft.rows[0]
    assert row.student_id is None
    assert row.verdict is Verdict.UNKNOWN
    assert row.present_no_marks is True, "the FACT survives; only its subject is missing"
    assert tekst.attendance_intents(draft) == []


# =============================================================================
#  P6's HALF: the two states really are different, through the live service
# =============================================================================

def test_procherk_present_no_marks_differs_from_absent(live_db, catalogue, sessions, students):
    """«Пришёл и не сдал» and «не был» are DIFFERENT values, read back from the database.

    The named test P6 built (`test_red_line_present_no_marks_differs_from_absent`) asserts
    this over P6's own writes.  This one asserts it over a write that STARTED as a typed
    dash, which is the seam this position adds — and it reads the result through P6's
    ``AttendanceView`` rather than through a second derivation of its own.
    """
    lesson = sessions.create_lesson(date(2026, 9, 2), config.SESSION_KINDS[0])

    draft = tekst.build_draft("Влад Быков —", students=students, catalogue=catalogue)
    for student_id in tekst.attendance_intents(draft):
        sessions.mark_attendance(lesson.id, student_id, tekst.PRESENT)

    # Somebody else, marked absent by the ordinary path.
    sessions.mark_attendance(lesson.id, 9, config.ATTENDANCE_STATUSES[1])

    views = sessions.attendance_for(lesson.id)

    came_and_handed_in_nothing = views[11]
    was_not_there = views[9]

    assert came_and_handed_in_nothing.present_no_marks is True
    assert was_not_there.present_no_marks is False
    assert came_and_handed_in_nothing != was_not_there, (
        "the two states collapsed into one value; the whole point of the прочерк is gone"
    )

    # And the third state — a child nobody wrote anything about — is neither.
    assert 23 not in views, "a child with no record must not be invented as present"


def test_procherk_twice_does_not_double_the_attendance(catalogue, sessions, students):
    """The same message sent twice leaves one attendance row, not two.

    Idempotency is P6's (``mark_attendance`` is idempotent on the same status); this test
    is here to prove that the text path does not defeat it by resending a different fact.
    """
    lesson = sessions.create_lesson(date(2026, 9, 2), config.SESSION_KINDS[0])
    draft = tekst.build_draft("Влад Быков —", students=students, catalogue=catalogue)

    first = [
        sessions.mark_attendance(lesson.id, student_id, tekst.PRESENT)
        for student_id in tekst.attendance_intents(draft)
    ]
    second = [
        sessions.mark_attendance(lesson.id, student_id, tekst.PRESENT)
        for student_id in tekst.attendance_intents(draft)
    ]

    assert [outcome.written for outcome in first] == [True]
    assert [outcome.written for outcome in second] == [False]
    assert [outcome.changed for outcome in second] == [False]
    assert len(sessions.attendance_for(lesson.id)) == 1


# =============================================================================
#  A ЯВКА IS A CLAIM ABOUT A CHILD, AND IT NEEDS THE SAME PROOF A PLUS DOES
# =============================================================================

def test_procherk_of_a_row_the_parser_distrusts_claims_nobody(students, catalogue):
    """«Санин 7 дома —» — the guard emptied Домра's cells and the явка went through anyway.

    Found by the §3 verifier, and it is the mark bug one door over: `present_no_marks` was
    read straight off the row while the CELLS of the same row were being refused. «Записать»
    then recorded Домра Евгений as present at a lesson the teacher never wrote him into.

    Worse than a stray plus in one respect: a plus that goes missing is noticed by the child
    it went missing from, and an invented явка is a fact nobody will ever go looking for.

    The gate heals itself — a tap on «кто это?» sets the verdict to CERTAIN and the явка
    counts from then on.
    """
    from bot.routers.text_input import draft_to_state, present_students

    draft = tekst.build_draft("Санин 7 дома —", students=students, catalogue=catalogue)
    stray = draft.rows[1]

    assert stray.student_id is not None, "this test needs the row to have resolved"
    assert stray.verdict is Verdict.DOUBTFUL
    assert stray.present_no_marks is True, "the FACT survives; only its subject is doubted"
    assert tekst.attendance_intents(draft) == []
    assert present_students(draft_to_state(draft)) == []


def test_procherk_of_a_confirmed_row_still_counts(students, catalogue):
    """The gate must refuse the doubtful row and nothing else."""
    from bot.routers.text_input import draft_to_state, present_students

    draft = tekst.build_draft("Влад Быков —", students=students, catalogue=catalogue)

    assert tekst.attendance_intents(draft) == [11]
    assert present_students(draft_to_state(draft)) == [11]


def test_procherk_counts_once_the_teacher_has_answered_kto_eto(students, catalogue):
    """The stored twin reads the verdict the TAP wrote, which is what makes the gate
    self-healing rather than a dead end for a child the parser could not name."""
    from bot.routers.text_input import draft_to_state, present_students

    stored = draft_to_state(
        tekst.build_draft("Санин 7 дома —", students=students, catalogue=catalogue)
    )
    assert present_students(stored) == []

    # Exactly what ``pick_student`` writes when the teacher taps an alternative.
    stored["rows"][1]["verdict"] = Verdict.CERTAIN.value
    assert present_students(stored) == [stored["rows"][1]["student_id"]]
