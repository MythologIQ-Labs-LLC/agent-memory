"""Held-out same-harness evaluation: v6 count-target signal vs #644 observer.

argv: <out.json>. The code tree under test is selected by PYTHONPATH.
Cases are generated from vocabulary disjoint from both the implementation's tests
and the independent unit harness. Gold labels are fixed by category BEFORE running.
gold_stop_safe: True iff the governed-current admitted evidence determines exactly one
current answer for a single-valued slot (so a mechanical review-stop would not be wrong).
"""
import json, sys, tempfile, time, tracemalloc, statistics, itertools
from agentmem_ref import AgentMemory
from agentmem_ref.api import contract
from agentmem_ref.memory import procedural_memory as pm
from agentmem_ref.recall_control import ControlledRecallPlanner, DeterministicRecallController
from agentmem_ref.runtime import typed_proposition as T

HAS_OBS = hasattr(ControlledRecallPlanner, "observe_persisted_typed_coverage")
if HAS_OBS:
    from agentmem_ref.runtime.evidence_sufficiency import CoverageNeed

ENTITIES = [("Kestrel router", "firmware"), ("Marlow invoice", "currency"), ("Quill warehouse", "manager"),
            ("Tamsin satellite", "orbit band"), ("Brisk ledger", "fiscal owner"), ("Copperfield lab", "safety lead")]
VALUES = [("v2", "v3"), ("EUR", "GBP"), ("Okafor", "Brandt"), ("L-band", "S-band"), ("Ruiz", "Haddad"), ("Ito", "Mensah")]

def P(s, a, v, assertion="state", cardinality="single", **flags):
    return {"subject": s, "attribute": a, "value": v, "assertion": assertion, "cardinality": cardinality, "flags": flags}

def ev(scope):
    sk = pm.SkillArtifact(skill_id="skill:heldout", version=1, purpose="heldout", scope=scope,
                          isolation_domain_refs=("tenant:h", scope), required_isolation_domain_refs=("tenant:h", scope),
                          procedure_markdown="# v\nok", provenance_refs=("evidence:heldout",))
    return pm.evidence_for(sk)

# category -> (gold_stop_safe, kind) ; kind used for secondary metrics
CATS = {
    "unique_single": (True, "plain"), "agree_two": (True, "plain"), "case_variant_agree": (True, "equiv"),
    "deleted_competitor": (True, "lifecycle"), "disputed_competitor": (True, "lifecycle"),
    "crossproject_competitor": (True, "lifecycle"), "typed_correction_applied": (True, "correction"),
    "facade_correction_applied": (True, "correction"),
    "conflict_single": (False, "conflict"), "multi_set": (False, "coexist"), "multi_one": (False, "coexist"),
    "unknown_cardinality": (False, "cardinality"), "change_unapplied": (False, "change"),
    "extracted_competitor": (False, "conflict_hidden"), "negated_competitor": (False, "conflict_hidden"),
    "hedged_change": (False, "change_hidden"), "attributed_competitor": (False, "conflict_hidden"),
    "untyped_competitor": (False, "conflict_hidden"), "expired_validity": (False, "temporal"),
    "paraphrase_unretrieved": (False, "retrieval"), "budget_cap_conflict": (False, "budget"),
}

