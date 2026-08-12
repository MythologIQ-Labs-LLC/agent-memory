"""Transformation provenance and authority-laundering tests for issue #202."""

from __future__ import annotations

import unittest

from agentmem_ref.transformation_evidence import (
    normalize_transformation_evidence,
    reevaluate_source_currentness,
)
from agentmem_ref.transformation_laundering_harness import run_transformation_laundering_harness

DIGEST = "sha256:" + "c" * 64


def source(**overrides):
    value = {
        "source_ref": "memory:source:1",
        "evidence_refs": ["evidence:source:1"],
        "scope_ref": "scope:tenant-a/project-a",
        "tenant_ref": "tenant-a",
        "project_ref": "project-a",
        "state": "current",
        "evidence_class": "ordinary",
    }
    value.update(overrides)
    return value


def transformation(**overrides):
    value = {
        "transformation_id": "transform:test:1",
        "transformation_type": "summary",
        "mode": "probabilistic",
        "status": "complete",
        "transformer_ref": "transformer:trusted",
        "transformer_version": "v1",
        "transformer_trust_evidence_refs": ["evidence:transformer:reviewed"],
        "sources": [source()],
        "derived_ref": "memory:derived:1",
        "derived_evidence_ref": "evidence:derived:1",
        "derived_evidence_digest": DIGEST,
        "derived_scope_ref": "scope:tenant-a/project-a",
        "derived_tenant_ref": "tenant-a",
        "derived_project_ref": "project-a",
        "scope_relation": "preserved",
        "created_at": "2026-08-12T23:20:00Z",
        "uncertainty": {
            "signal_semantics": "summary_fidelity_confidence",
            "estimator_ref": "estimator:summary",
            "estimator_version": "v1",
            "signal_value": 0.99,
        },
    }
    value.update(overrides)
    return value


