import json, collections, sys
R=[json.loads(l) for l in open("feas/features.jsonl")]
Q=collections.defaultdict(list)
for r in R: Q[(r["set"],r["q"])].append(r)
LEXB={"content_relevance","set_evidence","entity_coverage","ranked_above_sufficient","lifecycle_closure","exact_identity"}
def lex_suff(r):
    if not r["lex"] or r["relevance"] is None: return False
    if r["basis"] in LEXB: return True
    if r["basis"]=="non_lexical_route_evidence":
        rel=r["relative"] or 0; return rel>=0.5 or (r["several"] and rel>=0.25)
    return False
def topical(r): return (r["relevance"] or 0)>0
K=lambda r: 3 if r["several"] else 1
RULES={
 "C4 (cos>0.30)":            lambda r: r["cos"]>0.30 and r["drank"]<=16,
 "rankK & rel>=0.9":         lambda r: r["drank"]<=K(r) and r["rel"]>=0.9,
 "cos>0.30 & topical":       lambda r: r["cos"]>0.30 and topical(r),
 "topical & rank<=K":        lambda r: topical(r) and r["drank"]<=K(r),
 "topical & rank<=3":        lambda r: topical(r) and r["drank"]<=3,
 "(rankK&rel>=.9) | (topical&rank<=3)": lambda r: (r["drank"]<=K(r) and r["rel"]>=0.9) or (topical(r) and r["drank"]<=3),
 "(cos>.3&rankK&rel>=.9) | (topical&rank<=3)": lambda r: (r["cos"]>0.3 and r["drank"]<=K(r) and r["rel"]>=0.9) or (topical(r) and r["drank"]<=3),
 "(cos>.3&rank<=K) | (topical&rank<=3)": lambda r: (r["cos"]>0.3 and r["drank"]<=K(r)) or (topical(r) and r["drank"]<=3),
 "(cos>.3&rank<=K) | (topical&cos>.3)": lambda r: (r["cos"]>0.3 and r["drank"]<=K(r)) or (topical(r) and r["cos"]>0.3),
 "(cos>.3&rank<=K) | (topical&rank<=10)": lambda r: (r["cos"]>0.3 and r["drank"]<=K(r)) or (topical(r) and r["drank"]<=10),
}
for name, rule in RULES.items():
    strict=need_ret=extras=abst_ok=abst_n=0; per={}
    for key, rows in Q.items():
        ret=[r for r in rows if r["label"]!="excluded" or True if (lex_suff(r) or rule(r))]
        ret=sorted(ret, key=lambda r: r["drank"])[:10] if False else ret
        need={r["ref"] for r in rows if r["label"]=="need"}
        got={r["ref"] for r in ret}
        ok = need<=got and all(r["label"] in ("need","may") for r in ret)
        strict+=ok; need_ret+=len(need&got); extras+=sum(1 for r in ret if r["label"] not in ("need","may"))
        if not need: abst_n+=1; abst_ok+= not got
        per[key]=(ok,len(need&got))
    print(f"{name:48s} strict {strict:3d}/{len(Q)} needed {need_ret:3d}/384 extras {extras:4d} abstain {abst_ok}/{abst_n}")
print("--- reach-preserving family")
C4=lambda r: r["cos"]>0.30 and r["drank"]<=16
def run(name, rule):
    strict=need_ret=extras=abst_ok=abst_n=0
    for key, rows in Q.items():
        ret=[r for r in rows if lex_suff(r) or rule(r)]
        need={r["ref"] for r in rows if r["label"]=="need"}; got={r["ref"] for r in ret}
        strict+= need<=got and all(r["label"] in ("need","may") for r in ret)
        need_ret+=len(need&got); extras+=sum(1 for r in ret if r["label"] not in ("need","may"))
        if not need: abst_n+=1; abst_ok+= not got
    print(f"{name:52s} strict {strict:3d} needed {need_ret:3d} extras {extras:4d} abstain {abst_ok}/{abst_n}")
for t in (0.5,0.6,0.7,0.8):
    run(f"C4 & (rel>={t} | topical)", lambda r,t=t: C4(r) and (r["rel"]>=t or topical(r)))
    run(f"C4 & (rel>={t} | topical) | (topical&rank<=3)", lambda r,t=t: (C4(r) and (r["rel"]>=t or topical(r))) or (topical(r) and r["drank"]<=3))
    run(f"C4 & rel>={t}", lambda r,t=t: C4(r) and r["rel"]>=t)
run("C4 | (topical & rank<=3)", lambda r: C4(r) or (topical(r) and r["drank"]<=3))
