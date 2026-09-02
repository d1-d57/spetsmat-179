"""The domain of the room, where it does not need a dispatcher to be wrong.

THE SESSION OF A DAY IS THE ONE THING HERE THAT CAN GO WRONG SILENTLY.  ``sessions.held_on``
carries no unique index and three heads open their screens inside the same minute; two
session rows for one day would split one lesson's attendance in half, and each half would
look perfectly consistent to whoever was reading it.  That is the failure a test has to
catch, because nobody catches it by eye.
"""

from __future__ import annotations

from datetime import date, timedelta

import config
from core.services.room import RoomError, day_in_words
from conftest import OTHER_ROOM, ROOM, ROOM_SIZE, TODAY


def _sessions(connection, held_on: str) -> list:
    return [row["id"] for row in connection.execute(
        "select id from sessions where held_on = ? order by id", (held_on,)
    )]


def test_three_heads_opening_the_same_evening_get_one_session(
    connection, dispatcher, room_world
):
    room_service = dispatcher.workflow_data["room_service"]
    head = room_world.head_teacher_id

    assert _sessions(connection, TODAY) == []
    first = room_service.room_day(ROOM, TODAY, host_teacher_id=head)
    second = room_service.room_day(ROOM, TODAY, host_teacher_id=head)
    third = room_service.room_day(OTHER_ROOM, TODAY, host_teacher_id=room_world.neighbour_teacher_id)

    assert first.session_id == second.session_id == third.session_id
    assert len(_sessions(connection, TODAY)) == 1, (
        "opening the screen three times wrote %d session rows for one day"
        % len(_sessions(connection, TODAY))
    )


def test_a_day_that_already_carries_two_sessions_resolves_to_the_smaller_id(
    connection, dispatcher, room_world
):
    """A pair written before the get-or-create existed, or by an import.

    Every reader takes ``min(id)``, so the halves cannot drift apart afterwards: whichever
    screen opens next puts its rows where the earlier ones already are.
    """
    room_service = dispatcher.workflow_data["room_service"]
    for _ in range(2):
        connection.execute(
            "insert into sessions (held_on, kind) values (?, ?)",
            (TODAY, config.SESSION_KINDS[0]),
        )
    connection.commit()
    ids = _sessions(connection, TODAY)
    assert len(ids) == 2

    day = room_service.room_day(ROOM, TODAY, host_teacher_id=room_world.head_teacher_id)
    assert day.session_id == min(ids)


def test_a_room_reads_only_the_children_whose_standing_day_is_this_one(
    dispatcher, room_world
):
    """A day of the week nobody has a lesson on is an EMPTY room, not a traceback.

    It is a real state -- a head who opens the bot on a Sunday -- and the honest answer is
    a room with nobody in it rather than an exception he has no way to read.
    """
    room_service = dispatcher.workflow_data["room_service"]
    other_weekday = (date.fromisoformat(TODAY) + timedelta(days=1)).isoformat()
    day = room_service.room_day(
        ROOM, other_weekday, host_teacher_id=room_world.head_teacher_id
    )
    assert day.members == ()
    assert day.came == 0 and day.total == 0


def test_the_debt_count_is_asked_for_and_never_recomputed(dispatcher, room_world):
    """Every count on the screen equals what ``ProgressService`` answers, child by child.

    The screen does not own the rule -- obligatory problems on sheets older than the
    current one, counted from the child's ``first_sheet_id`` -- and the port it is given
    offers no way to reimplement it.  This checks the two agree over the whole room, so a
    screen that started counting for itself would be caught the first time the rule moved.
    """
    room_service = dispatcher.workflow_data["room_service"]
    progress = dispatcher.workflow_data["progress"]
    day = room_service.room_day(ROOM, TODAY, host_teacher_id=room_world.head_teacher_id)

    mismatched = [
        (member.student.surname, member.debts, len(progress.debts(member.student.id, 2)))
        for member in day.members
        if member.debts != len(progress.debts(member.student.id, 2))
    ]
    assert not mismatched, "the screen disagrees with the debts service: %r" % (mismatched[:3],)
    assert len(day.members) == ROOM_SIZE
    assert any(member.debts > 0 for member in day.members), (
        "nobody in the room owes anything: this test cannot tell a real count from a zero"
    )


