"""#583: classify every AgentMemBench search whose ordered top-k differs from canonical 3.0.1.

Usage: python amb_rank_diff.py <harness_repo_root> <memdialogue_v2.jsonl> <candidate_trace.json> <canonical_trace.json[.gz]>
Search 0 is the harness warmup; searches 1..1000 are retrieval records 0..999 in load order;
1001..1250 are conflict pairs. Query/memory texts are emitted only as digests.
"""
import gzip, hashlib, json, re, sys
from pathlib import Path

root, data, cand_path, can_path = sys.argv[1:5]
sys.path.insert(0, str(Path(root) / "reference"))
import run_agentmembench as amb  # noqa: E402

h = lambda t: hashlib.sha256(t.encode()).hexdigest()[:16]
load = lambda p: json.load(gzip.open(p)) if p.endswith(".gz") else json.load(open(p))
recs = amb.load_records(Path(data), 1000, 2027)
cand, can = load(cand_path), load(can_path)
assert all(h(recs[i]["query"]) == cand["searches"][i + 1]["query"] for i in range(1000)), "retrieval alignment"
assert [s["query"] for s in cand["searches"]] == [s["query"] for s in can["searches"]], "same query sequence"
rows, excluded_unchanged = [], 0
for i, (a, b) in enumerate(zip(cand["searches"], can["searches"])):
    if a["returned"] == b["returned"]:
        excluded_unchanged += bool(a["excluded_cues"])
        continue
    row = {"search_index": i, "excluded_cues": a["excluded_cues"], "intent": a["intent"],
           "same_topk_set": set(a["returned"]) == set(b["returned"]),
           "positions_changed": [k for k, (x, y) in enumerate(zip(a["returned"], b["returned"])) if x != y]}
    if 1 <= i <= 1000:
        r = recs[i - 1]
        g = h(r["text"])
        rank = lambda L: L.index(g) + 1 if g in L else None
        row.update(phase="retrieval", record_index=i - 1, event_type=r["event_type"], source_id=r["source_id"],
                   gold_rank_3_0_2=rank(a["returned"]), gold_rank_3_0_1=rank(b["returned"]),
                   exact_source_hit_changed=(g in a["returned"]) != (g in b["returned"]),
                   cue_occurrences_in_query=sum(len(re.findall(r"\b" + re.escape(c) + r"\b", r["query"], re.I)) for c in a["excluded_cues"]),
                   gold_text_contains_cue=any(re.search(r"\b" + re.escape(c) + r"\b", r["text"], re.I) for c in a["excluded_cues"]))
    else:
        row["phase"] = "conflict" if 1001 <= i <= 1250 else "other"
    row["classification"] = "INTENDED_583_EFFECT" if a["excluded_cues"] else "UNEXPLAINED"
    rows.append(row)
print(json.dumps({"candidate_trace": Path(cand_path).name, "canonical_trace": Path(can_path).name,
                  "search_calls": len(cand["searches"]),
                  "searches_with_excluded_cues": sum(bool(s["excluded_cues"]) for s in cand["searches"]),
                  "searches_with_excluded_cues_order_unchanged": excluded_unchanged,
                  "order_differences": len(rows),
                  "order_differences_without_excluded_cue": sum(r["classification"] != "INTENDED_583_EFFECT" for r in rows),
                  "exact_source_hit_changes": sum(bool(r.get("exact_source_hit_changed")) for r in rows),
                  "differences": rows}, indent=1))
