"""THE DATABASE HAS AN ADDRESS, NOT A NAME -- and the refusal is checked as a PAIR.

Every test here comes in two states, because one state alone proves nothing.  "It refused"
is worthless without "and with the variable set it works" (a tool that always refuses is
green on the first half and useless), and "it works" is worthless without "and without the
variable it refuses" (which is exactly the state the project was in until 2026-09-10, when
one name pointed at two files and pointed successfully).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

import config

KOREN = Path(__file__).resolve().parent.parent.parent


def _bez_peremennoj(env=None):
    """A copy of the environment with the source variable removed."""
    sreda = dict(env or os.environ)
    sreda.pop(config.BAZA_ENV, None)
    return sreda


def test_bez_peremennoj_otkaz_i_dva_zakonnyh_adresa():
    """State one of the pair: nobody named the source, so there is no honest answer."""
    with pytest.raises(SystemExit) as otkaz:
        config.put_bazy()
    tekst = str(otkaz.value)
    assert config.BAZA_ENV in tekst
    # 🔴 ОБА ЗАКОННЫХ ОТВЕТА, А НЕ ОДИН. Отказ, называющий только серверный путь,
    # оставляет всех, кто не на сервере, без хода -- и они возвращаются к тому, чем
    # это чинилось раньше: к локальной копии, названной базой.
    assert config.BAZA_NA_SERVERE in tekst, "первый законный ответ — боевой адрес"
    assert "--snyat-kopiyu" in tekst, "второй законный ответ — штатная дверь за копией"


def test_s_peremennoj_put_beryotsya_iz_sredy(tmp_path, monkeypatch):
    """State two of the pair: named, and then the answer is the file that was named."""
    nazvannaya = tmp_path / "nazvannaya.db"
    monkeypatch.setenv(config.BAZA_ENV, str(nazvannaya))
    assert config.put_bazy() == nazvannaya
    assert config.DB_PATH == nazvannaya


def test_peremennaya_chitaetsya_v_moment_ispolzovania(tmp_path, monkeypatch):
    """🔴 ОТВЕТ БЕРЁТСЯ ПРИ ВЫЗОВЕ, А НЕ ПРИ ИМПОРТЕ.

    A constant read at import time would freeze whatever the environment held when the
    first module happened to import ``config`` -- and a shell that exports the variable
    afterwards, or a test that sets it for one case, would be silently ignored.  Two
    different answers in one process is the whole proof.
    """
    pervaya = tmp_path / "pervaya.db"
    vtoraya = tmp_path / "vtoraya.db"
    monkeypatch.setenv(config.BAZA_ENV, str(pervaya))
    assert config.DB_PATH == pervaya
    monkeypatch.setenv(config.BAZA_ENV, str(vtoraya))
    assert config.DB_PATH == vtoraya


@pytest.mark.parametrize("instrument", [
    "tools/proverka_sostava.py",
    "tools/vidy_zadach.py",
    "veb/sobrat_fajl.py",
])
def test_instrument_pechatayushchij_chisla_otkazyvaet_bez_peremennoj(instrument):
    """🔴 ЖИВОЙ ПРОГОН НАСТОЯЩЕГО ИНСТРУМЕНТА, А НЕ ФИКСТУРЫ.

    ``config.put_bazy`` refusing in isolation says nothing about whether a tool ever
    reaches it: the tools used to carry their own ``data/spetsmat.db`` default, which the
    environment could not override.  So these run as subprocesses, exactly as a person
    runs them, and the criterion is the process exit code.
    """
    itog = subprocess.run([sys.executable, instrument],
                          cwd=str(KOREN), env=_bez_peremennoj(),
                          capture_output=True, text=True, timeout=120)
    assert itog.returncode != 0, (
        "%s отработал БЕЗ названного источника — это фантом, ради которого всё писалось:\n%s"
        % (instrument, itog.stdout + itog.stderr))
    vsyo = itog.stdout + itog.stderr
    assert config.BAZA_ENV in vsyo, "отказ обязан назвать переменную"
    assert config.BAZA_NA_SERVERE in vsyo, "отказ обязан назвать боевой адрес"


def test_ni_odin_chitatel_ne_derzhit_sobstvennogo_umolchania():
    """🔴 ВТОРОЕ УМОЛЧАНИЕ ЕСТЬ ВТОРОЙ ИСТОЧНИК, ГДЕ БЫ ОНО НИ СТОЯЛО.

    Taking the default out of ``config.py`` fixes nothing while six other files each keep
    their own ``data/spetsmat.db`` -- and on 2026-09-10 six of them did: two module-level
    constants (``veb/obshchee/karkas.py``, ``veb/sobrat_fajl.py``), one bare string
    (``tools/proverka_sostava.py``), one gate constant (``tools/gejt_verstki.py``) and two
    argparse defaults.  The environment could not override any of them, so the address was
    still a name six times over.  This test is a grep, and it is a grep on purpose: the
    disease is textual and reappears by copy-paste.
    """
    obrazcy = ('"data/spetsmat.db"', "'data/spetsmat.db'",
               '"data" / "spetsmat.db"', "'data' / 'spetsmat.db'")
    najdeno = []
    for papka in ("tools", "veb", "ops", "core", "infra", "bot"):
        for fajl in sorted((KOREN / papka).rglob("*.py")):
            for nomer, stroka in enumerate(
                    fajl.read_text(encoding="utf-8").splitlines(), start=1):
                golaya = stroka.split("#")[0]
                if any(o in golaya for o in obrazcy):
                    najdeno.append("%s:%d: %s" % (fajl.relative_to(KOREN), nomer, stroka.strip()))
    assert not najdeno, "путь базы вписан в код мимо источника:\n" + "\n".join(najdeno)
