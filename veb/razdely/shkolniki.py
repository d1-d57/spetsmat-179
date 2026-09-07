#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-code — rendered by `tools/sobrat_stranicu.sobrat_html`.
"""The pupils: who each of them goes to, and the controls for changing it.

This section owns the query that decides who counts as a pupil at all, and
the two dropdowns the organiser edits a pupil with. The guest sees a name and
a room in exactly the places the organiser sees those dropdowns — that is what
`data-gost` on the `<select>` is for, and `proverit_karkas()` in
`tools/sobrat_stranicu.py` fails the build if the two ever drift apart.

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


def shkolniki(c, slot):
    return c.execute("""
        select s.id, s.surname, s.name, s.class, e.teacher_id
        from students s
        left join enrollment e
          on e.student_id = s.id and e.valid_to = '9999-12-31' and e.slot = ?
        where s.status is null or s.status <> 'left'
        order by s.surname, s.name
    """, (slot,)).fetchall()


def gr_shk(kt, r, pr=None):
    pr = pr or kt.prep
    t_ = pr.get(r["teacher_id"])
    return t_["gruppa"] if t_ else None


def kab_shk(kt, r):
    return kt.kabinety.get(gr_shk(kt, r))


def vybor_prepoda(kt, r, sl, gostevoj_tekst):
    """Выпадающий список преподавателей — там же, где у гостя стоит его имя.

    🔴 `data-gost` НЕСЁТ ТО, ЧТО СТОЯЛО БЫ ЗДЕСЬ У ГОСТЯ. По нему гейт
    `proverit_karkas()` восстанавливает гостевой вид из админского и сверяет
    побайтово. Без этого атрибута «список вместо имени» был бы для машины
    просто расхождением, и проверку пришлось бы делать глазами — то есть
    не делать вовсе.
    """
    # Свои первыми: девять правок из десяти — внутри группы, и чужие не должны
    # попадаться раньше своих (находка из рабочего файла распределения).
    svoi, chuzhie = [], []
    moya = gr_shk(kt, r)
    for x in sorted(kt.prep.values(), key=lambda z: z["name"]):
        (svoi if x.get("gruppa") == moya else chuzhie).append(x)
    opts = ['<option value=""%s>— нет —</option>'
            % (" selected" if not r["teacher_id"] else "")]
    def opt(x):
        vybran = " selected" if x["id"] == r["teacher_id"] else ""
        return f'<option value="{x["id"]}"{vybran}>{e(x["name"])}</option>'
    if svoi:
        opts.append(f'<optgroup label="группа {e(moya or "—")}">'
                    + "".join(opt(x) for x in svoi) + "</optgroup>")
    po_gruppam = {}
    for x in chuzhie:
        po_gruppam.setdefault(x.get("gruppa") or "—", []).append(x)
    for kod in ("В", "Д", "Н"):
        if kod in po_gruppam:
            opts.append(f'<optgroup label="группа {kod}">'
                        + "".join(opt(x) for x in po_gruppam[kod]) + "</optgroup>")
    if "—" in po_gruppam:
        opts.append('<optgroup label="без группы">'
                    + "".join(opt(x) for x in po_gruppam["—"]) + "</optgroup>")
    return (f'<select class="org pr-sel" data-org="pravit-raspredelenie"'
            f' data-gost="{e(gostevoj_tekst)}" data-sid="{r["id"]}" data-slot="{sl}">'
            + "".join(opts) + '</select>')


def vybor_gruppy(r, tek):
    """Выпадающий список группы. «нигде» — это ВЫБОР, а не пустота.

    🔴 ОДИН НА ШКОЛЬНИКА, А НЕ ПО ОДНОМУ НА ДЕНЬ, И ЭТО СВОЙСТВО СХЕМЫ, А НЕ ВКУСА.
    Группа снятого школьника лежит в `students.gruppa` — ОДНОЙ колонке, у которой
    дня нет. Два поля показывали бы одно и то же значение, а запись во второе
    молча затирала бы первое; по дням разделён `enrollment`, то есть
    ПРЕПОДАВАТЕЛЬ, и ровно он и стоит на строке дважды.
    """
    opts = ['<option value=""%s>нигде</option>' % (" selected" if not tek else "")]
    for kod in ("В", "Д", "Н"):
        opts.append('<option value="%s"%s>%s</option>'
                    % (kod, " selected" if tek == kod else "", kod))
    return (f'<select class="org gr-sel" data-org="pravit-raspredelenie"'
            f' data-sid="{r["id"]}">'
            + "".join(opts) + '</select>')


def po_dnyam(kt, otbor=None):
    """Школьники ОДНИМ списком, у каждого — его строка в каждый из дней.

    🔴 ОДНА ТАБЛИЦА НА ОБА ДНЯ — РЕШЕНИЕ ВЛАДЕЛЬЦА 5 ОТ 07.09, дословно: «я бы делал
    одну табличку на оба дня… по умолчанию оба значения одинаковые». До этого дни
    были ДВУМЯ разметками одного и того же, между которыми переключала радиокнопка:
    чтобы увидеть, что у ребёнка понедельник и четверг разошлись, надо было помнить
    первый экран, стоя на втором. Теперь оба дня стоят рядом в одной строке, и
    расхождение видно, а не вспоминается.

    Ключ склейки — `students.id`: `shkolniki()` спрашивает один и тот же список
    школьников на каждый слот и отличается только присоединённым `teacher_id`,
    поэтому склейка по id полная и порядок сохраняется.

    `otbor` — предикат по (kt, ryady): им групповая вкладка оставляет своих.
    """
    poryadok = kt.shk_dnya[next(iter(kt.DNI))]
    po_id = {kl: {r["id"]: r for r in kt.shk_dnya[kl]} for kl in kt.DNI}
    vse = []
    for osnova in poryadok:
        ryady = {kl: po_id[kl].get(osnova["id"], osnova) for kl in kt.DNI}
        if otbor is None or otbor(ryady):
            vse.append(ryady)
    return vse


def gruppa_lyuboj_den(kt, ryady):
    """Группа школьника: по тому дню, где он у кого-то есть.

    Дни могут разойтись — тогда группой считается понедельничная, а четверговая
    показана на своей половине строки. Пустая у обоих — школьник «нигде».
    """
    for kl in kt.DNI:
        g = gr_shk(kt, ryady[kl])
        if g:
            return g
    return None


def para_shk(kt, ryady, pokazat_kab=True):
    """Строка «школьник → его преподаватель В КАЖДЫЙ ИЗ ДВУХ ДНЕЙ».

    Гостю — имена преподавателей и кабинет текстом. Организатору — В ТЕХ ЖЕ
    МЕСТАХ выпадающие списки: по одному на день, плюс группа, которая у школьника
    одна. Буква класса (К · И · Л) стоит только у организатора: ребёнку она не
    нужна, а тому, кто раскладывает людей по группам, нужна. Буквы группы у гостя
    нет — решение владельца 06.09: она дублирует кабинет и добавляет шум.

    🔴 ДВА ПОЛЯ СТОЯТ ВСЕГДА, ДАЖЕ КОГДА ОНИ РАВНЫ, и это не многословие. «По
    умолчанию оба значения одинаковые» — слова владельца о ДАННЫХ, а не о
    разметке: на живой базе 53 школьника из 53 сегодня имеют один и тот же
    ответ на оба дня. Схлопнуть равные значения в одно поле значило бы прятать
    ровно тот орган, которым день и разводят.
    """
    osnova = ryady[next(iter(kt.DNI))]
    klass = (f'<span class="kl" data-org="videt-klass"> {e(osnova["class"])}</span>'
             if kt.mozhno("videt-klass") and osnova["class"] else "")
    # 🔴 КАБИНЕТ — ГОСТЮ, НЕ АДМИНУ. Решение владельца 06.09: «на странице,
    # которую видят все, кабинет должен быть виден; на странице только для
    # администраторов номер кабинета не нужен». Тот, кто раскладывает людей,
    # смотрит на людей; кабинет он правит в шапке группы, и только там.
    yacheyki = []
    for kl in kt.DNI:
        r = ryady[kl]
        sl = kt.DNI[kl][1]
        t_ = kt.prep.get(r["teacher_id"])
        g = gr_shk(kt, r)
        imya_prepoda = e(t_["name"]) if t_ else "—"
        if kt.ADMIN:
            telo = vybor_prepoda(kt, r, sl, imya_prepoda)
        else:
            telo = imya_prepoda
            if pokazat_kab and g and kt.kabinety_dnya[kl].get(g):
                telo += '<span data-tolko-gost> ' + kt.kab_html(kl, g) + "</span>"
        yacheyki.append(f'<span class="dv dv-{kl}">{telo}</span>')
    hvost = "".join(yacheyki)
    if kt.ADMIN:
        hvost += vybor_gruppy(osnova, gruppa_lyuboj_den(kt, ryady))
    return (f'<div class="para" data-i="{e((osnova["surname"] + " " + osnova["name"]).lower())}">'
            f'<span class="kto"><b>{e(osnova["surname"])}</b> {e(osnova["name"])}{klass}</span>'
            f'<span class="komu">{hvost}</span></div>')


def shapka_dnej(kt):
    """Подписи столбцов: какой день где. Не переключатель — заголовок.

    Решение владельца 4 и 5 от 07.09: день недели перестал быть переключателем.
    Два столбца без подписи — две одинаковые фамилии подряд и никакого способа
    узнать, который из них четверг.
    """
    metki = "".join(f'<span class="dv dv-{kl}">{e(kt.DNI[kl][3])}</span>'
                    for kl in kt.DNI)
    # 🔴 ПУСТАЯ ЯЧЕЙКА ПОД ПОЛЕ ГРУППЫ — ИНАЧЕ ШАПКА СТОИТ НЕ НАД СВОИМИ
    # СТОЛБЦАМИ. У организатора в строке есть третий орган, группа; без такой же
    # пустой ячейки в шапке подписи съезжают на его ширину, и «ПН» повисает над
    # четверговым полем (замер верификатора: подпись 325–493 px, поля 245–459).
    # Ячейка несёт `data-org`, поэтому у гостя её нет — как нет у него и самого
    # поля группы, и каркасы остаются равными побайтово.
    if kt.ADMIN:
        metki += ('<span class="dv dv-gr" data-org="pravit-raspredelenie">'
                  "</span>")
    return ('<div class="para shapka-dnej"><span class="kto"></span>'
            f'<span class="komu">{metki}</span></div>')


def vid_vse(kt):
    """Вкладка «школьникам»: ДВА столбца, каждому — его преподаватели на оба дня.

    🔴 ДВА, А НЕ ТРИ, И ЭТО НЕ ВКУСОВЩИНА. Столько же, сколько в публичной
    версии, — потому что базовая вёрстка у гостя и у организатора обязана
    совпадать. Владелец 06.09, дословно: «если в разделе учеников для версии
    для читателей две колонки — то для версии для администраторов должно быть
    то же самое: те же самые две колонки». Три столбца тут стояли ровно один
    заход и были ошибкой исполнителя.

    Читается ПО СТОЛБЦАМ: фамилии идут сверху вниз внутри столбца, поэтому
    человека находишь по букве, а не просматривая каждую строку.
    """
    deti = po_dnyam(kt)
    pol = (len(deti) + 1) // 2
    shapka = shapka_dnej(kt)
    return ('<div class="dva">'
            f'<div class="kol">{shapka}{"".join(para_shk(kt, r) for r in deti[:pol])}</div>'
            f'<div class="kol">{shapka}{"".join(para_shk(kt, r) for r in deti[pol:])}</div></div>')
