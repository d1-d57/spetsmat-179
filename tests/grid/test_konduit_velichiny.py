"""The four величины on the page itself: the markup, and not only the arithmetic.

WHAT THIS FILE CATCHES THAT `test_statistiki.py` CANNOT.  The projections there are pure
and are already right; every way this feature breaks after that is in the wiring:

  * the counter computed over SOMEBODY ELSE'S cut -- a whole-year number printed on the
    row of a листок table, which looks entirely plausible;
  * the row glows, but the mark «свой ребёнок» has DISAPPEARED, because the two row
    classes displaced each other instead of adding up;
  * «сколько сдало» landed in the header of the wrong column -- and there are twenty-one
    columns under one header, so an off-by-one reads as a coincidence;
  * the initials of the принимающий arrived as a column, which the owner explicitly did
    not want.

Each is judged on the RENDER of the section, built by the same call the site builds it
with -- `konduit.razdel(kt)` -- over a small world from `seed_world`.
"""

from __future__ import annotations

import re

import pytest

from core.models import CellState
from tests.conftest import seed_world
from veb.obshchee.karkas import Kontekst
from veb.razdely import konduit


#: One листок: two обязательные, one письменная (obligatory as well), a звезда, an обычная.
LISTOK = ("обязательная", "обязательная", "письменная", "звезда", "обычная")


#: Columns the LIVE база carries and `migrations/` does not create: `teachers.gruppa`,
#: `teachers.kabinet`, `teachers.aktiven`, `students.gruppa`.  Found by this заход through
#: a direct comparison: the live база has them (and `veb/razdely/lichnaya.kabinet_na_datu`,
#: written by a neighbouring заход, already leans on them), while a database built from all
#: ten migrations has not one of them.  They are added here so the test judges THE schema
#: the site actually runs on; the fix belongs in `migrations/`, which is not this заход's
#: zone, and the question is named in `## ВОПРОСЫ`.
ZHIVYE_KOLONKI = (
    "alter table teachers add column kabinet text",
    "alter table teachers add column aktiven integer not null default 1",
    "alter table teachers add column gruppa text",
    "alter table students add column gruppa text",
)


@pytest.fixture
def mir(connection):
    """Five pupils, one листок, not a single mark: the marks are written by the test."""
    for zapros in ZHIVYE_KOLONKI:
        connection.execute(zapros)
    return seed_world(connection, students=5, sheets=(LISTOK,))


@pytest.fixture
def uchebnyj_den(monkeypatch):
    """Пятница — не учебный день, и без этой оснастки «мой школьник» не существует.

    🔴 ЭТО НЕ УДОБСТВО, А КРАСНОЕ, КОТОРОЕ УЖЕ СТОЯЛО.  `_moi_deti` спрашивает
    `deti_na_datu(..., segodnya())`, а та на дне без слота отвечает пустым списком
    («не учебный день: постоянных строк не применяется ни одной»,
    `veb/razdely/lichnaya.py:168`).  Значит любой тест про «моих» ЗЕЛЁН по понедельникам
    и четвергам и КРАСЕН в остальные пять дней недели, ничего не сообщая о коде: замер
    11.09 (пятница) — `test_being_mine_and_having_closed…` красный на `"moi"`, при
    целом механизме.  День занятия здесь называется явно, и результат перестаёт зависеть
    от того, когда запустили прогон.
    """
    monkeypatch.setattr(konduit, "segodnya", lambda: "2026-09-14")   # понедельник
    return "2026-09-14"


def kontekst(connection, prepod_id=None) -> Kontekst:
    """A `Kontekst` carrying exactly the fields the кондуит reads.

    Built by hand rather than through `sobrat_kontekst`: that one opens the LIVE database
    of the project by absolute path, and a test that called it would be judging today's
    school data instead of its own world.
    """
    return Kontekst(rezhim="admin", rol="organizator", mogu=frozenset(), c=connection,
                    DNI={}, kabinety_dnya={}, otkuda_kabinet={}, kabinety={}, gruppy={},
                    prep={}, prepod_id=prepod_id)


def otmetit(marking, student_id, problem_id, sostoyanie=CellState.SOLVED):
    marking.set_state(student_id, problem_id, sostoyanie, source="кнопка")


