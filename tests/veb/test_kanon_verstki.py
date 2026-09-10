"""The layout canon inside the ordinary test run.

`tools/gejt_verstki.py` judges the RENDER of the four pages by hand.  A gate that
only runs by hand runs on the day someone remembers it, so this file puts the same
judgement into `pytest tests/veb` -- and adds the two things the hand-run tool does
not cover:

  * **The tab it names is the tab it measures.**  The tool selects `#p-rasp` for the
    row «принимающим».  `#p-rasp` is the PAGE radio and is already `checked` on
    `/raspredelenie`; the tab radio is `#t-prep`.  Measured at 1440x900: `t-shk` has
    178 leaf elements, `t-prep` has 72, and the tool printed 178 for both rows -- two
    of its four named pages were the same page.  `tools/` lies outside the zone of
    the заход that wrote this file, so the fix lives here, where the zone allows it,
    and the tool's own defect is filed in `## ВОПРОСЫ` of
    `zhurnal/2026-09-02_spetsmat-bot/kod_kanon-verstki.md`.
  * **The owner's clause [F11]: every pupil of a group fits on ONE screen.**  That is
    a question about HEIGHT, and all three questions of the tool are about width.

🔴 THE NUMBER OF PUPILS IS NEVER WRITTEN DOWN HERE.  The owner's benchmark is «25
in group В», and 25 is what the live base happens to hold today; a constant would
turn the day the school gains a pupil into a red test instead of a red page.  The
count is read off the render and printed with the verdict.

WHAT THIS FILE DOES NOT CHECK, said out loud so a green run is not mistaken for a
good page: colour, contrast, readability, font substitution on a machine without the
project fonts, mobile widths, print, motion, screen readers, and any truncation done
on the SERVER (a string already shortened in Python arrives short in the markup and
overflows nothing).  It judges geometry at one viewport.
"""

from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api",
                    reason="гейт вёрстки судит по рендеру: без браузера судить нечем")

from playwright.sync_api import sync_playwright  # noqa: E402

from tools.gejt_verstki import (  # noqa: E402
    ETALON,
    ZAMER,
    kuka,
    podnyat_server,
    zhivaya_baza,
)

# The four pages of the criterion, each with the id of the radio that actually opens
# it.  `p-*` are the page radios of the frame, `t-*` the tab radios of the
# distribution section -- mixing the two families is exactly the hole described above.
STRANICY = [
    ("школьникам", "/raspredelenie", "t-shk"),
    ("принимающим", "/raspredelenie", "t-prep"),
    ("страница группы", "/glavnaya", "p-start"),
    ("кондуит", "/glavnaya", "p-kond"),
]

# The owner's benchmark tab: the biggest group of the three.
GRUPPA = ("группа В", "/raspredelenie", "t-В")

# Everything the browser is asked about the group screen in one go.
# 🔴 THE PUPILS ARE THE LEFT COLUMN ONLY.  The group tab holds two columns of
# `.para` rows: the pupils on the left, the accepting teachers' cards (`.kol-pr`)
# on the right.  Counting every `.para` gives 25 on group В and looks like the
# owner's benchmark of 25 by pure coincidence -- it is 19 pupils plus 6 cards.
# A number that is right for the wrong reason is worse than a wrong one: it stops
# being right the day a teacher leaves, and nobody knows why.
ZAMER_GRUPPY = """
() => {
  const sec = [...document.querySelectorAll('.vid')]
      .find(s => s.getBoundingClientRect().height > 1);
  if (!sec) return null;
  const shk = [...sec.querySelectorAll('.kol:not(.kol-pr) .para')];
  const nizy = shk.map(s => s.getBoundingClientRect().bottom);
  return {razdel: sec.id,
          shkolnikov: shk.length,
          kartochek: sec.querySelectorAll('.kol-pr .para').length,
          niz: nizy.length ? Math.round(Math.max(...nizy)) : 0,
          okno: window.innerHeight};
}
"""

