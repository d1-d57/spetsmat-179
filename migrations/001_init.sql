-- Initial schema of the spetsmat conduit: sheets, people, sessions, and the append-only
-- journal of marks that every other position of this project reads.
--
-- Plain SQL under yoyo-migrations.  yoyo splits a .sql migration with sqlparse, which
-- keeps `create trigger ... begin ... end;` together as one statement, so the triggers
-- below survive the split intact.
--
-- Three properties are carried BY THIS FILE and not by any Python above it, because a
-- rule held only by the service layer is a hope:
--
--   * marks are append-only        — triggers raise on UPDATE and on DELETE;
--   * every enumeration is closed  — CHECK on each one;
--   * enrollment history cannot    — partial unique index on the open row plus an
--     overlap or lose a row          overlap trigger.
--
-- THE SEMANTIC FORK, WRITTEN DOWN ONCE SO THAT NOBODY REDEFINES IT IN SIX MONTHS.
-- The state of a cell is the LAST event for the pair (student_id, problem_id):
--
--   no events   -> EMPTY      not credited; a debt, if the problem is obligatory
--   'assert'    -> SOLVED     credited; counts in statistics
--   'retract'   -> RETRACTED  NOT credited, and NOT a debt: it was handed in and not
--                             defended; counts in statistics as "handed in, not credited"
--   'erratum'   -> EMPTY      struck out of statistics entirely, as if it never was;
--                             a debt again, if the problem is obligatory
--
-- Reversing an event returns the cell to EMPTY (or to RETRACTED), NEVER to whatever
-- stood there before the reversed event.  The projection never looks past the last
-- event.  To put a plus back, the teacher taps the target state again and a fresh
-- 'assert' is written -- which is safe precisely because a button carries the target
-- state and never a "toggle" command.
--
-- All times are UTC ISO-8601.  Display goes through ZoneInfo("Europe/Moscow"), never
-- through timedelta(hours=3).
--
-- Enumerated VALUES are Russian on purpose: they are data, fixed by the base schema and
-- already present in seed/sheets.json and in last year's conduit.  Renaming them would
-- silently break the importer.  The three event kinds are new and named in English.
-- config.py mirrors every list here; tests/test_schema_matches_config.py fails on drift.

create table sheets (
  id integer primary key,
  number text not null unique,
  title text,
  issued_at text not null,
  ord integer not null
) strict;

create table students (
  id integer primary key,
  tg_id integer unique,
  surname text not null,
  name text not null,
  class text,
  status text not null default 'pending'
    check (status in ('pending', 'active', 'left')),
  -- The first sheet this student was present for.  Debts are counted from it: a student
  -- who arrived at sheet 6 does not owe sheets 1-5 (evidence: Пирогов, last year).
  first_sheet_id integer references sheets(id)
) strict;

create table teachers (
  id integer primary key,
  tg_id integer unique,
  name text not null,
  aka text,
  is_owner integer not null default 0 check (is_owner in (0, 1))
) strict;

create table problems (
  id integer primary key,
  sheet_id integer not null references sheets(id),
  label text not null,
  -- Only 'обязательная' creates a debt when left unsolved; see OBLIGATORY_KINDS.
  kind text not null
    check (kind in ('обязательная', 'обычная', 'звезда', 'двойная')),
  ord integer not null,
  unique (sheet_id, label)
) strict;

create table sessions (
  id integer primary key,
  held_on text not null,
  kind text not null default 'обычное'
    check (kind in ('обычное', 'зачёт', 'отменённое'))
) strict;

-- --------------------------------------------------------------------------- marks
--
-- The journal.  Append-only, one row per event, never updated and never deleted.
--
-- (a) TWO TIMES on every mark.  valid_at is when the check-off actually happened;
--     recorded_at is when it reached this database.  A mark entered a day late must be
--     distinguishable from one entered on the spot -- with a single timestamp the two
--     collapse and the "who marked late" question stops having an answer.
--
-- (b) THREE KINDS OF EVENT instead of one deleted flag.  The distinction comes from
--     accounting (сторно) and from FHIR.  reverses_id says exactly which event is being
--     reversed; an 'assert' reverses nothing, a 'retract' or an 'erratum' must name its
--     target.
--
-- (d) APPEND-ONLY BY TRIGGER, below.

create table marks (
  id integer primary key,
  student_id integer not null references students(id),
  problem_id integer not null references problems(id),
  session_id integer references sessions(id),
  event text not null check (event in ('assert', 'retract', 'erratum')),
  reverses_id integer references marks(id),
  teacher_id integer references teachers(id),
  -- when the check-off happened
  valid_at text not null
    check (valid_at glob '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]*Z'),
  -- when it reached this database
  recorded_at text not null
    check (recorded_at glob '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]*Z'),
  source text not null
    check (source in ('кнопка', 'фото', 'голос', 'импорт')),
  note text,
  -- Transport-level idempotency: the caller passes a key derived from the Telegram
  -- update (at-least-once delivery), and a redelivered tap collides here instead of
  -- doubling the journal.  NULL means "no key given", and SQLite lets NULLs repeat.
  idempotency_key text,
  check (
    (event = 'assert' and reverses_id is null)
    or (event in ('retract', 'erratum') and reverses_id is not null)
  )
) strict;