def panel(html: str, imya: str) -> str:
    """One tab of the page: the panels all sit in the DOM at once, hidden by CSS."""
    kusok = re.search(r'<section class="vid" id="n-%s">(.*?)</section>' % re.escape(imya),
                      html, re.S)
    assert kusok, "нет панели n-%s" % imya
    return kusok.group(1)


def schyotchiki(kusok: str) -> list:
    """Every obligatory counter of a panel, top to bottom: `(сдано, всего)` or `None`."""
    out = []
    for m in re.finditer(r'<i class="ob-sch( net)?"[^>]*>(.*?)</i>', kusok, re.S):
        if m.group(1):
            out.append(None)
            continue
        chisla = re.match(r'(\d+)<span class="iz">/(\d+)</span>$', m.group(2))
        assert chisla, "счётчик написан не двумя числами: %r" % m.group(2)
        out.append((int(chisla.group(1)), int(chisla.group(2))))
    return out


# --------------------------------------------- величина 1: обязательные у школьника


def test_the_counter_stands_left_of_every_pupil_on_every_panel(mir, connection, marking):
    """Five pupils, five counters on every panel, and not one more.

    There are three panels: the year overview of the ninth class, the year overview of the
    eighth, and the листок itself.  A counter forgotten on one of them leaves precisely the
    hole this величина was introduced to close.
    """
    otmetit(marking, mir.student_ids[0], mir.problems_by_sheet[mir.sheet_ids[0]][0])
    connection.commit()
    html = konduit.razdel(kontekst(connection))
    for imya in ("vse8", str(mir.sheet_ids[0])):
        assert len(schyotchiki(panel(html, imya))) == 5, "панель %s" % imya


def test_the_counter_counts_obligatory_only_and_counts_pismennaya_among_them(
    mir, connection, marking
):
    zadachi = mir.problems_by_sheet[mir.sheet_ids[0]]
    uchenik = mir.student_ids[0]
    otmetit(marking, uchenik, zadachi[0])          # обязательная
    otmetit(marking, uchenik, zadachi[2])          # письменная -- obligatory too
    otmetit(marking, uchenik, zadachi[3])          # звезда -- never counts at all
    connection.commit()
    schyot = schyotchiki(panel(konduit.razdel(kontekst(connection)),
                               str(mir.sheet_ids[0])))[0]
    assert schyot == (2, 3), "три обязательных на листке, сдано две из них"


def test_a_retracted_obligatory_is_not_counted_as_handed_in(mir, connection, marking):
    """Handed in and not defended is not «сдал» -- on the screen as well as in the journal."""
    zadachi = mir.problems_by_sheet[mir.sheet_ids[0]]
    uchenik = mir.student_ids[0]
    otmetit(marking, uchenik, zadachi[0])
    otmetit(marking, uchenik, zadachi[0], CellState.RETRACTED)
    connection.commit()
    assert schyotchiki(panel(konduit.razdel(kontekst(connection)),
                            str(mir.sheet_ids[0])))[0] == (0, 3)


# ------------------------------------------------------- величина 2: строка светится


def test_no_row_glows_for_having_closed_the_obligatory_problems(
    mir, connection, marking
):
    """The owner's edit of 10.09 (O1), read as the property it is: the row does not glow.

    This test USED to assert the opposite — «светится ровно строка того, кто закрыл
    обязательные» — and it was right until 10.09, when the owner looked at the live page
    and said: «я хочу видеть своих школьников, и я их вижу. А теперь ещё вижу почему-то
    школьников, которые просто всё сдали — это не нужно… Ты сейчас выделяешь всю строчку —
    не надо».  The pupil below closes every obligatory problem of the листок, which is
    exactly the state that used to light his row up.
    """
    zadachi = mir.problems_by_sheet[mir.sheet_ids[0]]
    for zadacha in (zadachi[0], zadachi[1], zadachi[2]):
        otmetit(marking, mir.student_ids[0], zadacha)
    # The second pupil took a ЗВЕЗДА and an обычная -- not one obligatory problem.
    otmetit(marking, mir.student_ids[1], zadachi[3])
    otmetit(marking, mir.student_ids[1], zadachi[4])
    connection.commit()
    kusok = panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0]))
    stroki = re.findall(r'<tr( class="[^"]*")?><td class="kto">', kusok)
    assert stroki, "строки школьников вообще нарисованы"
    assert not [k for k in stroki if k], "ни одна строка не несёт класса вовсе"
    assert "gotov" not in kusok, "класс подсветки не остался нигде в разметке"


