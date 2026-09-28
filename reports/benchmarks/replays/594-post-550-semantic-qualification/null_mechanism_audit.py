"""#594: stage-level audit of why the adapted profiles change no ranking.

Usage: PYTHONPATH=reference python null_mechanism_audit.py SOURCE.json OUT.json

A change needs a query whose intent orders temporally, so this re-runs every such
question on both planes under the three profiles (none, source_observed_at,
host_declared), exactly as the runner ingests and recalls. Per question and
profile it records:
  * the full admitted ranking (compared across profiles);
  * the stage that separated each adjacent pair in the top 50 (``ordered_before_next_by``, emitted by the runtime);
  * applicability labels and bases of all admitted candidates;
  * every admitted memory with a resolved interpreted self-validity window: its rank, label, and window.
It also counts adjacent top-50 pairs decided by a temporal stage. Nothing is modified.
"""
import hashlib
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

import run_longmemeval as lme
from agentmem_ref import AgentMemory
from agentmem_ref.runtime import temporal_intent as ti

MODES = ("none", "source_observed_at", "host_declared")
source, out_path = Path(sys.argv[1]), Path(sys.argv[2])
raw = source.read_bytes()
data = json.loads(raw)


def recall(row, row_index, plane, mode):
    items, gold = lme.corpus(row, plane)
    with tempfile.TemporaryDirectory(prefix="agent-memory-594-audit-") as temporary:
        with AgentMemory.open(temporary, tenant=f"tenant:longmemeval:{row_index}", actor_id="agent:benchmark",
                              scope=f"benchmark:longmemeval:{row_index}", purpose="LongMemEval retrieval evaluation") as memory:
            uuid_to_item = {}
            for item_index, item in enumerate(items):
                declared = {}
                if mode != "none":
                    stamp = lme._iso_date(item["date"])
                    if stamp:
                        declared["observed_at"] = stamp
                retained = memory.remember(f"memory:longmemeval:{row_index}:{item_index}", item["text"], **declared)
                uuid_to_item[str(retained["fact_uuid"])] = item["id"]
            reference_time = lme._iso_date(row["question_date"]) if mode == "host_declared" else None
            result = memory.recall(str(row["question"]), reference_time=reference_time)
    ranked = [uuid_to_item[u] for u in result["admitted"]]
    evidence = {uuid_to_item[u]: d["ranking_evidence"] for u, d in result["admissions"].items() if "ranking_evidence" in d}
    top = ranked[:50]
    deciders = Counter(evidence[doc].get("ordered_before_next_by") for doc in top[:-1])
    windows = []
    for doc in ranked:
        validity = (evidence[doc].get("temporal_evidence") or {}).get("interpreted_validity")
        if validity:
            windows.append({"item": doc, "rank": ranked.index(doc) + 1, "is_gold": doc in gold,
                            "applicability": evidence[doc].get("temporal_applicability"),
                            "basis": evidence[doc].get("temporal_applicability_basis"),
                            "valid_from": validity.get("valid_from"), "valid_until": validity.get("valid_until")})
    return {
        "ranked": ranked,
        "admitted_count": len(ranked),
        "top50_adjacent_pair_deciders": dict(sorted(deciders.items())),
        "applicability": dict(sorted(Counter(e.get("temporal_applicability") for e in evidence.values()).items())),
        "interpreted_basis_labels": sum(1 for e in evidence.values() if e.get("temporal_applicability_basis") == "interpreted"),
        "ordering_clock": dict(sorted(Counter(e.get("temporal_ordering_clock") for e in evidence.values()).items())),
        "admitted_interpreted_windows": windows,
    }


out = {"input_sha256": hashlib.sha256(raw).hexdigest(), "modes": MODES, "planes": {}}
for plane in ("session", "turn"):
    records = []
    for row_index, row in enumerate(data):
        intent = ti.interpret_query(row["question"], reference_time=lme._iso_date(row["question_date"]))
        if not intent.orders_temporally:
            continue
        runs = {mode: recall(row, row_index, plane, mode) for mode in MODES}
        records.append({
            "question_id": row["question_id"], "question_type": row["question_type"], "question": row["question"],
            "intent": {"mode": intent.mode, "posture": intent.posture, "confidence": intent.confidence, "evidence": list(intent.evidence)},
            "ranking_identical_across_profiles": len({json.dumps(r["ranked"]) for r in runs.values()}) == 1,
            "first_difference_rank_vs_none": {mode: next((i + 1 for i, (x, y) in enumerate(zip(runs["none"]["ranked"], runs[mode]["ranked"])) if x != y), None) for mode in MODES[1:]},
            "gold_rank_by_profile": {mode: {doc: (runs[mode]["ranked"].index(doc) + 1 if doc in runs[mode]["ranked"] else None) for doc in lme.corpus(row, plane)[1]} for mode in MODES},
            "profiles": {mode: {k: v for k, v in r.items() if k != "ranked"} for mode, r in runs.items()},
        })
    temporal_decided = {mode: sum(r["profiles"][mode]["top50_adjacent_pair_deciders"].get(stage, 0)
                                  for r in records for stage in ("temporal_applicability_tier", "temporal_order_within_query_regime"))
                        for mode in MODES}
    out["planes"][plane] = {
        "ordering_intent_questions": len(records),
        "rankings_identical_across_profiles": sum(r["ranking_identical_across_profiles"] for r in records),
        "earliest_first_difference_rank": {mode: min((r["first_difference_rank_vs_none"][mode] for r in records if r["first_difference_rank_vs_none"][mode]), default=None) for mode in MODES[1:]},
        "gold_rank_changes_vs_none": {mode: sum(1 for r in records for doc, rank in r["gold_rank_by_profile"][mode].items() if rank != r["gold_rank_by_profile"]["none"][doc]) for mode in MODES[1:]},
        "top50_adjacent_pairs_decided_by_temporal_stage": temporal_decided,
        "top50_adjacent_pair_deciders_total": {mode: dict(sum((Counter(r["profiles"][mode]["top50_adjacent_pair_deciders"]) for r in records), Counter())) for mode in MODES},
        "questions_with_admitted_interpreted_window": {mode: sum(1 for r in records if r["profiles"][mode]["admitted_interpreted_windows"]) for mode in MODES},
        "interpreted_basis_labels": {mode: sum(r["profiles"][mode]["interpreted_basis_labels"] for r in records) for mode in MODES},
        "rows": records,
    }
    print(plane, {k: v for k, v in out["planes"][plane].items() if k != "rows"})
out_path.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
