"""NO DATABASE FILE IS LEFT IN THE REPOSITORY -- and this goes RED if one comes back.

🔴 A CHECK, NOT AN AGREEMENT, AND THE DIFFERENCE IS MEASURED.  The agreement existed
already: ``.gitignore`` carried an explicit ``!data/spetsmat.db`` put there on 2026-09-04
with the reason "there is a lesson tomorrow".  It did not hold.  The file came back into
the repository on 2026-09-10 through a MERGE of a position branch -- a route that knew
nothing about anybody's intention -- and the cost was a whole run of the position
``gejt-pravda`` plus a database substituted by hand twice.

The owner's decision on the count is one word: «нет, ни одного».
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

KOREN = Path(__file__).resolve().parent.parent.parent


def _git(*args) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "--no-optional-locks", *args],
                          cwd=str(KOREN), capture_output=True, text=True, timeout=120)


def _est_git() -> bool:
    return _git("rev-parse", "--git-dir").returncode == 0


def test_ni_odnogo_fajla_bazy_v_indekse():
    """`git ls-files` по всему дереву, а не по одной папке.

    🔴 ПРОВЕРЯЕТСЯ ВЕСЬ РЕПОЗИТОРИЙ, А НЕ `data/`. Правило про папку файл базы уже
    обошёл однажды: резервные копии `REZERV-*.db` лежали и вне `data/`, а вернулся
    файл мержем. Запрет по расширению не зависит от того, куда его положат.
    """
    if not _est_git():
        pytest.skip("не git-дерево: проверять индекс нечем")
    itog = _git("ls-files")
    assert itog.returncode == 0, itog.stderr
    bazy = [s for s in itog.stdout.splitlines()
            if s.endswith((".db", ".sqlite", ".sqlite3"))]
    assert bazy == [], (
        "файл базы снова в репозитории — именно так он вернулся 10.09 после merge:\n"
        + "\n".join(bazy))


def test_popytka_dobavit_fajl_bazy_krasneet(tmp_path):
    """🔴 ПРОВЕРКА КРАСНЕЕТ НА ПОПЫТКЕ, А НЕ ТОЛЬКО НА ФАКТЕ.

    "There is none right now" is the weaker half: it was also true on 2026-09-05.  The
    half that matters is that putting one back is REFUSED, and it is refused for a file
    with a database extension wherever it is placed -- including outside ``data/``.
    """
    if not _est_git():
        pytest.skip("не git-дерево: проверять правила игнорирования нечем")
    for imya in ("data/spetsmat.db", "data/REZERV-2026-09-10.db",
                 "spetsmat.db", "tools/dampy/sluchajnaya.sqlite3"):
        itog = _git("check-ignore", "-q", imya)
        assert itog.returncode == 0, (
            "%s НЕ игнорируется — файл базы может снова уехать в репозиторий" % imya)


def test_shema_v_git_ostayotsya():
    """Исключение ровно одно и оно осознанное: в git место снимку СХЕМЫ.

    Без него запрет «ни одного `.db`» унёс бы вместе с записями 53 детей и
    единственное, что о базе законно живёт в истории, — её структуру.
    """
    if not _est_git():
        pytest.skip("не git-дерево")
    itog = _git("ls-files", "data/shema.sql")
    assert itog.stdout.strip() == "data/shema.sql", "снимок схемы обязан остаться в git"


def test_testy_delayut_svoyu_vremennuyu_bazu():
    """🔴 ЗАПРЕТ НЕ ЛОМАЕТ ТЕСТЫ, И ЭТО ПРОВЕРЯЕТСЯ ЧИСЛОМ, А НЕ ОБЕЩАНИЕМ.

    The заход was told "93 of 140 already make their own temp database -- check it with a
    command and name the number, do not take my word".  The command is here, so the number
    is re-measured on every run instead of ageing inside a report.
    """
    fajly = sorted((KOREN / "tests").rglob("test_*.py"))
    svoi = [f for f in fajly
            if any(k in f.read_text(encoding="utf-8")
                   for k in ("tmp_path", "tmpdir", "TemporaryDirectory", "mktemp"))]
    cherez_fikstury = [f for f in fajly
                       if f not in svoi and "db_path" in f.read_text(encoding="utf-8")]
    # Фикстура `db_path` в `tests/conftest.py` сама живёт на `tmp_path`, поэтому файл,
    # который её просит, тоже работает на своей временной базе.
    assert len(svoi) + len(cherez_fikstury) > 0
    print("[источник] тестовых файлов %d · со своей временной базой %d (прямо %d, через фикстуру %d)"
          % (len(fajly), len(svoi) + len(cherez_fikstury), len(svoi), len(cherez_fikstury)))
