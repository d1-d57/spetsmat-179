# MANDATE — volna-noch2

<!-- assembled by bootstrap_mandate.py; two halves, two authors; do not merge them -->

**STATUS:** `CLOSED-S-DOLGOM`
**TOP_HALF_STATUS:** `COMPLETE`
**BOTTOM_HALF_STATUS:** `COMPLETE`
**ARC:** `zhurnal/2026-09-02_spetsmat-bot`
**JOURNAL:** `zhurnal/2026-09-02_spetsmat-bot/ZHURNAL-ORKESTRATORA-NOCH2.md`
**ASSEMBLED:** `2026-09-11`

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

close every small debt of the day and CONNECT what is already written: the layout gate sees all screens, both journals work, the teacher page becomes a table, the conduit stops mixing meanings in one cell, the receiving-teacher field fits the longest name, marks can be set with no network, and the paper conduit of 07.09 lands in the base

### INTERVIEW — RENDERED IN ENGLISH FROM A RUSSIAN CONVERSATION — 2026-09-10

> **ИНТЕРВЬЮ ПРОВЕДЕНО** (flag `--intervyu da` at assembly). ⚠ The flag proves the
> assembler was asked, not that the conversation happened — same honest limit
> `bootstrap_zahod.py --intervyu` already prints. ⚠ The interview was held in
> Russian and what is recorded here is the ENGLISH RENDERING of the settled
> meaning, not a quotation. A rendering can be wrong, and only the owner can
> say so.

- **Q1** — Q: Q1
  — M: Offline: a WRITE queue in the browser plus reading from the last snapshot. A full local site merging two databases is REJECTED — it would be the second source of truth we spent the day killing.
- **Q2** — Q: Q2
  — M: Form of work: a WAVE of positions, not one big pass. Six different jobs in one context means the last items get done worse than the first, and we have already paid for that.
- **Q3** — Q: Q3
  — M: Design does not go to free models: whatever the owner judges by eye runs on Opus; pure mechanics — grep-and-replace, a threshold in a script, running a finished door — run free.
- **Q4** — Q: Q4
  — M: Design scope is ONE place: the width of the receiving-teacher field on the group tabs for a logged-in user, in both the per-lesson and the standing distribution. Left edge stays put, right edge moves right. Nothing else in the design, firmly.
- **Q5** — Q: Q5
  — M: There are TWO journals, not two tabs of one: the teachers journal, from which Natasha computes payroll, and the pupils journal, where grades will go and which is the seed of the personal page.

### FINALIZED AT INTERVIEW — 2026-09-10

- [F1] no new functionality: connect what is written; the standard functionality must work very well
- [F2] task entry as a dialogue is NOT built — everyone is used to pressing the button, the owner deferred it deliberately
- [F3] the bot is not needed now, it will be needed later
- [F4] offline: a WRITE queue plus reading from the last snapshot; a full local site is REJECTED as a second source of truth
- [F5] there are TWO journals: teachers (payroll) and pupils (grades); the word is journal, not history
- [F6] design is fixed in ONE place: the width of the receiving-teacher field on group tabs for a logged-in user, both versions; left edge stays, right edge moves right; nothing else
- [F7] design is not given to free models
- [F8] a plain, understandable door is needed for entering marks into the base from Cowork

### BOUNDARIES AND WHAT IS ALREADY CLOSED

- outside this wave: the entry dialogue · raising the bot · scrubbing the dead token lines · the speed of saving the distribution · forbidding a bare insert into marks
- already closed on 10.09 and NOT to be redone: the address of the base and the source door · one truth about the receiving teacher · the entrance to the lessons journal · the sheet caption, which lied by letter case and not by data · the ten-second timeout on a mark · the button that applies the standing distribution to a day

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

