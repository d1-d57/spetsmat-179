"""Четыре величины на самой странице: разметка, а не только арифметика.

WHAT THIS FILE CATCHES THAT `test_statistiki.py` CANNOT.  The projections there are pure
and are already right; the ways this feature breaks after that are all in the wiring:

  * счётчик посчитан по ЧУЖОМУ разрезу — на панели листка стоит годовое число, и оно
    выглядит совершенно правдоподобно;
  * строка светится, но признак «свой ребёнок» при этом ПРОПАЛ, потому что классы строки
    вытеснили друг друга вместо того, чтобы сложиться;
  * число «сколько сдало» встало в шапку не того столбца — а шапка одна на двадцать один
    столбец, и сдвиг на единицу читается как совпадение;
  * инициалы принимающего приехали колонкой, чего владелец прямо не хотел.

Каждая из четырёх проверяется на РЕНДЕРЕ секции, собранной тем же вызовом, каким её
собирает сайт, — `konduit.razdel(kt)`, — на маленьком мире из `seed_world`.
"""

from __future__ import annotations

import re

import pytest

from core.models import CellState
from tests.conftest import seed_world
from veb.obshchee.karkas import Kontekst
from veb.razdely import konduit


#: Один листок: две обязательные, письменная (она тоже обязательна), звезда и обычная.
LISTOK = ("обязательная", "обязательная", "письменная", "звезда", "обычная")


#: Колонки, которые ЖИВАЯ база несёт, а `migrations/` не создаёт: `teachers.gruppa`,
#: `teachers.kabinet`, `teachers.aktiven`, `students.gruppa`.  Найдено этим заходом
#: прямым сравнением: на боевой базе они есть (и `veb/razdely/lichnaya.kabinet_na_datu`,
#: написанная соседним заходом, уже на них опирается), а база, собранная всеми десятью
#: миграциями с нуля, не имеет ни одной из них.  Здесь они дописываются, чтобы тест
#: судил ТУ схему, на которой сайт работает; чинится это в `migrations/`, а не тут — не
#: зона этого захода, и вопрос назван в `## ВОПРОСЫ`.
ZHIVYE_KOLONKI = (
    "alter table teachers add column kabinet text",
    "alter table teachers add column aktiven integer not null default 1",
    "alter table teachers add column gruppa text",
    "alter table students add column gruppa text",
)


@pytest.fixture
def mir(connection):
    """Пять школьников, один листок, ни одной отметки — отметки ставит сам тест."""
    for zapros in ZHIVYE_KOLONKI:
        connection.execute(zapros)
    return seed_world(connection, students=5, sheets=(LISTOK,))


def kontekst(connection, prepod_id=None) -> Kontekst:
    """`Kontekst` ровно с теми полями, которые кондуит читает.

    Собирается здесь руками, а не через `sobrat_kontekst`: та открывает ЖИВУЮ базу
    проекта по абсолютному пути, и тест, который её позовёт, будет проверять сегодняшние
    данные школы вместо своего мира.
    """
    return Kontekst(rezhim="admin", rol="organizator", mogu=frozenset(), c=connection,
                    DNI={}, kabinety_dnya={}, otkuda_kabinet={}, kabinety={}, gruppy={},
                    prep={}, prepod_id=prepod_id)


def otmetit(marking, student_id, problem_id, sostoyanie=CellState.SOLVED):
    marking.set_state(student_id, problem_id, sostoyanie, source="кнопка")


def panel(html: str, imya: str) -> str:
    """Одна вкладка страницы: панели лежат в DOM все сразу и скрыты стилями."""
    kusok = re.search(r'<section class="vid" id="n-%s">(.*?)</section>' % re.escape(imya),
                      html, re.S)
    assert kusok, "нет панели n-%s" % imya
    return kusok.group(1)


def schyotchiki(kusok: str) -> list:
    """Все счётчики обязательных панели, сверху вниз: `(сдано, всего)` или `None`."""
    out = []
    for m in re.finditer(r'<i class="ob-sch( net)?"[^>]*>(.*?)</i>', kusok, re.S):
        if m.group(1):
            out.append(None)
            continue
        chisla = re.match(r'(\d+)<span class="iz">/(\d+)</span>$', m.group(2))
        assert chisla, "счётчик написан не двумя числами: %r" % m.group(2)
        out.append((int(chisla.group(1)), int(chisla.group(2))))
    return out


# --------------------------------------------- величина 1: обязательные у школьника


