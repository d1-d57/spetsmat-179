"""Nightly database archive -> the owner's Google Drive folder, so a dead machine does not
take everything with it.

WHY THIS EXISTS.  ``ops/rezervnaya_kopia.py`` snapshots the database and, by its own design,
sends nothing out (see that module's docstring: "that absence is the feature") -- every
snapshot it takes lands in ``data/backups`` on this same machine.  ``ops/vygruzka_v_tablicu.py``
already gives the conduit itself an off-server home, but a spreadsheet of check-offs is not
the database: it carries none of the distribution, attendance, teacher roster or listok
structure.  Losing the machine today loses all of that.  This tool is the door that leaves
for the rest: it takes one snapshot through the SAME path ``rezervnaya_kopia.make_backup``
already proved correct on a live, WAL-mode database (never a raw file copy -- see that
module for why), and uploads the resulting ``.db.gz`` into the owner's own Drive folder,
through the SAME service-account key ``vygruzka_v_tablicu.py`` already uses.

NOT A SECOND SNAPSHOT MECHANISM.  This module adds exactly one new label, ``"oblachnyj"``,
to ``rezervnaya_kopia.LABELS`` -- a name, not a rewrite -- so an archive bound for Drive is
greppable apart from the three purely-local cadences.  The VACUUM INTO / gzip code itself is
not touched or duplicated here.

ROTATION HAPPENS ONLY IN THE DRIVE FOLDER, NOT AGAIN LOCALLY.  ``rezervnaya_kopia.rotate()``
is label-agnostic (it globs every ``spetsmat-*.db.gz`` regardless of label) and the existing
daily timer already calls it, so the local copy of every ``oblachnyj`` snapshot is already
swept by infrastructure that exists.  A second local-rotation path here would be exactly the
kind of reinventing the interview asked not to do.  ``DRIVE_KEEP`` mirrors
``rezervnaya_kopia.DEFAULT_KEEP_DAYS`` (14) so both the local and the off-server retention
windows answer "how far back can this be restored" the same way.

DRY-RUN BY DEFAULT.  Without ``--primenit`` this takes a real local snapshot (there is no
dry-run concept one layer down in ``rezervnaya_kopia`` either -- every other timer built on
it always writes for real) but makes NO network call at all: it prints the snapshot it took
and what it would upload and rotate.  ``--primenit`` performs the real upload and rotation.

    python3 ops/vygruzka_bazy.py                        # real local snapshot, no network
    python3 ops/vygruzka_bazy.py --primenit              # snapshot, upload, rotate for real
    python3 ops/vygruzka_bazy.py --proverit-dostup       # one read-only Drive check, nothing else
    python3 ops/vygruzka_bazy.py --perenesti-tablicu     # one-off: move the conduit sheet here too

THE FOLDER ID IS NEVER IN CODE, NEVER PRINTED, NEVER LOGGED.  It lives in
``secrets/drive_papka.txt`` (owner-created folder, robot given Editor access -- see
``zhurnal/2026-09-02_spetsmat-bot/kod_bekap-v-papku.md``, ПРАВКА 1) and is read fresh on every
call.  A missing or unreadable file stops the run with a named reason instead of guessing.
"""

# TOOL-CONTRACT: called-by-hand
#
# Same shape as ops/vygruzka_v_tablicu.py's own declaration: `git_zona.py vlit-v-osnovnuyu`'s
# cross-repo `has_live_trigger` scan cannot see this repo's `deploy/*.service` ExecStart
# lines, so the real live call point is named here instead. It is one:
# `deploy/spetsmat-vygruzka-bazy.service` runs `--primenit` nightly, and a person types the
# bare form for the probe or one of the two one-off flags by hand.

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from ops import rezervnaya_kopia
from ops.vygruzka_v_tablicu import DEFAULT_KEY_PATH, SPREADSHEET_ID

#: One new label, not a new snapshot mechanism -- see the module docstring.
LABEL = "oblachnyj"

#: Where the owner's folder id lives.  Never the id itself: that would make a code change
#: the only way to react to the owner moving or recreating the folder.
DEFAULT_FOLDER_FILE = config.ROOT / "secrets" / "drive_papka.txt"

