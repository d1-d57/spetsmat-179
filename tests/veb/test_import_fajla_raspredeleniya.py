"""Тесты обратного хода круга: присланный файл → база.

Мир строится в тесте, а не берётся с диска: инструмент разбирает файл, который ездит
по почте и правится руками, и тест обязан уметь предъявить ЛЮБОЕ его состояние —
в том числе разъехавшийся справочник, которого в живом файле нет и быть не должно.

Даты передаются в `run` явно (`dni`, `segodnya`). Инструмент, берущий календарь сам,
проверялся бы ровно в тот день, когда тест написан.
"""

from __future__ import annotations

import json
from pathlib import Path

import config
from infra.db import apply_migrations, connect
from tools.import_fajla_raspredeleniya import (
    dannye_iz_fajla,
    main,
    run,
    sverit_spravochniki,
    vpered_ot,
)

# Ближайшие учебные дни в тестовом мире; настоящие считает `uchebnye_dni`.
DNI = {1: "2026-09-10", 2: "2026-09-12"}
SEGODNYA = "2026-09-07"


def _baza(tmp_path: Path):
    """Три школьника, два преподавателя, одна группа с кабинетом."""
    path = tmp_path / "test.db"
    apply_migrations(path, config.MIGRATIONS_DIR)
    conn = connect(path)
    sheet_id = conn.execute(
        "insert into sheets (number, title, issued_at, ord) values (?, ?, ?, ?)",
        ("1", "листок 1", "2026-09-01", 1),
    ).lastrowid
    for i in range(3):
        conn.execute(
            "insert into students (surname, name, class, status, first_sheet_id) "
            "values (?, ?, ?, 'active', ?)",
            (f"Фамилия-{i}", f"Имя-{i}", "10а", sheet_id),
        )
    for i in range(2):
        conn.execute(
            "insert into teachers (name, aka, is_owner) values (?, ?, 0)",
            (f"Преподаватель-{i}", f"p{i}"),
        )
    # `kabinet_na_den.gruppa` смотрит внешним ключом в `gruppy` — без этой строки
    # запись кабинета не легла бы, и тест бы это скрыл.
    conn.execute("insert or ignore into gruppy (kod, starshij) values ('В', 'старший')")
    conn.commit()
    return conn


def _dannye(shkolniki: list[dict], prepodavateli: list[dict] | None = None) -> dict:
    return {
        "data": DNI[1],
        "gruppy": [{"kod": "В", "starshij": "старший", "kabinet": "303"}],
        "prepodavateli": prepodavateli if prepodavateli is not None else [
            {"id": 1, "imya": "Преподаватель-0", "gruppa": "В", "aktiven": True},
            {"id": 2, "imya": "Преподаватель-1", "gruppa": "В", "aktiven": True},
        ],
        "shkolniki": shkolniki,
    }


def _shkolnik(sid: int, prepodavatel: int | None) -> dict:
    return {
        "id": sid,
        "familiya": f"Фамилия-{sid - 1}",
        "imya": f"Имя-{sid - 1}",
        "klass": "10а",
        "prepodavatel": prepodavatel,
        "gruppa": "В",
    }


def _fajl(tmp_path: Path, dannye: dict, imya: str = "raspredelenie.html") -> Path:
    """Присланный файл ровно той формы, что отдаёт кнопка «Скачать файлом»."""
    path = tmp_path / imya
    path.write_text(
        "<!doctype html>\n<html lang=\"ru\"><body>\n"
        '<script id="dannye" type="application/json">'
        + json.dumps(dannye, ensure_ascii=False)
        + "</script>\n</body></html>",
        encoding="utf-8",
    )
    return path


def _otkrytyh(conn, student_id: int | None = None) -> int:
    if student_id is None:
        return conn.execute(
            "select count(*) from enrollment where valid_to = ?",
            (config.OPEN_END_DATE,),
        ).fetchone()[0]
    return conn.execute(
        "select count(*) from enrollment where student_id = ? and valid_to = ?",
        (student_id, config.OPEN_END_DATE),
    ).fetchone()[0]


# ----------------------------------------------------------------------- разбор

def test_dannye_vynimayutsya_iz_prislannogo_fajla(tmp_path):
    dannye = _dannye([_shkolnik(1, 1)])
    razobrano = dannye_iz_fajla(_fajl(tmp_path, dannye).read_text(encoding="utf-8"))
    assert razobrano == dannye


# ------------------------------------------------------------- идемпотентность

def test_vtoroj_progon_ne_otkryvaet_vtoruyu_stroku(tmp_path):
    """Главное свойство: файл ездит туда-обратно, и его вносят не по одному разу."""
    conn = _baza(tmp_path)
    try:
        dannye = _dannye([_shkolnik(1, 1), _shkolnik(2, 2)])

        pervyj = run(conn, dannye, dni=DNI, segodnya=SEGODNYA, pisat=True)
        # Двое школьников × два слота: раскладка одна на четверг и на субботу.
        assert pervyj.assign == 4
        assert _otkrytyh(conn) == 4

        vtoroj = run(conn, dannye, dni=DNI, segodnya=SEGODNYA, pisat=True)
        assert _otkrytyh(conn) == 4, "второй прогон открыл лишние строки"
        assert vtoroj.assign == 0
        assert vtoroj.move == 0
        assert vtoroj.uzhe_verno == 4
        # И кабинеты второй раз не переписываются: они уже стоят.
        assert vtoroj.kabinety == 0
    finally:
        conn.close()


