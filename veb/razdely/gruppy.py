#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-code — rendered by `tools/sobrat_stranicu.sobrat_html`.
"""One group: its pupils on the left, its teachers on the right, numbers below.

This is the only section that composes two others — it lays out the pupils of
the group next to the teachers of the group. It therefore imports them, and
the arrow points one way only: pupils and teachers know nothing about groups.

It is handed `kt: Kontekst` and reads it; it opens no database and
imports no shell. What that buys is the point of the whole cut: this
file can be edited while somebody else edits the file next to it.

🔴 THE RUSSIAN COMMENTS BELOW ARE NOT TRANSLATED, ON PURPOSE. They carry the
owner's own words with the dates he said them on — "Владелец 06.09: …" — and a
translation would be a rewrite of evidence. Everything newly written here is in
English, as the задание requires; everything moved is verbatim, down to the
byte. That is also what makes the byte criterion of this refactor meaningful:
a diff between the page before and the page after can only show a mistake,
never a paraphrase.
"""
from __future__ import annotations

from veb.obshchee.karkas import e
from veb.razdely.prepodavateli import para_prep
from veb.razdely.shkolniki import gr_shk, para_shk


def vkladka_gruppy(kt, kod, kl):
    """Группа: слева школьники, справа преподаватели, служебное — ВНИЗУ.

    🔴 ШАПКИ НАВЕРХУ БОЛЬШЕ НЕТ, И ЭТО РЕШЕНИЕ ВЛАДЕЛЬЦА 06.09. Там стояли
    имя старшего и числа «преподавателей 6 · школьников 20» — и то и другое
    он назвал лишним в самом заметном месте экрана: «и так понятно, кто
    руководитель… надо вынести». Верхняя строка отдана тому, ради чего сюда
    пришли, — спискам.

    Служебное переехало ПОД список преподавателей, в свою рамку: числа, а у
    организатора ещё и поля кабинета на оба дня. Оно нужно, но не первым.
    """
    star = kt.gruppy[kod]
    kab = kt.kabinety_dnya[kl].get(kod)
    deti = [r for r in kt.shk_dnya[kl] if gr_shk(kt, r) == kod]
    svoi = sorted((x for x in kt.prep.values() if x["gruppa"] == kod),
                  key=lambda x: x["name"])
    sl = kt.DNI[kl][1]

    if kt.mozhno("pravit-kabinety"):
        # 🔴 КАБИНЕТЫ — ДВУМЯ ПОЛЯМИ, ПОНЕДЕЛЬНИК И ЧЕТВЕРГ, НА ОДНОМ ЭКРАНЕ.
        # Владелец: «у каждой аудитории должно быть два поля — понедельник и
        # четверг». Правят их вместе, накануне вечером; перещёлкивать день
        # ради второго поля — лишний ход. Это ЕДИНСТВЕННОЕ место, где кабинет
        # вводится: в списках распределения у организатора его нет вовсе.
        polya = "".join(
            f'<label class="kab-pole">{e(kt.DNI[k][3])}'
            f'<input class="org kab-inp" data-gruppa="{e(kod)}"'
            f' data-data="{e(kt.DNI[k][2])}"'
            f' value="{e(kt.kabinety_dnya[k].get(kod) or "")}"'
            f' size="5" placeholder="—"></label>'
            for k in kt.DNI)
        # 🔴 БЕЗ «СТАРШИЙ ИМЯРЕК». Владелец 06.09: «там всё равно не нужно
        # писать „Старший Ваня Яковлев“ — просто: преподавателей 6,
        # школьников 20, кабинет: пн 303, чт 307». Кто старший, видно по
        # самой вкладке; повторять это здесь нечем.
        nizhnyaya = ('<div class="gruppa-niz" data-org="pravit-kabinety">'
                     f'<span class="gruppa-cifry">принимающих <b>{len(svoi)}</b>'
                     f' · школьников <b>{len(deti)}</b></span>'
                     f'<span class="kab-polya">кабинет {polya}</span></div>')
    else:
        # 🔴 У ГОСТЯ НИЖНЕЙ ПАНЕЛИ НЕТ ВОВСЕ. Кабинет уже стоит наверху, в
        # строке вкладок, и повторять его внизу значит писать одно дважды —
        # ровно то, от чего избавляемся по всему сайту.
        nizhnyaya = ""

    return ('<div class="dva">'
            + f'<div class="kol">{"".join(para_shk(kt, r, kl, pokazat_kab=False) for r in deti)}</div>'
            + '<div class="kol kol-pr"><div class="prep-ramka">'
            + "".join(para_prep(kt, x, kl, pokazat_gruppu=False) for x in svoi)
            + "</div>" + nizhnyaya + "</div>"
            + "</div>")
