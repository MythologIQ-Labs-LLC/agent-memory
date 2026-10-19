"""Paired recall_all@k comparison of two LongMemEval reports on the same questions (exact McNemar)."""
import json, math, sys
base, cand = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
def mc(b, c):
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)
print("base", base["execution"].get("agent_memory_revision", "?")[:8], "cand", cand["execution"].get("agent_memory_revision", "?")[:8],
      "input", cand["input"]["sha256"][:12], "n", cand["input"]["question_count"])
for plane in cand["planes"]:
    B = {r["question_id"]: r for r in base["planes"][plane]["backends"]["agent_memory"]["rows"]}
    C = {r["question_id"]: r for r in cand["planes"][plane]["backends"]["agent_memory"]["rows"]}
    qs = [q for q in C if C[q]["status"] == "scored" and B[q]["status"] == "scored"]
    tb, tc = base["planes"][plane]["backends"]["agent_memory"].get("timing"), cand["planes"][plane]["backends"]["agent_memory"].get("timing")
    print(f"== {plane}: scored {len(qs)}")
    for k in (3, 5, 10):
        m = f"recall_all@{k}"
        b = [B[q]["metrics"][plane][m] for q in qs]; c = [C[q]["metrics"][plane][m] for q in qs]
        win = sum(1 for x, y in zip(b, c) if y > x); loss = sum(1 for x, y in zip(b, c) if y < x)
        print(f"  {m:13s} {sum(b)/len(qs):.4f} -> {sum(c)/len(qs):.4f}   +{win}/-{loss}  McNemar p={mc(win, loss):.3g}")
    print("  timing base", tb, "\n  timing cand", tc)
