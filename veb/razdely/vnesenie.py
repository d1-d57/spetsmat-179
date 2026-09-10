#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-code — the routes below are declared by `marshruty()` and
# collected by `veb.server._marshruty_razdelov` (`RAZDELY_S_MARSHRUTAMI` names this
# module), the same contract `veb/priyom.py` already uses.
"""«Внести задачи»: one scenario, three doors in — text, photo, voice — one confirmation
table, one door out.

The owner 09.09: *"ты вносишь в каком-то формате любой текст... дальше он у тебя
спрашивает, выводит гипотезу... нажимаешь, что всё хорошо, и он загружает эти плюсики
с пометкой, от какого преподавателя они пришли"*.

🔴 THERE IS NO DIRECT WRITE FROM ANY DRAFT DOOR.  `POST /api/vnesti/tekst`,
`.../foto` and `.../golos` each build a hypothesis and hand it BACK to the browser as
JSON; nothing in any of the three ever touches `MarkJournal`.  The one door that writes
is `POST /api/vnesti/zapisat`, and it writes exactly the cells the human confirmed —
never the server's own draft — through `MarkingService.give`, the same door
`veb/priyom.py` already uses.  A second journal is a declared failure of the whole wave.

🔴 TWO SHAPES, ONE WIRE FORMAT.  Photo answers as `core.services.raspoznavanie.DraftRow`
(flat `solved`/`retracted` label tuples); text and voice both answer as
`core.services.golos.Draft` (rows of cells, `bystryj_tekst.build_draft` returns exactly
that shape by contract).  `_polozhit_v_json` below is the one place that reconciles the
two into the row/cell shape the confirmation table renders, so the browser never has to
know which channel a row came from.

🔴 THE FLAKY OUTBOUND LINK (owner's #1 requirement: nothing breaks, nothing is lost).
Text makes no external call at all — pure local fuzzy matching — and cannot be hurt by
the network.  Photo and voice call `infra.llm.VisionModel` / `infra.asr` — both already
carry retries, timeouts and a spend-limit fork (§7 of `infra/llm.py`); that machinery is
read-only for this position and is not re-implemented here.  What this file adds on top
is the one thing infra's retries cannot buy: when every retry is exhausted, the browser
is told plainly what failed, and the ORIGINAL upload the human chose is never touched by
a failed request — the file input and the textarea keep exactly what was in them, so
"попробовать снова" costs one more tap, not retyping or reshooting.

🔴 NO KEY EVER REACHES THIS FILE'S OWN CODE OR LOGS.  `bot.app.build_vision` and
`infra.asr.build_transcriber` read the key from the environment themselves and this file
only ever holds the object they return, never the string.

DELIBERATELY NOT HERE: the "прочерк → явка" (attendance) path `bystryj_tekst.py` already
computes (`attendance_intents`) is shown to the human on a dash-only row — never silently
dropped — but confirming it does not yet write anything: attendance needs a `sessions`
row (a lesson) that no page in this зона creates today, and the criterion tests marks,
not attendance.  Named in `## ВОПРОСЫ`.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
from urllib.parse import parse_qs, urlparse

import config
from core.services import bystryj_tekst, golos, raspoznavanie
from core.services.marking import MarkingError, MarkingService
from infra.asr import TranscriptionUnavailable, build_transcriber
from infra.db import SystemClock
from infra.llm import LlmError
from infra.repositories import SqliteCatalogue, SqliteMarkJournal
from veb import vhod
from veb.obshchee.karkas import e

#: Built through the bot's own factory (`infra.llm.VisionModel` is read-only for this
#: position) so that "photo recognition" means the same thing, configured the same way,
#: on the bot and on this page — one environment, one key, one provider map.
from bot.app import build_vision


def marshruty():
    """Пути этой страницы: {путь: обработчик}."""
    return {
        "/vnesti": stranica_vnesenia,
        "/api/vnesti/tekst": api_tekst,
        "/api/vnesti/foto": api_foto,
        "/api/vnesti/golos": api_golos,
        "/api/vnesti/zapisat": api_zapisat,
    }


# ------------------------------------------------------------------------- helpers


def _soedinenie(h):
    """The server's own per-request connection.  Same device as `veb/priyom.py`'s —
    asking `h` first is what keeps the tests' tmp database working."""
    import sqlite3

    svoj = getattr(h, "_connection", None)
    if callable(svoj):
        return svoj()
    db_path = getattr(getattr(h, "server", None), "db_path", config.DB_PATH)
    raw = sqlite3.connect(str(db_path), check_same_thread=False, isolation_level=None)
    raw.execute("pragma foreign_keys = on")
    raw.execute("pragma journal_mode = WAL")
    raw.execute("pragma synchronous = normal")
    raw.execute("pragma busy_timeout = %d" % config.BUSY_TIMEOUT_MS)
    raw.row_factory = sqlite3.Row
    return raw


