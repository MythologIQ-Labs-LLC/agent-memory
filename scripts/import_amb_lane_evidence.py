#!/usr/bin/env python3
"""Import raw AMB same-harness lane artifacts into committed evidence records (#640).

A lane row becomes acceptable evidence only when its raw harness artifact and execution
identity are committed next to a record that binds them to the frozen lane. This script
takes the artifacts the ``Independent AMB Competitive Run`` workflow uploaded (as laid out
by ``gh run download``: ``<runs-dir>/<run_id>/<artifact-name>/...``) and writes, per row,
``reports/benchmarks/amb/<lane_id>/<provider>-<revision12>/``:

* the raw AMB ``EvalSummary`` JSON, execution identity, constraints file and provenance
  sidecar, self-check output and the run's own sha256 inventory, copied byte for byte and
  re-verified against that inventory;
* ``evidence.json``, the binding record: lane and row identity, the frozen input digest
  (re-derived from the lane file at the executing revision and, unless ``--no-fetch``,
  re-hashed from the pinned fixture URLs), the system revision the row freezes, the full
  execution identity, and a native summary recomputed from the raw per-case results in
  the harness's own shape (``summarize_run``).

The record carries ``authority_effect: none``. It never decides acceptance: that is the
``evidence_history`` entry a reviewer adds to the integration descriptor, whose
``report_binding`` points at ``input.sha256`` and ``system.revision`` in this file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import urllib.request
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "reference"))

from agentmem_ref.evaluation.registry import get_integration  # noqa: E402
from agentmem_ref.evaluation.same_harness_lane import lane_digest, validate_lane  # noqa: E402

CONTRACT_FAMILY = "agent-memory-same-harness-lane-evidence"
CONTRACT_VERSION = "1.0.0"
COPIED_FILES = (
    "execution-identity.json",
    "amb-constraints.txt",
    "amb-constraints-provenance.json",
    "precisionmembench-selfcheck.txt",
    "files.txt",
    "sha256.txt",
)


class ImportError_(RuntimeError):
    pass


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_inventory(path: Path) -> dict[str, str]:
    inventory: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        digest, _, name = line.partition("  ")
        inventory[name.strip().removeprefix("./")] = digest.strip()
    return inventory


def lane_at_revision(repo_root: Path, lane_file: str, revision: str, *, at_head: bool) -> dict:
    if at_head:
        text = (repo_root / lane_file).read_text(encoding="utf-8")
    else:
        text = subprocess.run(
            ["git", "show", f"{revision}:{lane_file}"], cwd=repo_root, capture_output=True, text=True, check=True
        ).stdout
    return validate_lane(json.loads(text))


def verify_fixtures(lane: dict) -> dict[str, str]:
    combined = hashlib.sha256()
    digests: dict[str, str] = {}
    for fixture in lane["dataset"]["fixtures"]:
        with urllib.request.urlopen(fixture["url"]) as response:  # noqa: S310 - pinned upstream commit URL from the lane
            payload = response.read()
        digest = hashlib.sha256(payload).hexdigest()
        if digest != fixture["sha256"]:
            raise ImportError_(f"fixture {fixture['name']} sha256 {digest} != frozen {fixture['sha256']}")
        digests[fixture["name"]] = digest
        combined.update(payload)
    if combined.hexdigest() != lane["dataset"]["input_sha256"]:
        raise ImportError_(f"combined fixture digest {combined.hexdigest()} != lane input_sha256")
    return digests


def native_summary(summary: dict) -> dict:
    """Recompute the harness's own PrecisionMemBench table from the raw per-case results."""
    results = summary["results"]
    by_type = Counter(r["meta"].get("pass_type") for r in results)
    passed = [r for r in results if r["correct"]]
    passed_by_type = Counter(r["meta"].get("pass_type") for r in passed)
    precision = [v for r in results if (v := r["meta"].get("retrieval_precision")) is not None]
    recall = [v for r in results if (v := r["meta"].get("retrieval_recall")) is not None]
    resolution: Counter = Counter()
    for r in results:
        resolution.update(r["meta"].get("resolution") or {})
    retrieve = [r["retrieve_time_ms"] for r in results if r.get("retrieve_time_ms") is not None]
    return {
        "total_queries": summary["total_queries"],
        "correct": summary["correct"],
        "accuracy": summary["accuracy"],
        "active_passes": passed_by_type["active"],
        "active_total": by_type["active"],
        "structural_passes": passed_by_type["structural"],
        "structural_total": by_type["structural"],
        "trivially_empty_passes": passed_by_type["trivially-empty"],
        "trivially_empty_total": by_type["trivially-empty"],
        "total_passes": len(passed),
        "mean_precision": round(sum(precision) / len(precision), 4) if precision else None,
        "mean_recall": round(sum(recall) / len(recall), 4) if recall else None,
        "id_resolution": dict(resolution.most_common()),
        "mean_retrieve_ms": round(sum(retrieve) / len(retrieve), 2) if retrieve else None,
        "ingestion_time_ms": summary.get("ingestion_time_ms"),
        "ingested_docs": summary.get("ingested_docs"),
        "answer_llm": summary.get("answer_llm"),
        "judge_llm": summary.get("judge_llm"),
        "shape_note": "recomputed from results[].meta exactly as the frozen harness's summarize_run does; active_passes/active_total is the upstream-comparable number",
    }


