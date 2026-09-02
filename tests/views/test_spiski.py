"""The lists, tested against the real seed rather than a toy world.

The silence rule is the only genuinely new computation in this position, and it is the
one thing on the teacher's screen that fixes a measured defect of the sheet system --
«проверяющие зачастую уделяют больше времени сильным учащимся».  A table of everybody
against everything does not fix it; the list of who has said nothing does.  So it is
tested on data prepared day by day, and its named test is the one the готовности criterion
runs by name.
"""

from __future__ import annotations

import config
from core.models import CellState
from core.services.spiski import DEBT_HORIZON_SHEETS, RECENT_SHEETS

#: Three consecutive lesson days plus one older one.  Spelled out rather than generated,
#: because the whole question is what falls inside the window and what falls outside it.
OLD_DAY = "2026-09-01"
DAYS = ("2026-09-08", "2026-09-15", "2026-09-22")


def _problem_of(catalogue, sheet_index: int = 0, problem_index: int = 0):
    sheets = sorted(catalogue.sheets(), key=lambda sheet: sheet.ord)
    return catalogue.problems_of_sheet(sheets[sheet_index].id)[problem_index]


# ----------------------------------------------------------------------- silence

def test_silent_list_names_the_students_who_handed_in_nothing_for_three_sessions(
    spiski, seeded_catalogue, mark_on, capsys
):
    """The named test of the готовности criterion, on prepared data.

    Three lesson days are written into the journal.  One student is active on every one
    of them, one is active only on the day BEFORE the window opens, and everybody else
    has never handed in anything at all.  The first must not be on the list, the second
    and the third must.
    """
    students = seeded_catalogue.students()
    speaker, lapsed = students[0], students[1]
    problem = _problem_of(seeded_catalogue)

    mark_on(lapsed.id, problem.id, OLD_DAY)
    for day in DAYS:
        # A different problem each day: the same cell twice would be an idempotent
        # no-write on the second day and the journal would hold one event, not three.
        mark_on(speaker.id, _problem_of(seeded_catalogue, 0, DAYS.index(day) + 1).id, day)

    result = spiski.silent()

    assert result.enough_days is True
    assert result.days == list(DAYS)
    assert result.considered == 56, "the sweep must be over the whole roster"
    named = [entry.student.id for entry in result.students]
    assert speaker.id not in named, "a student active inside the window is not silent"
    assert lapsed.id in named, "a student last active BEFORE the window is silent"
    assert len(named) == 55, "one student spoke; the other fifty-five did not"

    lapsed_entry = next(e for e in result.students if e.student.id == lapsed.id)
    assert lapsed_entry.last_active_day == OLD_DAY
    never = next(e for e in result.students if e.student.id == students[2].id)
    assert never.last_active_day is None

    with capsys.disabled():
        print(
            "\n[молчуны] окно %d занятий (%s) · молчат %d из %d · проверено %d из 56"
            % (
                config.SILENT_SESSIONS,
                ", ".join(result.days),
                result.found,
                result.considered,
                result.considered,
            )
        )


def test_silence_is_measured_over_config_silent_sessions_and_not_a_literal(
    spiski, seeded_catalogue, mark_on
):
    """The window length is the school's number, read from ``config.py``."""
    assert config.SILENT_SESSIONS == 3
    student = seeded_catalogue.students()[0]
    for index, day in enumerate(DAYS + ("2026-09-29",)):
        mark_on(student.id, _problem_of(seeded_catalogue, 0, index).id, day)

    assert len(spiski.silent().days) == config.SILENT_SESSIONS
    assert len(spiski.silent(sessions=2).days) == 2


def test_too_few_lesson_days_is_not_an_empty_silent_list(spiski, seeded_catalogue, mark_on):
    """Fewer days than the rule needs is «нечего мерить», never «все в порядке».

    An empty list of silent students reads as good news.  When the journal holds one
    lesson day and the rule asks for three, the honest answer is that the question cannot
    be answered yet -- and the screen has to be able to tell the two apart.
    """
    mark_on(seeded_catalogue.students()[0].id, _problem_of(seeded_catalogue).id, DAYS[0])
    result = spiski.silent()
    assert result.enough_days is False
    assert result.students == []
    assert result.considered == 56, "the coverage stands even when the answer is «not yet»"


