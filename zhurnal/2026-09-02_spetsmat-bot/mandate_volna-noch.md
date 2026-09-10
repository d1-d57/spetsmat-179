# MANDATE — volna-noch

<!-- assembled by bootstrap_mandate.py; two halves, two authors; do not merge them -->

**STATUS:** `CLOSED`
**TOP_HALF_STATUS:** `COMPLETE`
**BOTTOM_HALF_STATUS:** `COMPLETE`
**ARC:** `zhurnal/2026-09-02_spetsmat-bot`
**JOURNAL:** `ZHURNAL-ORKESTRATORA-NOCH.md`
<!-- 🔴 Путь СОКРАЩЁН оркестратором до имени файла 10.09 при закрытии, и вот почему.
     Полный repo-relative путь `zhurnal/2026-09-02_spetsmat-bot/ZHURNAL-ORKESTRATORA-NOCH.md`
     линтер НЕ находил, хотя файл лежит ровно там (60517 б, проверено `ls` из корня репозитория).
     `_najti_zhurnal` пробует два основания: `_koren_repo()` — это дом САМОГО ИНСТРУМЕНТА,
     то есть disciplina, а не spetsmat-bot; и папку мандата — тогда путь склеивается вдвойне
     (`zhurnal/…/zhurnal/…`). Ни один не совпадает. Имя файла резолвится вторым основанием,
     ровно как описано в докстринге резолвера: «a wave journal lives beside its mandate».
     Это ТОТ ЖЕ класс, что мучил волну всю ночь (см. классы 14 и 19 рефлексии): инструмент
     ищет от своего дома, а не от целевого репозитория. Занесено пунктом 15 АНАЛИТИКУ ДОПИСАТЬ. -->
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
03:20 · круг 12 · запущено: P5 (opus, 5 коммитов, вливает main в СВОЮ папку) P8 (sonnet, снимок снят и вывезен) · ПРИНЯТО: P2 P3 P6 · доработка: P1 P4 P5 P8 · без вердикта: 5 · main ЗЕЛЁНЫЙ 1107/1044 · выкачено до P6 · НЕ В GIT: 3 у P8 сняты снимком, у P5 40 путей внутри её собственного слияния — снимок невозможен, её 5 коммитов целы · чинил оснастку: нет
03:53 · круг 13 · запущено: P5 (opus) P4 (sonnet) · ПРИНЯТО: P2 P3 P6 P8 · доработка: P1 P4 P5 · без вердикта: 4 (P7 P9 P10 P11 P12 минус запущенные) · main ЗЕЛЁНЫЙ 1112/1044, упавших 17 как на входе · ВЫКАЧЕНО до P8, /kartochka/1 отдаёт 200 на боевом · НЕ В GIT: 0 · чинил оснастку: нет, чинил ОБЩУЮ БАЗУ — применил непринятую миграцию
03:59 · круг 14 · запущено: P4 (sonnet) P7 (opus) · ПРИНЯТО: P2 P3 P5 P6 P8 · доработка: P1 P4 · без вердикта: 4 (P4 в работе, P9 P10 P11 P12) · main ЗЕЛЁНЫЙ 1133/1044, упавших 17 · ВЫКАЧЕНО до P5 · НЕ В GIT: 0 · вопросов владельцу: 2 · чинил оснастку: да, обход потолка фоновых задач
04:13 · круг 15 · запущено: P7 (opus) P9 (sonnet) · ПРИНЯТО: P2 P3 P4 P5 P6 P8 — шесть · доработка: P1 · без вердикта: 4 (P7 P9 в работе, P10 P11 P12) · main ЗЕЛЁНЫЙ 1133/1044, упавших 17 · ВЫКАЧЕНО до P4 · НЕ В GIT: 0 · вопросов владельцу: 3 · чинил оснастку: нет
04:24 · круг 16 · запущено: P7 (opus, 5 коммитов) P9 (sonnet, снимок снят и вывезен) · ПРИНЯТО: 6 · доработка: P1 · без вердикта: 4 · main ЗЕЛЁНЫЙ 1133/1044 · выкачено до P4 · НЕ В GIT: 0 · чинил оснастку: нет
04:55 · круг 17 · запущено: P10 (opus) P11 (sonnet) · ПРИНЯТО: P2 P3 P4 P5 P6 P7 P8 P9 — ВОСЕМЬ · доработка: P1 · без вердикта: 3 (P10 P11 в работе, P12 условная) · main ЗЕЛЁНЫЙ 1186/1044, упавших 17 · ВЫКАЧЕНО до P9 · НЕ В GIT: 0 · вопросов владельцу: 3 · чинил оснастку: нет
05:05 · круг 18 · запущено: P10 (opus) P11 (sonnet) · ПРИНЯТО: 8 · доработка: P1 · без вердикта: 3 · main ЗЕЛЁНЫЙ 1186/1044 · выкачено до P9 · НЕ В GIT: 0 (снимки обеих живых сняты и вывезены: c43bc60, a7cd921) · чинил оснастку: нет
05:17 · круг 19 · запущено: P10 (opus) · ПРИНЯТО: ДЕВЯТЬ (P2 P3 P4 P5 P6 P7 P8 P9 P11) · доработка: P1 · без вердикта: 2 (P10 в работе, P12 условная) · main ЗЕЛЁНЫЙ 1198/1044, упавших 17 · ВЫКАЧЕНО до P11 · НЕ В GIT: 0 (снимок P10 46811b9) · чинил оснастку: нет
05:30 · круг 20 · запущено: P10 (opus, влила, дописывает отчёт) P1 (sonnet, добор) · ПРИНЯТО: 9 · доработка: P1 в работе · без вердикта: 2 (P10 ждёт отчёта, P12 условная) · main ЗЕЛЁНЫЙ 1215/1044, упавших 17 · ВЫКАЧЕНО до P10 · НЕ В GIT: 0 · чинил оснастку: нет
05:39 · круг 21 · запущено: P10 (opus, дописывает отчёт) · ПРИНЯТО: ДЕСЯТЬ (P1 P2 P3 P4 P5 P6 P7 P8 P9 P11) · доработка: нет · без вердикта: 2 (P10 ждёт отчёта, P12 условная) · main ЗЕЛЁНЫЙ 1215/1044, упавших 17 · выкачено до P10 · НЕ В GIT: 0 · чинил оснастку: нет
05:50 · круг 22 · запущено: P12 (opus) — УСЛОВИЕ ВЫПОЛНЕНО, все P1-P11 приняты · ПРИНЯТО: ОДИННАДЦАТЬ · доработка: нет · без вердикта: 1 (P12 в работе) · main ЗЕЛЁНЫЙ 1215/1044, упавших 17 · ВЫКАЧЕНО до P10, «Лена Мирошниченко» видна на боевой странице · НЕ В GIT: 0 · чинил оснастку: нет
06:06 · круг 24 · запущено: P12 (opus, 3 коммита) · ПРИНЯТО: 11 · доработка: нет · без вердикта: 1 (P12) · main ЗЕЛЁНЫЙ 1215/1044 · выкачено до P10 · НЕ В GIT: 0 · ФАЗА ЗНАНИЯ ПРОЙДЕНА: BORN 20, CLOSED 20, CARRIED 0 · часть Г рефлексии заполнена · чинил оснастку: нет
---

