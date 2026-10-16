"""Reviewer harness: run reviewer-authored scenarios through one tree's public facade.

usage: python harness.py <tree> <scenarios.json> <off|required> <ranked_prefix|relevance_sufficient> <out.json> [--fresh] [--budget N]
Default: one long-lived handle per (scenario, scope) for all queries (exercises cross-recall caches).
--fresh: a new handle per query.
"""
import json, sys, tempfile, time
from pathlib import Path

tree = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(tree / "reference"))
from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.memory import procedural_memory as pm  # noqa: E402

scen_path, semantic, selection, out_path = Path(sys.argv[2]), sys.argv[3], sys.argv[4], Path(sys.argv[5])
fresh = "--fresh" in sys.argv
budget = int(sys.argv[sys.argv.index("--budget") + 1]) if "--budget" in sys.argv else 10
TENANT, ACTOR = "tenant:rv", "agent:rv"


def evidence(scope):
    skill = pm.SkillArtifact(skill_id="skill:rv", version=1, purpose="apply a lifecycle change", scope=scope,
                             isolation_domain_refs=(TENANT, scope), required_isolation_domain_refs=(TENANT, scope),
                             procedure_markdown="# verify\nConfirm.", provenance_refs=("evidence:rv",))
    return pm.evidence_for(skill)


def open_(root, scope):
    kw = {} if semantic == "off" else {"semantic_retrieval": semantic}
    return AgentMemory.open(root, tenant=TENANT, actor_id=ACTOR, scope=scope, purpose="review", **kw)


rows = []
for sc in json.loads(scen_path.read_text())["scenarios"]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        by_uuid = {}
        for op in sc["operations"]:
            with open_(root, op["scope"]) as m:
                if op["op"] == "remember":
                    kw = {k: op[k] for k in ("observed_at", "valid_from", "valid_until") if op.get(k)}
                    o = m.remember(op["ref"], op["text"], **kw)
                elif op["op"] == "correct":
                    o = m.correct(op["ref"], op["text"], evidence=evidence(op["scope"]))
                else:
                    o = m.forget(op["ref"], evidence=evidence(op["scope"]))
            if o.get("committed") and o.get("fact_uuid"):
                key = op["ref"] + ("#corrected" if op["op"] == "correct" else "")
                by_uuid[str(o["fact_uuid"])] = (op["scope"], key)
            elif not o.get("committed"):
                print("OP FAILED", sc["id"], op, o.get("refusal"), file=sys.stderr)
        handles = {}
        for q in sc["queries"]:
            kw = {"budget": budget, "return_selection": selection}
            if q.get("temporal_intent"):
                kw["temporal_intent"] = q["temporal_intent"]
            if fresh:
                m = open_(root, q["scope"])
            else:
                m = handles.get(q["scope"]) or handles.setdefault(q["scope"], open_(root, q["scope"]))
            t0 = time.perf_counter()
            r = m.recall(q["query"], **kw)
            ms = (time.perf_counter() - t0) * 1000
            if fresh:
                m.close()

            def name(u):
                s, ref = by_uuid.get(str(u), ("?", "unmapped:" + str(u)[:8]))
                return ref if s == q["scope"] else f"{s}#{ref}"
            ranked = [name(u) for u in r["admitted"]]
            returned = [name(u) for u in r["returned"]]
            adm = {name(u): d for u, d in r["admissions"].items()}
            must = q["expect"].get("must_include") or []
            may = set(q["expect"].get("may_include") or [])
            ev = {ref: (adm.get(ref) or {}).get("ranking_evidence") or {} for ref in ranked}
            fusion_status = sorted({str((e.get("fusion") or {}).get("status")) for e in ev.values()})
            pair = None
            if q["kind"] in ("declared_open", "declared_closed", "as_of_open", "historical", "conflict") and must and may:
                pref, other = must[0], sorted(may)[0]
                pair = {"preferred": pref, "other": other,
                        "ranks": [ranked.index(x) + 1 if x in ranked else None for x in (pref, other)],
                        "applicability": [ev.get(x, {}).get("temporal_applicability") for x in (pref, other)],
                        "ordered_by": [ev.get(x, {}).get("ordered_before_next_by") for x in (pref, other)]}
                pair["preferred_first"] = (None if None in pair["ranks"] else pair["ranks"][0] < pair["ranks"][1])
            planted = q.get("planted") or []
            rows.append({
                "scenario": sc["id"], "id": q["id"], "kind": q["kind"], "query": q["query"],
                "ranked": ranked, "returned": returned, "ms": round(ms, 2), "fusion_status": fusion_status,
                "policy_versions": sorted({str(e.get("policy_version")) for e in ev.values()}),
                "needed_rank": {x: (ranked.index(x) + 1 if x in ranked else None) for x in must},
                "needed_returned": {x: x in returned for x in must},
                "cover": {f"@{k}": bool(must) and all(x in ranked[:k] for x in must) for k in (1, 3, 5, 10)},
                "planted_rank": {x: (ranked.index(x) + 1 if x in ranked else None) for x in planted},
                "extras_returned": [x for x in returned if x not in must and x not in may],
                "nonanswers_above_first_needed": (min([ranked.index(x) for x in must if x in ranked] or [len(ranked)])
                                                  if must else None),
                "passed": all(x in returned for x in must) and all(x in must or x in may for x in returned),
                "forbidden_seen": [x for x in ranked + returned + [name(u) for u in r["candidates"]]
                                   if x in (sc.get("forbidden") or []) or x.startswith("user:rv-other#")],
                "pair": pair,
                "top5_fusion": [[x, (ev[x].get("fusion") or {}).get("fused_score"),
                                 (ev[x].get("fusion") or {}).get("lexical_rank"), (ev[x].get("fusion") or {}).get("dense_rank"),
                                 (ev[x].get("fusion") or {}).get("dense_similarity"), ev[x].get("lexical_relevance_score")]
                                for x in ranked[:5]],
            })
        for h in handles.values():
            h.close()
out_path.write_text(json.dumps({"tree": str(tree), "semantic": semantic, "selection": selection, "fresh": fresh,
                                "budget": budget, "rows": rows}, indent=1))
print(out_path.name, len(rows), "rows")
