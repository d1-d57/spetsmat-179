#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-code — the routes below are declared by `marshruty()` and
# collected by `veb.server._marshruty_razdelov` (`RAZDELY_S_MARSHRUTAMI` names this
# module).  No edit of `veb/server.py` is needed for the page to become reachable.
"""Приём задач: the teacher taps a cell and the mark reaches the journal.

WHAT THIS PAGE IS FOR, in the owner's words (07.09): *«мне бы хотелось, чтобы
преподаватели на занятии могли бы ставить плюсики своим детям»*.  It is used standing,
on a phone, during the lesson — not at a desk — and that single fact decides most of the
design: big cells, one tap per mark, an answer that redraws one cell instead of
reloading the page.

🔴 THERE IS NO SECOND JOURNAL HERE, AND THAT IS THE WHOLE POINT.  Every write goes
through `MarkingService` (`give` / `retract`) and every read through `ProgressService`
— the same two doors `veb/razdely/konduit.py` and `tools/export_xlsx.py` already use.
Not one `INSERT` into `marks` lives in this file.  A second journal is declared a
failure of the whole wave in the мандат, and the reason is practical rather than
formal: the service carries idempotency and the reversing link, and a hand-rolled
INSERT reproduces neither.  The disagreement would not show up today — it would show up
the day the numbers stop matching, with nothing left to find it with.

🔴 A RETRACTION ADDS A ROW.  `retract` never deletes the `assert` it takes back: it
appends a new event pointing at it through `reverses_id`, and the state of a cell is the
LAST event of the pair (pupil, problem).  The live journal holds 15 900 events of which
735 are retractions; `data/` is outside git, so a deletion here would be unrecoverable.

🔴 «СВОИ ДЕТИ» IS A DEFAULT, NEVER A PERMISSION — the same choice
`veb/razdely/konduit.py` already made, and for the owner's own reason: he regularly
takes other people's children (`doc/PLAN-veb-2026-09.md:89`).  So one's own pupils are
sorted to the top and coloured, and everybody else is right there below them.

🔴 THE MARKING TEACHER COMES FROM THE COOKIE, and there is no second way of knowing who
is marking: `veb/vhod.py:kto(headers)` returns `teachers.id` for a personal password and
`None` for a shared one.  `None` is not an error — it means "nobody in particular", the
mark is written without a teacher and nobody's pupils are highlighted.

DESIGN IS INHERITED, NOT INVENTED (`doc/DIZAJN-ZAKREPLENO.md` §0).  The palette names,
the cell alphabet and the «только мои» filter all come from what already stands; this
page introduces no colour of its own and changes nothing on any existing page.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import config
from core.models import CellState
from core.services.marking import (
    IdempotencyKeyReused,
    MarkingError,
    MarkingService,
    NothingToReverse,
)
from core.services.progress import ProgressService
from infra.db import SystemClock
from infra.repositories import SqliteCatalogue, SqliteMarkJournal
from veb import vhod
from veb.obshchee.karkas import e
from veb.razdely.lichnaya import deti_na_datu, segodnya

#: `source` of every row this page writes.  The photo channel writes `'фото'` and the
#: import wrote `'импорт'`; a tap is its own channel and says so, because the day someone
#: asks "where did this mark come from" the answer has to be in the row itself.
ISTOCHNIK = "кнопка"

#: What a cell shows.  The alphabet is the кондуит's, not a new one: a tick for credited
#: (the owner's edit of 07.09), `x` for handed in and not credited, empty for nothing.
ZNAK = {CellState.SOLVED: "✓", CellState.RETRACTED: "x", CellState.EMPTY: ""}

#: Which state the next tap aims at.  The service takes a TARGET STATE and never a
#: "toggle" (`core/services/marking.py`), so the button carries where the cell should end
#: up — two taps arriving in either order leave the same cell, not two rows.
SLEDUYUSHCHEE = {
    CellState.EMPTY: CellState.SOLVED,
    CellState.SOLVED: CellState.RETRACTED,
    CellState.RETRACTED: CellState.SOLVED,
}

SOSTOYANIE_PO_IMENI = {s.value: s for s in CellState}


def _nachalo_uchebnogo_goda() -> str:
    """First of September of the CURRENT academic year, as an ISO date.

    🔴 ВОСЬМОЙ КЛАСС НЕ УЧАСТВУЕТ НИ В ВЫБОРЕ ЛИСТКА, НИ В ДОЛГЕ.  Требование
    владельца 07.09: «видны только задачи этого года… учитывать 8 класс в статистике
    точно не нужно».  Прошлогодние листки в базе помечены `issued_at='2025-09-01'`, а
    этого года — сентябрём 2026, так что граница берётся из даты выпуска и никакого
    второго признака «год» заводить не нужно.  Год считается от сентября, а не от
    января: до сентября текущий учебный год — прошлый календарный.
    """
    seychas = datetime.now(ZoneInfo(config.TZ_DISPLAY)).date()
    god = seychas.year if seychas.month >= 9 else seychas.year - 1
    return f"{god}-09-01"


def _listki_goda(listki) -> list:
    """Только листки текущего учебного года, в порядке выдачи."""
    granica = _nachalo_uchebnogo_goda()
    svoi = [sh for sh in listki if (sh.issued_at or "") >= granica]
    # Пустой результат означал бы пустую страницу в первый день учебного года, до
    # выдачи первого листка: тогда честнее показать всё, что есть, чем ничего.
    return sorted(svoi or list(listki), key=lambda sh: sh.ord)


# ----------------------------------------------------------------- объявление маршрутов

def marshruty():
    """Пути этой страницы: {путь: обработчик}. Зовётся сборкой сервера.

    A handler takes the live request handler and returns True when it has answered —
    the contract `veb/server.py` declares above `RAZDELY_S_MARSHRUTAMI`.

    🔴 `/api/priyom` ANSWERS BOTH POST AND GET, AND THE SECOND HALF IS NOT SLOPPINESS.
    The server collects these routes in `do_GET` only; `do_POST` has no such call yet,
    and `veb/server.py` is not this position's zone to add one to.  A page whose writes
    wait for a neighbour's edit is a page that does nothing on the day it was asked for,
    so the write door answers a GET as well and the browser falls back to it when POST
    comes back 404.  Add the same one line to `do_POST` and the fallback stops being
    used, with nothing here to change.
    """
    return {"/priyom": stranica_priyoma, "/api/priyom": otmetka}


# ------------------------------------------------------------------------- обработчики

def stranica_priyoma(h) -> bool:
    """`GET /priyom` — the sheet picker and the grid."""
    zapros = parse_qs(urlparse(h.path).query)
    rol = vhod.rol(h.headers)
    if rol is None:
        _otdat(h, 200, _stranica_vhoda(), "text/html; charset=utf-8")
        return True

    c = _soedinenie(h)
    try:
        telo = _sobrat_stranicu(c, vhod.kto(h.headers), zapros)
    finally:
        c.close()
    _otdat(h, 200, telo, "text/html; charset=utf-8")
    return True


def otmetka(h) -> bool:
    """`/api/priyom` — one tap: bring one cell into the target state, answer with it.

    The answer is the state the cell stands at NOW, whether or not this request is what
    put it there: the button redraws itself from the answer, so a request that changed
    nothing must still tell the truth about the cell.
    """
    if vhod.rol(h.headers) is None:
        _otdat_json(h, 403, {"error": "нужно войти"})
        return True

    try:
        p = _telo_zaprosa(h)
        student_id = int(p["student"])
        problem_id = int(p["problem"])
        target = SOSTOYANIE_PO_IMENI[str(p["target"])]
    except (KeyError, TypeError, ValueError):
        _otdat_json(h, 400, {"error": "нужны student, problem, target"})
        return True

    c = _soedinenie(h)
    try:
        marking = MarkingService(SqliteMarkJournal(c), SystemClock())
        try:
            itog = marking.set_state(
                student_id,
                problem_id,
                target,
                source=ISTOCHNIK,
                teacher_id=vhod.kto(h.headers),
                idempotency_key=_klyuch(student_id, problem_id, target),
            )
        except NothingToReverse:
            # Two teachers tapped the same empty cell and the other one's retraction
            # landed first.  Nothing to take back is not a server fault: answer with the
            # cell as it stands so the button stops disagreeing with the journal.
            sostoyanie = _sostoyanie_kletki(c, student_id, problem_id)
            _otdat_json(h, 200, {"sostoyanie": sostoyanie.value, "zapisano": False,
                                 "pochemu": "снимать нечего"})
            return True
        except (IdempotencyKeyReused, MarkingError) as oshibka:
            _otdat_json(h, 409, {"error": str(oshibka)})
            return True
        _otdat_json(h, 200, {"sostoyanie": itog.state.value,
                             "zapisano": itog.written, "pochemu": itog.reason})
    finally:
        c.close()
    return True


# ------------------------------------------------------------------------------ сборка

def _sobrat_stranicu(c, teacher_id, zapros) -> bytes:
    """The whole page: picker, grid, and the script that redraws one cell."""
    catalogue = SqliteCatalogue(c)
    progress = ProgressService(SqliteMarkJournal(c), catalogue)

    vse_listki = catalogue.sheets()
    if not vse_listki:
        return _obolochka("<p class=\"net\">в базе ещё нет листков</p>").encode("utf-8")
    listki = _listki_goda(vse_listki)
    svoi_listki = {sh.id for sh in listki}
    listok = _vybrannyj_listok(listki, zapros)

    zadachi = catalogue.problems_of_sheet(listok.id)
    deti = _deti(c, catalogue, teacher_id)
    svoi = {r["id"] for r in deti_na_datu(c, teacher_id, segodnya())} if teacher_id else set()
    prepody = _prepodavateli(c, segodnya())
    sostoyaniya = progress.states_for_many(
        [u.id for u in deti], [z.id for z in zadachi]
    )
    # Долг — только по листкам ЭТОГО года: `debts` честно считает от первого листка
    # ученика, то есть с прошлогодних тоже, и давал числа под шестьдесят — весь 8 класс
    # разом.  Владелец 07.09: «учитывать 8 класс в статистике точно не нужно».
    dolgi = {u.id: len([z for z in progress.debts(u.id, listok.ord)
                        if z.sheet_id in svoi_listki])
             for u in deti}

    telo = (_vybor(listki, listok)
            + _reshyotka(listok, zadachi, deti, svoi, prepody, dolgi, sostoyaniya))
    return _obolochka(telo).encode("utf-8")


def _vybrannyj_listok(listki, zapros):
    """The sheet from the query, else the newest one — that is the lesson's sheet."""
    prosili = zapros.get("listok", [""])[0]
    if prosili.isdigit():
        for sh in listki:
            if sh.id == int(prosili):
                return sh
    return max(listki, key=lambda sh: sh.ord)