def test_an_erratum_does_not_rescue_a_silent_student(spiski, seeded_catalogue, mark_on):
    """A struck-out record is not a hand-in.

    ``erratum`` means the record should never have existed.  If it counted as activity, a
    teacher's mistyped button on the last day would take a student off the silent list --
    the one student the screen exists to surface.
    """
    students = seeded_catalogue.students()
    ghost = students[3]
    problem = _problem_of(seeded_catalogue)

    for day in DAYS:
        mark_on(students[0].id, _problem_of(seeded_catalogue, 0, DAYS.index(day) + 1).id, day)
    # Written and then struck out, both on the last day of the window.
    mark_on(ghost.id, problem.id, DAYS[-1])
    mark_on(ghost.id, problem.id, DAYS[-1], state=CellState.EMPTY)

    named = [entry.student.id for entry in spiski.silent().students]
    assert ghost.id in named, "an erratum-struck cell leaves the student silent"


def test_a_retract_counts_as_a_conversation_that_happened(spiski, seeded_catalogue, mark_on):
    """«Сдал и не защитил» is not silence: the student stood there and talked."""
    students = seeded_catalogue.students()
    defended, problem = students[4], _problem_of(seeded_catalogue)

    for day in DAYS:
        mark_on(students[0].id, _problem_of(seeded_catalogue, 0, DAYS.index(day) + 1).id, day)
    mark_on(defended.id, problem.id, DAYS[-1])
    mark_on(defended.id, problem.id, DAYS[-1], state=CellState.RETRACTED)

    named = [entry.student.id for entry in spiski.silent().students]
    assert defended.id not in named


def test_a_day_nobody_in_the_group_worked_still_counts_as_a_lesson_day(
    spiski, seeded_catalogue, mark_on
):
    """The day sequence is the school's, not one group's.

    If lesson days were derived only from the students being looked at, a group that went
    quiet for three weeks would have no lesson days of its own -- and would therefore
    never appear on the list the whole screen exists to draw.
    """
    others = seeded_catalogue.students()[:2]
    for index, day in enumerate(DAYS):
        mark_on(others[0].id, _problem_of(seeded_catalogue, 0, index).id, day)

    assert spiski.lesson_days() == list(DAYS)
    quiet_ids = [entry.student.id for entry in spiski.silent().students]
    assert others[1].id in quiet_ids


# --------------------------------------------------------------------- graveyard

def test_graveyard_delegates_the_threshold_to_p1(spiski, seeded_catalogue, mark_on):
    """The threshold is read in P1's single place and never re-spelled here."""
    result = spiski.graveyard()
    assert result.threshold == config.GRAVEYARD_THRESHOLD
    assert result.considered == 56
    assert len(result.sheets) == RECENT_SHEETS


def test_a_problem_taken_by_enough_students_leaves_the_graveyard(
    spiski, seeded_catalogue, mark_on
):
    """At the threshold the problem stops being a graveyard, and the list gets shorter."""
    sheets = sorted(seeded_catalogue.sheets(), key=lambda sheet: sheet.ord)
    current = sheets[-1]
    problem = seeded_catalogue.problems_of_sheet(current.id)[0]
    students = seeded_catalogue.students()

    before = spiski.graveyard()
    assert any(
        entry.row.problem.id == problem.id for entry in before.entries
    ), "with an empty journal every problem of the recent sheets is a graveyard"

    for student in students[: config.GRAVEYARD_THRESHOLD]:
        mark_on(student.id, problem.id, DAYS[0])

    after = spiski.graveyard()
    assert not any(entry.row.problem.id == problem.id for entry in after.entries)
    assert after.found == before.found - 1


def test_graveyard_is_ordered_by_how_few_took_the_problem(spiski, seeded_catalogue, mark_on):
    """«л.6 №11 (0), л.6 №14 (1), л.5 №19 (2)» — the worst line first, because it is the
    one worth saying out loud in the room."""
    sheets = sorted(seeded_catalogue.sheets(), key=lambda sheet: sheet.ord)
    problems = seeded_catalogue.problems_of_sheet(sheets[-1].id)
    students = seeded_catalogue.students()

    mark_on(students[0].id, problems[1].id, DAYS[0])
    mark_on(students[0].id, problems[2].id, DAYS[0])
    mark_on(students[1].id, problems[2].id, DAYS[0])

    taken = [entry.row.taken_by for entry in spiski.graveyard().entries]
    assert taken == sorted(taken), "the list runs from the least taken upwards"


