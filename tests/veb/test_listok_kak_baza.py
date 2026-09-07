"""The sheet as a set of blocks: the parser, the gate that guards it, and the page.

WHAT THESE TESTS ARE FOR.  The composition of a sheet used to be typed in by hand, and on
2026-09-07 the typed version of `16α` and the PDF the site served disagreed — eleven cells
against fifteen problems.  The importer removes the typing; these tests hold the property
that made the typing dangerous in the first place: that nothing checks the result.

🔴 THE PDFs ARE THE FIXTURE, ON PURPOSE.  `docs/listki/*.pdf` are the files the site hands
out, they are in the repository, and parsing them here is parsing exactly what the pupils
downloaded.  A synthetic fixture would test the parser against a sheet that does not exist.
"""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

KOREN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOREN))

from tools.import_listka import (  # noqa: E402
    OZHIDAEMYJ_SOSTAV,
    razobrat,
    v_tex,
    vnesti,
    yachejki,
)
from veb.razdely import list_odin  # noqa: E402


@pytest.mark.parametrize("nomer", sorted(OZHIDAEMYJ_SOSTAV))
def test_razbor_pdf_daet_sostav_kotoryj_stoit_v_listke(nomer):
    """The parser reproduces, from the served PDF, the composition read off it by hand."""
    bloki, otkuda = razobrat(nomer)
    assert otkuda.suffix == ".pdf"
    assert yachejki(bloki) == OZHIDAEMYJ_SOSTAV[nomer]


def test_u_16alpha_punkty_stoyat_u_zadachi_14_a_ne_u_10():
    """The exact mistake of 2026-09-07, as a test: `14в` exists, `10в` does not."""
    sostav = yachejki(razobrat("16α")[0])
    assert "14в" in sostav
    assert "10в" not in sostav
    assert "10" in sostav


def _baza(tmp_path: Path) -> sqlite3.Connection:
    """A database with the schema of the project and one sheet in it."""
    put = tmp_path / "proba.db"
    subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, %r); from infra.db import apply_migrations; "
         "apply_migrations(%r, %r)" % (str(KOREN), str(put), str(KOREN / "migrations"))],
        check=True, capture_output=True)
    conn = sqlite3.connect(str(put), isolation_level=None)
    conn.execute("insert into sheets (number, title, issued_at, ord) "
                 "values ('16α', 'Деревья', '2026-09-03', 100)")
    return conn


def test_vtoroj_progon_nichego_ne_menyaet(tmp_path):
    """Idempotency by sheet number: the second import reports no changes at all."""
    conn = _baza(tmp_path)
    bloki = razobrat("16α")[0]
    vnesti(conn, "16α", bloki)
    vtoroj = vnesti(conn, "16α", bloki)
    assert vtoroj["блоков заведено"] == 0
    assert vtoroj["блоков обновлено"] == 0
    assert vtoroj["ячеек заведено"] == 0


def test_yachejka_s_otmetkoj_perezhivaet_import(tmp_path):
    """🔴 A cell that carries marks keeps its id, so the marks keep pointing at it.

    This is the property the whole two-table shape exists for: 16 013 marks were live on
    the server when it was chosen.
    """
    conn = _baza(tmp_path)
    sheet_id = conn.execute("select id from sheets").fetchone()[0]
    conn.execute("insert into problems (sheet_id, label, kind, ord) values (?, '10', 'обычная', 1)",
                 (sheet_id,))
    bylo = conn.execute("select id from problems where label = '10'").fetchone()[0]
    vnesti(conn, "16α", razobrat("16α")[0])
    stalo = conn.execute("select id from problems where label = '10'").fetchone()[0]
    assert stalo == bylo
    assert conn.execute("select block_id from problems where label = '10'").fetchone()[0] is not None


def test_stranica_pokazyvaet_zadachi_i_dve_ssylki_na_skachivanie(tmp_path):
    conn = _baza(tmp_path)
    vnesti(conn, "16α", razobrat("16α")[0])
    listok, bloki = list_odin.bloki(conn, "16α")
    html = list_odin.stranica(listok, bloki)
    assert "14в" in html            # the cell that did not exist before 2026-09-07
    assert "10в" not in html        # the cell that never should have
    assert "/listki/16α.pdf" in html
    assert "/listki/16α.tex" in html


def test_stranica_ne_vvodit_svoih_cvetov():
    """`doc/DIZAJN-ZAKREPLENO.md` §2: colours live in `:root` and nowhere else."""
    import re
    assert re.search(r"#[0-9a-fA-F]{3,6}\b", list_odin.SVOI_STILI) is None


def test_tex_sobiraetsya_iz_blokov():
    tex = v_tex("16α", razobrat("16α")[0])
    assert tex.startswith("% Собрано из базы задач")
    assert "\\begin{document}" in tex and "\\end{document}" in tex
    assert "Хозяйка испекла пирог" in tex          # problem 15, from the PDF


# ── THE ROUTE CONTRACT (ПРАВКА 4) ───────────────────────────────────────────
# A section declares `marshruty()` and the server picks it up, so a neighbouring заход
# adding `veb/priyom.py` needs no second edit of `veb/server.py`.

def test_otsutstvuyushchij_razdel_ne_ronyaet_sbor_marshrutov():
    """The neighbour is not on disk yet — the normal state while its заход runs."""
    from veb.server import _marshruty_razdelov

    assert isinstance(_marshruty_razdelov(), dict)


def test_razdel_obyavivshij_marshruty_popadaet_v_sbor(monkeypatch):
    import sys
    import types

    import veb.server as server

    modul = types.ModuleType("veb.priyom_proba")
    modul.marshruty = lambda: {"/priyom-proba": lambda handler: True}
    monkeypatch.setitem(sys.modules, "veb.priyom_proba", modul)
    monkeypatch.setattr(server, "RAZDELY_S_MARSHRUTAMI", ("veb.priyom_proba",))
    assert "/priyom-proba" in server._marshruty_razdelov()
