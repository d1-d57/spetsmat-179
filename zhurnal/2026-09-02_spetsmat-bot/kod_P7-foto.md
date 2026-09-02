# Канал исполнителя — P7-foto (один заход до конца)
> Твой единственный файл-заход. Читай ТОЛЬКО его и названные якоря; проект не изучай.
<!-- собран bootstrap_zahod.py -->
> План/вопросы/отчёт — в секции внизу. Метрика — КАЧЕСТВО. Часы — норма.
> **Модель: Opus 5** — конвейер с внешней моделью: отказы притворяются успехом (HTTP 200), лимит трат приходит как 429 без retry-after, а фамилии не имеют права уехать с сервера — цена ошибки не в качестве, а в утечке.

## СТАРТОВОЕ СООБЩЕНИЕ ВЛАДЕЛЬЦУ

> Это блок для владельца — то, чем тебя запустили. Исполнителю здесь делать нечего, твоё задание ниже.

```
bash /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/zhurnal/2026-09-02_spetsmat-bot/ZAPUSK-ZAHODA.sh P7-foto opus
```
🔴 **ЧЕМ ЭТА СТРОКА ОТЛИЧАЕТСЯ ОТ ТОЙ, ЧТО ПЕЧАТАЛ ГЕНЕРАТОР.**
Генератор вписал `claude -p --model arn:aws:bedrock:…` — ARN application inference
profile. На ЭТОЙ машине Bedrock-доступа НЕТ вовсе: ни `~/.aws/`, ни переменных `AWS_*`
(замер 2026-09-02 08:22). Цена оплачена соседней волной 2026-09-02 07:07: пять платных
позиций из пяти оборвались за девять минут с «Could not load credentials from any
providers», и снаружи это неотличимо от «заход думает». `ZAPUSK-ZAHODA.sh` берёт модель
вторым аргументом и сам выбирает маршрут; добор — тем же вызовом с `--dobor`.

<!-- прежняя строка генератора, сохранена дословно, НЕ исполнять:

python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py worktree add P7-foto --branch zahod/P7-foto && cd /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot-wt/P7-foto && claude -p --verbose --output-format stream-json --model arn:aws:bedrock:us-east-1:811345154057:application-inference-profile/d78ovu0ye0t4 --dangerously-skip-permissions 'Твой заход — файл /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/zhurnal/2026-09-02_spetsmat-bot/kod_P7-foto.md. Прочитай ТОЛЬКО его и то, что он называет; остальной проект не изучай. План/вопросы/отчёт пиши в этот же файл внизу (## ПЛАН / ## ВОПРОСЫ / ## ОТЧЁТ). Ничего сверх задачи не трогай — «ничего сверх задачи» относится к СОДЕРЖАНИЮ работы; git-контур §0.1 — законное исключение, он про состояние репозитория и исполняется целиком.' < /dev/null 2>&1 | tee /tmp/zahod-P7-foto.jsonl | python3 -u -c 'import sys,json
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
   print("  %s: вх %s вых %s USD %s" % (m, v.get("inputTokens"), v.get("outputTokens"), v.get("costUSD")))' /tmp/zahod-P7-foto.jsonl
