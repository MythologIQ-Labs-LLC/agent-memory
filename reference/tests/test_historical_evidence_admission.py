"""#549: explicit historical-evidence admission, separate from current-state admission.

    superseded by a governed STATE CHANGE + explicit historical/as-of recall inside
        its validity                          -> admit_with_warning, labelled non-current
    superseded + current (or inferred) query  -> refused superseded_not_current
    ERROR CORRECTION (prior value was wrong)  -> refused corrected_as_false, never "true then"
    disputed                                  -> refused disputed
    tombstoned                                -> refused tombstoned (deletion stays controlling)
    wrong scope                               -> never a candidate (#548 prefilter + admission)

A historical query must not become a route for leaking current-forbidden,
corrected-as-false, tombstoned, disputed, or wrong-scope state.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref import AgentMemory, policy  # noqa: E402
from agentmem_ref.memory import procedural_memory as pm  # noqa: E402

TENANT = "tenant:history"
SCOPE = "project:history"
NOW = "2026-09-26T12:00:00Z"
HISTORICAL = {"mode": "historical"}


def _open(root: str, scope: str = SCOPE) -> AgentMemory:
    return AgentMemory.open(root, tenant=TENANT, actor_id="agent:history", scope=scope, purpose="history tests")


def _evidence(scope: str = SCOPE):
    skill = pm.SkillArtifact(
        skill_id="skill:history-correction",
        version=1,
        purpose="correct retained test memory",
        scope=scope,
        isolation_domain_refs=(TENANT, scope),
        required_isolation_domain_refs=(TENANT, scope),
        procedure_markdown="# verify\nConfirm the correction against the current source.",
        provenance_refs=("evidence:history-correction-source",),
    )
    return pm.evidence_for(skill)


class HistoricalEvidenceAdmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.memory = _open(self._temp.name)
        self.old = self.memory.remember("memory:city", "Kevin lives in Denver.", valid_from="2020-01-01")["fact_uuid"]
        moved = self.memory.correct(
            "memory:city", "Kevin lives in Boston.", evidence=_evidence(), risk_class="low",
            replacement_kind="state_change", valid_from="2024-06-01",
        )
        self.assertTrue(moved["committed"], moved)
        self.new = moved["fact_uuid"]

    def tearDown(self) -> None:
        self.memory.close()
        self._temp.cleanup()

    def _admission(self, recalled: dict, ref: str) -> dict:
        return recalled["admissions"][ref]

    def test_current_query_keeps_superseded_state_non_current(self):
        recalled = self.memory.recall("Where does Kevin currently live?", reference_time=NOW)
        self.assertEqual(recalled["admitted"], [self.new])
        self.assertEqual(self._admission(recalled, self.old)["refusal"], "superseded_not_current")
        self.assertEqual(self._admission(recalled, self.new)["admission_basis"]["admission_mode"], "current_state")

    def test_inferred_historical_intent_never_widens_admission(self):
        recalled = self.memory.recall("Where did Kevin live previously?", reference_time=NOW)
        self.assertNotIn(self.old, recalled["admitted"])
        self.assertEqual(self._admission(recalled, self.old)["refusal"], "superseded_not_current")

    def test_explicit_historical_admits_state_change_as_labelled_non_current_evidence(self):
        recalled = self.memory.recall("Where does Kevin live?", temporal_intent=HISTORICAL, reference_time=NOW)
        self.assertIn(self.old, recalled["admitted"])
        decision = self._admission(recalled, self.old)
        self.assertEqual(decision["outcome"], "admit_with_warning")
        self.assertEqual(decision["reason_code"], "historical_evidence_not_current")
        basis = decision["admission_basis"]
        self.assertEqual(basis["admission_mode"], "historical_evidence")
        self.assertEqual(basis["currentness"], "historical_evidence_not_current")
        self.assertEqual(basis["replacement_kind"], "state_change")
        self.assertEqual((basis["valid_from"], basis["valid_until"]), ("2020-01-01", "2024-06-01"))
        self.assertEqual(basis["authority_effect"], "none")
        # The current state is still current, and marked as such.
        self.assertEqual(self._admission(recalled, self.new)["admission_basis"]["currentness"], "current_state")
        # Historical admission mutates nothing.
        self.assertEqual(self.memory.history("memory:city")["history"]["current_fact_uuid"], self.new)

    def test_explicit_as_of_respects_the_validity_interval(self):
        inside = self.memory.recall(
            "Where does Kevin live?",
            temporal_intent={"mode": "as_of", "target_start": "2022-01-01", "target_end": "2022-01-02"},
        )
        self.assertIn(self.old, inside["admitted"])
        after = self.memory.recall(
            "Where does Kevin live?",
            temporal_intent={"mode": "as_of", "target_start": "2025-01-01", "target_end": "2025-01-02"},
        )
        self.assertNotIn(self.old, after["admitted"])
        self.assertEqual(self._admission(after, self.old)["refusal"], "outside_historical_validity")

    def test_error_correction_is_never_presented_as_historically_true(self):
        wrong = self.memory.remember("memory:budget", "The project budget is 100 dollars.")["fact_uuid"]
        fixed = self.memory.correct("memory:budget", "The project budget is 200 dollars.", evidence=_evidence(), risk_class="low")
        self.assertTrue(fixed["committed"])
        recalled = self.memory.recall("project budget", temporal_intent=HISTORICAL, reference_time=NOW)
        self.assertNotIn(wrong, recalled["admitted"])
        self.assertEqual(self._admission(recalled, wrong)["refusal"], "corrected_as_false")

    def test_disputed_superseded_state_stays_refused(self):
        self.memory.runtime.adapter.mark_disputed(self.old)
        recalled = self.memory.recall("Where does Kevin live?", temporal_intent=HISTORICAL, reference_time=NOW)
        self.assertNotIn(self.old, recalled["admitted"])
        self.assertEqual(self._admission(recalled, self.old)["refusal"], "disputed")

    def test_tombstoned_superseded_state_stays_refused(self):
        adapter = self.memory.runtime.adapter
        adapter._tombstones[self.old] = {"memory_id": "memory:city", "deleted_at": NOW}
        recalled = self.memory.recall("Where does Kevin live?", temporal_intent=HISTORICAL, reference_time=NOW)
        self.assertNotIn(self.old, recalled["admitted"])
        self.assertEqual(self._admission(recalled, self.old)["refusal"], "tombstoned")

    def test_wrong_scope_historical_state_is_never_a_candidate(self):
        self.memory.close()
        with _open(self._temp.name, scope="project:elsewhere") as other:
            foreign_old = other.remember("memory:hq", "Kevin lives in Oslo headquarters.", valid_from="2019-01-01")["fact_uuid"]
            other.correct(
                "memory:hq", "Kevin lives in Bergen headquarters.", evidence=_evidence("project:elsewhere"),
                risk_class="low", replacement_kind="state_change", valid_from="2023-01-01",
            )
        self.memory = _open(self._temp.name)
        recalled = self.memory.recall("Where does Kevin live?", temporal_intent=HISTORICAL, reference_time=NOW)
        self.assertNotIn(foreign_old, recalled["candidates"])
        self.assertNotIn(foreign_old, recalled["admitted"])

    def test_replacement_kind_survives_restart(self):
        self.memory.close()
        self.memory = _open(self._temp.name)
        recalled = self.memory.recall("Where does Kevin live?", temporal_intent=HISTORICAL, reference_time=NOW)
        self.assertIn(self.old, recalled["admitted"])
        self.assertEqual(self._admission(recalled, self.old)["admission_basis"]["replacement_kind"], "state_change")

    def test_unknown_replacement_kind_is_rejected_before_any_commit(self):
        with self.assertRaises(ValueError):
            self.memory.correct("memory:city", "Kevin lives in Paris.", evidence=_evidence(), replacement_kind="rewrite_history")
        self.assertEqual(self.memory.history("memory:city")["history"]["current_fact_uuid"], self.new)


if __name__ == "__main__":
    unittest.main()
