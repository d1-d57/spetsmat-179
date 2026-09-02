# Канал исполнителя — P12-gruppy (один заход до конца)
> Твой единственный файл-заход. Читай ТОЛЬКО его и названные якоря; проект не изучай.
<!-- собран bootstrap_zahod.py -->
> План/вопросы/отчёт — в секции внизу. Метрика — КАЧЕСТВО. Часы — норма.
> **Модель: Opus 5** — закрепления с интервалами — место, где переназначение легко переписывает прошлое; цена ошибки высокая и всплывёт только через месяц, когда состав аудитории поменяется.

## СТАРТОВОЕ СООБЩЕНИЕ ВЛАДЕЛЬЦУ

> Это блок для владельца — то, чем тебя запустили. Исполнителю здесь делать нечего, твоё задание ниже.

```
bash /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/zhurnal/2026-09-02_spetsmat-bot/ZAPUSK-ZAHODA.sh P12-gruppy opus
```
🔴 **ЧЕМ ЭТА СТРОКА ОТЛИЧАЕТСЯ ОТ ТОЙ, ЧТО ПЕЧАТАЛ ГЕНЕРАТОР.**
Генератор вписал `claude -p --model arn:aws:bedrock:…` — ARN application inference
profile. На ЭТОЙ машине Bedrock-доступа НЕТ вовсе: ни `~/.aws/`, ни переменных `AWS_*`
(замер 2026-09-02 08:22). Цена оплачена соседней волной 2026-09-02 07:07: пять платных
позиций из пяти оборвались за девять минут с «Could not load credentials from any
providers», и снаружи это неотличимо от «заход думает». `ZAPUSK-ZAHODA.sh` берёт модель
вторым аргументом и сам выбирает маршрут; добор — тем же вызовом с `--dobor`.

<!-- прежняя строка генератора, сохранена дословно, НЕ исполнять:

python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py worktree add P12-gruppy --branch zahod/P12-gruppy && cd /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot-wt/P12-gruppy && claude -p --verbose --output-format stream-json --model arn:aws:bedrock:us-east-1:811345154057:application-inference-profile/d78ovu0ye0t4 --dangerously-skip-permissions 'Твой заход — файл /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/zhurnal/2026-09-02_spetsmat-bot/kod_P12-gruppy.md. Прочитай ТОЛЬКО его и то, что он называет; остальной проект не изучай. План/вопросы/отчёт пиши в этот же файл внизу (## ПЛАН / ## ВОПРОСЫ / ## ОТЧЁТ). Ничего сверх задачи не трогай — «ничего сверх задачи» относится к СОДЕРЖАНИЮ работы; git-контур §0.1 — законное исключение, он про состояние репозитория и исполняется целиком.' < /dev/null 2>&1 | tee /tmp/zahod-P12-gruppy.jsonl | python3 -u -c 'import sys,json
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
   print("  %s: вх %s вых %s USD %s" % (m, v.get("inputTokens"), v.get("outputTokens"), v.get("costUSD")))' /tmp/zahod-P12-gruppy.jsonl
