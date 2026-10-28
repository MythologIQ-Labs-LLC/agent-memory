"""v7 integration: the frozen #644 admission fixture on a scope_distinct_v1 store, and verifier runner selection.

``run_644_v7_replays_sd.py`` executes the frozen
``governed-persisted-typed-slot-sufficiency-admission-recheck-v1`` fixture, whose A4/A6/A9 cases write
a second project, on the supported multi-project profile. ``verify_644_v7_replays.runner_for`` picks
the runner a family's evidence recorded from a fixed allowlist; the chosen runner's bytes must
still match the recorded hash.
"""
from __future__ import annotations

import json
import runpy
import tempfile
import unittest
from pathlib import Path

import run_644_v7_replays as frozen  # noqa: E402  (reference/ is the test top-level directory)
import run_644_v7_replays_sd as sd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
verifier = runpy.run_path(str(ROOT / "scripts/verify_644_v7_replays.py"))
FAMILY = "governed-persisted-typed-slot-sufficiency-admission-recheck-v1"


def _case(case_id):
    fixture = json.loads((frozen.FIXTURE_DIR / f"{FAMILY}.json").read_text(encoding="utf-8"))
    return next(c for c in fixture["cases"] if c["id"] == case_id)


class ScopeDistinctAdmissionRunnerTests(unittest.TestCase):
    def test_the_cross_project_admission_case_passes_on_a_scope_distinct_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = sd.run_case(_case("A6-hidden-admissible-competitor-counted"), Path(tmp))
        self.assertEqual(result["outcome"], "pass", result)

    def test_the_frozen_runner_is_unchanged_and_still_stopped_by_the_default_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertNotEqual(frozen.run_case(_case("A6-hidden-admissible-competitor-counted"), Path(tmp))["outcome"],
                                "pass")
        self.assertEqual(frozen.Scenario.__module__, "run_644_v7_replays")

    def test_the_runner_refuses_families_it_does_not_execute(self):
        with self.assertRaises(ValueError):
            sd.run_replay("committed-governed-transition-witness-v1", allow_dirty=True)


class VerifierRunnerSelectionTests(unittest.TestCase):
    def manifest(self, root: Path, family: str, runner_path: str) -> Path:
        (root / family).mkdir(parents=True)
        (root / family / "manifest.json").write_text(json.dumps({"runner": {"path": runner_path}}), encoding="utf-8")
        return root

    def test_scope_distinct_evidence_selects_the_scope_distinct_runner(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.manifest(Path(tmp), FAMILY, "reference/run_644_v7_replays_sd.py")
            self.assertEqual(verifier["runner_for"](FAMILY, root).__name__, "run_644_v7_replays_sd")

    def test_frozen_evidence_and_unlisted_families_keep_the_frozen_runner(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.manifest(Path(tmp), FAMILY, "reference/run_644_v7_replays.py")
            self.assertEqual(verifier["runner_for"](FAMILY, root).__name__, "run_644_v7_replays")
            other = "committed-governed-transition-witness-v1"
            self.manifest(Path(tmp), other, "reference/run_644_v7_replays_sd.py")
            self.assertEqual(verifier["runner_for"](other, root).__name__, "run_644_v7_replays")
            self.assertEqual(verifier["runner_for"]("missing-family", root).__name__, "run_644_v7_replays")

    def test_an_explicit_runner_is_never_redirected(self):
        sentinel = object()
        with tempfile.TemporaryDirectory() as tmp:
            root = self.manifest(Path(tmp), FAMILY, "reference/run_644_v7_replays_sd.py")
            self.assertIs(verifier["runner_for"](FAMILY, root, sentinel), sentinel)


if __name__ == "__main__":
    unittest.main()
