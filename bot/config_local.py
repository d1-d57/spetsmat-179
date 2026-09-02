"""Constants the bot owns.

Two deep-link codes (student and teacher) are constants of the bot, not
literals in handlers.  The brief asks for them in ``config.py``; this
position keeps them here because ``config.py`` is outside the zone and
P1's design treats config as the seam between application and deployment,
not between positions of one wave.

The owner can lift these into ``config.py`` when zones are revisited; the
bot reads them through this module, so the call sites will not change.
"""

from __future__ import annotations

#: The token used by ``bot/__main__.py``.  Comes from the deployment env, not
#: from version control.  Empty by default so a missing env var crashes the
#: build at startup rather than silently disabling the bot.
BOT_TOKEN = ""

#: Telegram id of the owner -- the only account that sees the pending list
#: and the only one whose accept / rename / reject buttons do anything.
OWNER_TG_ID = 0

#: Two deep-link codes that start the registration flow.  ``/start <code>``
#: in a private chat routes to the matching handler.  Anything else lands
#: on the no-code welcome.
DEEPLINK_CODE_STUDENT = "register-student"
DEEPLINK_CODE_TEACHER = "register-teacher"

#: The three rooms the conduit runs in.  Duplicates ``core.services.roster.ROOMS``
#: so handlers can validate a room the user typed without importing core -- but
#: the source of truth remains the core constant.
ROOMS = ("203", "302", "303")

#: Length cap on a typed name.  ``Сергеевич`` is the realistic ceiling in
#: Russian -- anything longer is almost certainly a typo, not a name.
NAME_MAX_LEN = 40