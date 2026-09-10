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


@pytest.fixture
def mir(connection):
    """Пять школьников, один листок, ни одной отметки — отметки ставит сам тест."""
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
