#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-code — the route below is declared by `marshruty()` and
# collected by `veb.server._marshruty_razdelov` (`RAZDELY_S_MARSHRUTAMI`), the same seam
# `veb/razdely/istoria.py` already uses.
r"""История занятий: кто был на каждом ПРОШЕДШЕМ занятии, и у кого/с кем.

🔴 СТРОКА МОДУЛЯ СЫРАЯ (префикс `r` у тройной кавычки) ИЗ-ЗА ОДНОЙ
ПОСЛЕДОВАТЕЛЬНОСТИ `\|` НИЖЕ, И
ЭТО НЕ КОСМЕТИКА. `grep -n 'menyu\|ssyl'` в обычной строке — НЕВЕРНАЯ
управляющая последовательность: Python пока только предупреждает, но pytest
умеет поднимать предупреждения до ошибок, и тогда падает не тест, а ИМПОРТ
модуля, то есть весь файл тестов разом. Поймано живьём в этой сессии: первая
же компиляция после правки (пустой `__pycache__`) дала
`SyntaxError: invalid escape sequence \|` на строке 5 и увела в красное 42
зелёных теста; на втором прогоне, уже из кэша, всё было зелено — то есть
ловушка срабатывает ровно на чистой машине и молчит на своей.

WHAT THE OWNER ASKED FOR, 09.09, in his own words: *«я бы сделал вкладку История, где
вывел бы слева список… внутри было бы две вкладки, преподаватели и школьники… и у каждого
в первом столбце все фамилии школьников, а справа остальные столбцы соответствуют датам
занятий. И есть либо галочка, если человек был, либо крестик, если не был… наверное, нужна
не галочка, а инициалы преподавателя, который у них принимал»*. The motive, in his words
too: *«школьник всё время у одного преподавателя, а потом он заболел… мы хотим вспомнить,
у кого он был»*. This is a READ. Nothing here writes to the database.

🔴 NOT THE SAME FILE AS `veb/razdely/istoria.py`. That module is a DIFFERENT feature added
09.09 — the history of ONE MARK-JOURNAL CELL (right-click/long-press panel on Кондуит),
with its own `/api/istoria*` routes. This file is about LESSON ATTENDANCE, route `/istoria`.
Neither imports the other; the names collide in English only, not in what they answer.

🔴 THIS IS A STANDALONE PAGE, NOT A SIXTH SHELL TAB, AND THAT IS A ZONE CONSTRAINT, NOT A
DESIGN CHOICE. The site's tab machinery — the radio buttons, the menu row, the per-capability
lazy imports for «Кондуит»/«Моё» — lives in `veb/obshchee/karkas.py::obolochka()`, outside
this заход's zone. The exact same conflict already happened for those two sections, and the
codebase's own resolution is on record in `veb/razdely/kartochka.py`: build a standalone page
(own `<!doctype html>`, `_obshchij_stil()`) and record the missing menu link as a debt for
whoever owns `karkas.py`/`tools/sobrat_stranicu.py` next (see `## ВОПРОСЫ` of the заход this
file was written in).

🔴 ТОТ ДОЛГ ЗАКРЫТ 11.09, И СТРАНИЦА БОЛЬШЕ НЕ БЕЗ МЕНЮ. Она несла его НОЛЬ:
`grep -n 'menyu\|ssyl'` по этому файлу давал пусто, и рендер подтверждал — 0 пунктов
меню на 1440×900. Отсюда слова владельца «пропадает всё остальное меню» и «человек
попадает туда и не понимает, куда попал». Меню рисует `karkas.menyu_ssylkami("/istoria")`
— та же одна функция, что уже стоит на `/kabinet`; своего списка пунктов здесь нет и
заводить его нельзя. Страница по-прежнему самостоятельный документ, а не шестая вкладка
оболочки: меню — строка ссылок, а не переключатель разделов.

🔴 СЛОВО «ЖУРНАЛ» ВМЕСТО «ИСТОРИИ» — предложение владельца 10.09: «может, гораздо лучше
так писать». Поменялось то, что читает человек: подпись в меню, `<h1>` и `<title>`. Адрес
`/istoria` и имя модуля прежние — переименование маршрута задело бы `veb/server.py` и
каждую ссылку сайта, то есть чужую зону, а читателю не дало бы ничего.

WHAT "был" MEANS, AND WHY IT IS NOT RE-DECIDED HERE. A student is present at a past lesson
unless an `attendance` row names them absent — no row at all is the DEFAULT and means "as
usual", which is not this file's invention: it is the exact rule `veb/server.py`'s own write
path already encodes (a row is deleted, not kept, whenever it resolves back to plain
presence with no deviation). `core.services.sostav_na_den.SostavService.sostav(den)` already
answers this once per day; `core.services.istoria_poseshchenij.IstoriyaService` folds it over
every PAST date. Neither table is read a second time here — this file only turns the read
model into HTML.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import config
from core.services.history import nachalo_zanyatia_iso, zanyatie_po_iso
from core.services.istoria_poseshchenij import IstoriyaService
from core.services.sostav_na_den import SostavService
from infra.enrollment_repo import SqliteEnrollmentRepo
from infra.room_repo import SqliteAttendance, SqliteSessions
from infra.sessions_repo import SqliteSessionBook
from veb import vhod
from veb.obshchee.karkas import (
    SKRIPT_PAMYAT_VKLADOK,
    CHETVERTI_STILI, PRICHINY_OTSUTSTVIYA, SDACHI_SKRIPT, SDACHI_STILI,
    chetverti_goda, e, menyu_ssylkami, nomer_chetverti, otmetit_otsutstvie,
    perekluchatel_chetvertej, periody_otsutstvij, snyat_otsutstvie, v_rode)
from core.istochnik import put_bazy
from veb.razdely.list_odin import _obshchij_stil

#: Сколько занятий назад просить у базы. Учебный год держит два занятия в неделю; 400
#: покрывает несколько лет вперёд и назад с большим запасом и не растёт со временем
#: настолько, чтобы это было заметно на school масштабе (десятки, не тысячи занятий).
GLUBINA_ZANYATIJ = 400


class _AktivnyeShkolniki:
    """Порт `Roster` для `SostavService`: кто вообще школьник сегодня.

    Тот же критерий, что и везде на сайте (`shkolniki.shkolniki`,
    `zanyatie._Uchashchiesya`, `konduit._uchastniki`): ушедший (`status = 'left'`) не
    считается. Без этого порта школьник без единой строки в `enrollment`/`attendance` на
    какую-то дату просто исчезал бы с этой даты в решётке — см. предупреждение самого
    порта в `core/services/sostav_na_den.py`.
    """

    def __init__(self, c: sqlite3.Connection) -> None:
        self._c = c

    def aktivnye(self):
        return [r[0] for r in self._c.execute(
            "select id from students where status is null or status <> 'left'")]


class _TeacherAbsences:
    """Порт `TeacherAbsences`: кто из принимающих отмечен отсутствующим на занятие.

    Тот же запрос, что уже читает `veb/razdely/zanyatie.py::otsutstvuyushchie_prepodavateli`
    для той же таблицы `teacher_attendance` — не второе мнение, тот же факт, читаемый
    здесь под собственным маленьким портом, потому что `core/services/` не имеет права
    знать про sqlite.
    """

    def __init__(self, c: sqlite3.Connection) -> None:
        self._c = c

    def otsutstvuyushchie(self, session_id: int) -> frozenset:
        return frozenset(r[0] for r in self._c.execute(
            "select teacher_id from teacher_attendance where session_id = ? and status = ?",
            (session_id, "не был")))

    def prisutstvovavshie(self, session_id: int) -> frozenset:
        return frozenset(r[0] for r in self._c.execute(
            "select teacher_id from teacher_attendance where session_id = ? and status = ?",
            (session_id, "был")))


def _spravochniki(c: sqlite3.Connection) -> tuple:
    """Имена — школьники (активные) и преподаватели (активные), в порядке для решётки.

    🔴 `teachers.aktiven` — СХЕМНЫЙ ДРЕЙФ, как `teachers.gruppa`/`students.gruppa`
    (`veb/razdely/zanyatie.py::_spravochniki`, тот же комментарий): ни одна миграция его
    не заводит, а живая база несёт (её же уже фильтрует `karkas.sobrat_kontekst`, тем же
    условием). Не чинится здесь — чужая миграция вне зоны этого захода.
    """
    students = [dict(r) for r in c.execute(
        "select id, surname, name from students "
        "where status is null or status <> 'left' order by surname, name")]
    teachers = [dict(r) for r in c.execute(
        "select id, name, aka from teachers where aktiven = 1 order by name")]
    return students, teachers


def _initsialy(row: dict) -> str:
    polnoe = row.get("name") or ""
    return row.get("aka") or "".join(p[0] for p in polnoe.split()[:2]) or "?"


def _kratko(den: str) -> str:
    """`2026-09-07` → `07.09` — то же сжатие, что уже стоит под галочкой на Кондуите."""
    return "%s.%s" % (den[8:10], den[5:7])


#: 🔴 ДНЯ НЕДЕЛИ В ШАПКЕ БОЛЬШЕ НЕТ, И ЭТО ПРЯМОЕ СЛОВО ВЛАДЕЛЬЦА 11.09, А НЕ
#: ЭКОНОМИЯ МЕСТА: «там ничего другого не пиши, только даты». Здесь стояла пара
#: `DNI_NEDELI` + `_shapka_dnya`, дававшая «пн 07.09»; шапка теперь — ровно то, что
#: возвращает `_kratko`, то есть «07.09». Пара удалена целиком, а не оставлена без
#: зова: функция, которую никто не зовёт, зелена ровно потому, что её никто не зовёт.


def _sostavit(c: sqlite3.Connection):
    """Читает базу один раз и отдаёт `(решётка, строки sessions)`.

    Один вызов на страницу: и решётка, и род занятия, и число столбцов берутся из
    одного чтения, а не из трёх.
    """
    sostav = SostavService(
        enrollment=SqliteEnrollmentRepo(c),
        sessions=SqliteSessions(c),
        attendance=SqliteAttendance(c),
        roster=_AktivnyeShkolniki(c),
    )
    teachers_all = [dict(r) for r in c.execute(
        "select id from teachers where aktiven = 1")]
    service = IstoriyaService(
        sostav=sostav,
        teacher_absences=_TeacherAbsences(c),
        active_teacher_ids=[r["id"] for r in teachers_all],
    )
    vse_sessii = SqliteSessionBook(c).recent(GLUBINA_ZANYATIJ)
    # 🔴 СЕССИИ ВОЗВРАЩАЮТСЯ ВМЕСТЕ С РЕШЁТКОЙ, А НЕ ЧИТАЮТСЯ ВТОРОЙ РАЗ. Род занятия
    # (`sessions.kind`) уже приехал в этих же строках — `SqliteSessionBook` берёт его
    # каждой строкой. `IstoriyaService` его не несёт: его `dni` — кортеж дат, и добавить
    # туда род значило бы править `core/services/istoria_poseshchenij.py`, файл вне зоны
    # этого захода. Поэтому род собирается здесь, из списка, который уже в руках.
    return (service.sostavit(vse_sessii, seichas=datetime.now(timezone.utc)), vse_sessii)


# --------------------------------------------------------------- что сдано на занятии


#: Что кладётся в клетку сверх знака присутствия. Пусто СЕГОДНЯ и по решению
#: владельца («оценки и комментарии сейчас не вводим — оставить им место»), и
#: заполняется тем заходом, который оценки заводит: клетка уже несёт для них
#: отдельные ячейки, и таблицу для этого переделывать не придётся.
PUSTYE_MESTA = ('<span class="kl-ocenka" data-mesto="оценка"></span>'
                '<span class="kl-komm" data-mesto="комментарий"></span>')


def sdachi_po_zanyatiyam(c: sqlite3.Connection, dni) -> dict:
    """`{(день, школьник): ((задача, листок, кто принял), …)}` — что сдано в этот день.

    🔴 ИМЯ БЕЗ ПОДЧЁРКИВАНИЯ, ПОТОМУ ЧТО ЗВАТЕЛЕЙ ДВА: журнал (этот файл) и кабинет
    (`veb/razdely/kabinet.py`). Второй копии этого разбора заводить нельзя — она и
    была бы тем самым вторым мнением о том, к какому занятию относится галочка.

    🔴 ДЕНЬ ОТМЕТКИ НЕ ВЫВОДИТСЯ ЗДЕСЬ ЗАНОВО. Какому занятию принадлежит галочка,
    отвечает ровно одно место — `core.services.history.zanyatie_po_iso` (правило
    владельца 09.09: «галочка относится к последнему прошедшему занятию»), и
    перебивка человека живёт в `mark_lesson_override`, которую то же правило
    подставляет ВМЕСТО `valid_at` (`history.istoria_kletki`). Здесь та же пара:
    `coalesce(перебивка, valid_at)` уходит в `zanyatie_po_iso`, и второго мнения о
    дне не заводится. SQL ниже только СУЖАЕТ выборку по сырому времени — это
    граница, а не отнесение к занятию.

    🔴 ИМПОРТ ИСКЛЮЧЁН, И ЭТО НЕ ВКУС. Все 15 847 строк прошлогодней книги несут
    один и тот же `valid_at`: бумажная книга дат занятий не хранит вовсе
    (`core/services/spiski.py` открывается разбором этой же ловушки). Пущенные в
    решётку, они превратились бы в один фантомный «день», на котором сдал каждый.

    🔴 ПАРА ТЕХНИЧЕСКИХ НАЖАТИЙ ЗДЕСЬ НЕ ОТСЕИВАЕТСЯ, и это сказано вслух, а не
    умолчано: её признак считает `history.tehnicheskie` по ПОЛНОЙ ленте одной
    клетки, а этот запрос ленту не поднимает. Показывается то, что стоит: события
    `assert`. Отсев — заход, который будет вводить оценку, и он поднимет ленту.
    """
    if not dni:
        return {}
    try:
        granica = nachalo_zanyatia_iso(dni[0])
    except ValueError:
        # День занятия, заведённый руками вне пн/чт: расписание для него часа не
        # знает. Тогда границей берётся полночь этого дня — шире, чем нужно, и это
        # честнее, чем отбросить день целиком.
        granica = dni[0] + "T00:00:00Z"
    ryady = c.execute(
        """
        select m.student_id            as student_id,
               m.teacher_id            as teacher_id,
               coalesce(o.valid_at, m.valid_at) as kogda,
               p.label                 as zadacha,
               s.number                as listok
        from marks m
        join problems p on p.id = m.problem_id
        join sheets   s on s.id = p.sheet_id
        left join (
            select mark_id, valid_at,
                   row_number() over (partition by mark_id order by id desc) as svezhest
            from mark_lesson_override
        ) o on o.mark_id = m.id and o.svezhest = 1
        where m.event = 'assert' and m.source <> 'импорт'
          and coalesce(o.valid_at, m.valid_at) >= ?
        order by s.ord, p.ord
        """,
        (granica,),
    ).fetchall()
    nuzhnye = set(dni)
    itog: dict = {}
    for r in ryady:
        den = zanyatie_po_iso(r["kogda"])
        if den not in nuzhnye:
            continue
        itog.setdefault((den, r["student_id"]), []).append(
            (r["zadacha"], r["listok"], r["teacher_id"]))
    return {k: tuple(v) for k, v in itog.items()}


def _rod_zanyatiya(c: sqlite3.Connection, sessii) -> dict:
    """`{день: род}` из тех же строк `sessions`, которые уже прочитаны для решётки.

    🔴 РОД ЖИВОЙ, И ЭТО ПРОВЕРЕНО НА БОЕВОЙ БАЗЕ, А НЕ ПРЕДПОЛОЖЕНО: колонка
    `sessions.kind` заведена `migrations/001_init.sql:83`, `SqliteSessionBook`
    читает её каждой строкой (`_SESSION_COLUMNS = "id, held_on, kind"`), и на
    копии боевой базы 11.09 она несла значение `обычное` на единственном занятии
    10.09. Второго запроса за ней не нужно — строки уже в руках.

    🔴 РОДОВ В СХЕМЕ ТРИ, А ВЛАДЕЛЕЦ НАЗВАЛ ЧЕТЫРЕ, И ЧЕТВЁРТЫЙ НЕ ВЫДУМЫВАЕТСЯ.
    `check (kind in ('обычное', 'зачёт', 'отменённое'))` — база откажет на любом
    другом слове. Слова владельца переводятся на то, что схема ДЕРЖИТ:
    «контрольная» это `зачёт`, «отменено» это `отменённое`. «Дополнительное»
    держать нечем: это миграция, а `migrations/` — вне зоны этого захода. Пункт
    очереди стоит в `## ВОПРОСЫ`; показывать несуществующий род было бы
    сообщением о данных, которых в базе нет.
    """
    return {s.held_on: s.kind for s in sessii}


#: Род занятия — КЛАССОМ СТОЛБЦА, А НЕ СЛОВОМ В НЁМ. Здесь стояла таблица
#: `IMYA_RODA` («зачёт» → «контрольная», «отменённое» → «отменено»), и род печатался
#: второй строкой под датой у КАЖДОГО столбца. Владелец 11.09 назвал эту строку
#: первой: «вот это слово „обычное“ зачем нужно? Не нужно слово „обычное“. Там ничего
#: другого не пиши, только даты».
#:
#: 🔴 ФАКТ ПРИ ЭТОМ НЕ ПОТЕРЯН, И ЭТО РАЗНИЦА МЕЖДУ «УБРАТЬ СЛОВО» И «УБРАТЬ ЗНАНИЕ».
#: Владелец 10.09 просил ровно противоположное про сам факт: «когда были контрольные,
#: когда был праздник и урок отменился… всю эту историю курса важно где-то
#: документировать». Поэтому род уезжает в КЛАСС столбца: контрольная выделена
#: цветом, отменённый день зачёркнут. Читатель видит исключение и не читает слова —
#: а «обычное», которое и было шумом, не рисует ничего вовсе.
KLASS_RODA = {"зачёт": "ist-zachyot", "отменённое": "ist-otmen"}


def _imya_shkolnika(u: dict) -> str:
    return "%s %s" % (u["surname"], u["name"])


def _shapka(dni, rody, pervyj_stolbec: str) -> str:
    """Шапка решётки: ТОЛЬКО ДАТА. Род занятия — классом столбца, не словом в нём."""
    stolbcy = []
    for d in dni:
        klass = KLASS_RODA.get(rody.get(d), "")
        stolbcy.append(f'<th class="ist-zn {klass}">{e(_kratko(d))}</th>')
    return f'<th>{e(pervyj_stolbec)}</th>' + "".join(stolbcy)


def _kletka(klass: str, znak: str, vsplyv: str, den: str, vid: str, kto_id,
            ugolok: bool = False) -> str:
    """🔴 КЛЕТКА — МЕСТО, А НЕ ГАЛОЧКА, и это единственное место захода, где что-то
    сделано на шаг вперёд (владелец: «в неё позже пойдут ОЦЕНКА и КОММЕНТАРИЙ»).

    Что здесь ради будущего и почему это НЕ новый функционал:
      * клетка — контейнер с ИМЕНОВАННЫМИ ячейками (`kl-znak`, `kl-ocenka`,
        `kl-komm`), а не голый символ. Две последние сегодня пусты и ничего не
        рисуют; заходу, который заведёт оценку, останется положить в них текст —
        ни один `<td>`, ни одна строка, ни один селектор не переписываются.
      * клетка называет СЕБЯ (`data-den`, `data-vid`, `data-kto`) — по этим трём
        значениям её находит и раскрытие, и будущая правка. Без них редактор
        оценки был бы вынужден считать координаты по позиции столбца, то есть
        зависеть от порядка колонок.
    САМОЙ ОЦЕНКИ ЗДЕСЬ НЕТ И НЕ ЗАВОДИТСЯ: ни поля ввода, ни двери записи, ни
    колонки в базе — владелец сказал прямо, что сейчас их не вводим.
    """
    # 🔴 УГОЛОК — ОТДЕЛЬНЫЙ ОРГАН, ПОТОМУ ЧТО РЕДКОЕ ДЕЙСТВИЕ НЕ СМЕЕТ ЗАНИМАТЬ
    # ГЛАВНЫЙ ЖЕСТ. Владелец 11.09: «по умолчанию нажатие на клеточку должно
    # выводить кондуит… а можно где-то в углу сделать маленькое поле, при нажатии
    # на которое галочка будет меняться на крестик. Это более редкая ситуация».
    # Поэтому клик по ТЕЛУ клетки прошедшего дня открывает кондуит, а правка явки
    # живёт в уголке — и он есть только у того, кто вправе править.
    ugol = ('<span class="kl-ugol ots-klik" title="отметить, что его не было" '
            'role="button" tabindex="0">▫</span>') if ugolok else ""
    return (f'<td class="ist-kl {klass}" title="{vsplyv}" '
            f'data-den="{e(den)}" data-vid="{vid}" data-kto="{kto_id}" tabindex="0">'
            f'<span class="kl-znak">{znak}</span>{ugol}{PUSTYE_MESTA}</td>')


#: 🔴 СТОЛБЦЫ РЕШЁТКИ — КАЛЕНДАРЬ ЧЕТВЕРТИ, А НЕ СПИСОК ЗАПИСАННЫХ ЗАНЯТИЙ, И ЭТО
#: ПЕРЕВОРОТ, А НЕ ДОБАВКА. Раньше столбцами были `istoriya.dni` — то есть ровно те
#: дни, у которых уже есть строка в `sessions`. На живой базе такая строка была ОДНА
#: (10.09), и решётка «школьники × занятия» была таблицей в один столбец; отсюда
#: слова владельца 11.09: «не нужна пустая табличка, нужна табличка с узкими
#: колонками, распланированная сразу на 16 занятий».
#:
#: Столбцы теперь заводит `karkas.chetverti_goda` — шестнадцать дней занятий
#: четверти, все сразу, независимо от того, есть ли о них хоть одна запись. Данные
#: НАКЛАДЫВАЮТСЯ на этот календарь: день, о котором записи нет (будущий, или
#: прошедший, но не заведённый), даёт ПУСТУЮ клетку.
#:
#: 🔴 ПУСТАЯ КЛЕТКА — НЕ КРЕСТИК, И РАЗНИЦА ЗДЕСЬ СОДЕРЖАТЕЛЬНАЯ. Крестик значит «не
#: был» — утверждение о человеке, которое кто-то сделал. Будущее занятие такого
#: утверждения не несёт, и нарисовать там крестик значило бы сказать про весь класс,
#: что он не придёт. Пустая клетка не кликается и не открывает панель: открывать
#: нечего.
#:
#: `core/services/istoria_poseshchenij.py` при этом не тронут ни строкой — он вне
#: зоны этого захода, и наложение сделано ЗДЕСЬ, там, где календарь уже в руках.
KLETKA_PUSTAYA = '<td class="ist-pusta"></td>'


def _tablitsa_shkolnikov(students, teachers_by_id, istoriya, rody, dni, mozhno_pravit=False) -> str:
    est = set(istoriya.dni)
    # Всплывающая подсказка клетки — тоже фраза о человеке, и род у неё тот же.
    # Считается по разу на школьника, а не по разу на клетку: клеток 57 × 16.
    ne_byl = {u["id"]: v_rode(u["name"], "не был", "не была", u["surname"])
              for u in students}
    byl_bez = {u["id"]: v_rode(u["name"], "был, но принимающий не назначен",
                               "была, но принимающий не назначен", u["surname"])
               for u in students}
    stroki = []
    for u in students:
        po_dnyam = istoriya.shkolniki.get(u["id"], {})
        kletki = []
        for den in dni:
            yacheika = po_dnyam.get(den)
            if den not in est:
                kletki.append(KLETKA_PUSTAYA)
            elif yacheika is None or not yacheika.prisutstvoval:
                kletki.append(_kletka("ist-net", "✕", ne_byl[u["id"]],
                                      den, "shk", u["id"], ugolok=mozhno_pravit))
            elif yacheika.nekuda_det:
                kletki.append(_kletka("ist-def", "?", byl_bez[u["id"]],
                                      den, "shk", u["id"]))
            else:
                prep = teachers_by_id.get(yacheika.prepodavatel_id)
                initsialy = _initsialy(prep) if prep else "?"
                polnoe = e(prep["name"]) if prep else "принимающий неизвестен"
                kletki.append(_kletka("ist-byl", e(initsialy), polnoe,
                                      den, "shk", u["id"]))
        stroki.append(
            f'<tr><td class="ist-kto"><b>{e(u["surname"])}</b> {e(u["name"])}</td>'
            f'{"".join(kletki)}</tr>')
    return (f'<div class="ist-prokrutka"><table class="ist-tabl"><thead><tr>'
            f'{_shapka(dni, rody, "Школьник")}</tr></thead>'
            f'<tbody>{"".join(stroki)}</tbody></table></div>')


def otmetki_prisutstviya_po_dnyam(c) -> dict:
    """`{teacher_id: {день, …}}` — где человек отмечен «был» РУКОЙ.

    Нужна, чтобы ручная правка одной даты перевешивала постоянное правило «по
    четвергам не приходит»: владелец назвал эту возможность прямо — «пока не
    изменится текущее распределение или кто-то руками не поправит текущее
    распределение на одну из дат».
    """
    po: dict = {}
    for r in c.execute(
            "select ta.teacher_id tid, s.held_on den from teacher_attendance ta "
            "join sessions s on s.id = ta.session_id where ta.status = ?", ("был",)):
        tid = r["tid"] if hasattr(r, "keys") else r[0]
        den = r["den"] if hasattr(r, "keys") else r[1]
        po.setdefault(tid, set()).add(den)
    return po


def postoyanno_ne_prihodit(c) -> dict:
    """`{slot: {teacher_id, …}}` — кто НЕ ХОДИТ в этот слот вообще, всегда.

    🔴 ТРЕТИЙ ИСТОЧНИК ТОГО ЖЕ ФАКТА, И ЖУРНАЛ ОБЯЗАН ЕГО ЧИТАТЬ. Владелец 11.09:
    «в постоянном распределении зафиксировано, что по четвергам Ольга не в школе —
    это должно передаваться в текущее распределение на все будущие четверги и
    фиксироваться в журнале, то есть у неё во все четверги должны стоять крестики.
    Но не стоят». Факт лежит в `prepodavatel_ne_prihodit (teacher_id, slot)` —
    замер боевой базы 11.09: ровно одна строка, Ольга Рыжая, слот 2 (четверг).
    Распределение её читает (`core/services/sostav_na_den`), журнал — не читал.

    ПОРЯДОК СИЛЫ, И ОН ЕДИНСТВЕННЫЙ ЧЕСТНЫЙ: отметка на КОНКРЕТНУЮ дату
    (`teacher_attendance`) сильнее постоянного правила — иначе «поправить руками
    одну дату» стало бы невозможно, а владелец назвал эту возможность прямо.
    """
    po: dict = {}
    for r in c.execute("select teacher_id, slot from prepodavatel_ne_prihodit"):
        tid = r["teacher_id"] if hasattr(r, "keys") else r[0]
        sl = r["slot"] if hasattr(r, "keys") else r[1]
        po.setdefault(sl, set()).add(tid)
    return po


def otmetki_otsutstviya_po_dnyam(c) -> dict:
    """`{teacher_id: {день, …}}` — где человек отмечен «не был/не будет».

    🔴 ОДНА ТАБЛИЦА НА ТРИ ПАНЕЛИ. В `teacher_attendance` пишут ВСЕ трое: личный
    кабинет (`veb/razdely/kabinet.py`), текущее распределение
    (`veb/server.py::_post_zanyatie`) и этот журнал. Читать её обязаны тоже все, и
    именно поэтому чтение вынесено сюда одной функцией, а не повторено запросом в
    каждом месте: разошедшиеся копии одного факта — это ровно то, что владелец
    запретил 11.09 («должно быть ровно одно место»).
    """
    po: dict = {}
    for r in c.execute(
            "select ta.teacher_id tid, s.held_on den from teacher_attendance ta "
            "join sessions s on s.id = ta.session_id where ta.status = ?",
            ("не был",)):
        tid = r["tid"] if hasattr(r, "keys") else r[0]
        den = r["den"] if hasattr(r, "keys") else r[1]
        po.setdefault(tid, set()).add(den)
    return po


def _tablitsa_prepodavatelej(teachers, students_by_id, istoriya, rody, dni,
                             ots_po_dnyam=None, mozhno_pravit=False,
                             soedinenie_istorii=None) -> str:
    """Журнал преподавателей. Клетка дня отмеченного периода — СВОЕГО вида.

    🔴 ТРИ СОСТОЯНИЯ, А НЕ ДВА, И СПУТАТЬ ИХ НЕЛЬЗЯ (задание §3). `✕` значит «не
    был» — человек должен был прийти и не пришёл; `О` значит «его и не ждали, это
    отмеченный период»; пустая клетка значила бы «не отмечено». Раньше первые два
    выглядели одинаково, то есть журнал, ПО КОТОРОМУ СЧИТАЕТСЯ ЗАРПЛАТА, не
    отличал прогул от согласованного отсутствия.

    🔴 ПЕРИОД ПОБЕЖДАЕТ ОТМЕТКУ ПРИСУТСТВИЯ, И ЭТО НАМЕРЕННО. Если на день периода
    всё-таки стоит `teacher_attendance`-строка «был», сильнее человек, который
    отметил период: он говорил про весь отрезок, а строка присутствия могла
    приехать автоматом. Случай виден во всплывающей подсказке — она называет
    причину и сам период, — а не скрыт.
    """
    ots_po_dnyam = ots_po_dnyam or {}
    est = set(istoriya.dni)
    stroki = []
    # `{teacher_id: {день, …}}` — отметки «не был/не будет» из ЕДИНОЙ таблицы явки,
    # включая дни, до которых история ещё не дошла (будущее).
    net_po_prepam = (otmetki_otsutstviya_po_dnyam(soedinenie_istorii)
                     if soedinenie_istorii is not None else {})
    byl_po_prepam = (otmetki_prisutstviya_po_dnyam(soedinenie_istorii)
                     if soedinenie_istorii is not None else {})
    ne_hodit = (postoyanno_ne_prihodit(soedinenie_istorii)
                if soedinenie_istorii is not None else {})
    from core.services.sostav_na_den import slot_of
    for t in teachers:
        po_dnyam = istoriya.prepodavateli.get(t["id"], {})
        otmecheno_net = net_po_prepam.get(t["id"], frozenset())
        otmecheno_byl = byl_po_prepam.get(t["id"], frozenset())
        kletki = []
        for den in dni:
            svoi_periody = [x for x in ots_po_dnyam.get(den, ())
                            if x["teacher_id"] == t["id"]]
            if svoi_periody:
                kletki.append(_kletka(
                    "ist-otsut", "✕",
                    e("отсутствует · " + "; ".join(
                        _podpis_perioda(x) for x in svoi_periody)),
                    den, "prep", t["id"], ugolok=mozhno_pravit))
                continue
            # Постоянное «по четвергам не приходит» — крестик на КАЖДЫЙ такой день,
            # пока конкретная дата не поправлена рукой.
            sl_dnya = slot_of(den)
            if (sl_dnya in ne_hodit and t["id"] in ne_hodit[sl_dnya]
                    and den not in otmecheno_byl):
                kletki.append(_kletka(
                    "ist-otsut", "✕",
                    v_rode(t["name"], "по этим дням не приходит",
                           "по этим дням не приходит"),
                    den, "prep", t["id"], ugolok=mozhno_pravit))
                continue
            yacheika = po_dnyam.get(den)
            if den in otmecheno_byl and den not in est:
                # Рука сказала «будет» на дату, где правило говорит обратное —
                # показываем галочку, иначе снятое исключение выглядит как пустота
                # и человек не видит, что его правка сохранилась.
                kletki.append(_kletka("ist-byl", "✓",
                                      v_rode(t["name"], "будет", "будет"),
                                      den, "prep", t["id"], ugolok=mozhno_pravit))
                continue
            if den in otmecheno_net and den not in est:
                # 🔴 ЕДИНЫЙ ИСТОЧНИК ПРАВДЫ, И ЖУРНАЛ ЧИТАЕТ ЕГО ДАЖЕ ДЛЯ БУДУЩЕГО.
                # Требование владельца 11.09: «ровно одно место, которое
                # редактируется из трёх панелей… и изменение отображается сразу в
                # этих трёх местах». Разрыв найден замером: «его не будет 14.09»,
                # поставленное из РАСПРЕДЕЛЕНИЯ, легло в `teacher_attendance`, а
                # журнал рисовал ту же клетку пустой — он эту таблицу для будущих
                # дней не спрашивал вовсе.
                kletki.append(_kletka("ist-otsut", "✕",
                                      v_rode(t["name"], "его не будет", "её не будет"),
                                      den, "prep", t["id"], ugolok=mozhno_pravit))
                continue
            if den not in est:
                # 🔴 БУДУЩИЙ ДЕНЬ — ЭТО МЕСТО ДЛЯ ОТМЕТКИ, А НЕ ДЫРКА.
                # Владелец 11.09: «просто чтобы я мог кликнуть на клеточку в
                # расписании на будущее, и там появился бы крестик». Поэтому
                # пустая клетка будущего дня кликабельна и несёт свой адрес;
                # форма с полями «кто · с · по · почему» удалена целиком — она
                # спрашивала то, что клик говорит сам.
                if not mozhno_pravit:
                    kletki.append(KLETKA_PUSTAYA)
                    continue
                # 🔴 И ЗДЕСЬ ТОЖЕ ТОЛЬКО УГОЛОК. Владелец 11.09, повторно: «нажатие
                # на галочку меняет её на крестик, а я просил, чтобы нажатие
                # показывало, у кого принимал преподаватель, а где-то в углу было
                # маленькое место, куда можно нажать и переключить». Значит правило
                # ОДНО для всех трёх видов клетки: тело — показать, уголок — править.
                kletki.append(_kletka("ist-vpered", "",
                                      v_rode(t["name"], "его не будет?", "её не будет?"),
                                      den, "prep", t["id"], ugolok=mozhno_pravit))
            elif yacheika is None or not yacheika.prisutstvoval:
                kletki.append(_kletka(
                    "ist-net", "✕",
                    v_rode(t["name"], "не был", "не была"),
                    den, "prep", t["id"], ugolok=mozhno_pravit))
            else:
                imena = ", ".join(
                    _imya_shkolnika(students_by_id[sid])
                    for sid in yacheika.ucheniki if sid in students_by_id)
                kletki.append(_kletka(
                    "ist-byl", "✓", e(imena) or "никого",
                    den, "prep", t["id"], ugolok=mozhno_pravit))
        stroki.append(
            f'<tr><td class="ist-kto"><b>{e(t["name"])}</b></td>{"".join(kletki)}</tr>')
    return (f'<div class="ist-prokrutka"><table class="ist-tabl"><thead><tr>'
            f'{_shapka(dni, rody, "Преподаватель")}</tr></thead>'
            f'<tbody>{"".join(stroki)}</tbody></table></div>')


def _chto_raskryvaetsya(students, teachers, istoriya, sdachi, dni) -> dict:
    """Содержимое раскрытия каждой клетки — одним словарём, а не в самих клетках.

    🔴 ПОЧЕМУ ОТДЕЛЬНЫМ БЛОКОМ, А НЕ СПРЯТАННЫМ `<div>` В КАЖДОЙ КЛЕТКЕ. Решётка
    это школьники × занятия: 57 × N. К маю N около семидесяти, то есть четыре
    тысячи клеток, и спрятанная разметка в каждой удвоила бы документ ради того,
    что читатель откроет три раза. Словарь несёт то же самое один раз.

    🔴 И ПОЧЕМУ РАСКРЫТИЕ — КЛИК, А НЕ ЧЕКБОКС НА КЛЕТКУ. Чисто-CSS раскрытие
    требует `<input>` на каждую клетку — те же четыре тысячи узлов. Наведение
    (`title`) при этом остаётся на месте и работает без JS: страница без скриптов
    по-прежнему называет, у кого школьник был.
    """
    imena_prepov = {t["id"]: t["name"] for t in teachers}
    imena_detej = {u["id"]: _imya_shkolnika(u) for u in students}
    students_po_id = {u["id"]: u for u in students}
    # Только те дни решётки, о которых запись ЕСТЬ: пустая клетка не кликается, и
    # содержимое для неё было бы мёртвым весом в каждом ответе страницы.
    dni = tuple(d for d in dni if d in set(istoriya.dni))
    itog: dict = {}
    for u in students:
        po_dnyam = istoriya.shkolniki.get(u["id"], {})
        for den in dni:
            ya = po_dnyam.get(den)
            sdal = sdachi.get((den, u["id"]), ())
            komu = (imena_prepov.get(ya.prepodavatel_id)
                    if ya is not None and ya.prisutstvoval else None)
            itog["shk|%s|%s" % (den, u["id"])] = {
                "kto": imena_detej[u["id"]],
                "byl": bool(ya is not None and ya.prisutstvoval),
                "komu": komu,
                # 🔴 СЛОВА, КОТОРЫЕ МЕНЯЮТСЯ ПО РОДУ, СОБИРАЮТСЯ ЗДЕСЬ, А НЕ В
                # БРАУЗЕРЕ. Род выводится из имени (`karkas.rod_imeni`), имя есть
                # только на сервере, и посылать в JSON ещё и род значило бы
                # посылать промежуточный ответ вместо готового. Поэтому в клетку
                # уезжает уже согласованная строка.
                "prinyal": ("принимающий не назначен" if not komu
                            else "%s %s" % (v_rode(komu, "принимал", "принимала"),
                                            komu)),
                "ne_byl": v_rode(u["name"], "не был", "не была", u["surname"]),
                "ne_sdal": v_rode(u["name"], "ничего не сдал", "ничего не сдала",
                                  u["surname"]),
                "sdal": [{"zadacha": z, "listok": l} for z, l, _tid in sdal],
            }
    for t in teachers:
        po_dnyam = istoriya.prepodavateli.get(t["id"], {})
        for den in dni:
            ya = po_dnyam.get(den)
            deti = []
            if ya is not None and ya.prisutstvoval:
                for sid in ya.ucheniki:
                    if sid not in imena_detej:
                        continue
                    rebyonok = students_po_id[sid]
                    deti.append({
                        "kto": imena_detej[sid],
                        "ne_sdal": v_rode(rebyonok["name"], "ничего не сдал",
                                          "ничего не сдала", rebyonok["surname"]),
                        "sdal": [{"zadacha": z, "listok": l}
                                 for z, l, tid in sdachi.get((den, sid), ())
                                 if tid is None or tid == t["id"]],
                    })
            itog["prep|%s|%s" % (den, t["id"])] = {
                "kto": t["name"],
                "byl": bool(ya is not None and ya.prisutstvoval),
                "ne_prinimal": v_rode(t["name"], "в этот день не принимал",
                                      "в этот день не принимала"),
                "deti": deti,
            }
    return itog


# ──────────────────────────────────── ОТСУТСТВИЕ ПРЕПОДАВАТЕЛЯ: РАЗБОР И ФОРМА


def _dni_perioda(s_daty: str, po_datu: str) -> tuple:
    """Все календарные дни периода, ОБА КОНЦА ВКЛЮЧЕНЫ: `('2026-10-01', …, '2026-10-12')`.

    🔴 ВСЕ ДНИ, А НЕ ТОЛЬКО ДНИ ЗАНЯТИЙ, И ЭТО НЕ ИЗБЫТОЧНОСТЬ. Владелец отмечает
    период жизни человека («её физически нет»), а не расписание: он говорит «с
    первого по двенадцатое», и двенадцать клеток на экране — это его двенадцать
    дней. Сузив полосу до пн/чт, экран показал бы четыре клетки на период из
    двенадцати дней, и сверить его со словами владельца стало бы нечем.
    """
    from datetime import date, timedelta

    nachalo, konec = date.fromisoformat(s_daty), date.fromisoformat(po_datu)
    dni, d = [], nachalo
    while d <= konec:
        dni.append(d.isoformat())
        d += timedelta(days=1)
    return tuple(dni)


def _dlina_perioda(s_daty: str, po_datu: str) -> int:
    return len(_dni_perioda(s_daty, po_datu))


def _po_dnyam_otsutstvija(periody) -> dict:
    """`{ISO-день: (период, …)}` — разложенные по дням отметки.

    Одно чтение базы разворачивается здесь один раз, и дальше и решётка, и полоса
    спрашивают готовый словарь. Пересечения периодов законны (`migrations/013`
    их не запрещает), поэтому значение — КОРТЕЖ: «болезнь» и объявленный позже
    «отъезд» на те же дни оба остаются названными.
    """
    itog: dict = {}
    for per in periody:
        for den in _dni_perioda(per["s_daty"], per["po_datu"]):
            itog.setdefault(den, []).append(per)
    return {k: tuple(v) for k, v in itog.items()}


def _podpis_perioda(per: dict) -> str:
    """`болезнь · 01.10–12.10` — то, что стоит во всплывающей подсказке клетки."""
    return "%s · %s–%s" % (per["prichina"], _kratko(per["s_daty"]),
                           _kratko(per["po_datu"]))


def _forma_otsutstvia(teachers) -> str:
    """Окно «Отметить отсутствие»: кто, с какой даты, по какую, почему.

    🔴 ФОРМА СТОИТ В ЖУРНАЛЕ ПРЕПОДАВАТЕЛЕЙ, И МЕСТО НАЗВАНО САМИМ ЗАДАНИЕМ
    («Из журнала преподавателей: выбрать преподавателя, назвать период,
    сохранить»). Это же и единственный экран, на котором человека видно по дням:
    отметив период, организатор видит его действие тут же, не уходя со страницы.

    🔴 НИКАКОГО «НЕ РАНЬШЕ СЕГОДНЯ» У ПОЛЕЙ ДАТ НЕТ, И ЭТО ТРЕБОВАНИЕ, А НЕ
    НЕДОСМОТР: «Работает и назад („заболел сегодня“), и вперёд („не будет с 1 по
    12 октября“)». Атрибут `min` на поле даты запретил бы ровно первый случай.
    """
    opts = "".join(f'<option value="{t["id"]}">{e(t["name"])}</option>'
                   for t in teachers)
    prichiny = "".join(f'<option value="{e(x)}">{e(x)}</option>'
                       for x in PRICHINY_OTSUTSTVIYA)
    return f"""
