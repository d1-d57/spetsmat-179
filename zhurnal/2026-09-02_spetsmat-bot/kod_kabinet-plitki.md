# Канал исполнителя — kabinet-plitki (один заход до конца)
> Твой единственный файл-заход. Читай ТОЛЬКО его и названные якоря; проект не изучай.
<!-- собран bootstrap_zahod.py -->
> План/вопросы/отчёт — в секции внизу. Метрика — КАЧЕСТВО. Часы — норма.
> **Модель: Opus 5** — раскладка кабинета на четверть и формат индивидуального кондуита — то, что владелец судит глазами.

## СТАРТОВОЕ СООБЩЕНИЕ ВЛАДЕЛЬЦУ

> Это блок для владельца — то, чем тебя запустили. Исполнителю здесь делать нечего, твоё задание ниже.

```
cd /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot && opencode run --auto --model openrouter/anthropic/claude-opus-5 'Твой заход — файл /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/zhurnal/2026-09-02_spetsmat-bot/kod_kabinet-plitki.md. Прочитай ТОЛЬКО его и то, что он называет; остальной проект не изучай. План/вопросы/отчёт пиши в этот же файл внизу (## ПЛАН / ## ВОПРОСЫ / ## ОТЧЁТ). Ничего сверх задачи не трогай — «ничего сверх задачи» относится к СОДЕРЖАНИЮ работы; git-контур §0.1 — законное исключение, он про состояние репозитория и исполняется целиком.' < /dev/null 2>&1 | tee /tmp/zahod-kabinet-plitki.log
```

🔴 БЛОК ВЫШЕ — МАШИННЫЙ: его достаёт и запускает надзорный оркестратор, подменив в нём модель на живую. РУКАМИ ЕГО НЕ ЗАПУСКАЮТ — запуск без надзора и был тем, чем оплатили ночь на 05.09 (три позиции из шести не изменили ни байта: модели выгорели по квоте, а перевыбирать их было нечему).

ЗАПУСКАТЬ — ЭТИМ (проба живости и перевыбор модели внутри):
```
cd /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot && python3 /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/_generator/tools/orkestr.py zhurnal/2026-09-02_spetsmat-bot --rezhim progon --dvizhok opencode --rod suzhdenie --model openrouter/anthropic/claude-opus-5 --zahody kod_kabinet-plitki.md 2>&1 | tee /tmp/nadzor-kabinet-plitki.log
```