def _telo_zaprosa(h) -> dict:
    """The POST body as a dict — JSON only, this door takes no query-string form."""
    dlina = int(h.headers.get("Content-Length", "0") or "0")
    if not dlina:
        return {}
    return json.loads(h.rfile.read(dlina).decode("utf-8"))


def _otdat(h, status: int, telo: bytes, tip: str) -> None:
    h.send_response(status)
    h.send_header("Content-Type", tip)
    h.send_header("Content-Length", str(len(telo)))
    h.end_headers()
    h.wfile.write(telo)


def _otdat_json(h, status: int, payload) -> None:
    _otdat(h, status, json.dumps(payload, ensure_ascii=False).encode("utf-8"),
           "application/json; charset=utf-8")


def _student_label(student) -> str:
    return "%s %s" % (student.surname or "", student.name or "")


def _tekushchij_listok(catalogue):
    """The sheet a fresh draft is read against: the newest one, the lesson's own —
    the same convention `veb/priyom.py._vybrannyj_listok` and `veb/razdely/konduit.py`
    (`_samyj_novyj`) already use for "which sheet is today's".
    """
    listki = catalogue.sheets()
    if not listki:
        return None
    return max(listki, key=lambda sh: sh.ord)


# --------------------------------------------------------------- draft -> wire format


def _golos_draft_to_json(channel: str, draft, students, *, digest=None) -> dict:
    """`golos.Draft` (text's and voice's own shape) -> the wire format."""
    students_by_id = {s.id: s for s in students}
    return {
        "channel": channel,
        "digest": digest if digest is not None else draft.audio_sha256,
        "raw_text": draft.transcript,
        "channels_note": draft.channels,
        "rows": [_golos_row_json(row, students_by_id) for row in draft.rows],
    }


def _golos_row_json(row, students_by_id) -> dict:
    student = students_by_id.get(row.student_id)
    verdict = row.verdict.value if hasattr(row.verdict, "value") else str(row.verdict)
    return {
        "said": row.said,
        "student_id": row.student_id,
        "student_label": _student_label(student) if student is not None else None,
        "verdict": verdict.lower(),
        "alternatives": [
            {"id": sid, "label": _student_label(students_by_id[sid])}
            for sid in row.alternatives if sid in students_by_id
        ],
        "present_no_marks": bool(getattr(row, "present_no_marks", False)),
        "note": row.reason,
        "cells": [
            {
                "label": cell.printed_label or cell.label,
                "problem_id": cell.problem_id,
                "ticked": bool(cell.ticked),
            }
            for cell in row.cells
        ],
    }


def _foto_draft_to_json(rows, digest, raw_text, sheet, problems, students) -> dict:
    """`raspoznavanie.DraftRow` (photo's own flat shape) -> the same wire format."""
    students_by_id = {s.id: s for s in students}
    problems_by_label = {problem.label: problem for problem in problems}
    return {
        "channel": "фото",
        "digest": digest,
        "raw_text": raw_text,
        "channels_note": "лист %s: код + расшифровка бланка" % sheet.number,
        "rows": [_foto_row_json(row, problems_by_label, students_by_id) for row in rows],
    }


