"""AFTER-verifier for P19 (privyazka).  My own evidence, my own SQL.

Builds a real migrated SQLite database, loads the live seed of 56 students, gives
Пирогов Константин 201 imported marks, then measures what registration actually
does to the catalogue.  Counts rows with SQL after every step.
"""

from __future__ import annotations

import csv
import sqlite3
import sys
import tempfile
from pathlib import Path

REPO = Path("/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot-wt/P19-privyazka")
sys.path.insert(0, str(REPO))

import config  # noqa: E402
from infra.db import apply_migrations, connect  # noqa: E402
from infra.roster_repo import RosterRepo  # noqa: E402
from core.services.roster import RosterService, AmbiguousStudent  # noqa: E402

SEED = REPO / "seed" / "students.csv"
N_SHEETS = 18
PROBLEMS_PER_SHEET = 20


def read_seed():
    with SEED.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def build_db(tmpdir: Path, tag: str):
    """Fresh migrated journal + roster file, seeded with 56 active students."""
    journal_path = tmpdir / ("journal-%s.sqlite3" % tag)
    roster_path = tmpdir / ("roster-%s.sqlite3" % tag)
    applied = apply_migrations(journal_path, config.MIGRATIONS_DIR)
    journal = connect(journal_path)

    # sheets + problems first, so first_sheet_id can point somewhere real
    for number in range(1, N_SHEETS + 1):
        journal.execute(
            "insert into sheets (id, number, title, issued_at, ord) values (?,?,?,?,?)",
            (number, str(number), "Листок %d" % number, "2025-09-01", number),
        )
    problem_id = 0
    for sheet in range(1, N_SHEETS + 1):
        for k in range(1, PROBLEMS_PER_SHEET + 1):
            problem_id += 1
            journal.execute(
                "insert into problems (id, sheet_id, label, kind, ord) values (?,?,?,?,?)",
                (problem_id, sheet, "%d.%d" % (sheet, k), "обычная", k),
            )

    rows = read_seed()
    for index, row in enumerate(rows, start=1):
        first_sheet = int(row["first_sheet"] or 1)
        journal.execute(
            "insert into students (id, tg_id, surname, name, class, status, first_sheet_id) "
            "values (?, NULL, ?, ?, ?, 'active', ?)",
            (index, row["surname"], row["name"], row["class"] or None, first_sheet),
        )

    roster_conn = sqlite3.connect(str(roster_path))
    roster_conn.row_factory = sqlite3.Row
    return journal, roster_conn, applied, rows


def give_pirogov_201(journal):
    pid = journal.execute(
        "select id, first_sheet_id from students where surname='Пирогов' and name='Константин'"
    ).fetchone()
    for n in range(1, 202):
        journal.execute(
            "insert into marks (student_id, problem_id, event, valid_at, recorded_at, source) "
            "values (?, ?, 'assert', '2025-10-01T12:00:00Z', '2025-10-01T12:00:00Z', 'импорт')",
            (pid["id"], n),
        )
    return pid["id"], pid["first_sheet_id"]


def count(journal, sql, args=()):
    return journal.execute(sql, args).fetchone()[0]


def duplicates(journal):
    return journal.execute(
        "select count(*) from (select surname, name from students "
        "group by surname, name having count(*) > 1)"
    ).fetchone()[0]


def make_service(journal, roster_conn):
    repo = RosterRepo(journal, roster_conn)
    last_sheet = journal.execute("select id from sheets order by ord desc limit 1").fetchone()[0]
    return repo, RosterService(repo, sheets_for_current=lambda: last_sheet), last_sheet


