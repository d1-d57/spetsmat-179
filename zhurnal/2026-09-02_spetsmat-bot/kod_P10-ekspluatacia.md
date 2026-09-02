# Канал исполнителя — P10-ekspluatacia (один заход до конца)
> Твой единственный файл-заход. Читай ТОЛЬКО его и названные якоря; проект не изучай.
<!-- собран bootstrap_zahod.py -->
> План/вопросы/отчёт — в секции внизу. Метрика — КАЧЕСТВО. Часы — норма.
> **Модель: openrouter/thinkingmachines/inkling:free** — эксплуатация: заход не трогает код бота, только обвязку вокруг него; модель жива по замеру 02.09 08:22 порогом 120 с.

## СТАРТОВОЕ СООБЩЕНИЕ ВЛАДЕЛЬЦУ

> Это блок для владельца — то, чем тебя запустили. Исполнителю здесь делать нечего, твоё задание ниже.

```
python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py worktree add P10-ekspluatacia --branch zahod/P10-ekspluatacia ; cd /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot-wt/P10-ekspluatacia && opencode run --auto --model openrouter/thinkingmachines/inkling:free '🔴 ОТМЕНА ОДНОГО ПУНКТА ТВОЕГО ЗАХОДА, ЧИТАЙ ЭТО ПЕРВЫМ. СУБАГЕНТА ГИТ-КОНТУРА §0.1 НЕ ЗАПУСКАЙ — пункт отменён оркестратором, данное указание сильнее текста захода; причина замерена соседней волной: четыре захода из десяти умерли ровно на этом вызове. Вместо всего блока §0.1 выполни САМ одну команду и вставь её вывод в ## ОТЧЁТ: git --no-optional-locks branch --no-merged main | grep -c zahod/ . | Дальше: твой заход — файл /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/zhurnal/2026-09-02_spetsmat-bot/kod_P10-ekspluatacia.md . Прочитай ТОЛЬКО его и то, что он называет; остальной проект не изучай. План/вопросы/отчёт пиши в этот же файл внизу (## ПЛАН / ## ВОПРОСЫ / ## ОТЧЁТ), НА АНГЛИЙСКОМ. Ничего сверх задачи не трогай. Субагентов не зови ни на что, кроме верификатора §3; коммиты делай САМ, по ходу работы, а не одним последним ходом. Ветку в конце вливаешь САМ, последним ходом, после коммита зоны. 🔴 Частей в задании несколько: делай ПО ПОРЯДКУ, коммить КАЖДУЮ отдельно; не успел — назови несделанные списком в ## ОТЧЁТ, это законный исход.' < /dev/null 2>&1 | tee /tmp/zahod-P10-ekspluatacia.log
```
🔴 **СТРОКА ГЕНЕРАТОРА ЗАМЕНЕНА — У НЕЁ ТРИ ИЗМЕРЕННЫХ ДЕФЕКТА** (все три выглядят
снаружи одинаково: «модель упала», лог 0 байт; замер 02.09, шесть сожжённых прогонов):
1. путь `spetsmat-bot/_generator/tools/orkestr.py` НЕ СУЩЕСТВУЕТ — генератор подставил
   объявленный корень владельца в путь чужого инструмента;
2. строка РЕКУРСИВНА — зовёт `orkestr.py progon`, а тот исполняет стартовую команду
   из этого же файла: надзиратель запускает надзиратель;
3. `&&` после `worktree add`, который на существующей папке даёт `rc=1` при живом
   состоянии — на повторе всё умирает до движка. Здесь `;`.

**Пускать ТОЛЬКО под надзором** (мандат: бесплатное руками не пускают — надзиратель
различает упал · молчит · потолок · ЛОЖНЫЙ УСПЕХ):
```
python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/orkestr.py /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/zhurnal/2026-09-02_spetsmat-bot \
  --rezhim progon --rod instrumenty --molchanie 1800 --potolok 14400 --popytok 3 \
  --zahody kod_P10-ekspluatacia.md
```
⚠ `--molchanie 0` НЕ значит «не убивать»: `orkestr` читает это как «лог не рос 0 секунд
⇒ молчит» и убивает прогон мгновенно (замер 02.09 09:54, один сожжённый прогон).

<!-- прежняя строка генератора, сохранена дословно, НЕ исполнять:

python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py worktree add P10-ekspluatacia --branch zahod/P10-ekspluatacia && cd /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot-wt/P10-ekspluatacia && python3 /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/_generator/tools/orkestr.py zhurnal/2026-09-02_spetsmat-bot --rezhim progon --dvizhok opencode --rod instrumenty --model openrouter/thinkingmachines/inkling:free --zahody kod_P10-ekspluatacia.md < /dev/null 2>&1 | tee /tmp/zahod-P10-ekspluatacia.log

-->

── СЧЁТ НЕЗАКРЫТОГО (печать, не гейт) ──
ГРАНИЦА ОБЛАСТИ: сырые подстроки в `kod_*.md` (пункт 4) — НЕ парсер очереди `dostavit_urok` (который считает только пары ДОМ:/ДОСТАВЛЕНО:). Разница в числах — законна.
🔴 снимок при сборке 2026-09-02, ПРОВЕРЬ ПЕРВЫМ ХОДОМ: `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/schet_nezakrytogo.py zhurnal/2026-09-02_spetsmat-bot`
Область: «zhurnal/2026-09-02_spetsmat-bot» — сужены пункты 1, 3, 4; долги (2) глобальны намеренно (DOLG.md не размечен по записям).
Приоритет владельца: разобрать инциденты важнее, потом закрыть долги — неразобранный инцидент это повторяющаяся ошибка, долг может подождать.
  1. инцидентов без вердикта             : н/д — VERDIKTY.md/INCIDENTY.md не найдены
  2. долгов СТАТУС: ЖИВ                  : н/д — /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/skills/slajdy/DOLG.md недоступен (другой git-репозиторий)
  3. уроков фабрике без ВЕРДИКТ          : 7
  4. пунктов очереди «ДОСТАВЛЕНО: нет»   : 29
     из них разбором очереди (парсер `dostavit_urok`, записи с парой ДОМ:/ДОСТАВЛЕНО:): 15
       живых (чинится доставкой — «дом есть»)  : 3
       к владельцу (решение за человеком)      : 8
       адрес недоступен (нет/папка/код/указат.) : 2
       адрес не разобран                        : 0
       отработавших (машинный след закрытия)    : 0
       доставлено                               : 2
       🔴 не проверяется машиной: содержательная отработанность записей БЕЗ следа закрытия (метки в доме, строки ✅/ЗАКРЫТО) — нужна ревизия человеком; сырой греп сверх разбора — шаблонные строки формы.

