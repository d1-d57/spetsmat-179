"""The four величины on the page itself: the markup, and not only the arithmetic.

WHAT THIS FILE CATCHES THAT `test_statistiki.py` CANNOT.  The projections there are pure
and are already right; every way this feature breaks after that is in the wiring:

  * the counter computed over SOMEBODY ELSE'S cut -- a whole-year number printed on the
    row of a листок table, which looks entirely plausible;
  * the row glows, but the mark «свой ребёнок» has DISAPPEARED, because the two row
    classes displaced each other instead of adding up;
  * «сколько сдало» landed in the header of the wrong column -- and there are twenty-one
    columns under one header, so an off-by-one reads as a coincidence;
  * the initials of the принимающий arrived as a column, which the owner explicitly did
    not want.

Each is judged on the RENDER of the section, built by the same call the site builds it
with -- `konduit.razdel(kt)` -- over a small world from `seed_world`.
"""

from __future__ import annotations

import re

import pytest

from core.models import CellState
from tests.conftest import seed_world
from veb.obshchee.karkas import Kontekst
from veb.razdely import konduit


#: One листок: two обязательные, one письменная (obligatory as well), a звезда, an обычная.
LISTOK = ("обязательная", "обязательная", "письменная", "звезда", "обычная")


#: Columns the LIVE база carries and `migrations/` does not create: `teachers.gruppa`,
#: `teachers.kabinet`, `teachers.aktiven`, `students.gruppa`.  Found by this заход through
#: a direct comparison: the live база has them (and `veb/razdely/lichnaya.kabinet_na_datu`,
#: written by a neighbouring заход, already leans on them), while a database built from all
#: ten migrations has not one of them.  They are added here so the test judges THE schema
#: the site actually runs on; the fix belongs in `migrations/`, which is not this заход's
#: zone, and the question is named in `## ВОПРОСЫ`.
ZHIVYE_KOLONKI = (
    "alter table teachers add column kabinet text",
    "alter table teachers add column aktiven integer not null default 1",
    "alter table teachers add column gruppa text",
    "alter table students add column gruppa text",
)


@pytest.fixture
def mir(connection):
    """Five pupils, one листок, not a single mark: the marks are written by the test."""
    for zapros in ZHIVYE_KOLONKI:
        connection.execute(zapros)
    return seed_world(connection, students=5, sheets=(LISTOK,))


@pytest.fixture
def uchebnyj_den(monkeypatch):
    """Пятница — не учебный день, и без этой оснастки «мой школьник» не существует.

    🔴 ЭТО НЕ УДОБСТВО, А КРАСНОЕ, КОТОРОЕ УЖЕ СТОЯЛО.  `_moi_deti` спрашивает
    `deti_na_datu(..., segodnya())`, а та на дне без слота отвечает пустым списком
    («не учебный день: постоянных строк не применяется ни одной»,
    `veb/razdely/lichnaya.py:168`).  Значит любой тест про «моих» ЗЕЛЁН по понедельникам
    и четвергам и КРАСЕН в остальные пять дней недели, ничего не сообщая о коде: замер
    11.09 (пятница) — `test_being_mine_and_having_closed…` красный на `"moi"`, при
    целом механизме.  День занятия здесь называется явно, и результат перестаёт зависеть
    от того, когда запустили прогон.
    """
    monkeypatch.setattr(konduit, "segodnya", lambda: "2026-09-14")   # понедельник
    return "2026-09-14"


def kontekst(connection, prepod_id=None) -> Kontekst:
    """A `Kontekst` carrying exactly the fields the кондуит reads.

    Built by hand rather than through `sobrat_kontekst`: that one opens the LIVE database
    of the project by absolute path, and a test that called it would be judging today's
    school data instead of its own world.
    """
    return Kontekst(rezhim="admin", rol="organizator", mogu=frozenset(), c=connection,
                    DNI={}, kabinety_dnya={}, otkuda_kabinet={}, kabinety={}, gruppy={},
                    prep={}, prepod_id=prepod_id)


def otmetit(marking, student_id, problem_id, sostoyanie=CellState.SOLVED):
    marking.set_state(student_id, problem_id, sostoyanie, source="кнопка")


def panel(html: str, imya: str) -> str:
    """One tab of the page: the panels all sit in the DOM at once, hidden by CSS."""
    kusok = re.search(r'<section class="vid" id="n-%s">(.*?)</section>' % re.escape(imya),
                      html, re.S)
    assert kusok, "нет панели n-%s" % imya
    return kusok.group(1)


def schyotchiki(kusok: str) -> list:
    """Клетка обязательных каждой строки: `(сдано, всего)`, `None` — точка, `"\u2713"` — галочка.

    🔴 ТРЕТИЙ ИСХОД ПОЯВИЛСЯ 11.09 И ЭТО НЕ ПОСЛАБЛЕНИЕ ПРОВЕРКИ.  Владелец: «когда у
    тебя обязательные задачи все сданы, вместо того чтобы ставить счётчик вида N из N,
    ставить большую красивую галочку».  Клетка по-прежнему говорит РОВНО ОДНО — и
    функция по-прежнему возвращает ровно одно значение на строку; изменилось то, что
    одним из значений стала галочка.  Читается КЛЕТКА целиком, а не вложенный `<i>`:
    счётчик и галочка обязаны быть взаимоисключающими, и клетка, где они окажутся
    рядом, должна отсюда выйти красной, а не тихо показать первый попавшийся.
    """
    out = []
    for m in re.finditer(r'<td class="sch"[^>]*>(.*?)</td>', kusok, re.S):
        nutro = m.group(1)
        znaki = re.findall(r'<i class="ob-sch([^"]*)">(.*?)</i>', nutro, re.S)
        assert len(znaki) == 1, "в клетке обязательных не один знак: %r" % nutro
        klass, soderzhimoe = znaki[0]
        if "net" in klass:
            out.append(None)
            continue
        if "gt-da" in klass:
            assert soderzhimoe.startswith("\u2713"), soderzhimoe
            out.append("\u2713")
            continue
        chisla = re.match(r'(\d+)<span class="iz">/(\d+)</span>$', soderzhimoe)
        assert chisla, "счётчик написан не двумя числами: %r" % soderzhimoe
        out.append((int(chisla.group(1)), int(chisla.group(2))))
    return out


