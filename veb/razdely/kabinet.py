#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-code — the two routes below are declared by `marshruty()` and
# collected by `veb.server._marshruty_razdelov` (`RAZDELY_S_MARSHRUTAMI`), the same seam
# `veb/razdely/istoria.py` and `veb/razdely/istoria_zanyatij.py` already use.
"""Кабинет преподавателя: где я, кто ко мне идёт, и когда меня не будет.

WHAT THE OWNER ASKED FOR, 09.09, in his own words: *«когда я нажимаю Вход, я попадаю не
на страницу класс, в которой куча информации, которая мне не нужна, и не на страницу
листки-распределение-кондуит, а на какой-то свой личный кабинет… в котором я вижу, когда
у меня следующий спецмат, какой там будет листок и какие у меня школьники на следующий
спецмат»*.  And the new thing he asked for in the same breath: *«в этом личном кабинете
можно будет отметить, что меня не будет в такое-то число.  То есть в будущем я могу
поставить крестик в будущие клеточки… И это будет у нас в системе отмечаться, и мы будем
знать автоматически на вкладке распределение на такую-то дату, что этого человека нету
просто.  Там будет написано „отсутствует“, и это будет уже заморожено, потому что это
человек сказал»*.

🔴 THIS IS A STANDALONE PAGE, NOT A SIXTH SHELL TAB, AND THAT IS A ZONE CONSTRAINT, NOT A
DESIGN CHOICE — the same sentence `veb/razdely/istoria_zanyatij.py` opens with, for the
same reason and one заход later.  The menu row, the radio inputs behind it and the
capability table `VOZMOZHNOSTI` all live in `veb/obshchee/karkas.py::obolochka()`, outside
this заход's zone (`veb/razdely/` `veb/server.py` `core/services/` `tests/veb/`), and a
wave of twelve sequential positions shares that file.  The codebase's own resolution of
this collision is on record twice — `veb/razdely/kartochka.py` and
`veb/razdely/istoria_zanyatij.py` — and it is followed here: own route, own document, and
the missing menu label recorded as a debt.  What the owner actually asked for is not
lost by that: `POST /vhod` in `veb/server.py` now lands a person who signed in with a
PERSONAL password on `/kabinet`, and `veb/razdely/glavnaya.py` puts a «Мой кабинет →»
link under the front-page card so the page is reachable after he navigates away.

🔴 NOTHING HERE ASKS THE BASE A QUESTION SOMEBODY ELSE ALREADY ANSWERS.
  * room and pupils — `veb/razdely/lichnaya.kabinet_na_datu` / `deti_na_datu`, whose own
    docstring names the three properties of `enrollment` these two queries turn on (an
    open row is `9999-12-31` and never `NULL`; some open rows start in the FUTURE; a
    calendar day has no reliable slot, so the pupils are a UNION over slots).  Writing a
    second pair of queries here would be a second answer to a question already answered.
  * which dates are lesson days — `core.services.sostav_na_den.blizhajshie_zanyatiya`,
    which is the one place `SLOTY_ZANYATIJ` is consulted.
  * the sheet — `veb/razdely/listki.tekushchij`, the same call the front page makes.
  * the palette — `veb/razdely/list_odin._obshchij_stil`, the site's own `<style>`,
    never a copy of the colours (`doc/DIZAJN-ZAKREPLENO.md §2`).

🔴 «ОТСУТСТВУЕТ» IS WRITTEN INTO THE TABLE THAT ALREADY HOLDS IT, AND THAT IS WHY THE
DISTRIBUTION SCREEN NEEDED NO CHANGE AT ALL.  `teacher_attendance(session_id, teacher_id,
status)` is where `veb/server.py::_post_zanyatie` already puts the organiser's
«отсутствует» tick, and `karkas.sobrat_kontekst` already reads it back into
`Kontekst.otsutstvuyut_prepoda`, which is what prints the word on
`/raspredelenie?den=…`.  A teacher ticking a future cell here writes the identical row.
One fact, one table, two doors — and the freeze that guards it lives in `core/`
(`EnrollmentService`, `TeacherAbsentOnDay`) plus the lesson-layer door in
`veb/server.py`, so a page reload cannot reach the write a greyed-out control refused.

🔴 THE DOOR IS ITS OWN, AND NOT `/api/zanyatie`.  That route is behind
`_pravka_zapreshchena()` — «правит только организатор» — and a teacher would get 403 on
it.  The route below writes ONE person's row: the person named by the cookie, never a
`teacher_id` taken from the body.  A teacher cannot mark a colleague absent, and there is
nothing in the request for him to try it with.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import config
from core.services.sostav_na_den import (
    OTSUTSTVUET,
    blizhajshie_zanyatiya,
    slot_of,
)
from veb import vhod
from veb.obshchee.karkas import VREMYA, e
from veb.razdely.lichnaya import deti_na_datu, kabinet_na_datu, segodnya
from veb.razdely.list_odin import _obshchij_stil

#: How many lessons forward the grid of future absences shows.  Eight is four calendar
#: weeks of two lessons: the owner's own horizon in the same sentence — *«мы знаем, что
#: школьник или преподаватель будет отсутствовать в течение месяца»* — and short enough
#: that the grid stays one screen a person reads at a glance rather than scrolls.
GLUBINA_VPERYOD = 8

#: Which of the two lesson slots a Monday is, so the row can say «пн» / «чт» without a
#: second calendar of its own.  `sostav_na_den.SLOTY_ZANYATIJ` maps the ISO weekday to the
#: slot; this maps it to the word, and both are read from the ONE place that has it.
IMYA_DNYA = {1: "понедельник", 4: "четверг"}
KOROTKO_DNYA = {1: "пн", 4: "чт"}
MESYACY = ("января", "февраля", "марта", "апреля", "мая", "июня",
           "июля", "августа", "сентября", "октября", "ноября", "декабря")


def po_russki(iso: str) -> str:
    """`2026-09-10` → `10 сентября`.  Same spelling as `Kontekst.po_russki`.

    Not imported from `Kontekst`: that method belongs to a value built by reading the
    whole база for a page of the shell, and this page builds no `Kontekst`.  The month
    table is the one in `veb/obshchee/karkas.py`, copied deliberately and named here as
    a copy — `## ВОПРОСЫ` of this заход asks for the two to be given one home, which is
    a правка to `karkas.py` and therefore outside this зона.
    """
    _, mes, den = (int(x) for x in iso.split("-"))
    return "%d %s" % (den, MESYACY[mes - 1])


def imya_prepoda(c: sqlite3.Connection, teacher_id: int):
    """`(name, gruppa)` of one teacher, or `None`.

    🔴 `gruppa` ASKED SEPARATELY BECAUSE THE COLUMN IS NOT IN THE SCHEMA. Migrations
    give `teachers` only `id, tg_id, name, aka, is_owner`; `gruppa`, `kabinet` and
    `aktiven` are added at runtime by `veb/server.py` (`_obespechit_aktivnost` and its
    neighbours). A `select name, gruppa` therefore works on the live база and throws
    `no such column` on a база built from migrations alone — which is every test
    fixture, and would be every fresh deployment.
    """
    ryad = c.execute("select * from teachers where id = ?", (teacher_id,)).fetchone()
    if ryad is None:
        return None
    stolbcy = ryad.keys()
    return {"name": ryad["name"],
            "gruppa": ryad["gruppa"] if "gruppa" in stolbcy else None}


def _vremya(den: str) -> str:
    """The hours of the lesson on this date, from the ONE place the site keeps them.

    `karkas.VREMYA` is keyed `"pn"` / `"cht"`; the key is derived from the date rather
    than written down, so a date that is not a lesson day has no hours and says so.
    """
    wd = date.fromisoformat(den).isoweekday()
    return VREMYA.get({1: "pn", 4: "cht"}.get(wd, ""), "")


def otsutstviya(c: sqlite3.Connection, teacher_id: int, dni) -> set:
    """Which of these dates this teacher is already marked absent on.

    One query for the whole grid rather than one per date: the grid is eight rows today
    and the query is the same shape whatever `GLUBINA_VPERYOD` becomes.
    """
    if not dni:
        return set()
    mesta = ",".join("?" * len(dni))
    ryady = c.execute(
        "select s.held_on as den from teacher_attendance ta "
        "join sessions s on s.id = ta.session_id "
        "where ta.teacher_id = ? and ta.status = ? and s.held_on in (%s)" % mesta,
        (teacher_id, OTSUTSTVUET, *dni),
    ).fetchall()
    return {r["den"] for r in ryady}


# ------------------------------------------------------------------------- разметка


SVOI_STILI = """
/* Кабинет: одна колонка в меру ширины читаемой строки, крупно — эту страницу
   читают стоя, посреди занятия, с телефона в руке. Все цвета — переменные
   каркаса, ни одного своего. */
