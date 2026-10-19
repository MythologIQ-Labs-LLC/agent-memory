import sys
sys.argv = [sys.argv[0], "feas/features_ce.jsonl"]
exec(open("tools/simulate_ce.py").read().split('if __name__')[0])
c4 = lambda r: r["cos"] > 0.30 and r["drank"] <= 16
_, bper = evaluate(c4)
def show(name, rule):
    res, per = evaluate(rule)
    w = sum(1 for k in per if per[k][0] and not bper[k][0]); l = sum(1 for k in per if bper[k][0] and not per[k][0])
    pairs = sum(1 for r in R if r["drank"] <= 8) / len(Q)
    print(f"{name:52s} {res} strict +{w}/-{l}")
lost = [r for r in R if r["label"]=="need" and c4(r) and not (lex_suff(r)) and not (r["drank"]<=16 and r["qnli"]>0)]
print("needed lost by K16 gate:", len(lost), "cos dist", sorted(round(r["cos"],2) for r in lost)[::4], "drank", sorted(r["drank"] for r in lost)[::4], "qnli", sorted(round(r["qnli"],1) for r in lost)[::4])
for K in (8, 16):
    show(f"K{K}&q>0 | c4&drank1", lambda r,K=K: (r["drank"]<=K and r["qnli"]>0) or (c4(r) and r["drank"]==1))
    show(f"K{K}&q>0 | cos>0.5", lambda r,K=K: (r["drank"]<=K and r["qnli"]>0) or r["cos"]>0.5)
    show(f"K{K}&q>0 | c4&rel>=0.9", lambda r,K=K: (r["drank"]<=K and r["qnli"]>0) or (c4(r) and r["rel"]>=0.9))
    show(f"K{K}&q>-2", lambda r,K=K: (r["drank"]<=K and r["qnli"]>-2))
    show(f"K{K}&q>0 | c4&q>-3", lambda r,K=K: (r["drank"]<=K and r["qnli"]>0) or (c4(r) and r["qnli"]>-3))
