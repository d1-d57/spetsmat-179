#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-code — rendered by `tools/sobrat_stranicu.sobrat_html`.
"""The front page: what we are solving right now, who teaches, when, and where.

The dragon curve lives here too — it is a background of this page and of no
other. So does the search box script, because search answers questions about
pupils, teachers and sheets at once and therefore belongs to none of them.

🔴 THE CARD OF THE NEAREST SHEET IS UNDER A MACHINE LOCK. One typeface, one
size, one weight, one colour for all of its content; `proverit_shemu()` in
`tools/sobrat_stranicu.py` refuses to build the page if that is broken. Do not
add a bold word or a coloured link to it — read `doc/DIZAJN-ZAKREPLENO.md`.

It is handed `kt: Kontekst` and reads it; it opens no database and
imports no shell. What that buys is the point of the whole cut: this
file can be edited while somebody else edits the file next to it.

🔴 THE RUSSIAN COMMENTS BELOW ARE NOT TRANSLATED, ON PURPOSE. They carry the
owner's own words with the dates he said them on — "Владелец 06.09: …" — and a
translation would be a rewrite of evidence. Everything newly written here is in
English, as the задание requires; everything moved is verbatim, down to the
byte. That is also what makes the byte criterion of this refactor meaningful:
a diff between the page before and the page after can only show a mistake,
never a paraphrase.
"""
from __future__ import annotations

from veb.obshchee.karkas import VREMYA, e
from veb.razdely.listki import (
    L8_PERVOE,
    L8_VTOROE,
    L9,
    est,
    tekushchij,
)
from veb.razdely.shkolniki import gr_shk


DRAKON_SKRIPT = r"""
<script>
/* ── КРИВАЯ ДРАКОНА ХАРТЕРА—ХЕЙТУЭЯ ─────────────────────────────────────────────
   🔴 ЛИНИЕЙ СО СКРУГЛЁННЫМИ УГЛАМИ, А НЕ ЛЕСЕНКОЙ И НЕ ОБЛАКОМ ТОЧЕК.
   Первый заход рисовал её единичными шагами с острыми углами — на большом экране
   вышла пиксельная лесенка. Владелец: «плохо прорисовано… должна быть детальная,
   не пиксельная».

   Способ взят там, где он уже отработан: сайт лекции про кривую дракона
   (`materials/krivaya-drakona/sayt/src/dragon.js`) — слово складок, ломаная целыми
   координатами, скруглённые углы. Кривая рисуется одной непрерывной линией,
   которую можно проследить пальцем: это её смысл, а не её вид.

   СЛОВО СКЛАДОК. На каждом шаге к слову приписывается поворот налево и зеркально
   обращённое предыдущее слово: s = s + L + flip(s). Это буквально складывание
   полоски бумаги пополам, из которого кривая и получается.

   Ранг 13 — 8192 звена: достаточно, чтобы линия читалась как сплошная, и мало,
   чтобы рисоваться мгновенно. Холст перерисовывается при смене размера, поэтому
   на любом экране линия остаётся чёткой — в отличие от растянутой картинки. */
(function(){
  const holst = document.getElementById('drakon');
  if(!holst || !holst.getContext) return;

  /* Слово поворотов: +1 налево, −1 направо. */
  function slovo(rang){
    let s = [];
    for(let i = 0; i < rang; i++){
      const zerkalo = [];
      for(let j = s.length - 1; j >= 0; j--) zerkalo.push(-s[j]);
      s = s.concat([1], zerkalo);
    }
    return s;
  }

  /* Ломаная целыми координатами: округление обязательно, иначе поворот на 90°
     даёт 6.1e-17 вместо нуля и звенья перестают быть горизонтальными. */
  function lomanaya(rang){
    const pov = slovo(rang), shag = [[1,0],[0,1],[-1,0],[0,-1]];
    let n = 0, x = 0, y = 0;
    const tochki = [[0,0]];
    for(let i = 0; i <= pov.length; i++){
      x += shag[n][0]; y += shag[n][1];
      tochki.push([x, y]);
      if(i < pov.length) n = (n + (pov[i] === 1 ? 1 : 3)) % 4;
    }
    return tochki;
  }

  /* 🔴 РАНГ 16, А НЕ 13. На тринадцати звено занимает пять пикселей, и линия
     толщиной в половину звена слипается в кляксы — та самая «пиксельность», на
     которую пожаловался владелец. На шестнадцати звеньев 65 тысяч, каждое
     меньше двух пикселей, и кривая читается как тонкий плотный узор. Считается
     один раз при загрузке, дальше только перерисовывается. */
  const TOCHKI = lomanaya(16);

  function risovat(){
    const r = holst.getBoundingClientRect();
    if(r.width < 40 || r.height < 40) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    holst.width = Math.round(r.width * dpr);
    holst.height = Math.round(r.height * dpr);
    const ctx = holst.getContext('2d');
    ctx.clearRect(0, 0, holst.width, holst.height);

    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
    for(const [a, b] of TOCHKI){
      if(a < x0) x0 = a; if(a > x1) x1 = a;
      if(b < y0) y0 = b; if(b > y1) y1 = b;
    }
    /* Отрицательное поле: кривая НАМЕРЕННО больше холста и обрезается краями.
       Владелец: «увеличить её ещё в три раза, чтобы она вылезла за пределы».
       Обрезанная фигура читается как продолжающаяся за экран, целиком вписанная —
       как картинка на подставке. */
    const pole = -0.38;
    const mash = Math.min(holst.width * (1 - pole * 2) / (x1 - x0),
                          holst.height * (1 - pole * 2) / (y1 - y0));
    const sdvX = (holst.width - (x1 - x0) * mash) / 2;
    const sdvY = (holst.height - (y1 - y0) * mash) / 2;

    /* Цвет берётся из палитры страницы: тёмная и светлая темы переключаются
       переменными, и второй список цветов здесь неминуемо бы разъехался. */
    ctx.strokeStyle = getComputedStyle(document.documentElement)
      .getPropertyValue('--accent').trim() || '#2f6e8e';
    ctx.lineWidth = Math.max(0.7 * dpr, mash * 0.42);
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    ctx.globalAlpha = 1;
    ctx.beginPath();
    for(let i = 0; i < TOCHKI.length; i++){
      const px = sdvX + (TOCHKI[i][0] - x0) * mash;
      const py = holst.height - sdvY - (TOCHKI[i][1] - y0) * mash;
      if(i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    }
    ctx.stroke();
  }

  risovat();
  let zhdu;
  window.addEventListener('resize', function(){
    clearTimeout(zhdu); zhdu = setTimeout(risovat, 200);
  });
})();
</script>"""


