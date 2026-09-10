"""РЫЧАГ КАНОНА «НЕЛЬЗЯ СМЕШИВАТЬ»: одна клетка — один смысл, один признак — один носитель.

ЗАЧЕМ ЭТОТ ФАЙЛ СУЩЕСТВУЕТ.  Владелец сформулировал правило дословно: «есть простая мысль,
которая всегда проявляется: **нельзя смешивать**» (`TZ-DOBOR-10-09.md` §Q4).  Оно того же
рода, что «никогда по центру не центрируем», и у того правила рычаг уже есть — проверка
центрирования на тринадцати экранах.  У «нельзя смешивать» рычага не было, и потому оно
возвращалось: к 10.09 живых нарушений было ДВА сразу — инициалы принимающего надстрочником
в клетке с фамилией школьника, и подсветка строки, несущая одновременно «мой школьник» и
«сдал все обязательные».  Оба чинились правками O1–O3, и без этого файла они чинились бы
ровно до следующего раза, когда кому-нибудь снова понадобится «показать ещё один признак».

🔴 ПРАВИЛО СФОРМУЛИРОВАНО УЗКО И ПО МЕСТУ, И ЭТО ТРЕБОВАНИЕ САМОГО §Q4: «формулировать узко
и по месту, широкое правило здесь даст ложно-красные».  Поэтому судится РЕШЁТКА КОНДУИТА, а
не «таблицы сайта вообще»: у решётки есть закрытый список столбцов, каждый со своим
объявленным смыслом, и вопрос «что ещё влезло в эту клетку» имеет здесь однозначный ответ.
Личная карточка школьника, гробарий и распределение этим файлом не судятся — там столбцы
другие, и общее правило поверх них выдало бы красное на верной вёрстке.

ЧТО ИМЕННО ЛОВИТСЯ — ТРИ ВОПРОСА, КАЖДЫЙ СО СВОИМ СПОСОБОМ СЛОМАТЬСЯ:

  1. **Строка несёт больше одного признака.**  Так было до 10.09: `moi` и `gotov` стояли
     вместе, и прежняя редакция кода считала это достоинством («два признака СКЛАДЫВАЮТСЯ»).
  2. **В клетке живёт второй носитель.**  Так было с инициалами: `<td class="kto">` держал
     и фамилию, и инициалы принимающего надстрочником.
  3. **Один признак нарисован двумя средствами сразу.**  Самый тихий из трёх: «сдал всё
     обязательное» выражалось И фоном строки, И подложкой счётчика — снимешь одно, второе
     останется, и жалоба владельца вернётся при зелёном гейте.

Судится РЕНДЕР, собранный тем же вызовом, каким его собирает сайт (`konduit.razdel`), плюс
таблица стилей того же раздела (`konduit.stili`) — третий вопрос живёт в CSS и в разметке
не виден вовсе.
"""

from __future__ import annotations

import re

import pytest

from core.models import CellState
from tests.conftest import seed_world
from veb.obshchee.karkas import Kontekst
from veb.razdely import konduit


#: Тот же листок, что и у соседнего файла величин: две обязательные, одна письменная
#: (обязательная тоже), звезда и обычная.
LISTOK = ("обязательная", "обязательная", "письменная", "звезда", "обычная")

#: Колонки живой базы, которых не создают миграции (см. тот же список и то же объяснение в
#: `test_konduit_velichiny.py`): без них рендер падает на запросе принимающего.
ZHIVYE_KOLONKI = (
    "alter table teachers add column kabinet text",
    "alter table teachers add column aktiven integer not null default 1",
    "alter table teachers add column gruppa text",
    "alter table students add column gruppa text",
)

#: Классы строки, которые кондуит вправе ставить, и признак, который каждый из них несёт.
#: 🔴 ЭТО СПИСОК РАЗРЕШЁННОГО, А НЕ СПИСОК ЗАПРЕЩЁННОГО, и в этом вся сила проверки:
#: признак, добавленный завтра, красный по умолчанию, пока кто-нибудь не впишет его сюда
#: вместе с ответом на вопрос «а какой признак он вытесняет».
PRIZNAKI_STROKI = {"moi": "чей это ребёнок", "chuzh": "чей это ребёнок"}

