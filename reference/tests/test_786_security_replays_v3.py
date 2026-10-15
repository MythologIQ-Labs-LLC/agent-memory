"""#786 security replay family, generation -v3 (DSL/2): integrity, traceability and falsifiability.

The -v3 fixtures are preregistered (committed before first execution) and traced clause by
clause to their contract sources. These tests pin: fixture identity and DSL version; every
expectation traced to a quoted clause; contract sources hashing at the recorded base commit;
frozen -v1/-v2 fixtures untouched; every -v3 case passing through the DSL/2 runner; a flipped
expectation turning a case red; and committed evidence verifying and reading TAMPERED when
mutated. The frozen DSL/1 runner is not changed by the -v3 generation.
"""

from __future__ import annotations

import json
import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "reference"))

import run_786_security_replays as runner_v1  # noqa: E402
import run_786_security_replays_dsl2 as runner  # noqa: E402

DECLARATION = ROOT / "reports/runtime/proposals/786-cumulative-v6-to-v8.PROPOSED.json"
FROZEN_V1_V2_SHA256 = {
    # byte-frozen generations; a change here is a finding, never a refresh
    "cross-scope-write-authority-denial-v2.json": "9088c6f7704d221384431ce7ce8cf419691275b66ad05754822398f9528a7fed",
    "deleted-lineage-generations-and-restart-v2.json": "bda4c611de84a01754711faa7577dba8cdb591ee79c6f2d51c50f905d69c9d8f",
    "public-tombstone-redaction-and-observer-separation-v2.json": "5817a0ff7d39be2f29b97c7a918c05da8dba6ab13bca0acb955123eb65a1267e",
}


def _fixture(replay_id: str) -> dict:
    return json.loads((runner.FIXTURE_DIR / f"{replay_id}.json").read_text(encoding="utf-8"))


class SecurityReplayV3Fixtures(unittest.TestCase):
    def test_every_replay_has_a_preregistered_fixture_covering_its_invariants(self):
        for replay_id in runner.REPLAYS:
            with self.subTest(replay=replay_id):
                fx = _fixture(replay_id)
                self.assertEqual(fx["replay_id"], replay_id)
                self.assertEqual(fx["dsl_version"], runner.DSL_VERSION)
                self.assertEqual(fx["fixture_version"], 3)
                self.assertEqual(fx["status"], "supersedes_v2")
                covered = {i for c in fx["cases"] for i in c["invariants"]}
                self.assertEqual(covered, {i["id"] for i in fx["invariants"]})

    def test_every_expectation_is_traced_to_a_quoted_clause_of_a_listed_source(self):
        for replay_id in runner.REPLAYS:
            fx = _fixture(replay_id)
            sources = {s["path"] for s in fx["contract_sources"]}
            for case in fx["cases"]:
                with self.subTest(replay=replay_id, case=case["id"]):
                    traced = {o for clause in case["clauses"] for o in clause["observables"]}
                    self.assertTrue(set(case["expect"]) <= traced, set(case["expect"]) - traced)
                    self.assertTrue({c["source"] for c in case["clauses"]} <= sources)
                    for clause in case["clauses"]:
                        self.assertGreater(len(clause["clause"]), 20)
                    evidence = set(case.get("implementation_evidence", ()))
                    self.assertFalse(evidence & set(case["expect"]))
                    self.assertTrue(evidence <= set(case.get("record", ())))

    def test_contract_sources_hash_at_the_recorded_base_commit(self):
        for replay_id in runner.REPLAYS:
            fx = _fixture(replay_id)
            base = fx["base_commit"]
            if subprocess.run(["git", "cat-file", "-e", f"{base}^{{commit}}"], cwd=ROOT).returncode != 0:
                self.skipTest(f"base commit {base[:8]} is not in this checkout (shallow clone)")
            for source in fx["contract_sources"]:
                with self.subTest(replay=replay_id, source=source["path"]):
                    blob = subprocess.run(["git", "show", f"{base}:{source['path']}"], cwd=ROOT,
                                          capture_output=True, check=True).stdout
                    self.assertEqual(runner.sha256_bytes(blob), source["sha256_at_base"])
            # the closed-generation clauses the cases expect are present in the hashed sources
            docs44 = subprocess.run(["git", "show", f"{base}:docs/44-public-api-contract.md"], cwd=ROOT,
                                    capture_output=True, check=True).stdout.decode()
            for needle in ("already_deleted", "Scope is privileged host input", "generation-relative"):
                self.assertIn(needle, docs44)

    def test_frozen_v2_fixtures_and_dsl1_runner_are_byte_untouched(self):
        for name, digest in FROZEN_V1_V2_SHA256.items():
            with self.subTest(fixture=name):
                self.assertEqual(runner.sha256_file(runner.FIXTURE_DIR / name), digest)
        self.assertEqual(runner_v1.DSL_VERSION, "786-security-replay-dsl/1")
        self.assertEqual(runner.base, runner_v1)

    def test_no_frozen_holdout_or_v7_fixture_vocabulary(self):
        text = " ".join((runner.FIXTURE_DIR / f"{r}.json").read_text(encoding="utf-8") for r in runner.REPLAYS)
        for token in ("theatre", "vineyard", "Halcyon", "Cedarline", "Brightwater", "Fenmoor"):
            self.assertNotIn(token.lower(), text.lower())


