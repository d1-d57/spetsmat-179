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

from datetime import datetime, timezone

from core.services.history import zanyatie_dlya, zanyatie_po_iso
from core.services.progress import ProgressService
from infra.repositories import SqliteCatalogue, SqliteMarkJournal
from tools.export_xlsx import SIGN
from veb.obshchee.karkas import e
from veb.razdely.istoria import perebivki
from veb.razdely.lichnaya import deti_na_datu, segodnya


# ── ЗНАЧКИ ЛИСТКА ──────────────────────────────────────────────────────────
# 🔴 THE GLYPH IS THE SHEET'S OWN, NOT A NEW ALPHABET INVENTED FOR THE SCREEN.  The paper
# листок prints `◦` beside a problem that has to be handed in, `†` beside one that has to
# be handed in IN WRITING and `⋆` beside a hard one, and the conduit lost all three when
# the problems were entered — the owner on 2026-09-09: «в кондуите, где написаны номера
# задач, не отмечены кружочки и крестики… это должно быть прямо в кондуите видно».  So
# the mark drawn here is the same character, in the same meaning, and the pupil comparing
# screen with paper does not have to learn a second notation.
#
# `problems.kind` IS WHERE IT COMES FROM, and that is the whole point of the заход this
# was written in: the kind is DATA, written by `tools/import_listka.py` out of the PDF, so
# the neighbouring заход that counts "сколько обязательных сдано" reads the same column
# and cannot end up with a different answer than the screen shows.
ZNACHKI = {"обязательная": "◦", "письменная": "†", "звезда": "⋆"}
#: The class the glyph is drawn with, one per kind.  Latin, short and stable: it is
#: repeated once per column header of every листок.
ZNACHOK_KLASS = {"обязательная": "ob", "письменная": "pi", "звезда": "zv"}


def znachok(kind: str) -> str:
    """The mark for one problem's kind, ready to sit beside its number, or ``""``.

    An unknown kind draws NOTHING rather than a question mark.  `двойная` is the live
    example — two rows in `problems` carry it, nobody now knows what the senior meant by
    `**`, and a glyph invented for it here would be this file making a claim about
    somebody's data that no source backs.  `обычная` draws nothing for the honest reason:
    the sheet prints nothing beside it.
    """
    if kind not in ZNACHKI:
        return ""
    return '<i class="pm %s">%s</i>' % (ZNACHOK_KLASS[kind], ZNACHKI[kind])


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


def _samyj_novyj(kt, listki) -> int | None:
    """The id of the листок that opens by itself, ASKED OF THE БАЗА at draw time.

    🔴 THE ANSWER IS A QUERY AND NOT A CONSTANT, and that is the whole of the owner's
    request: «по умолчанию открывается самый новый листок».  Write the id into the code
    and the next листок issued has to be found by whoever notices the site is opening on
    the wrong one; ask the база and the листок that appears opens itself.

    NEWEST IS `issued_at`, NOT `ord`, and the difference is not academic on the sheets
    this site is serving right now.  `16A`, `16α` and `16ℵ` are ONE листок in three
    strengths — `veb/razdely/listki.L9` holds them as a single row `("16", "Деревья",
    [A, α, ℵ])` — so their `ord` runs 19, 20, 21 while all three carry the same
    `issued_at` of 2026-09-03.  Ordering by `ord` would open `16ℵ`, the weakest version,
    for everybody; ordering by the date and breaking the tie by `ord` opens `16A`, which
    is what the owner sees on his own page and asked for.

    ONLY A ЛИСТОК WITH CELLS CAN BE THE DEFAULT.  A row in `sheets` whose problems have
    not been imported yet is not yet a листок anybody can look at, and opening on it
    would greet the teacher with «в этом листке ещё нет задач» at the exact moment the
    next листок is being entered.  It becomes the default the moment it has a column.

    Returns ``None`` when there is nothing to open — an empty база, or a class whose
    листки all stand without cells.  The caller then falls back to «Весь год», which is
    where the conduit opened before this was written.
    """
    if not listki:
        return None
    mesta = ",".join("?" * len(listki))
    stroka = kt.c.execute(
        "select s.id from sheets s "
        "where s.id in (%s) and exists (select 1 from problems p where p.sheet_id = s.id) "
        "order by s.issued_at desc, s.ord asc limit 1" % mesta,
        [sh.id for sh in listki]).fetchone()
    return stroka[0] if stroka else None


