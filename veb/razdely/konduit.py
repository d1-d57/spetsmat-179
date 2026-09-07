#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-code — rendered by `veb.obshchee.karkas.obolochka`
# whenever the role being served has the capability `videt-konduit`.
"""The кондуит: who handed in which problem, read only.

WHAT THIS SECTION IS. The paper conduit was one table per листок — pupils down,
problems across, a tick in the cell. This is that table, on screen, for all 21
листков at once, plus the two views the paper never had: the whole year on one
grid, and one pupil's own record. Nothing on it edits anything: no form, no
`POST`, no `INSERT`. Marking is a different position of the wave with a zone of
its own, and the owner named only existence and readability as obligatory here.

🔴 THERE IS ONE READING OF THE JOURNAL AND IT IS NOT IN THIS FILE. What a cell
means — the state of the pair (pupil, problem) is its LAST event — lives in
`core/services/progress.py`, and this section asks that service through
`states_for_many`, exactly as `tools/export_xlsx.py` does. A second reading here
would be a second opinion about what a plus means, and the day the two disagree
the teacher believes the screen while the owner believes the workbook. The rule
is not a preference: "второго журнала отметок не заводить" is declared a failure
of the whole wave in the мандат.

The consequence worth stating in numbers, because it is the mistake this file
exists to not make: the журнал holds 15 900 events, of which 15 165 are
`assert` — and the number of handed-in cells is **14 430**, not either of those.
735 `retract` events take earlier marks back. Anyone who prints `count(*)` shows
the owner hundreds of solved problems that are not solved.

🔴 THE ALPHABET IS IMPORTED, NOT RETYPED. `1` credited, `x` handed in and not
credited, empty nothing — the signs come from `tools.export_xlsx.SIGN`, which in
turn is the reading side of `VALUE_REGISTRY` in `tools/import_konduit.py`. A copy
of that dictionary here would be a third place for it to drift, and the owner
would end up with two conduits wearing different signs.

🔴 «ТОЛЬКО МОИ» IS A FILTER AND NEVER A PERMISSION. A teacher sees the WHOLE
кондуит; the checkbox only narrows what is drawn. The reason is the owner's, and
it is about the lesson rather than about privacy: he regularly takes other
people's children (`doc/PLAN-veb-2026-09.md:89`). The narrowing is done in CSS,
by `display:none` on rows, so nothing is withheld by the server and nothing has
to be re-fetched to widen it again.

🔴 THIS SECTION HAS NO JAVASCRIPT, AND THAT IS LOAD-BEARING RATHER THAN TIDY.
The tabs are radio inputs and `:checked ~` rules — the device the rest of this
site already uses. The решётка has to open on a laptop with no internet, so
nothing is fetched, nothing is scripted, and no font or stylesheet is loaded
from anywhere.
"""
from __future__ import annotations

from core.services.progress import ProgressService
from infra.repositories import SqliteCatalogue, SqliteMarkJournal
from tools.export_xlsx import SIGN
from veb.obshchee.karkas import e
from veb.razdely.lichnaya import deti_na_datu, segodnya


def _uchastniki(catalogue) -> tuple:
    """The pupils on the roll today, and everybody the кондуит has a record of.

    Two lists, because the two are needed for different questions and answering
    both with one list is how a screen starts lying. The GRID is drawn for those
    on the roll — the same predicate every other list of pupils on this site uses
    (`veb/razdely/shkolniki.shkolniki`: `status is null or status <> 'left'`), 53
    of the 57 rows in `students`. The TOTAL of handed-in cells is counted over
    all 57, because a year that a pupil solved does not stop having happened when
    they leave, and because that is the number `tools/export_xlsx.py` writes.

    Both numbers are printed on the page side by side rather than one of them
    quietly standing for the other.
    """
    vse = catalogue.students()
    na_uchyote = [s for s in vse if (s.status or "") != "left"]
    return na_uchyote, vse


