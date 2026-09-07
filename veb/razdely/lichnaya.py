#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-code — rendered by `veb.obshchee.karkas.obolochka`
# whenever the role being served has the capability `videt-svoyo`.
"""The personal page: what one named person sees about themselves.

Two questions, and nothing else on it: WHERE AM I TODAY and WHO IS COMING TO ME
TODAY. A teacher who has entered by their personal password must get both answers
without reading the whole distribution — that is the clause this section exists to
close, and it is why the two queries below take a `teacher_id` and a DATE rather
than filtering a screenful of everybody in memory the way `veb/server.py:718`,
`:764` and the pupil tabs do.

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
from veb.obshchee.karkas import e


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
    return c.execute(
        """
        select distinct s.id, s.surname, s.name
        from enrollment e
        join students s on s.id = e.student_id
        where e.teacher_id = ?
          and e.valid_from <= ? and ? < e.valid_to
          and (s.status is null or s.status <> 'left')
        order by s.surname, s.name
        """,
        (teacher_id, den, den),
    ).fetchall()


def _imya_prepoda(kt, teacher_id: int) -> Optional[str]:
    """The name to put in the heading, asked of the база when the context is silent.

    `kt.prep` holds the ACTIVE teachers only. Somebody deactivated between minting
    a password and using it would otherwise get a page with an empty heading, so
    the база is asked directly before giving up.
    """
    svoj = kt.prep.get(teacher_id)
    if svoj:
        return svoj["name"]
    ryad = kt.c.execute(
        "select name from teachers where id = ?", (teacher_id,)).fetchone()
    return ryad["name"] if ryad else None


def _stolbcy(deti) -> str:
    """The names in two columns, read down each column — as on the pupils tab."""
    pol = (len(deti) + 1) // 2
    def para(r):
        return (f'<div class="para"><span class="kto">'
                f'<b>{e(r["surname"])}</b> {e(r["name"])}</span></div>')
    return ('<div class="dva">'
            f'<div class="kol">{"".join(para(r) for r in deti[:pol])}</div>'
            f'<div class="kol">{"".join(para(r) for r in deti[pol:])}</div></div>')


def razdel(kt) -> str:
    """The personal section, ready to hang in the shell.

    🔴 `data-org="videt-svoyo"` ON THE SECTION IS LOAD-BEARING, NOT DECORATION.
    This element sits inside the window the frame gate compares — from
    `id="s-rasp"` to the first `\\n<script>` — and `_snyat_organy` in
    `tools/sobrat_stranicu.py` removes it by that attribute before comparing what
    is left with the guest page. Take the attribute off and the gate reports the
    personal page as a frame that has drifted; leave the section unmarked outside
    a capability check and it appears on the public page.

    Nothing personal is shown when the entry could not say WHO came in: the two
    common passwords belong to nobody in particular (`veb/vhod.py::proverit_parol`
    answers `uid = None` for them), and a page that guessed at that point would be
    showing one teacher another teacher's children.
    """
    den = segodnya()
    zag = f'<p class="zag2">{e(kt.po_russki(den))}</p>'

    if kt.prepod_id is None:
        telo = ('<h1>Личная страница</h1>'
                '<p class="net">Вход по общему паролю: система не знает, кто именно '
                'вошёл. Свой кабинет и своих школьников показывает личный пароль.</p>')
        return (f'<section class="str holst" id="s-lich" data-org="videt-svoyo">'
                f'{zag}{telo}</section>')

    imya = _imya_prepoda(kt, kt.prepod_id)
    if imya is None:
        telo = ('<h1>Личная страница</h1>'
                '<p class="net">Такого преподавателя нет в базе.</p>')
        return (f'<section class="str holst" id="s-lich" data-org="videt-svoyo">'
                f'{zag}{telo}</section>')

    kab = kabinet_na_datu(kt.c, kt.prepod_id, den)
    deti = deti_na_datu(kt.c, kt.prepod_id, den)
    # Кабинет — ОДИН и на эту дату. Чип тот же, что и везде на сайте; пусто —
    # честное «не назначен», а не выдуманный номер (то же правило, что в
    # `Kontekst.kab_html`, только источник здесь личный, а не групповой).
    kab_html = (f'<span class="kab">{e(kab)}</span>' if kab
                else '<span class="net">кабинет не назначен</span>')
    deti_html = (_stolbcy(deti) if deti
                 else '<p class="net">на этот день школьников нет</p>')
    return (f'<section class="str holst" id="s-lich" data-org="videt-svoyo">'
            f'{zag}'
            f'<h1>{e(imya)}</h1>'
            f'<p class="data">кабинет {kab_html}</p>'
            f'{deti_html}</section>')
