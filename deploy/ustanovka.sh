#!/usr/bin/env bash
#
# Install the harness onto a machine that has systemd.
#
# THE ONE LINE THIS SCRIPT EXISTS FOR IS `systemctl enable`.  By the owner's own list,
# forgetting it is the most frequent real failure of the whole deployment: everything works,
# every check is green, and the bot is gone after the first reboot with nothing anywhere to
# say why.  Every unit with an [Install] section is enabled here, and ops/proverka_ustanovki.py
# proves afterwards that it was.
#
# PROVABLE WITHOUT A SERVER.  `--proba` prints every command and changes nothing, so the
# script can be read, run and reviewed on a laptop that has no systemd at all -- which is
# where it is being written, since there is no server yet.
#
#   sudo bash deploy/ustanovka.sh            # install for real
#   bash deploy/ustanovka.sh --proba         # dry run, needs no root and no systemd
#
set -euo pipefail

CHECKOUT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_DIR=/etc/systemd/system
JOURNAL_DIR=/etc/systemd/journald.conf.d
SERVICE_USER="${SPETSMAT_USER:-spetsmat}"
DRY_RUN=0

# Every unit that must be enabled.  A unit missing from this list installs, works, and
# disappears at the next reboot -- so the list is checked against the files on disk below,
# rather than trusted.
ENABLE_UNITS=(
  spetsmat-bot.service
  spetsmat-rezervnaya-kopia-pered-zanyatiem.timer
  spetsmat-rezervnaya-kopia-posle-zanyatia.timer
  spetsmat-rezervnaya-kopia-sutochnyj.timer
  spetsmat-proverka-vosstanovlenia.timer
  spetsmat-proverka-sredy.timer
)

# Templates: activated by OnFailure= and by the timers' Unit=, never enabled themselves.
TEMPLATE_UNITS=(
  spetsmat-alert@.service
  spetsmat-rezervnaya-kopia@.service
)

for argument in "$@"; do
  case "$argument" in
    --proba) DRY_RUN=1 ;;
    *) echo "unknown argument: $argument" >&2; exit 64 ;;
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

say "checkout   : $CHECKOUT"
say "service user: $SERVICE_USER"
[ "$DRY_RUN" = 1 ] && say "DRY RUN -- nothing on this machine will be changed"

# ---------------------------------------------------------------- the units themselves
#
# @CHECKOUT@ and @USER@ are substituted here and nowhere else.  A placeholder that reaches
# /etc/systemd/system unsubstituted gives "Failed to determine user credentials", which is
# a confusing way to say "the install script has a typo"; ops/proverka_ustanovki.py checks
# that every placeholder present in the unit files is one this script replaces.

# IS THE WATCHDOG WIRED YET?
#
# The unit declares Type=notify and WatchdogSec, and the ping has to come from inside the
# polling loop -- which lives in bot/, read-only to the position that wrote this harness.
# Installing a Type=notify unit against a bot that never notifies gives a unit that never
# finishes starting and is then killed at every interval: a harness that breaks the very
# thing it was built to keep alive.  So the state is ASKED, not assumed, and the watchdog
# is neutralised in the installed copy until bot/ has caught up.  deploy/README.md names
# the exact line; ops/proverka_ustanovki.py --storozh reports the debt.

WATCHDOG_SED=()
if python3 "$CHECKOUT/ops/proverka_ustanovki.py" --storozh >/dev/null 2>&1; then
  say "watchdog: bot/ sends READY=1 and WATCHDOG=1 -- installing the unit as written"
else
  say "watchdog: NOT WIRED in bot/ -- installing with Type=notify and WatchdogSec disabled"
  echo "  the bot will still run, restart and alert; it will NOT be watched for a dead poll."
  echo "  wire the hook named in deploy/README.md, then re-run this script."
  WATCHDOG_SED=(-e "s|^Type=notify|Type=simple|" \
                -e "s|^NotifyAccess=|#NotifyAccess=|" \
                -e "s|^WatchdogSec=|#WatchdogSec=|")
fi