.kab-stranica{max-width:60rem;margin:0 auto;padding:1.6rem 2rem 4rem}
.kab-stranica h1{margin:0 0 .2rem}
.kab-kto{font-family:var(--sans);color:var(--muted);margin:0 0 2rem;font-size:1.05rem}
.kab-blok{background:var(--panel);border:1px solid var(--rule);border-radius:16px;
  padding:1.4rem 1.7rem;margin:0 0 1.6rem}
.kab-kogda{font-family:var(--sans);font-size:1.5rem;font-weight:600;margin:.2rem 0 0}
.kab-listok{font-family:var(--sans);font-size:2rem;font-weight:600;margin:.5rem 0 0}
.kab-gde{font-family:var(--sans);font-size:1.25rem;margin:.7rem 0 0;color:var(--muted)}
.kab-gde .kab{font-size:1.5rem}
.kab-deti{display:grid;grid-template-columns:repeat(auto-fill,minmax(15rem,1fr));
  gap:.1rem 2rem;margin:1rem 0 0}
.kab-deti div{padding:.35rem 0;border-bottom:1px solid var(--rule);font-size:1.2rem}
.kab-ssylki{display:flex;gap:.7rem;flex-wrap:wrap;margin:0 0 2rem}
.kab-ssylki a{font-family:var(--sans);font-weight:600;font-size:1.05rem;
  color:var(--accent);text-decoration:none;padding:.5em 1.1em;border-radius:10px;
  background:var(--accent-soft)}
