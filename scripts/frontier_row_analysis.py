"""Aggregate-only row analysis of committed LongMemEval-S retrieval rows (#810 / #719 frontier work).

Reads per-question rows already committed by the comparator lanes and reports, per system and plane:
  A1 evidence-rank distribution (where each gold item sits: 1-5, 6-10, 11-30, 31-50, absent from top 50),
     overall, for multi-session questions and by evidence count;
  A2 complementarity against a pure dense ranking (union at k, an oracle upper bound);
  A3 an OFFLINE fusion counterfactual: reciprocal-rank fusion of two committed ranked lists with a
     deterministic tie-break. It is not a runtime intervention and not evidence that the runtime would
     reach the same numbers; it only measures whether the two signals are complementary.
Every recall_all@k recomputed here is first checked against the row's own stored metric; any mismatch aborts.
No per-question ids, gold or text are written to the output.

Usage: frontier_row_analysis.py DATA_DIR OUTPUT_JSON
"""
from __future__ import annotations

import gzip, json, math, random, sys
from collections import Counter
from pathlib import Path

BUCKETS = ((1, 5), (6, 10), (11, 30), (31, 50))


def load_report(path, backend, plane):
    d = json.load(gzip.open(path) if str(path).endswith(".gz") else open(path))
    return {r["question_id"]: r for r in d["planes"][plane]["backends"][backend]["rows"]}


def load_rows(path):
    return {json.loads(l)["question_id"]: json.loads(l) for l in open(path)}


def dedupe(seq):
    seen, out = set(), []
    for x in seq:
        if x not in seen:
            seen.add(x); out.append(x)
    return out


def recall_all(ranked, gold, k):
    return 1.0 if set(gold) <= set(dedupe(ranked)[:k]) else 0.0


def check(rows, plane, name):
    bad = 0
    for r in rows.values():
        if r.get("status") != "scored":
            continue
        for k in (5, 10, 50):
            if recall_all(r["ranked_top"], r["gold"], k) != r["metrics"][plane][f"recall_all@{k}"]:
                bad += 1
    if bad:
        raise SystemExit(f"{name}/{plane}: {bad} recomputed recall_all values disagree with stored metrics")


def rank_buckets(rows, qs):
    c = Counter()
    for q in qs:
        ranked = dedupe(rows[q]["ranked_top"])
        for g in rows[q]["gold"]:
            pos = ranked.index(g) + 1 if g in ranked else None
            label = next((f"{a}-{b}" for a, b in BUCKETS if pos and a <= pos <= b), "absent_top50")
            c[label] += 1
    n = sum(c.values())
    return {"evidence_items": n, **{k: round(c[k] / n, 4) for k in [f"{a}-{b}" for a, b in BUCKETS] + ["absent_top50"]}}


def rrf(a, b, k=60):
    a, b = dedupe(a), dedupe(b)
    score = {}
    for lst in (a, b):
        for i, x in enumerate(lst):
            score[x] = score.get(x, 0.0) + 1.0 / (k + i + 1)
    first = {x: i for i, x in enumerate(a)}
    second = {x: i for i, x in enumerate(b)}
    # deterministic tie-break: higher fused score, then better rank in list a, then list b, then id
    return sorted(score, key=lambda x: (-score[x], first.get(x, 10**6), second.get(x, 10**6), x))


def paired(base, cand, iters=10000, seed=810):
    w = sum(1 for x, y in zip(base, cand) if y > x); l = sum(1 for x, y in zip(base, cand) if y < x)
    n = w + l
    p = min(1.0, 2 * sum(math.comb(n, i) for i in range(min(w, l) + 1)) / 2 ** n) if n else 1.0
    rnd = random.Random(seed); d = [y - x for x, y in zip(base, cand)]; m = len(d)
    boots = sorted(sum(d[rnd.randrange(m)] for _ in range(m)) / m for _ in range(iters))
    return {"wins": w, "losses": l, "ties": m - n, "mcnemar_exact_p": float(f"{p:.3g}"),
            "delta": round(sum(d) / m, 4), "ci95": [round(boots[int(0.025 * iters)], 4), round(boots[int(0.975 * iters) - 1], 4)]}


