"""#786 security replay family: fixture integrity, execution, verifier tamper detection, negative controls.

The three replays execute through the real runner against a scratch evidence directory; the
verifier must report VERIFIED on untouched evidence and TAMPERED on a mutated report, and a
mutated fixture expectation must turn its case red (the family is falsifiable, not vacuous).
"""
from __future__ import annotations

import copy
import json
import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference"))
import run_786_security_replays as runner  # noqa: E402
from tests._tenant_wide_fixture import frozen_runner_store  # noqa: E402

# v7 integration: the frozen runner opens several projects in one root, which the default
# single_project_v1 store profile refuses; only its store opener is routed to the tenant-wide
# fixture (reference/tests/_tenant_wide_fixture.py), the runner and fixtures stay frozen.
setUpModule, tearDownModule = frozen_runner_store(runner)

verifier = runpy.run_path(str(ROOT / "scripts/verify_786_security_replays.py"))
DECLARATION = ROOT / "reports/runtime/proposals/786-cumulative-v6-to-v8.PROPOSED.json"


def _v2_declaration(folder: Path) -> Path:
    """The declaration now names the -v3 generation; the frozen -v2 family verifies through a
    scratch declaration that lists its own ids, exactly as it did when it was declared."""
    record = json.loads(DECLARATION.read_text(encoding="utf-8"))
    record["acceptance_evidence_required"] = [
        e for e in record["acceptance_evidence_required"] if e["kind"] != "security_replay"
    ] + [{"kind": "security_replay", "ref": r} for r in runner.REPLAYS]
    path = folder / "declaration-v2.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def fixture(replay_id: str) -> dict:
    return json.loads((runner.FIXTURE_DIR / f"{replay_id}.json").read_text(encoding="utf-8"))


class FixtureIntegrity(unittest.TestCase):
    def test_every_replay_has_a_frozen_fixture_whose_cases_cover_its_invariants(self):
        for replay_id in runner.REPLAYS:
            fx = fixture(replay_id)
            self.assertEqual(fx["replay_id"], replay_id)
            self.assertEqual(fx["dsl_version"], runner.DSL_VERSION)
            ids = [c["id"] for c in fx["cases"]]
            self.assertEqual(len(ids), len(set(ids)), replay_id)
            self.assertEqual({i["id"] for i in fx["invariants"]}, {i for c in fx["cases"] for i in c["invariants"]}, replay_id)
            self.assertTrue(fx["contract_sources"], replay_id)
            self.assertIn("development_history", fx)

    def test_contract_sources_hash_at_the_recorded_base_commit(self):
        for replay_id in runner.REPLAYS:
            fx = fixture(replay_id)
            present = subprocess.run(["git", "cat-file", "-e", f"{fx['base_commit']}^{{commit}}"], cwd=ROOT,
                                     capture_output=True).returncode == 0
            if not present:
                # a shallow checkout (e.g. the hosted validate workflow) does not carry the base
                # commit; the check needs the full clone and is reported as skipped, not passed
                self.skipTest(f"base commit {fx['base_commit'][:8]} is not in this checkout (shallow clone)")
            for source in fx["contract_sources"]:
                blob = subprocess.run(["git", "show", f"{fx['base_commit']}:{source['path']}"], cwd=ROOT,
                                      capture_output=True, check=True).stdout
                self.assertEqual(runner.sha256_bytes(blob), source["sha256_at_base"], source["path"])

    def test_no_frozen_holdout_or_v7_fixture_vocabulary(self):
        text = " ".join((runner.FIXTURE_DIR / f"{r}.json").read_text(encoding="utf-8") for r in runner.REPLAYS)
        for word in ("Orrin", "Halyard", "Vireo", "theatre", "vineyard", "Oslo", "Bergen", "Turku"):
            self.assertNotIn(word, text, word)


class Execution(unittest.TestCase):
    def test_every_case_of_every_replay_passes(self):
        for replay_id in runner.REPLAYS:
            report = runner.run_replay(replay_id, allow_dirty=True)
            failed = [(c["id"], c["error"], [k for k in c["checks"] if not k["holds"]]) for c in report["cases"] if c["outcome"] != "pass"]
            self.assertEqual(failed, [], replay_id)
            self.assertEqual(report["summary"]["cases"], len(fixture(replay_id)["cases"]))

    def test_a_weakened_runtime_would_be_caught_by_the_cross_scope_fixture(self):
        """Negative control: flip one expectation and the runner must report that case red."""
        fx = copy.deepcopy(fixture("cross-scope-write-authority-denial-v1"))
        case = next(c for c in fx["cases"] if c["id"] == "W1-remember-over-live-head")
        case["expect"]["b1_committed"] = {"eq": True}
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "cross-scope-write-authority-denial-v1.json").write_text(json.dumps(fx), encoding="utf-8")
            report = runner.run_replay("cross-scope-write-authority-denial-v1", fixture_dir=Path(tmp), allow_dirty=True)
        outcomes = {c["id"]: c["outcome"] for c in report["cases"]}
        self.assertEqual(outcomes["W1-remember-over-live-head"], "fail")
        self.assertEqual(report["verdict"], "FAIL")


class Verification(unittest.TestCase):
    def test_untampered_evidence_verifies_and_a_mutated_report_is_tampered(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "evidence"
            for replay_id in runner.REPLAYS:
                report = runner.run_replay(replay_id, allow_dirty=True)
                runner.write_outputs(report, evidence, "test")
            result = verifier["verify"](evidence, _v2_declaration(Path(tmp)))
            self.assertEqual({r["replay"] for r in result["replays"]}, set(runner.REPLAYS))
            for row in result["replays"]:
                self.assertIn(row["status"], ("VERIFIED", "STALE"), row)  # STALE only on a dirty runtime tree
                self.assertNotEqual(row["status"], "TAMPERED", row)
            target = evidence / runner.REPLAYS[0] / "report.json"
            doc = json.loads(target.read_text(encoding="utf-8"))
            doc["cases"][0]["checks"][0]["observed"] = "forged"
            target.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
            again = verifier["verify"](evidence, _v2_declaration(Path(tmp)))
            self.assertEqual(next(r for r in again["replays"] if r["replay"] == runner.REPLAYS[0])["status"], "TAMPERED")
            self.assertFalse(again["evidence_verified"])
            self.assertIn("NOT GRANTED", again["acceptance"])


if __name__ == "__main__":
    unittest.main()