def _deti(c, catalogue, teacher_id) -> list:
    """Everybody on the roll, one's own pupils first.

    🔴 «ТОЛЬКО МОИ» IS A SORT, NOT A FILTER OF THE QUERY.  Other people's children are
    on the page and can be marked; they simply stand below one's own.  The predicate for
    "on the roll" is the one every other list of pupils on this site uses
    (`veb/razdely/shkolniki`, `veb/razdely/konduit`): everybody whose status is not
    'left'.
    """
    na_uchyote = [s for s in catalogue.students()
                  if (getattr(s, "status", None) or "") != "left"]
    svoi = {r["id"] for r in deti_na_datu(c, teacher_id, segodnya())} if teacher_id else set()
    return sorted(na_uchyote, key=lambda s: (s.id not in svoi, s.surname or "", s.name or ""))


def _prepodavateli(c, den: str) -> dict:
    """`{student_id: teacher name}` — who takes this pupil today.

    A pupil attends one or two slots and may hold two open rows; the names are joined
    rather than one of them silently winning, because the teacher reading the row has to
    recognise their own name in it.
    """
    ryady = c.execute(
        """
        select e.student_id as sid, t.name as name
        from enrollment e
        join teachers t on t.id = e.teacher_id
        where e.valid_from <= ? and ? < e.valid_to
        order by t.name
        """,
        (den, den),
    ).fetchall()
    po_detyam: dict = {}
    for r in ryady:
        imena = po_detyam.setdefault(r["sid"], [])
        if r["name"] not in imena:
            imena.append(r["name"])
    return {sid: ", ".join(imena) for sid, imena in po_detyam.items()}


