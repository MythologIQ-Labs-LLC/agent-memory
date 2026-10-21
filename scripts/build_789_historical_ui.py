#!/usr/bin/env python3
"""Build read-only, non-promoted PrecisionMemBench v6 case diagnostics for UI.

All values derive from the three pinned source runs. Never imports a benchmark
score into accepted catalog/leaderboard. Does not copy prompts or gold data.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports/benchmarks/ui/historical-amb-v6.json"
BASE = "reports/benchmarks/amb/amb-precisionmembench-retrieval-v6"
SOURCE = (
    ("agent_memory", f"{BASE}/agent-memory-24048d55e26d/single-turn.json", "ea40e74850e2621ff39c65926c5ede89768e1a43"),
    ("mem0_oss", f"{BASE}/mem0-explicit-24048d55e26d/single-turn.json", "426a2f3c69220efcf5e461aef54aa593b4b82155"),
    ("bm25_control", f"{BASE}/bm25-24048d55e26d/single-turn.json", "4a7b779a2aed19dc4ef71d4fa5493b83220e6c92"),
)

def require(test, why):
    if not test:
        raise ValueError("historic AMB v6 evidence mismatch: " + why)

def build(root=ROOT):
    raw = {}
    for arm, path, sha in SOURCE:
        content = (root / path).read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
        require(blob == sha, "source Git blob " + arm)
        report = json.loads(content)
        require(report["dataset"] == "precisionmembench" and report["split"] == "single-turn" and report["mode"] == "retrieval", "source profile " + arm)
        require(report["total_queries"] == 77 and len(report["results"]) == 77 and len({r["query_id"] for r in report["results"]}) == 77, "source population " + arm)
        require(report["correct"] == sum(r["correct"] is True for r in report["results"]), "native correct total " + arm)
        raw[arm] = report
    maps = {a: {r["query_id"]: r for r in q["results"]} for a, q in raw.items()}
    cases = set(maps["agent_memory"])
    require(all(set(m) == cases for m in maps.values()), "case IDs")
    outcome_counts = {"agent_only": 0, "mem0_only": 0, "both_pass": 0, "both_fail": 0}
    categories = {}
    rows = []
    for cid in sorted(cases):
        source_rows = {a: m[cid] for a, m in maps.items()}
        first = source_rows["agent_memory"]
        require(all(r["query"] == first["query"] and r["gold_answers"] == first["gold_answers"] for r in source_rows.values()), "case query/gold " + cid)
        category = first["meta"]["category"]
        if category not in categories:
            categories[category] = dict(category=category, total=0, agent_memory=0, mem0_oss=0, bm25_control=0)
        counts = categories[category]; counts["total"] += 1
        a, m = (source_rows[k]["correct"] for k in ("agent_memory", "mem0_oss"))
        outcome = "both_pass" if a and m else "agent_only" if a else "mem0_only" if m else "both_fail"
        outcome_counts[outcome] += 1
        sys = {}
        for arm, r in source_rows.items():
            counts[arm] += int(r["correct"])
            failures = r["meta"].get("failures")
            require(isinstance(failures, list) and all(isinstance(f, str) for f in failures), "complete native failures")
            joined = "\n".join(failures)
            sys[arm] = {"pass": r["correct"], "unexpected": "unexpected belief" in joined,
                        "missing": "missing expected belief" in joined, "context_tokens": r["context_tokens"]}
        rows.append(dict(case_id=cid, category=category, outcome=outcome, systems=sys))
    systems = {}
    for arm, report in raw.items():
        p = [r["meta"]["retrieval_precision"] for r in report["results"] if isinstance(r["meta"].get("retrieval_precision"), (int, float)) and not isinstance(r["meta"].get("retrieval_precision"), bool)]
        v = [r["meta"]["retrieval_recall"] for r in report["results"] if isinstance(r["meta"].get("retrieval_recall"), (int, float)) and not isinstance(r["meta"].get("retrieval_recall"), bool)]
        require(p and v and abs(sum(p) / len(p) - report["mean_precision"]) < .000051 and abs(sum(v) / len(v) - report["mean_recall"]) < .000051, "native metric mean " + arm)
        systems[arm] = {"pass": report["correct"], "total": 77, "mean_precision": report["mean_precision"],
                        "precision_denominator": len(p), "mean_recall": report["mean_recall"], "recall_denominator": len(v)}
    diag = {"unexpected_only": 0, "missing_only": 0, "both": 0, "neither": 0}
    for r in rows:
        s = r["systems"]["agent_memory"]
        if s["pass"]:
            continue
        key = "both" if s["unexpected"] and s["missing"] else "unexpected_only" if s["unexpected"] else "missing_only" if s["missing"] else "neither"
        diag[key] += 1
    require(outcome_counts == {"agent_only": 6, "mem0_only": 1, "both_pass": 9, "both_fail": 61}, "native pairing")
    return {
        "schema_version": "historical-amb-v6-ui/1",
        "evidence_status": "historical_source_bound_not_promoted",
        "eligible_for_frontier_rankings": False,
        "authority_effect": "none",
        "source_main_sha": "3eebb6d54e2a218c4fd10cf53c52acac8384c3e6",
        "source_reports": [{"arm": arm, "path": path, "git_blob_sha": sha} for arm, path, sha in SOURCE],
        "review": {"selected_cases": 24, "completed_forms": 0, "required_forms": 96, "status": "not_started",
                   "selection_method": "all seven discordant cases, then first category cases, then lexical to 24"},
        "systems": systems,
        "pair_outcomes": outcome_counts,
        "agent_failure_diagnostics": diag,
        "categories": [categories[k] for k in sorted(categories)],
        "cases": rows,
    }

def main():
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true")
    action.add_argument("--write", action="store_true")
    args = parser.parse_args()
    data = build()
    if args.check:
        require(OUTPUT.exists() and json.loads(OUTPUT.read_text(encoding="utf-8")) == data, "generated projection out of date")
        print("historical AMB UI projection matches pinned native evidence")
    else:
        OUTPUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(OUTPUT)

if __name__ == "__main__":
    main()
