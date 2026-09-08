# spetsmat-bot

**Телеграм-бот приёма задач спецмата 179-й школы.** 56 учеников, 18 преподавателей,
три аудитории, два занятия в неделю. Заменяет гугл-таблицу, в которой это велось.
Преподаватель отмечает сданные задачи текстом, голосом или фотографией печатного
бланка; бот показывает черновик, человек подтверждает.

## Как поднять

    cd ~/Documents/GitHub/spetsmat-bot
    set -a; . secrets/bot.env; set +a          # BOT_TOKEN, OWNER_ID, ключи моделей
    nohup python3 -m bot >> logs/bot.log 2>&1 & disown

Лог — `logs/bot.log`. Подробности, сторож и что делать при падении —
[`doc/EKSPLUATACIA.md`](doc/EKSPLUATACIA.md).

## Три входа

- **текст** — блок на ученика, имя и номера задач; прочерк значит «был, не сдал»;
- **голос** — та же грамматика вслух;
- **фото** — только печатный бланк с кодами: фамилии не покидают сервер.

Форматы целиком, с примерами и границами — [`doc/VHODY.md`](doc/VHODY.md).

## 🔴 Главный запрет

**Отметка не попадает в журнал без подтверждения человеком.** Любой вход даёт
черновик; в базу его переводит нажатие. Этим объясняется половина архитектуры:
закрытые списки вместо догадок, кнопки при неоднозначности, отдельный экран
подтверждения.

## 🔴 Второй запрет — про сайт

**Новые страницы делаются ОТ существующего дизайна. Существующие страницы НЕ
переделываются под новые.** Заглавная переделывалась шесть раз за одну ночь и была
принята владельцем; всё, что придёт позже, дешевле переписать, чем её.

Схема закреплена машинно, а не обещанием: `proverit_karkas()` и `proverit_shemu()`
зовутся из `sobrat()` на каждой сборке, и нарушение роняет сборку — а с ней и
сохранение в админке. Полный список запретов и эталонные числа —
[`doc/DIZAJN-ZAKREPLENO.md`](doc/DIZAJN-ZAKREPLENO.md).

## Куда дальше

[`doc/KARTA.md`](doc/KARTA.md) — вопрос → файл. Там же граница между двумя домами:
`doc/` отвечает, **как устроен продукт**; `zhurnal/` — **как мы к этому пришли**,
и справкой не является.

---

## §6. Карта документов корня




**`zhurnal/2026-09-02_spetsmat-bot/DIAGNOZ-huka-2026-09-04.md`** (диагноз stop-хука: почему глобальная регистрация была ошибкой, для аналитика фабрики)

**`zhurnal/2026-09-02_spetsmat-bot/HANDOFF-2026-09-03.md`** (Хэндофф в сессию 2026-09-03)


**`zhurnal/2026-09-02_spetsmat-bot/HANDOFF-2026-09-04.md`** (Хэндофф в сессию 2026-09-04)


**`zhurnal/2026-09-02_spetsmat-bot/HANDOFF-2026-09-05.md`** (Хэндофф в сессию 2026-09-05)



**`zhurnal/2026-09-02_spetsmat-bot/HANDOFF-2026-09-08.md`** (Хэндофф в сессию 2026-09-08)

**`zhurnal/2026-09-02_spetsmat-bot/NADEZHNOST-zakaz-na-resyorch.md`** (надёжность: разбор топологии, оффлайн-очередь тапов, бэкапы и заказ на ресёрч Р1-Р7)

**`zhurnal/2026-09-02_spetsmat-bot/NAVIGATOR.md`** (навигатор арки 2026-09-02_spetsmat-bot (ориентация, читается первым): Кондуит спецмата в телеграме)


**`zhurnal/2026-09-02_spetsmat-bot/PLAN-RAZNOSA-sessii-veb.md`** (план разноса длинной сессии «сайт» по домам: выгрузка машинно, три захода по третям, сведение, список вопросов под ресёрч)

**`zhurnal/2026-09-02_spetsmat-bot/PLAN.md`** (план арки 2026-09-02_spetsmat-bot)



**`zhurnal/2026-09-02_spetsmat-bot/PODYOM-VOLNY-sajt.md`** (подъёмный лист волны «сайт»: две строки инструкции оркестратору, порядок позиций, модели, запреты)


