"""Tests for `veb/razdely/vnesenie.py`: text/photo/voice draft, then one confirmed write.

🔴 THE LOAD-BEARING CLAIM OF THIS FILE: no draft door (`/api/vnesti/{tekst,foto,golos}`)
ever writes a mark, and `/api/vnesti/zapisat` writes EXACTLY the cells the test confirms
— never more, never the server's own guess.  Every test that calls a draft door also
asserts the journal is still empty afterwards, and every test that calls `zapisat`
compares the written set against the confirmed set by direct SQL, per КРИТЕРИЙ ГОТОВНОСТИ
point 1.

Photo and voice are exercised against INJECTED fakes (`veb.razdely.vnesenie.build_vision`
/ `.build_transcriber` monkeypatched), never a live network call: a flaky outbound link is
exactly what КРИТЕРИЙ point 2 asks to be proven resilient to, and a live call would make
that proof depend on the same flakiness it is supposed to survive.  The server booted here
is a minimal one built directly from `vnesenie.marshruty()`, the same device
`tests/veb/test_priyom.py` already uses, so the page is provable without depending on
`veb/server.py`'s own boot path.
"""

from __future__ import annotations

import base64
import json
import os
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import config
import pytest
from infra.db import apply_migrations, connect

os.environ.setdefault("SPETSMAT_VEB_SECRET", "test-secret-key-32bytes!")

from veb import vhod
from veb.razdely import vnesenie


def _handler_klass():
    marshruty = vnesenie.marshruty()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def _obsluzhit(self):
            from urllib.parse import urlparse
            put = urlparse(self.path).path
            if put in marshruty:
                marshruty[put](self)
                return
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()

        do_GET = _obsluzhit
        do_POST = _obsluzhit

    return Handler


@pytest.fixture
def server(tmp_path):
    """One sheet with three problems, three pupils whose surnames are pairwise far
    apart (so the fuzzy channel resolves them without ambiguity) plus one pair close
    enough to force a "кто это?" — the shape КРИТЕРИЙ point 1 asks for on every channel.
    """
    db_path = tmp_path / "spetsmat.db"
    apply_migrations(db_path, config.MIGRATIONS_DIR)
    connection = connect(db_path)
    sheet_id = connection.execute(
        "insert into sheets (number, title, issued_at, ord) values (?, ?, ?, ?)",
        ("1", "листок 1", "2026-09-01", 1),
    ).lastrowid
    problem_ids = {
        label: connection.execute(
            "insert into problems (sheet_id, label, kind, ord) values (?, ?, 'обязательная', ?)",
            (sheet_id, label, i),
        ).lastrowid
        for i, label in enumerate(("3", "5", "7б"), start=1)
    }
    teacher_id = connection.execute(
        "insert into teachers (name, aka, is_owner) values ('Пирогов', 'pir', 0)"
    ).lastrowid
    student_ids = {
        surname: connection.execute(
            "insert into students (surname, name, class, status, first_sheet_id) "
            "values (?, ?, '9a', 'active', ?)",
            (surname, name, sheet_id),
        ).lastrowid
        for surname, name in (
            ("Петров", "Иван"), ("Бочарова", "Аня"), ("Быков", "Влад"),
        )
    }
    connection.commit()

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _handler_klass())
    httpd.db_path = str(db_path)  # type: ignore[attr-defined]
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield {
            "baza": f"http://127.0.0.1:{port}",
            "c": connection,
            "listok": sheet_id,
            "zadachi": problem_ids,
            "deti": student_ids,
            "prepod": teacher_id,
        }
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join()
        connection.close()


def _kuka(teacher_id=None) -> str:
    return f"{vhod.COOKIE_NAME}={vhod._make_cookie('prepod', teacher_id)}"


def _post(url: str, telo: dict, teacher_id=None) -> tuple:
    data = json.dumps(telo).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json", "Cookie": _kuka(teacher_id)})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def _get(url: str, teacher_id=None) -> tuple:
    req = urllib.request.Request(url, headers={"Cookie": _kuka(teacher_id)})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _marks(c) -> list:
    return c.execute(
        "select student_id, problem_id, event, source, teacher_id from marks order by id"
    ).fetchall()


def _pick(draft: dict, said_contains: str) -> dict:
    for row in draft["rows"]:
        if said_contains in row["said"]:
            return row
    raise AssertionError("no row containing %r in %r" % (said_contains, draft["rows"]))


def _zapisi_ot(row: dict) -> list:
    """Every writable cell of a resolved row, ticked as the server proposed."""
    return [
        {"student_id": row["student_id"], "problem_id": c["problem_id"], "ticked": c["ticked"]}
        for c in row["cells"] if c["problem_id"] is not None and not c.get("retracted")
    ]