<form class="ots-forma" id="ots-forma" autocomplete="off">
  <h3>Отметить отсутствие</h3>
  <p class="ots-zachem">Человека не будет в эти дни — он исчезнет из списка
     принимающих на каждый день периода, в обеих версиях распределения.</p>
  <div class="ots-polya">
    <label>кто<select name="teacher_id" id="ots-kto" required>{opts}</select></label>
    <label>с<input type="date" name="s_daty" id="ots-s" required></label>
    <label>по<input type="date" name="po_datu" id="ots-po" required></label>
    <label>почему<select name="prichina" id="ots-prichina">{prichiny}</select></label>
    <button type="submit" class="ots-knopka">Отметить</button>
  </div>
  <p class="ots-oshibka" id="ots-oshibka" hidden></p>
</form>"""


def _siroty_stroka(siroty) -> str:
    """Одна строка про детей, оставшихся без принимающего, — и ничего больше.

    🔴 СПИСОК ПЕРИОДОВ И ФОРМА УДАЛЕНЫ ПО ТРЕБОВАНИЮ ВЛАДЕЛЬЦА 11.09 («всё, что
    на втором скриншоте, надо удалить»). Отметка теперь живёт В КЛЕТКЕ: клик по
    будущему дню ставит крестик, клик по крестику снимает. Пояснительной прозы
    над таблицей не остаётся вовсе — её место заняла подсказка самой клетки.
    Единственное, что печатается, — предупреждение о детях, оставшихся без
    принимающего: это следствие отметки, которого человек не видит в решётке.
    """
    deti = [r for spisok in siroty.values() for r in spisok]
    if not deti:
        return ""
    return _stroka_bez_prinimayushchego(deti)


def _spisok_periodov(periody, teachers_by_id, siroty, mozhno_pravit=False) -> str:
    """Уже отмеченные периоды, поимённо — и со снятием ТОЛЬКО у того, кто правит.

    Пустой список говорит об этом словами: строка «отметок нет» отличима от
    страницы, на которой список просто не нарисовался.

    🔴 `mozhno_pravit` СТОИТ ЗДЕСЬ ПОТОМУ, ЧТО КНОПКА «СНЯТЬ» РИСОВАЛАСЬ ВСЕМ, И
    ЭТО НАШЁЛ ВЕРИФИКАТОР, А НЕ ЧТЕНИЕ. Замер: под ролью `prepod` страница
    `/istoria` честно прятала форму отметки и при этом показывала ТРИ кнопки
    «снять» на три периода. Дверь нажатие отбивала (403, проверено четырьмя
    запросами), то есть данные не пострадали бы никогда, — но орган правки,
    показанный тому, кто править не может, это обещание действия, которого не
    будет, и ровно то, что запрещает докстринг `stranica()` двадцатью строками
    ниже. Видеть отметку преподаватель обязан: его отсутствие — факт про него.
    """
    if not periody:
        return '<p class="ots-pusto">отметок об отсутствии нет</p>'

    def knopka_snyat(per: dict) -> str:
        if not mozhno_pravit:
            return ""
        return ('<button type="button" class="ots-snyat" data-id="%d">снять</button>'
                % per["id"])

    stroki = []
    for per in periody:
        kto = teachers_by_id.get(per["teacher_id"])
        imya = e(kto["name"]) if kto else "преподаватель №%d" % per["teacher_id"]
        stroki.append(
            f'<li class="ots-zapis"><b>{imya}</b>'
            f'<span class="ots-srok">{e(_kratko(per["s_daty"]))}'
            f'&#8202;–&#8202;{e(_kratko(per["po_datu"]))}</span>'
            f'<span class="ots-prichina">{e(per["prichina"])}</span>'
            f'<span class="ots-skolko">{_dlina_perioda(per["s_daty"], per["po_datu"])}&nbsp;дн.</span>'
            f'{knopka_snyat(per)}'
            f'{_polosa_dnej(per)}'
            f'{_stroka_bez_prinimayushchego(siroty.get(per["id"], ()))}'
            f'</li>')
    return '<ul class="ots-spisok">' + "".join(stroki) + "</ul>"


def _polosa_dnej(per: dict) -> str:
    """Полоса дней ОДНОГО периода: по клетке на каждый календарный день.

    🔴 ЗАЧЕМ ОНА НУЖНА СВЕРХ РЕШЁТКИ, И ЭТО НЕ УКРАШЕНИЕ, А ЕДИНСТВЕННЫЙ СПОСОБ
    ПОКАЗАТЬ БУДУЩИЙ ПЕРИОД. Столбцы решётки — ПРОШЕДШИЕ занятия:
    `IstoriyaService.sostavit` разворачивает `sessions`, а строки `sessions` на
    будущее не существует до самого занятия. Живой случай владельца — 01–12.10,
    то есть целиком впереди: в решётке у него НОЛЬ столбцов, и «выделить клетки
    периода» там физически нечего. Полоса и есть те двенадцать клеток особого
    вида, которые называет критерий готовности.

    Клетка полосы НЕСЁТ ТОТ ЖЕ КЛАСС `ist-otsut`, что и клетка решётки: один вид —
    один класс, иначе «отдельный вид» пришлось бы узнавать в двух местах и они бы
    разошлись при первой же правке цвета.
    """
    kletki = []
    for den in _dni_perioda(per["s_daty"], per["po_datu"]):
        kletki.append(
            f'<span class="ist-otsut ots-den" title="{e(_podpis_perioda(per))}" '
            f'data-den="{e(den)}">{e(_kratko(den))}</span>')
    return '<div class="ots-polosa">' + "".join(kletki) + "</div>"


def _bez_prinimayushchego(c: sqlite3.Connection, per: dict) -> tuple:
    """Дети, у которых на дни периода стоит ИМЕННО этот отсутствующий человек.

    🔴 РЕШЕНИЕ ПО ЗАДАНИЮ §1, И ОНО НАЗВАНО ВСЛУХ: НИЧЕГО НЕ УДАЛЯЕТСЯ.
    Постоянная строка `enrollment` остаётся как стояла. Причина простая: период
    КОНЧАЕТСЯ — тринадцатого она снова на месте, — и стереть закрепление значило
    бы уничтожить факт, который всё ещё верен, ради факта временного. Взамен
    организатору показывается список: «эти дети остались без принимающего».

    СЛОТЫ БЕРУТСЯ ИЗ САМИХ ДНЕЙ ПЕРИОДА, а не вписаны парой «1, 2»: период может
    целиком лечь между занятиями (вторник–среда), и тогда без принимающего не
    остаётся никто — правильный ответ, а не пустая забывчивость.
    """
    from core.services.sostav_na_den import slot_of

    sloty = {slot_of(d) for d in _dni_perioda(per["s_daty"], per["po_datu"])}
    sloty.discard(None)
    if not sloty:
        return ()
    mesta = ",".join("?" * len(sloty))
    ryady = c.execute(
        "select s.id as id, s.surname as surname, s.name as name, e.slot as slot "
        "from enrollment e join students s on s.id = e.student_id "
        "where e.teacher_id = ? and e.valid_to = ? and e.slot in (" + mesta + ") "
        "and (s.status is null or s.status <> 'left') "
        "order by s.surname, s.name",
        (per["teacher_id"], config.OPEN_END_DATE, *sorted(sloty))).fetchall()
    return tuple(dict(r) for r in ryady)


def _stroka_bez_prinimayushchego(deti) -> str:
    """Одна строка под полосой: сколько детей осталось без принимающего и кто.

    Пусто — так и сказано словами. Молчание здесь читалось бы как «никого», а это
    разные вещи: «ни у кого не стоял этот человек» и «список не нарисовался».
    """
    if not deti:
        return ('<p class="ots-sirot-net">на дни периода этот человек ни у кого не '
                'стоит принимающим</p>')
    imena = ", ".join(sorted({_imya_shkolnika(r) for r in deti}))
    return ('<p class="ots-siroty"><b>остались без принимающего: %d</b> — %s</p>'
            % (len({r["id"] for r in deti}), e(imena)))


SVOI_STILI = """
.istoria{max-width:none;padding:.9em 1.2em 1.6em}
.istoria .chetverti{display:inline-flex;margin:0 0 .8rem;vertical-align:middle}
.ist-prokrutka{width:100%}
.ist-tabl{width:100%;table-layout:auto}
.ist-tabl td.ist-kl{min-width:2.4rem}
.istoria h1{display:none}
.ist-vkladki{display:inline-flex;gap:.4rem;margin:0 1.6rem .8rem 0;
  vertical-align:middle;font-family:var(--sans)}
