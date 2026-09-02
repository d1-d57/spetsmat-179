#!/usr/bin/env python3
"""Собирает СТРОКИ, ДОЕЗЖАЮЩИЕ ДО ЧЕЛОВЕКА, из живого дерева репозитория.

Признак «доезжает до человека» — строковый литерал внутри вызова, который
показывает текст в Telegram: answer / reply / edit_text / send_message /
answer_callback_query / InlineKeyboardButton / KeyboardButton / _deny.

Считаем по AST, а не грепом: греп считает докстроки, регулярки и сообщения
ValueError, которые читает разработчик, а не ученик. Разница измерена
оркестратором 02.09: греп дал 25 находок там, где их 1.

Запуск:
    python3 tests/teksty/sobrat.py            # печать «файл:строка · текст»
    python3 tests/teksty/sobrat.py --json     # то же машинно
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

# Корень репозитория — на два уровня выше этого файла (tests/teksty/sobrat.py).
KOREN = Path(__file__).resolve().parents[2]

# Где живут тексты, обращённые к человеку.
PAPKI = ("bot", "core")

# Имена вызовов, которые показывают текст человеку. Для атрибутов сверяем
# ТОЛЬКО последнюю часть (message.answer, cb.message.edit_text, bot.send_message).
POKAZYVAYUT = frozenset(
    {
        "answer",
        "reply",
        "edit_text",
        "send_message",
        "answer_callback_query",
        "InlineKeyboardButton",
        "KeyboardButton",
        "_deny",
    }
)


def _imya_vyzova(uzel: ast.Call) -> str | None:
    f = uzel.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


def _literaly(uzel: ast.AST):
    """Строковые литералы внутри выражения, включая куски f-строк.

    Вложенные вызовы НЕ обходим: их разберёт собственная итерация walk —
    иначе текст кнопки внутри answer(...) посчитается дважды.
    """
    if isinstance(uzel, ast.Constant):
        if isinstance(uzel.value, str):
            yield uzel.lineno, uzel.value
        return
    if isinstance(uzel, ast.JoinedStr):
        for kusok in uzel.values:
            if isinstance(kusok, ast.Constant) and isinstance(kusok.value, str):
                yield uzel.lineno, kusok.value
            elif isinstance(kusok, ast.FormattedValue):
                yield from _literaly(kusok.value)
        return
    if isinstance(uzel, ast.Call):
        return
    for potomok in ast.iter_child_nodes(uzel):
        yield from _literaly(potomok)


def sobrat(koren: Path = KOREN) -> list[dict]:
    """Все строки, доезжающие до человека, отсортированные по адресу."""
    najdeno: list[dict] = []
    for papka in PAPKI:
        for put in sorted((koren / papka).rglob("*.py")):
            derevo = ast.parse(put.read_text(encoding="utf-8"), filename=str(put))
            for uzel in ast.walk(derevo):
                if not isinstance(uzel, ast.Call):
                    continue
                imya = _imya_vyzova(uzel)
                if imya not in POKAZYVAYUT:
                    continue
                vyrazhenia = list(uzel.args) + [k.value for k in uzel.keywords]
                for vyrazhenie in vyrazhenia:
                    for stroka, tekst in _literaly(vyrazhenie):
                        if not tekst.strip():
                            continue
                        najdeno.append(
                            {
                                "fajl": str(put.relative_to(koren)),
                                "stroka": stroka,
                                "vyzov": imya,
                                "tekst": tekst,
                            }
                        )
    najdeno.sort(key=lambda z: (z["fajl"], z["stroka"], z["tekst"]))
    return najdeno


def main() -> int:
    razbor = argparse.ArgumentParser(description=__doc__)
    razbor.add_argument("--json", action="store_true", help="машинный вывод")
    dovody = razbor.parse_args()

    najdeno = sobrat()
    if dovody.json:
        json.dump(najdeno, sys.stdout, ensure_ascii=False, indent=1)
        print()
        return 0

    fajly = []
    for zapis in najdeno:
        if zapis["fajl"] not in fajly:
            fajly.append(zapis["fajl"])
        print(
            "%s:%s · %s() · %s"
            % (zapis["fajl"], zapis["stroka"], zapis["vyzov"], zapis["tekst"])
        )
    print()
    print("строк, доезжающих до человека: %d, в %d файлах" % (len(najdeno), len(fajly)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
