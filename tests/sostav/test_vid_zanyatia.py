"""The lesson screen: the owner's three visual decisions, held by tests rather than care.

Each of the three was said out loud and each is cheap to lose in a later edit — that is
exactly the class of decision ``doc/DIZAJN-ZAKREPLENO.md`` exists for.
"""

from __future__ import annotations

import pytest

from core.services.sostav_na_den import OTSUTSTVUET, PRISUTSTVUET
from veb.razdely import zanyatie

MONDAY = "2026-09-07"
SATURDAY = "2026-09-12"


@pytest.fixture
def mir(connection):
    """One teacher, one child of his, and one child visiting from elsewhere."""
    usual = connection.execute(
        "insert into teachers (name, aka) values ('Елена Мирошниченко', 'ЕМ')").lastrowid
    other = connection.execute(
        "insert into teachers (name, aka) values ('Михаил Шнитке', 'МШ')").lastrowid
    stays = connection.execute(
        "insert into students (surname, name, class, status) "
        "values ('Глебова', 'Елизавета', '9Л', 'active')").lastrowid
    moves = connection.execute(
        "insert into students (surname, name, class, status) "
        "values ('Юсуфов', 'Арон', '9Л', 'active')").lastrowid
    for student in (stays, moves):
        connection.execute(
            "insert into enrollment (student_id, teacher_id, room, slot, valid_from, "
            "valid_to) values (?, ?, '307', 1, '2026-09-01', '9999-12-31')",
            (student, usual))
    session_id = connection.execute(
        "insert into sessions (held_on, kind) values (?, 'обычное')", (MONDAY,)).lastrowid
    return dict(connection=connection, usual=usual, other=other, stays=stays,
                moves=moves, session_id=session_id)


def test_a_child_who_is_elsewhere_today_carries_the_initials_of_his_usual_teacher(mir):
    """ТЗ §3.3 — and the form is the owner's own, from the sheet he used last year:
    initials on the row, the full name on hover."""
    mir["connection"].execute(
        "insert into attendance (session_id, student_id, teacher_id, status) "
        "values (?, ?, ?, ?)", (mir["session_id"], mir["moves"], mir["other"], PRISUTSTVUET))

    html = zanyatie.stranica(mir["connection"], MONDAY)

    assert "обычно у ЕМ" in html, "the initials go on the row"
    assert 'title="обычно у Елена Мирошниченко"' in html, "the full name goes on hover"
    # And the child who did not move carries no hint at all: a hint on everybody is noise.
    assert html.count("обычно у") == 2  # once in the visible text, once in the title


def test_an_absent_child_stays_on_his_teachers_list_and_is_not_red(mir):
    """Owner: «может быть, в списке у преподавателя должно быть таким вот серым»."""
    mir["connection"].execute(
        "insert into attendance (session_id, student_id, teacher_id, status) "
        "values (?, ?, NULL, ?)", (mir["session_id"], mir["moves"], OTSUTSTVUET))

    html = zanyatie.stranica(mir["connection"], MONDAY)

    assert "Юсуфов Арон" in html, "an absent child must not vanish from the screen"
    assert '<li class="chel net">' in html, "he is grey"
    assert "krasn" not in html.split('<div class="setka">')[1], "and he is NOT red"


def test_the_standing_arrangement_is_one_click_away_and_named_for_what_it_is(mir):
    html = zanyatie.stranica(mir["connection"], MONDAY)
    assert 'href="/raspredelenie/postoyannoe"' in html
    assert "Постоянное распределение" in html


def test_a_day_without_a_lesson_says_so_instead_of_showing_an_empty_school(mir):
    """An empty grid and «сегодня занятия нет» look identical, and only one is the truth."""
    html = zanyatie.stranica(mir["connection"], SATURDAY)
    assert "не день занятия" in html
    assert '<div class="setka">' not in html


# ---------------------------------------------------------------- the separation tool


def test_the_separation_tool_refuses_to_guess_an_absence(tmp_path, connection, mir):
    """`check_tool_contract.py` asks: what proves this tool rejects a bad input?  This.

    The tool's one irreducible ambiguity is «исчез из состава» — absent, or genuinely
    gone.  It must stop and name the child rather than pick one, because picking one
    writes a fact nobody stated into the base a school works on.
    """
    import sqlite3
    import subprocess
    import sys
    from pathlib import Path

    koren = Path(__file__).resolve().parents[2]
    utro = tmp_path / "utro.db"
    seychas = tmp_path / "seychas.db"
    # Two copies of the same world; in the later one the child's standing row is closed
    # and nothing replaces it — exactly the shape 2026-09-07 produced.
    # 🔴 Каждое соединение ЗАКРЫВАЕТСЯ явно. `with sqlite3.connect(...)` закрывает
    # транзакцию, а не файл: открытая копия остаётся в режиме WAL, и `mode=ro` на ней
    # падает с «unable to open database file» — тем самым отказом, который в этом тесте
    # неотличим от проверяемого.
    for target in (utro, seychas):
        connection.commit()
        out = sqlite3.connect(target)
        connection.backup(out)
        out.execute("pragma journal_mode = delete")
        out.commit()
        out.close()
    out = sqlite3.connect(seychas)
    out.execute("update enrollment set valid_to = ? where student_id = ?",
                (MONDAY, mir["stays"]))
    out.commit()
    out.close()

    run = subprocess.run(
        [sys.executable, "tools/sloi_zanyatia.py", "razdelit",
         "--baza", str(seychas), "--utro", str(utro), "--den", MONDAY],
        cwd=koren, capture_output=True, text=True)

    assert run.returncode == 2, run.stdout + run.stderr
    assert "ОТКАЗ" in run.stderr
    assert "--otsutstvuet %d" % mir["stays"] in run.stderr, \
        "the refusal must name the flag AND the child, or it is a dead end"