def main():
    D, out = Path(sys.argv[1]), Path(sys.argv[2])
    result = {"method": __doc__.strip().splitlines()[0], "authority_effect": "none", "full500": {}, "subset50": {}}
    for plane in ("session", "turn"):
        systems = {
            "agent_memory": load_report(D / "controls/full500/controls-500.json.gz", "agent_memory", plane),
            "lexical_overlap": load_report(D / "controls/full500/controls-500.json.gz", "lexical_overlap", plane),
            "hindsight_chunks": load_rows(D / f"640-hindsight/full500/{plane}.hindsight_chunks_onnx.rows.jsonl"),
            "mempalace": load_rows(D / f"mempalace/full500/{plane}.mempalace_default_local.rows.jsonl"),
        }
        for n, rows in systems.items():
            check(rows, plane, n)
        am = systems["agent_memory"]
        qs = sorted(q for q in am if am[q]["status"] == "scored" and all(systems[s][q]["status"] == "scored" for s in systems))
        ms = [q for q in qs if am[q]["question_type"] == "multi-session"]
        g3 = [q for q in qs if len(am[q]["gold"]) >= 3]
        block = {"scored_questions": len(qs), "rank_distribution": {}, "union_oracle": {}}
        for n, rows in systems.items():
            block["rank_distribution"][n] = {"all": rank_buckets(rows, qs), "multi_session": rank_buckets(rows, ms),
                                             "three_plus_evidence": rank_buckets(rows, g3)}
        k = 5 if plane == "session" else 10
        for peer in ("hindsight_chunks", "mempalace"):
            base = [recall_all(am[q]["ranked_top"], am[q]["gold"], k) for q in qs]
            peer_v = [recall_all(systems[peer][q]["ranked_top"], am[q]["gold"], k) for q in qs]
            union = [max(x, y) for x, y in zip(base, peer_v)]
            block["union_oracle"][f"agent_memory_or_{peer}@{k}"] = {"agent_memory": round(sum(base) / len(qs), 4),
                                                                    "peer": round(sum(peer_v) / len(qs), 4),
                                                                    "either_full": round(sum(union) / len(qs), 4)}
        result["full500"][plane] = block

        # subset50: Agent Memory vs pure dense rankings (Letta archival / bge-small; Mem0 explicit / MiniLM)
        sub = {
            "agent_memory": load_report(D / "controls/subset50/controls-50.json.gz", "agent_memory", plane),
            "lexical_overlap": load_report(D / "controls/subset50/controls-50.json.gz", "lexical_overlap", plane),
            "letta_archival_dense": load_rows(D / f"letta-{plane}.rows.jsonl"),
            "mem0_explicit_dense": load_report(D / "mem0/subset50/mem0-50.json.gz", "mem0_explicit", plane),
        }
        for n, rows in sub.items():
            check(rows, plane, n)
        sa = sub["agent_memory"]
        sq = sorted(q for q in sa if sa[q]["status"] == "scored" and all(sub[s][q]["status"] == "scored" for s in sub))
        sb = {"scored_questions": len(sq), "rank_distribution": {n: rank_buckets(r, sq) for n, r in sub.items()}, "fusion": {}}
        for dense in ("letta_archival_dense", "mem0_explicit_dense"):
            for left in ("agent_memory", "lexical_overlap"):
                fused = {q: rrf(sub[left][q]["ranked_top"], sub[dense][q]["ranked_top"]) for q in sq}
                entry = {}
                for kk in (5, 10, 50):
                    base = [recall_all(sa[q]["ranked_top"], sa[q]["gold"], kk) for q in sq]
                    f = [recall_all(fused[q], sa[q]["gold"], kk) for q in sq]
                    d = [recall_all(sub[dense][q]["ranked_top"], sa[q]["gold"], kk) for q in sq]
                    entry[f"recall_all@{kk}"] = {"agent_memory": round(sum(base) / len(sq), 4), "dense_alone": round(sum(d) / len(sq), 4),
                                                 "fused": round(sum(f) / len(sq), 4),
                                                 "union_oracle": round(sum(max(x, y) for x, y in zip(base, d)) / len(sq), 4),
                                                 "fused_vs_agent_memory": paired(base, f)}
                sb["fusion"][f"rrf60({left},{dense})"] = entry
        result["subset50"][plane] = sb
    out.write_text(json.dumps(result, indent=1) + "\n")
    print(out)


if __name__ == "__main__":
    main()