.ist-vkladki label{cursor:pointer;font-weight:600;padding:.35em 1.1rem;border-radius:8px;
  border:1px solid var(--rule);color:var(--muted)}
#iv-shk:checked~.ist-vkladki label[for=iv-shk],
#iv-prep:checked~.ist-vkladki label[for=iv-prep]{color:var(--accent);
  background:var(--accent-soft);border-color:var(--accent)}
#is-shk,#is-prep{display:none}
#iv-shk:checked~#is-shk,#iv-prep:checked~#is-prep{display:block}
.ist-pusto{color:var(--muted)}
/* Решётка «люди × даты» в той же форме, что уже стоит у Кондуита: закреплённая первая
   колонка, узкие клетки дат, никакого горизонтального скролла СТРАНИЦЫ (канон,
   правило 4) — прокручивается сама решётка, в своей обёртке `.ist-prokrutka`.
   🔴 ШИРИНА ТАБЛИЦЫ — `auto`, А НЕ `100%`, И ЭТО ПРЯМОЕ ТРЕБОВАНИЕ ВЛАДЕЛЬЦА 11.09:
   «нужна табличка с УЗКИМИ колонками». При `width:100%` шестнадцать столбцов
   растянулись бы на всю ширину экрана — то есть тем шире, чем больше монитор, —
   и «узкими» перестали бы быть ровно там, где владелец смотрит. Замер на 1440:
   12.5rem имени + 16 × 2.7rem дат = 55.7rem ≈ 890px, прокрутки нет. */
