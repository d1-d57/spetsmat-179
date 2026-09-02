"""The screens you LOOK at.  Nothing here writes a mark, and nothing here counts.

P1 computes the grid, the debts and the graveyard; ``core/services/spiski.py`` shapes them
into lists.  This module draws them and decides who may see what.  A second, diverging way
to count the same thing is exactly the class of bug P1 closed with a differential test, so
there is no arithmetic in this file at all.

TWO READERS, TWO DIFFERENT SCREENS, AND THE DIFFERENCE IS THE WHOLE POSITION.

* the student: their own year, sheet by sheet, and a SHORT list of what is owed;
* the teacher: FIRST the two lists -- who has said nothing, and which problems nobody
  took -- and the table of everybody against everything only SECOND.

THE PRIVACY BOUNDARY, AND IT IS CHECKED ON THE SERVER RATHER THAN DECLARED.

``callback_data`` is client-side data.  A payload naming somebody else's ``student_id``,
typed out by hand from a screenshot of a button, is a request this server really receives
-- the fact that no such button was ever drawn is not a defence.  Two independent carriers
answer it, and either one alone would be enough:

1. **The refusal.**  Every student handler compares the id in the payload with the id the
   middleware resolved from the Telegram account, and refuses the moment they differ.
   Refusing rather than silently serving the right data is deliberate: a forgery is worth
   seeing, and a screen that quietly answered the wrong question would be indistinguishable
   from a working one.
2. **The read.**  Every read below is made with ``identity.student_id`` and never with the
   number out of the payload.  Delete carrier 1 and nothing leaks; the handler would simply
   redraw the caller's own screen.

The teacher's screens are gated by ROLE, in the same shape P4 uses: a confirmed student is
refused by the middleware and never reaches a handler, so there is nothing in those
payloads for a student to forge either.

WHY THIS ROUTER MUST BE INCLUDED BEFORE ``marking.stale_router``.  That catch-all claims
every callback query nobody above it matched, and answers «экран устарел».  Included after
it, every button on every screen in this file would tell its reader the screen is out of
date.  ``bot/app.build`` puts it between the grid and the catch-all for that reason.
"""

from __future__ import annotations

from typing import Optional

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from bot.callbacks import ids_are_storable
from bot.keyboards.views import (
    ViewDebts,
    ViewLists,
    ViewSheet,
    ViewTable,
    ViewYear,
    debts_keyboard,
    debts_text,
    lists_keyboard,
    lists_text,
    own_sheet_keyboard,
    own_sheet_text,
    table_keyboard,
    table_text,
    year_keyboard,
    year_text,
)
from bot.middleware import require_role

#: Who may look at their own screens.  A pending student is refused by the gate itself:
#: the catalogue has no confirmed row for them, so there is no "own" to show.
STUDENT_ROLES = ("confirmed_student",)

#: Who may look at the two lists and the table.  Same set P4 gates the grid with -- a
#: student reaches none of it, which is why a forged payload there buys nothing either.
TEACHER_ROLES = ("teacher", "head", "owner")

#: The substring Telegram uses when a redraw would change nothing.  Matched inside the
#: message of ``TelegramBadRequest`` and nowhere else: that exception is also how a
#: deleted message, a bad payload and an expired query arrive, and a bare ``except``
#: would hide every API failure these screens can have.
NOT_MODIFIED = "message is not modified"

#: Sent with the whole-class table and with nothing else.  The bot's default parse mode is
#: ``None``; the table is the one screen that needs a monospaced block to be readable.
TABLE_PARSE_MODE = "HTML"


def build_router() -> Router:
    """One router with two role-gated children, so ``bot/app.build`` gains one include.

    Built per dispatcher rather than kept as a module global: a ``Router`` remembers the
    dispatcher it was attached to and refuses to be attached twice, which is why P3's
    fixtures have to null ``router._parent_router`` before every build.  A factory costs
    one line at the call site and removes the shared global that caused it -- the same
    choice ``bot/routers/marking.build_routers`` made, and for the same reason.
    """
    root = Router(name="views")

    student = Router(name="views-student")
    student.message.middleware(require_role(*STUDENT_ROLES))
    student.callback_query.middleware(require_role(*STUDENT_ROLES))
    student.message.register(open_year, F.text == "/god")
    student.message.register(open_debts_command, F.text == "/dolgi")
    student.callback_query.register(open_year_callback, ViewYear.filter())
    student.callback_query.register(open_own_sheet, ViewSheet.filter())
    student.callback_query.register(open_debts, ViewDebts.filter())

    teacher = Router(name="views-teacher")
    teacher.message.middleware(require_role(*TEACHER_ROLES))
    teacher.callback_query.middleware(require_role(*TEACHER_ROLES))
    teacher.message.register(open_lists, F.text == "/spiski")
    teacher.callback_query.register(open_lists_callback, ViewLists.filter())
    teacher.callback_query.register(open_table, ViewTable.filter())

    root.include_router(student)
    root.include_router(teacher)
    return root


