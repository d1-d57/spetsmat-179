#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-hand — зовётся, когда правленый файл вернулся владельцу.
"""Обратный ход круга: вносит присланный файл распределения в базу.

ЗАЧЕМ ОТДЕЛЬНЫМ ИНСТРУМЕНТОМ. Круг правки распределения состоит из двух половин, и
до сих пор в репозитории жила только одна. `veb/sobrat_fajl.py` увозит распределение
самодостаточным HTML; владелец правит его в браузере, пересылает дальше, получает
обратно — и на этом дорога кончалась. Пока сайт не выложен на сервер, файл ЕДИНСТВЕННЫЙ
канал правки, а значит обратный ход обязан быть инструментом, а не разовым скриптом из
песочницы: 05.09 его пришлось писать заново, и это ровно та работа, которую не хочется
делать во второй раз в третий.

🔴 НЕ ПУТАТЬ с `tools/import_raspredelenie.py`. Тот — РАЗОВЫЙ посев прошлогодней
раскладки из выгрузки таблицы владельца (`_studio/.../baza-2025-26.json`), он ищет людей
ПО ИМЕНАМ и законно пропускает то, что не сошлось. Этот — регулярный обратный ход, он
работает по ID и при первом же расхождении справочников не пишет НИЧЕГО.

ЧТО ДЕЛАЕТ, четырьмя действиями:

  1. ВЫНИМАЕТ JSON из `<script id="dannye">` — то самое состояние, которое кнопка
     «Скачать файлом» вморозила в файл перед отправкой.
  2. СВЕРЯЕТ СПРАВОЧНИКИ ДО ЕДИНОЙ ПРАВКИ. Каждый школьник и преподаватель обязан
     сойтись с базой И по id, И по имени. 🔴 Сверка стоит ПЕРЕД записью, а не по ходу:
     файл ездит по почте и правится руками, и разъехавшийся справочник значит, что
     присланный файл собран не с этой базы. Записать «то, что сошлось», и назвать
     остальное — здесь худший исход, чем не записать ничего: половина раскладки в базе
     хуже, чем её отсутствие, потому что выглядит как целая.
  3. ВЫЧЁРКИВАЕТ УШЕДШИХ. `prepodavatel = null` в файле — это решение человека «этого
     ребёнка в классе больше нет»: `students.status = 'left'` плюс закрытие его открытых
     строк `enrollment` через `EnrollmentService.end`. Закрытие, а не удаление: строки
     держат за собой, кто ставил ему отметки в октябре.
  4. СТАВИТ ОСТАЛЬНЫХ НА ОБА СЛОТА. Решение владельца 04.09: пока преподаватели ходят и
     в четверг, и в субботу, раскладка одна на оба дня. Файл дней не различает и различать
     не должен — поэтому один преподаватель ложится и на слот 1, и на слот 2. Кабинет
     берётся из `gruppy[].kabinet` по группе преподавателя и тем же ходом пишется в
     `kabinet_na_den` на оба учебных дня.

ИДЕМПОТЕНТНОСТЬ. Второй прогон на той же базе не открывает ни одной новой строки. Для
каждой пары `(школьник, слот)` сначала читается открытый интервал:

  * открытого нет                     → `assign`;
  * открытый с тем же (преп, кабинет) → ничего, считается «уже верно»;
  * открытый с другим                 → `move`, который закрывает старый интервал и
    открывает новый одним ходом.

Пишут только `assign`, `move` и `end`; частичный уникальный индекс в схеме не пропустит
второй открытой строки мимо них.

🔴 ЛОВУШКА, НА КОТОРОЙ ЭТОТ ИНСТРУМЕНТ УЖЕ ПОГОРЕЛ. `move` требует `effective_from`
СТРОГО больше `valid_from` стоящего интервала, а в базе есть строки, открытые БУДУЩИМ
числом: раскладку на ближайший четверг ставят заранее. Наивное `effective_from = сегодня`
на такой строке падает с `MoveNotForward` и роняет перевод. Рабочая формула — сдвиг на
день от более позднего из двух:

    eff = max(сегодня, valid_from стоящего интервала + 1 день)

Тем же числом закрываются строки ушедших: `end` проверяет то же условие.

СУХОЙ ПРОГОН — РЕЖИМ ПО УМОЛЧАНИЮ. Файл приходит по почте и от чужих рук; сначала
смотрят, что он собирается сделать, и только потом разрешают. Запись — по флагу `--pisat`.

КОДЫ ВЫХОДА:

    0 — прогон прошёл: сухой показал план, либо запись легла целиком;
    1 — база тронута, но часть переводов отбита доменом (каждый назван в отчёте);
    2 — НИЧЕГО НЕ ЗАПИСАНО: файла нет, в нём нет блока данных, или справочники не сошлись.

Запуск из корня репозитория:

    python3 tools/import_fajla_raspredeleniya.py ~/Downloads/raspredelenie-2026-09-05.html
    python3 tools/import_fajla_raspredeleniya.py <файл> --pisat
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

# Запуск идёт файлом из корня (`python3 tools/...`), и тогда на `sys.path` попадает
# `tools/`, а не корень репозитория. Тот же приём, что в соседних инструментах.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from core.services.enrollment import EnrollmentError, EnrollmentService
from infra.db import connect
from infra.enrollment_repo import SqliteEnrollmentRepo
from veb.sobrat_fajl import blizhajshij_den

# Блок с данными, который вморозила «Скачать файлом». Атрибуты после `id` берутся
# свободно: файл пересобирается браузером через `documentElement.innerHTML`, и держаться
# за точный порядок атрибутов значило бы ставить разбор в зависимость от движка.
METKA_DANNYH = re.compile(r'<script id="dannye"[^>]*>(.*?)</script>', re.S)

# 🔴 ДНИ ЗАНЯТИЙ ЖИВУТ В ОДНОМ МЕСТЕ, И ЭТО `veb/sobrat_fajl.py`. Четверг и суббота,
# `date.weekday()` от понедельника с нуля. Здесь только соответствие слоту: слот 1 —
# четверг, слот 2 — суббота. Раскладка на них одна (см. докстринг), различаются даты.
SLOT_DEN = {1: 3, 2: 5}


@dataclass
class Itog:
    """Что прогон сделал или сделал бы. Возвращается, а не печатается, — чтобы тест
    спрашивал итог, а не разбирал вывод."""

    assign: int = 0
    move: int = 0
    uzhe_verno: int = 0
    vycherknuto: int = 0
    kabinety: int = 0
    otkazy: int = 0
    #: Строки отчёта в порядке действий.
    log: list[str] = field(default_factory=list)

    def svodka(self) -> str:
        return (
            f"assign {self.assign} · move {self.move} · уже верно {self.uzhe_verno} · "
            f"вычеркнуто {self.vycherknuto} · кабинетов {self.kabinety} · "
            f"отказов {self.otkazy}"
        )


class FajlNeChitaetsya(Exception):
    """В присланном файле нет блока данных — разбирать нечего."""


# ------------------------------------------------------------------------ разбор

def dannye_iz_fajla(html: str) -> dict:
    """Состояние распределения из присланного HTML.

    Отдельной функцией, потому что это единственное место, где инструмент знает про
    вёрстку: дальше едет обычный словарь той же формы, что собирает `sobrat_dannye`.
    """
    najdeno = METKA_DANNYH.search(html)
    if najdeno is None:
        raise FajlNeChitaetsya(
            "в файле нет <script id=\"dannye\">: это не файл распределения, "
            "собранный veb/sobrat_fajl.py"
        )
    telo = najdeno.group(1).strip()
    if not telo or telo == "/*ДАННЫЕ*/":
        raise FajlNeChitaetsya(
            "блок данных пуст: это шаблон, а не собранный файл"
        )
    return json.loads(telo)


# -------------------------------------------------------------------- сверка

def sverit_spravochniki(connection: sqlite3.Connection, dannye: dict) -> list[str]:
    """Расхождения между справочниками файла и базы; пустой список — всё сошлось.

    Сверяются ОБА поля: id и имя. Одного id мало — файл правится руками и пересылается,
    и совпадение по id при разъехавшемся имени значит, что файл собран с другой базы, а
    не что кого-то переименовали. Молча положиться на id здесь — это записать раскладку
    чужого класса поверх своего.
    """
    v_baze_shk = {
        r["id"]: r["surname"]
        for r in connection.execute("select id, surname from students")
    }
    v_baze_prep = {
        r["id"]: r["name"]
        for r in connection.execute("select id, name from teachers")
    }

    bedy: list[str] = []
    for s in dannye.get("shkolniki", []):
        familiya = v_baze_shk.get(s["id"])
        if familiya is None:
            bedy.append(f"школьника id={s['id']} {s['familiya']} нет в базе")
        elif familiya != s["familiya"]:
            bedy.append(
                f"школьник id={s['id']}: файл «{s['familiya']}», база «{familiya}»"
            )
    for t in dannye.get("prepodavateli", []):
        imya = v_baze_prep.get(t["id"])
        if imya is None:
            bedy.append(f"преподавателя id={t['id']} {t['imya']} нет в базе")
        elif imya != t["imya"]:
            bedy.append(
                f"преподаватель id={t['id']}: файл «{t['imya']}», база «{imya}»"
            )
    return bedy


# ------------------------------------------------------------------ арифметика дня

def vpered_ot(stoyashchij_valid_from: str, segodnya: str) -> str:
    """День, с которого законно закрыть или подвинуть стоящий интервал.

    См. ловушку в докстринге модуля: `move` и `end` требуют дату СТРОГО больше
    `valid_from`, а раскладку на ближайший учебный день ставят заранее — будущим числом.
    """
    posle = (date.fromisoformat(stoyashchij_valid_from) + timedelta(days=1)).isoformat()
    return max(segodnya, posle)


def uchebnye_dni(ot: date | None = None) -> dict[int, str]:
    """`{слот: дата ближайшего такого учебного дня}` — по одному на каждый слот."""
    return {slot: blizhajshij_den(weekday, ot) for slot, weekday in SLOT_DEN.items()}


# ------------------------------------------------------------------------- прогон

def run(
    connection: sqlite3.Connection,
    dannye: dict,
    *,
    dni: dict[int, str],
    segodnya: str,
    pisat: bool = False,
) -> Itog:
    """Внести состояние файла в базу (или показать, что было бы внесено).

    Сверку справочников вызывающий делает САМ и до этого места: `run` уже пишет, и
    отказаться на середине означало бы оставить базу наполовину.

    `dni` и `segodnya` передаются, а не берутся из календаря внутри: инструмент,
    считающий дату сам, невозможно проверить тестом иначе как в тот единственный день,
    когда тест написан.
    """
    repo = SqliteEnrollmentRepo(connection)
    service = EnrollmentService(repo)
    itog = Itog()

    kabinet_gruppy = {g["kod"]: g.get("kabinet") for g in dannye.get("gruppy", [])}
    gruppa_prepa = {t["id"]: t.get("gruppa") for t in dannye.get("prepodavateli", [])}
    imya_prepa = {t["id"]: t["imya"] for t in dannye.get("prepodavateli", [])}

    # --- 1. ушедшие: вычеркнуть из класса ---------------------------------------
    for s in dannye.get("shkolniki", []):
        if s["prepodavatel"] is not None:
            continue
        zakryto = 0
        for slot in SLOT_DEN:
            stoit = repo.open_row(s["id"], slot)
            if stoit is None:
                continue
            eff = vpered_ot(stoit.valid_from, segodnya)
            if pisat:
                service.end(s["id"], slot=slot, effective_from=eff)
            zakryto += 1
        itog.log.append(
            f"ВЫЧЕРКНУТЬ id={s['id']} {s['familiya']} {s['imya']}: "
            f"status → left, закрыть открытых строк: {zakryto}"
        )
        itog.vycherknuto += 1
        if pisat:
            connection.execute(
                "update students set status = 'left' where id = ?", (s["id"],)
            )

    # --- 2. раскладка на ОБА слота ----------------------------------------------
    for s in dannye.get("shkolniki", []):
        teacher_id = s["prepodavatel"]
        if teacher_id is None:
            continue
        kabinet = kabinet_gruppy.get(gruppa_prepa.get(teacher_id) or "")
        if not kabinet:
            # Кабинет — часть строки enrollment, схема объявляет его not null. Пустой
            # кабинет здесь значит, что группе не назначили кабинет на день; это
            # законное состояние базы, но записать по нему нечего.
            itog.log.append(
                f"  🔴 пропуск {s['familiya']}: у группы "
                f"«{gruppa_prepa.get(teacher_id)}» нет кабинета в файле"
            )
            itog.otkazy += 1
            continue

        for slot in SLOT_DEN:
            stoit = repo.open_row(s["id"], slot)
            if stoit is None:
                itog.log.append(
                    f"  assign  {s['familiya']:22} слот{slot} → "
                    f"{imya_prepa.get(teacher_id)} каб.{kabinet}"
                )
                itog.assign += 1
                if pisat:
                    service.assign(
                        s["id"],
                        teacher_id,
                        room=kabinet,
                        slot=slot,
                        valid_from=dni[slot],
                    )
                continue
            if (stoit.teacher_id, stoit.room) == (teacher_id, kabinet):
                itog.uzhe_verno += 1
                continue
            eff = vpered_ot(stoit.valid_from, segodnya)
            itog.log.append(
                f"  move    {s['familiya']:22} слот{slot} → "
                f"{imya_prepa.get(teacher_id)} каб.{kabinet} "
                f"(было: {imya_prepa.get(stoit.teacher_id)} каб.{stoit.room}) с {eff}"
            )
            itog.move += 1
            if pisat:
                try:
                    service.move(
                        s["id"],
                        slot=slot,
                        to_teacher_id=teacher_id,
                        effective_from=eff,
                        room=kabinet,
                    )
                except EnrollmentError as exc:
                    itog.move -= 1
                    itog.otkazy += 1
                    itog.log.append(f"    🔴 {type(exc).__name__}: {exc}")

    # --- 3. кабинеты на оба учебных дня -----------------------------------------
    for slot, den in dni.items():
        for kod, kabinet in kabinet_gruppy.items():
            if not kabinet:
                continue
            bylo = connection.execute(
                "select kabinet from kabinet_na_den where data = ? and gruppa = ?",
                (den, kod),
            ).fetchone()
            bylo = bylo["kabinet"] if bylo else None
            if bylo == kabinet:
                continue
            itog.log.append(
                f"КАБИНЕТ {den} группа {kod}: {bylo or '—'} → {kabinet}"
            )
            itog.kabinety += 1
            if pisat:
                connection.execute(
                    "insert into kabinet_na_den (data, gruppa, kabinet) values (?, ?, ?) "
                    "on conflict (data, gruppa) do update set kabinet = excluded.kabinet",
                    (den, kod, kabinet),
                )

    return itog


# -------------------------------------------------------------------------- запуск

def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("fajl", type=Path, help="присланный raspredelenie-*.html")
    parser.add_argument("--baza", type=Path, default=None,
                        help="база (по умолчанию — та, что знает config)")
    parser.add_argument("--pisat", action="store_true",
                        help="записать; без флага — сухой прогон")
    args = parser.parse_args(argv)

    if not args.fajl.exists():
        print(f"файла нет: {args.fajl}", file=sys.stderr)
        return 2
    try:
        dannye = dannye_iz_fajla(args.fajl.read_text(encoding="utf-8"))
    except (FajlNeChitaetsya, json.JSONDecodeError) as exc:
        print(f"файл не разбирается: {exc}", file=sys.stderr)
        return 2

    connection = connect(args.baza)
    try:
        bedy = sverit_spravochniki(connection, dannye)
        if bedy:
            print("🔴 СПРАВОЧНИКИ НЕ СХОДЯТСЯ — ничего не пишу:")
            for beda in bedy:
                print("   -", beda)
            return 2
        print(
            f"справочники сошлись: {len(dannye.get('shkolniki', []))} школьников, "
            f"{len(dannye.get('prepodavateli', []))} преподавателей\n"
        )

        itog = run(
            connection,
            dannye,
            dni=uchebnye_dni(),
            segodnya=date.today().isoformat(),
            pisat=args.pisat,
        )
        for stroka in itog.log:
            print(stroka)
        print("\nИТОГ:", itog.svodka())

        if not args.pisat:
            print("\n(сухой прогон — база не тронута; повторить с --pisat)")
            return 0

        connection.commit()
        print(f"\n✅ записано в {args.baza or 'базу по умолчанию'}")
        aktivnyh = connection.execute(
            "select count(*) from students where status = 'active'"
        ).fetchone()[0]
        otkrytyh = connection.execute(
            "select count(*) from enrollment where valid_to = ?",
            (config.OPEN_END_DATE,),
        ).fetchone()[0]
        po_slotam = [
            tuple(r) for r in connection.execute(
                "select slot, count(*) from enrollment where valid_to = ? group by 1",
                (config.OPEN_END_DATE,),
            )
        ]
        print(f"активных школьников: {aktivnyh}")
        print(f"открытых enrollment: {otkrytyh} · по слотам: {po_slotam}")
        return 1 if itog.otkazy else 0
    finally:
        connection.close()


if __name__ == "__main__":
    sys.exit(main())
