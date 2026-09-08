"""One-off: the owner authorizes this deployment against HIS OWN Google account, by hand.

WHY THIS EXISTS.  ``ops/vygruzka_bazy.py`` used to upload the nightly archive through the same
service-account key ``ops/vygruzka_v_tablicu.py`` uses, and it could not work -- not through a
bug, through a documented Google rule: a service account has no Drive storage quota of its own,
so ``files().create`` answers 403 even in a folder the owner owns and even when that folder is
empty.  Measured, not assumed, by the previous заход (``zhurnal/2026-09-02_spetsmat-bot/
kod_bekap-v-papku.md``, clause 2: ``storageQuota.limit == "0"``, folder has no ``driveId`` and
is therefore a plain personal My Drive folder).  The remedy the owner chose is the first of the
three that заход offered: the archive is created BY THE OWNER'S OWN ACCOUNT, so the owner owns
the files and the quota is his.  This tool is the one place where that consent is collected.

🔴 THE ACCOUNT IS THE WHOLE POINT, AND IT IS NOT THE OBVIOUS ONE.  The Cloud project lives in
``matfak57@gmail.com``.  The Drive folder and the conduit spreadsheet live in
``ye.mathclub@gmail.com``.  Consent must be given by the SECOND.  Authorize as the first and
everything still looks successful -- archives are created, rc=0, the timer goes green -- and the
mistake surfaces only when a person opens the folder and finds it empty.  That is why this tool
shouts the account name before it opens anything, and why ``ops/vygruzka_bazy.py`` checks
``about().get(fields="user")`` rather than trusting that this went well.

STANDARD LIBRARY ONLY, ON PURPOSE.  The owner runs this on his laptop, and that laptop has
Python 3.9.6 with no ``google_auth_oauthlib`` (checked, not assumed).  Installing packages on
the owner's machine to collect one consent is a worse trade than writing the flow out: an
installed-app OAuth flow is a URL, a redirect caught on loopback, and one POST.  What this
writes is the ordinary ``authorized_user`` JSON shape, which the SERVER's ``google-auth``
(2.57.1) reads natively through ``Credentials.from_authorized_user_file`` -- so the library
lives where the libraries already are, and the laptop stays clean.

THE CLIENT SECRET IS READ FROM THE SERVER, NEVER KEPT ON THE LAPTOP.  ``secrets/`` on the
server is the one home for it (``.gitignore`` line 2, mode 600, owner ``spetsmat``).  This tool
fetches it over the ssh the owner already has, uses it in memory, and writes the resulting
token straight back the same way.  Nothing sensitive is left in ``~/Downloads`` -- which is what
makes deleting the downloaded copy safe rather than destructive.

    python3 ops/avtorizacia_drive.py                    # narrow scope: drive.file
    python3 ops/avtorizacia_drive.py --obyom polnyj     # wide scope: drive -- only on proof
    python3 ops/avtorizacia_drive.py --proba            # print what would happen, open nothing

SCOPE IS A MEASUREMENT, NOT A GUESS.  The default is the narrow ``drive.file``: the app sees
only files it created itself.  The wide ``drive`` is available behind ``--obyom polnyj`` and is
meant to be reached only after a real API refusal has been recorded -- see item C of this
заход's readiness criterion.  Scope is baked into the consent, so changing it costs the owner a
second run; that is the honest price of measuring instead of grabbing.
"""

# TOOL-CONTRACT: called-by-hand
#
# Same declaration shape as ops/vygruzka_bazy.py and ops/vygruzka_v_tablicu.py.  This one is
# genuinely hand-run and has no unit: it is a one-off that a HUMAN must sit through, because the
# thing it collects is a human's consent.  No timer can ever call it.

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets as secrets_module
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

#: The account that owns the Drive folder and the conduit spreadsheet.  Consent must be his.
PRAVILNYJ_AKKAUNT = "ye.mathclub@gmail.com"

#: The account that owns the Cloud project.  Authorizing as this one is the failure this whole
#: module is shaped against -- it looks like success.
NEPRAVILNYJ_AKKAUNT = "matfak57@gmail.com"

#: Narrow first.  ``drive.file`` limits the app to files it created itself.
SCOPE_UZKIJ = "https://www.googleapis.com/auth/drive.file"

#: Wide.  Reached only on a recorded API refusal, never "just in case".
SCOPE_POLNYJ = "https://www.googleapis.com/auth/drive"

