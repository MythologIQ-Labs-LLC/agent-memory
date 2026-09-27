#!/usr/bin/env python3
"""Measure #572 recall-decision validation cost without changing runtime policy.

The runner compares two validation implementations on the same governed recall
workload:

* ``canonical``: the pre-#572 Draft 2020-12 jsonschema oracle;
* ``fast``: the schema-bound built-in recall-decision validator used by #572.

Both modes execute the same ``GovernedMemoryAdapter.governed_recall`` path over
the same seeded adapter.  The runner is evidence only: it never changes the
candidate policy, admission policy, ranking policy, or persisted memory state.
Timing is observational and is never an authority or conformance signal.
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agentmem_ref.core import receipts  # noqa: E402
from agentmem_ref.harness.systems_characterization import _seed_substrate  # noqa: E402

QUERY = "systems characterization"


def _summary(samples: list[int]) -> dict[str, int]:
    return {
        "samples": len(samples),
        "minimum_ns": min(samples),
        "median_ns": int(statistics.median(samples)),
        "maximum_ns": max(samples),
    }


def _normalized_decisions(decisions: dict[str, dict]) -> dict[str, dict]:
    """Remove only generated observation identity/time for semantic comparison."""

    normalized: dict[str, dict] = {}
    for candidate_ref, decision in decisions.items():
        item = deepcopy(decision)
        item.pop("decision_id", None)
        item.pop("evaluated_at", None)
        normalized[candidate_ref] = item
    return normalized


def _semantic_snapshot(result) -> dict:
    return {
        "candidates": list(result.candidates),
        "admitted": list(result.admitted),
        "refusals": dict(result.refusals),
        "admission_basis": deepcopy(result.admission_basis),
        "admission_mode": result.admission_mode,
        "candidate_policy": deepcopy(result.candidate_policy),
        "decisions": _normalized_decisions(result.decisions),
    }


def _recall_once(adapter, *, fast: bool):
    # Patching only the implementation selector reproduces the pre-#572
    # canonical path while leaving candidate generation and admission untouched.
    with patch.object(receipts, "_builtin_recall_fastpath_enabled", return_value=fast):
        started = time.perf_counter_ns()
        result = adapter.governed_recall(QUERY)
        elapsed = time.perf_counter_ns() - started
    return elapsed, result


def _validation_totals(decisions: list[dict], repeats: int) -> tuple[dict, dict]:
    canonical_samples: list[int] = []
    fast_samples: list[int] = []

    # Warm both code paths before measuring.  The jsonschema validator is already
    # cached in production; this avoids timing one-time schema loading as if it
    # were per-candidate work.
    for decision in decisions[:1]:
        receipts._validate_with_jsonschema("contextual-recall-admission.schema.json", decision)
        receipts.validate("contextual-recall-admission.schema.json", decision)

    for repeat in range(repeats):
        modes = ("canonical", "fast") if repeat % 2 == 0 else ("fast", "canonical")
        for mode in modes:
            started = time.perf_counter_ns()
            if mode == "canonical":
                for decision in decisions:
                    receipts._validate_with_jsonschema(
                        "contextual-recall-admission.schema.json", decision
                    )
            else:
                for decision in decisions:
                    receipts.validate("contextual-recall-admission.schema.json", decision)
            elapsed = time.perf_counter_ns() - started
            (canonical_samples if mode == "canonical" else fast_samples).append(elapsed)

    canonical = _summary(canonical_samples)
    fast = _summary(fast_samples)
    count = len(decisions)
    canonical["mean_per_candidate_ns_from_median_total"] = canonical["median_ns"] // count
    fast["mean_per_candidate_ns_from_median_total"] = fast["median_ns"] // count
    return canonical, fast


def characterize_size(size: int, repeats: int) -> dict:
    _, adapter = _seed_substrate(size)

    # Warm both recall paths.  Alternating measured order below reduces runner
    # drift and keeps both modes on the same in-memory workload.
    _, canonical_warm = _recall_once(adapter, fast=False)
    _, fast_warm = _recall_once(adapter, fast=True)
    if _semantic_snapshot(canonical_warm) != _semantic_snapshot(fast_warm):
        raise RuntimeError(f"semantic divergence during warmup at size={size}")

    canonical_samples: list[int] = []
    fast_samples: list[int] = []
    canonical_snapshot = None
    fast_snapshot = None
    latest_fast = fast_warm

    for repeat in range(repeats):
        modes = (False, True) if repeat % 2 == 0 else (True, False)
        for fast in modes:
            elapsed, result = _recall_once(adapter, fast=fast)
            snapshot = _semantic_snapshot(result)
            if fast:
                fast_samples.append(elapsed)
                latest_fast = result
                if fast_snapshot is None:
                    fast_snapshot = snapshot
                elif fast_snapshot != snapshot:
                    raise RuntimeError(f"fast recall changed semantics across repeats at size={size}")
            else:
                canonical_samples.append(elapsed)
                if canonical_snapshot is None:
                    canonical_snapshot = snapshot
                elif canonical_snapshot != snapshot:
                    raise RuntimeError(
                        f"canonical recall changed semantics across repeats at size={size}"
                    )

    if canonical_snapshot != fast_snapshot:
        raise RuntimeError(f"canonical/fast semantic divergence at size={size}")

    decisions = list(latest_fast.decisions.values())
    canonical_validation, fast_validation = _validation_totals(decisions, repeats)
    canonical_recall = _summary(canonical_samples)
    fast_recall = _summary(fast_samples)

    return {
        "retained_facts": size,
        "candidate_count": len(latest_fast.candidates),
        "admitted_count": len(latest_fast.admitted),
        "semantic_identity": True,
        "canonical_recall": canonical_recall,
        "fast_recall": fast_recall,
        "recall_median_speedup": round(
            canonical_recall["median_ns"] / fast_recall["median_ns"], 4
        ),
        "canonical_validation": canonical_validation,
        "fast_validation": fast_validation,
        "validation_median_speedup": round(
            canonical_validation["median_ns"] / fast_validation["median_ns"], 4
        ),
    }


def build_report(revision: str, sizes: tuple[int, ...], repeats: int) -> dict:
    if len(revision) != 40:
        raise ValueError("revision must be an exact 40-character commit SHA")
    if not sizes or any(size <= 0 for size in sizes):
        raise ValueError("sizes must contain positive integers")
    if tuple(sorted(set(sizes))) != sizes:
        raise ValueError("sizes must be unique and strictly increasing")
    if repeats < 1:
        raise ValueError("repeats must be positive")
    if not receipts._builtin_recall_fastpath_enabled():
        raise RuntimeError(
            "#572 fast path is not bound to the current canonical contextual recall schema"
        )

    rows = [characterize_size(size, repeats) for size in sizes]
    return {
        "profile": "agent-memory-recall-validation-scaling",
        "version": "1.0.0",
        "revision": revision,
        "schema_blob_sha": receipts._CONTEXTUAL_RECALL_SCHEMA_BLOB_SHA,
        "runner": {
            "python": sys.version.split()[0],
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "method": {
            "sizes": list(sizes),
            "timing_repeats": repeats,
            "canonical_mode": "receipts._validate_with_jsonschema per candidate",
            "fast_mode": "schema-bound receipts.validate dispatch per candidate",
            "same_seeded_adapter_per_size": True,
            "semantic_identity_required": True,
            "timing_is_observational_only": True,
            "timing_is_not_authority": True,
            "candidate_policy_changed": False,
            "admission_policy_changed": False,
            "ranking_policy_changed": False,
        },
        "rows": rows,
        "all_semantics_identical": all(row["semantic_identity"] for row in rows),
        "claim_boundary": [
            "reference-runtime characterization, not universal production performance",
            "canonical mode reproduces the pre-#572 validator implementation on the same revision",
            "timing values are runner-specific observations",
            "performance does not create or widen recall authority",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--sizes", default="100,1000,5000,10000")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output")
    args = parser.parse_args()

    sizes = tuple(int(value.strip()) for value in args.sizes.split(",") if value.strip())
    report = build_report(args.revision, sizes, args.repeats)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["all_semantics_identical"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
