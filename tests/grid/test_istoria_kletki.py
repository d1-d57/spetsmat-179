"""The date rule, the test-click filter and the feed of one cell.

THE THREE QUESTIONS THIS FILE ANSWERS, and they are the owner's own three:

  * which lesson a tick belongs to when it was made on Friday (09.09: «бывает,
    преподаватель забыл, и в конце четверти я пришёл к человеку… это тогда по сути
    постфактум ставится»);
  * whether a plus put on and taken off inside a minute counts (09.09: «я нажал и сразу
    второй раз нажал, чтобы убрать»);
  * what the cell can tell about itself (09.09: «зажатие состояния клеточки должно дать
    нам возможность посмотреть всю историю»).

🔴 EVERY TIME HERE IS WRITTEN IN MOSCOW AND CONVERTED, never written as UTC and hoped
about.  The timetable is in Moscow (Monday 14:15, Thursday 13:10), the storage is in UTC,
and the three-hour gap is exactly wide enough to move a 13:10 lesson to the previous day
if the test does the arithmetic in its head.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

import config
from core.isotime import parse_iso, to_iso
from core.models import CellState
from core.services import history
from core.services.sostav_na_den import KONEC_ZANYATIA, NACHALO_ZANYATIA, SLOTY_ZANYATIJ

MSK = ZoneInfo(config.TZ_DISPLAY)

#: A known week of the live season: Monday 2026-09-07 … Thursday 2026-09-10.
PONEDELNIK = "2026-09-07"
CHETVERG = "2026-09-10"


def msk(den: str, chas: int, minuta: int = 0) -> datetime:
    god, mesyac, chislo = (int(x) for x in den.split("-"))
    return datetime(god, mesyac, chislo, chas, minuta, tzinfo=MSK)


# ------------------------------------------------------- the timetable has one home


def test_the_timetable_has_a_start_for_every_day_it_has_an_end_for():
    """Half a timetable is how ``ops/raspisanie.py`` came to disagree with the school."""
    assert set(NACHALO_ZANYATIA) == set(KONEC_ZANYATIA) == set(SLOTY_ZANYATIJ)
    for den, nachalo in NACHALO_ZANYATIA.items():
        assert nachalo < KONEC_ZANYATIA[den], (
            "занятие %d начинается не раньше, чем кончается" % den)


# ------------------------------------------------------------------- the date rule


@pytest.mark.parametrize("chas,minuta,ozhidaem,pochemu", [
    (13, 30, CHETVERG, "во время занятия — это оно"),
    (14, 0, CHETVERG, "через час после начала, занятие ещё идёт"),
    (16, 0, CHETVERG, "через час после конца — всё ещё то же занятие"),
])
def test_a_tick_made_on_thursday_belongs_to_thursday(chas, minuta, ozhidaem, pochemu):
    assert history.zanyatie_dlya(msk(CHETVERG, chas, minuta)).isoformat() == ozhidaem, pochemu


@pytest.mark.parametrize("den,chas,pochemu", [
    (CHETVERG, 23, "поздний вечер четверга"),
    ("2026-09-11", 12, "пятница"),
    ("2026-09-12", 10, "суббота"),
    ("2026-09-13", 20, "воскресенье"),
    ("2026-09-14", 9, "понедельник ДО начала: занятие ещё не началось"),
    ("2026-09-14", 14, "понедельник в 14:00 — до 14:15, значит всё ещё четверг"),
])
def test_everything_after_thursday_and_before_monday_starts_is_still_thursday(den, chas, pochemu):
    """The owner's rule word for word: «поставил в пятницу, субботу или в понедельник до
    начала — всё равно четверг»."""
    assert history.zanyatie_dlya(msk(den, chas)).isoformat() == CHETVERG, pochemu


def test_monday_becomes_the_lesson_the_moment_it_starts():
    nachalo = NACHALO_ZANYATIA[1]
    minutoj_ranshe = msk("2026-09-14", nachalo[0], nachalo[1]) - timedelta(minutes=1)
    assert history.zanyatie_dlya(minutoj_ranshe).isoformat() == CHETVERG
    assert history.zanyatie_dlya(msk("2026-09-14", *nachalo)).isoformat() == "2026-09-14"


def test_the_rule_reads_the_instant_in_moscow_and_not_in_utc():
    """13:10 MSK is 10:10 UTC.  A rule that compared UTC wall-clock to a Moscow timetable
    would put every Thursday afternoon tick on the previous Monday, and would be right
    about it for three hours a day."""
    mig = msk(CHETVERG, 13, 30)
    assert history.zanyatie_dlya(mig.astimezone(ZoneInfo("UTC"))) == history.zanyatie_dlya(mig)
    assert history.zanyatie_po_iso(to_iso(mig)) == CHETVERG


def test_a_naive_datetime_is_refused_rather_than_assumed_to_be_anything():
    with pytest.raises(ValueError):
        history.zanyatie_dlya(datetime(2026, 9, 10, 13, 30))


def test_the_stored_start_of_a_lesson_lands_inside_that_day_in_both_zones():
    """Midnight would not: ``2026-09-10T00:00`` in Moscow is the 9th in UTC, and the
    override column stores UTC."""
    zapis = history.nachalo_zanyatia_iso(CHETVERG)
    assert zapis.startswith(CHETVERG), zapis
    assert history.zanyatie_po_iso(zapis) == CHETVERG


def test_a_day_with_no_lesson_cannot_be_named_as_one():
    with pytest.raises(ValueError):
        history.nachalo_zanyatia_iso("2026-09-11")      # пятница


# ------------------------------------------------------------- the test-click filter


def _para(marking, world, clock, *, razryv_sek: int):
    """Put a plus on and take it off ``razryv_sek`` seconds later."""
    student, problem = world.student_ids[0], world.problem_ids[0]
    marking.give(student, problem, source="кнопка", teacher_id=world.teacher_ids[0])
    clock.tick(razryv_sek)
    marking.erratum(student, problem, source="кнопка", teacher_id=world.teacher_ids[0])
    return student, problem


def test_on_and_off_inside_the_minute_marks_both_halves_and_deletes_neither(
        marking, journal, world, clock):
    student, problem = _para(marking, world, clock, razryv_sek=10)

    sobytia = journal.events([student], [problem])
    assert len(sobytia) == 2, "журнал append-only: отсев не имеет права ничего стирать"
    assert history.tehnicheskie(sobytia) == {s.id for s in sobytia}
    assert history.schyot_sobytij(sobytia) == 0


def test_two_hours_later_is_a_real_correction_and_counts(marking, journal, world, clock):
    student, problem = _para(marking, world, clock, razryv_sek=2 * 60 * 60)

    sobytia = journal.events([student], [problem])
    assert history.tehnicheskie(sobytia) == set()
    assert history.schyot_sobytij(sobytia) == 2


def test_the_threshold_is_the_owners_sixty_seconds_and_is_half_open(
        marking, journal, world, clock):
    """59 s is a test click, 60 s is not.  The boundary is asserted because "under a
    minute" and "up to and including a minute" differ by exactly the case a person
    types when they reproduce the bug."""
    assert history.TEHNICHESKOE_OKNO_SEK == 60
    student, problem = _para(marking, world, clock, razryv_sek=59)
    assert history.tehnicheskie(journal.events([student], [problem]))

    vtoraya, zadacha = world.student_ids[1], world.problem_ids[0]
    marking.give(vtoraya, zadacha, source="кнопка")
    clock.tick(60)
    marking.erratum(vtoraya, zadacha, source="кнопка")
    assert history.tehnicheskie(journal.events([vtoraya], [zadacha])) == set()


def test_the_filter_reads_recorded_at_and_not_valid_at(marking, journal, world, clock):
    """A mark deliberately back-dated a week is not a test click, and a test click that
    carries yesterday's ``valid_at`` is still one.  The finger's speed lives in
    ``recorded_at``."""
    student, problem = world.student_ids[2], world.problem_ids[1]
    davno = to_iso(parse_iso(clock.now_iso()) - timedelta(days=7))
    marking.give(student, problem, source="кнопка", valid_at=davno)
    clock.tick(5)
    marking.erratum(student, problem, source="кнопка", valid_at=davno)

    sobytia = journal.events([student], [problem])
    assert {s.valid_at for s in sobytia} == {davno}
    assert history.tehnicheskie(sobytia) == {s.id for s in sobytia}, (
        "пять секунд между нажатиями — тест, какую бы дату им ни проставили")


def test_the_channel_named_by_the_filter_is_one_the_schema_allows():
    assert history.ISTOCHNIK_NAZHATIYA in config.MARK_SOURCES


def test_an_imported_retraction_is_never_a_test_click(marking, journal, world, clock,
                                                      connection):
    """🔴 ЦЕНА ЭТОГО ТЕСТА ИЗМЕРЕНА НА ЖИВОМ ЖУРНАЛЕ, а не придумана.  Импорт записал все
    15 847 своих рядов под ОДНИМ ``recorded_at`` — он один кусок, и честно об этом
    говорит.  Значит каждая из 735 его отмен стоит НОЛЬ секунд после того `assert`,
    который отменяет, и правило, смотрящее только на часы, объявило бы тестовым
    нажатием весь прошлогодний «сдал и не защитил» — 1 470 событий — и отдало бы это
    следующей позиции как факт.  Скорость пальца есть вопрос только там, где палец был.
    """
    student, problem = world.student_ids[0], world.problem_ids[2]
    mig = "2026-09-02T12:11:42Z"                       # один момент на весь кусок
    pervoe = connection.execute(
        "insert into marks (student_id, problem_id, event, valid_at, recorded_at, source) "
        "values (?, ?, 'assert', ?, ?, 'импорт')", (student, problem, mig, mig)).lastrowid
    connection.execute(
        "insert into marks (student_id, problem_id, event, reverses_id, valid_at, "
        "recorded_at, source) values (?, ?, 'retract', ?, ?, ?, 'импорт')",
        (student, problem, pervoe, mig, mig))
    connection.commit()

    sobytia = journal.events([student], [problem])
    assert len(sobytia) == 2
    assert history.tehnicheskie(sobytia) == set()
    assert history.schyot_sobytij(sobytia) == 2


def test_a_tap_that_undoes_an_imported_mark_is_not_a_pair_either(
        marking, journal, world, connection):
    """Половинки из разных каналов — это не один жест, сколько бы секунд их ни делило."""
    student, problem = world.student_ids[1], world.problem_ids[2]
    mig = "2026-09-02T08:00:00Z"
    connection.execute(
        "insert into marks (student_id, problem_id, event, valid_at, recorded_at, source) "
        "values (?, ?, 'assert', ?, ?, 'импорт')", (student, problem, mig, mig))
    connection.commit()

    marking.erratum(student, problem, source="кнопка")     # тот же час по часам
    sobytia = journal.events([student], [problem])
    assert len(sobytia) == 2
    assert history.tehnicheskie(sobytia) == set()


def test_a_retraction_hours_after_the_plus_is_not_noise(marking, journal, world, clock):
    """«Сдал и не защитил» is a fact about the lesson, not about the keyboard."""
    student, problem = world.student_ids[3], world.problem_ids[0]
    marking.give(student, problem, source="кнопка")
    clock.tick(3 * 60 * 60)
    marking.retract(student, problem, source="кнопка")
    assert history.tehnicheskie(journal.events([student], [problem])) == set()


def test_only_the_pair_is_marked_and_not_the_whole_cell(marking, journal, world, clock):
    """A real plus that stands after a test click keeps counting: the признак is per
    EVENT, which is what the statistics заход next door needs it to be."""
    student, problem = _para(marking, world, clock, razryv_sek=5)
    clock.tick(3600)
    marking.give(student, problem, source="кнопка")

    sobytia = journal.events([student], [problem])
    assert len(sobytia) == 3
    assert len(history.tehnicheskie(sobytia)) == 2
    assert history.schyot_sobytij(sobytia) == 1


# --------------------------------------------------------------- the feed of a cell


def test_the_feed_tells_what_happened_who_did_it_and_which_lesson_it_counts_for(
        marking, journal, progress, world, clock):
    student, problem = world.student_ids[0], world.problem_ids[0]
    prepod = world.teacher_ids[0]
    v_chetverg = to_iso(msk(CHETVERG, 13, 40))

    marking.give(student, problem, source="кнопка", teacher_id=prepod, valid_at=v_chetverg)
    clock.tick(3600)
    marking.retract(student, problem, source="кнопка", teacher_id=prepod, valid_at=v_chetverg)

    lenta = history.istoria_kletki(journal, student, problem)
    assert [s.imya for s in lenta] == ["сдал", "снято"], "лента идёт от старого к новому"
    assert [s.teacher_id for s in lenta] == [prepod, prepod]
    assert [s.zanyatie for s in lenta] == [CHETVERG, CHETVERG]
    assert [s.tehnicheskoe for s in lenta] == [False, False]
    assert lenta[1].otmenyaet == lenta[0].id
    assert progress.states_for(student, [problem])[problem] is CellState.RETRACTED


def test_the_feed_of_an_untouched_cell_is_empty_rather_than_invented(journal, world):
    assert history.istoria_kletki(journal, world.student_ids[4], world.problem_ids[3]) == []


def test_the_feed_carries_no_event_of_a_neighbouring_cell(marking, journal, world):
    student, problem = world.student_ids[0], world.problem_ids[0]
    marking.give(student, problem, source="кнопка")
    marking.give(student, world.problem_ids[1], source="кнопка")
    marking.give(world.student_ids[1], problem, source="кнопка")

    lenta = history.istoria_kletki(journal, student, problem)
    assert len(lenta) == 1


def test_an_override_moves_the_lesson_and_says_that_a_person_moved_it(
        marking, journal, world):
    """«С возможностью перебить занятие вручную» — and the feed has to show that it was
    overridden, not quietly show another date."""
    student, problem = world.student_ids[0], world.problem_ids[0]
    itog = marking.give(student, problem, source="кнопка",
                        valid_at=to_iso(msk("2026-09-11", 18, 0)))     # в пятницу

    po_pravilu = history.istoria_kletki(journal, student, problem)[0]
    assert (po_pravilu.zanyatie, po_pravilu.perebito) == (CHETVERG, False)

    ranshe = "2026-09-03"                                             # прошлый четверг
    perebito = history.istoria_kletki(
        journal, student, problem,
        perebivki={itog.mark.id: history.nachalo_zanyatia_iso(ranshe)})[0]
    assert (perebito.zanyatie, perebito.perebito) == (ranshe, True)


def test_an_override_writes_nothing_into_the_journal(marking, journal, world):
    """The override is a row of its own; ``marks`` is append-only and stays untouched."""
    student, problem = world.student_ids[0], world.problem_ids[0]
    itog = marking.give(student, problem, source="кнопка")
    do = [(s.id, s.valid_at, s.recorded_at) for s in journal.events([student], [problem])]

    history.istoria_kletki(journal, student, problem,
                           perebivki={itog.mark.id: history.nachalo_zanyatia_iso(CHETVERG)})

    posle = [(s.id, s.valid_at, s.recorded_at) for s in journal.events([student], [problem])]
    assert do == posle