#: Столбцы решётки и то единственное, что каждый из них значит.
SMYSL_STOLBCA = {
    "kto": "кто этот школьник",
    "pr": "кто у него принимает",
    "sch": "сколько обязательных сдано из скольких",
    "gt": "закрыл ли он всё, что должен",
}


@pytest.fixture
def mir(connection):
    for zapros in ZHIVYE_KOLONKI:
        connection.execute(zapros)
    return seed_world(connection, students=5, sheets=(LISTOK,))


def kontekst(connection, prepod_id=None) -> Kontekst:
    return Kontekst(rezhim="admin", rol="organizator", mogu=frozenset(), c=connection,
                    DNI={}, kabinety_dnya={}, otkuda_kabinet={}, kabinety={}, gruppy={},
                    prep={}, prepod_id=prepod_id)


@pytest.fixture
def vse_priznaki_srazu(mir, connection, marking, monkeypatch):
    """Мир, в котором ВСЕ признаки строки горят одновременно — иначе судить нечего.

    Первый школьник: ребёнок смотрящего преподавателя, закрыл все обязательные листка,
    принимающий назначен.  Именно на таком школьнике смешивание и происходило: пока
    признак один, любая раскладка выглядит чистой.

    День занятия назван явно: «мой школьник» считается по СЕГОДНЯШНЕМУ дню, и в пятницу
    таких нет ни у кого (`veb/razdely/lichnaya.deti_na_datu` на дне без слота отвечает
    пустым списком).  Без этой строки проверка была бы зелёной пять дней в неделю по
    той причине, что судить было нечего.
    """
    monkeypatch.setattr(konduit, "segodnya", lambda: "2026-09-14")   # понедельник
    zadachi = mir.problems_by_sheet[mir.sheet_ids[0]]
    for zadacha in zadachi[:3]:
        marking.set_state(mir.student_ids[0], zadacha, CellState.SOLVED, source="кнопка")
    prepod = mir.teacher_ids[0]
    for slot in (1, 2):
        connection.execute(
            "insert into enrollment (student_id, teacher_id, room, slot, valid_from) "
            "values (?, ?, ?, ?, ?)",
            (mir.student_ids[0], prepod, "303", slot, "2020-01-01"))
    connection.commit()
    return mir, prepod


def stroki_reshotki(html: str) -> list:
    """Все строки школьников решётки: `(классы строки, разметка строки)`.

    Берутся только `<tbody>` панелей решётки (`table class="kond"`) — шапка и таблицы
    личной карточки сюда не попадают по построению.
    """
    out = []
    for tablica in re.findall(r'<table class="kond"[^>]*>(.*?)</table>', html, re.S):
        telo = re.search(r"<tbody>(.*?)</tbody>", tablica, re.S)
        if not telo:
            continue
        for stroka in re.findall(r"<tr([^>]*)>(.*?)</tr>", telo.group(1), re.S):
            klassy = re.search(r'class="([^"]*)"', stroka[0])
            out.append(((klassy.group(1).split() if klassy else []), stroka[1]))
    return out


def kletki(razmetka: str) -> list:
    """Клетки строки: `(класс клетки, содержимое)`, в порядке слева направо."""
    return [(m.group(1) or "", m.group(2))
            for m in re.finditer(r'<td(?: class="([^"]*)")?[^>]*>(.*?)</td>',
                                 razmetka, re.S)]


# ── САМИ ПРОВЕРКИ, ОТДЕЛЬНО ОТ ТЕСТОВ ─────────────────────────────────────────────
# 🔴 ЧЕТЫРЕ ФУНКЦИИ НИЖЕ ВОЗВРАЩАЮТ СПИСОК НАРУШЕНИЙ, А НЕ ПАДАЮТ САМИ, И ЭТО НЕ СТИЛЬ.
# Рычаг обязан быть ДОКАЗУЕМ: «проверка есть» и «проверка ловит» — разные утверждения, и
# первое зелено даже тогда, когда второе ложно (замер соседнего гейта вёрстки, 10.09:
# `<select>` был исключён из проверки обрезки, гейт печатал «обрезка 0» по тринадцати
# экранам, а владелец жаловался на обрезку четвёртый раз).  Поэтому каждая проверка —
# функция, и в конце файла стоит САМОПРОВЕРКА: разметка ломается нарочно, и проверка
# обязана покраснеть на ней.


