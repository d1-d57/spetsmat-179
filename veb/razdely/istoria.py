#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-code — the routes below are declared by `marshruty()` and
# collected by `veb.server._marshruty_razdelov` (`RAZDELY_S_MARSHRUTAMI` names this
# module), which `do_GET` and `do_POST` both consult.
"""История одной клетки: кто, когда и к какому занятию — и перебивка занятия.

WHAT THE OWNER ASKED FOR, 09.09: *«когда ты ставишь галочку в крестик, там сохранялась
информация об этой галочке, когда и кто её поставил… примерно как в Google таблицах, там
тоже можно посмотреть состояние клеточки… зажатие состояния клеточки должно дать нам
возможность посмотреть всю историю»*.  Всё это уже лежало в базе: отметка несёт автора,
два времени и ссылку на событие, которое она отменяет.  Наружу не было выведено ничего.

🔴 ВТОРОГО ЖУРНАЛА ЗДЕСЬ НЕТ, И ЭТО ГЛАВНОЕ СВОЙСТВО ФАЙЛА.  Ни одного `insert into
marks`: чтение идёт через `MarkJournal` и `core.services.history`, а единственная запись
этого раздела — ряд в `mark_lesson_override`, ОТДЕЛЬНОЙ таблице, которая ничего в журнале
не трогает.  Что такое клетка, по-прежнему отвечает `ProgressService` и никто больше.

🔴 ЧТО ТАКОЕ SQL В ЭТОМ ФАЙЛЕ И ПОЧЕМУ ОН ЗДЕСЬ, А НЕ В `infra/`.  `core/` не знает про
sqlite по построению (`core/ports.py`), а `infra/repositories.py` — не зона этой позиции.
Поэтому две функции ниже (`perebivki` и `zapisat_perebivku`) — это адаптер таблицы,
живущий рядом со своим единственным потребителем.  Ровно одна таблица, ровно два запроса.

🔴 ВИДИМОЙ МЕТКИ НА КЛЕТКЕ НЕ ЗАВОДИТСЯ — решение владельца 09.09.  История открывается
жестом (правый клик · долгое зажатие), кондуит остаётся ровно таким, каким владелец его
принял; сам жест живёт в `veb/razdely/konduit.py`, потому что скрипт кондуита — часть его
раздела, а `veb/obshchee/karkas.py` не зона этой позиции.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import config
from core.isotime import now_iso, parse_iso
from core.services import history
from core.services.progress import ProgressService
from core.services.sostav_na_den import SLOTY_ZANYATIJ
from infra.repositories import SqliteCatalogue, SqliteMarkJournal
from veb import vhod

#: Сколько прошедших занятий предлагать в перебивке.  Владелец назвал сценарий «в конце
#: четверти я пришёл к человеку, говорю, у тебя долги» — четверть это около десяти недель
#: по два занятия, поэтому список покрывает четверть с запасом и не длиннее.
GLUBINA_VYBORA = 24

#: Как называются дни недели в списке занятий.  Короткие: строка «чт 10.09» читается
#: быстрее, чем «2026-09-10», а перебивают её глазами, а не парсером.
DNI = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")


# ------------------------------------------------------------- адаптер перебивок


def perebivki(c, mark_ids=None) -> dict:
    """`{mark_id: valid_at}` — ДЕЙСТВУЮЩАЯ перебивка каждой названной отметки.

    Действует последняя: у одной отметки может стоять несколько перебивок (человек
    вправе ошибиться и во второй раз), и побеждает та, у которой больше `id` — той же
    формы правило, что и «состояние клетки есть последнее её событие».

    `mark_ids=None` значит «все», и это нормальный запрос: таблица пуста ровно до тех
    пор, пока правило даты никого не подвело, а дальше растёт по ряду на исправление.
    """
    zapros = ("select o.mark_id as mark_id, o.valid_at as valid_at "
              "from mark_lesson_override o "
              "join (select mark_id, max(id) as last_id from mark_lesson_override "
              "      group by mark_id) posl on posl.last_id = o.id")
    parametry: tuple = ()
    if mark_ids is not None:
        spisok = list(mark_ids)
        if not spisok:
            return {}
        zapros += " where o.mark_id in (%s)" % ",".join("?" * len(spisok))
        parametry = tuple(spisok)
    return {r["mark_id"]: r["valid_at"] for r in c.execute(zapros, parametry)}


def zapisat_perebivku(c, mark_id: int, den: str, teacher_id, note=None) -> str:
    """Отнести отметку к занятию `den` (ISO-дата) и вернуть записанный момент.

    Хранится НАЧАЛО занятия, а не полночь: полночь по Москве — это предыдущий день по
    UTC, а колонка в UTC.  День, на котором занятия нет, отклоняется здесь же —
    `history.nachalo_zanyatia_iso` поднимает `ValueError`.
    """
    kogda = history.nachalo_zanyatia_iso(den)
    c.execute(
        "insert into mark_lesson_override (mark_id, valid_at, teacher_id, recorded_at, note) "
        "values (?, ?, ?, ?, ?)",
        (mark_id, kogda, teacher_id, now_iso(), note),
    )
    return kogda


# ------------------------------------------------------------------- вид для человека


def _mestnoe(kogda: str) -> str:
    """Момент из базы — в московское «10.09 13:42».  Через `ZoneInfo`, не через сдвиг."""
    m = parse_iso(kogda).astimezone(ZoneInfo(config.TZ_DISPLAY))
    return "%02d.%02d %02d:%02d" % (m.day, m.month, m.hour, m.minute)


def _vid_dnya(den: str) -> str:
    """`2026-09-10` → `чт 10.09`."""
    d = date.fromisoformat(den)
    return "%s %02d.%02d" % (DNI[d.weekday()], d.day, d.month)


def zanyatiya_do(segodnya: date, skolko: int = GLUBINA_VYBORA) -> list:
    """Прошедшие учебные дни, от свежего к старому, включая сегодняшний, если он учебный.

    «Прошедший» здесь — по календарю, а не по часам: перебивают уже случившееся, и
    занятие, которое идёт прямо сейчас, тоже уже началось.
    """
    dni, den = [], segodnya
    while len(dni) < skolko:
        if den.isoweekday() in SLOTY_ZANYATIJ:
            dni.append(den.isoformat())
        den -= timedelta(days=1)
        if (segodnya - den).days > skolko * 7 + 7:
            break
    return dni


def _lenta(c, student_id: int, problem_id: int) -> dict:
    """Всё, что показывает панель истории одной клетки."""
    journal = SqliteMarkJournal(c)
    catalogue = SqliteCatalogue(c)

    sobytia_syrye = journal.events([student_id], [problem_id])
    nashi = perebivki(c, [s.id for s in sobytia_syrye])
    lenta = history.istoria_kletki(journal, student_id, problem_id, perebivki=nashi)

    imena = {r["id"]: r["name"] for r in c.execute("select id, name from teachers")}
    uchenik = catalogue.student(student_id)
    zadacha = next((p for p in c.execute(
        "select p.label as label, s.number as number from problems p "
        "join sheets s on s.id = p.sheet_id where p.id = ?", (problem_id,))), None)

    sostoyanie = ProgressService(journal, catalogue).states_for(
        student_id, [problem_id])[problem_id]
    segodnya = datetime.now(ZoneInfo(config.TZ_DISPLAY)).date()

    return {
        "student": student_id,
        "problem": problem_id,
        "kto": ("%s %s" % (uchenik.surname, uchenik.name)) if uchenik else "ученик %d" % student_id,
        "chto": ("%s · %s" % (zadacha["number"], zadacha["label"])) if zadacha
                else "задача %d" % problem_id,
        "sostoyanie": sostoyanie.value,
        "schyot": history.schyot_sobytij(sobytia_syrye),
        "vsego": len(sobytia_syrye),
        "zanyatiya": [{"den": d, "vid": _vid_dnya(d)} for d in zanyatiya_do(segodnya)],
        "sobytia": [{
            "id": s.id,
            "chto": s.imya,
            "kto": imena.get(s.teacher_id) or "без имени",
            "kogda": _mestnoe(s.kogda),
            "zanyatie": s.zanyatie,
            "zanyatie_vid": _vid_dnya(s.zanyatie) if s.zanyatie else "—",
            "perebito": s.perebito,
            "tehnicheskoe": s.tehnicheskoe,
            "istochnik": s.source,
        } for s in reversed(lenta)],          # свежее сверху: его и смотрят
    }


# ----------------------------------------------------------------- объявление маршрутов


def marshruty():
    """Пути этого раздела: {путь: обработчик}.  Зовётся сборкой сервера.

    Обе двери отвечают и на POST, и на GET.  `do_GET` и `do_POST` спрашивают реестр
    одинаково, так что POST достаточно; GET у двери записи оставлен той же страховкой,
    какую завёл `veb/priyom.py` — жест открывает историю на живом занятии, и «не
    записалось, потому что метод не тот» это не тот ответ, который там можно себе
    позволить.
    """
    return {"/api/istoria": lenta_kletki, "/api/istoria/zanyatie": perebit_zanyatie}


# ------------------------------------------------------------------------- обработчики


def lenta_kletki(h) -> bool:
    """`/api/istoria?student=&problem=` — вся история одной клетки."""
    if vhod.rol(h.headers) is None:
        _otdat_json(h, 403, {"error": "нужно войти"})
        return True
    try:
        p = _telo(h)
        student_id, problem_id = int(p["student"]), int(p["problem"])
    except (KeyError, TypeError, ValueError):
        _otdat_json(h, 400, {"error": "нужны student и problem"})
        return True

    c = _soedinenie(h)
    try:
        _otdat_json(h, 200, _lenta(c, student_id, problem_id))
    finally:
        c.close()
    return True


def perebit_zanyatie(h) -> bool:
    """`/api/istoria/zanyatie` — отнести отметку к другому занятию.

    Отвечает той же лентой, что и чтение: панель перерисовывается ответом целиком, и
    перебивка сразу видна СЛЕДОМ в ленте, а не подменяет строку молча.
    """
    if vhod.rol(h.headers) is None:
        _otdat_json(h, 403, {"error": "нужно войти"})
        return True
    try:
        p = _telo(h)
        mark_id = int(p["mark"])
        den = str(p["zanyatie"])
    except (KeyError, TypeError, ValueError):
        _otdat_json(h, 400, {"error": "нужны mark и zanyatie"})
        return True

    c = _soedinenie(h)
    try:
        ryad = c.execute("select student_id, problem_id from marks where id = ?",
                         (mark_id,)).fetchone()
        if ryad is None:
            _otdat_json(h, 404, {"error": "нет отметки %d" % mark_id})
            return True
        try:
            zapisat_perebivku(c, mark_id, den, vhod.kto(h.headers))
        except ValueError as oshibka:
            _otdat_json(h, 400, {"error": str(oshibka)})
            return True
        _otdat_json(h, 200, _lenta(c, ryad["student_id"], ryad["problem_id"]))
    finally:
        c.close()
    return True


# ------------------------------------------------------------------------- обвязка HTTP


def _soedinenie(h) -> sqlite3.Connection:
    """Соединение сервера, а при его отсутствии — точно такое же.

    Спрашивать `h` первым — то, на чём держится временная база тестов: фикстура кладёт
    путь на объект сервера, а прагмы WAL и busy_timeout живут в `veb/server.py`.
    Повторять их по памяти здесь — способ развести два соединения по поведению.
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


def _telo(h) -> dict:
    """Значения запроса — из тела JSON или из строки адреса."""
    dlina = int(h.headers.get("Content-Length", "0") or "0")
    if dlina:
        return json.loads(h.rfile.read(dlina).decode("utf-8"))
    return {k: v[0] for k, v in parse_qs(urlparse(h.path).query).items()}


def _otdat_json(h, status: int, payload) -> None:
    telo = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    h.send_response(status)
    h.send_header("Content-Type", "application/json; charset=utf-8")
    h.send_header("Content-Length", str(len(telo)))
    h.end_headers()
    h.wfile.write(telo)
