from __future__ import annotations

import sys
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref import AgentMemory, policy  # noqa: E402
from agentmem_ref.memory import procedural_memory as pm  # noqa: E402
from agentmem_ref.runtime.adapter import Clock  # noqa: E402
from agentmem_ref.runtime.ranking_policy import PostAdmissionRankingPolicy, temporal_evidence  # noqa: E402
from agentmem_ref.runtime.runtime_composition import EXACT_IDENTITY_ROUTE, MULTI_ROUTE_RANKING_POLICY  # noqa: E402

TENANT = "tenant:ranking"
SCOPE = "project:ranking"
QUERY = "What is the current release codename?"


def _correction_evidence():
    skill = pm.SkillArtifact(
        skill_id="skill:ranking-correction",
        version=1,
        purpose="correct retained test memory",
        scope=SCOPE,
        isolation_domain_refs=(TENANT, SCOPE),
        required_isolation_domain_refs=(TENANT, SCOPE),
        procedure_markdown="# verify\nConfirm the correction against the current source.",
        provenance_refs=("evidence:ranking-correction-source",),
    )
    return pm.evidence_for(skill)


@dataclass
class _Hit:
    route_id: str
    raw_score: float


@dataclass
class _Fact:
    valid_at: str | None = None
    created_at: str | None = None


def _policy() -> PostAdmissionRankingPolicy:
    return PostAdmissionRankingPolicy(policy_id="test", route_score_order=("lexical",), exact_identity_route="exact")


class PolicyUnitTests(unittest.TestCase):
    def test_equal_relevance_orders_newer_first_then_stable_id(self):
        hits = {ref: [_Hit("lexical", 0.5)] for ref in ("ref-0001", "ref-0002", "ref-0003")}
        facts = {
            "ref-0001": _Fact(valid_at="2026-01-01T00:00:10Z"),
            "ref-0002": _Fact(valid_at="2026-01-01T00:02:00Z"),
            "ref-0003": _Fact(valid_at="2026-01-01T00:00:10Z"),
        }
        ordered, evidence = _policy().rank(list(hits), hits, facts.get)
        self.assertEqual(ordered, ["ref-0002", "ref-0001", "ref-0003"])
        self.assertEqual(evidence["ref-0002"]["temporal_axis"], "valid_at")
        self.assertEqual(evidence["ref-0002"]["authority_effect"], "none")

    def test_relevance_stages_dominate_temporal_evidence(self):
        hits = {"ref-0001": [_Hit("lexical", 0.9)], "ref-0002": [_Hit("lexical", 0.5)]}
        facts = {"ref-0001": _Fact(valid_at="2026-01-01T00:00:01Z"), "ref-0002": _Fact(valid_at="2026-01-02T00:00:00Z")}
        ordered, _ = _policy().rank(list(hits), hits, facts.get)
        self.assertEqual(ordered, ["ref-0001", "ref-0002"])

    def test_missing_or_unparseable_temporal_evidence_sorts_after_present_then_by_id(self):
        hits = {ref: [_Hit("lexical", 0.5)] for ref in ("ref-0001", "ref-0002", "ref-0003", "ref-0004")}
        facts = {
            "ref-0001": _Fact(),
            "ref-0002": _Fact(valid_at="2026-01-01T00:00:60Z", created_at=None),
            "ref-0003": _Fact(valid_at=None, created_at="2026-01-01T00:00:05Z"),
            "ref-0004": None,
        }
        ordered, evidence = _policy().rank(list(hits), hits, facts.get)
        self.assertEqual(ordered, ["ref-0003", "ref-0001", "ref-0002", "ref-0004"])
        self.assertEqual(evidence["ref-0003"]["temporal_axis"], "created_at")
        self.assertIsNone(evidence["ref-0002"]["temporal_seconds"])
        self.assertEqual(temporal_evidence(_Fact(valid_at="not-a-time")), (None, None, None))

    def test_temporal_tiebreak_can_be_disabled_explicitly(self):
        policy = PostAdmissionRankingPolicy(
            policy_id="no-time", route_score_order=("lexical",), exact_identity_route="exact", temporal_tiebreak="none"
        )
        hits = {ref: [_Hit("lexical", 0.5)] for ref in ("ref-0001", "ref-0002")}
        facts = {"ref-0001": _Fact(valid_at="2026-01-01T00:00:01Z"), "ref-0002": _Fact(valid_at="2026-01-02T00:00:00Z")}
        self.assertEqual(policy.rank(list(hits), hits, facts.get)[0], ["ref-0001", "ref-0002"])
        with self.assertRaises(ValueError):
            PostAdmissionRankingPolicy(policy_id="x", route_score_order=("a", "a"), exact_identity_route="e")
        with self.assertRaises(ValueError):
            PostAdmissionRankingPolicy(policy_id="x", route_score_order=("a",), exact_identity_route="e", temporal_tiebreak="oldest")

    def test_policy_identity_is_explicit_and_authority_neutral(self):
        identity = MULTI_ROUTE_RANKING_POLICY.identity()
        self.assertEqual(identity["policy_id"], "multi-route-default")
        self.assertEqual(identity["authority_effect"], "none")
        self.assertFalse(identity["route_scores_cross_comparable"])
        self.assertEqual(identity["stages"][-2:], ["temporal_evidence:newer_first", "candidate_ref_asc"])

    def test_clock_timestamps_are_valid_and_chronological_past_old_overflow(self):
        clock = Clock()
        stamps = [clock.now() for _ in range(250)]
        self.assertEqual(stamps, sorted(stamps))
        self.assertEqual(stamps[59], "2026-01-01T00:01:00Z")
        self.assertTrue(all(temporal_evidence(_Fact(valid_at=stamp))[2] is not None for stamp in stamps))


