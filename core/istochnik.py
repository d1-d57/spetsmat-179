"""ОДИН ИСТОЧНИК ПРАВДЫ: кто спросил базу — тот и называет, КАКУЮ базу он спросил.

🔴 ЗАЧЕМ ЭТОТ МОДУЛЬ ЕСТЬ. Требование владельца 10.09, дословно: «источник истины
один — задачи в базе, они там внесены поимённо, и оттуда же подгружаются в кондуит.
Надо удалить другой неактуальный источник, в который ты смотришь, раз и навсегда».

ЦЕНА, ОПЛАЧЕННАЯ ДО ЭТОГО МОДУЛЯ И ЗАМЕРЕННАЯ:
  * `data/spetsmat.db` лежала в git И одновременно жила. В свежем worktree выезжала
    версия БЕЗ миграции 009 — сайт там не поднимался вовсе, позиция потеряла целый
    прогон и дважды подменяла базу руками;
  * оркестратор волны УТРО смотрел на ДАТУ ФАЙЛА (12:21 сегодня) и считал базу
    свежей, когда самая поздняя запись в ней была от 3 сентября;
  * ни один из инструментов, читающих базу, не печатал, КАКУЮ базу он открыл, —
    поэтому число из мёртвой копии выглядело точно так же, как число из живой.

ДАТА ФАЙЛА НИЧЕГО НЕ ГОВОРИТ О СОДЕРЖИМОМ. Копирование, `git checkout`, rsync,
открытие в WAL-режиме — всё это трогает mtime, не добавив ни одной записи. Поэтому
здесь считается дата САМОЙ ПОЗДНЕЙ ЗАПИСИ ВНУТРИ базы, а не дата файла.
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import date as _date
from pathlib import Path
from typing import Optional, Tuple

#: Таблицы и колонки, по которым судится «когда в эту базу писали в последний раз».
#: Список НЕ полон намеренно: сюда входит только то, что меняется на занятии.
#: 🔴 `sessions.held_on` СЮДА НЕ ВХОДИТ, И ЭТО НЕ ОПЕЧАТКА. Занятие заводится
#: ЗАРАНЕЕ: это дата ПЛАНА, а не след того, что в базу писали. Первая версия этого
#: модуля её включала — и критерий владельца («живая и мёртвая печатают РАЗНЫЕ даты,
#: вторая красная») провалился на первом же прогоне: мёртвая копия показала ту же
#: дату 2026-09-10, потому что помнила будущее занятие, не имея ни одной записи о
#: нём. Ровно тот класс, ради которого модуль и написан: величина, которая ВЫГЛЯДИТ
#: как свежесть, но ею не является. Поймано критерием, а не глазами.
ГДЕ_ДАТЫ = (
    ("marks", "valid_at"),
    ("marks", "recorded_at"),
    ("attendance_pometki", "kogda"),
    ("enrollment", "valid_from"),
)


def poslednyaya_zapis(conn: sqlite3.Connection) -> Optional[str]:
    """Дата самой поздней записи ВНУТРИ базы, `YYYY-MM-DD`, или `None` для пустой."""
    naidено = []
    for tablica, kolonka in ГДЕ_ДАТЫ:
        try:
            r = conn.execute(f"select max({kolonka}) from {tablica}").fetchone()
        except sqlite3.Error:
            continue          # таблицы нет в этой схеме — не беда и не ошибка
        if r and r[0]:
            naidено.append(str(r[0])[:10])
    return max(naidено) if naidено else None


def poslednee_zanyatie(conn: sqlite3.Connection, segodnya: Optional[str] = None) -> Optional[str]:
    """Дата последнего ПРОШЕДШЕГО занятия — то, с чем сверяется свежесть.

    🔴 `max(held_on)` БЕЗ ОТСЕЧКИ ПО СЕГОДНЯ — ОШИБКА, И ОНА БЫЛА ЗДЕСЬ. Расписание
    заводится вперёд: на боевой базе 10.09 лежали занятия `2026-09-07`, `2026-09-10`
    и `2026-10-01`. Сравнение с максимумом объявляло МЁРТВОЙ живую боевую базу —
    «последняя запись 2026-09-10, а последнее занятие 2026-10-01», — то есть требовало
    записей о занятии, которое ещё не состоялось. Поймано прогоном на боевой, не
    рассуждением: это вторая ошибка того же рода в этом файле за десять минут, и обе
    поймал критерий, а не глаз.
    """
    segodnya = segodnya or _date.today().isoformat()
    try:
        r = conn.execute("select max(held_on) from sessions where held_on <= ?",
                         (segodnya,)).fetchone()
    except sqlite3.Error:
        return None
    return str(r[0])[:10] if r and r[0] else None


def put_bazy(conn: sqlite3.Connection) -> str:
    """АБСОЛЮТНЫЙ путь открытой базы, спрошенный у самого соединения.

    Спрашивается у `PRAGMA database_list`, а не берётся из настроек: настройка
    говорит, что СОБИРАЛИСЬ открыть, соединение — что открыли на самом деле.
    """
    try:
        for _, imya, fajl in conn.execute("PRAGMA database_list"):
            if imya == "main":
                return str(Path(fajl).resolve()) if fajl else "<в памяти>"
    except sqlite3.Error:
        pass
    return "<неизвестно>"


def nazvat(conn: sqlite3.Connection, potok=None) -> Tuple[str, Optional[str]]:
    """ПЕРВАЯ СТРОКА любого инструмента, печатающего числа из базы.

    Печатает абсолютный путь и дату последней записи. Возвращает обе величины,
    чтобы звавший мог их же и проверить.
    """
    potok = potok or sys.stdout
    put = put_bazy(conn)
    posl = poslednyaya_zapis(conn)
    print(f"источник: {put} · последняя запись: {posl or '—'}", file=potok)
    return put, posl


def proverit_svezhest(conn: sqlite3.Connection, potok=None) -> int:
    """🔴 КРАСНЕЕТ, если база старше последнего занятия, которое сама же помнит.

    Без этой проверки «печатать путь и дату» — надежда: напечатать можно и не
    посмотреть. Возврат — код: 0 свежая, 1 мёртвая.

    Сравнение идёт с последним занятием ИЗ ЭТОЙ ЖЕ базы, а не с системным
    «сегодня»: копия недельной давности помнит и своё последнее занятие тоже, и
    именно расхождение «занятие было, записей после него нет» её выдаёт.
    """
    potok = potok or sys.stderr
    posl = poslednyaya_zapis(conn)
    zan = poslednee_zanyatie(conn)
    if posl is None:
        print("🔴 БАЗА ПУСТА: ни одной записи. Числа из неё ничего не значат.", file=potok)
        return 1
    if zan and posl < zan:
        print(f"🔴 БАЗА МЁРТВАЯ: последняя запись {posl}, а последнее занятие {zan}. "
              f"Это КОПИЯ или отставшая версия — числа из неё описывают прошлое.",
              file=potok)
        return 1
    return 0


def nazvat_i_proverit(conn: sqlite3.Connection, potok=None) -> int:
    """Одной строкой то, что обязан сделать КАЖДЫЙ инструмент, печатающий числа.

    🔴 ЗАЧЕМ ОТДЕЛЬНАЯ ФУНКЦИЯ, А НЕ ДВА ВЫЗОВА НА КАЖДОМ ВЫЗЫВАЮЩЕМ. Их
    пятнадцать. Два вызова означали бы пятнадцать мест, где можно забыть второй, —
    и первый же забывший печатал бы источник, не проверив его свежесть, то есть
    выглядел бы честным, не будучи им. Здесь пара неразделима по построению.

    Печатает в `stdout` (это часть вывода инструмента, а не диагностика), возвращает
    код свежести: 0 — свежая, 1 — мёртвая. Инструмент волен решить, падать ли ему на
    единице; молча проигнорировать её он тоже может, но уже НАПЕЧАТАВ красное.
    """
    potok = potok or sys.stdout
    nazvat(conn, potok)
    return proverit_svezhest(conn, potok)


class SvidetelRaboty:
    """🔴 СВИДЕТЕЛЬ РАБОТЫ С ДАННЫМИ — ВМЕСТО КОММИТА, КОТОРОГО БОЛЬШЕ НЕ БУДЕТ.

    Живая база ушла из git (Д1), и это создало дыру ТЕМ ЖЕ ходом, которым закрыло
    другую: гейт «работа доехала в git» стоит ПЕРВЫМ во всей приёмке и работу с
    ДАННЫМИ больше не покрывает вовсе. Отсутствие коммита стало неотличимо от
    отсутствия работы — и это не рассуждение: 10.09 аналитик объявил внесённые с
    бумаги отметки невнесёнными, потому что искал копию базы в локальной папке, а
    она лежала на сервере. Тридцать шесть отметок существовали, а свидетеля не было.

    Поэтому свидетель делается ФОРМОЙ, а не разовой любезностью отчёта. Три
    величины, и все три снимаются КОМАНДОЙ, а не переписываются из памяти:
      * дата последней записи ДО работы,
      * дата последней записи ПОСЛЕ,
      * число затронутых строк (`total_changes` соединения — считает сама sqlite).

    Пример:
        with SvidetelRaboty(conn, "внесение кондуитов с бумаги 07.09") as svid:
            ...                       # работа
        print(svid.otchyot())
    """

    def __init__(self, conn: sqlite3.Connection, chto: str) -> None:
        self._conn = conn
        self._chto = chto
        self._put = put_bazy(conn)
        self._do = None
        self._posle = None
        self._strok_do = 0
        self._strok_posle = 0

    def __enter__(self) -> "SvidetelRaboty":
        self._do = poslednyaya_zapis(self._conn)
        self._strok_do = self._conn.total_changes
        return self

    def __exit__(self, tip, znachenie, sled) -> bool:
        self._posle = poslednyaya_zapis(self._conn)
        self._strok_posle = self._conn.total_changes
        return False          # исключения не глотаем: упавшая работа обязана упасть

    @property
    def zatronuto(self) -> int:
        return self._strok_posle - self._strok_do

    def otchyot(self) -> str:
        """Три строки, которые вставляются в отчёт как есть."""
        sdvinulos = "ДА" if self._do != self._posle else "нет"
        return (
            "— СВИДЕТЕЛЬ РАБОТЫ С ДАННЫМИ: %s —\n"
            "   база: %s\n"
            "   последняя запись ДО: %s · ПОСЛЕ: %s · сдвинулась: %s\n"
            "   затронуто строк: %d"
            % (self._chto, self._put, self._do or "—", self._posle or "—",
               sdvinulos, self.zatronuto)
        )


# ───────────────────────────────────────────────────────────────────────────────
# ДВЕРЬ: `python3 core/istochnik.py [путь]`
#
# 🔴 МОЛЧАЩАЯ ДВЕРЬ НЕОТЛИЧИМА ОТ СЛОМАННОЙ. Первая версия этого файла при прямом
# запуске печатала НОЛЬ строк и выходила с кодом 0 — владелец запустил её в 14:09 и
# не получил ничего. Это тот же класс, ради которого весь модуль и написан: «ноль
# находок» читается как «чисто», а на деле означает «никто не смотрел». Инструмент,
# который умеет назвать источник, ОБЯЗАН называть его и когда спрашивают его самого.
#
# Код возврата: 0 — база свежая, 1 — мёртвая или пустая, 2 — открыть не удалось.

def _dver(argv=None) -> int:
    import argparse
    import os

    razbor = argparse.ArgumentParser(
        description="Назвать источник: путь базы, дату последней записи, вердикт свежести.")
    razbor.add_argument("baza", nargs="?", default=None,
                        help="путь к базе; без него — та, что назначена в config.DB_PATH")
    args = razbor.parse_args(argv)

    put = args.baza
    if put is None:
        # 🔴 КОРЕНЬ РЕПОЗИТОРИЯ В `sys.path` — ИМЕННО ПРИ ПРЯМОМ ЗАПУСКЕ. Запущенный
        # как `python3 core/istochnik.py`, файл видит своим корнем `core/`, и
        # `import config` падает: дверь отвечала «не удалось узнать путь базы» там,
        # где база на месте. Импортированный модуль от этого не страдает — путь ему
        # выставляет тот, кто импортирует, — и потому дефект живёт только у двери.
        koren = str(Path(__file__).resolve().parent.parent)
        if koren not in sys.path:
            sys.path.insert(0, koren)
        try:
            from config import DB_PATH
            put = str(DB_PATH)
        except Exception as exc:                       # noqa: BLE001
            print("🔴 не удалось узнать путь базы из config: %s" % exc, file=sys.stderr)
            return 2
    if not os.path.exists(put):
        print("🔴 базы нет на диске: %s" % put, file=sys.stderr)
        return 2
    try:
        conn = sqlite3.connect("file:%s?mode=ro" % put, uri=True)
    except sqlite3.Error as exc:
        print("🔴 не удалось открыть базу %s: %s" % (put, exc), file=sys.stderr)
        return 2

    nazvat(conn)
    zan = poslednee_zanyatie(conn)
    print("последнее прошедшее занятие: %s" % (zan or "—"))
    rc = proverit_svezhest(conn, sys.stdout)
    print("вердикт: %s" % ("СВЕЖАЯ ✅" if rc == 0 else "МЁРТВАЯ 🔴"))
    return rc


if __name__ == "__main__":
    sys.exit(_dver())
