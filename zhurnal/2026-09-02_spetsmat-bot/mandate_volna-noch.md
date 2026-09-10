# MANDATE — volna-noch

<!-- assembled by bootstrap_mandate.py; two halves, two authors; do not merge them -->

**STATUS:** `OPEN`
**TOP_HALF_STATUS:** `COMPLETE`
**BOTTOM_HALF_STATUS:** `PENDING`
**ARC:** `zhurnal/2026-09-02_spetsmat-bot`
**JOURNAL:** `zhurnal/2026-09-02_spetsmat-bot/ZHURNAL-ORKESTRATORA-NOCH.md`
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

By the morning of 10.09 the spetsmat site answers the owner's eight layout complaints and the conduit shows what it already computes — before the lesson on Thursday at 13:10

### INTERVIEW — RENDERED IN ENGLISH FROM A RUSSIAN CONVERSATION — 2026-09-10

> **ИНТЕРВЬЮ ПРОВЕДЕНО** (flag `--intervyu da` at assembly). ⚠ The flag proves the
> assembler was asked, not that the conversation happened — same honest limit
> `bootstrap_zahod.py --intervyu` already prints. ⚠ The interview was held in
> Russian and what is recorded here is the ENGLISH RENDERING of the settled
> meaning, not a quotation. A rendering can be wrong, and only the owner can
> say so.

- **Q1** — Q: Q1
  — M: The night is one wave of twelve positions run by an orchestrator, not a list the owner launches by hand; he is asleep while it runs
- **Q2** — Q: Q2
  — M: Deployment to the live server happens after EVERY position during the night, not once in the morning, so a break is visible immediately
- **Q3** — Q: Q3
  — M: Free models are the default everywhere; a paid model is an escalation for one position after two consecutive free failures, and the reason is written down
  — note: The owner asked for free models to the maximum but named no numeric threshold; two consecutive failures is the analyst reading and may be tightened
- **Q4** — Q: Q4
  — M: The queue order is binding: the layout gate, the task kinds and the pupil card are foundations that later positions read
- **Q5** — Q: Q5
  — M: Position twelve, pupil passwords, is conditional and runs only if everything before it is green by morning
  — note: The owner gave both readings on the same recording and settled it as conditional-last during the interview
- **Q6** — Q: Q6
  — M: Nothing may break: reliability outranks features, and on conflict the feature is cut

### FINALIZED AT INTERVIEW — 2026-09-10

- [F1] The ceiling is five pupils per receiving teacher; the sixth turns red on screen and is refused on write
- [F2] Assigning a pupil to a teacher on a day that teacher does not come is forbidden hard: the teacher is absent from the list that day
- [F3] Conduit tabs run: Whole year, Grobarij, then the sheets; the newest sheet opens by default, determined by a command against the database. Class buttons 8 then 9, with 9 open
- [F4] A written kind of task is introduced and filled from the dagger mark in the sheet PDFs; circle, cross and star are visible in the conduit itself
- [F5] The date of submission is visible at the tick; cell history opens by gesture only; taps reversed within 60 seconds do not enter statistics; journal events are never deleted
- [F6] All four conduit statistics are reconciled against the live database by direct SQL, and both numbers are printed side by side
- [F7] Search leads to the group page; the pupil card shows a guest only the top and a logged-in teacher the ticks; this card is the future personal page of the pupil
- [F8] A Lessons History tab: pupils and teachers against lesson dates, hover reveals who received the work
- [F9] Teacher login leads to a separate Kabinet tab; the Next Spetsmat block is twice as large; a future absence mark freezes the distribution for that date
- [F10] Task entry works through all three channels — text, photo, voice — via a hypothesis confirmed by a human; writing without confirmation is forbidden
- [F11] The layout gate turns red on truncation, on a needless line wrap and on horizontal scroll; every pupil of a group fits on one screen
- [F12] Position P12 is conditional: it runs only if P2 through P11 are green by morning
- [F13] Break nothing: pytest not below entry, backups and security do not degrade — on conflict the feature is cut, not the reliability

### BOUNDARIES AND WHAT IS ALREADY CLOSED

- The Telegram bot is OUT of this wave — the owner said it in as many words: the bot is definitely not for tomorrow
- Grobarij is built as an empty tab; there is nothing to fill it with until Monday, when the current sheet becomes historical
- Passwords are not distributed to pupils over Telegram: the owner hands them out in person
- The pupil personal page is not built as a separate tab: it arrived as the card in position P8
- 🔴 NOT TONIGHT — THE SPEED OF SAVING THE DISTRIBUTION. The owner named it at 02:0x and the diagnosis is already written into `PLAN.md`, section СКОРОСТЬ: the client sends one POST per edit in a sequential loop (`veb/obshchee/karkas.py:738-745`), and the server rebuilds the whole public page on every POST (`veb/server.py:897`). It is a real defect and it is NOT a position of this wave: it touches the client, the server and the transactional guarantee of a page fifteen people will use on Thursday at 13:10. Do not fix it in passing while doing P4, and do not parallelise those requests — the sequence stops on the first refusal ON PURPOSE, so that half the edits are never left applied. If you touch that save path for another reason, say so in the report and change nothing about its timing.
- ALREADY CLOSED, do not rebuild: the privacy and terms pages, the nightly database archive to Google Drive, the site watchdog, and the distribution column alignment shipped on 09.09

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

