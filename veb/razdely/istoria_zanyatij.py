#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-code — the route below is declared by `marshruty()` and
# collected by `veb.server._marshruty_razdelov` (`RAZDELY_S_MARSHRUTAMI`), the same seam
# `veb/razdely/istoria.py` already uses.
"""История занятий: кто был на каждом ПРОШЕДШЕМ занятии, и у кого/с кем.

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
from datetime import datetime, timezone

import config
from core.services.history import nachalo_zanyatia_iso, zanyatie_po_iso
from core.services.istoria_poseshchenij import IstoriyaService
from core.services.sostav_na_den import SostavService
from infra.enrollment_repo import SqliteEnrollmentRepo
from infra.room_repo import SqliteAttendance, SqliteSessions
from infra.sessions_repo import SqliteSessionBook
from veb import vhod
from veb.obshchee.karkas import (
    PRICHINY_OTSUTSTVIYA, e, menyu_ssylkami, otmetit_otsutstvie,
    periody_otsutstvij, snyat_otsutstvie)
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


DNI_NEDELI = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")


def _shapka_dnya(den: str) -> str:
    from datetime import date
    d = date.fromisoformat(den)
    return "%s %s" % (DNI_NEDELI[d.weekday()], _kratko(den))


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


def _otmenennye(sessii, dni) -> tuple:
    """Дни, отменённые целиком, — их в решётке НЕТ И НЕ БУДЕТ, и молчать об этом нельзя.

    🔴 РЕШЁТКА ИХ НЕ СОДЕРЖИТ ПО УСТРОЙСТВУ, А НЕ ПО НЕДОСМОТРУ.
    `IstoriyaService.sostavit` отбирает занятия условием `s.kind != "отменённое"` —
    и это верно для решётки: столбец отменённого дня был бы столбцом крестиков,
    то есть сказал бы «никто не пришёл» там, где занятия не было вовсе.
    Но владелец просил ровно этот факт: «когда был праздник и урок отменился… Всю
    эту историю курса важно где-то документировать». Между «столбцом, который врёт»
    и «фактом, которого нет на экране» есть третье, и оно здесь: отменённые дни
    названы отдельной строкой под журналом, поимённо.
    Перенести их в саму решётку нельзя внутри этой зоны — отбор живёт в
    `core/services/istoria_poseshchenij.py`, а зона захода до него не достаёт;
    пункт очереди стоит в `## ВОПРОСЫ`.
    """
    v_reshetke = set(dni)
    return tuple(sorted(s.held_on for s in sessii
                        if s.kind == "отменённое" and s.held_on not in v_reshetke))


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


#: Как род занятия называется на экране. Слева — то, что ДЕРЖИТ схема, справа —
#: слово владельца (10.09). Ключа «дополнительное» здесь нет ровно потому, что
#: его нет и в базе: см. разбор у `_rod_zanyatiya`.
IMYA_RODA = {"обычное": "обычное", "зачёт": "контрольная", "отменённое": "отменено"}

#: Обычное занятие — норма, и подпись под ним приглушена; всё остальное владелец
#: ищет глазами («когда были контрольные, когда был праздник и урок отменился») и
#: потому выделено. Род печатается у КАЖДОГО столбца, а не только у исключений:
#: столбец без подписи неотличим от столбца, у которого род не прочитался.
ROD_OBYCHNYJ = "обычное"


def _imya_shkolnika(u: dict) -> str:
    return "%s %s" % (u["surname"], u["name"])


def _shapka(dni, rody, pervyj_stolbec: str) -> str:
    """Шапка решётки: день недели, дата и — если он не обычный — РОД занятия.

    Владелец 10.09: «когда были контрольные, когда был праздник и урок отменился,
    когда был дополнительный урок… Всю эту историю курса важно где-то
    документировать». Документируется она здесь, в шапке столбца, а не отдельной
    страницей: столбец И ЕСТЬ занятие.
    """
    stolbcy = []
    for d in dni:
        syroj = rody.get(d)
        rod = IMYA_RODA.get(syroj, syroj or "род не назван")
        tiho = " ist-rod-tiho" if syroj == ROD_OBYCHNYJ else ""
        stolbcy.append(f'<th class="ist-zn">{e(_shapka_dnya(d))}'
                       f'<span class="ist-rod{tiho}">{e(rod)}</span></th>')
    return f'<th>{e(pervyj_stolbec)}</th>' + "".join(stolbcy)


def _kletka(klass: str, znak: str, vsplyv: str, den: str, vid: str, kto_id) -> str:
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
    return (f'<td class="ist-kl {klass}" title="{vsplyv}" '
            f'data-den="{e(den)}" data-vid="{vid}" data-kto="{kto_id}" tabindex="0">'
            f'<span class="kl-znak">{znak}</span>{PUSTYE_MESTA}</td>')


def _tablitsa_shkolnikov(students, teachers_by_id, istoriya, rody) -> str:
    if not istoriya.dni:
        return '<p class="ist-pusto">прошедших занятий пока нет</p>'
    stroki = []
    for u in students:
        po_dnyam = istoriya.shkolniki.get(u["id"], {})
        kletki = []
        for den in istoriya.dni:
            yacheika = po_dnyam.get(den)
            if yacheika is None or not yacheika.prisutstvoval:
                kletki.append(_kletka("ist-net", "✕", "не был", den, "shk", u["id"]))
            elif yacheika.nekuda_det:
                kletki.append(_kletka("ist-def", "?", "был, но принимающий не назначен",
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
    return (f'<table class="ist-tabl"><thead><tr>'
            f'{_shapka(istoriya.dni, rody, "Школьник")}</tr></thead>'
            f'<tbody>{"".join(stroki)}</tbody></table>')


def _tablitsa_prepodavatelej(teachers, students_by_id, istoriya, rody) -> str:
    if not istoriya.dni:
        return '<p class="ist-pusto">прошедших занятий пока нет</p>'
    stroki = []
    for t in teachers:
        po_dnyam = istoriya.prepodavateli.get(t["id"], {})
        kletki = []
        for den in istoriya.dni:
            yacheika = po_dnyam.get(den)
            if yacheika is None or not yacheika.prisutstvoval:
                kletki.append(_kletka("ist-net", "✕", "не был", den, "prep", t["id"]))
            else:
                imena = ", ".join(
                    _imya_shkolnika(students_by_id[sid])
                    for sid in yacheika.ucheniki if sid in students_by_id)
                kletki.append(_kletka("ist-byl", "✓", e(imena) or "принимал: никого",
                                      den, "prep", t["id"]))
        stroki.append(
            f'<tr><td class="ist-kto"><b>{e(t["name"])}</b></td>{"".join(kletki)}</tr>')
    return (f'<table class="ist-tabl"><thead><tr>'
            f'{_shapka(istoriya.dni, rody, "Преподаватель")}</tr></thead>'
            f'<tbody>{"".join(stroki)}</tbody></table>')


def _chto_raskryvaetsya(students, teachers, istoriya, sdachi) -> dict:
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
    itog: dict = {}
    for u in students:
        po_dnyam = istoriya.shkolniki.get(u["id"], {})
        for den in istoriya.dni:
            ya = po_dnyam.get(den)
            sdal = sdachi.get((den, u["id"]), ())
            itog["shk|%s|%s" % (den, u["id"])] = {
                "kto": imena_detej[u["id"]],
                "byl": bool(ya is not None and ya.prisutstvoval),
                "komu": (imena_prepov.get(ya.prepodavatel_id)
                         if ya is not None and ya.prisutstvoval else None),
                "sdal": [{"zadacha": z, "listok": l,
                          "prinyal": imena_prepov.get(tid)} for z, l, tid in sdal],
            }
    for t in teachers:
        po_dnyam = istoriya.prepodavateli.get(t["id"], {})
        for den in istoriya.dni:
            ya = po_dnyam.get(den)
            deti = []
            if ya is not None and ya.prisutstvoval:
                for sid in ya.ucheniki:
                    if sid not in imena_detej:
                        continue
                    deti.append({
                        "kto": imena_detej[sid],
                        "sdal": [{"zadacha": z, "listok": l}
                                 for z, l, tid in sdachi.get((den, sid), ())
                                 if tid is None or tid == t["id"]],
                    })
            itog["prep|%s|%s" % (den, t["id"])] = {
                "kto": t["name"],
                "byl": bool(ya is not None and ya.prisutstvoval),
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


def _spisok_periodov(periody, teachers_by_id) -> str:
    """Уже отмеченные периоды, поимённо и со снятием.

    Пустой список говорит об этом словами: строка «отметок нет» отличима от
    страницы, на которой список просто не нарисовался.
    """
    if not periody:
        return '<p class="ots-pusto">отметок об отсутствии нет</p>'
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
            f'<button type="button" class="ots-snyat" data-id="{per["id"]}">снять</button>'
            f'</li>')
    return '<ul class="ots-spisok">' + "".join(stroki) + "</ul>"


SVOI_STILI = """
.istoria{max-width:none;padding:1.3em 2.4em 2.4em}
.istoria h1{font-family:var(--sans);font-size:1.6em;margin:0 0 .3em}
.istoria .podpis{color:var(--muted);font-family:var(--sans);font-size:.92em;margin:0 0 1.2em}
.ist-vkladki{display:flex;gap:.4rem;margin:0 0 1rem;font-family:var(--sans)}
.ist-vkladki label{cursor:pointer;font-weight:600;padding:.35em 1.1rem;border-radius:8px;
  border:1px solid var(--rule);color:var(--muted)}
