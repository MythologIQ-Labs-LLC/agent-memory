"""#583: classify every LongMemEval_S difference between a policy-3.0.2 replay and frozen 3.0.1 evidence.

Usage: python compare_lme_s_583.py <new.json> <frozen.json> <frozen.rows.json.gz> <attribution.json>

Rows are compared per plane/backend on every non-timing field. Policy-version strings
(3.0.1 / 3.0.2) are normalized and reported separately. Each differing agent_memory row
is classified (never collapsed into one count):

* INTENDED_583_EFFECT: the question had a cue excluded by ``relevance_query_for_intent``
  and only ranking-derived fields changed (``ranked_top``, ``metrics``,
  ``latest_gold_first``); admission, refusal, candidate, and failure fields are identical;
* FAILURE_OR_GOVERNANCE_CHANGE: any admission/candidate/refusal/failure/ingestion field changed;
* NUMERICAL_ONLY: an unaffected question whose ranked set and every metric are identical
  and only the order of equal-scored items moved (not determinable from rows alone, so
  such a row is reported as UNEXPLAINED unless proven otherwise);
* UNRELATED_DRIFT / UNEXPLAINED: any change to a question with no excluded cue.
Baselines (no_memory, lexical_overlap) must be identical: they do not consume the policy.
"""
import gzip, json, sys

new_path, frozen_path, frozen_rows_path, attribution_path = sys.argv[1:5]
new = json.load(open(new_path)); frozen = json.load(open(frozen_path))
frozen_rows = json.load(gzip.open(frozen_rows_path))
attribution = json.load(open(attribution_path))
affected = set(attribution["affected_ids"])
TIMING = {"ingest_seconds", "recall_seconds"}
RANKING_FIELDS = {"ranked_top", "metrics", "latest_gold_first"}
VERSIONS = {"3.0.1", "3.0.2"}


def norm(value, sink, path=""):
    if isinstance(value, dict):
        return {k: norm(v, sink, f"{path}.{k}") for k, v in value.items() if k not in TIMING and k != "timing"}
    if isinstance(value, list):
        return [norm(v, sink, f"{path}[{i}]") for i, v in enumerate(value)]
    if value in VERSIONS:
        sink.append(f"{path}={value}")
        return "<ranking-policy-version>"
    return value


out = {"new": new_path, "frozen": frozen_path, "attribution": attribution_path,
       "input_identical": {k: new["input"][k] == frozen["input"][k] for k in
                           ("sha256", "size_bytes", "question_count", "selection", "abstention_question_count",
                            "no_user_target_question_count", "duplicate_session_id_question_count")},
       "affected_question_count": len(affected), "planes": {}, "rows": [], "version_string_changes": []}
for plane in ("session", "turn"):
    for backend in ("no_memory", "lexical_overlap", "agent_memory"):
        a = new["planes"][plane]["backends"][backend]; b = frozen["planes"][plane]["backends"][backend]
        summary_diffs = []
        for key in sorted((set(a) | set(b)) - {"rows", "timing"}):
            va, vb, s1, s2 = a.get(key), b.get(key), [], []
            if norm(va, s1, key) != norm(vb, s2, key):
                summary_diffs.append(key)
            out["version_string_changes"] += [f"{plane}/{backend}.{p}" for p in sorted(set(s1) ^ set(s2))]
        new_rows, old_rows = a["rows"], frozen_rows[plane][backend]
        assert [r["question_id"] for r in new_rows] == [r["question_id"] for r in old_rows]
        counts = {}
        for x, y in zip(new_rows, old_rows):
            fields = sorted(k for k in set(x) | set(y) if k not in TIMING and norm(x.get(k), []) != norm(y.get(k), []))
            if not fields:
                continue
            qid = x["question_id"]
            if set(fields) - RANKING_FIELDS:
                cls = "FAILURE_OR_GOVERNANCE_CHANGE"
            elif qid in affected and backend == "agent_memory":
                cls = "INTENDED_583_EFFECT"
            else:
                cls = "UNEXPLAINED"
            counts[cls] = counts.get(cls, 0) + 1
            rx, ry = x.get("ranked_top") or [], y.get("ranked_top") or []
            first = next((i for i, (p, q) in enumerate(zip(rx, ry)) if p != q), None)
            gold = set(x.get("gold") or [])
            gold_ranks = lambda r: [i + 1 for i, item in enumerate(r) if item in gold]
            plane_metrics = lambda r: (r.get("metrics") or {}).get(plane, {})
            out["rows"].append({
                "plane": plane, "backend": backend, "question_id": qid, "question_type": x["question_type"],
                "classification": cls, "fields_changed": fields,
                "excluded_cues": attribution["rows"][qid]["excluded_cues"], "intent": attribution["rows"][qid]["intent"],
                "ranked_depth": [len(rx), len(ry)], "same_ranked_set": set(rx) == set(ry),
                "first_differing_rank": None if first is None else first + 1,
                "positions_changed": sum(p != q for p, q in zip(rx, ry)),
                "gold_ranks_3_0_2": gold_ranks(rx), "gold_ranks_3_0_1": gold_ranks(ry),
                "latest_gold_first": [x.get("latest_gold_first"), y.get("latest_gold_first")],
                "metric_deltas": {m: round(plane_metrics(x).get(m, 0) - plane_metrics(y).get(m, 0), 6)
                                  for m in sorted(set(plane_metrics(x)) | set(plane_metrics(y)))
                                  if plane_metrics(x).get(m) != plane_metrics(y).get(m)},
            })
        out["planes"][f"{plane}/{backend}"] = {"summary_fields_changed": summary_diffs, "rows": len(new_rows),
                                              "rows_changed": sum(counts.values()), "by_classification": counts}
        if backend == "agent_memory":
            for key in ("aggregate", "currentness"):
                out["planes"][f"{plane}/{backend}"][key] = {"new": a.get(key), "frozen": b.get(key)}
            for key in ("governance", "failures", "authority_effect", "boundary"):
                out["planes"][f"{plane}/{backend}"][f"{key}_identical"] = norm(a.get(key), []) == norm(b.get(key), [])
changed_ids = {r["question_id"] for r in out["rows"]}
out["affected_questions_without_any_change"] = sorted(affected - changed_ids)
out["classification_totals"] = {}
for r in out["rows"]:
    out["classification_totals"][r["classification"]] = out["classification_totals"].get(r["classification"], 0) + 1
out["wall_seconds"] = {"new": new["execution"]["wall_seconds"], "frozen": frozen["execution"]["wall_seconds"]}
print(json.dumps(out, indent=1, sort_keys=True))
