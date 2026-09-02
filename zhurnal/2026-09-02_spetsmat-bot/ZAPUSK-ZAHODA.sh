#!/bin/bash
# Запуск ОДНОГО захода волны sborka-bota (репозиторий spetsmat-bot).
#   bash ZAPUSK-ZAHODA.sh <имя-захода> <модель> [--dobor]
#
# 🔴 ПОЧЕМУ ЭТА ЗАПУСКАЛКА ЕСТЬ, А НЕ СТРОКА ГЕНЕРАТОРА.
# `bootstrap_zahod.py --dvizhok claude` вписывает в стартовую строку ARN
# Bedrock (`arn:aws:bedrock:us-east-1:811345154057:...`). На ЭТОЙ машине
# Bedrock-доступа НЕТ вовсе: ни `~/.aws/`, ни переменных `AWS_*`,
# `ANTHROPIC_BASE_URL=https://api.anthropic.com` (замер 2026-09-02 08:22,
# командой `ls -d ~/.aws; env | grep -c '^AWS_'` → «No such file», 0).
# Цена уже оплачена соседней волной 2026-09-02 07:07: ПЯТЬ платных позиций
# из пяти оборвались за девять минут, в каждом логе «API Error: Could not
# load credentials from any providers». Снаружи это неотличимо от «заход
# думает», и добор перезапускает в пустоту.
# Развилка ниже — та же, что уже вшита в починенный
# `disciplina/_studio/zhurnal/2026-08-20_poryadok-v-metaskillah/ZAPUSK-ZAHODA.sh`:
# есть Bedrock-креды — идём ARN, нет — штатной авторизацией `claude` по
# родовому имени модели. Проверено живьём 2026-09-02 08:22:
# `claude -p --model sonnet` → rc=0, `claude -p --model opus` → rc=0.
#
# 🔴 МОДЕЛЬ ПРИХОДИТ АРГУМЕНТОМ, а не вшита. Урок 55 (стоил ночи): имя модели
# жило в пяти домах, провайдер снял модель с раздачи, поправили в одном — волна
# работала в пустоту.
set -u
Z="${1:?нужно имя захода, например: bash ZAPUSK-ZAHODA.sh P1-yadro opus}"
MODEL="${2:?нужна модель вторым аргументом: opus | sonnet | openrouter/...:free}"
REZHIM="${3:-}"

KOREN="$HOME/Documents/GitHub/spetsmat-bot"
INSTR="$HOME/Documents/GitHub/disciplina/_generator/tools"
ARKA="zhurnal/2026-09-02_spetsmat-bot"
FAJL="$KOREN/$ARKA/kod_$Z.md"
WT="$HOME/Documents/GitHub/spetsmat-bot-wt"

export GIT_ZONA_REPO="$KOREN"

if [ ! -f "$FAJL" ]; then
  echo "❌ нет файла-захода: $FAJL"
  exit 1
fi

OBSHEE="Прочитай ТОЛЬКО его и то, что он называет; остальной проект не изучай. План/вопросы/отчёт пиши в этот же файл внизу (## ПЛАН / ## ВОПРОСЫ / ## ОТЧЁТ), НА АНГЛИЙСКОМ. Ничего сверх задачи не трогай — «ничего сверх задачи» относится к СОДЕРЖАНИЮ работы. Субагентов не зови ни на что, кроме верификатора §3; коммиты делай сам, по ходу работы, а не одним последним ходом. 🔴 Частей в задании несколько: делай ПО ПОРЯДКУ, коммить КАЖДУЮ отдельно; не успел — назови несделанные списком в ## ОТЧЁТ, это законный исход."

OTMENA="🔴 ОТМЕНА ОДНОГО ПУНКТА ТВОЕГО ЗАХОДА, ЧИТАЙ ЭТО ПЕРВЫМ. СУБАГЕНТА ГИТ-КОНТУРА §0.1 НЕ ЗАПУСКАЙ. §0.1 велит начать с него — пункт ОТМЕНЁН оркестратором, данное указание сильнее текста захода. Причина замерена соседней волной: четыре захода из десяти умерли ровно на этом вызове. Вместо всего блока §0.1 выполни САМ одну команду и вставь её вывод в ## ОТЧЁТ: git --no-optional-locks branch --no-merged main | grep -c zahod/ . Заполни в ## ГИГИЕНА ВХОДА строку **ВСЕ ДОЛГИ ВХОДА ЗАКРЫТЫ:** словом да или нет и вставь туда вывод той единственной команды — без этой строки приёмка краснеет гейтом Г12, и краснеет по вине отмены, а не по твоей. Дальше сразу иди в свою рабочую папку и работай по задаче. СВОЮ зону коммитишь по ходу. Верификатор §3 остаётся в силе. Ветку в конце вливаешь САМ, последним ходом, после коммита зоны."

