# MANDATE — volna-vecher

<!-- assembled by bootstrap_mandate.py; two halves, two authors; do not merge them -->

**STATUS:** `OPEN`
**TOP_HALF_STATUS:** `COMPLETE`
**BOTTOM_HALF_STATUS:** `PENDING`
**ARC:** `/sessions/fervent-beautiful-mccarthy/mnt/GitHub/spetsmat-bot/zhurnal/2026-09-02_spetsmat-bot`
**ASSEMBLED:** `2026-09-04`

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

By tonight the site answers the two questions students arrive with - what am I solving and where do I go - and it answers them at a permanent address.

### INTERVIEW — RENDERED IN ENGLISH FROM A RUSSIAN CONVERSATION — 2026-09-04

> **ИНТЕРВЬЮ ПРОВЕДЕНО** (flag `--intervyu da` at assembly). ⚠ The flag proves the
> assembler was asked, not that the conversation happened — same honest limit
> `bootstrap_zahod.py --intervyu` already prints. ⚠ The interview was held in
> Russian and what is recorded here is the ENGLISH RENDERING of the settled
> meaning, not a quotation. A rendering can be wrong, and only the owner can
> say so.

- **Q1** — Q: Q1
  — M: Goal narrowed to the two things the owner called burning tonight, distribution and a permanent address.
- **Q2** — Q: Q2
  — M: Boundaries confirmed: the three night positions that do not burn today are cut.
- **Q3** — Q: Q3
  — M: Failure criterion is the three machine-checkable conditions; rework is explicitly not failure.
- **Q4** — Q: Q4
  — M: Repository is public. The owner corrected the analyst first reading: names are not secret because the school publishes the class list, so privacy buys nothing and would cost a paid plan for Pages.
- **Q5** — Q: Q5
  — M: The bottom half is read by the analyst at acceptance and by tomorrow session; one verdict line per position.
- **Q6** — Q: Q6
  — M: English prose accepted; no whitelist word was found missing.

### FINALIZED AT INTERVIEW — 2026-09-04

- [F1] The two burning things tonight are the distribution and a page at a permanent address - the owner named them; everything else is cut against these
- [F2] Login is needed for exactly ONE thing today: the organiser editing a distribution row. Every page reads without a login
- [F3] The repository is PUBLIC - the owner says names in a public repository do not matter because the school site already lists the class, and Pages from a private repository would need a paid plan
- [F4] Family names stay on the published snapshot - the earlier decision stands
- [F5] Reliability outranks features: alarm among teachers from any failure costs more than a feature, and on conflict the feature is cut
- [F6] Roster changes named by the owner: Mayorov and Emelyantsev leave, Ishkaev joins - but the head counts do NOT agree and the wave must print the disagreement rather than pick a number

### BOUNDARIES AND WHAT IS ALREADY CLOSED

- OUT: teacher login through Telegram, task acceptance, last year's conduit - the three night positions that do not burn today
- OUT: student progress behind a password, generated solutions, a teacher instruction page, a course map, outside adults
- OUT: password reissue, buying a VPS, student cabinets, a second marks journal
- OUT: the stop hook - it lives in disciplina where a separate wave is running
- ALREADY DONE, do not rebuild: the distribution page is accepted and works, including the organiser in-place edit; verified by command at assembly

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

Five passes, one evening, all on free models with paid only as escalation; the distribution page and the login already exist, so this wave finishes them rather than building from zero.

### WHAT COUNTS AS FAILURE

Failure is any of three, each checkable by command: the distribution page does not open without a login and show a room per child; the site has no address that survives a process restart; enrollment still holds 56 rows covering only 53 distinct children instead of two rows per child. A position ending in rework is NOT failure.

## HALF TWO — WRITTEN BY THE ORCHESTRATOR, ON RETURN

> Not written yet: the wave has not returned. STATUS stays `OPEN` until it has, and
> `--lint` says so out loud instead of passing in silence.

## ДНЕВНИК ОРКЕСТРАТОРА — ведётся по ходу, не после

> Заведён по требованию владельца 18:12. Здесь — где я нахожусь, что превратилось во
> что, и вопросы аналитику. Это канал связи: ответы на запросы владельца пишутся СЮДА.

