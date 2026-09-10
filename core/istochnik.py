"""ОДИН ИСТОЧНИК ПРАВДЫ: кто спросил базу — тот и называет, КАКУЮ базу он спросил.

🔴 ЗАЧЕМ ЭТОТ МОДУЛЬ ЕСТЬ. Требование владельца 10.09, дословно: «источник истины
один — задачи в базе, они там внесены поимённо, и оттуда же подгружаются в кондуит.
Надо удалить другой неактуальный источник, в который ты смотришь, раз и навсегда».

ЦЕНА, ОПЛАЧЕННАЯ ДО ЭТОГО МОДУЛЯ И ЗАМЕРЕННАЯ:
  * `data/spetsmat.db` лежала в git И одновременно жила. В свежем worktree выезжала
    версия БЕЗ миграции 009 — сайт там не поднимался вовсе, позиция потеряла целый
    прогон и дважды подменяла базу руками;
  * оркестратор волны УТРО смотрел на ДАТУ ФАЙЛА (12:21 сегодня) и считал базу
    свежей, когда самая поздняя запись в ней была от 3 сентября;
  * ни один из инструментов, читающих базу, не печатал, КАКУЮ базу он открыл, —
    поэтому число из мёртвой копии выглядело точно так же, как число из живой.

ДАТА ФАЙЛА НИЧЕГО НЕ ГОВОРИТ О СОДЕРЖИМОМ. Копирование, `git checkout`, rsync,
открытие в WAL-режиме — всё это трогает mtime, не добавив ни одной записи. Поэтому
здесь считается дата САМОЙ ПОЗДНЕЙ ЗАПИСИ ВНУТРИ базы, а не дата файла.
"""

from __future__ import annotations

import socket
import sqlite3
import sys
from datetime import date as _date, datetime as _datetime, timezone as _timezone
from pathlib import Path
from typing import NamedTuple, Optional, Tuple

#: Таблицы и колонки, по которым судится «когда в эту базу писали в последний раз».
#: Список НЕ полон намеренно: сюда входит только то, что меняется на занятии.
#: 🔴 `sessions.held_on` СЮДА НЕ ВХОДИТ, И ЭТО НЕ ОПЕЧАТКА. Занятие заводится
#: ЗАРАНЕЕ: это дата ПЛАНА, а не след того, что в базу писали. Первая версия этого
#: модуля её включала — и критерий владельца («живая и мёртвая печатают РАЗНЫЕ даты,
#: вторая красная») провалился на первом же прогоне: мёртвая копия показала ту же
#: дату 2026-09-10, потому что помнила будущее занятие, не имея ни одной записи о
#: нём. Ровно тот класс, ради которого модуль и написан: величина, которая ВЫГЛЯДИТ
#: как свежесть, но ею не является. Поймано критерием, а не глазами.
ГДЕ_ДАТЫ = (
    ("marks", "valid_at"),
    ("marks", "recorded_at"),
    ("attendance_pometki", "kogda"),
    ("enrollment", "valid_from"),
)


# ───────────────────────────────────────────────────────────────────────────────
# МЕТКА ВНУТРИ БАЗЫ: файл сам говорит, что он такое
#
# 🔴 ОДНОЙ СВЕЖЕСТИ ДЛЯ ЭТОГО МАЛО, И ЭТО НЕ ОСТОРОЖНОСТЬ, А ЗАМЕР. В понедельник
# утром ЖИВАЯ боевая база тоже «отстаёт» от последнего занятия — записей после
# пятницы в ней нет, — и признак шумит ровно в тот момент, когда на него смотрят.
# Поэтому род базы записан ВНУТРИ неё (миграция 011), а не выводится из даты.
#
# 🔴 РОД БЕЗ ХОСТА НИЧЕГО НЕ СТОИТ. `cp boevaya.db kopiya.db` уносит слово «боевая»
# дословно, и копия проходит любую проверку, которую слово может выдержать в
# одиночку. Пара «род + хост, на котором род поставлен» такого не позволяет:
# боевая, открытая не на своей машине, — это унесённая копия по построению.