#: The card of the nearest lesson, enlarged onto a panel of its own.
#:
#: 🔴 THESE RULES LIVE HERE AND NOT IN THE STYLESHEET BECAUSE THE STYLESHEET IS OUT
#: OF THE ZONE. `veb/obshchee/karkas.py` holds `.blok-listok` and belongs to the
#: заход `kanon-verstki`; this file may not edit it. A `<style>` returned by the
#: section itself is the way this project already overrides the canon from inside a
#: section — `veb/razdely/verstka_stili.STILI` and `veb/razdely/konduit.stili()` do
#: exactly this, and a `<style>` element inside `<body>` is valid HTML5 and applies
#: like one in `<head>`. Every selector below names a class the canon already
#: defines; nothing here invents a visual language.
#:
#: 🔴 IT IS EMITTED ABOVE `<div class="blok-listok">`, AND THAT POSITION IS PART OF
#: THE MACHINERY. `tools/sobrat_stranicu.proverit_shemu()` reads the slice of markup
#: FROM `<div class="blok-listok">` TO `<div class="blok-vedut">` and refuses to
#: build the page if it finds `<b>`, `class="tihoe"`, `class="net"`, `class="gr"`,
#: `class="kab"` or `class="ver"` in it. A stylesheet placed inside that slice would
#: be read as card content. Outside it, the lock is untouched — and it stays
#: untouched by what these rules DO, too: they change only size, spacing and
#: background, and add neither a weight, nor a colour, nor a plate.
#:
#: WHAT THE OWNER ASKED FOR, 09.09, in his own words: *«я бы сделал такую заглушку
#: на главной странице… прямо на каком-то другом фоне, где большими буквами написал
#: бы Следующий спецмат… там было бы написано просто: четверг, 10 сентября,
#: 13:10–15:00, листок Деревья и номера кабинетов для трёх групп. Я бы его
#: растянул раза в два по сравнению с тем, как он сейчас устроен»*.
STILI_SPETSMAT = """
<style>
/* Вдвое крупнее: канон держит карточку на `clamp(1.02rem,1.15vw,1.24rem)`,
   здесь — вдвое от него, и все её строки набраны от этого одного кегля. */
.blok-listok{margin:2.2rem 0 0;width:auto;max-width:100%;
  font-size:clamp(2.04rem,2.3vw,2.48rem);
  background:var(--panel);border:1px solid var(--rule);border-radius:18px;
  padding:1.5rem 2rem 1.7rem}
/* Подпись — та самая «большими буквами Следующий спецмат». Она набрана
   служебным серым каркаса (`.zag2`), то есть тем же вторым цветом, который
   схема карточки разрешала и раньше; растёт только кегль. */
.blok-listok .zag2{font-size:.46em;letter-spacing:.13em;margin-bottom:.35rem}
/* Название листка остаётся главным словом, но кратность к базе уменьшена:
   прежние 2.55em от вдвое большего кегля вылезли бы за колонку. */
.listok-tema{font-size:1.6em;line-height:1.1}
.listok-nom{font-size:.5em;vertical-align:.55em}
/* Строки «когда» и «кабинеты» — служебные, мельче названия, но крупнее, чем
   были: их читают издалека, стоя. */
.listok-kogda{font-size:.6em;margin-top:.2rem}
.listok-kab{font-size:.55em;margin-top:.5rem}
.listok-moyo{font-size:.5em}
/* 🔴 ЛИЧНАЯ СТРОКА ЗАМЕНЯЕТ ОБЩУЮ, И ЭТО ОТМЕНА ПРАВИЛА, СТОЯВШЕГО ЗДЕСЬ С 09.09.
   Тогда владелец просил в карточке «номера кабинетов для трёх групп», и строка
   `.blok-listok:has(.listok-moyo) .listok-obshchij{display:block}` возвращала её
   вошедшему поверх канонного правила каркаса. 10.09 он посмотрел на результат
   своими глазами и отменил его (`TZ-DOBOR-10-09.md` H2.3, H2.4): «в карточке
   дублируются кабинеты для всех групп … кабинеты для всех — не нужно», «это
   абсурдно выглядит»; личное живёт в Кабинете. Правило снято — и работает то,
   что канон каркаса и говорил: у вошедшего остаётся ЕГО кабинет и его школьники.
   Гостю, у которого личной строки нет вовсе, три кабинета видны как и раньше.
   Разметка не тронута ни на байт, значит и побайтовая сверка каркаса — тоже. */
/* Канон запрещает этой строке переноситься (`white-space:nowrap`), а на вдвое
   большем кегле «понедельник, 14 сентября · 14:15—15:55» в колонку не влезает
   и даёт горизонтальную прокрутку всей странице — то, что гейт вёрстки считает
   красным. Перенос по словам, а не сжатие кегля. */
.listok-kogda,.listok-stroka{white-space:normal !important}
/* Ссылка в свой кабинет. Стоит ПОД карточкой, а не в ней: внутри она была бы
   вторым цветом на закреплённой схеме. */
/* 🔒 ССЫЛКА НА СВОЮ ГРУППУ НАБРАНА ЦВЕТОМ КАРТОЧКИ, А НЕ СИНИМ. Замок схемы
   (`proverit_shemu()`) держит карточку в одном цвете и одном весе; браузерная
   синева ссылки была бы вторым цветом ровно там, где его быть не должно.
   Ссылка видна подчёркиванием — оно из линейки каркаса (`--rule`), — и
   акцентом при наведении, то есть только в тот момент, когда на неё смотрят. */
.listok-moyo a{color:inherit;text-decoration:none;border-bottom:1px solid var(--rule)}
.listok-moyo a:hover{border-bottom-color:var(--accent);color:var(--accent)}
@media(max-width:940px){.blok-listok{font-size:clamp(1.5rem,4.6vw,2rem);
  padding:1.1rem 1.2rem 1.3rem}}
</style>"""


