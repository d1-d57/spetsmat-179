#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-code — `veb/obshchee/karkas.py` hangs `SKRIPT` on the page
# and `veb/razdely/konduit.py` hangs `polosa()` and `stili()` in the кондуит section.
# Nothing here is reachable by a URL of its own; there is no route to register.
"""Оффлайн-очередь записи: a tap stops waiting for the network.

WHY THIS EXISTS, in the owner's words (10.09): *«Нажимаю на клеточку, а галочка не
загорается. Оно просто так замирает»* — and next to it the requirement: *«если вдруг
пропал интернет, ты мог всё равно внести плюсик, поставить галочку, и она бы вносилась
в тот момент, когда интернет появится»*.  The cause is not the server: VPN plus jamming
in central Moscow, school wi-fi and mobile data that fall over.  For us that was an edge;
for this audience it is the norm.

🔴 THE QUEUE IS TRANSPORT AND NOTHING ELSE.  Interview point 4 and
`NADEZHNOST-zakaz-na-resyorch.md` §2 both say it in one sentence: *«источник правды —
сервер, локальная очередь только транспорт; терять её должно быть не страшно»*.  So
nothing is ever COMPUTED from what stands in the queue — no counts, no debts, no
statistics.  The only thing the queue decides is when a request leaves; what the request
MEANS is decided by the server, and every confirmed answer redraws the cell from what the
server said.  Losing the whole store costs at most the taps that had not left yet, and
costs no correctness at all.

🔴 STRICTLY ONE AT A TIME, IN THE ORDER OF THE TAPS.  The store's key is an
`autoIncrement`, so the key IS the order, and the sender never has more than one request
in flight.  That is the whole of the ordering machinery: `заказ` §2 says a queue drained
one by one keeps the order inside one device for free, with no vector clocks and — 🔴 —
with **no use of the phone's wall clock**, which is not to be laid into ordering at all.

🔴 `navigator.onLine` IS NOT TRUSTED, AND THAT IS A MEASURED DECISION, NOT A STYLE.  On
school wi-fi it says "online" while nothing reaches the internet (`заказ` §2).  Every
state transition below is driven by the outcome of a REAL request; the `online` /
`offline` events are read as a hint to try again sooner, never as an answer.

🔴 NO SERVICE WORKER AND NO PWA, DELIBERATELY.  Р1 (does the queue survive seven days in
an installed iOS PWA) and Р2 (Background Sync in Safari) are closed by an experiment on a
teacher's real iPhone, not by documentation, and this position has no such hardware.  So
everything here depends on NEITHER answer: the store is plain IndexedDB and it is drained
from the foreground only — on `online`, on `visibilitychange`, on page load, and on a
backoff timer while the page is open.  **The price, stated rather than hidden:** a COLD
load with no network still fails, because without a service worker the browser cannot
fetch the page at all.  What is covered is the case the owner actually described — the
page is open during the lesson and the network dies under it.

🔴 A REFUSAL IS NOT A NETWORK FAILURE, AND THE TWO GET OPPOSITE TREATMENT.  A request
that cannot ever succeed (`4xx`: not signed in, malformed, the key reused) is dropped
from the queue and reported loudly, because a head item that can never succeed would
block every tap standing behind it forever.  A request that failed for the network (no
answer, timeout, `5xx`, `429`) keeps its place and the sender stops until the next
attempt.  Both are the same event to the person only in one respect: nothing is ever lost
silently.
"""
from __future__ import annotations

#: Boundary between «снимок свежий» and «снимок старый», in minutes.  Fifteen is one
#: sensible reach of a lesson: data a quarter of an hour old is still the lesson you are
#: standing in, and anything beyond it is another lesson's picture.  Р7 asks for three
#: states and their texts; this is the only number the three states need.
STARYJ_CHEREZ_MINUT = 15

#: How long one attempt waits before it is called a failure.  The same ten seconds
#: `KONDUIT_SKRIPT` already spends (commit `db50f4f`), for the same stated reason: a
#: lesson is running, and a request silent for longer is useless whatever the cause.
TAJMAUT_MS = 10000


