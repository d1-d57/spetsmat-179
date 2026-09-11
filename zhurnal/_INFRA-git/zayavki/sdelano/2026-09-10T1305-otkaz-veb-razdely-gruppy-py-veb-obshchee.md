ЗАЯВКА: 2026-09-10T13:05 · автор: host · арка: не названа
СРОЧНОСТЬ: blokiruet
РОД: git-operaciya

ОТКАЗ GIT-ОПЕРАЦИИ: коммит зоны veb/razdely/gruppy.py, veb/obshchee/karkas.py
КОМАНДА: git_zona.py commit --zone veb/razdely/gruppy.py, veb/obshchee/karkas.py -m …
КОД ВОЗВРАТА: 1
ОШИБКА: [проверка индекса на чужое вне контракта зоны] rc=1: застейджено 1 путей вне зоны `veb/razdely/gruppy.py, veb/obshchee/karkas.py`: data/spetsmat.db
ЧТО НУЖНО ОТ АНАЛИТИКА: разобрать, чьё красное встало на пути (своё чинится, чужой долг обходится --no-verify С ПРИЧИНОЙ), и вернуть заходу замечание
ПОПЫТКА: 2026-09-10T13:05 · тот же отказ на той же операции, попытка 2 — новой заявки НЕ завожу
ЗАКРЫТО: 2026-09-11T10:23 · РАЗОБРАНО ОРКЕСТРАТОРОМ волны НОЧЬ-2 11.09 10:2x: отказ прошлой волны (10.09), работа не потеряна. Проверено фактом, а не рассуждением: все ветки заходов 10.09 (vidy-zadach, poisk-i-kartochka, kanal-diagnostika, statistiki-i-grobarij, paroli-shkolnikov, adres-bazy, data-i-istoria-kletki) ВЛИТЫ в main — git merge-base --is-ancestor по каждой. main вывезен на origin 11.09 03:09 зелёным (26 упавших против 29 в базовой линии, одна команда, два чистых дерева).