def find_artifact_dirs(runs_dir: Path) -> list[tuple[str, Path]]:
    found: list[tuple[str, Path]] = []
    for identity in sorted(runs_dir.rglob("execution-identity.json")):
        run_id = identity.relative_to(runs_dir).parts[0]
        found.append((run_id, identity.parent))
    if not found:
        raise ImportError_(f"no execution-identity.json under {runs_dir}")
    return found


def import_artifact(run_id: str, artifact_dir: Path, *, repo_root: Path, output_root: Path, fetch: bool, lane_at_head: bool) -> Path:
    identity = json.loads((artifact_dir / "execution-identity.json").read_text(encoding="utf-8"))
    if str(identity.get("workflow_run_id")) != str(run_id):
        raise ImportError_(f"identity workflow_run_id {identity.get('workflow_run_id')} != directory run id {run_id}")
    if not identity.get("lane_id"):
        raise ImportError_(f"run {run_id} did not execute a lane (lane_id is null)")
    if identity.get("full_selection") is not True or identity.get("amb_pmb_return_cap") is not None:
        raise ImportError_(f"run {run_id} is not a full-selection, uncapped lane execution")
    if identity.get("mode") != "retrieval" or identity.get("answer_model") or identity.get("judge_model"):
        raise ImportError_(f"run {run_id} is not a retrieval-mode, model-free execution")

    lane_file = identity["lane_file"]
    revision = identity["agent_memory_revision"]
    lane = lane_at_revision(repo_root, lane_file, revision, at_head=lane_at_head)
    if lane["lane_id"] != identity["lane_id"]:
        raise ImportError_(f"lane id {lane['lane_id']} != identity {identity['lane_id']}")
    if lane["harness"]["revision"] != identity["amb_revision"]:
        raise ImportError_(f"lane harness revision != executed AMB revision {identity['amb_revision']}")
    row = next((item for item in lane["systems"] if item["provider_key"] == identity["memory"]), None)
    if row is None:
        raise ImportError_(f"lane has no row for provider {identity['memory']}")
    if identity.get("harness_constraints") is None:
        raise ImportError_(f"run {run_id} carries no harness lock provenance")
    if identity["harness_constraints"]["uv_lock_git_blob"] != lane["execution"]["environment"]["harness_lock"]["git_blob"]:
        raise ImportError_("executed harness lock blob differs from the lane's recorded lock")

    inventory = read_inventory(artifact_dir / "sha256.txt")
    summaries = sorted(artifact_dir.glob("precisionmembench/*/retrieval/single-turn.json"))
    if len(summaries) != 1:
        raise ImportError_(f"expected exactly one EvalSummary in {artifact_dir}, found {len(summaries)}")
    summary_path = summaries[0]

    destination = output_root / lane["lane_id"] / f"{identity['memory']}-{revision[:12]}"
    destination.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}
    for name in COPIED_FILES:
        source = artifact_dir / name
        if not source.is_file():
            raise ImportError_(f"artifact {artifact_dir} lacks {name}")
        shutil.copyfile(source, destination / name)
        files[name] = sha256_of(destination / name)
    shutil.copyfile(summary_path, destination / "single-turn.json")
    files["single-turn.json"] = sha256_of(destination / "single-turn.json")

    # Re-verify every copied byte against the run's own inventory. sha256.txt lists
    # itself only implicitly, so it is checked by presence and files.txt by digest.
    summary_rel = str(summary_path.relative_to(artifact_dir))
    expected = {name: inventory.get(name) for name in COPIED_FILES if name != "sha256.txt"}
    expected["single-turn.json"] = inventory.get(summary_rel)
    for name, digest in expected.items():
        if digest is None:
            raise ImportError_(f"run inventory does not list {name}")
        if digest != files[name]:
            raise ImportError_(f"{name}: copied digest {files[name]} != inventory {digest}")

    summary = json.loads((destination / "single-turn.json").read_text(encoding="utf-8"))
    if summary.get("memory_provider") != identity["memory"] or summary.get("mode") != "retrieval":
        raise ImportError_("EvalSummary provider/mode do not match the execution identity")
    if summary.get("total_queries") != lane["dataset"]["query_count"]:
        raise ImportError_(f"EvalSummary total_queries {summary.get('total_queries')} != lane query_count {lane['dataset']['query_count']}")

    if row["source"]["kind"] == "repository_runtime":
        system_revision = revision
    else:
        system_revision = row["source"]["revision"]
    integration = get_integration(lane["benchmark_integration"])
    corpus_classes = integration["input_contract"]["corpus_classes"]
    if len(corpus_classes) != 1:
        raise ImportError_(f"integration {lane['benchmark_integration']} declares {len(corpus_classes)} corpus classes; the evidence record needs exactly one")
    fixture_digests = verify_fixtures(lane) if fetch else {f["name"]: f["sha256"] for f in lane["dataset"]["fixtures"]}

    record = {
        "contract_family": CONTRACT_FAMILY,
        "contract_version": CONTRACT_VERSION,
        "evidence_class": "same_harness_external_candidate",
        "lane_id": lane["lane_id"],
        "lane_file": lane_file,
        "lane_digest_at_execution": lane_digest(lane),
        "row": {
            "row_id": row["row_id"],
            "system_id": row["system_id"],
            "display_name": row["display_name"],
            "role": row["role"],
            "provider_key": row["provider_key"],
            "inference_posture": row.get("inference_posture"),
        },
        "system": {
            "id": row["system_id"],
            "revision": system_revision,
            "revision_rule": row["source"]["revision_rule"],
            "source_kind": row["source"]["kind"],
            "resolved_packages": identity.get("resolved_packages"),
            "mem0_optional_components": identity.get("mem0_optional_components"),
        },
        "input": {
            "sha256": lane["dataset"]["input_sha256"],
            "corpus_class": corpus_classes[0],
            "dataset_revision": f"{lane['dataset']['upstream']['repository']}@{lane['dataset']['upstream']['revision']}",
            "fixtures": fixture_digests,
            "verified_by": "re-hashed from the pinned fixture URLs at import" if fetch else "lane record only (import ran with --no-fetch)",
            "query_count": lane["dataset"]["query_count"],
            "selection_id": lane["selection"]["selection_id"],
        },
        "execution": identity,
        "workflow_run": {
            "id": str(run_id),
            "url": f"https://github.com/MythologIQ-Labs-LLC/agent-memory/actions/runs/{run_id}",
            "artifact_directory": artifact_dir.name,
        },
        "native_summary": native_summary(summary),
        "files": files,
        "authority_effect": "none",
    }
    (destination / "evidence.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs-dir", required=True, type=Path, help="directory holding <run_id>/<artifact-name>/... as gh run download lays it out")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output-root", type=Path, default=None, help="defaults to <repo-root>/reports/benchmarks/amb")
    parser.add_argument("--no-fetch", action="store_true", help="do not re-download the fixtures to re-verify the input digest")
    parser.add_argument("--lane-at-head", action="store_true", help="read the lane file from the working tree instead of the executing revision")
    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()
    output_root = (args.output_root or repo_root / "reports" / "benchmarks" / "amb").resolve()
    written = []
    for run_id, artifact_dir in find_artifact_dirs(args.runs_dir.resolve()):
        destination = import_artifact(
            run_id, artifact_dir, repo_root=repo_root, output_root=output_root, fetch=not args.no_fetch, lane_at_head=args.lane_at_head
        )
        record = json.loads((destination / "evidence.json").read_text(encoding="utf-8"))
        written.append({"run_id": run_id, "destination": str(destination.relative_to(repo_root)) if destination.is_relative_to(repo_root) else str(destination), "row_id": record["row"]["row_id"], "native_summary": record["native_summary"]})
    print(json.dumps(written, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ImportError_ as exc:
        print(f"refused: {exc}", file=sys.stderr)
        sys.exit(2)
