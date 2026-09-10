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
from veb.razdely.verstka_stili import STILI

# 🔴 A THIRD LAYER OF RULES, AND FOR THE SAME REASON THE SECOND ONE EXISTS.
# `veb/obshchee/karkas.py` (the canon) and `veb/razdely/verstka_stili.py` (the
# 09.09 corrections) are BOTH outside this заход's zone — the zone is the four
# section files and `tests/enrollment/`. A `<style>` inside `<body>` is valid
# HTML5 and applies exactly like one in `<head>`; `verstka_stili` is emitted from
# `vid_vse()` for the same reason and this block rides directly behind it, so it
# wins ties on cascade order without inventing higher specificity.
#
# Every selector below targets a class that already exists, except `.ob-kol`,
# which this заход introduces and therefore has to dress itself.
STILI_KOLONKI = """
<style>
/* ── §1 «обычно у» — СВОЯ КОЛОНКА ПЕРЕД ИМЕНЕМ ПРИНИМАЮЩЕГО, А НЕ ХВОСТ ФАМИЛИИ.
   Владелец 10.09 дословно: «мы ничего не дописываем просто в конец». Колонка
   стоит ВСЕГДА, пока экран однодневный, даже когда значка в строке нет: иначе
   имена принимающих съезжают по вертикали ровно на ширину значка — ради чего
   колонку и заводят. Ширина фиксирована и одна на все строки. */
.ob-kol{flex:0 0 1.35rem;min-width:0;text-align:center;font-size:.85em;
  line-height:1;align-self:center}
/* 🔴 `cursor:help` УБРАН, И ЭТО НЕ ВКУСОВЩИНА: он И ЕСТЬ «вопросительный знак»
   из жалобы G2.3 («наведение даёт вопросительный знак, а нажатие — ничего»).
   Курсор-вопрос читается как «нажми и узнаешь», а нажимать здесь нечего —
   подсказка приходит сама. Обычная стрелка ничего не обещает. */
.obychno{margin-left:0;cursor:default;flex:0 0 auto}
</style>
"""


def shkolniki(c, slot):
    return c.execute("""
        select s.id, s.surname, s.name, s.class, e.teacher_id
        from students s
        left join enrollment e
          on e.student_id = s.id and e.valid_to = '9999-12-31' and e.slot = ?
        where s.status is null or s.status <> 'left'
        order by s.surname, s.name
    """, (slot,)).fetchall()


