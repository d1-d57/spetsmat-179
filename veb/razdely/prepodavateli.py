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


def prihodit(kt, x, kl) -> bool:
    """Приходит ли принимающий в этот день — по строкам закрепления, а не по флагу.

    🔴 ПРИЗНАКА «РАБОТАЕТ ПО ПОНЕДЕЛЬНИКАМ» В СХЕМЕ НЕТ, И ЗАВОДИТЬ ЕГО ЗДЕСЬ НЕЛЬЗЯ.
    По дням разделён ровно `enrollment.slot`; `teachers.gruppa` — одна колонка на
    оба дня (её и не создаёт ни одна миграция — схема сервера ушла вперёд руками).
    Поэтому «он в этот день принимает» здесь значит ровно то, что можно измерить:
    в этот слот у него есть хотя бы один школьник. Прочерк в поле — та же мера с
    другой стороны, и потому она не врёт: пустой день и есть день без детей.
    """
    return any(r["teacher_id"] == x["id"] for r in kt.shk_dnya[kl])


def vybor_gruppy_prepoda(kt, x, kl, gostevoj_tekst):
    """Группа принимающего В ЭТОТ ДЕНЬ: В · Д · Н · —. Смена — правило, а не
    побочный эффект.

    Владелец 06.09: преподаватель уходит в другую группу — все его дети
    ОТКРЕПЛЯЮТСЯ и остаются в своих группах, преподаватель приходит в новую
    группу без детей. Само правило исполняет `/api/prepodavateli`, здесь
    только орган.

    🔴 ДВА ПОЛЯ, ПО ОДНОМУ НА ДЕНЬ, И ОНИ НЕ РАВНОПРАВНЫ — РЕШЕНИЕ ВЛАДЕЛЬЦА 6 ОТ
    07.09: «понедельник и четверг, значения В · Д · Н · —, где прочерк значит „в
    этот день не приходит“… это и есть способ сказать, что человека в один из
    дней не будет». Что из этих двух значений куда ложится, решает схема, а не
    экран: ГРУППА хранится одной колонкой на человека, поэтому её выбор меняет
    обоих дней сразу; ПРОЧЕРК ложится в `enrollment` того слота, где дни и
    разделены, — его строки этого дня закрываются, и дети становятся видны как
    нераспределённые на странице занятия, то есть работа «его в четверг не
    будет» превращается в работу «этих раздать», а не теряется.

    Чего этот орган НЕ умеет и не притворяется: развести ГРУППЫ по дням (В в
    понедельник, Д в четверг). Для этого нужна колонка, которой нет, а
    `migrations/` лежит вне зоны этого захода — названо в `## ПЛАН`, а не
    подделано.
    """
    sl = kt.DNI[kl][1]
    est = prihodit(kt, x, kl)
    tek = x["gruppa"] if est else ""
    opts = ['<option value=""%s>—</option>' % (" selected" if not tek else "")]
    for kod in ("В", "Д", "Н"):
        opts.append('<option value="%s"%s>%s</option>'
                    % (kod, " selected" if tek == kod else "", kod))
    return (f'<select class="org tgr-sel" data-org="pravit-raspredelenie"'
            f' data-gost="{e(gostevoj_tekst)}"'
            f' data-tid="{x["id"]}" data-slot="{sl}">'
            + "".join(opts) + '</select>')


def gruppa_dnya(kt, x, kl) -> str:
    """Что стоит в поле дня у гостя: буква группы или прочерк."""
    return (x["gruppa"] or "—") if prihodit(kt, x, kl) else "—"


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


def ego_deti(kt, x, kl):
    return sorted((r for r in kt.shk_dnya[kl] if r["teacher_id"] == x["id"]),
                  key=lambda r: r["surname"])


