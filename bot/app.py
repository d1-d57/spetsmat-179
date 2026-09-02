"""The bot factory.

``build`` opens both databases and wires the services in.  ``__main__`` is
the only caller of ``build`` in production; tests bypass it and call
``build`` directly with substituted paths and a fake session.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

import bot.config_local as cfg
from bot.handlers import owner, registration, student, teacher
from bot.middleware import AuthMiddleware
from bot.routers import marking, room
from bot.routers import photo, voice
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
    SqliteWorkingTeachers,
)
from core.services.enrollment import EnrollmentService
from core.services.marking import MarkingService
from core.services.progress import ProgressService
from core.services.room import RoomService
from core.services.roster import RosterService
from core.services.spiski import SpiskiService
from core.services.svodka import SvodkaService

log = logging.getLogger(__name__)


# ===========================================================================
#  RECOGNITION, BUILT FROM THE ENVIRONMENT
# ===========================================================================
#
# The class of error this section exists to close: a dependency that is ALIVE IN THE
# TESTS AND DEAD IN BATTLE.  ``bot/routers/photo.py:346`` reads ``data.get("vision")``
# and answers «Разбор фото не настроен» when it is missing; the word ``vision`` appeared
# nowhere in this file and only in ``tests/photo/conftest.py``, where a fixture supplies
# it.  P7 passed 18 gates out of 18 with the screen unreachable in production.
#
# Nothing secret lands in git here: the code holds the NAME of an environment variable
# and an empty default, never a value.

#: The environment variables that decide whether photo recognition is real.  The names
#: are the ones ``bot.env.example`` already carries; they are NOT in ``config.py``
#: because a key is a secret and that file is in git.
VISION_KEY_ENV = "LLM_API_KEY"
VISION_MODEL_ENV = "LLM_MODEL"
VISION_PROVIDER_ENV = "LLM_PROVIDER"

#: The OpenAI-compatible endpoint of each provider ``bot.env.example`` offers.  A
#: provider the map does not know turns recognition OFF and says so, rather than being
#: silently answered by whichever endpoint happens to be the default -- that silence is
#: the same class of failure this whole section is here to close.
VISION_ENDPOINTS = {
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    "openai": "https://api.openai.com/v1/chat/completions",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
}


def build_vision(environ: Optional[dict] = None) -> tuple:
    """``(vision | None, how)`` -- the recogniser this machine can actually offer.

    Shaped after ``infra.asr.build_transcriber`` on purpose: the second element is the
    sentence the starting process logs, so that «recognition is off» is never something a
    reader has to infer from the absence of a line.

    **No key configured means ``None``, not a crash.**  A bot without photo recognition is
    useful; a bot that refused to start would not be.  The screen already says «Разбор
    фото не настроен» for exactly this value.

    The model is built through P7's own constructor (``infra.llm.VisionModel``), which is
    read-only for this position; nothing here reimplements a line of it.
    """
    from infra.llm import DEFAULT_MODEL, VisionModel

    environ = os.environ if environ is None else environ
    key = (environ.get(VISION_KEY_ENV) or "").strip()
    model = (environ.get(VISION_MODEL_ENV) or "").strip() or DEFAULT_MODEL
    provider = (environ.get(VISION_PROVIDER_ENV) or "").strip().lower() or "openrouter"

    if not key:
        return None, (
            "NO VISION: %s unset -- photographs will be refused, not guessed"
            % VISION_KEY_ENV
        )
    endpoint = VISION_ENDPOINTS.get(provider)
    if endpoint is None:
        return None, (
            "NO VISION: %s=%r is not one of %s -- photographs will be refused"
            % (VISION_PROVIDER_ENV, provider, ", ".join(sorted(VISION_ENDPOINTS)))
        )
    return (
        VisionModel(api_key=key, model=model, endpoint=endpoint),
        "vision on: provider %s, model %s" % (provider, model),
    )


def build(
    *,
    token: str,
    owner_tg_id: int,
    journal_path,
    roster_path,
    bot: Optional[Bot] = None,
    storage: Optional[MemoryStorage] = None,
    environ: Optional[dict] = None,
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

    # P7's photograph screen and P8's voice screen.  Both were written, both passed their
    # gates, and NEITHER was reachable: no line here included them, so a photograph and a
    # voice note matched no handler at all and the user watched nothing happen.  Their
    # position in this list is load-bearing for the same reason P5's is -- included after
    # the catch-all below, every button of theirs would answer «экран устарел»
    # (``tests/photo/conftest.py`` moves its router here by hand for exactly that reason).
    photo_router, = photo.build_routers()
    dp.include_router(photo_router)
    dp.include_router(voice.build_router())

    # P14's after-lesson notifications.  It contributes ONE callback -- the teacher's
    # answer to «вы были на занятии?» -- and, like everything else here, must stand before
    # the catch-all or that answer would come back as «экран устарел».  The SENDING half
    # of this position is not a handler at all: it is `uvedomlenia.send_after_lesson`,
    # called with the id of a lesson that has closed, and when to call it is P10's
    # question.
    #
    # RESOLVED BY UNION, NOT BY CHOOSING A SIDE.  P7/P8 and P14 each ADDED their own
    # include here in parallel, and both are right: dropping either one leaves a router
    # that nothing reaches, which is the exact defect the block above says P7 and P8
    # already shipped once.
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
        # Who teaches on a given lesson day, read out of ``enrollment``.  Without it the
        # after-lesson question goes to every row of the ``teachers`` table; with it, only
        # to the people who work that weekday.  An unpopulated table falls back to the
        # wider set rather than to nobody.
        roll=SqliteWorkingTeachers(repo._journal),  # noqa: SLF001
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

    # The two recognisers, from the environment.  They go in through the SAME door as
    # everything above, because that door is the one aiogram resolves a handler's
    # arguments from: ``vision`` is read as ``data.get("vision")`` by the photo screen,
    # and ``transcriber`` / ``download`` / ``schema_extractor`` are declared by name in
    # the signature of ``voice.on_voice``.  Missing, the first answers «не настроен» and
    # the second raises before it says anything at all.
    vision, vision_note = build_vision(environ)
    dp.workflow_data["vision"] = vision
    dp.workflow_data["vision_note"] = vision_note
    dp.workflow_data.update(voice.voice_dependencies(catalogue, environ=environ))

    # Logged rather than silent, and the reason is measured in ``infra/asr.py``: a fake
    # recogniser that installs itself in silence answers every dictation with the same
    # canned line and looks exactly like a working bot.  The same is true of a vision
    # client that is ``None``.
    log.info("%s", vision_note)
    log.info("%s", dp.workflow_data["asr_note"])

    return dp


def _current_sheet_id(catalogue: SqliteCatalogue) -> int:
    sheets = catalogue.sheets()
    if not sheets:
        raise RuntimeError(
            "no sheets in the catalogue; refuse to register a student against NULL"
        )
    return max(sheets, key=lambda s: s.ord).id