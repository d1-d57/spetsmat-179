"""The screens, driven through the real dispatcher.

``dp.feed_raw_update`` with a recording session: every assertion below is about what the
bot TRIED to send, which is the only thing observable without a Telegram server.  The
services, the middleware and the router wiring are production's -- nothing is faked except
the transport.
"""

from __future__ import annotations

import config
from bot.keyboards.views import ViewDebts, ViewLists, ViewSheet, ViewTable, ViewYear
from tests.views.conftest import feed_callback, feed_message

DAYS = ("2026-09-08", "2026-09-15", "2026-09-22")


def _own_tg(bound_students, index: int = 0):
    return bound_students[index][1]


# ------------------------------------------------------------------ the wiring itself

def test_the_view_router_is_included_before_the_catch_all(dispatcher):
    """A view button must not be answered «экран устарел».

    ``marking``'s catch-all claims every callback nobody above it matched, so the include
    ORDER in ``bot/app.build`` is the whole difference between a working screen and one
    that tells its reader it is out of date.  Asserted on the dispatcher rather than by
    reading the source: the source can be right and the build wrong.
    """
    names = [router.name for router in dispatcher.sub_routers]
    assert "views" in names, "the viewing screens are not wired in at all"
    assert names.index("views") < names.index("stale-callbacks")


# --------------------------------------------------------------------- student screens

def test_a_student_opens_the_bot_and_sees_the_whole_year(
    dispatcher, bound_students, recorder, seeded_catalogue
):
    """First of September, and it is what P2 loaded fifteen thousand events for."""
    feed_message(dispatcher, bot=dispatcher.workflow_data["bot"],
                 from_id=_own_tg(bound_students), text="/god")

    sent = [text for text in recorder.texts() if text]
    assert sent, "the student got nothing back"
    year = sent[-1]
    for sheet in seeded_catalogue.sheets():
        assert "Листок %s ·" % sheet.number in year
    assert year.count("сдано") == 18


def test_the_year_shows_the_students_own_marks_and_not_a_neighbours(
    dispatcher, bound_students, recorder, seeded_catalogue, mark_on
):
    mine, theirs = bound_students[0], bound_students[1]
    sheets = sorted(seeded_catalogue.sheets(), key=lambda s: s.ord)
    problems = seeded_catalogue.problems_of_sheet(sheets[0].id)
    for problem in problems[:3]:
        mark_on(theirs[0], problem.id, DAYS[0])
    mark_on(mine[0], problems[0].id, DAYS[0])

    feed_message(dispatcher, bot=dispatcher.workflow_data["bot"],
                 from_id=mine[1], text="/god")
    year = [text for text in recorder.texts() if text][-1]
    assert "Листок %s · сдано 1 из %d" % (sheets[0].number, len(problems)) in year


def test_the_debt_screen_is_short_and_leaves_the_door_open(
    dispatcher, bound_students, recorder
):
    """One boundary named, everything older in one line, and the way back said out loud."""
    feed_message(dispatcher, bot=dispatcher.workflow_data["bot"],
                 from_id=_own_tg(bound_students), text="/dolgi")

    text = [t for t in recorder.texts() if t][-1]
    assert "обязательные из листка" in text
    assert "с более ранних листков" in text
    assert "прийти и сдать можно в любой момент" in text
    assert len(text.splitlines()) <= 5, (
        "the debt screen is short by construction; it rendered:\n%s" % text
    )


def test_a_student_walks_year_to_sheet_and_back(
    dispatcher, bound_students, recorder, seeded_catalogue, mark_on
):
    student_id, tg_id = bound_students[0]
    sheet = sorted(seeded_catalogue.sheets(), key=lambda s: s.ord)[0]
    problems = seeded_catalogue.problems_of_sheet(sheet.id)
    mark_on(student_id, problems[0].id, DAYS[0])

    bot = dispatcher.workflow_data["bot"]
    feed_callback(dispatcher, bot=bot, from_id=tg_id,
                  data=ViewSheet(student_id=student_id, sheet_id=sheet.id).pack())
    sheet_text = [t for t in recorder.texts() if t][-1]
    assert "%s — принята" % problems[0].label in sheet_text
    assert "%s — —" % problems[1].label in sheet_text

    recorder.reset()
    feed_callback(dispatcher, bot=bot, from_id=tg_id, update_id=3,
                  data=ViewYear(student_id=student_id).pack())
    assert "ваш год" in [t for t in recorder.texts() if t][-1]


# --------------------------------------------------------------------- teacher screens