# ── ЧТО СТОИТ НА ГЛАВНОЙ ────────────────────────────────────────────────
# Кабинеты ближайшего занятия — по группам, одной строкой. Неизвестные не
# выдумываются: их просто нет в строке.
def kab_skoro(kt, k):
    est = [(kod, kt.kabinety_dnya[k].get(kod)) for kod in ("В", "Д", "Н")]
    est = [(kod, v) for kod, v in est if v]
    return " · ".join(f'{kod}&nbsp;{e(v)}' for kod, v in est) if est \
        else '<span class="net">кабинеты уточняются</span>'

# 🔴 ТЕКУЩИЙ ЛИСТОК — САМОЕ ПОЛЕЗНОЕ, ЧТО ЗДЕСЬ МОЖЕТ СТОЯТЬ. Школьник заходит
# узнать, что решать; всё остальное на главной он уже знает. Берётся ПОСЛЕДНИЙ
# листок девятого класса, у которого есть хоть один файл на диске, — то есть


def razdel(kt) -> str:
    """The front page, assembled. Everything on it is counted, not written down."""
    listok_nom, listok_tema, listok_versii = tekushchij()
    listok_stroka = ""
    if listok_tema:
        versii_html = "".join(
            f'<a href="listki/{e(f)}">{e(z)}</a>' for z, f in listok_versii)
        # 🔒 Ни `<b>`, ни `class="tihoe"`: карточка набрана одним цветом и одним
        # весом целиком (см. закреплённую схему в разделе `.blok-listok`).
        # 🔴 ПРАВКА ВЛАДЕЛЬЦА 07.09: в карточке доминирует НАЗВАНИЕ листка.
        # Номер остаётся, но уходит по кеглю на второй план; название —
        # `<label for="p-list">`, то есть переводит на вкладку «Листки» БЕЗ
        # единой строки JS, той же техникой скрытых радиокнопок, что и меню.
        # Уровни A/α/ℵ по-прежнему ведут на сами файлы листка.
        # 🔒 Ни `<b>`, ни `class="tihoe"`: вес и цвет по-прежнему одни на всю
        # карточку, различает только КЕГЛЬ — этого замок не запрещает, и
        # владелец попросил именно выделения слова, а не веса или цвета.
        listok_stroka = (f'<label for="p-list" class="listok-nom">{e(listok_nom)}</label>'
                         f'<label for="p-list" class="listok-tema">{e(listok_tema)}</label>'
                         f'<span class="listok-ver">{versii_html}</span>')

    kabinety_skoro = kab_skoro(kt, kt.blizh)

    # 🔴 ПРАВКА ВЛАДЕЛЬЦА 07.09: ВОШЕДШИЙ ПРЕПОДАВАТЕЛЬ ВИДИТ В ЭТОЙ ЖЕ КАРТОЧКЕ
    # СВОЙ ОДИН КАБИНЕТ И ФАМИЛИИ СВОИХ ШКОЛЬНИКОВ.
    #
    # 🔒 ПОЧЕМУ ОБЩАЯ СТРОКА КАБИНЕТОВ ОСТАЁТСЯ В РАЗМЕТКЕ, А НЕ УБИРАЕТСЯ.
    # `proverit_karkas()` сверяет ПОБАЙТОВО две пары страниц: гость против
    # организатора и (проверкой, которую завела личная страница в
    # `veb/server.py`) гость против преподавателя. Пометка `data-tolko-gost`
    # снимается ТОЛЬКО с гостевой, `data-org` — только со страницы, у которой
    # возможность есть. Убери общую строку у преподавателя — и она осталась бы
    # у организатора, то есть первая пара разошлась бы; пометь её
    # `data-tolko-gost` — разошлась бы вторая. Поэтому в разметке стоят ОБЕ
    # строки, личная помечена `data-org="videt-svoyo"` и снимается при сверке,
    # а прячет общую строку у преподавателя CSS — на сравнение он не влияет.
    #
    # 🔒 И ГЛАВНОЕ: фамилии школьников сюда попадают ТОЛЬКО при `prepod_id`,
    # то есть после входа личным паролем. Гостевая сборка (`rezhim="gost"`,
    # `prepod_id is None`) их не содержит вовсе, а именно она уезжает в
    # `docs/index.html` публичного репозитория.
    moyo_html = ""
    if kt.prepod_id is not None:
        from veb.razdely.lichnaya import (kabinet_na_datu, deti_na_datu,
                                          segodnya as _segodnya)
        _den = _segodnya()
        _kab = kabinet_na_datu(kt.c, kt.prepod_id, _den)
        _deti = deti_na_datu(kt.c, kt.prepod_id, _den)
        _familii = ", ".join(e(r["surname"]) for r in _deti)
        _kab_txt = e(_kab) if _kab else "кабинет не назначен"
        _hvost = (f' · {_familii}' if _familii
                  else ' · на сегодня никого не записано')
        # 🔴 СВОЯ ГРУППА — ССЫЛКА (H1.3: «посмотреть свою группу нельзя»). Ведёт на
        # распределение на занятие, то есть туда, где эта группа и разложена.
        # Спрашивается у `kt.prep`, который уже прочитан для страницы: второго
        # запроса к базе ради одной буквы здесь не заводится.
        _svoy = kt.prep.get(kt.prepod_id) or {}
        _gruppa = _svoy["gruppa"] if "gruppa" in _svoy.keys() else None
        _gr_html = (f'<a href="/raspredelenie">группа {e(_gruppa)}</a> · '
                    if _gruppa else '')
        moyo_html = (f'\n          <p class="listok-kab listok-moyo" '
                     f'data-org="videt-svoyo">{_gr_html}{_kab_txt}{_hvost}</p>')

    # 🔴 КНОПКА «МОЙ КАБИНЕТ» УБРАНА ИЗ ТЕЛА СТРАНИЦЫ, ПОТОМУ ЧТО СТАЛА ВКЛАДКОЙ.
    # Она стояла здесь как единственная ссылка на `/kabinet`, которую тот заход мог
    # поставить: пункт меню живёт в `veb/obshchee/karkas.py::obolochka()`, и та
    # зона до него не доставала. Долг закрыт 10.09 — «Кабинет» стоит в верхнем
    # меню вторым, после «Класса». Владелец в тот же день назвал и остаток:
    # *«кнопка „Мой кабинет“ стоит в теле страницы, должна быть вкладкой в верхнем
    # меню, и называться просто „Кабинет“ — не „мой“»* (`TZ-DOBOR-10-09.md` H2.1).
    # Две двери в одно место — это ровно то повторение, от которого страница и
    # чистится; уходит та, что стоит не на месте.
    ssylka_v_kabinet = ""
    tekushchij_listok = tekushchij()

    # ── ДАННЫЕ ДЛЯ СТРАНИЦЫ КЛАССА ──────────────────────────────────────────
    # Всё, что можно посчитать, считается из базы. Вписано руками только то, чего
    # в базе нет: кто какой предмет ведёт и кто классный руководитель — этого
    # система не знает и знать пока негде.
    klassy = {}
    for r in kt.shk:
        if r["class"]:
            klassy[r["class"]] = klassy.get(r["class"], 0) + 1

    # 🔴 НЕ-ЛЮДИ ИЗ СПИСКА ВЫКИДЫВАЮТСЯ. В таблице преподавателей живут служебные
    # строки «отсутствует» и «НС» — это не люди, а способ сказать «никого». Дом у
    # этого знания один и он не здесь: `veb/sobrat_fajl.NE_LYUDI`.
    from veb.sobrat_fajl import NE_LYUDI
    vse_prepy = kt.c.execute("select name, aktiven from teachers order by name").fetchall()
    # 🔴 ЧЕТВЕРО ВЕДУЩИХ В СПИСОК ПРИНИМАЮЩИХ НЕ ПОПАДАЮТ. Они уже названы выше,
    # в «кто ведёт», и второе упоминание — то самое повторение, от которого мы
    # избавляемся по всему сайту. Владелец: «мы и так введём алгебру, геометрию и
    # спецмат, это не нужно». Список от этого короче и крупнее.
    VEDUT = {"Ольга Рыжая", "Наталия Стрелкова", "Даня Макаров", "Ваня Яковлев"}
    seychas = sorted({r["name"] for r in vse_prepy
                      if r["name"] not in NE_LYUDI and r["aktiven"]
                      and r["name"] not in VEDUT},
                     key=lambda s: s.lower())
    ranshe = sorted({r["name"] for r in vse_prepy
                     if r["name"] not in NE_LYUDI and not r["aktiven"]},
                    key=lambda s: s.lower())
    spisok_prepodavatelej = "".join(f"<li>{e(n)}</li>" for n in seychas)
    byvshie_html = ('<div class="zag2 ranshe-zag">Принимали раньше</div>'
                    '<ul class="prep-spisok ranshe">'
                    + "".join(f"<li>{e(n)}</li>" for n in ranshe) + "</ul>") if ranshe else ""

    # Кабинеты в подписи расписания: показываем те, что известны, и честно молчим,
    # когда их нет. Владелец назначает их накануне, и «уточняются» — нормальное
    # состояние, а не дефект.
    # 🔴 КАБИНЕТЫ БЛИЖАЙШЕГО ЗАНЯТИЯ, А НЕ ПОНЕДЕЛЬНИЧНЫЕ. Здесь стояло жёсткое
    # `["pn"]`, и в четверг карточка показывала кабинеты ПОНЕДЕЛЬНИКА: владелец
    # 10.09 записал на четверг В 301 · Н 207, страница распределения показала их
    # верно, а главная — старые «В 203 · Д 302 · Н 202», и он увидел это первым.
    # День ближайшего занятия знает `kt.blizh`; тот же ключ уже берёт `kab_skoro`
    # четырьмя строками выше — жёсткая «pn» была единственным местом, где день
    # выдумывался вместо того, чтобы спрашиваться.
    izvestnye = [f'{kod}&nbsp;{e(kt.kabinety_dnya[kt.blizh][kod])}'
                 for kod in ("В", "Д", "Н") if kt.kabinety_dnya[kt.blizh].get(kod)]
    kabinety_podpis = ("кабинеты: " + " · ".join(izvestnye)) if izvestnye \
        else '<span class="net">кабинеты уточняются</span>'
    return f"""<section class="str holst" id="s-start">{STILI_SPETSMAT}
  <!-- 🔴 КРИВАЯ ЛЕЖИТ ПОД ВСЕЙ СТРАНИЦЕЙ И ВЫХОДИТ ЗА КРАЯ, а текст стоит НА ней.
       Две колонки «слева текст, справа картинка» владелец назвал ужасной вёрсткой,
       и он прав: так картинка не взаимодействует с текстом, а стоит рядом. Здесь
       она заполняет собой весь экран, обрезается краями — и потому кажется больше
       экрана, — а содержание разложено поверх неё в двух потоках: главное слева,
       боковое справа. -->
  <div class="glav">
    <div class="glav-risunok"><canvas id="drakon" aria-hidden="true"></canvas></div>

    <header class="glav-shapka">
      <h1 class="glav-imya">Математический класс</h1>
      <p class="glav-pod">9&nbsp;КЛ · школа №&nbsp;179</p>
    </header>

    <div class="glav-setka">
      <div class="glav-glavnoe">
        <!-- 🔴 АКЦЕНТ НА ЛИСТОК, А НЕ НА ДАТУ. Владелец: «сейчас ты даёшь акцент
             на ближайшее занятие, а нужно на то, что мы сейчас решаем». Дата ушла
             в строку под листком и набрана мелко: «7 сент» вместо «7 сентября»,
             потому что длинная дата давила на то, ради чего блок существует. -->
        <!-- 🔴 ТРИ УРОВНЯ, СВЕРХУ ВНИЗ: когда · что решаем · где. Прежний блок
             владелец назвал разлапистым, и он им был: тема шла кеглем крупнее
             заголовка страницы и спорила с ним, а версии висели отдельной
             строкой сами по себе. Теперь тема набрана вровень с датой, версии
             стоят в той же строке, что и она, и весь блок читается как одна
             карточка, а не как четыре разных куска. -->
        <div class="blok-listok">
          <span class="zag2">следующий спецмат</span>
          <p class="listok-kogda">{e(kt.DNI[kt.blizh][0])}, {e(kt.po_russki(kt.DNI[kt.blizh][2]))}
            · {VREMYA[kt.blizh]}</p>
          <p class="listok-stroka">{listok_stroka}</p>
          <p class="listok-kab listok-obshchij">{kabinety_skoro}</p>{moyo_html}
        </div>{ssylka_v_kabinet}

        <div class="blok-vedut">
          <span class="zag2">Кто ведёт</span>
          <table class="vedut"><tbody>
            <tr><td class="predmet">алгебра</td><td>Ольга Рыжая</td></tr>
            <tr><td class="predmet">геометрия</td><td>Наталия Стрелкова</td></tr>
            <tr><td class="predmet">спецмат</td><td>Даня Макаров, Ваня Яковлев</td></tr>
            <tr><td class="predmet">классные руководители</td>
                <td><span class="imya-celikom">Дарья Аракелова</span>,
                    <span class="imya-celikom">Радий Скребцов</span></td></tr>
          </tbody></table>
        </div>
      </div>

      <aside class="glav-sboku">
        <div class="sboku-blok">
          <span class="zag2">Расписание спецмата</span>
          <table class="rasp"><tbody>
            {"".join(f'<tr><td class="den-imya">{e(kt.DNI[k][0])}</td>'
                     f'<td class="den-vremya">{VREMYA[k]}</td></tr>' for k in kt.DNI)}
          </tbody></table>
        </div>
        <div class="sboku-blok">
          <span class="zag2">Принимающие</span>
          <ul class="prep-spisok">{spisok_prepodavatelej}</ul>
          {byvshie_html}
        </div>
      </aside>
    </div>
  </div>
</section>"""


