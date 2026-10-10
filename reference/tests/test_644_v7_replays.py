"""#644 v7 replay packages: fixture integrity, regression, falsifiability and tamper detection.

The five replays are executed through the real runner. Negative controls prove each
contract can fail: a deliberately faulty observer, census, witness or receipt check must
turn the matching replay case red. Verifier tests prove that mutated fixtures, outputs,
membership evidence and provenance references are detected.
"""
from __future__ import annotations

import copy
import json
import runpy
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
import run_644_v7_replays as runner  # noqa: E402  (reference/ is the test top-level directory)

verifier = runpy.run_path(str(ROOT / "scripts/verify_644_v7_replays.py"))
inventory = runpy.run_path(str(ROOT / "scripts/check_644_v7_replay_inventory.py"))["inventory"]
DECLARATION = ROOT / "reports/runtime/baseline-v7-declaration.json"


def declared() -> list[str]:
    record = json.loads(DECLARATION.read_text(encoding="utf-8"))
    return [x["ref"] for x in record["acceptance_evidence_required"] if x["kind"] == "replay"]


def fixture(replay_id: str) -> dict:
    return json.loads((runner.FIXTURE_DIR / f"{replay_id}.json").read_text(encoding="utf-8"))


def run_cases(replay_id: str, ids: set[str] | None = None) -> dict:
    fx = fixture(replay_id)
    out = {}
    with tempfile.TemporaryDirectory() as tmp:
        for i, case in enumerate(fx["cases"]):
            if ids is None or case["id"] in ids:
                work = Path(tmp) / f"c{i}"
                work.mkdir()
                out[case["id"]] = runner.run_case(case, work)
    return out


class FixtureIntegrity(unittest.TestCase):
    def test_every_declared_replay_has_a_frozen_fixture(self):
        self.assertEqual(sorted(declared()), sorted(runner.REPLAYS))
        for replay_id in declared():
            fx = fixture(replay_id)
            self.assertEqual(fx["replay_id"], replay_id)
            self.assertEqual(fx["dsl_version"], runner.DSL_VERSION)
            self.assertEqual(fx["status"], "frozen_before_execution")

    def test_every_invariant_is_exercised_and_cases_are_unique(self):
        for replay_id in declared():
            fx = fixture(replay_id)
            ids = [c["id"] for c in fx["cases"]]
            self.assertEqual(len(ids), len(set(ids)), replay_id)
            invariants = {i["id"] for i in fx["invariants"]}
            covered = {x for c in fx["cases"] for x in c["invariants"]}
            self.assertEqual(invariants, covered, replay_id)
            for case in fx["cases"]:
                self.assertTrue(case["expect"], case["id"])
                for matcher in case["expect"].values():
                    self.assertEqual(len(matcher), 1)
                    self.assertIn(next(iter(matcher)), ("eq", "ne", "in", "not_in"))

    def test_contract_sources_hash_the_documents_at_the_base_commit(self):
        for replay_id in declared():
            fx = fixture(replay_id)
            for source in fx["contract_sources"]:
                shown = subprocess.run(["git", "show", f"{fx['base_commit']}:{source['path']}"], cwd=ROOT,
                                       capture_output=True, check=False)
                if shown.returncode != 0:
                    self.skipTest("base commit not available in this checkout")
                self.assertEqual(runner.sha256_bytes(shown.stdout), source["sha256_at_base"], source["path"])

    def test_fixtures_do_not_reuse_the_original_holdout_vocabulary(self):
        holdout_entities = ("Kestrel router", "Marlow invoice", "Quill warehouse", "Tamsin satellite", "Brisk ledger",
                            "Copperfield lab", "Orrin gateway")
        for replay_id in declared():
            text = (runner.FIXTURE_DIR / f"{replay_id}.json").read_text(encoding="utf-8")
            for entity in holdout_entities:
                self.assertNotIn(entity, text, replay_id)


