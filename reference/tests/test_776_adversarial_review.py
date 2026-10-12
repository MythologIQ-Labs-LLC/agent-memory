"""validation(#776): independent adversarial review of logical-memory deletion admission.

Authored by the reviewer against candidate c34a340 BEFORE any repair. Each test
states an invariant; a failure is a finding against that SHA, not a test to relax.
All writes, corrections and deletions use the governed composition runtime or the
public ``AgentMemory`` facade -- never private substrate mutation -- except the
scale test, which only reads admission with synthetic tombstone records.
"""
from __future__ import annotations

import json
import tempfile
import time
import unittest
from dataclasses import replace
from pathlib import Path

from agentmem_ref import AgentMemory, policy
from agentmem_ref.runtime.configured_restart import ConfigBoundRestartRuntime
from agentmem_ref.runtime_composition import ConfiguredCompositionRuntime
from agentmem_ref.vector_retrieval import (
    SEMANTIC_VECTOR_ROUTE,
    NativeVectorCandidateRetriever,
    VectorRepresentationSpec,
)
from agentmem_ref.verification import TRANSITION_VERIFIER, VerifierRegistry
from tests.qualified_fixtures import corpus_for, rule
from tests.test_644_combined_independent import _evidence, _prop
from tests.test_runtime_composition import PROJECT, TENANT, _context, _plan, _proposal
from tests.test_typed_propositions import PROP, TEXT

S, E = "state_change", "error_correction"
KILN = [("The kiln firing schedule uses cone 6 glaze.", None),
        ("The kiln firing schedule uses cone 10 glaze.", S)]
KILN_QUERY = "What glaze did the kiln firing schedule use?"


class _KilnVectors:
    """Credential-free deterministic fixture: every kiln sentence is near the query."""

    spec = VectorRepresentationSpec(
        representation_ref="agent-memory:test-776-review",
        representation_version="1.0.0",
        config_digest="sha256:test-776-review-v1",
        dimensions=2,
        deterministic_rebuild=True,
    )

    def embed(self, text: str) -> tuple[float, ...]:
        return (1.0, 0.0) if "kiln" in text.lower() else (0.0, 1.0)


class _Store:
    """Governed composition store whose host adjudicates exactly the declared transitions."""

    def __init__(self, case, *, vector=False):
        self.case = case
        tmp = tempfile.TemporaryDirectory()
        case.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self._verifiers = []
        self.registry = VerifierRegistry()
        self.registry.register(TRANSITION_VERIFIER, lambda item: any(v(item) for v in self._verifiers))
        self.vector = NativeVectorCandidateRetriever(_KilnVectors()) if vector else None
        self.runtime = ConfiguredCompositionRuntime.create(
            self.root, tenant=TENANT, plan=_plan(), verifier_registry=self.registry,
            vector_retriever=self.vector)
        self.ids: dict[str, list[str]] = {}

    @property
    def adapter(self):
        return self.runtime.adapter

    def proposal(self, memory, n, op="promotion", **kw):
        base = replace(_proposal(f"proposal:776r:{memory}:{n}", operation=op),
                       target_reference=f"memory:776r:{memory}")
        return replace(base, **kw)

    def chain(self, memory, versions, *, evidence_refs=None):
        first = self.runtime.retain(
            self.proposal(memory, 0, **({"evidence_refs": evidence_refs} if evidence_refs else {})),
            versions[0][0])
        self.case.assertTrue(first.committed, first)
        ids = [first.fact_uuid]
        for i, (text, kind) in enumerate(versions[1:], start=1):
            before = versions[i - 1][0]
            corpus = corpus_for(rule(rule_id=f"rule:776r:{memory}:{i}", target=f"memory:776r:{memory}",
                                     criterion="value-correction", from_state=before, to_values=(text,)))
            self._verifiers.append(corpus.verifier())
            out = self.runtime.correct(
                self.proposal(memory, i, "correction", state_snapshot=f"v{i}", review_satisfied=True,
                              approval_refs=("approval:776r",)),
                text, replacement_kind=kind,
                evidence=corpus.evidence_for(target_reference=f"memory:776r:{memory}",
                                             criterion="value-correction", pre_state=before, proposed_value=text))
            self.case.assertTrue(out.committed, out)
            ids.append(out.fact_uuid)
        self.ids[memory] = ids
        return ids

    def prune(self, memory):
        out = self.runtime.delete_current(replace(
            self.proposal(memory, 99, "pruning", review_satisfied=True, approval_refs=("approval:776r",)),
            target_class=policy.M1, proposed_strength="tentative"))
        self.case.assertTrue(out.committed, out)

    def purge(self, memory):
        corpus = corpus_for(rule(rule_id=f"rule:776r:{memory}:purge", target=f"memory:776r:{memory}",
                                 criterion="permanent-deletion", from_state="current", to_values=("deleted",)))
        self._verifiers.append(corpus.verifier())
        out = self.runtime.delete_current(
            replace(self.proposal(memory, 98, "permanent_deletion", review_satisfied=True,
                                  approval_refs=("approval:dpo",)), reversibility="irreversible"),
            evidence=corpus.evidence_for(target_reference=f"memory:776r:{memory}", criterion="permanent-deletion",
                                         pre_state="current", proposed_value="deleted"))
        self.case.assertTrue(out.committed, out)

    def recall(self, query=KILN_QUERY, mode="historical", runtime=None, **kw):
        return (runtime or self.runtime).multi_route_recall(query, _context(), temporal_intent={"mode": mode}, **kw)

    def recovered(self):
        durable = ConfigBoundRestartRuntime.recover(self.root, plan=_plan())
        return ConfiguredCompositionRuntime(durable_runtime=durable, plan=_plan(), vector_retriever=self.vector)


