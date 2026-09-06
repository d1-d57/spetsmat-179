"""A tiny HTTP server that shows ``enrollment`` and lets the owner change it.

ONE page, two views, one mutation.  The page is intentionally HTML+vanilla JS in
one file under ``veb/templates/``; the only mutable thing the server takes from
the request body is the next teacher for one ``(student, slot)`` pair.  No
session, no login, no analytics: the project has none of those yet, and adding
them here would commit the wrong choice twice (the code AND the documentation).

The two GET endpoints speak JSON for the page to fetch on load; the POST endpoint
takes JSON and replies with the resulting ``(closed, opened)`` pair.  All three
go through ``EnrollmentService`` — never through raw SQL — so the half-open
interval and the partial unique index stay the carrier of "one open row per
``(student, slot)``".

WHAT THE PAGE SHOWS.

  * By students  --  a row per catalogue student with their current teacher and
    the count of unsolved obligatory problems older than the current sheet
    (their debt, by ``ProgressService.debts``).

  * By teachers  --  a card per catalogue teacher with the students assigned to
    them and the headcount.  A teacher with zero students or more than five is
    highlighted in red; the brief calls that "where to look".

A change goes through the page by ``POST /api/enrollment``.  The server reads the
new ``teacher_id``, computes ``effective_from`` as today, and calls
``EnrollmentService.move`` (closing the old interval and opening a new one).  No
PATCH-style "set teacher on this row" exists, because the schema's only
mutation is ``close`` and a port without ``update`` is the whole point of the
half-open model.

SLOT, NOT WEEKDAY.  ``slot`` is the key the school actually teaches by: each child
attends one or two slots, and the unit of assignment is ``(student, slot)``.  The
schema's CHECK on the column still reads ``between 1 and 7`` because SQLite cannot
ALTER a CHECK in place and the values that exist today all fit; the ceiling is the
schema's, not a property of the slot concept.  See ``migrations/003_slot_vmesto_weekday.sql``
for the weekday-to-slot mapping.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import config
from core.services.enrollment import (
    EnrollmentError,
    EnrollmentService,
    MoveChangesNothing,
    MoveNotForward,
    NotEnrolled,
)
from infra.db import connect
from infra.enrollment_repo import SqliteEnrollmentRepo
from veb import vhod
from veb.sobrat_fajl import blizhajshee_zanyatie


SLOT_DEFAULT = 1  # The page shows one slot at a time.
PORT_DEFAULT = 8765

# 🔴 ТУМБЛЕР СВОБОДНОЙ ПРАВКИ, И ОН СНОВА ЗАКРЫТ (владелец, 2026-09-06). Цель
# сегодняшнего дня сформулирована им дословно: зайти на сайт, нажать кнопку входа,
# ввести пароль организатора — и попасть на редактирование распределения; «больше
# за паролем ничего быть не должно». Свободная правка была решением 04.09, когда
# кнопки входа на публичной странице не существовало вовсе и пароль стоял на
# критическом пути; теперь кнопка есть, и путь через неё короче прежнего.
# 🔴 ОТКАТ — БЕЗ ВЫКАТКИ: `SPETSMAT_VEB_SVOBODNAYA_PRAVKA=1` в `secrets/veb.env`
# плюс перезапуск юнита возвращает прежнее поведение. Публичная половина сайта
# паролем не закрыта и не будет: за паролем ровно один экран — правка.
SVOBODNAYA_PRAVKA = os.environ.get("SPETSMAT_VEB_SVOBODNAYA_PRAVKA", "0") != "0"

KOREN_PROEKTA = Path(__file__).resolve().parent.parent
# Публичная страница — ФАЙЛ на диске, и это не лень, а свойство: гость получает
# байты, пересобранные последней успешной правкой, даже если сборка сейчас сломана.
PUBLICHNAYA = KOREN_PROEKTA / "docs" / "index.html"
INSTRUMENT_SBORKI = KOREN_PROEKTA / "tools" / "sobrat_stranicu.py"

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
MATERIALS_DIR = Path("/Users/ivanyakovlev/Documents/GitHub/materials/spetsmat-2026")

# 🔴 ЗАГЛУШЕК `GLAVNAYA_STUB` · `LISTKI_STUB` · `UROVNI_STUB` ЗДЕСЬ БОЛЬШЕ НЕТ.
# Они печатали «Страница в разработке» на случай, если шаблон не найдётся, — и
# после переезда сайта именно они были бы единственным способом снова увидеть
# старый песочный вид, от которого владелец просил избавиться навсегда. Сами
# шаблоны лежат в `arhiv/veb-templates/` с объяснением, чем они были.



def _sborka_vozmozhna() -> None:
    """Можно ли вообще пересобрать публичную страницу. Зовётся ДО записи в базу.

    🔴 ПОРЯДОК ЗДЕСЬ — ЭТО И ЕСТЬ ТРЕБОВАНИЕ «БАЗА НЕ ИЗМЕНИЛАСЬ». Проверка стоит
    ПЕРЕД правкой, поэтому исчезнувший инструмент или закрытые права на `docs/`
    отказывают до того, как в базе что-нибудь поменялось. Если бы проверкой был
    сам факт сборки после записи, отказ приходил бы на уже изменённые данные — то
    есть ровно то расхождение «база новая, страница вчерашняя», от которого уходим.

    Падает исключением, а не возвращает False: текст исключения уезжает человеку.
    """
    if not INSTRUMENT_SBORKI.is_file():
        raise FileNotFoundError(
            "нет %s — публичную страницу нечем пересобрать" % INSTRUMENT_SBORKI)
    papka = PUBLICHNAYA.parent
    if not papka.is_dir():
        raise FileNotFoundError("нет папки %s" % papka)
    cel = PUBLICHNAYA if PUBLICHNAYA.exists() else papka
    if not os.access(cel, os.W_OK):
        raise PermissionError(
            "нет права записи в %s — публичную страницу некуда пересобрать" % cel)


def _peresobrat() -> list:
    """Пересобрать публичную страницу из базы. Падает громко и наружу."""
    from tools.sobrat_stranicu import sobrat
    svodka: list = []
    sobrat(svodka)
    return svodka


def _static_content_type(path: str) -> str:
    if path.endswith(".css"):
        return "text/css; charset=utf-8"
    if path.endswith(".js"):
        return "application/javascript; charset=utf-8"
    if path.endswith(".png"):
        return "image/png"
    if path.endswith(".svg"):
        return "image/svg+xml; charset=utf-8"
    return "application/octet-stream"


def _serve_static(self, path: str) -> bool:
    rel = path[len("/static/"):].lstrip("/")
    if not rel or ".." in rel.split("/"):
        self._send_json(404, {"error": "not found"})
        return True
    target = (STATIC_DIR / rel).resolve()
    try:
        target.relative_to(STATIC_DIR.resolve())
    except ValueError:
        self._send_json(404, {"error": "not found"})
        return True
    if not target.is_file():
        self._send_json(404, {"error": "not found"})
        return True
    body = target.read_bytes()
    self.send_response(200)
    self.send_header("Content-Type", _static_content_type(rel))
    self.send_header("Content-Length", str(len(body)))
    self.end_headers()
    self.wfile.write(body)
    return True


_BAD_LOGIN_HTML = (
    b"<!doctype html><html lang=\"ru\"><head>"
    b"<meta charset=\"utf-8\"><title>\xd0\x9d\xd0\xb5\xd0\xb2\xd0\xb5\xd1\x80\xd0\xbd\xd1\x8b\xd0\xb9 \xd0\xbf\xd0\xb0\xd1\x80\xd0\xbe\xd0\xbb\xd1\x8c \xe2\x80\x94 \xd0\xa1\xd0\xbf\xd0\xb5\xd1\x86\xd0\xbc\xd0\xb0\xd1\x82</title>"
    b"<link rel=\"stylesheet\" href=\"/static/vhod.css\"></head><body>"
    b"<header><h1>\xd0\xa1\xd0\xbf\xd0\xb5\xd1\x86\xd0\xbc\xd0\xb0\xd1\x82 \xe2\x80\x94 \xd0\xb2\xd1\x85\xd0\xbe\xd0\xb4</h1></header>"
    b"<main><p class=\"error\">\xd0\x9d\xd0\xb5\xd0\xb2\xd0\xb5\xd1\x80\xd0\xbd\xd1\x8b\xd0\xb9 \xd0\xbf\xd0\xb0\xd1\x80\xd0\xbe\xd0\xbb\xd1\x8c.</p>"
    b"<form method=\"post\" action=\"/vhod\">"
    b"<label for=\"parol\">\xd0\x9f\xd0\xb0\xd1\x80\xd0\xbe\xd0\xbb\xd1\x8c</label>"
    b"<input type=\"password\" id=\"parol\" name=\"parol\" required autocomplete=\"current-password\">"
    b"<button type=\"submit\">\xd0\x92\xd0\xbe\xd0\xb9\xd1\x82\xd0\xb8</button>"
    b"</form></main></body></html>"
)


# --------------------------------------------------------------------- helpers

def _all_students(connection: sqlite3.Connection) -> list[dict]:
    _obespechit_gruppu_shkolnika(connection)
    return [
        {"id": row["id"], "surname": row["surname"], "name": row["name"],
         "class": row["class"], "gruppa": row["gruppa"]}
        for row in connection.execute(
            "select id, surname, name, class, gruppa from students "
            "where status is null or status <> 'left' order by surname, name"
        ).fetchall()
    ]


def _all_teachers(connection: sqlite3.Connection) -> list[dict]:
    return [
        {"id": row["id"], "name": row["name"],
         "kabinet": row["kabinet"] if "kabinet" in row.keys() else None,
         "gruppa": row["gruppa"] if "gruppa" in row.keys() else None,
         "aktiven": bool(row["aktiven"]) if "aktiven" in row.keys() else True}
        # 🔴 `select *`, а не перечисление колонок: миграция 004 (кабинеты) могла ещё
        # не применяться — в тестах база свежая. Жёсткий список колонок ронял сборку
        # там, где данные просто старее кода.
        for row in connection.execute(
            "select * from teachers where aktiven is null or aktiven = 1 order by name"
        ).fetchall()
    ]


def _obespechit_aktivnost(connection: sqlite3.Connection) -> None:
    """Колонка `teachers.aktiven`, заводится один раз и молча.

    Владелец 2026-09-04: «сейчас там очень захардкожен список преподавателей».
    Состав в этом году другой, кого-то придётся позвать, кто-то приходит редко.
    🔴 УБРАТЬ = снять из активных, НЕ удалить: за преподавателем висит история
    прошлого года, и терять её нельзя.
    """
    kolonki = [r[1] for r in connection.execute("pragma table_info(teachers)")]
    if "aktiven" not in kolonki:
        connection.execute("alter table teachers add column aktiven integer not null default 1")
        connection.commit()


def _obespechit_gruppu_shkolnika(connection: sqlite3.Connection) -> None:
    """Колонка `students.gruppa` — СРЕДНЯЯ СТУПЕНЬ, и без неё её негде хранить.

    Ступеней у школьника три: «нигде» · «в группе, преподаватель не выбран» ·
    конкретный преподаватель. Средняя в `enrollment` не помещается по построению:
    `teacher_id` там `not null`, а преподавателя у этой ступени как раз нет.
    🔴 Ровно из-за отсутствия этой памяти снятый ребёнок ИСЧЕЗАЛ с той вкладки,
    на которой его сняли: группу вычисляли из преподавателя, преподавателя не
    стало — и ребёнок пропал в тот момент, когда его надо кому-то отдать.

    Заводится молча и один раз, тем же приёмом, что `teachers.aktiven` выше:
    `migrations/` живёт своей нумерацией, а колонка нужна коду, который её и
    создаёт, — иначе свежая тестовая база падает там, где данные просто старее.
    """
    kolonki = [r[1] for r in connection.execute("pragma table_info(students)")]
    if "gruppa" not in kolonki:
        connection.execute("alter table students add column gruppa text")
        connection.commit()


def _kabinety_grupp(connection: sqlite3.Connection):
    """``({группа: кабинет на сегодня}, {группа: старший})``.

    Кабинет назначается ГРУППЕ на КОНКРЕТНЫЙ ДЕНЬ и меняется: владелец ставит
    привязку накануне вечером. Нет строки на дату — кабинета на этот день нет,
    и это законный случай, а не потеря данных.
    """
    from datetime import date as _date
    try:
        segodnya = _date.today().isoformat()
        # 🔴 Берём БЛИЖАЙШУЮ дату, а не последнюю: словарь перезаписывается по ходу,
        # поэтому сортируем по УБЫВАНИЮ — ближайшая дата ложится последней и побеждает.
        # Без этого правка «кабинет на сегодня» молча проигрывала записи на завтра.
        kab = {r["gruppa"]: r["kabinet"] for r in connection.execute(
            "select gruppa, kabinet from kabinet_na_den where data >= ? order by data desc",
            (segodnya,))}
        star = {r["kod"]: r["starshij"] for r in connection.execute(
            "select kod, starshij from gruppy")}
        return kab, star
    except sqlite3.OperationalError:
        return {}, {}


def _rukovoditeli(connection: sqlite3.Connection) -> dict:
    """``{кабинет: имя руководителя | None}``.

    Кабинет держится РУКОВОДИТЕЛЕМ, а не преподавателем: заболел преподаватель —
    школьник идёт в тот же кабинет. Пока руководители не назначены владельцем,
    значение None, и интерфейс просто не показывает строку — врать нельзя.
    """
    try:
        rows = connection.execute(
            "select k.kabinet, t.name from kabinety k "
            "left join teachers t on t.id = k.rukovoditel_id"
        ).fetchall()
    except sqlite3.OperationalError:
        return {}
    return {row["kabinet"]: row["name"] for row in rows}


def _byvshaya_gruppa(connection: sqlite3.Connection, slot: int) -> dict[int, int]:
    """``{student_id: teacher_id последней ЗАКРЫТОЙ строки}`` — память о группе.

    🔴 ЗАКРЫТЫЕ СТРОКИ ВЫБРАСЫВАТЬ НЕЛЬЗЯ. Когда преподаватель ушёл, его строки
    закрыли датой — вместе с единственным следом того, В КАКОЙ ГРУППЕ ребёнок
    был. Без него дети выглядят «ничьими вообще», хотя группа у них известна и
    менять её незачем. Файловый сборщик это уже умел, а сервер — нет, и один и
    тот же ребёнок оказывался на сайте «нигде», а в файле — в своей группе.
    Две правды об одном ребёнке и есть тот разъезд, который здесь и сводится.

    Своя запись `students.gruppa` сильнее: её поставил человек руками.
    """
    rows = connection.execute(
        "select student_id, teacher_id from enrollment "
        "where slot = ? and valid_to <> ? order by valid_to, id",
        (slot, "9999-12-31"),
    ).fetchall()
    return {row["student_id"]: row["teacher_id"] for row in rows}


def _gruppy_vseh_prepodavatelej(connection: sqlite3.Connection) -> dict[int, str]:
    """``{teacher_id: группа}`` по ВСЕМ преподавателям, включая снятых с активных.

    🔴 Именно снятые и держат память: ребёнок «ничей» ровно потому, что его
    преподаватель ушёл. Спрашивать группу только у активных значит спрашивать
    всех, кроме того единственного, кто может ответить.
    """
    try:
        rows = connection.execute("select id, gruppa from teachers").fetchall()
    except sqlite3.OperationalError:
        return {}
    return {row["id"]: row["gruppa"] for row in rows if row["gruppa"]}


def _open_assignments(
    connection: sqlite3.Connection, slot: int
) -> dict[int, dict]:
    """``{student_id: {teacher_id, room, valid_from}}`` for the open rows."""
    rows = connection.execute(
        "select student_id, teacher_id, room, valid_from from enrollment "
        "where slot = ? and valid_to = ?",
        (slot, "9999-12-31"),
    ).fetchall()
    return {row["student_id"]: dict(row) for row in rows}


def _build_views(connection: sqlite3.Connection, slot: int) -> dict:
    _obespechit_aktivnost(connection)
    students = _all_students(connection)
    teachers = _all_teachers(connection)
    assignments = _open_assignments(connection, slot)

    by_students: list[dict] = []
    for student in students:
        assignment = assignments.get(student["id"])
        by_students.append({
            "student_id": student["id"],
            "surname": student["surname"],
            "name": student["name"],
            "class": student["class"],
            "teacher_id": assignment["teacher_id"] if assignment else None,
            "teacher_name": (
                next((t["name"] for t in teachers
                      if t["id"] == assignment["teacher_id"]), None)
                if assignment else None
            ),
            "room": assignment["room"] if assignment else None,
        })

    # 🔴 КАБИНЕТ ДЕРЖИТСЯ ГРУППОЙ, а не человеком (ТЗ §5). Меняешь кабинет группы —
    # меняется у всех её людей одним действием. Поэтому кабинет школьника и
    # преподавателя ВЫЧИСЛЯЮТСЯ, а не хранятся у каждого.
    kab_gruppy, starshie = _kabinety_grupp(connection)
    gruppa_prepoda = {t_["id"]: t_.get("gruppa") for t_ in teachers}
    svoya_gruppa = {s["id"]: s.get("gruppa") for s in students}
    byloe = _byvshaya_gruppa(connection, slot)
    gruppa_lyubogo = _gruppy_vseh_prepodavatelej(connection)
    for row in by_students:
        # 🔴 ТРИ СТУПЕНИ ЧИТАЮТСЯ ЗДЕСЬ, И ПОРЯДОК ВАЖЕН.
        #  1. У назначенного группа — ГРУППА ЕГО ПРЕПОДАВАТЕЛЯ. Перевели
        #     преподавателя — школьники уехали с ним сами, потому что группа
        #     вычисляется, а не хранится у каждого.
        #  2. Иначе — то, что человек поставил руками. Пустая строка здесь
        #     значит «нигде» И ЭТО РЕШЕНИЕ, а не отсутствие данных: без такой
        #     разницы «нигде» не держалось бы — пункт 3 возвращал бы ребёнка
        #     в покинутую группу при первой же перерисовке.
        #  3. И только если руками не трогали — память закрытых строк.
        svoy = svoya_gruppa.get(row["student_id"])
        if gruppa_prepoda.get(row["teacher_id"]):
            g = gruppa_prepoda[row["teacher_id"]]
        elif svoy is not None:
            g = svoy or None
        else:
            g = gruppa_lyubogo.get(byloe.get(row["student_id"]))
        row["gruppa"] = g
        row["room"] = kab_gruppy.get(g)
        row["starshij"] = starshie.get(g)

    by_teachers: list[dict] = []
    for teacher in teachers:
        kids = [row for row in by_students if row["teacher_id"] == teacher["id"]]
        by_teachers.append({
            "teacher_id": teacher["id"],
            "name": teacher["name"],
            "gruppa": teacher.get("gruppa"),
            "kabinet": kab_gruppy.get(teacher.get("gruppa")),
            "starshij": starshie.get(teacher.get("gruppa")),
            "load": len(kids),
            "students": [
                {"student_id": k["student_id"], "surname": k["surname"],
                 "name": k["name"]}
                for k in kids
            ],
        })

    return {
        "slot": slot,
        # День занятия и состав групп страница показывает в шапке; правило
        # «ближайший четверг или суббота» живёт в ОДНОМ месте — `veb/sobrat_fajl.py`,
        # чтобы сайт и файл не начали называть разные дни (так уже было).
        "data": blizhajshee_zanyatie(),
        "gruppy": [
            {"kod": k, "starshij": starshie.get(k), "kabinet": kab_gruppy.get(k)}
            for k in ("В", "Д", "Н")
        ],
        "students": by_students,
        "teachers": by_teachers,
    }


# -------------------------------------------------------------- request handler

class Handler(BaseHTTPRequestHandler):
    """One class, all routes.  The server is short enough that one class beats two."""

    server_version = "SpetsmatRaspred/0.1"

    def log_message(self, format, *args):  # silence the default stderr noise
        pass

    def _send_json(self, status: int, payload) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _connection(self) -> sqlite3.Connection:
        # ``ThreadingHTTPServer`` handles every request on its own thread, and
        # SQLite objects created in one thread cannot be used in another.  The
        # clean answer is to open a per-request connection with
        # ``check_same_thread=False`` and apply the project's pragmas on top of
        # it.  WAL lets readers and the writer run side by side; the test
        # fixture substitutes ``server.db_path`` for a tmp file.
        db_path = getattr(self.server, "db_path", config.DB_PATH)  # type: ignore[attr-defined]
        raw = sqlite3.connect(
            str(db_path), check_same_thread=False,
            isolation_level=None,  # we drive transactions explicitly via the repo
        )
        raw.execute("pragma foreign_keys = on")
        raw.execute("pragma journal_mode = WAL")
        raw.execute("pragma synchronous = normal")
        raw.execute("pragma busy_timeout = %d" % config.BUSY_TIMEOUT_MS)
        raw.row_factory = sqlite3.Row
        return raw

    # --------------------------------------------------------------- GET routes

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path.startswith("/materials/"):
            rel = path[len("/materials/"):].lstrip("/")
            if ".." in rel.split("/"):
                self._send_json(404, {"error": "not found"})
                return
            target = (MATERIALS_DIR / rel).resolve()
            try:
                target.relative_to(MATERIALS_DIR.resolve())
            except ValueError:
                self._send_json(404, {"error": "not found"})
                return
            if not target.is_file():
                self._send_json(404, {"error": "not found"})
                return
            body = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf" if target.suffix == ".pdf" else "application/octet-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path.startswith("/static/"):
            _serve_static(self, path)
            return
        if path in vhod.marshruty():
            self._send_html(200, vhod.marshruty()[path]())
            return
        if path == "/vhod" or path == "/vyhod":
            # Entry pages always open, no cookie required.
            pass  # fall through to marshruty handler below
        elif path in vhod.marshruty():
            # /vhod and /vyhod handled by marshruty
            pass  # already handled above; actually marshruty is only /vhod and /vyhod
        # 🔴 КОРЕНЬ — ОДИН И ТОТ ЖЕ САЙТ ДЛЯ ВСЕХ, РАЗНИЦУ ДЕЛАЕТ КУКА. Гостю
        # уходит файл `docs/index.html`, пересобранный последней успешной правкой;
        # организатору — та же страница, порождённая ТЕМ ЖЕ кодом, но с органами
        # правки в разделе распределения. Отдельной админки с собственной вёрсткой
        # больше нет: две вёрстки одного и того же уже разъезжались, и разъезд был
        # виден глазом на списке преподавателей.
        if path == "/":
            self._send_html(200, self._koren())
            return
        # 🔴 ТРИ ЛИШНИЕ СТРАНИЦЫ УВОДЯТ НА ЛЕНДИНГ. Владелец: «если заходишь на
        # листок — остаёшься на лендинге и видишь статичную версию». Их прежние
        # заглушки он видел на сервере и раздражался; сами шаблоны уехали в `arhiv/`.
        if path in ("/glavnaya", "/listki", "/listki-8"):
            self.send_response(302)
            self.send_header("Location", "/")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if path == "/raspredelenie":
            index = (TEMPLATES_DIR / "index.html").read_bytes()
            self._send_html(200, index)
            return
        if path == "/api/teachers":
            self._send_json(200, _all_teachers(self._connection()))
            return
        if path == "/api/view":
            slot = self._read_slot()
            if slot is None:
                self._send_json(400, {"error": "slot must be 1..7"})
                return
            self._send_json(200, _build_views(self._connection(), slot))
            return
        self._send_json(404, {"error": "not found"})

    def _koren(self) -> bytes:
        """Байты корневой страницы: гостю — файл, организатору — живой рендер.

        🔴 ГОСТЬ ПОЛУЧАЕТ ФАЙЛ, А НЕ РЕНДЕР, И ЭТО НАРОЧНО. Файл пересобирается
        после каждой успешной правки, поэтому он не устаревает; зато если сборка
        сломана, публичная половина сайта продолжает работать вчерашними байтами
        вместо того, чтобы отдать 500 всем сразу. Организатор рендерится живьём:
        он единственный, кому нужно видеть базу секунда-в-секунду, и он же тот,
        кто узнает о поломке сборки первым — его правка просто не пройдёт.
        """
        if vhod.rol(self.headers) == "organizator":
            from tools.sobrat_stranicu import sobrat_html
            return sobrat_html("admin").encode("utf-8")
        if not PUBLICHNAYA.is_file():
            # Файла нет вовсе — собрать его прямо сейчас. Падение здесь честнее
            # заглушки: отдавать «страница в разработке» на боевом адресе значит
            # прятать поломку ровно от того, кто может её починить.
            _peresobrat()
        return PUBLICHNAYA.read_bytes()

    def _read_slot(self) -> Optional[int]:
        from urllib.parse import parse_qs
        query = parse_qs(urlparse(self.path).query)
        raw = query.get("slot", ["1"])[0]
        try:
            n = int(raw)
        except ValueError:
            return None
        if not 1 <= n <= 7:
            return None
        return n

    # --------------------------------------------------------------- POST routes

    def _pravka_zapreshchena(self) -> bool:
        """Пускать ли правку. ОДНО место на все правящие роуты, и в этом смысл.

        🔴 Д1, найдено живым прогоном: `/api/prepodavateli` спрашивал роль
        напрямую и потому отвечал 403 ВСЕГДА. Пароль сегодня выключен
        (`SVOBODNAYA_PRAVKA`), куки никто не ставит, роли нет — отказ на любой
        запрос, и вкладка преподавателей на сервере была мертва. Условие стояло
        в двух местах, и второе о переключателе просто не знало. Теперь место одно.

        Механизм входа не удалён и работает: `veb/vhod.py`, роуты `/vhod` и
        `/vyhod`, подпись куки, роли. Вернуть пароль завтра — снять переключатель.
        """
        if SVOBODNAYA_PRAVKA:
            return False
        role = vhod.rol(self.headers)
        if role is None:
            self.send_response(302)
            self.send_header("Location", "/vhod")
            self.end_headers()
            return True
        if role != "organizator":
            self._send_json(403, {"error": "правит только организатор"})
            return True
        return False

    def _s_peresborkoj(self, rabota) -> None:
        """Правка → пересборка публичной страницы → и только потом ответ.

        🔴 СБОРКА УПАЛА — СОХРАНЕНИЕ ТОЖЕ УПАЛО. Решение владельца 2026-09-06, и у
        него есть цена, о которой он предупреждён: сохранение чуть медленнее.
        Альтернатива дороже — пропустить правку при упавшей сборке значит вернуться
        ровно к тому, от чего уходим: база новая, публичная страница вчерашняя, и
        никто об этом не знает, пока кто-нибудь не сверит их глазами.

        Ответ обработчика БУФЕРИЗУЕТСЯ, а не уходит сразу: 200, отправленный до
        пересборки, — это обещание, которое некому взять назад. Обработчиков три,
        и `_send_json` они зовут из десятка мест — перехват на одном методе дешевле
        и надёжнее, чем возврат кода через все ветки.
        """
        bufer = []
        nastoyashchij = self._send_json
        self._send_json = lambda status, payload: bufer.append((status, payload))
        try:
            rabota()
        finally:
            self._send_json = nastoyashchij
        status, payload = bufer[-1] if bufer else (500, {"error": "обработчик не ответил"})
        if not 200 <= status < 300:
            self._send_json(status, payload)
            return
        try:
            _peresobrat()
        except Exception as exc:  # noqa: BLE001 — текст обязан доехать до человека
            # Сюда попадаем только если сборка сломалась МЕЖДУ проверкой и записью:
            # база уже изменена, страница — нет. Молчать об этом нельзя.
            self._send_json(500, {"error":
                "правка СОХРАНЕНА в базу, но публичная страница НЕ пересобрана: "
                "%s: %s. Страница показывает прежние данные." % (type(exc).__name__, exc)})
            return
        if isinstance(payload, dict):
            payload = dict(payload)
            payload["stranica_peresobrana"] = True
        self._send_json(status, payload)

    def _sborka_nevozmozhna(self) -> bool:
        """Отказать ДО записи, если пересобрать страницу будет нечем."""
        try:
            _sborka_vozmozhna()
        except Exception as exc:  # noqa: BLE001
            self._send_json(500, {"error":
                "правка НЕ применена: публичную страницу нечем пересобрать — "
                "%s: %s" % (type(exc).__name__, exc)})
            return True
        return False

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/vhod":
            self._post_vhod()
            return
        if path == "/api/kabinety":
            # 🔴 КАБИНЕТ ГРУППЫ НА ДЕНЬ. Владелец: «если завтра у меня будет другой
            # кабинет, я захожу через админпанель и меняю закрепление В на другой
            # кабинет — и всё отображается сразу везде». Правка одной строки меняет
            # кабинет у всех людей группы, потому что он вычисляется, а не хранится.
            # 🔴 Владелец 2026-09-05: кабинеты правят те же люди, что распределение
            # и листки — права у трёх правящих роутов одинаковые.
            if self._pravka_zapreshchena():
                return
            if self._sborka_nevozmozhna():
                return
            self._s_peresborkoj(self._post_kabinety)
            return
        if path == "/api/prepodavateli":
            if self._pravka_zapreshchena():
                return
            if self._sborka_nevozmozhna():
                return
            self._s_peresborkoj(self._post_prepodavateli)
            return
        if path == "/api/enrollment":
            # 🔴 ПРАВКА ЗА ПАРОЛЕМ — решение владельца 2026-09-06 (см. SVOBODNAYA_PRAVKA).
            # Публичная половина сайта при этом открыта всем и пароля не спрашивает.
            if self._pravka_zapreshchena():
                return
            if self._sborka_nevozmozhna():
                return
            self._s_peresborkoj(self._post_enrollment)
            return
        self._send_json(404, {"error": "not found"})

    def _post_kabinety(self) -> None:
        """🔴 КАБИНЕТ ГРУППЫ НА ДЕНЬ. Владелец: «если завтра у меня будет другой
        кабинет, я захожу через админпанель и меняю закрепление В на другой
        кабинет — и всё отображается сразу везде». Правка одной строки меняет
        кабинет у всех людей группы, потому что он вычисляется, а не хранится.
        🔴 Владелец 2026-09-05: кабинеты правят те же люди, что распределение
        и листки — права у трёх правящих роутов одинаковые.
        """
        try:
            p = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        except (ValueError, TypeError):
            self._send_json(400, {"error": "нечитаемое тело"})
            return
        gruppa, kabinet = p.get("gruppa"), (p.get("kabinet") or "").strip()
        if gruppa not in ("В", "Д", "Н") or not kabinet:
            self._send_json(400, {"error": "нужны gruppa (В|Д|Н) и kabinet"})
            return
        from datetime import date as _d
        den = p.get("data") or _d.today().isoformat()
        conn = self._connection()
        conn.execute(
            "insert or replace into kabinet_na_den (data, gruppa, kabinet) values (?,?,?)",
            (den, gruppa, kabinet))
        conn.commit()
        self._send_json(200, {"gruppa": gruppa, "kabinet": kabinet, "data": den})

    def _post_vhod(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b""
        from urllib.parse import parse_qs
        form = parse_qs(raw.decode("utf-8"), keep_blank_values=True)
        submitted = (form.get("parol", [""])[0] or "")
        role = vhod._check_password(submitted)
        if role is None:
            self._send_html(401, _BAD_LOGIN_HTML)
            return
        self.send_response(302)
        self.send_header("Location", "/")
        cookie_value = vhod._make_cookie(role)
        self.send_header(
            "Set-Cookie",
            f"{vhod.COOKIE_NAME}={cookie_value}; Path=/; HttpOnly; SameSite=Lax; "
            f"Max-Age={vhod.COOKIE_MAX_AGE_SECONDS}",
        )
        self.end_headers()

    def _post_prepodavateli(self) -> None:
        """Добавить преподавателя, снять с активных, вернуть в активные, задать кабинет.

        Без правки кода и без миграции — требование владельца 2026-09-04.
        Удаления НЕТ ни в одном действии: за преподавателем висит история.
        """
        try:
            payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        except (ValueError, TypeError):
            self._send_json(400, {"error": "нечитаемое тело"})
            return
        deystvie = payload.get("deystvie")
        connection = self._connection()
        _obespechit_aktivnost(connection)

        if deystvie == "dobavit":
            imya = (payload.get("name") or "").strip()
            if not imya:
                self._send_json(400, {"error": "имя обязательно"})
                return
            est = connection.execute(
                "select id from teachers where name = ?", (imya,)).fetchone()
            if est:
                # Повтор не плодит человека — возвращаем в активные.
                connection.execute("update teachers set aktiven = 1 where id = ?", (est["id"],))
                connection.commit()
                self._send_json(200, {"teacher_id": est["id"], "vernuli": True})
                return
            cur = connection.execute(
                "insert into teachers (name, aka, is_owner, kabinet, aktiven) values (?, ?, 0, ?, 1)",
                (imya, payload.get("aka") or imya[:2], payload.get("kabinet")))
            connection.commit()
            self._send_json(200, {"teacher_id": cur.lastrowid})
            return

        tid = payload.get("teacher_id")
        if not tid:
            self._send_json(400, {"error": "нужен teacher_id"})
            return
        if deystvie == "ubrat":
            connection.execute("update teachers set aktiven = 0 where id = ?", (tid,))
        elif deystvie == "vernut":
            connection.execute("update teachers set aktiven = 1 where id = ?", (tid,))
        elif deystvie == "kabinet":
            connection.execute("update teachers set kabinet = ? where id = ?",
                               (payload.get("kabinet"), tid))
        elif deystvie == "gruppa":
            # 🔴 ПРЕПОДАВАТЕЛЬ УХОДИТ — ДЕТИ ОСТАЮТСЯ. Правило владельца 06.09,
            # дословно: «смена группы у преподавателя → все его дети автоматически
            # открепляются и остаются в своих группах; преподаватель приходит в
            # новую группу без детей». Это ПРАВИЛО, а не побочный эффект.
            #
            # 🔴 ЭТО ОБРАТНОЕ ПРЕЖНЕМУ ПОВЕДЕНИЮ, И ПОТОМУ НАПИСАНО ЯВНО. Раньше
            # школьники ехали за человеком: их `students.gruppa` переписывалась на
            # новую. Владелец назвал ровно противоположное — ребёнок занимается в
            # своей группе, и уход преподавателя не должен переселять ребёнка.
            #
            # Порядок здесь и есть содержание правила: СНАЧАЛА запоминаем каждому
            # ребёнку его ТЕКУЩУЮ группу (иначе после закрытия строки её негде
            # взять — она вычислялась из преподавателя), ПОТОМ закрываем строки
            # закрепления, и только ПОТОМ двигаем самого преподавателя.
            gruppa = payload.get("gruppa")
            if gruppa not in ("В", "Д", "Н"):
                self._send_json(400, {"error": "группа: В | Д | Н"})
                return
            _obespechit_gruppu_shkolnika(connection)
            staraya = connection.execute(
                "select gruppa from teachers where id = ?", (tid,)).fetchone()
            staraya = staraya["gruppa"] if staraya else None
            otkrepleny = []
            if staraya and staraya != gruppa:
                deti = connection.execute(
                    "select id, student_id, valid_from from enrollment "
                    "where teacher_id = ? and valid_to = ?",
                    (tid, "9999-12-31")).fetchall()
                segodnya = datetime.now(ZoneInfo("Europe/Moscow")).date().isoformat()
                for stroka in deti:
                    connection.execute(
                        "update students set gruppa = ? where id = ?",
                        (staraya, stroka["student_id"]))
                    if stroka["valid_from"] >= segodnya:
                        # Интервал, ещё НЕ НАЧАВШИЙСЯ, удаляется, а не закрывается:
                        # схема требует `valid_from < valid_to`, а терять тут нечего —
                        # по такой строке ребёнок ещё ни к кому не сходил. Тот же
                        # приём и то же `>=`, что в `_snyat_shkolnika`, и по той же
                        # причине: `valid_from` открытых строк лежит в будущем.
                        connection.execute("delete from enrollment where id = ?",
                                           (stroka["id"],))
                    else:
                        connection.execute(
                            "update enrollment set valid_to = ? where id = ?",
                            (segodnya, stroka["id"]))
                    otkrepleny.append(stroka["student_id"])
            connection.execute("update teachers set gruppa = ? where id = ?", (gruppa, tid))
            connection.commit()
            self._send_json(200, {"ok": True, "otkrepleny": otkrepleny,
                                  "iz_gruppy": staraya, "v_gruppu": gruppa})
            return
        else:
            self._send_json(400, {
                "error": "деиствие: dobavit | ubrat | vernut | kabinet | gruppa"})
            return
        connection.commit()
        self._send_json(200, {"ok": True})

    def _snyat_shkolnika(self, conn, student_id: int, slot: int,
                         gruppa, den: str) -> None:
        """Две ступени без преподавателя: «нигде» и «в группе, но без него».

        Разница между ними — ровно поле `students.gruppa`: у первой оно пустое,
        у второй хранит группу, в которой ребёнок числится, пока ему не нашли
        принимающего. Именно её отсутствие и роняло ребёнка с вкладки в тот
        момент, когда его надо было кому-то отдать.
        """
        if gruppa not in (None, "", "В", "Д", "Н"):
            self._send_json(400, {"error": "группа: В | Д | Н или пусто"})
            return
        _obespechit_gruppu_shkolnika(conn)
        # 🔴 ПУСТАЯ СТРОКА, А НЕ NULL. «Нигде» — это ВЫБОР человека, и он обязан
        # отличаться от «про этого ребёнка ещё ничего не решали»: иначе память
        # закрытых строк вернула бы его в старую группу, и снять его оттуда было
        # бы нечем — ровно та поломка, ради которой ступеней стало три.
        conn.execute("update students set gruppa = ? where id = ?",
                     (gruppa or "", student_id))
        repo = SqliteEnrollmentRepo(conn)
        standing = repo.open_row(student_id, slot)
        itog = {"snyat": True, "gruppa": gruppa or None}  # наружу — по-прежнему None
        if standing is not None:
            if standing.valid_from >= den:
                # 🔴 Интервал, КОТОРЫЙ ЕЩЁ НЕ НАЧАЛСЯ, УДАЛЯЕТСЯ, а не закрывается.
                # Закрыть его сегодняшним днём схема не даёт: `check (valid_from
                # < valid_to)`. И терять тут нечего — ребёнок по этой строке ещё
                # ни разу ни к кому не сходил. История прошлых дней не трогается.
                # 🔴 БЫЛО `== den`, СТАЛО `>= den`, и это не косметика: `valid_from`
                # у открытых строк лежит В БУДУЩЕМ — их ставит импорт датой
                # БЛИЖАЙШЕГО занятия, а не сегодняшним днём. Замер на живой базе
                # 2026-09-06: из 106 открытых строк 24 стоят на 2026-09-07 и 8 на
                # 2026-09-10. На них `== den` не срабатывал, дело доходило до
                # `close(valid_to=den)` с `valid_to < valid_from`, и схема роняла
                # правку. То есть тридцать два ребёнка из пятидесяти трёх сегодня
                # не откреплялись вовсе.
                conn.execute("delete from enrollment where id = ?", (standing.id,))
                itog["udalen"] = standing.id
            else:
                repo.close(standing.id, valid_to=den)
                itog["zakryt"] = standing.id
        conn.commit()
        self._send_json(200, itog)

    def _post_enrollment(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(400, {"error": "body is not JSON"})
            return

        try:
            student_id = int(payload["student_id"])
            # 🔴 `teacher_id: null` — ЗАКОННОЕ ЗНАЧЕНИЕ, а не отсутствие поля.
            # Ступеней у школьника три, и две из них без преподавателя: «нигде»
            # и «в группе, преподаватель ещё не выбран». Пока ступень была одна,
            # ребёнок бывшего преподавателя навсегда оставался в его группе:
            # убрать его оттуда было нечем.
            syroj = payload["teacher_id"]
            teacher_id = None if syroj is None or syroj == "" else int(syroj)
            slot = int(payload.get("slot", SLOT_DEFAULT))
        except (KeyError, TypeError, ValueError):
            self._send_json(400, {"error": "student_id, teacher_id and slot are required"})
            return
        if not 1 <= slot <= 7:
            self._send_json(400, {"error": "slot must be 1..7"})
            return

        effective_from = datetime.now(ZoneInfo("Europe/Moscow")).date().isoformat()
        try:
            date.fromisoformat(effective_from)
        except ValueError:
            self._send_json(500, {"error": "today is not a calendar day"})
            return

        conn = self._connection()
        if teacher_id is None:
            self._snyat_shkolnika(conn, student_id, slot,
                                  payload.get("gruppa"), effective_from)
            return

        # Группа назначенного — группа его преподавателя, и её запоминаем СРАЗУ:
        # завтра, когда ребёнка снимут, это единственное, что скажет, где он был.
        # Пишется до правки интервала намеренно — пока преподаватель стоит,
        # показанная группа всё равно вычисляется из него, и запись не видна.
        _obespechit_gruppu_shkolnika(conn)
        conn.execute(
            "update students set gruppa = (select gruppa from teachers where id = ?) "
            "where id = ?", (teacher_id, student_id))
        conn.commit()

        repo = SqliteEnrollmentRepo(conn)
        service = EnrollmentService(repo)
        try:
            move = service.move(
                student_id=student_id,
                slot=slot,
                to_teacher_id=teacher_id,
                effective_from=effective_from,
            )
        except NotEnrolled:
            # No open row to move from — try to assign instead.  This is the path
            # taken when the page is the FIRST place that opens an interval for
            # this child (the import did not see the child for some reason), and
            # ALSO the path back after a detach: крестик и смена группы
            # преподавателя закрывают строку, а вернуть ребёнка можно только сюда.
            #
            # 🔴 НАЧАЛО ИНТЕРВАЛА — НЕ ВСЕГДА СЕГОДНЯ, И БЕЗ ЭТОГО ОТКРЕПЛЕНИЕ
            # НЕОБРАТИМО. Закрытые строки этого ребёнка могут кончаться В БУДУЩЕМ:
            # `valid_to` им ставит импорт датой ближайшего занятия. Новый интервал,
            # открытый сегодняшним днём, пересекается с таким закрытым, и частичный
            # уникальный индекс отвечает «intervals for one (student_id, weekday)
            # must not overlap» — то есть ребёнка, которого только что открепили,
            # обратно прикрепить НЕЧЕМ.
            #
            # Найдено живым прогоном на боевой базе 2026-09-06: после проверки
            # правила «смена группы преподавателя открепляет детей» три открепления
            # из шести не восстанавливались через интерфейс, и состояние пришлось
            # чинить SQL-ом по снимку. Критерий готовности требует «вернуть как
            # было» — значит обратимость и есть часть работы, а не удобство.
            #
            # Берём максимум из сегодня и последнего `valid_to` закрытых строк:
            # раньше него открывать нельзя, позже — незачем.
            granica = conn.execute(
                "select max(valid_to) from enrollment "
                "where student_id = ? and slot = ? and valid_to <> ?",
                (student_id, slot, "9999-12-31")).fetchone()[0]
            nachalo = max(effective_from, granica) if granica else effective_from
            try:
                opened = service.assign(
                    student_id=student_id,
                    teacher_id=teacher_id,
                    room="000",  # placeholder — caller must follow up via move if wrong
                    slot=slot,
                    valid_from=nachalo,
                )
            except EnrollmentError as exc:
                self._send_json(409, {"error": str(exc)})
                return
            self._send_json(200, {"assigned": opened.id})
            return
        except MoveNotForward:
            # 🔴 ВТОРАЯ ПРАВКА ТОЙ ЖЕ СТРОКИ В ТОТ ЖЕ ДЕНЬ. Найдено живым прогоном
            # 2026-09-04: сервис закрывает старый интервал сегодняшним днём и открывает
            # новый тем же днём, а если стоящий интервал ТОЖЕ открыт сегодня, выходит
            # valid_from == valid_to, схема это запрещает, и правка падает с 409.
            # Для владельца это значило: строку можно поменять ОДИН раз в день, вторая
            # попытка молча не проходит — а он правит распределение перед занятием и
            # переставляет одного и того же ребёнка по нескольку раз.
            #
            # ЧТО ДЕЛАЕМ: интервал, КОТОРЫЙ ЕЩЁ НЕ НАЧАЛСЯ (открыт сегодня или
            # позже), правим НА МЕСТЕ. Истории это не теряет: по такой строке
            # ребёнок ни к кому сходить не успел. Прошлое не трогается вовсе.
            #
            # 🔴 УСЛОВИЕ РАСШИРЕНО С «== сегодня» ДО «>= сегодня», И БЕЗ ЭТОГО
            # ТРЕТЬ ДЕТЕЙ НЕ ПРАВИЛАСЬ ВООБЩЕ. Открытые строки несут `valid_from`
            # ближайшего ЗАНЯТИЯ, а не сегодняшнюю дату: их так ставит импорт. На
            # живой базе 2026-09-06 это 24 строки на 2026-09-07 и 8 на 2026-09-10.
            # Для них `move` давал `MoveNotForward`, а ветка «правим на месте» не
            # узнавала свой случай и отвечала 409. Найдено прогоном, не чтением:
            # первая же попытка сменить преподавателя первому по алфавиту ребёнку
            # вернула отказ.
            standing = repo.open_row(student_id, slot)
            if standing is None or standing.valid_from < effective_from:
                self._send_json(409, {"error":
                    "интервал открыт раньше сегодняшнего дня — правка на месте небезопасна"})
                return
            if standing.teacher_id == teacher_id:
                self._send_json(200, {"bez_izmenenij": True})
                return
            kab = conn.execute(
                "select kabinet from teachers where id = ?", (teacher_id,)
            ).fetchone()
            novyj_kabinet = (kab["kabinet"] if kab and "kabinet" in kab.keys() and kab["kabinet"]
                             else standing.room)
            conn.execute(
                "update enrollment set teacher_id = ?, room = ? where id = ?",
                (teacher_id, novyj_kabinet, standing.id),
            )
            conn.commit()
            self._send_json(200, {"pravka_na_meste": standing.id, "room": novyj_kabinet})
            return
        except MoveChangesNothing as exc:
            # The same teacher was chosen: that is not an error, but it is also
            # not a write.  Reply 200 with a flag so the page does not toast.
            self._send_json(200, {"no_change": True, "reason": str(exc)})
            return
        except EnrollmentError as exc:
            self._send_json(409, {"error": str(exc)})
            return
        self._send_json(200, {
            "closed": move.closed.id,
            "opened": move.opened.id,
        })


# --------------------------------------------------------------------- boot

def make_server(
    connection: sqlite3.Connection, port: int
) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.connection = connection  # type: ignore[attr-defined]
    return server


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=PORT_DEFAULT)
    parser.add_argument("--bind", default="127.0.0.1")
    args = parser.parse_args(argv)

    # Refuse to serve without the signing secret.  This is the STARTUP guard that used
    # to sit at import time in veb/vhod.py, where it broke test collection instead.
    vhod.proverit_okruzhenie()

    connection = connect()
    try:
        server = ThreadingHTTPServer((args.bind, args.port), Handler)
        server.connection = connection  # type: ignore[attr-defined]
        print(f"veb-raspredelenie serving on http://{args.bind}:{args.port}/")
        print("(Ctrl-C to stop)")
        server.serve_forever()
    finally:
        connection.close()


if __name__ == "__main__":
    sys.exit(main())