"""#644 live governed correction witness tests; explicit reviewer action only.

No network, inference provider, benchmark gold, implicit authorization or
automatic stop. This suite must be executed against a complete local checkout
before a runtime baseline successor is considered for acceptance.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.memory import procedural_memory as pm  # noqa: E402
from agentmem_ref.adapter import RecallContext  # noqa: E402

TENANT = "tenant:witness"
SCOPE = "project:witness"
ACTOR = "agent:witness"


def _proposition(value: str, *, assertion: str) -> dict:
    return {
        "subject": "Beacon API",
        "attribute": "region",
        "value": value,
        "assertion": assertion,
        "cardinality": "single",
        **({"replaces_value": "east"} if assertion == "change" else {}),
    }


def _review_evidence():
    skill = pm.SkillArtifact(
        skill_id="skill:governed-transition-review", version=1,
        purpose="verify scoped governed correction", scope=SCOPE,
        isolation_domain_refs=(TENANT, SCOPE),
        required_isolation_domain_refs=(TENANT, SCOPE),
        procedure_markdown="# Check\nConfirm replacement evidence with the source.",
        provenance_refs=("evidence:transition-review",),
    )
    return pm.evidence_for(skill)


class AppliedTransitionIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.memory = AgentMemory.open(
            self.temp.name, tenant=TENANT, scope=SCOPE, actor_id=ACTOR,
            purpose="governed transition witness tests",
        )
        first = self.memory.remember(
            "memory:prior", "Beacon API region is east",
            proposition=_proposition("east", assertion="state"),
        )
        later = self.memory.remember(
            "memory:source", "Beacon API region changed to west",
            proposition=_proposition("west", assertion="change"),
        )
        self.assertTrue(first["committed"], first)
        self.assertTrue(later["committed"], later)
        self.old = first["fact_uuid"]
        self.source = later["fact_uuid"]
        candidates = self.memory.semantic_proposals(status="open")
        self.assertEqual(len(candidates), 1, candidates)
        self.proposal_id = candidates[0]["proposal_id"]

    def tearDown(self) -> None:
        self.memory.close()
        self.temp.cleanup()

    def _context(self, scope: str = SCOPE) -> RecallContext:
        return RecallContext(
            target_domain_refs=(TENANT, scope), principal_ref=ACTOR,
            project_ref=scope, purpose="governed transition witness tests",
        )

    def _witnesses(self, refs: tuple[str, ...], *, scope: str = SCOPE):
        return self.memory.runtime.adapter.governed_applied_transition_witnesses(
            refs, self._context(scope)
        )

    def test_change_assertion_does_not_create_applied_witness(self):
        self.assertEqual(self._witnesses((self.old, self.source)), ())
        self.assertEqual(self.memory.semantic_proposals(status="applied"), [])

    def test_explicit_governed_apply_produces_bounded_witness(self):
        committed = self.memory.apply_semantic_proposal(
            self.proposal_id, evidence=_review_evidence(), risk_class="low",
        )
        self.assertTrue(committed["committed"], committed)
        current = committed["fact_uuid"]
        witnesses = self._witnesses((self.source, current))
        self.assertEqual(len(witnesses), 1)
        witness = witnesses[0]
        self.assertEqual(witness.source_fact_ref, self.source)
        self.assertEqual(witness.prior_fact_ref, self.old)
        self.assertEqual(witness.current_target_fact_ref, current)
        self.assertEqual(witness.proposal_ref, self.proposal_id)
        self.assertEqual(witness.status, "applied_state_change_observed")
        self.assertFalse(witness.immediate_successor_verified)
        self.assertFalse(witness.can_stop)
        self.assertEqual(self._witnesses((self.source,)), ())
        self.assertEqual(self._witnesses((current,)), ())
        self.assertEqual(self._witnesses((self.source, current), scope="project:other"), ())

    def test_uncited_correction_cannot_retroactively_apply_a_proposal(self):
        correction = self.memory.correct(
            "memory:prior", "Beacon API region is west",
            evidence=_review_evidence(), risk_class="low",
            replacement_kind="state_change",
        )
        self.assertTrue(correction["committed"], correction)
        self.assertEqual(self._witnesses((self.source, correction["fact_uuid"])), ())

    def test_error_correction_is_not_state_change_witness(self):
        correction = self.memory.correct(
            "memory:prior", "Beacon API region is west",
            evidence=_review_evidence(), risk_class="low",
            evidence_refs=(self.proposal_id,),
            replacement_kind="error_correction",
        )
        self.assertTrue(correction["committed"], correction)
        witnesses = self._witnesses((self.source, correction["fact_uuid"]))
        self.assertEqual(len(witnesses), 1)
        self.assertEqual(witnesses[0].status, "applied_error_correction_observed")
        self.assertFalse(witnesses[0].answer_quality_verified)

    def test_duplicate_admitted_refs_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate admitted"):
            self._witnesses((self.source, self.source))


if __name__ == "__main__":
    unittest.main()
