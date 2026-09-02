"""Parsing a listok: from the seed's known shapes to the parser, and back.

The seed ``seed/sheets.json`` is the oracle.  Three listki of last year are
parsed back from the labels the seed already carries, and the draft is
compared to the seed row by row:

  * sheet ``1``  -- the canonical "old" layout, with header, with kinds;
  * sheet ``2д`` -- carries the ``12д`` duplicate repair (P2 already paid for
                     this knowledge; the parser must reproduce the repair);
  * sheet ``4д`` -- the sheet the seed stores WITHOUT a header row.

🔴 ``4д`` used to be described here as "has ``✘`` on every problem".  The
workbook does; ``seed/sheets.json`` does NOT -- ``grep -c '✘' seed/sheets.json``
returns 0, and P2's import kept the graveyard answer out of the label and left
it to be computed from who actually wrote the problem down.  So the round-trip
over ``4д`` exercises the graveyard path on ZERO rows, and ``✘`` is covered by
a synthetic test instead.  The false sentence was found by the §3 verifier: a
comment claiming coverage that does not exist is worse than no comment, because
the next reader stops looking.

The parser is taught the label shapes by walking the seed in ``conftest.py``.
An UNKNOWN shape raises; a silent skip would hide a label the senior typed.
"""