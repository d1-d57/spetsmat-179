#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-code — imported by `tools/sobrat_stranicu.py` on every
# build, and by every module under `veb/razdely/`. Nothing here renders a section:
# this is the shell the sections hang in, plus the one value they all share.
"""The shell of the page, and the shared scope turned into a value you can pass.

WHY THIS FILE EXISTS. The page used to be one function, `sobrat_html`, with
twenty closures inside it sharing one scope: the role, the database handle, the
two lesson days, the rooms per day, the groups, the teachers, the pupils. Every
edit to any section therefore opened that one file, and two people could not
work on two sections at once. Cutting the sections apart is only possible once
the shared scope stops being a closure and becomes an argument. That argument
is `Kontekst`, and this is where it is built.

WHAT A SECTION MAY ASSUME. It is handed `kt: Kontekst` and reads it. It never
reaches back into the shell, and the shell never imports a section — the only
place that knows about both is the composition root, `sobrat_html`. There is
exactly one exception, and it is explained where it happens, in `sobrat_kontekst`.

🔴 THE LOOK OF THE PAGE IS NOT DECIDED HERE AND MUST NOT BE CHANGED HERE. Read
`doc/DIZAJN-ZAKREPLENO.md` before touching one byte of the markup or of the
stylesheet in `obolochka`. This file was produced by MOVING text, not by
rewriting it: the page it builds is byte-for-byte the page that was built before
the cut, and that is the only reason a refactor this size was allowed to happen
eleven hours before a lesson.

🔴 THE RUSSIAN COMMENTS BELOW ARE NOT TRANSLATED, ON PURPOSE. They carry the
owner's own words with the dates he said them on — "Владелец 06.09: …" — and a
translation would be a rewrite of evidence. Everything newly written here is in
English, as the задание requires; everything moved is verbatim, down to the
byte. That is also what makes the byte criterion of this refactor meaningful:
a diff between the page before and the page after can only show a mistake,
never a paraphrase.
"""
from __future__ import annotations

import html
import pathlib
import sqlite3
from datetime import date, datetime, timezone
from dataclasses import dataclass, field

KOREN = pathlib.Path(__file__).resolve().parent.parent.parent
# 🔴 АДРЕС, А НЕ ИМЯ. Здесь стоял путь от корня репозитория — то самое второе
# имя, из-за которого одна строка указывала на разные файлы на сервере и на
# машине владельца, и указывала успешно. Источник называет переменная среды
# `SPETSMAT_BAZA`; не названа — отказ с двумя законными адресами, а не фантом.
# Разбор — `doc/ISTOCHNIK-BAZY.md`.
def data() -> pathlib.Path:
    import config
    return config.DB_PATH

# 🔴 ДНИ ЗАНЯТИЙ БЕРУТСЯ ИЗ ОДНОГО ДОМА — `veb/sobrat_fajl.py`. Вписанные руками
# `DATA_NA` и `DATA_SLOVAMI` отсюда убраны: их никто не читал, а датой они
# повторяли ту самую строку, которая звала субботу четвергом.
from veb.sobrat_fajl import DNI_ZANYATIJ, SOKR_DNYA, blizhajshij_den  # noqa: E402


def e(s):
    return html.escape(str(s if s is not None else ""))


# ─────────────────────────────────────────────────────────────────────────────
# 🔴 УРОВНИ ДОСТУПА. ОДИН САЙТ, ОДИН КАРКАС, НАДСТРОЙКИ СВЕРХУ.
#
# Роль НЕ выбирает вёрстку. Роль выбирает НАБОР ВОЗМОЖНОСТЕЙ, а вёрстку рисует
# один и тот же код для всех. Разница между тем, что видит гость, и тем, что
# видит организатор, — это несколько ДОБАВЛЕННЫХ элементов, а не другая страница.
#
# Почему именно так, а не «страница для админа» отдельным файлом: две страницы
# одного и того же расходятся всегда. Не иногда, а всегда — потому что правку
# вносят в одну, а про вторую вспоминают через неделю. Здесь расходиться нечему.
#
# Как это проверяется машиной, а не вниманием человека: КАЖДЫЙ элемент, который
# существует только благодаря возможности, несёт атрибут `data-org`. Гейт
# `proverit_karkas()` снимает все такие элементы из версии с ролью и сравнивает
# остаток с гостевой ПОБАЙТОВО. Разошлось — значит каркас разъехался, и это
# ошибка сборки, а не вопрос вкуса.
#
# Как сюда добавляется НОВАЯ роль (преподаватель, школьник — они на очереди):
# одной строкой в этот словарь. Ни одна функция отрисовки при этом не меняется.
VOZMOZHNOSTI = {
    "gost": frozenset(),
    "organizator": frozenset({
        "pravit-raspredelenie",   # выпадающие списки вместо текста, крестики
        "pravit-kabinety",        # поля кабинета в шапке группы
        "videt-schyot",           # счётчики нагрузки и числа по группам
        "videt-klass",            # буква класса у школьника
        "pereklyuchat-dni",       # переключатель понедельник/четверг вместо даты
        "videt-konduit",          # раздел кондуита; см. примечание под словарём
    }),
    # 🔴 THE TEACHER, ADDED 2026-09-07 — one line, as the comment above promised.
    # `videt-svoyo` buys exactly one thing: the section where this named person
    # sees their own room and their own children. Not one editing capability is in
    # it, and that is deliberate: a teacher who is also the senior of an auditorium
    # enters as `organizator` by their personal password (`veb/vhod.py`), which is
    # a DIFFERENT role, not a bigger one. Everything else on the page a teacher
    # sees is what a guest sees — including the `data-tolko-gost` room chips, which
    # is what makes this role guest-like and matters to the frame gate (see
    # `veb/server.py::_karkas_prepoda_sovpadaet`).
    "prepod": frozenset({"videt-svoyo", "videt-konduit"}),
}
# 🔴 `videt-konduit` STANDS ON BOTH THE ORGANISER AND THE TEACHER, AND IT IS WHAT
# KEEPS THE КОНДУИТ OFF THE PUBLIC PAGE. `tools/sobrat_stranicu.sobrat()` writes
# the GUEST build to `docs/index.html`, `veb/server.py::_peresobrat` re-runs it
# after every successful write to the база, and this repository is public: a
# кондуит drawn without a capability would publish the surname of every pupil and
# the record of every problem they did or did not hand in. The мандат also
# requires `docs/index.html` byte-for-byte unchanged by this position, and one
# unguarded section would break that on the next save rather than in the diff.
# Ни одной возможности ПРАВКИ здесь нет: раздел только читает.


ALL_VOZMOZHNOSTI = frozenset().union(*VOZMOZHNOSTI.values())


# 🔴 ВРЕМЯ ЗАНЯТИЙ ЖИВЁТ ЗДЕСЬ, ОДНОЙ СТРОКОЙ НА ДЕНЬ. Раньше оно стояло
# прямо в разметке расписания, и второе место, где его надо показать (шапка
# распределения), пришлось бы писать копией — то есть завести вторую правду
# о том же. Продиктовано владельцем 06.09.
VREMYA = {"pn": "14:15\u2009—\u200915:55", "cht": "13:10\u2009—\u200915:00"}
MESYACY = ("января", "февраля", "марта", "апреля", "мая", "июня",
           "июля", "августа", "сентября", "октября", "ноября", "декабря")


@dataclass
class Kontekst:
    """Everything the sections share, as one value that is passed, not captured.

    Built once per page by `sobrat_kontekst`. A section reads it and returns
    markup; nothing in here is written to while a page is being rendered.

    The field names are the names the closures used inside `sobrat_html`, kept
    letter for letter. Renaming them to something prettier would have turned
    every moved body into a body that had also been edited, and the byte
    criterion of this refactor could then no longer tell a move from a mistake.
    """

    rezhim: str                # as the caller asked for it: "gost" | "admin"
    rol: str                   # as the roles table spells it: "gost" | "organizator"
    mogu: frozenset            # the capabilities that role has
    c: sqlite3.Connection
    DNI: dict                  # "pn" | "cht" → (day name, slot, date, short name)
    kabinety_dnya: dict        # day → group → room
    otkuda_kabinet: dict       # day → group → date the room was carried over from
    kabinety: dict             # Monday's rooms; kept under its old name on purpose
    gruppy: dict               # group code → its senior
    prep: dict                 # active teachers, by id
    # 🔴 В КАКИЕ ДНИ ПРИНИМАЮЩИЙ ПРИХОДИТ: `{teacher_id: {slot, …}}`. Это ПАМЯТЬ, а
    # не вывод из `enrollment`: «придёт, детей ещё не дали» ниоткуда не вычисляется,
    # а отметить это владельцу нужно (решение 07.09, две галочки).
    dni_prepodavatelej: dict = field(default_factory=dict)
    # 🔴 ДАТА ЗАНЯТИЯ ИЛИ `None`. Ровно этим разделы отличают экран «на сегодня» от
    # экрана «как обычно»: где ставить галочку «болеет», куда слать правку и надо
    # ли ждать кнопки «Сохранить». Одно поле вместо флага «режим» — потому что
    # дата здесь ещё и нужна сама по себе, как адрес правки.
    den: object = None
    # Кто из принимающих отмечен отсутствующим НА ЭТУ ДАТУ (`teacher_attendance`).
    # Пусто на постоянном экране: там нет «сегодня».
    otsutstvuyut_prepoda: frozenset = frozenset()
    # 🔴 ПЕРИОД ОТСУТСТВИЯ — ЭТО ДРУГОЙ ФАКТ, ЧЕМ СТРОКА ВЫШЕ, И ПОЛЕ ПОТОМУ ВТОРОЕ.
    # `otsutstvuyut_prepoda` отвечает про ОДНУ дату и только там, где занятие уже
    # заведено (`teacher_attendance` висит на `sessions`); это поле отвечает про
    # ЛЮБУЮ дату страницы, включая будущую, у которой строки `sessions` нет и не
    # будет до самого занятия. `{ISO-дата: frozenset(teacher_id)}` — по одному
    # ключу на каждую дату из `DNI`, то есть один ключ на экране занятия и два на
    # постоянном. Пустой словарь значит «периодов на эти даты нет», а не «не
    # спрашивали»: заполняет его `sobrat_kontekst`, всегда.
    otsutstvie_po_dnyam: dict = field(default_factory=dict)
    shk_dnya: dict = field(default_factory=dict)   # day → rows of pupils
    shk: list = field(default_factory=list)        # Monday's pupils
    # Who the page belongs to, when it belongs to somebody: `teachers.id`.
    # `None` is the ordinary answer for the guest page, for the organiser page, and
    # for a teacher who came in by the COMMON password — nobody in particular. A
    # section that shows personal data must treat all three the same way and show
    # none, which is what `veb/razdely/lichnaya.py` does.
    prepod_id: int | None = None

    def mozhno(self, vozmozhnost: str) -> bool:
        """Единственный способ спросить про права. Прямых сравнений с ролью нет.

        🔴 СПРАШИВАТЬ НАДО ПРО ВОЗМОЖНОСТЬ, А НЕ ПРО РОЛЬ. `if rol == "organizator"`
        разложенное по двадцати местам — это и есть та самая вторая версия сайта,
        только рассыпанная. Когда придёт роль преподавателя, её надо будет вписать
        в двадцать мест и в одном забыть. Здесь — в один словарь наверху.
        """
        assert vozmozhnost in ALL_VOZMOZHNOSTI, f"неизвестная возможность: {vozmozhnost}"
        return vozmozhnost in self.mogu

    @property
    def ADMIN(self) -> bool:
        """Короткое имя для самых частых мест."""
        return self.mozhno("pravit-raspredelenie")

    @property
    def blizh(self) -> str:
        """The day the page opens on — the nearest lesson, not the calendar today.

        It used to be computed twice inside `sobrat_html`, by the same expression
        written out in two places. One of the two was going to lag behind the
        other the first time the rule changed; here there is only one.
        """
        return min(self.DNI, key=lambda k: self.DNI[k][2])

    def po_russki_kratko(self, iso):
        """`2026-09-07` → `7 сент`. Длинная дата давила на то, что рядом с ней."""
        god, mes, den = (int(x) for x in iso.split("-"))
        return f"{den} {MESYACY[mes - 1][:4].rstrip('я')}"

    def po_russki(self, iso):
        """`2026-09-07` → `7 сентября`. Дата на странице читается человеком."""
        god, mes, den = (int(x) for x in iso.split("-"))
        return f"{den} {MESYACY[mes - 1]}"

    # 🔴 THE ROOM CHIP LIVES HERE AND NOT IN `veb/razdely/gruppy.py`, WHICH IS
    # WHERE THE SECTION MAP OF THE ЗАХОД PUT IT. Four sections call it — pupils
    # (`para_shk`), teachers (`para_prep` and `vid_prepodavateli`) and the tab row
    # of the front page — while `gruppy.py` must itself import `para_shk` and
    # `para_prep` in order to lay a group out. Following the map literally
    # produces the import cycle `gruppy → shkolniki → gruppy`, which Python does
    # not resolve at module level. The room chip is shared vocabulary, so its home
    # is `obshchee`. Everything else in the map is followed exactly.
    def kab_html(self, kl, kod):
        """Чип кабинета. Пусто — честное «не назначен», а не выдуманный номер."""
        k = self.kabinety_dnya[kl].get(kod)
        if not k:
            return '<span class="net">кабинет не назначен</span>'
        ot = self.otkuda_kabinet[kl].get(kod)
        podpis = (f' title="на этот день ещё не назначен; кабинет с {e(ot)}"'
                  if ot else "")
        klass = "kab staryj" if ot else "kab"
        return f'<span class="{klass}"{podpis}>{e(k)}</span>'


# ─────────────────────────────────────────────────────────────────────────────
# ПЕРИОДЫ ОТСУТСТВИЯ ПРИНИМАЮЩЕГО (`migrations/013_otsutstvie_prepodavatelya.sql`)
#
# 🔴 ПОЧЕМУ ЭТИ ПЯТЬ ФУНКЦИЙ ЖИВУТ ЗДЕСЬ, А НЕ В РАЗДЕЛЕ. Их читателей ДВА, и они
# в разных файлах: распределение (`veb/razdely/shkolniki.py` — кого вообще можно
# предложить принимающим) и журнал (`veb/razdely/istoria_zanyatij.py` — как
# выглядит клетка дня периода и кто остался без принимающего). Оба уже импортируют
# этот модуль, и ничего другого общего у них нет. Копия разбора в каждом из двух
# была бы вторым мнением о том, отсутствует человек в этот день или нет, — то есть
# ровно тем, от чего лечится весь этот файл.
#
# 🔴 `infra/` — НЕ ВАРИАНТ ДЛЯ ЭТОГО ЗАХОДА: он вне зоны. Приём тот же, что уже
# стоит у `infra/prepodavatel_den_repo`, и назван вслух здесь, а не унаследован
# молча: таблица заводится по требованию, потому что живая база старше миграции.
# ─────────────────────────────────────────────────────────────────────────────

#: Почему человека не будет. Набор ЗАКРЫТ — его называет само задание владельца
#: («болезнь/отъезд/иное»), и он же стоит в `CHECK` миграции 013. Свободная строка
#: за семестр собрала бы «болеет · болен · заболела · б-нь», и посчитать их было бы
#: уже нечем.
PRICHINY_OTSUTSTVIYA = ("болезнь", "отъезд", "иное")

_SOZDAT_OTSUTSTVIYA = """
create table if not exists otsutstvie_prepodavatelya (
    id           integer primary key,
    teacher_id   integer not null references teachers(id),
    s_daty       text not null
        check (s_daty glob '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    po_datu      text not null
        check (po_datu glob '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    prichina     text not null
        check (prichina in ('болезнь', 'отъезд', 'иное')),
    zametka      text,
    kto_otmetil  integer references teachers(id),
    kogda        text not null,
    check (s_daty <= po_datu)
)
"""


def obespechit_otsutstvia(c: sqlite3.Connection) -> None:
    """Завести таблицу периодов, если база старше миграции 013.

    🔴 ТОТ ЖЕ ПРИЁМ, ЧТО У `infra/prepodavatel_den_repo.obespechit`, И ПО ТОЙ ЖЕ
    ПРИЧИНЕ: боевая база живёт на сервере и мигрируется отдельно от выкладки кода,
    поэтому между выкладкой и миграцией есть окно, в котором страница уже зовёт
    таблицу, а таблицы ещё нет. Без этой строки окно выглядело бы как `sqlite3
    .OperationalError: no such table` на ГЛАВНОЙ странице сайта, а не как пустой
    список периодов.

    Определение здесь — БУКВАЛЬНАЯ КОПИЯ миграции, и это сказано вслух, потому что
    копия — это долг: разойдясь, две версии дадут разную таблицу на разных машинах.
    Держать их вместе нечем внутри зоны этого захода (`infra/` вне зоны), поэтому
    расхождение ловится проверкой в `tests/veb/test_otsutstvie_prepodavatelya.py`,
    которая сверяет обе схемы полем за полем.

    🔴 СНАЧАЛА СПРАШИВАЕМ, ПОТОМ СОЗДАЁМ, И ЭТО НЕ МИКРО-ОПТИМИЗАЦИЯ. Функция
    зовётся на КАЖДОМ рендере страницы (её зовёт `sobrat_kontekst`, по разу на
    каждую дату экрана), то есть три раза в секунду на живом занятии. `create
    table if not exists` в этом положении — DDL по запросу на главной странице
    сайта: он ничего не меняет 99.99 % раз, но именно он окажется тем оператором,
    который упрётся в чужой лок или в базу, открытую только на чтение, и уронит
    ВЕСЬ экран ради строки, которой и так нет работы. Чтение `sqlite_master` —
    обычный SELECT, и на нём ни лока, ни отказа не бывает.
    """
    est = c.execute("select 1 from sqlite_master where type = 'table' and name = ?",
                    ("otsutstvie_prepodavatelya",)).fetchone()
    if est is not None:
        return
    c.execute(_SOZDAT_OTSUTSTVIYA)
    c.execute("create index if not exists otsutstvie_po_prepodavatelyu "
              "on otsutstvie_prepodavatelya (teacher_id, s_daty)")
    c.execute("create index if not exists otsutstvie_po_datam "
              "on otsutstvie_prepodavatelya (s_daty, po_datu)")


def periody_otsutstvij(c: sqlite3.Connection, teacher_id=None) -> tuple:
    """Все отмеченные периоды, свежие сверху: `({id, teacher_id, s_daty, …}, …)`.

    Порядок — по началу периода вниз: человек, отмечающий отсутствие, смотрит на
    ближайшее, а не на прошлогоднее.
    """
    obespechit_otsutstvia(c)
    uslovie, parametry = "", ()
    if teacher_id is not None:
        uslovie, parametry = "where teacher_id = ? ", (teacher_id,)
    return tuple(dict(r) for r in c.execute(
        "select id, teacher_id, s_daty, po_datu, prichina, zametka, "
        "kto_otmetil, kogda from otsutstvie_prepodavatelya " + uslovie +
        "order by s_daty desc, id desc", parametry))


def otsutstvuyushchie_na_datu(c: sqlite3.Connection, den: str) -> frozenset:
    """`{teacher_id, …}` — кого нет В ЭТОТ ДЕНЬ по отмеченному периоду.

    🔴 СРАВНЕНИЕ СТРОКАМИ, И ЭТО ВЕРНО, А НЕ СОЙДЁТ. ISO-8601 в форме
    `ГГГГ-ММ-ДД` сортируется лексикографически ровно так же, как хронологически, —
    на этом уже стоит весь `enrollment` (`valid_from < valid_to`, `valid_to =
    '9999-12-31'`). Разбор в `date` добавил бы здесь только повод уронить страницу
    на кривой строке, которую `CHECK` в базу и не пустил.

    Оба конца ВКЛЮЧЕНЫ: `between` в SQLite включает границы, и это то самое «с 1 по
    12 октября» — двенадцать дней, а не одиннадцать.
    """
    obespechit_otsutstvia(c)
    return frozenset(r[0] for r in c.execute(
        "select distinct teacher_id from otsutstvie_prepodavatelya "
        "where ? between s_daty and po_datu", (den,)))


def otmetit_otsutstvie(c: sqlite3.Connection, teacher_id: int, s_daty: str,
                       po_datu: str, prichina: str, kto_otmetil=None,
                       zametka=None) -> int:
    """Отметить период. Возвращает `id` заведённой строки.

    🔴 НАЗАД И ВПЕРЁД — ОДНА И ТА ЖЕ СТРОКА, И НИКАКОЙ ПРОВЕРКИ «НЕ В ПРОШЛОМ»
    ЗДЕСЬ НЕТ. Владелец назвал оба случая одним предложением: *«Мы можем отмечать
    это в текущем распределении, что он заболел, а можем отмечать это в
    распределении на будущее»*. Запрет на прошлое сделал бы невозможным именно
    первый — «заболел сегодня» отмечают, когда день уже идёт.
    """
    if prichina not in PRICHINY_OTSUTSTVIYA:
        raise ValueError("причина: " + " | ".join(PRICHINY_OTSUTSTVIYA))
    if s_daty > po_datu:
        raise ValueError("начало периода позже его конца: %s > %s" % (s_daty, po_datu))
    obespechit_otsutstvia(c)
    kur = c.execute(
        "insert into otsutstvie_prepodavatelya "
        "(teacher_id, s_daty, po_datu, prichina, zametka, kto_otmetil, kogda) "
        "values (?, ?, ?, ?, ?, ?, ?)",
        (teacher_id, s_daty, po_datu, prichina, zametka, kto_otmetil,
         datetime.now(timezone.utc).isoformat(timespec="seconds")))
    return int(kur.lastrowid)


def snyat_otsutstvie(c: sqlite3.Connection, period_id: int) -> bool:
    """Убрать отметку целиком. `False` — такой строки не было.

    Отметка СНИМАЕТСЯ, а не гасится флагом: «я ошибся, он будет» — это не событие
    истории школы, это опечатка. Сам факт отсутствия, когда он состоялся, живёт в
    журнале посещений (`teacher_attendance`), и оттуда его никто не убирает.
    """
    obespechit_otsutstvia(c)
    kur = c.execute("delete from otsutstvie_prepodavatelya where id = ?", (period_id,))
    return kur.rowcount > 0


def _razobrat_rezhim(rezhim: str) -> tuple:
    """`"admin"` → `("organizator", None)`; `"admin:2"` → `("organizator", 2)`;
    `"prepod:17"` → `("prepod", 17)`.

    🔴 У ОРГАНИЗАТОРА ТОЖЕ ЕСТЬ ЛИЦО, И 07.09 ЭТО СТОИЛО ВЛАДЕЛЬЦУ ВСЕГО ЛИЧНОГО.
    Трое из четырнадцати принимающих — старшие по аудиториям, и вход личным
    паролем даёт им роль `organizator` ВМЕСТЕ с `uid`. Но `veb/server.py` для
    этой роли собирал страницу режимом `"admin"`, то есть выбрасывал `uid` —
    и владелец, войдя своим паролем, не видел ни своего кабинета, ни своих
    школьников, ни галочки «только мои». Роль и человек — разные вопросы;
    режим теперь несёт оба.

    🔴 THE PERSON RIDES INSIDE THE MODE STRING, AND THAT IS A CONSTRAINT, NOT A
    DESIGN. The composition root `tools/sobrat_stranicu.sobrat_html` is the only
    caller of this function, and it hands the mode down as its single argument;
    that file is outside the zone of the заход that added this, so the parameter
    it ought to grow (`sobrat_html(rezhim, *, prepod_id=None)`) could not be added
    there. The two alternatives were both worse: module-level state naming "the
    current person" races between two teachers inside one `ThreadingHTTPServer`,
    and a second renderer for the personal page is the very thing this whole file
    exists to prevent. Named in `## ВОПРОСЫ` of `kod_lichnaya-stranica-prepodavatelya.md`
    as the правка that belongs to whoever owns `tools/`.

    An unparseable person is not a person: `"prepod:"` and `"prepod:x"` give the
    role with `None` beside it, i.e. the page a teacher sees when the entry could
    not say WHO they are. Refusing to build would take the whole site down for a
    typo in a cookie.
    """
    if rezhim == "admin":
        return "organizator", None
    if rezhim.startswith("admin:"):
        hvost = rezhim.split(":", 1)[1]
        return "organizator", (int(hvost) if hvost.isdigit() else None)
    if ":" not in rezhim:
        return rezhim, None
    rol, _, hvost = rezhim.partition(":")
    try:
        return rol, int(hvost)
    except ValueError:
        return rol, None