### ЗАПИСЬ 1 · 2026-09-04 18:12 · ГДЕ Я НАХОЖУСЬ

**ГОРЯЩЕЕ ЗАКРЫТО. Распределение годно для отправки коллегам ПРЯМО СЕЙЧАС.**
Снято командой на живом сервере из `main`, минуту назад:

| требование владельца | замер | итог |
|---|---|---|
| открывается БЕЗ логина | `curl /raspredelenie` → **200** (было 302) | ✅ |
| все страницы без логина | `/` `/listki` `/listki-8` `/urovni` → **200 200 200 200** | ✅ |
| школьник · преподаватель · кабинет | «Агаркова Ирина · Полина · каб 203», «Аникина Анастасия · Настя · каб 302» — **56 школьников** | ✅ |
| организатор правит строку | вход паролем → кука; `POST /api/enrollment` → **200**; правка «Полина → Ваня» видна ПОСТОРОННЕМУ без куки | ✅ |
| правка без куки отклоняется | `POST` без куки → **302** | ✅ |

**ЧТО ПОТРЕБОВАЛОСЬ СВЕРХ РАБОТЫ ПОЗИЦИЙ.** Код ждал колонку `slot`, а в ЖИВОЙ базе
оставался `weekday`: позициям я намеренно раздал КОПИИ базы, чтобы две параллельные
записи не повредили живую. Миграцию на живую базу применил сам, через штатный yoyo,
имея резерв `data/REZERV-pered-volnoj-VECHER-1753.db` (3 874 816 байт).
Было: `weekday`, 56 строк. Стало: `slot`, 56 строк, раскладка `{1: 53, 2: 3}`.

**НЕОБРАТИМОЕ, ЧТО Я СДЕЛАЛ И ВЕРНУЛ — называю, потому что трогал живые данные.**
Проверяя правку организатора, я поменял преподавателя Агарковой на Ваню и вернул назад.
Возврат через интерфейс отдал `409`, поэтому вернул в базе руками: удалил новую строку
`id=58`, вернул `valid_to='9999-12-31'` строке `id=2`. Проверено после возврата:
56 строк, «Агаркова · Полина · каб 203», раскладка `{1: 53, 2: 3}` — состояние
в точности исходное.
🔴 **НАХОДКА ИЗ ЭТОГО:** откат правки через интерфейс НЕ РАБОТАЕТ — вернуть прежнего
преподавателя тем же способом нельзя, отдаёт `409`. Организатор, ошибившийся строкой,
своими силами её не починит. Это не держало волну, но это дефект, и он в долг.

### ЗАПИСЬ 2 · 18:12 · ЧТО ВО ЧТО ПРЕВРАТИЛОСЬ ЗА ВОЛНУ

* **S1** — три раза умирала (квота z-ai · зависание minimax-m3 на 35-й минуте при 0.9% CPU · неверная форма имени модели увела заход в чужой движок). Работу спасал коммитами дважды. Влилась. Схема переведена на слот, роуты добавлены. **Влитие сломало тесты main: 18 зелёных → 9 упавших**, потому что зона накрывала 2 файла из 8, где живёт `weekday`. Зона расширена, позиция в доборе.
* **S2** — не сделала НИЧЕГО за 14 минут: правила собственный файл-заход вместо работы. Причина — база в `.gitignore`, worktree её не видел, плюс общий файл-заход на 55 тысяч знаков. Обе причины устранены, позиция под отсечкой.
* **S3** — сделала ВСЁ: пять шаблонов, контракт имён соблюдён, 20 файловых ссылок из 20 живые, текст про уровни перенесён дословно. Данные не выдуманы, кроме одной строки — см. вопрос V3.
* **S4** — принято. Сторож перестал врать: 200 без нашего маркера теперь читается как «баннер», а не «жив».
* **S5** — сняла сплошной шлагбаум чтения, защиту правки сохранила. Влилась сама.

### ЗАПИСЬ 3 · 18:12 · СКОЛЬКО ОСТАЛОСЬ ВРЕМЕНИ

Дедлайн волны — **20:08**, сейчас 18:12. Остаётся **1 час 56 минут**.
Горящее закрыто, поэтому оставшееся время идёт на: зелёный `main` (S1 в доборе),
инструмент проверки состава (S2), приёмку S3 и S5, фазу знания.

