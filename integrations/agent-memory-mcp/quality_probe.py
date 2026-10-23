"""Development-only Gate 2 probe through real MCP tools, with SQLite FTS5 comparator.

This is NOT a benchmark holdout, an agent answer-quality score, a release gate,
or a fair system cost parity study. It is a consumer-path diagnostic: which
governed evidence keys reach the harness, how much irrelevant evidence is
delivered, and whether unanswerable questions receive distracting context.

Install the Agent Memory reference package and MCP SDK v2, then run:
  python integrations/agent-memory-mcp/quality_probe.py \
    --out /tmp/agent-memory-quality-probe.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import re
import sqlite3
import statistics
import sys
import tempfile
import time
from typing import Any

from mcp import Client, StdioServerParameters

HERE = Path(__file__).resolve().parent
CASES = HERE / "quality_cases_dev.json"
SERVER = HERE / "server.py"
_WORD = re.compile(r"[^\W_]+", re.UNICODE)
_STOP = frozenset("""which where what when who does did is are the a an for from
and or to of it its do at by with we our their how has have in on be was were
there that this does use used""".split())


def lexical_terms(query: str) -> list[str]:
    return sorted({term for term in _WORD.findall(query.casefold())
                   if len(term) > 2 and term not in _STOP})


def fts_query(query: str) -> str:
    # Parameterized fts5 MATCH expression; all terms are quoted literals.
    # Do not splice untrusted user input into SQL or fts5 grammar.
    return " OR ".join('"' + token.replace('"', '""') + '"' for token in lexical_terms(query))


def build_fts(records: list[dict]) -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.execute("CREATE VIRTUAL TABLE facts USING fts5(logical_key UNINDEXED, content, tokenize='unicode61')")
    db.executemany("INSERT INTO facts(logical_key, content) VALUES (?,?)",
                   ((r["key"], r["text"]) for r in records))
    db.commit()
    return db


def fts_find(db: sqlite3.Connection, query: str, max_items: int) -> list[str]:
    terms = fts_query(query)
    if not terms:
        return []
    return [r[0] for r in db.execute(
        "SELECT logical_key FROM facts WHERE facts MATCH ? ORDER BY bm25(facts), rowid LIMIT ?",
        (terms, max_items),
    )]


def fully_delivered_keys(evidence: list[dict], seeded: dict[str, str]) -> list[str]:
    """The one full-delivery contract for every harness: a returned source counts as delivered
    evidence only when it arrived ``resolved``, attributed to its key, with its whole seeded text.
    A truncated, abridged, unresolved or unattributed item is returned burden, never evidence."""
    return [
        e["memory_ref"] for e in evidence
        if (isinstance(e.get("memory_ref"), str) and e.get("state") == "resolved" and
            e.get("content") == seeded.get(e["memory_ref"]))
    ]


def score(keys: list[str], required: list[str], forbidden: list[str], *,
          fully_delivered_keys: list[str]) -> dict:
    # A source-key hit is NOT full evidence coverage if the MCP package only
    # delivered part of the source, or lost its provenance. There is no default:
    # a caller must say which returned keys carried their whole text (review
    # 5628673295: a forgotten argument used to credit every returned key). For
    # the indexed FTS5 control the entire text of every returned source is
    # retrievable, so its caller passes the returned keys explicitly.
    observed, wanted = set(keys), set(required)
    eligible = set(fully_delivered_keys)
    if not eligible.issubset(observed):
        raise ValueError("fully delivered evidence must be a subset of returned keys")
    hits = len(eligible & wanted)
    extras = sum(key not in wanted for key in keys)
    return {
        "required_key_hits": len(observed & wanted),
        "required_hits": hits,
        "required_total": len(wanted),
        "required_complete": wanted.issubset(eligible) if wanted else None,
        "unexpected_evidence_items": extras,
        "forbidden_keys_present": sorted(observed & set(forbidden)),
        "empty_context_on_no_answer": len(keys) == 0 if not wanted else None,
        "evidence_precision": hits / len(keys) if keys else (None if not wanted else 0.0),
    }


def aggregate(rows: list[dict], arm: str) -> dict:
    x = [r[arm] for r in rows]
    answered = [o for o in x if o["required_total"]]
    no_answer = [o for o in x if not o["required_total"]]
    latencies = [r[arm + "_elapsed_ms"] for r in rows]
    rank = sorted(latencies)
    p95 = rank[min(len(rank) - 1, max(0, (95 * len(rank) + 99) // 100 - 1))]
    return {
        "answerable_complete": sum(o["required_complete"] is True for o in answered),
        "answerable_total": len(answered),
        "required_hits": sum(o["required_hits"] for o in answered),
        "required_total": sum(o["required_total"] for o in answered),
        "no_answer_empty_context": sum(o["empty_context_on_no_answer"] is True for o in no_answer),
        "no_answer_total": len(no_answer),
        "unexpected_evidence_items": sum(o["unexpected_evidence_items"] for o in x),
        "forbidden_key_incidences": sum(len(o["forbidden_keys_present"]) for o in x),
        "mean_evidence_precision_on_answerable": statistics.mean(
            o["evidence_precision"] for o in answered
        ) if answered else None,
        "p50_ms": statistics.median(latencies),
        "p95_ms": p95,
    }


def validate_cases(data: dict) -> None:
    keys = [r["key"] for r in data["records"]]
    if len(keys) != len(set(keys)) or not all(
        isinstance(r["key"], str) and r["key"].startswith("memory:")
        and isinstance(r["text"], str) and r["text"].strip()
        for r in data["records"]
    ):
        raise ValueError("invalid or duplicate corpus keys")
    ids = [t["id"] for t in data["tasks"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate task IDs")
    for task in data["tasks"]:
        if not isinstance(task["question"], str) or not task["question"].strip():
            raise ValueError("empty question")
        required, forbidden = set(task["required"]), set(task["forbidden"])
        if not required.issubset(keys) or not forbidden.issubset(keys) or required & forbidden:
            raise ValueError("invalid required/forbidden key sets")


async def run(cases: dict, k: int = 5, *, selectivity: bool = False) -> dict:
    """``selectivity`` is passed through as the tool's ``experimental_selectivity`` argument, so
    the two consumer profiles can be measured through the same real MCP path (Gate 2 before/after)."""
    if type(k) is not int or not 1 <= k <= 8:
        raise ValueError("MCP provider supports k from 1 to 8")
    if type(selectivity) is not bool:
        raise ValueError("selectivity must be a bool")
    validate_cases(cases)
    # This *small fictional development fixture* fits under both delivery
    # budgets for either arm, including the five highest-length documents.
    # Fail if someone expands the corpus until the comparator silently gains
    # a full-text advantage over the MCP char/token-bound package.
    sizes = sorted((len(r["text"]) for r in cases["records"]), reverse=True)
    if sizes and (sizes[0] > 1200 or sum(sizes[:k]) > 5000 or
                  sum((n + 3) // 4 for n in sizes[:k]) > 1250 or
                  any(not r["text"].isascii() for r in cases["records"])):
        raise ValueError("corpus no longer fits equal full-text capacity; redesign the comparator")
    by_key = {r["key"]: r["text"] for r in cases["records"]}
    fts = build_fts(cases["records"])
    with tempfile.TemporaryDirectory(prefix="am-mcp-quality-") as temp:
        env = {
            "AGENT_MEMORY_MCP_ROOT": str(Path(temp) / "store"),
            "AGENT_MEMORY_MCP_TENANT": cases["tenant"],
            "AGENT_MEMORY_MCP_ACTOR": "agent:quality-probe",
            "AGENT_MEMORY_MCP_SCOPE": cases["scope"],
            "PATH": os.environ.get("PATH", ""),
        }
        # Experiment branch: forward the bounded runtime candidate flag to the server.
        if os.environ.get("AGENT_MEMORY_EXPERIMENTAL_LEXICAL_ADMISSION"):
            env["AGENT_MEMORY_EXPERIMENTAL_LEXICAL_ADMISSION"] = os.environ["AGENT_MEMORY_EXPERIMENTAL_LEXICAL_ADMISSION"]
        params = StdioServerParameters(command=sys.executable, args=[str(SERVER)], env=env)
        rows = []
        async with Client(params) as client:
            tools = await client.list_tools()
            assert {"memory_remember", "memory_get", "memory_find"} <= {t.name for t in tools.tools}
            for record in cases["records"]:
                saved = await client.call_tool("memory_remember", {
                    "key": record["key"], "text": record["text"],
                })
                if saved.is_error or not (saved.structured_content or {}).get("committed"):
                    raise RuntimeError(f"failed governed write for {record['key']}: {saved!r}")
            # The two arms use the same inputs and k; FTS5 indexes the exact
            # supplied texts, but it does NOT pay the same governance/ingest
            # costs or apply scope and lifecycle controls.
            for task in cases["tasks"]:
                question = task["question"]
                start = time.perf_counter()
                result = await client.call_tool("memory_find", {
                    "question": question, "max_items": k,
                    "experimental_selectivity": selectivity,
                })
                mcp_ms = (time.perf_counter() - start) * 1000
                if result.is_error or not isinstance(result.structured_content, dict):
                    raise RuntimeError(f"failed MCP read for {task['id']}: {result!r}")
                content = result.structured_content
                evidence = content.get("evidence") or []
                # Include even unidentified items in served-context burden;
                # never silently erase a missing provenance item from scoring.
                mcp_keys = [e.get("memory_ref") if isinstance(e.get("memory_ref"), str)
                            else "<unattributed>" for e in evidence]
                mcp_full_keys = fully_delivered_keys(evidence, by_key)
                fts_start = time.perf_counter()
                fts_keys = fts_find(fts, question, k)
                fts_ms = (time.perf_counter() - fts_start) * 1000
                # We keep the literal keys and scores, but not memory content,
                # in the default receipt. All fixture texts are fictional.
                rows.append({
                    "id": task["id"], "question": question,
                    "gold": task["required"], "forbidden": task["forbidden"],
                    "mcp_keys": mcp_keys, "mcp_full_text_keys": mcp_full_keys,
                    "fts5_keys": fts_keys,
                    "mcp": score(mcp_keys, task["required"], task["forbidden"],
                                 fully_delivered_keys=mcp_full_keys),
                    "fts5": score(fts_keys, task["required"], task["forbidden"],
                                  fully_delivered_keys=fts_keys),
                    "mcp_unattributed_items": mcp_keys.count("<unattributed>"),
                    "mcp_incomplete_text_items": len(mcp_keys) - len(mcp_full_keys),
                    "mcp_unavailable_items": len(content.get("unavailable") or []),
                    "mcp_elapsed_ms": mcp_ms, "fts5_elapsed_ms": fts_ms,
                    "mcp_package_status": content.get("package_status"),
                    "mcp_profile": content.get("profile"),
                    "mcp_selection_assessment": content.get("selection_assessment"),
                    "mcp_selection_policy_version": content.get("selection_policy_version"),
                    # which returned facts the selector declined, with its versioned reason
                    "mcp_omitted": [
                        {"fact_ref": o.get("fact_ref"), "reason": o.get("reason"),
                         "absence_grounding": o.get("absence_grounding")}
                        for o in (content.get("unavailable") or []) if o.get("state") == "omitted_selection"
                    ],
                    "mcp_answer_generated": content.get("answer_generated"),
                })
                if content.get("answer_generated") is not False:
                    raise AssertionError("MCP provider must not claim to answer questions")
        fts.close()
    return {
        "schema": "mcp-gate2-retrieval-probe/0.1.0",
        "experimental_lexical_admission": os.environ.get("AGENT_MEMORY_EXPERIMENTAL_LEXICAL_ADMISSION") or None,
        "qualification": "author-visible development diagnostic only; NOT blinded",
        "measures": "full seeded source evidence coverage, key-only hits, distraction, empty-context; not answer correctness",
        "provider": ("real stdio MCP / governed SQLite / memory_find experimental_selectivity="
                     f"{selectivity} ({'evidence_qualified' if selectivity else 'all_returned'} profile)"),
        "selectivity": selectivity,
        "comparator": "indexed SQLite FTS5 unicode61 bm25 OR terms; not ingestion/security cost parity",
        "budget": {"max_items": k, "provider_char_cap": 5000, "provider_token_cap": 1250,
                   "fts5_char_cap": None, "fts5_token_cap": None,
                   "development_fixture_full_text_fits_both_caps": True,
                   "caveat": "FTS5 does not incur governed ingestion or MCP transport costs"},
        "dataset": {"records": len(cases["records"]), "tasks": len(cases["tasks"])},
        "summary": {"mcp": aggregate(rows, "mcp"), "fts5": aggregate(rows, "fts5")},
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=CASES)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-items", type=int, default=5)
    parser.add_argument("--selectivity", action="store_true",
                        help="call memory_find with experimental_selectivity=true (evidence_qualified profile)")
    args = parser.parse_args()
    data = json.loads(args.cases.read_text(encoding="utf-8"))
    report = asyncio.run(run(data, k=args.max_items, selectivity=args.selectivity))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
