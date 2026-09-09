#!/usr/bin/env python3
# TOOL-CONTRACT: called-by-code — rendered by `tools/sobrat_stranicu.sobrat_html`.
"""Extra layout rules for the three distribution pages, layered ON TOP of the
canon in `veb/obshchee/karkas.py`.

🔴 WHY THIS FILE EXISTS INSTEAD OF EDITING THE CANON. `karkas.py` is outside this
заход's zone (`veb/razdely/` `veb/static/` `tests/veb/` only, see `## КОНТРАКТ
ЗОНЫ`) — the previous заход `kanon-verstki` owns it, and "бери оттуда, своего не
изобретай" means REUSE its class names and custom properties, not that this заход
may edit the file that defines them. A `<style>` tag inside `<body>` is valid
HTML5 and browsers apply it exactly like one in `<head>`; `konduit.py` already
returns its own `stili(kt)` string for the same reason. `STILI` is emitted
EXACTLY ONCE, from `shkolniki.vid_vse()`, which the composition root calls
exactly once per page — duplicating it from `prepodavateli.py` or `gruppy.py` as
well would just repeat the same rules three times in the document.

🔴 EVERY SELECTOR HERE TARGETS AN EXISTING CANON CLASS. Nothing here invents a
new visual language; it only overrides the numbers (widths, alignment, spacing)
that the owner's 09.09 review named as wrong, and adds the one rule the canon is
missing outright (`.obychno` has no CSS at all in `karkas.py`).
"""
from __future__ import annotations

