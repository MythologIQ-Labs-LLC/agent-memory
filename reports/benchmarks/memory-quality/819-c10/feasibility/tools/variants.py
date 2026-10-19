import sys, json
F = sys.argv[1]; cols = sys.argv[2:]
sys.argv = [sys.argv[0], F]
exec(open("tools/simulate_ce.py").read().split('if __name__')[0])
c4 = lambda r: r["cos"] > 0.30 and r["drank"] <= 16
_, bper = evaluate(c4)
for m in cols:
    agree = sum(1 for r in R if (r[m] > 0) == (r["qnli"] > 0)) / len(R)
    pos = [r[m] for r in R if r["label"] == "need"]; neg = [r[m] for r in R if r["label"] in ("other", "excluded")]
    print(f"{m}: decision agreement with fp32 qnli {agree:.4f}  AUC {auc(pos, neg):.3f}")
    for K in (8, 16, 32):
        res, per = evaluate(lambda r, K=K: r["drank"] <= K and r[m] > 0)
        w = sum(1 for k in per if per[k][0] and not bper[k][0]); l = sum(1 for k in per if bper[k][0] and not per[k][0])
        print(f"   dense<={K} & {m}>0 {res} strict +{w}/-{l}")
