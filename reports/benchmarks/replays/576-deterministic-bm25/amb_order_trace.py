"""#576: trace every AgentMemBench agent_memory search (ordered results) and every BM25 score.

Usage: PYTHONHASHSEED=<n> python amb_order_trace.py <repo_root> <trace_out.json> -- <run_agentmembench args>

Evidence-only wrapper: it imports the unmodified harness from <repo_root>, records the
ordered top-k returned by each ``AgentMemoryAdapter.search`` call and the float.hex of
every ``admitted_set_bm25`` score, then runs the harness ``main`` with the given args.
Concurrency-phase writes are threaded, but the harness issues no recalls there, so the
recorded call sequence is deterministic.
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


searches, scores = [], []
_search = amb.AgentMemoryAdapter.search
_bm25 = ranking_policy.admitted_set_bm25


def search(self, query, user_id, limit):
    result = _search(self, query, user_id, limit)
    searches.append({"query": h(query), "user": user_id, "limit": limit, "returned": [h(t) for t in result]})
    return result


def bm25(query, texts):
    result = _bm25(query, texts)
    scores.append({"query": h(query), "scores": sorted((h(texts[ref]), score.hex()) for ref, score in result.items())})
    return result


amb.AgentMemoryAdapter.search = search
ranking_policy.admitted_set_bm25 = bm25
sys.argv = ["run_agentmembench.py", *rest]
code = amb.main()


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, separators=(",", ":")).encode()).hexdigest()


Path(trace_out).write_text(json.dumps({
    "pythonhashseed": os.environ.get("PYTHONHASHSEED"), "repo_root": str(root), "args": rest,
    "search_calls": len(searches), "bm25_calls": len(scores),
    "search_order_digest": digest(searches), "bm25_score_digest": digest(scores),
    "searches": searches, "bm25": scores,
}) + "\n")
raise SystemExit(code)
