"""Кондуит и распределение отвечают ОДНО И ТО ЖЕ про принимающего на дату.

🔴 ЭТОТ ТЕСТ — ГЕЙТ ПРОТИВ ТРЕТЬЕЙ ПРАВДЫ, А НЕ ПРОВЕРКА СЕГОДНЯШНЕГО СЛУЧАЯ.
Владелец 10.09: «в распределении поменялся список школьников, а в кондуите нет, это
неправильно». Так и было: распределение считало `SostavService.sostav(den)` — со слоем
занятия и отсутствующими преподавателями, — а кондуит читал ЧИСТЫЙ `enrollment`. Надю
отмечали отсутствующей: в распределении её дети оставались без принимающего, в кондуите
продолжали носить её инициалы и считались её.

Тест сравнивает ДВА ОТВЕТА между собой, а не каждый с ожидаемым числом: пока они равны,
неважно, как именно считает каждый; разойдутся — красный, кто бы из них ни изменился.
Это дешевле и надёжнее, чем закреплять конкретные имена, которые меняются каждую неделю.
"""

import re
import sqlite3

import pytest

from core.services.sostav_na_den import SostavService, slot_of
from infra.enrollment_repo import SqliteEnrollmentRepo
from infra.room_repo import SqliteAttendance, SqliteSessions
from veb.razdely import konduit
from veb.razdely.zanyatie import otsutstvuyushchie_prepodavateli


class _Kt:
    def __init__(self, c):
        self.c = c


def _sostav(c, den):
    return SostavService(
        enrollment=SqliteEnrollmentRepo(c),
        sessions=SqliteSessions(c),
        attendance=SqliteAttendance(c),
        otsutstvuyushchie_prepoda=lambda d: otsutstvuyushchie_prepodavateli(c, d),
    ).sostav(den)


def _kto_po_konduitu(c, den):
    """{student_id: есть ли принимающий} — как это видит КОНДУИТ."""
    razmetka = konduit._prinimayushchie(_Kt(c), den)
    return {sid: True for sid in razmetka}


def test_konduit_i_raspredelenie_soglasny_pro_prinimayushchego(seeded_connection):
    """У кого распределение говорит «принимающего нет» — у того и кондуит молчит.

    Берётся ПЕРВЫЙ учебный день, на который в базе есть строки распределения: тест
    про СОГЛАСИЕ двух ответов, и конкретная дата ему безразлична.
    """
    connection = seeded_connection
    den = None
    for r in connection.execute("select distinct valid_from from enrollment order by valid_from"):
        kand = str(r[0])[:10]
        if slot_of(kand) is not None:
            den = kand
            break
    if den is None:
        pytest.skip("в базе нет ни одного учебного дня со строками распределения")

    sostav = _sostav(connection, den)
    po_konduitu = _kto_po_konduitu(connection, den)

    rashozhdenia = []
    for m in sostav.mesta:
        est_v_konduite = m.student_id in po_konduitu
        est_po_sostavu = m.segodnya is not None
        if est_v_konduite != est_po_sostavu:
            rashozhdenia.append(
                (m.student_id, "распределение: %s" % ("есть" if est_po_sostavu else "нет"),
                 "кондуит: %s" % ("есть" if est_v_konduite else "нет")))
    assert not rashozhdenia, (
        "кондуит и распределение разошлись по %d школьникам: %r"
        % (len(rashozhdenia), rashozhdenia[:5]))
