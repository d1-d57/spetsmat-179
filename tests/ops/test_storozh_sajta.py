"""Tests for ops/storozh_sajta.py: five outcomes, and the one distinction that matters.

The distinction the whole module exists for is "сайт лёг" vs "443 отфильтрован".  Two of the
tests below drive it end to end against real local sockets; the rest of the truth table is
pinned on ``postavit_diagnoz`` directly, because standing up a trusted TLS server inside a
unit test would prove the certificate machinery rather than the diagnosis.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from ops import opoveshchenie, storozh_sajta
from ops.storozh_sajta import OneCheck, postavit_diagnoz


NASH_OTVET = ("<!doctype html><title>Занятие четверг, 10 сентября — распределение</title>"
              "<h1>Распределение</h1>").encode("utf-8")


class NashSajtHandler(BaseHTTPRequestHandler):
    """Serves our real marker, in the lower case the live page actually uses."""

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(NASH_OTVET)

    def log_message(self, *a, **k):
        pass


class BannerHandler(BaseHTTPRequestHandler):
    """200, but somebody else's page standing where the site should be."""

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"console.serveo.net")

    def log_message(self, *a, **k):
        pass


class ErrorHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(500)
        self.end_headers()
        self.wfile.write(b"error")

    def log_message(self, *a, **k):
        pass


def _serve(handler):
    """Порт выдаёт ядро (0 = любой свободный), а не мы.

    Зашитые номера портов уже уронили этот файл с «Address already in use», когда рядом
    шёл другой прогон: тест краснел не от кода, а от соседа.
    """
    srv = HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def _svobodnyj_port() -> int:
    """Порт, на котором ГАРАНТИРОВАННО никто не слушает — для случая «молчат оба»."""
    import socket as _s
    with _s.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _nastroit(tmp_path, monkeypatch, host: str):
    monkeypatch.setattr(storozh_sajta, "HOST_FILE", tmp_path / "adres-sajta.txt")
    monkeypatch.setattr(storozh_sajta, "ADRES_FILE", tmp_path / "adres.txt")
    monkeypatch.setattr(storozh_sajta, "STATE_FILE", tmp_path / "state.json")
    (tmp_path / "adres-sajta.txt").write_text(host, encoding="utf-8")


def _sostoyanie(tmp_path) -> str:
    return json.loads((tmp_path / "state.json").read_text(encoding="utf-8")).get("last_verdict", "")


# ── Та самая пара, ради которой сторож переписан ──────────────────────────────

def test_443_otfiltrovan_kogda_http_zhiv_a_https_molchit(tmp_path, monkeypatch, capsys):
    """HTTP отдаёт наше содержимое, HTTPS не отвечает вовсе — это НЕ «сайт лёг».

    Недоступность 443 подделана честнейшим доступным способом: на порту стоит обычный
    HTTP-сервер, и попытка говорить с ним по TLS обрывается на уровне сети, ровно как
    при фильтрации на пути. Именно этот признак — http жив, https молчит — сторож и обязан
    отличать от смерти сайта, потому что действия у них противоположные.
    """
    srv, port = _serve(NashSajtHandler)
    try:
        _nastroit(tmp_path, monkeypatch, "localhost:%d" % port)
        code = storozh_sajta.main([])
        vyvod = capsys.readouterr().out
        assert code == 1
        assert _sostoyanie(tmp_path) == storozh_sajta.OTFILTROVAN
        assert "443 ОТФИЛЬТРОВАН" in vyvod
        # Действие обязано быть напечатано, и обязано быть «сервер не трогать»:
        # без него сторож посылает читателя чинить единственное, что не сломано.
        assert "СЕРВЕР НЕ ТРОГАТЬ" in vyvod
    finally:
        srv.shutdown()
        srv.server_close()


def test_mertv_kogda_molchat_oba(tmp_path, monkeypatch, capsys):
    """Ни один порт не отвечает — сайт лёг, и вот это уже «поднимать сервер»."""
    _nastroit(tmp_path, monkeypatch, "localhost:%d" % _svobodnyj_port())
    code = storozh_sajta.main([])
    vyvod = capsys.readouterr().out
    assert code == 1
    assert _sostoyanie(tmp_path) == storozh_sajta.MERTV
    assert "поднимать сайт" in vyvod


# ── Полная таблица диагноза ───────────────────────────────────────────────────

def _zhiv(name):
    return OneCheck(name, True, True, "жив")


def _molchit(name):
    return OneCheck(name, False, False, "молчит на уровне сети")


def _otvetil_ploho(name):
    return OneCheck(name, False, True, "мёртв: status=502")


def test_tablica_diagnoza():
    assert postavit_diagnoz(_zhiv("http"), _zhiv("https")) == storozh_sajta.ZHIV
    assert postavit_diagnoz(_zhiv("http"), _molchit("https")) == storozh_sajta.OTFILTROVAN
    assert postavit_diagnoz(_molchit("http"), _zhiv("https")) == storozh_sajta.HTTP_LEG
    assert postavit_diagnoz(_molchit("http"), _molchit("https")) == storozh_sajta.MERTV