def test_kabinet_lozhitsya_na_oba_uchebnyh_dnya(tmp_path):
    conn = _baza(tmp_path)
    try:
        run(conn, _dannye([_shkolnik(1, 1)]), dni=DNI, segodnya=SEGODNYA, pisat=True)
        stoit = {
            r["data"]: r["kabinet"]
            for r in conn.execute("select data, kabinet from kabinet_na_den")
        }
        assert stoit == {DNI[1]: "303", DNI[2]: "303"}
    finally:
        conn.close()


# --------------------------------------------------------- сверка справочников

def test_otkaz_pri_rashozhdenii_imeni(tmp_path):
    """Совпал id, разъехалось имя — файл собран не с этой базы."""
    conn = _baza(tmp_path)
    try:
        chuzhoj = _shkolnik(1, 1) | {"familiya": "Другая-Фамилия"}
        bedy = sverit_spravochniki(conn, _dannye([chuzhoj]))
        assert len(bedy) == 1
        assert "Другая-Фамилия" in bedy[0] and "Фамилия-0" in bedy[0]
    finally:
        conn.close()


def test_otkaz_pri_neizvestnom_prepodavatele(tmp_path):
    conn = _baza(tmp_path)
    try:
        bedy = sverit_spravochniki(conn, _dannye([_shkolnik(1, 1)], prepodavateli=[
            {"id": 1, "imya": "Преподаватель-0", "gruppa": "В", "aktiven": True},
            {"id": 99, "imya": "Призрак", "gruppa": "В", "aktiven": True},
        ]))
        assert len(bedy) == 1
        assert "id=99" in bedy[0]
    finally:
        conn.close()


def test_rashozhdenie_spravochnikov_nichego_ne_pishet(tmp_path):
    """Код выхода 2 И пустая база: отказ обязан быть ДО единой правки, а не по ходу."""
    conn = _baza(tmp_path)
    baza = tmp_path / "test.db"
    try:
        chuzhoj = _shkolnik(2, 1) | {"familiya": "Не-Тот"}
        fajl = _fajl(tmp_path, _dannye([_shkolnik(1, 1), chuzhoj]))

        kod = main([str(fajl), "--baza", str(baza), "--pisat"])

        assert kod == 2
        # Ни строки enrollment, ни кабинета — хотя первый школьник сошёлся.
        assert _otkrytyh(conn) == 0
        assert conn.execute("select count(*) from kabinet_na_den").fetchone()[0] == 0
    finally:
        conn.close()


# ------------------------------------------------------------------- вычёркивание

def test_ushedshego_vycherkivaet(tmp_path):
    """`prepodavatel = null` — это «ребёнка в классе больше нет»."""
    conn = _baza(tmp_path)
    try:
        # Сначала поставили обоих, потом второй ушёл.
        run(conn, _dannye([_shkolnik(1, 1), _shkolnik(2, 2)]),
            dni=DNI, segodnya=SEGODNYA, pisat=True)
        assert _otkrytyh(conn, 2) == 2

        itog = run(conn, _dannye([_shkolnik(1, 1), _shkolnik(2, None)]),
                   dni=DNI, segodnya=SEGODNYA, pisat=True)

        assert itog.vycherknuto == 1
        assert conn.execute(
            "select status from students where id = 2"
        ).fetchone()["status"] == "left"
        assert _otkrytyh(conn, 2) == 0, "открытые строки ушедшего не закрыты"
        # Закрыты, а не удалены: за строками стоят его прошлые отметки.
        assert conn.execute(
            "select count(*) from enrollment where student_id = 2"
        ).fetchone()[0] == 2
        # Оставшегося это не тронуло.
        assert _otkrytyh(conn, 1) == 2
    finally:
        conn.close()


# ------------------------------------------------ ловушка: интервал открыт будущим

def test_perevod_ot_stroki_otkrytoj_budushchim_chislom(tmp_path):
    """`move` требует дату СТРОГО больше `valid_from`, а раскладку ставят заранее.

    Интервалы здесь открыты 2026-09-10, а «сегодня» — 2026-09-07. Наивное
    `effective_from = сегодня` отбилось бы `MoveNotForward` и уронило перевод.
    """
    conn = _baza(tmp_path)
    try:
        run(conn, _dannye([_shkolnik(1, 1)]), dni=DNI, segodnya=SEGODNYA, pisat=True)
        assert conn.execute(
            "select valid_from from enrollment where slot = 1"
        ).fetchone()["valid_from"] == DNI[1]  # будущее относительно SEGODNYA

        itog = run(conn, _dannye([_shkolnik(1, 2)]),
                   dni=DNI, segodnya=SEGODNYA, pisat=True)

        assert itog.otkazy == 0, itog.log
        assert itog.move == 2
        assert _otkrytyh(conn, 1) == 2
        for row in conn.execute(
            "select slot, teacher_id, valid_from from enrollment where valid_to = ?",
            (config.OPEN_END_DATE,),
        ):
            assert row["teacher_id"] == 2
            # Сдвиг на день от даты стоящего интервала, а не «сегодня».
            assert row["valid_from"] == vpered_ot(DNI[row["slot"]], SEGODNYA)
    finally:
        conn.close()


# -------------------------------------------------------------------- сухой прогон

def test_suhoj_progon_nichego_ne_pishet(tmp_path):
    conn = _baza(tmp_path)
    try:
        itog = run(conn, _dannye([_shkolnik(1, 1), _shkolnik(2, 2)]),
                   dni=DNI, segodnya=SEGODNYA, pisat=False)
        assert itog.assign == 4
        assert _otkrytyh(conn) == 0
        assert conn.execute("select count(*) from kabinet_na_den").fetchone()[0] == 0
    finally:
        conn.close()