КОНТЕКСТ. `spetsmat-bot` — телеграм-бот кондуита спецмата 179-й школы: 56 учеников,
18 преподавателей, три аудитории, два занятия в неделю. Прошлый этап: P1 (ядро),
P2 (импорт прошлогодних данных) и P3 (регистрация и три роли) приняты и влиты в `main`;
`make check` на `main` зелёный, 148 тестов. Бот как программа существует, но нигде не
развёрнут и ничем не присмотрен: ни systemd-юнита, ни бэкапов, ни скрипта выкатки.
ЦЕЛЬ: обвязка вокруг бота — чтобы он поднимался сам, переживал обрыв сети, не терял
базу и не выкатывался посреди занятия.
Приёмка — по ОТЧЁТУ, без построчной сверки. Если стоп до цели: получишь юнит, бэкапы и
скрипт выкатки, но НЕ реальный сервер — VPS вне волны, это отдельное решение владельца.

## ЧТО ФИНАЛИЗИРОВАНО НА ИНТЕРВЬЮ

ИНТЕРВЬЮ ПРОВЕДЕНО: да (2026-09-02) — флаг `--intervyu da` при сборке. ⚠ Он доказывает, что аналитик не ЗАБЫЛ про интервью, и НЕ доказывает, что разговор был.

1. бэкап делается VACUUM INTO, никогда cp: cp берёт файл посреди чужой транзакции и в режиме WAL теряет боковые файлы
2. бэкап, который не проверяли, бэкапом не является — проверка восстановления это отдельная задача, а не приложение к бэкапу
3. выкатка в часы занятий запрещена скриптом: два процесса с одним токеном дают TelegramConflictError

## КОНТРАКТ ЗОНЫ (обязателен — не удалять; вписан Cowork)
- **МЕСТО РАБОТЫ:** **рабочая папка `/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot-wt/P10-ekspluatacia`** — ТОЛЬКО ДЛЯ КОДА (worktree захода, ветка `zahod/P10-ekspluatacia` в ней уже стоит). 🔴 **ДАЛЬШЕ — ТОЛЬКО ПУТИ ОТНОСИТЕЛЬНО ЭТОЙ ПАПКИ** (или `cd` в неё безусловно, каждым ходом): абсолютный путь в главную папку репозитория здесь — типичная ошибка, правка утекает МИМО worktree и найдётся только на коммите («вне git» в `git_zona.py check --zone` из рабочей папки, на файле, который уже правил, — цена, оплаченная живьём: 5 файлов, ручное копирование и откат главной папки). 🔴 `git checkout` в основной папке ЗАПРЕЩЁН: рядом идут другие заходы, переключение подменит файлы у них под ногами. 🔴 **Сам файл-заход (этот `.md`) при этом остаётся в ОСНОВНОЙ папке репозитория** — один экземпляр, не копия в рабочей папке: ПЛАН/ВОПРОСЫ/ОТЧЁТ/УРОКИ пишешь в него по абсолютному пути, названному в стартовой строке, а сам файл НЕ коммитишь — это делает аналитик при приёмке (цена обратного правила — полсуток 03.08: отчёт писали в рабочую папку, владелец и приёмка её не видели, приёмка трижды объявила отчёт пустым). 🔴 **Ветку в конце вливаешь САМ, последним ходом, после коммита зоны** (решение владельца 25.08; полный порядок печатает WARNING-блок ниже).
- **ЗОНА (можно менять):** `deploy/` `ops/` `tests/ops/`. Всё вне — **READ-ONLY**: не править, не двигать, не удалять, не рефакторить «заодно».
- 🔴 **ЗАВЁЛ НОВЫЙ `.md` — РЕГИСТРИРУЕШЬ ЕГО САМ, ТЕМ ЖЕ ХОДОМ, ОДНОЙ КОМАНДОЙ:** `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/register_doc.py <путь> "<описание>"` (из корня репо). `_studio/docs/` тебе по-прежнему READ-ONLY **для правки руками** — дверь ровно одна, и это она. Дверь идемпотентна (повторный вызов дубля не заведёт) и отказывает на пути вне `_studio/`, на несуществующем файле и на пустом описании. Свой файл-заход регистрировать не нужно: он рождается зарегистрированным из `bootstrap_zahod.py`. **Красный хук на ТВОЁМ новом `.md` — это не повод для `--no-verify`, а повод позвать дверь.** *Почему правило существует и почему оно теперь исполнимо: 26.07 оно записано с ценой в пять документов-сирот и через два дня повторилось дословно. Дальше стало хуже: до 30.07 указания «зарегистрируй» и «`docs/` только на чтение» противоречили друг другу, выход был ровно один — обойти хук, и по автологу `_INFRA-git/INCIDENTY.md` это 28 обходов `--no-verify` из 56 срывов коммита, 27 из них по одной этой причине (48 % всей боли с коммитами, тринадцать исполнителей подряд). Обходить больше нечего.*
- **КОММИТ:** два хода — `add` по своим путям, затем `commit` **с теми же путями после `--`** (полная форма и цена каждого хода — §4); коммить ПО ХОДУ работы, не одним последним ходом (§4). НИКОГДА `-A` / `.` / `commit -am`, и никогда `commit` без путей. Субагенты не коммитят. **`--no-optional-locks` обязателен:** обычный git переписывает индекс, берёт `.git/index.lock` и роняет параллельный ручной коммит владельца.
- **SCRATCHPAD — ТОЛЬКО ЛИЧНЫЙ.** Черновики, выкладки, промежуточные версии — в личную папку СВОЕГО захода `scratchpad/P10-ekspluatacia/`. Общие пути (`scratchpad/otchet.md`, любой `scratchpad/*` без имени твоей темы) ЗАПРЕЩЕНЫ: чужой отчёт уедет в твой файл или твой — в чужой, а приёмка читает отчёт без построчной сверки и подмену НЕ ЛОВИТ по построению. *Цена 25.08: готовый `## ОТЧЁТ` захода konvejer-incidentov был записан в общий `scratchpad/otchet.md`, и 92 строки чужого отчёта простояли в `kod_slovari-v-kod.md`.*
- 🔴 **Звал `register_doc.py` — допиши `_studio/docs/KARTA.md` к своим путям В ОБОИХ ходах.** Строка регистрации лежит физически в нём. Ворота 5 читают `§6` **с диска**, а не из индекса: коммит без этого файла пройдёт ЗЕЛЁНЫМ, документ уедет сиротой, а строка умрёт при первом `checkout` (дата данных 2026-07-30, найдено верификацией захода «kod_registracia-bez-obhoda.md»).
- **ЗАПРЕТ:** ничего за пределами зоны, даже если «мешает» или «чинится в одну строку». Нашёл проблему вне зоны → в отчёт, не трогай.

## 0. ПЕРВЫЙ ХОД
### 0.1 🔴 ГИТ-КОНТУР — ДО ВСЕГО ОСТАЛЬНОГО, И ПЕРВЫМ ХОДОМ ЦЕЛИКОМ

🔴 «ничего сверх задачи» относится к СОДЕРЖАНИЮ работы; git-контур §0.1 — законное исключение, он про состояние репозитория и исполняется целиком.

