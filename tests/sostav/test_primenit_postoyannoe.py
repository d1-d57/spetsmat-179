"""The button «применить постоянное к этому дню», end to end and by its rule.

WHY THIS FILE EXISTS, IN ONE PARAGRAPH
--------------------------------------------------------------------------------------

The owner reported that editing the STANDING arrangement for a Thursday does not show up
in the distribution FOR that Thursday.  Reproduced on a copy of the live base on
2026-09-10: the standing edit does arrive — for every pupil except the ones who already
carry a hand-made row in ``attendance`` with a teacher of their own.  That row is the
lesson layer, the lesson layer beats the standing one, and the owner's own rule says it
must («то, что вносится руками, важнее автоматического»).  So there is nothing to repair
in the ordering of the layers, and what was missing is a way to say «no hand edits today,
take the standing arrangement» — this button.

The tests below run against the REAL schema and the REAL web door, for the same reason
``test_sostav_na_den.py`` gives: the claim is as much about SQL and about the HTTP
handler as about a pure function, and a fake would only prove the code agrees with itself.
"""

from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import config
import pytest

from core.services.sostav_na_den import (
    OTSUTSTVUET,
    PRISUTSTVUET,
    SostavService,
    perekrytiya_k_snyatiyu,
)
from infra.db import apply_migrations, connect
from infra.enrollment_repo import SqliteEnrollmentRepo
from infra.room_repo import SqliteAttendance, SqliteSessions

# A signing secret must exist before an organiser cookie can be minted.  Any value does;
# this is not the production one.  Same line, same reason as in ``tests/veb/test_server.py``.
os.environ.setdefault("SPETSMAT_VEB_SECRET", "test-secret-key-32bytes!")

import veb.server as server  # noqa: E402  — after the env var, on purpose
from veb import vhod  # noqa: E402

THURSDAY = "2026-09-10"
SLOT_THURSDAY = 2


# --------------------------------------------------------------------------- fixtures


def _teacher(connection, name: str) -> int:
    return connection.execute("insert into teachers (name) values (?)", (name,)).lastrowid


def _student(connection, surname: str) -> int:
    return connection.execute(
        "insert into students (surname, name, class, status) values (?, ?, ?, 'active')",
        (surname, surname, "9Л"),
    ).lastrowid


def _standing(connection, student_id: int, teacher_id: int) -> None:
    connection.execute(
        "insert into enrollment (student_id, teacher_id, room, slot, valid_from, valid_to) "
        "values (?, ?, '302', ?, '2026-09-01', ?)",
        (student_id, teacher_id, SLOT_THURSDAY, config.OPEN_END_DATE),
    )


def _deviation(connection, session_id: int, student_id: int, teacher_id,
               status: str = PRISUTSTVUET, gruppa=None) -> None:
    connection.execute(
        "insert into attendance (session_id, student_id, teacher_id, status, gruppa) "
        "values (?, ?, ?, ?, ?)",
        (session_id, student_id, teacher_id, status, gruppa),
    )


@pytest.fixture
def shkola(tmp_path, monkeypatch):
    """A running server on a temp base, plus the connection to look inside it.

    🔴 ``_peresobrat`` IS SILENCED, AND THAT IS NOT A SHORTCUT.  The POST rebuilds the
    published page of whatever checkout the suite runs in — it writes ``docs/index.html``
    under ``config.ROOT``.  A test that leaves a modified file in the working tree turns a
    green run into a dirty repository, and the person who then commits does not know
    whether that file is his work or the test suite's.  What the rebuild does is not what
    this file is about; that it is CALLED is asserted nowhere and claimed nowhere.
    """
    monkeypatch.setattr(server, "_peresobrat", lambda: [])

    db_path = tmp_path / "spetsmat.db"
    apply_migrations(db_path, config.MIGRATIONS_DIR)
    connection = connect(db_path)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    httpd.connection = connection  # type: ignore[attr-defined]
    httpd.db_path = str(db_path)   # type: ignore[attr-defined]
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:%d" % port, connection
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join()
        connection.close()


def _kuka() -> str:
    return "%s=%s" % (vhod.COOKIE_NAME, vhod._make_cookie("organizator"))