class ReplayRegression(unittest.TestCase):
    """Every frozen case must hold on the current runtime."""

    def test_all_replay_cases_hold(self):
        for replay_id in declared():
            report = runner.run_replay(replay_id, allow_dirty=True)
            with self.subTest(replay=replay_id):
                failing = [(c["id"], c["error"] or [x for x in c["checks"] if not x["holds"]])
                           for c in report["cases"] if c["outcome"] != "pass"]
                self.assertEqual(failing, [])
                self.assertIn(report["verdict"], ("PASS", "BLOCKED"))

    def test_dirty_tree_never_yields_pass(self):
        with mock.patch.object(runner, "provenance", side_effect=lambda p: {**PROV, "fixture": {"path": str(p), "sha256": "x"}}):
            report = runner.run_replay("committed-governed-transition-witness-v1", allow_dirty=False)
        self.assertEqual(report["verdict"], "BLOCKED")


PROV = {"source_commit": "0" * 40, "runtime_tree": "0" * 40, "dirty_paths": ["reference/agentmem_ref/x.py"],
        "dirty_exclusion": runner.OUTPUT_REL, "runner": {"path": "r", "sha256": "x", "version": "v"},
        "python": "3", "sqlite": "3", "platform": "p"}


class NegativeControls(unittest.TestCase):
    """Each contract must be able to fail: inject the defect it guards against."""

    def test_expectation_mutation_turns_case_red(self):
        fx = fixture("governed-admitted-typed-value-coherence-v1")
        case = copy.deepcopy(next(c for c in fx["cases"] if c["id"] == "V3-competing-values"))
        case["expect"]["coherence_status"] = {"eq": "same_value_observed"}
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(runner.run_case(case, Path(tmp))["outcome"], "fail")

    def test_noninterference_detects_a_writing_observer(self):
        original = runner.ControlledRecallPlanner.observe_persisted_typed_coverage

        def writing(planner, result, ctx, *, needs):
            planner.adapter.events.append({"injected": "observer side effect"})
            return original(planner, result, ctx, needs=needs)

        with mock.patch.object(runner.ControlledRecallPlanner, "observe_persisted_typed_coverage", writing):
            out = run_cases("typed-sufficiency-noninterference-and-negative-controls-v1", {"N1-twin-lifecycle"})
        self.assertEqual(out["N1-twin-lifecycle"]["outcome"], "fail")

    def test_stop_gate_detects_a_stop_proposal(self):
        original = runner.ControlledRecallPlanner.observe_persisted_typed_coverage

        def stopping(planner, result, ctx, *, needs):
            report = original(planner, result, ctx, needs=needs)
            return runner.dataclasses.replace(report, continuation_proposal="review_stop")

        with mock.patch.object(runner.ControlledRecallPlanner, "observe_persisted_typed_coverage", stopping):
            out = run_cases("same-slot-safety-counterevidence-and-immutable-stop-gate-v1", {"S1-agreeing-coverage-never-stops"})
        self.assertEqual(out["S1-agreeing-coverage-never-stops"]["outcome"], "fail")

    def test_hidden_competitor_detection_depends_on_the_census(self):
        def blind(adapter, slots, admitted, ctx):
            return {s: {"eligible_unretrieved": 0, "qualified_counter_evidence": 0, "declared_temporal_boundary": 0}
                    for s in slots}

        from agentmem_ref.runtime.adapter import GovernedMemoryAdapter
        with mock.patch.object(GovernedMemoryAdapter, "current_typed_slot_obstacles", blind):
            out = run_cases("governed-persisted-typed-slot-sufficiency-admission-recheck-v1",
                            {"A6-hidden-admissible-competitor-counted"})
        self.assertEqual(out["A6-hidden-admissible-competitor-counted"]["outcome"], "fail")

    def test_witness_contract_detects_an_inferred_application(self):
        from agentmem_ref.runtime import governed_transition_witness as gtw
        from agentmem_ref.runtime.adapter import GovernedMemoryAdapter

        def eager(adapter, refs, ctx):
            if len(refs) < 2:
                return ()
            return (gtw.GovernedTransitionWitness(source_fact_ref=refs[1], prior_fact_ref=refs[0],
                                                  current_target_fact_ref=refs[1], proposal_ref="p",
                                                  correction_proposal_ref="c", replacement_kind="state_change"),)

        with mock.patch.object(GovernedMemoryAdapter, "governed_applied_transition_witnesses", eager):
            out = run_cases("committed-governed-transition-witness-v1", {"T1-asserted-change-only"})
        self.assertEqual(out["T1-asserted-change-only"]["outcome"], "fail")

    def test_receipt_gate_detects_blind_verification(self):
        with mock.patch.object(runner.rr.RecallObservationReceipt, "matches_mutable_result", lambda self, **kw: True):
            out = run_cases("same-slot-safety-counterevidence-and-immutable-stop-gate-v1", {"S4-mutation-change_query"})
        self.assertEqual(out["S4-mutation-change_query"]["outcome"], "fail")

    def test_admission_recheck_detects_stale_support(self):
        # Remove both read-time gates (admission and semantics visibility) for tombstoned facts:
        # a forgotten fact then keeps supporting the slot, and A3 must turn red.
        from agentmem_ref.runtime.adapter import GovernedMemoryAdapter
        original_refusal = GovernedMemoryAdapter._admission_refusal

        def lenient(adapter, fact, ctx, *args, **kwargs):
            reason = original_refusal(adapter, fact, ctx, *args, **kwargs)
            return None if reason == "tombstoned" else reason

        def visible(adapter, fact_uuid, ctx):
            return adapter._substrate.get_fact(fact_uuid)

        with mock.patch.object(GovernedMemoryAdapter, "_admission_refusal", lenient), \
                mock.patch.object(GovernedMemoryAdapter, "_semantics_visible", visible):
            out = run_cases("governed-persisted-typed-slot-sufficiency-admission-recheck-v1", {"A3-recheck-after-forget"})
        self.assertEqual(out["A3-recheck-after-forget"]["outcome"], "fail")


