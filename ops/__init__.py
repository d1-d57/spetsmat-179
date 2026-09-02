"""Operational harness AROUND the bot: schedule, backups, restore check, alerting.

Nothing in this package is imported by ``bot/``, ``core/`` or ``infra/``.  The dependency
points one way only -- the harness reads the application, never the other way round --
so that a broken backup script can never take the bot down with it.
"""
