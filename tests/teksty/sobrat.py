#!/usr/bin/env python3
"""Собирает СТРОКИ, ДОЕЗЖАЮЩИЕ ДО ЧЕЛОВЕКА, из живого дерева репозитория.

Два канала, и второй найден по ходу работы — прямой признак из задания
пропускает целые экраны.

КАНАЛ A — ПРЯМОЙ (признак из задания). Литерал стоит в ТЕКСТОВОЙ позиции
вызова, который показывает текст в Telegram: `answer`, `reply`, `edit_text`,
`send_message`, `answer_callback_query`, `InlineKeyboardButton`,
`KeyboardButton`, `_deny`. Текстовая позиция названа поимённо для каждого
вызова, потому что `callback_data="accept:%d"` человек не читает никогда, а
`InlineKeyboardButton` берёт оба одинаково.

КАНАЛ B — ЧЕРЕЗ ПОСРЕДНИКА. Экран собирается функцией, а показывается уже её
результат: `await message.answer(draft_text(draft, catalogue))`. Тогда ВСЕ
литералы `draft_text` доезжают до человека, а прямой признак не видит ни
одного. Так устроены обе таблицы подтверждения (`render` в `voice.py` и
`text_input.py`), черновик фото, список заявок владельца и все клавиатуры.
Канал находится неподвижной точкой: функция попадает в «показывающие», если
её вызов стоит в текстовой позиции показывающего вызова; повторяем, пока
множество растёт. Имена разрешаются внутри одного файла и по импортам вида
`from ... import name`.

Считаем по AST, а не грепом: греп считает докстроки, регулярки и сообщения
`ValueError`, которые читает разработчик, а не ученик. Разница измерена
оркестратором 02.09: греп дал 25 находок там, где их 1.

Запуск:
    python3 tests/teksty/sobrat.py            # печать «файл:строка · текст»
    python3 tests/teksty/sobrat.py --kanal a  # только прямой признак задания
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

#: Показывающие вызовы и их ТЕКСТОВЫЕ позиции: (номера позиционных аргументов,
#: имена ключевых). Всё остальное — `callback_data`, `reply_markup`,
#: `show_alert`, `chat_id` — человек не читает и в счёт не идёт.
POKAZYVAYUT: dict[str, tuple[tuple[int, ...], tuple[str, ...]]] = {
    "answer": ((0,), ("text",)),
    "reply": ((0,), ("text",)),
    "edit_text": ((0,), ("text",)),
    "answer_callback_query": ((0,), ("text",)),
    "send_message": ((1,), ("text",)),
    "InlineKeyboardButton": ((0,), ("text",)),
    "KeyboardButton": ((0,), ("text",)),
    # `_deny(event, "…")` и `_redraw(message, "…", markup)` — первый аргумент
    # адресат, текст второй.
    "_deny": ((1,), ("text",)),
    "_redraw": ((1,), ("text",)),
    "_redraw_message": ((1,), ("text",)),
    # Отказ приёма файла показывается ДОСЛОВНО: `answer(str(refusal))`
    # в `bot/routers/photo.py`. Значит его текст — текст для человека.
    "IntakeRefused": ((0,), ()),
}

#: Латиница в этих словах законна: их читает человек и они не внутренние.
#:
#: Первые четыре названы в задании. Остальные — СОБСТВЕННЫЕ КОМАНДЫ БОТА:
#: команда пишется латиницей всегда, человек её ЧИТАЕТ И НАБИРАЕТ, и отказ,
#: который обязан сказать «что делать дальше», без неё сказать этого не может.
#: Список закрытый и сверяется с живым кодом: `test_teksty.py` краснеет, если
#: здесь стоит команда, которую бот не регистрирует.
BELYJ_SPISOK_ZHIVOJ = (
    "Telegram",
    "setka",
    "god",
    "dolgi",
    "auditoria",
)

#: Названы в задании, но НИ В ОДНОЙ живой строке сейчас не стоят. Разрешены —
#: и вынесены отдельно, чтобы сторож не требовал от них живости: экспорт в
#: Excel и имя проекта появятся в тексте раньше, чем кто-нибудь вспомнит про
#: этот список, и красное на верной строке в день занятия хуже, чем лишнее
#: слово в разрешении.
BELYJ_SPISOK_PRO_ZAPAS = ("Excel", "spetsmat")

BELYJ_SPISOK = BELYJ_SPISOK_ZHIVOJ + BELYJ_SPISOK_PRO_ZAPAS


def _imya_vyzova(uzel: ast.Call) -> str | None:
    f = uzel.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


def _tekstovye_vyrazhenia(uzel: ast.Call, pozicii) -> list[ast.AST]:
    """Только те аргументы вызова, которые человек читает."""
    nomera, klyuchi = pozicii
    vyrazhenia: list[ast.AST] = []
    for nomer in nomera:
        if nomer < len(uzel.args) and not isinstance(uzel.args[nomer], ast.Starred):
            vyrazhenia.append(uzel.args[nomer])
    for klyuch in uzel.keywords:
        if klyuch.arg in klyuchi:
            vyrazhenia.append(klyuch.value)
    return vyrazhenia


def _literaly(uzel: ast.AST):
    """Строковые литералы внутри выражения, включая куски f-строк.

    НЕ спускаемся: во вложенные вызовы (их разберёт собственная итерация —
    иначе текст кнопки внутри `answer(...)` посчитается дважды) и в индекс
    подписки (`cell["label"]` — это имя поля словаря, а не текст на экране).
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
    if isinstance(uzel, ast.Subscript):
        yield from _literaly(uzel.value)
        return
    for potomok in ast.iter_child_nodes(uzel):
        yield from _literaly(potomok)


