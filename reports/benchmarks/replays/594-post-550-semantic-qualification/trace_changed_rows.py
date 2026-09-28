"""#594: re-run changed LongMemEval_S rows under two profiles and attribute every order change.

Usage: PYTHONPATH=reference python trace_changed_rows.py SOURCE.json COMPARE.json BEFORE_REPORT.json AFTER_REPORT.json OUT.json

For each changed ranking row in COMPARE.json, the question is re-ingested and recalled
under each temporal-metadata mode exactly as ``run_longmemeval._agent_memory`` does
(same tenant/scope/purpose/target references). A read-only spy on
``PostAdmissionRankingPolicy.keyed_stages`` records each candidate's stage keys, so
every pair whose relative order flipped is attributed to the first stage whose keys
differ, in each profile. Nothing in the runtime is modified.

Mechanism classes (per changed gold rank):
  interpreted_self_validity_demotion   deciding stage temporal_applicability_tier, basis interpreted
  declared_observation_clock_tiebreak  deciding stage temporal_order_within_query_regime on declared_observed_at
  admitted_set_membership_change       the admitted set differs (governance/admission)
  lexical_numerical_only               deciding stage lexical/route score with a differing value
  unexplained                          anything else
"""
import hashlib
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path
from unittest import mock

import run_longmemeval as lme
from agentmem_ref import AgentMemory
from agentmem_ref.runtime import ranking_policy as rp

source, compare_path, before_report, after_report, out_path = sys.argv[1:6]
compare = json.load(open(compare_path))
before_mode = compare["before"]["configuration"]["temporal_metadata"]
after_mode = compare["after"]["configuration"]["temporal_metadata"]
reports = {}
for label, path in (("before", before_report), ("after", after_report)):
    data = json.load(open(path))
    reports[label] = {plane: {r["question_id"]: r["ranked_top"] for r in data["planes"][plane]["backends"]["agent_memory"]["rows"]} for plane in ("session", "turn")}
wanted = {plane: {c["question_id"] for c in section["changed_rows"] if c["kind"] == "ranking"} for plane, section in compare["planes"].items()}
rows = {}
for row in json.loads(Path(source).read_bytes()):
    if any(row["question_id"] in ids for ids in wanted.values()):
        rows[row["question_id"]] = row
index_of = {}
for position, row in enumerate(json.loads(Path(source).read_bytes())):
    index_of[row["question_id"]] = position


def recall(row, plane, mode):
    items, gold = lme.corpus(row, plane)
    row_index = index_of[row["question_id"]]
    captured = {}
    original = rp.PostAdmissionRankingPolicy.keyed_stages

    def spy(self, evidence, intent=None):
        stages = original(self, evidence, intent)
        captured[evidence["candidate_ref"]] = [(name, repr(value)) for name, value in stages]
        return stages

    with tempfile.TemporaryDirectory(prefix="agent-memory-594-trace-") as temporary, \
            mock.patch.object(rp.PostAdmissionRankingPolicy, "keyed_stages", spy):
        with AgentMemory.open(temporary, tenant=f"tenant:longmemeval:{row_index}", actor_id="agent:benchmark",
                              scope=f"benchmark:longmemeval:{row_index}", purpose="LongMemEval retrieval evaluation") as memory:
            uuid_to_item, observed = {}, {}
            for item_index, item in enumerate(items):
                declared = {}
                if mode in {"host_declared", "source_observed_at"}:
                    stamp = lme._iso_date(item.get("date", ""))
                    if stamp:
                        declared["observed_at"] = stamp
                retained = memory.remember(f"memory:longmemeval:{row_index}:{item_index}", item["text"], **declared)
                uuid_to_item[str(retained["fact_uuid"])] = item["id"]
                observed[item["id"]] = declared.get("observed_at")
            reference_time = lme._iso_date(str(row.get("question_date", ""))) if mode == "host_declared" else None
            result = memory.recall(str(row["question"]), reference_time=reference_time)
    ranked = [uuid_to_item[u] for u in result["admitted"] if u in uuid_to_item]
    evidence = {}
    for uuid, decision in result["admissions"].items():
        if uuid in uuid_to_item and "ranking_evidence" in decision:
            ev = decision["ranking_evidence"]
            evidence[uuid_to_item[uuid]] = {
                "rank": ev.get("rank_position"),
                "temporal_applicability": ev.get("temporal_applicability"),
                "temporal_applicability_basis": ev.get("temporal_applicability_basis"),
                "temporal_ordering_clock": ev.get("temporal_ordering_clock"),
                "interpreted_validity": (ev.get("temporal_evidence") or {}).get("interpreted_validity"),
                "lexical_relevance_score": ev.get("lexical_relevance_score"),
                "stages": captured.get(uuid),
            }
    intent = next((d["ranking_evidence"].get("query_temporal_intent") for d in result["admissions"].values() if "ranking_evidence" in d), None)
    return {"ranked": ranked, "gold": gold, "evidence": evidence, "intent": intent, "observed": observed,
            "admitted": sorted(uuid_to_item[u] for u in result["admitted"] if u in uuid_to_item), "reference_time": reference_time}


