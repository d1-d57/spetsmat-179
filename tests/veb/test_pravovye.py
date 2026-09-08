"""Tests for ``veb/razdely/pravovye.py``: the two static /privacy and /terms pages.

Neither route touches the database, so the fixture here is deliberately lighter than
``test_server.py``'s ``running_server`` — no migrations, no rows, no ``db_path`` override
needed. A handful of real surnames come from the project's own local ``data/spetsmat.db``
(read-only, never written to) so clause 3 of this заход's readiness criterion (no personal
data on either page) is checked against real names, not fixture ones — the surnames
themselves are asserted absent, never printed.
"""

from __future__ import annotations

import re
import sqlite3
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import config
import pytest

import veb.server as server


@pytest.fixture(scope="module")
def running_server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join()


def _get(base: str, path: str) -> tuple[int, str]:
    with urllib.request.urlopen(base + path) as r:
        return r.status, r.read().decode("utf-8")


def test_privacy_and_terms_answer_200(running_server):
    for path in ("/privacy", "/terms"):
        status, _ = _get(running_server, path)
        assert status == 200


def test_both_pages_mention_google_drive_and_its_purpose(running_server):
    for path in ("/privacy", "/terms"):
        _, body = _get(running_server, path)
        assert "Google" in body
        assert "Диск" in body


def test_neither_page_leaks_a_real_pupil_surname(running_server):
    """Clause 3: grep the real catalogue for a handful of surnames, none may appear.

    The database is read-only here (``sqlite3.connect(..., uri=True, mode=ro)`` would be
    stricter still, but this connection never executes a write) and the surnames pulled
    from it are used only for the ``assert ... not in`` check below — never printed.
    """
    if not config.DB_PATH.is_file():
        pytest.skip("no local data/spetsmat.db to check against")
    conn = sqlite3.connect(str(config.DB_PATH))
    conn.row_factory = sqlite3.Row
    surnames = [
        row["surname"]
        for row in conn.execute(
            "select distinct surname from students where surname is not null limit 6"
        ).fetchall()
    ]
    conn.close()
    assert surnames, "fixture database has no students to check against"

    _, privacy = _get(running_server, "/privacy")
    _, terms = _get(running_server, "/terms")
    for surname in surnames:
        assert surname not in privacy
        assert surname not in terms


def test_neither_page_makes_an_external_subrequest(running_server):
    """Clause 4: no ``src=``/``href=`` pointing outside this page's own site."""
    external = re.compile(r'(?:src|href)\s*=\s*["\'](https?://[^"\']+)')
    for path in ("/privacy", "/terms"):
        _, body = _get(running_server, path)
        assert external.findall(body) == []


def test_pages_carry_the_site_frame_not_a_foreign_look(running_server):
    """Clause 5 (the local half of it): same CSS variables and fonts as the rest of the
    site (``veb/obshchee/karkas.py``), a link back to the site, not a bare orphan page.
    """
    for path in ("/privacy", "/terms"):
        _, body = _get(running_server, path)
        assert "Source Sans 3" in body
        assert "Source Serif 4" in body
        assert 'href="/"' in body
