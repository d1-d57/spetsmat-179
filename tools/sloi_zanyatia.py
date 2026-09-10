"""Separate the two layers that 2026-09-07 merged by hand, and prove it lost nothing.

WHAT HAPPENED, SO THAT THIS FILE IS READABLE IN A YEAR
--------------------------------------------------------------------------------------

On 2026-09-07 five children were moved to other teachers **for one lesson**, and there was
nowhere to record that: the site knew only the standing arrangement.  So the standing
arrangement itself was edited — six open intervals closed with ``valid_to='2026-09-07'``
and five new ones opened.  From that moment the ``enrollment`` table held two different
kinds of fact mixed together, and only a human could tell which row was which.

This tool undoes exactly that: it derives today's real composition from the live base,
restores ``enrollment`` to the morning snapshot **row for row**, and re-expresses today as
deviations in the lesson layer (``sessions`` + ``attendance``), where a one-day fact
belongs.  Nothing is invented and nothing is hardcoded: every id below is computed from
the two databases handed in.

🔴 IT REFUSES RATHER THAN GUESSES.  A child who is in the morning arrangement and in no
arrangement today is either absent or genuinely removed, and the two are indistinguishable
from inside the data — the owner said so and so does ``doc/TZ-sloj-zanyatia.md §5а``.  Such
a child must be named with ``--otsutstvuet``; otherwise the tool stops and prints who.

USAGE
--------------------------------------------------------------------------------------

    python3 tools/sloi_zanyatia.py damp      --baza <db> --kuda <file.json>
    python3 tools/sloi_zanyatia.py razlichia --baza <db> --utro <snapshot.db|.gz> --den 2026-09-07
    python3 tools/sloi_zanyatia.py razdelit  --baza <db> --utro <snapshot.db|.gz> --den 2026-09-07 \
                                             --otsutstvuet <student_id> [--primenit]
    python3 tools/sloi_zanyatia.py sverka    --baza <db> --utro <snapshot.db|.gz> \
                                             --damp <file.json> --den 2026-09-07

``razdelit`` is a DRY RUN unless ``--primenit`` is given: it prints the whole plan and
touches nothing.  That default is not politeness — the thing it writes to is the base the
school works on.
"""

# TOOL-CONTRACT: called-by-hand
#
# This tool has no automatic call site and must not acquire one.  It writes to the base a
# school works on, and the one decision it cannot make — «отсутствовал или ушёл» — belongs
# to a human by construction (``doc/TZ-sloj-zanyatia.md §5а``: the two are indistinguishable
# from inside the data).  A timer that ran it would be a timer that guessed.

from __future__ import annotations

import argparse
import gzip
import json
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

KOREN = Path(__file__).resolve().parent.parent
if str(KOREN) not in sys.path:
    sys.path.insert(0, str(KOREN))

from core.services.sostav_na_den import OTSUTSTVUET, PRISUTSTVUET, slot_of  # noqa: E402

OPEN_END = "9999-12-31"
POLYA = ("id", "student_id", "teacher_id", "room", "slot", "valid_from", "valid_to")


# --------------------------------------------------------------------------- plumbing


def _open_ro(path: str) -> sqlite3.Connection:
    """Read-only, and through the URI form so SQLite enforces it rather than us."""
    conn = sqlite3.connect("file:%s?mode=ro" % Path(path).resolve(), uri=True)
    # 🔴 ПЕРВОЙ СТРОКОЙ — ОТКУДА ЧИСЛА (Д1, владелец 10.09). Путь и дата последней
    # ЗАПИСИ внутри базы; красное, если база старше последнего занятия. Дата ФАЙЛА
    # для этого не годится: копирование и rsync её обновляют, не добавив ни строки.
    try:                                  # запуск и модулем, и файлом из tools/
        from core.istochnik import nazvat_i_proverit
    except ModuleNotFoundError:           # прямой запуск: корня репозитория нет в sys.path
        import sys as _s, pathlib as _p
        _s.path.insert(0, str(_p.Path(__file__).resolve().parent.parent))
        from core.istochnik import nazvat_i_proverit
    nazvat_i_proverit(conn)
    conn.row_factory = sqlite3.Row
    return conn