def sobrat_kontekst(rezhim: str = "gost", den=None, baza=None) -> Kontekst:
    """Read the database once and hand back everything the sections will need.

    🔴 `baza` — НЕ УДОБСТВО, А ЗАКРЫТИЕ ВТОРОГО ИСТОЧНИКА. Оболочка сайта читала
    базу САМА, модульной константой, и потому обслуживала запрос НЕ ИЗ ТОГО файла,
    который назвали серверу: один запрос — две базы, и ни одна строка страницы об
    этом не говорила. Пока обе указывали на `data/spetsmat.db`, расхождение было
    невидимо; стоило базе получить адрес — оно вылезло сразу. Теперь базу называет
    тот, кто её знает, а `None` значит «спроси источник» (`config.DB_PATH`).

    This is the only place that talks to the database on behalf of the shell.
    A section that needs a query of its own owns that query — see
    `veb/razdely/shkolniki.shkolniki` — but a section never opens a connection.

    ГЛАВНОЕ ПРО `den`, И ЭТО РЕШЕНИЕ ВЛАДЕЛЬЦА 07.09
    ----------------------------------------------------------------------------------
    `den=None` — ПОСТОЯННОЕ распределение: в `DNI` два дня, и у каждого школьника
    два поля. `den="2026-09-10"` — распределение НА ЗАНЯТИЕ: в `DNI` ровно один
    день, и те же самые разделы рисуют одну колонку, ничего про это не зная.

    Владелец, дословно: *«те же самые пять вкладок должны быть на сегодня… отличие
    этих двух менюшек минимальное. В текущем распределении бессмысленно
    устанавливать день недели — там устанавливается на конкретную дату, поэтому там
    не нужно две вкладки»*. Второй набор разделов «для занятия» был бы второй
    вёрсткой того же самого — ровно той болезнью, от которой лечится весь этот файл.

    Состав на занятии берётся НЕ из `enrollment` напрямую, а из
    `core.services.sostav_na_den`: постоянное ПЛЮС отклонения этого дня. Это и есть
    «текущее поверх базового» словами владельца: *«распределение текущего расписания
    всегда поверх базовой системы»*.
    """
    rol, prepod_id = _razobrat_rezhim(rezhim)
    if rol not in VOZMOZHNOSTI:
        raise ValueError("роль: " + " | ".join(sorted(VOZMOZHNOSTI)))
    mogu = VOZMOZHNOSTI[rol]


    c = sqlite3.connect(str(baza) if baza else data())
    c.row_factory = sqlite3.Row


    # 🔴 РАСПРЕДЕЛЕНИЕ ЗАВИСИТ ОТ ДНЯ. Занятия по понедельникам и четвергам, и
    # кабинет у группы в эти дни может быть РАЗНЫЙ. Поэтому строим оба дня сразу,
    # а на странице переключатель; по умолчанию открывается ближайший.
    # 🔴 ДЕНЬ СЧИТАЕТСЯ, А НЕ ВПИСЫВАЕТСЯ. Вписанная руками дата протухает молча:
    # так `2026-09-05` уже звался здесь четвергом, будучи субботой. Ни один гейт
    # этого не видел — вписанная строка всегда согласна сама с собой. Проверяется
    # одной строкой:
    #   python3 -c "from datetime import date;print(date(2026,9,7).weekday())"
    # Оба дня сейчас ОДИНАКОВЫ по составу, и это по-прежнему так. Здесь чинится
    # ИМЯ дня, а не раскладка.
    # 🔴 ПОНЕДЕЛЬНИК И ЧЕТВЕРГ, И ЭТО ПРАВКА ПОДПИСЕЙ, А НЕ ДАННЫХ. В
    # `migrations/003_slot_vmesto_weekday.sql` записано weekday=1 → slot=1,
    # weekday=4 → slot=2, то есть слот 1 — понедельник, слот 2 — четверг, и так уже
    # давно. Отстали только имена дней: код до сих пор звал их четвергом и субботой.
    # `enrollment` не трогается ни строкой.
    # Имена и номера дней НЕ вписаны здесь, а взяты из `veb/sobrat_fajl.DNI_ZANYATIJ` —
    # того самого «одного дома», который этот файл и объявляет. Вписанная копия уже
    # однажды разошлась с домом и печатала на странице неверные дни.
    _dni_po_poryadku = sorted(DNI_ZANYATIJ)          # пн, затем чт
    if den is None:
        DNI = {("pn", "cht")[i]: (DNI_ZANYATIJ[w], i + 1, blizhajshij_den(w), SOKR_DNYA[w])
               for i, w in enumerate(_dni_po_poryadku)}
    else:
        # 🔴 ОДИН ДЕНЬ — И ЭТО НЕ «ПОЛОВИНА ДВУХ», А ДРУГОЙ ВОПРОС. Ключ здесь не
        # «пн» и не «чт», а `den`: на этом экране спрашивают не «что бывает по
        # четвергам», а «что будет 10 сентября». Номер слота всё равно нужен —
        # им читается постоянный слой под отклонениями.
        # 🔴 КЛЮЧ ЗДЕСЬ `weekday()`, А НЕ `isoweekday()`, И РАЗНИЦА НЕ КОСМЕТИЧЕСКАЯ:
        # `DNI_ZANYATIJ` и `SOKR_DNYA` (`veb/sobrat_fajl`) считают понедельник НУЛЁМ,
        # а `enrollment.slot` — единицей. Спутать их — значит назвать четверг
        # пятницей и не заметить: строка «не день занятия · пт» на четверговой
        # странице ровно так и родилась при первом прогоне.
        from core.services.sostav_na_den import slot_of
        _wd = date.fromisoformat(den).weekday()
        DNI = {"den": (DNI_ZANYATIJ.get(_wd, "не день занятия"),
                       slot_of(den) or 0, den, SOKR_DNYA.get(_wd, ""))}
    # 🔴 КАБИНЕТ НА ДЕНЬ, А ЕСЛИ НА ЭТОТ ДЕНЬ ЕЩЁ НЕ НАЗНАЧЕН — ПОСЛЕДНИЙ
    # ИЗВЕСТНЫЙ, И ЭТО ВИДНО. Владелец ставит привязку накануне вечером, поэтому
    # «на послезавтра строки нет» — обычное состояние, а не потеря данных. Голый
    # `where data = ?` в этом состоянии печатал «кабинет не назначен» у всех трёх
    # групп разом, и переезд подписей дней (четверг+суббота → понедельник+четверг)
    # сделал бы это состоянием по умолчанию: строк на новые дни в базе просто нет.
    # Точное совпадение печатается как есть; последний известный несёт `title` с
    # датой, откуда он взят, — читатель обязан отличать одно от другого.
    kabinety_dnya = {}
    otkuda_kabinet = {}
    for kl, (_, _, dat, _sokr) in DNI.items():
        tochno = {r["gruppa"]: r["kabinet"] for r in c.execute(
            "select gruppa, kabinet from kabinet_na_den where data = ?", (dat,))}
        proshloe = {}
        for r in c.execute("select data, gruppa, kabinet from kabinet_na_den "
                           "where data < ? order by data", (dat,)):
            proshloe[r["gruppa"]] = (r["kabinet"], r["data"])
        svedeno, istochnik = {}, {}
        for kod in ("В", "Д", "Н"):
            if kod in tochno:
                svedeno[kod] = tochno[kod]
            elif kod in proshloe:
                svedeno[kod], istochnik[kod] = proshloe[kod]
        kabinety_dnya[kl] = svedeno
        otkuda_kabinet[kl] = istochnik

    # «Кабинеты по умолчанию» — понедельничные на постоянном экране и кабинеты
    # самой даты на экране занятия: ключ в `DNI` там один, и он же первый.
    kabinety = kabinety_dnya[next(iter(DNI))]
    gruppy = {r["kod"]: r["starshij"] for r in c.execute(
        "select kod, starshij from gruppy order by kod")}
    prep = {r["id"]: dict(r) for r in c.execute(
        "select id, name, gruppa from teachers where aktiven = 1")}
    # Дни принимающих — из своей таблицы; репозиторий сам заводит её, если база
    # старше миграции 007 (`infra/prepodavatel_den_repo.obespechit`). Хранится
    # ОТСУТСТВИЕ, разворот в присутствие делает сам репозиторий.
    from infra.prepodavatel_den_repo import dni as dni_prepodavatelej
    dni_prep = dni_prepodavatelej(c)

    kt = Kontekst(rezhim=rezhim, rol=rol, mogu=mogu, c=c, DNI=DNI,
                  kabinety_dnya=kabinety_dnya, otkuda_kabinet=otkuda_kabinet,
                  kabinety=kabinety, gruppy=gruppy, prep=prep,
                  dni_prepodavatelej=dni_prep, den=den, prepod_id=prepod_id)

    # 🔴 ПЕРИОДЫ ЧИТАЮТСЯ ДЛЯ КАЖДОЙ ДАТЫ СТРАНИЦЫ, А НЕ ТОЛЬКО ДЛЯ «СЕГОДНЯ», И
    # ИМЕННО ЭТИМ ЗАКРЫВАЕТСЯ «В ОБЕИХ ВЕРСИЯХ РАСПРЕДЕЛЕНИЯ». На экране занятия
    # дата одна — та, которую спросили. На ПОСТОЯННОМ экране их две: ближайший
    # понедельник и ближайший четверг, и они лежат в `DNI` третьим полем каждой
    # записи. Строкой ниже обе версии получают один и тот же ответ из одного и того
    # же места; отдельной ветки «а на постоянном экране считаем иначе» нет и быть не
    # должно — она и была бы вторым мнением о том, кого сегодня нет.
    kt.otsutstvie_po_dnyam = {dat: otsutstvuyushchie_na_datu(c, dat)
                             for (_, _, dat, _s) in DNI.values()}

    # 🔴 THE IMPORT SITS INSIDE THE FUNCTION, AND THAT IS NOT SLOPPINESS.
    # "Who counts as a pupil" is a question belonging to the pupils section, so
    # the query lives there — that is what the section map says. The pupils
    # section in turn renders through `e()` and reads `Kontekst`, both of which
    # live here. An import at the top of this file would close the ring
    # `karkas → shkolniki → karkas`, which Python refuses at module level. Inside
    # the function the ring is open: by the time anybody calls this, both modules
    # are loaded. The same trick is already the house idiom — `veb/server.py`
    # imports the builder from inside `_peresobrat` for the same reason.
    from veb.razdely.shkolniki import shkolniki

    if den is None:
        kt.shk_dnya = {kl: shkolniki(c, sl) for kl, (_, sl, _, _s) in DNI.items()}
        kt.shk = kt.shk_dnya["pn"]
    else:
        # 🔴 НА ЗАНЯТИИ СПРАШИВАЮТ СОСТАВ, А НЕ ЗАКРЕПЛЕНИЕ. Постоянное — это то,
        # как обычно; сегодня же кто-то болеет, а кого-то отдали в другую группу
        # на один раз, и обе поправки лежат в слое занятия. Складывает их
        # `core.services.sostav_na_den`, единственное место в проекте, которое
        # умеет это делать, — второй такой расчёт здесь был бы второй правдой.
        from veb.razdely.zanyatie import otsutstvuyushchie_prepodavateli, sostav_dnya_strokami
        kt.shk_dnya = {"den": sostav_dnya_strokami(c, den, shkolniki(c, DNI["den"][1]))}
        kt.shk = kt.shk_dnya["den"]
        kt.otsutstvuyut_prepoda = otsutstvuyushchie_prepodavateli(c, den)
    return kt


VHOD_SKRIPT = r"""
<div class="okno" id="okno-vhod" hidden>
  <div class="okno-fon" data-zakryt></div>
  <form class="okno-telo" id="forma-vhoda" method="post" action="/vhod">
    <h2>Вход</h2>
    <!-- 🔴 СКРЫТОЕ ИМЯ ПОЛЬЗОВАТЕЛЯ СТОИТ ЗДЕСЬ НЕ ДЛЯ СЕРВЕРА — ОН ЕГО НЕ ЧИТАЕТ.
         Менеджеры паролей сохраняют ПАРУ «логин + пароль» и форму без логина чаще
         всего пропускают молча. С этим полем браузер предлагает запомнить вход и
         подставляет его в следующий раз. Владелец 06.09: «нужно, чтобы после
         входа пароль запоминался автоматически». -->
    <input type="text" name="kto" value="организатор" autocomplete="username"
           readonly hidden aria-hidden="true" tabindex="-1">
    <label for="parol">Пароль организатора</label>
    <input type="password" id="parol" name="parol" required autocomplete="current-password">
    <p class="okno-oshibka" id="vhod-oshibka" hidden>Неверный пароль.</p>
    <div class="okno-knopki">
      <button type="button" class="vtoraya" data-zakryt>Отмена</button>
      <button type="submit" class="glavnaya">ОК</button>
    </div>
  </form>
</div>
<script>
/* ── ВХОД ВСПЛЫВАЮЩИМ ОКНОМ, А НЕ ОТДЕЛЬНОЙ СТРАНИЦЕЙ ───────────────────────────
   Владелец 06.09: «нажимаю Вход — появляется небольшое всплывающее окно для
   пароля, ввожу поверх всего, нажимаю ОК и остаюсь на той же странице».
   Отдельная страница /vhod осталась жива и работает — она нужна как запасной
   путь и как то, куда сервер отправляет неавторизованного; но обычный человек
   её больше не видит. */
(function(){
  const okno = document.getElementById('okno-vhod');
  const forma = document.getElementById('forma-vhoda');
  const pole = document.getElementById('parol');
  const oshibka = document.getElementById('vhod-oshibka');
  if(!okno) return;

  function otkryt(){ okno.hidden = false; oshibka.hidden = true; pole.value=''; pole.focus(); }
  function zakryt(){ okno.hidden = true; }

  document.addEventListener('click', function(ev){
    const knopka = ev.target.closest('[data-otkryt-vhod]');
    if(knopka){ ev.preventDefault(); otkryt(); return; }
    if(ev.target.closest('[data-zakryt]')) zakryt();
  });
  document.addEventListener('keydown', function(ev){
    if(ev.key === 'Escape' && !okno.hidden) zakryt();
  });

  /* 🔴 ФОРМА ОТПРАВЛЯЕТСЯ БРАУЗЕРОМ, А НЕ СКРИПТОМ, И ЭТО ГЛАВНОЕ ЗДЕСЬ.
     Раньше вход шёл через `fetch` с `preventDefault` — и менеджер паролей не
     видел входа вовсе, поэтому не предлагал пароль сохранить и не подставлял
     его потом. Владелец вводил пароль каждый раз заново.

     Обычная отправка это чинит: браузер понимает, что произошёл вход, сервер
     отвечает 302 на `/`, и человек оказывается ровно там же, где был, — то есть
     обещание «остаюсь на той же странице» выполняется и без скрипта. Неверный
     пароль возвращает на `/?vhod=ne-pustil`, и окно открывается снова с ошибкой.

     Скрипт здесь только один: показать окно и запомнить, что оно было открыто. */
  const adres = new URL(location.href);
  if(adres.searchParams.get('vhod') === 'ne-pustil'){
    otkryt();
    oshibka.textContent = 'Неверный пароль.';
    oshibka.hidden = false;
    adres.searchParams.delete('vhod');
    history.replaceState(null, '', adres.pathname + adres.search + adres.hash);
  }
})();
</script>"""


