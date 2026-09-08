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
    """Приходит ли принимающий в этот день — СПРОШЕНО У ПАМЯТИ, а не выведено.

    Раньше здесь стояло «есть ли у него в этот день хоть один школьник», и это
    отвечало на другой вопрос: человек, которому детей ещё не дали, выглядел
    отсутствующим, а отметить его присутствие было нечем. Память дня —
    `prepodavatel_ne_prihodit` (`infra/prepodavatel_den_repo`), она и отвечает.
    """
    return kt.DNI[kl][1] in kt.dni_prepodavatelej.get(x["id"], frozenset())


def galochka_dnya(kt, x, kl):
    """Галочка «в этот день прихожу». Владелец 07.09 назвал её именно так.

    🔴 ГАЛОЧКА — ПРО ПРИСУТСТВИЕ, А ГРУППА — ОТДЕЛЬНОЕ ПОЛЕ, И РАЗДЕЛЕНИЕ ЭТО НЕ
    ОФОРМИТЕЛЬСКОЕ. Прошлая редакция ставила в каждый день выбор `В · Д · Н · —`,
    то есть разрешала записать разные группы в разные дни; владелец сказал, что
    такого не бывает: *«он ходит только в одну группу, за которой он фиксирован,
    но либо один, либо два дня»*. Орган, которым можно записать невозможное,
    однажды его и запишет.

    🔴 У ГОСТЯ ЗДЕСЬ СВОЙ ЭЛЕМЕНТ, А НЕ ЭТОТ ЖЕ БЕЗ ПРАВКИ. Гейт `proverit_karkas`
    снимает `data-org` с админской стороны и `data-tolko-gost` — с гостевой, и
    сверяет ОСТАТКИ. Поэтому пара органов «чекбокс организатору / метка гостю»
    законна и проверяема, а один общий элемент с атрибутом-надстройкой — нет.
    """
    sl = kt.DNI[kl][1]
    est = prihodit(kt, x, kl)
    return ('<label class="den-gal%s" data-org="pravit-raspredelenie"'
            ' title="%s — %s">'
            '<input class="org den-chk" type="checkbox" data-tid="%s" data-slot="%d"%s>'
            "<span>%s</span></label>"
            % ("" if est else " pusto", e(kt.DNI[kl][0]),
               "приходит" if est else "не приходит",
               x["id"], sl, " checked" if est else "",
               e(kt.DNI[kl][3])))


def metka_dnya(kt, x, kl):
    """То же самое гостю: закрашена — приходит, бледная — нет. Читать, не править."""
    est = prihodit(kt, x, kl)
    return ('<span class="den-metka%s" data-tolko-gost title="%s">%s</span>'
            % ("" if est else " pusto", e(kt.DNI[kl][0]), e(kt.DNI[kl][3])))


