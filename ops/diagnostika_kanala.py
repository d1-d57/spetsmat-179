"""The channel diagnosis: numbers, not guesses, about the server's OUTBOUND network.

WHY THIS EXISTS
----------------
The server (``deploy/README.md``) has an unstable outbound channel: three separate
incidents already traced back to it (the bot dying, alerts not arriving, one false alarm
from the watchdog). Manual spot checks on 2026-09-08 found ``curl -6`` leaving with no
route at all, ``curl -4`` succeeding roughly one time in two or three, and the system
resolver (``/etc/resolv.conf``) pointing at ``198.18.18.18`` -- an address from the block
RFC 2544 reserves for network-equipment benchmarking, not a public resolver. This module
turns those spot checks into a repeatable measurement with enough samples to be a number,
not an impression, so the owner can hand a hoster a ticket that says what is broken and
how often, instead of "it feels flaky".

WHAT IS MEASURED, AND WHY EACH PIECE
-------------------------------------
Three independent addresses (``api.telegram.org``, ``openrouter.ai``, ``1.1.1.1``) under
two protocols (``-4``, ``-6``) each get a batch of probes: an HTTPS request timed by
``curl`` itself, which already does the DNS lookup + TCP connect + TLS handshake this
channel keeps failing at. ``1.1.1.1`` is a literal address on purpose -- it is the one
target in the batch whose probe involves no DNS resolution at all, so it separates "the
network path is bad" from "the resolver is bad".

Resolution is compared separately, once per hostname: what the system resolver
(``/etc/resolv.conf``) returns versus what a direct query to ``8.8.8.8`` returns for the
same name. A difference between the two is the resolver under suspicion; agreement rules
it out as a cause, which is itself useful to know before writing to the hoster.

The first hop is approximated with ``ip route get`` rather than a real traceroute:
``traceroute`` is not installed on this server and this module does not install packages
on a production machine it was asked only to measure (``## СТОП ДО ЦЕЛИ`` in the entry
file). ``ip route get`` reports the kernel's own routing decision -- interface and
next-hop gateway -- which is a legitimate, if weaker, proxy: it says how a packet would
leave, not how far it actually got. That weakness is printed alongside the number, not
hidden.

WHY EACH PROBE IS WRITTEN TO DISK AS IT HAPPENS
-------------------------------------------------
The process doing the measuring runs over the same channel it is measuring. A run that
buffers results in memory and writes them out at the end loses everything if the channel
(or the SSH session carrying this script) dies partway through -- which, given the
failure being investigated, is not a hypothetical. Each probe is appended to its JSONL
file and ``fsync``-ed before the next one starts, so a killed run still leaves every
sample it completed.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

#: The three independent targets. ``1.1.1.1`` is a literal address -- it is the control
#: that involves no DNS resolution, isolating "network path" from "resolver" failures.
ADDRESSES = ("api.telegram.org", "openrouter.ai", "1.1.1.1")

PROTOCOLS = ("-4", "-6")

DEFAULT_PROBES = 100
#: Chosen against the 2026-09-08 spot check: a successful request answered in well under
#: a second, so 3s gives a real connection ample room while keeping a failing one from
#: costing more than 3s of wall time -- 600+ probes at a worse timeout do not finish.
DEFAULT_TIMEOUT_S = 3.0

#: Public resolver queried directly, bypassing the system's ``/etc/resolv.conf``, to
#: compare against what the system resolver hands back for the same name.
REFERENCE_RESOLVER = "8.8.8.8"


@dataclass(frozen=True)
class Probe:
    ts: str
    address: str
    protocol: str
    seq: int
    rc: int
    http_code: str | None
    time_total: float | None
    success: bool

    def to_json(self) -> str:
        return json.dumps(self.__dict__, ensure_ascii=False)


def run_one_probe(address: str, protocol: str, seq: int, timeout_s: float) -> Probe:
    """One HTTPS request through ``curl``, timed and classified by ``curl`` itself.

    ``-k`` skips certificate verification: probing ``1.1.1.1`` by literal address makes
    the hostname in Cloudflare's certificate not match, which is a cert-shape mismatch,
    not a channel failure, and must not be counted as one. Success here means the
    connection and TLS handshake completed (``rc == 0``); the HTTP status itself is
    recorded but does not affect success -- a live 4xx still proves the channel works.
    """
    cmd = [
        "curl", protocol, "-sk", "-o", "/dev/null",
        "--max-time", str(timeout_s),
        "-w", "%{http_code} %{time_total}",
        "https://%s/" % address,
    ]
    try:
        completed = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout_s + 5,
        )
        rc = completed.returncode
        out = completed.stdout.strip()
    except subprocess.TimeoutExpired:
        rc = 124
        out = ""

    http_code, _, time_total_text = out.partition(" ")
    time_total = float(time_total_text) if time_total_text else None
    return Probe(
        ts=datetime.now(timezone.utc).isoformat(),
        address=address, protocol=protocol, seq=seq,
        rc=rc, http_code=http_code or None,
        time_total=time_total,
        success=(rc == 0),
    )


def probe_batch(address: str, protocol: str, count: int, timeout_s: float,
                 out_path: Path) -> list[Probe]:
    """Run ``count`` probes for one (address, protocol) pair, writing each as it lands."""
    results: list[Probe] = []
    with open(out_path, "a", encoding="utf-8") as fh:
        for seq in range(count):
            probe = run_one_probe(address, protocol, seq, timeout_s)
            fh.write(probe.to_json() + "\n")
            fh.flush()
            os.fsync(fh.fileno())
            results.append(probe)
    return results


@dataclass(frozen=True)
class BatchStats:
    address: str
    protocol: str
    total: int
    successes: int
    median_s: float | None
    worst_decile_s: float | None

    @property
    def success_rate(self) -> float:
        return self.successes / self.total if self.total else 0.0

    def line(self) -> str:
        med = "%.3f" % self.median_s if self.median_s is not None else "n/a"
        worst = "%.3f" % self.worst_decile_s if self.worst_decile_s is not None else "n/a"
        return "  %-18s %-3s  %3d/%3d ok (%5.1f%%)  median=%ss  worst-10%%=%ss" % (
            self.address, self.protocol, self.successes, self.total,
            100 * self.success_rate, med, worst,
        )


def summarize(address: str, protocol: str, probes: list[Probe]) -> BatchStats:
    times = sorted(p.time_total for p in probes if p.success and p.time_total is not None)
    if not times:
        return BatchStats(address, protocol, len(probes), 0, None, None)
    median_s = statistics.median(times)
    #: "worst 10%" = the mean of the slowest decile; a single slowest sample is noise,
    #: the slowest tenth is a shape.
    decile_start = max(0, len(times) - max(1, round(len(times) * 0.1)))
    worst_decile_s = statistics.mean(times[decile_start:])
    return BatchStats(address, protocol, len(probes),
                       sum(1 for p in probes if p.success), median_s, worst_decile_s)


def _run(cmd: list[str], timeout_s: float = 10.0) -> tuple[int, str]:
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
        return completed.returncode, (completed.stdout or completed.stderr or "").strip()
    except (OSError, subprocess.SubprocessError) as failure:
        return -1, str(failure)


def compare_resolution(hostname: str) -> dict:
    """What the system resolver returns for ``hostname`` versus a direct query to
    :data:`REFERENCE_RESOLVER`, for A and AAAA separately."""
    system_a = _run(["dig", "+short", "A", hostname])[1].splitlines()
    system_aaaa = _run(["dig", "+short", "AAAA", hostname])[1].splitlines()
    reference_a = _run(["dig", "+short", "@%s" % REFERENCE_RESOLVER, "A", hostname])[1].splitlines()
    reference_aaaa = _run(["dig", "+short", "@%s" % REFERENCE_RESOLVER, "AAAA", hostname])[1].splitlines()
    system_a = sorted(x for x in system_a if x)
    system_aaaa = sorted(x for x in system_aaaa if x)
    reference_a = sorted(x for x in reference_a if x)
    reference_aaaa = sorted(x for x in reference_aaaa if x)
    return {
        "hostname": hostname,
        "system_resolver_A": system_a,
        "system_resolver_AAAA": system_aaaa,
        "reference_resolver_A": reference_a,
        "reference_resolver_AAAA": reference_aaaa,
        "A_agrees": system_a == reference_a,
        "AAAA_agrees": system_aaaa == reference_aaaa,
    }


def first_hop(target_ip: str, protocol: str) -> dict:
    """The kernel's routing decision toward ``target_ip`` -- a proxy for a real
    traceroute's first hop, used because ``traceroute`` is not installed on this server
    and this run does not install packages on it (see module docstring)."""
    flag = ["-6"] if protocol == "-6" else []
    rc, out = _run(["ip"] + flag + ["route", "get", target_ip])
    return {"target": target_ip, "protocol": protocol, "rc": rc, "route": out}


def resolve_for_route(hostname_or_ip: str, protocol: str) -> str | None:
    if hostname_or_ip.count(".") == 3 and all(part.isdigit() for part in hostname_or_ip.split(".")):
        return hostname_or_ip if protocol == "-4" else None
    record_type = "AAAA" if protocol == "-6" else "A"
    rc, out = _run(["dig", "+short", record_type, hostname_or_ip])
    lines = [line for line in out.splitlines() if line and not line.endswith(".")]
    return lines[0] if lines else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--probes", type=int, default=DEFAULT_PROBES,
                        help="probes per (address, protocol) pair, minimum 100 per the task")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S,
                        help="curl --max-time per probe, seconds")
    parser.add_argument("--outdir", default=None,
                        help="where per-probe JSONL lands (default: a fresh /tmp dir)")
    args = parser.parse_args(argv)

    outdir = Path(args.outdir) if args.outdir else Path(
        "/tmp/kanal-diagnostika-%s" % datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    )
    outdir.mkdir(parents=True, exist_ok=True)

    print("== resolution: system resolver vs %s ==" % REFERENCE_RESOLVER)
    resolution = {}
    for hostname in (a for a in ADDRESSES if not a.replace(".", "").isdigit()):
        result = compare_resolution(hostname)
        resolution[hostname] = result
        print("  %-18s A agrees=%s AAAA agrees=%s  sys-A=%s ref-A=%s"
              % (hostname, result["A_agrees"], result["AAAA_agrees"],
                 result["system_resolver_A"], result["reference_resolver_A"]))
    (outdir / "resolution.json").write_text(json.dumps(resolution, indent=2), encoding="utf-8")

    print("\n== first hop (ip route get -- traceroute not installed, see module docstring) ==")
    routes = []
    for address in ADDRESSES:
        for protocol in PROTOCOLS:
            target = resolve_for_route(address, protocol)
            if target is None:
                print("  %-18s %-3s  no %s address available, skipped" % (
                    address, protocol, "AAAA" if protocol == "-6" else "A"))
                continue
            route = first_hop(target, protocol)
            routes.append(route)
            print("  %-18s %-3s -> %-40s rc=%s  %s" % (
                address, protocol, target, route["rc"], route["route"].splitlines()[0] if route["route"] else "(no output)"))
    (outdir / "routes.json").write_text(json.dumps(routes, indent=2), encoding="utf-8")

    print("\n== probes (%d per address x protocol, timeout=%ss) ==" % (args.probes, args.timeout))
    stats: list[BatchStats] = []
    for address in ADDRESSES:
        for protocol in PROTOCOLS:
            out_path = outdir / ("%s_%s.jsonl" % (address.replace(".", "-"), protocol.lstrip("-")))
            probes = probe_batch(address, protocol, args.probes, args.timeout, out_path)
            batch_stats = summarize(address, protocol, probes)
            stats.append(batch_stats)
            print(batch_stats.line())

    total_probes = sum(s.total for s in stats)
    print("\ntotal probes: %d (raw data: %s)" % (total_probes, outdir))
    print("NOT MEASURED by this run: the INBOUND channel (nothing here listens for "
          "incoming connections), behaviour under concurrent load, and any difference "
          "between night and day -- this is one run, one point in time.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
