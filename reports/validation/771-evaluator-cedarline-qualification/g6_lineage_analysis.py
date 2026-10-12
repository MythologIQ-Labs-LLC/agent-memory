"""Phase E evidence (validation-only, offline): is G6 a lineage problem?

For every historical-intent answerable question, locate the critical memory in
the unchanged runtime's full ranked admission and check whether it is the
governed PREDECESSOR (same logical memory, replaced by a state change) of a
memory ranked above it. Lineage comes from the execution inputs' governed
history, never from gold wording.
"""
import json, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
EVAL = HERE.parents[2]
D = json.loads((HERE / "phase-d-results.json").read_text())
SRC = {"halcyon-v1.1": ("reports/validation/771-cloud-qualification/holdout/halcyon-holdout-v1.1-input.json",
                        "reports/validation/771-cloud-qualification/holdout/halcyon-holdout-v1-gold.json"),
       "cedarline-v1.1": ("reference/fixtures/evaluation/cedarline-independent-v1.1-input.json",
                          "reference/fixtures/evaluation/cedarline-independent-v1.1-gold.json")}
out = {}
for corpus, entry in D["corpora"].items():
    show = lambda p: json.loads(subprocess.run(["git", "-C", str(EVAL), "show", f"{entry['source_commit']}:{p}"], check=True, capture_output=True).stdout)
    inputs, gold = show(SRC[corpus][0]), {c["id"]: c for c in show(SRC[corpus][1])["cases"]}
    memory_of, chain = {}, {}
    for e in inputs["events"]:
        if e["op"] in ("retain", "update", "correct"):
            memory_of[e["id"]] = e["memory"]; chain.setdefault(e["memory"], []).append((e["id"], e["op"]))
    rows = []
    for side in entry["variants"]["v7-9b025f9/composed-default"]["per_query"]:
        case = gold[side["id"]]
        if case["intent"] != "historical" or not case["safe_answer_exists"]:
            continue
        crit = [r for g in case["critical_groups"] for r in g]
        ranked = side["ranked_admitted"]
        for c in crit:
            pos = ranked.index(c) + 1 if c in ranked else None
            versions = [v for v, _ in chain[memory_of[c]]]
            successors_above = [r for r in ranked[:(pos - 1 if pos else len(ranked))]
                                if memory_of.get(r) == memory_of[c] and versions.index(r) > versions.index(c)]
            rows.append({"id": side["id"], "critical": c, "rank": pos, "budget": case["budget"],
                         "served": pos is not None and pos <= case["budget"],
                         "governed_successor_ranked_above": successors_above,
                         "lineage_kind": ("predecessor_of_" + ",".join(successors_above)) if successors_above
                         else ("same_memory_chain" if len(versions) > 1 else "independent_memory")})
    out[corpus] = rows
(HERE / "g6-lineage-analysis.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
for c, rows in out.items():
    for r in rows:
        print(c, r["id"], r["critical"], "rank", r["rank"], "budget", r["budget"], r["lineage_kind"])
