"""Research-only: can the existing governed semantic route rescue strict-lexical losses?

No model downloads or changes to runtime, accepted baselines, agent tools, or default
configuration. Requires an installed, SHA256-verified pinned ONNX representation.
This is author-visible diagnostic data, NOT independent Gate 2 acceptance.

From the repository root, in a qualified Linux checkout at this branch head:

  python -m pip install -e '.[semantic]'
  python integrations/agent-memory-mcp/semantic_rescue_probe.py \
    --representation-dir /private/pinned-model-dir \
    --out /tmp/819-semantic-rescue.json

The pinned model's required files, revisions, and SHA256 values are defined
in reference/agentmem_ref/runtime/representation_onnx.py. Do not fetch a
different model, silently degrade semantic=required, or change the threshold.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import statistics
import tempfile
import time

HERE = Path(__file__).resolve().parent
DEFAULT_CASES = HERE.parents[1] / "reports/validation/mcp-gate2-task-probe/admission-experiment/task_cases_disjoint.json"
FLAG = "AGENT_MEMORY_EXPERIMENTAL_LEXICAL_ADMISSION"


def validate_cases(cases: dict) -> None:
    keys = [item["key"] for item in cases["records"]]
    if len(keys) != len(set(keys)) or not keys:
        raise ValueError("records must have distinct keys")
    required = {key for task in cases["tasks"] for key in task["required"]}
    if not required.issubset(keys):
        raise ValueError("task requires an unknown memory key")
    if len({t["id"] for t in cases["tasks"]}) != len(cases["tasks"]):
        raise ValueError("duplicate task IDs")
    if any(not r["text"].strip() for r in cases["records"]):
        raise ValueError("empty memory source text")


@contextmanager
def admission_mode(mode: str | None):
    existing = os.environ.get(FLAG)
    try:
        if mode is None:
            os.environ.pop(FLAG, None)
        else:
            os.environ[FLAG] = mode
        yield
    finally:
        if existing is None:
            os.environ.pop(FLAG, None)
        else:
            os.environ[FLAG] = existing


def assess(returned: list[str], required: list[str]) -> dict:
    returned_set = set(returned)
    expected = set(required)
    return {
        "required_complete": expected.issubset(returned_set) if expected else None,
        "required_hits": len(expected & returned_set),
        "unexpected_items": sum(key not in expected for key in returned),
        "empty_no_answer_context": not returned if not expected else None,
    }


def summarize(rows: list[dict]) -> dict:
    positive = [r for r in rows if r["required"]]
    negative = [r for r in rows if not r["required"]]
    times = sorted(r["elapsed_ms"] for r in rows)
    return {
        "answerable_complete": sum(r["score"]["required_complete"] is True for r in positive),
        "answerable_total": len(positive),
        "required_hits": sum(r["score"]["required_hits"] for r in positive),
        "required_total": sum(len(r["required"]) for r in positive),
        "no_answer_empty_context": sum(r["score"]["empty_no_answer_context"] is True for r in negative),
        "no_answer_total": len(negative),
        "unexpected_items": sum(r["score"]["unexpected_items"] for r in rows),
        "p50_ms": statistics.median(times) if times else None,
        "p95_ms": times[min(len(times)-1, max(0, (95*len(times)+99)//100-1))] if times else None,
    }


def execute(cases: dict, representation_dir: Path, *, k: int = 5) -> dict:
    if not 1 <= k <= 8:
        raise ValueError("k must be 1..8")
    validate_cases(cases)
    from agentmem_ref import AgentMemory

    results = {}
    with tempfile.TemporaryDirectory(prefix="am-semantic-rescue-") as temp:
        root = Path(temp) / "store"
        options = {
            "tenant": cases["tenant"], "actor_id": "agent:rescue-probe",
            "scope": cases["scope"], "purpose": "research-only semantic rescue probe",
        }
        # Seed once, with the existing default runtime, so each arm reads
        # the same committed facts under the same tenant and scope.
        with admission_mode(None), AgentMemory.open(root, **options) as memory:
            expected_facts = {}
            for record in cases["records"]:
                write = memory.remember(record["key"], record["text"],
                                        source_ref="research:semantic-rescue-probe")
                if not write.get("committed") or not write.get("fact_uuid"):
                    raise RuntimeError(f"seed write was refused for {record['key']}: {write}")
                expected_facts[write["fact_uuid"]] = record["key"]
        arms = (
            ("default_lexical", None, "off"),
            ("strict_lexical", "content_term", "off"),
            ("strict_plus_semantic", "content_term", "required"),
            ("default_plus_semantic", None, "required"),
        )
        for name, flag, semantic in arms:
            with admission_mode(flag):
                with AgentMemory.open(root, **options, semantic_retrieval=semantic,
                                      representation_dir=representation_dir) as memory:
                    posture = memory.semantic_retrieval_posture()
                    if semantic == "required" and posture.get("status") != "enabled":
                        raise RuntimeError("semantic=required did not enable the pinned vector route")
                    # Verify AFTER retrieval, because the vector cache is
                    # derived lazily from canonical facts during those reads.
                    # Verification checks numeric rows against the pinned
                    # model; no automatic rebuilding can conceal a mismatch.
                    verified = None
                    rows = []
                    for task in cases["tasks"]:
                        start = time.perf_counter()
                        package = memory.recall_context(
                            task["question"], max_items=k, consumer_profile="all_returned",
                            max_chars_per_item=1200, max_total_chars=5000, max_tokens=1250,
                        )
                        duration = (time.perf_counter() - start) * 1000
                        # Inspect only the governed delivered content; missing
                        # or truncated evidence cannot become a successful hit.
                        items = package.get("items") or []
                        keys = []
                        for item in items:
                            if item.get("state") != "resolved":
                                continue
                            fact = item.get("fact_ref")
                            key = (item.get("provenance") or {}).get("memory_ref")
                            if fact not in expected_facts or key != expected_facts[fact]:
                                continue
                            original = next(r["text"] for r in cases["records"] if r["key"] == key)
                            if item.get("content") == original:
                                keys.append(key)
                        rows.append({
                            "id": task["id"], "required": task["required"],
                            "returned_keys": keys,
                            "score": assess(keys, task["required"]),
                            "elapsed_ms": duration,
                            "raw_returned_count": len(package.get("recall", {}).get("returned") or []),
                            "delivered_count": len(items),
                        })
                    if semantic == "required":
                        verified = memory.verify_semantic_store(rebuild=False)
                        if verified.get("mismatched") or verified.get("orphans"):
                            raise RuntimeError(f"derived vector store failed verification: {verified}")
                    results[name] = {
                        "semantic_mode": semantic, "lexical_flag": flag or "off",
                        "semantic_posture": {key: posture.get(key) for key in ("status", "mode", "reason")},
                        "verification": verified,
                        "summary": summarize(rows),
                        "rows": rows,
                    }

    base = {r["id"]: r for r in results["default_lexical"]["rows"]}
    strict = {r["id"]: r for r in results["strict_lexical"]["rows"]}
    rescue = {r["id"]: r for r in results["strict_plus_semantic"]["rows"]}
    lost_ids = [
        ident for ident in base
        if base[ident]["score"]["required_complete"] is True
        and strict[ident]["score"]["required_complete"] is False
    ]
    return {
        "schema": "agent-memory-semantic-rescue-research/0.1.0",
        "qualification": "open development cohort only; no model training, answer-quality or sealed holdout claim",
        "dataset_sha256": hashlib.sha256(
            json.dumps(cases, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "dataset_records": len(cases["records"]),
        "dataset_tasks": len(cases["tasks"]),
        "k": k,
        "representation_dir": "<host-local-pinned-model>",
        "scoring": "full exact source content with trusted fact_ref and memory_ref",
        "arms": results,
        "lost_with_strict_lexical": lost_ids,
        "recovered_by_semantic": [
            ident for ident in lost_ids if rescue[ident]["score"]["required_complete"] is True
        ],
        "not_recovered_by_semantic": [
            ident for ident in lost_ids if rescue[ident]["score"]["required_complete"] is not True
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--representation-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-items", type=int, default=5)
    args = parser.parse_args()
    if not args.representation_dir.is_dir():
        parser.error("pinned representation directory must already exist; no automatic download")
    report = execute(json.loads(args.cases.read_text(encoding="utf-8")),
                     args.representation_dir, k=args.max_items)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True, default=str)+"\n",
                        encoding="utf-8")
    print(json.dumps({
        "summaries": {name: a["summary"] for name,a in report["arms"].items()},
        "lost": report["lost_with_strict_lexical"],
        "recovered": report["recovered_by_semantic"],
        "not_recovered": report["not_recovered_by_semantic"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