def schyotchik() -> str:
    """The counter chip: «в очереди N отметок».  Born hidden — at zero there is nothing
    to say, and a chip standing at zero is an organ that does nothing.
    """
    return ('<span class="och-schyot" id="och-schyot" data-org="videt-konduit"'
            ' hidden></span>')


def banner(snyato: str) -> str:
    """The degradation banner — the carrier of Р7's three states.

    ``snyato`` is the time this page was RENDERED, `HH:MM`, produced on the server.  It
    is printed as «данные от …» and is never recomputed in the browser: the phone's clock
    may be anything, and a banner that lies about the age of what it covers is worse than
    no banner.  The AGE is measured separately and monotonically — see `_SKRIPT`.

    `role="status"` and not `role="alert"`: the banner appears while the teacher is
    tapping, and an alert would drag a screen reader off the cell mid-lesson.
    """
    return ('<div class="och-banner" id="och-banner" data-org="videt-konduit"'
            ' data-snyato="' + snyato + '" role="status" hidden></div>')


def otkazy() -> str:
    """The refusal strip: what the server refused, and why, until the person closes it.

    🔴 IT DOES NOT GO AWAY BY ITSELF, AND THAT IS THE WHOLE REQUIREMENT.  Точка 4 захода:
    *«отказ обязан ПЕРЕЖИВАТЬ перезагрузку: правка не смеет исчезать молча на глазах
    человека»*.  A message on a timer is a message nobody read; a page that reloads on
    top of it is the same thing with extra steps.  So this strip has a close button and
    no timer, and every refusal names the cell and the reason.
    """
    return ('<div class="och-otkaz" id="och-otkaz" data-org="videt-konduit"'
            ' role="alert" hidden></div>')


def stili() -> str:
    """The queue's CSS.  Every value is a variable the кондуит stylesheet already defines.

    `doc/DIZAJN-ZAKREPLENO.md` §0: a new organ TAKES the palette and the sizes of what
    already stands.  Not one colour is invented here.
    """
    return """
/* ── Оффлайн-очередь: счётчик, баннер деградации, клетка «в очереди» ───────── */
#s-kond .och-schyot{font-family:var(--sans);font-size:.95rem;font-weight:600;
  color:var(--accent);background:var(--accent-soft);border:1px solid var(--accent);
  border-radius:8px;padding:.25em .7rem;white-space:nowrap}
#s-kond .och-banner{font-family:var(--sans);font-size:.95rem;margin:.5rem 0 0;
  padding:.5em .9rem;border-radius:8px;border:1px solid var(--rule);
  background:var(--panel);color:var(--text)}
#s-kond .och-banner.staryj{border-color:var(--accent);background:var(--accent-soft)}
#s-kond .och-banner b{font-weight:600}
/* Полоса отказов. Стоит, пока её не закроют: см. `otkazy()`. */
#s-kond .och-otkaz{font-family:var(--sans);font-size:.95rem;margin:.5rem 0 0;
  padding:.5em .9rem;border-radius:8px;border:1px solid var(--warm);
  background:var(--panel);color:var(--text)}
#s-kond .och-otkaz p{margin:0 0 .25em}
#s-kond .och-otkaz p:last-of-type{margin-bottom:.4em}
#s-kond .och-otkaz b{font-weight:600;color:var(--warm)}
#s-kond .och-otkaz button{font-family:var(--sans);font-size:.9rem;cursor:pointer;
  border:1px solid var(--rule);border-radius:6px;padding:.2em .8rem;
  background:var(--bg);color:var(--text)}
/* Клетка, чей тап ещё не подтверждён сервером: знак уже стоит, но он «свой», а не
   «из журнала». Пунктир — то же различие, каким страница правок метит несохранённое. */
#s-kond .kond td.v-ocheredi{outline:2px dashed var(--accent);outline-offset:-2px}
/* Клетка, чей тап сервер ОТКЛОНИЛ. Знак уже вернулся к тому, что в журнале; метка
   держится до следующего тапа по ней, а причина стоит в `title`. */
#s-kond .kond td.otkazano{outline:2px solid var(--accent);outline-offset:-2px}
"""


