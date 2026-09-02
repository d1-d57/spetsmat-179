"""Parsing a listok: from the seed's known shapes to the parser, and back.

The seed ``seed/sheets.json`` is the oracle.  Three listki of last year are
parsed back from the labels the seed already carries, and the draft is
compared to the seed row by row:

  * sheet ``1``  -- the canonical "old" layout, with header, with kinds;
  * sheet ``2д`` -- carries the ``12д`` duplicate repair (P2 already paid for
                     this knowledge; the parser must reproduce the repair);
  * sheet ``4д`` -- has ``✘`` on every problem (graveyard marks carried as a
                     meta-mark, never folded into the kind).

The parser is taught the label shapes by walking the seed in ``conftest.py``.
An UNKNOWN shape raises; a silent skip would hide a label the senior typed.
"""