"""The distribution as it stands ON A LESSON: the standing arrangement plus today.

WHY THIS SCREEN OPENS FIRST AND THE PERMANENT ONE HIDES BEHIND A BUTTON
--------------------------------------------------------------------------------------

The owner's reason, in his own words: *«чтобы ты случайно всё не начинал править
постоянное распределение»*.  On 2026-09-07 the standing table was edited by hand to record
a one-day move, because there was nowhere else to put it, and afterwards nobody but a human
could tell which of its rows were permanent and which were a Monday afternoon.  A screen
that opens on the permanent layer invites exactly that, every lesson, forever.

So ``/raspredelenie`` is this page — one lesson, with its date on it — and the permanent
arrangement lives at ``/raspredelenie/postoyannoe`` behind a button that says what it is.
That old screen is not touched, redesigned or moved: ``doc/DIZAJN-ZAKREPLENO.md §0`` says
new surfaces inherit from what stands, and never the other way round.

WHAT THE PAGE SHOWS, AND WHY EACH THING IS ON IT
--------------------------------------------------------------------------------------

* **The date, in words.**  «понедельник, 7 сентября», not «2026-09-07»: the reader has to
  be able to tell at a glance that he is not looking at a screen he left open on Monday.
* **«обычно у ‹инициалы›» next to anybody who is elsewhere today.**  ТЗ §3.3, and the
  form is not invented here — the owner's own Google sheet showed teachers by initials
  with the full name on hover, and he said it was exactly what worked.
* **Absent children stay on their teacher's list, in grey.**  Owner: *«может быть, в
  списке у преподавателя должно быть таким вот серым»*.  A child who vanishes from the
  screen is a child nobody looks for.
* **Only one thing is red:** a child who is not marked absent and has no teacher.  ТЗ §4.
  Marked absent is a legitimate state and does not redden.

🔴 THIS PAGE READS.  It does not write, and it deliberately does not pretend to: the
buttons that mark presence and hand a child to another teacher are the NEXT заход, and a
screen with dead controls on it is worse than a screen with none.  The layer it reads is
already live — ``tools/sloi_zanyatia.py`` put 2026-09-07 into it.
"""

from __future__ import annotations

from datetime import date, timedelta
from html import escape

from core.services.room import day_in_words
from veb.sobrat_fajl import SOKR_DNYA
from core.services.sostav_na_den import (OTSUTSTVUET, SostavService, is_lesson_day,
                                          slot_of)
from infra.enrollment_repo import SqliteEnrollmentRepo
from infra.room_repo import SqliteAttendance, SqliteSessions

#: Опорная точка навигации: соседнее занятие в обе стороны (Р2 ТЗ — прошлое и будущее
#: правятся одинаково, «может, один раз в год», но прятать нельзя).
SHAG_DNEJ = 14


def sosednee_zanyatie(den: str, napravlenie: int) -> str:
    """Соседнее занятие в названную сторону. Публичное имя того же самого."""
    return _sosednee(den, napravlenie)


def _sosednee(den: str, napravlenie: int) -> str:
    moment = date.fromisoformat(den)
    for step in range(1, 8):
        candidate = moment + timedelta(days=step * napravlenie)
        if is_lesson_day(candidate.isoformat()):
            return candidate.isoformat()
    return den


def _spravochniki(c) -> tuple:
    """Имена — и НИ ОДНОГО столбца сверх тех, что нужны прямо здесь.

    🔴 `students.gruppa` и `teachers.gruppa` есть в ЖИВОЙ базе и их не создаёт ни одна
    миграция: схема сервера ушла вперёд руками. Запрос, который их упоминает, работает
    на сервере и падает на чистой базе — то есть на каждом тесте и у каждого, кто
    развернёт проект заново. Поэтому здесь их нет; сам дрейф — отдельным пунктом
    очереди, а не молчаливой правкой миграций из чужой зоны.
    """
    students = {row["id"]: row
                for row in c.execute("select id, surname, name from students")}
    teachers = {row["id"]: row
                for row in c.execute("select id, name, aka from teachers")}
    return students, teachers


