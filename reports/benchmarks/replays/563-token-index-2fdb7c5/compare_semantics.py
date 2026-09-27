"""Compare a streaming-loader LongMemEval report with frozen whole-file evidence.

Timing fields (per-row ingest/recall seconds, backend timing, execution) are
non-semantic and reported separately; every other field must match exactly.
"""
import gzip, json, sys
new_path, frozen_path, frozen_rows_path, backends = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(",")
new = json.load(open(new_path)); frozen = json.load(open(frozen_path)); frozen_rows = json.load(gzip.open(frozen_rows_path))
TIMING_ROW = {"ingest_seconds", "recall_seconds"}
out = {"new": new_path, "frozen": frozen_path, "backends": backends, "checks": {}, "differences": []}
def check(name, a, b):
    ok = a == b
    out["checks"][name] = ok
    if not ok: out["differences"].append(name)
inp_new, inp_old = new["input"], frozen["input"]
for key in ("sha256", "size_bytes", "question_count", "abstention_question_count", "no_user_target_question_count", "duplicate_session_id_question_count", "selection"):
    check(f"input.{key}", inp_new[key], inp_old[key])
rows_compared = 0
for plane in ("session", "turn"):
    for backend in backends:
        a = new["planes"][plane]["backends"][backend]; b = frozen["planes"][plane]["backends"][backend]
        for key in sorted(set(a) | set(b)):
            if key in ("rows", "timing"): continue
            check(f"{plane}/{backend}.{key}", a.get(key), b.get(key))
        new_rows = a["rows"]; old_rows = frozen_rows[plane][backend]
        check(f"{plane}/{backend}.question_order", [r["question_id"] for r in new_rows], [r["question_id"] for r in old_rows])
        mism = 0
        for x, y in zip(new_rows, old_rows):
            rows_compared += 1
            if {k: v for k, v in x.items() if k not in TIMING_ROW} != {k: v for k, v in y.items() if k not in TIMING_ROW}:
                mism += 1
        check(f"{plane}/{backend}.rows_semantic_identical({len(new_rows)})", mism, 0)
        out.setdefault("timing", {})[f"{plane}/{backend}"] = {"new": a.get("timing"), "frozen": b.get("timing")}
out["rows_compared"] = rows_compared
out["verdict"] = "IDENTICAL" if not out["differences"] else "DIFFERENT"
out["resource_consumption_new"] = new["execution"].get("resource_consumption")
out["wall_seconds"] = {"new": new["execution"]["wall_seconds"], "frozen": frozen["execution"]["wall_seconds"]}
print(json.dumps(out, indent=2, sort_keys=True))
