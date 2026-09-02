"""Makes ``tests/text`` a package, on purpose and not by habit.

Two things follow from the file existing, and both are already open заявки against this
tree (`2026-09-02T13:01` and `2026-09-02T15:09`):

  * ``from .conftest import OWNER_LINES`` works.  Without a package there is no parent
    module and the relative import is an ImportError at COLLECTION -- the whole run stops,
    not one test.
  * The module is named by its full path rather than by its basename.  Two test files
    sharing a basename in different folders otherwise collide with «import file mismatch»
    at collection, and that measured accident (``tests/views/test_privacy.py`` against
    ``tests/photo/test_privacy.py``, 02.09) collected zero tests for everybody.

This closes the class for THIS folder only -- ``tests/`` and its other subfolders are
outside this position's zone, and the заявка that would close it everywhere stays open.
"""