class FacadeRankingTests(unittest.TestCase):
    def _open(self, root: str, scope: str = SCOPE) -> AgentMemory:
        return AgentMemory.open(root, tenant=TENANT, actor_id="agent:ranking", scope=scope, purpose="ranking tests")

    def test_equal_score_independent_writes_rank_newer_first_without_supersession(self):
        with tempfile.TemporaryDirectory() as root, self._open(root) as memory:
            for index in range(120):  # push the deterministic clock past the old overflow points
                memory.remember(f"memory:filler:{index}", f"unrelated filler observation {index}")
            old = memory.remember("memory:release:old", "The current release codename is Alder.")
            new = memory.remember("memory:release:new", "The current release codename is Birch.")
            recalled = memory.recall(QUERY)
            self.assertEqual(recalled["admitted"][:2], [new["fact_uuid"], old["fact_uuid"]])
            old_evidence = recalled["admissions"][old["fact_uuid"]]["ranking_evidence"]
            new_evidence = recalled["admissions"][new["fact_uuid"]]["ranking_evidence"]
            self.assertEqual(old_evidence["route_scores"], new_evidence["route_scores"])
            self.assertGreater(new_evidence["temporal_seconds"], old_evidence["temporal_seconds"])
            self.assertEqual(new_evidence["policy_id"], "multi-route-default")
            self.assertEqual(new_evidence["authority_effect"], "none")
            # Ranking is not supersession: both facts stay current and admitted.
            self.assertEqual(memory.history("memory:release:old")["history"]["current_fact_uuid"], old["fact_uuid"])
            self.assertIn(old["fact_uuid"], recalled["admitted"])

    def test_ranking_is_deterministic_across_calls_and_restart(self):
        with tempfile.TemporaryDirectory() as root:
            with self._open(root) as memory:
                for index in range(5):
                    memory.remember(f"memory:codename:{index}", f"The current release codename is v{index}.")
                first = memory.recall(QUERY)["admitted"]
                second = memory.recall(QUERY)["admitted"]
            with self._open(root) as memory:
                third = memory.recall(QUERY)["admitted"]
        self.assertEqual(first, second)
        self.assertEqual(first, third)

    def test_wrong_scope_and_superseded_candidates_stay_refused_regardless_of_recency(self):
        with tempfile.TemporaryDirectory() as root, self._open(root) as memory:
            first = memory.remember("memory:release", "The current release codename is Alder.")
            corrected = memory.correct(
                "memory:release", "The current release codename is Cedar.", evidence=_correction_evidence()
            )
            self.assertTrue(corrected["committed"])
            self.assertEqual(corrected["outcome"], policy.ALLOW_WITH_LEDGER)
            other_scope = {
                "scope": "project:other",
                "isolation_domain_refs": [TENANT, "project:other"],
                "required_isolation_domain_refs": [TENANT, "project:other"],
                "project_ref": "project:other",
            }
            # The foreign fact is the NEWEST write; recency must not admit it.
            foreign = memory.remember("memory:foreign", "The current release codename is Zelkova.", overrides=other_scope)
            self.assertTrue(foreign["committed"])
            recalled = memory.recall(QUERY)
            for refused in (first["fact_uuid"], foreign["fact_uuid"]):
                self.assertIn(refused, recalled["candidates"])
                self.assertNotIn(refused, recalled["admitted"])
                self.assertIn("refusal", recalled["admissions"][refused])
                self.assertNotIn("ranking_evidence", recalled["admissions"][refused])
            self.assertEqual(recalled["admitted"], [corrected["fact_uuid"]])

    def test_route_provenance_survives_ranking(self):
        with tempfile.TemporaryDirectory() as root, self._open(root) as memory:
            fact = memory.remember("memory:release", "The current release codename is Alder.")
            recalled = memory.recall(QUERY, logical_memory_refs=["memory:release"])
            decision = recalled["admissions"][fact["fact_uuid"]]
            routes = sorted({hit["route_id"] for hit in decision["route_provenance"]})
            self.assertEqual(routes, decision["ranking_evidence"]["routes"])
            self.assertIn(EXACT_IDENTITY_ROUTE, routes)
            self.assertTrue(decision["ranking_evidence"]["exact_identity"])
            self.assertEqual(decision["rank_position"], decision["ranking_evidence"]["rank_position"])


if __name__ == "__main__":
    unittest.main()