def _open_rw(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("pragma foreign_keys = on")
    return conn


def _snapshot(path: str) -> tuple:
    """Open a snapshot that may be gzipped; returns ``(connection, tempdir or None)``.

    Decompressed into a temporary directory of our own and never next to the original:
    writing beside a backup is how a backup directory silently fills up, and on the server
    that directory is owned by the service account.
    """
    if not path.endswith(".gz"):
        return _open_ro(path), None
    tmp = tempfile.mkdtemp(prefix="sloj-utro-")
    plain = Path(tmp) / "utro.db"
    with gzip.open(path, "rb") as source, open(plain, "wb") as target:
        shutil.copyfileobj(source, target)
    return _open_ro(str(plain)), tmp


def _enrollment(conn: sqlite3.Connection) -> dict:
    return {row["id"]: {k: row[k] for k in POLYA}
            for row in conn.execute("select %s from enrollment" % ", ".join(POLYA))}


def _sostav(rows: dict, den: str) -> dict:
    """``{student_id: (teacher_id, room)}`` — who is with whom on ``den``, standing only.

    The interval is half-open, ``valid_from <= den < valid_to``, exactly as
    ``infra/enrollment_repo.py`` reads it; a row closed ON ``den`` does not cover it.
    """
    slot = slot_of(den)
    if slot is None:
        return {}
    sostav = {}
    for row in rows.values():
        if row["slot"] != slot:
            continue
        if row["valid_from"] <= den < row["valid_to"]:
            sostav[row["student_id"]] = (row["teacher_id"], row["room"])
    return sostav


def _imena(conn: sqlite3.Connection) -> tuple:
    students = {r["id"]: "%s %s" % (r["surname"], r["name"])
                for r in conn.execute("select id, surname, name from students")}
    teachers = {r["id"]: r["name"] for r in conn.execute("select id, name from teachers")}
    return students, teachers


# --------------------------------------------------------------------------- commands


def cmd_damp(args) -> int:
    """Step A: the row-by-row dump that is the ONLY carrier of today's composition.

    Ids only, never names.  ``data/`` is gitignored in this project precisely because a
    snapshot carries fifty-seven children's names, and this file is meant to be committed:
    it must be reconstructable evidence, not personal data in a public repository.
    """
    conn = _open_ro(args.baza)
    rows = [dict(zip(POLYA, [r[k] for k in POLYA]))
            for r in conn.execute("select %s from enrollment order by id" % ", ".join(POLYA))]
    marks = conn.execute("select count(*) from marks").fetchone()[0]
    payload = {
        "snyato_s": str(Path(args.baza).resolve()),
        "strok_enrollment": len(rows),
        "strok_marks": marks,
        "enrollment": rows,
    }
    Path(args.kuda).parent.mkdir(parents=True, exist_ok=True)
    Path(args.kuda).write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                               encoding="utf-8")
    print("enrollment: %d строк, marks: %d → %s" % (len(rows), marks, args.kuda))
    return 0


def _plan(args):
    """Everything both commands need: the diff, and the deviations it implies."""
    live = _open_ro(args.baza)
    utro_conn, tmp = _snapshot(args.utro)
    seychas, utrom = _enrollment(live), _enrollment(utro_conn)
    students, teachers = _imena(live)

    sostav_seychas = _sostav(seychas, args.den)
    sostav_utrom = _sostav(utrom, args.den)

    otkloneniya, propali, gosti = [], [], []
    for student_id, (teacher_id, _room) in sostav_utrom.items():
        if student_id not in sostav_seychas:
            propali.append(student_id)
        elif sostav_seychas[student_id][0] != teacher_id:
            otkloneniya.append((student_id, sostav_seychas[student_id][0]))
    for student_id in sostav_seychas:
        if student_id not in sostav_utrom:
            gosti.append(student_id)

    return dict(live=live, utro=utro_conn, tmp=tmp, seychas=seychas, utrom=utrom,
                students=students, teachers=teachers, sostav_seychas=sostav_seychas,
                sostav_utrom=sostav_utrom, otkloneniya=otkloneniya, propali=propali,
                gosti=gosti)


def cmd_razlichia(args) -> int:
    """Step C: the diff a human reads before anything is applied."""
    p = _plan(args)
    students, teachers = p["students"], p["teachers"]
    print("enrollment: утром %d строк, сейчас %d" % (len(p["utrom"]), len(p["seychas"])))
    print("состав на %s: утром %d, сейчас %d"
          % (args.den, len(p["sostav_utrom"]), len(p["sostav_seychas"])))
    print("\nсменили преподавателя (%d):" % len(p["otkloneniya"]))
    for student_id, teacher_id in p["otkloneniya"]:
        print("  %-28s обычно у %-22s сегодня у %s"
              % (students.get(student_id), teachers.get(p["sostav_utrom"][student_id][0]),
                 teachers.get(teacher_id)))
    print("\nисчезли из состава (%d) — отсутствие или настоящий уход, машина не различит:"
          % len(p["propali"]))
    for student_id in p["propali"]:
        print("  %-28s обычно у %s"
              % (students.get(student_id), teachers.get(p["sostav_utrom"][student_id][0])))
    print("\nпоявились в составе (%d):" % len(p["gosti"]))
    for student_id in p["gosti"]:
        print("  %-28s сегодня у %s"
              % (students.get(student_id), teachers.get(p["sostav_seychas"][student_id][0])))
    return 0


