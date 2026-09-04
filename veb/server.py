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
    NotEnrolled,
)
from infra.db import connect
from infra.enrollment_repo import SqliteEnrollmentRepo
from veb import vhod


SLOT_DEFAULT = 1  # The page shows one slot at a time.
PORT_DEFAULT = 8765

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
MATERIALS_DIR = Path("/Users/ivanyakovlev/Documents/GitHub/materials/spetsmat-2026")

GLAVNAYA_STUB = b"<!doctype html><html lang=\"ru\"><head><meta charset=\"utf-8\"><title>\xd0\x93\xd0\xbb\xd0\xb0\xd0\xb2\xd0\xbd\xd0\xb0\xd1\x8f</title></head><body><p>\xd0\xa1\xd1\x82\xd1\x80\xd0\xb0\xd0\xbd\xd0\xb8\xd1\x86\xd0\xb0 \xd0\xb2 \xd1\x80\xd0\xb0\xd0\xb7\xd1\x80\xd0\xb0\xd0\xb1\xd0\xbe\xd1\x82\xd0\xba\xd0\xb5.</p></body></html>"
LISTKI_STUB = b"<!doctype html><html lang=\"ru\"><head><meta charset=\"utf-8\"><title>\xd0\x9b\xd0\xb8\xd1\x81\xd1\x82\xd0\xba\xd0\xb8</title></head><body><p>\xd0\x9b\xd0\xb8\xd1\x81\xd1\x82\xd0\xba\xd0\xb8 \xd0\xb2 \xd1\x80\xd0\xb0\xd0\xb7\xd1\x80\xd0\xb0\xd0\xb1\xd0\xbe\xd1\x82\xd0\xba\xd0\xb5.</p></body></html>"
UROVNI_STUB = b"<!doctype html><html lang=\"ru\"><head><meta charset=\"utf-8\"><title>\xd0\xa3\xd1\x80\xd0\xbe\xd0\xb2\xd0\xbd\xd0\xb8</title></head><body><p>\xd0\xa2\xd0\xb5\xd0\xba\xd1\x81\xd1\x82 \xd0\xbf\xd1\x80\xd0\xbe \xd1\x83\xd1\x80\xd0\xbe\xd0\xb2\xd0\xbd\xd0\xb8 \xd0\xb2 \xd1\x80\xd0\xb0\xd0\xb7\xd1\x80\xd0\xb0\xd0\xb1\xd0\xbe\xd1\x82\xd0\xba\xd0\xb5.</p></body></html>"


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
    return [
        {"id": row["id"], "surname": row["surname"], "name": row["name"],
         "class": row["class"]}
        for row in connection.execute(
            "select id, surname, name, class from students "
            "where status is null or status <> 'left' order by surname, name"
        ).fetchall()
    ]


def _all_teachers(connection: sqlite3.Connection) -> list[dict]:
    return [
        {"id": row["id"], "name": row["name"], "kabinet": row["kabinet"],
         "aktiven": bool(row["aktiven"])}
        for row in connection.execute(
            "select id, name, kabinet, aktiven from teachers order by name"
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

    ruk = _rukovoditeli(connection)
    kabinet_prepoda = {t_["id"]: t_.get("kabinet") for t_ in teachers}
    for row in by_students:
        # Кабинет строки перекрывает постоянную привязку — дорога временному
        # переводу (болезнь) оставлена открытой, как просил владелец.
        kab = row["room"] or kabinet_prepoda.get(row["teacher_id"])
        row["room"] = kab
        row["rukovoditel"] = ruk.get(kab)

    by_teachers: list[dict] = []
    for teacher in teachers:
        kids = [row for row in by_students if row["teacher_id"] == teacher["id"]]
        by_teachers.append({
            "teacher_id": teacher["id"],
            "name": teacher["name"],
            "kabinet": teacher.get("kabinet"),
            "rukovoditel": ruk.get(teacher.get("kabinet")),
            "load": len(kids),
            "students": [
                {"student_id": k["student_id"], "surname": k["surname"],
                 "name": k["name"]}
                for k in kids
            ],
        })

    return {
        "slot": slot,
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
            except Value:
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
        # Reading endpoints open without cookie
        # `/glavnaya` — прощающий синоним корня. Шаблоны S3 ссылаются на него,
        # контракт волны кладёт главную на `/`; 404 в шапке каждой страницы дороже
        # одной лишней строки (решение оркестратора при сведении, 2026-09-04).
        if path in ("/", "/glavnaya"):
            glavnaya = TEMPLATES_DIR / "glavnaya.html"
            if glavnaya.is_file():
                self._send_html(200, glavnaya.read_bytes())
            else:
                self._send_html(200, GLAVNAYA_STUB)
            return
        if path == "/raspredelenie":
            index = (TEMPLATES_DIR / "index.html").read_bytes()
            self._send_html(200, index)
            return
        # 🔴 РОУТЫ ОТДАЮТ ШАБЛОНЫ S3, А НЕ JSON. Правка оркестратора при сведении
        # 2026-09-04: S1 сделала эти три роута JSON-эндпойнтами, а S3 написала под них
        # HTML-шаблоны — и они не отдавались никогда. Снаружи это выглядело как 200 с
        # пустой страницей, то есть БЕЛЫЙ ЭКРАН, ровно тот, о котором предупреждал
        # контракт имён волны. Ни один тест этого не видел: тесты судили код ответа.
        # JSON остаётся доступен под /api/listki, /api/listki-8, /api/urovni.
        for _put, _shablon in (("/listki", "listki.html"),
                               ("/listki-8", "listki8.html"),
                               ("/urovni", "urovni.html")):
            if path == _put:
                _fajl = TEMPLATES_DIR / _shablon
                if _fajl.is_file():
                    self._send_html(200, _fajl.read_bytes())
                else:
                    # Надёжность выше функционала: заглушка, а не 500.
                    self._send_html(200, ("<h1>%s</h1><p>Страница ещё не собрана.</p>" % _put).encode("utf-8"))
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

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/vhod":
            self._post_vhod()
            return
        if path == "/api/prepodavateli":
            role = vhod.rol(self.headers)
            if role != "organizator":
                self._send_json(403, {"error": "правит только организатор"})
                return
            self._post_prepodavateli()
            return
        if path == "/api/enrollment":
            role = vhod.rol(self.headers)
            if role is None:
                self.send_response(302)
                self.send_header("Location", "/vhod")
                self.end_headers()
                return
            if role != "organizator":
                self._send_json(403, {"error": "only organizator may change enrollment"})
                return
            self._post_enrollment()
            return
        self._send_json(404, {"error": "not found"})

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
        else:
            self._send_json(400, {"error": "деиствие: dobavit | ubrat | vernut | kabinet"})
            return
        connection.commit()
        self._send_json(200, {"ok": True})

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
            teacher_id = int(payload["teacher_id"])
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
            # this child (the import did not see the child for some reason).
            try:
                opened = service.assign(
                    student_id=student_id,
                    teacher_id=teacher_id,
                    room="000",  # placeholder — caller must follow up via move if wrong
                    slot=slot,
                    valid_from=effective_from,
                )
            except EnrollmentError as exc:
                self._send_json(409, {"error": str(exc)})
                return
            self._send_json(200, {"assigned": opened.id})
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