def _get(url: str) -> tuple:
    req = urllib.request.Request(url, headers={"Cookie": _kuka()})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _post(url: str, payload: dict) -> tuple:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", "Cookie": _kuka()},
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _den_pokazyvaet(connection, student_id: int):
    """Who the distribution screen names for this pupil on this Thursday."""
    sostav = SostavService(
        enrollment=SqliteEnrollmentRepo(connection),
        sessions=SqliteSessions(connection),
        attendance=SqliteAttendance(connection),
    ).sostav(THURSDAY)
    return next(m for m in sostav.mesta if m.student_id == student_id).segodnya


# ------------------------------------------------------- the symptom, before the button


def test_the_standing_edit_reaches_a_pupil_without_an_override_and_not_one_with_it(
        shkola):
    """The owner's symptom, reproduced in eleven lines.

    This is the whole diagnosis: standing edits are NOT stuck.  They are invisible on
    exactly the pupils the lesson layer already speaks about, and on nobody else.
    """
    _, c = shkola
    staryj, novyj, gost = _teacher(c, "старый"), _teacher(c, "новый"), _teacher(c, "гость")
    bez = _student(c, "Без")
    s_pravkoj = _student(c, "Справкой")
    _standing(c, bez, staryj)
    _standing(c, s_pravkoj, staryj)
    session_id = c.execute(
        "insert into sessions (held_on) values (?)", (THURSDAY,)).lastrowid
    _deviation(c, session_id, s_pravkoj, gost)
    c.commit()

    # The standing arrangement changes for BOTH of them, from today.
    c.execute("update enrollment set teacher_id = ? where slot = ?", (novyj, SLOT_THURSDAY))
    c.commit()

    assert _den_pokazyvaet(c, bez) == novyj          # follows the standing edit
    assert _den_pokazyvaet(c, s_pravkoj) == gost     # does not — the hand row wins


# ----------------------------------------------------------- three scenarios of the day


def test_the_button_returns_a_pupil_with_an_override_to_the_standing_teacher(shkola):
    """Scenario 1 of the criterion: a pupil WITH an override."""
    base, c = shkola
    svoj, gost = _teacher(c, "свой"), _teacher(c, "гость")
    sid = _student(c, "Перекрытый")
    _standing(c, sid, svoj)
    session_id = c.execute(
        "insert into sessions (held_on) values (?)", (THURSDAY,)).lastrowid
    _deviation(c, session_id, sid, gost)
    c.commit()
    assert _den_pokazyvaet(c, sid) == gost

    status, otvet = _post(base + "/api/den/primenit-postoyannoe", {"den": THURSDAY})
    assert status == 200 and otvet["snyato"] == 1
    assert _den_pokazyvaet(c, sid) == svoj
    # 🔴 СНЯТО УДАЛЕНИЕМ СТРОКИ, А НЕ ЗАПИСЬЮ ПОСТОЯННОГО В СЛОЙ ЗАНЯТИЯ.  Строка,
    # переписанная на сегодняшнего преподавателя, заморозила бы постоянное на этом дне
    # ровно так же, как ручная правка, — то есть кнопка воспроизвела бы причину.
    assert c.execute("select count(*) from attendance where session_id = ?",
                     (session_id,)).fetchone()[0] == 0


def test_the_button_leaves_a_pupil_without_an_override_exactly_as_he_was(shkola):
    """Scenario 2: a pupil WITHOUT an override.  The standing layer already governs him,
    and the button must not invent a row to say so."""
    base, c = shkola
    svoj = _teacher(c, "свой")
    sid = _student(c, "Чистый")
    _standing(c, sid, svoj)
    session_id = c.execute(
        "insert into sessions (held_on) values (?)", (THURSDAY,)).lastrowid
    c.commit()

    status, otvet = _post(base + "/api/den/primenit-postoyannoe", {"den": THURSDAY})
    assert status == 200 and otvet["snyato"] == 0
    assert _den_pokazyvaet(c, sid) == svoj
    assert c.execute("select count(*) from attendance where session_id = ?",
                     (session_id,)).fetchone()[0] == 0


