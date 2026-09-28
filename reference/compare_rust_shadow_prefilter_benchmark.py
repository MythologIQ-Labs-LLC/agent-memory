from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

EXPECTED_CONTRACT = "591_identity_first_prefilter_compute_v1"


def load(path: Path, implementation: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("contract") != EXPECTED_CONTRACT:
        raise ValueError(f"{path}: unexpected contract {payload.get('contract')!r}")
    if payload.get("implementation") != implementation:
        raise ValueError(f"{path}: expected implementation {implementation!r}")
    if payload.get("authority_effect") != "none":
        raise ValueError(f"{path}: benchmark output must have no authority effect")
    return payload


def median_metric(runs: list[dict], key: str) -> float:
    return float(statistics.median(float(run[key]) for run in runs))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", type=Path, nargs=2, required=True)
    parser.add_argument("--rust", type=Path, nargs=2, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    python_runs = [load(path, "python") for path in args.python]
    rust_runs = [load(path, "rust") for path in args.rust]
    runs = python_runs + rust_runs

    identity = {(run["rows"], run["queries"], run["iterations"], run["sample_count"]) for run in runs}
    if len(identity) != 1:
        raise SystemExit(f"workload identity mismatch: {sorted(identity)}")

    signatures = {run["result_signature_sha256"] for run in runs}
    if len(signatures) != 1:
        raise SystemExit(f"RESULT PARITY FAILURE: signatures differ: {sorted(signatures)}")

    python_total = median_metric(python_runs, "total_ms")
    rust_total = median_metric(rust_runs, "total_ms")
    python_throughput = median_metric(python_runs, "projected_rows_examined_per_second")
    rust_throughput = median_metric(rust_runs, "projected_rows_examined_per_second")

    rows, queries, iterations, sample_count = next(iter(identity))
    summary = {
        "schema_version": 1,
        "contract": EXPECTED_CONTRACT,
        "evidence_class": "matched_ci_hot_path_performance",
        "platform_scope": "same_ubuntu_github_actions_job",
        "workload": {
            "rows": rows,
            "queries": queries,
            "iterations_per_run": iterations,
            "query_samples_per_run": sample_count,
            "execution_orders": ["python_then_rust", "rust_then_python"],
            "timing_scope": "prefilter_compute_only_rows_prebuilt",
            "rust_compile_time_included": False,
        },
        "result_parity": {
            "status": "PASS",
            "signature_sha256": next(iter(signatures)),
        },
        "python": {
            "median_total_ms": python_total,
            "median_p50_query_ms": median_metric(python_runs, "p50_query_ms"),
            "median_p95_query_ms": median_metric(python_runs, "p95_query_ms"),
            "median_projected_rows_examined_per_second": python_throughput,
            "individual_total_ms": [float(run["total_ms"]) for run in python_runs],
        },
        "rust": {
            "median_total_ms": rust_total,
            "median_p50_query_ms": median_metric(rust_runs, "p50_query_ms"),
            "median_p95_query_ms": median_metric(rust_runs, "p95_query_ms"),
            "median_projected_rows_examined_per_second": rust_throughput,
            "individual_total_ms": [float(run["total_ms"]) for run in rust_runs],
        },
        "relative": {
            "rust_speedup_by_total_time": python_total / rust_total if rust_total else None,
            "rust_throughput_multiple": rust_throughput / python_throughput if python_throughput else None,
        },
        "qualification": [
            "same deterministic generated workload",
            "same CI job/runner",
            "result signature equality required before timing comparison",
            "two execution orders to reduce first/second-run bias",
            "micro/hot-path evidence only; not full-runtime performance",
        ],
        "authority_effect": "none",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
