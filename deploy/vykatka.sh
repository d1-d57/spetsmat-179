#!/usr/bin/env bash
#
# Deploy: rsync a named list of paths to the server, restart the site, prove it answers 200.
#
# 🔴 THE TARGET IS NOT A GIT CHECKOUT.  `/opt/spetsmat-bot` on the server is a plain
# directory of files -- there is no `.git` in it and there never was.  The previous version
# of this script opened with "Deploy: pull, migrate, restart" and ran `git pull` there, so
# it could not work, and the runbook beside it said "There is no server yet" while the
# server was serving a lesson.  Two passes in a row therefore re-derived the way to deploy
# by hand, live, on the production machine.  This script exists so that the third one does
# not have to.  This runs FROM a laptop checkout and PUSHES over ssh; it is not run on the
# server.
#
# THE SINGLE MOST USEFUL LINE IN THIS SCRIPT IS STILL THE REFUSAL TO DEPLOY DURING A LESSON,
# and it is still the first thing that runs.  Two instances of one bot cannot poll Telegram
# at once: the second gets TelegramConflictError, and during a restart there is a moment
# when both exist.  During a lesson that moment is eighteen teachers tapping into a bot that
# answers nobody.  Blue-green is not merely redundant here -- it is impossible, for the same
# reason.
#
# PROVABLE WITHOUT A SERVER:
#   bash deploy/vykatka.sh --proba --chas-zanyatia   # must REFUSE  (rc=3)
#   bash deploy/vykatka.sh --proba --svobodnyj-chas  # must proceed (rc=0), touching nothing
#
# ROLLBACK:
#   bash deploy/vykatka.sh --otkat                   # restore the latest snapshot, restart
#
set -euo pipefail

CHECKOUT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVER="${SPETSMAT_SERVER:-ivan@159.194.254.52}"
TARGET="${SPETSMAT_TARGET:-/opt/spetsmat-bot}"
PUBLIC_URL="${SPETSMAT_URL:-http://159.194.254.52/}"
UNIT_VEB="${SPETSMAT_UNIT_VEB:-spetsmat-veb.service}"
UNIT_BOT="${SPETSMAT_UNIT_BOT:-spetsmat-bot.service}"
PYTHON="${PYTHON:-python3}"
SSH="ssh -o BatchMode=yes -o ConnectTimeout=15"
OZHIDANIE_200=30          # seconds the site is given to answer 200 after the restart
DRY_RUN=0
CLOCK=""
ROLLBACK_ONLY=0

#: Distinct exit codes, because "refused on purpose" and "broke" must not look alike.
RC_REFUSED_LESSON=3
RC_DIRTY_TREE=4
RC_STEP_FAILED=5
RC_ROLLED_BACK=6
RC_MIGRATION_NEEDS_A_HUMAN=7

# --------------------------------------------------------------- what is rolled out
#
# 🔴 THE ORDER OF THIS LIST IS PART OF THE MACHINERY, NOT TIDINESS.  `veb/` goes before
# `tools/`, because `tools/sobrat_stranicu.py` imports `veb.razdely` and `veb.obshchee`,
# and `veb/server.py` calls that tool after every successful write to the database.  Send
# the tool first and there is a window in which the live server imports a package that is
# not on disk yet: every save during that window is a 500.  Additions first, then the file
# that starts depending on them, and the window closes before it opens.
VYKATYVAEM=(
  veb
  tools
  bot
  core
  infra
  ops
  migrations
  seed
  deploy
  config.py
  bot.env.example
  Makefile
  pyproject.toml
)

# 🔴 NEVER ROLLED OUT -- THE LIST LIVES HERE, IN THE SCRIPT, AND NOT IN THE HEAD OF WHOEVER
# TYPES THE COMMAND.  A list that lives in a head is a list that is remembered on the good
# days.  Each of these three is a way to destroy a working day:
#   * `data/` -- the LIVE database.  It holds today's marks for 53 pupils and 14 teachers,
#     and the laptop copy is not a fresher version of it but an older, different one: a
#     measurement on 2026-09-04 found the server knowing `Полина Романова` where the laptop
#     knew only `Полина`.  Overwriting it loses a day of a school.
#   * `secrets/` -- `veb.env` with the two shared passwords and `veb-lichnye-paroli.json`
#     with the hashes of the personal ones.  The laptop files are NOT the same files, and
#     the repository is public.
#   * `docs/index.html` -- the server rebuilds it itself after every save.  A copy pushed
#     from here is overwritten within the minute, and until it is, it shows stale data of
#     the wrong day to whoever opens the site.
NE_VYKATYVAEM=(
  --exclude 'data/'
  --exclude 'secrets/'
  --exclude 'docs/index.html'
  --exclude 'logs/'
  --exclude '__pycache__/'
  --exclude '*.pyc'
  --exclude '.git/'
)

