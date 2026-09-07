#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-code — rendered by `tools/sobrat_stranicu.sobrat_html`.
"""The problem sheets: which ones exist on disk, and the page that lists them.

A sheet is on the page if, and only if, its file is on disk — nothing here is
written down twice. `tekushchij()` answers the one question the front page
asks of this section: which sheet is the one being solved right now.

It is handed `kt: Kontekst` and reads it; it opens no database and
imports no shell. What that buys is the point of the whole cut: this
file can be edited while somebody else edits the file next to it.

🔴 THE RUSSIAN COMMENTS BELOW ARE NOT TRANSLATED, ON PURPOSE. They carry the
owner's own words with the dates he said them on — "Владелец 06.09: …" — and a
translation would be a rewrite of evidence. Everything newly written here is in
English, as the задание requires; everything moved is verbatim, down to the
byte. That is also what makes the byte criterion of this refactor meaningful:
a diff between the page before and the page after can only show a mistake,
never a paraphrase.
"""
from __future__ import annotations

import pathlib

from veb.obshchee.karkas import e


KOREN = pathlib.Path(__file__).resolve().parent.parent.parent
# 🔴 ЛИСТКИ ИЩУТСЯ ТАМ, КУДА ВЕДУТ ССЫЛКИ. Было `KOREN.parent / "materials" /
# "spetsmat-2026"` — СОСЕДНИЙ репозиторий на маке владельца, которого на сервере
# нет вовсе (`ls /opt/materials` → No such file or directory). Ссылки при этом
# всегда были относительные, вида `href="listki/16A-derevya.pdf"`, то есть от
# `docs/`. Пока сборку звали руками с мака, расхождение не проявлялось; первая же
# пересборка на сервере вычистила бы обе таблицы листков молча — проверка
# существования файла не находила бы НИ ОДНОГО.
MAT = KOREN / "docs"


# ── ЛИСТКИ ────────────────────────────────────────────────────────────────
# Номер и название по СМЫСЛУ, а не имя файла. Ведущие нули убраны, слово
# «ДРАФТ» снято: это готовая версия, а не черновик (слова владельца 04.09).
# Зачёт стоит ПОСЛЕ листка 10 — им заканчивалось первое полугодие.
# Числа Фибоначчи не выдавались вовсе, поэтому их на странице нет.
L8_PERVOE = [
    ("1",  "Постепенно, с первого шага",       "01_Постепенно, с первого шага.pdf"),
    ("2",  "Правило суммы и произведения",     "02_Правило суммы и произведения.pdf"),
    ("3",  "Пары и тройки",                    "03_Пары и тройки.pdf"),
    ("4",  "Ещё раз про сложение и умножение", "04_Еще раз про сложение и умножение.pdf"),
    ("5",  "Биекции",                          "05_Биекции.pdf"),
    ("6",  "Графы",                            "06_Графы.pdf"),
    ("7",  "Множества",                        "07_Множества.pdf"),
    ("8",  "Зоопарк теории графов",            "08_Зоопарк теории графов.pdf"),
    ("9",  "Индукция",                         "09_Индукция.pdf"),
    ("10", "Биномиальные коэффициенты",        "10_Биномиальные коэффициенты.pdf"),
    ("",   "Программа зачёта",                 "Программа зачета.pdf"),
    ("Д1", "Информация",                       "д01_Информация.pdf"),
    ("Д2", "Геометрическое суммирование",      "д02_Геометрическое суммирование.pdf"),
]
L8_VTOROE = [
    ("11", "Соответствия",  "11_Соответствия.pdf"),
    ("12", "Делимость",     "12_Делимость.pdf"),
    ("13", "Остатки",       "13_Остатки.pdf"),
    ("14", "ОТА",           "14_ОТА.pdf"),
    ("15", "Бесконечность", "15_Бесконечность.pdf"),
    ("Д3", "Игры",          "д03_Игры.pdf"),
]
# 9 класс: одна ТЕМА, три версии в одну строку слева направо — A · α · ℵ.
L9 = [("16", "Деревья", [("A", "16A-derevya.pdf"),
                         ("α", "16α-derevya.pdf"),
                         ("ℵ", "16ℵ-derevya.pdf")])]



def est(papka, fajl):
    return (MAT / papka).joinpath(fajl).is_file()


def stroki_8(spisok, papka):
    out = []
    for nom, nazv, fajl in spisok:
        if not est(papka, fajl):
            continue
        out.append(f'<tr><td class="nom">{e(nom)}</td>'
                   f'<td><a href="{papka}/{e(fajl)}">{e(nazv)}</a></td></tr>')
    return "".join(out)


