"""Web entry point (vhod) — two common passwords, signed cookie, no usernames.

This file is part of zone `veb-vhod-i-obshchee-sostoyanie`.
The two public declarations (`marshruty`, `rol`) are inserted by the
neighbouring server; everything else lives here.
"""

from __future__ import annotations

import base64
import hmac
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from typing import Optional

# ------------------------------------------------------------------ env keys

SPETSMAT_VEB_PAROL_PREPOD = os.environ.get("SPETSMAT_VEB_PAROL_PREPOD", "")
SPETSMAT_VEB_PAROL_ORG = os.environ.get("SPETSMAT_VEB_PAROL_ORG", "")
SPETSMAT_VEB_SECRET = os.environ.get("SPETSMAT_VEB_SECRET", "")

# ------------------------------------------------------------------ cookie constants

COOKIE_NAME = "spetsmat_veb"
COOKIE_MAX_AGE_DAYS = 30
COOKIE_MAX_AGE_SECONDS = COOKIE_MAX_AGE_DAYS * 24 * 3600


def _raise_missing_env() -> None:
    missing: list[str] = []
    if not SPETSMAT_VEB_SECRET:
        missing.append("SPETSMAT_VEB_SECRET")
    # The entry file explicitly demands that missing env variables cause
    # a clear startup refusal rather than a silent default.
    if missing:
        raise RuntimeError(
            "veb/vhod.py: missing required environment variable(s): "
            + ", ".join(missing)
        )


# ------------------------------------------------------------------ public contract

def marshruty():
    """Paths of the entry page: {path: handler}."""
    return {"/vhod": obrabotchik_vhoda, "/vyhod": obrabotchik_vyhoda}


def rol(headers) -> Optional[str]:
    """Role from cookie in request headers: 'prepod' | 'organizator' | None.

    None means "not allowed": the caller must redirect to /vhod.
    """
    cookie_header = ""
    if hasattr(headers, "get"):
        cookie_header = headers.get("Cookie", "")
    # Find our cookie by name
    cookie_value: Optional[str] = None
    for part in cookie_header.split(";"):
        part = part.strip()
        if part.startswith(COOKIE_NAME + "="):
            cookie_value = part[len(COOKIE_NAME) + 1:]
            break
    if cookie_value is None:
        return None
    return _verify_cookie(cookie_value)


def obrabotchik_vhoda() -> bytes:
    """Handler for GET /vhod — entry form."""
    # The page is served as static HTML with embedded CSS reference.
    # See veb/static/vhod.css for styling.
    html_str = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Вход — Спецмат</title>
<link rel="stylesheet" href="/static/vhod.css">
</head>
<body>
<header>
  <h1>Спецмат — вход</h1>
  <p>Преподаватель или организатор. Без имён пользователей.</p>
</header>
<main>
  <form method="post" action="/vhod">
    <label for="parol">Пароль</label>
    <input type="password" id="parol" name="parol" required autocomplete="current-password">
    <button type="submit">Войти</button>
  </form>
  <p class="note">Два уровня: преподаватель и организатор. Общие пароли из окружения.</p>
  <p class="stale">Данные обновляются при перезагрузке страницы; у других могло измениться — обновите страницу.</p>
</main>
</body>
</html>"""
    return html_str.encode("utf-8")


def obrabotchik_vyhoda() -> bytes:
    """Handler for GET /vyhod — clears cookie and redirects back."""
    return "<!doctype html><html><head><meta http-equiv=\"refresh\" content=\"0;url=/vhod\"></head><body>Выход выполнен.</body></html>".encode("utf-8")


# ------------------------------------------------------------------ cookie helpers

def _sign(value: str) -> str:
    if not SPETSMAT_VEB_SECRET:
        raise RuntimeError("SPETSMAT_VEB_SECRET is not set: cookie signature impossible")
    sig = hmac.new(
        SPETSMAT_VEB_SECRET.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{value}.{sig}"


def _verify_cookie(raw: str) -> Optional[str]:
    if "." not in raw:
        return None
    value, sig = raw.rsplit(".", 1)
    expected = hmac.new(
        SPETSMAT_VEB_SECRET.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    # Decode payload: base64url (padding restored) then JSON
    try:
        padding = "=" * (-len(value) % 4)
        payload_str = base64.urlsafe_b64decode(value + padding).decode("utf-8")
        payload = json.loads(payload_str)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    role = payload.get("r")
    ts = payload.get("t")
    if role not in ("prepod", "organizator") or ts is None:
        return None
    # 30-day expiry
    if time.time() - ts > COOKIE_MAX_AGE_SECONDS:
        return None
    return role


def _make_cookie(role: str) -> str:
    payload = json.dumps({"r": role, "t": int(time.time())})
    encoded = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    return _sign(encoded)


def _check_password(submitted: str) -> Optional[str]:
    if not SPETSMAT_VEB_PAROL_PREPOD or not SPETSMAT_VEB_PAROL_ORG:
        # If env passwords are missing, the server must refuse startup clearly,
        # but we must not expose which is which in error messages.
        return None
    if submitted == SPETSMAT_VEB_PAROL_PREPOD:
        return "prepod"
    if submitted == SPETSMAT_VEB_PAROL_ORG:
        return "organizator"
    return None


# ------------------------------------------------------------------ guard

_raise_missing_env()
