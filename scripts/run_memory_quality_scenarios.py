#!/usr/bin/env python3
"""Run lifecycle memory-quality scenarios through the public ``AgentMemory`` facade (#819).

A scenario is an isolated store. Its operations (``remember``, ``correct``, ``forget``) are
applied in order, each through ``AgentMemory.open(root, scope=<op scope>)``, and then each query
runs ``recall(query, budget=10)`` in its own scope. Expectations are read only to score the
returned refs; they never reach the runtime.

Scoring (fixed in the cohort's authoring brief):
- a query passes when every ``must_include`` ref is returned, no ``must_exclude`` ref is
  returned, and every returned ref is in ``must_include`` or ``may_include``;
- precision = returned refs in ``must_include`` or ``may_include``, over all returned refs;
- recall = returned ``must_include`` refs, over all ``must_include`` refs;
- a safety violation is any returned ``must_exclude`` ref whose reason is ``superseded``,
  ``forgotten`` or ``other_scope``.

A ``remember`` may also carry ``source_ref`` and a typed ``proposition``; they are forwarded
only when present. Corrections and forgets carry a qualified skill-evidence artifact, which ordinary PAMA requires
before it commits them. An operation that does not commit is recorded, never retried.

    python scripts/run_memory_quality_scenarios.py scenarios.json --output report.json \
        [--return-selection ranked_prefix]
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.memory import procedural_memory as pm  # noqa: E402

TENANT = "tenant:memory-quality"
ACTOR = "agent:memory-quality"
BUDGET = 10
SAFETY_REASONS = frozenset({"superseded", "forgotten", "other_scope"})


def _evidence(scope: str):
    skill = pm.SkillArtifact(
        skill_id="skill:memory-quality-lifecycle",
        version=1,
        purpose="apply a scenario's correction or deletion",
        scope=scope,
        isolation_domain_refs=(TENANT, scope),
        required_isolation_domain_refs=(TENANT, scope),
        procedure_markdown="# verify\nConfirm the lifecycle change against the scenario source.",
        provenance_refs=("evidence:memory-quality-scenario",),
    )
    return pm.evidence_for(skill)


def _open(root: Path, scope: str) -> AgentMemory:
    return AgentMemory.open(root, tenant=TENANT, actor_id=ACTOR, scope=scope, purpose="memory quality scenario")


def run_scenario(scenario: dict, return_selection: str | None) -> dict:
    by_uuid: dict[str, tuple[str, str]] = {}
    op_failures: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="agent-memory-quality-") as temporary:
        root = Path(temporary)
        for index, op in enumerate(scenario["operations"]):
            scope, ref = op["scope"], op["ref"]
            with _open(root, scope) as memory:
                if op["op"] == "remember":
                    kwargs = {"observed_at": op["observed_at"]} if op.get("observed_at") else {}
                    # Optional caller-declared structure, forwarded only when a scenario states it.
                    for key in ("source_ref", "proposition"):
                        if op.get(key):
                            kwargs[key] = op[key]
                    outcome = memory.remember(ref, op["text"], **kwargs)
                elif op["op"] == "correct":
                    outcome = memory.correct(ref, op["text"], evidence=_evidence(scope))
                elif op["op"] == "forget":
                    outcome = memory.forget(ref, evidence=_evidence(scope))
                else:
                    raise ValueError(f"unknown op {op['op']!r}")
            if outcome.get("committed") and outcome.get("fact_uuid"):
                by_uuid[str(outcome["fact_uuid"])] = (scope, ref)
            elif not outcome.get("committed"):
                op_failures.append({"index": index, "op": op["op"], "ref": ref,
                                    "outcome": outcome.get("outcome"), "refusal": outcome.get("refusal")})
        results = []
        for query in scenario["queries"]:
            kwargs = {"budget": BUDGET}
            if return_selection is not None:
                kwargs["return_selection"] = return_selection
            started = time.perf_counter()
            with _open(root, query["scope"]) as memory:
                recalled = memory.recall(query["query"], **kwargs)
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            returned = []
            for uuid in recalled.get("returned") or []:
                scope, ref = by_uuid.get(str(uuid), ("?", f"unmapped:{uuid}"))
                returned.append(ref if scope == query["scope"] else f"{scope}#{ref}")
            results.append(score(query, returned, len(recalled.get("admitted") or []), elapsed_ms))
    return {"id": scenario["id"], "category": scenario.get("category"), "op_failures": op_failures,
            "queries": results}


def score(query: dict, returned: list[str], admitted: int, elapsed_ms: float) -> dict:
    expect = query["expect"]
    must = list(dict.fromkeys(expect.get("must_include") or []))
    may = set(expect.get("may_include") or [])
    excluded = {item["ref"]: item.get("reason") for item in expect.get("must_exclude") or []}
    allowed = set(must) | may
    returned_set = set(returned)
    violations = sorted(ref for ref in returned_set if excluded.get(ref) in SAFETY_REASONS
                        or any(ref.endswith("#" + other) and reason == "other_scope"
                               for other, reason in excluded.items()))
    passed = (all(ref in returned_set for ref in must)
              and not any(ref in returned_set for ref in excluded)
              and returned_set <= allowed)
    return {
        "id": query["id"],
        "kind": "abstention" if not must else ("multi" if len(must) > 1 else "single"),
        "passed": passed,
        "precision": (len(returned_set & allowed) / len(returned_set)) if returned_set else None,
        "recall": (len(returned_set & set(must)) / len(must)) if must else None,
        "returned": returned,
        "returned_count": len(returned),
        "admitted_count": admitted,
        "must_include_count": len(must),
        "safety_violations": violations,
        "elapsed_ms": round(elapsed_ms, 3),
    }


def summarize(scenarios: list[dict]) -> dict:
    rows = [(s["category"], q) for s in scenarios for q in s["queries"]]

    def agg(items):
        precisions = [q["precision"] for _, q in items if q["precision"] is not None]
        recalls = [q["recall"] for _, q in items if q["recall"] is not None]
        return {
            "queries": len(items),
            "passed": sum(q["passed"] for _, q in items),
            "mean_precision": round(sum(precisions) / len(precisions), 4) if precisions else None,
            "mean_recall": round(sum(recalls) / len(recalls), 4) if recalls else None,
            "mean_returned": round(sum(q["returned_count"] for _, q in items) / len(items), 3) if items else None,
            "safety_violations": sum(len(q["safety_violations"]) for _, q in items),
        }

    by_category = defaultdict(list)
    by_kind = defaultdict(list)
    for category, query in rows:
        by_category[category].append((category, query))
        by_kind[query["kind"]].append((category, query))
    latencies = sorted(q["elapsed_ms"] for _, q in rows)
    return {
        "overall": agg(rows),
        "by_category": {k: agg(v) for k, v in sorted(by_category.items())},
        "by_kind": {k: agg(v) for k, v in sorted(by_kind.items())},
        "op_failures": sum(len(s["op_failures"]) for s in scenarios),
        "recall_latency_ms_p50": latencies[len(latencies) // 2] if latencies else None,
        "recall_latency_ms_p95": latencies[max(0, -(-95 * len(latencies) // 100) - 1)] if latencies else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("scenarios", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--return-selection", default=None)
    args = parser.parse_args()
    raw = args.scenarios.read_bytes()
    cohort = json.loads(raw)
    supports = "return_selection" in inspect.signature(AgentMemory.recall).parameters
    if args.return_selection is not None and not supports:
        raise SystemExit("this runtime has no return_selection parameter")
    scenarios = [run_scenario(s, args.return_selection) for s in cohort["scenarios"]]
    revision = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--", "reference"],
                           capture_output=True, text=True).stdout.strip()
    report = {
        "runner": "scripts/run_memory_quality_scenarios.py",
        "agent_memory_revision": revision,
        "reference_worktree_dirty": bool(dirty),
        "cohort_sha256": hashlib.sha256(raw).hexdigest(),
        "budget": BUDGET,
        "return_selection": args.return_selection,
        "summary": summarize(scenarios),
        "scenarios": scenarios,
    }
    args.output.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"]["overall"]), report["summary"]["op_failures"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
