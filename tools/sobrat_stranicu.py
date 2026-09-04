#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-hand — зовётся при выкладке статики на GitHub Pages.
"""Собирает САМОДОСТАТОЧНУЮ статику по ТЗ 07_TZ-SAJT.md.

Три страницы, меню из трёх пунктов строкой сверху (§1: «может быть, наверху, чтобы
ничего не выезжало»). Текст занимает весь экран.

Данные вмораживаются на момент сборки: Pages отдаёт статику, ей не нужен ни сервер,
ни база, и чтение переживает выключенный ноутбук — в этом смысл разделения (§7).
"""
import html
import pathlib
import sqlite3
import sys

KOREN = pathlib.Path(__file__).resolve().parent.parent
DATA = KOREN / "data" / "spetsmat.db"
VYHOD = KOREN / "docs" / "index.html"
MAT = KOREN.parent / "materials" / "spetsmat-2026"
DATA_NA = "2026-09-05"
DATA_SLOVAMI = "5 сентября"


def e(s):
    return html.escape(str(s if s is not None else ""))


def sobrat():
    c = sqlite3.connect(DATA)
    c.row_factory = sqlite3.Row

    # 🔴 РАСПРЕДЕЛЕНИЕ ЗАВИСИТ ОТ ДНЯ. Занятия по четвергам и субботам, и кабинет
    # у группы в эти дни может быть РАЗНЫЙ. Поэтому строим оба дня сразу, а на
    # странице переключатель; по умолчанию открывается ближайший (в пятницу и
    # субботу — суббота, иначе четверг).
    DNI = {"cht": ("четверг", 1, "2026-09-05"), "sub": ("суббота", 2, "2026-09-06")}
    kabinety_dnya = {}
    for kl, (_, _, dat) in DNI.items():
        kabinety_dnya[kl] = {r["gruppa"]: r["kabinet"] for r in c.execute(
            "select gruppa, kabinet from kabinet_na_den where data = ?", (dat,))}
    kabinety = kabinety_dnya["cht"]
    gruppy = {r["kod"]: r["starshij"] for r in c.execute(
        "select kod, starshij from gruppy order by kod")}
    prep = {r["id"]: dict(r) for r in c.execute(
        "select id, name, gruppa from teachers where aktiven = 1")}

    def shkolniki(slot):
        return c.execute("""
            select s.id, s.surname, s.name, s.class, e.teacher_id
            from students s
            left join enrollment e
              on e.student_id = s.id and e.valid_to = '9999-12-31' and e.slot = ?
            where s.status is null or s.status <> 'left'
            order by s.surname, s.name
        """, (slot,)).fetchall()

    shk_dnya = {kl: shkolniki(sl) for kl, (_, sl, _) in DNI.items()}
    shk = shk_dnya["cht"]

    def gr_shk(r, pr=None):
        pr = pr or prep
        t_ = pr.get(r["teacher_id"])
        return t_["gruppa"] if t_ else None

    def kab_shk(r):
        return kabinety.get(gr_shk(r))

    def para_shk(r, kl, pokazat_kab=True):
        """Строка «школьник → его преподаватель»."""
        kab = kabinety_dnya[kl]
        t_ = prep.get(r["teacher_id"])
        g = gr_shk(r)
        hvost = ""
        if t_:
            hvost = e(t_["name"])
            if pokazat_kab and kab.get(g):
                hvost += f' <span class="kab">{e(kab.get(g))}</span>'
        else:
            hvost = "—"
        return (f'<div class="para" data-i="{e((r["surname"] + " " + r["name"]).lower())}">'
                f'<span class="kto"><b>{e(r["surname"])}</b> {e(r["name"])}</span>'
                f'<span class="komu">{hvost}</span></div>')

    def para_prep(x, kl, pokazat_gruppu=True):
        """Строка «преподаватель → его школьники».

        🔴 ТОЛЬКО ФАМИЛИИ школьников: с именами строка не влезает (замечание
        владельца 04.09). Группа и кабинет на вкладке ГРУППЫ не печатаются — там
        и так все из одной группы и одного кабинета, это шум.
        """
        kab = kabinety_dnya[kl]
        ego = sorted(r["surname"] for r in shk_dnya[kl] if r["teacher_id"] == x["id"])
        redko = ' <span class="redko">не всегда</span>' if x["name"] == "Ольга Рыжая" else ""
        metki = ""
        if pokazat_gruppu:
            if x["gruppa"]:
                metki += f' <span class="gr">{e(x["gruppa"])}</span>'
            if kab.get(x["gruppa"]):
                metki += f' <span class="kab">{e(kab.get(x["gruppa"]))}</span>'
        deti_html = ("".join(f'<span>{e(d)}</span>' for d in ego)
                     or '<span class="net">—</span>')
        return (f'<div class="para" data-i="{e(x["name"].lower())}">'
                f'<span class="kto"><b>{e(x["name"])}</b>{redko}{metki}</span>'
                f'<span class="komu deti">{deti_html}</span></div>')

    def vid_vse(kl):
        """Вкладка «все»: школьники двумя столбцами, каждому — его преподаватель."""
        deti = shk_dnya[kl]
        pol = (len(deti) + 1) // 2
        return ('<div class="dva">'
                f'<div class="kol">{"".join(para_shk(r, kl) for r in deti[:pol])}</div>'
                f'<div class="kol">{"".join(para_shk(r, kl) for r in deti[pol:])}</div></div>')

    def vid_prepodavateli(kl):
        """Отдельная вкладка преподавателей — чтобы преподаватель посмотрел на себя."""
        prepy = sorted(prep.values(), key=lambda x: x["name"])
        return f'<div class="odin">{"".join(para_prep(x, kl) for x in prepy)}</div>'

    def vkladka_gruppy(kod, kl):
        """Группа — ОДИН столбец: половина экрана пустой быть не должна.

        Группа и кабинет у каждой строки не печатаются: на вкладке группы они
        одинаковы у всех и стоят один раз в шапке.
        """
        star = gruppy[kod]
        kab = kabinety_dnya[kl].get(kod)
        deti = [r for r in shk_dnya[kl] if gr_shk(r) == kod]
        svoi = sorted((x for x in prep.values() if x["gruppa"] == kod), key=lambda x: x["name"])
        shapka = (f'<p class="shapka"><b>{e(star)}</b> · '
                  + (f'кабинет <span class="kab">{e(kab)}</span>' if kab else '<span class="net">кабинет не назначен</span>')
                  + f' · преподавателей {len(svoi)} · школьников {len(deti)}</p>')
        return (shapka + '<div class="dva">'
                + f'<div class="kol">{"".join(para_shk(r, kl, pokazat_kab=False) for r in deti)}</div>'
                + f'<div class="kol kol-pr">{"".join(para_prep(x, kl, pokazat_gruppu=False) for x in svoi)}</div>'
                + '</div>')

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

    l9 = [f for _, _, vs in L9 for _, f in vs if est("listki", f)]
    l8 = [f for _, _, f in L8_PERVOE + L8_VTOROE if est("listki-8kl", f)]

    zhdut = [r for r in shk if r["teacher_id"] not in prep]

    VYHOD.write_text(f"""<!doctype html>
<html lang="ru">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Спецмат · 9 класс</title>
<style>
:root{{--bg:#fbfaf6;--panel:#fffdf8;--text:#211f1b;--muted:#726c60;--rule:#e7e2d6;
  --accent:#2f6e8e;--accent-soft:#e8f0f4;--warm:#c9743a;--faint:#b7ae9c;--chip:#e7e0d2;
  --sans:"Source Sans 3",system-ui,-apple-system,"Helvetica Neue",Arial,sans-serif;
  --serif:"Source Serif 4",Georgia,"Times New Roman",serif}}
@media(prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#1b1e22;--panel:#23272c;
  --text:#dcd8d0;--muted:#9a948a;--rule:#343a41;--accent:#7fb6d2;--accent-soft:#22333d;
  --warm:#e0946a;--faint:#6b6f75;--chip:#333a41}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--text);font-family:var(--serif);font-size:20px}}
/* Меню — строка сверху: три пункта помещаются, ничего выезжать не должно (§1). */
.menu{{position:sticky;top:0;z-index:40;display:flex;gap:.3rem;align-items:baseline;
  padding:.9rem 3rem;background:var(--panel);border-bottom:1px solid var(--rule);
  font-family:var(--sans);flex-wrap:wrap}}
.menu .im{{font-weight:600;font-size:1.05rem;margin-right:1.6rem;white-space:nowrap}}
.menu label{{cursor:pointer;font-weight:600;font-size:1.05rem;color:var(--muted);
  padding:.35em 1rem;border-radius:8px}}
.menu label:hover{{color:var(--text);background:var(--accent-soft)}}
.holst{{padding:2.2rem 3rem 4rem;max-width:none}}
h1{{font-family:var(--sans);font-size:2.5rem;font-weight:600;letter-spacing:-.02em;margin:0 0 .1em}}
.data{{color:var(--muted);font-family:var(--sans);font-size:1rem;margin:0 0 1.6rem}}
.oblozhka p{{font-size:1.3rem;line-height:1.5;max-width:52em;margin:0 0 .8em}}
.raspisanie{{border:1px solid var(--rule);border-radius:10px;padding:1.1rem 1.4rem;
  margin:1.6rem 0 0;background:var(--panel);max-width:52em}}
.zag2{{font-family:var(--sans);font-size:.85rem;font-weight:600;letter-spacing:.09em;
  text-transform:uppercase;color:var(--faint);margin:0 0 .5em}}
.str,.vid{{display:none}}
#p-start:checked~#s-start,#p-list:checked~#s-list,#p-rasp:checked~#s-rasp{{display:block}}
#p-start:checked~.menu label[for=p-start],#p-list:checked~.menu label[for=p-list],
#p-rasp:checked~.menu label[for=p-rasp]{{color:var(--accent);background:var(--accent-soft)}}
input.rd{{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none}}
.tabbar{{display:flex;gap:.25rem;border-bottom:2px solid var(--rule);margin:0 0 1.8rem;flex-wrap:wrap}}
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
.kab{{font-family:var(--sans);font-weight:600;background:var(--chip);border-radius:7px;
  padding:.1em .55em;white-space:nowrap}}
.gr{{font-family:var(--sans);font-weight:600;color:var(--accent)}}
.pr{{white-space:nowrap}}
.deti{{font-size:.95rem;color:var(--muted);line-height:1.45}}
.ch{{font-family:var(--sans);color:var(--muted);text-align:right;white-space:nowrap}}
.net{{color:var(--warm);font-family:var(--sans);font-size:.95rem}}
.redko{{font-family:var(--sans);font-size:.85rem;color:var(--warm)}}
.shapka{{font-family:var(--sans);font-size:1.15rem;color:var(--muted);margin:0 0 1.4rem}}
.zhdut{{border:1px solid var(--warm);border-radius:10px;padding:1rem 1.3rem;margin:0 0 1.8rem}}
.zhdut .zag2{{color:var(--warm)}}
.poisk{{width:100%;max-width:640px;padding:.65em .9em;font:inherit;font-size:1.1rem;
  border:1px solid var(--rule);border-radius:9px;background:var(--panel);color:var(--text);margin:0 0 1.5rem}}
.poisk:focus{{outline:none;border-color:var(--accent)}}
.podskazki{{position:relative;max-width:640px}}
.spisok{{position:absolute;left:0;right:0;top:3.1rem;z-index:20;background:var(--panel);
  border:1px solid var(--rule);border-radius:0 0 9px 9px;max-height:18rem;overflow:auto}}
.spisok div{{padding:.5em .9em;cursor:pointer}}
.spisok div:hover{{background:var(--accent-soft);color:var(--accent)}}
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
.para .kto{{flex:0 0 auto;min-width:0}}
.para .komu{{margin-left:auto;text-align:right;color:var(--muted);font-family:var(--sans);
  font-size:1.05rem}}
.para .komu.deti{{white-space:normal;text-align:right}}
.para .komu.deti span{{display:inline-block;margin-left:.55rem}}
.kol-pr .para{{padding:.45rem 0}}
.kol-pr .komu.deti{{font-size:1rem}}
.para.skryt{{display:none}}
/* Переключатель дня — сверху справа, рядом с заголовком. */
.shapka-str{{display:flex;align-items:baseline;gap:1.5rem;flex-wrap:wrap;margin:0 0 1rem}}
.dni{{display:flex;gap:.25rem;margin-left:auto}}
.dni label{{cursor:pointer;font-family:var(--sans);font-weight:600;font-size:1.05rem;
  color:var(--muted);padding:.35em 1.1rem;border:1px solid var(--rule);border-radius:9px}}
.dni label:hover{{color:var(--text)}}
#d-cht:checked~.holst .dni label[for=d-cht],
#d-sub:checked~.holst .dni label[for=d-sub],
#d-cht:checked~#s-rasp .dni label[for=d-cht],
#d-sub:checked~#s-rasp .dni label[for=d-sub]{{color:var(--accent);border-color:var(--accent);
  background:var(--accent-soft)}}
.den{{display:none}}
#d-cht:checked~#s-rasp .den-cht,#d-sub:checked~#s-rasp .den-sub{{display:block}}
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
</style>

<input class="rd" type="radio" name="den" id="d-cht" checked>
<input class="rd" type="radio" name="den" id="d-sub">
<input class="rd" type="radio" name="str" id="p-start" checked>
<input class="rd" type="radio" name="str" id="p-list">
<input class="rd" type="radio" name="str" id="p-rasp">
<nav class="menu">
  <label class="im" for="p-start">Спецмат 9 класс</label>
  <label for="p-list">Листки</label>
  <label for="p-rasp">Распределение</label>
</nav>

<section class="str holst" id="s-start">
  <div class="oblozhka">
    <h1>Спецмат · 9 класс</h1>
    <p class="data">9К и 9Л · распределение на {DATA_SLOVAMI}</p>
    <p>Кто у кого занимается и в каком кабинете, и все листки — этого года и прошлого.</p>
    <div class="raspisanie">
      <div class="zag2">Расписание</div>
      <div>Занятия по четвергам и субботам. <span class="net">время пока не указано</span></div>
    </div>
    <div class="podskazki" style="margin-top:2rem">
      <input class="poisk" id="poisk" placeholder="Найти себя — фамилия школьника или имя преподавателя" autocomplete="off">
      <div class="spisok" id="spisok" hidden></div>
      <div id="nashli"></div>
    </div>
  </div>
</section>

<section class="str holst" id="s-list">
  <h1>Листки</h1>
  <input class="rd" type="radio" name="lst" id="l-9" checked>
  <input class="rd" type="radio" name="lst" id="l-8">
  <div class="tabbar"><label for="l-9">9 класс</label><label for="l-8">8 класс</label></div>
  <section class="vid" id="w-9">
    <table class="listki"><tbody>{stroki_9()}</tbody></table>
  </section>
  <section class="vid" id="w-8">
    <p class="polug">первое полугодие</p>
    <table class="listki"><tbody>{stroki_8(L8_PERVOE, "listki-8kl")}</tbody></table>
    <p class="polug">второе полугодие</p>
    <table class="listki"><tbody>{stroki_8(L8_VTOROE, "listki-8kl")}</tbody></table>
  </section>
</section>

<section class="str holst" id="s-rasp">
  <div class="shapka-str">
    <h1>Распределение</h1>
    <input class="poisk poisk-str" id="poisk-r" placeholder="Фамилия школьника или имя преподавателя" autocomplete="off">
    <div class="dni">
      <label for="d-cht">четверг</label><label for="d-sub">суббота</label>
    </div>
  </div>

  <input class="rd" type="radio" name="vk" id="t-shk" checked>
  <input class="rd" type="radio" name="vk" id="t-prep">
  <input class="rd" type="radio" name="vk" id="t-В">
  <input class="rd" type="radio" name="vk" id="t-Д">
  <input class="rd" type="radio" name="vk" id="t-Н">
  <div class="tabbar">
    <label for="t-shk">школьникам</label><label for="t-prep">преподавателям</label>
    <label for="t-В">В</label><label for="t-Д">Д</label><label for="t-Н">Н</label>
  </div>
  <section class="vid" id="v-shk">
    <div class="den den-cht">{vid_vse("cht")}</div>
    <div class="den den-sub">{vid_vse("sub")}</div>
  </section>
  <section class="vid" id="v-prep">
    <div class="den den-cht">{vid_prepodavateli("cht")}</div>
    <div class="den den-sub">{vid_prepodavateli("sub")}</div>
  </section>
  {"".join(f'<section class="vid" id="v-{k}">'
           f'<div class="den den-cht">{vkladka_gruppy(k, "cht")}</div>'
           f'<div class="den den-sub">{vkladka_gruppy(k, "sub")}</div></section>'
           for k in ("В", "Д", "Н"))}
</section>

<script>
// Поиск ищет и школьника, и преподавателя, подсказывает от двух букв: людей мало.
const IMENA = {[e(f'{r["surname"]} {r["name"]}') for r in shk] + [e(t["name"]) for t in prep.values()]!r};
// Что показать по найденному. Для школьника — к кому и куда идти; для
// преподавателя — его группа, старший, кабинет и сколько у него школьников.
const KOMU = {{{",".join(
  [f'"{e(r["surname"])} {e(r["name"])}":"{e(prep[r["teacher_id"]]["name"]) if r["teacher_id"] in prep else "—"} · группа {e(gr_shk(r) or "—")} · кабинет {e(kab_shk(r) or "не назначен")}"' for r in shk]
+ [f'"{e(t_["name"])}":"группа {e(t_["gruppa"] or "—")} · старший {e(gruppy.get(t_["gruppa"], "—"))} · кабинет {e(kabinety.get(t_["gruppa"]) or "не назначен")} · школьников {sum(1 for r in shk if r["teacher_id"] == t_["id"])}"' for t_ in prep.values()]
)}}};
const poisk=document.getElementById('poisk'),spisok=document.getElementById('spisok'),nashli=document.getElementById('nashli');
poisk.addEventListener('input',e=>{{
  const q=e.target.value.trim().toLowerCase(); nashli.innerHTML='';
  if(q.length<2){{spisok.hidden=true;return;}}
  const r=IMENA.filter(n=>n.toLowerCase().includes(q)).slice(0,8);
  spisok.innerHTML=r.map(n=>'<div>'+n+'</div>').join(''); spisok.hidden=!r.length;
}});
spisok.addEventListener('click',e=>{{
  if(e.target.tagName!=='DIV')return;
  const n=e.target.textContent; poisk.value=n; spisok.hidden=true;
  nashli.innerHTML = KOMU[n] ? '<p class="shapka" style="margin-top:1rem">'+n+' → '+KOMU[n]+'</p>' : '';
}});
document.addEventListener('click',e=>{{if(!e.target.closest('.podskazki'))spisok.hidden=true;}});

// Поиск на РАСПРЕДЕЛЕНИИ: прячет строки, не совпавшие с фамилией или именем.
// Работает разом во всех вкладках и в обоих днях — искать надо там, где смотришь.
const pr=document.getElementById('poisk-r');
pr.addEventListener('input',e=>{{
  const q=e.target.value.trim().toLowerCase();
  document.querySelectorAll('#s-rasp .para').forEach(d=>{{
    d.classList.toggle('skryt', !!q && !d.dataset.i.includes(q) &&
      !d.textContent.toLowerCase().includes(q));
  }});
}});
</script>
""", encoding="utf-8")
    print(f"собрано: {VYHOD}")
    print(f"  школьников {len(shk)} · преподавателей {len(prep)} · ждут назначения {len(zhdut)}")
    print(f"  группы: " + " · ".join(f"{k}→{kabinety.get(k,'—')}" for k in ("В","Д","Н")))
    print(f"  листки: 9кл {len(l9)} · 8кл {len(l8)}")
    return 0


if __name__ == "__main__":
    sys.exit(sobrat())
