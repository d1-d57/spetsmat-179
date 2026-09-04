#!/bin/bash
# РЫЧАГ ПРИЁМКИ волны ВЕЧЕР. Прогоняет критерий САМ, а не читает отчёт:
# замерено — 2 минуты на позицию против 8 при чтении отчёта.
#   bash RYCHAG-VECHER.sh <позиция>
# Позиции: S1 S2 S3 S4 S5
set -u
R="$HOME/Documents/GitHub/spetsmat-bot"
PORT="${PORT:-8899}"
cd "$R" || exit 1

# 🔴 СЕРВЕР НЕ СТАРТУЕТ БЕЗ ПЕРЕМЕННЫХ — замерено рычагом на main:
# veb/server.py main() зовёт vhod.proverit_okruzhenie(), и без SPETSMAT_VEB_SECRET
# процесс падает с RuntimeError ещё до первого запроса. Это не дефект позиции,
# это условие запуска; рычаг обязан его выполнять, иначе краснеет на пустом месте.
export SPETSMAT_VEB_SECRET="${SPETSMAT_VEB_SECRET:-rychag-priyomki-vechera-ne-dlya-boya}"
export SPETSMAT_VEB_PAROL_ORG="${SPETSMAT_VEB_PAROL_ORG:-rychag-org}"
export SPETSMAT_VEB_PAROL_PREPOD="${SPETSMAT_VEB_PAROL_PREPOD:-rychag-prepod}"

podnyat() {
  python3 -m veb.server --port "$PORT" >/tmp/rychag-veb.log 2>&1 &
  echo $! > /tmp/rychag-veb.pid
  for i in 1 2 3 4 5 6 7 8 9 10; do
    curl -sS -o /dev/null "http://localhost:$PORT/" 2>/dev/null && return 0
    perl -e 'select(undef,undef,undef,0.5)'
  done
  return 1
}
opustit() { [ -f /tmp/rychag-veb.pid ] && kill "$(cat /tmp/rychag-veb.pid)" 2>/dev/null; rm -f /tmp/rychag-veb.pid; }

case "${1:-}" in
S1)
  echo "── S1: роуты и слот ──"
  podnyat || { echo "🔴 сервер не поднялся, лог:"; tail -20 /tmp/rychag-veb.log; exit 1; }
  for a in / /raspredelenie /listki /listki-8 /urovni; do
    curl -sS -o /dev/null -w "%{http_code} $a\n" "http://localhost:$PORT$a"
  done
  echo "── /api/view (слот) ──"
  curl -sS "http://localhost:$PORT/api/view?slot=1" | head -c 400; echo
  echo "── weekday ещё жив в коде? (должно быть пусто или только совместимость) ──"
  grep -c 'weekday' veb/server.py
  echo "── тесты ──"; python3 -m pytest tests/veb -q 2>&1 | tail -3
  opustit ;;
S2)
  echo "── S2: состав и 112 строк ──"
  python3 -c "import sqlite3,collections;c=sqlite3.connect('data/spetsmat.db');k=collections.Counter(r[0] for r in c.execute('select student_id from enrollment'));print('строк',sum(k.values()),'детей',len(k),'раскладка',dict(collections.Counter(k.values())),'без единой строки',c.execute('select count(*) from students where id not in (select student_id from enrollment)').fetchone()[0])"
  echo "── инструмент проверки (ищу его сам) ──"; ls tools/*sostav* tools/*proverk* 2>/dev/null
  echo "── ушедшие и пришедший ──"
  python3 -c "import sqlite3;c=sqlite3.connect('data/spetsmat.db');[print(r) for r in c.execute(\"select id,familia,imya,klass,status from students where familia in ('Майоров','Емельянцев','Ишкаев')\")]" 2>&1 | head
  echo "── тесты ──"; python3 -m pytest tests/test_sostav.py -q 2>&1 | tail -3 ;;
S3)
  echo "── S3: шаблоны ──"
  ls -la veb/templates/
  echo "── битые ссылки: href/src на локальные файлы ──"
  grep -rhoE '(href|src)="[^"#?:]+"' veb/templates/ 2>/dev/null | sed 's/.*="//; s/"//' | sort -u | while read -r p; do
    case "$p" in /*) f="veb/static${p}";; *) f="veb/templates/$p";; esac
    [ -e "$f" ] || [ -e "veb/$p" ] || echo "  ⚠ не найден на диске: $p"
  done
  echo "── страницы живьём ──"
  podnyat || { echo "🔴 сервер не поднялся"; exit 1; }
  for a in / /listki /listki-8 /urovni; do
    echo "--- $a ---"; curl -sS "http://localhost:$PORT$a" | sed 's/<[^>]*>//g' | grep -v '^\s*$' | head -12
  done
  opustit ;;
S4)
  echo "── S4: постоянный адрес ──"
  echo "ADRES.txt:"; cat deploy/ADRES.txt 2>/dev/null
  A="$(head -1 deploy/ADRES.txt 2>/dev/null)"
  [ -n "$A" ] && curl -sS -o /dev/null -w "туннель → %{http_code}\n" --max-time 15 "$A"
  echo "── сторож ──"; python3 ops/storozh_sajta.py 2>&1 | head -5
  echo "── сторож на баннере провайдера (обязан НЕ сказать «жив») ──"
  SPETSMAT_ADRES="https://console.serveo.net" python3 ops/storozh_sajta.py 2>&1 | head -3
  echo "── тесты ──"; python3 -m pytest tests/ops -q 2>&1 | tail -3 ;;
S5)
  echo "── S5: вход ──"
  podnyat || { echo "🔴 сервер не поднялся"; exit 1; }
  echo "чтение БЕЗ куки:"
  curl -sS -o /dev/null -w "  /raspredelenie → %{http_code}\n" "http://localhost:$PORT/raspredelenie"
  curl -sS "http://localhost:$PORT/api/view?slot=1" | head -c 300; echo
  echo "правка БЕЗ куки (обязан отказ, не 200 и не 500):"
  curl -sS -o /dev/null -w "  POST → %{http_code}\n" -X POST -H 'Content-Type: application/json' \
    -d '{"student_id":1,"teacher_id":2,"slot":1}' "http://localhost:$PORT/api/enrollment"
  echo "── модуль входа подключён? ──"
  curl -sS -o /dev/null -w "  /vhod → %{http_code}\n" "http://localhost:$PORT/vhod"
  echo "── тесты ──"; python3 -m pytest tests/veb/test_vhod.py -q 2>&1 | tail -3
  opustit ;;
*) echo "нужна позиция: S1 S2 S3 S4 S5"; exit 2 ;;
esac
