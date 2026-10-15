#!/usr/bin/env python3
"""Synthetic smoke for a registered AMB provider (#810): ingest, retrieve, cross-user isolation.

No benchmark data is used. Run from ``reference/`` in the provider's AMB environment:
``python ../scripts/smoke_amb_provider.py PROVIDER_KEY AMB_ROOT STORE OUT.json``
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import run_amb_external  # noqa: F401  (imports every bridge)
from amb_agent_memory_bridge import install_amb_agent_memory_provider  # noqa: F401
from amb_graphiti_bridge import install_amb_graphiti_provider
from amb_mempalace_bridge import install_amb_mempalace_provider
from amb_hindsight_bridge import install_amb_hindsight_provider


def main() -> int:
    key, amb_root, store, out = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
    install_amb_graphiti_provider(amb_root)
    install_amb_mempalace_provider(amb_root)
    install_amb_hindsight_provider(amb_root)
    from memory_bench.memory import REGISTRY  # type: ignore[import-not-found]
    from memory_bench.models import Document  # type: ignore[import-not-found]

    docs = [
        Document(id="s1", content="Alice works as an engineer at Acme Corp in Boston.", user_id="user-a", timestamp="2025-01-10T09:00:00Z"),
        Document(id="s2", content="Alice's favourite editor is Vim.", user_id="user-a", timestamp="2025-02-01T09:00:00Z"),
        Document(id="s3", content="Alice left Acme Corp and now works at Globex in Denver.", user_id="user-a", timestamp="2025-06-01T09:00:00Z"),
        Document(id="s4", content="Bob works at Initech.", user_id="user-b", timestamp="2025-03-01T09:00:00Z"),
    ]
    provider = REGISTRY[key]()
    provider.prepare(store, reset=True)
    provider.ingest(docs)
    report = {"provider": key, "searches": {}}
    for name, query, user in (("alice_work", "Where does Alice work now?", "user-a"),
                              ("alice_editor", "Which editor does Alice prefer?", "user-a"),
                              ("bob_from_a", "Where does Bob work?", "user-a"),
                              ("bob_from_b", "Where does Bob work?", "user-b")):
        documents, raw = provider.retrieve(query, k=10, user_id=user)
        report["searches"][name] = {"doc_ids": [d.id for d in documents], "raw": raw}
    provider.cleanup()
    s = report["searches"]
    report["checks"] = {
        "alice_work_returns_alice_docs": bool({"s1", "s3"} & set(s["alice_work"]["doc_ids"])),
        "alice_editor_returns_s2": "s2" in s["alice_editor"]["doc_ids"],
        "no_cross_user_leak_a": all("s4" not in s[n]["doc_ids"] for n in ("alice_work", "alice_editor", "bob_from_a")),
        "no_cross_user_leak_b": not ({"s1", "s2", "s3"} & set(s["bob_from_b"]["doc_ids"])),
        "budget_respected": all(len(v["doc_ids"]) <= 10 for v in s.values()),
    }
    out.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(report["checks"], indent=2))
    return 0 if all(report["checks"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