def pole(r, imya, po_umolchaniyu=None):
    """Поле строки, которого может не быть вовсе.

    🔴 СТРОКИ ЗДЕСЬ ДВУХ ПОРОД, И ЭТО НЕ НЕРЯШЛИВОСТЬ, А УСТРОЙСТВО. Постоянное
    распределение отдаёт `sqlite3.Row` прямо из запроса; занятие — словарь,
    собранный из состава дня, и у него есть поля, которых в первой породе нет
    (`net`, `obychno`, `gruppa_dnya`). `Row` не знает метода `get` и на
    незнакомом ключе бросает `IndexError` — одна такая строка уронила сборку
    ВСЕЙ страницы на первом же прогоне. Спрашивать надо здесь, одним способом.
    """
    try:
        znachenie = r[imya]
    except (KeyError, IndexError):
        return po_umolchaniyu
    return po_umolchaniyu if znachenie is None else znachenie


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
    # 🔴 `data-den` ОТЛИЧАЕТ ПРАВКУ НА ОДИН РАЗ ОТ ПРАВКИ НАВСЕГДА, И ЭТО ЕДИНСТВЕННОЕ,
    # ЧЕМ ОНИ ОТЛИЧАЮТСЯ НА ЭКРАНЕ. Есть дата — правка едет в слой занятия и
    # сохраняется СРАЗУ (владелец 07.09: *«распределение на день не нужно писать
    # кнопку „Сохранить“… там просто нужно сразу сохраняться»*). Нет даты — это
    # постоянное распределение, и правка копится до большой кнопки, *«потому что там
    # можно долго его двигать и в итоге прийти к оптимальному варианту»*.
    den = f' data-den="{e(kt.den)}"' if kt.den else ""
    return (f'<select class="org pr-sel" data-org="pravit-raspredelenie"'
            f' data-gost="{e(gostevoj_tekst)}" data-sid="{r["id"]}" data-slot="{sl}"{den}>'
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


def _initsialy(kt, teacher_id):
    """Кто он, коротко: «ИЯ» с полным именем в подсказке.

    Форма не выдумана здесь: рабочая таблица владельца показывала преподавателей
    инициалами, и он сказал, что это ровно то, что работает.
    """
    x = kt.prep.get(teacher_id)
    if x is None:
        return ("?", "преподаватель %s" % teacher_id)
    polnoe = x["name"] or ""
    return ("".join(part[0] for part in polnoe.split()[:2]) or "?", polnoe)


def _zhenskaya(imya: str, familia: str) -> bool:
    """Женское ли это «Имя Фамилия» — СПРОШЕНО У ФАМИЛИИ ПЕРВОЙ, И ЭТО ВАЖНО.

    Судить по имени нельзя: «Ваня», «Вася», «Даня», «Саша», «Миша» кончаются на
    «-я»/«-а» ровно как женские, а в этой самой школе трое из них — мужчины.
    Фамилия отвечает надёжнее: «-ова/-ева/-ина/-ая» женская, «-ов/-ев/-ин/-ский»
    мужская. Имя спрашивают только тогда, когда фамилия молчит («Амбург»,
    «Маршалл», «Шнитке») — там оно единственный свидетель.
    """
    for konec in ("ова", "ева", "ёва", "ина", "ына", "ская", "цкая", "ая", "яя"):
        if familia.endswith(konec):
            return True
    for konec in ("ов", "ев", "ёв", "ин", "ын", "ский", "цкий", "ый", "ий"):
        if familia.endswith(konec):
            return False
    return imya.endswith(("а", "я"))


def _imya_rod(slovo: str) -> str:
    """Имя в родительном падеже: «Наталья» → «Натальи»."""
    if slovo.endswith("я"):
        return slovo[:-1] + "и"
    if slovo.endswith("а"):
        # Шипящие и заднеязычные не терпят «ы» после себя (правило «жи-ши»):
        # «Ольга» → «Ольги», но «Дима» → «Димы».
        return slovo[:-1] + ("и" if slovo[-2:-1] in "кгхжчшщ" else "ы")
    if slovo.endswith("й"):
        return slovo[:-1] + "я"
    if slovo.endswith("ь"):
        return slovo[:-1] + "я"
    if slovo[-1:].lower() in "оеиуыэю":
        return slovo
    return slovo + "а"


def _familia_rod(slovo: str, zhenskaya: bool) -> str:
    """Фамилия в родительном падеже. Несклоняемая — возвращается как есть."""
    if zhenskaya:
        for konec, zamena in (("ова", "овой"), ("ева", "евой"), ("ёва", "ёвой"),
                              ("ина", "иной"), ("ына", "ыной"),
                              ("ская", "ской"), ("цкая", "цкой"),
                              ("яя", "ей")):
            if slovo.endswith(konec):
                return slovo[:-len(konec)] + zamena
        if slovo.endswith("ая"):
            # «Рыжая» → «Рыжей», но «Толстая» → «Толстой»: после шипящих и «ц»
            # безударное окончание пишется через «е». Правило то же, что делает
            # «Ольги» из «Ольга» в `_imya_rod`, только другой стороной.
            return slovo[:-2] + ("ей" if slovo[-3:-2] in "жшчщц" else "ой")
        # 🔴 ЖЕНСКАЯ ФАМИЛИЯ НА СОГЛАСНЫЙ НЕ СКЛОНЯЕТСЯ ВОВСЕ — это и есть пример
        # владельца: «Наталья Амбург» → «Натальи Амбург», а не «Амбурга».
        return slovo
    for konec in ("ов", "ев", "ёв", "ин", "ын"):
        if slovo.endswith(konec):
            return slovo + "а"
    for konec, zamena in (("ский", "ского"), ("цкий", "цкого"),
                          ("ый", "ого"), ("ий", "его")):
        if slovo.endswith(konec):
            return slovo[:-len(konec)] + zamena
    if slovo.endswith(("а", "я")):
        return _imya_rod(slovo)
    if slovo[-1:].lower() in "оеиуыэю":
        return slovo
    return slovo + "а"


def v_roditelnom(polnoe: str) -> str:
    """«Наталья Амбург» → «Натальи Амбург»: подсказка значка «обычно у ‹кого›».

    🔴 ПАДЕЖ НАЗВАН ВЛАДЕЛЬЦЕМ, А НЕ ВЫБРАН ЗДЕСЬ (G2.3, дословно: «обычно у
    Натальи Амбург», а не инициалы и не вопросительный знак). Именительный после
    предлога «у» — не сокращение, а ошибка, и читается она как машинный текст;
    ради одного этого предлога тут и стоит склонение.

    Осторожность одна и записана: склоняется только запись, КАЖДОЕ слово которой
    начинается с заглавной и не набрано заглавными целиком. Служебные записи
    живой базы — «НС», «отсутствует» — не имена, и склонять их значило бы
    печатать «НСа». Длина словом НЕ проверяется: «Ян» и «Ия» — имена.
    """
    slova = polnoe.split()
    if not slova or len(slova) > 2:
        return polnoe
    if not all(s[:1].isupper() and s != s.upper() for s in slova):
        return polnoe
    if len(slova) == 1:
        return _imya_rod(slova[0])
    imya, familia = slova
    zh = _zhenskaya(imya, familia)
    return f"{_imya_rod(imya)} {_familia_rod(familia, zh)}"


def svyazka_dnej(kt, ryady):
    """Замок: связаны поля понедельника и четверга или разведены.

    🔴 ЗАМОК ЗАЖАТ ПО УМОЛЧАНИЮ, И ЭТО ПРЯМОЕ УКАЗАНИЕ ВЛАДЕЛЬЦА 07.09: *«должны
    быть зажаты тумблеры — можно нарисовать замочек. Если замочек зажатый, то
    одновременно меняешь двух преподавателей слева и справа. Изначально они
    зажаты»*. Прежняя редакция ставила галочку «дни разные», то есть отмеченным
    было ИСКЛЮЧЕНИЕ, а не правило, и владелец прочитал её ровно наоборот: *«когда
    галочка нажата — не работает»*.

    🔴 СОСТОЯНИЕ НЕ ХРАНИТСЯ, А ЧИТАЕТСЯ ИЗ САМИХ ДАННЫХ. «Связаны» здесь значит
    ровно «в оба дня стоит один и тот же человек» — это видно в базе, и отдельный
    флажок мог бы с ней разойтись: у школьника разные дни, а флажок говорит
    «связано», и следующая правка молча затрёт один из них.
    """
    znacheniya = {ryady[kl]["teacher_id"] for kl in kt.DNI}
    svyazany = len(znacheniya) == 1
    return ('<label class="zamok%s" data-org="pravit-raspredelenie" title="%s">'
            '<input class="org svyaz-chk" type="checkbox"%s>'
            '<span aria-hidden="true">%s</span></label>'
            % ("" if svyazany else " otkryt",
               "дни связаны: правка одного меняет оба" if svyazany
               else "дни разведены: поля правятся по отдельности",
               " checked" if svyazany else "",
               "\U0001f512" if svyazany else "\U0001f513"))


def otsutstvie(kt, r):
    """«Отсутствует» — один статус на школьника и на принимающего, и одно слово.

    🔴 СЛОВО ИМЕННО ЭТО, И ЭТО ПОПРАВКА ВЛАДЕЛЬЦА 07.09 К ПРЕДЫДУЩЕЙ РЕДАКЦИИ:
    *«болеет — неправильная кнопка… у преподавателя или у школьника должна быть
    возможность установить статус „отсутствует“. И всё»*. «Болеет» — догадка о
    причине, а на занятии причина неизвестна: *«я не понимаю, он заболел или нет»*.
    Экран обязан уметь работать при неполной информации, а не требовать диагноз.

    🔴 ОТМЕЧЕННЫЙ ВЫПАДАЕТ, А НЕ СЕРЕЕТ. *«Он, например, выпадает из моего списка,
    списка моей аудитории. Всё, я про него больше не думаю»*. Поэтому его нет ни в
    карточке преподавателя, ни на вкладке группы; остаётся он ровно в одном месте —
    в общем списке школьников, где стоит его же галочка, иначе снять её было бы
    нечем.
    """
    otmechen = bool(pole(r, "net"))
    # 🔴 КНОПКА, А НЕ ГАЛОЧКА, И ЭТО ТРЕБОВАНИЕ ВЛАДЕЛЬЦА 07.09: *«там не нужна
    # галочка, нужна просто кнопка, на которую можно нажать. Квадратик не нужен.
    # Чем больше таких элементов, тем сложнее и хуже выглядит»*. На экране их
    # пятьдесят четыре — по одной на школьника, — и квадратик рядом с каждым
    # словом даёт сто восемь предметов вместо пятидесяти четырёх.
    #
    # Сам `input` остаётся: он и есть состояние, и он же делает кнопку доступной
    # с клавиатуры. Видимым его делать нечем — за него говорит сама кнопка.
    return ('<label class="otsut%s" data-org="pravit-raspredelenie" title="%s">'
            '<input class="org otsut-chk" type="checkbox" data-sid="%s"'
            ' data-den="%s"%s><span>отсутствует</span></label>'
            % ("" if otmechen else " pusto",
               "сегодня его нет" if otmechen else "отметить, что его сегодня нет",
               r["id"], e(kt.den), " checked" if otmechen else ""))


def prishol(r) -> bool:
    """Он сегодня здесь? Пустое поле `net` — обычный ответ «да»."""
    return not pole(r, "net")


def para_shk(kt, ryady, pokazat_kab=True):
    """Строка «школьник → его преподаватель»: на каждый день по полю.

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

    🔴 НА ЭКРАНЕ ЗАНЯТИЯ ПОЛЕ ОДНО — потому что `kt.DNI` там из одного дня, — и
    рядом появляются две вещи, которых у постоянного нет и быть не может:
    отметка «болеет» и подпись «обычно у ‹кого›» у того, кого сегодня отдали
    другому. Ни одной ветки «если это занятие» в разметке ниже нет: она вся в
    том, что дней один, а не два.
    """
    osnova = ryady[next(iter(kt.DNI))]
    # 🔴 КЛАСС — ОТДЕЛЬНАЯ КОЛОНКА, А НЕ ХВОСТ ИМЕНИ (владелец 09.09, п.5: «класс
    # «9Л/9К» приклеен хвостом после имени вместо отдельной колонки»). Был span
    # ВНУТРИ `.kto`, склеенный с фамилией без видимой границы; теперь отдельный
    # флекс-ребёнок `.para` между `.kto` и `.komu`, тем же `data-org`, поэтому
    # гейт `proverit_karkas` (вне зоны, сравнивает admin-минус-org с гостем)
    # видит ту же картину: у гостя колонки нет вовсе, у админа — есть.
    klass = (f'<span class="kl-kol" data-org="videt-klass">{e(osnova["class"])}</span>'
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
        # 🔴 ИМЯ И КАБИНЕТ — ДВА РАЗНЫХ ФЛЕКС-РЕБЁНКА, А НЕ ОДНА СТРОКА ТЕКСТА
        # (ПРАВКА 1). Прежде плашка кабинета была приклеена к имени преподавателя
        # внутри одной ячейки `.dv`, и на длинных именах («Елена Мирошниченко»,
        # «Александр Тертерян») выдавливалась за границу колонки — колонка держала
        # фиксированную ширину, а её СОДЕРЖИМОЕ не было разбито на усекаемое имя и
        # несжимаемую плашку. `.prep-imya` получает `text-overflow:ellipsis`,
        # `.kab-mesto` — `flex:0 0 auto`; правило — `veb/obshchee/karkas.py`,
        # `.para .komu .dv`.
        # 🔴 ОБЁРТКА ОДИНАКОВА В ОБЕИХ ВЕТКАХ, И ЭТО НЕ КОСМЕТИКА. `proverit_karkas()`
        # (`tools/sobrat_stranicu.py`, вне зоны этого захода) подставляет вместо
        # `<select data-gost="…">` голый текст `data-gost` — БЕЗ обёртки. Обернуть
        # `.prep-imya` только в гостевой ветке значило бы, что после сверки у гостя
        # появляется span, которого нет у роли «organizator», — гейт каркаса краснеет
        # на этом же расхождении (найдено первым прогоном теста, не рассуждением).
        if kt.ADMIN:
            telo = f'<span class="prep-imya">{vybor_prepoda(kt, r, sl, imya_prepoda)}</span>'
        else:
            telo = f'<span class="prep-imya">{imya_prepoda}</span>'
            if pokazat_kab and g and kt.kabinety_dnya[kl].get(g):
                telo += ('<span class="kab-mesto" data-tolko-gost>'
                         + kt.kab_html(kl, g) + "</span>")
        yacheyki.append(f'<span class="dv dv-{kl}">{telo}</span>')
    hvost = "".join(yacheyki)
    if kt.ADMIN and not kt.den:
        hvost += svyazka_dnej(kt, ryady) + vybor_gruppy(osnova, gruppa_lyuboj_den(kt, ryady))
    elif kt.ADMIN:
        # 🔴 ТРИ СТУПЕНИ НУЖНЫ ИМЕННО НА ЗАНЯТИИ, А НЕ ТОЛЬКО В ШАБЛОНЕ. Владелец
        # 07.09: *«ко мне пришёл новый ребёнок… он пока не распределённый, но он уже
        # в моей аудитории, я должен это видеть»*. «В группе, но ни к кому не
        # закреплён» — рабочее состояние середины занятия, и без него такого
        # ребёнка некуда деть, кроме как приписать наугад.
        hvost += vybor_gruppy_dnya(kt, osnova)
    if kt.den and kt.ADMIN:
        hvost += otsutstvie(kt, osnova)

    # «Обычно у ‹кого›» — только там, где сегодня НЕ как обычно (ТЗ §3.3).
    #
    # 🔴 ОТДЕЛЬНАЯ КОЛОНКА ПЕРЕД ИМЕНЕМ ПРИНИМАЮЩЕГО, А НЕ ХВОСТ ФАМИЛИИ
    # (владелец 10.09, G2.1–G2.2: «мы ничего не дописываем просто в конец»;
    # порядок в строке — фамилия школьника · КОЛОНКА ЗНАЧКА · принимающий ·
    # кабинет). Прошлая редакция дописывала значок ВНУТРЬ `.kto`, и он ехал
    # вместе с концом фамилии: у «Цуканова» в одном месте, у
    # «Тухватулина-Йалчына» — в другом.
    #
    # 🔴 ЯЧЕЙКА ПУСТАЯ, НО ЕСТЬ. Без неё колонка появлялась бы только в тех
    # строках, где значок есть, и сдвигала бы имя принимающего вправо ровно в
    # них — то самое «имена разъедутся по вертикали», ради которого владелец и
    # просил колонку. Ставится она только на ОДНОДНЕВНОМ экране: поля `obychno`
    # в постоянном слое нет вовсе, и пустая колонка на всю страницу была бы
    # шириной, отнятой у имён ни за чем.
    #
    # 🔴 ПОДСКАЗКА — ПОЛНОЕ ИМЯ В РОДИТЕЛЬНОМ ПАДЕЖЕ (G2.3), не инициалы:
    # «обычно у Натальи Амбург». Клик не делает ничего и не должен — курсор
    # `help` (тот самый «вопросительный знак при наведении») снят в
    # `STILI_KOLONKI` выше.
    obychno = ""
    if kt.den:
        znachok = ""
        if pole(osnova, "obychno") and osnova["obychno"] != osnova["teacher_id"]:
            _, polnoe = _initsialy(kt, osnova["obychno"])
            znachok = ('<span class="obychno" title="обычно у %s">\U0001f501</span>'
                       % e(v_roditelnom(polnoe)))
        obychno = f'<span class="ob-kol">{znachok}</span>'

    klassy = "para"
    if kt.den and pole(osnova, "net"):
        # Серым — только здесь, в общем списке: это единственное место, где
        # отсутствующий вообще показан, и показан он ради своей же галочки.
        klassy += " net"
    elif kt.den and not osnova["teacher_id"]:
        klassy += " krasn"               # единственное красное на этом экране
    # 🔴 `data-shk-id` НА САМОЙ СТРОКЕ, ОДИНАКОВО У ОБЕИХ РОЛЕЙ. Поиск с главной
    # находит школьника по фамилии, но фамилий бывает несколько — только id
    # называет ровно ОДНУ строку, и подсветка с адреса `?sid=` бьёт по нему.
    # Атрибут стоит вне `data-org`/`data-gost`, поэтому он ОДИНАКОВ у гостя и
    # у организатора и не портит побайтовое сравнение `proverit_karkas()`.
    # 🔴 НЕ `data-sid` — ИМЯ ЗАНЯТО. `data-sid` уже стоит в `ATRIBUTY_ORGANA`
    # (`tools/sobrat_stranicu.py`, вне зоны этого захода) как атрибут-надстройка
    # организатора на СОВСЕМ ДРУГИХ элементах (выпадающий список преподавателя,
    # чекбокс отсутствия) и снимается `_snyat_organy()` при сверке ролей. Взять
    # то же имя здесь значило бы, что сверка молча стирает его и у гостя, и у
    # преподавателя по-разному — что и произошло (`proverit_karkas` разошёлся
    # на позиции 7611, найдено прогоном, не рассуждением).
    return (f'<div class="{klassy}" data-i="{e((osnova["surname"] + " " + osnova["name"]).lower())}"'
            f' data-shk-id="{osnova["id"]}">'
            f'<span class="kto"><b>{e(osnova["surname"])}</b> {e(osnova["name"])}'
            f'</span>'
            f'{klass}{obychno}'
            f'<span class="komu">{hvost}</span></div>')


def shapka_dnej(kt):
    """Подписи столбцов: какой день где. Не переключатель — заголовок.

    Решение владельца 4 и 5 от 07.09: день недели перестал быть переключателем.
    Два столбца без подписи — две одинаковые фамилии подряд и никакого способа
    узнать, который из них четверг.
    """
    # Один столбец не нуждается в подписи «какой это день»: она уже стоит в шапке
    # страницы, датой и словом. Подписывают, когда столбцов два и их можно спутать.
    if kt.den:
        return ""
    metki = "".join(f'<span class="dv dv-{kl}">{e(kt.DNI[kl][3])}</span>'
                    for kl in kt.DNI)
    # 🔴 ПУСТЫЕ ЯЧЕЙКИ ПОД ЗАМОК И ГРУППУ. Владелец 07.09: «понедельник стоит не
    # над колонкой для понедельника, четверг не над колонкой для четверга, он
    # стоит над замочком». Подпись съезжает ровно на ширину органов, которых в
    # шапке нет, — значит они в ней должны быть, пустыми.
    # 🔴 ПУСТАЯ ЯЧЕЙКА ПОД ПОЛЕ ГРУППЫ — ИНАЧЕ ШАПКА СТОИТ НЕ НАД СВОИМИ
    # СТОЛБЦАМИ. У организатора в строке есть третий орган, группа; без такой же
    # пустой ячейки в шапке подписи съезжают на его ширину, и «ПН» повисает над
    # четверговым полем (замер верификатора: подпись 325–493 px, поля 245–459).
    # Ячейка несёт `data-org`, поэтому у гостя её нет — как нет у него и самого
    # поля группы, и каркасы остаются равными побайтово.
    if kt.ADMIN:
        metki += ('<span class="dv dv-zam" data-org="pravit-raspredelenie">'
                  "</span>"
                  '<span class="dv dv-gr" data-org="pravit-raspredelenie">'
                  "</span>")
    # Пустая ячейка под колонку класса — тем же приёмом, что и под замок/группу
    # выше: без неё шапка «ПН · ЧТ» съезжала бы на ширину органа, которого в
    # шапке нет.
    kl_pusto = ('<span class="kl-kol" data-org="videt-klass"></span>'
                if kt.mozhno("videt-klass") else "")
    return ('<div class="para shapka-dnej"><span class="kto"></span>'
            f'{kl_pusto}<span class="komu">{metki}</span></div>')


def shirina_imeni_ch(kt) -> int:
    """Ширина полосы под ФИО, в символах (`ch`) — СЧИТАНА ИЗ УЖЕ ЗАГРУЖЕННЫХ
    СТРОК, А НЕ ВПИСАНА КОНСТАНТОЙ (владелец 09.09, критерий готовности §2).

    🔴 НИКАКОГО НОВОГО ОБРАЩЕНИЯ К БАЗЕ — `kt.shk_dnya` уже принесён контекстом
    (`sobrat_kontekst`, вне зоны этого захода); этот файл, как сказано в его же
    шапке, «не открывает базу и не импортирует shell» — и не начинает сейчас.
    Берём самую длинную строку «Фамилия Имя» среди уже загруженных школьников,
    а не только фамилию: `.kto` показывает оба слова одной строкой без переноса,
    и по одной фамилии ширина оказалась бы тесной для сочетания длинной фамилии
    с длинным именем.
    """
    rows = next(iter(kt.shk_dnya.values()), [])
    if not rows:
        return 18
    return max(len(f'{r["surname"]} {r["name"]}') for r in rows)


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
    # 🔴 `STILI` И `--imya-w` ЭМИТИРУЮТСЯ ЗДЕСЬ И РОВНО ЗДЕСЬ. `vid_vse()`
    # вызывается композицией страницы ОДИН раз на рендер (в отличие от
    # `vkladka_gruppy`, которую зовут трижды — по разу на В/Д/Н); эмиссия из неё
    # даёт ОДИН `<style>` на страницу, а не три одинаковых. `--imya-w` живёт на
    # `:root`, поэтому её видят и три вкладки групп — общий предел ширины для
    # всей школы, не только для этой вкладки. Место в разметке (внутри `<body>`)
    # валидно для HTML5. Множитель и добавка подобраны замером: `ch` мерит
    # ширину цифры «0», а кириллица в заголовочной паре («Й», «Ю», «Щ») шире —
    # запас 15% плюс место под значок «обычно у» и внутренние отступы.
    imya_style = ('<style>:root{--imya-w:calc(%dch * 0.85 + .5rem)}</style>'
                  % shirina_imeni_ch(kt))
    return (STILI + STILI_KOLONKI + imya_style + '<div class="dva">'
            f'<div class="kol">{shapka}{"".join(para_shk(kt, r) for r in deti[:pol])}</div>'
            f'<div class="kol">{shapka}{"".join(para_shk(kt, r) for r in deti[pol:])}</div></div>')


def vybor_gruppy_dnya(kt, r):
    """Группа школьника НА ЭТО ЗАНЯТИЕ: «нигде · В · Д · Н».

    Пишется в слой занятия, рядом с переводом к другому преподавателю, и живёт
    ровно один день: назавтра он снова там, где его поставил шаблон.
    """
    # 🔴 ПОЛЕ ПОКАЗЫВАЕТ ТО, ЧТО ЕСТЬ, А НЕ ТО, ЧТО В НЁМ ЗАПИСАНО РУКАМИ. Группа
    # на день пуста у всех, кого сегодня не двигали, — а стоят они при этом не
    # «нигде», а у своего человека, то есть в его группе. Показывать «нигде»
    # сорока пяти детям, которые на самом деле распределены, — врать в самом
    # заметном месте экрана. «Нигде» остаётся ровно там, где оно правда: ни
    # сегодняшнего преподавателя, ни поставленной руками группы.
    tek = pole(r, "gruppa_dnya", "") or (gr_shk(kt, r) or "")
    opts = ['<option value=""%s>нигде</option>' % (" selected" if not tek else "")]
    for kod in ("В", "Д", "Н"):
        opts.append('<option value="%s"%s>%s</option>'
                    % (kod, " selected" if tek == kod else "", kod))
    return (f'<select class="org grd-sel" data-org="pravit-raspredelenie"'
            f' data-sid="{r["id"]}" data-den="{e(kt.den)}">'
            + "".join(opts) + '</select>')


def prisutstvuyushchie(kt, kl=None):
    """Школьники, которые сегодня ЗДЕСЬ: без отмеченных отсутствующими.

    На постоянном экране фильтровать нечего — там нет «сегодня», и функция
    честно отдаёт всех.
    """
    kl = kl or next(iter(kt.DNI))
    return [r for r in kt.shk_dnya[kl] if prishol(r)]
