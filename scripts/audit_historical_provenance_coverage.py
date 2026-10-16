#!/usr/bin/env python3
"""#808 item 6: which v1 envelope fields the historical normalized runs actually captured.

Read-only. For every ``reports/benchmarks/normalized/*.json`` (and its committed
``execution_identity`` artifact, when one exists) each envelope field family is classified as:

* ``recorded`` - a machine-captured value is committed for this run;
* ``not_recorded`` - the field was not captured; it must stay absent, never be backfilled;
* ``evidence_gap`` - acceptance under the v1 envelope would need it, and nothing committed
  can supply it;
* ``not_applicable`` - model identity for a system kind that runs no model (lexical, no_memory).

Nothing is inferred from lane declarations or defaults. Output is JSON on stdout.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FOR_ACCEPTANCE = {"hardware.cpu_ram_gpu", "execution.stdout_stderr_digests", "costs", "inference.model_identity"}


def _identity(run: dict) -> dict:
    for artifact in run["artifacts"]:
        if artifact["kind"] == "execution_identity" and artifact.get("uri"):
            path = ROOT / artifact["uri"]
            if path.is_file():
                return json.loads(path.read_text(encoding="utf-8"))
    return {}


def coverage(run: dict) -> dict:
    execution, env, ident = run["execution"], run["execution"].get("environment") or {}, _identity(run)
    kinds = {a["kind"]: bool(a.get("sha256")) for a in run["artifacts"]}

    def state(present: bool, family: str) -> str:
        if family == "inference.model_identity" and run["system"].get("kind") in ("lexical", "no_memory"):
            return "not_applicable"
        return "recorded" if present else ("evidence_gap" if family in REQUIRED_FOR_ACCEPTANCE else "not_recorded")

    families = {
        "benchmark.input_sha256": bool(run["benchmark"].get("input_sha256")),
        "benchmark.dataset_revision": run["benchmark"].get("dataset_revision") not in (None, "", "unrecorded"),
        "system.revision": bool(run["system"].get("revision")),
        "system.adapter_revision": bool(run["system"].get("adapter_revision")),
        "system.configuration_digest": bool(run["system"].get("configuration_digest")),
        "timing.started_at_elapsed": bool(execution.get("started_at")) and execution.get("elapsed_ms") is not None,
        "timing.finished_at": False,
        "hardware.os": bool(env.get("platform") or env.get("runner")),
        "hardware.cpu_ram_gpu": False,
        "environment.runtime_version": bool(env.get("python")),
        "environment.dependency_lock": bool(env.get("resolved_packages") or env.get("harness_lock_git_blob") or ident.get("resolved_packages")),
        "environment.container_digest": False,
        "execution.source_blobs": bool(ident.get("source_blobs")),
        "execution.workflow_run_id": bool(ident.get("workflow_run_id")),
        "execution.seed": "seed" in execution,
        "execution.peak_memory": bool(env.get("resource_consumption")),
        "execution.stdout_stderr_digests": False,
        "inference.model_identity": False,
        "costs": False,
        "artifacts.native_result_sha256": kinds.get("benchmark_native_results", False),
        "artifacts.row_level_sha256": kinds.get("row_level_rankings", False),
    }
    return {family: state(present, family) for family, present in families.items()}


def main() -> int:
    runs = sorted((ROOT / "reports/benchmarks/normalized").glob("*.json"))
    per_run, totals, by_lane = {}, defaultdict(Counter), defaultdict(lambda: defaultdict(Counter))
    for path in runs:
        run = json.loads(path.read_text(encoding="utf-8"))
        result = coverage(run)
        per_run[path.name] = result
        lane = run["benchmark"].get("task_profile", "?").rsplit(":", 1)[0]
        for family, value in result.items():
            totals[family][value] += 1
            by_lane[lane][family][value] += 1
    print(json.dumps({"normalized_runs": len(runs),
                      "totals": {k: dict(v) for k, v in sorted(totals.items())},
                      "by_profile": {lane: {k: dict(v) for k, v in sorted(f.items())} for lane, f in sorted(by_lane.items())},
                      "per_run": per_run}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
