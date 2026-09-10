ЗАЯВКА: 2026-09-10T18:11 · автор: host · арка: не названа
СРОЧНОСТЬ: obychnaya
РОД: git-operaciya

вывоз main: после влития zahod/adres-bazy в main 6 невывезенных коммитов (origin https://github.com/d1-d57/spetsmat-179.git). main заход не вывозит по канону — публикация main есть решение владельца

КАК ВЛИВАТЬ: ЧТО: вливать нечего, ветка zahod/adres-bazy УЖЕ влита (merge 8906b48), нужен только push main в origin · ГДЕ ЖДАТЬ КОНФЛИКТА: нигде при push; если origin/main ушёл вперёд — конфликт возможен на .gitignore и config.py · ЧЬЕЙ СТОРОНОЙ: .gitignore разрешать ОБЪЕДИНЕНИЕМ правил, но исключение !data/spetsmat.db не восстанавливать ни при каких условиях (решение владельца 10.09 «нет, ни одного»); config.py — стороной этой ветки, там снят молчаливый DB_PATH · ПОСЛЕ: из главной папки SPETSMAT_BAZA=<путь> python3 core/istochnik.py (обязан назвать путь, род, свежесть, вердикт) и python3 -m pytest tests/istochnik/ -q (24 зелёных)