01:06 · круг 1 · запущено: P1 P2 · принято: — · без вердикта: 12 · main КРАСНЫЙ на входе (1044 passed, 17 failed, 30 errors) · выкачено до: — · чинил оснастку: да, 9 мин из 19
01:33 · круг 2 · запущено: P4, P2 (пуск 3) · принято: — · доработка: P1 · без вердикта: 11 · main красный (входное 1044) · выкачено до: — · чинил оснастку: да, 26 мин из 46
🔴 метки кругов 1 и 2 выше сняты ИЗ ГОЛОВЫ и врут вперёд до 34 минут (замер владельца снаружи 01:19). Круг 1 был около 00:52, круг 2 около 01:05. Дальше все метки из `date`.
01:26 · круг 4 · запущено: P2 (opus, добор), P3 (sonnet) · принято: — · доработка: P1 P2 P4 P5 · без вердикта: 9 · main красный (входное 1044) · выкачено до: — · чинил оснастку: да, гейт вёрстки написан своими руками

> Not written yet: the wave has not returned. STATUS stays `OPEN` until it has, and
> `--lint` says so out loud instead of passing in silence.

### WHAT WAS ASSEMBLED AND LAUNCHED

Twelve positions, all twelve launched, all twelve accepted. Nineteen runs in total for twelve
positions: seven re-runs, all of them named in VERDICTS above with their reason.

Launch channels used, and why both were needed:
* **Free pool** (`orkestr.py --rezhim progon`, models `inkling`, `inkling-small`, `laguna`) —
  four runs, **zero lines of product**. Cause found at 01:26 and named in the journal: the
  entry ritual §0.1 consumes the whole run. One position wrote a 119 KB log and reported
  honestly «содержательная работа не начата». The cancellation of that ritual was carried
  from the paid launcher into the free channel on ten position files at 01:40; it was never
  re-tested, because by then the paid channel was alive and carried everything.
* **Paid channel** (`ZAPUSK-ZAHODA.sh <тема> opus|sonnet`) — every accepted position. Two in
  parallel, never two on one model: `opus` and `sonnet` alternated by slot.

The paid channel was DEAD at the start of the wave — `claude -p` answered
`Failed to authenticate: OAuth session expired`, and OpenRouter had credit for 586 tokens of
32000. For that hour the orchestrator took the critical path itself and wrote the layout gate
(`tools/gejt_verstki.py`) by hand. The owner restored the channel at 01:20; the orchestrator
handed the gate to position P2 by a ПРАВКА and returned to orchestrating within one circle.

### WHAT IT REPAIRED ITSELF AND WHY IT WAS BROKEN

Nine failures of the wave's own rigging, all of them other people's mechanisms, all worked
around live. Recorded as classes 13–21 in `REFLEKSIA-ORKESTRATOROV.md`, part А.

1. **All three alarms died in 65 seconds** — the glob `kod_*.md` took 71 pass files of eight
   previous waves; the mechanism that alone can wake a LIVE head was dead from minute one.
   Fixed: the position list is read from the file `VOLNA-POZICII` (which already lay in the
   arc and was read by nobody). ⚠ The sentinel carries the same glob on lines 145 and 153 and
   is NOT fixed — named as a debt.
2. **A position's worktree landed in the FOREIGN repository `disciplina`** — `git_zona.py`
   without `GIT_ZONA_REPO` takes its own home. Worked around: the variable is set on every
   launch. Two tombstones removed.
3. **The orchestrator's own retry killed its own work** — `worktree add` on an existing folder
   returns rc=2, the `&&` chain breaks before the engine, `tee` truncates the log to zero, and
   the orchestrator reads its own retry as «the command died». Fixed on ten position files:
   `{ … || true; }`.
