# MANDATE — veb-raspredelenie

<!-- assembled by bootstrap_mandate.py; two halves, two authors; do not merge them -->

**STATUS:** `OPEN`
**TOP_HALF_STATUS:** `COMPLETE`
**BOTTOM_HALF_STATUS:** `PENDING`
**ARC:** `/sessions/epic-laughing-bardeen/mnt/GitHub/spetsmat-bot/zhurnal/2026-09-02_spetsmat-bot`
**ASSEMBLED:** `2026-09-03`

> Status is one of `OPEN` · `CLOSED` · `REFUSED`. `REFUSED` is a LAWFUL outcome and
> needs a written reason in the bottom half — refusing is not the same as stopping.
> The one outcome forbidden to the orchestrator is to stop and leave the wave
> untouched: a tool's refusal is a task, not an outcome
> (`skills/disciplina-orkestrator/SKILL.md`).

> Phase markers — `TOP_HALF_STATUS: COMPLETE` (this tool always writes the top
> half) and `BOTTOM_HALF_STATUS: PENDING` / `COMPLETE` (the orchestrator flips it
> on return). The linter REFUSES mismatch with STATUS: OPEN ↔ PENDING, CLOSED ↔
> COMPLETE. A reader without context can tell which half is done.

## HALF ONE — WRITTEN BY COWORK, BEFORE THE WAVE

### GOAL

A site reachable from other people's computers, over the bot's own database, where the three room heads change the distribution behind a password and everyone else reads it - plus the past year's conduit and a first place to record acceptance - so that tonight there is somewhere to do the distribution that is not one person's browser.

### INTERVIEW — RENDERED IN ENGLISH FROM A RUSSIAN CONVERSATION — 2026-09-03

> **ИНТЕРВЬЮ ПРОВЕДЕНО** (flag `--intervyu da` at assembly). ⚠ The flag proves the
> assembler was asked, not that the conversation happened — same honest limit
> `bootstrap_zahod.py --intervyu` already prints. ⚠ The interview was held in
> Russian and what is recorded here is the ENGLISH RENDERING of the settled
> meaning, not a quotation. A rendering can be wrong, and only the owner can
> say so.

- **Q1** — Q: Q1
  — M: The goal is a site other people can open and edit tonight; shared state is the point, not the pages.
- **Q2** — Q: Q2
  — M: Boundaries complete; reachability moved IN, the VPS moved OUT in favour of a tunnel, live sync moved OUT explicitly.
- **Q3** — Q: Q3
  — M: Failure is concrete and its first clause is a second machine opening the page.
- **Q4** — Q: Q4
  — M: Eight finalized items, each checkable against the database, the running site or the wave's own files.
  — note: Two items added after the interview reopened: free models everywhere with paid as escalation, and the orchestrator's autonomy to refuse, re-run and write follow-up zahody without asking.
- **Q5** — Q: Q5
  — M: The owner alone reads the bottom half, at acceptance, tonight.
- **Q6** — Q: Q6
  — M: Goal and boundaries are in English.

### FINALIZED AT INTERVIEW — 2026-09-03

- [F1] The distinguishing property of this wave over the owner's existing prototype is shared state on a server. Everything else he already had in a browser.
- [F2] P1 delivers what was promised for tonight and runs first, alone.
- [F3] Recording acceptance of problems is IN, in a basic form, and never as a second journal - through the existing marking and progress services.
- [F4] Two password levels this wave: teacher and organiser. Shared passwords from the environment, signed cookie, no usernames. The password also opens the past year's conduit.
- [F5] P4 is the past year's conduit for reading - 15 847 events already in the database - not the worksheet catalogue, which is done.
- [F6] Free models everywhere by owner's decision 2026-09-03: on measured work they beat the paid mid-tier. Paid is an escalation after failure, never a pre-assignment. The one exception is acceptance, which is never given to a free model.
- [F7] The orchestrator is autonomous and judged on the wave being DONE, not on rounds performed: it refuses positions, re-runs them, writes follow-up zahody itself, and reorders. It stops for the owner only on a costed fork, or on its own breakdown signal from the instruction.
- [F8] The orchestrator obeys INSTRUKCIYA-ORKESTRATORU-2026-09-03.md and the lift sheet PODYOM-VOLNY-sajt.md: state on disk every round, liveness by commits, verdicts by running the lever, UROKI written as it goes.

### BOUNDARIES AND WHAT IS ALREADY CLOSED

