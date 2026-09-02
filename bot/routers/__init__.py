"""Routers added by P4.

``bot/handlers/`` is P3's tree and stays P3's; the grid arrives here as a separate
package so that the two positions extend the dispatcher by ADDING, never by rewriting
each other's modules.

``marking.build_routers()`` returns TWO routers, and the difference between them is the
whole reason a stale button does not hang:

  * the SCREEN, gated to the roles that may write a mark;
  * the CATCH-ALL, included LAST, which answers every callback nobody else claimed.
    Included anywhere but last it would swallow the handlers below it.

They come from a factory rather than from module globals on purpose: a ``Router``
remembers the dispatcher it was attached to, so a global one can be built into exactly
one dispatcher per process -- which is why P3's test fixture has to null
``module.router._parent_router`` before every build.  The reason is written out in full
in ``marking.build_routers``.
"""
