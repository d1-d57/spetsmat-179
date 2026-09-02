"""🔴 The position: the check can go red, and it says which assertion caught it.

A check that cannot fail is a hope, not a check, and the only way to know it can is to
break a snapshot on purpose and demand that it says so.  Every test here is that demand,
plus the one test that is easy to forget: that the corruption run itself notices a
corruption coming back GREEN, because otherwise the self-test is the hope.

Coverage is stated, not implied: six corruptions, each named, each aimed at a named
assertion, and the boundaries of the two numeric assertions checked on both sides.  Two of
the six -- an empty snapshot and a mark dated in the future -- are there because the §3
verifier of this position found the check GREEN on them; they are regressions now.
"""

from __future__ import annotations

import gzip
import shutil
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from core.isotime import to_iso
from tools.proverka_vosstanovlenia import (
    FRESH_DAYS,
    MIN_STUDENTS,
    PORCHI,
    command_na_porchennom,
    main,
    proverit_snimok,
    snyat_snimok,
)


def _krasnye(proverki) -> list:
    return [p.imya for p in proverki if not p.ok]


@pytest.fixture
def celyj_snimok(bolshoy_mir, svezhaya_otmetka, zakrytaya_baza, tmp_path):
    """A whole snapshot of a healthy database: the control every corruption is measured from."""
    return snyat_snimok(zakrytaya_baza, tmp_path / "backups")


# ---------------------------------------------------------------------------- control


def test_celyj_snimok_zelyonyj_po_vsem_tryom(celyj_snimok):
    """Green, and green with values -- otherwise the corruptions below prove nothing.

    If the whole snapshot were red, every corruption would "redden" for free and the
    coverage number would be a lie told with true arithmetic.
    """
    proverki = proverit_snimok(celyj_snimok)

    assert len(proverki) == 3
    assert _krasnye(proverki) == []
    assert [p.imya for p in proverki] == ["целостность", "учеников", "свежесть отметки"]
    assert "56" in proverki[1].znachenie, "проверка обязана печатать измеренное значение"


# ------------------------------------------------------------------------ the corruptions


@pytest.mark.parametrize(
    "imya, celilis",
    [
        ("обрезан", "целостность"),
        ("бит перевёрнут", "целостность"),
        ("таблица учеников пуста", "учеников"),
        ("последняя отметка состарена", "свежесть отметки"),
        ("снимок пуст", "целостность"),
        ("отметка из будущего", "свежесть отметки"),
    ],
)
def test_kazhdaya_porcha_krasneet_na_svoyom_utverzhdenii(celyj_snimok, tmp_path, imya, celilis):
    """Every corruption reddens, and the assertion it was aimed at is among the red ones.

    "Reddened" alone is not enough: a snapshot that failed the wrong assertion would still
    print red, and the check would be right by accident.  This asserts the aim.
    """
    porchenyj = tmp_path / ("porcha-%s.db.gz" % imya.replace(" ", "-"))
    shutil.copyfile(celyj_snimok, porchenyj)

    assert PORCHI[imya](porchenyj) == celilis

    krasnye = _krasnye(proverit_snimok(porchenyj))
    assert krasnye, "ЗЕЛЁНОЕ НА ПОРЧЕ «%s» — это провал позиции" % imya
    assert celilis in krasnye


def test_reestr_porch_pokryvaet_vse_tri_utverzhdeniya(celyj_snimok, tmp_path):
    """Between them the corruptions aim at all three assertions.

    A registry that reddened only assertion 1 six times would report "порч 6, покраснело 6"
    while assertions 2 and 3 had never once been shown to work.
    """
    celi = set()
    for imya, porcha in PORCHI.items():
        porchenyj = tmp_path / ("cel-%d.db.gz" % len(celi))
        shutil.copyfile(celyj_snimok, porchenyj)
        celi.add(porcha(porchenyj))

    assert celi == {"целостность", "учеников", "свежесть отметки"}


def test_nerazobrannyj_snimok_krasnit_vse_tri_a_ne_molchit(celyj_snimok, tmp_path):
    """A snapshot that does not unpack reports three reds, not one red and two silences.

    A skipped assertion in the report of a failure reads exactly like one that passed, and
    the person reading it at midnight has to go and find out which.
    """
    porchenyj = tmp_path / "obrezan.db.gz"
    shutil.copyfile(celyj_snimok, porchenyj)
    PORCHI["обрезан"](porchenyj)

    proverki = proverit_snimok(porchenyj)
    assert len(_krasnye(proverki)) == 3
    assert "не распаковывается" in proverki[0].znachenie
    assert all("не проверено" in p.znachenie for p in proverki[1:])