🔴 **ПОРЯДОК ЗДЕСЬ — ЧАСТЬ УСТРОЙСТВА, А НЕ ОФОРМЛЕНИЕ. Сначала субагент вливает названные через `--vlit` ЧУЖИЕ ветки В ОСНОВНУЮ, и только ПОТОМ ты заводишь свою рабочую папку; СВОЮ ветку он не трогает никогда — её вливаешь ты сам последним ходом (граница прав ниже).** Пока влитие шло в ветку захода, а влитие в основную было ходом приёмки (которая из песочницы в `.git` писать не может), работа копилась лестницей в последней ветке цепочки, а основная не получала ничего — замер 14.08: 14 невлитых веток, цепочка из пяти внутри последней, 84 невывезенных коммита, и генератор в основной папке не знал о собственных улучшениях. Заводя ветку ПОСЛЕ влития, ты отпочковываешь её от основной, которая уже всё содержит: инструмент оказывается на диске сам, дотаскивать нечего.

**1. ВЕСЬ КОНТУР — В СУБАГЕНТА, ОДНИМ ХОДОМ, ДО СВОЕЙ ПАПКИ.** Очередь заявок, влитие названных веток в ОСНОВНУЮ, что забрать в git по ходу и что погасить после — на содержание твоей задачи не влияют. Запусти ОДНОГО субагента, дождись его и вставь его шесть строк в `## ОТЧЁТ` дословно; сам эти пункты не исполняй. 🔴 ПОРЯДОК ПРИ ПАДЕНИИ ЭТОГО ВЫЗОВА — исполняй, не изобретай (движок роняет `network_error` на вызове субагента и уносит с собой ВЕСЬ заход, замер волны 3A — 4 захода из 13). Пауза 45 секунд, до трёх попыток; время меряй `date`, не суммой своих `sleep`. После третьей — работай БЕЗ субагента: контур остаётся неразобранным, и это ОТДЕЛЬНАЯ строка в `## ОТЧЁТ`, а не молчание. У него ОТДЕЛЬНЫЕ ПРАВА, объявленные в его же промпте: главная папка, основная ветка, вывоз — и ничего сверх; зону захода он не коммитит, её коммитишь ты сам, по ходу работы (§4). 🔴 ОТВЕТ ЛЮБОГО субагента, которого ты запускаешь (не только этого), обязан КОНЧАТЬСЯ строкой «выдано N позиций из M найденных»: канал мог оборвать его молча, и без этой строки усечение неотличимо от честного «мало нашлось». Нет строки — ответ усечён, в `## ОТЧЁТ` не вставляй, перезапроси. Полный текст задания печатает команда:
```
python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/bootstrap_zahod.py --zadanie-subagentu --zone deploy/ --zone ops/ --zone tests/ops/ --kommitit 'deploy/ ops/ tests/ops/' --zakryt 'влить ветку zahod/P10-ekspluatacia в main последним ходом, после коммита зоны'
```

🔴 ГРАНИЦА ПРАВ, ЧЕТЫРЕ ОТВЕТА (та же, что в самом задании субагенту — одно место в тексте, а не пересказ): **кто вливает ЧУЖИЕ названные (`--vlit`) ветки** — субагент, в ОСНОВНУЮ ветку, до заведения твоей папки; **кто вливает СВОЮ ветку этого захода** — ты сам, последним ходом, после коммита зоны (`git_zona.py vlit-v-osnovnuyu`; решение владельца 25.08 — оно сняло противоречие волны 4, когда машинное §0.1 и текстовое «ветку НЕ вливать» спорили молча, и машинное побеждало); **кто закрывает заявки** — субагент, `zayavka-zakryt`; **кто коммитит пути ВНЕ зоны захода** — субагент (хвост Cowork и что назовёт пункт 3 его задания). Ты коммитишь ТОЛЬКО зону этого захода, по ходу работы (§4). 🔴 Конфликт на `README.md` при ЛЮБОМ слиянии разрешается ОБЪЕДИНЕНИЕМ записей реестра, НИКОГДА выбором стороны: параллельные заходы волны дописали в реестр по строке — обе записи правы, выбор одной молча уничтожает регистрацию соседа.

**2. ТЕПЕРЬ ЗАВОДИ СВОЮ РАБОЧУЮ ПАПКУ** (команда — в блоке «МЕСТО РАБОТЫ» выше) и работай в ней как обычно. Её ветка отпочкована от свежей основной, поэтому инструмент, которым ты работаешь, уже на диске — отдельного «влить перед работой» больше нет.

вливать нечего, проверено командой `git branch --no-merged` — но проверено ПРИ СБОРКЕ, а не сейчас: невлитых `zahod/*`-веток было 0. 🔴 снимок при сборке 2026-09-02, ПРОВЕРЬ ПЕРВЫМ ХОДОМ: `git --no-optional-locks branch --no-merged main | grep -c 'zahod/'`. Число могло устареть между сборкой и твоим прогоном — 14.08 заход нёс ровно этот ноль, а к прогону невлитых было три.


- деплоя в этом заходе нет.

- `cd /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot-wt/P10-ekspluatacia` — рабочая папка ДЛЯ КОДА. Ветку НЕ переключай: `zahod/P10-ekspluatacia` в ней уже стоит.
- Проверить, что на месте: `git rev-parse --abbrev-ref HEAD` → должно быть `zahod/P10-ekspluatacia`.
- ПЛАН/ВОПРОСЫ/ОТЧЁТ/УРОКИ ФАБРИКЕ пиши в ЭТОТ файл — он в основной папке, не копируй его в рабочую.
- Точка отката: `git add deploy/ ops/ tests/ops/` → commit (или zip), если зона не чиста в HEAD (не фабрикуй, если чиста).
- Прочитать ТОЛЬКО: `названные файлы-якоря`. Проект не изучай.
- ПЛАН — в `## ПЛАН` перед действиями.

## 1. ДИСЦИПЛИНА (Карпатов)
🔴 **Код возврата — ПЕРВЫМ, до содержательного вывода команды.** «Отработала» и «упала, а я читаю прошлое состояние» выглядят одинаково; сначала `echo $?`, потом выводы. То же с гейтами. *Цена 21.07: `rc=128` (сбой прав окружения) четырежды прочитан как результат — едва не откатили верное правило по ложным данным.*
Предпосылки/развилки назвать вслух; минимум без спекуляций; хирургия (строка → к заданию); критерий, который может провалиться. Якорные замены — abort при ≠1. Сохранять по умолчанию. **Оспорить ложную предпосылку — включая КРИТЕРИЙ ГОТОВНОСТИ: считаешь его кривым — скажи в `## ПЛАН`, ДО работы, и предложи поправку.** Субагенты: ≤5, рейт-лимит = отступить + доложить (не слепой ретрай).

🔴 **Пишешь содержательный текст — термин НЕ употребляется раньше, чем определён**, включая заголовки, подводки и формулировки теорем. «Определение в тексте есть» не считается: если оно ниже первого рабочего употребления, читатель встаёт ровно там. Чинится ПЕРЕСТАНОВКОЙ определения вверх, не дописыванием пояснения. Гейт: `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/check_termin.py <src>` (exit 1 при нарушении). Канон — `../docs/kak-delat/STANDART-teksta.md` правило 11. *Цена 30.07: теорема пользовалась словом «ординал», определение стояло строкой ниже; поймал владелец, ни один гейт не увидел, раздел переписан дважды.*

