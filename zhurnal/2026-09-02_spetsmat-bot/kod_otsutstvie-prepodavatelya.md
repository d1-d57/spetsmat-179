# Канал исполнителя — otsutstvie-prepodavatelya (один заход до конца)
> Твой единственный файл-заход. Читай ТОЛЬКО его и названные якоря; проект не изучай.
<!-- собран bootstrap_zahod.py -->
> План/вопросы/отчёт — в секции внизу. Метрика — КАЧЕСТВО. Часы — норма.
> **Модель: Opus 5** — период отсутствия живёт в базе и влияет на обе версии распределения и на журнал — это проектирование, а не правка.

## СТАРТОВОЕ СООБЩЕНИЕ ВЛАДЕЛЬЦУ

> Это блок для владельца — то, чем тебя запустили. Исполнителю здесь делать нечего, твоё задание ниже.

```
cd /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot && opencode run --auto --model openrouter/anthropic/claude-opus-5 'Твой заход — файл /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/zhurnal/2026-09-02_spetsmat-bot/kod_otsutstvie-prepodavatelya.md. Прочитай ТОЛЬКО его и то, что он называет; остальной проект не изучай. План/вопросы/отчёт пиши в этот же файл внизу (## ПЛАН / ## ВОПРОСЫ / ## ОТЧЁТ). Ничего сверх задачи не трогай — «ничего сверх задачи» относится к СОДЕРЖАНИЮ работы; git-контур §0.1 — законное исключение, он про состояние репозитория и исполняется целиком.' < /dev/null 2>&1 | tee /tmp/zahod-otsutstvie-prepodavatelya.log
```

🔴 БЛОК ВЫШЕ — МАШИННЫЙ: его достаёт и запускает надзорный оркестратор, подменив в нём модель на живую. РУКАМИ ЕГО НЕ ЗАПУСКАЮТ — запуск без надзора и был тем, чем оплатили ночь на 05.09 (три позиции из шести не изменили ни байта: модели выгорели по квоте, а перевыбирать их было нечему).

ЗАПУСКАТЬ — ЭТИМ (проба живости и перевыбор модели внутри):
```
cd /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot && python3 /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/_generator/tools/orkestr.py zhurnal/2026-09-02_spetsmat-bot --rezhim progon --dvizhok opencode --rod suzhdenie --model openrouter/anthropic/claude-opus-5 --zahody kod_otsutstvie-prepodavatelya.md 2>&1 | tee /tmp/nadzor-otsutstvie-prepodavatelya.log
```