def test_a_guest_may_not_be_brought_in_twice(dispatcher, room_world):
    """A second row for one child at one session is what the schema's unique key forbids.

    Refused in the service and with a sentence, rather than left to a driver error the
    handler would have to read out of a string.
    """
    room_service = dispatcher.workflow_data["room_service"]
    head = room_world.head_teacher_id
    day = room_service.room_day(ROOM, TODAY, host_teacher_id=head)
    guest_id = room_world.outsiders[0]

    day = room_service.add_guest(day, guest_id, head, host_teacher_id=head)
    try:
        room_service.add_guest(day, guest_id, head, host_teacher_id=head)
    except RoomError:
        pass
    else:
        raise AssertionError("the same guest was brought in twice")


def test_the_day_is_read_out_in_words_in_the_genitive(dispatcher):
    """«четверг, 4 сентября», never «2026-09-04» and never «4 сентябрь».

    The head reads the header to check that he is looking at today rather than at a screen
    he left open since Monday, and an ISO date does not answer that at a glance.
    """
    assert day_in_words("2026-09-03") == "четверг, 3 сентября"
    assert day_in_words("2026-01-01") == "четверг, 1 января"
    assert day_in_words("2026-05-31") == "воскресенье, 31 мая"


class _EnrollmentSpy:
    """Forwards ``resolve_many`` and REDDENS on any other attribute of the seam.

    The module's own claim used to be «there is no method here that could write to
    enrollment», and it was not true: the constructor takes the whole
    ``EnrollmentService``, and ``assign``, ``move`` and ``end`` are one attribute away.  A
    Protocol declares the narrow seam but does not build a wall around the object handed in
    at runtime, so this is the thing that actually holds the line -- and the claim in the
    docstring now says «checked», which is what it is.
    """

    def __init__(self, real) -> None:
        self._real = real
        self.touched = []

    def __getattr__(self, name):
        self.touched.append(name)
        if name != "resolve_many":
            raise AssertionError(
                "core/services/room.py reached for %r on the enrollment seam: the standing "
                "arrangement is READ from this module and nothing else" % (name,)
            )
        return self._real.resolve_many


def test_this_module_touches_exactly_one_method_of_the_enrollment_seam(
    connection, roster_path, dispatcher, room_world
):
    import sqlite3

    from core.services.enrollment import EnrollmentService
    from core.services.progress import ProgressService
    from core.services.room import RoomService
    from infra.db import SystemClock
    from infra.enrollment_repo import SqliteEnrollmentRepo
    from infra.repositories import SqliteCatalogue, SqliteMarkJournal
    from infra.room_repo import (
        SqliteAttendance,
        SqliteRoomRoster,
        SqliteSessions,
        SqliteTeachers,
    )

    roster_connection = sqlite3.connect(roster_path)
    roster_connection.row_factory = sqlite3.Row
    catalogue = SqliteCatalogue(connection)
    spy = _EnrollmentSpy(EnrollmentService(SqliteEnrollmentRepo(connection)))
    service = RoomService(
        catalogue=catalogue,
        enrollment=spy,
        progress=ProgressService(SqliteMarkJournal(connection), catalogue),
        attendance=SqliteAttendance(connection),
        sessions=SqliteSessions(connection),
        teachers=SqliteTeachers(connection),
        roster=SqliteRoomRoster(roster_connection),
        clock=SystemClock(),
    )
    try:
        head = room_world.head_teacher_id
        day = service.room_day(ROOM, TODAY, host_teacher_id=head)
        service.candidate_guests(day)
        service.teacher_names(day)
        day = service.set_present(day, room_world.students[0], True, host_teacher_id=head)
        day = service.set_today_teacher(
            day, room_world.students[0], room_world.other_teacher_of(0), host_teacher_id=head
        )
        day = service.add_guest(day, room_world.outsiders[0], head, host_teacher_id=head)
        service.set_present(day, room_world.students[0], False, host_teacher_id=head)
    finally:
        roster_connection.close()

    assert set(spy.touched) == {"resolve_many"}, spy.touched
    assert spy.touched, "the seam was never used at all: this test would pass on a stub"