def _daty(kt) -> dict:
    """(pupil, problem) → the LESSON DAY the last event on that pair counts towards.

    🔴 THIS IS NOT A SECOND READING OF THE JOURNAL, AND THE LINE IS EXACT: the
    query below never selects the column `event` and never decides anything about
    a cell. WHAT a cell is stays the answer of `ProgressService.states_for_many`
    and of nothing else; this only says when the event that the projection already
    chose was dated. Take `event` from here as well and the file would have grown
    the second opinion its whole docstring refuses.

    One query instead of fourteen thousand calls to `last_event`, riding the same
    index `marks_lookup (student_id, problem_id, id)` the projection rides.

    🔴 ЭТО ДЕНЬ ЗАНЯТИЯ, А НЕ МОМЕНТ ЗАПИСИ, и правило владельца 09.09 живёт в
    ОДНОМ месте — `core/services/history.zanyatie_dlya`: галочка относится к
    последнему НАЧАВШЕМУСЯ занятию по московскому времени, так что поставленная в
    пятницу или в понедельник до начала она всё равно четверговая. Здесь правило
    только зовётся. Ответ кэшируется по строке `valid_at`: у 15 847 импортных
    событий она одна на всех, и без кэша одно и то же вычислялось бы четырнадцать
    тысяч раз на каждой пересборке страницы (а страница пересобирается после
    КАЖДОЙ записи в базу — `veb/server.py::_peresobrat`).

    Перебивка (`mark_lesson_override`) сильнее правила и читается тем же адаптером,
    что и панель истории, — второго чтения этой таблицы в проекте нет.
    """
    posledniye = list(kt.c.execute("""
        select m.id, m.student_id, m.problem_id, m.valid_at
        from marks m
        join (select student_id, problem_id, max(id) as last_id
                from marks group by student_id, problem_id) last
          on last.last_id = m.id
    """))
    ruchnye = perebivki(kt.c, [r["id"] for r in posledniye])
    pamyat: dict = {}
    daty = {}
    for r in posledniye:
        kogda = ruchnye.get(r["id"], r["valid_at"])
        if kogda not in pamyat:
            pamyat[kogda] = zanyatie_po_iso(kogda)
        daty[(r["student_id"], r["problem_id"])] = pamyat[kogda]
    return daty


def _kratko(den: str) -> str:
    """`2026-09-10` → `10.09` — то, что помещается под галочкой в клетке 3em шириной.

    Год не пишется: кондуит показывает один учебный год, и четыре лишних знака
    съели бы ровно ту ширину, из-за которой владелец уже просил расширить клетку.
    """
    return "%s.%s" % (den[8:10], den[5:7])


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


def _listok(sh, zad, na_uchyote, sostoyaniya, chuzhoj, daty) -> str:
    """Cut two: one листок, in the alphabet of the workbook — `1`, `x`, empty.

    This is the table `tools/export_xlsx.py` writes to a worksheet, drawn on
    screen from the same call to the same service, so the two cannot disagree.
    The signs are `SIGN` itself, imported: `1` credited, `x` handed in and not
    credited, an empty cell nothing written.
    """
    if not zad:
        telo = '<p class="net">в этом листке ещё нет задач</p>'
    else:
        # The glyph rides in the column header and nowhere else: one mark per COLUMN,
        # twenty-one of them on the widest листок, instead of one per cell — the same
        # grid holds thirty-one thousand cells, and a mark repeated in every one of them
        # would be both unreadable and a quarter of a megabyte on a page that has to open
        # on a laptop with no internet.
        shapka = "".join(f'<th class="zn">{e(p.label)}{znachok(p.kind)}</th>' for p in zad)
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
                # 🔴 ДАТА СДАЧИ СТОИТ У ГАЛОЧКИ, И ОНА ПРИЕЗЖАЕТ АТРИБУТОМ, А НЕ
                # ТЕКСТОМ. Владелец 09.09 просил видеть, «когда и кто её поставил»;
                # «когда» помещается прямо в клетку, «кто» — в историю по жесту.
                # Атрибут, а не вложенный узел, по одной живой причине: скрипт
                # кондуита в `veb/obshchee/karkas.py` (не зона этой позиции)
                # перерисовывает клетку после тапа через `td.textContent = ЗНАК`,
                # то есть СНОСИТ всё содержимое узла. Атрибут это переживает, и
                # дату рисует `::before` в стилях ниже. Пустой клетке дата не
                # ставится: у неё нет события, о котором можно было бы сказать
                # «когда», и 16 500 лишних атрибутов на странице тоже не нужны.
                kogda = daty.get((u.id, p.id))
                if znak and kogda:
                    adres += f' data-d="{_kratko(kogda)}"'
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
                f'{f" title={chr(34)}{e(k)}{chr(34)}" if k else ""}>{e(p.label)}'
                f'{znachok(p.kind)}</i>'
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


