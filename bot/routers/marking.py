"""The conveyor: open a student, tap the problems handed in, tap «Готово», next student.

Five to fifteen seconds in the seam between two students, and no navigation inside that
seam.  Everything in this module exists to protect that number.

FOUR FAILURES THAT LOOK LIKE «THE BOT IS BROKEN», AND WHERE EACH IS CLOSED HERE
--------------------------------------------------------------------------------

1. **Double tap.**  Closed in ``bot/callbacks.py`` and in ``MarkingService.set_state``,
   not here: the payload names the TARGET state, so two identical taps ask for the same
   world twice and the second one writes nothing.  On top of that every tap carries an
   idempotency key derived from ``callback_query.id``, which closes the other half --
   Telegram delivers at least once, and a REDELIVERED update is the same tap arriving
   twice with no human involved.  ``tests/grid/test_conveyor.py`` proves both.

2. **The spinner.**  ``answer()`` runs BEFORE the redraw, always.  The redraw is an API
   round-trip; the callback query expires in fifteen seconds, and a silent update with no
   toast is forbidden outright -- at 800 ms a person cannot tell whether the tap counted
   and taps again.  The order is not a convention here, it is asserted by a test that
   reads the sequence of outbound calls.

3. **``message is not modified``.**  Suppressed BY SUBSTRING, in one helper, and never by
   swallowing ``TelegramBadRequest`` as a whole: that exception is also how a deleted
   message, a bad payload and an expired query arrive, and swallowing it hides every API
   failure this screen can have.

4. **A stale button from history.**  After the payload schema changes, a button from an
   old message matches no filter, aiogram drops the update, and the user watches an
   eternal spinner with not one line in the log.  The catch-all router is included LAST
   and answers everything nobody claimed: «экран устарел», then a redraw of the list.

THE PRIVACY BOUNDARY.  ``callback_data`` is client-side data, so a forged payload naming
a foreign ``student_id`` is a request the server actually receives.  It buys nothing here
because the decision never consults the id: ``_may_open`` refuses every identity that is
not a teacher, a head or the owner, and there is no branch a student can reach by
changing the number.  Surnames never enter a payload either, so an id in flight cannot be
read back into a name by whoever holds the message.
"""

from __future__ import annotations

from typing import Optional

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from bot.callbacks import OPS, OP_SOLVE, Done, Mark, Noop, OpenGrid, PickSheet, ids_are_storable
from bot.keyboards.grid import (
    grid_header,
    grid_keyboard,
    last_action_line,
    mark_toast,
    sheets_keyboard,
    students_keyboard,
)
from bot.middleware import require_role
from core.models import CellState, Problem, Sheet

#: Who may see and write on this screen.  A confirmed student is refused by the gate
#: itself -- the grid is a teacher's instrument, and P5 is where a student sees their own.
MARKING_ROLES = ("teacher", "head", "owner")

#: Where a mark written by this screen came from.  One of ``config.MARK_SOURCES``; photo,
#: voice and quick text (P7, P8, P15) will write their own value through the same service.
SOURCE = "кнопка"

#: The substring Telegram uses when the redraw would change nothing.  Matched inside the
#: message of ``TelegramBadRequest`` and nowhere else.
NOT_MODIFIED = "message is not modified"

#: The separator every ``CallbackData`` factory of this project packs with.  A payload
#: that does not contain it carries no fields, so it cannot be a screen payload from any
#: schema this bot has ever had -- see ``stale_screen`` for why the catch-all cares.
PAYLOAD_SEPARATOR = ":"


