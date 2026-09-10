ЗАЯВКА: 2026-09-10T05:17 · автор: host · арка: не названа
СРОЧНОСТЬ: blokiruet
РОД: git-operaciya

ОТКАЗ GIT-ОПЕРАЦИИ: влитие ветки zahod/kabinet-prepodavatelya в основную main — конфликт в 1 путях
КОМАНДА: git_zona.py vlit-v-osnovnuyu zahod/kabinet-prepodavatelya
КОД ВОЗВРАТА: 1
ОШИБКА: конфликтуют: veb/server.py
ЧТО НУЖНО ОТ АНАЛИТИКА: решить, чьей стороной разрешать конфликт (это смысловое решение, инструмент его не принимает), затем vlit-v-osnovnuyu --continue или --abort
ЗАКРЫТО: 2026-09-10T05:28 · Конфликт разрешён самим заходом ОБЪЕДИНЕНИЕМ, а не выбором стороны: спор был в реестре RAZDELY_S_MARSHRUTAMI (veb/server.py) — соседний заход дописал в тот же кортеж 'veb.razdely.vnesenie', этот дописал 'veb.razdely.kabinet'. Обе записи правы, выбор одной уничтожил бы регистрацию соседа. В main стоят обе; _marshruty_razdelov() из главной папки собирает 14 маршрутов, соседские /vnesti* на месте, свои /kabinet и /api/kabinet/otsutstvie на месте. Слияние завершено: b2e35be, затем e25bbc2.