.ist-prokrutka{overflow-x:auto}
/* 🔴 РЕШЁТКА ЗАНИМАЕТ ВЕСЬ ЭКРАН, И ЭТО ТРЕБОВАНИЕ, А НЕ ВКУС. Владелец 11.09,
   дважды: «табличку растянуть на весь экран… клеточки всё ещё очень маленькие, а
   чтобы уголок работал, клетки должны быть большими». Прежняя ширина была `auto` с
   колонкой в 2.7rem: на 1440 решётка занимала меньше двух третей ширины, а клетка
   была размером со знак — попасть в уголок мышью в ней нельзя. Теперь колонки
   делят всю доступную ширину, а клетка имеет рост. */
.ist-tabl{font-size:1rem;width:100%;table-layout:fixed;
  border-collapse:separate;border-spacing:0}
.ist-tabl th.ist-zn{width:auto;padding:.5rem .1rem;text-align:center;font-size:.72rem;
  border-bottom:2px solid var(--rule);border-left:1px solid var(--rule)}
.ist-tabl thead th:first-child{width:13rem}
.ist-tabl td.ist-kl,.ist-tabl td.ist-pusta{height:2.6rem}
.ist-tabl td.ist-kl{cursor:pointer}
/* Клетка дня, о котором записи нет: будущее занятие четверти или прошедшее, но не
   заведённое. Ничего не рисует, ничего не открывает — см. `KLETKA_PUSTAYA`. */
