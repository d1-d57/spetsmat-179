#!/usr/bin/env python3
"""Дозаполнение файла-захода, собранного `bootstrap_zahod.py`, — одной командой.

    python3 dozapolnit_zahod.py <тема> --model opus \
        --kontekst <файл.md> --zadacha <файл.md>

ЗАЧЕМ ЭТОТ ФАЙЛ. Генератор оставляет в каждом заходе места вида `<...>`, и их
дозаполняет аналитик. В волне на шестнадцать позиций это шестнадцать раз одна
и та же ручная работа над файлом в 320 строк — то есть шестнадцать шансов
пропустить один плейсхолдер молча. Здесь она сведена к двум содержательным
кускам (контекст и задача), всё остальное выводится из самого файла.

ЧТО ДЕЛАЕТ, по шагам:

  1. ЗАМЕНЯЕТ СТАРТОВУЮ СТРОКУ. Генератор с `--dvizhok claude` вписывает
     `claude -p --model arn:aws:bedrock:...`. На этой машине Bedrock-доступа
     НЕТ (`ls -d ~/.aws` → нет, `env | grep -c '^AWS_'` → 0), и та же дверь
     сегодня в 07:07 убила пять платных позиций соседней волны за девять
     минут — снаружи это неотличимо от «заход думает». Ставится вызов
     `ZAPUSK-ZAHODA.sh <тема> <модель>`, а прежняя строка сохраняется
     ДОСЛОВНО в комментарии рядом, с причиной замены.

  2. ВПИСЫВАЕТ КОНТЕКСТ И ЗАДАЧУ из названных файлов.

  3. РАЗВОРАЧИВАЕТ ПЛЕЙСХОЛДЕРЫ ГИТ-ГИГИЕНЫ в полные пути. Зона берётся из
     самого захода (строка «**ЗОНА (можно менять):**»), а не из аргумента:
     два источника одной правды разъезжаются молча.
     🔴 Именно ПОЛНЫЕ пути, не префикс: префикс, не совпавший ни с чем, даёт
     зелёный гейт на несохранённой работе.

  4. ПЕЧАТАЕТ ОСТАТОК. Финальная строка — «незакрытых плейсхолдеров: N».
     Ноль обязателен только для тех, что заполняет аналитик; поля исполнителя
     (`## ОТЧЁТ`, `## ПЛАН`, `## ВОПРОСЫ`) остаются пустыми законно и в счёт
     не идут.

КОДЫ ВОЗВРАТА: 0 — дозаполнил · 1 — нашёл дефект (якорь не совпал, заход уже
дозаполнен) · 2 — позвали неверно (нет файла, нет аргумента).
"""
import argparse
import pathlib
import re
import sys

ARKA = pathlib.Path(__file__).resolve().parent
REPO = ARKA.parent.parent
ZAPUSK = ARKA / "ZAPUSK-ZAHODA.sh"

RC_OK, RC_DEFECT, RC_MISUSE = 0, 1, 2


def zona_iz_zahoda(t: str) -> str:
    """Зона — из самого файла-захода, чтобы источник правды был один."""
    m = re.search(r"\*\*ЗОНА \(можно менять\):\*\*\s*(.+?)\.\s*Всё вне", t)
    if not m:
        return ""
    # Пути приходят в бэктиках: `core/` `infra/` … — снимаем их.
    return " ".join(re.findall(r"`([^`]+)`", m.group(1)))


