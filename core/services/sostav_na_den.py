"""The composition of one lesson day: the standing arrangement plus the deviations.

WHAT THIS FILE IS FOR, IN ONE SENTENCE
--------------------------------------------------------------------------------------

``core/services/room.py`` already composes those two layers **for one room, during the
lesson, for the head standing in it**.  Nothing composed them **for the whole school on a
given date**, and that is the read the distribution screen needs before anybody is in the
building: which lesson is the nearest one, who is with whom on it, and what exactly
differs from the usual.  Composing it a second time inside the web layer would be the
second source of truth this project spends its whole architecture removing, so it is
composed here, in ``core/``, where neither sqlite3 nor a template can reach.

THE MODEL IS NOT RE-DECIDED HERE.  It is the one ``doc/TZ-sloj-zanyatia.md §2`` settled:
**a lesson stores only DEVIATIONS.**  Whatever the lesson does not mention is read from
the standing arrangement on the fly, and "put him back as usual" is the deletion of a row,
not the writing of one.  Every consequence below follows from that and from nothing else.

🔴 THE SLOT OF A DAY IS NOT ITS ISO WEEKDAY, AND THIS IS THE ONE PLACE THAT KNOWS IT
--------------------------------------------------------------------------------------

``migrations/003_slot_vmesto_weekday.sql`` mapped ``weekday=1 -> slot=1`` and
``weekday=4 -> slot=2``, and the live base carries exactly those two values (105 rows in
slot 1, 86 in slot 2, measured 2026-09-07).  ``core.services.enrollment.weekday_of``
returns the ISO weekday and its callers pass that straight in as the slot, so a Monday
resolves by coincidence (1 == 1) and a **Thursday asks for slot 4, which no row has ever
carried**.  A screen built on that would show an empty school every Thursday.

``slot_of`` below is the mapping the migration actually performed.  It is deliberately
NOT a fix applied to ``resolve_many``: that call site is depended on by a dozen green
tests whose fixtures write ``slot=4`` for a Thursday, so correcting it is a change of
behaviour across the project and belongs to its own заход, not to a side effect of this
one.  The defect is reported rather than smuggled.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional, Protocol, Sequence

import config
from core.models import Session

#: ISO weekday → the ``enrollment.slot`` that day is taught in, per migration 003.
#: A day absent from this mapping is not a lesson day at all.
SLOTY_ZANYATIJ = {1: 1, 4: 2}

#: The status an ``attendance`` row carries when the student is not at the lesson.
#: ``config.ATTENDANCE_STATUSES`` is ``('был', 'не был')``; the ТЗ calls this state
#: «отсутствует» in prose, and it is this value on disk — there is no third status,
#: and inventing one would give the same fact two spellings.
OTSUTSTVUET = config.ATTENDANCE_STATUSES[1]
PRISUTSTVUET = config.ATTENDANCE_STATUSES[0]


#: When the lesson ENDS, by ISO weekday.  The timetable since 2026-09-07 is Monday
#: 14:15–15:55 and Thursday 13:10–15:00 — ``doc/PLAN-veb-2026-09.md``, the owner's own
#: line, and the only written source that is current.
#:
#: 🔴 ``ops/raspisanie.py`` DISAGREES AND IS WRONG: it still carries ``LESSON_START=16:00``,
#: ``LESSON_END=19:00`` and days ``(1, 4)`` from an earlier season.  The disagreement is
#: not theoretical — on 2026-09-07 the «перед занятием» backup timer fired at 15:45 MSK,
#: ten minutes before the lesson ENDED, and the snapshot named "before the lesson" was
#: taken after it.  Repairing that module is a separate заход; what this one must not do
#: is inherit its numbers.
KONEC_ZANYATIA = {1: (15, 55), 4: (15, 0)}

#: When the lesson BEGINS, by ISO weekday -- the other half of the same timetable and
#: the same source (``doc/PLAN-veb-2026-09.md``): Monday 14:15, Thursday 13:10.
#:
#: 🔴 IT LIVES BESIDE ``KONEC_ZANYATIA`` AND NOWHERE ELSE.  It is added here rather than
#: in the file that needed it (``core/services/history.py``, which decides which lesson a
#: tick belongs to) precisely because the end times are already here: two halves of one
#: timetable in two files is how ``ops/raspisanie.py`` came to believe in 16:00–19:00
#: while the school taught 13:10–15:00, and that disagreement cost a backup named "before
#: the lesson" taken ten minutes before it ENDED.  A weekday absent from ``SLOTY_ZANYATIJ``
#: is not a lesson day and is absent here too.
NACHALO_ZANYATIA = {1: (14, 15), 4: (13, 10)}


def slot_of(day: str) -> Optional[int]:
    """The lesson slot of a calendar day, or ``None`` when no lesson is taught on it."""
    return SLOTY_ZANYATIJ.get(date.fromisoformat(day).isoweekday())


def is_lesson_day(day: str) -> bool:
    return slot_of(day) is not None


def nearest_lesson(today: str, *, lesson_over: bool = False) -> str:
    """The date the screen opens on by default.

    Р4 of the ТЗ, in the owner's own words: *on the day of a lesson the nearest lesson is
    TODAY, until the lesson ends* — because correcting the table mid-lesson is a working
    scenario ("a teacher arrived halfway through and I need to know who he should work
    with"), not documentation.  Once it is over, the nearest lesson is the next one.

    ``lesson_over`` is passed in rather than computed here on purpose: the hours live in
    ``ops/raspisanie.py``, whose constants are known stale (it still believes 16:00–19:00
    on Mon/Thu, while the timetable since 2026-09-07 is Mon 14:15–15:55 and Thu
    13:10–15:00).  A pure function that silently trusted them would inherit the lie.
    """
    if is_lesson_day(today) and not lesson_over:
        return today
    moment = date.fromisoformat(today)
    for step in range(1, 8):
        candidate = moment + timedelta(days=step)
        if candidate.isoweekday() in SLOTY_ZANYATIJ:
            return candidate.isoformat()
    raise AssertionError("SLOTY_ZANYATIJ is empty: every week would have no lesson")


def blizhajshie_zanyatiya(ot: str, skolko: int) -> list:
    """The next ``skolko`` lesson days, starting from ``ot`` inclusive if it is one.

    The grid a teacher ticks his future absences into is a list of DATES, and this is
    the one place that knows which dates those are.  Written here rather than in the
    web layer for the same reason ``slot_of`` is here: ``SLOTY_ZANYATIJ`` is the fact,
    and a screen that stepped through the calendar itself would be a second opinion
    about which days are lesson days — the exact defect this module's own docstring
    opens by naming.

    Inclusive of ``ot`` when ``ot`` is a lesson day, because the day of a lesson is
    still a day a teacher may say he will not come to; whether it is too late to say
    so is a question about the CLOCK, not about the calendar, and belongs to the
    caller that has one.
    """
    if skolko <= 0:
        return []
    moment = date.fromisoformat(ot)
    dni = []
    # 7 days per lesson week times the number wanted, plus one week of slack, is a
    # bound that cannot loop forever however ``SLOTY_ZANYATIJ`` is later edited.
    for step in range(0, 7 * skolko + 7):
        kandidat = moment + timedelta(days=step)
        if kandidat.isoweekday() in SLOTY_ZANYATIJ:
            dni.append(kandidat.isoformat())
            if len(dni) == skolko:
                break
    return dni


def data_po_umolchaniyu(now=None) -> str:
    """The date the lesson screen opens on.

    🔴 NOT the same function as ``veb.sobrat_fajl.blizhajshee_zanyatie``, and the two are
    deliberately not merged.  That one answers «какое занятие следующее» for the PUBLIC
    landing card and never rolls over during the day; this one implements Р4 — on a lesson
    day the nearest lesson stays TODAY until the lesson ENDS, because correcting the table
    mid-lesson is a working scenario.  Merging them would drag the landing page's meaning
    into an editing screen, or the other way round; ``doc/DIZAJN-ZAKREPLENO.md §0`` says
    which direction is forbidden.  Their weekday conventions differ too (ISO here, Python
    ``weekday()`` there), which is exactly the kind of quiet mismatch a shared helper hides.

    The instant is read into the school's own timezone through ``ZoneInfo`` and never
    through a fixed ``timedelta(hours=3)``: the offset is wrong twice a year, and an
    afternoon lesson is exactly where a three-hour error moves the day.
    """
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo

    moment = now if now is not None else datetime.now(timezone.utc)
    local = moment.astimezone(ZoneInfo(config.TZ_DISPLAY))
    today = local.date().isoformat()
    konec = KONEC_ZANYATIA.get(local.isoweekday())
    over = konec is not None and (local.hour, local.minute) >= konec
    return nearest_lesson(today, lesson_over=over)


# --------------------------------------------------------------------------- ports


class EnrollmentRows(Protocol):
    """The standing layer, read-only.  One method, and the narrowness is the point.

    This service never writes ``enrollment`` — not one row, not a short interval, not a
    "temporary" one.  Writing a today-only fact into the standing table is precisely the
    accident of 2026-09-07 that this заход exists to undo.
    """

    def rows_valid_on(self, day: str, slot: int,
                      student_ids: Optional[Sequence[int]] = None) -> list: ...


class SessionsOfDay(Protocol):
    def for_day(self, held_on: str) -> Optional[Session]: ...


class Roster(Protocol):
    """Кто вообще учится — список id, и больше отсюда ничего не нужно.

    🔴 БЕЗ ЭТОГО ПОРТА ШКОЛЬНИК, ОСТАВШИЙСЯ БЕЗ СТРОКИ НА ЭТОТ ДЕНЬ, ПРОСТО ИСЧЕЗАЛ
    С ЭКРАНА. Состав собирался из `enrollment` и отклонений, то есть отвечал на
    вопрос «кого куда распределили», а спрашивают у него другое — «все ли на
    месте». Замер 07.09: у принимающего сняли четверг, три его строки закрылись,
    и трое детей пропали из четверга молча — ни в чьём списке, ни в «некуда деть».
    Ребёнок, которого не видно, — это ребёнок, которого никто не ищет.
    """

    def aktivnye(self) -> Sequence[int]: ...


class DeviationRows(Protocol):
    def rows_for_session(self, session_id: int) -> list: ...


# --------------------------------------------------------------------------- read model


@dataclass(frozen=True)
class Mesto:
    """One student on one lesson day, with BOTH layers visible at once.

    ``obychno`` is what ТЗ §3.3 is about and the reason this dataclass carries two teacher
    fields instead of one resolved answer: the screen has to show *«обычно у ‹имя›»* next
    to today's teacher, and a read model that had already collapsed the two could not.
    """

    student_id: int
    obychno: Optional[int]          # the standing teacher — «обычно у него»
    segodnya: Optional[int]         # today's teacher, standing one included
    room: Optional[str]
    otmechen_otsutstvuyushchim: bool
    otklonenie: bool                # is there a row in the lesson layer at all
    # 🔴 ТРЕТЬЯ СТУПЕНЬ: «в аудитории, но ни к кому не закреплён». Владелец 07.09:
    # *«он пока не распределённый, но он уже в моей аудитории, я должен это видеть»*.
    # Пусто — сегодня группу не меняли, и школьник там, куда его кладёт шаблон.
    gruppa: Optional[str] = None
    # 🔴 «ЛЕЖИТ ЛИ НА НЁМ РУЧНАЯ ПРАВКА ПО ПРИНИМАЮЩЕМУ» — ОТДЕЛЬНЫЙ ВОПРОС, И
    # `u_drugogo` НА НЕГО НЕ ОТВЕЧАЕТ. `u_drugogo` сравнивает двух преподавателей и
    # молчит, когда правка назвала того же самого, кто стоит в постоянном: строка в
    # слое занятия ЕСТЬ, а разницы на экране НЕТ. Кнопка «применить постоянное»
    # снимает именно СТРОКИ, поэтому считать их обязана по строкам, а не по разнице
    # имён — иначе показанное число N («снять N ручных правок?») не совпадёт с тем,
    # сколько их снимется.
    perekryt_prepodavatelem: bool = False

    @property
    def u_drugogo(self) -> bool:
        """Today with somebody other than usual."""
        return (self.segodnya is not None
                and self.obychno is not None
                and self.segodnya != self.obychno)

    @property
    def nekuda_det(self) -> bool:
        """Red, and the only red on the lesson layer (ТЗ §4).

        Not marked absent and yet with no teacher.  A student who IS marked absent is not
        lost and does not redden: that is the distinction the whole layer exists to make.
        """
        return not self.otmechen_otsutstvuyushchim and self.segodnya is None


@dataclass(frozen=True)
class SostavDnya:
    """The whole school on one date."""

    den: str
    slot: Optional[int]
    session_id: Optional[int]
    mesta: tuple

    @property
    def otkloneniya(self) -> tuple:
        return tuple(m for m in self.mesta if m.otklonenie)

    @property
    def otsutstvuyut(self) -> tuple:
        return tuple(m for m in self.mesta if m.otmechen_otsutstvuyushchim)

    @property
    def krasnye(self) -> tuple:
        return tuple(m for m in self.mesta if m.nekuda_det)

    def po_prepodavatelyam(self) -> dict:
        """``{teacher_id: (Mesto, ...)}`` for today, absences excluded.

        Grouped by TODAY's teacher, because the load a teacher actually carries this
        lesson is what ТЗ §4 counts as overload — «по фактически присутствующим», not by
        the standing list.
        """
        po: dict = {}
        for mesto in self.mesta:
            if mesto.otmechen_otsutstvuyushchim or mesto.segodnya is None:
                continue
            po.setdefault(mesto.segodnya, []).append(mesto)
        return {tid: tuple(v) for tid, v in po.items()}


# --------------------------------------------------------------------------- service


class SostavService:
    """Standing arrangement + lesson deviations, composed on the fly.

    Nothing is copied into the lesson when it is created: a lesson that copied the
    standing arrangement would freeze it, and a later correction of the standing layer
    would never reach the lesson — the two-sources illness again, one table further down.
    """

    def __init__(self, enrollment: EnrollmentRows, sessions: SessionsOfDay,
                 attendance: DeviationRows, roster: Optional[Roster] = None,
                 otsutstvuyushchie_prepoda=None) -> None:
        self._enrollment = enrollment
        self._sessions = sessions
        self._attendance = attendance
        # 🔴 ОТСУТСТВИЕ ПРИНИМАЮЩЕГО НА ДЕНЬ — ВЫЧИСЛЯЕМОЕ СОСТОЯНИЕ, А НЕ ЗАПИСЬ.
        # Владелец 10.09: «сегодня нет Нади… она отмечается как отсутствующая, но в
        # распределении её дети остаются закреплёнными за ней. Так не должно быть,
        # они должны оставаться в той же аудитории, но без прикрепления к принимающему».
        #
        # Порт зовётся с датой и отдаёт множество id тех, кого сегодня нет
        # (`veb/razdely/zanyatie.otsutstvuyushchie_prepodavateli`). Необязателен по
        # той же причине, что и `roster`: без него служба отвечает ровно как прежде.
        #
        # 🔴 ЧЕГО ЗДЕСЬ НАМЕРЕННО НЕ СДЕЛАНО, И ЭТО ВАЖНЕЕ САМОЙ ПРАВКИ:
        #   * НЕ пишется строка в слой занятия. `teacher_id = NULL` в строке
        #     отклонения означает «перекрытия нет» — то есть постоянный преподаватель
        #     ОСТАЁТСЯ, ровно то, от чего избавляемся. Записывать нечего: состояние
        #     считается из `teacher_attendance`, где оно уже лежит.
        #   * НЕ трогается `prepodavatel_ne_prihodit`: там только (teacher_id, slot),
        #     даты нет вовсе, и это высказывание «по понедельникам не бывает». Слить
        #     две породы отсутствия значило бы, что «заболел десятого» вычёркивает
        #     человека из всех четвергов навсегда.
        self._otsutstvuyushchie_prepoda = otsutstvuyushchie_prepoda
        # Необязателен НАМЕРЕННО: без него служба отвечает ровно как отвечала, и
        # дюжина зелёных тестов вокруг неё продолжает спрашивать то же самое.
        # С ним она отвечает полнее — «вот вся школа на этот день», включая тех,
        # кого в этот день никому не отдали.
        self._roster = roster

    def sostav(self, den: str) -> SostavDnya:
        slot = slot_of(den)
        if slot is None:
            # Not a lesson day: no standing rows apply and no deviations can exist.
            # Returning an empty composition rather than raising lets a caller ask about
            # any date the owner types, which Р2 says must be possible in both directions.
            return SostavDnya(den=den, slot=None, session_id=None, mesta=())

        standing = {row.student_id: row for row in self._enrollment.rows_valid_on(den, slot)}

        # Кого из принимающих сегодня нет. Спрашивается ОДИН раз на состав, а не на
        # каждого школьника: ответ один и тот же для всего дня.
        net_segodnya = frozenset()
        if self._otsutstvuyushchie_prepoda is not None:
            net_segodnya = frozenset(self._otsutstvuyushchie_prepoda(den) or ())

        session = self._sessions.for_day(den)
        deviations = {}
        if session is not None:
            for row in self._attendance.rows_for_session(session.id):
                deviations[row.student_id] = row

        vse = set(standing) | set(deviations)
        if self._roster is not None:
            vse |= set(self._roster.aktivnye())

        mesta = []
        for student_id in sorted(vse):
            row = standing.get(student_id)
            obychno = row.teacher_id if row is not None else None
            room = row.room if row is not None else None
            otklonenie = deviations.get(student_id)

            gruppa_dnya = getattr(otklonenie, "gruppa", None) if otklonenie else None

            if otklonenie is None:
                # No row — «как обычно».  This is the majority branch and it is the whole
                # economy of the deviations model: 45 students, and on a quiet lesson the
                # layer holds nothing at all.
                #
                # 🔴 ЕДИНСТВЕННОЕ УСЛОВИЕ, КОТОРЫМ ОТСУТСТВИЕ ПРИНИМАЮЩЕГО СНИМАЕТ
                # ПРИКРЕПЛЕНИЕ. `room` СОХРАНЯЕТСЯ намеренно: ребёнок остаётся в той же
                # аудитории — «они должны оставаться в той же аудитории, но без
                # прикрепления к принимающему». Отклонения в слое нет и не заводится.
                segodnya = None if obychno in net_segodnya else obychno
                mesta.append(Mesto(student_id=student_id, obychno=obychno,
                                   segodnya=segodnya, room=room,
                                   otmechen_otsutstvuyushchim=False, otklonenie=False,
                                   perekryt_prepodavatelem=False))
                continue

            absent = otklonenie.status == OTSUTSTVUET
            # ``teacher_id`` on the deviation row overrides the standing one for THIS
            # session and for nothing else.  It being NULL means "no override", so the
            # standing teacher stands — except for somebody marked absent, who is with
            # nobody by definition.
            segodnya = otklonenie.teacher_id if otklonenie.teacher_id is not None else obychno
            if absent:
                segodnya = None
            # То же условие для ветки с отклонением: и постоянный, и назначенный на
            # сегодня принимающий одинаково может оказаться отсутствующим.
            elif segodnya in net_segodnya:
                segodnya = None
            mesta.append(Mesto(student_id=student_id, obychno=obychno,
                               segodnya=segodnya, room=room,
                               otmechen_otsutstvuyushchim=absent, otklonenie=True,
                               gruppa=gruppa_dnya,
                               perekryt_prepodavatelem=otklonenie.teacher_id is not None))

        return SostavDnya(den=den, slot=slot,
                          session_id=session.id if session is not None else None,
                          mesta=tuple(mesta))


# ------------------------------------------------------- «применить постоянное к дню»


def perekrytiya_k_snyatiyu(
    sostav: SostavDnya,
    otsutstvuyushchie_prepodavateli: Sequence[int] = (),   # ОБЕ породы отсутствия
) -> tuple:
    """Кого кнопка «применить постоянное к этому дню» вернёт в постоянное.

    Возвращает id школьников — по возрастанию, чтобы число, показанное человеку в
    вопросе «снять N ручных правок за этот день?», и набор строк, который потом
    снимется, происходили из ОДНОГО вычисления. Два вычисления одного и того же
    числа — это и есть та вторая правда, от которой уходит весь этот модуль.

    Правило владельца дословно: *«начиная с сегодняшнего дня распределение должно
    меняться так, как написано в постоянном, кроме конкретных вещей, если
    преподаватель или школьник отметили, что он отсутствует в будущем»*. «Кроме»
    здесь — не оговорка, а половина правила, и ниже она разложена на три отказа.
    Каждый назван вслух, потому что молчаливый отказ неотличим от недоработки.

    🔴 ОТКАЗ 1 — ШКОЛЬНИК ОТМЕЧЕН ОТСУТСТВУЮЩИМ. Его строка не трогается вовсе.
    Отметка отсутствия — это то, что про себя сказал человек, и кнопка, которая её
    снимает, стирает не «автоматику», а чужое высказывание. Инвариант, который
    держит этот отказ, проверяется числом: отметок отсутствия ДО и ПОСЛЕ поровну.

    🔴 ОТКАЗ 2 — ПОСТОЯННОГО ПРЕПОДАВАТЕЛЯ ЭТОГО ШКОЛЬНИКА СЕГОДНЯ НЕТ В ЗДАНИИ.
    Ручная правка на таком школьнике существует ровно потому, что отдавать его
    некому: вернуть его в постоянное значило бы приписать ребёнка человеку, которого
    сегодня нет, — то есть сделать ровно то, ради предотвращения чего правку и внесли.

    🔴 «НЕТ В ЗДАНИИ» СОБИРАЕТСЯ ИЗ ДВУХ ТАБЛИЦ, И ОДНОЙ БЫЛО МАЛО. «Сегодня заболел»
    живёт в `teacher_attendance`, «по четвергам не хожу вообще» — в
    `prepodavatel_ne_prihodit`, и это РАЗНЫЕ высказывания, которые проект намеренно
    держит порознь (`veb/razdely/zanyatie.otsutstvuyushchie_prepodavateli` объясняет,
    почему сливать их нельзя). Отказ, знавший только первую, честно отказывал
    заболевшему и молча отдавал ребёнка тому, кого по четвергам не бывает никогда:
    найдено верификатором этого захода на подставленной строке `(13, слот 2)` —
    ребёнок вернулся к преподавателю 13, и `nekuda_det` его не покраснил, потому что
    формально преподаватель у него есть. Владелец сказал «кроме… если преподаватель
    отметил, что он отсутствует В БУДУЩЕМ» — вторая таблица и есть будущее.

    Обе приезжают сюда ОДНИМ списком: этот модуль в базу не ходит и складывать их
    здесь было бы третьим мнением о том, кто сегодня на месте.

    🔴 ОТКАЗ 3 — В ПОСТОЯННОМ У ШКОЛЬНИКА НИКОГО НЕТ. «Применить постоянное» не может
    означать «применить пустоту»: снятие правки не вернуло бы ребёнка на место, а
    только сделало бы его красным («некуда деть») и стёрло единственную запись о том,
    где он сегодня был. Это отказ ПО ЧТЕНИЮ исполнителя, а не по словам владельца, и
    назван он здесь отдельно от двух первых именно поэтому.

    Строка слоя занятия БЕЗ своего преподавателя (только отметка присутствия или
    только группа дня) перекрытием по принимающему не является и здесь не считается:
    постоянное на таком школьнике и так уже действует.
    """
    otsutstvuyut = frozenset(otsutstvuyushchie_prepodavateli)
    return tuple(sorted(
        mesto.student_id
        for mesto in sostav.mesta
        if mesto.perekryt_prepodavatelem
        and not mesto.otmechen_otsutstvuyushchim
        and mesto.obychno is not None
        and mesto.obychno not in otsutstvuyut
    ))