def para_prep(kt, x, pokazat_gruppu=True):
    """Строка «преподаватель → его школьники», ОБА ДНЯ РЯДОМ.

    🔴 ТОЛЬКО ФАМИЛИИ школьников: с именами строка не влезает (замечание
    владельца 04.09). Группа и кабинет на вкладке ГРУППЫ не печатаются — там
    и так все из одной группы и одного кабинета, это шум.
    """
    metki = ""
    if pokazat_gruppu and x["gruppa"]:
        metki += f' <span class="gr">{e(x["gruppa"])}</span>'
    yacheyki = []
    for kl in kt.DNI:
        ego = ego_deti(kt, x, kl)
        sl = kt.DNI[kl][1]
        hvost = ""
        if pokazat_gruppu and x["gruppa"] and kt.kabinety_dnya[kl].get(x["gruppa"]) \
                and not kt.ADMIN:
            hvost = ('<span data-tolko-gost> '
                     + kt.kab_html(kl, x["gruppa"]) + "</span>")
        schyot = ""
        if kt.mozhno("videt-schyot"):
            schyot = ('<span class="sch%s" data-org="videt-schyot"> %d</span>'
                      % ("" if 3 <= len(ego) <= 4 else " ploho", len(ego)))
        yacheyki.append(f'<span class="dv dv-{kl}">'
                        + deti_prepoda(kt, x, ego, sl) + schyot + hvost + "</span>")
    return (f'<div class="para" data-i="{e(x["name"].lower())}">'
            f'<span class="kto"><b>{e(x["name"])}</b>{metki}</span>'
            f'<span class="komu deti">{"".join(yacheyki)}</span></div>')


def vid_prepodavateli(kt):
    """Вкладка преподавателей ТАБЛИЦЕЙ: колонки обязаны стоять ровно.

    Порядок владельца: преподаватель · школьники · группа · кабинет —
    кабинет самое неважное и уходит вправо. Дней теперь два, и каждый несёт
    СВОИХ школьников и СВОЁ поле группы: одна таблица на оба дня, решение
    владельца 5 от 07.09.
    """
    ryady = ['<tr class="prep-shapka"><td class="tp"></td>'
             + "".join(f'<td class="td-deti">{e(kt.DNI[k][3])}</td>' for k in kt.DNI)
             + "".join(f'<td class="tg">{e(kt.DNI[k][3])}</td>' for k in kt.DNI)
             + '<td class="tk"></td></tr>']
    for x in sorted(kt.prep.values(), key=lambda z: z["name"]):
        deti_yach, gruppy_yach = [], []
        for kl in kt.DNI:
            ego = ego_deti(kt, x, kl)
            sl = kt.DNI[kl][1]
            # 🔴 СЧЁТЧИК — ТОЛЬКО В АДМИНКЕ. Норма 3–4; красным 0, 1, 2 и 5+.
            # Гостю нагрузка преподавателя не нужна и является техническим числом
            # (ТЗ §2.5), а тому, кто раскладывает людей, она и есть главный сигнал.
            schyot = ('<span class="tsch%s" data-org="videt-schyot"> %d</span>'
                      % ("" if 3 <= len(ego) <= 4 else " ploho", len(ego))) \
                     if kt.mozhno("videt-schyot") else ""
            deti_yach.append(f'<td class="td-deti dv-{kl}">'
                             + deti_prepoda(kt, x, ego, sl) + schyot + "</td>")
            gostevoe = gruppa_dnya(kt, x, kl)
            gruppy_yach.append(
                f'<td class="tg dv-{kl}">'
                + (vybor_gruppy_prepoda(kt, x, kl, gostevoe) if kt.ADMIN
                   else e(gostevoe))
                + "</td>")
        k = kt.kabinety_dnya[next(iter(kt.DNI))].get(x["gruppa"])
        ryady.append(
            f'<tr data-i="{e(x["name"].lower())}" data-tid="{x["id"]}">'
            f'<td class="tp"><b>{e(x["name"])}</b></td>'
            + "".join(deti_yach)
            + "".join(gruppy_yach)
            + (f'<td class="tk"><span data-tolko-gost>'
               f'{kt.kab_html(next(iter(kt.DNI)), x["gruppa"])}'
               f'</span></td>' if k and not kt.ADMIN else '<td class="tk"></td>')
            + '</tr>')
    return '<table class="prep-tab"><tbody>' + "".join(ryady) + '</tbody></table>'
