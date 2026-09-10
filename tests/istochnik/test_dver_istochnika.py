"""THE DOOR ANSWERS WHEN IT IS ASKED ABOUT ITSELF: `python3 core/istochnik.py`.

🔴 МОЛЧАЩАЯ ДВЕРЬ НЕОТЛИЧИМА ОТ СЛОМАННОЙ. The first version of that file printed ZERO
lines on a direct run and exited 0; the owner ran it at 14:09 and got nothing back.  That
is the same disease the whole module exists for -- "no findings" reads as "clean" while it
actually means "nobody looked".  So the door is tested as a SUBPROCESS, the way a person
runs it, and every line the criterion names is asserted by name.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

import config
from core import istochnik
from infra.db import apply_migrations, connect

KOREN = Path(__file__).resolve().parent.parent.parent


def _zapusk(*args, baza=None):
    sreda = dict(os.environ)
    if baza is None:
        sreda.pop(config.BAZA_ENV, None)
    else:
        sreda[config.BAZA_ENV] = str(baza)
    return subprocess.run([sys.executable, "core/istochnik.py", *args],
                          cwd=str(KOREN), env=sreda,
                          capture_output=True, text=True, timeout=120)


@pytest.fixture
def zhivaya(tmp_path: Path) -> Path:
    """A migrated database with a real record in it, stamped боевая on this machine."""
    put = tmp_path / "spetsmat.db"
    apply_migrations(put)
    c = connect(put)
    try:
        c.execute("insert into students (id, surname, name) values (1, 'Иванов', 'Иван')")
        c.execute("insert into teachers (id, name) values (1, 'Стрелкова')")
        c.execute("insert into sessions (id, held_on, kind) values (1, '2026-09-01', 'обычное')")
        c.execute("insert into enrollment (student_id, teacher_id, room, slot, valid_from) "
                  "values (1, 1, '203', 1, '2026-09-01')")
        istochnik.pometit(c, "боевая")
    finally:
        c.close()
    return put


def test_dver_ne_molchit_i_nazyvaet_chetyre_velichiny(zhivaya):
    """Путь · род по метке · свежесть · вердикт — все четыре, одним прогоном."""
    itog = _zapusk(baza=zhivaya)
    vyvod = itog.stdout
    assert vyvod.strip(), "дверь промолчала — ровно тот дефект, что чинили 10.09"
    assert str(zhivaya.resolve()) in vyvod, "не назван путь"
    assert "род: боевая" in vyvod, "не назван род по метке"
    assert "последняя запись" in vyvod, "не названа свежесть"
    assert "вердикт:" in vyvod, "не назван вердикт"


def test_kod_nol_na_boevoj(zhivaya):
    """ПАРА, СОСТОЯНИЕ ПЕРВОЕ: боевая на своём хосте и свежая → 0."""
    itog = _zapusk(baza=zhivaya)
    assert itog.returncode == 0, itog.stdout + itog.stderr


def test_kod_nenulevoj_na_kopii(zhivaya, tmp_path):
    """ПАРА, СОСТОЯНИЕ ВТОРОЕ: та же база, снятая штатной дверью → не 0."""
    kopia = istochnik.snyat_kopiyu(zhivaya, tmp_path / "kopia.db")
    itog = _zapusk(baza=kopia)
    assert itog.returncode != 0, itog.stdout + itog.stderr
    assert "род: копия" in itog.stdout


def test_bez_peremennoj_kod_dva_a_ne_odin():
    """🔴 «ИСТОЧНИК НЕ НАЗВАН» И «БАЗА МЁРТВАЯ» — РАЗНЫЕ ОТВЕТЫ, РАЗНЫЕ КОДЫ.

    Слипшись в единицу, они становятся неразличимы для вызывающего конвейера, и он
    молча идёт дальше по той же дороге, по которой и пришёл к фантому.
    """
    itog = _zapusk()
    assert itog.returncode == 2, itog.stdout + itog.stderr
    assert config.BAZA_ENV in (itog.stdout + itog.stderr)


def test_pometit_stavit_rod_i_pechataet_ego(tmp_path):
    """`--pometit` — единственная дверь, через которую база становится боевой."""
    put = tmp_path / "spetsmat.db"
    apply_migrations(put)
    itog = _zapusk("--pometit", "боевая", baza=put)
    assert itog.returncode == 0, itog.stdout + itog.stderr
    assert "род: боевая" in itog.stdout
    c = connect(put)
    try:
        m = istochnik.metka(c)
    finally:
        c.close()
    assert m is not None and m.rod == "боевая" and m.host == istochnik.etot_host()


def test_snyat_kopiyu_pechataet_put_i_kak_na_nego_ukazat(zhivaya, tmp_path):
    """Отказ отправляет за копией — значит дверь за копией обязана существовать
    и печатать путь, который человек скопирует, а не «копия снята»."""
    kuda = tmp_path / "rabochaya.db"
    itog = _zapusk("--snyat-kopiyu", str(kuda), baza=zhivaya)
    assert itog.returncode == 0, itog.stdout + itog.stderr
    assert str(kuda) in itog.stdout
    assert "%s=%s" % (config.BAZA_ENV, kuda) in itog.stdout
    assert kuda.exists()


def test_nechitaemaya_baza_eto_kod_2_a_ne_lozhnoe_pusto(tmp_path):
    """🔴 «НЕ ЧИТАЕТСЯ» И «ПУСТА» — РАЗНЫЕ ОТВЕТЫ, И ДВЕРЬ ИХ ПУТАЛА.

    `sqlite3.connect` соединяется лениво, а все чтения обёрнуты в `except
    sqlite3.Error`, поэтому файл, который не читается ВОВСЕ, выглядел как «БАЗА
    ПУСТА · НЕ ПОМЕЧЕНА, накати миграции» — красное с неверным диагнозом,
    отправляющее читателя не туда. Найдено проверкой на обход на `cp` WAL-базы без
    спутников; здесь тот же класс воспроизводится файлом, который базой не является.
    """
    ne_baza = tmp_path / "eto-ne-baza.db"
    ne_baza.write_bytes("не sqlite, а просто байты".encode("utf-8") * 100)
    itog = _zapusk(baza=ne_baza)
    assert itog.returncode == 2, itog.stdout + itog.stderr
    vsyo = itog.stdout + itog.stderr
    assert "ПРОЧИТАТЬ" in vsyo, "дверь обязана сказать «не читается», а не «пуста»"
    assert "БАЗА ПУСТА" not in vsyo, "ложный диагноз «пуста» на нечитаемом файле"