4. **`orkestr.py` crashes at the acceptance stage on a foreign repository** — `KOREN` is its
   own home, `relative_to` raises. Acceptance was done by hand all night.
5. **The entry ritual eats a free model's whole run** — cause of the zero product above.
6. **The paid channel was dead** — restored by the owner, question [V1].
7. **The background-task ceiling kills a pass that honestly waits for its §3 verifier** — cost
   the best content work of the night its report. `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0`
   written into the paid launcher at 03:57.
8. **The head took time from itself, not from `date`** — drift reached 34 minutes over 33
   minutes of work; measured from outside by the owner. All marks after 01:26 are from `date`.
9. **The head rewrote a script while it was running** — bash reads by offset; the running
   instance died on `line 154` of a 136-line file.

### VERDICTS

- **kod_kanal-diagnostika.md** — доработка — Отчёт называет ops/diagnostika_kanala.py и ops/PISMO-HOSTERU.md — обоих нет на диске, коммит зоны пуст, ветка захода несёт 0 собственных коммитов; названная блокирующей причина «нет доступа к серверу» опровергнута живой пробой ssh rc=0. Правка вписана в ПРАВКИ ПОСЛЕ ВЫДАЧИ, позиция перезапускается
- **kod_kanon-verstki.md** — доработка — Прогон 2: отчёт честный, но работа не сделана — исполнитель прочёл границу как «канон и гейт делает следующая позиция». Ноль коммитов ветки. Правка 1 с цитатой состава вписана; гейт написан оркестратором и передан правкой 2; позиция передана платному каналу
- **kod_pravila-raspredeleniya.md** — доработка — 0 коммитов ветки, 0 файлов вне git; отчёт сам говорит «код не изменён в этом ходе, работа с кодом отложена». Весь прогон ушёл на входной ритуал гит-контура §0.1
- **kod_vidy-zadach.md** — доработка — 0 коммитов ветки при логе 119 КБ; отчёт сам говорит «содержательная работа (виды, PDF, кондуит) не начата». Тот же входной ритуал съел прогон целиком
- **kod_kanon-verstki.md** — принято — Прогон 5 на opus: 766 строк в четырёх файлах, влито в main ab76e8b. Критерий прогнан ОРКЕСТРАТОРОМ заново, не прочитан: гейт rc=0, четыре страницы по три нуля, охват 4 из 4, 639 элементов; самопроверка --slomat краснеет; pytest tests/veb 76 на входе против 88 passed 2 xfailed после; main 1056 против входных 1044 — выше входа; выкатка rc=0, kanon.css отдаётся боевым сервером 200 и 6775 б, подключён на /raspredelenie. Число 27 школьников в классе снято из живой базы, не константой. ЧАСТИЧНЫЙ ПРОМАХ, не отменяющий приёмку: standalone-гейт мерит только организатора, охват 4 из 4 считает страницы и молчит про роли; роль гостя закрыта в pytest-обёртке (test_gost_vidit_to_zhe_chto_organizator). Позиция НАШЛА и передала числом дефект зоны P3: гость видит 48 обрезанных фамилий на боевом /raspredelenie — проверено оркестратором напрямую
- **kod_verstka-raspredeleniya.md** — принято — Работа сделана и доказана числом на БОЕВОМ сайте: гость видел 48 обрезанных фамилий на /raspredelenie, после выкатки видит 0, скролла нет, размер ответа 123107 б, титул на месте. Замер оркестратора headless-браузером БЕЗ куки, до и после. Продукт: veb/razdely/verstka_stili.py (общая сетка колонок вместо замороженного flex:0 0 9.6rem), правки prepodavateli.py и shkolniki.py, 512 строк. ЧЕГО ПОЗИЦИЯ НЕ СДЕЛАЛА САМА: заход снят потолком фоновой задачи в 02:21:59, не дописав отчёт, не дождавшись верификатора §3 и не влив ветку. Влитие сделал оркестратор через vlit-v-osnovnuyu с названной причиной (e1aa86c), pytest после влития 1107 passed против входных 1044, выкатка rc=0
- **kod_data-i-istoria-kletki.md** — принято — 1552 строки в 8 файлах, влито самим заходом 819dfb6. Критерий прогнан оркестратором заново: tests/grid/test_istoria_kletki.py + tests/veb/test_istoria.py — 44 passed; гейт 0 по зоне позиции зелёный; main 1107 passed против входных 1044, упавших 17 — предсуществующий фон; выкатка rc=0; рендер кондуита на выкаченном коде: вкладка p-kond на месте, 14730 дат у отметок, разметка истории по жесту присутствует. Миграция 009_perebivka_zanyatia проверена чтением: перебивка занятия сделана ДОПИСЫВАНИЕМ отдельной таблицей, а не правкой marks — журнал append-only держат триггеры, и пустая таблица есть штатное состояние. Позиция нашла и починила настоящий дефект данных: импорт записал 15847 строк под одним recorded_at, и отсев тестовых нажатий по времени потерял бы 735 настоящих отзывов — отсев переведён на канал кнопки
- **kod_poisk-i-kartochka.md** — доработка — Работа СДЕЛАНА и цела: ветка zahod/poisk-i-kartochka вершина 8249a44, вывезена на origin, карточка школьника /kartochka/<id>. Но заход умер ПОСРЕДИ слияния своей ветки в ГЛАВНУЮ папку: остался MERGE_HEAD и маркеры конфликта в veb/razdely/shkolniki.py:342, главная папка не собиралась вовсе (pytest падал на сборе SyntaxError). Оркестратор конфликт разрешил, получил два новых красных HTTP 500 на POST /api/enrollment: proverit_karkas требует побайтового равенства сборки гостя и преподавателя, и после слияния оно рвётся на позиции 7611. Это НАСТОЯЩИЙ СТЫК с починкой P3, а не опечатка: ветка отошла от main до переноса {klass} наружу из span. Слияние откачено, main вернулась к 1107 passed и 17 упавшим. Стык возвращён владельцу зоны правкой с полным разбором и перезапущен добором
- **kod_poisk-i-kartochka.md** — принято — ПОПРАВКА К МОЕМУ ЖЕ ВЕРДИКТУ доработка, вынесенному в 03:15: он опирался на неверный диагноз. Слияние P8 перемерено честно, с применёнными миграциями — main 1112 passed против входных 1044, упавших 17, то есть тот же предсуществующий фон. Тридцать два красных, за которые я откатил слияние, давала НЕ работа P8, а непринятая миграция 009_perebivka_zanyatia на общей рабочей базе data/spetsmat.db: код позиции P6 читает таблицу mark_lesson_override, а к базе миграция применена не была, и любой POST /api/enrollment падал 500 на пересборке публичной страницы. Проверено живьём: гейт вёрстки четыре страницы по три нуля; выкатка rc=0; боевой сайт — /raspredelenie 200 и 0 обрезанных, / 200 и 0 обрезанных, НОВАЯ страница /kartochka/1 отдаёт 200, 52331 б, титул «Агаркова Ирина — Ключики». Стык каркаса гостя и преподавателя, из-за которого позиция возвращалась добором, ею же и починен
- **kod_vidy-zadach.md** — принято — Механизм доставлен и проверен оркестратором НА КОПИИ живой базы, а не прочитан: python3 tools/import_listka.py 16A даёт «переразметка: 8: обязательная → письменная», 16α — четыре крестика, и tools/vidy_zadach.py на той же копии печатает 16A † 1, 16α † 4, 16ℵ † 0 — ровно те числа, что называет состав волны («в 16A крестик один, в 16α четыре»). tests/sheets 33 passed, как обещал отчёт. main после влития 1133 passed против входных 1044, упавших 17 — фон. Ветка была влита самим заходом (ee3922c) и снята моим ошибочным reset; заход подал об этом точную заявку 2026-09-10T0346 и сознательно не вливал повторно, чтобы не воскресить чужое снятое слияние — это правильное поведение, влитие восстановлено мной (8333c21). Разбор печатает ОХВАТ и список того, чего не проверяет. ОСТАЁТСЯ РЕШЕНИЕ ВЛАДЕЛЬЦА, вынесено в QUESTIONS: разметка БОЕВОЙ базы импортом — изменение живых записей школы, оркестратор его не делает
- **kod_pravila-raspredeleniya.md** — принято — Суть доставлена и проверена оркестратором прогоном, а не чтением: tests/enrollment/test_calendar_and_ceiling.py — 10 passed, и имена тестов покрывают обе клаузы владельца дословно: assigning_on_a_day_the_teacher_does_not_attend_is_refused, moving_a_student_onto_a_day_the_teacher_does_not_attend_is_refused (F2) и a_sixth_student_in_one_slot_is_refused, the_fifth_student_is_the_last_one_accepted, moving_a_sixth_student_onto_a_full_teacher_is_refused (F1); отдельным тестом закрыт стык с сервером — enforce_is_public_for_the_in_place_edit_path_in_veb_server. Влито в main 5cfb506, main 1133 passed против входных 1044, упавших 17. Позиция НЕ тронула два живых нарушения и это ПРАВИЛЬНО: они требуют решения владельца, каждое описано с двумя вариантами и вынесено в QUESTIONS. Заодно нашла нестыковку задания с фактом: в нём 15 принимающих, активных 14
- **kod_statistiki-i-grobarij.md** — принято — 1205 строк в 4 файлах, влито 50cf01e. Прогнано оркестратором: tests/grid/test_konduit_velichiny.py + test_statistiki.py — 35 passed; main 1186 passed против входных 1044, упавших 17 — фон; гейт вёрстки 4 страницы по три нуля, осмотрено 669 элементов; выкатка rc=0, боевая 200. Клауза F6 закрыта БУКВАЛЬНО, а не пересказом: сверка идёт прямым SQL по снимку БОЕВОЙ базы, снятому через sqlite3.Connection.backup сквозь WAL (16188 событий, 57 школьников, 595 задач, 21 листок, 247 строк enrollment), проверочный скрипт не импортирует ни строки проектного кода, и числа печатаются рядом: «1а экран 16 SQL 16», «1б экран 15 SQL 15», «2 экран 12 SQL 12», «3 экран 10 SQL 10». Гробарий сделан пустой вкладкой по решению владельца и наполнится сам, когда листок станет историческим; отдельным тестом закрыт край «задача, взятая тремя и больше, в гробарий не попадает»
- **kod_istoria-zanyatij.md** — принято — Вкладка История зանятий: core/services/istoria_poseshchenij.py, veb/razdely/istoria_zanyatij.py и тесты, влито в main самим заходом. Прогнано оркестратором: tests/sessions — 29 passed; main 1186 passed против входных 1044, упавших 17 — фон; гейт вёрстки зелёный, кондуит вырос со 235 до 265 осмотренных элементов и остался по нулям; выкатка rc=0. Заход честно назвал границу своих прав: свою ветку влил и вывез, а вывоз main трогать не стал и подал заявку — это правильное поведение по правилу владельца
- **kod_vnesenie-zadach.md** — принято — Самая дорогая позиция волны доставлена: 1132 строки, veb/razdely/vnesenie.py на 674 строки плюс 445 строк тестов, влито ab72ceb. Прогнано оркестратором: tests/veb/test_vnesenie.py — 12 passed; main 1198 passed против входных 1044, упавших 17 — фон; гейт вёрстки четыре страницы по нулям, 670 элементов; выкатка rc=0, боевая 200 и 175013 б. Клауза F10 закрыта ПО ВСЕМ ТРЁМ КАНАЛАМ, и это видно по именам тестов, а не по отчёту: tekst_tri_vnesenia_pishut_rovno_podtverzhdyonnoe, foto_tri_vnesenia_pishut_rovno_podtverzhdyonnoe, golos_tri_vnesenia_pishut_rovno_podtverzhdyonnoe. Запрет записи без подтверждения закрыт отдельным тестом draft_dver_nichego_ne_pishet — то есть дверь гипотезы физически не пишет в базу. Плюс края, о которых не спрашивали: двусмысленное имя даёт КНОПКИ, а не догадку; отказ внешнего API показывается, а не проглатывается; без куки отказывают все двери и форма не показывается вовсе
- **kod_kanal-diagnostika.md** — принято — ВТОРОЙ прогон, на платном канале, после вердикта доработка за выдуманный отчёт. Теперь всё проверено оркестратором ФАКТАМИ НА СЕРВЕРЕ, а не чтением: ops/diagnostika_kanala.py (13042 б) и ops/PISMO-HOSTERU.md (6165 б) СУЩЕСТВУЮТ на диске и в git — гейт зоны ops/tests/ops зелёный, влито e7ee14b. Замер прогнан НА БОЕВОМ СЕРВЕРЕ, а не на ноутбуке: /tmp/kanal-diagnostika-run1/ на 159.194.254.52 несёт 8 файлов и РОВНО 600 строк проб, первая строка — {ts 2026-09-10T02:21:50Z, address api.telegram.org, protocol -4, http_code 302, time_total 0.289206, success true}, то есть три адреса на два протокола по сотне проб, как требовал критерий. Письмо хостеру несёт настоящие числа (0.0%, 100%, таймауты 1 и 3 с) и называет резолвер 198.18.18.18. Позиция сама написала в отчёте, что прошлая отговорка про недоступный ssh была ложной, и подтвердила доступ прежде, чем работать
- **kod_kabinet-prepodavatelya.md** — принято — Влито e25bbc2; прогнано оркестратором: tests/veb/test_kabinet.py — 17 passed, main 1215 passed против входных 1044, упавших 17 — фон; выкатка rc=0. Клауза F9 закрыта по всем трём частям. «Лена вместо Елены» ПРОВЕРЕНО НА БОЕВОЙ СТРАНИЦЕ, а не в отчёте: curl по /raspredelenie даёт «prep-imya">Лена Мирошниченко», единственное оставшееся «Елена» — цитата внутри комментария о длинных именах, а не имя на экране. Отдельная ценность: замораживание распределения на дату сделано ОТКАЗОМ НА ЗАПИСИ, а не серой кнопкой, и переиспользует enforce_calendar_and_ceiling соседней позиции pravila-raspredeleniya, а не пишет то же правило второй раз; второго хранилища не заведено — пишется та же строка teacher_attendance, которую уже читает каркас, поэтому экран распределения не потребовал ни одной правки. Дверь кабинета своя и поля teacher_id в запросе нет вовсе — подделать чужое отсутствие нечем
- **kod_paroli-shkolnikov.md** — принято — УСЛОВНАЯ позиция: условие [F12] выполнено — P1-P11 все приняты к 05:50, за пять часов до дедлайна, поэтому запуск законен. Влито d9a6243. Содержательные коммиты в main: cbe60e9 «личный пароль каждому активному школьнику, слиянием в файл преподавателей», 546b4e3 «вход узнаёт школьника по его паролю и НЕ ДАЁТ ему никакой роли», 0ea26cf «человек заменяет выданный пароль своим, в отдельном файле». Прогнано оркестратором: tests/veb/test_vhod.py + tests/klyuchi — 14 passed; main 1252 passed против входных 1044, упавших 17 — предсуществующий фон не сдвинулся; гейт вёрстки четыре страницы по нулям; выкатка rc=0; боевой сайт целиком зелёный — /, /raspredelenie, /kartochka/1 и /vhod по 200, обрезанных 0, скролла 0. Ключевое решение позиции верное: пароль школьника не даёт РОЛИ вовсе — он опознаёт человека, а не выдаёт права, поэтому карточка P8 остаётся тем же экраном и не требует второго контура прав
### WHAT WAS EXCLUDED AND WHY