#: Три рода. Значения — данные, ограничены CHECK'ом в миграции 011.
RODA = ("боевая", "копия", "тест")


class Metka(NamedTuple):
    """Что база говорит о себе сама."""

    rod: str
    host: str
    kogda: str
    otkuda: str
    #: Абсолютный путь ФАЙЛА, для которого метка поставлена (миграция 012). Пустая
    #: строка — метка старше 012 и боевой себя назвать не может: см. `proverit_metku`.
    put: str = ""


def etot_host() -> str:
    """Имя машины, на которой идёт этот процесс."""
    return socket.gethostname()


def metka(conn: sqlite3.Connection) -> Optional[Metka]:
    """Метка базы или `None`, если база старше миграции 011.

    `None` — НЕ «всё в порядке». Это база, которая о себе не сказала ничего, и
    судится она строже помеченной: см. `proverit_metku`.
    """
    try:
        r = conn.execute(
            "select rod, host, kogda, otkuda, put from istochnik_metka where id = 1").fetchone()
    except sqlite3.Error:
        # Колонки `put` нет — база между миграциями 011 и 012. Читаем без неё, а
        # решение «такая метка боевой не считается» принимает `proverit_metku`, а не
        # это место: здесь мы только читаем, что написано.
        try:
            r = conn.execute(
                "select rod, host, kogda, otkuda from istochnik_metka where id = 1").fetchone()
        except sqlite3.Error:
            return None
        if not r:
            return None
        return Metka(str(r[0]), str(r[1] or ""), str(r[2] or ""), str(r[3] or ""), "")
    if not r:
        return None
    return Metka(str(r[0]), str(r[1] or ""), str(r[2] or ""), str(r[3] or ""), str(r[4] or ""))