def _vybor(listki, vybran) -> str:
    """The sheet picker: every sheet, the open one marked."""
    knopki = []
    for sh in sorted(listki, key=lambda s: s.ord):
        klass = " class=\"tek\"" if sh.id == vybran.id else ""
        knopki.append(f'<a href="/priyom?listok={sh.id}"{klass}>{e(sh.number)}</a>')
    return f'<nav class="listki">{"".join(knopki)}</nav>'


def _reshyotka(listok, zadachi, deti, svoi, prepody, dolgi, sostoyaniya) -> str:
    """The grid: a row per pupil, a column per problem.

    🔴 ДОЛГ И ПРИНИМАЮЩИЙ ПРЕПОДАВАТЕЛЬ СТОЯТ НА ТОЙ ЖЕ СТРОКЕ, ЧТО И УЧЕНИК.  Named
    word for word as a failure condition of the wave in the мандат, and the reason is the
    lesson itself: the teacher looks at one line and sees this child is mine and owes
    this much.  Splitting them across two places is what the paper conduit did badly.
    """
    if not zadachi:
        return '<p class="net">в этом листке ещё нет задач</p>'

    shapka = "".join(f'<th class="zn">{e(z.label)}</th>' for z in zadachi)
    stroki = []
    for u in deti:
        kletki = []
        for z in zadachi:
            sostoyanie = sostoyaniya[(u.id, z.id)]
            kletki.append(
                f'<td><button class="kl {sostoyanie.value}" type="button"'
                f' data-u="{u.id}" data-z="{z.id}"'
                f' aria-label="{e(u.surname)} · {e(z.label)}">'
                f'{ZNAK[sostoyanie]}</button></td>')
        dolg = dolgi.get(u.id, 0)
        klass = ' class="moi"' if u.id in svoi else (' class="chuzh"' if svoi else "")
        stroki.append(
            f'<tr{klass}>'
            f'<td class="kto"><b>{e(u.surname)}</b> '
            f'<span class="imya">{e(u.name)}</span>'
            f'<span class="inic">{e((u.name or " ")[0])}.</span></td>'
            f'<td class="prep">{e(prepody.get(u.id, "—"))}</td>'
            f'<td class="dolg">{_dolg(dolg)}</td>'
            f'{"".join(kletki)}</tr>')

    return (f'<p class="zag2">{e(listok.title or listok.number)}</p>'
            f'<table class="setka">'
            f'<thead><tr><th>Ученик</th><th>Принимает</th><th>Долг</th>{shapka}</tr></thead>'
            f'<tbody>{"".join(stroki)}</tbody></table>')