if [ "$REZHIM" = "--dobor" ]; then
  PROMPT="$OTMENA | Дальше: твой заход — файл $FAJL. 🔴 ЭТО ПЕРЕЗАПУСК ПОСЛЕ ОБРЫВА, а не новый заход. Вторым ходом, до работы: прочитай в файле-заходе разделы ## ПЛАН, ## ОТЧЁТ и ## ПРАВКИ ПОСЛЕ ВЫДАЧИ, если они есть, и выполни 'git --no-optional-locks log --oneline -20' в своей рабочей папке — вместе они говорят, что уже сделано и закоммичено. Продолжай С МЕСТА ОБРЫВА. С нуля НЕ начинай и уже сделанное НЕ переделывай. Первой строкой в ## ОТЧЁТ напиши, на чём прошлый прогон остановился и с чего ты продолжил. $OBSHEE"
else
  PROMPT="$OTMENA | Дальше: твой заход — файл $FAJL. $OBSHEE"
fi

echo "══ заход: $Z ${REZHIM:+($REZHIM)}  ·  модель: $MODEL"
cd "$KOREN" || exit 1

# 🔴 КОД ВОЗВРАТА `worktree add` НЕ СУДИМ — судим машинный факт: папка на месте
# и стоит на нужной ветке. На повторе команда возвращает ненулевой код при
# живом состоянии, и `|| exit 1` убил бы все окна волны на первой же строке.
python3 "$INSTR/git_zona.py" worktree add "$Z" --branch "zahod/$Z"

if [ ! -d "$WT/$Z" ]; then
  echo "❌ рабочей папки нет: $WT/$Z — и завести её не удалось."
  exit 1
fi
cd "$WT/$Z" || exit 1

VETKA=$(git --no-optional-locks rev-parse --abbrev-ref HEAD 2>/dev/null)
if [ "$VETKA" != "zahod/$Z" ]; then
  echo "⚠ папка стоит на '$VETKA', а нужна 'zahod/$Z' — переставляю."
  if git --no-optional-locks show-ref --verify --quiet "refs/heads/zahod/$Z"; then
    git --no-optional-locks checkout "zahod/$Z" 2>&1 | tail -2
  else
    git --no-optional-locks checkout -b "zahod/$Z" 2>&1 | tail -2
  fi
  VETKA=$(git --no-optional-locks rev-parse --abbrev-ref HEAD 2>/dev/null)
  if [ "$VETKA" != "zahod/$Z" ]; then
    echo "❌ переставить не удалось: осталось '$VETKA'."
    exit 1
  fi
fi

echo "══ рабочая папка: $(pwd)  ·  ветка: $VETKA"
echo "══ старт: $(date '+%F %T')"

# ── Движок по имени модели: со слэшем или :free — opencode, родовое имя — claude.
case "$MODEL" in
  *:free|*/*) DVIZHOK=opencode ;;
  *)          DVIZHOK=claude ;;
esac

LOG="/tmp/zahod-$Z.log"

if [ "$DVIZHOK" = "opencode" ]; then
  opencode run --auto --model "$MODEL" "$PROMPT" < /dev/null 2>&1 | tee -a "$LOG"
else
  BEDROCK_EST=0
  if [ -n "${AWS_ACCESS_KEY_ID:-}${AWS_PROFILE:-}${AWS_ROLE_ARN:-}${AWS_WEB_IDENTITY_TOKEN_FILE:-}${AWS_CONTAINER_CREDENTIALS_RELATIVE_URI:-}" ] \
     || [ -f "$HOME/.aws/credentials" ] || [ -f "$HOME/.aws/config" ]; then
    BEDROCK_EST=1
  fi
  if [ "$BEDROCK_EST" = "1" ]; then
    ARN=$(python3 "$INSTR/modeli.py" "$MODEL" 2>/dev/null | tail -1 | sed 's/.*→ *//')
    case "$ARN" in
      arn:aws:bedrock:*) : ;;
      *) echo "❌ modeli.py вернул не ARN для «$MODEL»: ${ARN:-пусто}"; exit 1 ;;
    esac
    CLAUDE_CODE_USE_BEDROCK=1 claude -p --model "$ARN" --dangerously-skip-permissions "$PROMPT" < /dev/null 2>&1 | tee -a "$LOG"
  else
    echo "⚠ Bedrock-доступа на машине нет — иду штатной авторизацией claude, модель «$MODEL»."
    claude -p --model "$MODEL" --dangerously-skip-permissions "$PROMPT" < /dev/null 2>&1 | tee -a "$LOG"
  fi
fi

# 🔴 ГОТОВНОСТЬ = ЗАПОЛНЕННЫЙ ОТЧЁТ С ХЭШЕМ, А НЕ ЗАГОЛОВОК. Заголовок
# «## ОТЧЁТ» стоит в каркасе с рождения: сторож соседней волны, судивший по
# нему, объявил 22 готовых из 22 при нуле написанных отчётов.
if grep -q '^## ОТЧЁТ' "$FAJL" 2>/dev/null &&
   sed -n '/^## ОТЧЁТ/,$p' "$FAJL" | grep -qE '`[0-9a-f]{7,}`|КОММИТА НЕТ|коммита нет'; then
  echo "══ отчёт с коммитом на месте — заход закончил."
else
  echo "══ 🔴 ВЫШЕЛ БЕЗ ОТЧЁТА С ХЭШЕМ. Это НЕ успех: смотри $LOG и решай про добор."
fi

echo "══ заход $Z закончил в $(date '+%F %T'). Лог: $LOG"