usage() {
  cat <<'USAGE'
usage: bash deploy/vykatka.sh [--proba] [--chas-zanyatia | --svobodnyj-chas] [--otkat]

  --proba            print every step, change nothing, touch no network
  --chas-zanyatia    ask the schedule about a known LESSON moment instead of the clock
  --svobodnyj-chas   ask the schedule about a known FREE moment instead of the clock
  --otkat            restore the latest snapshot on the server and restart; deploy nothing

exit codes: 0 deployed  3 refused, a lesson is running  4 the rolled-out paths are dirty
            5 a step failed  6 deployed and rolled back (the site did not answer 200)
            7 a migration is pending and a human must decide
USAGE
}

for argument in "$@"; do
  case "$argument" in
    --proba) DRY_RUN=1 ;;
    --otkat) ROLLBACK_ONLY=1 ;;
    --chas-zanyatia|--svobodnyj-chas)
      # The two simulation flags are mutually exclusive.  With "last one wins" the pair
      # `--chas-zanyatia --svobodnyj-chas` deployed and the reverse order refused, which is
      # a coin toss dressed as a decision.  Found by the §3 verifier.
      if [ -n "$CLOCK" ] && [ "$CLOCK" != "$argument" ]; then
        echo "$argument contradicts $CLOCK -- name one moment, not two" >&2
        exit 64
      fi
      CLOCK="$argument" ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $argument" >&2; usage >&2; exit 64 ;;
  esac
done

run() {
  if [ "$DRY_RUN" = 1 ]; then
    echo "  would run: $*"
  else
    "$@"
  fi
}

say() { echo "== $*"; }

cd "$CHECKOUT"

# ------------------------------------------------------------------ 1. the refusal
#
# FIRST, before the snapshot, before the transfer, before anything that costs time or
# changes state.  A refusal that arrives after half the files have moved is not a refusal,
# it is a half-deploy.
#
# The answer comes from ops/raspisanie.py and from nowhere else: one place knows when a
# lesson is, so the deploy and the backup timers cannot disagree about it.
#
# THE ANSWER MUST BE AN ANSWER, NOT AN EMPTY STRING.  `if reason="$(...)"` looks only at the
# exit code.  An interpreter that exits 0 and prints nothing -- `PYTHON=/usr/bin/true`, a
# stub on PATH, a truncated checkout -- therefore produced a silent green and a deploy in
# the middle of a lesson.  Found by the §3 verifier.  A broken interpreter already failed
# closed (rc != 0 -> refuse); a SILENT one did not, and now both do.  The refusal is the
# safe side, so anything unexpected lands on it.

say "is a lesson running?"
if reason="$("$PYTHON" "$CHECKOUT/ops/raspisanie.py" $CLOCK)"; then
  if [ -z "$reason" ]; then
    echo "REFUSED: the schedule answered nothing at all -- $PYTHON is not running" >&2
    echo "ops/raspisanie.py.  Refusing rather than guessing that no lesson is on." >&2
    exit "$RC_REFUSED_LESSON"
  fi
  echo "  $reason"
else
  echo "  $reason"
  cat >&2 <<EOF

REFUSED: no deploy during a lesson.

  $reason

Two instances of one bot cannot poll Telegram at once -- the second gets
TelegramConflictError -- and a restart is precisely the moment when both exist.
Deploy after the lesson, or outside the guard window around it.
EOF
  exit "$RC_REFUSED_LESSON"
fi

# ------------------------------------------------------------------------ the rollback
#
# `--otkat` is a whole mode and not a step: it is what you type when the site is already
# broken, so it must not depend on anything the broken deploy left behind.  The pointer file
# is written by every deploy and names the snapshot that deploy made.