def _moi_deti(kt) -> set:
    """The ids of the children of the person who is looking, or an empty set.

    🔴 THE SEAM IS CALLED, NOT REWRITTEN. `students_of(teacher_id, on_date)` does
    not exist — checked across all 43 branches of this repository, zero hits — but
    the same question does, under another name: `veb.razdely.lichnaya.deti_na_datu`,
    which V2 shipped for the personal page. It holds the two properties of
    `enrollment` that decide the answer and that a fresh query gets wrong: an open
    row is `valid_to = '9999-12-31'` and never `NULL` (`valid_to is null` matches 0
    rows out of 186), and some open rows start in the FUTURE, so the test has to be
    the full interval `valid_from <= day and day < valid_to`
    (`infra/enrollment_repo.py:122-127`). Writing a second one here would have
    reproduced both traps for nothing.

    An empty set means nobody in particular is looking — the organiser, or a
    teacher who came in by the COMMON password — and the checkbox is then not
    drawn at all. A filter that hides everyone is worse than no filter.
    """
    if kt.prepod_id is None:
        return set()
    return {r["id"] for r in deti_na_datu(kt.c, kt.prepod_id, segodnya())}


def _daty(kt) -> dict:
    """(pupil, problem) → the date of the last event on that pair. WHEN, never WHAT.

    🔴 THIS IS NOT A SECOND READING OF THE JOURNAL, AND THE LINE IS EXACT: the
    query below never selects the column `event` and never decides anything about
    a cell. WHAT a cell is stays the answer of `ProgressService.states_for_many`
    and of nothing else; this only says when the event that the projection already
    chose was dated. Take `event` from here as well and the file would have grown
    the second opinion its whole docstring refuses.

    One query instead of fourteen thousand calls to `last_event`, riding the same
    index `marks_lookup (student_id, problem_id, id)` the projection rides.
    """
    return {(r["student_id"], r["problem_id"]): r["valid_at"] for r in kt.c.execute("""
        select m.student_id, m.problem_id, m.valid_at
        from marks m
        join (select student_id, problem_id, max(id) as last_id
                from marks group by student_id, problem_id) last
          on last.last_id = m.id
    """)}


def _obzor(na_uchyote, listki, zadachi, sostoyaniya, chuzhoj, imya="vse") -> str:
    """Cut one: the whole year on one grid — a row per pupil, a column per листок.

    In the cell "credited of total" for that листок. This is the view the owner
    asked the conduit for in the first place: it answers "who stalled where"
    without opening anything. The surname is a `<label>`, and pressing it opens
    that pupil's own record — cut three, and the whole of "по щелчку на фамилии"
    with no script behind it.
    """
    shapka = "".join(f'<th class="zn" title="{e(sh.title or "")}">{e(sh.number)}</th>'
                     for sh in listki)
    stroki = []
    for u in na_uchyote:
        kletki = []
        for sh in listki:
            zad = zadachi[sh.id]
            vzyato = sum(1 for p in zad if sostoyaniya[(u.id, p.id)].is_credited)
            if not zad:
                kletki.append('<td></td>')
            elif vzyato == len(zad):
                kletki.append(f'<td class="vsyo">{vzyato}</td>')
            elif vzyato:
                kletki.append(f'<td>{vzyato}<span class="iz">/{len(zad)}</span></td>')
            else:
                kletki.append('<td class="pusto">·</td>')
        # Тот же признак, что и в разрезе одного листка: класс ставится на СВОИХ.
        # 07.09 он стоял только там, и на общей вкладке свои не выделялись вовсе —
        # владелец увидел это раньше, чем я.
        klass = (' class="chuzh"' if u.id in chuzhoj
                 else (' class="moi"' if chuzhoj else ""))
        stroki.append(
            f'<tr{klass}><td class="kto"><label for="k-u{u.id}">'
            f'<b>{e(u.surname)}</b> {e(u.name)}</label></td>{"".join(kletki)}</tr>')
    return (f'<section class="vid" id="n-{imya}">'
            f'<table class="kond" style="max-width:{16 + len(listki) * 5.5:.1f}em">'
            f'<thead><tr><th>Ученик</th>{shapka}</tr></thead>'
            f'<tbody>{"".join(stroki)}</tbody></table></section>')