# 🔴 THE SCRIPT IS A PLAIN STRING AND NOT AN f-STRING, ON PURPOSE.  Its body is JavaScript
# and therefore full of `{}`; an f-string would need every one of them doubled, and the
# first missed pair is a syntax error inside a string, which Python reports at the wrong
# line and the browser reports not at all.  The two values that must reach it are pushed
# in by `skript()` with `str.replace`, NOT with `%` or `.format`: the body already
# contains `%` as the JavaScript remainder operator and `{}` as blocks, and both of the
# usual mechanisms would have to escape every one of them.  A placeholder that looks
# like nothing else in the file cannot collide with either.
_SKRIPT = r"""
<script>
/* ── ОЧЕРЕДЬ ЗАПИСИ: ТАП ПЕРЕСТАЁТ ЖДАТЬ СЕТЬ ─────────────────────────────────
   Полное «почему» — в docstring `veb/razdely/ochered.py` и в `doc/OFFLAJN.md`.
   Здесь — только устройство.

   Наружу выставлено ровно четыре вещи, и ни одна из них ничего не рисует в решётке:
     OCHERED.postavit(zapis)   — поставить запрос в очередь; отдаёт Promise
     OCHERED.vse()             — всё, что стоит в очереди сейчас (для перерисовки
                                 после перезагрузки страницы)
     OCHERED.podpisatsya(fn)   — уведомления о судьбе записей и о состоянии связи
     OCHERED.tolknut()         — попробовать вывезти прямо сейчас
   Рисует клетки кондуит, потому что клетки — его. Транспорт рисует только свои два
   органа: счётчик и баннер. */
window.OCHERED = (function () {
  "use strict";
  var BAZA = "spetsmat-offlajn", SKLAD = "tapy", ZAPAS = "spetsmat-offlajn-zapas";
  var TAJMAUT = @TAJMAUT@;                /* мс на одну попытку */
  var STARYJ = @STARYJ@ * 60000;          /* мс: граница «свежий / старый» */
  var PAUZA_NACHALO = 2000, PAUZA_POTOLOK = 30000;

  /* ── ХРАНИЛИЩЕ ────────────────────────────────────────────────────────────
     IndexedDB — основное; `localStorage` — запасное. Запасное существует не для
     красоты: в приватном окне Safari IndexedDB открывается и падает на первой же
     транзакции, и без запаса тап в этот момент исчезал бы молча — ровно то, что
     запрещено требованием 4 захода. Порядок в обоих один и тот же: возрастающий
     числовой ключ, и он же — порядок нажатий. */
  var idb = null, idb_probovali = false;

  function otkryt() {
    return new Promise(function (ok, net) {
      if (idb) { ok(idb); return; }
      if (idb_probovali || !window.indexedDB) { net(new Error("нет IndexedDB")); return; }
      var z;
      try { z = indexedDB.open(BAZA, 1); }
      catch (e) { idb_probovali = true; net(e); return; }
      z.onupgradeneeded = function () {
        var db = z.result;
        if (!db.objectStoreNames.contains(SKLAD)) {
          db.createObjectStore(SKLAD, {keyPath: "id", autoIncrement: true});
        }
      };
      z.onsuccess = function () { idb = z.result; ok(idb); };
      z.onerror = function () { idb_probovali = true; net(z.error); };
      z.onblocked = function () { idb_probovali = true; net(new Error("IndexedDB занята")); };
    });
  }

  function tranzakcia(rezhim, rabota) {
    return otkryt().then(function (db) {
      return new Promise(function (ok, net) {
        var t = db.transaction(SKLAD, rezhim), s = t.objectStore(SKLAD), itog;
        t.onerror = function () { net(t.error); };
        t.onabort = function () { net(t.error || new Error("транзакция отменена")); };
        t.oncomplete = function () { ok(itog); };
        try { rabota(s, function (v) { itog = v; }); }
        catch (e) { try { t.abort(); } catch (e2) {} net(e); }
      });
    });
  }

  /* Запасное хранилище: тот же интерфейс, тот же порядок ключей. */
  var zapas = {
    chitat: function () {
      try { return JSON.parse(localStorage.getItem(ZAPAS) || '{"n":0,"z":[]}'); }
      catch (e) { return {n: 0, z: []}; }
    },
    pisat: function (s) {
      try { localStorage.setItem(ZAPAS, JSON.stringify(s)); return true; }
      catch (e) { return false; }
    }
  };
  /* Записи, которым не досталось ни IndexedDB, ни localStorage. Живут только в
     памяти вкладки и честно теряются с ней — но НЕ теряются молча: счётчик их
     показывает, и человек видит, что тап ещё не уехал. */
  var v_pamyati = {n: 0, z: []};
  var gde = null;                 /* "idb" | "zapas" | "pamyat" — решается при первой записи */

  function dobavit(z) {
    return tranzakcia("readwrite", function (s) { s.add(z); })
      .then(function () { gde = "idb"; })
      .catch(function () {
        var s = zapas.chitat();
        s.n += 1; z.id = s.n; s.z.push(z);
        if (zapas.pisat(s)) { gde = "zapas"; return; }
        v_pamyati.n += 1; z.id = v_pamyati.n; v_pamyati.z.push(z); gde = "pamyat";
      });
  }

  function vse() {
    return tranzakcia("readonly", function (s, otdat) {
      var z = s.getAll ? s.getAll() : null;
      if (z) { z.onsuccess = function () { otdat(z.result); }; return; }
      var sobrano = [], k = s.openCursor();      /* старый Safari без getAll */
      k.onsuccess = function () {
        var c = k.result;
        if (c) { sobrano.push(c.value); c.continue(); } else { otdat(sobrano); }
      };
    }).catch(function () {
      var s = zapas.chitat();
      return s.z.length ? s.z : v_pamyati.z;
    });
  }

  function pervyj() {
    return vse().then(function (z) { return z.length ? z[0] : null; });
  }

  function udalit(id) {
    return tranzakcia("readwrite", function (s) { s.delete(id); })
      .catch(function () {
        var s = zapas.chitat();
        s.z = s.z.filter(function (z) { return z.id !== id; });
        if (!zapas.pisat(s)) {
          v_pamyati.z = v_pamyati.z.filter(function (z) { return z.id !== id; });
        }
      });
  }

  /* ── СОСТОЯНИЕ СВЯЗИ (Р7: живо · снимок свежий · снимок старый) ────────────
     🔴 ВОЗРАСТ МЕРЯЕТСЯ `performance.now()`, А НЕ `Date.now()`. Настенные часы
     телефона переводятся, врут и прыгают при смене часового пояса; заказ прямо
     запрещает закладывать их во что-либо, кроме справочного поля. `performance.now()`
     монотонен от загрузки страницы — а нам ровно и нужно «сколько прошло с последнего
     удавшегося ответа», а не «который час».
     ВРЕМЯ, КОТОРОЕ ЧИТАЕТ ЧЕЛОВЕК, приходит с сервера (`data-snyato`) и не считается
     здесь вовсе. */
  var zhivo = true;                 /* страница пришла с сервера — значит связь была */
  var udacha_v = (window.performance && performance.now) ? performance.now() : 0;
  function teper() {
    return (window.performance && performance.now) ? performance.now() : udacha_v;
  }
  function sostoyanie() {
    if (zhivo) { return "zhivo"; }
    return (teper() - udacha_v) < STARYJ ? "svezhij" : "staryj";
  }

  /* ── ПОДПИСЧИКИ ───────────────────────────────────────────────────────────── */
  var podpischiki = [];
  function podpisatsya(fn) { podpischiki.push(fn); }
  function soobshchit(sob) {
    sob.svyaz = sostoyanie();
    for (var i = 0; i < podpischiki.length; i++) {
      try { podpischiki[i](sob); } catch (e) {}
    }
  }

  /* ── ОРГАНЫ ТРАНСПОРТА: СЧЁТЧИК И БАННЕР ──────────────────────────────────── */
  var SCHYOT = null, BANNER = null, OTKAZ = null;
  function organy() {
    if (SCHYOT === null) { SCHYOT = document.getElementById("och-schyot") || false; }
    if (BANNER === null) { BANNER = document.getElementById("och-banner") || false; }
    if (OTKAZ === null) { OTKAZ = document.getElementById("och-otkaz") || false; }
  }
  function ekran(s) {
    return String(s).replace(/[&<>"]/g, function (z) {
      return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[z]; });
  }
  /* 🔴 ОТКАЗ ПИШЕТСЯ И ОСТАЁТСЯ. Ни таймера, ни перезагрузки поверх: точка 4 захода
     запрещает и то и другое. Строки НАКАПЛИВАЮТСЯ — два отказа подряд это два разных
     события, и второй не имеет права затереть первый. */
  function zapisat_otkaz(z, pochemu) {
    organy();
    if (!OTKAZ) { return; }
    var kto = (z && z.metka && z.metka.podpis) ? (ekran(z.metka.podpis) + ": ") : "";
    var stroka = "<p><b>Не сохранилось.</b> " + kto + ekran(pochemu) + "</p>";
    var knopka = OTKAZ.querySelector("button");
    if (knopka) { knopka.remove(); }
    OTKAZ.insertAdjacentHTML("beforeend", stroka);
    OTKAZ.insertAdjacentHTML("beforeend",
      '<button type="button" id="och-otkaz-x">Понятно, скрыть</button>');
    OTKAZ.hidden = false;
  }
  document.addEventListener("click", function (sob) {
    if (!sob.target.closest || !sob.target.closest("#och-otkaz-x")) { return; }
    organy();
    if (OTKAZ) { OTKAZ.innerHTML = ""; OTKAZ.hidden = true; }
  });
  function slovo(n) {
    var sto = n % 100, des = n % 10;
    if (sto > 10 && sto < 20) { return "отметок"; }
    if (des === 1) { return "отметка"; }
    if (des >= 2 && des <= 4) { return "отметки"; }
    return "отметок";
  }
  /* 🔴 ТЕКСТЫ ТРЁХ СОСТОЯНИЙ — ЭТО ОТВЕТ НА Р7, А НЕ УКРАШЕНИЕ. Каждый говорит ровно
     три вещи: что видно на экране, откуда оно, и что будет дальше. Ни один не
     обвиняет человека и ни один не предлагает ему что-то починить: чинить нечего,
     сеть вернётся сама. */
  function narisovat_organy(n) {
    organy();
    if (SCHYOT) {
      SCHYOT.hidden = !n;
      SCHYOT.textContent = n ? ("в очереди " + n + " " + slovo(n)) : "";
      /* Число стоит ещё и атрибутом. Оно нужно живому прогону
         (`tests/veb/test_offlajn_brauzer.py`): длину очереди отдаёт Promise, а
         ожидание в браузере обязано быть СИНХРОННЫМ предикатом — иначе оно видит
         сам Promise, считает его истиной и просыпается раньше времени. Поймано
         живьём: тест «отметка уехала» проходил, не дождавшись ни одной отправки. */
      SCHYOT.setAttribute("data-n", String(n));
    }
    if (!BANNER) { return; }
    var s = sostoyanie();
    if (s === "zhivo") { BANNER.hidden = true; BANNER.className = "och-banner"; return; }
    var kogda = BANNER.getAttribute("data-snyato") || "";
    BANNER.hidden = false;
    BANNER.className = "och-banner" + (s === "staryj" ? " staryj" : "");
    var hvost = n
      ? ("Отметки сохраняются здесь: " + n + " " + slovo(n)
         + " в очереди, уедут сами, как только связь вернётся.")
      : "Новые отметки будут сохранены здесь и уедут сами, как только связь вернётся.";
    BANNER.innerHTML = (s === "svezhij")
      ? "<b>Связи с сервером нет.</b> На экране данные от " + kogda + ". " + hvost
      : "<b>Связи с сервером нет дольше " + (STARYJ / 60000) + " минут.</b> На экране"
        + " данные от " + kogda + " — за это время их мог изменить кто-то другой. " + hvost;
  }
  function obnovit() {
    return vse().then(function (z) { narisovat_organy(z.length); return z.length; });
  }

  /* ── ОТПРАВКА ─────────────────────────────────────────────────────────────── */
  function poslat(z) {
    var otsechka = new AbortController();
    var budilnik = setTimeout(function () { otsechka.abort(); }, TAJMAUT);
    return fetch(z.put, {
      method: "POST", headers: {"Content-Type": "application/json"},
      signal: otsechka.signal, cache: "no-store",
      body: JSON.stringify(z.telo)
    }).then(function (r) {
      clearTimeout(budilnik);
      /* Сервер жив — значит связь есть, чем бы он ни ответил. */
      if (r.status >= 500 || r.status === 429) {
        /* Тело дочитывается и здесь: см. `proba` — недочитанный ответ держит
           соединение открытым, и следующая попытка встаёт в очередь за ним. */
        return r.text().catch(function () {}).then(function () {
          return {rod: "net-seti", pochemu: "сервер занят (" + r.status + ")",
                  zhiv: true};
        });
      }
      return r.json().catch(function () { return {}; }).then(function (d) {
        if (r.ok) { return {rod: "ok", dannye: d, zhiv: true}; }
        return {rod: "otkaz", zhiv: true,
                pochemu: (d && d.error) || ("сервер отказал (" + r.status + ")")};
      });
    }).catch(function (o) {
      clearTimeout(budilnik);
      return {rod: "net-seti", zhiv: false,
              pochemu: (o && o.name === "AbortError")
                ? ("сервер не ответил за " + (TAJMAUT / 1000) + " с") : "связи нет"};
    });
  }

  var idyot = false, pauza = PAUZA_NACHALO, budilnik_povtora = null;

  function pozzhe() {
    if (budilnik_povtora) { return; }
    budilnik_povtora = setTimeout(function () {
      budilnik_povtora = null; vyvezti();
    }, pauza);
    pauza = Math.min(pauza * 2, PAUZA_POTOLOK);
  }

  function otmetit_svyaz(zhiv) {
    var bylo = zhivo;
    zhivo = zhiv;
    if (zhiv) { udacha_v = teper(); pauza = PAUZA_NACHALO; }
    if (bylo !== zhiv) { soobshchit({rod: "svyaz"}); }
  }

  /* 🔴 ОДИН ЗАПРОС В ПОЛЁТЕ, ВСЕГДА. `idyot` — не оптимизация, а само требование
     «отправлять строго по одному в порядке очереди»: два параллельных вывоза
     поменяли бы местами два тапа по одной клетке, и последним в журнале оказался бы
     не последний нажатый. */
  function vyvezti() {
    if (idyot) { return Promise.resolve(); }
    idyot = true;
    function shag() {
      return pervyj().then(function (z) {
        if (!z) { return obnovit().then(function () {}); }
        return poslat(z).then(function (itog) {
          otmetit_svyaz(!!itog.zhiv);
          if (itog.rod === "net-seti") {
            /* Запись ОСТАЁТСЯ на месте и остаётся первой: порядок не рвётся. */
            return obnovit().then(function () { pozzhe(); });
          }
          return udalit(z.id).then(function () {
            if (itog.rod !== "ok") { zapisat_otkaz(z, itog.pochemu); }
            soobshchit({rod: itog.rod === "ok" ? "uehala" : "otkaz", zapis: z,
                        dannye: itog.dannye, pochemu: itog.pochemu});
            return obnovit().then(shag);
          });
        });
      });
    }
    return shag().catch(function () {}).then(function () { idyot = false; });
  }

  function postavit(zapis) {
    zapis.kogda = new Date().toISOString();   /* справочное поле, и только оно */
    return dobavit(zapis).then(function () {
      soobshchit({rod: "postavlena", zapis: zapis});
      return obnovit();
    }).then(function () { vyvezti(); });
  }

  /* ── ПРОБА СВЯЗИ, КОГДА ОЧЕРЕДЬ ПУСТА ──────────────────────────────────────
     Очередь пуста почти всегда, а баннер обязан гаснуть сам, без нажатий. Проба —
     самый дешёвый запрос, какой есть на сервере: без базы и без сборки страницы. */
  var proba_idyot = false;
  function proba() {
    if (proba_idyot) { return Promise.resolve(); }
    proba_idyot = true;
    var otsechka = new AbortController();
    var budilnik = setTimeout(function () { otsechka.abort(); }, TAJMAUT);
    /* 🔴 ТЕЛО ОТВЕТА ДОЧИТЫВАЕТСЯ, ХОТЯ ОНО НАМ НЕ НУЖНО, И ЭТО НЕ ПЕДАНТИЗМ.
       `fetch`, у которого не прочитали `body`, оставляет поток открытым: браузер
       считает запрос НЕЗАВЕРШЁННЫМ, соединение не освобождается, а на сервере из
       stdlib `http.server` поток обработчика висит вместе с ним. Поймано живьём:
       страница поднималась и работала, но `networkidle` не наступал никогда —
       снаружи это неотличимо от «сервер не отвечает». Восемнадцать телефонов,
       пробующих связь раз в полминуты, оставили бы столько же висящих потоков. */
    return fetch("/api/zhiv", {cache: "no-store", signal: otsechka.signal})
      .then(function (r) {
        clearTimeout(budilnik);
        return r.text().catch(function () {}).then(function () { otmetit_svyaz(r.ok); });
      })
      .catch(function () { clearTimeout(budilnik); otmetit_svyaz(false); })
      .then(function () { proba_idyot = false; return obnovit(); });
  }

  function tolknut() {
    return vse().then(function (z) { return z.length ? vyvezti() : proba(); });
  }

  /* ── КОГДА ПРОБОВАТЬ СНОВА ─────────────────────────────────────────────────
     `online` и `offline` читаются ПОДСКАЗКОЙ: на школьном wi-fi флаг говорит
     «online», когда наружу не проходит ничего. Поэтому по событию мы не меняем
     состояние, а просто пробуем раньше, чем собирались. */
  window.addEventListener("online", function () { pauza = PAUZA_NACHALO; tolknut(); });
  window.addEventListener("offline", function () { obnovit(); });
  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) { pauza = PAUZA_NACHALO; tolknut(); }
  });
  /* Пока связи нет, возраст снимка растёт, и «свежий» однажды становится «старым».
     Раз в полминуты перерисовываем баннер, чтобы граница не ждала нажатия. */
  setInterval(function () { if (!zhivo) { obnovit(); } }, 30000);

  /* Первый вывоз — при загрузке страницы: очередь могла пережить перезагрузку. */
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { tolknut(); });
  } else { tolknut(); }

  return {postavit: postavit, vse: vse, podpisatsya: podpisatsya, tolknut: tolknut,
          sostoyanie: sostoyanie, obnovit: obnovit};
})();
</script>
"""


def skript() -> str:
    """The queue script, with the two numbers of this module pushed into it.

    They are pushed rather than written out twice: `STARYJ_CHEREZ_MINUT` is also the
    number `doc/OFFLAJN.md` names and the number the tests assert, and a copy inside the
    JavaScript would drift away from all three silently.
    """
    return (_SKRIPT.replace("@TAJMAUT@", str(TAJMAUT_MS))
            .replace("@STARYJ@", str(STARYJ_CHEREZ_MINUT)))
