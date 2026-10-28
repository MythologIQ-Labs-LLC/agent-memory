"""Cross-branch regression: execute the frozen v7 replay fixtures on the integrated tree (#674 x #786).

The #786 security replay families and the #644 replays are frozen fixtures executed by frozen
runners, and their committed evidence binds the #836 protected tree. Their runners open several
projects in one SQLite root through ``AgentMemory.open``; on the integrated tree the default
``single_project_v1`` store profile refuses the second project before any case runs, so that
evidence cannot be re-recorded as-is and is marked for fresh qualification.

This harness is the non-recording cross-check. It runs every declared family with its frozen
fixture and frozen runner, unmodified, and replaces only the runners' store opener with the
test-only tenant-wide fixture in host-declared mode (``tests/_tenant_wide_fixture.py``), which
reproduces the pre-profile tenant-wide store and the contract 1.8.0 facade override semantics
the replays were written against. It then compares each family's observation digest with the
committed evidence, and also runs each family unpatched (default ``single_project_v1`` profile)
to record which frozen runners the store profile stops. Equal digests show the integrated canonical runtime behaves exactly as the
reviewed #836 runtime on every frozen case. It records nothing and grants nothing.

    PYTHONPATH=reference python reference/security_falsifiers/v7_integration_replay_crosscheck.py [--out PATH]
"""
from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

REFERENCE = Path(__file__).resolve().parents[1]
ROOT = REFERENCE.parent
sys.path.insert(0, str(REFERENCE))
sys.path.insert(0, str(ROOT / "scripts"))

from tests._tenant_wide_fixture import FrozenRunnerOpener  # noqa: E402

DECLARATION = ROOT / "reports" / "runtime" / "baseline-v7-declaration.json"
# The latest committed #836 evidence naming all five security families (digests are identical at 2d83db0e, 07cd8692, 2ad4cf23).
SECURITY_EVIDENCE = ROOT / "reports/validation/674-cumulative-candidate/security-replays-2ad4cf23d366fc784a486b0245550230e64bfa25"
REPLAY_EVIDENCE = ROOT / "reports/validation/674-cumulative-candidate/644-v7-replays-2ad4cf23d366fc784a486b0245550230e64bfa25"


@contextmanager
def tenant_wide(module, enabled=True):
    if not enabled:
        yield
        return
    with mock.patch.object(module, "AgentMemory", FrozenRunnerOpener):
        yield


def _row(kind, replay_id, run, module, evidence_root):
    committed = _committed_digest(evidence_root, replay_id)
    row = {"family": replay_id, "kind": kind, "committed_observations_sha256": committed}
    for label, enabled in (("tenant_wide_fixture", True), ("default_store_profile", False)):
        with tenant_wide(module, enabled):
            report = run(replay_id, allow_dirty=True)
        row[label] = {"cases": len(report["cases"]),
                      "failed_cases": [case["id"] for case in report["cases"] if case["outcome"] != "pass"],
                      "observations_sha256": report["observations_sha256"],
                      "identical_to_committed": report["observations_sha256"] == committed}
    row["identical_to_committed"] = row["tenant_wide_fixture"]["identical_to_committed"]
    return row


# The #836 families whose committed evidence this harness cross-checks. They are fixed here because the
# v7 declaration now names their scope-distinct successors (DSL/5), which this harness does not run.
FAMILIES = {
    "security_replay": ("cross-scope-write-authority-denial-v3", "deleted-lineage-generations-and-restart-v3",
                        "public-tombstone-redaction-and-observer-separation-v3", "evidence-reference-authorization-v1",
                        "scope-safe-graph-discovery-v2"),
    "replay": ("typed-sufficiency-noninterference-and-negative-controls-v1",
               "governed-persisted-typed-slot-sufficiency-admission-recheck-v1", "governed-admitted-typed-value-coherence-v1",
               "committed-governed-transition-witness-v1", "same-slot-safety-counterevidence-and-immutable-stop-gate-v1"),
}


def _declared(kind: str) -> list[str]:
    return list(FAMILIES[kind])


def _committed_digest(evidence_root: Path, replay_id: str) -> str | None:
    manifest = evidence_root / replay_id / "manifest.json"
    if not manifest.is_file():
        return None
    return json.loads(manifest.read_text(encoding="utf-8")).get("observations_sha256")


def security_replays() -> list[dict]:
    verifier = importlib.import_module("verify_786_security_replays")
    base = importlib.import_module("run_786_security_replays")
    return [_row("security_replay", replay_id, verifier.runner_for(replay_id, base.FIXTURE_DIR).run_replay, base,
                 SECURITY_EVIDENCE) for replay_id in _declared("security_replay")]


def replays_644() -> list[dict]:
    runner = importlib.import_module("run_644_v7_replays")
    return [_row("replay", replay_id, runner.run_replay, runner, REPLAY_EVIDENCE) for replay_id in _declared("replay")]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    rows = security_replays() + replays_644()
    git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    record = {"schema_version": 1, "harness": "v7-integration-replay-crosscheck",
              "source_commit": git("rev-parse", "HEAD"), "runtime_tree": git("rev-parse", "HEAD:reference/agentmem_ref"),
              "dirty_paths": [line[3:] for line in git("status", "--porcelain").splitlines()],
              "security_evidence": str(SECURITY_EVIDENCE.relative_to(ROOT)),
              "replay_evidence": str(REPLAY_EVIDENCE.relative_to(ROOT)), "rows": rows,
              "all_identical": all(row["identical_to_committed"] for row in rows),
              "records_evidence": False, "authority_effect": "none"}
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for row in rows:
        fixture, default = row["tenant_wide_fixture"], row["default_store_profile"]
        status = "IDENTICAL" if row["identical_to_committed"] else "DIFFERS"
        print(f"{status:9} {row['kind']:15} {row['family']}: {fixture['cases']} cases, failed {fixture['failed_cases']}; "
              f"default profile: identical={default['identical_to_committed']}, {len(default['failed_cases'])} not passing")
    print(f"all identical to committed evidence: {record['all_identical']}")
    return 0 if record["all_identical"] else 1


if __name__ == "__main__":
    sys.exit(main())