#iv-shk:checked~.ist-vkladki label[for=iv-shk],
#iv-prep:checked~.ist-vkladki label[for=iv-prep]{color:var(--accent);
  background:var(--accent-soft);border-color:var(--accent)}
#is-shk,#is-prep{display:none}
#iv-shk:checked~#is-shk,#iv-prep:checked~#is-prep{display:block}
.ist-pusto{color:var(--muted)}
/* Решётка «люди × даты» в той же форме, что уже стоит у Кондуита: закреплённая первая
   колонка, узкие клетки дат, никакого горизонтального скролла страницы (канон, правило 4)
   — при паре занятий в неделю ширина решётки далека от предела, который Кондуит уже
   проверил на двадцати одном столбце. */
.ist-tabl{font-size:.95rem;width:100%;border-collapse:separate;border-spacing:0}
.ist-tabl th.ist-zn{padding:.5rem .2rem;text-align:center;font-size:.78rem;min-width:3em;
  border-bottom:2px solid var(--rule);border-left:1px solid var(--rule)}
.ist-tabl thead th{position:sticky;top:0;z-index:2;background:var(--panel)}
.ist-tabl thead th:first-child{left:0;z-index:3;text-align:left;
  border-bottom:2px solid var(--rule)}
.ist-tabl td.ist-kto{white-space:nowrap;padding:.3rem 1.2rem .3rem 0;font-size:.95rem;
  position:sticky;left:0;z-index:1;background:var(--bg);border-bottom:1px solid var(--rule)}