#: Панель истории клетки и жест, которым она открывается.
#:
#: 🔴 ВИДИМОЙ МЕТКИ НА КЛЕТКЕ НЕТ — решение владельца 09.09: «правый клик на десктопе,
#: долгое зажатие на телефоне, видимой метки не заводить». Кондуит остаётся ровно тем,
#: каким владелец его принял; в разметке появились только атрибут даты на клетке и эта
#: панель, свёрнутая до жеста.
#:
#: 🔴 СКРИПТ ЖИВЁТ ЗДЕСЬ, А НЕ В `veb/obshchee/karkas.py`, И ЭТО НЕ СТИЛЬ. Каркас — не
#: зона этой позиции, а раздел ею является; и раздел ЦЕЛИКОМ снимается со страницы
#: гостя по `data-org="videt-konduit"` (`tools/sobrat_stranicu._snyat_organy` считает
#: вложенные теги, поэтому скрипт внутри секции уходит вместе с ней). То есть ни один
#: гейт каркаса его не видит и в `docs/index.html` он не попадает — там нет и самой
#: секции. По той же причине здесь НЕТ переноса строки перед `<script>`: окно, которое
#: сверяют оба гейта, кончается на первом `\n<script>`.
#:
#: 🔴 ДОЛГОЕ ЗАЖАТИЕ ОБЯЗАНО ГАСИТЬ ПОСЛЕДУЮЩИЙ ТАП. Клик по клетке ставит отметку
#: (слушатель каркаса на `document`), и без гашения «посмотреть историю» на телефоне
#: означало бы «поставить галочку». Гасится перехватом на ФАЗЕ ПОГРУЖЕНИЯ
#: (`addEventListener(..., true)`): она проходит раньше всплывающего слушателя каркаса,
#: и другого способа опередить чужой слушатель, не трогая его файл, нет.
ISTORIA_SKRIPT = """<div class="kl-ist" id="kl-ist" hidden>\
<div class="kl-ist-verh"><b id="kl-ist-kto"></b>\
<span class="kl-ist-chto" id="kl-ist-chto"></span>\
<button type="button" class="kl-ist-x" id="kl-ist-x" aria-label="закрыть">✕</button></div>\
<div class="kl-ist-telo" id="kl-ist-telo"></div></div><script>
(function () {
  var PANEL = document.getElementById("kl-ist");
  if (!PANEL) { return; }
  var TELO = document.getElementById("kl-ist-telo");
  var KTO = document.getElementById("kl-ist-kto");
  var CHTO = document.getElementById("kl-ist-chto");
  var ZANYATIE_SEGODNYA = "%(segodnya)s";   // день занятия, к которому пойдёт новый тап
  var ZADERZHKA = 550;                      // мс: столько держат палец, чтобы это было «зажатие»
  var tekushchaya = null;                   // клетка, чья история открыта
  var tajmer = null, gasit_klik = false, nachalo = null;

  function ekran(s) { return String(s).replace(/[&<>"]/g, function (z) {
    return {"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;"}[z]; }); }

  function zakryt() { PANEL.hidden = true; tekushchaya = null; }

  function postavit(td) {
    // Рядом с клеткой на ноутбуке, шторкой снизу на телефоне (там позиция снимается
    // медиазапросом). Панель прижимается к краю окна, если у края не помещается.
    //
    // 🔴 ВЕРХНИЙ КРАЙ — ЭТО НИЗ МЕНЮ, А НЕ НОЛЬ. Меню липкое и рисуется поверх; панель,
    // прижатая к нулю, уезжает ПОД него вместе со своей шапкой — с фамилией, задачей и
    // кнопкой «закрыть». Случай не выдуманный: когда лента длинная, панель не помещается
    // ни под клеткой, ни над ней, и прежняя редакция клала её на 8 пикселей от верха
    // окна — то есть под меню. На боевой базе клетки с семью событиями есть уже сегодня
    // (ученик 23, задача 582), и их панель выше трёхсот пикселей.
    // Высоту меню спрашиваем у самого меню — то же решение и по той же причине, что и у
    // липкой шапки решётки (`--vysota-menu`), только здесь она нужна в пикселях сразу.
    var r = td.getBoundingClientRect();
    PANEL.hidden = false;
    var menu = document.querySelector(".menu");
    var verh = menu ? Math.max(8, menu.getBoundingClientRect().bottom + 6) : 8;
    var w = PANEL.offsetWidth, h = PANEL.offsetHeight;
    var x = Math.min(Math.max(8, r.left), Math.max(8, window.innerWidth - w - 8));
    var y = r.bottom + 6;
    if (y + h > window.innerHeight - 8) { y = r.top - h - 6; }
    y = Math.min(Math.max(verh, y), Math.max(verh, window.innerHeight - h - 8));
    PANEL.style.left = x + "px";
    PANEL.style.top = y + "px";
  }

  function narisovat(d) {
    KTO.textContent = d.kto;
    CHTO.textContent = d.chto;
    if (!d.sobytia.length) {
      TELO.innerHTML = '<p class="kl-ist-net">по этой клетке ещё ничего не отмечали</p>';
      return;
    }
    var vybor = d.zanyatiya.map(function (z) {
      return '<option value="' + ekran(z.den) + '">' + ekran(z.vid) + "</option>"; }).join("");
    TELO.innerHTML = d.sobytia.map(function (s) {
      return '<div class="kl-ist-ryad' + (s.tehnicheskoe ? " teh" : "") + '">'
        + '<span class="kl-ist-chto2">' + ekran(s.chto) + "</span>"
        + '<span class="kl-ist-kto2">' + ekran(s.kto) + "</span>"
        + '<span class="kl-ist-kogda">' + ekran(s.kogda) + "</span>"
        + (s.tehnicheskoe ? '<span class="kl-ist-teh">техническое</span>' : "")
        + '<label class="kl-ist-zan">занятие '
        + '<select data-mark="' + s.id + '">' + vybor + "</select>"
        + (s.perebito ? '<span class="kl-ist-ruka">перебито</span>' : "") + "</label>"
        + "</div>"; }).join("");
    // Выбранным стоит то занятие, к которому событие отнесено СЕЙЧАС.
    d.sobytia.forEach(function (s) {
      var sel = TELO.querySelector('select[data-mark="' + s.id + '"]');
      if (sel && s.zanyatie) { sel.value = s.zanyatie; }
    });
  }

  function otkryt(td) {
    tekushchaya = td;
    KTO.textContent = "";
    CHTO.textContent = "";
    TELO.innerHTML = '<p class="kl-ist-net">читаю журнал…</p>';
    postavit(td);
    fetch("/api/istoria?student=" + (+td.dataset.u) + "&problem=" + (+td.dataset.z))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (tekushchaya !== td) { return; }        // успели открыть другую клетку
        if (d && d.sobytia) { narisovat(d); postavit(td); }
        else { TELO.innerHTML = '<p class="kl-ist-net">'
                 + ekran((d && d.error) || "историю не отдали") + "</p>"; }
      })
      .catch(function (o) {
        TELO.innerHTML = '<p class="kl-ist-net">' + ekran("не прочиталось: " + o) + "</p>"; });
  }

  // ── жест: правый клик на ноутбуке
  document.addEventListener("contextmenu", function (sob) {
    var td = sob.target.closest && sob.target.closest("#s-kond .kond td[data-u]");
    if (!td) { return; }
    sob.preventDefault();
    otkryt(td);
  });

  // ── жест: долгое зажатие на телефоне
  document.addEventListener("pointerdown", function (sob) {
    var td = sob.target.closest && sob.target.closest("#s-kond .kond td[data-u]");
    if (!td || sob.button) { return; }
    nachalo = {x: sob.clientX, y: sob.clientY};
    tajmer = setTimeout(function () {
      tajmer = null; gasit_klik = true; otkryt(td); }, ZADERZHKA);
  });
  function otmenit() { if (tajmer) { clearTimeout(tajmer); tajmer = null; } }
  document.addEventListener("pointerup", otmenit);
  document.addEventListener("pointercancel", otmenit);
  document.addEventListener("scroll", otmenit, true);
  document.addEventListener("pointermove", function (sob) {
    if (!tajmer || !nachalo) { return; }
    if (Math.abs(sob.clientX - nachalo.x) > 8 || Math.abs(sob.clientY - nachalo.y) > 8) {
      otmenit();                                   // это прокрутка, а не зажатие
    }
  });
  // Гашение тапа, который пришёл бы следом за зажатием: фаза погружения — раньше
  // слушателя каркаса, ставящего отметку.
  document.addEventListener("click", function (sob) {
    if (!gasit_klik) { return; }
    gasit_klik = false;
    if (sob.target.closest && sob.target.closest("#s-kond .kond td[data-u]")) {
      sob.preventDefault(); sob.stopPropagation();
    }
  }, true);

  // ── перебивка занятия
  TELO.addEventListener("change", function (sob) {
    var sel = sob.target.closest && sob.target.closest("select[data-mark]");
    if (!sel) { return; }
    sel.disabled = true;
    fetch("/api/istoria/zanyatie", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({mark: +sel.dataset.mark, zanyatie: sel.value})
    }).then(function (r) { return r.json(); }).then(function (d) {
      if (d && d.sobytia) {
        narisovat(d);
        // Клетка обязана показать ту же дату, что и лента: они об одном событии.
        if (tekushchaya && d.sobytia.length && d.sobytia[0].zanyatie) {
          pometit(tekushchaya, d.sobytia[0].zanyatie);
        }
      } else {
        sel.disabled = false;
        TELO.insertAdjacentHTML("afterbegin", '<p class="kl-ist-net">'
          + ekran((d && d.error) || "не перебилось") + "</p>");
      }
    }).catch(function () { sel.disabled = false; });
  });

  // ── закрытие
  document.getElementById("kl-ist-x").addEventListener("click", zakryt);
  document.addEventListener("keydown", function (sob) {
    if (sob.key === "Escape") { zakryt(); } });
  document.addEventListener("click", function (sob) {
    if (PANEL.hidden) { return; }
    if (sob.target.closest && sob.target.closest("#kl-ist")) { return; }
    zakryt();
  });

  // ── дата в клетке обязана пережить чужую перерисовку
  //
  // Скрипт каркаса после тапа делает `td.textContent = ЗНАК[состояние]` — то есть
  // ставит новый знак, ничего не зная о дате. Дата приезжает атрибутом и рисуется
  // `::before`, поэтому она НЕ стирается — но становится вчерашней. Наблюдатель ниже
  // ловит именно ту перерисовку и приводит дату к правилу: у отмеченной клетки —
  // сегодняшнее занятие, у опустевшей — никакой.
  function pometit(td, den) {
    if (den) { td.setAttribute("data-d", den.slice(8, 10) + "." + den.slice(5, 7)); }
    else { td.removeAttribute("data-d"); }
  }
  var setka = document.getElementById("s-kond");
  if (setka && window.MutationObserver) {
    var nablyudatel = new MutationObserver(function (izmenenia) {
      izmenenia.forEach(function (i) {
        var uzel = i.target.nodeType === 1 ? i.target : i.target.parentNode;
        var td = uzel && uzel.closest && uzel.closest("#s-kond .kond td[data-u]");
        if (!td) { return; }
        pometit(td, td.textContent.trim() ? ZANYATIE_SEGODNYA : "");
      });
    });
    nablyudatel.observe(setka, {subtree: true, childList: true,
                                characterData: true, attributes: true,
                                attributeFilter: ["class"]});
    setka._nablyudatel_daty = nablyudatel;   // ссылка живёт: без неё Chrome соберёт её
  }
})();
</script>"""


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
/* 🔴 ШАПКА ЛИПНЕТ К НИЗУ МЕНЮ, И ВЫСОТУ МЕНЮ СООБЩАЕТ САМО МЕНЮ.
   `--vysota-menu` ставит скрипт кондуита (`veb/obshchee/karkas.py`), измеряя живой
   `.menu`; 4rem осталось запасным значением — это высота меню на ноутбуке (64px),
   и она верна ровно там. Раньше это число стояло здесь жёстко, и на телефоне меню
   в 53px оставляло под собой щель в 11px, а при переносе меню на две строки шапка
   и вовсе оказывалась ПОД ним — снаружи это выглядело как «на телефоне шапка не
   залипает». Прежний комментарий требовал «изменится меню — изменить и здесь»:
   теперь менять нечего. */
