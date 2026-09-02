"""Backwards-compatible re-export: these constants now live in ``config.py``.

The module is kept only so its call sites (``bot/__main__.py``, ``bot/app.py``,
``bot/middleware.py``, ``bot/handlers/owner.py``, ``bot/handlers/registration.py``)
need not change here; it is deleted together with the edit of those call sites.

Nothing is defined in this file.  A value written here instead of in ``config.py``
recreates the second home this position closed.
"""

from __future__ import annotations

from config import (
    BOT_TOKEN,
    DEEPLINK_CODE_STUDENT,
    DEEPLINK_CODE_TEACHER,
    NAME_MAX_LEN,
    OWNER_TG_ID,
    ROOMS,
)

__all__ = [
    "BOT_TOKEN",
    "DEEPLINK_CODE_STUDENT",
    "DEEPLINK_CODE_TEACHER",
    "NAME_MAX_LEN",
    "OWNER_TG_ID",
    "ROOMS",
]