class _Facade(unittest.TestCase):
    QUERY = "Orrin gateway region"

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name + "/m"
        self.memory = self.open()
        self.addCleanup(lambda: self.memory.closed or self.memory.close())

    def open(self, scope="project:a"):
        return AgentMemory.open(self.root, tenant="tenant:c644", actor_id="agent:c644", scope=scope, purpose="c644")

    def reopen(self, scope="project:a"):
        self.memory.close()
        self.memory = self.open(scope)

    def state_changed(self, memory="memory:a", values=("Oslo", "Bergen")):
        first = self.memory.remember(memory, f"{self.QUERY} is {values[0]}", proposition=_prop(values[0]))
        self.assertTrue(first["committed"], first)
        ids = [first["fact_uuid"]]
        for value in values[1:]:
            out = self.memory.correct(memory, f"{self.QUERY} is {value}", evidence=_evidence(), risk_class="low",
                                      replacement_kind="state_change")
            self.assertTrue(out["committed"], out)
            ids.append(out["fact_uuid"])
        return ids


# ------------------------------------------------------------------ #774 reproduction (no expectedFailure)

class PreExistingDeletionLeakReproduction(unittest.TestCase):
    def test_plain_historical_recall_does_not_serve_a_deleted_memorys_history(self):
        # Verbatim invariant of #774's PreExistingDeletionLeak, decorator removed.
        h = _Store(self)
        old, _ = h.chain("kiln", KILN)
        self.assertIn(old, h.recall().admitted)
        h.prune("kiln")
        self.assertNotIn(old, h.recall().admitted)


# ------------------------------------------------------------------ P0: indirect disclosure surfaces

class DeletedHistoryNotDisclosedThroughSemantics(_Facade):
    def test_write_semantics_of_an_earlier_version_is_withheld_after_forget(self):
        old, new = self.state_changed()
        self.assertIn("Oslo", json.dumps(self.memory.write_semantics(old)))  # visible before deletion
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        self.assertIsNone(self.memory.write_semantics(new))
        self.assertIsNone(self.memory.write_semantics(old))

    def test_write_semantics_of_an_earlier_version_is_withheld_after_restart(self):
        old, _ = self.state_changed()
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        self.reopen()
        self.assertIsNone(self.memory.write_semantics(old))

    def test_semantics_of_a_fact_derived_from_an_earlier_version_is_withheld(self):
        old, _ = self.state_changed()
        derived = self.memory.remember("memory:digest", "Digest: the gateway region used to be Oslo",
                                       evidence_refs=(old,))
        self.assertTrue(derived["committed"], derived)
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        recalled = self.memory.recall("gateway region digest Oslo", temporal_intent={"mode": "current"})
        self.assertNotIn(derived["fact_uuid"], recalled["admitted"])
        self.assertIsNone(self.memory.write_semantics(derived["fact_uuid"]))

    def test_semantic_proposals_do_not_reference_a_deleted_memorys_earlier_version(self):
        a1 = self.memory.remember("memory:a", TEXT["room_old"], proposition=PROP["room_old"])["fact_uuid"]
        self.memory.remember("memory:b", TEXT["room_new"], proposition=PROP["room_new"])
        self.assertEqual([p["target_fact_uuid"] for p in self.memory.semantic_proposals()], [a1])
        self.assertTrue(self.memory.correct("memory:a", "The Kestrel standup meets in room Cobalt.",
                                            evidence=_evidence(), risk_class="low",
                                            replacement_kind="state_change")["committed"])
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        self.assertEqual([p for p in self.memory.semantic_proposals() if p["target_reference"] == "memory:a"], [])

    def test_unrelated_memory_semantics_remain_available(self):
        self.state_changed()
        other = self.memory.remember("memory:b", "Orrin gateway owner is Team Kite",
                                     proposition=_prop("Team Kite", attribute="owner"))["fact_uuid"]
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        self.assertIn("Team Kite", json.dumps(self.memory.write_semantics(other)))


