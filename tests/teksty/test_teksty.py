"""СТОРОЖ ТЕКСТОВ: ни одна строка, доезжающая до человека, не печатает ему
внутреннее состояние бота.

Почему сторож вообще есть. 02.09 в 14:24 владелец открыл бота и получил от него
`this screen is for pending_student or pending_teacher or stranger; you are a
owner.` — по-английски, именами членов перечисления `Role`. Позиция, написавшая
эту строку, была принята со всеми зелёными гейтами: её тест проверял, что доступ
ЗАПРЕЩЁН, и текст отказа его не интересовал. Отсюда правило: у текста, который
читает живой человек, обязана быть СВОЯ проверка, и она обязана уметь краснеть.

Что именно запрещено — четыре класса, и все четыре взяты из живых находок:
  * внутренние имена ролей (`stranger`, `teacher`, `head`, …) — та самая строка;
  * имена полей базы (`student_id`, `sheet_id`, `valid_at`, …) — «ученик %d»
    с первичным ключом вместо фамилии стоял на трёх экранах разбора;
  * подстрока `id=` — список заявок владельца печатал `- id=7: Иванов Пётр`;
  * `None` и латиница длиннее трёх букв — «Вы — teacher, аудитория 203.» и
    «recogniser unreachable: <urlopen error …>».

Охват берётся у `sobrat.py` — у того же сборщика, которым эти строки читали
руками. Один источник на чтение и на проверку: разойтись им негде.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sobrat import (  # noqa: E402
    BELYJ_SPISOK,
    BELYJ_SPISOK_ZHIVOJ,
    KOREN,
    sobrat,
)

# ----------------------------------------------------------------- что запрещено

#: Внутренние имена ролей. `Role` — перечисление в `core/services/roster.py`,
#: и его значения не предназначены человеку ни в каком регистре.
IMENA_ROLEJ = (
    "stranger",
    "pending_student",
    "pending_teacher",
    "owner",
    "student",
    "teacher",
    "head",
)

#: Имена полей базы и хранилища состояния.
IMENA_POLEJ = (
    "valid_at",
    "recorded_at",
    "tg_id",
    "student_id",
    "problem_id",
    "sheet_id",
    "enrollment",
    "workflow_data",
)

#: Латиница длиннее трёх букв. Три и короче оставлены нарочно: за них цепляются
#: римские цифры и однобуквенные пометки, а внутреннее имя короче четырёх букв
#: в этом коде не встречается.
LATINICA = re.compile(r"[A-Za-z]{4,}")

#: `None`, отдельным словом: «Nonе» внутри фамилии человека нас не касается.
SLOVO_NONE = re.compile(r"\bNone\b")


def _bez_belogo_spiska(tekst: str) -> str:
    for slovo in BELYJ_SPISOK:
        tekst = tekst.replace(slovo, " ")
    return tekst


def narusheniya(tekst: str) -> list[str]:
    """Чем именно эта строка провинилась. Пустой список — строка чистая."""
    najdeno: list[str] = []
    for imya in IMENA_ROLEJ + IMENA_POLEJ:
        if imya in tekst or imya.upper() in tekst:
            najdeno.append("внутреннее имя «%s»" % imya)
    if "id=" in tekst:
        najdeno.append("подстрока «id=»")
    if SLOVO_NONE.search(tekst):
        najdeno.append("слово «None»")
    for kusok in LATINICA.findall(_bez_belogo_spiska(tekst)):
        najdeno.append("латиница «%s»" % kusok)
    return najdeno


# ----------------------------------------------------------------- сам сторож

#: Охват печатает `conftest.py` после прогона: `print` внутри теста pytest
#: проглатывает, а число обязано быть видно и на зелёном.
OHVAT: dict = {}


@pytest.fixture(scope="module")
def stroki() -> list[dict]:
    """Все строки, доезжающие до человека, из ЖИВОГО дерева репозитория.

    Не фикстура-образец: сборщик читает `bot/` и `core/` с диска. Проверка по
    выдуманному входу зелена ровно потому, что вход выдуман.
    """
    najdeno = sobrat(KOREN)
    assert najdeno, "сборщик не нашёл ни одной строки — сломан он, а не тексты"
    return najdeno


def test_ni_odna_stroka_ne_pechataet_vnutrennego(stroki):
    """Главный гейт: человек не читает ни одного имени из кода."""
    plohie = [(z, narusheniya(z["tekst"])) for z in stroki]
    plohie = [(z, chem) for z, chem in plohie if chem]

    OHVAT["vsego"] = len(stroki)
    OHVAT["narushenij"] = len(plohie)
    OHVAT["fajlov"] = len({z["fajl"] for z in stroki})

    if plohie:
        otchet = "\n".join(
            "  %s:%s [%s] %r — %s"
            % (z["fajl"], z["stroka"], z["kanal"], z["tekst"], "; ".join(chem))
            for z, chem in plohie
        )
        pytest.fail(
            "внутреннее состояние доехало до человека в %d строках из %d:\n%s"
            % (len(plohie), len(stroki), otchet)
        )


def test_belyj_spisok_ne_protuh(stroki):
    """Белый список не должен разрешать больше, чем нужно.

    Каждое слово ЖИВОЙ половины списка обязано встречаться хоть в одной
    строке. Слово, которое больше нигде не стоит, — это дырка, оставленная про
    запас: завтра под неё попадёт настоящее внутреннее имя, и сторож промолчит.
    Вторая половина (`BELYJ_SPISOK_PRO_ZAPAS`) названа заданием и от живости
    освобождена нарочно — почему, написано рядом с ней.
    """
    ves_tekst = " ".join(z["tekst"] for z in stroki)
    mertvye = [slovo for slovo in BELYJ_SPISOK_ZHIVOJ if slovo not in ves_tekst]
    assert not mertvye, (
        "белый список разрешает слова, которых в текстах уже нет: %s — "
        "уберите их, иначе они прикроют собой чужое имя" % ", ".join(mertvye)
    )


def test_imya_roli_ne_podstavlyaetsya_v_tekst():
    """То, что литерал поймать не может: `role.value` ВНУТРИ показанной строки.

    Строка, с которой началась эта позиция, была не литералом: «Вы — teacher,
    аудитория 203.» получалась из `identity.teacher.role.value`, и никакая
    проверка литералов её не увидит. Здесь проверяется само выражение: `.value`
    у чего-либо, названного `role`, не имеет права стоять в аргументе показа.
    """
    import ast

    def _imya_vyzova_ast(uzel):
        f = uzel.func
        return f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)

    najdeno: list[str] = []
    for papka in ("bot", "core"):
        for put in sorted((KOREN / papka).rglob("*.py")):
            derevo = ast.parse(put.read_text(encoding="utf-8"), filename=str(put))
            for uzel in ast.walk(derevo):
                if not isinstance(uzel, ast.Call):
                    continue
                imya = (
                    uzel.func.attr
                    if isinstance(uzel.func, ast.Attribute)
                    else getattr(uzel.func, "id", None)
                )
                if imya not in ("answer", "reply", "edit_text", "send_message"):
                    continue
                for dovod in list(uzel.args) + [k.value for k in uzel.keywords]:
                    # `.value`, ушедшее внутрь ЕЩЁ ОДНОГО вызова, — это почти
                    # всегда перевод: `ROL_PO_RUSSKI.get(role.value, …)`. А
                    # `str()` и `repr()` переводом не являются и остаются
                    # запрещёнными.
                    v_vyzove: set[int] = set()
                    for gde in ast.walk(dovod):
                        if isinstance(gde, ast.Call) and _imya_vyzova_ast(gde) not in (
                            "str",
                            "repr",
                            "format",
                        ):
                            for kusok in ast.walk(gde):
                                if kusok is not gde:
                                    v_vyzove.add(id(kusok))
                    for vnutri in ast.walk(dovod):
                        if not isinstance(vnutri, ast.Attribute):
                            continue
                        if vnutri.attr != "value" or id(vnutri) in v_vyzove:
                            continue
                        vladelec = vnutri.value
                        if (
                            isinstance(vladelec, ast.Attribute)
                            and vladelec.attr in ("role", "intended_role", "kind")
                        ) or (
                            isinstance(vladelec, ast.Name)
                            and vladelec.id in ("role", "intended_role", "kind")
                        ):
                            najdeno.append(
                                "%s:%d" % (put.relative_to(KOREN), vnutri.lineno)
                            )
    assert not najdeno, (
        "значение роли подставляется прямо в текст для человека: %s — "
        "это «teacher» и «head», имена членов перечисления `Role`"
        % ", ".join(sorted(set(najdeno)))
    )
