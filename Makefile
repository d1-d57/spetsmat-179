# ONE check command, and it is the one the готовности criterion runs.
#
#   make check   ->  applies every migration to a temp FILE database, then runs pytest,
#                    and prints the test count.
#
# The migration step is not decoration: pytest builds its own database per test through
# the fixtures, so a schema that fails to apply outside pytest -- a bad split of a
# trigger, a yoyo bookkeeping clash -- would otherwise be found by the deploy instead of
# by this command.
#
# THE TEMP DATABASE IS A FILE, never :memory:.  WAL does not work on an in-memory
# database with more than one connection, and WAL is the whole reason this project uses
# SQLite the way it does; an in-memory check would be checking a different database from
# the one that runs.
#
# PYTHON is overridable so the same target serves a bare machine and a virtualenv:
#     make check                          # the system interpreter
#     make check PYTHON=.venv/bin/python  # a venv, if the deps live there instead
# The criterion calls `python3 -m pytest` directly, so the default is `python3` and not
# a venv the criterion would never look into.

PYTHON ?= python3
TMPDB := $(shell mktemp -d)/spetsmat-check.db

.PHONY: check deps migrate test clean

check: deps migrate test

deps:
	@$(PYTHON) -c "import pytest, yoyo" 2>/dev/null \
	  || { echo "missing test dependencies for $(PYTHON)."; \
	       echo "install them with:  $(PYTHON) -m pip install --user pytest yoyo-migrations"; \
	       exit 1; }
	@echo "deps: pytest and yoyo-migrations importable by $(PYTHON)"

migrate:
	@echo "migrate: applying migrations to $(TMPDB)"
	@$(PYTHON) -c "import sys; sys.path.insert(0, '.'); \
	from infra.db import apply_migrations; \
	applied = apply_migrations('$(TMPDB)'); \
	print('migrate: applied %d migration(s): %s' % (len(applied), ', '.join(applied))); \
	sys.exit(0 if applied else 1)"

test:
	$(PYTHON) -m pytest -q

# The live database is never touched here -- only the temp files this target made.
clean:
	@rm -rf .pytest_cache
	@find . -name '__pycache__' -type d -prune -exec rm -rf {} +
	@echo "clean: caches removed; the database under data/ was not touched"
