#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-code — зовётся `veb/server.py::_peresobrat` после КАЖДОЙ
# успешной записи в базу, и руками при выкладке статики. Прежний контракт
# `called-by-hand` был верен ровно до появления сервера: снимок старел, пока база
# жила, и внешняя версия расходилась с внутренней.
"""Builds the SELF-CONTAINED static site, out of the sections it is cut into.

🔴 WHAT IS LEFT IN THIS FILE, AFTER THE CUT OF 2026-09-07. Three things, and
nothing else: the composition root `sobrat_html`, which asks each section for its
markup and hands the lot to the shell; the two machine locks that refuse to build
a page whose look has drifted; and `sobrat`, which writes the result to disk.
Every piece of markup now lives in the section that owns it:

    veb/obshchee/karkas.py       the shell, the stylesheet, the shared Kontekst
    veb/razdely/glavnaya.py      the front page, the dragon curve, the search
    veb/razdely/listki.py        the problem sheets
    veb/razdely/shkolniki.py     the pupils tab
    veb/razdely/prepodavateli.py the teachers tab
    veb/razdely/gruppy.py        one group tab
    veb/razdely/lichnaya.py      empty; the next position of the wave
    veb/razdely/konduit.py       empty; the next position of the wave

Before the cut all of that was one 1290-line function with twenty closures
sharing one scope, so every edit to any section opened this file and no two
people could work at once. The page this file builds is byte-for-byte the page it
built before the cut — that was the entire acceptance criterion of the cut.

Три страницы, меню из трёх пунктов строкой сверху (§1: «может быть, наверху, чтобы
ничего не выезжало»). Текст занимает весь экран.

Данные вмораживаются на момент сборки: Pages отдаёт статику, ей не нужен ни сервер,
ни база, и чтение переживает выключенный ноутбук — в этом смысл разделения (§7).

🔴 ПРЕЖДЕ ЧЕМ ПРАВИТЬ ЗДЕСЬ ЧТО-ЛИБО ПО ВИДУ СТРАНИЦЫ — ПРОЧИТАЙ
`doc/DIZAJN-ZAKREPLENO.md`. Заглавная переделывалась шесть раз за одну ночь и была
принята; её закон:

    Новые страницы делаются ОТ существующего дизайна.
    Существующие страницы НЕ переделываются под новые.

Два замка ниже в этом файле стерегут её машинно и зовутся из `sobrat()` на КАЖДОЙ
сборке: `proverit_karkas()` — гость и организатор побайтово один каркас;
`proverit_shemu()` — карточка ближайшего листка набрана одним весом и одним цветом.
Нарушил — страница не собралась, а значит и сохранение в админке не прошло.
Так и задумано: схему ломают не назло, а мимоходом.
"""
# Мак владельца несёт Python 3.9, сервер — 3.12. `list | None` в аннотации на 3.9
# исполняется и падает; с этим импортом аннотации не вычисляются вовсе, и один и
# тот же файл работает в обоих местах. Проверено запуском на обоих.
from __future__ import annotations

import pathlib
import sys
from functools import partial

KOREN = pathlib.Path(__file__).resolve().parent.parent
VYHOD = KOREN / "docs" / "index.html"

sys.path.insert(0, str(KOREN))
from veb.obshchee.karkas import (  # noqa: E402
    obolochka,
    razdel_raspredeleniya,
    sobrat_kontekst,
)
from veb.razdely import glavnaya, listki  # noqa: E402
from veb.razdely.listki import L8_PERVOE, L8_VTOROE, L9, est  # noqa: E402
from veb.razdely.gruppy import vkladka_gruppy  # noqa: E402
from veb.razdely.prepodavateli import vid_prepodavateli  # noqa: E402
from veb.razdely.shkolniki import vid_vse  # noqa: E402


