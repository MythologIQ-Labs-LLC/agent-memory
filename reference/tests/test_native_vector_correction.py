from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.qualified_fixtures import corpus_for, registry_for, rule

from agentmem_ref import policy
from agentmem_ref.adapter import RecallContext
from agentmem_ref.runtime_composition import ConfiguredCompositionRuntime
from agentmem_ref.runtime_config import validate_runtime_configuration
from agentmem_ref.vector_retrieval import (
    SEMANTIC_VECTOR_ROUTE,
    NativeVectorCandidateRetriever,
    VectorRepresentationSpec,
)


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "reference" / "fixtures" / "runtime-configuration" / "reference-composed-runtime.json"
TENANT = "tenant-vector-correction"
PROJECT = "project-alpha"
MEMORY = "memory:vehicle-guidance"
OLD_VALUE = "use the legacy repair procedure"
NEW_VALUE = "use the revised repair procedure"
QUERY = "vehicle repair recommendation"


def _plan():
    return validate_runtime_configuration(json.loads(CONFIG.read_text(encoding="utf-8")))


def _correction_corpus():
    return corpus_for(
        rule(
            rule_id="rule:vehicle-guidance-correction",
            target=MEMORY,
            criterion="value-correction",
            from_state=OLD_VALUE,
            to_values=(NEW_VALUE,),
        )
    )


def _proposal(
    proposal_id: str,
    *,
    operation: str,
    state_snapshot: str = "",
) -> policy.Proposal:
    return policy.Proposal(
        proposal_id=proposal_id,
        actor_id="agent:vector-correction-test",
        charter_version="charter-v1",
        target_reference=MEMORY,
        target_class=policy.M2,
        scope=TENANT,
        operation=operation,
        current_strength="observed",
        proposed_strength="promoted",
        downstream_authority=policy.A1,
        reversibility="reversible",
        risk_class="low",
        evidence_refs=(f"evidence:{proposal_id}",),
        tenant_ref=TENANT,
        isolation_domain_refs=(TENANT, PROJECT),
        required_isolation_domain_refs=(PROJECT,),
        project_ref=PROJECT,
        purpose="native-vector-correction-test",
        state_snapshot=state_snapshot,
    )


def _context() -> RecallContext:
    return RecallContext(
        target_domain_refs=(TENANT, PROJECT),
        principal_ref="agent:vector-correction-test",
        project_ref=PROJECT,
        purpose="native-vector-correction-test",
    )


class _CorrectionRepresentation:
    spec = VectorRepresentationSpec(
        representation_ref="agent-memory:test-vector-correction",
        representation_version="1.0.0",
        config_digest="sha256:test-vector-correction-v1",
        dimensions=2,
        deterministic_rebuild=True,
    )

    _vectors = {
        QUERY: (1.0, 0.0),
        OLD_VALUE: (1.0, 0.0),
        NEW_VALUE: (0.8, 0.2),
    }

    def embed(self, text: str) -> tuple[float, ...]:
        return self._vectors.get(text, (0.0, 0.0))


class NativeVectorCorrectionTests(unittest.TestCase):
    def test_correction_rebuilds_current_vector_view_without_stale_influence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            corpus = _correction_corpus()
            retriever = NativeVectorCandidateRetriever(_CorrectionRepresentation())
            runtime = ConfiguredCompositionRuntime.create(
                Path(temp),
                tenant=TENANT,
                plan=_plan(),
                verifier_registry=registry_for(corpus),
                vector_retriever=retriever,
            )

            original = runtime.retain(
                _proposal("proposal:old", operation="promotion"),
                OLD_VALUE,
            )
            self.assertTrue(original.committed)
            self.assertIsNotNone(original.fact_uuid)

            correction = _proposal(
                "proposal:new",
                operation="correction",
                state_snapshot="v1",
            )
            corrected = runtime.correct(
                correction,
                NEW_VALUE,
                evidence=corpus.evidence_for(
                    target_reference=MEMORY,
                    criterion="value-correction",
                    pre_state=OLD_VALUE,
                    proposed_value=NEW_VALUE,
                ),
            )
            self.assertTrue(corrected.committed, f"refused: {corrected.refusal}")
            self.assertIsNotNone(corrected.fact_uuid)
            self.assertNotEqual(corrected.fact_uuid, original.fact_uuid)
            self.assertEqual(runtime.adapter.current_fact_uuid(MEMORY), corrected.fact_uuid)

            result = runtime.multi_route_recall(QUERY, _context())

            # Both canonical facts remain reconstructable and therefore may be
            # discovered by the derived vector scan. Only current governed state
            # may influence recall.
            self.assertIn(original.fact_uuid, result.candidates)
            self.assertIn(corrected.fact_uuid, result.candidates)
            self.assertEqual(result.refusals[original.fact_uuid], "superseded_not_current")
            self.assertNotIn(original.fact_uuid, result.admitted)
            self.assertNotIn(original.fact_uuid, result.ranked_admitted)
            self.assertIn(corrected.fact_uuid, result.admitted)
            self.assertIn(corrected.fact_uuid, result.ranked_admitted)

            old_vector_hits = [
                hit
                for hit in result.provenance_for(original.fact_uuid)
                if hit.route_id == SEMANTIC_VECTOR_ROUTE
            ]
            new_vector_hits = [
                hit
                for hit in result.provenance_for(corrected.fact_uuid)
                if hit.route_id == SEMANTIC_VECTOR_ROUTE
            ]
            self.assertEqual(len(old_vector_hits), 1)
            self.assertEqual(len(new_vector_hits), 1)
            self.assertGreater(old_vector_hits[0].raw_score, new_vector_hits[0].raw_score)
            self.assertEqual(old_vector_hits[0].authority_effect, "none")
            self.assertEqual(new_vector_hits[0].authority_effect, "none")


if __name__ == "__main__":
    unittest.main()