PRAVKA_SKRIPT = r"""
<div class="soob" id="soob"></div>
<script>
/* ── ПРАВКИ НАКАПЛИВАЮТСЯ, СОХРАНЯЕТ КНОПКА ────────────────────────────────────
   Владелец 06.09: «должна быть большая кнопка Сохранить; должна быть возможность
   откатить правки или сохранить; при попытке перезагрузить, если есть
   несохранённые правки, должно выдаваться предупреждение. Это стандартные
   правила». Так и сделано, и это ЗАМЕНА прежнего поведения: раньше каждое
   движение мыши уходило в базу немедленно, и отменить его было нечем.

   🔴 ЭКРАН НЕ ПЕРЕСЧИТЫВАЕТ СЛЕДСТВИЯ ПРАВКИ САМ, И ЭТО НАРОЧНО. Кто в какой
   группе, сколько у кого школьников, куда переехали дети — считает сервер, по
   правилам, которые живут в одном месте. Если бы это же считал и браузер, правил
   стало бы двое, и они разошлись бы — ровно та болезнь, от которой лечится вся
   эта страница. Поэтому правка помечается жёлтым «не сохранено», а после
   «Сохранить» страница перечитывается и показывает то, что в базе. */
(function(){
  const panel = document.getElementById('panel-pravok');
  const schyot = document.getElementById('skolko-pravok');
  const soob = document.getElementById('soob');
  // 🔴 БЕЗ ПАНЕЛИ СКРИПТ НЕ ВЫКЛЮЧАЕТСЯ, А РАБОТАЕТ ДРУГИМ КОНЦОМ. На экране
  // занятия кнопок «Сохранить/Сбросить» нет вовсе (правки уезжают сразу), и
  // прежний ранний выход убил бы вместе с ними ВСЮ правку этого экрана.

  const pravki = new Map();          // ключ → операция; последняя правка побеждает
  const KLYUCH_VYBORA = 'spetsmat-vybor';
  /* Слоты дней снимаются С САМОЙ СТРАНИЦЫ, а не вписываются числами: какие номера
     несут понедельник и четверг, знает `migrations/003` и повторяет `kt.DNI`;
     вписанная сюда пара «1, 2» разошлась бы с ними молча и в другую сторону. */
  const SLOTY = Array.from(new Set(
    Array.from(document.querySelectorAll('.pr-sel')).map(function(el){
      return +el.dataset.slot;
    }))).sort();

  function slovo(n){
    const sto = n % 100, des = n % 10;
    if(sto > 10 && sto < 20) return 'правок';
    if(des === 1) return 'правка';
    if(des >= 2 && des <= 4) return 'правки';
    return 'правок';
  }
  function obnovit(){
    /* 🔴 КНОПКИ ВСЕГДА НА ВИДУ, В ВЕРХНЕЙ ПАНЕЛИ, И ПРОСТО ГАСНУТ. Кнопка,
       появляющаяся из ниоткуда, не сообщает, что сохранение вообще существует, —
       владелец её искал. А подпись, объясняющая кнопку словами, не нужна вовсе:
       число несохранённых правок стоит на самой кнопке, и этого достаточно. */
    if(!panel) return;               // экран занятия: копить нечего, кнопок нет
    const n = pravki.size;
    const est = n > 0;
    document.getElementById('sohranit').disabled = !est;
    document.getElementById('sbrosit').disabled = !est;
    panel.classList.toggle('est-pravki', est);
    schyot.textContent = est ? ' ' + n : '';
  }
  /* 🔴 ДВА МОМЕНТА ЗАПИСИ, И ЭТО РЕШЕНИЕ ВЛАДЕЛЬЦА 07.09, А НЕ ДВА СТИЛЯ КОДА.
     «Распределение на день не нужно писать кнопку „Сохранить“ — там могут быть
     ошибки, это не… как с кондуитом, там просто нужно сразу сохраняться. А
     постоянное распределение не нужно сохранять сразу, потому что там можно долго
     его двигать и в итоге прийти к оптимальному варианту, нажать „Сохранить“, и
     дальше оно влияет».

     Различает их ровно `data-den` на самом органе: есть дата — правка на один раз,
     она уезжает немедленно; нет — это шаблон, и она ждёт кнопки. Ни одного второго
     обработчика: ниже по файлу все ветки зовут `pomenyalos`, и решение принимается
     здесь, один раз. */
  /* 🔴 ПОСЛЕДНЕЕ ИЗВЕСТНОЕ ХОРОШЕЕ ЗНАЧЕНИЕ КАЖДОГО ОРГАНА, СНЯТОЕ ПРИ ЗАГРУЗКЕ.
     Оно нужно ровно для одного: вернуть орган на место, когда сервер отказал. Снимок
     остаётся верным всю жизнь страницы, потому что УСПЕШНАЯ немедленная правка её
     перечитывает, а накопительная до кнопки «Сохранить» в базу не ходит вовсе. */
  const bylo = new WeakMap();
  function znachenie(el){
    return (el.type === 'checkbox' || el.type === 'radio') ? el.checked : el.value;
  }
  function vernut_znachenie(el, v){
    if(el.type === 'checkbox' || el.type === 'radio'){ el.checked = v; }
    else { el.value = v; }
    /* Вид органа обязан вернуться вместе со значением: обработчик `change` рисует
       пустую строку и открытый замок сам, и без этого на экране осталась бы правка,
       которой в базе нет, — та самая молчаливая потеря. */
    if(el.classList.contains('otsut-chk') || el.classList.contains('totsut-chk')){
      const o = el.closest('.otsut');
      if(o) o.classList.toggle('pusto', !el.checked);
    }
    if(el.classList.contains('den-chk')){
      const d = el.closest('.den-gal');
      if(d) d.classList.toggle('pusto', !el.checked);
    }
  }
  document.querySelectorAll('.org').forEach(function(el){
    if(!bylo.has(el)) bylo.set(el, znachenie(el));
  });

  /* 🔴 ОТКАЗ СТОИТ, ПОКА ЕГО НЕ ЗАКРОЮТ. Ни таймера, ни перезагрузки поверх. */
  function pokazat_otkaz(pochemu){
    soob.className = 'soob ploho';
    soob.innerHTML = '<button type="button" class="soob-x">Понятно</button>'
      + '<span></span>';
    soob.querySelector('span').textContent =
      'НЕ СОХРАНИЛОСЬ: ' + pochemu + ' — значение вернулось к прежнему';
  }
  soob.addEventListener('click', function(ev){
    if(!ev.target.closest('.soob-x')) return;
    soob.className = 'soob';
    soob.textContent = '';
  });

  async function srazu(el, operacia){
    const ryad = el.closest('.para, tr');
    if(ryad) ryad.classList.add('idet');
    let ok = false, dannye = {}, pochemu = '';
    /* 🔴 ТАЙМАУТ ЗДЕСЬ — ТА ЖЕ ПОЧИНКА, ЧТО УЖЕ СТОИТ В КОНДУИТЕ (`db50f4f`), И
       ПО ТОЙ ЖЕ ЗАМЕРЕННОЙ ПРИЧИНЕ: при пропавшей сети `fetch` не отвечает ВООБЩЕ —
       ни `then`, ни `catch`, он просто висит. Строка так и оставалась бы в классе
       `idet` до перезагрузки страницы, и человек не узнал бы ни что правка не
       уехала, ни что можно повторить. Десять секунд — потолок ожидания: занятие
       идёт, и орган, молчащий дольше, бесполезен при любой причине молчания. */
    const otsechka = new AbortController();
    const budilnik = setTimeout(function(){ otsechka.abort(); }, 10000);
    try{
      const otvet = await fetch(operacia.put, {method:'POST',
        headers:{'Content-Type':'application/json'},
        signal: otsechka.signal,
        body: JSON.stringify(operacia.telo)});
      ok = otvet.ok;
      try{ dannye = await otvet.json(); }catch(err){}
      if(!ok) pochemu = dannye.error || ('сервер отказал (' + otvet.status + ')');
    }catch(err){
      ok = false;
      pochemu = (err && err.name === 'AbortError')
        ? 'сервер не ответил за 10 с' : 'связи с сервером нет';
    }
    clearTimeout(budilnik);
    if(ryad) ryad.classList.remove('idet');
    if(!ok){
      /* 🔴 НА ОТКАЗЕ СТРАНИЦА БОЛЬШЕ НЕ ПЕРЕЗАГРУЖАЕТСЯ. Требование владельца
         (точка 4 задания): «правка не смеет исчезать молча на глазах человека».
         Прежняя редакция показывала сообщение и через 1,2 с делала
         `location.reload()` — сообщение затиралось раньше, чем его успевали
         прочитать, и снаружи это выглядело как «правка слетела сама». Теперь
         орган возвращается к прежнему значению ЗДЕСЬ, на месте, сообщение
         называет ПРИЧИНУ и стоит, пока человек его не закроет.
         Правда базы от этого не теряется: страница не перерисована, а вернулась
         ровно к тому, что в базе и стоит, — правка ведь не уехала. */
      vernut_znachenie(el, bylo.has(el) ? bylo.get(el) : znachenie(el));
      pokazat_otkaz(pochemu || 'сервер отказал');
      return;
    }
    /* Счётчики, «некуда деть» и списки принимающих считает сервер, а не браузер:
       вторая правда про одни и те же числа — болезнь, от которой лечится вся эта
       страница. Поэтому после записи страница перечитывается. */
    location.reload();
  }

  function pomenyalos(el, klyuch, operacia){
    /* 🔴 ОДНО ИМЯ АТРИБУТА, И ЭТО СОГЛАШЕНИЕ, А НЕ ПРОВЕРКА. Правка на один день
       уезжает сразу; шаблонная ждёт кнопки. Различает их `data-den` — и ТОЛЬКО он.
       Второе имя здесь было бы заплаткой: имён стало бы два, и следующий орган
       выпал бы опять. Поле кабинета, единственное выпавшее из соглашения, приведено
       к нему (`veb/razdely/gruppy.py`), а не обойдено здесь. */
    if(el.dataset.den){
      srazu(el, operacia);
      return;
    }
    pravki.set(klyuch, operacia);
    const ryad = el.closest('.para, tr, .shapka');
    if(ryad) ryad.classList.add('tronuto');
    obnovit();
  }

  /* Предупреждение при уходе со страницы — стандартное поведение браузера. */
  window.addEventListener('beforeunload', function(ev){
    if(pravki.size === 0) return;
    ev.preventDefault();
    ev.returnValue = '';
    return '';
  });

  function pomnit(){
    const s = {};
    document.querySelectorAll('input.rd').forEach(i => { if(i.checked) s[i.name] = i.id; });
    try{ sessionStorage.setItem(KLYUCH_VYBORA, JSON.stringify(s)); }catch(err){}
  }
  (function vernut(){
    let s;
    try{ s = JSON.parse(sessionStorage.getItem(KLYUCH_VYBORA) || '{}'); }catch(err){ return; }
    Object.keys(s).forEach(function(k){
      const el = document.getElementById(s[k]);
      if(!el) return;
      /* 🔴 НЕ ВОССТАНАВЛИВАЕМ ВКЛАДКУ, РАЗДЕЛА КОТОРОЙ НА ЭТОЙ СТРАНИЦЕ НЕТ.
         Радиокнопка живёт в общем каркасе и есть всегда, а секция — не всегда:
         на странице занятия нет ни «Класса», ни «Листков». Отмеченная кнопка без
         своей секции даёт пустой экран под меню — ровно это владелец и увидел на
         боевом сайте. */
      const razdel = document.getElementById('s-' + el.id.replace(/^p-/, ''));
      if(el.name === 'str' && !razdel) return;
      el.checked = true;
    });
  })();

  document.addEventListener('change', function(ev){
    const el = ev.target;
    if(!el.classList || !el.classList.contains('org')) return;
    /* Вид кнопки меняется в тот же миг, что и её состояние: страница
       перечитывается позже, а рука уже отпустила кнопку. */
    if(el.classList.contains('otsut-chk') || el.classList.contains('totsut-chk')){
      el.closest('.otsut').classList.toggle('pusto', !el.checked);
    }
    if(el.classList.contains('svyaz-chk')){
      const z = el.closest('.zamok');
      z.classList.toggle('otkryt', !el.checked);
      z.querySelector('span').textContent = el.checked ? '\uD83D\uDD12' : '\uD83D\uDD13';
      return;                       /* замок ничего не пишет в базу: он про то,
                                       как правятся ДРУГИЕ поля этой строки */
    }
    const sl = +el.dataset.slot;
    if(el.classList.contains('pr-sel')){
      const sid = +el.dataset.sid;
      if(el.dataset.den){
        /* На занятии «нет» значит «сегодня ни у кого», а не «убрать из группы»:
           группы у дня нет вовсе, она свойство постоянного. */
        pomenyalos(el, 'zan:' + sid,
          {put:'/api/zanyatie', telo:{den:el.dataset.den, student_id:sid,
                                      teacher_id: el.value ? +el.value : null}});
      }else if(el.value){
        /* 🔴 СВЯЗАННЫЕ ДНИ ПРАВЯТСЯ ВМЕСТЕ, И ЭТО ПОВЕДЕНИЕ ПО УМОЛЧАНИЮ.
           Владелец 07.09: «у каждого школьника два преподавателя, хотя по
           умолчанию они должны быть одинаковыми… можно нажать галочку, и тогда
           оно отвязывается». Пока галочка «×2» не нажата, поставленный в
           понедельник человек становится и четверговым — иначе каждую правку
           пришлось бы делать дважды, а забытая половина расходится молча. */
        const stroka = el.closest('.para');
        /* Замок ЗАЖАТ — дни связаны (владелец: «изначально они зажаты»). */
      const zamok = stroka && stroka.querySelector('.svyaz-chk');
      const raznye = !!zamok && !zamok.checked;
        const polya = (!raznye && stroka) ? stroka.querySelectorAll('.pr-sel') : [el];
        polya.forEach(function(p){
          p.value = el.value;
          pomenyalos(p, 'shk:' + sid + ':' + p.dataset.slot,
            {put:'/api/enrollment',
             telo:{student_id:sid, slot:+p.dataset.slot, teacher_id:+el.value}});
        });
      }else{
        const gr = el.parentElement.querySelector('.gr-sel');
        pomenyalos(el, 'shk:' + sid + ':' + sl,
          {put:'/api/enrollment', telo:{student_id:sid, slot:sl, teacher_id:null,
                                        gruppa: gr ? gr.value : ''}});
      }
    }else if(el.classList.contains('gr-sel')){
      /* 🔴 ГРУППА У ШКОЛЬНИКА ОДНА, А ДНЕЙ ДВА — ЗНАЧИТ ПРАВОК ТОЖЕ ДВЕ.
         `students.gruppa` не разделена по дням, и «перевести в группу» означает
         снять его с преподавателя В ОБА ДНЯ: оставить один день у прежнего
         человека значило бы, что ребёнок числится и там, и в новой группе, а
         экран показывал бы одно из двух — смотря на какой день смотришь. */
      const sid = +el.dataset.sid;
      const stroka = el.closest('.para');
      const pr = stroka ? stroka.querySelectorAll('.pr-sel') : [];
      pr.forEach(function(p){ p.value = ''; });   /* группа сменилась — преподаватель снимается */
      SLOTY.forEach(function(slot){
        pomenyalos(el, 'shk:' + sid + ':' + slot,
          {put:'/api/enrollment', telo:{student_id:sid, slot:slot, teacher_id:null,
                                        gruppa: el.value}});
      });
    }else if(el.classList.contains('otsut-chk')){
      /* «Отсутствует» — отметка ОДНОГО занятия, одно слово на школьника и на
         принимающего (поправка владельца 07.09). Снятая отметка возвращает строку
         к «как обычно», а не пишет «был» поверх: разбирается с этим сервер. */
      const sid = +el.dataset.sid;
      pomenyalos(el, 'otsut:' + sid,
        {put:'/api/zanyatie', telo:{den:el.dataset.den, student_id:sid,
                                    net: el.checked}});
    }else if(el.classList.contains('totsut-chk')){
      const tid = +el.dataset.tid;
      pomenyalos(el, 'totsut:' + tid,
        {put:'/api/zanyatie', telo:{den:el.dataset.den, rod:'prepodavatel',
                                    teacher_id:tid, net: el.checked}});
    }else if(el.classList.contains('grd-sel')){
      /* Группа на это занятие: «он уже в аудитории, к кому — ещё решаем». */
      const sid = +el.dataset.sid;
      pomenyalos(el, 'grd:' + sid,
        {put:'/api/zanyatie', telo:{den:el.dataset.den, student_id:sid,
                                    gruppa: el.value}});
    }else if(el.classList.contains('den-chk')){
      /* 🔴 ГАЛОЧКА ДНЯ И ВЫБОР ГРУППЫ — РАЗНЫЕ ОРГАНЫ, ПОТОМУ ЧТО ЭТО РАЗНЫЕ ВЕЩИ.
         Владелец 07.09: «не бывает принимающего, который в разные дни в разных
         группах… можно сделать проще: две кнопки-галочки — „в четверг прихожу“ и
         „в понедельник прихожу“, и отдельно выбирается группа принимающего». День
         отвечает за присутствие, группа — одна на человека. */
      const tid = +el.dataset.tid;
      el.closest('.den-gal').classList.toggle('pusto', !el.checked);
      pomenyalos(el, 'prep-den:' + tid + ':' + sl,
        {put:'/api/prepodavateli',
         telo:{deystvie:'den', teacher_id:tid, slot:sl, prihodit:el.checked}});
    }else if(el.classList.contains('tgr-sel')){
      const tid = +el.dataset.tid;
      pomenyalos(el, 'prep:' + tid,
        {put:'/api/prepodavateli', telo:{deystvie:'gruppa', teacher_id:tid, gruppa:el.value}});
    }else if(el.classList.contains('kab-inp')){
      const k = el.value.trim();
      if(!k){ el.value = el.defaultValue; return; }
      /* День читается ОТТУДА ЖЕ, откуда его берёт `pomenyalos` — из `data-den`.
         Два источника одной даты разошлись бы при первой же правке разметки. */
      pomenyalos(el, 'kab:' + el.dataset.gruppa + ':' + el.dataset.den,
        {put:'/api/kabinety', telo:{gruppa:el.dataset.gruppa, kabinet:k,
                                    data:el.dataset.den}});
    }
  });

  document.addEventListener('click', function(ev){
    const krest = ev.target.closest('.tabl[data-snyat]');
    if(krest){
      const sid = +krest.dataset.snyat, sl = +krest.dataset.slot;
      krest.classList.add('snyato');
      pomenyalos(krest, 'shk:' + sid + ':' + sl,
        {put:'/api/enrollment', telo:{student_id:sid, slot:sl, teacher_id:null,
                                      gruppa: krest.dataset.gruppa}});
      return;
    }
  });

  if(panel){
  document.getElementById('sbrosit').addEventListener('click', function(){
    if(pravki.size === 0) return;
    if(!window.confirm('Отменить ' + pravki.size + ' ' + slovo(pravki.size)
        + ' и вернуть как было?')) return;
    pravki.clear();
    obnovit();
    pomnit();
    location.reload();
  });

  document.getElementById('sohranit').addEventListener('click', async function(){
    if(pravki.size === 0) return;
    const spisok = Array.from(pravki.entries());
    soob.className = 'soob idet';
    soob.textContent = 'сохраняю…';
    for(let i = 0; i < spisok.length; i++){
      const [klyuch, op] = spisok[i];
      soob.textContent = 'сохраняю ' + (i + 1) + ' из ' + spisok.length + '…';
      let otvet, dannye = {};
      try{
        otvet = await fetch(op.put, {method:'POST',
          headers:{'Content-Type':'application/json'}, body: JSON.stringify(op.telo)});
      }catch(err){
        soob.className = 'soob ploho';
        soob.textContent = 'НЕ СОХРАНЕНО: сервер недоступен (' + err + '). '
          + 'Сохранено до этого: ' + i + ' из ' + spisok.length + '.';
        return;
      }
      try{ dannye = await otvet.json(); }catch(err){}
      if(!otvet.ok){
        /* 🔴 ОСТАНАВЛИВАЕМСЯ НА ПЕРВОМ ОТКАЗЕ. Идти дальше значило бы оставить
           половину правок применённой, а человека — в уверенности, что применилось
           всё либо ничего. Сохранённое до отказа названо числом. */
        soob.className = 'soob ploho';
        soob.textContent = 'НЕ СОХРАНЕНО (' + otvet.status + '): '
          + (dannye.error || 'сервер отказал')
          + ' · применено до отказа: ' + i + ' из ' + spisok.length;
        return;
      }
      pravki.delete(klyuch);
    }
    obnovit();
    pomnit();
    location.reload();
  });

  }
  obnovit();
})();
</script>"""


def verh_prava(kt) -> str:
    """The right-hand end of the top bar: what this role may do, and nothing else."""
    # ── ЧЕМ РЕЖИМЫ ОТЛИЧАЮТСЯ, ЦЕЛИКОМ И В ОДНОМ МЕСТЕ ───────────────────────
    # Гость видит кнопку «Вход». Организатор — метку режима, кнопку «Выход» и
    # скрипт правки. Больше ничем: вся остальная разметка у них общая, потому
    # что порождена одним кодом.
    # 🔴 «Вход» ОТКРЫВАЕТ ОКНО, а не уводит на другую страницу. Ссылка на `/vhod`
    # оставлена в `href` нарочно: без JavaScript она по-прежнему работает и ведёт
    # на настоящую страницу входа. Окно — улучшение поверх работающего, а не
    # замена его на то, что ломается при первой же ошибке в скрипте.
    # 🔴 СОХРАНИТЬ И СБРОСИТЬ СТОЯТ РЯДОМ С ВЫХОДОМ, В ВЕРХНЕЙ ПАНЕЛИ. Нижняя
    # плашка убрана: она занимала низ экрана постоянно и объясняла сама себя
    # фразой, которой владелец не поверил ни секунды («правок нет — можно менять
    # распределение»). Кнопке не нужна подпись — ей нужно быть на виду и гаснуть,
    # когда нажимать нечего. Число несохранённых правок стоит на самой кнопке.
    # 🔴 НА ЭКРАНЕ ЗАНЯТИЯ КНОПКИ «СОХРАНИТЬ» НЕТ, И ЕЁ ОТСУТСТВИЕ — ЧАСТЬ ОТВЕТА.
    # Владелец 07.09: *«распределение на день не нужно писать кнопку „Сохранить“…
    # там просто нужно сразу сохраняться. А постоянное распределение не нужно
    # сохранять сразу, потому что там можно долго его двигать и в итоге прийти к
    # оптимальному варианту, нажать „Сохранить“, и дальше оно влияет»*. Кнопка,
    # стоящая там, где ничего не копится, обещает несуществующий шаг: человек
    # уходит со страницы, не нажав её, и не знает, сохранилось ли.
    if kt.ADMIN and not kt.den:
        verh_prava = ('<span class="verh-prava" id="panel-pravok">'
                      '<button type="button" id="sbrosit" class="vtoraya" disabled>Сбросить</button>'
                      '<button type="button" id="sohranit" class="glavnaya" disabled>'
                      'Сохранить<span class="schyot-pravok" id="skolko-pravok"></span></button>'
                      '<a class="vhod" href="/vyhod">Выход</a></span>')
    elif kt.ADMIN:
        verh_prava = ('<span class="verh-prava">'
                      '<span class="srazu">правки сохраняются сразу</span>'
                      '<a class="vhod" href="/vyhod">Выход</a></span>')
    else:
        verh_prava = ('<span class="verh-prava">'
                      '<a class="vhod" href="/vhod" data-otkryt-vhod>Вход</a></span>')
    return verh_prava


#: Тап по клетке кондуита. Владелец 07.09: «я хочу, чтобы можно было нажимать на
#: пустую клеточку на кондуите и чтобы там появлялась галочка… вид остаётся тем же
#: самым, просто клетки должны тапаться».
#:
#: 🔴 ЗАПИСЬ ИДЁТ В ЧУЖУЮ ДВЕРЬ, И ЭТО ГЛАВНОЕ СВОЙСТВО ЭТОГО СКРИПТА. `/api/priyom`
#: — единственная дверь записи отметок (`veb/priyom.py`), а она пишет через
#: `MarkingService`, который несёт идемпотентность и снятие событием `retract` со
#: ссылкой `reverses_id`. Кондуит по-прежнему НЕ пишет в базу сам и остаётся тем,
#: чем был, — проекцией журнала; второго журнала отметок в проекте не появилось.
#:
#: 🔴 КНОПКА НЕСЁТ ЦЕЛЕВОЕ СОСТОЯНИЕ, А НЕ «ПЕРЕКЛЮЧИ». Того требует устройство
#: сервиса: два тапа, пришедшие в любом порядке, оставляют одну и ту же клетку и
#: один ряд в журнале, а не два.

PRIMENIT_SKRIPT = r"""
<script>
/* ── «ПРИМЕНИТЬ ПОСТОЯННОЕ К ЭТОМУ ДНЮ» ────────────────────────────────────────
   Кнопка в верхней строке дня рождается СКРЫТОЙ и пустой. Этот скрипт спрашивает
   сервер, есть ли что применять, и только тогда её показывает — с числом.

   🔴 ЧИСЛО СПРАШИВАЕТСЯ У СЕРВЕРА, А НЕ СЧИТАЕТСЯ ЗДЕСЬ. Сколько на дне ручных
   перекрытий — знает тот же слой, что их снимает; посчитай их браузер по разметке,
   и правил стало бы двое. Ровно та болезнь, от которой лечится вся эта страница
   (см. PRAVKA_SKRIPT).

   Ноль перекрытий — кнопки НЕТ ВОВСЕ, а не серая: владелец 10.09 дословно «не
   заводить орган, который ничего не делает». */
(function(){
  const knopka = document.getElementById('primenit-post');
  if (!knopka) return;                 // гость, или постоянное распределение
  const den = knopka.dataset.den;
  if (!den) return;

  function slovo(n){                   // «правку · правки · правок» — по-русски
    const d = n % 10, dd = n % 100;
    if (d === 1 && dd !== 11) return 'правку';
    if (d >= 2 && d <= 4 && (dd < 12 || dd > 14)) return 'правки';
    return 'правок';
  }

  function sprosit(){
    fetch('/api/den/perekrytiya?den=' + encodeURIComponent(den), {credentials:'same-origin'})
      .then(function(o){ return o.ok ? o.json() : null; })
      .then(function(d){
        if (!d || !d.n) { knopka.hidden = true; return; }   // ноль — кнопки нет
        knopka.textContent = 'Применить постоянное · ' + d.n;
        knopka.title = 'снимет ' + d.n + ' ручн' + (d.n === 1 ? 'ую ' : 'ых ')
                     + slovo(d.n) + ' за этот день'
                     + (d.shkolniki && d.shkolniki.length ? ': ' + d.shkolniki.join(', ') : '');
        knopka.dataset.skolko = d.n;
        knopka.hidden = false;
      })
      .catch(function(){ knopka.hidden = true; });
  }

  knopka.addEventListener('click', function(){
    const n = Number(knopka.dataset.skolko || 0);
    if (!n) return;
    if (!confirm('Снять ' + n + ' ручн' + (n === 1 ? 'ую ' : 'ых ') + slovo(n)
                 + ' за этот день и вернуть постоянное распределение?')) return;
    knopka.disabled = true;
    fetch('/api/den/primenit-postoyannoe', {
      method:'POST', credentials:'same-origin',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({den: den})
    }).then(function(o){
      if (!o.ok) throw new Error('otkaz');
      /* Страница ПЕРЕЧИТЫВАЕТСЯ, а не правится на месте: что стало с распределением
         после снятия перекрытий, считает сервер — здесь этого знания нет. */
      location.reload();
    }).catch(function(){
      knopka.disabled = false;
      alert('Не удалось применить постоянное. Попробуйте ещё раз.');
    });
  });

  sprosit();
})();
</script>
"""