def test_a_listok_with_no_obligatory_problems_lights_up_nobody(connection, marking):
    """`1д`-`4д` on the live база are exactly like this: 99 problems and no obligatory one."""
    for zapros in ZHIVYE_KOLONKI:
        connection.execute(zapros)
    mir = seed_world(connection, students=3, sheets=(("звезда", "обычная"),))
    connection.commit()
    kusok = panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0]))
    assert "gotov" not in kusok
    assert schyotchiki(kusok) == [None, None, None], "листок без обязательных пишет точку"


def test_the_row_carries_the_one_priznak_of_whose_child_it_is_and_no_other(
    mir, connection, marking, uchebnyj_den
):
    """One признак, one носитель (O1, and the owner's канон «нельзя смешивать», Q4).

    The pupil below is BOTH the teacher's own child AND has closed every obligatory
    problem — the case where the two marks used to be added onto one row (this test
    asserted that sum until 10.09).  Now the row says «мой» and says nothing else; the
    second fact is drawn in its own column and is checked there.
    """
    zadachi = mir.problems_by_sheet[mir.sheet_ids[0]]
    for zadacha in zadachi[:3]:
        otmetit(marking, mir.student_ids[0], zadacha)
    prepod = mir.teacher_ids[0]
    # 🔴 СТРОКА НА ОБА СЛОТА, И ЭТО НЕ ИЗБЫТОЧНОСТЬ. С 10.09 «мой» считается ПО ДНЮ:
    # кондуит спрашивает ту же службу, что распределение (требование владельца —
    # «изменение в текущем расписании на сегодня не обновляет кабинет и вкладку в
    # кондуите»).
    for slot in (1, 2):
        connection.execute(
            "insert into enrollment (student_id, teacher_id, room, slot, valid_from) "
            "values (?, ?, ?, ?, ?)",
            (mir.student_ids[0], prepod, "303", slot, "2020-01-01"))
    connection.commit()
    kusok = panel(konduit.razdel(kontekst(connection, prepod_id=prepod)),
                  str(mir.sheet_ids[0]))
    pervaya = re.search(r'<tr class="([^"]*)"><td class="kto">', kusok).group(1)
    assert pervaya.split() == ["moi"], pervaya


# ------------------------------------------------- величина 3: сколько сдало задачу


def shapka(kusok: str) -> list:
    """The columns of a листок, left to right: `(label, сдало, closed by the class)`."""
    return [(m.group("label"), int(m.group("n")), bool(m.group("zakr")))
            for m in re.finditer(
                r'<th class="zn">(?P<label>.*?)(?:<i class="pm[^>]*>.</i>)?'
                r'<b class="sdalo(?P<zakr> zakr)?"[^>]*>(?P<n>\d+)</b></th>', kusok)]


def test_every_column_carries_how_many_took_it_and_the_number_is_per_column(
    mir, connection, marking
):
    """The number stands over ITS OWN column.

    An off-by-one is the most plausible way this величина breaks: one header over
    twenty-one columns, every number present, and not one of them about its own problem.
    So the world is built on purpose so that all five numbers are DIFFERENT.
    """
    zadachi = mir.problems_by_sheet[mir.sheet_ids[0]]
    for nomer, zadacha in enumerate(zadachi):        # 0, 1, 2, 3 and 4 solvers
        for uchenik in mir.student_ids[:nomer]:
            otmetit(marking, uchenik, zadacha)
    connection.commit()
    stolbcy = shapka(panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0])))
    assert [n for _label, n, _z in stolbcy] == [0, 1, 2, 3, 4]
    assert [label for label, _n, _z in stolbcy] == ["1.1", "1.2", "1.3", "1.4", "1.5"]


