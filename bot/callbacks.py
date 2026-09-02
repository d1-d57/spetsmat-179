"""Every ``callback_data`` payload of the bot, and nothing else.

TWO LAWS SHAPE THIS FILE.

**A payload carries the TARGET STATE, never an operation to apply to whatever the
server finds.**  ``Mark`` names the state the cell must end up in; the navigation
buttons name the NEIGHBOUR'S id rather than a ``+1`` to add to something the server
looks up.  This is what makes a double tap harmless by construction: two identical
payloads arriving in either order leave the same cell state, so the whole subject of
races disappears instead of being defended against.

**Only numbers go into a payload.  Not one string typed by a human.**  Two independent
reasons, both measured on this project's own seed rather than imagined:

  * the separator is ``:``, and ``seed/sheets.json`` contains the problem label
    ``10а:)`` -- packing it would raise ``ValueError`` at the moment the keyboard is
    built, i.e. for one particular sheet out of eighteen, in production;
  * Telegram counts ``callback_data`` in BYTES, capped at 64, and a Cyrillic character
    costs two of them.  A surname in the payload would also be a surname leaving the
    server, which §5 of the brief forbids outright.

``tests/grid/test_payloads.py`` proves the bound over all 18 seed sheets and all 544
problems, and prints the coverage it reached.
"""

from __future__ import annotations

from aiogram.filters.callback_data import CallbackData

#: Telegram's hard limit on ``callback_data``, in BYTES of UTF-8.  Not a style rule and
#: not ours to raise: the Bot API rejects the whole ``sendMessage`` above it.
CALLBACK_DATA_LIMIT_BYTES = 64

#: The two target states a grid button can name.  Deliberately NOT the three states of
#: ``CellState``: ``retract`` ("handed in, did not defend") is a different fact about the
#: world, it needs an event standing to reverse, and binding it to a bare two-state
#: button would make a repeated tap raise instead of doing nothing.  The router maps
#: these onto ``CellState`` -- the payload stays an integer, because an enum's *value*
#: would be a human-typed string again.
OP_CLEAR = 0
OP_SOLVE = 1

#: The only two values ``Mark.op`` may carry.  Anything else is a payload from a schema
#: this bot does not have, and it must be REFUSED rather than folded into one of the two:
#: ``op`` is typed ``int`` because a payload is numbers, and an ``int`` field accepts
#: ``7`` and ``-3`` as readily as ``0``.
OPS = (OP_CLEAR, OP_SOLVE)

#: SQLite stores an INTEGER in 64 bits and raises ``OverflowError`` on anything wider --
#: from inside the query, i.e. after the handler has started and before it has answered.
#: Python integers have no such bound, so a payload of twenty digits fits the 64 BYTES,
#: unpacks cleanly, passes every type check, and then explodes at the database.  The
#: bound belongs here, beside the payloads, because it is a property of what an id CAN
#: be rather than of any one screen.
ID_MAX = 2 ** 63 - 1
ID_MIN = -ID_MAX - 1


def ids_are_storable(*values: int) -> bool:
    """Can every one of these ids reach the database at all?

    False means the payload cannot name a real row and never could: the honest answer is
    that the screen is out of date, not a traceback halfway through a query.
    """
    return all(ID_MIN <= value <= ID_MAX for value in values)


class Mark(CallbackData, prefix="m"):
    """One tap on one problem of one student's grid: ``m:56:600:1``.

    ``op`` is the TARGET, not a toggle: ``1`` means "this cell must end up solved" and
    ``0`` means "this cell must end up empty".  Tapping the same button twice therefore
    asks for the same world twice, and the second ask writes nothing.
    """

    student_id: int
    task_id: int
    op: int


class OpenGrid(CallbackData, prefix="g"):
    """Draw the grid of this student over this sheet: ``g:56:12``.

    Used by the student list, by the sheet chooser and by both navigation arrows.  The
    arrows carry the NEIGHBOUR'S id -- computed when the keyboard was built, from the
    order the teacher was looking at -- so a stale screen cannot walk the roster from a
    position that no longer exists.
    """

    student_id: int
    sheet_id: int


class Done(CallbackData, prefix="d"):
    """«Готово»: back to the list of students, on this sheet: ``d:12``.

    Back to the LIST, never to a menu.  It is a conveyor: the next student is one tap
    away, and the sheet the teacher was working on is remembered by the payload rather
    than by server-side state that a second teacher would share.
    """

    sheet_id: int


class PickSheet(CallbackData, prefix="s"):
    """«Другой листок»: offer the sheet chooser for this student: ``s:56``."""

    student_id: int


class Noop(CallbackData, prefix="x"):
    """A filler cell in the last row of a grid whose problem count is not a multiple of
    ``config.GRID_COLUMNS``.

    It exists so that every row is exactly as wide as every other row: Telegram stretches
    a short row's buttons to the full width, and a last row of three WIDER buttons breaks
    the thumb-target geometry that the four-column rule exists to protect.  Tapping one
    dismisses the spinner and changes nothing -- which is why it is a real payload with a
    real handler and not a silently unhandled string.
    """


def payload_fits(data: str) -> bool:
    """Does this rendered payload fit Telegram's limit?  Bytes, never characters."""
    return len(data.encode("utf-8")) <= CALLBACK_DATA_LIMIT_BYTES