DEFAULT_SERVER = os.environ.get("SPETSMAT_SERVER", "ivan@159.194.254.52")
DEFAULT_CHECKOUT = os.environ.get("SPETSMAT_CHECKOUT", "/opt/spetsmat-bot")

#: Where the two halves live on the server.  Both mode 600, owner ``spetsmat``.
KLIENT_NA_SERVERE = "secrets/oauth_klient.json"
TOKEN_NA_SERVERE = "secrets/oauth_token.json"

SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15"]


class OtkazAvtorizacii(Exception):
    """Consent did not happen, or happened as the wrong account.  Said in words."""


def scope_for(obyom: str) -> str:
    """``--obyom`` -> the scope string.  Pure; the one place the two names are mapped."""
    if obyom == "uzkij":
        return SCOPE_UZKIJ
    if obyom == "polnyj":
        return SCOPE_POLNYJ
    raise ValueError("неизвестный объём прав: %r" % obyom)


def preduprezhdenie(scope: str) -> str:
    """The banner printed BEFORE the browser opens.

    Kept as a pure function so a test can assert that the right account is named and the wrong
    one is named as wrong -- the single most expensive thing this tool can get silently wrong.
    """
    ramka = "=" * 72
    shirokij = " ПОЛНЫЙ (весь Диск)" if scope == SCOPE_POLNYJ else " узкий (только свои файлы)"
    return "\n".join([
        "",
        ramka,
        "",
        "        СЕЙЧАС ОТКРОЕТСЯ GOOGLE.",
        "",
        "        ВЫБЕРИ АККАУНТ:   %s" % PRAVILNYJ_AKKAUNT,
        "        НЕ ВЫБИРАЙ:       %s" % NEPRAVILNYJ_AKKAUNT,
        "",
        ramka,
        "",
        "Папка с архивами и таблица кондуита лежат у %s." % PRAVILNYJ_AKKAUNT,
        "Проект в Google Cloud заведён на %s -- это НЕ тот аккаунт." % NEPRAVILNYJ_AKKAUNT,
        "Авторизуешься не тем -- архивы лягут в чужой Диск, всё будет выглядеть успешным,",
        "и увидит это только тот, кто однажды откроет папку и найдёт её пустой.",
        "",
        "Объём прав:%s" % shirokij,
        "",
        "Google покажет предупреждение «Google не проверил это приложение» -- это ожидаемо",
        "для личного приложения. Путь через:  Дополнительные настройки  ->  Перейти на",
        "страницу «Spetsmat bekap» (небезопасно).",
        "",
        ramka,
        "",
    ])


def build_auth_url(auth_uri: str, client_id: str, redirect_uri: str, scope: str,
                   state: str, code_challenge: str) -> str:
    """The consent URL.  Pure, so the two parameters that matter can be asserted by a test.

    🔴 ``access_type=offline`` and ``prompt=consent`` are both load-bearing and neither is a
    default.  Without ``access_type=offline`` Google issues no refresh token at all; without
    ``prompt=consent`` it issues one only on the FIRST ever consent for this client+account and
    silently omits it on every later run -- so a re-authorization (a scope change, say) would
    return an access token that expires in an hour and nothing that survives the night.
    """
    query = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    })
    return "%s?%s" % (auth_uri, query)


def parse_callback(path: str, state: str) -> str:
    """The ``code`` out of the redirect Google sends back, or a named refusal.

    Pure and total: every way this can go wrong is a sentence, not a traceback, because the
    person reading it is the owner in a terminal, not a developer in a stack trace.
    """
    query = urllib.parse.parse_qs(urllib.parse.urlparse(path).query)
    if query.get("state", [None])[0] != state:
        raise OtkazAvtorizacii(
            "ответ Google не совпал по метке state -- запрос пришёл не от того окна, "
            "которое открыл этот инструмент; ничего не сохранено, запусти заново")
    if "error" in query:
        oshibka = query["error"][0]
        if oshibka == "access_denied":
            raise OtkazAvtorizacii(
                "согласие не выдано (в окне Google нажата «Отмена») -- ничего не сохранено")
        raise OtkazAvtorizacii("Google отказал: %s -- ничего не сохранено" % oshibka)
    code = query.get("code", [None])[0]
    if not code:
        raise OtkazAvtorizacii(
            "Google вернулся без кода согласия -- ничего не сохранено, запусти заново")
    return code