def test_the_teacher_gets_the_two_lists_first_and_the_table_second(
    dispatcher, teacher_tg_id, recorder, seeded_catalogue, mark_on
):
    """Defect no. 7 of the sheet system is fixed by the silent list, not by the table.

    «Проверяющие зачастую уделяют больше времени сильным учащимся»: a table of everybody
    against everything shows the teacher what the teacher already sees.  So the lists are
    the first screen and the table is one tap behind them.
    """
    students = seeded_catalogue.students()
    sheets = sorted(seeded_catalogue.sheets(), key=lambda s: s.ord)
    problems = seeded_catalogue.problems_of_sheet(sheets[0].id)
    for index, day in enumerate(DAYS):
        mark_on(students[0].id, problems[index].id, day)

    bot = dispatcher.workflow_data["bot"]
    feed_message(dispatcher, bot=bot, from_id=teacher_tg_id, text="/spiski")
    first = [t for t in recorder.texts() if t][-1]
    assert first.index("Не сдавал ничего") < first.index("Задачи, которые не взял")
    assert "всего 55 из 56" in first
    assert "<pre>" not in first, "the table is not the first screen"

    recorder.reset()
    feed_callback(dispatcher, bot=bot, from_id=teacher_tg_id,
                  data=ViewTable(sheet_id=sheets[-1].id).pack())
    table = [t for t in recorder.texts() if t and t.startswith("<pre>")]
    assert table, "tapping «Таблица листка» produced no table"
    assert "Листок %s · учеников 56" % sheets[-1].number in table[-1]


def test_the_silent_list_uses_the_threshold_from_config(
    dispatcher, teacher_tg_id, recorder, seeded_catalogue, mark_on
):
    students = seeded_catalogue.students()
    problems = seeded_catalogue.problems_of_sheet(seeded_catalogue.sheets()[0].id)
    for index, day in enumerate(DAYS):
        mark_on(students[0].id, problems[index].id, day)

    feed_message(dispatcher, bot=dispatcher.workflow_data["bot"],
                 from_id=teacher_tg_id, text="/spiski")
    text = [t for t in recorder.texts() if t][-1]
    assert "Не сдавал ничего %d занятия подряд" % config.SILENT_SESSIONS in text
    assert "порог %d" % config.GRAVEYARD_THRESHOLD in text


def test_the_teacher_returns_from_the_table_to_the_lists(
    dispatcher, teacher_tg_id, recorder, seeded_catalogue
):
    bot = dispatcher.workflow_data["bot"]
    sheet = sorted(seeded_catalogue.sheets(), key=lambda s: s.ord)[-1]
    feed_callback(dispatcher, bot=bot, from_id=teacher_tg_id,
                  data=ViewTable(sheet_id=sheet.id).pack())
    recorder.reset()
    feed_callback(dispatcher, bot=bot, from_id=teacher_tg_id, update_id=3,
                  data=ViewLists().pack())
    assert "Задачи, которые не взял почти никто" in [t for t in recorder.texts() if t][-1]


# ------------------------------------------------------------------------- edge cases

def test_a_button_naming_a_sheet_that_is_gone_says_so_instead_of_raising(
    dispatcher, bound_students, recorder
):
    student_id, tg_id = bound_students[0]
    feed_callback(dispatcher, bot=dispatcher.workflow_data["bot"], from_id=tg_id,
                  data=ViewSheet(student_id=student_id, sheet_id=10 ** 6).pack())
    # 🔴 СРАВНЕНИЕ ЦЕЛОЙ СТРОКИ ЗАПРЕЩАЕТ ОТКАЗУ ПОДСКАЗЫВАТЬ, ЧТО ДЕЛАТЬ ДАЛЬШЕ.
    # P18 дописала «Откройте свой год заново: /god.» — ровно то, чего требовало её
    # задание, — и тест упал на равенстве. Проверяем вхождение: суть в том, ЧТО
    # сказано, а не в том, что после этого не сказано больше ничего.
    assert any("Такого листка нет." in a for a in recorder.alerts()), recorder.alerts()


def test_an_id_wider_than_the_store_is_refused_before_it_reaches_a_query(
    dispatcher, bound_students, recorder
):
    """A twenty-digit id fits 64 bytes, unpacks cleanly and explodes at SQLite.

    It has to be refused BEFORE anything queries, or the traceback lands after the handler
    started and before it answered -- a spinner that never stops.
    """
    tg_id = _own_tg(bound_students)
    feed_callback(dispatcher, bot=dispatcher.workflow_data["bot"], from_id=tg_id,
                  data="vy:99999999999999999999")
    assert any("Экран устарел" in alert for alert in recorder.alerts())


def test_no_screen_of_this_position_writes_anything_to_the_journal(
    dispatcher, bound_students, teacher_tg_id, recorder, seeded_journal, seeded_catalogue
):
    """These are the screens you LOOK at.  Not one of them may append an event."""
    student_id, tg_id = bound_students[0]
    sheet = sorted(seeded_catalogue.sheets(), key=lambda s: s.ord)[0]
    bot = dispatcher.workflow_data["bot"]
    before = len(seeded_journal.events())

    feed_message(dispatcher, bot=bot, from_id=tg_id, text="/god")
    feed_message(dispatcher, bot=bot, from_id=tg_id, text="/dolgi")
    feed_callback(dispatcher, bot=bot, from_id=tg_id, update_id=3,
                  data=ViewSheet(student_id=student_id, sheet_id=sheet.id).pack())
    feed_callback(dispatcher, bot=bot, from_id=tg_id, update_id=4,
                  data=ViewDebts(student_id=student_id).pack())
    feed_message(dispatcher, bot=bot, from_id=teacher_tg_id, text="/spiski", update_id=5)
    feed_callback(dispatcher, bot=bot, from_id=teacher_tg_id, update_id=6,
                  data=ViewTable(sheet_id=sheet.id).pack())

    assert len(seeded_journal.events()) == before
