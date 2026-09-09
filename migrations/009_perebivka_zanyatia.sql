-- depends: 008_gruppa_na_zanyatii
--
-- ПЕРЕБИВКА ЗАНЯТИЯ У ОТМЕТКИ. Решение владельца 09.09, его словами: «бывает ситуация,
-- когда вносит преподаватель, бывает, преподаватель забыл, и в конце четверти я пришёл
-- к человеку, говорю, у тебя долги… конечно, это тогда по сути постфактум ставится».
--
-- 🔴 ПОЧЕМУ ЭТО ОТДЕЛЬНАЯ ТАБЛИЦА, А НЕ КОЛОНКА В `marks`. Журнал append-only, и это
-- держат триггеры `marks_append_only_update` / `marks_append_only_delete` в
-- `001_init.sql`, а не договорённость: `update marks set valid_at = …` падает у любого
-- клиента. Перебивка обязана быть ДОПИСЫВАНИЕМ, и она им и является — ряд здесь, а
-- не правка ряда там. Владелец сказал о журнале ровно то же: «события из журнала не
-- удаляются никогда».
--
-- 🔴 ЗАНЯТИЕ ОТМЕТКИ ПО УМОЛЧАНИЮ НЕ ХРАНИТСЯ ВОВСЕ. Оно ВЫЧИСЛЯЕТСЯ из `valid_at`
-- правилом «последнее НАЧАВШЕЕСЯ занятие» (`core/services/history.py::zanyatie_dlya`),
-- поэтому у всех 15 900 событий, которые уже лежат в журнале, занятие есть сегодня же
-- и без единой записи сюда. Строка появляется только там, где ЧЕЛОВЕК сказал, что
-- правило ошиблось. Пустая таблица — нормальное и ожидаемое состояние.
--
-- ДЕЙСТВУЕТ ПОСЛЕДНЯЯ. Перебивок у одной отметки может быть несколько (человек может
-- ошибиться и во второй раз тоже), и побеждает та, у которой больше `id` — ровно так же,
-- как состояние клетки есть ПОСЛЕДНЕЕ её событие. Второй формы «правильности» в проекте
-- не заводится.

create table mark_lesson_override (
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

-- Читают всегда одинаково: «последняя перебивка этой отметки» и «последние перебивки
-- вот этих отметок» — то есть по `mark_id`, беря максимальный `id`.
create index mark_lesson_override_lookup on mark_lesson_override (mark_id, id);

-- След не стирается и не переписывается — по той же причине и тем же способом, что и
-- сам журнал. Без этих двух триггеров «перебивка оставляет след» держалось бы только
-- тем, что никто не написал `update`.
create trigger mark_lesson_override_append_only_update
before update on mark_lesson_override
begin
  select raise(abort, 'mark_lesson_override is append-only: UPDATE forbidden, append another override instead');
end;

create trigger mark_lesson_override_append_only_delete
before delete on mark_lesson_override
begin
  select raise(abort, 'mark_lesson_override is append-only: DELETE forbidden, append another override instead');
end;
