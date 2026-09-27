"""#576: compare AgentMemBench order/score traces across revisions and hash seeds.

Usage: python compare_amb_traces.py <trace_dir> <out.json>
Expects trace-{before,after}-seed{0,1,2}.json from amb_order_trace.py.
"""
import json, sys
from itertools import combinations
from pathlib import Path

base = Path(sys.argv[1])
SEEDS = ("0", "1", "2")
traces = {(rev, s): json.load(open(base / f"trace-{rev}-seed{s}.json")) for rev in ("before", "after") for s in SEEDS}


def order_diffs(a, b):
    if len(a["searches"]) != len(b["searches"]):
        return [{"call": None, "note": f"call count {len(a['searches'])} != {len(b['searches'])}"}]
    return [{"call": i, "query": x["query"], "a": x["returned"], "b": y["returned"]}
            for i, (x, y) in enumerate(zip(a["searches"], b["searches"])) if x != y]


def score_bit_diffs(a, b):
    n = 0
    examples = []
    for i, (x, y) in enumerate(zip(a["bm25"], b["bm25"])):
        if x != y:
            n += 1
            if len(examples) < 5:
                pairs = [(p, q) for p, q in zip(x["scores"], y["scores"]) if p != q][:2]
                examples.append({"bm25_call": i, "query": x["query"],
                                 "differing_scores": [{"text": p[0], "a_hex": p[1], "b_hex": q[1],
                                                       "a": float.fromhex(p[1]), "b": float.fromhex(q[1])} for p, q in pairs]})
    return n, examples


out = {"calls": {f"{rev}-seed{s}": {"search_calls": t["search_calls"], "bm25_calls": t["bm25_calls"],
                                     "search_order_digest": t["search_order_digest"], "bm25_score_digest": t["bm25_score_digest"]}
                 for (rev, s), t in traces.items()}, "comparisons": {}}
for label, pairs in {
    "before_cross_seed": [(("before", a), ("before", b)) for a, b in combinations(SEEDS, 2)],
    "after_cross_seed": [(("after", a), ("after", b)) for a, b in combinations(SEEDS, 2)],
    "before_vs_after_same_seed": [(("before", s), ("after", s)) for s in SEEDS],
}.items():
    for x, y in pairs:
        n_bits, examples = score_bit_diffs(traces[x], traces[y])
        od = order_diffs(traces[x], traces[y])
        out["comparisons"][f"{label}:{x[0]}-{x[1]}_vs_{y[0]}-{y[1]}"] = {
            "retrieval_order_differences": len(od), "order_difference_examples": od[:10],
            "bm25_calls_with_bit_differences": n_bits, "bm25_bit_difference_examples": examples}
out["summary"] = {
    "after_cross_seed_bm25_digests": sorted({traces[("after", s)]["bm25_score_digest"] for s in SEEDS}),
    "after_cross_seed_order_digests": sorted({traces[("after", s)]["search_order_digest"] for s in SEEDS}),
    "before_cross_seed_bm25_digests": sorted({traces[("before", s)]["bm25_score_digest"] for s in SEEDS}),
    "before_cross_seed_order_digests": sorted({traces[("before", s)]["search_order_digest"] for s in SEEDS}),
    "any_retrieval_order_difference": any(c["retrieval_order_differences"] for c in out["comparisons"].values()),
}
Path(sys.argv[2]).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
print(json.dumps(out["summary"], indent=1))
for k, v in out["comparisons"].items():
    print(k, "order_diffs", v["retrieval_order_differences"], "bm25_bit_diff_calls", v["bm25_calls_with_bit_differences"])