── СЧЁТ НЕЗАКРЫТОГО (печать, не гейт) ──
ГРАНИЦА ОБЛАСТИ: сырые подстроки в `kod_*.md` (пункт 4) — НЕ парсер очереди `dostavit_urok` (который считает только пары ДОМ:/ДОСТАВЛЕНО:). Разница в числах — законна.
🔴 снимок при сборке 2026-09-11, ПРОВЕРЬ ПЕРВЫМ ХОДОМ: `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/schet_nezakrytogo.py zhurnal/2026-09-02_spetsmat-bot`
Область: «zhurnal/2026-09-02_spetsmat-bot» — сужены пункты 1, 3, 4; долги (2) глобальны намеренно (DOLG.md не размечен по записям).
Приоритет владельца: разобрать инциденты важнее, потом закрыть долги — неразобранный инцидент это повторяющаяся ошибка, долг может подождать.
  1. инцидентов без вердикта             : 0
  2. долгов СТАТУС: ЖИВ                  : н/д — ни одного skills/*/DOLG.md нет на диске (другой git-репозиторий)
  3. уроков фабрике без ВЕРДИКТ          : 59
  4. пунктов очереди «ДОСТАВЛЕНО: нет»   : 610
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

1. убрать сводную фразу про «2 из 3» целиком, «сдач» заменить на «задач», род глагола по полу: сдала и приняла
2. будущие занятия — пустые плитки с кнопкой «меня не будет»; кондуит за занятие вызывается видимой кнопкой

## КОНТРАКТ ЗОНЫ (обязателен — не удалять; вписан Cowork)
- **МЕСТО РАБОТЫ:** ветка `zahod/kabinet-plitki` в основной папке. 🔴 Она должна УЖЕ стоять. НЕ на ней — СТОП, НЕ делай `git checkout`: в общей папке он МОЛЧА откатывает дерево к состоянию ветки (цена 27→28.07: файл сильно откатился ночью, поймал владелец вручную; след в git НЕ остаётся). Тогда заход пересобрать с `--worktree`. Ветку не переключай, в другие НЕ коммить.
- **ЗОНА (можно менять):** `veb/razdely/kabinet.py` `veb/razdely/lichnaya.py` `veb/obshchee/karkas.py` `tests/veb/` `zhurnal/2026-09-02_spetsmat-bot/kod_kabinet-plitki.md`. Всё вне — **READ-ONLY**: не править, не двигать, не удалять, не рефакторить «заодно».
- 🔴 **ЗАВЁЛ НОВЫЙ `.md` — РЕГИСТРИРУЕШЬ ЕГО САМ, ТЕМ ЖЕ ХОДОМ, ОДНОЙ КОМАНДОЙ:** `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/register_doc.py <путь> "<описание>"` (из корня репо). `_studio/docs/` тебе по-прежнему READ-ONLY **для правки руками** — дверь ровно одна, и это она. Дверь идемпотентна (повторный вызов дубля не заведёт) и отказывает на пути вне `_studio/`, на несуществующем файле и на пустом описании. Свой файл-заход регистрировать не нужно: он рождается зарегистрированным из `bootstrap_zahod.py`. **Красный хук на ТВОЁМ новом `.md` — это не повод для `--no-verify`, а повод позвать дверь.** *Почему правило существует и почему оно теперь исполнимо: 26.07 оно записано с ценой в пять документов-сирот и через два дня повторилось дословно. Дальше стало хуже: до 30.07 указания «зарегистрируй» и «`docs/` только на чтение» противоречили друг другу, выход был ровно один — обойти хук, и по автологу `_INFRA-git/INCIDENTY.md` это 28 обходов `--no-verify` из 56 срывов коммита, 27 из них по одной этой причине (48 % всей боли с коммитами, тринадцать исполнителей подряд). Обходить больше нечего.*
- **КОММИТ:** два хода — `add` по своим путям, затем `commit` **с теми же путями после `--`** (полная форма и цена каждого хода — §4); коммить ПО ХОДУ работы, не одним последним ходом (§4). НИКОГДА `-A` / `.` / `commit -am`, и никогда `commit` без путей. Субагенты не коммитят. **`--no-optional-locks` обязателен:** обычный git переписывает индекс, берёт `.git/index.lock` и роняет параллельный ручной коммит владельца.
- **SCRATCHPAD — ТОЛЬКО ЛИЧНЫЙ.** Черновики, выкладки, промежуточные версии — в личную папку СВОЕГО захода `scratchpad/kabinet-plitki/`. Общие пути (`scratchpad/otchet.md`, любой `scratchpad/*` без имени твоей темы) ЗАПРЕЩЕНЫ: чужой отчёт уедет в твой файл или твой — в чужой, а приёмка читает отчёт без построчной сверки и подмену НЕ ЛОВИТ по построению. *Цена 25.08: готовый `## ОТЧЁТ` захода konvejer-incidentov был записан в общий `scratchpad/otchet.md`, и 92 строки чужого отчёта простояли в `kod_slovari-v-kod.md`.*
- 🔴 **Звал `register_doc.py` — допиши `_studio/docs/KARTA.md` к своим путям В ОБОИХ ходах.** Строка регистрации лежит физически в нём. Ворота 5 читают `§6` **с диска**, а не из индекса: коммит без этого файла пройдёт ЗЕЛЁНЫМ, документ уедет сиротой, а строка умрёт при первом `checkout` (дата данных 2026-07-30, найдено верификацией захода «kod_registracia-bez-obhoda.md»).
- **ЗАПРЕТ:** ничего за пределами зоны, даже если «мешает» или «чинится в одну строку». Нашёл проблему вне зоны → в отчёт, не трогай.

## 0. ПЕРВЫЙ ХОД
### 0.1 🔴 ГИТ-КОНТУР — ДО ВСЕГО ОСТАЛЬНОГО, И ПЕРВЫМ ХОДОМ ЦЕЛИКОМ

🔴 «ничего сверх задачи» относится к СОДЕРЖАНИЮ работы; git-контур §0.1 — законное исключение, он про состояние репозитория и исполняется целиком.

🔴 **ПОРЯДОК ЗДЕСЬ — ЧАСТЬ УСТРОЙСТВА, А НЕ ОФОРМЛЕНИЕ. Сначала САМ прогоняешь две команды самопроверки контура (пункт 1 ниже), и только ПОТОМ заводишь свою рабочую папку** — её ветка отпочковывается от основной такой, какая она есть на момент запуска: контур пуст, доносить инструмент влитием нечего.

**1. ВЕСЬ КОНТУР ПУСТ — САМОПРОВЕРКА ВМЕСТО СУБАГЕНТА.** При сборке проверены три числа контура, и все три нулевые: невлитых `zahod/*`-веток 0 (🔴 снимок при сборке 2026-09-11, ПРОВЕРЬ ПЕРВЫМ ХОДОМ: `git --no-optional-locks branch --no-merged main | grep -c 'zahod/'`); открытых заявок 0 (снимок при сборке 2026-09-11, пересчитать самому: `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py zayavki`); названных `--vlit` 0. Звать субагента не за чем — выполни САМ две команды и вставь их вывод в `## ОТЧЁТ` дословно:
```
git --no-optional-locks branch --no-merged main | grep -c 'zahod/'   # снимок при сборке 2026-09-11: 0
python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone veb/razdely/kabinet.py veb/razdely/lichnaya.py veb/obshchee/karkas.py tests/veb/
```
Первая вернула не 0 — НИЧЕГО чужого не вливай (свою ветку вольёшь последним ходом, см. ниже), назови число строкой в `## ОТЧЁТ` и работай дальше. Вторая красная — сначала приведи в порядок свою зону.

Если при следующей сборке хоть одно из трёх чисел окажется ненулевым, генератор сам вернёт сюда задание субагенту гит-контура — печатает его дверь `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/bootstrap_zahod.py --zadanie-subagentu`; звать его в этом заходе не надо.

🔴 ОТВЕТ ЛЮБОГО субагента, которого ты запускаешь (не только этого), обязан КОНЧАТЬСЯ строкой «выдано N позиций из M найденных»: канал мог оборвать его молча, и без этой строки усечение неотличимо от честного «мало нашлось». Нет строки — ответ усечён, в `## ОТЧЁТ` не вставляй, перезапроси.

**2. ТЕПЕРЬ ЗАВОДИ СВОЮ РАБОЧУЮ ПАПКУ** (команда — в блоке «МЕСТО РАБОТЫ» выше) и работай в ней как обычно. Её ветка отпочкована от свежей основной, поэтому инструмент, которым ты работаешь, уже на диске — отдельного «влить перед работой» больше нет.

вливать нечего, проверено командой `git branch --no-merged` — но проверено ПРИ СБОРКЕ, а не сейчас: невлитых `zahod/*`-веток было 0. 🔴 снимок при сборке 2026-09-11, ПРОВЕРЬ ПЕРВЫМ ХОДОМ: `git --no-optional-locks branch --no-merged main | grep -c 'zahod/'`. Число могло устареть между сборкой и твоим прогоном — 14.08 заход нёс ровно этот ноль, а к прогону невлитых было три.


- деплоя в этом заходе нет.

- Проверь ветку: `git branch --show-current` — обязано быть `zahod/kabinet-plitki`. Не она — СТОП, `git checkout` НЕ делай (§4 GIT-disciplina), нужен `--worktree`.
- Точка отката: `git add veb/razdely/kabinet.py veb/razdely/lichnaya.py veb/obshchee/karkas.py tests/veb/ zhurnal/2026-09-02_spetsmat-bot/kod_kabinet-plitki.md` → commit (или zip), если зона не чиста в HEAD (не фабрикуй, если чиста).
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

Верификатор нужен, тип — **ПОСЛЕ-типа** — судит результат, стоит в конце, после задачи. Свежий субагент, ДРУГИМ методом (прогон по живой копии базы: пересчитать плитки против занятий четверти, развернуть три прошедшие), не перечитывает свою же правку. Доля сплошной выборки: 16 из 16 занятий четверти и 3 из 3 развёрнутых плиток. Финальная строка ответа обязательна дословно: «выдано N позиций из M найденных» — без неё ответ считается усечённым и в отчёт не вставляется.

## 4. 🔴 КОММИТ СВОЕЙ ЗОНЫ — ПО ХОДУ РАБОТЫ, НЕ ОДНИМ ПОСЛЕДНИМ ХОДОМ
Ты работаешь host-side и в `.git` ПИШЕШЬ — значит коммитишь САМ, никому не передавая. Каждую завершённую часть работы коммить СРАЗУ, теми же двумя ходами — не копи всё к финальному ходу:
```
git --no-optional-locks add -- veb/razdely/kabinet.py veb/razdely/lichnaya.py veb/obshchee/karkas.py tests/veb/ zhurnal/2026-09-02_spetsmat-bot/kod_kabinet-plitki.md                     # вводит НОВЫЕ пути в индекс
git --no-optional-locks commit -m "<зона>: <что сделано>" -- veb/razdely/kabinet.py veb/razdely/lichnaya.py veb/obshchee/karkas.py tests/veb/ zhurnal/2026-09-02_spetsmat-bot/kod_kabinet-plitki.md   # отсекает всё чужое
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

**ЗОНА ГИГИЕНЫ:** `veb/razdely/kabinet.py` `veb/razdely/lichnaya.py` `veb/obshchee/karkas.py` `tests/veb/` `zhurnal/2026-09-02_spetsmat-bot/kod_kabinet-plitki.md`

- **Г1. Зона доехала в git.** `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone veb/razdely/kabinet.py` → ✅; `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone veb/razdely/lichnaya.py` → ✅; `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone veb/obshchee/karkas.py` → ✅; `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone tests/veb/` → ✅; `python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py check --zone zhurnal/2026-09-02_spetsmat-bot/kod_kabinet-plitki.md` → ✅. Красное на любой из команд — отчёт не принимается: приёмка гоняет их все первым ходом.
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
python3 /Users/ivanyakovlev/Documents/GitHub/disciplina/_generator/tools/git_zona.py vlit-v-osnovnuyu zahod/kabinet-plitki --zone <своя зона> \
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
> Находка не про эту сессию, а закономерность про саму фабрику, годная другим заходам, — оформи как пункт очереди в `## ВОПРОСЫ` (формат там же) с `ДОМ: <эта арка>/UROKI-FABRIKE.md`, а не пиши прямо сюда неструктурированной строкой.
> **Не про задачу — про САМУ ФАБРИКУ.** Ты работаешь с пустым контекстом и потому видишь то, чего не видит аналитик: он писал этот заход и ему приятно, что заход хорош. Сломался ВХОД (издание не то, id врёт, зона не содержит файла с ответом)? Критерий готовности кривой? Инструкция канона противоречит живому файлу? — сюда, строкой.
> Формат жёсткий (по нему гейт): `### <что произошло>` / `ЦЕНА: <что сломалось и сколько стоило>`.
> **ЦЕНА обязательна.** Без неё это наблюдение, а не урок, и в канон оно не пойдёт. Не знаешь цены — не пиши.
> **Не сочиняй.** Пустая секция — законный отчёт. Выдуманный урок хуже отсутствующего: он попадёт в канон, который читают ВСЕ будущие проекты.

### КРИТЕРИЙ ГОТОВНОСТИ, СФОРМУЛИРОВАННЫЙ КАК `pytest -q` → `rc=0`, НЕ ПРОВЕРЯЕТ ЭКРАН, ПОЛОВИНА КОТОРОГО — СКРИПТ

ЦЕНА: пункт 8 — тот, который владелец назвал ГЛАВНЫМ, — приехал полностью нерабочим и
был зелёным у всех тридцати тестов файла. `function uzel(…)` перекрылось стоявшим выше
`var uzel = document.getElementById(…)`: `var` всплывает и перетирает объявление функции,
`pokazat` падал с `uzel is not a function`, и панель кондуита не открывалась НИ РАЗУ.
Разметка при этом была совершенно правильной, поэтому все проверки «в теле ответа есть
такая-то строка» проходили. Нашёл дефект браузерный прогон (playwright, 1440×900), то
есть тот самый «живой прогон на реальном объекте», который стоит в `§2 КРИТЕРИЙ
ГОТОВНОСТИ` этого захода. Если бы я остановился на `pytest -q` → `31 passed`, владелец
получил бы экран, где главная кнопка не делает ничего, и отчёт с честным «сделано».
Обобщение для фабрики: там, где заход правит СТРАНИЦУ, «прогон на реальном объекте» это
браузер, а не HTTP-ответ; `grep` по разметке и исполнение скрипта — разные проверки, и
первая систематически зеленее второй.

## ПЛАН — (заполняет исполнитель)

Все eight points of the owner's review touch ONE screen — `/kabinet`, drawn by
`veb/razdely/kabinet.py::stranica`.  They are done in the order they are numbered, each
its own commit, each with its own test in `tests/veb/test_kabinet.py`.

**Assumptions stated BEFORE the code, per §1.**

*A1 · THERE IS NO GENDER IN THE БАЗА, AND POINT 3 THEREFORE CHANGES SHAPE.*  Measured,
not assumed: `students` is `(id, tg_id, surname, name, class, status, first_sheet_id,
gruppa)` and `teachers` is `(id, tg_id, name, aka, is_owner, kabinet, aktiven, gruppa)`
— no column carries sex, and no other table does either (20 tables checked on the live
copy).  The заход itself forbids guessing it from the name.  So the screen stops
printing a gendered verb at all instead of printing the wrong one: `сдал N` becomes
`задач: N`, `ничего не сдал` becomes `задач нет`.  That answers what the owner actually
objected to («Бочарова Анна — она СДАЛА, а не сдал»: no wrong form is shown) and it is
the same word point 2 asks for.  Where the gender data should come from is named in
`## ВОПРОСЫ` and in `## ОТЧЁТ`.  The other gendered verb, `принято сдач`, lives inside
the summary line that point 1 deletes, so it leaves with it.

*A2 · «16 ИЗ 16» IS AN ESTIMATE, NOT A FACT OF THE CALENDAR, AND I SAY SO BEFORE I START.*
The критерий готовности asks for «плиток в четверти 16 из 16».  16 is the заход's own
arithmetic («~8 недель × 2 занятия»).  The real count is whatever the quarter's dates
and `SLOTY_ZANYATIJ` (пн, чт) produce, and no quarter calendar exists anywhere in this
repo — `grep` over `*.py` and `*.sql` finds the word «четверть» only in prose.  So I
write the quarter boundaries down once, in `kabinet.py`, as the standard grid of the
2026/2027 school year, and I report the ACTUAL number with охват — «плиток N из N, то
есть все дни занятий четверти на экране» — plus the part that is genuinely checkable and
is what the owner asked for: five columns, everything visible, no horizontal scroll.  The
boundaries themselves go to `## ВОПРОСЫ` with `ДОМ: владелец`, because only he knows them.

*A3 · THE WHOLE YEAR IS DRAWN, NOT JUST THE PAST PLUS EIGHT DAYS.*  Four tabs means four
quarters of tiles in the document.  This costs nothing new in queries: point 6 removes
the pupil list from FUTURE tiles, so a future tile needs no `deti_na_datu` call at all,
and the past is the same set of days the page already walked.

**ORDER OF WORK — one commit per point.**

1. Delete the summary line `с начала года: …` and everything computed only for it
   (`prinyato_vsego`, `deti_vsego`, `_byli_deti`, `svoi_dni`, `svodka`, `.kab-svodka`).
   Two tests assert that line and are removed with it; one new test asserts the line is
   gone.
2. `сдач: N` → `задач: N` in the tile header, `сдал N` → `задач: N` on the pupil.
3. No gendered verb anywhere on the screen (A1): the two remaining `не сдал` strings in
   the JS become `задач нет`.  Test greps the rendered page for `сдал`/`сдач`.
4. Tiles collapse.  A past tile becomes `<details class="kab-zanyatie …">` with the date
   row as its `<summary>` — closed by default, which is exactly «по умолчанию свёрнуто,
   потом я нажимаю, оно разворачивается», and it costs no JS and keeps the keyboard.
5. `.kab-tablica{columns:4}` → `columns:5`, and four tabs «1 четверть … 4 четверть» over
   four bodies.  Tabs are radio inputs plus CSS siblings — the site's own way of doing
   tabs (`karkas.obolochka`), not a new mechanism.  The tab holding today opens.
6. A future tile loses its list of five surnames: date plus the «меня не будет» control,
   nothing else.  The checkbox and its door stay exactly as they are.
7. A visible `Кондуит за занятие` button inside every past tile.  The click that used to
   hang on the date line moves onto it, because the date line is now the collapse toggle.
8. The кондуит panel stops being a `<ul>` of «листок 16A · задача 3» and becomes one ROW
   PER SHEET: a big sheet button that is a real link to `/listki/<номер>`, then the tasks
   of that sheet as pills — `3`, `8`, `10а`, without the word «задача».

**КРИТЕРИЙ, КОТОРЫЙ МОЖЕТ ПРОВАЛИТЬСЯ** — a live run against the live copy of the база
(57 pupils, 15 847 marks), not only the fixture: `/kabinet` rendered for a real teacher,
counted by script — tiles of the open quarter N of N, columns 5, future tiles carrying a
pupil surname 0, occurrences of `сдач`/`сдал` 0, summary line absent, three past tiles
expanded each carrying a `/listki/` sheet button and its task pills.

## ВОПРОСЫ — (заполняет исполнитель)
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

1. THE БАЗА HOLDS NO SEX, SO POINT 3 CANNOT BE DONE AS «СДАЛА» UNTIL SOMEBODY PUTS IT
   THERE. Measured on the live copy (57 pupils, 15 847 marks): `students` is
   `(id, tg_id, surname, name, class, status, first_sheet_id, gruppa)` and `teachers` is
   `(id, tg_id, name, aka, is_owner, kabinet, aktiven, gruppa)` — no sex column, no
   patronymic to derive one from, and none of the other 18 tables carries either. The
   screen therefore stopped using a gendered verb at all (`задач: N`, `задач нет`), which
   is correct for every person and is the word point 2 asked for anyway. Where the data
   could come from, cheapest first: (а) one `pol` column on `students` and on `teachers`,
   filled by the owner in the same screen where he edits people — 57 + 19 rows, one
   sitting; (б) the same column filled once from the class lists he already imports, if
   those name it; (в) nothing automatic — guessing from the given name is what the заход
   forbids, and it is wrong exactly on «Саша», «Женя», «Ян» and every non-Russian surname.
   ДОМ: владелец
   ДОСТАВЛЕНО: нет

2. THE SCHOOL YEAR HAS NO QUARTER CALENDAR ANYWHERE IN THE REPO, AND POINT 5 NEEDED ONE.
   `grep` over every `*.py` and `*.sql` finds «четверть» only in prose comments. The four
   boundaries are now written down once, as `CHETVERTI` in `veb/razdely/kabinet.py`, using
   the standard grid of the 2026/2027 school year (01.09–25.10 · 05.11–27.12 · 12.01–22.03
   · 01.04–31.05). They are a DEFAULT, not a fact taken from the school: only the owner
   knows the real dates, and a wrong boundary silently moves lessons between tabs.
   ДОМ: владелец
   ДОСТАВЛЕНО: нет

3. ON THE LIVE БАЗА THE КОНДУИТ IS EMPTY FOR ALMOST EVERYONE, AND THE REASON IS THE DATA,
   NOT THE SCREEN. Counted on a copy of the live база on 11.09, over all three lessons the
   school year has had so far and all 19 teachers: marks exist on ONE day only, 2026-09-03
   (53 of them), and on that day `enrollment` gives a composition to exactly ONE teacher of
   the nineteen — Ольга Рыжая, 3 pupils. The other two lessons (07.09, 10.09) have a
   composition for 14 teachers each and not a single mark. So «кондуит за занятие» prints
   «задач нет» for thirteen of the fourteen working teachers, and it is right to: the задачи
   of 03.09 belong to pupils who, according to `enrollment`, were not anybody's that day.
   The формат of point 8 is verified on the one row that does exist (`[16α] 2 3 4`,
   Симонова Анастасия, and `/listki/16α` answers 200). Whether the 03.09 распределение was
   simply entered later, or those 53 marks belong to a day that has no composition at all,
   is a question about the data and only the owner can answer it.
   ДОМ: владелец
   ДОСТАВЛЕНО: нет

4. TEN LESSON DAYS OF THE YEAR ARE IN NO TAB AT ALL, AND THAT IS THE PRICE OF THE DEFAULT
   QUARTER GRID. Counted by the verifier and re-counted here: пн/чт between 01.09.2026 and
   31.05.2027 number 78; the four quarters hold 68. The ten that fall out are the holiday
   days 26.10 · 29.10 · 02.11 · 28.12 · 31.12 · 04.01 · 07.01 · 11.01 · 25.03 · 29.03 — они
   ложатся между четвертями. If a lesson is ever held on one of them, it has nowhere to
   appear and the teacher cannot tick «меня не будет» on it. Fixed by the same one answer
   as item 2: the real quarter dates. Named separately because item 2 is «the boundaries
   may be wrong» and this is «a day between two right boundaries still disappears».
   ДОМ: владелец
   ДОСТАВЛЕНО: нет

5. THE «СЛЕДУЮЩИЙ СПЕЦМАТ» CARD STILL NAMES THE PUPILS OF A FUTURE LESSON, AND TWO OF THE
   OWNER'S OWN REQUESTS POINT OPPOSITE WAYS HERE. 09.09 he asked for exactly that card:
   *«я вижу, когда у меня следующий спецмат, какой там будет листок и какие у меня
   школьники на следующий спецмат»*. 11.09, point 6, he said of the TILES: *«какие там
   школьники на будущее, непонятно. Список школьников я бы не ставил»*. Point 6 is done to
   its letter — the tiles carry no surnames (measured: 1235 future tiles across all 19
   teachers, 0 surnames in them). The card above the table was left alone, because
   removing it would silently undo the 09.09 request, and this заход was not asked to.
   Found by the verifier. Which of the two stands is the owner's call.
   ДОМ: владелец
   ДОСТАВЛЕНО: нет

6. TWO TESTS OF THIS FILE SKIP OR NOT DEPENDING ON THE DAY OF THE WEEK THE RUN HAPPENS.
   `tests/veb/test_kabinet.py` — `test_a_lesson_that_ended_today_reads_as_past_and_not_as_
   future` and `test_a_future_lesson_is_frozen_even_though_it_is_weeks_away` both call
   `pytest.skip("сегодня не день занятия")`. 11.09 is a Friday, so both skipped, and the
   boundary «занятие сегодня уже кончилось» went unchecked on this run. The skip is honest
   — the state genuinely does not exist on a Friday — but it means the suite's coverage is
   a function of the calendar, and two thirds of the week it is lower without saying so.
   Fixable by injecting the clock (the page already takes `seichas=` for exactly this
   reason) instead of reading `date.today()`. Not done here: it is a change to tests of the
   WRITE path that nobody asked for, and the заход says not to.
   ДОМ: владелец
   *(дом-файл назвать нечем: `ДОМ: tests/veb/test_kabinet.py` дверь отклоняет — «дом —
   исполняемый код», а документа про покрытие тестов у этого проекта нет.)*
   ДОСТАВЛЕНО: нет

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

🔴 **СУБАГЕНТА ГИТ-КОНТУРА §0.1 ОТМЕНИЛ ОРКЕСТРАТОР, И ЭТУ СЕКЦИЮ ЗАПОЛНИЛ ИСПОЛНИТЕЛЬ.**
Причина названа оркестратором при запуске и замерена соседней волной: четыре захода из
десяти умерли ровно на вызове этого субагента. Вместо всего блока §0.1 велено выполнить
САМОМУ одну команду и вставить её вывод сюда. Она выполнена ПЕРВЫМ ходом, до всякой
работы, и её вывод — ниже дословно.

**СНИМОК ВХОДА** *(команда и её ВЫВОД, снято первым ходом)*
```
$ git --no-optional-locks branch --no-merged main | grep -c zahod/
0
```
Остальное снято тем же ходом, из рабочей папки `spetsmat-bot-wt/kabinet-plitki`:
```
$ git branch --show-current
zahod/kabinet-plitki
$ git --no-optional-locks status --porcelain | wc -l
0
$ git --no-optional-locks log --oneline @{u}.. | wc -l
fatal: no upstream configured for branch 'zahod/kabinet-plitki'
$ python3 …/git_zona.py zayavki
Охват: заявок открыто 0, переадресовано 28, постоянных исключений 0, сторож краснеет
на 0, держателей 0, двойной захват на 0
$ …/git_zona.py check --zone <каждый путь зоны по очереди>
✅ veb/razdely/kabinet.py · ✅ veb/razdely/lichnaya.py · ✅ veb/obshchee/karkas.py
✅ tests/veb/ · (зона чиста в HEAD — точку отката не фабриковал)
```

**ЧТО СДЕЛАНО** *(с хэшами)*
Вливать на входе было НЕЧЕГО: невлитых `zahod/*`-веток 0, открытых заявок 0, вне git 0.
Поэтому «сделано» на входе — ничего, и это не пропуск, а пустой контур. Своя ветка
`zahod/kabinet-plitki` вливается ПОСЛЕДНИМ ходом, по §«ПОСЛЕДНИЙ ХОД ПЕРЕД ОТЧЁТОМ».

🔴 **ЧИСЛО ВЫРОСЛО ПО ХОДУ РАБОТЫ, И ЭТО НЕ МОЙ ДОЛГ — НАЗЫВАЮ ПОИМЁННО (Г3).**
Повторный замер тем же способом в конце работы даёт **4** вместо 0:
```
$ git --no-optional-locks branch --no-merged main
* zahod/kabinet-plitki                  ← моя
+ zahod/konduit-galochki-i-podskazki    ← чужая ЖИВАЯ рабочая папка (знак «+»)
+ zahod/otsutstvie-prepodavatelya       ← чужая ЖИВАЯ рабочая папка
+ zahod/zhurnal-setka                   ← чужая ЖИВАЯ рабочая папка
```
Знак `+` в выводе `git branch` означает, что ветка занята ДРУГИМ worktree, то есть в ней
прямо сейчас работает соседняя позиция волны. Три эти ветки завелись между моим снимком
входа и этим замером; вливать их запрещено и текстом захода («первая вернула не 0 —
НИЧЕГО чужого не вливай»), и здравым смыслом — влитие чужой недоделанной работы уносит
её автора. Своя из четырёх — одна, и она влита последним ходом.

**ВСЕ ДОЛГИ ВХОДА ЗАКРЫТЫ:** `да`

*(На входе долгов не было ни одного: невлитых `zahod/*` 0 — вывод команды выше, — заявок
0, вне git 0. Закрывать было нечего, и это состояние ПРОВЕРЕНО командой, а не
предположено.)*
*(`нет` законно — но ТОЛЬКО со списком поимённо: что осталось и почему это непроходимо ТВОИМИ
правами (чужая живая рабочая папка, нужно решение владельца, конфликт, обеих сторон которого
не понимаешь). «Сложно» и «не моя тема» причинами не являются. `нет` без списка = красный.)*

## ОТЧЁТ — (заполняет исполнитель)
**АРТЕФАКТ:** `/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/scratchpad/kabinet-plitki/1-po-umolchaniyu.png` — открыть просмотрщиком картинок (рядом ещё три снимка и `PROGON-zhivaya-kopiya.txt`, это вывод замера)

Четыре снимка — то, как экран выглядит ПОСЛЕ всех восьми пунктов, сняты браузером на
эталоне 1440×900 по копии боевой базы, преподаватель Ольга Рыжая (id=13 — единственный,
у кого на живых данных кондуит непустой, разбор ниже):
* `1-po-umolchaniyu.png` — то, что владелец увидит, открыв кабинет: 15 плиток первой
  четверти в пять колонок, ВСЕ свёрнуты, четыре вкладки четвертей
* `2-konduit-za-zanyatie.png` — раскрытая плитка и её кнопка «Кондуит за занятие»
* `3-konduit-shkolnika.png` — **главный пункт 8**: строка `[16α] 2 3 4`, где `16α` —
  кнопка-ссылка на сам листок, а `2 3 4` — задачи пилюлями, без слова «задача»
* `4-chetvert-4.png` — переключение вкладки: четвёртая четверть, 18 плиток

САМ ЭКРАН (он же настоящий артефакт — это заход про код) поднимается так:
```
cd /Users/ivanyakovlev/Documents/GitHub/spetsmat-bot && SPETSMAT_BAZA=data/spetsmat.db \
  SPETSMAT_VEB_SECRET=любая-строка PYTHONPATH=. python3 -m veb.server --port 8099
# затем http://127.0.0.1:8099/kabinet, войдя ЛИЧНЫМ паролем (общий кабинет не покажет)
```

**РОД АРТЕФАКТА:** `исходник`
*(продукт захода — код `veb/razdely/kabinet.py` и его тесты; снимки приложены как
доказательство, а не как продукт.)*

**КОММИТ:** `d618bba` — «kabinet: the konduit panel never opened — 'var uzel' shadowed
'function uzel'; fixed, plus a browser test and a var/function collision gate» — последний
коммит КОДА; после него шли только коммиты этого отчёта и снимков. Всего коммитов
пятнадцать, по одному на каждый пункт рецензии и далее по ходу работы; полный список —
`git log --oneline 5220b59..zahod/kabinet-plitki`, разбор — в таблице ниже.
`git_zona.py check --zone` по всем пяти путям зоны → ✅ ✅ ✅ ✅ ✅
Ветка **влита в `main`** (последнее слияние `9576d9a`) и **вывезена** на `origin`.

---

### ЧТО СДЕЛАНО И ЗАЧЕМ — ВОСЕМЬ ПУНКТОВ РЕЦЕНЗИИ, ПО ОДНОМУ КОММИТУ НА ПУНКТ

| # | что просил владелец | коммит | чем закрыто |
|---|---|---|---|
| 1 | убрать сводную фразу «2 из 3» | `57e6558` | строка и все четыре счётчика, жившие только ради неё, удалены; два теста, ТРЕБОВАВШИХ эту строку, сняты вместе с ней и заменены тестом на её отсутствие |
| 2 | «сдач» → «задач» | `e8f0414` | шапка плитки говорит `задач: N` — формат владельца дословно |
| 3 | род глагола по полу | `fe55762` | **пола в базе НЕТ** (замер ниже) ⇒ экран перестал употреблять глагол вовсе |
| 4 | плитки свёрнуты | `723c166` | прошедшая плитка — `<details>` без `open`; раскрывает браузер, ни строки скрипта |
| 5 | 5 колонок и вкладки четвертей | `1ab5b69` | `columns:5`, четыре вкладки на радиокнопках и CSS — механизм самой оболочки сайта |
| 6 | будущее не заполнять | `5ce95d3` | будущая плитка = дата + «меня не будет»; она же больше не спрашивает базу вовсе |
| 7 | кондуит — видимой кнопкой | `c50c3fd` | `<button>Кондуит за занятие</button>` внутри плитки; клик уехал со строки-даты |
| 8 | формат кондуита | `5ef8148` | строка на ЛИСТОК: кнопка-ссылка `/listki/<номер>` + задачи пилюлями |

Ещё три коммита: `563017f` — замеренное число вместо обещания замера в комментарии;
`771a0b2` — `## ГИГИЕНА ВХОДА` и пункты очереди; `d618bba` — починка дефекта, который
нашёл браузерный прогон (ниже отдельно, это самое важное в отчёте).

### 🔴 ГЛАВНОЕ: ПУНКТ 8 ПРИЕХАЛ НЕРАБОЧИМ И БЫЛ ЗЕЛЁНЫМ У ВСЕХ ТЕСТОВ

`function uzel(…)` перекрылось стоявшим выше в той же области `var uzel =
document.getElementById('kab-dannye')`. `var` всплывает наверх и перетирает объявление
функции: `pokazat` падал с `uzel is not a function`, **панель кондуита не открывалась ни
разу**. Разметка была правильной, поэтому тридцать тестов, читающих разметку, были
зелёными. Поймал браузерный прогон (playwright, 1440×900) — то есть ровно тот «живой
прогон на реальном объекте», которого требует `§2 КРИТЕРИЙ ГОТОВНОСТИ`.
Починено (`d618bba`) и закрыто ДВУМЯ носителями, а не извинением:
* `test_in_a_real_browser_the_konduit_button_opens_a_row_per_sheet` — настоящий браузер:
  открывает страницу, раскрывает плитку, жмёт кнопку и проверяет ТО, ЧТО ПОСЛЕ ЭТОГО
  ВИДНО (строка листка, адрес, пилюли), плюс ловит любую ошибку скрипта через `pageerror`;
* `test_no_name_in_the_page_script_is_both_a_var_and_a_function` — дешёвый гейт ровно на
  этот класс, отвечает без Chromium.
Урок фабрике записан выше, с ценой.

### КРИТЕРИЙ ГОТОВНОСТИ — ЖИВОЙ ПРОГОН ПО КОПИИ БОЕВОЙ БАЗЫ, С ОХВАТОМ

Копия снята с `/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot/data/spetsmat.db`
(3 940 352 байта) в свой scratchpad; **в саму базу не писал ни разу**.

```
СТАТУС                          : 200
СЕГОДНЯ                         : 2026-09-11 · открыта четверть 1
четверть 1 (2026-09-01 … 2026-10-25): занятий 15, плиток на экране 15 ✅
четверть 2 (2026-11-05 … 2026-12-27): занятий 15, плиток на экране 15 ✅
четверть 3 (2027-01-12 … 2027-03-22): занятий 20, плиток на экране 20 ✅
четверть 4 (2027-04-01 … 2027-05-31): занятий 18, плиток на экране 18 ✅
ПЛИТОК В ОТКРЫТОЙ ЧЕТВЕРТИ      : 15 из 15
КОЛОНОК (из таблицы стилей)     : 5
СВЁРНУТЫ ВСЕ ПЛИТКИ             : ✅ да
СВОДНАЯ ФРАЗА «2 из 3»          : ✅ нет
СЛОВО «сдач» НА ЭКРАНЕ          : ✅ 0
ГЕНДЕРНЫЕ ГЛАГОЛЫ НА ЭКРАНЕ     : ✅ 0
БУДУЩИХ ПЛИТОК                  : 65 · из них со списком школьников: 0 ✅
КНОПОК «Кондуит за занятие»     : 3   (= числу завершившихся занятий, 3 из 3)
── РАЗВЁРНУТО ТРИ ПРОШЕДШИЕ ПЛИТКИ ──
  2026-09-03 · кнопка кондуита: есть · Симонова Анастасия  [16α] 2 3 4
  2026-09-07 · кнопка кондуита: есть · школьников 3, задач нет
  2026-09-10 · кнопка кондуита: есть · школьников 3, задач нет
   /listki/16α → 200
```
И в БРАУЗЕРЕ, эталон 1440×900, роль `prepod` (гейт вёрстки эту роль не меряет вовсе —
он сам это печатает в своём списке «не проверяется», и его прогон на `/kabinet` измерил
заглушку для организатора, 206 знаков, а не кабинет):
```
горизонтальная прокрутка : НЕТ  (scrollWidth 1440 = clientWidth 1440)
колонок фактически       : 5
плиток видно             : 15 · за экраном 0 · ниже сгиба 0
раскрытых при загрузке   : 0 из 3
вкладок                  : 4 · переключение на 4 четверть → 18 плиток, первая скрыта
будущих плиток со списком: 0
панель кондуита          : [16α] → /listki/16%CE%B1 · пилюли «2» «3» «4» ·
                           слова «задача» нет · горизонтальной прокрутки в панели нет
```

**🔴 ОТРИЦАТЕЛЬНЫЙ ВЕРДИКТ ПО «16 ИЗ 16» — С ОХВАТОМ.** Критерий просил «плиток в четверти
16 из 16». **16 не подтвердилось: их 15**, и это не недоделка, а арифметика. 16 — оценка
самого захода («~8 недель × 2 занятия»); реальное число даёт календарь: пн/чт между
01.09 и 25.10 — пятнадцать. Что ПРОВЕРЕНО и держится: **все дни занятий четверти на
экране, 15 из 15**, и то же по остальным трём — 15/15, 20/20, 18/18, **68 из 68 за год**,
чужих дней в чужой вкладке 0 (пересчитано и мной, и верификатором независимо).

### ЧТО НЕ СДЕЛАНО ТАК, КАК БЫЛО НАПИСАНО, И ПОЧЕМУ — ПУНКТ 3

Пола в базе **нет**, и это замерено, а не предположено:
```
students : id, tg_id, surname, name, class, status, first_sheet_id, gruppa
teachers : id, tg_id, name, aka, is_owner, kabinet, aktiven, gruppa
```
Ни столбца пола, ни отчества, из которого его выводят, — ни здесь, ни в остальных 18
таблицах. Заход прямо запрещает угадывать пол по имени, и правильно делает: «Саша»,
«Женя», «Ян» и любая нерусская фамилия дают ошибку молча. Поэтому сделано другое: **экран
перестал употреблять глагол вовсе** — `сдал N` → `задач: N`, `ничего не сдал` → `задач
нет`. Безличная форма рода не имеет и неверной быть не может; она же — то самое слово
«задач», которое владелец просил пунктом 2. Второй гендерный глагол, «принято сдач», стоял
внутри сводной строки и ушёл с ней по пункту 1. Откуда брать пол, если владелец хочет
именно «сдала» — пункт очереди 1 в `## ВОПРОСЫ`, `ДОМ: владелец`.

### ЧЕГО НЕ ТРОГАЛ

* `veb/razdely/lichnaya.py` и `veb/obshchee/karkas.py` — в зоне, но менять их не
  понадобилось ни разу: все восемь пунктов про то, ЧТО рисует кабинет
* путь ЗАПИСИ отметки «меня не будет» (`otmetit_otsutstvie`, `teacher_attendance`,
  заморозка в `core/`) — ни строки; пункт 6 менял только показ
* карточка «следующий спецмат» — оставлена как есть (пункт очереди 5, разбор там)
* всё вне зоны

### ЧИСЛА ПРОГОНОВ

* `pytest tests/veb/test_kabinet.py -q` → **31 passed, 2 skipped** (было на входе
  23 passed, 2 skipped; +8 новых тестов, 2 снятых вместе со сводной строкой)
* `pytest tests/veb/ -q` → **179 passed, 8 failed, 15 skipped, 2 xfailed, 13 errors**.
  На ВХОДЕ, до единой моей правки: **173 passed, 8 failed, 15 skipped, 2 xfailed,
  13 errors**. Списки красного сверены построчно: `comm` даёт ПУСТО в обе стороны —
  ни одной новой поломки, ни одной случайно починенной. Красное унаследовано и лежит в
  `test_priyom.py`, `test_server.py`, `test_kanon_verstki.py`; последний ошибается
  потому, что `data/spetsmat.db` в рабочей папке — пустой файл 0 байт.
* два теста этого файла пропущены по дню недели (11.09 — пятница) — пункт очереди 6

### РЕЗУЛЬТАТ ВЕРИФИКАТОРА (§3, ПОСЛЕ-типа, свежий субагент, другой метод)

Метод другой: он ходил в кабинет куками **всех 19 преподавателей** и считал по собранной
странице, а не по коду. Вердикт — **все восемь пунктов ✅, ложных зелёных не найдено**.
Его числа: сводная фраза 0/19 страниц · «сдач» видимо 0/19 · гендерных глаголов 0 даже в
сыром HTML · `<details>` 57, с `open` 0 · дни четвертей 15/15/20/18=68 совпали поимённо
у 19/19, чужих 0 · будущих плиток 1235, фамилий в них 0 (сверял по всем 57 фамилиям из
`students`), «меня не будет» 1235, флажков 1235 · прошедших плиток 57, без кнопки
кондуита 0 · все 21 номер листка из базы отвечают 200.
Финальная строка получена: **«выдано 14 позиций из 14 найденных»** — ответ не усечён.
Его находки сверх задания превращены в пункты очереди 3, 4, 5, 6 (я их перепроверил;
одну его формулировку уточнил: состав 03.09 есть у одного преподавателя **с учётом
слота**, без фильтра по слоту строк больше).

### ПОВТОРЯЕМОСТЬ НАХОДОК

* **ПОВТОРИТСЯ на следующем же заходе, который правит страницу** — критерий готовности,
  сформулированный как `pytest -q` → `rc=0`, не проверяет экран, половина которого скрипт.
  Это НЕ пункт очереди, а заход ДО следующего прогона (класс НЕМЕДЛЕННОЕ): цена уже
  оплачена здесь — главный пункт владельца приехал нерабочим и зелёным. Записано уроком
  фабрике выше.
* **НЕ повторится** — отсутствие пола в базе, отсутствие календаря четвертей, пустой
  кондуит на живых данных, пропуск двух тестов по дню недели: это свойства ЭТОГО проекта
  и этих данных. Законно ушли пунктами очереди 1–6.

### НЕОБРАТИМОЕ

Удалены две проверки в `tests/veb/test_kabinet.py` — `test_the_cabinet_sums_itself_up_in_
one_line` и `test_the_summary_does_not_count_a_lesson_the_teacher_did_not_teach`. Обе
требовали ровно ту строку, которую владелец пунктом 1 велел убрать; оставить их значило
бы запретить выполнение просьбы. Восстанавливается `git show 5220b59:tests/veb/test_
kabinet.py`; содержательная находка второй (сводка складывала календарь с работой)
сохранена комментарием у места, где сводка считалась. Ничего другого необратимого нет:
файлов не удалял, не переименовывал, не перемещал, `reset`/`checkout` поверх
несохранённого не делал, за зону не выходил, в боевую базу не писал (работал с копией).

### ГИГИЕНА §4.1 — ВЫВОД КОМАНД, НЕ ПЕРЕСКАЗ

**Г1 · зона доехала в git** — пять команд, пять ✅:
```
✅ зона veb/razdely/kabinet.py: работа доехала в git, вне git ничего нет.
✅ зона veb/razdely/lichnaya.py: работа доехала в git, вне git ничего нет.
✅ зона veb/obshchee/karkas.py: работа доехала в git, вне git ничего нет.
✅ зона tests/veb/: работа доехала в git, вне git ничего нет.
✅ зона zhurnal/2026-09-02_spetsmat-bot/kod_kabinet-plitki.md: работа доехала в git…
```
**Г2 · второй репозиторий** — неприменимо, и это проверено, а не предположено: все пути,
которых я касался, лежат внутри `spetsmat-bot`; за его пределы зона не выходила.
**Г3 · невлитых не прибавилось МОИХ** — на входе 0, сейчас 4. Выросло на три ЧУЖИЕ,
каждая названа поимённо с причиной в `## ГИГИЕНА ВХОДА`: это живые рабочие папки соседних
позиций волны (знак `+` в выводе `git branch` = ветка занята другим worktree). Моя из
четырёх одна, и она влита последним ходом.
**Г4 · новый инструмент имеет точку вызова** — неприменимо: ни одного нового `.py` в
`_generator/**` не заводил. Два `.py`, которые я завёл (`scratchpad/kabinet-plitki/
progon.py` и `brauzer.py`), — это замеры прогона, а не инструменты фабрики, и лежат они
в личном scratchpad захода, куда `check_tool_contract.py` не смотрит.
**Г5 · новый `.md` зарегистрирован** — неприменимо: ни одного нового `.md` не заводил,
`register_doc.py` не звал, `_studio/docs/KARTA.md` не трогал. Полный список добавленных
файлов — семь, все в `scratchpad/kabinet-plitki/`, и ни одного `.md` среди них.
**Г6 · чужих путей в коммите нет** — `git diff --name-only 5220b59..HEAD` даёт ровно
десять путей, и все мои: `veb/razdely/kabinet.py` · `tests/veb/test_kabinet.py` ·
`zhurnal/2026-09-02_spetsmat-bot/kod_kabinet-plitki.md` · семь файлов
`scratchpad/kabinet-plitki/`. Ни одного чужого.

**ВРЕМЯ ПРОГОНА + ТОКЕНЫ:** неприменимо — движок `opencode`, счётчика стоимости в логе нет.

### ПОЛНАЯ ГИТ-ГИГИЕНА ПОСЛЕДНИМ ХОДОМ — ЧИСЛА, ПЕЧАТАННЫЕ КОМАНДОЙ

**1 · ВСЕ КОММИТЫ.** Своя рабочая папка: `git status --porcelain | wc -l` → **вне git 0**.
Главная папка: **14 грязных путей, и ни один не мой** — это живое состояние волны и
соседних сессий: `README.md`, шесть файлов дежурства и состояния
(`SERDCE-VOLNY-noch2.md`, `PULS-CHASOVOGO-noch2.log`, `SESSIYA.md`, `SOSTOYANIE.md`,
`.chasovoj-zamki/okon-bylo`), `zhurnal/_INFRA-git/INCIDENTY.md`, чужой
`HANDOFF-2026-09-12.md`, `scratchpad/verifikator/`, два `.DS_Store` и три файла заявок —
среди них МОЯ заявка (её завёл сам инструмент, см. шаг 5). Чужую содержательную работу
не коммичу и не трогаю: `zhurnal/_INFRA-git/` и файлы волны вне зоны захода.

**2 · ВЛИТИЕ СВОЕЙ ВЕТКИ.** Слияния без конфликтов:
```
✅ Влито в `main` без конфликтов: 8e1b057 Merge branch 'zahod/kabinet-plitki'  — весь код
✅ Влито в `main` без конфликтов: 97d78ff Merge branch 'zahod/kabinet-plitki'  — маркеры
✅ Влито в `main` без конфликтов: 9576d9a Merge branch 'zahod/kabinet-plitki'  — отчёт
```
Второе — потому что первое напечатало «ВЛИТО, НО НЕ ВСТРОЕНО (2)» на моих двух
замерочных `.py`. Долгом не оставил, хотя это было бы законно: оба получили маркер
`# TOOL-CONTRACT: called-by-hand` (они и правда зовутся только рукой — ходят в КОПИЮ
базы), и второе слияние прошло без единого флага.
🔴 **САМОЕ ПОСЛЕДНЕЕ СЛИЯНИЕ ПРОЦИТИРОВАТЬ НЕЛЬЗЯ, И ЭТО НЕ ПРОПУСК.** Этот абзац едет в
`main` слиянием, хэш которого станет известен ПОСЛЕ того, как абзац написан. Выше названы
все, какие можно назвать; проверяется это не хэшем, а состоянием, и оно снято командой:
`git branch --merged main` называет `zahod/kabinet-plitki`, а `git status --porcelain` в
рабочей папке пуст. Приёмка гоняет те же две команды и увидит то же самое.

**3 · ПОСТ-ПРОВЕРКА ИЗ ГЛАВНОЙ ПАПКИ — ЗЕЛЁНАЯ.** Не «коммит виден», а «механизм встал»:
из `/Users/ivanyakovlev/Documents/GitHub/spetsmat-bot` поднят сервер и СОБРАНА страница по
копии боевой базы — `СТАТУС 200`, 15/15 · 15/15 · 20/20 · 18/18 плиток, колонок 5,
свёрнуты все, сводной фразы нет, «сдач» 0, гендерных глаголов 0, будущих со списком 0 из
65, кнопок кондуита 3 из 3, кондуит `Симонова Анастасия [16α] 2 3 4`, `/listki/16α` → 200.
Живая точка вызова на месте: `grep -n 'veb.razdely.kabinet' veb/server.py` →
`122: "veb.razdely.vnesenie", "veb.razdely.kabinet")` — раздел стоит в
`RAZDELY_S_MARSHRUTAMI`, то есть маршрут действительно зарегистрирован, а не просто
написан. Откатывать нечего.

**4 · ГАШЕНИЕ.** `git branch --no-merged main` → осталось **2**, обе ЧУЖИЕ и обе живые:
```
+ zahod/otsutstvie-prepodavatelya
+ zahod/zhurnal-setka
```
Знак `+` = ветка занята другим worktree, то есть в ней прямо сейчас работает соседняя
позиция волны; вливать чужую недоделанную работу нельзя. (Третья, `zahod/konduit-
galochki-i-podskazki`, за время моего прогона влилась сама — её сессия закончила
раньше.) Моей в списке нет: `git branch --merged main` называет
`zahod/kabinet-plitki`. `git_zona.py poteri --branch zahod/kabinet-plitki` →
«✅ Потерь нет, проверено 1 из 1» — ветку можно гасить, но гашение это решение владельца.

**5 · ВЫВОЗ.** Своя ветка вывезена: `git push -u origin zahod/kabinet-plitki` →
`* [new branch] zahod/kabinet-plitki`, после чего
`git log --oneline @{u}.. | wc -l` → **0**. `main` НЕ вывозил — §5 это прямо запрещает
(публикация витрины есть решение владельца), а невывезенного в нём **17 коммитов**,
включая моё слияние `97d78ff`. Поставлена заявка:
`2026-09-11T1208-main-origin-17-97d78ff-kabinet-plitki` · род `git-operaciya`.

**6 · ПРОВЕРКА ФАКТОМ.** Числа по каждому репозиторию — один, `spetsmat-bot`:
вне git **0** (своя папка) и **14 чужих** (главная, поимённо выше) · невлитых своих
**0**, чужих **2** (названы) · невывезенных СВОЕЙ ВЕТКИ **0** · пост-проверка **зелёная,
откат не потребовался**.

**ПРАВКИ ПРОЧИТАНЫ:** блок `## ПРАВКИ ПОСЛЕ ВЫДАЧИ` пуст — правок не было.

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

**ВЕТКА РАБОТЫ:** `zahod/kabinet-plitki`
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

### ЧТО ИМЕННО ПРОСИТ ВЛАДЕЛЕЦ (его слова)

«Мне нравится… но я сразу предлагаю его перестроить немножко.» Дальше по пунктам:

1. **УБРАТЬ СВОДНУЮ ФРАЗУ.** «Я не понял, что значит занятия с вашими школьниками 2 из 3… это
   какая-то фраза вставлена, которую можно удалить вообще. Фразы от себя лучше удалять.»
   Строку `с начала года: занятий с вашими школьниками 2 из 3 · принято сдач 69 · работал со
   школьниками: 5` — УДАЛИТЬ целиком.
2. **СЛОВО.** «Потом слово „сдач“ очень странное. Лучше пиши „задач“.» → `задач: 23`.
3. **РОД.** «Бочарова Анна — она СДАЛА, а не сдал.» Род глагола по полу преподавателя и
   школьника: сдала/сдал, приняла/принял. Пол берётся из данных, а не угадывается по имени;
   если данных о поле нет — НАЗОВИ это в отчёте и предложи, откуда их брать.
4. **ПЛИТКИ СВОРАЧИВАЮТСЯ.** «Мне кажется, что такой формат не очень удобный. Удобнее, если у
   тебя будет свёрнуто… потом я нажимаю, оно разворачивается.» По умолчанию свёрнуты все.
5. **ПЯТЬ КОЛОНОК И ЧЕТВЕРТИ.** «Можно оставить такую плитку, но тогда нужно, чтобы 5 было
   колонок, чтобы на всю четверть ты прям видел… У нас будет вкладка четверть 1, потом четверть
   2, 3, 4.» В четверти ~8 недель × 2 занятия = 16 плиток; они обязаны поместиться.
6. **БУДУЩЕЕ НЕ ЗАПОЛНЯТЬ.** «На будущее точно не надо их заполнять сейчас. Какие там школьники
   на будущее, непонятно. Список школьников я бы не ставил, на будущее пустые такие таблетки и
   просто возможность нажать „меня не будет“.» Сейчас будущие плитки несут список из пяти
   фамилий — убрать, оставить дату и кнопку «меня не будет».
7. **КОНДУИТ ЗА ЗАНЯТИЕ — ВИДИМОЙ КНОПКОЙ.** «Чтобы вывести кондуит за занятие, я должен нажать
   на дату. Должно быть гораздо более видно это. Должна быть кнопка „Кондуит за занятие“.»
8. **ФОРМАТ ИНДИВИДУАЛЬНОГО КОНДУИТА — ГЛАВНОЕ.** «Кондуит записан странно: задачи записаны в
   список. Если было бы 10 задач, это было бы нереально поместить. Нужно писать в несколько
   колонок: первая колонка — 16A, то есть название листка, кнопочкой большой красивой, и дальше
   список задач тоже кнопочками, без слова „задача“: просто 3, 8, 10а. Вторая строчка: 16 альфа
   и тоже 1, 2. По кнопке листка должна быть возможность перейти к этому листку.»
   То есть строка на ЛИСТОК: кнопка листка (ссылка на сам листок) + задачи этого листка кнопками.

### КРИТЕРИЙ ГОТОВНОСТИ
Числа с охватом: плиток в четверти 16 из 16 и все помещаются в пять колонок; развёрнуты три
прошедшие — в каждой индивидуальный кондуит в формате «листок + задачи кнопками»; будущих плиток
со списком школьников — НОЛЬ; слова «сдач» на экране — ноль; сводной фразы — нет.
