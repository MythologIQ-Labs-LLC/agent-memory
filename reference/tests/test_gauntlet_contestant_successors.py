"""#786 successor Gauntlet contestants: identity, runtime pin, digest and real runs.

The v1 public-facade contestants drive several projects through one tenant-wide store,
which #786 store profiles refuse; their manifests, adapters and historical results are
preserved byte-for-byte and are not re-labelled. The v2 contestants differ only by
creating ``scope_distinct_v1`` stores. This module verifies each v2 identity independently
and runs both v2 contestants for real.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from agentmem_ref import AgentMemory
from agentmem_ref._paths import REPO_ROOT
from agentmem_ref.evaluation.contract import load_run
from agentmem_ref.evaluation.gauntlet_contract import validate_manifest
from agentmem_ref.evaluation.gauntlet_orchestrator import run_gauntlet
from agentmem_ref.evaluation.gauntlet_profiles import DURABILITY_RECOVERY_PROFILE_ID, GOVERNANCE_ALPHA_PROFILE_ID

from tests.test_gauntlet_durability import _case_map, _qualified_contestant_launch

FIXTURES = REPO_ROOT / "fixtures" / "gauntlet"
DURABILITY_V1 = FIXTURES / "agent-memory-public-durability-adapter.json"
DURABILITY_V2 = FIXTURES / "agent-memory-public-durability-adapter-v2.json"
GOVERNANCE_V1 = FIXTURES / "agent-memory-public-governance-adapter.json"
GOVERNANCE_V2 = FIXTURES / "agent-memory-public-governance-adapter-v2.json"
# Historical bytes, pinned before the successors existed (HEAD f83edbb4).
V1_MANIFEST_SHA256 = {
    DURABILITY_V1: "e33761c01f0245214fe542ba2483ebb2f4ba6a8bfa415f147d6fbaf14e09fbb5",
    GOVERNANCE_V1: "ef33d49bc24cf605cc205ff5835d77f5cd4ffeace6575d7318d68b0c1c1afd96",
}
V1_DURABILITY_ADAPTER_BLOB = "76b58bafa04ea7e10d9cf3f7ec915393cd586a40"
PROTECTED_RUNTIME = ["reference/agentmem_ref", ":(exclude)reference/agentmem_ref/evaluation/**", "pyproject.toml"]


def _blob(path: str) -> str:
    return subprocess.run(["git", "hash-object", path], cwd=REPO_ROOT, capture_output=True, text=True,
                          check=True).stdout.strip()


def _manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class HistoricalContestantPreservationTests(unittest.TestCase):
    def test_v1_manifests_and_adapter_are_byte_identical(self):
        for path, digest in V1_MANIFEST_SHA256.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest, path.name)
        self.assertEqual(_blob("reference/agentmem_ref/evaluation/gauntlet_agent_memory_durability.py"),
                         V1_DURABILITY_ADAPTER_BLOB)
        self.assertEqual(_manifest(DURABILITY_V1)["adapter"]["revision"], f"git-blob:{V1_DURABILITY_ADAPTER_BLOB}")

    def test_v1_contestants_are_refused_by_the_supported_contract(self):
        # Classification, not a pass: v1 is incompatible with #786 store profiles.
        with tempfile.TemporaryDirectory() as temporary:
            result = run_gauntlet(GOVERNANCE_V1, GOVERNANCE_ALPHA_PROFILE_ID, output_dir=Path(temporary) / "runs")
        self.assertEqual(result["status"], "blocked")
        self.assertIn("StoreIdentityError", result["failure"]["message"])

    def test_successors_name_the_exact_manifests_they_supersede(self):
        for v1, v2 in ((DURABILITY_V1, DURABILITY_V2), (GOVERNANCE_V1, GOVERNANCE_V2)):
            supersedes = _manifest(v2)["metadata"]["supersedes"]
            self.assertEqual(supersedes["manifest"], str(v1.relative_to(REPO_ROOT)))
            self.assertEqual(supersedes["sha256"], hashlib.sha256(v1.read_bytes()).hexdigest())


class SuccessorIdentityTests(unittest.TestCase):
    def test_manifests_validate_and_identities_are_distinct(self):
        for v1, v2 in ((DURABILITY_V1, DURABILITY_V2), (GOVERNANCE_V1, GOVERNANCE_V2)):
            new = validate_manifest(_manifest(v2))
            self.assertNotEqual(new["adapter"]["id"], _manifest(v1)["adapter"]["id"])
            self.assertEqual(new["metadata"]["store_profile"], "scope_distinct_v1")

    def test_adapter_and_wrapper_revisions_are_the_real_blobs(self):
        durability = _manifest(DURABILITY_V2)
        self.assertEqual(durability["adapter"]["revision"],
                         "git-blob:" + _blob("reference/agentmem_ref/evaluation/gauntlet_agent_memory_durability_v2.py"))
        self.assertEqual(durability["metadata"]["transport_wrapper_revision"],
                         "git-blob:" + _blob("examples/gauntlet/agent_memory_durability_v2_stdio.py"))
        self.assertEqual(_manifest(GOVERNANCE_V2)["adapter"]["revision"],
                         "git-blob:" + _blob("reference/agentmem_ref/evaluation/gauntlet_agent_memory_v2.py"))

    def test_pinned_runtime_commit_is_the_runtime_under_test(self):
        pins = {
            _manifest(DURABILITY_V2)["system"]["revision"].removeprefix("git-commit:"),
            _manifest(GOVERNANCE_V2)["system"]["revision"].split("@", 1)[1],
        }
        self.assertEqual(len(pins), 1)
        pin = pins.pop()
        drift = subprocess.run(["git", "diff", "--name-only", pin, "--", *PROTECTED_RUNTIME], cwd=REPO_ROOT,
                               capture_output=True, text=True, check=True).stdout.split()
        self.assertEqual(drift, [], "the protected runtime differs from the commit the successors pin; re-pin them")

    def test_v7_declaration_requires_both_successor_runs(self):
        declaration = json.loads((REPO_ROOT / "reports" / "runtime" / "baseline-v7-declaration.json").read_text())
        required = {(item["kind"], item["ref"]) for item in declaration["acceptance_evidence_required"]}
        self.assertIn(("public_gauntlet", f"{DURABILITY_RECOVERY_PROFILE_ID}:agent-memory-public-durability-adapter-v2"),
                      required)
        self.assertIn(("public_gauntlet", f"{GOVERNANCE_ALPHA_PROFILE_ID}:agent-memory-public-governance-adapter-v2"),
                      required)

    def test_configuration_digest_is_the_live_runtime_digest(self):
        with tempfile.TemporaryDirectory() as temp:
            with AgentMemory.open(temp, store_profile="scope_distinct_v1") as memory:
                live = memory.posture()["posture"]["configuration"]["digest"]
        self.assertEqual(_manifest(DURABILITY_V2)["system"]["configuration_digest"], live)


class SuccessorRunTests(unittest.TestCase):
    def test_durability_successor_qualifies_with_scope_isolation_and_digest(self):
        with tempfile.TemporaryDirectory() as temporary, _qualified_contestant_launch():
            result = run_gauntlet(DURABILITY_V2, DURABILITY_RECOVERY_PROFILE_ID, output_dir=Path(temporary) / "runs",
                                  allow_external_process=True, allow_destructive_operations=True)
            self.assertEqual(result["status"], "complete", result)
            run = load_run(result["artifacts"]["normalized_run"]["path"])
            manifest = _manifest(DURABILITY_V2)
            # The run records the manifest's identity; the recover evidence below is the
            # independent, live check of the digest.
            self.assertEqual(run["system"]["configuration_digest"],
                             manifest["system"]["configuration_digest"].removeprefix("sha256:"))
            self.assertEqual(run["system"]["adapter_revision"], manifest["adapter"]["revision"])
            native = json.loads(Path(result["artifacts"]["native_results"]["path"]).read_text(encoding="utf-8"))
        cases = _case_map(run)
        for case_id in ("DUR-REC-001", "DUR-DEL-001", "DUR-DET-001", "DUR-ISO-001"):
            self.assertEqual(cases[case_id]["behavioral_outcome"], "pass", cases[case_id])
            self.assertEqual(cases[case_id]["evidence_qualification"], "sufficient", cases[case_id])
        for case_id in ("DUR-COR-001", "DUR-CHK-001"):
            self.assertEqual(cases[case_id]["behavioral_outcome"], "unsupported")
            self.assertFalse(cases[case_id]["transition"]["operation_executed"])
        self.assertEqual(run["authority_effect"], "none")

    def test_successor_recover_reports_the_manifest_digest_live(self):
        # Independent check: the digest the running v2 contestant observes from the live
        # runtime posture equals the digest its manifest declares.
        from agentmem_ref.evaluation.gauntlet_agent_memory_durability_v2 import agent_memory_durability_adapter
        from agentmem_ref.evaluation.gauntlet_durability import _request

        namespace = f"successor-digest-{id(self)}"
        payload = {"namespace": namespace, "scope": "project:digest"}
        try:
            remembered = agent_memory_durability_adapter(_request("remember", "r1", {
                **payload, "record": {"id": "memory:digest", "text": "digest probe"}}))
            self.assertEqual(remembered["status"], "ok", remembered)
            recovered = agent_memory_durability_adapter(_request("recover", "r2", payload))
            described = agent_memory_durability_adapter(_request("describe", "r3", {"namespace": namespace}))
        finally:
            agent_memory_durability_adapter(_request("reset", "r4", {"namespace": namespace}))
        self.assertEqual(recovered["result"]["configuration_digest"],
                         _manifest(DURABILITY_V2)["system"]["configuration_digest"])
        self.assertEqual(recovered["result"]["store_profile"], "scope_distinct_v1")
        self.assertEqual(described["result"]["store_profile"], "scope_distinct_v1")

    def test_governance_successor_keeps_every_v1_claim_boundary(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = run_gauntlet(GOVERNANCE_V2, GOVERNANCE_ALPHA_PROFILE_ID, output_dir=Path(temporary) / "runs")
            self.assertEqual(result["status"], "complete", result)
            run = load_run(result["artifacts"]["normalized_run"]["path"])
        cases = {case["case_id"]: case for case in run["native_results"]["cases"]}
        for case_id in ("GOV-ISO-001", "GOV-ISO-005", "GOV-AUTH-002", "GOV-AUTH-003"):
            self.assertEqual(cases[case_id]["result"], "unsupported", case_id)
        self.assertEqual(cases["GOV-ISO-002"]["result"], "pass", cases["GOV-ISO-002"])
        self.assertEqual(cases["GOV-DEL-001"]["result"], "pass", cases["GOV-DEL-001"])
        self.assertEqual(cases["GOV-DEL-002"]["result"], "blocked")
        self.assertEqual(run["dimensions"]["governance"]["status"], "partial")
        self.assertEqual(run["authority_effect"], "none")


if __name__ == "__main__":
    unittest.main()
