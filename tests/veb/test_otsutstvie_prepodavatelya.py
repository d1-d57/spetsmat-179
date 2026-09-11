"""Tests for a teacher's PERIOD OF ABSENCE — storage, door, journal, distribution.

WHAT THE OWNER ASKED FOR, 11.09, in his own words: *«Есть Ольга Александровна, Ольга
Рыжая, которая не будет с 1 по 12 октября… чтобы в будущих всех распределениях период
этот на всех занятиях этого периода уже не появлялось в списке преподавателей… И чтобы
это сразу выделялось в журнале преподавателей»*.

🔴 THE DISTRIBUTION IS CHECKED THROUGH `karkas.sobrat_kontekst`, NOT THROUGH A HAND-BUILT
`Kontekst`. A fabricated context would prove that the filter filters, and nothing about
whether the page ever reaches it: the period has to be read out of the база, land in
`Kontekst.otsutstvie_po_dnyam`, and only then narrow the list. That whole chain is what
the owner's sentence is about, and only the real builder runs all of it.

🔴 WHY THE PERMANENT SCREEN NEEDS `blizhajshij_den` PATCHED, AND WHY THAT IS NOT CHEATING.
The permanent screen has no date of its own — it shows the NEAREST Monday and Thursday,
computed from the clock. To ask it about the 3rd of October the clock has to say that the
3rd of October is the day it opens on; there is no other input. The narrowing itself is
not patched, only which two dates the screen is looking at.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import urllib.error
import urllib.request
from datetime import date, timedelta
from http.server import ThreadingHTTPServer

import config
import pytest
from infra.db import apply_migrations, connect

os.environ.setdefault("SPETSMAT_VEB_SECRET", "test-secret-key-32bytes!")

import veb.server as server
from veb import vhod
from veb.obshchee import karkas
from veb.razdely import istoria_zanyatij, shkolniki

#: Живой случай владельца, день в день.
S_DATY, PO_DATU = "2026-10-01", "2026-10-12"
DNEJ_V_PERIODE = 12


def _dni_perioda() -> list:
    d, konec, out = date.fromisoformat(S_DATY), date.fromisoformat(PO_DATU), []
    while d <= konec:
        out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def _proshedshij_ponedelnik() -> str:
    """Прошедший понедельник-занятие, ЛЕЖАЩИЙ В ПОКАЗЫВАЕМОЙ ЧЕТВЕРТИ.

    🔴 ПРАВКА СЛИЯНИЯ, А НЕ КОСМЕТИКА, И У НЕЁ ЗАМЕР. Здесь стояло «сегодня минус
    семь, назад до понедельника». Пока столбцами журнала были ЗАПИСАННЫЕ дни, этого
    хватало; с 11.09 столбцы — календарь ЧЕТВЕРТИ (владелец: «распланированная сразу
    на 16 занятий»), и 11.09 эта формула давала 31.08 — прошлый учебный год, за краем
    всех шестнадцати столбцов. Клетка периода честно рисовалась и в решётку не
    попадала: тест краснел на дате фикстуры, а не на коде страницы.
    Дата берётся теперь из ТОЙ ЖЕ функции, что строит столбцы: последний прошедший
    понедельник нынешней четверти, а если в ней такого ещё нет — предыдущей.
    """
    from veb.obshchee import karkas

    segodnya = date.today().isoformat()
    vse = karkas.chetverti_goda(segodnya)
    for nomer in range(karkas.nomer_chetverti(segodnya), 0, -1):
        pn = [d for d in vse[nomer - 1]
              if d < segodnya and date.fromisoformat(d).isoweekday() == 1]
        if pn:
            return pn[-1]
    # В учебном году ещё не было ни одного прошедшего понедельника-занятия: вернуть
    # первый понедельник первой четверти честнее, чем выдумать дату вне решётки, —
    # тест тогда скажет своё «нет клетки» про реальное состояние календаря.
    return next(d for d in vse[0] if date.fromisoformat(d).isoweekday() == 1)


@pytest.fixture
def baza(tmp_path):
    """Одна Ольга, один сосед, двое детей, у обоих открытое закрепление на оба дня."""
    db_path = tmp_path / "spetsmat.db"
    apply_migrations(db_path, config.MIGRATIONS_DIR)
    c = connect(db_path)
    c.execute("alter table teachers add column aktiven integer not null default 1")
    c.execute("alter table teachers add column gruppa text")
    c.execute("alter table students add column gruppa text")
    olga = c.execute("insert into teachers (name, aka, aktiven, gruppa) "
                     "values ('Ольга Рыжая', 'ОР', 1, 'В')").lastrowid
    sosed = c.execute("insert into teachers (name, aka, aktiven, gruppa) "
                      "values ('Пётр Соседний', 'ПС', 1, 'В')").lastrowid
    deti = []
    for familia, imya in (("Фефелов", "Иван"), ("Агаркова", "Ирина")):
        deti.append(c.execute(
            "insert into students (surname, name, class, status) values (?, ?, '9К', 'active')",
            (familia, imya)).lastrowid)
    for sid in deti:
        for slot in (1, 2):
            c.execute("insert into enrollment "
                      "(student_id, teacher_id, room, slot, valid_from, valid_to) "
                      "values (?, ?, '301', ?, '2020-01-01', ?)",
                      (sid, olga, slot, config.OPEN_END_DATE))
    for kod, starshij in (("В", "Ваня"), ("Д", "Даня"), ("Н", "Наталья")):
        c.execute("insert into gruppy (kod, starshij) values (?, ?)", (kod, starshij))
    c.commit()
    yield {"put": db_path, "c": c, "olga": olga, "sosed": sosed, "deti": deti}
    c.close()


# ───────────────────────────────────────────────────────── часть 1 · ХРАНИЛИЩЕ


def test_migracia_zavodit_tablicu_i_oba_konca_vklyucheny(baza):
    c = baza["c"]
    karkas.otmetit_otsutstvie(c, baza["olga"], S_DATY, PO_DATU, "болезнь")
    c.commit()
    est = [d for d in _dni_perioda()
           if baza["olga"] in karkas.otsutstvuyushchie_na_datu(c, d)]
    assert len(est) == DNEJ_V_PERIODE, "период обязан накрывать ровно двенадцать дней"
    assert baza["olga"] not in karkas.otsutstvuyushchie_na_datu(c, "2026-09-30")
    assert baza["olga"] not in karkas.otsutstvuyushchie_na_datu(c, "2026-10-13")


def test_zapis_pomnit_kto_pochemu_i_kogda(baza):
    """Задание §1: «кто, с какой даты, по какую, почему, кто отметил, когда»."""
    c = baza["c"]
    karkas.otmetit_otsutstvie(c, baza["olga"], S_DATY, PO_DATU, "отъезд",
                              kto_otmetil=baza["sosed"], zametka="конференция")
    c.commit()
    (zapis,) = karkas.periody_otsutstvij(c)
    assert zapis["teacher_id"] == baza["olga"]
    assert (zapis["s_daty"], zapis["po_datu"]) == (S_DATY, PO_DATU)
    assert zapis["prichina"] == "отъезд"
    assert zapis["kto_otmetil"] == baza["sosed"]
    assert zapis["kogda"].startswith("20") and "T" in zapis["kogda"]


def test_prichina_i_poryadok_dat_otkazyvayut(baza):
    c = baza["c"]
    with pytest.raises(ValueError):
        karkas.otmetit_otsutstvie(c, baza["olga"], S_DATY, PO_DATU, "грипп")
    with pytest.raises(ValueError):
        karkas.otmetit_otsutstvie(c, baza["olga"], PO_DATU, S_DATY, "болезнь")


def test_neskolko_periodov_na_odnogo_cheloveka_zakonny(baza):
    """Пересечение — не противоречие: обе записи говорят одно и то же слово «нет»."""
    c = baza["c"]
    karkas.otmetit_otsutstvie(c, baza["olga"], S_DATY, PO_DATU, "болезнь")
    karkas.otmetit_otsutstvie(c, baza["olga"], "2026-10-05", "2026-10-20", "отъезд")
    c.commit()
    assert len(karkas.periody_otsutstvij(c)) == 2
    assert baza["olga"] in karkas.otsutstvuyushchie_na_datu(c, "2026-10-20")


def test_obespechit_povtoryaet_migraciyu_pole_v_pole(tmp_path):
    """🔴 КОПИЯ ОПРЕДЕЛЕНИЯ — ДОЛГ, И ОН СТОРОЖИТСЯ ЗДЕСЬ.

    `karkas.obespechit_otsutstvia` повторяет `create table` миграции 013 словом в
    слово, потому что `infra/` вне зоны этого захода. Разойдясь, две версии дадут
    разную таблицу на машине, где миграция применена, и на машине, где нет. Гейт —
    этот тест: он строит таблицу обоими путями и сверяет колонки.
    """
    po_migracii = tmp_path / "m.db"
    apply_migrations(po_migracii, config.MIGRATIONS_DIR)
    a = connect(po_migracii)

    po_ruke = sqlite3.connect(str(tmp_path / "r.db"))
    po_ruke.row_factory = sqlite3.Row
    karkas.obespechit_otsutstvia(po_ruke)

    def kolonki(soединение):
        return [(r["name"], r["type"], r["notnull"], r["pk"]) for r in
                soединение.execute("pragma table_info(otsutstvie_prepodavatelya)")]

    assert kolonki(a) == kolonki(po_ruke) != []
    a.close()
    po_ruke.close()


# ───────────────────────────────────────────────────────── часть 2 · ОТМЕТИТЬ


@pytest.fixture
def server_s_bazoj(baza):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    httpd.db_path = str(baza["put"])  # type: ignore[attr-defined]
    port = httpd.server_address[1]
    potok = threading.Thread(target=httpd.serve_forever, daemon=True)
    potok.start()
    try:
        yield dict(baza, adres="http://127.0.0.1:%d" % port)
    finally:
        httpd.shutdown()
        httpd.server_close()
        potok.join()


def _kuka(rol_cheloveka="organizator"):
    """Заголовок `Cookie:` целиком. `_make_cookie` отдаёт ЗНАЧЕНИЕ, а не пару
    «имя=значение», и без имени `vhod._kuka_iz_zagolovkov` куку не находит — дверь
    честно отвечает «нужно войти» на подписанную куку.
    """
    return "%s=%s" % (vhod.COOKIE_NAME, vhod._make_cookie(rol_cheloveka))


def _post(adres, telo, rol_cheloveka="organizator"):
    zapros = urllib.request.Request(
        adres + "/api/otsutstvie", data=json.dumps(telo).encode("utf-8"),
        headers={"Content-Type": "application/json", "Cookie": _kuka(rol_cheloveka)},
        method="POST")
    try:
        with urllib.request.urlopen(zapros) as otvet:
            return otvet.status, json.loads(otvet.read())
    except urllib.error.HTTPError as oshibka:
        return oshibka.code, json.loads(oshibka.read() or b"{}")


def _stranica(adres, rol_cheloveka="organizator"):
    zapros = urllib.request.Request(adres + "/istoria",
                                    headers={"Cookie": _kuka(rol_cheloveka)})
    with urllib.request.urlopen(zapros) as otvet:
        return otvet.read().decode("utf-8")


def test_dver_otmechaet_period_vperyod(server_s_bazoj):
    kod, otvet = _post(server_s_bazoj["adres"], {
        "teacher_id": server_s_bazoj["olga"], "s_daty": S_DATY,
        "po_datu": PO_DATU, "prichina": "болезнь"})
    assert kod == 200, otvet
    assert otvet["dnej"] == DNEJ_V_PERIODE
    assert server_s_bazoj["olga"] in karkas.otsutstvuyushchie_na_datu(
        connect(server_s_bazoj["put"]), "2026-10-07")


def test_dver_otmechaet_i_zadnim_chislom(server_s_bazoj):
    """«Заболел сегодня» — та же дверь и та же строка, без запрета на прошлое."""
    vchera = (date.today() - timedelta(days=1)).isoformat()
    kod, otvet = _post(server_s_bazoj["adres"], {
        "teacher_id": server_s_bazoj["olga"], "s_daty": vchera,
        "po_datu": vchera, "prichina": "болезнь"})
    assert kod == 200, otvet
    assert otvet["dnej"] == 1


def test_dver_otkazyvaet_na_krivyh_dannyh(server_s_bazoj):
    adres = server_s_bazoj["adres"]
    olga = server_s_bazoj["olga"]
    assert _post(adres, {"teacher_id": olga, "s_daty": "2026-13-45",
                         "po_datu": PO_DATU, "prichina": "болезнь"})[0] == 400
    assert _post(adres, {"teacher_id": olga, "s_daty": PO_DATU,
                         "po_datu": S_DATY, "prichina": "болезнь"})[0] == 400
    assert _post(adres, {"teacher_id": olga, "s_daty": S_DATY,
                         "po_datu": PO_DATU, "prichina": "грипп"})[0] == 400
    assert _post(adres, {"teacher_id": 99999, "s_daty": S_DATY,
                         "po_datu": PO_DATU, "prichina": "болезнь"})[0] == 404
    assert _post(adres, {"s_daty": S_DATY, "po_datu": PO_DATU,
                         "prichina": "болезнь"})[0] == 400


def test_dver_ne_puskaet_prepoda_i_gostya(server_s_bazoj):
    telo = {"teacher_id": server_s_bazoj["olga"], "s_daty": S_DATY,
            "po_datu": PO_DATU, "prichina": "болезнь"}
    assert _post(server_s_bazoj["adres"], telo, rol_cheloveka="prepod")[0] == 403
    zapros = urllib.request.Request(
        server_s_bazoj["adres"] + "/api/otsutstvie",
        data=json.dumps(telo).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        urllib.request.urlopen(zapros)
        assert False, "дверь пустила человека без куки"
    except urllib.error.HTTPError as oshibka:
        assert oshibka.code == 403


def test_otmetku_mozhno_snyat(server_s_bazoj):
    adres = server_s_bazoj["adres"]
    _, otvet = _post(adres, {"teacher_id": server_s_bazoj["olga"], "s_daty": S_DATY,
                             "po_datu": PO_DATU, "prichina": "болезнь"})
    assert _post(adres, {"snyat": otvet["id"]})[0] == 200
    assert _post(adres, {"snyat": otvet["id"]})[0] == 404
    assert karkas.otsutstvuyushchie_na_datu(
        connect(server_s_bazoj["put"]), "2026-10-07") == frozenset()


# ─────────────────────────────────────────────────────────── часть 3 · ВИДНО


def test_v_zhurnale_dvenadcat_kletok_osobogo_vida(server_s_bazoj):
    """Критерий готовности, дословно: «в журнале преподавателей 12 клеток особого вида»."""
    _post(server_s_bazoj["adres"], {"teacher_id": server_s_bazoj["olga"],
                                    "s_daty": S_DATY, "po_datu": PO_DATU,
                                    "prichina": "болезнь"})
    html = _stranica(server_s_bazoj["adres"])
    kletki = re.findall(r'class="ist-otsut ots-den"[^>]*data-den="(\d{4}-\d\d-\d\d)"', html)
    assert sorted(kletki) == _dni_perioda()


def test_kletka_proshedshego_dnya_ne_krestik_i_ne_pustota(server_s_bazoj):
    """Три состояния, а не два: `✕` «не был», `О` «отмеченный период», пусто «не отмечено»."""
    ponedelnik = _proshedshij_ponedelnik()
    c = connect(server_s_bazoj["put"])
    c.execute("insert into sessions (held_on, kind) values (?, 'обычное')", (ponedelnik,))
    c.commit()
    _post(server_s_bazoj["adres"], {"teacher_id": server_s_bazoj["olga"],
                                    "s_daty": ponedelnik, "po_datu": ponedelnik,
                                    "prichina": "болезнь"})
    html = _stranica(server_s_bazoj["adres"])
    kletka = re.search(
        r'<td class="ist-kl ist-otsut" title="([^"]*)" data-den="%s" data-vid="prep" '
        r'data-kto="%d"' % (ponedelnik, server_s_bazoj["olga"]), html)
    assert kletka, "клетка дня периода обязана быть своего вида, а не крестиком"
    assert "отсутствует" in kletka.group(1) and "болезнь" in kletka.group(1)


def test_deti_ne_udalyayutsya_a_nazvany_spiskom(server_s_bazoj):
    """Задание §1: не удалять молча, а показать «эти дети остались без принимающего»."""
    _post(server_s_bazoj["adres"], {"teacher_id": server_s_bazoj["olga"],
                                    "s_daty": S_DATY, "po_datu": PO_DATU,
                                    "prichina": "болезнь"})
    html = _stranica(server_s_bazoj["adres"])
    stroka = re.search(r"остались без принимающего: (\d+)</b> — ([^<]*)", html)
    assert stroka, "список детей без принимающего обязан стоять на странице"
    assert int(stroka.group(1)) == 2
    assert "Агаркова Ирина" in stroka.group(2) and "Фефелов Иван" in stroka.group(2)
    c = connect(server_s_bazoj["put"])
    zhivyh = c.execute(
        "select count(*) from enrollment where teacher_id = ? and valid_to = ?",
        (server_s_bazoj["olga"], config.OPEN_END_DATE)).fetchone()[0]
    assert zhivyh == 4, "закрепления не удаляются — период кончится, а они верны"


def test_knopki_snyat_u_neorganizatora_net(server_s_bazoj):
    """🔴 НАЙДЕНО ВЕРИФИКАТОРОМ, А НЕ ЧТЕНИЕМ, И ПОТОМУ СТОРОЖИТСЯ ТЕСТОМ.

    Форма отметки пряталась правильно, а кнопка «снять» рисовалась ВСЕМ: под ролью
    `prepod` их было три на три периода. Дверь нажатие отбивает (403, тест ниже),
    так что данные не пострадали бы никогда, — но орган правки, показанный тому,
    кто править не может, обещает действие, которого не будет.
    """
    for nomer in range(3):
        _post(server_s_bazoj["adres"], {
            "teacher_id": server_s_bazoj["olga"],
            "s_daty": "2026-1%d-01" % nomer, "po_datu": "2026-1%d-02" % nomer,
            "prichina": "болезнь"})
    u_organizatora = _stranica(server_s_bazoj["adres"])
    assert u_organizatora.count('class="ots-snyat"') == 3
    u_prepoda = _stranica(server_s_bazoj["adres"], rol_cheloveka="prepod")
    assert u_prepoda.count('class="ots-snyat"') == 0
    assert "ots-zapis" in u_prepoda, "сами отметки преподаватель видеть обязан"


def test_formy_u_neorganizatora_net(server_s_bazoj):
    _post(server_s_bazoj["adres"], {"teacher_id": server_s_bazoj["olga"],
                                    "s_daty": S_DATY, "po_datu": PO_DATU,
                                    "prichina": "болезнь"})
    assert 'id="ots-forma"' in _stranica(server_s_bazoj["adres"])
    u_prepoda = _stranica(server_s_bazoj["adres"], rol_cheloveka="prepod")
    assert 'id="ots-forma"' not in u_prepoda
    assert "ots-den" in u_prepoda, "видеть отметку преподаватель обязан, править — нет"


# ────────────────────────────────────────────────────────── часть 4 · ДЕЙСТВУЕТ


def _spisok_prinimayushchih(kt, slot, tekushchij=None):
    return [x["name"] for x in shkolniki.prihodyashchie_v_slot(kt, slot, tekushchij)]


#: 🔴 ДЕНЬ ПЕРИОДА, КОТОРЫЙ НЕ ЯВЛЯЕТСЯ ДНЁМ ЗАНЯТИЯ, — ЭТО НЕ ПОЛОВИНА ПРОВЕРКИ,
#: А ЕЁ ДРУГОЙ ОТВЕТ, И РАЗНИЦУ НАДО НАЗВАТЬ, А НЕ ЗАМАЗАТЬ. Занятия идут по
#: понедельникам и четвергам (`migrations/003`), поэтому из двенадцати дней
#: 01–12.10 занятий четыре. В остальные восемь список принимающих ПУСТ у всех —
#: `slot_of` отвечает `None`, и колонки не существует вовсе. Утверждение «её нет в
#: списке» верно во все двенадцать дней; утверждение «сосед есть» проверяется там,
#: где список вообще бывает непуст, — иначе зелёный тест не отличал бы работающий
#: отбор от пустой школы.
def _est_zanyatie(den: str) -> bool:
    from core.services.sostav_na_den import slot_of

    return slot_of(den) is not None


@pytest.mark.parametrize("den", _dni_perioda())
def test_na_zanyatii_eyo_net_v_spiske(baza, den):
    """Версия распределения «по занятию»: двенадцать дней, двенадцать проверок."""
    karkas.otmetit_otsutstvie(baza["c"], baza["olga"], S_DATY, PO_DATU, "болезнь")
    baza["c"].commit()
    kt = karkas.sobrat_kontekst("admin", den=den, baza=baza["put"])
    slot = kt.DNI["den"][1]
    assert "Ольга Рыжая" not in _spisok_prinimayushchih(kt, slot, baza["olga"])
    if _est_zanyatie(den):
        assert "Пётр Соседний" in _spisok_prinimayushchih(kt, slot)


@pytest.mark.parametrize("den", _dni_perioda())
def test_v_postoyannom_eyo_net_v_spiske(baza, den, monkeypatch):
    """Версия «постоянное»: тот же вопрос к тем же двенадцати дням.

    Постоянный экран своей даты не имеет — он показывает БЛИЖАЙШИЕ пн и чт. Чтобы
    спросить его про 3 октября, часам приходится сказать, что страница открывается
    на 3 октября; сам отбор при этом не подменяется ничем.
    """
    karkas.otmetit_otsutstvie(baza["c"], baza["olga"], S_DATY, PO_DATU, "болезнь")
    baza["c"].commit()
    monkeypatch.setattr(karkas, "blizhajshij_den", lambda weekday, ot=None: den)
    kt = karkas.sobrat_kontekst("admin", den=None, baza=baza["put"])
    for slot in (1, 2):
        assert "Ольга Рыжая" not in _spisok_prinimayushchih(kt, slot, baza["olga"])
        assert "Пётр Соседний" in _spisok_prinimayushchih(kt, slot)


def test_vne_perioda_ona_na_meste(baza):
    """Отрицательная половина: без неё тест выше зелен и у пустой школы.

    День взят ПЕРВЫЙ ЗАНЯТИЙНЫЙ после периода — четверг 15.10. Тринадцатое —
    вторник, и списка принимающих в этот день нет ни у кого: на нём проверка
    «она вернулась» была бы зелёной и при начисто сломанном отборе.
    """
    karkas.otmetit_otsutstvie(baza["c"], baza["olga"], S_DATY, PO_DATU, "болезнь")
    baza["c"].commit()
    assert _est_zanyatie("2026-10-15"), "проверять надо на дне, у которого есть слот"
    kt = karkas.sobrat_kontekst("admin", den="2026-10-15", baza=baza["put"])
    assert "Ольга Рыжая" in _spisok_prinimayushchih(kt, kt.DNI["den"][1])


def test_pole_nazyvaet_prichinu_a_ne_molchit(baza):
    """Поле не показывает отсутствующего выбранным — и не врёт, что ребёнок ничей."""
    karkas.otmetit_otsutstvie(baza["c"], baza["olga"], S_DATY, PO_DATU, "болезнь")
    baza["c"].commit()
    kt = karkas.sobrat_kontekst("admin", den="2026-10-01", baza=baza["put"])
    ryad = {"id": baza["deti"][0], "teacher_id": baza["olga"]}
    razmetka = shkolniki.vybor_prepoda(kt, ryad, kt.DNI["den"][1], "Ольга Рыжая")
    assert "принимающий отсутствует" in razmetka
    assert 'value=""  selected' in razmetka.replace(" selected", "  selected", 1) \
        or 'value="" selected' in razmetka
    assert ">Ольга Рыжая<" not in razmetka


# ─────────────────────────────────────────── часть 5 · ПЕРЕЖИВАЕТ ПЕРЕЗАГРУЗКУ


def test_otmetka_perezhivaet_perezapusk_servera(baza):
    """Сервер поднимается, отмечает, умирает; поднимается заново — отметка на месте."""
    def podnyat():
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        httpd.db_path = str(baza["put"])  # type: ignore[attr-defined]
        potok = threading.Thread(target=httpd.serve_forever, daemon=True)
        potok.start()
        return httpd, potok, "http://127.0.0.1:%d" % httpd.server_address[1]

    httpd, potok, adres = podnyat()
    try:
        kod, _ = _post(adres, {"teacher_id": baza["olga"], "s_daty": S_DATY,
                               "po_datu": PO_DATU, "prichina": "болезнь"})
        assert kod == 200
    finally:
        httpd.shutdown(); httpd.server_close(); potok.join()

    httpd, potok, adres = podnyat()
    try:
        html = _stranica(adres)
        assert len(re.findall(r'class="ist-otsut ots-den"', html)) == DNEJ_V_PERIODE
        kt = karkas.sobrat_kontekst("admin", den="2026-10-07", baza=baza["put"])
        assert "Ольга Рыжая" not in _spisok_prinimayushchih(kt, kt.DNI["den"][1],
                                                            baza["olga"])
    finally:
        httpd.shutdown(); httpd.server_close(); potok.join()
