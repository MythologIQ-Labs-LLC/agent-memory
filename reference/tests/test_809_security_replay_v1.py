"""#809 security replay generation ``evidence-reference-authorization-v1`` (DSL/3): integrity, traceability, falsifiability.

The fixture is preregistered (committed before first execution) and traced clause by clause to
its contract sources at the repair commit. These tests pin: fixture identity and DSL version;
every expectation traced to a quoted clause; contract sources hashing at the recorded base
commit and carrying the #809 clause; the three -v3 fixtures and the DSL/1 and DSL/2 runners
byte-untouched; every case passing through the DSL/3 runner; a flipped expectation turning a
case red; and committed evidence verifying and reading TAMPERED when mutated.
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
import run_786_security_replays_dsl2 as runner_v2  # noqa: E402
import run_786_security_replays_dsl3 as runner  # noqa: E402
from tests._tenant_wide_fixture import frozen_runner_store  # noqa: E402

# v7 integration: the frozen runner opens several projects in one root, which the default
# single_project_v1 store profile refuses; only its store opener is routed to the tenant-wide
# fixture (reference/tests/_tenant_wide_fixture.py), the runner and fixtures stay frozen.
setUpModule, tearDownModule = frozen_runner_store(runner_v1)

DECLARATION = ROOT / "reports/runtime/proposals/786-cumulative-v6-to-v8.PROPOSED.json"
REPLAY = "evidence-reference-authorization-v1"
CLAUSE = "Canonical derivation is bound under the writer's own authority"
FROZEN_V3_SHA256 = {
    # byte-frozen generation; a change here is a finding, never a refresh
    "cross-scope-write-authority-denial-v3.json": "99580f996e602946885f5edde128e7d58fc543cdbaa195f6b01ddbfdd565303b",
    "deleted-lineage-generations-and-restart-v3.json": "412799ee22c77760adb33264dd32ade2ee9764cd069e770a5b4f66fe0a5eba00",
    "public-tombstone-redaction-and-observer-separation-v3.json": "80338243a6f4a995dccd7b90f7e6688728fb6a4bf11753b06d8d522996b3f8e4",
}
FROZEN_RUNNERS_SHA256 = {
    "reference/run_786_security_replays.py": "21db05148c369815fa154bfa83db0b3b35f6c4712596ec0f137002a6611d8269",
    "reference/run_786_security_replays_dsl2.py": "73f0cd175b5a97f8e61d168bfc93cd796152aab02c76209bf2374153f35dba86",
}


def _fixture() -> dict:
    return json.loads((runner.FIXTURE_DIR / f"{REPLAY}.json").read_text(encoding="utf-8"))


def _scratch_declaration(folder: Path) -> Path:
    record = json.loads(DECLARATION.read_text(encoding="utf-8"))
    record["acceptance_evidence_required"] = [
        e for e in record["acceptance_evidence_required"] if e["kind"] != "security_replay"
    ] + [{"kind": "security_replay", "ref": r} for r in runner.REPLAYS]
    path = folder / "declaration-809.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


class Fixture(unittest.TestCase):
    def test_identity_and_invariant_coverage(self):
        fx = _fixture()
        self.assertEqual(runner.REPLAYS, (REPLAY,))
        self.assertEqual(fx["replay_id"], REPLAY)
        self.assertEqual(fx["dsl_version"], runner.DSL_VERSION)
        self.assertEqual(fx["fixture_version"], 1)
        self.assertEqual(fx["status"], "additive")
        self.assertEqual(fx["owning_issue"], 809)
        ids = [c["id"] for c in fx["cases"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual({i for c in fx["cases"] for i in c["invariants"]}, {i["id"] for i in fx["invariants"]})
        self.assertIn(REPLAY, [e["ref"] for e in json.loads(DECLARATION.read_text(encoding="utf-8"))["acceptance_evidence_required"]
                               if e["kind"] == "security_replay"])

    def test_every_expectation_is_traced_to_a_quoted_clause_of_a_listed_source(self):
        fx = _fixture()
        sources = {s["path"] for s in fx["contract_sources"]}
        for case in fx["cases"]:
            with self.subTest(case=case["id"]):
                traced = {o for clause in case["clauses"] for o in clause["observables"]}
                controls = set(case.get("controls", ()))
                self.assertTrue(controls <= set(case["expect"]) and not (controls & traced), case["id"])
                self.assertTrue(set(case["expect"]) <= traced | controls, set(case["expect"]) - traced - controls)
                self.assertTrue({c["source"] for c in case["clauses"]} <= sources)
                for clause in case["clauses"]:
                    self.assertGreater(len(clause["clause"]), 20)
                evidence = set(case.get("implementation_evidence", ()))
                self.assertFalse(evidence & set(case["expect"]))
                self.assertTrue(evidence <= set(case.get("record", ())))

    def test_contract_sources_hash_at_the_recorded_base_commit_and_carry_the_clause(self):
        fx = _fixture()
        base = fx["base_commit"]
        if subprocess.run(["git", "cat-file", "-e", f"{base}^{{commit}}"], cwd=ROOT).returncode != 0:
            self.skipTest(f"base commit {base[:8]} is not in this checkout (shallow clone)")
        for source in fx["contract_sources"]:
            with self.subTest(source=source["path"]):
                blob = subprocess.run(["git", "show", f"{base}:{source['path']}"], cwd=ROOT, capture_output=True, check=True).stdout
                self.assertEqual(runner.sha256_bytes(blob), source["sha256_at_base"])
        texts = {source["path"]: subprocess.run(["git", "show", f"{base}:{source['path']}"], cwd=ROOT,
                                                capture_output=True, check=True).stdout.decode()
                 for source in fx["contract_sources"]}
        self.assertIn(CLAUSE, texts["docs/44-public-api-contract.md"])
        # every quoted clause of every case is present verbatim and in full in its own hashed source
        for case in fx["cases"]:
            for clause in case["clauses"]:
                with self.subTest(case=case["id"], clause=clause["clause"][:40]):
                    self.assertIn(clause["clause"], texts[clause["source"]])

    def test_frozen_v3_fixtures_and_base_runners_are_byte_untouched(self):
        for name, digest in FROZEN_V3_SHA256.items():
            with self.subTest(fixture=name):
                self.assertEqual(runner.sha256_file(runner.FIXTURE_DIR / name), digest)
        for path, digest in FROZEN_RUNNERS_SHA256.items():
            with self.subTest(runner=path):
                self.assertEqual(runner.sha256_file(ROOT / path), digest)
        self.assertIs(runner.base, runner_v2)
        self.assertIs(runner_v2.base, runner_v1)

    def test_no_frozen_holdout_or_other_fixture_vocabulary(self):
        text = (runner.FIXTURE_DIR / f"{REPLAY}.json").read_text(encoding="utf-8").lower()
        for token in ("theatre", "vineyard", "halcyon", "cedarline", "brightwater", "fenmoor", "orrin", "marrow", "oslo", "bergen", "turku"):
            self.assertNotIn(token, text)


FIRST_EXECUTION = ROOT / "reports/validation/809-security-replays" / REPLAY / "report.json"


@unittest.skipUnless(FIRST_EXECUTION.is_file(),
                     "the first execution of this fixture is the runner's own on a clean tree, committed under "
                     "reports/validation/809-security-replays; until then the test suite does not execute it")
class Execution(unittest.TestCase):
    def test_every_case_passes(self):
        report = runner.run_replay(REPLAY, allow_dirty=True)
        failed = [(c["id"], c["error"], [k for k in c["checks"] if not k["holds"]]) for c in report["cases"] if c["outcome"] != "pass"]
        self.assertEqual(failed, [])
        self.assertEqual(report["summary"]["errors"], 0)
        self.assertEqual(report["summary"]["cases"], len(_fixture()["cases"]))
        self.assertEqual(report["provenance"]["runner"]["version"], runner.RUNNER_VERSION)
        self.assertEqual(report["provenance"]["runner_base"]["version"], runner_v2.RUNNER_VERSION)
        self.assertEqual(report["provenance"]["runner_root"]["version"], runner_v1.RUNNER_VERSION)

    def test_a_reopened_oracle_would_be_caught(self):
        """Negative control: flip the deleted-foreign admission of E1 and the case must go red."""
        fx = _fixture()
        case = next(c for c in fx["cases"] if c["id"] == "E1-four-references-after-pruning")
        case["expect"]["admitted_bd"] = {"eq": False}  # the boolean recall_admits probe (reviewer note, section 8)
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / f"{REPLAY}.json").write_text(json.dumps(fx), encoding="utf-8")
            report = runner.run_replay(REPLAY, fixture_dir=Path(tmp), allow_dirty=True)
        self.assertEqual(report["verdict"], "FAIL")
        self.assertEqual([c["id"] for c in report["cases"] if c["outcome"] == "fail"], ["E1-four-references-after-pruning"])

    def test_untampered_evidence_verifies_and_a_mutated_report_is_tampered(self):
        verifier = runpy.run_path(str(ROOT / "scripts/verify_786_security_replays.py"))
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "evidence"
            runner.write_outputs(runner.run_replay(REPLAY, allow_dirty=True), evidence, "test")
            declaration = _scratch_declaration(Path(tmp))
            result = verifier["verify"](evidence, declaration)
            self.assertEqual([r["replay"] for r in result["replays"]], [REPLAY])
            for row in result["replays"]:
                self.assertIn(row["status"], ("VERIFIED", "STALE"), row)  # STALE only on a dirty runtime tree
            target = evidence / REPLAY / "report.json"
            report = json.loads(target.read_text(encoding="utf-8"))
            report["cases"][0]["checks"][0]["observed"] = "forged"
            target.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
            again = verifier["verify"](evidence, declaration)
            self.assertEqual(again["replays"][0]["status"], "TAMPERED")
            self.assertFalse(again["evidence_verified"])


if __name__ == "__main__":
    unittest.main()
