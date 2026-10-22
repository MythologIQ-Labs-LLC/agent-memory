"""Known AMB PrecisionMemBench 77-case diagnostic through the public context API, native scorer.

Arms: raw recall ids, default context, rejected lexical rule (post hoc), evidence_qualified,
and an FTS5 comparator over the same documents. Diagnostic/regression only: never lane evidence.
usage: amb_paired.py <amb_workspace> <runtime> <output.json>
"""
import copy, json, os, platform, statistics, subprocess, sys, tempfile, time, types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paired  # noqa: E402

workspace, runtime, output = map(Path, sys.argv[1:4])
for name, path in [("memory_bench", workspace / "amb/src/memory_bench"), ("memory_bench.dataset", workspace / "amb/src/memory_bench/dataset")]:
    module = types.ModuleType(name); module.__path__ = [str(path)]; sys.modules[name] = module
sys.path.insert(0, str(runtime / "reference"))
os.environ["PRECISIONMEMBENCH_DATA_PATH"] = str(workspace / "precisionmembench/fixtures")
for key in list(os.environ):
    if key.startswith(("AMB_", "OMB_", "AGENT_MEMORY_AMB_")):
        os.environ.pop(key)
from agentmem_ref import AgentMemory
from amb_agent_memory_bridge import _scope, _logical_id, _TENANT, _ACTOR, _PURPOSE
from memory_bench.dataset.precisionmembench import PrecisionMemBenchDataset

ARMS = ("raw", "default", "lexical", "eq", "fts5")
D = PrecisionMemBenchDataset(); mapping = {}; rows = []; by_doc = {}
with tempfile.TemporaryDirectory(prefix="amb-819-") as tmp:
    documents = D.load_documents("single-turn")
    by_doc = {d.id: d for d in documents}
    fts_by_user = {}
    for user in sorted({d.user_id for d in documents}):
        with AgentMemory.open(tmp, tenant=_TENANT, actor_id=_ACTOR, scope=_scope(user), purpose=_PURPOSE) as m:
            for d in documents:
                if d.user_id != user:
                    continue
                r = m.remember(_logical_id(d.id, d.user_id), d.content, observed_at=d.timestamp)
                assert r["committed"]; mapping[r["fact_uuid"]] = d
        fts_by_user[user] = paired.FTS5Index([(d.id, d.content) for d in documents if d.user_id == user])
    for q in D.load_queries("single-turn"):
        k = q.meta["retrieval_limit"]; arms = {}; ids = {}
        if q.query.strip() and k > 0:
            with AgentMemory.open(tmp, tenant=_TENANT, actor_id=_ACTOR, scope=_scope(q.user_id), purpose=_PURPOSE) as m:
                am = paired.am_arms(m, q.query, k)
            for arm in ("raw", "default", "lexical", "eq"):
                ids[arm] = [mapping[u].id for u in am[arm]]
            ids["fts5"] = fts_by_user[q.user_id].search(q.query, k) if q.user_id in fts_by_user else []
            selection = {**{kk: vv for kk, vv in am["eq_selection"].items() if kk != "decisions"},
                         "decisions": {mapping[u].id: d for u, d in am["eq_selection"]["decisions"].items()}}
            ms = am["ms"]
        else:
            ids = {arm: [] for arm in ARMS}; selection = None; ms = {}
        for arm in ARMS:
            scored = copy.deepcopy(q)
            correct, reason = D.score_retrieval(scored, [by_doc[i] for i in ids[arm]])
            arms[arm] = {"correct": correct, "reason": reason, "meta": scored.meta, "returned_ids": ids[arm]}
        rows.append({"case_id": q.id, "category": q.meta["category"], "query": q.query, "arms": arms, "eq_selection": selection, "ms": ms})
    for f in fts_by_user.values():
        f.close()
summary = {}
for arm in ARMS:
    rr = [r["arms"][arm] for r in rows]
    no_answer = [x for x in rr if x["meta"]["pass_type"] == "trivially-empty"]
    summary[arm] = {
        "strict": sum(x["correct"] for x in rr), "cases": len(rr), "metrics": D.summary_metrics(rr),
        "returned_count": sum(len(x["returned_ids"]) for x in rr),
        "must_exclude_failure_cases": sum(any("forbidden belief" in f for f in x["meta"]["failures"]) for x in rr),
        "unexpected_belief_failure_cases": sum(any("unexpected belief" in f for f in x["meta"]["failures"]) for x in rr),
        "missing_expected_failure_cases": sum(any("missing expected belief" in f for f in x["meta"]["failures"]) for x in rr),
        "no_answer_cases": len(no_answer), "no_answer_correct": sum(x["correct"] for x in no_answer),
        "no_answer_empty_relevant": sum(not x["meta"]["relevant_beliefs"] for x in no_answer),
        "by_category": {c: {"cases": sum(1 for r in rows if r["category"] == c), "strict": sum(r["arms"][arm]["correct"] for r in rows if r["category"] == c)}
                        for c in sorted({r["category"] for r in rows})},
    }
paired_strict = {arm: {"improved": [r["case_id"] for r in rows if r["arms"][arm]["correct"] and not r["arms"]["default"]["correct"]],
                       "regressed": [r["case_id"] for r in rows if not r["arms"][arm]["correct"] and r["arms"]["default"]["correct"]]}
                 for arm in ARMS if arm != "default"}
report = {"kind": "known_AMB_diagnostic_native_scorer_public_context_arms_not_full_CLI_not_lane_evidence",
          "runtime_sha": subprocess.check_output(["git", "-C", str(runtime), "rev-parse", "HEAD"], text=True).strip(),
          "selector_blob": subprocess.check_output(["git", "-C", str(runtime), "hash-object", "reference/agentmem_ref/api/context_selection.py"], text=True).strip(),
          "amb_sha": subprocess.check_output(["git", "-C", str(workspace / "amb"), "rev-parse", "HEAD"], text=True).strip(),
          "python": sys.version, "platform": platform.platform(), "summary": summary, "paired_strict_vs_default": paired_strict, "rows": rows}
output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
print(json.dumps({a: {k: v for k, v in s.items() if k not in ("by_category",)} for a, s in summary.items()}, indent=1))
print(json.dumps(paired_strict, indent=1))
