#!/usr/bin/env python3
"""Внести отметки с БУМАЖНОГО кондуита — одна дверь вместо ручных `insert`.

🔴 ЗАЧЕМ ЭТОТ ИНСТРУМЕНТ СУЩЕСТВУЕТ. Бумажные кондуиты приезжают каждое занятие,
раздела «Внести задачи» с диалогом ещё нет, и 10.09 их вносили руками дважды за
день. Ручное внесение в журнальную таблицу ломает инварианты молча: `marks` —
append-only журнал с `event`, `idempotency_key` и историей клетки, и «поставить
галочку» там не равно «вставить строку». Поэтому отметки идут ТЕМ ЖЕ швом, каким
их ставит сайт: `MarkingService.set_state`.

🔴 ЧЕГО ЭТА ДВЕРЬ НЕ ДЕЛАЕТ И НЕ БУДЕТ. Она не угадывает. Не нашёлся школьник,
листок, задача или занятие — она ОТКАЗЫВАЕТ и печатает, чего именно не нашла.
Цена угадывания заплачена в тот же день: аналитик назвал номера задач по мёртвой
локальной копии базы и был неправ дважды подряд.

🔴 ПО УМОЛЧАНИЮ НИЧЕГО НЕ ПИШЕТ. Без `--da` это проба: печатает, что БЫЛО БЫ
сделано, и выходит. Живые записи школы стоят одного лишнего флага.

Пример (проба, потом запись):
    python3 tools/vnesti_s_bumagi.py --den 2026-09-07 --shkolnik Романчук \\
        --listok 16A --zadachi 1а,1б --prepodavatel "Наталия Стрелкова" \\
        --pochemu "бумажный кондуит 07.09, ответ владельца 10.09"
    ... то же с --da
"""

from __future__ import annotations

import argparse
import pathlib
import sqlite3
import sys

KOREN = pathlib.Path(__file__).resolve().parent.parent
if str(KOREN) not in sys.path:
    sys.path.insert(0, str(KOREN))

import config                                                    # noqa: E402
from core.istochnik import SvidetelRaboty, nazvat_i_proverit      # noqa: E402
from core.models import CellState                                 # noqa: E402
from core.services.marking import MarkingService                  # noqa: E402
from infra.db import SystemClock                                  # noqa: E402
from infra.repositories import SqliteMarkJournal                  # noqa: E402

# `source` ограничен CHECK'ом четырьмя значениями, и «бумага» среди них НЕТ.
# Схему ради одной надписи не трогаем: род транспорта — «импорт», а происхождение
# едет в `note`, поле без ограничения. Это решение головы волны УТРО 10.09, и оно
# правильное: инвариант дороже удобства поиска.
ROD = "импорт"


