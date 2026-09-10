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
    """`{фамилия или имя: пароль}` out of the plaintext list the owner hands out.

    The two lists are shaped differently, and the teachers' one is why this is not a `split()`:
    a teacher is written down by full name («Ваня Яковлев»), so the first whitespace-separated
    token is a given name, not the key.  The word «аудитория» is the fixed marker after it.
    """
    otvet = {}
    for stroka in put.read_text(encoding="utf-8").splitlines():
        if not stroka.strip() or stroka.startswith("#"):
            continue
        if "аудитория" in stroka:
            imya = stroka.split("аудитория")[0].strip()
        else:
            imya = stroka.split()[0]
        otvet[imya] = stroka.split()[-1]
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


# ------------------------------------------------------------------ часть 2: граница


@pytest.fixture
def tri_shkolnika(baza, tmp_path, monkeypatch):
    """Mint for the fixture база and point `veb.vhod` at the result.

    Returns `{фамилия: (uid, пароль)}` for the three pupils and the two teachers.
    """
    tajniki = tmp_path / "secrets"
    assert chekanit(baza, tajniki, "vse").returncode == 0
    monkeypatch.setenv("SPETSMAT_VEB_LICHNYE", str(tajniki / "veb-lichnye-paroli.json"))
    monkeypatch.setenv("SPETSMAT_VEB_SMENENNYE", str(tajniki / "veb-smenennye-paroli.json"))
    monkeypatch.setenv("SPETSMAT_VEB_SECRET", "test-secret-key-32bytes!")

    zapisi = json.loads((tajniki / "veb-lichnye-paroli.json").read_text())["lyudi"]
    po_imeni = {}
    for spisok, klyuch in ((tajniki / next(p.name for p in tajniki.iterdir()
                                           if p.name.startswith("paroli-shkolnikov-")), "shkolnik"),
                           (tajniki / next(p.name for p in tajniki.iterdir()
                                           if p.name.startswith("paroli-prepodavatelej-")), None)):
        for imya, parol in paroli_iz_spiska(spisok).items():
            zapis = next(z for z in zapisi
                         if (z.get("familiya") or z.get("imya")) == imya
                         and (z["rol"] == "shkolnik") == (klyuch == "shkolnik"))
            po_imeni[imya] = (zapis["uid"], parol)
    po_imeni["_tajniki"] = tajniki
    return po_imeni


def test_shkolnik_vhodit_i_ego_uznayut(tri_shkolnika):
    """Three pupils sign in, and each cookie names the pupil it was made for -- nobody else."""
    for familiya in ("Агаркова", "Фомин", "Шарова"):
        uid, parol = tri_shkolnika[familiya]
        otvet = vh.proverit_parol(parol)
        assert otvet == ("shkolnik", uid), familiya
        golova = kuka(vh._make_cookie("shkolnik", uid))
        assert vh.shkolnik(golova) == uid


def test_shkolnik_ne_poluchaet_roli_i_potomu_nichego_ne_vidit(tri_shkolnika):
    """🔴 ГЛАВНОЕ МЕСТО ОТКАЗА.  A pupil's cookie is valid and gives `rol()` None.

    Every gate on this site — ticking (`veb/priyom.py:159`), the card's `vhodivshij`
    (`veb/server.py:893`), editing, the root page — is `rol(...) is None`.  So this one
    assertion is what says a signed-in pupil can neither see nor set a single mark, anybody's
    own included, without a line changing in any of those files.
    """
    uid, parol = tri_shkolnika["Агаркова"]
    golova = kuka(vh._make_cookie("shkolnik", uid))
    assert vh.rol(golova) is None
    assert vh._check_password(parol) is None
    # ... and the pupil is still recognised as themselves.
    assert vh.shkolnik(golova) == uid


def test_uid_shkolnika_ne_utekaet_v_kto(tri_shkolnika):
    """`kto()` means `teachers.id`.  A pupil id arriving there would name a different person.

    `students.id` 1 and `teachers.id` 1 are both real rows in the fixture база, which is the
    whole reason this cannot be left to "the roles are different, it will be fine".
    """
    uid, _ = tri_shkolnika["Агаркова"]
    assert uid == 1
    assert vh.kto(kuka(vh._make_cookie("shkolnik", uid))) is None
    # ... and symmetrically, a teacher is not a pupil.
    assert vh.shkolnik(kuka(vh._make_cookie("prepod", 1))) is None
    assert vh.kto(kuka(vh._make_cookie("prepod", 1))) == 1


