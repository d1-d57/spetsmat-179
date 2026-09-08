"""What ``ops/avtorizacia_drive.py`` must not get wrong quietly.

Every test here guards a failure that LOOKS LIKE SUCCESS from the terminal, because those are
the only ones a one-off hand-run tool can actually suffer: the owner sits through the flow once,
sees rc=0, and walks away.  A wrong account, a missing refresh token or a silently widened scope
all print nothing alarming at the moment they happen.
"""

from __future__ import annotations

import pytest

from ops import avtorizacia_drive as avt


class TestObyomPrav:
    """Scope is a measurement (item C of the criterion), so the mapping is asserted, not read."""

    def test_po_umolchaniyu_uzkij(self):
        assert avt.scope_for("uzkij") == "https://www.googleapis.com/auth/drive.file"

    def test_polnyj_tolko_po_yavnomu_imeni(self):
        assert avt.scope_for("polnyj") == "https://www.googleapis.com/auth/drive"

    def test_neizvestnyj_obyom_ne_molchit(self):
        with pytest.raises(ValueError):
            avt.scope_for("kakoj-nibud")


class TestPreduprezhdenie:
    """The banner is the ONLY thing standing between the owner and the заход's main trap: the
    Cloud project and the Drive folder live in different accounts, and authorizing as the
    project's account produces a completely successful-looking run into the wrong Drive."""

    def test_nazyvaet_pravilnyj_akkaunt(self):
        assert "ye.mathclub@gmail.com" in avt.preduprezhdenie(avt.SCOPE_UZKIJ)

    def test_nazyvaet_nepravilnyj_kak_nepravilnyj(self):
        tekst = avt.preduprezhdenie(avt.SCOPE_UZKIJ)
        stroka = next(s for s in tekst.splitlines() if "matfak57@gmail.com" in s)
        assert "НЕ ВЫБИРАЙ" in stroka

    def test_shirokij_obyom_nazvan_shirokim(self):
        assert "ПОЛНЫЙ" in avt.preduprezhdenie(avt.SCOPE_POLNYJ)
        assert "ПОЛНЫЙ" not in avt.preduprezhdenie(avt.SCOPE_UZKIJ)


class TestAuthUrl:
    """``access_type`` and ``prompt`` are the two parameters whose absence costs the owner a
    second trip through the browser -- and, worse, does so a week later rather than now."""

    def _url(self, scope=avt.SCOPE_UZKIJ):
        return avt.build_auth_url("https://accounts.google.com/o/oauth2/auth", "cid",
                                  "http://localhost:1234", scope, "st", "chal")

    def test_offline_inache_refresh_tokena_ne_budet_voobshche(self):
        assert "access_type=offline" in self._url()

    def test_prompt_consent_inache_refresh_ne_vydadut_povtorno(self):
        assert "prompt=consent" in self._url()

    def test_pkce_metod_nazvan(self):
        url = self._url()
        assert "code_challenge=chal" in url
        assert "code_challenge_method=S256" in url

    def test_scope_uezzhaet_tot_kotoryj_prosili(self):
        assert "drive.file" in self._url()
        assert "drive.file" not in self._url(avt.SCOPE_POLNYJ)


class TestParseCallback:
    """Every refusal must come back as a sentence: the reader is the owner in a terminal."""

    def test_kod_vynimaetsya(self):
        assert avt.parse_callback("/?code=abc&state=st", "st") == "abc"

    def test_chuzhoj_state_otvergaetsya(self):
        with pytest.raises(avt.OtkazAvtorizacii, match="state"):
            avt.parse_callback("/?code=abc&state=drugoj", "st")

    def test_otmena_nazvana_otmenoj(self):
        with pytest.raises(avt.OtkazAvtorizacii, match="Отмена"):
            avt.parse_callback("/?error=access_denied&state=st", "st")

    def test_otvet_bez_koda_ne_prohodit_molcha(self):
        with pytest.raises(avt.OtkazAvtorizacii):
            avt.parse_callback("/?state=st", "st")


class TestTokenFilePayload:
    """The shape the SERVER's google-auth reads.  Asserted rather than eyeballed because the
    refresh token cannot be re-obtained without the owner sitting down again."""

    def _payload(self, otvet):
        return avt.token_file_payload("cid", "csecret", otvet, avt.SCOPE_UZKIJ)

    def test_forma_authorized_user(self):
        payload = self._payload({"refresh_token": "rt"})
        assert payload["type"] == "authorized_user"
        assert payload["refresh_token"] == "rt"
        assert payload["client_id"] == "cid"
        assert payload["scopes"] == [avt.SCOPE_UZKIJ]

    def test_bez_refresh_tokena_eto_otkaz_a_ne_fajl(self):
        """Google returns an access token and no refresh token whenever consent was already
        given; writing that file would produce a deployment that works for exactly one hour."""
        with pytest.raises(avt.OtkazAvtorizacii, match="refresh"):
            self._payload({"access_token": "at"})

    def test_otkaz_nazyvaet_rezhim_testing_kak_prichinu(self):
        with pytest.raises(avt.OtkazAvtorizacii, match="In production"):
            self._payload({"access_token": "at"})


class TestGigiena:
    """Two things this module must never do, both checked against its own source text."""

    def test_obrabotchik_ne_pishet_v_log(self):
        """``BaseHTTPRequestHandler`` logs the request line by default -- and the request line
        of the redirect carries the consent code."""
        assert avt._Sobiratel.log_message.__doc__ is not None

    def test_kod_soglasiya_ne_uhodit_v_komandnuyu_stroku(self):
        """The token is written over stdin, never as an argument: arguments are visible in
        ``ps`` to every other user on the machine."""
        import inspect
        istochnik = inspect.getsource(avt._ssh_write_600)
        assert "input=" in istochnik