def _odin(conn: sqlite3.Connection, zapros: str, parametry: tuple, chto: str):
    """Ровно одна строка или отказ. Ноль и два — разные болезни, и обе называются."""
    ryady = conn.execute(zapros, parametry).fetchall()
    if not ryady:
        raise SystemExit("🔴 не нашлось: %s" % chto)
    if len(ryady) > 1:
        raise SystemExit("🔴 нашлось %d вместо одного: %s — уточни" % (len(ryady), chto))
    return ryady[0]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Отметки с бумажного кондуита, через сервис.")
    p.add_argument("--den", required=True, help="день занятия, YYYY-MM-DD")
    p.add_argument("--shkolnik", required=True, help="фамилия")
    p.add_argument("--listok", required=True, help="номер листка, например 16A")
    p.add_argument("--zadachi", required=True, help="метки через запятую, например 1а,1б")
    p.add_argument("--prepodavatel", default=None, help="кто принимал (имя как в базе)")
    p.add_argument("--pochemu", required=True, help="происхождение — уедет в note")
    p.add_argument("--db", default=None, help="база (по умолчанию config.DB_PATH)")
    p.add_argument("--da", action="store_true", help="писать; без него — проба")
    p.add_argument("--vsyo-ravno", action="store_true",
                   help="писать даже в базу, которую дверь источника назвала мёртвой")
    a = p.parse_args(argv)

    put = pathlib.Path(a.db) if a.db else config.DB_PATH
    conn = sqlite3.connect(put)
    conn.row_factory = sqlite3.Row

    # 🔴 ПЕРВЫМ ХОДОМ — ИСТОЧНИК. Ровно та ловушка, в которую 10.09 попали дважды:
    # дату файла ставит checkout, а не запись данных. Дверь называет обе.
    # Отказ гейтует ЗАПИСЬ, а не пробу: разбор бумаги по мёртвой копии никому не
    # вреден и полезен — так проверяется сам разбор, до всякого доступа к боевой.
    kod = nazvat_i_proverit(conn)
    if kod != 0 and a.da and not a.vsyo_ravno:
        print("отказ: писать в базу, названную мёртвой, можно только с --vsyo-ravno")
        return 1

    shk = _odin(conn, "select id, surname, name from students where surname = ?",
                (a.shkolnik,), "школьник с фамилией %r" % a.shkolnik)
    lst = _odin(conn, "select id, number from sheets where number = ?",
                (a.listok,), "листок %r" % a.listok)
    zan = _odin(conn, "select id, held_on from sessions where held_on = ?",
                (a.den,), "занятие на %s" % a.den)

    prep = None
    if a.prepodavatel:
        prep = _odin(conn, "select id, name from teachers where name = ?",
                     (a.prepodavatel,), "преподаватель %r" % a.prepodavatel)

    metki = [m.strip() for m in a.zadachi.split(",") if m.strip()]
    est = {r["label"]: r["id"] for r in conn.execute(
        "select id, label from problems where sheet_id = ?", (lst["id"],))}
    net = [m for m in metki if m not in est]
    if net:
        print("🔴 в листке %s нет таких задач: %s" % (lst["number"], ", ".join(net)))
        print("   есть: %s" % " ".join(sorted(est)))
        return 1

    print()
    print("школьник:      %s %s (id %d)" % (shk["surname"], shk["name"], shk["id"]))
    print("листок:        %s (id %d)" % (lst["number"], lst["id"]))
    print("задачи:        %s" % ", ".join(metki))
    print("занятие:       %s (id %d)" % (zan["held_on"], zan["id"]))
    print("принимающий:   %s" % (prep["name"] if prep else "не назван"))
    print("происхождение: %s" % a.pochemu)

    if not a.da:
        print()
        print("ПРОБА. Ничего не записано. Повтори с --da, если всё верно.")
        return 0

    # `valid_at` — когда сдача произошла НА САМОМ ДЕЛЕ, и она в прошлом; полный ISO
    # требует сервис. Полдень — середина занятия, а не попытка угадать минуту.
    kogda = "%sT12:00:00Z" % a.den
    marking = MarkingService(SqliteMarkJournal(conn), SystemClock())

    with SvidetelRaboty(conn, "внесение с бумаги: %s %s, %s" % (
            shk["surname"], lst["number"], ",".join(metki))) as svid:
        napisano = 0
        for m in metki:
            itog = marking.set_state(
                shk["id"], est[m], CellState.SOLVED,
                source=ROD,
                teacher_id=prep["id"] if prep else None,
                session_id=zan["id"],
                valid_at=kogda,
                note=a.pochemu,
                idempotency_key="bumaga:%s:%d:%d" % (a.den, shk["id"], est[m]),
            )
            print("  %-4s → %s%s" % (m, itog.state,
                                     "" if itog.written else "  (уже стояло, не задвоено)"))
            napisano += 1 if itog.written else 0
        conn.commit()

    print()
    print("клеток обработано: %d · новых событий: %d" % (len(metki), napisano))
    print(svid.otchyot())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
