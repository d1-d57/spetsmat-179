"""THE DATABASE SAYS WHAT IT IS, FROM INSIDE ITSELF -- and a copy cannot say "боевая".

🔴 WHY FRESHNESS ALONE WAS NOT ENOUGH, tested here rather than argued: on a Monday morning
the LIVE database is also behind its own last session, so the freshness signal goes red on
the healthy file exactly when somebody is leaning on it.  ``test_svezhest_odna_ne_otlichaet``
below builds that Monday and shows the two files scoring the same on freshness and
differently on the stamp.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from core import istochnik
from infra.db import apply_migrations, connect


def _zasejat(c) -> None:
    """Одна запись, дата которой РЕАЛЬНО считается свежестью.

    Свежесть меряется по `ГДЕ_ДАТЫ` в `core/istochnik.py`, и `sessions.held_on` в этот
    список НЕ входит намеренно: занятие заводят заранее, это дата ПЛАНА, а не след
    записи. Поэтому здесь пишется `enrollment.valid_from` — одна из тех колонок,
    которые след записи действительно оставляют.
    """
    c.execute("insert into students (id, surname, name) values (1, 'Иванов', 'Иван')")
    c.execute("insert into teachers (id, name) values (1, 'Стрелкова')")
    c.execute("insert into sessions (id, held_on, kind) values (1, '2026-09-01', 'обычное')")
    c.execute("insert into enrollment (student_id, teacher_id, room, slot, valid_from) "
              "values (1, 1, '203', 1, '2026-09-01')")


@pytest.fixture
def baza(tmp_path: Path) -> Path:
    put = tmp_path / "spetsmat.db"
    apply_migrations(put)
    return put


def _conn(put: Path) -> sqlite3.Connection:
    c = connect(put)
    c.row_factory = sqlite3.Row
    return c


def test_migracia_seet_test_a_ne_boevuyu(baza):
    """🔴 НАПРАВЛЕНИЕ УМОЛЧАНИЯ — ЭТО И ЕСТЬ ВСЯ БЕЗОПАСНОСТЬ.

    A migration cannot know which machine it is being applied on and therefore must not
    guess towards trust.  Every database that gets migration 011 -- a temp file in a test,
    a restored snapshot, the live file on the server -- starts as `тест`.
    """
    with _conn(baza) as c:
        m = istochnik.metka(c)
    assert m is not None, "миграция 011 не накатилась"
    assert m.rod == "тест"


def test_kopia_na_zapros_boevyh_chisel_otkazyvaet(baza):
    """ПАРА, СОСТОЯНИЕ ПЕРВОЕ: помечена `копия` → боевых чисел не даёт."""
    with _conn(baza) as c:
        istochnik.pometit(c, "копия", otkuda="снята с боевой 2026-09-10")
        assert istochnik.proverit_metku(c) == 1
        assert istochnik.nazvat_i_proverit(c, boevye=True) != 0


def test_boevaya_na_svoyom_hoste_rabotaet(baza):
    """ПАРА, СОСТОЯНИЕ ВТОРОЕ: помечена `боевая` здесь же → работает."""
    with _conn(baza) as c:
        m = istochnik.pometit(c, "боевая")
        assert m.host == istochnik.etot_host()
        assert istochnik.proverit_metku(c) == 0


def test_boevaya_s_chuzhoj_mashiny_eto_unesyonnaya_kopia(baza):
    """🔴 РОД БЕЗ ХОСТА НИЧЕГО НЕ СТОИТ, И ВОТ ПОЧЕМУ.

    ``cp boevaya.db kopiya.db`` carries the word "боевая" verbatim.  Here the stamp is
    rewritten to name another machine -- which is precisely what such a copy looks like
    from inside -- and the check must still refuse.
    """
    with _conn(baza) as c:
        istochnik.pometit(c, "боевая")
        c.execute("update istochnik_metka set host = 'server-kotorogo-zdes-net' where id = 1")
        c.commit()
        assert istochnik.proverit_metku(c) == 1


def test_baza_bez_metki_boevyh_chisel_ne_dayot(tmp_path):
    """Молчание не есть согласие: база старше миграции 011 тоже отказывает."""
    put = tmp_path / "staraya.db"
    c = sqlite3.connect(put)
    c.execute("create table pusto (id integer primary key)")
    c.commit()
    assert istochnik.metka(c) is None
    assert istochnik.proverit_metku(c) == 1
    c.close()


def test_svezhest_odna_ne_otlichaet_zhivuyu_ot_kopii(baza, tmp_path):
    """🔴 ПОНЕДЕЛЬНИК УТРОМ: ОДНОЙ СВЕЖЕСТИ МАЛО, И ЭТО ЗДЕСЬ ПОКАЗАНО ЧИСЛОМ.

    Both files carry the same records and the same past session, so ``proverit_svezhest``
    gives them the SAME answer -- the state in which the project spent 2026-09-10 unable to
    tell which file it was reading.  The stamp separates them where freshness cannot.
    """
    with _conn(baza) as c:
        _zasejat(c)
        c.commit()
        istochnik.pometit(c, "боевая")

    kopia = istochnik.snyat_kopiyu(baza, tmp_path / "kopia.db")

    with _conn(baza) as zhivaya_c, _conn(kopia) as kopia_c:
        # Свежесть у обеих одинаковая — записи те же, занятие то же.
        assert istochnik.proverit_svezhest(zhivaya_c) == istochnik.proverit_svezhest(kopia_c)
        # А род — разный, и именно он отвечает на вопрос «это та база?».
        assert istochnik.proverit_metku(zhivaya_c) == 0
        assert istochnik.proverit_metku(kopia_c) == 1


def test_shtatnaya_dver_pomechaet_kopiyu_tem_zhe_hodom(baza, tmp_path):
    """Снятая дверью копия помечена `копия` ДО того, как путь возвращён звавшему."""
    with _conn(baza) as c:
        istochnik.pometit(c, "боевая")
    kuda = istochnik.snyat_kopiyu(baza, tmp_path / "rabochaya.db")
    with _conn(kuda) as c:
        m = istochnik.metka(c)
    assert m is not None and m.rod == "копия"
    assert str(baza) in m.otkuda, "копия обязана помнить, откуда она снята"


def test_cp_kopia_na_toj_zhe_mashine_boevoj_sebya_ne_nazovyot(baza, tmp_path):
    """🔴 ДЫРА, НАЙДЕННАЯ ПРОВЕРКОЙ НА ОБХОД, И ЕЁ ЗАКРЫТИЕ.

    Хост ловит копию, УНЕСЁННУЮ на другую машину, и не ловит `cp` НА ТОЙ ЖЕ машине —
    а на сервере `cp` делается именно там, где боевая и живёт. Снято дословно до
    миграции 012: `cp boevaya.db chestnaya-cp.db` давал `вердикт: БОЕВАЯ, СВЕЖАЯ,
    СВОЯ ✅`. Копия лежит по ДРУГОМУ пути по определению — иначе она не копия, а тот
    же файл, — и метка теперь помнит файл, для которого поставлена.
    """
    import shutil

    with _conn(baza) as c:
        _zasejat(c)
        c.commit()
        istochnik.pometit(c, "боевая")
        c.execute("pragma wal_checkpoint(TRUNCATE)")

    kopia = tmp_path / "cp-kopia.db"
    for hvost in ("", "-wal", "-shm"):          # копируем ВМЕСТЕ со спутниками,
        src = baza.with_name(baza.name + hvost)  # иначе копия просто не читается
        if src.exists():
            shutil.copy2(src, str(kopia) + hvost)

    with _conn(baza) as zhivaya_c, _conn(kopia) as kopia_c:
        assert istochnik.proverit_metku(zhivaya_c) == 0, "оригинал обязан остаться боевым"
        assert istochnik.proverit_metku(kopia_c) == 1, (
            "`cp` на той же машине выдал себя за боевую — ровно та дыра, что закрыта 012")


def test_metka_bez_puti_boevoj_ne_schitaetsya(baza):
    """Метка старше миграции 012 не отличит боевую от её копии — значит не боевая.

    Направление умолчания то же, что у засева `тест`: неизвестность не даёт доверия.
    """
    with _conn(baza) as c:
        istochnik.pometit(c, "боевая")
        c.execute("update istochnik_metka set put = '' where id = 1")
        c.commit()
        assert istochnik.proverit_metku(c) == 1