def _funkcii(derevo: ast.AST) -> dict[str, ast.AST]:
    """Функции файла по имени — цели, в которые может уйти сборка экрана."""
    najdeno: dict[str, ast.AST] = {}
    for uzel in ast.walk(derevo):
        if isinstance(uzel, (ast.FunctionDef, ast.AsyncFunctionDef)):
            najdeno[uzel.name] = uzel
    return najdeno


def _vse_literaly_tela(uzel: ast.AST):
    """Все строковые литералы тела функции, кроме докстроки и подписок."""
    telo = list(getattr(uzel, "body", []))
    if (
        telo
        and isinstance(telo[0], ast.Expr)
        and isinstance(telo[0].value, ast.Constant)
        and isinstance(telo[0].value.value, str)
    ):
        telo = telo[1:]
    for shag in telo:
        for vnutri in ast.walk(shag):
            if isinstance(vnutri, ast.Subscript):
                continue
            if isinstance(vnutri, ast.Constant) and isinstance(vnutri.value, str):
                # Индексы подписок отсеиваем ниже, по родителю.
                yield vnutri
            elif isinstance(vnutri, ast.JoinedStr):
                for kusok in vnutri.values:
                    if isinstance(kusok, ast.Constant) and isinstance(kusok.value, str):
                        yield kusok


#: Вызовы, чей строковый аргумент — ИМЯ ПОЛЯ или образец сравнения, а не текст:
#: `row.get("label")`, `data.startswith("accept:")`, `state.update_data(...)`.
NE_TEKST_VYZOVY = frozenset(
    {"get", "setdefault", "pop", "startswith", "endswith", "split", "rsplit",
     "strip", "lstrip", "rstrip", "join", "count", "index", "replace",
     "getattr", "hasattr", "setattr", "update_data", "set_data", "encode",
     "decode", "debug", "info", "warning", "error", "exception"}
)


def _ne_tekst(derevo: ast.AST) -> set[int]:
    """id() литералов, которые человек не читает при всём желании.

    Три источника: индекс подписки (`cell["label"]`), аргумент служебного
    вызова (`row.get("label")`, `log.warning("…")`) и операнд сравнения
    (`match.kind == "ambiguous"`). Все три — имена полей и образцы состояния,
    и все три давали ложные находки на первом прогоне сборщика.
    """
    najdeno: set[int] = set()

    def pomet(uzel: ast.AST) -> None:
        for vnutri in ast.walk(uzel):
            if isinstance(vnutri, ast.Constant):
                najdeno.add(id(vnutri))

    for uzel in ast.walk(derevo):
        if isinstance(uzel, ast.Raise):
            # `raise ValueError("callback_data %r is %d bytes…")` — текст для
            # того, кто чинит код. Исключение, которое ПОКАЗЫВАЮТ дословно,
            # объявлено в `POKAZYVAYUT` и через этот отсев не проходит.
            vinovnik = uzel.exc
            imya = _imya_vyzova(vinovnik) if isinstance(vinovnik, ast.Call) else None
            if imya not in POKAZYVAYUT:
                pomet(uzel)
        elif isinstance(uzel, ast.Dict):
            for klyuch in uzel.keys:
                if klyuch is not None:
                    pomet(klyuch)
        elif isinstance(uzel, ast.Subscript):
            pomet(uzel.slice)
        elif isinstance(uzel, ast.Compare):
            pomet(uzel.left)
            for sravnenie in uzel.comparators:
                pomet(sravnenie)
        elif isinstance(uzel, ast.Call) and _imya_vyzova(uzel) in NE_TEKST_VYZOVY:
            for dovod in uzel.args:
                pomet(dovod)
            for klyuch in uzel.keywords:
                pomet(klyuch.value)
    return najdeno