def test_closed_by_the_class_means_MORE_than_three_took_it(mir, connection, marking):
    """Exactly three is not closed yet; four is closed.  The words of the owner, literally."""
    zadachi = mir.problems_by_sheet[mir.sheet_ids[0]]
    for uchenik in mir.student_ids[:3]:
        otmetit(marking, uchenik, zadachi[0])
    for uchenik in mir.student_ids[:4]:
        otmetit(marking, uchenik, zadachi[1])
    connection.commit()
    stolbcy = shapka(panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0])))
    assert (stolbcy[0][1], stolbcy[0][2]) == (3, False), "трое — ещё не закрыта"
    assert (stolbcy[1][1], stolbcy[1][2]) == (4, True), "четверо — закрыта классом"


def test_a_retracted_hand_in_does_not_count_towards_closing_a_problem(
    mir, connection, marking
):
    """Exactly the case the threshold exists for: handed in and never defended."""
    zadacha = mir.problems_by_sheet[mir.sheet_ids[0]][0]
    for uchenik in mir.student_ids[:5]:
        otmetit(marking, uchenik, zadacha)
    for uchenik in mir.student_ids[:4]:
        otmetit(marking, uchenik, zadacha, CellState.RETRACTED)
    connection.commit()
    stolbcy = shapka(panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0])))
    assert (stolbcy[0][1], stolbcy[0][2]) == (1, False)


# --------------------------------------------- величина 4: инициалы принимающего


PRIN = re.compile(r'<i class="prin( net)?" title="принимающий:? ?([^"]*)">([^<]*)</i>')


def zapisat(connection, student_id, teacher_id, slot, room="303",
            ot="2020-01-01", do="9999-12-31"):
    connection.execute(
        "insert into enrollment (student_id, teacher_id, room, slot, valid_from, valid_to) "
        "values (?, ?, ?, ?, ?, ?)", (student_id, teacher_id, room, slot, ot, do))


def test_the_initials_stand_beside_the_surname_and_not_in_a_column_of_their_own(
    mir, connection
):
    """The decision of the owner, 09.09: «не колонкой».

    Judged by shape rather than by text: a column of принимающие would pass any check
    on wording.  The header of a листок carries the surname, the счётчик обязательных
    (its own column since the owner's edit of 10.09, H4.4) and one column per problem —
    and NOTHING else.

    🔴 THE COUNT IS SPELLED OUT AS A SUM, NOT WRITTEN AS A NUMBER.  When the счётчик
    got its column this assertion went red, and the honest question at that moment was
    "which column appeared" — a bare `== 7` cannot be asked that.  Naming the two
    non-problem columns keeps the test able to say what it is defending.
    """
    zapisat(connection, mir.student_ids[0], mir.teacher_ids[0], 1)
    connection.commit()
    kusok = panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0]))
    FAMILIA, SCHYOTCHIK = 1, 1
    assert len(re.findall(r"<th[ >]", kusok)) == FAMILIA + SCHYOTCHIK + len(LISTOK)
    # The one column that is not a problem and not the surname is the счётчик, named
    # by its class: a column of принимающие would be an <th> of some other kind.
    assert len(re.findall(r'<th class="sch"', kusok)) == SCHYOTCHIK
    assert "прин" not in re.search(r"<thead>(.*?)</thead>", kusok, re.S).group(1)
    # And the initials themselves live inside the surname cell.
    yacheyka = re.search(r'<td class="kto">(.*?)</td>', kusok, re.S).group(1)
    assert '<i class="prin"' in yacheyka


def test_the_hover_carries_the_name_the_group_and_the_room(mir, connection):
    connection.execute("update teachers set name = ?, gruppa = ? where id = ?",
                       ("Андрей Рябичев", "Д", mir.teacher_ids[0]))
    zapisat(connection, mir.student_ids[0], mir.teacher_ids[0], 1, room="302")
    connection.commit()
    kusok = panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0]))
    net, title, txt = PRIN.findall(kusok)[0]
    assert txt == "А.Р."
    assert title == "Андрей Рябичев · группа Д · кабинет 302"
    assert not net


def test_a_pupil_with_no_open_row_gets_a_dash_and_not_a_blank(mir, connection):
    """A blank reads as «forgot to draw it»; a dash says the question was asked and has no answer."""
    connection.commit()
    kusok = panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0]))
    nayden = PRIN.findall(kusok)
    assert len(nayden) == 5
    assert all(net and txt == "—" for net, _title, txt in nayden)