**Excluded by the owner's decision, recorded in the top half — not touched, and rightly:**
the Telegram bot; filling the Гробарий (the sheet becomes historical only on Monday, so the tab
is built empty by design); handing passwords to pupils over Telegram; the pupil's personal page
as a separate tab (it arrived as the card in P8).

**Excluded by the orchestrator, each with its reason — and each is a QUESTION, not a silent cut:**
* **Marking the LIVE database by import** — [V2]. The mechanism is delivered, merged and
  deployed; the data step changes live records of the school and, on sheet 16α, touches three
  cells «сверх источника». Not mine to decide at four in the morning.
* **The two live distribution violations** — [V3]. The ban that would now prevent them works and
  is closed by ten tests; who moves where is the owner's knowledge, not mine.

**NOT excluded, and stated plainly because it looks like an exclusion:** the seventeen failing
tests and thirty errors on `main` are PRE-EXISTING — they stood at the entrance measurement at
00:51 and did not move once all night. They live in `tests/ops/test_vykatka.py`,
`tests/test_enrollment_scd2.py`, `tests/test_sostav.py`, `tests/svodka/`, `tests/room/`. Fixing
them was not this wave's task and would have burned hours that the twelve positions needed.

### IRREVERSIBLE ACTIONS

Four, all named here rather than buried, and each with what made it recoverable.

