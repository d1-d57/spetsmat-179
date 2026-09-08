ЗАЯВКА: 2026-09-08T17:13 · автор: host · арка: не названа
СРОЧНОСТЬ: obychnaya
РОД: git-operaciya

main опережает origin/main на 2 коммита (влитие zahod/storozh-vstal, штатно, без конфликтов, fast-forward-совместимо) -- заход storozh-vstal НЕ вывозит main сам (§5 WARNING-блока), нужен push origin main от владельца/аналитика

КАК ВЛИВАТЬ: ЧТО: вливать нечего, всё уже в локальном main (zahod/storozh-vstal влита заходом самостоятельно, git log main..zahod/storozh-vstal = 0) · ГДЕ ЖДАТЬ КОНФЛИКТА: конфликта нет, операция односторонняя; если origin успел уйти вперёд -- на README.md, реестр регистраций · ЧЬЕЙ СТОРОНОЙ: README.md разрешать ОБЪЕДИНЕНИЕМ записей реестра, никогда выбором стороны · ПОСЛЕ: git log --oneline origin/main..main | wc -l -> 0
