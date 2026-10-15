"""Offline feasibility of rank fusion on recorded diagnosis rows (#819 C7). No runtime change.

The input is a diagnosis file with ``admitted_scores`` (ref, BM25, shared-evidence score, cosine)
for every admitted memory. It re-orders each query's admitted list four ways:
- ``current``: the runtime's own order;
- ``dense``: cosine only;
- ``rrf@k``: reciprocal-rank fusion of the BM25 list (BM25 > 0), the shared-evidence list and
  the cosine list. Equal scores share a rank (competition ranking); remaining ties break on ref.

It reports evidence-set coverage at depths 3, 5 and 10, needed memories in the top 5, and
non-needed memories in the top 5. k = 60 is fixed in advance as the literature default; the
other values are sensitivity only.

    python fusion_feasibility.py diag/C4-required-ranked_prefix.json
"""

import json
import sys


def competition_ranks(scores):
    ordered = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    ranks, previous, rank = {}, None, 0
    for position, (ref, value) in enumerate(ordered, start=1):
        if value != previous:
            rank, previous = position, value
        ranks[ref] = rank
    return ranks


def rrf(rows, k):
    lex = competition_ranks({r: b for r, b, _, _ in rows if b})
    shared = competition_ranks({r: s for r, _, s, _ in rows if s})
    dense = competition_ranks({r: round(c, 6) for r, _, _, c in rows if c is not None})
    fused = {r: sum(1.0 / (k + ranks[r]) for ranks in (lex, shared, dense) if r in ranks) for r, *_ in rows}
    return sorted(fused, key=lambda r: (-round(fused[r], 12), r))


data = json.load(open(sys.argv[1]))
orders = {"current": lambda rows, ranked: ranked,
          "dense": lambda rows, ranked: [r for r, *_ in sorted(rows, key=lambda x: (-(x[3] or 0), x[0]))]}
for k in (10, 30, 60):
    orders[f"rrf@{k}"] = (lambda k: lambda rows, ranked: rrf(rows, k))(k)
for name, fn in orders.items():
    cover = {3: 0, 5: 0, 10: 0}
    top5_needed = top5_other = 0
    for row in data["rows"]:
        must = list(row["needed"])
        ranked = [r for r, *_ in row["admitted_scores"]]
        order = fn(row["admitted_scores"], ranked)
        if must:
            for d in cover:
                cover[d] += all(r in order[:d] for r in must)
        top5_needed += sum(1 for r in order[:5] if r in must)
        top5_other += sum(1 for r in order[:5] if r not in must)
    n = sum(1 for row in data["rows"] if row["needed"])
    print(f"{name:8s} coverage@3 {cover[3]:2d} @5 {cover[5]:2d} @10 {cover[10]:2d} (of {n})  needed in top5 {top5_needed}  others in top5 {top5_other}")