def _foto_row_json(row, problems_by_label, students_by_id) -> dict:
    student = students_by_id.get(row.student_id)
    cells = [
        {"label": label, "problem_id": getattr(problems_by_label.get(label), "id", None),
         "ticked": True}
        for label in row.solved
    ] + [
        # Снятое показывается, но НЕ предзачёркнуто как «к записи»: эта позиция пишет
        # только `give`, а «снято» — `MarkingService.retract`, дверь которого сюда не
        # заведена (см. `## ВОПРОСЫ`) — показать находку человеку важнее, чем притвориться,
        # что её нет, но галочка тут не пишущая, поэтому cells отдельно не помечает её как
        # writable; `ticked: False` не даёт её случайно записать как «сдано».
        {"label": label, "problem_id": getattr(problems_by_label.get(label), "id", None),
         "ticked": False, "retracted": True}
        for label in row.retracted
    ]
    verdict = "unknown" if row.state == raspoznavanie.UNKNOWN else row.state
    return {
        "said": row.code or "?",
        "student_id": row.student_id,
        "student_label": _student_label(student) if student is not None else None,
        "verdict": verdict,
        "alternatives": [
            {"id": sid, "label": _student_label(students_by_id[sid])}
            for sid in row.alternatives if sid in students_by_id
        ],
        "present_no_marks": False,
        "note": ("совпадение кода и расшифровки: %.0f%%" % (row.score * 100)
                 if row.student_id is not None else "код не распознан уверенно"),
        "cells": cells,
    }


# ------------------------------------------------------------------------- обработчики


def stranica_vnesenia(h) -> bool:
    """`GET /vnesti` — the three-tab page."""
    if vhod.rol(h.headers) is None:
        _otdat(h, 200, _stranica_vhoda(), "text/html; charset=utf-8")
        return True
    _otdat(h, 200, _obolochka().encode("utf-8"), "text/html; charset=utf-8")
    return True