**ЗАКРЫВАЮЩАЯ ПОЗИЦИЯ:** `ZK1` — zakon-zakrytiya-volna-noch2

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
ZK1|zakon-zakrytiya-volna-noch2|opus|zhurnal/2026-09-02_spetsmat-bot/mandate_volna-noch2.md|pryamoj
```

### SCALE

eight positions, one night. V1 goes first and alone: every other position touches layout, and layout must be judged by a gate that does not stay silent. V1-V4 on Opus, V5-V8 on free models.

### WHAT COUNTS AS FAILURE

the wave has failed if by morning any screen still truncates an input field, or a journal does not switch tabs, or a mark cannot be set without network, or Romanchuk still stands at zero of eleven, or the bottom half of this mandate is unwritten

## HALF TWO — WRITTEN BY THE ORCHESTRATOR, ON RETURN

### WHAT WAS ASSEMBLED AND LAUNCHED

Восемь позиций, все восемь подняты и все восемь доведены до влития в `main`.
V1 `gejt-vse-ekrany` поднята первой и одной в 00:22:42; V2–V8 — одной пачкой в 00:54:12–00:54:19
после поправки владельца, что гейт нужен НА ПРИЁМКЕ, а не на старте (моё буквальное чтение
правила 1 стоило волне 32 минут очереди за самой большой позицией).

🔴 СОСТАВ БЫЛ НЕПОЛОН: файл `VOLNA-NOCH2-SOSTAV.txt` перечислял семь позиций, а заход
`kod_shirina-prep-vdn.md` был собран в 00:12 и строки не имел. Мандат в разделе SCALE считает
волну восьмипозиционной; строка V8 дописана оркестратором с пометкой, кто и почему её дописал.

🔴 ТРИ МОДЕЛИ ИЗ ЧЕТЫРЁХ БЕСПЛАТНЫХ НЕ СУЩЕСТВОВАЛИ НА РАЗДАЧЕ. Проверено `opencode models`
в 00:24 (408 имён, бесплатных 19): `z-ai/glm-5.2:free` (V5), `minimax/minimax-m3:free` (V6),
`minimax/minimax-m2.7:free` (V8) — ни одной; жила только `thinkingmachines/inkling:free` (V7).
Перевыбраны БЕСПЛАТНЫЕ, каждая проверена живым прогоном, правка внесена в ШАПКУ своего захода —
один дом, как велит пункт 4. Позже `cohere/north-mini-code:free` (V8) умерла через 106 секунд
(`UnknownError · ref err_71a5f2e3`) — перевыбрана снова бесплатная. На Opus не поднята ни одна.

### WHAT IT REPAIRED ITSELF AND WHY IT WAS BROKEN

* **Оснастка волны жила не в том доме.** До 00:47 оркестратор бил в `SERDCE-VOLNY-noch.md` —
  сердце МЁРТВОЙ волны УТРО, и часовой мерил по нему же: четыре часа он печатал «сердце молчит
  240м» и звал владельца вхолостую. Заведена оснастка `*-noch2`, поднят часовой этой волны,
  ДВА старых часовых (17424, 37736) погашены — они караулили покойника.
* **Мандат волны и вся её оснастка лежали ВНЕ git.** Закон, по которому волна живёт, полтора
  часа существовал только на диске одной машины. Сохранено оркестратором.
* **Двадцать четыре заявки висели с 10.09**, и три из них ПРОСИЛИ вывезти `main` — то есть
  дверь git загораживала ровно то, о чём её же почта просила сутки. Разобраны фактом (все ветки
  10.09 влиты, проверено `merge-base --is-ancestor` по каждой) и закрыты.
* **Бэклог веб-части лежал в ЧУЖОМ репозитории** третьи сутки вопреки требованию владельца от
  08.09. Перенесён в `doc/OCHERED-veb.md` побайтово: md5 исходника совпал с md5 первых 36 899
  байт копии.
* **Позиция V8 не влила за собой ветку** — на бесплатной модели последнего хода может не быть.
  Влитие доделал оркестратор (`f5a0d99`), иначе правка, которую владелец судит ГЛАЗАМИ,
  шесть часов была бы сделана и не видна.

### VERDICTS

| позиция | вердикт | чем проверено ОРКЕСТРАТОРОМ, а не отчётом |
|---|---|---|
| V1 gejt-vse-ekrany | принято | гейт прогнан дважды: на пустой базе 13 экранов из 39 (узлов 99), на восстановленном снимке 15 847 отметок — 14 из 41 (узлов 327), rc=1 в обоих. Список экранов ПОРОЖДЁН роутами: 17 маршрутов → 23 экрана против девяти рукописных строк |
| V2 zhurnaly-i-kabinet | принято | `pytest test_kabinet.py test_istoria_zanyatij.py` → 35 passed, 2 skipped В ДВУХ деревьях: в ветке позиции и в чистой главной папке на main |
| V3 konduit-i-raspredelenie | принято | числа воспроизведены своей командой на живом рендере: инициалы в своём столбце 1242, галочек 558, строк `gotov` 0, инициалов в клетке фамилии 0 — совпали с отчётом ДО ЕДИНИЦЫ |
| V4 offlajn-ochered | принято | `pytest test_offlajn_ochered.py test_offlajn_brauzer.py` → 19 passed |
| V5 melochi-i-dovoz | принято | греп по живым файлам: «Елена» → 0 в каждом из трёх, «Лена» есть, «приходит» → 5, три doc/ от 06.09 под git |
| V6 nadzor-zvonit | принято | ЕДИНСТВЕННАЯ позиция, проверенная не прогоном, а СОБЫТИЕМ: замок `skazano-o-prostoe` создан в 10:08, `getMe` по ALERT_TOKEN → HTTP 200, владелец пришёл в 10:20 после восьми часов молчания |
| V7 dannye-07-09 | **доработка** | запрет соблюдён: `data/spetsmat.db` не менялась (mtime 10.09 17:00), в копию не внесено ничего; F8 закрыта (9a43f89). НО: отчёт остался плейсхолдерами, и готовых команд ДВЕ при одиннадцати отметках Романчука |
| V8 shirina-prep-vdn | принято | `flex:0 0 11rem;max-width:11rem` для групп В/Д/Н против прежних 8.6rem, левый край не тронут; влитие доделал оркестратор |

Машинная приёмка `priyomka.py`: у пяти позиций все 18 гейтов зелёные; у V2 и V5 по одному
красному (Г10 «долг репозитория» и Г14 «ветки нет» — ветка ВЛИТА И ПОГАШЕНА, гейт этого
состояния не знает); у V7 три красных, и они честные — это и есть её доработка.

### WHAT WAS EXCLUDED AND WHY

* Диалог внесения задач, бот, чистка мёртвых строк токена, скорость сохранения распределения,
  запрет голого `insert into marks` — исключены САМИМ МАНДАТОМ, не мной.
* Внесение отметок 07.09 в базу — невозможно с этой машины: боевая база на сервере, доступа нет
  (замер 00:36: `/srv/spetsmat/data` нет, `SPETSMAT_BAZA` не выставлена, ssh-хоста нет, туннеля
  нет). Владелец назвал этот случай заранее: «либо вносишь по-настоящему, либо V7 останавливается
  и говорит об этом строкой». Выбран второй, в копию не внесено НИЧЕГО.
* Боевой прогон гейта по `spetsmat.school` — НЕ СДЕЛАН. Это мой долг, а не исключение: адрес
  владелец дал, но к тому часу я уже не работала. Гейт для этого готов — он принимает адрес
  снаружи; команда названа в отчёте V1.
* Пароли школьников — владелец прямо оставил на утро, в волну не добавлял.

### IRREVERSIBLE ACTIONS

1. `push` в `origin/main` — трижды (03:09, 10:31 и финальный), каждый раз ПОСЛЕ замера.
2. Закрытие 24 заявок очереди git — перенос в `zayavki/sdelano/`, с письменным разбором в каждой.
3. Влитие ветки `zahod/shirina-prep-vdn` в `main` за позицию (`f5a0d99`).
4. Правка ЧУЖИХ отчётов на приёмке: дописаны строки АРТЕФАКТ у V2 и V7 и галочка гигиены входа
   у V5 — каждая помечена словами «ДОПИСАНО ОРКЕСТРАТОРОМ НА ПРИЁМКЕ».
5. Погашены два процесса часового прошлой волны (PID 17424, 37736).
Ничего не удалено безвозвратно: ни файлов, ни веток, ни записей базы.

### QUESTIONS TO THE OWNER — ANSWER IN PLACE, UNDER EACH

- **[V1] Столбцы журнала берутся из `sessions`, а она заводится ЛЕНИВО.** Замерено V2 на копии
  боевой базы: в `sessions` РОВНО ОДНА строка (2026-09-10), при этом отметки о сдаче существуют
  на 2026-09-03 (53 события, 15 школьников). Занятие было, сдача была, столбца в журнале нет.
  Форма ответа одной строкой: «заводить sessions по расписанию» ИЛИ «оставить лениво и принять дыры».

- **[V2] Родов занятия в схеме ТРИ, а вы назвали ЧЕТЫРЕ.** `check (kind in ('обычное','зачёт',
  'отменённое'))`. «Контрольная» легла на «зачёт», «отменено» на «отменённое», «дополнительное»
  держать нечем — нужна миграция. Форма ответа: «добавить род дополнительное миграцией» ИЛИ «трёх хватит».

- **[V3] Кабинета ШКОЛЬНИКА не существует, и это новая страница, а не правка.** Сегодня
  `/kabinet` отказывает школьнику намеренно — единственная строка, которая держит вошедшего
  школьника от чтения чужих отметок. Вы просили «не делать нового функционала». Форма ответа:
  «делать школьный кабинет отдельной позицией» ИЛИ «пока не надо».

- **[V4] `<select>` исключён из проверки обрезки в гейте, и слепое пятно приходится ровно на то
  место, где вы жалуетесь четвёртый раз.** Адрес правки назван V3 точно: `tools/gejt_verstki.py`
  строки 167, 169, 644 — судить `<select>` по `selectedOptions[0]`. V1 этой ночью частично это
  сделала (мерит клон контрола), но исключение в трёх местах осталось. Форма ответа:
  «чинить гейт до вёрстки» ИЛИ «оставить как есть».

- **[V5] На НЕУЧЕБНОМ дне у преподавателя пропадает признак «мой школьник».** Замер V3 на базе:
  пятница 11.09 — строк «мои» 0 и галочки «только мои» нет вовсе; понедельник 14.09 — 69 строк.
  Пять дней в неделю кондуит не показывает преподавателю своих детей. Форма ответа: «показывать
  моих по ближайшему занятию» ИЛИ «так и задумано».

- **[V6] Ваш пример «у Бочаровой Анны 17 из 21» не воспроизводится.** Проверено V3 на базе:
  «Весь год» 9 класса даёт `1/33`, 8 класс `213/215`, числа `17/21` нет ни на одном разрезе.
  Знаменатель по устройству верен. Форма ответа: назвать ВКЛАДКУ, на которой вы это видели.

- **[V7] У Романчука подготовлено ДВЕ отметки (16A: 1а, 1б), а вы говорите про одиннадцать.**
  Перечень собран с ваших слов 10.09, бумаги у исполнителя не было. Форма ответа: продиктовать
  остальные девять (листок и номера задач) — команды на внесение уже написаны построчно.

- **[V8] `/privacy` и `/terms` красные по правилу «всё на один экран».** Это юридические
  документы, требование к ним не относится ни в каком смысле, но правило списка исключений
  жёсткое: в него попадает только то, что владелец назвал исключением ВСЛУХ. Форма ответа:
  «внести оба в исключения» ИЛИ «пусть краснеют».

- **[V9] Пароли школьников: дыры две, и вторая дороже первой.** (1) Файл
  `secrets/veb-lichnye-paroli.json` от 07.09 несёт 14 преподавателей, слово `shkolnik` — 0 раз.
  (2) `deploy/vykatka.sh:97` исключает `secrets/` из выкатки целиком — даже выпущенные пароли на
  сервер не попадут, и как они туда попадают, не решено нигде. Форма ответа: назвать способ
  доставки секретов на сервер, после чего выпуск делается отдельной позицией.


### ДОЛГ УСЛОВИЙ ЗАКОНА ЗАКРЫТИЯ — ЧЕТЫРЕ КРАСНЫХ, И КАЖДОЕ УЕЗЖАЕТ ИМЕНЕМ, А НЕ МОЛЧАНИЕМ

Прогон `check_zakon_zakrytiya.py` по этому мандату: выполнено 1 из 5, провалено 0,
НЕПРОВЕРЯЕМО 4. «Непроверяемо» — это не «чисто»: гейту нечем судить, и он говорит это вслух.
Поэтому исход волны — `CLOSED-S-DOLGOM`, и каждое незелёное условие названо позицией СЛЕДУЮЩЕЙ
волны, как того требует закон.

**ДОЛГ УСЛОВИЯ (а):** `V9-baza-volny-snimok` — снимать базовую линию долга ПЕРЕД подъёмом позиций и класть её в арку файлом `BAZA-VOLNY-*.json`, который гейт ищет; без неё условие (а) непроверяемо в каждой волне

Подробно: долг волны не вырос — СУДИТЬ НЕЧЕМ: в арке нет файла базовой линии
`BAZA-VOLNY-*.json`, то есть неизвестно, каков был долг ДО волны. Позиция следующей волны:
`baza-volny-snimok` — снимать базовую линию долга ПЕРЕД подъёмом позиций и класть её в арку
тем именем, которое гейт ищет. Пока файла нет, условие (а) будет непроверяемым в каждой волне.

**ДОЛГ УСЛОВИЯ (б):** `V10-dom-urokov-o-zahodah` — завести дом для уроков ПРО САМИ ЗАХОДЫ (кандидат `disciplina-zahod`) и внести туда семь перенесённых уроков поимённо; пока дома нет, судья придумывает адреса — в этой волне выдумал три

Подробно: правило с носителем — состав волны не назвал НИ ОДНОГО каталога
`skills/<имя>/`, то есть правил машине не адресовано. Это ровно то, что вскрылось в фазе знания
с другой стороны: судья придумал три несуществующих дома. Позиция следующей волны:
`dom-urokov-o-zahodah` — завести дом для уроков ПРО САМИ ЗАХОДЫ (кандидат `disciplina-zahod`)
и внести в него семь перенесённых уроков поимённо.

**ДОЛГ УСЛОВИЯ (в):** `V11-zhurnal-zahodov-mashine` — писать перезапуски позиций в машиночитаемый журнал; по этой волне перезапуск был ОДИН (V8 после смерти модели через 106 секунд), причина разовая, модель сменена — но машине это недоступно

Подробно: позиция по постоянной причине не перезапущена — гейт честно пишет, что
журнал заходов ему недоступен, и называет свою слепую зону: даже с журналом он судил бы НАЛИЧИЕ
перезапуска, а не постоянство причины. По этой волне ответ известен и записан здесь как факт:
перезапуск был ОДИН — V8 `shirina-prep-vdn` после смерти модели через 106 секунд, и причина была
РАЗОВАЯ (`UnknownError` провайдера), а не постоянная; модель при перезапуске сменили.
Позиция следующей волны: `zhurnal-zahodov-mashine` — писать перезапуски в машиночитаемый журнал,
чтобы (в) судилось, а не рассказывалось.

**ДОЛГ УСЛОВИЯ (г):** `V12-vlit-p7-delta-bazy` — влить инструмент `delta_bazy.py` (P7), которым условие (г) считает платные позиции против базовой линии; причины платных позиций V1–V4 записаны в шапках заходов, но машине недоступны

Подробно: причина платной позиции записана — гейт требует `delta_bazy.py` (P7),
инструмент не влит, поэтому «не измерено», а не «чисто». По этой волне причина каждой платной
позиции записана В ШАПКЕ её захода (V1–V4, дословные обоснования на месте), но машине это
недоступно. Позиция следующей волны: `vlit-p7-delta-bazy`.

**УСЛОВИЕ (д)** — единственное зелёное: причина записана.

### CLOSING PHASE — KNOWLEDGE BALANCE

> The four numbers below are the point of this section. `DELTA` is not
> stored, it is CHECKED: `--lint` recomputes `BORN` minus `CLOSED` and
> refuses a mismatch. `CARRIED` above zero REQUIRES the unjudged lessons
> to be listed BY NAME underneath — carried is lawful, silent is not.

**BORN:** `13`
**CLOSED:** `6`
**CARRIED:** `7`
**DELTA:** `7`

**a. HARVEST.** `urozhaj.py --sostav VOLNA-NOCH2-SOSTAV.txt --arka <арка>` → 8 файлов из 8 на
месте, уроков 9, все девять С ЦЕНОЙ (на доработку по форме — ноль). К ним добавлены ЧЕТЫРЕ урока
самого оркестратора, собранные из журнала волны, как и велит пункт «a» (из `kod_*` И из журнала).
Итого BORN = 13.

**b. JUDGE.** Судила СВЕЖАЯ БЕСПЛАТНАЯ модель, не автор ни одного урока, одной партией из 13.
Дошло не с первой попытки, и это часть отчёта: `nemotron-3-ultra:free` промолчала (пустой ответ),
`poolside/laguna-s-2.1:free` вернула `temporarily rate-limited upstream`, ответила третья —
`thinkingmachines/inkling:free`. Вердиктов 13: ПРАВИЛО — 11, ДОЛГ — 2, отклонено — 0.

🔴 **И ТУТ ЖЕ ПРОВЕРКА САМОГО СУДЬИ, БЕЗ КОТОРОЙ ЕГО ВЕРДИКТ БЫЛ БЫ ПУСТЫМ ЗВУКОМ.** Судья
назвал дома — я проверила КАЖДЫЙ на диске. Из пяти названных скиллов существуют ДВА:
`skills/disciplina-priyomka/SKILL.md` и `skills/disciplina-orkestrator/SKILL.md`. Трёх других —
`skills/gejt-vse-ekrany`, `skills/zhurnaly-i-kabinet`, `skills/konduit-i-raspredelenie` — НЕ
СУЩЕСТВУЕТ: судья их выдумал по имени позиции. Правило, отправленное в несуществующий дом, не
правило, а надежда (`skills/disciplina-kachestvo/SKILL.md`), и засчитывать его закрытым значило
бы соврать в ту же сторону, в какую врали все девять ложно-зелёных этой ночи.

**c. RULES TO CARRIERS.** ЗАКРЫТО ШЕСТЬ — те, у кого дом существует и носитель назван:
* четыре урока оркестратора → `disciplina-priyomka` (объект замера спрашивается у проекта:
  `Makefile`, цель `check`) и `disciplina-orkestrator` (событие-развязка в правиле порядка ·
  влитие ветки как обязанность оркестратора, а не последнего хода модели · будильник головы);
* два ДОЛГА с реальными адресами: `tests/veb/test_istoria_zanyatij.py` (дата занятия в фикстуре
  выводится из `SLOTY_ZANYATIJ`, а не из «сегодня минус N») и `UROKI-FABRIKE.md` (сторож
  оркестратора коммитит чужую зону своим сообщением).

**d. BALANCE.** BORN 13 − CLOSED 6 = CARRIED 7. Волна закрыла знания меньше, чем родила, и это
названо числом, а не настроением.

_Carried by name (one line each, or the single word `none`):_
1. `gejt-vse-ekrany`: входной документ захода жил только в главной папке, а работать велено в worktree — дом не заведён
2. `gejt-vse-ekrany`: пара «сломано → починено» на ЖИВОМ дефекте зеленеет ровно до дня починки — дом не заведён
3. `gejt-vse-ekrany`: правка после выдачи доехала до исполнителя глазами, а не механизмом — дом не заведён
4. `gejt-vse-ekrany`: самопроверка объявляла поломку нанесённой, не спросив, попала ли она в то, что проверка судит — дом не заведён
5. `zhurnaly-i-kabinet`: заход назвал ВХОДОМ разделы, которых в названном файле нет вовсе (файл кончается на `K3`) — дом не заведён
6. `konduit-i-raspredelenie`: задачу сузили после сборки, а КРИТЕРИЙ ГОТОВНОСТИ сузить забыли — дом не заведён
7. `konduit-i-raspredelenie`: файл-ВХОД назван по имени, а в рабочей папке лежит его СТАРАЯ редакция — дом не заведён

Всем семи нужен ОДИН И ТОТ ЖЕ ход, и он назван здесь как следующая работа: у волны-фабрики нет
дома для уроков ПРО САМИ ЗАХОДЫ (не про оркестратора и не про приёмку). Пока его нет, судья будет
придумывать адреса, а уроки — переноситься из волны в волну. Кандидат-дом: `disciplina-zahod`.

### LINE-BY-LINE ANSWER TO EVERY FINALIZED ITEM

Восемь пунктов, восемь ответов — ниже, каждый со способом проверки.

> One line per finalized item, and every item of the top half must get one: `done` or `not done` with the reason. This field is the point of the whole artifact.
- [F1] `сделано` — нового функционала не строили: восемь позиций ПОДКЛЮЧАЛИ написанное. Проверка не на слово: main после волны даёт 26 упавших тестов против 29 до неё при 1313 прошедших против 1266 — то есть стандартный функционал стал работать лучше, а не появился новый.
- [F2] `сделано (не делали)` — внесение задач диалогом не тронуто ни одной позицией; `git log 457342e..main` не содержит ни одного коммита об этом.
- [F3] `сделано (не делали)` — бот не поднимался. Единственное касание Telegram за ночь — `getMe` по ALERT_TOKEN часового, и то на приёмке V6, чтобы доказать, что канал звонка жив (HTTP 200).
- [F4] `сделано` — V4 `offlajn-ochered` влита: отметка попадает в очередь в момент касания, отказ переживает перезагрузку, чтение из снимка. Перегнано оркестратором: `pytest tests/veb/test_offlajn_ochered.py tests/veb/test_offlajn_brauzer.py` → 19 passed. Полный локальный сайт со второй базой НЕ строился — как и запрещено.
- [F5] `сделано` — V2 влита: два ЖУРНАЛА, не две вкладки одного. Её же находка объясняет, почему это не косметика: вкладки были ПЛЕМЯННИКАМИ, а не братьями, и обе таблицы не показывались НИКОГДА. Слово «история» осталось в адресе `/istoria` и имени модуля — названо вопросом [V-?] и требует отдельной позиции, потому что задевает `veb/server.py` и каждую ссылку сайта.
- [F6] `сделано` — V8 `shirina-prep-vdn`: `flex:0 0 11rem;max-width:11rem` для групп В/Д/Н против прежних 8.6rem, обе версии, левый край не двинут. Влитие доделал оркестратор (`f5a0d99`), потому что позиция вышла раньше последнего хода.
- [F7] `сделано` — дизайн не отдан ни одной бесплатной модели: V1–V4 работали на Opus 5. Больше того, когда ТРИ бесплатные модели из четырёх оказались несуществующими на раздаче, а потом одна из замен умерла через 106 секунд, ни одна позиция не была молча поднята на Opus — перевыбиралась БЕСПЛАТНАЯ, и каждая замена записана в шапке своего захода с причиной.
- [F8] `сделано частично` — V7 закрыла человекочитаемость двери (`9a43f89`: внятные отказы, понятный список задач, объяснение пробы), и это ровно то, что F8 просит. НО отчёта она не написала (плейсхолдеры), и это её доработка. Само внесение отметок не выполнено ЗАКОННО: боевой базы на машине нет (замер 00:36), а в копию владелец вносить запретил.


---

# ЦИКЛ ОРКЕСТРАТОРА — ВПИСАН РУКАМИ, ГЕНЕРАТОР ЕГО НЕ ВЫДАЁТ (класс Д1 рефлексии)

> 🔴 Это самая дорогая дыра генератора мандатов: без цикла голова изобретает порядок заново
> каждую волну. Ниже — семнадцать пунктов, собранных из ТРИДЦАТИ ТРЁХ классов отказов
> `REFLEKSIA-ORKESTRATOROV.md`. Каждый пункт оплачен, ни один не выдуман.

**1. ПЕРВЫЕ ДЕСЯТЬ МИНУТ.** Запусти V1 `gejt-vse-ekrany` — и ТОЛЬКО его. Остальные семь позиций
трогают то, что владелец судит глазами, а принимать это должно чем-то, что не молчит. Утром
10.09 сработал ровно этот порядок: сначала гейт (G0), потом всё, что он ловит. Дождись, пока V1
даст первый коммит, и лишь затем поднимай V2–V8 одной пачкой.

**2. 🔴 ПУТИ В ЗАХОДАХ УЖЕ ПОЧИНЕНЫ АНАЛИТИКОМ. НЕ СВЕРЯЙ ИХ С ГЕНЕРАТОРОМ.** Генератор восемь
раз из восьми выдал пути песочницы (`/sessions/...`, 204 вхождения) и восемь раз напечатал «пути
не подменялись». Все заменены на `/Users/ivanyakovlev/Documents/GitHub/...`, проверено грепом:
ноль. Если увидишь песочный путь — это твоя находка, а не норма; чини и назови.

**3. ВХОДНОЙ РИТУАЛ §0.1 В КАЖДОМ ЗАХОДЕ ОТМЕНЁН красной строкой поверх.** Не возвращай его.
Ночью 10.09 он съедал прогон целиком: одиннадцать позиций из двенадцати не дошли до задачи.

**4. МОДЕЛЬ ЖИВЁТ В ШАПКЕ СВОЕГО ЗАХОДА, И БОЛЬШЕ НИГДЕ.** В составе волны колонки «позиция →
модель» нет намеренно: 10.09 имя модели жило в пяти домах, провайдер снял её с раздачи,
поправили в одном — волна работала в пустоту.

**5. 🔴 ДИЗАЙН НЕ ОТДАЁТСЯ БЕСПЛАТНЫМ МОДЕЛЯМ.** Решение владельца 10.09. V1–V4 на Opus, V5–V8
на бесплатных. Если бесплатная модель на V5–V8 выгорела — перевыбери БЕСПЛАТНУЮ, не поднимай
позицию на Opus молча.

**6. КОММИТ ПЕРВЫМ, ОТЧЁТ ВТОРЫМ.** Требование владельца дословно: «чтобы всегда все заходы, и
платные и бесплатные, все коммитили — чтобы если вдруг всё отвалится, всё бы выжило».

**7. 🔴 У ПЛАТНОЙ ДВЕРИ АВТОСОХРАНЕНИЯ НЕТ. КОММИТЬ ЧУЖИЕ РАБОЧИЕ ПАПКИ САМА.** 10.09 ты спасла
так 95 строк и ещё один полуфабрикат; в обоих случаях позиция подхватила твой коммит и дописала
к нему обоснование. Помечай такие коммиты словами «СОХРАНЕНИЕ ОРКЕСТРАТОРОМ».

**8. ОТЧЁТНАЯ СТРОКА КРУГА КАЖДЫЕ 15–20 МИНУТ, ВРЕМЯ ИЗ `date` В ТОТ ЖЕ ХОД.** 10.09 ты дважды
датировала строку вперёд и один раз отстала журналом на полтора часа при живых коммитах. Журнал,
датированный вперёд, перестаёт быть свидетельством — именно этим он и ценен. Форма строки:
`ЧЧ:ММ · круг N · запущено · принято · без вердикта · main зелёный (число) · выкачено до ·
не в git · смотрел глазами · ЗАКРЫТО X из Y`.

**9. 🔴 «НОЛЬ НАХОДОК» ОЗНАЧАЕТ «НЕ СМОТРЕЛ», ПОКА НЕ НАЗВАН ОХВАТ.** Пять лиц этого класса за
сутки: гейт не видел узла · гейт не знал правила · гейт не ходил на экран · `<select>` был
исключён из проверки · правило CSS не совпало ни с чем. Требуй у каждой позиции ОХВАТ рядом с
числом: «проверено X из Y», и у ПОЛОЖИТЕЛЬНОГО вердикта тоже.

**10. ЧИСЛО ОТЧЁТА ПЕРЕГОНЯЙ САМА, НА ЖИВОМ ОБЪЕКТЕ.** Не «числа сходятся», а «число
воспроизведено командой». И оба конца сверки снимай ОДНИМ ходом: 10.09 ты сравнила замер базы со
снимком страницы, снятым минутами раньше, и объявила дефект, которого не было.

**11. ЗАКРЫТЫЕ ЗАЯВКИ ЧИТАЙ ТОЖЕ.** Ты объявила «живой токен бота» по открытой заявке, не
посмотрев в `zayavki/sdelano/`: токен был отозван владельцем 08.09, проверено `getMe → 401`.
Владелец сходил в BotFather зря. И `git_zona.py --vsyo-ravno` печатает только ПЕРВУЮ открытую
заявку — их было тринадцать; читай все.

**12. 🔴 БАЗА ВНЕ GIT — РАБОТА С ДАННЫМИ КОММИТА НЕ ОСТАВЛЯЕТ.** Гейт «работа доехала в git»
стоит первым во всей приёмке и данные больше НЕ покрывает. Свидетелем служит `SvidetelRaboty`:
дата последней записи ДО и ПОСЛЕ и число строк. Требуй его у V7. Без него 10.09 аналитик объявил
внесённые отметки невнесёнными.

**13. ИСТОЧНИК НАЗЫВАЕТСЯ РЯДОМ С ЧИСЛОМ, ВСЕГДА.** Пять промахов аналитика за сутки — один
класс: величина или причина названа БЕЗ источника. Дверь `core/istochnik.py` теперь сама говорит
путь, дату последней записи и вердикт свежести. Зови её и требуй у позиций.

**14. МЕХАНИЗМ СУЩЕСТВУЕТ ≠ МЕХАНИЗМ СРАБОТАЛ ЗДЕСЬ.** Аналитик нашёл в живом коде стройную
причину «правка слетала», проверил каждое звено — и ошибся: владелец делал другое, а причина была
в сети. Прежде чем объяснять симптом, спроси одной строкой, что человек делал руками.

**15. ЧАСОВОЙ 10.09 НЕ ЗАМЕТИЛ ДВЕ СМЕРТИ ГОЛОВЫ** (13:29:45 и 16:02:26) — печатал «сердце
молчит» и не эскалировал. Это чинит V6. Пока не починено — **сама пиши в отчётную строку, сколько
минут молчит сердце**, и не полагайся на будильник.

**16. АУДИТ АВТОНОМИИ В ПЕРВЫЕ ПОЛЧАСА.** Пока владелец ещё отвечает — назови ему всё, чего тебе
не хватает для работы до утра. После полуночи спрашивать будет некого.

**17. НИЖНЯЯ ПОЛОВИНА ЭТОГО МАНДАТА — ПОСЛЕДНИЙ ХОД ВОЛНЫ, И ОН НЕ ФАКУЛЬТАТИВЕН.**
`BOTTOM_HALF_STATUS: PENDING` висел две волны подряд. Закрывающая сессия читает МАНДАТ, а журнал
круга не читает по устройству: без нижней половины свидетельства о волне не существует там, где
его будут искать. Форма — ЧАСТЬ Г в `REFLEKSIA-ORKESTRATOROV.md`; классы 1–33 уже там, твой отчёт
встанет рядом.

# РЕЕСТР ОТКАЗОВ — ЧТО УЖЕ СЛОМАНО И ЧИНИТЬ ЗАНОВО НЕ НАДО

| что | состояние |
|---|---|
| стартовая строка генератора зовёт `orkestr.py` внутри `spetsmat-bot`, где его нет | заменена на `ZAPUSK-ZAHODA.sh` во всех заходах |
| `worktree add … &&` неидемпотентен | `ZAPUSK-ZAHODA.sh` судит по ФАКТУ наличия папки |
| входной ритуал §0.1 съедает прогон | отменён красной строкой в каждом заходе |
| у платной двери нет автосохранения | коммитишь сама, пункт 7 выше |
| ARN Bedrock в строке запуска при отсутствии кредов | развилка вшита в `ZAPUSK-ZAHODA.sh` |
| потолок фоновых задач снимает заход, ждущий верификатора | снят в `ZAPUSK-ZAHODA.sh` |
| песочные пути в заходах | заменены аналитиком, 204 вхождения, проверено грепом |

# ЧТО ДЕЛАТЬ, ЕСЛИ ПОЗИЦИЯ МОЛЧИТ

Пауза 45 секунд, до трёх попыток; время меряй `date`, не суммой своих `sleep`. После третьей —
работай без неё и напиши это ОТДЕЛЬНОЙ строкой в отчёт, а не молчи. Молчание неотличимо от
работы: ровно поэтому «окон заходов 0» у часового ничего не значит — работа доказывается
КОММИТАМИ, а не числом окон.
