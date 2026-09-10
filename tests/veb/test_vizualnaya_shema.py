"""Замок визуальной схемы заглавной страницы.

Владелец 07.09, после четырёх заходов правок по одной и той же карточке:
«дальше нужно эту визуальную схему максимально закрепить, чтобы её случайно
не правили и не портили».

Схему уже стережёт `proverit_shemu()` внутри сборки — страница не соберётся,
если карточку усложнить. Этот файл держит сам замок: он проверяет, что замок
на месте, что он ловит нарушение и что закреплённые решения не отменены
мимоходом. Без него можно снять проверку из сборки и не заметить.
"""

from __future__ import annotations

import pytest

import config
from tools.sobrat_stranicu import (
    SHEMA_KARTOCHKI_ZAPRETY,
    _kartochka,
    proverit_shemu,
    sobrat_html,
)

# 🔴 ЭТИ ПРОВЕРКИ СМОТРЯТ НА ЖИВУЮ СТРАНИЦУ, А ЖИВАЯ СТРАНИЦА СОБИРАЕТСЯ ИЗ ЖИВОЙ
# БАЗЫ. Пока `data/spetsmat.db` лежала в репозитории, они были зелёными «сами
# собой» — и это была не проверка вёрстки, а проверка того, что в git лежит файл с
# записями 53 детей. Файл ушёл по решению владельца 10.09; источник теперь называет
# переменная среды, и без неё собирать нечего. Пропуск ЧЕСТНЕЕ зелёного: он говорит
# «не проверено», а не «проверено и хорошо».
try:
    _BAZA = config.DB_PATH
except SystemExit:
    _BAZA = None
pytestmark = pytest.mark.skipif(
    _BAZA is None or not _BAZA.is_file(),
    reason="источник не назван (%s) или названной базы нет на диске — "
           "живую страницу собирать не из чего" % config.BAZA_ENV)


def test_zhivaya_stranica_shemu_ne_narushaet():
    assert proverit_shemu() == []


def test_zamok_lovit_zhirnoe_slovo_v_kartochke():
    """Замок обязан ловить именно то, ради чего поставлен, а не молчать."""
    kusok = _kartochka(sobrat_html("gost")).replace(
        '<p class="listok-stroka">', '<p class="listok-stroka"><b>жирное</b>')
    najdeno = [chem for obrazec, chem in SHEMA_KARTOCHKI_ZAPRETY
               if obrazec in kusok]
    assert "жирное начертание" in najdeno


def test_v_kartochke_odna_nasyshchennost_i_odin_cvet():
    """Ни жирного, ни второго цвета в самих строках карточки.

    Владелец: «максимум два цвета. Либо всё жирное, либо всё нежирное».
    Два цвета — это серая подпись сверху (общий стиль подписей всех блоков)
    и основной цвет на всё остальное; в строках карточки цвет ровно один.
    """
    for rezhim in ("gost", "admin"):
        kusok = _kartochka(sobrat_html(rezhim))
        assert kusok, f"карточка ближайшего листка пропала в режиме {rezhim}"
        for obrazec, chem in SHEMA_KARTOCHKI_ZAPRETY:
            assert obrazec not in kusok, f"{rezhim}: {chem} ({obrazec})"


def test_ssylki_versij_ne_krasyatsya_akcentom():
    """Голубой на A/α/ℵ был четвёртым цветом на карточке из четырёх строк."""
    html = sobrat_html("gost")
    assert ".listok-ver a{color:inherit" in html


def test_na_zaglavnoj_stroki_ne_podsvechivayutsya():
    """Подсветка обещала нажатие, которого на заглавной нет."""
    html = sobrat_html("gost")
    assert "#s-start tr:hover td" in html
    assert "#s-start tr:hover td,#s-start tr:hover th{background:none}" in html


def test_listki_otkryvayutsya_s_devyatogo_klassa():
    html = sobrat_html("gost")
    assert '<input class="rd" type="radio" name="lst" id="l-9" checked>' in html
    assert '<input class="rd" type="radio" name="lst" id="l-8">' in html
