"""Post-hoc analysis of a frozen LongMemEval profile report (no re-execution).

Usage:
  PYTHONPATH=reference python reference/analyze_longmemeval_report.py \
      REPORT.json REPORT.rows.json.gz longmemeval_s_cleaned.json

Separates retrieval (by type, paired Agent Memory - lexical deltas with bootstrap
95% intervals, omissions), currentness (knowledge-update ordering failures
classified by Agent Memory's own candidate score), and operational cost (per-commit
ingest and recall latency by corpus-size quartile). Output is diagnostic evidence,
not an upstream metric and not memory authority.
"""
import gzip, json, random, statistics, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_longmemeval as M
rep = json.load(open(sys.argv[1]))
for g, backends in json.load(gzip.open(sys.argv[2])).items():
    for b, rows in backends.items():
        rep["planes"][g]["backends"][b]["rows"] = rows
data = {r["question_id"]: r for r in json.load(open(sys.argv[3]))}
def amtok(t):  # mirrors agentmem_ref.state.sqlite_substrate._tokens
    return {x.strip(".,;:!?").lower() for x in t.split() if x.strip(".,;:!?")}


out = {}
# chronological order of haystacks
chron = sum(1 for r in data.values() if [M._parse_date(d) for d in r["haystack_dates"]] == sorted(M._parse_date(d) for d in r["haystack_dates"]))
out["haystacks_in_chronological_order"] = f"{chron}/{len(data)}"
for g in ("session", "turn"):
    B = rep["planes"][g]["backends"]
    am = {r["question_id"]: r for r in B["agent_memory"]["rows"]}; lx = {r["question_id"]: r for r in B["lexical_overlap"]["rows"]}
    scored = [q for q, r in am.items() if r["status"] == "scored"]
    # by type
    out[f"{g}_by_type"] = {t: {b: {k: round(v, 3) for k, v in B[b]["by_question_type"][t]["headline"].items() if k in ("recall_all@5", "recall_all@10", "ndcg_any@10") } | {"n": B[b]["by_question_type"][t]["evaluated_question_count"]} for b in ("lexical_overlap", "agent_memory")} for t in sorted(B["agent_memory"]["by_question_type"])}
    # paired comparison
    for metric in ("recall_all@5", "recall_all@10", "ndcg_any@10"):
        diffs = [am[q]["metrics"][g][metric] - lx[q]["metrics"][g][metric] for q in scored]
        rng = random.Random(2027); boots = sorted(statistics.fmean(rng.choices(diffs, k=len(diffs))) for _ in range(2000))
        out[f"{g}_paired_{metric}"] = {"mean_diff_am_minus_lex": round(statistics.fmean(diffs), 4), "ci95": [round(boots[50], 4), round(boots[1949], 4)],
            "am_better": sum(d > 0 for d in diffs), "lex_better": sum(d < 0 for d in diffs), "equal": sum(d == 0 for d in diffs)}
    # omissions
    k = 10
    out[f"{g}_omission@10"] = {b: {"no_gold_in_top10": sum(1 for q in scored if R[q]["metrics"][g]["recall_any@10"] == 0), "partial_gold_in_top10": sum(1 for q in scored if R[q]["metrics"][g]["recall_any@10"] == 1 and R[q]["metrics"][g]["recall_all@10"] == 0), "n": len(scored)} for b, R in (("agent_memory", am), ("lexical_overlap", lx))}
    # currentness failure classification (Agent Memory)
    cls = Counter(); examples = []
    for q in scored:
        r = am[q]; row = data[q]
        if row["question_type"] != "knowledge-update" or r["latest_gold_first"] is not False: continue
        items, gold = M.corpus(row, g); text = {i["id"]: i["text"] for i in items}; dates = {i["id"]: M._parse_date(i["date"]) for i in items}
        qt = amtok(row["question"])
        latest = max(gold, key=lambda d: dates[d])
        sc = lambda d: len(qt & amtok(text[d])) / max(len(qt), 1)
        ranked = r["ranked_top"]
        if latest not in ranked:
            cls["latest_gold_not_returned_in_top50"] += 1; continue
        older_ahead = [d for d in ranked[:ranked.index(latest)] if d in gold and dates[d] < dates[latest]]
        if not older_ahead: cls["older_gold_ahead_only_beyond_top50"] += 1; continue
        o = older_ahead[0]
        if abs(sc(o) - sc(latest)) < 1e-12: cls["tie_broken_by_insertion_order_older_first"] += 1
        elif sc(o) > sc(latest): cls["older_scores_higher_lexically"] += 1
        else: cls["other"] += 1
        if len(examples) < 3: examples.append({"question_id": q, "question": row["question"], "older": o, "latest": latest, "score_older": round(sc(o), 3), "score_latest": round(sc(latest), 3)})
    out[f"{g}_currentness_failures_agent_memory"] = {"classification": dict(cls), "examples": examples,
        "applicable": B["agent_memory"]["currentness"]["latest_gold_ranked_first"]["applicable_question_count"]}
    # ties in general: how often is the first-ranked item's AM score tied with the next
    # operational
    if True:
        pts = [(r["corpus_size"], r["ingest_seconds"] / r["corpus_size"] * 1000, r["recall_seconds"] * 1000, q) for q, r in am.items()]
        pts.sort()
        n = len(pts); bins = [pts[:n // 4], pts[n // 4:n // 2], pts[n // 2:3 * n // 4], pts[3 * n // 4:]]
        out[f"{g}_ingest_scaling"] = [{"corpus_size_range": [b[0][0], b[-1][0]], "mean_ms_per_commit": round(statistics.fmean(x[1] for x in b), 2), "mean_recall_ms": round(statistics.fmean(x[2] for x in b), 2)} for b in bins]
        out[f"{g}_slowest_ingest"] = sorted(((round(am[q]["ingest_seconds"], 2), am[q]["corpus_size"], q) for q in am), reverse=True)[:3]
        out[f"{g}_slowest_recall_ms"] = sorted(((round(am[q]["recall_seconds"] * 1000, 1), am[q]["corpus_size"], q) for q in am), reverse=True)[:3]
    out[f"{g}_abstention"] = {b: B[b]["aggregate"]["abstention_diagnostic"] for b in ("lexical_overlap", "agent_memory")}
    worst = sorted(scored, key=lambda q: am[q]["metrics"][g]["ndcg_any@10"] - lx[q]["metrics"][g]["ndcg_any@10"])[:3]
    out[f"{g}_largest_am_deficits"] = [(q, data[q]["question_type"], round(am[q]["metrics"][g]["ndcg_any@10"], 3), round(lx[q]["metrics"][g]["ndcg_any@10"], 3)) for q in worst]
print(json.dumps(out, indent=1))