# 🔴 THREE BREAKAGES, ONE PER DETECTOR, AND NOT ONE COMBINED ONE.  The tool's own
# `--slomat` hangs a 2400px block off the body and calls the gate proven: the run goes
# red, the self-test prints «рычаг работает» and returns 0.  Measured by the verifier
# of this заход, 10.09: that breakage reddens the SCROLL number only -- clipping and
# wrapping both stay at 0 on all four pages.  Two detectors out of three were being
# certified by a test that never touched them, which is the exact shape of a silent
# gate: it is not the gate that is silent, it is the proof of the gate.
# Each entry says WHERE it breaks as well as HOW: the wrap detector needs a page that
# carries a text leaf with slack around it, and «страница группы» has two of them
# («9 КЛ · школа №179», «В 303 · Д 302 · Н 20»), while the distribution rows are
# already snug and answer an indent with a scrollbar instead of a second line.
SLOMAT = {
    # Squeeze every visible text leaf until its own text cannot fit inside it.
    "obrezka": ("/raspredelenie", "t-shk", """
() => {
  [...document.querySelectorAll('body *')].filter(el => {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return false;
    const t = (el.textContent || '').trim();
    if (!t) return false;
    return ![...el.children].some(c => (c.textContent || '').trim().length > 0);
  }).forEach(el => { el.style.width = '12px'; el.style.overflow = 'hidden'; });
}
"""),
    # Push the first line of every text leaf sideways so that a word that fitted on one
    # line no longer does -- a wrap the available width did not require.
    "perenos": ("/glavnaya", "p-start", """
() => {
  [...document.querySelectorAll('p, span, td, li, label')].forEach(el => {
    el.style.textIndent = '90%';
  });
}
"""),
    # The tool's own breakage, kept as it is: a block wider than the window.
    "skroll": ("/raspredelenie", "t-shk", """
() => {
  const d = document.createElement('div');
  d.style.width = '2400px'; d.style.height = '1px';
  document.body.appendChild(d);
}
"""),
}


def _otkryt(page, baza_url, put, radio):
    page.goto(baza_url + put, wait_until="networkidle", timeout=20000)
    if page.query_selector(f"#{radio}"):
        page.evaluate(f"document.getElementById('{radio}').checked = true")
        page.wait_for_timeout(150)
    else:                                   # pragma: no cover -- a renamed radio
        pytest.fail(f"радиокнопки #{radio} нет на {put}: гейт измерил бы не ту вкладку")


@pytest.fixture(scope="module")
def zamer():
    """One server, one browser, every measurement this file makes.

    Booting Chromium costs about a second and the pages are read-only, so the whole
    module shares one run; a per-test browser would triple the price of the suite for
    no extra confidence.
    """
    db = zhivaya_baza()
    httpd, conn, potok, url = podnyat_server(db)
    itog = {"stranicy": {}, "kanon": {}, "gruppa": None, "slomannaya": {}, "gost": None}
    try:
        with sync_playwright() as pw:
            brauzer = pw.chromium.launch()
            ctx = brauzer.new_context(viewport=ETALON)
            c = kuka()
            ctx.add_cookies([{**c, "url": url}])
            page = ctx.new_page()

            for imya, put, radio in STRANICY:
                _otkryt(page, url, put, radio)
                itog["stranicy"][imya] = page.evaluate(ZAMER)
                itog["kanon"][imya] = page.evaluate("""
                    () => [...document.querySelectorAll('.kolonka')].map(el => {
                      const s = getComputedStyle(el);
                      return {vyravnivanie: s.textAlign, shirina: s.width,
                              zadana: el.style.width || '',
                              put: el.className};
                    })""")

            imya, put, radio = GRUPPA
            _otkryt(page, url, put, radio)
            itog["gruppa"] = page.evaluate(ZAMER_GRUPPY)

            # 🔴 THE SAME PAGE, THE OTHER ROLE.  Everything above is measured with an
            # organiser cookie, because the conduit tab does not exist without one --
            # and an organiser sees the teacher's name inside a `<select>`, which
            # sizes itself to its options.  A guest sees the same name as plain text
            # in a column frozen at `flex:0 0 9.6rem`, and that is a different render
            # of the same markup.  Measuring one role and reporting «the page» is how
            # a gate stays green over a page most of its visitors see broken.
            gost_ctx = brauzer.new_context(viewport=ETALON)
            gost = gost_ctx.new_page()
            _otkryt(gost, url, "/raspredelenie", "t-shk")
            itog["gost"] = gost.evaluate(ZAMER)
            gost_ctx.close()

            # The lever must be provable per DETECTOR, not merely present: each of the
            # three questions is broken on its own page load and must go red by itself.
            for vopros, (put, radio, skript) in SLOMAT.items():
                _otkryt(page, url, put, radio)
                page.evaluate(skript)
                page.wait_for_timeout(120)
                itog["slomannaya"][vopros] = page.evaluate(ZAMER)

            brauzer.close()
    finally:
        httpd.shutdown()
        httpd.server_close()
        potok.join()
        conn.close()
    return itog