# --------------------------------------------- величина 1: обязательные у школьника


def test_the_counter_stands_left_of_every_pupil_on_every_panel(mir, connection, marking):
    """Five pupils, five counters on every panel, and not one more.

    There are three panels: the year overview of the ninth class, the year overview of the
    eighth, and the листок itself.  A counter forgotten on one of them leaves precisely the
    hole this величина was introduced to close.
    """
    otmetit(marking, mir.student_ids[0], mir.problems_by_sheet[mir.sheet_ids[0]][0])
    connection.commit()
    html = konduit.razdel(kontekst(connection))
    for imya in ("vse8", str(mir.sheet_ids[0])):
        assert len(schyotchiki(panel(html, imya))) == 5, "панель %s" % imya


def test_the_counter_counts_obligatory_only_and_counts_pismennaya_among_them(
    mir, connection, marking
):
    zadachi = mir.problems_by_sheet[mir.sheet_ids[0]]
    uchenik = mir.student_ids[0]
    otmetit(marking, uchenik, zadachi[0])          # обязательная
    otmetit(marking, uchenik, zadachi[2])          # письменная -- obligatory too
    otmetit(marking, uchenik, zadachi[3])          # звезда -- never counts at all
    connection.commit()
    schyot = schyotchiki(panel(konduit.razdel(kontekst(connection)),
                               str(mir.sheet_ids[0])))[0]
    assert schyot == (2, 3), "три обязательных на листке, сдано две из них"


def test_a_retracted_obligatory_is_not_counted_as_handed_in(mir, connection, marking):
    """Handed in and not defended is not «сдал» -- on the screen as well as in the journal."""
    zadachi = mir.problems_by_sheet[mir.sheet_ids[0]]
    uchenik = mir.student_ids[0]
    otmetit(marking, uchenik, zadachi[0])
    otmetit(marking, uchenik, zadachi[0], CellState.RETRACTED)
    connection.commit()
    assert schyotchiki(panel(konduit.razdel(kontekst(connection)),
                            str(mir.sheet_ids[0])))[0] == (0, 3)


# ------------------------------------- величина 2: столбец крупной зелёной галочки


def galki(kusok: str) -> list:
    """Клетка обязательных, сверху вниз: `True` там, где вместо числа стоит галочка.

    🔴 ЧИТАЕТСЯ ПО КЛАССУ ЗНАКА В КЛЕТКЕ `sch`, А НЕ ПО СИМВОЛУ.  До 11.09 галочка
    стояла в собственном столбце `td.gt`, и эта функция читала его; правка владельца
    («ставить галочку там, где написано слово „обязательное“») столбец упразднила,
    и признак переехал в клетку счётчика.  Символ ✓ в решётке значит совсем другое —
    «задача сдана», — поэтому судится класс `ob-sch gt-da`, а не знак.
    """
    return ["\u2713" == z for z in schyotchiki(kusok)]


def test_no_row_glows_for_having_closed_the_obligatory_problems(
    mir, connection, marking
):
    """The owner's edit of 10.09 (O1), read as the property it is: the row does not glow.

    This test USED to assert the opposite — «светится ровно строка того, кто закрыл
    обязательные» — and it was right until 10.09, when the owner looked at the live page
    and said: «я хочу видеть своих школьников, и я их вижу. А теперь ещё вижу почему-то
    школьников, которые просто всё сдали — это не нужно… Ты сейчас выделяешь всю строчку —
    не надо».  The pupil below closes every obligatory problem of the листок, which is
    exactly the state that used to light his row up.
    """
    zadachi = mir.problems_by_sheet[mir.sheet_ids[0]]
    for zadacha in (zadachi[0], zadachi[1], zadachi[2]):
        otmetit(marking, mir.student_ids[0], zadacha)
    # The second pupil took a ЗВЕЗДА and an обычная -- not one obligatory problem.
    otmetit(marking, mir.student_ids[1], zadachi[3])
    otmetit(marking, mir.student_ids[1], zadachi[4])
    connection.commit()
    kusok = panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0]))
    stroki = re.findall(r'<tr( class="[^"]*")?><td class="kto">', kusok)
    assert stroki, "строки школьников вообще нарисованы"
    assert not [k for k in stroki if k], "ни одна строка не несёт класса вовсе"
    assert "gotov" not in kusok, "класс подсветки не остался нигде в разметке"


