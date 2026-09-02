# Канал исполнителя — P2-import (один заход до конца)
> Твой единственный файл-заход. Читай ТОЛЬКО его и названные якоря; проект не изучай.
<!-- собран bootstrap_zahod.py -->
> План/вопросы/отчёт — в секции внизу. Метрика — КАЧЕСТВО. Часы — норма.
> **Модель: Opus 5** — здесь чинится ошибка, которую уже один раз пропустили: проверка импорта была тавтологией.

## СТАРТОВОЕ СООБЩЕНИЕ ВЛАДЕЛЬЦУ

> Это блок для владельца — то, чем тебя запустили. Исполнителю здесь делать нечего, твоё задание ниже.

```
bash /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/zhurnal/2026-09-02_spetsmat-bot/ZAPUSK-ZAHODA.sh P2-import opus
```
🔴 **ЧЕМ ЭТА СТРОКА ОТЛИЧАЕТСЯ ОТ ТОЙ, ЧТО ПЕЧАТАЛ ГЕНЕРАТОР.**
Генератор вписал `claude -p --model arn:aws:bedrock:…` — ARN application inference
profile. На ЭТОЙ машине Bedrock-доступа НЕТ вовсе: ни `~/.aws/`, ни переменных `AWS_*`
(замер 2026-09-02 08:22). Цена оплачена соседней волной 2026-09-02 07:07: пять платных
позиций из пяти оборвались за девять минут с «Could not load credentials from any
providers», и снаружи это неотличимо от «заход думает». `ZAPUSK-ZAHODA.sh` берёт модель
вторым аргументом и сам выбирает маршрут; добор — тем же вызовом с `--dobor`.

<!-- прежняя строка генератора, сохранена дословно, НЕ исполнять:

