#!/usr/bin/env bash
#
# Raise the veb site ON THIS MACHINE today (no systemd on macOS).
# Spec: nohup + disown so the server and the tunnel survive terminal close.
#
# PROVABLE WITHOUT A SERVER:
#   python3 -m http.server 8000 &     # for the probe; the script below also
#                                     # works against the python http.server if
#                                     # veb/ is missing -- it will say so.
#   bash deploy/podnyat_sajt.sh --proba     # prints the actions without running
#
# What this script does, in order:
#   1. Discover the veb entry point at run time with `ls veb/*.py`. If veb/ is
#      missing -- say so in words and exit 1. The veb/ position is being written
#      by a parallel pass; we re-check at every invocation, NOT at install time.
#   2. nohup-launch the site, save its PID.
#   3. nohup-launch the tunnel (which itself writes deploy/ADRES.txt), save its PID.
#   4. Print three lines: site PID, tunnel PID, https URL.
#
# Exit codes:
#   0  everything started, URL captured
#   1  veb/ entry not found -- script refused, NOTHING was started
#   6  PORT is not a number
#   7  the site process died immediately (start failed)
#   8  the tunnel process died immediately (start failed, no URL captured)
#
set -euo pipefail

PORT="${SPETSMAT_VEB_PORT:-8000}"
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then
  echo "podnyat_sajt.sh: SPETSMAT_VEB_PORT must be an integer 1..65535, got: $PORT" >&2
  exit 6
fi

CHECKOUT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${TMPDIR:-/tmp}"
SITE_LOG="$LOG_DIR/spetsmat-veb-site.log"
TUNNEL_LOG="$LOG_DIR/spetsmat-veb-tunnel.log"
PID_DIR="$LOG_DIR"
SITE_PID_FILE="$PID_DIR/spetsmat-veb-site.pid"
TUNNEL_PID_FILE="$PID_DIR/spetsmat-veb-tunnel.pid"

DRY_RUN=0
for argument in "$@"; do
  case "$argument" in
    --proba) DRY_RUN=1 ;;
    -h|--help) cat <<'USAGE'
usage: bash deploy/podnyat_sajt.sh [--proba]

Environment:
  SPETSMAT_VEB_PORT  port to bind (default 8000)
USAGE
      exit 0 ;;
    *) echo "unknown argument: $argument" >&2; exit 64 ;;
  esac
done

# ------------------------------------------------------------------ 1. discover entry
echo "== podnyat_sajt.sh: locating the veb entry point"
# Built for /usr/bin/env bash on macOS, where bash may be 3.2 and `mapfile`
# is not available. Use a while-read into a regular array.
VEB_ENTRIES=()
for entry in "$CHECKOUT/veb/"*.py; do
  [ -e "$entry" ] || continue
  VEB_ENTRIES+=("$entry")
done
if [ "${#VEB_ENTRIES[@]}" -eq 0 ]; then
  cat >&2 <<EOF
REFUSED: the veb site is not present in this checkout yet.

  expected at: $CHECKOUT/veb/*.py
  found:       (nothing)

The veb/ position is being written by a parallel pass; raise the site once that
pass has landed an entry file there. Until then deploy/podnyat_sajt.sh refuses
rather than launching a placeholder that the URL would resolve to nothing.
EOF
  exit 1
fi

# If there are several, the convention from veb-raspredelenie-mvp is one file
# that names itself after the module; pick the only one if there is one, list
# them if there are more. The position that owns veb/ is the authority on which
# is the entry; this script does not second-guess it.
if [ "${#VEB_ENTRIES[@]}" -eq 1 ]; then
  ENTRY="${VEB_ENTRIES[0]}"
  ENTRY_MODULE="$(basename "${VEB_ENTRIES[0]}" .py)"
else
  ENTRY="${VEB_ENTRIES[0]}"
  ENTRY_MODULE="$(basename "${VEB_ENTRIES[0]}" .py)"
  echo "  note: multiple veb/*.py found, using first: $ENTRY_MODULE" >&2
fi
echo "  entry: veb/$ENTRY_MODULE"

# ------------------------------------------------------------------ 2. site
echo "== podnyat_sajt.sh: starting site on port $PORT"
if [ "$DRY_RUN" = 1 ]; then
  echo "  would run: cd $CHECKOUT && nohup python3 -m veb.$ENTRY_MODULE $PORT"
  SITE_PID=""
else
  # nohup ... & disown -- survives terminal close (spec: 14 of 16 live, the
  # other two were the same script that backgrounded before disown).
  # PID is written into a file by the subshell that forked python; we read it
  # back. Then we disown the subshell so it is not reaped on terminal exit.
  SITE_PID=""
  (
    cd "$CHECKOUT"
    nohup python3 -m "veb.$ENTRY_MODULE" "$PORT" \
      > "$SITE_LOG" 2>&1 &
    echo $! > "$SITE_PID_FILE"
    disown
    # Hold this subshell open with `wait` so it does not exit and orphan
    # python; `wait` returns when the last backgrounded child exits.
    wait
  ) &
  disown
  sleep 1
  SITE_PID="$(cat "$SITE_PID_FILE")"
  if ! kill -0 "$SITE_PID" 2>/dev/null; then
    echo "FAILED: site process (pid $SITE_PID) died immediately; tail of $SITE_LOG:" >&2
    tail -n 20 "$SITE_LOG" >&2 || true
    exit 7
  fi
fi

# ------------------------------------------------------------------ 3. tunnel
echo "== podnyat_sajt.sh: starting tunnel"
if [ "$DRY_RUN" = 1 ]; then
  echo "  would run: cd $CHECKOUT && nohup bash deploy/tunnel.sh $PORT"
  TUNNEL_PID=""
else
  TUNNEL_PID=""
  (
    cd "$CHECKOUT"
    nohup bash deploy/tunnel.sh "$PORT" \
      > "$TUNNEL_LOG" 2>&1 &
    echo $! > "$TUNNEL_PID_FILE"
    disown
    # Hold the subshell so tunnel.sh stays as the leader of the ssh child,
    # and so the URL survives terminal close (see spec note on nohup + disown).
    wait
  ) &
  disown
  TUNNEL_PID="$(cat "$TUNNEL_PID_FILE")"
  # Wait up to 90 seconds for the tunnel to write ADRES.txt. tunnel.sh will
  # exit non-zero if all three paths fail; we want to surface that too.
  for _ in $(seq 1 90); do
    if [ -s "$CHECKOUT/deploy/ADRES.txt" ]; then
      break
    fi
    if ! kill -0 "$TUNNEL_PID" 2>/dev/null; then
      echo "FAILED: tunnel process (pid $TUNNEL_PID) died; tail of $TUNNEL_LOG:" >&2
      tail -n 20 "$TUNNEL_LOG" >&2 || true
      exit 8
    fi
    sleep 1
  done
  if [ ! -s "$CHECKOUT/deploy/ADRES.txt" ]; then
    echo "FAILED: tunnel is alive but no URL captured in 90s; tail of $TUNNEL_LOG:" >&2
    tail -n 20 "$TUNNEL_LOG" >&2 || true
    exit 8
  fi
fi

# ------------------------------------------------------------------ 4. the report
URL="$(cat "$CHECKOUT/deploy/ADRES.txt")"
echo "== podnyat_sajt.sh: up"
echo "  site_pid:   ${SITE_PID:-<dry-run>}"
echo "  tunnel_pid: ${TUNNEL_PID:-<dry-run>}"
echo "  url:        $URL"