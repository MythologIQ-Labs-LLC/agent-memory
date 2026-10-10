"""#644 preregistered reproducer (META_LEDGER Entry #126): doc 77's no_eligible_value disposition.

Doc 77's disposition table states that a requested typed slot with no eligible typed value
among admitted facts has disposition `no_eligible_value`. When no typed claim exists for any
requested need, the report omits value coherence entirely. A consumer then cannot tell
"no eligible value" apart from "coherence never assessed". Replay
`governed-admitted-typed-value-coherence-v1` case V1 observes the omission.
"""
from __future__ import annotations

import unittest

from agentmem_ref.runtime import evidence_sufficiency as es
from agentmem_ref.runtime import typed_proposition as typed


def _need(subject: str, attribute: str) -> es.CoverageNeed:
    return es.CoverageNeed(typed.typed_slot(subject, attribute))


class NoEligibleValueDisposition(unittest.TestCase):
    def test_need_without_any_typed_claim_reports_no_eligible_value(self):
        need = _need("Disposition probe", "owner")
        report = es.assess_sufficiency(es.SufficiencyObservation(admitted_refs=("fact-a",), needs=(need,)))
        self.assertEqual([(v.need_key, v.status, v.fact_groups) for v in report.value_coherence],
                         [(need.key, "no_eligible_value", ())])
        self.assertEqual(report.to_dict()["value_coherence"],
                         [{"need_key": need.key, "status": "no_eligible_value", "fact_groups": []}])

    def test_every_declared_need_is_assessed_and_order_is_stable(self):
        needs = (_need("Disposition probe", "region"), _need("Disposition probe", "owner"))
        report = es.assess_sufficiency(es.SufficiencyObservation(admitted_refs=("fact-a",), needs=needs))
        self.assertEqual([v.need_key for v in report.value_coherence], sorted(n.key for n in needs))
        self.assertTrue(all(v.status == "no_eligible_value" for v in report.value_coherence))

    def test_no_eligible_value_never_creates_value_ambiguity_or_authority(self):
        need = _need("Disposition probe", "owner")
        report = es.assess_sufficiency(es.SufficiencyObservation(admitted_refs=("fact-a",), needs=(need,)))
        self.assertEqual(report.diagnosis, "missing_declared_evidence")
        self.assertEqual(report.continuation_proposal, "continue_if_permitted")
        self.assertEqual(report.to_dict()["authority_effect"], "none")

    def test_no_needs_means_no_assessments(self):
        report = es.assess_sufficiency(es.SufficiencyObservation(admitted_refs=("fact-a",)))
        self.assertEqual(report.value_coherence, ())


if __name__ == "__main__":
    unittest.main()
