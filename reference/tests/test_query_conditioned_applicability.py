"""ADR-039 (proposed) adversarial conformance fixtures for query-conditioned applicability.

Each test names the ADR-039 case it exercises. Cases the first bounded profile does not
satisfy are asserted as explicit, named limitations rather than skipped, so a later
change that closes (or silently alters) them fails loudly.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.runtime import ranking_policy, temporal_intent  # noqa: E402
from agentmem_ref.runtime.runtime_composition import MULTI_ROUTE_RANKING_POLICY  # noqa: E402
from agentmem_ref.runtime.temporal_intent import interpret_query  # noqa: E402

TENANT = "tenant:applicability"
SCOPE = "project:applicability"
NOW = "2026-09-26T12:00:00Z"


def _open(root: str, scope: str = SCOPE) -> AgentMemory:
    return AgentMemory.open(root, tenant=TENANT, actor_id="agent:applicability", scope=scope, purpose="applicability tests")


def _evidence(recalled: dict, fact_uuid: str) -> dict:
    return recalled["admissions"][fact_uuid]["ranking_evidence"]


class QueryConditionedApplicabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.memory = _open(self._temp.name)

    def tearDown(self) -> None:
        self.memory.close()
        self._temp.cleanup()

    def remember(self, key: str, text: str, **temporal) -> str:
        result = self.memory.remember(f"memory:{key}", text, **temporal)
        self.assertTrue(result["committed"], result)
        return result["fact_uuid"]

    def _ceo_pair(self) -> tuple[str, str]:
        old = self.remember(
            "ceo:2015", "The chief executive officer and CEO of Acme is Alice Smith.",
            valid_from="2015-01-01", valid_until="2020-06-01",
        )
        new = self.remember("ceo:2020", "Acme appointed Bob Jones as CEO.", valid_from="2020-06-01")
        return old, new

    # C1 / C23: current state beats a historically valid, semantically stronger match.
    def test_c1_c23_current_query_demotes_expired_exact_match(self):
        old, new = self._ceo_pair()
        recalled = self.memory.recall("Who is the current chief executive officer CEO of Acme?", reference_time=NOW)
        self.assertEqual(recalled["admitted"][:2], [new, old])
        old_evidence, new_evidence = _evidence(recalled, old), _evidence(recalled, new)
        self.assertGreater(old_evidence["lexical_relevance_score"], new_evidence["lexical_relevance_score"])
        self.assertEqual(old_evidence["temporal_applicability"], "outside_target_interval")
        self.assertEqual(new_evidence["temporal_applicability"], "applicable")
        self.assertEqual(new_evidence["ordered_before_next_by"], "temporal_applicability_tier")
        # Demoted, not refused: historical context remains available.
        self.assertIn(old, recalled["admitted"])

    # C2: as-of query prefers the evidence valid at the target instant.
    def test_c2_as_of_query_prefers_historically_applicable(self):
        old, new = self._ceo_pair()
        recalled = self.memory.recall("Who was the CEO of Acme in 2018?", reference_time=NOW)
        intent = _evidence(recalled, old)["query_temporal_intent"]
        self.assertEqual((intent["mode"], intent["posture"], intent["target_start"]), ("as_of", "inferred", "2018-01-01"))
        self.assertEqual(recalled["admitted"][:2], [old, new])
        self.assertEqual(_evidence(recalled, new)["temporal_applicability"], "prospectively_applicable")

    # C3 / C22: atemporal query does not let recency order equally relevant evidence.
    def test_c3_c22_atemporal_query_applies_no_temporal_preference(self):
        first = self.remember("notes:a", "Half-life notes: decay follows context.", valid_from="2020-01-01")
        second = self.remember("notes:b", "Half-life notes: decay follows usage.", valid_from="2026-01-01")
        recalled = self.memory.recall("What did I write about half-life decay?", reference_time=NOW)
        a, b = _evidence(recalled, first), _evidence(recalled, second)
        self.assertEqual(a["query_temporal_intent"]["mode"], "atemporal_or_unspecified")
        self.assertEqual(a["temporal_applicability"], "not_evaluated")
        self.assertIsNone(a["temporal_ordering_clock"])
        top = _evidence(recalled, recalled["admitted"][0])
        self.assertIn(top["ordered_before_next_by"], {"candidate_ref_neutral_digest", "lexical_relevance_desc:bm25_admitted_set:lexical"})
        # An older, more relevant memory beats a newer distractor (C22).
        gold = self.remember("notes:gold", "Memory half-life decay notes: half-life depends on context.", valid_from="2019-01-01")
        self.remember("notes:new", "Half-life came up briefly.", valid_from="2026-09-01")
        self.assertEqual(self.memory.recall("What did I write about memory half-life decay?", reference_time=NOW)["admitted"][0], gold)

    # C4: temporary exception interval, and recovery of the ordinary rule after expiry.
    def test_c4_temporary_exception_interval(self):
        rule = self.remember("office:rule", "The office closes at 5 PM.", valid_from="2025-01-01")
        exception = self.remember(
            "office:exception", "The office closes at 3 PM today because of weather.",
            valid_from="2026-09-25T00:00:00Z", valid_until="2026-09-26T00:00:00Z",
        )
        during = self.memory.recall("When does the office currently close?", reference_time="2026-09-25T12:00:00Z")
        self.assertEqual(_evidence(during, exception)["temporal_applicability"], "applicable")
        self.assertEqual(_evidence(during, rule)["temporal_applicability"], "applicable")
        after = self.memory.recall("When does the office currently close?", reference_time="2026-09-27T12:00:00Z")
        self.assertEqual(after["admitted"][0], rule)  # the rule is current again without reinsertion
        self.assertEqual(_evidence(after, exception)["temporal_applicability"], "outside_target_interval")
        # LIMITATION (ADR-039 C4, first half): during the exception both are applicable,
        # and the policy has no exception/specificity dimension. Relevance decides, so the
        # exception is not guaranteed to rank first. Recorded as an unmodelled dimension.
        self.assertEqual(set(during["admitted"][:2]), {rule, exception})

    # C5: disagreeing clocks; valid time, not transaction or observation time, orders current state.
    def test_c5_valid_time_is_not_replaced_by_transaction_or_observation_time(self):
        later_valid = self.remember(
            "plan:y", "The deployment plan is Yarrow.", valid_from="2025-01-01", observed_at="2021-01-01"
        )
        earlier_valid = self.remember(
            "plan:x", "The deployment plan is Xeno.", valid_from="2020-01-01", observed_at="2026-06-01"
        )
        recalled = self.memory.recall("What is the current deployment plan?", reference_time=NOW)
        self.assertEqual(recalled["admitted"][:2], [later_valid, earlier_valid])
        evidence = _evidence(recalled, later_valid)
        self.assertEqual(evidence["temporal_ordering_clock"], "declared_valid_from")
        self.assertEqual(
            set(evidence["temporal_evidence"]["clocks"]),
            {"declared_valid_from", "declared_observed_at", "transaction_time"},
        )

    # C6: unknown temporal basis is exposed, never treated as timeless or current.
    def test_c6_unknown_temporal_basis_is_explicit(self):
        unknown = self.remember("endpoint:unknown", "The deployment endpoint is alpha.example.")
        recalled = self.memory.recall("What is the current deployment endpoint?", reference_time=NOW)
        evidence = _evidence(recalled, unknown)
        self.assertEqual(evidence["temporal_applicability"], "unknown_temporal_basis")
        self.assertEqual(evidence["temporal_ordering_clock"], "transaction_time")
        self.assertEqual(evidence["temporal_evidence"]["substrate_valid_at_basis"], "runtime_write_clock")

    # C7: metabolic strength is not used and cannot resurrect stale current state.
    def test_c7_metabolic_strength_is_not_used(self):
        old, new = self._ceo_pair()
        for _ in range(10):  # repeated use of the stale memory
            self.memory.recall("Alice Smith chief executive officer", reference_time=NOW)
        recalled = self.memory.recall("Who is the current CEO of Acme?", reference_time=NOW)
        self.assertEqual(recalled["admitted"][0], new)
        self.assertEqual(_evidence(recalled, old)["metabolic_evidence"], "not_used")

    # C8, C9, C10, C11: newer independent writes never supersede; multi-valued and
    # hierarchical properties coexist.
    def test_c8_to_c11_independent_writes_coexist(self):
        pairs = [
            ("likes", "Kevin likes coffee.", "Kevin likes tea.", "What does Kevin currently like?"),
            ("lives", "Kevin lives in Maryland.", "Kevin lives in Stevensville.", "Where does Kevin currently live?"),
            ("works", "Kevin works at Bicameral.", "Kevin works at Accountable.Live.", "Where does Kevin currently work?"),
        ]
        for key, first_text, second_text, query in pairs:
            first = self.remember(f"{key}:1", first_text)
            second = self.remember(f"{key}:2", second_text)
            recalled = self.memory.recall(query, reference_time=NOW)
            self.assertIn(first, recalled["admitted"])
            self.assertIn(second, recalled["admitted"])
            self.assertEqual(self.memory.history(f"memory:{key}:1")["history"]["current_fact_uuid"], first)
            self.assertEqual(self.memory.history(f"memory:{key}:2")["history"]["current_fact_uuid"], second)

    # C12: a wrong-scope perfect current match remains refused and has no rank influence.
    def test_c12_wrong_scope_perfect_match_stays_refused(self):
        local = self.remember("status:local", "The current project status is green.", valid_from="2026-01-01")
        self.memory.close()
        with _open(self._temp.name, scope="project:foreign") as foreign:
            foreign_fact = foreign.remember(
                "memory:status:foreign", "The current project status is green and current.", valid_from="2026-09-01"
            )["fact_uuid"]
        self.memory = _open(self._temp.name)
        recalled = self.memory.recall("What is the current project status?", reference_time=NOW)
        self.assertNotIn(foreign_fact, recalled["admitted"])
        self.assertIn("refusal", recalled["admissions"][foreign_fact])
        self.assertNotIn("ranking_evidence", recalled["admissions"][foreign_fact])
        self.assertEqual(recalled["admitted"], [local])

    # C13 / C14: timeline shape keeps several states in chronological order.
    def test_c13_c14_timeline_preserves_every_state(self):
        roles = [
            self.remember("role:1", "My role was intern.", valid_from="2019-01-01", valid_until="2020-01-01"),
            self.remember("role:2", "My role was engineer.", valid_from="2020-01-01", valid_until="2024-01-01"),
            self.remember("role:3", "My role is architect.", valid_from="2024-01-01"),
        ]
        recalled = self.memory.recall("How did my role change over time?", reference_time=NOW)
        self.assertEqual(set(recalled["admitted"]), set(roles))
        evidence = {ref: _evidence(recalled, ref) for ref in roles}
        self.assertTrue(all(item["recall_shape"] == "timeline" for item in evidence.values()))
        self.assertEqual([evidence[ref]["timeline_position"] for ref in roles], [1, 2, 3])
        self.assertEqual(evidence[roles[0]]["query_temporal_intent"]["mode"], "historical")

    # C14 / C25 (governed correction): LIMITATION. A governed-superseded record is refused
    # at admission for every temporal intent, so recall cannot return the prior state.
    # history() serves it. Changing that is an admission decision, not a ranking one.
    def test_c14_c25_governed_superseded_state_is_not_recallable(self):
        self.remember("policy:retention", "The retention policy is 30 days.")
        corrected = self.memory.correct(
            "memory:policy:retention", "The retention policy is 90 days.", risk_class="low",
            evidence=_correction_evidence(),
        )
        recalled = self.memory.recall(
            "What was the retention policy before?",
            temporal_intent={"mode": "historical"},
            reference_time=NOW,
        )
        self.assertTrue(corrected["committed"], corrected)
        refusals = {decision.get("refusal") for decision in recalled["admissions"].values()}
        self.assertIn("superseded_not_current", refusals)
        self.assertEqual(recalled["admitted"], [corrected["fact_uuid"]])

    # C16: a low-confidence cue never becomes a temporal exclusion.
    def test_c16_low_confidence_intent_does_not_demote(self):
        expired = self.remember("rain:expired", "It is raining in Stevensville.", valid_until="2026-01-01")
        recalled = self.memory.recall("Is it still raining in Stevensville?", reference_time=NOW)
        evidence = _evidence(recalled, expired)
        self.assertEqual(evidence["query_temporal_intent"]["confidence"], "low")
        self.assertFalse(evidence["query_temporal_intent"]["orders_temporally"])
        self.assertEqual(evidence["temporal_applicability"], "not_evaluated")
        # Conflicting cues preserve ambiguity rather than choosing.
        ambiguous = interpret_query("Where do I live now, and where did I live before?")
        self.assertEqual((ambiguous.mode, ambiguous.confidence), ("atemporal_or_unspecified", "low"))

    # C17: explicit as-of intent overrides the inferred current cue.
    def test_c17_explicit_intent_overrides_inference(self):
        old, new = self._ceo_pair()
        recalled = self.memory.recall(
            "Who is the current CEO of Acme?",
            temporal_intent={"mode": "as_of", "target_start": "2018-01-01", "target_end": "2019-01-01"},
            reference_time=NOW,
        )
        intent = _evidence(recalled, old)["query_temporal_intent"]
        self.assertEqual((intent["mode"], intent["posture"]), ("as_of", "explicit"))
        self.assertEqual(recalled["admitted"][0], old)

    # C18: prospective memory is returned for prospective queries and demoted for current ones.
    def test_c18_prospective_commitment(self):
        current = self.remember("migration:current", "The database migration runs on the old cluster.", valid_from="2026-01-01")
        planned = self.remember(
            "migration:planned", "The database migration is scheduled for the new cluster.", valid_from="2026-10-05"
        )
        future = self.memory.recall("Which database migration is scheduled next week?", reference_time=NOW)
        self.assertEqual(_evidence(future, planned)["query_temporal_intent"]["mode"], "prospective")
        self.assertEqual(future["admitted"][0], planned)
        now = self.memory.recall("Where does the database migration currently run?", reference_time=NOW)
        self.assertEqual(_evidence(now, planned)["temporal_applicability"], "prospectively_applicable")
        self.assertEqual(now["admitted"][0], current)

    # C19 / C20: deterministic replay and policy-version identity.
    def test_c19_c20_deterministic_and_versioned(self):
        self._ceo_pair()
        runs = [self.memory.recall("Who is the current CEO of Acme?", reference_time=NOW)["admitted"] for _ in range(3)]
        self.assertEqual(runs[0], runs[1])
        self.assertEqual(runs[1], runs[2])
        self.memory.close()
        self.memory = _open(self._temp.name)
        self.assertEqual(self.memory.recall("Who is the current CEO of Acme?", reference_time=NOW)["admitted"], runs[0])
        identity = MULTI_ROUTE_RANKING_POLICY.identity()
        self.assertEqual((identity["policy_version"], identity["temporal_regime"]), ("3.0.0", "query_conditioned"))

    # C21: no benchmark-specific branching in the applicability path.
    def test_c21_no_benchmark_identifiers_in_policy_modules(self):
        for module in (ranking_policy, temporal_intent):
            source = Path(module.__file__).read_text(encoding="utf-8").lower()
            for token in ("longmemeval", "agentmembench", "memdialogue", "locomo", "knowledge-update", "question_type"):
                self.assertNotIn(token, source, (module.__name__, token))

    # C24: disputed evidence stays disputed. LIMITATION/stronger: this runtime refuses a
    # disputed fact at admission, so applicability never presents it at all.
    def test_c24_disputed_current_evidence_is_refused(self):
        disputed = self.remember("status:disputed", "The current release is Cedar.", valid_from="2026-09-01")
        self.memory.runtime.adapter.mark_disputed(disputed)
        recalled = self.memory.recall("What is the current release?", reference_time=NOW)
        self.assertNotIn(disputed, recalled["admitted"])
        self.assertEqual(recalled["admissions"][disputed]["refusal"], "disputed")

    # Declared temporal evidence is validated and never becomes lifecycle state.
    def test_declared_temporal_is_evidence_not_lifecycle(self):
        with self.assertRaises(ValueError):
            self.memory.remember("memory:bad", "bad interval", valid_from="2026-01-02", valid_until="2026-01-01")
        with self.assertRaises(ValueError):
            self.memory.remember("memory:bad", "bad time", valid_from="yesterday")
        expired = self.remember("fact:expired", "The legacy endpoint is beta.example.", valid_until="2020-01-01")
        recalled = self.memory.recall("legacy endpoint beta", reference_time=NOW)
        self.assertEqual(recalled["admitted"], [expired])  # admitted: validity is not admission
        self.assertEqual(self.memory.history("memory:fact:expired")["history"]["current_fact_uuid"], expired)


def _correction_evidence():
    from agentmem_ref.memory import procedural_memory as pm

    skill = pm.SkillArtifact(
        skill_id="skill:applicability-correction",
        version=1,
        purpose="correct retained test memory",
        scope=SCOPE,
        isolation_domain_refs=(TENANT, SCOPE),
        required_isolation_domain_refs=(TENANT, SCOPE),
        procedure_markdown="# verify\nConfirm the correction against the current source.",
        provenance_refs=("evidence:applicability-correction-source",),
    )
    return pm.evidence_for(skill)


if __name__ == "__main__":
    unittest.main()