def _listok(sh, zad, na_uchyote, sostoyaniya, chuzhoj) -> str:
    """Cut two: one листок, in the alphabet of the workbook — `1`, `x`, empty.

    This is the table `tools/export_xlsx.py` writes to a worksheet, drawn on
    screen from the same call to the same service, so the two cannot disagree.
    The signs are `SIGN` itself, imported: `1` credited, `x` handed in and not
    credited, an empty cell nothing written.
    """
    if not zad:
        telo = '<p class="net">в этом листке ещё нет задач</p>'
    else:
        shapka = "".join(f'<th class="zn">{e(p.label)}</th>' for p in zad)
        stroki = []
        for u in na_uchyote:
            kletki = []
            for p in zad:
                znak = SIGN[sostoyaniya[(u.id, p.id)]]
                # 🔴 АДРЕС ПАРЫ НА КАЖДОЙ КЛЕТКЕ — ЭТО ВСЁ, ЧТО НУЖНО ДЛЯ ТАПА.
                # Владелец 07.09: «я хочу, чтобы можно было нажимать на пустую
                # клеточку на кондуите и чтобы там появлялась галочка… вид остаётся
                # тем же самым, просто клетки должны тапаться». Поэтому здесь не
                # появилось ни кнопки, ни формы, ни единого нового знака: те же
                # `<td>` с теми же классами, плюс два атрибута, по которым скрипт
                # каркаса знает, какую пару он отмечает. Запись идёт в ЕДИНСТВЕННУЮ
                # дверь `veb/priyom.py::otmetka` (`/api/priyom`), то есть через
                # `MarkingService`; второго журнала здесь по-прежнему нет, и этот
                # раздел по-прежнему не пишет в базу сам.
                adres = f' data-u="{u.id}" data-z="{p.id}"'
                if znak == "1":
                    # 🔴 ПРАВКА ВЛАДЕЛЬЦА 07.09: сдано — это ГАЛОЧКА, не единица.
                    # Алфавит клетки от этого не меняется: `tools/export_xlsx.py`
                    # по-прежнему пишет `1`, а решётка на экране рисует тот же
                    # факт знаком, который читается быстрее. Снятое (`x`) и
                    # пустое — как были.
                    kletki.append(f'<td class="vsyo"{adres}>✓</td>')
                elif znak:
                    kletki.append(f'<td class="snyato"{adres}>{znak}</td>')
                else:
                    kletki.append(f'<td{adres}></td>')
            # 🔴 ПРАВКА ВЛАДЕЛЬЦА 07.09: СВОИ ШКОЛЬНИКИ ВЫДЕЛЯЮТСЯ ЦВЕТОМ.
            # Класс ставится на СВОИХ, а не выводится как «отсутствие чужого»:
            # у организатора и у общего пароля своих нет вовсе (`chuzhoj` пуст),
            # и правило `tr:not(.chuzh)` покрасило бы им всех до одного.
            klass = (' class="chuzh"' if u.id in chuzhoj
                     else (' class="moi"' if chuzhoj else ""))
            stroki.append(f'<tr{klass}><td class="kto">'
                          f'<b>{e(u.surname)}</b> {e(u.name)}</td>{"".join(kletki)}</tr>')
        potolok = 16 + len(zad) * 5.5
        telo = (f'<table class="kond" style="max-width:{potolok:.1f}em">'
                f'<thead><tr><th>Ученик</th>{shapka}</tr></thead>'
                f'<tbody>{"".join(stroki)}</tbody></table>')
    return (f'<section class="vid" id="n-{sh.id}">'
            f'<p class="zag2">{e(sh.title or sh.number)}</p>{telo}</section>')


def _uchenik(u, listki, zadachi, sostoyaniya, daty) -> str:
    """Cut three: one pupil's own record — his листки, what is on them, and when.

    A line per листок: how many of it he has, then every problem he touched, each
    carrying the date of the event that decides its state. Листки he has not
    touched at all are still listed: a листок missing from the record looks like
    a листок that never existed, which is the same mistake the workbook refuses
    to make by giving every sheet a worksheet.
    """
    stroki = []
    for sh in listki:
        zad = zadachi[sh.id]
        if not zad:
            continue
        vzyato = sum(1 for p in zad if sostoyaniya[(u.id, p.id)].is_credited)
        fishki = []
        for p in zad:
            sost = sostoyaniya[(u.id, p.id)]
            znak = SIGN[sost]
            if not znak:
                continue
            fishki.append((p, znak, daty.get((u.id, p.id))))
        if fishki:
            spisok = "".join(
                f'<i class="{"vsyo" if z == "1" else "snyato"}"'
                f'{f" title={chr(34)}{e(k)}{chr(34)}" if k else ""}>{e(p.label)}</i>'
                for p, z, k in fishki)
        else:
            spisok = '<span class="net">ничего не отмечено</span>'
        stroki.append(
            f'<tr><td class="kto">{e(sh.number)}</td>'
            f'<td class="skolko">{vzyato} из {len(zad)}</td>'
            f'<td class="fishki">{spisok}</td></tr>')
    return (f'<section class="vid" id="n-u{u.id}">'
            f'<p class="zag2"><label for="k-vse">← ко всем</label></p>'
            f'<h2 class="kond-imya">{e(u.surname)} {e(u.name)}</h2>'
            f'<table class="kond-lich"><tbody>{"".join(stroki)}</tbody></table></section>')