-- The projection reads the journal cell by cell and takes the largest id.
create index marks_lookup on marks (student_id, problem_id, id);

create unique index marks_idempotency
  on marks (idempotency_key) where idempotency_key is not null;

-- An event is reversed at most once.  Without this, two retracts of the same assert are
-- legal rows and the journal stops telling a single story about what happened.
create unique index marks_reverses_once
  on marks (reverses_id) where reverses_id is not null;

-- (d) Append-only enforced BY THE SCHEMA.  These two triggers are the carrier: a direct
-- UPDATE or DELETE from any client -- the bot, a migration, a person with sqlite3 open
-- on the production file -- raises here.
create trigger marks_append_only_update
before update on marks
begin
  select raise(abort, 'marks is append-only: UPDATE forbidden, write a retract or an erratum event instead');
end;

create trigger marks_append_only_delete
before delete on marks
begin
  select raise(abort, 'marks is append-only: DELETE forbidden, write an erratum event instead');
end;

-- A foreign key can say "reverses_id is some mark"; it cannot say "and it is a mark
-- about the same student and the same problem".  Without this, a mistyped id quietly
-- reverses somebody else's plus.
create trigger marks_reverses_same_cell
before insert on marks
when new.reverses_id is not null
begin
  select raise(abort, 'reverses_id must point at an event for the same (student_id, problem_id)')
  where not exists (
    select 1 from marks m
     where m.id = new.reverses_id
       and m.student_id = new.student_id
       and m.problem_id = new.problem_id
  );
end;

create table attendance (
  id integer primary key,
  session_id integer not null references sessions(id),
  student_id integer not null references students(id),
  teacher_id integer references teachers(id),
  status text not null check (status in ('был', 'не был')),
  unique (session_id, student_id)
) strict;

-- ---------------------------------------------------------------------- enrollment
--
-- (c) Who teaches whom, as a Type 2 slowly-changing dimension.
--
-- A student's teacher changes during the year.  Stored as a current value, a
-- reassignment rewrites the past: every mark ever given by the previous teacher starts
-- reporting under the new one.  Stored as history, the past stays put.
--
-- Intervals are HALF-OPEN: [valid_from, valid_to).  The still-open row carries
-- '9999-12-31' rather than NULL -- with NULL the partial unique index below never fires
-- (NULLs are not equal to each other) and every query grows an `or valid_to is null`
-- branch that someone eventually forgets.
--
-- THE KEY IS PER LESSON DAY.  The same student may have one teacher on Monday and
-- another on Thursday (last year: Кахиани = Ваня on Mon, Ян on Thu), so weekday is part
-- of the key and not an attribute.  A teacher is bound to a group hard for the whole
-- year and never moves; students move occasionally, which is exactly what this table
-- records.

create table enrollment (
  id integer primary key,
  student_id integer not null references students(id),
  teacher_id integer not null references teachers(id),
  room text not null,
  -- ISO-8601 weekday, Monday = 1.
  weekday integer not null check (weekday between 1 and 7),
  valid_from text not null
    check (valid_from glob '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  valid_to text not null default '9999-12-31'
    check (valid_to glob '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  check (valid_from < valid_to)
) strict;

-- At most one OPEN row per (student, lesson day).  This is the cheap half of the
-- overlap guard and it is an index, so it costs nothing at read time.
create unique index enrollment_one_open_row
  on enrollment (student_id, weekday) where valid_to = '9999-12-31';

create index enrollment_by_teacher on enrollment (teacher_id, weekday, valid_from);

-- The expensive half: two CLOSED intervals for one (student, weekday) must not overlap
-- either.  Half-open overlap test: a.from < b.to and b.from < a.to.
create trigger enrollment_no_overlap_insert
before insert on enrollment
begin
  select raise(abort, 'enrollment intervals for one (student_id, weekday) must not overlap')
  where exists (
    select 1 from enrollment e
     where e.student_id = new.student_id
       and e.weekday = new.weekday
       and e.valid_from < new.valid_to
       and new.valid_from < e.valid_to
  );
end;

create trigger enrollment_no_overlap_update
before update on enrollment
begin
  select raise(abort, 'enrollment intervals for one (student_id, weekday) must not overlap')
  where exists (
    select 1 from enrollment e
     where e.id <> new.id
       and e.student_id = new.student_id
       and e.weekday = new.weekday
       and e.valid_from < new.valid_to
       and new.valid_from < e.valid_to
  );
end;
