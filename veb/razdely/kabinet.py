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
from datetime import date, datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import config
from core.services.istoria_poseshchenij import zanyatie_zaversheno
from core.services.sostav_na_den import (
    OTSUTSTVUET,
    blizhajshie_zanyatiya,
    slot_of,
)
from veb import vhod
from veb.obshchee.karkas import VREMYA, e, menyu_ssylkami
from veb.razdely.istoria_zanyatij import sdachi_po_zanyatiyam
from veb.razdely.lichnaya import deti_na_datu, kabinet_na_datu, segodnya
from core.istochnik import put_bazy
from veb.razdely.list_odin import _obshchij_stil

#: How many lessons forward the grid of future absences shows.  Eight is four calendar
#: weeks of two lessons: the owner's own horizon in the same sentence — *«мы знаем, что
#: школьник или преподаватель будет отсутствовать в течение месяца»* — and short enough
#: that the grid stays one screen a person reads at a glance rather than scrolls.
GLUBINA_VPERYOD = 8

#: Месяц, с которого считается учебный год. Полоса в кабинете показывает занятия «с
#: начала года» (владелец 10.09, H1.6), и начало года — не 1 января: 1 сентября того
#: года, в котором мы сейчас, если сентябрь уже был, и предыдущего, если ещё нет. Число
#: считается от сегодняшней даты, а не вписывается: вписанный год протухает молча —
#: ровно тем способом, каким `2026-09-05` уже звался здесь четвергом, будучи субботой.
NACHALO_GODA_MESYAC = 9


def nachalo_uchebnogo_goda(den: str) -> str:
    """`2026-09-10` → `2026-09-01`; `2027-02-03` → `2026-09-01`."""
    d = date.fromisoformat(den)
    god = d.year if d.month >= NACHALO_GODA_MESYAC else d.year - 1
    return date(god, NACHALO_GODA_MESYAC, 1).isoformat()


def proshedshie_zanyatiya(den: str) -> list:
    """Дни занятий с начала учебного года ДО `den`, не включая его самого.

    🔴 КАЛЕНДАРЬ, А НЕ ТАБЛИЦА `sessions`, И ЭТО РАЗНЫЕ ВОПРОСЫ. `sessions` заводится
    ЛЕНИВО — строка появляется, когда кто-то первым открыл экран этого дня или
    поставил отметку (`veb/server.py::_post_zanyatie`, и точно так же дверь ниже в
    этом файле). Занятие, на котором никто ничего не отметил, в таблице не лежит, и
    полоса, построенная по ней, молча теряла бы дни. Какие дни недели — занятия,
    знает ровно одно место, `sostav_na_den.SLOTY_ZANYATIJ`, и `slot_of` его читает.
    """
    d = date.fromisoformat(nachalo_uchebnogo_goda(den))
    konec = date.fromisoformat(den)
    dni = []
    while d < konec:
        if slot_of(d.isoformat()) is not None:
            dni.append(d.isoformat())
        d += timedelta(days=1)
    return dni


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

    One query for the whole strip rather than one per date: the strip is the lesson days
    of the school year so far plus `GLUBINA_VPERYOD` forward, and by May that is about
    seventy dates — seventy queries where one has the same shape.
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
/* 🔴 ВСЁ НА ВЕСЬ ЭКРАН, И ЭТО СТАРАЯ, МНОГО РАЗ НАЗВАННАЯ ПРЕТЕНЗИЯ ВЛАДЕЛЬЦА
   (10.09, H1.8): «я давным-давно говорил, что так нельзя делать. У нас все
   полоски делаются на весь экран». Здесь стояло `max-width:60rem;margin:0 auto`
   — узкая колонка по центру. Поля берутся у `.holst` каркаса, то есть у той же
   меры, которой отбита каждая другая страница сайта. */
