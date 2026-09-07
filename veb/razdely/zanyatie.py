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
from core.services.sostav_na_den import SostavService, is_lesson_day, slot_of
from infra.enrollment_repo import SqliteEnrollmentRepo
from infra.room_repo import SqliteAttendance, SqliteSessions

#: Опорная точка навигации: соседнее занятие в обе стороны (Р2 ТЗ — прошлое и будущее
#: правятся одинаково, «может, один раз в год», но прятать нельзя).
SHAG_DNEJ = 14


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