**ЗАКРЫВАЮЩАЯ ПОЗИЦИЯ:** `ZK1` — zakon-zakrytiya-volna-noch

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
ZK1|zakon-zakrytiya-volna-noch|opus|zhurnal/2026-09-02_spetsmat-bot/mandate_volna-noch.md|pryamoj
```

### SCALE

Twelve positions, one night, deadline 11:00 on 10.09. Free models everywhere by default; a paid model is an escalation for a single position after two consecutive free failures, with the reason written down. At most two positions in parallel, never two on the same model.

### WHAT COUNTS AS FAILURE

The wave has failed if, at the deadline: (a) pytest on main is BELOW the entry number taken by command before the first position; (b) the live site math-kluychiki.ru does not answer 200 on the front page, the distribution page or the conduit; (c) the mandate holds a position with no verdict and no named reason for the absence. A doorabotka verdict does NOT count as failure.

## ЦИКЛ ОРКЕСТРАТОРА — по-русски, потому что исполнять его тебе

> Этого раздела не было ни в одном прошлом мандате: цикл жил в скилле по ссылке, и каждая
> волна восстанавливала его заново. Здесь он записан целиком, потому что носитель — тот файл,
> который читают, а не тот, на который ссылаются.

### Круг — единица твоей работы

Один круг: бей сердце → сними состояние → запусти, что можно запустить → проверь живых →
прими вернувшихся → запиши дневник → взведи будильники заново. Круг короче двадцати минут.

**1. СЕРДЦЕ.** `date >> <арка>/SERDCE-VOLNY-noch.md` при КАЖДОМ обращении к bash, а не раз в круг.
Ход бывает длиннее порога простоя, и тогда молчание сердца не отличает «думаю» от «умер».

**2. СОСТОЯНИЕ.** Пиши `SOSTOYANIE-VOLNY-noch.md` каждый круг, строкой на позицию:
id · тема · модель · pid · старт · последний коммит N минут назад · вердикт. **Строка про себя
самого — обязательна**, включая долю времени, ушедшую в починку собственной оснастки.

**3. ЗАПУСК ПОЗИЦИИ.** Только через оркестратор, в фоне, и ТОЛЬКО с АБСОЛЮТНЫМ путём арки:

```
python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/orkestr.py \
  /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/zhurnal/2026-09-02_spetsmat-bot \
  --rezhim progon --zahody kod_<тема>.md --molchanie 420 --potolok 3600 \
  --popytok 3 --avtosohranenie 600
```

🔴 **Абсолютный путь — не стиль, а условие надзора.** Часовой считает твои окна образцом
`orkestr.py <АБСОЛЮТНЫЙ путь арки>`; с относительным путём он увидит ноль окон при живой работе,
и «окон стало меньше» превратится в ложный звонок приёмки.

Параллельно не больше двух позиций и никогда две на одной модели. Порядок очереди из состава
обязателен: P2 кладёт гейт вёрстки, P5 виды задач, P8 карточку школьника — на них стоят следующие.

**4. ЖИВОСТЬ.** Три разных смерти, снаружи одинаковые, и различает их только продукт:
* **лог пуст, ни байта** — команда умерла ДО движка: чини команду, модель НИ ПРИ ЧЁМ;
* **лог не растёт дольше 420 с при живом процессе** — молчит: снимай по PID и перевыбирай модель;
* **rc=0, а файл-заход не тронут** — ложный успех: движок напечатал ошибку и вышел нулём.

Признак жизни бери из ПРОДУКТА — коммиты ветки захода и отпечаток зоны, — а лог считай
вспомогательным: молчание лога при живых коммитах не смерть.

**5. ПРИЁМКА.** Гейт 0 ПЕРВЫМ ходом, ДО чтения отчёта:
`git_zona.py check --zone <зона позиции>` — красный, и отчёт не принимается, что бы в нём ни было.
Потом **прогони критерий САМ**, а не читай про него: замерено — две минуты против восьми.
Числовые утверждения отчёта перегоняй командой. Вердикт вписывай дверью, а не руками:

```
python3 .../bootstrap_mandate.py --append-verdict <арка>/mandate_volna-noch.md \
  --pass kod_<тема>.md --verdict ПРИНЯТО|ДОРАБОТКА|ОТКЛОНЕНО --reason "одной строкой почему"
