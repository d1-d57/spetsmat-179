"""The Telegram bot.

P3 closed the entry: deep-link registration, role-based middleware, and the
skeleton handlers P4 (sheet upload) and P5 (viewing screens) will stand on.

Three rules that shape this tree:

  1. **Authorization is a middleware.** A check that can be forgotten in one
     handler is not a carrier -- the only honest place for a role rule is the
     outermost layer that sees every update.

  2. **Two stores, one entry point.** ``bot/app.build`` opens both databases
     and wires them in; nothing inside ``bot/`` opens a connection by hand.

  3. **Nothing here leaks below ``core/services/``.** No SQL, no journal, no
     enum from the catalogue -- only the ``RosterService`` seam and the
     ``MarkingService`` seam.
"""