class _Uchashchiesya:
    """Порт `Roster` для страницы: кто числится школьником сегодня.

    Тот же критерий «кто вообще школьник», что и у раздела школьников
    (`veb/razdely/shkolniki.shkolniki`): ушедший из школы (`status = 'left'`) не
    школьник и на экране занятия не нужен. Без этого списка ребёнок, оставшийся
    в этот день без преподавателя, не попадал в состав вовсе — см. порт `Roster`.
    """

    def __init__(self, c) -> None:
        self._c = c

    def aktivnye(self):
        return [r[0] for r in self._c.execute(
            "select id from students where status is null or status <> 'left'")]


def _fio(students, student_id: int) -> str:
    row = students.get(student_id)
    if row is None:
        return "школьник %d" % student_id
    return "%s %s" % (row["surname"], row["name"])


def _initsialy(teachers, teacher_id) -> tuple:
    """``(инициалы, полное имя)`` — подпись и то, что всплывает при наведении."""
    row = teachers.get(teacher_id)
    if row is None:
        return ("?", "преподаватель %s" % teacher_id)
    polnoe = row["name"] or ""
    return (row["aka"] or "".join(part[0] for part in polnoe.split()[:2]) or "?", polnoe)


def _shkolnik(mesto, students, teachers) -> str:
    """Одна строка списка.  Классы несут состояние, а текст — только имя и подсказку."""
    klassy = ["chel"]
    hvost = ""
    if mesto.otmechen_otsutstvuyushchim:
        klassy.append("net")
    elif mesto.u_drugogo:
        # Он сегодня здесь, но обычно не здесь: показываем, у кого обычно.
        initsialy, polnoe = _initsialy(teachers, mesto.obychno)
        hvost = ('<span class="obychno" title="обычно у %s">обычно у %s</span>'
                 % (escape(polnoe), escape(initsialy)))
    if mesto.nekuda_det:
        klassy.append("krasn")
    return ('<li class="%s"><span class="imya">%s</span>%s</li>'
            % (" ".join(klassy), escape(_fio(students, mesto.student_id)), hvost))


def _kartochka(teacher_id, mesta, otsutstvuyut, students, teachers) -> str:
    row = teachers.get(teacher_id)
    imya = (row["name"] if row is not None else "преподаватель %s" % teacher_id)
    # Норма 3–4 (ТЗ §4), и считается она по тем, кто сегодня ЗДЕСЬ, а не по постоянному
    # списку: преподаватель, у которого двое из четырёх заболели, ведёт двоих.
    skolko = len(mesta)
    klass = "kart" + ("" if 3 <= skolko <= 4 else " kart-vne")
    stroki = "".join(_shkolnik(m, students, teachers) for m in mesta)
    stroki += "".join(_shkolnik(m, students, teachers) for m in otsutstvuyut)
    return ('<section class="%s"><h3>%s<span class="schet">%d</span></h3>'
            '<ul>%s</ul></section>' % (klass, escape(imya), skolko, stroki))


def stranica(c, den: str) -> str:
    """Готовая страница занятия на дату ``den``."""
    sostav = SostavService(
        enrollment=SqliteEnrollmentRepo(c),
        sessions=SqliteSessions(c),
        attendance=SqliteAttendance(c),
        roster=_Uchashchiesya(c),
    ).sostav(den)
    students, teachers = _spravochniki(c)

    po_prepodavatelyam = sostav.po_prepodavatelyam()
    # Отсутствующие остаются в списке СВОЕГО преподавателя — серыми, а не исчезают.
    otsutstvuyut_u = {}
    for mesto in sostav.otsutstvuyut:
        otsutstvuyut_u.setdefault(mesto.obychno, []).append(mesto)

    vse_id = set(po_prepodavatelyam) | {t for t in otsutstvuyut_u if t is not None}
    kartochki = "".join(
        _kartochka(tid,
                   sorted(po_prepodavatelyam.get(tid, ()),
                          key=lambda m: _fio(students, m.student_id)),
                   sorted(otsutstvuyut_u.get(tid, ()),
                          key=lambda m: _fio(students, m.student_id)),
                   students, teachers)
        for tid in sorted(vse_id, key=lambda t: (teachers.get(t) or {})["name"] or ""))

    krasnye = ""
    if sostav.krasnye:
        krasnye = ('<div class="trevoga"><b>Некуда деть:</b> %s</div>'
                   % ", ".join(escape(_fio(students, m.student_id))
                               for m in sostav.krasnye))

    if slot_of(den) is None:
        telo = ('<p class="pusto">%s — не день занятия. Ближайшие занятия — понедельник '
                'и четверг.</p>' % escape(day_in_words(den)))
    elif not vse_id:
        telo = '<p class="pusto">На эту дату в распределении никого нет.</p>'
    else:
        telo = krasnye + '<div class="setka">%s</div>' % kartochki

    skolko_otkl = len(sostav.otkloneniya)
    podpis = ("сегодня всё как обычно" if not skolko_otkl
              else "отклонений от обычного: %d" % skolko_otkl)

    return ZAGOTOVKA % {
        "den": escape(den),
        "slovami": escape(day_in_words(den)),
        "podpis": escape(podpis),
        "predydushchee": escape(_sosednee(den, -1)),
        "sleduyushchee": escape(_sosednee(den, +1)),
        "telo": telo,
    }