def test_the_green_tick_lights_in_the_counters_own_cell_for_who_closed_everything(
    mir, connection, marking
):
    """O2 (10.09) as the owner RE-DECIDED it on 11.09: the tick stands where the counter would.

    Дословно: «я галочки предлагал ставить в другом месте — там, где написано слово
    „обязательное“.  Когда у тебя обязательные задачи все сданы, вместо того чтобы
    ставить счётчик вида N из N, ставить большую красивую галочку».  До 11.09 галочка
    жила в собственном столбце `td.gt` рядом со счётчиком, и у закрывшего горели ОБА —
    `3/3` и галочка вплотную.  Этот тест требовал именно того столбца; теперь он
    требует, чтобы столбца НЕ БЫЛО, а знак стоял в клетке счётчика.

    The same world as the test above: the first pupil closes all three obligatory
    problems, the second takes a звезда and an обычная and closes none.  The признак the
    row lost is checked HERE, in the cell that now carries it — that is the whole of
    O1+O2 together, and checking only the loss would leave the fact silently dropped.
    """
    zadachi = mir.problems_by_sheet[mir.sheet_ids[0]]
    for zadacha in (zadachi[0], zadachi[1], zadachi[2]):
        otmetit(marking, mir.student_ids[0], zadacha)
    otmetit(marking, mir.student_ids[1], zadachi[3])
    otmetit(marking, mir.student_ids[1], zadachi[4])
    connection.commit()
    html = konduit.razdel(kontekst(connection))
    kusok = panel(html, str(mir.sheet_ids[0]))
    assert galki(kusok) == [True, False, False, False, False]
    # Того, кто закрыл всё, счётчик больше не называет числами — на их месте знак.
    assert schyotchiki(kusok) == ["\u2713", (0, 3), (0, 3), (0, 3), (0, 3)]
    # И столбца под галочку в шапке НЕТ: колонка обязательных ровно одна.
    shapka_html = re.search(r"<thead>(.*?)</thead>", kusok, re.S).group(1)
    assert '<th class="gt"' not in shapka_html, shapka_html
    assert shapka_html.count('<th class="sch"') == 1, shapka_html
    # And the tick is drawn green by the class, not by a colour written in the cell.
    assert re.search(r"\.ob-sch\.gt-da\{[^}]*var\(--zel\)",
                     konduit.stili(kontekst(connection)))


def test_the_tick_is_not_smeared_over_the_surname_cell_or_the_counter(
    mir, connection, marking
):
    """Q4, «нельзя смешивать», judged where it actually breaks: one признак, one place.

    The pupil below is in the state that carries the признак, so a second carrier would
    be visible right now rather than in theory.
    """
    for zadacha in mir.problems_by_sheet[mir.sheet_ids[0]][:3]:
        otmetit(marking, mir.student_ids[0], zadacha)
    connection.commit()
    kusok = panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0]))
    telo = re.search(r"<tbody>(.*?)</tbody>", kusok, re.S).group(1)
    stroka = re.search(r"<tr[^>]*>(.*?)</tr>", telo, re.S).group(1)
    assert '<i class="ob-sch gt-da">' in stroka, "галочка у этого школьника вообще есть"
    kto = re.search(r'<td class="kto">(.*?)</td>', stroka, re.S).group(1)
    sch = re.search(r'<td class="sch"[^>]*>(.*?)</td>', stroka, re.S).group(1)
    pr = re.search(r'<td class="pr"[^>]*>(.*?)</td>', stroka, re.S).group(1)
    assert "✓" not in kto and "✓" not in pr, (kto, pr)
    # 🔴 И В САМОЙ КЛЕТКЕ ОБЯЗАТЕЛЬНЫХ ЗНАК НЕ СТОИТ РЯДОМ С ЧИСЛОМ, А ВМЕСТО НЕГО.
    # Правка 11.09 — это ЗАМЕНА, а не добавление: «вместо того чтобы ставить счётчик
    # вида N из N».  Галочка, приписанная к `3/3`, выглядела бы исполнением просьбы и
    # была бы прежним столбцом `gt`, сдвинутым на два пикселя влево.
    assert not re.search(r"\d", sch), sch


def test_a_listok_with_no_obligatory_problems_lights_up_nobody(connection, marking):
    """`1д`-`4д` on the live база are exactly like this: 99 problems and no obligatory one."""
    for zapros in ZHIVYE_KOLONKI:
        connection.execute(zapros)
    mir = seed_world(connection, students=3, sheets=(("звезда", "обычная"),))
    connection.commit()
    kusok = panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0]))
    assert galki(kusok) == [False, False, False], (
        "галочка «сдал всё обязательное» на листке без обязательных не горит ни у кого: "
        "вакуумная истина зажгла бы её всем сразу, и признак перестал бы что-либо значить")
    assert schyotchiki(kusok) == [None, None, None], "листок без обязательных пишет точку"


def test_the_row_carries_the_one_priznak_of_whose_child_it_is_and_no_other(
    mir, connection, marking, uchebnyj_den
):
    """One признак, one носитель (O1, and the owner's канон «нельзя смешивать», Q4).

    The pupil below is BOTH the teacher's own child AND has closed every obligatory
    problem — the case where the two marks used to be added onto one row (this test
    asserted that sum until 10.09).  Now the row says «мой» and says nothing else; the
    second fact is drawn in its own column and is checked there.
    """
    zadachi = mir.problems_by_sheet[mir.sheet_ids[0]]
    for zadacha in zadachi[:3]:
        otmetit(marking, mir.student_ids[0], zadacha)
    prepod = mir.teacher_ids[0]
    # 🔴 СТРОКА НА ОБА СЛОТА, И ЭТО НЕ ИЗБЫТОЧНОСТЬ. С 10.09 «мой» считается ПО ДНЮ:
    # кондуит спрашивает ту же службу, что распределение (требование владельца —
    # «изменение в текущем расписании на сегодня не обновляет кабинет и вкладку в
    # кондуите»).
    for slot in (1, 2):
        connection.execute(
            "insert into enrollment (student_id, teacher_id, room, slot, valid_from) "
            "values (?, ?, ?, ?, ?)",
            (mir.student_ids[0], prepod, "303", slot, "2020-01-01"))
    connection.commit()
    kusok = panel(konduit.razdel(kontekst(connection, prepod_id=prepod)),
                  str(mir.sheet_ids[0]))
    pervaya = re.search(r'<tr class="([^"]*)"><td class="kto">', kusok).group(1)
    assert pervaya.split() == ["moi"], pervaya


