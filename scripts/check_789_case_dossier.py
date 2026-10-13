"""Replay AMB v6 competitive dossier against the pinned native raw reports.

No network, inference, leaderboard write or reviewer score. Run from repo root:
python scripts/check_789_case_dossier.py
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from pathlib import Path

ARMS = ("agent_memory", "mem0_oss", "bm25_control")
DOSSIER = "reports/benchmarks/audits/789-amb-v6-case-dossiers.json"


def require(ok: bool, label: str) -> None:
    if not ok:
        raise ValueError("dossier source mismatch: " + label)


def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def source_load(root: Path, dossier: dict) -> dict:
    loaded = {}
    for ref in dossier["source_reports"]:
        arm = ref["arm"]
        require(arm in ARMS and arm not in loaded, "invalid or repeated arm")
        path = (root / ref["path"]).resolve()
        require(path.is_relative_to(root.resolve()), "path outside repository")
        data = path.read_bytes()
        require(blob_sha(data) == ref["git_blob_sha"], "native Git blob " + arm)
        loaded[arm] = json.loads(data)
    return loaded


def diagnostics(row: dict) -> dict:
    # The native judge_reason may be truncated. Use complete meta.failures.
    failures = row.get("meta", {}).get("failures", [])
    require(isinstance(failures, list) and all(isinstance(v, str) for v in failures), "native failures")
    joined = "\n".join(failures)
    return {
        "unexpected_belief": "unexpected belief" in joined,
        "missing_expected_belief": "missing expected belief" in joined,
        "pass": row["correct"],
    }


def selected_cases(entries: list[dict], count: int) -> list[str]:
    chosen = {r["case_id"] for r in entries if r["outcome"] in ("agent_only", "mem0_only")}
    for category in sorted({r["benchmark_category"] for r in entries}):
        options = sorted(r["case_id"] for r in entries if r["benchmark_category"] == category and r["case_id"] not in chosen)
        if options:
            chosen.add(options[0])
    for case_id in sorted(r["case_id"] for r in entries):
        if len(chosen) >= count:
            break
        chosen.add(case_id)
    require(len(chosen) == count, "selection capacity")
    return sorted(chosen)


def validate_dossier(dossier: dict, reports: dict, *, expected_count: int = 77, review_count: int = 24) -> dict:
    require(dossier.get("schema_version") == "competitive-case-dossier/1", "schema")
    refs = dossier.get("source_reports", [])
    require(len(refs) == len(ARMS) and {r["arm"] for r in refs} == set(ARMS), "source set")
    require(set(reports) == set(ARMS), "loaded source set")
    all_rows = {}
    for ref in refs:
        arm = ref["arm"]
        raw = reports[arm]
        rows = raw["results"]
        ids = [x["query_id"] for x in rows]
        require(len(ids) == len(set(ids)) == expected_count, "query count/duplicates " + arm)
        require(raw["total_queries"] == ref["total_queries"] == expected_count, "native denominator " + arm)
        require(raw["run_name"] == ref["run_name"], "native run identity " + arm)
        require(raw["dataset"] == "precisionmembench" and raw["split"] == "single-turn" and raw["mode"] == "retrieval", "lane identity " + arm)
        require(sum(row["correct"] is True for row in rows) == raw["correct"], "native pass total " + arm)
        all_rows[arm] = {x["query_id"]: x for x in rows}
    cases = set(all_rows[ARMS[0]])
    require(all(set(rows) == cases for rows in all_rows.values()), "paired case IDs")
    entries = dossier["entries"]
    require(len(entries) == expected_count and len({r["case_id"] for r in entries}) == expected_count, "dossier duplicate/missing cases")
    require({r["case_id"] for r in entries} == cases, "dossier case set")
    pair = Counter()
    categories = {}
    for entry in entries:
        case = entry["case_id"]
        native = {arm: all_rows[arm][case] for arm in ARMS}
        first = native[ARMS[0]]
        require(all(x["query"] == first["query"] and x["gold_answers"] == first["gold_answers"] for x in native.values()), "query/gold join " + case)
        category = first["meta"]["category"]
        require(entry["source_row_key"] == case and entry["benchmark_category"] == category, "case metadata " + case)
        require(set(entry["arms"]) == set(ARMS), "case arm set " + case)
        for arm, raw in native.items():
            shown = entry["arms"][arm]
            require(shown["passed_native_scorer"] is raw["correct"], "verdict " + case + "/" + arm)
            require(shown["context_tokens"] == raw["context_tokens"] and shown["retrieval_ms"] == raw["retrieve_time_ms"], "observations " + case + "/" + arm)
            require(shown["diagnostic_flags"] == diagnostics(raw), "complete failures " + case + "/" + arm)
        a, m = native["agent_memory"]["correct"], native["mem0_oss"]["correct"]
        outcome = "both_pass" if a and m else "agent_only" if a else "mem0_only" if m else "both_fail"
        require(entry["outcome"] == outcome, "pair outcome " + case)
        pair[outcome] += 1
        if category not in categories:
            categories[category] = {"category": category, "case_count": 0, "agent_pass": 0, "mem0_pass": 0, "bm25_pass": 0}
        c = categories[category]
        c["case_count"] += 1
        for arm, field in (("agent_memory", "agent_pass"), ("mem0_oss", "mem0_pass"), ("bm25_control", "bm25_pass")):
            c[field] += int(native[arm]["correct"])
    summary = dossier["summary"]
    require(summary["count"] == expected_count, "summary count")
    require(summary["pair_outcomes"] == dict(pair), "pair outcomes")
    require(summary["category_breakdown"] == [categories[x] for x in sorted(categories)], "category breakdown")
    for arm in ARMS:
        raw = reports[arm]
        require(summary["correct"][arm] == raw["correct"], "summary pass " + arm)
        require(math.isclose(summary["native_accuracy"][arm], raw["accuracy"], abs_tol=1e-10), "summary accuracy " + arm)
        for label, source_field in (("native_mean_precision", "mean_precision"), ("native_mean_recall", "mean_recall")):
            require(math.isclose(summary[label][arm], raw[source_field], abs_tol=1e-10), "summary " + label + "/" + arm)
    discordant = pair["agent_only"] + pair["mem0_only"]
    p = min(1.0, 2 * sum(math.comb(discordant, i) for i in range(min(pair["agent_only"], pair["mem0_only"]) + 1)) / (2 ** discordant))
    require(math.isclose(summary["mcnemar_exact_two_sided_agent_vs_mem0"], p, abs_tol=1e-10), "paired significance")
    require(dossier["review_selection"]["target_case_ids"] == selected_cases(entries, review_count), "frozen sample")
    require(dossier.get("accepted_score_update") is False and dossier.get("qualitative_review_status") == "not_started", "unauthorized promotion")
    return {"status": "source_replay_pass", "cases": len(entries), "pair": dict(pair), "sample_cases": review_count, "source_blobs_verified_by_cli": True}


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    dossier = json.loads((root / DOSSIER).read_text(encoding="utf-8"))
    result = validate_dossier(dossier, source_load(root, dossier))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