## 2. ЗАДАЧА

🔴 **WRITE YOUR `## ОТЧЁТ`, `## ПЛАН` AND `## ВОПРОСЫ` IN ENGLISH, AND EVERY FILE AND EVERY COMMIT MESSAGE YOU PRODUCE TOO.** Owner's decision 30.08. It is a каркас-level rule, not a preference — wave 2 lost it twice because the pass text listed the report SECTIONS and never said «every file you create». Fixed Russian addresses stay Cyrillic: `ЦЕНА:` · `ВЕРДИКТ:` · `ДОМ:` · `ДОСТАВЛЕНО:` · `ПОДЪЁМ:` · `[ДОЛГ: …]` · every `## ` heading of this file · every path and command.
You build the harness AROUND the bot: it must come up by itself, survive a broken network,
never lose the database, and refuse to deploy during a lesson. You do NOT touch the bot's code —
`bot/`, `core/`, `infra/` are read-only to you.

⚠ **There is no server yet, and getting one is NOT your job.** Moving the owner to Russian
hosting with a proxy is his decision, explicitly out of this wave. You write the unit, the
scripts and the checks so that they are testable HERE, on this machine, and deployable later.
Everything you write must have a way to be proven WITHOUT a VPS — say in the report how each
piece was proven.

### 1 · systemd unit

`Restart=always`, `RestartSec=5`, `StartLimitBurst=5` per 5 minutes. Five crashes in a row means
broken CODE, not a broken network — the unit stops instead of looping forever. **But a stop
nobody hears is the same as no stop:** `OnFailure=` fires an alert through a SECOND bot (the
alerter has no code of its own, so it has nothing to crash with).

🔴 **The most frequent real failure, by the owner's own list, is forgetting `systemctl enable`** —
the bot then lives until the first reboot. Your install script does it and your check proves it.

### 2 · 🔴 The watchdog must be pinged from INSIDE the polling loop

The nastiest failure: the connection is dead at TCP level, there are no timeouts, the bot is
silent, the process is alive, and systemd is perfectly happy. `WatchdogSec` catches it ONLY if
the process reports "I am alive" from a place that PROVES `getUpdates` is answering — never from
an independent timer, which would keep pinging beside a dead poll.

⚠ The ping belongs inside `bot/`, which is read-only to you. So: write the unit and the check,
and name in `## ВОПРОСЫ` the exact one-line hook the bot must call, so the next position wires it.
Do not edit `bot/` to make your own check pass — that is the whole discipline of this wave.

### 3 · Backups — and the check that they can be restored

- **`VACUUM INTO`, never `cp`.** `cp` takes the file mid-transaction and in WAL mode loses the
  side files; the result looks valid and restores "almost". For our size `VACUUM INTO` is
  milliseconds.
- **Schedule tied to LESSONS, not to days**: a snapshot before the lesson starts, one right
  after, one daily. Then the worst possible loss is one lesson, not one day.
- gzip, local rotation 14 days.
- 🔴 **Backups do NOT go into a Telegram channel.** That is a transfer of children's personal
  data to a third-party operator outside the perimeter, and the best available leak vector.
- 🔴 **The restore check is a SEPARATE task, not an appendix to the backup.** Weekly: unpack the
  latest snapshot, check integrity, and assert that there are no fewer than fifty students and
  that the latest mark is not older than a week. All three must pass before a ping goes out;
  silence means alarm. **A backup nobody restored is not a backup** — by the owner's own list
  this is the most expensive failure of all, because it is discovered only when it is needed.

### 4 · Deploy script — and its most useful line

`git pull` + `yoyo apply` + `systemctl restart`, downtime 2–5 seconds. Updates are not lost:
Telegram keeps them a day and re-delivers. You can only lose them by two acts of your own —
dropping pending updates at start, or killing the process instead of stopping it gracefully.

🔴 **The single most useful line in the whole script is the refusal to deploy on lesson days and
hours.** It has saved more projects than any architecture. Two instances of one bot cannot poll
Telegram at once — the second gets `TelegramConflictError`.

Blue-green is not merely redundant here, it is impossible, for the same reason.

### 5 · Timezone — UTC on the system, Moscow in the code

Russia has no daylight saving, Germany does. With the system zone set to Berlin the timetable
moves by an hour twice a year. System stays UTC; Moscow time is obtained in code through
`ZoneInfo(TZ_DISPLAY)`, never `timedelta(hours=3)`.

### 6 · Also on the owner's measured list of what actually breaks

Disk filled by logs left at debug level after debugging (set a journal limit); OOM from unclosed
sessions; `database is locked` exactly when several teachers mark at once (WAL and `busy_timeout`
are already in `config.py` — assert they are actually applied, do not assume); expired root
certificates on a long-unupdated system.

**КРИТЕРИЙ ГОТОВНОСТИ (может ПРОВАЛИТЬСЯ), каждая команда печатает ЧИСЛО:**

    cd /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot-wt/P10-ekspluatacia
    make check
        # rc=0; печатает «N passed», N больше того, что было до тебя
    python3 -m pytest tests/ops -q
        # rc=0; не менее 6 проверок: 3 порчи снимка × 2 сценария времени выкатки
    bash deploy/vykatka.sh --proba --chas-zanyatia
        # rc≠0 И печатает причину отказа — ЗЕЛЁНОЕ ЗДЕСЬ ЕСТЬ ПРОВАЛ ПОЗИЦИИ
    python3 tools/proverka_vosstanovlenia.py --na-porchennom
        # rc≠0 И печатает, какая из трёх проверок покраснела — ЗЕЛЁНОЕ ЗДЕСЬ ЕСТЬ ПРОВАЛ

🔴 Две последние команды обязаны КРАСНЕТЬ. Проверка, которая не умеет покраснеть, — надежда,
а не проверка. Отрицательный вердикт несёт охват В СЕБЕ: «покраснело 3 из 3 порч».
**Отрицательный вердикт несёт ОХВАТ В СЕБЕ:** не «дыр не найдено», а «дыр не найдено, проверено X из Y». Без охвата вердикт не принимается — «проверено 2 из 9» и «проверено 9 из 9» выглядят одинаково.

## 3. ВЕРИФИКАТОР (если двигаем/теряем/жмём)

Верификатор нужен, тип — **ПОСЛЕ-типа** — судит результат, стоит в конце, после задачи. Свежий субагент, ДРУГИМ методом (порча и восстановление: испортить снимок базы — проверка восстановления обязана покраснеть; выкатить в час занятия — скрипт обязан отказать), не перечитывает свою же правку. Доля сплошной выборки: 3 порчи × 2 сценария времени = 6 проверок, ложно-зелёных 0. Финальная строка ответа обязательна дословно: «выдано N позиций из M найденных» — без неё ответ считается усечённым и в отчёт не вставляется.

