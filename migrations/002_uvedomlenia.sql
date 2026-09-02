-- What the bot has already SAID, and whether a teacher was there at all.
--
-- depends: 001_init
--
-- Two tables, and neither one is a convenience: each closes a failure the position that
-- added them measured in the anchors rather than imagined.
--
-- (a) sent_notifications -- THE CARRIER OF "ONE LESSON, ONE MESSAGE".
--
--     The summary of one lesson goes to one person once.  A restarted process, a second
--     replica, a hand-run of the same command, a timer that fired twice because the
--     machine woke from sleep -- every one of them calls the same code a second time, and
--     every one of them must be answered by the DATABASE and not by a flag in memory,
--     which dies with the process that held it.
--
--     The unique key is (session_id, recipient_kind, recipient_id): the lesson plus the
--     addressee, exactly as the task words it.  A caller claims a row with
--     `insert ... on conflict do nothing` and reads the affected count: ONE means the
--     claim is his and he sends; ZERO means somebody already did and he stops.  The check
--     and the claim are therefore a single statement, so two processes racing on the same
--     lesson cannot both read "not sent yet" and both send.
--
--     recipient_kind is a closed set for the same reason every other enumeration in this
--     schema is: a typo in the kind ('teacher ' with a space) would silently open a second
--     namespace and deliver the message twice, which is precisely the bug the table exists
--     to make impossible.
--
-- (b) teacher_attendance -- A TEACHER IS NOT A STUDENT, AND `attendance` SAYS SO.
--
--     001_init declares `attendance.student_id integer not null references students(id)`
--     with `unique(session_id, student_id)`.  A teacher answering "был" has no row he can
--     legally occupy there: his id is not a student id, and writing it would either break
--     the foreign key or, worse, land on a real child who happens to share the number.
--
--     So the teacher's own presence gets a table shaped exactly like the student one and
--     carrying THE SAME TWO VALUES -- 'был' / 'не был', config.ATTENDANCE_STATUSES -- so
--     that attendance is one vocabulary across the project even though it is two tables.
--     Whoever later unifies them inherits a set of values that already agrees.
--
--     Idempotent by the same unique key: a teacher who taps twice updates his own row and
--     does not grow a second one.  Correcting an answer is legitimate -- he may tap "не был"
--     and then remember he did come in for ten minutes -- so the row is UPDATEABLE, unlike
--     the mark journal next door, which is append-only by trigger.  Nothing statistical is
--     derived from the history of this answer, so there is nothing for an append-only
--     journal here to protect.

create table sent_notifications (
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

create index sent_notifications_by_session on sent_notifications (session_id);

create table teacher_attendance (
  id integer primary key,
  session_id integer not null references sessions(id),
  teacher_id integer not null references teachers(id),
  -- The same two values as attendance.status, and the same CHECK, so the two tables can
  -- never drift into two spellings of the one fact.
  status text not null check (status in ('был', 'не был')),
  answered_at text not null,
  unique (session_id, teacher_id)
) strict;
