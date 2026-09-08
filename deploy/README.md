# Runbook: the harness around the bot

Everything here is the harness, not the bot. The bot's own code (`bot/`, `core/`, `infra/`,
`config.py`) is untouched by this position, deliberately — see "the one line `bot/` must
call" below, which is a debt handed to the next position rather than an edit made here.

## 🔴 The server exists. Read this before anything else here

| | |
| --- | --- |
| address | `http://159.194.254.52/` — ssh `ivan@159.194.254.52`, `sudo` without a password |
| the tree | `/opt/spetsmat-bot` — **a plain directory of files, NOT a git checkout** |
| the site | `spetsmat-veb.service` → `python3 -m veb.server --bind 127.0.0.1 --port 8765`, nginx in front |
| the bot | `spetsmat-bot.service` |
| deployed by | `bash deploy/vykatka.sh` from a laptop checkout — rsync over ssh, never `git pull` |
| rolled back by | `bash deploy/vykatka.sh --otkat` |

**This file used to open by declaring that no server existed and that getting one was a
separate decision.** The server has existed since 2026-09-04 and has run lessons on it.
`deploy/vykatka.sh` beside it opened by calling itself a pull-migrate-restart and ran
`git pull` in a directory that has no `.git`. Two passes in a row therefore worked out how to
deploy by hand, live, on the production machine, and the second one wrote down what the first
had already paid for. The cost of a runbook that lies is not that it is unhelpful — it is
that it is believed.

**`tunnel.sh`, `podnyat_sajt.sh` and `ADRES.txt` in this folder are the route from BEFORE the
server** — a laptop holding an `lhr.life` tunnel open. They still work and are left alone,
but they are not how the site is published now, and the URL committed in `ADRES.txt` is a
dead tunnel (it answers 503). If you are looking for where the site lives, it is the table
above.

Everything below the deploy section is still provable on a laptop, and the way to prove each
piece is written next to it.

## Install

```
sudo bash deploy/ustanovka.sh              # for real; needs systemd and root
bash deploy/ustanovka.sh --proba           # dry run; needs neither
python3 ops/proverka_ustanovki.py          # the declaration is sound
python3 ops/proverka_ustanovki.py --zhivaya   # ... and systemd really has it enabled
```

`SPETSMAT_USER` overrides the service account (default `spetsmat`). The script installs
**every `.service` and `.timer` file it finds in `deploy/`** — found by looking, never from a
list — substitutes `@CHECKOUT@` and `@USER@`, installs the journal cap, creates
`secrets/bot.env` from `bot.env.example` without ever overwriting an existing one, and then
runs `systemctl enable --now` on every unit that has an `[Install]` section.

The install list used to be hand-written, and it was wrong: `spetsmat-proverka-sredy.service`
and `spetsmat-proverka-vosstanovlenia.service` have no `[Install]` of their own (their timers
start them by name) and were in neither list, so on a real server both timers would have
fired into units that do not exist — silently, forever. The backups would have kept being
taken and nobody would ever have learnt they could not be restored, which is the one failure
this whole runbook exists to prevent. `ops/proverka_ustanovki.py` now answers "does the
script install everything?" by RUNNING its dry run and reading what it says.

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

Run it **from a laptop checkout**, not on the server. It rsyncs a named list of paths over
ssh and restarts the site; there is no `git pull` anywhere, because there is no checkout on
the other end to pull into.

```
bash deploy/vykatka.sh                            # deploy
bash deploy/vykatka.sh --otkat                    # restore the latest snapshot, restart
bash deploy/vykatka.sh --proba --chas-zanyatia    # must REFUSE, rc=3
bash deploy/vykatka.sh --proba --svobodnyj-chas   # must proceed, rc=0
```

Exit codes: `0` deployed · `3` refused, a lesson is running · `4` the rolled-out paths have
uncommitted changes · `5` a step failed · `6` deployed and rolled back, the site never
answered 200 · `7` a migration is pending and a human must decide.

### 🔴 What is never rolled out — the list lives in the script, not in your head

| path | why |
| --- | --- |
| `data/` | the LIVE database — today's marks of 53 pupils and 14 teachers. The laptop copy is not a fresher version of it but an older, different one: on 2026-09-04 the server knew `Полина Романова` where the laptop knew only `Полина`. Overwriting it loses a school day |
| `secrets/` | `veb.env` with the two shared passwords, `veb-lichnye-paroli.json` with the hashes of the personal ones. The laptop files are not the same files, and this repository is public |
| `docs/index.html` | the server rebuilds it itself after every save. A copy pushed from here is overwritten within the minute, and until then it shows the wrong day's data |

### The order of the transfer is machinery, not tidiness

