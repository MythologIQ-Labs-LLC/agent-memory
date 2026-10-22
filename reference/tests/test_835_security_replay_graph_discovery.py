"""#835 / #836: the scope-safe graph discovery security replay (DSL/4) is frozen, falsifiable and verifiable.

Mirrors the family tests of the earlier generations (test_786_security_replays_v3,
test_809_security_replay_v1): fixture integrity against its base commit, every case holds on the
current runtime, negative controls prove the contract can fail, and the verifier dispatches the
fixture to the DSL/4 runner. Nothing here grants acceptance.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import run_786_security_replays_dsl4 as runner  # noqa: E402  (reference/ is the test top-level directory)
from agentmem_ref import recall_control

ROOT = Path(__file__).resolve().parents[2]
REPLAY = "scope-safe-graph-discovery-v2"
SUPERSEDED = "scope-safe-graph-discovery-v1"
DECLARATION = ROOT / "reports/runtime/baseline-v7-declaration.json"


def _fixture(replay_id: str) -> dict:
    return json.loads((runner.FIXTURE_DIR / f"{replay_id}.json").read_text(encoding="utf-8"))


def _run(ids: set[str] | None = None, fixture: dict | None = None) -> dict:
    fx = fixture or _fixture(REPLAY)
    out = {}
    with tempfile.TemporaryDirectory() as tmp:
        for i, case in enumerate(fx["cases"]):
            if ids is None or case["id"] in ids:
                work = Path(tmp) / f"c{i}"
                work.mkdir()
                out[case["id"]] = runner.run_case(case, work)
    return out


class FixtureIntegrity(unittest.TestCase):
    def test_identity_status_and_supersession(self):
        fx = _fixture(REPLAY)
        self.assertEqual((fx["replay_id"], fx["dsl_version"], fx["status"], fx["owning_issue"]),
                         (REPLAY, runner.DSL_VERSION, "frozen_before_execution", 835))
        self.assertEqual(runner.REPLAYS, (REPLAY,))
        self.assertEqual(runner.SUPERSEDED, (SUPERSEDED,))
        v1 = _fixture(SUPERSEDED)
        self.assertEqual(fx["supersedes"]["replay_id"], SUPERSEDED)
        self.assertEqual(fx["supersedes"]["fixture_sha256"], runner.sha256_file(runner.FIXTURE_DIR / f"{SUPERSEDED}.json"))
        # -v2 differs from -v1 in exactly the two recorded observables and the identity/supersession fields
        a, b = copy.deepcopy(v1), copy.deepcopy(fx)
        for key in ("replay_id", "fixture_version", "base_commit", "supersedes"):
            a.pop(key, None), b.pop(key, None)
        for c1, c2 in zip(a["cases"], b["cases"]):
            if c1["id"] in ("G7-deleted-bridge-confers-no-reachability", "G9-direct-live-path-survives-deleted-alternate"):
                self.assertEqual(c1["expect"]["old_refusal"], {"eq": "logical_memory_deleted"})
                self.assertEqual(c2["expect"]["old_refusal"], {"in": ["tombstoned", "logical_memory_deleted"]})
                c1["expect"].pop("old_refusal"), c2["expect"].pop("old_refusal")
            self.assertEqual(c1, c2, c1["id"])
        self.assertEqual(a, b)

    def test_contract_sources_hash_the_documents_at_the_base_commit(self):
        for replay_id in (SUPERSEDED, REPLAY):
            fx = _fixture(replay_id)
            for source in fx["contract_sources"]:
                shown = subprocess.run(["git", "show", f"{fx['base_commit']}:{source['path']}"], cwd=ROOT,
                                       capture_output=True, check=False)
                if shown.returncode != 0:
                    self.skipTest("base commit not available in this checkout")
                self.assertEqual(runner.sha256_bytes(shown.stdout), source["sha256_at_base"], source["path"])

    def test_every_invariant_is_exercised_and_every_expectation_cites_a_clause(self):
        fx = _fixture(REPLAY)
        ids = [c["id"] for c in fx["cases"]]
        self.assertEqual(len(ids), len(set(ids)))
        covered = {inv for c in fx["cases"] for inv in c["invariants"]}
        self.assertEqual(covered, {inv["id"] for inv in fx["invariants"]})
        for case in fx["cases"]:
            self.assertTrue(case["expect"], case["id"])
            cited = {obs for clause in case["clauses"] for obs in clause["observables"]}
            for observable, matcher in case["expect"].items():
                self.assertEqual(len(matcher), 1)
                self.assertIn(next(iter(matcher)), ("eq", "ne", "in", "not_in"))
                if observable not in case.get("controls", ()):  # a declared positive control cites no clause
                    self.assertIn(observable, cited, f"{case['id']}: {observable} is expected without a clause")
            for observable in case.get("implementation_evidence", ()):
                self.assertNotIn(observable, case["expect"], f"{case['id']}: {observable} is evidence, never expected")

    def test_no_frozen_holdout_vocabulary(self):
        text = (runner.FIXTURE_DIR / f"{REPLAY}.json").read_text(encoding="utf-8")
        for entity in ("Kestrel router", "Marlow invoice", "Quill warehouse", "Tamsin satellite", "Brisk ledger",
                       "Copperfield lab", "Orrin gateway", "kiln firing schedule"):
            self.assertNotIn(entity, text)


class ReplayRegression(unittest.TestCase):
    def test_every_case_holds_on_the_current_runtime(self):
        report = runner.run_replay(REPLAY, allow_dirty=True)
        failing = [(c["id"], c["error"] or [x for x in c["checks"] if not x["holds"]])
                   for c in report["cases"] if c["outcome"] != "pass"]
        self.assertEqual(failing, [])
        self.assertIn(report["verdict"], ("PASS", "BLOCKED"))
        self.assertEqual(report["summary"]["cases"], 11)
        limitation = next(c for c in report["cases"] if c["id"] == "G10-eligibility-probe-ceiling-recorded")
        self.assertIn("late_admitted", limitation["recorded"])  # recorded, never expected

    def test_declaration_names_this_generation_and_not_the_placeholder(self):
        record = json.loads(DECLARATION.read_text(encoding="utf-8"))
        refs = [e["ref"] for e in record["acceptance_evidence_required"] if e["kind"] == "security_replay"]
        self.assertIn(REPLAY, refs)
        self.assertNotIn(SUPERSEDED, refs)
        self.assertNotIn("scope-safe-graph-discovery-v7", [e["ref"] for e in record["acceptance_evidence_required"]])


class NegativeControls(unittest.TestCase):
    """Each contract must be able to fail: remove the guard it exercises and the case turns red."""

    def _without(self, *predicate_names: str):
        original = recall_control.NativeTypedGraphCandidateRetriever.search

        def search(self, substrate, seed_refs, **kw):
            for name in predicate_names:
                kw[name] = None
            return original(self, substrate, seed_refs, **kw)
        return mock.patch.object(recall_control.NativeTypedGraphCandidateRetriever, "search", search)

    def test_dropping_hop_eligibility_turns_isolation_cases_red(self):
        # both #835 predicates guard a hop (identity first, then the fact); dropping either alone is
        # caught by the other, so the control drops both
        with self._without("eligible", "eligible_identity"):
            out = _run({"G2-inaccessible-neighbour-never-reported", "G3-no-hop-through-inaccessible-intermediate",
                        "G4-fanout-not-spent-on-ineligible-neighbours"})
        self.assertEqual({k: v["outcome"] for k, v in out.items()},
                         {k: "fail" for k in out}, {k: v["checks"] for k, v in out.items()})

    def test_dropping_the_opaque_predicate_turns_the_deleted_bridge_red(self):
        with self._without("opaque"):
            out = _run({"G7-deleted-bridge-confers-no-reachability", "G8-withheld-seed-not-expanded"})
        self.assertEqual(out["G7-deleted-bridge-confers-no-reachability"]["outcome"], "fail")
        self.assertEqual(out["G8-withheld-seed-not-expanded"]["outcome"], "fail")

    def test_dropping_the_exclusion_turns_the_reported_path_red(self):
        with self._without("exclude"):
            out = _run({"G9-direct-live-path-survives-deleted-alternate"})
        self.assertEqual(out["G9-direct-live-path-survives-deleted-alternate"]["outcome"], "fail")


class VerifierDispatch(unittest.TestCase):
    def test_verifier_picks_the_dsl4_runner_for_this_fixture(self):
        spec = importlib.util.spec_from_file_location("verify_786_security_replays", ROOT / "scripts/verify_786_security_replays.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertIs(module.runner_for(REPLAY, module.runner.FIXTURE_DIR), module.runner_dsl4)
        self.assertIs(module.runner_for("evidence-reference-authorization-v1", module.runner.FIXTURE_DIR), module.runner_dsl3)


if __name__ == "__main__":
    unittest.main()