**`zhurnal/2026-09-02_spetsmat-bot/RESHENIA-2026-09-05.md`** (решения сессии 04.09: постоянная ссылка через Pages, вход преподавателя через Telegram, slot вместо weekday в enrollment)

**`zhurnal/2026-09-02_spetsmat-bot/SESSIYA.md`** (дневник арки 2026-09-02_spetsmat-bot)


**`zhurnal/2026-09-02_spetsmat-bot/SOSTOYANIE.md`** (состояние арки 2026-09-02_spetsmat-bot — что сделано/осталось, чем измерено, дом разведки)


**`zhurnal/2026-09-02_spetsmat-bot/SVERKA-2026-09-04.md`** (сверка волны «сайт» с реальностью: что заявлено против того, что снято командами)

**`zhurnal/2026-09-02_spetsmat-bot/TZ.md`** (контракт арки 2026-09-02_spetsmat-bot)

**`zhurnal/2026-09-02_spetsmat-bot/UROKI-FABRIKE.md`** (уроки арки 2026-09-02_spetsmat-bot с ценой, вход закрывающей сессии)



**`zhurnal/2026-09-02_spetsmat-bot/VHOD-2026-09-04.md`** (Вход без закрытия предыдущей сессии 2026-09-04)


**`zhurnal/2026-09-02_spetsmat-bot/VHOD-2026-09-05.md`** (Вход в сессию 2026-09-05: волна ОСНОВАНИЕ собрана, семь заходов готовы, ждёт починки хука)


**`zhurnal/2026-09-02_spetsmat-bot/VHOD-2026-09-09.md`** (Вход в сессию: приёмка двух заходов и решение по заявке в Search Console)

**`zhurnal/2026-09-02_spetsmat-bot/VYGRUZKA-2026-09-02.md`** (Выгрузка сессии 2026-09-02 — сырьё для дневника арки 2026-09-02_spetsmat-bot)




**`zhurnal/2026-09-02_spetsmat-bot/VYGRUZKA-2026-09-03-2.md`** (Выгрузка сессии 2026-09-03 — сырьё для дневника арки 2026-09-02_spetsmat-bot)


**`zhurnal/2026-09-02_spetsmat-bot/VYGRUZKA-2026-09-03-3.md`** (Выгрузка сессии 2026-09-03 — сырьё для дневника арки 2026-09-02_spetsmat-bot)


**`zhurnal/2026-09-02_spetsmat-bot/VYGRUZKA-2026-09-03-4.md`** (Выгрузка сессии 2026-09-03 — сырьё для дневника арки 2026-09-02_spetsmat-bot)

**`zhurnal/2026-09-02_spetsmat-bot/VYGRUZKA-2026-09-03.md`** (Выгрузка сессии 2026-09-03 — сырьё для дневника арки 2026-09-02_spetsmat-bot)






**`zhurnal/2026-09-02_spetsmat-bot/VYGRUZKA-2026-09-04-2.md`** (Выгрузка сессии 2026-09-04 — сырьё для дневника арки 2026-09-02_spetsmat-bot)


**`zhurnal/2026-09-02_spetsmat-bot/VYGRUZKA-2026-09-04-3.md`** (Выгрузка сессии 2026-09-04 — сырьё для дневника арки 2026-09-02_spetsmat-bot)

**`zhurnal/2026-09-02_spetsmat-bot/VYGRUZKA-2026-09-04.md`** (Выгрузка сессии 2026-09-04 — сырьё для дневника арки 2026-09-02_spetsmat-bot)



**`zhurnal/2026-09-02_spetsmat-bot/VYGRUZKA-2026-09-07-2.md`** (Выгрузка сессии 2026-09-07 — сырьё для дневника арки 2026-09-02_spetsmat-bot)


**`zhurnal/2026-09-02_spetsmat-bot/VYGRUZKA-2026-09-07-3.md`** (Выгрузка сессии 2026-09-07 — сырьё для дневника арки 2026-09-02_spetsmat-bot)

**`zhurnal/2026-09-02_spetsmat-bot/VYGRUZKA-2026-09-07.md`** (Выгрузка сессии 2026-09-07 — сырьё для дневника арки 2026-09-02_spetsmat-bot)