def test_ohvat_ne_nol(zamer):
    """Ноль осмотренных страниц при живом сервере — красный, а не зелёный."""
    izmereno = sum(1 for z in zamer["stranicy"].values() if z)
    print(f"\nОХВАТ: проверено {izmereno} страниц из {len(STRANICY)}; "
          f"осмотрено элементов {sum(z['osmotreno'] for z in zamer['stranicy'].values() if z)}")
    assert izmereno == len(STRANICY)
    assert all(z["osmotreno"] > 0 for z in zamer["stranicy"].values())


@pytest.mark.parametrize("imya", [s[0] for s in STRANICY])
def test_tri_voprosa_kanona(zamer, imya):
    """Обрезка, лишний перенос, горизонтальный скролл — все три нули."""
    z = zamer["stranicy"][imya]
    assert z, f"страница «{imya}» не измерена"
    print(f"\n{imya}: обрезка {len(z['obrezka'])}, переносы {len(z['perenos'])}, "
          f"скролл {z['skroll']} px, осмотрено {z['osmotreno']}")
    assert z["skroll"] == 0, f"«{imya}»: документ шире окна на {z['skroll']} px"
    assert not z["obrezka"], (
        f"«{imya}»: текст обрезан рамкой — " +
        "; ".join(f"{d['put']} «{d['tekst']}» надо {d['nado']} есть {d['est']}"
                  for d in z["obrezka"][:5]))
    assert not z["perenos"], (
        f"«{imya}»: строка встала в две высоты там, где хватало одной — " +
        "; ".join(f"{d['put']} «{d['tekst']}» надо {d['nuzhno']} есть {d['est']}"
                  for d in z["perenos"][:5]))


@pytest.mark.parametrize("vopros", list(SLOMAT))
def test_kazhdyj_detektor_krasneet_otdelno(zamer, vopros):
    """🔴 Молчащий гейт хуже отсутствующего — и доказывать это надо по детекторам.

    Страница ломается тремя способами, по одному на вопрос, и каждый обязан покрасить
    СВОЁ число. Общая поломка, красящая одно число из трёх, аттестует два детектора,
    которых она не касалась: находка верификатора этого захода 10.09 — штатный
    `--slomat` инструмента даёт скролл 960 px на всех четырёх страницах при обрезке 0
    и переносах 0.
    """
    z = zamer["slomannaya"][vopros]
    chislo = z["skroll"] if vopros == "skroll" else len(z[vopros])
    print(f"\nСАМОПРОВЕРКА · {vopros}: обрезка {len(z['obrezka'])}, "
          f"переносы {len(z['perenos'])}, скролл {z['skroll']} px")
    assert chislo, (f"страницу сломали именно по вопросу «{vopros}», а этот детектор "
                    "остался зелёным")


@pytest.mark.xfail(strict=True, reason=(
    "ЗАМЕРЕНО, А НЕ ПРЕДПОЛОЖЕНО: клауза владельца [F11] сегодня НЕ выполняется. "
    "19 школьников группы В при шаге строки 1.6rem кончаются на 1189 px при окне "
    "900 px — треть группы под сгибом. Чинится это перевёрсткой самой вкладки "
    "(veb/razdely/**), а она — зона захода verstka-raspredeleniya (P3), не этого. "
    "Здесь стоит РЫЧАГ, а не заплатка: строгий xfail держит дефект записанным и "
    "посчитанным (`xfailed: 1` в каждом прогоне), и в тот день, когда P3 починит "
    "страницу, тест покраснеет как XPASS. Это красное значит ровно одно — «сними "
    "маркер», и это единственный способ, которым маркер не переживёт дефект."))