def cmd_razdelit(args) -> int:
    """Steps D+E: today becomes deviations, ``enrollment`` returns to the morning."""
    p = _plan(args)
    students, teachers = p["students"], p["teachers"]
    nazvany = set(args.otsutstvuet or ())

    neizvestnye = [s for s in p["propali"] if s not in nazvany]
    if neizvestnye:
        print("🔴 ОТКАЗ: из состава исчезли школьники, про которых не сказано, что они "
              "отсутствовали.\n   Отсутствие и настоящий уход изнутри данных неразличимы "
              "— это решение человека.\n   Назови каждого флагом --otsutstvuet <id> "
              "или объясни иначе:", file=sys.stderr)
        for student_id in neizvestnye:
            print("     --otsutstvuet %d   # %s" % (student_id, students.get(student_id)),
                  file=sys.stderr)
        return 2
    if p["gosti"]:
        print("🔴 ОТКАЗ: в составе появились школьники, которых утром в нём не было. "
              "Гость на занятие — законное состояние слоя, но эта команда его не пишет: "
              "она разбирает правки, сделанные ПОВЕРХ утреннего состава.", file=sys.stderr)
        return 2

    # --- what will be written -------------------------------------------------------
    vosstanovit = {"udalit": [], "vernut": [], "vstavit": []}
    for row_id, row in p["seychas"].items():
        if row_id not in p["utrom"]:
            vosstanovit["udalit"].append(row_id)
        elif row != p["utrom"][row_id]:
            vosstanovit["vernut"].append((row_id, p["utrom"][row_id]))
    for row_id, row in p["utrom"].items():
        if row_id not in p["seychas"]:
            vosstanovit["vstavit"].append(row)

    zapisi = [(student_id, teacher_id, PRISUTSTVUET) for student_id, teacher_id in p["otkloneniya"]]
    zapisi += [(student_id, None, OTSUTSTVUET) for student_id in sorted(nazvany)]

    print("СЛОЙ ЗАНЯТИЯ на %s — %d отклонений:" % (args.den, len(zapisi)))
    for student_id, teacher_id, status in zapisi:
        print("  %-28s %s" % (students.get(student_id),
                              "у %s" % teachers.get(teacher_id) if teacher_id
                              else "отсутствует"))
    print("\nПОСТОЯННОЕ вернуть к утреннему: удалить %d строк, вернуть %d, вставить %d"
          % (len(vosstanovit["udalit"]), len(vosstanovit["vernut"]),
             len(vosstanovit["vstavit"])))
    if not args.primenit:
        print("\n(проба: ничего не записано. Для записи — --primenit)")
        return 0

    # --- the write ------------------------------------------------------------------
    # One transaction for both halves.  Half-applied is the worst of the three possible
    # outcomes: the standing table would be restored while today's composition existed
    # nowhere at all, and that is the loss this whole заход exists to prevent.
    conn = _open_rw(args.baza)
    marks_do = conn.execute("select count(*) from marks").fetchone()[0]
    conn.execute("begin immediate")
    try:
        session = conn.execute("select id from sessions where held_on = ? order by id",
                               (args.den,)).fetchone()
        if session is None:
            session_id = conn.execute(
                "insert into sessions (held_on, kind) values (?, 'обычное')",
                (args.den,)).lastrowid
        else:
            session_id = session["id"]
        for student_id, teacher_id, status in zapisi:
            conn.execute(
                "insert into attendance (session_id, student_id, teacher_id, status) "
                "values (?, ?, ?, ?) on conflict (session_id, student_id) do update set "
                "teacher_id = excluded.teacher_id, status = excluded.status",
                (session_id, student_id, teacher_id, status))
        for row_id in vosstanovit["udalit"]:
            conn.execute("delete from enrollment where id = ?", (row_id,))
        for row_id, row in vosstanovit["vernut"]:
            conn.execute(
                "update enrollment set student_id=?, teacher_id=?, room=?, slot=?, "
                "valid_from=?, valid_to=? where id = ?",
                (row["student_id"], row["teacher_id"], row["room"], row["slot"],
                 row["valid_from"], row["valid_to"], row_id))
        for row in vosstanovit["vstavit"]:
            conn.execute(
                "insert into enrollment (id, student_id, teacher_id, room, slot, "
                "valid_from, valid_to) values (?, ?, ?, ?, ?, ?, ?)",
                tuple(row[k] for k in POLYA))
        marks_posle = conn.execute("select count(*) from marks").fetchone()[0]
        if marks_posle != marks_do:
            raise AssertionError(
                "marks изменилось внутри транзакции: %d → %d" % (marks_do, marks_posle))
        conn.execute("commit")
    except BaseException:
        conn.execute("rollback")
        raise
    print("\n✅ записано. session_id=%d, отклонений %d, marks %d → %d"
          % (session_id, len(zapisi), marks_do,
             conn.execute("select count(*) from marks").fetchone()[0]))
    return 0


