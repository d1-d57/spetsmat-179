#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-hand — зовётся, когда распределение надо увезти файлом.
"""Собирает САМОДОСТАТОЧНЫЙ HTML распределения ИЗ ТОГО ЖЕ шаблона, что и сайт.

Зачем отдельный режим. Правит распределение не один человек: владелец правит своих,
отдаёт файл дальше, тот правит своих и присылает обратно. Файл лежит на диске,
работает офлайн, ничего не деплоится — сервер и туннель под это не нужны.

Зачем ОДИН шаблон. Страница сайта и рабочий файл разъехались ровно потому, что
были двумя копиями: правку приходилось вносить дважды, и вторую забывали. Теперь
вёрстка, раскладка и вся логика живут в `veb/templates/index.html`, а разница
между режимами — ровно два места: откуда данные и куда уезжает правка.

Что делает сборка, тремя действиями:

  1. ВЫРЕЗАЕТ серверный блок `/*РЕЖИМ-СЕРВЕР НАЧАЛО*/ … /*РЕЖИМ-СЕРВЕР КОНЕЦ*/`.
     🔴 Именно вырезает, а не выключает флагом: выключенный `fetch` остался бы
     ТЕКСТОМ в файле, который владелец открывает с диска и пересылает почтой.
     Файл обязан не иметь обращений к сети вовсе, а не иметь их «в рантайме».
  2. Ставит `NA_SERVERE = false` — файл читает сам себя и пишет в память браузера.
  3. Вмораживает данные вместо метки `/*ДАННЫЕ*/`.

Запуск из корня репозитория:
    python3 veb/sobrat_fajl.py                     # → data/raspredelenie.html
    python3 veb/sobrat_fajl.py --vyhod <путь>
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

KOREN = Path(__file__).resolve().parent.parent
SHABLON = KOREN / "veb" / "templates" / "index.html"
VYHOD_PO_UMOLCHANIYU = KOREN / "data" / "raspredelenie.html"
BAZA = KOREN / "data" / "spetsmat.db"

SLOT = 1  # тот же слот, что показывает страница на сервере

# 🔴 Группа у трёх ушедших записана инициалами старшего, а не кодом группы.
# Это не догадка: ДМ = Даня Макаров, НС = Наталья Стрелкова, ИЯ = Иван Яковлев —
# ровно старшие трёх групп. Чиним на чтении, базу не трогаем.
POCHINKA_GRUPPY = {"ДМ": "Д", "НС": "Н", "ИЯ": "В"}

# Записи-нелюди в таблице преподавателей: служебная заглушка и дубль Стрелковой.
NE_LYUDI = {"отсутствует", "НС"}

NACHALO = "/*РЕЖИМ-СЕРВЕР НАЧАЛО*/"
KONEC = "/*РЕЖИМ-СЕРВЕР КОНЕЦ*/"
METKA_DANNYH = "/*ДАННЫЕ*/"
METKA_REZHIMA = "let NA_SERVERE = true;          /*РЕЖИМ*/"


# 🔴 ДНИ ЗАНЯТИЙ ЖИВУТ В ОДНОМ МЕСТЕ, И ЭТО ОНО. Занятия по четвергам и субботам;
# `date.weekday()` считает от понедельника с нуля, поэтому чт = 3, сб = 5.
DNI_ZANYATIJ = {3: "четверг", 5: "суббота"}


def blizhajshij_den(weekday: int, ot: date | None = None) -> str:
    """Ближайший такой день недели, начиная с сегодняшнего.

    🔴 ДЕНЬ СЧИТАЕТСЯ, А НЕ ВПИСЫВАЕТСЯ. Вписанная руками дата протухает молча и
    начинает врать в заголовке: так `2026-09-05` и звался в коде четвергом, будучи
    субботой, а `2026-09-06` — субботой, будучи воскресеньем. Никакой гейт этого
    не видел, потому что вписанная строка всегда «верна» самой себе.
    """
    ot = ot or date.today()
    for sdvig in range(7):
        den = ot + timedelta(days=sdvig)
        if den.weekday() == weekday:
            return den.isoformat()
    raise AssertionError("за семь дней обязан встретиться любой день недели")


def blizhajshee_zanyatie(ot: date | None = None) -> str:
    """Ближайшее занятие — то есть ближайший из дней `DNI_ZANYATIJ`."""
    return min(blizhajshij_den(w, ot) for w in DNI_ZANYATIJ)


def sobrat_dannye(baza: Path, den: str) -> dict:
    # 🔴 Обычное подключение, а не `mode=ro`. База живёт в режиме WAL, а WAL,
    # открытый ТОЛЬКО НА ЧТЕНИЕ, требует рядом файл `-shm`; в свежей копии
    # репозитория его нет, и `mode=ro` падает с «unable to open database file».
    # Сборка не пишет в базу ни одной строкой — это видно по запросам ниже.
    c = sqlite3.connect(str(baza))
    c.row_factory = sqlite3.Row

    gruppy = {r["kod"]: r["starshij"] for r in c.execute("select kod, starshij from gruppy")}
    kabinety = {
        r["gruppa"]: r["kabinet"]
        for r in c.execute(
            "select gruppa, kabinet from kabinet_na_den where data = ?", (den,)
        )
    }

    prepodavateli = []
    for r in c.execute("select id, name, gruppa, aktiven from teachers order by name"):
        if r["name"] in NE_LYUDI:
            continue
        prepodavateli.append({
            "id": r["id"],
            "imya": r["name"],
            "gruppa": POCHINKA_GRUPPY.get(r["gruppa"], r["gruppa"]),
            "aktiven": bool(r["aktiven"]),
        })

    zakreplenie = {
        r["student_id"]: r["teacher_id"]
        for r in c.execute(
            "select student_id, teacher_id from enrollment "
            "where slot = ? and valid_to = '9999-12-31'", (SLOT,)
        )
    }
    # 🔴 ЗАКРЫТЫЕ строки выбрасывать нельзя. Когда преподаватель ушёл, его строки
    # закрыли датой — вместе с единственным следом того, В КАКОЙ ГРУППЕ ребёнок был.
    # Без него дети выглядят «ничьими вообще», хотя группа у них известна.
    byloe = {}
    for r in c.execute(
        "select student_id, teacher_id from enrollment "
        "where slot = ? and valid_to <> '9999-12-31' order by valid_to, id", (SLOT,)
    ):
        byloe[r["student_id"]] = r["teacher_id"]

    aktivnye_id = {p["id"] for p in prepodavateli if p["aktiven"]}
    po_id = {p["id"]: p for p in prepodavateli}

    # Своя память группы, проставленная человеком на сайте. Пустая строка здесь
    # значит «нигде» и это РЕШЕНИЕ: она сильнее памяти закрытых строк ниже, иначе
    # снятый в никуда ребёнок вернулся бы в покинутую группу при первой сборке.
    kolonki = [x[1] for x in c.execute("pragma table_info(students)")]
    svoya_gruppa = {}
    if "gruppa" in kolonki:
        svoya_gruppa = {r["id"]: r["gruppa"] for r in c.execute(
            "select id, gruppa from students where gruppa is not null")}

    shkolniki = []
    for r in c.execute(
        "select id, surname, name, class from students "
        "where status = 'active' order by surname, name"
    ):
        tid = zakreplenie.get(r["id"])
        # Закрепление на УШЕДШЕГО — это отсутствие принимающего, а не принимающий.
        # Ровно так дети и терялись: строка есть, человека за ней нет.
        if tid is not None and tid not in aktivnye_id:
            tid = None
        if tid is None:
            svoj = svoya_gruppa.get(r["id"])
            if svoj is not None:
                gruppa = svoj or None          # "" — это «нигде», а не «не решали»
            else:
                gruppa = po_id.get(byloe.get(r["id"]), {}).get("gruppa")
        else:
            gruppa = po_id.get(tid, {}).get("gruppa")
        shkolniki.append({
            "id": r["id"],
            "familiya": r["surname"],
            "imya": r["name"],
            "klass": r["class"],
            "prepodavatel": tid,
            "gruppa": gruppa,
        })

    return {
        "data": den,
        "sobrano": date.today().isoformat(),
        "gruppy": [
            {"kod": k, "starshij": gruppy.get(k), "kabinet": kabinety.get(k)}
            for k in ("В", "Д", "Н")
        ],
        "prepodavateli": prepodavateli,
        "shkolniki": shkolniki,
    }


def rezhim_fajla(shablon: str) -> str:
    """Шаблон → файловая половина: серверный блок вырезан, флаг снят."""
    if NACHALO not in shablon or KONEC not in shablon:
        sys.exit("В шаблоне нет меток режима — вырезать нечего, сборка была бы ложной.")
    out = re.sub(
        re.escape(NACHALO) + r".*?" + re.escape(KONEC), "", shablon, flags=re.S
    )
    if METKA_REZHIMA not in out:
        sys.exit("В шаблоне нет строки флага режима — файл собрался бы серверным.")
    out = out.replace(METKA_REZHIMA, "let NA_SERVERE = false;         /*РЕЖИМ*/")
    # Проверка, а не надежда: обращений к сети в собранном файле не остаётся ни
    # одного. Список — ровно то, чем страница МОЖЕТ выйти в сеть; упоминание
    # адреса в комментарии сетью не является и здесь не ловится.
    for zapreshcheno in ("fetch(", "XMLHttpRequest", "sendBeacon", "EventSource",
                         "http://", "https://"):
        if zapreshcheno in out:
            sys.exit(f"После вырезания в файле осталось «{zapreshcheno}» — файл не офлайновый.")
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--vyhod", type=Path, default=VYHOD_PO_UMOLCHANIYU)
    p.add_argument("--baza", type=Path, default=BAZA)
    p.add_argument("--den", default=None, help="день занятия ГГГГ-ММ-ДД; по умолчанию ближайший")
    args = p.parse_args(argv)

    # 🔴 КОД 2 — «ПОЗВАЛИ НЕВЕРНО», И ОН ОБЯЗАН ОТЛИЧАТЬСЯ ОТ ОСТАЛЬНЫХ ДВУХ.
    # 0 — собрал, 1 — позвали верно, но собрать нечем (шаблон без метки, в файле
    # осталась сеть), 2 — неверный вызов. Слипшись, «нет такой базы» и «шаблон
    # сломан» выглядят снаружи одинаково, и вызывающий конвейер молча идёт дальше.
    if not args.baza.is_file():
        print(f"Не нашёл базу: {args.baza}", file=sys.stderr)
        return 2

    den = args.den or blizhajshee_zanyatie()
    dannye = sobrat_dannye(args.baza, den)

    if not SHABLON.is_file():
        print(f"Не нашёл шаблон: {SHABLON}", file=sys.stderr)
        return 2

    shablon = SHABLON.read_text(encoding="utf-8")
    if METKA_DANNYH not in shablon:
        sys.exit(f"В шаблоне нет метки {METKA_DANNYH} — вставлять данные некуда.")
    fajl = rezhim_fajla(shablon).replace(
        METKA_DANNYH, json.dumps(dannye, ensure_ascii=False, separators=(",", ":")))

    args.vyhod.parent.mkdir(parents=True, exist_ok=True)
    args.vyhod.write_text(fajl, encoding="utf-8")

    net = [s for s in dannye["shkolniki"] if s["prepodavatel"] is None]
    aktivnyh = sum(1 for x in dannye["prepodavateli"] if x["aktiven"])
    print(f"собран {args.vyhod}  ({args.vyhod.stat().st_size // 1024} КБ)")
    print(f"день занятия {den} · школьников {len(dannye['shkolniki'])} · "
          f"преподавателей активных {aktivnyh}")
    print(f"не назначены: {len(net)} — " + ", ".join(s["familiya"] for s in net))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