**`zhurnal/2026-09-02_spetsmat-bot/VYGRUZKA-2026-09-08-2.md`** (Выгрузка сессии 2026-09-08 — сырьё для дневника арки 2026-09-02_spetsmat-bot)

**`zhurnal/2026-09-02_spetsmat-bot/VYGRUZKA-2026-09-08.md`** (Выгрузка сессии 2026-09-08 — сырьё для дневника арки 2026-09-02_spetsmat-bot)

**`zhurnal/2026-09-02_spetsmat-bot/kod_N0-dovezti-rabotu-noch-0904.md`** (довезти в git работу ночи 04.09: две регрессии и вся волна ОСНОВАНИЕ, двумя коммитами)

**`zhurnal/2026-09-02_spetsmat-bot/kod_N1-slot-vmesto-weekday.md`** (enrollment переводится с weekday на slot 1|2, room выносится в отдельную таблицу)

**`zhurnal/2026-09-02_spetsmat-bot/kod_N2-chelovek-bez-klassa.md`** (инструмент, называющий подозрительные строки состава и НЕ удаляющий ничего сам)


**`zhurnal/2026-09-02_spetsmat-bot/kod_N3-vhod-cherez-telegram.md`** (вход преподавателя по одноразовой ссылке от бота, преподавательского пароля больше нет)


**`zhurnal/2026-09-02_spetsmat-bot/kod_N4-priyom-zadach.md`** (сетка «ученик x задачи листка», отметка ставится тапом через существующий сервис)


**`zhurnal/2026-09-02_spetsmat-bot/kod_N5-konduit-proshlogo-goda.md`** (чтение архива прошлого года: 18 листков, 56 учеников, 15847 событий)


**`zhurnal/2026-09-02_spetsmat-bot/kod_N6-stranica-pages-i-zaglushka.md`** (страница Pages со снимком распределения и честной заглушкой, когда туннель молчит)


**`zhurnal/2026-09-02_spetsmat-bot/kod_N7-repozitorii-pages-tunnel.md`** (репозитории, Pages, origin и постоянный туннель — исполняется на машине владельца под его учёткой gh)

**`zhurnal/2026-09-02_spetsmat-bot/kod_P1-yadro.md`** (P1 волны sborka-bota: ядро — схема, миграции, журнал отметок append-only)




**`zhurnal/2026-09-02_spetsmat-bot/kod_P10-ekspluatacia.md`** (P10-ekspluatacia: systemd, сторожевой таймер изнутри цикла опроса, бэкапы и запрет выкатки в часы занятий)


**`zhurnal/2026-09-02_spetsmat-bot/kod_P11-priyomka.md`** (сквозная приёмка волны: ничего не пишет, всё прогоняет)

**`zhurnal/2026-09-02_spetsmat-bot/kod_P12-gruppy.md`** (P12: группы и закрепление, зависящее от ДНЯ ЗАНЯТИЙ)



**`zhurnal/2026-09-02_spetsmat-bot/kod_P13-ekran-auditorii.md`** (P13: экран аудитории для старшего — восемнадцать учеников с числом долгов на кнопке)


**`zhurnal/2026-09-02_spetsmat-bot/kod_P14-uvedomlenia.md`** (P14: уведомления после занятия — преподавателю вопрос, старшему сводка)


**`zhurnal/2026-09-02_spetsmat-bot/kod_P15-tekst.md`** (P15: быстрый текстовый ввод — «[7] Петров 3,5,7б» через тот же нечёткий индекс и ту же таблицу подтверждения)

**`zhurnal/2026-09-02_spetsmat-bot/kod_P16-eksport.md`** (P16-eksport: экспорт в Excel и еженедельная проверка восстановления, которая краснеет сама)


**`zhurnal/2026-09-02_spetsmat-bot/kod_P17-konstanty.md`** (P17: поднять константы в config.py — закрыть долг, порождённый слишком узкими зонами)



**`zhurnal/2026-09-02_spetsmat-bot/kod_P18-teksty.md`** (сплошной проход по текстам, которые видит человек: судит модель, которая их не писала)