#s-kond .kond thead th{{position:sticky;top:var(--vysota-menu,4rem);z-index:6;
  background:var(--panel)}}
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
/* 🔴 ДАТА СДАЧИ ПОД ГАЛОЧКОЙ. Владелец 09.09 просил видеть у галочки, «когда и кто её
   поставил»; «когда» стоит прямо в клетке, «кто» открывается жестом.
   Три решения, и каждое оплачено устройством этой страницы:
   1. Рисуется `::before` из АТРИБУТА, а не вложенным узлом. Скрипт кондуита
      (`veb/obshchee/karkas.py`, не зона этой позиции) после тапа делает
      `td.textContent = ЗНАК` и снёс бы любой вложенный узел; атрибут это переживает.
   2. `::before`, а не `::after`: `::after` этой же клетки уже занят подсветкой столбца
      при наведении (правило ниже), и второго псевдоэлемента у узла не бывает.
   3. Место под дату отводится ВСЕМ клеткам листка (`td[data-u]`), а не только
      отмеченным: иначе строка, где сдана одна задача, стала бы выше соседних, и
      решётка поехала бы ступеньками. Клетки годового обзора и личной карточки адреса
      пары не несут и остаются как были. */
#s-kond .kond tbody td[data-u]{{padding-bottom:1rem}}
#s-kond .kond tbody td[data-d]::before{{content:attr(data-d);position:absolute;
  left:0;right:0;bottom:.1rem;font-family:var(--sans);font-size:.6rem;line-height:1;
  font-weight:400;letter-spacing:-.02em;color:var(--muted);pointer-events:none}}
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
/* ── ЗНАЧОК ЛИСТКА У НОМЕРА ЗАДАЧИ ────────────────────────────────────────
   Значок стоит НАДСТРОЧНО и вплотную к номеру: колонка шириной 3em, а номер
   бывает трёхсимвольный (`13б`, `-1в`), и значок на общей строке отодвинул бы
   номер из середины клетки. Кегль крупнее номера — иначе `◦` при .78rem
   неотличим от точки. Ни одного нового цвета: `--accent` уже несёт «твоё, важное»
   по всему сайту, `--warm` — «внимание» (им же покрашено снятое), `--faint` —
   «фон, а не сообщение». Разные ЦВЕТА, а не только разные символы: четыре десятка
   значков в строке различаются полосой цвета раньше, чем формой. */
