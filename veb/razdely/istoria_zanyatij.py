#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-code — the route below is declared by `marshruty()` and
# collected by `veb.server._marshruty_razdelov` (`RAZDELY_S_MARSHRUTAMI`), the same seam
# `veb/razdely/istoria.py` already uses.
"""История занятий: кто был на каждом ПРОШЕДШЕМ занятии, и у кого/с кем.

WHAT THE OWNER ASKED FOR, 09.09, in his own words: *«я бы сделал вкладку История, где
вывел бы слева список… внутри было бы две вкладки, преподаватели и школьники… и у каждого
в первом столбце все фамилии школьников, а справа остальные столбцы соответствуют датам
занятий. И есть либо галочка, если человек был, либо крестик, если не был… наверное, нужна
не галочка, а инициалы преподавателя, который у них принимал»*. The motive, in his words
too: *«школьник всё время у одного преподавателя, а потом он заболел… мы хотим вспомнить,
у кого он был»*. This is a READ. Nothing here writes to the database.

🔴 NOT THE SAME FILE AS `veb/razdely/istoria.py`. That module is a DIFFERENT feature added
09.09 — the history of ONE MARK-JOURNAL CELL (right-click/long-press panel on Кондуит),
with its own `/api/istoria*` routes. This file is about LESSON ATTENDANCE, route `/istoria`.
Neither imports the other; the names collide in English only, not in what they answer.

🔴 THIS IS A STANDALONE PAGE, NOT A SIXTH SHELL TAB, AND THAT IS A ZONE CONSTRAINT, NOT A
DESIGN CHOICE. The site's tab machinery — the radio buttons, the menu row, the per-capability
lazy imports for «Кондуит»/«Моё» — lives in `veb/obshchee/karkas.py::obolochka()`, outside
this заход's zone. The exact same conflict already happened for those two sections, and the
codebase's own resolution is on record in `veb/razdely/kartochka.py`: build a standalone page
(own `<!doctype html>`, `_obshchij_stil()`) and record the missing menu link as a debt for
whoever owns `karkas.py`/`tools/sobrat_stranicu.py` next (see `## ВОПРОСЫ` of the заход this
file was written in). Reached today by its own URL, `/istoria`, not by a menu label.

WHAT "был" MEANS, AND WHY IT IS NOT RE-DECIDED HERE. A student is present at a past lesson
unless an `attendance` row names them absent — no row at all is the DEFAULT and means "as
usual", which is not this file's invention: it is the exact rule `veb/server.py`'s own write
path already encodes (a row is deleted, not kept, whenever it resolves back to plain
presence with no deviation). `core.services.sostav_na_den.SostavService.sostav(den)` already
answers this once per day; `core.services.istoria_poseshchenij.IstoriyaService` folds it over
every PAST date. Neither table is read a second time here — this file only turns the read
model into HTML.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import config
from core.services.istoria_poseshchenij import IstoriyaService
from core.services.sostav_na_den import SostavService
from infra.enrollment_repo import SqliteEnrollmentRepo
from infra.room_repo import SqliteAttendance, SqliteSessions
from infra.sessions_repo import SqliteSessionBook
from veb import vhod
from veb.obshchee.karkas import e
from veb.razdely.list_odin import _obshchij_stil

#: Сколько занятий назад просить у базы. Учебный год держит два занятия в неделю; 400
#: покрывает несколько лет вперёд и назад с большим запасом и не растёт со временем
#: настолько, чтобы это было заметно на school масштабе (десятки, не тысячи занятий).
GLUBINA_ZANYATIJ = 400


class _AktivnyeShkolniki:
    """Порт `Roster` для `SostavService`: кто вообще школьник сегодня.

    Тот же критерий, что и везде на сайте (`shkolniki.shkolniki`,
    `zanyatie._Uchashchiesya`, `konduit._uchastniki`): ушедший (`status = 'left'`) не
    считается. Без этого порта школьник без единой строки в `enrollment`/`attendance` на
    какую-то дату просто исчезал бы с этой даты в решётке — см. предупреждение самого
    порта в `core/services/sostav_na_den.py`.
    """

    def __init__(self, c: sqlite3.Connection) -> None:
        self._c = c

    def aktivnye(self):
        return [r[0] for r in self._c.execute(
            "select id from students where status is null or status <> 'left'")]


class _TeacherAbsences:
    """Порт `TeacherAbsences`: кто из принимающих отмечен отсутствующим на занятие.

    Тот же запрос, что уже читает `veb/razdely/zanyatie.py::otsutstvuyushchie_prepodavateli`
    для той же таблицы `teacher_attendance` — не второе мнение, тот же факт, читаемый
    здесь под собственным маленьким портом, потому что `core/services/` не имеет права
    знать про sqlite.
    """

    def __init__(self, c: sqlite3.Connection) -> None:
        self._c = c

    def otsutstvuyushchie(self, session_id: int) -> frozenset:
        return frozenset(r[0] for r in self._c.execute(
            "select teacher_id from teacher_attendance where session_id = ? and status = ?",
            (session_id, "не был")))


def _spravochniki(c: sqlite3.Connection) -> tuple:
    """Имена — школьники (активные) и преподаватели (активные), в порядке для решётки.

    🔴 `teachers.aktiven` — СХЕМНЫЙ ДРЕЙФ, как `teachers.gruppa`/`students.gruppa`
    (`veb/razdely/zanyatie.py::_spravochniki`, тот же комментарий): ни одна миграция его
    не заводит, а живая база несёт (её же уже фильтрует `karkas.sobrat_kontekst`, тем же
    условием). Не чинится здесь — чужая миграция вне зоны этого захода.
    """
    students = [dict(r) for r in c.execute(
        "select id, surname, name from students "
        "where status is null or status <> 'left' order by surname, name")]
    teachers = [dict(r) for r in c.execute(
        "select id, name, aka from teachers where aktiven = 1 order by name")]
    return students, teachers


def _initsialy(row: dict) -> str:
    polnoe = row.get("name") or ""
    return row.get("aka") or "".join(p[0] for p in polnoe.split()[:2]) or "?"


def _kratko(den: str) -> str:
    """`2026-09-07` → `07.09` — то же сжатие, что уже стоит под галочкой на Кондуите."""
    return "%s.%s" % (den[8:10], den[5:7])


DNI_NEDELI = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")


def _shapka_dnya(den: str) -> str:
    from datetime import date
    d = date.fromisoformat(den)
    return "%s %s" % (DNI_NEDELI[d.weekday()], _kratko(den))


def _sostavit(c: sqlite3.Connection):
    """Читает базу один раз и складывает решётку — то, что нужно и странице, и стилям
    (число колонок для ширины таблицы), одним и тем же вызовом."""
    sostav = SostavService(
        enrollment=SqliteEnrollmentRepo(c),
        sessions=SqliteSessions(c),
        attendance=SqliteAttendance(c),
        roster=_AktivnyeShkolniki(c),
    )
    teachers_all = [dict(r) for r in c.execute(
        "select id from teachers where aktiven = 1")]
    service = IstoriyaService(
        sostav=sostav,
        teacher_absences=_TeacherAbsences(c),
        active_teacher_ids=[r["id"] for r in teachers_all],
    )
    vse_sessii = SqliteSessionBook(c).recent(GLUBINA_ZANYATIJ)
    return service.sostavit(vse_sessii, seichas=datetime.now(timezone.utc))


def _tablitsa_shkolnikov(students, teachers_by_id, istoriya) -> str:
    shapka = "".join(f'<th class="ist-zn">{e(_shapka_dnya(d))}</th>' for d in istoriya.dni)
    stroki = []
    for u in students:
        po_dnyam = istoriya.shkolniki.get(u["id"], {})
        kletki = []
        for den in istoriya.dni:
            yacheika = po_dnyam.get(den)
            if yacheika is None or not yacheika.prisutstvoval:
                kletki.append('<td class="ist-net" title="не был">✕</td>')
            elif yacheika.nekuda_det:
                kletki.append(
                    '<td class="ist-def" title="был, но принимающий не назначен">?</td>')
            else:
                prep = teachers_by_id.get(yacheika.prepodavatel_id)
                initsialy = _initsialy(prep) if prep else "?"
                polnoe = e(prep["name"]) if prep else "принимающий неизвестен"
                kletki.append(f'<td class="ist-byl" title="{polnoe}">{e(initsialy)}</td>')
        stroki.append(
            f'<tr><td class="ist-kto"><b>{e(u["surname"])}</b> {e(u["name"])}</td>'
            f'{"".join(kletki)}</tr>')
    if not istoriya.dni:
        return '<p class="ist-pusto">прошедших занятий пока нет</p>'
    return (f'<table class="ist-tabl"><thead><tr><th>Школьник</th>{shapka}</tr></thead>'
            f'<tbody>{"".join(stroki)}</tbody></table>')


def _tablitsa_prepodavatelej(teachers, students_by_id, istoriya) -> str:
    shapka = "".join(f'<th class="ist-zn">{e(_shapka_dnya(d))}</th>' for d in istoriya.dni)
    stroki = []
    for t in teachers:
        po_dnyam = istoriya.prepodavateli.get(t["id"], {})
        kletki = []
        for den in istoriya.dni:
            yacheika = po_dnyam.get(den)
            if yacheika is None or not yacheika.prisutstvoval:
                kletki.append('<td class="ist-net" title="не был">✕</td>')
            else:
                imena = ", ".join(
                    "%s %s" % (students_by_id[sid]["surname"], students_by_id[sid]["name"])
                    for sid in yacheika.ucheniki if sid in students_by_id)
                kletki.append(f'<td class="ist-byl" title="{e(imena)}">✓</td>')
        stroki.append(
            f'<tr><td class="ist-kto"><b>{e(t["name"])}</b></td>{"".join(kletki)}</tr>')
    if not istoriya.dni:
        return '<p class="ist-pusto">прошедших занятий пока нет</p>'
    return (f'<table class="ist-tabl"><thead><tr><th>Преподаватель</th>{shapka}</tr></thead>'
            f'<tbody>{"".join(stroki)}</tbody></table>')


SVOI_STILI = """
.istoria{max-width:none;padding:1.3em 2.4em 2.4em}
.istoria h1{font-family:var(--sans);font-size:1.6em;margin:0 0 .3em}
.istoria .podpis{color:var(--muted);font-family:var(--sans);font-size:.92em;margin:0 0 1.2em}
.ist-vkladki{display:flex;gap:.4rem;margin:0 0 1rem;font-family:var(--sans)}
.ist-vkladki label{cursor:pointer;font-weight:600;padding:.35em 1.1rem;border-radius:8px;
  border:1px solid var(--rule);color:var(--muted)}
