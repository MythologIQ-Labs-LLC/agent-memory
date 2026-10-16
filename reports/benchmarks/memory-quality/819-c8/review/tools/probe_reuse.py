"""Similarity-reuse correctness probe for C8 (real pinned model).

usage: python probe_reuse.py <c8-tree>

1. bit-identity: after a recall, every reused cosine (retriever._last_scores) equals, with ==, a
   recomputation through similarities() with the cache cleared, and the fusion evidence's
   dense_similarity equals round(recomputed, 6).
2. long-lived handle vs fresh handle: the same sequence of recalls with writes, forgets,
   corrections, scope overrides and intent changes between them gives identical ranked
   admitted lists and identical fusion evidence on a long-lived handle and on a fresh handle per recall.
3. same query string, different temporal intents / scopes / selections back to back.
4. what _last_scores holds after a recall: does it contain non-admitted (forgotten, superseded,
   other-scope) facts? Is any of it exposed in the public result?
"""
import json, sys, tempfile
from pathlib import Path

tree = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(tree / "reference"))
from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.memory import procedural_memory as pm  # noqa: E402

TENANT, ACTOR, SCOPE, OTHER = "tenant:rvr", "agent:rvr", "user:rvr", "user:rvr-other"


def evidence(scope):
    skill = pm.SkillArtifact(skill_id="skill:rvr", version=1, purpose="apply a lifecycle change", scope=scope,
                             isolation_domain_refs=(TENANT, scope), required_isolation_domain_refs=(TENANT, scope),
                             procedure_markdown="# verify\nConfirm.", provenance_refs=("evidence:rvr",))
    return pm.evidence_for(skill)


def open_(root, scope=SCOPE):
    return AgentMemory.open(root, tenant=TENANT, actor_id=ACTOR, scope=scope, purpose="rvr", semantic_retrieval="required")