def test_the_button_does_not_hand_a_pupil_back_to_a_teacher_marked_absent(shkola):
    """Scenario 3: the standing teacher is marked ABSENT for this lesson.

    The owner's rule keeps its «кроме»: standing applies from today EXCEPT where somebody
    said he will not be there.  The override on this pupil exists precisely because his
    usual teacher is away; undoing it would put a child with a person who is not in the
    building — and the screen would say so without a word of warning.
    """
    base, c = shkola
    svoj, gost = _teacher(c, "свой"), _teacher(c, "гость")
    sid = _student(c, "Отданный")
    _standing(c, sid, svoj)
    session_id = c.execute(
        "insert into sessions (held_on) values (?)", (THURSDAY,)).lastrowid
    _deviation(c, session_id, sid, gost)
    c.execute(
        "insert into teacher_attendance (session_id, teacher_id, status, answered_at) "
        "values (?, ?, ?, '2026-09-10T09:00:00')", (session_id, svoj, OTSUTSTVUET))
    c.commit()

    status, otvet = _post(base + "/api/den/primenit-postoyannoe", {"den": THURSDAY})
    assert status == 200 and otvet["snyato"] == 0
    assert _den_pokazyvaet(c, sid) == gost


# --------------------------------------------------------------------- the invariants


def test_the_button_touches_no_absence_mark_of_a_pupil(shkola):
    """The number that judges the button: absence marks BEFORE and AFTER must be equal.

    An absence mark is what a person said about himself.  A button that quietly removes it
    is not applying the standing arrangement — it is deleting evidence.
    """
    base, c = shkola
    svoj, gost = _teacher(c, "свой"), _teacher(c, "гость")
    otsutstvuet = _student(c, "Отсутствует")
    perekryt = _student(c, "Перекрытый")
    _standing(c, otsutstvuet, svoj)
    _standing(c, perekryt, svoj)
    session_id = c.execute(
        "insert into sessions (held_on) values (?)", (THURSDAY,)).lastrowid
    _deviation(c, session_id, otsutstvuet, gost, status=OTSUTSTVUET)
    _deviation(c, session_id, perekryt, gost)
    c.commit()

    status, otvet = _post(base + "/api/den/primenit-postoyannoe", {"den": THURSDAY})
    assert status == 200
    assert otvet["do"]["otmetok_otsutstvia"] == otvet["posle"]["otmetok_otsutstvia"] == 1
    assert otvet["do"]["s_prepodavatelem"] == 2 and otvet["posle"]["s_prepodavatelem"] == 1
    assert otvet["snyato"] == 1
    # The absent pupil keeps his row, his mark AND the teacher written beside it: the
    # button said nothing about him at all.
    stroka = c.execute(
        "select teacher_id, status from attendance where session_id = ? and student_id = ?",
        (session_id, otsutstvuet)).fetchone()
    assert stroka["status"] == OTSUTSTVUET and stroka["teacher_id"] == gost


def test_a_row_that_also_carries_a_group_of_the_day_keeps_its_row(shkola):
    """Only the teacher is taken off.  «Он в этой аудитории» is a second statement about
    the same child, and this button makes no claim about it."""
    base, c = shkola
    svoj, gost = _teacher(c, "свой"), _teacher(c, "гость")
    sid = _student(c, "Сгруппой")
    _standing(c, sid, svoj)
    session_id = c.execute(
        "insert into sessions (held_on) values (?)", (THURSDAY,)).lastrowid
    _deviation(c, session_id, sid, gost, gruppa="В")
    c.commit()

    status, otvet = _post(base + "/api/den/primenit-postoyannoe", {"den": THURSDAY})
    assert status == 200 and otvet["snyato"] == 1
    stroka = c.execute(
        "select teacher_id, gruppa from attendance where session_id = ? and student_id = ?",
        (session_id, sid)).fetchone()
    assert stroka is not None and stroka["teacher_id"] is None and stroka["gruppa"] == "В"


def test_a_pupil_with_no_standing_row_keeps_his_hand_placement(shkola):
    """«Применить постоянное» cannot mean «применить пустоту».

    Dropping the override here would not return the child anywhere: it would only turn him
    red («некуда деть») and erase the only record of where he actually was.  This refusal
    is the executor's reading rather than the owner's words, and it is written down as such
    in the service — so that overruling it is one edit and not an excavation.
    """
    base, c = shkola
    gost = _teacher(c, "гость")
    sid = _student(c, "Ничей")
    session_id = c.execute(
        "insert into sessions (held_on) values (?)", (THURSDAY,)).lastrowid
    _deviation(c, session_id, sid, gost)
    c.commit()

    status, otvet = _post(base + "/api/den/primenit-postoyannoe", {"den": THURSDAY})
    assert status == 200 and otvet["snyato"] == 0
    assert _den_pokazyvaet(c, sid) == gost


