# MANDATE — volna-noch2

<!-- assembled by bootstrap_mandate.py; two halves, two authors; do not merge them -->

**STATUS:** `OPEN`
**TOP_HALF_STATUS:** `COMPLETE`
**BOTTOM_HALF_STATUS:** `PENDING`
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

> Not written yet: the wave has not returned. STATUS stays `OPEN` until it has, and
> `--lint` says so out loud instead of passing in silence.

### WHAT WAS ASSEMBLED AND LAUNCHED

<NOT FILLED>

### WHAT IT REPAIRED ITSELF AND WHY IT WAS BROKEN

<NOT FILLED>

### VERDICTS

<NOT FILLED>

### WHAT WAS EXCLUDED AND WHY

<NOT FILLED>

### IRREVERSIBLE ACTIONS

<NOT FILLED>

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

<NOT FILLED>

### CLOSING PHASE — KNOWLEDGE BALANCE

> The four numbers below are the point of this section. `DELTA` is not
> stored, it is CHECKED: `--lint` recomputes `BORN` minus `CLOSED` and
> refuses a mismatch. `CARRIED` above zero REQUIRES the unjudged lessons
> to be listed BY NAME underneath — carried is lawful, silent is not.

**BORN:** `<NOT FILLED>`
**CLOSED:** `<NOT FILLED>`
**CARRIED:** `<NOT FILLED>`
**DELTA:** `<NOT FILLED>`

_Carried by name (one line each, or the single word `none`):_
<NOT FILLED>

### LINE-BY-LINE ANSWER TO EVERY FINALIZED ITEM

<NOT FILLED>

> One line per finalized item, and every item of the top half must get one: `done` or `not done` with the reason. This field is the point of the whole artifact.
- [F1] <NOT FILLED>
- [F2] <NOT FILLED>
- [F3] <NOT FILLED>
- [F4] <NOT FILLED>
- [F5] <NOT FILLED>
- [F6] <NOT FILLED>
- [F7] <NOT FILLED>
- [F8] <NOT FILLED>


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
