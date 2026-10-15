import json,sys
c6,c4s,c4=[{r["id"]:r for r in json.load(open(f))} for f in sys.argv[1:4]]
def must(r,gen):
    return r
sc=json.load(open(sys.argv[4]))["scenarios"]
exp={q["id"]:q["expect"] for s in sc for q in s["queries"]}
gain_vs_off=[];lost_vs_sem=[];gain_vs_sem=[]
for i,r in c6.items():
    m=set(exp[i]["must_include"])
    a=set(r["returned"])&m; b=set(c4s[i]["returned"])&m; c=set(c4[i]["returned"])&m
    gain_vs_off+= [(i,x) for x in a-c]
    lost_vs_sem+= [(i,x) for x in b-a]
    gain_vs_sem+= [(i,x) for x in a-b]
print("needed memories C6 returns that C4-default does not (discovery vs default):",len(gain_vs_off))
print("needed memories C4+sem returns that C6 loses:",len(lost_vs_sem),lost_vs_sem)
print("needed memories C6 returns that C4+sem does not:",len(gain_vs_sem),gain_vs_sem)
# strict flips
flip=lambda A,B:([i for i in A if A[i]["pass"] and not B[i]["pass"]],[i for i in A if B[i]["pass"] and not A[i]["pass"]])
up,down=flip(c6,c4s);print("C6 vs C4+sem strict: +%d -%d"%(len(up),len(down)),"regress:",down)
# of the C6 wins over C4+sem, how many have identical needed coverage (pure suppression of extras)?
pure=[i for i in up if set(c6[i]["returned"])&set(exp[i]["must_include"])==set(c4s[i]["returned"])&set(exp[i]["must_include"])]
print("  of which wins with same needed coverage as C4+sem (precision only):",len(pure),pure)
up,down=flip(c6,c4);print("C6 vs C4 default strict: +%d -%d"%(len(up),len(down)),"regress:",down)
print("extras: C6 %d C4sem %d C4 %d"%tuple(sum(x[i]["extra"] for i in x) for x in (c6,c4s,c4)))
