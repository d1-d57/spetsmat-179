"""Test 5 of the five, and the reason this position is paid.

The grid projection produced by ``core/services/progress.py`` -- which asks SQLite for
the last event of each pair with a grouped ``max(id)`` -- is compared against a naive
fold of the same journal written a SECOND, INDEPENDENT way: a plain Python ``dict``,
event by event, no SQL, no import of ``STATE_AFTER``, the three event names spelled out
here as literal strings.

Two independently written paths to one answer is not a tautology.  It catches the whole
class "the table drifted from reality" -- the projection quietly disagreeing with the
journal it is supposed to be a view of.

THE WORLD IS SMALL ON PURPOSE: five students and four problems, twenty cells.  All the
bugs of this kind live in collisions between events on the same cell, and random large
ids almost never collide.  The required coverage of at least 200 pairs is reached by
ACCUMULATING comparisons over thirty randomised scenarios on that small world, not by
widening the world -- a wide world would compare more pairs and exercise fewer collisions.

The test prints its coverage as a number.  A negative verdict here carries its own
coverage: "0 mismatches, 600 of 600 pairs compared", never "no mismatches found" -- zero
compared pairs on a non-empty set is RED, and the two are indistinguishable without the
number.
"""

from __future__ import annotations

import random

import config
from core.services.marking import MarkingService, NothingToReverse
from core.services.progress import ProgressService
from infra.db import connect
from infra.repositories import SqliteCatalogue, SqliteMarkJournal
from tests.conftest import FrozenClock, seed_world

#: Five students by four problems.  Twenty cells, so events collide constantly.
STUDENTS = 5
PROBLEMS = 4

#: Thirty scenarios of twenty-five operations each.  30 x 20 = 600 accumulated pairs,
#: comfortably past the 200 the criterion asks for, and every scenario is a different
#: interleaving of events over the same twenty cells.
SCENARIOS = 30
OPERATIONS_PER_SCENARIO = 25

#: The target states a button can carry.  Written as the plain strings the schema uses,
#: so this file does not lean on the enum it is checking.
TARGETS = ("solved", "retracted", "empty")

#: What each event kind does to a cell, written out here in full.  This is the SECOND
#: definition of the fork; ``core/models.py`` holds the first, and the point of the test
#: is that the two were written independently and must agree.
#:
#:   'assert'  -> the cell is credited
#:   'retract' -> handed in, not credited; still counts in statistics
#:   'erratum' -> struck out entirely, as if the record had never existed
NAIVE_STATE_AFTER = {
    "assert": "solved",
    "retract": "retracted",
    "erratum": "empty",
}


def naive_fold(connection) -> dict:
    """Fold the raw journal into cell states with a dict, oldest event first.

    Deliberately primitive: it reads the three columns it needs in id order and keeps
    overwriting one dict entry per pair.  No grouping, no max(), no join -- if the
    grouped query in ``infra/repositories.py`` has an off-by-one in its ordering or drops
    a row on some join path, this fold does not share the mistake.
    """
    states = {}
    rows = connection.execute(
        "select student_id, problem_id, event from marks order by id"
    ).fetchall()
    for row in rows:
        states[(row["student_id"], row["problem_id"])] = NAIVE_STATE_AFTER[row["event"]]
    return states


