"""The bot entry point.

Run from the project root with:

    python3 -m bot

Reads ``BOT_TOKEN`` from the environment and uses ``data/`` for the two
SQLite files.  Real deployment goes through systemd; this file is what
systemd calls.
"""

from __future__ import annotations

import asyncio
import sys

from aiogram import Bot

from bot.app import build
from bot.config_local import BOT_TOKEN, OWNER_TG_ID
import config


async def _main() -> None:
    if not BOT_TOKEN:
        print(
            "BOT_TOKEN is empty.  Set the environment variable and try again.",
            file=sys.stderr,
        )
        sys.exit(2)
    dp = build(
        token=BOT_TOKEN,
        owner_tg_id=OWNER_TG_ID,
        journal_path=config.DB_PATH,
        roster_path=config.DB_PATH.parent / "roster.db",
    )
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(_main())