def token_file_payload(client_id: str, client_secret: str, otvet: dict, scope: str) -> dict:
    """The ``authorized_user`` JSON the SERVER's google-auth reads.

    Pure, and the reason it is pure is clause 3 of this tool's own risk: the refresh token is
    the only part of this exchange that cannot be re-obtained without the owner sitting down
    again, so the shape that carries it is asserted by a test rather than eyeballed once.
    """
    refresh = otvet.get("refresh_token")
    if not refresh:
        raise OtkazAvtorizacii(
            "Google не выдал refresh-токен. Обычная причина -- согласие для этой пары "
            "приложение+аккаунт уже выдавалось раньше, а запрос ушёл без prompt=consent. "
            "Этот инструмент его всегда посылает, поэтому проверь другое: приложение должно "
            "быть In production (не Testing) на экране Audience -- в режиме Testing "
            "refresh-токен протухает через семь дней. Ничего не сохранено.")
    return {
        "type": "authorized_user",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh,
        "token_uri": "https://oauth2.googleapis.com/token",
        "scopes": [scope],
    }


def _pkce() -> tuple[str, str]:
    """``(verifier, challenge)``.  PKCE is cheap here and closes the one window in a loopback
    flow where a local process racing for the port could pick up the code."""
    verifier = base64.urlsafe_b64encode(secrets_module.token_bytes(64)).rstrip(b"=").decode()
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


class _Sobiratel(BaseHTTPRequestHandler):
    """Catches the one redirect and says something human in the browser tab."""

    kod: str | None = None
    sboj: str | None = None
    state = ""

    def do_GET(self) -> None:  # noqa: N802  (name fixed by http.server)
        try:
            _Sobiratel.kod = parse_callback(self.path, _Sobiratel.state)
            telo = ("<h2>Готово.</h2><p>Согласие получено. Можно закрыть эту вкладку "
                    "и вернуться в Терминал.</p>")
        except OtkazAvtorizacii as otkaz:
            _Sobiratel.sboj = str(otkaz)
            telo = "<h2>Не вышло.</h2><p>%s</p>" % otkaz
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(("<html><meta charset='utf-8'><body style='font:16px/1.5 "
                          "system-ui;padding:3em'>%s</body></html>" % telo).encode("utf-8"))

    def log_message(self, *_args) -> None:
        """Silence.  The default handler prints the request line -- which carries the consent
        code -- straight to stderr."""


def _ssh_read(server: str, checkout: str, otnositelnyj: str) -> str:
    """Reads one file from the server as ``spetsmat``.  Never echoed anywhere."""
    put = "%s/%s" % (checkout, otnositelnyj)
    gotovo = subprocess.run(
        SSH + [server, "sudo -u spetsmat cat %s" % put],
        capture_output=True, text=True)
    if gotovo.returncode != 0:
        raise OtkazAvtorizacii(
            "не прочитать %s на сервере %s (код %d): %s"
            % (put, server, gotovo.returncode, gotovo.stderr.strip()))
    return gotovo.stdout


def _ssh_write_600(server: str, checkout: str, otnositelnyj: str, soderzhimoe: str) -> None:
    """Writes one file to the server as ``spetsmat``, mode 600, without it ever touching the
    laptop's disk or any command line (it goes over stdin, so it never reaches ``ps``)."""
    put = "%s/%s" % (checkout, otnositelnyj)
    gotovo = subprocess.run(
        SSH + [server, "sudo -u spetsmat sh -c 'umask 077; cat > %s'" % put],
        input=soderzhimoe, capture_output=True, text=True)
    if gotovo.returncode != 0:
        raise OtkazAvtorizacii(
            "не записать %s на сервере %s (код %d): %s"
            % (put, server, gotovo.returncode, gotovo.stderr.strip()))