def _dolg(skolko: int) -> str:
    """The debt count, silent at zero: a column of noughts reads as noise."""
    return f'<span class="est">{skolko}</span>' if skolko else '<span class="net0">·</span>'


# ------------------------------------------------------------------------- обвязка HTTP

def _obolochka(telo: str) -> str:
    """The page around the grid.  No external load of any kind: it opens on a phone in a
    classroom, and the кондуит made the same choice for the same reason."""
    return f"""<!doctype html>
<html lang="ru">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Приём задач · Спецмат</title>
<link rel="stylesheet" href="/static/priyom.css">
<body>
<header class="verh">
  <h1>Приём задач</h1>
  <a class="vyh" href="/">на сайт</a>
</header>
<main class="holst">
{telo}
</main>
<script>
// One tap: send the TARGET state, redraw the cell from the answer.  The target is
// computed from what the cell shows, because the service takes a state and never a
// toggle -- two taps arriving in either order then leave the same cell.
var DALEE = {{"empty":"solved","solved":"retracted","retracted":"solved"}};
var ZNAK = {{"empty":"","solved":"\\u2713","retracted":"x"}};
function narisovat(k, s) {{
  k.className = "kl " + s;
  k.textContent = ZNAK[s];
}}
async function poslat(k) {{
  var bylo = k.className.replace("kl ", "").split(" ")[0];
  var target = DALEE[bylo] || "solved";
  var telo = {{student: +k.dataset.u, problem: +k.dataset.z, target: target}};
  k.disabled = true;
  narisovat(k, target);                       // ответ обычно быстрее взгляда
  try {{
    var r = await fetch("/api/priyom", {{
      method: "POST", headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify(telo)}});
    if (r.status === 404 || r.status === 405) {{
      // `do_POST` ещё не зовёт реестр разделов — та же дверь через GET.
      r = await fetch("/api/priyom?student=" + telo.student
                      + "&problem=" + telo.problem + "&target=" + telo.target);
    }}
    var otvet = await r.json();
    if (otvet.sostoyanie) {{ narisovat(k, otvet.sostoyanie); }}
    else {{ narisovat(k, bylo); k.title = otvet.error || "не записалось"; }}
  }} catch (oshibka) {{
    narisovat(k, bylo);                       // сеть отвалилась — клетка не врёт
    k.title = "не записалось: " + oshibka;
  }}
  k.disabled = false;
}}
document.addEventListener("click", function (sob) {{
  var k = sob.target.closest(".kl");
  if (k) {{ poslat(k); }}
}});
</script>
</html>
"""