def test_on_the_year_tab_the_tick_also_lights_for_one_listok_closed_entirely(
    connection, marking
):
    """O5: «есть ли у школьника долги» — листки даны НА ВЫБОР.

    Owner 10.09: «школьник закрыл один и не закрывал второй — это норма, а не долг.  По
    кондуиту такого не различить.  На вкладке „Весь год“ ставить галочку, когда школьник
    закрыл все обязательные ИЛИ один из листков целиком».

    Two листка of five problems each, three of them obligatory.  The pupil closes the
    FIRST листок whole — every problem of it, obligatory and not — and touches nothing on
    the second.  He therefore has 3 of 6 obligatory over the cut, so the счётчик alone
    would call him a debtor, which is exactly the hole the owner named.
    """
    for zapros in ZHIVYE_KOLONKI:
        connection.execute(zapros)
    mir = seed_world(connection, students=3, sheets=(LISTOK, LISTOK))
    pervyj = mir.sheet_ids[0]
    for zadacha in mir.problems_by_sheet[pervyj]:
        otmetit(marking, mir.student_ids[0], zadacha)
    # The second pupil closes the obligatory HALF of the first листок and no more: not a
    # whole листок, not the whole cut — no tick.
    for zadacha in mir.problems_by_sheet[pervyj][:3]:
        otmetit(marking, mir.student_ids[1], zadacha)
    connection.commit()
    god = panel(konduit.razdel(kontekst(connection)), "vse8")
    assert galki(god) == [True, False, False]
    # 🔴 ЧИСЛА НЕ ПРОПАЛИ ВМЕСТЕ СО СЧЁТЧИКОМ, А ПЕРЕЕХАЛИ В ПОДСКАЗКУ КЛЕТКИ.
    # С 11.09 галочка занимает место счётчика, и именно на этом школьнике видно, чего
    # замена могла стоить: по обязательным разреза у него 3 из 6, и долга при этом нет.
    # Исчезни это число совсем — правка «поставить галочку вместо счётчика» отняла бы
    # факт, о потере которого никто не просил.
    assert schyotchiki(god)[0] == "\u2713", "вместо числа у него стоит галочка"
    podskazka = re.search(r'<td class="sch" title="([^"]*)"', god).group(1)
    assert "обязательных сдано 3 из 6" in podskazka, podskazka
    assert schyotchiki(god)[1] == (3, 6), "у соседа без галочки числа стоят как стояли"


def test_on_a_listok_tab_closing_that_listok_whole_is_not_a_second_criterion(
    connection, marking
):
    """The disjunction of O5 belongs to the year cut and stays there.

    On one листок «закрыл этот листок целиком» and «закрыл всё обязательное этого листка»
    are two answers about the SAME листок, and taking the weaker one would quietly change
    what the tick means on that tab.  Here the pupil takes the two `обязательная` problems
    and NOT the `письменная` — obligatory too — so he has closed neither.
    """
    for zapros in ZHIVYE_KOLONKI:
        connection.execute(zapros)
    mir = seed_world(connection, students=2, sheets=(LISTOK,))
    zadachi = mir.problems_by_sheet[mir.sheet_ids[0]]
    for zadacha in (zadachi[0], zadachi[1], zadachi[3], zadachi[4]):
        otmetit(marking, mir.student_ids[0], zadacha)
    connection.commit()
    kusok = panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0]))
    assert galki(kusok) == [False, False]
    assert schyotchiki(kusok)[0] == (2, 3), "письменная не сдана, и она обязательная"


def test_the_year_tick_says_in_words_which_of_the_two_facts_lit_it(
    connection, marking
):
    """The tooltip is the only place where the meaning of the column is written out.

    Two different facts light the same tick on the year tab, and «закрыл все обязательные»
    printed over a pupil who closed one листок instead would be the screen making a claim
    the база does not support.
    """
    for zapros in ZHIVYE_KOLONKI:
        connection.execute(zapros)
    mir = seed_world(connection, students=2, sheets=(LISTOK, LISTOK))
    for zadacha in mir.problems_by_sheet[mir.sheet_ids[0]]:
        otmetit(marking, mir.student_ids[0], zadacha)
    connection.commit()
    god = panel(konduit.razdel(kontekst(connection)), "vse8")
    podskazka = re.search(r'<td class="sch" title="([^"]*)"[^>]*>'
                          r'<i class="ob-sch gt-da"', god).group(1)
    assert "листок" in podskazka and "целиком" in podskazka, podskazka


def podpisi_galok(kusok: str) -> list:
    """Подпись рядом с каждой горящей галочкой, сверху вниз (пустая строка — нет подписи)."""
    out = []
    for kletka in re.findall(r'<td class="sch"[^>]*>(.*?)</td>', kusok, re.S):
        znak = re.search(r'<i class="ob-sch gt-da">\u2713(.*?)</i>', kletka, re.S)
        if not znak:
            continue
        podpis = re.match(r'^<span class="iz">(.*)</span>$', znak.group(1))
        out.append(podpis.group(1) if podpis else znak.group(1))
    return out


