"""UTC ISO-8601, in exactly one format, in exactly one place.

Every timestamp stored by this project is UTC and looks like ``2026-09-02T08:22:31Z``.
The schema enforces that shape with a GLOB constraint, so a second format invented
elsewhere does not drift quietly -- it raises on insert.

Display in local time goes through ``zoneinfo.ZoneInfo(config.TZ_DISPLAY)``.  Never
through ``timedelta(hours=3)``: that is wrong twice a year for every country that still
shifts its clock, and wrong forever for rows imported from earlier seasons.
"""

from __future__ import annotations

from datetime import datetime, timezone

#: The one wire format.  Seconds resolution: two taps inside the same second are ordered
#: by the journal's autoincrementing id, not by the clock, so sub-second precision would
#: buy nothing and only widen the format the schema has to accept.
ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def utc_now() -> datetime:
    """Timezone-aware current moment in UTC."""
    return datetime.now(timezone.utc)


def to_iso(moment: datetime) -> str:
    """Render a moment as the one wire format.

    A naive datetime is rejected rather than assumed to be UTC: "assumed UTC" is how a
    Moscow wall-clock time ends up in the database three hours in the past.
    """
    if moment.tzinfo is None:
        raise ValueError("naive datetime: attach a timezone before storing it")
    return moment.astimezone(timezone.utc).strftime(ISO_FORMAT)


def parse_iso(text: str) -> datetime:
    """Read the one wire format back into an aware datetime."""
    return datetime.strptime(text, ISO_FORMAT).replace(tzinfo=timezone.utc)


def now_iso() -> str:
    """Shorthand for the common case."""
    return to_iso(utc_now())