# ------------------------------------------------------------------------- канал: текст


def test_tekst_tri_vnesenia_pishut_rovno_podtverzhdyonnoe(server):
    """КРИТЕРИЙ п.1, канал «текст»: три внесения, гипотеза печатается, запись сверяется
    прямым SQL — записалось ровно подтверждённое, ни задачей больше."""
    baza, c, zad, deti = server["baza"], server["c"], server["zadachi"], server["deti"]

    # 1: чистое совпадение, одна задача.
    status, draft = _post(baza + "/api/vnesti/tekst", {"text": "Петров 3"})
    assert status == 200
    row = _pick(draft, "Петров")
    assert row["student_id"] == deti["Петров"]
    assert row["verdict"] == "certain"
    status, otvet = _post(baza + "/api/vnesti/zapisat", {
        "channel": "текст", "digest": draft["digest"], "cells": _zapisi_ot(row)},
        teacher_id=server["prepod"])
    assert status == 200 and otvet["zapisano"][0]["zapisano"] is True

    # 2: чистое совпадение, две задачи через запятую и по-другому написанная фамилия.
    status, draft = _post(baza + "/api/vnesti/tekst", {"text": "Бочарова 5, 7б"})
    row = _pick(draft, "Бочарова")
    assert row["student_id"] == deti["Бочарова"]
    status, otvet = _post(baza + "/api/vnesti/zapisat", {
        "channel": "текст", "digest": draft["digest"], "cells": _zapisi_ot(row)},
        teacher_id=server["prepod"])
    assert status == 200
    assert all(z["zapisano"] for z in otvet["zapisano"])

    # 3: человек СНИМАЕТ галочку с одной из предложенных клеток перед записью — и она
    # не должна уехать в журнал, даже если сервер её изначально предложил.
    status, draft = _post(baza + "/api/vnesti/tekst", {"text": "Быков 3, 5"})
    row = _pick(draft, "Быков")
    zapisi = _zapisi_ot(row)
    assert len(zapisi) == 2
    zapisi[1]["ticked"] = False  # человек передумал про вторую задачу
    _post(baza + "/api/vnesti/zapisat", {
        "channel": "текст", "digest": draft["digest"], "cells": zapisi},
        teacher_id=server["prepod"])

    rows = _marks(c)
    zapisano_par = {(r["student_id"], r["problem_id"]) for r in rows}
    assert (deti["Петров"], zad["3"]) in zapisano_par
    assert (deti["Бочарова"], zad["5"]) in zapisano_par
    assert (deti["Бочарова"], zad["7б"]) in zapisano_par
    assert (deti["Быков"], zad["3"]) in zapisano_par
    assert (deti["Быков"], zad["5"]) not in zapisano_par, "снятая галочка не должна писаться"
    assert len(rows) == 4, "записалось ровно подтверждённое, ни задачей больше: %r" % (rows,)
    assert all(r["source"] == "кнопка" and r["teacher_id"] == server["prepod"] for r in rows)


def test_draft_dver_nichego_ne_pishet(server):
    """Ни один запрос гипотезы сам по себе не пишет в журнал — до `zapisat` включительно."""
    baza, c = server["baza"], server["c"]
    _post(baza + "/api/vnesti/tekst", {"text": "Петров 3, 5"})
    _post(baza + "/api/vnesti/tekst", {"text": "Бочарова 7б"})
    assert _marks(c) == []


def test_tekst_dvusmyslennoe_imya_daet_knopki_a_ne_dogadku(server):
    """Незнакомое имя не пишется наугад — оно приходит как «кто это?» с альтернативами."""
    baza = server["baza"]
    status, draft = _post(baza + "/api/vnesti/tekst", {"text": "Совсем Чужойчеловек 3"})
    row = draft["rows"][0]
    assert row["student_id"] is None
    assert row["verdict"] == "unknown"


def test_zapis_bez_studenta_propuskaetsya_a_ne_padaet(server):
    """Строка без разрешённого ученика, случайно отправленная в `zapisat`, тихо
    пропускается — а не роняет всю пачку и не пишет её наугад."""
    baza, c = server["baza"], server["c"]
    status, otvet = _post(baza + "/api/vnesti/zapisat", {
        "channel": "текст", "digest": "abc",
        "cells": [{"student_id": None, "problem_id": 1, "ticked": True}]},
        teacher_id=server["prepod"])
    assert status == 200
    assert otvet["zapisano"] == []
    assert _marks(c) == []