### WHAT WAS ASSEMBLED AND LAUNCHED

<заполняется при закрытии волны>

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

- [V1] **ПОСТОЯННЫЙ АДРЕС ТУННЕЛЕМ НЕДОСТИЖИМ — нужно ваше решение.**
  ЧТО ЗАБЛОКИРОВАНО: второе из двух горящих дел — «страница по постоянному адресу».
  ЧТО ЗАМЕРЕНО: поднял сайт и туннель сам, прогнал ваш критерий дословно.
  Перезапуск САЙТА адрес переживает (`598c6edac618b6.lhr.life` → 302 до и после).
  Перезапуск ТУННЕЛЯ — нет: адрес стал `f0a4bf9fecabd2.lhr.life`. `localhost.run`
  на бесплатном тире даёт новый поддомен на каждое соединение. Ссылка, розданная
  преподавателям, умирает при перезапуске процесса.
  ФОРМА ОТВЕТА, одной строкой: «Pages» (нужна ваша учётка, репозиторий публичный —
  адрес будет постоянным) · или «платный поддомен у туннеля» · или «сегодня хватит
  сегодняшнего адреса, постоянный завтра».
  ⚠ Вы написали, что туннель поднимаете сами отдельным терминалом — тогда этот вопрос
  только про то, нужен ли ПОСТОЯННЫЙ адрес сегодня или можно завтра.

- [V2] **ТЕКСТ ПРО ТРИ УРОВНЯ — публиковать эту редакцию или ждать вашу?**
  ЧТО ЗАБЛОКИРОВАНО: ничего, страница готова и работает.
  ЧТО ЗАМЕРЕНО: источник `teksty/2026-09-04_post-pro-tri-listka.md` в шапке говорит
  дословно: «Владелец правил редакцию 1 у себя и пришлёт свою — тогда эта заменяется
  целиком». Сайт сейчас показывает редакцию 2.
  ФОРМА ОТВЕТА: «публикуй эту» · или «жди мою, пришлю».

- [V3] **ВРЕМЯ ЗАНЯТИЙ НА ГЛАВНОЙ ВЫДУМАНО — назовите настоящее или уберу строку.**
  ЧТО ЗАБЛОКИРОВАНО: ничего, но школьник прочтёт это как факт.
  ЧТО ЗАМЕРЕНО: на главной стоит «Время 16:00 – 19:00 (МСК)».
  `grep -rn "16:00" ../materials/spetsmat-2026/*.md` → ПУСТО. Источника нет.
  Рядом «Следующее — четверг, 16:00» вбито в шаблон жёстко и в пятницу будет врать.
  «Понедельник и четверг» — не выдумка, совпадает с базой.
  ФОРМА ОТВЕТА: «занятия с ЧЧ:ММ до ЧЧ:ММ» · или «убери строку про время».

- [V4] **ТРОЕ ДЕТЕЙ БЕЗ ЕДИНОЙ СТРОКИ РАСПРЕДЕЛЕНИЯ — они в курсе или нет?**
  ЧТО ЗАБЛОКИРОВАНО: числа состава не сходятся, и волне запрещено выбирать за вас.
  ЧТО ЗАМЕРЕНО: строк 56 · разных детей 53 · у 50 по одной строке · у 3 по две ·
  **у 3 нет ни одной**. На сайте они видны с пустым преподавателем и пустым кабинетом
  (например «Аракелова Дарья · None · каб None»). Ваше число «53» в точности равно
  числу детей, у кого есть хоть одна строка.
  ФОРМА ОТВЕТА: «трое без строк в курсе не участвуют» · или «участвуют, распредели их».

- [V5] **ОТКАТ ПРАВКИ ОРГАНИЗАТОРОМ НЕ РАБОТАЕТ — чинить сегодня или в долг?**
  ЧТО ЗАМЕРЕНО: поменял преподавателя через интерфейс — прошло (200). Вернул прежнего
  тем же способом — `409`. Пришлось править базу руками.
  ФОРМА ОТВЕТА: «в долг, завтра» · или «почини сегодня».

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
