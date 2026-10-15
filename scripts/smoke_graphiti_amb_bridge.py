#!/usr/bin/env python3
"""Synthetic smoke for the Graphiti AMB bridge (#812): install, ingest, retrieve, correction,
cross-user isolation, persistence across a restart. No benchmark data is used.

Run from ``reference/`` with the AMB+Graphiti environment and the local shim up:
``GRAPHITI_LOCAL_BASE_URL=http://127.0.0.1:8089/v1 python ../scripts/smoke_graphiti_amb_bridge.py AMB_ROOT STORE OUT.json``
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from amb_graphiti_bridge import frozen_configuration, install_amb_graphiti_provider


def main() -> int:
    amb_root, store, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    provider_cls = install_amb_graphiti_provider(amb_root)
    from memory_bench.models import Document  # type: ignore[import-not-found]

    docs = [
        Document(id="s1", content="Alice works as an engineer at Acme Corp in Boston.", user_id="user-a",
                 timestamp="2025-01-10T09:00:00Z"),
        Document(id="s2", content="Alice's favourite editor is Vim.", user_id="user-a",
                 timestamp="2025-02-01T09:00:00Z"),
        Document(id="s3", content="Alice left Acme Corp and now works at Globex in Denver.", user_id="user-a",
                 timestamp="2025-06-01T09:00:00Z"),
        Document(id="s4", content="Bob works at Initech.", user_id="user-b", timestamp="2025-03-01T09:00:00Z"),
    ]
    report: dict = {"configuration": None, "checks": {}, "ingest": [], "searches": {}}
    provider = provider_cls()
    started = time.perf_counter()
    provider.prepare(store, reset=True)
    report["configuration"] = frozen_configuration(provider._base_url)
    provider.ingest(docs)
    report["ingest"] = provider.ingest_log()
    report["ingest_seconds"] = round(time.perf_counter() - started, 1)

    def search(query: str, user: str, k: int = 10) -> dict:
        documents, raw = provider.retrieve(query, k=k, user_id=user)
        return {"doc_ids": [d.id for d in documents], "facts": [d.content for d in documents], "raw": raw}

    report["searches"]["alice_work"] = search("Where does Alice work now?", "user-a")
    report["searches"]["alice_editor"] = search("Which editor does Alice prefer?", "user-a")
    report["searches"]["bob_from_a"] = search("Where does Bob work?", "user-a")
    report["searches"]["bob_from_b"] = search("Where does Bob work?", "user-b")
    edges_before = report["searches"]["alice_work"]["raw"]["edges"]

    provider.cleanup()
    provider2 = provider_cls()
    provider2.prepare(store, reset=False)  # reopen the same database file
    _, raw_after = provider2.retrieve("Where does Alice work now?", k=10, user_id="user-a")
    provider2.cleanup()
    report["searches"]["alice_work_after_restart"] = {"raw": raw_after}

    all_a_ids = {i for key in ("alice_work", "alice_editor", "bob_from_a") for i in report["searches"][key]["doc_ids"]}
    checks = report["checks"]
    checks["every_document_ingested"] = len(report["ingest"]) == len(docs)
    checks["edges_extracted"] = sum(r["edges"] for r in report["ingest"]) > 0
    checks["alice_work_returns_alice_docs"] = bool({"s1", "s3"} & set(report["searches"]["alice_work"]["doc_ids"]))
    checks["no_cross_user_leak_a"] = "s4" not in all_a_ids
    checks["no_cross_user_leak_b"] = not ({"s1", "s2", "s3"} & set(report["searches"]["bob_from_b"]["doc_ids"]))
    checks["correction_invalidated_old_fact"] = any(e.get("invalid_at") or e.get("expired_at") for e in edges_before)
    checks["persistent_after_restart"] = (
        sorted(e["uuid"] for e in raw_after["edges"]) == sorted(e["uuid"] for e in edges_before)
    )
    out.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(checks, indent=2))
    # Every check is reported; the run fails only on the structural ones. Whether the small local
    # model invalidated the superseded fact is an observation about the system, not a smoke gate.
    required = [k for k in checks if k != "correction_invalidated_old_fact"]
    return 0 if all(checks[k] for k in required) else 1


if __name__ == "__main__":
    raise SystemExit(main())
