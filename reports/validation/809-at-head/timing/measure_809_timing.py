"""#809 timing measurement (evidence, not a guarantee): write latency of a citation of a
foreign deleted id, a foreign live id, a guess and no reference, through AgentMemory.open.

Usage: python3 measure_809_timing.py <reference dir> <rounds> ; prints JSON with per-case
median / p90 / min in microseconds and the ratio of each case to the guess case.
"""
import json, statistics, sys, tempfile, time
sys.path.insert(0, sys.argv[1])
from agentmem_ref import AgentMemory
from tests.test_644_combined_independent import _prop

TENANT, ACTOR, QUERY = "tenant:c786", "agent:c786", "Kristiansund harbour"
GUESS = "fact-guess-" + "9" * 12
rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 200


def run_round(i):
    root = tempfile.mkdtemp() + "/m"
    a = AgentMemory.open(root, tenant=TENANT, actor_id=ACTOR, scope="project:a", purpose="c786")
    a1 = a.remember("memory:a", f"{QUERY} is Oslo", proposition=_prop("Oslo"))["fact_uuid"]
    a2 = a.remember("memory:a2", f"{QUERY} is Bergen", proposition=_prop("Bergen"))["fact_uuid"]
    assert a.forget("memory:a")["committed"]
    a.close()
    b = AgentMemory.open(root, tenant=TENANT, actor_id=ACTOR, scope="project:b", purpose="c786")
    cases = [("deleted", a1), ("live", a2), ("unknown", GUESS), ("none", None)]
    order = cases[i % 4:] + cases[:i % 4]  # rotate to spread cache/warm-up effects
    out = {}
    for label, ref in order:
        kw = {"evidence_refs": (ref,)} if ref else {}
        t0 = time.perf_counter_ns()
        r = b.remember(f"memory:b-{label}", f"{QUERY} digest {label}", **kw)
        out[label] = (time.perf_counter_ns() - t0) / 1000
        assert r["committed"], r
    b.close()
    return out


samples = {k: [] for k in ("deleted", "live", "unknown", "none")}
for i in range(rounds):
    for k, v in run_round(i).items():
        samples[k].append(v)
report = {}
for k, v in samples.items():
    v = sorted(v)
    report[k] = {"n": len(v), "median_us": round(statistics.median(v), 1), "p90_us": round(v[int(len(v) * 0.9)], 1),
                 "min_us": round(v[0], 1)}
for k in report:
    report[k]["median_ratio_to_unknown"] = round(report[k]["median_us"] / report["unknown"]["median_us"], 3)
print(json.dumps(report, indent=1))