- IN, newly: the site must be reachable over HTTPS from another machine this wave. Shared editing is the whole point; a page that only runs on one laptop is the prototype the owner already has.
- OUT: buying and configuring the Russian VPS - blocked on a VPN problem and not on tonight's path; a tunnel from the owner's machine gives the same URL in minutes.
- OUT: pupil self-service accounts and pupil passwords - deferred 2026-09-03.
- OUT: live multi-user sync. Refreshing shows what others changed; saying so in the interface is part of the work.
- OUT: the teachers' attendance-share ledger kept by Natalia Pavlovna.
- OUT: the year's lesson schedule as a feature - a placeholder the organiser fills.
- CLOSED 2026-09-03: publishing 56 pupil surnames is not a concern.
- CLOSED 2026-09-03: rooms are 203 (NS), 302 (DM), 303 (IYa).
- CLOSED 2026-09-03: a teacher seeing the whole school is wanted behaviour; own pupils are highlighted, never filtered out.
- CLOSED 2026-09-03: compound acceptors are two weekday-keyed rows, not a modelling gap.
- CLOSED: the worksheet catalogue is built and deployed as the spetsmat-179 repository. This wave neither rebuilds nor restyles it.

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

### SCALE

One evening, five positions, all of them on free models. P1 runs first and alone because it creates veb/; P2-P5 fan out afterwards on disjoint files. A paid model is never assigned in advance - it is an escalation the orchestrator applies to a position that came back empty, died on context, or shipped defective twice.

### WHAT COUNTS AS FAILURE

The wave has failed if by the end of the evening the owner cannot open the distribution from a second machine and change it; if an edit made on one computer is invisible on another; if editing is not behind a password; if a pupil's debt is not on the same row as who accepts him; if a second store of standing assignments or a second journal of marks appears; or if UROKI-VOLNY-sajt.md comes back empty or written from memory.

## HALF TWO — WRITTEN BY THE ORCHESTRATOR, ON RETURN

> 🔴 **ЭТО ПРЕДОТЧЁТ, СНЯТЫЙ 2026-09-03 в 23:34. ВОЛНА НЕ ЗАКРЫТА.** `STATUS` остаётся
> `OPEN`, `BOTTOM_HALF_STATUS` остаётся `PENDING`, и это не оплошность: две позиции
> ещё идут, фаза знания не проведена, четыре условия закрытия не выполнены. Предотчёт
> написан по просьбе владельца, чтобы состояние было понятно НЕ ИЗ РАЗГОВОРА, а из
> артефакта. Всё, что ниже, снято командой в названное время; ни одно число здесь не
> из памяти. Незаконченное названо незаконченным.

### ГДЕ МЫ НАХОДИМСЯ — ОДНОЙ КАРТИНКОЙ, НА 23:34

```
                     что это           состояние            чем доказано
P1 распределение     страница+импорт   РАБОТАЕТ             прогон оркестратора: 200, 56 детей
P2 вход по паролю    кука+WAL          КОД СДАН, идёт       334 строки в git, 4 теста зелёные
P5 наружу+сторож     туннель+сторож    ДОРАБОТКА            снаружи 200; сторож ложно-зелёный
P3 приём задач       сетка отметок     ПЕРЕНОС на завтра    ваша ПРАВКА 3: стадия 2
P4 кондуит           архив на чтение   ПЕРЕНОС на завтра    ваша ПРАВКА 3: стадия 2
P6 снимок на Pages   статическая часть НЕ НАЧАТА, вопрос    основания нет: git не заведён
```

**Одной фразой: то, ради чего поднята волна, уже работает и проверено; осталось надеть
на него пароль, убрать следы проверок и отдать вам адрес.**

### ЧТО УСТАНОВЛЕНО ФАКТОМ — прогоны оркестратора, не отчёты позиций

**Свойство, которым судится волна — «правка на одном компьютере видна на другом» —
предъявлено в двух половинах, обе мои, обе с выводом команд.**

Половина первая, общее состояние (23:12):
```
POST /api/enrollment {"student_id":1,"teacher_id":16,"weekday":1}  → {"closed":2,"opened":48}
из живого процесса  → teacher_name: Александр Александрович Тертерян
kill <pid сервера>  → curl 000 (Couldn't connect)
подъём заново       → teacher_name: Александр Александрович Тертерян   ✅
в базе: (2, teacher 14, 2026-09-01 → 2026-09-03) закрыт · (48, teacher 16, → 9999-12-31) открыт
```
Правка легла ИНТЕРВАЛОМ, а не перезаписью. Это и есть отличие от прототипа с `localStorage`.

