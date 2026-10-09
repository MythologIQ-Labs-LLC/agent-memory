"""Phase D: SQLite cost of governed recall, receipt capture, indexed slot audit and observer.

usage:
  perf644.py build <store_root> <n>            # build one store (untimed for comparison)
  perf644.py measure <store_root> <n> <out.json> [--samples K] [--cold-samples C]

The tree under test is selected by PYTHONPATH. Features missing from a tree are
recorded as null (v6 has no observer or receipt; e002536 has no receipt).
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import time

from agentmem_ref import AgentMemory
from agentmem_ref.recall_control import ControlledRecallPlanner, DeterministicRecallController
from agentmem_ref.runtime import typed_proposition as T

try:
    from agentmem_ref.runtime.evidence_sufficiency import CoverageNeed
except ImportError:
    CoverageNeed = None
try:
    from agentmem_ref.runtime import recall_observation_receipt as R
except ImportError:
    R = None

QUERY, SUBJECT, ATTR = "Entity5 attribute5", "Entity5", "attribute5"


def open_store(root):
    return AgentMemory.open(root, tenant="tenant:perf", actor_id="agent:perf", scope="project:perf", purpose="perf")


def build(root, n):
    m = open_store(root)
    for i in range(n):
        m.remember(f"memory:{i}", f"Entity{i} attribute{i % 7} is value{i}",
                   proposition={"subject": f"Entity{i}", "attribute": f"attribute{i % 7}", "value": f"value{i}",
                                "assertion": "state", "cardinality": "single"})
    m.close()


def stats(xs):
    if not xs:
        return None
    s = sorted(xs)
    p95 = s[max(0, min(len(s) - 1, int(round(0.95 * len(s))) - 1))]
    return {"n": len(xs), "median_ms": round(statistics.median(s) * 1e3, 3), "p95_ms": round(p95 * 1e3, 3),
            "min_ms": round(s[0] * 1e3, 3), "max_ms": round(s[-1] * 1e3, 3)}


def timed(fn):
    t0 = time.perf_counter()
    out = fn()
    return time.perf_counter() - t0, out


def capture_args(result, context):
    rec, plan = result.recall, result.plan
    return dict(
        query=rec.query, reader_domain_refs=tuple(context.target_domain_refs), principal_ref=context.principal_ref,
        project_ref=context.project_ref, purpose=context.purpose, task_ref=context.task_ref,
        controller_ref=plan.controller_ref, admission_policy=rec.policy_version, admission_mode=rec.admission_mode,
        evaluated_at=rec.evaluated_at, candidates=rec.candidates, admitted=rec.admitted, ranked=rec.ranked_admitted,
        route_observations=tuple(R.RouteObservation(route_id=b.route_id, candidate_limit=b.candidate_limit,
                                                    anchor_limit=b.anchor_limit,
                                                    returned_count=result.route_candidate_counts.get(b.route_id, 0),
                                                    executed=b.candidate_limit > 0) for b in plan.route_budgets),
        observed_route_counts=result.route_candidate_counts, plan=plan.to_dict(), refusals=rec.refusals)


def session(root):
    m = open_store(root)
    pl = ControlledRecallPlanner(m.runtime.adapter, controller=DeterministicRecallController())
    ctx = m._handle_recall_context()
    gov = m.runtime.durable_runtime.run_governed_read
    return m, pl, ctx, gov


def measure(root, n, out, samples, cold_samples):
    has_obs = hasattr(ControlledRecallPlanner, "observe_persisted_typed_coverage")
    need = (CoverageNeed(T.typed_slot(SUBJECT, ATTR)),) if has_obs else None
    report = {"n_facts": n, "has_observer": has_obs, "has_receipt": R is not None, "samples": samples}

    # ---- cold: fresh open; first recall, first index build, first audit, first observer
    cold = {k: [] for k in ("open", "first_recall", "first_index_build", "first_audit", "first_observer")}
    for _ in range(cold_samples):
        t, (m, pl, ctx, gov) = timed(lambda: session(root))
        cold["open"].append(t)
        try:
            t, res = timed(lambda: gov(lambda: pl.recall(QUERY, ctx)))
            cold["first_recall"].append(t)
            if has_obs:
                adapter = m.runtime.adapter
                if getattr(adapter, "_semantic_slot_index", "absent") is None:
                    t, _ = timed(adapter._semantic_index)
                    cold["first_index_build"].append(t)
                t, _ = timed(lambda: adapter.current_typed_slot_obstacles(
                    (need[0].key,), tuple(res.recall.admitted), ctx))
                cold["first_audit"].append(t)
                t, _ = timed(lambda: gov(lambda: pl.observe_persisted_typed_coverage(res, ctx, needs=need)))
                cold["first_observer"].append(t)
        finally:
            m.close()
    report["cold"] = {k: stats(v) for k, v in cold.items()}

    # ---- warm: one open session, repeated operations after warm-up
    m, pl, ctx, gov = session(root)
    try:
        res = gov(lambda: pl.recall(QUERY, ctx))
        report["admitted"] = len(res.recall.admitted)
        report["candidates"] = len(res.recall.candidates)
        warm = {k: [] for k in ("recall", "receipt_capture", "receipt_verify", "index_rebuild", "audit_indexed",
                                "audit_full_scan_reference", "observer_combined")}
        adapter = m.runtime.adapter
        if has_obs:
            gov(lambda: pl.observe_persisted_typed_coverage(res, ctx, needs=need))
        for _ in range(samples):
            warm["recall"].append(timed(lambda: gov(lambda: pl.recall(QUERY, ctx)))[0])
            if R is not None:
                args = capture_args(res, ctx)
                warm["receipt_capture"].append(timed(lambda: R.capture_recall_observation(**args))[0])
                warm["receipt_verify"].append(timed(res.observation_unchanged)[0])
            if has_obs:
                warm["audit_indexed"].append(timed(lambda: adapter.current_typed_slot_obstacles(
                    (need[0].key,), tuple(res.recall.admitted), ctx))[0])
                warm["observer_combined"].append(timed(
                    lambda: gov(lambda: pl.observe_persisted_typed_coverage(res, ctx, needs=need)))[0])
        if has_obs:
            for _ in range(max(3, samples // 5)):
                # full-store enumeration with the same per-fact work: the e002536 strategy
                def scan():
                    for fact in adapter._substrate.all_facts():
                        if fact.is_transaction_expired or adapter._admission_refusal(fact, ctx) is not None:
                            continue
                        adapter.write_semantics(fact.uuid, ctx)
                warm["audit_full_scan_reference"].append(timed(scan)[0])
                if hasattr(adapter, "_semantic_slot_index"):
                    adapter._semantic_slot_index = None
                    warm["index_rebuild"].append(timed(adapter._semantic_index)[0])
        report["warm"] = {k: stats(v) for k, v in warm.items()}
    finally:
        m.close()
    json.dump(report, open(out, "w"), indent=1)
    print(json.dumps(report))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "build":
        build(sys.argv[2], int(sys.argv[3]))
    else:
        args = sys.argv[5:]
        samples = int(args[args.index("--samples") + 1]) if "--samples" in args else 30
        cold = int(args[args.index("--cold-samples") + 1]) if "--cold-samples" in args else 5
        measure(sys.argv[2], int(sys.argv[3]), sys.argv[4], samples, cold)
