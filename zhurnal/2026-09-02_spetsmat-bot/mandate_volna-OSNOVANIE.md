# MANDATE — osnovanie

<!-- assembled by bootstrap_mandate.py; two halves, two authors; do not merge them -->

**STATUS:** `OPEN`
**TOP_HALF_STATUS:** `COMPLETE`
**BOTTOM_HALF_STATUS:** `PENDING`
**ARC:** `/sessions/eager-jolly-hawking/mnt/GitHub/spetsmat-bot/zhurnal/2026-09-02_spetsmat-bot`
**ASSEMBLED:** `2026-09-04`

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

Put a foundation under the site so it can be sent to the teachers: a permanent link, enrollment that is true for BOTH lessons of the week, and a teacher the site can tell apart from the other seventeen.

### INTERVIEW — RENDERED IN ENGLISH FROM A RUSSIAN CONVERSATION — 2026-09-04

> **ИНТЕРВЬЮ ПРОВЕДЕНО** (flag `--intervyu da` at assembly). ⚠ The flag proves the
> assembler was asked, not that the conversation happened — same honest limit
> `bootstrap_zahod.py --intervyu` already prints. ⚠ The interview was held in
> Russian and what is recorded here is the ENGLISH RENDERING of the settled
> meaning, not a quotation. A rendering can be wrong, and only the owner can
> say so.

- **Q1** — Q: Q1
  — M: Owner confirmed the goal verbatim: this wave is about the foundation, not about new features, because it was the missing foundation and not the missing features that sank the previous evening.
- **Q2** — Q: Q2
  — M: Owner REJECTED the proposed boundary list on one point: creating the repositories and the tunnel must be INSIDE this wave, not outside it. Added as position N7 and as a finalized item; the remaining four boundaries stand.
  — note: This reverses the previous wave arrangement, where P7 sat in the composition and was never run. Naming it in-scope is the correction.
- **Q3** — Q: Q3
  — M: Owner accepted all three failure conditions unchanged and added none.
- **Q4** — Q: Q4
  — M: Owner confirmed all four obligatory items, and by the answer to Q2 a fifth was added. Marking screen (N4) and last year conduit (N5) stay desirable but NOT obligatory: the wave is not failed without them.

### FINALIZED AT INTERVIEW — 2026-09-04

- [F1] enrollment keyed by slot (1 or 2), not by ISO weekday: after import, 112 open rows for 56 children, and every child present on BOTH slots
- [F2] the permanent link the teachers receive is the GitHub Pages address, never the tunnel address; the page carries an honest fallback saying the machine is off and marks are taken on paper
- [F3] no teacher password exists at all: the teacher enters through a personal one-time link from the bot, and the cookie carries teacher_id rather than the role 'some teacher'
- [F4] a roster check tool that names suspicious rows (a person with no class, a child with no enrollment) and deletes nothing by itself
- [F5] spetsmat-179 is a real repository published on Pages, spetsmat-bot has an origin, and the tunnel address survives a restart

### BOUNDARIES AND WHAT IS ALREADY CLOSED

- student personal accounts: stage 3, explicitly forbidden to think about in this wave
- buying a VPS: the tunnel from the owner's machine solves this for the coming days
- encrypting the Pages snapshot: a named possibility, not a task, until marks appear in the snapshot
- fixing the stop-hook: it lives in the disciplina repository where another wave (ORK-NOCH) is live; diagnosed here, repaired there
- a second store of enrollment or a second journal of marks: named as the failure of the previous wave and still forbidden

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

### RESPONSIBILITIES — fixed here so they stop being re-decided every wave

| what | whose |
|---|---|
| MERGING a branch | the pass itself, as its last move |
| ACCEPTANCE of a returned pass | the orchestrator, per pass, in parallel |
| COMMITS ALONG THE WAY | the pass, by path, as it goes |
| THE FINAL COMMITS AND THE PUSH | the orchestrator |
| THE CLOSING PHASE | the orchestrator, before the mandate is closed |

### SCALE

Seven positions over one night plus the owner's morning. N1 runs first and alone because it moves the schema; N2-N6 run in parallel after it; N7 is interactive and runs on the owner's machine under his own gh account.

### WHAT COUNTS AS FAILURE

Any one of three, each checkable by command: (a) the link is sent to the teachers while 53 of 56 children still have nobody on the second lesson day; (b) the address handed out is a throwaway tunnel again, dying on restart; (c) a second store of enrollment or a second journal of marks appears anywhere.

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
