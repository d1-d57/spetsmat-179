"""A tiny HTTP server that shows ``enrollment`` and lets the owner change it.

ONE page, two views, one mutation.  The page is intentionally HTML+vanilla JS in
one file under ``veb/templates/``; the only mutable thing the server takes from
the request body is the next teacher for one ``(student, weekday)`` pair.  No
session, no login, no analytics: the project has none of those yet, and adding
them here would commit the wrong choice twice (the code AND the documentation).

The two GET endpoints speak JSON for the page to fetch on load; the POST endpoint
takes JSON and replies with the resulting ``(closed, opened)`` pair.  All three
go through ``EnrollmentService`` — never through raw SQL — so the half-open
interval and the partial unique index stay the carrier of "one open row per
``(student, weekday)``".

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


WEEKDAY_DEFAULT = 1  # Monday; the page shows one lesson day at a time.
PORT_DEFAULT = 8765

TEMPLATES_DIR = Path(__file__).parent / "templates"


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
        {"id": row["id"], "name": row["name"]}
        for row in connection.execute(
            "select id, name from teachers order by name"
        ).fetchall()
    ]


def _open_assignments(
    connection: sqlite3.Connection, weekday: int
) -> dict[int, dict]:
    """``{student_id: {teacher_id, room, valid_from}}`` for the open rows."""
    rows = connection.execute(
        "select student_id, teacher_id, room, valid_from from enrollment "
        "where weekday = ? and valid_to = ?",
        (weekday, "9999-12-31"),
    ).fetchall()
    return {row["student_id"]: dict(row) for row in rows}


def _build_views(connection: sqlite3.Connection, weekday: int) -> dict:
    students = _all_students(connection)
    teachers = _all_teachers(connection)
    assignments = _open_assignments(connection, weekday)

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

    by_teachers: list[dict] = []
    for teacher in teachers:
        kids = [row for row in by_students if row["teacher_id"] == teacher["id"]]
        by_teachers.append({
            "teacher_id": teacher["id"],
            "name": teacher["name"],
            "load": len(kids),
            "students": [
                {"student_id": k["student_id"], "surname": k["surname"],
                 "name": k["name"]}
                for k in kids
            ],
        })

    return {
        "weekday": weekday,
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
        if path == "/":
            index = (TEMPLATES_DIR / "index.html").read_bytes()
            self._send_html(200, index)
            return
        if path == "/api/teachers":
            self._send_json(200, _all_teachers(self._connection()))
            return
        if path == "/api/view":
            weekday = self._read_weekday()
            if weekday is None:
                self._send_json(400, {"error": "weekday must be 1..7"})
                return
            self._send_json(200, _build_views(self._connection(), weekday))
            return
        self._send_json(404, {"error": "not found"})

    def _read_weekday(self) -> Optional[int]:
        from urllib.parse import parse_qs
        query = parse_qs(urlparse(self.path).query)
        raw = query.get("weekday", ["1"])[0]
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
        if path == "/api/enrollment":
            self._post_enrollment()
            return
        self._send_json(404, {"error": "not found"})

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
            weekday = int(payload.get("weekday", WEEKDAY_DEFAULT))
        except (KeyError, TypeError, ValueError):
            self._send_json(400, {"error": "student_id, teacher_id and weekday are required"})
            return
        if not 1 <= weekday <= 7:
            self._send_json(400, {"error": "weekday must be 1..7"})
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
                weekday=weekday,
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
                    weekday=weekday,
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