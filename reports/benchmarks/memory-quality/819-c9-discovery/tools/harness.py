#!/usr/bin/env python3
"""Stage-decomposing scenario harness (#819 discovery lane). Evaluation-only.

    harness.py <runtime_root> <scenarios.json> <out.json> [--sem off|required] [--rs relevance_sufficient|ranked_prefix]

Same operations and scoring as scripts/run_memory_quality_scenarios.py (budget 10). Expectations are
read only after recall, to classify each needed (must_include) memory into the stage that lost it:
  never_discovered      not in result.candidates
  proposed_excluded     candidate, refused by governed admission
  admitted_withheld     admitted, not selected as sufficient
  ranked_below_budget   selected (or admitted under ranked_prefix) but beyond the budget
  returned
"""
import argparse, hashlib, json, subprocess, sys, tempfile, time
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("root"); ap.add_argument("scenarios"); ap.add_argument("out")
ap.add_argument("--sem", default="off"); ap.add_argument("--rs", default=None)
a = ap.parse_args()
ROOT = Path(a.root).resolve()
sys.path.insert(0, str(ROOT / "reference")); sys.path.insert(0, str(ROOT / "scripts"))
import run_memory_quality_scenarios as R  # noqa: E402
from agentmem_ref import AgentMemory  # noqa: E402
if a.sem != "off":  # one verified provider per process (load time only; numerics unchanged)
    from agentmem_ref.runtime import representation_onnx as _ro
    _Real, _cache = _ro.OnnxSentenceEmbeddingProvider, {}
    def _provider(model_dir=None):
        if model_dir not in _cache:
            _cache[model_dir] = _Real(model_dir)
        return _cache[model_dir]
    _ro.OnnxSentenceEmbeddingProvider = _provider

def _open(root, scope):
    return AgentMemory.open(root, tenant=R.TENANT, actor_id=R.ACTOR, scope=scope, purpose="memory quality scenario",
                            semantic_retrieval=a.sem)

def run(scenario):
    by_uuid, rows = {}, []
    with tempfile.TemporaryDirectory(prefix="amq-") as tmp:
        root = Path(tmp)
        for op in scenario["operations"]:
            scope, ref = op["scope"], op["ref"]
            with _open(root, scope) as m:
                if op["op"] == "remember":
                    kw = {"observed_at": op["observed_at"]} if op.get("observed_at") else {}
                    for key in ("source_ref", "proposition"):
                        if op.get(key):
                            kw[key] = op[key]
                    out = m.remember(ref, op["text"], **kw)
                elif op["op"] == "correct":
                    out = m.correct(ref, op["text"], evidence=R._evidence(scope))
                else:
                    out = m.forget(ref, evidence=R._evidence(scope))
            if out.get("committed") and out.get("fact_uuid"):
                if op["op"] == "correct":  # an earlier version of a corrected memory is not that memory
                    for u, sr in list(by_uuid.items()):
                        if sr == (scope, ref):
                            by_uuid[u] = (scope, ref + "@superseded")
                by_uuid[str(out["fact_uuid"])] = (scope, ref)
        for q in scenario["queries"]:
            kw = {"budget": R.BUDGET}
            if a.rs:
                kw["return_selection"] = a.rs
            t = time.perf_counter()
            with _open(root, q["scope"]) as m:
                rec = m.recall(q["query"], **kw)
            ms = (time.perf_counter() - t) * 1000
            def name(u):
                s, r = by_uuid.get(str(u), ("?", f"unmapped:{u}"))
                return r if s == q["scope"] else f"{s}#{r}"
            returned = [name(u) for u in rec.get("returned") or []]
            row = R.score(q, returned, len(rec.get("admitted") or []), ms)
            cands = {name(u): u for u in rec.get("candidates") or []}
            admitted = [name(u) for u in rec.get("admitted") or []]
            adm = rec.get("admissions") or {}
            sel = {name(u) for u, d in adm.items() if (d.get("return_selection") or {}).get("sufficient")}
            stages = {}
            for need in dict.fromkeys(q["expect"].get("must_include") or []):
                if need in returned: st = "returned"
                elif need not in cands: st = "never_discovered"
                elif need not in admitted: st = "proposed_excluded"
                elif a.rs != "ranked_prefix" and need not in sel: st = "admitted_withheld"
                else: st = "ranked_below_budget"
                d = adm.get(cands.get(need), {}) if need in cands else {}
                stages[need] = {"stage": st, "routes": sorted({h["route_id"] for h in d.get("route_provenance", [])}),
                                "rank": d.get("rank_position"), "refusal": d.get("refusal")}
            sem = [d for d in adm.values() if any(h["route_id"] == "semantic_vector" for h in d.get("route_provenance", []))]
            row["superseded_returned"] = sum(1 for x in returned if x.endswith("@superseded"))
            row.update(stages=stages, candidate_count=len(cands), category=scenario.get("category"),
                       sem_hits=len(sem), sem_refused=sum(1 for d in sem if d.get("refusal")),
                       refusals=sorted(str(d.get("refusal")) for d in sem if d.get("refusal")))
            rows.append(row)
    return rows

data = json.loads(Path(a.scenarios).read_bytes())
scen = data["scenarios"] if isinstance(data, dict) else data
rows = [r for s in scen for r in run(s)]
rev = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
Path(a.out).write_text(json.dumps({"revision": rev, "sem": a.sem, "rs": a.rs,
                                   "cohort_sha256": hashlib.sha256(Path(a.scenarios).read_bytes()).hexdigest(),
                                   "rows": rows}, indent=1, sort_keys=True))
from collections import Counter
c = Counter(st["stage"] for r in rows for st in r["stages"].values())
need = sum(c.values())
print(f"{Path(a.scenarios).name} rev={rev[:8]} sem={a.sem} rs={a.rs} q={len(rows)} strict={sum(r['passed'] for r in rows)} "
      f"needed={need} {dict(c)} extras={sum(r['returned_count'] - sum(1 for x in r['returned'] if x in r['stages']) for r in rows)} "
      f"cands_mean={sum(r['candidate_count'] for r in rows)/len(rows):.1f} viol={sum(len(r['safety_violations']) for r in rows)} superseded_returned={sum(r['superseded_returned'] for r in rows)} "
      f"sem_hits={sum(r['sem_hits'] for r in rows)} sem_refused={sum(r['sem_refused'] for r in rows)}")