STILI = """
<style>
/* ── §3 «обычно у» — значок с подсказкой, а не голый текст встык с фамилией.
   Канон вообще не содержит правила `.obychno` — этот span рисовался неотделённым
   от фамилии. Разворачивается в полное имя через `title`; строка не растёт,
   потому что значок — один символ той же высоты, что и текст рядом. */
.obychno{margin-left:.35rem;font-size:.85em;cursor:help;flex:0 0 auto}

/* ── §5 класс — своя колонка между ФИО и днями, узкая и по центру, вместо
   хвоста, приклеенного к фамилии. */
.kl-kol{flex:0 0 2.3rem;min-width:0;color:var(--muted);font-family:var(--sans);
  font-size:.85rem;text-align:center;align-self:flex-start;margin-top:.15em}
/* 🔴 НА ВКЛАДКАХ ГРУПП ИМЯ ПЕРЕНОСИТСЯ (канон, крупный шрифт 1.6rem), А
   `.kto{{flex:0 0 auto;overflow:visible}}` СЧИТАЕТ СВОЮ ШИРИНУ ПО САМОЙ
   КОРОТКОЙ СТРОКЕ ПЕРЕНОСА, А НЕ ПО САМОЙ ДЛИННОЙ — текст первой строки
   («Верхошинский») визуально вылезал за рамку своего же флекс-бокса и
   наезжал на соседний `.kl-kol`, вставший сразу за узкой рамкой (найдено
   скриншотом: «Верхошинскийк»). До появления `.kl-kol` это было безвредно —
   переполнение уходило в пустоту перед `.komu` (`margin-left:auto`). Разумный
   минимум ширины даёт первой строке кому расти, не трогая сам перенос. */
#v-В .kol .kto,#v-Д .kol .kto,#v-Н .kol .kto{min-width:13rem}

/* ── §1/§2/§4 (владелец 09.09). Канон держит колонку дня фиксированной
   `9.6rem` и прижимает имя к правому краю (`justify-content:flex-end`,
   `text-align:right`) — на живых длинных именах («Дима Елисеев», «Наталия
   Стрелкова») это и даёт обрезку многоточием ПРИ ПУСТОМ МЕСТЕ СПРАВА (владелец,
   п.1), а на коротких («Надя») — имя, прижатое к разным точкам от строки к
   строке, и оттого не читается колонкой (владелец, п.2, «Надя… не стоит в
   одну линию с остальными»).
   🔴 БЮДЖЕТ СЧИТАН ЗАМЕРОМ, А НЕ ПОДОБРАН НА ГЛАЗ (`diag.py`/`diag2.py` в
   scratchpad этого захода). Канон пришпиливает `.komu` к
   `#s-rasp .para .komu{flex:0 0 auto}` — ID-селектор, computed показал
   `flexGrow:0,flexShrink:0` у `.komu` НЕЗАВИСИМО от того, что написано на
   `.kto`/`.dv`: при таком якоре гибкий тяни-толкай между двумя вложенными
   флекс-контейнерами (`.para` → `.komu` → `.dv`) даёт непредсказуемый результат
   от прогона к прогону (замерено трижды, три разных числа на одних и тех же
   правилах). Вместо гонки за флекс-долями — ФИКСИРОВАННЫЕ ширины по бюджету:
   `.kol` под текст (за вычетом `padding-right:2rem`) — 619px на эталоне
   1440×900.
   🔴 РАСШИРЕНИЕ — ТОЛЬКО ДЛЯ ОДНОДНЕВНОЙ СТРОКИ (`.dv-den`: гостевая
   `/raspredelenie` и админский вид ближайшего занятия — ИМЕННО ОТТУДА примеры
   владельца «Дима Елисеев», «Наталия Стрелкова»). На ПОСТОЯННОМ виде в строке
   ОБА дня разом (`.dv-pn` и `.dv-cht`) плюс замок плюс группа — тот же бюджет
   на вдвое больше органов; первая попытка дать и `.dv-pn`, и `.dv-cht` те же
   13/18rem каждой раздвинула строку почти на 800px при 619px места и вместо
   обрезки дала НАЛОЖЕНИЕ текста (найдено скриншотом, не гейтом — `gejt_verstki`
   на это конкретное наложение не заточен). `.dv-pn`/`.dv-cht` поэтому остаются
   на каноновых `9.6rem`: та же боль обрезки, что была, но НЕ НОВАЯ строка,
   зато выравнивание (лево вместо право, «ПН»/«ЧТ» по центру) чинится и там —
   этого владелец и просил в пп.2/4, ширина не единственная причина жалобы. */
/* 🔴 ТОЛЬКО `#v-shk`. На вкладках групп `.kto` и так ведёт себя иначе (канон:
   `#v-В .kol .kto{white-space:normal;overflow:visible;...}` — имя ПЕРЕНОСИТСЯ
   на карточке покрупнее, не обрезается) и никогда не было в списке жалоб
   владельца — там уже было хорошо (см. скриншот `before_grV.png` этого
   захода). Фиксированная ширина `--imya-w` туда же поверх переноса даёт
   наложение «класс» на вторую строку длинного имени при 1.6rem (найдено
   скриншотом: «Верхошинский» переносится, «9К» съезжает поверх «Марк»). */
#v-shk .para:has(.dv-den) .kto{flex:0 0 var(--imya-w,16ch);min-width:0}
.para .komu .dv-den{flex:0 0 13rem;min-width:0;justify-content:space-between}
.para .komu .dv-den .org{min-width:0;max-width:100%}
/* Гость — шире: у гостя в ячейке нет ни `<select>`, ни соседних органов
   правки, ради которых колонка зажата до `13rem` у админа. */
.para .komu .dv-den:not(:has(.org)){flex:0 0 18rem}
/* На постоянном (два дня разом) ширину не трогаем — только выравнивание. */
.para .komu .dv-pn,.para .komu .dv-cht{justify-content:space-between}
.para .komu .dv-pn .prep-imya,.para .komu .dv-cht .prep-imya,
.para .komu .dv-den .prep-imya{text-align:left}
/* Компактнее в этой конкретной строке (не везде на сайте) — тем же приёмом,
   что канон уже применяет на вкладках групп (`#v-В .otsut` и т.д.): освобождает
   долю бюджета в пользу имени и выпадающего списка на однодневной строке. */
#s-rasp .para .otsut{font-size:.76rem;padding:.1em .4em}
#s-rasp .para .grd-sel,#s-rasp .para .gr-sel{width:3.6rem;flex:0 0 3.6rem}
/* Шапка дней (только на постоянном — на занятии шапки нет вовсе) — то же
   место, но текст без prep-imya, центр вместо левого края (владелец, п.4:
   «буквы ПН и ЧТ… по центру своей колонки»). */
.shapka-dnej .komu .dv-pn,.shapka-dnej .komu .dv-cht{justify-content:center}

/* ── §8 карточки принимающих на вкладке группы — были прижаты к верху,
   оставляя нижнюю половину экрана пустой (владелец, п.8). Канон уже делает их
   широкими построчно (`.kol-pr .para`); не хватало вертикального воздуха и
   зримой границы «полосы». Увеличенный внутренний отступ плюс отступ снизу —
   пять-шесть карточек растягиваются на высоту экрана, а не жмутся к верху. */
.kol-pr .para{padding:2.1rem 1.2rem;margin-bottom:.8rem;background:var(--panel);
  border:1px solid var(--rule);border-radius:12px}
.kol-pr .para:last-child{margin-bottom:0}

/* ── §7 «принимающим»: кнопки пн/чт переехали внутрь своих же колонок дней
   (см. `prepodavateli.vid_prepodavateli`) — небольшой отступ от списка
   фамилий, чтобы кнопка не сливалась с последней таблеткой. */
.td-deti .den-gal{margin-left:.5rem}
</style>
"""
