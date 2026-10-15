"""Calibrate the C5 semantic floors on the self-authored development set (never on held-out data).

1. Run every dev scenario once through the public facade with the semantic route enabled
   (``required``), capturing each recall's selection inputs (ranked admitted list, routes, fact
   texts, similarities) at the facade's call into ``select_relevance_sufficient``.
2. Replay only the selection stage for every point of the preregistered grid
   (tau in {0.30, ..., 0.50}, delta in {0.05, ..., 0.30}, tau_set <= tau_abs,
   delta_set >= delta_single + 0.05; erratum 3), apply the budget, and score with the
   held-out runner's own ``score``.
3. Choose the point with the most dev strict passes subject to the preregistered constraint
   (dev precision >= C4-semantic-on dev precision - 0.05); ties go to higher dev recall, then
   higher precision, then the more conservative point (higher floors, then smaller margins).
   (Erratum 2: the first run's conservative-first tie-break chose a 27-pass point with recall
   0.575 although 27-pass points with recall 0.775 existed; recall is the hypothesis' target.) The C4-equivalent replay (semantic channel off, the
   route's candidates unconditional) is the reference.

    AGENT_MEMORY_REPRESENTATION_DIR=<pinned model> python calibrate.py dev-scenarios.json --output calibration.json
"""

from __future__ import annotations

import argparse
import importlib.util
import itertools
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref.api import surface  # noqa: E402
from agentmem_ref.runtime import return_selection as rs  # noqa: E402

_spec = importlib.util.spec_from_file_location("runner", ROOT / "scripts" / "run_memory_quality_scenarios.py")
runner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(runner)

# Erratum 3: floors at or above the semantic route's discovery floor (0.30).
TAUS = [round(0.30 + 0.05 * i, 2) for i in range(5)]
DELTAS = [round(0.05 + 0.05 * i, 2) for i in range(6)]


class _Fact:
    def __init__(self, text: str) -> None:
        self.fact_text = text


def capture(scenarios: list[dict]) -> list[dict]:
    """One row per dev query: its expectation, uuid->ref map and captured selection inputs."""
    holder: dict = {}
    real = surface.select_relevance_sufficient

    def recorder(ranked, routes, lookup, **kwargs):
        holder["record"] = {
            "ranked": list(ranked),
            "routes": {ref: list(value) for ref, value in routes.items()},
            "texts": {ref: getattr(lookup(ref), "fact_text", "") or "" for ref in ranked},
            "successors": {ref: list(v) for ref, v in (kwargs.pop("lifecycle_successors", None) or {}).items()},
            "kwargs": kwargs,
        }
        return real(ranked, routes, lookup, lifecycle_successors=holder["record"]["successors"], **kwargs)

    surface.select_relevance_sufficient = recorder
    runner.SEMANTIC_RETRIEVAL = "required"
    rows: list[dict] = []
    try:
        for scenario in scenarios:
            by_uuid: dict[str, tuple[str, str]] = {}
            with tempfile.TemporaryDirectory(prefix="c5-calibration-") as temporary:
                root = Path(temporary)
                for op in scenario["operations"]:
                    with runner._open(root, op["scope"]) as memory:
                        if op["op"] == "remember":
                            kwargs = {"observed_at": op["observed_at"]} if op.get("observed_at") else {}
                            outcome = memory.remember(op["ref"], op["text"], **kwargs)
                        elif op["op"] == "correct":
                            outcome = memory.correct(op["ref"], op["text"], evidence=runner._evidence(op["scope"]))
                        else:
                            outcome = memory.forget(op["ref"], evidence=runner._evidence(op["scope"]))
                    if outcome.get("committed") and outcome.get("fact_uuid"):
                        by_uuid[str(outcome["fact_uuid"])] = (op["scope"], op["ref"])
                for query in scenario["queries"]:
                    holder.clear()
                    with runner._open(root, query["scope"]) as memory:
                        memory.recall(query["query"], budget=runner.BUDGET)
                    rows.append({"scenario": scenario["id"], "query": query, "record": holder.get("record"),
                                 "by_uuid": dict(by_uuid)})
    finally:
        surface.select_relevance_sufficient = real
        runner.SEMANTIC_RETRIEVAL = None
    return rows


