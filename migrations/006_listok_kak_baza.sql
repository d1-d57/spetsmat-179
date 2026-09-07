-- depends: 005_gruppy_i_kabinet_na_den
--
-- A SHEET STOPS BEING A LIST OF LABELS AND BECOMES A SET OF BLOCKS WITH TEXT.
--
-- WHY THIS MIGRATION EXISTS.  Until today the composition of a sheet was typed into
-- `problems` by hand, label by label, and had no source it could be derived from.  On
-- 2026-09-07 that cost a lesson: sheet `16α` held eleven cells `1–8, 10а, 10б, 10в`,
-- while the PDF the site itself serves has fifteen problems with the sub-items on
-- problem 14 and none on problem 10.  Eight check-offs of 5 September had nowhere to
-- land.  The fix is not more care: it is giving the composition a source.
--
-- 🔴 WHY A NEW TABLE AND NOT A REBUILT `problems`.  `problems` is the target of
-- `marks.problem_id`, and `marks` holds 16 013 rows of a school's history (measured on
-- the live server before this migration was written).  It also carries
-- `check (kind in ('обязательная','обычная','звезда','двойная'))` — a mark-level
-- classification, not a document-level one.  Widening that check means recreating the
-- table under a live foreign key with 16 013 dependants: exactly the operation that can
-- lose a mark.  So `problems` is not touched at all.  The content of a sheet lands in a
-- table of its own, and the two are joined by one nullable column.
--
-- WHAT LIVES WHERE, AFTER THIS MIGRATION:
--   * `sheet_blocks` — WHAT IS WRITTEN ON THE SHEET: every block in reading order, its
--     kind, its printed number, whether it is starred, and its TeX.  A definition, a
--     theorem or a comment lives here and is never marked by anybody.
--   * `problems`     — WHAT CAN BE CHECKED OFF: the cells the conduit has columns for
--     and `marks` points at.  Unchanged, row for row.
--   * `problems.block_id` — the link between them, nullable: a cell whose block has not
--     been imported yet is still a perfectly good cell (that is the state of every sheet
--     before its first import).
--
-- The importer `tools/import_listka.py` is the single writer of both tables and is what
-- keeps them consistent.

-- Blocks of a sheet: the document, in reading order.
create table if not exists sheet_blocks (
    id        integer primary key,
    sheet_id  integer not null references sheets(id),
    -- What kind of block this is.  Only `task` is ever markable; the rest is the prose
    -- that makes a sheet a sheet rather than a list of exercises.
    kind      text not null
        check (kind in ('task', 'definition', 'theorem', 'lemma', 'axiom', 'comment', 'figure')),
    -- The number as PRINTED on the sheet: `1`, `14`, `-1`, `0`.  Text, not integer:
    -- sheet `16ℵ` starts at `-1`, and a number is a label here, not an amount.
    -- NULL for a block that carries no number of its own (a definition between problems).
    num       text,
    -- Starred problems are an invitation, not a debt.  Kept separate from `num` because
    -- the star is a property of the problem, not part of its name.
    star      integer not null default 0 check (star in (0, 1)),
    -- The block's text, TeX as written on the sheet.  This is the payload: it is what
    -- the page renders and what the downloadable `.tex` is generated from.
    tex       text not null,
    -- Reading order within the sheet.  Not derived from `num`: an unnumbered definition
    -- sits between two numbered problems and has to keep its place.
    ord       integer not null,
    unique (sheet_id, ord)
) strict;

create index if not exists sheet_blocks_sheet on sheet_blocks (sheet_id, ord);

-- 🔴 THE ONE CHANGE TO AN EXISTING TABLE, AND IT IS ADDITIVE.  `alter table ... add
-- column` on SQLite rewrites no rows and touches no index: existing `problems` rows get
-- NULL and keep their ids, so every `marks.problem_id` still points where it pointed.
alter table problems add column block_id integer references sheet_blocks(id);
