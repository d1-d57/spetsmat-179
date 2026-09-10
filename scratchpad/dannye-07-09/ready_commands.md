# Ready insertion commands — line by line, one per mark, full args
# Execute ONLY on server with live DB: SPETSMAT_BAZA=/srv/spetsmat/data/spetsmat.db
# Each line is self-contained; insert in any order; no `--da` needed if DB is already set.

# Romanchuk Timofey — 07.09 — sheet 16A — task 1а
python3 tools/vnesti_s_bumagi.py --den 2026-09-07 --shkolnik Романчук --listok 16A --zadachi 1а --prepodavatel "Наталия Стрелкова" --pochemu "бумажный кондуит 07.09, ответ владельца 10.09" --da

# Romanchuk Timofey — 07.09 — sheet 16A — task 1б
python3 tools/vnesti_s_bumagi.py --den 2026-09-07 --shkolnik Романчук --listok 16A --zadachi 1б --prepodavatel "Наталия Стрелкова" --pochemu "бумажный кондуит 07.09, ответ владельца 10.09" --da