python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py worktree add P2-import --branch zahod/P2-import && cd /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot-wt/P2-import && claude -p --verbose --output-format stream-json --model arn:aws:bedrock:us-east-1:811345154057:application-inference-profile/d78ovu0ye0t4 --dangerously-skip-permissions 'Твой заход — файл /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/zhurnal/2026-09-02_spetsmat-bot/kod_P2-import.md. Прочитай ТОЛЬКО его и то, что он называет; остальной проект не изучай. План/вопросы/отчёт пиши в этот же файл внизу (## ПЛАН / ## ВОПРОСЫ / ## ОТЧЁТ). Ничего сверх задачи не трогай — «ничего сверх задачи» относится к СОДЕРЖАНИЮ работы; git-контур §0.1 — законное исключение, он про состояние репозитория и исполняется целиком.' < /dev/null 2>&1 | tee /tmp/zahod-P2-import.jsonl | python3 -u -c 'import sys,json
for l in sys.stdin:
 try:
  d=json.loads(l); t=d.get("type")
  if t=="assistant":
   for b in d.get("message",{}).get("content",[]):
    k=b.get("type")
    if k=="text" and (b.get("text") or "").strip(): print(b.get("text"))
    elif k=="tool_use": print("  . "+str(b.get("name")))
  elif t=="result":
   u=d.get("usage") or {}
   print("== ПРОГОН: %s c . USD %s . токены вх %s / вых %s / кэш-чтение %s" % ((d.get("duration_ms") or 0)//1000, d.get("total_cost_usd"), u.get("input_tokens"), u.get("output_tokens"), u.get("cache_read_input_tokens")))
 except Exception:
  sys.stdout.write(l)'

-->

Приёмке — время и токены печатает команда, руками их не вписывают (`KONSTITUCIYA §10`; лог остаётся на диске после прогона):
```
python3 -c 'import sys,json
for l in open(sys.argv[1], encoding="utf-8"):
 try:
  d=json.loads(l)
 except Exception:
  continue
 if d.get("type")=="result":
  u=d.get("usage") or {}
  print("время: %s c" % ((d.get("duration_ms") or 0)//1000))
  print("стоимость USD: %s" % d.get("total_cost_usd"))
  print("токены: вход %s, выход %s, кэш-чтение %s" % (u.get("input_tokens"), u.get("output_tokens"), u.get("cache_read_input_tokens")))
  for m,v in (d.get("modelUsage") or {}).items():
   print("  %s: вх %s вых %s USD %s" % (m, v.get("inputTokens"), v.get("outputTokens"), v.get("costUSD")))' /tmp/zahod-P2-import.jsonl
```

── СЧЁТ НЕЗАКРЫТОГО (печать, не гейт) ──
ГРАНИЦА ОБЛАСТИ: сырые подстроки в `kod_*.md` (пункт 4) — НЕ парсер очереди `dostavit_urok` (который считает только пары ДОМ:/ДОСТАВЛЕНО:). Разница в числах — законна.
🔴 снимок при сборке 2026-09-02, ПРОВЕРЬ ПЕРВЫМ ХОДОМ: `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/schet_nezakrytogo.py zhurnal/2026-09-02_spetsmat-bot`
Область: «zhurnal/2026-09-02_spetsmat-bot» — сужены пункты 1, 3, 4; долги (2) глобальны намеренно (DOLG.md не размечен по записям).
Приоритет владельца: разобрать инциденты важнее, потом закрыть долги — неразобранный инцидент это повторяющаяся ошибка, долг может подождать.
  1. инцидентов без вердикта             : н/д — VERDIKTY.md/INCIDENTY.md не найдены
  2. долгов СТАТУС: ЖИВ                  : н/д — /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/skills/slajdy/DOLG.md недоступен (другой git-репозиторий)
  3. уроков фабрике без ВЕРДИКТ          : 4
  4. пунктов очереди «ДОСТАВЛЕНО: нет»   : 3
     из них разбором очереди (парсер `dostavit_urok`, записи с парой ДОМ:/ДОСТАВЛЕНО:): 0
       живых (чинится доставкой — «дом есть»)  : 0
       к владельцу (решение за человеком)      : 0
       адрес недоступен (нет/папка/код/указат.) : 0
       адрес не разобран                        : 0
       отработавших (машинный след закрытия)    : 0
       доставлено                               : 0
       🔴 не проверяется машиной: содержательная отработанность записей БЕЗ следа закрытия (метки в доме, строки ✅/ЗАКРЫТО) — нужна ревизия человеком; сырой греп сверх разбора — шаблонные строки формы.

КОНТЕКСТ. `spetsmat-bot` — телеграм-бот кондуита спецмата 179-й школы: 56 учеников,
18 преподавателей, три аудитории. Прошлый этап: позиция P1 ПРИНЯТА и влита в `main` —
есть схема (`migrations/001_init.sql`), журнал отметок с `assert`/`retract`/`erratum`,
двумя временами и SCD2-закреплениями, `core/` без единой строки aiogram, 66 тестов,
`make check` зелёный. Базы с данными нет: она пустая. ЦЕЛЬ: загрузить в неё
прошлогодний кондуит — 56 учеников, 18 преподавателей, 18 листков, 544 задачи,
15 112 отметок — так, чтобы долги и гробарий ВОСПРОИЗВЕЛИСЬ, и доказать это тремя
оракулами, независимыми от проверяемых ячеек, плюс негативным контролем.
Приёмка — по ОТЧЁТУ, без построчной сверки. Если стоп до цели: получишь загруженный
засев и инвентарь значений, но НЕ проверку оракулами — а именно она и есть эта позиция.

## ЧТО ФИНАЛИЗИРОВАНО НА ИНТЕРВЬЮ

ИНТЕРВЬЮ ПРОВЕДЕНО: да (2026-09-02) — флаг `--intervyu da` при сборке. ⚠ Он доказывает, что аналитик не ЗАБЫЛ про интервью, и НЕ доказывает, что разговор был.

1. оракул засчитывается, только если произведён независимо от проверяемых ячеек
2. импорт начинается с инвентаря всех различных значений и ПАДАЕТ на незнакомом
3. пришедшим позже старые листки не вменяются — поле «первый листок»

## КОНТРАКТ ЗОНЫ (обязателен — не удалять; вписан Cowork)
- **МЕСТО РАБОТЫ:** **рабочая папка `/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot-wt/P2-import`** — ТОЛЬКО ДЛЯ КОДА (worktree захода, ветка `zahod/P2-import` в ней уже стоит). 🔴 **ДАЛЬШЕ — ТОЛЬКО ПУТИ ОТНОСИТЕЛЬНО ЭТОЙ ПАПКИ** (или `cd` в неё безусловно, каждым ходом): абсолютный путь в главную папку репозитория здесь — типичная ошибка, правка утекает МИМО worktree и найдётся только на коммите («вне git» в `git_zona.py check --zone` из рабочей папки, на файле, который уже правил, — цена, оплаченная живьём: 5 файлов, ручное копирование и откат главной папки). 🔴 `git checkout` в основной папке ЗАПРЕЩЁН: рядом идут другие заходы, переключение подменит файлы у них под ногами. 🔴 **Сам файл-заход (этот `.md`) при этом остаётся в ОСНОВНОЙ папке репозитория** — один экземпляр, не копия в рабочей папке: ПЛАН/ВОПРОСЫ/ОТЧЁТ/УРОКИ пишешь в него по абсолютному пути, названному в стартовой строке, а сам файл НЕ коммитишь — это делает аналитик при приёмке (цена обратного правила — полсуток 03.08: отчёт писали в рабочую папку, владелец и приёмка её не видели, приёмка трижды объявила отчёт пустым). 🔴 **Ветку в конце вливаешь САМ, последним ходом, после коммита зоны** (решение владельца 25.08; полный порядок печатает WARNING-блок ниже).
- **ЗОНА (можно менять):** `tools/import_konduit.py` `core/services/seeding.py` `tests/import/`. Всё вне — **READ-ONLY**: не править, не двигать, не удалять, не рефакторить «заодно».
- 🔴 **ЗАВЁЛ НОВЫЙ `.md` — РЕГИСТРИРУЕШЬ ЕГО САМ, ТЕМ ЖЕ ХОДОМ, ОДНОЙ КОМАНДОЙ:** `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/register_doc.py <путь> "<описание>"` (из корня репо). `_studio/docs/` тебе по-прежнему READ-ONLY **для правки руками** — дверь ровно одна, и это она. Дверь идемпотентна (повторный вызов дубля не заведёт) и отказывает на пути вне `_studio/`, на несуществующем файле и на пустом описании. Свой файл-заход регистрировать не нужно: он рождается зарегистрированным из `bootstrap_zahod.py`. **Красный хук на ТВОЁМ новом `.md` — это не повод для `--no-verify`, а повод позвать дверь.** *Почему правило существует и почему оно теперь исполнимо: 26.07 оно записано с ценой в пять документов-сирот и через два дня повторилось дословно. Дальше стало хуже: до 30.07 указания «зарегистрируй» и «`docs/` только на чтение» противоречили друг другу, выход был ровно один — обойти хук, и по автологу `_INFRA-git/INCIDENTY.md` это 28 обходов `--no-verify` из 56 срывов коммита, 27 из них по одной этой причине (48 % всей боли с коммитами, тринадцать исполнителей подряд). Обходить больше нечего.*
- **КОММИТ:** два хода — `add` по своим путям, затем `commit` **с теми же путями после `--`** (полная форма и цена каждого хода — §4); коммить ПО ХОДУ работы, не одним последним ходом (§4). НИКОГДА `-A` / `.` / `commit -am`, и никогда `commit` без путей. Субагенты не коммитят. **`--no-optional-locks` обязателен:** обычный git переписывает индекс, берёт `.git/index.lock` и роняет параллельный ручной коммит владельца.
- **SCRATCHPAD — ТОЛЬКО ЛИЧНЫЙ.** Черновики, выкладки, промежуточные версии — в личную папку СВОЕГО захода `scratchpad/P2-import/`. Общие пути (`scratchpad/otchet.md`, любой `scratchpad/*` без имени твоей темы) ЗАПРЕЩЕНЫ: чужой отчёт уедет в твой файл или твой — в чужой, а приёмка читает отчёт без построчной сверки и подмену НЕ ЛОВИТ по построению. *Цена 25.08: готовый `## ОТЧЁТ` захода konvejer-incidentov был записан в общий `scratchpad/otchet.md`, и 92 строки чужого отчёта простояли в `kod_slovari-v-kod.md`.*
- 🔴 **Звал `register_doc.py` — допиши `_studio/docs/KARTA.md` к своим путям В ОБОИХ ходах.** Строка регистрации лежит физически в нём. Ворота 5 читают `§6` **с диска**, а не из индекса: коммит без этого файла пройдёт ЗЕЛЁНЫМ, документ уедет сиротой, а строка умрёт при первом `checkout` (дата данных 2026-07-30, найдено верификацией захода «kod_registracia-bez-obhoda.md»).
- **ЗАПРЕТ:** ничего за пределами зоны, даже если «мешает» или «чинится в одну строку». Нашёл проблему вне зоны → в отчёт, не трогай.

## 0. ПЕРВЫЙ ХОД
### 0.1 🔴 ГИТ-КОНТУР — ДО ВСЕГО ОСТАЛЬНОГО, И ПЕРВЫМ ХОДОМ ЦЕЛИКОМ

🔴 «ничего сверх задачи» относится к СОДЕРЖАНИЮ работы; git-контур §0.1 — законное исключение, он про состояние репозитория и исполняется целиком.

🔴 **ПОРЯДОК ЗДЕСЬ — ЧАСТЬ УСТРОЙСТВА, А НЕ ОФОРМЛЕНИЕ. Сначала субагент вливает названные через `--vlit` ЧУЖИЕ ветки В ОСНОВНУЮ, и только ПОТОМ ты заводишь свою рабочую папку; СВОЮ ветку он не трогает никогда — её вливаешь ты сам последним ходом (граница прав ниже).** Пока влитие шло в ветку захода, а влитие в основную было ходом приёмки (которая из песочницы в `.git` писать не может), работа копилась лестницей в последней ветке цепочки, а основная не получала ничего — замер 14.08: 14 невлитых веток, цепочка из пяти внутри последней, 84 невывезенных коммита, и генератор в основной папке не знал о собственных улучшениях. Заводя ветку ПОСЛЕ влития, ты отпочковываешь её от основной, которая уже всё содержит: инструмент оказывается на диске сам, дотаскивать нечего.

**1. ВЕСЬ КОНТУР — В СУБАГЕНТА, ОДНИМ ХОДОМ, ДО СВОЕЙ ПАПКИ.** Очередь заявок, влитие названных веток в ОСНОВНУЮ, что забрать в git по ходу и что погасить после — на содержание твоей задачи не влияют. Запусти ОДНОГО субагента, дождись его и вставь его шесть строк в `## ОТЧЁТ` дословно; сам эти пункты не исполняй. 🔴 ПОРЯДОК ПРИ ПАДЕНИИ ЭТОГО ВЫЗОВА — исполняй, не изобретай (движок роняет `network_error` на вызове субагента и уносит с собой ВЕСЬ заход, замер волны 3A — 4 захода из 13). Пауза 45 секунд, до трёх попыток; время меряй `date`, не суммой своих `sleep`. После третьей — работай БЕЗ субагента: контур остаётся неразобранным, и это ОТДЕЛЬНАЯ строка в `## ОТЧЁТ`, а не молчание. У него ОТДЕЛЬНЫЕ ПРАВА, объявленные в его же промпте: главная папка, основная ветка, вывоз — и ничего сверх; зону захода он не коммитит, её коммитишь ты сам, по ходу работы (§4). 🔴 ОТВЕТ ЛЮБОГО субагента, которого ты запускаешь (не только этого), обязан КОНЧАТЬСЯ строкой «выдано N позиций из M найденных»: канал мог оборвать его молча, и без этой строки усечение неотличимо от честного «мало нашлось». Нет строки — ответ усечён, в `## ОТЧЁТ` не вставляй, перезапроси. Полный текст задания печатает команда:
```
python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/bootstrap_zahod.py --zadanie-subagentu --zone tools/import_konduit.py --zone core/services/seeding.py --zone tests/import/ --kommitit 'tools/import_konduit.py, core/services/seeding.py, tests/import/' --zakryt 'влить ветку zahod/P2-import в main последним ходом, после коммита зоны'
```

🔴 ГРАНИЦА ПРАВ, ЧЕТЫРЕ ОТВЕТА (та же, что в самом задании субагенту — одно место в тексте, а не пересказ): **кто вливает ЧУЖИЕ названные (`--vlit`) ветки** — субагент, в ОСНОВНУЮ ветку, до заведения твоей папки; **кто вливает СВОЮ ветку этого захода** — ты сам, последним ходом, после коммита зоны (`git_zona.py vlit-v-osnovnuyu`; решение владельца 25.08 — оно сняло противоречие волны 4, когда машинное §0.1 и текстовое «ветку НЕ вливать» спорили молча, и машинное побеждало); **кто закрывает заявки** — субагент, `zayavka-zakryt`; **кто коммитит пути ВНЕ зоны захода** — субагент (хвост Cowork и что назовёт пункт 3 его задания). Ты коммитишь ТОЛЬКО зону этого захода, по ходу работы (§4). 🔴 Конфликт на `README.md` при ЛЮБОМ слиянии разрешается ОБЪЕДИНЕНИЕМ записей реестра, НИКОГДА выбором стороны: параллельные заходы волны дописали в реестр по строке — обе записи правы, выбор одной молча уничтожает регистрацию соседа.

**2. ТЕПЕРЬ ЗАВОДИ СВОЮ РАБОЧУЮ ПАПКУ** (команда — в блоке «МЕСТО РАБОТЫ» выше) и работай в ней как обычно. Её ветка отпочкована от свежей основной, поэтому инструмент, которым ты работаешь, уже на диске — отдельного «влить перед работой» больше нет.

Невлитых `zahod/*`-веток, НЕ покрытых `--vlit`, — 1: `zahod/P1-yadro` — 🔴 снимок при сборке 2026-09-02, ПРОВЕРЬ ПЕРВЫМ ХОДОМ: `git --no-optional-locks branch --no-merged main | grep -c 'zahod/'`. 🔴 КЛАПАН ОТКРЫТ АНАЛИТИКОМ, причина дословно: «волна идёт: zahod/P1-yadro прямо сейчас работает в своей рабочей папке (окно живо, ppid=1). Вливать чужой незакрытый заход нельзя — он вольёт незаконченную работу и подменит файлы под ногами исполнителя. Вливает КАЖДЫЙ заход СВОЮ ветку сам, последним ходом, как велит мандат в разделе RESPONSIBILITIES». Заход собран ВОПРЕКИ невлитому этой веткой — отключение видно здесь, в артефакте, а не осталось решением в голове аналитика (§79 канона: невлитая ветка законна, рядом может идти чужой заход).


- деплоя в этом заходе нет.

- `cd /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot-wt/P2-import` — рабочая папка ДЛЯ КОДА. Ветку НЕ переключай: `zahod/P2-import` в ней уже стоит.
- Проверить, что на месте: `git rev-parse --abbrev-ref HEAD` → должно быть `zahod/P2-import`.
- ПЛАН/ВОПРОСЫ/ОТЧЁТ/УРОКИ ФАБРИКЕ пиши в ЭТОТ файл — он в основной папке, не копируй его в рабочую.
- Точка отката: `git add tools/import_konduit.py core/services/seeding.py tests/import/` → commit (или zip), если зона не чиста в HEAD (не фабрикуй, если чиста).
- Прочитать ТОЛЬКО: `названные файлы-якоря`. Проект не изучай.
- ПЛАН — в `## ПЛАН` перед действиями.

## 1. ДИСЦИПЛИНА (Карпатов)
🔴 **Код возврата — ПЕРВЫМ, до содержательного вывода команды.** «Отработала» и «упала, а я читаю прошлое состояние» выглядят одинаково; сначала `echo $?`, потом выводы. То же с гейтами. *Цена 21.07: `rc=128` (сбой прав окружения) четырежды прочитан как результат — едва не откатили верное правило по ложным данным.*
Предпосылки/развилки назвать вслух; минимум без спекуляций; хирургия (строка → к заданию); критерий, который может провалиться. Якорные замены — abort при ≠1. Сохранять по умолчанию. **Оспорить ложную предпосылку — включая КРИТЕРИЙ ГОТОВНОСТИ: считаешь его кривым — скажи в `## ПЛАН`, ДО работы, и предложи поправку.** Субагенты: ≤5, рейт-лимит = отступить + доложить (не слепой ретрай).

🔴 **Пишешь содержательный текст — термин НЕ употребляется раньше, чем определён**, включая заголовки, подводки и формулировки теорем. «Определение в тексте есть» не считается: если оно ниже первого рабочего употребления, читатель встаёт ровно там. Чинится ПЕРЕСТАНОВКОЙ определения вверх, не дописыванием пояснения. Гейт: `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/check_termin.py <src>` (exit 1 при нарушении). Канон — `../docs/kak-delat/STANDART-teksta.md` правило 11. *Цена 30.07: теорема пользовалась словом «ординал», определение стояло строкой ниже; поймал владелец, ни один гейт не увидел, раздел переписан дважды.*

## 2. ЗАДАЧА

🔴 **WRITE YOUR `## ОТЧЁТ`, `## ПЛАН` AND `## ВОПРОСЫ` IN ENGLISH, AND EVERY FILE AND EVERY COMMIT MESSAGE YOU PRODUCE TOO.** Owner's decision 30.08. It is a каркас-level rule, not a preference — wave 2 lost it twice because the pass text listed the report SECTIONS and never said «every file you create». Fixed Russian addresses stay Cyrillic: `ЦЕНА:` · `ВЕРДИКТ:` · `ДОМ:` · `ДОСТАВЛЕНО:` · `ПОДЪЁМ:` · `[ДОЛГ: …]` · every `## ` heading of this file · every path and command.
🔴 **THIS POSITION EXISTS TO FIX AN ERROR THAT WAS ALREADY MADE ONCE AND MISSED.**
The previous `import_konduit.py` compared the number of solvers computed from the journal
against row 2 of the Excel sheet. But row 2 is a `SUM` over the very cells the script read.
The match "to the unit across all 544 problems" proved that `openpyxl` can read a file, and
nothing beyond it. Worse: `main()` returned `None`, so the exit code was always zero — the
test could not fail physically. Do not reproduce this shape in any form.

### 1 · Inventory FIRST, and FAIL on the unknown

The old script's `value()` returned `None` for everything except `1.0` and `"x"`, and silently
threw away real data. A second agent found what it was discarding:

- the mark `✘` on **88 problems** — undocumented; in sheet 4д it marks all 26 problems;
- the value `2` in sheet 9 (Фёдоров, problem −4б) and a backtick in sheet 15 (Искеева, 1°д);
- **sheet 15 has a THIRD column layout** — surname, name, closed, empty, receiver;
- **sheets 1д and 2д have no header row at all** — 50 problems with no type.

So: the importer BEGINS by collecting the set of every distinct cell value in the source and
**raises on an unknown one**. No silent `None`, ever. The inventory is printed with counts and
goes into the report, so the next reader sees what the data actually contains.

### 2 · What to load

`seed/students.csv` (56 students: 55 live + 1 technical; 9К — 28, 9Л — 27),
`seed/teachers.csv` (18 teachers, 17 live), `seed/sheets.json` (18 sheets, 544 problems:
215 obligatory, 288 plain, 39 starred, 2 double-starred). The marks `°` (102) and `●` (113)
give exactly 215 obligatory — the two signs are self-consistent, either may be trusted.

**`source` = `импорт` on every imported mark**, and the enum values of the base schema stay
Cyrillic — they are data fixed by `seed/sheets.json`, and renaming them breaks the seed.

### 3 · `first_sheet_id` — DECIDED, do not re-open, and it is the reason P1 asked

Exactly two students moved during the year, both 9К: **Гамаюнова Софья** left after sheet 6,
**Пирогов Константин** arrived from sheet 6. This is the whole reason the field exists:
those who arrive later are not charged the old sheets.

🔴 **The orchestrator's decision, taken because P1 raised it and P2 is what fills the field:**
- on IMPORT, `first_sheet_id` is set EXPLICITLY for every student — the earliest sheet in
  which that student has any row. `NULL` must not survive this import: assert it at the end,
  `select count(*) from students where first_sheet_id is null` → 0, and print the number.
- P1 left the fallback "NULL means owes from the very first sheet", pinned by
  `tests/test_verifier_findings.py::test_a_student_with_no_first_sheet_owes_from_the_very_first_sheet`.
  That fallback is right for imported rows and WRONG for a freshly registered student, who
  would open the bot to a wall of debts on day one. **Do not change P1's fallback** — it is
  out of your zone and it is pinned by a test. Just make `NULL` impossible on import, and say
  so in the report. Registration's default is P3's business.

### 4 · Three oracles, and NOT the spreadsheet's own SUM row

An oracle counts only if it is produced INDEPENDENTLY of the cells being checked:

1. **the examination sheet** (`итоговая ведомость`) by which the year's credit was awarded;
2. **thirty cells checked by hand** — pick them spread across sheets and students, write each
   one out in the report as `sheet · student · problem · expected · got`, so a human can
   re-check any of them without re-running anything;
3. **the debts sheet** (`лист «долги»`), honouring `first_sheet_id`. Last time the debts
   diverged on exactly one student, and that divergence is what revealed the Пирогов rule —
   so a divergence here is a FINDING, not noise: name the student and the reason.

### 5 · 🔴 NEGATIVE CONTROL — the part that makes the oracles mean anything

Corrupt the data three ways and the test MUST go red on each. Green on a corruption is a
failure of the position:

- delete one event from the journal;
- flip one mark (`assert` → `retract`);
- swap two students.

Five lines of code that would have killed the previous tautology in a minute.

### 6 · Two holes in the data — close them, do not paper over them

- **The senior of room 203, initials НС, is not registered as a teacher anywhere** — neither in
  the list nor on the «принимающие» sheet, and five students are attributed to him. Register him.
- **Composite receivers**: «Саша Оревкова/Ольга Александровна», «Наталия Павлована/Ольга
  Александровна». The conduit holds 19 distinct receiver strings against 17 live teachers, and
  the model "one author per mark" cannot express this. Decide and write down HOW you express it
  — a second author on the mark, or a separate record — and say why in the report. This is a
  modelling decision inside your zone; make it, do not ask.

**КРИТЕРИЙ ГОТОВНОСТИ (может ПРОВАЛИТЬСЯ), каждая команда печатает ЧИСЛО:**

    cd /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot-wt/P2-import
    make check                                   # rc=0, все тесты зелёные, число печатается
    python3 tools/import_konduit.py --proverit   # rc=0; печатает по каждому из ТРЁХ оракулов
                                                 # «сверено N из M, расхождений K»; 544 задачи,
                                                 # 30 ручных клеток, долги по листу «долги»
    python3 tools/import_konduit.py --negativnyj-kontrol
                                                 # rc=0 И печатает «порч 3 из 3, покраснело 3»
                                                 # ЗЕЛЁНОЕ НА ПОРЧЕ = ПРОВАЛ ПОЗИЦИИ

🔴 Ноль сверенных при непустом источнике — КРАСНЫЙ, а не зелёный. Отрицательный вердикт обязан
нести охват В СЕБЕ: «расхождений 0, сверено 544 из 544», а не «расхождений не найдено».

### 7 · ГДЕ ИСХОДНИК — найдено и измерено оркестратором, не ищи заново

🔴 **Путь в самом `tools/import_konduit.py` МЁРТВЫЙ.** Строка 13:
`SRC = "/sessions/funny-eager-bell/mnt/uploads/Кондуит 8КЛ.xlsx"` — это путь песочницы Cowork,
на этой машине такого каталога нет вовсе. Это первое, что чинится.

**Живой источник:** `/Users/ivanyakovlev/Downloads/Кондуит 8КЛ.xlsx` — 33 листа,
`['1','2','3','4','6','7','8','9','10','11','12','13','14','15','1д','2д','3д','4д','1 кр',
'1,5 кр (геогр)','2 кр','6 кр', …]`. Рядом лежит `Кондуит 8КЛ-2.xlsx`, новее на сутки и с
другим md5 — **это НЕ вторая версия данных**: оркестратор сверил обе книги поклеточно,
`906333 клеток сверено, различий 0`. Бери любую, ambiguity закрыта замером. Есть ещё
`Распределение.xlsx` — он про раскладку по аудиториям, в эту позицию не входит.

🔴 **Исходник в репозиторий НЕ КОПИРУЕТСЯ и НЕ КОММИТИТСЯ.** Это персональные данные
пятидесяти шести детей; в git едет только обезличенный производный засев, который уже там.
Путь к книге кладётся КОНСТАНТОЙ в `config.py` (все константы живут там — правило волны),
с значением по умолчанию `~/Downloads/Кондуит 8КЛ.xlsx` и внятным отказом, если файла нет.

⚠ `seed/students.csv` УЖЕ несёт колонку `first_sheet` — не вычисляй её заново, сверь с тем,
что даёт книга, и расхождение назови находкой.
**Отрицательный вердикт несёт ОХВАТ В СЕБЕ:** не «дыр не найдено», а «дыр не найдено, проверено X из Y». Без охвата вердикт не принимается — «проверено 2 из 9» и «проверено 9 из 9» выглядят одинаково.

## 3. ВЕРИФИКАТОР (если двигаем/теряем/жмём)

Верификатор нужен, тип — **ПОСЛЕ-типа** — судит результат, стоит в конце, после задачи. Свежий субагент, ДРУГИМ методом (негативный контроль: три порчи данных (удалить событие, перевернуть отметку, поменять местами двух учеников) — тест обязан покраснеть на каждой), не перечитывает свою же правку. Доля сплошной выборки: все 544 задачи и все 3 порчи, расхождений 0. Финальная строка ответа обязательна дословно: «выдано N позиций из M найденных» — без неё ответ считается усечённым и в отчёт не вставляется.

## 4. 🔴 КОММИТ СВОЕЙ ЗОНЫ — ПО ХОДУ РАБОТЫ, НЕ ОДНИМ ПОСЛЕДНИМ ХОДОМ
Ты работаешь host-side и в `.git` ПИШЕШЬ — значит коммитишь САМ, никому не передавая. Каждую завершённую часть работы коммить СРАЗУ, теми же двумя ходами — не копи всё к финальному ходу:
```
git --no-optional-locks add -- tools/import_konduit.py core/services/seeding.py tests/import/                     # вводит НОВЫЕ пути в индекс
git --no-optional-locks commit -m "<что сделано>" -- tools/import_konduit.py core/services/seeding.py tests/import/   # отсекает всё чужое
python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone "tools/import_konduit.py" && \
    git_zona.py check --zone "core/services/seeding.py" && \
    git_zona.py check --zone "tests/import/"   # из корня репо; должен быть ✅
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

**ЗОНА ГИГИЕНЫ:** `tools/import_konduit.py` `core/services/seeding.py` `tests/import/`

- **Г1. Зона доехала в git.** `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone tools/import_konduit.py` → ✅; `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone core/services/seeding.py` → ✅; `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone tests/import/` → ✅. Красное на любой из команд — отчёт не принимается: приёмка гоняет их все первым ходом.
- **Г2. Второй репозиторий.** **неприменимо, и это проверено при сборке, а не предположено:** все пути зоны лежат внутри репозитория `spetsmat-bot` (тот же критерий, что у С2 `check_sborki.py`). Зона расширилась за его пределы по ходу — пункт снова применим; команда та же, что в применимом случае: `cd ../<репозиторий> && git --no-optional-locks status --porcelain` → пусто. *Команда названа и здесь нарочно (находка верификатора): пункт, который объявлен неприменимым и не говорит, ЧТО делать, когда станет применим, исполнить в этот момент нечем.*
- **Г3. Невлитых веток не прибавилось.** `git --no-optional-locks branch --no-merged main` — число сравни с тем, что было на входе. Выросло — назови, чьи ветки и почему они законны.
- **Г4. Новый инструмент имеет живую точку вызова.** Завёл `.py` в `_generator/**` — `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/check_tool_contract.py <свои новые файлы>` → rc=0. Ни одного нового `.py` — так и напиши. *Инструмент без точки вызова зелен ровно потому, что его никто не звал.*
- **Г5. Новый `.md` зарегистрирован.** Завёл — звал ли ты `register_doc.py` и лежит ли строка на диске: `grep -c '<имя файла>' <карта своего корня>` → 1. Карту своего корня называет `korni.карта_для('<путь>')`, руками её не угадывай.
- **Г6. В коммите нет чужих путей.** `git --no-optional-locks show --stat` — только твои пути. Чужой путь в своём коммите — это чужая работа, унесённая твоим `commit` без `--`.

## 5. ОТЧЁТ → секция `## ОТЧЁТ` внизу
Что сделал + ЗАЧЕМ / как проверил / что НЕ трогал / вопросы / результат верификатора / открытое «возвращаться» / **время прогона + токены — их снимает ПРИЁМКА из лога прогона** (исполнителю счётчик недоступен: он снаружи его сессии, и `/cost` не существует — команда называется `/usage`. Извиняться за это не нужно и оценку писать не нужно: число печатает сама стартовая команда в `result`-строку лога) / **ПОВТОРЯЕМОСТЬ находок (строка обязательна — см. ниже)** / **АРТЕФАКТ (строка обязательна)** / **КОММИТ (строка обязательна, см. §4)**.

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
python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py vlit-v-osnovnuyu zahod/P2-import --zone "tools/import_konduit.py" --zone "core/services/seeding.py" --zone "tests/import/" \
    --vsyo-ravno "своя рабочая папка ещё жива — влитие последним ходом захода, штатно"
```
Конфликт — ЗАКОННЫЙ исход, не повод форсировать: разрешай по существу, если понимаешь обе
стороны; не понимаешь — `git_zona.py vlit-v-osnovnuyu --abort`, ветка остаётся невлитой,
строка в отчёт и заявка на влитие (`git_zona.py zayavka --rod git-operaciya`).
🔴 Конфликт на `README.md` — только ОБЪЕДИНЕНИЕМ записей реестра, никогда выбором стороны:
параллельные заходы волны дописали по строке — обе записи правы, выбор одной молча уничтожает
регистрацию соседа.

**3 · ПОСТ-ПРОВЕРКА ИЗ ГЛАВНОЙ ПАПКИ.** Отвечает на вопрос «механизм ВСТАЛ», а не «коммит
виден»: прогон изменённого механизма из `/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot`, НЕ из рабочей папки `/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot-wt/P2-import` плюс `grep` по ЖИВОМУ файлу,
который его зовёт (хук, конвейер, генератор):
```
cd /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot && make check && python3 tools/import_konduit.py --proverit && echo $?
grep -n 'KONDUIT_XLSX\|--proverit\|--negativnyj-kontrol' config.py tools/import_konduit.py
grep -c 'first_sheet' tools/import_konduit.py   # правило Пирогова живёт в коде, а не в отчёте
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

### The заход written to kill a tautology named a tautology as its own oracle
§4 forbids the sheet's `SUM` row because it is computed from the cells being checked, and
then names the `долги` sheet as oracle 3. Read with `data_only=False`, every per-sheet
column of `долги` is `=INDEX(INDIRECT(<лист>&"!A:A"), MATCH(...))` — a VLOOKUP of that
sheet's `закрыт` column, which is itself `=SUMPRODUCT(...)` over the very mark cells. It is
the SUM row with two extra hops.
ЦЕНА: followed literally, this position ships a long-form SUM row and reproduces the exact
error it exists to fix — while reporting «три оракула, расхождений 0» and passing acceptance.
The measurement that catches it (open the source a second time with formulas visible and
classify each oracle by provenance BEFORE trusting it) took ten minutes and appears in no
checklist. It generalises: **a заход that names an oracle living inside the same artefact as
the data must require that oracle's provenance to be measured, not asserted.**

### A заход's branch can be cut before its dependency merges, and §0.1 cannot see it
`zahod/P2-import` was cut from `main` before P1 was accepted. By the time this заход ran,
`main` was 9 commits ahead and my worktree held no `core/`, no `config.py`, no `migrations/`,
no `Makefile`, no `tests/` — my own zone path `core/services/seeding.py` was in P1's tree,
not mine. §0.1's design («твоя ветка отпочкована от свежей основной, поэтому инструмент уже
на диске») assumes the branch is created AFTER the merge; a wave launching заходы in
parallel breaks that silently.
ЦЕНА: without checking `git log zahod/P2-import..main` first, I would have written
`core/services/seeding.py` into an empty tree against a schema that was not there and
duplicated P1's core — a whole position thrown away plus a conflict in every file. Detection
cost five minutes. **A заход whose zone names a file an earlier заход produces should be
required to verify that file is on disk before the first line of work, and to merge `main`
into its own branch if it is not.**

### The three named corruptions all passed; every defect the verifier found came from ones it invented
§3 specifies the verifier's method as the three named corruptions (delete an event, flip a
mark, swap two students). All three were already red before it ran. Its nine findings came
entirely from six corruptions it invented itself — and one of them, «rename one of the 544
labels», exposed a real defect in my work: coverage was PRINTED but not JUDGED, so a
543-of-544 run still exited 0.
ЦЕНА: a verifier that had executed §3 literally would have returned «порч 3 из 3,
покраснело 3» — a clean pass — and the defect would have shipped inside the very position
whose subject is checks that cannot fail. **§3 should require the verifier to invent
corruptions BEYOND the named ones, and should say that the named three are a floor, not the
method.** The named three are the ones the author already thought of, which is exactly why
they are the ones that pass.

### A subagent that dies on a transport error takes its findings with it, and only §0.1 has a retry protocol
The §3 verifier died at ~6 minutes on a Cloudflare 522 against `api.anthropic.com`. §0.1
carries a precise protocol for this (45-second pause, up to three attempts, time measured by
`date`) — but written as a property of the git-contour subagent, and §3 says nothing.
ЦЕНА: six minutes of verification lost, and with no protocol stated at §3 the natural
reading is that the verifier cannot be run — i.e. the one mandatory subagent of the заход
gets silently skipped. I applied §0.1's protocol by analogy and relaunched (attempt 2 of 3,
after a 130-second backoff). **The retry protocol belongs to the section on subagents in
general, not to §0.1 alone.**

<!-- инструкция раздела УРОКИ сохранена ниже -->
> Находка не про эту сессию, а закономерность про саму фабрику, годная другим заходам, — оформи как пункт очереди в `## ВОПРОСЫ` (формат там же) с `ДОМ: <эта арка>/UROKI-FABRIKE.md`, а не пиши прямо сюда неструктурированной строкой.
> **Не про задачу — про САМУ ФАБРИКУ.** Ты работаешь с пустым контекстом и потому видишь то, чего не видит аналитик: он писал этот заход и ему приятно, что заход хорош. Сломался ВХОД (издание не то, id врёт, зона не содержит файла с ответом)? Критерий готовности кривой? Инструкция канона противоречит живому файлу? — сюда, строкой.
> Формат жёсткий (по нему гейт): `### <что произошло>` / `ЦЕНА: <что сломалось и сколько стоило>`.
> **ЦЕНА обязательна.** Без неё это наблюдение, а не урок, и в канон оно не пойдёт. Не знаешь цены — не пиши.
> **Не сочиняй.** Пустая секция — законный отчёт. Выдуманный урок хуже отсутствующего: он попадёт в канон, который читают ВСЕ будущие проекты.

## ПЛАН — (заполняет исполнитель)

### 0 · What was found before planning (measured, not assumed)

- `main` had moved: P1 was accepted and merged while this branch was already cut, so
  `zahod/P2-import` sat **9 commits behind** and did not contain `core/`, `config.py`,
  `migrations/`, `Makefile` or `tests/` at all — my own zone path
  `core/services/seeding.py` lives in P1's tree. First action was `git merge main` into
  this branch. Nothing else in the tree was touched.
- `git --no-optional-locks branch --no-merged main | grep -c zahod/` → **0** (§0.1 replaced
  by the orchestrator's single command; the subagent was NOT launched, per the cancellation).
- The source workbook is where §7 says: `~/Downloads/Кондуит 8КЛ.xlsx`, 33 sheets.
- Seed and book agree exactly: **18 sheets, 544 labels, 0 sheets with any label difference**;
  `seed/sheets.json` = 215 обязательная / 288 обычная / 39 звезда / 2 двойная.
- Full inventory of the 29 920 mark cells: `None` 14 824 · `1.0` 14 377 · `'x'` 735 ·
  `2.0` 1 · `` '`' `` 1. Nothing else. §1's list is confirmed cell by cell.
- Status row: `✓` 191 · `●` 113 · `°` 102 · `✘` 88 = 494; the remaining 50 of 544 are
  sheets `1д`/`2д`, which have no status row. §1's numbers reproduce exactly.
- Column layouts: **four**, not three — old (`1,2,3,4,6,7,8`: header row 3, принимающий at
  col 2), new (`9..14,3д,4д`: header row 3, фамилия at col 1, закрыт at col 3), `15` (a
  blank column before принимающий), and `1д`/`2д` (**header IS row 1**, data starts row 2).
- Receivers: 19 distinct non-empty strings, of which **three**, not two, are composite:
  `Саша Оревкова/Ольга Александровна`, `Наталия Павлована/Ольга Александровна`, and
  **`Даня/Ольга Александровна`** — the third one is not named in §6 and is a finding.
  `Мика/Вася` contains a slash but is ONE teacher (`seed/teachers.csv`, aka `МН`).

### 1 · 🔴 A FALSE PREMISE IN THE ГОТОВНОСТИ CRITERION, RAISED BEFORE WORK AS §1 REQUIRES

§4 demands three oracles and forbids the sheet's own `SUM` row because it is computed from
the very cells being checked. I opened the workbook a second time with `data_only=False`
and read the formulas. **Two of the three oracles §4 names are the same tautology in a
longer form**, and this has to be said before anything is built on them:

- the `закрыт` column of every sheet is
  `=IF(SUMPRODUCT(REGEXMATCH(labels,"[°˚]") * NOT(REGEXMATCH(cells,"^(1|x)$")))=0,"✓",<count>)`
  — a formula over the same mark cells;
- **every per-sheet column of the `долги` sheet is
  `=INDEX(INDIRECT(<sheet>&"!A:A"), MATCH($A<row>, INDIRECT(<sheet>&"!C:C"), 0))`** — a
  VLOOKUP of that `закрыт` column. The debts sheet is therefore *not* independent evidence;
  it is the SUM row with two extra hops.

It is not worthless, and I am not discarding it: it encodes a **different definition** of
the same question (obligatory-by-label-regex rather than by `seed/sheets.json`; `x` closes
a debt), so a disagreement still finds a real defect. But it must be labelled for what it
is, or this position repeats the exact error it exists to fix.

What IS independent, measured:

- **`гробарий` — 20 rows, and every student surname in them is hand-typed (0 formula cells
  in the name columns).** A human wrote down who took each problem. This is the only
  full-provenance oracle in the book and it is not in §4's list.
- **`зачёт` — 55 rows, columns D and E hand-entered (0 formula cells).** The year's credit,
  awarded by a person. Independent, and it answers a different question than the grid does.
- **thirty cells re-read by hand** — independent by construction, as §4 says.

**Proposed correction, which I will implement unless told otherwise:** oracle 1 becomes
`гробарий` (fully independent), oracle 2 stays the thirty hand cells, oracle 3 stays `долги`
**declared as partially independent** with the formula quoted in the output, and `зачёт` is
measured as a fourth. Every oracle prints its own independence class next to its coverage,
so no reader can mistake a semi-independent agreement for a proof. The `544 из 544` figure
the criterion asks for is printed where it is honest: as the coverage of the inventory and
catalogue pass, which really does span all 544 problems.

### 2 · Decisions I am making inside the zone (§6 says decide, do not ask)

- **`'x'` (735 cells) → `assert` + `retract`, cell lands `RETRACTED`.** The schema offers
  exactly three states; `x` must be "not credited AND not a debt" (the book's own `закрыт`
  formula treats `1` and `x` identically), and `RETRACTED` is the only state with that
  meaning. `retract` requires `reverses_id`, so a carrier `assert` precedes it; that carrier
  is stamped in `note` so it can never be read as an observed check-off.
- **`2.0` and `` '`' `` (1 cell each) → quarantined, no event written, listed by name in the
  output.** They are not silent `None`: they are two named entries in an explicit registry,
  and any value outside that registry raises. This agrees with the book's own arithmetic —
  neither matches `^(1|x)$`, so the spreadsheet counts both as not-closed too.
- **Composite receivers → a second author on the mark is impossible (`marks.teacher_id` is
  one column) and inventing a record per pair loses the pairing.** Decision: the composite
  is a `teachers` row in its own right, carrying the pair as its `name` and both members
  through a resolved list in the importer, with `note` on each mark naming the second
  teacher. Written up in full in the report.
- **The unregistered senior of room 203, initials НС** — registered as a teacher.

### 3 · Order of work, one commit per part

1. `config.py` gains `KONDUIT_XLSX` (**a named zone extension** — §7 commands it and the
   post-check greps for it; reported as such).
2. `core/services/seeding.py` — the seed into a migrated database, idempotent.
3. `tools/import_konduit.py` part 1 — inventory that FAILS on the unknown, `--inventar`.
4. `tools/import_konduit.py` part 2 — the import: marks, teachers, explicit `first_sheet_id`
   with `select count(*) ... is null` → 0 asserted and printed.
5. `tools/import_konduit.py` part 3 — `--proverit`, the oracles above.
6. `tools/import_konduit.py` part 4 — `--negativnyj-kontrol`, three corruptions, red on each.
7. `tests/import/` — the whole of the above under `make check`.

## ВОПРОСЫ — (заполняет исполнитель)

1. Лист «гробарий», листок 3, задача 16б*: выписан один Цуканов, в сетке двое — Аникина
   (строка 5) и Цуканов (строка 54); собственный счётчик столбца даёт 2. Гробарий недосчитан
   на одно имя. На знак это не влияет (`=IF(COUNTA(D:ZZ)<=2,"✘","✓")` при одном и при двух
   именах одинаков), но список имён в книге неполон.
   ДОМ: владелец
   ДОСТАВЛЕНО: нет

2. Листок 4д: 26 задач, отметок НОЛЬ у всех 55 учеников, строка счётчиков — сплошные нули,
   строка статуса — 26 знаков `✘`. Это факт (листок никто не сдавал) или потерянные данные?
   Импорт вносит его как есть; если данные потеряны, восстанавливать надо до того, как
   прошлый год станет основанием для долгов.
   ДОМ: владелец
   ДОСТАВЛЕНО: нет

3. Лист «2д» несёт метку `12д` дважды (столбцы 28 и 30), а буква `г` в ряду `12а…12ж`
   отсутствует. Схема запрещает `unique (sheet_id, label)`, поэтому засев без починки не
   грузится вовсе. Починка сделана реестром (`столбец 28 → 12г`), оба столбца пусты, цена
   нулевая — но правильно исправить сам `seed/sheets.json` и книгу. `seed/` вне моей зоны.
   ДОМ: владелец
   ДОСТАВЛЕНО: нет

4. Таблица `enrollment` (кто кого ведёт, SCD2) после импорта ПУСТА. Данные для неё — в
   `Распределение.xlsx`, который §7 прямо выводит за границы этой позиции. Пока она пуста,
   у любой проекции «по преподавателю» нет истории.
   ДОМ: zhurnal/2026-09-02_spetsmat-bot/PLAN.md
   ДОСТАВЛЕНО: нет

5. `valid_at` у всех импортированных отметок — одна условная дата `2026-06-30`: книга не
   хранит дат ни по отметке, ни по листку. Есть даты выдачи листков — проставляются одним
   параметром (`seed_catalogue(issued_at=…)`, `IMPORT_VALID_AT`).
   ДОМ: владелец
   ДОСТАВЛЕНО: нет

6. Парность составных принимающих живёт в `note` как `соавтор: <имя>` (860 отметок).
   Полноценная таблица `mark_authors` требует миграции — вне зоны P2.
   ДОМ: zhurnal/2026-09-02_spetsmat-bot/PLAN.md
   ДОСТАВЛЕНО: нет

7. `git_zona.py vlit-v-osnovnuyu` пометил три влитых файла как «влито, но не встроено»
   (`core/services/seeding.py`, `tests/import/conftest.py`, `tests/import/synthetic.py`).
   Проверено — у всех трёх живая точка вызова: `tools/import_konduit.py:53` импортирует
   `core.services.seeding`, `conftest.py:14` и `test_value_registry.py:24` импортируют
   `synthetic`, а `conftest.py` грузит сам pytest и его фикстуры зовут все пять тестовых
   модулей. Эвристика ищет хук/шаг сборки и не видит ни python-импорта, ни сбора pytest —
   ложное срабатывание на любом модуле-библиотеке и на любом conftest.
   ДОМ: zhurnal/_INFRA-git/INCIDENTY.md
   ДОСТАВЛЕНО: нет

<!-- инструкция раздела ВОПРОСЫ сохранена ниже -->
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

🔴 **ЭТУ СЕКЦИЮ ЗАПОЛНЯЕТ СУБАГЕНТ ГИТ-КОНТУРА, А ОН НЕ ЗАПУСКАЛСЯ: §0.1 ОТМЕНЁН ОРКЕСТРАТОРОМ**
в стартовом сообщении, дословно — «СУБАГЕНТА ГИТ-КОНТУРА §0.1 НЕ ЗАПУСКАЙ… пункт ОТМЕНЁН
оркестратором, данное указание сильнее текста захода. Причина замерена соседней волной: четыре
захода из десяти умерли ровно на этом вызове.» Вместо всего блока §0.1 предписана ОДНА команда,
её вывод — ниже. Гигиена ВХОДА поэтому не разбиралась никем; гигиена ВЫХОДА (блок WARNING)
исполнена мной полностью и её числа — в `## ОТЧЁТ`, раздел `### КОММИТ`.

Единственная предписанная команда, первым ходом, до всякой работы:
```
$ git --no-optional-locks branch --no-merged main | grep -c zahod/
0
```

Остальной снимок входа снят мной ПОПУТНО (не по заданию субагента — его не было), первым же
ходом в рабочей папке:
```
$ git --no-optional-locks branch --no-merged main
(пусто — невлитых веток не было)

$ git --no-optional-locks status --porcelain | wc -l
0

$ git --no-optional-locks log --oneline @{u}.. | wc -l
fatal: no upstream configured for branch 'zahod/P2-import'
(у репозитория НЕТ remote вовсе: `git remote -v` пуст — вывозить некуда)
```

**ЧТО СДЕЛАНО** *(с хэшами)*

Ничего из работы субагента — он отменён. Мной, как часть СВОЕЙ работы:
- обнаружено, что `zahod/P2-import` отстала от `main` на **9 коммитов** (P1 принята и влита
  ПОСЛЕ того, как эта ветка была отрезана), и мой собственный путь зоны
  `core/services/seeding.py` физически отсутствовал в рабочей папке → `git merge main`;
- девять своих коммитов по ходу работы: `33e1268` `17aced5` `09e55d9` `20742a0` `bc2c7b7`
  `056631f` `22b01b7` `9c76fb8` `8981bb6`;
- своя ветка влита в `main` последним ходом: мерж `8c1bc79`.

Заявок (`git_zona.py zayavki`) не закрывал и не заводил — закрытие заявок принадлежит
субагенту, которого не было; своих заявок у меня не возникло.

**ВСЕ ДОЛГИ ВХОДА ЗАКРЫТЫ:** `да` *(на входе их не было: невлитых веток 0, вне git 0,
невывезенного нет за отсутствием remote)*

⚠ Оговорка, чтобы галочка не читалась шире, чем она есть: на входе разбирать было нечего, и
это ЗАМЕРЕНО, а не предположено. Долги, появившиеся В ХОДЕ волны и НЕ мои — правки соседних
заходов в `README.md`, пульс/сердце оркестратора, автолог `INCIDENTY.md`, чужой `.commit-plan` —
я оставил и назвал поимённо в `## ОТЧЁТ`, раздел `### WHAT I DID NOT TOUCH`.

## ОТЧЁТ — (заполняет исполнитель)

### §0.1 — CANCELLED BY THE ORCHESTRATOR; WHAT WAS RUN INSTEAD

The git-contour subagent was NOT launched — the orchestrator cancelled that clause in the
starting message. The one command ordered in its place, and its output:

```
$ git --no-optional-locks branch --no-merged main | grep -c zahod/
0
```

**Before any work:** `zahod/P2-import` was **9 commits behind `main`** — P1 was accepted and
merged after this branch was cut, so `core/`, `config.py`, `migrations/`, `Makefile`, `tests/`
and my own zone path `core/services/seeding.py` were absent from my worktree. `git merge main`
first, nothing else touched. (Урок фабрике #2.)

### WHAT WAS DONE AND WHY — nine commits, one per part, committed as the work went

| commit | what |
|---|---|
| `33e1268` | `config.py`: `KONDUIT_XLSX`, `SEED_DIR` — the dead sandbox path leaves the importer |
| `17aced5` | `core/services/seeding.py`: the anonymised catalogue into a migrated DB, idempotent |
| `09e55d9` | `tools/import_konduit.py`: inventory, the import, oracles labelled by independence |
| `20742a0` | `tests/import/`: a synthetic conduit, so the suite runs without the children's data |
| `bc2c7b7` | the sheet list comes from the seed, not from a tuple beside it |
| `056631f` | the reader applies the same label repair as the seed loader — 544 of 544 |
| `22b01b7` | the debts oracle checks the late arrival's pre-arrival sheets — 770 of 770 |
| `9c76fb8` | count the journal's ROWS too, and refuse a second import into a full journal |
| `8981bb6` | judge coverage instead of printing it; make the §6 attribution falsifiable |

### 🔴 THE FALSE PREMISE IN §4 — RAISED IN `## ПЛАН` BEFORE WORK, AND MEASURED

§4 forbids the sheet's own `SUM` row because it is computed from the cells being checked, and
then names the `долги` sheet as an independent oracle. Opened a second time with
`data_only=False`:

- the `закрыт` column (16 of the 18 sheets carry one) is
  `=IF(SUMPRODUCT(REGEXMATCH(labels,"[°˚]") * NOT(REGEXMATCH(cells,"^(1|x)$")))=0,"✓",<count>)`
  — over the very mark cells;
- **every** per-sheet column of `долги` is
  `=INDEX(INDIRECT(<лист>&"!A:A"), MATCH($A<row>, INDIRECT(<лист>&"!C:C"), 0))` — a VLOOKUP of
  that `закрыт` column.

**The debts sheet is the SUM row with two extra hops.** It is run anyway — it encodes a
*different definition* (obligatory by label regex rather than by `seed/sheets.json`; `x`
closing a debt), so a disagreement still finds a real defect — but it prints as
`ПОЛУЗАВИСИМЫЙ` and is never sold as proof.

The only **fully independent** oracle in the book is `гробарий`: 20 rows whose student
surnames are typed by a person, **0 formula cells** in the name columns. §4 does not name it;
it is now oracle 1. `зачёт` is measured as a fourth. Every check prints its independence
class beside its coverage.

### HOW IT WAS CHECKED — every verdict carries its coverage inside it

```
$ make check                                              rc=0   148 passed (69 of them mine)
$ python3 tools/import_konduit.py --proverit              rc=0
    [зелёный] гробарий (имена от руки)     сверено 20 из 20, расхождений 0, известных дефектов книги 1   (НЕЗАВИСИМЫЙ)
    [зелёный] тридцать клеток вручную      сверено 30 из 30, расхождений 0   (ДЛЯ РУЧНОЙ СВЕРКИ)
    [зелёный] лист «долги»                 сверено 770 из 770, расхождений 0   (ПОЛУЗАВИСИМЫЙ)
    [зелёный] лист «зачёт» (имена)         сверено 55 из 55, расхождений 0   (НЕЗАВИСИМЫЙ)
    [зелёный] журнал: число событий        сверено 15847 из 15847, расхождений 0   (ВНУТРЕННИЙ)
    [зелёный] привязка к принимающему      сверено 15526 из 15847, объявлено пропусков 321, расхождений 0   (ВНУТРЕННИЙ)
    [зелёный] полная сетка, задач 544 из 544 сверено 29938 из 29938, расхождений 0   (ВНУТРЕННИЙ)
$ python3 tools/import_konduit.py --negativnyj-kontrol    rc=0   порч 3 из 3, покраснело 3
    [покраснело] удалить событие из журнала      поймали: тридцать клеток, лист «долги», полная сетка
    [покраснело] перевернуть отметку             поймали: тридцать клеток, полная сетка
    [покраснело] поменять местами двух учеников  поймали: ГРОБАРИЙ (независимый), лист «долги», полная сетка
```

`main()` returns an `int` on all five of its paths (checked by AST; 0 bare returns) — the old
one returned `None`, so the exit code was always zero and the check could not fail
physically. Proven capable of failing: on a corrupted journal the same path returns 1.

The **thirty hand cells** print as `листок · строка · столбец · ученик · задача · в книге ·
в журнале`, so any can be re-checked by opening the workbook without running anything. They
cover every meaning class — four `x` cells and both quarantined cells included — because a
strided sample alone drew nothing but `1` and empty and would never have exercised the one
decision most likely to be wrong.

### THE NUMBERS RECONCILE EXACTLY

```
grid            14377 ('1') + 735 ('x') + 2 (quarantined) + 14824 (empty) = 29938   ✔
journal         15112 assert + 735 retract = 15847
                15112 assert − 735 carriers = 14377 = the count of '1' cells        ✔
catalogue       18 sheets · 544 problems (215/288/39/2) · 56 students · 19 teachers
first_sheet_id  set explicitly 56 of 56 · NULL 0 · 0 disagreements with the seed column
```

### DECISIONS MADE INSIDE THE ZONE (§6 says decide, do not ask)

- **`x` (735 cells) → `assert` + `retract`, cell lands `RETRACTED`.** The book's own
  arithmetic settles it: `закрыт` reads `NOT(REGEXMATCH(cell,"^(1|x)$"))`, treating `1` and
  `x` alike as «does not owe this», so `x` must mean *not credited AND not a debt* — and
  `RETRACTED` is the only state in this schema with that meaning. `retract` requires
  `reverses_id`, so a carrier `assert` precedes it, stamped in `note`. All 735 carriers are
  reversed (asserted: 0 unreversed), so a carrier can never project as SOLVED.
- **`2.0` and `` ` `` → quarantined**, no event, printed by name with coordinates. Not the old
  silent `None`: two named entries in a registry, and any value outside it stops the import.
  It agrees with the book — neither matches `^(1|x)$`, so the spreadsheet counts both as
  not-closed too.
- **Composite receivers (§6b).** `marks.teacher_id` is one column, so «one author per mark»
  cannot hold a pair. The mark goes to the **first-named** teacher; the second rides in `note`
  as a machine-readable `соавтор: <имя>` tag, on 860 marks. First-named is not a coin flip:
  `seed/teachers.csv` gives Ольга Александровна `students_actual = 0` against
  `students_count = 3`, so the seed already treats the first name as the attributed one, and
  following it keeps per-teacher statistics agreeing with the seed. A later `mark_authors`
  table can reconstruct every pair without re-reading the book. **A `teachers` row per pair
  was rejected** — a pair is not a person, and every per-teacher projection would count a
  phantom colleague. *(This revises the sketch in `## ПЛАН`, changed after measuring
  `students_actual`.)*
- **§6a — the senior of room 203, `НС`, is registered.** `senior_aka` names three seniors:
  `ДМ` is Даня and `ИЯ` is Ваня, both rows of the file; `НС` is nobody. All the book records
  of him is the initials, so the initials are his name — a full name would be invented data.
- **A third composite the задание does not name:** `Даня/Ольга Александровна` (16 rows).
  `Мика/Вася` contains a slash and is **one** teacher.
- **One label repair, registry-driven.** `2д` carries `12д` twice, which `unique (sheet_id,
  label)` refuses — the seed could not be loaded at all. Columns 25–31 are a seven-column run
  missing exactly the letter `г`, breaking at the fourth column; both duplicate columns are
  empty over all 55 students (measured), so no mark can be misattributed. A duplicate not in
  the registry raises.

### FOUR LAYOUTS, NOT THREE

`1 2 3 4 6 7 8` (header row 3, принимающий at col 2) · `9…14 3д 4д` (header row 3, surname at
col 1, закрыт at col 3) · `15` (a blank column before принимающий) · **`1д 2д` — the header
IS row 1, with no status row at all**, where 50 of the 544 problems live. The old layout
finder could not see the last of these.

### РЕЗУЛЬТАТ ВЕРИФИКАТОРА §3 — nine findings, all acted on

Fresh subagent, different method, after-type. Its verdict: *«the central error has not
returned in its original form — the exit code is real, `main()` returns an int, `долги` is
correctly outed as ПОЛУЗАВИСИМЫЙ, and 6 of my 9 corruption/probe attacks were caught. But two
of six oracles wear an independence label their own definition forbids, coverage is printed
rather than judged so a 543-of-544 run exits 0, and three of my six corruptions passed
unnoticed.»* Final line as required: **«выдано 9 позиций из 9 найденных»**.

It confirmed independently, with its own openpyxl and without importing my reader: 544 problem
columns, 29938 mark cells, all five values with identical counts; `гробарий` names 0 formulas,
`зачёт` 0 formulas, `долги` an INDEX/INDIRECT/MATCH lookup in 766 of 770 cells; 56 students,
0 NULL `first_sheet_id`, 56 of 56 agreeing with the seed; 10 files changed, all in scope; P1's
fallback test untouched and passing; no `.xlsx` in git; all three commands exit 0.

**What it found wrong in my work, and what I did about each — all nine fixed in `8981bb6`:**

| # | finding | fix |
|---|---|---|
| **5** | **coverage was PRINTED, not JUDGED**: `is_red` fired only on ZERO coverage, so renaming one of 544 labels gave «543 из 544» and still exited 0 | incomplete coverage is red on its own; a legitimate skip must be DECLARED in `skipped` and is counted. **Verified: that attack now exits 1** |
| 2 | `journal_cardinality` labelled `НЕЗАВИСИМЫЙ` though both sides descend from `read_cells` | relabelled `ВНУТРЕННИЙ` |
| 3 | the thirty hand cells likewise use my own reader; independence exists only if a human looks | relabelled `ДЛЯ РУЧНОЙ СВЕРКИ` |
| 6 | **no check read `teacher_id` at all** — the whole §6 decision could not fail; wiping every mark onto one teacher passed all six checks green | new `привязка к принимающему` check against the `принимающий` column. Caught now |
| 7 | the carrier marker was free text nothing tested; stripping it went green | reversal asserted (0 unreversed) and the note itself checked. Caught now |
| 9 | 544/29938 were pinned only by `test_real_workbook.py`, which SKIPS without the book — pinned by nothing on CI | coverage identity asserted on the synthetic conduit too; **56 passed with the workbook absent** |
| 1 | comments said «29 920 cells»; the real number is 29938 | corrected in 3 places |
| 8 | «the `закрыт` formula of every sheet» is 16 of 18 (`1д`/`2д` have none) | corrected |
| 4 | `oracle_credit`'s docstring cited columns D and E; it reads B and C | corrected — I re-checked B and C myself: 0 formulas, the conclusion stands, the reasoning did not |

The verifier's own three "still green" corruptions were re-run after the fix: **wipe teacher
attribution → RED · strip the carrier note → RED · rename one of 544 labels → RED.**

**Its one point I did not act on** is its note that genuinely independent evidence about the
*marks* is 24 of 544 (20 `гробарий` problems + 4 hand-typed `долги` cells). That is correct
and it is a property of the book, not of the code: the book contains no more hand-made
evidence than that. It is why the independence class is printed on every line rather than
averaged away, and it is the honest ceiling of this position.

### WHAT I DID NOT TOUCH

- **P1's fallback is untouched** — «NULL means owes from the very first sheet», pinned by
  `tests/test_verifier_findings.py::test_a_student_with_no_first_sheet_owes_from_the_very_first_sheet`
  (verified unchanged and passing). It is out of my zone and right for imported rows. This
  import instead makes `NULL` impossible (56 of 56 set), so the fallback never fires for
  anyone who came from the book. Registration's default is P3's business.
- Everything outside the zone, with **one declared extension**: `config.py`, +19 lines, two
  constants. §7 commands the path constant to live there and the WARNING post-check greps that
  file for `KONDUIT_XLSX`. Nothing else outside the zone was edited.
- **The workbook is not in the repository and was not copied into it.** `git ls-files | grep -i
  xlsx` → empty. Only the anonymised seed already in git is read.
- **Not mine, left alone and named**, in the main folder: `README.md` (registry lines for the
  P4 and P6 заходы), `zhurnal/2026-09-02_spetsmat-bot/PULS-CHASOVOGO-sborka-bota.log` and
  `SERDCE-VOLNY-sborka-bota.md` (orchestrator heartbeat), `zhurnal/_INFRA-git/INCIDENTY.md`
  (`git_zona.py`'s own autolog, four lines, two about my merge and two about P3's), and
  `.commit-plan` (untracked, not mine).

### НЕОБРАТИМОЕ

**Необратимого нет.** `tools/import_konduit.py` was rewritten; the previous version is in git
history (`git show f588899:tools/import_konduit.py`). No file deleted, moved or renamed; no
`git reset` or `checkout` over unsaved work; the source workbook was opened read-only and
never written; the importer writes only to a throwaway temp database. My own drafts were moved
out of the repository to the session scratchpad so the worktree is clean — nothing of the
project was in them.

### ПОВТОРЯЕМОСТЬ НАХОДОК

- **Repeats on the NEXT unit of work — fix before the next run, not a queue item:** the
  branch-behind-`main` trap (Урок #2) hits every заход whose zone names a file another заход
  produces, and P4/P6 depend on P1–P3 exactly that way; the subagent retry protocol living
  only in §0.1 (Урок #3) applies to every заход with a §3 verifier, i.e. all of them; and
  §3's «three named corruptions» floor (Урок #4) — a verifier that runs only the named three
  passes cleanly and misses the real defect, as it did here.
- **Does not repeat — legitimate queue items:** the tautology in §4 (Урок #1) is specific to
  this position's oracles, though the rule it yields is general; and every item in
  `## ВОПРОСЫ`, which is about last year's data rather than about the next unit of work.

### ВРЕМЯ И ТОКЕНЫ

Снимает ПРИЁМКА из лога прогона — исполнителю счётчик недоступен.

### АРТЕФАКТ

```
/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/tools/import_konduit.py
/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/core/services/seeding.py
/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/tests/import/
```

Открыть и запустить:
```
cd /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot && python3 tools/import_konduit.py --proverit
```

### КОММИТ

Девять коммитов, по ходу работы, каждая часть отдельно — влиты в `main` мержем `8c1bc79`.

```
вне git (моя рабочая папка)              0
вне git (главная папка)                  5 — все ЧУЖИЕ, перечислены выше поимённо
невлитых веток zahod/ на входе           0
невлитых веток zahod/ на выходе          0
невывезенных коммитов                    неприменимо: у репозитория НЕТ remote вовсе
                                         (`git remote -v` пуст) — вывозить некуда
пост-проверка из главной папки           ЗЕЛЁНАЯ: make check rc=0 (148 passed),
                                         --proverit rc=0, --negativnyj-kontrol rc=0
Г1 зона доехала в git                    ✅ ✅ ✅ (все три пути)
Г2 второй репозиторий                    неприменимо: все пути зоны внутри spetsmat-bot
Г3 невлитых не прибавилось               0 → 0
Г4 новый .py в _generator/**             неприменимо: ни одного не заводил
Г5 новый .md зарегистрирован             неприменимо: ни одного .md не заводил
Г6 чужих путей в коммитах                нет — 10 файлов, все свои (+ config.py по §7)
```

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

**ВЕТКА РАБОТЫ:** `zahod/P2-import`
*(проверяется фактом, не словом: ветка обязана существовать и быть либо ВЛИТА в основную, либо названа в открытой заявке на влитие. Ни того, ни другого — Г14 краснеет. Снять состояние: `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py poteri --branch <ветка>`)*

**ЗАЯВКИ, ПОСТАВЛЕННЫЕ ЭТОЙ ПРИЁМКОЙ — ПРОДУБЛИРУЙ СЮДА ТО, ЧТО УЖЕ ЛЕЖИТ В СПИСКЕ:**
> Адрес списка: `/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/zhurnal/_INFRA-git/zayavki`
> Читается командой (из любой папки, в том числе из worktree): `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py zayavki`
> Ставится командой: `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py zayavka --rod <git-operaciya|pravka-koda> "<текст>"`
> 🔴 Вопрос здесь НЕ «что ты хочешь сделать», а «что ты УЖЕ положил в очередь». Дубль сверяется с очередью по id машинно; намерение сверить не с чем.

- `<id заявки>` — `<род>` — `<суть одной строкой: влитие / коммит / вывоз / деплой / гашение>`

*(Заявок эта приёмка не ставила — так и напиши строкой «заявок нет: <почему ни одна из пяти операций не понадобилась>». Пустая строка и прочерк не принимаются: молчание неотличимо от «забыл».)*
