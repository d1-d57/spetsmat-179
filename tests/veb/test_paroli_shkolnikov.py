"""Pupil passwords: minting, and the boundary that keeps a pupil inside their own row.

Zone: `tools/sozdat_lichnye_paroli.py`, `veb/vhod.py`, `core/services/lichnye_paroli.py`.

🔴 WHAT THESE TESTS ARE FOR.  The заход names the boundary, not the login, as the place this
feature fails: «Школьник, вошедший под собой, не должен видеть ни одной чужой галочки; и уж
точно не должен их ставить.  Проверяется запросами с чужими идентификаторами, а не
рассуждением о ролях.»  So the boundary tests below hand the code somebody else's identifier
and check what comes back, rather than asserting that a constant equals a string.
"""

import json
import subprocess
import sys
import sqlite3
from pathlib import Path

import pytest

KOREN = Path(__file__).resolve().parent.parent.parent

# The module reads these at use, not at import, but `veb.vhod` needs a secret to sign with.
import os
os.environ.setdefault("SPETSMAT_VEB_PAROL_PREPOD", "teacher-pass")
os.environ.setdefault("SPETSMAT_VEB_PAROL_ORG", "org-pass")
os.environ.setdefault("SPETSMAT_VEB_SECRET", "test-secret-key-32bytes!")

import veb.vhod as vh
import tools.sozdat_lichnye_paroli as mint


class FakeHeaders:
    """Minimal stand-in for BaseHTTPRequestHandler.headers, as in test_vhod.py."""

    def __init__(self, cookie=""):
        self._cookie = cookie

    def get(self, name, default=""):
        return self._cookie if name == "Cookie" else default


def kuka(raw: str) -> FakeHeaders:
    return FakeHeaders(cookie="%s=%s" % (vh.COOKIE_NAME, raw))


@pytest.fixture
def baza(tmp_path):
    """A база with two teachers and three pupils -- the three the criterion asks for."""
    put = tmp_path / "spetsmat.db"
    c = sqlite3.connect(put)
    c.executescript("""
        create table teachers (id integer primary key, tg_id integer, name text not null,
            aka text, is_owner integer not null default 0, kabinet text,
            aktiven integer not null default 1, gruppa text);
        create table gruppy (kod text primary key, starshij text not null);
        create table students (id integer primary key, tg_id integer, surname text not null,
            name text not null, class text, status text not null default 'pending',
            first_sheet_id integer, gruppa text);
        insert into teachers (id, name, aktiven, gruppa) values (1, 'Ваня Яковлев', 1, 'В');
        insert into teachers (id, name, aktiven, gruppa) values (2, 'Пётр Петров', 1, 'Д');
        insert into gruppy (kod, starshij) values ('В', 'Ваня Яковлев');
        insert into students (id, surname, name, class, status)
            values (1, 'Агаркова', 'Ирина', '9Л', 'active');
        insert into students (id, surname, name, class, status)
            values (2, 'Фомин', 'Иван', '9К', 'active');
        insert into students (id, surname, name, class, status)
            values (3, 'Шарова', 'Жанна', '9К', 'active');
        insert into students (id, surname, name, class, status)
            values (4, 'Ушедший', 'Олег', '9К', 'left');
    """)
    c.commit()
    c.close()
    return put


def chekanit(baza, tajniki, kogo, *dopolnitelno):
    """Run the real script as a subprocess -- the way the owner runs it."""
    return subprocess.run(
        [sys.executable, str(KOREN / "tools" / "sozdat_lichnye_paroli.py"),
         "--db", str(baza), "--secrets", str(tajniki), "--kogo", kogo, *dopolnitelno],
        cwd=str(KOREN), capture_output=True, text=True)


def paroli_iz_spiska(put: Path) -> dict:
    """`{фамилия: пароль}` out of the plaintext list the owner hands out."""
    otvet = {}
    for stroka in put.read_text(encoding="utf-8").splitlines():
        if not stroka.strip() or stroka.startswith("#"):
            continue
        chasti = stroka.split()
        otvet[chasti[0]] = chasti[-1]
    return otvet


# ------------------------------------------------------------------ часть 1: чеканка