.kab-stranica{padding:1.3rem 3rem 4rem}
.kab-stranica h1{margin:0 0 .2rem}
.kab-kto{font-family:var(--sans);color:var(--muted);margin:0 0 2rem;font-size:1.05rem}
.kab-kto a{color:var(--accent);text-decoration:none}
.kab-kto a:hover{text-decoration:underline}
.kab-blok{background:var(--panel);border:1px solid var(--rule);border-radius:16px;
  padding:1.4rem 1.7rem;margin:0 0 1.6rem}
.kab-kogda{font-family:var(--sans);font-size:1.5rem;font-weight:600;margin:.2rem 0 0}
.kab-listok{font-family:var(--sans);font-size:2rem;font-weight:600;margin:.5rem 0 0}
.kab-listok a{color:inherit;text-decoration:none;border-bottom:2px solid var(--rule)}
.kab-listok a:hover{border-bottom-color:var(--accent);color:var(--accent)}
.kab-gde{font-family:var(--sans);font-size:1.25rem;margin:.7rem 0 0;color:var(--muted)}
.kab-gde .kab{font-size:1.5rem}
.kab-deti{display:grid;grid-template-columns:repeat(auto-fill,minmax(15rem,1fr));
  gap:.1rem 2rem;margin:1rem 0 0}
.kab-deti div{padding:.35rem 0;border-bottom:1px solid var(--rule);font-size:1.2rem}
/* 🔴 ПОЛОСЫ КНОПОК ЗДЕСЬ БОЛЬШЕ НЕТ, И ЕЁ ПРАВИЛА СНЯТЫ ВМЕСТЕ С НЕЙ.
   `.kab-polosa`, `.kab-den` и их состояния описывали строку плашек с датами
   (владелец 10.09, H1.6). Разметка её больше не порождает — на её месте таблица
   занятий (`.kab-tablica` ниже, L1.3), — и правило, которому не с чем совпасть,
   это не запас на будущее, а третье место, где записан цвет «был». Цвет и
   поведение переехали целиком: `.kab-zanyatie.byl` / `.ne-byl` / `.vperyod`. */
.kab-beda{color:var(--krasn);font-family:var(--sans);font-size:1rem;margin:.8rem 0 0;
  min-height:1.2em}
/* 🔴 ПОЛОСА КНОПОК ЗАМЕНЕНА ТАБЛИЦЕЙ ЗАНЯТИЙ (L1.3, владелец 10.09): «строки —
   занятия, в каждой список школьников, клик по школьнику раскрывает сдачу.
   Раскладка многоколоночная СВЕРХУ ВНИЗ: вся четверть должна поместиться,
   горизонтальной прокрутки быть не должно».
   СВЕРХУ ВНИЗ — это `columns`, а не `grid`: колоночная вёрстка льёт занятия
   вниз по первой колонке, потом во вторую, и порядок чтения остаётся
   хронологическим. `grid` с тем же числом колонок разложил бы их СЛЕВА НАПРАВО,
   то есть перемешал бы даты в каждой строке. */
.kab-tablica{columns:4;column-gap:1.6rem;margin:.9rem 0 0}
.kab-zanyatie{break-inside:avoid;-webkit-column-break-inside:avoid;
  border:1px solid var(--rule);border-radius:12px;padding:.6rem .8rem;
  margin:0 0 .8rem;background:var(--bg);font-family:var(--sans)}
.kab-zanyatie.byl{border-color:var(--zel);background:var(--zel-fon)}
.kab-zanyatie.ne-byl{border-color:var(--krasn);background:var(--krasn-fon)}
.kab-zanyatie.vperyod.netu{border-color:var(--krasn);background:var(--krasn-fon)}
.kab-zag{display:flex;align-items:baseline;gap:.5rem;font-weight:600;font-size:1.02rem;
  cursor:pointer}
