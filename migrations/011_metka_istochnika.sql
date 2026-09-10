-- depends: 010_vid_pismennaya
--
-- THE DATABASE SAYS WHAT IT IS, FROM INSIDE ITSELF.
--
-- WHY THIS MIGRATION EXISTS.  Until 2026-09-10 the only way to tell the live database
-- from a dead copy was to look at it from outside: the file name (identical), the file
-- date (a `git checkout` or an rsync updates it without adding a row -- the orchestrator
-- of wave УТРО read 12:21 today off a file whose latest record was 3 September), or the
-- freshness of its newest record.  Freshness alone is not enough and the reason is
-- ordinary: on a Monday morning the LIVE database is also "behind the last session", so
-- the signal is noisy exactly when somebody needs it.  A copy must not be able to call
-- itself боевая even by accident, so the answer has to be written INSIDE the file, where
-- copying carries it along and the copying door can then correct it.
--
-- THREE FIELDS AND NO MORE.
--   * `род`   — боевая | копия | тест.  Which of the three this file is.
--   * `хост`  — the machine the stamp was made on.  🔴 WITHOUT THE HOST HALF THE STAMP IS
--     WORTHLESS: `cp` of the live file inherits the word "боевая" verbatim, and the copy
--     then passes every check the word alone can support.  `core/istochnik.py` compares
--     the stamped host with the machine it is running on and refuses a "боевая" file that
--     is being opened somewhere else -- that is a carried-off copy by construction.
--   * `когда` / `откуда` — when the stamp was made and, for a copy, which file it was
--     taken from.  These do not gate anything; they are what a person reads when the
--     refusal has already happened and the question is "so which file IS this?".
--
-- 🔴 THE SEEDED ROW IS `тест`, NOT `боевая`, AND THAT IS THE WHOLE SAFETY PROPERTY.
-- A migration cannot know which machine it is being applied on, so it must not guess in
-- the direction that grants trust.  Every database that gets this migration -- a fresh
-- test database in a temp directory, a restored snapshot, the live file on the server --
-- starts out as `тест` and therefore refuses to hand out боевые numbers.  Exactly one
-- explicit command, run once, on the server, promotes the live file:
--
--     SPETSMAT_BAZA=/srv/spetsmat/data/spetsmat.db python3 core/istochnik.py --pometit боевая
--
-- The direction of the default is the point: a file that nobody vouched for is a file
-- nobody should be quoting numbers from.
--
-- ONE ROW, ENFORCED BY THE SCHEMA (`check (id = 1)`), not by convention.  Two rows would
-- be two answers to "what is this file", which is the same disease one level down.

create table istochnik_metka (
  id integer primary key check (id = 1),
  rod text not null check (rod in ('боевая', 'копия', 'тест')),
  host text not null default '',
  kogda text not null default '',
  otkuda text not null default ''
) strict;

insert into istochnik_metka (id, rod, host, kogda, otkuda)
  values (1, 'тест', '', '', 'засеяна миграцией 011: род не подтверждён человеком');
