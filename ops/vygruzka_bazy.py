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
AS THE OWNER HIMSELF.

🔴 WHY NOT THE SERVICE-ACCOUNT KEY ANY MORE -- MEASURED, NOT PREFERRED.  This module used to
share ``vygruzka_v_tablicu.py``'s service-account key, and it could not work: a service account
has NO DRIVE STORAGE QUOTA OF ITS OWN, so ``files().create`` answers 403 even inside a folder
the owner owns and even when that folder is empty.  Proved live rather than read off a doc page
(``kod_bekap-v-papku.md``, clause 2): ``storageQuota.limit == "0"``, and the folder carries no
``driveId``, so it is a personal My Drive folder and not the Shared Drive that Google exempts.
Writing into an EXISTING spreadsheet creates no file, which is exactly why the conduit export
next door still works on that key and is deliberately left alone.

So the upload now runs on the owner's own OAuth credentials, collected once by hand through
``ops/avtorizacia_drive.py`` and living in ``secrets/oauth_token.json``.  The archives are owned
by the account that owns the folder, and the quota is his.

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
from ops.vygruzka_v_tablicu import SPREADSHEET_ID

#: One new label, not a new snapshot mechanism -- see the module docstring.
LABEL = "oblachnyj"

#: Where the owner's folder id lives.  Never the id itself: that would make a code change
#: the only way to react to the owner moving or recreating the folder.
DEFAULT_FOLDER_FILE = config.ROOT / "secrets" / "drive_papka.txt"

#: How many archives stay in the Drive folder.  Matches ``rezervnaya_kopia.DEFAULT_KEEP_DAYS``
#: (14) on purpose -- see the module docstring for why the two numbers being the same is the
#: point, not a coincidence.
DRIVE_KEEP = 14

#: The owner's OAuth credentials, written by ``ops/avtorizacia_drive.py``.  Mode 600, owner
#: ``spetsmat``, and -- like the key it replaces -- never anywhere near git.
DEFAULT_TOKEN_PATH = config.ROOT / "secrets" / "oauth_token.json"

#: 🔴 WHOSE DRIVE THE ARCHIVE MUST LAND IN, CHECKED ON EVERY REAL RUN.  The Cloud project
#: belongs to ``matfak57@gmail.com``; the folder and the conduit spreadsheet belong to this
#: account.  Consent given as the project's account produces a run that is successful in every
#: observable way -- rc=0, a file created, rotation performed -- into a Drive nobody will think
#: to open.  The заход's clause 2 exists against exactly that, and so does this constant: the
#: check belongs in the nightly path, not only in a one-off verification someone ran once.
OZHIDAEMYJ_AKKAUNT = "ye.mathclub@gmail.com"


class FolderMissing(Exception):
    """The owner's Drive folder id is not where it was told to be.  Said in words."""


class SoglasieProtuhlo(Exception):
    """The owner's consent no longer refreshes.  Said in words, with the one-line cure."""


class NeTotAkkaunt(Exception):
    """The token belongs to the wrong Google account -- the заход's clause 2, in code."""


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


def _credentials(token_path: Path):
    """The owner's own credentials.  The scope is NOT re-declared here on purpose: it was
    decided at consent time and is recorded in the file, so re-stating it in code would let the
    two drift apart silently and would describe rights this token may not actually carry."""
    # The existence check comes FIRST, before the imports: a missing consent file is the most
    # likely failure on a fresh checkout, and it must be reportable on a machine that has no
    # Google libraries at all -- which is exactly the machine the owner runs this from.
    if not token_path.exists():
        raise FileNotFoundError(
            "нет согласия владельца: %s -- его выдаёт ЧЕЛОВЕК, руками, один раз:\n"
            "    python3 ops/avtorizacia_drive.py\n"
            "файл живёт вне git и в свежем checkout не появляется сам" % token_path
        )

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    credentials = Credentials.from_authorized_user_file(str(token_path))
    if not credentials.valid:
        # The access token lives an hour; the refresh token is what makes an unattended
        # nightly timer possible at all.  A refresh that fails must say so in words rather
        # than surface later as an opaque 401 from some unrelated call.
        try:
            credentials.refresh(Request())
        except Exception as sboj:  # noqa: BLE001 -- the reason matters more than the type
            raise SoglasieProtuhlo(
                "согласие владельца больше не действует (%s).\n"
                "Обычные причины: доступ отозван на myaccount.google.com/permissions, "
                "или приложение вернули в режим Testing (там refresh-токен живёт 7 дней).\n"
                "Лечится одним прогоном: python3 ops/avtorizacia_drive.py" % sboj)
    return credentials


def _service(token_path: Path):
    from googleapiclient.discovery import build

    return build("drive", "v3", credentials=_credentials(token_path), cache_discovery=False)


