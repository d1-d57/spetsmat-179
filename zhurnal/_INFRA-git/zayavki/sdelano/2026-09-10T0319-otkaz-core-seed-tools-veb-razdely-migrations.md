ЗАЯВКА: 2026-09-10T03:19 · автор: host · арка: не названа
СРОЧНОСТЬ: blokiruet
РОД: git-operaciya

ОТКАЗ GIT-ОПЕРАЦИИ: коммит зоны core, seed, tools, veb/razdely, migrations, tests/sheets
КОМАНДА: git_zona.py commit --zone core, seed, tools, veb/razdely, migrations, tests/sheets -m …
КОД ВОЗВРАТА: 128
ОШИБКА: [предполётный диагноз состояния репозитория] rc=128: незаконченная операция git: MERGE — незаконченное слияние → git_zona.py merge --continue (разрешив конфликты) либо merge --abort; pathspec-коммит отказывает `fatal: cannot do a partial commit during a merge`
ЧТО НУЖНО ОТ АНАЛИТИКА: разобрать, чьё красное встало на пути (своё чинится, чужой долг обходится --no-verify С ПРИЧИНОЙ), и вернуть заходу замечание
ЗАКРЫТО: 2026-09-10T03:43 · Разобрано заходом vidy-zadach, чью зону заявка называет. Отказ не содержательный: предполётный диагноз git_zona.py увидел ГЛАВНУЮ папку в незавершённом слиянии СОСЕДА (MERGE_HEAD = 8249a44, заход poisk-i-kartochka, отдельная заявка 2026-09-10T0256) и отказался от pathspec-коммита с rc=128 — 'cannot do a partial commit during a merge'. Ни одной строки моей работы это не остановило: все семь коммитов зоны сделаны прямыми 'git add -- <пути>' + 'git commit -- <пути>', как велит §4 захода, и все семь прошли (dfd1ac8 b13c169 341603b 301f7bb bb6af86 a0c8311 55ad7a4, плюс влитие ee3922c). Чужое слияние к этому моменту рассосалось: .git/MERGE_HEAD в главной папке нет. Ворота зоны сейчас: core/ seed/ tools/ migrations/ tests/sheets/ — все пять зелёные; veb/razdely/ красная ЧУЖИМ (glavnaya.py, kartochka.py, shkolniki.py заходов poisk-i-kartochka и соседей), мой konduit.py в git.
