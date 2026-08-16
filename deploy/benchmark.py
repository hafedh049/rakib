"""Load benchmark for the 2 vCPU / 4 GB envelope. Run ON the VPS:

    python3 /root/rakib/src/deploy/benchmark.py [requests] [concurrency]

Measures POST /complaints, which spec section 9 requires to return in under
100 ms at p95. Triage itself runs in the worker, so this measures the path a
claimant actually waits on.

Run against the ClusterIP rather than the public host so the numbers describe
the application, not the round trip to Let's Encrypt's TLS and back.
"""

import json
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

#: Every row the benchmark creates carries this address so it can be removed
#: again. A load test that leaves a thousand complaints behind does not just
#: clutter the demo — it inflates the annual declaration to the regulator.
BENCH_EMAIL = "benchmark@rakib.invalid"

BODY = {
    "subject": "Retrait debite sans distribution de billets",
    "body": (
        "J ai effectue un retrait de 300 dinars au distributeur et aucun "
        "billet n est sorti, mais mon compte a bien ete debite. "
        "J ai deja appele le service client deux fois sans resultat."
    ),
    "channel": "web",
    # Recognisable on purpose: these rows are real complaints in the real
    # database and they land in the BCT declaration. Marking them makes the
    # cleanup below exact rather than approximate.
    "claimant": {"full_name": "Charge de test", "email": BENCH_EMAIL},
}


def one(url: str) -> tuple[float, int, str]:
    """Return (milliseconds, status, detail).

    `detail` exists because an earlier version swallowed every exception into
    `status = 0` and then printed a latency table over 200 failed requests,
    verdict PASS. A benchmark that cannot fail loudly is worse than none: it
    manufactures a number nobody checks.
    """
    payload = json.dumps(BODY).encode()
    request = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response.read()
            return (time.perf_counter() - started) * 1000, response.status, ""
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:200]
        return (time.perf_counter() - started) * 1000, exc.code, detail
    except Exception as exc:  # noqa: BLE001 — the reason is the point
        return (time.perf_counter() - started) * 1000, 0, f"{type(exc).__name__}: {exc}"


def default_url() -> str:
    """Reach the API without going through the public host or TLS.

    The in-cluster DNS name only resolves inside a pod; run from the node it
    fails, and the first version of this script reported that as a latency
    result. So resolve the Service ClusterIP directly and fall back to the DNS
    name only if kubectl is unavailable.
    """
    try:
        ip = subprocess.run(
            ["kubectl", "-n", "reclamations", "get", "svc", "api",
             "-o", "jsonpath={.spec.clusterIP}"],
            capture_output=True, text=True, timeout=10, check=True,
        ).stdout.strip()
        if ip:
            return f"http://{ip}:8000/api/v1/complaints"
    except Exception:  # noqa: BLE001 — fall through to the DNS name
        pass
    return "http://api.reclamations.svc.cluster.local:8000/api/v1/complaints"


def cleanup() -> None:
    """Delete the rows this benchmark created.

    Runs by default. Skipping it is possible (--keep) but has to be asked for,
    because the failure mode is silent: the complaints look real, they are
    categorised and counted, and they only become visible as a wrong number in
    a regulatory report months later.
    """
    script = "\n".join([
        "import asyncio",
        "from app import db",
        "from app.models.complaint import Complaint",
        "async def main():",
        "    await db.init_db()",
        f"    result = await Complaint.find({{'claimant.email': '{BENCH_EMAIL}'}}).delete()",
        "    print('cleanup: deleted', result.deleted_count if result else 0)",
        "    await db.close_db()",
        "asyncio.run(main())",
    ])
    subprocess.run(
        ["kubectl", "-n", "reclamations", "exec", "deploy/api", "--",
         "python", "-c", script],
        check=False,
    )


def main() -> None:
    total = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    concurrency = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    url = sys.argv[3] if len(sys.argv) > 3 else default_url()

    # Warm the process: the first request pays for lazy imports and the first
    # Mongo round trip, and reporting that as p99 would be dishonest.
    for _ in range(10):
        one(url)

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        results = list(pool.map(lambda _: one(url), range(total)))
    wall = time.perf_counter() - started

    latencies = sorted(latency for latency, _, _ in results)
    ok = sum(1 for _, status, _ in results if status == 201)

    def percentile(share: float) -> float:
        return latencies[min(len(latencies) - 1, int(len(latencies) * share))]

    print(f"requests      {total} @ concurrency {concurrency}")
    print(f"succeeded     {ok}/{total}")

    if ok < total:
        # Show what actually came back, grouped, so a systematic failure is
        # visible instead of hiding behind an average.
        failures: dict[tuple[int, str], int] = {}
        for _, status, detail in results:
            if status != 201:
                failures[(status, detail)] = failures.get((status, detail), 0) + 1
        for (status, detail), count in sorted(
            failures.items(), key=lambda item: -item[1]
        )[:5]:
            label = status or "no response"
            print(f"  {count:5d} x {label}  {detail}")

    if ok == 0:
        print()
        print("Every request failed. The latency figures below would describe "
              "error handling, not the service, so no verdict is given.")
        raise SystemExit(1)
    print(f"throughput    {total / wall:.1f} req/s")
    print(f"mean          {statistics.mean(latencies):.1f} ms")
    print(f"p50           {percentile(0.50):.1f} ms")
    print(f"p95           {percentile(0.95):.1f} ms")
    print(f"p99           {percentile(0.99):.1f} ms")
    print(f"max           {latencies[-1]:.1f} ms")
    print()
    if "--keep" not in sys.argv:
        cleanup()

    print("target: POST /complaints under 100 ms p95 (spec section 9)")
    # A pass requires the requests to have worked. Timing failures fast is not
    # a performance result.
    passed = percentile(0.95) < 100 and ok == total
    print("verdict:", "PASS" if passed else "FAIL")
    if ok != total:
        print(f"         ({total - ok} request(s) did not return 201)")


if __name__ == "__main__":
    main()
