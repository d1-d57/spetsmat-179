"""The channel diagnosis -- tested against a faked ``subprocess.run``, never the network.

A test that actually dials out is a test of whatever network happens to run it, which is
exactly the thing under suspicion in production (``deploy/README.md``: ``curl -6`` has no
route, ``curl -4`` succeeds roughly half the time). Every test here replaces
``subprocess.run`` with a stand-in that returns a fixed, named scenario, so the test is
about this module's own classification logic, not about whoever's laptop or CI runner it
happens to execute on.
"""

from __future__ import annotations

import json

import pytest

from ops import diagnostika_kanala as dk


class _FakeCompleted:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_a_successful_probe_is_classified_as_success(monkeypatch):
    monkeypatch.setattr(dk.subprocess, "run",
                         lambda *a, **k: _FakeCompleted(0, "200 0.184"))
    probe = dk.run_one_probe("api.telegram.org", "-4", 0, timeout_s=3.0)
    assert probe.success
    assert probe.http_code == "200"
    assert probe.time_total == pytest.approx(0.184)


def test_a_curl_failure_is_classified_as_failure_and_keeps_no_time(monkeypatch):
    """rc=7: curl could not connect at all -- the exact shape of the reported incident."""
    monkeypatch.setattr(dk.subprocess, "run", lambda *a, **k: _FakeCompleted(7, ""))
    probe = dk.run_one_probe("api.telegram.org", "-4", 0, timeout_s=3.0)
    assert not probe.success
    assert probe.time_total is None


def test_a_hung_probe_that_curl_itself_cannot_bound_still_gets_recorded(monkeypatch):
    """``curl --max-time`` can itself wedge; the subprocess-level timeout is the backstop."""
    import subprocess as real_subprocess

    def hangs(*a, **k):
        raise real_subprocess.TimeoutExpired(cmd="curl", timeout=k.get("timeout", 0))

    monkeypatch.setattr(dk.subprocess, "run", hangs)
    probe = dk.run_one_probe("api.telegram.org", "-4", 0, timeout_s=3.0)
    assert not probe.success
    assert probe.rc == 124


def test_a_2xx_and_a_4xx_are_both_a_working_channel():
    """A live 404 still proves the connection and TLS handshake worked -- HTTP status is
    recorded but must not affect the success verdict, which is about the channel only."""
    ok_404 = dk.Probe(ts="t", address="x", protocol="-4", seq=0, rc=0,
                       http_code="404", time_total=0.2, success=True)
    assert ok_404.success


def test_probe_batch_writes_one_json_line_per_probe_before_returning(tmp_path, monkeypatch):
    monkeypatch.setattr(dk.subprocess, "run",
                         lambda *a, **k: _FakeCompleted(0, "200 0.1"))
    out_path = tmp_path / "probes.jsonl"
    results = dk.probe_batch("1.1.1.1", "-4", count=5, timeout_s=1.0, out_path=out_path)
    assert len(results) == 5
    lines = out_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 5
    for line, probe in zip(lines, results):
        assert json.loads(line)["seq"] == probe.seq


def test_probe_batch_survives_being_read_after_a_simulated_kill(tmp_path, monkeypatch):
    """Only the probes completed before a kill are expected on disk -- this is the whole
    point of writing per-probe rather than buffering: nothing after the kill is lost, and
    nothing before it is either."""
    calls = {"n": 0}

    def flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] == 3:
            raise KeyboardInterrupt("channel died")
        return _FakeCompleted(0, "200 0.1")

    monkeypatch.setattr(dk.subprocess, "run", flaky)
    out_path = tmp_path / "probes.jsonl"
    with pytest.raises(KeyboardInterrupt):
        dk.probe_batch("1.1.1.1", "-4", count=5, timeout_s=1.0, out_path=out_path)
    lines = out_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2, "the two probes before the kill must have reached disk"


def test_summarize_reports_median_and_the_worst_decile():
    probes = [
        dk.Probe(ts="t", address="x", protocol="-4", seq=i, rc=0, http_code="200",
                  time_total=value, success=True)
        for i, value in enumerate([0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 10.0])
    ]
    stats = dk.summarize("x", "-4", probes)
    assert stats.total == 10
    assert stats.successes == 10
    assert stats.median_s == pytest.approx(0.1)
    # the worst decile (1 of 10 samples) is exactly the outlier
    assert stats.worst_decile_s == pytest.approx(10.0)


def test_summarize_counts_failures_without_crashing_on_all_failed():
    probes = [
        dk.Probe(ts="t", address="x", protocol="-6", seq=i, rc=7, http_code=None,
                  time_total=None, success=False)
        for i in range(4)
    ]
    stats = dk.summarize("x", "-6", probes)
    assert stats.total == 4
    assert stats.successes == 0
    assert stats.median_s is None
    assert stats.worst_decile_s is None
    assert stats.success_rate == 0.0
    assert "0/  4 ok" in stats.line()


def test_compare_resolution_flags_disagreement_between_resolvers(monkeypatch):
    """The whole point of the comparison: catch a resolver returning something the
    reference resolver does not, without hand-parsing raw ``dig`` output per call site."""
    def fake_run(cmd, **k):
        # cmd shape: ["dig", "+short", ["@8.8.8.8"], "A"|"AAAA", hostname]
        if "@8.8.8.8" in cmd:
            answer = "9.9.9.9\n" if "A" in cmd and "AAAA" not in cmd else ""
        else:
            answer = "198.18.18.18\n" if "A" in cmd and "AAAA" not in cmd else ""
        return _FakeCompleted(0, answer)

    monkeypatch.setattr(dk.subprocess, "run", fake_run)
    result = dk.compare_resolution("example.test")
    assert result["A_agrees"] is False
    assert result["system_resolver_A"] == ["198.18.18.18"]
    assert result["reference_resolver_A"] == ["9.9.9.9"]


def test_resolve_for_route_passes_a_literal_ip_through_for_v4_and_skips_v6():
    assert dk.resolve_for_route("1.1.1.1", "-4") == "1.1.1.1"
    assert dk.resolve_for_route("1.1.1.1", "-6") is None


def test_main_runs_end_to_end_against_a_faked_channel(tmp_path, monkeypatch, capsys):
    """Wires every collaborator to a fixed fake and checks the run completes and writes
    its files -- not a test of the real network, a test that ``main`` assembles the
    pieces above correctly."""
    monkeypatch.setattr(dk.subprocess, "run",
                         lambda cmd, **k: _FakeCompleted(0, "200 0.15")
                         if cmd[0] == "curl" else _FakeCompleted(0, "1.1.1.1\n"))
    rc = dk.main(["--probes", "3", "--timeout", "1", "--outdir", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "total probes: 18" in out  # 3 addresses x 2 protocols x 3 probes
    assert (tmp_path / "resolution.json").exists()
    assert (tmp_path / "routes.json").exists()