.ist-tabl td.ist-pusta{border-left:1px solid var(--rule);
  border-bottom:1px solid var(--rule)}
.ist-tabl thead th{position:sticky;top:0;z-index:2;background:var(--panel)}
.ist-tabl thead th:first-child{left:0;z-index:3;text-align:left;
  border-bottom:2px solid var(--rule)}
.ist-tabl td.ist-kto{white-space:nowrap;padding:.3rem 1.2rem .3rem 0;font-size:.9rem;
  overflow:hidden;text-overflow:ellipsis;
  position:sticky;left:0;z-index:1;background:var(--bg);border-bottom:1px solid var(--rule)}
.ist-tabl tbody td+td{text-align:center;padding:.42rem .1rem;font-family:var(--sans);
  font-size:.85rem;border-left:1px solid var(--rule);
  border-bottom:1px solid var(--rule)}
.ist-tabl td.ist-byl{color:var(--accent);font-weight:600}
.ist-tabl td.ist-net{color:var(--faint)}
.ist-tabl td.ist-def{color:var(--warm);font-weight:700}
/* Род занятия — ВИДОМ столбца, а не словом в нём (владелец 11.09: «только даты»).
   Обычное занятие не рисует ничего: оно норма. Контрольная выделена, отменённый
   день зачёркнут — исключения видно глазом, и ни одно из них не названо словом. */
.ist-tabl th.ist-zachyot{color:var(--accent);font-weight:700}
.ist-tabl th.ist-otmen{color:var(--muted);text-decoration:line-through}
/* Клетка — МЕСТО: знак и два пустых, поимённо названных гнезда под оценку и
   комментарий. Пустые гнёзда ничего не рисуют и ничего не занимают. */
.ist-tabl td.ist-kl{cursor:pointer}
.ist-tabl td.ist-kl:hover,.ist-tabl td.ist-kl:focus-visible{outline:2px solid var(--accent);
  outline-offset:-2px;border-radius:4px}
.ist-tabl td.ist-kl.ist-otkryta{background:var(--accent-soft)}
.kl-ocenka:empty,.kl-komm:empty{display:none}
.kl-ocenka{font-weight:700;margin-left:.25em}
.kl-komm{color:var(--muted);margin-left:.2em}
/* Раскрытие клетки — одна панель на страницу, снизу; таблица под ней не прыгает. */
.ist-raskrytie{position:sticky;bottom:0;z-index:30;margin:1.2rem 0 0;
  background:var(--panel);border:1px solid var(--rule);border-radius:14px;
  padding:1rem 1.3rem;font-family:var(--sans);box-shadow:0 -2px 14px rgba(0,0,0,.06)}
.ist-raskrytie[hidden]{display:none}
.ist-raskrytie h2{font-size:1.1rem;margin:0 0 .5rem;font-family:var(--sans)}
.ist-raskrytie .ist-zakryt{float:right;cursor:pointer;border:1px solid var(--rule);
  background:none;color:var(--muted);border-radius:8px;padding:.2em .7em;font:inherit}
.ist-raskrytie .ist-nichego{color:var(--muted)}
/* ── ОТСУТСТВИЕ ПРЕПОДАВАТЕЛЯ: форма, список отметок ───────────────────────────
   Форма стоит НАД решёткой, а не под ней: её нажимают до того, как смотрят на
   журнал, и искать её прокруткой за четырьмя тысячами клеток было бы издевательством. */
.ots-forma{border:1px solid var(--rule);border-radius:14px;padding:.9rem 1.1rem;
  margin:0 0 .9rem;background:var(--panel);font-family:var(--sans)}
.ots-forma h3{margin:0 0 .2rem;font-size:1.02rem}
.ots-zachem{color:var(--muted);font-size:.88rem;margin:0 0 .7rem}
.ots-polya{display:flex;flex-wrap:wrap;gap:.7rem 1rem;align-items:flex-end}
.ots-polya label{display:flex;flex-direction:column;gap:.2rem;font-size:.82rem;
  color:var(--muted)}
.ots-polya select,.ots-polya input{font:inherit;font-size:.94rem;padding:.3em .5em;
  border:1px solid var(--rule);border-radius:8px;background:var(--bg);color:inherit}
.ots-knopka{font:inherit;font-weight:600;padding:.42em 1.2em;border-radius:8px;
  border:1px solid var(--accent);background:var(--accent-soft);color:var(--accent);
  cursor:pointer}
.ots-oshibka{color:var(--warm);font-size:.9rem;margin:.6rem 0 0}
.ots-spisok{list-style:none;margin:0 0 1rem;padding:0;font-family:var(--sans);
  font-size:.92rem}
.ots-zapis{display:flex;flex-wrap:wrap;gap:.55rem .9rem;align-items:baseline;
  padding:.32rem 0;border-bottom:1px solid var(--rule)}
.ots-srok{font-variant-numeric:tabular-nums}
.ots-prichina,.ots-skolko{color:var(--muted)}
.ots-snyat{margin-left:auto;font:inherit;font-size:.85rem;cursor:pointer;
  border:1px solid var(--rule);border-radius:8px;background:none;color:var(--muted);
  padding:.12em .7em}
.ots-pusto{color:var(--muted);font-family:var(--sans);font-size:.92rem;margin:0 0 1rem}
/* 🔴 ОТДЕЛЬНЫЙ ВИД КЛЕТКИ, А НЕ ОТТЕНОК КРЕСТИКА. `ist-net` — приглушённый
   `--faint` («не был»), `ist-otsut` — заливка и рамка тёплым: он читается как
   ПОМЕЧЕННЫЙ, а не как слабый. Ровно этого требует §3 задания: пустая клетка уже
   значит «не отмечено», и спутать эти два состояния нельзя. */
.ist-tabl td.ist-otsut{color:var(--warm);font-weight:700;
  background:color-mix(in srgb, var(--warm) 14%, transparent)}
.ots-polosa{display:flex;flex-wrap:wrap;gap:.22rem;margin:.45rem 0 .1rem;
  flex-basis:100%}
.ist-otsut.ots-den{display:inline-block;font-size:.72rem;font-weight:700;
  font-variant-numeric:tabular-nums;padding:.16em .42em;border-radius:6px;
  color:var(--warm);border:1px solid var(--warm);
  background:color-mix(in srgb, var(--warm) 14%, transparent)}
.ist-vpered{cursor:pointer}
.ist-kl{position:relative}
/* Уголок — своя зона нажатия, не «символ рядом»: у него есть площадь (минимум
   палец на телефоне), он прижат к правому нижнему углу и проявляется на наведении.
   Тело клетки остаётся под главный жест — «показать, у кого принимал». */
.kl-ugol{position:absolute;right:0;bottom:0;width:1.15rem;height:1.15rem;
  display:flex;align-items:center;justify-content:center;font-size:.8rem;line-height:1;
  color:var(--muted);opacity:.25;cursor:pointer;border-top-left-radius:6px}
