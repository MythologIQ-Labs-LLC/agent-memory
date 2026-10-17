"""Selection-stage attribution through the public facade (#819 C9; C8's harness plus selection records).

For each query and each needed memory (``must_include``) it records the C8 fields (stage, rank,
BM25, cosine, dense rank) and, from the facade's own ``admissions[ref].return_selection`` record,
the selection basis and relative content relevance. For every admitted memory in the fused top
``budget`` it records whether selection withheld it, and whether it is needed, allowed (may) or
neither. The 3.4.0 base order is captured by wrapping ``AgentMemory._select_returned``
(diagnostic only; the wrapper calls the original unchanged).

    python diagnose_c9.py <reference-dir> <off|required> <relevance_sufficient|ranked_prefix> scenarios.json --output out.json [--budget 5]
"""

from __future__ import annotations

import argparse
import inspect
import json
import math
import sys
import tempfile
import time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("reference", type=Path)
parser.add_argument("semantic", choices=("off", "required"))
parser.add_argument("selection", choices=("relevance_sufficient", "ranked_prefix"))
parser.add_argument("scenarios", type=Path)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--budget", type=int, default=5)
args = parser.parse_args()
sys.path.insert(0, str(args.reference))

from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.memory import procedural_memory as pm  # noqa: E402

TENANT, ACTOR = "tenant:c9-diag", "agent:c9-diag"
SUPPORTS_SELECTION = "return_selection" in inspect.signature(AgentMemory.recall).parameters
captured: dict = {}
if hasattr(AgentMemory, "_select_returned"):
    original = AgentMemory._select_returned

    def wrapped(self, query, intent, result, admissions, k):
        captured["base"] = list(getattr(result, "base_ranked_admitted", None) or result.ranked_admitted)
        return original(self, query, intent, result, admissions, k)

    AgentMemory._select_returned = wrapped


def evidence(scope):
    skill = pm.SkillArtifact(skill_id="skill:c9", version=1, purpose="apply a lifecycle change", scope=scope,
                             isolation_domain_refs=(TENANT, scope), required_isolation_domain_refs=(TENANT, scope),
                             procedure_markdown="# verify\nConfirm.", provenance_refs=("evidence:c9",))
    return pm.evidence_for(skill)


def open_(root, scope):
    kwargs = {} if args.semantic == "off" else {"semantic_retrieval": "required"}
    return AgentMemory.open(root, tenant=TENANT, actor_id=ACTOR, scope=scope, purpose="c9 diagnosis", **kwargs)


embed = None
if args.semantic == "required":
    from agentmem_ref.runtime.representation_onnx import OnnxSentenceEmbeddingProvider
    embed = OnnxSentenceEmbeddingProvider().embed


def cosine(a, b):
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b)) / (na * nb) if na and nb else 0.0


