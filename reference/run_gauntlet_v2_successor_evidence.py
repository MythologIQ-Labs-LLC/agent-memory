"""Local, revision-bound evidence for the #786 v2 public-facade Gauntlet contestants.

Runtime Baseline v7 publication (docs/67 Step B1) retires the v1 public-facade contestants,
whose multi-project tenant-wide stores #786 refuses, so the v7 declaration requires a real
run of each v2 successor. Publication evidence is produced by the repository workflows at
the published revision; this script produces the pre-publication record those runs must
reproduce. It runs both successors twice for real, verifies each identity independently
of its manifest's claims, and writes one JSON record. It never edits a v1 file or a v1
result, and the record has ``authority_effect: none``.

    PYTHONPATH=reference python reference/run_gauntlet_v2_successor_evidence.py [--out PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from agentmem_ref import AgentMemory
from agentmem_ref._paths import REPO_ROOT
from agentmem_ref.api import contract, store_contract
from agentmem_ref.evaluation.contract import load_run
from agentmem_ref.evaluation.gauntlet_contract import validate_manifest
from agentmem_ref.evaluation.gauntlet_orchestrator import run_gauntlet
from agentmem_ref.evaluation.gauntlet_profiles import DURABILITY_RECOVERY_PROFILE_ID, GOVERNANCE_ALPHA_PROFILE_ID

sys.path.insert(0, str(REPO_ROOT / "reference"))
from tests.test_gauntlet_durability import _qualified_contestant_launch  # noqa: E402

FIXTURES = REPO_ROOT / "fixtures" / "gauntlet"
OUT = REPO_ROOT / "reports" / "gauntlet" / "agent-memory-public-v2-successors" / "local-qualification.json"
PROTECTED = ["reference/agentmem_ref", ":(exclude)reference/agentmem_ref/evaluation/**", "pyproject.toml"]
CONTESTANTS = (
    {
        "profile_id": DURABILITY_RECOVERY_PROFILE_ID,
        "manifest": FIXTURES / "agent-memory-public-durability-adapter-v2.json",
        "supersedes": FIXTURES / "agent-memory-public-durability-adapter.json",
        "adapter_source": "reference/agentmem_ref/evaluation/gauntlet_agent_memory_durability_v2.py",
        "wrapper_source": "examples/gauntlet/agent_memory_durability_v2_stdio.py",
        "external": True,
    },
    {
        "profile_id": GOVERNANCE_ALPHA_PROFILE_ID,
        "manifest": FIXTURES / "agent-memory-public-governance-adapter-v2.json",
        "supersedes": FIXTURES / "agent-memory-public-governance-adapter.json",
        "adapter_source": "reference/agentmem_ref/evaluation/gauntlet_agent_memory_v2.py",
        "wrapper_source": None,
        "external": False,
    },
)


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pin(manifest: dict) -> str:
    revision = manifest["system"]["revision"]
    return revision.removeprefix("git-commit:").split("@", 1)[-1]


def _live_configuration_digest() -> str:
    with tempfile.TemporaryDirectory() as temp:
        with AgentMemory.open(temp, store_profile="scope_distinct_v1") as memory:
            return memory.posture()["posture"]["configuration"]["digest"]


def _cases(run: dict) -> dict:
    out = {}
    for case in run["native_results"]["cases"]:
        out[case["case_id"]] = {
            key: case[key] for key in ("result", "behavioral_outcome", "evidence_qualification") if key in case
        }
    return dict(sorted(out.items()))


def _run_once(spec: dict) -> dict:
    with tempfile.TemporaryDirectory() as temporary:
        kwargs = {"allow_external_process": True, "allow_destructive_operations": True} if spec["external"] else {}
        if spec["external"]:
            with _qualified_contestant_launch():
                result = run_gauntlet(spec["manifest"], spec["profile_id"], output_dir=Path(temporary) / "runs", **kwargs)
        else:
            result = run_gauntlet(spec["manifest"], spec["profile_id"], output_dir=Path(temporary) / "runs", **kwargs)
        if result["status"] != "complete":
            return {"status": result["status"], "failure": result.get("failure")}
        run = load_run(result["artifacts"]["normalized_run"]["path"])
    return {
        "status": "complete",
        "system": run["system"],
        "authority_effect": run["authority_effect"],
        "dimension_status": {name: block["status"] for name, block in sorted(run["dimensions"].items())},
        "cases": _cases(run),
    }


def qualify(spec: dict, head: str, live_digest: str) -> dict:
    raw = json.loads(spec["manifest"].read_text(encoding="utf-8"))
    manifest = validate_manifest(raw)
    pin = _pin(manifest)
    drift = _git("diff", "--name-only", pin, "HEAD", "--", *PROTECTED).split()
    checks = {
        "manifest_validates": True,
        "adapter_revision_is_real_blob": manifest["adapter"]["revision"] == "git-blob:" + _git("hash-object", spec["adapter_source"]),
        "runtime_pin_equals_head_protected_surface": drift == [],
        "supersedes_names_exact_v1_bytes": manifest["metadata"]["supersedes"]["sha256"] == _sha256(spec["supersedes"]),
        "store_profile_is_scope_distinct": manifest["metadata"]["store_profile"] == "scope_distinct_v1",
    }
    if spec["wrapper_source"]:
        checks["wrapper_revision_is_real_blob"] = (
            manifest["metadata"]["transport_wrapper_revision"] == "git-blob:" + _git("hash-object", spec["wrapper_source"]))
    if "configuration_digest" in manifest["system"]:
        checks["configuration_digest_is_live_posture_digest"] = manifest["system"]["configuration_digest"] == live_digest
    first, second = _run_once(spec), _run_once(spec)
    checks["runs_complete"] = first["status"] == second["status"] == "complete"
    checks["runs_deterministic"] = first == second
    checks["run_records_manifest_identity"] = (
        first.get("system", {}).get("revision") == manifest["system"]["revision"]
        and first.get("system", {}).get("adapter_revision") == manifest["adapter"]["revision"])
    return {
        "profile_id": spec["profile_id"],
        "manifest": str(spec["manifest"].relative_to(REPO_ROOT)),
        "manifest_sha256": _sha256(spec["manifest"]),
        "adapter_id": manifest["adapter"]["id"],
        "adapter_revision": manifest["adapter"]["revision"],
        "system_revision": manifest["system"]["revision"],
        "runtime_pin": pin,
        "supersedes": manifest["metadata"]["supersedes"],
        "checks": checks,
        "qualified": all(checks.values()),
        "run": first,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args(argv)
    head = _git("rev-parse", "HEAD")
    dirty = _git("status", "--porcelain", "--", "reference", "fixtures", "examples", "pyproject.toml")
    live = _live_configuration_digest()
    contestants = [qualify(spec, head, live) for spec in CONTESTANTS]
    record = {
        "schema_version": 1,
        "evidence_id": "agent-memory-public-v2-successors-local-qualification",
        "evidence_class": "local_pre_publication",
        "issue": 786,
        "baseline_id": "agent-memory-runtime-baseline-v7",
        "baseline_status": "unaccepted transition candidate; publication evidence comes from the docs/67 B1/B2 workflow runs",
        "executed_at_head": head,
        "worktree_clean_for_inputs": dirty == "",
        "environment": {"python": platform.python_version(), "sqlite": sqlite3.sqlite_version, "platform": sys.platform},
        "envelope_contract_version": contract.CONTRACT_VERSION,
        "store_open_contract": f"{store_contract.STORE_OPEN_CONTRACT_ID} {store_contract.STORE_OPEN_CONTRACT_VERSION}",
        "live_configuration_digest": live,
        "historical_v1_untouched": {
            str(spec["supersedes"].relative_to(REPO_ROOT)): _sha256(spec["supersedes"]) for spec in CONTESTANTS},
        "contestants": contestants,
        "qualified": all(item["qualified"] for item in contestants) and dirty == "",
        "authority_effect": "none",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for item in contestants:
        failed = [name for name, ok in item["checks"].items() if not ok]
        print(f"{item['adapter_id']}: {'QUALIFIED' if item['qualified'] else 'NOT QUALIFIED ' + str(failed)}")
    print(f"record: {args.out} qualified={record['qualified']}")
    return 0 if record["qualified"] else 1


if __name__ == "__main__":
    sys.exit(main())
