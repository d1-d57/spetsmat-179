#!/usr/bin/env python3
"""Проверка состава: каждому ребёнку ровно две строки в enrollment.

Печатает «детей N, строк M, ожидается 2N» и возвращает 0 при сходстве
(M == 2N), 1 при расхождении. Печатает ВСЕ пять спорных чисел рядом и
говорит прямо, что они не сходятся. Выбирать «правильное» ЗАПРЕЩЕНО.
"""
import sqlite3
import sys
from collections import Counter

DB = "data/spetsmat.db"

# Пять спорных чисел, ни одно не подтверждено другим (задание части 1).
OWNER_CLAIM = 53          # владелец назвал 53
SPEC_CLAIM = 54           # спека сайта 06_SAYT-razdely.md: таблица на 54 человека
COMPOSITION_ARITH = 55    # арифметика по изменениям состава: 56 - 2 + 1 = 55


def main() -> int:
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    n_students = cur.execute("select count(*) from students").fetchone()[0]
    rows = cur.execute("select student_id from enrollment").fetchall()
    m_rows = len(rows)
    k = Counter(r[0] for r in rows)
    n_enrolled = len(k)
    no_rows = cur.execute(
        "select count(*) from students where id not in (select student_id from enrollment)"
    ).fetchone()[0]

    expected = 2 * n_students

    print(f"детей {n_students}, строк {m_rows}, ожидается 2*{n_students}={expected}")

    print("ПЯТЬ СПОРНЫХ ЧИСЕЛ (ни одно не подтверждено другим):")
    print(f"  1. students в базе: {n_students}")
    print(f"  2. enrollment: {m_rows} строк, но {n_enrolled} разных ребёнка")
    print(f"  3. арифметика по изменениям состава: 56 - 2 + 1 = {COMPOSITION_ARITH}")
    print(f"  4. владелец назвал: {OWNER_CLAIM}")
    print(f"  5. спека сайта 06_SAYT-razdely.md: таблица на {SPEC_CLAIM} человека")

    if m_rows != expected:
        print(
            f"РАСХОЖДЕНИЕ: строк {m_rows} != ожидается {expected} "
            f"(2N, N={n_students} — число детей в students)"
        )
        print(
            f"  дополнительный факт: {n_enrolled} разных детей имеют строки, "
            f"{no_rows} детей не имеют ни одной строки"
        )
        conn.close()
        return 1

    print(f"СХОДИТСЯ: строк {m_rows} == 2N ({expected})")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())