def test_a_row_that_is_already_closed_does_not_name_a_принимающий(mir, connection):
    """The interval is half-open: a row closed yesterday does not answer today.

    `valid_to` is the day FROM WHICH the row no longer holds, and `<=` in place of `<`
    would show yesterday's принимающий for one more day.
    """
    zapisat(connection, mir.student_ids[0], mir.teacher_ids[0], 1,
            ot="2020-01-01", do="2020-06-01")
    connection.commit()
    kusok = panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0]))
    assert PRIN.findall(kusok)[0][2] == "—"


def test_two_different_принимающих_are_both_named_with_their_days(mir, connection):
    """Different people on Monday and on Thursday: the hover must say who is there when."""
    connection.execute("update teachers set name = ?, gruppa = ? where id = ?",
                       ("Андрей Рябичев", "Д", mir.teacher_ids[0]))
    connection.execute("update teachers set name = ?, gruppa = ? where id = ?",
                       ("Ваня Яковлев", "В", mir.teacher_ids[1]))
    zapisat(connection, mir.student_ids[0], mir.teacher_ids[0], 1, room="302")
    zapisat(connection, mir.student_ids[0], mir.teacher_ids[1], 2, room="303")
    connection.commit()
    kusok = panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0]))
    _net, title, txt = PRIN.findall(kusok)[0]
    assert txt == "А.Р./В.Я."
    assert title == ("пн — Андрей Рябичев · группа Д · кабинет 302; "
                     "чт — Ваня Яковлев · группа В · кабинет 303")


def test_one_принимающий_in_both_slots_is_one_person_and_one_pair_of_initials(
    mir, connection
):
    connection.execute("update teachers set name = ?, gruppa = ? where id = ?",
                       ("Андрей Рябичев", "Д", mir.teacher_ids[0]))
    zapisat(connection, mir.student_ids[0], mir.teacher_ids[0], 1, room="302")
    zapisat(connection, mir.student_ids[0], mir.teacher_ids[0], 2, room="302")
    connection.commit()
    kusok = panel(konduit.razdel(kontekst(connection)), str(mir.sheet_ids[0]))
    _net, title, txt = PRIN.findall(kusok)[0]
    assert txt == "А.Р.", "один человек — одни инициалы, а не «А.Р./А.Р.»"
    assert title.startswith("Андрей Рябичев"), "дня недели тут не нужно: он один и тот же"


def test_a_one_word_name_keeps_its_word():
    """«Надя» and «Наталья Амбург» are two live принимающие, and «Н.» would merge them into one."""
    assert konduit.initsialy("Надя") == "Надя"
    assert konduit.initsialy("Наталья Амбург") == "Н.А."


# --------------------------------------------------------- величина 5: гробарий


def grobarij(html: str) -> str:
    return panel(html, "grob")


def devyatyj(connection, listki):
    """A world whose листки the кондуит counts as the NINTH class.

    The кондуит takes the class from `veb.razdely.listki.L9` -- «the number starts with 16»
    -- and there is no other mark of it in the база at all.  So the листки here are named
    `16…`: the test has to ask in exactly the way the page asks, or it would be judging the
    eighth-class tab bar, which carries no гробарий by this заход's own decision.
    """
    for zapros in ZHIVYE_KOLONKI:
        connection.execute(zapros)
    mir = seed_world(connection, students=5, sheets=listki)
    for poryadok, sheet_id in enumerate(mir.sheet_ids):
        connection.execute(
            "update sheets set number = ?, issued_at = ? where id = ?",
            ("16%s" % "ABCD"[poryadok], "2026-09-%02d" % (3 + poryadok * 7), sheet_id))
    return mir


def test_with_one_listok_issued_the_grobarij_says_it_is_empty_and_why(connection):
    """The state of the live база today, reproduced: exactly one листок has been issued."""
    devyatyj(connection, (LISTOK,))
    connection.commit()
    kusok = grobarij(konduit.razdel(kontekst(connection)))
    assert "Гробарий пуст" in kusok
    assert "исторических листков пока нет" in kusok
    assert "наполнится сам" in kusok, "пустая вкладка обязана сказать, чего она ждёт"
    assert "меньше 3" in kusok, "правило написано во вкладке всегда, а не только когда есть строки"


