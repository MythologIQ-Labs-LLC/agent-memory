"""Bounded load probe: chunked Adds then Searches against a running service, timed per call.

Synthetic content only (no benchmark data). Sizes default to roughly one long AML history
per user (``--messages`` per user, sent in 20-message chunks as the platform does) across
``--users`` users written concurrently, followed by ``--searches`` top_k=100 Searches per user.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from .smoke import Client

WORDS = (
    "meeting budget flight hotel doctor garden recipe guitar marathon invoice lease puppy camera "
    "painting library sister birthday conference deadline vacation museum bicycle laptop concert "
    "insurance dentist kitchen wedding promotion apartment"
).split()


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, max(0, round(fraction * len(ordered)) - 1))], 1)


def _summary(values: list[float]) -> dict:
    return {"n": len(values), "p50": _percentile(values, 0.5), "p95": _percentile(values, 0.95), "max": round(max(values), 1), "mean": round(statistics.mean(values), 1)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--key", default=os.environ.get("AML_MEMORY_KEY"))
    parser.add_argument("--users", type=int, default=8)
    parser.add_argument("--messages", type=int, default=1000)
    parser.add_argument("--searches", type=int, default=20)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--report")
    args = parser.parse_args(argv)
    client = Client(args.base_url, args.key, timeout=1200)
    run_id = uuid.uuid4().hex[:10]
    failures: list[str] = []

    def write_user(index: int) -> list[float]:
        rng = random.Random(index)
        user = f"load:{run_id}:{index}"
        timings = []
        for chunk_start in range(0, args.messages, 20):
            messages = [
                {"role": "user" if i % 2 == 0 else "assistant", "timestamp": 1704067200000 + i * 60_000,
                 "content": f"turn {i}: " + " ".join(rng.choices(WORDS, k=40))}
                for i in range(chunk_start, min(args.messages, chunk_start + 20))
            ]
            body = {"request_id": f"{user}:chunk-{chunk_start // 20}", "user_id": user, "session_id": f"{user}:s{chunk_start // 200}", "messages": messages}
            status, _, elapsed = client.call("POST", "/add", body)
            if status != 200:
                failures.append(f"add {user} chunk {chunk_start // 20}: {status}")
            timings.append(elapsed)
        return timings

    def search_user(index: int) -> list[float]:
        rng = random.Random(1000 + index)
        user = f"load:{run_id}:{index}"
        timings = []
        for _ in range(args.searches):
            query = "When did I talk about the " + " and the ".join(rng.sample(WORDS, 2)) + "?"
            status, payload, elapsed = client.call("POST", "/search", {"query": query, "user_id": user, "top_k": 100})
            if status != 200 or not isinstance(payload, dict) or len(payload.get("data", [])) > 100:
                failures.append(f"search {user}: {status}")
            timings.append(elapsed)
        return timings

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        add_timings = [t for chunk in pool.map(write_user, range(args.users)) for t in chunk]
    add_wall = time.perf_counter() - started
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        search_timings = [t for chunk in pool.map(search_user, range(args.users)) for t in chunk]
    search_wall = time.perf_counter() - started
    report = {
        "schema": "agent-memory-aml-load-probe/1",
        "parameters": {k: getattr(args, k) for k in ("users", "messages", "searches", "concurrency")},
        "add_ms_per_20_message_chunk": _summary(add_timings),
        "add_wall_s": round(add_wall, 1),
        "messages_written": args.users * args.messages,
        "search_ms_top_k_100": _summary(search_timings),
        "search_wall_s": round(search_wall, 1),
        "failures": failures,
    }
    text = json.dumps(report, indent=2)
    print(text)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