def test_pustoy_zhurnal_eto_krasnoe_a_ne_zelyonoe(bolshoy_mir, zakrytaya_baza, tmp_path):
    """A database with no marks at all fails assertion 3 rather than passing it vacuously.

    ``max(valid_at)`` over an empty table is NULL, and "no marks" compared against a
    threshold would sail through every naive comparison.
    """
    snapshot = snyat_snimok(zakrytaya_baza, tmp_path / "backups")
    proverki = proverit_snimok(snapshot)

    assert "свежесть отметки" in _krasnye(proverki)
    assert "отметок нет вовсе" in proverki[2].znachenie


# ------------------------------------------------------------------------- the boundaries


@pytest.mark.parametrize("uchenikov, ozhidaem_krasnoe", [(MIN_STUDENTS - 1, True), (MIN_STUDENTS, False)])
def test_granica_chisla_uchenikov(celyj_snimok, tmp_path, uchenikov, ozhidaem_krasnoe):
    """Assertion 2 is ``>=``: at fifty it passes, at forty-nine it does not."""
    porchenyj = tmp_path / ("granica-%d.db.gz" % uchenikov)
    _hirurgiya(celyj_snimok, porchenyj,
               "delete from students where id in (select id from students order by id desc limit %d)"
               % (56 - uchenikov))

    proverki = proverit_snimok(porchenyj)
    assert ("учеников" in _krasnye(proverki)) is ozhidaem_krasnoe
    assert str(uchenikov) in proverki[1].znachenie


@pytest.mark.parametrize(
    "minut_ot_granicy, ozhidaem_krasnoe", [(-1, False), (1, True), (60 * 23, True)]
)
def test_granica_svezhesti_schitaetsya_po_intervalu_a_ne_po_celym_dnyam(
    celyj_snimok, tmp_path, minut_ot_granicy, ozhidaem_krasnoe
):
    """Assertion 3 measures the interval, not ``timedelta.days``.

    🔴 THE THIRD CASE IS THE ONE THAT USED TO PASS.  ``.days`` floors, so a mark seven days
    and twenty-three hours old measured as 7 and sailed through a rule that says "no older
    than a week": the assertion was quietly a day and a half wider than it claimed, and it
    was the §3 verifier that measured it.
    """
    vozrast = timedelta(days=FRESH_DAYS, minutes=minut_ot_granicy)
    staraya = to_iso(datetime.now(timezone.utc) - vozrast)
    porchenyj = tmp_path / ("vozrast-%d.db.gz" % minut_ot_granicy)
    _hirurgiya(celyj_snimok, porchenyj,
               "drop trigger if exists marks_append_only_update",
               "update marks set valid_at = '%s'" % staraya)

    proverki = proverit_snimok(porchenyj)
    assert ("свежесть отметки" in _krasnye(proverki)) is ozhidaem_krasnoe
    assert "возраст" in proverki[2].znachenie


def test_otmetka_iz_budushchego_krasnaya_i_nazvana_otdelno(celyj_snimok, tmp_path):
    """A mark dated ahead of now is red, and red for its own reason.

    🔴 IT USED TO BE GREEN, at "возраст -365 дн." -- one skewed row would have held this
    assertion green while nobody marked anything for a term.  The verdict names the clock
    rather than the staleness, because the repair is a different repair.
    """
    budushchee = to_iso(datetime.now(timezone.utc) + timedelta(days=365))
    porchenyj = tmp_path / "budushchee.db.gz"
    _hirurgiya(celyj_snimok, porchenyj,
               "drop trigger if exists marks_append_only_update",
               "update marks set valid_at = '%s'" % budushchee)

    proverki = proverit_snimok(porchenyj)
    assert "свежесть отметки" in _krasnye(proverki)
    assert "БУДУЩЕМ" in proverki[2].znachenie


def test_nebolshoy_sdvig_chasov_ne_krasneet(celyj_snimok, tmp_path):
    """A mark a minute ahead of now is ordinary clock skew, not a corrupted backup.

    The bound has to be a bound and not zero: the mark is stamped by the bot's machine and
    read by whichever machine runs the check.
    """
    chut_vperedi = to_iso(datetime.now(timezone.utc) + timedelta(minutes=1))
    porchenyj = tmp_path / "sdvig.db.gz"
    _hirurgiya(celyj_snimok, porchenyj,
               "drop trigger if exists marks_append_only_update",
               "update marks set valid_at = '%s'" % chut_vperedi)

    assert "свежесть отметки" not in _krasnye(proverit_snimok(porchenyj))


