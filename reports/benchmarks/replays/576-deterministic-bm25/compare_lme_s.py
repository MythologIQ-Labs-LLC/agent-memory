"""#576: compare a LongMemEval_S replay with the frozen report, row by row.

Usage: python compare_lme_s.py <new.json> <frozen.json> <frozen.rows.json.gz> <backends> [<new_rows_source>]

Every per-question field except per-row timing must match. For each row whose
``ranked_top`` differs, the first differing rank and both lists are recorded; a rank
difference is never folded into "numerically insignificant". Fields expected to change
with the policy patch (``policy_version`` strings) are reported separately and are the
only permitted difference.
"""
import gzip, json, sys

new_path, frozen_path, frozen_rows_path, backends = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(",")
new = json.load(open(new_path)); frozen = json.load(open(frozen_path))
frozen_rows = json.load(gzip.open(frozen_rows_path)) if frozen_rows_path.endswith(".gz") else {
    p: {b: frozen["planes"][p]["backends"][b]["rows"] for b in backends} for p in ("session", "turn")}
TIMING_ROW = {"ingest_seconds", "recall_seconds"}
out = {"new": new_path, "frozen": frozen_path, "backends": backends, "checks": {}, "differences": [],
       "expected_version_changes": [], "rank_differences": [], "metrics": {}}


def check(name, a, b):
    ok = a == b
    out["checks"][name] = ok
    if not ok:
        out["differences"].append(name)


def strip_versions(value, path, sink):
    """Return value with 3.0.0/3.0.1 policy-version strings normalized, recording where."""
    if isinstance(value, dict):
        return {k: strip_versions(v, f"{path}.{k}", sink) for k, v in value.items()}
    if isinstance(value, list):
        return [strip_versions(v, f"{path}[{i}]", sink) for i, v in enumerate(value)]
    if value in ("3.0.0", "3.0.1"):
        sink.add((path, value))
        return "<ranking-policy-version>"
    return value


for key in ("sha256", "size_bytes", "question_count", "abstention_question_count",
            "no_user_target_question_count", "duplicate_session_id_question_count", "selection"):
    check(f"input.{key}", new["input"][key], frozen["input"][key])
rows_compared = 0
for plane in ("session", "turn"):
    for backend in backends:
        a = new["planes"][plane]["backends"][backend]; b = frozen["planes"][plane]["backends"][backend]
        seen_new, seen_old = set(), set()
        for key in sorted(set(a) | set(b)):
            if key in ("rows", "timing"):
                continue
            check(f"{plane}/{backend}.{key}", strip_versions(a.get(key), key, seen_new), strip_versions(b.get(key), key, seen_old))
        for (path, value) in sorted(seen_new ^ seen_old):
            out["expected_version_changes"].append(f"{plane}/{backend}.{path}={value}")
        out["metrics"][f"{plane}/{backend}"] = {"new": a.get("metrics"), "frozen": b.get("metrics")}
        new_rows = a["rows"]; old_rows = frozen_rows[plane][backend]
        check(f"{plane}/{backend}.question_order", [r["question_id"] for r in new_rows], [r["question_id"] for r in old_rows])
        mismatched_fields = 0
        for x, y in zip(new_rows, old_rows):
            rows_compared += 1
            if x.get("ranked_top") != y.get("ranked_top"):
                first = next((i for i, (p, q) in enumerate(zip(x["ranked_top"], y["ranked_top"])) if p != q),
                             min(len(x["ranked_top"]), len(y["ranked_top"])))
                out["rank_differences"].append({"plane": plane, "backend": backend, "question_id": x["question_id"],
                                                "first_differing_rank": first + 1,
                                                "new": x["ranked_top"][first:first + 5], "frozen": y["ranked_top"][first:first + 5]})
            sink = set()
            if strip_versions({k: v for k, v in x.items() if k not in TIMING_ROW}, "", sink) != \
               strip_versions({k: v for k, v in y.items() if k not in TIMING_ROW}, "", set()):
                mismatched_fields += 1
        check(f"{plane}/{backend}.rows_semantic_identical({len(new_rows)})", mismatched_fields, 0)
out["rows_compared"] = rows_compared
out["rank_difference_count"] = len(out["rank_differences"])
out["verdict"] = "IDENTICAL" if not out["differences"] and not out["rank_differences"] else "DIFFERENT"
out["wall_seconds"] = {"new": new["execution"]["wall_seconds"], "frozen": frozen["execution"]["wall_seconds"]}
print(json.dumps(out, indent=2, sort_keys=True))
