"""Build a #808 v1 benchmark-execution manifest for one comparator run (candidate evidence only).

Inputs are files this session produced: the runner/driver report or rows, the run_logged
exec record (argv, exit, wall, peak RSS), stdout/stderr, the frozen pip freeze, and a small
system descriptor. Nothing is inferred that was not measured; unknowns are null.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import statistics
from pathlib import Path


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cpu_model() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "unknown"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-id", required=True)
    p.add_argument("--normalized", type=Path, required=True, help="summary/report JSON scored by the frozen evaluator")
    p.add_argument("--rows", type=Path, help="row-level JSONL when separate from --normalized")
    p.add_argument("--exec-record", type=Path, required=True)
    p.add_argument("--stdout", type=Path, required=True)
    p.add_argument("--stderr", type=Path, required=True)
    p.add_argument("--freeze", type=Path, required=True)
    p.add_argument("--system", type=Path, required=True, help="JSON: id, revision, adapter_id, adapter_revision, configuration, calls, notes, limitations, network_access")
    p.add_argument("--plane", required=True)
    p.add_argument("--sample-count", type=int, required=True)
    p.add_argument("--excluded-count", type=int, required=True)
    p.add_argument("--selection-id", required=True)
    p.add_argument("--input-sha256", required=True)
    p.add_argument("--evaluator-revision", required=True)
    p.add_argument("--latencies-ms", type=Path, help="JSON list of per-question latencies")
    p.add_argument("--uri-root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    ex = json.loads(a.exec_record.read_text())
    system = json.loads(a.system.read_text())
    config_bytes = json.dumps(system["configuration"], sort_keys=True, separators=(",", ":")).encode()
    lat = json.loads(a.latencies_ms.read_text()) if a.latencies_ms else []

    def rel(path: Path) -> str:
        return os.path.relpath(path.resolve(), a.uri_root.resolve())

    def pct(values, q):
        if not values:
            return None
        values = sorted(values)
        return round(values[min(len(values) - 1, int(round(q * (len(values) - 1))))], 3)

    from datetime import datetime, timedelta, timezone
    started = datetime.strptime(ex["started_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    finished = started + timedelta(seconds=ex["wall_seconds"])
    if a.rows:  # summary and rows are separate files
        artifacts = [{"kind": "evaluator_report", "uri": rel(a.normalized), "sha256": sha(a.normalized)},
                     {"kind": "row_level_results", "uri": rel(a.rows), "sha256": sha(a.rows)}]
    else:  # the frozen runner's report carries the per-question rows itself
        artifacts = [{"kind": "row_level_results", "uri": rel(a.normalized), "sha256": sha(a.normalized)}]
    for kind, path in (("execution_log", a.exec_record), ("execution_log", a.stdout), ("execution_log", a.stderr), ("other", a.freeze)):
        artifacts.append({"kind": kind, "uri": rel(path), "sha256": sha(path)})
    manifest = {
        "schema_version": "1.0.0",
        "run_id": a.run_id,
        "normalized_run": {"uri": rel(a.normalized), "sha256": sha(a.normalized)},
        "benchmark": {"id": "longmemeval-s-retrieval", "task_profile": f"longmemeval-s-retrieval-parity-v1:{a.plane}",
                      "dataset_revision": "xiaowu0162/longmemeval-cleaned longmemeval_s_cleaned.json",
                      "input_sha256": a.input_sha256, "selection_id": a.selection_id,
                      "sample_count": a.sample_count, "evaluator_revision": a.evaluator_revision,
                      "excluded_count": a.excluded_count},
        "system": {"id": system["id"], "revision": system["revision"], "adapter_id": system["adapter_id"],
                   "adapter_revision": system["adapter_revision"],
                   "configuration_sha256": hashlib.sha256(config_bytes).hexdigest(),
                   "worktree_clean": bool(system.get("worktree_clean", True)), "build_sha256": None},
        "timing": {"started_at": started.isoformat().replace("+00:00", "Z"),
                   "finished_at": finished.isoformat().replace("+00:00", "Z"),
                   "elapsed_ms": int(round(ex["wall_seconds"] * 1000))},
        "hardware": {"os": platform.system(), "os_release": platform.release(), "architecture": platform.machine(),
                     "cpu_model": cpu_model(), "cpu_cores": os.cpu_count(),
                     "ram_bytes": os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"), "gpus": []},
        "environment": {"runtime": "CPython", "runtime_version": system.get("python", platform.python_version()),
                        "isolation": "cloud_sandbox", "container_digest": None,
                        "dependency_lock_sha256": sha(a.freeze), "network_access": system.get("network_access", "restricted"),
                        "notes": system.get("notes", []) + ["execution.timeout_ms 0 = no runner-level timeout (per-call product timeouts recorded in configuration where they exist)."]},
        "inference": {"used": bool(system.get("calls")), "calls": system.get("calls", [])},
        "execution": {"command_sha256": hashlib.sha256("\0".join(ex["argv"]).encode()).hexdigest(),
                      "argv_redacted": ex["argv"], "random_seed": 0, "timeout_ms": 0, "retries": 0,
                      "context_budget_tokens": system.get("context_budget_tokens"), "retrieval_top_k": 50,
                      "stdout_sha256": sha(a.stdout), "stderr_sha256": sha(a.stderr), "exit_code": ex["exit_status"],
                      "peak_rss_bytes": int(ex["peak_rss_mib"] * 1024 * 1024), "peak_vram_bytes": None,
                      "latency_p50_ms": pct(lat, 0.5), "latency_p95_ms": pct(lat, 0.95)},
        "costs": {"status": "not_measured", "currency": "USD", "amount": None, "input_tokens": None,
                  "output_tokens": None, "billing_reference_sha256": None},
        "artifacts": artifacts,
        "redaction": {"reviewed": True, "contains_secrets": False, "contains_private_data": False,
                      "note": "Runs used an allowlisted environment with no tokens; argv contains only local paths and flags. Dataset is public LongMemEval-S."},
        "review": {"status": "candidate", "reviewer": None, "decision_ref": None,
                   "limitations": system.get("limitations", []), "comparison_eligibility": "not_assessed"},
        "authority_effect": "none",
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(manifest, indent=2) + "\n")
    print(a.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
