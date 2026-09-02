"""A dispatcher built the way production builds one, and the fake session under it.

Deliberately NOT importing ``tests/photo/conftest.py``'s fixtures: a fixture file is a
file, and two positions writing into one file is the thing a wave cannot do.  The
duplication is small, named here, and named again in ``## ОТЧЁТ``.

**The environment handed to ``build`` is EMPTY on purpose.**  This gate must pass on a
machine with no keys at all -- that is the machine the tests run on, and a gate that
needed a key would be skipped in CI and would therefore never go red.  What it checks is
that every dependency a handler asks for is PRESENT in ``workflow_data``; whether the
value behind it is a real recogniser or an honest ``None`` is a different question, and
``tests/photo`` and ``tests/voice`` already answer it.
"""

from __future__ import annotations

import pytest
from aiogram import Bot
from aiogram.client.session.base import BaseSession


class SilentSession(BaseSession):
    """Swallows every Telegram call.  Nothing in this directory sends one."""

    async def close(self) -> None:
        pass

    async def make_request(self, bot, method, timeout=None):
        return None

    async def stream_content(self, *args, **kwargs):  # pragma: no cover -- never called
        yield b""


@pytest.fixture
def bot_instance() -> Bot:
    return Bot(token="0:fake", session=SilentSession())


@pytest.fixture
def roster_path(tmp_path):
    return tmp_path / "roster-klyuchi.db"


@pytest.fixture
def dispatcher(db_path, roster_path, bot_instance):
    """``bot.app.build`` itself -- not a fixture's idea of what it should have wired.

    The whole point of this directory is that the two must not be allowed to differ.  A
    dispatcher assembled here by hand would be assembled from the same beliefs that let
    ``vision`` go missing for the length of a whole position.
    """
    from bot.app import build

    for module_name in ("owner", "registration", "student", "teacher"):
        module = __import__("bot.handlers." + module_name, fromlist=[module_name])
        module.router._parent_router = None

    return build(
        token="0:fake",
        owner_tg_id=999999,
        journal_path=db_path,
        roster_path=roster_path,
        bot=bot_instance,
        environ={},
    )