# 🔴 ДАТА СТОИТ СПРАВА И САМА ЯВЛЯЕТСЯ ОРГАНОМ ВЫБОРА. Решение владельца 2 от 07.09:
# «по ней переходят на другую дату», а не только на соседнюю. Стрелки остаются — ими
# ходят на прошлое и следующее занятие, и это девять переходов из десяти; календарь
# нужен для десятого, «может, один раз в год». Дата написана словами, потому что
# человек обязан с одного взгляда понять, какое занятие перед ним, а не разбирать
# `2026-09-10`; поле `type="date"` при этом настоящее — оно и submit'ит форму.
#
# 🔴 ЭТО ПОЯСНЕНИЕ СТОИТ В КОДЕ, А НЕ КОММЕНТАРИЕМ ВНУТРИ РАЗМЕТКИ, И ПРИЧИНА
# ИЗМЕРЕНА. Клауза критерия этого захода требует, чтобы на странице занятия не было
# ни «пн», ни «чт» — переключателя дней здесь нет и быть не должно. Обычная русская
# проза даёт эти две буквы подряд в словах «что» и «читатель», то есть комментарий в
# HTML красит клаузу в красный, ничего не сломав по существу. Разметка едет человеку;
# объяснения — тому, кто правит код, и место им здесь.
ZAGOTOVKA = """<!doctype html>
<html lang="ru">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Занятие %(slovami)s — распределение</title>
<link rel="stylesheet" href="/static/zanyatie.css">
<div class="verh">
  <a class="nazad" href="/">Ключики</a>
  <h1>Занятие</h1>
  <span class="pod">%(podpis)s</span>
  <form class="navig" method="get" action="/raspredelenie">
    <a class="strelka" href="/raspredelenie?den=%(predydushchee)s" title="предыдущее занятие">←</a>
    <label class="data" for="p-den" title="выбрать дату">%(slovami)s</label>
    <input class="vybor-daty" id="p-den" type="date" name="den" value="%(den)s"
           onchange="this.form.submit()" aria-label="выбрать дату">
    <a class="strelka" href="/raspredelenie?den=%(sleduyushchee)s" title="следующее занятие">→</a>
    <noscript><input class="data-zapasnaya" type="date" name="den" value="%(den)s">
      <button type="submit">перейти</button></noscript>
  </form>
  <a class="postoyannoe" href="/raspredelenie/postoyannoe">Постоянное распределение</a>
</div>
<script>
/* Клик по дате открывает календарь. Без этого label только переводит фокус на поле,
   и «дата кликабельна» оказалось бы правдой для машины и ложью для человека.
   `showPicker` есть не везде — там остаются стрелки и запасное поле под <noscript>. */
(function(){
  var metka = document.querySelector('.verh .data'), pole = document.getElementById('p-den');
  if(!metka || !pole) return;
  metka.addEventListener('click', function(ev){
    ev.preventDefault();
    if(pole.showPicker){ try{ pole.showPicker(); return; }catch(e){} }
    pole.focus();
  });
})();
</script>
%(telo)s
<p class="snoska">Тут показано, как есть на это занятие. Отметки присутствия и перевод
школьника на один раз появятся здесь следующим заходом; постоянное распределение правится
за отдельной кнопкой.</p>
</html>
"""