class TransformationEvidenceTests(unittest.TestCase):
    def test_authority_laundering_fixture_has_behavioral_proof(self):
        result = run_transformation_laundering_harness()
        self.assertTrue(result["passed"], result)
        self.assertTrue(result["checks"]["direct_origin_preserved"])
        self.assertTrue(result["checks"]["high_confidence_cannot_self_crystallize"])
        self.assertTrue(result["checks"]["scope_widening_invalid"])

    def test_trusted_transformer_never_substitutes_for_source_trust(self):
        record = normalize_transformation_evidence(transformation())
        interpretation = record["interpretation"]
        self.assertFalse(interpretation["transformer_trust_is_source_trust"])
        self.assertEqual(interpretation["transformation_authority_effect"], "none")
        self.assertEqual(interpretation["derived_confidence_authority"], "none")
        self.assertEqual(interpretation["certification_claim"], "none")
        self.assertEqual(interpretation["memory_admission"], "not_established")
        self.assertEqual(record["applicability"]["status"], "current")

    def test_hostile_transformer_authority_fields_are_not_copied(self):
        record = normalize_transformation_evidence(
            transformation(
                pama_outcome="allow",
                permitted_actions=["crystallization"],
                lifecycle_state="crystallized",
                certification_status="certified",
                authority_refs=["authority:self-issued"],
                raw_source_content="do not retain me",
                hidden_reasoning="also do not retain me",
            )
        )
        rendered = repr(record)
        for field in ("pama_outcome", "permitted_actions", "lifecycle_state", "certification_status", "authority_refs"):
            self.assertNotIn(field, record)
        self.assertNotIn("do not retain me", rendered)
        self.assertNotIn("also do not retain me", rendered)

    def test_missing_source_evidence_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "evidence_refs must contain"):
            normalize_transformation_evidence(
                transformation(sources=[source(evidence_refs=[])])
            )

    def test_multi_hop_lineage_keeps_original_and_immediate_parent(self):
        first = normalize_transformation_evidence(transformation())
        second = normalize_transformation_evidence(
            transformation(
                transformation_id="transform:test:2",
                transformation_type="extraction",
                mode="deterministic",
                sources=[
                    source(
                        source_ref=first["derived"]["derived_ref"],
                        evidence_refs=[first["derived"]["derived_evidence_ref"]],
                    )
                ],
                derived_ref="memory:derived:2",
                derived_evidence_ref="evidence:derived:2",
            ),
            parent_records=(first,),
        )
        self.assertIn("memory:source:1", second["lineage"]["original_source_refs"])
        self.assertIn("memory:derived:1", second["lineage"]["direct_source_refs"])
        self.assertEqual(second["lineage"]["parent_transformation_refs"], ["transform:test:1"])

    def test_source_dispute_revocation_and_tombstone_require_revalidation(self):
        record = normalize_transformation_evidence(transformation())
        for state in ("disputed", "revoked", "superseded", "tombstoned", "deleted"):
            with self.subTest(state=state):
                updated = reevaluate_source_currentness(record, {"memory:source:1": state})
                self.assertEqual(updated["source_currentness"]["status"], "revalidation_required")
                self.assertEqual(updated["applicability"]["status"], "revalidation_required")
                self.assertIn(f"source_{state}:memory:source:1", updated["source_currentness"]["reasons"])

    def test_unknown_source_state_is_not_treated_as_current(self):
        record = reevaluate_source_currentness(
            normalize_transformation_evidence(transformation()),
            {"memory:source:1": "unknown"},
        )
        self.assertEqual(record["source_currentness"]["status"], "unknown")
        self.assertEqual(record["applicability"]["status"], "revalidation_required")

    def test_scope_widening_or_cross_tenant_rebinding_is_invalid(self):
        record = normalize_transformation_evidence(
            transformation(
                transformation_id="transform:test:widen",
                derived_scope_ref="scope:tenant-b/project-b",
                derived_tenant_ref="tenant-b",
                derived_project_ref="project-b",
            )
        )
        self.assertEqual(record["scope"]["binding_status"], "mismatch")
        self.assertEqual(record["applicability"]["status"], "invalid")
        self.assertIn("tenant_widening_or_mismatch", record["applicability"]["reasons"])

    def test_explicit_scope_narrowing_requires_basis_evidence(self):
        with self.assertRaisesRegex(ValueError, "scope_relation"):
            normalize_transformation_evidence(transformation(scope_relation="broadened"))

        missing_basis = normalize_transformation_evidence(
            transformation(
                transformation_id="transform:test:narrow-no-basis",
                derived_ref="memory:derived:narrow-no-basis",
                derived_scope_ref="scope:tenant-a/project-a/task-7",
                scope_relation="narrowed",
            )
        )
        self.assertEqual(missing_basis["scope"]["binding_status"], "mismatch")
        self.assertEqual(missing_basis["applicability"]["status"], "invalid")

        narrowed = normalize_transformation_evidence(
            transformation(
                transformation_id="transform:test:narrow",
                derived_ref="memory:derived:narrow",
                derived_scope_ref="scope:tenant-a/project-a/task-7",
                scope_relation="narrowed",
                scope_basis_refs=["policy:scope-narrowing:task-7"],
            )
        )
        self.assertEqual(narrowed["scope"]["binding_status"], "narrowed")
        self.assertEqual(narrowed["applicability"]["status"], "current")

    def test_negative_and_adversarial_evidence_are_not_neutralized(self):
        for evidence_class in ("negative", "adversarial"):
            with self.subTest(evidence_class=evidence_class):
                record = normalize_transformation_evidence(
                    transformation(sources=[source(evidence_class=evidence_class)])
                )
                self.assertEqual(record["derived"]["evidence_character"], "negative_or_adversarial")

    def test_partial_or_failed_transformation_is_not_current(self):
        for status in ("partial", "failed"):
            with self.subTest(status=status):
                record = normalize_transformation_evidence(transformation(status=status))
                self.assertEqual(record["applicability"]["status"], "incomplete")
                self.assertIn(f"transformation_{status}", record["applicability"]["reasons"])

    def test_deterministic_identity_for_same_inputs(self):
        first = normalize_transformation_evidence(transformation())
        second = normalize_transformation_evidence(transformation())
        self.assertEqual(first, second)
        self.assertEqual(first["identity_digest"], second["identity_digest"])


if __name__ == "__main__":
    unittest.main()