def _stranica_vhoda() -> bytes:
    """No cookie: say so and point at the entry, without showing a single name."""
    return (_obolochka(
        '<p class="net">Страница приёма открыта преподавателям. '
        '<a href="/vhod">Войти</a>.</p>').encode("utf-8"))


def _soedinenie(h) -> sqlite3.Connection:
    """The server's own per-request connection, or an identical one when it has none.

    Asking `h` first is what keeps the tests' tmp database working: the fixture puts the
    path on the server object, and the pragmas that make WAL and the busy timeout right
    live in `veb/server.py` — repeating them from memory here is how two connections
    start behaving differently.
    """
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
    """The tap's three values, from a JSON body or from the query string."""
    dlina = int(h.headers.get("Content-Length", "0") or "0")
    if dlina:
        return json.loads(h.rfile.read(dlina).decode("utf-8"))
    zapros = parse_qs(urlparse(h.path).query)
    return {k: v[0] for k, v in zapros.items()}


def _klyuch(student_id: int, problem_id: int, target: CellState) -> str:
    """Idempotency key of one tap — its own shape, never the photo channel's.

    The photo channel keys a cell and a day (`<student>-<problem>-<date>`), which is
    right for it: one photo of one workbook page is one delivery.  A tap is not — the
    same teacher may credit, take back and credit again within a lesson, and a key that
    coarse would answer the third tap from the first tap's row and leave the button
    doing nothing.  So the key carries the target state and the second: a double click
    is one delivery, a deliberate second tap is another.
    """
    mig = datetime.now(ZoneInfo(config.TZ_DISPLAY)).strftime("%Y%m%dT%H%M%S")
    return f"{ISTOCHNIK}-{student_id}-{problem_id}-{target.value}-{mig}"


def _sostoyanie_kletki(c, student_id: int, problem_id: int) -> CellState:
    """What the cell stands at now, asked of the one service that reads the journal."""
    progress = ProgressService(SqliteMarkJournal(c), SqliteCatalogue(c))
    return progress.states_for(student_id, [problem_id])[problem_id]


def _otdat(h, status: int, telo: bytes, tip: str) -> None:
    h.send_response(status)
    h.send_header("Content-Type", tip)
    h.send_header("Content-Length", str(len(telo)))
    h.end_headers()
    h.wfile.write(telo)


def _otdat_json(h, status: int, payload) -> None:
    _otdat(h, status, json.dumps(payload, ensure_ascii=False).encode("utf-8"),
           "application/json; charset=utf-8")