```

── СЧЁТ НЕЗАКРЫТОГО (печать, не гейт) ──
ГРАНИЦА ОБЛАСТИ: сырые подстроки в `kod_*.md` (пункт 4) — НЕ парсер очереди `dostavit_urok` (который считает только пары ДОМ:/ДОСТАВЛЕНО:). Разница в числах — законна.
🔴 снимок при сборке 2026-09-02, ПРОВЕРЬ ПЕРВЫМ ХОДОМ: `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/schet_nezakrytogo.py zhurnal/2026-09-02_spetsmat-bot`
Область: «zhurnal/2026-09-02_spetsmat-bot» — сужены пункты 1, 3, 4; долги (2) глобальны намеренно (DOLG.md не размечен по записям).
Приоритет владельца: разобрать инциденты важнее, потом закрыть долги — неразобранный инцидент это повторяющаяся ошибка, долг может подождать.
  1. инцидентов без вердикта             : н/д — VERDIKTY.md/INCIDENTY.md не найдены
  2. долгов СТАТУС: ЖИВ                  : н/д — /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/skills/slajdy/DOLG.md недоступен (другой git-репозиторий)
  3. уроков фабрике без ВЕРДИКТ          : 6
  4. пунктов очереди «ДОСТАВЛЕНО: нет»   : 16
     из них разбором очереди (парсер `dostavit_urok`, записи с парой ДОМ:/ДОСТАВЛЕНО:): 3
       живых (чинится доставкой — «дом есть»)  : 0
       к владельцу (решение за человеком)      : 1
       адрес недоступен (нет/папка/код/указат.) : 0
       адрес не разобран                        : 0
       отработавших (машинный след закрытия)    : 0
       доставлено                               : 2
       🔴 не проверяется машиной: содержательная отработанность записей БЕЗ следа закрытия (метки в доме, строки ✅/ЗАКРЫТО) — нужна ревизия человеком; сырой греп сверх разбора — шаблонные строки формы.

КОНТЕКСТ. `spetsmat-bot` — телеграм-бот кондуита спецмата 179-й школы: 56 учеников,
18 преподавателей, три аудитории (203, 302, 303 — примерно по шесть преподавателей в
каждой), два занятия в неделю. Прошлый этап: P1 (ядро) принята и влита — в схеме УЖЕ
есть таблица `enrollment(student_id, teacher_id, room, valid_from, valid_to)` как SCD
Type 2 с полуоткрытыми интервалами, `9999-12-31` вместо NULL, частичный уникальный
индекс на открытую строку и триггеры против перекрытия; модель `Enrollment` в
`core/models.py` тоже есть. Логики над ней нет ни строки. P2 (импорт) и P3
(регистрация и три роли) приняты и влиты.
ЦЕЛЬ: закрепление ученика за преподавателем, зависящее от ДНЯ ЗАНЯТИЙ, и перевод
ученика, который не переписывает прошлое.
Приёмка — по ОТЧЁТУ, без построчной сверки. Если стоп до цели: получишь сервис
закреплений с тестами, но НЕ экран аудитории (P13) — он встанет поверх тебя.

## ЧТО ФИНАЛИЗИРОВАНО НА ИНТЕРВЬЮ

ИНТЕРВЬЮ ПРОВЕДЕНО: да (2026-09-02) — флаг `--intervyu da` при сборке. ⚠ Он доказывает, что аналитик не ЗАБЫЛ про интервью, и НЕ доказывает, что разговор был.

1. преподаватель закреплён за группой ЖЁСТКО на весь год и никогда не двигается; ученики иногда переходят
2. закрепление ПОДНЁВНОЕ: часть преподавателей приходит раз в неделю, и один ученик может иметь разных преподавателей в понедельник и в четверг
3. перевод ученика НЕ переписывает историю: кто принимал в октябре, остаётся собой

## КОНТРАКТ ЗОНЫ (обязателен — не удалять; вписан Cowork)
- **МЕСТО РАБОТЫ:** **рабочая папка `/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot-wt/P12-gruppy`** — ТОЛЬКО ДЛЯ КОДА (worktree захода, ветка `zahod/P12-gruppy` в ней уже стоит). 🔴 **ДАЛЬШЕ — ТОЛЬКО ПУТИ ОТНОСИТЕЛЬНО ЭТОЙ ПАПКИ** (или `cd` в неё безусловно, каждым ходом): абсолютный путь в главную папку репозитория здесь — типичная ошибка, правка утекает МИМО worktree и найдётся только на коммите («вне git» в `git_zona.py check --zone` из рабочей папки, на файле, который уже правил, — цена, оплаченная живьём: 5 файлов, ручное копирование и откат главной папки). 🔴 `git checkout` в основной папке ЗАПРЕЩЁН: рядом идут другие заходы, переключение подменит файлы у них под ногами. 🔴 **Сам файл-заход (этот `.md`) при этом остаётся в ОСНОВНОЙ папке репозитория** — один экземпляр, не копия в рабочей папке: ПЛАН/ВОПРОСЫ/ОТЧЁТ/УРОКИ пишешь в него по абсолютному пути, названному в стартовой строке, а сам файл НЕ коммитишь — это делает аналитик при приёмке (цена обратного правила — полсуток 03.08: отчёт писали в рабочую папку, владелец и приёмка её не видели, приёмка трижды объявила отчёт пустым). 🔴 **Ветку в конце вливаешь САМ, последним ходом, после коммита зоны** (решение владельца 25.08; полный порядок печатает WARNING-блок ниже).
- **ЗОНА (можно менять):** `core/services/enrollment.py` `infra/enrollment_repo.py` `tests/enrollment/`. Всё вне — **READ-ONLY**: не править, не двигать, не удалять, не рефакторить «заодно».
- 🔴 **ЗАВЁЛ НОВЫЙ `.md` — РЕГИСТРИРУЕШЬ ЕГО САМ, ТЕМ ЖЕ ХОДОМ, ОДНОЙ КОМАНДОЙ:** `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/register_doc.py <путь> "<описание>"` (из корня репо). `_studio/docs/` тебе по-прежнему READ-ONLY **для правки руками** — дверь ровно одна, и это она. Дверь идемпотентна (повторный вызов дубля не заведёт) и отказывает на пути вне `_studio/`, на несуществующем файле и на пустом описании. Свой файл-заход регистрировать не нужно: он рождается зарегистрированным из `bootstrap_zahod.py`. **Красный хук на ТВОЁМ новом `.md` — это не повод для `--no-verify`, а повод позвать дверь.** *Почему правило существует и почему оно теперь исполнимо: 26.07 оно записано с ценой в пять документов-сирот и через два дня повторилось дословно. Дальше стало хуже: до 30.07 указания «зарегистрируй» и «`docs/` только на чтение» противоречили друг другу, выход был ровно один — обойти хук, и по автологу `_INFRA-git/INCIDENTY.md` это 28 обходов `--no-verify` из 56 срывов коммита, 27 из них по одной этой причине (48 % всей боли с коммитами, тринадцать исполнителей подряд). Обходить больше нечего.*
- **КОММИТ:** два хода — `add` по своим путям, затем `commit` **с теми же путями после `--`** (полная форма и цена каждого хода — §4); коммить ПО ХОДУ работы, не одним последним ходом (§4). НИКОГДА `-A` / `.` / `commit -am`, и никогда `commit` без путей. Субагенты не коммитят. **`--no-optional-locks` обязателен:** обычный git переписывает индекс, берёт `.git/index.lock` и роняет параллельный ручной коммит владельца.
- **SCRATCHPAD — ТОЛЬКО ЛИЧНЫЙ.** Черновики, выкладки, промежуточные версии — в личную папку СВОЕГО захода `scratchpad/P12-gruppy/`. Общие пути (`scratchpad/otchet.md`, любой `scratchpad/*` без имени твоей темы) ЗАПРЕЩЕНЫ: чужой отчёт уедет в твой файл или твой — в чужой, а приёмка читает отчёт без построчной сверки и подмену НЕ ЛОВИТ по построению. *Цена 25.08: готовый `## ОТЧЁТ` захода konvejer-incidentov был записан в общий `scratchpad/otchet.md`, и 92 строки чужого отчёта простояли в `kod_slovari-v-kod.md`.*
- 🔴 **Звал `register_doc.py` — допиши `_studio/docs/KARTA.md` к своим путям В ОБОИХ ходах.** Строка регистрации лежит физически в нём. Ворота 5 читают `§6` **с диска**, а не из индекса: коммит без этого файла пройдёт ЗЕЛЁНЫМ, документ уедет сиротой, а строка умрёт при первом `checkout` (дата данных 2026-07-30, найдено верификацией захода «kod_registracia-bez-obhoda.md»).
- **ЗАПРЕТ:** ничего за пределами зоны, даже если «мешает» или «чинится в одну строку». Нашёл проблему вне зоны → в отчёт, не трогай.

## 0. ПЕРВЫЙ ХОД
### 0.1 🔴 ГИТ-КОНТУР — ДО ВСЕГО ОСТАЛЬНОГО, И ПЕРВЫМ ХОДОМ ЦЕЛИКОМ

🔴 «ничего сверх задачи» относится к СОДЕРЖАНИЮ работы; git-контур §0.1 — законное исключение, он про состояние репозитория и исполняется целиком.

🔴 **ПОРЯДОК ЗДЕСЬ — ЧАСТЬ УСТРОЙСТВА, А НЕ ОФОРМЛЕНИЕ. Сначала субагент вливает названные через `--vlit` ЧУЖИЕ ветки В ОСНОВНУЮ, и только ПОТОМ ты заводишь свою рабочую папку; СВОЮ ветку он не трогает никогда — её вливаешь ты сам последним ходом (граница прав ниже).** Пока влитие шло в ветку захода, а влитие в основную было ходом приёмки (которая из песочницы в `.git` писать не может), работа копилась лестницей в последней ветке цепочки, а основная не получала ничего — замер 14.08: 14 невлитых веток, цепочка из пяти внутри последней, 84 невывезенных коммита, и генератор в основной папке не знал о собственных улучшениях. Заводя ветку ПОСЛЕ влития, ты отпочковываешь её от основной, которая уже всё содержит: инструмент оказывается на диске сам, дотаскивать нечего.

**1. ВЕСЬ КОНТУР — В СУБАГЕНТА, ОДНИМ ХОДОМ, ДО СВОЕЙ ПАПКИ.** Очередь заявок, влитие названных веток в ОСНОВНУЮ, что забрать в git по ходу и что погасить после — на содержание твоей задачи не влияют. Запусти ОДНОГО субагента, дождись его и вставь его шесть строк в `## ОТЧЁТ` дословно; сам эти пункты не исполняй. 🔴 ПОРЯДОК ПРИ ПАДЕНИИ ЭТОГО ВЫЗОВА — исполняй, не изобретай (движок роняет `network_error` на вызове субагента и уносит с собой ВЕСЬ заход, замер волны 3A — 4 захода из 13). Пауза 45 секунд, до трёх попыток; время меряй `date`, не суммой своих `sleep`. После третьей — работай БЕЗ субагента: контур остаётся неразобранным, и это ОТДЕЛЬНАЯ строка в `## ОТЧЁТ`, а не молчание. У него ОТДЕЛЬНЫЕ ПРАВА, объявленные в его же промпте: главная папка, основная ветка, вывоз — и ничего сверх; зону захода он не коммитит, её коммитишь ты сам, по ходу работы (§4). 🔴 ОТВЕТ ЛЮБОГО субагента, которого ты запускаешь (не только этого), обязан КОНЧАТЬСЯ строкой «выдано N позиций из M найденных»: канал мог оборвать его молча, и без этой строки усечение неотличимо от честного «мало нашлось». Нет строки — ответ усечён, в `## ОТЧЁТ` не вставляй, перезапроси. Полный текст задания печатает команда:
```
python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/bootstrap_zahod.py --zadanie-subagentu --zone core/services/enrollment.py --zone infra/enrollment_repo.py --zone tests/enrollment/ --kommitit 'core/services/enrollment.py, infra/enrollment_repo.py, tests/enrollment/' --zakryt 'влить ветку zahod/P12-gruppy в main последним ходом, после коммита зоны'
```

🔴 ГРАНИЦА ПРАВ, ЧЕТЫРЕ ОТВЕТА (та же, что в самом задании субагенту — одно место в тексте, а не пересказ): **кто вливает ЧУЖИЕ названные (`--vlit`) ветки** — субагент, в ОСНОВНУЮ ветку, до заведения твоей папки; **кто вливает СВОЮ ветку этого захода** — ты сам, последним ходом, после коммита зоны (`git_zona.py vlit-v-osnovnuyu`; решение владельца 25.08 — оно сняло противоречие волны 4, когда машинное §0.1 и текстовое «ветку НЕ вливать» спорили молча, и машинное побеждало); **кто закрывает заявки** — субагент, `zayavka-zakryt`; **кто коммитит пути ВНЕ зоны захода** — субагент (хвост Cowork и что назовёт пункт 3 его задания). Ты коммитишь ТОЛЬКО зону этого захода, по ходу работы (§4). 🔴 Конфликт на `README.md` при ЛЮБОМ слиянии разрешается ОБЪЕДИНЕНИЕМ записей реестра, НИКОГДА выбором стороны: параллельные заходы волны дописали в реестр по строке — обе записи правы, выбор одной молча уничтожает регистрацию соседа.

**2. ТЕПЕРЬ ЗАВОДИ СВОЮ РАБОЧУЮ ПАПКУ** (команда — в блоке «МЕСТО РАБОТЫ» выше) и работай в ней как обычно. Её ветка отпочкована от свежей основной, поэтому инструмент, которым ты работаешь, уже на диске — отдельного «влить перед работой» больше нет.

вливать нечего, проверено командой `git branch --no-merged` — но проверено ПРИ СБОРКЕ, а не сейчас: невлитых `zahod/*`-веток было 0. 🔴 снимок при сборке 2026-09-02, ПРОВЕРЬ ПЕРВЫМ ХОДОМ: `git --no-optional-locks branch --no-merged main | grep -c 'zahod/'`. Число могло устареть между сборкой и твоим прогоном — 14.08 заход нёс ровно этот ноль, а к прогону невлитых было три.


- деплоя в этом заходе нет.

- `cd /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot-wt/P12-gruppy` — рабочая папка ДЛЯ КОДА. Ветку НЕ переключай: `zahod/P12-gruppy` в ней уже стоит.
- Проверить, что на месте: `git rev-parse --abbrev-ref HEAD` → должно быть `zahod/P12-gruppy`.
- ПЛАН/ВОПРОСЫ/ОТЧЁТ/УРОКИ ФАБРИКЕ пиши в ЭТОТ файл — он в основной папке, не копируй его в рабочую.
- Точка отката: `git add core/services/enrollment.py infra/enrollment_repo.py tests/enrollment/` → commit (или zip), если зона не чиста в HEAD (не фабрикуй, если чиста).
- Прочитать ТОЛЬКО: `названные файлы-якоря`. Проект не изучай.
- ПЛАН — в `## ПЛАН` перед действиями.

## 1. ДИСЦИПЛИНА (Карпатов)
🔴 **Код возврата — ПЕРВЫМ, до содержательного вывода команды.** «Отработала» и «упала, а я читаю прошлое состояние» выглядят одинаково; сначала `echo $?`, потом выводы. То же с гейтами. *Цена 21.07: `rc=128` (сбой прав окружения) четырежды прочитан как результат — едва не откатили верное правило по ложным данным.*
Предпосылки/развилки назвать вслух; минимум без спекуляций; хирургия (строка → к заданию); критерий, который может провалиться. Якорные замены — abort при ≠1. Сохранять по умолчанию. **Оспорить ложную предпосылку — включая КРИТЕРИЙ ГОТОВНОСТИ: считаешь его кривым — скажи в `## ПЛАН`, ДО работы, и предложи поправку.** Субагенты: ≤5, рейт-лимит = отступить + доложить (не слепой ретрай).

🔴 **Пишешь содержательный текст — термин НЕ употребляется раньше, чем определён**, включая заголовки, подводки и формулировки теорем. «Определение в тексте есть» не считается: если оно ниже первого рабочего употребления, читатель встаёт ровно там. Чинится ПЕРЕСТАНОВКОЙ определения вверх, не дописыванием пояснения. Гейт: `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/check_termin.py <src>` (exit 1 при нарушении). Канон — `../docs/kak-delat/STANDART-teksta.md` правило 11. *Цена 30.07: теорема пользовалась словом «ординал», определение стояло строкой ниже; поймал владелец, ни один гейт не увидел, раздел переписан дважды.*

## 2. ЗАДАЧА

🔴 **WRITE YOUR `## ОТЧЁТ`, `## ПЛАН` AND `## ВОПРОСЫ` IN ENGLISH, AND EVERY FILE AND EVERY COMMIT MESSAGE YOU PRODUCE TOO.** Owner's decision 30.08. It is a каркас-level rule, not a preference — wave 2 lost it twice because the pass text listed the report SECTIONS and never said «every file you create». Fixed Russian addresses stay Cyrillic: `ЦЕНА:` · `ВЕРДИКТ:` · `ДОМ:` · `ДОСТАВЛЕНО:` · `ПОДЪЁМ:` · `[ДОЛГ: …]` · every `## ` heading of this file · every path and command.
You build enrollment: who works with whom, on which day, in which room — and how that changes
during the year without rewriting the past. `core/` only, no aiogram, no screens.

### 0 · Read first, do NOT rebuild and do NOT edit

- `migrations/001_init.sql` — `enrollment` ALREADY EXISTS with `valid_from` / `valid_to`,
  `OPEN_END_DATE = "9999-12-31"`, a partial unique index on the open row and overlap triggers.
  **Do not write a migration** — migrations are outside your zone. Something genuinely missing →
  `## ВОПРОСЫ`, not a new migration.
- `core/models.py` — `Enrollment`. `core/ports.py`, `infra/repositories.py`, `config.py` —
  **shared, read-only to you.** Your port lives in `core/services/enrollment.py`, your adapter in
  `infra/enrollment_repo.py`.
- `config.py` — `OPEN_END_DATE`, `WEEKDAY_MIN`, `WEEKDAY_MAX`. Every constant lives there.

### 1 · 🔴 THE ASSIGNMENT IS PER LESSON DAY — this is the whole reason the position is paid

Some teachers come only once a week. **The same student may have one teacher on Monday and
another on Thursday.** This is not a hypothesis: it is in the owner's 2025 tool, where
`kakhiani = vanya on mon, yan on thu`.

So the resolution query is `(student, date) → teacher`, and the day of week is part of the key,
not a filter applied afterwards. An `enrollment` row that does not say which weekday it covers
cannot express the case at all — decide HOW you express it and say why in the report. Whatever
you choose, `valid_from` / `valid_to` must keep their meaning: the interval is WHEN the
arrangement held, the weekday is WHICH DAY it covers inside that interval.

**A teacher is bound to a group HARD for the whole year and never moves. Students move
occasionally.** So the mutable side is the student's row, and a teacher's group is a fixed point
the year is built around — do not build machinery for moving teachers.

### 2 · 🔴 MOVING A STUDENT MUST NOT REWRITE HISTORY

This is the defect that made this position exist: an assignment stored as a CURRENT VALUE means
reassignment silently rewrites who worked with whom in October.

- Moving = closing the open interval (`valid_to` = the day before) and opening a new one. Never
  an `UPDATE` of `teacher_id` on the existing row.
- **The test that IS this position:** take a student with marks made in October by teacher A;
  move him to teacher B in December; then ask again who received the October marks. The answer
  must still be A. If it comes back B, the position has failed regardless of everything else.
- Half-open intervals, `9999-12-31` instead of NULL — with NULL the index breaks and every query
  grows an error. The schema already enforces this; your service must not fight it.
- Overlap is refused by the schema's trigger. Prove the refusal with a test, do not assume it.

### 3 · Rooms and their heads

Three rooms: 203 (senior — initials НС), 302 (ДМ, Даня), 303 (ИЯ, Ваня). The room is part of the
enrollment row, because "who worked with him" and "where he sat" are the same question at a
lesson. ⚠ P2 was closing a hole: the head of 203 was not registered as a teacher anywhere.
Depend on the ROW being resolvable, not on that particular person existing.

### 4 · Two things you may be tempted to do and must not

- **Do not invent a "current teacher" column** anywhere. The current teacher is a QUERY over
  intervals, not stored state. A stored copy is the exact bug this position removes.
- **Do not build the room screen.** That is P13, it stands on you.

### 5 · Data you can test against — last year, and it is small on purpose

Movement of the roster over the whole year was exactly two people, both 9К: **Гамаюнова Софья**
left after sheet 6, **Пирогов Константин** arrived from sheet 6. Property-based tests, if you
write them, must make the world SMALL — 5 students, 2 teachers, 2 weekdays — because all the bugs
live in collisions and large random ids almost never collide.

**КРИТЕРИЙ ГОТОВНОСТИ (может ПРОВАЛИТЬСЯ), каждая команда печатает ЧИСЛО:**

    cd /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot-wt/P12-gruppy
    make check
        # rc=0; печатает «N passed», N больше того, что было до тебя
    python3 -m pytest tests/enrollment -q
        # rc=0; тест разрешения печатает «разрешено N из M, ошибок 0» —
        # 56 учеников × 2 дня недели = 112 разрешений
    python3 -c "import pathlib,sys; bad=[str(p) for p in pathlib.Path('core').rglob('*.py') if 'aiogram' in p.read_text()]; print('aiogram в core/:', len(bad), bad); sys.exit(1 if bad else 0)"
        # rc=0 и «aiogram в core/: 0 []»

🔴 Ноль разрешений при непустом составе — КРАСНЫЙ, а не зелёный. Отрицательный вердикт обязан
нести охват В СЕБЕ: «ошибок 0, разрешено 112 из 112», а не «ошибок не найдено».
**Отрицательный вердикт несёт ОХВАТ В СЕБЕ:** не «дыр не найдено», а «дыр не найдено, проверено X из Y». Без охвата вердикт не принимается — «проверено 2 из 9» и «проверено 9 из 9» выглядят одинаково.

## 3. ВЕРИФИКАТОР (если двигаем/теряем/жмём)

Верификатор нужен, тип — **ПОСЛЕ-типа** — судит результат, стоит в конце, после задачи. Свежий субагент, ДРУГИМ методом (тест на данных прошлого года: один и тот же ученик разрешается в РАЗНЫХ преподавателей в понедельник и в четверг; перевод ученика не меняет авторов старых отметок), не перечитывает свою же правку. Доля сплошной выборки: 56 учеников × 2 дня недели = 112 разрешений, ошибок 0. Финальная строка ответа обязательна дословно: «выдано N позиций из M найденных» — без неё ответ считается усечённым и в отчёт не вставляется.

## 4. 🔴 КОММИТ СВОЕЙ ЗОНЫ — ПО ХОДУ РАБОТЫ, НЕ ОДНИМ ПОСЛЕДНИМ ХОДОМ
Ты работаешь host-side и в `.git` ПИШЕШЬ — значит коммитишь САМ, никому не передавая. Каждую завершённую часть работы коммить СРАЗУ, теми же двумя ходами — не копи всё к финальному ходу:
```
git --no-optional-locks add -- core/services/enrollment.py infra/enrollment_repo.py tests/enrollment/                     # вводит НОВЫЕ пути в индекс
git --no-optional-locks commit -m "<что сделано>" -- core/services/enrollment.py infra/enrollment_repo.py tests/enrollment/   # отсекает всё чужое
python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone "core/services/enrollment.py" && \
    git_zona.py check --zone "infra/enrollment_repo.py" && \
    git_zona.py check --zone "tests/enrollment/"   # из корня репо; должен быть ✅
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

**ЗОНА ГИГИЕНЫ:** `core/services/enrollment.py` `infra/enrollment_repo.py` `tests/enrollment/`

- **Г1. Зона доехала в git.** `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone core/services/enrollment.py` → ✅; `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone infra/enrollment_repo.py` → ✅; `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone tests/enrollment/` → ✅. Красное на любой из команд — отчёт не принимается: приёмка гоняет их все первым ходом.
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
python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py vlit-v-osnovnuyu zahod/P12-gruppy --zone "core/services/enrollment.py" --zone "infra/enrollment_repo.py" --zone "tests/enrollment/" \
    --vsyo-ravno "своя рабочая папка ещё жива — влитие последним ходом захода, штатно"
```
Конфликт — ЗАКОННЫЙ исход, не повод форсировать: разрешай по существу, если понимаешь обе
стороны; не понимаешь — `git_zona.py vlit-v-osnovnuyu --abort`, ветка остаётся невлитой,
строка в отчёт и заявка на влитие (`git_zona.py zayavka --rod git-operaciya`).
🔴 Конфликт на `README.md` — только ОБЪЕДИНЕНИЕМ записей реестра, никогда выбором стороны:
параллельные заходы волны дописали по строке — обе записи правы, выбор одной молча уничтожает
регистрацию соседа.

**3 · ПОСТ-ПРОВЕРКА ИЗ ГЛАВНОЙ ПАПКИ.** Отвечает на вопрос «механизм ВСТАЛ», а не «коммит
виден»: прогон изменённого механизма из `/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot`, НЕ из рабочей папки `/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot-wt/P12-gruppy` плюс `grep` по ЖИВОМУ файлу,
который его зовёт (хук, конвейер, генератор):
```
cd /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot && make check && python3 -m pytest tests/enrollment -q && echo $?
grep -c 'UPDATE' infra/enrollment_repo.py   # перевод НЕ обновляет teacher_id на месте
grep -n 'OPEN_END_DATE' core/services/enrollment.py infra/enrollment_repo.py   # 9999-12-31 константой, не литералом
grep -rn 'weekday\|день недели' core/services/enrollment.py | head -3   # день недели РЕАЛЬНО в ключе
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

**Entry snapshot (§0.1 replacement, run by me on the orchestrator's instruction — the
git-contour subagent was cancelled by the orchestrator, that cancellation overrides the
text of §0.1):**

```
$ git --no-optional-locks branch --no-merged main | grep -c zahod/
0
$ git rev-parse --abbrev-ref HEAD
zahod/P12-gruppy
$ python3 -m pytest -q | tail -1
148 passed in 27.69s
```

### What I read (and nothing else)

`migrations/001_init.sql`, `config.py`, `core/models.py`, `core/ports.py`,
`infra/repositories.py`, `infra/roster_repo.py`, `infra/db.py`, `core/services/marking.py`,
`core/services/roster.py`, `core/services/seeding.py`, `tests/conftest.py`,
`tests/test_enrollment_scd2.py`, `Makefile`, `seed/students.csv`, `seed/teachers.csv`.

### Two premises of the задание I contest BEFORE writing code (§1)

**1. §2 says "closing the open interval (`valid_to` = the day before)". Taken literally
this is wrong and would break the schema's own guard.** The intervals are HALF-OPEN,
`[valid_from, valid_to)` — stated in `001_init.sql`, in `config.OPEN_END_DATE` and proved
by P1's `test_half_open_intervals_touch_without_overlapping`. Under half-open semantics
the clean handover on effective day `D` is `old.valid_to = D` and `new.valid_from = D`;
the old row then covers through `D - 1 day` inclusive, which is what "the day before"
*means* — but writing the literal date `D - 1` into `valid_to` would leave day `D - 1`
uncovered by anybody and is a closed-closed convention the schema does not use.
**I implement `valid_to = effective_from` and say so here rather than silently.**

**2. §1 says an enrollment row "that does not say which weekday it covers cannot express
the case — decide HOW you express it".** That decision is already made and already on
disk: `enrollment.weekday integer not null check (weekday between 1 and 7)`, ISO-8601 with
Monday = 1, and it is part of both guards (`enrollment_one_open_row` is on
`(student_id, weekday)`, the overlap triggers filter on `e.weekday = new.weekday`).
`migrations/` is outside my zone, so there was never a decision left for me to make here —
only the obligation to key the resolution query on the weekday rather than filter by it
afterwards. The report will say exactly this instead of claiming a design choice I did not
have to make.

### The parts, in order — each is its own commit

**Part 1 — `core/services/enrollment.py`** (the domain; no sqlite3, no bot framework).
- `EnrollmentPort` Protocol: the seam. `transaction()`, `open_row`, `rows_valid_on`,
  `insert`, `close`, `history`. `rows_valid_on` is bulk on purpose — the readiness
  criterion resolves 112 pairs and P13 will resolve a whole room at once; 112 single
  queries would be an N+1 baked into the port shape.
- `weekday_of(day)` — the derivation `date → ISO weekday`, one place. This is what makes
  the day of week part of the KEY: `resolve` computes it from the asked-for date and
  passes it into the lookup, never filters rows after the fact.
- `Assignment` result object (teacher_id, room, weekday, valid_from, valid_to) and
  `Resolution` for the "no lesson that day" answer, which is NOT an error.
- `EnrollmentService.assign(...)` — first row for a (student, weekday).
- `EnrollmentService.move(...)` — close the open row at `effective_from`, insert a new
  one from `effective_from`. Both inside ONE `transaction()`. Never writes `teacher_id`
  onto an existing row.
- `EnrollmentService.teacher_on(student, date)` / `resolve_many(students, date)` — the
  resolution query, and the answer to "who received the October marks".
- `history_of(student, weekday=None)`.
- Domain errors: `NotEnrolled`, `AlreadyEnrolled`, `MoveNotForward`, `OverlappingHistory`.

**Part 2 — `infra/enrollment_repo.py`** (the SQLite adapter).
- `SqliteEnrollmentRepo`, styled on `infra/repositories.py`: `begin immediate`
  transaction that joins an outer one, row → `core.models.Enrollment` mapping,
  `_in_clause`-style bulk filter, `config.OPEN_END_DATE` by name and never as a literal.
- The only column it ever writes on an existing row is `valid_to`. `teacher_id` is
  written by `insert` and by nothing else — that is the defect this position exists to
  remove, and I make it structurally impossible rather than promising it.
- Surfaces the schema's `IntegrityError` as `OverlappingHistory` so the bot can print a
  sentence; the schema stays the carrier.

**Part 3 — `tests/enrollment/`.**
- `test_service.py` — the service against a FAKE port (dict), so the domain rules are
  tested without SQLite: move closes and opens, move never rewrites, weekday is in the
  key, refusals.
- `test_repo.py` — the adapter against the real migrated database: the Кахиани case
  (Mon ≠ Thu for one student), the schema's overlap refusal REACHED THROUGH THE SERVICE
  (§2: prove the refusal, do not assume it), the touching handover.
- `test_history_is_not_rewritten.py` — **the test that IS this position**: student marked
  in October by teacher A through the real `MarkingService`, moved to B in December, and
  the October marks still resolve to A. Fails loudly if it comes back B.
- `test_full_roster_resolution.py` — the readiness criterion: seed the real catalogue
  (56 students, 18 teachers from `seed/`), enroll every student on Monday and Thursday,
  resolve all 112 and print `разрешено 112 из 112, ошибок 0`. Zero resolutions against a
  non-empty roster is asserted RED, per the задание.
  *(That one printed string stays Cyrillic: it is the fixed contract string the
  КРИТЕРИЙ ГОТОВНОСТИ greps for. Every other line of every file I write is English.)*

**Part 4 — verifier (§3, ПОСЛЕ-type, fresh subagent, different method), hygiene Г1–Г6,
report, merge of my own branch as the last move.**

### What I will not do
No migration (`migrations/` is read-only to me and the schema already carries everything).
No "current teacher" column anywhere. No room screen — that is P13 and it stands on me.
No edits to `core/ports.py`, `infra/repositories.py`, `config.py`, or any existing test.

## ВОПРОСЫ — (заполняет исполнитель)

1. `git_zona.py check --zone` — the Г1 gate — answers about the MAIN folder on branch `main`, not about the worktree the заход actually works in. Run from the working folder after a legitimate commit, it printed `⚠ зоны ... ещё нет ни на диске, ни в git` and then `✅ работа доехала в git` with rc=0 — a GREEN on a zone that did not exist anywhere. §4 tells the executor to run it after every commit-along-the-way, and until the branch is merged every one of those runs is a meaningless green. It only became a real green after §WARNING step 2. The gate cannot currently tell "committed in my worktree" from "no work at all", and приёмка runs it first.
   ДОМ: zhurnal/2026-09-02_spetsmat-bot/UROKI-FABRIKE.md
   ДОСТАВЛЕНО: нет

2. §2 of this заход says a move closes the interval with "`valid_to` = the day before", while the same §2, `config.OPEN_END_DATE`, `migrations/001_init.sql` and P1's own `test_half_open_intervals_touch_without_overlapping` all require HALF-OPEN intervals, in which the correct value is the effective day itself. Executed literally the phrase leaves one calendar day per handover covered by nobody — and the КРИТЕРИЙ ГОТОВНОСТИ would not catch it, because 112 resolutions on two dates far from any handover stay green. The заход's prose and the schema it points at disagreed, and only the prose was categorical.
   ДОМ: zhurnal/2026-09-02_spetsmat-bot/UROKI-FABRIKE.md
   ДОСТАВЛЕНО: нет

3. §1 says "an `enrollment` row that does not say which weekday it covers cannot express the case at all — decide HOW you express it and say why in the report", but `enrollment.weekday` was already in `migrations/001_init.sql` and `migrations/` is READ-ONLY to this position. The заход asked for a decision it had itself removed the ability to make. The failure mode this creates is specific: an executor who took it at face value would go looking for a way to express the weekday, find the table closed, and either write a migration outside the zone or invent a second expression beside the one already there.
   ДОМ: zhurnal/2026-09-02_spetsmat-bot/UROKI-FABRIKE.md
   ДОСТАВЛЕНО: нет

4. The partial unique index `enrollment_one_open_row` is unreachable on INSERT: SQLite runs the `before insert` trigger first, and two open rows always overlap (both intervals end at the sentinel), so `enrollment_no_overlap_insert` refuses the case before the index is consulted. Measured, not reasoned — `tests/enrollment/test_repo.py::test_two_open_rows_for_one_lesson_day_are_refused` pins the refusal and says which carrier speaks. The index is not thereby decoration (it is the read-time-free half and survives a dropped trigger), but anyone reading the schema will expect its message and never see it. `migrations/` is outside this position's zone, so this is reported, not changed.
   ДОМ: migrations/001_init.sql
   ДОСТАВЛЕНО: нет

5. A foreign-key failure from `infra/enrollment_repo.py` — an unknown `teacher_id` or `student_id` — reaches a `core/` caller as a raw `sqlite3.IntegrityError`. This is deliberate (`_as_overlap` re-raises every integrity error that is not an overlap, so an overlap is never mislabelled, and `tests/enrollment/test_repo.py::test_an_integrity_error_that_is_not_an_overlap_is_not_reported_as_one` pins it), but it is still a driver exception crossing the seam `core/` exists to keep sqlite3 behind. Wrapping it in a `NoSuchPerson` domain error is a caller-facing decision that belongs to whoever builds the screen over this service (P13), and inventing it now would be a message with no reader.
   ДОМ: владелец
   ДОСТАВЛЕНО: нет

6. Last year's ACTUAL per-weekday grouping cannot be recovered from the seed. `seed/teachers.csv` carries one `room` and one `students_count` per teacher; the counts sum to 57 (`students_actual` sums to 51) against 56 students, and there is no column saying which lesson day a teacher came on. So the 112-resolution test builds a round-robin over the REAL 56 students and REAL 17 teachers rather than reproducing the real Monday/Thursday pairs, and the report says so rather than implying real pairs were checked. If the real grouping matters to P13's screen, it has to come from somewhere else — the workbook or the owner.
   ДОМ: владелец
   ДОСТАВЛЕНО: нет
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

**ВСЕ ДОЛГИ ВХОДА ЗАКРЫТЫ:** `да` — заполнено ОРКЕСТРАТОРОМ, а не исполнителем, и вот почему: субагента гит-контура §0.1 отменил оркестратор в промпте запуска (замер соседней волны: четыре захода из десяти умерли ровно на этом вызове), поэтому секцию заполнить было некому. Замена — одна команда, прогнана оркестратором при приёмке: `git --no-optional-locks branch --no-merged main | grep -c zahod/` → **0**. Системная причина закрыта в источнике: промпт запуска (`ZAPUSK-ZAHODA.sh` и `dozapolnit_zahod.py`) теперь ВЕЛИТ заходу заполнить эту строку самому, так что у следующих позиций Г12 краснеть не будет.
*(`нет` законно — но ТОЛЬКО со списком поимённо: что осталось и почему это непроходимо ТВОИМИ
правами (чужая живая рабочая папка, нужно решение владельца, конфликт, обеих сторон которого
не понимаешь). «Сложно» и «не моя тема» причинами не являются. `нет` без списка = красный.)*

## ОТЧЁТ — (заполняет исполнитель)
**АРТЕФАКТ:** `/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/core/services/enrollment.py` — open in an editor; it is the deliverable, with `/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/infra/enrollment_repo.py` beside it and `/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/tests/enrollment/` proving it. Run it with `cd /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot && python3 -m pytest tests/enrollment -q`.
**РОД АРТЕФАКТА:** `исходник`
**КОММИТ:** `45474d7` — `enrollment: refuse the open-end sentinel as a start day — the verifier's three findings, one of which closed a row to the value that means still open` · `git_zona.py check --zone "core/services/enrollment.py" && git_zona.py check --zone "infra/enrollment_repo.py" && git_zona.py check --zone "tests/enrollment/"` → ✅ ✅ ✅ (all rc=0, re-run after the merge; see "the Г1 caveat" below)
Four commits, one per part, each with only its own paths:
- `c2883c0` — `core/services/enrollment.py` (the domain service)
- `bc85dbd` — `infra/enrollment_repo.py` (the SQLite adapter)
- `290c570` — `tests/enrollment/` (six files)
- `45474d7` — the verifier's three findings closed
- `e58bc9a` — `Merge branch 'zahod/P12-gruppy'` into `main`, my own last move

**ПРАВКИ ПРОЧИТАНЫ:** блок `## ПРАВКИ ПОСЛЕ ВЫДАЧИ` пуст (`<правок нет>`) — читать было нечего.

### §0.1 — исполнено по указанию оркестратора, НЕ субагентом

The orchestrator cancelled the §0.1 git-contour subagent outright (four заходы out of ten measured dying on that call) and told me to run one command myself instead. I did, first move, before anything else:

```
$ git --no-optional-locks branch --no-merged main | grep -c zahod/
0
```

The снимок in §0.1 said 0 at assembly time and it was still 0 at my run. The git contour therefore stands UNRESOLVED as a separate item, not as silence: no заявки were read or closed, no foreign branches were merged into `main` by me, and `## ГИГИЕНА ВХОДА` is unfilled because its owner — the subagent — was cancelled. The `## ГИГИЕНА ВХОДА` section carries the Г12 gate; it is empty for that stated reason and not from omission.

### What I did, and why

The position is one service and its store: **who works with whom, on which day, in which room — and how that changes during the year without rewriting the past.**

**`core/services/enrollment.py`** — the domain. `EnrollmentPort` is the seam, and its shape is the load-bearing decision: it offers `insert`, `close(id, valid_to=…)` and reads, and it offers **no way to set `teacher_id` on a row that already exists**. The service above it therefore does not *promise* not to rewrite the past; it *cannot*. `assign` opens the first interval for a (student, lesson day); `move` closes the open one and opens its successor inside one transaction; `end` closes without a successor; `teacher_on(student, day)`, `teacher_at(student, instant)` and `resolve_many(students, day)` are the resolution.

**`infra/enrollment_repo.py`** — the SQLite adapter. The whole file contains exactly one `update` statement and it names exactly one column:

```
$ grep -c 'UPDATE' infra/enrollment_repo.py
0
$ grep -rn 'update .* set' infra/enrollment_repo.py
infra/enrollment_repo.py:193:  "update enrollment set valid_to = ? where id = ?",
$ grep -rn '9999' core/services/enrollment.py infra/enrollment_repo.py tests/enrollment/ | wc -l
0          # the sentinel is only ever config.OPEN_END_DATE, never a literal
```

**HOW THE LESSON DAY IS EXPRESSED, and why there was no choice to make.** §1 asked me to decide how an enrollment row says which weekday it covers. That decision was already on disk and outside my zone: `migrations/001_init.sql` declares `weekday integer not null check (weekday between 1 and 7)`, ISO-8601 with Monday = 1, and both guards are written around it — `enrollment_one_open_row` is unique on `(student_id, weekday)`, and the overlap triggers filter on `e.weekday = new.weekday`. So what was actually left to me was the obligation §1 states next: keep the weekday in the KEY and not in a filter. `teacher_on` takes a DATE, derives the weekday from it in one place (`weekday_of`), and passes it into the lookup; the only SQL that reads intervals is `where weekday = ? and valid_from <= ? and ? < valid_to`. No code path anywhere fetches rows without the weekday and narrows them afterwards — which matters because a lookup that did would find two legal open rows for one student and would have to pick one, a coin toss dressed as an answer. I have written this in `## ВОПРОСЫ` #3 as an input defect of the заход rather than claiming a design decision I did not have to make.

**`valid_to` — WHERE I DEPARTED FROM THE LETTER OF §2, said in `## ПЛАН` before writing code.** §2 says a move closes the interval with "`valid_to` = the day before". Taken literally that is closed-closed arithmetic and it contradicts the half-open convention that the same §2, `config.OPEN_END_DATE`, the schema and P1's own `test_half_open_intervals_touch_without_overlapping` all require. Writing the literal previous date into `valid_to` — which is EXCLUSIVE here and in the triggers — would leave one calendar day per handover covered by nobody. I implemented `valid_to = effective_from`: the outgoing teacher covers through the day before, the incoming one from the day itself, no gap and no overlap. `tests/enrollment/test_service.py::test_the_handover_is_half_open_and_leaves_no_uncovered_day` pins it. `## ВОПРОСЫ` #2 carries this as a factory-level finding, because the readiness criterion could not have caught the literal reading.

### How I checked (each command printed a number)

```
$ make check
191 passed in 23.40s              rc=0     # before me: 148 passed — +43, all mine

$ python3 -m pytest tests/enrollment -q
разрешено 112 из 112, ошибок 0
43 passed in 0.83s                rc=0

$ python3 -c "import pathlib,sys; bad=[str(p) for p in pathlib.Path('core').rglob('*.py') if 'aiogram' in p.read_text()]; print('aiogram в core/:', len(bad), bad); sys.exit(1 if bad else 0)"
aiogram в core/: 0 []             rc=0
```

The 112 is not a synthetic world: `tests/enrollment/test_full_roster_resolution.py` loads the real anonymised catalogue (`seed/students.csv` = 56 students, `seed/teachers.csv` = 18 teachers of whom 17 are people and one is the technical `отсутствует` placeholder), enrolls every student on Monday and on Thursday with a DIFFERENT teacher, and resolves all 112 pairs. The Thursday offset is 7 against 17 teachers — coprime, so all 56 students exercise the "different teacher on the two days" case, not one lucky index. Zero resolutions against a non-empty roster is asserted RED (`assert resolved > 0`), and the verdict carries its denominator by construction.
⚠ The Monday/Thursday pairing is a round-robin over the REAL people, not last year's real grouping — the seed does not record which lesson day a teacher came on. Stated here rather than implied away; `## ВОПРОСЫ` #6.

**The test that IS this position** is `tests/enrollment/test_history_is_not_rewritten.py`: a student is marked on four October Mondays by teacher A through the real `MarkingService`, moved to teacher B effective 1 December, and every October mark is then asked again through `teacher_at(student, mark.valid_at)`. All four still answer A. It carries a negative control — a December lesson must answer B — because a resolution that always returned the first row it found would otherwise have passed. The schema's overlap refusal is proved rather than assumed, against the real migrated database, in `tests/enrollment/test_repo.py`.

### Верификатор (§3) — ПОСЛЕ-типа, свежий субагент, ДРУГИМ методом

It refused to use my tests or pytest as evidence and wrote its own scripts, driving the service and then checking every answer against its OWN raw SQL — where the two disagreed, the service was to be wrong.

- **Claim 1 (per-lesson-day key) — HOLDS.** 112 resolved, 0 errors, 0 disagreements with raw SQL. 56 of 56 students answered a different teacher on Monday than on Thursday. A Wednesday resolves to `None`, not to a coin toss.
- **Claim 2 (a move does not rewrite the past) — HOLDS.** Raw SQL after the move showed two rows, the first with its **id unchanged** and still carrying teacher A. All four October marks still attribute to A, and still do after a *second* move. Sweeping all 40 Mondays of the season: 40 covered, **0 gaps, 0 double-covers**.
- **Claim 3 (coverage) — HOLDS.** On a second clean database: resolved 112 of 112, errors 0, raw-SQL mismatches 0.
- **Coverage of the negative verdict: 249 checks and probes made, 5 items reported.** Its final line was present and verbatim: `выдано 5 позиций из 5 найденных`.

**It found three real defects, all in the open-end-sentinel corner, and I fixed all three** (`45474d7`):
1. `end(effective_from='9999-12-31')` returned an `Enrollment` that read as closed while setting `valid_to` to the value that MEANS still open — a student reported as having left stayed enrolled, **silently**. The worst of the three.
2. `move(effective_from='9999-12-31')` leaked a raw `sqlite3.IntegrityError` across the seam `core/` exists to keep sqlite3 behind.
3. `assign(valid_from='9999-12-31')` leaked the same way.

One guard closes all three: `as_start_day` refuses the sentinel (and anything past it) on every caller-supplied start day, with `tests/enrollment/test_service.py::test_the_open_sentinel_cannot_open_or_close_an_interval` and `test_repo.py::test_the_open_sentinel_is_refused_on_the_real_store_too` pinning it on both the fake and the real store. Verified directly afterwards, because the verifier's own probe records that finding whenever the row is still open and so could not tell my fix from the bug:

```
end(effective_from=sentinel)      EnrollmentError (domain, seam held)
move(effective_from=sentinel)     EnrollmentError (domain, seam held)
assign(valid_from=sentinel)       EnrollmentError (domain, seam held)
enrollment rows after the three refusals: [(1, 1, '2025-09-01', '9999-12-31')]
the student is still with his teacher, unclosed: True
```
(`scratchpad/recheck_sentinel.py`; the verifier's own scripts are `scratchpad/verify_enrollment.py` and `scratchpad/verify_extra.py` under `/private/tmp/claude-501/-Users-ivanyakovlev-Documents-GitHub-spetsmat-bot-wt-P12-gruppy/c598c069-d2d0-4876-a5fe-5c15b4650851/`.)

Its two remaining items were **doubts, not defects**, and I left both, each with a reason: the deliberate foreign-key pass-through (`## ВОПРОСЫ` #5), and the theoretical observation that under `[from, to)` the sentinel day 9999-12-31 is itself covered by nobody — observable only for a weekday-5 enrollment, since 9999-12-31 is a Friday. I judged the second not worth code: the repair would be a special case in the hottest read path of the project, paid every lesson for eight thousand years, to fix a day nobody will resolve.

### Что НЕ трогал

No migration — `migrations/` is read-only to me and the schema already carried everything (§1's "something genuinely missing → `## ВОПРОСЫ`" produced #4, not a migration). No "current teacher" column anywhere; `tests/enrollment/test_history_is_not_rewritten.py::test_who_taught_in_october_is_a_query_and_never_a_stored_column` asserts the absence on both tables rather than leaving it to review. No room screen — that is P13 and it stands on me. Not one line changed in `core/ports.py`, `infra/repositories.py`, `config.py`, `core/models.py`, or any pre-existing test. The merge diff is exactly my 8 new files and nothing else.

### §4.1 ГИГИЕНА — Г1–Г6

- **Г1. Зона доехала в git.** All three ✅, rc=0 each, re-run after the merge.
  🔴 **The Г1 caveat, and it is a finding.** `git_zona.py check --zone` answers about the MAIN folder on branch `main`, not about the worktree the заход works in. Run from my working folder after a real commit it printed `⚠ зоны ... ещё нет ни на диске, ни в git` and then `✅ работа доехала в git`, rc=0 — a GREEN on a zone that existed nowhere it was looking. Every such run before the merge was a meaningless green. The three ✅ above are from AFTER `e58bc9a` and are the real ones. `## ВОПРОСЫ` #1.
- **Г2. Второй репозиторий.** Неприменимо: every zone path is inside `spetsmat-bot`, and the zone never grew past it. Checked, not assumed — the merge diff `31ab856..e58bc9a` lists 8 paths, all under `core/`, `infra/`, `tests/`.
- **Г3. Невлитых веток не прибавилось.** Entry: 0. Exit: **1** — `zahod/P4-setka`. Grew by one, and it is not mine: it is a neighbouring заход of this wave that appeared during my run (it did not exist at my entry snapshot). It is legal and it is not mine to merge — §0.1 gives foreign branches to the subagent, and the subagent was cancelled. My own branch is merged: `git branch --merged main` lists `zahod/P12-gruppy`.
- **Г4. Новый инструмент имеет живую точку вызова.** No new `.py` under `_generator/**` — 0. (`git_zona.py` flagged 4 of my 8 files as "влито, но не встроено"; its heuristic does not recognise pytest fixtures and imports. Measured rather than argued: `core/services/enrollment.py` is imported by `infra/enrollment_repo.py` and by 4 test modules, `infra/enrollment_repo.py` by 4, `tests/enrollment/fakes.py` by all 4 test modules, and `tests/enrollment/conftest.py` is loaded by pytest itself — every one runs on `make check`, which is the readiness criterion. Not a debt.)
- **Г5. Новый `.md` зарегистрирован.** I created no `.md` — `git diff --name-only 31ab856..e58bc9a | grep -c '\.md$'` → **0**. `register_doc.py` was not needed and `_studio/docs/KARTA.md` was not touched.
- **Г6. В коммите нет чужих путей.** Each of the four commits `show --stat` lists only its own zone paths; the merge `e58bc9a` brings exactly the 8 files above.

### §WARNING — полная гит-гигиена последним ходом

**1 · ВСЕ КОММИТЫ.**
```
$ git -C /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot --no-optional-locks status --porcelain
 M README.md
 M zhurnal/2026-09-02_spetsmat-bot/SERDCE-VOLNY-sborka-bota.md
 M zhurnal/_INFRA-git/INCIDENTY.md
?? .commit-plan
$ git -C /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot-wt/P12-gruppy --no-optional-locks status --porcelain
(пусто)
```
**вне git: рабочая папка 0 · главная папка 4, и НИ ОДИН из четырёх не мой содержательно.** `README.md` (+39 lines) and `SERDCE-VOLNY-sborka-bota.md` (+1) are the wave's registry, written by parallel заходы. `.commit-plan` is untracked and dated 08:31, two hours before my run started. `INCIDENTY.md` has 11 new lines of which exactly ONE is my footprint — the `git_zona.py` autolog entry for my own `--vsyo-ravno` merge at 11:20; the other ten belong to other заходы. I left all four: committing `INCIDENTY.md` to capture my one line would sweep ten other заходы' lines into my commit, which is exactly what pathspec commits exist to prevent, and the other three are foreign content (§4: назвать строкой и оставить).
⚠ **My own file-заход is already IN git and I did not put it there.** The analyst's process is committing the main folder live and swept my `## ПЛАН` into `2ba4e62` (98 lines) while I worked. Consistent with the zone contract (the analyst commits this file, not me) — recorded because it means the file was not mine to be dirty.

**2 · ВЛИТИЕ СВОЕЙ ВЕТКИ.** `main` before: `31ab856`. `✅ Влито в main без конфликтов: e58bc9a Merge branch 'zahod/P12-gruppy'`. No conflict, so no `README.md` merge decision arose. Merged with `--vsyo-ravno "своя рабочая папка ещё жива — влитие последним ходом захода, штатно"`, as §WARNING step 2 instructs.

**3 · ПОСТ-ПРОВЕРКА ИЗ ГЛАВНОЙ ПАПКИ** — **ЗЕЛЁНАЯ**, no rollback needed. Run from `/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot`, not from the working folder:
```
$ cd /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot && make check
191 passed in 26.16s        rc=0
$ python3 -m pytest tests/enrollment -q
разрешено 112 из 112, ошибок 0
43 passed in 0.97s          rc=0
$ grep -c 'UPDATE' infra/enrollment_repo.py
0
$ grep -n 'OPEN_END_DATE' core/services/enrollment.py infra/enrollment_repo.py
8 hits, all `config.OPEN_END_DATE`, zero literals
$ grep -rn 'weekday' core/services/enrollment.py | head -3
present from line 9; 61 lines in all
```

**4 · ГАШЕНИЕ.** `git --no-optional-locks branch --no-merged main` → **1**: `zahod/P4-setka`, named above in Г3 — a live neighbouring заход of this wave, not mine to merge and not mine to kill. No showcase branch was merged into.

**5 · ВЫВОЗ.** **Неприменимо, и это проверено командой, а не предположено:** `git remote -v` prints nothing — the repository has NO remote, so `@{u}` does not resolve (`fatal: no upstream configured for branch 'zahod/P12-gruppy'`) and there is nowhere to push. Невывезенных своей ветки: н/д, вывоз невозможен по устройству репозитория. No заявка was placed for it: a заявка asks a human to perform an operation, and there is no destination for anyone to perform it to.

**6 · ЧИСЛА.** вне git: рабочая папка **0**, главная папка **4** (all foreign, itemised above) · невлитых `zahod/`: вход **0**, выход **1** (`zahod/P4-setka`, foreign) · своя ветка влита: **да**, `e58bc9a` · невывезенных: **н/д** (нет remote) · пост-проверка: **зелёная**, отката не было.

### НЕОБРАТИМОЕ

- **Слияние `zahod/P12-gruppy` в `main`** · репозиторий `/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot` · merge-коммит `e58bc9a`, приносит 8 новых файлов и не переписывает ни одного существующего.
  🔴 **Отменять — `git -C /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot --no-optional-locks revert -m 1 e58bc9a`, а НЕ `reset --hard`.** Состояние `main` до моего влития было `31ab856`, но аналитик продолжил коммитить в главную папку ПОСЛЕ него (на момент написания отчёта `main` уже на `2a0efae`), поэтому `reset` на `31ab856` снёс бы вместе с моей работой и его — P7, P13 и всё, что легло следом. Проверять хвост перед откатом: `git --no-optional-locks log --oneline 31ab856..main`.
- **Одна строка дописана в `zhurnal/_INFRA-git/INCIDENTY.md`** инструментом `git_zona.py` как побочный эффект моего `--vsyo-ravno` · не закоммичена, снимается `git checkout -- zhurnal/_INFRA-git/INCIDENTY.md` (что заодно снимет и десять чужих строк — поэтому я её и не трогал).

Больше ничего необратимого нет: ни удалений, ни перезаписей, ни переименований, ни перемещений, ни `reset`/`checkout` поверх несохранённого, ни одной правки за пределами зоны.

### ПОВТОРЯЕМОСТЬ находок

- **Повторится на СЛЕДУЮЩЕЙ единице работы → заход ДО следующего прогона, не пункт очереди:** `## ВОПРОСЫ` #1, the Г1 false green. It is not about this задание at all — `git_zona.py check --zone` is run by EVERY заход of every wave, after every commit-along-the-way, and by приёмка as its gate 0. Every one of those pre-merge runs is currently a green that proves nothing, and the failure mode it hides is precisely the one §WARNING exists for: work that never reached git. Класс НЕМЕДЛЕННОЕ.
- **Условно повторится:** `## ВОПРОСЫ` #3 — a задание asking the executor to "decide how to express X" when X is already fixed in a file the zone declares read-only. It recurs wherever a заход is written against an existing schema, which on this arc is most of them (P13 stands on exactly this table). Cheap to prevent at assembly: the generator already knows the zone, so a задание that asks for a decision inside a read-only path is machine-detectable.
- **Не повторится → законно уходит пунктом очереди:** #2 (the "day before" phrasing is specific to describing SCD2, and P13 does not write intervals), #4 (one observation about one index), #5 and #6 (both are decisions for whoever builds over this service).

### Открытое «возвращаться»

- The four `## ВОПРОСЫ` items with `ДОМ:` outside this заход are undelivered by construction — delivering them is the analyst's move at приёмка, not mine.
- P13 (экран аудитории) stands on this service. It needs `resolve_many(student_ids, day)`, which is bulk in ONE query precisely so the screen is not an N+1; and it will hit the foreign-key pass-through of `## ВОПРОСЫ` #5 the first time somebody assigns to a teacher who does not exist.
- `## ГИГИЕНА ВХОДА` is unfilled because its owner, the §0.1 subagent, was cancelled by the orchestrator. Gate Г12 of `priyomka.py` will be red on it, and that is the expected consequence of the cancellation, not an omission by me.

## ПРАВКИ ПОСЛЕ ВЫДАЧИ — (заполняет АНАЛИТИК; исполнитель ЧИТАЕТ)
> 🔴 **Пусто — значит заход не правился с момента выдачи.** Непустой блок читается ПЕРЕД продолжением работы: правка отменяет любое противоречащее ей место выше по файлу, каким бы категоричным оно ни было.
> **Форма строки — жёсткая, по ней судит приёмка:** `### ПРАВКА N · ГГГГ-ММ-ДД ЧЧ:ММ · <что изменилось, одной фразой>`, дальше — что именно перечитать и что откатить, если уже сделано по старой редакции.
> **Аналитик:** внёс правку — обязан ОТДЕЛЬНО послать владельцу короткое сообщение для пересылки исполнителю. Правка, лежащая только в файле, до работающего исполнителя не доезжает: он файл не перечитывает сам.
> **Исполнитель:** прочитал правку — назови её номер в `## ОТЧЁТ` строкой `ПРАВКИ ПРОЧИТАНЫ: 1, 2`. Нет строки при непустом блоке = отчёт не принимается: неизвестно, по какой редакции работали.

<правок нет>

## ФАЗА ПРИЁМКИ — (заполняет АНАЛИТИК, не исполнитель)
> 🔴 **Без этого раздела заход НЕ ЗАКРЫТ.** Гейт — `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/priyomka.py <этот файл>` (Г13): пока раздел пуст или несёт плейсхолдеры, приёмка красная, и это единственное место, где вердикт остаётся ЗАПИСАННЫМ, а не сказанным в чат.
> Заполняется ПОСЛЕ отчёта исполнителя. Исполнителю сюда писать нечего — его половина выше.

**ВЕРДИКТ:** принято — прогнано оркестратором ИЗ ГЛАВНОЙ ПАПКИ после влития: `make check` → 220 passed (было 148 до этой полосы), `pytest tests/enrollment -q` → 43 passed, `aiogram в core/` → 0, ветка влита (`git branch --merged main`). Суть позиции закрыта ИМЕНОВАННЫМ тестом, а не словами: `test_moving_a_student_in_december_does_not_change_who_marked_him_in_october` — перевод ученика в декабре не меняет того, кто принимал у него в октябре. Рядом второй: `test_who_taught_in_october_is_a_query_and_never_a_stored_column` — то есть «текущий преподаватель» остался ЗАПРОСОМ по интервалам, а не хранимой колонкой, и класс багов «копия разошлась с журналом» закрыт по построению. Верификатор нашёл три дефекта, один из них закрывал интервал значением `9999-12-31`, которое означает «ещё открыт» — поймано ДО влития. Гейтов приёмки 16 из 18 на входе; Г13 — сам этот вердикт, Г12 закрыт оркестратором с причиной (см. ГИГИЕНА ВХОДА: субагента §0.1 отменил оркестратор, заполнять было некому; системная причина закрыта в источнике — промпт запуска теперь велит заходу заполнить строку самому).

**ВЕТКА РАБОТЫ:** `zahod/P12-gruppy`
*(проверяется фактом, не словом: ветка обязана существовать и быть либо ВЛИТА в основную, либо названа в открытой заявке на влитие. Ни того, ни другого — Г14 краснеет. Снять состояние: `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py poteri --branch <ветка>`)*

**ЗАЯВКИ, ПОСТАВЛЕННЫЕ ЭТОЙ ПРИЁМКОЙ — ПРОДУБЛИРУЙ СЮДА ТО, ЧТО УЖЕ ЛЕЖИТ В СПИСКЕ:**
> Адрес списка: `/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/zhurnal/_INFRA-git/zayavki`
> Читается командой (из любой папки, в том числе из worktree): `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py zayavki`
> Ставится командой: `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py zayavka --rod <git-operaciya|pravka-koda> "<текст>"`
> 🔴 Вопрос здесь НЕ «что ты хочешь сделать», а «что ты УЖЕ положил в очередь». Дубль сверяется с очередью по id машинно; намерение сверить не с чем.

заявок нет: ни одна из пяти операций не сорвалась. **Влитие** — сделано самим заходом, мерж `e58bc9a`, проверено `git branch --merged main`; **коммит** — по ходу работы, Г1 нашёл каждый хэш; **вывоз** — непроверяем, у `spetsmat-bot` нет ни одного удалённого; **деплой** — вне этой позиции (P10); **гашение** — ветка оставлена живой намеренно, волна идёт.

*(Заявок эта приёмка не ставила — так и напиши строкой «заявок нет: <почему ни одна из пяти операций не понадобилась>». Пустая строка и прочерк не принимаются: молчание неотличимо от «забыл».)*
