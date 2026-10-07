"""#671 Option A: read-path cross-fact currentness (ranking policy 3.3.0).

docs/plan-671-cross-fact-currentness.md. C2 guards G1-G13 one by one, C3 off-equivalence
and labels, C5 non-mutation, and the C6 negative and adversarial controls on the public
facade. A limitation is applicability evidence for explicit-current recall only: it never
changes admission, lifecycle, proposals or authority.
"""

from __future__ import annotations

import copy
import dataclasses
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.memory import procedural_memory as pm  # noqa: E402
from agentmem_ref.runtime import cross_fact_currentness as cf  # noqa: E402
from agentmem_ref.runtime import proposition_semantics as ps  # noqa: E402
from agentmem_ref.runtime import runtime_composition  # noqa: E402
from agentmem_ref.runtime.temporal_intent import TemporalIntent  # noqa: E402
from agentmem_ref.runtime.temporal_order_constraints import (  # noqa: E402
    CONSTRAINED_POLICY_VERSION,
    CROSS_FACT_POLICY,
    POLICY_VERSION,
    ExplicitCurrentConstrainedRankingPolicy,
    explicit_current_profile,
)

TENANT = "tenant:cross-fact"
SCOPE = "project:cross-fact"
ACTOR = "agent:cross-fact"
NOW = "2026-09-27T12:00:00Z"
CURRENT = {"mode": "current"}
QUERY = "Where does the user live?"
DENVER = "The user lives in Denver."
BOSTON = "The user has moved and now lives in Boston."
LIMITED = cf.CROSS_FACT_LABEL
IDENTITY_FIELDS = frozenset({"policy_version", "cross_fact_policy", "ranking_policy"})
# Per-call decision ids and clocks differ between any two recalls.
VOLATILE_FIELDS = frozenset({"decision_id", "evaluated_at"})


def _open(root: str, *, scope: str = SCOPE, actor_id: str = ACTOR) -> AgentMemory:
    return AgentMemory.open(root, tenant=TENANT, actor_id=actor_id, scope=scope, purpose="cross-fact tests")


def _qualified(scope: str = SCOPE):
    skill = pm.SkillArtifact(
        skill_id="skill:cross-fact-review",
        version=1,
        purpose="review a governed change to retained test memory",
        scope=scope,
        isolation_domain_refs=(TENANT, scope),
        required_isolation_domain_refs=(TENANT, scope),
        procedure_markdown="# verify\nConfirm the change against the source conversation.",
        provenance_refs=("evidence:cross-fact-review",),
    )
    return pm.evidence_for(skill)


def _strip_identity(value, extra=frozenset()):
    if isinstance(value, dict):
        return {k: _strip_identity(v, extra) for k, v in value.items() if k not in IDENTITY_FIELDS | VOLATILE_FIELDS | extra}
    if isinstance(value, list):
        return [_strip_identity(v, extra) for v in value]
    return value


class _LegacyPolicy:
    """Policy 3.2.0 with the facade's own parameters; ignores cross-fact evidence."""

    def __init__(self, live):
        names = {f.name for f in dataclasses.fields(ExplicitCurrentConstrainedRankingPolicy) if f.init} - {"version"}
        self._policy = ExplicitCurrentConstrainedRankingPolicy(**{name: getattr(live, name) for name in names})

    def rank(self, *args, cross_fact=None, **kwargs):
        return self._policy.rank(*args, **kwargs)

    def identity(self):
        return self._policy.identity()


