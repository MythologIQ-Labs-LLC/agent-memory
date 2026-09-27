"""#583: per-question policy-3.0.2 lexical-query attribution for LongMemEval_S.

Usage: python lme_query_attribution.py <repo_root> <longmemeval_s_cleaned.json> <out.json>
Resolves each question's temporal intent exactly as the default replay does
(``resolve_intent(question)``; no caller intent, no reference time) and records the
cues ``relevance_query_for_intent`` excludes. Question text is not emitted.
"""
import hashlib, json, sys
from collections import Counter
from pathlib import Path

root, data, out = sys.argv[1:4]
sys.path.insert(0, str(Path(root) / "reference"))
from agentmem_ref.runtime import ranking_policy, temporal_intent  # noqa: E402

raw = Path(data).read_bytes()
rows = {}
for row in json.loads(raw):
    intent = temporal_intent.resolve_intent(row["question"])
    lexical, excluded = ranking_policy.relevance_query_for_intent(row["question"], intent)
    rows[row["question_id"]] = {"question_type": row["question_type"],
                                "intent": f"{intent.mode}/{intent.posture}/{intent.confidence}",
                                "orders_temporally": intent.orders_temporally,
                                "excluded_cues": list(excluded), "lexical_query_changed": lexical != row["question"]}
affected = {q: r for q, r in rows.items() if r["excluded_cues"]}
Path(out).write_text(json.dumps({
    "input_sha256": hashlib.sha256(raw).hexdigest(), "questions": len(rows),
    "ranking_policy": ranking_policy.POLICY_VERSION,
    "temporal_interpreter": temporal_intent.INTERPRETER_VERSION,
    "intent_distribution": dict(sorted(Counter(r["intent"] for r in rows.values()).items())),
    "affected_questions": len(affected),
    "affected_by_cue": dict(sorted(Counter(c for r in affected.values() for c in r["excluded_cues"]).items())),
    "affected_by_question_type": dict(sorted(Counter(r["question_type"] for r in affected.values()).items())),
    "affected_ids": sorted(affected), "rows": rows}, indent=1, sort_keys=True) + "\n")