def _sobrat(kt):
    """Everything both `razdel` and `stili` need, read once.

    The two are called one after the other by the shell, and the catalogue is the
    same catalogue both times; reading it twice would be two chances for the tabs
    and the panels to be built from different lists of листки.
    """
    catalogue = SqliteCatalogue(kt.c)
    progress = ProgressService(SqliteMarkJournal(kt.c), catalogue)
    na_uchyote, vse = _uchastniki(catalogue)
    listki = catalogue.sheets()
    zadachi = {sh.id: catalogue.problems_of_sheet(sh.id) for sh in listki}
    return catalogue, progress, na_uchyote, vse, listki, zadachi


def stili(kt) -> str:
    """The CSS the section needs, and not one colour or size that is not already here.

    `doc/DIZAJN-ZAKREPLENO.md` §0: a new page TAKES the palette, the sizes and the
    devices of what already stands. Every value below is a variable this stylesheet
    already defines. What is genuinely new is only the tab plumbing — show my panel
    when my radio is checked — and it has to be generated rather than written out,
    because there is one panel per листок and one per pupil and both lists live in
    the база.
    """
    _c, _p, na_uchyote, _v, listki, _z = _sobrat(kt)
    klyuchi = ["vse9", "vse8"] + [str(sh.id) for sh in listki]
    vkladki = "".join(
        f"#k-{k}:checked~#n-{k}{{display:block}}"
        f"#k-{k}:checked~.tabbar label[for=k-{k}]"
        "{color:var(--accent);background:var(--panel);"
        "border-color:var(--rule) var(--rule) var(--panel)}"
        for k in klyuchi)
    lyudi = "".join(f"#k-u{u.id}:checked~#n-u{u.id}{{display:block}}" for u in na_uchyote)
    return f"""
/* Кондуит — вкладка меню, её разделы и решётка. */
/* 🔴 ПРАВКА ВЛАДЕЛЬЦА 07.09: деление на классы, по умолчанию девятый.
   Переключатель — те же скрытые радиокнопки, что и везде на этой странице:
   ни строки JS. Вкладки чужого класса не прячутся `display:none` у меток,
   а именно снимаются из потока — иначе полоса вкладок держала бы пустое
   место там, где стояли восемнадцать листков восьмого класса. */
#s-kond .kond-klassy{{display:flex;gap:.4rem;margin:.2rem 0 .9rem}}
#s-kond .kond-klassy label{{cursor:pointer;font-family:var(--sans);font-weight:600;
  font-size:1.05rem;color:var(--muted);padding:.35em 1.1rem;border-radius:8px;
  border:1px solid var(--rule)}}
#s-kond .kond-klassy label:hover{{color:var(--text);background:var(--accent-soft)}}
#kl-9:checked~.kond-klassy label[for=kl-9],
#kl-8:checked~.kond-klassy label[for=kl-8]{{color:var(--accent);
  background:var(--accent-soft);border-color:var(--accent)}}
#kl-9:checked~.tabbar .kl8{{display:none}}
#kl-8:checked~.tabbar .kl9{{display:none}}
#p-kond:checked~#s-kond{{display:block}}
#p-kond:checked~.menu label[for=p-kond]{{color:var(--accent);background:var(--accent-soft)}}
{vkladki}{lyudi}
/* «Только мои» — фильтр строк, и ничего кроме. Ни одна строка не удерживается
   сервером: снял галочку — снова видно всех. */
#k-moi:checked~.vid tr.chuzh{{display:none}}
/* 🔴 Свои школьники видны цветом и слева полосой — без этого «только мои»
   остаётся единственным способом их найти, а владелец просил видеть их и в
   общем списке. Ни одного нового цвета: `--accent` уже несёт «моё» по всему
   сайту, `--accent-soft` — фон выбранной вкладки. */
#s-kond .kond tbody tr.moi td{{background:var(--accent-soft)}}
/* 🔴 ПОЛОСА СТОИТ В ОТСТУПЕ, А НЕ ПОВЕРХ ФАМИЛИИ. Владелец 07.09: «мелочь, но
   вот тут наезжает вертикальная линия на фамилии» — `box-shadow:inset` рисуется
   ВНУТРИ ячейки, поэтому при прежнем отступе полоса ложилась на первую букву.
   Лечится отступом слева у своих строк, а не снятием полосы: без неё своих детей
   в общем списке не найти, о чём владелец просил отдельно. */
#s-kond .kond tbody tr.moi td.kto{{color:var(--accent);
  box-shadow:inset .22rem 0 0 0 var(--accent);padding-left:.85rem}}
#s-kond .kond tbody tr.moi td.kto b{{color:var(--accent)}}
/* Наведение обязано оставаться отличимым от «своей» строки, иначе выделение
   съедает подсветку: у своих строк фон уже накрашен, поэтому наведение
   различается рамкой на клетке и полосой столбца, а не цветом фона. */
#s-kond .kond tbody tr.moi:hover td{{background:var(--chip)}}
/* Клетка листка тапается: курсор и подсветка обещают действие, которое есть.
   Клетки годового обзора и личной карточки адреса пары не несут и остаются
   обычным текстом — там столбец это ЛИСТОК, а не задача, и отмечать нечего. */
#s-kond .kond td[data-u]{{cursor:pointer}}
#s-kond .kond td[data-u]:hover{{background:var(--accent-soft)}}
#s-kond .kond td[data-u].zhdyot{{opacity:.5}}
#s-kond .kond-verh{{display:flex;align-items:baseline;justify-content:space-between;
  gap:1.5rem;flex-wrap:wrap}}
#s-kond .kond-moi{{cursor:pointer;font-family:var(--sans);font-weight:600;font-size:1rem;
  color:var(--muted);padding:.35em 1rem;border:1px solid var(--rule);border-radius:8px;
  white-space:nowrap}}
#s-kond .kond-moi::before{{content:"☐\\00a0"}}
#k-moi:checked~.kond-verh .kond-moi{{color:var(--accent);background:var(--accent-soft);
  border-color:var(--accent)}}
#k-moi:checked~.kond-verh .kond-moi::before{{content:"☑\\00a0"}}
#s-kond .tabbar label{{padding:.4rem .7rem;font-size:1rem}}
/* 🔴 ПРАВКА ВЛАДЕЛЬЦА 07.09. Решётка занимала половину доступной ширины при
   шестнадцати задачах — на экране, где текстовая область тянется во всю ширину,
   это читается как ошибка вёрстки, а не как замысел. Клетка расширена ВДВОЕ,
   решётка получила линии, шапка закреплена, и наведение показывает столбец
   целиком. Ни одного нового цвета: всё из уже объявленных переменных. */
/* 🔴 ПРАВКА ВЛАДЕЛЬЦА 07.09, вторая: решётка занимала половину экрана.
   Теперь она ТЯНЕТСЯ во всю доступную ширину (`width:100%`), а чтобы при трёх
   столбцах девятого класса клетка не разъехалась на пол-экрана, потолок
   считается по числу столбцов и приезжает инлайном на самой таблице:
   имя + столбцы × 5.5em. Инлайн здесь дешевле класса: таблиц двадцать две,
   а клеток тридцать одна тысяча. */
#s-kond table.kond{{font-size:.95rem;width:100%;border-collapse:separate;
  border-spacing:0}}
#s-kond .kond th.zn{{padding:.5rem .2rem;text-align:center;font-size:.78rem;
  min-width:3em;border-bottom:2px solid var(--rule);border-left:1px solid var(--rule)}}
/* 🔴 4rem — это ИЗМЕРЕННАЯ высота меню (64px при корневом кегле 16px), а не
   прикидка: при 3.4rem шапка уезжала под меню на десять пикселей, и владелец
   это увидел. Меню — `position:sticky;top:0`, его высота задана его же
   padding'ом .9rem сверху и снизу плюс строка 1.05rem. Изменится меню —
   изменить и здесь; проверяется одной командой: высота `.menu` в браузере. */
#s-kond .kond thead th{{position:sticky;top:4rem;z-index:6;background:var(--panel)}}
#s-kond .kond thead th:first-child{{left:0;z-index:7;text-align:left;
  border-bottom:2px solid var(--rule)}}
#s-kond .kond td.kto{{white-space:nowrap;padding:.3rem 1.2rem .3rem 0;font-size:.95rem;
  position:sticky;left:0;z-index:4;background:var(--bg);
  border-bottom:1px solid var(--rule)}}
#s-kond .kond td.kto label{{cursor:pointer}}
#s-kond .kond td.kto label:hover{{color:var(--accent)}}
/* Каждая клетка КРОМЕ первой в строке — это клетка кондуита. Класс на ней не
   пишется: тридцать одна тысяча клеток × `class="z"` — четверть мегабайта на
   странице, которая обязана открываться на ноутбуке. */
#s-kond .kond tbody td+td{{text-align:center;padding:.42rem .3rem;
  font-family:var(--sans);font-size:1rem;min-width:3em;position:relative;
  border-left:1px solid var(--rule);border-bottom:1px solid var(--rule)}}
#s-kond .kond tbody td.vsyo{{color:var(--accent);font-weight:600}}
#s-kond .kond tbody td.snyato{{color:var(--warm);font-weight:600}}
#s-kond .kond tbody td.pusto{{color:var(--faint)}}
/* Наведение: подсвечивается СТРОКА и весь СТОЛБЕЦ до самой шапки. Столбец
   рисуется псевдоэлементом в полную высоту таблицы — так наведение на пустую
   клетку показывает, о какой задаче речь, и делает это без единой строки JS.
   ⚠ Обёртки с `overflow` здесь НЕТ намеренно: она сделала бы себя ближайшим
   прокручиваемым предком, и шапка липла бы к её верху, а не к окну — то есть
   ровно не то, что просили. Ширина решётки при двадцати одном столбце по 3em
   укладывается в экран владельца 1710px; если когда-нибудь перестанет —
   прокрутится страница целиком, и шапка останется на месте. */
#s-kond .kond tbody tr:hover td{{background:var(--accent-soft)}}
#s-kond .kond tbody tr:hover td.kto{{background:var(--accent-soft)}}
#s-kond .kond tbody td+td:hover::after{{content:"";position:absolute;
  left:0;width:100%;top:-100vh;height:200vh;background:var(--accent-soft);
  z-index:-1;pointer-events:none}}
#s-kond .kond tbody td+td:hover{{outline:2px solid var(--accent);outline-offset:-2px}}
#s-kond .kond .iz{{color:var(--faint);font-size:.75rem}}
#s-kond .kond-imya{{font-family:var(--sans);font-size:1.5rem;font-weight:600;margin:0 0 1rem}}
#s-kond .kond-lich td{{vertical-align:baseline}}
#s-kond .kond-lich .kto{{font-family:var(--sans);font-weight:600;white-space:nowrap;
  padding-right:1.2rem}}
#s-kond .kond-lich .skolko{{color:var(--muted);white-space:nowrap;padding-right:1.2rem;
  font-family:var(--sans);font-size:.9rem}}
#s-kond .kond-lich i{{display:inline-block;font-style:normal;font-family:var(--sans);
  font-size:.85rem;background:var(--chip);border-radius:6px;padding:.05em .45em;
  margin:0 .25em .25em 0}}
#s-kond .kond-lich i.vsyo{{color:var(--accent)}}
#s-kond .kond-lich i.snyato{{color:var(--warm)}}"""


