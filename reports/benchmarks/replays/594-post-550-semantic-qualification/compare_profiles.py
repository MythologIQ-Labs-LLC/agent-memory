"""#594: paired comparison of two LongMemEval_S profile reports (canonical vs adapted).

Usage: python compare_profiles.py BEFORE.json AFTER.json OUT.json

Reports every metric of both planes separately (no aggregate), per question type,
currentness, failures, governance, and every row whose returned ranking differs,
with each gold item's rank before and after.
"""
import json
import sys

before_path, after_path, out_path = sys.argv[1:4]
before, after = json.load(open(before_path)), json.load(open(after_path))
DEPTH = 50


def gold_ranks(row):
    position = {doc: index + 1 for index, doc in enumerate(row["ranked_top"])}
    return {doc: position.get(doc) for doc in row["gold"]}


out = {
    "before": {"path": before_path.rsplit("/", 1)[-1], "revision": before["execution"]["agent_memory_revision"],
               "dirty": before["execution"]["agent_memory_worktree_dirty"], "configuration": before["execution"]["agent_memory_configuration"]},
    "after": {"path": after_path.rsplit("/", 1)[-1], "revision": after["execution"]["agent_memory_revision"],
              "dirty": after["execution"]["agent_memory_worktree_dirty"], "configuration": after["execution"]["agent_memory_configuration"]},
    "input_identical": before["input"] == after["input"],
    "rank_depth_compared": DEPTH,
    "planes": {},
}
for plane in ("session", "turn"):
    B = before["planes"][plane]["backends"]
    A = after["planes"][plane]["backends"]
    section = {"baselines_identical": {name: B[name]["rows"] == A[name]["rows"] for name in ("no_memory", "lexical_overlap")}}
    b, a = B["agent_memory"], A["agent_memory"]
    metrics = {}
    for sub in b["aggregate"]["metrics"]:
        for name in sorted(b["aggregate"]["metrics"][sub]):
            x, y = b["aggregate"]["metrics"][sub][name], a["aggregate"]["metrics"][sub][name]
            metrics[f"{sub}.{name}"] = {"before": x, "after": y, "delta": round(y - x, 6)}
    section["metrics"] = metrics
    section["by_question_type"] = {
        qtype: {name: {"before": b["by_question_type"][qtype]["headline"][name], "after": a["by_question_type"][qtype]["headline"][name]}
                for name in b["by_question_type"][qtype]["headline"]}
        for qtype in sorted(b["by_question_type"])
    }
    section["knowledge_update"] = {
        name: {"before": b["currentness"]["knowledge_update"]["aggregate"]["headline"][name] if "aggregate" in b["currentness"]["knowledge_update"] else b["currentness"]["knowledge_update"]["headline"][name],
               "after": a["currentness"]["knowledge_update"]["aggregate"]["headline"][name] if "aggregate" in a["currentness"]["knowledge_update"] else a["currentness"]["knowledge_update"]["headline"][name]}
        for name in b["currentness"]["knowledge_update"]["headline"]
    }
    section["latest_gold_ranked_first"] = {"before": b["currentness"]["latest_gold_ranked_first"], "after": a["currentness"]["latest_gold_ranked_first"]}
    section["failures"] = {"before": b["failures"], "after": a["failures"]}
    section["governance"] = {"before": b["governance"], "after": a["governance"]}
    rows_b = {r["question_id"]: r for r in b["rows"]}
    rows_a = {r["question_id"]: r for r in a["rows"]}
    assert list(rows_b) == list(rows_a)
    changed = []
    lgf = {"fixed": [], "broken": []}
    for qid, rb in rows_b.items():
        ra = rows_a[qid]
        for key in ("candidate_count", "admitted_count", "refusal_reasons", "unmapped_admitted_count", "ingestion_failures", "runtime_error", "out_of_corpus_returned_count", "returned_count"):
            if rb.get(key) != ra.get(key):
                changed.append({"question_id": qid, "kind": "governance_or_failure", "field": key, "before": rb.get(key), "after": ra.get(key)})
        if rb["latest_gold_first"] is False and ra["latest_gold_first"] is True:
            lgf["fixed"].append(qid)
        if rb["latest_gold_first"] is True and ra["latest_gold_first"] is False:
            lgf["broken"].append(qid)
        if rb["ranked_top"] != ra["ranked_top"]:
            gb, ga = gold_ranks(rb), gold_ranks(ra)
            metric_delta = {f"{sub}.{name}": round(ra["metrics"][sub][name] - rb["metrics"][sub][name], 6)
                            for sub in rb["metrics"] for name in rb["metrics"][sub] if ra["metrics"][sub][name] != rb["metrics"][sub][name]}
            changed.append({
                "question_id": qid, "question_type": rb["question_type"], "status": rb["status"], "kind": "ranking",
                "gold_rank_changes": {doc: {"before": gb[doc], "after": ga[doc]} for doc in rb["gold"] if gb[doc] != ga[doc]},
                "latest_gold_first": {"before": rb["latest_gold_first"], "after": ra["latest_gold_first"]},
                "metric_deltas": metric_delta,
                "first_difference_position": next(i + 1 for i, (x, y) in enumerate(zip(rb["ranked_top"] + [None] * DEPTH, ra["ranked_top"] + [None] * DEPTH)) if x != y),
            })
    section["latest_gold_first_transitions"] = lgf
    section["changed_rows"] = changed
    section["changed_ranking_row_count"] = sum(1 for c in changed if c["kind"] == "ranking")
    section["changed_gold_rank_row_count"] = sum(1 for c in changed if c["kind"] == "ranking" and c["gold_rank_changes"])
    section["governance_or_failure_row_changes"] = sum(1 for c in changed if c["kind"] != "ranking")
    out["planes"][plane] = section
open(out_path, "w").write(json.dumps(out, indent=1, sort_keys=True) + "\n")
for plane, section in out["planes"].items():
    print(plane, "changed ranking rows", section["changed_ranking_row_count"], "with gold rank change", section["changed_gold_rank_row_count"],
          "gov/failure", section["governance_or_failure_row_changes"], "lgf", {k: len(v) for k, v in section["latest_gold_first_transitions"].items()})