.kab-ssylki a:hover{text-decoration:underline}
/* Сетка будущих занятий: строка на занятие, крестик слева, дата справа от него.
   Отмеченная строка гасится и подписывается словом — «отсутствует» это то самое
   слово, которым то же состояние названо на распределении. */
.kab-setka{margin:.8rem 0 0}
.kab-ryad{display:flex;align-items:center;gap:1rem;padding:.7rem .2rem;
  border-bottom:1px solid var(--rule);font-family:var(--sans);font-size:1.2rem}
.kab-ryad input{width:1.4rem;height:1.4rem;flex:0 0 auto;cursor:pointer;
  accent-color:var(--krasn)}
.kab-ryad .kab-data{flex:1 1 auto;min-width:0}
.kab-ryad .kab-chas{color:var(--muted);font-size:1rem;flex:0 0 auto}
.kab-ryad .kab-slovo{color:var(--krasn);font-weight:600;flex:0 0 auto;
  font-size:1rem;visibility:hidden}
.kab-ryad.netu .kab-data{color:var(--muted);text-decoration:line-through}
.kab-ryad.netu{background:var(--krasn-fon);border-radius:8px}
.kab-ryad.netu .kab-slovo{visibility:visible}
.kab-beda{color:var(--krasn);font-family:var(--sans);font-size:1rem;margin:.8rem 0 0;
  min-height:1.2em}
@media(max-width:640px){.kab-stranica{padding:1.1rem 1rem 3rem}
  .kab-listok{font-size:1.6rem}}
