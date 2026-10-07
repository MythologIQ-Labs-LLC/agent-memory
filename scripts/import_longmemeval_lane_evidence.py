#!/usr/bin/env python3
"""Import raw LongMemEval same-harness lane artifacts into committed evidence records (#640).

A lane row becomes acceptable evidence only when its raw report and execution identity are
committed next to a record that binds them to the frozen lane. This script takes the
artifacts the ``LongMemEval Same-Harness Lane Run`` workflow uploaded (as laid out by
``gh run download``: ``<runs-dir>/<run_id>/<artifact-name>/...``) and writes, per
(row, plane), ``reports/benchmarks/longmemeval/<lane_id>/<backend>-<plane>-<revision12>/``:

* ``report.json``, the runner's native report with its per-question rows moved to
  ``report.rows.json.gz`` (the repository's convention for LongMemEval evidence); the raw
  artifact bytes are proven to recompose exactly from the two files and the raw digest is
  recorded;
* ``execution-identity.json``, ``lane-validation.json``, ``files.txt`` and ``sha256.txt``
  copied byte for byte and re-verified against the run's own inventory;
* ``evidence.json``, the binding record: lane and row identity, the frozen input digest
  (re-derived from the lane file at the executing revision and, unless ``--no-fetch``,
  re-hashed from the pinned fixture URL), the system revision the row freezes, the full
  execution identity, and the native headline block copied from the report.

Every check is fail-closed: the lane digest, the bound evaluator and adapter blobs, the
full selection, the input digest and selection digest, the backend and plane, the frozen
Agent Memory comparability posture, and (for the Mem0 row) the exact release, the
extras posture and the pinned retrieval stack must all match the lane. The record carries
``authority_effect: none``. It never decides acceptance: that is the ``evidence_history``
entry a reviewer adds to the integration descriptor, whose ``report_binding`` points at
``input.sha256`` and ``system.revision`` in this file.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "reference"))

from agentmem_ref.evaluation.registry import get_integration  # noqa: E402
from agentmem_ref.evaluation.same_harness_lane import lane_digest, validate_lane  # noqa: E402

CONTRACT_FAMILY = "agent-memory-same-harness-lane-evidence"
CONTRACT_VERSION = "1.0.0"
COPIED_FILES = ("execution-identity.json", "lane-validation.json", "files.txt", "sha256.txt")
PLANES = ("session", "turn")
_SHA256_RE = re.compile(r"\b[0-9a-f]{64}\b")
#: The runner's own defaults for the Agent Memory configuration it records
#: (``run_longmemeval._AGENT_MEMORY_CONFIGURATION``). The importer never reads the runner at
#: HEAD: a lane pins the runner blob that produced its evidence, and the expectation is the
#: defaults overlaid with the keys the lane's control row declares.
RUNNER_CONFIGURATION_DEFAULTS = {
    "temporal_metadata": "none",
    "ranking_variant": "default",
    "budget": "none",
    "semantic_retrieval": "off",
    "recall_control": "off",
}
#: ``execution.agent_memory_semantic_posture`` fields a row's ``semantic_representation``
#: pins (#669 D2); ``status`` must be ``enabled`` and ``mode`` must equal the row's mode.
SEMANTIC_POSTURE_FIELDS = (
    "representation_ref",
    "representation_version",
    "config_digest",
    "dimensions",
    "minimum_similarity",
    "candidate_limit",
)
RUNTIME_BASELINE_STATES = ("PASS", "TRANSITION")
#: The first lane generation whose ``agent_memory`` row must carry the per-question cross-fact
#: record (plan-671-evidence-v5 E2): ``longmemeval-s-retrieval-parity-v5`` and later.
CROSS_FACT_FIRST_GENERATION = 5
CROSS_FACT_PROVIDER_KEY = "agent_memory"
CROSS_FACT_RECORD_FIELDS = ("limited_count", "limited_item_ids", "refusal_counts", "ranked_top_mechanism_off")
_GENERATION_RE = re.compile(r"-v(\d+)$")


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
    digests: dict[str, str] = {}
    for fixture in lane["dataset"]["fixtures"]:
        digest = hashlib.sha256()
        with urllib.request.urlopen(fixture["url"]) as response:  # noqa: S310 - pinned hub revision URL from the lane
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                digest.update(chunk)
        if digest.hexdigest() != fixture["sha256"]:
            raise ImportError_(f"fixture {fixture['name']} sha256 {digest.hexdigest()} != frozen {fixture['sha256']}")
        digests[fixture["name"]] = digest.hexdigest()
    return digests


def frozen_selection_digest(lane: dict) -> str:
    found = _SHA256_RE.findall(lane["selection"]["selection_method"])
    if len(found) != 1:
        raise ImportError_("lane selection_method must name exactly one frozen question_ids_sha256")
    return found[0]


def control_row(lane: dict) -> dict:
    return next(item for item in lane["systems"] if item["role"] == "control")


def agent_memory_row(lane: dict, row: dict | None = None) -> dict:
    """The row whose configuration the run's recorded Agent Memory configuration must match.

    A row that runs the ``agent_memory`` backend (the control, or a measured variant such as
    #669 D2's ``agent_memory_semantic``) is matched against its own declaration, never the
    control's, so a semantic-route run checked against the control is refused. Every other
    row records the control's Agent Memory configuration (the workflow passes it unchanged).
    """

    if row is not None and (row.get("configuration") or {}).get("backend", row["provider_key"]) == "agent_memory":
        return row
    return control_row(lane)


def expected_agent_memory_configuration(lane: dict, row: dict | None = None) -> dict[str, str]:
    """The runner defaults overlaid with the declared configuration of ``agent_memory_row``."""

    declared = agent_memory_row(lane, row).get("configuration") or {}
    return {key: str(declared.get(key, default)) for key, default in RUNNER_CONFIGURATION_DEFAULTS.items()}


def recorded_agent_memory_configuration(execution: dict) -> dict[str, str]:
    recorded = execution.get("agent_memory_configuration") or {}
    return {key: str(recorded.get(key, default)) for key, default in RUNNER_CONFIGURATION_DEFAULTS.items()}


def check_semantic_posture(execution: dict, row: dict) -> dict | None:
    """Bind the run's recorded semantic-route posture to the row's pinned representation (#669 D2)."""

    recorded = execution.get("agent_memory_semantic_posture")
    configuration = row.get("configuration") or {}
    mode = str(configuration.get("semantic_retrieval", "off"))
    pinned = configuration.get("semantic_representation")
    if mode == "off":
        if recorded is not None or pinned is not None:
            raise ImportError_(f"row {row['row_id']} declares no semantic route but the run or row carries a posture")
        return None
    if not isinstance(pinned, dict):
        raise ImportError_(f"row {row['row_id']} declares semantic_retrieval {mode} without a semantic_representation pin")
    if not isinstance(recorded, dict):
        raise ImportError_("the run recorded no agent_memory_semantic_posture")
    if recorded.get("status") != "enabled" or recorded.get("mode") != mode:
        raise ImportError_(f"semantic route was {recorded.get('status')}/{recorded.get('mode')}, not enabled/{mode}")
    mismatched = [field for field in SEMANTIC_POSTURE_FIELDS if recorded.get(field) != pinned.get(field)]
    if mismatched:
        raise ImportError_(f"semantic posture differs from the row's pin in {mismatched}")
    return dict(recorded)


def check_recall_control(native: dict, mode: str, row: dict) -> dict | None:
    """Bind per-question shadow telemetry to the row's ``recall_control`` mode (plan-644-lanes-v4 L2).

    A shadow row must carry the telemetry record (``authority_effect: none``) on every question
    without a runtime error, plus the report aggregate; every other row must carry none. The
    telemetry is evidence for T-controller-2, never benchmark authority.
    """

    rows = native.get("rows") or []
    carrying = [item for item in rows if "recall_control" in item]
    if mode != "shadow":
        if carrying or "recall_control_summary" in native:
            raise ImportError_(f"row {row['row_id']} runs recall_control {mode} but the report carries shadow telemetry")
        return None
    for item in rows:
        if item.get("runtime_error") is not None:
            continue
        record = item.get("recall_control")
        if not isinstance(record, dict) or record.get("authority_effect") != "none":
            raise ImportError_(f"shadow row {row['row_id']} question {item.get('question_id')} lacks an authority-free telemetry record")
        if "elapsed_ms" in (record.get("usage") or {}):
            raise ImportError_(f"shadow row {row['row_id']} question {item.get('question_id')} records non-deterministic elapsed_ms")
    summary = native.get("recall_control_summary")
    if not isinstance(summary, dict) or summary.get("questions_with_telemetry") != len(carrying):
        raise ImportError_(f"shadow row {row['row_id']} report lacks a recall_control_summary over its telemetry")
    return summary


def lane_generation(lane: dict) -> int:
    """The lane generation its id names (``...-v5`` is 5; the unsuffixed v1 id is 1)."""

    found = _GENERATION_RE.search(str(lane["lane_id"]))
    return int(found.group(1)) if found else 1


def check_cross_fact(native: dict, lane: dict, row: dict) -> dict | None:
    """Bind the per-question cross-fact records to the row (plan-671-evidence-v5 E2).

    From the ``-v5`` generation on, the ``agent_memory`` row must carry a well-formed
    ``cross_fact`` record on every question without a runtime error (an error row carries
    none) and the report's ``cross_fact_summary`` over them; every other row, and every row of
    an earlier generation, must carry neither. The records are evidence for the E1 attribution
    check, never benchmark authority.
    """

    rows = native.get("rows") or []
    carrying = [item for item in rows if "cross_fact" in item]
    required = lane_generation(lane) >= CROSS_FACT_FIRST_GENERATION and row["provider_key"] == CROSS_FACT_PROVIDER_KEY
    if not required:
        if carrying or "cross_fact_summary" in native:
            raise ImportError_(f"row {row['row_id']} of {lane['lane_id']} carries cross_fact records it does not declare")
        return None
    for item in rows:
        record = item.get("cross_fact")
        if item.get("runtime_error") is not None:
            if record is not None:
                raise ImportError_(f"row {row['row_id']} question {item.get('question_id')} has a runtime error and a cross_fact record")
            continue
        if not isinstance(record, dict) or set(record) != set(CROSS_FACT_RECORD_FIELDS):
            raise ImportError_(f"row {row['row_id']} question {item.get('question_id')} lacks a cross_fact record")
        limited = record["limited_count"]
        if not isinstance(limited, int) or limited < 0 or len(record["limited_item_ids"] or []) != limited:
            raise ImportError_(f"row {row['row_id']} question {item.get('question_id')} cross_fact limited_count is malformed")
        if (record["ranked_top_mechanism_off"] is None) != (limited == 0):
            raise ImportError_(
                f"row {row['row_id']} question {item.get('question_id')} cross_fact ranked_top_mechanism_off must be null exactly when limited_count is 0"
            )
    summary = native.get("cross_fact_summary")
    if (
        not isinstance(summary, dict)
        or summary.get("questions_with_record") != len(carrying)
        or summary.get("limited_total") != sum(item["cross_fact"]["limited_count"] for item in carrying)
    ):
        raise ImportError_(f"row {row['row_id']} report lacks a cross_fact_summary over its records")
    return summary


def runtime_baseline_binding(identity: dict, lane: dict, row: dict | None = None) -> dict | None:
    """Bind the checker state the run recorded to the posture the lane's control row pins.

    A lane whose control row declares ``configuration.runtime_baseline_posture`` executes
    during a declared baseline transition: the run must record a checker state the posture
    admits and the declaration blob the posture pins, so a declaration amended between runs
    (docs/67 Step A.6) is refused rather than silently accepted. A lane without a posture
    (both v1 lanes) binds nothing here.
    """

    posture = (agent_memory_row(lane, row).get("configuration") or {}).get("runtime_baseline_posture")
    if posture is None:
        return None
    state = identity.get("runtime_baseline_state")
    if state not in posture.get("checker_state_required", list(RUNTIME_BASELINE_STATES)):
        raise ImportError_(f"runtime baseline state {state!r} is not admitted by the lane's posture")
    if identity.get("declaration_blob") != posture["declaration_blob"]:
        raise ImportError_(
            f"executed declaration blob {identity.get('declaration_blob')} != lane-pinned {posture['declaration_blob']}"
        )
    return {
        "state": state,
        "line": identity.get("runtime_baseline_line"),
        "declaration_blob": identity.get("declaration_blob"),
        "declared_successor": posture["declared_successor"],
        "predecessor": posture["predecessor"],
    }


def lane_reference_blobs(lane: dict) -> dict[str, str]:
    return {path: blob for path, blob in lane["harness"]["source_blobs"].items() if path.startswith("reference/")}


def find_artifact_dirs(runs_dir: Path) -> list[tuple[str, Path]]:
    found: list[tuple[str, Path]] = []
    for identity in sorted(runs_dir.rglob("execution-identity.json")):
        run_id = identity.relative_to(runs_dir).parts[0]
        found.append((run_id, identity.parent))
    if not found:
        raise ImportError_(f"no execution-identity.json under {runs_dir}")
    return found


def _check_identity(run_id: str, identity: dict, lane: dict) -> dict:
    if str(identity.get("workflow_run_id")) != str(run_id):
        raise ImportError_(f"identity workflow_run_id {identity.get('workflow_run_id')} != directory run id {run_id}")
    if identity.get("lane_id") != lane["lane_id"]:
        raise ImportError_(f"run {run_id} executed lane {identity.get('lane_id')!r}, not {lane['lane_id']}")
    if identity.get("full_selection") is not True or str(identity.get("subset_size")) != "0":
        raise ImportError_(f"run {run_id} is not a full-selection lane execution")
    if identity.get("lane_digest_sha256") != lane_digest(lane):
        raise ImportError_(f"run {run_id} executed lane digest {identity.get('lane_digest_sha256')} != frozen {lane_digest(lane)}")
    if identity.get("upstream_revision") != lane["harness"]["revision"]:
        raise ImportError_("executed upstream revision differs from the lane's harness revision")
    if identity.get("input_sha256") != lane["dataset"]["input_sha256"]:
        raise ImportError_("executed input digest differs from the lane's input_sha256")
    expected_blobs = lane_reference_blobs(lane)
    if identity.get("source_blobs") != expected_blobs:
        raise ImportError_(f"executed source blobs {identity.get('source_blobs')} != frozen {expected_blobs}")
    plane = identity.get("granularity")
    if plane not in PLANES:
        raise ImportError_(f"run {run_id} granularity {plane!r} is not a lane plane")
    row = next((item for item in lane["systems"] if item["provider_key"] == identity.get("backend")), None)
    if row is None:
        raise ImportError_(f"lane has no row for backend {identity.get('backend')!r}")
    # A row may run a built-in backend under its own identity (#669 D2); the identity then
    # records the backend the runner executed. Absent, the runner backend is the row key.
    runner_backend = identity.get("runner_backend", identity.get("backend"))
    declared_backend = (row.get("configuration") or {}).get("backend", row["provider_key"])
    if runner_backend != declared_backend:
        raise ImportError_(f"row {row['row_id']} runs backend {declared_backend!r}, but the run executed {runner_backend!r}")
    if row["status"] not in {"frozen", "executed", "accepted"}:
        raise ImportError_(f"row {row['row_id']} is {row['status']}; only a declared row can be executed")
    return row


def runner_backend_of(identity: dict) -> str:
    return identity.get("runner_backend", identity["backend"])


def _check_report(report: dict, *, identity: dict, lane: dict, row: dict) -> None:
    backend, plane = runner_backend_of(identity), identity["granularity"]
    input_block = report["input"]
    if input_block.get("sha256") != lane["dataset"]["input_sha256"]:
        raise ImportError_("report input digest differs from the lane's input_sha256")
    if input_block.get("corpus_class") != "external_frozen":
        raise ImportError_(f"report corpus_class {input_block.get('corpus_class')!r} is not external_frozen")
    if input_block.get("question_count") != lane["dataset"]["query_count"] or input_block.get("source_question_count") != lane["dataset"]["query_count"]:
        raise ImportError_("report question counts differ from the lane's query_count")
    selection = input_block.get("selection") or {}
    if selection.get("method") != "all" or selection.get("question_ids_sha256") != frozen_selection_digest(lane):
        raise ImportError_("report selection is not the frozen full selection")
    if report.get("upstream", {}).get("revision") != lane["harness"]["revision"]:
        raise ImportError_("report upstream revision differs from the lane's harness revision")
    execution = report["execution"]
    if execution.get("agent_memory_revision") != identity["agent_memory_revision"]:
        raise ImportError_("report repository revision differs from the execution identity")
    if execution.get("agent_memory_worktree_dirty") is not False:
        raise ImportError_("report was produced from a dirty or unknown worktree")
    if execution.get("backends") != [backend] or execution.get("granularities") != [plane]:
        raise ImportError_(f"report executed {execution.get('backends')} x {execution.get('granularities')}, expected [{backend}] x [{plane}]")
    expected_configuration = expected_agent_memory_configuration(lane, row)
    if recorded_agent_memory_configuration(execution) != expected_configuration:
        raise ImportError_(
            f"Agent Memory configuration {execution.get('agent_memory_configuration')} is not row {row['row_id']}'s declared posture {expected_configuration}"
        )
    check_semantic_posture(execution, agent_memory_row(lane, row))
    planes = report.get("planes") or {}
    if list(planes) != [plane] or list(planes[plane].get("backends") or {}) != [backend]:
        raise ImportError_("report planes/backends do not match the execution identity")
    native = planes[plane]["backends"][backend]
    if len(native.get("rows") or []) != lane["dataset"]["query_count"]:
        raise ImportError_("report does not carry one row per frozen question")
    check_recall_control(native, expected_configuration["recall_control"], row)
    check_cross_fact(native, lane, row)
    external = (execution.get("external_backends") or {}).get(backend)
    if row["source"]["kind"] == "python_package":
        if external is None:
            raise ImportError_(f"external row {backend} carries no execution.external_backends identity")
        if external.get("system_revision") != row["source"]["revision"]:
            raise ImportError_(f"external system revision {external.get('system_revision')} != frozen {row['source']['revision']}")
        bridge_blob = lane["harness"]["source_blobs"].get(row["adapter"]["module"])
        if external.get("adapter_revision") != bridge_blob:
            raise ImportError_(f"adapter revision {external.get('adapter_revision')} != frozen bridge blob {bridge_blob}")
        posture = external.get("install_posture") or {}
        if posture.get("fastembed_installed") is not False or posture.get("spacy_installed") is not False:
            raise ImportError_(f"Mem0 extras posture {posture} violates the frozen base-package row")
        resolved = identity.get("resolved_packages") or {}
        for pin in row["dependency_pins"]:
            name, _, version = pin.partition("==")
            if resolved.get(name) != version:
                raise ImportError_(f"resolved {name}={resolved.get(name)!r} != frozen pin {pin}")
        if posture.get("mem0ai") != resolved.get("mem0ai"):
            raise ImportError_("Mem0 version seen by the bridge differs from the resolved package")
    elif external is not None:
        raise ImportError_(f"built-in row {backend} unexpectedly carries an external identity")


def native_summary(report: dict, plane: str, backend: str) -> dict:
    native = report["planes"][plane]["backends"][backend]
    summary = {
        "plane": plane,
        "backend": backend,
        "evaluated_question_count": native["aggregate"]["evaluated_question_count"],
        "headline": dict(native["aggregate"]["headline"]),
        "knowledge_update_headline": dict(native["currentness"]["knowledge_update"]["headline"]),
        "latest_gold_ranked_first": dict(native["currentness"]["latest_gold_ranked_first"]),
        "failures": dict(native["failures"]),
        "timing": dict(native["timing"]),
        "shape_note": "copied from the runner's own aggregate for this plane and backend; the full native report is report.json",
    }
    for key in ("governance", "external_system"):
        if key in native:
            summary[key] = dict(native[key])
    return summary


def import_artifact(run_id: str, artifact_dir: Path, *, repo_root: Path, output_root: Path, fetch: bool, lane_at_head: bool) -> Path:
    identity = json.loads((artifact_dir / "execution-identity.json").read_text(encoding="utf-8"))
    if not identity.get("lane_id") or not identity.get("lane_file"):
        raise ImportError_(f"run {run_id} did not execute a lane")
    revision = identity["agent_memory_revision"]
    lane = lane_at_revision(repo_root, identity["lane_file"], revision, at_head=lane_at_head)
    row = _check_identity(run_id, identity, lane)
    key, backend, plane = row["provider_key"], runner_backend_of(identity), identity["granularity"]

    inventory = read_inventory(artifact_dir / "sha256.txt")
    raw_name = f"{plane}-{key}.json"
    raw_path = artifact_dir / raw_name
    if not raw_path.is_file():
        raise ImportError_(f"artifact {artifact_dir} lacks {raw_name}")
    raw_bytes = raw_path.read_bytes()
    raw_digest = hashlib.sha256(raw_bytes).hexdigest()
    if inventory.get(raw_name) != raw_digest:
        raise ImportError_(f"{raw_name}: artifact digest {raw_digest} != inventory {inventory.get(raw_name)}")
    report = json.loads(raw_bytes.decode("utf-8"))
    _check_report(report, identity=identity, lane=lane, row=row)

    destination = output_root / lane["lane_id"] / f"{key}-{plane}-{revision[:12]}"
    destination.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}
    for name in COPIED_FILES:
        source = artifact_dir / name
        if not source.is_file():
            raise ImportError_(f"artifact {artifact_dir} lacks {name}")
        shutil.copyfile(source, destination / name)
        files[name] = sha256_of(destination / name)
        if name != "sha256.txt":
            if inventory.get(name) is None:
                raise ImportError_(f"run inventory does not list {name}")
            if inventory[name] != files[name]:
                raise ImportError_(f"{name}: copied digest {files[name]} != inventory {inventory[name]}")

    # Rows move to the gzip sidecar the repository uses for LongMemEval evidence; prove the
    # raw artifact recomposes byte for byte from the two committed files before writing.
    rows = {plane: {backend: report["planes"][plane]["backends"][backend].pop("rows")}}
    stripped = json.dumps(report, indent=2, sort_keys=True) + "\n"
    recomposed = json.loads(stripped)
    recomposed["planes"][plane]["backends"][backend]["rows"] = rows[plane][backend]
    if (json.dumps(recomposed, indent=2, sort_keys=True) + "\n").encode("utf-8") != raw_bytes:
        raise ImportError_(f"{raw_name} does not recompose from report.json + report.rows.json.gz; refusing to split it")
    (destination / "report.json").write_text(stripped, encoding="utf-8")
    with gzip.open(destination / "report.rows.json.gz", "wb", compresslevel=9) as handle:
        handle.write(json.dumps(rows, sort_keys=True).encode("utf-8"))
    files["report.json"] = sha256_of(destination / "report.json")
    files["report.rows.json.gz"] = sha256_of(destination / "report.rows.json.gz")

    if row["source"]["kind"] == "python_package":
        system_revision = row["source"]["revision"]
    else:
        system_revision = revision
    integration = get_integration(lane["benchmark_integration"])
    fixture_digests = verify_fixtures(lane) if fetch else {f["name"]: f["sha256"] for f in lane["dataset"]["fixtures"]}
    record = {
        "contract_family": CONTRACT_FAMILY,
        "contract_version": CONTRACT_VERSION,
        "evidence_class": "same_harness_external_candidate",
        "benchmark_integration": integration["integration_id"],
        "lane_id": lane["lane_id"],
        "lane_file": identity["lane_file"],
        "lane_digest_at_execution": lane_digest(lane),
        "row": {
            "row_id": row["row_id"],
            "system_id": row["system_id"],
            "display_name": row["display_name"],
            "role": row["role"],
            "provider_key": row["provider_key"],
            "backend": backend,
            "plane": plane,
            "inference_posture": row.get("inference_posture"),
        },
        "system": {
            "id": row["system_id"],
            "revision": system_revision,
            "revision_rule": row["source"]["revision_rule"],
            "source_kind": row["source"]["kind"],
            "resolved_packages": identity.get("resolved_packages"),
            "mem0_optional_components": identity.get("mem0_optional_components"),
            "external_backend_identity": (report["execution"].get("external_backends") or {}).get(backend),
            "runtime_baseline": runtime_baseline_binding(identity, lane, row),
            "semantic_route_posture": report["execution"].get("agent_memory_semantic_posture"),
            "recall_control_summary": report["planes"][plane]["backends"][backend].get("recall_control_summary"),
            "cross_fact_summary": report["planes"][plane]["backends"][backend].get("cross_fact_summary"),
        },
        "input": {
            "sha256": lane["dataset"]["input_sha256"],
            "corpus_class": "external_frozen",
            "dataset_revision": f"{integration['input_contract']['dataset_id']}@{lane['dataset']['fixtures'][0]['url'].split('/resolve/')[1].split('/')[0]}",
            "fixtures": fixture_digests,
            "verified_by": "re-hashed from the pinned hub URL at import" if fetch else "lane record only (import ran with --no-fetch)",
            "query_count": lane["dataset"]["query_count"],
            "selection_id": lane["selection"]["selection_id"],
            "question_ids_sha256": report["input"]["selection"]["question_ids_sha256"],
        },
        "execution": identity,
        "workflow_run": {
            "id": str(run_id),
            "url": f"https://github.com/MythologIQ-Labs-LLC/agent-memory/actions/runs/{run_id}",
            "artifact_directory": artifact_dir.name,
        },
        "raw_report": {
            "name": raw_name,
            "sha256": raw_digest,
            "split_rule": "rows moved to report.rows.json.gz ({plane: {backend: rows}}); report.json is the remainder; recomposition verified byte for byte at import",
        },
        "native_summary": native_summary({"planes": {plane: {"backends": {backend: {**report["planes"][plane]["backends"][backend]}}}}}, plane, backend),
        "files": files,
        "authority_effect": "none",
    }
    (destination / "evidence.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs-dir", required=True, type=Path, help="directory holding <run_id>/<artifact-name>/... as gh run download lays it out")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output-root", type=Path, default=None, help="defaults to <repo-root>/reports/benchmarks/longmemeval")
    parser.add_argument("--no-fetch", action="store_true", help="do not re-download the input to re-verify its digest")
    parser.add_argument("--lane-at-head", action="store_true", help="read the lane file from the working tree instead of the executing revision")
    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()
    output_root = (args.output_root or repo_root / "reports" / "benchmarks" / "longmemeval").resolve()
    written = []
    fetched: set[str] = set()
    for run_id, artifact_dir in find_artifact_dirs(args.runs_dir.resolve()):
        # The 277 MB input is re-hashed once per import, not once per artifact.
        fetch = not args.no_fetch and "input" not in fetched
        destination = import_artifact(run_id, artifact_dir, repo_root=repo_root, output_root=output_root, fetch=fetch, lane_at_head=args.lane_at_head)
        if fetch:
            fetched.add("input")
        record = json.loads((destination / "evidence.json").read_text(encoding="utf-8"))
        written.append(
            {
                "run_id": run_id,
                "destination": str(destination.relative_to(repo_root)) if destination.is_relative_to(repo_root) else str(destination),
                "row_id": record["row"]["row_id"],
                "plane": record["row"]["plane"],
                "native_summary": record["native_summary"],
            }
        )
    print(json.dumps(written, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ImportError_ as exc:
        print(f"refused: {exc}", file=sys.stderr)
        sys.exit(2)