# ------------------------------------------------- the number shown and the number done


def test_the_number_in_the_question_is_the_number_that_gets_removed(shkola):
    """«Снять N ручных правок за этот день?» — N comes from the SAME computation that then
    does the removing, and the endpoint that answers it names the pupils too.

    Two computations of one number is the second source of truth this whole module exists
    to remove; here it would show up as a person confirming one thing and getting another.
    """
    base, c = shkola
    svoj, gost = _teacher(c, "свой"), _teacher(c, "гость")
    ids = [_student(c, "Перекрытый-%d" % i) for i in range(3)]
    for sid in ids:
        _standing(c, sid, svoj)
    session_id = c.execute(
        "insert into sessions (held_on) values (?)", (THURSDAY,)).lastrowid
    for sid in ids[:2]:
        _deviation(c, session_id, sid, gost)
    c.commit()

    status, schet = _get(base + "/api/den/perekrytiya?den=" + THURSDAY)
    assert status == 200 and schet["n"] == 2
    assert schet["id"] == ids[:2]
    # 🔴 `shkolniki` — СТРОКИ, И ЭТО ПРОВЕРЯЕТСЯ ЗДЕСЬ, А НЕ ПОДРАЗУМЕВАЕТСЯ.  Кнопка
    # печатает их прямо в подсказку через `join(', ')`; список объектов дал бы человеку
    # «[object Object]», и ни один зелёный тест этого бы не заметил.
    assert schet["shkolniki"] == ["Перекрытый-0 Перекрытый-0", "Перекрытый-1 Перекрытый-1"]
    assert all(isinstance(x, str) for x in schet["shkolniki"])

    status, otvet = _post(base + "/api/den/primenit-postoyannoe", {"den": THURSDAY})
    assert status == 200 and otvet["snyato"] == schet["n"]
    assert otvet["id"] == schet["id"]

    # Pressed twice, it has nothing left to do: the second press is not a second removal.
    assert _post(base + "/api/den/primenit-postoyannoe", {"den": THURSDAY})[1]["snyato"] == 0


def test_a_day_that_is_not_a_lesson_day_is_refused_by_both_doors(shkola):
    base, _ = shkola
    assert _get(base + "/api/den/perekrytiya?den=2026-09-12")[0] == 400
    assert _post(base + "/api/den/primenit-postoyannoe", {"den": "2026-09-12"})[0] == 400


def test_a_day_with_no_lesson_row_at_all_answers_zero_and_writes_nothing(shkola):
    """The button does not create the lesson: it takes apart what lies on one."""
    base, c = shkola
    status, otvet = _post(base + "/api/den/primenit-postoyannoe", {"den": THURSDAY})
    assert status == 200 and otvet["snyato"] == 0
    assert c.execute("select count(*) from sessions").fetchone()[0] == 0


# ------------------------------------------------------------------ the selector itself


def test_the_selector_counts_rows_and_not_the_difference_between_two_names(shkola):
    """A hand row naming the SAME teacher as the standing layer is still a hand row.

    ``u_drugogo`` compares two teachers and stays silent here; the button removes ROWS, so
    it must count rows.  Otherwise the question says «снять 0 правок» while one is removed.
    """
    _, c = shkola
    svoj = _teacher(c, "свой")
    sid = _student(c, "Тотже")
    _standing(c, sid, svoj)
    session_id = c.execute(
        "insert into sessions (held_on) values (?)", (THURSDAY,)).lastrowid
    _deviation(c, session_id, sid, svoj)
    c.commit()

    sostav = SostavService(
        enrollment=SqliteEnrollmentRepo(c),
        sessions=SqliteSessions(c),
        attendance=SqliteAttendance(c),
    ).sostav(THURSDAY)
    mesto = next(m for m in sostav.mesta if m.student_id == sid)
    assert mesto.u_drugogo is False
    assert mesto.perekryt_prepodavatelem is True
    assert perekrytiya_k_snyatiyu(sostav) == (sid,)