**`zhurnal/2026-09-02_spetsmat-bot/kod_P19-privyazka.md`** (P19: регистрация ПРИВЯЗЫВАЕТ телеграм к ученику каталога, а не создаёт второго; и владелец узнаёт о заявке сразу)

**`zhurnal/2026-09-02_spetsmat-bot/kod_P2-import.md`** (P2: импорт прошлогоднего кондуита, засев, три независимых оракула и негативный контроль)



**`zhurnal/2026-09-02_spetsmat-bot/kod_P20-klyuchi.md`** (P20: ключ распознавания доходит до бота, имена переменных ASR сведены к одному дому)

**`zhurnal/2026-09-02_spetsmat-bot/kod_P3-registracia.md`** (P3: регистрация по deep link и три роли — ученик, преподаватель, старший аудитории)



**`zhurnal/2026-09-02_spetsmat-bot/kod_P4-setka.md`** (P4: сетка приёма — главный экран, четыре кнопки в ряд, кнопка несёт целевое состояние)


**`zhurnal/2026-09-02_spetsmat-bot/kod_P5-ekrany.md`** (P5: экраны просмотра — ученику свои плюсы и долги, преподавателю два списка первым экраном)

**`zhurnal/2026-09-02_spetsmat-bot/kod_P6-zanyatia.md`** (P6: занятия и явка — явка отличима от отсутствия отметок, отметка задним числом)



**`zhurnal/2026-09-02_spetsmat-bot/kod_P7-foto.md`** (P7: приём отметок по фотографии печатного бланка — черновик, подтверждение таблицей, журнал)


**`zhurnal/2026-09-02_spetsmat-bot/kod_P8-golos.md`** (P8: голосовое сообщение — «Петров три пять семь бэ» в отметки через ту же таблицу подтверждения)

**`zhurnal/2026-09-02_spetsmat-bot/kod_P9-listok.md`** (P9: загрузка листка старшим аудитории — разбор на задачи с метками и типами)


**`zhurnal/2026-09-02_spetsmat-bot/kod_R1-foto.md`** (фото: обрезка режет коды и подписи · прочерк приезжает как сдача)


**`zhurnal/2026-09-02_spetsmat-bot/kod_R2-slovar.md`** (словарь SpeechKit: 192 термина собираются и никуда не уезжают)


**`zhurnal/2026-09-02_spetsmat-bot/kod_R3-istochniki.md`** (сверка живого кода с ИСХОДНЫМИ документами владельца, а не с мандатом)





**`zhurnal/2026-09-02_spetsmat-bot/kod_S1-slot-i-routy.md`** (S1 волны ВЕЧЕР: слот вместо weekday в схеме и коде, плюс роуты под шаблоны контракта имён)


**`zhurnal/2026-09-02_spetsmat-bot/kod_S2-sostav-i-112-strok.md`** (S2 волны ВЕЧЕР)


**`zhurnal/2026-09-02_spetsmat-bot/kod_S3-glavnaya-i-listki.md`** (S3 волны ВЕЧЕР: главная и страницы листков по спеке владельца)


**`zhurnal/2026-09-02_spetsmat-bot/kod_S4-postoyannyj-adres.md`** (S4 волны ВЕЧЕР: постоянный адрес и починка ложно-зелёного сторожа)


**`zhurnal/2026-09-02_spetsmat-bot/kod_S5-vhod-organizatora.md`** (S5 волны ВЕЧЕР: вход дорабатывается до минимума спеки)





**`zhurnal/2026-09-02_spetsmat-bot/kod_bekap-v-papku.md`** (выгрузка архива боевой базы .db.gz в папку владельца на Google Диске, рядом с таблицей кондуита)

**`zhurnal/2026-09-02_spetsmat-bot/kod_bystro-i-bezopasno.md`** (диагноз медленного https у владельца и решение, сохраняющее профиль безопасности Google)


**`zhurnal/2026-09-02_spetsmat-bot/kod_chistka-tokenov.md`** (вычистить мёртвые строки токена из четырёх файлов и из истории git публичного репозитория)

**`zhurnal/2026-09-02_spetsmat-bot/kod_dozabivka-dolgov-sklejki.md`** (закрыть долги заходa склейки: права у кабинетов, опечатка except Value, красные тесты enrollment)