Половина вторая, доступ снаружи (23:14):
```
python3 -m veb.server --port 8790        локально 200
bash deploy/tunnel.sh 8790               https://a543a2e5e9a317.lhr.life
curl <URL>/                              СНАРУЖИ 200
curl <URL>/api/view?weekday=1            живое распределение: 56 школьников, 19 преподавателей
```
Снаружи пришла не заглушка, а настоящая страница. **Погашено сразу:** пароля ещё не было, а
редактируемое распределение без пароля названо провалом волны в верхней половине этого мандата.

**Импорт прошлого года — на живой базе, дважды, оба раза rc=0:**
`enrollment` 0 → 47 → **56**. Второй прогон уже с починкой составных приёмщиков.

**Оба запрета волны сняты командой, а не словами (23:16):**
```
git diff --stat <первый коммит волны>..HEAD -- bot/ core/ infra/ migrations/   → пусто
git diff --name-only main...<каждая ветка> | grep -E '^(bot|core|infra)/'      → 0, 0, 0
git grep 'CREATE TABLE' <ветки> -- veb/ tools/ deploy/ ops/                    → пусто
git grep 'INSERT INTO enrollment|UPDATE enrollment' -- veb/ tools/             → пусто
```
**Бот не тронут. Второго хранилища нет.** Запись в `enrollment` идёт только через
`EnrollmentService`.

**Полный прогон тестов на ветке P1 (23:31): `945 passed, 13 skipped`.** Волна не сломала бота.

### ЧТО СОБРАНО И ЗАПУЩЕНО

Пять заходов собраны генератором и налиты, все прошли `check_zahod.py` с `rc=0`. Работа в
ветках на 23:34, зоны не пересеклись НИ ОДНИМ файлом:

| ветка | коммитов | строк | файлы |
|---|---:|---:|---|
| `veb-raspredelenie-mvp` | 3 | 1441 | `veb/server.py`, `veb/templates/index.html`, `tools/import_raspredelenie.py`, 2 теста |
| `veb-vhod-i-obshchee-sostoyanie` | 1 | 334 | `veb/vhod.py`, `veb/sostoyanie.py`, `veb/static/vhod.css`, тест |
| `vykatka-tunnel-i-storozh` | 2 | 620 | `deploy/tunnel.sh`, `deploy/podnyat_sajt.sh`, `deploy/spetsmat-veb.service`, `ops/storozh_sajta.py`, тест |

Итого **2395 строк в 14 файлах**. Заходы P3 и P4 собраны, налиты, линтер зелёный — не пускались
по вашей ПРАВКЕ 3.

### ЧТО Я ПОЧИНИЛ САМ И ПОЧЕМУ ОНО БЫЛО СЛОМАНО

1. **Пересборка захода под бесплатную модель уничтожила бы его тело.** Подъёмный лист велел
   `--pereversborka`; по коду генератора этот флаг пишет файл ЗАНОВО из параметров, а тело P1
   дописано руками. Перевёл модель ПРАВКОЙ, тело цело.
2. **Живая база не в git, и в рабочей папке захода её нет.** `config.py` считает путь от своей
   папки — заход открыл бы ПУСТУЮ базу, импорт «прошёл» бы, тесты позеленели бы, а ваша база не
   сдвинулась. Вписал в заход абсолютный путь, ссылку и проверку числом `(15847,)` со стоп-сигналом.
3. **Стартовая команда захода обречена падать.** Генератор сам создаёт рабочую папку и сам же
   вписывает в команду `worktree add`, который на существующей папке даёт `rc=1`. Оркестр
   списывал это на модели и пометил павшими двух живых. Снял префикс.
4. **§0.1 велит запустить субагента, которого у бесплатного движка нет.** P5 потерял на поиске
   пять минут и весь контекст. Отменил субагента правкой в трёх заходах.
5. **Три позиции на одной бесплатной модели съели её квоту** — снаружи это выглядит как смерть
   модели. Развёл по разным, держу правило «не больше двух на модель».
6. **Спас 453 строки**, написанные P5 и не закоммиченные к моменту, когда надзиратель снял его
   за молчание.

### НЕОБРАТИМЫЕ ДЕЙСТВИЯ — названы все, `data/` вне git

1. **Импорт распределения в живую базу**, дважды. Копии до: `backups/spetsmat-do-importa-raspredeleniya.db`
   и `backups/spetsmat-do-otkata-probnoj-pravki.db`.