def hr(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def part_A(tmpdir):
    hr("A. SWEEP — все 56 заявок из живого seed")
    journal, roster_conn, applied, rows = build_db(tmpdir, "A")
    print("migrations applied: %r" % (applied,))
    repo, roster, last_sheet = make_service(journal, roster_conn)

    before = count(journal, "select count(*) from students")
    print("students BEFORE: %d" % before)

    kinds = {"single": 0, "ambiguous": 0, "none": 0}
    bound_right = 0
    bound_wrong = []
    ambiguous_names = []
    none_names = []
    errors = []

    for index, row in enumerate(rows, start=1):
        surname, name = row["surname"], row["name"]
        tg = 900000 + index
        pending = roster.submit_student(tg_id=tg, surname=surname, name=name)
        match = roster.match_student(pending)
        kinds[match.kind] = kinds.get(match.kind, 0) + 1
        if match.kind == "single":
            try:
                bound_id = roster.bind_student(pending, match.one.id)
            except Exception as exc:  # noqa: BLE001
                errors.append((surname, name, repr(exc)))
                roster.accept(pending.id)
                continue
            got = journal.execute(
                "select surname, name from students where id = ?", (bound_id,)
            ).fetchone()
            if (got["surname"], got["name"]) == (surname, name):
                bound_right += 1
            else:
                bound_wrong.append((surname, name, got["surname"], got["name"]))
        elif match.kind == "ambiguous":
            ambiguous_names.append(
                (surname, name, [c.student.label for c in match.candidates])
            )
        else:
            none_names.append((surname, name))
        roster.accept(pending.id)

    after = count(journal, "select count(*) from students")
    bound_rows = count(journal, "select count(*) from students where tg_id is not null")
    print("resolutions: single=%d ambiguous=%d none=%d  (всего %d)"
          % (kinds["single"], kinds["ambiguous"], kinds["none"], len(rows)))
    print("bound to the RIGHT (surname,name) row: %d of %d" % (bound_right, len(rows)))
    print("bound to a WRONG row: %d  %r" % (len(bound_wrong), bound_wrong))
    print("bind errors: %d %r" % (len(errors), errors))
    print("students AFTER: %d   (must be %d)" % (after, before))
    print("rows carrying a tg_id: %d" % bound_rows)
    print("DUPLICATE (surname,name) pairs in students: %d" % duplicates(journal))
    if ambiguous_names:
        print("ambiguous заявки: %r" % (ambiguous_names,))
    if none_names:
        print("unresolved (none) заявки: %r" % (none_names,))
    verdict = (after == before == 56 and kinds["single"] > 0
               and bound_right == kinds["single"] and duplicates(journal) == 0)
    print("A VERDICT: %s" % ("GREEN" if verdict else "RED"))
    journal.close()
    roster_conn.close()
    return verdict


def part_B(tmpdir):
    hr("B. ПИРОГОВ — 201 отметка должна остаться на той же строке")
    journal, roster_conn, applied, rows = build_db(tmpdir, "B")
    pirogov_id, pirogov_sheet = give_pirogov_201(journal)
    print("Пирогов catalogue id=%d, first_sheet_id=%s, marks=%d"
          % (pirogov_id, pirogov_sheet,
             count(journal, "select count(*) from marks where student_id=?", (pirogov_id,))))
    repo, roster, last_sheet = make_service(journal, roster_conn)
    print("current sheet the service would use for a NEW row: %d" % last_sheet)

    before = count(journal, "select count(*) from students")
    pending = roster.submit_student(tg_id=555001, surname="Пирогов", name="Константин")
    match = roster.match_student(pending)
    print("match kind=%s candidates=%r"
          % (match.kind, [(c.student.label, round(c.score, 3)) for c in match.candidates]))
    bound_id = None
    if match.kind == "single":
        bound_id = roster.bind_student(pending, match.one.id)
    after = count(journal, "select count(*) from students")

    holder = journal.execute(
        "select id, first_sheet_id, status from students where tg_id = 555001"
    ).fetchone()
    marks_on_holder = count(
        journal, "select count(*) from marks where student_id=?", (holder["id"],)
    ) if holder else -1
    print("students BEFORE=%d AFTER=%d" % (before, after))
    print("row carrying tg_id 555001: id=%s (Пирогов's id is %d)"
          % (holder["id"] if holder else None, pirogov_id))
    print("marks on that row: %d (must be 201)" % marks_on_holder)
    print("its first_sheet_id: %s (was %s)" % (holder["first_sheet_id"] if holder else None,
                                               pirogov_sheet))
    print("its status: %s" % (holder["status"] if holder else None))
    print("DUPLICATE (surname,name) pairs: %d" % duplicates(journal))
    verdict = (after == before == 56 and holder is not None
               and holder["id"] == pirogov_id == bound_id
               and marks_on_holder == 201
               and holder["first_sheet_id"] == pirogov_sheet)
    print("B VERDICT: %s" % ("GREEN" if verdict else "RED"))
    journal.close()
    roster_conn.close()
    return verdict


def part_C(tmpdir):
    hr("C. ЧЕЛОВЕК НЕ ИЗ СПИСКА — «Иванов Иван»")
    journal, roster_conn, applied, rows = build_db(tmpdir, "C")
    repo, roster, last_sheet = make_service(journal, roster_conn)
    before = count(journal, "select count(*) from students")
    pending = roster.submit_student(tg_id=777001, surname="Иванов", name="Иван")
    match = roster.match_student(pending)
    after_match = count(journal, "select count(*) from students")
    print("match kind=%s candidates=%r"
          % (match.kind, [(c.student.label, round(c.score, 3)) for c in match.candidates]))
    print("students BEFORE=%d, AFTER match=%d (nothing written?)" % (before, after_match))
    new_id = roster.create_new_student(pending, klass="9К")
    after_create = count(journal, "select count(*) from students")
    created = journal.execute(
        "select id, surname, name, status, first_sheet_id, tg_id from students where id=?",
        (new_id,),
    ).fetchone()
    print("after explicit create_new_student: students=%d, new row id=%d %s %s "
          "status=%s first_sheet_id=%s tg_id=%s"
          % (after_create, created["id"], created["surname"], created["name"],
             created["status"], created["first_sheet_id"], created["tg_id"]))
    verdict = (match.kind == "none" and before == after_match == 56 and after_create == 57)
    print("C VERDICT: %s" % ("GREEN" if verdict else "RED"))
    journal.close()
    roster_conn.close()
    return verdict


def part_D(tmpdir):
    hr("D. ДВА КАНДИДАТА — «Цукунов Александр»")
    journal, roster_conn, applied, rows = build_db(tmpdir, "D")
    repo, roster, last_sheet = make_service(journal, roster_conn)
    before = count(journal, "select count(*) from students")
    pending = roster.submit_student(tg_id=888001, surname="Цукунов", name="Александр")
    match = roster.match_student(pending)
    after = count(journal, "select count(*) from students")
    labels = [c.student.label for c in match.candidates]
    print("match kind=%s" % match.kind)
    for c in match.candidates:
        print("   candidate: %s  score=%.4f" % (c.student.label, c.score))
    print("students BEFORE=%d AFTER=%d (nothing written?)" % (before, after))
    print("rows carrying a tg_id: %d"
          % count(journal, "select count(*) from students where tg_id is not null"))
    try:
        match.one
        one_raised = False
    except AmbiguousStudent:
        one_raised = True
    print("StudentMatch.one raises AmbiguousStudent: %s" % one_raised)
    try:
        roster.confirm_student(pending)
        confirm_raised = False
    except AmbiguousStudent:
        confirm_raised = True
    print("confirm_student refuses the tie: %s; students now=%d"
          % (confirm_raised, count(journal, "select count(*) from students")))
    verdict = (match.kind == "ambiguous"
               and "Цикунов Александр" in labels and "Цуканов Александр" in labels
               and before == after == 56 and one_raised and confirm_raised)
    print("D VERDICT: %s" % ("GREEN" if verdict else "RED"))
    journal.close()
    roster_conn.close()
    return verdict


CASES = [
    # (surname, name, expected_kind, expected_label_or_None, description)
    ("пирогов", "константин", "single", "Пирогов Константин", "нижний регистр"),
    ("ПИРОГОВ", "КОНСТАНТИН", "single", "Пирогов Константин", "верхний регистр"),
    ("Пирогова", "Константина", "single", "Пирогов Константин", "косвенный падеж (род.)"),
    ("Пирогову", "Константину", "single", "Пирогов Константин", "косвенный падеж (дат.)"),
    ("  Пирогов  ", " Константин ", "single", "Пирогов Константин", "лишние пробелы"),
    ("Пирогов", "К.", "single", "Пирогов Константин", "инициал вместо имени"),
    ("Коневник", "Фёдор", "single", "Коневник Федор", "ё против е в заявке"),
    ("Болотин", "Федор", "single", "Болотин Фёдор", "е против ё в каталоге"),
    ("Иванов", "Иван", "none", None, "никого такого нет"),
    ("Сидоров", "Пётр", "none", None, "второй посторонний"),
    ("Пирогов", "Пётр", None, None, "верная фамилия, чужое имя"),
    ("Пирогов Константин", "Константин", None, None, "ФИО целиком в поле фамилии"),
    ("Пирогов", "Костя", None, None, "уменьшительное имя"),
    ("Пироков", "Константин", None, None, "опечатка в фамилии"),
    ("Пирогов", "", None, None, "пустое имя"),
]


def part_E(tmpdir):
    hr("E. ТОЧЕЧНЫЕ ПРОВЕРКИ УСТОЙЧИВОСТИ")
    journal, roster_conn, applied, rows = build_db(tmpdir, "E")
    repo, roster, last_sheet = make_service(journal, roster_conn)
    before = count(journal, "select count(*) from students")
    ok = 0
    checked = 0
    failures = []
    for i, (surname, name, want_kind, want_label, why) in enumerate(CASES, start=1):
        pending = roster.submit_student(tg_id=990000 + i, surname=surname, name=name)
        match = roster.match_student(pending)
        labels = [(c.student.label, round(c.score, 3)) for c in match.candidates]
        checked += 1
        verdict = "—"
        if want_kind is not None:
            good = match.kind == want_kind
            if good and want_label is not None:
                good = match.candidates and match.candidates[0].student.label == want_label
            verdict = "OK" if good else "FAIL"
            if good:
                ok += 1
            else:
                failures.append((surname, name, why, match.kind, labels))
        print("  %-28s | %-22s | kind=%-9s | %s | %s"
              % ("«%s %s»" % (surname.strip(), name.strip()), why, match.kind,
                 verdict, labels))
        roster.accept(pending.id)
    after = count(journal, "select count(*) from students")
    print("students BEFORE=%d AFTER=%d (matching writes nothing)" % (before, after))
    print("E: %d of %d expectation-bearing cases passed; checked %d cases total"
          % (ok, sum(1 for c in CASES if c[2] is not None), checked))
    if failures:
        print("E failures: %r" % (failures,))
    journal.close()
    roster_conn.close()
    return not failures and before == after == 56


def part_F(tmpdir):
    hr("F. ВРЕД: вторая заявка на уже привязанного ребёнка")
    journal, roster_conn, applied, rows = build_db(tmpdir, "F")
    pirogov_id, pirogov_sheet = give_pirogov_201(journal)
    repo, roster, last_sheet = make_service(journal, roster_conn)

    first = roster.submit_student(tg_id=111001, surname="Пирогов", name="Константин")
    roster.bind_student(first, roster.match_student(first).one.id)
    roster.accept(first.id)
    print("первая заявка привязана к id=%d" % pirogov_id)

    second = roster.submit_student(tg_id=222002, surname="Пирогов", name="Константин")
    match = roster.match_student(second)
    print("вторая заявка: kind=%s candidates=%r"
          % (match.kind, [c.student.label for c in match.candidates]))
    outcome = "bound"
    try:
        roster.bind_student(second, match.one.id)
    except Exception as exc:  # noqa: BLE001
        outcome = type(exc).__name__
    after = count(journal, "select count(*) from students")
    holder = journal.execute(
        "select id from students where tg_id = 222002"
    ).fetchone()
    print("bind_student результат: %s" % outcome)
    print("students=%d, строка с tg_id 222002: %s"
          % (after, holder["id"] if holder else None))
    print("отметок на строке Пирогова: %d"
          % count(journal, "select count(*) from marks where student_id=?", (pirogov_id,)))
    print("DUPLICATE (surname,name) pairs: %d" % duplicates(journal))
    verdict = (match.kind == "single" and outcome == "TelegramIdAlreadyBound"
               and after == 56 and holder is None)
    print("F VERDICT: %s" % ("GREEN" if verdict else "RED"))
    journal.close()
    roster_conn.close()
    return verdict


def main():
    with tempfile.TemporaryDirectory() as raw:
        tmpdir = Path(raw)
        results = {
            "A": part_A(tmpdir),
            "B": part_B(tmpdir),
            "C": part_C(tmpdir),
            "D": part_D(tmpdir),
            "E": part_E(tmpdir),
            "F": part_F(tmpdir),
        }
    hr("ИТОГ")
    for key, value in results.items():
        print("%s: %s" % (key, "GREEN" if value else "RED"))
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
