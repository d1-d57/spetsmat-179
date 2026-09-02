"""Handlers the bot exposes, grouped by what they do.

Each module exposes a single ``Router`` named ``router``.  ``bot/app.build``
includes them in this order:

  * ``registration``  -- the deep-link flows, open to strangers;
  * ``owner``         -- the moderation screen, open to the owner only;
  * ``student``       -- the student-only screens;
  * ``teacher``       -- the teacher-only screens (HEAD shares them).

A handler that ignores its group belongs here: the per-group ``require_role``
middleware is what enforces the boundary.
"""