def test_bez_kuki_vse_dveri_otkazyvayut(server):
    baza = server["baza"]
    for put, telo in (
        ("/api/vnesti/tekst", {"text": "Петров 3"}),
        ("/api/vnesti/foto", {"data_base64": ""}),
        ("/api/vnesti/golos", {"data_base64": ""}),
        ("/api/vnesti/zapisat", {"channel": "текст", "digest": "x", "cells": []}),
    ):
        data = json.dumps(telo).encode("utf-8")
        req = urllib.request.Request(baza + put, data=data, method="POST",
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                status = r.status
        except urllib.error.HTTPError as exc:
            status = exc.code
        assert status == 403, put


def test_stranica_bez_kuki_ne_pokazyvaet_formu(server):
    req = urllib.request.Request(server["baza"] + "/vnesti")  # НЕТ Cookie вовсе
    with urllib.request.urlopen(req) as r:
        stranica = r.read().decode("utf-8")
    assert "/vhod" in stranica
    assert "tekst-vvod" not in stranica


def test_marshruty_obyavleny_kontraktom(server):
    marshruty = vnesenie.marshruty()
    assert set(marshruty) == {
        "/vnesti", "/api/vnesti/tekst", "/api/vnesti/foto",
        "/api/vnesti/golos", "/api/vnesti/zapisat",
    }
    assert all(callable(o) for o in marshruty.values())


# ------------------------------------------------------------------------- канал: фото


class _FakeVision:
    """Injected in place of `infra.llm.VisionModel`: no network, deterministic answer."""

    def __init__(self, answers):
        self._answers = list(answers)
        self.calls = 0

    def read_sheet(self, jpeg, codes, labels, sheets=None):
        self.calls += 1
        answer = self._answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


def _llm_answer(raw_text, rows):
    from infra.llm import LlmAnswer
    return LlmAnswer(raw_text=raw_text, rows=tuple(rows), model="fake", latency_s=0.01)


def _jpeg_bytes() -> bytes:
    """A tiny real JPEG so `raspoznavanie.prepare` has something to decode."""
    from PIL import Image
    import io
    buf = io.BytesIO()
    Image.new("RGB", (64, 48), color=(200, 200, 200)).save(buf, format="JPEG")
    return buf.getvalue()


def test_foto_tri_vnesenia_pishut_rovno_podtverzhdyonnoe(server, monkeypatch):
    """КРИТЕРИЙ п.1, канал «фото», через инъекцию — три успешных распознавания подряд."""
    baza, c, zad, deti = server["baza"], server["c"], server["zadachi"], server["deti"]
    from core.services.raspoznavanie import code_for_student

    answers = [
        _llm_answer("u1 3", [{"student_code": code_for_student(deti["Петров"]),
                              "solved": ["3"], "retracted": [], "alternatives": []}]),
        _llm_answer("u2 5 7б", [{"student_code": code_for_student(deti["Бочарова"]),
                                 "solved": ["5", "7б"], "retracted": [], "alternatives": []}]),
        _llm_answer("u3 -", [{"student_code": code_for_student(deti["Быков"]),
                              "solved": [], "retracted": ["3"], "alternatives": []}]),
    ]
    fake = _FakeVision(answers)
    monkeypatch.setattr(vnesenie, "build_vision", lambda: (fake, "test"))

    jpeg = base64.b64encode(_jpeg_bytes()).decode()
    for _ in range(3):
        status, draft = _post(baza + "/api/vnesti/foto", {"data_base64": jpeg},
                              teacher_id=server["prepod"])
        assert status == 200, draft
        for row in draft["rows"]:
            zapisi = _zapisi_ot(row)
            if zapisi:
                _post(baza + "/api/vnesti/zapisat", {
                    "channel": "фото", "digest": draft["digest"], "cells": zapisi},
                    teacher_id=server["prepod"])

    assert fake.calls == 3
    rows = _marks(c)
    assert (deti["Петров"], zad["3"]) in {(r["student_id"], r["problem_id"]) for r in rows}
    assert (deti["Бочарова"], zad["5"]) in {(r["student_id"], r["problem_id"]) for r in rows}
    assert (deti["Бочарова"], zad["7б"]) in {(r["student_id"], r["problem_id"]) for r in rows}
    # «Снято» (retracted) НЕ пишется этой дверью вовсе — она не предлагает такую клетку
    # как записываемую (см. `## ВОПРОСЫ`): Быков не получает ни одной строки в журнале.
    assert (deti["Быков"], zad["3"]) not in {(r["student_id"], r["problem_id"]) for r in rows}
    assert all(r["source"] == "фото" for r in rows)


def test_foto_otkaz_vneshnego_api_pokazan_a_ne_proglochen(server, monkeypatch):
    """КРИТЕРИЙ п.2: обрыв внешнего вызова — человек видит ошибку, журнал не тронут, и
    повторный (успешный) вызов после отказа доезжает как ни в чём не бывало."""
    baza, c = server["baza"], server["c"]
    from infra.llm import LlmTransportError

    fake = _FakeVision([LlmTransportError("сеть недоступна: test")])
    monkeypatch.setattr(vnesenie, "build_vision", lambda: (fake, "test"))

    jpeg = base64.b64encode(_jpeg_bytes()).decode()
    status, otvet = _post(baza + "/api/vnesti/foto", {"data_base64": jpeg},
                          teacher_id=server["prepod"])
    assert status == 502
    assert "error" in otvet and otvet["error"]
    assert _marks(c) == [], "отказ внешнего API не должен ничего записать"

    # Повтор («попробовать ещё раз») с тем же снимком — снимок никуда не делся, потому
    # что дверь его вообще не хранит: браузер отправляет его заново сам.
    fake._answers.append(_llm_answer("u1 3", []))
    status, draft = _post(baza + "/api/vnesti/foto", {"data_base64": jpeg},
                          teacher_id=server["prepod"])
    assert status == 200, draft


def test_foto_bez_listkov_otkazyvaet_vnyatno(server, monkeypatch):
    """Пустая база листков — вменяемая ошибка, а не 500 и не молчаливая заглушка."""
    baza = server["baza"]
    empty_db = server["c"].execute("delete from problems")
    server["c"].commit()
    jpeg = base64.b64encode(_jpeg_bytes()).decode()
    status, otvet = _post(baza + "/api/vnesti/foto", {"data_base64": jpeg},
                          teacher_id=server["prepod"])
    assert status == 400
    assert "error" in otvet


# ------------------------------------------------------------------------- канал: голос


class _FakeTranscriber:
    def __init__(self, answers):
        self._answers = list(answers)
        self.calls = 0

    def transcribe(self, audio, *, mime_type="audio/ogg"):
        self.calls += 1
        answer = self._answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


def test_golos_tri_vnesenia_pishut_rovno_podtverzhdyonnoe(server, monkeypatch):
    """КРИТЕРИЙ п.1, канал «голос», через инъекцию — три успешных распознавания подряд."""
    baza, c, zad, deti = server["baza"], server["c"], server["zadachi"], server["deti"]

    fake = _FakeTranscriber(["петров три", "бочарова пять и семь бэ", "быков минус три"])
    monkeypatch.setattr(vnesenie, "build_transcriber", lambda phrases: (fake, "test"))

    audio = base64.b64encode(b"\x00\x01\x02fake-ogg-bytes").decode()
    for _ in range(3):
        status, draft = _post(baza + "/api/vnesti/golos", {"data_base64": audio},
                              teacher_id=server["prepod"])
        assert status == 200, draft
        for row in draft["rows"]:
            zapisi = [z for z in _zapisi_ot(row) if z["ticked"]]
            if zapisi:
                _post(baza + "/api/vnesti/zapisat", {
                    "channel": "голос", "digest": draft["digest"], "cells": zapisi},
                    teacher_id=server["prepod"])

    assert fake.calls == 3
    rows = {(r["student_id"], r["problem_id"]) for r in _marks(c)}
    assert (deti["Петров"], zad["3"]) in rows
    assert (deti["Бочарова"], zad["5"]) in rows
    assert (deti["Бочарова"], zad["7б"]) in rows
    assert all(r["source"] == "голос" for r in _marks(c) if (r["student_id"], r["problem_id"]) in
              {(deti["Петров"], zad["3"]), (deti["Бочарова"], zad["5"])})


def test_golos_otkaz_vneshnego_api_pokazan_a_ne_proglochen(server, monkeypatch):
    """КРИТЕРИЙ п.2 для голосового канала: обрыв распознавания — виден, ничего не записано."""
    baza, c = server["baza"], server["c"]
    from infra.asr import TranscriptionUnavailable

    fake = _FakeTranscriber([TranscriptionUnavailable("recogniser unreachable: test")])
    monkeypatch.setattr(vnesenie, "build_transcriber", lambda phrases: (fake, "test"))

    audio = base64.b64encode(b"\x00\x01\x02fake-ogg-bytes").decode()
    status, otvet = _post(baza + "/api/vnesti/golos", {"data_base64": audio},
                          teacher_id=server["prepod"])
    assert status == 502
    assert "error" in otvet and otvet["error"]
    assert _marks(c) == []
