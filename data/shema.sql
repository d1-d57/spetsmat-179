-- СНИМОК СХЕМЫ боевой базы. Записей здесь нет и быть не должно (Д1, 10.09).
-- Снят: 2026-09-10. Живая база лежит вне git — см. .gitignore.

CREATE TRIGGER enrollment_no_overlap_insert
before insert on enrollment
begin
  select raise(abort, 'enrollment intervals for one (student_id, weekday) must not overlap')
  where exists (
    select 1 from enrollment e
     where e.student_id = new.student_id
       and e.slot = new.slot
       and e.valid_from < new.valid_to
       and new.valid_from < e.valid_to
  );
end;

CREATE TRIGGER enrollment_no_overlap_update
before update on enrollment
begin
  select raise(abort, 'enrollment intervals for one (student_id, weekday) must not overlap')
  where exists (
    select 1 from enrollment e
     where e.id <> new.id
       and e.student_id = new.student_id
       and e.slot = new.slot
       and e.valid_from < new.valid_to
       and new.valid_from < e.valid_to
  );
end;

CREATE TRIGGER mark_lesson_override_append_only_delete
before delete on mark_lesson_override
begin
  select raise(abort, 'mark_lesson_override is append-only: DELETE forbidden, append another override instead');
end;

CREATE TRIGGER mark_lesson_override_append_only_update
before update on mark_lesson_override
begin
  select raise(abort, 'mark_lesson_override is append-only: UPDATE forbidden, append another override instead');
end;

CREATE TRIGGER marks_append_only_delete
before delete on marks
begin
  select raise(abort, 'marks is append-only: DELETE forbidden, write an erratum event instead');
end;

CREATE TRIGGER marks_append_only_update
before update on marks
begin
  select raise(abort, 'marks is append-only: UPDATE forbidden, write a retract or an erratum event instead');
end;

CREATE TRIGGER marks_reverses_same_cell
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

CREATE TABLE "_yoyo_log" (
            "id" VARCHAR(36),
            "migration_hash" VARCHAR(64),
            "migration_id" VARCHAR(255),
            "operation" VARCHAR(10),
            "username" VARCHAR(255),
            "hostname" VARCHAR(255),
            "comment" VARCHAR(255),
            "created_at_utc" TIMESTAMP,
            PRIMARY KEY ("id")
        );

CREATE TABLE "_yoyo_migration" (
            "migration_hash" VARCHAR(64),
            "migration_id" VARCHAR(255),
            "applied_at_utc" TIMESTAMP,
            PRIMARY KEY ("migration_hash")
        );

CREATE TABLE "_yoyo_version" (
            "version" INT NOT NULL PRIMARY KEY,
            "installed_at_utc" TIMESTAMP
        );

CREATE TABLE attendance (
  id integer primary key,
  session_id integer not null references sessions(id),
  student_id integer not null references students(id),
  teacher_id integer references teachers(id),
  status text not null check (status in ('был', 'не был')), gruppa text,
  unique (session_id, student_id)
) strict;

