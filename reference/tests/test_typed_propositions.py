"""#732 remediation: typed write-time propositions (docs/plan-732-remediation.md R1-R4).

Caller-declared propositions (R1), the optional extractor with its recorded-fixture stub (R2),
classifier 1.1.0 (R3) and the typed guard branch of assertion filter 6.1.0 under ranking policy
3.4.0 (R4). The control tests are the plan's R6 caller-declared list and the T2/U1 link
controls; the extractor never makes a network call here.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.api import contract  # noqa: E402
from agentmem_ref.memory import procedural_memory as pm  # noqa: E402
from agentmem_ref.runtime import cross_fact_currentness as cf  # noqa: E402
from agentmem_ref.runtime import proposition_extraction as px  # noqa: E402
from agentmem_ref.runtime import proposition_semantics as ps  # noqa: E402
from agentmem_ref.runtime import typed_proposition as tp  # noqa: E402
from agentmem_ref.runtime.temporal_intent import TemporalIntent  # noqa: E402
from agentmem_ref.runtime.temporal_order_constraints import POLICY_VERSION, explicit_current_profile  # noqa: E402

DATA = ROOT / "reference" / "testdata" / "typed_proposition"
STUB = json.loads((DATA / "stub_recordings.json").read_text(encoding="utf-8"))
GOLDEN = json.loads((DATA / "extractor_off_write_semantics_v5.json").read_text(encoding="utf-8"))["writes"]
TEXT, PROP = STUB["texts"], STUB["propositions"]
TENANT, SCOPE, ACTOR = "tenant:typed", "project:typed", "agent:typed"
NOW = "2026-09-27T12:00:00Z"
CURRENT = {"mode": "current"}
LIMITED = cf.CROSS_FACT_LABEL


def _recordings() -> dict:
    out = {}
    for name, recording in STUB["recordings"].items():
        entry = {"output": {"proposition": PROP[recording["proposition"]],
                            "updates_fact_uuid": recording.get("updates_fact_uuid")}}
        if "link_to" in recording:
            entry["link_to_candidate_text"] = TEXT[recording["link_to"]]
        out[TEXT[name]] = entry
    return out


def _stub(recordings: dict | None = None, egress_policy=lambda text: True) -> px.RecordedFixtureExtractor:
    return px.RecordedFixtureExtractor(_recordings() if recordings is None else recordings, egress_policy=egress_policy)


def _with_flag(name: str, flag: str) -> dict:
    return {**PROP[name], "flags": {flag: True}}


def _qualified():
    skill = pm.SkillArtifact(
        skill_id="skill:typed-review", version=1, purpose="review a governed change to retained test memory",
        scope=SCOPE, isolation_domain_refs=(TENANT, SCOPE), required_isolation_domain_refs=(TENANT, SCOPE),
        procedure_markdown="# verify\nConfirm the change against the source conversation.",
        provenance_refs=("evidence:typed-review",),
    )
    return pm.evidence_for(skill)


class _Case(unittest.TestCase):
    extractor = None

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.root = self._temp.name
        self.memory = self.open()

    def tearDown(self) -> None:
        self.memory.close()
        self._temp.cleanup()

    def open(self, *, actor_id: str = ACTOR, scope: str = SCOPE, extractor=None) -> AgentMemory:
        return AgentMemory.open(self.root, tenant=TENANT, actor_id=actor_id, scope=scope, purpose="typed tests",
                                proposition_extractor=extractor)

    def reopen(self, **kwargs) -> AgentMemory:
        self.memory.close()
        self.memory = self.open(**kwargs)
        return self.memory

    def write(self, target: str, name: str, memory: AgentMemory | None = None, **kwargs) -> str:
        result = (memory or self.memory).remember(f"memory:{target}", TEXT[name], **kwargs)
        self.assertTrue(result["committed"], result)
        return result["fact_uuid"]

    def semantics(self, fact_uuid: str) -> dict:
        return self.memory.write_semantics(fact_uuid) or {}

    def stored(self, fact_uuid: str) -> dict:
        return self.memory.runtime.adapter._substrate.get_fact(fact_uuid).attributes[ps.WRITE_SEMANTICS_KEY]

    def recall(self, query: str = "room_query") -> dict:
        return self.memory.recall(TEXT[query], temporal_intent=CURRENT, reference_time=NOW)

    def evidence(self, recalled: dict, fact_uuid: str) -> dict:
        return recalled["admissions"][fact_uuid].get("ranking_evidence") or {}

    def assert_engaged(self, old: str, new: str, query: str = "room_query") -> None:
        recalled = self.recall(query)
        evidence = self.evidence(recalled, old)
        self.assertEqual(evidence["temporal_applicability"], LIMITED)
        [item] = evidence["cross_fact_limitation"]
        self.assertEqual(item["source_fact_uuid"], new)
        self.assertEqual(item["authority_effect"], "none")
        self.assertEqual(item["assertion_filter_version"], "6.1.0")
        self.assertLess(recalled["admitted"].index(new), recalled["admitted"].index(old))

    def assert_not_engaged(self, old: str, query: str = "room_query", reason: str | None = None) -> None:
        recalled = self.recall(query)
        self.assertIn(old, recalled["admitted"])
        evidence = self.evidence(recalled, old)
        self.assertNotEqual(evidence.get("temporal_applicability"), LIMITED)
        self.assertNotIn("cross_fact_limitation", evidence)
        if reason is not None:
            self.assertEqual(evidence.get("cross_fact_refusal_reason"), reason)

    def declared_pair(self, new_proposition: dict | None = None, **kwargs) -> tuple[str, str]:
        old = self.write("a", "room_old", proposition=PROP["room_old"])
        new = self.write("b", "room_new", proposition=new_proposition or PROP["room_new"], **kwargs)
        return old, new


# ------------------------------------------------------------------------------- versions and R1


class VersionTests(unittest.TestCase):
    def test_versions(self):
        self.assertEqual(contract.CONTRACT_VERSION, "1.6.0")
        self.assertEqual(ps.CLASSIFIER_VERSION, "1.0.0")
        self.assertEqual(ps.TYPED_CLASSIFIER_VERSION, "1.1.0")
        self.assertEqual(cf.ASSERTION_FILTER_VERSION, "6.1.0")
        self.assertEqual(POLICY_VERSION, "3.4.0")


class DeclarationValidationTests(_Case):
    def test_typed_slot_normalization(self):
        self.assertEqual(tp.typed_slot("  The   Kestrel Standup. ", "Meeting  ROOM!"), "typed:the kestrel standup|meeting room")
        self.assertEqual(tp.norm("\"Aurora\""), "aurora")

    def test_closed_schema(self):
        base = PROP["room_new"]
        bad = [
            "not an object",
            {k: v for k, v in base.items() if k != "subject"},
            {**base, "extra": 1},
            {**base, "assertion": "maybe"},
            {**base, "cardinality": "hierarchical"},
            {**base, "subject": ""},
            {**base, "subject": "   "},
            {**base, "value": "x" * 201},
            {**base, "value": "line\nbreak"},
            {**base, "attribute": "..."},
            {**base, "replaces_value": 3},
            {**base, "flags": {"sarcastic": True}},
            {**base, "flags": {"hedged": "yes"}},
            {**base, "flags": ["hedged"]},
        ]
        for record in bad:
            with self.assertRaises(ValueError, msg=record):
                tp.validate(record)
            with self.assertRaises(ValueError, msg=record):
                self.memory.remember("memory:x", TEXT["room_new"], proposition=record)
        self.assertIsNone(self.memory.runtime.adapter.current_fact_uuid("memory:x"))

    def test_flags_default_false_and_record_is_persisted(self):
        old, new = self.declared_pair()
        record = self.semantics(new)["typed_proposition"]
        self.assertEqual(record["basis"], tp.CALLER_DECLARED)
        self.assertEqual(record["slot"], "typed:kestrel standup|meeting room")
        self.assertEqual(record["flags"], dict.fromkeys(tp.FLAGS, False))
        self.assertNotIn("updates_fact_uuid", record)
        self.assertEqual(self.stored(new)["version"], "1.1.0/1.1.0")
        self.assertEqual(self.semantics(new)["classifier"], {"version": "1.1.0"})

    def test_typed_declaration_grants_nothing(self):
        old, new = self.declared_pair()
        adapter = self.memory.runtime.adapter
        self.assertEqual(adapter.current_fact_uuid("memory:a"), old)
        [proposal] = self.memory.semantic_proposals(status="open")
        self.assertFalse(proposal["applied"])
        self.assertEqual(proposal["authority_effect"], "none")

    def test_pre_existing_facts_are_unaffected(self):
        old = self.write("a", "room_old")
        before = json.dumps(self.stored(old))
        self.write("b", "room_new", proposition=PROP["room_new"])
        self.assertEqual(json.dumps(self.stored(old)), before)


# ------------------------------------------------------------------------------- R3 classification


class ClassificationTests(_Case):
    def relation(self, fact_uuid: str) -> dict:
        [relation] = self.semantics(fact_uuid)["relations"]
        return relation

    def test_typed_slot_change_is_a_proposal(self):
        old, new = self.declared_pair()
        relation = self.relation(new)
        self.assertEqual((relation["classification"], relation["basis"]), (ps.STATE_CHANGE_CANDIDATE, tp.TYPED_SLOT))
        self.assertEqual(relation["proposal"]["target_fact_uuid"], old)
        self.assertEqual(relation["proposal"]["proposal_id"],
                         ps.proposal_id(new, old, classifier_version=ps.TYPED_CLASSIFIER_VERSION))

    def test_same_value_coexistence_and_state(self):
        old = self.write("a", "room_old", proposition=PROP["room_old"])
        cases = {
            "same": ({**PROP["room_new"], "value": "aurora."}, ps.SAME_VALUE, tp.TYPED_SLOT),
            "multi": ({**PROP["room_new"], "cardinality": "multi"}, ps.COEXISTENCE, tp.TYPED_SLOT),
            "state": ({**PROP["room_new"], "assertion": "state"}, ps.UNRESOLVED, "typed_slot_without_change_assertion"),
        }
        for index, (name, (record, kind, basis)) in enumerate(cases.items()):
            new = self.write(f"b{index}", "room_new", proposition=record)
            relation = next(r for r in self.semantics(new)["relations"] if r["other_fact_uuid"] == old)
            self.assertEqual((relation["classification"], relation["basis"]), (kind, basis), name)

    def test_each_matching_fact_gets_its_own_relation(self):
        first = self.write("a1", "room_old", proposition=PROP["room_old"])
        second = self.write("a2", "room_old", proposition=PROP["room_old"])
        new = self.write("b", "room_new", proposition=PROP["room_new"])
        relations = self.semantics(new)["relations"]
        self.assertEqual(sorted(r["other_fact_uuid"] for r in relations), sorted([first, second]))
        self.assertTrue(all(r["classification"] == ps.STATE_CHANGE_CANDIDATE for r in relations))

    def test_typed_eligibility_drops_parser_reasons_only(self):
        old, new = self.declared_pair()
        self.assertEqual(self.semantics(new)["typed_ineligible_reasons"], [])
        hedged = self.write("c", "room_hedged", proposition=PROP["room_new"])
        relation = next(r for r in self.semantics(hedged)["relations"] if r["other_fact_uuid"] == old)
        self.assertEqual(self.semantics(hedged)["typed_ineligible_reasons"], ["hedged"])
        self.assertEqual((relation["classification"], relation["basis"]),
                         (ps.UNRESOLVED, "change_evidence_not_proposable:hedged"))
        self.assertEqual(tp.typed_ineligible_reasons(
            {"proposal_ineligible_reasons": ["proposition_unknown", "proposition_ambiguous", "untrusted_self_claim"]},
            {"flags": {"hedged": True}}), ["hedged", "untrusted_self_claim"])

    def test_untyped_facts_are_not_typed_slot_matches(self):
        self.write("a", "room_old")
        new = self.write("b", "room_new", proposition=PROP["room_new"])
        self.assertEqual(self.semantics(new).get("relations", []), [])

    def test_link_confirmation_rules(self):
        typed = tp.typed_record(tp.validate(PROP["room_new"]), "extracted:x@1", updates_fact_uuid="u")
        untyped = {"proposition": {"status": ps.KNOWN, "value": "42"}}
        cases = [
            ({**typed, "replaces_value": "Aurora"}, TEXT["room_old"], None, True),
            ({**typed, "replaces_value": "Polaris"}, TEXT["room_old"], None, False),
            ({**typed, "replaces_value": "Borealis"}, TEXT["room_new"], None, False),
            ({**typed, "replaces_value": "A"}, "room A", None, False),
            ({**typed, "replaces_value": "off"}, TEXT["flag_old"], None, False),
            ({**typed, "replaces_value": "17"}, "room 17", None, False),
            ({**typed, "replaces_value": "42"}, "number 42", untyped, True),
            ({**typed, "replaces_value": None}, TEXT["room_old"], None, False),
            ({**typed, "replaces_value": "Aurora"}, TEXT["room_old"],
             {"typed_proposition": {"slot": "typed:other|thing", "value": "Aurora"}}, False),
            ({**typed, "replaces_value": None}, TEXT["room_old"],
             {"typed_proposition": {"slot": typed["slot"], "value": "Aurora"}}, True),
        ]
        for record, text, other, expected in cases:
            self.assertEqual(tp.link_confirmed(record, text, other), expected, (record["replaces_value"], text, other))


# ------------------------------------------------------------------------------- R4 control tests (caller-declared)


class CallerDeclaredControlTests(_Case):
    def test_confirmed_change_engages(self):
        old, new = self.declared_pair()
        self.assert_engaged(old, new)
        self.assertEqual(self.memory.runtime.adapter.current_fact_uuid("memory:a"), old)

    def test_each_flag_refuses(self):
        for flag in tp.FLAGS:
            with self.subTest(flag=flag):
                self.memory.close()
                self._temp.cleanup()
                self._temp = tempfile.TemporaryDirectory()
                self.root = self._temp.name
                self.memory = self.open()
                old, new = self.declared_pair(_with_flag("room_new", flag))
                [relation] = self.semantics(new)["relations"]
                self.assertEqual(relation["classification"], ps.UNRESOLVED)
                self.assertNotIn("proposal", relation)
                self.assert_not_engaged(old, reason="relation_not_state_change")

    def test_g12_typed_flags_refuse_without_text_recheck(self):
        for flag in tp.FLAGS:
            verdict = _evaluate(_typed_source(flags={flag: True}))
            self.assertEqual(verdict["T"]["refusal"], f"typed_assertion_not_assertive:{flag}")
        # The text is never re-checked: a caller-declared relation passes on its typed evidence.
        [accepted] = _evaluate(_typed_source(text="Free text that the interpreter could never parse?"))["T"]["accepted"]
        self.assertEqual(accepted["relation_basis"], tp.TYPED_SLOT)

    def test_g3_requires_a_typed_basis(self):
        for basis in (None, "interpreted", "extracted:", "caller"):
            self.assertEqual(_evaluate(_typed_source(basis=basis))["T"]["refusal"], "relation_basis_not_accepted")
        self.assertEqual(_evaluate(_typed_source(basis="extracted:stub@1"))["T"]["refusal"], None)

    def test_g6_reads_typed_ineligible_reasons(self):
        verdict = _evaluate(_typed_source(reasons=["untrusted_self_claim"]))
        self.assertEqual(verdict["T"]["refusal"], "hedged_or_untrusted_claim")
        # Interpreted-only reasons do not gate a typed relation; typed reasons already fold them in.
        self.assertEqual(_evaluate(_typed_source(extra={"proposal_ineligible_reasons": ["x"]}))["T"]["refusal"], None)

    def test_actor_mismatch_refuses(self):
        old = self.write("a", "room_old", proposition=PROP["room_old"])
        other = self.reopen(actor_id="agent:other")
        self.write("b", "room_new", memory=other, proposition=PROP["room_new"])
        self.reopen()
        self.assert_not_engaged(old, reason="actor_mismatch")

    def test_source_mismatch_refuses(self):
        old = self.write("a", "room_old", proposition=PROP["room_old"], source_ref="user:alice")
        self.write("b", "room_new", proposition=PROP["room_new"], source_ref="tool:search")
        self.assert_not_engaged(old, reason="source_mismatch")

    def test_scope_mismatch_refuses(self):
        old = self.write("a", "room_old", proposition=PROP["room_old"])
        other = self.reopen(scope="project:elsewhere")
        new = self.write("b", "room_new", memory=other, proposition=PROP["room_new"])
        self.assertEqual(other.write_semantics(new).get("relations", []), [])
        self.reopen()
        self.assert_not_engaged(old)
        task_scoped = self.write("c", "room_new", proposition=PROP["room_new"], overrides={"task_ref": "task:other"})
        self.assertEqual(self.semantics(task_scoped).get("relations", []), [])

    def test_dispute_refuses(self):
        old, new = self.declared_pair()
        disputed = self.memory.dispute("memory:b", fact_uuid=new, evidence=_qualified(), risk_class="low")
        self.assertTrue(disputed["committed"], disputed)
        self.assert_not_engaged(old)
        verdict = self.memory.runtime.adapter.cross_fact_applicability(
            [old, new], TemporalIntent(mode="current", posture="explicit", intent_basis="caller_declared"))
        self.assertTrue(verdict[old]["refusal"].startswith("proposal_not_open:"), verdict)

    def test_forget_refuses(self):
        old, new = self.declared_pair()
        self.assertTrue(self.memory.forget("memory:b")["committed"])
        self.assert_not_engaged(old)

    def test_declaration_outranks_the_extractor(self):
        stub = _stub()
        self.reopen(extractor=stub)
        old, new = self.declared_pair()
        self.assertEqual(stub.calls, [])
        self.assertNotIn("extraction", self.semantics(new))
        self.assertEqual(self.semantics(new)["typed_proposition"]["basis"], tp.CALLER_DECLARED)


# ------------------------------------------------------------------------------- R2 extractor


class ExtractorTests(_Case):
    def test_constructor_requires_an_egress_policy(self):
        with self.assertRaises(TypeError):
            px.RecordedFixtureExtractor({})
        with self.assertRaises(TypeError):
            px.RecordedFixtureExtractor({}, egress_policy=None)
        with self.assertRaises(TypeError):
            px.AnthropicMessagesExtractor("test-model")
        with self.assertRaises(ValueError):
            AgentMemory.open(self.root, tenant=TENANT, actor_id=ACTOR, scope=SCOPE, proposition_extractor=object())

    def test_stub_change_engages_through_an_untyped_link(self):
        old = self.write("a", "room_old")
        stub = _stub()
        self.reopen(extractor=stub)
        new = self.write("b", "room_new")
        semantics = self.semantics(new)
        record = semantics["typed_proposition"]
        self.assertEqual(record["basis"], "extracted:recorded-fixture@1.0.0")
        self.assertEqual(record["updates_fact_uuid"], old)
        [relation] = semantics["relations"]
        self.assertEqual((relation["classification"], relation["basis"]), (ps.STATE_CHANGE_CANDIDATE, tp.TYPED_LINK))
        extraction = semantics["extraction"]
        self.assertEqual(extraction["status"], "extracted")
        self.assertEqual(extraction["candidate_uuids"], [old])
        self.assertEqual(extraction["prompt_sha256"], px.PROMPT_SHA256)
        self.assertTrue(extraction["request_id"].startswith("fixture:"))
        self.assertEqual(json.loads(extraction["raw_output"])["updates_fact_uuid"], old)
        self.assertEqual(stub.calls[0]["candidates"], [{"fact_uuid": old, "text": TEXT["room_old"]}])
        self.assert_engaged(old, new)

    def test_different_slot_typed_link_refuses(self):
        dentist = self.write("dentist", "dentist", proposition=PROP["dentist"])
        self.reopen(extractor=_stub())
        new = self.write("home", "home_move")
        self.assertEqual(self.semantics(new)["typed_proposition"]["updates_fact_uuid"], dentist)
        [relation] = self.semantics(new)["relations"]
        self.assertEqual((relation["classification"], relation["basis"]), (ps.UNRESOLVED, tp.TYPED_LINK_UNCONFIRMED))
        self.assertNotIn("proposal", relation)
        self.assert_not_engaged(dentist, query="home_query", reason="relation_not_state_change")

    def test_trivial_replaces_value_refuses(self):
        old = self.write("flag", "flag_old")
        self.reopen(extractor=_stub())
        new = self.write("flag2", "flag_new")
        self.assertEqual(self.semantics(new)["typed_proposition"]["updates_fact_uuid"], old)
        [relation] = self.semantics(new)["relations"]
        self.assertEqual((relation["classification"], relation["basis"]), (ps.UNRESOLVED, tp.TYPED_LINK_UNCONFIRMED))
        self.assert_not_engaged(old, query="flag_query", reason="relation_not_state_change")

    def test_unconfirmed_link_refuses(self):
        old = self.write("a", "room_old")
        self.reopen(extractor=_stub())
        new = self.write("b", "unlinked_new")
        [relation] = self.semantics(new)["relations"]
        self.assertEqual((relation["classification"], relation["basis"], relation["other_fact_uuid"]),
                         (ps.UNRESOLVED, tp.TYPED_LINK_UNCONFIRMED, "ref-9999"))
        self.assert_not_engaged(old)

    def test_candidates_are_filtered_and_bounded(self):
        for index in range(10):
            self.write(f"a{index}", "room_old")
        disputed_target = self.write("z", "room_old")
        self.memory.dispute("memory:z", fact_uuid=disputed_target, evidence=_qualified(), risk_class="low")
        other = self.reopen(scope="project:elsewhere")
        foreign = self.write("y", "room_old", memory=other)
        stub = _stub()
        self.reopen(extractor=stub)
        new = self.write("b", "room_new")
        sent = [item["fact_uuid"] for item in stub.calls[0]["candidates"]]
        self.assertLessEqual(len(sent), px.MAX_CANDIDATES)
        self.assertEqual(len(sent), px.MAX_CANDIDATES)
        self.assertNotIn(disputed_target, sent)
        self.assertNotIn(foreign, sent)
        self.assertEqual(self.semantics(new)["extraction"]["candidate_uuids"], sent)

    def test_egress_policy_governs_what_leaves(self):
        old = self.write("a", "room_old")
        refuse_candidates = _stub(egress_policy=lambda text: text != TEXT["room_old"])
        self.reopen(extractor=refuse_candidates)
        new = self.write("b", "room_new")
        self.assertEqual(refuse_candidates.calls[0]["candidates"], [])
        self.assertEqual(self.semantics(new)["extraction"]["candidate_uuids"], [])
        self.assertIsNone(self.semantics(new)["typed_proposition"]["updates_fact_uuid"])
        self.assertEqual(self.semantics(new).get("relations", []), [])
        refuse_new = _stub(egress_policy=lambda text: text != TEXT["room_new"])
        self.reopen(extractor=refuse_new)
        refused = self.write("c", "room_new")
        self.assertEqual(refuse_new.calls, [])
        self.assert_failed(refused, px.EGRESS_REFUSED)
        failing_policy = _stub(egress_policy=lambda text: 1 / 0)
        self.reopen(extractor=failing_policy)
        self.assert_failed(self.write("d", "room_new"), px.EGRESS_REFUSED)
        self.assertEqual(failing_policy.calls, [])
        self.assertIsNotNone(old)

    def assert_failed(self, fact_uuid: str, reason: str) -> dict:
        semantics = self.semantics(fact_uuid)
        self.assertIn("typed_proposition", semantics)
        self.assertIsNone(semantics["typed_proposition"])
        self.assertEqual(semantics["extraction"]["status"], "failed")
        self.assertTrue(semantics["extraction"]["reason"].startswith(reason), semantics["extraction"])
        self.assertEqual(semantics["classifier"], {"version": ps.CLASSIFIER_VERSION})
        self.assertNotIn("typed_ineligible_reasons", semantics)
        return semantics

    def test_failures_take_the_interpreted_path_and_commit(self):
        reference = AgentMemory.open(Path(self.root) / "reference", tenant=TENANT, actor_id=ACTOR, scope=SCOPE,
                                     purpose="typed tests")
        try:
            reference.remember("memory:a", TEXT["room_old"])
            reference_new = reference.remember("memory:b", TEXT["room_new"])["fact_uuid"]
            expected = reference.write_semantics(reference_new)
        finally:
            reference.close()
        cases = {
            "error": ({"error": "provider unavailable"}, px.EXTRACTOR_ERROR),
            "invalid": ({"output": {"proposition": {"subject": "x"}}}, px.EXTRACTOR_OUTPUT_INVALID),
            "unparseable": ({"raw_output": "not json"}, px.EXTRACTOR_OUTPUT_INVALID),
            "declined": ({"output": {"proposition": None}}, px.EXTRACTOR_DECLINED),
            "timeout": ({"delay_seconds": 1.0, "output": {"proposition": PROP["room_new"]}}, px.EXTRACTOR_TIMEOUT),
        }
        for index, (name, (recording, reason)) in enumerate(cases.items()):
            with self.subTest(name), mock.patch.object(px, "EXTRACTION_TIMEOUT_SECONDS", 0.05):
                self.memory.close()
                self._temp.cleanup()
                self._temp = tempfile.TemporaryDirectory()
                self.root = self._temp.name
                self.memory = self.open()
                self.write("a", "room_old")
                self.reopen(extractor=_stub({TEXT["room_new"]: recording}))
                new = self.write("b", "room_new")
                semantics = self.assert_failed(new, reason)
                strip = lambda value: {k: v for k, v in value.items() if k not in ("typed_proposition", "extraction")}
                self.assertEqual(json.dumps(strip(semantics)), json.dumps(expected), name)
        self.assertEqual(px.EXTRACTION_TIMEOUT_SECONDS, 20.0)

    def test_recovery_and_reads_never_call_the_extractor(self):
        old = self.write("a", "room_old")
        stub = _stub()
        self.reopen(extractor=stub)
        new = self.write("b", "room_new")
        self.assertEqual(len(stub.calls), 1)
        before = json.dumps(self.stored(new))

        class Exploding:
            extractor_id, extractor_version = "exploding", "1"
            egress_policy = staticmethod(lambda text: True)
            calls = 0

            def extract(self, new_text, candidates):
                type(self).calls += 1
                raise AssertionError("an extractor was called outside a new write")

        exploding = Exploding()
        self.reopen(extractor=exploding)
        self.assertEqual(json.dumps(self.stored(new)), before)
        self.semantics(new)
        self.memory.semantic_proposals()
        self.assert_engaged(old, new)
        self.memory.runtime.adapter._semantic_slot_index = None
        self.memory.runtime.adapter._semantic_index()
        self.assertEqual(Exploding.calls, 0)
        self.assertEqual(len(stub.calls), 1)


class AnthropicProviderTests(unittest.TestCase):
    def setUp(self):
        self.extractor = px.AnthropicMessagesExtractor("test-model", egress_policy=lambda text: True)

    def test_request_is_frozen_and_deterministic(self):
        body = self.extractor.request_body(TEXT["room_new"], [{"fact_uuid": "f1", "text": TEXT["room_old"]}])
        self.assertEqual(body["model"], "test-model")
        self.assertEqual(body["temperature"], 0.0)
        self.assertEqual(body["system"], px.FROZEN_PROMPT)
        self.assertEqual(body["output_config"]["format"]["schema"], px.FROZEN_OUTPUT_SCHEMA)
        self.assertIn("test-model", self.extractor.extractor_version)
        self.assertNotIn("temperature", px.AnthropicMessagesExtractor(
            "test-model", egress_policy=lambda text: True, temperature=None).request_body("x", []))

    def test_response_parsing(self):
        answer = json.dumps({"proposition": PROP["room_new"], "updates_fact_uuid": "f1"})
        message = {"stop_reason": "end_turn", "content": [{"type": "text", "text": answer}]}
        with mock.patch.object(self.extractor, "_post", return_value=(message, "req_1")):
            result = self.extractor.extract(TEXT["room_new"], [])
        self.assertEqual((result.updates_fact_uuid, result.request_id, result.raw_output), ("f1", "req_1", answer))
        for bad in ({"stop_reason": "max_tokens", "content": [{"type": "text", "text": answer}]},
                    {"stop_reason": "end_turn", "content": [{"type": "text", "text": "{"}]},
                    {"stop_reason": "end_turn", "content": [{"type": "text", "text": "{\"x\": 1}"}]}):
            with mock.patch.object(self.extractor, "_post", return_value=(bad, "req_2")):
                with self.assertRaises(px.ExtractionOutputError):
                    self.extractor.extract(TEXT["room_new"], [])

    def test_missing_credential_is_a_typed_failure_without_network(self):
        with mock.patch.dict("os.environ", {}, clear=True), \
                mock.patch("urllib.request.urlopen", side_effect=AssertionError("network")):
            outcome = px.extract_for_write(self.extractor, TEXT["room_new"], [])
        self.assertIsNone(outcome["typed_proposition"])
        self.assertEqual(outcome["extraction"]["reason"], f"{px.EXTRACTOR_ERROR}:RuntimeError")


# ------------------------------------------------------------------------------- byte identity and S6


class ExtractorOffByteIdentityTests(unittest.TestCase):
    def test_write_semantics_bytes_equal_v5(self):
        with tempfile.TemporaryDirectory() as root:
            memory = AgentMemory.open(root, tenant="tenant:golden", actor_id="agent:golden", scope="project:golden",
                                      purpose="golden")
            try:
                for item in GOLDEN:
                    result = memory.remember(f"memory:{item['target']}", item["text"], observed_at=item["observed_at"])
                    self.assertEqual(result["fact_uuid"], item["fact_uuid"])
                    fact = memory.runtime.adapter._substrate.get_fact(result["fact_uuid"])
                    self.assertEqual(json.dumps(fact.attributes[ps.WRITE_SEMANTICS_KEY]), item["stored"], item["text"])
                    self.assertEqual(json.dumps(memory.write_semantics(result["fact_uuid"])), item["expanded"])
            finally:
                memory.close()
        self.assertTrue(any("proposal_id" in item["stored"] for item in GOLDEN))


class PromptSimilarityTests(unittest.TestCase):
    def test_s6_similarity_check_passes(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_extractor_prompt_similarity.py")],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["failures"], [])
        self.assertLess(report["max_similarity"], 0.5)
        self.assertGreater(report["checked_texts"], 0)

    def test_prompt_contract_is_frozen(self):
        self.assertEqual(px.PROMPT_SHA256, px.hashlib.sha256(px.FROZEN_PROMPT.encode("utf-8")).hexdigest())
        properties = px.FROZEN_OUTPUT_SCHEMA["properties"]["proposition"]["anyOf"][1]["properties"]
        self.assertEqual(set(properties), set(tp.REQUIRED_FIELDS + tp.OPTIONAL_FIELDS))
        self.assertEqual(set(properties["flags"]["properties"]), set(tp.FLAGS))


# ------------------------------------------------------------------------------- guard fixtures


def _typed_source(*, flags=None, basis="caller_declared", reasons=(), text="Typed source text.", extra=None):
    record = {**tp.typed_record(tp.validate(PROP["room_new"]), "caller_declared")}
    record["flags"] = {**record["flags"], **(flags or {})}
    if basis is None:
        record.pop("basis")
    else:
        record["basis"] = basis
    semantics = {
        "typed_proposition": record,
        "typed_ineligible_reasons": list(reasons),
        "relations": [{"classification": ps.STATE_CHANGE_CANDIDATE, "basis": tp.TYPED_SLOT, "other_fact_uuid": "T",
                       "other_memory_ref": "memory:t", "slot": record["slot"],
                       "proposal": {"proposal_id": "prop:typed", "applied": False, "authority_effect": "none"}}],
        **(extra or {}),
    }
    return _fact("S", text, semantics)


def _fact(uuid: str, text: str, semantics: dict | None = None):
    attributes = {cf.WRITE_PROVENANCE_KEY: {"version": "1.0.0", "actor_id": "a", "tenant": "t", "purpose": "p",
                                            "channel": "caller_observation", "source_ref": "actor:a"}}
    if semantics is not None:
        attributes[ps.WRITE_SEMANTICS_KEY] = semantics
    return SimpleNamespace(uuid=uuid, fact_text=text, group_id="t", attributes=attributes)


def _evaluate(source) -> dict:
    facts = {"S": source, "T": _fact("T", TEXT["room_old"])}
    return cf.evaluate(
        ["S", "T"], TemporalIntent(mode="current", posture="explicit", intent_basis="caller_declared"),
        fact_lookup=facts.get, proposal_status=lambda proposal: "open",
        fact_scope=lambda ref: {"domain_refs": ["d"]}, same_scope=lambda a, b: True,
        explicit_current=explicit_current_profile,
    )


if __name__ == "__main__":
    unittest.main()