def test_502_po_https_eto_ne_filtracia():
    """Сервер ОТВЕТИЛ пятисоткой — значит 443 доходит, и фильтрацией это назвать нельзя.

    Граница узкая нарочно: стоит записать сюда любую неудачу https, и слово
    «отфильтрован» перестанет что-либо значить.
    """
    assert postavit_diagnoz(_zhiv("http"), _otvetil_ploho("https")) == storozh_sajta.MERTV


# ── Остальные исходы ──────────────────────────────────────────────────────────

def test_zhiv_na_zhivom_portu(tmp_path, monkeypatch):
    """Наш маркер в СТРОЧНОМ виде — как на живой странице — обязан читаться как «жив».

    До 07.09 сверка была регистрозависимой и по первым 512 байтам; живой сайт, отдающий
    200 и заголовок «… — распределение», сторож объявлял мёртвым.
    """
    srv, port = _serve(NashSajtHandler)
    try:
        _nastroit(tmp_path, monkeypatch, "localhost:%d" % port)
        proverka = storozh_sajta.probe("http://localhost:%d" % port)
        assert proverka.passed
        assert proverka.otvetil_seteviy
    finally:
        srv.shutdown()
        srv.server_close()


def test_banner_ne_schitaetsya_zhivym(tmp_path, monkeypatch):
    """200 без нашего содержимого — чужая страница на нашем месте, а не живой сайт."""
    srv, port = _serve(BannerHandler)
    try:
        proverka = storozh_sajta.probe("http://localhost:%d" % port)
        assert not proverka.passed
        assert proverka.otvetil_seteviy  # сеть-то дошла
    finally:
        srv.shutdown()
        srv.server_close()


def test_500_eto_otvet_a_ne_tishina(tmp_path, monkeypatch):
    srv, port = _serve(ErrorHandler)
    try:
        proverka = storozh_sajta.probe("http://localhost:%d" % port)
        assert not proverka.passed
        assert proverka.otvetil_seteviy
    finally:
        srv.shutdown()
        srv.server_close()


def test_ne_smog_proverit_kogda_adresa_net(tmp_path, monkeypatch):
    monkeypatch.setattr(storozh_sajta, "HOST_FILE", tmp_path / "net.txt")
    monkeypatch.setattr(storozh_sajta, "ADRES_FILE", tmp_path / "tozhe-net.txt")
    monkeypatch.setattr(storozh_sajta, "STATE_FILE", tmp_path / "state.json")
    code = storozh_sajta.main([])
    assert code == 1
    assert _sostoyanie(tmp_path) == storozh_sajta.NE_SMOG


def test_staryj_adres_ostayotsya_zapasnym(tmp_path, monkeypatch):
    """ADRES.txt эпохи туннеля несёт ПОЛНЫЙ url — он обязан сводиться к тому же хосту."""
    monkeypatch.setattr(storozh_sajta, "HOST_FILE", tmp_path / "net.txt")
    monkeypatch.setattr(storozh_sajta, "ADRES_FILE", tmp_path / "adres.txt")
    (tmp_path / "adres.txt").write_text("https://288c65b4b43b89.lhr.life/", encoding="utf-8")
    assert storozh_sajta.read_host() == "288c65b4b43b89.lhr.life"


# ── Тревога только на смене состояния ─────────────────────────────────────────

def test_trevoga_na_smene_sostoyania(tmp_path, monkeypatch, capsys):
    _nastroit(tmp_path, monkeypatch, "localhost:%d" % _svobodnyj_port())
    (tmp_path / "state.json").write_text(json.dumps({"last_verdict": "жив"}), encoding="utf-8")
    code = storozh_sajta.main([])
    vyvod = capsys.readouterr().out
    assert code == 1
    assert "ALARM: жив -> мёртв" in vyvod
    assert _sostoyanie(tmp_path) == storozh_sajta.MERTV


def test_tiho_gasit_trevogu(tmp_path, monkeypatch, capsys):
    _nastroit(tmp_path, monkeypatch, "localhost:%d" % _svobodnyj_port())
    (tmp_path / "state.json").write_text(json.dumps({"last_verdict": "жив"}), encoding="utf-8")
    code = storozh_sajta.main(["--tiho"])
    vyvod = capsys.readouterr().out
    assert code == 1
    assert "ALARM:" not in vyvod


# ── Первый запуск больше не молчит (только когда сайт жив: OnFailure= уже кроет нездоровый) ──

