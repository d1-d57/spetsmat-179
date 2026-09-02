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

from core.services.enrollment import EnrollmentService
from fakes import FakeEnrollmentStore
from infra.enrollment_repo import SqliteEnrollmentRepo


@pytest.fixture
def store():
    return FakeEnrollmentStore()


@pytest.fixture
def fake_enrollment(store):
    """The service over the dict store: the domain, without a database in the way."""
    return EnrollmentService(store)


@pytest.fixture
def enrollment_repo(connection):
    return SqliteEnrollmentRepo(connection)


@pytest.fixture
def enrollment(enrollment_repo):
    """The service over the real migrated database."""
    return EnrollmentService(enrollment_repo)
