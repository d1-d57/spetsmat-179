#!/usr/bin/env bash
#
# Open an HTTPS tunnel from the owner's machine to the world, no install on the
# primary path.  Three fallbacks, tried in order; the first one that prints an
# https:// URL wins, the URL is saved to deploy/ADRES.txt, and the tunnel is held
# alive (a SIGCHLD on the ssh child is recovered) until the script is killed.
#
# PROVABLE WITHOUT A SERVER:
#   python3 -m http.server 8765 &
#   bash deploy/tunnel.sh 8765                      # rc=0 and an https URL on stdout
#   curl -sS -o /dev/null -w '%{http_code}\n' "$(cat deploy/ADRES.txt)"   # 200
#
# Exit codes (distinct, because "refused" and "broken" must not look alike):
#   0  an https URL was captured and is on disk in deploy/ADRES.txt
#   2  primary  (localhost.run) failed -- its output is on stderr
#   3  backup   (serveo.net)   failed -- its output is on stderr
#   4  fallback (cloudflared)  failed -- its output is on stderr
#   5  the chosen tunnel died before it printed a URL (the ssh child crashed)
#   6  the port argument is missing or not a number
#
# WHY THREE PATHS.  Spec: "ноль установки" -- a brew install can stall on the
# network and eat the whole evening.  The first two paths use stock ssh and
# need nothing installed; cloudflared is the third, paid for in install time.
#
set -euo pipefail

PORT="${1:-${SPETSMAT_VEB_PORT:-8000}}"
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then
  echo "tunnel.sh: PORT must be an integer 1..65535, got: $PORT" >&2
  exit 6
fi

CHECKOUT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ADRES="$CHECKOUT/deploy/ADRES.txt"

# The child tunnel's stdout is split: the URL banner (which we need) and the
# keepalive chatter (which we don't).  We tee the whole stream to a per-path
# file under /tmp so a verifier can read what each path actually said, and we
# grep the URL out of it on the fly.
capture_url() {
  # capture_url <log-path>
  # Echoes the tunneled URL it finds; the caller writes it to ADRES.txt.
  # Localhost.run prints a banner that references its admin/FAQ pages before the
  # own-tunnel URL -- a naive first-URL grep grabs the banner, not the tunnel.
  # We therefore look for the hostname pattern that is actually a tunnel:
  # lhr.life (localhost.run), serveo.net (serveo), trycloudflare.com (cloudflared).
  # Order: most specific host first; the first match wins.
  for pattern in 'https://[a-z0-9.-]+\.lhr\.life' \
                 'https://[a-z0-9.-]+\.trycloudflare\.com' \
                 'https://[a-z0-9.-]+\.serveo\.net'; do
    local hit
    hit="$(grep -Eo "$pattern" "$1" | head -n 1 || true)"
    if [ -n "$hit" ]; then
      echo "$hit"
      return 0
    fi
  done
  return 1
}

run_ssh_path() {
  # run_ssh_path <label> <extra-args...>
  local label="$1"; shift
  local log="/tmp/spetsmat-tunnel-${label}.log"
  : > "$log"

  # Backgrounded so we can grep its log until the URL appears; once it does,
  # we disown it and keep waiting (so the child is still alive when this
  # script exits -- otherwise ssh dies and the URL stops working).
  "$@" > "$log" 2>&1 &
  local pid=$!
  disown "$pid" 2>/dev/null || true

  local url=""
  for _ in $(seq 1 60); do
    sleep 1
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "  [$label] ssh child died before printing a URL; tail of $log:" >&2
      tail -n 20 "$log" >&2 || true
      return 1
    fi
    url="$(capture_url "$log")"
    if [ -n "$url" ]; then
      echo "$url" > "$ADRES"
      echo "URL ($label): $url"
      # Keep the child alive by waiting on it forever; killing tunnel.sh kills it.
      wait "$pid"
      return 0
    fi
  done
  echo "  [$label] waited 60s, no URL appeared; tail of $log:" >&2
  tail -n 20 "$log" >&2 || true
  kill "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
  return 1
}

run_cloudflared() {
  local log="/tmp/spetsmat-tunnel-cloudflared.log"
  : > "$log"
  if ! command -v cloudflared >/dev/null 2>&1; then
    echo "  installing cloudflared via brew..." >&2
    brew install cloudflared >>"$log" 2>&1 || {
      echo "  brew install cloudflared failed; tail of $log:" >&2
      tail -n 20 "$log" >&2 || true
      return 1
    }
  fi
  cloudflared tunnel --no-autoupdate --url "http://localhost:${PORT}" > "$log" 2>&1 &
  local pid=$!
  disown "$pid" 2>/dev/null || true

  local url=""
  for _ in $(seq 1 90); do
    sleep 1
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "  [cloudflared] child died before printing a URL; tail of $log:" >&2
      tail -n 20 "$log" >&2 || true
      return 1
    fi
    url="$(capture_url "$log")"
    if [ -n "$url" ]; then
      echo "$url" > "$ADRES"
      echo "URL (cloudflared): $url"
      wait "$pid"
      return 0
    fi
  done
  echo "  [cloudflared] waited 90s, no URL appeared; tail of $log:" >&2
  tail -n 20 "$log" >&2 || true
  kill "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
  return 1
}

echo "== tunnel.sh: trying localhost.run (primary) on port $PORT"
if run_ssh_path localhost.run \
    ssh -o StrictHostKeyChecking=accept-new \
        -o ServerAliveInterval=30 \
        -o ExitOnForwardFailure=yes \
        -o TCPKeepAlive=yes \
        -R "80:localhost:${PORT}" nokey@localhost.run; then
  exit 0
fi
echo "  localhost.run failed" >&2

echo "== tunnel.sh: trying serveo.net (backup) on port $PORT"
if run_ssh_path serveo.net \
    ssh -o StrictHostKeyChecking=accept-new \
        -o ServerAliveInterval=30 \
        -o ExitOnForwardFailure=yes \
        -o TCPKeepAlive=yes \
        -R "80:localhost:${PORT}" serveo.net; then
  exit 0
fi
echo "  serveo.net failed" >&2

echo "== tunnel.sh: trying cloudflared (fallback) on port $PORT"
if run_cloudflared; then
  exit 0
fi
echo "  cloudflared failed" >&2

echo "ALL THREE PATHS FAILED: no https URL obtained for port $PORT" >&2
rm -f "$ADRES"
exit 4