def test_the_counter_stands_left_of_every_pupil_on_every_panel(mir, connection, marking):
    """Пять школьников — пять счётчиков на каждой панели, и ни одним больше.

    Панелей три: годовой обзор девятого, годовой обзор восьмого и сам листок. Счётчик,
    забытый на одной из них, оставляет ровно ту дыру, ради которой величину и заводили.
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
    otmetit(marking, uchenik, zadachi[2])          # письменная — тоже обязательная
    otmetit(marking, uchenik, zadachi[3])          # звезда — не считается вовсе
    connection.commit()
    schyot = schyotchiki(panel(konduit.razdel(kontekst(connection)),
                               str(mir.sheet_ids[0])))[0]
    assert schyot == (2, 3), "три обязательных на листке, сдано две из них"


def test_a_retracted_obligatory_is_not_counted_as_handed_in(mir, connection, marking):
    """Сдал и не защитил — это не «сдал», и на экране тоже."""
    zadachi = mir.problems_by_sheet[mir.sheet_ids[0]]
    uchenik = mir.student_ids[0]
    otmetit(marking, uchenik, zadachi[0])
    otmetit(marking, uchenik, zadachi[0], CellState.RETRACTED)
    connection.commit()
    assert schyotchiki(panel(konduit.razdel(kontekst(connection)),
                            str(mir.sheet_ids[0])))[0] == (0, 3)


# ------------------------------------------------------- величина 2: строка светится


def test_the_row_glows_exactly_for_the_pupil_who_closed_his_obligatory(
    mir, connection, marking
):
    zadachi = mir.problems_by_sheet[mir.sheet_ids[0]]
    for zadacha in (zadachi[0], zadachi[1], zadachi[2]):
        otmetit(marking, mir.student_ids[0], zadacha)
    # Второй школьник сдал ЗВЕЗДУ и обычную — обязательных не закрыл ни одной.
    otmetit(marking, mir.student_ids[1], zadachi[3])
    otmetit(marking, mir.student_ids[1], zadachi[4])
    connection.commit()
    kusok = panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0]))
    stroki = re.findall(r'<tr( class="[^"]*")?><td class="kto">', kusok)
    goryat = [i for i, klass in enumerate(stroki) if "gotov" in (klass or "")]
    assert goryat == [0], "светится ровно строка того, кто закрыл обязательные"


def test_a_listok_with_no_obligatory_problems_lights_up_nobody(connection, marking):
    """`1д`–`4д` на живой базе именно такие: 99 задач и ни одной обязательной."""
    for zapros in ZHIVYE_KOLONKI:
        connection.execute(zapros)
    mir = seed_world(connection, students=3, sheets=(("звезда", "обычная"),))
    connection.commit()
    kusok = panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0]))
    assert "gotov" not in kusok
    assert schyotchiki(kusok) == [None, None, None], "листок без обязательных пишет точку"


def test_being_mine_and_having_closed_are_both_visible_at_once(
    mir, connection, marking
):
    """Два признака СКЛАДЫВАЮТСЯ. Прежняя форма выражения («свой» ИЛИ «чужой») не имела
    места для третьего класса, и добавить его, не потеряв первый, — это и есть проверка.
    """
    zadachi = mir.problems_by_sheet[mir.sheet_ids[0]]
    for zadacha in zadachi[:3]:
        otmetit(marking, mir.student_ids[0], zadacha)
    prepod = mir.teacher_ids[0]
    connection.execute(
        "insert into enrollment (student_id, teacher_id, room, slot, valid_from) "
        "values (?, ?, ?, ?, ?)",
        (mir.student_ids[0], prepod, "303", 1, "2020-01-01"))
    connection.commit()
    kusok = panel(konduit.razdel(kontekst(connection, prepod_id=prepod)),
                  str(mir.sheet_ids[0]))
    pervaya = re.search(r'<tr class="([^"]*)"><td class="kto">', kusok).group(1)
    assert "moi" in pervaya and "gotov" in pervaya, pervaya


# ------------------------------------------------- величина 3: сколько сдало задачу


def shapka(kusok: str) -> list:
    """Столбцы листка сверху вниз: `(метка, сдало, закрыта ли классом)`."""
    return [(m.group("label"), int(m.group("n")), bool(m.group("zakr")))
            for m in re.finditer(
                r'<th class="zn">(?P<label>.*?)(?:<i class="pm[^>]*>.</i>)?'
                r'<b class="sdalo(?P<zakr> zakr)?"[^>]*>(?P<n>\d+)</b></th>', kusok)]


def test_every_column_carries_how_many_took_it_and_the_number_is_per_column(
    mir, connection, marking
):
    """Число стоит у СВОЕГО столбца.

    Сдвиг на единицу — самая правдоподобная поломка этой величины: шапка одна на
    двадцать один столбец, все числа на месте, и ни одно не относится к своей задаче.
    Поэтому мир нарочно сделан так, что все пять чисел РАЗНЫЕ.
    """
    zadachi = mir.problems_by_sheet[mir.sheet_ids[0]]
    for nomer, zadacha in enumerate(zadachi):        # 0, 1, 2, 3 и 4 сдавших
        for uchenik in mir.student_ids[:nomer]:
            otmetit(marking, uchenik, zadacha)
    connection.commit()
    stolbcy = shapka(panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0])))
    assert [n for _label, n, _z in stolbcy] == [0, 1, 2, 3, 4]
    assert [label for label, _n, _z in stolbcy] == ["1.1", "1.2", "1.3", "1.4", "1.5"]


def test_closed_by_the_class_means_MORE_than_three_took_it(mir, connection, marking):
    """Ровно три — ещё не закрыта; четыре — закрыта. Слова владельца, буквально."""
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
    """Ровно тот случай, ради которого порог и придуман: сдали, но не защитили."""
    zadacha = mir.problems_by_sheet[mir.sheet_ids[0]][0]
    for uchenik in mir.student_ids[:5]:
        otmetit(marking, uchenik, zadacha)
    for uchenik in mir.student_ids[:4]:
        otmetit(marking, uchenik, zadacha, CellState.RETRACTED)
    connection.commit()
    stolbcy = shapka(panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0])))
    assert (stolbcy[0][1], stolbcy[0][2]) == (1, False)


# --------------------------------------------- величина 4: инициалы принимающего


PRIN = re.compile(r'<i class="prin( net)?" title="принимающий:? ?([^"]*)">([^<]*)</i>')


def zapisat(connection, student_id, teacher_id, slot, room="303",
            ot="2020-01-01", do="9999-12-31"):
    connection.execute(
        "insert into enrollment (student_id, teacher_id, room, slot, valid_from, valid_to) "
        "values (?, ?, ?, ?, ?, ?)", (student_id, teacher_id, room, slot, ot, do))


def test_the_initials_stand_beside_the_surname_and_not_in_a_column_of_their_own(
    mir, connection
):
    """Решение владельца 09.09 — «не колонкой».

    Проверяется формой: число `<th>` в шапке обязано остаться числом задач плюс один
    столбец фамилии.  Колонка принимающего прошла бы любую проверку текста.
    """
    zapisat(connection, mir.student_ids[0], mir.teacher_ids[0], 1)
    connection.commit()
    kusok = panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0]))
    assert len(re.findall(r"<th[ >]", kusok)) == 1 + len(LISTOK)
    # А сами инициалы — внутри ячейки фамилии.
    yacheyka = re.search(r'<td class="kto">(.*?)</td>', kusok, re.S).group(1)
    assert '<i class="prin"' in yacheyka


def test_the_hover_carries_the_name_the_group_and_the_room(mir, connection):
    connection.execute("update teachers set name = ?, gruppa = ? where id = ?",
                       ("Андрей Рябичев", "Д", mir.teacher_ids[0]))
    zapisat(connection, mir.student_ids[0], mir.teacher_ids[0], 1, room="302")
    connection.commit()
    kusok = panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0]))
    net, title, txt = PRIN.findall(kusok)[0]
    assert txt == "А.Р."
    assert title == "Андрей Рябичев · группа Д · кабинет 302"
    assert not net


def test_a_pupil_with_no_open_row_gets_a_dash_and_not_a_blank(mir, connection):
    """Пустое место читается как «забыли нарисовать»; прочерк говорит, что ответа нет."""
    connection.commit()
    kusok = panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0]))
    nayden = PRIN.findall(kusok)
    assert len(nayden) == 5
    assert all(net and txt == "—" for net, _title, txt in nayden)


def test_a_row_that_is_already_closed_does_not_name_a_принимающий(mir, connection):
    """Интервал полуоткрытый: закрытая вчера строка сегодня уже не отвечает.

    `valid_to` — это день, С КОТОРОГО строка не действует, и `<=` вместо `<` показал бы
    вчерашнего принимающего ещё один день.
    """
    zapisat(connection, mir.student_ids[0], mir.teacher_ids[0], 1,
            ot="2020-01-01", do="2020-06-01")
    connection.commit()
    kusok = panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0]))
    assert PRIN.findall(kusok)[0][2] == "—"


def test_two_different_принимающих_are_both_named_with_their_days(mir, connection):
    """Разные люди в понедельник и в четверг — подсказка обязана сказать, кто когда."""
    connection.execute("update teachers set name = ?, gruppa = ? where id = ?",
                       ("Андрей Рябичев", "Д", mir.teacher_ids[0]))
    connection.execute("update teachers set name = ?, gruppa = ? where id = ?",
                       ("Ваня Яковлев", "В", mir.teacher_ids[1]))
    zapisat(connection, mir.student_ids[0], mir.teacher_ids[0], 1, room="302")
    zapisat(connection, mir.student_ids[0], mir.teacher_ids[1], 2, room="303")
    connection.commit()
    kusok = panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0]))
    _net, title, txt = PRIN.findall(kusok)[0]
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
    _net, title, txt = PRIN.findall(kusok)[0]
    assert txt == "А.Р.", "один человек — одни инициалы, а не «А.Р./А.Р.»"
    assert title.startswith("Андрей Рябичев"), "дня недели тут не нужно: он один и тот же"


def test_a_one_word_name_keeps_its_word():
    """«Надя» и «Наталья Амбург» — двое живых принимающих, и «Н.» слило бы их в одно."""
    assert konduit.initsialy("Надя") == "Надя"
    assert konduit.initsialy("Наталья Амбург") == "Н.А."