── СЧЁТ НЕЗАКРЫТОГО (печать, не гейт) ──
ГРАНИЦА ОБЛАСТИ: сырые подстроки в `kod_*.md` (пункт 4) — НЕ парсер очереди `dostavit_urok` (который считает только пары ДОМ:/ДОСТАВЛЕНО:). Разница в числах — законна.
🔴 снимок при сборке 2026-09-11, ПРОВЕРЬ ПЕРВЫМ ХОДОМ: `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/schet_nezakrytogo.py zhurnal/2026-09-02_spetsmat-bot`
Область: «zhurnal/2026-09-02_spetsmat-bot» — сужены пункты 1, 3, 4; долги (2) глобальны намеренно (DOLG.md не размечен по записям).
Приоритет владельца: разобрать инциденты важнее, потом закрыть долги — неразобранный инцидент это повторяющаяся ошибка, долг может подождать.
  1. инцидентов без вердикта             : 0
  2. долгов СТАТУС: ЖИВ                  : н/д — ни одного skills/*/DOLG.md нет на диске (другой git-репозиторий)
  3. уроков фабрике без ВЕРДИКТ          : 59
  4. пунктов очереди «ДОСТАВЛЕНО: нет»   : 607
     из них разбором очереди (парсер `dostavit_urok`, записи с парой ДОМ:/ДОСТАВЛЕНО:): 349
       живых (чинится доставкой — «дом есть»)  : 141
       к владельцу (решение за человеком)      : 151
       адрес недоступен (нет/папка/код/указат.) : 54
       адрес не разобран                        : 0
       отработавших (машинный след закрытия)    : 0
       доставлено                               : 3
       🔴 не проверяется машиной: содержательная отработанность записей БЕЗ следа закрытия (метки в доме, строки ✅/ЗАКРЫТО) — нужна ревизия человеком; сырой греп сверх разбора — шаблонные строки формы.

КОНТЕКСТ. <проект в 1–2 фразы>. Прошлый этап: <состояние>. ЦЕЛЬ: <что закрыть>.
Приёмка — по ОТЧЁТУ, без построчной сверки. <Если стоп до цели: получишь X, но НЕ Y.>

## ЧТО ФИНАЛИЗИРОВАНО НА ИНТЕРВЬЮ

ИНТЕРВЬЮ ПРОВЕДЕНО: да (2026-09-11) — флаг `--intervyu da` при сборке. ⚠ Он доказывает, что аналитик не ЗАБЫЛ про интервью, и НЕ доказывает, что разговор был.

1. Ольга Рыжая не будет с 1 по 12 октября — живой случай, на нём и проверять; на любое число периода её нельзя выбрать принимающей ни по занятию, ни в постоянном
2. отметка ставится и задним числом, и на будущее, переживает перезагрузку и видна в журнале преподавателей отдельным видом клетки

## КОНТРАКТ ЗОНЫ (обязателен — не удалять; вписан Cowork)
- **МЕСТО РАБОТЫ:** ветка `zahod/otsutstvie-prepodavatelya` в основной папке. 🔴 Она должна УЖЕ стоять. НЕ на ней — СТОП, НЕ делай `git checkout`: в общей папке он МОЛЧА откатывает дерево к состоянию ветки (цена 27→28.07: файл сильно откатился ночью, поймал владелец вручную; след в git НЕ остаётся). Тогда заход пересобрать с `--worktree`. Ветку не переключай, в другие НЕ коммить.
- **ЗОНА (можно менять):** `veb/razdely/istoria_zanyatij.py` `veb/razdely/shkolniki.py` `veb/obshchee/karkas.py` `migrations/` `tests/veb/` `zhurnal/2026-09-02_spetsmat-bot/kod_otsutstvie-prepodavatelya.md`. Всё вне — **READ-ONLY**: не править, не двигать, не удалять, не рефакторить «заодно».
- 🔴 **ЗАВЁЛ НОВЫЙ `.md` — РЕГИСТРИРУЕШЬ ЕГО САМ, ТЕМ ЖЕ ХОДОМ, ОДНОЙ КОМАНДОЙ:** `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/register_doc.py <путь> "<описание>"` (из корня репо). `_studio/docs/` тебе по-прежнему READ-ONLY **для правки руками** — дверь ровно одна, и это она. Дверь идемпотентна (повторный вызов дубля не заведёт) и отказывает на пути вне `_studio/`, на несуществующем файле и на пустом описании. Свой файл-заход регистрировать не нужно: он рождается зарегистрированным из `bootstrap_zahod.py`. **Красный хук на ТВОЁМ новом `.md` — это не повод для `--no-verify`, а повод позвать дверь.** *Почему правило существует и почему оно теперь исполнимо: 26.07 оно записано с ценой в пять документов-сирот и через два дня повторилось дословно. Дальше стало хуже: до 30.07 указания «зарегистрируй» и «`docs/` только на чтение» противоречили друг другу, выход был ровно один — обойти хук, и по автологу `_INFRA-git/INCIDENTY.md` это 28 обходов `--no-verify` из 56 срывов коммита, 27 из них по одной этой причине (48 % всей боли с коммитами, тринадцать исполнителей подряд). Обходить больше нечего.*
- **КОММИТ:** два хода — `add` по своим путям, затем `commit` **с теми же путями после `--`** (полная форма и цена каждого хода — §4); коммить ПО ХОДУ работы, не одним последним ходом (§4). НИКОГДА `-A` / `.` / `commit -am`, и никогда `commit` без путей. Субагенты не коммитят. **`--no-optional-locks` обязателен:** обычный git переписывает индекс, берёт `.git/index.lock` и роняет параллельный ручной коммит владельца.
- **SCRATCHPAD — ТОЛЬКО ЛИЧНЫЙ.** Черновики, выкладки, промежуточные версии — в личную папку СВОЕГО захода `scratchpad/otsutstvie-prepodavatelya/`. Общие пути (`scratchpad/otchet.md`, любой `scratchpad/*` без имени твоей темы) ЗАПРЕЩЕНЫ: чужой отчёт уедет в твой файл или твой — в чужой, а приёмка читает отчёт без построчной сверки и подмену НЕ ЛОВИТ по построению. *Цена 25.08: готовый `## ОТЧЁТ` захода konvejer-incidentov был записан в общий `scratchpad/otchet.md`, и 92 строки чужого отчёта простояли в `kod_slovari-v-kod.md`.*
- 🔴 **Звал `register_doc.py` — допиши `_studio/docs/KARTA.md` к своим путям В ОБОИХ ходах.** Строка регистрации лежит физически в нём. Ворота 5 читают `§6` **с диска**, а не из индекса: коммит без этого файла пройдёт ЗЕЛЁНЫМ, документ уедет сиротой, а строка умрёт при первом `checkout` (дата данных 2026-07-30, найдено верификацией захода «kod_registracia-bez-obhoda.md»).
- **ЗАПРЕТ:** ничего за пределами зоны, даже если «мешает» или «чинится в одну строку». Нашёл проблему вне зоны → в отчёт, не трогай.

## 0. ПЕРВЫЙ ХОД
### 0.1 🔴 ГИТ-КОНТУР — ДО ВСЕГО ОСТАЛЬНОГО, И ПЕРВЫМ ХОДОМ ЦЕЛИКОМ

🔴 «ничего сверх задачи» относится к СОДЕРЖАНИЮ работы; git-контур §0.1 — законное исключение, он про состояние репозитория и исполняется целиком.

🔴 **ПОРЯДОК ЗДЕСЬ — ЧАСТЬ УСТРОЙСТВА, А НЕ ОФОРМЛЕНИЕ. Сначала САМ прогоняешь две команды самопроверки контура (пункт 1 ниже), и только ПОТОМ заводишь свою рабочую папку** — её ветка отпочковывается от основной такой, какая она есть на момент запуска: контур пуст, доносить инструмент влитием нечего.

**1. ВЕСЬ КОНТУР ПУСТ — САМОПРОВЕРКА ВМЕСТО СУБАГЕНТА.** При сборке проверены три числа контура, и все три нулевые: невлитых `zahod/*`-веток 0 (🔴 снимок при сборке 2026-09-11, ПРОВЕРЬ ПЕРВЫМ ХОДОМ: `git --no-optional-locks branch --no-merged main | grep -c 'zahod/'`); открытых заявок 0 (снимок при сборке 2026-09-11, пересчитать самому: `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py zayavki`); названных `--vlit` 0. Звать субагента не за чем — выполни САМ две команды и вставь их вывод в `## ОТЧЁТ` дословно:
```
git --no-optional-locks branch --no-merged main | grep -c 'zahod/'   # снимок при сборке 2026-09-11: 0
python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone veb/razdely/istoria_zanyatij.py veb/razdely/shkolniki.py veb/obshchee/karkas.py migrations/ tests/veb/
```
Первая вернула не 0 — НИЧЕГО чужого не вливай (свою ветку вольёшь последним ходом, см. ниже), назови число строкой в `## ОТЧЁТ` и работай дальше. Вторая красная — сначала приведи в порядок свою зону.

Если при следующей сборке хоть одно из трёх чисел окажется ненулевым, генератор сам вернёт сюда задание субагенту гит-контура — печатает его дверь `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/bootstrap_zahod.py --zadanie-subagentu`; звать его в этом заходе не надо.

🔴 ОТВЕТ ЛЮБОГО субагента, которого ты запускаешь (не только этого), обязан КОНЧАТЬСЯ строкой «выдано N позиций из M найденных»: канал мог оборвать его молча, и без этой строки усечение неотличимо от честного «мало нашлось». Нет строки — ответ усечён, в `## ОТЧЁТ` не вставляй, перезапроси.

**2. ТЕПЕРЬ ЗАВОДИ СВОЮ РАБОЧУЮ ПАПКУ** (команда — в блоке «МЕСТО РАБОТЫ» выше) и работай в ней как обычно. Её ветка отпочкована от свежей основной, поэтому инструмент, которым ты работаешь, уже на диске — отдельного «влить перед работой» больше нет.

вливать нечего, проверено командой `git branch --no-merged` — но проверено ПРИ СБОРКЕ, а не сейчас: невлитых `zahod/*`-веток было 0. 🔴 снимок при сборке 2026-09-11, ПРОВЕРЬ ПЕРВЫМ ХОДОМ: `git --no-optional-locks branch --no-merged main | grep -c 'zahod/'`. Число могло устареть между сборкой и твоим прогоном — 14.08 заход нёс ровно этот ноль, а к прогону невлитых было три.


- деплоя в этом заходе нет.

- Проверь ветку: `git branch --show-current` — обязано быть `zahod/otsutstvie-prepodavatelya`. Не она — СТОП, `git checkout` НЕ делай (§4 GIT-disciplina), нужен `--worktree`.
- Точка отката: `git add veb/razdely/istoria_zanyatij.py veb/razdely/shkolniki.py veb/obshchee/karkas.py migrations/ tests/veb/ zhurnal/2026-09-02_spetsmat-bot/kod_otsutstvie-prepodavatelya.md` → commit (или zip), если зона не чиста в HEAD (не фабрикуй, если чиста).
- Прочитать ТОЛЬКО: `названные файлы-якоря`. Проект не изучай.
- ПЛАН — в `## ПЛАН` перед действиями.

## 1. ДИСЦИПЛИНА (Карпатов)
🔴 **Код возврата — ПЕРВЫМ, до содержательного вывода команды.** «Отработала» и «упала, а я читаю прошлое состояние» выглядят одинаково; сначала `echo $?`, потом выводы. То же с гейтами. *Цена 21.07: `rc=128` (сбой прав окружения) четырежды прочитан как результат — едва не откатили верное правило по ложным данным.*
Предпосылки/развилки назвать вслух; минимум без спекуляций; хирургия (строка → к заданию); критерий, который может провалиться. Якорные замены — abort при ≠1. Сохранять по умолчанию. **Оспорить ложную предпосылку — включая КРИТЕРИЙ ГОТОВНОСТИ: считаешь его кривым — скажи в `## ПЛАН`, ДО работы, и предложи поправку.** Субагенты: ≤5, рейт-лимит = отступить + доложить (не слепой ретрай).

🔴 **Пишешь содержательный текст — термин НЕ употребляется раньше, чем определён**, включая заголовки, подводки и формулировки теорем. «Определение в тексте есть» не считается: если оно ниже первого рабочего употребления, читатель встаёт ровно там. Чинится ПЕРЕСТАНОВКОЙ определения вверх, не дописыванием пояснения. Гейт: `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/check_termin.py <src>` (exit 1 при нарушении). Канон — `../docs/kak-delat/STANDART-teksta.md` правило 11. *Цена 30.07: теорема пользовалась словом «ординал», определение стояло строкой ниже; поймал владелец, ни один гейт не увидел, раздел переписан дважды.*

## 2. ЗАДАЧА

🔴 **WRITE YOUR `## ОТЧЁТ`, `## ПЛАН` AND `## ВОПРОСЫ` IN ENGLISH, AND EVERY FILE AND EVERY COMMIT MESSAGE YOU PRODUCE TOO.** Owner's decision 30.08. It is a каркас-level rule, not a preference — wave 2 lost it twice because the pass text listed the report SECTIONS and never said «every file you create». Fixed Russian addresses stay Cyrillic: `ЦЕНА:` · `ВЕРДИКТ:` · `ДОМ:` · `ДОСТАВЛЕНО:` · `ПОДЪЁМ:` · `[ДОЛГ: …]` · every `## ` heading of this file · every path and command.
Конкретные шаги — у автора. **КРИТЕРИЙ ГОТОВНОСТИ (может ПРОВАЛИТЬСЯ):** живой прогон на реальном объекте репозитория (не только фикстура) — `python3 -c '<команда прогона>'` на собранном файле или `bash _generator/tools/fixtures/bootstrap_zahod/PROGNAT.sh` → `rc=0` и все ловушки зелёные..
**Отрицательный вердикт несёт ОХВАТ В СЕБЕ:** не «дыр не найдено», а «дыр не найдено, проверено X из Y». Без охвата вердикт не принимается — «проверено 2 из 9» и «проверено 9 из 9» выглядят одинаково.

## 3. ВЕРИФИКАТОР (если двигаем/теряем/жмём)

Верификатор нужен, тип — **ПОСЛЕ-типа** — судит результат, стоит в конце, после задачи. Свежий субагент, ДРУГИМ методом (прогон по живой копии базы: отметить период, проверить каждый его день на обеих версиях распределения, перезапустить сервер, проверить снова), не перечитывает свою же правку. Доля сплошной выборки: 12 из 12 дней периода и 2 из 2 версий распределения. Финальная строка ответа обязательна дословно: «выдано N позиций из M найденных» — без неё ответ считается усечённым и в отчёт не вставляется.

## 4. 🔴 КОММИТ СВОЕЙ ЗОНЫ — ПО ХОДУ РАБОТЫ, НЕ ОДНИМ ПОСЛЕДНИМ ХОДОМ
Ты работаешь host-side и в `.git` ПИШЕШЬ — значит коммитишь САМ, никому не передавая. Каждую завершённую часть работы коммить СРАЗУ, теми же двумя ходами — не копи всё к финальному ходу:
```
git --no-optional-locks add -- veb/razdely/istoria_zanyatij.py veb/razdely/shkolniki.py veb/obshchee/karkas.py migrations/ tests/veb/ zhurnal/2026-09-02_spetsmat-bot/kod_otsutstvie-prepodavatelya.md                     # вводит НОВЫЕ пути в индекс
git --no-optional-locks commit -m "<зона>: <что сделано>" -- veb/razdely/istoria_zanyatij.py veb/razdely/shkolniki.py veb/obshchee/karkas.py migrations/ tests/veb/ zhurnal/2026-09-02_spetsmat-bot/kod_otsutstvie-prepodavatelya.md   # отсекает всё чужое
python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone <зона>   # из корня репо; должен быть ✅
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

**ЗОНА ГИГИЕНЫ:** `veb/razdely/istoria_zanyatij.py` `veb/razdely/shkolniki.py` `veb/obshchee/karkas.py` `migrations/` `tests/veb/` `zhurnal/2026-09-02_spetsmat-bot/kod_otsutstvie-prepodavatelya.md`

- **Г1. Зона доехала в git.** `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone veb/razdely/istoria_zanyatij.py` → ✅; `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone veb/razdely/shkolniki.py` → ✅; `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone veb/obshchee/karkas.py` → ✅; `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone migrations/` → ✅; `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone tests/veb/` → ✅; `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone zhurnal/2026-09-02_spetsmat-bot/kod_otsutstvie-prepodavatelya.md` → ✅. Красное на любой из команд — отчёт не принимается: приёмка гоняет их все первым ходом.
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
for R in <репозитории, которых ты касался>; do
  echo "== $R"; git -C $R --no-optional-locks status --porcelain
done
```
Своя зона — своими путями (`add` + `commit -- <пути>`). Чужая содержательная работа — НЕ твоя:
называешь строкой в отчёте и оставляешь. Пусто у всех — так и напиши числом «вне git 0».

**2 · ВЛИТИЕ СВОЕЙ ВЕТКИ В ОСНОВНУЮ.** Только после того, как шаг 1 дал «вне git 0» на своей
зоне — влитие отказывает на грязном дереве:
```
python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py vlit-v-osnovnuyu zahod/otsutstvie-prepodavatelya --zone <своя зона> \
    --vsyo-ravno "своя рабочая папка ещё жива — влитие последним ходом захода, штатно"
```
Конфликт — ЗАКОННЫЙ исход, не повод форсировать: разрешай по существу, если понимаешь обе
стороны; не понимаешь — `git_zona.py vlit-v-osnovnuyu --abort`, ветка остаётся невлитой,
строка в отчёт и заявка на влитие (`git_zona.py zayavka --rod git-operaciya`).
🔴 Конфликт на `README.md` — только ОБЪЕДИНЕНИЕМ записей реестра, никогда выбором стороны:
параллельные заходы волны дописали по строке — обе записи правы, выбор одной молча уничтожает
регистрацию соседа.

**3 · ПОСТ-ПРОВЕРКА ИЗ ГЛАВНОЙ ПАПКИ.** Отвечает на вопрос «механизм ВСТАЛ», а не «коммит
виден»: прогон изменённого механизма (здесь она же — checkout-режим, папка одна) плюс `grep` по ЖИВОМУ файлу,
который его зовёт (хук, конвейер, генератор):
```
cd /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot && <команда прогона механизма, который заход менял> && echo $?
grep -n '<как механизм назван в вызывающем коде>' <живая точка вызова>
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

### Критерий готовности требовал того, чего названная зона показать не может

Критерий гласил: «в журнале преподавателей 12 клеток особого вида». Живой случай —
01–12.10, то есть период целиком В БУДУЩЕМ. Решётка журнала строится из `sessions`
(`IstoriyaService.sostavit`), а строки `sessions` на будущую дату нет и не будет до самого
занятия: столбцов у будущего периода НОЛЬ. Двенадцать клеток в решётке были физически
невозможны, и починить это внутри зоны было нечем — отбор живёт в
`core/services/istoria_poseshchenij.py`, вне зоны.

ЦЕНА: полчаса на разбор и вторая раскладка (полоса дней периода рядом с решёткой),
придуманная исполнителем вместо того, чтобы быть названной в задании. Исполнитель, который
разбираться не станет, имеет два выхода, и оба плохие: посчитать что-нибудь другое и
назвать это двенадцатью клетками, либо сдать красный критерий при работающей функции.
Аналитик, пишущий критерий по числу клеток, обязан проверить, что клетки этого рода вообще
существуют на экране, который он называет, — одним запросом к тому файлу, из которого экран
собирается.

> Находка не про эту сессию, а закономерность про саму фабрику, годная другим заходам, — оформи как пункт очереди в `## ВОПРОСЫ` (формат там же) с `ДОМ: <эта арка>/UROKI-FABRIKE.md`, а не пиши прямо сюда неструктурированной строкой.
> **Не про задачу — про САМУ ФАБРИКУ.** Ты работаешь с пустым контекстом и потому видишь то, чего не видит аналитик: он писал этот заход и ему приятно, что заход хорош. Сломался ВХОД (издание не то, id врёт, зона не содержит файла с ответом)? Критерий готовности кривой? Инструкция канона противоречит живому файлу? — сюда, строкой.
> Формат жёсткий (по нему гейт): `### <что произошло>` / `ЦЕНА: <что сломалось и сколько стоило>`.
> **ЦЕНА обязательна.** Без неё это наблюдение, а не урок, и в канон оно не пойдёт. Не знаешь цены — не пиши.
> **Не сочиняй.** Пустая секция — законный отчёт. Выдуманный урок хуже отсутствующего: он попадёт в канон, который читают ВСЕ будущие проекты.

## ПЛАН — (заполняет исполнитель)

**Read first, decided before writing code.** The zone is
`veb/razdely/istoria_zanyatij.py` · `veb/razdely/shkolniki.py` ·
`veb/obshchee/karkas.py` · `migrations/` · `tests/veb/`. Everything below stays
inside it; the one thing that does not fit is named at the end as a debt.

### What the existing code already holds, and why a new table is still needed
* `teacher_attendance(session_id, teacher_id, status)` is «сегодня заболел» — it
  hangs off a `sessions` row, so it can only speak about a date on which a lesson
  has already been opened. `_OtsutstvieNaDatuAdapter` in `veb/server.py` says this
  out loud: *«A date with no `sessions` row has no absence either»*. A period of
  twelve October days, ten of which are not lesson days at all, cannot live there.
* `prepodavatel_ne_prihodit(teacher_id, slot)` is «по четвергам не хожу вообще» —
  a weekday rule with no dates. Also not a period.
* So part 1 of the задание («строка в базе: кто, с какой даты, по какую, почему,
  кто отметил, когда») is a new table, exactly as the задание says.

### Part 1 — ХРАНИЛИЩЕ (own commit)
* `migrations/013_otsutstvie_prepodavatelya.sql` (yoyo, plain SQL, `-- depends: 012_…`):
  `otsutstvie_prepodavatelya(id, teacher_id, s_daty, po_datu, prichina, kto_otmetil, kogda)`.
  Both ends INCLUSIVE — the owner said «с 1 по 12 октября» and the готовности
  criterion counts twelve days, which is `01..12` inclusive. `check (s_daty <= po_datu)`,
  ISO `glob` checks like the rest of the schema, index on `(teacher_id, s_daty)`.
  Several periods per teacher are allowed; overlaps are not forbidden by the schema
  (two overlapping «болезнь» rows are not a contradiction, they are two notes).
* The access layer goes into `veb/obshchee/karkas.py`, because both readers
  (`shkolniki.py` for the distribution, `istoria_zanyatij.py` for the journal) already
  import that module and nothing else is shared by the two. Functions:
  `obespechit_otsutstvia(c)` (create-if-missing, the same idiom
  `infra/prepodavatel_den_repo.obespechit` already uses for a live база older than its
  migration), `periody_otsutstvij(c)`, `otsutstvuyushchie_na_datu(c, den)`,
  `otmetit_otsutstvie(...)`, `snyat_otsutstvie(c, id)`.

### What happens to pupils ALREADY assigned to those days — decision
**Nothing is deleted, and the fact is shown instead.** The `enrollment` row stays as
it is; the journal page grows a block «остались без принимающего» listing, per period,
every pupil whose open row on the period's slots points at the absent teacher. Reason:
the period ends (she is back on the 13th) — deleting the standing assignment would
destroy a fact that is still true, to express a fact that is temporary. This follows
the задание's own suggestion and is named again in `## ОТЧЁТ`.

### Part 2 — ОТМЕТИТЬ (own commit)
A form on the teachers' journal (`/istoria`, tab «Преподаватели»): teacher, `с`, `по`,
reason, save. New route `/api/otsutstvie` declared by
`istoria_zanyatij.marshruty()` — the seam is dispatched on **both** GET and POST by
`veb/server.py` (`do_GET` and `do_POST` each end with the same `_marshruty_razdelov()`
branch), so the door can live inside the zone. `POST` marks, `DELETE`-by-`snyat` field
removes. Backdating is not restricted in any way: «заболел сегодня» and «не будет с
1 октября» are the same row, which is exactly what the owner asked for.

### Part 3 — ВИДНО (own commit)
* In the teachers' grid a cell whose day falls in a period renders as its **own kind**
  (`ist-otsut`, sign `О`, its own colour and `title` naming the reason and the period)
  — not `✕` («не был»), not empty («не отмечено»). This is what covers a backdated mark.
* The grid's columns are PAST lessons only (`IstoriyaService` folds over `sessions`),
  so a future period — the live case, 01–12.10 — has no column to colour. Therefore the
  page also gets a **day-by-day strip per marked period**: one cell per calendar day of
  the period, each of the same special kind. That is where the «12 клеток особого вида»
  of the готовности criterion actually are, and it is the only way to show a future
  period without inventing lesson days that do not exist.

### Part 4 — ДЕЙСТВУЕТ (own commit)
* `shkolniki.prihodyashchie_v_slot(kt, sl, tekushchij)` is the ONE place that decides
  who may be offered as принимающий, and it already serves **both** versions: the
  permanent screen calls it once per column (slots 1 and 2), the lesson screen once for
  the single column. Narrowing it therefore covers both versions with one rule.
* The date of a column comes from `kt.DNI` (`{ключ: (имя, слот, дата, сокр)}`) — the
  lesson screen carries the requested date, the permanent screen carries the nearest
  Monday and Thursday. `Kontekst` gets `otsutstvie_po_dnyam: {дата: frozenset(teacher_id)}`,
  filled by `sobrat_kontekst` for every date in `DNI`.
* **The absent teacher is removed even when she is the CURRENT value**, which is the one
  exception to the existing «текущий остаётся в списке всегда» rule, and it is deliberate:
  that rule exists so a field can show its own value, and here the field says instead
  «— нет — (принимающий отсутствует)» on the selected option. That is not a silent lie —
  it names the state — and it is what «не серым, а отсутствует в выборе» requires.
  Nothing is saved by rendering it: the shell's script enqueues a правка only on a
  `change` event (`karkas.py`, `pravki` Map), so an untouched field writes nothing.

### Part 5 — ПЕРЕЖИВАЕТ ПЕРЕЗАГРУЗКУ (checked, not claimed)
A live run on a COPY of the боевая база (`data/spetsmat.db`, copied — the original is
never written): mark Ольга Рыжая 01.10–12.10, check 12 days × 2 versions = 24, count the
special cells, stop the server, start it again, repeat all 24 + the cell count.

### What does NOT fit in the zone, and is reported rather than done
The second half of part 4 — *«если выбор всё же придёт запросом (старая вкладка), дверь
записи ОТКАЗЫВАЕТ»* — lives in `veb/server.py` (`_OtsutstvieNaDatuAdapter`, line ~443,
used at line ~1583 for the lesson layer) and in `core/services/enrollment.py`
(`enforce_calendar_and_ceiling`) for the permanent layer. Both are outside the zone and
both are READ-ONLY for this заход. The exact patch is written out in `## ВОПРОСЫ` so
that whoever owns `veb/server.py` next can apply it without re-deriving it.


## ВОПРОСЫ — (заполняет исполнитель)

1. The WRITE DOOR of the lesson layer still refuses only on `teacher_attendance`, so a
   stale tab that already carries the absent teacher's id in its `<select>` can still POST
   it. The patch is one condition next to the existing one at `veb/server.py:1583`
   (`_OtsutstvieNaDatuAdapter(conn).otsutstvuet(teacher_id, den)`): add
   `or teacher_id in karkas.otsutstvuyushchie_na_datu(conn, den)` and answer 409 with
   «преподавателя нет в этот день — отмечен период отсутствия». Outside this заход's zone,
   which is why it is written out rather than applied.
   ДОМ: владелец
   ДОСТАВЛЕНО: нет

2. The WRITE DOOR of the permanent layer (`enforce_calendar_and_ceiling`) knows
   `TeacherCalendarPort.attends(teacher_id, slot)` — a weekday question with no date, so it
   cannot see a period at all. It needs a second port asking «отсутствует ли он в день
   `effective_from`», the same shape `TeacherPresencePort` already has for the lesson layer.
   Until then the permanent screen is protected by the list only, not by the door.
   ДОМ: владелец
   ДОСТАВЛЕНО: нет

3. `karkas.obespechit_otsutstvia` repeats the `create table` of
   `migrations/013_otsutstvie_prepodavatelya.sql` word for word, because the home of such a
   repository (`infra/`) is outside this заход's zone. The copy is guarded by
   `tests/veb/test_otsutstvie_prepodavatelya.py::test_obespechit_povtoryaet_migraciyu_pole_v_pole`,
   which compares the two schemas column for column — but the right fix is to move the five
   functions next to `prepodavatel_den_repo`, which already solves the same problem for
   migration 007.
   ДОМ: владелец
   ДОСТАВЛЕНО: нет

4. The teacher CARDS on a group tab are filtered by `kt.otsutstvuyut_prepoda` only
   (`veb/razdely/gruppy.py:68`), i.e. by `teacher_attendance`. A teacher with a marked
   period therefore vanishes from the receiver LIST but still has a card on the group tab of
   a day inside the period. One line, `kt.otsutstvie_po_dnyam`, fixes it; outside the zone.
   ДОМ: владелец
   ДОСТАВЛЕНО: нет

5. The word «отсутствует» on the teachers' tab of the distribution
   (`veb/razdely/prepodavateli.py:226` and `:323`) is likewise read out of
   `kt.otsutstvuyut_prepoda` alone, so a marked period does not put it there. Same one-field
   fix, same reason it is not applied here.
   ДОМ: владелец
   ДОСТАВЛЕНО: нет

6. The journal grid can only carry columns for PAST lessons: `IstoriyaService.sostavit`
   unfolds `sessions`, and a future date has no row there. A future absence period therefore
   has no grid column to mark, which is why this заход added a day strip beside the grid. If
   the owner wants future days as real columns, the selection must grow a «планируемые дни»
   source, and that lives in the service, not in the page.
   ДОМ: владелец
   ДОСТАВЛЕНО: нет

7. `tests/veb/test_kanon_verstki.py` errors at SETUP on this machine — thirteen errors,
   all `config.IstochnikNeNazvan: переменная среды SPETSMAT_BAZA не выставлена`. It is not
   caused by this заход (the same errors stand on the commit before it), but it means the
   layout canon suite is silent by default, and a заход that breaks the canon would find that
   out from the owner rather than from a gate. The fixture should name a copy of its own the
   way the other suites do, or say out loud that it is skipped.
   ДОМ: владелец
   ДОСТАВЛЕНО: нет

> Нашёл вещь, которая принадлежит чужому дому (термин/источник/урок/следующий заход) — не только вопрос владельцу? Оформи ПУНКТОМ ОЧЕРЕДИ, тремя строками:
> ```
> N. <текст находки>
>    ДОМ: <путь от корня репозитория | владелец>
>    ДОСТАВЛЕНО: нет
> ```
> 🔴 **`ДОМ:` — ОБЯЗАТЕЛЬНОЕ ПОЛЕ, И АДРЕС В НЁМ ОБЯЗАН СУЩЕСТВОВАТЬ В МОМЕНТ, КОГДА ТЫ ЕГО ПИШЕШЬ.** Путь, которого нет на диске, — не адрес: такую запись нельзя ни доставить, ни спросить, и она не чинится ничем. Замер 2026-09-06 по 632 файлам `kod_*.md`: 370 пунктов очереди из 1570 родились ровно так — больше, чем всех доставимых (195) вместе взятых. Проверить СВОЙ файл до отчёта — одна команда:
> ```
> python3 _generator/tools/bootstrap_zahod.py --proverit-doma <этот файл>
> ```
> rc=0 — все дома достижимы; rc=1 — назван дом, которого нет (команда печатает какой именно). Тот же разбор гоняет `Г7` приёмки, и у него храповик: у ЭТОГО захода база 0, поэтому первый же недостижимый дом здесь — красный на приёмке, а не запись, которую через неделю никто не найдёт.
> `ДОМ: владелец` — законный адрес и НЕ недостижимый дом: он значит «дома-файла нет вовсе, решение за человеком». Не знаешь пути — пиши его, а не выдуманный путь. Для урока фабрике дом почти всегда `<эта арка>/UROKI-FABRIKE.md`. Аналитик при переносе меняет `ДОСТАВЛЕНО: нет` на `ДОСТАВЛЕНО: <имя-захода>#<N>` И дописывает ЭТУ ЖЕ строку-метку в файл по адресу ДОМ — `priyomka.py` (Г7) красным ловит и «доставлено» без метки на месте, и недостижимый дом сверх базы; достижимое-недоставленное печатает.
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

> 🔴 **БЛОК §0.1 ОТМЕНЁН ОРКЕСТРАТОРОМ ПЕРЕД ЗАПУСКОМ, И ЭТО НЕ РЕШЕНИЕ ИСПОЛНИТЕЛЯ.**
> Указание дословно: «СУБАГЕНТА ГИТ-КОНТУРА §0.1 НЕ ЗАПУСКАЙ… Причина замерена соседней
> волной: четыре захода из десяти умерли ровно на этом вызове. Вместо всего блока §0.1
> выполни САМ одну команду и вставь её вывод». Команда выполнена первым ходом, её вывод —
> ниже. Гейт Г12 краснеет здесь по отмене, а не по несделанной работе.

**СНИМОК ВХОДА** *(команды и их ВЫВОД, а не пересказ; снят ПЕРВЫМ ходом, до всякой работы)*
```
$ git --no-optional-locks branch --no-merged main | grep -c zahod/
0
```
Это и есть та единственная команда, которой оркестратор заменил весь §0.1. Остальные три
команды снимка §0.1 отменены вместе с блоком; ниже — то, что снято по ним ПОСЛЕ работы, в
рамках §4.1 (`Г3`) и финальной гигиены, чтобы число входа было с чем сравнить:
```
$ git --no-optional-locks branch --no-merged main | grep zahod/     # ПОСЛЕ работы
+ zahod/kabinet-plitki
+ zahod/konduit-galochki-i-podskazki
* zahod/otsutstvie-prepodavatelya
+ zahod/zhurnal-setka
$ python3 .../git_zona.py zayavki
Охват: заявок открыто 0, переадресовано 28, постоянных исключений 0, сторож краснеет на 0
```

**ЧТО СДЕЛАНО** *(с хэшами)*
Долгов входа не было: на входе невлитых `zahod/*`-веток НОЛЬ, открытых заявок НОЛЬ.
Вливать, гасить и закрывать было нечего — ни одной чужой ветки и ни одной заявки к моменту
первого хода не существовало. Своя работа — пять коммитов, они названы в `## ОТЧЁТ`.
🔴 Три ЧУЖИЕ невлитые ветки (`kabinet-plitki`, `konduit-galochki-i-podskazki`,
`zhurnal-setka`) появились УЖЕ ПОСЛЕ снимка входа: это соседние заходы той же волны,
работающие прямо сейчас в своих рабочих папках. Они не мои долги входа и вливать их
нельзя — каждая вливает себя сама последним ходом (тот же порядок, что у меня).

**ВСЕ ДОЛГИ ВХОДА ЗАКРЫТЫ:** `да`
*(`нет` законно — но ТОЛЬКО со списком поимённо: что осталось и почему это непроходимо ТВОИМИ
правами (чужая живая рабочая папка, нужно решение владельца, конфликт, обеих сторон которого
не понимаешь). «Сложно» и «не моя тема» причинами не являются. `нет` без списка = красный.)*

## ОТЧЁТ — (заполняет исполнитель)
**АРТЕФАКТ:** `/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/veb/razdely/istoria_zanyatij.py` — the teachers' journal, opened in a browser at `http://math-kluychiki.ru/istoria` (locally: `SPETSMAT_BAZA=<копия> SPETSMAT_VEB_SECRET=<строка> PYTHONPATH=. python3 -m veb.server --port 8731`, then `/istoria`, tab «Преподаватели»). Beside it: `/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/migrations/013_otsutstvie_prepodavatelya.sql` and `/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/veb/obshchee/karkas.py`.
**РОД АРТЕФАКТА:** `исходник`
**КОММИТ:** `1426974` — `otsutstvie: two verifier findings, and a landmine my own edit exposed` (последний из СЕМИ; предыдущие — `474ffdf` · `8d7aa19` · `d7eaaf1` · `7998a51` · `9e8ced5` · `db330c2`) · `git_zona.py check --zone <каждый путь зоны по очереди>` → ✅ (шесть путей, шесть ✅)

### ЧТО СДЕЛАНО, ПО ЧАСТЯМ ЗАДАНИЯ, КАЖДАЯ СВОИМ КОММИТОМ

| часть | коммит | что в нём |
|---|---|---|
| 1 · ХРАНИЛИЩЕ | `474ffdf` | `migrations/013_otsutstvie_prepodavatelya.sql` + пять функций доступа в `veb/obshchee/karkas.py` |
| 2 · ОТМЕТИТЬ | `8d7aa19` | дверь `POST /api/otsutstvie` и форма в журнале преподавателей |
| 3 · ВИДНО | `d7eaaf1` | отдельный вид клетки `ist-otsut`, полоса дней периода, список «остались без принимающего» |
| 4 · ДЕЙСТВУЕТ | `7998a51` | сужение `shkolniki.prihodyashchie_v_slot` по дате колонки + 41 тест |
| 5 · ПЕРЕЗАГРУЗКА | `9e8ced5` | живой прогон + отчёт; отдельного кода не требует |
| гигиена | `db330c2` | DDL убран с пути каждого рендера |
| по находкам верификатора | `1426974` | кнопка «снять» только правящему · честный комментарий миграции · сырая строка модуля |

**ЗАЧЕМ ИМЕННО ТАК — три решения, которые стоило бы оспорить, и почему они такие.**

1. **Третья таблица, а не третье значение в чужой.** `teacher_attendance` висит на строке
   `sessions`, и `veb/server.py::_OtsutstvieNaDatuAdapter` сам пишет в докстроке: *«A date
   with no `sessions` row has no absence either»*. Из двенадцати дней 01–12.10 занятий
   четыре, строк `sessions` — ноль. `prepodavatel_ne_prihodit` — день НЕДЕЛИ без дат:
   записав туда, мы убрали бы человека со всех понедельников года, а не с двух.
2. **Уже назначенные дети НЕ удаляются** (это был открытый вопрос §1 задания). Период
   кончается — тринадцатого она на месте, — и стереть постоянное закрепление значило бы
   уничтожить верный факт ради временного. Вместо этого организатору показан список
   «остались без принимающего: N — имена», и на живой базе это **3 ребёнка: Быков
   Владислав, Кудишин Андрей, Фёдоров Михаил**. Закрепления в `enrollment` целы —
   проверено счётом строк в тесте `test_deti_ne_udalyayutsya_a_nazvany_spiskom`.
3. **Отсутствующая снимается со списка ДАЖЕ будучи текущим значением поля** — единственное
   исключение из стоящего в коде правила «текущий остаётся в списке всегда». Правило
   существует, чтобы поле могло показать своё значение; здесь поле показывает подписанный
   пустой пункт `— нет — (принимающий отсутствует)`, то есть НАЗЫВАЕТ состояние, а не врёт
   о нём. Ничего при этом не сохраняется: скрипт оболочки кладёт правку в очередь только
   по событию `change` (`karkas.py`, `pravki`), а нетронутое поле не пишет ничего.

### КАК ПРОВЕРЕНО (числа, а не «должно работать»)

**ЖИВОЙ ПРОГОН НА КОПИИ БОЕВОЙ БАЗЫ** (копия снята штатной дверью
`core/istochnik.py --snyat-kopiyu`; в боевую базу не записано ничего). База: 57 школьников,
15 900 отметок, 14 действующих принимающих, «Ольга Рыжая» = `teachers.id 13`. Период отмечен
через ЖИВУЮ HTTP-дверь, а не вставкой в базу: `POST /api/otsutstvie` → `200 {'ok': True,
'id': 1, 'dnej': 12}`.

```
клеток особого вида в журнале преподавателей: 12 —
  2026-10-01 … 2026-10-12 (все двенадцать, поимённо)
остались без принимающего: 3 — Быков Владислав, Кудишин Андрей, Фёдоров Михаил

== ДО ПЕРЕЗАПУСКА ==   (12 строк, по одной на день; печатались все)
  2026-10-01 занятие | по занятию: НЕТ ✅ (в списке 13) | постоянное: НЕТ ✅ (в списке 13)
  …
  2026-10-12 занятие | по занятию: НЕТ ✅ (в списке 13) | постоянное: НЕТ ✅ (в списке 13)
  проверено 24 из 24, зелёных 24
— сервер остановлен, поднят заново —
клеток особого вида после перезапуска: 12
== ПОСЛЕ ПЕРЕЗАПУСКА ==
  проверено 24 из 24, зелёных 24
ИТОГ: 24/24 до · 24/24 после · 12 клеток до · 12 клеток после → ЗЕЛЁНО ✅   (rc=0)
```

**ОТРИЦАТЕЛЬНАЯ ПОЛОВИНА — критерий СПОСОБЕН провалиться, и это показано числом.** На той же
живой копии:
```
2026-09-28 | принимающих в списке: 14 | Ольга Рыжая: ЕСТЬ
2026-10-01 | принимающих в списке: 13 | Ольга Рыжая: нет
2026-10-12 | принимающих в списке: 13 | Ольга Рыжая: нет
2026-10-15 | принимающих в списке: 14 | Ольга Рыжая: ЕСТЬ
активных преподавателей в базе: 14
```
Без этой половины зелёные 24 проверки были бы зелены и у пустой школы.

**ТЕСТЫ.** Новый файл `tests/veb/test_otsutstvie_prepodavatelya.py` — **41 тест, все
зелёные** (в том числе 12 дней × 2 версии параметризацией, отказы двери на кривой дате,
перевёрнутом периоде, выдуманной причине и несуществующем преподавателе, 403 без куки и
под ролью `prepod`, снятие отметки, и перезапуск сервера внутри одного теста).

**ВСЯ ПАПКА `tests/veb/`** (без трёх браузерных файлов, которым нужен playwright и
`SPETSMAT_BAZA`): `207 passed, 8 failed, 9 skipped`.
🔴 **Эти 8 красных — НЕ мои, и это ЗАМЕРЕНО, а не предположено.** Прогнал те же файлы на
`main` в отдельной отцепленной рабочей папке (`git worktree add --detach`, `b921b26`):
**тот же список из 8, файл в файл, тест в тест** (`test_server.py` — 7, `test_priyom.py` — 1).
Папка после замера удалена.

**`tests/veb/test_kanon_verstki.py` — 13 ошибок НА SETUP**, все
`config.IstochnikNeNazvan: переменная среды SPETSMAT_BAZA не выставлена`. Тоже не моё
(фикстура требует названного источника), но означает, что канон вёрстки по умолчанию молчит —
пункт 7 в `## ВОПРОСЫ`.

### ЧЕГО Я НЕ СДЕЛАЛ — СПИСКОМ, И ПОЧЕМУ

* **Отказ ДВЕРИ ЗАПИСИ на пришедший запросом выбор** (вторая половина §4 задания: *«если
  выбор всё же придёт запросом (старая вкладка), дверь записи ОТКАЗЫВАЕТ с внятной
  причиной»*). Обе двери — вне зоны: слой занятия в `veb/server.py:1583`, постоянный слой в
  `core/services/enrollment.py::enforce_calendar_and_ceiling`. Правка выписана дословно в
  пунктах 1 и 2 `## ВОПРОСЫ`, чтобы её не пришлось выводить заново. **Сегодня старая
  вкладка запись ПРОВЕДЁТ** — список сужен, дверь нет.
* **Карточки преподавателей на вкладке группы и слово «отсутствует» на вкладке
  принимающих** читают только `teacher_attendance` и периода не видят
  (`veb/razdely/gruppy.py:68`, `veb/razdely/prepodavateli.py:226`). Одна строка в каждом,
  оба вне зоны — пункты 4 и 5.
* **Будущие дни периода не становятся СТОЛБЦАМИ решётки** — отбор столбцов живёт в
  `core/services/istoria_poseshchenij.py`, вне зоны. Вместо этого сделана полоса дней
  (пункт 6 и урок фабрике).

### ЧТО НЕ ТРОГАЛ
Ничего вне зоны: `veb/server.py`, `core/`, `infra/`, `tools/`, `docs/`, `veb/razdely/*`
кроме `shkolniki.py` и `istoria_zanyatij.py` — не изменены ни байтом (`git show --stat` по
каждому коммиту несёт только пути зоны). Новых `.md` не заводил, поэтому `register_doc.py`
не звался и `_studio/docs/KARTA.md` не трогался.

### НЕОБРАТИМОЕ
* **Прогон через `git stash push -u` и обратно.** Чтобы сравнить красные тесты с `main`, я
  на минуту убрал незакоммиченную правку файла-захода в стеш и вернул её `stash apply` по
  SHA, затем удалил запись. · где: `zhurnal/2026-09-02_spetsmat-bot/kod_otsutstvie-prepodavatelya.md`
  · чем восстанавливается: уже восстановлено (`git stash apply 3486767…`, запись `stash@{0}`
  удалена, `git stash list` пуст); правка целиком лежит в коммите отчёта. Приём назван
  вслух, потому что стек стеша общий с соседними рабочими папками — риск был, ущерба нет.
* **Временная отцепленная рабочая папка** `…/scratchpad/baza-main` на `main` для замера
  чужих красных · удалена `git worktree remove --force`, `git worktree list` её не
  показывает.
* **Копия боевой базы** в личный scratchpad (`progon.db`). В саму боевую базу
  `/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/data/spetsmat.db` не записано ничего —
  копия снята штатной дверью, сервер прогона поднимался с `SPETSMAT_BAZA=<копия>`.
* Ничего не удалено, не переименовано и не перезаписано в репозитории. **Другого
  необратимого нет.**

### ПОВТОРЯЕМОСТЬ НАХОДОК
* **ПОВТОРИТСЯ на следующем заходе этой волны, то есть это заход, а не запись в очередь:**
  критерий готовности, требующий N клеток на экране, который этих клеток по устройству
  данных дать не может (урок фабрике ниже). Волна идёт по одному шаблону критериев, и
  следующий заход по журналу упрётся в то же самое.
* **ПОВТОРИТСЯ:** восемь красных тестов `test_server.py`/`test_priyom.py` на `main` —
  каждый следующий исполнитель этой зоны потратит те же 10 минут, чтобы выяснить, что они
  не его. Их надо либо починить, либо пометить `xfail` с причиной.
* **НЕ повторится** (законно уходит пунктами очереди): двери записи, карточки групп,
  слово «отсутствует» на вкладке принимающих, столбцы будущих дней — это конкретные места
  конкретной фичи, а не форма работы.

### ПОЛНАЯ ГИТ-ГИГИЕНА ПОСЛЕДНИМ ХОДОМ — ЧИСЛА КОМАНДАМИ, А НЕ ПАМЯТЬЮ

**1 · ВСЕ КОММИТЫ.** Восемь коммитов, все по путям зоны (`git show --stat` каждого несёт
только их). Вне git:
```
/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot-wt/otsutstvie-prepodavatelya : 0
/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot                              : 15
```
🔴 **Эти 15 — ЧУЖИЕ и содержательные, я их не трогал и трогать не имею права:**
`README.md`, `SERDCE-VOLNY-noch2.md`, `PULS-CHASOVOGO-noch2.log`, `SESSIYA.md`,
`SOSTOYANIE.md`, `.chasovoj-zamki/okon-bylo`, `zhurnal/_INFRA-git/INCIDENTY.md`,
`HANDOFF-2026-09-12.md`, четыре файла заявок, `.DS_Store` ×2 и
`scratchpad/verifikator/` (чужая папка от 10.09 20:10–20:18, к моему верификатору
отношения не имеет — мой работал сегодня и вне репозитория). Это живая бухгалтерия
волны в руках оркестратора. Моей зоны среди них нет ни одного файла.

**2 · ВЛИТИЕ.** `git_zona.py vlit-v-osnovnuyu` с шестью `--zone` →
**✅ влито в `main` без конфликтов: `64a97d3`**, затронуто путей 6, новых исполняемых
файлов 1 (`tests/veb/test_otsutstvie_prepodavatelya.py`, «встроен»). Инструмент сам
напечатал предупреждение, что 16 грязных путей главной папки в merge-коммит не поедут, —
и они не поехали.

**3 · ПОСТ-ПРОВЕРКА ИЗ ГЛАВНОЙ ПАПКИ — механизм ВСТАЛ, а не «коммит виден».** Прогон
`PROGNAT.py` целиком из `/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot` на СВЕЖЕЙ
копии боевой базы:
```
ОТМЕТКА через живую дверь /api/otsutstvie: (200, {'ok': True, 'id': 1, 'dnej': 12})
клеток особого вида: 12 — 2026-10-01 … 2026-10-12
  проверено 24 из 24, зелёных 24
клеток особого вида после перезапуска: 12
  проверено 24 из 24, зелёных 24
ИТОГ: ЗЕЛЁНО ✅   (rc=0)
```
🔴 **Эта копия БЕЗ применённой миграции 013 — ровно в том состоянии, в каком боевая база
находится сегодня.** Таблицу завёл сам механизм при первом рендере
(`karkas.obespechit_otsutstvia`). То есть проверено не «работает после миграции», а
«работает на сегодняшней боевой схеме».
Грепы по ЖИВЫМ точкам вызова, в главной папке:
```
veb/server.py:121               "veb.razdely.istoria", "veb.razdely.istoria_zanyatij",
veb/razdely/istoria_zanyatij.py:1217        "/api/otsutstvie": dver_otsutstvia}
veb/obshchee/karkas.py:552      kt.otsutstvie_po_dnyam = {dat: otsutstvuyushchie_na_datu(c, dat)
veb/razdely/shkolniki.py:311    net_v_etot_den = otsutstvuyushchie_v_slot(kt, sl)
veb/razdely/shkolniki.py:381    r["teacher_id"] and r["teacher_id"] in otsutstvuyushchie_v_slot(kt, sl))
```
Отката не потребовалось: пост-проверка зелёная.

**4 · ГАШЕНИЕ.** Невлитых `zahod/*`-веток осталось **1**, поимённо:
`zahod/zhurnal-setka` — ЖИВОЙ соседний заход той же волны, он вливает себя сам последним
ходом, как и я. Две другие, стоявшие невлитыми в середине моей работы
(`kabinet-plitki`, `konduit-galochki-i-podskazki`), влились сами, пока я работал.
Ветку-витрину не вливал: её здесь нет.

**5 · ВЫВОЗ.** Своя ветка вывезена: `git push -u origin zahod/otsutstvie-prepodavatelya` →
`* [new branch]`, и `git log --oneline @{u}.. | wc -l` → **0**.
🔴 **`main` НЕ вывезен, невывезенных в нём 42, и НОВОЙ заявки я не ставлю — она уже
открыта и не моя.** Заявка от 2026-09-07T16:02, адресат ВЛАДЕЛЕЦ: вывоз `main` отбивается
открытым инцидентом с живым токеном бота в ПУБЛИЧНОМ репозитории, разблокируется
действием человека (`/revoke` в BotFather). Обходить её `--vsyo-ravno` значило бы
опубликовать поверх открытого инцидента с секретом — это решение владельца о
безопасности, а не операция захода. Дубль заявки не ставлю сознательно: очередь
сверяется машинно, а второй записью о том же я бы только спрятал первую.

**6 · ЧИСЛА ОДНОЙ ТАБЛИЦЕЙ**

| что | число |
|---|---|
| вне git · рабочая папка захода | **0** |
| вне git · главная папка | **15** (все чужие, поимённо выше) |
| невлитых `zahod/*` | **1** (`zahod/zhurnal-setka`, живой сосед) |
| невывезенных СВОЕЙ ветки | **0** |
| невывезенных `main` | **42** (блокирует чужая открытая заявка от 07.09) |
| пост-проверка | **зелёная**, отката не было |

### 🔴 ПОСЛЕДНЕЕ СОСТОЯНИЕ ГЛАВНОЙ ПАПКИ — ЧУЖОЙ ОТКРЫТЫЙ КОНФЛИКТ, НЕ МОЙ, И НЕ ЧИНЮ

Через минуту после моего влития `git_zona.py check` покраснел на трёх путях зоны. Причина
снята фактом, а не догадкой: в ГЛАВНОЙ папке идёт ЧУЖОЕ слияние, прямо сейчас.
```
$ cat .git/MERGE_HEAD                     → cc6e1fa693b3a0f446296c1fa2dbdd817f4120df
$ git branch --contains cc6e1fa           → + zahod/zhurnal-setka
$ head -1 .git/MERGE_MSG                  → Merge branch 'zahod/zhurnal-setka'
$ git status --porcelain | grep veb/      → UU veb/razdely/istoria_zanyatij.py
$ ls -la .git/MERGE_HEAD                  → Sep 11 12:13   (сейчас 12:14)
```
Соседний заход той же волны правит ТОТ ЖЕ файл журнала и разрешает конфликт в эту минуту.
По §4 это ровно тот случай: *«чужое состояние репозитория НЕ чини»*. Не трогал ничего.

**МОЯ РАБОТА ПРИ ЭТОМ В `main` УЖЕ ЛЕЖИТ — проверено по КОММИТУ, а не по рабочему дереву**
(`git show 4789ea1:<файл> | grep -c`):
```
veb/razdely/istoria_zanyatij.py              15 совпадений
veb/obshchee/karkas.py                       22
veb/razdely/shkolniki.py                      6
migrations/013_otsutstvie_prepodavatelya.sql  5
tests/veb/test_otsutstvie_prepodavatelya.py  21
```
Мои слияния: **`64a97d3`** (код) и **`4789ea1`** (отчёт), оба «без конфликтов».

🔴 **ЧТО ПРОВЕРИТЬ ПРИЁМКЕ ПЕРВЫМ ХОДОМ, И ПОЧЕМУ ИМЕННО ЭТО.** Сосед разрешает конфликт
в `veb/razdely/istoria_zanyatij.py` — файле, половина которого моя. Разрешение «выбором
стороны» молча уничтожит либо его правку, либо мою (дверь `/api/otsutstvie`, полоса дней,
клетка `ist-otsut`, список «остались без принимающего»). Сверить одной командой:
```
git -C /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot show main:veb/razdely/istoria_zanyatij.py | grep -c 'dver_otsutstvia\|ots-polosa\|ist-otsut'
```
Ноль или заметно меньше пятнадцати — мою половину потеряли при разрешении конфликта;
восстанавливается из `64a97d3` и из `origin/zahod/otsutstvie-prepodavatelya`.

**ЭТА СЕКЦИЯ ОСТАЛАСЬ НА ВЕТКЕ И В `origin`, А НЕ В `main`,** и это законный исход, а не
забывчивость: влить её я не могу, пока в главной папке открыто чужое слияние — влитие
отказывает на грязном дереве, а чинить чужой конфликт мне запрещено. Ветка вывезена
(`origin/zahod/otsutstvie-prepodavatelya`, невывезенных 0); секция доедет в `main` тем же
`git_zona.py vlit-v-osnovnuyu`, как только сосед закроет своё слияние. Всё СОДЕРЖАТЕЛЬНОЕ
(код, миграция, тесты, весь остальной отчёт) в `main` уже стоит — см. числа выше.

### ВРЕМЯ ПРОГОНА И ТОКЕНЫ
**НЕПРИМЕНИМО:** движок `opencode`, счётчика стоимости в логе нет.

### ПРАВКИ ПРОЧИТАНЫ
Блок `## ПРАВКИ ПОСЛЕ ВЫДАЧИ` пуст (`<правок нет>`) — заход не правился с момента выдачи.

### ОТКРЫТОЕ «ВОЗВРАЩАТЬСЯ»
Две двери записи (пункты 1–2 `## ВОПРОСЫ`) — до них старая вкладка проводит запись на
отсутствующего человека. Это самое дорогое из оставшегося и единственное, что стоило бы
взять следующим заходом сразу.

### РЕЗУЛЬТАТ ВЕРИФИКАТОРА §3

Тип — ПОСЛЕ. Свежий субагент, СВОЙ прогон другим методом: своя копия боевой базы, свой
сервер на своём порту, отметка через HTTP-дверь, свои скрипты. Финальная строка получена
дословно: **«выдано 127 позиций из 127 найденных»** — ответ не усечён.

**ВЕРДИКТ ВЕРИФИКАТОРА: утверждение ПОДТВЕРЖДАЕТСЯ, охват 123 проверки из 127 прошли,
2 неприменимы, 2 — находки ниже; ни одна проверка не провалилась.**

* **(A) 24 из 24.** На учебных днях периода (01.10 чт, 05.10 пн, 08.10 чт, 12.10 пн)
  список **13** вместо 14. Сильнее моего скрипта: он взял НАСТОЯЩИЙ HTML по HTTP и
  посчитал `<option>` — `/raspredelenie?den=2026-10-01` дал **99 → 0** опций «Ольга
  Рыжая» при контроле «Андрей Рябичев» 99 → 99; главная страница при периоде, накрывшем
  ближайшие пн/чт, **198 → 0**. `tekushchij=13` её не возвращает (5 дней).
* **(B) 12 клеток, ровно те дни**, `title="болезнь · 01.10–12.10"`, крестиков в строке
  Ольги ноль. Отдельно проверил вид клетки РЕШЁТКИ, отметив период 08–11.09: клетка за
  10.09 перешла `ist-byl/✓` → `ist-otsut/О`.
* **(C) переживает перезапуск** — повторил всё целиком, снова 24/24 и 12 клеток.
* **(D) проверка способна провалиться:** 15.10, 28.09, 19.10, 22.10 — список 14, Ольга
  ЕСТЬ.
* **Попытки сломать (его главная работа):** кривые даты/причина/`teacher_id`/не-JSON →
  400/404 и **0 строк записано**; POST без куки и под ролью `prepod` → 403, 4 из 4;
  `GET /api/otsutstvie` → 405; после снятия отметки Ольга вернулась в список, а
  **`enrollment` побайтово тот же** (108 строк, SHA `acd6f982…`, все 8 строк с
  `teacher_id 13` целы); два пересекающихся периода легли оба и снимаются по одному;
  отметка соседу не протекает на Ольгу; **база БЕЗ миграции 013 — а боевая сейчас именно
  такая — заводит таблицу сама при первом рендере, и `CHECK`-и на ней живы.**

**ДВЕ НАХОДКИ ВЕРИФИКАТОРА, ОБЕ ПОЧИНЕНЫ ТУТ ЖЕ — коммит `1426974`:**

1. **Кнопка «снять» рисовалась ВСЕМ.** Форма отметки пряталась от преподавателя
   правильно, а кнопок «снять» под ролью `prepod` было ТРИ на три периода. Дверь
   нажатие отбивает (403, замерено четырьмя запросами), данные не пострадали бы никогда,
   но орган правки, показанный тому, кто править не может, обещает действие, которого не
   будет — ровно против правила, записанного в докстринге `stranica()`. Починено, и
   сторожится тестом `test_knopki_snyat_u_neorganizatora_net` (3 кнопки у организатора,
   0 у преподавателя, сами отметки видны обоим).
2. **Комментарий миграции 013 обещал больше, чем даёт механизм:** «a date that is not a
   date has to be refused by the база, not by the caller». Неверно — `glob` проверяет
   ФОРМУ, и прямой `insert` с `s_daty='2026-13-45'` прошёл. Существование дня проверяет
   ДВЕРЬ (`strptime`), а не база. Обещание исправлено, а не удалено: строка, обещающая
   больше механизма, опаснее отсутствующей. Тот же класс и та же правка, что «ПОПРАВКА
   ОРКЕСТРАТОРА 10.09» в миграции 012.

**УТОЧНЕНИЕ ВЕРИФИКАТОРА ПО (B), И ОНО СПРАВЕДЛИВО.** Формулировка критерия «в журнале
преподавателей 12 клеток особого вида» читается шире, чем есть на самом деле: 12 клеток —
это **полоса дней периода** (`.ots-polosa`) в панели отметок, а не ячейки решётки.
В решётке на 11.09 один столбец (10.09), октябрьских столбцов в ней нет ФИЗИЧЕСКИ — они
строятся из прошедших `sessions`. Класс и счёт верны, но читать это надо именно так; почему
иначе нельзя внутри зоны — пункт 6 `## ВОПРОСЫ` и урок фабрике выше.

### ТРЕТЬЯ НАХОДКА — МОЯ СОБСТВЕННАЯ, ВСКРЫТАЯ МОЕЙ ЖЕ ПРАВКОЙ (тот же коммит `1426974`)
Строка модуля `veb/razdely/istoria_zanyatij.py` несёт внутри обычной (не сырой) строки
последовательность `\|` — грепом в цитате. Python пока только предупреждает, но pytest
умеет поднимать предупреждения до ошибок, и тогда падает не тест, а ИМПОРТ модуля, то есть
весь файл тестов разом. Поймано живьём: первая же компиляция после правки (пустой
`__pycache__`) увела в красное 42 зелёных теста с `SyntaxError: invalid escape sequence`,
а второй прогон, уже из кэша, был зелёным. **Ловушка срабатывает ровно на чистой машине и
молчит на своей.** Строка сделана сырой; `python3 -W error -c "import …"` теперь чист.

### ЗАМЕР В БРАУЗЕРЕ (playwright, 1440×900, живая копия базы)
```
skroll_po_gorizontali : false        (ширина документа ровно 1440 — канон, правило 4)
forma_vidna           : true
kletok_vidno          : 12
cvet_kletki           : rgb(201, 116, 58)   — тёплый, не приглушённый `--faint`
fon_kletki            : var(--warm) 14 %    — клетка ПОМЕЧЕНА, а не ослаблена
siroty                : «остались без принимающего: 3 — Быков Владислав, Кудишин Андрей, Фёдоров Михаил»
```
Снимок экрана: `/private/tmp/claude-501/-Users-ivanyakovlev-Documents-GitHub-spetsmat-bot-wt-otsutstvie-prepodavatelya/d862f339-1f93-437a-a592-bb091c2528c5/scratchpad/zhurnal-1440x900.png`
(временная папка сессии — она исчезнет; страница пересобирается командой из строки АРТЕФАКТ).

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

**ВЕТКА РАБОТЫ:** `zahod/otsutstvie-prepodavatelya`
*(проверяется фактом, не словом: ветка обязана существовать и быть либо ВЛИТА в основную, либо названа в открытой заявке на влитие. Ни того, ни другого — Г14 краснеет. Снять состояние: `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py poteri --branch <ветка>`)*

**ЗАЯВКИ, ПОСТАВЛЕННЫЕ ЭТОЙ ПРИЁМКОЙ — ПРОДУБЛИРУЙ СЮДА ТО, ЧТО УЖЕ ЛЕЖИТ В СПИСКЕ:**
> Адрес списка: `/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/zhurnal/_INFRA-git/zayavki`
> Читается командой (из любой папки, в том числе из worktree): `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py zayavki`
> Ставится командой: `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py zayavka --rod <git-operaciya|pravka-koda> "<текст>"`
> 🔴 Вопрос здесь НЕ «что ты хочешь сделать», а «что ты УЖЕ положил в очередь». Дубль сверяется с очередью по id машинно; намерение сверить не с чем.

- `<id заявки>` — `<род>` — `<суть одной строкой: влитие / коммит / вывоз / деплой / гашение>`

*(Заявок эта приёмка не ставила — так и напиши строкой «заявок нет: <почему ни одна из пяти операций не понадобилась>». Пустая строка и прочерк не принимаются: молчание неотличимо от «забыл».)*


## 🔴 ЗАДАЧА — ИЗ РЕЦЕНЗИИ ВЛАДЕЛЬЦА 11.09, ЧИТАЙ ЭТО ГЛАВНЫМ

Источник — голосовая рецензия владельца по живому сайту (`~/Downloads/сайт рец.md`).
Ниже пункты РАЗНЕСЕНЫ по позициям; твои — только те, что в этом файле. Чужого не трогай.
Живой сайт: http://math-kluychiki.ru (он же 159.194.254.52). Локально поднимается так:
`SPETSMAT_BAZA=<копия базы> SPETSMAT_VEB_SECRET=<любая строка> PYTHONPATH=. python3 -m veb.server --port <порт>`
Копия боевой базы для прогона: `data/spetsmat.db` (57 школьников, 15 847 отметок) — СНИМИ КОПИЮ
и работай с ней, в саму базу не пиши.

### ЧТО ИМЕННО ПРОСИТ ВЛАДЕЛЕЦ (его слова, не пересказ)

«Есть Ольга Александровна, Ольга Рыжая, которая не будет с 1 по 12 октября. И это должно быть
возможность отметить… чтобы это было видно, и чтобы в будущих всех распределениях период этот
на всех занятиях этого периода уже не появлялось в списке преподавателей. Чтобы было понятно,
что ей нельзя в текущем распределении на любое число между первым и двенадцатым октября нельзя
добавлять школьников, потому что её просто физически нет… Должна быть очень важная система, в
которой мы можем отмечать, что человека не будет. Мы можем отмечать это в текущем распределении,
что он заболел, а можем отмечать это в распределении на будущее. И чтобы это сразу выделялось
в журнале преподавателей.»

### ЧТО ЭТО ЗНАЧИТ ПО ЧАСТЯМ — КАЖДАЯ СВОИМ КОММИТОМ

1. **ХРАНИЛИЩЕ.** Период отсутствия — строка в базе: кто, с какой даты, по какую, почему
   (болезнь/отъезд/иное), кто отметил, когда. Миграция — твоя зона. Один преподаватель может
   иметь несколько периодов; периоды могут пересекаться с уже проставленными назначениями —
   что делать с УЖЕ назначенными на эти дни школьниками, реши и НАЗОВИ в отчёте (предложение:
   не удалять молча, а показать организатору список «эти дети остались без принимающего»).
2. **ОТМЕТИТЬ.** Из журнала преподавателей: выбрать преподавателя, назвать период, сохранить.
   Работает и назад («заболел сегодня»), и вперёд («не будет с 1 по 12 октября»).
3. **ВИДНО.** В журнале преподавателей клетки дней периода — ОТДЕЛЬНЫЙ ВИД, а не пустота:
   пустая клетка уже значит «не отмечено», и спутать эти два состояния нельзя.
4. **ДЕЙСТВУЕТ.** На КАЖДЫЙ день периода преподаватель исчезает из списка принимающих — в обеих
   версиях распределения (по занятию и постоянное). Не «серым», а отсутствует в выборе; если
   выбор всё же придёт запросом (старая вкладка), дверь записи ОТКАЗЫВАЕТ с внятной причиной.
5. **ПЕРЕЖИВАЕТ ПЕРЕЗАГРУЗКУ.** Проверяется прогоном: отметил → перезапустил сервер → смотришь.

### КРИТЕРИЙ ГОТОВНОСТИ, ПРОВЕРЯЕМЫЙ КОМАНДОЙ
На копии боевой базы отмечен период Ольги Рыжей 01.10–12.10. Дальше — числа с охватом:
проверено 12 из 12 дней периода × 2 версии распределения = 24 проверки, в каждой её нет в списке
принимающих; в журнале преподавателей 12 клеток особого вида; после перезапуска сервера всё то же.