def test_shkolnik_a_ne_mozhet_poprosit_dannye_shkolnika_b(tri_shkolnika):
    """🔴 Критерий 2, and it is checked with somebody else's identifier, not by reasoning.

    Pupil A holds A's cookie and wants B.  There are exactly two things A can do: pass B's id
    (there is no parameter for it — `shkolnik(headers)` takes headers and nothing else), or
    edit the cookie to say B.  The second is what this test does, byte by byte, and it fails
    on the signature before any id is read.
    """
    a_uid, _ = tri_shkolnika["Агаркова"]
    b_uid, _ = tri_shkolnika["Фомин"]
    assert a_uid != b_uid

    a_kuka = vh._make_cookie("shkolnik", a_uid)
    assert vh.shkolnik(kuka(a_kuka)) == a_uid

    # A rewrites the payload to name B and keeps A's signature.
    import base64
    telo, podpis = a_kuka.rsplit(".", 1)
    razobrano = json.loads(base64.urlsafe_b64decode(telo + "=" * (-len(telo) % 4)))
    razobrano["u"] = b_uid
    poddelka = base64.urlsafe_b64encode(json.dumps(razobrano).encode()).decode().rstrip("=")
    assert vh.shkolnik(kuka("%s.%s" % (poddelka, podpis))) is None

    # A promotes itself to a staff role, same trick.
    razobrano["u"], razobrano["r"] = a_uid, "organizator"
    poddelka = base64.urlsafe_b64encode(json.dumps(razobrano).encode()).decode().rstrip("=")
    assert vh.rol(kuka("%s.%s" % (poddelka, podpis))) is None

    # A guesses B's password by shape.  Ninety candidates; none of them is A's business, and
    # the ones that are wrong answer nothing at all.
    _, b_parol = tri_shkolnika["Фомин"]
    nachalo = b_parol.rstrip("0123456789")
    lozhnye = ["%s%s" % (nachalo, n) for n in range(10, 100) if "%s%s" % (nachalo, n) != b_parol]
    assert all(vh.proverit_parol(p) is None for p in lozhnye[:12])


def test_vhod_prepodavatelej_posle_pravki_rabotaet(tri_shkolnika):
    """🔴 Критерий 4 in the suite; the live half is in `## ОТЧЁТ`."""
    for imya in ("Ваня Яковлев", "Пётр Петров"):
        uid, parol = tri_shkolnika[imya]
        rol_i_kto = vh.proverit_parol(parol)
        assert rol_i_kto is not None, imya
        assert rol_i_kto[0] in vh.ROLI_PERSONALA
        assert rol_i_kto[1] == uid
    # The senior of an auditorium is still the organiser, by the rule and not by a list.
    assert vh.proverit_parol(tri_shkolnika["Ваня Яковлев"][1])[0] == "organizator"


def test_obshchie_paroli_iz_okruzheniya_zhivy(tri_shkolnika, monkeypatch):
    monkeypatch.setenv("SPETSMAT_VEB_PAROL_PREPOD", "teacher-pass")
    monkeypatch.setenv("SPETSMAT_VEB_PAROL_ORG", "org-pass")
    assert vh.proverit_parol("teacher-pass") == ("prepod", None)
    assert vh.proverit_parol("org-pass") == ("organizator", None)


def test_neverny_parol_stoit_ne_dorozhe_chem_do_shkolnikov(tri_shkolnika):
    """The bucketing, checked as behaviour: a wrong password is hashed against the adults and
    the pupils sharing its initials, not against every pupil in the school.

    Counted rather than timed — a timing assertion on a laptop under load is a flake.
    """
    schyot = {"n": 0}
    nastoyashchij = vh._hesh_kandidata

    def schitat(*args, **kwargs):
        schyot["n"] += 1
        return nastoyashchij(*args, **kwargs)

    vh._hesh_kandidata = schitat
    try:
        assert vh.proverit_parol("ZZ99") is None
        vzroslyh = 2
        # the two teachers, plus the pupils whose initials are literally "ZZ" (none)
        assert schyot["n"] == vzroslyh
    finally:
        vh._hesh_kandidata = nastoyashchij


# ------------------------------------------------------------------ часть 3: смена пароля


def test_smena_parolya_gasit_vydannyj_i_zapominaetsya(tri_shkolnika):
    """«Смена пароля на свой — и он запоминается навсегда.»

    Three facts, and the middle one is the whole point: the new one works, the OLD one stops
    working, and a fresh mint of the pupils does not resurrect the old one.
    """
    from core.services.lichnye_paroli import smenit

    uid, vydannyj = tri_shkolnika["Агаркова"]
    assert vh.proverit_parol(vydannyj) == ("shkolnik", uid)

    smenit("shkolnik", uid, vydannyj, "moy-sobstvennyj-parol", proverka=vh.proverit_parol)

    assert vh.proverit_parol("moy-sobstvennyj-parol") == ("shkolnik", uid)
    assert vh.proverit_parol(vydannyj) is None

    # ... and it survives the owner minting everybody's password afresh.
    tajniki = tri_shkolnika["_tajniki"]
    baza = json.loads((tajniki / "veb-lichnye-paroli.json").read_text())["istochnik"]
    assert chekanit(Path(baza), tajniki, "shkolniki", "--perezapisat").returncode == 0
    assert vh.proverit_parol("moy-sobstvennyj-parol") == ("shkolnik", uid)