class EvidenceVerification(unittest.TestCase):
    REPLAY = "committed-governed-transition-witness-v1"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.declaration = self.root / "declaration.json"
        self.declaration.write_text(json.dumps({
            "baseline_id": "agent-memory-runtime-baseline-v7", "issue": 644,
            "acceptance_evidence_required": [{"kind": "replay", "ref": self.REPLAY}]}), encoding="utf-8")
        self.fixtures = self.root / "fixtures"
        self.fixtures.mkdir()
        shutil.copy(runner.FIXTURE_DIR / f"{self.REPLAY}.json", self.fixtures)
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        tree = subprocess.run(["git", "rev-parse", "HEAD:reference/agentmem_ref"], cwd=ROOT, capture_output=True,
                              text=True).stdout.strip()
        clean = {"source_commit": head, "runtime_tree": tree, "dirty_paths": [], "dirty_exclusion": runner.OUTPUT_REL,
                 "runner": {"path": "reference/run_644_v7_replays.py", "sha256": runner.sha256_file(Path(runner.__file__)),
                            "version": runner.RUNNER_VERSION}, "python": "3", "sqlite": "3", "platform": "p"}
        with mock.patch.object(runner, "provenance", side_effect=lambda p: {**clean, "fixture": {
                "path": str(p), "sha256": runner.sha256_file(p)}}):
            report = runner.run_replay(self.REPLAY, fixture_dir=self.fixtures)
        self.evidence = self.root / "evidence"
        runner.write_outputs(report, self.evidence, "test")
        self.report_path = self.evidence / self.REPLAY / "report.json"
        self.manifest_path = self.evidence / self.REPLAY / "manifest.json"

    def tearDown(self):
        self.tmp.cleanup()

    def status(self, reexecute=False):
        row = verifier["verify"](self.evidence, self.declaration, self.fixtures, reexecute)["replays"][0]
        return row["status"], row["problems"]

    def rewrite(self, mutate_report=None, mutate_manifest=None, rehash=True):
        report = json.loads(self.report_path.read_text())
        if mutate_report:
            mutate_report(report)
        data = json.dumps(report, indent=1, sort_keys=True).encode() + b"\n"
        self.report_path.write_bytes(data)
        manifest = json.loads(self.manifest_path.read_text())
        if rehash:
            manifest["report"]["sha256"] = runner.sha256_bytes(data)
        if mutate_manifest:
            mutate_manifest(manifest)
        self.manifest_path.write_text(json.dumps(manifest))

    def test_untampered_evidence_verifies_and_reexecutes(self):
        status, problems = self.status(reexecute=True)
        self.assertEqual((status, problems), ("VERIFIED", []))

    def test_unhashed_output_edit_is_detected(self):
        self.rewrite(lambda r: r["cases"][0]["observations"].update(witness_count=9), rehash=False)
        self.assertEqual(self.status()[0], "TAMPERED")

    def test_rehashed_observation_edit_is_detected(self):
        def flip(r):
            case = next(c for c in r["cases"] if c["id"] == "T2-applied-state-change")
            case["observations"]["witness_count"] = 0
        self.rewrite(flip)
        self.assertEqual(self.status()[0], "TAMPERED")

    def test_membership_evidence_edit_is_detected_even_when_fully_rehashed(self):
        def forge(r):
            case = next(c for c in r["cases"] if c["id"] == "T4-source-only")
            case["observations"]["witness_count"] = 1
            for check in case["checks"]:
                check["observed"], check["matcher"], check["holds"] = 1, {"eq": 1}, True
            r["observations_sha256"] = verifier["observations_digest"](r)
        self.rewrite(forge, lambda m: m.update(observations_sha256=None))
        status, problems = self.status()
        self.assertEqual(status, "TAMPERED")
        self.assertTrue(any("expectations" in p or "digest" in p for p in problems))

    def test_consistently_forged_observations_fail_reexecution(self):
        def forge(r):
            case = next(c for c in r["cases"] if c["id"] == "T9-restart")
            case["observations"]["state_unchanged_extra"] = True
            r["observations_sha256"] = verifier["observations_digest"](r)
        report = json.loads(self.report_path.read_text())
        forge(report)
        self.rewrite(lambda r: r.update(report), lambda m: m.update(observations_sha256=report["observations_sha256"]))
        self.assertEqual(self.status(reexecute=False)[0], "VERIFIED")
        status, problems = self.status(reexecute=True)
        self.assertEqual(status, "TAMPERED")
        self.assertIn("re-execution produced different observations", problems)

    def test_dropped_failing_check_is_detected(self):
        self.rewrite(lambda r: r["cases"][1].update(checks=r["cases"][1]["checks"][1:]))
        self.assertEqual(self.status()[0], "TAMPERED")

    def test_verdict_upgrade_is_detected(self):
        def upgrade(r):
            r["cases"][0]["outcome"] = "fail"
            r["verdict"] = "PASS"
        self.rewrite(upgrade)
        self.assertEqual(self.status()[0], "TAMPERED")

    def test_fixture_edit_after_execution_is_detected(self):
        path = self.fixtures / f"{self.REPLAY}.json"
        fx = json.loads(path.read_text())
        fx["cases"][0]["expect"]["witness_count"] = {"eq": 5}
        path.write_text(json.dumps(fx))
        self.assertEqual(self.status()[0], "TAMPERED")

    def test_forged_provenance_reference_is_detected(self):
        self.rewrite(lambda r: r["provenance"].update(source_commit="f" * 40),
                     lambda m: m.update(source_commit="f" * 40))
        self.assertEqual(self.status()[0], "TAMPERED")

    def test_runtime_tree_substitution_is_detected(self):
        self.rewrite(lambda r: r["provenance"].update(runtime_tree="e" * 40), lambda m: m.update(runtime_tree="e" * 40))
        self.assertEqual(self.status()[0], "TAMPERED")

    def test_manifest_identity_swap_is_detected(self):
        self.rewrite(None, lambda m: m.update(replay_id="another-replay"))
        self.assertEqual(self.status()[0], "TAMPERED")

    def test_missing_evidence_is_reported(self):
        shutil.rmtree(self.evidence / self.REPLAY)
        self.assertEqual(self.status()[0], "MISSING")

    def test_inventory_stays_blocked_even_with_verified_evidence(self):
        result = inventory(self.declaration, self.evidence)
        self.assertEqual(result["qualification"], "BLOCKED")
        self.assertEqual([r["status"] for r in result["replays"]], ["UNVERIFIED"])
        verified = verifier["verify"](self.evidence, self.declaration, self.fixtures, False)
        self.assertTrue(verified["evidence_verified"])
        self.assertTrue(verified["acceptance"].startswith("NOT GRANTED"))


if __name__ == "__main__":
    unittest.main()
