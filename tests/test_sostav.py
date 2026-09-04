"""Тест инструмента проверки состава tools/proverka_sostava.py.

Инструмент должен краснеть (rc=1) при M != 2N и зеленеть (rc=0) при M == 2N.
Проверяется на временных базах, чтобы не зависеть от состояния data/spetsmat.db.
"""
import os
import sqlite3
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS))

import proverka_sostava  # noqa: E402


def _make_db(path: str, n_students: int, per_student: int) -> str:
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("create table students (id integer primary key)")
    cur.execute("create table enrollment (id integer primary key, student_id integer)")
    cur.executemany("insert into students (id) values (?)", [(i,) for i in range(1, n_students + 1)])
    rows = []
    for i in range(1, n_students + 1):
        for _ in range(per_student):
            rows.append((i,))
    cur.executemany("insert into enrollment (student_id) values (?)", rows)
    conn.commit()
    conn.close()
    return path


def test_red_when_m_not_2n(tmp_path, monkeypatch):
    db = _make_db(str(tmp_path / "red.db"), n_students=5, per_student=1)
    monkeypatch.setattr(proverka_sostava, "DB", db)
    assert proverka_sostava.main() == 1


def test_green_when_m_equals_2n(tmp_path, monkeypatch):
    db = _make_db(str(tmp_path / "green.db"), n_students=5, per_student=2)
    monkeypatch.setattr(proverka_sostava, "DB", db)
    assert proverka_sostava.main() == 0


def test_red_when_zero_rows(tmp_path, monkeypatch):
    db = _make_db(str(tmp_path / "zero.db"), n_students=5, per_student=0)
    monkeypatch.setattr(proverka_sostava, "DB", db)
    assert proverka_sostava.main() == 1