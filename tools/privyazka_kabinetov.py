#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-hand — зовётся при сведении волны и при смене состава.
"""Постоянная привязка «преподаватель → кабинет» и «кабинет → руководитель».

ЗАЧЕМ ОТДЕЛЬНЫМ ИНСТРУМЕНТОМ, а не строкой в миграции. `alter table ... add column`
в SQLite НЕ идемпотентен: второй прогон падает «duplicate column name». Миграция
обязана переживать повторный прогон, поэтому условная часть живёт здесь, где можно
спросить `pragma table_info` и решить.

ЧТО ДЕЛАЕТ, идемпотентно:
  1. добавляет `teachers.kabinet`, если его ещё нет;
  2. заполняет его из ЖИВОГО enrollment — по фактическому кабинету преподавателя;
  3. печатает связку и молчит про руководителей: кто из троих чей, решает владелец.

ЗАПУСК:  python3 tools/privyazka_kabinetov.py [--baza data/spetsmat.db]
КОДЫ:    0 — связка полная · 1 — есть преподаватель без кабинета или кабинет без руководителя
"""
import argparse
import collections
import sqlite3
import sys


def kolonki(c, tablica):
    return [r[1] for r in c.execute(f"pragma table_info({tablica})")]


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--baza", default="data/spetsmat.db")
    a = p.parse_args(argv)
    c = sqlite3.connect(a.baza)

    if "kabinet" not in kolonki(c, "teachers"):
        c.execute("alter table teachers add column kabinet text")
        c.commit()
        print("teachers.kabinet заведена")
    else:
        print("teachers.kabinet уже есть — не трогаю")

    # Кабинет преподавателя — из живых строк распределения, а не из головы.
    svyazka = collections.defaultdict(set)
    for tid, room in c.execute(
        "select teacher_id, room from enrollment "
        "where valid_to = \'9999-12-31\' and room is not null"
    ):
        svyazka[tid].add(room)

    spornye = {t: r for t, r in svyazka.items() if len(r) > 1}
    for tid, rooms in svyazka.items():
        if len(rooms) == 1:
            c.execute("update teachers set kabinet = ? where id = ?", (rooms.pop(), tid))
    c.commit()

    print()
    print("ПРЕПОДАВАТЕЛЬ → КАБИНЕТ (постоянная привязка):")
    for tid, name, kab in c.execute(
        "select id, name, kabinet from teachers where kabinet is not null order by kabinet, name"
    ):
        print(f"  {kab}  {name}")

    bez = [r[1] for r in c.execute(
        "select id, name from teachers where kabinet is null order by name")]
    print()
    print(f"без кабинета ({len(bez)}): {bez}")

    print()
    print("КАБИНЕТ → РУКОВОДИТЕЛЬ:")
    bez_ruk = []
    for kab, ruk in c.execute("select kabinet, rukovoditel_id from kabinety order by kabinet"):
        if ruk is None:
            bez_ruk.append(kab)
            print(f"  {kab}  — РУКОВОДИТЕЛЬ НЕ НАЗНАЧЕН")
        else:
            imya = c.execute("select name from teachers where id = ?", (ruk,)).fetchone()
            print(f"  {kab}  {imya[0] if imya else ruk}")

    if spornye:
        print()
        print(f"СПОРНЫЕ (преподаватель в нескольких кабинетах): {spornye}")

    plohо = bool(bez) or bool(bez_ruk) or bool(spornye)
    if plohо:
        print()
        print("РАСХОЖДЕНИЕ: связка неполная — см. выше. Руководителей назначает владелец.")
    return 1 if plohо else 0


if __name__ == "__main__":
    sys.exit(main())