def whoami(service) -> str:
    """The e-mail of the account this token actually belongs to.

    🔴 THE ONE QUESTION THAT CANNOT BE ANSWERED BY LOOKING AT THE RUN.  Every other outcome of
    a wrong-account authorization is indistinguishable from a right one.
    """
    return service.about().get(fields="user").execute()["user"]["emailAddress"]


def proverit_akkaunt(service, ozhidaem: str = OZHIDAEMYJ_AKKAUNT) -> str:
    """Returns the account, or refuses in words.  Called before every real upload."""
    akkaunt = whoami(service)
    if akkaunt != ozhidaem:
        raise NeTotAkkaunt(
            "согласие выдано аккаунтом %s, а папка владельца принадлежит %s.\n"
            "Архивы легли бы в чужой Диск, и выглядело бы это полностью успешным.\n"
            "Лечится повторной авторизацией ПРАВИЛЬНЫМ аккаунтом:\n"
            "    python3 ops/avtorizacia_drive.py" % (akkaunt, ozhidaem))
    return akkaunt


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


def vladelec_fajla(service, file_id: str) -> str:
    """The e-mail that owns one Drive file.  ``whoami`` says who authorized; this says who the
    upload actually made the owner -- and under a service account those two differed, which is
    the whole reason this module was rewritten."""
    owners = service.files().get(
        fileId=file_id, fields="owners", supportsAllDrives=True,
    ).execute().get("owners", [])
    return owners[0].get("emailAddress", "?") if owners else "?"


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
    parser.add_argument("--token", type=Path, default=DEFAULT_TOKEN_PATH,
                        help="путь к согласию владельца (ops/avtorizacia_drive.py)")
    parser.add_argument("--kto-zhdyom", default=OZHIDAEMYJ_AKKAUNT,
                        help="какой аккаунт обязан стоять за согласием")
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
            service = _service(arguments.token)
            akkaunt = whoami(service)
            _, can_write, name = check_access(service, folder_id)
        except (FolderMissing, FileNotFoundError, SoglasieProtuhlo) as error:
            print(error, file=sys.stderr)
            return 5
        # Printed FIRST and unconditionally: "can I write" is worthless without "as whom".
        print("согласие выдано аккаунтом: %s%s"
              % (akkaunt, "" if akkaunt == arguments.kto_zhdyom
                 else "  🔴 А ЖДАЛИ %s" % arguments.kto_zhdyom))
        print("папка %r видна; писать в неё %s" % (name, "можно" if can_write else "НЕЛЬЗЯ"))
        return 0 if can_write and akkaunt == arguments.kto_zhdyom else 5

    if arguments.perenesti_tablicu:
        try:
            folder_id = _folder_id(arguments.papka_fajl)
            service = _service(arguments.token)
            print(move_table(service, arguments.tablica, folder_id))
        except (FolderMissing, FileNotFoundError, SoglasieProtuhlo) as error:
            print(error, file=sys.stderr)
            return 5
        return 0

    try:
        archive = rezervnaya_kopia.make_backup(arguments.baza, arguments.kuda, label=LABEL)
    except (RuntimeError, FileNotFoundError, ValueError) as failure:
        print("snapshot FAILED: %s" % failure, file=sys.stderr)
        return 1
    # 🔴 NEVER PRINT THE ARCHIVE'S OWN NAME/PATH.  It ends in ``.db.gz``, and
    # ``ops/opoveshchenie.py``'s own perimeter guard (``FORBIDDEN_IN_TEXT``) refuses to send
    # ANY alert whose journal tail mentions that -- correctly, since a path is a request to
    # fetch a snapshot.  A success line printed here lingers in the unit's journal past a
    # LATER failure (the upload), so this line must stay clean even though it is not the
    # line that failed.  The directory is safe to name; only the file's own name is not.
    print("снимок: %d байт, папка %s" % (archive.stat().st_size, archive.parent))

    if not arguments.primenit:
        print("ПРОБА: снимок взят локально; в папку владельца ничего не загружено, "
              "ротация не выполнена; для загрузки -- --primenit")
        return 0

    try:
        folder_id = _folder_id(arguments.papka_fajl)
        service = _service(arguments.token)
        # 🔴 BEFORE the upload, never after: a file created under the wrong account is already
        # in the wrong Drive, and deleting it needs that same wrong account.
        akkaunt = proverit_akkaunt(service, arguments.kto_zhdyom)
        print("согласие выдано аккаунтом: %s" % akkaunt)
        file_id = upload(service, folder_id, archive)
        print("владелец загруженного архива: %s" % vladelec_fajla(service, file_id))
        total_before, kept, deleted = rotate_drive(service, folder_id, arguments.keep)
    except (FolderMissing, FileNotFoundError, SoglasieProtuhlo, NeTotAkkaunt) as error:
        print(error, file=sys.stderr)
        return 5

    print("загружено в папку владельца; архивов было %d, оставлено %d, удалено %d"
          % (total_before, kept, deleted))
    return 0


if __name__ == "__main__":
    sys.exit(main())
