"""The story of one cell: which lesson a tick belongs to, and which taps were a test.

WHAT THIS FILE ADDS AND WHAT IT DELIBERATELY DOES NOT.  The journal already knows
everything the owner asked to see -- «когда ты ставишь галочку в крестик, там сохранялась
информация об этой галочке, когда и кто её поставил» (09.09) -- because a mark carries an
author, two times and the event it reverses.  Nothing was missing from the data; what was
missing was a reading of it.  So this module READS and never writes: not one ``INSERT``
into ``marks`` lives here, and the state of a cell is still the answer of
``ProgressService`` and of nothing else.

🔴 THE LESSON A TICK BELONGS TO IS DERIVED, NOT STORED, AND THAT IS A DECISION WITH A
REASON.  ``marks`` is append-only by trigger, so a stored attribution could never be
corrected; and the door every tap goes through (``veb/priyom.py``) writes
``valid_at = recorded_at`` and is not this position's zone to change.  A pure function of
``valid_at`` therefore reaches every tap that has already been made and every tap that
will be made through any door, without a migration and without a second writer.  The one
thing a pure function cannot do -- disagree with itself when a human says «нет, это было в
прошлый четверг» -- is what ``mark_lesson_override`` is for, and an override is itself an
appended row rather than an edit.

🔴 A TECHNICAL PAIR IS A PROPERTY OF EVENTS, NOT A FILTER ON A SCREEN.  The owner named
the noise: «я нажал и сразу второй раз нажал, чтобы убрать. Просто хотел посмотреть, как
щёлкается» (09.09).  Both halves of such a pair are marked, ``ЕДИНСТВЕННЫМ`` признаком,
and NOTHING IS DELETED -- the journal is append-only and «события из журнала не удаляются
никогда» is the owner's own word for it.  The признак is exposed as a set of ids so that
the statistics заход next door can ask the same question of the same data instead of
re-deriving it from a screen.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable, Mapping, Optional, Sequence
from zoneinfo import ZoneInfo

import config
from core.isotime import parse_iso, to_iso
from core.models import Mark, MarkEvent
from core.ports import MarkJournal
from core.services.sostav_na_den import NACHALO_ZANYATIA, SLOTY_ZANYATIJ

#: How close two opposite taps have to stand to be read as one test click.  The owner's
#: number, 09.09: «порог отсева тестовых нажатий 60 секунд — поставил и снял внутри
#: минуты, пара не идёт в статистику».
TEHNICHESKOE_OKNO_SEK = 60

#: The ``source`` a tap carries.  Named here rather than imported from ``veb/priyom.py``
#: because ``core/`` does not import the web layer; the value is fixed by the schema
#: (``migrations/001_init.sql`` closes the enumeration to «кнопка · фото · голос ·
#: импорт») and ``config.MARK_SOURCES`` mirrors it, so there is no third spelling to
#: drift into.
ISTOCHNIK_NAZHATIYA = "кнопка"

#: How far back ``zanyatie_dlya`` will look for a lesson.  Two weeks is generous for a
#: timetable with two lesson days: it survives a week with no lesson at all (a holiday,
#: a cancelled Monday) and still terminates on a day that is somehow not in the school
#: year.  A wider window would not buy an answer -- it would invent one.
GLUBINA_POISKA_DNEJ = 14

#: What each event kind is called in the feed the teacher reads.  The journal's three
#: kinds keep their meaning: ``retract`` is «сдал и не защитил», ``erratum`` is «нажато
#: по ошибке», and they are NOT the same fact even though both empty the cell of credit.
IMYA_SOBYTIA = {
    MarkEvent.ASSERT: "сдал",
    MarkEvent.RETRACT: "снято",
    MarkEvent.ERRATUM: "вычеркнуто",
}


# ------------------------------------------------------------------ the date rule


def _moskva(moment: datetime) -> datetime:
    """The instant, read in the school's own timezone.

    Through ``ZoneInfo`` and never through ``timedelta(hours=3)`` -- the offset is wrong
    twice a year, and an afternoon lesson is exactly where a three-hour error moves the
    day (``core/isotime.py`` says the same thing about storage).
    """
    if moment.tzinfo is None:
        raise ValueError("naive datetime: attach a timezone before asking about lessons")
    return moment.astimezone(ZoneInfo(config.TZ_DISPLAY))


def nachalo(den: date) -> Optional[datetime]:
    """The moment this calendar day's lesson starts, or None if it is not a lesson day."""
    chas = NACHALO_ZANYATIA.get(den.isoweekday())
    if chas is None:
        return None
    return datetime(den.year, den.month, den.day, chas[0], chas[1],
                    tzinfo=ZoneInfo(config.TZ_DISPLAY))