say "installing units into $UNIT_DIR"
for unit in "${ENABLE_UNITS[@]}" "${TEMPLATE_UNITS[@]}"; do
  source_file="$CHECKOUT/deploy/$unit"
  [ -f "$source_file" ] || { echo "missing unit file: $source_file" >&2; exit 1; }
  if [ "$DRY_RUN" = 1 ]; then
    echo "  would install: $source_file -> $UNIT_DIR/$unit (with @CHECKOUT@ and @USER@ substituted)"
  else
    sed -e "s|@CHECKOUT@|$CHECKOUT|g" -e "s|@USER@|$SERVICE_USER|g" \
      "${WATCHDOG_SED[@]}" "$source_file" > "$UNIT_DIR/$unit"
    chmod 0644 "$UNIT_DIR/$unit"
  fi
done

say "installing the journal cap into $JOURNAL_DIR/spetsmat.conf"
run mkdir -p "$JOURNAL_DIR"
if [ "$DRY_RUN" = 1 ]; then
  echo "  would install: $CHECKOUT/deploy/journald-spetsmat.conf -> $JOURNAL_DIR/spetsmat.conf"
else
  install -m 0644 "$CHECKOUT/deploy/journald-spetsmat.conf" "$JOURNAL_DIR/spetsmat.conf"
fi

# ------------------------------------------------------------------------- the secrets
#
# Created from the example and NEVER overwritten: a re-run of this script must not wipe a
# token that is already there.  Mode 0600, and secrets/ is in .gitignore.

say "secrets"
if [ "$DRY_RUN" = 1 ]; then
  echo "  would create $CHECKOUT/secrets/bot.env from bot.env.example if it does not exist (mode 0600)"
else
  mkdir -p "$CHECKOUT/secrets"
  if [ ! -f "$CHECKOUT/secrets/bot.env" ]; then
    cp "$CHECKOUT/bot.env.example" "$CHECKOUT/secrets/bot.env"
    echo "  created $CHECKOUT/secrets/bot.env -- FILL IN BOT_TOKEN, ALERT_TOKEN AND OWNER_ID"
  else
    echo "  $CHECKOUT/secrets/bot.env exists, left alone"
  fi
  chmod 0600 "$CHECKOUT/secrets/bot.env"
  chown "$SERVICE_USER:$SERVICE_USER" "$CHECKOUT/secrets/bot.env" 2>/dev/null || true
fi

run mkdir -p "$CHECKOUT/data" "$CHECKOUT/data/backups"

# ------------------------------------------------------------------------------- enable
#
# THE LINE THIS SCRIPT EXISTS FOR.  `systemctl enable` and not merely `start`: start makes
# it run now, enable makes it run after the reboot, and only the second one survives the
# power cut that nobody planned.

say "systemctl daemon-reload"
run systemctl daemon-reload

for unit in "${ENABLE_UNITS[@]}"; do
  say "systemctl enable --now $unit"
  run systemctl enable --now "$unit"
done

say "systemctl restart systemd-journald  (to pick up the journal cap)"
run systemctl restart systemd-journald

# ------------------------------------------------------------------------------- proof
#
# The install is not finished when the commands have run; it is finished when the check
# says so.  A green install with a forgotten enable is exactly the state this proves is
# absent.

# ------------------------------------------------------------------ the token debt
#
# There is a standing decision of the owner (git-operaciya request 2026-09-02T1431) that
# the bot token must be rotated BEFORE the repository or the bot becomes reachable by
# anyone but him, and one of its three named trigger conditions is THE FIRST DEPLOY TO A
# SERVER -- which is this script.  A live token is in the git history of this checkout.
# The condition is checked here rather than remembered, because this is the moment it fires.

say "token rotation debt"
cat <<'DEBT'
  🔴 OWNER'S DECISION 2026-09-02: rotate the bot token BEFORE the repository or the bot
     becomes reachable by anyone but you.  A live @conduit179_bot token sits in this
     checkout's git history, and "first deploy to a server" is one of the three conditions
     that make the debt due.  Running this script on a server IS that condition.

       1. @BotFather -> /revoke
       2. put the new token ONLY in secrets/bot.env, never in a chat and never in git
       3. re-run this script

     While the checkout has no remote and lives only on your machine, the debt sleeps.
     Check with:  git remote | wc -l    (0 means it is still asleep)
DEBT

say "proving the install"
if [ "$DRY_RUN" = 1 ]; then
  echo "  would run: python3 $CHECKOUT/ops/proverka_ustanovki.py --zhivaya"
  echo
  echo "dry run finished.  Nothing was changed."
else
  python3 "$CHECKOUT/ops/proverka_ustanovki.py" --zhivaya
fi