def narusheniya_stroki(html: str) -> list:
    """Строка несёт больше одного признака — или признак, который никто не объявлял."""
    plohie = []
    for klassy, _razmetka in stroki_reshotki(html):
        lishnie = [k for k in klassy if k not in PRIZNAKI_STROKI]
        if lishnie:
            plohie.append("строка несёт необъявленный класс: %s" % lishnie)
            continue
        priznaki = {PRIZNAKI_STROKI[k] for k in klassy}
        if len(priznaki) > 1:
            plohie.append("строка несёт два признака сразу: %s" % sorted(priznaki))
    return plohie


def narusheniya_stilej(stili: str) -> list:
    """Строку красит класс, который признаком строки не объявлен."""
    klassy = set(re.findall(r"#s-kond \.kond tbody tr\.([a-z-]+)", stili))
    return ["строку красит необъявленный признак: %s" % k
            for k in sorted(klassy - set(PRIZNAKI_STROKI))]


def narusheniya_kletok(html: str) -> list:
    """В клетке живёт второй носитель данных."""
    plohie = []
    for _klassy, razmetka in stroki_reshotki(html):
        for klass, soderzhimoe in kletki(razmetka):
            imya = klass.split()[0] if klass else ""
            if imya not in SMYSL_STOLBCA:
                continue                     # клетка задачи: её судят другие файлы
            nositeli = re.findall(r"<(i|b|span|label)\b", soderzhimoe)
            # `<b>` — фамилия, `<label>` — та же фамилия как кнопка перехода: оба про
            # ОДНО, кто этот школьник.  `<i>` в этой клетке и был вторым носителем.
            if imya == "kto" and "i" in nositeli:
                plohie.append("в клетке фамилии второй носитель: %r" % soderzhimoe)
            if imya == "gt" and nositeli:
                plohie.append("в столбце галочки нарисовано ещё что-то: %r" % soderzhimoe)
    return plohie


def narusheniya_znaka(html: str) -> list:
    """Знак «закрыл всё» стоит не в своём столбце — или не стоит нигде."""
    plohie, goryat = [], 0
    for _klassy, razmetka in stroki_reshotki(html):
        for klass, soderzhimoe in kletki(razmetka):
            imya = klass.split()[0] if klass else ""
            if imya == "gt":
                goryat += "\u2713" in soderzhimoe
            elif imya in ("kto", "pr", "sch") and "\u2713" in soderzhimoe:
                plohie.append("знак «закрыл всё» в столбце «%s» (его смысл — «%s»)"
                              % (imya, SMYSL_STOLBCA[imya]))
    if not goryat:
        plohie.append("галочка не горит нигде — проверять нечего, и это тоже красное")
    return plohie


# ---------------------------------------- вопрос 1: строка несёт один признак


def test_a_row_carries_at_most_one_priznak(vse_priznaki_srazu, connection):
    """Строка, у которой признаков два, — это и есть жалоба владельца 10.09 дословно.

    Мир построен так, что у первого школьника ОБА прежних признака истинны сразу: он
    и «мой», и закрыл все обязательные.  До правки его строка несла `moi gotov`.
    """
    _mir, prepod = vse_priznaki_srazu
    html = konduit.razdel(kontekst(connection, prepod_id=prepod))
    assert stroki_reshotki(html), "решётка вообще нарисована"
    assert narusheniya_stroki(html) == [], narusheniya_stroki(html)


def test_the_stylesheet_paints_a_row_from_one_priznak_only(mir, connection):
    """Третий вопрос: признак, выраженный ДВУМЯ средствами, в разметке не виден.

    Правило `tbody tr.<класс>` в таблице стилей — это и есть «строка что-то значит».
    Список разрешённых классов закрыт: новый признак, покрасивший строку, краснеет здесь
    ДО того, как кто-нибудь посмотрит на экран.
    """
    stili = konduit.stili(kontekst(connection))
    assert narusheniya_stilej(stili) == [], narusheniya_stilej(stili)


# ------------------------------------- вопрос 2: в клетке один носитель данных