def _kanal_b_funkcii(
    derevo: ast.AST,
    imena: dict[str, ast.AST],
    cherez_imya: dict[str, set[str]],
    izvne: set[str] = frozenset(),
) -> set[str]:
    """Функции файла, чей результат уходит на экран. Неподвижная точка.

    `izvne` — показывающие имена, найденные в других файлах: их вызов здесь
    тоже открывает экран.
    """
    pokazyvayushie: set[str] = set(izvne)
    rosli = True
    while rosli:
        rosli = False
        for uzel in ast.walk(derevo):
            if not isinstance(uzel, ast.Call):
                continue
            imya = _imya_vyzova(uzel)
            if imya in POKAZYVAYUT:
                pozicii = POKAZYVAYUT[imya]
            elif imya in pokazyvayushie:
                # Результат уже показывающей функции — тоже экран; текст в ней
                # стоит в любом аргументе, сузить нечем.
                pozicii = (tuple(range(len(uzel.args))), tuple(
                    k.arg for k in uzel.keywords if k.arg
                ))
            else:
                continue
            for vyrazhenie in _tekstovye_vyrazhenia(uzel, pozicii):
                for vnutri in ast.walk(vyrazhenie):
                    if isinstance(vnutri, ast.Call):
                        vlozhennoe = _imya_vyzova(vnutri)
                        if vlozhennoe in imena and vlozhennoe not in pokazyvayushie:
                            pokazyvayushie.add(vlozhennoe)
                            rosli = True
                    elif isinstance(vnutri, ast.Name) and vnutri.id in cherez_imya:
                        for vlozhennoe in cherez_imya[vnutri.id]:
                            if vlozhennoe in imena and vlozhennoe not in pokazyvayushie:
                                pokazyvayushie.add(vlozhennoe)
                                rosli = True

        # Эстафета вниз: показывающая функция возвращает не свои литералы, а
        # результат ещё одной. Так собран год ученика — `open_year` показывает
        # то, что вернул `_compose_year`, а тот возвращает `year_text`, и все
        # слова экрана лежат в третьей функции.
        for imya_f in sorted(pokazyvayushie & set(imena)):
            for shag in ast.walk(imena[imya_f]):
                if not isinstance(shag, ast.Return) or shag.value is None:
                    continue
                for vnutri in ast.walk(shag.value):
                    if isinstance(vnutri, ast.Call):
                        vlozhennye = {_imya_vyzova(vnutri)}
                    elif isinstance(vnutri, ast.Name):
                        vlozhennye = cherez_imya.get(vnutri.id, set())
                    else:
                        continue
                    for vlozhennoe in vlozhennye:
                        if vlozhennoe and vlozhennoe not in pokazyvayushie:
                            pokazyvayushie.add(vlozhennoe)
                            rosli = True
    return pokazyvayushie


def _cherez_imya(derevo: ast.AST) -> dict[str, set[str]]:
    """Переменная → функции, чей результат в неё кладут.

    Экран сплошь и рядом собирается в два хода: `text, markup = render(…)`,
    и только потом `_redraw(message, text, markup)`. Без этого шага канал B
    не видит ни одной таблицы подтверждения — а это два главных экрана
    завтрашнего занятия.
    """
    svyazi: dict[str, set[str]] = {}
    for uzel in ast.walk(derevo):
        if isinstance(uzel, ast.Assign):
            celi, znachenie = uzel.targets, uzel.value
        elif isinstance(uzel, ast.AnnAssign) and uzel.value is not None:
            celi, znachenie = [uzel.target], uzel.value
        else:
            continue
        istochniki = {
            _imya_vyzova(v)
            for v in ast.walk(znachenie)
            if isinstance(v, ast.Call) and _imya_vyzova(v)
        }
        if not istochniki:
            continue
        for cel in celi:
            for imya in ast.walk(cel):
                if isinstance(imya, ast.Name):
                    svyazi.setdefault(imya.id, set()).update(istochniki)
    return svyazi


def _fajly(koren: Path):
    """Пары «путь ОТ КОРНЯ репозитория, разобранное дерево»."""
    for papka in PAPKI:
        for put in sorted((koren / papka).rglob("*.py")):
            yield (
                put.relative_to(koren),
                ast.parse(put.read_text(encoding="utf-8"), filename=str(put)),
            )


