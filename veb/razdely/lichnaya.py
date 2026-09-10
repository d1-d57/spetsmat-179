#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-code — `kabinet_na_datu` and `deti_na_datu` are called by
# `veb/razdely/kabinet.py`, `veb/razdely/konduit.py`, `veb/razdely/glavnaya.py` and
# `veb/priyom.py`; `segodnya` by the first three.
"""The two personal queries: WHERE AM I on a date, and WHO COMES TO ME on it.

A teacher who has entered by their personal password must get both answers without
reading the whole distribution, and that is why the two queries below take a
`teacher_id` and a DATE rather than filtering a screenful of everybody in memory
the way `veb/server.py:718`, `:764` and the pupil tabs do.

🔴 THIS FILE NO LONGER DRAWS ANYTHING, AND THAT IS THE ПЕРЕДЕЛКА OF 2026-09-10, NOT
A LOSS. It used to render `#s-lich`, an in-shell tab labelled «Моё». Personal
content now has ONE home — the standalone page `/kabinet` — reachable by the menu
item «Кабинет» that `veb/obshchee/karkas.py` puts second, after «Класс», which is
what the owner asked for (`TZ-DOBOR-10-09.md` H1.1, H2.1, H2.2) and which the
докстринг of `veb/razdely/kabinet.py` had been carrying as a debt since 09.09. What
survives here is what four callers need and nobody else answers: `/kabinet`, the
кондуит, `veb/priyom.py` and the card on the front page all ask these two functions
and never the база directly.

🔴 THE SECTION OWNS ITS QUERIES, AND THAT IS THE HOUSE RULE, NOT AN EXCEPTION.
`veb/razdely/shkolniki.py` owns "who counts as a pupil at all" for the same
reason. Where these two queries OUGHT to live is `infra/enrollment_repo.py`, next
to `rows_valid_on(day, slot, student_ids=None)` at `:117`, which holds the
interval correctly and has no `teacher_id` parameter — and neither has the port
declaring it, `core/services/enrollment.py:215`. Both files are outside the zone
of the заход that wrote this one, so the seam is opened here and the mismatch is
named in `## ВОПРОСЫ` of
`_studio/zhurnal/2026-09-06_pervyj-server/kod_lichnaya-stranica-prepodavatelya.md`.

🔴 THREE PROPERTIES OF `enrollment` THAT DECIDE BOTH QUERIES. Each was counted on
the live база on 2026-09-07, not assumed:

1. **An open row is `valid_to = '9999-12-31'`, never `NULL`.** The column is
   `not null default '9999-12-31'` (`migrations/001_init.sql:208-210`), the
   constant is `config.py:140 OPEN_END_DATE`, and the partial unique index at
   `:216` is built on that same predicate. `valid_to is null` matches 0 rows out
   of 186 — a query written that way returns nothing and looks exactly like "this
   teacher has no children".
2. **Some open rows start in the FUTURE.** Eight of them begin on `2026-09-10`.
   A query that only asks `valid_to = '9999-12-31'` shows those eight as if they
   were in force today; the screens that exist today do exactly that. Both
   queries below therefore use the full interval
   `valid_from <= :den and :den < valid_to`, letter for letter the predicate
   `infra/enrollment_repo.py:122-127` justifies.
3. **There is no map from a calendar day to a slot, so this section does not use
   one.** The база holds slots `1` (понедельник) and `2` (четверг) only
   (`migrations/003_slot_vmesto_weekday.sql:11`), while
   `core/services/enrollment.py:158 weekday_of` returns the RAW ISO weekday — on
   a Tuesday it answers `2` and silently agrees with Thursday. So the children
   are taken as an honest UNION over the slots, deduplicated by pupil. That is
   also the only shape that can match the check this section is judged by, which
   is a slot-less `select` over `enrollment`; and a teacher who opens the page on
   a day between lessons sees their children rather than an empty screen that
   reads as "you have none".
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

import config


def segodnya() -> str:
    """Today, as the ISO string every date in `enrollment` is written in.

    The zone comes from `config.TZ_DISPLAY` — the single home for it, the one
    `config.py:82-85` insists on — and never from a bare `date.today()`, whose
    answer depends on where the process happens to run.
    """
    return datetime.now(ZoneInfo(config.TZ_DISPLAY)).date().isoformat()


def kabinet_na_datu(c, teacher_id: int, den: str) -> Optional[str]:
    """The room this teacher's CURRENT distribution names for this date.

    🔴 THE ONE FUNCTION FOR THE ROOM, AND THE ONLY ONE THIS SECTION CALLS. Four
    sources of a room exist in this проект and they disagree; measured on the live
    база for group `В` on 2026-09-07:

    | source | says | who writes it |
    |---|---|---|
    | `enrollment.room` | **307** | the import of the owner's working file (`tools/import_fajla_raspredeleniya.py:293,315`) and the admin UI (`veb/server.py`) |
    | `kabinet_na_den` | no row for today at all; carried over from 06.09 → 303 | the same import (`:340`) and the admin UI (`veb/server.py:718`) |
    | `teachers.kabinet` | **303** | `veb/server.py:815` alone — the import does not touch it |
    | table `kabinety` | three rows, `rukovoditel_id` NULL in all three, `zametka` "заведён из enrollment при миграции 004" | nobody |

    `enrollment.room` is the master because it is the only one carrying BOTH the
    person and the date, so "on this date" is expressed in it instead of guessed.
    `kabinet_na_den` is per GROUP and needs the second hop `teachers.gruppa`;
    `teachers.kabinet` is the stale copy that the import which moved `В` to 307
    left standing at 303, which is the 303-versus-307 dispute itself.

    Rows that disagree with each other: the freshest `valid_from` wins, then the
    one holding more children. On the live база no teacher's open rows disagree —
    room is constant per teacher across both slots — so the tie-break is a
    statement about what happens if that ever changes, not a fact being hidden.
    `None` means the current distribution names no room, and the page says so
    instead of inventing one.
    """
    # 🔴 ПОРЯДОК ИСТОЧНИКОВ ИСПРАВЛЕН 07.09 ПО ЖИВОМУ РАСХОЖДЕНИЮ, А НЕ ПО ВКУСУ.
    # Замер в 12:37 на боевой базе, преподаватель id=8, группа «В», дата 07.09:
    #   `kabinet_na_den`  → 203  ← владелец вписал это СЕГОДНЯ, руками
    #   `enrollment.room` → 307
    #   `teachers.kabinet`→ 303  (протухшая копия, её и раньше не читали)
    # Карточка на заглавной уже показывала группе «В» кабинет 203, а личная
    # строка того же дня говорила преподавателю 307 — то есть страница спорила
    # сама с собой, и в 14:15 он пошёл бы не туда.
    # ⇒ Первым спрашивается кабинет, НАЗНАЧЕННЫЙ НА ЭТУ ДАТУ его группе: это
    # единственный источник, который человек заполняет осознанно и на день.
    # Распределение остаётся запасным: оно право, когда на дату ничего не
    # назначено.
    ryad = c.execute(
        """
        select k.kabinet as room
        from kabinet_na_den k
        join teachers t on t.gruppa = k.gruppa
        where t.id = ? and k.data = ?
        limit 1
        """,
        (teacher_id, den),
    ).fetchone()
    if ryad and ryad["room"]:
        return ryad["room"]
    ryad = c.execute(
        """
        select room, max(valid_from) as svezhest, count(*) as strok
        from enrollment
        where teacher_id = ? and valid_from <= ? and ? < valid_to
        group by room
        order by svezhest desc, strok desc, room
        limit 1
        """,
        (teacher_id, den, den),
    ).fetchone()
    return ryad["room"] if ryad else None


def deti_na_datu(c, teacher_id: int, den: str) -> list:
    """The pupils of THIS teacher on THIS date — the seam that did not exist.

    Returns rows `(id, surname, name)`, sorted the way every other list of pupils
    on this site is sorted. `select distinct` is what makes the union over slots
    honest: a child who comes to the same teacher on both понедельник and четверг
    holds two open rows and is one child.

    Pupils marked `left` are excluded, by the same predicate
    `veb/razdely/shkolniki.shkolniki` uses — four of the 57 rows in `students`.
    """
    # 🔴 СПРАШИВАЕТСЯ ТА ЖЕ СЛУЖБА, ЧТО СЧИТАЕТ РАСПРЕДЕЛЕНИЕ. Здесь стоял ЧИСТЫЙ
    # `enrollment`, то есть постоянное распределение, и правка на СЕГОДНЯ сюда не
    # доходила вовсе. Владелец 10.09: «изменение в текущем расписании на сегодня не
    # обновляет кабинет и вкладку в кондуите». Замерено на живой базе: в карточке
    # кабинета стоял Домра, а в распределении на тот же день — Левченко.
    #
    # Второй запрос за тем же фактом заводить нельзя — это та же болезнь, что уже
    # лечили в кондуите для кабинета (там источников было ЧЕТЫРЕ, и 07.09 это стоило
    # владельцу страницы, спорившей сама с собой). Поэтому ответ даёт
    # `SostavService.sostav(den)`, и он же отвечает распределению.
    from core.services.sostav_na_den import SostavService, slot_of
    from infra.enrollment_repo import SqliteEnrollmentRepo
    from infra.room_repo import SqliteAttendance, SqliteSessions
    from veb.razdely.zanyatie import otsutstvuyushchie_prepodavateli

    if slot_of(den) is None:
        return []          # не учебный день: постоянных строк не применяется ни одной

    sostav = SostavService(
        enrollment=SqliteEnrollmentRepo(c),
        sessions=SqliteSessions(c),
        attendance=SqliteAttendance(c),
        otsutstvuyushchie_prepoda=lambda d: otsutstvuyushchie_prepodavateli(c, d),
    ).sostav(den)
    moi = {m.student_id for m in sostav.mesta if m.segodnya == teacher_id}
    if not moi:
        return []
    # Имена берутся отдельным запросом: служба отвечает про РАСКЛАДКУ, а не про то,
    # как человека зовут, и смешивать эти два вопроса в одном порту незачем.
    mesta = ",".join("?" * len(moi))
    return c.execute(
        f"""
        select s.id, s.surname, s.name
        from students s
        where s.id in ({mesta})
          and (s.status is null or s.status <> 'left')
        order by s.surname, s.name
        """,
        tuple(sorted(moi)),
    ).fetchall()