def sobrat_html(rezhim: str = "gost", svodka: list | None = None,
                den: str | None = None) -> str:
    """Собирает страницу и ВОЗВРАЩАЕТ её. Один рендерер на все уровни доступа.

    🔴 ЗДЕСЬ ЖИВЁТ ГЛАВНОЕ РЕШЕНИЕ ЭТОГО ФАЙЛА: гость и организатор смотрят на
    страницу, порождённую ОДНИМ И ТЕМ ЖЕ кодом. Режим добавляет органы правки в
    те же места, где у гостя стоит текст, и НЕ трогает окружающую разметку.
    Пока рендерера было два — сайт и админка, — они разъезжались: расхождение
    видно было глазом на списке преподавателей, и «привести к похожему виду
    руками» лечило его ровно до следующей правки. Разъехаться нельзя, если код
    один; это и есть проверка «взять блок из гостевой и из админской и сверить».

    `rezhim`: `"gost"` — то, что лежит в `docs/index.html` и что видят все;
    `"admin"` — то же самое плюс выпадающие списки, счётчики и крестики.
    `svodka`: если передан список, в него дописываются строки отчёта сборки.
    """
    # `den` — страница ОДНОГО ЗАНЯТИЯ: те же вкладки, но на дату и одной колонкой.
    # Разделы «Класс» и «Листки» на ней не собираются: их расписание читает
    # `kt.DNI`, а он тут из одного дня (см. `karkas.sobrat_kontekst`).
    kt = sobrat_kontekst(rezhim, den=den)

    l9 = [f for _, _, vs in L9 for _, f in vs if est("listki", f)]
    l8 = [f for _, _, f in L8_PERVOE + L8_VTOROE if est("listki-8kl", f)]

    zhdut = [r for r in kt.shk if r["teacher_id"] not in kt.prep]

    if svodka is not None:
        svodka.append(f"  режим {rezhim} · школьников {len(kt.shk)} · преподавателей "
                      f"{len(kt.prep)} · ждут назначения {len(zhdut)}")
        svodka.append("  группы: " + " · ".join(f"{k}→{kt.kabinety.get(k,'—')}"
                                                for k in ("В", "Д", "Н")))
        svodka.append(f"  листки: 9кл {len(l9)} · 8кл {len(l8)}")

    # 🔴 THE SECTIONS ARE PASSED IN, NOT IMPORTED BY THE SHELL. This function is
    # the only place in the codebase that knows both that a shell exists and that
    # sections exist. `partial` binds the context once so the shell can call a
    # section with nothing but a day or a group code, exactly as the markup did
    # when the section was still a closure standing in this scope.
    return obolochka(
        kt,
        glavnaya="" if den else glavnaya.razdel(kt),
        listki="" if den else listki.razdel(kt),
        tolko_raspredelenie=bool(den),
        raspredelenie=razdel_raspredeleniya(
            kt,
            vid_vse=partial(vid_vse, kt),
            vid_prepodavateli=partial(vid_prepodavateli, kt),
            vkladka_gruppy=partial(vkladka_gruppy, kt),
        ),
        poisk_skript=glavnaya.poisk_skript(kt),
        drakon_skript=glavnaya.DRAKON_SKRIPT,
    )


# 🔴 ГВОЗДЬ. ГЕЙТ, КОТОРЫЙ НЕ ДАЁТ КАРКАСУ РАЗЪЕХАТЬСЯ.
#
# Требование владельца 06.09, дословно: «они должны быть склеены… это не должно
# различаться — мы не должны за этим следить, это должно быть прибито гвоздями».
# Следить и не надо: за этим следит машина, на каждой сборке.
#
# КАК ЭТО РАБОТАЕТ. Из страницы с ролью снимается всё, что добавлено
# ВОЗМОЖНОСТЬЮ, — и остаток обязан совпасть с гостевой страницей ПОБАЙТОВО.
# Снимается ровно три вещи, и список закрытый:
#   1. элементы с `data-org` — их у гостя нет вовсе (крестик, счётчик, поля);
#   2. `<select data-gost="X">…</select>` → `X` — орган правки, вставший на место
#      гостевого текста; сам текст он и несёт в `data-gost`, поэтому подстановка
#      механическая, а не догадка;
#   3. атрибуты из закрытого списка `ATRIBUTY_ORGANA` на общих элементах.
# Из гостевой снимаются элементы `data-tolko-gost` — то, что роль намеренно НЕ
# показывает (кабинет в списках школьников: тому, кто раскладывает людей, он не
# нужен, решение владельца).
#
# Что гейт НЕ проверяет и не должен: скрипты и кнопку входа/выхода. Это не каркас
# страницы, а её поведение.
import re as _re

