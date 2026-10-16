"""Latency / peak-RSS probe. usage: python perf.py <tree> <n_memories> <selection> [--shared-word] [--no-reuse] [--recalls 40]

Store: n generated memories. Default: roughly a third share a word with each query (moderate admitted set).
--shared-word: every memory contains the word "garden" and every query asks about the garden,
  so (nearly) all n memories are admitted (adversarial for fusion; 500 sits just under the 512 bound).
--no-reuse: clears the route's cached cosines before fusion (C7-equivalent fusion cost) to price a reuse miss.
"""
import random, resource, statistics, sys, tempfile, time
from pathlib import Path
tree = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(tree / "reference"))
from agentmem_ref import AgentMemory  # noqa: E402
n, selection = int(sys.argv[2]), sys.argv[3]
shared = "--shared-word" in sys.argv
no_reuse = "--no-reuse" in sys.argv
recalls = int(sys.argv[sys.argv.index("--recalls") + 1]) if "--recalls" in sys.argv else 40
rng = random.Random(7)
SUBJ = ["the boiler", "the car", "Ella", "Sam", "the garden", "the bank", "Grandma", "the school", "the dentist", "the cat",
        "the shed", "the kitchen", "the holiday", "the neighbours", "the bike", "work"]
VERB = ["needs", "had", "got", "lost", "found", "booked", "moved", "fixed", "cancelled", "planned"]
OBJ = ["a new filter", "an appointment", "a parcel", "the keys", "a quote", "a refund", "paint", "a reminder",
       "new tyres", "a letter", "the invoice", "a booking", "tickets", "a spare part", "a password"]
WHEN = ["on Monday", "last week", "in March", "yesterday", "next month", "at the weekend", "in the morning", "after school"]
def text(i):
    s = rng.choice(SUBJ)
    body = f"{s} {rng.choice(VERB)} {rng.choice(OBJ)} {rng.choice(WHEN)} (note {i})."
    if shared:
        body = f"In the garden, {body}"
    return body[0].upper() + body[1:]
QUERIES = (["What happened in the garden last week?", "What does the garden need?", "Did we book anything for the garden?",
            "What was fixed in the garden?", "Who planned the garden work?", "What did the garden get?",
            "When was the garden appointment?", "What was cancelled for the garden?"] if shared else
           ["What does the boiler need?", "Did Ella get a parcel?", "What did we book for the holiday?",
            "Who fixed the bike?", "What happened at the bank?", "When is the dentist appointment?",
            "What did the neighbours cancel?", "What did Sam lose?"])
with tempfile.TemporaryDirectory() as tmp:
    with AgentMemory.open(tmp, tenant="t:p", actor_id="a:p", scope="s:p", purpose="perf", semantic_retrieval="required") as m:
        for i in range(n):
            m.remember(f"memory:n{i}", text(i))
        retr = m._semantic["retriever"]
        if no_reuse and hasattr(retr, "similarities"):
            orig = retr.similarities
            def nocache(q, facts, _o=orig, _r=retr):
                _r._last_scores = None
                return _o(q, facts)
            retr.similarities = nocache
        m.recall(QUERIES[0], budget=10, return_selection=selection)  # warm: fills derived vectors
        lat, admitted, status = [], [], set()
        cpu0 = time.process_time()
        for k in range(recalls):
            t0 = time.perf_counter()
            r = m.recall(QUERIES[k % len(QUERIES)], budget=10, return_selection=selection)
            lat.append((time.perf_counter() - t0) * 1000)
            admitted.append(len(r["admitted"]))
            for d in r["admissions"].values():
                f = (d.get("ranking_evidence") or {}).get("fusion")
                if f: status.add(f.get("status"))
        cpu = (time.process_time() - cpu0) * 1000 / recalls
lat.sort()
rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024
print(f"{tree.name} n={n} sel={selection} shared={shared} no_reuse={no_reuse} admitted_med={int(statistics.median(admitted))} "
      f"fusion={sorted(map(str, status)) or ['none']} p50={lat[len(lat)//2]:.1f}ms p95={lat[int(len(lat)*0.95)-1]:.1f}ms cpu/recall={cpu:.1f}ms rss_mb={rss}")