#s-kond .kond th.zn .pm{{font-style:normal;font-size:.9rem;line-height:1;
  vertical-align:super;margin-left:.05em}}
#s-kond .pm.ob{{color:var(--accent)}}
#s-kond .pm.pi{{color:var(--warm);font-weight:700}}
#s-kond .pm.zv{{color:var(--faint)}}
/* Словарь значков — один раз на странице, между кнопками классов и полосой
   вкладок, то есть до первой решётки и после выбора класса. */
#s-kond .kond-slovar{{margin:.1rem 0 .7rem;font-family:var(--sans);font-size:.85rem;
  color:var(--muted)}}
#s-kond .kond-slovar .pm{{font-style:normal;font-size:1rem;line-height:1}}
#s-kond .kond-slovar .iz{{color:var(--faint);font-size:.85rem}}
#s-kond .kond-lich i .pm{{font-style:normal;vertical-align:super;font-size:.75rem;
  line-height:1}}
#s-kond .kond-imya{{font-family:var(--sans);font-size:1.5rem;font-weight:600;margin:0 0 1rem}}
#s-kond .kond-lich td{{vertical-align:baseline}}
#s-kond .kond-lich .kto{{font-family:var(--sans);font-weight:600;white-space:nowrap;
  padding-right:1.2rem}}
