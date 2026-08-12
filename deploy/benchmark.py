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
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BODY = {
    "subject": "Aucun reseau dans le quartier",
    "body": (
        "Depuis trois jours il n y a plus aucun signal dans le quartier. "
        "Impossible de passer un appel, toute la rue est concernee. "
        "J ai deja appele le service client deux fois sans resultat."
    ),
    "channel": "web",
    "claimant": {"full_name": "Charge de test", "email": "bench@example.tn"},
}


def one(url: str) -> tuple[float, int]:
    payload = json.dumps(BODY).encode()
    request = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response.read()
            status = response.status
    except urllib.error.HTTPError as exc:
        status = exc.code
    except Exception:
        status = 0
    return (time.perf_counter() - started) * 1000, status


def main() -> None:
    total = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    concurrency = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    url = "http://api.reclamations.svc.cluster.local:8000/api/v1/complaints"
    if len(sys.argv) > 3:
        url = sys.argv[3]

    # Warm the process: the first request pays for lazy imports and the first
    # Mongo round trip, and reporting that as p99 would be dishonest.
    for _ in range(10):
        one(url)

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        results = list(pool.map(lambda _: one(url), range(total)))
    wall = time.perf_counter() - started

    latencies = sorted(latency for latency, _ in results)
    ok = sum(1 for _, status in results if status == 201)

    def percentile(share: float) -> float:
        return latencies[min(len(latencies) - 1, int(len(latencies) * share))]

    print(f"requests      {total} @ concurrency {concurrency}")
    print(f"succeeded     {ok}/{total}")
    print(f"throughput    {total / wall:.1f} req/s")
    print(f"mean          {statistics.mean(latencies):.1f} ms")
    print(f"p50           {percentile(0.50):.1f} ms")
    print(f"p95           {percentile(0.95):.1f} ms")
    print(f"p99           {percentile(0.99):.1f} ms")
    print(f"max           {latencies[-1]:.1f} ms")
    print()
    print("target: POST /complaints under 100 ms p95 (spec section 9)")
    print("verdict:", "PASS" if percentile(0.95) < 100 else "FAIL")


if __name__ == "__main__":
    main()