## 4. 🔴 КОММИТ СВОЕЙ ЗОНЫ — ПО ХОДУ РАБОТЫ, НЕ ОДНИМ ПОСЛЕДНИМ ХОДОМ
Ты работаешь host-side и в `.git` ПИШЕШЬ — значит коммитишь САМ, никому не передавая. Каждую завершённую часть работы коммить СРАЗУ, теми же двумя ходами — не копи всё к финальному ходу:
```
git --no-optional-locks add -- deploy/ ops/ tests/ops/                     # вводит НОВЫЕ пути в индекс
git --no-optional-locks commit -m "<что сделано>" -- deploy/ ops/ tests/ops/   # отсекает всё чужое
python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone "deploy/" && \
    git_zona.py check --zone "ops/" && \
    git_zona.py check --zone "tests/ops/"   # из корня репо; должен быть ✅
git --no-optional-locks show --stat                        # обязаны быть ТОЛЬКО твои пути
```
🔴 **КОММИТЬ ПО ХОДУ — РЕШЕНИЕ ВЛАДЕЛЬЦА 25.08 (В11), ПЕРЕВЕРНУВШЕЕ прежний канон «одним последним ходом».** Цена прежнего канона: за сутки ДВА обрыва — канал `opencode run --auto` односторонний и умирает вместе с сессией (владелец закрыл ноутбук), и незакоммиченная работа пропадала целиком. Закончил кусок — закоммитил его; последний ход только ПРОВЕРЯЕТ, что коммитить нечего (`git status --porcelain` пуст, `git_zona.py check --zone` ✅).
🔴 **ОБА хода обязательны, ни один не лишний** (полное «почему» и цена — `../docs/kak-delat/GIT-disciplina.md §3`):
- **`add`** — pathspec-коммит знает только **отслеживаемые** пути; новый файл без `add` даёт `did not match any file(s) known to git`.
- **`-- <пути>` в самом `commit`** — иначе `commit` забирает индекс ЦЕЛИКОМ, вместе с чужим, застейдженным кем угодно рядом с тобой (репо `materials/` общий, писателей трое). *Обе половины оплачены 21.07 в один вечер: голый `commit` подмёл чужой индекс — коммит на 89 файлов вместо трёх; «починка», убравшая `add`, завалила все 10 коммитов повторно.*
⚠ **Хук `pre-commit` покраснел — сначала посмотри, на ЧЬИХ путях.**
- Красное на ТВОИХ путях (новый `.md` не зарегистрирован в `../../docs/KARTA.md §6`, битая ссылка) — **чини, не обходи**: там только твоё, обходить нечего.
- Красное на ЧУЖОМ, унаследованном долге (ворота дают сотни ❌ старых нарушений) — законный обход, но ТОЛЬКО с причиной; голый `--no-verify` инструмент отклонит, а причина сама уедет в `INCIDENTY.md`:
```
python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py commit --zone <зона> \
    --no-verify "чужой долг: <что именно покраснело>" -m "<что и зачем>" --push
```
Ту же причину назови отдельной строкой отчёта долгом. *Урок 9: обход был законен по канону и не существовал в инструменте — первый же коммит владельца встал на чужом долге.*
**Коммит не прошёл по ВНЕШНЕЙ причине** (чужой лок, конфликт, detached HEAD) — чужое состояние репозитория НЕ чини: зафиксируй файлы и напиши в отчёт отдельной строкой «коммита нет, причина такая-то, нужно ваше действие». Это законный отчёт. Молчаливое «сделано» при незакоммиченной зоне — брак: приёмка гоняет тот же гейт первым ходом и завернёт отчёт, не читая (`RUKOVODSTVO §Приёмка`, гейт 0).

## 4.1 🔴 ГИГИЕНА — ПРОВЕРКИ ПЕРЕД СДАЧЕЙ (вшито `bootstrap_zahod.py`; исполнителю НЕ удалять)
> Раздел про СОСТОЯНИЕ РЕПОЗИТОРИЯ после твоей работы, а не про правильность
> этого файла и не про планы: правильность файла судят С1/С3/С7 `check_sborki.py`
> ДО прогона, намерение «что влить/коммитить/закрыть» — блок §0.1 ГИТ-КОНТУР.
> Здесь не повторяется ни то, ни другое. Каждый пункт — КОМАНДА; её вывод, а не
> пересказ, уходит в `## ОТЧЁТ`. Пункт неприменим — так и напиши: «неприменимо,
> потому что …». **Молчание читается как «не сделано», а не как «всё чисто».**
> ⚠ `Г1`–`Г6` ниже — пункты ЭТОГО раздела. Гейты `priyomka.py` (`Г7` в секции
> `## ВОПРОСЫ`) — ЧУЖАЯ семья с той же буквой: их гоняет приёмка, не ты.
> Столкновение нумерации нашёл свежий исполнитель, читавший только этот файл.

**ЗОНА ГИГИЕНЫ:** `deploy/` `ops/` `tests/ops/`

- **Г1. Зона доехала в git.** `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone deploy/` → ✅; `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone ops/` → ✅; `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone tests/ops/` → ✅. Красное на любой из команд — отчёт не принимается: приёмка гоняет их все первым ходом.
- **Г2. Второй репозиторий.** **неприменимо, и это проверено при сборке, а не предположено:** все пути зоны лежат внутри репозитория `spetsmat-bot` (тот же критерий, что у С2 `check_sborki.py`). Зона расширилась за его пределы по ходу — пункт снова применим; команда та же, что в применимом случае: `cd ../<репозиторий> && git --no-optional-locks status --porcelain` → пусто. *Команда названа и здесь нарочно (находка верификатора): пункт, который объявлен неприменимым и не говорит, ЧТО делать, когда станет применим, исполнить в этот момент нечем.*
- **Г3. Невлитых веток не прибавилось.** `git --no-optional-locks branch --no-merged main` — число сравни с тем, что было на входе. Выросло — назови, чьи ветки и почему они законны.
- **Г4. Новый инструмент имеет живую точку вызова.** Завёл `.py` в `_generator/**` — `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/check_tool_contract.py <свои новые файлы>` → rc=0. Ни одного нового `.py` — так и напиши. *Инструмент без точки вызова зелен ровно потому, что его никто не звал.*
- **Г5. Новый `.md` зарегистрирован.** Завёл — звал ли ты `register_doc.py` и лежит ли строка на диске: `grep -c '<имя файла>' <карта своего корня>` → 1. Карту своего корня называет `korni.карта_для('<путь>')`, руками её не угадывай.
- **Г6. В коммите нет чужих путей.** `git --no-optional-locks show --stat` — только твои пути. Чужой путь в своём коммите — это чужая работа, унесённая твоим `commit` без `--`.

