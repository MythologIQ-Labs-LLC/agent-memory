"""C10 feasibility simulator over feas/features_ce.jsonl (evaluation-only; C9-S simulate.py semantics).

Returned = lexical sufficiency taken from the C4+sem run (lex_suff) OR a semantic rule.
C4+sem's semantic rule is ``cos > 0.30 and dense rank <= 16`` (every semantic-route hit is sufficient).
"""
import collections, json, random, sys
F = sys.argv[1]
R = [json.loads(l) for l in open(F)]
Q = collections.defaultdict(list)
for r in R: Q[(r["set"], r["q"])].append(r)
LEXB = {"content_relevance", "set_evidence", "entity_coverage", "ranked_above_sufficient", "lifecycle_closure", "exact_identity"}
def lex_suff(r):
    if not r["lex"] or r["relevance"] is None: return False
    if r["basis"] in LEXB: return True
    if r["basis"] == "non_lexical_route_evidence":
        rel = r["relative"] or 0; return rel >= 0.5 or (r["several"] and rel >= 0.25)
    return False
MODELS = ["msm6", "msm12", "mxbx", "qnli", "bger"]

def auc(pos, neg):
    if not pos or not neg: return float("nan")
    allv = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg])
    rank_sum = 0; i = 0
    while i < len(allv):
        j = i
        while j < len(allv) and allv[j][0] == allv[i][0]: j += 1
        avg = (i + j + 1) / 2
        rank_sum += avg * sum(1 for k in range(i, j) if allv[k][1])
        i = j
    return (rank_sum - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))

def evaluate(rule, keys=None, lex=lex_suff):
    st = nr = ex = ab_ok = ab_n = 0; per = {}
    for key in keys or Q:
        rows = Q[key]
        got = {r["ref"] for r in rows if lex(r) or rule(r)}
        need = {r["ref"] for r in rows if r["label"] == "need"}
        bad = sum(1 for r in rows if r["ref"] in got and r["label"] not in ("need", "may"))
        ok = need <= got and bad == 0
        st += ok; nr += len(need & got); ex += bad
        if not need: ab_n += 1; ab_ok += not got
        per[key] = (ok, len(need & got), bad)
    return dict(strict=st, needed=nr, extras=ex, abstain=f"{ab_ok}/{ab_n}"), per

if __name__ == "__main__":
    n_need = sum(1 for r in R if r["label"] == "need")
    print(f"queries {len(Q)} rows {len(R)} needed {n_need}")
    c4 = lambda r: r["cos"] > 0.30 and r["drank"] <= 16
    base, bper = evaluate(c4)
    miss = [r for r in R if r["label"] == "need" and not (lex_suff(r) or c4(r))]
    print("C4+sem", base, "misses", len(miss))
    print("\n## Separation (AUC need vs other/excluded, all in-scope pairs; and within the 143 misses' queries)")
    for m in ["cos", "bcos"] + MODELS:
        pos = [r[m] for r in R if r["label"] == "need"]; neg = [r[m] for r in R if r["label"] in ("other", "excluded")]
        mk = {(r["set"], r["q"]) for r in miss}
        pos2 = [r[m] for r in miss]; neg2 = [r[m] for r in R if (r["set"], r["q"]) in mk and r["label"] in ("other", "excluded")]
        top1 = sum(1 for r in miss if r.get(m + "_rank", r["drank"] if m == "cos" else r.get("brank")) == 1)
        pos_frac = sum(1 for r in miss if r[m] > 0) if m in MODELS else None
        print(f"{m:6s} AUC all {auc(pos, neg):.3f}  AUC misses-vs-their-negatives {auc(pos2, neg2):.3f}  misses at model rank1 {top1}  misses with logit>0 {pos_frac}")
    print("\n## Rules at the model's intrinsic boundary (logit > 0), no fitted threshold")
    for m in MODELS:
        for name, rule in [
            (f"C4sem & {m}>0 (gate only)", lambda r, m=m: c4(r) and r[m] > 0),
            (f"dense<=32 & {m}>0 (gate+reach)", lambda r, m=m: r["drank"] <= 32 and r[m] > 0),
            (f"any & {m}>0", lambda r, m=m: r[m] > 0),
        ]:
            res, per = evaluate(rule)
            w = sum(1 for k in per if per[k][0] and not bper[k][0]); l = sum(1 for k in per if bper[k][0] and not per[k][0])
            print(f"{name:34s} {res}  strict +{w}/-{l}")
    print("\n## Gate applied to lexical selection too: (lex_suff | dense<=32) & m>0")
    for m in MODELS:
        res, per = evaluate(lambda r, m=m: r["drank"] <= 32 and r[m] > 0, lex=lambda r, m=m: lex_suff(r) and r[m] > 0)
        print(f"{m:6s} {res}")