def api_tekst(h) -> bool:
    """`POST /api/vnesti/tekst` — a typed block, straight through
    `bystryj_tekst.build_draft`.  No external call: this channel cannot be hurt by the
    flaky outbound link.
    """
    if vhod.rol(h.headers) is None:
        _otdat_json(h, 403, {"error": "нужно войти"})
        return True
    try:
        text = str(_telo_zaprosa(h)["text"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        _otdat_json(h, 400, {"error": "нужен text"})
        return True
    if not text.strip():
        _otdat_json(h, 400, {"error": "пустой текст"})
        return True

    c = _soedinenie(h)
    try:
        catalogue = SqliteCatalogue(c)
        students = [s for s in catalogue.students() if (s.status or "") != "left"]
        if not students:
            _otdat_json(h, 400, {"error": "в базе ещё нет школьников"})
            return True
        draft = bystryj_tekst.build_draft(text, students=students, catalogue=catalogue)
    finally:
        c.close()
    _otdat_json(h, 200, _golos_draft_to_json("текст", draft, students))
    return True


def api_foto(h) -> bool:
    """`POST /api/vnesti/foto` — `{data_base64, mime_type}` -> a hypothesis.

    🔴 Every failure that survives `VisionModel`'s own retries (§7 of `infra/llm.py`) is
    caught HERE, before it can become an unhandled exception, and answered with a
    sentence a teacher can read on a phone.  The uploaded bytes were never written to
    disk and are not needed again: they still sit in the browser's own file input,
    untouched by a failed request, so a retry is one more tap.
    """
    if vhod.rol(h.headers) is None:
        _otdat_json(h, 403, {"error": "нужно войти"})
        return True
    try:
        p = _telo_zaprosa(h)
        raw = base64.b64decode(str(p["data_base64"]), validate=True)
    except (KeyError, TypeError, ValueError, binascii.Error, json.JSONDecodeError):
        _otdat_json(h, 400, {"error": "нужен data_base64 — снимок бланка"})
        return True

    try:
        prepared = raspoznavanie.prepare(raw)
    except raspoznavanie.IntakeRefused as otkaz:
        _otdat_json(h, 400, {"error": str(otkaz)})
        return True

    c = _soedinenie(h)
    try:
        catalogue = SqliteCatalogue(c)
        students = [s for s in catalogue.students() if (s.status or "") != "left"]
        sheet = _tekushchij_listok(catalogue)
        if sheet is None:
            _otdat_json(h, 400, {"error": "в базе ещё нет листков"})
            return True
        problems = catalogue.problems_of_sheet(sheet.id)
        if not problems or not students:
            _otdat_json(h, 400, {"error": "в текущем листке ещё нет задач, или нет школьников"})
            return True

        vision, note = build_vision()
        if vision is None:
            _otdat_json(h, 503, {"error": "разбор фото сейчас не настроен: %s" % note})
            return True

        codes = [raspoznavanie.code_for_student(s.id) for s in students]
        labels = [problem.label for problem in problems]
        try:
            answer = vision.read_sheet(prepared.jpeg, codes, labels)
        except LlmError as oshibka:
            # 🔴 THE WHOLE POINT: shown, not swallowed, and the photo the teacher chose
            # is still sitting in their own file input — nothing here discarded it.
            _otdat_json(h, 502, {
                "error": "не удалось распознать снимок: %s — попробуйте ещё раз, "
                         "снимок никуда не делся" % oshibka
            })
            return True

        known_ids = {s.id for s in students}
        rows = raspoznavanie.rows_from_answer(answer, known_ids)
        payload = _foto_draft_to_json(
            rows, prepared.sha256, answer.raw_text, sheet, problems, students
        )
    finally:
        c.close()
    _otdat_json(h, 200, payload)
    return True


def api_golos(h) -> bool:
    """`POST /api/vnesti/golos` — `{data_base64, mime_type}` -> a hypothesis.

    Same failure discipline as `api_foto`: every `TranscriptionUnavailable` that
    survives `infra.asr`'s own handling is caught here and answered plainly; the
    recording stays in the browser's file input, untouched.
    """
    if vhod.rol(h.headers) is None:
        _otdat_json(h, 403, {"error": "нужно войти"})
        return True
    try:
        p = _telo_zaprosa(h)
        raw = base64.b64decode(str(p["data_base64"]), validate=True)
        mime_type = str(p.get("mime_type") or "audio/ogg")
    except (KeyError, TypeError, ValueError, binascii.Error, json.JSONDecodeError):
        _otdat_json(h, 400, {"error": "нужен data_base64 — голосовая запись"})
        return True

    c = _soedinenie(h)
    try:
        catalogue = SqliteCatalogue(c)
        students = [s for s in catalogue.students() if (s.status or "") != "left"]
        sheet = _tekushchij_listok(catalogue)
        if sheet is None or not students:
            _otdat_json(h, 400, {"error": "в базе ещё нет листков, или нет школьников"})
            return True
        problems = catalogue.problems_of_sheet(sheet.id)

        surnames = [s.surname for s in students]
        labels = sorted({golos.normalise_label(problem.label) for problem in problems})
        phrases = golos.build_user_dictionary(surnames, labels)
        transcriber, note = build_transcriber(phrases=phrases)

        digest = hashlib.sha256(raw).hexdigest()
        try:
            transcript = transcriber.transcribe(raw, mime_type=mime_type)
        except TranscriptionUnavailable as oshibka:
            _otdat_json(h, 502, {
                "error": "не удалось распознать запись: %s — попробуйте ещё раз, "
                         "запись никуда не делась" % oshibka
            })
            return True

        draft = golos.build_draft(transcript, students=students, problems=problems)
        payload = _golos_draft_to_json("голос", draft, students, digest=digest)
    finally:
        c.close()
    _otdat_json(h, 200, payload)
    return True


#: `channel` (as this file names it in every draft) -> the source `MarkJournal` rows of
#: it are stamped with.  `config.MARK_SOURCES = ("кнопка", "фото", "голос", "импорт")`
#: has no `"текст"` value — a debt `core/services/bystryj_tekst.py` already names and
#: falls back from (`bystryj_tekst.SOURCE`); this table borrows the same fallback rather
#: than inventing a second one, so the two files cannot drift about what a typed mark's
#: `source` column says.
_ISTOCHNIK = {"текст": bystryj_tekst.SOURCE, "фото": "фото", "голос": "голос"}
_ZAMETKA = {"текст": bystryj_tekst.NOTE}


def api_zapisat(h) -> bool:
    """`POST /api/vnesti/zapisat` — the one door that writes.

    Body: `{channel, digest, cells: [{student_id, problem_id, ticked}, ...]}`.  Only
    cells with BOTH a resolved `student_id` and `ticked: true` are written; everything
    else is silently skipped rather than refused, because an unresolved or unticked row
    is exactly what "показать гипотезу, не записывать" is for — the human decided it not
    to become a mark.
    """
    if vhod.rol(h.headers) is None:
        _otdat_json(h, 403, {"error": "нужно войти"})
        return True
    try:
        p = _telo_zaprosa(h)
        channel = str(p["channel"])
        digest = str(p["digest"])
        cells = list(p["cells"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        _otdat_json(h, 400, {"error": "нужны channel, digest, cells"})
        return True
    istochnik = _ISTOCHNIK.get(channel)
    if istochnik is None:
        _otdat_json(h, 400, {"error": "неизвестный канал %r" % channel})
        return True
    if not digest:
        _otdat_json(h, 400, {"error": "нужен digest — какую попытку распознавания подтверждаем"})
        return True

    zapisano = []
    c = _soedinenie(h)
    try:
        marking = MarkingService(SqliteMarkJournal(c), SystemClock())
        for cell in cells:
            if not isinstance(cell, dict) or not cell.get("ticked"):
                continue
            try:
                student_id = int(cell["student_id"])
                problem_id = int(cell["problem_id"])
            except (KeyError, TypeError, ValueError):
                continue  # неразрешённая строка — не пишем и не отказываем всей пачке
            klyuch = "vnesenie-%s-%s-%s-%s" % (channel, digest, student_id, problem_id)
            try:
                itog = marking.give(
                    student_id, problem_id,
                    source=istochnik,
                    teacher_id=vhod.kto(h.headers),
                    note=_ZAMETKA.get(channel),
                    idempotency_key=klyuch,
                )
            except MarkingError as oshibka:
                zapisano.append({"student_id": student_id, "problem_id": problem_id,
                                 "zapisano": False, "oshibka": str(oshibka)})
                continue
            zapisano.append({"student_id": student_id, "problem_id": problem_id,
                             "sostoyanie": itog.state.value, "zapisano": itog.written})
    finally:
        c.close()
    _otdat_json(h, 200, {"zapisano": zapisano})
    return True


# ------------------------------------------------------------------------------ сборка


def _stranica_vhoda() -> bytes:
    return ('<!doctype html><meta charset="utf-8">'
            '<p>Страница открыта преподавателям. <a href="/vhod">Войти</a>.</p>'
            ).encode("utf-8")


def _obolochka() -> str:
    """The whole page: no external load of any kind — the same choice every page of
    this site makes, so it opens the same way it always has."""
    return """<!doctype html>
<html lang="ru">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Внести задачи · Спецмат</title>
<style>
body{{font-family:sans-serif;max-width:40rem;margin:0 auto;padding:.5rem 1rem 3rem}}
.tabbar{{display:flex;gap:.4rem;margin:.6rem 0}}
.tabbar button{{flex:1;padding:.6rem;font-size:1rem;border:1px solid #ccc;border-radius:8px;
  background:#f4f4f4;cursor:pointer}}
.tabbar button.tek{{background:#333;color:#fff;border-color:#333}}
.vkl{{display:none}}
.vkl.tek{{display:block}}
textarea{{width:100%;min-height:6rem;font-size:1rem;box-sizing:border-box}}
input[type=file]{{width:100%}}
button.go{{margin-top:.5rem;padding:.6rem 1rem;font-size:1rem}}
.oshibka{{color:#a00;white-space:pre-wrap}}
.stroka{{border:1px solid #ddd;border-radius:8px;padding:.5rem .7rem;margin:.5rem 0}}
.stroka.doubtful{{border-color:#c90}}
.stroka.unknown{{border-color:#a00}}
.kto{{font-weight:600}}
.said{{color:#777;font-size:.85rem}}
.note{{color:#777;font-size:.8rem}}
.cell{{display:inline-flex;align-items:center;gap:.2rem;margin:.15rem .4rem .15rem 0;
  padding:.15rem .4rem;border:1px solid #ddd;border-radius:6px}}
.cell.retracted{{color:#a00;border-color:#a00}}
.alt button{{margin:.1rem .3rem .1rem 0}}
#zapisano{{margin-top:1rem}}
</style>
<body>
<header><h1>Внести задачи</h1><a href="/">на сайт</a></header>
<main>
<div class="tabbar">
  <button data-vkl="tekst" class="tek">Текст</button>
  <button data-vkl="foto">Фото</button>
  <button data-vkl="golos">Голос</button>
</div>

<section id="vkl-tekst" class="vkl tek">
  <textarea id="tekst-vvod" placeholder="Петров 3, 5&#10;Иванова 2а, 4&#10;Быков —"></textarea>
  <button class="go" id="tekst-go">Показать гипотезу</button>
</section>

<section id="vkl-foto" class="vkl">
  <input type="file" accept="image/*" id="foto-vvod">
  <button class="go" id="foto-go">Показать гипотезу</button>
</section>

<section id="vkl-golos" class="vkl">
  <input type="file" accept="audio/*" id="golos-vvod">
  <button class="go" id="golos-go">Показать гипотезу</button>
</section>

<div id="oshibka" class="oshibka"></div>
<div id="draft"></div>
<div id="zapisano"></div>
</main>
<script>
(function () {{
  var TEKUSHCHIJ = {{channel: null, digest: null, rowsMeta: []}};

  document.querySelectorAll(".tabbar button").forEach(function (b) {{
    b.addEventListener("click", function () {{
      document.querySelectorAll(".tabbar button").forEach(function (x) {{ x.classList.remove("tek"); }});
      document.querySelectorAll(".vkl").forEach(function (x) {{ x.classList.remove("tek"); }});
      b.classList.add("tek");
      document.getElementById("vkl-" + b.dataset.vkl).classList.add("tek");
    }});
  }});

  function fileToBase64(file) {{
    return new Promise(function (resolve, reject) {{
      var r = new FileReader();
      r.onload = function () {{ resolve(String(r.result).split(",")[1] || ""); }};
      r.onerror = reject;
      r.readAsDataURL(file);
    }});
  }}

  function pokazatOshibku(text) {{
    document.getElementById("oshibka").textContent = text || "";
  }}

  async function poslat(put, telo) {{
    var r = await fetch(put, {{method: "POST", headers: {{"Content-Type": "application/json"}},
                              body: JSON.stringify(telo)}});
    var otvet = await r.json();
    if (!r.ok) {{ throw new Error(otvet.error || ("сервер ответил " + r.status)); }}
    return otvet;
  }}

  function narisovatDraft(otvet) {{
    TEKUSHCHIJ.channel = otvet.channel;
    TEKUSHCHIJ.digest = otvet.digest;
    var holst = document.getElementById("draft");
    if (!otvet.rows.length) {{
      holst.innerHTML = "<p>Ни одной строки не распознано" +
        (otvet.raw_text ? ": «" + escapeHtml(otvet.raw_text) + "»" : "") + ".</p>";
      return;
    }}
    holst.innerHTML = otvet.rows.map(function (row, i) {{
      var kto = row.student_label
        ? "<span class=\\"kto\\">" + escapeHtml(row.student_label) + "</span>"
        : "<span class=\\"kto\\">кто это?</span>";
      var alt = "";
      if (!row.student_id && row.alternatives.length) {{
        alt = "<div class=\\"alt\\">" + row.alternatives.map(function (a) {{
          return "<button type=\\"button\\" data-row=\\"" + i + "\\" data-pick=\\"" + a.id +
                 "\\">" + escapeHtml(a.label) + "</button>";
        }}).join("") + "</div>";
      }}
      var cells = row.cells.map(function (c, j) {{
        var pisat = !!row.student_id && c.problem_id != null && !c.retracted;
        var klass = "cell" + (c.retracted ? " retracted" : "");
        var box = pisat
          ? "<input type=\\"checkbox\\" data-row=\\"" + i + "\\" data-cell=\\"" + j + "\\"" +
            (c.ticked ? " checked" : "") + ">"
          : "";
        return "<label class=\\"" + klass + "\\">" + box + escapeHtml(c.label) +
               (c.retracted ? " (снято)" : (c.problem_id == null ? " (нет такой задачи)" : "")) +
               "</label>";
      }}).join("");
      return "<div class=\\"stroka " + row.verdict + "\\" data-row=\\"" + i + "\\" data-student=\\"" +
        (row.student_id || "") + "\\">" + kto +
        " <span class=\\"said\\">«" + escapeHtml(row.said) + "»</span>" + alt +
        "<div>" + cells + "</div>" +
        (row.present_no_marks ? "<p class=\\"note\\">пришёл, ничего не сдал — " +
          "явка сейчас этой страницей не пишется, только показана</p>" : "") +
        "<p class=\\"note\\">" + escapeHtml(row.note || "") + "</p></div>";
    }}).join("") + '<button class="go" id="zapisat-go">Записать</button>';

    TEKUSHCHIJ.rowsMeta = otvet.rows;
    holst.querySelectorAll("[data-pick]").forEach(function (b) {{
      b.addEventListener("click", function () {{
        var i = +b.dataset.row, id = +b.dataset.pick;
        var chosen = TEKUSHCHIJ.rowsMeta[i].alternatives.find(function (a) {{ return a.id === id; }});
        TEKUSHCHIJ.rowsMeta[i].student_id = id;
        TEKUSHCHIJ.rowsMeta[i].student_label = chosen ? chosen.label : null;
        narisovatDraft({{channel: TEKUSHCHIJ.channel, digest: TEKUSHCHIJ.digest,
                        raw_text: "", rows: TEKUSHCHIJ.rowsMeta}});
      }});
    }});
    document.getElementById("zapisat-go").addEventListener("click", zapisat);
  }}

  function escapeHtml(s) {{
    return String(s).replace(/[&<>"]/g, function (z) {{
      return {{"&": "&amp;", "<": "&lt;", ">": "&gt;", "\\"": "&quot;"}}[z];
    }});
  }}

  async function zapisat() {{
    var cells = [];
    document.querySelectorAll("#draft .stroka").forEach(function (div) {{
      var i = +div.dataset.row, studentId = +div.dataset.student || null;
      var row = TEKUSHCHIJ.rowsMeta[i];
      if (!studentId) {{ return; }}
      div.querySelectorAll("input[type=checkbox]").forEach(function (box) {{
        var j = +box.dataset.cell;
        cells.push({{student_id: studentId, problem_id: row.cells[j].problem_id,
                    ticked: box.checked}});
      }});
    }});
    pokazatOshibku("");
    try {{
      var otvet = await poslat("/api/vnesti/zapisat",
        {{channel: TEKUSHCHIJ.channel, digest: TEKUSHCHIJ.digest, cells: cells}});
      document.getElementById("zapisano").textContent =
        "Записано: " + otvet.zapisano.filter(function (z) {{ return z.zapisano; }}).length +
        " из " + otvet.zapisano.length + " отмеченных клеток.";
    }} catch (oshibka) {{
      pokazatOshibku("Не записалось: " + oshibka.message + " — ничего не потеряно, " +
                     "гипотеза выше осталась, можно нажать «Записать» ещё раз.");
    }}
  }}

  document.getElementById("tekst-go").addEventListener("click", async function () {{
    pokazatOshibku("");
    var text = document.getElementById("tekst-vvod").value;
    try {{ narisovatDraft(await poslat("/api/vnesti/tekst", {{text: text}})); }}
    catch (oshibka) {{ pokazatOshibku(oshibka.message); }}
  }});

  document.getElementById("foto-go").addEventListener("click", async function () {{
    pokazatOshibku("");
    var input = document.getElementById("foto-vvod");
    if (!input.files.length) {{ pokazatOshibku("выберите снимок"); return; }}
    try {{
      var data = await fileToBase64(input.files[0]);
      narisovatDraft(await poslat("/api/vnesti/foto", {{data_base64: data}}));
    }} catch (oshibka) {{ pokazatOshibku(oshibka.message); }}
  }});

  document.getElementById("golos-go").addEventListener("click", async function () {{
    pokazatOshibku("");
    var input = document.getElementById("golos-vvod");
    if (!input.files.length) {{ pokazatOshibku("выберите запись"); return; }}
    try {{
      var data = await fileToBase64(input.files[0]);
      narisovatDraft(await poslat("/api/vnesti/golos",
        {{data_base64: data, mime_type: input.files[0].type || "audio/ogg"}}));
    }} catch (oshibka) {{ pokazatOshibku(oshibka.message); }}
  }});
}})();
</script>
</html>
""".format()