#s-kond .kond-lich .skolko{{color:var(--muted);white-space:nowrap;padding-right:1.2rem;
  font-family:var(--sans);font-size:.9rem}}

/* ═══ 🔴 ТЕЛЕФОН. ТОЛЬКО ВНУТРИ ЭТОГО ЗАПРОСА — ДЕСКТОПНЫЙ ВИД КОНДУИТА,
   ПРИНЯТЫЙ ВЛАДЕЛЬЦЕМ, НЕ МЕНЯЕТСЯ НИ ОДНИМ ПРАВИЛОМ.

   Кондуит — это то место, где на занятии ставят плюсики, и до сегодняшнего дня
   на телефоне он был непригоден: столбец с фамилией занимал 250 из 375 точек,
   и в кадр помещались ДВА столбца задач из тринадцати. Мерено на живой странице
   при 375px, а не на глаз.

   Три вещи, и все три — про палец, а не про красоту:
   1. Фамилия ужимается и обрезается многоточием. Не снимается: по ней узнают
      строку. Столбец остаётся липким слева — прокручивая решётку вбок, видно,
      чью строку отмечаешь.
   2. Клетка получает 44 точки высоты — меньший размер взрослый стоя не попадает.
      Ширина при этом ужимается, чтобы столбцов в кадре стало больше.
   3. Кегли уменьшены: они заданы под ноутбук и на телефоне просто крупные.

   ⚠ Обёртки с `overflow` здесь по-прежнему НЕТ — по той же причине, что описана
   выше: она стала бы ближайшим прокручиваемым предком и оторвала бы липкую шапку
   от окна. Решётка прокручивается страницей, а `position:sticky` на первом
   столбце работает и так. ═══ */
