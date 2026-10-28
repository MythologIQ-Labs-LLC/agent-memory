"""v7 declaration requalification: every acceptance item resolves to a concrete, bound artefact.

The declaration schema admits the kinds (including ``formal_replay``); these checks make each item
resolve, so an acceptance list cannot name evidence that does not exist or is bound to another
identity:

* ``replay``: a frozen #644 fixture;
* ``security_replay``: a frozen #786 fixture whose ``dsl_version`` the security verifier dispatches;
* ``formal_replay``: a formal freeze that
  - binds the declaration's target public contract and the candidate's protected runtime tree,
  - supersedes its predecessor's exact bytes,
  - has not been executed (no committed report for its run id);
* ``lane``: a v7 lane spec pinning this declaration's blob;
* ``public_gauntlet``: a registered profile and an existing contestant manifest.
"""
from __future__ import annotations

import hashlib
import json
import runpy
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DECLARATION_PATH = "reports/runtime/baseline-v7-declaration.json"
DECLARATION = json.loads((ROOT / DECLARATION_PATH).read_text(encoding="utf-8"))
FREEZES = ROOT / "reference/fixtures/benchmarks/agentmembench"
FORMAL_REPORTS = ROOT / "reports/benchmarks/agentmembench-mesa-formal"


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def _items(kind: str) -> list[str]:
    return [item["ref"] for item in DECLARATION["acceptance_evidence_required"] if item["kind"] == kind]


def _target_contract() -> str:
    deltas = {d["identity_path"]: d["to"] for d in DECLARATION["identity_deltas"]}
    return deltas["identity.public_contract_version"]


class AcceptanceItemBindingTests(unittest.TestCase):
    def test_every_kind_present_is_resolved_by_this_module(self):
        kinds = {item["kind"] for item in DECLARATION["acceptance_evidence_required"]}
        self.assertLessEqual(kinds, {"replay", "security_replay", "formal_replay", "lane", "public_gauntlet"})
        refs = [(i["kind"], i["ref"]) for i in DECLARATION["acceptance_evidence_required"]]
        self.assertEqual(len(refs), len(set(refs)))

    def test_replays_name_frozen_fixtures(self):
        for ref in _items("replay"):
            with self.subTest(ref=ref):
                fixture = json.loads((ROOT / "reference/fixtures/644-v7-replays" / f"{ref}.json").read_text(encoding="utf-8"))
                self.assertEqual(fixture["replay_id"], ref)

    def test_security_replays_name_frozen_fixtures_the_verifier_dispatches(self):
        verifier = runpy.run_path(str(ROOT / "scripts/verify_786_security_replays.py"))
        for ref in _items("security_replay"):
            with self.subTest(ref=ref):
                fixture = json.loads((ROOT / "reference/fixtures/786-security-replays" / f"{ref}.json").read_text(encoding="utf-8"))
                self.assertEqual(fixture["replay_id"], ref)
                self.assertIn(fixture["dsl_version"], verifier["RUNNERS"])

    def test_formal_replays_name_unexecuted_freezes_bound_to_the_declared_identity(self):
        refs = _items("formal_replay")
        self.assertTrue(refs)
        tree = _git("rev-parse", "HEAD:reference/agentmem_ref")
        for ref in refs:
            with self.subTest(ref=ref):
                freeze_path = FREEZES / f"{ref}-freeze.json"
                freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
                self.assertEqual(freeze["freeze_id"], f"agent-memory-agentmembench-{ref}")
                self.assertEqual(freeze["agent_memory"]["public_contract_version"], _target_contract())
                self.assertEqual(freeze["agent_memory"]["runtime_tree"], tree,
                                 "the protected runtime moved after the formal freeze; refreeze before any run")
                predecessor = ROOT / freeze["supersedes"]["path"]
                self.assertEqual(hashlib.sha256(predecessor.read_bytes()).hexdigest(), freeze["supersedes"]["sha256"])
                self.assertFalse((FORMAL_REPORTS / f"{freeze['run_id']}.json").exists(),
                                 "a formal freeze is executed only once; a report exists for this run id")
                self.assertIn("not executed", freeze["status"])

    def test_lanes_pin_this_declaration(self):
        blob = _git("hash-object", DECLARATION_PATH)
        for ref in _items("lane"):
            with self.subTest(ref=ref):
                spec_text = (ROOT / "reference/agentmem_ref/evaluation/lanes" / f"{ref}.json").read_text(encoding="utf-8")
                self.assertEqual(set(_declaration_blobs(json.loads(spec_text))), {blob})

    def test_public_gauntlet_items_name_registered_profiles_and_existing_manifests(self):
        from agentmem_ref.evaluation.gauntlet_profiles import list_gauntlet_profiles

        profiles = {p["profile_id"] for p in list_gauntlet_profiles()}
        for ref in _items("public_gauntlet"):
            with self.subTest(ref=ref):
                profile, _, contestant = ref.partition(":")
                self.assertIn(profile, profiles)
                if contestant:
                    self.assertTrue((ROOT / "fixtures/gauntlet" / f"{contestant}.json").is_file())


def _declaration_blobs(node) -> list[str]:
    found = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "declaration_blob" and isinstance(value, str):
                found.append(value)
            else:
                found.extend(_declaration_blobs(value))
    elif isinstance(node, list):
        for value in node:
            found.extend(_declaration_blobs(value))
    return found


if __name__ == "__main__":
    unittest.main()