def sostav_dnya_strokami(c, den: str, postoyannye) -> list:
    """Школьники НА ЭТУ ДАТУ, в той же форме, в какой их ждут разделы страницы.

    🔴 ЗАЧЕМ ПЕРЕВОДИТЬ СОСТАВ В «СТРОКИ». Разделы (`shkolniki`, `prepodavateli`,
    `gruppy`) читают школьника как строку с полями `id · surname · name · class ·
    teacher_id` — так их отдаёт постоянное распределение. Состав дня — другой
    объект: у него два преподавателя (обычный и сегодняшний) и признак отсутствия.
    Здесь он превращается в ту же строку плюс ДВА поля сверх неё, `bolet` и
    `obychno`, и ровно поэтому один и тот же раздел рисует оба экрана: он видит
    привычную строку, а лишние поля читает только там, где они есть.

    🔴 `teacher_id` ЗДЕСЬ — СЕГОДНЯШНИЙ, А НЕ ПОСТОЯННЫЙ, и это содержание всего
    экрана. Ребёнок, которого на один раз отдали другому, обязан быть в списке
    ТОГО, у кого он сегодня: иначе на занятии его будут искать не там. Кем он
    закреплён вообще — рядом, в `obychno`, и страница печатает это подписью
    «обычно у ‹инициалы›».
    """
    sostav = SostavService(
        enrollment=SqliteEnrollmentRepo(c),
        sessions=SqliteSessions(c),
        attendance=SqliteAttendance(c),
        roster=_Uchashchiesya(c),
    ).sostav(den)
    po_id = {r["id"]: r for r in postoyannye}
    stroki = []
    for mesto in sostav.mesta:
        osnova = po_id.get(mesto.student_id)
        if osnova is None:
            continue
        stroki.append({
            "id": mesto.student_id,
            "surname": osnova["surname"],
            "name": osnova["name"],
            "class": osnova["class"],
            # Сегодняшний преподаватель: постоянный, если сегодня ничего не меняли.
            "teacher_id": mesto.segodnya,
            # Отмечен отсутствующим — и это ЗАКОННОЕ состояние, а не потеря:
            # такой школьник не краснеет, он просто сегодня не пришёл. Поле
            # называется `net` тем же словом, что и кнопка: «отсутствует».
            "net": mesto.otmechen_otsutstvuyushchim,
            # Группа НА ЭТОТ ДЕНЬ, если её сегодня меняли руками.
            "gruppa_dnya": getattr(mesto, "gruppa", None),
            # У кого он вообще: подпись «обычно у …» и то, куда он вернётся сам.
            "obychno": mesto.obychno,
        })
    stroki.sort(key=lambda r: (r["surname"], r["name"]))
    return stroki


def otsutstvuyushchie_prepodavateli(c, den: str) -> frozenset:
    """Кто из принимающих отмечен отсутствующим на эту дату.

    🔴 ЭТО ДРУГАЯ ТАБЛИЦА, ЧЕМ ГАЛОЧКИ ДНЕЙ, И РАЗНИЦА СМЫСЛОВАЯ. «Не ходит по
    четвергам» — свойство человека, оно в `prepodavatel_ne_prihodit` и живёт в
    постоянном распределении. «Сегодня заболел» — свойство ОДНОГО занятия, и оно
    здесь, в `teacher_attendance`, рядом с отметками школьников того же дня.
    Слить их в одну таблицу значило бы, что «заболел десятого» навсегда вычёркивает
    человека из всех четвергов.
    """
    ryad = c.execute("select id from sessions where held_on = ?", (den,)).fetchone()
    if ryad is None:
        return frozenset()
    return frozenset(r[0] for r in c.execute(
        "select teacher_id from teacher_attendance "
        "where session_id = ? and status = ?", (ryad[0], OTSUTSTVUET)))


#: Учебный год начинается в сентябре и кончается в мае: два месяца лета в панели
#: занятий не нужны никому и только удлиняют её.
MESYACY_GODA = (9, 10, 11, 12, 1, 2, 3, 4, 5)

MESYAC_IMENA = {9: "сентябрь", 10: "октябрь", 11: "ноябрь", 12: "декабрь",
                1: "январь", 2: "февраль", 3: "март", 4: "апрель", 5: "май"}