def razdel(kt) -> str:
    """The кондуит section, ready to hang in the shell.

    🔴 `data-org="videt-konduit"` ON THE SECTION IS LOAD-BEARING, NOT DECORATION,
    AND IT IS WHAT KEEPS FIFTY-SEVEN CHILDREN OFF THE PUBLIC INTERNET. This
    element sits inside the window both frame gates compare — from `id="s-rasp"`
    to the first `\\n<script>` — and `_snyat_organy` in `tools/sobrat_stranicu.py`
    removes it by that attribute before comparing the remainder with the guest
    page. Take the attribute off and both gates report a frame that has drifted;
    render the section outside a capability check and the surnames and the record
    of every pupil land in `docs/index.html`, which
    `veb/server.py::_peresobrat` rewrites after every successful write to the
    база and which this repository publishes.
    """
    _c, progress, na_uchyote, vse, listki, zadachi = _sobrat(kt)
    vse_zadachi = [p for sh in listki for p in zadachi[sh.id]]
    sostoyaniya = progress.states_for_many([s.id for s in vse],
                                           [p.id for p in vse_zadachi])
    daty = _daty(kt)

    sdano_vsego = sum(1 for s in sostoyaniya.values() if s.is_credited)
    na_uchyote_ids = {u.id for u in na_uchyote}
    sdano_na_uchyote = sum(1 for (sid, _pid), s in sostoyaniya.items()
                           if s.is_credited and sid in na_uchyote_ids)
    vybyli = [s for s in vse if s.id not in na_uchyote_ids]

    moi = _moi_deti(kt)
    chuzhoj = ({u.id for u in na_uchyote} - moi) if moi else set()

    # 🔴 ГАЛОЧКА РИСУЕТСЯ ТОЛЬКО ТОГДА, КОГДА ЕСТЬ КОГО ФИЛЬТРОВАТЬ. Организатор и
    # общий пароль — это «никто в частности» (`veb/vhod.py::proverit_parol` отдаёт
    # `uid = None`), и галочка «только мои» у них спрятала бы всех до одного.
    if moi:
        galka = '<input class="rd" type="checkbox" id="k-moi">'
        metka_galki = (f'<label class="kond-moi" for="k-moi">только мои '
                       f'<span class="iz">({len(moi)})</span></label>')
    else:
        galka = metka_galki = ""

    # 🔴 ПРАВКА ВЛАДЕЛЬЦА 07.09: КОНДУИТ ДЕЛИТСЯ НА КЛАССЫ, ПО УМОЛЧАНИЮ ДЕВЯТЫЙ.
    # Признак класса берётся из ЕДИНСТВЕННОГО места, где он уже объявлен —
    # списка `L9` в `veb/razdely/listki.py`, откуда страница листков рисует
    # раздел девятого класса. Второго источника не заводится: в таблице `sheets`
    # признака класса нет вовсе, и завести его тут значило бы объявить схему
    # данных из отрисовки.
    from veb.razdely.listki import L9
    nomera_9 = tuple(nom for nom, _tema, _versii in L9)
    listki_9 = [sh for sh in listki if sh.number.startswith(nomera_9)]
    listki_8 = [sh for sh in listki if sh not in listki_9]

    radio = ('<input class="rd" type="radio" name="kl" id="kl-9" checked>'
             '<input class="rd" type="radio" name="kl" id="kl-8">'
             '<input class="rd" type="radio" name="knd" id="k-vse9" checked>'
             '<input class="rd" type="radio" name="knd" id="k-vse8">'
             + "".join(f'<input class="rd" type="radio" name="knd" id="k-{sh.id}">'
                       for sh in listki)
             + "".join(f'<input class="rd" type="radio" name="knd" id="k-u{u.id}">'
                       for u in na_uchyote))
    klassy = ('<div class="kond-klassy">'
              '<label for="kl-9">9 класс</label>'
              '<label for="kl-8">8 класс</label></div>')
    vkladki = ('<div class="tabbar">'
               '<label class="kl9" for="k-vse9">Весь год</label>'
               '<label class="kl8" for="k-vse8">Весь год</label>'
               + "".join(f'<label class="kl9" for="k-{sh.id}">{e(sh.number)}</label>'
                         for sh in listki_9)
               + "".join(f'<label class="kl8" for="k-{sh.id}">{e(sh.number)}</label>'
                         for sh in listki_8)
               + "</div>")
    panely = (_obzor(na_uchyote, listki_9, zadachi, sostoyaniya, chuzhoj, "vse9")
              + _obzor(na_uchyote, listki_8, zadachi, sostoyaniya, chuzhoj, "vse8")
              + "".join(_listok(sh, zadachi[sh.id], na_uchyote, sostoyaniya, chuzhoj)
                        for sh in listki)
              + "".join(_uchenik(u, listki, zadachi, sostoyaniya, daty)
                        for u in na_uchyote))

    return (f'<section class="str holst" id="s-kond" data-org="videt-konduit">'
            f'{galka}{radio}'
            f'<div class="kond-verh"><div>'
            f'<h1>Кондуит</h1>'
            f'</div>{metka_galki}</div>'
            f'{klassy}{vkladki}{panely}</section>')