KONDUIT_SKRIPT = """
<script>
(function () {
  // 🔴 ВТОРОЙ ТАП СНИМАЕТ ГАЛОЧКУ, А НЕ СТАВИТ КРЕСТИК. Владелец 07.09, увидев
  // работающий тап: «второй тап должен снимать галочку, а не ставить крестик».
  // Целевое состояние «пусто» — это событие `erratum`, и оно доменно верное имя
  // для «нажал по ошибке»: запись вычёркивается из статистики целиком, и клетка
  // снова становится долгом. `retract` значит другое — «сдал и не защитил», и
  // такая клетка перестала бы быть долгом; крестик остаётся законным состоянием
  // (735 таких событий в журнале от прошлых лет), но ставится не кнопкой.
  // Журнал по-прежнему только ДОПИСЫВАЕТСЯ: `erratum` добавляет строку со ссылкой
  // на ту, которую вычёркивает, и ничего не удаляет.
  var DALEE = {"":"solved", "\u2713":"empty", "x":"solved"};
  var ZNAK = {"empty":"", "solved":"\u2713", "retracted":"x"};
  var KLASS = {"empty":"", "solved":"vsyo", "retracted":"snyato"};
  function narisovat(td, s) {
    td.className = KLASS[s] || "";
    td.textContent = ZNAK[s];
  }
  // 🔴 ОБНОВЛЕНИЕ СТРАНИЦЫ БОЛЬШЕ НЕ ВЫБРАСЫВАЕТ НА ГЛАВНУЮ. Владелец 07.09:
  // «когда я обновляю страницу кондуита, меня выкидывает на главную, так не должно
  // быть». Вкладки сделаны радиокнопками — устройство, на котором стоит весь сайт и
  // которое трогать не надо, — но их состояние живёт только в DOM и умирает с
  // перезагрузкой. Здесь оно просто ЗАПОМИНАЕТСЯ: какая вкладка была выбрана в
  // каждой группе, та и восстанавливается. Разметка не меняется ни на байт, и при
  // выключенном хранилище всё работает ровно как раньше.
  var PAMYAT = "spetsmat-vkladki";
  function zapomnit() {
    try {
      var bylo = {};
      document.querySelectorAll("input.rd:checked").forEach(function (r) {
        bylo[r.name] = r.id;
      });
      localStorage.setItem(PAMYAT, JSON.stringify(bylo));
    } catch (e) { /* приватное окно или запрет хранилища — молча живём без памяти */ }
  }
  function vspomnit() {
    try {
      var bylo = JSON.parse(localStorage.getItem(PAMYAT) || "{}");
      Object.keys(bylo).forEach(function (imya) {
        var r = document.getElementById(bylo[imya]);
        if (r && r.name === imya) { r.checked = true; }
      });
    } catch (e) { /* см. выше */ }
  }
  vspomnit();
  document.addEventListener("change", function (sob) {
    if (sob.target.classList && sob.target.classList.contains("rd")) { zapomnit(); }
  });

  /* 🔴 КНОПКА «ОТМЕНИТЬ» — ДЛЯ СЛУЧАЙНОГО ТАПА, И ОНА ПОМНИТ РОВНО ОДИН ХОД.
     Владелец 10.09: «хочется, чтобы в кондуите была кнопка отменить, если случайно
     ткнул куда-то (особенно с телефона легко это сделать)».
     ОДИН ход, а не стопка: на занятии тапают быстро и много, и стопка отмен
     превратилась бы в способ незаметно откатить чужую работу. Отменяется последнее
     СВОЁ действие на этой странице — то, которое человек только что видел.
     Отмена идёт ТОЙ ЖЕ дверью `/api/priyom` с прежним состоянием как целевым:
     журнал только дописывается, и «отменить» здесь — это не удаление события, а
     возврат клетки в то, что стояло до тапа. */
  /* Знак в клетке → состояние, которым его вернуть. Обратная таблица к ZNAK. */
  var SOSTOYANIE_ZNAKA = {"": "empty", "\u2713": "solved", "x": "retracted"};
  /* Адрес клетки на странице. Пара (школьник, задача) уникальна в решётке, и она же
     лежит в записи очереди — по ней клетка находится и после перезагрузки. */
  function kletka(m) {
    if (!m) { return null; }
    return document.querySelector('#s-kond .kond td[data-u="' + m.u
                                  + '"][data-z="' + m.z + '"]');
  }
  /* Как назвать клетку человеку в сообщении об отказе. Фамилия — в первом столбце
     строки, задача — в шапке того же столбца. Ни того, ни другого может не быть
     (личная вкладка школьника устроена иначе), поэтому подпись необязательна. */
  function podpis(td) {
    try {
      var ryad = td.closest("tr"), tabl = td.closest("table");
      var kto = ryad && ryad.querySelector("td.kto b");
      var shapka = tabl && tabl.tHead && tabl.tHead.rows[0];
      var stolb = shapka && shapka.cells[td.cellIndex];
      return [kto ? kto.textContent.trim() : "",
              stolb ? stolb.textContent.trim() : ""].filter(Boolean).join(" · ");
    } catch (e) { return ""; }
  }

  /* 🔴 ТАП БОЛЬШЕ НЕ ЖДЁТ СЕТЬ — ОН ЛОЖИТСЯ В ОЧЕРЕДЬ. Владелец 10.09: «если вдруг
     пропал интернет, ты мог всё равно внести плюсик, поставить галочку, и она бы
     вносилась в тот момент, когда интернет появится». Поэтому здесь больше нет ни
     `fetch`, ни таймаута, ни класса `zhdyot`: всё это уехало в транспорт
     (`veb/razdely/ochered.py`), вместе с прежней десятисекундной отсечкой, прежним
     разбором ответа и прежним «клетка возвращается в кликабельное состояние».
     ЗДЕСЬ ОСТАЛОСЬ РОВНО ДВА ДЕЙСТВИЯ, И ОБА МГНОВЕННЫЕ: нарисовать целевое
     состояние и поставить запись в очередь. Клетка НЕ блокируется — блокировка была
     нужна, только пока тап ждал ответа, а теперь ждать нечего: второй тап по той же
     клетке это законная вторая запись, и уедут они по очереди, в порядке нажатий.
     Дверь по-прежнему одна, `/api/priyom`, и второго пути записи в кондуите нет. */
  function otpravit(td, target, eto_otmena) {
    /* Метки транспорта в «то, к чему вернуть» не попадают: вернуть надо к состоянию
       ЖУРНАЛА, а не к пунктиру, который эта же страница только что нарисовала. */
    /* 🔴 ОБРАТНЫЕ КОСЫЕ В ЭТОМ РЕГУЛЯРНОМ ВЫРАЖЕНИИ УДВОЕНЫ, И ЭТО НЕ ОПЕЧАТКА.
       `KONDUIT_SKRIPT` — ОБЫЧНАЯ питоновская строка, а не сырая, и одиночная
       обратная косая перед `b` дала бы в браузер символ забоя, а перед `s` —
       недопустимую escape-последовательность.
       ЦЕНА, ОПЛАЧЕННАЯ ЖИВЬЁМ: пост-проверка ИЗ ГЛАВНОЙ папки уронила импорт
       `veb/obshchee/karkas.py` («invalid escape sequence»), то есть страница не
       собиралась ВОВСЕ — а в рабочей папке ровно тот же код был зелёным, потому
       что там лежал уже скомпилированный `.pyc`. В комментарии их писать тоже
       нельзя: комментарий лежит ВНУТРИ той же строки. */
    var vernut = td.className.replace(/\\bv-ocheredi\\b|\\botkazano\\b/g, "")
                             .replace(/\\s+/g, " ").trim();
    var znak_byl = td.textContent;
    /* Галочка загорается СРАЗУ, ещё до всякой сети — это и есть починка. Пунктир
       `v-ocheredi` честно говорит, что сервер этого пока не подтвердил. */
    narisovat(td, target);
    /* 🔴 ВЫДЕЛЕНИЕ «ПОСТАВЛЕНО МНОЙ СЕЙЧАС» ДОРИСОВЫВАЕТСЯ ЗДЕСЬ. Класс `moya`
       ставит сервер при отрисовке страницы, но `narisovat` перезаписывает
       `className` целиком — и только что поставленная галочка оказывалась
       невыделенной до следующего открытия страницы. То есть ровно та галочка, ради
       которой владелец и просил выделение («что успел я на этом занятии»), его и не
       получала. Пустая клетка выделения не несёт: выделять нечего. */
    if (target !== "empty") { td.classList.add("moya"); }
    td.classList.add("v-ocheredi");
    td.removeAttribute("title");
    /* Отмена САМА отменяемой не становится: иначе кнопка превратилась бы в
       переключатель двух состояний, и человек, ткнувший её дважды, вернул бы
       ровно то, что отменял. */
    if (!eto_otmena) {
      poslednij = {td: td, sostoyanie: SOSTOYANIE_ZNAKA[znak_byl.trim()] || "empty"};
      pokazat_otmenu(true);
    }
    OCHERED.postavit({
      put: "/api/priyom",
      telo: {student: +td.dataset.u, problem: +td.dataset.z, target: target},
      metka: {u: +td.dataset.u, z: +td.dataset.z, target: target,
              vernut: vernut, znak: znak_byl, podpis: podpis(td)}
    });
  }

  /* 🔴 ОЧЕРЕДЬ ПЕРЕЖИВАЕТ ПЕРЕЗАГРУЗКУ, ЗНАЧИТ ПЕРЕЖИВАЮТ И ГАЛОЧКИ. Страница,
     перечитанная с сервера, знает только журнал — а в журнале ещё нет того, что
     стоит в очереди. Без этой перерисовки человек увидел бы, как его отметки
     «слетели» при обновлении, и это ровно та молчаливая потеря правки, которую
     запрещает точка 4 задания. Записи применяются В ПОРЯДКЕ ОЧЕРЕДИ, поэтому по
     каждой клетке побеждает последний нажатый тап — тот же, что победит на сервере. */
  function perekrasit() {
    return OCHERED.vse().then(function (zapisi) {
      var byli = document.querySelectorAll("#s-kond .kond td.v-ocheredi");
      for (var i = 0; i < byli.length; i++) { byli[i].classList.remove("v-ocheredi"); }
      zapisi.forEach(function (z) {
        var td = kletka(z.metka);
        if (!td) { return; }
        narisovat(td, z.metka.target);
        if (z.metka.target !== "empty") { td.classList.add("moya"); }
        td.classList.add("v-ocheredi");
      });
    }).catch(function () {});
  }

  OCHERED.podpisatsya(function (sob) {
    if (sob.rod === "uehala") {
      var td = kletka(sob.zapis.metka);
      /* Ответ сервера — ПРАВДА журнала, и рисуется она, а не то, что нажал человек:
         соседний преподаватель мог отметить ту же клетку раньше. */
      if (td && sob.dannye && sob.dannye.sostoyanie) {
        narisovat(td, sob.dannye.sostoyanie);
        if (sob.dannye.sostoyanie !== "empty") { td.classList.add("moya"); }
      }
      perekrasit();
    } else if (sob.rod === "otkaz") {
      var otk = kletka(sob.zapis.metka);
      if (otk) {
        /* Причина стоит и на самой клетке: полосу отказов человек закроет, а
           вопрос «какая именно клетка не сохранилась» останется. */
        otk.className = sob.zapis.metka.vernut;
        otk.textContent = sob.zapis.metka.znak;
        otk.classList.add("otkazano");
        otk.title = sob.pochemu || "не записалось";
      }
      perekrasit();
    } else if (sob.rod === "postavlena") {
      perekrasit();
    }
  });
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", perekrasit);
  } else { perekrasit(); }

  var poslednij = null;          // {td, sostoyanie} — куда и во что вернуть
  var knopka_otmeny = null;

  function pokazat_otmenu(vidno) {
    if (!knopka_otmeny) {
      knopka_otmeny = document.getElementById("otmenit-tap");
    }
    if (knopka_otmeny) { knopka_otmeny.hidden = !vidno; }
  }

  document.addEventListener("click", function (sob) {
    var otm = sob.target.closest("#otmenit-tap");
    if (otm) {
      if (!poslednij) { return; }
      var cel = poslednij;
      poslednij = null;
      pokazat_otmenu(false);
      otpravit(cel.td, cel.sostoyanie, true);
      return;
    }
    var td = sob.target.closest("#s-kond .kond td[data-u]");
    /* Клетка больше не бывает заблокированной: тап не ждёт сети (см. `otpravit`). */
    if (!td) { return; }
    var bylo = td.textContent.trim();
    otpravit(td, DALEE[bylo] || "solved", false);
  });

  // 🔴 ШАПКА КОНДУИТА ЛИПНЕТ К НИЗУ МЕНЮ, А НЕ К ЧИСЛУ 4rem.
  //
  // Стиль держал `top:4rem` — измеренную высоту меню НА НОУТБУКЕ (64px). На
  // телефоне меню ниже: 53px при ширине 375. Одиннадцать пикселей между меню и
  // шапкой — щель, в которую видно проезжающие строки. Хуже другое: узкий экран
  // переносит меню на две строки, оно становится ВЫШЕ 64px, и тогда липкая шапка
  // встаёт ПОД ним — то есть залипает исправно, а увидеть её нельзя. Снаружи это
  // неотличимо от «шапка не залипает вовсе», и именно так это и выглядело.
  //
  // Число здесь больше не пишется: высота меню СПРАШИВАЕТСЯ у самого меню и едет в
  // `--vysota-menu`, а стиль читает её. Комментарий в `konduit.py`, требовавший
  // «изменится меню — изменить и здесь», можно больше не исполнять руками.
  // ResizeObserver ловит и поворот экрана, и перенос строки меню; там, где его нет,
  // остаётся `resize` и посадка при загрузке, а без JS вовсе — прежние 4rem
  // запасным значением в самом `var()`.
  // ⚠ НАБЛЮДАТЕЛЬ ХРАНИТСЯ В ПЕРЕМЕННОЙ, И ЭТО НЕ СТИЛЬ. `new ResizeObserver(f)
  // .observe(el)` без сохранённой ссылки Chrome собирает сборщиком мусора вместе с
  // подпиской: первый вызов проходит, а дальше наблюдатель молча перестаёт
  // существовать. Поймано живьём здесь же — при 1440 меню стало 64px, а переменная
  // осталась 53px. Ссылка держится замыканием этой функции, которое живо, пока жив
  // слушатель `resize` на ней.
  var menu = document.querySelector(".menu");
  var nablyudatel = null;
  if (menu) {
    var otdat = function () {
      document.documentElement.style.setProperty(
        "--vysota-menu", menu.getBoundingClientRect().height + "px");
    };
    otdat();
    window.addEventListener("resize", otdat);
    window.addEventListener("orientationchange", otdat);
    if (window.ResizeObserver) {
      nablyudatel = new ResizeObserver(otdat);
      nablyudatel.observe(menu);
    }
  }
})();
</script>
"""


# 🔴 THE PERMANENT ARRANGEMENT HAS ITS OWN ADDRESS, AND A CSS TAB CANNOT BE OPENED
# BY ONE — SO THREE LINES OPEN IT. `/raspredelenie/postoyannoe` serves this very page
# (`veb/server.py`), and which tab is `checked` is decided by
# `tools/sobrat_stranicu.sobrat_html`, which lies OUTSIDE the зона of this заход: the
# switch is therefore made here, where the зона reaches, and not by editing the file
# that builds the page.
#
# It runs for every role, guest included, and that is deliberate: the guest build
# `docs/index.html` is served at that address too, and a guest following the link from
# the lesson page must land on the same section as everybody else. It touches nothing
# on any other address — `/` opens exactly as it did.
VKLADKA_SKRIPT = r"""
<script>
/* 🔴 НА ЛЮБОМ АДРЕСЕ РАСПРЕДЕЛЕНИЯ ОТКРЫТА ВКЛАДКА РАСПРЕДЕЛЕНИЯ, И ЭТО СИЛЬНЕЕ
   ПАМЯТИ БРАУЗЕРА. Цена прежней редакции, измеренная владельцем на боевом сайте:
   ПУСТОЙ ЭКРАН. `PRAVKA_SKRIPT` восстанавливает последнюю открытую вкладку из
   `sessionStorage`, а на странице занятия разделов «Класс» и «Листки» нет вовсе
   (их расписание читает `kt.DNI`, а он тут из одного дня). Восстановленный
   `p-start` показывал секцию, которой на странице не существует, — и человек
   видел меню и НИЧЕГО под ним. Его слова: «нажимаю распределение, у меня моргает
   распределение, но я остаюсь на вкладке кондуит… я ничего не вижу».

   Поэтому: адрес сильнее памяти, и проверка идёт по префиксу, а не по одному
   пути. Скрипт стоит ПОСЛЕДНИМ (см. `skripty`), чтобы перебить восстановление. */
/* Панель занятий закрывается кликом мимо неё: она перекрывает таблицу, а
   отдельная кнопка «закрыть» — ещё один предмет на экране, где их и так много. */
document.addEventListener('click', function(ev){
  var kal = document.getElementById('p-kal');
  if(!kal || !kal.checked) return;
  if(ev.target.closest('.zan-navig')) return;
  kal.checked = false;
});
var _put = location.pathname.replace(/\/+$/, '');
if(_put === '/raspredelenie' || _put.indexOf('/raspredelenie/') === 0){
  var rasp = document.getElementById('p-rasp');
  if(rasp) rasp.checked = true;
}
/* 🔴 АДРЕС `/#s-list` ОТКРЫВАЕТ ВКЛАДКУ «ЛИСТКИ», А НЕ ПРОСТО ПРОКРУЧИВАЕТ В НИКУДА.
   Такая ссылка стоит в меню страницы занятия с 07.09 и до сих пор не открывала
   ничего: раздел скрыт, пока не отмечена его радиокнопка, а якорь радиокнопок не
   трогает — человек попадал на заглавную и видел «Класс». Теперь на неё же ведут
   пункты меню КАБИНЕТА, страницы отдельной от оболочки, и без этих четырёх строк
   уйти из кабинета можно было бы только на «Класс» и «Распределение».
   Правило одно на все разделы: `#s-XXX` отмечает `p-XXX`, если такая пара есть. */
var _yakor = (location.hash || '').replace('#', '');
if(_yakor.indexOf('s-') === 0){
  var _vkl = document.getElementById('p-' + _yakor.slice(2));
  if(_vkl && _vkl.classList.contains('rd')) _vkl.checked = true;
}
</script>
"""


def skripty(kt, drakon_skript: str) -> str:
    """The scripts of the page. Not the frame — its behaviour.

    The dragon curve belongs to the front page and is handed in from there; the
    login window and the edit panel belong to the shell and live in this file.

    🔴 Тап по кондуиту едет ровно тем, кто кондуит ВИДИТ, и нового права под него не
    заведено: `videt-konduit` уже отделяет вошедших от гостя, а гостю раздел не
    рисуется вовсе (`tools/sobrat_stranicu.sobrat()` пишет в `docs/index.html`
    гостевую сборку). Поэтому скрипт не может попасть на публичную страницу вместе
    с чужими фамилиями — его там просто нет.
    """
    # Окно входа лежит в странице ВСЕГДА, у обеих ролей: так каркас у них
    # совпадает буквально, и гейту нечего прощать.
    # 🔴 VKLADKA_SKRIPT GOES LAST, AND THE ORDER IS LOAD-BEARING. `PRAVKA_SKRIPT`
    # restores the tab the visitor last had open out of `sessionStorage`, inline and
    # immediately; standing before it, the address-driven switch would be overwritten
    # by yesterday's choice and `/raspredelenie/postoyannoe` would open on «Класс».
    # 🔴 ОЧЕРЕДЬ СТОИТ ПЕРЕД КОНДУИТОМ, И ПОРЯДОК ЗДЕСЬ НЕСУЩИЙ. `KONDUIT_SKRIPT`
    # зовёт `OCHERED.podpisatsya` в теле своей IIFE, то есть НЕМЕДЛЕННО при разборе
    # страницы; стоя первым, он получил бы `OCHERED is not defined` и вместе с
    # подпиской унёс бы весь свой скрипт — то есть и тап, и историю клетки, и липкую
    # шапку. Импорт лежит внутри функции по той же причине, что и у самого кондуита
    # ниже: каркас не имеет права знать, какие разделы существуют, на уровне модуля.
    from veb.razdely.ochered import skript as ochered_skript
    return (drakon_skript + VHOD_SKRIPT
            + (PRAVKA_SKRIPT + PRIMENIT_SKRIPT if kt.ADMIN else "")
            + ((ochered_skript() + KONDUIT_SKRIPT) if kt.mozhno("videt-konduit") else "")
            + VKLADKA_SKRIPT)


def razdel_raspredeleniya(kt, *, vid_vse, vid_prepodavateli, vkladka_gruppy) -> str:
    """The distribution page: the tab row, and three sections hung in it.

    🔴 THE THREE SECTIONS ARRIVE AS FUNCTIONS, THEY ARE NOT IMPORTED HERE. The
    shell must not know which modules exist — that is the whole point of cutting
    the page up, and an import here would put `karkas` back on top of every
    section it is supposed to be independent of. The composition root passes them
    in; see `tools/sobrat_stranicu.sobrat_html`.
    """
    # ── ПРАВАЯ ЧАСТЬ СТРОКИ ВКЛАДОК ─────────────────────────────────────────
    # 🔴 ГОСТЮ — БЛИЖАЙШЕЕ ЗАНЯТИЕ, А НЕ ПЕРЕКЛЮЧАТЕЛЬ ДНЯ. Владелец 06.09: «для
    # распределения на общей странице не нужна вкладка понедельник и четверг —
    # имеется в виду распределение на ближайшее занятие… лучше написать „7 сентября“
    # и время сразу». Человек, зашедший посмотреть, куда идти, спрашивает «куда мне
    # СЕГОДНЯ», а не «покажи мне четверг».
    #
    # 🔴 И ОРГАНИЗАТОРУ ПЕРЕКЛЮЧАТЕЛЯ БОЛЬШЕ НЕТ — РЕШЕНИЕ ВЛАДЕЛЬЦА 5 ОТ 07.09,
    # дословно: «я бы делал одну табличку на оба дня… по умолчанию оба значения
    # одинаковые». Переключатель отвечал на вопрос «покажи мне четверг», а
    # спрашивают здесь другое — «разошлись ли у этого ребёнка понедельник с
    # четвергом», и на него переключатель ответить не может по построению: два
    # состояния экрана нельзя увидеть одновременно. Оба дня теперь стоят в одной
    # строке таблицы, каждый своим полем; какой день где — говорит шапка столбцов.
    # Возможность `pereklyuchat-dni` из словаря НЕ убрана: словарь ролей — чужая
    # территория этого захода, и мёртвая возможность безвреднее, чем правка прав
    # заодно.
    #
    # 🔴 СТРОКА «БЛИЖАЙШЕЕ ЗАНЯТИЕ» ОСТАЁТСЯ ГОСТЕВОЙ, И `if not kt.ADMIN` ЗДЕСЬ —
    # НЕ УКРАШЕНИЕ, А ТРЕБОВАНИЕ ГЕЙТА. `data-tolko-gost` снимается ТОЛЬКО с
    # гостевой стороны (`_snyat_gostevoe`), поэтому тот же элемент, оставленный
    # организатору, разводит каркасы: гость — пусто, организатор — строка. Ровно
    # так же и по той же причине собирается `kabinety_verh` ниже.
    if kt.den:
        # 🔴 НА ЗАНЯТИИ В ЭТОЙ СТРОКЕ СТОИТ ДАТА, И ОНА ЖЕ ОРГАН. Стрелки ведут на
        # соседнее занятие, клик по дате открывает календарь: владелец правит не
        # только сегодня — *«я могу пойти назад или вперёд, например, вперёд на
        # текущем распределении, на 2-3 занятия поставить, что этот преподаватель
        # болеет»*. Рядом — дверь в постоянное, и она названа словом, а не значком.
        from veb.razdely.zanyatie import panel_vybora, sosednee_zanyatie
        den = kt.den
        zanyatie_verh = (
            '<span class="zan-navig">'
            f'<a class="strelka" href="/raspredelenie?den={e(sosednee_zanyatie(den, -1))}"'
            f' title="предыдущее занятие" aria-label="предыдущее занятие">‹</a>'
            f'<label class="data-zan" for="p-kal" title="выбрать занятие">'
            f'{e(kt.DNI["den"][0])}, {e(kt.po_russki_kratko(den))}</label>'
            f'<a class="strelka" href="/raspredelenie?den={e(sosednee_zanyatie(den, +1))}"'
            f' title="следующее занятие" aria-label="следующее занятие">›</a>'
            f'<a class="k-drugomu" href="/raspredelenie/postoyannoe">Постоянное</a>'
            # 🔴 «ПРИМЕНИТЬ ПОСТОЯННОЕ К ЭТОМУ ДНЮ» — КНОПКА, КОТОРАЯ ЗНАЕТ, ЕСТЬ ЛИ
            # ЧТО ПРИМЕНЯТЬ. Владелец 10.09: правки постоянного не видны там, где
            # поверх лежит ручное перекрытие, и снимать их по одному через пустое
            # значение — работа руками. Требования его же, дословно: кнопка стоит на
            # экране «Распределение» НА ЛЮБОЙ вкладке; перекрытий ноль — кнопки НЕТ
            # ВОВСЕ, а не серая («не заводить орган, который ничего не делает»); есть
            # — на кнопке ЧИСЛО, чтобы не нажимать наугад.
            #
            # Здесь она рождается СКРЫТОЙ и без числа: сколько перекрытий на этом дне,
            # знает только `GET /api/den/perekrytiya`, и спрашивать его надо в момент
            # ПОКАЗА, а не сборки — страница стоит открытой весь урок, пока день правят
            # с телефонов. Показывает и наполняет её `PRIMENIT_SKRIPT`.
            #
            # `data-org` обязателен: кнопка ПИШЕТ в базу, у гостя её нет, и гейт
            # каркаса сверяет гостевой остаток побайтово — без метки он покраснеет.
            # Ветка `elif kt.ADMIN` ниже — постоянное распределение, и кнопки там нет
            # по построению: применять к «всегда» нечего (требование 6).
            # 🔴 РИСУЕТСЯ ТОЛЬКО ВОШЕДШЕМУ, И `data-org` ЭТОГО НЕ ДЕЛАЕТ. Метка —
            # для СВЕРКИ каркасов (`_snyat_organy` убирает помеченное у роли и
            # сравнивает остаток с гостевым побайтово), а не запрет рисовать.
            # Кнопка, отданная гостю, осталась бы у него и исчезла у организатора —
            # ровно то расхождение, которое гейт каркаса ловит и на котором
            # страница перестаёт собираться.
            + (f'<button type="button" class="k-drugomu primenit-post"'
               f' id="primenit-post" data-org="pravit-raspredelenie"'
               f' data-den="{e(den)}" hidden></button>' if kt.ADMIN else "")
            + panel_vybora(den) +
            "</span>")
    elif kt.ADMIN:
        # На постоянном — дверь в обратную сторону: к ближайшему занятию.
        # `data-org` обязателен: этой двери у гостя нет, и гейт каркаса снимает
        # её вместе с остальными органами, сверяя остаток с гостевым побайтово.
        zanyatie_verh = ('<span class="zan-navig" data-org="pravit-raspredelenie">'
                         '<a class="k-drugomu" href="/raspredelenie">'
                         'Распределение на занятие</a></span>')
    else:
        zanyatie_verh = (
            f'<span class="skoro" data-tolko-gost>{e(kt.po_russki(kt.DNI[kt.blizh][2]))}'
            f' · {e(kt.DNI[kt.blizh][0])} · {VREMYA[kt.blizh]}</span>')

    # 🔴 КАБИНЕТ ГРУППЫ ПЕРЕЕХАЛ НАВЕРХ, В ТУ ЖЕ СТРОКУ. Он занимал отдельную
    # строку под вкладками — ради одного числа. Показывается только на вкладке
    # своей группы; какая вкладка открыта, знает CSS, а не скрипт.
    kabinety_verh = "".join(
        f'<span class="kab-verh kab-verh-{kod}" data-tolko-gost>'
        + kt.kab_html(kt.blizh, kod) + "</span>"
        for kod in ("В", "Д", "Н")) if not kt.ADMIN else ""
    return f"""<section class="str holst" id="s-rasp">
  <!-- Ни заголовка «Распределение», ни отдельной строки под поиск: название
       раздела уже стоит во вкладке наверху, повторять его нечем и незачем.
       Вкладки — одной строкой; дней в ней больше нет, они внутри таблицы. -->
  <input class="rd" type="radio" name="vk" id="t-shk" checked>
  <input class="rd" type="radio" name="vk" id="t-prep">
  <input class="rd" type="radio" name="vk" id="t-В">
  <input class="rd" type="radio" name="vk" id="t-Д">
  <input class="rd" type="radio" name="vk" id="t-Н">
  <div class="tabbar tabbar-rasp">
    <label for="t-shk">школьникам</label><label for="t-prep">принимающим</label>
    <label for="t-В">В</label><label for="t-Д">Д</label><label for="t-Н">Н</label>
    <span class="zanyatie">{zanyatie_verh}</span>
    {kabinety_verh}
  </div>
  <section class="vid" id="v-shk">{vid_vse()}</section>
  <section class="vid" id="v-prep">{vid_prepodavateli()}</section>
  {"".join(f'<section class="vid" id="v-{k}">{vkladka_gruppy(k)}</section>'
           for k in ("В", "Д", "Н"))}
</section>"""


# 🔴 ВКЛАДКА «КАБИНЕТ» — ССЫЛКА, А НЕ РАДИОКНОПКА, И СТОИТ ВТОРОЙ ПОСЛЕ «КЛАССА».
# Требование владельца 10.09 (`TZ-DOBOR-10-09.md` H1.1, H2.1, H2.2): *«поиск очень
# широкий, ничего не поменяется, если я добавлю кабинет первой кнопкой или второй
# после класса»*, и название — «Кабинет», без слова «мой».
#
# 🔴 УСЛОВИЕ — `prepod_id`, А НЕ ВОЗМОЖНОСТЬ `videt-svoyo`, И ЭТО ЗАМЕР, А НЕ ВКУС.
# На скриншоте `20` вошёл САМ ВЛАДЕЛЕЦ: справа в шапке стоят «Сбросить/Сохранить»,
# то есть роль `organizator`, у которой `videt-svoyo` НЕТ (`VOZMOZHNOSTI` выше).
# Вкладка, повешенная на эту возможность, была бы невидима ровно тому человеку,
# который её попросил. `prepod_id` — то же самое условие, при котором `glavnaya.py`
# печатает «Мой кабинет →»: ссылка и вкладка появляются и исчезают вместе.
# Гостевая сборка (`prepod_id is None`) не получает ни того, ни другого, и
# `docs/index.html` этой правкой не меняется.
#
# 🔴 ПОМЕТКА `data-org` ЗДЕСЬ НЕ НУЖНА И БЫЛА БЫ ВРЕДНА. Окно, которое сверяет гейт
# каркаса, начинается с `id="s-rasp"` (`tools/sobrat_stranicu.py:160`); меню стоит
# ВЫШЕ него и в сравнение не попадает. А пометка `videt-svoyo` на этом пункте
# сняла бы его со страницы преподавателя и оставила у организатора — то есть ровно
# наоборот тому, зачем пункт заведён.
# ────────────────────────────────────────────────────── РОД ЧЕЛОВЕКА ПО ЕГО ИМЕНИ
#
# 🔴 ЭТО ПОМОЩНИК, А НЕ ПОЛЕ В БАЗЕ, И ПРИЧИНА НАЗВАНА ЗАМЕРОМ. Владелец 11.09:
# «опять у тебя „принял Саша Оревкова“. Ну пол учитывай». Пола в схеме НЕТ:
# `pragma table_info(teachers)` на боевой базе даёт `id · tg_id · name · aka ·
# is_owner · kabinet · aktiven · gruppa`, у `students` его тоже нет. Завести колонку
# значило бы миграцию, а `migrations/` — вне зоны захода, в котором это понадобилось.
# Род поэтому ВЫВОДИТСЯ из имени, и правило записано один раз здесь, а не в каждой
# странице, которой понадобилось сказать «принял».
#
# 🔴 ФАМИЛИЯ СИЛЬНЕЕ ИМЕНИ, И ЭТО НЕ ВКУС, А ЕДИНСТВЕННОЕ, ЧТО РАБОТАЕТ НА ЭТИХ
# ДАННЫХ. Правило «имя на -а/-я значит женское» на живой базе ошибается пять раз из
# девятнадцати: Ваня Яковлев, Даня Макаров, Дима Елисеев, Саша Оревкова, Вася — из
# них четверо мужчины, а пятая женщина с мужским по форме именем. Фамилия при этом
# отвечает верно у всех, у кого она склоняемая; имя спрашивается только там, где
# фамилия несклоняемая (Шнитке, Амбург, Мирошниченко, Маршалл, Тертерян) или её нет
# вовсе (Вика, Надя, Полина, Вася).
#
# 🔴 ПРЕДЕЛ ПРАВИЛА НАЗВАН ВСЛУХ, И ОН ИЗМЕРЕН. Прогон по ВСЕМ людям боевой базы:
# 19 преподавателей из 19 верно, 57 школьников из 57 верно — но последнее лишь
# после того, как замер нашёл «Кахиани Нино» (фамилия несклоняемая, имя грузинское)
# и правило русских окончаний ответило «мужской». Два списка-исключения ниже — это
# ровно те места, где окончание не решает; они короткие нарочно, и оба выросли из
# замера, а не из воображения. Неизвестное имя на -а/-я читается как женское,
# любое другое — как мужское: так верно для подавляющего большинства русских имён,
# и так ошибка остаётся на немаркированной форме.