2. **Проверочная правка и её откат прямым SQL.** Чтобы доказать переживание перезапуска, я
   перевёл Агаркову Ирину на другого преподавателя. Откатить страницей оказалось нельзя: правка,
   сделанная сегодня, сегодня же даёт интервал нулевой длины, а схема требует
   `valid_from < valid_to`. Откатил `delete` + `update` (порядок обязателен, обратный даёт
   `IntegrityError`). **Агаркова снова у Полины, проверено.**
3. **Снял четыре утёкших ssh-туннеля** позиции P5 по номерам, счёт 4 → 0, посторонние не тронуты.
4. **Дописал `data` в `.gitignore`** — чтобы ссылка на живую базу из рабочих папок не уехала в git.

### 🔴 ЧТО ЕЩЁ НЕ СДЕЛАНО — и это главная часть предотчёта

1. **Следы проверок на живой базе не убраны.** Клауза «правка переживает перезапуск»
   доказывается только правкой живого ребёнка, и прогоны P1 переставили **Афанасьеву и
   Белеванцеву** с Насти на Полину. Убирается после того, как P1 завершится. **Пока не убрано —
   распределение показывать нельзя.**
2. **Вход не приделан к серверу.** `veb/vhod.py` написан и сдан, но зона P2 не включает
   `veb/server.py`, и связывает их приёмка — я, одной вставкой. Это следующий ход.
3. **Ветки не влиты в основную.** Три ветки, 2395 строк, всё в git и цело, но `main` их ещё не
   содержит.
4. **Адрес вам не выдан** — по пункту 1 и 2.
5. **Фаза знания не проведена.** 20 уроков написано ПО ХОДУ; их разбор свежей моделью, вердикты
   и баланс — в конце.
6. **P5 — вердикт `доработка`**, вписан в его заход: сторож ложно-зелёный.

### ВЕРДИКТЫ — на 23:34

| позиция | вердикт | основание |
|---|---|---|
| P1 | **пока нет** — идёт | 3 коммита, 945 тестов зелёные, две клаузы из пяти закрыты моим прогоном |
| P2 | **пока нет** — идёт | 334 строки в git, 4 теста зелёные, контракт соблюдён дословно |
| P5 | **доработка** | наружные 200 предъявлены; сторож рапортует «ЖИВ 200», проверяя `https://console.serveo.net` |
| P3 | **перенос** | ваша ПРАВКА 3: стадия 2 |
| P4 | **перенос** | ваша ПРАВКА 3: стадия 2; снят мной по номеру процесса в 23:11 |



### 🔄 ОБНОВЛЕНИЕ ПРЕДОТЧЁТА — СНИМОК ВТОРОЙ, 23:50

Первый снимок сделан в 23:34 и остаётся выше без правок: предотчёт ДОПОЛНЯЕТСЯ, а не
переписывается — иначе по нему нельзя увидеть, что менялось. Ниже только то, что изменилось за
эти минуты, и всё снято командой.

#### ЧТО ИЗМЕНИЛОСЬ К ЛУЧШЕМУ

**1. Все три ветки волны влиты в основную.** На 23:34 они лежали отдельно; сейчас `main` содержит
всю работу — 2395 строк в 14 файлах. Слияние сделали сами позиции последним ходом, ветку P5 влил я
(её заход был снят надзирателем раньше, чем дошёл до влития).

**2. Три настоящих вердикта вписаны в заходы, все по прогону рычага:**

| позиция | вердикт | чем снят |
|---|---|---|
| **P1** распределение | **`принято`** | импорт rc=0, `enrollment` 56; `GET /` = 200; правка ложится ИНТЕРВАЛОМ; переживает `kill`; `pytest tests -q` → **945 passed, 13 skipped** |
| **P2** вход | **`доработка`** | контракт и подпись куки хороши, но клаузы 1 и 3 сняты на сервере, куда его модуль не подключён |
| **P5** туннель | **`доработка`** | снаружи 200 предъявлен; сторож рапортует «ЖИВ», проверяя чужую страницу |

**3. Живая база чиста и проверена:** `enrollment` = **56**, все 56 открытые, интервалов, закрытых
сегодня, — **ноль**. Все три ребёнка, переставленные проверками (Агаркова, Афанасьева,
Белеванцева), возвращены своим преподавателям. **Долг, названный в первом снимке, ЗАКРЫТ.**

