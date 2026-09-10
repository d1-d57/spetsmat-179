# MANDATE — volna-utro

<!-- assembled by bootstrap_mandate.py; two halves, two authors; do not merge them -->

**STATUS:** `CLOSED-S-DOLGOM`
**TOP_HALF_STATUS:** `COMPLETE`
**BOTTOM_HALF_STATUS:** `COMPLETE`
**ARC:** `zhurnal/2026-09-02_spetsmat-bot`
**JOURNAL:** `zhurnal/2026-09-02_spetsmat-bot/ZHURNAL-ORKESTRATORA-UTRO.md`
**ASSEMBLED:** `2026-09-10`

> Status is one of `OPEN` · `CLOSED` · `REFUSED`. `REFUSED` is a LAWFUL outcome and
> needs a written reason in the bottom half — refusing is not the same as stopping.
> The one outcome forbidden to the orchestrator is to stop and leave the wave
> untouched: a tool's refusal is a task, not an outcome
> (`skills/disciplina-orkestrator/SKILL.md`).

> Phase markers — `TOP_HALF_STATUS: COMPLETE` (this tool always writes the top
> half) and `BOTTOM_HALF_STATUS: PENDING` / `COMPLETE` (the orchestrator flips it
> on return). The linter REFUSES mismatch with STATUS: OPEN ↔ PENDING, CLOSED ↔
> COMPLETE. A reader without context can tell which half is done.

> 🔴 `JOURNAL` — the wave's journal, written ALONG THE WAY, circle by circle, never
> reconstructed at the end of the shift (owner, 03.09, repeated 06.09). Every record
> carries a PRICE AS A NUMBER and a line ABOUT THE LEADING HEAD ITSELF, not only
> about the subject of the wave. At `STATUS: CLOSED` the linter REFUSES a mandate
> whose journal is absent, empty, missing those two halves in a record, or reached
> git in a single sitting; where the journal is outside git the signal cannot be
> computed and the linter answers `НЕПРОВЕРЯЕМО` (rc 3) rather than passing in
> silence. A wave whose journal is empty or back-dated does not count as closed.

## HALF ONE — WRITTEN BY COWORK, BEFORE THE WAVE

### GOAL

By 12:15 on 10.09 the site no longer shows the owner what he called impossible to show other people: no truncated names, nothing spilling out of its card, one control panel instead of stacked rows, and a cabinet you can leave

### INTERVIEW — RENDERED IN ENGLISH FROM A RUSSIAN CONVERSATION — 2026-09-10

> **ИНТЕРВЬЮ ПРОВЕДЕНО** (flag `--intervyu da` at assembly). ⚠ The flag proves the
> assembler was asked, not that the conversation happened — same honest limit
> `bootstrap_zahod.py --intervyu` already prints. ⚠ The interview was held in
> Russian and what is recorded here is the ENGLISH RENDERING of the settled
> meaning, not a quotation. A rendering can be wrong, and only the owner can
> say so.

- **Q1** — Q: Q1
  — M: Design belongs to Opus with a browser, and visual acceptance belongs to the orchestrator itself: opening a page and looking at it is a cheap operation
- **Q2** — Q: Q2
  — M: Everything the owner praised in review two must survive: the wave adds, it does not trade
- **Q3** — Q: Q3
  — M: Speed matters more than completeness today: finish your own points, deploy, and name what is left undone

### FINALIZED AT INTERVIEW — 2026-09-10

- [F1] The icon meaning usually-with-someone-else gets its own column BEFORE the receiving teacher, and that column exists on every row even when empty
- [F2] Hovering that icon shows the FULL name, usually with Natalya Amburg; clicking does nothing
- [F3] Pupils under a receiving teacher stand in ONE row of pills; seven of them fit, as the permanent view already proves
- [F4] The counts four five seven three become ONE column in a fixed place, the same for every teacher
- [F5] The ceiling of five no longer refuses a write: the sixth saves, and the overloaded teacher turns red
- [F6] The teacher list narrows by day: whoever does not come on Thursday is not offered on Thursday at all
- [F7] The cabinet gets the top menu, a tab called Kabinet without the word my, and a full-width strip of lesson dates instead of a link that leads nowhere
- [F8] In the conduit the counter moves into its own column after the surname, Vnesti zadachi becomes a large button, and the legend, the class buttons and the filter collapse into ONE panel row
- [F9] The layout gate is repaired FIRST: it reported zero truncations while the owner sees them, and it never looked for content spilling outside its container
- [F10] Marking the live database runs with a database copy as its first step