#: Окончания фамилий. Женские проверяются ПЕРВЫМИ: `-ская` длиннее, чем `-ая`, и
#: обе длиннее, чем `-ий`, а первое совпадение и есть ответ.
FAMILIA_ZHENSKAYA = ("ова", "ева", "ёва", "ина", "ына", "ская", "цкая", "ая", "яя")
FAMILIA_MUZHSKAYA = ("ов", "ев", "ёв", "ин", "ын", "ский", "цкий", "ий", "ый", "ой")

#: Мужские имена, которые кончаются на гласную и потому выглядят женскими. Первые
#: пять взяты с живой базы (Ваня, Даня, Дима, Вася + двуполое Саша), остальные —
#: столь же обычные уменьшительные, которые появятся при первом новом преподавателе.
IMENA_MUZHSKIE_NA_GLASNUYU = frozenset("""
ваня даня дима саша женя валя слава вася гоша миша паша лёша леша коля толя юра
серёжа сережа гриша petya петя костя витя никита илья кузьма фома лука
""".split())


#: Женские имена, которые НЕ кончаются на -а/-я и потому выглядят мужскими.
#: 🔴 ПЕРВОЕ ИМЯ ЗДЕСЬ — НАЙДЕНО ЗАМЕРОМ, А НЕ ПРИДУМАНО. Прогон правила по всем 57
#: школьникам боевой базы дал 56 верных ответов и ровно один неверный: «Кахиани
#: Нино» — фамилия несклоняемая, имя грузинское, и правило русских окончаний
#: отвечало «мужской». Остальные — те русские женские имена на согласную и мягкий
#: знак, которые правило прочитало бы так же и по той же причине.
IMENA_ZHENSKIE_NA_SOGLASNUYU = frozenset("""
нино элисо любовь нинель эсфирь юдифь рахиль суламифь мариам тамар
""".split())


def rod_imeni(imya: str, familiya: str = ""):
    """`'ж'` · `'м'` · `None` — грамматический род человека по тому, как он назван.

    `familiya` называется отдельно там, где порядок слов не «Имя Фамилия»: у
    школьников на этом сайте хранится `surname` + `name`, и последнее слово строки
    там — ИМЯ, а не фамилия. Не названа — фамилией считается последнее слово `imya`,
    именем первое.

    `None` значит «сказать нечего»: пустая строка. Во всех остальных случаях правило
    отвечает — см. разбор его предела выше.
    """
    slova = (imya or "").split()
    if not slova and not (familiya or "").strip():
        return None
    fam = (familiya or (slova[-1] if len(slova) > 1 else "")).strip().lower()
    for konec in FAMILIA_ZHENSKAYA:
        if fam.endswith(konec):
            return "ж"
    for konec in FAMILIA_MUZHSKAYA:
        if fam.endswith(konec):
            return "м"
    lichnoe = (slova[0] if slova else "").strip().lower()
    if not lichnoe:
        return None
    if lichnoe in IMENA_MUZHSKIE_NA_GLASNUYU:
        return "м"
    if lichnoe in IMENA_ZHENSKIE_NA_SOGLASNUYU:
        return "ж"
    return "ж" if lichnoe.endswith(("а", "я")) else "м"


def v_rode(imya: str, muzhskoe: str, zhenskoe: str, familiya: str = "") -> str:
    """Слово в роде этого человека: `v_rode("Саша Оревкова", "принял", "приняла")`.

    Род не определился (человек не назван вовсе) — мужское: оно немаркированное,
    и это единственный случай, когда выбор делается не по данным.
    """
    return zhenskoe if rod_imeni(imya, familiya) == "ж" else muzhskoe


# ───────────────────────────────────── ЧТО СДАНО: СТРОКА НА ЛИСТОК, ЗАДАЧИ КНОПКАМИ
#
# 🔴 ОДИН ВИД СДАЧИ НА ВЕСЬ САЙТ, И ЖИВЁТ ОН ЗДЕСЬ. Владелец 11.09 попросил, чтобы
# клетка журнала открывала то же, что открывает плитка кабинета: «чтобы была
# возможность нажать и посмотреть, что кто сдал», формат — «строка на листок, кнопка
# листка + задачи кнопками». Две страницы, каждая со своей разметкой этого списка,
# разошлись бы на первой же правке и обе остались бы зелёными; разметка поэтому
# написана один раз — ЗДЕСЬ, браузерной функцией, которую обе страницы включают.
#
# 🔴 ФУНКЦИЯ БРАУЗЕРНАЯ, А НЕ ПИТОНОВСКАЯ, И ЭТО НЕ ВКУС. Раскрытие клетки рисуется
# на клиенте из блока JSON: решётка это 57 школьников × 16 занятий, и спрятанная в
# каждой клетке разметка удвоила бы документ ради того, что читатель откроет три
# раза (разбор — `istoria_zanyatij._chto_raskryvaetsya`). Помощник обязан стоять там
# же, где рисуют, иначе он не помощник.
#
# 🔴 ЛИСТОК — ССЫЛКА НА СВОЮ СТРАНИЦУ; ЗАДАЧА — НЕ ССЫЛКА, И ЭТО СКАЗАНО ВСЛУХ.
# У листка адрес есть (`/listki/<номер>`, его отдаёт `veb/server.py::_listok`), у
# отдельной задачи — нет ни одного. Кнопка, которая никуда не ведёт, обещает нажатие
# и не отвечает на него; поэтому задачи нарисованы как кнопки, но являются
# `<span>` — вид владельца, без ложного обещания.

#: Стили вида «что сдано». Рядом с функцией, а не в странице: их двое читателей.
SDACHI_STILI = """
.sd{margin:.3rem 0 0}
.sd-ryad{display:flex;flex-wrap:wrap;align-items:center;gap:.35rem;padding:.18rem 0}
.sd-listok{flex:0 0 auto;min-width:6.5rem;text-decoration:none;font-weight:600;
  color:var(--accent);border:1px solid var(--rule);border-radius:8px;
  padding:.16em .6rem;font-size:.92rem}
.sd-listok:hover{border-color:var(--accent);background:var(--accent-soft)}
.sd-zad{display:inline-block;border:1px solid var(--rule);border-radius:7px;
  padding:.1em .5rem;font-size:.9rem;color:var(--text);background:var(--bg)}
.sd-nichego{color:var(--muted);margin:.3rem 0 0}
"""

#: Браузерная половина того же помощника. Включается страницей ОДИН раз, до её
#: собственного скрипта; обе страницы зовут `Kluchiki.sdachiPoListkam(сдачи, пусто)`.
SDACHI_SKRIPT = """
<script>
window.Kluchiki = window.Kluchiki || {};
(function(){
  function ekran(s){
    var u = document.createElement('span');
    u.textContent = s === null || s === undefined ? '' : String(s);
    return u.innerHTML;
  }
  // `сдачи` — массив `{listok, zadacha}` в порядке листков и задач, как их отдала
  // база (`order by s.ord, p.ord`); порядок здесь не пересчитывается, иначе он стал
  // бы вторым мнением о том, в каком порядке идут листки.
  window.Kluchiki.sdachiPoListkam = function(sdachi, pusto){
    if (!sdachi || !sdachi.length) {
      return '<p class="sd-nichego">' + ekran(pusto) + '</p>';
    }
    var poryadok = [], po = {};
    sdachi.forEach(function(z){
      if (!po[z.listok]) { po[z.listok] = []; poryadok.push(z.listok); }
      po[z.listok].push(z.zadacha);
    });
    return '<div class="sd">' + poryadok.map(function(n){
      return '<div class="sd-ryad"><a class="sd-listok" href="/listki/'
           + encodeURIComponent(n) + '">листок ' + ekran(n) + '</a>'
           + po[n].map(function(z){
               return '<span class="sd-zad">' + ekran(z) + '</span>';
             }).join('')
           + '</div>';
    }).join('') + '</div>';
  };
})();
</script>"""


# ──────────────────────────────────────────── ЧЕТВЕРТЬ: ШЕСТНАДЦАТЬ ЗАНЯТИЙ ВПЕРЁД
#
# 🔴 ЭТО ОБЩИЙ ПОМОЩНИК, А НЕ ЧАСТЬ ЖУРНАЛА, И ИМЕННО ПОЭТОМУ ОН ЗДЕСЬ. Владелец
# 11.09 попросил одну и ту же вещь на ДВУХ экранах: «нужна табличка с узкими
# колонками, распланированная сразу на 16 занятий» (журнал) и «переключатель
# четвертей — как в кабинете». Две страницы, каждая со своим представлением о том,
# где кончается четверть, разошлись бы на первой же правке — и разошлись бы МОЛЧА,
# потому что обе были бы зелёными. Определение четверти живёт тут в одном экземпляре;
# `veb/razdely/istoria_zanyatij.py` и `veb/razdely/kabinet.py` его ЗОВУТ.
#
# 🔴 ЧЕТВЕРТЬ ОПРЕДЕЛЕНА ЗАНЯТИЯМИ, А НЕ КАЛЕНДАРЁМ ПРАЗДНИКОВ, И ЭТО АРИФМЕТИКА
# ВЛАДЕЛЬЦА, А НЕ УПРОЩЕНИЕ ЗА НЕГО: «до конца четверти, примерно 8 недель в
# четверти, то есть 16 клеточек узких». Восемь недель по два занятия — шестнадцать.
# Календарь школьных каникул в этом проекте не хранится НИГДЕ (ни таблицы, ни файла,
# проверено грепом по репозиторию), поэтому граница четверти, выведенная из него,
# была бы выдуманной датой. Шестнадцать занятий подряд от 1 сентября — граница,
# которую можно посчитать из того, что есть.
#
# 🔴 КАКИЕ ДНИ ВООБЩЕ ЯВЛЯЮТСЯ ДНЯМИ ЗАНЯТИЙ, ЗДЕСЬ НЕ РЕШАЕТСЯ. На это отвечает
# ровно одно место — `core.services.sostav_na_den` со своим `SLOTY_ZANYATIJ`
# (пн и чт), и его собственный docstring открывается разбором того, во что обошлось
# второе мнение об этом. Отсюда зовётся его `blizhajshie_zanyatiya`.

#: Сколько занятий в четверти. Слова владельца 11.09, дословно: «16 клеточек узких».
ZANYATIJ_V_CHETVERTI = 16

#: Четвертей в учебном году. 4 × 16 = 64 занятия ≈ 32 недели, то есть сентябрь — май.
CHETVERTEJ_V_GODU = 4

#: Месяц, с которого считается учебный год. Год НЕ вписывается числом: вписанный
#: протухает молча — тот же приём и та же причина, что у
#: `veb/razdely/kabinet.py::nachalo_uchebnogo_goda`.
NACHALO_GODA_MESYAC = 9


def nachalo_uchebnogo_goda(den: str) -> str:
    """`2026-11-03` → `2026-09-01`; `2026-03-03` → `2025-09-01`."""
    d = date.fromisoformat(den)
    god = d.year if d.month >= NACHALO_GODA_MESYAC else d.year - 1
    return date(god, NACHALO_GODA_MESYAC, 1).isoformat()


def chetverti_goda(den: str) -> tuple:
    """Четыре четверти учебного года, содержащего `den`: кортеж кортежей дат.

    Каждая четверть — ровно `ZANYATIJ_V_CHETVERTI` подряд идущих дней занятий,
    считая от 1 сентября. Ни одна дата не повторяется в двух четвертях, и вместе
    они покрывают год без дыр — это одна последовательность, нарезанная на четыре.
    """
    from core.services.sostav_na_den import blizhajshie_zanyatiya

    vse = blizhajshie_zanyatiya(nachalo_uchebnogo_goda(den),
                                ZANYATIJ_V_CHETVERTI * CHETVERTEJ_V_GODU)
    return tuple(tuple(vse[n * ZANYATIJ_V_CHETVERTI:(n + 1) * ZANYATIJ_V_CHETVERTI])
                 for n in range(CHETVERTEJ_V_GODU))


def nomer_chetverti(den: str) -> int:
    """В какой четверти лежит `den` — 1..4.

    День между четвертями (каникулы) относится к БЛИЖАЙШЕЙ СЛЕДУЮЩЕЙ четверти: экран
    открывается на той, к которой человек готовится, а не на той, что кончилась.
    День после последней — четвёртая: за край года эта функция не уходит.
    """
    for nomer, dni in enumerate(chetverti_goda(den), 1):
        if dni and den <= dni[-1]:
            return nomer
    return CHETVERTEJ_V_GODU


#: Стили переключателя. Отдельной строкой, а не внутри страницы, по той же причине,
#: по какой сам переключатель здесь: два экрана, один вид.
CHETVERTI_STILI = """
.chetverti{display:flex;gap:.4rem;align-items:baseline;margin:0 0 1rem;
  font-family:var(--sans)}
.chetverti .cht{text-decoration:none;color:var(--muted);font-weight:600;
  padding:.3em .85rem;border:1px solid var(--rule);border-radius:8px}
.chetverti .cht:hover{color:var(--accent);border-color:var(--accent)}
.chetverti .cht-tut{color:var(--accent);background:var(--accent-soft);
  border-color:var(--accent)}
"""


def perekluchatel_chetvertej(adres: str, tekushchaya: int, den: str = "") -> str:
    """Полоса «1 2 3 4» ссылками на тот же адрес с `?ch=N`.

    🔴 ССЫЛКИ, А НЕ РАДИОКНОПКИ, И ЭТО НЕ ВКУС. Радиокнопка переключает то, что уже
    лежит на странице; четверть — это ДРУГИЕ шестнадцать столбцов и другой блок
    данных к ним, то есть другой ответ сервера. Ссылкой он ещё и делится: адрес
    четверти можно послать человеку, и он откроет ровно её.

    `den` — дата, по которой считается, какие четверти вообще существуют; пустая
    строка значит «сегодня». Он есть в подписи параметров ради тестов и ради
    страницы, которая смотрит не на сегодняшний день.
    """
    segodnya = den or date.today().isoformat()
    vsego = len(chetverti_goda(segodnya))
    punkty = []
    for nomer in range(1, vsego + 1):
        tut = " cht-tut" if nomer == tekushchaya else ""
        punkty.append('<a class="cht%s" href="%s?ch=%d">%d</a>'
                      % (tut, e(adres), nomer, nomer))
    return ('<nav class="chetverti" aria-label="четверть">'
            '<span class="cht-imya">четверть</span>%s</nav>' % "".join(punkty))


MENYU_PUNKT_KABINETA = '<a class="ssyl ssyl-kab" href="/kabinet">Кабинет</a>'

#: 🔴 ВХОД НА `/istoria` — H5.1, И ЭТО ВОССТАНОВЛЕНИЕ, А НЕ НОВАЯ СТРАНИЦА.
#: Владелец 10.09: «вкладка История занятий не видна. Может быть, сделана, но по
#: кнопке не подключена». Измерено: страница `veb/razdely/istoria_zanyatij.py` — 321
#: строка и 29 зелёных тестов, отдаёт 200 и 70 923 байта, а `grep -c 'href="/istoria'`
#: давал НОЛЬ на главной, ноль в кабинете, ноль в распределении. Существующая
#: страница, которой для пользователя не существовало.
#: Условие показа — то же `prepod_id`, что у «Кабинета»: страница за входом
#: (`pokazat_istoriyu` не пускает гостя), и гостю пункт был бы дверью в отказ.
#:
#: 🔴 СЛОВО — «ЖУРНАЛ», И МЕСТО — САМОЕ ПОСЛЕДНЕЕ. Владелец 10.09 предложил слово
#: сам: «может, гораздо лучше так писать» — вместо «истории». Порядок пунктов он
#: назвал дословно: кабинет · листки · распределение · кондуит · журнал В САМОМ
#: КОНЦЕ; до этой правки журнал стоял ТРЕТЬИМ. Меняется ПОДПИСЬ и МЕСТО пункта;
#: адрес `/istoria` и имя модуля остаются прежними — их переименование задело бы
#: `veb/server.py` и каждую ссылку сайта, то есть чужую зону, и стоило бы ровно
#: ничего для читателя, который видит только эту подпись.
MENYU_PUNKT_ZHURNALA = '<a class="ssyl ssyl-ist" href="/istoria">Журнал</a>'


def menyu_ssylkami(tut: str = "") -> str:
    """Верхнее меню для страницы, которая НЕ собрана оболочкой.

    🔴 ПОЧЕМУ ЭТО ОТДЕЛЬНАЯ ФУНКЦИЯ, А НЕ КУСОК `obolochka()`. `/kabinet`,
    `/istoria` и `/raspredelenie` — самостоятельные документы: у них нет ни
    `Kontekst`, ни радиокнопок разделов, ни поиска, потому что нет разделов, между
    которыми переключаться. Меню при этом обязано стоять и на них — владелец 10.09
    про кабинет: *«из кабинета некуда уйти, это плохо»*. Одно место, где записаны
    названия и адреса пунктов, — здесь; `obolochka()` ниже собирает свою строку из
    тех же слов.

    `tut` — адрес текущей страницы (`/kabinet`), чтобы её пункт был отмечен тем же
    цветом, каким оболочка отмечает открытую вкладку.

    Пункты ведут на якоря разделов (`/#s-list`), и открывает их `VKLADKA_SKRIPT`,
    который для этого и научен переводить `#s-XXX` в отметку `p-XXX`.
    """
    def punkt(adres: str, imya: str) -> str:
        tut_klass = " ssyl-tut" if adres == tut else ""
        return f'<a class="ssyl{tut_klass}" href="{adres}">{imya}</a>'

    return ('<nav class="menu">\n'
            '  <span class="im">Ключики</span>\n  '
            # 🔴 «ЖУРНАЛ» СТОИТ ЗДЕСЬ ЖЕ, А НЕ ОТДЕЛЬНОЙ ПРАВКОЙ В `kabinet.py`
            # (H5.1). Эта функция — ОДНО место, где записаны названия и адреса
            # пунктов для страниц вне оболочки; добавить пункт в кабинете отдельно
            # значило бы завести второй список пунктов, который разойдётся с первым
            # на следующей же правке. Страница `/istoria` существовала и работала
            # (321 строка, 29 зелёных тестов, 200 и 81 238 байт), а входа на неё не
            # было НИ ОДНОГО: `grep -c 'href="/istoria'` давал ноль везде.
            #
            # 🔴 ПОРЯДОК — ТРЕБОВАНИЕ ВЛАДЕЛЬЦА 10.09, ДОСЛОВНО: кабинет · листки ·
            # распределение · кондуит · журнал В САМОМ КОНЦЕ. Журнал стоял третьим.
            # Тот же порядок повторён в `obolochka()` ниже — не потому, что список
            # записан дважды, а потому что это ДВА РЕНДЕРА одного списка: оболочка
            # рисует свои пункты метками радиокнопок, эта функция — ссылками, и
            # разойтись им нельзя.
            + "\n  ".join((punkt("/", "Класс"),
                           punkt("/kabinet", "Кабинет"),
                           punkt("/#s-list", "Листки"),
                           punkt("/raspredelenie", "Распределение"),
                           punkt("/#s-kond", "Кондуит"),
                           punkt("/istoria", "Журнал")))
            + '\n</nav>')