"""

#: The tick writes at once, exactly as the lesson screen does — the owner's ruling of
#: 07.09 about that screen («там просто нужно сразу сохраняться») is about the same kind
#: of correction and there is no reason for this one to grow a Save button.  A refused
#: write puts the checkbox back where it was: an unchecked box that the server rejected
#: would otherwise read as «сохранено».
SKRIPT = """
<script>
document.querySelectorAll('.kab-ryad input').forEach(function(fl){
  fl.addEventListener('change', function(){
    var ryad = fl.closest('.kab-ryad');
    var beda = document.getElementById('kab-beda');
    beda.textContent = '';
    ryad.classList.toggle('netu', fl.checked);
    fetch('/api/kabinet/otsutstvie', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({den: fl.dataset.den, net: fl.checked ? 1 : 0})
    }).then(function(o){ return o.json().then(function(j){ return [o.ok, j]; }); })
      .then(function(p){
        if (!p[0]) {
          fl.checked = !fl.checked;
          ryad.classList.toggle('netu', fl.checked);
          beda.textContent = p[1].error || 'не сохранилось';
        }
      })
      .catch(function(){
        fl.checked = !fl.checked;
        ryad.classList.toggle('netu', fl.checked);
        beda.textContent = 'не сохранилось: сеть недоступна';
      });
  });
});
</script>"""


def stranica(c: sqlite3.Connection, teacher_id: int) -> str:
    """The whole page for one named teacher."""
    from veb.razdely.listki import tekushchij

    kto = imya_prepoda(c, teacher_id)
    if kto is None:
        return _dokument("Кабинет", '<div class="kab-stranica">'
                                    '<h1>Кабинет</h1>'
                                    '<p class="net">Такого преподавателя нет в базе.</p>'
                                    '</div>')

    dni = blizhajshie_zanyatiya(segodnya(), GLUBINA_VPERYOD)
    net_na = otsutstviya(c, teacher_id, dni)
    blizhajshee = dni[0] if dni else None

    # ── СЛЕДУЮЩЕЕ ЗАНЯТИЕ. Оно же первое в сетке ниже: два ответа об одном дне
    # берутся из одного списка, а не из двух вычислений, которые однажды разойдутся.
    if blizhajshee is None:
        blok_blizh = ('<div class="kab-blok"><p class="net">'
                      'ближайшее занятие не найдено</p></div>')
    else:
        wd = date.fromisoformat(blizhajshee).isoweekday()
        kab = kabinet_na_datu(c, teacher_id, blizhajshee)
        deti = deti_na_datu(c, teacher_id, blizhajshee)
        nomer, tema, _versii = tekushchij()
        listok = ("%s · %s" % (e(nomer), e(tema))) if tema else "листок пока не назван"
        kab_html = (f'<span class="kab">{e(kab)}</span>' if kab
                    else '<span class="net">кабинет не назначен</span>')
        if blizhajshee in net_na:
            # Он сам сказал, что его не будет: список школьников на этот день — не
            # то, что ему нужно видеть, и показывать его значило бы спорить с его же
            # отметкой. Ниже, в сетке, эта строка перечёркнута тем же словом.
            deti_html = ('<p class="kab-gde">вы отметили, что вас не будет '
                         'на этом занятии</p>')
        elif deti:
            deti_html = ('<div class="kab-deti">'
                         + "".join('<div><b>%s</b> %s</div>'
                                   % (e(r["surname"]), e(r["name"])) for r in deti)
                         + "</div>")
        else:
            deti_html = '<p class="net">на это занятие школьников пока нет</p>'
        blok_blizh = (
            '<div class="kab-blok">'
            '<p class="zag2">следующий спецмат</p>'
            f'<p class="kab-kogda">{e(IMYA_DNYA.get(wd, ""))}, '
            f'{e(po_russki(blizhajshee))} · {_vremya(blizhajshee)}</p>'
            f'<p class="kab-listok">{listok}</p>'
            f'<p class="kab-gde">кабинет {kab_html}</p>'
            f'{deti_html}</div>')

    # ── СЕТКА БУДУЩИХ ЗАНЯТИЙ. Крестик в клетку — «меня не будет».
    ryady = []
    for den in dni:
        wd = date.fromisoformat(den).isoweekday()
        netu = den in net_na
        ryady.append(
            f'<label class="kab-ryad{" netu" if netu else ""}">'
            f'<input type="checkbox" data-den="{e(den)}"{" checked" if netu else ""}>'
            f'<span class="kab-data">{e(KOROTKO_DNYA.get(wd, ""))} '
            f'{e(po_russki(den))}</span>'
            f'<span class="kab-chas">{_vremya(den)}</span>'
            f'<span class="kab-slovo">отсутствует</span></label>')

    telo = f"""<div class="kab-stranica">
  <h1>{e(kto["name"])}</h1>
  <p class="kab-kto">кабинет преподавателя{
      ' · группа ' + e(kto["gruppa"]) if kto["gruppa"] else ''}</p>
  {blok_blizh}
  <div class="kab-ssylki">
    <a href="/istoria">Моя история занятий</a>
    <a href="/raspredelenie">Распределение на занятие</a>
    <a href="/">На заглавную</a>
  </div>
  <div class="kab-blok">
    <p class="zag2">когда меня не будет</p>
    <p class="kab-gde">Поставьте крестик в занятие, на которое вы не придёте.
      Отметка сохраняется сразу; на распределении на эту дату вы будете отмечены
      отсутствующим, и школьников вам на этот день назначить будет нельзя.</p>
    <div class="kab-setka">{"".join(ryady)}</div>
    <p class="kab-beda" id="kab-beda"></p>
  </div>