.kab-zanyatie.byl .kab-zag{color:var(--zel)}
.kab-zanyatie.ne-byl .kab-zag{color:var(--krasn)}
.kab-skolko{margin-left:auto;font-weight:400;font-size:.85rem;color:var(--muted)}
.kab-spisok{list-style:none;margin:.45rem 0 0;padding:0;font-size:.95rem}
.kab-spisok li{padding:.1rem 0}
.kab-shk{background:none;border:none;padding:.1rem 0;font:inherit;color:var(--text);
  cursor:pointer;text-align:left;width:100%;border-radius:5px}
.kab-shk:hover,.kab-shk:focus-visible{color:var(--accent);background:var(--accent-soft)}
.kab-nikogo{color:var(--muted);font-size:.9rem;margin:.4rem 0 0}
/* Будущее: клетка сама себе выключатель, как и была. Флажок спрятан, а не убран —
   им работают клавиатура и `:focus-visible`, и он же несёт дату для двери. */
.kab-vpered-metka{display:flex;align-items:baseline;gap:.5rem;cursor:pointer;
  font-weight:600;font-size:1.02rem}
.kab-zanyatie.vperyod.netu .kab-vpered-metka{color:var(--krasn);
  text-decoration:line-through}
.kab-zanyatie input{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none}
.kab-zanyatie input:focus-visible+.kab-den-tekst{outline:2px solid var(--accent);
  outline-offset:3px;border-radius:3px}
.kab-raskrytie{position:sticky;bottom:0;z-index:30;margin:1.2rem 0 0;
  background:var(--panel);border:1px solid var(--rule);border-radius:14px;
  padding:1rem 1.3rem;font-family:var(--sans);box-shadow:0 -2px 14px rgba(0,0,0,.06)}
.kab-raskrytie[hidden]{display:none}
.kab-raskrytie h2{font-size:1.1rem;margin:0 0 .5rem;font-family:var(--sans)}
.kab-raskrytie ul{margin:.3rem 0 0;padding-left:1.2rem}
.kab-raskrytie .kab-nichego{color:var(--muted)}
.kab-raskrytie .kab-zakryt{float:right;cursor:pointer;border:1px solid var(--rule);
  background:none;color:var(--muted);border-radius:8px;padding:.2em .7em;font:inherit}