def test_pervyj_zdorovyj_zapusk_shlyot_puls(tmp_path, monkeypatch):
    """Без сохранённого состояния сравнивать не с чем — а «жив» никогда не даёт rc≠0,
    так что `OnFailure=` для этого случая не сработает никогда. Без прямой отправки здесь
    исправно работающий сторож мог бы всю жизнь молчать о том, что вообще существует."""
    _nastroit(tmp_path, monkeypatch, "localhost:1")
    monkeypatch.setattr(storozh_sajta, "probe",
                        lambda url: OneCheck(url.split("://")[0], True, True, "жив: status=200"))
    otpravleno = {}
    monkeypatch.setattr(opoveshchenie, "send",
                        lambda text, kind="trevoga", **kw: otpravleno.update(text=text, kind=kind))
    code = storozh_sajta.main([])
    assert code == 0
    assert otpravleno["kind"] == "puls"
    assert "впервые" in otpravleno["text"] and storozh_sajta.ZHIV in otpravleno["text"]
    assert _sostoyanie(tmp_path) == storozh_sajta.ZHIV


def test_pervyj_zdorovyj_zapusk_perezhivaet_sboj_otpravki(tmp_path, monkeypatch, capsys):
    """Пульс не смог уйти (сеть/токен) — сторож обязан отработать и отчитаться, а не упасть."""
    _nastroit(tmp_path, monkeypatch, "localhost:1")
    monkeypatch.setattr(storozh_sajta, "probe",
                        lambda url: OneCheck(url.split("://")[0], True, True, "жив: status=200"))

    def padaet(*a, **k):
        raise opoveshchenie.RefusedToSend("нет токена")
    monkeypatch.setattr(opoveshchenie, "send", padaet)
    code = storozh_sajta.main([])
    vyvod = capsys.readouterr().out
    assert code == 0
    assert "heartbeat FAILED" in vyvod
    assert _sostoyanie(tmp_path) == storozh_sajta.ZHIV


def test_pervyj_nezdorovyj_zapusk_ne_shlyot_svoj_puls(tmp_path, monkeypatch):
    """Нездоровый первый запуск не дублирует сообщение: OnFailure= уже пришлёт тревогу сам."""
    _nastroit(tmp_path, monkeypatch, "localhost:%d" % _svobodnyj_port())
    zvali = []
    monkeypatch.setattr(opoveshchenie, "send", lambda *a, **k: zvali.append((a, k)))
    code = storozh_sajta.main([])
    assert code == 1
    assert zvali == []


# ── Третья беда: TLS дошёл, но сертификату верить нельзя ──────────────────────

def test_prosrochennyj_sertifikat_eto_ne_filtracia(monkeypatch):
    """Провал проверки сертификата ДОКАЗЫВАЕТ, что 443 доходит, а не опровергает это.

    Рукопожатие зашло достаточно далеко, чтобы сервер предъявил сертификат; фильтрация на
    пути такого не допускает. Без этой ветки сторож на просроченном сертификате печатал бы
    «СЕРВЕР НЕ ТРОГАТЬ, вопрос к провайдеру» — то есть самое вредное из возможных действий
    ровно тогда, когда чинить надо именно сервер. Найдено верификатором захода на живом
    expired.badssl.com; текущий сертификат годен до 05.12.2026.
    """
    import ssl as _ssl

    def upal(*a, **k):
        raise _ssl.SSLCertVerificationError(1, "[SSL: CERTIFICATE_VERIFY_FAILED] certificate has expired")

    monkeypatch.setattr(storozh_sajta.urllib.request, "urlopen", upal)
    proverka = storozh_sajta.probe("https://math-kluychiki.ru")
    assert not proverka.passed
    assert proverka.sertifikat_krasnyj
    # Вот это поле и решает: сеть ДОШЛА.
    assert proverka.otvetil_seteviy
    assert postavit_diagnoz(_zhiv("http"), proverka) == storozh_sajta.SERTIFIKAT


def test_dejstvie_po_sertifikatu_shlyot_na_server_a_ne_k_provajderu():
    dejstvie = storozh_sajta.DEJSTVIE[storozh_sajta.SERTIFIKAT]
    assert "certbot renew" in dejstvie
    assert "не фильтрация" in dejstvie


def test_rukopozhatie_bez_sertifikata_ostayotsya_molchaniem(monkeypatch):
    """А вот обычный обрыв TLS — по-прежнему молчание сети и по-прежнему фильтрация.

    Граница между двумя ветками проходит по тому, предъявил ли сервер сертификат, и её
    надо держать: стоит записать в «сертификат» любую ошибку TLS, и ветка фильтрации
    опустеет.
    """
    import ssl as _ssl

    def upal(*a, **k):
        raise _ssl.SSLError(1, "[SSL: WRONG_VERSION_NUMBER] wrong version number")

    monkeypatch.setattr(storozh_sajta.urllib.request, "urlopen", upal)
    proverka = storozh_sajta.probe("https://math-kluychiki.ru")
    assert not proverka.sertifikat_krasnyj
    assert not proverka.otvetil_seteviy
    assert postavit_diagnoz(_zhiv("http"), proverka) == storozh_sajta.OTFILTROVAN