CREATE TABLE enrollment (
  id integer primary key,
  student_id integer not null references students(id),
  teacher_id integer not null references teachers(id),
  room text not null,
  -- ISO-8601 weekday, Monday = 1.
  slot integer not null check (slot between 1 and 7),
  valid_from text not null
    check (valid_from glob '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  valid_to text not null default '9999-12-31'
    check (valid_to glob '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  check (valid_from < valid_to)
) strict;

CREATE TABLE gruppy (
    kod       text primary key,        -- ИЯ · ДМ · НС
    starshij  text not null            -- Ваня Яковлев · Даня Макаров · Наталья Стрелкова
);

CREATE TABLE kabinet_na_den (
    data      text not null,           -- ГГГГ-ММ-ДД
    gruppa    text not null references gruppy(kod),
    kabinet   text not null,
    primary key (data, gruppa)
);

CREATE TABLE kabinety (
    kabinet         text primary key,
    rukovoditel_id  integer references teachers(id),
    zametka         text
);

CREATE TABLE mark_lesson_override (
  id integer primary key,
  mark_id integer not null references marks(id),
  -- Момент, к которому отметку отнесли. Хранится НАЧАЛО занятия, а не полночь: полночь
  -- по Москве — это предыдущий день по UTC, а колонка в UTC, и день бы уехал.
  valid_at text not null
    check (valid_at glob '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]*Z'),
  -- Кто перебил. NULL — «никто в частности»: общий пароль отдаёт `uid = None`
  -- (`veb/vhod.py::proverit_parol`), и это не ошибка, а известное состояние.
  teacher_id integer references teachers(id),
  recorded_at text not null
    check (recorded_at glob '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]*Z'),
  note text
) strict;

CREATE TABLE marks (
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

CREATE TABLE prepodavatel_ne_prihodit (
            teacher_id  integer not null references teachers(id),
            slot        integer not null check (slot between 1 and 7),
            primary key (teacher_id, slot)
        );

CREATE TABLE "problems" (
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

CREATE TABLE sent_notifications (
  id integer primary key,
  session_id integer not null references sessions(id),
  -- Who the message was addressed to.  'teacher' is the question of §2, 'head' is the
  -- summary of §3; two kinds and no more, so a new kind is a schema change somebody reads.
  recipient_kind text not null check (recipient_kind in ('teacher', 'head')),
  -- The teachers(id) of the addressee.  Not a tg_id: a person who re-registers gets a new
  -- Telegram id and would then be sent the same lesson's summary all over again.
  recipient_id integer not null references teachers(id),
  sent_at text not null,
  unique (session_id, recipient_kind, recipient_id)
) strict;

CREATE TABLE sessions (
  id integer primary key,
  held_on text not null,
  kind text not null default 'обычное'
    check (kind in ('обычное', 'зачёт', 'отменённое'))
) strict;

CREATE TABLE sheet_blocks (
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

CREATE TABLE sheets (
  id integer primary key,
  number text not null unique,
  title text,
  issued_at text not null,
  ord integer not null
) strict;

CREATE TABLE students (
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
, gruppa text) strict;

CREATE TABLE teacher_attendance (
  id integer primary key,
  session_id integer not null references sessions(id),
  teacher_id integer not null references teachers(id),
  -- The same two values as attendance.status, and the same CHECK, so the two tables can
  -- never drift into two spellings of the one fact.
  status text not null check (status in ('был', 'не был')),
  answered_at text not null,
  unique (session_id, teacher_id)
) strict;

CREATE TABLE teachers (
  id integer primary key,
  tg_id integer unique,
  name text not null,
  aka text,
  is_owner integer not null default 0 check (is_owner in (0, 1))
, kabinet text, aktiven integer not null default 1, gruppa text) strict;

CREATE TABLE "yoyo_lock" ("locked" INT DEFAULT 1, "ctime" TIMESTAMP,"pid" INT NOT NULL,PRIMARY KEY ("locked"));

CREATE INDEX enrollment_by_teacher on enrollment (teacher_id, slot, valid_from);

CREATE UNIQUE INDEX enrollment_one_open_row
  on enrollment (student_id, slot) where valid_to = '9999-12-31';

CREATE INDEX mark_lesson_override_lookup on mark_lesson_override (mark_id, id);

CREATE UNIQUE INDEX marks_idempotency
  on marks (idempotency_key) where idempotency_key is not null;

CREATE INDEX marks_lookup on marks (student_id, problem_id, id);

CREATE UNIQUE INDEX marks_reverses_once
  on marks (reverses_id) where reverses_id is not null;

CREATE INDEX sent_notifications_by_session on sent_notifications (session_id);

CREATE INDEX sheet_blocks_sheet on sheet_blocks (sheet_id, ord);
