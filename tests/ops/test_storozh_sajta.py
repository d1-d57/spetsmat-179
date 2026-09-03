"""Tests for ops/storozh_sajta.py: three outcomes and state-change alarm."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from ops import storozh_sajta


class OkHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *a, **k):
        pass


class ErrorHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(500)
        self.end_headers()
        self.wfile.write(b"error")

    def log_message(self, *a, **k):
        pass


def _serve(port: int, handler):
    srv = HTTPServer(("127.0.0.1", port), handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv


def test_zhiv_on_live_port(tmp_path, monkeypatch):
    srv = _serve(18765, OkHandler)
    monkeypatch.setattr(storozh_sajta, "ADRES_FILE", tmp_path / "adres.txt")
    (tmp_path / "adres.txt").write_text("http://localhost:18765", encoding="utf-8")
    # Clear state file
    monkeypatch.setattr(storozh_sajta, "STATE_FILE", tmp_path / "state.json")
    code = storozh_sajta.main([])
    assert code == 0
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert state.get("last_verdict") == "жив"
    srv.shutdown()
    srv.server_close()


def test_mertv_on_500(tmp_path, monkeypatch):
    srv = _serve(18766, ErrorHandler)
    monkeypatch.setattr(storozh_sajta, "ADRES_FILE", tmp_path / "adres.txt")
    (tmp_path / "adres.txt").write_text("http://localhost:18766", encoding="utf-8")
    monkeypatch.setattr(storozh_sajta, "STATE_FILE", tmp_path / "state.json")
    code = storozh_sajta.main([])
    assert code == 1
    srv.shutdown()
    srv.server_close()


def test_ne_smog_proverit_on_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(storozh_sajta, "ADRES_FILE", tmp_path / "adres.txt")
    monkeypatch.setattr(storozh_sajta, "STATE_FILE", tmp_path / "state.json")
    code = storozh_sajta.main([])
    assert code == 1
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert state.get("last_verdict") == "не смог проверить"


def test_alarm_on_state_change(tmp_path, monkeypatch):
    monkeypatch.setattr(storozh_sajta, "ADRES_FILE", tmp_path / "adres.txt")
    (tmp_path / "adres.txt").write_text("http://localhost:9999", encoding="utf-8")
    monkeypatch.setattr(storozh_sajta, "STATE_FILE", tmp_path / "state.json")
    (tmp_path / "state.json").write_text(json.dumps({"last_verdict": "жив"}), encoding="utf-8")
    # 9999 is unreachable -> не смог проверить, different from prev -> alarm
    code = storozh_sajta.main([])
    assert code == 1
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert state.get("last_verdict") == "не смог проверить"


def test_tiho_silences_first_run_alarm(tmp_path, monkeypatch):
    monkeypatch.setattr(storozh_sajta, "ADRES_FILE", tmp_path / "adres.txt")
    (tmp_path / "adres.txt").write_text("http://localhost:9998", encoding="utf-8")
    monkeypatch.setattr(storozh_sajta, "STATE_FILE", tmp_path / "state.json")
    # Existing state file with same value; --tiho suppresses any alarm.
    (tmp_path / "state.json").write_text(json.dumps({"last_verdict": "не смог проверить"}), encoding="utf-8")
    code = storozh_sajta.main(["--tiho"])
    # Should not alarm; result is still failure.
    assert code == 1