# 🔴 ЗАКРЫТЫЙ СПИСОК, И КАЖДОЕ ИМЯ В НЁМ ЗАРАБОТАНО. Сюда попадает атрибут,
# который у роли ЕСТЬ, а у гостя на том же элементе НЕТ. `data-tid` здесь стоял
# и был убран: он висит на строке таблицы у ОБОИХ, и снятие его только с одной
# стороны само создавало расхождение — гейт поймал это на себе же.
ATRIBUTY_ORGANA = ("data-org", "data-gost", "data-snyat", "data-slot", "data-gruppa",
                   "data-sid", "data-data", "role", "tabindex")
# `title` в этот список НЕ входит и входить не должен: у чипа кабинета он общий
# и объясняет, откуда взят номер. Подсказка «открепить» живёт на крестике, то
# есть на элементе, которого у гостя нет вовсе, и снимается вместе с ним.


def _razdel_raspredeleniya(html: str) -> str:
    m = _re.search(r'<section class="str holst" id="s-rasp">.*?(?=\n<script>|\Z)',
                   html, _re.S)
    assert m, "раздел распределения не найден — гейт нечего сверять"
    return m.group(0)


def _ubrat_elementy(html: str, priznak: str) -> str:
    """Удалить каждый элемент, в открывающем теге которого есть `priznak`, целиком.

    🔴 РАЗБОР С БАЛАНСИРОВКОЙ, А НЕ РЕГУЛЯРКА. Регулярка здесь была и была неверна:
    нежадное `.*?</span>` останавливалось на ПЕРВОМ закрывающем теге и оставляло
    лишний, а вариант с оглядкой не брал вложенные одноимённые теги вовсе —
    `<span data-tolko-gost><span class="kab">…</span></span>` не удалялся никогда.
    Оба раза это поймал сам гейт на первом же прогоне, и оба раза он был прав.
    Вложенность тегов регулярными выражениями не разбирается — это её свойство,
    а не невезение.
    """
    out, i = [], 0
    while True:
        j = html.find("<", i)
        if j == -1:
            out.append(html[i:])
            return "".join(out)
        k = html.find(">", j)
        if k == -1:
            out.append(html[i:])
            return "".join(out)
        teg = html[j:k + 1]
        m = _re.match(r"<([a-zA-Z][\w-]*)", teg)
        if not m or priznak not in teg or teg.endswith("/>"):
            out.append(html[i:k + 1])
            i = k + 1
            continue
        # нашли открывающий тег с признаком — ищем ЕГО закрытие, считая вложенные
        imya = m.group(1)
        out.append(html[i:j])
        glubina, pos = 1, k + 1
        otkr = _re.compile(r"<" + imya + r"(?=[\s/>])", _re.I)
        zakr = "</" + imya + ">"
        while glubina and pos < len(html):
            sled_o = otkr.search(html, pos)
            sled_z = html.find(zakr, pos)
            if sled_z == -1:
                pos = len(html)
                break
            if sled_o and sled_o.start() < sled_z:
                glubina += 1
                pos = sled_o.end()
            else:
                glubina -= 1
                pos = sled_z + len(zakr)
        i = pos


def _snyat_organy(html: str) -> str:
    """Убрать из страницы всё, что добавила возможность. Больше ничего."""
    # 2. орган правки на месте гостевого текста — вернуть текст, который он несёт
    html = _re.sub(r'<select\b[^>]*\bdata-gost="([^"]*)"[^>]*>.*?</select>',
                   lambda m: m.group(1), html, flags=_re.S)
    # 1. элементы, которых у гостя нет вовсе
    html = _ubrat_elementy(html, "data-org=")
    # 3. атрибуты-надстройки на общих элементах
    for atr in ATRIBUTY_ORGANA:
        html = _re.sub(r'\s' + atr + r'="[^"]*"', "", html)
    return html


def _snyat_gostevoe(html: str) -> str:
    """То же самое с другой стороны: убрать то, что роль намеренно НЕ показывает."""
    return _ubrat_elementy(html, "data-tolko-gost")


def proverit_karkas(roli=("organizator",)) -> list:
    """Сверить каркас каждой роли с гостевым. Возвращает список расхождений.

    Пустой список — каркас един. Зовётся из `sobrat()` на каждой сборке, поэтому
    разъехаться незаметно нельзя: страница просто не соберётся.
    """
    gost = _snyat_gostevoe(_razdel_raspredeleniya(sobrat_html("gost")))
    bedy = []
    for rol in roli:
        s_rolyu = _snyat_organy(_razdel_raspredeleniya(
            sobrat_html("admin" if rol == "organizator" else rol)))
        if s_rolyu != gost:
            # назвать ПЕРВОЕ расхождение — по нему чинят, а не по факту «не равно»
            i = next((i for i in range(min(len(gost), len(s_rolyu)))
                      if gost[i] != s_rolyu[i]), min(len(gost), len(s_rolyu)))
            bedy.append(
                f"каркас роли «{rol}» разошёлся с гостевым на позиции {i}:\n"
                f"    гость: …{gost[max(0, i - 60):i + 60]!r}\n"
                f"    {rol}: …{s_rolyu[max(0, i - 60):i + 60]!r}")
    return bedy


