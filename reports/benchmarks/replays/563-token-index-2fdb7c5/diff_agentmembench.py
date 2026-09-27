import json, re, sys
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
TIMING = re.compile(r"(latency|seconds|_ms$|ms_|throughput|ops_per|started_at|finished_at|wall|rss|revision|dirty|resource|p50|p95|p99|mean_ms|median|elapsed|duration)", re.I)
diffs = []
def walk(x, y, path):
    if isinstance(x, dict) and isinstance(y, dict):
        for k in sorted(set(x) | set(y)):
            if TIMING.search(k): continue
            walk(x.get(k), y.get(k), f"{path}.{k}")
    elif isinstance(x, list) and isinstance(y, list):
        if len(x) != len(y): diffs.append((path, f"len {len(x)} != {len(y)}")); return
        for i, (p, q) in enumerate(zip(x, y)): walk(p, q, f"{path}[{i}]")
    elif x != y:
        diffs.append((path, x, y))
walk(a, b, "")
print(len(diffs), "non-timing differences"); [print(d) for d in diffs[:20]]
