# Runbook: the harness around the bot

Everything here is the harness, not the bot. The bot's own code (`bot/`, `core/`, `infra/`,
`config.py`) is untouched by this position, deliberately — see "the one line `bot/` must
call" below, which is a debt handed to the next position rather than an edit made here.

There is no server yet, and getting one is a separate decision. Every piece below is
therefore provable on a laptop, and the way to prove each one is written next to it.

## Install

```
sudo bash deploy/ustanovka.sh              # for real; needs systemd and root
bash deploy/ustanovka.sh --proba           # dry run; needs neither
python3 ops/proverka_ustanovki.py          # the declaration is sound
python3 ops/proverka_ustanovki.py --zhivaya   # ... and systemd really has it enabled
```

`SPETSMAT_USER` overrides the service account (default `spetsmat`). The script substitutes
`@CHECKOUT@` and `@USER@` into the units, installs the journal cap, creates
`secrets/bot.env` from `bot.env.example` without ever overwriting an existing one, and then
runs `systemctl enable --now` on every unit that has an `[Install]` section.

**`systemctl enable` is the line this script exists for.** By the owner's own list, the most
frequent real failure of a deployment is forgetting it: everything works, every check is
green, and the bot is gone after the first reboot with nothing anywhere to say why.

## What gets installed

| unit | what it does | when |
| --- | --- | --- |
| `spetsmat-bot.service` | the bot | always, `Restart=always` |
| `spetsmat-alert@.service` | one alarm through the second bot | fired by `OnFailure=` |
| `spetsmat-rezervnaya-kopia@.service` | one snapshot, `%i` is the label | fired by the timers |
| `spetsmat-rezervnaya-kopia-pered-zanyatiem.timer` | snapshot before the lesson | Mon, Thu 12:45 UTC |
| `spetsmat-rezervnaya-kopia-posle-zanyatia.timer` | snapshot after the lesson | Mon, Thu 16:15 UTC |
| `spetsmat-rezervnaya-kopia-sutochnyj.timer` | daily snapshot | 01:00 UTC |
| `spetsmat-proverka-vosstanovlenia.timer` | the restore check | Sun 04:00 UTC |
| `spetsmat-proverka-sredy.timer` | the environment check | 03:00 UTC |
| `journald-spetsmat.conf` | the journal cap | `/etc/systemd/journald.conf.d/spetsmat.conf` |

The timer times are UTC because the system clock is UTC. They must agree with
`ops/raspisanie.py`, and `tests/ops/test_deploy_edinicy.py` asserts that they still do — two
answers to "when is a lesson" would surface as a missing snapshot on exactly the day
something was lost.

## 🔴 The one line `bot/` must call — the debt handed on

The watchdog is declared (`WatchdogSec=120`, `Type=notify`) and it is **not yet wired**,
because the ping belongs inside the polling loop and `bot/` is read-only to the position that
wrote this. Until it is wired, `systemd-notify` never arrives and the unit will be restarted
every two minutes, so **install with `WatchdogSec` commented out, or wire the hook first.**

The hook must be called from the place that PROVES `getUpdates` answered — inside the update
handler of the polling loop in `bot/__main__.py`, never from an independent timer, which
would keep pinging beside a dead poll and remove the suspicion along with the symptom:

```python
import sdnotify                       # or: os.write to $NOTIFY_SOCKET
sdnotify.SystemdNotifier().notify("WATCHDOG=1")
```

placed inside the loop that consumes updates, plus one `notify("READY=1")` after
`start_polling` has connected, which is what `Type=notify` waits for.

The failure this guards against is the nastiest one this bot has: the connection dies at TCP
level, no timeout fires, `getUpdates` never returns, the process is alive, and systemd is
perfectly happy.

## Deploy

```
bash deploy/vykatka.sh                        # pull, migrate, restart
bash deploy/vykatka.sh --proba --chas-zanyatia    # must REFUSE, rc=3
bash deploy/vykatka.sh --proba --svobodnyj-chas   # must proceed, rc=0
```

Exit codes: `0` deployed, `3` refused because a lesson is running, `4` the checkout is
dirty, `5` the bot did not come back.

**The refusal during a lesson is the most useful line in the script**, and it is the first
thing that runs. Two instances of one bot cannot poll Telegram at once — the second gets
`TelegramConflictError` — and a restart is precisely the moment when both exist. For the
same reason blue-green here is not redundant but impossible.

Updates are not lost by a restart: Telegram keeps them a day and re-delivers. They can only
be lost by two acts of ours — dropping pending updates at startup, and killing the process
instead of stopping it. Both are asserted against in `tests/ops/test_vykatka.py`.

## Backups

```
python3 ops/rezervnaya_kopia.py --metka sutochnyj
```

`VACUUM INTO`, gzip, local rotation of fourteen days. Never `cp`: `cp` takes the file
mid-transaction, and in WAL mode the committed data is partly in the side files, so the copy
restores "almost". Snapshots stay in `data/backups/`, which `.gitignore` excludes.

**Backups do not go into a Telegram channel.** That is a transfer of fifty-six children's
personal data to a third-party operator outside the perimeter, and the best available leak
vector. `ops/rezervnaya_kopia.py` has no upload path at all, and a test fails if one appears.

## Restore check — a separate task, not an appendix

```
python3 ops/proverka_vosstanovlenia.py                  # the latest snapshot; rc=0 green
python3 ops/proverka_vosstanovlenia.py --na-porchennom  # PROVE it can go red; rc=1 expected
```

Three assertions, all of which must pass before the heartbeat goes out: `pragma
integrity_check`, at least fifty students in the roster, the newest mark not older than a
week. **Silence means alarm** — whoever watches the channel watches for the missing pulse,
because a check that died before it could complain is as loud as one that failed.

`--na-porchennom` breaks a snapshot three ways, one per assertion, and demands each be
caught by its own assertion. `rc=1` means every corruption went red, which is the demanded
outcome; `rc=2` means one slipped through and the check is broken. It never returns 0.

## When the alarm fires

`OnFailure=` means the unit gave up after five failed starts in five minutes. That is broken
CODE, not a broken network — a broken network is what `Restart=always` handles, and the bot
recovers from it by itself. So:

1. `journalctl -u spetsmat-bot.service -n 100` — the traceback is there;
2. fix or `git revert`, then `bash deploy/vykatka.sh` (which will refuse if a lesson is
   running, and it is right to);
3. `systemctl reset-failed spetsmat-bot.service` before restarting by hand, or the burst
   counter is still full.

## How each piece was proven without a server

| piece | proof |
| --- | --- |
| the unit's directives | `ops/proverka_ustanovki.py`, plus tests that break a copy of `deploy/` and demand each check goes red |
| `systemctl enable` | the enable list is parsed out of `ustanovka.sh` and compared with the units that have `[Install]` |
| the install script | `--proba` runs for real in the test and the checkout is compared before and after |
| the backup | a writer connection is left open with data still in the WAL, and the snapshot must carry it |
| the restore check | `--na-porchennom`: three corruptions, three assertions, and a stub that makes the self-test itself go red |
| the deploy refusal | both time scenarios run as real subprocesses against fixed known moments |
| the timetable | the same instant is checked under three system zones, Berlin included |
| the pragmas | a `connect` that forgets one pragma, and the check must notice |
| `systemctl is-enabled` | **not proven here** — reported as SKIPPED, never as green; run `--zhivaya` on the server |
