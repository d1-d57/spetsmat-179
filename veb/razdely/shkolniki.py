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


def vybor_gruppy(r, sl, tek):
    """Выпадающий список группы. «нигде» — это ВЫБОР, а не пустота."""
    opts = ['<option value=""%s>нигде</option>' % (" selected" if not tek else "")]
    for kod in ("В", "Д", "Н"):
        opts.append('<option value="%s"%s>%s</option>'
                    % (kod, " selected" if tek == kod else "", kod))
    return (f'<select class="org gr-sel" data-org="pravit-raspredelenie"'
            f' data-sid="{r["id"]}" data-slot="{sl}">'
            + "".join(opts) + '</select>')


def para_shk(kt, r, kl, pokazat_kab=True):
    """Строка «школьник → его преподаватель».

    Гостю — имя преподавателя и кабинет текстом. Организатору — В ТОМ ЖЕ
    МЕСТЕ два выпадающих списка: преподаватель и группа. Буква класса
    (К · И · Л) стоит только у организатора: ребёнку она не нужна, а тому,
    кто раскладывает людей по группам, нужна. Буквы группы у гостя нет —
    решение владельца 06.09: она дублирует кабинет и добавляет шум.
    """
    kab = kt.kabinety_dnya[kl]
    sl = kt.DNI[kl][1]
    t_ = kt.prep.get(r["teacher_id"])
    g = gr_shk(kt, r)
    klass = (f'<span class="kl" data-org="videt-klass"> {e(r["class"])}</span>'
             if kt.mozhno("videt-klass") and r["class"] else "")
    # 🔴 КАБИНЕТ — ГОСТЮ, НЕ АДМИНУ. Решение владельца 06.09: «на странице,
    # которую видят все, кабинет должен быть виден; на странице только для
    # администраторов номер кабинета не нужен». Тот, кто раскладывает людей,
    # смотрит на людей; кабинет он правит в шапке группы, и только там.
    imya_prepoda = e(t_["name"]) if t_ else "—"
    if kt.ADMIN:
        hvost = (vybor_prepoda(kt, r, sl, imya_prepoda) + vybor_gruppy(r, sl, g))
    else:
        hvost = imya_prepoda
        if pokazat_kab and g and kab.get(g):
            hvost += '<span data-tolko-gost> ' + kt.kab_html(kl, g) + "</span>"
    return (f'<div class="para" data-i="{e((r["surname"] + " " + r["name"]).lower())}">'
            f'<span class="kto"><b>{e(r["surname"])}</b> {e(r["name"])}{klass}</span>'
            f'<span class="komu">{hvost}</span></div>')


def vid_vse(kt, kl):
    """Вкладка «школьникам»: ДВА столбца, каждому — его преподаватель.

    🔴 ДВА, А НЕ ТРИ, И ЭТО НЕ ВКУСОВЩИНА. Столько же, сколько в публичной
    версии, — потому что базовая вёрстка у гостя и у организатора обязана
    совпадать. Владелец 06.09, дословно: «если в разделе учеников для версии
    для читателей две колонки — то для версии для администраторов должно быть
    то же самое: те же самые две колонки». Три столбца тут стояли ровно один
    заход и были ошибкой исполнителя.

    Читается ПО СТОЛБЦАМ: фамилии идут сверху вниз внутри столбца, поэтому
    человека находишь по букве, а не просматривая каждую строку.
    """
    deti = kt.shk_dnya[kl]
    pol = (len(deti) + 1) // 2
    return ('<div class="dva">'
            f'<div class="kol">{"".join(para_shk(kt, r, kl) for r in deti[:pol])}</div>'
            f'<div class="kol">{"".join(para_shk(kt, r, kl) for r in deti[pol:])}</div></div>')
