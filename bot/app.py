"""The bot factory.

``build`` opens both databases and wires the services in.  ``__main__`` is
the only caller of ``build`` in production; tests bypass it and call
``build`` directly with substituted paths and a fake session.
"""

from __future__ import annotations

from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

import bot.config_local as cfg
from bot.handlers import owner, registration, student, teacher
from bot.middleware import AuthMiddleware
from bot.routers import marking, room
from bot.routers import uvedomlenia
from bot.routers import views
from infra.db import SystemClock
from infra.enrollment_repo import SqliteEnrollmentRepo
from infra.repositories import SqliteCatalogue, SqliteMarkJournal
from infra.room_repo import (
    SqliteAttendance,
    SqliteRoomRoster,
    SqliteSessions,
    SqliteTeachers,
)
from infra.roster_repo import RosterRepo
from infra.sessions_repo import SqliteSessionBook
from infra.uvedomlenia_repo import (
    SqliteHeadsOfRooms,
    SqliteNotifiableTeachers,
    SqliteSentLog,
    SqliteTeacherAttendance,
)
from core.services.enrollment import EnrollmentService
from core.services.marking import MarkingService
from core.services.progress import ProgressService
from core.services.room import RoomService
from core.services.roster import RosterService
from core.services.spiski import SpiskiService
from core.services.svodka import SvodkaService


def build(
    *,
    token: str,
    owner_tg_id: int,
    journal_path,
    roster_path,
    bot: Optional[Bot] = None,
    storage: Optional[MemoryStorage] = None,
) -> Dispatcher:
    """Build the dispatcher with the middleware and handlers wired in.

    ``bot`` and ``storage`` are injectable so tests can substitute a fake
    session (the brief: handlers are tested through ``dp.feed_raw_update``).
    """
    bot = bot or Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=None),
    )
    storage = storage or MemoryStorage()
    dp = Dispatcher(storage=storage)

    # The two stores and the seam over them.
    repo = RosterRepo.open(journal_path=journal_path, roster_path=roster_path)
    catalogue = SqliteCatalogue(repo._journal)  # noqa: SLF001  -- shared journal connection
    roster = RosterService(repo, sheets_for_current=lambda: _current_sheet_id(catalogue))

    # P4's two seams over the same journal connection: the grid writes through
    # ``MarkingService`` and reads through ``ProgressService``, and reimplements
    # neither.  Nothing under ``bot/`` opens a connection by hand.
    journal = SqliteMarkJournal(repo._journal)  # noqa: SLF001  -- shared journal connection
    marking_service = MarkingService(journal, SystemClock())
    progress_service = ProgressService(journal, catalogue)

    # P13's room screen.  It ASKS P1 for debts and P12 for the standing arrangement and
    # recomputes neither; the today-only row it writes goes into ``attendance``, which is
    # already keyed per session, so a move for tonight cannot reach an enrollment
    # interval.  Every port comes from the same journal connection the grid uses.
    room_service = RoomService(
        catalogue=catalogue,
        enrollment=EnrollmentService(SqliteEnrollmentRepo(repo._journal)),  # noqa: SLF001
        progress=progress_service,
        attendance=SqliteAttendance(repo._journal),  # noqa: SLF001
        sessions=SqliteSessions(repo._journal),  # noqa: SLF001
        teachers=SqliteTeachers(repo._journal),  # noqa: SLF001
        # The room of a teacher lives in the ROSTER store, not the journal: see the
        # docstring of infra/roster_repo.py.  It is what tells the screen which teachers a
        # child may be handed to, including one who happens to hold nobody tonight.
        roster=SqliteRoomRoster(repo._roster),  # noqa: SLF001
        clock=SystemClock(),
    )

    # Single outer middleware stamps ``identity`` onto every update.
    dp.message.middleware(AuthMiddleware(roster, owner_tg_id=owner_tg_id))
    dp.callback_query.middleware(AuthMiddleware(roster, owner_tg_id=owner_tg_id))

    # Routers in order: registration first (it owns /start), then owner
    # moderation, then the role-restricted screens.
    dp.include_router(registration.router)
    dp.include_router(owner.router)
    dp.include_router(student.router)
    dp.include_router(teacher.router)
    grid_router, stale_router = marking.build_routers()
    dp.include_router(grid_router)
    # The head's room screen.  Its own payload prefixes, so it claims only its own
    # buttons; included before the catch-all for the same reason everything else is.
    dp.include_router(room.build_router())

    # P5's viewing screens, and the position in this list is load-bearing: they must come
    # BEFORE the catch-all below, which claims every callback nobody above it matched.
    # Included after it, every view button would answer «экран устарел».
    dp.include_router(views.build_router())

    # P14's after-lesson notifications.  It contributes ONE callback -- the teacher's
    # answer to «вы были на занятии?» -- and, like everything else here, must stand before
    # the catch-all or that answer would come back as «экран устарел».  The SENDING half
    # of this position is not a handler at all: it is `uvedomlenia.send_after_lesson`,
    # called with the id of a lesson that has closed, and when to call it is P10's
    # question.
    dp.include_router(uvedomlenia.build_router())

    # LAST, and the order is load-bearing rather than tidy: this catch-all claims every
    # callback query no router above it matched.  Included any earlier it would swallow
    # the screens below it; left out entirely, a button from a message older than the
    # payload schema matches nothing, aiogram drops the update, and the user watches a
    # spinner turn with not one line in the log.
    dp.include_router(stale_router)

    # P5's lists, built once so that P14's notifications read the SAME projection the
    # screens do rather than a second one built beside it.
    spiski_service = SpiskiService(journal, catalogue, progress_service)

    # P14's after-lesson notifications.  Every store it writes lives in the journal except
    # the head of a room, which `infra/roster_repo.py` keeps in the roster file; the two
    # connections are the ones already open above and nothing here opens a third.
    svodka_service = SvodkaService(
        lessons=SqliteSessionBook(repo._journal),  # noqa: SLF001  -- shared journal connection
        spiski=spiski_service,
        journal=journal,
        catalogue=catalogue,
        teachers=SqliteNotifiableTeachers(repo._journal),  # noqa: SLF001
        heads=SqliteHeadsOfRooms(repo._roster),  # noqa: SLF001
        sent_log=SqliteSentLog(repo._journal),  # noqa: SLF001
        teacher_attendance=SqliteTeacherAttendance(repo._journal),  # noqa: SLF001
        clock=SystemClock(),
    )

    # Stash the service so handlers that need it get it through DI -- the
    # ``roster`` argument they declare is resolved by aiogram because the
    # dispatcher looks for a callable named ``roster`` on the dispatcher or
    # on ``workflow_data``.  Setting it here is the canonical way.
    dp.workflow_data.update(
        {
            "roster": roster,
            "catalogue": catalogue,
            "marking": marking_service,
            "progress": progress_service,
            "spiski": spiski_service,
            # The handler declares an argument named ``svodka``; aiogram resolves it from
            # here, the same way every other service on this dispatcher is resolved.
            "svodka": svodka_service,
            "room_service": room_service,
            "owner_tg_id": owner_tg_id,
        }
    )

    return dp


def _current_sheet_id(catalogue: SqliteCatalogue) -> int:
    sheets = catalogue.sheets()
    if not sheets:
        raise RuntimeError(
            "no sheets in the catalogue; refuse to register a student against NULL"
        )
    return max(sheets, key=lambda s: s.ord).id