1. **`git merge --abort` on `main` at 03:07** — removed a hung merge left by a position that died
   mid-merge IN THE MAIN CHECKOUT, with `MERGE_HEAD` set and conflict markers in
   `veb/razdely/shkolniki.py:342`. `main` did not even collect (`SyntaxError` on the markers).
   Recoverable: the position's work was verified on origin (`cba0a77`) by `git ls-remote` BEFORE
   the abort.
2. **`git reset --hard 542e10f` on `main` at 03:45** — ROLLED BACK A HEALTHY MERGE on a wrong
   diagnosis. The 32 red tests came from an unapplied migration on the shared working database,
   not from the merge. The arc was copied to the scratchpad first and restored after; the
   position's branch was on origin; both merges were restored within the hour. This is the
   single worst decision of the night and it is written up in full, twice: journal 04:07 and
   reflection class 19.
3. **Resolving another position's merge conflict by hand at 02:59** in `shkolniki.py` — took
   `data-sid` from one side and the `{klass}` placement from the other, because taking either
   side whole would have silently reverted the fix for 48 cropped surnames. Later superseded:
   the position resolved the same seam itself.
4. **Nine deploys to the live server** (`deploy/vykatka.sh`), each after an accepted position,
   each rc=0 with the page answering 200. The script refuses during lesson hours by itself and
   was never forced.

