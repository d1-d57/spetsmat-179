#!/usr/bin/env python3
"""Галочки «в понедельник прихожу» и «в четверг прихожу» — решение владельца 07.09.

🔴 ЧТО ИМЕННО ЗДЕСЬ ПРОВЕРЯЕТСЯ И ПОЧЕМУ ЭТОГО НЕ ХВАТАЛО РАНЬШЕ. День принимающего
раньше ВЫЧИСЛЯЛСЯ: «есть ли у него в этот день дети». Такой ответ не умеет держать
отметку человека, которому детей ещё не дали, — она гасла на первой же перезагрузке.
Поэтому первый тест ниже проверяет не форму, а память: поставили — держится.

Владелец, дословно: *«не бывает принимающего, который в разные дни в разных группах,
такого никогда не было… он ходит только в одну группу, за которой он фиксирован, но
либо один, либо два дня»*. Отсюда второй тест: группа одна на человека, а не на день.
"""
from __future__ import annotations

import sqlite3

import config
import pytest
from infra.db import apply_migrations, connect
from infra.prepodavatel_den_repo import dni, otmetit


@pytest.fixture
def baza(tmp_path):
    path = tmp_path / "spetsmat.db"
    apply_migrations(path, config.MIGRATIONS_DIR)
    c = connect(path)
    c.execute("insert into teachers (name, aka, is_owner) values ('Пример', 'П', 0)")
    c.execute("insert into sheets (number, title, issued_at, ord) "
              "values ('1', 'листок', '2026-09-01', 1)")
    c.execute("insert into students (surname, name, class, status, first_sheet_id) "
              "values ('Фамилия', 'Имя', '9К', 'active', 1)")
    c.execute("insert into enrollment (student_id, teacher_id, room, slot, "
              "valid_from, valid_to) values (1, 1, '201', 1, '2026-09-01', '9999-12-31')")
    c.commit()
    return c


def test_the_tick_of_a_day_survives_being_read_back(baza):
    """Память дня — это память, а не отражение `enrollment`.

    Ставим галочку четверга человеку, у которого В ЧЕТВЕРГ НЕТ НИ ОДНОГО ребёнка.
    Прежняя, вычисляемая версия ответила бы «не приходит» — и стёрла бы ровно то,
    что владелец только что отметил.
    """
    otmetit(baza, 1, 2, True)
    assert 2 in dni(baza)[1], "поставленная галочка обязана пережить чтение"

    otmetit(baza, 1, 2, False)
    assert 2 not in dni(baza).get(1, set()), "снятая — тоже"
    assert 1 in dni(baza)[1], "второй день не тронут"


def test_the_first_fill_marks_only_the_day_a_teacher_is_visibly_absent_from(baza):
    """Первое заполнение читается из `enrollment` и отмечает ТОЛЬКО отсутствие.

    У человека открытая строка в понедельник и ни одной в четверг — значит в
    четверг он не приходит, а в понедельник приходит. Это ровно то, что показывал
    экран до появления галочек: переезд не меняет ни одного ответа под руками у
    владельца.
    """
    # Таблица заводится ПУСТОЙ базе, а заполняется по той, где данные уже есть, —
    # на боевой это один момент, здесь два. Роняем её и просим завести заново:
    # это ровно тот путь, которым пойдёт миграция на живой базе.
    baza.execute("drop table prepodavatel_ne_prihodit")
    baza.commit()

    est = dni(baza)[1]
    assert 1 in est and 2 not in est, est


def test_a_teacher_nobody_has_given_children_to_yet_still_comes(baza):
    """Про кого не сказано ничего — тот ходит. Пустая таблица = «все ходят всегда».

    Иначе КАЖДЫЙ новый преподаватель появлялся бы «не ходящим ни в один день», и
    его пришлось бы «включать» руками, гадая, почему его нигде нет.
    """
    baza.execute("insert into teachers (name, aka, is_owner) values ('Новый', 'Н', 0)")
    baza.commit()
    novyj = baza.execute("select id from teachers where name = 'Новый'").fetchone()[0]
    assert dni(baza)[novyj] == {1, 2}


def test_the_day_never_carries_a_group(baza):
    """Группа одна на человека — в таблице дней её нет и быть не должно.

    Решение владельца 07.09. Колонка `gruppa` здесь разрешила бы записать
    «в понедельник в В, в четверг в Д» — то, чего в школе не бывает.
    """
    kolonki = {r[1] for r in baza.execute(
        "pragma table_info(prepodavatel_ne_prihodit)")}
    assert kolonki == {"teacher_id", "slot"}, kolonki


def test_a_pupil_left_without_a_teacher_that_day_is_still_on_the_lesson_screen(baza):
    """Ребёнок, оставшийся без строки на этот день, ОБЯЗАН быть виден.

    🔴 ЦЕНА, ЗАМЕРЕННАЯ ЖИВЬЁМ 07.09: у принимающего сняли четверг, три его строки
    закрылись — и трое детей исчезли из четверга совсем: ни в чьём списке, ни в
    «некуда деть». Состав дня собирался из `enrollment`, то есть отвечал «кого куда
    распределили», а спрашивают у него «все ли на месте».
    """
    from core.services.sostav_na_den import SostavService
    from infra.enrollment_repo import SqliteEnrollmentRepo
    from infra.room_repo import SqliteAttendance, SqliteSessions

    class Vse:
        def aktivnye(self):
            return [r[0] for r in baza.execute("select id from students")]

    chetverg = "2026-09-10"      # четверг, слот 2 — строк у школьника там нет
    sostav = SostavService(
        enrollment=SqliteEnrollmentRepo(baza),
        sessions=SqliteSessions(baza),
        attendance=SqliteAttendance(baza),
        roster=Vse(),
    ).sostav(chetverg)

    krasnye = [m.student_id for m in sostav.krasnye]
    assert krasnye == [1], "школьник без преподавателя на этот день обязан краснеть"

    bez_roster = SostavService(
        enrollment=SqliteEnrollmentRepo(baza),
        sessions=SqliteSessions(baza),
        attendance=SqliteAttendance(baza),
    ).sostav(chetverg)
    assert bez_roster.mesta == (), "без списка школьников служба отвечает как раньше"