**4. Фаза знания начата, а не отложена на конец.** Урожай собран машинно:
`UROZHAJ-VOLNY-sajt.md` — **23 урока, у всех ЦЕНА числом, к доработке ноль**. Пять из них про
самого оркестратора.

#### 🔴 ГЛАВНАЯ НАХОДКА ВЕЧЕРА, КОТОРОЙ НЕ БЫЛО В ПЕРВОМ СНИМКЕ

**Две позиции из трёх сдали зелёное на подделке, независимо друг от друга, и обе были честны.**

```
P5:  5 зелёных тестов, сторож «ЖИВ 200»  → проверял https://console.serveo.net, баннер провайдера
P2:  4 зелёных теста, 6 зелёных клауз     → проверял сервер без своего же модуля
     проверка: без куки  grep 'Вход — Спецмат' → 0,  grep 'Распределение' → 2
```

Обе написали правду о том, что видели; обе измеряли не то, что называли. **Причина одна, и она
моя.** Зоны позиций разведены идеально — ни одного пересечения на 14 файлах, — и ровно поэтому
файл-роутер `veb/server.py` не вошёл НИ В ОДНУ зону. Без него ни вход, ни сторож не могли
подключиться к тому, что проверяли. Я развёл зоны так, чтобы позиции не подрались, и тем же ходом
отнял у них возможность проверить себя по-настоящему.

Это повторилось ТРИЖДЫ за волну: вход у P2, сторож у P5, кука у склейки. Правило на будущее
записано уроком: **разведение зон по файлам разводит и ответственность за стык; места стыка надо
называть и отдавать поимённо.**

#### ЧТО ИДЁТ ПРЯМО СЕЙЧАС

Заход `kod_sklejka-vhoda-s-serverom.md` — зона из одного файла `veb/server.py`, расширена
ПРАВКОЙ 1 до двух. Он приделывает вход к серверу. Два дефекта на его пути уже сняты:

1. **Кука не лезла в куку.** `_make_cookie` клала в ЗНАЧЕНИЕ куки сырой JSON — с пробелом,
   кавычкой и запятой, всеми тремя запрещёнными. Диагноз мой, командой:
   `rol()` на полном значении → `organizator`, на обрезанном по первому пробелу → `None`, а
   обрезает его любой настоящий клиент. Позиция билась вслепую: `vhod.py` не входил в её зону.
   Расширил зону, отдал диагноз — **починено, коммит `7962064`, проверено: запрещённых символов
   в куке нет.**
2. **`Set-Cookie` уходит без имени куки** — `Set-Cookie: eyJyIjog…` вместо
   `Set-Cookie: spetsmat_veb=eyJyIjog…`. Клиент такую куку не сохраняет, банка `curl` остаётся
   пустой, следующий запрос снова `302`. Позиция сейчас на этом. Причина в имени функции:
   `_make_cookie` читается как «сделает куку», а делает только значение.

#### ДОПОЛНЕНИЕ К СНИМКУ ВТОРОМУ — 23:53: ЭСКАЛАЦИЯ НА ПЛАТНУЮ

Склейка отработала на бесплатных ТРИ прогона и упёрлась. Правило подъёмного листа сработало
дословно: «позиция вернулась пустой, умерла на контексте или сдала брак ДВАЖДЫ → перезапускаешь
её платной». Здесь было и то, и другое: брак дважды (кодировку куки починила, имя куки — нет) плюс
один «ложный успех» — движок вернул `rc=0`, отказав по существу.

**Что бесплатные успели и что принято, а не переделывается:** вход приделан к серверу; защита
работает — проверено мной живьём, без куки приходит страница входа (`grep 'Вход'` → 1,
`grep 'Распределение'` → 0), распределение наружу не течёт; кодировка куки починена в base64url,
запрещённых символов в значении не осталось.

**Что осталось и отдано платной — ровно две вещи, обе названы точным кодом:**
1. `veb/server.py:313` отдаёт `Set-Cookie` БЕЗ имени куки. Банка кук клиента остаётся пустой
   (`grep -c spetsmat /tmp/jar` → **0**), войти невозможно. По коду ответа не видно: `302` при
   неудачном входе и `302` при правильном отказе неотличимы.
2. Семь тестов в `tests/veb/test_vhod.py` упали от смены формата куки — файл был вне зоны, теперь
   в зоне.

Запущена на `sonnet`, зона расширена до трёх файлов. **Это первая платная модель за волну:
до провала платную не трогали, как и велено.**

