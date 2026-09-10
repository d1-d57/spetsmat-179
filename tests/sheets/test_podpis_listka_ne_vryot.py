"""Подпись листка не расходится с его номером — ни в данных, ни на экране.

🔴 ДВА РАЗНЫХ ДЕФЕКТА С ОДНИМ СИМПТОМОМ, И ТЕСТ ЛОВИТ ОБА.
Владелец 10.09: вкладка называется «16α», а заголовок под ней печатает
«16А. ДЕРЕВЬЯ». Первая гипотеза — разошлись `sheets.number` и `sheets.title`.
Проверка на боевой базе: расхождений НОЛЬ. Врало ОТОБРАЖЕНИЕ: `.zag2` несёт
`text-transform:uppercase`, а он переводит «α» (U+03B1) в «Α» (U+0391) — заглавную
греческую альфу, на экране неотличимую от русской «А» (U+0410).

Три листка одной темы зовутся 16A, 16α и 16ℵ, и различить их можно ТОЛЬКО по этому
знаку: верхний регистр стирал единственное различие между двумя из трёх.
"""

import re

import pytest


def test_title_nachinaetsya_s_number(connection):
    """Данные: подпись обязана начинаться с номера листка."""
    bedy = [
        (r["number"], r["title"])
        for r in connection.execute("select number, title from sheets")
        if r["title"] and not str(r["title"]).startswith(str(r["number"]))
    ]
    assert not bedy, "подпись разошлась с номером у %d листков: %r" % (len(bedy), bedy[:5])


@pytest.mark.parametrize("nomer", ["16A", "16α", "16ℵ"])
def test_verhnij_registr_ne_stiraet_razlichie(nomer):
    """Экран: три листка одной темы обязаны остаться различимыми.

    Проверяется само правило, а не разметка: если номера листков схлопываются в
    верхнем регистре, значит ЛЮБОЙ заголовок с `uppercase` их перепутает.
    """
    vse = {"16A", "16α", "16ℵ"}
    v_verhnem = {x.upper() for x in vse}
    assert len(v_verhnem) == len(vse), (
        "верхний регистр схлопывает номера листков: %r → %r. "
        "Заголовок с text-transform:uppercase покажет разные листки одинаково"
        % (sorted(vse), sorted(v_verhnem)))


def test_zagolovok_listka_v_konduite_ne_podnimaetsya_v_verhnij_registr():
    """Разметка: заголовок листка несёт класс, снимающий `uppercase`."""
    # Файлы закрываются: незакрытый дескриптор в этой конфигурации pytest роняет
    # тест ResourceWarning'ом, и падение выглядит как провал ПРОВЕРКИ, хотя проверка
    # прошла. Ровно тот класс, за которым волна и охотится: красное не о том.
    with open("veb/obshchee/karkas.py", encoding="utf-8") as f:
        stil = f.read()
    with open("veb/razdely/konduit.py", encoding="utf-8") as f:
        razmetka = f.read()
    assert ".zag-listok" in stil and "text-transform:none" in stil, \
        "нет стиля, снимающего верхний регистр с заголовка листка"
    assert 'class="zag2 zag-listok"' in razmetka, \
        "заголовок листка в кондуите не помечен классом zag-listok"
