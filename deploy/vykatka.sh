#!/usr/bin/env bash
#
# Deploy: pull, migrate, restart.  Downtime 2-5 seconds.
#
# THE SINGLE MOST USEFUL LINE IN THIS SCRIPT IS THE REFUSAL TO DEPLOY DURING A LESSON, and
# it is the first thing that runs.  Two instances of one bot cannot poll Telegram at once:
# the second gets TelegramConflictError, and during a restart there is a moment when both
# exist.  During a lesson that moment is eighteen teachers tapping into a bot that answers
# nobody.  Blue-green is not merely redundant here -- it is impossible, for the same reason.
#
# UPDATES ARE NOT LOST BY A RESTART.  Telegram keeps undelivered updates for a day and
# re-delivers them.  There are exactly two ways to lose them, and both are acts of ours:
#   * dropping pending updates at startup -- `bot/__main__.py` does not, and
#     tests/ops/test_vykatka.py asserts that it still does not;
#   * killing the process instead of stopping it -- the unit uses SIGTERM with a real
#     TimeoutStopSec, and `systemctl restart` honours it.
#
# PROVABLE WITHOUT A SERVER:
#   bash deploy/vykatka.sh --proba --chas-zanyatia   # must REFUSE  (rc=3)
#   bash deploy/vykatka.sh --proba --svobodnyj-chas  # must proceed (rc=0), changing nothing
#
set -euo pipefail

CHECKOUT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT=spetsmat-bot.service
PYTHON="${PYTHON:-python3}"
DRY_RUN=0
CLOCK=""

#: Distinct exit codes, because "refused on purpose" and "broke" must not look alike.
RC_REFUSED_LESSON=3
RC_DIRTY_TREE=4
RC_STEP_FAILED=5

usage() {
  cat <<'USAGE'
usage: bash deploy/vykatka.sh [--proba] [--chas-zanyatia | --svobodnyj-chas]

  --proba            print every step, change nothing
  --chas-zanyatia    ask the schedule about a known LESSON moment instead of the clock
  --svobodnyj-chas   ask the schedule about a known FREE moment instead of the clock
USAGE
}

for argument in "$@"; do
  case "$argument" in
    --proba) DRY_RUN=1 ;;
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
# FIRST, before the pull, before the snapshot, before anything that costs time or changes
# state.  A refusal that arrives after `git pull` has already moved the checkout is not a
# refusal, it is a half-deploy.
#
# The answer comes from ops/raspisanie.py and from nowhere else: one place knows when a
# lesson is, so the deploy and the backup timers cannot disagree about it.

# THE ANSWER MUST BE AN ANSWER, NOT AN EMPTY STRING.
#
# `if reason="$(...)"` looks only at the exit code.  An interpreter that exits 0 and prints
# nothing -- `PYTHON=/usr/bin/true`, a stub on PATH, a truncated checkout -- therefore
# produced a silent green and a deploy in the middle of a lesson.  Found by the §3 verifier.
# A broken interpreter already failed closed (rc != 0 -> refuse); a SILENT one did not, and
# now both do.  The refusal is the safe side, so anything unexpected lands on it.

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

# ------------------------------------------------------- 2. nothing uncommitted underfoot
#
# A dirty tree means `git pull` will either refuse or merge over somebody's edit.  Better
# to stop here with the tree intact.

say "is the checkout clean?"
if [ -n "$(git --no-optional-locks status --porcelain)" ]; then
  echo "REFUSED: the checkout has uncommitted changes; deploy from a clean tree." >&2
  git --no-optional-locks status --porcelain >&2
  exit "$RC_DIRTY_TREE"
fi
echo "  clean"

# --------------------------------------------------------------- 3. a snapshot first
#
# Before the migration and not after it: a migration that goes wrong is exactly the case
# where the snapshot is needed, and a snapshot taken afterwards is a snapshot of the damage.

say "snapshot before the migration"
run "$PYTHON" "$CHECKOUT/ops/rezervnaya_kopia.py" --metka ruchnoj

# ------------------------------------------------------------------------ 4. the code
say "git pull"
run git --no-optional-locks pull --ff-only

# ------------------------------------------------------------------- 5. the migrations
#
# Through infra.db.apply_migrations, which is the project's own yoyo runner -- the same
# call `make check` makes.  Calling the `yoyo` CLI instead would need a second copy of the
# connection settings, and the second copy is what drifts.

say "apply migrations"
if [ "$DRY_RUN" = 1 ]; then
  echo "  would run: $PYTHON -c 'from infra.db import apply_migrations; print(apply_migrations())'"
else
  "$PYTHON" -c "import sys; sys.path.insert(0, '.'); from infra.db import apply_migrations; \
applied = apply_migrations(); print('applied %d migration(s): %s' % (len(applied), ', '.join(applied) or 'none'))"
fi

# ---------------------------------------------------------------- 6. the environment
#
# Before the restart, so that a full disk or an expired trust store is found while the old
# process is still serving, and not as a bot that comes back and immediately fails.

say "environment check"
run "$PYTHON" "$CHECKOUT/ops/proverka_sredy.py"

# ------------------------------------------------------------------------ 7. the restart
#
# `systemctl restart` and not `stop; start`: restart honours the unit's SIGTERM and
# TimeoutStopSec, so the update in the bot's hands is finished before it goes.  The two to
# five seconds of downtime are Telegram's to remember, and it does.

say "restart $UNIT"
run systemctl restart "$UNIT"

# -------------------------------------------------------------------------- 8. the proof
#
# A deploy is finished when the bot is answering, not when the command returned.

say "did it come back?"
if [ "$DRY_RUN" = 1 ]; then
  echo "  would run: systemctl is-active $UNIT  (expect: active)"
  echo
  echo "dry run finished.  Nothing was changed."
  exit 0
fi

sleep 5
if ! systemctl is-active --quiet "$UNIT"; then
  echo "DEPLOY FAILED: $UNIT is not active after the restart." >&2
  systemctl status "$UNIT" --no-pager >&2 || true
  "$PYTHON" "$CHECKOUT/ops/opoveshchenie.py" --rod trevoga \
    --tekst "deploy failed: the bot did not come back after the restart" --edinica "$UNIT" \
    --strok-zhurnala 20 || true
  exit "$RC_STEP_FAILED"
fi

say "deployed; $UNIT is active"
