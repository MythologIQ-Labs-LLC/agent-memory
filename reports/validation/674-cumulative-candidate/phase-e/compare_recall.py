#!/usr/bin/env python3
"""Phase E task-correctness comparison: run the same scenarios against whichever
``agentmem_ref`` is first on sys.path (main or the cumulative candidate) and emit JSON.

usage: python compare_recall.py <reference-dir> <label> <out.json>

Scenarios (all deterministic, in-process, SQLite composition runtime under a temp dir):
  A  graph neighbourhood where inaccessible (other-project) neighbours are ranked ahead of
     required accessible ones; required-recall, cross-scope exposure, bridging via a foreign
     intermediate, and the eligibility-probe ceiling limitation
  B  shared-domain evidence that must stay recallable (seed in the project, neighbour held in a
     shared isolation domain the reader holds); typed-graph and shared-evidence routes
  C  wrong-subject lexical collision (ranking sanity)
  D  no-answer behaviour
  E  deletion correctness through the public facade (direct and derived)
  F  context budget (returned prefix vs admitted)
  G  latency: facade recall p50/p95 over a 1,500-fact corpus; controlled graph recall p50/p95
     on a 400-neighbour hub (high-degree traversal overhead)
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

REFERENCE = Path(sys.argv[1]).resolve()
LABEL = sys.argv[2]
OUT = Path(sys.argv[3])
sys.path.insert(0, str(REFERENCE))
os.chdir(REFERENCE)

from agentmem_ref import AgentMemory, policy  # noqa: E402
from agentmem_ref.adapter import RecallContext  # noqa: E402
from agentmem_ref.recall_control import (  # noqa: E402
    ControlledRecallPlanner,
    GraphTraversalSpec,
    NativeTypedGraphCandidateRetriever,
    RecallControlPlan,
    RecallRouteBudget,
    TYPED_GRAPH_ROUTE,
)
from agentmem_ref.runtime_composition import (  # noqa: E402
    EXACT_IDENTITY_ROUTE,
    LEXICAL_ROUTE,
    SHARED_EVIDENCE_ROUTE,
    ConfiguredCompositionRuntime,
)
from agentmem_ref.runtime_config import validate_runtime_configuration  # noqa: E402
from agentmem_ref.substrate import TypedRelation  # noqa: E402

CONFIG = REFERENCE / "fixtures" / "runtime-configuration" / "reference-composed-runtime.json"
TENANT = "tenant-phase-e"
ALPHA = "project-alpha"
BETA = "project-beta"
SHARED = "shared:team"
REPORT: dict = {"label": LABEL, "reference": str(REFERENCE), "scenarios": {}}


def plan():
    return validate_runtime_configuration(json.loads(CONFIG.read_text(encoding="utf-8")))


def proposal(target, *, evidence_refs, project_ref=ALPHA, domains=None, required=None):
    domains = domains if domains is not None else (TENANT, project_ref)
    required = required if required is not None else (project_ref,)
    return policy.Proposal(
        proposal_id=f"proposal:{target}",
        actor_id="agent:phase-e",
        charter_version="charter-v1",
        target_reference=target,
        target_class=policy.M2,
        scope=TENANT,
        operation="promotion",
        current_strength="observed",
        proposed_strength="promoted",
        downstream_authority=policy.A1,
        reversibility="reversible",
        risk_class="low",
        evidence_refs=tuple(evidence_refs),
        tenant_ref=TENANT,
        isolation_domain_refs=tuple(domains),
        required_isolation_domain_refs=tuple(required),
        project_ref=project_ref,
        purpose="phase-e",
    )


def context(project_ref=ALPHA, domains=None):
    return RecallContext(
        target_domain_refs=tuple(domains) if domains is not None else (TENANT, project_ref),
        principal_ref="agent:phase-e",
        project_ref=project_ref,
        purpose="phase-e",
    )


def relation(rid, source, target, *, weight=1.0, rtype="supports"):
    return TypedRelation(
        relation_id=rid, source_uuid=source, target_uuid=target, relation_type=rtype,
        group_id=TENANT, evidence_refs=(), retrieval_weight=weight,
        created_at="2026-09-24T00:00:00Z", valid_at="2026-09-24T00:00:00Z",
    )


class Fixed:
    def __init__(self, budgets):
        self._plan = RecallControlPlan(controller_ref="phase-e", controller_version="1", route_budgets=tuple(budgets))

    def plan(self, query, *, logical_memory_refs, available_routes):
        return self._plan


def graph_plan(graph_limit=8, exact=1, shared=0, lexical=0):
    return Fixed((
        RecallRouteBudget(LEXICAL_ROUTE, lexical),
        RecallRouteBudget(EXACT_IDENTITY_ROUTE, exact),
        RecallRouteBudget(TYPED_GRAPH_ROUTE, graph_limit),
        RecallRouteBudget(SHARED_EVIDENCE_ROUTE, shared),
    ))


def new_runtime(tmp):
    return ConfiguredCompositionRuntime.create(Path(tmp), tenant=TENANT, plan=plan())


def retain(rt, target, text, **kw):
    outcome = rt.retain(proposal(target, evidence_refs=kw.pop("evidence_refs", (f"evidence:{target}",)), **kw), text)
    assert outcome.committed, (target, outcome)
    return outcome.fact_uuid


def pct(values, p):
    values = sorted(values)
    if not values:
        return None
    k = (len(values) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


# ---------------------------------------------------------------- A: inaccessible-before-required
def scenario_a():
    out = {}
    with tempfile.TemporaryDirectory() as tmp:
        rt = new_runtime(tmp)
        seed = retain(rt, "memory:seed", "alpha seed topic")
        foreign = [retain(rt, f"memory:foreign-{i:02d}", f"beta private {i}", project_ref=BETA) for i in range(12)]
        required = [retain(rt, f"memory:required-{i}", f"alpha required detail {i}") for i in range(3)]
        sub = rt.adapter.checkpoint_substrate()
        # foreign neighbours carry the higher weight, so a naive fan-out spends itself on them first
        for i, f in enumerate(foreign):
            sub.write_relation(relation(f"r:foreign-{i}", seed, f, weight=1.0))
        for i, r in enumerate(required):
            sub.write_relation(relation(f"r:required-{i}", seed, r, weight=0.5))
        res = ControlledRecallPlanner(rt.adapter, controller=graph_plan(graph_limit=16),
                                      graph_retriever=NativeTypedGraphCandidateRetriever()).recall(
            "", context(), logical_memory_refs=("memory:seed",))
        out["A1_required_before_inaccessible"] = {
            "required_recalled": sum(r in res.admitted for r in required),
            "required_total": len(required),
            "foreign_in_caller_visible_candidates": sum(f in res.candidates for f in foreign),
            "foreign_in_admitted": sum(f in res.admitted for f in foreign),
            "graph_route_count": res.route_candidate_counts.get(TYPED_GRAPH_ROUTE),
            "max_fanout": GraphTraversalSpec().max_fanout,
        }
    # A2 bridging: seed -> foreign intermediate -> required
    with tempfile.TemporaryDirectory() as tmp:
        rt = new_runtime(tmp)
        seed = retain(rt, "memory:seed", "alpha seed topic")
        bridge = retain(rt, "memory:bridge", "beta intermediate", project_ref=BETA)
        target = retain(rt, "memory:target", "alpha indirect answer")
        sub = rt.adapter.checkpoint_substrate()
        sub.write_relation(relation("r:seed-bridge", seed, bridge))
        sub.write_relation(relation("r:bridge-target", bridge, target))
        res = ControlledRecallPlanner(rt.adapter, controller=graph_plan(),
                                      graph_retriever=NativeTypedGraphCandidateRetriever(GraphTraversalSpec(max_depth=2))).recall(
            "", context(), logical_memory_refs=("memory:seed",))
        out["A2_bridge_through_foreign_intermediate"] = {
            "target_reached_via_foreign_bridge": target in res.admitted,
            "bridge_in_caller_visible_candidates": bridge in res.candidates,
        }
    # A3 eligibility-probe ceiling: 8*16 = 128 foreign ahead of one eligible neighbour (documented limitation)
    with tempfile.TemporaryDirectory() as tmp:
        rt = new_runtime(tmp)
        seed = retain(rt, "memory:seed", "alpha seed topic")
        n_foreign = GraphTraversalSpec().max_fanout * 16 + 1
        foreign = [retain(rt, f"memory:f-{i:03d}", f"beta private {i}", project_ref=BETA) for i in range(n_foreign)]
        late = retain(rt, "memory:late-eligible", "alpha late eligible")
        sub = rt.adapter.checkpoint_substrate()
        for i, f in enumerate(foreign):
            sub.write_relation(relation(f"r:f-{i}", seed, f, weight=1.0))
        sub.write_relation(relation("r:late", seed, late, weight=0.5))
        t0 = time.perf_counter()
        res = ControlledRecallPlanner(rt.adapter, controller=graph_plan(),
                                      graph_retriever=NativeTypedGraphCandidateRetriever()).recall(
            "", context(), logical_memory_refs=("memory:seed",))
        out["A3_eligibility_probe_ceiling"] = {
            "foreign_ahead": n_foreign,
            "late_eligible_recalled": late in res.admitted,
            "foreign_in_caller_visible_candidates": sum(f in res.candidates for f in foreign),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
            "note": "candidate: bounded probe ceiling (max_fanout*16) can exclude an eligible neighbour ranked behind >128 ineligible ones; main: fan-out spent on the first 8 ineligible neighbours",
        }
    REPORT["scenarios"]["A"] = out


# ---------------------------------------------------------------- B: shared-domain evidence preserved
def scenario_b():
    out = {}
    with tempfile.TemporaryDirectory() as tmp:
        rt = new_runtime(tmp)
        seed = retain(rt, "memory:seed", "alpha seed topic", evidence_refs=("session:shared",))
        shared = retain(rt, "memory:shared", "team shared detail", evidence_refs=("session:shared",),
                        domains=(TENANT, SHARED), required=(SHARED,))
        private_beta = retain(rt, "memory:beta", "beta private detail", evidence_refs=("session:shared",), project_ref=BETA)
        sub = rt.adapter.checkpoint_substrate()
        sub.write_relation(relation("r:seed-shared", seed, shared, weight=0.9))
        sub.write_relation(relation("r:seed-beta", seed, private_beta, weight=1.0))
        ctx = context(ALPHA, domains=(TENANT, ALPHA, SHARED))
        res_graph = ControlledRecallPlanner(rt.adapter, controller=graph_plan(),
                                            graph_retriever=NativeTypedGraphCandidateRetriever()).recall(
            "", ctx, logical_memory_refs=("memory:seed",))
        shared_only = Fixed((RecallRouteBudget(LEXICAL_ROUTE, 0), RecallRouteBudget(EXACT_IDENTITY_ROUTE, 1),
                             RecallRouteBudget(SHARED_EVIDENCE_ROUTE, 8)))
        res_shared = ControlledRecallPlanner(rt.adapter, controller=shared_only).recall(
            "", ctx, logical_memory_refs=("memory:seed",))
        res_multi = rt.multi_route_recall("", ctx, logical_memory_refs=("memory:seed",))
        out["shared_domain_neighbour_via_typed_graph"] = shared in res_graph.admitted
        out["shared_domain_neighbour_via_shared_evidence_route"] = shared in res_shared.admitted
        out["shared_domain_neighbour_via_default_multi_route"] = shared in res_multi.admitted
        out["beta_private_exposed_graph"] = private_beta in res_graph.candidates
        out["beta_private_exposed_shared_evidence"] = private_beta in res_shared.candidates
        out["beta_private_exposed_multi_route"] = private_beta in res_multi.candidates
    REPORT["scenarios"]["B"] = out


# ---------------------------------------------------------------- C, D, E, F via the public facade
def facade_scenarios():
    out = {}
    with tempfile.TemporaryDirectory() as tmp:
        m = AgentMemory.open(Path(tmp), tenant=TENANT, actor_id="agent:phase-e", scope=ALPHA, purpose="phase-e")
        m.remember("memory:alice-phone", "alice phone number is 555-0101")
        m.remember("memory:bob-phone", "bob phone number is 555-0202")
        m.remember("memory:alice-city", "alice lives in lisbon")
        res = m.recall("bob phone number")
        ranked = res.get("admitted") or []
        out["C_wrong_subject"] = {
            "top_ranked_is_bob": bool(ranked) and ranked[0] == m.recall("", logical_memory_refs=("memory:bob-phone",))["admitted"][0],
            "admitted_count": len(ranked),
        }
        none = m.recall("zebra quantum lattice")
        out["D_no_answer"] = {"candidates": len(none.get("candidates") or []), "admitted": len(none.get("admitted") or []),
                              "returned": len(none.get("returned") or [])}
        budget = m.recall("phone number", budget=1)
        out["F_context_budget"] = {"admitted": len(budget["admitted"]), "returned": len(budget["returned"]),
                                   "return_policy_applied": budget.get("return_policy", {}).get("applied")}
        # E deletion: direct and derived (a memory citing the deleted fact's uuid as evidence)
        src = m.remember("memory:source", "source note about the quarterly budget")
        src_uuid = src.get("fact_uuid")
        derived = m.remember("memory:derived", "derived note citing the quarterly budget", evidence_refs=(src_uuid,))
        before = m.recall("quarterly budget")
        gone = m.forget("memory:source")
        after = m.recall("quarterly budget")
        out["E_deletion"] = {
            "before_admitted": len(before["admitted"]),
            "forget_committed": gone.get("committed"),
            "source_recalled_after_forget": src_uuid in after["admitted"],
            "derived_recalled_after_forget": derived.get("fact_uuid") in after["admitted"],
            "deleted_id_in_public_candidates": src_uuid in (after.get("candidates") or []),
        }
        m.close()
    REPORT["scenarios"]["facade"] = out


# ---------------------------------------------------------------- G latency
def scenario_g():
    out = {}
    with tempfile.TemporaryDirectory() as tmp:
        m = AgentMemory.open(Path(tmp), tenant=TENANT, actor_id="agent:phase-e", scope=ALPHA, purpose="phase-e")
        words = ["alpha", "budget", "release", "lisbon", "phone", "ticket", "deploy", "review", "memory", "graph",
                 "schema", "policy", "tenant", "scope", "audit"]
        t_w = []
        for i in range(1500):
            text = f"{words[i % 15]} {words[(i * 7) % 15]} {words[(i * 11) % 15]} note {i}"
            t0 = time.perf_counter()
            m.remember(f"memory:corpus-{i:04d}", text)
            t_w.append((time.perf_counter() - t0) * 1000)
        t_r = []
        admitted_sizes = []
        for i in range(200):
            q = f"{words[i % 15]} {words[(i * 3) % 15]}"
            t0 = time.perf_counter()
            r = m.recall(q, budget=20)
            t_r.append((time.perf_counter() - t0) * 1000)
            admitted_sizes.append(len(r["admitted"]))
        m.close()
        out["facade_remember_ms"] = {"p50": round(pct(t_w, .5), 2), "p95": round(pct(t_w, .95), 2)}
        out["facade_recall_ms"] = {"p50": round(pct(t_r, .5), 2), "p95": round(pct(t_r, .95), 2),
                                   "mean_admitted": round(statistics.mean(admitted_sizes), 1), "queries": 200, "corpus": 1500}
    with tempfile.TemporaryDirectory() as tmp:
        rt = new_runtime(tmp)
        seed = retain(rt, "memory:hub", "hub topic")
        n = 400
        refs = []
        for i in range(n):
            proj = BETA if i % 2 else ALPHA
            refs.append(retain(rt, f"memory:n-{i:03d}", f"neighbour {i}", project_ref=proj))
        sub = rt.adapter.checkpoint_substrate()
        for i, r in enumerate(refs):
            sub.write_relation(relation(f"r:hub-{i}", seed, r, weight=1.0 - i * 0.001))
        planner = ControlledRecallPlanner(rt.adapter, controller=graph_plan(graph_limit=8),
                                          graph_retriever=NativeTypedGraphCandidateRetriever())
        t = []
        last = None
        for _ in range(50):
            t0 = time.perf_counter()
            last = planner.recall("", context(), logical_memory_refs=("memory:hub",))
            t.append((time.perf_counter() - t0) * 1000)
        out["high_degree_graph_recall_ms"] = {
            "p50": round(pct(t, .5), 2), "p95": round(pct(t, .95), 2), "hub_degree": n,
            "graph_route_count": last.route_candidate_counts.get(TYPED_GRAPH_ROUTE),
            "foreign_in_candidates": sum(r in last.candidates for i, r in enumerate(refs) if i % 2),
            "alpha_admitted": sum(r in last.admitted for i, r in enumerate(refs) if not i % 2),
        }
    REPORT["scenarios"]["G"] = out


SELECT = set(sys.argv[4].split(",")) if len(sys.argv) > 4 else None
for fn in (scenario_a, scenario_b, facade_scenarios, scenario_g):
    if SELECT is not None and fn.__name__ not in SELECT:
        continue
    try:
        fn()
    except Exception as exc:  # record, never hide
        REPORT["scenarios"][fn.__name__ + "_error"] = repr(exc)
OUT.write_text(json.dumps(REPORT, indent=2) + "\n", encoding="utf-8")
print(json.dumps(REPORT, indent=2))