def test_gruppa_pomeshchaetsya_na_odin_ekran(zamer):
    """Клауза владельца [F11]: все школьники группы — на одном экране.

    Число школьников СЧИТАЕТСЯ ПО РЕНДЕРУ и печатается: в группе В их сегодня 19,
    и это НЕ эталонные 25 владельца — 25 получается, только если сложить их с
    шестью карточками принимающих в соседней колонке. Ни одно из этих чисел здесь
    не написано константой: школа вырастет, и красной обязана стать страница, а не
    этот файл.
    """
    g = zamer["gruppa"]
    assert g and g["shkolnikov"] > 0, "вкладка группы пуста: судить нечего"
    print(f"\nГРУППА В · школьников {g['shkolnikov']}, карточек принимающих "
          f"{g['kartochek']} · последняя строка школьника на {g['niz']} px "
          f"при окне {g['okno']} px")
    assert g["niz"] <= g["okno"], (
        f"группа не помещается на экран: {g['shkolnikov']} школьников, последняя "
        f"строка кончается на {g['niz']} px при окне {g['okno']} px")


# 🔴 МАРКЕР СНЯТ ОРКЕСТРАТОРОМ 10.09 в 02:35, И ЭТО ТО САМОЕ ДЕЙСТВИЕ, КОТОРОЕ ОН ПРЕДПИСЫВАЛ.
# Строгий xfail, поставленный позицией kanon-verstki, держал дефект «гостю рамка режет
# имена принимающих» записанным и посчитанным: 36 элементов на здешней базе, 48 на боевом
# сервере. В его же тексте стояло условие снятия: «в тот день, когда P3 починит страницу,
# тест покраснеет как XPASS. Это красное значит ровно одно — сними маркер».
# P3 (verstka-raspredeleniya) починила: общая сетка колонок в veb/razdely/verstka_stili.py
# вместо замороженного flex:0 0 9.6rem. Замер оркестратора после влития e1aa86c:
#   ГОСТЬ · /raspredelenie: обрезка 0, переносы 0, скролл 0 px, осмотрено 167
# Маркер пережил бы дефект ровно на один прогон — и не пережил.
def test_gost_vidit_to_zhe_chto_organizator(zamer):
    """Гость — тоже роль, и страницу он видит ЧАЩЕ организатора.

    Гейт `tools/gejt_verstki.py` ходит по сайту только с куки организатора: без неё
    нет вкладки кондуита. Цена — целый режим страницы, ни разу не измеренный.
    """
    z = zamer["gost"]
    print(f"\nГОСТЬ · /raspredelenie: обрезка {len(z['obrezka'])}, "
          f"переносы {len(z['perenos'])}, скролл {z['skroll']} px, "
          f"осмотрено {z['osmotreno']}")
    for d in z["obrezka"][:3]:
        print(f"   ОБРЕЗКА · {d['put']} · «{d['tekst']}» · надо {d['nado']} есть {d['est']}")
    assert not z["obrezka"], f"гостю обрезано {len(z['obrezka'])} элементов"
    assert z["skroll"] == 0
    assert not z["perenos"]


@pytest.mark.parametrize("imya", [s[0] for s in STRANICY])
def test_klass_kanona_soblyudaetsya(zamer, imya):
    """Носит класс канона — обязан вести себя по канону.

    Сегодня разделы ещё не переведены на `.kolonka` (разметка `veb/razdely/**` —
    зона `verstka-raspredeleniya`), и проверка проходит по пустому множеству; это
    сказано вслух, а не спрятано. Рычагом она становится в тот момент, когда P3
    впервые напишет класс: выравнивание внутри колонки — только левое, ширина —
    от данных, а не заданная в разметке пикселями.
    """
    kolonki = zamer["kanon"][imya]
    print(f"\n{imya}: элементов с классом канона — {len(kolonki)}")
    for k in kolonki:
        assert k["vyravnivanie"] in ("left", "start"), (
            f"«{imya}»: {k['put']} носит класс канона, а выровнен по "
            f"{k['vyravnivanie']}")
        assert "px" not in k["zadana"], (
            f"«{imya}»: {k['put']} — ширина колонки задана в разметке ({k['zadana']}), "
            "а канон берёт её от самого длинного значения из базы")
