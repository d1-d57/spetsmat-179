"""Fixtures over the synthetic conduit built in ``synthetic.py``.

The real book is the personal data of fifty-six children.  It is not in the repository and
never will be, so a suite that could only run beside it would be a suite almost nobody
could run -- not CI, not the acceptance pass, not the next заход.  Everything here works
without it; ``test_real_workbook.py`` uses the real book when it happens to be present.
"""

from __future__ import annotations

import pytest

import config
from synthetic import build_seed, build_workbook


@pytest.fixture
def seed_dir(tmp_path, monkeypatch):
    """A synthetic seed, installed as ``config.SEED_DIR`` for the duration of the test."""
    directory = build_seed(tmp_path / "seed")
    monkeypatch.setattr(config, "SEED_DIR", directory)
    return directory


@pytest.fixture
def workbook_path(tmp_path):
    return build_workbook(tmp_path / "конduit.xlsx")


@pytest.fixture
def workbook(workbook_path):
    import openpyxl

    return openpyxl.load_workbook(workbook_path, data_only=True)


@pytest.fixture
def imported(connection, seed_dir, workbook):
    """A migrated database with the synthetic conduit already imported into it."""
    from tools.import_konduit import import_workbook

    counts = import_workbook(connection, workbook)
    return counts