def build_routers() -> tuple:
    """Fresh ``(screen, catch_all)`` routers, built per dispatcher rather than once per
    process.

    A module-level ``router = Router()`` is the idiom, and it is the reason
    ``tests/bot/conftest.py`` has to reach into ``module.router._parent_router`` and null
    it before every build: a ``Router`` remembers the dispatcher it was attached to and
    refuses to be attached twice.  P3 paid that with a fixture; a second position paying
    it again would mean editing P3's conftest, i.e. two writers in one file.  A factory
    costs one line at the call site and removes the shared global that caused it.

    The catch-all comes back as a SEPARATE router because it has to be included LAST, and
    "last" is a property of the include order in ``bot/app.build`` -- it cannot be
    expressed inside a router that also holds the screen's own handlers.
    """
    screen = Router(name="marking")
    screen.message.middleware(require_role(*MARKING_ROLES))
    screen.callback_query.middleware(require_role(*MARKING_ROLES))
    screen.message.register(open_list, F.text == "/setka")
    screen.callback_query.register(open_grid, OpenGrid.filter())
    screen.callback_query.register(set_mark, Mark.filter())
    screen.callback_query.register(done, Done.filter())
    screen.callback_query.register(pick_sheet, PickSheet.filter())
    screen.callback_query.register(filler, Noop.filter())

    # No role gate on the catch-all: a stale button must be answered for whoever holds
    # it, or the spinner never stops.  What it may REDRAW is gated inside the handler.
    catch_all = Router(name="stale-callbacks")
    catch_all.callback_query.register(stale_screen)
    return screen, catch_all


# ----------------------------------------------------------------- the privacy gate

def _may_open(identity) -> bool:
    """May this identity look at, and write on, a grid?

    A teacher, a head and the owner may.  A confirmed student may reach nothing here --
    not even their own row: this screen WRITES marks, and P5 is the read-only screen.

    THIS IS WHY A FORGED ``student_id`` BUYS NOTHING.  ``callback_data`` is client-side
    data, so a payload naming somebody else's id is a request the server really receives;
    the answer is that the decision does not consult the id at all.  A rule of the form
    "refuse when the id is not yours" would have to be right on every handler and would
    be one forgotten call away from leaking; a rule of the form "students do not reach
    this screen" cannot be forged, because there is nothing in the payload to forge.
    The check is a function rather than four inlined copies so that the forged-payload
    test has one thing to aim at.
    """
    if identity is None:
        return False
    return identity.kind in MARKING_ROLES


async def _refuse_as_stale(query: CallbackQuery) -> None:
    """The answer to a payload that parsed but cannot mean anything.

    Two shapes reach this, and both are «a button from a schema the server does not
    have» rather than «a button whose row is gone»: an ``op`` outside ``OPS``, and an id
    outside what the store can hold.  Both used to be worse than the stale button this
    screen was built to fix -- one silently STRUCK a mark, the other raised inside a
    query before anything had answered, leaving the spinner turning.
    """
    await query.answer("Экран устарел — откройте сетку заново.", show_alert=True)


def _editable(query: CallbackQuery) -> Optional[Message]:
    """The message to redraw, or ``None`` when Telegram gave us one we cannot edit.

    A callback can arrive attached to an ``InaccessibleMessage`` -- too old, or from a
    chat the bot was re-added to.  It has no ``edit_text``, and reaching for it is an
    ``AttributeError`` inside a handler, i.e. a spinner that never stops.
    """
    message = query.message
    return message if isinstance(message, Message) else None


def _teacher_id(identity) -> Optional[int]:
    """Which teacher gets written into the journal row.  ``None`` for the owner, who has
    no teacher binding -- the mark is still theirs to make, and the column is nullable."""
    teacher = getattr(identity, "teacher", None)
    return teacher.teacher_id if teacher is not None else None


# ------------------------------------------------------------------- catalogue reads

def _current_sheet(catalogue) -> Optional[Sheet]:
    """The sheet being worked on now: the largest ``ord``.  ``None`` on an empty
    catalogue, which is a real state before the importer has ever run."""
    sheets = catalogue.sheets()
    return max(sheets, key=lambda sheet: sheet.ord) if sheets else None