## 5. ОТЧЁТ → секция `## ОТЧЁТ` внизу
Что сделал + ЗАЧЕМ / как проверил / что НЕ трогал / вопросы / результат верификатора / открытое «возвращаться» / **время прогона + токены — НЕПРИМЕНИМО: движок `opencode`, счётчика стоимости в логе нет** (лог `.log` — обычный текст без `result`-строки, число снимать неоткуда; строку не заполнять числом и не извиняться за его отсутствие) / **ПОВТОРЯЕМОСТЬ находок (строка обязательна — см. ниже)** / **АРТЕФАКТ (строка обязательна)** / **КОММИТ (строка обязательна, см. §4)**.

🔴 **АРТЕФАКТ — АБСОЛЮТНЫЙ ПУТЬ К СОБРАННОМУ ФАЙЛУ, отдельной строкой.** Не «колода пересобрана», не «см. `dist/`», а путь, который владелец скопирует и откроет. *Цена 31.07: за сессию собрано три артефакта, ни один путь не был назван в отчёте — владелец не нашёл ни одного и сказал прямо: «я всё время не могу найти твои новые файлы». Хуже: он открыл СТАРУЮ колоду, потому что сборка молча не запустилась, и решил, что правка не сработала; ушёл целый круг на диагностику того, чего не было. Отчёт без адреса артефакта — это отчёт о работе, которую нельзя посмотреть.*

🔴 **НЕОБРАТИМОЕ — ОТДЕЛЬНЫМ СПИСКОМ, даже если оно стояло в задании.** Удаление, перезапись, переименование, перемещение, `git reset`/`checkout` поверх несохранённого, любая правка, вышедшая за зону, — каждое ОДНОЙ строкой: **что · где · чем восстанавливается** (хэш коммита, путь к бэкапу). Ты запущен без запроса разрешений (`--dangerously-skip-permissions`): владелец НЕ видел ни одного из этих действий в момент, когда оно происходило, и этот список — единственное место, где он о них узнаёт. **Необратимого не было — напиши «необратимого нет».** Молчание от пустоты не отличается, и приёмка прочитает его как пустоту.

🔴 **ПОВТОРЯЕМОСТЬ находок — назови, какие из них повторятся на СЛЕДУЮЩЕЙ единице работы** (лекция/слайд/заход). Критерий вычислимый, не про приоритет: повторится — это НЕ пункт очереди, а заход ДО следующего прогона (правило «класс НЕМЕДЛЕННОЕ», `../../docs/kak-delat/RUKOVODSTVO-zahodami.md`). Не повторится — законно уходит в `## ВОПРОСЫ` пунктом очереди. *Пример владельца: белый фон иллюстраций повторился бы тринадцать раз, каждый раз ценой переделки картинки — заход, а не запись; число, вписанное аналитиком не глядя, на следующих слайдах не повторяется — запись, а не заход.* Находка сделана ПРОБНЫМ прогоном — чинится ДО следующего прогона: «проба, после которой ничего не починили, — потраченные токены».

## ⚠️🔴 WARNING · ПОСЛЕДНИЙ ХОД ПЕРЕД ОТЧЁТОМ — ПОЛНАЯ ГИТ-ГИГИЕНА. НЕ ПРОПУСКАТЬ 🔴⚠️

**СТОП. Прежде чем писать хоть строку в `## ОТЧЁТ` — прогони это целиком.** Требование владельца
2026-08-16, поводом стал заход, который сделал работу и не закоммитил НИЧЕГО: *«он ничего не
коммитит… всегда, когда собираешь по генератору, там должна быть фраза, что начинать надо с полной
проверки гигиены»*. Гит-контур §0.1 стоит в НАЧАЛЕ и разбирает то, что накопилось ДО тебя; этот блок
стоит в КОНЦЕ и разбирает то, что накопил ты сам. Один другого не заменяет.

**ПОРЯДОК ЖЁСТКИЙ, ОН НАЗВАН ВЛАДЕЛЬЦЕМ: коммит → влитие своей ветки в основную → пост-проверка
ИЗ ГЛАВНОЙ ПАПКИ → гашение → вывоз.** Обратный порядок не работает технически: влитие отказывает
на грязном дереве, пост-проверка неисполнима до влития, вывоз — на невлитом. **Решение владельца
20.08 пересматривает решение 05.08** («в конце может это worktree вливать, но, наверное, это не
нужно делать») — теперь вливает САМ заход, но только при зелёной пост-проверке.

**1 · ВСЕ КОММИТЫ.** Ничего не осталось вне git — ни в рабочем репозитории, ни в соседних, до
которых ты дотянулся по ходу работы:
```
for R in /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot; do
  echo "== $R"; git -C $R --no-optional-locks status --porcelain
done
```
Своя зона — своими путями (`add` + `commit -- <пути>`). Чужая содержательная работа — НЕ твоя:
называешь строкой в отчёте и оставляешь. Пусто у всех — так и напиши числом «вне git 0».

**2 · ВЛИТИЕ СВОЕЙ ВЕТКИ В ОСНОВНУЮ.** Только после того, как шаг 1 дал «вне git 0» на своей
зоне — влитие отказывает на грязном дереве:
```
python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py vlit-v-osnovnuyu zahod/P10-ekspluatacia --zone "deploy/" --zone "ops/" --zone "tests/ops/" \
    --vsyo-ravno "своя рабочая папка ещё жива — влитие последним ходом захода, штатно"
```
Конфликт — ЗАКОННЫЙ исход, не повод форсировать: разрешай по существу, если понимаешь обе
стороны; не понимаешь — `git_zona.py vlit-v-osnovnuyu --abort`, ветка остаётся невлитой,
строка в отчёт и заявка на влитие (`git_zona.py zayavka --rod git-operaciya`).
🔴 Конфликт на `README.md` — только ОБЪЕДИНЕНИЕМ записей реестра, никогда выбором стороны:
параллельные заходы волны дописали по строке — обе записи правы, выбор одной молча уничтожает
регистрацию соседа.

**3 · ПОСТ-ПРОВЕРКА ИЗ ГЛАВНОЙ ПАПКИ.** Отвечает на вопрос «механизм ВСТАЛ», а не «коммит
виден»: прогон изменённого механизма из `/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot`, НЕ из рабочей папки `/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot-wt/P10-ekspluatacia` плюс `grep` по ЖИВОМУ файлу,
который его зовёт (хук, конвейер, генератор):
```
cd /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot && make check && python3 -m pytest tests/ops -q && echo $?
grep -n 'WatchdogSec' deploy/*.service   # сторожевой таймер объявлен
grep -rn 'systemctl enable' deploy/   # самая частая реальная поломка — забыть enable
```
🔴 **Красная пост-проверка = ОТКАТ ВЛИТИЯ И СТРОКА В ОТЧЁТ**, а не «доложу, пусть приёмка
решает»: `git_zona.py vlit-v-osnovnuyu --abort`, если слияние ещё не закоммичено, иначе
`git -C /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot --no-optional-locks reset --hard <хэш ДО влития>`. Заход, который влил
и сломал `main`, обязан вернуть `main` сам.