def _pokazyvayushie_vsyudu(derevya: dict) -> set[str]:
    """Имена показывающих функций, собранные ПО ВСЕМ файлам сразу.

    Экран собирает один файл (`bot/keyboards/views.py`), а показывает другой
    (`bot/routers/views.py`), и внутри одного файла эта связь невидима.
    Имя — единственный мост, который у сканера есть: разрешать импорты
    по-настоящему значит писать половину интерпретатора. Цена приближения —
    одноимённая функция в чужом файле попадёт в охват лишней; цена точного
    разрешения — экраны клавиатур не проверяются вовсе.
    """
    obshie: set[str] = set()
    rosli = True
    while rosli:
        rosli = False
        for put, derevo in derevya.items():
            # 🔴 МОСТ ПО ИМЕНИ — ТОЛЬКО ВНУТРИ `bot/`. Экраны живут там, и там
            # одноимённая функция почти всегда та самая. В `core/` он тащил
            # ЧУЖОЕ: `reason` и `channels` разбора речи (`golos.py`) хранятся в
            # черновике, но ни одна из двух `render` их не печатает, а тексты
            # `RoomError` — это то, что читает журнал, тогда как человеку
            # показывается отдельное поле `told`. Оба ловились как нарушения,
            # которых нет.
            if put.parts[0] != "bot":
                continue
            imena = _funkcii(derevo)
            cherez = _cherez_imya(derevo)
            svoi = _kanal_b_funkcii(derevo, imena, cherez, obshie)
            novye = (svoi | (obshie & set(imena))) - obshie
            if novye:
                obshie |= novye
                rosli = True
    return obshie


def sobrat(koren: Path = KOREN, *, tolko_kanal_a: bool = False) -> list[dict]:
    """Все строки, доезжающие до человека, отсортированные по адресу."""
    najdeno: list[dict] = []
    derevya = {put: derevo for put, derevo in _fajly(koren)}
    obshie = set() if tolko_kanal_a else _pokazyvayushie_vsyudu(derevya)
    for put, derevo in derevya.items():
            adres = str(put)
            vidno: dict[tuple[int, str], dict] = {}

            # --- канал A: литерал прямо в текстовой позиции показа
            for uzel in ast.walk(derevo):
                if not isinstance(uzel, ast.Call):
                    continue
                imya = _imya_vyzova(uzel)
                if imya not in POKAZYVAYUT:
                    continue
                for vyrazhenie in _tekstovye_vyrazhenia(uzel, POKAZYVAYUT[imya]):
                    for stroka, tekst in _literaly(vyrazhenie):
                        if tekst.strip():
                            vidno.setdefault(
                                (stroka, tekst),
                                {"kanal": "A", "vyzov": imya},
                            )

            # --- канал B: литерал внутри функции, чей результат показывают
            if not tolko_kanal_a:
                imena = _funkcii(derevo)
                indeksy = _ne_tekst(derevo)
                cherez_imya = _cherez_imya(derevo)
                # Мост по имени действует только внутри `bot/` — там, где
                # живут экраны; см. `_pokazyvayushie_vsyudu`.
                izvne = obshie if put.parts[0] == "bot" else frozenset()
                svoi = _kanal_b_funkcii(derevo, imena, cherez_imya, izvne)
                for imya_f in sorted((svoi | izvne) & set(imena)):
                    for uzel in _vse_literaly_tela(imena[imya_f]):
                        if id(uzel) in indeksy or not uzel.value.strip():
                            continue
                        vidno.setdefault(
                            (uzel.lineno, uzel.value),
                            {"kanal": "B", "vyzov": imya_f},
                        )

            for (stroka, tekst), pro in vidno.items():
                najdeno.append(
                    {
                        "fajl": adres,
                        "stroka": stroka,
                        "kanal": pro["kanal"],
                        "vyzov": pro["vyzov"],
                        "tekst": tekst,
                    }
                )
    najdeno.sort(key=lambda z: (z["fajl"], z["stroka"], z["tekst"]))
    return najdeno


def main() -> int:
    razbor = argparse.ArgumentParser(description=__doc__)
    razbor.add_argument("--json", action="store_true", help="машинный вывод")
    razbor.add_argument(
        "--kanal",
        choices=("a", "ab"),
        default="ab",
        help="a — только прямой признак задания; ab — оба канала (по умолчанию)",
    )
    dovody = razbor.parse_args()

    najdeno = sobrat(tolko_kanal_a=dovody.kanal == "a")
    if dovody.json:
        json.dump(najdeno, sys.stdout, ensure_ascii=False, indent=1)
        print()
        return 0

    fajly: list[str] = []
    for zapis in najdeno:
        if zapis["fajl"] not in fajly:
            fajly.append(zapis["fajl"])
        print(
            "%s:%s · %s · %s() · %s"
            % (
                zapis["fajl"],
                zapis["stroka"],
                zapis["kanal"],
                zapis["vyzov"],
                zapis["tekst"],
            )
        )
    a = sum(1 for z in najdeno if z["kanal"] == "A")
    print()
    print(
        "строк, доезжающих до человека: %d, в %d файлах "
        "(прямых A: %d, через посредника B: %d)"
        % (len(najdeno), len(fajly), a, len(najdeno) - a)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