def _find_problem(catalogue, problem_id: int) -> Optional[Problem]:
    """The problem one payload names.

    ``Catalogue`` has ``problems_of_sheet`` and ``problems_between`` but no
    ``problem(problem_id)``, so this walks the whole ord range and filters.  It is a read
    of a few hundred rows out of SQLite on the same connection, which is cheap enough for
    a tap -- but it is a seam missing from ``core/``, not a thing that belongs in a
    router, and it is named as such in ``## ВОПРОСЫ`` rather than quietly normalised.
    """
    sheets = catalogue.sheets()
    if not sheets:
        return None
    first, last = sheets[0].ord, sheets[-1].ord
    for problem in catalogue.problems_between(first, last):
        if problem.id == problem_id:
            return problem
    return None


def _active_students(catalogue) -> list:
    """The students on the belt, in the order the list and the arrows both use.

    A student whose status is ``left`` stays in the catalogue -- the journal points at
    their rows and always will -- but they are not somebody the teacher walks past on a
    Thursday, and leaving them in the conveyor costs a tap per lesson forever.  Filtered
    in ONE place so that the list and the arrows cannot disagree about what "next" means.
    """
    return [student for student in catalogue.students() if student.status != "left"]


def _neighbours(students: list, student_id: int) -> tuple:
    """The students on either side, in the order the teacher is looking at.

    Resolved HERE, while the keyboard is built, so that the arrows can carry the
    neighbour's id instead of a «next» the server would have to resolve later against a
    roster that may have changed.
    """
    ids = [student.id for student in students]
    if student_id not in ids:
        return None, None
    index = ids.index(student_id)
    previous = students[index - 1] if index > 0 else None
    following = students[index + 1] if index + 1 < len(students) else None
    return previous, following


# ------------------------------------------------------------------ drawing helpers

async def _redraw(message: Message, text: str, markup: InlineKeyboardMarkup) -> None:
    """Redraw the ONE message the teacher is working in, in place.

    The message lives for the whole work with a student; a new message per tap would
    push the grid off the screen and cost the teacher a scroll in the middle of the seam.

    ``message is not modified`` is matched as a SUBSTRING and swallowed; every other
    ``TelegramBadRequest`` is re-raised, because "the message was deleted", "the payload
    is too long" and "the query expired" arrive as the same exception type and must not
    be hidden by a bare ``except``.
    """
    try:
        await message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as error:
        if NOT_MODIFIED not in str(error).lower():
            raise


def _compose_grid(catalogue, progress, *, student_id: int, sheet_id: int, last: Optional[dict]):
    """Text and keyboard of one student's grid.  Pure apart from the catalogue reads."""
    student = catalogue.student(student_id)
    sheet = catalogue.sheet(sheet_id)
    problems = catalogue.problems_of_sheet(sheet_id)
    states = progress.states_for(student_id, [problem.id for problem in problems])

    lines = [grid_header(student, sheet, states)]
    if last is not None:
        lines.append(
            last_action_line(
                student=student,
                problem_label=last["label"],
                at_iso=last["at"],
                cleared=last["cleared"],
            )
        )
    previous_student, next_student = _neighbours(_active_students(catalogue), student_id)
    markup = grid_keyboard(
        problems,
        states,
        student_id=student_id,
        sheet_id=sheet_id,
        previous_student=previous_student,
        next_student=next_student,
    )
    return "\n".join(lines), markup


def _compose_list(catalogue, sheet_id: int):
    """The list «Готово» returns to.  A conveyor returns to the belt, not to a menu."""
    students = _active_students(catalogue)
    sheet = catalogue.sheet(sheet_id)
    text = "Листок %s · учеников %d" % (
        sheet.number if sheet is not None else "?",
        len(students),
    )
    return text, students_keyboard(students, sheet_id=sheet_id)