def test_the_year_tick_names_the_листок_that_closed_it(connection, marking):
    """🔴 ТРЕБОВАНИЕ ВЛАДЕЛЬЦА 11.09, ДОСЛОВНО: «Что значит галочка в разделе Весь год?
    Я не понимаю.  Это значит, что один из листков закрыт?  Тогда должна быть не просто
    галочка, а дописано, ЧТО ЭТО 16-й листок — что у него нет долгов по 16-му листку,
    потому что он сдал 16A».

    Мир построен так, что ОБЕ причины годовой галочки горят в одном столбце, на соседних
    строках, — иначе проверять нечего:
      * первый школьник закрыл ПЕРВЫЙ листок целиком и не тронул второй.  Обязательных у
        него 3 из 6, то есть галочку зажёг именно листок, и его номер обязан стоять рядом;
      * второй сдал обязательные ОБОИХ листков и ничего сверх них.  Ни одного листка
        целиком у него нет — называть нечего, и подпись говорит «всё».
    Третий не закрыл ничего: у него стоит счётчик, и подписи нет вовсе.
    """
    for zapros in ZHIVYE_KOLONKI:
        connection.execute(zapros)
    # 🔴 НОМЕРА ЛИСТКОВ НЕ ПЕРЕПИСЫВАЮТСЯ ПОД КРАСИВЫЙ ПРИМЕР ВЛАДЕЛЬЦА («16A»).
    # Номер, начинающийся с «16», кондуит относит к ДЕВЯТОМУ классу (`veb.razdely.listki.L9`),
    # и переименованный листок уехал бы с той вкладки, которую читает этот тест.  Номер
    # берётся из шапки самой панели — так же, как его увидит владелец.
    mir = seed_world(connection, students=3, sheets=(LISTOK, LISTOK))
    pervyj, vtoroj = mir.sheet_ids
    for zadacha in mir.problems_by_sheet[pervyj]:
        otmetit(marking, mir.student_ids[0], zadacha)
    for listok in (pervyj, vtoroj):
        for zadacha in mir.problems_by_sheet[listok][:3]:
            otmetit(marking, mir.student_ids[1], zadacha)
    connection.commit()
    god = panel(konduit.razdel(kontekst(connection)), "vse8")

    nomera = re.findall(r'<th class="zn"[^>]*>([^<]*)</th>', god)
    assert len(nomera) == 2, nomera

    assert galki(god) == [True, True, False]
    assert podpisi_galok(god) == [nomera[0], "всё"]

    podskazki = re.findall(r'<td class="sch" title="([^"]*)"', god)
    assert nomera[0] in podskazki[0] and "целиком" in podskazki[0], podskazki[0]
    assert "все 6 обязательных" in podskazki[1], podskazki[1]
    # 🔴 И «ВСЁ» НЕ ВЫДАЁТ СЕБЯ ЗА НОМЕР ЛИСТКА: у второго школьника ни один листок
    # целиком не закрыт, и вписанный туда номер был бы утверждением, которого база не
    # поддерживает.  Это и есть та половина критерия готовности, которую заход оспорил
    # в `## ПЛАН` до работы.
    assert not [n for n in nomera if n in podskazki[1]], podskazki[1]


def test_on_a_listok_tab_the_tick_carries_no_подпись(mir, connection, marking):
    """Подпись — ответ на вопрос «почему долгов нет», и он есть только у годового разреза.

    На вкладке ОДНОГО листка галочка значит ровно одно — «закрыл всё обязательное этого
    листка», — и дописывать к ней номер листка, который написан заголовком панели над
    таблицей и вкладкой над ней же, значило бы повторить его третий раз.
    """
    for zadacha in mir.problems_by_sheet[mir.sheet_ids[0]][:3]:
        otmetit(marking, mir.student_ids[0], zadacha)
    connection.commit()
    kusok = panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0]))
    assert galki(kusok)[0] is True
    assert podpisi_galok(kusok) == [""]


# ------------------------------------------------- величина 3: сколько сдало задачу


def shapka(kusok: str) -> list:
    """The columns of a листок, left to right: `(label, сдало, closed by the class)`."""
    return [(m.group("label"), int(m.group("n")), bool(m.group("zakr")))
            for m in re.finditer(
                r'<th class="zn">(?P<label>.*?)(?:<i class="pm[^>]*>.</i>)?'
                r'<b class="sdalo(?P<zakr> zakr)?"[^>]*>(?P<n>\d+)</b></th>', kusok)]


def test_every_column_carries_how_many_took_it_and_the_number_is_per_column(
    mir, connection, marking
):
    """The number stands over ITS OWN column.

    An off-by-one is the most plausible way this величина breaks: one header over
    twenty-one columns, every number present, and not one of them about its own problem.
    So the world is built on purpose so that all five numbers are DIFFERENT.
    """
    zadachi = mir.problems_by_sheet[mir.sheet_ids[0]]
    for nomer, zadacha in enumerate(zadachi):        # 0, 1, 2, 3 and 4 solvers
        for uchenik in mir.student_ids[:nomer]:
            otmetit(marking, uchenik, zadacha)
    connection.commit()
    stolbcy = shapka(panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0])))
    assert [n for _label, n, _z in stolbcy] == [0, 1, 2, 3, 4]
    assert [label for label, _n, _z in stolbcy] == ["1.1", "1.2", "1.3", "1.4", "1.5"]


def test_closed_by_the_class_means_MORE_than_three_took_it(mir, connection, marking):
    """Exactly three is not closed yet; four is closed.  The words of the owner, literally."""
    zadachi = mir.problems_by_sheet[mir.sheet_ids[0]]
    for uchenik in mir.student_ids[:3]:
        otmetit(marking, uchenik, zadachi[0])
    for uchenik in mir.student_ids[:4]:
        otmetit(marking, uchenik, zadachi[1])
    connection.commit()
    stolbcy = shapka(panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0])))
    assert (stolbcy[0][1], stolbcy[0][2]) == (3, False), "трое — ещё не закрыта"
    assert (stolbcy[1][1], stolbcy[1][2]) == (4, True), "четверо — закрыта классом"


def test_a_retracted_hand_in_does_not_count_towards_closing_a_problem(
    mir, connection, marking
):
    """Exactly the case the threshold exists for: handed in and never defended."""
    zadacha = mir.problems_by_sheet[mir.sheet_ids[0]][0]
    for uchenik in mir.student_ids[:5]:
        otmetit(marking, uchenik, zadacha)
    for uchenik in mir.student_ids[:4]:
        otmetit(marking, uchenik, zadacha, CellState.RETRACTED)
    connection.commit()
    stolbcy = shapka(panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0])))
    assert (stolbcy[0][1], stolbcy[0][2]) == (1, False)