def zanyatie_dlya(moment: datetime) -> Optional[date]:
    """The lesson a tick made at ``moment`` belongs to: the LAST one that has STARTED.

    The owner's rule, 09.09: «галочка относится к последнему прошедшему занятию по
    московскому времени» -- marked during the lesson, it is that lesson; marked on Friday,
    on Saturday, or on Monday before the lesson begins, it is still Thursday's.

    Written as "the last lesson whose START has passed" rather than as a table of cases,
    and the two are the same answer: during a lesson its start has passed, and after it
    nothing newer has started.  The end of the lesson never enters the rule -- a teacher
    who stays ten minutes late is still marking that lesson, which is the working
    scenario ``sostav_na_den.nearest_lesson`` describes from the other side.

    None means the search window found no lesson at all, which for a real timestamp
    cannot happen with a two-day-a-week timetable and is not papered over with a guess.
    """
    mestnoe = _moskva(moment)
    segodnya = mestnoe.date()
    for shag in range(GLUBINA_POISKA_DNEJ + 1):
        den = segodnya - timedelta(days=shag)
        nach = nachalo(den)
        if nach is not None and nach <= mestnoe:
            return den
    return None


def zanyatie_po_iso(kogda: str) -> Optional[str]:
    """``zanyatie_dlya`` over a stored UTC timestamp, answering an ISO date."""
    den = zanyatie_dlya(parse_iso(kogda))
    return den.isoformat() if den is not None else None


def nachalo_zanyatia_iso(den: str) -> str:
    """The stored form of a lesson day's start -- what an override writes as ``valid_at``.

    A calendar day is not a moment, and the override column is a moment: storing the
    lesson's own start rather than midnight keeps the value inside the day in Moscow AND
    in UTC, which midnight does not (``2026-09-10T00:00`` MSK is the 9th in UTC).
    """
    moment = nachalo(date.fromisoformat(den))
    if moment is None:
        raise ValueError("%s не учебный день: занятия по %s"
                         % (den, ", ".join(str(d) for d in sorted(SLOTY_ZANYATIJ))))
    return to_iso(moment)


# --------------------------------------------------------------- the technical pair


def tehnicheskie(sobytia: Iterable[Mark]) -> set:
    """Ids of every event that is one half of a test click.

    A pair is technical when a reversing event (``retract`` or ``erratum``) undoes an
    event that was recorded less than ``TEHNICHESKOE_OKNO_SEK`` ago AND both halves came
    from a finger on a button.  BOTH ids come back: the plus that was never meant and the
    undo that took it away are one gesture, and counting either of them is counting the
    gesture.

    🔴 MEASURED BY ``recorded_at`` AND NEVER BY ``valid_at``.  ``valid_at`` is when the
    check-off happened in the world and may be moved by hand into the past; the question
    here is how fast the human's finger was, which is a fact about the keyboard and lives
    in ``recorded_at``.  Reading ``valid_at`` would call a correctly back-dated mark a
    test click, and would miss a real one.

    🔴 ONLY THE BUTTON CHANNEL IS JUDGED, AND THIS IS NOT A REFINEMENT -- IT IS THE
    DIFFERENCE BETWEEN THE FILTER WORKING AND THE FILTER DESTROYING A YEAR OF DATA.
    Measured on the live journal: the import wrote all 15 847 of its rows under ONE
    ``recorded_at`` (it is one lump, and honestly so), so every one of the 735 retractions
    it carries stands zero seconds after the ``assert`` it takes back.  A rule that looked
    only at the clock would have declared the whole of last year's «сдал и не защитил» a
    test click -- 1 470 events -- and handed that to the statistics position next door as
    fact.  Speed of a finger is only a question where there was a finger: ``source`` says
    so, and ``'кнопка'`` is the channel this page and `/priyom` write under.

    Nothing is deleted and nothing is written: this is a set of ids computed from rows
    that stay exactly where they are.
    """
    po_id = {s.id: s for s in sobytia}
    para = set()
    for sobytie in po_id.values():
        if sobytie.reverses_id is None or sobytie.source != ISTOCHNIK_NAZHATIYA:
            continue
        otmenyaemoe = po_id.get(sobytie.reverses_id)
        if otmenyaemoe is None or otmenyaemoe.source != ISTOCHNIK_NAZHATIYA:
            # Either the reversed event is outside the slice we were handed -- a caller
            # asking about one cell always has it, so that is a partial read -- or it
            # arrived by another channel, and the pair is not one gesture at all.
            continue
        razryv = parse_iso(sobytie.recorded_at) - parse_iso(otmenyaemoe.recorded_at)
        if timedelta(0) <= razryv < timedelta(seconds=TEHNICHESKOE_OKNO_SEK):
            para.add(sobytie.id)
            para.add(otmenyaemoe.id)
    return para


