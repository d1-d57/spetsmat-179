#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-hand — зовётся руками аналитиком при сверке состава.
# ДОЛГ, названный оркестратором 2026-09-04: живой точки вызова нет. Пока числа состава
# не сойдутся (см. вопрос [V4] мандата), автоматический вызов повесил бы красное на
# каждый прогон и приучил бы к красному, а это дороже отсутствия вызова.
"""Проверка состава: каждому ребёнку ровно две строки в enrollment.

Печатает «детей N, строк M, ожидается 2N» и возвращает 0 при сходстве
(M == 2N), 1 при расхождении. Печатает ВСЕ пять спорных чисел рядом и
говорит прямо, что они не сходятся. Выбирать «правильное» ЗАПРЕЩЕНО.
"""
import sqlite3
import sys
from collections import Counter

# TOOL-CONTRACT: called-by-hand — вызывается вручную заголовком одной команды,
# живой точки вызова в коде не имеет (это измеритель, а не часть конвейера).

# 🔴 АДРЕС, А НЕ ИМЯ. Здесь стоял путь от корня репозитория — то самое второе
# имя, из-за которого одна строка указывала на разные файлы на сервере и на
# машине владельца, и указывала успешно. Источник называет переменная среды
# `SPETSMAT_BAZA`; не названа — отказ с двумя законными адресами, а не фантом.
# Разбор — `doc/ISTOCHNIK-BAZY.md`.
def _db():
    # Корень репозитория в `sys.path` — этот файл запускают ФАЙЛОМ из `tools/`,
    # и своим корнем он тогда видит `tools/`. Тот же приём, что у двери источника.
    import pathlib
    koren = str(pathlib.Path(__file__).resolve().parent.parent)
    if koren not in sys.path:
        sys.path.insert(0, koren)
    import config
    return str(config.DB_PATH)

# Пять спорных чисел, ни одно не подтверждено другим (задание части 1).
OWNER_CLAIM = 53          # владелец назвал 53
SPEC_CLAIM = 54           # спека сайта 06_SAYT-razdely.md: таблица на 54 человека
COMPOSITION_ARITH = 55    # арифметика по изменениям состава: 56 - 2 + 1 = 55


def main() -> int:
    conn = sqlite3.connect(_db())
    # 🔴 ПЕРВОЙ СТРОКОЙ — ОТКУДА ЧИСЛА (Д1, владелец 10.09). Путь и дата последней
    # ЗАПИСИ внутри базы; красное, если база старше последнего занятия. Дата ФАЙЛА
    # для этого не годится: копирование и rsync её обновляют, не добавив ни строки.
    try:                                  # запуск и модулем, и файлом из tools/
        from core.istochnik import nazvat_i_proverit
    except ModuleNotFoundError:           # прямой запуск: корня репозитория нет в sys.path
        import sys as _s, pathlib as _p
        _s.path.insert(0, str(_p.Path(__file__).resolve().parent.parent))
        from core.istochnik import nazvat_i_proverit
    nazvat_i_proverit(conn)
    cur = conn.cursor()

    # 🔴 ТОЛЬКО АКТИВНЫЕ. Правка оркестратора 2026-09-04 18:44: ушедшие остаются в
    # таблице со `status='left'` — за школьником висит история, и удалять его нельзя.
    # Пока ушедших не было, `count(*)` совпадал с числом активных и был верен случайно;
    # в тот же час, когда владелец назвал первых двух ушедших, инструмент насчитал 57
    # вместо 55 и потребовал 114 строк вместо 110. Совпадение перестало быть верным
    # ровно тогда, когда стало важным — ровно та болезнь, ради которой инструмент и писан.
    n_students = cur.execute(
        "select count(*) from students where status is null or status <> 'left'"
    ).fetchone()[0]
    rows = cur.execute("select student_id from enrollment").fetchall()
    m_rows = len(rows)
    k = Counter(r[0] for r in rows)
    n_enrolled = len(k)
    no_rows = cur.execute(
        "select count(*) from students where (status is null or status <> 'left') "
        "and id not in (select student_id from enrollment)"
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