async def _last_mark(state: FSMContext, student_id: int) -> Optional[dict]:
    """The last action line, but only for the student it was made on.

    Kept in the FSM store rather than in the journal: it is a property of THIS teacher's
    screen, and two teachers working side by side must not see each other's last tap.
    """
    data = await state.get_data()
    last = data.get("last_mark")
    if last is None or last.get("student_id") != student_id:
        return None
    return last


# ------------------------------------------------------------------------ handlers

async def open_list(message: Message, catalogue) -> None:
    """The entry: the list of students on the current sheet."""
    sheet = _current_sheet(catalogue)
    if sheet is None:
        await message.answer("В каталоге ещё нет листков — сетку не на чем открыть.")
        return
    text, markup = _compose_list(catalogue, sheet.id)
    await message.answer(text, reply_markup=markup)


async def open_grid(
    query: CallbackQuery,
    callback_data: OpenGrid,
    identity,
    catalogue,
    progress,
    state: FSMContext,
) -> None:
    """Draw one student's grid, in place of whatever the message showed before."""
    if not _may_open(identity):
        await query.answer("Эта сетка не ваша.", show_alert=True)
        return
    if not ids_are_storable(callback_data.student_id, callback_data.sheet_id):
        await _refuse_as_stale(query)
        return
    if catalogue.student(callback_data.student_id) is None:
        await query.answer("Такого ученика нет.", show_alert=True)
        return

    await query.answer()
    message = _editable(query)
    if message is None:
        return
    text, markup = _compose_grid(
        catalogue,
        progress,
        student_id=callback_data.student_id,
        sheet_id=callback_data.sheet_id,
        last=await _last_mark(state, callback_data.student_id),
    )
    await _redraw(message, text, markup)


async def set_mark(
    query: CallbackQuery,
    callback_data: Mark,
    identity,
    catalogue,
    marking,
    progress,
    state: FSMContext,
) -> None:
    """One tap on one cell.

    THE ORDER OF THE THREE BEATS IS THE POINT, and it is asserted by a test rather than
    left to whoever edits this next:

      1. write -- a local SQLite transaction, microseconds, and it is what the toast has
         to be truthful about;
      2. ``answer()`` -- the immediate toast, BEFORE any round-trip that can be slow;
      3. the redraw -- one ``editMessageText``, because the header count and the
         last-action line are part of the TEXT and go stale if only the markup is redrawn.
    """
    if not _may_open(identity):
        await query.answer("Эта сетка не ваша.", show_alert=True)
        return
    # BEFORE any catalogue read, and before the toast: an unknown ``op`` must not be
    # folded into "clear" (that would let a forged payload ERASE a mark), and an id wider
    # than the store must not reach a query (that would raise before anything answered).
    if callback_data.op not in OPS:
        await _refuse_as_stale(query)
        return
    if not ids_are_storable(callback_data.student_id, callback_data.task_id):
        await _refuse_as_stale(query)
        return

    problem = _find_problem(catalogue, callback_data.task_id)
    if problem is None:
        await query.answer("Экран устарел: такой задачи нет.", show_alert=True)
        return
    student = catalogue.student(callback_data.student_id)
    if student is None:
        await query.answer("Такого ученика нет.", show_alert=True)
        return

    target = CellState.SOLVED if callback_data.op == OP_SOLVE else CellState.EMPTY
    outcome = marking.set_state(
        callback_data.student_id,
        callback_data.task_id,
        target,
        source=SOURCE,
        teacher_id=_teacher_id(identity),
        # The query id is unique per delivered callback, so a REDELIVERY carries the same
        # key and is answered from the journal instead of being written twice.  Two
        # different taps on the same target get different keys and are stopped one layer
        # further in, by the target-state rule itself.
        idempotency_key="cb:%s" % query.id,
    )

    cleared = target is CellState.EMPTY
    await query.answer(mark_toast(problem.label, student, cleared=cleared))

    at_iso = outcome.mark.recorded_at if outcome.mark is not None else None
    if at_iso is not None:
        await state.update_data(
            last_mark={
                "student_id": callback_data.student_id,
                "problem_id": problem.id,
                "label": problem.label,
                "at": at_iso,
                "cleared": cleared,
            }
        )

    message = _editable(query)
    if message is None:
        return
    text, markup = _compose_grid(
        catalogue,
        progress,
        student_id=callback_data.student_id,
        sheet_id=problem.sheet_id,
        last=await _last_mark(state, callback_data.student_id),
    )
    await _redraw(message, text, markup)


