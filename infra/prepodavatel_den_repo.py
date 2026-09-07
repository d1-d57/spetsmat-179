#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-code — read by `veb/obshchee/karkas.sobrat_kontekst`,
# written by `veb/server._post_prepodavateli`.
"""В какие дни принимающий НЕ приходит: `prepodavatel_ne_prihodit`, и только это.

🔴 ТАБЛИЦА ОТВЕЧАЕТ НА ОДИН ВОПРОС, И ЕГО СТОИТ НАПИСАТЬ ДОСЛОВНО: «отмечено ли,
что этот человек в этот день не приходит». Не «в какой он группе в этот день» —
владелец 07.09 сказал прямо: *«не бывает принимающего, который в разные дни в
разных группах, такого никогда не было… он ходит только в одну группу, за которой
он фиксирован, но либо один, либо два дня»*. Группа лежит одной колонкой на
человека (`teachers.gruppa`) и здесь не повторяется.

🔴 ХРАНИТСЯ ОТСУТСТВИЕ, А НЕ ПРИСУТСТВИЕ. Пустая таблица значит «все ходят всегда»,
и это правда про 14 из 14 сегодня. Храни мы обратное, каждый НОВЫЙ преподаватель
появлялся бы «не ходящим ни в один день», пока про него не вспомнят отдельно.

🔴 ПОЧЕМУ ЭТОГО НЕЛЬЗЯ ВЫЧИСЛИТЬ ИЗ `enrollment`. Вычисляется только половина —
«у него сегодня есть дети». Вторая половина, «придёт, но детей ему ещё не дали»,
не выразима ни одной строкой `enrollment`, а именно она и нужна: галочка, которую
поставили в этом состоянии, обязана пережить перезагрузку страницы.

Таблицу заводит `migrations/007_prepodavatel_po_dnyam.sql`. `obespechit` ниже —
не второй источник правды, а страховка для базы, до которой миграция ещё не
доехала: та же форма и то же первое заполнение.
"""
from __future__ import annotations

import sqlite3

#: Открытый интервал `enrollment`: `valid_to` там `not null`, и его «пусто» — вот это.
OTKRYTA = "9999-12-31"

#: Дни занятий, в номерах `enrollment.slot`: 1 понедельник, 2 четверг (миграция 003).
SLOTY = (1, 2)


def obespechit(c: sqlite3.Connection) -> None:
    """Завести таблицу и отметить явные отсутствия, если её ещё нет. Молча и ОДИН РАЗ.

    🔴 «ОДИН РАЗ» ЗДЕСЬ — ПРОВЕРЯЕМОЕ УСЛОВИЕ, А НЕ ОБЕЩАНИЕ, И ЦЕНА ЕГО ИЗМЕРЕНА
    ЖИВЬЁМ. Пока первое заполнение шло на КАЖДОМ вызове, отметка возвращалась сама:
    её удаляли, а следующее же чтение вписывало обратно из `enrollment`. То есть
    отметка не держалась ни одной перезагрузки — ровно та болезнь, ради которой
    таблица и заведена. Поэтому: таблица уже есть — не трогаем ничего.
    """
    if c.execute("select 1 from sqlite_master where type = 'table' "
                 "and name = 'prepodavatel_ne_prihodit'").fetchone():
        return
    c.execute("""
        create table if not exists prepodavatel_ne_prihodit (
            teacher_id  integer not null references teachers(id),
            slot        integer not null check (slot between 1 and 7),
            primary key (teacher_id, slot)
        )
    """)
    # Кто ведёт детей в один день и не ведёт в другой — в другой не приходит:
    # ровно это показывал экран до того, как у дня появилась своя память. Кто не
    # ведёт никого вовсе, не отсутствует — ему просто ещё никого не дали.
    c.execute("""
        insert or ignore into prepodavatel_ne_prihodit (teacher_id, slot)
        select vedushchie.teacher_id, dni.slot
        from (select distinct teacher_id from enrollment where valid_to = ?) vedushchie
        cross join (select 1 as slot union all select 2) dni
        where not exists (
            select 1 from enrollment e
            where e.teacher_id = vedushchie.teacher_id
              and e.slot = dni.slot
              and e.valid_to = ?)
    """, (OTKRYTA, OTKRYTA))
    c.commit()


def dni(c: sqlite3.Connection) -> dict:
    """`{teacher_id: {slot, …}}` — дни, в которые человек ПРИХОДИТ.

    Спрашивают у этой функции присутствие, а хранится отсутствие: разворот делается
    здесь, один раз, чтобы экран не думал об этом на каждой строке.
    """
    obespechit(c)
    net: dict = {}
    for row in c.execute("select teacher_id, slot from prepodavatel_ne_prihodit"):
        net.setdefault(row[0], set()).add(row[1])
    vse = {r[0] for r in c.execute("select id from teachers")}
    return {tid: {s for s in SLOTY if s not in net.get(tid, ())} for tid in vse}


def otmetit(c: sqlite3.Connection, teacher_id: int, slot: int, prihodit: bool) -> None:
    """Поставить или снять галочку дня. Строк `enrollment` НЕ трогает.

    Открепление школьников при снятой галочке — отдельное действие и отдельное
    решение: оно правит чужие строки, и место ему там, где это видно, — в
    `veb/server._post_prepodavateli`, рядом с тем же приёмом для смены группы.
    """
    obespechit(c)
    if prihodit:
        c.execute("delete from prepodavatel_ne_prihodit "
                  "where teacher_id = ? and slot = ?", (teacher_id, slot))
    else:
        c.execute("insert or ignore into prepodavatel_ne_prihodit (teacher_id, slot) "
                  "values (?, ?)", (teacher_id, slot))
    c.commit()