def schyot_sobytij(sobytia: Sequence[Mark]) -> int:
    """How many events these are, for statistics: the test clicks do not count.

    This is the counter the next заход (`statistiki-i-grobarij`) counts with, exposed here
    so that «отсев» is one answer given by one function rather than a filter re-written on
    every screen that needs it.
    """
    shum = tehnicheskie(sobytia)
    return sum(1 for s in sobytia if s.id not in shum)


# ------------------------------------------------------------------ the cell's feed


@dataclass(frozen=True)
class SobytieKletki:
    """One line of the story of a cell, ready to be read by a person.

    ``zanyatie`` is the lesson this event is attributed to and ``perebito`` says whether a
    human moved it there by hand -- the two are kept apart because «отнесено к четвергу
    по правилу» and «Иван сказал, что это был прошлый четверг» are different facts, and
    the second one is exactly what the owner asked to be able to say: «в конце четверти я
    пришёл к человеку, говорю, у тебя долги… это тогда по сути постфактум ставится».
    """

    id: int
    sobytie: MarkEvent
    kogda: str                      # recorded_at: when the tap reached the database
    zanyatie: Optional[str]         # the lesson day it counts towards, ISO
    perebito: bool                  # that lesson was named by a person, not by the rule
    tehnicheskoe: bool
    teacher_id: Optional[int]
    source: str
    otmenyaet: Optional[int]
    note: Optional[str] = None

    @property
    def imya(self) -> str:
        return IMYA_SOBYTIA[self.sobytie]


def istoria_kletki(
    journal: MarkJournal,
    student_id: int,
    problem_id: int,
    *,
    perebivki: Optional[Mapping[int, str]] = None,
) -> list:
    """Everything that ever happened to one cell, oldest first.

    ``perebivki`` is ``{mark_id: valid_at}`` -- the standing override of each mark, read
    by the caller from ``mark_lesson_override`` (``core/`` knows no SQL, so the table is
    read by the adapter and handed in).  Absent means "the rule decides", which is the
    normal case for all 15 900 events already in the journal.
    """
    perebivki = perebivki or {}
    sobytia = [s for s in journal.events([student_id], [problem_id])
               if s.student_id == student_id and s.problem_id == problem_id]
    shum = tehnicheskie(sobytia)
    lenta = []
    for s in sobytia:
        perebito = s.id in perebivki
        kogda_schitaetsya = perebivki[s.id] if perebito else s.valid_at
        lenta.append(SobytieKletki(
            id=s.id,
            sobytie=s.event,
            kogda=s.recorded_at,
            zanyatie=zanyatie_po_iso(kogda_schitaetsya),
            perebito=perebito,
            tehnicheskoe=s.id in shum,
            teacher_id=s.teacher_id,
            source=s.source,
            otmenyaet=s.reverses_id,
            note=s.note,
        ))
    return lenta