def _obmen(token_uri: str, client_id: str, client_secret: str, code: str,
           redirect_uri: str, verifier: str) -> dict:
    """Trades the consent code for tokens.  The one network call this tool makes to Google."""
    telo = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "code_verifier": verifier,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }).encode("ascii")
    zapros = urllib.request.Request(
        token_uri, data=telo,
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(zapros, timeout=60) as otvet:
            return json.loads(otvet.read().decode("utf-8"))
    except urllib.error.HTTPError as sboj:
        # 🔴 The body carries Google's own reason and NOT the secret we sent.  Printing it is
        # what turns "invalid_grant" into something the owner can act on.
        raise OtkazAvtorizacii(
            "обмен кода на токен отклонён (HTTP %d): %s -- ничего не сохранено"
            % (sboj.code, sboj.read().decode("utf-8", "replace")[:400]))


def main(argv: list[str] | None = None) -> int:
    """Returns an exit code, ALWAYS -- see ops/vygruzka_v_tablicu.py for why that is stated
    rather than assumed in this codebase."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--obyom", choices=["uzkij", "polnyj"], default="uzkij",
                        help="объём прав: uzkij -- drive.file (по умолчанию), polnyj -- drive")
    parser.add_argument("--server", default=DEFAULT_SERVER, help="куда класть токен")
    parser.add_argument("--checkout", default=DEFAULT_CHECKOUT, help="путь к чекауту на сервере")
    parser.add_argument("--klient", type=Path, default=None,
                        help="локальный файл клиента вместо чтения с сервера")
    parser.add_argument("--kuda", type=Path, default=None,
                        help="записать токен в локальный файл вместо сервера (для проверки)")
    parser.add_argument("--proba", action="store_true",
                        help="напечатать, что будет сделано, и выйти -- браузер не открывать")
    arguments = parser.parse_args(argv)

    scope = scope_for(arguments.obyom)

    try:
        if arguments.klient is not None:
            syroj = arguments.klient.read_text(encoding="utf-8")
        else:
            syroj = _ssh_read(arguments.server, arguments.checkout, KLIENT_NA_SERVERE)
        klient = json.loads(syroj)["installed"]
    except OtkazAvtorizacii as otkaz:
        print(otkaz, file=sys.stderr)
        return 5
    except (KeyError, ValueError) as sboj:
        print("файл клиента не похож на ключ типа Desktop app: %s" % sboj, file=sys.stderr)
        return 5

    if arguments.proba:
        print(preduprezhdenie(scope))
        print("ПРОБА: браузер не открыт, ничего не записано.")
        print("объём прав: %s" % scope)
        print("токен лёг бы в %s:%s/%s"
              % (arguments.server, arguments.checkout, TOKEN_NA_SERVERE))
        return 0

    server = HTTPServer(("127.0.0.1", 0), _Sobiratel)
    redirect_uri = "http://localhost:%d" % server.server_port
    verifier, challenge = _pkce()
    state = secrets_module.token_urlsafe(24)
    _Sobiratel.state = state
    _Sobiratel.kod = None
    _Sobiratel.sboj = None

    url = build_auth_url(klient["auth_uri"], klient["client_id"], redirect_uri,
                         scope, state, challenge)

    print(preduprezhdenie(scope))
    print("Если браузер не открылся сам -- открой эту ссылку вручную:\n\n%s\n" % url)
    sys.stdout.flush()
    webbrowser.open(url)

    print("жду согласия в браузере...")
    server.handle_request()
    server.server_close()

    if _Sobiratel.sboj:
        print(_Sobiratel.sboj, file=sys.stderr)
        return 4
    if not _Sobiratel.kod:
        print("согласие не получено -- ничего не сохранено", file=sys.stderr)
        return 4

    try:
        otvet = _obmen(klient["token_uri"], klient["client_id"], klient["client_secret"],
                       _Sobiratel.kod, redirect_uri, verifier)
        payload = token_file_payload(klient["client_id"], klient["client_secret"], otvet, scope)
    except OtkazAvtorizacii as otkaz:
        print(otkaz, file=sys.stderr)
        return 4

    # 🔴 NEVER PRINT ``payload`` OR ANY PART OF IT.  It carries the refresh token, which is the
    # single most durable secret this deployment has: it does not expire, and it is the whole
    # reason the nightly timer can run unattended.  What gets printed is that it was written
    # and where -- never what.
    telo = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    try:
        if arguments.kuda is not None:
            arguments.kuda.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(str(arguments.kuda), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as fajl:
                fajl.write(telo)
            kuda = str(arguments.kuda)
        else:
            _ssh_write_600(arguments.server, arguments.checkout, TOKEN_NA_SERVERE, telo)
            kuda = "%s:%s/%s" % (arguments.server, arguments.checkout, TOKEN_NA_SERVERE)
    except OtkazAvtorizacii as otkaz:
        print(otkaz, file=sys.stderr)
        return 5

    print("\nсогласие получено; refresh-токен записан в %s (права 600)" % kuda)
    print("объём прав: %s" % scope)
    print("\nЧья это учётка -- проверит сам инструмент выгрузки; на слово здесь не верят:")
    print("    sudo -u spetsmat python3 ops/vygruzka_bazy.py --proverit-dostup")
    return 0


if __name__ == "__main__":
    sys.exit(main())