.ist-tabl tbody td+td{text-align:center;padding:.42rem .3rem;font-family:var(--sans);
  font-size:.92rem;min-width:3em;border-left:1px solid var(--rule);
  border-bottom:1px solid var(--rule)}
.ist-tabl td.ist-byl{color:var(--accent);font-weight:600}
.ist-tabl td.ist-net{color:var(--faint)}
.ist-tabl td.ist-def{color:var(--warm);font-weight:700}
/* Род занятия — второй строкой в шапке столбца, и только когда он НЕ обычный:
   владелец ищет глазами исключения (контрольная, отменённый урок), а подпись
   «обычное» над каждым столбцом была бы шумом ровно поверх них. */
.ist-tabl th.ist-zn .ist-rod{display:block;font-size:.68rem;font-weight:600;
  letter-spacing:.02em;color:var(--warm);text-transform:none}
/* 🔴 `--muted`, А НЕ `--faint`, И ЭТО ЗАМЕР ВЕРИФИКАТОРА, А НЕ ВКУС. На `--faint`
   подпись давала контраст 2.16:1 при пороге AA 4.5:1 — самый слабый текст на
   странице, и ровно на нём стоит слово, ради которого столбец подписан. */
.ist-tabl th.ist-zn .ist-rod-tiho{color:var(--muted);font-weight:400}
.ist-otmeneno{font-family:var(--sans);font-size:.92rem;color:var(--warm);margin:.8rem 0 0}
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
.ist-raskrytie ul{margin:.3rem 0 0;padding-left:1.2rem}
.ist-raskrytie li{padding:.12rem 0}
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
.ist-zhurnal{margin:0 0 .2rem;font-family:var(--sans);font-size:1.15rem;font-weight:600}
.ist-zachem{color:var(--muted);font-family:var(--sans);font-size:.92rem;margin:0 0 .8rem}
@media(max-width:760px){
  .istoria{padding-left:1.1rem;padding-right:1.1rem}
  .ist-tabl td.ist-kto{width:7rem;max-width:7rem;overflow:hidden;text-overflow:ellipsis;
    white-space:nowrap}
}
"""


#: 🔴 ДВА ЖУРНАЛА — ЭТО ДВЕ РАЗНЫЕ ВЕЩИ, И ВЛАДЕЛЕЦ ПОПРАВИЛ ЗА ИХ СМЕШЕНИЕ.
#: Преподавательский — кто в какой день был; ПО НЕМУ СЧИТАЕТСЯ ЗАРПЛАТА, и неверная
#: клетка стоит денег живому человеку. Школьный — посещения и сколько сдал, и туда же
#: пойдут оценки: «это прообраз будущего личного кабинета». До этой правки они были
#: двумя безымянными вкладками «Школьники»/«Преподаватели» — то есть выглядели как
#: два вида одного списка. Названия и подписи ниже — единственное, чем экран говорит,
#: что это разные документы с разной ценой ошибки.
ZACHEM_ZHURNAL = {
    "shk": ("Журнал школьников",
            "посещения и сдача. Сюда же пойдут оценки — прообраз личного кабинета"),
    "prep": ("Журнал преподавателей",
             "кто в какой день был. По нему считается зарплата — цена ошибки в клетке "
             "не в отображении, а в деньгах"),
}

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

  function spisok(punkty, pusto){
    if (!punkty.length) return '<p class="ist-nichego">' + pusto + '</p>';
    return '<ul>' + punkty.map(function(x){ return '<li>' + x + '</li>'; }).join('') + '</ul>';
  }
  function zadachi(sdal){
    return sdal.map(function(z){
      return 'листок ' + z.listok + ' · задача ' + z.zadacha
             + (z.prinyal ? ' — принял ' + z.prinyal : '');
    });
  }
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
      telo.innerHTML = !d.byl
        ? '<p class="ist-nichego">на этом занятии не был</p>'
        : '<p>принимал: <b>' + (d.komu || 'принимающий не назначен') + '</b></p>'
          + '<p>сдал:</p>' + spisok(zadachi(d.sdal), 'в этот день ничего не сдал');
    } else {
      telo.innerHTML = !d.byl
        ? '<p class="ist-nichego">в этот день не принимал</p>'
        : '<p>принимал:</p>' + spisok(d.deti.map(function(r){
            var z = zadachi(r.sdal);
            return '<b>' + r.kto + '</b>' + (z.length ? ' — ' + z.join('; ') : ' — ничего не сдал');
          }), 'в этот день никого');
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
  var forma = document.getElementById('ots-forma');
  if(!forma) return;                      // не организатор: формы на странице нет
  var oshibka = document.getElementById('ots-oshibka');

  function skazat(text){
    oshibka.textContent = text;
    oshibka.hidden = !text;
  }
  function poslat(telo, chto){
    return fetch('/api/otsutstvie', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(telo)
    }).then(function(otvet){
      return otvet.json().catch(function(){ return {}; }).then(function(d){
        if(!otvet.ok){ skazat(d.error || (chto + ' не удалось: ' + otvet.status)); return; }
        /* 🔴 СТРАНИЦА ПЕРЕЧИТЫВАЕТСЯ ЦЕЛИКОМ, А НЕ ПОДПРАВЛЯЕТСЯ НА МЕСТЕ.
           Отметка меняет ТРИ вещи сразу: список отметок, вид клеток в решётке и
           полосу дней периода. Подправить их руками — значит завести второе
           описание того же факта в браузере, и оно разойдётся с сервером на
           первом же пересечении периодов. */
        location.reload();
      });
    }).catch(function(){ skazat(chto + ' не удалось: сервер не ответил'); });
  }

  forma.addEventListener('submit', function(sob){
    sob.preventDefault();
    skazat('');
    var s = document.getElementById('ots-s').value;
    var po = document.getElementById('ots-po').value;
    if(!s || !po){ skazat('нужны обе даты'); return; }
    if(s > po){ skazat('начало периода позже его конца'); return; }
    poslat({
      teacher_id: +document.getElementById('ots-kto').value,
      s_daty: s, po_datu: po,
      prichina: document.getElementById('ots-prichina').value
    }, 'отметка');
  });

  document.addEventListener('click', function(sob){
    var knopka = sob.target.closest ? sob.target.closest('.ots-snyat') : null;
    if(!knopka) return;
    skazat('');
    poslat({snyat: +knopka.dataset.id}, 'снятие отметки');
  });
})();
</script>"""


