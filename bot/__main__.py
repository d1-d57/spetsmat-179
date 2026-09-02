"""The bot entry point.

Run from the project root with:

    python3 -m bot

Reads ``BOT_TOKEN`` from the environment and uses ``data/`` for the two
SQLite files.  Real deployment goes through systemd; this file is what
systemd calls.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from aiogram import Bot

from bot.app import build
from bot.config_local import BOT_TOKEN, OWNER_TG_ID
import config


#: Уровень журнала. INFO по умолчанию, и это не вкусовщина: ИМЕННО НА INFO пишутся
#: обе строки, которыми процесс ДОКАЗЫВАЕТ человеку, что распознавание фото и речи
#: включено, — «vision on: …» и «speechkit …» / «NO RECOGNISER: …».
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()


def nastroit_zhurnal(level: str = "", stream=None) -> None:
    """Дать корневому логгеру УРОВЕНЬ и ПРИЁМНИК. Без этого `log.info()` уходит в никуда.

    🔴 ЦЕНА ОТСУТСТВИЯ, найдено владельцем 02.09 вечером. `bot/app.py:52` заводит
    логгер, `basicConfig` не вызывался НИГДЕ во всём боевом коде (проверено грепом
    по `bot/ core/ infra/ tools/ config.py` — ноль вхождений `basicConfig`,
    `dictConfig`, `addHandler`). У корневого логгера уровень WARNING и НОЛЬ
    приёмников, поэтому `log.isEnabledFor(INFO)` возвращает False, и обе строки,
    ради которых `P20` их и писала, печатались в пустоту.

    Это ровно тот класс, что и остальные дефекты этой волны: ДОКАЗАТЕЛЬСТВО ЕСТЬ,
    А УВИДЕТЬ ЕГО НЕЛЬЗЯ. Пустой `BOT_TOKEN` при 486 зелёных тестах, `vision` не
    проведённый в `workflow_data` при 18 гейтах из 18 — и вот теперь запись в
    журнал, которой некуда лечь.

    Пишем в `stderr`, а не в файл: боевая выкатка `P10` идёт под systemd, и
    `journald` забирает поток юнита сам (`deploy/journald-spetsmat.conf`). Файл
    рядом с процессом потребовал бы своей ротации и своих прав.

    `force=True` обязателен: любая библиотека, успевшая позвать `basicConfig`
    раньше нас, иначе оставит корень со своим уровнем, и наша настройка будет
    молча проигнорирована — тот же тихий отказ, который мы здесь и чиним.
    """
    logging.basicConfig(
        level=getattr(logging, (level or LOG_LEVEL), logging.INFO),
        stream=stream or sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=True,
    )


async def _main() -> None:
    # 🔴 ПЕРВЫМ ХОДОМ, ДО `build()`: именно build() пишет строки про vision и речь,
    # и настройка, сделанная после него, опоздала бы ровно на то, ради чего нужна.
    nastroit_zhurnal()
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