def obolochka(kt, *, glavnaya: str, listki: str, raspredelenie: str,
              poisk_skript: str, drakon_skript: str,
              tolko_raspredelenie: bool = False) -> str:
    """Assemble the whole page out of the sections already rendered for it.

    Everything constant lives here: the stylesheet, the radio inputs that drive
    every tab on the site, the top bar. Everything that varies by section arrives
    as a finished string. That is the shape of the cut in one sentence — this
    function does not know what a group tab contains, and a group tab does not
    know it is on a page.
    """
    verh = verh_prava(kt)
    hvost = skripty(kt, drakon_skript)
    # 🔴 THE SHELL IMPORTS A SECTION HERE — THE SECOND EXCEPTION IN THIS FILE, AND
    # IT IS FORCED BY THE ZONE, NOT CHOSEN. The rule at the top of this file is
    # that only the composition root knows both that a shell exists and that
    # sections exist; the composition root is `tools/sobrat_stranicu.sobrat_html`,
    # which lies OUTSIDE the zone of the заход that added the personal page, so it
    # could not be taught to pass this section in the way it passes the other four.
    # The import sits inside the function and inside the capability check, so it
    # runs only while a teacher is being served: the ring `karkas → lichnaya →
    # karkas` stays open exactly as it does for `shkolniki` in `sobrat_kontekst`,
    # and neither the guest build nor the organiser build ever touches it.
    # The правка that removes this exception is named in `## ВОПРОСЫ` of
    # `_studio/zhurnal/2026-09-06_pervyj-server/kod_lichnaya-stranica-prepodavatelya.md`.
    #
    # 🔴 `data-org` STANDS ON THE LABEL AND ON THE SECTION, AND MUST NOT STAND ON
    # THE RADIO INPUT. `_ubrat_elementy` in `tools/sobrat_stranicu.py` removes a
    # marked element by BALANCING its tags — it looks for `</input>`, which does
    # not exist in HTML, does not find it, and deletes the whole rest of the
    # document. The input is above the menu, i.e. outside the window the frame gate
    # compares (`id="s-rasp"` up to the first `\n<script>`), so it needs no mark;
    # the section IS inside that window and carries one.
    # 🔴 ВКЛАДКА «МОЁ» СНЯТА, И ЭТО ПЕРЕДЕЛКА ПО УСТРОЙСТВУ, А НЕ УБОРКА. Личное
    # жило в двух местах сразу: раздел `#s-lich` в оболочке и страница `/kabinet`,
    # рождённая на день позже и знающая про человека всё то же самое и больше.
    # Владелец 10.09 просил ОДНУ вкладку с одним именем — «Кабинет» — и она ведёт
    # на страницу, а не на раздел. Две двери в одно место это и есть та самая
    # вторая версия сайта, от которой мы избавляемся по всему проекту.
    # `veb/razdely/lichnaya.py` остаётся домом двух запросов (`kabinet_na_datu`,
    # `deti_na_datu`): их зовут и `/kabinet`, и карточка на заглавной.
    lichnaya = lich_vhod = lich_stili = ""
    start_vybran = " checked"
    # Пункт «Кабинет» — по `prepod_id`, разбор условия у `MENYU_PUNKT_KABINETA`.
    # 🔴 «ЖУРНАЛ» ОТЦЕПЛЁН ОТ «КАБИНЕТА» И УЕХАЛ В КОНЕЦ СТРОКИ. Оба появляются по
    # одному условию (`prepod_id`), но стоят в разных местах меню: владелец 10.09
    # назвал порядок дословно — кабинет · листки · распределение · кондуит ·
    # журнал В САМОМ КОНЦЕ. Пока они склеены в одну метку, журнал физически не
    # может оказаться последним, потому что «Кабинет» обязан быть вторым.
    kab_metka = ('\n  ' + MENYU_PUNKT_KABINETA) if kt.prepod_id is not None else ""
    zhurnal_metka = ('\n  ' + MENYU_PUNKT_ZHURNALA) if kt.prepod_id is not None else ""
    if tolko_raspredelenie:
        # Раздел на этой странице один; открывать нечего, кроме него.
        start_vybran, rasp_vybran = "", " checked"
    else:
        rasp_vybran = ""
    # 🔴 THE THIRD FORCED IMPORT, FOR THE THIRD TIME THE SAME REASON, AND IT IS
    # WORTH SAYING PLAINLY: the composition root `tools/sobrat_stranicu.sobrat_html`
    # is the only place that ought to know both that a shell exists and that
    # sections exist, and it lies OUTSIDE the zone of this заход, so it cannot be
    # taught to pass a sixth section in the way it passes the other four. The
    # import sits inside the function AND inside the capability check, so the ring
    # `karkas → konduit → karkas` stays open exactly as it does for `shkolniki` and
    # for `lichnaya`, and the guest build never touches it. The правка that removes
    # all three exceptions at once belongs to whoever owns `tools/`.
    #
    # 🔴 `data-org` СТОИТ НА МЕТКЕ И НА РАЗДЕЛЕ И НЕ ДОЛЖЕН СТОЯТЬ НА РАДИОКНОПКЕ —
    # то же правило и та же цена, что абзацем выше: `_ubrat_elementy` ищет
    # `</input>`, не находит и сносит остаток документа.
    # 🔴 НА СТРАНИЦЕ ЗАНЯТИЯ РАЗДЕЛОВ «КЛАСС» И «ЛИСТКИ» НЕТ, А ПУНКТЫ МЕНЮ ЕСТЬ —
    # ССЫЛКАМИ НА ГЛАВНУЮ. Причина не в экономии: контекст этой страницы собран на
    # ОДИН день, и расписание, нарисованное из него, показало бы вместо двух
    # занятий одно. Оглавление при этом обязано стоять на месте — владелец 07.09:
    # *«оглавление куда-то исчезло»*, и это было первое, что он заметил.
    if tolko_raspredelenie:
        punkty = ('<a class="ssyl" href="/">Класс</a>' + kab_metka + '\n'
                  '  <a class="ssyl" href="/#s-list">Листки</a>')
        rasp_adres, rasp_aktivna = "/raspredelenie", " ssyl-tut"
    else:
        punkty = ('<label for="p-start">Класс</label>' + kab_metka + '\n'
                  '  <label for="p-list">Листки</label>')
        rasp_adres, rasp_aktivna = "/raspredelenie", ""
    if kt.mozhno("videt-konduit"):
        from veb.razdely.konduit import razdel as konduit_razdel, stili as konduit_stili
        konduit = konduit_razdel(kt)
        kond_stili = konduit_stili(kt)
        kond_vhod = '\n<input class="rd" type="radio" name="str" id="p-kond">'
        kond_metka = '\n  <label for="p-kond" data-org="videt-konduit">Кондуит</label>'
    else:
        konduit = kond_vhod = kond_metka = kond_stili = ""
    return f"""<!doctype html>
<html lang="ru">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Спецмат · 9 класс</title>
<style>
:root{{--bg:#fbfaf6;--panel:#fffdf8;--text:#211f1b;--muted:#726c60;--rule:#e7e2d6;
  --accent:#2f6e8e;--accent-soft:#e8f0f4;--warm:#c9743a;--faint:#b7ae9c;--chip:#e7e0d2;
  --krasn:#b3402a;--krasn-fon:rgba(179,64,42,.08);
  /* 🔴 ЗЕЛЁНЫЙ ЗАВЕДЁН ЗДЕСЬ, РЯДОМ С КРАСНЫМ, И БОЛЬШЕ НИГДЕ. Полоса занятий в
     кабинете красит «был» и «не был», и второго цвета для «был» в палитре не
     было вовсе. `doc/DIZAJN-ZAKREPLENO.md` §2 запрещает не новый цвет, а ВТОРОЕ
     МЕСТО, где он записан: страница `/kabinet` берёт таблицу стилей отсюда
     целиком (`list_odin._obshchij_stil`), так что запись остаётся одна. Пара
     построена по образцу красной: тон и та же полупрозрачная подложка. */
  --zel:#3d7a4e;--zel-fon:rgba(61,122,78,.10);
  --sans:"Source Sans 3",system-ui,-apple-system,"Helvetica Neue",Arial,sans-serif;
  --serif:"Source Serif 4",Georgia,"Times New Roman",serif}}
@media(prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#1b1e22;--panel:#23272c;
  --text:#dcd8d0;--muted:#9a948a;--rule:#343a41;--accent:#7fb6d2;--accent-soft:#22333d;
  --warm:#e0946a;--faint:#6b6f75;--chip:#333a41;
  --krasn:#e8836a;--krasn-fon:rgba(232,131,106,.12);
  --zel:#7cc08e;--zel-fon:rgba(124,192,142,.14)}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--text);font-family:var(--serif);font-size:20px}}
/* Меню — строка сверху: три пункта помещаются, ничего выезжать не должно (§1). */
.menu{{position:sticky;top:0;z-index:40;display:flex;gap:.3rem;align-items:baseline;
  padding:.9rem 3rem;background:var(--panel);border-bottom:1px solid var(--rule);
  font-family:var(--sans);flex-wrap:wrap}}
.menu .im{{font-weight:600;font-size:1.05rem;margin-right:1.6rem;white-space:nowrap}}
.menu label,.menu a.ssyl{{cursor:pointer;font-weight:600;font-size:1.05rem;color:var(--muted);
  padding:.35em 1rem;border-radius:8px;text-decoration:none}}
.menu label:hover,.menu a.ssyl:hover{{color:var(--text);background:var(--accent-soft)}}
.holst{{padding:1.3rem 3rem 2rem;max-width:none}}
h1{{font-family:var(--sans);font-size:2.1rem;font-weight:600;letter-spacing:-.02em;margin:0}}
.data{{color:var(--muted);font-family:var(--sans);font-size:1rem;margin:0 0 1.6rem}}
.oblozhka p{{font-size:1.3rem;line-height:1.5;max-width:52em;margin:0 0 .8em}}
.rasp-str{{font-size:1.15rem;padding:.15em 0}}
.raspisanie{{border:1px solid var(--rule);border-radius:10px;padding:1.1rem 1.4rem;
  margin:1.6rem 0 0;background:var(--panel);max-width:52em}}
.zag2{{font-family:var(--sans);font-size:.82rem;font-weight:700;letter-spacing:.1em;
  text-transform:uppercase;color:var(--faint);margin:0 0 .5em}}
/* 🔴 ЗАГОЛОВОК ЛИСТКА НЕ ПОДНИМАЕТСЯ В ВЕРХНИЙ РЕГИСТР, И ЭТО НЕ ВКУС.
   Владелец 10.09: вкладка называется «16α», а заголовок под ней печатал
   «16А. ДЕРЕВЬЯ» — и он читал это как расхождение в данных. Данные ЦЕЛЫ:
   сверка на боевой базе дала НОЛЬ листков, где `title` не начинается с `number`.
   Врало отображение: `text-transform:uppercase` переводит «α» (U+03B1) в «Α»
   (U+0391) — ЗАГЛАВНУЮ ГРЕЧЕСКУЮ АЛЬФУ, которая на экране неотличима от русской
   «А» (U+0410). Три листка одной темы называются 16A, 16α и 16ℵ, и различить их
   можно ТОЛЬКО по этому знаку — то есть регистр стирал единственное различие.
   Проверяется командой: python3 -c "print('16α'.upper())" → 16Α. */
.zag-listok{{text-transform:none;letter-spacing:.02em}}
.str,.vid{{display:none}}
#p-start:checked~#s-start,#p-list:checked~#s-list,#p-rasp:checked~#s-rasp{{display:block}}
#p-start:checked~.menu label[for=p-start],#p-list:checked~.menu label[for=p-list],
#p-rasp:checked~.menu .ssyl-rasp{{color:var(--accent);background:var(--accent-soft)}}
input.rd{{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none}}
.tabbar{{display:flex;gap:.25rem;border-bottom:2px solid var(--rule);margin:0 0 1rem;flex-wrap:wrap}}
.tabbar label{{cursor:pointer;font-family:var(--sans);font-weight:600;font-size:1.1rem;
  color:var(--muted);padding:.5rem 1.2rem;border:2px solid transparent;border-bottom:none;
  border-radius:10px 10px 0 0;margin-bottom:-2px}}
.tabbar label:hover{{color:var(--text)}}
{"".join(f"#t-{k}:checked~#v-{k}{{display:block}}#t-{k}:checked~.tabbar label[for=t-{k}]"
         "{color:var(--accent);background:var(--panel);border-color:var(--rule) var(--rule) var(--panel)}"
         for k in ("shk","prep","В","Д","Н"))}
{"".join(f"#l-{k}:checked~#w-{k}{{display:block}}#l-{k}:checked~.tabbar label[for=l-{k}]"
         "{color:var(--accent);background:var(--panel);border-color:var(--rule) var(--rule) var(--panel)}"
         for k in ("9","8"))}
table{{border-collapse:collapse;width:100%;font-size:1.05rem}}
th{{font-family:var(--sans);font-size:.8rem;font-weight:600;letter-spacing:.09em;
  text-transform:uppercase;color:var(--faint);text-align:left;padding:0 1.1rem .55rem 0;
  border-bottom:1px solid var(--rule)}}
td{{padding:.5rem 1.1rem .5rem 0;border-bottom:1px solid var(--rule);vertical-align:baseline}}
tr:hover td{{background:var(--accent-soft)}}
.kl{{color:var(--muted);font-family:var(--sans);font-size:.9rem}}
.kab.staryj{{background:none;border:1px dashed var(--rule);color:var(--muted)}}
.kab{{font-family:var(--sans);font-weight:600;background:var(--chip);border-radius:7px;
  padding:.1em .55em;white-space:nowrap}}
.gr{{font-family:var(--sans);font-weight:600;color:var(--accent)}}
.pr{{white-space:nowrap}}
.deti{{font-size:.95rem;color:var(--muted);line-height:1.45}}
.ch{{font-family:var(--sans);color:var(--muted);text-align:right;white-space:nowrap}}
.net{{color:var(--warm);font-family:var(--sans);font-size:.95rem}}
.redko{{font-family:var(--sans);font-size:.85rem;color:var(--warm)}}
.shapka{{font-family:var(--sans);font-size:1.15rem;color:var(--muted);margin:0 0 .8rem}}
.zhdut{{border:1px solid var(--warm);border-radius:10px;padding:1rem 1.3rem;margin:0 0 1.8rem}}
.zhdut .zag2{{color:var(--warm)}}
.poisk{{width:100%;max-width:640px;padding:.65em .9em;font:inherit;font-size:1.1rem;
  border:1px solid var(--rule);border-radius:9px;background:var(--panel);color:var(--text);margin:0 0 1.5rem}}
.poisk:focus{{outline:none;border-color:var(--accent)}}
.podskazki{{position:relative;max-width:640px}}
.podskazki.bolshoj{{max-width:none;margin-top:2.2rem}}
.poisk-big{{max-width:none;width:100%;font-size:1.6rem;padding:.85em 1.1em;border-radius:14px}}
.podskazki.bolshoj .spisok{{top:5.2rem;font-size:1.3rem}}
.podskazki.bolshoj .spisok div{{padding:.6em 1.1em}}
#nashli{{max-width:none;font-size:1.5rem;line-height:1.45;margin-top:1.6rem}}
.otvet{{width:100%;padding:1rem 1.2rem;border:1px solid var(--rule);border-radius:12px;
  background:var(--panel);color:var(--text)}}
.spisok{{position:absolute;left:0;right:0;top:3.1rem;z-index:20;background:var(--panel);
  border:1px solid var(--rule);border-radius:0 0 9px 9px;max-height:18rem;overflow:auto}}
.spisok div{{padding:.5em .9em;cursor:pointer}}
.spisok div:hover{{background:var(--accent-soft);color:var(--accent)}}
/* Строка школьника, на которую привёл поиск (`?sid=` — `glavnaya.poisk_skript`). */
.podsvechen{{outline:2px solid var(--accent);border-radius:6px;background:var(--accent-soft)}}
/* ТРИ КОЛОНКИ ВО ВЕСЬ ЭКРАН. Слева и посередине — школьник и его преподаватель,
   справа — преподаватель и его школьники. Разделены вертикальной линией.
   Списками, а не квадратиками: человек ищет свою фамилию по алфавиту. */
.dva{{display:grid;grid-template-columns:1fr 1fr;gap:0 2.5rem;align-items:start}}
.odin{{max-width:none}}
.kol{{padding-right:2rem;border-right:1px solid var(--rule);min-width:0}}
.kol:last-child{{border-right:none;padding-right:0}}
/* Крупнее и плотнее: пустой половины экрана быть не должно. */
.para{{display:flex;gap:.8rem;align-items:baseline;padding:.34rem 0;flex-wrap:wrap;
  border-bottom:1px solid var(--rule);font-size:1.15rem}}
/* На вкладках групп места больше — там строки крупнее. */
#v-В .para,#v-Д .para,#v-Н .para{{font-size:1.6rem;padding:.48rem 0}}
#v-В .komu,#v-Д .komu,#v-Н .komu{{font-size:1.5rem}}
/* На общей вкладке школьников, наоборот, чуть плотнее — там 54 строки. */
#v-shk .para{{font-size:1.08rem;padding:.26rem 0}}
#v-shk .komu{{font-size:1rem}}
/* 🔴 СЖИМАЕТСЯ ИМЯ, А НЕ СТОЛБЕЦ. Раньше `.kto` не сжимался вовсе, и самая
   длинная фамилия выталкивала поля за правый край колонки — страница получала
   горизонтальную прокрутку (замер верификатора: `scrollWidth` 1444 при окне
   1440, три строки за границей). Столбцы дней обязаны стоять ровно; имя,
   которое не влезло, честнее обрезать многоточием — оно целиком есть в
   подсказке поиска и в самой строке при наведении. */
.para .kto{{flex:0 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;
  white-space:nowrap}}
.para .komu{{margin-left:auto;text-align:right;color:var(--muted);font-family:var(--sans);
  font-size:1.05rem}}
.para .komu.deti{{white-space:normal;text-align:right}}
.para .komu.deti span{{display:inline-block;margin-left:.55rem}}
/* 🔴 ИМЯ — СТРОКОЙ, ДЕТИ — РЯДОМ ПОД НИМ, ВО ВСЮ ШИРИНУ. Владелец 07.09:
   «сбоку в углу школьники — они должны быть спокойно расположены в ряд на всю
   ширину, а не сжаты к правой стороне… почему-то обрезалась Наталья Стрелкова,
   хотя там куча места». Прижатые вправо, они делили строку с именем и толкали
   его в многоточие; в столбик под именем места хватает обоим.
   Имя здесь НЕ обрезается вовсе: строка отдана ему целиком. */
/* 🔴 КАРТОЧКЕ ВЕРНУЛИ ВЫСОТУ. Владелец 07.09: «ты стал гораздо больше места
   уделять на каждого преподавателя… сейчас ты её обратно случайно сжал. Сделай
   обратно её широкой». Имя крупное, дни под ним, между строками воздух: этот
   столбец читают издалека, стоя, посреди занятия. */
.kol-pr .para{{flex-direction:column;align-items:stretch;gap:.35rem;
  padding:.85rem 0;font-size:1.5rem}}
.kol-pr .komu.deti{{font-size:1.05rem}}
.kol-pr .para .kto{{overflow:visible;text-overflow:clip;white-space:normal;
  flex:0 0 auto}}
/* Дети идут СЛЕВА НАПРАВО во всю ширину карточки: `margin-left:auto` из общего
   правила `.para .komu` прижимал их к правому краю, и последние фамилии уезжали
   за границу колонки — ровно то, что владелец увидел как «сжаты к правой
   стороне» и «обрезалась Наталья Стрелкова, хотя там куча места». */
#s-rasp .kol-pr .komu.deti,.kol-pr .komu.deti{{margin-left:0;margin-right:auto;
  text-align:left;font-size:1rem;white-space:normal;display:flex;flex-wrap:wrap;
  align-items:baseline;gap:.15rem .35rem;flex:1 1 100%;min-width:0}}
.kol-pr .komu.deti span{{display:inline-flex;margin-left:0}}
#s-rasp .kol-pr .para{{flex-wrap:wrap;flex-direction:column}}
#s-rasp .kol-pr .para .kto{{white-space:normal;overflow:visible;
  text-overflow:clip;flex:0 0 auto}}
/* Счётчик в карточке — в конце ряда детей, а не за краем. */
.kol-pr .komu.deti .sch{{margin-left:.3rem}}
/* День в карточке принимающего — своей строкой: подпись слева, дети за ней.
   Так видно, что списков ДВА и они разные, — а слитый ряд читался как один. */
.den-ryad{{display:flex;align-items:baseline;gap:.5rem;flex:1 1 100%;min-width:0}}
.den-podpis{{flex:0 0 1.7rem;color:var(--faint);font-family:var(--sans);
  font-size:.7rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase}}
.deti-ryad{{display:flex;flex-wrap:wrap;align-items:baseline;gap:.2rem .35rem;
  flex:1 1 auto;min-width:0}}
/* 🔴 ЧИСЛО СТОИТ СВОЕЙ КОЛОНКОЙ, А НЕ ТАМ, ГДЕ КОНЧИЛИСЬ ФАМИЛИИ. Владелец 07.09:
   «почему съехали цифры? Почему цифры ни на одном уровне? Должно быть на одном
   уровне, должна быть колонка, в которой цифры». Число, стоящее вплотную к
   последней фамилии, каждую строку начинается в новом месте, и глазу приходится
   искать его заново — а читают этот столбец сверху вниз, одним движением. */
.den-ryad .sch{{flex:0 0 2.2rem;margin-left:auto;text-align:right}}
/* Запятая между фамилиями рисуется CSS: у гостя и у организатора один и тот же
   элемент `.det`, и разметка обоих режимов отличается ровно кнопкой-органом. */
.zpt:not(:last-child)::after{{content:", "}}
.tabl .zpt:not(:last-child)::after{{content:none}}
/* Кнопка входа — справа в том же меню, тем же шрифтом, что и его пункты. */
.vhod{{margin-left:auto;font-family:var(--sans);font-weight:600;font-size:1.05rem;
  color:var(--accent);text-decoration:none;padding:.35em 1rem;border:1px solid var(--accent);
  border-radius:8px;white-space:nowrap}}
.vhod:hover{{background:var(--accent);color:var(--panel)}}
.rezhim{{font-family:var(--sans);font-weight:600;font-size:.95rem;color:var(--warm);
  margin-left:auto;margin-right:.8rem;white-space:nowrap}}
.rezhim+.vhod{{margin-left:0}}
/* ── ОРГАНЫ ПРАВКИ. Стоят там же, где у гостя текст, и больше нигде. ── */
.org{{font:inherit;font-family:var(--sans);font-size:.95rem;color:var(--text);
  background:var(--panel);border:1px solid var(--rule);border-radius:7px;
  padding:.12em .3em;margin-left:.4rem;max-width:11rem}}
.org:hover,.org:focus{{border-color:var(--accent);outline:none}}
/* Столбец с числом: узкий, по правому краю, одинаковый во всех строках — по нему
   читают нагрузку сверху вниз, а не ищут число в конце каждого списка. */
.prep-tab td.tsch{{font-family:var(--sans);font-weight:600;text-align:right;
  width:2.4rem;padding-right:.9rem;white-space:nowrap;color:var(--accent)}}
/* Строки таблицы принимающих — просторнее: их читают издалека, стоя. */
.prep-tab td{{padding-top:.5rem;padding-bottom:.5rem}}
/* 🔴 ЧИСЛО НЕ КРАСНЕЕТ — КРАСНЕЕТ МЕСТО. Владелец 07.09: «цифра 5 плохо
   выглядит. Лучше писать 5 синим, а красным подчёркивать, выделять поле — не
   обязательно красным, каким-то менее ярким, красноватым». Красная цифра среди
   серых читается как ошибка ЧИСЛА; подсвеченное поле читается как «здесь
   перебор», а это и есть смысл. */
/* 🔴 ПОДСВЕЧИВАЕТСЯ СТРОКА, А НЕ ЧИСЛО. Владелец 07.09: «я предлагал выделять не
   цифру 5 красноватым цветом, а всю строчку… точно так же, если у школьника не
   назначены преподаватели, это тоже должно подчёркиваться». Подсвеченное число —
   это «неверное число»; подсвеченная строка — «здесь разберись», и разбираются
   именно со строкой. */
.tsch.ploho,.sch.ploho{{color:var(--accent)}}
tr:has(.tsch.ploho),.para:has(.sch.ploho),.den-ryad:has(.sch.ploho){{
  background:var(--krasn-fon)}}
#s-rasp .para.krasn{{background:var(--krasn-fon)}}
#s-rasp .para.krasn .kto b{{color:var(--text)}}
/* Подсветка не должна обрывать строку по краям колонки: она идёт от края до края. */
tr:has(.tsch.ploho) td:first-child,.para:has(.sch.ploho),#s-rasp .para.krasn{{
  border-radius:8px}}
.den-ryad:has(.sch.ploho){{border-radius:8px;padding:.1rem .35rem;margin:0 -.35rem}}
.sch{{font-family:var(--sans);font-weight:600;font-size:.8em;color:var(--accent)}}

/* Крестик = открепить. Появляется по клику на фамилии преподавателя, не раньше:
   восемнадцать всегда видимых крестиков — это приглашение промахнуться. */
/* ── ТАБЛЕТКА ФАМИЛИИ. Приём взят из рабочего файла распределения владельца:
   мелкий шрифт и скруглённая пилюля, чтобы пять школьников влезали в строку
   преподавателя и не переносились, оставляя дыру. Крестик занимает НОЛЬ ширины,
   пока на таблетку не навели мышь, — поэтому у гостя и у организатора список
   ровно одинаковой ширины. Элемент один и тот же; правку добавляет data-org. */
/* ── БЛИЖАЙШЕЕ ЗАНЯТИЕ И КАБИНЕТ — В СТРОКЕ ВКЛАДОК, а не отдельной полосой. ── */
.tabbar-rasp .zanyatie{{margin-left:auto;align-self:center;display:flex;align-items:center;gap:.3rem}}
.skoro{{font-family:var(--sans);font-size:1rem;color:var(--muted);white-space:nowrap}}
.kab-verh{{display:none;align-self:center;margin-left:.9rem}}
#t-В:checked~.tabbar .kab-verh-В,#t-Д:checked~.tabbar .kab-verh-Д,
#t-Н:checked~.tabbar .kab-verh-Н{{display:inline-block}}
/* ── ГРУППА: преподаватели в рамке, служебное — под ними. ── */
.prep-ramka{{border-top:1px solid var(--rule);border-bottom:1px solid var(--rule);
  padding:.5rem 0}}
.gruppa-niz{{margin-top:1rem;border:1px solid var(--rule);border-radius:11px;
  padding:.7rem 1.1rem;background:var(--panel);display:flex;align-items:center;
  gap:1.2rem;flex-wrap:wrap;font-family:var(--sans);font-size:.98rem;color:var(--muted)}}
.gruppa-niz b{{color:var(--text)}}
.gruppa-cifry{{white-space:nowrap}}
/* Строки списков подсвечиваются под мышкой — видно, на чём стоишь. */
#s-rasp .para:hover{{background:var(--accent-soft);border-radius:6px}}
.prep-tab tr:hover td{{background:var(--accent-soft)}}
/* ── СТРАНИЦА КЛАССА. Ни одного повтора имени сайта: оно стоит наверху. ── */
.klass{{display:grid;grid-template-columns:minmax(0,1fr) 17rem;gap:0 3rem;align-items:start}}
@media(max-width:900px){{.klass{{grid-template-columns:1fr}}}}
/* ── ЗАГЛАВНАЯ. Кривая — подложка во весь экран с выходом за края;
   содержание лежит НА ней двумя потоками. Не колонка текста и колонка картинки:
   так картинка не взаимодействует с текстом, а просто стоит рядом. ── */
/* 🔴 ЗАГЛАВНАЯ РОВНО В ЭКРАН, БЕЗ ПРОКРУТКИ. Кривая выходит за края, и без
   обрезки на самой секции это давало полосы прокрутки вбок и вниз: страница
   становилась больше окна. Обрезаем по секции — она во всю ширину окна, поэтому
   видимого шва не появляется, а прокрутка исчезает. */
#s-start{{overflow:hidden;padding-bottom:1rem}}
/* 🔴 НА ЗАГЛАВНОЙ СТРОКИ НЕ ПОДСВЕЧИВАЮТСЯ. Общая подсветка `tr:hover` создана
   для таблиц, по строкам которых нажимают. На заглавной нажимать не по чему, и
   бирюзовая полоса под мышкой обещает действие, которого нет. Владелец дважды:
   «когда я навожу на понедельник… выделяется бирюзовая подсветка. Очень
   странно». Гасим по всей секции, а не по одной таблице. */
#s-start tr:hover td,#s-start tr:hover th{{background:none}}
.glav{{position:relative;min-height:calc(100vh - 9.5rem);display:flex;
  flex-direction:column}}
/* 🔴 ЗАГЛАВНАЯ ДОХОДИТ РОВНО ДО НИЖНЕГО КРАЯ ОКНА. Секция обрезает холст по
   себе (`overflow:hidden`), и пока она кончалась выше окна, кривая обрывалась
   ровной горизонталью, а под ней лежала пустая полоса. Владелец: «у тебя опять
   обрезалась картинка — нижней части нет, нет кривого дракона».
   6.3rem = высота меню (4rem) + отступы секции сверху и снизу. Правило
   включено только там, где меню стоит одной строкой: если оно переносится,
   точная высота перестаёт сходиться и появилась бы полоса прокрутки. */
@media(min-width:1100px){{.glav{{min-height:calc(100vh - 6.3rem)}}
  #s-start{{margin-bottom:-2rem}}}}
/* 🔴 ХОЛСТ ВЫХОДИТ ЗА КРАЯ ЭКРАНА, А НЕ ОБРЫВАЕТСЯ ВНУТРИ НЕГО. Раньше он был
   меньше страницы, и кривая кончалась ровной вертикалью посреди экрана — прямая
   линия там, где у фрактала её быть не может, и глаз цепляется именно за неё.
   Владелец: «кривая обрезана… её нельзя так делать, надо её до конца пустить».
   Отступы в vw/vh и отрицательные — чтобы холст перекрывал поля `.holst` и
   уходил за границу окна со всех сторон. */
/* Верхний край уходит ПОД панель меню — она непрозрачна и кривую скрывает.
   Иначе под панелью оставалась ровная горизонталь: у фрактала прямых границ
   не бывает, и глаз цепляется именно за неё. */
.glav-risunok{{position:absolute;left:-6vw;right:-6vw;top:-18vh;bottom:-10vh;
  z-index:0;pointer-events:none;overflow:hidden}}
/* Тише, чем хочется: кривая обязана попадаться на глаза и не мешать читать.
   Владелец: «должна быть незаметной, не сильно выбивать содержание». */
#drakon{{width:100%;height:100%;opacity:.20}}
@media(prefers-color-scheme:dark){{:root:not([data-theme=light]) #drakon{{opacity:.24}}}}
.glav-shapka,.glav-setka{{position:relative;z-index:1}}
/* 🔴 ГАЛО ВОКРУГ ТЕКСТА, А НЕ ПОДЛОЖКА ПОД НИМ. Кривая набрана тем же
   акцентным цветом, что и часть надписей, и на её плотных участках текст читался
   «белым по белому». Плашка под текстом убила бы весь смысл фона; свечение
   цветом фона отодвигает кривую ровно на толщину буквы и не рисует ни одной
   лишней границы. Приём взят из скилла cinematic-longread — там же он назван
   halo и применён по той же причине. */
.glav-tekst,.glav-sboku{{text-shadow:0 0 10px var(--bg),0 0 22px var(--bg),
  0 0 3px var(--bg)}}
/* Имена принимающих — основным цветом, а не приглушённым: на фоне кривой
   приглушённый сливался с ней. */
.prep-spisok{{color:var(--text)}}
.rasp .den-vremya{{color:var(--text)}}
.glav-imya{{font-size:clamp(2.6rem,6.2vw,5.6rem);font-weight:600;letter-spacing:-.03em;
  line-height:1.02;margin:1.2rem 0 0}}
.glav-pod{{font-family:var(--sans);font-size:clamp(1.05rem,1.8vw,1.4rem);
  color:var(--muted);margin:.5rem 0 0}}
/* 🔴 ЛИСТОК ПОДНЯТ В ПУСТОТУ, А НЕ ПРИЖАТ К НИЗУ. Раньше вся сетка уезжала
   вниз `margin-top:auto`, и над ней зияла треть экрана. Теперь колонка занимает
   всю высоту и распределяет содержание по ней: листок сразу под заголовком,
   «кто ведёт» — у нижнего края. Владелец: «вынести Деревья вверх на пустое
   место и постараться заполнить большую часть пространства». */
.glav-setka{{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(0,1fr);
  gap:2.5rem 4rem;margin-top:2.5vh;padding:0;align-items:stretch;flex:1 1 auto}}
.glav-glavnoe{{display:flex;flex-direction:column;justify-content:space-between;
  gap:2rem;padding-bottom:.5rem}}
/* Карточка опускается отступом сверху в самом правиле `.blok-listok` ниже —
   отдельным правилом здесь его гасило `margin:0` оттуда же: при равной силе
   побеждает то, что стоит в файле ниже. */
@media(max-width:940px){{.glav-setka{{grid-template-columns:1fr;align-items:start}}}}
/* Главное — листок. Он и набран крупнее всего, что рядом. */
/* ── 🔒 КАРТОЧКА БЛИЖАЙШЕГО ЛИСТКА — ЗАКРЕПЛЁННАЯ СХЕМА. НЕ УСЛОЖНЯТЬ.
   Схему стережёт `proverit_shemu()`: страница не соберётся, если её нарушить.

   ОДНА гарнитура, ОДИН кегль, ОДНА насыщенность, ОДИН цвет на всё содержание.
   Серым набрана только подпись сверху — тем же служебным стилем, что и
   подписи соседних блоков.

   Так вышло не с первого раза. Сначала на карточке стояли две гарнитуры,
   четыре кегля, четыре цвета и три плашки с фоном; владелец сосчитал:
   «на одной карточке 10 разных визуальных элементов». Потом осталось
   четыре цвета и смесь жирного с нежирным — и это оказалось той же ошибкой
   помельче: «серый, желтовато-серый, белый и голубой… здесь должно быть
   максимум два цвета. Либо всё жирное, либо всё нежирное. Нельзя смешивать
   жирное и нежирное в одном месте — так не работает».

   Отсюда три запрета, которые и проверяются на сборке:
   ЗАПРЕЩЕНО жирное начертание внутри карточки;
   ЗАПРЕЩЁН акцентный цвет — в том числе на ссылках версий;
   ЗАПРЕЩЕНЫ приглушённые и служебные цвета в строках карточки. */
/* `margin-top` опускает ОДНУ карточку: колонка разложена `space-between`, и
   «кто ведёт» остаётся приколоченным к нижнему краю. Владелец: «сам блок
   опустить вниз, не меняя ничего другого». */
/* 🔴 ПРАВКА ВЛАДЕЛЬЦА 07.09, вторая: в карточке важно ОДНО СЛОВО, всё
   остальное — служебное. Дата, время, уровни и кабинеты уходят на один общий
   мелкий кегль, а название листка остаётся крупным. Блок сжимается по ширине
   САМОЙ ШИРОКОЙ своей строки (`width:max-content`) — тем самым «прямоугольник
   повторяет строчку с названием» и перестаёт вылезать за колонку. */
.blok-listok{{margin:4.5rem 0 0;width:max-content;max-width:min(34rem,100%);
  font-family:var(--sans);font-size:clamp(1.02rem,1.15vw,1.24rem);
  line-height:1.3;font-weight:400}}
.blok-listok p{{margin:.15rem 0 0;color:var(--text);font-weight:400}}
.listok-kogda{{margin-top:.4rem}}
/* Версии — ссылки того же цвета и веса, что и текст вокруг. Голубой на них
   был четвёртым цветом на карточке из четырёх строк; подчёркивание под мышкой
   показывает, что по ним нажимают, и не вводит ни одного нового цвета. */
/* 🔴 ПРАВКА ВЛАДЕЛЬЦА 07.09: в карточке доминирует НАЗВАНИЕ листка.
   Различает только КЕГЛЬ: вес и цвет на карточке по-прежнему одни на всё
   содержание, и замок схемы это подтверждает. Номер не выброшен — он ушёл
   на второй план, потому что по нему всё ещё узнают листок в разговоре. */
.listok-tema{{font-size:2.55em;line-height:1.12;cursor:pointer}}
.listok-tema:hover{{text-decoration:underline}}
.listok-nom{{font-size:1em;margin-right:.4em;cursor:pointer;
  vertical-align:.9em;opacity:.75}}
.listok-nom:hover{{text-decoration:underline}}
/* 🔴 Преподаватель видит В КАРТОЧКЕ свой ОДИН кабинет и своих школьников,
   а общая строка трёх кабинетов у него прячется. Прячется именно CSS-ом, а не
   отсутствием в разметке: обе строки обязаны стоять в HTML, иначе побайтовая
   сверка каркаса гостя с админом и с преподавателем разойдётся (разбор — в
   `veb/razdely/glavnaya.py`, рядом с `moyo_html`). */
.blok-listok:has(.listok-moyo) .listok-obshchij{{display:none}}
.listok-moyo{{white-space:normal;line-height:1.35}}
.listok-stroka{{margin-top:.35rem !important;margin-bottom:.15rem !important;
  white-space:nowrap}}
.listok-ver{{font-size:1em}}
.blok-listok .zag2{{margin-bottom:.1rem}}
.listok-ver{{margin-left:.3rem;white-space:nowrap}}
.listok-ver a{{color:inherit;text-decoration:none;padding:0 .28rem;
  font-weight:inherit}}
.listok-ver a:hover{{text-decoration:underline}}
.blok-listok .net{{color:inherit}}
.vedut{{border-collapse:collapse;font-size:clamp(1.6rem,2.5vw,2.5rem)}}
.vedut td{{border:none;padding:.5rem 0;vertical-align:baseline}}
.vedut .predmet{{color:var(--muted);padding-right:2.6rem;white-space:nowrap;
  font-family:var(--sans);font-size:clamp(1.2rem,1.45vw,1.65rem)}}
.imya-celikom{{white-space:nowrap}}
/* Боковое — поверх кривой, мельче, с воздухом между блоками. */
.glav-sboku{{display:flex;flex-direction:column;gap:2.4rem;justify-content:flex-end}}
.sboku-blok{{}}
/* Боковая колонка набрана крупно нарочно: мелким она занимала нижнюю треть,
   а верх оставался пустым. Владелец: «увеличить шрифт… за счёт этого меньше
   будет пустого места». */
.rasp{{border-collapse:collapse;font-size:clamp(1.4rem,1.9vw,2.2rem)}}
.rasp td{{border:none;padding:.45rem 0;vertical-align:baseline}}
.rasp .den-imya{{font-weight:600;padding-right:2rem}}
.rasp .den-vremya{{white-space:nowrap;color:var(--muted);font-family:var(--sans)}}
.prep-spisok{{list-style:none;margin:.6rem 0 0;padding:0;
  font-size:clamp(1.3rem,1.7vw,2rem);columns:2;column-gap:2.2rem}}
.prep-spisok li{{padding:.28rem 0;break-inside:avoid}}
.prep-spisok.ranshe{{columns:2;color:var(--muted);font-size:clamp(1.1rem,1.35vw,1.55rem)}}
.ranshe-zag{{margin-top:1.4rem}}
.zag2{{font-size:clamp(.82rem,.95vw,1rem)}}
.klass-sboku{{border-left:1px solid var(--rule);padding-left:2rem}}
@media(max-width:900px){{.klass-sboku{{border-left:none;padding-left:0;margin-top:1.5rem}}}}
.ranshe-zag{{margin-top:1.4rem}}
/* ── ЛИСТКИ: восьмой класс двумя столбцами, чтобы не тянуться одной колонкой. ── */
.dva-listka{{display:grid;grid-template-columns:1fr 1fr;gap:0 3rem;align-items:start}}
@media(max-width:900px){{.dva-listka{{grid-template-columns:1fr}}}}
/* Переключатель дня стоит в той же строке, что и вкладки, а не отдельной полосой. */
/* ── СТРОКА НЕ ПЕРЕНОСИТСЯ. Перенос был не косметикой, а поломкой: список
   переставал читаться колонкой, и на месте переноса зияла дыра. Причина —
   раздутые выпадающие списки, съедавшие место у фамилии. Лечится тем же, чем
   в рабочем файле распределения: фамилии отдаётся всё оставшееся место, а поля
   получают фиксированную ширину и не растягиваются. */
#s-rasp .para{{flex-wrap:nowrap}}
#s-rasp .para .kto{{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
#s-rasp .para .komu{{flex:0 0 auto;white-space:nowrap}}
#s-rasp .para .komu.deti{{flex:1 1 auto;white-space:normal}}
.org.pr-sel{{max-width:12.5rem;flex:0 0 auto}}
/* 🔴 НА ВКЛАДКАХ ГРУПП КОЛОНКА ВДВОЕ УЖЕ: там рядом стоит список принимающих.
   Поля здесь компактнее ровно настолько, чтобы фамилия школьника помещалась
   целиком — она в этой таблице главное, а имя преподавателя и так повторено
   справа, в его карточке. */
#v-В .org.pr-sel,#v-Д .org.pr-sel,#v-Н .org.pr-sel{{max-width:12.5rem}}
#s-rasp #v-В .kol .para .komu .dv-pn:has(.org.pr-sel),#s-rasp #v-Д .kol .para .komu .dv-pn:has(.org.pr-sel),#s-rasp #v-Н .kol .para .komu .dv-pn:has(.org.pr-sel),#s-rasp #v-В .kol .para .komu .dv-cht:has(.org.pr-sel),#s-rasp #v-Д .kol .para .komu .dv-cht:has(.org.pr-sel),#s-rasp #v-Н .kol .para .komu .dv-cht:has(.org.pr-sel),#s-rasp #v-В .kol .org.pr-sel,#s-rasp #v-Д .kol .org.pr-sel,#s-rasp #v-Н .kol .org.pr-sel{{flex:0 0 12.5rem;max-width:12.5rem}}
#v-В .org.gr-sel,#v-Д .org.gr-sel,#v-Н .org.gr-sel{{width:3.2rem;flex:0 0 3.2rem}}
#v-В .otsut,#v-Д .otsut,#v-Н .otsut{{font-size:.76rem;padding:.12em .45em}}
/* 🔴 ИМЯ ПЕРЕНОСИТСЯ, А НЕ ОБРЕЗАЕТСЯ. Владелец 07.09: «посмотри, как обрезалась
   вёрстка текста — это просто жесть. Слева в куче мест имена обрезались, хотя
   место есть». На вкладках групп колонка вдвое уже (рядом стоит список
   принимающих), и самая длинная фамилия в неё не влезает никогда — сколько ни
   ужимай поля. Многоточие прячет то, ради чего в таблицу и смотрят; перенос
   стоит одной лишней строки и не прячет ничего. */
#v-В .kol .para,#v-Д .kol .para,#v-Н .kol .para{{flex-wrap:wrap}}
#v-В .kol .kto,#v-Д .kol .kto,#v-Н .kol .kto{{white-space:normal;overflow:visible;
  text-overflow:clip;flex:1 1 9rem}}
#v-В .kol .komu,#v-Д .kol .komu,#v-Н .kol .komu{{flex:0 0 auto}}
/* 🔴 ШИРИНА ФИКСИРОВАНА, А НЕ ОГРАНИЧЕНА СВЕРХУ. При `max-width` поле группы
   мерилось по своему тексту — «нигде» шире, чем «В», — и на эту разницу ехали
   ВЛЕВО оба столбца дня: замер верификатора, левый край поля «пн» гулял от 245
   до 297 px в одной колонке, и таблица читалась лесенкой. */
.org.gr-sel{{width:3.8rem;flex:0 0 3.8rem}}
/* 🔴 НА ТЕЛЕФОНЕ ЗАПРЕТ ПЕРЕНОСА ПРЕВРАЩАЕТСЯ В ГОРИЗОНТАЛЬНУЮ ПРОКРУТКУ.
   Фамилия и два выпадающих списка в 375 пикселей не помещаются никак, и строка
   уезжает за край экрана — то есть лечение узкой колонки на большом экране
   ломает маленький. Поэтому ниже 760 пикселей перенос возвращается: там колонка
   всё равно одна, и разваливать ей нечего. Поймано прогоном в мобильном виде,
   а не рассуждением: `scrollWidth > clientWidth` было истиной. */
@media(max-width:760px){{
  #s-rasp .para{{flex-wrap:wrap}}
  #s-rasp .para .kto{{white-space:normal;overflow:visible;text-overflow:clip}}
  #s-rasp .para .komu{{white-space:normal}}
  .org.pr-sel{{max-width:100%}}
  .kab-polya{{margin-left:0}}
}}
.tabl{{display:inline-flex;align-items:center;gap:0;padding:.14em .55em;
  border:1px solid var(--rule);border-radius:999px;background:var(--panel);
  font-family:var(--sans);font-size:.85rem;line-height:1.25;color:var(--text);
  white-space:nowrap;margin:.12em .3em .12em 0}}
.tabl[data-snyat]{{cursor:pointer}}
.tabl[data-snyat]:hover,.tabl[data-snyat]:focus-visible{{border-color:var(--krasn);
  background:var(--krasn-fon);color:var(--krasn);outline:none}}
.tabl .x{{width:0;overflow:hidden;color:var(--krasn);font-size:1rem;line-height:1;
  transition:width .12s,margin-left .12s}}
.tabl[data-snyat]:hover .x,.tabl[data-snyat]:focus-visible .x{{width:.7em;margin-left:.3em}}
/* Поля кабинета: два дня рядом, оба на одном экране. */
.kab-polya{{margin-left:auto;display:inline-flex;gap:.9rem;align-items:center;flex-wrap:wrap}}
.kab-pole{{display:inline-flex;align-items:center;gap:.4rem;font-size:.95rem;
  color:var(--muted)}}
.kab-pole input{{width:5rem;text-align:center;font-weight:600;font-size:1.05rem}}
.shapka{{display:flex;align-items:baseline;gap:1.2rem;flex-wrap:wrap}}
/* ── ВСПЛЫВАЮЩЕЕ ОКНО ВХОДА ── */
.okno{{position:fixed;inset:0;z-index:100;display:flex;align-items:center;
  justify-content:center;padding:1rem}}
.okno[hidden]{{display:none}}
.okno-fon{{position:absolute;inset:0;background:rgba(0,0,0,.45)}}
.okno-telo{{position:relative;background:var(--panel);border:1px solid var(--rule);
  border-radius:14px;padding:1.6rem 1.8rem;min-width:min(22rem,92vw);
  box-shadow:0 18px 50px rgba(0,0,0,.3);font-family:var(--sans)}}
.okno-telo h2{{margin:0 0 1rem;font-size:1.35rem;font-weight:600}}
.okno-telo label{{display:block;font-size:.95rem;color:var(--muted);margin:0 0 .35rem}}
.okno-telo input{{width:100%;font:inherit;font-size:1.1rem;padding:.55em .7em;
  border:1px solid var(--rule);border-radius:9px;background:var(--bg);color:var(--text)}}
.okno-telo input:focus{{outline:none;border-color:var(--accent)}}
.okno-oshibka{{color:var(--krasn);font-size:.95rem;margin:.7rem 0 0}}
.okno-knopki{{display:flex;gap:.6rem;justify-content:flex-end;margin-top:1.3rem}}
button.glavnaya,button.vtoraya{{font:inherit;font-family:var(--sans);font-weight:600;
  padding:.5em 1.4em;border-radius:9px;cursor:pointer;border:1px solid var(--rule);
  background:var(--panel);color:var(--text)}}
button.glavnaya{{background:var(--accent);border-color:var(--accent);color:#fff}}
button.glavnaya:hover{{opacity:.88}}
button.vtoraya{{color:var(--muted)}}
button.vtoraya:hover{{color:var(--text)}}
/* ── ПАНЕЛЬ НЕСОХРАНЁННЫХ ПРАВОК ── */
/* ── ВЕРХНЯЯ ПАНЕЛЬ: имя, разделы, поиск, права. Одна строка на всё. ── */
.menu .im{{font-weight:600;font-size:1.05rem;margin-right:1.4rem;white-space:nowrap;
  color:var(--text);padding:0;background:none;cursor:default}}
.menu .im:hover{{background:none}}
/* 🔴 ШИРЕ, А НЕ ПРЕЖНИЕ 34REM. Владелец 09.09, дословно: «почему ты выбрал
   какую-то очень узкую маленькую текстовую область? Хотя здесь места на
   каждой странице много». `.menu` уже переносит строку по `flex-wrap:wrap`,
   так что рост поля отодвигает соседей на вторую строку, а не режет их. */
.poisk-verh{{flex:3 1 24rem;max-width:56rem;margin:0 1.2rem;min-width:10rem}}
.poisk-verh .poisk{{margin:0;font-size:1rem;padding:.42em .8em;width:100%;max-width:none}}
.poisk-verh .spisok{{top:2.6rem}}
.poisk-verh #nashli{{position:absolute;left:0;right:0;top:2.6rem;z-index:19}}
.verh-prava{{display:flex;align-items:center;gap:.5rem;margin-left:auto;white-space:nowrap}}
.verh-prava button{{padding:.38em 1em;font-size:.98rem}}
.schyot-pravok{{font-variant-numeric:tabular-nums}}
.est-pravki .glavnaya{{box-shadow:0 0 0 3px var(--accent-soft)}}
button.glavnaya[disabled],button.vtoraya[disabled]{{opacity:.45;cursor:default}}
button.glavnaya[disabled]:hover{{opacity:.45}}
/* Панель занимает низ экрана — страница не должна прятать под ней последние строки. */
body{{padding-bottom:2rem}}
/* Тронутое, но не сохранённое — видно глазом и не спутаешь с сохранённым. */
.tronuto{{background:rgba(201,116,58,.10);outline:2px solid rgba(201,116,58,.35);
  outline-offset:2px;border-radius:6px}}
.tabl.snyato{{text-decoration:line-through;opacity:.55}}
/* Ответ сервера человеку. Отказ виден внизу экрана и не пропускается. */
.soob{{position:fixed;left:0;right:0;bottom:0;z-index:60;font-family:var(--sans);
  font-size:1.05rem;padding:.7rem 1.2rem;display:none}}
.soob.idet{{display:block;background:var(--accent-soft);color:var(--text)}}
.soob.ploho{{display:block;background:#c0392b;color:#fff;font-weight:600}}
/* Кнопка закрытия отказа. Она есть, потому что отказ больше не гаснет сам:
   пока человек её не нажал, сообщение стоит (см. `srazu` в `PRAVKA_SKRIPT`). */
.soob .soob-x{{float:right;margin-left:1rem;font-family:var(--sans);font-size:.95rem;
  font-weight:600;cursor:pointer;color:#fff;background:transparent;
  border:1px solid rgba(255,255,255,.6);border-radius:6px;padding:.15em .7em}}
/* Таблица преподавателей: колонки ровные, кабинет уходит вправо. */
.prep-tab{{width:100%;border-collapse:collapse}}
.prep-tab td{{padding:.55rem .8rem .55rem 0;border-bottom:1px solid var(--rule);
  vertical-align:baseline;font-size:1.75rem}}
.prep-tab .tp{{white-space:nowrap;width:1%;padding-right:2rem}}
.prep-tab .td-deti{{color:var(--muted);font-family:var(--sans);font-size:1.25rem;
  width:auto;padding-right:2rem}}
.prep-tab tr.skryt{{display:none}}
.prep-tab .tg{{font-family:var(--sans);font-weight:600;color:var(--accent);
  text-align:center;width:1%;white-space:nowrap}}
.prep-tab .tk{{text-align:right;width:1%;white-space:nowrap;padding-right:0}}
.para.skryt{{display:none}}
/* Переключатель дня — сверху справа, рядом с заголовком. */
.shapka-str{{display:flex;align-items:baseline;gap:1.5rem;flex-wrap:wrap;margin:0 0 .7rem}}
/* ── ДВА ДНЯ В ОДНОЙ СТРОКЕ ───────────────────────────────────────────────────
   Понедельник и четверг стоят рядом, столбцами равной ширины, и подписаны шапкой.
   Ширина фиксирована и одинакова у обоих: столбец, который меряется по самому
   длинному имени внутри себя, разъезжается от строки к строке, и глаз перестаёт
   читать таблицу сверху вниз — а читают её именно так (`doc/TZ-raspredelenie-
   dizajn-i-dva-sloya.md`: публичный вид читается ПО СТОЛБЦАМ). */
#v-shk .para .komu,#v-prep .para .komu,#v-В .para .komu,#v-Д .para .komu,
#v-Н .para .komu{{display:flex;align-items:baseline;justify-content:flex-end;
  gap:.4rem;min-width:0}}
/* 🔴 СТОЛБЕЦ ДНЯ НЕ СЖИМАЕТСЯ (`flex:0 0`), И ЭТО И ЕСТЬ «ОДНА ТАБЛИЧКА». Со
   сжатием ширина столбца зависела бы от длины имени в СВОЕЙ строке, столбцы
   разъезжались бы по вертикали, и таблицу нельзя было бы читать сверху вниз —
   а читают её именно так. На узком экране раскладка и так уходит в одну колонку
   (медиазапрос ниже), поэтому фиксированная ширина здесь ничего не ломает. */
/* 🔴 КОЛОНКА ДНЯ — ФЛЕКС-РЯД ИЗ ДВУХ ЧАСТЕЙ, А НЕ ОДНА СТРОКА ТЕКСТА (ПРАВКА 1,
   владелец: «на первом скриншоте с номерами кабинетов… они должны быть выравнены
   в колонку»). Ширина ячейки фиксирована (`flex:0 0 9.6rem`), как и была; но
   раньше имя преподавателя и плашка кабинета были СКЛЕЕНЫ в одну надпись внутри
   неё — на длинных именах («Лена Мирошниченко», «Александр Тертерян», 18
   символов, сняты запросом к живой базе) плашка выдавливалась за правую границу
   колонки и налезала на соседнюю. Теперь `.prep-imya` — усекаемое многоточием
   (`flex:1 1 auto`, отдаёт место соседу), `.kab-mesto` — несжимаемое
   (`flex:0 0 auto`): плашка держит своё место у правого края ВСЕГДА, чем бы имя
   ни было. */
.para .komu .dv{{flex:0 0 12.5rem;min-width:0;display:flex;align-items:baseline;
  justify-content:flex-end;gap:.3rem}}
.para .komu .dv .prep-imya{{flex:1 1 auto;min-width:0;overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap;text-align:right}}
.para .komu .dv .kab-mesto{{flex:0 0 auto}}
/* Ячейка без вложенных частей (например пустая ячейка заголовка `shapka_dnej`,
   `.dv-gr`/`.dv-zam`) держит своё прежнее поведение: `justify-content:flex-end`
   уже прижимает голый текстовый узел вправо без потребности в `.prep-imya`. */
/* 🔴 ТА ЖЕ БОЛЕЗНЬ НА ВКЛАДКЕ «ПРИНИМАЮЩИМ» (ПРАВКА 1, второй скриншот владельца
   — «с именами преподавателей»): плашка кабинета была последним элементом ВНУТРИ
   `.deti-ryad` (список детей переносится по словам), и вставала там, где перенос
   случайно кончился в конкретной строке — не колонкой. `.kab-mesto` здесь —
   сосед `.deti-ryad` внутри `.den-ryad`, тем же приёмом, что уже решает эту
   задачу для счётчика `.sch` двумя строками ниже. */
.den-ryad .kab-mesto{{flex:0 0 auto;margin-left:auto}}
/* Пустые ячейки шапки ровно под замком и полем группы — те же ширины, что у них. */
.para .komu .dv-gr{{flex:0 0 3.8rem}}
.para .komu .dv-zam{{flex:0 0 1.7rem}}
/* Подпись дня — мелкая и ровно над своим столбцом; крупная подпись съедала
   высоту строки и толкала последнего школьника за нижний край экрана. */
.shapka-dnej{{font-size:.72rem;padding:.1rem 0}}
.shapka-dnej .komu .dv{{color:var(--faint)}}
.para .komu .dv .org{{max-width:100%;width:100%}}
.shapka-dnej{{border-bottom:2px solid var(--rule);color:var(--faint);
  font-family:var(--sans);font-size:.85rem;letter-spacing:.06em;text-transform:uppercase}}
#v-shk .shapka-dnej,#v-В .shapka-dnej,#v-Д .shapka-dnej,#v-Н .shapka-dnej{{font-size:.85rem}}
.shapka-dnej .komu .dv{{color:var(--faint)}}
/* Шапка столбцов в таблице принимающих — та же роль, другой элемент. */
.prep-shapka td{{color:var(--faint);font-family:var(--sans);font-size:.85rem;
  letter-spacing:.06em;text-transform:uppercase;border-bottom:2px solid var(--rule)}}
/* Ячейка дня в таблице принимающих: два столбца детей, потом галочки и группа;
   у четверга своя граница слева — иначе он читается как продолжение понедельника. */
.prep-tab td.dv-cht{{border-left:1px solid var(--rule)}}
.tdni{{white-space:nowrap;width:1%;padding-right:1.2rem}}
/* 🔴 ЭТО КНОПКИ, А НЕ ГАЛОЧКИ, И КВАДРАТИКА В НИХ НЕТ. Владелец 07.09: «там не
   нужна галочка, нужна просто кнопка, на которую можно нажать. Квадратик не
   нужен. Чем больше таких элементов, тем сложнее и хуже выглядит». На экране их
   по одной на каждого из 54 школьников, и квадратик рядом с каждым словом даёт
   вдвое больше предметов, чем ответов. Сам `input` остаётся — он и есть
   состояние, и он же делает кнопку доступной с клавиатуры, — но его не видно. */
.den-gal input,.otsut input,.zamok input{{position:absolute;width:1px;height:1px;
  opacity:0;pointer-events:none}}
.den-gal,.otsut,.zamok{{display:inline-flex;align-items:center;cursor:pointer;
  font-family:var(--sans);font-weight:600;line-height:1.2;white-space:nowrap;
  border-radius:7px;border:1px solid transparent;transition:none}}
.den-gal{{font-size:.88rem;color:var(--accent);border-color:var(--accent);
  background:var(--accent-soft);padding:.16em .55em;margin-right:.3rem}}
.den-gal.pusto{{color:var(--faint);border-color:var(--rule);background:none}}
.den-gal:hover{{border-color:var(--accent)}}
/* Гостю — та же метка без органа: закрашена, если человек в этот день приходит. */
.den-metka{{display:inline-block;font-family:var(--sans);font-size:.9rem;font-weight:700;
  color:var(--accent);border:1px solid var(--accent);border-radius:8px;
  padding:.14em .5em;margin-right:.35rem;background:var(--accent-soft)}}
.den-metka.pusto{{color:var(--faint);border-color:var(--rule);background:none}}
/* Вместо кнопки «Сохранить» на экране занятия — строка о том, что её нет и почему. */
.srazu{{font-family:var(--sans);font-size:.9rem;color:var(--muted);margin-right:.9rem}}

/* «Отсутствует» — одна и та же кнопка у школьника и у принимающего: тот же
   орган, то же слово, тот же вид. Ненажатая — тихая, серая; нажатая — тёплая
   заливка, потому что это состояние, в котором человек СЕГОДНЯ отсутствует, и
   его надо видеть краем глаза, не читая. */
.otsut{{font-size:.82rem;color:var(--faint);border-color:var(--rule);
  padding:.14em .6em;margin-left:.5rem}}
.otsut:hover{{color:var(--warm);border-color:var(--warm)}}
.otsut:not(.pusto){{color:var(--warm);border-color:var(--warm);
  background:var(--krasn-fon)}}
/* Замок связки дней: зажат — дни правятся вместе, открыт — врозь. */
.zamok{{font-size:.95rem;padding:.06em .3em;margin:0 .15rem;border-color:transparent;
  color:var(--accent)}}
.zamok.otkryt{{color:var(--faint);opacity:.75}}
.zamok:hover{{border-color:var(--rule)}}
/* Пока правка одного занятия едет в базу — строка приглушена. Она уезжает сразу,
   без кнопки, и человеку нужен признак, что нажатие принято. */
.para.idet,tr.idet{{opacity:.45}}
/* Строка занятия: отмеченный отсутствующим — серым, а не вычеркнутым (он вернётся
   сам); единственное красное — ребёнок, которого сегодня никто не ждёт. */
#s-rasp .para.net .kto{{color:var(--faint)}}
#s-rasp .para.krasn .kto b{{color:var(--krasn)}}
/* Шапка страницы занятия: дата — орган, стрелки рядом, дверь в постоянное — справа. */
.zan-navig{{display:flex;align-items:center;gap:.35rem;margin-left:auto;
  font-family:var(--sans);position:relative}}
/* 🔴 СТРЕЛКИ ОПИСАНЫ ЗДЕСЬ, И ИМЕННО ПОЭТОМУ ОНИ БОЛЬШЕ НЕ СИНЕ-ФИОЛЕТОВЫЕ.
   Класс `.strelka` был описан в `veb/static/zanyatie.css` — файле СТАРОЙ
   отдельной страницы занятия. Внутри сайта его нет, и ссылки красились
   браузером по умолчанию: непосещённая синяя, посещённая фиолетовая. Владелец:
   «почему загорается стрелочка неправильного цвета?.. превращают сайт в дизайн
   из какого-то 1998 года». Цвет ссылки, заданный браузером, — всегда чужой. */
.zan-navig .strelka{{display:inline-flex;align-items:center;justify-content:center;
  width:1.9rem;height:1.9rem;border-radius:8px;text-decoration:none;
  color:var(--muted);font-size:1.05rem;line-height:1;border:1px solid var(--rule)}}
.zan-navig .strelka:hover{{color:var(--accent);border-color:var(--accent);
  background:var(--accent-soft)}}
/* Кнопка даты не выше строки вкладок: её рамка налезала на линию под вкладками,
   и на наведении это читалось как сбой вёрстки (замечание владельца 07.09). */
.data-zan{{cursor:pointer;color:var(--text);font-size:1.02rem;font-weight:600;
  white-space:nowrap;padding:.18em .65em;border:1px solid var(--rule);
  border-radius:8px;line-height:1.35}}
.data-zan:hover{{border-color:var(--accent);color:var(--accent)}}
/* 🔴 ПАНЕЛЬ ЗАНЯТИЙ ВМЕСТО СИСТЕМНОГО КАЛЕНДАРЯ. Владелец 07.09: «нам не нужен
   календарь — у нас занятия два раза в неделю… нужна своя кастомная большая
   панель, на которой легко достичь расписание года в кратком виде». Календарь
   предлагает 365 дней, из которых годятся 64, и заставляет человека отсеивать
   то, что система знает сама. Здесь весь год стоит месяцами, занятие — кнопкой
   с числом и днём; прошедшие приглушены, сегодняшнее обведено. */
/* 🔴 ПАНЕЛЬ ЗАНИМАЕТ МЕСТО, КОТОРОЕ У НЕЁ ЕСТЬ. Владелец 07.09: «у тебя огромное
   пространство есть, которое ты можешь занять расписанием… сделай его шире —
   кнопки больше, в два раза шире, чтобы всё было видно, удобная навигация,
   ничего не вылезало в две строки». Узкая панель ломала каждый месяц на две
   строки и превращала год в лестницу. */
.kal-panel{{display:none;position:absolute;top:calc(100% + .6rem);right:0;z-index:60;
  max-height:76vh;overflow:auto;padding:1.1rem 1.4rem;border:1px solid var(--rule);
  border-radius:14px;background:var(--panel);box-shadow:0 16px 40px rgba(0,0,0,.32);
  width:min(64rem,92vw)}}
#p-kal:checked~.kal-panel{{display:block}}
.zan-navig #p-kal:checked~.data-zan,.data-zan:has(~#p-kal:checked){{
  border-color:var(--accent);color:var(--accent);background:var(--accent-soft)}}
.kal-mesyac{{display:flex;align-items:center;gap:.9rem;padding:.42rem 0}}
.kal-mesyac+.kal-mesyac{{border-top:1px solid var(--rule)}}
.kal-imya{{flex:0 0 7rem;color:var(--muted);font-size:.95rem}}
.kal-dni{{display:flex;flex-wrap:wrap;gap:.4rem}}
.kal-den{{display:inline-flex;align-items:baseline;gap:.25rem;text-decoration:none;
  color:var(--text);font-size:1.02rem;font-weight:600;padding:.3em .75em;
  border:1px solid var(--rule);border-radius:9px;min-width:4rem;
  justify-content:center}}
.kal-den:hover{{border-color:var(--accent);color:var(--accent);
  background:var(--accent-soft)}}
.kal-den.bylo{{color:var(--faint);border-color:transparent}}
.kal-den.tut{{color:var(--panel);background:var(--accent);border-color:var(--accent)}}
.kal-sokr{{font-size:.72rem;font-weight:400;opacity:.75}}
.k-drugomu{{font-size:.92rem;text-decoration:none;color:var(--muted);
  border:1px solid var(--rule);border-radius:9px;padding:.35em .8em;white-space:nowrap}}
.k-drugomu:hover{{color:var(--accent);border-color:var(--accent)}}
.menu a.ssyl.ssyl-tut{{color:var(--accent);background:var(--accent-soft)}}
.poisk-str{{margin:0;max-width:32rem;flex:1 1 18rem}}
@media(max-width:900px){{.dva{{grid-template-columns:1fr}}
  .kol{{border-right:none;padding-right:0}}}}
/* Карточки группы: всё на один экран, колонками — преподаватель и его дети. */
.karty{{display:grid;grid-template-columns:repeat(auto-fill,minmax(15rem,1fr));gap:1rem}}
.kart{{border:1px solid var(--rule);border-radius:10px;padding:.7rem .9rem;background:var(--panel)}}
.kart-z{{display:flex;align-items:baseline;gap:.4rem;font-family:var(--sans);font-size:1rem;
  padding-bottom:.4rem;margin-bottom:.4rem;border-bottom:1px solid var(--rule)}}
.kart-z .ch{{margin-left:auto;color:var(--muted)}}
.kart ul{{list-style:none;margin:0;padding:0}}
.kart li{{font-size:.95rem;padding:.12rem 0}}
.kart.zhd{{border-color:var(--warm)}}
.kart.zhd .kart-z b{{color:var(--warm)}}
/* Листки: номер · название · версии в одну строку. */
.listki{{max-width:46em}}
.listki td{{padding:.4rem 1rem .4rem 0}}
.listki .nom{{font-family:var(--sans);font-weight:600;color:var(--faint);
  width:3.5rem;white-space:nowrap}}
.listki a{{color:var(--accent);text-decoration:none;font-size:1.05rem}}
.listki a:hover{{text-decoration:underline}}
.verstroka{{white-space:nowrap;text-align:right}}
.ver{{display:inline-block;font-family:var(--sans);font-weight:600;background:var(--chip);
  border-radius:7px;padding:.12em .6em;margin-left:.35rem;color:var(--text)!important;
  text-decoration:none!important}}
.ver:hover{{background:var(--accent);color:var(--panel)!important}}
.polug{{font-family:var(--sans);font-size:.85rem;font-weight:600;letter-spacing:.09em;
  text-transform:uppercase;color:var(--faint);margin:1.8rem 0 .5rem}}
.polug:first-child{{margin-top:0}}
.menu label.im{{font-weight:600;font-size:1.05rem;margin-right:1.6rem;color:var(--text);
  padding-left:0}}
.fajly{{list-style:none;margin:0;padding:0;columns:2;column-gap:3rem}}
.fajly li{{padding:.4em 0;border-bottom:1px solid var(--rule);break-inside:avoid}}
.fajly a{{color:var(--accent);text-decoration:none;font-size:1.05rem}}
@media(max-width:760px){{.menu,.holst{{padding-left:1.1rem;padding-right:1.1rem}}.fajly{{columns:1}}}}

/* ═══ 🔴 ТЕЛЕФОН. ВСЁ НИЖЕ — ТОЛЬКО ВНУТРИ МЕДИАЗАПРОСОВ, ДЕСКТОП НЕ МЕНЯЕТСЯ.
   Требование владельца 07.09: «твоя задача не менять ничего, кроме мобильной
   версии, но её нужно довести до идеала на всех экранах, в первую очередь на
   главном, во вторую на странице с приёмом/кондуитом».

   ЧТО БЫЛО СЛОМАНО, ИЗМЕРЕНО НА ЖИВОЙ СТРАНИЦЕ ПРИ 375px, А НЕ НА ГЛАЗ:
   страница переполнялась вбок на 145px — `.glav-glavnoe` занимала 502px при
   экране 375. Виновата не сетка (она уже `minmax(0,1fr)` и с 940px в одну
   колонку), а `.blok-listok{{width:max-content}}`: карточка растягивалась по
   самой длинной своей строке — списку фамилий «302 · Бирюков, Будылин,
   Искеева, Тухватулин-Йалчын» — и распирала колонку изнутри. Следом за ней
   уезжал вправо весь блок «кто ведёт», и имена преподавателей обрезались
   краем экрана: владелец видел «Ольга Р», «Даня Ма», «Ваня Яко».

   Второе: кегли главной заданы `clamp(...vw...)`, и их НИЖНЯЯ граница считана
   под ноутбук — `.vedut` держал 25.6px, `.rasp` 22.4px на экране в 375
   пикселей. `vw` тут не спасает: при узком экране включается именно минимум.
   Поэтому телефон получает свои размеры, а не масштабированные ноутбучные.

   🔴 Ни одно правило отсюда не действует шире 760px: закреплённый десктопный
   вид (`doc/DIZAJN-ZAKREPLENO.md`) остаётся ровно таким, каким владелец его
   принял, и эталонные числа §5 снимаются при 1440×900 как раньше. ═══ */
@media(max-width:760px){{
  /* Карточка ближайшего листка. Схема не трогается — те же гарнитура, кегли,
     цвета и ноль плашек, что стережёт `proverit_shemu()`; меняется ТОЛЬКО то,
     что карточка перестаёт быть шире экрана. */
  .blok-listok{{width:auto;max-width:100%;margin-top:2rem}}
  .listok-kogda,.listok-stroka,.listok-kab{{white-space:normal;overflow-wrap:anywhere}}
  .listok-imya{{font-size:2.1rem}}

  /* «Кто ведёт» — предмет и имя в одной строке, но кеглем, который помещается. */
  .vedut{{font-size:1.05rem;width:100%}}
  .vedut td{{padding:.32rem 0}}
  .vedut .predmet{{padding-right:.9rem;font-size:.95rem;white-space:normal}}

  /* Расписание и списки преподавателей: одна колонка вместо двух — на 375px
     вторая колонка давала по два слова в строке. */
  .rasp{{font-size:1.05rem;width:100%}}
  .rasp .den-imya{{padding-right:.9rem}}
  .rasp td{{padding:.3rem 0}}
  .prep-spisok{{columns:1;font-size:1rem}}
  .prep-spisok.ranshe{{columns:1;font-size:.92rem}}

  /* Заголовок и воздух: на телефоне первый экран должен показывать не только
     название, но и то, ради чего страницу открыли. */
  .glav-imya{{font-size:2.5rem;line-height:1.05}}
  .glav-pod{{font-size:1rem}}
  .glav-setka{{gap:1.5rem 0;margin-top:1rem}}
  /* На ноутбуке колонка растянута на всю высоту и раскладывает блоки
     `space-between`; на телефоне высоты нет, и та же раскладка оставляла между
     заголовком и карточкой пустую треть экрана. */
  .glav-glavnoe{{justify-content:flex-start;gap:1.5rem;padding-bottom:0}}
  .glav-sboku{{gap:1.5rem}}
  .glav{{min-height:0}}

  /* Шапка занимала 174px — почти четверть экрана, и это до всякого содержания.
     Меню прокручивается вбок одной строкой вместо того, чтобы переноситься. */
  .menu{{padding:.55rem 1.1rem;gap:.2rem;flex-wrap:nowrap;overflow-x:auto;
    -webkit-overflow-scrolling:touch}}
  .menu::-webkit-scrollbar{{display:none}}
  .menu .im{{font-size:.98rem;margin-right:.7rem}}
  .menu label,.menu a.ssyl{{font-size:.98rem;padding:.3em .7rem;white-space:nowrap}}
  .poisk{{font-size:1rem;padding:.5em .7em}}
}}

/* Совсем узкие телефоны (iPhone SE и ему подобные): на 320 точках заголовок в
   2.5rem встаёт впритык к краю, и запаса не остаётся ни на что. */
@media(max-width:380px){{
  .glav-imya{{font-size:2.05rem}}
  .listok-imya{{font-size:1.85rem}}
  .glav-pod{{font-size:.95rem}}
}}{lich_stili}{kond_stili}
</style>
<!-- 🔴 КАНОН КОЛОНОК СТОИТ ПОСЛЕ ВСТРОЕННОГО СТИЛЯ, И ПОРЯДОК ЗДЕСЬ — ЧАСТЬ
     ПРАВИЛА, А НЕ ОФОРМЛЕНИЕ. The canon is the site's last word about columns:
     where a rule of the stylesheet above contradicts it, the canon must win, and
     between two rules of equal specificity the later one wins. Moved above the
     `<style>` this link keeps its text and loses its force. The file itself says
     what the canon is and who has yet to adopt it: `veb/static/kanon.css`. -->
<link rel="stylesheet" href="/static/kanon.css">

<input class="rd" type="radio" name="str" id="p-start"{start_vybran}>
<input class="rd" type="radio" name="str" id="p-list">
<input class="rd" type="radio" name="str" id="p-rasp"{rasp_vybran}>{lich_vhod}{kond_vhod}

<!-- ВЕРХНЯЯ ПАНЕЛЬ. Имя сайта стоит ОДИН раз и здесь; разделы больше не повторяют
     своё название заголовком внутри себя. Поиск живёт тут же и работает на всех
     разделах — искать надо там, где смотришь, а не там, где нашлось место.

     🔴 «РАСПРЕДЕЛЕНИЕ» IS A LINK, NOT A TAB, AND IT LEADS TO THE LESSON.
     Owner's решение 1 of 2026-09-07. The tab it used to be opened the STANDING
     arrangement, so the page written for «кто у кого сегодня» was reachable by
     nobody: the owner pressed «Распределение», landed in the editor of the
     permanent layer and concluded the work had not been merged. The permanent
     layer keeps its own address, `/raspredelenie/postoyannoe`, and the button
     that says what it is stands on the lesson page — «чтобы ты случайно всё не
     начинал править постоянное распределение».

     The radio `p-rasp` below stays: it is what SHOWS the standing section, and
     `/raspredelenie/postoyannoe` checks it (VKLADKA_SKRIPT). Removing it would
     take the section off the site altogether. -->
<nav class="menu">
  <span class="im">Ключики</span>
  {punkty}
  <a class="ssyl ssyl-rasp{rasp_aktivna}" href="{rasp_adres}">Распределение</a>{kond_metka}{zhurnal_metka}
  <div class="podskazki poisk-verh">
    <input class="poisk" id="poisk" placeholder="Поиск — школьник, принимающий, листок" autocomplete="off">
    <div class="spisok" id="spisok" hidden></div>
    <div id="nashli"></div>
  </div>
  {verh}
</nav>

{glavnaya}

{listki}

{raspredelenie}{lichnaya}{konduit}

{poisk_skript}
{hvost}
"""