rows = []
for scenario in json.loads(args.scenarios.read_text())["scenarios"]:
    by_uuid, text_of, scope_of = {}, {}, {}
    with tempfile.TemporaryDirectory(prefix="c9-diag-") as tmp:
        root = Path(tmp)
        for op in scenario["operations"]:
            with open_(root, op["scope"]) as memory:
                if op["op"] in ("correct", "forget"):
                    # the earlier fact keeps a distinct name, so returning it is visible as a violation
                    suffix = "#superseded" if op["op"] == "correct" else "#forgotten"
                    for uuid, name in list(by_uuid.items()):
                        if name == op["ref"]:
                            by_uuid[uuid] = name + suffix
                if op["op"] == "remember":
                    kw = {k: op[k] for k in ("observed_at", "valid_from", "valid_until") if op.get(k)}
                    out = memory.remember(op["ref"], op["text"], **kw)
                elif op["op"] == "correct":
                    out = memory.correct(op["ref"], op["text"], evidence=evidence(op["scope"]))
                else:
                    out = memory.forget(op["ref"], evidence=evidence(op["scope"]))
            if out.get("committed") and out.get("fact_uuid"):
                by_uuid[str(out["fact_uuid"])] = op["ref"]
                text_of[op["ref"]] = op["text"]
                scope_of[op["ref"]] = op["scope"]
        vectors = {ref: embed(text) for ref, text in text_of.items()} if embed else {}
        for query in scenario["queries"]:
            kwargs = {"budget": args.budget}
            if SUPPORTS_SELECTION:
                kwargs["return_selection"] = args.selection
            if query.get("temporal_intent"):
                kwargs["temporal_intent"] = query["temporal_intent"]
            if query.get("reference_time"):
                kwargs["reference_time"] = query["reference_time"]
            captured.clear()
            with open_(root, query["scope"]) as memory:
                started = time.perf_counter()
                result = memory.recall(query["query"], **kwargs)
                ms = (time.perf_counter() - started) * 1000
            ref = lambda u: by_uuid.get(str(u), str(u))  # noqa: E731
            cands = [ref(u) for u in result.get("candidates") or []]
            ranked = [ref(u) for u in result.get("admitted") or []]
            base = [ref(u) for u in captured.get("base", [])] or ranked
            returned = [ref(u) for u in result.get("returned") or []]
            admissions = {ref(u): d for u, d in (result.get("admissions") or {}).items()}
            expect = query["expect"]
            must, may = expect.get("must_include") or [], set(expect.get("may_include") or [])
            # Earlier sets write {"ref", "reason"}; only lifecycle and scope reasons are safety, the
            # others (topical distractor, adversarial stuffing) are precision and reported separately.
            excluded = {e["ref"] if isinstance(e, dict) else e for e in expect.get("must_exclude") or []}
            safety_excluded = {e["ref"] if isinstance(e, dict) else e for e in expect.get("must_exclude") or []
                               if not isinstance(e, dict) or e.get("reason") not in ("topical_distractor", "adversarial")}
            qv = embed(query["query"]) if embed else None
            cos = {r: round(cosine(qv, vectors[r]), 4) for r in ranked if r in vectors} if embed else {}
            dense_order = sorted(ranked, key=lambda r: (-cos.get(r, 0.0), r)) if embed else []

            def info(r):
                d = admissions.get(r) or {}
                ev = d.get("ranking_evidence") or {}
                sel = d.get("return_selection") or {}
                return {
                    "stage": ("returned" if r in returned else "withheld" if r in ranked
                              else "refused" if r in cands else "not_discovered"),
                    "rank": ranked.index(r) + 1 if r in ranked else None,
                    "base_rank": base.index(r) + 1 if r in base else None,
                    "basis": sel.get("basis"),
                    "relative_to_best": sel.get("relative_to_best"),
                    "content_relevance": sel.get("content_relevance"),
                    "bm25": ev.get("lexical_relevance_score"),
                    "routes": sorted({h.get("route_id") for h in d.get("route_provenance") or []}),
                    "cosine": cos.get(r),
                    "dense_rank": dense_order.index(r) + 1 if r in dense_order else None,
                    "role": "must" if r in must else "may" if r in may else "other",
                }

            rows.append({
                "scenario": scenario["id"], "id": query["id"], "kind": query.get("kind", "unlabelled"),
                "query": query["query"], "requirement": next(iter((admissions.get(r) or {}).get("return_selection", {}).get("requirement") for r in ranked), None) if ranked else None,
                "needed": {r: info(r) for r in must},
                "top_budget": {r: info(r) for r in ranked[:args.budget]},
                "admitted_count": len(ranked), "returned": returned,
                "extra": [r for r in returned if r not in must and r not in may],
                "violations": [r for r in returned if r in safety_excluded
                               or "#" in r or scope_of.get(r, query["scope"]) != query["scope"]],
                "excluded_returned": [r for r in returned if r in excluded],
                "passed": all(r in returned for r in must) and all(r in must or r in may for r in returned),
                "recall_ms": round(ms, 2),
            })

stages = [n["stage"] for r in rows for n in r["needed"].values()]
summary = {"queries": len(rows), "strict": sum(r["passed"] for r in rows), "needed": len(stages)}
for s in ("returned", "withheld", "refused", "not_discovered"):
    summary[s] = stages.count(s)
summary["needed_in_top_budget"] = sum(1 for r in rows for n in r["needed"] if n in r["top_budget"])
summary["needed_in_top_budget_withheld"] = sum(1 for r in rows for n in r["needed"] if n in r["top_budget"] and n not in r["returned"])
summary["extra"] = sum(len(r["extra"]) for r in rows)
summary["safety_violations"] = sum(len(r["violations"]) for r in rows)
summary["excluded_returned"] = sum(len(r["excluded_returned"]) for r in rows)
summary["no_answer_returning"] = sum(1 for r in rows if not r["needed"] and r["returned"])
summary["recall"] = round(summary["returned"] / summary["needed"], 4) if summary["needed"] else None
lat = sorted(r["recall_ms"] for r in rows)
summary["recall_p50_ms"] = lat[len(lat) // 2]
args.output.write_text(json.dumps({"reference": str(args.reference), "semantic": args.semantic, "budget": args.budget,
                                   "selection": args.selection, "summary": summary, "rows": rows}, indent=1))
print(args.semantic, args.selection, json.dumps(summary))
