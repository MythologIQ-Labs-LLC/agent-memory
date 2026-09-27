"""#576: compare an AgentMemBench (MemDialogue v2) replay with canonical evidence, per dimension.

Usage: python compare_amb.py <new.json> <canonical.json>
Timing/resource fields are excluded; every other field, per dimension and in the
per-backend governance tallies, must match exactly.
"""
import json, re, sys

TIMING = re.compile(r"(latency|seconds|_ms$|ms_|throughput|ops_per|started_at|finished_at|wall|rss|revision|dirty|"
                    r"resource|p50|p95|p99|mean_ms|median|elapsed|duration)", re.I)


def walk(x, y, path, diffs):
    if isinstance(x, dict) and isinstance(y, dict):
        for k in sorted(set(x) | set(y)):
            if not TIMING.search(k):
                walk(x.get(k), y.get(k), f"{path}.{k}", diffs)
    elif isinstance(x, list) and isinstance(y, list):
        if len(x) != len(y):
            diffs.append([path, f"len {len(x)}", f"len {len(y)}"]); return
        for i, (p, q) in enumerate(zip(x, y)):
            walk(p, q, f"{path}[{i}]", diffs)
    elif x != y:
        diffs.append([path, x, y])


new, old = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
# Canonical reports written with --omit-details carry no per-query retrieval details;
# compare like with like and say so.
details_dropped = []
for name, report, other in (("new", new, old), ("canonical", old, new)):
    for backend, body in report["backends"].items():
        retrieval = body["phases"].get("retrieval", {})
        if "details" in retrieval and "details" not in other["backends"].get(backend, {}).get("phases", {}).get("retrieval", {}):
            retrieval.pop("details"); details_dropped.append(f"{name}:{backend}")
out = {"new": sys.argv[1], "canonical": sys.argv[2], "input_sha256_equal": new["input"]["sha256"] == old["input"]["sha256"],
       "parameters_equal": new["parameters"] == old["parameters"], "dimensions": {}, "governance": {},
       "retrieval_details_dropped_for_comparability": details_dropped}
for dim in sorted(set(new["dimensions"]) | set(old["dimensions"])):
    diffs = []
    walk(new["dimensions"].get(dim), old["dimensions"].get(dim), dim, diffs)
    out["dimensions"][dim] = {"non_timing_differences": len(diffs), "examples": diffs[:10]}
for backend in new["backends"]:
    diffs = []
    walk(new["backends"][backend], old["backends"].get(backend), backend, diffs)
    out["governance"][backend] = {"non_timing_differences": len(diffs), "examples": diffs[:10]}
out["total_non_timing_differences"] = sum(v["non_timing_differences"] for v in out["dimensions"].values()) + \
    sum(v["non_timing_differences"] for v in out["governance"].values())
out["verdict"] = "IDENTICAL" if out["total_non_timing_differences"] == 0 and out["input_sha256_equal"] and out["parameters_equal"] else "DIFFERENT"
out["wall_seconds"] = {"new": new["execution"]["wall_seconds"], "canonical": old["execution"]["wall_seconds"]}
print(json.dumps(out, indent=2, sort_keys=True))