#iv-shk:checked~.ist-vkladki label[for=iv-shk],
#iv-prep:checked~.ist-vkladki label[for=iv-prep]{color:var(--accent);
  background:var(--accent-soft);border-color:var(--accent)}
#is-shk,#is-prep{display:none}
#iv-shk:checked~#is-shk,#iv-prep:checked~#is-prep{display:block}
.ist-pusto{color:var(--muted)}
/* Решётка «люди × даты» в той же форме, что уже стоит у Кондуита: закреплённая первая
   колонка, узкие клетки дат, никакого горизонтального скролла страницы (канон, правило 4)
   — при паре занятий в неделю ширина решётки далека от предела, который Кондуит уже
   проверил на двадцати одном столбце. */
.ist-tabl{font-size:.95rem;width:100%;border-collapse:separate;border-spacing:0}
.ist-tabl th.ist-zn{padding:.5rem .2rem;text-align:center;font-size:.78rem;min-width:3em;
  border-bottom:2px solid var(--rule);border-left:1px solid var(--rule)}
.ist-tabl thead th{position:sticky;top:0;z-index:2;background:var(--panel)}
.ist-tabl thead th:first-child{left:0;z-index:3;text-align:left;
  border-bottom:2px solid var(--rule)}
.ist-tabl td.ist-kto{white-space:nowrap;padding:.3rem 1.2rem .3rem 0;font-size:.95rem;
  position:sticky;left:0;z-index:1;background:var(--bg);border-bottom:1px solid var(--rule)}