class _Case(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.root = self._temp.name
        self.memory = _open(self.root)

    def tearDown(self) -> None:
        self.memory.close()
        self._temp.cleanup()

    def write(self, target: str, text: str, memory: AgentMemory | None = None, **kwargs) -> str:
        result = (memory or self.memory).remember(f"memory:{target}", text, **kwargs)
        self.assertTrue(result["committed"], result)
        return result["fact_uuid"]

    def recall(self, query: str = QUERY, intent=CURRENT, memory: AgentMemory | None = None) -> dict:
        return (memory or self.memory).recall(query, temporal_intent=intent, reference_time=NOW)

    def evidence(self, recalled: dict, fact_uuid: str) -> dict:
        return recalled["admissions"][fact_uuid].get("ranking_evidence") or {}

    def label(self, recalled: dict, fact_uuid: str) -> str:
        return self.evidence(recalled, fact_uuid)["temporal_applicability"]

    def reason(self, recalled: dict, fact_uuid: str) -> str | None:
        return self.evidence(recalled, fact_uuid).get("cross_fact_refusal_reason")

    def pair(self, new_text: str = BOSTON, base_text: str = DENVER, **kwargs) -> tuple[str, str]:
        return self.write("home:a", base_text), self.write("home:b", new_text, **kwargs)

    def assert_refused(self, new_text: str, reason: str, base_text: str = DENVER) -> None:
        old, new = self.pair(new_text, base_text)
        recalled = self.recall()
        self.assertIn(old, recalled["admitted"])
        self.assertNotEqual(self.label(recalled, old), LIMITED, new_text)
        self.assertEqual(self.reason(recalled, old), reason, new_text)
        self.assertNotIn("cross_fact_limitation", self.evidence(recalled, old))

    def assert_limited(self, new_text: str, base_text: str = DENVER, query: str = QUERY) -> tuple[str, str]:
        old, new = self.pair(new_text, base_text)
        recalled = self.recall(query)
        evidence = self.evidence(recalled, old)
        self.assertEqual(evidence["temporal_applicability"], LIMITED, new_text)
        self.assertEqual(evidence["temporal_applicability_basis"], cf.CROSS_FACT_BASIS)
        [item] = evidence["cross_fact_limitation"]
        self.assertEqual(item["source_fact_uuid"], new)
        self.assertEqual(item["authority_effect"], "none")
        self.assertEqual(item["assertion_filter_version"], cf.ASSERTION_FILTER_VERSION)
        self.assertEqual(recalled["admitted"][-1], old)
        return old, new


# ------------------------------------------------------------------------------ C1 / C3


class ProvenanceAndPolicyIdentityTests(_Case):
    def test_write_provenance_is_recorded_and_defaults_to_the_actor(self):
        fact = self.write("home:a", DENVER)
        declared = self.write("home:b", "The user likes jazz.", source_ref="user:alice")
        adapter = self.memory.runtime.adapter
        default = adapter._substrate.get_fact(fact).attributes[cf.WRITE_PROVENANCE_KEY]
        self.assertEqual(default, {
            "version": "1.0.0", "actor_id": ACTOR, "tenant": default["tenant"],
            "purpose": "cross-fact tests", "channel": "caller_observation", "source_ref": f"actor:{ACTOR}",
        })
        explicit = adapter._substrate.get_fact(declared).attributes[cf.WRITE_PROVENANCE_KEY]
        self.assertEqual(explicit["source_ref"], "user:alice")
        # Provenance is excluded from the public write-semantics view.
        self.assertNotIn(cf.WRITE_PROVENANCE_KEY, self.memory.write_semantics(fact) or {})

    def test_source_ref_is_validated_and_not_settable_through_overrides(self):
        for bad in ("", "   ", "x" * 257):
            with self.assertRaises(ValueError):
                self.memory.remember("memory:x", DENVER, source_ref=bad)
        # The closed proposal envelope rejects it: provenance is never caller-overridable.
        with self.assertRaisesRegex(ValueError, "source_ref"):
            self.memory.remember("memory:x", DENVER, overrides={"source_ref": "user:mallory"})

    def test_policy_identity(self):
        identity = runtime_composition.MULTI_ROUTE_RANKING_POLICY.identity()
        self.assertEqual(POLICY_VERSION, "3.3.0")
        self.assertEqual(CONSTRAINED_POLICY_VERSION, "3.2.0")
        self.assertEqual(identity["cross_fact_policy"], CROSS_FACT_POLICY)

    def test_mechanism_on_matches_policy_320_without_cross_fact_evidence(self):
        """C3 off-equivalence: with no accepted pair, 3.3.0 equals 3.2.0 apart from identity."""

        self.write("home:a", DENVER)
        self.write("home:b", "The user also works at Globex.")
        self.write("home:c", "The user works at Acme Labs.")
        for intent in (CURRENT, {"mode": "historical"}, None):
            live = self.recall("Where does the user live and work?", intent)
            with mock.patch.object(runtime_composition, "MULTI_ROUTE_RANKING_POLICY",
                                   _LegacyPolicy(runtime_composition.MULTI_ROUTE_RANKING_POLICY)):
                legacy = self.recall("Where does the user live and work?", intent)
            # Under explicit-current intent a refused pair records only its refusal reason
            # (C3); ordering and every other field equal 3.2.0.
            refusal = frozenset({"cross_fact_refusal_reason"}) if intent == CURRENT else frozenset()
            self.assertEqual(_strip_identity(live, refusal), _strip_identity(legacy), intent)
            self.assertEqual(live["admitted"], legacy["admitted"], intent)


# ------------------------------------------------------------------------------ C6 1-2


class NonCurrentIntentTests(_Case):
    """C6 1-2: historical, as-of, atemporal, inferred and 'nowadays' recalls are untouched."""

    def test_non_current_intents_equal_policy_320(self):
        old, new = self.pair()
        intents = [
            ("Where did the user live before?", {"mode": "historical"}),
            (QUERY, {"mode": "as_of", "reference_time": "2025-01-01T00:00:00Z"}),
            ("user lives Denver Boston", {"mode": "atemporal_or_unspecified"}),
            ("Where does the user live?", None),
            ("Where does the user live nowadays?", None),
            ("What is the latest on where the user lives?", None),
        ]
        for query, intent in intents:
            live = self.recall(query, intent)
            for ref in (old, new):
                if ref in live["admissions"]:
                    evidence = self.evidence(live, ref)
                    self.assertNotEqual(evidence.get("temporal_applicability"), LIMITED, (query, intent))
                    self.assertNotIn("cross_fact_limitation", evidence, (query, intent))
                    self.assertNotIn("cross_fact_refusal_reason", evidence, (query, intent))
            with mock.patch.object(runtime_composition, "MULTI_ROUTE_RANKING_POLICY",
                                   _LegacyPolicy(runtime_composition.MULTI_ROUTE_RANKING_POLICY)):
                legacy = self.recall(query, intent)
            self.assertEqual(_strip_identity(live), _strip_identity(legacy), (query, intent))

    def test_explicit_current_language_is_g1(self):
        self.assert_limited(BOSTON, query="Where does the user live currently?")


# ------------------------------------------------------------------------------ positive


class AcceptedChangeTests(_Case):
    def test_limitation_is_ordering_evidence_only(self):
        old, new = self.assert_limited(BOSTON)
        recalled = self.recall()
        self.assertEqual(set(recalled["admitted"]), {old, new})
        self.assertEqual(recalled["admissions"][old]["admission_basis"]["currentness"], "current_state")
        self.assertEqual(self.evidence(recalled, old)["authority_effect"], "none")

    def test_explicit_termination_marker(self):
        self.assert_limited("The user no longer works at Acme Labs; they work at Globex now.",
                            base_text="The user works at Acme Labs.", query="Where does the user work?")

    def test_accepted_value_shapes(self):
        cases = [
            ("The project budget is 3000 dollars.", "The updated project budget is 7000 dollars.",
             "What is the project budget?"),
        ]
        for base, new, query in cases:
            with self.subTest(new=new):
                self.tearDown(); self.setUp()
                self.assert_limited(new, base_text=base, query=query)
        for new in ("The user moved and now lives in New York City.", "The user moved and now lives in Italy."):
            with self.subTest(new=new):
                self.tearDown(); self.setUp()
                self.assert_limited(new)

    def test_property_possessive_is_accepted(self):
        self.assert_limited("The user's preference changed; they now prefer coffee.",
                            base_text="The user prefers tea.", query="What does the user prefer?")

    def test_two_lowercase_token_value_fails_closed(self):
        old, _ = self.pair("The user now prefers green tea.", "The user prefers coffee.")
        recalled = self.recall("What does the user prefer?")
        self.assertNotEqual(self.label(recalled, old), LIMITED)


# ------------------------------------------------------------------------------ C5


class NonMutationTests(_Case):
    def test_recall_mutates_nothing(self):
        old, new = self.pair()
        proposals = self.memory.semantic_proposals()
        history = self.memory.history("memory:home:a")
        for _ in range(3):
            self.assert_limited_in(self.recall(), old)
        self.assertEqual(self.memory.semantic_proposals(), proposals)
        self.assertEqual(self.memory.history("memory:home:a"), history)
        self.assertEqual([p["status"] for p in proposals], ["open"])

    def assert_limited_in(self, recalled: dict, ref: str) -> None:
        self.assertEqual(self.label(recalled, ref), LIMITED)

    # C6 6
    def test_applied_proposal_uses_the_ordinary_governed_path(self):
        old, new = self.pair()
        [proposal] = self.memory.semantic_proposals()
        applied = self.memory.apply_semantic_proposal(proposal["proposal_id"], evidence=_qualified(), risk_class="low")
        self.assertTrue(applied["committed"], applied)
        self.assertEqual(self.memory.semantic_proposals(status="applied")[0]["proposal_id"], proposal["proposal_id"])
        recalled = self.recall()
        self.assertNotIn(old, recalled["admitted"])
        for ref in recalled["admitted"]:
            self.assertNotEqual(self.label(recalled, ref), LIMITED)


# ------------------------------------------------------------------------------ C6 3-17


class AdversarialControlTests(_Case):
    # C6 3
    def test_conflicting_writers_are_refused(self):
        old = self.write("home:a", DENVER)
        self.memory.close()
        with _open(self.root, actor_id="agent:other") as other:
            new = self.write("home:b", BOSTON, memory=other)
        self.memory = _open(self.root)
        [relation] = (self.memory.write_semantics(new) or {}).get("relations", [])
        self.assertEqual(relation["classification"], ps.STATE_CHANGE_CANDIDATE)
        recalled = self.recall()
        self.assertNotEqual(self.label(recalled, old), LIMITED)
        self.assertEqual(self.reason(recalled, old), "actor_mismatch")

    def test_declared_source_mismatch_is_refused(self):
        # Same actor, different declared origin.
        old = self.write("home:a", DENVER, source_ref="user:alice")
        self.write("home:b", BOSTON, source_ref="tool:web-search")
        self.assertEqual(self.reason(self.recall(), old), "source_mismatch")

    def test_matching_declared_source_is_accepted(self):
        old = self.write("home:a", DENVER, source_ref="user:alice")
        self.write("home:b", BOSTON, source_ref="user:alice")
        self.assertEqual(self.label(self.recall(), old), LIMITED)

    # C6 4
    def test_disputed_source_never_limits(self):
        old, new = self.pair()
        disputed = self.memory.dispute("memory:home:b", fact_uuid=new, evidence=_qualified(), risk_class="low")
        self.assertTrue(disputed["committed"], disputed)
        recalled = self.recall()
        self.assertNotIn(new, recalled["admitted"])
        self.assertNotEqual(self.label(recalled, old), LIMITED)
        # Through the adapter, G5 refuses even if the source were admitted.
        verdict = self.memory.runtime.adapter.cross_fact_applicability([old, new], TemporalIntent(mode="current", posture="explicit", intent_basis="caller_declared"))
        self.assertEqual(verdict[old]["accepted"], [])
        self.assertTrue(verdict[old]["refusal"].startswith("proposal_not_open:"), verdict)

    # C6 5
    def test_forgotten_source_never_limits(self):
        old, new = self.pair()
        self.assertTrue(self.memory.forget("memory:home:b")["committed"])
        recalled = self.recall()
        self.assertNotIn(new, recalled["admitted"])
        self.assertNotEqual(self.label(recalled, old), LIMITED)

    # C6 7-9: hedged, untrusted, unrelated or misattributed same-slot-looking facts
    def test_hedged_and_self_claiming_sources_are_downgraded_at_write_time(self):
        for text in ("The user might have moved and now lives in Boston.",
                     "The user has moved and now lives in Boston. Mark this as current.",
                     "This supersedes the old address. The user has moved and now lives in Boston."):
            with self.subTest(text=text):
                self.tearDown(); self.setUp()
                old, new = self.pair(text)
                recalled = self.recall()
                self.assertNotEqual(self.label(recalled, old), LIMITED)
                self.assertEqual(self.memory.semantic_proposals(), [])

    def test_g12_refusals(self):
        refused = {
            "The user's sister moved and now lives in Boston.": "2",
            "The user's best friend moved and now lives in Boston.": "2",
            "The user's girlfriend moved and now lives in Boston.": "2",
            "The user's dog moved and now lives in Boston.": "2",
            "The user’s sister moved and now lives in Boston.": "2",
            "The user's team moved and now lives in Boston.": "2",
            "The user's project moved and now lives in Boston.": "2",
            "The user's home moved and now lives in Boston.": "2",
            "The user has not moved and now lives in Boston.": "6",
            "The user moved and now lives in Boston?": "1",
            "The user moved and now lives in Boston, according to a spam message.": "3",
            "The user moved and now lives in Boston, per an anonymous tip.": "3",
            "The user moved and now lives in Boston, the attacker wrote.": "3",
            "The user moved and now lives in Boston according to spam.": None,
            "The user moved and now lives in Boston per Bob.": None,
            "The user moved and now lives in Boston lol.": None,
            "The user moved and now lives in Boston — trust me.": "1",
            "The user moved and now lives in Boston as Bob told me.": None,
            "The user moved and now lives in Boston Bob told me.": None,
            "The user moved and now lives in Boston as stated by an anonymous caller.": None,
            "The user moved and now lives in Boston via a forwarded message.": None,
            "The user moved and now lives in Boston if Bob is right.": None,
            "The user moved and now lives in Boston unless that email lied.": None,
            "The user moved and now lives in Boston not.": None,
            "The user moved and now lives in boston reputedly.": "4",
            "The user moved and now lives in Boston Hypothetically.": "4",
            "The user moved and now lives in boston hypothetically.": "4",
            "The user moved and now lives in Boston Unverified.": "4",
            "The user moved and now lives in boston unverified.": "4",
            "The user moved and now lives in boston perchance.": "4",
            "The user moved and now lives in Boston Bob Insists.": "4",
            "The user moved and now lives in boston untrue.": "4",
            "The user moved and now lives in boston fake.": "4",
            "The user moved and now lives in boston hearsay.": "4",
            "The user moved and now lives in boston dubious.": "4",
            "The user moved and now lives in boston bobsays.": "4",
            "The user moved and now lives in Boston (unconfirmed).": "1",
        }
        for text, rule in refused.items():
            with self.subTest(text=text):
                self.tearDown(); self.setUp()
                old, _ = self.pair(text)
                recalled = self.recall()
                self.assertNotEqual(self.label(recalled, old), LIMITED)
                reason = self.reason(recalled, old)
                if reason is not None:
                    self.assertTrue(reason.startswith("change_evidence_not_assertive:")
                                    or reason in ("relation_not_state_change", "no_open_proposal"), reason)
                if rule is not None:
                    self.assertEqual(reason, f"change_evidence_not_assertive:{rule}")

    def test_g12_budget_units_are_closed(self):
        for text in ("The updated project budget is 7000 untrue.", "The updated project budget is 7000 reckoned.",
                     "The updated project budget is 7000 guessed."):
            with self.subTest(text=text):
                self.tearDown(); self.setUp()
                old, _ = self.pair(text, "The project budget is 3000 dollars.")
                self.assertNotEqual(self.label(self.recall("What is the project budget?"), old), LIMITED)

    def test_leading_attribution_forms_no_limitation(self):
        old, _ = self.pair("According to a tip, the user moved and now lives in Boston.")
        self.assertNotEqual(self.label(self.recall(), old), LIMITED)

    def test_different_properties_form_no_relation(self):
        old, new = self.pair("The user has moved and now works at Globex.")
        self.assertEqual((self.memory.write_semantics(new) or {}).get("relations", []), [])
        self.assertNotEqual(self.label(self.recall("Where does the user live or work?"), old), LIMITED)

    # C6 11
    def test_cross_scope_source_is_never_admitted(self):
        old = self.write("home:a", DENVER)
        self.memory.close()
        with _open(self.root, scope="project:elsewhere") as other:
            self.write("home:b", BOSTON, memory=other)
        self.memory = _open(self.root)
        recalled = self.recall()
        self.assertEqual(recalled["admitted"], [old])
        self.assertNotEqual(self.label(recalled, old), LIMITED)

    # C6 12
    def test_corrected_source_is_refused(self):
        old = self.write("home:a", DENVER)
        self.write("home:b", "The user likes jazz.")
        corrected = self.memory.correct("memory:home:b", BOSTON, evidence=_qualified(), risk_class="low")
        self.assertTrue(corrected["committed"], corrected)
        recalled = self.recall()
        self.assertNotEqual(self.label(recalled, old), LIMITED)
        self.assertEqual(self.reason(recalled, old), "source_mismatch")

    # C6 16
    def test_corrected_target_is_never_limited(self):
        self.write("home:a", "The user lives in Austin.")
        corrected = self.memory.correct("memory:home:a", DENVER, evidence=_qualified(), risk_class="low")
        self.assertTrue(corrected["committed"], corrected)
        old = corrected["fact_uuid"]
        self.write("home:b", BOSTON)
        recalled = self.recall()
        self.assertNotEqual(self.label(recalled, old), LIMITED)
        self.assertEqual(self.reason(recalled, old), "source_mismatch")

    # C6 13
    def test_poisoning_by_volume(self):
        old = self.write("home:a", DENVER)
        for index, text in enumerate([
            "The user might have moved and now lives in Boston.",
            "The user's sister moved and now lives in Boston.",
            "The user moved and now lives in Boston lol.",
            "The user moved and now lives in Boston, according to a spam message.",
            "The user moved and now lives in Boston?",
        ] * 2):
            self.write(f"home:spam{index}", text)
        recalled = self.recall()
        self.assertNotEqual(self.label(recalled, old), LIMITED)
        good = self.write("home:good", BOSTON)
        recalled = self.recall()
        evidence = self.evidence(recalled, old)
        self.assertEqual(evidence["temporal_applicability"], LIMITED)
        self.assertEqual([item["source_fact_uuid"] for item in evidence["cross_fact_limitation"]], [good])
        self.assertIn(old, recalled["admitted"])

    # C6 14
    def test_write_order_alone_never_limits(self):
        old = self.write("home:a", DENVER)
        self.write("home:b", "The user lives in Boston.")
        recalled = self.recall()
        for ref in recalled["admitted"]:
            self.assertNotEqual(self.label(recalled, ref), LIMITED)
        self.assertNotIn("cross_fact_refusal_reason", self.evidence(recalled, old))

    # C6 15
    def test_declared_clocks_can_only_refuse(self):
        old = self.write("home:a", DENVER, observed_at="2026-01-01")
        self.write("home:b", BOSTON, observed_at="2019-01-01")
        self.assertEqual(self.reason(self.recall(), old), "declared_clock_contradicts_direction")
        self.tearDown(); self.setUp()
        old = self.write("home:a", DENVER, observed_at="2026-01-01")
        self.write("home:b", BOSTON)
        self.assertEqual(self.reason(self.recall(), old), "declared_clock_unconfirmed")
        self.tearDown(); self.setUp()
        old = self.write("home:a", DENVER, observed_at="2019-01-01")
        self.write("home:b", BOSTON, observed_at="2026-01-01")
        self.assertEqual(self.label(self.recall(), old), LIMITED)

    def test_declared_validity_on_the_target_wins(self):
        old = self.write("home:a", DENVER, valid_from="2020-01-01")
        self.write("home:b", BOSTON, valid_from="2026-01-01")
        recalled = self.recall()
        self.assertNotEqual(self.label(recalled, old), LIMITED)


# ------------------------------------------------------------------------------ C2 guards (pure)


def _fact(uuid, text, *, provenance=True, semantics=None, temporal=None, group="g", actor="a", channel="caller_observation", source="actor:a"):
    attributes = {}
    if provenance:
        attributes[cf.WRITE_PROVENANCE_KEY] = {"version": "1.0.0", "actor_id": actor, "tenant": group, "purpose": "p",
                                               "channel": channel, "source_ref": source}
    if semantics is not None:
        attributes[ps.WRITE_SEMANTICS_KEY] = semantics
    if temporal is not None:
        from agentmem_ref.runtime.temporal_intent import DECLARED_TEMPORAL_KEY
        attributes[DECLARED_TEMPORAL_KEY] = temporal
    return SimpleNamespace(uuid=uuid, fact_text=text, attributes=attributes, group_id=group)


def _semantics(**overrides):
    relation = {
        "classification": ps.STATE_CHANGE_CANDIDATE,
        "basis": "single_valued_replacement_marker",
        "other_fact_uuid": "T",
        "proposal": {"proposal_id": "prop:1", "applied": False, "authority_effect": "none"},
    }
    relation.update(overrides.pop("relation", {}))
    value = {
        "proposition": {"entity": "user", "property": "live in", "value": "boston"},
        "markers": {"change": ["moved"]},
        "relations": [relation],
        "proposal_ineligible_reasons": [],
    }
    value.update(overrides)
    return value


EXPLICIT = TemporalIntent(mode="current", posture="explicit", intent_basis="caller_declared")


class GuardTests(unittest.TestCase):
    def evaluate(self, source=None, target=None, *, intent=EXPLICIT, status="open", scope=None, same_scope=True):
        facts = {
            "S": source or _fact("S", "The user moved and now lives in Boston.", semantics=_semantics()),
            "T": target or _fact("T", DENVER),
        }
        scopes = scope or {"S": {"domain_refs": ["d"]}, "T": {"domain_refs": ["d"]}}
        return cf.evaluate(
            ["S", "T"], intent,
            fact_lookup=facts.get,
            proposal_status=lambda proposal: status,
            fact_scope=scopes.get,
            same_scope=lambda a, b: same_scope,
            explicit_current=explicit_current_profile,
        )

    def refusal(self, **kwargs):
        verdict = self.evaluate(**kwargs)
        self.assertEqual(verdict["T"]["accepted"], [])
        return verdict["T"]["refusal"]

    def test_all_guards_pass(self):
        [evidence] = self.evaluate()["T"]["accepted"]
        self.assertEqual(evidence["basis"], cf.CROSS_FACT_BASIS)
        self.assertEqual(evidence["guards"], [f"G{i}" for i in range(1, 14)])
        self.assertEqual(evidence["authority_effect"], "none")

    def test_g1_explicit_current_only(self):
        for intent in (TemporalIntent(mode="current", posture="inferred", confidence="high", intent_basis="query_cue_inference"),
                       TemporalIntent(mode="historical", posture="explicit", intent_basis="caller_declared"),
                       TemporalIntent()):
            self.assertEqual(self.evaluate(intent=intent), {})

    def test_g2_g3_g4(self):
        cases = {
            "relation_not_state_change": {"classification": ps.COEXISTENCE},
            "relation_basis_not_accepted": {"basis": "something_else"},
            "no_open_proposal": {"proposal": {"proposal_id": "p", "applied": True, "authority_effect": "none"}},
        }
        for reason, relation in cases.items():
            source = _fact("S", "The user moved and now lives in Boston.", semantics=_semantics(relation=relation))
            self.assertEqual(self.refusal(source=source), reason)

    def test_g5_status(self):
        for status in ("applied", "stale", "disputed"):
            self.assertEqual(self.refusal(status=status), f"proposal_not_open:{status}")

    def test_g6_hedge_and_self_claims(self):
        for semantics in (_semantics(markers={"change": ["moved"], "hedge": ["might"]}),
                          _semantics(markers={"change": ["moved"], "self_claims": ["current"]}),
                          _semantics(proposal_ineligible_reasons=["hedged"])):
            source = _fact("S", "The user moved and now lives in Boston.", semantics=semantics)
            self.assertEqual(self.refusal(source=source), "hedged_or_untrusted_claim")

    def test_g7_missing_identity(self):
        source = _fact("S", "The user moved and now lives in Boston.", semantics=_semantics(), provenance=False)
        self.assertEqual(self.refusal(source=source), "cross_fact_identity_unavailable")
        self.assertEqual(self.refusal(target=_fact("T", DENVER, provenance=False)), "cross_fact_identity_unavailable")

    def test_g8_g9_g10(self):
        self.assertEqual(self.refusal(target=_fact("T", DENVER, actor="b")), "actor_mismatch")
        self.assertEqual(self.refusal(target=_fact("T", DENVER, source="user:alice")), "source_mismatch")
        self.assertEqual(self.refusal(target=_fact("T", DENVER, channel="caller_correction")), "source_mismatch")
        self.assertEqual(self.refusal(same_scope=False), "scope_mismatch")
        self.assertEqual(self.refusal(scope={"S": {"domain_refs": ["d"], "required_domain_refs": ["x"]},
                                             "T": {"domain_refs": ["d"]}}), "scope_mismatch")

    def test_g11_mutual_limitation(self):
        source = _fact("S", "The user moved and now lives in Boston.", semantics=_semantics())
        target_semantics = _semantics(relation={"other_fact_uuid": "S", "proposal": {"proposal_id": "prop:2", "applied": False, "authority_effect": "none"}},
                                      proposition={"entity": "user", "property": "live in", "value": "denver"})
        target = _fact("T", "The user moved and now lives in Denver.", semantics=target_semantics)
        verdict = self.evaluate(source=source, target=target)
        self.assertEqual(verdict["T"]["refusal"], "contradictory_cross_fact_evidence")
        self.assertEqual(verdict["S"]["refusal"], "contradictory_cross_fact_evidence")
        self.assertEqual(verdict["T"]["accepted"], [])
        self.assertEqual(verdict["S"]["accepted"], [])

    def test_g12_is_versioned(self):
        source = _fact("S", "The user's sister moved and now lives in Boston.", semantics=_semantics())
        self.assertEqual(self.refusal(source=source), "change_evidence_not_assertive:2")
        self.assertEqual(cf.ASSERTION_FILTER_VERSION, "6.0.0")

    def test_g13_clocks(self):
        older = {"observed_at": "2026-01-01T00:00:00Z"}
        newer = {"observed_at": "2019-01-01T00:00:00Z"}
        source = _fact("S", "The user moved and now lives in Boston.", semantics=_semantics(), temporal=newer)
        self.assertEqual(self.refusal(source=source, target=_fact("T", DENVER, temporal=older)),
                         "declared_clock_contradicts_direction")
        self.assertEqual(self.refusal(target=_fact("T", DENVER, temporal=older)), "declared_clock_unconfirmed")

    def test_source_must_be_admitted(self):
        facts = {"S": _fact("S", "The user moved and now lives in Boston.", semantics=_semantics()), "T": _fact("T", DENVER)}
        verdict = cf.evaluate(["T"], EXPLICIT, fact_lookup=facts.get, proposal_status=lambda p: "open",
                              fact_scope=lambda ref: {"domain_refs": ["d"]}, same_scope=lambda a, b: True,
                              explicit_current=explicit_current_profile)
        self.assertEqual(verdict, {})

    def test_evaluation_is_pure(self):
        source = _fact("S", "The user moved and now lives in Boston.", semantics=_semantics())
        target = _fact("T", DENVER)
        before = copy.deepcopy((source.attributes, target.attributes))
        self.evaluate(source=source, target=target)
        self.assertEqual((source.attributes, target.attributes), before)


if __name__ == "__main__":
    unittest.main()
