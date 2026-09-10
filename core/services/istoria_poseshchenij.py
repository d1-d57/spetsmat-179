"""История посещаемости: who was at which PAST lesson, and who taught them.

WHAT THE OWNER ASKED FOR, 09.09, in his own words: *«я бы сделал вкладку История, где
вывел бы слева список… школьники и преподаватели… у каждого в первом столбце все фамилии,
а справа остальные столбцы соответствуют датам занятий. И есть либо галочка, если человек
был, либо крестик, если не был»*. This is READING ONLY: nothing here writes to the
database, and nothing here decides what "был" means a second time.

🔴 NO SECOND COMPOSITION OF A LESSON DAY. What "был" means for a student on one day --
their standing teacher unless overridden, absent unless a row says so -- is already
answered, once, by ``core.services.sostav_na_den.SostavService.sostav(den)``. This module
calls it once per PAST date and folds the results into a grid; it does not re-derive
presence from ``enrollment`` or ``attendance`` itself. The day this file starts reading
those tables directly is the day «История» and «Распределение» can show two different
answers for the same Monday.

NOTHING HERE IMPORTS sqlite3. The port below (``TeacherAbsences``) is a Protocol; its
adapter lives beside the web section that renders this view, the same split every other
file in ``core/services/`` already uses.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, Protocol, Sequence
from zoneinfo import ZoneInfo

import config
from core.models import Session
from core.services.sostav_na_den import KONEC_ZANYATIA, SostavService


def zanyatie_zaversheno(held_on: str, *, seichas: datetime) -> bool:
    """Прошло ли занятие этого дня целиком, по местному (московскому) времени.

    «История» — про ПРОШЕДШЕЕ (СТОП ТЗ этого захода: будущие отметки — другой заход).
    Сегодняшний день, на который занятие ещё не началось или идёт прямо сейчас, в историю
    не входит: экран не должен утверждать «он не был», когда занятие ещё продолжается.
    """
    den = date.fromisoformat(held_on)
    mestnoe = seichas.astimezone(ZoneInfo(config.TZ_DISPLAY))
    if den < mestnoe.date():
        return True
    if den > mestnoe.date():
        return False
    konec = KONEC_ZANYATIA.get(den.isoweekday())
    if konec is None:
        # Занятие с датой на день, где расписание никакого времени не называет
        # (руками заведённая дата вне пн/чт) — считается завершённым, а не зависшим
        # навечно «сегодняшним».
        return True
    return (mestnoe.hour, mestnoe.minute) >= konec


class TeacherAbsences(Protocol):
    """Кто из принимающих отмечен отсутствующим на КОНКРЕТНОЕ занятие.

    Отдельный порт, а не часть ``SostavService``: `teacher_attendance` — своя таблица,
    рядом с `attendance`, и `SostavService` её не читает (она про распределение детей, а
    не про то, вышел ли сам принимающий).
    """

    def otsutstvuyushchie(self, session_id: int) -> frozenset:
        """Id принимающих, отмеченных отсутствующими на этом занятии."""


@dataclass(frozen=True)
class YacheikaShkolnika:
    """Одна клетка школьника: один день, один факт.

    ``prepodavatel_id`` — кто в этот день принимал (переопределение дня, а не переопределения
    нет — тогда обычный преподаватель). ``None`` при отсутствии школьника, и ``None`` при
    ``nekuda_det`` тоже — оба РАЗНЫЕ причины пустоты, и клетка их не путает: одна несёт
    ``prisutstvoval=False``, другая — ``nekuda_det=True``.
    """

    prisutstvoval: bool
    prepodavatel_id: Optional[int]
    nekuda_det: bool = False


@dataclass(frozen=True)
class YacheikaPrepodavatelya:
    """Одна клетка принимающего: был в этот день или нет, и с кем."""

    prisutstvoval: bool
    ucheniki: tuple = ()


@dataclass(frozen=True)
class IstoriyaPoseshchenij:
    """Вся решётка: дни по возрастанию, и две таблицы под них."""

    dni: tuple
    shkolniki: dict           # student_id -> {den: YacheikaShkolnika}
    prepodavateli: dict       # teacher_id -> {den: YacheikaPrepodavatelya}

    @property
    def nekuda_det_vsego(self) -> int:
        """Число клеток «присутствовал, но принимающий не назначен» — дефект, а не факт."""
        return sum(
            1
            for po_dnyam in self.shkolniki.values()
            for yacheika in po_dnyam.values()
            if yacheika.nekuda_det
        )


class IstoriyaService:
    """Складывает ``SostavService.sostav(den)`` по всем ПРОШЕДШИМ занятиям в одну решётку."""

    def __init__(
        self,
        sostav: SostavService,
        teacher_absences: TeacherAbsences,
        active_teacher_ids: Sequence[int],
    ) -> None:
        self._sostav = sostav
        self._otsutstvia = teacher_absences
        self._prepy = tuple(active_teacher_ids)

    def sostavit(self, vse_sessii: Sequence[Session], *, seichas: datetime) -> IstoriyaPoseshchenij:
        proshedshie = sorted(
            (s for s in vse_sessii
             if s.kind != "отменённое" and zanyatie_zaversheno(s.held_on, seichas=seichas)),
            key=lambda s: s.held_on,
        )
        dni = tuple(s.held_on for s in proshedshie)

        shkolniki: dict = {}
        prepodavateli: dict = {tid: {} for tid in self._prepy}

        for sessia in proshedshie:
            den = sessia.held_on
            sostav_dnya = self._sostav.sostav(den)

            for mesto in sostav_dnya.mesta:
                yacheika = YacheikaShkolnika(
                    prisutstvoval=not mesto.otmechen_otsutstvuyushchim,
                    prepodavatel_id=mesto.segodnya,
                    nekuda_det=mesto.nekuda_det,
                )
                shkolniki.setdefault(mesto.student_id, {})[den] = yacheika

            po_prepu = sostav_dnya.po_prepodavatelyam()
            otsutstvuyut = self._otsutstvia.otsutstvuyushchie(sessia.id)
            for tid in self._prepy:
                mesta_prepa = po_prepu.get(tid, ())
                byl = tid not in otsutstvuyut and bool(mesta_prepa)
                prepodavateli[tid][den] = YacheikaPrepodavatelya(
                    prisutstvoval=byl,
                    ucheniki=tuple(m.student_id for m in mesta_prepa) if byl else (),
                )

        return IstoriyaPoseshchenij(dni=dni, shkolniki=shkolniki, prepodavateli=prepodavateli)
