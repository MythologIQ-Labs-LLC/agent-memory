"""Evaluate the preregistered mesa-formal-v4 predictions against the committed replay (#786).

The v4 freeze preregisters P1-P6 as a confirmation of mesa-formal-v3: the scope-host migration
changes key binding, handle serialization, timing and concurrency, not retrieval or admission
semantics. This script recomputes every prediction from committed files only (the v4 and v3
linked-only reports, the C7 ordering report regenerated at the execution runtime, and the v6
C7 report) and writes one record. It never reads the dataset and never edits a frozen record;
the evaluation is evidence for the v7 acceptance step, not acceptance, and has
``authority_effect: none``.

    PYTHONPATH=reference python reference/evaluate_mesa_formal_v4_predictions.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FREEZE = REPO / "reference" / "fixtures" / "benchmarks" / "agentmembench" / "mesa-formal-v4-freeze.json"
MESA = REPO / "reports" / "benchmarks" / "agentmembench-mesa-formal"
V4 = MESA / "agent_memory_formal_v4_s2027_9170.json"
V3 = MESA / "agent_memory_formal_v3_s2027_9170.json"
C7_DIR = REPO / "reports" / "runtime" / "cross-fact-currentness-671"
C7_V7 = C7_DIR / "ordering-difference-report-v7.json"
C7_V6 = C7_DIR / "ordering-difference-report-v6.json"
OUT = MESA / "mesa-formal-v4-prediction-evaluation.json"
LATENCY_MARKERS = ("latency", "_ms", "throughput", "wall")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _non_latency(value):
    if isinstance(value, dict):
        return {k: _non_latency(v) for k, v in value.items() if not any(marker in k for marker in LATENCY_MARKERS)}
    if isinstance(value, list):
        return [_non_latency(v) for v in value]
    return value


def evaluate() -> dict:
    freeze, v4, v3, c7, c7_v6 = _load(FREEZE), _load(V4), _load(V3), _load(C7_V7), _load(C7_V6)
    m4 = v4["agent_memory"]["m4_failure_classification"]
    predictions = freeze["predictions"]
    binding = v4["agent_memory"]["freeze"]
    p6_phases = {phase: _non_latency(v4["phases"][phase]) == _non_latency(v3["phases"][phase])
                 for phase in ("retrieval", "conflict", "isolation", "deletion", "scale", "concurrency")}
    checks = {
        "report_binds_this_freeze": binding["path"] == str(FREEZE.relative_to(REPO)) and binding["sha256"] == _sha256(FREEZE),
        "runtime_tree_is_the_frozen_tree": (v4["agent_memory"]["agent_memory_verification"]["runtime_tree"]
                                            == freeze["agent_memory"]["runtime_tree"]),
        "P1_outcomes": m4["outcomes"] == predictions["P1"]["m4_failure_classification.outcomes"],
        "P1_dual_version_rate": v4["phases"]["conflict"]["dual_version_rate"] == predictions["P1"]["phases.conflict.dual_version_rate"],
        "P2_win_basis": m4["win_basis_counts"] == predictions["P2"]["m4_failure_classification.win_basis_counts"],
        "P3_primary_stages": m4["primary_stage_counts"] == predictions["P3"]["m4_failure_classification.primary_stage_counts"],
        "P3_unmet_stages": m4["unmet_stage_counts"] == predictions["P3"]["m4_failure_classification.unmet_stage_counts"],
        "P4_no_guard_failure": (c7["blockers"] == [] and c7["comparison"]["m4_pairs"] == 250
                                and c7["comparison"]["m4_limited"] == 250 and c7["comparison"]["m4_refusals"] == {}),
        "P5_upstream_consistent": m4["upstream_consistency"]["consistent"] is predictions["P5"][
            "m4_failure_classification.upstream_consistency.consistent"],
        "P6_retrieved_digests": ([row["retrieved"] for row in v4["phases"]["retrieval"]["details"]]
                                 == [row["retrieved"] for row in v3["phases"]["retrieval"]["details"]]),
        **{f"P6_{phase}_non_latency": equal for phase, equal in p6_phases.items()},
    }
    return {
        "schema_version": 1,
        "evidence_id": "mesa-formal-v4-prediction-evaluation",
        "freeze_id": freeze["freeze_id"],
        "freeze_sha256": _sha256(FREEZE),
        "executed_at": v4["agent_memory"]["agent_memory_verification"]["revision"],
        "runtime_tree": v4["agent_memory"]["agent_memory_verification"]["runtime_tree"],
        "environment": {"python": v4["agent_memory"]["identity"]["python"],
                        "packages": v4["agent_memory"]["agent_memory_verification"]["packages"]},
        "upstream": v4["agent_memory"]["upstream_verification"],
        "inputs_sha256": {str(path.relative_to(REPO)): _sha256(path) for path in (V4, V3, C7_V7, C7_V6)},
        "c7_equal_to_v6_c7": c7 == c7_v6,
        "checks": checks,
        "all_predictions_hold": all(checks.values()),
        "on_miss": predictions["on_miss"],
        "reported_only": {
            "phase_wall_seconds": {"v3": v3["agent_memory"]["phase_wall_seconds"], "v4": v4["agent_memory"]["phase_wall_seconds"]},
            "concurrency_throughput_ops_s": {
                workers: {"v3": v3["phases"]["concurrency"][workers]["throughput_ops_s"],
                          "v4": v4["phases"]["concurrency"][workers]["throughput_ops_s"]}
                for workers in sorted(v4["phases"]["concurrency"], key=int)},
        },
        "runner_label": v4["agent_memory"]["scope_binding_migration"],
        "judge": "M2 judged recall stays blocked (deviation D1): no authorized judge is provisioned",
        "status": "replay executed under the refrozen v4 identity; predictions evaluated; not benchmark acceptance",
        "authority_effect": "none",
    }


def main() -> int:
    record = evaluate()
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for name, ok in record["checks"].items():
        print(f"{'ok  ' if ok else 'MISS'} {name}")
    print(f"all predictions hold: {record['all_predictions_hold']} -> {OUT.relative_to(REPO)}")
    return 0 if record["all_predictions_hold"] else 1


if __name__ == "__main__":
    sys.exit(main())
