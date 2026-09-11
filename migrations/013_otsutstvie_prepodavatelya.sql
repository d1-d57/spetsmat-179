-- depends: 012_metka_znaet_svoj_put
--
-- A PERIOD OF ABSENCE OF A TEACHER: from which date to which, and why.
--
-- THE OWNER'S OWN WORDS, 11.09: «Есть Ольга Александровна, Ольга Рыжая, которая не
-- будет с 1 по 12 октября… чтобы в будущих всех распределениях период этот на всех
-- занятиях этого периода уже не появлялось в списке преподавателей… Мы можем отмечать
-- это в текущем распределении, что он заболел, а можем отмечать это в распределении на
-- будущее.»
--
-- 🔴 WHY NEITHER EXISTING TABLE COULD HOLD THIS, AND THIS IS READ OUT OF THE CODE,
-- NOT GUESSED.
--   * `teacher_attendance(session_id, teacher_id, status)` is «сегодня заболел». It
--     hangs off a `sessions` row, and `veb/server.py::_OtsutstvieNaDatuAdapter` states
--     the consequence in its own docstring: *«A date with no `sessions` row has no
--     absence either: the lesson has not been opened yet»*. The live case is twelve
--     October days of which ten are not lesson days at all and none has a `sessions`
--     row — in that table the period is not expressible, it is invisible.
--   * `prepodavatel_ne_prihodit(teacher_id, slot)` (migration 007) is «по четвергам не
--     хожу вообще»: a weekday, forever, with no dates. A period that starts and ends
--     is not a weekday rule, and writing one as the other would make the teacher
--     disappear from every Thursday of the year instead of two of them.
-- So this is a third fact, and it gets a third table rather than a fourth meaning
-- squeezed into one of the first two.
--
-- 🔴 BOTH ENDS ARE INCLUSIVE, AND THAT IS THE OWNER'S SENTENCE, NOT A CONVENTION.
-- «с 1 по 12 октября» is twelve days, and the готовности criterion of the задание
-- counts twelve. A half-open `po_datu` would have made `2026-10-12` a working day for
-- a person who is not there, and the count would have read eleven — the кто-то would
-- have had to notice a missing day rather than a wrong one.
--
-- 🔴 SEVERAL PERIODS PER TEACHER ARE ALLOWED, AND OVERLAPS ARE NOT FORBIDDEN. Two
-- rows that overlap are not a contradiction — they are two notes about the same days
-- («болезнь» and then «отъезд» announced later), and a person absent twice over is
-- still absent. `enrollment` forbids overlaps because two different teachers for one
-- day would be two different answers to one question; here every row says the same
-- word, «нет», and there is nothing to disagree about.
--
-- 🔴 `prichina` IS A FIXED SET, BECAUSE THE задание NAMES IT AS ONE:
-- «почему (болезнь/отъезд/иное)». A free-text column would have collected «болеет»,
-- «болен», «заболела» and «б-нь» within a term, and nothing could then count them.
-- `иное` is the escape hatch, and the note travels in `zametka`.
create table if not exists otsutstvie_prepodavatelya (
    id           integer primary key,
    teacher_id   integer not null references teachers(id),
    -- ISO-8601, both ends INCLUSIVE. Same `glob` shape the rest of the schema uses:
    -- a date that is not a date has to be refused by the база, not by the caller.
    s_daty       text not null
        check (s_daty glob '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    po_datu      text not null
        check (po_datu glob '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    prichina     text not null
        check (prichina in ('болезнь', 'отъезд', 'иное')),
    zametka      text,
    -- Who marked it. NULL is a known state, not an error: the COMMON organiser
    -- password hands out no `uid` at all (`veb/vhod.py::proverit_parol` returns
    -- `("organizator", None)`), and the same NULL is already legal in
    -- `mark_lesson_override.teacher_id` for exactly this reason.
    kto_otmetil  integer references teachers(id),
    kogda        text not null,
    check (s_daty <= po_datu)
);

-- Читается всегда одинаково: «кого нет в этот день». Индекс по человеку и началу
-- периода — тот же порядок, в котором идёт и выборка, и показ в журнале.
create index if not exists otsutstvie_po_prepodavatelyu
    on otsutstvie_prepodavatelya (teacher_id, s_daty);
create index if not exists otsutstvie_po_datam
    on otsutstvie_prepodavatelya (s_daty, po_datu);