def test_initsialy_idut_imya_potom_familiya():
    """The owner's own example: `ИФ17` -- ИМЯ first, ФАМИЛИЯ second, not the other way round."""
    assert mint.initsialy("Ирина", "Агаркова") == "IA"
    assert mint.initsialy("Иван", "Фомин") == "IF"
    # A letter whose single-Latin form would collide with another letter's keeps its digraph.
    assert mint.initsialy("Жанна", "Шарова") == "ZHSH"


def test_parol_shkolnika_eto_initsialy_i_chislo(baza, tmp_path):
    tajniki = tmp_path / "secrets"
    rezultat = chekanit(baza, tajniki, "shkolniki")
    assert rezultat.returncode == 0, rezultat.stderr

    paroli = paroli_iz_spiska(tajniki / next(
        p.name for p in tajniki.iterdir() if p.name.startswith("paroli-shkolnikov-")))
    assert paroli["Агаркова"].startswith("IA")
    assert paroli["Фомин"].startswith("IF")
    assert all(p[len(p.rstrip("0123456789")):].isdigit() for p in paroli.values())
    # Only the three ACTIVE pupils; the one who left gets no password.
    assert set(paroli) == {"Агаркова", "Фомин", "Шарова"}


def test_chislo_v_parole_ne_est_nomer_stroki(baza, tmp_path):
    """🔴 The number must NOT be `students.id`: the roster of names is on the public half of
    the site, so an id-derived password is derivable by anyone who can read the site.

    Minted twice, the same pupil must get a different number -- which an id never would.
    """
    chisla = set()
    for n in range(6):
        tajniki = tmp_path / ("s%d" % n)
        assert chekanit(baza, tajniki, "shkolniki").returncode == 0
        spisok = next(p for p in tajniki.iterdir() if p.name.startswith("paroli-shkolnikov-"))
        chisla.add(paroli_iz_spiska(spisok)["Агаркова"])
    assert len(chisla) > 1, "the number repeats across mints -- it is derived, not random"


def test_chekanka_shkolnikov_ne_gasit_prepodavatelej(baza, tmp_path):
    """🔴 Критерий 4.  Minting pupils must leave every teacher password working.

    Not "the file still has teachers in it" -- the exact salt and hash, byte for byte.  A
    re-hash would be invisible here and would log all fourteen teachers out in production.
    """
    tajniki = tmp_path / "secrets"
    assert chekanit(baza, tajniki, "prepodavateli").returncode == 0
    do = {z["uid"]: (z["sol"], z["hesh"])
          for z in json.loads((tajniki / "veb-lichnye-paroli.json").read_text())["lyudi"]}
    assert len(do) == 2

    assert chekanit(baza, tajniki, "shkolniki").returncode == 0
    posle = json.loads((tajniki / "veb-lichnye-paroli.json").read_text())["lyudi"]
    prepody = {z["uid"]: (z["sol"], z["hesh"]) for z in posle if z["rol"] != "shkolnik"}
    assert prepody == do
    assert sum(1 for z in posle if z["rol"] == "shkolnik") == 3


def test_vtoraya_chekanka_otkazyvaet_bez_perezapisat(baza, tmp_path):
    tajniki = tmp_path / "secrets"
    assert chekanit(baza, tajniki, "shkolniki").returncode == 0
    povtor = chekanit(baza, tajniki, "shkolniki")
    assert povtor.returncode == 1
    assert "REFUSED" in povtor.stderr
    assert chekanit(baza, tajniki, "shkolniki", "--perezapisat").returncode == 0


def test_ni_odin_parol_ne_popal_v_vyvod_progona(baza, tmp_path):
    """Критерий 5, the half a test can carry: the run's own output names no password."""
    tajniki = tmp_path / "secrets"
    rezultat = chekanit(baza, tajniki, "shkolniki")
    spisok = next(p for p in tajniki.iterdir() if p.name.startswith("paroli-shkolnikov-"))
    paroli = set(paroli_iz_spiska(spisok).values())
    assert paroli
    vyvod = rezultat.stdout + rezultat.stderr
    assert not [p for p in paroli if p in vyvod]
    # ... and the hash file carries none of them either.
    heshi = (tajniki / "veb-lichnye-paroli.json").read_text(encoding="utf-8")
    assert not [p for p in paroli if p in heshi]


def test_oba_fajla_600(baza, tmp_path):
    tajniki = tmp_path / "secrets"
    assert chekanit(baza, tajniki, "shkolniki").returncode == 0
    for put in tajniki.iterdir():
        assert put.stat().st_mode & 0o777 == 0o600, put
