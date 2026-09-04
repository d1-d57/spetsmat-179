"""``GET /materials/..`` must answer 404, not crash with a 500.

This belongs conceptually next to ``tests/veb/test_server.py``, but that
directory is outside this заход's zone (``veb/server.py``, ``tests/enrollment/``,
``core/enrollment.py``, ``veb/sobrat_fajl.py``) and is read-only here, so the
regression test for the ``except Value:`` typo (``veb/server.py``, the
``/materials/`` route) lives in the one test directory this zone may write to.

Note on the literal ``..`` case: ``do_GET`` already rejects any path segment
equal to ``".."`` before ever reaching ``target.relative_to(...)`` — that
check is unaffected by the typo. The typo's actual failure mode needs the
escape to happen WITHOUT a literal ``..`` segment, which is exactly what a
symlink inside ``MATERIALS_DIR`` pointing outside it produces: no ``..``
component, but ``.resolve()`` still lands outside the directory, and it is
``relative_to``'s ``except`` clause — the one with the typo — that must catch it.
"""

from __future__ import annotations

import os
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import config
import pytest
from infra.db import apply_migrations, connect

os.environ.setdefault("SPETSMAT_VEB_SECRET", "test-secret-key-32bytes!")

import veb.server as server


@pytest.fixture
def running_server(tmp_path, monkeypatch):
    db_path = tmp_path / "spetsmat.db"
    apply_migrations(db_path, config.MIGRATIONS_DIR)
    connection = connect(db_path)
    connection.commit()

    materials_dir = tmp_path / "materials"
    materials_dir.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    secret = outside_dir / "secret.txt"
    secret.write_text("should not be servable via /materials/")
    (materials_dir / "escape").symlink_to(secret)
    monkeypatch.setattr(server, "MATERIALS_DIR", materials_dir)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    httpd.connection = connection  # type: ignore[attr-defined]
    httpd.db_path = str(db_path)   # type: ignore[attr-defined]
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join()
        connection.close()


def _get(url: str) -> int:
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status
    except urllib.error.HTTPError as exc:
        return exc.code


def test_materials_dotdot_path_is_404(running_server):
    status = _get(running_server + "/materials/../../../etc/passwd")
    assert status == 404


def test_materials_symlink_escaping_materials_dir_is_404_not_500(running_server):
    """The actual branch the ``except Value:`` typo broke: no literal ``..``,
    the escape happens through ``.resolve()`` following a symlink."""
    status = _get(running_server + "/materials/escape")
    assert status == 404