```

**6. ВЛИТИЕ — делает САМ ЗАХОД последним ходом, не ты.** Твоё дело проверить, что влилось,
и что `main` после влития ЗЕЛЁНЫЙ: `pytest -q` не ниже входного числа. Две по отдельности
зелёные позиции вместе дают красный `main` через общий стык, за который не отвечает никто —
это случалось трижды, и гейт зон этого не видит по построению.

**7. ВЫКАТКА — после КАЖДОЙ принятой позиции**, `bash deploy/vykatka.sh`. Скрипт сам откажется
во время занятия. Живую страницу суди РАЗМЕРОМ и СОДЕРЖИМЫМ ответа, а не кодом 200: «200» уже
дважды означал заглушку чужого сервиса.

**8. ДОРАБОТКА.** Вердикт «доработка» — нормальный исход, не провал. Перезапускай ту же позицию
тем же способом: заход прочитает свои `## ПЛАН` и `## ОТЧЁТ` и продолжит.
🔴 **В `kod_*.md` ЖИВОЙ позиции не писать.** Два писателя в один файл стоили трёх позиций из
пяти за один вечер. Правку клади в `## ПРАВКИ ПОСЛЕ ВЫДАЧИ` и только когда процесс мёртв.

**9. ПЕРЕПИСЫВАТЬ БУДУЩИЕ ЗАХОДЫ — ТВОЁ ПРАВО И ТВОЯ ОБЯЗАННОСТЬ.** Позиция вскрыла, что
предпосылка следующей неверна, — правь её файл (процесс мёртв) и запиши в дневник с ценой.
Новый заход заводится ТОЛЬКО генератором `bootstrap_zahod.py` с `--grjaznaya-arka-prichina`;
руками файл-заход не пишется — теряются контракт зоны, гит-контур и стартовая строка.

**10. ЛЕСТНИЦА МОДЕЛЕЙ.** Бесплатная везде. Платная — эскалация ОДНОЙ позиции после ДВУХ
подряд отказов, и причина пишется в дневник. Проба живости бесплатной модели ЕСТЬ ЕЁ РАСХОД:
не проверяй пул «на всякий случай».

**11. КОГДА ЗВАТЬ ВЛАДЕЛЬЦА.** Он спит; будить его нечем и незачем. Всё, что требует ЕГО
решения, идёт в раздел `QUESTIONS TO THE OWNER` нижней половины — это единственная законная
форма «не смог, потому что решение не моё». Исключение одно: сайт лёг и не поднимается.

**12. ЗАКРЫТИЕ ВОЛНЫ — твой последний ход, а не отдельная позиция.** Фаза знания, нижняя
половина, `STATUS: CLOSED`. Закрывающей позиции в составе нет намеренно: объявленная в составе
позиция без файла на диске держала голову шестьдесят кругов подряд.

**13. РЕФЛЕКСИЯ — отдельный файл и отдельная обязанность, не часть дневника.**
`REFLEKSIA-ORKESTRATOROV.md` в этой же папке переживает волны: он про устройство ГОЛОВЫ, а не
про ход ночи. В нём уже лежат двенадцать классов твоих отказов с ценой и рычагом, десять
механизмов, которые НЕ ломаются, и пять честно открытых мест. Прочитай части А и Б ДО первого
запуска: это карта того, где ты сломаешься сегодня.
🔴 **ДО закрытия волны заполни часть Г — пять блоков дословно теми заголовками.** Владелец
10.09: оркестратор обязан накопить уроки и ЧЁТКО сообщить аналитику, чтобы тот дописал. Последний
блок называется «АНАЛИТИКУ ДОПИСАТЬ», и он не риторический: строка на пункт, каждая с адресом
дома. У каждой записи — `ЦЕНА` числом, `ДОМ:` и `ДОСТАВЛЕНО: нет`; пары ДОМ/ДОСТАВЛЕНО считает
`schet_nezakrytogo.py`, запись без них теряется молча.

**14. ПЕРВЫЙ ХОД ВОЛНЫ — КОММИТ, И ЭТО НЕ ФОРМАЛЬНОСТЬ.** Сборка волны (мандат, оснастка,
двенадцать заходов, состав) на момент твоего старта ЛЕЖИТ ВНЕ GIT: аналитик из песочницы
коммитить не может, а команда владельца отвергнута — флаг `--zone` берёт ОДНО значение, и
`README.md` вторым аргументом ушёл посторонним. Заявка лежит в очереди
(`git_zona.py zayavki`, род `git-operaciya`, операция `kommit`). Исполни её ДВУМЯ отдельными
командами и закрой:
```
git_zona.py commit --zone zhurnal/2026-09-02_spetsmat-bot -m "..." --push
git_zona.py commit --zone README.md -m "..." --push
```
README обязан уехать: без него мандат становится документом-сиротой — ворота читают раздел 6
с диска, а не из индекса, и коммит без него пройдёт ЗЕЛЁНЫМ.

**15. РИТМ ОТЧЁТА — КАЖДЫЕ ДВАДЦАТЬ МИНУТ, ТРИ НОСИТЕЛЯ, НЕ ОДИН.** Требование владельца 10.09:
«должно быть всё заведено так, чтобы он просыпался каждые 20 минут и писал небольшой кусочек
отчёта». Один носитель — не отчёт: файл может не обновиться, и молчание будет неотличимо от
работы. Пиши ВСЕ ТРИ, и они разные по назначению:

| носитель | что туда | как часто |
|---|---|---|
| `## ДНЕВНИК ОРКЕСТРАТОРА` в этом мандате | ОДНА строка круга по форме из раздела | каждый круг, не реже 20 минут |
| `SOSTOYANIE-VOLNY-noch.md` | строка на позицию плюс строка ПРО СЕБЯ | переписывается целиком каждый круг |
| `ZHURNAL-ORKESTRATORA-NOCH.md` | находка с `ЦЕНА` числом и `ПРО ГОЛОВУ` | на каждую находку, не по расписанию |

🔴 **ЧИНИЛ СВОЮ ОСНАСТКУ — ЗАПИСЬ В ЖУРНАЛ ОБЯЗАТЕЛЬНА, И ЭТО НЕ БЮРОКРАТИЯ.** Замер снаружи
10.09 00:55: ты за первые семь минут нашёл и починил настоящий дефект — глоб `kod_*.md` брал
71 файл-заход восьми прошлых волн, и все три будильника вышли за минуту, то есть механизм,
который ОДИН умеет будить живую голову, был мёртв с первой минуты волны. Починка отличная.
Записи о ней нет НИГДЕ: ни в журнале, ни в рефлексии. Находка без записи не существует —
через две недели никто не вспомнит, почему в будильнике появился `VOLNA-POZICII`, и глоб
вернётся первым же «упрощением». ЦЕНА этого класса уже оплачена: правило «не убивать чужие
процессы» жило в тексте и не сработало, потому что было текстом, а не формой команды.

**16. АВТОНОМИЯ — ПРОВЕРИТЬ, ПОКА ВЛАДЕЛЕЦ ЕЩЁ НЕ СПИТ.** После того как он уснёт, вопросов
задавать НЕКОМУ, и «остановился, потому что нужно решение» будет означать потерянную ночь.
Прогони этот список СЕЙЧАС, одним ходом, и всё, чего не хватает, спроси ОДНИМ сообщением:

1. **Права.** Пройдёт ли у тебя команда, которой ты ещё не пользовался, без запроса
   подтверждения? Ты уже делал `nohup`, коммит и правку файлов — значит эти классы открыты.
   Непроверенные: выход в сеть, `ssh`, запуск чужого движка.
2. 🔴 **ВЫКАТКА — САМОЕ ОПАСНОЕ МЕСТО, потому что она стоит в критерии ВСЕХ ДВЕНАДЦАТИ позиций.**
   `deploy/vykatka.sh` ходит `ssh -o BatchMode=yes`: при запертом ключе она не спросит пароль,
   а откажет мгновенно — и двенадцать позиций подряд будут «сделаны, но не доехали».
   Проверь ДВУМЯ холостыми прогонами, они ничего не трогают:
   `bash deploy/vykatka.sh --proba --chas-zanyatia` (обязан ОТКАЗАТЬ, rc=3) и
   `bash deploy/vykatka.sh --proba --svobodnyj-chas` (обязан пройти, rc=0).
   Плюс одна живая проба связи с сервером. Ключ заперт — это ВОПРОС ВЛАДЕЛЬЦУ, и задать его
   надо СЕЙЧАС, а не в три часа ночи.
3. **Секреты.** `secrets/` на диске: `bot.env`, ключ сервисного аккаунта, пароли. Хватает ли их
   позиции P11 (фото и голос ходят во внешние API)? Нет ключа — спроси сейчас.
4. **Переменные окружения сервера.** Без `SPETSMAT_VEB_SECRET` локальный сервер не стартует
   вовсе — это условие запуска, а не дефект позиции.
5. **Движок и лимиты.** `opencode` установлен и отвечает? Бесплатный пул жив? Чем платить, если
   к утру бесплатные кончатся, — и разрешена ли тебе платная модель без спроса (да, разрешена:
   эскалация после двух отказов, пункт 10, причина в журнал).
6. **Место и квоты.** Хватит ли диска на двенадцать рабочих папок.

🔴 **ПОСЛЕ ЭТОГО СООБЩЕНИЯ ВОПРОСОВ НЕ ЗАДАВАТЬ.** Всё, что осталось неясным, идёт в
`QUESTIONS TO THE OWNER` нижней половины и НЕ останавливает работу. Отказ инструмента — задача,
а не исход: обойди, запиши цену, иди дальше. Единственное исключение, при котором ты будишь
владельца, названо в пункте 11: боевой сайт лёг и не поднимается.

**17. 🔴 СОХРАННОСТЬ РАБОТЫ — КАЖДАЯ ПОЗИЦИЯ КОММИТИТ ПО ТАЙМЕРУ, НЕЗАВИСИМО ОТ КАНАЛА.**
Требование владельца 10.09 дословно: «важно, чтобы всегда все заходы — и платные, и бесплатные —
всё коммитили, чтобы если вдруг всё отвалится, всё бы выжило».