`veb/` goes first and `tools/` after it. `tools/sobrat_stranicu.py` imports `veb.razdely` and
`veb.obshchee`, and `veb/server.py` calls that tool after **every** successful write to the
database. Send the tool first and there is a window in which the live server imports a
package that is not yet on disk — every save inside that window is a 500. The script does two
rsync passes for this reason; one invocation makes no promise about order.

### Rollback

Every deploy takes a snapshot of exactly what it is about to overwrite, into
`/opt/spetsmat-bot-bak-<ISO>/`, **before the first byte moves**, and writes the path into
`/opt/spetsmat-bot-bak-POSLEDNYAYA`. `--otkat` reads that pointer, restores, restarts and
waits for 200.

You rarely have to type it: after the restart the script polls the public URL for 200 for
thirty seconds, and if the answer never comes it **rolls itself back** and then reports.
The owner's rule of 2026-09-07 — the site matters more than any feature that did not get
deployed, so the site comes back first and the diagnosis happens afterwards, on a site
that is up.

### Migrations are not applied by this door

The old script applied them from the laptop against the laptop's database, which on a push
deploy is the wrong database. Applying them to the live one is a decision about a school's
data, not a step in a transfer — so when `migrations/` has changed, the script refuses with
`rc=7` and prints the command to apply them deliberately. A door that silently skipped them
would be lying in the other direction.

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
integrity_check`, at least fifty students in the roster, and the newest mark neither older
than a week **nor in the future**. **Silence means alarm** — whoever watches the channel
watches for the missing pulse, because a check that died before it could complain is as loud
as one that failed.

The future bound is not decoration. With only an upper bound, a single mark dated ahead —
one teacher's phone with a wrong clock, one import with a bad date — keeps `max(valid_at)`
in the future forever, and "not older than a week" is then satisfied by a journal that
stopped months ago. The schema cannot stop it: its `CHECK` on `valid_at` is a glob over the
ISO shape, and a well-formed 2027 passes. Found by the §3 verifier on a snapshot whose real
activity had ended 45 days earlier and which was reported GREEN.

`--na-porchennom` breaks a snapshot four ways, and demands each be caught by the assertion
that exists for it. `rc=1` means every corruption went red, which is the demanded outcome;
`rc=2` means one slipped through and the check is broken. It never returns 0.

**What this check deliberately cannot do:** it cannot tell OUR database from a different one
of the same shape. A snapshot of another school's conduit with fifty-six students and a fresh
mark passes all three. Anchoring on an installation identity would mean writing to the
schema, which was read-only to the position that built this. The question answered here is
"is the backup usable?", not "is it ours?".

## When the alarm fires

`OnFailure=` means the unit gave up after five failed starts in five minutes. **That is NOT
necessarily broken code** — measured 08.09: five failed starts fired on a `TelegramNetworkError`
(`Request timeout error`), i.e. a broken network, not broken code, and `Restart=always` alone
did not save it because the burst limit tripped first. Five-failures-in-five-minutes looks the
same either way; only the actual exception line says which. That is why the alert text itself
is no longer a fixed guess (`ops/opoveshchenie.py --avto-diagnoz` greps the failing unit's own
journal for it) — read the delivered message first, it usually already names the real cause:

1. `journalctl -u spetsmat-bot.service -n 100` — the traceback is there;
2. fix or `git revert`, then `bash deploy/vykatka.sh` from your laptop (which will refuse
   if a lesson is running, and it is right to). If the site rather than the bot is down,
   `bash deploy/vykatka.sh --otkat` first and diagnose afterwards;
3. `systemctl reset-failed spetsmat-bot.service` before restarting by hand, or the burst
   counter is still full.

## How each piece was proven without a server

| piece | proof |
| --- | --- |
| the unit's directives | `ops/proverka_ustanovki.py`, plus tests that break a copy of `deploy/` and demand each check goes red |
| `systemctl enable` | the enable list is parsed out of `ustanovka.sh` and compared with the units that have `[Install]` |
| the install script | `--proba` runs for real in the test and the checkout is compared before and after |
| the backup | a writer connection is left open with data still in the WAL, and the snapshot must carry it |
| the restore check | `--na-porchennom`: four corruptions, each caught by its own assertion, and a stub that makes the self-test itself go red |
| the install coverage | the dry run is executed and the units it says it would install are compared with the files in `deploy/` |
| the unit contents | twelve deliberate breakages of a copied checkout — `ExecStart`, `OnCalendar`, `[Timer]`, a missing target service — each must go red |
| the deploy refusal | both time scenarios run as real subprocesses against fixed known moments |
| the timetable | the same instant is checked under three system zones, Berlin included |
| the pragmas | a `connect` that forgets one pragma, and the check must notice |
| `systemctl is-enabled` | **not proven here** — reported as SKIPPED, never as green; run `--zhivaya` on the server |
