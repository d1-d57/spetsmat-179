# MANDATE — sborka-bota

<!-- assembled by bootstrap_mandate.py; two halves, two authors; do not merge them -->

**STATUS:** `OPEN`
**TOP_HALF_STATUS:** `COMPLETE`
**BOTTOM_HALF_STATUS:** `PENDING`
**ARC:** `zhurnal/2026-09-02_spetsmat-bot`
**ASSEMBLED:** `2026-09-02`

> Status is one of `OPEN` · `CLOSED` · `REFUSED`. `REFUSED` is a LAWFUL outcome and
> needs a written reason in the bottom half — refusing is not the same as stopping.
> The one outcome forbidden to the orchestrator is to stop and leave the wave
> untouched: a tool's refusal is a task, not an outcome
> (`skills/disciplina-orkestrator/SKILL.md`).

> Phase markers — `TOP_HALF_STATUS: COMPLETE` (this tool always writes the top
> half) and `BOTTOM_HALF_STATUS: PENDING` / `COMPLETE` (the orchestrator flips it
> on return). The linter REFUSES mismatch with STATUS: OPEN ↔ PENDING, CLOSED ↔
> COMPLETE. A reader without context can tell which half is done.

## HALF ONE — WRITTEN BY COWORK, BEFORE THE WAVE

### GOAL

WAVE 1, ASSEMBLY - fifteen positions building a Telegram bot that records problem check-offs for the 179 school special-maths stream: 56 students, 18 teachers, three rooms, two lesson days a week. The core is an append-only journal; the grid of task buttons is the screen everything else exists for. Photo, voice and text are accelerators over one shared confirmation table, never a direct write. Last year's 15112 marks are loaded on day one so the bot is not empty when a student first opens it.

### INTERVIEW — RENDERED IN ENGLISH FROM A RUSSIAN CONVERSATION — 2026-09-02

> **ИНТЕРВЬЮ ПРОВЕДЕНО** (flag `--intervyu da` at assembly). ⚠ The flag proves the
> assembler was asked, not that the conversation happened — same honest limit
> `bootstrap_zahod.py --intervyu` already prints. ⚠ The interview was held in
> Russian and what is recorded here is the ENGLISH RENDERING of the settled
> meaning, not a quotation. A rendering can be wrong, and only the owner can
> say so.

- **Q1** — Q: Q1
  — M: Goal is a working bot for one real group by the first September lesson, not a product: the owner is the first administrator, and the tool must survive six teachers working in one room
- **Q2** — Q: Q2
  — M: Out of scope: written tests with partial scores, term marks, the final examination, free-text characteristics, teacher payment shares, a web client, a Mini App, parental access, and any setting outside config.py
- **Q3** — Q: Q3
  — M: Failure is any of: tests not green, the import failing to reproduce debts and the graveyard, the negative control not going red on corrupted data, the bot not coming up live, ratings or percentages or points surviving in the code, surnames leaving the server into a foreign model, a mark written without human confirmation, or lessons of the wave left unjudged
- **Q4** — Q: Q4
  — M: The wave may not leave undone: everything committed through git_zona, every pass accepted with a verdict, every lesson judged by a fresh model that did not write it, every rule given something that goes red or declared a hope in writing with the share named as a number
- **Q5** — Q: Q5
  — M: The bottom half is read by the owner in the morning and by the next wave: one verdict line per position plus the wave balance in numbers, each number produced by a command
- **Q6** — Q: Q6
  — M: Goal and boundaries in English; fixed Russian addresses stay Cyrillic because translating an address breaks it

### FINALIZED AT INTERVIEW — 2026-09-02