#### ЧТО ОСТАЛОСЬ ДО ВЫДАЧИ АДРЕСА — три хода, все мои

1. Дождаться склейки и снять её вердикт рычагом.
2. Прогнать сборку приёмки: подъём с паролями → туннель → **проверка снаружи РАЗЛИЧЕНИЕМ ТЕЛ**
   (без куки обязана прийти страница входа, с кукой — распределение; `200` этого не отличает, и
   на этом уже сели двое).
3. Отдать адрес и пароль организатора.

#### ЧТО НЕ ИЗМЕНИЛОСЬ И ЖДЁТ ВАШЕГО СЛОВА

Четыре вопроса ниже — без ответа. Главный по-прежнему **[V1]**: статическая половина из вашей
ПРАВКИ 2 стоит на несуществующем основании — в `spetsmat-179` нет даже git, хотя мандат числит
каталог выложенным.

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

### ВОПРОСЫ ВЛАДЕЛЬЦУ — ОТВЕЧАТЬ ПРЯМО ПОД ВОПРОСОМ (заполнено в предотчёте 23:34)

**[V1] Выкладывать ли `spetsmat-179` на GitHub Pages сегодня и класть ли туда снимок с фамилиями?**
ЧТО ЗАБЛОКИРОВАНО: вся статическая половина из вашей ПРАВКИ 2 и позиция P6.
ЧТО ИЗМЕРЕНО: и мандат, и подъёмный лист числят каталог листков ВЫЛОЖЕННЫМ («CLOSED: built and
DEPLOYED as the spetsmat-179 repository»). Проверено 23:12: `cd ~/Documents/GitHub/spetsmat-179
&& git log` → `fatal: not a git repository`. Папка собрана (`index.html`, 21 PDF, `build.py`),
git не заведён, remote нет, Pages нет. Рядом лежит `VYKLADKA.md` — инструкция на выкладку,
адресованная мне. `gh` авторизован как `d1-d57`, выкатка занимает 5–10 минут.
ПОЧЕМУ НЕ СДЕЛАЛ САМ: создание публичного репозитория под вашей учётной записью необратимо, а
`VYKLADKA.md` писалась ДО решения класть на ту же страницу снимок распределения с 56 фамилиями.
ФОРМА ОТВЕТА: «выкладывай каталог» · «выкладывай каталог и снимок» · «не сегодня».
ОТВЕТ ВЛАДЕЛЬЦА:

**[V2] Постоянное имя для динамической половины — чем платим?**
ЧТО ЗАБЛОКИРОВАНО: ничего сегодня; завтрашняя раздача ссылки трём организаторам.
ЧТО ИЗМЕРЕНО: `localhost.run` без учётной записи выдаёт СЛУЧАЙНЫЙ поддомен на каждое соединение.
Проверено дважды: адрес 23:06 через восемь минут отдавал `503 no tunnel here`. Значит закрыли
ноутбук — разосланная ссылка мертва, новая будет другой.
ФОРМА ОТВЕТА: «заводи `cloudflared` на мою почту» (бесплатно, постоянное имя, нужна ваша
регистрация) · «переживу случайный адрес, буду пересылать новый» · «жду VPS».
ОТВЕТ ВЛАДЕЛЬЦА:

**[V3] «Мика/Вася» — один преподаватель или два?**
ЧТО ЗАБЛОКИРОВАНО: правильность распределения у трёх детей — Рыбаков, Цикунов, Фёдоров.
ЧТО ИЗМЕРЕНО: в таблице `teachers` есть запись id 8 с именем «Мика/Вася». Импорт её не создавал:
преподавателей было 19 и осталось 19. Поэтому Кудишин, Симонова и Тухватулин-Йалчын получили по
ДВЕ строки на разные дни, как велит ваше решение о составных приёмщиках, а эти трое — одну строку
на слепленную запись.
ФОРМА ОТВЕТА: «разделить на Мику и Васю по дням, дни такие-то» · «оставить как есть».
ОТВЕТ ВЛАДЕЛЬЦА:

**[V4] Сухов Данил — в составе этого года?**
ЧТО ЗАБЛОКИРОВАНО: одно закрепление из книги прошлого года.
ЧТО ИЗМЕРЕНО: импорт отказал словами «no student with this surname+name in the catalogue». Он
есть в книге 2025/26 и его нет в списке 56 учеников.
ФОРМА ОТВЕТА: «завести» · «его нет в этом году».
ОТВЕТ ВЛАДЕЛЬЦА:

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
