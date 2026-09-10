-- depends: 009_perebivka_zanyatia
--
-- A FIFTH KIND OF PROBLEM: `письменная` — OBLIGATORY, AND OBLIGATORY IN WRITING.
--
-- WHY THIS MIGRATION EXISTS.  The sheets print a mark beside every problem number and
-- the site lost it.  `◦` means "hand this one in", `†` means "hand this one in in
-- writing", `⋆` means "this one is hard, and it is an invitation".  Only the star ever
-- reached the database; the circle and the dagger were dropped when the problems were
-- entered, so the conduit showed a column of bare numbers where the paper sheet showed
-- three different obligations.  The owner said it on 2026-09-09 in one sentence: «это же
-- наш прошлый кондуит стандартный… там весь этот функционал был. Тут он у тебя пропал».
--
-- `двойная` IS LEFT EXACTLY AS IT IS, deliberately.  Two rows in `problems` carry it and
-- nobody now knows what the senior meant by `**`; renaming or folding it would be a guess
-- about somebody's data, and a guess costs more than an unexplained value.
--
-- 🔴 WHY THE TABLE IS REBUILT, WHEN `006_listok_kak_baza` REFUSED TO REBUILD IT.
-- That refusal was about a DIFFERENT change and its reasoning still holds where it was
-- made: 006 needed a new column, `alter table ... add column` gives one without touching
-- a single row, so rebuilding would have been risk taken for nothing.  A CHECK list
-- cannot be widened that way — SQLite has no `alter table ... drop constraint` — so the
-- choice here is between the documented rebuild and leaving the schema unable to hold the
-- value the code is about to write.  A kind the database refuses is not a kind.
--
-- THE REBUILD IS THE PROCEDURE FROM THE SQLite MANUAL, AND EVERY STEP OF IT IS HERE:
-- a new table with the desired schema, the rows copied by explicit column list, the old
-- table dropped, the new one renamed into its place.  Three properties make it safe for
-- the 15 900 rows of `marks` that point at this table, and all three were measured on a
-- copy of the live database before this file was written:
--   * `id` IS COPIED, NOT REGENERATED.  `insert ... select id, ...` keeps every row's
--     primary key, so every `marks.problem_id` still points at the row it pointed at.
--     Measured after the rebuild: 15 900 marks join a problem, 0 marks are orphaned.
--   * FOREIGN KEYS ARE OFF WHILE A MIGRATION RUNS, and that is a fact of this project
--     rather than a hope: `infra/db.py::connect` turns them on for the APPLICATION's
--     connection, `apply_migrations` deliberately does not reuse it, and yoyo's own
--     connection leaves SQLite's default (`pragma foreign_keys` → 0, probed on this
--     tree).  So `drop table problems` does not have to fight `marks`, and `marks` keeps
--     its `references problems(id)` clause pointing at the name, which the rename
--     restores.
--   * NOTHING ELSE HANGS OFF THIS TABLE.  `sqlite_master` lists one index for it and it
--     is `sqlite_autoindex_problems_1`, created by `unique (sheet_id, label)` and
--     therefore recreated with the table.  No trigger, no view, nothing to restore.
-- After applying: `pragma foreign_key_check` → empty, `pragma integrity_check` → ok.
--
-- 🔴 THIS FILE WAS `009_vid_pismennaya.sql` UNTIL THE MERGE OF 2026-09-10 AND WAS
-- RENUMBERED, not rewritten.  The neighbouring заход of the same wave landed
-- `009_perebivka_zanyatia.sql` in `main` and on the live server while this one was being
-- written, and two migrations sharing a number is the kind of thing that reads fine on a
-- laptop and turns into "which 009 is applied here?" on the server at the moment somebody
-- needs an answer fast.  `depends:` now names it, so the order the two are applied in is
-- stated rather than left to a sort.  Nothing else in the file changed.
--
-- The Python-side copy of this list is `config.PROBLEM_KINDS`, and
-- `tests/test_schema_matches_config.py` reads the CHECK out of the LIVE schema and goes
-- red if the two ever drift.  Change one, change the other, in the same commit.

create table problems_novye (
  id integer primary key,
  sheet_id integer not null references sheets(id),
  label text not null,
  -- Both 'обязательная' and 'письменная' create a debt when left unsolved; the second
  -- says the hand-in has to be on paper.  See OBLIGATORY_KINDS.
  kind text not null
    check (kind in ('обязательная', 'обычная', 'звезда', 'двойная', 'письменная')),
  ord integer not null, block_id integer references sheet_blocks(id),
  unique (sheet_id, label)
) strict;

insert into problems_novye (id, sheet_id, label, kind, ord, block_id)
  select id, sheet_id, label, kind, ord, block_id from problems;

drop table problems;

alter table problems_novye rename to problems;
