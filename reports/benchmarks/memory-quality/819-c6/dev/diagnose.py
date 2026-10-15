"""Stage attribution of recall failures through the public facade (#819 C6 diagnosis).

For each query and each needed memory (``must_include``) it records where the memory was lost:

* ``not_discovered``: no route proposed it (not among the caller-visible candidates);
* ``refused``: proposed, but governed admission refused it (refusal reason recorded);
* ``withheld``: admitted, but return selection or the budget did not return it;
* ``returned``.

It also records returned memories that the question does not need (``extra``: not in
must/may), the routes that proposed each needed memory, and recall latency. When the pinned
local model is available it records each needed memory's dense rank among all in-scope
memories of its store (diagnostic only: what a dense discovery route *could* reach).

Only the store's own synthetic content in the querying scope is read; other-scope memories are
never printed. ``uuid -> ref`` mapping comes from the write receipts.

    python diagnose.py <reference-dir> <config: default|ranked_prefix|semantic> diag-scenarios.json --output out.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
import time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("reference", type=Path)
parser.add_argument("config", choices=("default", "ranked_prefix", "semantic"))
parser.add_argument("scenarios", type=Path)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--dense-ranks", action="store_true")
args = parser.parse_args()
sys.path.insert(0, str(args.reference))

from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.memory import procedural_memory as pm  # noqa: E402

TENANT, ACTOR, BUDGET = "tenant:c6-diag", "agent:c6-diag", 10


def evidence(scope):
    skill = pm.SkillArtifact(skill_id="skill:c6", version=1, purpose="apply a lifecycle change", scope=scope,
                             isolation_domain_refs=(TENANT, scope), required_isolation_domain_refs=(TENANT, scope),
                             procedure_markdown="# verify\nConfirm.", provenance_refs=("evidence:c6",))
    return pm.evidence_for(skill)


def open_(root, scope):
    kwargs = {"semantic_retrieval": "required"} if args.config == "semantic" else {}
    return AgentMemory.open(root, tenant=TENANT, actor_id=ACTOR, scope=scope, purpose="c6 diagnosis", **kwargs)


embed = None
if args.dense_ranks:
    from agentmem_ref.runtime.representation_onnx import OnnxSentenceEmbeddingProvider
    embed = OnnxSentenceEmbeddingProvider().embed


def cosine(a, b):
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b)) / (na * nb) if na and nb else 0.0


rows = []
cohort = json.loads(args.scenarios.read_text())["scenarios"]
for scenario in cohort:
    by_uuid, text_of, current = {}, {}, {}
    with tempfile.TemporaryDirectory(prefix="c6-diag-") as tmp:
        root = Path(tmp)
        for op in scenario["operations"]:
            with open_(root, op["scope"]) as memory:
                if op["op"] == "remember":
                    out = memory.remember(op["ref"], op["text"])
                elif op["op"] == "correct":
                    out = memory.correct(op["ref"], op["text"], evidence=evidence(op["scope"]))
                else:
                    out = memory.forget(op["ref"], evidence=evidence(op["scope"]))
            if out.get("committed") and out.get("fact_uuid"):
                by_uuid[str(out["fact_uuid"])] = (op["scope"], op["ref"])
                if op["op"] != "forget":
                    current[(op["scope"], op["ref"])] = op["text"]
        for query in scenario["queries"]:
            scope = query["scope"]
            ref_of = {u: (r if s == scope else f"{s}#{r}") for u, (s, r) in by_uuid.items()}
            started = time.perf_counter()
            with open_(root, scope) as memory:
                opened = time.perf_counter()
                result = memory.recall(query["query"], budget=BUDGET)
            recall_ms = (time.perf_counter() - opened) * 1000
            cands = {ref_of.get(u, u) for u in result.get("candidates") or []}
            admitted = {ref_of.get(u, u) for u in result.get("admitted") or []}
            returned = [ref_of.get(u, u) for u in result.get("returned") or []]
            refusals, routes = {}, {}
            for uuid, decision in (result.get("admissions") or {}).items():
                ref = ref_of.get(uuid, uuid)
                if decision.get("refusal"):
                    refusals[ref] = decision["refusal"]
                provenance = decision.get("route_provenance") or []
                routes[ref] = sorted({p.get("route_id") for p in provenance if isinstance(p, dict)} - {None})
            expect = query["expect"]
            must, may = expect.get("must_include") or [], set(expect.get("may_include") or [])
            stages = {}
            for ref in must:
                stages[ref] = ("returned" if ref in returned else "withheld" if ref in admitted
                               else "refused" if ref in cands else "not_discovered")
            dense = {}
            if embed is not None:
                pool = {r: t for (s, r), t in current.items() if s == scope}
                qv = embed(query["query"])
                ranked = sorted(pool, key=lambda r: -cosine(qv, embed(pool[r])))
                dense = {ref: {"rank": ranked.index(ref) + 1, "cosine": round(cosine(qv, embed(pool[ref])), 3)}
                         for ref in must if ref in pool}
            rows.append({
                "scenario": scenario["id"], "id": query["id"], "kind": query["kind"], "query": query["query"],
                "stages": stages, "refusals_of_needed": {r: refusals[r] for r in must if r in refusals},
                "routes_of_needed": {r: routes.get(r, []) for r in must},
                "returned": returned, "extra": [r for r in returned if r not in must and r not in may],
                "excluded_returned": [x["ref"] for x in expect.get("must_exclude") or [] if x["ref"] in returned],
                "candidates": len(cands), "admitted": len(admitted), "recall_ms": round(recall_ms, 2),
                "dense": dense,
            })

summary = {}
for row in rows:
    s = summary.setdefault(row["kind"], {"queries": 0, "needed": 0, "returned": 0, "withheld": 0, "refused": 0,
                                         "not_discovered": 0, "extra": 0, "excluded_returned": 0, "strict": 0})
    s["queries"] += 1
    for stage in row["stages"].values():
        s["needed"] += 1
        s[stage] += 1
    s["extra"] += len(row["extra"])
    s["excluded_returned"] += len(row["excluded_returned"])
    s["strict"] += int(all(v == "returned" for v in row["stages"].values()) and not row["extra"] and not row["excluded_returned"])
args.output.write_text(json.dumps({"config": args.config, "reference": str(args.reference), "summary": summary, "rows": rows}, indent=1))
tot = {k: sum(v[k] for v in summary.values()) for k in next(iter(summary.values()))}
print(args.config, json.dumps(tot))
for kind, s in sorted(summary.items()):
    print(f"  {kind:11s} {json.dumps(s)}")