def test_the_previous_listok_falls_in_by_itself_when_the_next_one_is_issued(
    connection, marking
):
    """🔴 THE CENTRAL CHECK OF THIS ВЕЛИЧИНА.

    The owner: «гробарий наполнится сам в понедельник, когда 16-й листок станет
    историческим».  A tab that is empty because emptiness was written into it looks
    EXACTLY THE SAME today as this one does -- and the difference would show up on Monday,
    in front of a class.  Here the second листок is issued inside the test, and the first
    one has to appear in the гробарий with no edit to the code at all.
    """
    mir = devyatyj(connection, (LISTOK, LISTOK))
    staryj, novyj = mir.sheet_ids
    zadachi = mir.problems_by_sheet[staryj]
    # Four took the first problem: it is past the threshold and stays out.
    for uchenik in mir.student_ids[:4]:
        marking.set_state(uchenik, zadachi[0], CellState.SOLVED, source="кнопка")
    # Two took the second, which is exactly the гробарий case.
    for uchenik in mir.student_ids[:2]:
        marking.set_state(uchenik, zadachi[1], CellState.SOLVED, source="кнопка")
    connection.commit()

    kusok = grobarij(konduit.razdel(kontekst(connection)))
    assert "Гробарий пуст" not in kusok
    zadachi_v_grobarii = re.findall(r'<td class="kto">([^<]*)', kusok)
    assert "1.1" not in zadachi_v_grobarii, "четверо сдали — не гробарий"
    assert "1.2" in zadachi_v_grobarii, "двое сдали — гробарий"
    # Problems of the CURRENT листок never fall in, even when nobody took them.
    assert not any(z.startswith("2.") for z in zadachi_v_grobarii), zadachi_v_grobarii


def test_the_graveyard_names_the_first_solvers_in_order(connection, marking):
    mir = devyatyj(connection, (LISTOK, LISTOK))
    zadacha = mir.problems_by_sheet[mir.sheet_ids[0]][1]
    marking.set_state(mir.student_ids[2], zadacha, CellState.SOLVED,
                      source="кнопка", valid_at="2026-09-03T10:10:00Z")
    marking.set_state(mir.student_ids[0], zadacha, CellState.SOLVED,
                      source="кнопка", valid_at="2026-09-07T11:15:00Z")
    connection.commit()
    kusok = grobarij(konduit.razdel(kontekst(connection)))
    imena = re.findall(r'<i>([^<]*)</i>', kusok)
    assert imena == ["surname-2 name-2", "surname-0 name-0"], "раньше сдал — раньше в списке"


def test_a_problem_nobody_took_says_so_instead_of_showing_an_empty_cell(
    connection, marking
):
    mir = devyatyj(connection, (("обязательная",), ("обязательная",)))
    connection.commit()
    kusok = grobarij(konduit.razdel(kontekst(connection)))
    assert ">никто<" in kusok, "«никто не сдал» — самое сильное, что говорит гробарий"


def test_versions_of_one_listok_do_not_make_each_other_historical(connection):
    """`16A`, `16α` and `16ℵ` are one листок in three strengths and one `issued_at`.

    Comparing by `ord` would declare two of them historical on the day they were issued,
    and the гробарий would open on the problems of the CURRENT листок.  This is the live
    база as it stands today, not a hypothetical.
    """
    for zapros in ZHIVYE_KOLONKI:
        connection.execute(zapros)
    mir = seed_world(connection, students=3, sheets=(LISTOK, LISTOK, LISTOK))
    for nomer, sheet_id in zip(("16A", "16α", "16ℵ"), mir.sheet_ids):
        connection.execute("update sheets set number = ?, issued_at = ? where id = ?",
                           (nomer, "2026-09-03", sheet_id))
    connection.commit()
    assert "Гробарий пуст" in grobarij(konduit.razdel(kontekst(connection)))


def test_a_listok_row_without_problems_does_not_bury_the_current_one(connection):
    """A row for the next листок whose problems are not entered yet is not an issued листок."""
    mir = devyatyj(connection, (LISTOK,))
    connection.execute(
        "insert into sheets (number, title, issued_at, ord) values (?, ?, ?, ?)",
        ("16Z", "следующий, задачи ещё не внесены", "2026-09-14", 99))
    connection.commit()
    assert "Гробарий пуст" in grobarij(konduit.razdel(kontekst(connection)))
