#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# СТОРОЖ БОТА. Поднимает упавшего сам и говорит об этом человеку.
#
# 🔴 ПОЧЕМУ ОН ПОЯВИЛСЯ ТОЛЬКО ВЕЧЕРОМ, И ЭТО ПРЕТЕНЗИЯ ВЛАДЕЛЬЦА 02.09 20:25:
# у ВОЛНЫ была целая машинерия против смерти — сердце, часовой, будильник,
# подъёмный лист, порог смерти, детектор убыли окон, — а у БОТА, ради которого
# волна существует, не было ничего. Он жил процессом в окне терминала владельца:
# закрыл окно — умер, упал — лежит, и узнаёт об этом человек, стоящий перед
# восемнадцатью детьми. Перевёрнутый приоритет: оснастка выживания нужна прежде
# всего продукту.
#
# 🔴 ЗАПУСКАТЬ ТОЛЬКО ПОД nohup, чтобы ppid стал 1 и он пережил любую сессию:
#     nohup bash STOROZH-BOTA.sh >> /tmp/storozh-bota.out 2>&1 & disown
#
# 🔴 ОБРАЗЕЦ ПОИСКА БОТА — БЕЗ УЧЁТА РЕГИСТРА. Урок 20, цена — поднятый второй
# экземпляр рядом с боевым: macOS запускает интерпретатор как
# `.../Python.app/Contents/MacOS/Python -m bot`, с ЗАГЛАВНОЙ P, и образец
# `python.*-m bot` не совпадает НИ С ЧЕМ, а молчание читается как «бот не идёт».
#
# 🔴 ПОТОЛОК ПОДЪЁМОВ. Бот, падающий сразу после старта, — это не «поднимай ещё
# раз», это сломанный код. После PODYOMOV_MAX за час сторож ПЕРЕСТАЁТ поднимать
# и зовёт человека: бесконечный перезапуск скрывает поломку вместо того, чтобы
# её показать.
# ═══════════════════════════════════════════════════════════════════════════
set -u
KOREN="$HOME/Documents/GitHub/spetsmat-bot"
ARKA="$KOREN/zhurnal/2026-09-02_spetsmat-bot"
PULS="$ARKA/PULS-STOROZHA-BOTA.log"
LOG_BOTA="$KOREN/logs/bot.log"
SEKRET="$KOREN/secrets/bot.env"

PERIOD_SEK=30           # чаще, чем у волнового: занятие идёт минутами, не часами
PODYOMOV_MAX=5          # за скользящий час; больше — зовём человека
OKNO_SEK=3600

puls() { echo "$(date '+%F %T') $*" >> "$PULS"; }

# Живой бот — процесс `-m bot` ЭТОГО репозитория, без учёта регистра имени
# интерпретатора. Себя и свой grep исключаем через `$1 == "bash"`-фильтр в awk.
pid_bota() {
  ps -Ao pid=,command= 2>/dev/null \
    | awk 'tolower($0) ~ /-m bot/ && $0 !~ /STOROZH-BOTA/ && $0 !~ /awk/ {print $1; exit}'
}

skazat_cheloveku() {
  # 🔴 ПАДЕНИЕ, О КОТОРОМ НИКТО НЕ УЗНАЛ, НИЧЕМ НЕ ЛУЧШЕ НЕЗАМЕЧЕННОГО ПАДЕНИЯ.
  # Токен сторожевого бота уже проверен доставленным сообщением (@watchman57_bot).
  [ -f "$SEKRET" ] || return 0
  local T C
  T=$(awk -F= '/^ALERT_TOKEN=/{print $2}' "$SEKRET" | tr -d ' \r\n')
  C=$(awk -F= '/^OWNER_ID=/{print $2}' "$SEKRET" | tr -d ' \r\n')
  [ -n "$T" ] && [ -n "$C" ] || { puls "⚠ нет ALERT_TOKEN или OWNER_ID — сказать некому"; return 0; }
  curl -s -m 20 -X POST "https://api.telegram.org/bot$T/sendMessage" \
       --data-urlencode "chat_id=$C" --data-urlencode "text=$1" >/dev/null 2>&1 \
    && puls "→ владельцу отправлено: $1" \
    || puls "⚠ отправить владельцу НЕ УДАЛОСЬ: $1"
}

podnyat() {
  cd "$KOREN" || return 1
  mkdir -p "$KOREN/logs"
  set -a; . "$SEKRET"; set +a
  nohup python3 -m bot >> "$LOG_BOTA" 2>&1 &
  disown 2>/dev/null || true
  sleep 8                       # даём построиться диспетчеру и начать опрос
  pid_bota
}

puls "СТОРОЖ БОТА ПОДНЯТ pid=$$ ppid=$PPID · период=${PERIOD_SEK}с · потолок=${PODYOMOV_MAX}/час"
PODYOMY=""                       # метки времени подъёмов, для скользящего окна
BYL_ZHIV=1

while :; do
  PID=$(pid_bota)
  SEJCHAS=$(date +%s)

  if [ -n "$PID" ]; then
    [ "$BYL_ZHIV" = "0" ] && puls "✅ бот снова жив, pid $PID"
    BYL_ZHIV=1
  else
    BYL_ZHIV=0
    # чистим окно подъёмов
    NOVYE=""
    for m in $PODYOMY; do [ $((SEJCHAS - m)) -lt $OKNO_SEK ] && NOVYE="$NOVYE $m"; done
    PODYOMY="$NOVYE"
    SCHET=$(echo $PODYOMY | wc -w | tr -d ' ')

    if [ "$SCHET" -ge "$PODYOMOV_MAX" ]; then
      puls "🔴 БОТ УПАЛ, но подъёмов за час уже $SCHET из $PODYOMOV_MAX — НЕ поднимаю, это петля."
      skazat_cheloveku "🔴 Бот упал $SCHET раз за час и больше не поднимается сам. Это не сбой связи, а поломка кода. Лог: $LOG_BOTA"
      sleep 300
      continue
    fi

    puls "🔴 БОТ НЕ НАЙДЕН — поднимаю (подъём $((SCHET+1)) из $PODYOMOV_MAX за час)"
    NOVYJ=$(podnyat)
    PODYOMY="$PODYOMY $SEJCHAS"
    if [ -n "$NOVYJ" ]; then
      puls "✅ поднят заново, pid $NOVYJ"
      skazat_cheloveku "⚠️ Бот падал и поднят сторожем в $(date '+%H:%M:%S'). Новый pid $NOVYJ. Если это повторится — смотрите $LOG_BOTA"
    else
      puls "❌ подъём НЕ УДАЛСЯ — смотри $LOG_BOTA"
      skazat_cheloveku "🔴 Бот упал и НЕ ПОДНЯЛСЯ. Нужен человек. Лог: $LOG_BOTA"
    fi
  fi
  sleep "$PERIOD_SEK"
done