**ДЫРА ИЗМЕРЕНА СНАРУЖИ 10.09 01:55, И ОНА РОВНО ТАМ, ГДЕ СЕЙЧАС ИДЁТ ВСЯ РАБОТА.**
Разница между дверьми не в том, что одна про коммит молчит, а в том, ЧЕЙ это коммит.
* **Бесплатная дверь** (`orkestr.py`) несёт МЕХАНИЗМ: `--avtosohranenie` коммитит зону САМ, по
  таймеру и перед каждым выходом, включая убийство. Модель в этом не участвует.
* **Платная дверь** (`ZAPUSK-ZAHODA.sh`) несёт ПРАВИЛО, адресованное модели: «коммиты делай сам,
  по ходу работы, а не одним последним ходом» (строка 42) и «СВОЮ зону коммитишь по ходу»
  (строка 44), плюс проверку по завершении, что в отчёте есть хэш (строка 117). **Таймера в ней
  нет вовсе** — `sleep`, `while`, периодичность: ноль совпадений.

⚠ **ПОПРАВКА К МОЕЙ ЖЕ ПЕРВОЙ ФОРМУЛИРОВКЕ, снятой кривым грепом в 01:53:** я написал «ноль
упоминаний коммита» — это НЕВЕРНО, их четыре. Верное утверждение: правило есть, механизма нет.
Разница существенная, и она вся в том, кто исполнитель: правило исполняет модель, механизм —
инструмент. Четыре бесплатные позиции этой ночи показали, что модель правило НЕ исполняет:
ноль коммитов ветки при логе до 119 КБ. Критический путь волны переведён на платный канал, то
есть **работа пошла ровно там, где её страхует правило, а не механизм**.

**ЧТО ДЕЛАТЬ, ПОКА ДВЕРЬ НЕ ПОЧИНЕНА — рычаг у тебя, а не у двери.** Раз в круг, для КАЖДОЙ живой
позиции, коммить её рабочую папку сам, не спрашивая позицию и не мешая ей:

```
python3 <путь>/git_zona.py commit --zone <зона позиции> -m "автосохранение <тема>: снимок круга <N>" --push
```

Незаконченная работа в коммите — это НЕ грязный коммит, а страховка: цена оплачена 04.09, когда
453 строки чужой работы спас именно промежуточный коммит соседа. Ветка позиции на то и своя,
чтобы в неё можно было класть промежуточное.

🔴 **И ПРОВЕРЯЙ ЭТО ЧИСЛОМ, А НЕ НАМЕРЕНИЕМ.** В строку круга дневника добавь поле
`не в git:` — сколько грязных путей суммарно по живым рабочим папкам. Ноль — работа переживёт
любое падение. Не ноль дольше одного круга — ты теряешь то, что уже сделано.

**ПОЧЕМУ ЭТО ВАЖНЕЕ, ЧЕМ КАЖЕТСЯ.** Ночью тебя может снять что угодно: кап подписки, зависший
движок, перезапуск приложения, часовой, поднявший вторую голову. Всё это — штатные исходы, и
каждый из них безопасен ровно настолько, насколько работа лежит в git. Позиция, чья работа не
закоммичена, при снятии даёт НОЛЬ, и утром будет неотличима от той, что не начиналась.

## ПЕРВЫЕ ДЕСЯТЬ МИНУТ — пять проверок, каждая ловит уже случавшееся

Сделай их ДО того, как запустишь вторую позицию. Каждая выведена из живого отказа.

**1. Заход реально стартовал — лог непуст.**
`for f in /tmp/zahod-*.log; do printf '%8d %s\n' "$(stat -f%z "$f")" "$f"; done`
Ноль байт = движок не вызывался: чини команду, а не перевыбирай модель. Цена класса: шесть
сожжённых прогонов и час диагностики, потому что снаружи это выглядит как «модель упала».

**2. Лог растёт.** Снять размеры, `sleep 120`, снять снова, сравнить. Позиция без роста через
две минуты — кандидат на снятие. Отсечку ставь ДО срока, а не «посмотрю ещё чуть-чуть».

**3. Ни одна модель не несёт больше двух позиций.**
`ps -Ao command= | grep -o -- '--model [^ ]*' | sort | uniq -c | sort -rn`
Три на одном имени — разводи немедленно: три параллельных прогона съели квоту целиком, и
квоту исчерпал сам оркестратор, а не чужие люди.

**4. Автолог инцидентов не набирает повторов.**
`tail -25 <репо>/zhurnal/_INFRA-git/INCIDENTY.md`
Две записи подряд по одной позиции = виновата не модель, а заход или команда.

**5. Надзор смотрит на ТВОЮ волну.** Указатель объявлен персонально, состав виден, позиции на
диске: `cat <арка>/VOLNA-NOCH-SOSTAV.txt | head -5` и число `kod_*.md` из состава. Молчащий хук
неотличим от исправного — а он молчит ровно тогда, когда не нашёл файлов позиций.

## РЕЕСТР ОТКАЗОВ — что ломалось РЕГУЛЯРНО и чем ловится

Это не история, а список того, что случится снова. Каждая строка оплачена.