### BOUNDARIES AND WHAT IS ALREADY CLOSED

- The speed of saving the distribution is NOT in this wave: it touches the client, the server and the transactional guarantee
- Redesigning the front card as a designer would (G1.5) is NOT in this wave: it is a separate pass in design mode
- 🔴 THE CYCLE, THE FIRST-TEN-MINUTES CHECKS AND THE TWELVE FAILURE CLASSES ARE NOT REWRITTEN HERE. They live in mandate_volna-noch.md and are INHERITED whole. Read them there before starting; this mandate carries only what differs

### CLOSING PHASE — KNOWLEDGE

**The orchestrator runs this phase AFTER the last pass is ACCEPTED and BEFORE the
bottom half is written.** It is not optional and not a report: `--lint` refuses a
bottom half that does not answer it with numbers.

**a. HARVEST.** Collect every lesson, debt and incident born in THIS wave — from the
`kod_*` files of the wave and from the wave journal. Count them.

**b. JUDGE.** Every harvested lesson gets a verdict, from a FRESH free-model pass, in
batches of about ten, and NEVER from the model that wrote it — the author is the
wrong judge, and that is the structural reason this phase exists at all. Three
lawful verdicts: it becomes a **RULE** in a named skill · it becomes a **DEBT** at a
named address · it is **dismissed** with a reason. A lesson with no `ЦЕНА:` is not
judged at all: it goes back to its author as `доработка`, because a lesson without a
price is an observation.

**c. RULES TO CARRIERS.** For every lesson promoted to a rule, name what goes RED when
it is violated. If nothing can, the rule is declared a **hope**, in writing, by our own
law (`skills/disciplina-kachestvo/SKILL.md`). Each new carrier — a gate, a phase, an
artifact field — becomes a NAMED follow-up pass, written now: run in this wave if the
clock allows, carried into the next mandate if not.

**d. BALANCE.** Print the four numbers below. That single delta is what tells us
whether we are winning.

**COST.** All of it on free models, judging batched, and each judging pass reads only
the lesson text, its price and its named home — never the repository. The phase is
bounded by the CLOCK, not by a number of tries: when time runs out, unjudged lessons
are listed BY NAME in the bottom half and carried into the next mandate as an explicit
debt. They may never be dropped silently.

### RESPONSIBILITIES — fixed here so they stop being re-decided every wave

| what | whose |
|---|---|
| MERGING a branch | the pass itself, as its last move |
| ACCEPTANCE of a returned pass | the orchestrator, per pass, in parallel |
| COMMITS ALONG THE WAY | the pass, by path, as it goes |
| THE FINAL COMMITS AND THE PUSH | the orchestrator |
| THE CLOSING PHASE | the orchestrator, before the mandate is closed |

**ЗАКРЫВАЮЩАЯ ПОЗИЦИЯ:** `ZK1` — zakon-zakrytiya-volna-utro