- [F1] 02.09 (owner): THE ORCHESTRATOR COMMITS FIRST, before launching any position. Cowork created files but does not commit: the arc and its six memory documents, the mandate, seed/ (3 files), tools/ (4 files), .gitignore, bot.env.example, README - all through git_zona.py, README in the SAME commit, secrets/ never. A second commit belongs in the FOREIGN repository disciplina: korni.py gained the spetsmat-bot registry entry and skills/kak-zavesti-telegram-bota/SKILL.md gained the long-polling half
- [F2] 02.09 (owner): THREE roles - HEAD (runs a room, uploads sheets, receives the post-lesson summary, influences the programme), TEACHER (checks off problems only), STUDENT. The post-lesson report belongs to the HEAD by its meaning
- [F3] 02.09 (owner): a teacher is bound to a group HARD for the whole year and never moves; students move occasionally. Assignment is PER LESSON DAY, because some teachers only come once a week: the same student may have one teacher on Monday and another on Thursday (evidence: the owner's 2025 tool, kakhiani = vanya on mon, yan on thu)
- [F4] 02.09 (owner): the room screen IS wanted - the head sees the ~18 students in front of him with each one's debt count on the button, marks who came, adds a guest from another group, adjusts today's assignment. It must be genuinely well designed, not merely functional
- [F5] 02.09 (owner): a student sees his OWN debts only - per sheet and as a total across sheets
- [F6] 02.09 (owner): last year's marks are loaded so that on day one a student opens the bot and sees his whole eighth grade
- [F7] 02.09 (owner): text input carries the sheet in square brackets - [7] Petrov 3,5,7b
- [F8] 02.09 (owner): after the lesson the bot notifies - the teacher who marked nothing is asked whether he was there, the head gets the summary. Sent AFTER the lesson: Telegram is unreliable inside the school building
- [F9] 02.09 (owner): a mark is NEVER written to the database without human confirmation - the single most important rule of the project
- [F10] 02.09 (owner, earlier): a mark is an event in an append-only journal; the state of a cell is its last event; a button carries the target state, never a toggle; core/ imports aiogram in not one line; all constants in config.py; no ratings, percentages, points, levels, streaks or badges, and nothing written next to a plus

### BOUNDARIES AND WHAT IS ALREADY CLOSED

- ALREADY CLOSED and not reopened: the data model, the seed contents (56 students, 18 teachers, 544 problems, 15112 marks), Telegram as the only client, the decision not to fork the VMSH bot, the bot token and the OpenRouter key (both live and verified 02.09)
- P0 commit goes FIRST. Then P1 blocks all. P4 lands before P7, P8, P15. P12 lands before P13. P11 goes last and waits
- OUT: moving to Russian hosting with a proxy, the RKN notification, the consent button - owner decisions, not executor work. OUT: the owner's broken ZAPUSK-ZAHODA.sh line 138 - a different repository's problem

### CLOSING PHASE — KNOWLEDGE

**The orchestrator runs this phase AFTER the last pass is ACCEPTED and BEFORE the
bottom half is written.** It is not optional and not a report: `--lint` refuses a
bottom half that does not answer it with numbers.

**a. HARVEST.** Collect every lesson, debt and incident born in THIS wave — from the
`kod_*` files of the wave and from the wave journal. Count them.

**b. JUDGE.** Every harvested lesson gets a verdict, from a FRESH free-model pass, in
batches of about ten, and NEVER from the model that wrote it — the author is the
wrong judge, and that is the structural reason this phase exists at all. Three
lawful verdicts: it becomes a **RULE** in a named skill · it becomes a **DEBT** at a
named address · it is **dismissed** with a reason. A lesson with no `ЦЕНА:` is not
judged at all: it goes back to its author as `доработка`, because a lesson without a
price is an observation.

**c. RULES TO CARRIERS.** For every lesson promoted to a rule, name what goes RED when
it is violated. If nothing can, the rule is declared a **hope**, in writing, by our own
law (`skills/disciplina-kachestvo/SKILL.md`). Each new carrier — a gate, a phase, an
artifact field — becomes a NAMED follow-up pass, written now: run in this wave if the
clock allows, carried into the next mandate if not.

**d. BALANCE.** Print the four numbers below. That single delta is what tells us
whether we are winning.

**COST.** All of it on free models, judging batched, and each judging pass reads only
the lesson text, its price and its named home — never the repository. The phase is
bounded by the CLOCK, not by a number of tries: when time runs out, unjudged lessons
are listed BY NAME in the bottom half and carried into the next mandate as an explicit
debt. They may never be dropped silently.

### P0 — THE OPENING COMMIT, BEFORE ANY POSITION IS LAUNCHED

Cowork built the ground but does not commit. The orchestrator's first move, through
`git_zona.py`, never bare git:

```
zone 1 (this repo):  zhurnal/2026-09-02_spetsmat-bot/  seed/  tools/  .gitignore
                     bot.env.example  README.md      ← README in the SAME commit
zone 2 (disciplina): _generator/tools/korni.py        ← spetsmat-bot registry entry
                     skills/kak-zavesti-telegram-bota/SKILL.md  ← long-polling half
```

`secrets/` is never committed and is already ignored — verify with
`git check-ignore -v secrets/`, not with the silence of `git status`.

### POSITIONS

| # | position | proves itself by | model |
|---|---|---|---|
| P1 | core: schema, migrations, mark journal | idempotent re-mark, retraction, rollback; append-only enforced by trigger; **differential test — the grid projection equals a naive fold of the journal written a second, independent way** | paid |
| P2 | import of last year's data, seeding, all 15112 marks loaded | three oracles that are NOT the spreadsheet's own SUM row: the examination sheet, thirty hand-checked cells, the debts sheet honouring first_sheet; **negative control — corrupting data must turn the test red**; an inventory of every distinct cell value that FAILS on an unknown one | paid |
| P3 | registration and three roles | an unconfirmed student sees nothing; a confirmed one sees only his own; a teacher cannot upload a sheet, a head can | free |
| P12 | groups and day-dependent assignment | the same student resolves to different teachers on Monday and Thursday; a teacher never moves; moving a student does not rewrite history | paid |
| P4 | the grid — the main screen | exactly four per row; no callback_data over 64 bytes; double tap does not double-write; a stale button gets "screen expired", not an endless spinner | paid |
| P13 | the room screen for the head | ~18 students with each one's debt count on the button; present/absent toggled; a guest added; today's assignment adjusted without touching the standing one. **Design quality is part of the acceptance here, not a nicety** | paid |
| P5 | viewing screens | a student cannot reach another student's marks by any query; debts per sheet and total; the silent-students list correct on prepared data | free |
| P6 | lessons and attendance | attendance distinguishable from absence of marks; a back-dated mark gets the right valid_at with today's recorded_at | free |
| P14 | post-lesson notifications | the teacher who marked nothing is asked whether he was there; the head gets the summary — who handed in how much, who has been silent three lessons running, which problems nobody took. Sent after the lesson, never during | free |
| P15 | fast text input | `[7] Petrov 3,5,7b` resolves through the same fuzzy index and the same confirmation table | free |
| P7 | photo | printed form generator (`tools/blank.py` already works); EXIF honoured, no upscaling, thinking_level=minimum; **markdown fence stripped before parsing**; idempotent by SHA-256 of file bytes plus a confirmed-drafts table; model refusal arrives as HTTP 200 and spend-limit exhaustion as 429 without retry-after | paid |
| P8 | voice | "Petrov three five seven be" resolves to Petrov, problems 3, 5, 7b; numeral normalisation is our own code | paid |
| P9 | sheet upload by a head | three real sheets from last year parse to metadata identical to seed/sheets.json | free + paid |
| P16 | export and backups | export to Excel; `VACUUM INTO` on a schedule tied to lessons; a weekly restore check that goes red by itself | free |
| P10 | operations | kill the process — it returns; cut the network — it survives without exhausting the restart limit; deploy during a lesson — the script refuses | free |
| P11 | end-to-end acceptance and judgement of the wave's knowledge | writes nothing; runs everything; judges every lesson with a FRESH model that did not write it | paid |

**Order.** P0 commit. Then P1 alone. Then P2, P3, P6, P9, P10, P16 in parallel. P12 after P3.
P4 after P3. P13 after P12 and P4. P5, P14, P7, P8, P15 after P4. P11 last, waiting.

**Forbidden everywhere:** a mark written without human confirmation · ratings, percentages, points,
levels, streaks, badges · any text next to a plus · a student seeing another's data · surnames
leaving the server into a foreign model · aiogram imported under core/ · bare git.

### MODEL DISCIPLINE

PAID positions may run three to four in parallel. FREE positions run **strictly one at a time**
through `orkestr.py progon` — the free gateway holds a rate limit and nine simultaneous requests
measured "0 alive out of 9" in the very minute one of them was working
(`_generator/tools/orkestr.py`, red block). Free work is never launched by hand: the supervisor
distinguishes four outcomes that look identical from outside — crashed, silent, ceiling, and FALSE
SUCCESS, where opencode prints `Error:` and exits zero with the file untouched. A failed model is
dropped from the candidates and the incident logged. The liveness registry
(`doma/zahody/MODELI-ZHIVOST.json`, last taken 2026-08-31, 11 of 25 alive) is refreshed BEFORE the
wave starts.

**MEASURED 2026-09-02, before the wave, on a live OpenRouter key.** Seven free vision models were run
against an empty printed form; the correct answer is "no marks at all", and a model that finds
something on an empty form is lying. Three answered correctly — dots-3-note-preview,
nemotron-3-nano-omni, minimax-m3. Two returned 403 (not in this tier), two returned 429 (rate limit,
cured by spacing calls). **The finding that goes into the code: a model wraps its JSON in a markdown
fence even under a strict schema.** minimax-m3 returned a valid `{"rows": []}` inside a fence and the
naive parser rejected it. P7, P8 and P15 must strip the fence before parsing; a bot that does not
will drop valid answers and look broken.

### RESPONSIBILITIES — fixed here so they stop being re-decided every wave

| what | whose |
|---|---|
| MERGING a branch | the pass itself, as its last move |
| ACCEPTANCE of a returned pass | the orchestrator, per pass, in parallel |
| COMMITS ALONG THE WAY | the pass, by path, as it goes |
| THE FINAL COMMITS AND THE PUSH | the orchestrator |
| THE CLOSING PHASE | the orchestrator, before the mandate is closed |

### SCALE

Fifteen positions plus the opening commit, one night

### WHAT COUNTS AS FAILURE

Any of the eight failure conditions above. Success may not be declared by the positions merely finishing.

## HALF TWO — WRITTEN BY THE ORCHESTRATOR, ON RETURN

> Not written yet: the wave has not returned. STATUS stays `OPEN` until it has, and
> `--lint` says so out loud instead of passing in silence.

### WHAT WAS ASSEMBLED AND LAUNCHED

<NOT FILLED>

### WHAT IT REPAIRED ITSELF AND WHY IT WAS BROKEN

<NOT FILLED>

### VERDICTS

<NOT FILLED>

### WHAT WAS EXCLUDED AND WHY

<NOT FILLED>

### IRREVERSIBLE ACTIONS

<NOT FILLED>

### QUESTIONS TO THE OWNER — ANSWER IN PLACE, UNDER EACH

> 🔴 **A QUESTION HERE IS NOT A COMPLAINT — IT IS THE ONLY LAWFUL FORM OF
> «I could not do this because the decision is not mine».** An item excluded
> with a written reason that amounts to «I lacked the owner's decision» is not
> an outcome: it is a question that was never asked, and the orchestrator
> quietly decided for two people that there was no time to ask.
>
> **Form:** one `[Vn]` item per question. Each carries WHAT is blocked,
> WHAT was measured about it already, and the SHAPE of a usable answer — so the
> owner can reply in one line rather than reconstruct the problem. The owner
> writes the answer directly underneath, in place.
>
> **Empty is lawful** and means «nothing was blocked by a missing decision» —
> which is a claim, not a default, and `--lint` will not let it hide a REFUSED
> or a partially delivered wave.

<NOT FILLED>

### CLOSING PHASE — KNOWLEDGE BALANCE

> The four numbers below are the point of this section. `DELTA` is not
> stored, it is CHECKED: `--lint` recomputes `BORN` minus `CLOSED` and
> refuses a mismatch. `CARRIED` above zero REQUIRES the unjudged lessons
> to be listed BY NAME underneath — carried is lawful, silent is not.

**BORN:** `<NOT FILLED>`
**CLOSED:** `<NOT FILLED>`
**CARRIED:** `<NOT FILLED>`
**DELTA:** `<NOT FILLED>`

_Carried by name (one line each, or the single word `none`):_
<NOT FILLED>

### LINE-BY-LINE ANSWER TO EVERY FINALIZED ITEM

<NOT FILLED>

> One line per finalized item, and every item of the top half must get one: `done` or `not done` with the reason. This field is the point of the whole artifact.
- [F1] <NOT FILLED>
- [F2] <NOT FILLED>
- [F3] <NOT FILLED>
- [F4] <NOT FILLED>
- [F5] <NOT FILLED>
- [F6] <NOT FILLED>
- [F7] <NOT FILLED>
- [F8] <NOT FILLED>
- [F9] <NOT FILLED>
- [F10] <NOT FILLED>
