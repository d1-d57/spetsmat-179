"""Отсутствие ПРИНИМАЮЩЕГО на день снимает прикрепление и сохраняет аудиторию.

🔴 ЭТОТ ТЕСТ СРАВНИВАЕТ С «БЫЛО», А НЕ С НУЛЁМ, И ЭТО ЕГО ГЛАВНОЕ СВОЙСТВО.
Правило выведено волной УТРО 10.09 на живом отказе: проверка, утверждающая «стало
ноль», зеленеет и тогда, когда ноль был всегда — например, когда данных не завезли
вовсе. Такая проверка не отличает починку от пустоты. Поэтому здесь снимаются ТРИ
состояния подряд одного и того же состава: как было · при отметке · после снятия, —
и утверждения делаются о ПЕРЕХОДАХ между ними.

Требование владельца 10.09, дословно: «сегодня нет Нади… она отмечается как
отсутствующая, но в распределении её дети остаются закреплёнными за ней. Так не
должно быть, они должны оставаться в той же аудитории, но без прикрепления к
принимающему».
"""

import sqlite3

import pytest

from core.services.sostav_na_den import SostavService

OTSUTSTVUET = "не был"


class _Ryady:
    """Постоянные строки: три школьника у одного преподавателя, все в 203."""

    def __init__(self, teacher_id, room="203"):
        self._t, self._r = teacher_id, room

    def rows_valid_on(self, den, slot, students=None):
        class R:
            pass
        out = []
        for sid in (1, 2, 3):
            r = R(); r.student_id = sid; r.teacher_id = self._t
            r.room = self._r; r.id = sid; r.slot = slot
            out.append(r)
        return out


class _Sessii:
    def for_day(self, den):
        class S:
            id = 1
        return S()


class _Otkloneniya:
    def rows_for_session(self, session_id):
        return []


def _sostav(net_segodnya):
    return SostavService(
        enrollment=_Ryady(teacher_id=9),
        sessions=_Sessii(),
        attendance=_Otkloneniya(),
        otsutstvuyushchie_prepoda=lambda d: net_segodnya,
    ).sostav("2026-09-10")


def test_otsutstvie_prepodavatelya_snimaet_prikreplenie_i_hranit_auditoriyu():
    bylo = _sostav(frozenset())
    pri_otmetke = _sostav(frozenset({9}))
    posle_snyatiya = _sostav(frozenset())

    # 1. БЫЛО: все трое закреплены. Без этого утверждения следующее ничего не стоит.
    assert [m.segodnya for m in bylo.mesta] == [9, 9, 9]
    assert [m.room for m in bylo.mesta] == ["203", "203", "203"]

    # 2. ПЕРЕХОД: прикрепление снялось У ТЕХ ЖЕ, аудитория осталась ТА ЖЕ.
    assert [m.segodnya for m in pri_otmetke.mesta] == [None, None, None]
    assert [m.room for m in pri_otmetke.mesta] == [m.room for m in bylo.mesta]
    # `obychno` не трогается: постоянное распределение — не про этот день.
    assert [m.obychno for m in pri_otmetke.mesta] == [m.obychno for m in bylo.mesta]
    # Счётчик отсутствующего — ноль. Считается ровно так же, как на экране.
    assert sum(1 for m in pri_otmetke.mesta if m.segodnya == 9) == 0
    assert sum(1 for m in bylo.mesta if m.segodnya == 9) == 3

    # 3. ОБРАТИМОСТЬ: снятие отметки возвращает ровно то, что было.
    assert [(m.student_id, m.segodnya, m.room) for m in posle_snyatiya.mesta] \
        == [(m.student_id, m.segodnya, m.room) for m in bylo.mesta]


def test_v_sloj_zanyatiya_nichego_ne_pishetsya():
    """Состояние ВЫЧИСЛЯЕМОЕ: отклонений не заводится ни одного.

    `teacher_id = NULL` в строке отклонения означает «перекрытия нет», то есть
    постоянный преподаватель ОСТАЁТСЯ — ровно то, от чего избавляемся. Поэтому
    запись сюда не только лишняя, но и обратная по смыслу.
    """
    pri_otmetke = _sostav(frozenset({9}))
    assert all(not m.otklonenie for m in pri_otmetke.mesta)
    assert all(not m.perekryt_prepodavatelem for m in pri_otmetke.mesta)