def zamenit(t: str, staroe: str, novoe: str, gde: str) -> str:
    n = t.count(staroe)
    if n != 1:
        print(f"❌ якорь «{gde}» встретился {n} раз, ждали 1", file=sys.stderr)
        raise SystemExit(RC_DEFECT)
    return t.replace(staroe, novoe)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tema")
    ap.add_argument("--model", required=True, help="opus | sonnet | openrouter/...:free")
    ap.add_argument("--kontekst", required=True, help="файл с абзацем КОНТЕКСТ")
    ap.add_argument("--zadacha", required=True, help="файл с телом секции ЗАДАЧА")
    a = ap.parse_args(argv)

    fajl = ARKA / f"kod_{a.tema}.md"
    if not fajl.exists():
        print(f"❌ нет файла-захода: {fajl}", file=sys.stderr)
        return RC_MISUSE
    for p in (a.kontekst, a.zadacha):
        if not pathlib.Path(p).exists():
            print(f"❌ нет файла: {p}", file=sys.stderr)
            return RC_MISUSE

    t = fajl.read_text(encoding="utf-8")
    if "ZAPUSK-ZAHODA.sh " + a.tema in t:
        print(f"❌ заход {a.tema} уже дозаполнен — повторный прогон затёр бы работу",
              file=sys.stderr)
        return RC_DEFECT

    zona = zona_iz_zahoda(t)
    if not zona:
        print("❌ не нашёл зону в самом заходе — дальше идти нельзя, "
              "полные пути взять неоткуда", file=sys.stderr)
        return RC_DEFECT

    # ── 1. стартовая строка ────────────────────────────────────────────────
    m = re.search(r"^```\npython3 \S+git_zona\.py worktree add " + re.escape(a.tema)
                  + r".*?\n```\n", t, re.S | re.M)
    if not m:
        print("❌ не нашёл стартовый блок генератора", file=sys.stderr)
        return RC_DEFECT
    staraya = m.group(0)
    t = t.replace(staraya, (
        "```\n"
        f"bash {ZAPUSK} {a.tema} {a.model}\n"
        "```\n"
        "🔴 **ЧЕМ ЭТА СТРОКА ОТЛИЧАЕТСЯ ОТ ТОЙ, ЧТО ПЕЧАТАЛ ГЕНЕРАТОР.**\n"
        "Генератор вписал `claude -p --model arn:aws:bedrock:…` — ARN application inference\n"
        "profile. На ЭТОЙ машине Bedrock-доступа НЕТ вовсе: ни `~/.aws/`, ни переменных `AWS_*`\n"
        "(замер 2026-09-02 08:22). Цена оплачена соседней волной 2026-09-02 07:07: пять платных\n"
        "позиций из пяти оборвались за девять минут с «Could not load credentials from any\n"
        "providers», и снаружи это неотличимо от «заход думает». `ZAPUSK-ZAHODA.sh` берёт модель\n"
        "вторым аргументом и сам выбирает маршрут; добор — тем же вызовом с `--dobor`.\n"
        "\n"
        "<!-- прежняя строка генератора, сохранена дословно, НЕ исполнять:\n"
        + staraya.replace("```", "") + "-->\n"))

    # ── 2. контекст и задача ───────────────────────────────────────────────
    t = zamenit(
        t,
        "КОНТЕКСТ. <проект в 1–2 фразы>. Прошлый этап: <состояние>. ЦЕЛЬ: <что закрыть>.\n"
        "Приёмка — по ОТЧЁТУ, без построчной сверки. <Если стоп до цели: получишь X, но НЕ Y.>",
        pathlib.Path(a.kontekst).read_text(encoding="utf-8").strip(),
        "КОНТЕКСТ")

    m = re.search(r"^Конкретные шаги — у автора\. \*\*КРИТЕРИЙ ГОТОВНОСТИ.*?$", t, re.M)
    if not m:
        print("❌ не нашёл строку-заглушку критерия готовности в §2", file=sys.stderr)
        return RC_DEFECT
    t = t.replace(m.group(0), pathlib.Path(a.zadacha).read_text(encoding="utf-8").strip())

    # ── 3. плейсхолдеры гит-гигиены ────────────────────────────────────────
    pary = [
        ("for R in <репозитории, которых ты касался>; do", f"for R in {REPO}; do"),
        # 🔴 ФЛАГ ПОВТОРЯЕТСЯ, А НЕ СКЛЕИВАЕТСЯ. Находка захода P1 (отчёт 02.09
        # 09:39): у `vlit-v-osnovnuyu` флаг `--zone` объявлен `action="append"`,
        # и `in_zone()` берёт КАЖДОЕ значение как ОДИН префикс. Строка
        # `--zone "core/ infra/ tests/"` не может совпасть ни с чем: такого пути
        # нет. Слияние отказало на полностью корректном дереве, а в отказе
        # перечислило файлы своей же зоны — читается как «унёс чужое».
        ("--zone <своя зона> \\",
         " ".join(f'--zone "{z}"' for z in zona.split()) + " \\"),
        # 🔴 У `check` флаг `--zone` НЕ append: он берёт ОДИН префикс. Список
        # путей одной строкой не совпадёт ни с чем и даст ЗЕЛЁНОЕ на
        # несохранённой работе — ровно «зона-префикс даёт ложно-зелёное».
        # Поэтому — по вызову на путь.
        ('git_zona.py check --zone <зона>',
         (' && \\\n    '.join(
             f'git_zona.py check --zone "{z}"' for z in zona.split()))),
        ('commit -m "<зона>: <что сделано>"', 'commit -m "<что сделано>"'),
    ]
    for staroe, novoe in pary:
        if staroe in t:
            t = t.replace(staroe, novoe)

    fajl.write_text(t, encoding="utf-8")

    # ── 4. остаток ─────────────────────────────────────────────────────────
    # Поля исполнителя законно пусты — считаем только то, что заполняет аналитик.
    hvost = t.split("## УРОКИ ФАБРИКЕ")[0]
    ost = re.findall(r"<[а-яА-ЯёЁ][^>\n]{3,}>", hvost)
    print(f"✅ {fajl.name}: стартовая строка заменена, контекст и задача вписаны, "
          f"зона развёрнута в полные пути")
    print(f"   зона: {zona}")
    for o in sorted(set(ost)):
        print(f"   осталось: {o}")
    print(f"незакрытых плейсхолдеров: {len(set(ost))}")
    return RC_OK


if __name__ == "__main__":
    sys.exit(main())