@media(max-width:760px){{
  #s-kond .kond-imya{{font-size:1.2rem;margin:0 0 .6rem}}
  #s-kond .kond{{font-size:.9rem;max-width:none}}
  #s-kond .kond thead th{{font-size:.78rem;padding:.4rem .2rem}}
  /* 🔴 НА ТЕЛЕФОНЕ ВИДНА ФАМИЛИЯ ЦЕЛИКОМ, А НЕ ПОЛОВИНА ФАМИЛИИ И ПОЛОВИНА
     ИМЕНИ. Первая редакция просто обрезала ячейку многоточием — и резала по
     фамилии: «Афанасьев…», «Белеванце…». Фамилия и есть то, по чему узнают
     строку, поэтому на узком экране прячется ИМЯ. Разметка при этом не
     трогается: фамилия уже лежит в `<b>`, а имя — голым текстом рядом, так что
     нулевой кегль на ячейке гасит имя, а `<b>` возвращает себе свой. */
  #s-kond .kond td.kto{{width:7.2rem;max-width:7.2rem;overflow:hidden;
    padding:.2rem .4rem .2rem 0;font-size:0}}
  #s-kond .kond td.kto b,#s-kond .kond td.kto label{{font-size:.8rem;
    display:block;overflow:hidden;text-overflow:ellipsis}}
  #s-kond .kond tbody tr.moi td.kto{{padding-left:.55rem}}
  #s-kond .kond td.kto label{{display:block;overflow:hidden;text-overflow:ellipsis}}
  /* Клетка — цель пальца: 44 точки в высоту, компактнее в ширину. */
  #s-kond .kond tbody td+td{{min-width:2.5em;height:44px;padding:.2rem;
    font-size:1.05rem}}
  #s-kond .kond .iz{{font-size:.62rem}}
  /* Заголовок раздела и галочка «только мои» переносятся, а не сжимают друг друга. */
  #s-kond .kond-verh{{gap:.6rem}}
  #s-kond .kond-moi{{font-size:.9rem;padding:.3em .7rem}}
}}

/* На 320 точках столбец фамилии съедал бы больше трети экрана. */
@media(max-width:380px){{
  #s-kond .kond td.kto{{width:6.2rem;max-width:6.2rem}}
  #s-kond .kond td.kto b,#s-kond .kond td.kto label{{font-size:.76rem}}
  #s-kond .kond tbody td+td{{min-width:2.2em}}
}}
#s-kond .kond-lich i{{display:inline-block;font-style:normal;font-family:var(--sans);
  font-size:.85rem;background:var(--chip);border-radius:6px;padding:.05em .45em;
  margin:0 .25em .25em 0}}
#s-kond .kond-lich i.vsyo{{color:var(--accent)}}
#s-kond .kond-lich i.snyato{{color:var(--warm)}}

/* ═══ ИСТОРИЯ КЛЕТКИ. Открывается жестом — правый клик на ноутбуке, долгое зажатие
   на телефоне; видимой метки на клетке НЕТ (решение владельца 09.09). Ни одного
   нового цвета: всё из переменных, которые эта страница уже объявила. ═══ */
#s-kond .kl-ist{{position:fixed;z-index:20;max-width:min(26rem,calc(100vw - 1rem));
  max-height:calc(100vh - 6rem);overflow:auto;
  background:var(--panel);border:1px solid var(--rule);border-radius:10px;
  box-shadow:0 .5rem 1.6rem rgba(0,0,0,.18);padding:.7rem .85rem .8rem;
  font-family:var(--sans);font-size:.9rem}}
#s-kond .kl-ist-verh{{display:flex;align-items:baseline;gap:.5rem;
  border-bottom:1px solid var(--rule);padding-bottom:.45rem;margin-bottom:.5rem}}
#s-kond .kl-ist-verh b{{white-space:nowrap}}
#s-kond .kl-ist-chto{{color:var(--muted);font-size:.82rem;flex:1}}
#s-kond .kl-ist-x{{background:none;border:0;cursor:pointer;color:var(--muted);
  font-size:1rem;line-height:1;padding:.1rem .2rem}}
#s-kond .kl-ist-x:hover{{color:var(--text)}}
#s-kond .kl-ist-telo{{max-height:min(24rem,60vh);overflow-y:auto}}
#s-kond .kl-ist-net{{color:var(--muted);margin:.2rem 0}}
#s-kond .kl-ist-ryad{{display:flex;flex-wrap:wrap;align-items:baseline;gap:.4rem .6rem;
  padding:.4rem 0;border-bottom:1px solid var(--rule)}}
#s-kond .kl-ist-ryad:last-child{{border-bottom:0}}
#s-kond .kl-ist-chto2{{font-weight:600;min-width:5.5em}}
#s-kond .kl-ist-kto2{{color:var(--accent)}}
#s-kond .kl-ist-kogda{{color:var(--muted);font-size:.82rem;white-space:nowrap}}
/* Техническое нажатие видно и НЕ спрятано: событие из журнала не удаляется никогда,
   поэтому оно стоит в ленте, приглушённое, с прямым словом о том, что это. */
#s-kond .kl-ist-ryad.teh{{opacity:.6}}
#s-kond .kl-ist-teh{{font-size:.72rem;color:var(--warm);border:1px solid var(--warm);
  border-radius:5px;padding:0 .35em}}
