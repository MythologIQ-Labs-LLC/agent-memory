"""Rank-stage attribution for multi-evidence recall through the public facade (#819 C7 diagnosis).

For each query and each needed memory (``must_include``) it records:
- the stage where the memory was lost:
  - ``not_discovered``: no route proposed it;
  - ``refused``: proposed, but governed admission refused it;
  - ``withheld``: admitted, but selection or the budget did not return it;
  - ``returned``;
- its rank among the admitted memories (the facade's ranked ``admitted`` list), its admitted-set
  BM25 score and its semantic route score, when the route proposed it;
- with ``--dense``, its cosine to the query under the pinned local model, and its rank among the
  admitted memories by cosine alone. This is diagnostic only and never fed back to the runtime.

Per query it also records:
- evidence-set coverage in the ranked admitted list at depths 3, 5 and 10 (all needed memories
  inside the top k);
- the returned set, extras (returned memories outside must ∪ may), and whether a newer
  conflicting statement is ranked ahead of the older one.

Only the store's own synthetic content in the querying scope is read. The uuid-to-ref mapping
comes from write receipts.

    python diagnose_c7.py <reference-dir> <off|required> <relevance_sufficient|ranked_prefix|default> c7-scenarios.json --output out.json [--dense]
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
parser.add_argument("selection", choices=("relevance_sufficient", "ranked_prefix", "default"))
parser.add_argument("scenarios", type=Path)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--dense", action="store_true")
parser.add_argument("--budget", type=int, default=10)
args = parser.parse_args()
sys.path.insert(0, str(args.reference))

from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.memory import procedural_memory as pm  # noqa: E402

TENANT, ACTOR = "tenant:c7-diag", "agent:c7-diag"
SUPPORTS_SELECTION = "return_selection" in inspect.signature(AgentMemory.recall).parameters


def evidence(scope):
    skill = pm.SkillArtifact(skill_id="skill:c7", version=1, purpose="apply a lifecycle change", scope=scope,
                             isolation_domain_refs=(TENANT, scope), required_isolation_domain_refs=(TENANT, scope),
                             procedure_markdown="# verify\nConfirm.", provenance_refs=("evidence:c7",))
    return pm.evidence_for(skill)


def open_(root, scope):
    kwargs = {} if args.semantic == "off" else {"semantic_retrieval": "required"}
    return AgentMemory.open(root, tenant=TENANT, actor_id=ACTOR, scope=scope, purpose="c7 diagnosis", **kwargs)


embed = None
if args.dense:
    from agentmem_ref.runtime.representation_onnx import OnnxSentenceEmbeddingProvider
    embed = OnnxSentenceEmbeddingProvider().embed


def cosine(a, b):
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b)) / (na * nb) if na and nb else 0.0


rows = []
for scenario in json.loads(args.scenarios.read_text())["scenarios"]:
    by_uuid, text_of = {}, {}
    with tempfile.TemporaryDirectory(prefix="c7-diag-") as tmp:
        root = Path(tmp)
        for op in scenario["operations"]:
            with open_(root, op["scope"]) as memory:
                if op["op"] == "remember":
                    kw = {"observed_at": op["observed_at"]} if op.get("observed_at") else {}
                    out = memory.remember(op["ref"], op["text"], **kw)
                elif op["op"] == "correct":
                    out = memory.correct(op["ref"], op["text"], evidence=evidence(op["scope"]))
                else:
                    out = memory.forget(op["ref"], evidence=evidence(op["scope"]))
            if out.get("committed") and out.get("fact_uuid"):
                by_uuid[str(out["fact_uuid"])] = op["ref"]
                text_of[op["ref"]] = op["text"]
        vectors = {ref: embed(text) for ref, text in text_of.items()} if embed else {}
        for query in scenario["queries"]:
            kwargs = {"budget": args.budget}
            if args.selection != "default" and SUPPORTS_SELECTION:
                kwargs["return_selection"] = args.selection
            with open_(root, query["scope"]) as memory:
                started = time.perf_counter()
                result = memory.recall(query["query"], **kwargs)
                ms = (time.perf_counter() - started) * 1000
            ref = lambda u: by_uuid.get(str(u), str(u))  # noqa: E731
            cands = [ref(u) for u in result.get("candidates") or []]
            ranked = [ref(u) for u in result.get("admitted") or []]
            returned = [ref(u) for u in result.get("returned") or []]
            admissions = {ref(u): d for u, d in (result.get("admissions") or {}).items()}
            expect = query["expect"]
            must, may = expect.get("must_include") or [], set(expect.get("may_include") or [])
            qv = embed(query["query"]) if embed else None
            dense_order = sorted(ranked, key=lambda r: (-cosine(qv, vectors[r]), r)) if embed else []
            needed = {}
            for r in must:
                d = admissions.get(r) or {}
                ev = d.get("ranking_evidence") or {}
                needed[r] = {
                    "stage": ("returned" if r in returned else "withheld" if r in ranked
                              else "refused" if r in cands else "not_discovered"),
                    "rank": ranked.index(r) + 1 if r in ranked else None,
                    "bm25": ev.get("lexical_relevance_score"),
                    "corroboration": ev.get("route_corroboration_count"),
                    "semantic_route": (ev.get("subordinate_route_scores") or {}).get("semantic_vector"),
                    "ordered_before_next_by": ev.get("ordered_before_next_by"),
                    "cosine": round(cosine(qv, vectors[r]), 3) if embed and r in vectors else None,
                    "dense_rank": dense_order.index(r) + 1 if embed and r in dense_order else None,
                }
            cover = {f"@{k}": bool(must) and all(r in ranked[:k] for r in must) for k in (3, 5, 10)}
            conflict = None
            if query["kind"] == "conflict" and must and may:
                newer, older = must[0], sorted(may)[0]
                if newer in ranked and older in ranked:
                    conflict = ranked.index(newer) < ranked.index(older)
            rows.append({
                "scenario": scenario["id"], "id": query["id"], "kind": query["kind"], "query": query["query"],
                "needed": needed, "coverage": cover, "admitted_count": len(ranked),
                "top10": ranked[:10], "returned": returned,
                "extra": [r for r in returned if r not in must and r not in may],
                "passed": all(r in returned for r in must) and all(r in must or r in may for r in returned),
                "newer_first": conflict, "recall_ms": round(ms, 2),
                # every admitted memory's BM25, shared-evidence route score and cosine (offline feasibility only)
                "admitted_scores": [[r, (admissions.get(r, {}).get("ranking_evidence") or {}).get("lexical_relevance_score"),
                                     ((admissions.get(r, {}).get("ranking_evidence") or {}).get("route_scores") or {}).get("shared_evidence_neighbor"),
                                     round(cosine(qv, vectors[r]), 4) if embed and r in vectors else None]
                                    for r in ranked],
            })

summary = {"queries": len(rows), "strict": sum(r["passed"] for r in rows)}
stages = [n["stage"] for r in rows for n in r["needed"].values()]
summary["needed"] = len(stages)
for s in ("returned", "withheld", "refused", "not_discovered"):
    summary[s] = stages.count(s)
summary["extra"] = sum(len(r["extra"]) for r in rows)
multi = [r for r in rows if r["needed"]]
for k in ("@3", "@5", "@10"):
    summary[f"coverage{k}"] = sum(r["coverage"][k] for r in multi)
summary["coverage_of"] = len(multi)
ranks = [n["rank"] for r in rows for n in r["needed"].values() if n["rank"]]
summary["needed_rank_le5"] = sum(1 for x in ranks if x <= 5)
summary["needed_rank_6_10"] = sum(1 for x in ranks if 6 <= x <= 10)
summary["needed_rank_gt10"] = sum(1 for x in ranks if x > 10)
if embed:
    dr = [n["dense_rank"] for r in rows for n in r["needed"].values() if n["dense_rank"]]
    summary["needed_dense_rank_le5"] = sum(1 for x in dr if x <= 5)
summary["newer_first"] = [r["newer_first"] for r in rows if r["kind"] == "conflict"].count(True)
summary["abstention_returning"] = sum(1 for r in rows if not r["needed"] and r["returned"])
lat = sorted(r["recall_ms"] for r in rows)
summary["recall_p50_ms"] = lat[len(lat) // 2]
args.output.write_text(json.dumps({"reference": str(args.reference), "semantic": args.semantic,
                                   "selection": args.selection, "summary": summary, "rows": rows}, indent=1))
print(args.semantic, args.selection, json.dumps(summary))