# --------------------------------------------- величина 4: инициалы принимающего


#: Клетка принимающего целиком: подсказка висит на `<td>`, инициалы лежат внутри.
#: 🔴 ЧИТАЕТСЯ ИМЕННО КЛЕТКА, А НЕ ВЛОЖЕННЫЙ `<i>`, И ЭТО СУТЬ ДЕФЕКТА 11.09.  Владелец
#: навёл «на клеточку» и не увидел ничего: `title` стоял на инициалах — двух сантиметрах
#: текста внутри клетки `3.4rem`.  Выражение, знающее только `<i ... title=...>`, было бы
#: зелёным ровно в том состоянии, на которое он пожаловался.
PRIN = re.compile(r'<td class="pr" title="принимающий:? ?([^"]*)">'
                  r'<i class="prin( net)?">([^<]*)</i></td>')


def zapisat(connection, student_id, teacher_id, slot, room="303",
            ot="2020-01-01", do="9999-12-31"):
    connection.execute(
        "insert into enrollment (student_id, teacher_id, room, slot, valid_from, valid_to) "
        "values (?, ?, ?, ?, ?, ?)", (student_id, teacher_id, room, slot, ot, do))


def test_the_initials_stand_in_a_column_of_their_own_and_not_in_the_surname_cell(
    mir, connection
):
    """The decision of the owner, 10.09 (O3), which REVERSES his decision of 09.09.

    On 09.09 he said «не колонкой» and the initials were written into the surname cell
    as a superscript; this test asserted THAT.  On 10.09 he looked at «Агаркова Ирина
    ᴰ·ᴱ·» on the live page and said: «ты правильно решил поместить инициалы
    преподавателя в строку, но для этого нужен ОТДЕЛЬНЫЙ СТОЛБЕЦ. Должно быть:
    „Агаркова Ирина“, а дальше идёт столбец» — and answered the objection that made
    the first decision («there is no room») himself: «там, где заканчивается самая
    длинная фамилия, ещё есть место».

    🔴 THE COUNT IS SPELLED OUT AS A SUM, NOT WRITTEN AS A NUMBER.  Every time a column
    appears this assertion goes red, and the honest question at that moment is "which
    column appeared" — a bare `== 9` cannot be asked that.
    """
    zapisat(connection, mir.student_ids[0], mir.teacher_ids[0], 1)
    connection.commit()
    kusok = panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0]))
    # 🔴 СТОЛБЦА ГАЛОЧКИ В ЭТОЙ СУММЕ БОЛЬШЕ НЕТ — ПРАВКА ВЛАДЕЛЬЦА 11.09: галочка
    # переехала в клетку счётчика, и колонок стало на одну МЕНЬШЕ, а не больше.
    FAMILIA, PRINIMAYUSHCHIJ, OBYAZATELNYE = 1, 1, 1
    assert len(re.findall(r"<th[ >]", kusok)) == (
        FAMILIA + PRINIMAYUSHCHIJ + OBYAZATELNYE + len(LISTOK))
    shapka_html = re.search(r"<thead>(.*?)</thead>", kusok, re.S).group(1)
    assert len(re.findall(r'<th class="pr"', shapka_html)) == PRINIMAYUSHCHIJ
    # 🔴 И ЭТО ТА ЖЕ ПРОВЕРКА ФОРМОЙ, ЧТО БЫЛА: клетка фамилии не несёт второго
    # носителя.  Раньше она требовала инициалы ВНУТРИ неё, теперь — снаружи;
    # проверяется одно и то же место, и подменить его словами по-прежнему нельзя.
    yacheyka = re.search(r'<td class="kto">(.*?)</td>', kusok, re.S).group(1)
    assert "prin" not in yacheyka, yacheyka
    assert '<td class="pr" title="принимающий: ' in kusok


def test_the_hover_carries_the_name_the_group_and_the_room(mir, connection):
    connection.execute("update teachers set name = ?, gruppa = ? where id = ?",
                       ("Андрей Рябичев", "Д", mir.teacher_ids[0]))
    zapisat(connection, mir.student_ids[0], mir.teacher_ids[0], 1, room="302")
    connection.commit()
    kusok = panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0]))
    title, net, txt = PRIN.findall(kusok)[0]
    assert txt == "А.Р."
    assert title == "Андрей Рябичев · группа Д · кабинет 302"
    assert not net


def test_the_hover_target_is_the_whole_cell_and_not_the_initials_inside_it(
    mir, connection
):
    """🔴 ЖАЛОБА ВЛАДЕЛЬЦА 11.09 ДОСЛОВНО: «тут написано ДМ… я навожу на клеточку —
    не всплывает Даня Макаров».

    Текст подсказки был верен и до правки — на живой базе все 1242 клетки несли
    «принимающий: Даня Макаров · группа Д · кабинет 302».  Неверна была МИШЕНЬ: `title`
    стоял на `<i class="prin">`, то есть на инициалах внутри клетки `3.4rem` с полями, и
    наведение на клетку мимо букв не показывало ничего.  Поэтому проверяется не наличие
    текста, а то, НА ЧЁМ он висит: подсказка обязана быть на `<td>`, и внутри неё не
    должно остаться второй такой же на `<i>` — иначе мишень снова сожмётся до текста, а
    в разметке появится два носителя одного факта.
    """
    connection.execute("update teachers set name = ?, gruppa = ? where id = ?",
                       ("Даня Макаров", "Д", mir.teacher_ids[0]))
    zapisat(connection, mir.student_ids[0], mir.teacher_ids[0], 1, room="302")
    connection.commit()
    html = konduit.razdel(kontekst(connection))
    kletki = re.findall(r'<td class="pr"[^>]*>.*?</td>', html, re.S)
    assert kletki, "клетки принимающего вообще нарисованы"
    bez_podskazki = [k for k in kletki if not k.startswith('<td class="pr" title="')]
    assert bez_podskazki == [], (
        "клетка принимающего без подсказки — ровно тот промах, на который "
        "пожаловался владелец: %r" % bez_podskazki[:2])
    vnutri = [k for k in kletki if re.search(r'<i class="prin[^"]*" title=', k)]
    assert vnutri == [], (
        "подсказка осталась и на инициалах: мишень снова сжата до текста, %r"
        % vnutri[:2])
    nash = [k for k in kletki if "Даня Макаров" in k]
    assert len(nash) >= 1, "имя принимающего не доехало в подсказку клетки"
    assert "Д.М." in nash[0], nash[0]
    # И курсор обещает подсказку по всей площади клетки, а не над буквами.
    assert re.search(r"tbody td\.pr\{[^}]*cursor:help", konduit.stili(kontekst(connection)))