```

── СЧЁТ НЕЗАКРЫТОГО (печать, не гейт) ──
ГРАНИЦА ОБЛАСТИ: сырые подстроки в `kod_*.md` (пункт 4) — НЕ парсер очереди `dostavit_urok` (который считает только пары ДОМ:/ДОСТАВЛЕНО:). Разница в числах — законна.
🔴 снимок при сборке 2026-09-02, ПРОВЕРЬ ПЕРВЫМ ХОДОМ: `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/schet_nezakrytogo.py zhurnal/2026-09-02_spetsmat-bot`
Область: «zhurnal/2026-09-02_spetsmat-bot» — сужены пункты 1, 3, 4; долги (2) глобальны намеренно (DOLG.md не размечен по записям).
Приоритет владельца: разобрать инциденты важнее, потом закрыть долги — неразобранный инцидент это повторяющаяся ошибка, долг может подождать.
  1. инцидентов без вердикта             : н/д — VERDIKTY.md/INCIDENTY.md не найдены
  2. долгов СТАТУС: ЖИВ                  : н/д — /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/skills/slajdy/DOLG.md недоступен (другой git-репозиторий)
  3. уроков фабрике без ВЕРДИКТ          : 7
  4. пунктов очереди «ДОСТАВЛЕНО: нет»   : 46
     из них разбором очереди (парсер `dostavit_urok`, записи с парой ДОМ:/ДОСТАВЛЕНО:): 22
       живых (чинится доставкой — «дом есть»)  : 6
       к владельцу (решение за человеком)      : 10
       адрес недоступен (нет/папка/код/указат.) : 4
       адрес не разобран                        : 0
       отработавших (машинный след закрытия)    : 0
       доставлено                               : 2
       🔴 не проверяется машиной: содержательная отработанность записей БЕЗ следа закрытия (метки в доме, строки ✅/ЗАКРЫТО) — нужна ревизия человеком; сырой греп сверх разбора — шаблонные строки формы.

КОНТЕКСТ. `spetsmat-bot` — телеграм-бот кондуита спецмата 179-й школы: 56 учеников,
18 преподавателей, три аудитории. Прошлый этап: приняты и влиты P1 (ядро), P2 (импорт
прошлого года), P3 (регистрация и роли) и P4 (сетка приёма — главный экран). Кнопками
отметить можно; но преподаватель на занятии часто пишет на бумаге, а вносит потом.
ЦЕЛЬ: третий равноправный способ ввода — сфотографировал печатный бланк, бот разобрал,
показал ВСЮ таблицу целиком, преподаватель поправил тапами и подтвердил.
Приёмка — по ОТЧЁТУ, без построчной сверки. Если стоп до цели: получишь генератор бланка
и конвейер до черновика, но НЕ голос (P8) и НЕ быстрый текст (P15) — они переиспользуют
твою таблицу подтверждения.

## ЧТО ФИНАЛИЗИРОВАНО НА ИНТЕРВЬЮ

ИНТЕРВЬЮ ПРОВЕДЕНО: да (2026-09-02) — флаг `--intervyu da` при сборке. ⚠ Он доказывает, что аналитик не ЗАБЫЛ про интервью, и НЕ доказывает, что разговор был.

1. печатные бланки вместо свободных записок: фамилия и номер листка сверху один раз, номера задач в сетке
2. подтверждение — ВСЯ разобранная таблица целиком, галочка снимается и ставится тапом
3. фамилии НЕ покидают сервер: в модель уходит бланк с кодами или обрезанным полем, сопоставление локальное
4. отметка НИКОГДА не пишется в базу без подтверждения человеком — самое важное правило проекта

## КОНТРАКТ ЗОНЫ (обязателен — не удалять; вписан Cowork)
- **МЕСТО РАБОТЫ:** **рабочая папка `/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot-wt/P7-foto`** — ТОЛЬКО ДЛЯ КОДА (worktree захода, ветка `zahod/P7-foto` в ней уже стоит). 🔴 **ДАЛЬШЕ — ТОЛЬКО ПУТИ ОТНОСИТЕЛЬНО ЭТОЙ ПАПКИ** (или `cd` в неё безусловно, каждым ходом): абсолютный путь в главную папку репозитория здесь — типичная ошибка, правка утекает МИМО worktree и найдётся только на коммите («вне git» в `git_zona.py check --zone` из рабочей папки, на файле, который уже правил, — цена, оплаченная живьём: 5 файлов, ручное копирование и откат главной папки). 🔴 `git checkout` в основной папке ЗАПРЕЩЁН: рядом идут другие заходы, переключение подменит файлы у них под ногами. 🔴 **Сам файл-заход (этот `.md`) при этом остаётся в ОСНОВНОЙ папке репозитория** — один экземпляр, не копия в рабочей папке: ПЛАН/ВОПРОСЫ/ОТЧЁТ/УРОКИ пишешь в него по абсолютному пути, названному в стартовой строке, а сам файл НЕ коммитишь — это делает аналитик при приёмке (цена обратного правила — полсуток 03.08: отчёт писали в рабочую папку, владелец и приёмка её не видели, приёмка трижды объявила отчёт пустым). 🔴 **Ветку в конце вливаешь САМ, последним ходом, после коммита зоны** (решение владельца 25.08; полный порядок печатает WARNING-блок ниже).
- **ЗОНА (можно менять):** `core/services/raspoznavanie.py` `infra/llm.py` `bot/routers/photo.py` `tools/blank.py` `tests/photo/`. Всё вне — **READ-ONLY**: не править, не двигать, не удалять, не рефакторить «заодно».
- 🔴 **ЗАВЁЛ НОВЫЙ `.md` — РЕГИСТРИРУЕШЬ ЕГО САМ, ТЕМ ЖЕ ХОДОМ, ОДНОЙ КОМАНДОЙ:** `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/register_doc.py <путь> "<описание>"` (из корня репо). `_studio/docs/` тебе по-прежнему READ-ONLY **для правки руками** — дверь ровно одна, и это она. Дверь идемпотентна (повторный вызов дубля не заведёт) и отказывает на пути вне `_studio/`, на несуществующем файле и на пустом описании. Свой файл-заход регистрировать не нужно: он рождается зарегистрированным из `bootstrap_zahod.py`. **Красный хук на ТВОЁМ новом `.md` — это не повод для `--no-verify`, а повод позвать дверь.** *Почему правило существует и почему оно теперь исполнимо: 26.07 оно записано с ценой в пять документов-сирот и через два дня повторилось дословно. Дальше стало хуже: до 30.07 указания «зарегистрируй» и «`docs/` только на чтение» противоречили друг другу, выход был ровно один — обойти хук, и по автологу `_INFRA-git/INCIDENTY.md` это 28 обходов `--no-verify` из 56 срывов коммита, 27 из них по одной этой причине (48 % всей боли с коммитами, тринадцать исполнителей подряд). Обходить больше нечего.*
- **КОММИТ:** два хода — `add` по своим путям, затем `commit` **с теми же путями после `--`** (полная форма и цена каждого хода — §4); коммить ПО ХОДУ работы, не одним последним ходом (§4). НИКОГДА `-A` / `.` / `commit -am`, и никогда `commit` без путей. Субагенты не коммитят. **`--no-optional-locks` обязателен:** обычный git переписывает индекс, берёт `.git/index.lock` и роняет параллельный ручной коммит владельца.
- **SCRATCHPAD — ТОЛЬКО ЛИЧНЫЙ.** Черновики, выкладки, промежуточные версии — в личную папку СВОЕГО захода `scratchpad/P7-foto/`. Общие пути (`scratchpad/otchet.md`, любой `scratchpad/*` без имени твоей темы) ЗАПРЕЩЕНЫ: чужой отчёт уедет в твой файл или твой — в чужой, а приёмка читает отчёт без построчной сверки и подмену НЕ ЛОВИТ по построению. *Цена 25.08: готовый `## ОТЧЁТ` захода konvejer-incidentov был записан в общий `scratchpad/otchet.md`, и 92 строки чужого отчёта простояли в `kod_slovari-v-kod.md`.*
- 🔴 **Звал `register_doc.py` — допиши `_studio/docs/KARTA.md` к своим путям В ОБОИХ ходах.** Строка регистрации лежит физически в нём. Ворота 5 читают `§6` **с диска**, а не из индекса: коммит без этого файла пройдёт ЗЕЛЁНЫМ, документ уедет сиротой, а строка умрёт при первом `checkout` (дата данных 2026-07-30, найдено верификацией захода «kod_registracia-bez-obhoda.md»).
- **ЗАПРЕТ:** ничего за пределами зоны, даже если «мешает» или «чинится в одну строку». Нашёл проблему вне зоны → в отчёт, не трогай.

## 0. ПЕРВЫЙ ХОД
### 0.1 🔴 ГИТ-КОНТУР — ДО ВСЕГО ОСТАЛЬНОГО, И ПЕРВЫМ ХОДОМ ЦЕЛИКОМ

🔴 «ничего сверх задачи» относится к СОДЕРЖАНИЮ работы; git-контур §0.1 — законное исключение, он про состояние репозитория и исполняется целиком.

🔴 **ПОРЯДОК ЗДЕСЬ — ЧАСТЬ УСТРОЙСТВА, А НЕ ОФОРМЛЕНИЕ. Сначала субагент вливает названные через `--vlit` ЧУЖИЕ ветки В ОСНОВНУЮ, и только ПОТОМ ты заводишь свою рабочую папку; СВОЮ ветку он не трогает никогда — её вливаешь ты сам последним ходом (граница прав ниже).** Пока влитие шло в ветку захода, а влитие в основную было ходом приёмки (которая из песочницы в `.git` писать не может), работа копилась лестницей в последней ветке цепочки, а основная не получала ничего — замер 14.08: 14 невлитых веток, цепочка из пяти внутри последней, 84 невывезенных коммита, и генератор в основной папке не знал о собственных улучшениях. Заводя ветку ПОСЛЕ влития, ты отпочковываешь её от основной, которая уже всё содержит: инструмент оказывается на диске сам, дотаскивать нечего.

**1. ВЕСЬ КОНТУР — В СУБАГЕНТА, ОДНИМ ХОДОМ, ДО СВОЕЙ ПАПКИ.** Очередь заявок, влитие названных веток в ОСНОВНУЮ, что забрать в git по ходу и что погасить после — на содержание твоей задачи не влияют. Запусти ОДНОГО субагента, дождись его и вставь его шесть строк в `## ОТЧЁТ` дословно; сам эти пункты не исполняй. 🔴 ПОРЯДОК ПРИ ПАДЕНИИ ЭТОГО ВЫЗОВА — исполняй, не изобретай (движок роняет `network_error` на вызове субагента и уносит с собой ВЕСЬ заход, замер волны 3A — 4 захода из 13). Пауза 45 секунд, до трёх попыток; время меряй `date`, не суммой своих `sleep`. После третьей — работай БЕЗ субагента: контур остаётся неразобранным, и это ОТДЕЛЬНАЯ строка в `## ОТЧЁТ`, а не молчание. У него ОТДЕЛЬНЫЕ ПРАВА, объявленные в его же промпте: главная папка, основная ветка, вывоз — и ничего сверх; зону захода он не коммитит, её коммитишь ты сам, по ходу работы (§4). 🔴 ОТВЕТ ЛЮБОГО субагента, которого ты запускаешь (не только этого), обязан КОНЧАТЬСЯ строкой «выдано N позиций из M найденных»: канал мог оборвать его молча, и без этой строки усечение неотличимо от честного «мало нашлось». Нет строки — ответ усечён, в `## ОТЧЁТ` не вставляй, перезапроси. Полный текст задания печатает команда:
```
python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/bootstrap_zahod.py --zadanie-subagentu --zone core/services/raspoznavanie.py --zone infra/llm.py --zone bot/routers/photo.py --zone tools/blank.py --zone tests/photo/ --kommitit 'core/services/raspoznavanie.py, infra/llm.py, bot/routers/photo.py, tools/blank.py, tests/photo/' --zakryt 'влить ветку zahod/P7-foto в main последним ходом, после коммита зоны'
```

🔴 ГРАНИЦА ПРАВ, ЧЕТЫРЕ ОТВЕТА (та же, что в самом задании субагенту — одно место в тексте, а не пересказ): **кто вливает ЧУЖИЕ названные (`--vlit`) ветки** — субагент, в ОСНОВНУЮ ветку, до заведения твоей папки; **кто вливает СВОЮ ветку этого захода** — ты сам, последним ходом, после коммита зоны (`git_zona.py vlit-v-osnovnuyu`; решение владельца 25.08 — оно сняло противоречие волны 4, когда машинное §0.1 и текстовое «ветку НЕ вливать» спорили молча, и машинное побеждало); **кто закрывает заявки** — субагент, `zayavka-zakryt`; **кто коммитит пути ВНЕ зоны захода** — субагент (хвост Cowork и что назовёт пункт 3 его задания). Ты коммитишь ТОЛЬКО зону этого захода, по ходу работы (§4). 🔴 Конфликт на `README.md` при ЛЮБОМ слиянии разрешается ОБЪЕДИНЕНИЕМ записей реестра, НИКОГДА выбором стороны: параллельные заходы волны дописали в реестр по строке — обе записи правы, выбор одной молча уничтожает регистрацию соседа.

**2. ТЕПЕРЬ ЗАВОДИ СВОЮ РАБОЧУЮ ПАПКУ** (команда — в блоке «МЕСТО РАБОТЫ» выше) и работай в ней как обычно. Её ветка отпочкована от свежей основной, поэтому инструмент, которым ты работаешь, уже на диске — отдельного «влить перед работой» больше нет.

Невлитых `zahod/*`-веток, НЕ покрытых `--vlit`, — 2: `zahod/P12-gruppy`, `zahod/P4-setka` — 🔴 снимок при сборке 2026-09-02, ПРОВЕРЬ ПЕРВЫМ ХОДОМ: `git --no-optional-locks branch --no-merged main | grep -c 'zahod/'`. 🔴 КЛАПАН ОТКРЫТ АНАЛИТИКОМ, причина дословно: «волна идёт: zahod/P4-setka, zahod/P12-gruppy и zahod/P6-zanyatia работают прямо сейчас. P7 СТАРТУЕТ ТОЛЬКО ПОСЛЕ ПРИЁМКИ P4 — таблица подтверждения переиспользует её сетку. Ветку вливает каждый заход свою сам.». Заход собран ВОПРЕКИ невлитому этой веткой — отключение видно здесь, в артефакте, а не осталось решением в голове аналитика (§79 канона: невлитая ветка законна, рядом может идти чужой заход).


- деплоя в этом заходе нет.

- `cd /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot-wt/P7-foto` — рабочая папка ДЛЯ КОДА. Ветку НЕ переключай: `zahod/P7-foto` в ней уже стоит.
- Проверить, что на месте: `git rev-parse --abbrev-ref HEAD` → должно быть `zahod/P7-foto`.
- ПЛАН/ВОПРОСЫ/ОТЧЁТ/УРОКИ ФАБРИКЕ пиши в ЭТОТ файл — он в основной папке, не копируй его в рабочую.
- Точка отката: `git add core/services/raspoznavanie.py infra/llm.py bot/routers/photo.py tools/blank.py tests/photo/` → commit (или zip), если зона не чиста в HEAD (не фабрикуй, если чиста).
- Прочитать ТОЛЬКО: `названные файлы-якоря`. Проект не изучай.
- ПЛАН — в `## ПЛАН` перед действиями.

## 1. ДИСЦИПЛИНА (Карпатов)
🔴 **Код возврата — ПЕРВЫМ, до содержательного вывода команды.** «Отработала» и «упала, а я читаю прошлое состояние» выглядят одинаково; сначала `echo $?`, потом выводы. То же с гейтами. *Цена 21.07: `rc=128` (сбой прав окружения) четырежды прочитан как результат — едва не откатили верное правило по ложным данным.*
Предпосылки/развилки назвать вслух; минимум без спекуляций; хирургия (строка → к заданию); критерий, который может провалиться. Якорные замены — abort при ≠1. Сохранять по умолчанию. **Оспорить ложную предпосылку — включая КРИТЕРИЙ ГОТОВНОСТИ: считаешь его кривым — скажи в `## ПЛАН`, ДО работы, и предложи поправку.** Субагенты: ≤5, рейт-лимит = отступить + доложить (не слепой ретрай).

🔴 **Пишешь содержательный текст — термин НЕ употребляется раньше, чем определён**, включая заголовки, подводки и формулировки теорем. «Определение в тексте есть» не считается: если оно ниже первого рабочего употребления, читатель встаёт ровно там. Чинится ПЕРЕСТАНОВКОЙ определения вверх, не дописыванием пояснения. Гейт: `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/check_termin.py <src>` (exit 1 при нарушении). Канон — `../docs/kak-delat/STANDART-teksta.md` правило 11. *Цена 30.07: теорема пользовалась словом «ординал», определение стояло строкой ниже; поймал владелец, ни один гейт не увидел, раздел переписан дважды.*

## 2. ЗАДАЧА

🔴 **WRITE YOUR `## ОТЧЁТ`, `## ПЛАН` AND `## ВОПРОСЫ` IN ENGLISH, AND EVERY FILE AND EVERY COMMIT MESSAGE YOU PRODUCE TOO.** Owner's decision 30.08. It is a каркас-level rule, not a preference — wave 2 lost it twice because the pass text listed the report SECTIONS and never said «every file you create». Fixed Russian addresses stay Cyrillic: `ЦЕНА:` · `ВЕРДИКТ:` · `ДОМ:` · `ДОСТАВЛЕНО:` · `ПОДЪЁМ:` · `[ДОЛГ: …]` · every `## ` heading of this file · every path and command.
Photo → draft → confirmation table → journal. **There is never a direct write.**

Everything below is MEASURED, not preference. Where a number is given, it came from a benchmark
or from a live run on this project — do not re-derive it and do not "improve" it by intuition.

### 1 · The printed form is what makes this tractable

`tools/blank.py` already generates a printed form. The owner prints tables: surname and sheet
number at the top ONCE, task numbers in a grid. There is nowhere to confuse a handwritten 7 with
a 5 in a printed grid — this removes most of the recognition problem before the model sees anything.

🔴 **The form carries CODES, not surnames** (`u17`, not «Петров»). See §4.

### 2 · Intake

- `getFile` gives at most **20 MB** — asymmetric: the bot can send 50, download 20.
- A photo arrives as an array of sizes. Ceiling 2560 px on the long side with the sender's HD
  toggle on, otherwise 1280. Compression is always client-side; the original does not exist.
- Ask for a document only when the handwriting is small or the sheet was shot from far away —
  the gain is not resolution (models downscale anyway) but the absence of a second JPEG generation.

### 3 · 🔴 PREPROCESSING: THE CLASSIC OCR ADVICE ACTIVELY HARMS HERE

VLM-RobustBench, March 2026, 133 configurations over 9–11 models, accuracy loss in percentage points:

| operation | loss |
|---|---|
| autocontrast | 0,0 |
| greyscale | 3,2 |
| histogram equalisation | 3,5 |
| inversion | 10,1 |
| **upscaling** | **up to 34 — the worst operation in the entire benchmark** |

**DO:** honour EXIF orientation (the cheapest and largest single win, up to 14% on closed models),
crop the sheet out of the frame, correct perspective only if the quadrilateral is visibly not
rectangular, downscale with `INTER_AREA` to ~1568, JPEG quality 90.
**DO NOT:** binarise, greyscale, denoise, upscale, equalise histograms. Blur is the worst measured
degradation and `fastNlMeansDenoisingColored` costs 3,4 s on top.
Order matters: geometry and tone AFTER the resize — ten times cheaper on a small image. The whole
pipeline fits in 230–250 ms.

**Do NOT slice into per-row strips.** The only direct measurement on handwritten tabular records:
CER 64 with per-row slicing against 1,21 on the whole scan. A strip without context invents. Plus
triple the tokens.

### 4 · 🔴 SURNAMES DO NOT LEAVE THE SERVER — this is a legal boundary, not a preference

Sending surnames to Gemini or OpenAI is a cross-border transfer of personal data, and the lawful
procedure for a private person is unworkable. **But if the image carries no personal data, there
is no object of regulation at all.** So: the form carries codes (`u17`), or the surname field is
cropped off BEFORE the outgoing request — never «we'll delete it later». Matching is local.
This is data minimisation in its purest form, not a loophole.

**The model is given a CLOSED LIST** — an `enum` over student IDs and task IDs, never surnames.
Then it physically cannot invent a student who does not exist.

### 5 · The call, and the settings that matter more than all the preprocessing

`temperature=0`, resolution `high`, and — the counterintuitive one — **`thinking_level=minimum`**:
at minimal reasoning results are **up to 75% better**, because high reasoning makes the model
talk itself out of what it saw.

**Schema.** `raw_text` FIRST and REQUIRED — the verbatim transcription, not normalised. Required
fields are emitted in schema order, and the main quality loss under a schema comes from the
instruction to format, cured by transcribing first and formatting second. It also gives a second,
independent matching channel.

🔴 **Split the enum across TWO fields.** Gemini's practical ceiling is ~120 values; 56 students
plus 45 tasks is 101 — on the edge. Validate the task label in code.

🔴 **A MODEL WRAPS ITS JSON IN A MARKDOWN FENCE EVEN UNDER A STRICT SCHEMA.** Measured on this
project 2026-09-02 on a live key: `minimax-m3` returned a perfectly valid `{"rows": []}` inside a
fence and the naive parser rejected it. **Strip the fence before parsing.** A bot that does not
will drop valid answers and look broken.

### 6 · Confidence from the model does not exist

A numeric `confidence` collapses to 0,9 and 1,0 and stays high while accuracy falls. Logprobs are
unavailable as a substitute across all three providers. **Compute your own:** expand the 56
surnames across cases (350–670 forms), `rapidfuzz.fuzz.ratio` against `raw_text`, threshold ~0,7.
**Not `token_set_ratio`** — it returns 100 on containment («Иванов И.» against «Иванов»).
Disagreement between the model's pick and the fuzzy match IS the signal «doubtful».
On ambiguity («two Petyas») the model must return `UNKNOWN` and fill `alternatives` — the bot then
shows two buttons. Never make it guess: it will.

### 7 · Failures that pretend to be something else

- **A model refusal and a content filter are HTTP 200.** Check the stop reason BEFORE touching JSON.
- **Spend-limit exhaustion arrives as 429 WITHOUT `retry-after`** — a standard retry hammers
  forever. Distinguish by the error text. Eternal retry is forbidden.
- Google's SDK has **no timeout and no retries by default** (its documentation describes what you
  must switch on), and its `timeout` is in **milliseconds**.
- Timeout 30–60 s, never 600: a handler hanging ten minutes is a dead bot to a teacher.

### 8 · Confirmation, and idempotency

The whole parsed table is shown as «ученик × галочки»; a tap toggles a cell. **Nothing reaches the
journal until confirmed.** Then it goes through P4's existing marking path — you do not write a
second one.

**Idempotency key = SHA-256 of the downloaded BYTES**, not `file_unique_id` (whose guarantee is
literally worded «is supposed to be the same»). Plus a confirmed-drafts table: zero rows affected
means «already recorded, exit». This is the only layer that survives both a process restart and a
re-delivered update.

**КРИТЕРИЙ ГОТОВНОСТИ (может ПРОВАЛИТЬСЯ), каждая команда печатает ЧИСЛО:**

    cd /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot-wt/P7-foto
    make check
        # rc=0; печатает «N passed», N больше того, что было до тебя
    python3 -m pytest tests/photo -q
        # rc=0; печатает охват: 3 класса отказа (200-отказ, 429 без retry-after,
        # таймаут) × 2 повтора = 6 проверок, задвоений 0
    python3 -m pytest tests/photo -q -k "fence or fenc"
        # rc=0; ИМЕНОВАННЫЙ тест: JSON в markdown-заборе разбирается, а не отвергается
    python3 tools/blank.py --proba
        # rc=0; печатает, сколько кодов и задач помещено на бланк, и что фамилий на нём 0
    grep -rn "фамили\|surname" core/services/raspoznavanie.py infra/llm.py | grep -i "prompt\|payload\|request" ; echo "rc=$? (1 = фамилия не уходит в запрос = верно)"

🔴 Отрицательный вердикт несёт охват В СЕБЕ. И тест на отказ модели обязан ПАДАТЬ, если код
принимает HTTP 200 за успех не глядя.
**Отрицательный вердикт несёт ОХВАТ В СЕБЕ:** не «дыр не найдено», а «дыр не найдено, проверено X из Y». Без охвата вердикт не принимается — «проверено 2 из 9» и «проверено 9 из 9» выглядят одинаково.

## 3. ВЕРИФИКАТОР (если двигаем/теряем/жмём)

Верификатор нужен, тип — **ПОСЛЕ-типа** — судит результат, стоит в конце, после задачи. Свежий субагент, ДРУГИМ методом (идемпотентность по SHA-256 байтов файла: то же фото дважды не задваивает отметки; отказ модели приходит как HTTP 200 и обязан быть распознан; 429 без retry-after не уходит в вечный ретрай), не перечитывает свою же правку. Доля сплошной выборки: 3 класса отказа × 2 повтора = 6 проверок, задвоений 0. Финальная строка ответа обязательна дословно: «выдано N позиций из M найденных» — без неё ответ считается усечённым и в отчёт не вставляется.

## 4. 🔴 КОММИТ СВОЕЙ ЗОНЫ — ПО ХОДУ РАБОТЫ, НЕ ОДНИМ ПОСЛЕДНИМ ХОДОМ
Ты работаешь host-side и в `.git` ПИШЕШЬ — значит коммитишь САМ, никому не передавая. Каждую завершённую часть работы коммить СРАЗУ, теми же двумя ходами — не копи всё к финальному ходу:
```
git --no-optional-locks add -- core/services/raspoznavanie.py infra/llm.py bot/routers/photo.py tools/blank.py tests/photo/                     # вводит НОВЫЕ пути в индекс
git --no-optional-locks commit -m "<что сделано>" -- core/services/raspoznavanie.py infra/llm.py bot/routers/photo.py tools/blank.py tests/photo/   # отсекает всё чужое
python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone "core/services/raspoznavanie.py" && \
    git_zona.py check --zone "infra/llm.py" && \
    git_zona.py check --zone "bot/routers/photo.py" && \
    git_zona.py check --zone "tools/blank.py" && \
    git_zona.py check --zone "tests/photo/"   # из корня репо; должен быть ✅
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

**ЗОНА ГИГИЕНЫ:** `core/services/raspoznavanie.py` `infra/llm.py` `bot/routers/photo.py` `tools/blank.py` `tests/photo/`

- **Г1. Зона доехала в git.** `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone core/services/raspoznavanie.py` → ✅; `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone infra/llm.py` → ✅; `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone bot/routers/photo.py` → ✅; `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone tools/blank.py` → ✅; `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone tests/photo/` → ✅. Красное на любой из команд — отчёт не принимается: приёмка гоняет их все первым ходом.
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
python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py vlit-v-osnovnuyu zahod/P7-foto --zone "core/services/raspoznavanie.py" --zone "infra/llm.py" --zone "bot/routers/photo.py" --zone "tools/blank.py" --zone "tests/photo/" \
    --vsyo-ravno "своя рабочая папка ещё жива — влитие последним ходом захода, штатно"
```
Конфликт — ЗАКОННЫЙ исход, не повод форсировать: разрешай по существу, если понимаешь обе
стороны; не понимаешь — `git_zona.py vlit-v-osnovnuyu --abort`, ветка остаётся невлитой,
строка в отчёт и заявка на влитие (`git_zona.py zayavka --rod git-operaciya`).
🔴 Конфликт на `README.md` — только ОБЪЕДИНЕНИЕМ записей реестра, никогда выбором стороны:
параллельные заходы волны дописали по строке — обе записи правы, выбор одной молча уничтожает
регистрацию соседа.

**3 · ПОСТ-ПРОВЕРКА ИЗ ГЛАВНОЙ ПАПКИ.** Отвечает на вопрос «механизм ВСТАЛ», а не «коммит
виден»: прогон изменённого механизма из `/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot`, НЕ из рабочей папки `/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot-wt/P7-foto` плюс `grep` по ЖИВОМУ файлу,
который его зовёт (хук, конвейер, генератор):
```
cd /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot && make check && python3 -m pytest tests/photo -q && echo $?
grep -c 'thinking_level' infra/llm.py   # minimum, а не по умолчанию
grep -c 'sha256' core/services/raspoznavanie.py   # идемпотентность по байтам файла
grep -c 'INTER_AREA' core/services/raspoznavanie.py   # даунскейл, апскейла быть не должно
grep -c 'upscale\|resize.*up' core/services/raspoznavanie.py   # должно быть 0
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

**Entry state, measured first move.** `git rev-parse --abbrev-ref HEAD` -> `zahod/P7-foto`;
`git status --porcelain | wc -l` -> 0; `git branch --no-merged main | grep -c zahod/` -> 0.
The branch was **29 commits behind `main`**: P4's grid (`bot/routers/marking.py`,
`bot/keyboards/grid.py`, `bot/callbacks.py`), P12's enrollment and P13 were all merged into
`main` AFTER this worktree's branch was cut, so §8's "P4's existing marking path" did not
exist on this disk.  First move was therefore `git merge --ff-only main` (a strict
fast-forward, `main..HEAD` = 0, no merge commit, nothing to conflict).  Baseline after the
fast-forward: `make check` rc=0, **221 passed**.

**Objection to nothing in the criterion.**  The КРИТЕРИЙ ГОТОВНОСТИ is falsifiable as
written and I take it as it stands.  One correction to a premise, stated before the work
rather than discovered in the report: the зона names `bot/routers/photo.py`, and a router
in `bot/routers/` is dead until `bot/app.build` includes it — but `bot/app.py` is OUTSIDE
the зона and the контракт зоны forbids touching it.  I keep the зона: `photo.py` ships
P4's `build_routers()` factory shape, `tests/photo/` proves it end-to-end through a REAL
`Dispatcher` built by `bot.app.build` plus the two include lines applied in the fixture,
and the exact two-line diff `bot/app.py` needs is filed as a queue item in `## ВОПРОСЫ`
rather than applied from here.

**Assumptions stated before writing code, not guessed silently.**
1. *No new table, and therefore no migration.*  §8 asks for "a confirmed-drafts table";
   `migrations/` is outside the зона, and a schema change cannot be smuggled in.  It is
   not needed: `migrations/001_init.sql:133` already carries
   `create unique index marks_idempotency on marks (idempotency_key)`, and
   `MarkingService.set_state` already answers a repeated key from the journal instead of
   writing.  A per-cell key `foto:<sha256-of-bytes>:<student_id>:<problem_id>` therefore
   IS the confirmed-drafts table, with the same "zero rows affected -> already recorded,
   exit" semantics, surviving both a process restart and a re-delivered update.
2. *`rapidfuzz` is not installed on this machine* (checked, `ModuleNotFoundError`), and
   `make check` must not grow a dependency it cannot import.  §6 asks for
   `rapidfuzz.fuzz.ratio` and explicitly NOT `token_set_ratio`.  `fuzz.ratio` is the
   normalised indel similarity `200*LCS/(len(a)+len(b))`; the code uses `rapidfuzz` when
   importable and otherwise computes that exact metric locally.  A test pins the two
   against the §6 example «Иванов И.» vs «Иванов» — the containment case that
   `token_set_ratio` returns 100 on and `ratio` must not.
3. *`cv2` is imported lazily.*  It is installed here, but a hard import at module scope
   would make `pytest` fail to COLLECT on a machine without it.

**Parts, in order, each its own commit.**
1. **§1 · `tools/blank.py`** — the form carries CODES (`u17`), never surnames; `--proba`
   prints how many codes and tasks fit and that surnames on it are 0.
2. **§2–§3 · `core/services/raspoznavanie.py`, intake and preprocessing** — the 20 MB
   `getFile` ceiling; EXIF orientation honoured; downscale to 1568 with `INTER_AREA`;
   JPEG q90; geometry and tone AFTER the resize.  What the benchmark forbids —
   binarise, greyscale, denoise, equalise and above all UPSCALE (up to 34 pp) — is
   refused by a named guard, not by an absence.  No per-row slicing (CER 64 vs 1,21).
3. **§4–§5, §7 · `infra/llm.py`** — the closed list as TWO enums (student codes, task
   labels) because ~120 is Gemini's practical ceiling and 56+45 = 101; `raw_text` FIRST
   and REQUIRED; `temperature=0`, `thinking_level=minimum`, resolution high; timeout
   30–60 s; the markdown fence stripped BEFORE parsing; the stop reason checked BEFORE
   the JSON is touched; 429 without `retry-after` distinguished by error text and NOT
   retried forever.
4. **§6 · own confidence, in `core/services/raspoznavanie.py`** — surnames expanded over
   Russian cases, indel ratio against `raw_text`, threshold 0,7; disagreement between the
   model's pick and the fuzzy match IS the signal «doubtful»; ambiguity returns `UNKNOWN`
   with `alternatives`.
5. **§8 · `bot/routers/photo.py`** — the WHOLE parsed table as «ученик × галочки», a tap
   toggles one cell, and NOTHING reaches the journal until «Подтвердить».  The write goes
   through P4's `MarkingService`, with `source="фото"`.
6. **`tests/photo/`** — the six failure checks (3 classes × 2 repeats), the named fence
   test, idempotency by byte hash, and the negative control that the failure tests can
   actually go red.

**Verifier §3** runs last, fresh subagent, by the other method.

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
**КОММИТ:** `<хэш>` — `<сообщение>` · `git_zona.py check --zone "core/services/raspoznavanie.py" && \
    git_zona.py check --zone "infra/llm.py" && \
    git_zona.py check --zone "bot/routers/photo.py" && \
    git_zona.py check --zone "tools/blank.py" && \
    git_zona.py check --zone "tests/photo/"` → ✅
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

**ВЕТКА РАБОТЫ:** `zahod/P7-foto`
*(проверяется фактом, не словом: ветка обязана существовать и быть либо ВЛИТА в основную, либо названа в открытой заявке на влитие. Ни того, ни другого — Г14 краснеет. Снять состояние: `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py poteri --branch <ветка>`)*

**ЗАЯВКИ, ПОСТАВЛЕННЫЕ ЭТОЙ ПРИЁМКОЙ — ПРОДУБЛИРУЙ СЮДА ТО, ЧТО УЖЕ ЛЕЖИТ В СПИСКЕ:**
> Адрес списка: `/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/zhurnal/_INFRA-git/zayavki`
> Читается командой (из любой папки, в том числе из worktree): `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py zayavki`
> Ставится командой: `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py zayavka --rod <git-operaciya|pravka-koda> "<текст>"`
> 🔴 Вопрос здесь НЕ «что ты хочешь сделать», а «что ты УЖЕ положил в очередь». Дубль сверяется с очередью по id машинно; намерение сверить не с чем.

- `<id заявки>` — `<род>` — `<суть одной строкой: влитие / коммит / вывоз / деплой / гашение>`

*(Заявок эта приёмка не ставила — так и напиши строкой «заявок нет: <почему ни одна из пяти операций не понадобилась>». Пустая строка и прочерк не принимаются: молчание неотличимо от «забыл».)*