def stranica(c: sqlite3.Connection, mozhno_pravit: bool = False) -> str:
    """Вся страница: два журнала, собранные по одному разу каждый.

    `mozhno_pravit` — рисовать ли форму отметки отсутствия. Она ОРГАН ПРАВКИ, и
    показывать её тому, кому дверь всё равно ответит 403, значит обещать действие,
    которого не будет. Сам порог живёт в двери (`_pravit_nelzya`): форма — только
    его отражение, и её отсутствие ничего не запрещает само по себе.
    """
    students, teachers = _spravochniki(c)
    students_by_id = {u["id"]: u for u in students}
    teachers_by_id = {t["id"]: t for t in teachers}
    istoriya, sessii = _sostavit(c)
    rody = _rod_zanyatiya(c, sessii)
    periody = periody_otsutstvij(c)
    otmeneno = _otmenennye(sessii, istoriya.dni)
    sdachi = sdachi_po_zanyatiyam(c, istoriya.dni)
    dannye = _chto_raskryvaetsya(students, teachers, istoriya, sdachi)

    podpis = ("прошедших занятий пока нет" if not istoriya.dni
              else "занятий: %d" % len(istoriya.dni))
    if istoriya.nekuda_det_vsego:
        podpis += " · без принимающего в этот день: %d" % istoriya.nekuda_det_vsego

    stroka_otmen = (
        '<p class="ist-otmeneno">отменённые занятия (в решётке их нет — занятия не '
        'было): %s</p>' % e(", ".join(_shapka_dnya(d) for d in otmeneno))
        if otmeneno else "")

    def zagolovok(vid: str) -> str:
        imya, zachem = ZACHEM_ZHURNAL[vid]
        return (f'<p class="ist-zhurnal">{e(imya)}</p>'
                f'<p class="ist-zachem">{e(zachem)}</p>')

    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Журнал — Ключики</title>