@media(max-width:1200px){.kab-tablica{columns:3}}
@media(max-width:900px){.kab-tablica{columns:2}}
@media(max-width:640px){.kab-tablica{columns:1}}
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
document.querySelectorAll('.kab-zanyatie input').forEach(function(fl){
  fl.addEventListener('change', function(){
    var ryad = fl.closest('.kab-zanyatie');
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

/* 🔴 РАСКРЫТИЕ ЗАНЯТИЯ И ШКОЛЬНИКА (L1.2, владелец 10.09): «клик по прошлому
   занятию раскрывает своё — кто был и что поставлено», и клик по школьнику —
   его сдачу. Одна панель на страницу и один обработчик на документ: занятий к
   маю около семидесяти, и по спрятанному блоку на каждое было бы вторым
   документом внутри первого. Содержимое лежит одним словарём в `kab-dannye`. */
(function(){
  var uzel = document.getElementById('kab-dannye');
  var dannye = uzel ? JSON.parse(uzel.textContent) : {};
  var panel = document.getElementById('kab-raskrytie');
  var telo = document.getElementById('kab-raskrytie-telo');
  var zag = document.getElementById('kab-raskrytie-zag');
  function zadachi(sdal){
    return sdal.map(function(z){ return 'листок ' + z.listok + ' · задача ' + z.zadacha; });
  }
  function spisok(punkty, pusto){
    if (!punkty.length) return '<p class="kab-nichego">' + pusto + '</p>';
    return '<ul>' + punkty.map(function(x){ return '<li>' + x + '</li>'; }).join('') + '</ul>';
  }
  function zakryt(){ panel.hidden = true; }
  function pokazat(klyuch){
    var d = dannye[klyuch];
    if (!d) return;
    zag.textContent = d.kto;
    if (d.deti) {
      telo.innerHTML = spisok(d.deti.map(function(r){
        var z = zadachi(r.sdal);
        return '<b>' + r.kto + '</b>' + (z.length ? ' — ' + z.join('; ') : ' — ничего не сдал');
      }), 'в этот день школьников не было');
    } else {
      telo.innerHTML = '<p>' + d.den + '</p>'
        + spisok(zadachi(d.sdal), 'в этот день ничего не сдал');
    }
    panel.hidden = false;
  }
  document.addEventListener('click', function(sob){
    if (!sob.target.closest) return;
    var shk = sob.target.closest('.kab-shk');
    if (shk) { pokazat(shk.dataset.den + '|' + shk.dataset.sid); return; }
    var zagolovok = sob.target.closest('.kab-zag');
    if (zagolovok) { pokazat(zagolovok.dataset.den); return; }
    if (sob.target.closest('#kab-raskrytie')) return;
    zakryt();
  });
  document.addEventListener('keydown', function(sob){
    if (sob.key === 'Escape') zakryt();
    if ((sob.key === 'Enter' || sob.key === ' ')
        && sob.target.classList && sob.target.classList.contains('kab-zag')) {
      sob.preventDefault(); pokazat(sob.target.dataset.den);
    }
  });
  document.getElementById('kab-zakryt').addEventListener('click', zakryt);
})();
</script>"""


def stranica(c: sqlite3.Connection, teacher_id: int) -> str:
    """The whole page for one named teacher."""
    from veb.razdely.listki import tekushchij

    kto = imya_prepoda(c, teacher_id)
    if kto is None:
        return _dokument("Кабинет", '<div class="kab-stranica">'
                                    '<h1>Кабинет</h1>'
                                    '<p class="net">Такого преподавателя нет в базе.</p>'
                                    '</div>', put_bazy(c))

    # 🔴 ОТМЕТКИ СПРАШИВАЮТСЯ СРАЗУ ЗА ВСЮ ПОЛОСУ, ОДНИМ ЗАПРОСОМ. Раньше их брали
    # только на восемь дней вперёд, потому что и рисовали только их; полоса красит
    # ещё и прошлое, и запрос на восемь дней покрасил бы каждый прошедший день
    # зелёным — то есть соврал бы ровно там, где владелец смотрит.
    dni = blizhajshie_zanyatiya(segodnya(), GLUBINA_VPERYOD)
    proshlo = proshedshie_zanyatiya(segodnya())
    net_na = otsutstviya(c, teacher_id, proshlo + dni)
    blizhajshee = dni[0] if dni else None

    # ── СЛЕДУЮЩЕЕ ЗАНЯТИЕ. Оно же первая будущая клетка полосы ниже: два ответа об одном дне
    # берутся из одного списка, а не из двух вычислений, которые однажды разойдутся.
    if blizhajshee is None:
        blok_blizh = ('<div class="kab-blok"><p class="net">'
                      'ближайшее занятие не найдено</p></div>')
    else:
        wd = date.fromisoformat(blizhajshee).isoweekday()
        kab = kabinet_na_datu(c, teacher_id, blizhajshee)
        deti = deti_na_datu(c, teacher_id, blizhajshee)
        nomer, tema, _versii = tekushchij()
        # 🔴 НАЗВАНИЕ ЛИСТКА — ССЫЛКА (H1.2: «нажать нельзя»). Ведёт на вкладку
        # «Листки» заглавной, и открывает её `karkas.VKLADKA_SKRIPT`, который для
        # того и научен переводить якорь `#s-list` в отметку радиокнопки.
        listok = (('%s · <a href="/#s-list">%s</a>' % (e(nomer), e(tema))) if tema
                  else "листок пока не назван")
        kab_html = (f'<span class="kab">{e(kab)}</span>' if kab
                    else '<span class="net">кабинет не назначен</span>')
        if blizhajshee in net_na:
            # Он сам сказал, что его не будет: список школьников на этот день — не
            # то, что ему нужно видеть, и показывать его значило бы спорить с его же
            # отметкой. Ниже, в полосе, эта клетка перечёркнута и покрашена красным.
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

    # ── ТАБЛИЦА ЗАНЯТИЙ С НАЧАЛА УЧЕБНОГО ГОДА (L1.3, владелец 10.09).
    # Здесь стояла ПОЛОСА КНОПОК: дата и цвет, а кто на занятии был — только во
    # всплывающей подсказке. Владелец попросил другое: «строки — занятия, в каждой
    # список школьников, клик по школьнику раскрывает сдачу», и «вся четверть должна
    # поместиться», без горизонтальной прокрутки. Раскладку даёт `columns` (разбор —
    # у `.kab-tablica` в стилях выше).
    #
    # 🔴 ГРАНИЦА «ПРОШЛОЕ/БУДУЩЕЕ» БОЛЬШЕ НЕ СРАВНИВАЕТ ДАТЫ, И ЭТО ПОЧИНКА ДЕФЕКТА
    # ФАКТА L1.1, А НЕ ПЕРЕКРАСКА. Владелец 10.09 провёл занятие 10.09 и увидел, что
    # плашка того дня НЕ зелёная. Причина: здесь стояло `den < segodnya()`, и для
    # СЕГОДНЯШНЕГО занятия оно ложно — то есть занятие, которое он только что провёл,
    # рисовалось как БУДУЩЕЕ: без цвета и с флажком «меня не будет». Состояния
    # «сегодня, и оно уже кончилось» у полосы не было вовсе.
    # Замер, часы переведены на дату владельца (копия боевой базы, преподаватель id=2):
    #   часы 2026-09-10 → клетка 10.09 несёт класс `kab-den vperyod`, флажок есть
    #   часы 2026-09-11 → та же клетка несёт `kab-den byl`, флажка нет
    # Один и тот же факт, два разных экрана — потому что вопрос задавался календарю,
    # а не расписанию. Спрашивается теперь то, что на него уже отвечает:
    # `istoria_poseshchenij.zanyatie_zaversheno(den, seichas=…)` — единственное место,
    # знающее, кончилось ли занятие этого дня (оно же держит `KONEC_ZANYATIA`).
    #
    # 🔴 У ДВЕРИ ЗАПИСИ ГРАНИЦА ОСТАЁТСЯ СВОЯ, И ЭТО СКАЗАНО ВСЛУХ. `otmetit_otsutstvie`
    # отказывает на `den < segodnya()`, потому что отвечает на ДРУГОЙ вопрос — «можно
    # ли ещё сказать, что меня не будет», а не «кончилось ли занятие». После этой
    # правки занятие, которое сегодня уже прошло, показывается зелёным и флажка не
    # предлагает, а дверь такую запись всё ещё приняла бы. Расширять или сужать дверь
    # этот заход не стал: это правка пути ЗАПИСИ, которой никто не просил.
    seichas = datetime.now(timezone.utc)
    sdachi = sdachi_po_zanyatiyam(c, tuple(proshlo))
    bloki = []
    raskrytie: dict = {}
    for den in proshlo + dni:
        proshlo_li = zanyatie_zaversheno(den, seichas=seichas)
        d = date.fromisoformat(den)
        wd = d.isoweekday()
        podpis = "%s %02d.%02d" % (KOROTKO_DNYA.get(wd, ""), d.day, d.month)
        # Наведение и список называют школьников ТОГО дня: `deti_na_datu` держит
        # интервал `enrollment`, поэтому на прошедшую дату отвечает состав, который
        # был тогда, а не сегодняшний.
        kto_byl = deti_na_datu(c, teacher_id, den)
        netu = den in net_na
        if proshlo_li:
            punkty = []
            sdach_dnya = 0
            for r in kto_byl:
                sdal = sdachi.get((den, r["id"]), ())
                sdach_dnya += len(sdal)
                raskrytie["%s|%s" % (den, r["id"])] = {
                    "kto": "%s %s" % (r["surname"], r["name"]),
                    "den": po_russki(den),
                    "sdal": [{"zadacha": z, "listok": l} for z, l, _t in sdal],
                }
                punkty.append(
                    '<li><button class="kab-shk" type="button" data-den="%s" '
                    'data-sid="%s"><b>%s</b> %s%s</button></li>'
                    % (e(den), r["id"], e(r["surname"]), e(r["name"]),
                       (' <span class="kab-skolko">сдал %d</span>' % len(sdal))
                       if sdal else ""))
            raskrytie[den] = {
                "kto": po_russki(den),
                "den": po_russki(den),
                "deti": [{"kto": "%s %s" % (r["surname"], r["name"]),
                          "sdal": [{"zadacha": z, "listok": l}
                                   for z, l, _t in sdachi.get((den, r["id"]), ())]}
                         for r in kto_byl],
            }
            spisok = ('<ul class="kab-spisok">%s</ul>' % "".join(punkty) if punkty
                      else '<p class="kab-nikogo">школьников в этот день не было</p>')
            bloki.append(
                '<div class="kab-zanyatie %s" data-den="%s">'
                '<div class="kab-zag" data-den="%s" tabindex="0">%s'
                '<span class="kab-skolko">%s</span></div>%s</div>'
                % ("ne-byl" if netu else "byl", e(den), e(den), e(podpis),
                   # 🔴 «ЗАДАЧ», А НЕ «СДАЧ» — ПУНКТ 2 РЕЦЕНЗИИ ВЛАДЕЛЬЦА 11.09,
                   # дословно: *«потом слово „сдач“ очень странное. Лучше пиши
                   # „задач“»*, и формат он назвал тоже сам — `задач: 23`. Считается
                   # ровно то же самое, что и считалось: сколько задач принято в этот
                   # день у школьников этого преподавателя. Переименовано ТОЛЬКО
                   # слово на экране; имя переменной `sdach_dnya` осталось, потому что
                   # словарь, из которого число берётся, зовётся `sdachi` и живёт в
                   # чужом файле (`istoria_zanyatij.sdachi_po_zanyatiyam`) — менять
                   # имя здесь значило бы развести его с источником.
                   e("вас не было" if netu else "задач: %d" % sdach_dnya), spisok))
        else:
            imena = ", ".join("%s %s" % (e(r["surname"]), e(r["name"]))
                              for r in kto_byl)
            bloki.append(
                '<div class="kab-zanyatie vperyod%s" data-den="%s">'
                '<label class="kab-vpered-metka">'
                '<input type="checkbox" data-den="%s"%s>'
                '<span class="kab-den-tekst">%s</span>'
                '<span class="kab-skolko">меня не будет</span></label>'
                '%s</div>'
                % (" netu" if netu else "", e(den), e(den),
                   " checked" if netu else "", e(podpis),
                   ('<ul class="kab-spisok"><li>%s</li></ul>'
                    % imena.replace(", ", "</li><li>")) if imena
                   else '<p class="kab-nikogo">школьников пока нет</p>'))

    # 🔴 СВОДНОЙ СТРОКИ «С НАЧАЛА ГОДА: …» ЗДЕСЬ БОЛЬШЕ НЕТ, И ЭТО РЕШЕНИЕ
    # ВЛАДЕЛЬЦА 11.09, А НЕ УПРОЩЕНИЕ. Дословно: *«я не понял, что значит занятия с
    # вашими школьниками 2 из 3… это какая-то фраза вставлена, которую можно удалить
    # вообще. Фразы от себя лучше удалять»*. Строка родилась из его же «и это должно
    # сводиться в один текст» 10.09 и была дописана здесь по догадке о том, ЧТО именно
    # сводить; посмотрев на неё на живом сайте, он сказал, что не понимает её. Ни одно
    # из четырёх чисел не спрашивалось отдельным запросом — все считались тем же
    # обходом, который рисует блоки, — поэтому вместе со строкой уходят и счётчики
    # (`prinyato_vsego`, `deti_vsego`, `_byli_deti`, `svoi_dni`): считать их больше
    # не для кого, а счётчик без читателя это третье место, где записан тот же факт.
    # Числа дня остались там, где владелец их и смотрит — в шапке самой плитки.
    gruppa_html = (' · <a href="/raspredelenie">группа %s</a>' % e(kto["gruppa"])
                   if kto["gruppa"] else "")
    telo = f"""<div class="kab-stranica">
  <h1>{e(kto["name"])}</h1>
  <p class="kab-kto">кабинет преподавателя{gruppa_html}</p>
  {blok_blizh}
  <div class="kab-blok">
    <p class="zag2">мои занятия с начала года</p>
    <!-- 🔴 НИ ПОДПИСИ-ПОЯСНЕНИЯ, НИ СВОДНОЙ СТРОКИ ЗДЕСЬ НЕТ И НЕ ДОЛЖНО БЫТЬ.
         «Зелёная — вы были, красная — вас не было…» владелец назвал НЕЙРОСЛОПОМ
         10.09 и велел убрать целиком; сводную строку «с начала года: занятий с
         вашими школьниками 2 из 3…» он убрал 11.09 теми же словами — «фразы от
         себя лучше удалять». Короткая версия на том же месте — то же самое, только
         тише. Разбор — у места, где строка считалась, выше в этом файле. -->
    <div class="kab-tablica">{"".join(bloki)}</div>
    <p class="kab-beda" id="kab-beda"></p>
  </div>
  <div class="kab-raskrytie" id="kab-raskrytie" hidden>
    <button class="kab-zakryt" id="kab-zakryt" type="button">закрыть</button>
    <h2 id="kab-raskrytie-zag"></h2>
    <div id="kab-raskrytie-telo"></div>
  </div>
</div>
<script type="application/json" id="kab-dannye">{json.dumps(raskrytie, ensure_ascii=False)}</script>{SKRIPT}"""
    return _dokument("Кабинет — " + kto["name"], telo, put_bazy(c))


def _dokument(zagolovok: str, telo: str, baza=None) -> str:
    """Документ кабинета — С ВЕРХНИМ МЕНЮ, и это первое, о чём просил владелец 10.09.

    Дословно (`TZ-DOBOR-10-09.md` H1.1): *«нет верхнего меню, из кабинета некуда
    уйти, это плохо»*. Меню рисует `karkas.menyu_ssylkami` — одно место, где
    записаны названия и адреса пунктов, общее с оболочкой; его стили приезжают
    вместе со всей таблицей сайта через `_obshchij_stil()`, и ни одного своего
    цвета здесь по-прежнему нет.
    """
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(zagolovok)}</title>
<style>{_obshchij_stil(baza)}{SVOI_STILI}</style></head>
<body>
{menyu_ssylkami("/kabinet")}
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
    # 🔴 `getattr(x, "db_path", config.DB_PATH)` — ЛОВУШКА, И ОНА СРАБОТАЛА.
    # Значение по умолчанию у `getattr` вычисляется ДО того, как проверено
    # наличие атрибута, поэтому обращение к источнику происходило даже там, где
    # база уже названа сервером. `or` короткозамкнут: спрашиваем источник только
    # тогда, когда сервер базу НЕ назвал.
    db_path = getattr(getattr(h, "server", None), "db_path", None) or config.DB_PATH
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
            '<p class="kab-gde"><a href="/vhod">Вход</a></p></div>',
            getattr(getattr(h, "server", None), "db_path", None)))
        return True
    if kto is None:
        _otdat_html(h, 200, _dokument(
            "Кабинет", '<div class="kab-stranica"><h1>Кабинет</h1>'
            '<p class="net">Вход по общему паролю: система не знает, кто именно вошёл. '
            'Свой кабинет, своих школьников и отметку отсутствия показывает личный '
            'пароль.</p>'
            '<p class="kab-gde"><a href="/">На заглавную</a></p></div>',
            getattr(getattr(h, "server", None), "db_path", None)))
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