def returned_refs(row: dict, uuids: list[str]) -> list[str]:
    out = []
    for uuid in uuids:
        scope, ref = row["by_uuid"].get(uuid, ("?", f"unmapped:{uuid}"))
        out.append(ref if scope == row["query"]["scope"] else f"{scope}#{ref}")
    return out


def replay(row: dict, point: tuple[float, float, float, float] | None) -> list[str]:
    """Selection at a grid point; ``None`` replays C4 (no semantic channel: route candidates unconditional)."""
    record = row["record"]
    if record is None:
        return []
    saved = (rs.SEMANTIC_ABSOLUTE_FLOOR, rs.SEMANTIC_SINGLE_MARGIN, rs.SEMANTIC_SET_FLOOR, rs.SEMANTIC_SET_MARGIN)
    kwargs = dict(record["kwargs"])
    if point is None:
        kwargs["semantic_similarity"] = None
    else:
        rs.SEMANTIC_ABSOLUTE_FLOOR, rs.SEMANTIC_SINGLE_MARGIN, rs.SEMANTIC_SET_FLOOR, rs.SEMANTIC_SET_MARGIN = point
    try:
        selected, _, _ = rs.select_relevance_sufficient(
            record["ranked"], record["routes"], lambda ref: _Fact(record["texts"][ref]),
            lifecycle_successors=record["successors"], **kwargs)
    finally:
        rs.SEMANTIC_ABSOLUTE_FLOOR, rs.SEMANTIC_SINGLE_MARGIN, rs.SEMANTIC_SET_FLOOR, rs.SEMANTIC_SET_MARGIN = saved
    return returned_refs(row, selected[:runner.BUDGET])


def evaluate(rows: list[dict], point) -> dict:
    scored = [runner.score(row["query"], replay(row, point), len((row["record"] or {}).get("ranked", [])), 0.0) for row in rows]
    precision = [s["precision"] for s in scored if s["precision"] is not None]
    recall = [s["recall"] for s in scored if s["recall"] is not None]
    low_overlap = [s["recall"] for row, s in zip(rows, scored) if s["recall"] is not None]
    return {
        "passed": sum(s["passed"] for s in scored),
        "queries": len(scored),
        "mean_precision": round(sum(precision) / len(precision), 4) if precision else None,
        "mean_recall": round(sum(recall) / len(recall), 4) if recall else None,
        "mean_returned": round(sum(s["returned_count"] for s in scored) / len(scored), 3),
        "safety_violations": sum(len(s["safety_violations"]) for s in scored),
        "per_query": {row["query"]["id"]: s["passed"] for row, s in zip(rows, scored)},
        "low_overlap_recall": round(sum(low_overlap) / len(low_overlap), 4) if low_overlap else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("scenarios", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cohort = json.loads(args.scenarios.read_text())
    rows = capture(cohort["scenarios"] if isinstance(cohort, dict) else cohort)
    reference = evaluate(rows, None)
    floor = reference["mean_precision"] - 0.05
    grid = []
    for tau_abs, d_single, tau_set, d_set in itertools.product(TAUS, DELTAS, TAUS, DELTAS):
        if tau_set > tau_abs or d_set < d_single + 0.05 - 1e-9:
            continue  # erratum 3: the set channel is looser than the single-answer channel
        result = evaluate(rows, (tau_abs, d_single, tau_set, d_set))
        grid.append({"point": [tau_abs, d_single, tau_set, d_set], **{k: v for k, v in result.items() if k != "per_query"}})
    eligible = [g for g in grid if g["mean_precision"] is not None and g["mean_precision"] >= floor and g["safety_violations"] == 0]
    eligible.sort(key=lambda g: (-g["passed"], -g["mean_recall"], -g["mean_precision"],
                                 -g["point"][0], g["point"][1], -g["point"][2], g["point"][3]))
    chosen = eligible[0] if eligible else None
    failing = []
    if chosen:
        detail = evaluate(rows, tuple(chosen["point"]))["per_query"]
        failing = sorted(qid for qid, passed in detail.items() if not passed)
    report = {
        "failing_dev_queries_at_chosen": failing,
        "reference_c4_semantic_on": {k: v for k, v in reference.items() if k != "per_query"},
        "precision_constraint": round(floor, 4),
        "grid_size": len(grid),
        "chosen": chosen,
        "top10": eligible[:10],
        "grid": grid,
    }
    args.output.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({"reference": report["reference_c4_semantic_on"], "chosen": chosen}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
