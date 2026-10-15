"""Calibrate the C6 rank-bounded proposal policy on the self-authored development union.

Each development store is built once through the public facade with the semantic route enabled
(``required``, pinned local model). Its handle stays open, and every grid point sets the live
retriever's ``proposal_policy`` (harness only). Each query then runs through ``recall`` and is
scored with the held-out runner's own ``score``. No held-out cohort, benchmark gold or other
user's content is read.

``policy=None`` is C4's semantic route (absolute 0.30 floor, at most 16, no pool restriction) on
the same runtime; selection and admission are identical, so it is the C4-semantic-on reference.

    AGENT_MEMORY_REPRESENTATION_DIR=<pinned model> python calibrate.py --output calibration.json
"""

from __future__ import annotations

import argparse
import importlib.util
import itertools
import json
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref.runtime.vector_retrieval import RankBoundedProposalPolicy  # noqa: E402

_spec = importlib.util.spec_from_file_location("runner", ROOT / "scripts" / "run_memory_quality_scenarios.py")
runner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(runner)
runner.SEMANTIC_RETRIEVAL = "required"

SETS = ("diag-scenarios.json", "c5-dev-scenarios.json")
GRID = dict(k_single=(1, 2, 3), k_set=(2, 3, 4, 6), margin=(0.05, 0.10, 0.15, 0.20), min_best=(0.30, 0.35, 0.40, 0.45))


def build(scenarios, folder: Path):
    """Write every scenario's operations; return [(scenario, root, {uuid: (scope, ref)})]."""
    stores = []
    for index, scenario in enumerate(scenarios):
        root = folder / f"s{index}"
        by_uuid = {}
        for op in scenario["operations"]:
            with runner._open(root, op["scope"]) as memory:
                if op["op"] == "remember":
                    kwargs = {"observed_at": op["observed_at"]} if op.get("observed_at") else {}
                    out = memory.remember(op["ref"], op["text"], **kwargs)
                elif op["op"] == "correct":
                    out = memory.correct(op["ref"], op["text"], evidence=runner._evidence(op["scope"]))
                else:
                    out = memory.forget(op["ref"], evidence=runner._evidence(op["scope"]))
            if out.get("committed") and out.get("fact_uuid"):
                by_uuid[str(out["fact_uuid"])] = (op["scope"], op["ref"])
        stores.append((scenario, root, by_uuid))
    return stores


def evaluate(handles, policy) -> dict:
    scored, latencies = [], []
    for scenario, by_uuid, memories in handles:
        for query in scenario["queries"]:
            memory = memories[query["scope"]]
            memory._semantic["retriever"].proposal_policy = policy
            started = time.perf_counter()
            result = memory.recall(query["query"], budget=runner.BUDGET)
            latencies.append((time.perf_counter() - started) * 1000)
            returned = []
            for uuid in result.get("returned") or []:
                scope, ref = by_uuid.get(str(uuid), ("?", f"unmapped:{uuid}"))
                returned.append(ref if scope == query["scope"] else f"{scope}#{ref}")
            row = runner.score(query, returned, len(result.get("admitted") or []), 0.0)
            expect = query["expect"]
            allowed = set(expect.get("must_include") or []) | set(expect.get("may_include") or [])
            row["extra"] = len([r for r in returned if r not in allowed])
            row["no_answer_broken"] = (not expect.get("must_include")) and bool(set(returned) - allowed)
            row["needed"] = len(expect.get("must_include") or [])
            row["needed_returned"] = len(set(returned) & set(expect.get("must_include") or []))
            scored.append(row)
    latencies.sort()
    return {
        "strict": sum(r["passed"] for r in scored),
        "queries": len(scored),
        "needed_recall": round(sum(r["needed_returned"] for r in scored) / max(sum(r["needed"] for r in scored), 1), 4),
        "extra": sum(r["extra"] for r in scored),
        "no_answer_broken": sum(r["no_answer_broken"] for r in scored),
        "safety_violations": sum(len(r["safety_violations"]) for r in scored),
        "recall_p50_ms": round(latencies[len(latencies) // 2], 1),
        "per_query": {r["id"]: r["passed"] for r in scored},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    scenarios = []
    for name in SETS:
        cohort = json.loads((HERE / name).read_text())
        for scenario in cohort["scenarios"]:
            scenarios.append({**scenario, "id": f"{name.split('-')[0]}:{scenario['id']}",
                              "queries": [{**q, "id": f"{name.split('-')[0]}:{q['id']}"} for q in scenario["queries"]]})
    with tempfile.TemporaryDirectory(prefix="c6-calibration-") as tmp:
        stores = build(scenarios, Path(tmp))
        handles = []
        try:
            for scenario, root, by_uuid in stores:
                scopes = {q["scope"] for q in scenario["queries"]}
                handles.append((scenario, by_uuid, {scope: runner._open(root, scope) for scope in scopes}))
            reference = evaluate(handles, None)
            grid = []
            for k_single, k_set, margin, min_best in itertools.product(*GRID.values()):
                if k_set < k_single:
                    continue
                policy = RankBoundedProposalPolicy(min_best=min_best, margin=margin, k_single=k_single, k_set=k_set)
                result = evaluate(handles, policy)
                grid.append({"point": policy.to_dict(), **{k: v for k, v in result.items() if k != "per_query"}})
        finally:
            for _, _, memories in handles:
                for memory in memories.values():
                    memory.close()
    def order(g):
        p = g["point"]
        return (-g["strict"], -g["needed_recall"], g["extra"], p["k_single"], p["k_set"], -p["min_best"], p["margin"])
    grid.sort(key=order)
    report = {"reference_c4_semantic_on": {k: v for k, v in reference.items() if k != "per_query"},
              "reference_per_query": reference["per_query"], "grid_size": len(grid), "chosen": grid[0], "grid": grid}
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({"reference": report["reference_c4_semantic_on"], "chosen": grid[0], "next": grid[1:6]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