# ------------------------------------------------------------------ declared deletion policies

class DeletionPolicies(unittest.TestCase):
    def test_permanent_deletion_physically_removes_every_version(self):
        h = _Store(self)
        old, new = h.chain("kiln", KILN)
        h.purge("kiln")
        substrate = h.adapter._substrate
        self.assertIsNone(substrate.get_fact(new))
        self.assertIsNone(substrate.get_fact(old))
        self.assertNotIn("cone 6 glaze", (h.root / "substrate.json").read_text(encoding="utf-8"))
        self.assertNotIn(old, h.recall().admitted)

    def test_pruning_keeps_every_version_recoverable_but_inadmissible(self):
        h = _Store(self)
        old, new = h.chain("kiln", KILN)
        h.prune("kiln")
        self.assertIsNotNone(h.adapter._substrate.get_fact(old))
        self.assertIsNotNone(h.adapter._substrate.get_fact(new))
        result = h.recall()
        self.assertFalse({old, new} & set(result.admitted))
        self.assertEqual(result.refusals.get(old), "logical_memory_deleted")

    def test_recreating_a_deleted_memory_is_admitted_without_its_deleted_history(self):
        # v7 admits a governed re-creation after deletion. A deletion of the old
        # lineage must not silently make every future write to the id invisible.
        h = _Store(self)
        old, new = h.chain("kiln", KILN)
        h.prune("kiln")
        again = h.runtime.retain(h.proposal("kiln", 200), "The kiln firing schedule uses cone 8 glaze.")
        self.assertTrue(again.committed, again)
        current = h.recall(mode="current")
        self.assertIn(again.fact_uuid, current.admitted, current.refusals.get(again.fact_uuid))
        historical = h.recall()
        self.assertIn(again.fact_uuid, historical.admitted)
        self.assertFalse({old, new} & set(historical.admitted))


# ------------------------------------------------------------------ restart and every route

