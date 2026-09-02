"""THE GATE ON THE CLASS: every dependency a handler asks for is one ``build`` supplies.

Not a test that ``vision`` is wired.  That test is green forever the day after it is
written, and the next ``data.get("что-то")`` reopens exactly the hole it was written for.
This gate derives BOTH sides and fails on their difference:

  asked for   -- from the syntax tree of ``bot/**`` (``tests/klyuchi/dependency_scan.py``)
  supplied    -- from a dispatcher that ``bot.app.build`` actually built
  and by aiogram -- MEASURED, by feeding a real update through a bare dispatcher and
                    reading the keys a handler receives, rather than by a list that would
                    quietly rot on the next aiogram release

What it caught the day it was written: ``vision``, consumed at ``bot/routers/photo.py:346``
and supplied by nobody, with P7 accepted eighteen gates out of eighteen and 645 tests
green; and, through the second gate below, ``transcriber`` / ``download`` -- declared by
name in ``voice.on_voice``, where a missing key is not «не настроен» but a ``TypeError``
in front of a teacher who has just spoken.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from aiogram import Dispatcher, Router
from aiogram.fsm.storage.memory import MemoryStorage

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dependency_scan as scanner  # noqa: E402


# =============================================================================
#  WHAT AIOGRAM ITSELF PUTS IN -- measured, not listed
# =============================================================================

def _probe(bot) -> set:
    """The keys aiogram hands a handler, obtained by asking aiogram.

    A bare dispatcher, one handler that takes ``**data``, one message and one callback
    query fed through it.  The union of what arrives is aiogram's own contribution:
    ``bot``, ``state``, ``event_update`` and the rest.  Written this way because the list
    is a property of the installed aiogram (3.22 here) and a hand-written copy of it goes
    stale in silence -- which is the same failure mode this whole file exists to close.
    """
    seen: set = set()

    async def probe(event, **data):
        seen.update(data)

    dp = Dispatcher(storage=MemoryStorage())
    router = Router(name="probe")
    router.message.register(probe)
    router.callback_query.register(probe)
    dp.include_router(router)

    user = {"id": 5, "is_bot": False, "first_name": "t"}
    chat = {"id": 5, "type": "private"}
    message = {"message_id": 1, "date": 1, "chat": chat, "from": user, "text": "hi"}
    updates = [
        {"update_id": 1, "message": message},
        {"update_id": 2, "callback_query": {
            "id": "1", "from": user, "chat_instance": "1", "message": message, "data": "x",
        }},
    ]
    loop = asyncio.new_event_loop()
    try:
        for update in updates:
            loop.run_until_complete(dp.feed_raw_update(bot, update))
    finally:
        loop.close()
    assert seen, "the probe received nothing: aiogram's contribution could not be measured"
    return seen


@pytest.fixture
def aiogram_keys(bot_instance) -> set:
    return _probe(bot_instance)


@pytest.fixture
def supplied(dispatcher, aiogram_keys) -> set:
    """Everything a handler can count on: workflow_data, aiogram's own, the middleware's."""
    return set(dispatcher.workflow_data) | aiogram_keys | set(scanner.middleware_providers())


# =============================================================================
#  GATE 1 -- the invisible route: ``**data`` and ``data.get("...")``
# =============================================================================

def test_every_key_a_handler_reads_out_of_data_is_one_build_puts_there(supplied, capsys):
    """``data.get("vision")`` with nothing behind it is a screen that is off in battle."""
    scan = scanner.scan_bot()
    asked = scan.keys()
    missing = sorted(asked - supplied)

    with capsys.disabled():
        print(
            "\n[ключи] файлов bot/** прочитано %d · потребляется %d, кладётся %d, "
            "НЕ ПОДСТАВЛЕНО %d"
            % (len(scan.files), len(asked), len(asked & supplied), len(missing))
        )

    assert not scan.unreadable, (
        "гейт не покрывает %d обращений с невычислимым ключом — охват неполон, "
        "и «дыр не найдено» здесь означало бы «не смотрели»:\n  %s"
        % (len(scan.unreadable), "\n  ".join(scan.unreadable))
    )
    assert not missing, (
        "%d зависимост(ь/и) берутся мимо сигнатуры и не кладутся в workflow_data — "
        "экран жив в тестах и мёртв в бою:\n%s"
        % (len(missing), "\n".join("  %s — %s" % (key, scan.where(key)) for key in missing))
    )


# =============================================================================
#  GATE 2 -- the visible route: a NAMED parameter aiogram resolves by name
# =============================================================================

def test_every_named_parameter_of_a_registered_handler_can_be_resolved(dispatcher, supplied, capsys):
    """``transcriber`` hides here, not behind ``data.get`` -- and it raises, not refuses.

    Only handlers on routers this dispatcher actually includes are examined, because that
    is the population that can be reached by an update.  A handler on a router nobody
    included cannot fail in battle; it also cannot work, which is what gate 3 is about.
    """
    handlers = scanner.registered_handlers(dispatcher)
    holes = []
    for where, callback, handler in handlers:
        # Per-handler, never blanket: a filter forgives a name only on the handler that
        # actually carries that filter.
        here = supplied | scanner.filter_supplied(handler)
        for name in scanner.named_parameters(callback):
            if name not in here:
                holes.append("  %s — просит %r" % (where, name))

    with capsys.disabled():
        print(
            "[ключи] хендлеров на включённых роутерах проверено %d из %d · "
            "неразрешимых аргументов %d"
            % (len(handlers), len(handlers), len(holes))
        )

    assert handlers, "ни одного хендлера не найдено — гейт ничего не проверил"
    assert not holes, (
        "%d именованн(ый/ых) аргумент(а/ов) хендлера не лежат в workflow_data — "
        "aiogram поднимет TypeError в момент, когда учитель нажмёт кнопку:\n%s"
        % (len(holes), "\n".join(holes))
    )


# =============================================================================
#  GATE 3 -- the door that was not hung at all
# =============================================================================

def test_every_screen_router_under_bot_is_included_by_build(dispatcher, capsys):
    """A screen nobody included answers nothing, and no dependency gate can see that.

    This is the hole ``vision`` was the SECOND lock on: ``bot/routers/photo.py`` and
    ``bot/routers/voice.py`` were written, tested and accepted while ``bot/app.py``
    included neither, so a photograph matched no handler and a teacher watched nothing
    happen.  Both fixtures that tested them built their own dispatcher and could not see
    it -- which is why this gate builds production's.
    """
    import ast

    package = scanner.BOT_PACKAGE
    factories = []
    for path in sorted((package / "routers").rglob("*.py")):
        if "__pycache__" in path.parts or path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in (
                "build_router",
                "build_routers",
            ):
                factories.append(path.stem)
    factories = sorted(set(factories))

    included = {router.name for router in scanner._routers(dispatcher)}
    missing = [name for name in factories if name not in included]

    with capsys.disabled():
        print(
            "[ключи] роутеров-экранов найдено %d, включено build() %d, не включено %d"
            % (len(factories), len(factories) - len(missing), len(missing))
        )

    assert factories, "ни одной фабрики роутера не найдено — гейт ничего не проверил"
    assert not missing, (
        "экран(ы) %s имеют фабрику роутера, но bot/app.py их не включает: "
        "обновление до них не доходит вовсе" % ", ".join(missing)
    )