FACTS = {
 "memory:a": "The spare house key is under the blue plant pot.",
 "memory:b": "Our house insurance is with Aviva and renews in May.",
 "memory:c": "The plumber, Gavin, fixed the leaking kitchen tap.",
 "memory:d": "We keep the car keys on the hook by the front door.",
 "memory:e": "The key safe code for Grandma's house is 4471.",
 "memory:f": "The garage door remote needs a new battery.",
 "memory:g": "Ella's school bag is always by the stairs.",
 "memory:h": "The shed padlock key is in the kitchen drawer.",
}
report = {}
with tempfile.TemporaryDirectory() as tmp:
    with open_(tmp, OTHER) as o:
        o.remember("memory:o1", "The neighbours keep our spare house key for emergencies.")
    m = open_(tmp)
    uuid = {}
    for ref, text in FACTS.items():
        uuid[ref] = m.remember(ref, text)["fact_uuid"]
    name = {v: k for k, v in uuid.items()}
    retr = m._semantic["retriever"]
    sub = m.runtime.adapter.checkpoint_substrate()

    # 1. bit identity
    q = "Where is the spare house key?"
    bit = {}
    for selection in ("ranked_prefix", "relevance_sufficient"):
        r = m.recall(q, budget=10, return_selection=selection)
        query, reused = retr._last_scores
        admitted = r["admitted"]
        saved = retr._last_scores
        retr._last_scores = None
        recomputed = retr.similarities(q, [sub.get_fact(u) for u in admitted])
        retr._last_scores = saved
        # also recompute from scratch without the store (pure provider) and with a new provider instance
        exact = all(reused[u] == recomputed[u] for u in admitted)
        ev = {u: r["admissions"][u]["ranking_evidence"]["fusion"]["dense_similarity"] for u in admitted}
        rounded = all(ev[u] == round(recomputed[u], 6) for u in admitted)
        bit[selection] = {"admitted": len(admitted), "scanned": len(reused), "reused_eq_recomputed": exact,
                          "evidence_eq_round6": rounded,
                          "non_admitted_in_last_scores": sorted(name.get(u, u) for u in set(reused) - set(admitted))}
    report["1_bit_identity"] = bit

    # 4. contents of _last_scores after lifecycle changes
    m.forget("memory:e", evidence=evidence(SCOPE))
    c = m.correct("memory:h", "The shed padlock key now hangs inside the shed door.", evidence=evidence(SCOPE))
    uuid["memory:h#corrected"] = c["fact_uuid"]
    name = {v: k for k, v in uuid.items()}
    exposure = {}
    for selection in ("ranked_prefix", "relevance_sufficient"):
        r = m.recall(q, budget=10, return_selection=selection)
        held = retr._last_scores[1]
        blob = json.dumps(r)
        exposure[selection] = {
            "last_scores_refs": sorted(name.get(u, "OTHER-SCOPE/unknown:" + u[:8]) for u in held),
            "admitted": sorted(name.get(u, u) for u in r["admitted"]),
            "candidates": sorted(name.get(u, u) for u in r["candidates"]),
            "forgotten_uuid_in_result": uuid["memory:e"] in blob,
            "forgotten_text_in_result": "4471" in blob,
            "superseded_text_in_result": "kitchen drawer" in blob,
            "other_scope_text_in_result": "neighbours keep" in blob,
            "fusion_records_only_admitted": all(("fusion" in (d.get("ranking_evidence") or {})) == (u in r["admitted"])
                                                for u, d in r["admissions"].items()),
            "refused_candidate_route_scores": {name.get(u, u): [h.get("raw_score") for h in d.get("route_provenance", [])
                                                                 if h.get("route_id") == "semantic_vector"]
                                               for u, d in r["admissions"].items() if u not in r["admitted"]},
        }
    report["4_exposure_after_forget_correct"] = exposure

    # 2/3. long-lived vs fresh handle across a sequence with writes in between
    seq = [
        ("recall", q, None, "ranked_prefix", None),
        ("recall", q, {"mode": "historical", "target_start": "2020-01-01T00:00:00Z", "target_end": "2027-01-01T00:00:00Z"}, "ranked_prefix", None),
        ("recall", q, {"mode": "current"}, "relevance_sufficient", None),
        ("recall", q, None, "ranked_prefix", OTHER),          # same query string, other scope via project_ref
        ("write", "memory:i", "The spare key for the house is now with Pat next door."),
        ("recall", q, None, "ranked_prefix", None),
        ("forget", "memory:a"),
        ("recall", q, None, "ranked_prefix", None),
        ("recall", "Who fixed the tap?", None, "ranked_prefix", None),
        ("recall", q, None, "relevance_sufficient", None),
    ]
    m.close()

def run_sequence(root, fresh):
    outs = []
    h = None if fresh else open_(root)
    def handle():
        return open_(root) if fresh else h
    for ref, text in FACTS.items():
        x = handle(); x.remember(ref, text); fresh and x.close()
    for step in seq:
        x = handle()
        if step[0] == "write":
            x.remember(step[1], step[2])
        elif step[0] == "forget":
            x.forget(step[1], evidence=evidence(SCOPE))
        else:
            _, qq, intent, sel, proj = step
            kw = {"budget": 10, "return_selection": sel, "reference_time": "2026-10-16T00:00:00Z"}
            if intent: kw["temporal_intent"] = intent
            if proj: kw["project_ref"] = proj
            try:
                res = x.recall(qq, **kw)
                outs.append((res["admitted"], {u: (res["admissions"][u]["ranking_evidence"].get("fusion") or {}).get("dense_similarity")
                                               for u in res["admitted"]}, res["returned"]))
            except Exception as exc:
                outs.append(("error", type(exc).__name__, str(exc)[:120]))
        if fresh: x.close()
    if h: h.close()
    return outs

with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2:
    live_out, fresh_out = run_sequence(t1, False), run_sequence(t2, True)
    report["2_live_vs_fresh"] = {"steps": len(live_out), "identical": live_out == fresh_out,
                                 "diffs": [i for i, (a, b) in enumerate(zip(live_out, fresh_out)) if a != b],
                                 "other_scope_step": str(live_out[3])[:200]}
print(json.dumps(report, indent=1))
