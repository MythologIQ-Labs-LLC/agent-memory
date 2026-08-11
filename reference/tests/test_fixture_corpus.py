"""The doctrine fixture corpus, driven through the adapter's enforcement code.

Two kinds of test live here, and the second is what makes the first mean
anything:

1. every fixture's declared authority envelope is enforced by the adapter's
   own membership rule; and
2. the checker itself is mutation-tested, so a corpus that passes is evidence
   rather than a check that cannot fail.

Run: python -m unittest discover -s reference/tests -t reference
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentmem_ref import fixture_conformance as fc  # noqa: E402

REPO_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


class FixtureCorpusTests(unittest.TestCase):
    def test_corpus_is_present_and_versioned(self):
        fixtures = fc.load_fixtures()
        self.assertGreaterEqual(len(fixtures), 25)
        for name, fixture in fixtures:
            self.assertIn("fixture_version", fixture, f"{name} lacks fixture_version")

    def test_every_declared_envelope_is_enforced(self):
        result = fc.run()
        self.assertEqual(
            result["fixtures_failed"],
            [],
            msg=f"envelope enforcement failures: {json.dumps(result['failures'], indent=2)}",
        )
        self.assertEqual(len(result["fixtures_run"]), len(list(REPO_FIXTURES.glob("*.json"))))
        self.assertGreater(result["fixtures_with_authority_envelope"], 0)


class CheckerHasTeethTests(unittest.TestCase):
    """A conformance check that cannot fail is decoration."""

    def setUp(self) -> None:
        source = REPO_FIXTURES / "high-confidence-false-promotion.json"
        self.base = json.loads(source.read_text(encoding="utf-8"))

    def _run_mutant(self, mutate) -> dict:
        fixture = json.loads(json.dumps(self.base))
        mutate(fixture)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mutant.json"
            path.write_text(json.dumps(fixture), encoding="utf-8")
            return fc.run(Path(tmp))

    def test_detects_permitted_and_prohibited_overlap(self):
        result = self._run_mutant(
            lambda f: f["governed_uncertainty"].update(
                {"permitted_actions": ["crystallize", "mark_disputed"]}
            )
        )
        self.assertEqual(result["fixtures_failed"], ["mutant"])

    def test_detects_selection_of_prohibited_action(self):
        result = self._run_mutant(
            lambda f: f["governed_uncertainty"].update({"selected_action": "crystallize"})
        )
        self.assertEqual(result["fixtures_failed"], ["mutant"])

    def test_detects_selection_outside_permitted_set(self):
        result = self._run_mutant(
            lambda f: f["governed_uncertainty"].update({"selected_action": "invented_action"})
        )
        self.assertEqual(result["fixtures_failed"], ["mutant"])

    def test_detects_crystallization_against_stated_expectation(self):
        result = self._run_mutant(
            lambda f: f["governed_uncertainty"]["permitted_actions"].append("crystallize_anyway")
        )
        self.assertEqual(result["fixtures_failed"], ["mutant"])


if __name__ == "__main__":
    unittest.main()