# ------------------------------------------------------------------------- debts

def test_debts_within_the_horizon_are_enumerated_and_older_ones_are_collapsed(
    spiski, seeded_catalogue
):
    """A short list with one boundary, and a single line for everything older.

    The seed leaves ``first_sheet_id`` NULL, so P1 counts a student's debts from the very
    first sheet of the year: with an empty journal every obligatory problem of every
    earlier sheet is owed.  That is the worst case for this screen and exactly the one the
    rule exists for -- a person must not be handed eighteen sheets' worth of what they owe.
    """
    student = seeded_catalogue.students()[0]
    result = spiski.debts(student.id)

    assert result.total > 0
    assert len(result.near) == DEBT_HORIZON_SHEETS
    for group in result.near:
        assert group.problems, "an enumerated group with nothing in it is not a group"
        assert all(problem.is_obligatory for problem in group.problems)
    assert result.older_problems > 0, "the seed has more history than the horizon"
    assert result.older_sheets > 0
    assert [group.sheet.ord for group in result.near] == sorted(
        [group.sheet.ord for group in result.near], reverse=True
    ), "the nearest boundary is read first"


def test_the_nearest_boundary_skips_sheets_that_owe_nothing(
    spiski, seeded_catalogue, seeded_progress
):
    """«Ближайшая граница» is the nearest sheet where something is in fact owed.

    The last four sheets of the seed (``1д``-``4д``) carry no obligatory problems at all.
    A window counted as "the two sheets before the current one" is therefore empty on the
    real data, and the student would be shown a collapsed line and no boundary -- the one
    thing the screen is asked to show.  So the window counts sheets that carry a debt.
    """
    student = seeded_catalogue.students()[0]
    current = spiski.current_sheet()
    result = spiski.debts(student.id)

    assert result.near, "the real seed must still name a boundary"
    assert current.ord - result.near[0].sheet.ord > DEBT_HORIZON_SHEETS, (
        "this seed's nearest sheet with a debt is further back than the raw window"
    )
    named = {group.sheet.ord for group in result.near}
    owed_ords = {
        seeded_catalogue.sheet(problem.sheet_id).ord
        for problem in seeded_progress.debts(student.id, current.ord)
    }
    assert named == set(sorted(owed_ords, reverse=True)[:DEBT_HORIZON_SHEETS])


def test_a_student_who_owes_nothing_gets_a_clear_debt_list(spiski, seeded_catalogue, mark_on):
    """Every obligatory problem handed in means an empty list, and it says so."""
    student = seeded_catalogue.students()[0]
    current = spiski.current_sheet()
    for sheet in seeded_catalogue.sheets():
        if sheet.ord >= current.ord:
            continue
        for problem in seeded_catalogue.problems_of_sheet(sheet.id):
            if problem.is_obligatory:
                mark_on(student.id, problem.id, DAYS[0])

    result = spiski.debts(student.id)
    assert result.is_clear
    assert result.total == 0


# -------------------------------------------------------------------- own year

def test_the_year_overview_covers_every_sheet_in_issue_order(spiski, seeded_catalogue, mark_on):
    """First of September: the student opens the bot and sees the whole eighth form.

    Every sheet is present, including the ones with nothing on them -- a year that
    silently dropped its empty sheets would not be the year that happened.
    """
    student = seeded_catalogue.students()[0]
    sheets = sorted(seeded_catalogue.sheets(), key=lambda sheet: sheet.ord)
    problem = seeded_catalogue.problems_of_sheet(sheets[2].id)[0]
    mark_on(student.id, problem.id, DAYS[0])

    rows = spiski.year(student.id)
    assert len(rows) == 18
    assert [row.sheet.ord for row in rows] == [sheet.ord for sheet in sheets]
    assert sum(row.total for row in rows) == 544
    assert sum(row.solved for row in rows) == 1
    assert rows[2].solved == 1