def stroki_9():
    out = []
    for nom, tema, versii in L9:
        live = [(z, f) for z, f in versii if est("listki", f)]
        if not live:
            continue
        ssylki = " ".join(
            f'<a class="ver" href="listki/{e(f)}">{e(z)}</a>' for z, f in live)
        out.append(f'<tr><td class="nom">{e(nom)}</td>'
                   f'<td>{e(tema)}</td><td class="verstroka">{ssylki}</td></tr>')
    return "".join(out)


# 🔴 ТЕКУЩИЙ ЛИСТОК — САМОЕ ПОЛЕЗНОЕ, ЧТО ЗДЕСЬ МОЖЕТ СТОЯТЬ. Школьник заходит
# узнать, что решать; всё остальное на главной он уже знает. Берётся ПОСЛЕДНИЙ
# листок девятого класса, у которого есть хоть один файл на диске, — то есть
# тот, что выдан. Ни одного файла нет — блока нет вовсе, а не пустая рамка.
def tekushchij():
    """Номер, тема и живые версии текущего листка — тремя кусками.

    🔴 ОТДАЁТ КУСКИ, А НЕ ГОТОВЫЙ БЛОК. Раньше функция возвращала целую
    вёрстку, и собрать из неё другую композицию было нельзя, не переписав
    функцию. Теперь она отвечает за ДАННЫЕ (какой листок сейчас выдан и
    какие его версии лежат на диске), а как их разложить — дело шаблона.
    """
    for nom, tema, versii in reversed(L9):
        zhivye = [(z, f) for z, f in versii if est("listki", f)]
        if zhivye:
            return nom, tema, zhivye
    return None, None, []


# 🔴 СРОК ВЫВОДИТСЯ, А НЕ ХРАНИТСЯ — И ЭТО РЕШЕНИЕ ПРОЕКТА, НЕ ЭКОНОМИЯ.
# `doc/model.md:38`: «Дедлайн листка наступает в момент выдачи следующего».
# `doc/arhitektura.md:40`: «дедлайн листка есть выдача следующего, это свойство
# данных, а не режим». Колонки `deadline` в `sheets` поэтому нет, и заводить её
# значило бы молча отменить записанное решение — а не добавить поле.
#
# Следующий листок выдаётся на занятии, то есть срок текущего — ближайшее
# занятие. Его дата уже стоит первой строкой карточки (`.listok-kogda`), и
# второй раз она здесь НЕ называется: «второе упоминание — то самое повторение,
# от которого мы избавляемся по всему сайту» (`glavnaya.py`, про список
# принимающих). Строка называет срок и опирается на дату строкой выше.
SROK_TEKST = "сдать на этом занятии"


def srok() -> str:
    """The current sheet's deadline in words, or "" when no sheet is out.

    🔴 RETURNS "" RATHER THAN A PLACEHOLDER, ON PURPOSE. The card is under the
    machine lock of `proverit_shemu()`, and the neighbouring `kab_skoro()` shows
    exactly what must not be copied: on unknown data it emits
    `<span class="net">кабинеты уточняются</span>` — a forbidden pattern that
    would refuse the build, and with it the admin's ability to save. No data
    here means no line at all, not a line saying there is no data.
    """
    _, tema, _ = tekushchij()
    return SROK_TEKST if tema else ""


def razdel(kt) -> str:
    """The whole sheets page: eighth class in two columns, ninth class open first."""
    return f"""<section class="str holst" id="s-list">
  <!-- Открывается девятый класс: он сейчас идёт. Владелец: «листки должны
       открываться по умолчанию не с 8 класса, а сразу с 9». -->
  <input class="rd" type="radio" name="lst" id="l-8">
  <input class="rd" type="radio" name="lst" id="l-9" checked>
  <div class="tabbar"><label for="l-8">8 класс</label><label for="l-9">9 класс</label></div>
  <section class="vid" id="w-8">
    <div class="dva-listka">
      <div>
        <p class="polug">первое полугодие</p>
        <table class="listki"><tbody>{stroki_8(L8_PERVOE, "listki-8kl")}</tbody></table>
      </div>
      <div>
        <p class="polug">второе полугодие</p>
        <table class="listki"><tbody>{stroki_8(L8_VTOROE, "listki-8kl")}</tbody></table>
      </div>
    </div>
  </section>
  <section class="vid" id="w-9">
    <table class="listki"><tbody>{stroki_9()}</tbody></table>
  </section>
</section>"""