class SecurityReplayV3Execution(unittest.TestCase):
    def test_every_case_of_every_replay_passes(self):
        for replay_id in runner.REPLAYS:
            report = runner.run_replay(replay_id, allow_dirty=True)
            failed = [c["id"] for c in report["cases"] if c["outcome"] != "pass"]
            self.assertEqual(failed, [], [(c["id"], c["error"], [k for k in c["checks"] if not k["holds"]])
                                          for c in report["cases"] if c["outcome"] != "pass"])
            self.assertEqual(report["summary"]["errors"], 0)
            self.assertEqual(report["provenance"]["runner"]["version"], runner.RUNNER_VERSION)
            self.assertEqual(report["provenance"]["runner_base"]["version"], runner_v1.RUNNER_VERSION)

    def test_a_weakened_runtime_would_be_caught(self):
        """Negative control: flip one expectation and the runner must report that case red."""
        fx = _fixture("cross-scope-write-authority-denial-v3")
        case = next(c for c in fx["cases"] if c["id"] == "W1-remember-over-live-head")
        case["expect"]["b1_committed"] = {"eq": True}
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "cross-scope-write-authority-denial-v3.json").write_text(json.dumps(fx), encoding="utf-8")
            report = runner.run_replay("cross-scope-write-authority-denial-v3", fixture_dir=Path(tmp), allow_dirty=True)
        self.assertEqual(report["verdict"], "FAIL")
        self.assertEqual([c["id"] for c in report["cases"] if c["outcome"] == "fail"], ["W1-remember-over-live-head"])

    def test_untampered_evidence_verifies_and_a_mutated_report_is_tampered(self):
        verifier = runpy.run_path(str(ROOT / "scripts/verify_786_security_replays.py"))
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "evidence"
            for replay_id in runner.REPLAYS:
                runner.write_outputs(runner.run_replay(replay_id, allow_dirty=True), evidence, "test")
            result = verifier["verify"](evidence, DECLARATION)
            self.assertEqual({r["replay"] for r in result["replays"]}, set(runner.REPLAYS))
            self.assertTrue(all(r["status"] == "VERIFIED" for r in result["replays"]), result)
            self.assertIn("NOT GRANTED", result["acceptance"])
            target = evidence / runner.REPLAYS[0] / "report.json"
            report = json.loads(target.read_text(encoding="utf-8"))
            report["cases"][0]["outcome"] = "pass"
            report["cases"][0]["checks"][0]["holds"] = True
            report["cases"][0]["checks"][0]["observed"] = "forged"
            target.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
            again = verifier["verify"](evidence, DECLARATION)
            self.assertEqual(next(r for r in again["replays"] if r["replay"] == runner.REPLAYS[0])["status"], "TAMPERED")


if __name__ == "__main__":
    unittest.main()