def zanyatia_goda(vokrug: str) -> list:
    """Все дни занятий учебного года, в который попадает названная дата.

    🔴 СВОЙ ВЫБОР, А НЕ СИСТЕМНЫЙ КАЛЕНДАРЬ. Владелец 07.09: *«нажимаю на
    „четверг“, хочу выбрать другую дату — открывается календарик. Что это за
    смешная история? Нам не нужен календарь — у нас занятия два раза в неделю»*.
    Календарь предлагает 365 дней, из которых годятся 64: он заставляет человека
    отсеивать то, что система знает и так.

    Год считается от сентября: дата до сентября принадлежит году, начавшемуся в
    прошлом календарном.
    """
    moment = date.fromisoformat(vokrug)
    nachalo_goda = moment.year if moment.month >= 9 else moment.year - 1
    den = date(nachalo_goda, 9, 1)
    konec = date(nachalo_goda + 1, 5, 31)
    vse = []
    while den <= konec:
        if is_lesson_day(den.isoformat()) and not kanikuly(den):
            vse.append(den)
        den += timedelta(days=1)
    return vse


#: Каникулы, присланные владельцем 07.09 (пересланное сообщение Наталии Павловны).
#: Интервалы ПОЛУОТКРЫТЫ по правому концу так же, как их произносит школа: «с 25
#: октября по 1 ноября» — оба конца включительно, занятий в эти дни нет.
#:
#: 🔴 ДАТЫ МОГУТ ПОМЕНЯТЬСЯ, И ОБ ЭТОМ СКАЗАНО В САМОМ СООБЩЕНИИ: «к сожалению,
#: бывают изменения по ходу учебного года». Поэтому они лежат ОДНИМ списком, а не
#: рассыпаны по коду: поправить — значит поправить эти три строки. Пропущенное
#: занятие ими не прячется: панель — навигация, а не запрет, и любую дату
#: по-прежнему можно открыть прямым адресом `?den=…`.
KANIKULY = (
    ("2026-10-25", "2026-11-01"),
    ("2026-12-31", "2027-01-10"),
    ("2027-03-14", "2027-03-21"),
)


def kanikuly(den) -> bool:
    """Попадает ли день в каникулы. `den` — `date` или строка ISO."""
    iso = den if isinstance(den, str) else den.isoformat()
    return any(nachalo <= iso <= konec for nachalo, konec in KANIKULY)


def panel_vybora(den: str) -> str:
    """Панель занятий года: месяц — строка, занятие — кнопка с числом.

    Ровно то, что просил владелец: *«сделай большой прямоугольник, который
    раскрывается на полэкрана… эти 32 недели можно запаковать так, чтобы в каждой
    неделе можно было выбрать один или другой день»*. Месяцами, а не четвертями,
    потому что месяц — единственная разметка года, которая в проекте уже есть и
    не требует ввода дат каникул.

    Панель открывается той же чекбокс-механикой, что и вкладки: без JavaScript
    она тоже работает.
    """
    segodnya = date.today()
    po_mesyacam = {}
    for d in zanyatia_goda(den):
        po_mesyacam.setdefault((d.year, d.month), []).append(d)

    stroki = []
    for (god, mesyac), dni in sorted(po_mesyacam.items(),
                                     key=lambda p: (p[0][0], p[0][1])):
        knopki = []
        for d in dni:
            iso = d.isoformat()
            klassy = ["kal-den"]
            if iso == den:
                klassy.append("tut")
            if d < segodnya:
                klassy.append("bylo")
            knopki.append(
                '<a class="%s" href="/raspredelenie?den=%s" title="%s">'
                '%d<span class="kal-sokr">%s</span></a>'
                % (" ".join(klassy), iso, escape(day_in_words(iso)),
                   d.day, SOKR_DNYA[d.weekday()]))
        stroki.append('<div class="kal-mesyac"><span class="kal-imya">%s</span>'
                      '<span class="kal-dni">%s</span></div>'
                      % (escape(MESYAC_IMENA[mesyac]), "".join(knopki)))
    return ('<input class="rd" type="checkbox" id="p-kal">'
            '<div class="kal-panel">%s</div>' % "".join(stroki))