</div>{SKRIPT}"""
    return _dokument("Кабинет — " + kto["name"], telo)


def _dokument(zagolovok: str, telo: str) -> str:
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(zagolovok)}</title>
<style>{_obshchij_stil()}{SVOI_STILI}</style></head>
<body>
{telo}
</body></html>"""


# ------------------------------------------------------------------------- обвязка HTTP


def _soedinenie(h) -> sqlite3.Connection:
    """Соединение сервера, а при его отсутствии — точно такое же.

    Тот же приём, что уже стоит в `veb/razdely/istoria.py::_soedinenie` и
    `veb/razdely/istoria_zanyatij.py`: фикстура тестов кладёт путь на объект сервера, а
    прагмы WAL/busy_timeout живут в `veb/server.py`.
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


def _otdat_html(h, status: int, telo: str) -> None:
    telo_bytes = telo.encode("utf-8")
    h.send_response(status)
    h.send_header("Content-Type", "text/html; charset=utf-8")
    h.send_header("Content-Length", str(len(telo_bytes)))
    h.end_headers()
    h.wfile.write(telo_bytes)


def _otdat_json(h, status: int, payload) -> None:
    telo = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    h.send_response(status)
    h.send_header("Content-Type", "application/json; charset=utf-8")
    h.send_header("Content-Length", str(len(telo)))
    h.end_headers()
    h.wfile.write(telo)


def _telo(h) -> dict:
    dlina = int(h.headers.get("Content-Length", "0") or "0")
    if dlina:
        return json.loads(h.rfile.read(dlina).decode("utf-8"))
    return {k: v[0] for k, v in parse_qs(urlparse(h.path).query).items()}


def pokazat_kabinet(h) -> bool:
    """`/kabinet` — своя страница вошедшего.

    🔴 ТОЛЬКО ЛИЧНЫЙ ПАРОЛЬ, И ЭТО НЕ СТРОГОСТЬ РАДИ СТРОГОСТИ. Два общих пароля
    принадлежат никому в частности (`veb/vhod.py::proverit_parol` отвечает `uid = None`
    для них), а страница целиком про «моё»: и кабинет, и фамилии школьников, и отметка,
    которую человек ставит ЗА СЕБЯ. Страница, угадавшая в этом месте, показала бы
    одному преподавателю чужих детей и дала бы ему отметить чужое отсутствие.
    """
    kto = vhod.kto(h.headers)
    if vhod.rol(h.headers) is None:
        _otdat_html(h, 403, _dokument(
            "Кабинет", '<div class="kab-stranica"><h1>Кабинет</h1>'
            '<p class="net">Нужно войти.</p>'
            '<div class="kab-ssylki"><a href="/vhod">Вход</a></div></div>'))
        return True
    if kto is None:
        _otdat_html(h, 200, _dokument(
            "Кабинет", '<div class="kab-stranica"><h1>Кабинет</h1>'
            '<p class="net">Вход по общему паролю: система не знает, кто именно вошёл. '
            'Свой кабинет, своих школьников и отметку отсутствия показывает личный '
            'пароль.</p>'
            '<div class="kab-ssylki"><a href="/">На заглавную</a></div></div>'))
        return True
    c = _soedinenie(h)
    try:
        _otdat_html(h, 200, stranica(c, kto))
    finally:
        c.close()
    return True


def otmetit_otsutstvie(h) -> bool:
    """`/api/kabinet/otsutstvie` — «меня не будет» на одну дату, за себя.

    🔴 ЧЕЛОВЕК БЕРЁТСЯ ИЗ КУКИ, А НЕ ИЗ ТЕЛА ЗАПРОСА, И ПОЛЯ `teacher_id` ЗДЕСЬ НЕТ
    ВОВСЕ. Дверь открыта каждому вошедшему личным паролем — то есть всем пятнадцати
    принимающим, а не только организаторам, — и поле с чужим номером было бы способом
    отметить отсутствие коллеги. Отсутствующего поля не подделать.

    🔴 ПРОШЕДШЕЕ ЗАНЯТИЕ ОТМЕТИТЬ НЕЛЬЗЯ. Владелец просил отметку ВПЕРЁД («я могу
    поставить крестик в будущие клеточки»); прошлое — это уже история посещений, её
    ведёт `/istoria` по факту, а не по обещанию. День САМОГО занятия остаётся
    открытым: сказать утром «сегодня меня не будет» — обычный случай, и он же тот, в
    котором отметка полезнее всего.
    """
    if vhod.rol(h.headers) is None:
        _otdat_json(h, 403, {"error": "нужно войти"})
        return True
    teacher_id = vhod.kto(h.headers)
    if teacher_id is None:
        _otdat_json(h, 403, {"error":
                             "общий пароль не называет человека — нужен личный"})
        return True
    try:
        p = _telo(h)
        den = str(p["den"]).strip()
        net = str(p.get("net", "1")) not in ("0", "", "False", "false")
    except (KeyError, TypeError, ValueError):
        _otdat_json(h, 400, {"error": "нужен den"})
        return True
    if slot_of_bezopasno(den) is None:
        _otdat_json(h, 400, {"error": "не день занятия: %s" % den})
        return True
    if den < segodnya():
        _otdat_json(h, 400, {"error": "прошедшее занятие отметить нельзя"})
        return True

    c = _soedinenie(h)
    try:
        ryad = c.execute("select id from sessions where held_on = ?", (den,)).fetchone()
        if ryad is None:
            # Занятия ещё нет в базе — его заводит первый экран, открытый на этот день,
            # и эта отметка тоже такой экран. Ровно та же строка, что в
            # `veb/server.py::_post_zanyatie`, и по той же причине.
            kur = c.execute("insert into sessions (held_on) values (?)", (den,))
            session_id = kur.lastrowid
        else:
            session_id = ryad["id"]
        if net:
            # `answered_at` в схеме `not null`: таблицу завёл опрос преподавателей, и
            # время ответа там обязательно. Отметка рукой — тоже ответ, и её время это
            # момент, когда её поставили.
            c.execute(
                "insert or replace into teacher_attendance "
                "(session_id, teacher_id, status, answered_at) values (?, ?, ?, ?)",
                (session_id, teacher_id, OTSUTSTVUET,
                 datetime.now(ZoneInfo(config.TZ_DISPLAY)).isoformat(timespec="seconds")))
        else:
            # Снятая отметка — УДАЛЕНИЕ строки, а не «был»: «как обычно» это отсутствие
            # отклонения, то же правило, по которому снятая отметка школьника удаляет
            # его строку в `attendance`.
            c.execute("delete from teacher_attendance "
                      "where session_id = ? and teacher_id = ?", (session_id, teacher_id))
        _peresobrat_tiho(h)
        _otdat_json(h, 200, {"ok": True, "den": den, "net": bool(net)})
    finally:
        c.close()
    return True


def slot_of_bezopasno(den: str):
    """`slot_of`, но нечитаемая дата — это «не день занятия», а не исключение."""
    try:
        return slot_of(den)
    except ValueError:
        return None


def _peresobrat_tiho(h) -> None:
    """Пересобрать публичную страницу и НЕ уронить отметку, если сборка сломана.

    Дословно тот же выбор, что в `veb/server.py::_peresobrat_tiho`, и по той же
    причине: запись в базу уже произошла и от сборки не зависит, а 500 здесь означал бы
    «не сохранилось» на экране при сохранённых данных.
    """
    svoy = getattr(h, "_peresobrat_tiho", None)
    if callable(svoy):
        svoy()
        return
    try:
        from tools.sobrat_stranicu import sobrat

        sobrat()
    except Exception:
        pass


def marshruty():
    """Пути этого раздела: `{путь: обработчик}`. Зовётся сборкой сервера.

    Обе двери отвечают и на GET, и на POST, потому что `do_GET` и `do_POST` спрашивают
    реестр одинаково — та же страховка, которую завёл `veb/priyom.py`: «не записалось,
    потому что метод не тот» это не тот ответ, который можно себе позволить на живом
    занятии.
    """
    return {"/kabinet": pokazat_kabinet,
            "/api/kabinet/otsutstvie": otmetit_otsutstvie}