otkatit() {
  local pochemu="$1"
  say "ОТКАТ: $pochemu"
  if [ "$DRY_RUN" = 1 ]; then
    echo "  would restore $TARGET from the snapshot named in $TARGET-bak-POSLEDNYAYA"
    echo "  would run: systemctl restart $UNIT_VEB"
    return 0
  fi
  $SSH "$SERVER" "set -e
    BAK=\$(sudo cat $TARGET-bak-POSLEDNYAYA 2>/dev/null || true)
    if [ -z \"\$BAK\" ] || [ ! -d \"\$BAK\" ]; then
      echo 'НЕТ КОПИИ: $TARGET-bak-POSLEDNYAYA is empty or names a directory that is gone' >&2
      echo 'Restore by hand: ls -d $TARGET-bak-* | tail -1' >&2
      exit 1
    fi
    echo \"  restoring from \$BAK\"
    for D in \$(cd \"\$BAK\" && ls); do
      sudo rsync -a \"\$BAK/\$D\" $TARGET/
    done
    sudo systemctl restart $UNIT_VEB"
}

if [ "$ROLLBACK_ONLY" = 1 ]; then
  otkatit "asked for by hand"
  if [ "$DRY_RUN" = 1 ]; then echo; echo "dry run finished.  Nothing was changed."; exit 0; fi
  say "did the site come back?"
  for _ in $(seq 1 "$OZHIDANIE_200"); do
    if [ "$(curl -s -o /dev/null -w '%{http_code}' -m 5 "$PUBLIC_URL" || true)" = "200" ]; then
      say "rolled back; the site answers 200"; exit 0
    fi
    sleep 1
  done
  echo "ROLLBACK FAILED: $PUBLIC_URL did not answer 200 within ${OZHIDANIE_200}s" >&2
  exit "$RC_STEP_FAILED"
fi

# ------------------------------------------- 2. nothing uncommitted under the rolled-out paths
#
# 🔴 THE ROLLED-OUT PATHS, NOT THE WHOLE TREE.  The old script refused on any dirty file
# anywhere, and this repository legitimately carries dirty files that never leave the laptop
# -- the arc journals in `zhurnal/`, drafts in `doc/`, the local `data/spetsmat.db`.  A door
# that refuses every single time is a door nobody uses, and the way people stop using it is
# by deploying around it, by hand, which is exactly what happened twice.  So the question
# asked here is the one that matters: is what I am about to SEND committed?

say "are the rolled-out paths clean?"
gryaz="$(git --no-optional-locks status --porcelain -- "${VYKATYVAEM[@]}" 2>/dev/null || true)"
if [ -n "$gryaz" ]; then
  echo "REFUSED: the paths this deploy sends have uncommitted changes." >&2
  echo "$gryaz" >&2
  echo "Commit them first: what is deployed must be what is in git, or the server and the" >&2
  echo "history disagree and nobody can tell which is running." >&2
  # 🔴 THE DRY RUN SAYS IT AND CARRIES ON, AND THAT IS DELIBERATE.  `--proba` is the one
  # check that has to work on any laptop at any moment -- it is how the lesson refusal is
  # proven without a server, and the readiness criterion of this position runs it as a
  # fixed pair (rc=3 during a lesson, rc=0 outside one).  Whoever runs it has almost always
  # just edited `deploy/`, so a dry run whose exit code depends on the state of the working
  # tree answers a different question every time it is asked, and the pair stops meaning
  # anything.  A dry run changes nothing, so there is nothing here to protect.
  [ "$DRY_RUN" = 1 ] || exit "$RC_DIRTY_TREE"
  echo "  (dry run: saying so and carrying on -- nothing is being sent)"
else
  echo "  clean"
fi
echo "  deploying $(git --no-optional-locks rev-parse --abbrev-ref HEAD) @ $(git --no-optional-locks rev-parse --short HEAD)"

# ------------------------------------------------------------------ 3. a snapshot first
#
# 🔴 BEFORE THE FIRST BYTE MOVES, NOT AFTER THE RESTART.  A snapshot taken afterwards is a
# snapshot of the damage.  What is copied is exactly what this script is about to overwrite,
# plus `docs/index.html`, which the server rewrites by itself as soon as the new code runs.

say "snapshot before the transfer"
if [ "$DRY_RUN" = 1 ]; then
  echo "  would run: snapshot of ${VYKATYVAEM[*]} and docs/index.html into $TARGET-bak-<ISO>/"
else
  BAK="$($SSH "$SERVER" "set -e
    BAK=$TARGET-bak-\$(date -u +%Y%m%dT%H%M%SZ)
    sudo mkdir -p \"\$BAK\"
    for P in ${VYKATYVAEM[*]}; do
      [ -e $TARGET/\$P ] && sudo rsync -aR --exclude '__pycache__' -- $TARGET/./\$P \"\$BAK/\" || true
    done
    sudo mkdir -p \"\$BAK/docs\"
    [ -f $TARGET/docs/index.html ] && sudo cp -a $TARGET/docs/index.html \"\$BAK/docs/\" || true
    echo \"\$BAK\" | sudo tee $TARGET-bak-POSLEDNYAYA >/dev/null
    echo \"\$BAK\"")"
  echo "  $BAK"
fi

# ---------------------------------------------------------------- 4. is a migration pending
#
# The old script applied migrations itself, from the laptop, against the laptop database --
# which on a push deploy is the wrong database.  Applying them against the LIVE one is a
# decision with a blast radius of one school day, so this door does not make it silently in
# either direction: it REFUSES and says so.  Deploying while pretending migrations do not
# exist is the same lie this rewrite exists to remove.

say "is a migration pending?"
if [ "$DRY_RUN" = 1 ]; then
  echo "  would compare $CHECKOUT/migrations/ with $TARGET/migrations/"
else
  novye="$(rsync -rn --out-format='%n' -e "$SSH" ./migrations/ "$SERVER:$TARGET/migrations/" | grep -v '/$' || true)"
  if [ -n "$novye" ]; then
    cat >&2 <<EOF
REFUSED: migrations/ has changed and this door does not apply migrations by itself.

$novye

Applying a migration to the live database is a decision about a school's data, not a step
in a transfer.  Apply it deliberately, then deploy:
  ssh $SERVER "cd $TARGET && sudo -u spetsmat python3 -c \\
    'import sys; sys.path.insert(0,\".\"); from infra.db import apply_migrations; print(apply_migrations())'"
EOF
    exit "$RC_MIGRATION_NEEDS_A_HUMAN"
  fi
  echo "  none"
fi

# ------------------------------------------------------------------------ 5. the code
#
# Two passes, and the split is the import order explained at VYKATYVAEM above: `veb/` first,
# everything else after.  One rsync invocation gives no promise about the order in which the
# arguments are transferred; two invocations do.

say "rsync veb/  (the modules others import)"
run rsync -a --itemize-changes "${NE_VYKATYVAEM[@]}" -e "$SSH" ./veb "$SERVER:$TARGET/"

say "rsync the rest"
IZMENENO=""
if [ "$DRY_RUN" = 1 ]; then
  echo "  would run: rsync -a ${VYKATYVAEM[*]} -> $SERVER:$TARGET/"
else
  ostalnoe=()
  for P in "${VYKATYVAEM[@]}"; do [ "$P" = "veb" ] || ostalnoe+=("./$P"); done
  IZMENENO="$(rsync -a --itemize-changes "${NE_VYKATYVAEM[@]}" -e "$SSH" \
      "${ostalnoe[@]}" "$SERVER:$TARGET/" | awk '$1 ~ /^[<>ch]/ {print $2}')"
  echo "${IZMENENO:-  nothing changed outside veb/}"
fi

# ------------------------------------------------------------------------ 6. the restart
#
# The site always: its code just moved.  The bot ONLY if a path the bot runs actually
# changed -- restarting it costs a window in which two instances exist, and paying that for
# a deploy that did not touch the bot is paying for nothing.  But NOT restarting it after
# its code moved is the other half-deploy: the files are new and the running process is old,
# and nothing anywhere says so.  So the answer comes from what rsync reports it changed.

say "restart $UNIT_VEB"
run $SSH "$SERVER" "sudo systemctl restart $UNIT_VEB"

if [ "$DRY_RUN" = 1 ]; then
  echo "  would restart $UNIT_BOT only if bot/ core/ infra/ ops/ config.py changed"
elif echo "$IZMENENO" | grep -qE '^(bot|core|infra|ops)/|^config\.py$'; then
  say "restart $UNIT_BOT (its code changed)"
  $SSH "$SERVER" "sudo systemctl restart $UNIT_BOT"
else
  say "$UNIT_BOT left alone (nothing it runs changed)"
fi

# -------------------------------------------------------------------------- 7. the proof
#
# 🔴 A DEPLOY IS FINISHED WHEN THE SITE ANSWERS, NOT WHEN THE COMMAND RETURNED.  And when it
# does not answer, this script does not report and wait to be told what to do: it rolls
# itself back.  The owner's rule, 2026-09-07: the site matters more than any feature that
# did not get deployed.  Diagnosis happens afterwards, on a site that is up.

if [ "$DRY_RUN" = 1 ]; then
  echo "  would poll $PUBLIC_URL for 200, up to ${OZHIDANIE_200}s, and roll back if it never came"
  echo
  echo "dry run finished.  Nothing was changed."
  exit 0
fi

say "does $PUBLIC_URL answer 200?"
for i in $(seq 1 "$OZHIDANIE_200"); do
  if [ "$(curl -s -o /dev/null -w '%{http_code}' -m 5 "$PUBLIC_URL" || true)" = "200" ]; then
    say "deployed; the site answered 200 after ${i}s"
    exit 0
  fi
  sleep 1
done

echo "DEPLOY FAILED: $PUBLIC_URL did not answer 200 within ${OZHIDANIE_200}s." >&2
otkatit "the site did not come back after the deploy"
for i in $(seq 1 "$OZHIDANIE_200"); do
  if [ "$(curl -s -o /dev/null -w '%{http_code}' -m 5 "$PUBLIC_URL" || true)" = "200" ]; then
    echo "ROLLED BACK: the site answered 200 after ${i}s on the restored snapshot." >&2
    exit "$RC_ROLLED_BACK"
  fi
  sleep 1
done
echo "🔴 ROLLED BACK AND STILL DOWN: the snapshot did not bring the site back either." >&2
echo "   The fault is not in what was deployed.  ssh $SERVER; journalctl -u $UNIT_VEB -n 100" >&2
exit "$RC_STEP_FAILED"
