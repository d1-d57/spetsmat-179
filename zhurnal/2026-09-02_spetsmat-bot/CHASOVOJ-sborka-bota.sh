#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# ЧАСОВОЙ ВОЛНЫ sborka-bota. Одна обязанность, и она про МОЮ ЖЕ голову.
#
# 🔴 ЗАЧЕМ. Механика перенята у волн 6–9 (`disciplina/_studio/zhurnal/
# 2026-08-20_poryadok-v-metaskillah/STOROZH-VOLNY.sh`, решение владельца 02.09).
# Диагноз оттуда, дословно и буквально применимый: СЕССИЯ МЕЖДУ ХОДАМИ НЕ
# СУЩЕСТВУЕТ. «Проверяй каждые 10 минут» исполняется как несколько проверок
# ВНУТРИ ОДНОГО хода, после чего ход кончается — снаружи это неотличимо от
# ожидания. Ждать умеет только ПРОЦЕСС, переживающий сессию. ЦЕНА, замерена
# соседями: две волны из четырёх простояли, не начав работу, и обе считали,
# что ждут.
#
# 🔴 ЧЕМ ЭТОТ ЧАСОВОЙ ОТЛИЧАЕТСЯ ОТ СОСЕДСКОГО. Соседский `STOROZH-VOLNY.sh`
# в обязанности 2 ЯВНО пропускает свою волну («свою волну ведёт своя сессия»)
# и держит закрытый список `VSE_VOLNY` четырёх волн репозитория disciplina.
# Волна sborka-bota живёт в ДРУГОМ репозитории и в тот список не входит —
# значит поднимать её при смерти головы некому. Это ровно та слепая зона,
# которую `skills/disciplina-orkestrator/SKILL.md` объявляет своей первой:
# «единственный наблюдатель снаружи сессии сегодня — владелец».
# Здесь она закрыта: часовой смотрит за МОЕЙ головой и поднимает ЕЁ.
#
# 🔴 ЗАПУСК — ТОЛЬКО ТАК, иначе умрёт вместе с сессией:
#   nohup bash .../CHASOVOJ-sborka-bota.sh >/dev/null 2>&1 & disown
#   Отвязку проверять ТОЛЬКО ОТДЕЛЬНЫМ вызовом, после выхода запускавшей
#   оболочки: `ps -o ppid= -p <pid>` → 1. Проверка в том же шелле отвечает
#   уверенно и неверно (замер соседей 02.09 08:15).
#
# 🔴 ЧЕМ ЧАСОВОЙ ДОКАЗЫВАЕТСЯ. Не словом «я его поставил», а РОСТОМ ФАЙЛА-ПУЛЬСА.
# Поставил — проверь ДВАЖДЫ с интервалом больше периода круга, что номер круга
# и метка времени сдвинулись. Не сдвинулись — часового НЕТ, как бы он ни
# выглядел в отчёте. Жив был и тот сторож, который никого не будил.
# ═══════════════════════════════════════════════════════════════════════════
set -u
KOREN="$HOME/Documents/GitHub/spetsmat-bot"
ARKA="$KOREN/zhurnal/2026-09-02_spetsmat-bot"

PERIOD_SEK=300
MERTVA_MIN=90           # сердце молчит столько — голова считается умершей
PODYOMOV_MAX=2          # больше — петля, нужен человек

PULS="$ARKA/PULS-CHASOVOGO-sborka-bota.log"
SERDCE="$ARKA/SERDCE-VOLNY-sborka-bota.md"
LIST="$ARKA/PODYOM-VOLNY-sborka-bota.md"
MANDAT="$ARKA/mandate_sborka-bota.md"
ZAMKI="$ARKA/.chasovoj-zamki"
mkdir -p "$ZAMKI"

mtime() { stat -f %m "$1" 2>/dev/null || stat -c %Y "$1" 2>/dev/null || echo 0; }
puls()  { echo "$(date '+%F %T') $*" >> "$PULS"; }

