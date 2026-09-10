"""Fixtures for the enrollment position: the domain on a dict, the store on real SQLite.

TWO LEVELS, ON PURPOSE.

  * ``fake_enrollment`` runs the service over ``fakes.FakeEnrollmentStore`` so that the
    DOMAIN rules — a move closes and opens, the weekday is part of the key, a no-op move
    is refused — are tested without a database in the way.

  * ``enrollment`` runs the same service over the real migrated database, which is where
    the schema's guards are proven rather than imitated.

The world these build is small on purpose — five students, two teachers, a couple of
weekdays.  All the bugs in interval arithmetic live in collisions, and large random ids
never collide.
"""

from __future__ import annotations

import pytest

from core.services.enrollment import TEACHER_CEILING, EnrollmentService
from fakes import FakeCalendar, FakeEnrollmentStore
from infra.enrollment_repo import SqliteEnrollmentRepo


@pytest.fixture
def store():
    return FakeEnrollmentStore()


@pytest.fixture
def fake_enrollment(store):
    """The service over the dict store: the domain, without a database in the way."""
    return EnrollmentService(store)


@pytest.fixture
def calendar():
    """Everybody attends everything by default; a test narrows it by reassigning."""
    return FakeCalendar()


@pytest.fixture
def guarded_enrollment(store, calendar):
    """The same dict store, with the day-attendance and ceiling refusals switched on.

    A separate fixture rather than turning them on in ``fake_enrollment``: most of
    ``test_service.py`` tests interval arithmetic that has nothing to do with either
    rule, and turning them on there would make every one of those tests responsible
    for a calendar it never mentions.
    """
    return EnrollmentService(store, calendar=calendar, ceiling=TEACHER_CEILING)


@pytest.fixture
def enrollment_repo(connection):
    return SqliteEnrollmentRepo(connection)


@pytest.fixture
def enrollment(enrollment_repo):
    """The service over the real migrated database."""
    return EnrollmentService(enrollment_repo)