.ist-kl:hover .kl-ugol{opacity:.75;background:color-mix(in srgb, var(--warm) 18%, transparent)}
.kl-ugol:hover{opacity:1;color:var(--warm);background:color-mix(in srgb, var(--warm) 32%, transparent)}
.ist-vpered:hover{background:color-mix(in srgb, var(--warm) 10%, transparent)}
.ots-klik{cursor:pointer}
.ots-zhdyot{opacity:.45}
.ist-otsut .kl-znak{color:var(--warm);font-weight:700}
.ots-siroty{flex-basis:100%;margin:.3rem 0 0;font-size:.88rem;color:var(--warm)}
.ots-sirot-net{flex-basis:100%;margin:.3rem 0 0;font-size:.88rem;color:var(--muted)}
.ist-raskrytie .ist-komu{margin:0 0 .5rem;font-weight:600}
.ist-raskrytie .ist-rebyonok{padding:.35rem 0;border-top:1px solid var(--rule)}
.ist-raskrytie .ist-rebyonok:first-of-type{border-top:none}
.ist-raskrytie .ist-imya{margin:0;font-weight:600}
.ist-zhurnal{margin:0 0 .8rem;font-family:var(--sans);font-size:1.15rem;font-weight:600}
@media(max-width:760px){
  .istoria{padding-left:1.1rem;padding-right:1.1rem}
  .ist-tabl td.ist-kto{width:7rem;max-width:7rem;overflow:hidden;text-overflow:ellipsis;
    white-space:nowrap}
}
"""


#: 🔴 ИМЯ ЖУРНАЛА — ОДНА СТРОКА, И ПОЯСНЕНИЯ ПОД НЕЙ БОЛЬШЕ НЕТ. Здесь стояла
#: пара «имя + зачем»: «посещения и сдача. Сюда же пойдут оценки — прообраз личного
#: кабинета» и «кто в какой день был. По нему считается зарплата — цена ошибки в
#: клетке не в отображении, а в деньгах». Владелец 11.09, глядя на живой экран, назвал
#: ровно эти две строки: «опять какие-то странные подписи сверху, которых не надо
#: делать… выкидываем все комментарии, это ужасно, это нельзя людям показывать».
#: Почему они вообще появились, записано выше по истории файла и остаётся ВЕРНЫМ —
#: два журнала действительно две разные вещи с разной ценой ошибки. Но объяснять это
#: читателю СТРОКОЙ НА ЭКРАНЕ он запретил прямо; объяснение живёт здесь, в коде.
IMYA_ZHURNALA = {"shk": "Журнал школьников", "prep": "Журнал преподавателей"}

#: Раскрытие клетки. Одна панель на страницу и один обработчик на таблицу: клетка
#: называет себя тремя значениями (`data-den`, `data-vid`, `data-kto`), панель по ним
#: находит своё содержимое в блоке `ist-dannye`. Наведение (`title`) остаётся и без
#: скрипта — страница без JS по-прежнему называет, у кого школьник был.
SKRIPT = """
<script>
(function(){
  var uzel = document.getElementById('ist-dannye');
  var dannye = uzel ? JSON.parse(uzel.textContent) : {};
  var panel = document.getElementById('ist-raskrytie');
  var telo = document.getElementById('ist-raskrytie-telo');
  var zag = document.getElementById('ist-raskrytie-zag');
  var otkryta = null;

  // 🔴 ВИД СДАЧИ БОЛЬШЕ НЕ ЖИВЁТ ЗДЕСЬ. Он один на весь сайт и лежит в
  // `karkas.SDACHI_SKRIPT` — та же строка на листок и те же задачи кнопками, что
  // просил владелец 11.09 и что показывает плитка кабинета. Здесь остаётся только
  // зов: две копии одного списка разошлись бы молча.
  var sdachi = window.Kluchiki.sdachiPoListkam;
  function zakryt(){
    panel.hidden = true;
    if (otkryta) { otkryta.classList.remove('ist-otkryta'); otkryta = null; }
  }
  function pokazat(kletka){
    var klyuch = kletka.dataset.vid + '|' + kletka.dataset.den + '|' + kletka.dataset.kto;
    var d = dannye[klyuch];
    if (!d) return;
    if (otkryta) otkryta.classList.remove('ist-otkryta');
    otkryta = kletka; kletka.classList.add('ist-otkryta');
    zag.textContent = d.kto + ' · ' + kletka.dataset.den;
    if (kletka.dataset.vid === 'shk') {
      // Слова уже согласованы по роду на сервере (`_chto_raskryvaetsya`): здесь
      // печатается готовая строка, а не собирается фраза из кусков.
      telo.innerHTML = !d.byl
        ? '<p class="ist-nichego">на этом занятии ' + d.ne_byl + '</p>'
        : '<p class="ist-komu">' + d.prinyal + '</p>'
          + sdachi(d.sdal, 'в этот день ' + d.ne_sdal);
    } else {
      telo.innerHTML = !d.byl
        ? '<p class="ist-nichego">' + d.ne_prinimal + '</p>'
        : (d.deti.length
             ? d.deti.map(function(r){
                 return '<div class="ist-rebyonok"><p class="ist-imya">' + r.kto + '</p>'
                      + sdachi(r.sdal, r.ne_sdal) + '</div>';
               }).join('')
             : '<p class="ist-nichego">в этот день никого</p>');
    }
    panel.hidden = false;
  }
  document.addEventListener('click', function(sob){
    var kletka = sob.target.closest ? sob.target.closest('td.ist-kl') : null;
    if (kletka) { pokazat(kletka); return; }
    if (sob.target.closest && sob.target.closest('#ist-raskrytie')) return;
    zakryt();
  });
  document.addEventListener('keydown', function(sob){
    if (sob.key === 'Escape') zakryt();
    if ((sob.key === 'Enter' || sob.key === ' ')
        && sob.target.classList && sob.target.classList.contains('ist-kl')) {
      sob.preventDefault(); pokazat(sob.target);
    }
  });
  document.getElementById('ist-zakryt').addEventListener('click', zakryt);
})();
</script>"""


#: Форма отсутствия. Отдельный блок, а не ветка в `SKRIPT`: тот раскрывает клетки
#: и не пишет в базу вовсе, а этот — единственное место страницы, которое ПИШЕТ.
#: Смешав их, следующий читатель искал бы дверь записи внутри обработчика клика по
#: клетке.
SKRIPT_OTSUTSTVIE = """
<script>
(function(){
  /* 🔴 ОТМЕТКА ЖИВЁТ В КЛЕТКЕ, А НЕ В ФОРМЕ. Владелец 11.09: «просто чтобы я мог
     кликнуть на клеточку в расписании на будущее, и там появился бы крестик».
     Форма «кто · с · по · почему» удалена целиком: три её поля из четырёх клетка
     знает о себе сама (кто — строка, день — колонка), а четвёртое спрашивать не
     о чем. Повторный клик по крестику снимает отметку. */
  var tablica = document.getElementById('is-prep');
  if(!tablica) return;
  tablica.addEventListener('click', function(sob){
    var kl = sob.target.closest('.ots-klik');
    if(!kl) return;
    /* 🔴 ГЛУШИМ ВСПЛЫТИЕ: по клетке слушает ещё и раскрытие кондуита
       (`td.ist-kl` в основном скрипте). Без этого клик по уголку разом правил бы
       явку И открывал панель — два ответа на один жест. */
    sob.preventDefault();
    sob.stopPropagation();
    var yach = kl.closest('td.ist-kl') || kl;
    var den = yach.getAttribute('data-den'), kto = yach.getAttribute('data-kto');
    if(!den || !kto) return;
    yach.classList.add('ots-zhdyot');
    fetch('/api/otsutstvie', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({teacher_id: Number(kto), den: den})
    }).then(function(o){
      return o.json().catch(function(){ return {}; }).then(function(d){
        if(!o.ok){ yach.classList.remove('ots-zhdyot'); alert(d.error || ('не вышло: ' + o.status)); return; }
        /* перечитываем страницу целиком: отметка меняет и клетку, и списки
           принимающих на обеих версиях распределения — держать второе описание
           того же факта в браузере значит разойтись с сервером */
        location.reload();
      });
    }).catch(function(){ yach.classList.remove('ots-zhdyot'); alert('сервер не ответил'); });
  });
})();
</script>
"""


def stranica(c: sqlite3.Connection, mozhno_pravit: bool = False,
             chetvert=None, segodnya: str = "") -> str:
    """Вся страница: два журнала на ОДНУ четверть, по одному разу каждый.

    `mozhno_pravit` — рисовать ли форму отметки отсутствия. Она ОРГАН ПРАВКИ, и
    показывать её тому, кому дверь всё равно ответит 403, значит обещать действие,
    которого не будет. Сам порог живёт в двери (`_pravit_nelzya`): форма — только
    его отражение, и её отсутствие ничего не запрещает само по себе.

    `chetvert` — номер 1..4; вне диапазона или `None` значит «та, в которой мы
    сейчас». `segodnya` есть ради теста и ради прогона на дату, отличную от
    сегодняшней; пустая строка значит сегодня.
    """
    segodnya = segodnya or date.today().isoformat()
    vse_chetverti = chetverti_goda(segodnya)
    nomer = chetvert if chetvert in range(1, len(vse_chetverti) + 1) \
        else nomer_chetverti(segodnya)
    dni_setki = vse_chetverti[nomer - 1]

    students, teachers = _spravochniki(c)
    students_by_id = {u["id"]: u for u in students}
    teachers_by_id = {t["id"]: t for t in teachers}
    istoriya, sessii = _sostavit(c)
    rody = _rod_zanyatiya(c, sessii)
    periody = periody_otsutstvij(c)
    ots_po_dnyam = _po_dnyam_otsutstvija(periody)
    siroty = {per["id"]: _bez_prinimayushchego(c, per) for per in periody}
    sdachi = sdachi_po_zanyatiyam(c, dni_setki)
    dannye = _chto_raskryvaetsya(students, teachers, istoriya, sdachi, dni_setki)

    def zagolovok(vid: str) -> str:
        # 🔴 ЗАГОЛОВОК УБРАН ПО ТРЕБОВАНИЮ ВЛАДЕЛЬЦА 11.09: «убери лишние надписи
        # „Журнал преподавателей“ и „остались без принимающего…“». Какая вкладка
        # открыта, видно по самой вкладке — подпись повторяла её и занимала строку.
        # Функция оставлена пустой, а не вырезана: её зовут два места сборки, и
        # удаление тронуло бы их обоих ради нуля пользы.
        return ""

    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Журнал — Ключики</title>
<style>{_obshchij_stil(put_bazy(c))}{CHETVERTI_STILI}{SDACHI_STILI}{SVOI_STILI}</style></head>
<body>
{menyu_ssylkami("/istoria")}
<main class="istoria">
  <!-- 🔴 ПЕРЕКЛЮЧАТЕЛИ СТОЯТ ЗДЕСЬ, ВНУТРИ `<main>`, И ЭТО НЕ ОФОРМЛЕНИЕ — ЭТО
       ПРИЧИНА, ПО КОТОРОЙ СТРАНИЦА БЫЛА МЕРТВА. Два `<input>` лежали в `<body>`,
       ПЕРЕД `<main>`, а панели `#is-shk` / `#is-prep` и метки `.ist-vkladki` —
       внутри него. Комбинатор `~` требует СЕСТРУ; племянница ему не подходит
       никогда. Значит из двух правил работало ровно одно — то, что гасит панели
       (`#is-shk,#is-prep` → display none); второе, `#iv-shk:checked~#is-shk`,
       не совпадало ни при какой отметке. Обе таблицы были невидимы ВСЕГДА, и по той
       же одной причине была мертва подсветка выбранной кнопки. Отсюда слова
       владельца: «кнопки не нажимаются, я ничего не вижу».
       Замер до правки (рендер 1440×900 на копии боевой базы, playwright):
       `#is-shk` → `display:none`, `#is-prep` → `display:none`, видимых строк 0 и 0,
       и клик по «Преподавателям» ничего из этого не менял.
       Починка ОДНА и она здесь: переключатели, метки и панели стали сёстрами.
       Ни одно правило CSS при этом не изменилось — изменилось РОДСТВО узлов. -->
  <input class="rd" type="radio" name="ist-vid" id="iv-shk" checked hidden>
  <input class="rd" type="radio" name="ist-vid" id="iv-prep" hidden>
  <!-- 🔴 ОДНА ПОЛОСА УПРАВЛЕНИЯ ВМЕСТО ТРЁХ ЭТАЖЕЙ. Владелец 11.09: вкладки и
       кнопки четвертей ставятся НА ОДИН УРОВЕНЬ, отдельные подписи убираются,
       имя остаётся только на ярлыке вкладки, а таблица растягивается на весь
       экран. Три строки шапки занимали ровно ту высоту, которой не хватало
       решётке. -->
  <nav class="ist-vkladki" id="ist-vkladki">
    <label for="iv-shk">Школьники</label>
    <label for="iv-prep">Преподаватели</label>
  </nav>
  {perekluchatel_chetvertej("/istoria", nomer, segodnya)}
  <section id="is-shk">{zagolovok("shk")}
    {_tablitsa_shkolnikov(students, teachers_by_id, istoriya, rody, dni_setki, mozhno_pravit)}</section>
  <section id="is-prep">{zagolovok("prep")}
    {_tablitsa_prepodavatelej(teachers, students_by_id, istoriya, rody,
                              dni_setki, ots_po_dnyam, mozhno_pravit, c)}</section>
  <div class="ist-raskrytie" id="ist-raskrytie" hidden>
    <button class="ist-zakryt" id="ist-zakryt" type="button">закрыть</button>
    <h2 id="ist-raskrytie-zag"></h2>
    <div id="ist-raskrytie-telo"></div>
  </div>
</main>
<script type="application/json" id="ist-dannye">{json.dumps(dannye, ensure_ascii=False)}</script>
{SDACHI_SKRIPT}
{SKRIPT}{SKRIPT_OTSUTSTVIE if mozhno_pravit else ''}
{SKRIPT_PAMYAT_VKLADOK}
</body></html>"""