.ist-tabl tbody td+td{text-align:center;padding:.42rem .3rem;font-family:var(--sans);
  font-size:.92rem;min-width:3em;border-left:1px solid var(--rule);
  border-bottom:1px solid var(--rule)}
.ist-tabl td.ist-byl{color:var(--accent);font-weight:600}
.ist-tabl td.ist-net{color:var(--faint)}
.ist-tabl td.ist-def{color:var(--warm);font-weight:700}
@media(max-width:760px){
  .istoria{padding-left:1.1rem;padding-right:1.1rem}
  .ist-tabl td.ist-kto{width:7rem;max-width:7rem;overflow:hidden;text-overflow:ellipsis;
    white-space:nowrap}
}
"""


def stranica(c: sqlite3.Connection) -> str:
    """Вся страница: обе решётки собраны один раз каждая, показывает CSS без JS."""
    students, teachers = _spravochniki(c)
    students_by_id = {u["id"]: u for u in students}
    teachers_by_id = {t["id"]: t for t in teachers}
    istoriya = _sostavit(c)

    podpis = ("прошедших занятий пока нет" if not istoriya.dni
              else "занятий: %d" % len(istoriya.dni))
    if istoriya.nekuda_det_vsego:
        podpis += " · без принимающего в этот день: %d" % istoriya.nekuda_det_vsego

    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>История занятий — Ключики</title>
<style>{_obshchij_stil()}{SVOI_STILI}</style></head>
<body>
<input class="rd" type="radio" name="ist-vid" id="iv-shk" checked hidden>
<input class="rd" type="radio" name="ist-vid" id="iv-prep" hidden>
<main class="istoria">
  <h1>История</h1>
  <p class="podpis">{e(podpis)} · галочка — инициалы принимавшего, наведение — полное имя;
    у преподавателя наведение показывает, кого он в этот день принимал</p>
  <nav class="ist-vkladki">
    <label for="iv-shk">Школьники</label>
    <label for="iv-prep">Преподаватели</label>
  </nav>
  <section id="is-shk">{_tablitsa_shkolnikov(students, teachers_by_id, istoriya)}</section>
  <section id="is-prep">{_tablitsa_prepodavatelej(teachers, students_by_id, istoriya)}</section>
</main>
</body></html>"""