# ----------------------------------------------------------------- the privacy gate

def _own_student_id(identity, claimed: Optional[int] = None) -> Optional[int]:
    """The caller's OWN student id, or ``None`` when they may not have one.

    ``claimed`` is the id out of the payload.  It is compared and then thrown away: the
    return value is always the id the middleware resolved from the Telegram account, so a
    handler that used this function cannot read a foreign row even if the comparison were
    deleted tomorrow.

    A ``kind`` check stands here as well as in the router's middleware.  It is not
    redundant belt-and-braces: ``Identity.student_id`` is ``None`` for every other kind,
    and returning it would turn a role slip into a query against ``student_id = None``
    instead of a refusal.
    """
    if identity is None or getattr(identity, "kind", None) not in STUDENT_ROLES:
        return None
    mine = getattr(identity, "student_id", None)
    if mine is None:
        return None
    if claimed is not None and claimed != mine:
        return None
    return mine


async def _refuse_foreign(query: CallbackQuery) -> None:
    """The answer to a payload that names somebody else.

    The same sentence P3's ``/peek`` refusal uses, on purpose: a person who probes two
    different screens must not be able to tell from the wording which one has a hole.
    """
    await query.answer("Вы видите только свои данные.", show_alert=True)


async def _refuse_as_stale(query: CallbackQuery) -> None:
    """A payload that parsed but cannot name a real row.

    An id outside what SQLite can hold reaches the database as an ``OverflowError`` from
    inside the query -- after the handler has started and before it has answered, which is
    a spinner that never stops.  The honest answer is that the screen is out of date.
    """
    await query.answer("Экран устарел — откройте экран заново.", show_alert=True)


def _editable(query: CallbackQuery) -> Optional[Message]:
    """The message to redraw, or ``None`` when Telegram gave us one we cannot edit.

    A callback can arrive attached to an ``InaccessibleMessage`` -- too old, or from a
    chat the bot was re-added to.  It has no ``edit_text``, and reaching for it is an
    ``AttributeError`` inside a handler.
    """
    message = query.message
    return message if isinstance(message, Message) else None


async def _redraw(
    message: Message,
    text: str,
    markup: InlineKeyboardMarkup,
    *,
    parse_mode: Optional[str] = None,
) -> None:
    """Redraw the one message the reader is looking at, in place.

    ``message is not modified`` is matched as a SUBSTRING and swallowed -- tapping «К году»
    from the year is a real thing a person does, and it must not raise.  Every other
    ``TelegramBadRequest`` is re-raised.
    """
    try:
        await message.edit_text(text, reply_markup=markup, parse_mode=parse_mode)
    except TelegramBadRequest as error:
        if NOT_MODIFIED not in str(error).lower():
            raise


# ------------------------------------------------------------- composing the screens

def _compose_year(spiski, catalogue, student_id: int):
    student = catalogue.student(student_id)
    rows = spiski.year(student_id)
    return year_text(student, rows), year_keyboard(rows, student_id=student_id)


def _compose_own_sheet(spiski, catalogue, student_id: int, sheet_id: int):
    student = catalogue.student(student_id)
    sheet = catalogue.sheet(sheet_id)
    problems, states = spiski.sheet_states(student_id, sheet_id)
    return (
        own_sheet_text(student, sheet, problems, states),
        own_sheet_keyboard(student_id=student_id),
    )


def _compose_debts(spiski, catalogue, student_id: int):
    student = catalogue.student(student_id)
    return (
        debts_text(student, spiski.debts(student_id)),
        debts_keyboard(student_id=student_id),
    )


