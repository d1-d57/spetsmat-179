"""Keyboards: the only place in the bot that builds an ``InlineKeyboardMarkup``.

A keyboard is a pure function of what it shows -- a list of problems, a list of states, a
list of students -- and knows nothing about the journal, the dispatcher or the update
that asked for it.  That is what lets ``tests/grid/`` walk all eighteen seed sheets
through the real builder without a database, a Telegram token or an event loop.
"""

from bot.keyboards.grid import (
    grid_header,
    grid_keyboard,
    last_action_line,
    mark_toast,
    sheets_keyboard,
    students_keyboard,
)

__all__ = [
    "grid_header",
    "grid_keyboard",
    "last_action_line",
    "mark_toast",
    "sheets_keyboard",
    "students_keyboard",
]