> **This is the LAST NAMED POSITION of the wave, and it is what runs the law
> of closure over this mandate.** It does not live in a Stop hook: a hook is
> killed at its 600 s ceiling and its verdict then vanishes without a word, so
> «found no violation» and «stopped existing» look identical from outside.
> A position of the wave has no ceiling.
>
> Its outcome is one of two, and both are lawful: `CLOSED`, or `CLOSED-S-DOLGOM`
> with one `**ДОЛГ УСЛОВИЯ (<letter>):**` line per condition that stayed red.
> The wave ends either way — a red condition MOVES, with a name, and is never
> dropped. `--lint` refuses a closing status that did not name this position.
>
> 🔴 **ORDER OF MOVES, AND IT IS NOT DECORATION.** This position appends its own
> line to the СОСТАВ file, which means the law it runs JUDGES IT TOO. Run the law
> only AFTER this position's own report has been accepted and its branch merged
> and retired — otherwise the branch condition and the verdict condition go red
> on the position itself, and the wave reads that as its own failure. Measured
> live, not reasoned: running the law straight after appending the line failed
> the verdict condition (this position's own kod_ file is not on disk yet) and
> left the branch condition unjudgeable; completing the cycle first gave five
> green out of five.

_Its line for the wave's `СОСТАВ` file — append it as it stands, no hand editing:_

```
ZK1|zakon-zakrytiya-volna-utro|opus|zhurnal/2026-09-02_spetsmat-bot/mandate_volna-utro.md|pryamoj
```

### SCALE

Five positions running IN PARALLEL, zones split file by file with no overlap. Deadline 12:15, lesson at 13:10. Design work goes to Opus with a browser — the owner's decision on 10.09, after the free pool produced zero lines on four content positions overnight. Only the data-marking position stays on a free model.

### WHAT COUNTS AS FAILURE

The wave has failed if, at 12:15: (a) pytest on main is BELOW the entry number taken by command before the first position; (b) the live site does not answer on the front page, the distribution page or the conduit; (c) anything the owner PRAISED in review two has disappeared — the marks, the dates on ticks, the cell history, the grobarij, the initials. Losing a praised feature to fix an unpraised one is the one outcome worse than doing nothing.

## ЦИКЛ — НАСЛЕДУЕТСЯ ЦЕЛИКОМ, ЗДЕСЬ ТОЛЬКО ОТЛИЧИЯ

🔴 **Читай `mandate_volna-noch.md`, разделы «ЦИКЛ ОРКЕСТРАТОРА» (17 пунктов), «ПЕРВЫЕ ДЕСЯТЬ
МИНУТ» и «РЕЕСТР ОТКАЗОВ».** Они писались этой ночью и оплачены ею; переписывать их здесь
значило бы завести вторую редакцию, которая разойдётся с первой. Ниже — ТОЛЬКО то, чем эта
волна отличается.

**О1. ПЯТЬ ПОЗИЦИЙ ИДУТ ПАРАЛЛЕЛЬНО.** Зоны разведены пофайлово, пересечений нет ни одного.
Запускай их сразу, не по очереди: до занятия три часа с небольшим.

**О2. ДИЗАЙН — НА OPUS, И С БРАУЗЕРОМ.** Решение владельца 10.09. Четыре позиции из пяти —
дизайнерские, они идут платным каналом. `razmetka-bazy` механическая, ей хватит бесплатной.
Причина замерена ночью: бесплатный пул на содержательной работе дал ноль из четырёх.

**О3. 🔴 ВИЗУАЛЬНАЯ ПРИЁМКА — ТВОЯ РАБОТА, И ОНА ДЕШЁВАЯ.** Открыть страницу браузером и
посмотреть глазами стоит секунды. Не отдавай это отдельной позиции и не подменяй чтением
отчёта. Владелец 10.09 прямо: «может быть, это можно поручить даже оркестратору». Смотри и
после каждой принятой позиции, и **за элементами, которые появляются попутно** — если сосед
завёл новый блок, посмотри, как он выглядит, и поправь, не заводя ради этого заход.

**О4. ГЕЙТ ЧИНИТСЯ ПЕРВЫМ, НО НЕ БЛОКИРУЕТ ОСТАЛЬНЫХ.** `gejt-pravda` идёт вместе со всеми.
Пока он не починен, вёрсточные позиции судятся ТВОИМИ глазами через браузер — и это законный
способ приёмки сегодня, а не поблажка.

**О5. ⛔ ОТМЕНЁН ПОПРАВКОЙ О11 — ЧИТАЙ О11. Прежний текст:** Владелец сказал дословно: «я сказал довольно
много вещей, и не все из них должны быть выправлены». Приоритет — то, что он назвал словами
«дико», «кошмар», «неудобно показывать людям». Несделанное называется списком, это законный
исход, а не провал.

**О6. 🔴 НЕ СЛОМАТЬ ПОХВАЛЕННОЕ.** В `TZ-DOBOR-10-09.md` есть раздел H0 — семь вещей, которыми
владелец доволен. Проверяй их ПОСЛЕ каждой выкатки: значки, даты у галочек, история клетки,
гробарий, инициалы, вид кондуита, сам факт кабинета. Потерять похваленное ради непохваленного —
единственный исход хуже, чем не сделать ничего.

**О7. СРОК 12:15, ЗАНЯТИЕ В 13:10.** `VOLNA-DEDLAJN` читается командой. За полчаса до срока
останови начатое, выкати сделанное и собери отчёт: владельцу нужен работающий сайт в 13:10, а
не полный список закрытых пунктов в 13:30.

## О8. 🔴 ЗАПУСК — ПЯТЬ СТРОК, ОДНОЙ ПАЧКОЙ, В ПЕРВЫЕ ДЕСЯТЬ МИНУТ

```
cd ~/Documents/GitHub/spetsmat-bot
bash zhurnal/2026-09-02_spetsmat-bot/ZAPUSK-ZAHODA.sh gejt-pravda opus
bash zhurnal/2026-09-02_spetsmat-bot/ZAPUSK-ZAHODA.sh karkas-menyu-kabinet opus
bash zhurnal/2026-09-02_spetsmat-bot/ZAPUSK-ZAHODA.sh raspredelenie-kolonki opus
bash zhurnal/2026-09-02_spetsmat-bot/ZAPUSK-ZAHODA.sh konduit-panel opus
bash zhurnal/2026-09-02_spetsmat-bot/ZAPUSK-ZAHODA.sh razmetka-bazy sonnet
```

Каждую — фоновой задачей, все пять сразу. Зоны не пересекаются ни одним файлом, ждать нечего.

🔴 **ЧЕТЫРЕ ПОЛОМКИ, КОТОРЫЕ ЗДЕСЬ УЖЕ ЗАКРЫТЫ — НЕ ЧИНИ ИХ ЗАНОВО.** Ночная голова потратила
на них час; повторять этот час нельзя, у волны его нет.

| поломка | как убивала ночью | закрыто чем |
|---|---|---|
| стартовая строка генератора зовёт `orkestr.py` внутри `spetsmat-bot`, где его НЕТ | команда умирает до движка, лог 0 байт, вина списывается на модель | `ZAPUSK-ZAHODA.sh` знает путь в `disciplina`; строка генератора в заходах помечена «не использовать» |
| `worktree add` неидемпотентен, а надзиратель перезапускает строку | ретрай рвал цепочку и СТИРАЛ сделанное: 11 позиций из 12, 15 КБ работы | запускатель судит ФАКТ наличия папки, а не код возврата |
| входной ритуал §0.1 съедает прогон целиком | 4 позиции из 4 дали ноль строк при логах до 119 КБ | ритуал ОТМЕНЁН и запускателем, и красной строкой в §0.1 каждого захода |
| будильник берёт темы глобом по всей арке (71 файл восьми волн) | все три будильника умирали за минуту, будить голову было нечем | будильник читает `VOLNA-POZICII`, файл переписан под пять позиций этой волны |

## О9. 🔴 АВТОСОХРАНЕНИЯ У ПЛАТНОЙ ДВЕРИ НЕТ — КОММИТИШЬ ТЫ

`ZAPUSK-ZAHODA.sh` не несёт таймера: в нём ноль совпадений по `sleep`, `while`, `commit`. У
бесплатной двери сохранность — механизм, у платной — только правило, адресованное модели, а
четыре позиции ночью показали, чего это правило стоит: ноль коммитов ветки при логе 119 КБ.
**Раз в круг коммить рабочую папку каждой живой позиции сам** и печатай в строку круга
поле `не в git: N`. Из песочницы аналитика это НЕ ВИДНО вовсе — `.git` рабочей папки указывает
абсолютным путём машины владельца.

## О10. ЧАСОВОГО НЕ ПОДНИМАТЬ ВТОРОГО

Часовой ночной волны ЖИВ и крутится (круг 118 на 10:34). Второй поверх него — два писателя в
одни файлы. Бей ЕГО сердце: `date >> zhurnal/2026-09-02_spetsmat-bot/SERDCE-VOLNY-noch.md`,
каждым обращением к bash. Указатель волны перепиши на имя `UTRO`, чтобы хук судил состав этой
волны, а не ночной.


## О11. 🔴 ПОПРАВКА ВЛАДЕЛЬЦА 11:0x — ЦЕЛЬ И РИТМ ДОСТАВКИ ИЗМЕНИЛИСЬ

**Я НАПИСАЛ НЕВЕРНО, ЧТО «НЕ ВСЁ ОБЯЗАНО БЫТЬ СДЕЛАНО» (пункт О5). Владелец не согласен, и он
прав. Действует это:**

**ЦЕЛЬ — ЗАКРЫТЬ ВСЕ ДВАДЦАТЬ ВОСЕМЬ ПУНКТОВ К НАЧАЛУ ЗАНЯТИЯ**, а не то, что успеется за час.
Час — это не срок волны, а срок ПЕРВОЙ ПОРЦИИ. Дословно: «за первый час закроется 10–15 самых
важных, за следующий ещё 10, потом ещё 8. К началу занятия надо закрыть всё, просто постепенно
и постепенно пушить».

**РИТМ — НЕПРЕРЫВНАЯ ДОСТАВКА, А НЕ ОДНА СДАЧА В КОНЦЕ.** Дословно: «мы вообще пушим всё
время. Все правки, которые готовы — пушим. Он видит, что что-то прошло, что-то работает, пушит
это. Потом ещё что-то работает, закоммитилось — пушит это».

Практически, и это твой цикл на сегодня:
1. Позиции коммитят **каждую готовую правку отдельно**, не копят до конца задания. Одна правка —
   один коммит с внятным сообщением.
2. Ты **смотришь, какие коммиты появились**, проверяешь их глазами через браузер и **сразу
   пушишь и выкатываешь** то, что работает. Не ждёшь, пока позиция закончит все свои пункты.
3. Сломалось после выкатки — откатываешь ЭТУ правку, а не всю позицию.
4. Так каждые 15–20 минут: коммит → взгляд → выкатка → строка в дневник.

**ПРИОРИТЕТ ПЕРВОЙ ПОРЦИИ — ТО, ЧТО СЕЙЧАС МЕШАЕТ РАБОТАТЬ, А НЕ ТО, ЧТО ПЛОХО ВЫГЛЯДИТ.**

🔴 **САМОЕ ВАЖНОЕ, И ЭТО СЛОВА ВЛАДЕЛЬЦА: «сейчас распределение НЕ РАБОТАЕТ, потому что нельзя
поставить больше человека. Должно сохраняться с любым количеством человек».** Это пункт A1 —
снять `CeilingExceeded` в `core/services/enrollment.py:434`. Он стоит в задании позиции
`raspredelenie-kolonki` пятым по счёту; **сделать его ПЕРВЫМ, закоммитить отдельно и выкатить
немедленно**, не дожидаясь остальных пяти правок этой позиции. Пока он не выкачен, человек,
правящий распределение перед занятием, упирается в отказ на законной правке.

Дальше по убыванию «мешает работать»:
* A2 — список принимающих сужается по дню (нельзя выбрать того, кого нет);
* H5.1 — вкладка «История занятий» существует, но потерян ВХОД в неё;
* H1.1 и H2.1 — из кабинета некуда уйти, вкладки «Кабинет» нет в меню;
* G5 и H3.3 — таблетки вылезают за карточку, «неудобно показывать людям»;
* дальше — остальная вёрстка по разделам G и H.

**ЧТО ЭТО МЕНЯЕТ В ОТЧЁТНОСТИ:** в строке круга теперь два числа — **закрыто пунктов X из 28**
и **выкачено на боевой Y из X**. Владелец следит снаружи и спрашивает по ним.

## ДНЕВНИК ОРКЕСТРАТОРА — строка на круг, не реже двадцати минут

`ЧЧ:ММ · круг N · запущено: … · принято: … · без вердикта: … · main зелёный/красный · выкачено до: … · не в git: N · смотрел глазами: да/нет`

`10:57 · круг 1 · запущено: 5 · принято: 0 · без вердикта: 5 · main зелёный (вход 1252 passed) · выкачено до: 1a4cc80 · не в git: 11 · смотрел глазами: да · ЗАКРЫТО 1 из 28 (A1) · ВЫКАЧЕНО 1 из 1`

`11:13 · круг 3 · запущено: 5 · принято: 1 · без вердикта: 4 · main зелёный (1252 passed = вход) · выкачено до: 2efeee0 · не в git: 0 · смотрел глазами: да · ЗАКРЫТО 10 из 28 · ВЫКАЧЕНО 10 из 10`

`11:20 · круг 5 · запущено: 5 · принято: 1 · без вердикта: 4 · main зелёный (1252 passed = вход) · выкачено до: 92a838d · не в git: 2 · смотрел глазами: да · ЗАКРЫТО 19 из 28 · ВЫКАЧЕНО 19 из 19`

`11:32 · круг 6 · запущено: 6 (шестым sloi-postoyannoe-v-den по срочному пункту владельца) · принято: 2 · без вердикта: 4 · main зелёный (327 passed целевых, гейт 13 passed) · выкачено до: dcc6e2a · не в git: 0 · смотрел глазами: да · ЗАКРЫТО 21 из 28 · ВЫКАЧЕНО 21 из 21`

`12:02 · круг 10 · запущено: 6 · принято: 3 · без вердикта: 3 · main зелёный (гейт 25 passed) · выкачено до: 793440a · не в git: 1 · смотрел глазами: да · ЗАКРЫТО 24 из 28 · ВЫКАЧЕНО 24 из 24`

`12:31 · круг 17 · запущено: 6 · принято: 6 · без вердикта: 1 · main ЗЕЛЁНЫЙ И ВЫРОС: 1294 passed против входных 1252 · выкачено до: c8f5a09 · не в git: 0 · смотрел глазами: да · ЗАКРЫТО 26 из 28 · ВЫКАЧЕНО 26 из 26`

---


## HALF TWO — WRITTEN BY THE ORCHESTRATOR, ON RETURN

> Not written yet: the wave has not returned. STATUS stays `OPEN` until it has, and
> `--lint` says so out loud instead of passing in silence.

### WHAT WAS ASSEMBLED AND LAUNCHED

Семь позиций, все приняты. Пять по составу (`gejt-pravda`, `karkas-menyu-kabinet`,
`raspredelenie-kolonki`, `konduit-panel`, `razmetka-bazy`) запущены одной пачкой в первые десять
минут по О8 — зоны не пересеклись ни одним файлом. Шестая, `sloi-postoyannoe-v-den`, добавлена
срочным пунктом владельца в 11:23. Седьмая — добор `gejt-pravda --dobor` с требованием J1.
Вход в волну: два коммита сборки по заявке очереди (`daa75c4`, `aef4a37`), оба с push.

### WHAT IT REPAIRED ITSELF AND WHY IT WAS BROKEN

* **Ложный ноль надзора:** «окон заходов 0» при пяти живых позициях — часовой считает образцом
  `orkestr.py`, а волна запущена `ZAPUSK-ZAHODA.sh` по О8. Различено `ps`.
* **Ложный ноль лога:** пять логов по 0 байт при пяти работающих позициях — `claude -p` отдаёт
  вывод одним куском в конце.
* **Мёртвый туннель** `deploy/ADRES.txt` отдавал осмысленную страницу «no tunnel here».
* **Ложная просадка pytest** (1241 против 1252): мой локальный сервер занял порт, который
  поднимают тесты канона.
* **Испорченная `cp` локальная база** — восстановлена `VACUUM INTO`; боевой не касалось.

### VERDICTS

- **kod_razmetka-bazy.md** — принято — критерий B1 перегнан МОЕЙ командой на БОЕВОЙ базе через ssh: 16A † 1, 16α † 4, 16ℵ † 0 — совпало точно; гейт 0 по зоне tools/ ops/ зелёный; кода не меняла, ветка пуста законно (импорт владелец прогнал руками в 00:26, позиция это вскрыла и проверила независимо: своя резервная копия, marks 16190 до и после). НЕ ПРОВЕРЕНО МНОЙ: крестик глазами в кондуите — раздел за входом, путь роутинга не найден за отведённое время
- **kod_konduit-panel.md** — принято — все шесть пунктов H4 закрыты и проверены МОИМИ глазами на живой странице: большая кнопка у заголовка, счётчик колонкой ОБЯЗ. после фамилии, одна панель, легенда «⋆ сложная», строчные 6а/6б, цвета замерены computed style (⋆ rgb(232,131,106) против ◦ rgb(127,182,210)). Гейт 0 по зоне зелёный, невлитого 0, её число tests/grid 93 passed перегнано мной — совпало. H0 цело: даты у галочек, инициалы, гробарий на месте
- **kod_karkas-menyu-kabinet.md** — принято — владелец принял дословно: «кабинет устроен роскошно, шикарно, так и нужно». Гейт 0 зелёный, ветка влита e8038e1, 20 passed перегнано мной. В плюс: сама назвала недостижимость критерия 2 в его форме и не подогнала числа; сама не стала входить чужим паролем
- **kod_sloi-postoyannoe-v-den.md** — принято — диагноз верен, обе двери API прогнаны мной (GET n:3 → POST snyato:3 → GET n:0), 30 passed, владелец подтвердил кнопку на боевом. Разметку доделал оркестратор: коммит «the button» трогал только server.py — это увидел владелец. Расхождение чисел 8 против 5 объяснено: все ручные строки против расходящихся с постоянным
- **kod_raspredelenie-kolonki.md** — принято — её числа перегнаны моим прогоном гейта в 12:30: обрезка 0, переносы 0, вышли 0, скролл 0 на всех 13 экранах обеих ролей. Владелец принял дословно. Глазами: J3, G2.2, G3.1, G4.3, G7 закрыты. Не закрыто и названо: J2.3 и J2.4 на постоянном распределении — экран, который гейт не обходит вовсе
- **kod_gejt-pravda.md** — принято — обе половины G0 прогнаны мной: краснел на живой обрезке точным числом, зелёный после починки. J1 закрыт, 32 passed, центр на кондуите 96 → 39. Сделала больше задания: ловит и justify-content:center. Осталось не ей поручённое: EKRANY не содержит постоянного распределения
### WHAT WAS EXCLUDED AND WHY

* **G6.2** (убрать кнопки «пн»/«чт» из постоянного) — НЕ сделано намеренно и вынесено вопросом:
  эта галка ЕДИНСТВЕННЫЙ орган, задающий «в четверг прихожу», она пишет в
  `prepodavatel_ne_prihodit`, а та же таблица сужает список по дню — пункт A2, закрытый этой же
  волной по прямому требованию владельца. Убрать орган значило бы молча обрушить A2. Сделана
  безопасная половина — G6.1, дублирующая подпись дня снята.
* **K2** (что-то с кнопкой «Внести задачи») — владелец сформулировал неуверенно и сам сказал не
  угадывать.
* **K3** (выделение обязательных задач) и **G1.5** (карточка главной в дизайн-режиме) — владелец
  сам вынес за границу волны.
* **Пятое значение `source`** для внесённого с бумаги — правка СХЕМЫ, решение владельца; сам не
  трогал, происхождение положил в `note`.
* **Чистка токенов** — не запускалась: её половина А переписывает публичную историю `push --force`,
  а живые worktree остались бы на осиротевших коммитах. Порядок владельца соблюдён.

### IRREVERSIBLE ACTIONS

* **Записи в ЖИВУЮ базу школы**, каждая с копией штатной дверью первым шагом:
  38 отметок с бумажных кондуитов за 07.09 (36 + 2 Романчуку), слой занятия 07.09 на четверых
  школьников, три строки кабинетов на 10.09 (В 301 · Д 302 · Н 207).
  Копии: `spetsmat-20260910T102341Z-ruchnoj.db.gz` (до кондуитов), `...T102903Z` (после),
  `...T134533Z` (до Романчука).
* **`data/spetsmat.db` снята с индекса git** — файл на диске цел, в git снимок схемы
  `data/shema.sql`.
* **Девять выкаток на боевой**, каждая после `pytest` и с проверкой ответа 200.

### QUESTIONS TO THE OWNER — ANSWER IN PLACE, UNDER EACH

> 🔴 **A QUESTION HERE IS NOT A COMPLAINT — IT IS THE ONLY LAWFUL FORM OF
> «I could not do this because the decision is not mine».** An item excluded
> with a written reason that amounts to «I lacked the owner's decision» is not
> an outcome: it is a question that was never asked, and the orchestrator
> quietly decided for two people that there was no time to ask.
>
> **Form:** one `[Vn]` item per question. Each carries WHAT is blocked,
> WHAT was measured about it already, and the SHAPE of a usable answer — so the
> owner can reply in one line rather than reconstruct the problem. The owner
> writes the answer directly underneath, in place.
>
> **Empty is lawful** and means «nothing was blocked by a missing decision» —
> which is a claim, not a default, and `--lint` will not let it hide a REFUSED
> or a partially delivered wave.

[V1] Кнопки «пн»/«чт» в постоянном распределении (G6.2).** ЧТО ЗАБЛОКИРОВАНО: убрать их, как
  вы решили 10.09. ЧТО ЗАМЕРЕНО: галка — единственный орган, пишущий в `prepodavatel_ne_prihodit`
  (`infra/prepodavatel_den_repo.py:60`), а эта таблица сужает список принимающих по дню — пункт
  A2, закрытый этой же волной. ФОРМА ОТВЕТА: либо «убрать, задавать день иначе — вот как», либо
  «оставить, хватит снятой подписи (G6.1)».
[V2] Романчук, бумага Стрелковой.** ОТВЕЧЕНО ВАМИ 10.09: 16A, задачи 1а и 1б. Внесено дверью
  `tools/vnesti_s_bumagi.py`, 2 клетки, 2 новых события.
[V3] Верхошинский, приписка «2 пункт» рядом с задачей 11.** Не угадывал. Смысл не знаем.
[V4] Виляев, листок в рукописи «16ба».** Вносил в 16α — 2, 3, 4, 6 там есть. Подтвердите.
[V5] Юсуфов Арон.** На листе Шнитке его нет ВОВСЕ, хотя он в постоянной четвёрке. Ни отметок,
  ни отсутствия ему не выдумывал.
[V6] Виляев по постоянному у Амбург, а сдавал Шнитке.** Слой занятия за 07.09 ему НЕ правил:
  поручены были только трое у Стрелковой. Править?
[V7] Пятое значение `source`** (или отдельное поле) для внесённого с бумаги: сейчас ищется
  грепом по свободному тексту `note`. Схему сам не трогаю.

### CLOSING PHASE — KNOWLEDGE BALANCE

> The four numbers below are the point of this section. `DELTA` is not
> stored, it is CHECKED: `--lint` recomputes `BORN` minus `CLOSED` and
> refuses a mismatch. `CARRIED` above zero REQUIRES the unjudged lessons
> to be listed BY NAME underneath — carried is lawful, silent is not.

**BORN:** `16`
**CLOSED:** `6`
**CARRIED:** `10`
**DELTA:** `10`

_Carried by name (one line each, or the single word `none`):_
Проверка синтаксиса JS в `tests/` — я сломала живой скрипт кондуита, `pytest` остался зелёным.
`git_zona.py --vsyo-ravno` печатает ВСЕ открытые заявки (заявка `2026-09-10T1224` заведена).
Правило «копия базы — только `ops/rezervnaya_kopia.py`, никогда `cp`» — в мандат.
Часовой обязан ЗВОНИТЬ на молчание сердца, а не печатать в пульс.
Вилка живости по движку в «ПЕРВЫХ ДЕСЯТИ МИНУТАХ»: `claude -p` не растит лог до конца.
Счётчик окон часового слеп к позициям, запущенным `ZAPUSK-ZAHODA.sh`.
Прогон гейта вёрстки пишет фамилии детей в публичный `docs/index.html`.
Проверка «правящий орган несёт `data-den` либо стоит на странице с кнопкой Сохранить».
Неподтверждённое значение в поле обязано выглядеть иначе, чем сохранённое (молчащий отказ).
Пятое значение `source` для внесённого с бумаги — решение владельца.

### LINE-BY-LINE ANSWER TO EVERY FINALIZED ITEM

> One line per finalized item, and every item of the top half must get one: `done` or `not done` with the reason. This field is the point of the whole artifact.
- [F1] **done** — колонка значка «обычно у» стоит ПЕРЕД именем принимающего и существует в каждой строке. Проверено глазами на боевом.
- [F2] **done** — наведение даёт полное имя: `title="обычно у Натальи Амбург"`, и у гостя тоже. Клик не делает ничего.
- [F3] **done** — школьники одного принимающего стоят в ОДИН ряд внутри карточки. У Дани Макарова шесть таблеток в строку; было в две.
- [F4] **done** — числа собраны в одну колонку в фиксированном месте (`6e04689`).
- [F5] **done** — потолок пяти не отвергает запись: `ceiling=None` в форме, `CellState` сервиса не бросает `CeilingExceeded`; перегруз остался видимым признаком. Выкачено в 10:53, через 8 минут после поправки О11.
- [F6] **done** — список принимающих сужается по дню (`a99fe9c`), заодно сортировка по фамилии.
- [F7] **done** — верхнее меню есть, вкладка «Кабинет» без слова «мой» после «Класса», вместо ссылки — полоса дат занятий с начала года, зелёная/красная. Владелец принял дословно: «устроен роскошно, шикарно».
- [F8] **done** — счётчик отдельной колонкой после фамилии, «Внести задачи» большой кнопкой на строке заголовка, легенда и кнопки классов в ОДНОЙ верхней панели. Принято владельцем: «мне всё нравится».
- [F9] **done** — гейт починен ПЕРВЫМ и обе половины критерия прогнаны: краснел на живой обрезке точным числом («надо 247 есть 215»), зелёный после починки. Сверх того: пятая проверка на центрирование, экран постоянного распределения (там первый же прогон нашёл 62 обрезки) и печать ОХВАТА рядом с числом находок.
- [F10] **done** — разметка боевой базы шла с копией первым шагом; критерий перегнан моей командой на боевой: `16A † 1`, `16α † 4`, `16ℵ † 0`.
