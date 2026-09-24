"""PestKG API performance benchmark.

Measures latency distributions (P50/P95/P99) and throughput for the
hot API endpoints. Run it after installing the API dependencies:

    python apps/api/tests/perf_benchmark.py

The script starts an in-process TestClient, warms up each endpoint,
then runs a fixed number of timed requests and reports statistics.
"""
from __future__ import annotations

import os
import statistics
import sys
import time
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "apps/api/src"))
os.environ["PESTKG_DATA_DIR"] = str(ROOT / "data/releases")
os.environ.pop("PESTKG_NEO4J_URI", None)
os.environ.pop("PESTKG_NEO4J_PASSWORD", None)

from fastapi.testclient import TestClient  # noqa: E402

from pestkg_api.config import get_settings  # noqa: E402
get_settings.cache_clear()
from pestkg_api.main import app  # noqa: E402


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(len(ordered) * pct / 100)))
    return ordered[index]


def measure(name: str, func: Callable[[], int], iterations: int = 200) -> None:
    # warmup
    for _ in range(10):
        func()
    latencies: list[float] = []
    errors = 0
    start = time.perf_counter()
    for _ in range(iterations):
        t0 = time.perf_counter()
        try:
            status = func()
        except Exception:
            status = 0
            errors += 1
        latencies.append((time.perf_counter() - t0) * 1000)
        if status >= 400:
            errors += 1
    total = time.perf_counter() - start
    rps = iterations / total if total > 0 else 0
    print(
        f"{name:<45} "
        f"n={iterations}  "
        f"P50={percentile(latencies, 50):7.3f}ms  "
        f"P95={percentile(latencies, 95):7.3f}ms  "
        f"P99={percentile(latencies, 99):7.3f}ms  "
        f"avg={statistics.mean(latencies):7.3f}ms  "
        f"rps={rps:7.1f}  "
        f"errors={errors}"
    )


def main() -> None:
    with TestClient(app) as client:
        # Discover a valid node id and use id for path/neighborhood tests.
        search_resp = client.get("/api/v1/search", params={"q": "GLYPHOSATE", "limit": 5})
        node_id = search_resp.json()["data"][0]["id"] if search_resp.json()["data"] else "AU:AI:d22fdad88d35b630b33716b8"

        uses_resp = client.post(
            "/api/v1/registration-uses/query",
            json={"filters": {"jurisdictions": ["AU"]}, "page_size": 2},
        )
        uses_data = uses_resp.json()["data"]
        use_id_a = uses_data[0]["use_id"] if uses_data else "AU:USE:0"
        use_id_b = uses_data[1]["use_id"] if len(uses_data) > 1 else use_id_a

        print("=" * 100)
        print("PestKG API Performance Benchmark")
        print("=" * 100)

        measure(
            "GET /api/v1/stats/overview",
            lambda: client.get("/api/v1/stats/overview").status_code,
        )
        measure(
            "GET /api/v1/stats/countries",
            lambda: client.get("/api/v1/stats/countries").status_code,
        )
        measure(
            "GET /api/v1/schema",
            lambda: client.get("/api/v1/schema").status_code,
        )
        measure(
            "GET /api/v1/search?q=GLYPHOSATE",
            lambda: client.get("/api/v1/search", params={"q": "GLYPHOSATE", "limit": 50}).status_code,
        )
        measure(
            "GET /api/v1/search?q=毒死蜱",
            lambda: client.get("/api/v1/search", params={"q": "毒死蜱", "limit": 10}).status_code,
        )
        measure(
            "GET /api/v1/search (empty, type filter)",
            lambda: client.get("/api/v1/search", params={"entity_type": "ActiveIngredientLocal", "limit": 50}).status_code,
        )
        measure(
            f"GET /api/v1/entities/{node_id}",
            lambda: client.get(f"/api/v1/entities/{node_id}").status_code,
        )
        measure(
            "GET /api/v1/graph/neighborhood depth=1",
            lambda: client.get("/api/v1/graph/neighborhood", params={"node_id": node_id, "depth": 1}).status_code,
        )
        measure(
            "GET /api/v1/graph/neighborhood depth=2",
            lambda: client.get("/api/v1/graph/neighborhood", params={"node_id": node_id, "depth": 2}).status_code,
        )
        measure(
            "GET /api/v1/graph/path (same graph)",
            lambda: client.get("/api/v1/graph/path", params={"start_id": use_id_a, "end_id": use_id_b, "max_depth": 3}).status_code,
        )
        measure(
            "POST /api/v1/registration-uses/query (filtered)",
            lambda: client.post(
                "/api/v1/registration-uses/query",
                json={"filters": {"jurisdictions": ["AU"], "active_ingredient": "GLYPHOSATE"}, "page_size": 50},
            ).status_code,
        )
        measure(
            "POST /api/v1/registration-uses/query (unfiltered)",
            lambda: client.post(
                "/api/v1/registration-uses/query",
                json={"filters": {}, "page_size": 50},
            ).status_code,
        )
        measure(
            "GET /api/v1/compare/q5?jurisdiction=AU",
            lambda: client.get("/api/v1/compare/q5", params={"jurisdiction": "AU", "limit": 100}).status_code,
        )
        measure(
            "GET /api/v1/releases",
            lambda: client.get("/api/v1/releases").status_code,
        )


if __name__ == "__main__":
    main()
