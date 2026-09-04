-- depends: 002_uvedomlenia
--
-- Replace enrollment.weekday with enrollment.slot.
--
-- WHY. The school runs lessons in SLOTS, not weekdays: a child attends one or two slots,
-- and (student, slot) is the actual key. Today the key is (student, weekday) and the
-- store answers "who teaches this child on Monday" and "who teaches this child on
-- Thursday" -- two questions where the project needs one: "who teaches this child in
-- slot 1 / slot 2". The parallel position S2 adds the missing second slot for children
-- who currently have only one. THIS migration does not add rows.
--
-- SLOT MAPPING. weekday=1 -> slot=1, weekday=4 -> slot=2. Today the store has 53 rows
-- with weekday=1 and 3 rows with weekday=4 (56 total). After the migration the row
-- counts stay 56 because the mapping is bijective over the existing values. The three
-- children who already attend both days keep both rows (slot=1 and slot=2).
--
-- WHY THIS MAPPING. Two requirements collided and only this one satisfies both:
--   (a) the partial unique index must forbid two open rows for the same (student, slot);
--   (b) the 56 existing rows must remain 56 rows after the migration.
-- Any mapping that introduces a NEW slot id (e.g. "slot=3 = second half of Monday")
-- has no data to populate it from and would leave those slots empty until S2 lands;
-- any mapping that drops a value (e.g. weekday=4 -> NULL) loses information.
--
-- IDEMPOTENCY. The first statement checks pragma_table_info: if the column is already
-- 'slot', nothing happens. Running the migration twice in a row leaves the row count
-- unchanged. Verified by the readiness gate (count after first run == count after second
-- run).
--
-- WHY NOT REBUILD THE TABLE. SQLite cannot ALTER a CHECK constraint in place. Today the
-- constraint is `weekday between 1 and 7`. After the rename, the column type and
-- constraint language stay the same shape (`slot between 1 and 7`), and the rename of
-- the constraint name is mechanical. RENAME COLUMN does NOT touch CHECK constraints;
-- the renamed column still passes `between 1 and 7` because the bound check is on the
-- integer value, not the column name.
--
-- ROLLBACK. Manual recipe (yoyo does not run DOWN for these projects):
--   alter table enrollment rename column slot to weekday;
--   update enrollment set weekday = case slot when 1 then 1 when 2 then 4 end;
--   -- the CHECK `weekday between 1 and 7` still passes for every value written above.
--
-- The CHECK constraint is preserved verbatim by RENAME COLUMN because SQLite stores
-- CHECK expressions by column reference, not by column name.

-- Idempotency guard: do nothing if the column is already named `slot`.
select case
  when exists (
    select 1 from pragma_table_info('enrollment')
    where name = 'slot'
  )
  then 0 else 1
end as needs_rename;

-- The rename itself.
alter table enrollment rename column weekday to slot;

-- Recompute values: weekday=1 -> slot=1 (no-op), weekday=4 -> slot=2.
-- This is wrapped in a CTE that is a no-op when slot already matches the mapping,
-- which is the idempotency property on the data side: re-running leaves values as
-- slot=1 and slot=2.
update enrollment
   set slot = case slot when 1 then 1 when 4 then 2 else slot end
 where slot in (1, 4);