# ─────────────────────────────────── ПАМЯТЬ ВКЛАДОК, ОБЩАЯ ДЛЯ ВСЕХ СТРАНИЦ

#: 🔴 ВКЛАДКА СБРАСЫВАЛАСЬ НА ПЕРВУЮ ПРИ КАЖДОЙ ПЕРЕЗАГРУЗКЕ, И ЭТО БЫЛО ВИДНО
#: ВЛАДЕЛЬЦУ КАЖДЫЙ ДЕНЬ. Его слова 11.09: «когда я перезагружаю страницу, часто
#: переключается вкладка; в том числе если зайти на страницу журнала преподавателей
#: и обновить, открывается журнал школьников; на других страницах тоже такое бывает».
#: ПРИЧИНА, НАЙДЕННАЯ ЗАМЕРОМ, А НЕ ДОГАДКОЙ: механизм памяти вкладок в проекте УЖЕ
#: БЫЛ (`spetsmat-vkladki`, localStorage), но жил внутри скрипта ГЛАВНОЙ страницы, а
#: разделы `/istoria` и `/kabinet` собирают свой документ сами и этот скрипт не
#: подключают — проверено: `"spetsmat-vkladki" in html` давало False на обеих.
#: Поэтому память вынесена сюда и подключается КАЖДОЙ страницей с вкладками.
#: Запоминаются все радио-вкладки по имени группы, а не только класс `rd`: вкладки
#: четвертей в кабинете носят класс `kab-p`, и прежний селектор их не видел.
SKRIPT_PAMYAT_VKLADOK = """
<script>
(function(){
  var PAMYAT = "spetsmat-vkladki";
  function vse(){ return document.querySelectorAll('input[type=radio][name]'); }
  function zapomnit(){
    try{
      var bylo = {};
      try{ bylo = JSON.parse(localStorage.getItem(PAMYAT) || "{}"); }catch(e){}
      vse().forEach(function(r){ if(r.checked && r.id){ bylo[r.name] = r.id; } });
      localStorage.setItem(PAMYAT, JSON.stringify(bylo));
    }catch(e){}
  }
  function vspomnit(){
    try{
      var bylo = JSON.parse(localStorage.getItem(PAMYAT) || "{}");
      Object.keys(bylo).forEach(function(imya){
        var r = document.getElementById(bylo[imya]);
        if(r && r.name === imya && r.type === "radio"){ r.checked = true; }
      });
    }catch(e){}
  }
  vspomnit();
  document.addEventListener("change", function(sob){
    var t = sob.target;
    if(t && t.type === "radio" && t.name){ zapomnit(); }
  });
})();
</script>
"""