def build(cat, ent, vals, root):
    s, a = ent; v1, v2 = vals; scope = "project:h"
    m = AgentMemory.open(root, tenant="tenant:h", actor_id="agent:h", scope=scope, purpose="heldout")
    txt = lambda v: f"{s} {a} is {v}"
    rel = []  # gold-relevant refs: facts whose evidence bears on the slot and are current
    def rem(t, prop=None, **kw):
        r = m.remember(f"memory:{len(rel)}-{abs(hash(t)) % 10**6}", t, proposition=prop, **kw); assert r["committed"], r
        return r["fact_uuid"]
    lexical = 12
    if cat == "unique_single": rel.append(rem(txt(v1), P(s, a, v1)))
    elif cat == "agree_two": rel += [rem(txt(v1), P(s, a, v1)), rem(txt(v1) + " (confirmed)", P(s, a, v1))]
    elif cat == "case_variant_agree": rel += [rem(txt(v1), P(s, a, v1)), rem(txt(v1.lower()) + " noted", P(s, a, v1.lower()))]
    elif cat in ("deleted_competitor", "disputed_competitor"):
        rel.append(rem(txt(v1), P(s, a, v1)))
        t2 = "memory:competitor"; r = m.remember(t2, txt(v2), proposition=P(s, a, v2)); assert r["committed"]
        if cat == "deleted_competitor": assert m.forget(t2)["committed"]
        else: assert m.dispute(t2, fact_uuid=r["fact_uuid"], evidence=ev(scope), risk_class="low", evidence_refs=("evidence:x",))["committed"]
    elif cat == "crossproject_competitor":
        rel.append(rem(txt(v1), P(s, a, v1)))
        o = AgentMemory.open(root + "-o", tenant="tenant:h", actor_id="agent:h", scope="project:other", purpose="heldout")
        o.remember("memory:o", txt(v2), proposition=P(s, a, v2)); o.close()
    elif cat == "typed_correction_applied":
        r = m.remember("memory:c", txt(v1), proposition=P(s, a, v1)); assert r["committed"]
        prop = contract.proposal_from_envelope(m._proposal(target_reference="memory:c", fact_text=txt(v2), operation="correction",
                                                           current_strength="reinforced", proposed_strength="reinforced", risk_class="low"))
        out = m.runtime.durable_runtime.commit_proposal(prop, txt(v2), evidence=ev(scope), replacement_kind="state_change",
                                                         typed_write={"typed_proposition": T.typed_record(T.validate(P(s, a, v2)), T.CALLER_DECLARED)})
        assert out.committed, out.refusal; rel.append(out.fact_uuid)
    elif cat == "facade_correction_applied":
        r = m.remember("memory:c", txt(v1), proposition=P(s, a, v1)); assert r["committed"]
        out = m.correct("memory:c", txt(v2), evidence=ev(scope), risk_class="low", replacement_kind="state_change")
        assert out["committed"], out; rel.append(out["fact_uuid"])
    elif cat == "conflict_single": rel += [rem(txt(v1), P(s, a, v1)), rem(txt(v2), P(s, a, v2))]
    elif cat == "multi_set": rel += [rem(txt(v1), P(s, a, v1, cardinality="multi")), rem(txt(v2), P(s, a, v2, cardinality="multi"))]
    elif cat == "multi_one": rel.append(rem(txt(v1), P(s, a, v1, cardinality="multi")))
    elif cat == "unknown_cardinality": rel.append(rem(txt(v1), P(s, a, v1, cardinality=None)))
    elif cat == "change_unapplied": rel += [rem(txt(v1), P(s, a, v1)), rem(f"{s} {a} changed to {v2}", P(s, a, v2, assertion="change"))]
    elif cat == "extracted_competitor":
        rel.append(rem(txt(v1), P(s, a, v1)))
        prop = contract.proposal_from_envelope(m._proposal(target_reference="memory:x", fact_text=txt(v2), operation="promotion", risk_class="low"))
        out = m.runtime.retain(prop, txt(v2), typed_write={"typed_proposition": T.typed_record(T.validate(P(s, a, v2)), "extracted:heldout@1")})
        assert out.committed; rel.append(out.fact_uuid)
    elif cat == "negated_competitor": rel += [rem(txt(v1), P(s, a, v1)), rem(f"{s} {a} is not {v1}", P(s, a, v1, negated=True))]
    elif cat == "hedged_change": rel += [rem(txt(v1), P(s, a, v1)), rem(f"{s} {a} may have switched to {v2}", P(s, a, v2, assertion="change", hedged=True))]
    elif cat == "attributed_competitor": rel += [rem(txt(v1), P(s, a, v1)), rem(f"Auditors report {s} {a} is {v2}", P(s, a, v2, attributed_to_other=True))]
    elif cat == "untyped_competitor": rel += [rem(txt(v1), P(s, a, v1)), rem(txt(v2))]
    elif cat == "expired_validity": rel.append(rem(txt(v1), P(s, a, v1), valid_from="2019-01-01", valid_until="2019-12-31"))
    elif cat == "paraphrase_unretrieved":
        rel.append(rem(txt(v1), P(s, a, v1))); rel.append(rem(f"Since Monday it is {v2}", P(s, a, v2)))
    elif cat == "budget_cap_conflict":
        rel += [rem(txt(v1), P(s, a, v1)), rem(txt(v1) + " again", P(s, a, v1)), rem(txt(v2) + " now", P(s, a, v2))]
        lexical = 2
    return m, rel, lexical

class Fixed:
    def __init__(self, lexical): self.lexical = lexical
    def plan(self, query, *, logical_memory_refs, available_routes):
        p = DeterministicRecallController().plan(query, logical_memory_refs=logical_memory_refs, available_routes=available_routes)
        from dataclasses import replace
        from agentmem_ref.recall_control import RecallRouteBudget
        return replace(p, route_budgets=tuple(RecallRouteBudget(b.route_id, self.lexical, anchor_limit=b.anchor_limit)
                                               if b.route_id == "lexical" else b for b in p.route_budgets))

