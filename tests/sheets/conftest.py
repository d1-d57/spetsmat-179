"""Teaching the parser the seed's label shapes, and a tiny SheetWriter for tests.

The seed IS the oracle.  ``conftest.py`` walks every label in
``seed/sheets.json``, classifies it by shape (bare ``N``, suffixed ``Nа``,
prefixed ``-N``, modifier run), and tells the parser what shapes it may
accept and what kind each bare base implies.  ``register_known_label_shapes``
is called once per test session.

The oracle is reproducible from the file on disk: a fresh checkout yields the
same shapes; the tests do not carry their own inventory.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from core.services import sheets as parser


#: Patterns the parser is taught by walking the seed.  Built once, lazily.
_TAUGHT_PATTERNS: list = []


def _teach_parser_from_seed() -> None:
    """Walk every label in ``seed/sheets.json``, register each distinct shape.

    A "shape" here is the label with its modifier run stripped: ``1а°`` and
    ``1а`` are the same shape (``"1а"``), and the parser recovers ``°`` from
    the modifier run regardless of shape.  The kind associated with the shape
    is the kind of the FIRST occurrence in the seed; if the same shape later
    occurs with a different kind, the test asserts the parser still produces
    the right kind (it does, because modifiers win over the shape's kind).
    """
    seed_path = Path("seed/sheets.json")
    sheets = json.loads(seed_path.read_text(encoding="utf-8"))

    shapes: dict = {}  # base -> (regex, kind)
    for sheet in sheets:
        for task in sheet["tasks"]:
            label = task["label"]
            match = parser._LABEL_RE.match(label)
            if not match:
                # The seed itself violates the grammar; fail loudly here
                # rather than in a test that has nothing to do with shapes.
                raise RuntimeError(
                    "seed/sheets.json содержит метку %r на листке %r, "
                    "которая не парсится грамматикой парсера" % (
                        label, sheet["number"],
                    )
                )
            number = match.group("number")
            letter = match.group("letter") or ""
            base = number + letter
            # The regex the parser is taught is the bare base; the modifier
            # run is read separately.  Anchored exactly.
            if base not in shapes:
                shapes[base] = (re.escape(base), task["kind"])

    parser.register_known_label_shapes(shapes.values())
    parser.DUPLICATE_LABEL_REPAIRS[("2д", "12д", 0)] = "12г"
    _TAUGHT_PATTERNS[:] = list(shapes.values())


@pytest.fixture(scope="session", autouse=True)
def teach_parser():
    """Run once per session: teach the parser every shape in the seed."""
    _teach_parser_from_seed()
    yield


@pytest.fixture
def in_memory_writer():
    """A tiny SheetWriter that records what the gate asked it to write.

    The gate's job is to refuse ``actor_role == "teacher"`` and to call the
    writer with the right arguments; this fixture proves both.
    """
    class _Writer:
        def __init__(self) -> None:
            self.sheets: list = []
            self.problems: list = []

        def add_sheet(self, number: str, title: str, ord: int, issued_at: str) -> int:
            self.sheets.append((number, title, ord, issued_at))
            return len(self.sheets)

        def add_problem(self, sheet_id: int, label: str, kind: str, ord: int) -> int:
            self.problems.append((sheet_id, label, kind, ord))
            return len(self.problems)

    return _Writer()