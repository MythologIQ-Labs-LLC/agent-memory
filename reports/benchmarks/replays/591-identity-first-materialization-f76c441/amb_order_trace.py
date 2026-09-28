"""#583: trace every AgentMemBench agent_memory search, BM25 score, and consumed-cue exclusion.

Usage: PYTHONHASHSEED=<n> python amb_order_trace.py <repo_root> <trace_out.json> -- <run_agentmembench args>

Evidence-only wrapper (extends the #576 tracer). It imports the unmodified harness from
<repo_root> and records, per ``AgentMemoryAdapter.search`` call, the ordered top-k
returned and, when the runtime has policy 3.0.2's ``relevance_query_for_intent``, the
temporal cues it excluded from the lexical query. Query and memory texts are recorded
only as truncated SHA-256 digests; excluded cues are interpreter vocabulary, not corpus text.
"""
import hashlib, json, os, sys
from pathlib import Path

root, trace_out = Path(sys.argv[1]).resolve(), sys.argv[2]
rest = sys.argv[sys.argv.index("--") + 1:]
sys.path.insert(0, str(root / "reference"))
import run_agentmembench as amb  # noqa: E402
from agentmem_ref.runtime import ranking_policy  # noqa: E402


def h(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


searches, scores, pending = [], [], []
_search = amb.AgentMemoryAdapter.search
_bm25 = ranking_policy.admitted_set_bm25
_relevance = getattr(ranking_policy, "relevance_query_for_intent", None)


def search(self, query, user_id, limit):
    pending.clear()
    result = _search(self, query, user_id, limit)
    searches.append({"query": h(query), "user": user_id, "limit": limit, "returned": [h(t) for t in result],
                     "excluded_cues": sorted({c for item in pending for c in item["excluded"]}),
                     "intent": sorted({item["intent"] for item in pending})})
    return result


def bm25(query, texts):
    result = _bm25(query, texts)
    scores.append({"query": h(query), "scores": sorted((h(texts[ref]), score.hex()) for ref, score in result.items())})
    return result


def relevance(query, intent):
    lexical, excluded = _relevance(query, intent)
    pending.append({"excluded": list(excluded),
                    "intent": f"{intent.mode}/{intent.posture}/{intent.confidence}"})
    return lexical, excluded


amb.AgentMemoryAdapter.search = search
ranking_policy.admitted_set_bm25 = bm25
if _relevance is not None:
    ranking_policy.relevance_query_for_intent = relevance
sys.argv = ["run_agentmembench.py", *rest]
code = amb.main()


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, separators=(",", ":")).encode()).hexdigest()


Path(trace_out).write_text(json.dumps({
    "pythonhashseed": os.environ.get("PYTHONHASHSEED"), "repo_root": str(root), "args": rest,
    "relevance_hook_present": _relevance is not None,
    "search_calls": len(searches), "bm25_calls": len(scores),
    "search_order_digest": digest([{k: s[k] for k in ("query", "user", "limit", "returned")} for s in searches]),
    "bm25_score_digest": digest(scores),
    "searches": searches, "bm25": scores,
}) + "\n")
raise SystemExit(code)