def vybor_gruppy_prepoda(x, gostevoj_tekst):
    """Группа принимающего — ОДНА на человека, без дня. Смена — правило, а не
    побочный эффект.

    Владелец 06.09: преподаватель уходит в другую группу — все его дети
    ОТКРЕПЛЯЮТСЯ и остаются в своих группах, преподаватель приходит в новую
    группу без детей. Само правило исполняет `/api/prepodavateli`, здесь
    только орган.
    """
    pusto = " selected disabled" if not x["gruppa"] else " disabled"
    opts = ['<option value=""%s>—</option>' % pusto]
    for kod in ("В", "Д", "Н"):
        opts.append('<option value="%s"%s>%s</option>'
                    % (kod, " selected" if x["gruppa"] == kod else "", kod))
    return (f'<select class="org tgr-sel" data-org="pravit-raspredelenie"'
            f' data-gost="{e(gostevoj_tekst)}" data-tid="{x["id"]}">'
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
    """Его школьники в этот день — БЕЗ отмеченных отсутствующими.

    Владелец 07.09: *«он выпадает из моего списка, списка моей аудитории. Всё, я
    про него больше не думаю»*. Заодно это чинит счётчик: преподаватель, у
    которого двое из четырёх сегодня не пришли, ведёт двоих, и норма 3–4 должна
    считаться по тем, кто здесь.
    """
    from veb.razdely.shkolniki import prishol
    return sorted((r for r in kt.shk_dnya[kl]
                   if r["teacher_id"] == x["id"] and prishol(r)),
                  key=lambda r: r["surname"])


def para_prep(kt, x, pokazat_gruppu=True):
    """Карточка принимающего в группе: имя строкой, под ним день за днём.

    🔴 ДНИ ИДУТ СТРОКАМИ, А НЕ ОДНИМ РЯДОМ, И ЭТО ПОПРАВКА ВЛАДЕЛЬЦА 07.09: *«у
    тебя такие широкие строки — на первой строке имя преподавателя, ниже, в этой
    же большой по вертикали строке, список в понедельник, ещё ниже список в
    четверг»*. Слитый ряд читался как один список из семи фамилий, в котором
    четверо повторяются, — а это два списка по трое, и они разные.

    На занятии день один, и подпись ему не нужна: она стоит в шапке страницы.

    🔴 ТОЛЬКО ФАМИЛИИ школьников: с именами строка не влезает (замечание
    владельца 04.09). Группа и кабинет на вкладке ГРУППЫ не печатаются — там
    и так все из одной группы и одного кабинета, это шум.
    """
    metki = ""
    if pokazat_gruppu and x["gruppa"]:
        metki += f' <span class="gr">{e(x["gruppa"])}</span>'
    stroki = []
    for kl in kt.DNI:
        ego = ego_deti(kt, x, kl)
        sl = kt.DNI[kl][1]
        hvost = ""
        if pokazat_gruppu and x["gruppa"] and kt.kabinety_dnya[kl].get(x["gruppa"]) \
                and not kt.ADMIN:
            # 🔴 ПЛАШКА — СВОЙ ФЛЕКС-РЕБЁНОК В `.den-ryad`, А НЕ ХВОСТ ВНУТРИ
            # `.deti-ryad` (ПРАВКА 1). Список детей переносится по словам
            # (`flex-wrap:wrap`); плашка, приклеенная последним элементом ВНУТРИ
            # этого переноса, вставала там, где список случайно кончился в этой
            # конкретной строке, — не колонкой. Вынесена СОСЕДОМ `.deti-ryad`, с
            # `flex:0 0 auto;margin-left:auto` (как у `.sch`, которая ту же задачу
            # уже решает для счётчика) — правило в `veb/obshchee/karkas.py`.
            hvost = ('<span class="kab-mesto" data-tolko-gost>'
                     + kt.kab_html(kl, x["gruppa"]) + "</span>")
        schyot = ""
        if kt.mozhno("videt-schyot"):
            schyot = ('<span class="sch%s" data-org="videt-schyot">%d</span>'
                      % ("" if 3 <= len(ego) <= 4 else " ploho", len(ego)))
        podpis = ("" if kt.den
                  else f'<span class="den-podpis">{e(kt.DNI[kl][3])}</span>')
        stroki.append(f'<span class="den-ryad dv-{kl}">{podpis}'
                      '<span class="deti-ryad">'
                      + deti_prepoda(kt, x, ego, sl) + "</span>"
                      + hvost + schyot + "</span>")
    return (f'<div class="para" data-i="{e(x["name"].lower())}">'
            f'<span class="kto"><b>{e(x["name"])}</b>{metki}</span>'
            f'<span class="komu deti">{"".join(stroki)}</span></div>')


def otsutstvie_prepoda(kt, x):
    """«Отсутствует» — то же слово и тот же смысл, что у школьника.

    🔴 ОДИН СТАТУС НА ОБОИХ, И ЭТО ПОПРАВКА ВЛАДЕЛЬЦА 07.09: *«у преподавателя или
    у школьника должна быть возможность установить статус „отсутствует“. И всё»*.
    Две разные кнопки с разными словами заставляли бы читателя гадать, одно ли это
    состояние; оно одно.

    🔴 ДВЕ РАЗНЫЕ ВЕЩИ, КОТОРЫЕ ЛЕГКО СПУТАТЬ, И ОНИ ЖИВУТ В РАЗНЫХ МЕСТАХ.
    «Он вообще не ходит по четвергам» — постоянное, галочка дня
    (`prepodavatel_ne_prihodit`). «Его сегодня нет» — одно занятие,
    `teacher_attendance`, и ставится оно в том числе ВПЕРЁД: *«мы знаем, что
    школьник или преподаватель будет отсутствовать в течение месяца… тогда мы это
    можем проставить даже вперёд»*.
    """
    net = x["id"] in kt.otsutstvuyut_prepoda
    return ('<label class="otsut%s" data-org="pravit-raspredelenie" title="%s">'
            '<input class="org totsut-chk" type="checkbox" data-tid="%s"'
            ' data-den="%s"%s><span>отсутствует</span></label>'
            % ("" if net else " pusto",
               "сегодня его нет" if net else "отметить, что его сегодня нет",
               x["id"], e(kt.den), " checked" if net else ""))


def vidimye_prepodavateli(kt):
    """Кого показывать в этом экране.

    На постоянном — всех активных. На занятии — только тех, кто в этот день
    вообще ходит: владелец 07.09, *«в постоянном распределении мы зафиксируем,
    что этот преподаватель вообще не ходит по четвергам, и тогда мы его не будем
    видеть в текущем распределении на четверг»*.
    """
    vse = sorted(kt.prep.values(), key=lambda z: z["name"])
    if not kt.den:
        return vse
    slot = kt.DNI[next(iter(kt.DNI))][1]
    return [x for x in vse
            if slot in kt.dni_prepodavatelej.get(x["id"], {slot})]


def vid_prepodavateli(kt):
    """Вкладка преподавателей ТАБЛИЦЕЙ: колонки обязаны стоять ровно.

    Порядок владельца: преподаватель · школьники · дни · группа · кабинет —
    кабинет самое неважное и уходит вправо. На постоянном школьники показаны по
    каждому дню отдельно, дни отмечены галочками, группа одна. На занятии столбец
    один, а вместо галочек дней — отметка «сегодня его нет».
    """
    # 🔴 НА ЗАНЯТИИ ШАПКИ НЕТ ВОВСЕ. Владелец 07.09: *«верхняя строка над словом
    # „Александр Тертерян“ на вкладке „принимающие“ — ненужная информация… надо
    # убирать лишнюю информацию, это очень важно, потому что информации много»*.
    # Подписывать один столбец днём, который написан в шапке страницы, — это
    # третье повторение одного и того же на одном экране.
    ryady = []
    if not kt.den:
        ryady.append(
            '<tr class="prep-shapka"><td class="tp"></td>'
            + "".join(f'<td class="td-deti">{e(kt.DNI[k][3])}</td>'
                      # `data-org` обязателен: у гостя счётчиков нет вовсе, и гейт
                      # каркаса снимает эту ячейку вместе с остальными органами.
                      + ('<td class="tsch" data-org="videt-schyot"></td>'
                         if kt.mozhno("videt-schyot") else "")
                      for k in kt.DNI)
            + '<td class="tdni">приходит</td><td class="tg">группа</td>'
            + '<td class="tk"></td></tr>')
    for x in vidimye_prepodavateli(kt):
        deti_yach = []
        for kl in kt.DNI:
            ego = ego_deti(kt, x, kl)
            sl = kt.DNI[kl][1]
            # 🔴 СЧЁТЧИК — ТОЛЬКО В АДМИНКЕ. Норма 3–4; красным 0, 1, 2 и 5+.
            # Гостю нагрузка преподавателя не нужна и является техническим числом
            # (ТЗ §2.5), а тому, кто раскладывает людей, она и есть главный сигнал.
            # 🔴 ЧИСЛО — СВОЯ ЯЧЕЙКА, А НЕ ХВОСТ СПИСКА. Владелец 07.09: «цифры
            # выставлены не там, где нужно… всё должно быть в своих столбцах».
            # Внутри ячейки с фамилиями число начинается там, где кончились
            # фамилии, то есть в каждой строке в новом месте.
            schyot = ('<td class="tsch%s" data-org="videt-schyot">%d</td>'
                      % ("" if 3 <= len(ego) <= 4 else " ploho", len(ego))) \
                     if kt.mozhno("videt-schyot") else ""
            deti_yach.append(f'<td class="td-deti dv-{kl}">'
                             + deti_prepoda(kt, x, ego, sl) + "</td>" + schyot)
        if kt.den:
            otmetka = otsutstvie_prepoda(kt, x) if kt.ADMIN else (
                '<span class="den-metka%s" data-tolko-gost>нет</span>'
                % ("" if x["id"] in kt.otsutstvuyut_prepoda else " pusto"))
        else:
            otmetka = "".join(
                (galochka_dnya(kt, x, kl) if kt.ADMIN else metka_dnya(kt, x, kl))
                for kl in kt.DNI)
        gostevoe = x["gruppa"] or "—"
        gruppa_yach = (vybor_gruppy_prepoda(x, gostevoe) if kt.ADMIN and not kt.den
                       else e(gostevoe))
        k = kt.kabinety_dnya[next(iter(kt.DNI))].get(x["gruppa"])
        ryady.append(
            f'<tr data-i="{e(x["name"].lower())}" data-tid="{x["id"]}">'
            f'<td class="tp"><b>{e(x["name"])}</b></td>'
            + "".join(deti_yach)
            + f'<td class="tdni">{otmetka}</td>'
            + f'<td class="tg">{gruppa_yach}</td>'
            + (f'<td class="tk"><span data-tolko-gost>'
               f'{kt.kab_html(next(iter(kt.DNI)), x["gruppa"])}'
               f'</span></td>' if k and not kt.ADMIN else '<td class="tk"></td>')
            + '</tr>')
    return '<table class="prep-tab"><tbody>' + "".join(ryady) + '</tbody></table>'