def test_chuzhoj_tekushchij_parol_smenu_ne_otkryvaet(tri_shkolnika):
    """🔴 The boundary again, arriving through the door meant to protect it.

    Pupil B's password is a REAL password — it just is not A's.  If the change accepted "any
    password that belongs to somebody", B could rewrite A's password out from under A.
    """
    from core.services.lichnye_paroli import OtkazSmeny, smenit

    a_uid, a_parol = tri_shkolnika["Агаркова"]
    _, b_parol = tri_shkolnika["Фомин"]

    with pytest.raises(OtkazSmeny):
        smenit("shkolnik", a_uid, b_parol, "novyj-parol", proverka=vh.proverit_parol)
    with pytest.raises(OtkazSmeny):
        smenit("shkolnik", a_uid, "sovsem-ne-parol", "novyj-parol", proverka=vh.proverit_parol)
    # A's own password is untouched by either refusal.
    assert vh.proverit_parol(a_parol) == ("shkolnik", a_uid)


def test_shkolnik_ne_mozhet_smenit_parol_prepodavatelyu(tri_shkolnika):
    """A pupil holding their own password cannot aim the change at a teacher's row."""
    from core.services.lichnye_paroli import OtkazSmeny, smenit

    _, parol_shkolnika = tri_shkolnika["Агаркова"]
    prepod_uid, _ = tri_shkolnika["Пётр Петров"]
    with pytest.raises(OtkazSmeny):
        smenit("prepod", prepod_uid, parol_shkolnika, "novyj", proverka=vh.proverit_parol)


def test_smena_ne_puskaet_negodnyj_parol(tri_shkolnika):
    from core.services.lichnye_paroli import OtkazSmeny, smenit

    uid, vydannyj = tri_shkolnika["Агаркова"]
    for negodnyj in ("abc", " parol", "parol ", "x" * 200):
        with pytest.raises(OtkazSmeny):
            smenit("shkolnik", uid, vydannyj, negodnyj, proverka=vh.proverit_parol)
    assert vh.proverit_parol(vydannyj) == ("shkolnik", uid)


def test_smena_pishet_600_i_ne_hranit_parol(tri_shkolnika):
    from core.services.lichnye_paroli import fajl_smenennyh, smenit

    uid, vydannyj = tri_shkolnika["Агаркова"]
    smenit("shkolnik", uid, vydannyj, "moy-sobstvennyj-parol", proverka=vh.proverit_parol)
    put = fajl_smenennyh()
    assert put.stat().st_mode & 0o777 == 0o600
    tekst = put.read_text(encoding="utf-8")
    assert "moy-sobstvennyj-parol" not in tekst
    assert vydannyj not in tekst


def test_vtoraya_smena_zamenyaet_pervuyu_a_ne_dobavlyaet(tri_shkolnika):
    """Two changes leave ONE way in, not two."""
    from core.services.lichnye_paroli import fajl_smenennyh, smenit

    uid, vydannyj = tri_shkolnika["Агаркова"]
    smenit("shkolnik", uid, vydannyj, "pervyj-vybrannyj", proverka=vh.proverit_parol)
    smenit("shkolnik", uid, "pervyj-vybrannyj", "vtoroj-vybrannyj", proverka=vh.proverit_parol)

    assert vh.proverit_parol("vtoroj-vybrannyj") == ("shkolnik", uid)
    assert vh.proverit_parol("pervyj-vybrannyj") is None
    zapisi = json.loads(fajl_smenennyh().read_text())["lyudi"]
    assert len([z for z in zapisi if z["uid"] == uid and z["rol"] == "shkolnik"]) == 1


def test_smena_ne_trogaet_sosedej(tri_shkolnika):
    """A change is one row.  Everybody else logs in exactly as before."""
    from core.services.lichnye_paroli import smenit

    uid, vydannyj = tri_shkolnika["Агаркова"]
    smenit("shkolnik", uid, vydannyj, "moy-sobstvennyj-parol", proverka=vh.proverit_parol)
    for imya in ("Фомин", "Шарова", "Ваня Яковлев", "Пётр Петров"):
        chuzhoj_uid, chuzhoj_parol = tri_shkolnika[imya]
        otvet = vh.proverit_parol(chuzhoj_parol)
        assert otvet is not None and otvet[1] == chuzhoj_uid, imya


def test_smenennyj_parol_vsyo_ravno_ne_daet_roli(tri_shkolnika):
    """A pupil who chose a long strong password is still a pupil: `rol()` is still None."""
    from core.services.lichnye_paroli import smenit

    uid, vydannyj = tri_shkolnika["Агаркова"]
    smenit("shkolnik", uid, vydannyj, "moy-sobstvennyj-parol", proverka=vh.proverit_parol)
    rol_i_kto = vh.proverit_parol("moy-sobstvennyj-parol")
    assert rol_i_kto == ("shkolnik", uid)
    golova = kuka(vh._make_cookie(*rol_i_kto))
    assert vh.rol(golova) is None
    assert vh.kto(golova) is None
    assert vh.shkolnik(golova) == uid