**4 · ГАШЕНИЕ.** Невлитого не осталось: `git --no-optional-locks branch --no-merged main`.
Каждая оставшаяся ветка названа поимённо с причиной, почему она жива. 🔴 Ветку-витрину (`main`
там, где с неё публикуется сайт) НЕ вливать — влитие туда есть публикация и решение владельца.

**5 · ВЫВОЗ.** Вывези СВОЮ ветку; `main` НЕ вывози: если после работы в нём есть невывезенное,
поставь заявку `--rod git-operaciya` и назови число в отчёте. Команда для своей ветки:
`git --no-optional-locks log --oneline @{u}.. | wc -l` → 0.
Ненулевое на своей ветке означает, что работа существует только на этом диске.

**6 · ПРОВЕРКА ФАКТОМ, А НЕ ПАМЯТЬЮ.** Числа по каждому репозиторию — вне git · невлитых своих
и чужих; невывезенных СВОЕЙ ВЕТКИ, не по каждому репозиторию · результат пост-проверки
(зелёная/откачена) — печатаются командой и уходят в `## ОТЧЁТ` дословно. Ненулевое число или
красная пост-проверка без объяснения — приёмка читает как несделанную работу: она гоняет те же
команды первым ходом.

🔴 **Отчёт без этих чисел не принимается.** «Я закоммитил» — не то же самое, что `status --porcelain`
пустой: за одну сессию работа не доезжала трижды, каждый раз с честным «сделано» в отчёте.
## УРОКИ ФАБРИКЕ — (заполняет исполнитель; пусто — нормальный исход)
> Находка не про эту сессию, а закономерность про саму фабрику, годная другим заходам, — оформи как пункт очереди в `## ВОПРОСЫ` (формат там же) с `ДОМ: <эта арка>/UROKI-FABRIKE.md`, а не пиши прямо сюда неструктурированной строкой.
> **Не про задачу — про САМУ ФАБРИКУ.** Ты работаешь с пустым контекстом и потому видишь то, чего не видит аналитик: он писал этот заход и ему приятно, что заход хорош. Сломался ВХОД (издание не то, id врёт, зона не содержит файла с ответом)? Критерий готовности кривой? Инструкция канона противоречит живому файлу? — сюда, строкой.
> Формат жёсткий (по нему гейт): `### <что произошло>` / `ЦЕНА: <что сломалось и сколько стоило>`.
> **ЦЕНА обязательна.** Без неё это наблюдение, а не урок, и в канон оно не пойдёт. Не знаешь цены — не пиши.
> **Не сочиняй.** Пустая секция — законный отчёт. Выдуманный урок хуже отсутствующего: он попадёт в канон, который читают ВСЕ будущие проекты.

## ПЛАН — (заполняет исполнитель)

**Baseline measured before any edit:** `make check` -> rc=0, `148 passed`. Unmerged
`zahod/*` branches at entry: `1` (`zahod/P9-listok`, checked out in a neighbour worktree).

### Premise I dispute BEFORE working (as §1 requires)

The КРИТЕРИЙ ГОТОВНОСТИ names `python3 tools/proverka_vosstanovlenia.py --na-porchennom`,
but `tools/` is NOT in my zone (`deploy/ ops/ tests/ops/`) and the ЗАПРЕТ is categorical:
"ничего за пределами зоны". Two rules of the same заход contradict each other. I resolve
it in favour of the zone contract, because the zone contract is the one whose violation is
irreversible for other people's work, and I say the corrected command here, before working:

    python3 ops/proverka_vosstanovlenia.py --na-porchennom     # instead of tools/...

Everything else in the criterion is unchanged and I run it verbatim.

### Order of parts (each committed separately)

1. **`ops/raspisanie.py`** — the one place that knows lesson days and hours. Everything
   else (deploy refusal, backup timers) reads it, so "when is a lesson" has a single
   answer. System clock is UTC, Moscow is obtained through `ZoneInfo(config.TZ_DISPLAY)`,
   never `timedelta(hours=3)` (§5 of the task).
2. **`ops/rezervnaya_kopia.py`** — `VACUUM INTO` + gzip + 14-day rotation, never `cp`.
3. **`ops/proverka_vosstanovlenia.py`** — the SEPARATE restore check: unpack the latest
   snapshot, `pragma integrity_check`, >= 50 students, latest mark not older than a week.
   All three must pass before a ping; silence is alarm. `--na-porchennom` is the mode that
   PROVES the check can go red.
4. **`ops/proverka_pragm.py`** — asserts WAL and `busy_timeout` are actually applied on a
   live connection, not merely written in `config.py` (§6 of the task).
5. **`ops/opoveshchenie.py`** — the alerter through a SECOND bot token; it has no code of
   its own to crash with, and it refuses to send the database anywhere.
6. **`deploy/*.service`, `*.timer`, `deploy/journald.conf`** — the unit with
   `Restart=always`, `RestartSec=5`, `StartLimitBurst=5` per 5 min, `WatchdogSec`,
   `OnFailure=`, `Environment=TZ=UTC`, plus the backup/restore-check timers.
7. **`deploy/ustanovka.sh`** — installs and, above all, runs `systemctl enable`; and
   **`ops/proverka_ustanovki.py`** — proves `enable` and `WatchdogSec` are there WITHOUT a
   VPS, by parsing the unit files (and, when systemd is present, by asking systemd).
8. **`deploy/vykatka.sh`** — `git pull` + `yoyo apply` + `systemctl restart`, graceful
   stop, pending updates never dropped, and the refusal to deploy on lesson days/hours.
   `--proba` is a dry run so the refusal is provable on this machine.
9. **`tests/ops/`** — at least 6 checks: 3 snapshot corruptions x 2 deploy-time scenarios,
   plus the pragma and unit-file assertions.
10. Verifier subagent (§3), then git hygiene, then merge my own branch last.

### What I do NOT touch

`bot/`, `core/`, `infra/`, `config.py`, `migrations/`, `tools/`, `tests/` outside
`tests/ops/`. The watchdog ping belongs inside the polling loop, i.e. inside `bot/`, which
is read-only to me: I write the unit and the check and name the exact one-line hook in
`## ВОПРОСЫ` for the next position, and I do NOT edit `bot/` to make my own check pass.


## ВОПРОСЫ — (заполняет исполнитель)
> Нашёл вещь, которая принадлежит чужому дому (термин/источник/урок/следующий заход) — не только вопрос владельцу? Оформи ПУНКТОМ ОЧЕРЕДИ, тремя строками:
> ```
> N. <текст находки>
>    ДОМ: <путь от корня репозитория | владелец>
>    ДОСТАВЛЕНО: нет
> ```
> `ДОМ: владелец` — когда дома-файла нет вовсе (сам вопрос владельцу); для урока фабрике дом почти всегда `<эта арка>/UROKI-FABRIKE.md`. Аналитик при переносе меняет `ДОСТАВЛЕНО: нет` на `ДОСТАВЛЕНО: <имя-захода>#<N>` И дописывает ЭТУ ЖЕ строку-метку в файл по адресу ДОМ — `priyomka.py` (Г7) красным ловит только случай «доставлено» без метки на месте, недоставленное просто печатает.
> 🔴 **Метку ставь ТОЛЬКО одним ходом вместе с самим переносом содержания, никогда раньше.** Гейт проверяет факт «строка-метка на месте», а не смысл «содержание перенесено верно» — метка без содержания рядом даст ложно-зелёный Г7.

