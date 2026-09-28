"""#594: report the pre-registered future-dated subgroup explicitly for C, P1 and P2.

Usage: PYTHONPATH=reference python future_dated_subgroup.py <longmemeval_s_cleaned.json> C.rows.json.gz P1.rows.json.gz P2.rows.json.gz OUT.json

The subgroup is fixed by the source alone, exactly as the manifest's hazard pre-registers
it: questions with at least one haystack session dated after `question_date`. Membership
never depends on any profile result. The profiles are neither filtered nor changed; this
reads their committed rows and restricts the report to the subgroup's question ids.
"""
import gzip
import hashlib
import json
import sys
from pathlib import Path

import run_longmemeval as lme

source, c_path, p1_path, p2_path, out_path = (Path(p) for p in sys.argv[1:6])
raw = source.read_bytes()
data = json.loads(raw)

members = []
definition_counts = {}
for plane in ("session", "turn"):
    counts = {"items_observed_after_question_date": 0, "gold_items_observed_after_question_date": 0}
    for row in data:
        items, gold = lme.corpus(row, plane)
        asked = lme._iso_date(row["question_date"])
        later = [item for item in items if lme._iso_date(item["date"]) and asked and lme._iso_date(item["date"]) > asked]
        counts["items_observed_after_question_date"] += len(later)
        counts["gold_items_observed_after_question_date"] += sum(item["id"] in gold for item in later)
        if plane == "session" and later:
            members.append(row["question_id"])
    definition_counts[plane] = counts
subgroup = set(members)

profiles = {name: json.load(gzip.open(path)) for name, path in (("C", c_path), ("P1", p1_path), ("P2", p2_path))}


def summary(rows):
    scored = [r for r in rows if r["status"] == "scored"]
    names = sorted({f"{sub}.{name}" for r in scored for sub in r["metrics"] for name in r["metrics"][sub]
                    if name.rsplit("@", 1)[-1] in {"1", "5", "10", "50"}})
    means = {key: round(sum(r["metrics"][key.split(".", 1)[0]][key.split(".", 1)[1]] for r in scored) / len(scored), 6) for key in names}
    lgf = [r["latest_gold_first"] for r in rows if r["latest_gold_first"] is not None]
    return {
        "questions": len(rows),
        "scored": len(scored),
        "question_types": dict(sorted({t: sum(r["question_type"] == t for r in rows) for t in {r["question_type"] for r in rows}}.items())),
        "latest_gold_first": {"evaluable": len(lgf), "true": sum(lgf)},
        "metric_means_over_scored": means,
    }


def gold_ranks(row):
    position = {doc: index + 1 for index, doc in enumerate(row["ranked_top"])}
    return {doc: position.get(doc) for doc in row["gold"]}


planes = {}
for plane in ("session", "turn"):
    rows = {name: [r for r in doc[plane]["agent_memory"] if r["question_id"] in subgroup] for name, doc in profiles.items()}
    assert all(len(v) == len(subgroup) for v in rows.values()), plane
    section = {name: summary(v) for name, v in rows.items()}
    base = {r["question_id"]: r for r in rows["C"]}
    for name in ("P1", "P2"):
        changed = [r["question_id"] for r in rows[name] if r["ranked_top"] != base[r["question_id"]]["ranked_top"]]
        gold_changed = [r["question_id"] for r in rows[name] if gold_ranks(r) != gold_ranks(base[r["question_id"]])]
        lgf = [r["question_id"] for r in rows[name] if r["latest_gold_first"] != base[r["question_id"]]["latest_gold_first"]]
        metrics = [r["question_id"] for r in rows[name] if r["metrics"] != base[r["question_id"]]["metrics"]]
        section[f"C_vs_{name}"] = {"changed_ranking_rows": len(changed), "changed_gold_rank_rows": len(gold_changed),
                                   "latest_gold_first_changes": len(lgf), "rows_with_metric_changes": len(metrics),
                                   "question_ids": sorted(set(changed + gold_changed + lgf + metrics))}
    planes[plane] = section

Path(out_path).write_text(json.dumps({
    "subgroup": "future_dated: questions with at least one haystack session dated after question_date",
    "pre_registration": "source-anchor-manifest.json hazards (P2), committed in 9fc452f before any adapted score",
    "membership_depends_on_results": False,
    "profiles_filtered_or_changed": False,
    "input_sha256": hashlib.sha256(raw).hexdigest(),
    "row_sources": {"C": c_path.name, "P1": p1_path.name, "P2": p2_path.name},
    "questions_in_subgroup": len(subgroup),
    "question_ids": sorted(subgroup),
    "definition_counts": definition_counts,
    "planes": planes,
}, indent=1, sort_keys=True) + "\n")
for plane, section in planes.items():
    print(plane, {k: v for k, v in section.items() if k.startswith("C_vs")})