def pometit(conn: sqlite3.Connection, rod: str, otkuda: str = "") -> Metka:
    """Поставить метку. Боевая ставится ОДИН раз, на сервере, руками.

    Хост и время берутся у машины, а не у звавшего: метка, чьи поля можно передать
    аргументом, — это не свидетельство, а пересказ.
    """
    if rod not in RODA:
        raise ValueError("род %r не из %s" % (rod, ", ".join(RODA)))
    kogda = _datetime.now(tz=_timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # 🔴 ПУТЬ СПРАШИВАЕТСЯ У СОЕДИНЕНИЯ, А НЕ ПРИНИМАЕТСЯ АРГУМЕНТОМ. Тот же довод,
    # что у `put_bazy`: аргумент говорит, что СОБИРАЛИСЬ пометить, соединение — что
    # пометили на самом деле. Метка, чей путь можно передать со стороны, — пересказ.
    novaya = Metka(rod, etot_host(), kogda, otkuda, put_bazy(conn))
    try:
        conn.execute("""
            insert into istochnik_metka (id, rod, host, kogda, otkuda, put)
              values (1, ?, ?, ?, ?, ?)
              on conflict(id) do update set rod = excluded.rod, host = excluded.host,
                                            kogda = excluded.kogda, otkuda = excluded.otkuda,
                                            put = excluded.put
        """, (novaya.rod, novaya.host, novaya.kogda, novaya.otkuda, novaya.put))
    except sqlite3.OperationalError:
        # База между 011 и 012. Пометить можно, но БЕЗ пути — и такая метка боевой
        # не считается: накати миграции и пометь заново.
        conn.execute("""
            insert into istochnik_metka (id, rod, host, kogda, otkuda) values (1, ?, ?, ?, ?)
              on conflict(id) do update set rod = excluded.rod, host = excluded.host,
                                            kogda = excluded.kogda, otkuda = excluded.otkuda
        """, (novaya.rod, novaya.host, novaya.kogda, novaya.otkuda))
        novaya = novaya._replace(put="")
    conn.commit()
    return novaya


def opisat_metku(m: Optional[Metka]) -> str:
    """Одна строка о роде базы — то, что человек читает вместо догадки."""
    if m is None:
        return "род: НЕ ПОМЕЧЕНА (база старше миграции 011)"
    hvost = ""
    if m.put:
        hvost += " · для файла: %s" % m.put
    if m.otkuda:
        hvost += " · откуда: %s" % m.otkuda
    return "род: %s · помечена на %s · когда: %s%s" % (
        m.rod, m.host or "—", m.kogda or "—", hvost)


def proverit_metku(conn: sqlite3.Connection, potok=None) -> int:
    """🔴 МОЖНО ЛИ БРАТЬ ИЗ ЭТОГО ФАЙЛА БОЕВЫЕ ЧИСЛА. 0 — да, 1 — нет.

    Ровно четыре ответа, и три из них отрицательные:
      * `боевая` на том хосте, где она помечена — да;
      * `боевая` на ЧУЖОМ хосте — нет: это унесённая копия, слово приехало вместе
        с файлом;
      * `копия` / `тест` — нет, и это же нормальное состояние такого файла;
      * метки нет вовсе — нет: база о себе не сказала, а молчание не есть согласие.
    """
    potok = potok or sys.stderr
    m = metka(conn)
    if m is None:
        print("🔴 БАЗА НЕ ПОМЕЧЕНА: род неизвестен, боевых чисел она не даёт. "
              "Накати миграции (`infra/db.py::apply_migrations`) и пометь явно.",
              file=potok)
        return 1
    if m.rod != "боевая":
        print("🔴 ЭТО НЕ БОЕВАЯ БАЗА: %s. Числа из неё описывают её саму, "
              "а не школу." % opisat_metku(m), file=potok)
        return 1
    zdes = etot_host()
    if m.host and m.host != zdes:
        print("🔴 БОЕВАЯ МЕТКА С ЧУЖОЙ МАШИНЫ: помечена на %s, открыта на %s. "
              "Файл унесли с сервера — это копия, как бы она себя ни называла."
              % (m.host, zdes), file=potok)
        return 1
    # 🔴 ХОСТА МАЛО, И ЭТО ЗАМЕР, А НЕ ОСТОРОЖНОСТЬ. Хост ловит копию, УНЕСЁННУЮ на
    # другую машину, и не ловит `cp` НА ТОЙ ЖЕ машине — а на сервере `cp` делается
    # именно там, где боевая и живёт. Проверкой на обход снято дословно: `cp
    # boevaya.db chestnaya-cp.db` на той же машине давал `вердикт: БОЕВАЯ, СВЕЖАЯ,
    # СВОЯ ✅`. Копия лежит по ДРУГОМУ пути по определению — иначе она не копия, а тот
    # же файл; поэтому метка помнит файл, для которого поставлена (миграция 012).
    if not m.put:
        print("🔴 МЕТКА НЕ ЗНАЕТ СВОЕГО ФАЙЛА: она старше миграции 012 и потому не "
              "отличит боевую от её `cp`-копии. Накати миграции и пометь заново: "
              "`python3 core/istochnik.py --pometit боевая`.", file=potok)
        return 1
    otkryt = put_bazy(conn)
    if m.put != otkryt:
        print("🔴 БОЕВАЯ МЕТКА ОТ ДРУГОГО ФАЙЛА: поставлена для %s, а открыт %s. "
              "Это копия — слово «боевая» приехало вместе с байтами."
              % (m.put, otkryt), file=potok)
        return 1
    return 0


def poslednyaya_zapis(conn: sqlite3.Connection) -> Optional[str]:
    """Дата самой поздней записи ВНУТРИ базы, `YYYY-MM-DD`, или `None` для пустой."""
    naidено = []
    for tablica, kolonka in ГДЕ_ДАТЫ:
        try:
            r = conn.execute(f"select max({kolonka}) from {tablica}").fetchone()
        except sqlite3.Error:
            continue          # таблицы нет в этой схеме — не беда и не ошибка
        if r and r[0]:
            naidено.append(str(r[0])[:10])
    return max(naidено) if naidено else None


def poslednee_zanyatie(conn: sqlite3.Connection, segodnya: Optional[str] = None) -> Optional[str]:
    """Дата последнего ПРОШЕДШЕГО занятия — то, с чем сверяется свежесть.

    🔴 `max(held_on)` БЕЗ ОТСЕЧКИ ПО СЕГОДНЯ — ОШИБКА, И ОНА БЫЛА ЗДЕСЬ. Расписание
    заводится вперёд: на боевой базе 10.09 лежали занятия `2026-09-07`, `2026-09-10`
    и `2026-10-01`. Сравнение с максимумом объявляло МЁРТВОЙ живую боевую базу —
    «последняя запись 2026-09-10, а последнее занятие 2026-10-01», — то есть требовало
    записей о занятии, которое ещё не состоялось. Поймано прогоном на боевой, не
    рассуждением: это вторая ошибка того же рода в этом файле за десять минут, и обе
    поймал критерий, а не глаз.
    """
    segodnya = segodnya or _date.today().isoformat()
    try:
        r = conn.execute("select max(held_on) from sessions where held_on <= ?",
                         (segodnya,)).fetchone()
    except sqlite3.Error:
        return None
    return str(r[0])[:10] if r and r[0] else None


def put_bazy(conn: sqlite3.Connection) -> str:
    """АБСОЛЮТНЫЙ путь открытой базы, спрошенный у самого соединения.

    Спрашивается у `PRAGMA database_list`, а не берётся из настроек: настройка
    говорит, что СОБИРАЛИСЬ открыть, соединение — что открыли на самом деле.
    """
    try:
        for _, imya, fajl in conn.execute("PRAGMA database_list"):
            if imya == "main":
                return str(Path(fajl).resolve()) if fajl else "<в памяти>"
    except sqlite3.Error:
        pass
    return "<неизвестно>"


def nazvat(conn: sqlite3.Connection, potok=None) -> Tuple[str, Optional[str]]:
    """ПЕРВАЯ СТРОКА любого инструмента, печатающего числа из базы.

    Печатает абсолютный путь и дату последней записи. Возвращает обе величины,
    чтобы звавший мог их же и проверить.
    """
    potok = potok or sys.stdout
    put = put_bazy(conn)
    posl = poslednyaya_zapis(conn)
    print(f"источник: {put} · последняя запись: {posl or '—'}", file=potok)
    # 🔴 РОД ПЕЧАТАЕТСЯ ВСЕГДА, А НЕ ТОЛЬКО КОГДА ОН ПЛОХОЙ. Строка, появляющаяся
    # лишь при беде, приучает к своему отсутствию: читатель перестаёт её искать и
    # не замечает, что её нет. Здесь она стоит рядом с путём каждый раз.
    print(opisat_metku(metka(conn)), file=potok)
    return put, posl


def proverit_svezhest(conn: sqlite3.Connection, potok=None) -> int:
    """🔴 КРАСНЕЕТ, если база старше последнего занятия, которое сама же помнит.

    Без этой проверки «печатать путь и дату» — надежда: напечатать можно и не
    посмотреть. Возврат — код: 0 свежая, 1 мёртвая.

    Сравнение идёт с последним занятием ИЗ ЭТОЙ ЖЕ базы, а не с системным
    «сегодня»: копия недельной давности помнит и своё последнее занятие тоже, и
    именно расхождение «занятие было, записей после него нет» её выдаёт.
    """
    potok = potok or sys.stderr
    posl = poslednyaya_zapis(conn)
    zan = poslednee_zanyatie(conn)
    if posl is None:
        print("🔴 БАЗА ПУСТА: ни одной записи. Числа из неё ничего не значат.", file=potok)
        return 1
    if zan and posl < zan:
        print(f"🔴 БАЗА МЁРТВАЯ: последняя запись {posl}, а последнее занятие {zan}. "
              f"Это КОПИЯ или отставшая версия — числа из неё описывают прошлое.",
              file=potok)
        return 1
    return 0


def nazvat_i_proverit(conn: sqlite3.Connection, potok=None, boevye: bool = False) -> int:
    """Одной строкой то, что обязан сделать КАЖДЫЙ инструмент, печатающий числа.

    🔴 ЗАЧЕМ ОТДЕЛЬНАЯ ФУНКЦИЯ, А НЕ ДВА ВЫЗОВА НА КАЖДОМ ВЫЗЫВАЮЩЕМ. Их
    пятнадцать. Два вызова означали бы пятнадцать мест, где можно забыть второй, —
    и первый же забывший печатал бы источник, не проверив его свежесть, то есть
    выглядел бы честным, не будучи им. Здесь пара неразделима по построению.

    Печатает в `stdout` (это часть вывода инструмента, а не диагностика), возвращает
    код свежести: 0 — свежая, 1 — мёртвая. Инструмент волен решить, падать ли ему на
    единице; молча проигнорировать её он тоже может, но уже НАПЕЧАТАВ красное.
    """
    potok = potok or sys.stdout
    nazvat(conn, potok)
    kod = proverit_svezhest(conn, potok)
    if boevye:
        # 🔴 ДВА РАЗНЫХ ВОПРОСА, И ВТОРОЙ ЗАДАЁТСЯ НЕ ВСЕГДА. «Свежая ли база» спрашивают
        # все; «боевая ли она» — только тот, кто собирается выдать числа за числа ШКОЛЫ
        # или в неё написать. Разбор бумаги на тестовой копии — законная работа, и
        # требовать от неё боевой метки значило бы запретить пробу.
        kod = max(kod, proverit_metku(conn, potok))
    return kod


class SvidetelRaboty:
    """🔴 СВИДЕТЕЛЬ РАБОТЫ С ДАННЫМИ — ВМЕСТО КОММИТА, КОТОРОГО БОЛЬШЕ НЕ БУДЕТ.

    Живая база ушла из git (Д1), и это создало дыру ТЕМ ЖЕ ходом, которым закрыло
    другую: гейт «работа доехала в git» стоит ПЕРВЫМ во всей приёмке и работу с
    ДАННЫМИ больше не покрывает вовсе. Отсутствие коммита стало неотличимо от
    отсутствия работы — и это не рассуждение: 10.09 аналитик объявил внесённые с
    бумаги отметки невнесёнными, потому что искал копию базы в локальной папке, а
    она лежала на сервере. Тридцать шесть отметок существовали, а свидетеля не было.

    Поэтому свидетель делается ФОРМОЙ, а не разовой любезностью отчёта. Три
    величины, и все три снимаются КОМАНДОЙ, а не переписываются из памяти:
      * дата последней записи ДО работы,
      * дата последней записи ПОСЛЕ,
      * число затронутых строк (`total_changes` соединения — считает сама sqlite).

    Пример:
        with SvidetelRaboty(conn, "внесение кондуитов с бумаги 07.09") as svid:
            ...                       # работа
        print(svid.otchyot())
    """

    def __init__(self, conn: sqlite3.Connection, chto: str) -> None:
        self._conn = conn
        self._chto = chto
        self._put = put_bazy(conn)
        self._do = None
        self._posle = None
        self._strok_do = 0
        self._strok_posle = 0

    def __enter__(self) -> "SvidetelRaboty":
        self._do = poslednyaya_zapis(self._conn)
        self._strok_do = self._conn.total_changes
        return self

    def __exit__(self, tip, znachenie, sled) -> bool:
        self._posle = poslednyaya_zapis(self._conn)
        self._strok_posle = self._conn.total_changes
        return False          # исключения не глотаем: упавшая работа обязана упасть

    @property
    def zatronuto(self) -> int:
        return self._strok_posle - self._strok_do

    def otchyot(self) -> str:
        """Три строки, которые вставляются в отчёт как есть."""
        sdvinulos = "ДА" if self._do != self._posle else "нет"
        return (
            "— СВИДЕТЕЛЬ РАБОТЫ С ДАННЫМИ: %s —\n"
            "   база: %s\n"
            "   последняя запись ДО: %s · ПОСЛЕ: %s · сдвинулась: %s\n"
            "   затронуто строк: %d"
            % (self._chto, self._put, self._do or "—", self._posle or "—",
               sdvinulos, self.zatronuto)
        )


def snyat_kopiyu(otkuda, kuda) -> Path:
    """ШТАТНАЯ ДВЕРЬ ЗА КОПИЕЙ: снять и ТУТ ЖЕ пометить `копия`.

    🔴 СНЯТИЕ И ПОМЕТКА — ОДИН ХОД, А НЕ ДВА. Копия, помеченная вторым ходом,
    существует между ходами как файл со словом «боевая» внутри: достаточно одного
    обрыва, чтобы такая копия осталась на диске навсегда. Здесь метка ставится до
    того, как путь возвращён звавшему.

    `VACUUM INTO`, а не `cp`: в режиме WAL часть закоммиченного лежит в `-wal`
    рядом, и `cp` даёт рваный файл плюс два осиротевших спутника — он открывается,
    выглядит целым и восстанавливает «почти» (полный разбор — `ops/rezervnaya_kopia.py`).
    """
    otkuda = Path(otkuda).expanduser().resolve()
    kuda = Path(kuda).expanduser()
    if not otkuda.exists():
        raise FileNotFoundError("нечего копировать: %s нет на диске" % otkuda)
    kuda.parent.mkdir(parents=True, exist_ok=True)
    if kuda.exists():
        kuda.unlink()          # VACUUM INTO отказывается писать в существующий файл
    istochnik_conn = sqlite3.connect(str(otkuda))
    try:
        istochnik_conn.execute("vacuum into '%s'" % str(kuda).replace("'", "''"))
    finally:
        istochnik_conn.close()
    kogda = _datetime.now(tz=_timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    kopia_conn = sqlite3.connect(str(kuda))
    try:
        pometit(kopia_conn, "копия", otkuda="%s на %s, снята %s" % (otkuda, etot_host(), kogda))
    finally:
        kopia_conn.close()
    return kuda


# ───────────────────────────────────────────────────────────────────────────────
# ДВЕРЬ: `python3 core/istochnik.py [--pometit РОД] [--snyat-kopiyu ПУТЬ]`
#
# 🔴 МОЛЧАЩАЯ ДВЕРЬ НЕОТЛИЧИМА ОТ СЛОМАННОЙ. Первая версия этого файла при прямом
# запуске печатала НОЛЬ строк и выходила с кодом 0 — владелец запустил её в 14:09 и
# не получил ничего. Это тот же класс, ради которого весь модуль и написан: «ноль
# находок» читается как «чисто», а на деле означает «никто не смотрел». Инструмент,
# который умеет назвать источник, ОБЯЗАН называть его и когда спрашивают его самого.
#
# Код возврата: 0 — база боевая, своя и свежая; 1 — не боевая, чужая или мёртвая;
#               2 — открыть не удалось или источник не назван вовсе.

def _dver(argv=None) -> int:
    import argparse
    import os

    razbor = argparse.ArgumentParser(
        description="Назвать источник: путь базы, род по метке, свежесть, вердикт.")
    razbor.add_argument("baza", nargs="?", default=None,
                        help="путь к базе; без него — та, что назвала переменная среды")
    razbor.add_argument("--pometit", choices=RODA, default=None,
                        help="поставить род базе и выйти (боевая ставится ОДИН раз, на сервере)")
    razbor.add_argument("--snyat-kopiyu", default=None, metavar="ПУТЬ",
                        help="снять рабочую копию по этому пути и пометить её `копия`")
    args = razbor.parse_args(argv)

    put = args.baza
    if put is None:
        # 🔴 КОРЕНЬ РЕПОЗИТОРИЯ В `sys.path` — ИМЕННО ПРИ ПРЯМОМ ЗАПУСКЕ. Запущенный
        # как `python3 core/istochnik.py`, файл видит своим корнем `core/`, и
        # `import config` падает: дверь отвечала «не удалось узнать путь базы» там,
        # где база на месте. Импортированный модуль от этого не страдает — путь ему
        # выставляет тот, кто импортирует, — и потому дефект живёт только у двери.
        koren = str(Path(__file__).resolve().parent.parent)
        if koren not in sys.path:
            sys.path.insert(0, koren)
        try:
            import config
            put = str(config.DB_PATH)
        except SystemExit as otkaz:
            # 🔴 ОТКАЗ ИСТОЧНИКА ПЕЧАТАЕТСЯ, А НЕ ПРОБРАСЫВАЕТСЯ. Проброшенный, он
            # уходит с кодом 1 — тем же, каким эта дверь отвечает «база мёртвая», —
            # и два разных ответа становятся неразличимы. «Не назван» это 2.
            print(str(otkaz), file=sys.stderr)
            return 2
        except Exception as exc:                       # noqa: BLE001
            print("🔴 не удалось узнать путь базы из config: %s" % exc, file=sys.stderr)
            return 2
    if args.snyat_kopiyu:
        if not os.path.exists(put):
            print("🔴 базы нет на диске: %s" % put, file=sys.stderr)
            return 2
        kuda = snyat_kopiyu(put, args.snyat_kopiyu)
        print("снята копия: %s" % kuda)
        print("указать её явно:  SPETSMAT_BAZA=%s" % kuda)
        return 0
    if not os.path.exists(put):
        print("🔴 базы нет на диске: %s" % put, file=sys.stderr)
        return 2
    if args.pometit:
        conn = sqlite3.connect(put)
        try:
            m = pometit(conn, args.pometit)
        except sqlite3.Error as exc:
            print("🔴 не удалось пометить %s: %s" % (put, exc), file=sys.stderr)
            return 2
        finally:
            conn.close()
        print("источник: %s" % Path(put).resolve())
        print(opisat_metku(m))
        return 0
    try:
        conn = sqlite3.connect("file:%s?mode=ro" % put, uri=True)
        # 🔴 `connect` НИЧЕГО НЕ ОТКРЫВАЕТ — ЭТО ПРОБА, БЕЗ КОТОРОЙ ДВЕРЬ ВРЁТ ПРИЧИНОЙ.
        # sqlite3 соединяется лениво, первая ошибка приходит на первом запросе, а все
        # чтения здесь обёрнуты в `except sqlite3.Error` и молча дают «пусто». Поэтому
        # файл, который НЕ ЧИТАЕТСЯ ВОВСЕ, выглядел как «БАЗА ПУСТА · НЕ ПОМЕЧЕНА,
        # накати миграции» — красное с неверным диагнозом, отправляющее читателя не туда.
        # Живой случай, снятый проверкой на обход: `cp` WAL-базы без спутников `-wal`/
        # `-shm`, открытый `mode=ro`, падает на `select 1` с «unable to open database
        # file», а дверь советовала накатывать миграции.
        conn.execute("select 1").fetchone()
    except sqlite3.Error as exc:
        print("🔴 базу %s не удалось ПРОЧИТАТЬ: %s\n"
              "   Частая причина: это WAL-база, скопированная `cp` без спутников\n"
              "   `-wal`/`-shm`. Копии снимаются штатной дверью, а не `cp`:\n"
              "   python3 core/istochnik.py --snyat-kopiyu <путь>"
              % (put, exc), file=sys.stderr)
        return 2

    nazvat(conn)
    zan = poslednee_zanyatie(conn)
    print("последнее прошедшее занятие: %s" % (zan or "—"))
    svezhest = proverit_svezhest(conn, sys.stdout)
    rod = proverit_metku(conn, sys.stdout)
    rc = max(svezhest, rod)
    print("вердикт: %s" % ("БОЕВАЯ, СВЕЖАЯ, СВОЯ ✅" if rc == 0
                           else "БОЕВЫХ ЧИСЕЛ НЕ ДАЁТ 🔴"))
    return rc


if __name__ == "__main__":
    sys.exit(_dver())