class RestartAndRoutes(unittest.TestCase):
    def test_restart_cannot_resurrect_history(self):
        h = _Store(self)
        old, new = h.chain("tram", [("Route 4 trams run every 20 minutes.", None),
                                    ("Route 4 trams run every 15 minutes.", S),
                                    ("Route 4 trams run every 10 minutes.", S)])[0], h.ids["tram"][-1]
        h.prune("tram")
        recovered = h.recovered()
        result = h.recall("How often did Route 4 trams run?", runtime=recovered)
        self.assertFalse(set(h.ids["tram"]) & set(result.admitted))
        self.assertEqual(result.refusals.get(old), "logical_memory_deleted")

    def test_exact_identity_lexical_vector_and_composed_routes_share_admission(self):
        h = _Store(self, vector=True)
        old, new = h.chain("kiln", KILN)
        keep = h.chain("pump", [("The water pump service interval was 7 days.", None),
                                ("The water pump service interval became 14 days.", S)])
        h.prune("kiln")
        ctx = _context()
        composed = h.recall(logical_memory_refs=("memory:776r:kiln", "memory:776r:pump"))
        self.assertIn(old, composed.candidates)  # residue is rediscovered by some route ...
        self.assertFalse({old, new} & set(composed.admitted))  # ... but never admitted
        self.assertFalse({old, new} & set(composed.ranked_admitted))
        vector_hits = [hit for hit in composed.provenance_for(old) if hit.route_id == SEMANTIC_VECTOR_ROUTE]
        self.assertTrue(vector_hits, "vector route should rediscover the pruned residue")
        self.assertIn(keep[0], composed.admitted)
        lexical = h.runtime.recall("kiln firing schedule glaze", ctx)
        self.assertFalse({old, new} & set(lexical.admitted))
        for mode in ("current", "historical"):
            exact = h.recall("", mode, logical_memory_refs=("memory:776r:kiln",))
            self.assertFalse({old, new} & set(exact.admitted), mode)
        self.assertEqual(h.adapter.current_governed_typed_claim(old, ctx), (False, None))

    def test_typed_graph_route_cannot_reach_a_deleted_earlier_version(self):
        # No governed relation-write API exists; the relation is written on the
        # substrate exactly as tests/test_typed_graph_retrieval.py does.
        from agentmem_ref.recall_control import (ControlledRecallPlanner, NativeTypedGraphCandidateRetriever,
                                                 RecallControlPlan, RecallRouteBudget, TYPED_GRAPH_ROUTE)
        from agentmem_ref.runtime_composition import EXACT_IDENTITY_ROUTE, LEXICAL_ROUTE, SHARED_EVIDENCE_ROUTE
        from tests.test_typed_graph_retrieval import _FixedController, _relation

        h = _Store(self)
        old, _ = h.chain("kiln", KILN)
        seed = h.chain("studio", [("The pottery studio fires glazes on Fridays.", None)])[0]
        h.adapter.checkpoint_substrate().write_relation(replace(
            _relation("relation:studio-kiln", seed, old), group_id=TENANT))
        h.prune("kiln")
        plan = RecallControlPlan(controller_ref="test:776r", controller_version="1", route_budgets=(
            RecallRouteBudget(LEXICAL_ROUTE, 0), RecallRouteBudget(EXACT_IDENTITY_ROUTE, 1),
            RecallRouteBudget(TYPED_GRAPH_ROUTE, 8), RecallRouteBudget(SHARED_EVIDENCE_ROUTE, 0)))
        planner = ControlledRecallPlanner(h.adapter, controller=_FixedController(plan),
                                          graph_retriever=NativeTypedGraphCandidateRetriever())
        for mode in ("current", "historical"):
            result = planner.recall("", _context(), logical_memory_refs=("memory:776r:studio",),
                                    temporal_intent={"mode": mode})
            self.assertIn(seed, result.recall.admitted, mode)
            self.assertIn(old, result.recall.candidates, mode)  # reachable ...
            self.assertNotIn(old, result.recall.admitted, mode)  # ... never admitted
            self.assertEqual(result.recall.refusals.get(old), "logical_memory_deleted")

    def test_out_of_scope_reader_never_learns_of_the_deletion(self):
        h = _Store(self)
        old, _ = h.chain("kiln", KILN)
        h.prune("kiln")
        foreign = replace(_context(), project_ref="project-beta", target_domain_refs=(TENANT, "project-beta"))
        result = h.runtime.multi_route_recall(KILN_QUERY, foreign, temporal_intent={"mode": "historical"})
        self.assertNotIn(old, result.admitted)
        self.assertNotIn(result.refusals.get(old), ("logical_memory_deleted", "derived_from_deleted_logical_memory"))
        self.assertIsNone(h.adapter.write_semantics(old, foreign))


# ------------------------------------------------------------------ scale

class TombstoneScale(unittest.TestCase):
    def test_admission_cost_does_not_grow_with_the_number_of_tombstones(self):
        h = _Store(self)
        for i in range(20):
            h.runtime.retain(h.proposal(f"m{i}", 0), f"The pump station {i} service interval is {i} days.")
        facts = list(h.adapter._substrate.all_facts())
        ctx = _context()

        def per_candidate():
            best = float("inf")
            for _ in range(3):
                start = time.perf_counter()
                for fact in facts:
                    h.adapter._admission_refusal(fact, ctx, "historical")
                best = min(best, (time.perf_counter() - start) / len(facts))
            return best

        # One genuine deletion so the deleted-memory branch is exercised.
        h.chain("kiln", KILN)
        h.prune("kiln")
        small = per_candidate()
        # Read-only synthetic records shaped like governed tombstones.
        for k in range(50_000):
            h.adapter._tombstones[f"synthetic-{k}"] = {
                "memory_id": f"memory:synthetic:{k}", "fact_uuid": f"synthetic-{k}",
                "deleted_at": "2026-01-01T00:00:00Z", "deleted_fact_uuids": [f"synthetic-{k}"]}
        large = per_candidate()
        self.assertLess(large, 10 * small + 50e-6, f"{small * 1e6:.1f}us -> {large * 1e6:.1f}us per candidate")


if __name__ == "__main__":
    unittest.main()
