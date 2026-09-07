#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-code — rendered by `tools/sobrat_stranicu.sobrat_html`.
"""The teachers: who comes to each of them, and the controls for changing it.

The guest and the organiser get the SAME markup here and differ by exactly one
thing — the cross that detaches a pupil. The surname is always a `<span
class="tabl">`; for the organiser it is wrapped in a button. Keep it that way:
the moment the two roles are built out of different elements, comparing them
stops being possible and the frame gate goes blind.

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


def vybor_gruppy_prepoda(x, sl):
    """Группа преподавателя. Смена — правило, а не побочный эффект.

    Владелец 06.09: преподаватель уходит в другую группу — все его дети
    ОТКРЕПЛЯЮТСЯ и остаются в своих группах, преподаватель приходит в новую
    группу без детей. Само правило исполняет `/api/prepodavateli`, здесь
    только орган.
    """
    pusto = " selected disabled" if not x["gruppa"] else " disabled"
    opts = [f'<option value=""{pusto}>—</option>']
    for kod in ("В", "Д", "Н"):
        opts.append('<option value="%s"%s>%s</option>'
                    % (kod, " selected" if x["gruppa"] == kod else "", kod))
    return (f'<select class="org tgr-sel" data-org="pravit-raspredelenie"'
            f' data-gost="{e(x["gruppa"] or "")}"'
            f' data-tid="{x["id"]}" data-slot="{sl}">'
            + "".join(opts) + '</select>')


def deti_prepoda(kt, x, ego, sl):
    """Список школьников преподавателя. Крестик = ОТКРЕПИТЬ, и только в админке.

    Ребёнок остаётся в СВОЕЙ группе — поэтому крестик несёт группу самого
    преподавателя, а не пустоту: снятый без группы ребёнок провалился бы в
    «нигде», а его никто никуда не переводил.
    """
    if not ego:
        return '<span class="net">—</span>'
    # \U0001f534 ОДНА И ТА ЖЕ РАЗМЕТКА В ОБОИХ РЕЖИМАХ, И РАЗЛИЧАЕТ ИХ РОВНО
    # ОРГАН ПРАВКИ. Фамилия — всегда `<span class="det">`; у организатора она
    # ЗАВЁРНУТА в кнопку с крестиком, и это единственная разница. Запятые в
    # таблице преподавателей рисует CSS, а не строка — иначе гостевой вариант
    # был бы одним текстовым узлом, админский двадцатью элементами, и «сверить
    # блок списка из гостевой и из админской» стало бы сравнением несравнимого.
    # ТАБЛЕТКИ, А НЕ СТРОКИ, И МЕЛКИМ ШРИФТОМ — приём из рабочего файла
    # распределения владельца. С пятью школьниками обычная строка не влезает
    # и переносится, оставляя дыру; уменьшенная фамилия влезает всегда.
    # Крестик занимает НОЛЬ ширины, пока на таблетку не навели мышь, — поэтому
    # у гостя и у организатора список одинаковой ширины, а не «почти такой же».
    if not ego:
        return '<span class="net">—</span>'
    kuski = []
    for r in ego:
        atr, krest = "", ""
        if kt.ADMIN:
            atr = (f' role="button" tabindex="0"'
                   f' data-snyat="{r["id"]}" data-slot="{sl}"'
                   f' data-gruppa="{e(x["gruppa"] or "")}"')
            krest = ('<span class="x" data-org="pravit-raspredelenie"'
                     ' title="открепить">\u00d7</span>')
        kuski.append(f'<span class="tabl"{atr}>{e(r["surname"])}{krest}</span>')
    return "".join(kuski)


def para_prep(kt, x, kl, pokazat_gruppu=True):
    """Строка «преподаватель → его школьники».

    🔴 ТОЛЬКО ФАМИЛИИ школьников: с именами строка не влезает (замечание
    владельца 04.09). Группа и кабинет на вкладке ГРУППЫ не печатаются — там
    и так все из одной группы и одного кабинета, это шум.
    """
    kab = kt.kabinety_dnya[kl]
    sl = kt.DNI[kl][1]
    ego = sorted((r for r in kt.shk_dnya[kl] if r["teacher_id"] == x["id"]),
                 key=lambda r: r["surname"])
    redko = ""
    metki = ""
    if pokazat_gruppu:
        if x["gruppa"]:
            metki += f' <span class="gr">{e(x["gruppa"])}</span>'
        if x["gruppa"] and kab.get(x["gruppa"]) and not kt.ADMIN:
            metki += '<span data-tolko-gost> ' + kt.kab_html(kl, x["gruppa"]) + "</span>"
    if kt.mozhno("videt-schyot"):
        metki += '<span class="sch%s" data-org="videt-schyot"> %d</span>' % (
            "" if 3 <= len(ego) <= 4 else " ploho", len(ego))
    deti_html = deti_prepoda(kt, x, ego, sl)
    return (f'<div class="para" data-i="{e(x["name"].lower())}">'
            f'<span class="kto"><b>{e(x["name"])}</b>{redko}{metki}</span>'
            f'<span class="komu deti">{deti_html}</span></div>')


def vid_prepodavateli(kt, kl):
    """Вкладка преподавателей ТАБЛИЦЕЙ: колонки обязаны стоять ровно.

    Порядок владельца: преподаватель · школьники · группа · кабинет —
    кабинет самое неважное и уходит вправо.
    """
    kab = kt.kabinety_dnya[kl]
    sl = kt.DNI[kl][1]
    ryady = []
    for x in sorted(kt.prep.values(), key=lambda z: z["name"]):
        ego = sorted((r for r in kt.shk_dnya[kl] if r["teacher_id"] == x["id"]),
                     key=lambda r: r["surname"])
        deti = deti_prepoda(kt, x, ego, sl)
        k = kab.get(x["gruppa"])
        # 🔴 СЧЁТЧИК — ТОЛЬКО В АДМИНКЕ. Норма 3–4; красным 0, 1, 2 и 5+.
        # Гостю нагрузка преподавателя не нужна и является техническим числом
        # (ТЗ §2.5), а тому, кто раскладывает людей, она и есть главный сигнал.
        schet = ('<td class="tsch%s" data-org="videt-schyot">%d</td>'
                 % ("" if 3 <= len(ego) <= 4 else " ploho", len(ego))) \
                if kt.mozhno("videt-schyot") else ""
        gr = vybor_gruppy_prepoda(x, sl) if kt.ADMIN else e(x["gruppa"] or "")
        # 🔴 ОБА ДНЯ ВИДНЫ СРАЗУ, У КАЖДОГО ПРЕПОДАВАТЕЛЯ. Владелец 06.09:
        # «„понедельник-четверг“ как текст не нужен, а кнопки нужны… рядом с
        # каждым преподавателем». Общий переключатель дня отвечает на вопрос
        # «что сегодня»; здесь нужен другой — «ходит ли он в этот день вообще».
        #
        # 🔴 ЭТО ПОКА ОТМЕТКА, А НЕ ВЫКЛЮЧАТЕЛЬ, И ВЫГЛЯДИТ ОНА ОТМЕТКОЙ.
        # Признака «преподаватель работает по понедельникам» в базе нет: есть
        # только его школьники по слотам, и отметка честно показывает именно
        # их — закрашена, если в этот день у него кто-то есть. Нарисовать
        # нажимаемую кнопку без своего поля в схеме значило бы поставить
        # выключатель, который ничего не выключает. Это предмет захода про
        # слой занятия, и там же появится настоящее «работает в этот день».
        dni_metki = "".join(
            '<span class="den-metka%s" title="%s">%s</span>' % (
                "" if any(r["teacher_id"] == x["id"] for r in kt.shk_dnya[k]) else " pusto",
                e(kt.DNI[k][0]), e(kt.DNI[k][3]))
            for k in kt.DNI)
        ryady.append(
            f'<tr data-i="{e(x["name"].lower())}" data-tid="{x["id"]}">'
            f'<td class="tp"><b>{e(x["name"])}</b></td>'
            f'<td class="td-deti">{deti}</td>'
            + f'<td class="tdni">{dni_metki}</td>'
            + schet
            + f'<td class="tg">{gr}</td>'
            + (f'<td class="tk"><span data-tolko-gost>{kt.kab_html(kl, x["gruppa"])}'
               f'</span></td>' if k and not kt.ADMIN else '<td class="tk"></td>')
            + '</tr>')
    return '<table class="prep-tab"><tbody>' + "".join(ryady) + '</tbody></table>'