podnyat_svoyu_golovu_esli_myortva() {
  # Признаки И-связкой, чтобы не поднять живого.
  [ -f "$LIST" ]   || { puls "подъёмного листа нет — поднимать нечем, НЕ поднимаю"; return 0; }
  [ -f "$SERDCE" ] || { puls "сердца нет — отличить «думает» от «умерла» нечем, НЕ поднимаю"; return 0; }
  grep -q '^\*\*STATUS:\*\* *`CLOSED`' "$MANDAT" 2>/dev/null && return 0
  grep -q '^\*\*STATUS:\*\* *`REFUSED`' "$MANDAT" 2>/dev/null && return 0
  pgrep -f "PODYOM-VOLNY-sborka-bota" >/dev/null 2>&1 && return 0

  local NOW TISH
  NOW=$(date +%s)
  TISH=$(( (NOW - $(mtime "$SERDCE")) / 60 ))
  [ "$TISH" -lt "$MERTVA_MIN" ] && return 0

  local SCHET_F="$ZAMKI/podyomov" SCHET=0
  [ -f "$SCHET_F" ] && SCHET=$(cat "$SCHET_F")
  if [ "$SCHET" -ge "$PODYOMOV_MAX" ]; then
    puls "⚠ голова мертва (тишина ${TISH}м), но подъёмов уже $SCHET из $PODYOMOV_MAX — НЕ поднимаю, это петля. Нужен человек."
    return 0
  fi

  # Замок атомарный: mkdir падает, если каталог есть — два часовых не поднимут две головы.
  mkdir "$ZAMKI/podnimayu" 2>/dev/null || { puls "подъём уже ведёт другой часовой, не мешаю"; return 0; }

  puls "🔴 ГОЛОВА МЕРТВА (сердце молчит ${TISH}м ≥ ${MERTVA_MIN}м, мандат открыт, подъёма в процессах нет). ПОДНИМАЮ, подъём $((SCHET+1)) из $PODYOMOV_MAX."
  echo "$((SCHET+1))" > "$SCHET_F"
  nohup claude -p --model opus --dangerously-skip-permissions "[PODYOM-VOLNY-sborka-bota] $(cat "$LIST")" >> "/tmp/podyom-sborka-bota.log" 2>&1 &
  disown 2>/dev/null || true
  sleep 30
  if pgrep -f "\[PODYOM-VOLNY-sborka-bota\]" >/dev/null 2>&1; then
    puls "✅ подъём запущен, лог /tmp/podyom-sborka-bota.log"
  else
    puls "❌ подъём НЕ поднялся — смотри /tmp/podyom-sborka-bota.log"
  fi
  rmdir "$ZAMKI/podnimayu" 2>/dev/null || true
}

puls "ЧАСОВОЙ ПОДНЯТ pid=$$ ppid=$PPID · период=${PERIOD_SEK}с · порог смерти=${MERTVA_MIN}м"

KRUG=0
while :; do
  KRUG=$((KRUG+1))
  SEJCHAS=$(date +%s)
  TISH=$(( (SEJCHAS - $(mtime "$SERDCE")) / 60 ))

  # Живые заходы волны — окна ZAPUSK-ZAHODA.sh ЭТОЙ арки плюс рабочие папки.
  OKON=$(pgrep -fl 'spetsmat-bot/zhurnal/2026-09-02_spetsmat-bot/ZAPUSK-ZAHOD[A].sh' 2>/dev/null | grep -v 'CHASOVOJ' | wc -l | tr -d ' \n')
  # Заходы, чьи файлы тронуты за последние 30 минут — работа, видимая по следу.
  SVEZHIH=0
  for F in "$ARKA"/kod_*.md; do
    [ -e "$F" ] || continue
    [ $(( (SEJCHAS - $(mtime "$F")) / 60 )) -lt 30 ] && SVEZHIH=$((SVEZHIH+1))
  done

  puls "круг $KRUG · сердце молчит ${TISH}м · окон заходов $OKON · свежих kod_* $SVEZHIH"

  podnyat_svoyu_golovu_esli_myortva

  sleep "$PERIOD_SEK"
done