def cmd_sverka(args) -> int:
    """The readiness criterion, run as a command instead of asserted in prose."""
    live = _open_ro(args.baza)
    utro_conn, _tmp = _snapshot(args.utro)
    seychas, utrom = _enrollment(live), _enrollment(utro_conn)

    # --- clause 1: the standing table is the morning one, row for row ---------------
    rashozhdenia = []
    for row_id in sorted(set(seychas) | set(utrom)):
        if seychas.get(row_id) != utrom.get(row_id):
            rashozhdenia.append(row_id)
    print("КЛАУЗА 1 · постоянное против утреннего снимка: %d строк живых, %d утром, "
          "расхождений %d" % (len(seychas), len(utrom), len(rashozhdenia)))
    if rashozhdenia:
        for row_id in rashozhdenia:
            print("    id=%s  утро=%s  сейчас=%s"
                  % (row_id, utrom.get(row_id), seychas.get(row_id)))

    # --- clause 2: today, assembled the NEW way, equals the step-A dump -------------
    damp = json.loads(Path(args.damp).read_text(encoding="utf-8"))
    do = _sostav({r["id"]: r for r in damp["enrollment"]}, args.den)
    posle_standing = _sostav(seychas, args.den)

    session = live.execute("select id from sessions where held_on = ? order by id",
                           (args.den,)).fetchone()
    otkloneniya = {}
    if session is not None:
        for row in live.execute(
                "select student_id, teacher_id, status from attendance where session_id = ?",
                (session["id"],)):
            otkloneniya[row["student_id"]] = (row["teacher_id"], row["status"])

    sobrano, otsutstvuyut = {}, set()
    for student_id, (teacher_id, room) in posle_standing.items():
        override = otkloneniya.get(student_id)
        if override is None:
            sobrano[student_id] = (teacher_id, room)
            continue
        if override[1] == OTSUTSTVUET:
            otsutstvuyut.add(student_id)
            continue
        sobrano[student_id] = (override[0] if override[0] is not None else teacher_id, room)

    propali_v_dampe = set(do) - set(sobrano)
    lishnie = set(sobrano) - set(do)
    inye = {s for s in set(do) & set(sobrano) if do[s][0] != sobrano[s][0]}
    print("КЛАУЗА 2 · состав на %s: из дампа шага A %d, собрано новым способом %d "
          "(+%d отмечены отсутствующими)"
          % (args.den, len(do), len(sobrano), len(otsutstvuyut)))
    print("    расхождений: пропало %d, лишних %d, у другого преподавателя %d"
          % (len(propali_v_dampe - otsutstvuyut), len(lishnie), len(inye)))
    students, teachers = _imena(live)
    for student_id in sorted((propali_v_dampe - otsutstvuyut) | lishnie | inye):
        print("      %s: дамп=%s собрано=%s" % (students.get(student_id),
                                                do.get(student_id), sobrano.get(student_id)))

    # Absences are not a discrepancy: a child marked absent is legitimately with nobody,
    # and the dump — taken while the layer did not exist — could not carry that fact.
    # He must, however, be exactly the child the dump also has nowhere.
    neuchtennye = otsutstvuyut & set(do)
    if neuchtennye:
        print("    🔴 отмечен отсутствующим, но в дампе стоит у преподавателя: %s"
              % sorted(neuchtennye))

    print("    marks сейчас: %d (в дампе шага A было %d)"
          % (live.execute("select count(*) from marks").fetchone()[0], damp["strok_marks"]))
    ok = not rashozhdenia and not (propali_v_dampe - otsutstvuyut) and not lishnie \
        and not inye and not neuchtennye
    print("\n%s" % ("✅ обе клаузы зелёные" if ok else "🔴 есть расхождения, см. выше"))
    return 0 if ok else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="komanda", required=True)

    p = sub.add_parser("damp", help="построчный дамп enrollment живой базы")
    p.add_argument("--baza", required=True)
    p.add_argument("--kuda", required=True)
    p.set_defaults(fn=cmd_damp)

    for name, fn in (("razlichia", cmd_razlichia), ("razdelit", cmd_razdelit)):
        p = sub.add_parser(name)
        p.add_argument("--baza", required=True)
        p.add_argument("--utro", required=True)
        p.add_argument("--den", required=True)
        if name == "razdelit":
            p.add_argument("--otsutstvuet", type=int, action="append", default=[])
            p.add_argument("--primenit", action="store_true")
        p.set_defaults(fn=fn)

    p = sub.add_parser("sverka")
    p.add_argument("--baza", required=True)
    p.add_argument("--utro", required=True)
    p.add_argument("--damp", required=True)
    p.add_argument("--den", required=True)
    p.set_defaults(fn=cmd_sverka)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