def run_scenario(connection, seed: int) -> tuple:
    """Play one randomised scenario and return (projected, naive) state maps.

    Both maps cover EVERY pair of the world, including the pairs that no event ever
    touched: those are the cells the teacher still has to tap, and a projection that
    silently omitted them would show a short sheet.
    """
    rng = random.Random(seed)
    clock = FrozenClock()
    world = seed_world(
        connection,
        students=STUDENTS,
        sheets=(("обязательная", "обязательная", "обычная", "звезда"),),
    )
    journal = SqliteMarkJournal(connection)
    catalogue = SqliteCatalogue(connection)
    marking = MarkingService(journal, clock)
    progress = ProgressService(journal, catalogue)

    from core.models import CellState

    target_of = {
        "solved": CellState.SOLVED,
        "retracted": CellState.RETRACTED,
        "empty": CellState.EMPTY,
    }

    for step in range(OPERATIONS_PER_SCENARIO):
        student = rng.choice(world.student_ids)
        problem = rng.choice(world.problem_ids)
        target = rng.choice(TARGETS)
        clock.tick()
        try:
            marking.set_state(
                student,
                problem,
                target_of[target],
                source=rng.choice(config.MARK_SOURCES),
                session_id=world.session_id,
                teacher_id=rng.choice(world.teacher_ids),
            )
        except NothingToReverse:
            # Retracting a cell that never had an event is a caller bug, and the service
            # says so rather than inventing an event to reverse.  In a random walk it
            # simply means this step did nothing; the scenario carries on.
            pass

    projected_states = progress.states_for_many(world.student_ids, world.problem_ids)
    projected = {pair: state.value for pair, state in projected_states.items()}

    folded = naive_fold(connection)
    naive = {
        (student, problem): folded.get((student, problem), "empty")
        for student in world.student_ids
        for problem in world.problem_ids
    }
    return projected, naive


def test_projection_equals_a_naive_fold_of_the_journal(tmp_path, capsys):
    """The differential itself, accumulated over thirty scenarios on the small world."""
    compared = 0
    mismatches = []

    for scenario in range(SCENARIOS):
        db_path = tmp_path / ("scenario-%02d.db" % scenario)
        from infra.db import apply_migrations

        apply_migrations(db_path, config.MIGRATIONS_DIR)
        connection = connect(db_path)
        try:
            projected, naive = run_scenario(connection, seed=1000 + scenario)
        finally:
            connection.close()

        assert set(projected) == set(naive), (
            "scenario %d: the projection and the fold do not even cover the same pairs"
            % scenario
        )
        for pair in sorted(projected):
            compared += 1
            if projected[pair] != naive[pair]:
                mismatches.append(
                    "scenario %d, pair %s: projection says %s, journal fold says %s"
                    % (scenario, pair, projected[pair], naive[pair])
                )

    expected = SCENARIOS * STUDENTS * PROBLEMS
    # The coverage goes to stdout so that `make check` and a bare pytest run both show
    # it.  A verdict without coverage is not a verdict: "checked 2 of 9" and "checked
    # 9 of 9" read identically when only the mismatch count is printed.
    with capsys.disabled():
        print(
            "\n[differential] mismatches %d, compared %d of %d student x problem pairs "
            "over %d scenarios on a world of %d students x %d problems"
            % (len(mismatches), compared, expected, SCENARIOS, STUDENTS, PROBLEMS)
        )

    assert compared == expected, (
        "coverage collapsed: compared %d pairs, expected %d" % (compared, expected)
    )
    assert compared >= 200, "coverage below the 200 pairs the criterion asks for"
    assert not mismatches, "\n".join(mismatches)


def test_a_planted_drift_is_caught(tmp_path):
    """The differential must be able to FAIL, or its green means nothing.

    A projection is faked by hand -- one cell flipped -- and the same comparison is run
    against the honest fold.  If this test does not see the flip, the test above is
    decoration.
    """
    db_path = tmp_path / "planted.db"
    from infra.db import apply_migrations

    apply_migrations(db_path, config.MIGRATIONS_DIR)
    connection = connect(db_path)
    try:
        projected, naive = run_scenario(connection, seed=777)
        assert projected == naive, "the honest comparison must agree before we plant"

        drifted = dict(projected)
        pair = sorted(drifted)[0]
        drifted[pair] = "solved" if drifted[pair] != "solved" else "empty"

        mismatches = [key for key in drifted if drifted[key] != naive[key]]
        assert len(mismatches) == 1, (
            "the comparison did not notice a planted drift on %s" % (pair,)
        )
    finally:
        connection.close()