def _soedinenie(h) -> sqlite3.Connection:
    """Соединение сервера, а при его отсутствии — точно такое же.

    Тот же приём, что уже стоит в `veb/razdely/istoria.py::_soedinenie` — фикстура тестов
    кладёт путь на объект сервера, а прагмы WAL/busy_timeout живут в `veb/server.py`.
    """
    svoj = getattr(h, "_connection", None)
    if callable(svoj):
        return svoj()
    db_path = getattr(getattr(h, "server", None), "db_path", config.DB_PATH)
    raw = sqlite3.connect(str(db_path), check_same_thread=False, isolation_level=None)
    raw.execute("pragma foreign_keys = on")
    raw.execute("pragma journal_mode = WAL")
    raw.execute("pragma synchronous = normal")
    raw.execute("pragma busy_timeout = %d" % config.BUSY_TIMEOUT_MS)
    raw.row_factory = sqlite3.Row
    return raw


def _otdat_html(h, status: int, telo: str) -> None:
    telo_bytes = telo.encode("utf-8")
    h.send_response(status)
    h.send_header("Content-Type", "text/html; charset=utf-8")
    h.send_header("Content-Length", str(len(telo_bytes)))
    h.end_headers()
    h.wfile.write(telo_bytes)


def pokazat_istoriyu(h) -> bool:
    """`/istoria` — обе решётки на одной странице. Только для вошедших.

    Гость сюда не пускается тем же порогом, каким закрыт Кондуит: полные фамилии и
    посещаемость — не гостевые данные. `karkas.VOZMOZHNOSTI` вне зоны этого захода, так
    что порог — прямая проверка роли, а не новая именованная возможность.
    """
    if vhod.rol(h.headers) is None:
        _otdat_html(h, 403, "<p>нужно войти</p>")
        return True
    c = _soedinenie(h)
    try:
        _otdat_html(h, 200, stranica(c))
    finally:
        c.close()
    return True


def marshruty():
    """Пути этого раздела: `{путь: обработчик}`. Зовётся сборкой сервера."""
    return {"/istoria": pokazat_istoriyu}
