"""Where the three thresholds in ``core/services/roster.py`` come from.

Run from the repository root: ``python3 scratchpad/P19-privyazka/proto.py``.

This is the measurement, kept because the numbers in the module are otherwise three
unexplained constants.  It sweeps the live seed list of fifty-six, asks whether every
child resolves to their own row and nobody else's, and prints the typo cases the задание
names -- an initial, a case ending, an ё/е difference, a stray space, a name nobody has,
and the one real tie in the catalogue («Цукунов» sits exactly between «Цикунов» and
«Цуканов»).  Measured result: 56 of 56, zero misses.
"""

# TOOL-CONTRACT: called-by-hand -- the measurement the thresholds in
# core/services/roster.py were read off.  Re-run it when seed/students.csv changes.

import sys, csv, re
sys.path.insert(0, '.')
from core.services.raspoznavanie import ratio, case_forms

def norm(t):
    t = (t or "").strip().lower().replace("ё", "е").replace("-", " ")
    t = " ".join(w for w in t.split() if not re.fullmatch(r"[а-я]\.", w))
    return " ".join(t.split())

def sc(q, word):
    q = norm(q)
    if not q:
        return 0.0
    return max(ratio(q, norm(f)) for f in case_forms(word)) / 100.0

rows = list(csv.DictReader(open('seed/students.csv')))
print(len(rows))

SUR, ACC, BAND = 0.75, 0.80, 0.05

def resolve(qs, qn):
    scored = []
    for i, r in enumerate(rows):
        s = sc(qs, r['surname']); n = sc(qn, r['name'])
        c = 0.7*s + 0.3*n
        if s >= SUR and c >= ACC:
            scored.append((c, i, r))
    if not scored:
        return []
    best = max(c for c, _, _ in scored)
    return [(c, i, r) for c, i, r in scored if c >= best - BAND]

bad = 0
for i, r in enumerate(rows):
    res = resolve(r['surname'], r['name'])
    if len(res) != 1 or res[0][1] != i:
        bad += 1
        print("MISS", r['surname'], r['name'], [(round(c,3), x['surname'], x['name']) for c, _, x in res])
print("bad", bad)
print("--- typo tests")
for q in [("Пирогов","Константин"), ("Пирогов К.","Константин"), ("пирогов","константин"),
          ("Цукунов","Александр"), ("Федоров","Михаил"), ("Коневник","Фёдор"),
          ("Иванов","Иван"), (" Пирогов ","Костя")]:
    res = resolve(*q)
    print(q, "->", [(round(c,3), x['surname'], x['name']) for c, _, x in res])
