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
from bot.routers import marking
from infra.db import SystemClock
from infra.repositories import SqliteCatalogue, SqliteMarkJournal
from infra.roster_repo import RosterRepo
from core.services.marking import MarkingService
from core.services.progress import ProgressService
from core.services.roster import RosterService


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

    # LAST, and the order is load-bearing rather than tidy: this catch-all claims every
    # callback query no router above it matched.  Included any earlier it would swallow
    # the screens below it; left out entirely, a button from a message older than the
    # payload schema matches nothing, aiogram drops the update, and the user watches a
    # spinner turn with not one line in the log.
    dp.include_router(stale_router)

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