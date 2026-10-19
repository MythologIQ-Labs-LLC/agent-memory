import sys; sys.argv=[sys.argv[0], "feas/features_ce.jsonl"]
exec(open("tools/simulate_ce.py").read().split('if __name__')[0])
c4 = lambda r: r["cos"] > 0.30 and r["drank"] <= 16
_, bper = evaluate(c4)
def show(name, rule):
    res, per = evaluate(rule)
    w = sum(1 for k in per if per[k][0] and not bper[k][0]); l = sum(1 for k in per if bper[k][0] and not per[k][0])
    nw = sum(max(0, per[k][1]-bper[k][1]) for k in per); nl = sum(max(0, bper[k][1]-per[k][1]) for k in per)
    pairs = sum(1 for r in R if rule.__defaults__ is None or True)
    print(f"{name:40s} {res} strict +{w}/-{l} needed +{nw}/-{nl}")
for K in (4, 8, 12, 16, 24, 32):
    show(f"dense<={K} & qnli>0", lambda r, K=K: r["drank"] <= K and r["qnli"] > 0)
for K in (8,16,32):
    show(f"dense<={K} & cos>0.2 & qnli>0", lambda r, K=K: r["drank"] <= K and r["cos"]>0.2 and r["qnli"] > 0)
show("C4sem & qnli>0 | dense<=16 & qnli>2", lambda r: (c4(r) and r["qnli"]>0) or (r["drank"]<=16 and r["qnli"]>2))
import statistics
for K in (8,16,32):
    print(K, "pairs/query mean", round(statistics.mean(min(len(v),K) for v in Q.values()),1), "max n", max(len(v) for v in Q.values()))
print("c4sem pairs/query", round(sum(1 for r in R if c4(r))/len(Q),1))
# per-set breakdown at K=16
for s in sorted({k[0] for k in Q}):
    keys=[k for k in Q if k[0]==s]
    print(s, "C4sem", evaluate(c4, keys)[0], "K16", evaluate(lambda r: r["drank"]<=16 and r["qnli"]>0, keys)[0])
# 2-fold CV for fitted threshold over sets (leave-one-set-out)
sets=sorted({k[0] for k in Q}); tot=dict(strict=0,needed=0,extras=0)
for s in sets:
    train=[k for k in Q if k[0]!=s]; test=[k for k in Q if k[0]==s]
    best=None
    for t in [x/2 for x in range(-8,9)]:
        r_,_=evaluate(lambda r,t=t: r["drank"]<=16 and r["qnli"]>t, train)
        base_,_=evaluate(c4,train)
        if r_["needed"]>=base_["needed"]*0.98:
            sc=r_["strict"]-0.1*r_["extras"]
            if best is None or sc>best[0]: best=(sc,t)
    r_,_=evaluate(lambda r,t=best[1]: r["drank"]<=16 and r["qnli"]>t, test)
    for k in tot: tot[k]+=r_[k]
    print("LOSO", s, "t*", best[1], r_)
print("LOSO total", tot)
