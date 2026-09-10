# Draft — paper log 07.09 (human-readable, with source per line)

## 1. Romanchuk Timofey — 2026-09-07
Source: `бумажный кондуит 07.09, ответ владельца 10.09`
Sheet: 16A (only `1а` and `1б` exist in 16A; 16α has `1`, not `1а`/`1б`)
Tasks: `1а`, `1б`
Teacher: Natalia Strelkova (`prepodavatel` argument)
Note (origin): `бумажный кондуит 07.09, ответ владельца 10.09`
Status before insertion: 0 solved marks in the cell (per task description).
Ready command (line by line, full args, one per mark):
```
python3 tools/vnesti_s_bumagi.py --den 2026-09-07 --shkolnik Романчук --listok 16A --zadachi 1а --prepodavatel "Наталия Стрелкова" --pochemu "бумажный кондуит 07.09, ответ владельца 10.09"
python3 tools/vnesti_s_bumagi.py --den 2026-09-07 --shkolnik Романчук --listok 16A --zadachi 1б --prepodavatel "Наталия Стрелкова" --pochemu "бумажный кондуит 07.09, ответ владельца 10.09"
```
These commands are to be inserted with `--da` ONLY when `SPETSMAT_BAZA=/srv/spetsmat/data/spetsmat.db` points to live server DB.

## 2. Owner attendance — 10.09
Source: interview 10.09; office strip does NOT show green.
Observation: the mechanism did not deliver attendance — not a manual painting issue.
Root cause to investigate (mechanism-level): why did the attendance not arrive in the cabinet strip? (Named for morning; do NOT paint by hand.)
Ready command (once mechanism is fixed or confirmed live):
```
# Command to be confirmed after mechanism fix; not executable without live DB.
# Example: attendance insertion depends on mechanism fix — do not run now.
```

## 3. Yusupov Aron — Thursday
Source: owner decision 10.09; `mandate_sborka-bota.md` notes he is not attached to anyone.
Action: data correction (`core/models` or relevant table) — not a `marks` insertion; needs owner confirmation on which sheet/session to attach.
Ready command: none yet — requires owner decision on attachment target.

## Witness (`SvidetelRaboty` / `core/istochnik.py:314`)
No live DB on machine (`SPETSMAT_BAZA` missing; `/srv/spetsmat/data` missing). Therefore no witness possible: `н/д` (cause: no database file present). Before insertion on server, run:
```
SPETSMAT_BAZA=/srv/spetsmat/data/spetsmat.db python3 core/istochnik.py --snyat-kopiyu ...
```
And after insertion, print `svid.otchyot()` output.