def test_every_cell_of_the_grid_carries_exactly_one_thing(vse_priznaki_srazu, connection):
    """«Агаркова Ирина ᴰ·ᴱ·» — вот как выглядит нарушение, из-за которого файл написан.

    Клетка фамилии обязана нести фамилию и имя, и ничего кроме: ни инициалов
    принимающего, ни галочки, ни счётчика.  Проверяется формой — по вложенным узлам,
    а не по словам: второй носитель это всегда отдельный элемент.
    """
    _mir, prepod = vse_priznaki_srazu
    html = konduit.razdel(kontekst(connection, prepod_id=prepod))
    assert narusheniya_kletok(html) == [], narusheniya_kletok(html)


def test_the_sign_of_closing_everything_lives_in_one_column_and_no_other(
    vse_priznaki_srazu, connection
):
    """Один признак — один носитель, проверенный по САМОМУ ЗНАКУ, а не по классам.

    Галочка, продублированная в клетке фамилии или в счётчике «чтобы заметнее», — это
    то же смешивание, только добавленное из добрых побуждений.
    """
    _mir, prepod = vse_priznaki_srazu
    html = konduit.razdel(kontekst(connection, prepod_id=prepod))
    assert narusheniya_znaka(html) == [], narusheniya_znaka(html)


# ─────────────────────────── САМОПРОВЕРКА: рычаг обязан КРАСНЕТЬ ───────────────────────
# Каждое нарушение ломается ровно так, как оно стояло на живой странице до 10.09, и
# проверка обязана его назвать.  Без этих четырёх тестов файл выше доказывает только то,
# что проверка НАПИСАНА.


def test_samoproverka_row_with_two_priznaki_goes_red(vse_priznaki_srazu, connection,
                                                     monkeypatch):
    """Ровно прежняя редакция `_klass_stroki`: «мой» и «закрыл» на одной строке."""
    _mir, prepod = vse_priznaki_srazu
    monkeypatch.setattr(konduit, "_klass_stroki",
                        lambda u, chuzhoj: ' class="moi gotov"')
    html = konduit.razdel(kontekst(connection, prepod_id=prepod))
    plohie = narusheniya_stroki(html)
    assert plohie, "рычаг не увидел строку с двумя признаками"
    assert "необъявленный класс" in plohie[0], plohie[0]


def test_samoproverka_a_second_row_colour_in_the_stylesheet_goes_red():
    """Прежнее правило `tbody tr.gotov td{background:var(--chip)}`, слово в слово."""
    slomannye = "#s-kond .kond tbody tr.gotov td{background:var(--chip)}"
    assert narusheniya_stilej(slomannye), "рычаг не увидел второй крашеный признак"


def test_samoproverka_initials_back_inside_the_surname_cell_go_red(
    vse_priznaki_srazu, connection, monkeypatch
):
    """«Агаркова Ирина ᴰ·ᴱ·»: инициалы возвращаются в клетку фамилии, столбец пустеет."""
    _mir, prepod = vse_priznaki_srazu
    # Столбец пустеет, а инициалы возвращаются туда, где они стояли до 10.09, — внутрь
    # клетки фамилии, тем же приёмом, каким они там жили.
    monkeypatch.setattr(konduit, "_stolbec_prin",
                        lambda prinimayushchie, sid: '<td class="pr"></td>')
    html = konduit.razdel(kontekst(connection, prepod_id=prepod))
    html = html.replace('</label></td>', '</label><i class="prin">Д.Е.</i></td>')
    plohie = narusheniya_kletok(html)
    assert plohie, "рычаг не увидел второй носитель в клетке фамилии"
    assert "в клетке фамилии" in plohie[0], plohie[0]


def test_samoproverka_a_duplicate_tick_beside_the_counter_goes_red(
    vse_priznaki_srazu, connection, monkeypatch
):
    """Галочка, добавленная в счётчик «чтобы заметнее», — то же смешивание, тише."""
    _mir, prepod = vse_priznaki_srazu
    monkeypatch.setattr(
        konduit, "_schyotchik",
        lambda schyot: '<i class="ob-sch">\u2713 %d</i>' % schyot.sdano)
    html = konduit.razdel(kontekst(connection, prepod_id=prepod))
    plohie = narusheniya_znaka(html)
    assert plohie, "рычаг не увидел галочку, продублированную в чужом столбце"
    assert "в столбце «sch»" in plohie[0], plohie[0]