# ────────────────────────────────────────────── ОТМЕТИТЬ ОТСУТСТВИЕ (часть 2)


def _pravit_nelzya(h) -> bool:
    """Тот же порог, что у правящих роутов `veb/server.py::_pravka_zapreshchena`.

    🔴 ПОРОГ СКОПИРОВАН НЕ ОТ ЛЕНИ, А ПОТОМУ ЧТО ЗВАТЬ ОРИГИНАЛ НЕЧЕМ: он МЕТОД
    обработчика (`self._pravka_zapreshchena`), а не функция, и снаружи у него нет
    имени. Копируется при этом ровно условие, включая переключатель
    `SVOBODNAYA_PRAVKA`, — и вот почему он здесь обязателен. Д1 живого прогона:
    `/api/prepodavateli` спрашивал роль напрямую и отвечал 403 ВСЕГДА, потому что
    при выключенном пароле куки никто не ставит и роли нет. Дверь, которая
    отказывает всем, выглядит как мёртвая вкладка, а не как защищённая.

    `SVOBODNAYA_PRAVKA` берётся из `veb.server` ИМПОРТОМ ВНУТРИ ФУНКЦИИ: модуль
    сервера импортирует ЭТОТ модуль (`RAZDELY_S_MARSHRUTAMI`), и импорт наверху
    замкнул бы кольцо. К моменту вызова оба модуля загружены — тот же приём, что
    `karkas.sobrat_kontekst` уже применяет к `veb.razdely.shkolniki`.
    """
    if _mozhno_pravit(h):
        return False
    if vhod.rol(h.headers) is None:
        _otdat_json(h, 403, {"error": "нужно войти"})
    else:
        _otdat_json(h, 403, {"error": "отмечает отсутствие только организатор"})
    return True


def _mozhno_pravit(h) -> bool:
    """Тот же вопрос БЕЗ побочного действия: страница спрашивает его, чтобы решить,
    рисовать ли форму, и ответ «нет» здесь не должен отправлять 403 в середину
    HTML. Дверь выше зовёт эту же функцию, и второго условия в файле нет.
    """
    from veb.server import SVOBODNAYA_PRAVKA

    return bool(SVOBODNAYA_PRAVKA) or vhod.rol(h.headers) == "organizator"


def _telo_zaprosa(h) -> dict:
    """JSON тела запроса; нечитаемое тело — пустой словарь, а не исключение."""
    try:
        syroe = h.rfile.read(int(h.headers.get("Content-Length", 0) or 0))
        return json.loads(syroe or b"{}")
    except (ValueError, TypeError):
        return {}


ISO_DEN = "%Y-%m-%d"


def _den_ili_nichego(znachenie) -> str | None:
    """`'2026-10-01'` → та же строка; что угодно другое → `None`.

    Дата проверяется РАЗБОРОМ, а не длиной строки: `'2026-13-45'` имеет ту же
    длину и тот же вид, и `CHECK` миграции его пропустит — `glob` проверяет форму,
    а не существование дня. Отказ здесь стоит одного `if`; тринадцатый месяц,
    доехавший в базу, стоит поиска по всем страницам, на которых он потом не
    нашёлся.
    """
    if not isinstance(znachenie, str):
        return None
    try:
        datetime.strptime(znachenie, ISO_DEN)
    except ValueError:
        return None
    return znachenie