def test_a_pupil_with_no_open_row_gets_a_dash_and_not_a_blank(mir, connection):
    """A blank reads as «forgot to draw it»; a dash says the question was asked and has no answer."""
    connection.commit()
    kusok = panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0]))
    nayden = PRIN.findall(kusok)
    assert len(nayden) == 5
    assert all(net and txt == "—" for _title, net, txt in nayden)


def test_a_row_that_is_already_closed_does_not_name_a_принимающий(mir, connection):
    """The interval is half-open: a row closed yesterday does not answer today.

    `valid_to` is the day FROM WHICH the row no longer holds, and `<=` in place of `<`
    would show yesterday's принимающий for one more day.
    """
    zapisat(connection, mir.student_ids[0], mir.teacher_ids[0], 1,
            ot="2020-01-01", do="2020-06-01")
    connection.commit()
    kusok = panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0]))
    assert PRIN.findall(kusok)[0][2] == "—"


def test_two_different_принимающих_are_both_named_with_their_days(mir, connection):
    """Different people on Monday and on Thursday: the hover must say who is there when."""
    connection.execute("update teachers set name = ?, gruppa = ? where id = ?",
                       ("Андрей Рябичев", "Д", mir.teacher_ids[0]))
    connection.execute("update teachers set name = ?, gruppa = ? where id = ?",
                       ("Ваня Яковлев", "В", mir.teacher_ids[1]))
    zapisat(connection, mir.student_ids[0], mir.teacher_ids[0], 1, room="302")
    zapisat(connection, mir.student_ids[0], mir.teacher_ids[1], 2, room="303")
    connection.commit()
    kusok = panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0]))
    title, _net, txt = PRIN.findall(kusok)[0]
    assert txt == "А.Р./В.Я."
    assert title == ("пн — Андрей Рябичев · группа Д · кабинет 302; "
                     "чт — Ваня Яковлев · группа В · кабинет 303")


def test_one_принимающий_in_both_slots_is_one_person_and_one_pair_of_initials(
    mir, connection
):
    connection.execute("update teachers set name = ?, gruppa = ? where id = ?",
                       ("Андрей Рябичев", "Д", mir.teacher_ids[0]))
    zapisat(connection, mir.student_ids[0], mir.teacher_ids[0], 1, room="302")
    zapisat(connection, mir.student_ids[0], mir.teacher_ids[0], 2, room="302")
    connection.commit()
    kusok = panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0]))
    title, _net, txt = PRIN.findall(kusok)[0]
    assert txt == "А.Р.", "один человек — одни инициалы, а не «А.Р./А.Р.»"
    assert title.startswith("Андрей Рябичев"), "дня недели тут не нужно: он один и тот же"


def test_a_one_word_name_keeps_its_word():
    """«Надя» and «Наталья Амбург» are two live принимающие, and «Н.» would merge them into one."""
    assert konduit.initsialy("Надя") == "Надя"
    assert konduit.initsialy("Наталья Амбург") == "Н.А."


# --------------------------------------------------------- величина 5: гробарий


def grobarij(html: str) -> str:
    return panel(html, "grob")


def proza(kusok: str) -> str:
    """Текст панели БЕЗ разметки и без её собственного заголовка — то, что владелец
    назвал «кучей текста от тебя» (O4).  Именно эта величина обязана быть пустой у
    пустого гробария; таблица с задачами прозой не считается — это данные."""
    tekst = re.sub(r"<[^>]+>", "", kusok).strip()
    return tekst[len("Гробарий"):].strip() if tekst.startswith("Гробарий") else tekst


def pust(kusok: str) -> bool:
    """Пустой гробарий — тот, в котором нет ни одной строки задачи.

    🔴 СУДИТСЯ ФОРМОЙ, А НЕ СЛОВАМИ.  До 10.09 эти проверки искали фразу «Гробарий
    пуст» — то есть держались за ту самую прозу, которую владелец потребовал убрать, и
    покраснели бы на верной правке.  Пустота — это отсутствие таблицы, и такой ответ
    переживает любой текст вокруг.
    """
    return "<table" not in kusok


def devyatyj(connection, listki):
    """A world whose листки the кондуит counts as the NINTH class.

    The кондуит takes the class from `veb.razdely.listki.L9` -- «the number starts with 16»
    -- and there is no other mark of it in the база at all.  So the листки here are named
    `16…`: the test has to ask in exactly the way the page asks, or it would be judging the
    eighth-class tab bar, which carries no гробарий by this заход's own decision.
    """
    for zapros in ZHIVYE_KOLONKI:
        connection.execute(zapros)
    mir = seed_world(connection, students=5, sheets=listki)
    for poryadok, sheet_id in enumerate(mir.sheet_ids):
        connection.execute(
            "update sheets set number = ?, issued_at = ? where id = ?",
            ("16%s" % "ABCD"[poryadok], "2026-09-%02d" % (3 + poryadok * 7), sheet_id))
    return mir