## ГИГИЕНА ВХОДА — (заполняет СУБАГЕНТ гит-контура, не исполнитель)
> 🔴 **Каждый заход — ДВЕ независимые работы.** Первая — навести полную гигиену со всем, что
> накопилось к этому моменту. Вторая — собственно заход. Друг от друга они не зависят, но
> **первая обязательна ВСЕГДА**: без заполненной секции отчёт не принимается (гейт Г12 `priyomka.py`).
>
> 🔴 **ГАЛОЧКА — НЕ ИСТОЧНИК ИСТИНЫ.** Приёмка прогоняет те же команды заново и сравнивает
> с заявленным; расходится — красный НЕЗАВИСИМО от галочки. *Цена: исполнитель добросовестно
> написал «вливать не моя задача, это работа субагента, уже выполнена» при ВОСЬМИ невлитых ветках.*
>
> 🔴 **СНИМОК ВХОДА снимается ДО работы.** Без него «все долги закрыты» непроверяемо: неизвестно,
> какие были. Пустой снимок = красный.

**СНИМОК ВХОДА** *(команды и их ВЫВОД, а не пересказ; снять ПЕРВЫМ ходом, до всякой работы)*
```
git --no-optional-locks branch --no-merged <основная>     # невлитые
git --no-optional-locks status --porcelain | wc -l        # не закоммичено
git --no-optional-locks log --oneline @{u}.. | wc -l      # не вывезено
python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py zayavki              # открытые заявки
```
<сюда — вывод, дословно>

**ЧТО СДЕЛАНО** *(с хэшами)*
<влито / закоммичено / вывезено / погашено / заявки закрыты — поимённо>

**ВСЕ ДОЛГИ ВХОДА ЗАКРЫТЫ:** `<да | нет>`
*(`нет` законно — но ТОЛЬКО со списком поимённо: что осталось и почему это непроходимо ТВОИМИ
правами (чужая живая рабочая папка, нужно решение владельца, конфликт, обеих сторон которого
не понимаешь). «Сложно» и «не моя тема» причинами не являются. `нет` без списка = красный.)*

## ОТЧЁТ — (заполняет исполнитель)
**АРТЕФАКТ:** `<АБСОЛЮТНЫЙ путь к собранному файлу, который владелец должен открыть>` — `<чем открывать>`
*(собрал HTML, документ, PDF, картинки — путь сюда. Собранного файла нет — напиши «артефакта нет: <почему>». Пустая строка = отчёт не принимается: гейт `check_uroki.py` краснеет на коммите.)*
**РОД АРТЕФАКТА:** `<исходник | собранный>`
*(`собранный` — колода, PDF, картинка, любой файл, ПОРОЖДЁННЫЙ этим заходом: он обязан быть моложе файла-захода, и Г3 приёмки сверяет ВРЕМЯ. `исходник` — заход, чей продукт есть КОД: он коммитится РАНЬШЕ отчёта, потому что отчёт цитирует хэш коммита, и сверка по времени дала бы вечное ложное красное — тогда Г3 сверяет не время, а «доехал ли артефакт в названный §4 коммит». Не заполнено — Г3 работает по времени, как раньше.)*
**КОММИТ:** `<хэш>` — `<сообщение>` · `git_zona.py check --zone "deploy/" && \
    git_zona.py check --zone "ops/" && \
    git_zona.py check --zone "tests/ops/"` → ✅
*(нет хэша — назови причину прямо здесь; пустая строка = отчёт не принимается)*

## ПРАВКИ ПОСЛЕ ВЫДАЧИ — (заполняет АНАЛИТИК; исполнитель ЧИТАЕТ)
> 🔴 **Пусто — значит заход не правился с момента выдачи.** Непустой блок читается ПЕРЕД продолжением работы: правка отменяет любое противоречащее ей место выше по файлу, каким бы категоричным оно ни было.
> **Форма строки — жёсткая, по ней судит приёмка:** `### ПРАВКА N · ГГГГ-ММ-ДД ЧЧ:ММ · <что изменилось, одной фразой>`, дальше — что именно перечитать и что откатить, если уже сделано по старой редакции.
> **Аналитик:** внёс правку — обязан ОТДЕЛЬНО послать владельцу короткое сообщение для пересылки исполнителю. Правка, лежащая только в файле, до работающего исполнителя не доезжает: он файл не перечитывает сам.
> **Исполнитель:** прочитал правку — назови её номер в `## ОТЧЁТ` строкой `ПРАВКИ ПРОЧИТАНЫ: 1, 2`. Нет строки при непустом блоке = отчёт не принимается: неизвестно, по какой редакции работали.

<правок нет>

## ФАЗА ПРИЁМКИ — (заполняет АНАЛИТИК, не исполнитель)
> 🔴 **Без этого раздела заход НЕ ЗАКРЫТ.** Гейт — `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/priyomka.py <этот файл>` (Г13): пока раздел пуст или несёт плейсхолдеры, приёмка красная, и это единственное место, где вердикт остаётся ЗАПИСАННЫМ, а не сказанным в чат.
> Заполняется ПОСЛЕ отчёта исполнителя. Исполнителю сюда писать нечего — его половина выше.

**ВЕРДИКТ:** `<принято | доработка | отклонено>` — `<почему именно так, одной фразой: что проверено и чем>`

**ВЕТКА РАБОТЫ:** `zahod/P10-ekspluatacia`
*(проверяется фактом, не словом: ветка обязана существовать и быть либо ВЛИТА в основную, либо названа в открытой заявке на влитие. Ни того, ни другого — Г14 краснеет. Снять состояние: `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py poteri --branch <ветка>`)*

**ЗАЯВКИ, ПОСТАВЛЕННЫЕ ЭТОЙ ПРИЁМКОЙ — ПРОДУБЛИРУЙ СЮДА ТО, ЧТО УЖЕ ЛЕЖИТ В СПИСКЕ:**
> Адрес списка: `/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/zhurnal/_INFRA-git/zayavki`
> Читается командой (из любой папки, в том числе из worktree): `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py zayavki`
> Ставится командой: `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py zayavka --rod <git-operaciya|pravka-koda> "<текст>"`
> 🔴 Вопрос здесь НЕ «что ты хочешь сделать», а «что ты УЖЕ положил в очередь». Дубль сверяется с очередью по id машинно; намерение сверить не с чем.

- `<id заявки>` — `<род>` — `<суть одной строкой: влитие / коммит / вывоз / деплой / гашение>`

*(Заявок эта приёмка не ставила — так и напиши строкой «заявок нет: <почему ни одна из пяти операций не понадобилась>». Пустая строка и прочерк не принимаются: молчание неотличимо от «забыл».)*