def dver_otsutstvia(h) -> bool:
    """`/api/otsutstvie` — отметить период и снять отметку. Только POST.

    🔴 МАРШРУТ ОБЪЯВЛЕН ЗДЕСЬ, А НЕ В `veb/server.py`, И ЭТО НЕ ОБХОД ЗОНЫ, А ШОВ,
    КОТОРЫЙ СЕРВЕР САМ ДЛЯ ЭТОГО И ДЕРЖИТ. `_marshruty_razdelov()` спрашивается и в
    `do_GET`, и в `do_POST` — второе добавлено заходом `veb-priyom-zadach` ровно
    потому, что дверь раздела, которая ПИШЕТ, есть POST. Так что раздел, объявивший
    путь, объявил его для обоих методов.

    Два действия и одно тело:
      * `{"teacher_id": 7, "s_daty": "2026-10-01", "po_datu": "2026-10-12",
         "prichina": "болезнь", "zametka": null}` — отметить;
      * `{"snyat": 3}` — снять отметку целиком.
    Разделять их на два пути незачем: это одно окно на экране и одна форма.
    """
    if getattr(h, "command", "POST") != "POST":
        _otdat_json(h, 405, {"error": "только POST"})
        return True
    if _pravit_nelzya(h):
        return True
    p = _telo_zaprosa(h)
    c = _soedinenie(h)
    try:
        # 🔴 КЛИК ПО КЛЕТКЕ — ТРЕТЬЕ ДЕЙСТВИЕ ЭТОЙ ЖЕ ДВЕРИ, И ОНО ПЕРЕКЛЮЧАТЕЛЬ.
        # Владелец 11.09: «просто чтобы я мог кликнуть на клеточку в расписании на
        # будущее, и там появился бы крестик». Клик НЕ спрашивает ни причины, ни
        # второй даты: день известен из самой клетки, период равен одному дню.
        # Повторный клик по крестику снимает отметку — иначе поставить её было бы
        # можно, а убрать нечем, и человек остался бы отсутствующим навсегда.
        if p.get("den") is not None and p.get("snyat") is None:
            den = _den_ili_nichego(p.get("den"))
            if den is None:
                _otdat_json(h, 400, {"error": "нужны даты в виде ГГГГ-ММ-ДД"})
                return True
            try:
                tid = int(p["teacher_id"])
            except (KeyError, TypeError, ValueError):
                _otdat_json(h, 400, {"error": "нужен teacher_id"})
                return True
            est = [x for x in periody_otsutstvij(c)
                   if x["teacher_id"] == tid and x["s_daty"] <= den <= x["po_datu"]]
            if est:
                for x in est:
                    snyat_otsutstvie(c, int(x["id"]))
                _otdat_json(h, 200, {"ok": True, "den": den, "stalo": "снято"})
                return True
            # 🔴 ДЕНЬ, У КОТОРОГО ЕСТЬ ЗАНЯТИЕ, — ЭТО ПРАВКА ЯВКИ, А НЕ ОТСУТСТВИЕ.
            # Владелец 11.09: «сделай возможность менять галочки на крестики
            # постфактум, чтобы я мог отмечать поля, которые заполнены неправильно;
            # поскольку у нас автоматическая система, там могут быть ошибки» и
            # «первое занятие, 3-го, там сейчас нет отметок — одно нажатие галочка,
            # второе крестик». Значит у прошедшего дня ТРИ состояния по кругу:
            # пусто → был → не был → пусто. Отсутствие периодом остаётся способом
            # сказать о БУДУЩЕМ, где занятия ещё нет.
            # 🔴 БУДУЩЕЕ РЕШАЕТСЯ ДАТОЙ, А НЕ НАЛИЧИЕМ СТРОКИ В `sessions`.
            # Живой случай владельца 11.09: «почему-то нету возможности поставить
            # крестик на 14». Замер боевой базы: строка `sessions` на 2026-09-14 УЖЕ
            # ЕСТЬ — её завёл экран кабинета, показывающий «следующий спецмат 14
            # сентября». Прежний порядок вёл такой день в ветку ЯВКИ: отметка ложилась
            # в `teacher_attendance`, а клетка будущего дня её не читает и оставалась
            # пустой. Человек кликал, запись происходила, и на экране не менялось
            # НИЧЕГО — худший вид поломки.
            # 🔴 ОДНО МЕСТО ДЛЯ ФАКТА «ЕГО НЕ БУДЕТ НА ЭТОМ ЗАНЯТИИ» — ТАБЛИЦА ЯВКИ.
            # Требование владельца 11.09: «должно быть ровно одно место, которое
            # редактируется из трёх панелей: личный кабинет, текущее расписание и
            # журнал». Распределение и кабинет пишут в `teacher_attendance`; журнал
            # теперь пишет туда же — и для прошедшего дня, и для будущего. Прежде он
            # заводил на будущий день ПЕРИОД отсутствия, то есть второй ответ на тот
            # же вопрос: у одной клетки было два хозяина, и они расходились.
            # Периоды остаются для многодневных отметок («не будет две недели») —
            # их журнал ЧИТАЕТ и показывает, но новые кликом не заводит.
            segodnya = date.today().isoformat()
            ryad = c.execute("select id from sessions where held_on = ?", (den,)).fetchone()
            if ryad is None:
                # 🔴 ПРОШЕДШИЙ ДЕНЬ БЕЗ ЗАНЯТИЯ В БАЗЕ — ЭТО НЕ БУДУЩЕЕ, А ДЫРА.
                # Владелец 11.09: «первое занятие, 3-го, там сейчас нет отметок — у
                # меня должна быть возможность проставить их вручную». Строка в
                # `sessions` заводится ЛЕНИВО, первым открывшим экран этого дня, и
                # для 03.09 её просто нет. Клик по такой клетке заводит занятие —
                # ровно так же, как это делает отметка из кабинета
                # (`veb/razdely/kabinet.py`: «Занятия ещё нет в базе — его заводит
                # первый экран, открытый на этот день»).
                c.execute("insert into sessions (held_on) values (?)", (den,))
                ryad = c.execute("select id from sessions where held_on = ?", (den,)).fetchone()
            if ryad is not None:
                session_id = ryad["id"] if hasattr(ryad, "keys") else ryad[0]
                tek = c.execute(
                    "select status from teacher_attendance "
                    "where session_id = ? and teacher_id = ?", (session_id, tid)).fetchone()
                tek = (tek["status"] if hasattr(tek, "keys") else tek[0]) if tek else None
                byl, ne_byl = config.ATTENDANCE_STATUSES[0], config.ATTENDANCE_STATUSES[1]
                # 🔴 ДВА СОСТОЯНИЯ, А НЕ ТРИ, И ЭТО ПОПРАВЛЕНО ПОСЛЕ ЖИВОГО ПРОГОНА.
                # Владелец сказал ровно: «одно нажатие галочка, второе крестик».
                # Третий клик я сперва сделала «пусто» — и прогон показал, что в
                # решётке ПУСТО НЕОТЛИЧИМО ОТ КРЕСТИКА: клетка без строки в
                # `teacher_attendance` и так рисуется «не был». Состояние, которого
                # не видно, — это не состояние, а обещание.
                # 🔴 ЦИКЛ НАЧИНАЕТСЯ С ТОГО, ЧТО ЧЕЛОВЕК ВИДИТ, А НЕ С ТОГО, ЧТО
                # ЛЕЖИТ В ТАБЛИЦЕ. Найдено на живом случае, названном владельцем:
                # «поставить крестик у Нади не получается, хотя она не была ни разу».
                # У неё в `teacher_attendance` строки НЕТ — клетка показывает ✓
                # автоматом, потому что на неё записаны принятые задачи. Прежний
                # цикл начинал с «пусто → был», то есть первый клик писал ровно то,
                # что и так на экране, и до крестика было не добраться ВООБЩЕ.
                if tek is None:
                    # Клетка показывает ✓ по ДВУМ причинам: за человеком записаны
                    # принятые задачи этого дня ИЛИ на него назначены школьники в
                    # слоте этого дня. Спрашиваем обе — иначе у того, кто ни разу не
                    # принимал, но стоит в постоянном распределении (случай Нади),
                    # первый клик снова написал бы «был».
                    from core.services.sostav_na_den import slot_of
                    sl = slot_of(den)
                    # 🔴 ОТМЕТКИ ПРИВЯЗАНЫ К ДНЮ ДАТОЙ, А НЕ ЗАНЯТИЕМ. Замер на живой
                    # базе 11.09: `select count(*) from marks where session_id is not
                    # null` → НОЛЬ при 15 900 отметках, тогда как `teacher_id` стоит у
                    # 15 526. Связь «отметка → занятие» в данных не заведена вовсе, и
                    # запрос по `session_id` не нашёл бы ничего никогда.
                    est_zadachi = c.execute(
                        "select 1 from marks where substr(valid_at, 1, 10) = ? "
                        "and teacher_id = ? limit 1", (den, tid)).fetchone() is not None
                    # 🔴 ЧТО ВИДНО НА БУДУЩЕМ ДНЕ, ЗАВИСИТ ОТ ПОСТОЯННОГО ПРАВИЛА.
                    # Обычно клетка будущего пуста → первый клик значит «не будет».
                    # Но если человек по этому слоту НЕ ХОДИТ ВООБЩЕ
                    # (`prepodavatel_ne_prihodit`), клетка уже показывает крестик, и
                    # первый клик обязан значить обратное — «на эту дату будет».
                    # Иначе снять исключение на одну дату нечем, а владелец назвал
                    # эту возможность прямо.
                    from core.services.sostav_na_den import slot_of as _slot
                    _sl = _slot(den)
                    po_pravilu_net = _sl is not None and c.execute(
                        "select 1 from prepodavatel_ne_prihodit "
                        "where teacher_id = ? and slot = ? limit 1",
                        (tid, _sl)).fetchone() is not None
                    if den > segodnya:
                        vidno_galochku = not po_pravilu_net
                        est_zadachi = est_deti = False
                    est_deti = (not (den > segodnya)) and bool(sl) and c.execute(
                        "select 1 from enrollment where teacher_id = ? and slot = ? "
                        "and (valid_from is null or valid_from <= ?) "
                        "and (valid_to is null or valid_to >= ?) limit 1",
                        (tid, sl, den, den)).fetchone() is not None
                    if den <= segodnya:
                        vidno_galochku = (est_zadachi or est_deti) and not po_pravilu_net
                    novoe = ne_byl if vidno_galochku else byl
                else:
                    novoe = ne_byl if tek == byl else byl
                if True:
                    c.execute(
                        "insert or replace into teacher_attendance "
                        "(session_id, teacher_id, status, answered_at) values (?, ?, ?, ?)",
                        (session_id, tid, novoe,
                         datetime.now(ZoneInfo(config.TZ_DISPLAY)).isoformat(timespec="seconds")))
                # 🔴 «ЕГО НЕ БЫЛО» ОБЯЗАНО СНИМАТЬ ЕГО ИМЯ С ПРИНЯТЫХ ЗАДАЧ.
                # Владелец 11.09, дословно: «плюсики, которые ставили её детям другие
                # преподаватели, записали на неё… мы не знаем, кто принимал у её
                # учеников, но самое главное — мы должны знать, что её не было;
                # значит её плюсики будут анонимными, такая возможность тоже должна
                # быть». Иначе отметка «не был» противоречит самим данным: человека
                # не было, а задачи приняты им же. Отметки НЕ УДАЛЯЮТСЯ — сдача
                # школьника была, — у них лишь пропадает ложный принимающий.
                # 🔴 ОБЕЗЛИЧИТЬ ПЛЮСИКИ ЗДЕСЬ НЕЛЬЗЯ, И ЭТО НЕ ЛЕНЬ, А ЗАПРЕТ СХЕМЫ.
                # Владелец 11.09 просил: «её плюсики будут анонимными, такая
                # возможность тоже должна быть». Прямой `update marks set teacher_id
                # = null` ОТКЛОНЁН базой живьём: «marks is append-only: UPDATE
                # forbidden, write a retract or an erratum event instead». Журнал
                # сдач принципиально дописываемый: сдача ребёнка не переписывается
                # задним числом, у неё добавляется событие-исправление. Значит
                # обезличивание — это ПАЧКА СОБЫТИЙ erratum, а не правка строки, и
                # оно трогает журнал сдач; делать это попутно с отметкой явки
                # нельзя. Здесь считается и возвращается ТОЛЬКО ЧИСЛО — сколько
                # плюсиков этого дня всё ещё записаны на него, — чтобы человек видел
                # масштаб и решил отдельно.
                obezlicheno = 0
                na_nyom = c.execute(
                    "select count(*) from marks where substr(valid_at, 1, 10) = ? "
                    "and teacher_id = ?", (den, tid)).fetchone()
                na_nyom = (na_nyom[0] if na_nyom else 0)
                c.commit()
                _otdat_json(h, 200, {"ok": True, "den": den, "stalo": novoe or "пусто",
                                     "plyusikov_na_nyom": na_nyom})
                return True
            otmetit_otsutstvie(c, tid, den, den, PRICHINY_OTSUTSTVIYA[0])
            _otdat_json(h, 200, {"ok": True, "den": den, "stalo": "отмечено"})
            return True
        if p.get("snyat") is not None:
            try:
                snyato = snyat_otsutstvie(c, int(p["snyat"]))
            except (TypeError, ValueError):
                _otdat_json(h, 400, {"error": "нужен числовой id отметки"})
                return True
            c.commit()
            if not snyato:
                _otdat_json(h, 404, {"error": "такой отметки нет"})
                return True
            _otdat_json(h, 200, {"ok": True, "snyato": int(p["snyat"])})
            return True

        syroj_tid = p.get("teacher_id")
        try:
            teacher_id = int(syroj_tid)
        except (TypeError, ValueError):
            _otdat_json(h, 400, {"error": "нужен teacher_id"})
            return True
        s_daty = _den_ili_nichego(p.get("s_daty"))
        po_datu = _den_ili_nichego(p.get("po_datu"))
        if s_daty is None or po_datu is None:
            _otdat_json(h, 400, {"error": "нужны даты в виде ГГГГ-ММ-ДД"})
            return True
        prichina = p.get("prichina") or PRICHINY_OTSUTSTVIYA[0]
        # Преподаватель обязан существовать и быть активным: отметка на снятого
        # человека не влияет ни на один список и потому неотличима от потерянной.
        est = c.execute("select 1 from teachers where id = ? and aktiven = 1",
                        (teacher_id,)).fetchone()
        if est is None:
            _otdat_json(h, 404, {"error": "нет такого действующего преподавателя"})
            return True
        try:
            novyj = otmetit_otsutstvie(
                c, teacher_id, s_daty, po_datu, prichina,
                # 🔴 `vhod.kto` ОТДАЁТ `None` ПРИ ОБЩЕМ ПАРОЛЕ, И ЭТО ИЗВЕСТНОЕ
                # СОСТОЯНИЕ, А НЕ ПОТЕРЯ. `proverit_parol` на общем пароле
                # организатора возвращает `("organizator", None)`, то есть «кто-то
                # из организаторов». Та же `NULL` уже законна в
                # `mark_lesson_override.teacher_id` ровно по этой причине.
                kto_otmetil=vhod.kto(h.headers),
                zametka=(p.get("zametka") or None))
        except ValueError as oshibka:
            _otdat_json(h, 400, {"error": str(oshibka)})
            return True
        c.commit()
        _otdat_json(h, 200, {"ok": True, "id": novyj, "s_daty": s_daty,
                             "po_datu": po_datu, "dnej": _dlina_perioda(s_daty, po_datu)})
        return True
    finally:
        c.close()


def _soedinenie(h) -> sqlite3.Connection:
    """Соединение сервера, а при его отсутствии — точно такое же.

    Тот же приём, что уже стоит в `veb/razdely/istoria.py::_soedinenie` — фикстура тестов
    кладёт путь на объект сервера, а прагмы WAL/busy_timeout живут в `veb/server.py`.
    """
    svoj = getattr(h, "_connection", None)
    if callable(svoj):
        return svoj()
    # 🔴 `getattr(x, "db_path", config.DB_PATH)` — ЛОВУШКА, И ОНА СРАБОТАЛА.
    # Значение по умолчанию у `getattr` вычисляется ДО того, как проверено
    # наличие атрибута, поэтому обращение к источнику происходило даже там, где
    # база уже названа сервером. `or` короткозамкнут: спрашиваем источник только
    # тогда, когда сервер базу НЕ назвал.
    db_path = getattr(getattr(h, "server", None), "db_path", None) or config.DB_PATH
    raw = sqlite3.connect(str(db_path), check_same_thread=False, isolation_level=None)
    raw.execute("pragma foreign_keys = on")
    raw.execute("pragma journal_mode = WAL")
    raw.execute("pragma synchronous = normal")
    raw.execute("pragma busy_timeout = %d" % config.BUSY_TIMEOUT_MS)
    raw.row_factory = sqlite3.Row
    return raw


def _otdat_html(h, status: int, telo: str) -> None:
    telo_bytes = telo.encode("utf-8")
    h.send_response(status)
    h.send_header("Content-Type", "text/html; charset=utf-8")
    h.send_header("Content-Length", str(len(telo_bytes)))
    h.end_headers()
    h.wfile.write(telo_bytes)


def _otdat_json(h, status: int, telo: dict) -> None:
    telo_bytes = json.dumps(telo, ensure_ascii=False).encode("utf-8")
    h.send_response(status)
    h.send_header("Content-Type", "application/json; charset=utf-8")
    h.send_header("Content-Length", str(len(telo_bytes)))
    h.end_headers()
    h.wfile.write(telo_bytes)


def _chetvert_iz_adresa(put: str):
    """`?ch=3` → `3`. Всё нечисловое и пустое — `None`, то есть «четверть сейчас».

    Номер НЕ проверяется здесь на диапазон: единственное место, которое знает,
    сколько четвертей в году, — `karkas.chetverti_goda`, и проверка живёт там же,
    в `stranica`. Здесь только разбор адреса.
    """
    from urllib.parse import parse_qs, urlparse

    syroj = parse_qs(urlparse(put).query).get("ch", [""])[0]
    try:
        return int(syroj)
    except ValueError:
        return None


def pokazat_istoriyu(h) -> bool:
    """`/istoria` — обе решётки на одной странице. Только для вошедших.

    Гость сюда не пускается тем же порогом, каким закрыт Кондуит: полные фамилии и
    посещаемость — не гостевые данные. `karkas.VOZMOZHNOSTI` вне зоны этого захода, так
    что порог — прямая проверка роли, а не новая именованная возможность.
    """
    if vhod.rol(h.headers) is None:
        _otdat_html(h, 403, "<p>нужно войти</p>")
        return True
    c = _soedinenie(h)
    try:
        _otdat_html(h, 200, stranica(c, mozhno_pravit=_mozhno_pravit(h),
                                     chetvert=_chetvert_iz_adresa(h.path)))
    finally:
        c.close()
    return True


def marshruty():
    """Пути этого раздела: `{путь: обработчик}`. Зовётся сборкой сервера."""
    return {"/istoria": pokazat_istoriyu,
            "/api/otsutstvie": dver_otsutstvia}
