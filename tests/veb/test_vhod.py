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
    cookie_raw = vh._make_cookie("prepod")
    assert cookie_raw.startswith('{"')
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


def test_cookie_expiry_refuses_old_cookie(monkeypatch):
    import time
    cookie_raw = vh._make_cookie("organizator")
    # Force the payload timestamp to be in the past beyond 30 days
    payload_part, sig = cookie_raw.rsplit(".", 1)
    import json
    payload = json.loads(payload_part)
    payload["t"] = int(time.time()) - vh.COOKIE_MAX_AGE_DAYS * 24 * 3600 - 1
    new_payload_part = json.dumps(payload)
    old_cookie = vh._sign(new_payload_part)  # Actually _sign takes value string
    # Rebuild properly
    import hmac, hashlib
    new_sig = hmac.new(
        vh.SPETSMAT_VEB_SECRET.encode("utf-8"),
        new_payload_part.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    old_cookie_str = f"{new_payload_part}.{new_sig}"
    assert vh.rol(FakeHeaders(cookie=f"{vh.COOKIE_NAME}={old_cookie_str}")) is None
