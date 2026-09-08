"""Tests for veb/vhod.py — signature, redirect without cookie, cookie forgery.

Zone: veb-vhod-i-obshchee-sostoyanie.
"""

import os
import pytest

# We test the module logic; the env variables must be set for the module
# to load without the startup refusal demanded by the contract.
os.environ.setdefault("SPETSMAT_VEB_PAROL_PREPOD", "teacher-pass")
os.environ.setdefault("SPETSMAT_VEB_PAROL_ORG", "org-pass")
os.environ.setdefault("SPETSMAT_VEB_SECRET", "test-secret-key-32bytes!")

import veb.vhod as vh


class FakeHeaders:
    """Minimal stand-in for BaseHTTPRequestHandler.headers."""
    def __init__(self, cookie=""):
        self._cookie = cookie
    def get(self, name, default=""):
        return self._cookie if name == "Cookie" else default


def test_cookie_signature_and_verify():
    import base64
    import json as _json

    cookie_raw = vh._make_cookie("prepod")
    payload_part, _sig = cookie_raw.rsplit(".", 1)
    assert not payload_part.startswith('{"')  # payload is base64url-encoded now
    padding = "=" * (-len(payload_part) % 4)
    payload = _json.loads(base64.urlsafe_b64decode(payload_part + padding).decode("utf-8"))
    assert payload["r"] == "prepod"
    full_cookie = f"{vh.COOKIE_NAME}={cookie_raw}"
    role = vh.rol(FakeHeaders(cookie=full_cookie))
    assert role == "prepod"


def test_no_cookie_returns_none():
    assert vh.rol(FakeHeaders(cookie="")) is None
    assert vh.rol(FakeHeaders(cookie="other=value")) is None


def test_cookie_forgery_fails():
    cookie_raw = vh._make_cookie("prepod")
    full_cookie = f"{vh.COOKIE_NAME}={cookie_raw}"
    # Modify one byte in the signature part (after the last dot)
    forged = cookie_raw[:-1] + ("X" if cookie_raw[-1] != "X" else "Y")
    assert vh.rol(FakeHeaders(cookie=f"{vh.COOKIE_NAME}={forged}")) is None


def test_entry_form_posts_relative_and_never_pins_the_session_to_443():
    """The form must NOT hard-code a scheme, so the visitor stays on whichever one they arrived by.

    This test replaces `test_entry_form_posts_to_absolute_https` of 2026-09-08 05:40, which
    asserted the opposite. That absolute `action` was measured on the owner's laptop
    (заход `bystro-i-bezopasno`, 2026-09-08) to pin the WHOLE session to port 443: the POST
    went to the https origin and the 302 answering it carries a relative `Location`, so every
    click after the login stayed on https — 20 submissions out of 20 landed on https, against
    20 out of 20 landing on http once the action became relative. Port 443 on this path is
    filtered intermittently (probe of 2026-09-06: 30 successes out of 30, an hour later 3
    timeouts out of 3), so pinning the session to it is what the owner experienced as "every
    button takes minutes". Forcing https was never a Google requirement:
    `ZAMYSEL-profil-bezopasnosti.md` §4 names the visible warning line as the maximum here,
    and it is asserted by the test below.
    """
    html = vh.obrabotchik_vhoda().decode("utf-8")
    assert 'action="/vhod"' in html
    assert "action=\"https://" not in html
    assert "action=\"http://" not in html


def test_entry_form_carries_http_warning_hidden_by_default():
    html = vh.obrabotchik_vhoda().decode("utf-8")
    assert 'id="http-predupr"' in html
    assert "hidden" in html
    assert "без шифрования" in html
    assert 'location.protocol === "http:"' in html


def test_cookie_expiry_refuses_old_cookie(monkeypatch):
    import time
    import base64
    import json

    cookie_raw = vh._make_cookie("organizator")
    # Force the payload timestamp to be in the past beyond 30 days
    payload_part, sig = cookie_raw.rsplit(".", 1)
    padding = "=" * (-len(payload_part) % 4)
    payload = json.loads(base64.urlsafe_b64decode(payload_part + padding).decode("utf-8"))
    payload["t"] = int(time.time()) - vh.COOKIE_MAX_AGE_DAYS * 24 * 3600 - 1
    new_payload_part = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).decode().rstrip("=")
    old_cookie_str = vh._sign(new_payload_part)
    assert vh.rol(FakeHeaders(cookie=f"{vh.COOKIE_NAME}={old_cookie_str}")) is None
