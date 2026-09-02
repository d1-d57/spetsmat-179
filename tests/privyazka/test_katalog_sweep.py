"""THE COVERAGE TEST.  All fifty-six заявки, and the three numbers printed.

The брief is explicit that a verdict without coverage is not a verdict: «проверено 2 из
9» and «проверено 9 из 9» read the same.  So this file does not sample.  It registers
every one of the fifty-six children of the live catalogue, accepts every заявка, and
prints how many were resolved into an EXISTING row, how many made a new one, and how
many duplicates the catalogue holds afterwards.

🔴 The number that decides the position is the third one, and it is asserted twice: as
a row count (56 before, 56 after) and as a set of (surname, name) pairs with no
repetition.  A test that only counted rows would stay green if one binding overwrote
another; a test that only checked names would stay green if a row were created and
another deleted.
"""

from __future__ import annotations

from conftest import tg_for


def _all_students(connection) -> list:
    return connection.execute(
        "select id, surname, name, tg_id, status, first_sheet_id from students order by id"
    ).fetchall()


def test_all_fifty_six_bind_into_existing_rows_and_make_no_duplicates(
    connection, roster, full_catalogue, names, capsys
):
    """Every child of the live list registers; every one lands on their OWN row."""
    before = _all_students(connection)
    assert len(before) == 56, "the fixture did not build the live catalogue"

    resolved_into_existing = 0
    created_new = 0
    ambiguous = 0
    wrong_row: list = []

    for index, (surname, name) in enumerate(names):
        expected_id = full_catalogue["student_ids"][(surname, name)]
        pending = roster.submit_student(
            tg_id=tg_for(index), surname=surname, name=name
        )
        match = roster.match_student(pending)
        if match.kind == "ambiguous":
            ambiguous += 1
            roster.reject(pending.id)
            continue
        if match.kind == "none":
            created_new += 1
            roster.create_new_student(pending)
            roster.accept(pending.id)
            continue
        bound_id = roster.bind_student(pending, match.one.id)
        resolved_into_existing += 1
        if bound_id != expected_id:
            wrong_row.append((surname, name, bound_id, expected_id))
        roster.accept(pending.id)

    after = _all_students(connection)
    pairs = [(row["surname"], row["name"]) for row in after]
    duplicates = len(pairs) - len(set(pairs))

    # 🔴 The numbers the brief asks to be PRINTED, and printed with capture DISABLED:
    # pytest swallows a plain ``print`` on a passing test, so a green run would show
    # the coverage to nobody -- which is the exact failure «проверено 2 из 9 и
    # проверено 9 из 9 выглядят одинаково» describes.
    with capsys.disabled():
        print(
            "\nОХВАТ ПРИВЯЗКИ: каталог %d учеников · заявок подано %d\n"
            "  разрешено в существующих: %d\n"
            "  создано новых:            %d\n"
            "  ушло на кнопки владельцу: %d\n"
            "  ДУБЛЕЙ:                   %d"
            % (len(before), len(names), resolved_into_existing, created_new,
               ambiguous, duplicates)
        )

    assert not wrong_row, "заявка bound to the WRONG catalogue row: %r" % (wrong_row,)
    assert duplicates == 0, "duplicates appeared: %r" % (
        sorted(p for p in pairs if pairs.count(p) > 1),
    )
    assert created_new == 0, (
        "%d заявки made a NEW row although the child is in the catalogue" % created_new
    )
    assert ambiguous == 0, (
        "%d заявки with a correctly spelled name went to buttons" % ambiguous
    )
    assert resolved_into_existing == 56, (
        "🔴 zero (or partial) resolution against a NON-EMPTY catalogue is RED, not "
        "green: resolved %d of 56" % resolved_into_existing
    )
    assert len(after) == len(before), (
        "the catalogue grew from %d rows to %d" % (len(before), len(after))
    )
    for row in after:
        assert row["tg_id"] is not None, "%s %s was never bound" % (row["surname"], row["name"])
        assert row["status"] == "active"


def test_binding_leaves_first_sheet_id_alone(
    connection, roster, full_catalogue, names
):
    """The imported anchor survives the binding -- for every one of the fifty-six.

    Overwriting ``first_sheet_id`` with today's sheet is the quiet version of the same
    bug: the row keeps its marks and loses the reason they are not debts.
    """
    before = {
        row["id"]: row["first_sheet_id"] for row in _all_students(connection)
    }
    for index, (surname, name) in enumerate(names):
        pending = roster.submit_student(tg_id=tg_for(index), surname=surname, name=name)
        roster.bind_student(pending, roster.match_student(pending).one.id)
        roster.accept(pending.id)
    after = {row["id"]: row["first_sheet_id"] for row in _all_students(connection)}
    assert after == before, "first_sheet_id was rewritten by the binding"
    assert (
        after[full_catalogue["student_ids"][("Пирогов", "Константин")]]
        == full_catalogue["first_sheet_of_pirogov"]
    )


def test_second_binding_of_the_same_row_is_refused_loudly(
    connection, roster, full_catalogue, names
):
    """``tg_id`` UNIQUE is the carrier and this path does not soften it."""
    import pytest

    from core.services.roster import TelegramIdAlreadyBound

    surname, name = names[0]
    first = roster.submit_student(tg_id=tg_for(0), surname=surname, name=name)
    roster.bind_student(first, roster.match_student(first).one.id)
    roster.accept(first.id)

    second = roster.submit_student(tg_id=tg_for(999), surname=surname, name=name)
    match = roster.match_student(second)
    assert match.kind == "single", (
        "an already-bound row must stay a CANDIDATE, or the owner would be offered "
        "«завести нового» and the duplicate would come back in"
    )
    with pytest.raises(TelegramIdAlreadyBound):
        roster.bind_student(second, match.one.id)
    assert len(_all_students(connection)) == 56


def test_confirm_student_binds_and_does_not_insert(connection, roster, full_catalogue, names):
    """``confirm_student`` -- the one-call path -- resolves rather than creates.

    The owner's screen calls ``match_student`` and then ``bind_student``, so this
    method has its own test: it is public, it is what P3's own tests call, and a
    version of it that fell back to inserting would leave every other test green while
    putting the duplicate straight back on the live base.
    """
    before = connection.execute("select count(*) c from students").fetchone()["c"]
    surname, name = names[10]
    pending = roster.submit_student(tg_id=tg_for(810), surname=surname, name=name)
    bound = roster.confirm_student(pending)
    assert bound == full_catalogue["student_ids"][(surname, name)], (
        "confirm_student created a row instead of binding to the catalogue"
    )
    assert connection.execute("select count(*) c from students").fetchone()["c"] == before


def test_confirm_student_creates_only_when_nobody_matches(connection, roster, full_catalogue):
    """The fallback is real, and it is reached ONLY by a name nobody in the list has."""
    before = connection.execute("select count(*) c from students").fetchone()["c"]
    pending = roster.submit_student(tg_id=tg_for(811), surname="Иванов", name="Иван")
    new_id = roster.confirm_student(pending)
    assert connection.execute("select count(*) c from students").fetchone()["c"] == before + 1
    row = connection.execute(
        "select surname, first_sheet_id from students where id = ?", (new_id,)
    ).fetchone()
    assert row["surname"] == "Иванов"
    assert row["first_sheet_id"] == full_catalogue["sheet_ids"][-1]