def poisk_skript(kt) -> str:
    """The search box: pupils, teachers and sheets in one index, built at build time.

    The page is static, so the answer to "who does this child go to" is frozen
    into it here rather than asked of a server that may be off.
    """
    return f"""<script>
// Поиск ищет и школьника, и преподавателя, подсказывает от двух букв: людей мало.
const IMENA = {[e(f'{r["surname"]} {r["name"]}') for r in kt.shk] + [e(t["name"]) for t in kt.prep.values()]
               + [e(f'{n} {tema}') for n, tema, _ in L9] + [e(f'{n} {nz}') for n, nz, _ in L8_PERVOE + L8_VTOROE if n]!r};
// Школьник → {{id, группа}}. Клик по школьнику теперь ВЕДЁТ на его группу, а не
// пишет текст поверх страницы — владелец 09.09, дословно: «мне нужно не
// открыть вот эту странную полоску, ... а перевести меня на страницу с
// распределением группы В, чтобы я увидел Ивана Фефелова, с другой стороны —
// его преподавателя». Группа пустой строкой — школьник нигде, и открывается
// вкладка «школьникам», а не «В»/«Д»/«Н» (см. скрипт перехода ниже).
const UCHENIKI = {{{",".join(
  f'"{e(r["surname"])} {e(r["name"])}":{{"id":{r["id"]},"g":"{e(gr_shk(kt, r) or "")}"}}' for r in kt.shk
)}}};
// Что показать по найденному ПРЕПОДАВАТЕЛЮ или ЛИСТКУ — текстом на месте, как
// и раньше: это не тот адрес, на который владелец пожаловался.
const KOMU = {{{",".join(
  [f'"{e(n)} {e(tema)}":"листок 9 класса · {" · ".join(z for z, f in vs if est("listki", f))}"' for n, tema, vs in L9]
+ [f'"{e(n)} {e(nz)}":"листок 8 класса"' for n, nz, fl in L8_PERVOE + L8_VTOROE if n and est("listki-8kl", fl)]
+ [f'"{e(t_["name"])}":"{e(", ".join(sorted(r["surname"] + " " + r["name"] for r in kt.shk if r["teacher_id"] == t_["id"])) or "школьников нет")} · {e(t_["gruppa"] or "—")} · {e(kt.kabinety.get(t_["gruppa"]) or "кабинет не назначен")}"' for t_ in kt.prep.values()]
)}}};
const poisk=document.getElementById('poisk'),spisok=document.getElementById('spisok'),nashli=document.getElementById('nashli');
poisk.addEventListener('input',e=>{{
  const q=e.target.value.trim().toLowerCase(); nashli.innerHTML='';
  if(q.length<2){{spisok.hidden=true;return;}}
  const r=IMENA.filter(n=>n.toLowerCase().includes(q)).slice(0,8);
  spisok.innerHTML=r.map(n=>'<div>'+n+'</div>').join(''); spisok.hidden=!r.length;
}});
spisok.addEventListener('click',e=>{{
  if(e.target.tagName!=='DIV')return;
  const n=e.target.textContent; spisok.hidden=true;
  // 🔴 ШКОЛЬНИК — ПЕРЕХОДОМ, ПРЕПОДАВАТЕЛЬ/ЛИСТОК — ПО-СТАРОМУ, ТЕКСТОМ. Уйти с
  // адреса распределения дальше можно как угодно (назад, другая вкладка меню) —
  // сбрасывать здесь нечего, это обычная навигация браузера.
  const uch = UCHENIKI[n];
  if(uch){{
    location.href = '/raspredelenie?sid=' + uch.id
      + (uch.g ? '&g=' + encodeURIComponent(uch.g) : '');
    return;
  }}
  poisk.value=n;
  nashli.innerHTML = KOMU[n] ? '<div class="otvet"><b>'+n+'</b> → '+KOMU[n]+'</div>' : '';
}});
// 🔴 УХОД КЛИКОМ МИМО ГАСИТ И ПОДСКАЗКИ, И ОТВЕТ. Раньше гас только `spisok`;
// `nashli` (ответ по преподавателю/листку) оставался висеть, пока не наберут
// новый запрос заново, — то самое «полоску невозможно закрыть, не сбросив
// человека», только уже для НЕ-школьника. Дублирует часть жалобы 09.09, но
// чинится тем же способом и в том же файле, что и переход школьника.
document.addEventListener('click',e=>{{
  if(!e.target.closest('.podskazki')){{spisok.hidden=true;nashli.innerHTML='';}}
}});

// 🔴 ПРИШЛИ ПО ССЫЛКЕ ИЗ ПОИСКА — ВКЛАДКА ГРУППЫ И ПОДСВЕТКА СТРОКИ. `sid`/`g`
// читаются из адреса при каждой загрузке, а не запоминаются нигде: обычная
// навигация, уйти можно куда угодно, ничего не сбрасывая. Работает на любом
// адресе распределения — на занятии и на постоянном каркас один и тот же.
(function(){{
  const q = new URLSearchParams(location.search);
  const sid = q.get('sid');
  if(!sid) return;
  const g = q.get('g');
  const vk = g && document.getElementById('t-' + g);
  if(vk) vk.checked = true;
  const stroka = document.querySelector('[data-shk-id="' + CSS.escape(sid) + '"]');
  if(stroka){{ stroka.classList.add('podsvechen'); stroka.scrollIntoView({{block:'center'}}); }}
}})();

// Поиск на РАСПРЕДЕЛЕНИИ: прячет строки, не совпавшие с фамилией или именем.
// Работает разом во всех вкладках и в обеих половинах строки — искать надо там,
// где смотришь.
// 🔴 ВЫБОРА ДНЯ ПРИ ОТКРЫТИИ БОЛЬШЕ НЕТ, И ЭТО НЕ УПРОЩЕНИЕ, А СЛЕДСТВИЕ. Здесь
// стояло `getElementById('d-cht').checked = true` — отметить четверг во вторник,
// среду и четверг. Переключателя дней не существует с решения владельца 5 от
// 07.09 (одна табличка на оба дня), радиокнопок `d-pn`/`d-cht` в странице нет, и
// строка бросала `TypeError` на КАЖДОМ открытии, обрывая весь скрипт ниже —
// вместе с поиском.
//
// 🔴 ПОИСК ИЩЕТ В ТОМ ПОЛЕ, КОТОРОЕ НА СТРАНИЦЕ ЕСТЬ. Здесь стояло `poisk-r` —
// id, которого в разметке нет НИ ОДНОГО, и не было до этого захода: замерено
// и на боевом сайте (`grep -c 'id="poisk-r"'` → 0), и в `HEAD~2`. То есть
// `pr` был `null`, строка ниже бросала второй `TypeError`, и поиск по
// распределению не работал вовсе — молча, потому что консоль никто не открывал.
// Поле поиска на этой странице одно, наверху, и его id — `poisk`.
const pr=document.getElementById('poisk');
pr.addEventListener('input',e=>{{
  const q=e.target.value.trim().toLowerCase();
  // 🔴 `[data-i]` НА ОБОИХ СЕЛЕКТОРАХ. Строка-шапка столбцов «пн · чт» — тоже
  // `.para`, но искомого имени не несёт и `data-i` не имеет; без фильтра поиск
  // падал на `undefined.includes` на первой же букве и не прятал НИЧЕГО.
  document.querySelectorAll('#s-rasp .para[data-i], #s-rasp tr[data-i]').forEach(d=>{{
    d.classList.toggle('skryt', !!q && !d.dataset.i.includes(q) &&
      !d.textContent.toLowerCase().includes(q));
  }});
}});
</script>"""
