"""Общее состояние — сердце волны. Read from DB on every request, no process cache.

Zone: veb-vhod-i-obshchee-sostoyanie.
"""

from __future__ import annotations

import sqlite3
from typing import Optional

import config
from core.services.enrollment import EnrollmentService
from infra.db import connect


# ------------------------------------------------------------------ WAL setup

def _connect_wal(db_path: Optional[str] = None) -> sqlite3.Connection:
    # 🔴 THE DEFAULT IS RESOLVED HERE, NOT IN THE SIGNATURE.  It used to read
    # ``db_path: str = str(config.DB_PATH)``, and a default argument is evaluated when
    # the module is IMPORTED.  Once ``config.DB_PATH`` became a question the environment
    # answers, that turned ``import veb.sostoyanie`` itself into a refusal -- the whole
    # module unusable because of a default nobody had asked for yet.
    if db_path is None:
        db_path = str(config.DB_PATH)
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


# ------------------------------------------------------------------ state page

def sostoyanie_page(weekday: int = 1) -> bytes:
    """HTML page showing current enrollment state.

    The critical property of the wave: the page reads directly from the
    database on every request, with no in-memory cache in this process.
    This makes edits from another session visible immediately.
    """
    conn = _connect_wal()
    try:
        repo = __import__("infra.enrollment_repo", fromlist=[""]).SqliteEnrollmentRepo(conn)
        service = EnrollmentService(repo)
        students = __import__("core.services.enrollment", fromlist=[""]).EnrollmentService
        # Read students and open assignments directly for the page.
        cursor = conn.execute(
            "SELECT id, surname, name FROM students WHERE status IS NULL OR status <> 'left' ORDER BY surname, name"
        )
        students_rows = cursor.fetchall()
        teachers_cursor = conn.execute("SELECT id, name FROM teachers ORDER BY name")
        teachers_rows = teachers_cursor.fetchall()

        # Build assignment lookup for the given slot
        open_assignments = {}
        for row in conn.execute(
            "SELECT student_id, teacher_id, room FROM enrollment WHERE slot = ? AND valid_to = ?",
            (weekday, config.OPEN_END_DATE),
        ).fetchall():
            open_assignments[row["student_id"]] = dict(row)

        rows: list[str] = []
        for s in students_rows:
            assignment = open_assignments.get(s["id"])
            teacher_name = None
            if assignment:
                for t in teachers_rows:
                    if t["id"] == assignment["teacher_id"]:
                        teacher_name = t["name"]
                        break
            rows.append(
                f'<tr><td>{s["surname"]} {s["name"]}</td>'
                f'<td>{teacher_name or "—"}</td></tr>'
            )

        html = f"""<!doctype html>
<html lang="ru">
<head><meta charset="utf-8"><title>Общее состояние</title>
<link rel="stylesheet" href="/static/vhod.css"></head>
<body>
<header><h1>Общее состояние — распределение</h1></header>
<main>
<table>
<thead><tr><th>Ученик</th><th>Преподаватель (неделя {weekday})</th></tr></thead>
<tbody>
{''.join(rows)}
</tbody>
</table>
<p class="stale">Данные на {__import__('datetime').datetime.now(__import__('zoneinfo').ZoneInfo('Europe/Moscow')).strftime('%H:%M')}; у других могло измениться — обновите страницу.</p>
</main>
</body></html>"""
        return html.encode("utf-8")
    finally:
        conn.close()
