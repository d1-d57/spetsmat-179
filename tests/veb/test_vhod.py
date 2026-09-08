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


def test_entry_form_posts_to_absolute_https():
    """The password must leave over https even when the page itself was fetched over http —
    `marshruty()` hands `obrabotchik_vhoda` no request context, so the fix has to be an
    address that is right regardless of which scheme served the page, not a runtime check."""
    html = vh.obrabotchik_vhoda().decode("utf-8")
    assert 'action="https://math-kluychiki.ru/vhod"' in html
    assert 'action="/vhod"' not in html


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