# ── 🔒 ЗАМОК ВИЗУАЛЬНОЙ СХЕМЫ ЗАГЛАВНОЙ ─────────────────────────────────────
# Владелец 07.09: «дальше нужно эту визуальную схему максимально закрепить,
# чтобы её случайно не правили и не портили». Комментарий такого не удержит:
# схему ломают не назло, а мимоходом — дописав жирное слово или подкрасив
# ссылку. Поэтому она проверяется на каждой сборке, рядом с проверкой каркаса,
# и нарушение означает, что страница не собирается вовсе.
#
# Стережётся ровно то, что владелец назвал вслух: одна насыщенность и не более
# двух цветов на карточке ближайшего листка.
SHEMA_KARTOCHKI_ZAPRETY = (
    ("<b>", "жирное начертание"),
    ("<strong", "жирное начертание"),
    ('class="tihoe"', "приглушённый цвет"),
    ('class="net"', "служебный цвет"),
    ('class="gr"', "акцентный цвет"),
    ('class="kab"', "плашка"),
    ('class="ver"', "плашка версии"),
)


def _kartochka(html: str) -> str:
    """Кусок разметки между открытием и закрытием карточки листка."""
    n = html.find('<div class="blok-listok">')
    if n < 0:
        return ""
    k = html.find('<div class="blok-vedut">', n)
    return html[n:k if k > 0 else len(html)]


def proverit_shemu() -> list:
    """Сверить карточку листка с закреплённой схемой. Пустой список — цела."""
    bedy = []
    for rezhim in ("gost", "admin"):
        kusok = _kartochka(sobrat_html(rezhim))
        if not kusok:
            bedy.append(f"режим «{rezhim}»: карточка ближайшего листка исчезла")
            continue
        for obrazec, chem in SHEMA_KARTOCHKI_ZAPRETY:
            if obrazec in kusok:
                bedy.append(
                    f"режим «{rezhim}»: в карточке ближайшего листка появилось "
                    f"{chem} ({obrazec}). Схема закреплена: одна гарнитура, один "
                    f"кегль, одна насыщенность, один цвет на всё содержание.")
    return bedy


def sobrat(svodka: list | None = None) -> int:
    """Пишет ГОСТЕВУЮ страницу в `docs/index.html`. Зовётся руками и из сервера.

    \U0001f534 ПАДАЕТ ГРОМКО. Ни одного `except` вокруг: сервер зовёт эту функцию
    после каждой успешной записи в базу и обязан упасть вместе с ней. Тихая
    сборка вернула бы ровно то, от чего уходим, — новую базу при вчерашней
    странице, о которой никто не знает.
    """
    svodka = [] if svodka is None else svodka
    # 🔴 ГВОЗДЬ ЗАБИВАЕТСЯ ЗДЕСЬ, НА КАЖДОЙ СБОРКЕ. Каркас разъехался — страница
    # не собирается вовсе. Не предупреждение, не запись в лог: отказ. Владелец
    # 06.09: «мы не должны за этим следить, это должно быть прибито гвоздями».
    # Следить и не надо — не соберётся.
    bedy = proverit_karkas()
    if bedy:
        raise AssertionError(
            "каркас гостя и роли разошёлся — страница не собрана:\n" + "\n".join(bedy))
    svodka.append("  каркас: гость и организатор совпадают побайтово ✅")
    bedy = proverit_shemu()
    if bedy:
        raise AssertionError(
            "визуальная схема карточки нарушена — страница не собрана:\n"
            + "\n".join(bedy))
    svodka.append("  схема карточки: один вес, один цвет ✅")
    VYHOD.write_text(sobrat_html("gost", svodka), encoding="utf-8")
    print(f"собрано: {VYHOD}")
    for stroka in svodka:
        print(stroka)
    return 0


if __name__ == "__main__":
    sys.exit(sobrat())