#: How many archives stay in the Drive folder.  Matches ``rezervnaya_kopia.DEFAULT_KEEP_DAYS``
#: (14) on purpose -- see the module docstring for why the two numbers being the same is the
#: point, not a coincidence.
DRIVE_KEEP = 14

SCOPES = ["https://www.googleapis.com/auth/drive"]


class FolderMissing(Exception):
    """The owner's Drive folder id is not where it was told to be.  Said in words."""


def _folder_id(path: Path) -> str:
    if not path.exists():
        raise FolderMissing(
            "нет id папки владельца: %s\n"
            "владелец создаёт папку на своём Диске сам и кладёт её id сюда -- см. "
            "ПРАВКА 1, zhurnal/2026-09-02_spetsmat-bot/kod_bekap-v-papku.md" % path
        )
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise FolderMissing("файл %s пуст -- в нём должен быть только id папки" % path)
    return value


def _credentials(key_path: Path):
    from google.oauth2.service_account import Credentials

    if not key_path.exists():
        raise FileNotFoundError(
            "нет ключа сервисного аккаунта: %s -- ключ живёт вне git и не появляется в "
            "свежем checkout сам" % key_path
        )
    return Credentials.from_service_account_file(str(key_path), scopes=SCOPES)


def _service(key_path: Path):
    from googleapiclient.discovery import build

    return build("drive", "v3", credentials=_credentials(key_path), cache_discovery=False)


def check_access(service, folder_id: str) -> tuple[bool, bool, str]:
    """``(readable, can_add_children, name)`` for the folder -- ПРАВКА 1's "check first"."""
    metadata = service.files().get(
        fileId=folder_id, fields="name,capabilities", supportsAllDrives=True,
    ).execute()
    capabilities = metadata.get("capabilities", {})
    return True, bool(capabilities.get("canAddChildren")), metadata.get("name", "?")


def list_archives(service, folder_id: str) -> list[dict]:
    """Every ``spetsmat-*.db.gz`` this robot itself put in the folder, id and name only."""
    query = "'%s' in parents and name contains 'spetsmat-' and trashed = false" % folder_id
    entries: list[dict] = []
    page_token = None
    while True:
        response = service.files().list(
            q=query, fields="nextPageToken, files(id, name)",
            pageToken=page_token, supportsAllDrives=True, includeItemsFromAllDrives=True,
        ).execute()
        entries.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            return entries


def plan_rotation(names: list[str], keep: int) -> tuple[list[str], list[str]]:
    """``(kept, to_delete)``, newest first -- pure, no Drive call.

    The timestamp in ``rezervnaya_kopia.snapshot_name`` sorts lexicographically the same way
    it sorts chronologically, so a plain name sort is enough: no need to parse dates back out.
    """
    ordered = sorted(names, reverse=True)
    return ordered[:keep], ordered[keep:]


def rotate_drive(service, folder_id: str, keep: int = DRIVE_KEEP) -> tuple[int, int, int]:
    """Upload-side rotation.  Returns ``(total_before, kept, deleted)``."""
    entries = list_archives(service, folder_id)
    by_name = {entry["name"]: entry["id"] for entry in entries}
    kept, to_delete = plan_rotation(list(by_name), keep)
    for name in to_delete:
        service.files().delete(fileId=by_name[name], supportsAllDrives=True).execute()
    return len(entries), len(kept), len(to_delete)


def upload(service, folder_id: str, path: Path) -> str:
    """Uploads ``path`` into the folder; returns the new file's id."""
    from googleapiclient.http import MediaFileUpload

    metadata = {"name": path.name, "parents": [folder_id]}
    media = MediaFileUpload(str(path), mimetype="application/gzip", resumable=False)
    created = service.files().create(
        body=metadata, media_body=media, fields="id", supportsAllDrives=True,
    ).execute()
    return created["id"]


def table_parents_after_move(current_parents: list[str], folder_id: str) -> tuple[str, str] | None:
    """``(add, remove)`` for ``files().update``, or ``None`` if already parented correctly.

    Pure and testable without touching the network: the one judgment call
    ``--perenesti-tablicu`` makes.
    """
    if folder_id in current_parents:
        return None
    return folder_id, ",".join(current_parents)