**`zhurnal/2026-09-02_spetsmat-bot/kod_dve-stranicy-raspredelenia.md`** (разделить навигацию: Распределение ведёт на ближайшее занятие с датой сверху, постоянное — отдельной страницей с колонками пн и чт)

**`zhurnal/2026-09-02_spetsmat-bot/kod_https-i-domen.md`** (HTTPS на math-kluychiki.ru: сертификат, редиректы с http и с IP, сторож на новый адрес)

**`zhurnal/2026-09-02_spetsmat-bot/kod_listki-kak-baza-zadach.md`** (листок как база задач: страница листка вместо PDF, скачивание PDF и TeX, кондуит и состав из базы, отметки 05.09)



**`zhurnal/2026-09-02_spetsmat-bot/kod_pages-i-materialy.md`** (Pages перестаёт отдавать устаревшую копию и уводит на живой сайт; /materials/ перестаёт быть вечным 404)

**`zhurnal/2026-09-02_spetsmat-bot/kod_profil-bezopasnosti.md`** (снять пометку «обманные страницы»: закрыть default_server, заголовки, robots.txt, пароль уходит по https)

**`zhurnal/2026-09-02_spetsmat-bot/kod_skleit-adminku-s-sajtom.md`** (свести рабочий редактор распределения и страницу правки на сайте в один шаблон с двумя режимами)

**`zhurnal/2026-09-02_spetsmat-bot/kod_sklejka-vhoda-s-serverom.md`** (Склейка: вход veb/vhod.py приделывается к серверу veb/server.py — единственный файл, которого не было ни в одной зоне)


**`zhurnal/2026-09-02_spetsmat-bot/kod_sloj-zanyatia.md`** (слой занятия: сегодняшнее распределение сохранить как слой на 07.09, постоянное вернуть к утреннему, дальше разделить жёстко)


**`zhurnal/2026-09-02_spetsmat-bot/kod_storozh-vstal.md`** (подключить сторож сайта таймером и сделать его тревогу доходящей и не врущей)

**`zhurnal/2026-09-02_spetsmat-bot/kod_veb-konduit-proshlogo-goda.md`** (Кондуит прошлого года на чтение: 18 листков на 56 учеников, 15847 событий, уже лежащих в базе)


**`zhurnal/2026-09-02_spetsmat-bot/kod_veb-priyom-zadach.md`** (Сетка «ученик x задачи листка»: отметка о сдаче ставится тапом, только через marking.py и progress.py)

**`zhurnal/2026-09-02_spetsmat-bot/kod_veb-raspredelenie-mvp.md`** (MVP веб-распределения: импорт базы прошлого года в enrollment и страница с двумя разрезами, где правка сохраняется в базу, а не в браузер)



**`zhurnal/2026-09-02_spetsmat-bot/kod_veb-vhod-i-obshchee-sostoyanie.md`** (Два пароля из окружения в подписанной куке и общее состояние: правка с одного компьютера видна на другом)


**`zhurnal/2026-09-02_spetsmat-bot/kod_vygruzka-v-tablicu.md`** (ночная выгрузка кондуита в Google-таблицу владельца через сервисный аккаунт Sheets API и суточный таймер)

**`zhurnal/2026-09-02_spetsmat-bot/kod_vykatka-tunnel-i-storozh.md`** (Выкатка сайта распределения наружу по HTTPS через туннель с машины владельца плюс сторож продукта)


**`zhurnal/2026-09-02_spetsmat-bot/mandate_sborka-bota.md`** (MANDATE — two halves, two authors; status OPEN/CLOSED/REFUSED lives in the file)

**`zhurnal/2026-09-02_spetsmat-bot/mandate_veb-raspredelenie.md`** (MANDATE — two halves, two authors; status OPEN/CLOSED/REFUSED lives in the file)

**`zhurnal/2026-09-02_spetsmat-bot/mandate_volna-OSNOVANIE.md`** (MANDATE — two halves, two authors; status OPEN/CLOSED/REFUSED lives in the file)

**`zhurnal/2026-09-02_spetsmat-bot/mandate_volna-vecher.md`** (MANDATE — two halves, two authors; status OPEN/CLOSED/REFUSED lives in the file)