**NOT done, deliberately:** no process was killed all night; the owner's password files were
never used to log in anywhere; the live database was never written to by the orchestrator.

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

[V2] РАЗМЕТКА БОЕВОЙ БАЗЫ ИМПОРТОМ — единственное, что отделяет вас от крестиков в кондуите.
  ЧТО ЗАБЛОКИРОВАНО: клауза [F4], вид «письменная» из крестика в PDF листка. Механизм готов,
  влит в main и выкачен; данные в БОЕВОЙ базе не размечены, поэтому в кондуите крестиков не
  видно — там сейчас `† 0` во всех листках.
  ЧТО ЗАМЕРЕНО, на КОПИИ живой базы, не на боевой:
    · `python3 tools/import_listka.py 16A --db <копия>` → «переразметка: 8: обязательная →
      письменная», изменений 35;
    · `python3 tools/import_listka.py 16α --db <копия>` → изменений 37, и отдельной строкой
      «ячеек в базе сверх источника: 3 · лишние: 10а, 10б, 10в»;
    · `python3 tools/vidy_zadach.py --db <копия>` после этого печатает **16A † 1, 16α † 4,
      16ℵ † 0** — ровно те числа, что вы назвали при сборке волны.
  ПОЧЕМУ Я ЭТОГО НЕ СДЕЛАЛ САМ: это изменение ЖИВЫХ ЗАПИСЕЙ школы, а не выкатка кода. Импорт
  не только переставляет вид у одной ячейки — он приводит состав ячеек листка к разбору PDF, и
  на 16α насчитал три ячейки «сверх источника» (10а, 10б, 10в). Судить, лишние они или живые,
  я не могу: это ваши задачи и ваши дети, и откат такого — только из ночного архива на Drive.
  ФОРМА ГОДНОГО ОТВЕТА — одна строка:
    · «размечай, 10а/10б/10в лишние» — выполняется одной командой на каждый листок;
    · «размечай, но 16α не трогай» — тогда 16A получит свой крестик, 16α останется как есть;
    · «сам утром» — механизм ждёт вас, ничего не сломано.

[V3] ДВА ЖИВЫХ НАРУШЕНИЯ РАСПРЕДЕЛЕНИЯ, которые новый запрет отныне НЕ ДАЛ БЫ создать — но
     они созданы раньше и сидят в боевой базе прямо сейчас.
  ЧТО ЗАБЛОКИРОВАНО: ничего в коде. Запрет [F1]/[F2] работает и закрыт десятью тестами.
  Заблокирована ПРАВКА ДАННЫХ: кого куда переставить — знаете только вы.
  ЧТО ЗАМЕРЕНО, позицией pravila-raspredeleniya по БОЕВОЙ базе и перепроверено мной:
    · **Ольга Рыжая (id 13)** отмечена как не приходящая в слот 2 (четверг), а **Юсуфов Арон
      (id 56)** с 2026-09-09 висит у неё в этом самом слоте открытой строкой;
    · **Вася Филянин (id 8)** несёт **6** школьников в слоте 1 и **7** в слоте 2 при потолке 5.
  ФОРМА ГОДНОГО ОТВЕТА — по строке на каждое:
    · Юсуфов: «переставить к <имя>» — или «Рыжая ради него приходит, снимите отметку»;
    · Филянин: «переставить <кого> к <кому>» — или «Филянину можно 7, потолок ему не писан».
  ⚠ И ОТДЕЛЬНО, мелочь с ценой: задание волны называет **15 принимающих**, в базе активных
  **14**. Одно из двух чисел неверно, и это надо поправить до того, как по нему что-то считают.