| # | Отказ | Чем ловится СЕЙЧАС |
|---|---|---|
| 1 | **Ложный успех:** rc=0, зелёный отчёт, работы нет (8 случаев за две ночи; заглушка `def test_placeholder: pass` прошла как «доведено до конца») | Признак жизни из продукта; страница судится размером и содержимым. 🔴 Полного рычага нет: судить СМЫСЛ коммита машина не умеет — это твоя работа, а не гейта |
| 2 | **Команда умирает до движка** (`worktree add` на существующей папке, `&&`-цепочка, рекурсия) — лог 0 байт, списывается на модель | Пустой лог = модель не вызывалась, `orkestr.py` это различает. Проверка 1 первых десяти минут |
| 3 | **Позиция молчит:** процесс жив, работа не растёт (5 случаев; 35 минут при 0.9% CPU) | `--molchanie 420`, меряется ростом лога. Правило «не больше двух позиций на модель» |
| 4 | **Пул объявлен мёртвым при живом пуле** — «живых 3 из 25» при пороге 45 с; на 120 с те же модели дали 12 | Живость берётся ПО ОДНОЙ, не параллельно; провалившаяся выбрасывается из кандидатов |
| 5 | **Критерий требует того, чего заход не может** (пять случаев за день; восьмой случился ПОСЛЕ того, как урок был записан) | 🔴 Рычага нет, только предложен. У всех двенадцати позиций этой волны выкатка стоит в критерии ЯВНО — класс закрыт вручную при сборке |
| 6 | **Гейт читает строку, а не смысл:** честный отчёт объявлен оборвавшимся | `КОММИТ(Ы)?` расширен. Помни: ложный добор поверх готовой работы дороже, чем лишний круг чтения |
| 7 | **Зоны разведены идеально — и за стык не отвечает никто** (две зелёные позиции дают красный `main`) | Только твоя проверка `main` после каждого влития. Гейт зон этого не видит по построению |
| 8 | **Хук ловит чужую волну или молчит совсем** — 15 заблокированных кругов, ноль работы, разомкнул человек | Персональный указатель по session_id + состав волны файлом. Проверка 5 первых десяти минут |
| 9 | **Модели назначены таблицей, а они — очередь** (13 запусков на 5 позиций, 7 отказов) | В составе НЕТ колонки «позиция → модель». Имя выбирается в момент запуска |
| 10 | **Бесплатная модель делает работу и не делает форму отчёта** (5 прогонов, 2 часа, шапка осталась плейсхолдером) | Форма шапки — часть приёмки. Работа сделана, а форма нет — это доработка на платной, а не переделка работы |
| 11 | **Два писателя в один `kod_*.md`** — три позиции из пяти за вечер | Правило 8 цикла: в живой файл не писать |
| 12 | **`pkill -f` по имени движка убил чужую живую волну** и вместе с ней метрику целой волны | Снимать только по PID из своего файла-метки. Никогда по имени движка |


## HALF TWO — WRITTEN BY THE ORCHESTRATOR, ON RETURN


## ДНЕВНИК ОРКЕСТРАТОРА — ведётся ПО ХОДУ, не после

🔴 **Требование владельца 10.09:** запись в дневнике на КАЖДОМ круге, чтобы он утром мог
проконтролировать и понять, в какой ты точке. Здесь — короткая строка состояния каждый круг;
находки с ценой и разбором — в `ZHURNAL-ORKESTRATORA-NOCH.md`, форма записи описана в его шапке.

Форма строки круга, одна строка, без прозы:

`ЧЧ:ММ · круг N · запущено: P3 P6 · принято: P1 P2 · без вердикта: 9 · main зелёный/красный · выкачено до P2 · чинил оснастку: нет`