async def done(query: CallbackQuery, callback_data: Done, catalogue) -> None:
    """«Готово» — back to the LIST of students, never to a menu.  It is a conveyor."""
    if not ids_are_storable(callback_data.sheet_id):
        await _refuse_as_stale(query)
        return
    await query.answer()
    message = _editable(query)
    if message is not None:
        text, markup = _compose_list(catalogue, callback_data.sheet_id)
        await _redraw(message, text, markup)


async def pick_sheet(
    query: CallbackQuery, callback_data: PickSheet, identity, catalogue
) -> None:
    """«Другой листок» — the one place this screen has a second level, and it is one tap
    deep by design: an extra level of navigation costs a full cycle of the seam."""
    if not _may_open(identity):
        await query.answer("Эта сетка не ваша.", show_alert=True)
        return
    if not ids_are_storable(callback_data.student_id):
        await _refuse_as_stale(query)
        return
    await query.answer()
    message = _editable(query)
    if message is None:
        return
    student = catalogue.student(callback_data.student_id)
    text = "%s · какой листок?" % (
        ("%s %s" % (student.surname, student.name)).strip() if student else "ученик"
    )
    await _redraw(
        message,
        text,
        sheets_keyboard(catalogue.sheets(), student_id=callback_data.student_id),
    )


async def filler(query: CallbackQuery) -> None:
    """A tap on the padding of the last row.  Dismiss the spinner, change nothing.

    It has a handler precisely so that it is NOT a stale button: an unclaimed payload
    would fall through to ``stale_router`` and tell the teacher their screen is out of
    date, which would be a lie about the row they are looking at.
    """
    await query.answer()


async def stale_screen(query: CallbackQuery, identity, catalogue) -> None:
    """Everything nobody claimed: a button from a message older than the payload schema.

    Included LAST.  Without it aiogram drops the update silently -- no handler, no log
    line, and a spinner that turns until Telegram gives up.  With it the user gets a
    sentence and, when a redraw is the right answer, a working screen in the same tap.

    THREE CONDITIONS ON THE REDRAW, and the answer is under none of them.

    * The ANSWER is unconditional.  A stranger holding a forwarded button must still get
      their spinner stopped; that is the whole failure this handler exists to close.
    * The redraw is gated by role, so stopping a stranger's spinner does not hand them
      the roster.
    * The redraw needs a payload that CARRIES FIELDS.  Every schema this project has ever
      packed uses ``prefix:field:field``; a bare token with no separator is a decoration
      -- a label button drawn to be looked at rather than tapped -- and it belongs to
      whatever screen is currently on the display.  Redrawing over it would replace a
      live screen of somebody else's with this one, which is a worse failure than the
      spinner: ``bot/handlers/owner.py`` really does draw ``callback_data="noop"`` on
      every pending row, and without this condition an owner who taps a name loses their
      moderation list.  (That button having no handler at all is P3's defect and is
      reported rather than fixed from here; this handler only refuses to make it worse.)
    """
    await query.answer("Экран устарел — открыт заново.", show_alert=True)
    message = _editable(query)
    if not _may_open(identity) or message is None:
        return
    if PAYLOAD_SEPARATOR not in (query.data or ""):
        return
    sheet = _current_sheet(catalogue)
    if sheet is None:
        return
    text, markup = _compose_list(catalogue, sheet.id)
    await _redraw(message, text, markup)