def move_table(service, spreadsheet_id: str, folder_id: str) -> str:
    """Moves the conduit spreadsheet's PARENT, never recreates it -- see the module docstring
    and item D of the readiness criterion: the id the nightly export writes to must not change.
    """
    metadata = service.files().get(
        fileId=spreadsheet_id, fields="parents", supportsAllDrives=True,
    ).execute()
    current = metadata.get("parents", [])
    plan = table_parents_after_move(current, folder_id)
    if plan is None:
        return "таблица кондуита уже в папке владельца -- ничего не делать"
    add, remove = plan
    service.files().update(
        fileId=spreadsheet_id, addParents=add, removeParents=remove,
        fields="id, parents", supportsAllDrives=True,
    ).execute()
    return "таблица кондуита перенесена в папку владельца"


def main(argv: list[str] | None = None) -> int:
    """Returns an exit code, ALWAYS -- see ops/vygruzka_v_tablicu.py for why that is stated
    rather than assumed in this codebase."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--primenit", action="store_true",
                        help="загрузить снимок и прочистить папку по-настоящему; без флага -- только проба")
    parser.add_argument("--proverit-dostup", action="store_true",
                        help="только проверить доступ к папке владельца и выйти")
    parser.add_argument("--perenesti-tablicu", action="store_true",
                        help="разовое: перенести таблицу кондуита в ту же папку и выйти")
    parser.add_argument("--baza", type=Path, default=None,
                        help="путь к базе; по умолчанию config.DB_PATH")
    parser.add_argument("--kuda", type=Path, default=None,
                        help="локальная папка снимков; по умолчанию rezervnaya_kopia.DEFAULT_BACKUP_DIR")
    parser.add_argument("--klyuch", type=Path, default=DEFAULT_KEY_PATH,
                        help="путь к ключу сервисного аккаунта")
    parser.add_argument("--papka-fajl", type=Path, default=DEFAULT_FOLDER_FILE,
                        help="файл с id папки владельца")
    parser.add_argument("--tablica", default=SPREADSHEET_ID,
                        help="id таблицы кондуита; по умолчанию таблица владельца")
    parser.add_argument("--keep", type=int, default=DRIVE_KEEP,
                        help="сколько архивов оставлять в папке")
    arguments = parser.parse_args(argv)

    if arguments.proverit_dostup:
        try:
            folder_id = _folder_id(arguments.papka_fajl)
            service = _service(arguments.klyuch)
            _, can_write, name = check_access(service, folder_id)
        except (FolderMissing, FileNotFoundError) as error:
            print(error, file=sys.stderr)
            return 5
        print("папка %r видна роботу; писать в неё %s" % (name, "можно" if can_write else "НЕЛЬЗЯ"))
        return 0 if can_write else 5

    if arguments.perenesti_tablicu:
        try:
            folder_id = _folder_id(arguments.papka_fajl)
            service = _service(arguments.klyuch)
            print(move_table(service, arguments.tablica, folder_id))
        except (FolderMissing, FileNotFoundError) as error:
            print(error, file=sys.stderr)
            return 5
        return 0

    try:
        archive = rezervnaya_kopia.make_backup(arguments.baza, arguments.kuda, label=LABEL)
    except (RuntimeError, FileNotFoundError, ValueError) as failure:
        print("snapshot FAILED: %s" % failure, file=sys.stderr)
        return 1
    print("снимок: %s (%d байт)" % (archive, archive.stat().st_size))

    if not arguments.primenit:
        print("ПРОБА: снимок взят локально; в папку владельца ничего не загружено, "
              "ротация не выполнена; для загрузки -- --primenit")
        return 0

    try:
        folder_id = _folder_id(arguments.papka_fajl)
        service = _service(arguments.klyuch)
        upload(service, folder_id, archive)
        total_before, kept, deleted = rotate_drive(service, folder_id, arguments.keep)
    except (FolderMissing, FileNotFoundError) as error:
        print(error, file=sys.stderr)
        return 5

    print("загружено в папку владельца; архивов было %d, оставлено %d, удалено %d"
          % (total_before, kept, deleted))
    return 0


if __name__ == "__main__":
    sys.exit(main())
