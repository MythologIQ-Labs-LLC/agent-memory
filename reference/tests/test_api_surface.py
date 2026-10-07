"""Sprint 4a (LD4, LD5): the five public functions covering six PRD-001 R1 stages."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentmem_ref import policy  # noqa: E402
from agentmem_ref import procedural_memory as pm  # noqa: E402
from agentmem_ref.adapter import GovernedMemoryAdapter  # noqa: E402
from agentmem_ref.api import contract, surface  # noqa: E402
from agentmem_ref.substrate import InMemoryTemporalGraph  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "reference" / "fixtures" / "api"
EXAMPLE = json.loads((FIXTURES / "proposal-envelope.example.json").read_text(encoding="utf-8"))
RECALL = json.loads((FIXTURES / "recall-context.example.json").read_text(encoding="utf-8"))
ORG = "org:example"
TARGET = EXAMPLE["target_reference"]


class RecordingAdapter(GovernedMemoryAdapter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.writes = 0

    def commit_proposal(self, *args, **kwargs):
        self.writes += 1
        return super().commit_proposal(*args, **kwargs)

    def governed_delete(self, *args, **kwargs):
        self.writes += 1
        return super().governed_delete(*args, **kwargs)


def _correction(risk: str = "medium", snapshot: str = "v1", **extra) -> dict:
    return {**EXAMPLE, "operation": "correction", "risk_class": risk, "state_snapshot": snapshot, **extra}


def _skill_evidence():
    skill = pm.SkillArtifact(
        skill_id="skill-1", version=1, purpose="p", scope="project",
        isolation_domain_refs=("d1",), required_isolation_domain_refs=("d1",),
        procedure_markdown="# steps", provenance_refs=("prov-1",),
    )
    return pm.evidence_for(skill)


def _attestation(proposal_id: str = EXAMPLE["proposal_id"]) -> policy.ExternalVerification:
    return policy.ExternalVerification(bound_proposal_id=proposal_id, verifier_principal_id="human:reviewer",
                                       authority_kind=policy.HUMAN_CONFIRMATION, max_risk_class="critical")


class PublicSurface(unittest.TestCase):
    def setUp(self):
        self.memory = RecordingAdapter(InMemoryTemporalGraph(), tenant=ORG)
        seed = surface.commit(self.memory, EXAMPLE, "release branch release")
        self.assertTrue(seed["committed"]); self.assertEqual(seed["stage"], "commit")
        self.memory.writes = 0

    def test_propose_evaluates_without_writing(self):
        result = surface.propose(self.memory, _correction())
        self.assertEqual((result["stage"], result["outcome"]), ("proposal", policy.REQUIRE_REVIEW))
        self.assertEqual(result["compatibility"], contract.CURRENT)
        self.assertEqual(self.memory.state_version(TARGET), 1)
        self.assertEqual(self.memory.writes, 0)

    def test_approve_with_asserted_evidence_discharges_at_medium(self):
        result = surface.approve(self.memory, _correction(), evidence=_skill_evidence())
        self.assertEqual((result["stage"], result["outcome"]), ("approval", policy.ALLOW_WITH_LEDGER))
        self.assertEqual(result["decision"]["discharge_authority"], policy.DELEGATED_POLICY)
        self.assertEqual(self.memory.writes, 0)

    def test_approve_with_attestation_discharges_external_verification_at_critical(self):
        base = surface.propose(self.memory, _correction("critical"))
        self.assertEqual(base["outcome"], policy.REQUIRE_EXTERNAL_VERIFICATION)
        result = surface.approve(self.memory, _correction("critical"), attestation=_attestation())
        self.assertIn(result["outcome"], (policy.ALLOW, policy.ALLOW_WITH_LEDGER))
        # evaluate_with_external_verification records the attestation as review_discharge="verified".
        self.assertEqual(result["decision"]["review_discharge"], "verified")
        self.assertEqual(self.memory.writes, 0)

    def test_approve_without_evidence_parks(self):
        result = surface.approve(self.memory, _correction())
        self.assertEqual(result["outcome"], policy.REQUIRE_REVIEW)
        self.assertIn("enter_pending_verification", result["decision"]["permitted_actions"])
        self.assertEqual(result["decision"]["discharge_authority"], "")

    def test_commit_forwards_evidence_and_parks_without(self):
        parked = surface.commit(self.memory, _correction(), "release branch main")
        self.assertFalse(parked["committed"]); self.assertEqual(parked["outcome"], policy.REQUIRE_REVIEW)
        self.assertEqual(self.memory.state_version(TARGET), 1)
        committed = surface.commit(self.memory, _correction(), "release branch main", evidence=_skill_evidence())
        self.assertTrue(committed["committed"]); self.assertEqual(committed["receipt"]["decision_outcome"], policy.ALLOW_WITH_LEDGER)
        self.assertEqual(self.memory.state_version(TARGET), 2)

    def test_public_api_readmission_requires_separate_reversal_authority(self):
        first = _correction(
            "medium", "v1", proposal_id="proposal:public-to-main"
        )
        corrected = surface.commit(
            self.memory, first, "release branch main", evidence=_skill_evidence()
        )
        self.assertTrue(corrected["committed"])
        self.assertEqual(self.memory.state_version(TARGET), 2)

        reversal = _correction(
            "medium", "v2", proposal_id="proposal:public-back-to-release"
        )
        evidence_only = surface.commit(
            self.memory, reversal, "release branch release", evidence=_skill_evidence()
        )
        self.assertFalse(evidence_only["committed"])
        self.assertEqual(evidence_only["outcome"], policy.ALLOW_WITH_LEDGER)
        self.assertEqual(
            evidence_only["refusal"], "rejected_value_requires_reconciliation"
        )
        self.assertEqual(self.memory.state_version(TARGET), 2)

        approved = surface.commit(
            self.memory,
            reversal,
            "release branch release",
            evidence=_skill_evidence(),
            attestation=_attestation("proposal:public-back-to-release"),
        )
        self.assertTrue(approved["committed"])
        self.assertEqual(self.memory.state_version(TARGET), 3)
        history = self.memory.rejected_value_history(TARGET, "release branch release")
        self.assertEqual(history[0]["readmission_proposal_id"], "proposal:public-back-to-release")
        self.assertEqual(history[0]["readmission_verifier_principal_id"], "human:reviewer")
        self.assertEqual(history[0]["readmission_authority_kind"], policy.HUMAN_CONFIRMATION)

    def test_commit_attestation_only_discharges_external_verification_at_critical(self):
        result = surface.commit(
            self.memory,
            _correction("critical"),
            "release branch main",
            attestation=_attestation(),
        )
        self.assertTrue(result["committed"])
        self.assertEqual(result["outcome"], policy.ALLOW_WITH_LEDGER)
        self.assertEqual(result["decision"]["review_discharge"], "verified")
        self.assertEqual(self.memory.state_version(TARGET), 2)

    def test_commit_attestation_only_does_not_discharge_require_review(self):
        result = surface.commit(
            self.memory,
            _correction("medium"),
            "release branch main",
            attestation=_attestation(),
        )
        self.assertFalse(result["committed"])
        self.assertEqual(result["outcome"], policy.REQUIRE_REVIEW)
        self.assertEqual(result["decision"]["review_discharge"], "")
        self.assertEqual(self.memory.state_version(TARGET), 1)

    def test_commit_attestation_only_still_enforces_proposal_binding(self):
        result = surface.commit(
            self.memory,
            _correction("critical"),
            "release branch main",
            attestation=_attestation("proposal:wrong"),
        )
        self.assertFalse(result["committed"])
        self.assertEqual(result["outcome"], policy.REQUIRE_EXTERNAL_VERIFICATION)
        self.assertIn("attestation_not_bound_to_proposal", result["decision"]["reasons"])
        self.assertEqual(self.memory.state_version(TARGET), 1)

    def test_recall_returns_candidates_and_admissions(self):
        fact = self.memory.current_fact_uuid(TARGET)
        result = surface.recall(self.memory, "release branch", RECALL)
        self.assertEqual(result["stage"], "recall")
        self.assertIn(fact, result["candidates"])
        self.assertEqual(result["admissions"][fact]["outcome"], "admit")
        self.assertEqual(result["admissions"][fact]["reason_code"], "builtin_admission")
        self.assertEqual(result["candidate_policy"]["candidate_scope"], "domain_eligible")
        # Contract 1.3.0 (#548): outside the caller's domains the fact is not a candidate,
        # has no admission record, and nothing reveals that it matched.
        blocked = surface.recall(self.memory, "release branch", {**RECALL, "target_domain_refs": ["org:elsewhere"]})
        self.assertEqual(blocked["candidates"], [])
        self.assertEqual(blocked["admissions"], {})
        self.assertEqual(blocked["admitted"], [])

    def test_recall_budget_returns_ranked_prefix_and_keeps_admitted(self):
        # Contract 1.4.0 (#670): the budget is policy after admission; admitted stays whole.
        second = surface.commit(self.memory, {**EXAMPLE, "proposal_id": "proposal-second",
                                              "target_reference": "memory:second-release-branch"},
                                "release branch second")
        self.assertTrue(second["committed"])
        unbudgeted = surface.recall(self.memory, "release branch", RECALL)
        self.assertEqual(len(unbudgeted["admitted"]), 2)
        self.assertEqual(unbudgeted["returned"], unbudgeted["admitted"])
        self.assertEqual((unbudgeted["return_policy"]["requested_k"], unbudgeted["return_policy"]["applied"]), (None, False))
        budgeted = surface.recall(self.memory, "release branch", {**RECALL, "budget": {"k": 1}})
        self.assertEqual(budgeted["returned"], [budgeted["admitted"][0]])
        self.assertEqual(budgeted["admitted"], unbudgeted["admitted"])
        # the adapter's decision records carry per-call event ids; the decisions themselves are equal
        self.assertEqual({k: v["outcome"] for k, v in budgeted["admissions"].items()},
                         {k: v["outcome"] for k, v in unbudgeted["admissions"].items()})
        self.assertEqual(budgeted["candidates"], unbudgeted["candidates"])
        policy_record = budgeted["return_policy"]
        self.assertEqual((policy_record["requested_k"], policy_record["applied"]), (1, True))
        self.assertEqual((policy_record["admitted_count"], policy_record["returned_count"]), (2, 1))
        self.assertEqual(policy_record["authority_effect"], "none")

    def test_blocked_recall_under_budget_is_empty_not_truncated(self):
        blocked = surface.recall(self.memory, "release branch",
                                 {**RECALL, "target_domain_refs": ["org:elsewhere"], "budget": {"k": 1}})
        self.assertEqual(blocked["stage"], "recall")
        self.assertEqual((blocked["candidates"], blocked["admissions"], blocked["admitted"]), ([], {}, []))
        self.assertEqual(blocked["returned"], [])
        self.assertEqual((blocked["return_policy"]["applied"], blocked["return_policy"]["admitted_count"],
                          blocked["return_policy"]["returned_count"]), (False, 0, 0))

    def test_migration_required_envelope_carries_no_return_fields(self):
        newer = surface.recall(self.memory, "release branch", {**RECALL, "contract_version": "1.6.0", "budget": {"k": 1}})
        self.assertEqual((newer["stage"], newer["compatibility"]), ("none", contract.MIGRATION_REQUIRED))
        self.assertNotIn("returned", newer)
        self.assertNotIn("return_policy", newer)
        unknown = surface.recall(self.memory, "release branch", {k: v for k, v in RECALL.items() if k != "contract_version"})
        self.assertEqual((unknown["stage"], unknown["compatibility"]), ("none", contract.UNKNOWN))
        self.assertNotIn("returned", unknown)
        self.assertNotIn("return_policy", unknown)

    def test_forget_forwards_and_refuses_unknown(self):
        unknown = surface.forget(self.memory, {**_correction(), "target_reference": "repo:example:nothing"})
        self.assertFalse(unknown["committed"]); self.assertEqual(unknown["refusal"], "fact_not_found")
        deletion = {**EXAMPLE, "operation": "pruning", "risk_class": "low", "state_snapshot": "v1", "reversibility": "reversible"}
        result = surface.forget(self.memory, deletion, evidence=_skill_evidence())
        self.assertEqual(result["stage"], "forget")
        self.assertIn(result["outcome"], (policy.ALLOW, policy.ALLOW_WITH_LEDGER, policy.REQUIRE_REVIEW))

    def test_incompatible_version_runs_no_stage(self):
        result = surface.commit(self.memory, {**_correction(), "contract_version": "2.0.0"}, "x")
        self.assertEqual((result["stage"], result["compatibility"]), ("none", contract.INCOMPATIBLE))
        self.assertEqual(self.memory.writes, 0)
        invalid = surface.propose(self.memory, {**_correction(), "review_satisfied": True})
        self.assertEqual(invalid["stage"], "none"); self.assertIn("review_satisfied", invalid["validation_error"])


if __name__ == "__main__":
    unittest.main()