def test_with_one_listok_issued_the_empty_grobarij_is_EMPTY(connection):
    """The state of the live база today, reproduced: exactly one листок has been issued.

    🔴 THIS TEST ASSERTED THE OPPOSITE UNTIL 10.09 and was named «…says it is empty and
    why»: it demanded the rule «сюда попадают задачи листка…» and the sentence «Гробарий
    пуст, и это не ошибка… наполнится сам».  The owner read that text on the live page and
    said: «мне не нравится, что сюда попадает куча текста от тебя, а гробарий пуст.  Это не
    ошибка — это нейрослоп.  Убираем это.  Пустой гробарий пусть будет пустым» (O4).
    Nothing short replaces it, by the same rule that removed the кабинет caption (K1).
    """
    devyatyj(connection, (LISTOK,))
    connection.commit()
    kusok = grobarij(konduit.razdel(kontekst(connection)))
    assert pust(kusok), kusok
    assert proza(kusok) == "", proza(kusok)
    # Заголовок панели остаётся: он называет вкладку, как называет её любая другая
    # панель раздела, и он не «текст от тебя».
    assert '<p class="zag2">Гробарий</p>' in kusok


def test_the_previous_listok_falls_in_by_itself_when_the_next_one_is_issued(
    connection, marking
):
    """🔴 THE CENTRAL CHECK OF THIS ВЕЛИЧИНА.

    The owner: «гробарий наполнится сам в понедельник, когда 16-й листок станет
    историческим».  A tab that is empty because emptiness was written into it looks
    EXACTLY THE SAME today as this one does -- and the difference would show up on Monday,
    in front of a class.  Here the second листок is issued inside the test, and the first
    one has to appear in the гробарий with no edit to the code at all.
    """
    mir = devyatyj(connection, (LISTOK, LISTOK))
    staryj, novyj = mir.sheet_ids
    zadachi = mir.problems_by_sheet[staryj]
    # Four took the first problem: it is past the threshold and stays out.
    for uchenik in mir.student_ids[:4]:
        marking.set_state(uchenik, zadachi[0], CellState.SOLVED, source="кнопка")
    # Two took the second, which is exactly the гробарий case.
    for uchenik in mir.student_ids[:2]:
        marking.set_state(uchenik, zadachi[1], CellState.SOLVED, source="кнопка")
    connection.commit()

    kusok = grobarij(konduit.razdel(kontekst(connection)))
    assert not pust(kusok), kusok
    zadachi_v_grobarii = re.findall(r'<td class="kto">([^<]*)', kusok)
    assert "1.1" not in zadachi_v_grobarii, "четверо сдали — не гробарий"
    assert "1.2" in zadachi_v_grobarii, "двое сдали — гробарий"
    # Problems of the CURRENT листок never fall in, even when nobody took them.
    assert not any(z.startswith("2.") for z in zadachi_v_grobarii), zadachi_v_grobarii


def test_the_graveyard_names_the_first_solvers_in_order(connection, marking):
    mir = devyatyj(connection, (LISTOK, LISTOK))
    zadacha = mir.problems_by_sheet[mir.sheet_ids[0]][1]
    marking.set_state(mir.student_ids[2], zadacha, CellState.SOLVED,
                      source="кнопка", valid_at="2026-09-03T10:10:00Z")
    marking.set_state(mir.student_ids[0], zadacha, CellState.SOLVED,
                      source="кнопка", valid_at="2026-09-07T11:15:00Z")
    connection.commit()
    kusok = grobarij(konduit.razdel(kontekst(connection)))
    imena = re.findall(r'<i>([^<]*)</i>', kusok)
    assert imena == ["surname-2 name-2", "surname-0 name-0"], "раньше сдал — раньше в списке"


def test_a_problem_nobody_took_says_so_instead_of_showing_an_empty_cell(
    connection, marking
):
    mir = devyatyj(connection, (("обязательная",), ("обязательная",)))
    connection.commit()
    kusok = grobarij(konduit.razdel(kontekst(connection)))
    assert ">никто<" in kusok, "«никто не сдал» — самое сильное, что говорит гробарий"


def test_versions_of_one_listok_do_not_make_each_other_historical(connection):
    """`16A`, `16α` and `16ℵ` are one листок in three strengths and one `issued_at`.

    Comparing by `ord` would declare two of them historical on the day they were issued,
    and the гробарий would open on the problems of the CURRENT листок.  This is the live
    база as it stands today, not a hypothetical.
    """
    for zapros in ZHIVYE_KOLONKI:
        connection.execute(zapros)
    mir = seed_world(connection, students=3, sheets=(LISTOK, LISTOK, LISTOK))
    for nomer, sheet_id in zip(("16A", "16α", "16ℵ"), mir.sheet_ids):
        connection.execute("update sheets set number = ?, issued_at = ? where id = ?",
                           (nomer, "2026-09-03", sheet_id))
    connection.commit()
    assert pust(grobarij(konduit.razdel(kontekst(connection))))


def test_a_listok_row_without_problems_does_not_bury_the_current_one(connection):
    """A row for the next листок whose problems are not entered yet is not an issued листок."""
    mir = devyatyj(connection, (LISTOK,))
    connection.execute(
        "insert into sheets (number, title, issued_at, ord) values (?, ?, ?, ?)",
        ("16Z", "следующий, задачи ещё не внесены", "2026-09-14", 99))
    connection.commit()
    assert pust(grobarij(konduit.razdel(kontekst(connection))))