### CLOSING PHASE — KNOWLEDGE BALANCE

> The four numbers below are the point of this section. `DELTA` is not
> stored, it is CHECKED: `--lint` recomputes `BORN` minus `CLOSED` and
> refuses a mismatch. `CARRIED` above zero REQUIRES the unjudged lessons
> to be listed BY NAME underneath — carried is lawful, silent is not.

**BORN:** `20`
**CLOSED:** `20`
**CARRIED:** `0`
**DELTA:** `0`

_Carried by name (one line each, or the single word `none`):_
none

> **How the numbers were reached, so they can be checked rather than believed.**
> **BORN 20** = 11 real lessons with a `ЦЕНА` in the `## УРОКИ ФАБРИКЕ` sections of the twelve
> pass files (nine further matches were the section's own template preamble, not lessons) plus
> 9 classes born in this wave in `REFLEKSIA-ORKESTRATOROV.md` part А, numbers 13–21.
> **CLOSED 20** = judged in three batches on three DIFFERENT free models, none judging its own
> author: the positions' lessons (written by opus and sonnet) were judged by
> `inkling-small:free`; the orchestrator's classes (written by the orchestrator) by
> `laguna-s-2.1:free` and `inkling:free`.
> **CARRIED 0** — nothing was left unjudged, so nothing is carried into the next mandate.
>
> 🔴 **AND THE HONEST LIMIT OF THIS PHASE, which the numbers hide.** The verdicts came back in
> poor FORM: `inkling-small` answered «ПРАВИЛО <имя позиции>» eleven times where a skill name
> was asked for, so its rules carry no deliverable home; `laguna` returned all three verdicts
> for every lesson instead of choosing one; `inkling` returned capitalised restatements of the
> headings. The phase produced a real SIGNAL — `laguna` independently confirmed that class 18
> is a correction of class 15 and that `/konduit` 404 is correct behaviour, which is exactly the
> place where the author was wrong — but it did not produce a usable FORM, and the homes were
> assigned by the head. The next mandate should promise the signal and not the form; this is
> item 13 of АНАЛИТИКУ ДОПИСАТЬ.

### ЗАКРЫВАЮЩАЯ ПОЗИЦИЯ `ZK1` — почему её нет в составе и кто исполнил её работу

`ZK1 · zakon-zakrytiya-volna-noch` НЕ был добавлен в `VOLNA-NOCH-SOSTAV.txt`, и это записано
в самом составе как решение с ценой, а не как забывчивость: хук волны читает второе поле каждой
строки как ТЕМУ и ищет на диске `kod_<тема>.md`; файла закрывающей позиции не существует, а
объявленная-но-отсутствующая позиция уже держала голову шестьдесят кругов подряд с единственным
выходом через рубильник.

**Закон закрытия над этим мандатом исполнил САМ ОРКЕСТРАТОР последним ходом**, как предписывает
пункт 12 раздела ЦИКЛ. Пять условий закона проверены командами, а не памятью:

| условие | проверка | результат |
|---|---|---|
| вердикт у каждой позиции | `--append-verdict` двенадцать раз | ✅ 12 из 12, все `принято` |
| ветки влиты и погашены | `git branch --no-merged main` | ✅ пусто |
| работа доехала в git | `git_zona.py check` по зонам + push каждый круг | ✅ вне git 0 |
| журнал вёлся ПО ХОДУ | 24 строки круга в дневнике, 19 записей с `ЦЕНА` в журнале | ✅ не задним числом |
| фаза знания пройдена | BORN 20 · CLOSED 20 · CARRIED 0 | ✅ |

Пять из пяти зелёные, поэтому статус волны — `CLOSED`, а не `CLOSED-S-DOLGOM`. Долгов условий
нет; то, что осталось нерешённым, — три ВОПРОСА ВЛАДЕЛЬЦУ, а вопрос не есть красное условие.

### LINE-BY-LINE ANSWER TO EVERY FINALIZED ITEM

Каждый пункт — `done` или `not done` с причиной, и у `done` стоит то, ЧЕМ это проверено.

> One line per finalized item, and every item of the top half must get one: `done` or `not done` with the reason. This field is the point of the whole artifact.
- [F1] **done.** Потолок пяти проверен прогоном, а не отчётом: `tests/enrollment/test_calendar_and_ceiling.py` — 10 passed, из них `a_sixth_student_in_one_slot_is_refused`, `the_fifth_student_is_the_last_one_accepted`, `moving_a_sixth_student_onto_a_full_teacher_is_refused`. Отказ стоит НА ЗАПИСИ, а не на кнопке, и вынесен в публичную `enforce_calendar_and_ceiling`; отдельный тест держит стык с сервером (`enforce_is_public_for_the_in_place_edit_path_in_veb_server`).
- [F2] **done.** `assigning_on_a_day_the_teacher_does_not_attend_is_refused` и `moving_a_student_onto_a_day_the_teacher_does_not_attend_is_refused` — те же 10 passed. Позиция `kabinet-prepodavatelya` ПЕРЕИСПОЛЬЗОВАЛА это правило вместо своей копии, поэтому запрет один на оба экрана.
- [F3] **done частично, и разница названа.** Вкладки кондуита и порядок сделаны позицией `statistiki-i-grobarij`, вкладка Гробарий стоит пустой по решению владельца. Самый новый листок определяется командой из базы (`_samyj_novyj`), а не константой, и позиция отдельно закрыла край «текущий листок не уезжает в гробарий за сутки до раздачи». 🔴 Чего я НЕ проверил живьём: порядок кнопок классов «8 затем 9, и 9 открыт» — он за входом, а входить чужими учётными данными я не стал; проверено рендером кондуита на выкаченном коде, где вкладка `p-kond` и 14730 дат на месте.
- [F4] **not done до конца, и остановлено НАМЕРЕННО.** Механизм доставлен и проверен на КОПИИ живой базы: `tools/import_listka.py 16A` даёт «переразметка: 8: обязательная → письменная», а `tools/vidy_zadach.py` печатает `16A † 1`, `16α † 4`, `16ℵ † 0` — ровно те числа, что названы в составе волны. В БОЕВОЙ базе разметки нет: импорт меняет живые записи школы и на 16α трогает три ячейки «сверх источника» (10а, 10б, 10в). Это вопрос **[V2]**, а не забытый шаг.
- [F5] **done.** Дата у галочки, история клетки жестом и отсев тестовых нажатий с порогом 60 секунд — `tests/grid/test_istoria_kletki.py` + `tests/veb/test_istoria.py`, 44 passed. События журнала не удаляются: перебивка занятия сделана ДОПИСЫВАНИЕМ в отдельную таблицу `mark_lesson_override`, а append-only держат триггеры `001_init.sql`, а не договорённость. Позиция нашла и починила настоящий дефект данных: импорт записал 15847 строк под одним `recorded_at`, и отсев по времени потерял бы 735 настоящих отзывов — отсев переведён на канал кнопки.
- [F6] **done, и закрыто буквально.** Сверка идёт прямым SQL по снимку БОЕВОЙ базы, снятому `sqlite3.Connection.backup` СКВОЗЬ WAL (16188 событий, 57 школьников, 595 задач, 21 листок, 247 строк enrollment); проверочный скрипт не импортирует ни строки проектного кода, то есть сверяются две независимые реализации. Числа напечатаны рядом: «1а экран 16 SQL 16», «1б экран 15 SQL 15», «2 экран 12 SQL 12», «3 экран 10 SQL 10».
- [F7] **done.** Поиск ведёт на страницу группы; карточка школьника живёт отдельной страницей `/kartochka/<id>` и проверена НА БОЕВОМ сервере: 200, 52331 б, титул «Агаркова Ирина — Ключики». Гость видит верх, вошедший — галочки. Карточка строится из того же `_build_views`, что и экран распределения, поэтому не может разойтись с группой в том, кто принимает.
- [F8] **done.** Вкладка История занятий: `core/services/istoria_poseshchenij.py` и `veb/razdely/istoria_zanyatij.py`, `tests/sessions` — 29 passed. Гейт вёрстки после её появления вырос с 235 до 266 осмотренных элементов кондуита и остался по нулям — новая вкладка канон не сломала.
- [F9] **done, все три части.** `tests/veb/test_kabinet.py` — 17 passed. Вход преподавателя ведёт в отдельную вкладку «Кабинет»; отметка будущего отсутствия замораживает распределение ОТКАЗОМ НА ЗАПИСИ, а не серой кнопкой, и пишет ту же строку `teacher_attendance`, которую уже читает каркас — второго хранилища не заведено. «Лена вместо Елены» проверена на боевой странице: `prep-imya">Лена Мирошниченко`.
- [F10] **done, по всем трём каналам.** `tests/veb/test_vnesenie.py` — 12 passed, и это видно по именам: `tekst_tri_vnesenia_pishut_rovno_podtverzhdyonnoe`, `foto_…`, `golos_…`. Запрет записи без подтверждения закрыт отдельно — `draft_dver_nichego_ne_pishet`: дверь гипотезы физически не пишет в базу. Сверх задания: двусмысленное имя даёт КНОПКИ, а не догадку; отказ внешнего API показывается, а не проглатывается.
- [F11] **done, и у клаузы теперь есть РЫЧАГ, которого у неё не было трижды до этого.** `tools/gejt_verstki.py` судит РЕНДЕР в headless Chromium 1440×900 на живой базе и печатает три числа на страницу плюс ОХВАТ плюс список того, чего не проверяет. Самопроверка `--slomat` краснеет на подстроенном нарушении. Итог на боевом сайте: у ГОСТЯ на `/raspredelenie` было **48 обрезанных фамилий**, стало **0**; горизонтального скролла нет. Число 27 школьников в классе снято из живой базы, а не вписано константой.
- [F12] **done.** Условие выполнено честно: P1–P11 все приняты к 05:50, за пять часов до дедлайна, и только после этого P12 была запущена. Пароли школьников: `cbe60e9` выдаёт личный пароль каждому активному, `546b4e3` — вход узнаёт школьника и НЕ ДАЁТ ему роли вовсе, `0ea26cf` — человек заменяет выданный пароль своим. `tests/veb/test_vhod.py` + `tests/klyuchi` — 14 passed.
- [F13] **done, и это главное число ночи.** `pytest` на `main`: **1044 passed на входе → 1252 passed на выходе**, упавших **17 и на входе, и на выходе** — предсуществующий фон не сдвинулся НИ РАЗУ за девять влитий. Ни одна фича не была протащена ценой надёжности: дважды красное `main` останавливало выкатку (зависшее слияние в 03:00 и 32 красных в 03:40), и оба раза волна сначала возвращала `main` в зелёное. Бэкапы и безопасность не деградировали: живая база оркестратором не изменена, пароли владельца не использованы, ни один процесс не снят.