def decisive(stages_a, stages_b):
    for (name, x), (_, y) in zip(stages_a, stages_b):
        if x != y:
            return name
    return "indistinguishable"


def attribute(before, after, doc):
    """Classify why gold item ``doc`` moved, from the pairs whose order flipped around it."""

    if set(before["admitted"]) != set(after["admitted"]):
        return "admitted_set_membership_change", []
    pb = {d: i for i, d in enumerate(before["ranked"])}
    pa = {d: i for i, d in enumerate(after["ranked"])}
    flips = []
    for other in pb:
        if other == doc:
            continue
        if (pb[doc] < pb[other]) != (pa[doc] < pa[other]):
            eb, ea = before["evidence"][doc], after["evidence"][doc]
            ob, oa = before["evidence"][other], after["evidence"][other]
            flips.append({
                "other": other,
                "before_decided_by": decisive(eb["stages"], ob["stages"]) if pb[doc] < pb[other] else decisive(ob["stages"], eb["stages"]),
                "after_decided_by": decisive(ea["stages"], oa["stages"]) if pa[doc] < pa[other] else decisive(oa["stages"], ea["stages"]),
                "other_applicability_after": oa["temporal_applicability"], "other_basis_after": oa["temporal_applicability_basis"],
                "other_clock_after": oa["temporal_ordering_clock"],
            })
    stages = Counter(f["after_decided_by"] for f in flips)
    if not flips:
        return "unexplained", flips
    top = stages.most_common(1)[0][0]
    if top == "temporal_applicability_tier":
        bases = {after["evidence"][doc]["temporal_applicability_basis"]} | {f["other_basis_after"] for f in flips}
        return ("interpreted_self_validity_demotion" if "interpreted" in bases else "unexplained"), flips
    if top == "temporal_order_within_query_regime":
        clocks = {after["evidence"][doc]["temporal_ordering_clock"]} | {f["other_clock_after"] for f in flips}
        return ("declared_observation_clock_tiebreak" if "declared_observed_at" in clocks else "unexplained"), flips
    if top.startswith(("lexical_relevance", "route_score")):
        return "lexical_numerical_only", flips
    return "unexplained", flips


out = {"before_mode": before_mode, "after_mode": after_mode, "source_sha256": hashlib.sha256(Path(source).read_bytes()).hexdigest(), "planes": {}}
for plane, ids in wanted.items():
    records = []
    for qid in sorted(ids):
        row = rows[qid]
        before, after = recall(row, plane, before_mode), recall(row, plane, after_mode)
        record = {"question_id": qid, "question_type": row["question_type"], "question": row["question"], "question_date": row["question_date"],
                  "query_temporal_intent": {k: (after["intent"] or {}).get(k) for k in ("mode", "posture", "confidence", "orders_temporally", "reference_time", "evidence")},
                  "admitted_set_identical": set(before["admitted"]) == set(after["admitted"]),
                  "gold": []}
        for doc in before["gold"]:
            if doc not in before["evidence"] and doc not in after["evidence"]:
                continue
            rank_before = before["ranked"].index(doc) + 1 if doc in before["ranked"] else None
            rank_after = after["ranked"].index(doc) + 1 if doc in after["ranked"] else None
            if rank_before == rank_after:
                continue
            mechanism, flips = attribute(before, after, doc)
            eb, ea = before["evidence"].get(doc, {}), after["evidence"].get(doc, {})
            record["gold"].append({
                "item": doc, "rank_before": rank_before, "rank_after": rank_after, "mechanism": mechanism,
                "applicability_before": eb.get("temporal_applicability"), "applicability_after": ea.get("temporal_applicability"),
                "basis_after": ea.get("temporal_applicability_basis"), "ordering_clock_before": eb.get("temporal_ordering_clock"),
                "ordering_clock_after": ea.get("temporal_ordering_clock"), "interpreted_validity_after": ea.get("interpreted_validity"),
                "source_timestamp_used": after["observed"].get(doc),
                "flipped_pairs": len(flips), "after_deciding_stages": dict(Counter(f["after_decided_by"] for f in flips)),
                "before_deciding_stages": dict(Counter(f["before_decided_by"] for f in flips)),
            })
        record["all_order_flip_stages"] = dict(Counter(
            decisive(after["evidence"][x]["stages"], after["evidence"][y]["stages"])
            for i, x in enumerate(after["ranked"][:50]) for y in after["ranked"][i + 1:50]
            if x in before["ranked"] and y in before["ranked"] and before["ranked"].index(x) > before["ranked"].index(y)))
        record["reproduces_report"] = {"before": before["ranked"][:50] == reports["before"][plane][qid],
                                       "after": after["ranked"][:50] == reports["after"][plane][qid]}
        records.append(record)
    out["planes"][plane] = {"rows": records, "mechanism_counts": dict(Counter(g["mechanism"] for r in records for g in r["gold"])),
                            "rows_reproducing_both_reports": sum(1 for r in records if all(r["reproduces_report"].values()))}
open(out_path, "w").write(json.dumps(out, indent=1, sort_keys=True, default=str) + "\n")
for plane, section in out["planes"].items():
    print(plane, len(section["rows"]), "reproduced", section["rows_reproducing_both_reports"], section["mechanism_counts"])