def run():
    rows, obs_t, rec_t, obs_mem = [], [], [], []
    for cat, (gold, kind) in CATS.items():
        for i, (ent, vals) in enumerate(zip(ENTITIES, VALUES)):
            with tempfile.TemporaryDirectory() as d:
                m, rel, lexical = build(cat, ent, vals, d + "/m")
                try:
                    pl = ControlledRecallPlanner(m.runtime.adapter, controller=Fixed(lexical))
                    ctx = m._handle_recall_context()
                    q = f"{ent[0]} {ent[1]}"
                    t0 = time.perf_counter()
                    res = m.runtime.durable_runtime.run_governed_read(lambda: pl.recall(q, ctx))
                    rec_t.append(time.perf_counter() - t0)
                    row = {"cat": cat, "kind": kind, "gold_stop_safe": gold, "i": i,
                           "v6_stop": bool(res.evidence_sufficiency_met), "admitted": list(res.admitted)}
                    if HAS_OBS:
                        need = (CoverageNeed(T.typed_slot(*ent)),)
                        tracemalloc.start(); t0 = time.perf_counter()
                        rep = pl.observe_persisted_typed_coverage(res, ctx, needs=need)
                        obs_t.append(time.perf_counter() - t0)
                        obs_mem.append(tracemalloc.get_traced_memory()[1]); tracemalloc.stop()
                        row.update({"obs_stop": rep.continuation_proposal == "review_stop", "diagnosis": rep.diagnosis,
                                    "status": [v.status for v in rep.value_coherence],
                                    "support_refs": list(rep.need_support_refs[0][1]),
                                    "support_precision": (len(set(rep.need_support_refs[0][1]) & set(rel)) / len(rep.need_support_refs[0][1])
                                                          if rep.need_support_refs[0][1] else None)})
                    rows.append(row)
                finally:
                    m.close()
    med = lambda xs: round(statistics.median(xs) * 1e3, 4) if xs else None
    return {"has_observer": HAS_OBS, "rows": rows, "recall_ms_median": med(rec_t), "observe_ms_median": med(obs_t),
            "observe_ms_p95": round(sorted(obs_t)[int(0.95 * len(obs_t)) - 1] * 1e3, 4) if obs_t else None,
            "observe_peak_bytes_median": statistics.median(obs_mem) if obs_mem else None}

def summarize(out):
    rows = out["rows"]; s = {}
    def rate(pred, sel):
        sub = [r for r in rows if sel(r)]; return f"{sum(pred(r) for r in sub)}/{len(sub)}"
    for sig in ("v6_stop", "obs_stop"):
        if sig not in rows[0]: continue
        s[sig] = {"false_stop(unsafe cases)": rate(lambda r: r[sig], lambda r: not r["gold_stop_safe"]),
                  "correct_stop(safe cases)": rate(lambda r: r[sig], lambda r: r["gold_stop_safe"]),
                  "per_category_stop": {c: rate(lambda r: r[sig], lambda r, c=c: r["cat"] == c) for c in CATS}}
    if out["has_observer"]:
        s["value_competition_detected(conflict_single)"] = rate(lambda r: "competing_values_unresolved" in r["status"], lambda r: r["cat"] == "conflict_single")
        s["hidden_conflict_detected"] = rate(lambda r: not r["obs_stop"], lambda r: r["kind"] in ("conflict_hidden", "change_hidden"))
        s["coexistence_reported"] = rate(lambda r: "coexistence_possible" in r["status"], lambda r: r["kind"] == "coexist")
        s["change_flagged_unresolved"] = rate(lambda r: "change_assertion_unresolved" in r["status"], lambda r: r["kind"] in ("change", "change_hidden"))
        s["false_conflict(case_variant)"] = rate(lambda r: "competing_values_unresolved" in r["status"], lambda r: r["cat"] == "case_variant_agree")
        precs = [r["support_precision"] for r in rows if r["support_precision"] is not None]
        s["support_ref_precision"] = round(sum(precs) / len(precs), 4)
    for k in ("recall_ms_median", "observe_ms_median", "observe_ms_p95", "observe_peak_bytes_median"):
        s[k] = out[k]
    return s

if __name__ == "__main__":
    out = run(); out["summary"] = summarize(out)
    json.dump(out, open(sys.argv[1], "w"), indent=1)
    print(json.dumps(out["summary"], indent=1))