def test_pustoy_snimok_krasneet_na_celostnosti(celyj_snimok, tmp_path):
    """🔴 A zero-byte snapshot is RED, and red on the assertion named ``целостность``.

    It used to be GREEN there, and that is the failure this whole position is about: the
    backup "ran", copied nothing, and the one assertion whose job is to notice reported
    ``ок``.  ``gzip`` yields an empty stream without complaining and ``sqlite3.connect``
    builds a fresh empty database out of the nothing, so ``pragma integrity_check`` was
    answering about a database it had just created itself.  Found by the §3 verifier.
    """
    pustoy = tmp_path / "pustoy.db.gz"
    pustoy.write_bytes(b"")

    proverki = proverit_snimok(pustoy)
    assert "целостность" in _krasnye(proverki)
    assert "0 байт" in proverki[0].znachenie
    assert len(_krasnye(proverki)) == 3, "нечего восстанавливать — молчать нельзя ни по одному"


def test_ne_baza_pod_gzipom_krasneet_na_celostnosti(celyj_snimok, tmp_path):
    """Something that unpacks fine but is not a database is red on the same assertion."""
    import gzip as _gzip

    ne_baza = tmp_path / "ne-baza.db.gz"
    with _gzip.open(ne_baza, "wb") as handle:
        handle.write("это не база, это обычный текст".encode("utf-8") * 100)

    proverki = proverit_snimok(ne_baza)
    assert "целостность" in _krasnye(proverki)
    assert "не в базу SQLite" in proverki[0].znachenie


def _hirurgiya(istochnik: Path, cel: Path, *sql: str) -> Path:
    """Unpack a snapshot, run SQL on it, pack it back under a new name."""
    plain = cel.with_suffix(".plain.db")
    with gzip.open(istochnik, "rb") as source:
        plain.write_bytes(source.read())
    connection = sqlite3.connect(str(plain), isolation_level=None)
    try:
        for statement in sql:
            connection.execute(statement)
    finally:
        connection.close()
    with plain.open("rb") as source, gzip.open(cel, "wb") as target:
        shutil.copyfileobj(source, target)
    return cel


# ------------------------------------------------------- the self-test of the self-test


def test_progon_po_porcham_vozvrashchaet_1_i_schitaet_ohvat(
    bolshoy_mir, svezhaya_otmetka, zakrytaya_baza, tmp_path, capsys
):
    """``--na-porchennom`` is red BY CONSTRUCTION, and rc=1 means every corruption was caught.

    The criterion demands rc≠0 here: this is a run of the check over corrupted snapshots,
    and a zero would be the very thing the position exists to rule out.  The two non-zero
    codes carry the verdict -- 1 for "all caught", 2 for "one came back green".
    """
    kod = command_na_porchennom(zakrytaya_baza, tmp_path / "backups")
    vyvod = capsys.readouterr().out

    assert kod == 1
    assert "порч %d, покраснело %d" % (len(PORCHI), len(PORCHI)) in vyvod
    for imya in PORCHI:
        assert imya in vyvod, "каждая порча обязана быть названа поимённо"
    assert "ложно-зелёных 0" in vyvod


def test_zelyonoe_na_porche_eto_rc_2_a_ne_tihiy_uspekh(
    bolshoy_mir, svezhaya_otmetka, zakrytaya_baza, tmp_path, capsys, monkeypatch
):
    """🔴 A corruption that does NOT redden is caught and named, and the run returns 2.

    This is the test of the test.  Without it, ``--na-porchennom`` would be a self-test
    that can only ever agree with itself: a corruption that quietly did nothing would look
    exactly like a corruption the check survived, and both would print green.
    """
    def nichego_ne_portit(snapshot):
        return "целостность"

    # ``monkeypatch`` puts the registry back afterwards; the following test would otherwise
    # count five corruptions and fail for a reason that has nothing to do with it.
    monkeypatch.setitem(PORCHI, "мнимая порча", nichego_ne_portit)
    kod = command_na_porchennom(zakrytaya_baza, tmp_path / "backups")
    vyvod = capsys.readouterr().out

    assert kod == 2
    assert "ЗЕЛЁНОЕ НА ПОРЧЕ" in vyvod
    assert "мнимая порча" in vyvod


def test_cli_na_porchennom_krasnyj(bolshoy_mir, svezhaya_otmetka, zakrytaya_baza, tmp_path, capsys):
    """The criterion's own command line, through ``main``."""
    kod = main(["--baza", str(zakrytaya_baza), "--snimki", str(tmp_path / "backups"),
                "--na-porchennom"])
    assert kod != 0, "ЗЕЛЁНОЕ ЗДЕСЬ ЕСТЬ ПРОВАЛ ПОЗИЦИИ"
    assert "порч 6, покраснело 6" in capsys.readouterr().out