01:43 · круг 5 · запущено: P2 (opus) P3 (sonnet), обе ЖИВЫ · принято: — · доработка: P1 P2 P4 P5 · без вердикта: 9 · main красный (входное 1044) · выкачено до: — · чинил оснастку: да, отмена входного ритуала перенесена в бесплатный канал на 10 позициях
01:56 · круг 6 · запущено: P3 (sonnet) P6 (opus) · ПРИНЯТО: P2 · доработка: P1 P4 P5 · без вердикта: 9 · main ЗЕЛЁНЫЙ 1056 против входных 1044 · ВЫКАЧЕНО до P2, боевая 200/175013 б · чинил оснастку: нет
01:58 · круг 7 · запущено: P3 (sonnet) P6 (opus) · ПРИНЯТО: P2 · доработка: P1 P4 P5 · без вердикта: 9 · main ЗЕЛЁНЫЙ 1056/1044 · выкачено до P2 · НЕ В GIT: 0 (страховка круга: P3 закоммичена a773bda и вывезена на origin) · чинил оснастку: нет
02:13 · круг 8 · запущено: P3 (sonnet, 2 коммита) P6 (opus, 3 коммита) · ПРИНЯТО: P2 · доработка: P1 P4 P5 · без вердикта: 9 · main ЗЕЛЁНЫЙ 1056/1044 · выкачено до P2 · НЕ В GIT: 0 (обе позиции коммитят сами, снимок не понадобился) · чинил оснастку: нет
02:38 · круг 9 · запущено: P6 (opus) P8 (sonnet) · ПРИНЯТО: P2 P3 · доработка: P1 P4 P5 · без вердикта: 7 · main ЗЕЛЁНЫЙ 1107/1044, упавших снова 17 · ВЫКАЧЕНО до P3, гость видит 0 обрезанных вместо 48 · НЕ В GIT: 0 · чинил оснастку: нет
02:47 · круг 10 · запущено: P6 (opus, влила в main, дописывает отчёт) P8 (sonnet, 3 коммита) · ПРИНЯТО: P2 P3 · доработка: P1 P4 P5 · без вердикта: 7 · main ЗЕЛЁНЫЙ 1107/1044 · выкачено до P3 · НЕ В GIT: 0 (снимок P8 снят и вывезен) · чинил оснастку: нет
03:09 · круг 11 · запущено: P5 (opus, добор) P8 (sonnet, добор) · ПРИНЯТО: P2 P3 P6 · доработка: P1 P4 P5 P8 · без вердикта: 5 · main ЗЕЛЁНЫЙ 1107/1044, упавших 17 как на входе · ВЫКАЧЕНО до P6 · НЕ В GIT: 1 · чинил оснастку: нет, чинил ГЛАВНУЮ ПАПКУ — снял зависшее слияние P8
---

01:06 · круг 1 · запущено: P1 P2 · принято: — · без вердикта: 12 · main КРАСНЫЙ на входе (1044 passed, 17 failed, 30 errors) · выкачено до: — · чинил оснастку: да, 9 мин из 19
01:33 · круг 2 · запущено: P4, P2 (пуск 3) · принято: — · доработка: P1 · без вердикта: 11 · main красный (входное 1044) · выкачено до: — · чинил оснастку: да, 26 мин из 46
🔴 метки кругов 1 и 2 выше сняты ИЗ ГОЛОВЫ и врут вперёд до 34 минут (замер владельца снаружи 01:19). Круг 1 был около 00:52, круг 2 около 01:05. Дальше все метки из `date`.
01:26 · круг 4 · запущено: P2 (opus, добор), P3 (sonnet) · принято: — · доработка: P1 P2 P4 P5 · без вердикта: 9 · main красный (входное 1044) · выкачено до: — · чинил оснастку: да, гейт вёрстки написан своими руками

> Not written yet: the wave has not returned. STATUS stays `OPEN` until it has, and
> `--lint` says so out loud instead of passing in silence.

### WHAT WAS ASSEMBLED AND LAUNCHED

<NOT FILLED>

### WHAT IT REPAIRED ITSELF AND WHY IT WAS BROKEN

<NOT FILLED>

### VERDICTS