def _compose_lists(spiski):
    """The teacher's first screen.  The table is reached from it, never instead of it."""
    return (
        lists_text(spiski.silent(), spiski.graveyard()),
        lists_keyboard(spiski.recent_sheets()),
    )


def _compose_table(spiski, catalogue, sheet_id: int):
    problems, students, states = spiski.sheet_table(sheet_id)
    return table_text(catalogue.sheet(sheet_id), problems, students, states), table_keyboard()


# ------------------------------------------------------------------ student handlers

async def open_year(message: Message, identity, spiski, catalogue) -> None:
    """«/god» — the whole year, which is what P2 loaded fifteen thousand events for."""
    student_id = _own_student_id(identity)
    if student_id is None:
        await message.answer("Вы видите только свои данные.")
        return
    text, markup = _compose_year(spiski, catalogue, student_id)
    await message.answer(text, reply_markup=markup)


async def open_debts_command(message: Message, identity, spiski, catalogue) -> None:
    """«/dolgi» — the short list, reachable without walking through the year first."""
    student_id = _own_student_id(identity)
    if student_id is None:
        await message.answer("Вы видите только свои данные.")
        return
    text, markup = _compose_debts(spiski, catalogue, student_id)
    await message.answer(text, reply_markup=markup)


async def open_year_callback(
    query: CallbackQuery, callback_data: ViewYear, identity, spiski, catalogue
) -> None:
    if not ids_are_storable(callback_data.student_id):
        await _refuse_as_stale(query)
        return
    student_id = _own_student_id(identity, callback_data.student_id)
    if student_id is None:
        await _refuse_foreign(query)
        return
    await query.answer()
    message = _editable(query)
    if message is None:
        return
    text, markup = _compose_year(spiski, catalogue, student_id)
    await _redraw(message, text, markup)


async def open_own_sheet(
    query: CallbackQuery, callback_data: ViewSheet, identity, spiski, catalogue
) -> None:
    if not ids_are_storable(callback_data.student_id, callback_data.sheet_id):
        await _refuse_as_stale(query)
        return
    student_id = _own_student_id(identity, callback_data.student_id)
    if student_id is None:
        await _refuse_foreign(query)
        return
    if catalogue.sheet(callback_data.sheet_id) is None:
        await query.answer("Такого листка нет.", show_alert=True)
        return
    await query.answer()
    message = _editable(query)
    if message is None:
        return
    text, markup = _compose_own_sheet(spiski, catalogue, student_id, callback_data.sheet_id)
    await _redraw(message, text, markup)


async def open_debts(
    query: CallbackQuery, callback_data: ViewDebts, identity, spiski, catalogue
) -> None:
    if not ids_are_storable(callback_data.student_id):
        await _refuse_as_stale(query)
        return
    student_id = _own_student_id(identity, callback_data.student_id)
    if student_id is None:
        await _refuse_foreign(query)
        return
    await query.answer()
    message = _editable(query)
    if message is None:
        return
    text, markup = _compose_debts(spiski, catalogue, student_id)
    await _redraw(message, text, markup)


# ------------------------------------------------------------------ teacher handlers

async def open_lists(message: Message, spiski) -> None:
    """«/spiski» — the FIRST screen, and its order is the position itself.

    The list of who has said nothing comes before the table because a table of everybody
    against everything shows the teacher what the teacher already sees.  Without a record,
    a teacher simply does not know whom they have not talked to.
    """
    text, markup = _compose_lists(spiski)
    await message.answer(text, reply_markup=markup)


async def open_lists_callback(query: CallbackQuery, spiski) -> None:
    await query.answer()
    message = _editable(query)
    if message is None:
        return
    text, markup = _compose_lists(spiski)
    await _redraw(message, text, markup)


async def open_table(
    query: CallbackQuery, callback_data: ViewTable, spiski, catalogue
) -> None:
    """The table of one sheet — the SECOND screen, reached from the lists."""
    if not ids_are_storable(callback_data.sheet_id):
        await _refuse_as_stale(query)
        return
    if catalogue.sheet(callback_data.sheet_id) is None:
        await query.answer("Такого листка нет.", show_alert=True)
        return
    await query.answer()
    message = _editable(query)
    if message is None:
        return
    text, markup = _compose_table(spiski, catalogue, callback_data.sheet_id)
    await _redraw(message, text, markup, parse_mode=TABLE_PARSE_MODE)
