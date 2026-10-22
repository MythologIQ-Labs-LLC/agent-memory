"""Shared paired-evaluation helpers for the #819 evidence-qualified selector.

Arms on one governed store and one question:
  raw       the public recall() returned prefix (identifiers; the accepted lane protocol)
  default   recall_context(consumer_profile="all_returned") delivered facts (== raw)
  lexical   the REJECTED bc98e965 lexical_content rule, replayed post hoc over the default
            package (diagnosis only; the runtime carries no such code)
  eq        recall_context(consumer_profile="evidence_qualified") delivered facts
  fts5      a competent indexed SQLite FTS5 (unicode61, bm25) comparator over the same texts

Nothing here reads gold before retrieval; gold is joined after the arms ran.
"""
from __future__ import annotations

import re
import sqlite3
import time

# The rejected candidate's exact term rule (bc98e965 context_package._content_terms).
_REJECTED_GRAMMATICAL = frozenset(
    "a an the and or but if in on at of to for from with by as is are was were "
    "be been being do does did have has had how what when where which who whom whose".split()
)
# The competent indexed baseline's stop list (tools/jarvis_scale/experiment.py at 1d0de74c).
FTS_STOP = frozenset("a an and are as at be by did do does for from how i in is it me my of on or our the their to was were what when where which who with you your".split())
_FTS_TOKEN = re.compile(r"[a-z0-9]+")
CHARS = dict(max_chars_per_item=200_000, max_total_chars=50_000_000)  # never let budgets hide evidence


def rejected_terms(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.casefold())) - _REJECTED_GRAMMATICAL


def rejected_lexical_delivered(query: str, package: dict, admissions: dict) -> list[str]:
    """bc98e965: omit a resolved item whose routes are all lexical and whose content terms do not
    intersect the query's content terms. Replayed over the default package, never in runtime."""
    q = rejected_terms(query)
    out = []
    for item in package["items"]:
        if item["state"] not in ("resolved", "truncated"):
            continue
        decision = admissions.get(item["fact_ref"]) or {}
        nonlexical = any(h.get("route_id") and h.get("route_id") != "lexical" for h in decision.get("route_provenance") or ())
        if not nonlexical and not (q & rejected_terms(item["content"])):
            continue
        out.append(item["fact_ref"])
    return out


def delivered(package: dict) -> list[str]:
    return [i["fact_ref"] for i in package["items"] if i["state"] in ("resolved", "truncated")]


class FTS5Index:
    name = "sqlite_fts5_bm25"

    def __init__(self, docs):
        start = time.perf_counter()
        self.db = sqlite3.connect(":memory:")
        self.db.execute("CREATE VIRTUAL TABLE memories USING fts5(id UNINDEXED, text, tokenize='unicode61')")
        self.db.executemany("INSERT INTO memories(id, text) VALUES(?,?)", ((i, t) for i, t in docs))
        self.db.commit()
        self.build_ms = (time.perf_counter() - start) * 1000

    def search(self, query: str, limit: int) -> list[str]:
        ts = sorted(set(_FTS_TOKEN.findall(query.lower())) - FTS_STOP)
        if not ts or not limit:
            return []
        expression = " OR ".join(f'"{t}"' for t in ts)
        sql = "SELECT id FROM memories WHERE memories MATCH ? ORDER BY bm25(memories), id LIMIT ?"
        return [row[0] for row in self.db.execute(sql, (expression, limit))]

    def close(self):
        self.db.close()


def am_arms(memory, query: str, k: int) -> dict:
    """All Agent Memory arms for one question on an open handle; asserts raw recall invariance."""
    raw = memory.recall(query, budget=k)
    t = time.perf_counter()
    default = memory.recall_context(query, max_items=k, consumer_profile="all_returned", **CHARS)
    default_ms = (time.perf_counter() - t) * 1000
    t = time.perf_counter()
    eq = memory.recall_context(query, max_items=k, consumer_profile="evidence_qualified", **CHARS)
    eq_ms = (time.perf_counter() - t) * 1000
    after = memory.recall(query, budget=k)
    for key in ("candidates", "admitted", "returned", "return_policy"):
        assert raw[key] == after[key], key
    assert default["recall"]["returned"] == raw["returned"] == eq["recall"]["returned"]
    assert delivered(default) == raw["returned"], "default context must deliver exactly the returned prefix"
    assert default["status"] in ("empty", "complete"), default["status"]
    assert eq["status"] in ("empty", "complete"), eq["status"]
    sel = eq["selection"]
    return {
        "raw": list(raw["returned"]),
        "default": delivered(default),
        "lexical": rejected_lexical_delivered(query, default, raw["admissions"]),
        "eq": delivered(eq),
        "eq_selection": {
            "assessment": sel["assessment"], "delivered_count": sel["delivered_count"], "omitted_count": sel["omitted_count"],
            "uncertain_count": sel["uncertain_count"], "omitted_reasons": sel["omitted_reasons"],
            "decisions": {ref: {k2: v for k2, v in d.items() if k2 in ("outcome", "evidence", "reason", "certainty")}
                          for ref, d in sel["decisions"].items()},
        },
        "ms": {"default_context": default_ms, "eq_context": eq_ms},
    }


def score(delivered_ids: list[str], gold: list[str]) -> dict:
    g = set(gold)
    hits = len(set(delivered_ids) & g)
    return {
        "delivered": len(delivered_ids), "hits": hits, "gold": len(gold),
        "complete": (hits == len(g)) if g else None,
        "precision": (hits / len(delivered_ids)) if delivered_ids else None,
        "recall": (hits / len(g)) if g else None,
        "abstained": len(delivered_ids) == 0,
    }


def summarize(rows: list[dict], arms: tuple[str, ...]) -> dict:
    out = {}
    for arm in arms:
        scored = [r for r in rows if r["gold"]]
        noans = [r for r in rows if not r["gold"]]
        s = [r["scores"][arm] for r in scored]
        n = [r["scores"][arm] for r in noans]
        prec = [x["precision"] for x in s if x["precision"] is not None]
        out[arm] = {
            "scored_questions": len(scored), "complete": sum(1 for x in s if x["complete"]),
            "required_hits": sum(x["hits"] for x in s), "required_total": sum(x["gold"] for x in s),
            "delivered_total": sum(x["delivered"] for x in s),
            "micro_precision": (sum(x["hits"] for x in s) / sum(x["delivered"] for x in s)) if sum(x["delivered"] for x in s) else None,
            "macro_precision": (sum(prec) / len(prec)) if prec else None,
            "empty_on_answerable": sum(1 for x in s if x["abstained"]),
            "no_answer_questions": len(noans), "no_answer_abstained": sum(1 for x in n if x["abstained"]),
            "no_answer_delivered_total": sum(x["delivered"] for x in n),
        }
    # paired losses against the default arm: the blocking gate
    for arm in arms:
        if arm == "default":
            continue
        lost = [r["id"] for r in rows if r["gold"] and r["scores"]["default"]["hits"] > r["scores"][arm]["hits"]]
        gained = [r["id"] for r in rows if r["gold"] and r["scores"]["default"]["hits"] < r["scores"][arm]["hits"]]
        out[arm]["questions_losing_required_evidence_vs_default"] = lost
        out[arm]["questions_gaining_required_evidence_vs_default"] = gained
    return out
