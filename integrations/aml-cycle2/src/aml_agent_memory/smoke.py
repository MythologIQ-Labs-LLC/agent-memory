"""Contract smoke for an AML Cycle 2 Add/Search deployment (ours or any other).

Plays the platform's side of the published contract against ``--base-url`` and records one
JSON report: health without credentials, 401 on a bad key, chunked Add with exact ID echo,
immediate searchability, idempotent replay (no duplicate memories), 409 on a reused
request_id with a different payload, Search shape/order/top_k, and strict user isolation.
Every check uses fresh random user ids, so it never reads or disturbs other data.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from typing import Any


class Client:
    def __init__(self, base_url: str, key: str, timeout: float = 120.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.key = key
        self.timeout = timeout

    def call(self, method: str, path: str, body: Any = None, *, key: str | None = None, auth: bool = True) -> tuple[int, Any, float]:
        headers = {"Content-Type": "application/json"}
        if auth:
            headers["Authorization"] = f"Bearer {self.key if key is None else key}"
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(self.base_url + path, data=data, method=method, headers=headers)
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                status, raw = response.status, response.read()
        except urllib.error.HTTPError as error:
            status, raw = error.code, error.read()
        elapsed = (time.perf_counter() - started) * 1000
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else None
        except (UnicodeDecodeError, json.JSONDecodeError):
            payload = {"_raw": raw[:200].decode("utf-8", "replace")}
        return status, payload, elapsed


def _messages(tag: str, start: int, count: int) -> list[dict]:
    return [
        {
            "role": "user" if index % 2 == 0 else "assistant",
            "timestamp": 1704067200000 + index * 60_000,
            "content": f"Session note {index} for {tag}: the user's favourite marker colour is {'teal' if index == 3 else 'grey'}"
            + (f" and the project codename is {tag}" if index == start else ""),
        }
        for index in range(start, start + count)
    ]


def run(client: Client) -> dict:
    run_id = uuid.uuid4().hex[:12]
    user_a = f"smoke:{run_id}:user-a"
    user_b = f"smoke:{run_id}:user-b"
    codename = f"zq{run_id}"
    checks: list[dict] = []
    latencies: dict[str, list[float]] = {"add": [], "search": []}

    def check(name: str, passed: bool, detail: Any = None) -> bool:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})
        return passed

    status, payload, _ = client.call("GET", "/health", auth=False)
    check("health_unauthenticated_2xx", 200 <= status < 300, status)

    status, _, _ = client.call("POST", "/add", {"request_id": "x", "user_id": user_a, "session_id": "s", "messages": [{"role": "user", "content": "x"}]}, key="wrong-key-0000000000")
    check("add_rejects_bad_key_401", status == 401, status)
    status, _, _ = client.call("POST", "/search", {"query": "x", "user_id": user_a, "top_k": 5}, auth=False)
    check("search_rejects_missing_key_401", status == 401, status)

    chunks = [_messages(codename, 0, 20), _messages(codename, 20, 20), _messages(codename, 40, 5)]
    for index, chunk in enumerate(chunks):
        body = {"request_id": f"smoke:{run_id}:conv-a:chunk-{index}", "user_id": user_a, "session_id": f"smoke:{run_id}:session-{index}", "messages": chunk}
        status, payload, elapsed = client.call("POST", "/add", body)
        latencies["add"].append(elapsed)
        echoed = isinstance(payload, dict) and payload.get("success") is True and all(payload.get(k) == body[k] for k in ("request_id", "user_id", "session_id"))
        check(f"add_chunk_{index}_200_and_exact_echo", status == 200 and echoed, {"status": status, "payload": payload})
        if index == 0:
            status, payload, elapsed = client.call("POST", "/search", {"query": f"What is the project codename {codename}?", "user_id": user_a, "top_k": 100})
            latencies["search"].append(elapsed)
            found = status == 200 and any(codename in item.get("content", "") for item in payload.get("data", []))
            check("searchable_immediately_after_add_200", found, {"status": status, "returned": len((payload or {}).get("data", []))})

    status, payload, elapsed = client.call("POST", "/search", {"query": "favourite marker colour", "user_id": user_a, "top_k": 100})
    latencies["search"].append(elapsed)
    data = payload.get("data") if isinstance(payload, dict) else None
    check("search_200_with_data_array", status == 200 and isinstance(data, list) and set(payload) == {"data"}, {"status": status})
    data = data or []
    check("search_items_have_nonempty_id_and_content", all(isinstance(i.get("id"), str) and i["id"] and isinstance(i.get("content"), str) and i["content"] for i in data), len(data))
    scores = [item.get("score") for item in data]
    check("search_scores_descending", all(isinstance(s, (int, float)) for s in scores) and scores == sorted(scores, reverse=True), scores[:5])
    ids_before = sorted(item["id"] for item in data if "id" in item)
    check("search_returns_all_45_acknowledged_messages", len(ids_before) == 45 and len(set(ids_before)) == 45, len(ids_before))

    status, payload, _ = client.call("POST", "/search", {"query": "favourite marker colour", "user_id": user_a, "top_k": 7})
    check("search_respects_top_k", status == 200 and len(payload.get("data", [])) <= 7, len((payload or {}).get("data", [])))
    status, payload, _ = client.call("POST", "/search", {"query": "favourite marker colour", "user_id": user_a, "top_k": 5, "options": ["A. teal", "B. grey"]})
    check("search_accepts_options", status == 200 and len(payload.get("data", [])) <= 5, status)

    replay = {"request_id": f"smoke:{run_id}:conv-a:chunk-0", "user_id": user_a, "session_id": f"smoke:{run_id}:session-0", "messages": chunks[0]}
    status, payload, _ = client.call("POST", "/add", replay)
    check("add_replay_is_idempotent_200", status == 200 and payload == {"success": True, "request_id": replay["request_id"], "user_id": user_a, "session_id": replay["session_id"]}, {"status": status})
    status, payload, _ = client.call("POST", "/search", {"query": "favourite marker colour", "user_id": user_a, "top_k": 100})
    check("add_replay_stores_nothing_new", sorted(item["id"] for item in payload.get("data", [])) == ids_before, len(payload.get("data", [])))
    conflict = dict(replay, messages=_messages("different", 0, 2))
    status, payload, _ = client.call("POST", "/add", conflict)
    check("add_reused_request_id_different_payload_409", status == 409, {"status": status, "payload": payload})

    status, payload, _ = client.call("POST", "/search", {"query": f"project codename {codename} favourite marker colour", "user_id": user_b, "top_k": 100})
    check("isolation_unknown_user_gets_empty_data", status == 200 and payload == {"data": []}, payload)
    body = {"request_id": f"smoke:{run_id}:conv-a:chunk-0", "user_id": user_b, "session_id": "b", "messages": [{"role": "user", "content": "user b only talks about lighthouses"}]}
    status, _, _ = client.call("POST", "/add", body)
    check("same_request_id_under_other_user_is_independent_200", status == 200, status)
    status, payload, _ = client.call("POST", "/search", {"query": f"project codename {codename} favourite marker colour lighthouses", "user_id": user_b, "top_k": 100})
    contents = [item.get("content", "") for item in (payload or {}).get("data", [])]
    check("isolation_no_cross_user_memory", status == 200 and contents and all(codename not in c and "marker" not in c for c in contents), contents)

    status, payload, _ = client.call("POST", "/search", {"query": "", "user_id": user_a, "top_k": 5})
    check("search_rejects_blank_query_422", status == 422, status)
    status, payload, _ = client.call("POST", "/add", {"request_id": "r", "user_id": user_a, "session_id": "s", "messages": []})
    check("add_rejects_empty_messages_422", status == 422, status)

    return {
        "schema": "agent-memory-aml-smoke/1",
        "base_url": client.base_url,
        "run_id": run_id,
        "checks": checks,
        "passed": sum(item["passed"] for item in checks),
        "failed": sum(not item["passed"] for item in checks),
        "latency_ms": {name: {"n": len(values), "max": round(max(values), 1) if values else None} for name, values in latencies.items()},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--key", default=os.environ.get("AML_MEMORY_KEY"), help="memory system key (default: $AML_MEMORY_KEY)")
    parser.add_argument("--report", help="write the JSON report here")
    args = parser.parse_args(argv)
    if not args.key:
        parser.error("--key or AML_MEMORY_KEY is required")
    report = run(Client(args.base_url, args.key))
    text = json.dumps(report, indent=2)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    for item in report["checks"]:
        print(("PASS " if item["passed"] else "FAIL ") + item["check"])
    print(f"{report['passed']} passed, {report['failed']} failed")
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