<style>{_obshchij_stil(put_bazy(c))}{SVOI_STILI}</style></head>
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
  <h1>Журнал</h1>
  <p class="podpis">{e(podpis)}</p>
  <nav class="ist-vkladki" id="ist-vkladki">
    <label for="iv-shk">Школьники</label>
    <label for="iv-prep">Преподаватели</label>
  </nav>
  <section id="is-shk">{zagolovok("shk")}
    {_tablitsa_shkolnikov(students, teachers_by_id, istoriya, rody)}</section>
  <section id="is-prep">{zagolovok("prep")}
    {_forma_otsutstvia(teachers) if mozhno_pravit else ""}
    {_spisok_periodov(periody, teachers_by_id)}
    {_tablitsa_prepodavatelej(teachers, students_by_id, istoriya, rody)}</section>
  {stroka_otmen}
  <div class="ist-raskrytie" id="ist-raskrytie" hidden>
    <button class="ist-zakryt" id="ist-zakryt" type="button">закрыть</button>
    <h2 id="ist-raskrytie-zag"></h2>
    <div id="ist-raskrytie-telo"></div>
  </div>
</main>
<script type="application/json" id="ist-dannye">{json.dumps(dannye, ensure_ascii=False)}</script>
{SKRIPT}{SKRIPT_OTSUTSTVIE}
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
        _otdat_html(h, 200, stranica(c, mozhno_pravit=_mozhno_pravit(h)))
    finally:
        c.close()
    return True


def marshruty():
    """Пути этого раздела: `{путь: обработчик}`. Зовётся сборкой сервера."""
    return {"/istoria": pokazat_istoriyu,
            "/api/otsutstvie": dver_otsutstvia}
