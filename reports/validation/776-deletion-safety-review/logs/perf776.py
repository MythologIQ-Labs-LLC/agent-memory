import sys, time, unittest
sys.path.insert(0, sys.argv[1])
from tests.test_776_logical_deletion_admission import _HistoricalDeletionStore
from tests.test_runtime_composition import _context
class T(unittest.TestCase):
    def runTest(self): pass
t=T(); s=_HistoricalDeletionStore(t); ctx=_context(); ad=s.runtime.adapter
for i in range(40):
    s.runtime.retain(s.proposal(f"m{i}", 0), f"The pump station {i} service interval is {i} days.")
facts = list(ad._substrate.all_facts())
base_tombs = dict(ad._tombstones)
for T_ in (0, 1000, 10000, 100000):
    ad._tombstones = dict(base_tombs)
    for k in range(T_):
        ad._tombstones[f"synthetic-{k}"] = {"memory_id": f"memory:synthetic:{k}", "fact_uuid": f"synthetic-{k}"}
    n = 0; t0 = time.perf_counter()
    for _ in range(5):
        for f in facts:
            ad._admission_refusal(f, ctx, "historical"); n += 1
    per = (time.perf_counter()-t0)/n*1e6
    t0 = time.perf_counter(); s.runtime.multi_route_recall("pump station service interval", ctx, temporal_intent={"mode":"historical"}); rt=(time.perf_counter()-t0)*1e3
    print(f"tombstones={T_:6d} admission_check={per:9.1f} us/candidate  recall({len(facts)} facts)={rt:8.1f} ms")