#s-kond .kl-ist-zan{{flex-basis:100%;color:var(--muted);font-size:.82rem;
  display:flex;align-items:center;gap:.4rem}}
#s-kond .kl-ist-zan select{{font-family:var(--sans);font-size:.82rem;
  border:1px solid var(--rule);border-radius:6px;padding:.1rem .3rem;
  background:var(--bg);color:var(--text)}}
#s-kond .kl-ist-ruka{{color:var(--accent)}}
/* На телефоне панель — шторка снизу: она шире экрана в любой другой раскладке, и
   попасть пальцем в узкое окно рядом с клеткой невозможно. Позиция, которую поставил
   скрипт, здесь перебивается — `!important` ровно потому, что она инлайновая. */
@media(max-width:760px){{
  #s-kond .kl-ist{{left:0!important;right:0;top:auto!important;bottom:0;
    max-width:none;border-radius:12px 12px 0 0;padding-bottom:1.2rem}}
  #s-kond .kl-ist-telo{{max-height:55vh}}
}}"""


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

    # 🔴 ПРАВКА ВЛАДЕЛЬЦА 09.09: ОТКРЫВАЕТСЯ САМЫЙ НОВЫЙ ЛИСТОК, А НЕ «ВЕСЬ ГОД».
    # Который именно — спрашивается у базы (`_samyj_novyj`), а не вписано сюда числом:
    # выдадут следующий листок — он и откроется, и чинить для этого нечего.  Класс по
    # умолчанию девятый, поэтому и листок ищется среди девятого; если у девятого нет ни
    # одного листка с задачами, отметка остаётся на «Весь год», как было раньше.
    otkryt = _samyj_novyj(kt, listki_9)
    radio = ('<input class="rd" type="radio" name="kl" id="kl-9" checked>'
             '<input class="rd" type="radio" name="kl" id="kl-8">'
             f'<input class="rd" type="radio" name="knd" id="k-vse9"'
             f'{"" if otkryt else " checked"}>'
             '<input class="rd" type="radio" name="knd" id="k-vse8">'
             + "".join(f'<input class="rd" type="radio" name="knd" id="k-{sh.id}"'
                       f'{" checked" if sh.id == otkryt else ""}>'
                       for sh in listki)
             + "".join(f'<input class="rd" type="radio" name="knd" id="k-u{u.id}">'
                       for u in na_uchyote))
    klassy = ('<div class="kond-klassy">'
              '<label for="kl-8">8 класс</label>'
              '<label for="kl-9">9 класс</label></div>')

    # 🔴 СЛОВАРЬ ЗНАЧКОВ ПОДПИСАН ОДИН РАЗ НА СТРАНИЦЕ, А НЕ В КАЖДОЙ КЛЕТКЕ.  Ровно то,
    # что просил владелец: значки обязаны быть различимы, когда их четыре десятка в
    # строке, а объяснение — стоять один раз и не мешать.  Подпись в каждой ячейке
    # (`title="обязательная"`) не годится дважды: на телефоне её нечем вызвать, и она
    # выросла бы в тридцать одну тысячу повторов одного и того же слова.
    slovar = ('<p class="kond-slovar">'
              + "".join(f'{znachok(vid)}\u2009{vid}' + ("  " if vid != "звезда" else "")
                        for vid in ("обязательная", "письменная", "звезда"))
              + '<span class="iz"> · без значка — обычная, сдавать не обязательно</span>'
              + '</p>')
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
              + "".join(_listok(sh, zadachi[sh.id], na_uchyote, sostoyaniya, chuzhoj, daty)
                        for sh in listki)
              + "".join(_uchenik(u, listki, zadachi, sostoyaniya, daty)
                        for u in na_uchyote))

    # День занятия, к которому пойдёт отметка, поставленная ПРЯМО СЕЙЧАС. Считается на
    # сервере тем же правилом, что и все остальные даты, и уезжает в скрипт одним
    # значением: клетка, перерисованная после тапа, обязана показать ту же дату, какую
    # покажет следующая пересборка страницы. Страница, открытая до начала занятия и не
    # обновлённая после, будет знать прежний день — она и данные показывает прежние.
    sejchas = zanyatie_dlya(datetime.now(timezone.utc))
    istoria = ISTORIA_SKRIPT.replace("%(segodnya)s",
                                     sejchas.isoformat() if sejchas else "")

    return (f'<section class="str holst" id="s-kond" data-org="videt-konduit">'
            f'{galka}{radio}'
            f'<div class="kond-verh"><div>'
            f'<h1>Кондуит</h1>'
            f'</div>{metka_galki}</div>'
            f'{klassy}{slovar}{vkladki}{panely}{istoria}</section>')