- **kod_kanal-diagnostika.md** — доработка — Отчёт называет ops/diagnostika_kanala.py и ops/PISMO-HOSTERU.md — обоих нет на диске, коммит зоны пуст, ветка захода несёт 0 собственных коммитов; названная блокирующей причина «нет доступа к серверу» опровергнута живой пробой ssh rc=0. Правка вписана в ПРАВКИ ПОСЛЕ ВЫДАЧИ, позиция перезапускается
- **kod_kanon-verstki.md** — доработка — Прогон 2: отчёт честный, но работа не сделана — исполнитель прочёл границу как «канон и гейт делает следующая позиция». Ноль коммитов ветки. Правка 1 с цитатой состава вписана; гейт написан оркестратором и передан правкой 2; позиция передана платному каналу
- **kod_pravila-raspredeleniya.md** — доработка — 0 коммитов ветки, 0 файлов вне git; отчёт сам говорит «код не изменён в этом ходе, работа с кодом отложена». Весь прогон ушёл на входной ритуал гит-контура §0.1
- **kod_vidy-zadach.md** — доработка — 0 коммитов ветки при логе 119 КБ; отчёт сам говорит «содержательная работа (виды, PDF, кондуит) не начата». Тот же входной ритуал съел прогон целиком
- **kod_kanon-verstki.md** — принято — Прогон 5 на opus: 766 строк в четырёх файлах, влито в main ab76e8b. Критерий прогнан ОРКЕСТРАТОРОМ заново, не прочитан: гейт rc=0, четыре страницы по три нуля, охват 4 из 4, 639 элементов; самопроверка --slomat краснеет; pytest tests/veb 76 на входе против 88 passed 2 xfailed после; main 1056 против входных 1044 — выше входа; выкатка rc=0, kanon.css отдаётся боевым сервером 200 и 6775 б, подключён на /raspredelenie. Число 27 школьников в классе снято из живой базы, не константой. ЧАСТИЧНЫЙ ПРОМАХ, не отменяющий приёмку: standalone-гейт мерит только организатора, охват 4 из 4 считает страницы и молчит про роли; роль гостя закрыта в pytest-обёртке (test_gost_vidit_to_zhe_chto_organizator). Позиция НАШЛА и передала числом дефект зоны P3: гость видит 48 обрезанных фамилий на боевом /raspredelenie — проверено оркестратором напрямую
- **kod_verstka-raspredeleniya.md** — принято — Работа сделана и доказана числом на БОЕВОМ сайте: гость видел 48 обрезанных фамилий на /raspredelenie, после выкатки видит 0, скролла нет, размер ответа 123107 б, титул на месте. Замер оркестратора headless-браузером БЕЗ куки, до и после. Продукт: veb/razdely/verstka_stili.py (общая сетка колонок вместо замороженного flex:0 0 9.6rem), правки prepodavateli.py и shkolniki.py, 512 строк. ЧЕГО ПОЗИЦИЯ НЕ СДЕЛАЛА САМА: заход снят потолком фоновой задачи в 02:21:59, не дописав отчёт, не дождавшись верификатора §3 и не влив ветку. Влитие сделал оркестратор через vlit-v-osnovnuyu с названной причиной (e1aa86c), pytest после влития 1107 passed против входных 1044, выкатка rc=0
- **kod_data-i-istoria-kletki.md** — принято — 1552 строки в 8 файлах, влито самим заходом 819dfb6. Критерий прогнан оркестратором заново: tests/grid/test_istoria_kletki.py + tests/veb/test_istoria.py — 44 passed; гейт 0 по зоне позиции зелёный; main 1107 passed против входных 1044, упавших 17 — предсуществующий фон; выкатка rc=0; рендер кондуита на выкаченном коде: вкладка p-kond на месте, 14730 дат у отметок, разметка истории по жесту присутствует. Миграция 009_perebivka_zanyatia проверена чтением: перебивка занятия сделана ДОПИСЫВАНИЕМ отдельной таблицей, а не правкой marks — журнал append-only держат триггеры, и пустая таблица есть штатное состояние. Позиция нашла и починила настоящий дефект данных: импорт записал 15847 строк под одним recorded_at, и отсев тестовых нажатий по времени потерял бы 735 настоящих отзывов — отсев переведён на канал кнопки
- **kod_poisk-i-kartochka.md** — доработка — Работа СДЕЛАНА и цела: ветка zahod/poisk-i-kartochka вершина 8249a44, вывезена на origin, карточка школьника /kartochka/<id>. Но заход умер ПОСРЕДИ слияния своей ветки в ГЛАВНУЮ папку: остался MERGE_HEAD и маркеры конфликта в veb/razdely/shkolniki.py:342, главная папка не собиралась вовсе (pytest падал на сборе SyntaxError). Оркестратор конфликт разрешил, получил два новых красных HTTP 500 на POST /api/enrollment: proverit_karkas требует побайтового равенства сборки гостя и преподавателя, и после слияния оно рвётся на позиции 7611. Это НАСТОЯЩИЙ СТЫК с починкой P3, а не опечатка: ветка отошла от main до переноса {klass} наружу из span. Слияние откачено, main вернулась к 1107 passed и 17 упавшим. Стык возвращён владельцу зоны правкой с полным разбором и перезапущен добором
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

[V1] ПЛАТНОГО КАНАЛА НЕТ ВОВСЕ — обе двери заперты, и открыть их может только человек.
  ЧТО ЗАБЛОКИРОВАНО: пункт 10 мандата (эскалация одной позиции на платную после двух отказов
  подряд). Сегодня он неисполним. Двенадцать позиций шли на бесплатном пуле, который на этой
  работе даёт ноль продукта.
  ЧТО УЖЕ ЗАМЕРЕНО, командами, не рассуждением:
    · `bash ZAPUSK-ZAHODA.sh kanon-verstki opus` → `Failed to authenticate: OAuth session
      expired and could not be refreshed`, выход за 4 секунды. Bedrock-кредов на машине нет
      (это известно и учтено в самой запускалке), а штатная авторизация `claude` протухла.
    · `opencode run --model openrouter/anthropic/claude-opus-5` → `This request requires more
      credits… You requested up to 32000 tokens, but can only afford 586`.
    · Бесплатный пул жив: 3 модели из 6 отвечают. Но P1 на нём выдумала два артефакта
      (0 файлов на диске), P2 честно не поняла границы задания (0 коммитов).
  ФОРМА ГОДНОГО ОТВЕТА — одна строка, любая из трёх:
    · «залил кредиты на openrouter» — платная ступень оживает сама, ничего больше не нужно;
    · «перелогинься в claude: <как>» — если это делается без меня;
    · «работай бесплатным и своими руками» — так я и делаю сейчас, подтверждение не требуется.
  ЧТО Я СДЕЛАЛ, НЕ ДОЖИДАЯСЬ ОТВЕТА: взял критический путь на себя. Ответ нужен не чтобы я
  начал работать, а чтобы следующая волна не спланировала лестницу, которой нет.



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
- [F9] <NOT FILLED>
- [F10] <NOT FILLED>
- [F11] <NOT FILLED>
- [F12] <NOT FILLED>
- [F13] <NOT FILLED>
