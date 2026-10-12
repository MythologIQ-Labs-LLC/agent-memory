"""Render PHASE_BD.md from phase-d-results.json. Every number is computed here.

Failure categories are assigned by fixed, corpus-independent rules over the
gold and the served IDs (no hand classification):
  stale_exposure        a stale-for-intent memory was served
  no_answer_context     no safe answer exists but context was served
  historical_target     historical question, answer not at rank 1
  why_target            stratum mentions why/reason/cause/explanation, answer not at rank 1
  multi_fact_incomplete >1 critical group and not all served
  unconfirmed_first     rank 1 is a grade-1 memory whose stratum is rumor/unreliable/contradiction
  current_top1_miss     current-intent answerable question, answer not at rank 1
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVAL_ROOT = HERE.parents[2]
D = json.loads((HERE / "phase-d-results.json").read_text())
VIEW = "v7-9b025f9/composed-default"


def _gold(corpus):
    sha = D["corpora"][corpus]["source_commit"]
    path = {"halcyon-v1.1": "reports/validation/771-cloud-qualification/holdout/halcyon-holdout-v1-gold.json",
            "cedarline-v1.1": "reference/fixtures/evaluation/cedarline-independent-v1.1-gold.json"}[corpus]
    raw = subprocess.run(["git", "-C", str(EVAL_ROOT), "show", f"{sha}:{path}"], check=True,
                         capture_output=True).stdout
    return {c["id"]: c for c in json.loads(raw)["cases"]}


def categories(case, served, stratum):
    crit = {r for g in case["critical_groups"] for r in g}
    top1 = bool(served) and served[0] in crit
    out = []
    if any(r in case["stale"] for r in served):
        out.append("stale_exposure")
    if not case["safe_answer_exists"]:
        if served:
            out.append("no_answer_context")
        return out
    s = (stratum or "").lower()
    if case["intent"] == "historical" and not top1:
        out.append("historical_target")
    if any(k in s for k in ("why", "reason", "cause", "explanation")) and not top1:
        out.append("why_target")
    if len(case["critical_groups"]) > 1 and not all(any(r in served for r in g) for g in case["critical_groups"]):
        out.append("multi_fact_incomplete")
    if served and case["relevance"][served[0]] == 1 and any(k in s for k in ("rumor", "unreliable", "contradiction")):
        out.append("unconfirmed_first")
    if case["intent"] == "current" and not top1:
        out.append("current_top1_miss")
    return out


def main():
    lines = ["# Phases B and D: Cedarline and Halcyon on the reference runtime, and #773 before/after (generated)", "",
             f"Explicit reference instant for `-T` modes: `{D['reference_time']}`. No composite score.", ""]
    cat_counts = {}
    for corpus, entry in D["corpora"].items():
        gold = _gold(corpus)
        lines += [f"## {corpus} (frozen at `{entry['source_commit'][:12]}`)", "",
                  "| Variant (runtime / mode) | runtime blob | P0 prohibited / stale | answer@1 | all critical | no-answer with context (items) | empty on answerable | precision@b | recall@b | nDCG@b | distractors |",
                  "|---|---|---|---|---|---|---|---|---|---|---|"]
        for name, v in sorted(entry["variants"].items()):
            p1, p2 = v["P1"], v["P2"]
            lines.append(f"| {name} | `{v['identity']['runtime_composition_blob'][:10]}` | "
                         f"{v['P0']['cases_with_prohibited_exposure']} / {v['P0']['cases_with_stale_exposure']} | "
                         f"{p1['top1_critical_rate']:.3f} | {p1['all_critical_groups_covered_rate']:.3f} | "
                         f"{p1['no_safe_answer_with_context_count']}/{p1['no_safe_answer_case_count']} ({p1['no_safe_answer_served_total']}) | "
                         f"{p1['empty_delivery_on_answerable_count']} | {p2['macro_relevant_precision']:.3f} | "
                         f"{p2['macro_relevant_recall_at_budget']:.3f} | {p2['macro_ndcg_at_budget']:.3f} | {p2['irrelevant_served_total']} |")
        lines += ["", "**Stability** (served rows / full ranked admissions that differ):", ""]
        for k, s in entry["stability"].items():
            lines.append(f"- {k}: served {s['served_rows_differ'] or 'none'}; ranked {s['ranked_admitted_differ'] or 'none'}")
        base = entry["variants"][VIEW]
        strata = {q["id"]: q["stratum"] for q in entry["before_after"]}
        lines += ["", f"### Per question, unchanged reference runtime ({VIEW})", "",
                  "| Q | stratum | intent | budget | served | answer@1 | critical | failure categories |",
                  "|---|---|---|---|---|---|---|---|"]
        for row, side in zip(base["run"]["rows"], base["per_query"]):
            case = gold[row["id"]]
            crit = {r for g in case["critical_groups"] for r in g}
            cats = categories(case, row["returned"], strata[row["id"]])
            for c in cats:
                cat_counts.setdefault(c, {}).setdefault(corpus, []).append(row["id"])
            t1 = ("✓" if row["returned"] and row["returned"][0] in crit else "✗") if case["safe_answer_exists"] else "n/a"
            cov = f'{sum(any(r in row["returned"] for r in g) for g in case["critical_groups"])}/{len(case["critical_groups"])}'
            lines.append(f"| {row['id']} | {strata[row['id']]} | {case['intent']} | {case['budget']} | "
                         f"{', '.join(row['returned']) or '∅'} | {t1} | {cov} | {', '.join(cats) or '–'} |")
        lines += ["", f"### #773 before/after at the same instant (v7 composed-T → #773 selector-T)", "",
                  "| Q | intent | before | after | change | excluded as known-not-current | valid evidence excluded |",
                  "|---|---|---|---|---|---|---|"]
        for q in entry["before_after"]:
            if q["intent"] != "current":
                continue
            lines.append(f"| {q['id']} | {q['intent']} | {', '.join(q['before']['served']) or '∅'} | "
                         f"{', '.join(q['after']['served']) or '∅'} | {', '.join(q['changes'])} | "
                         f"{', '.join(q['excluded_known_inapplicable']) or '–'} | {', '.join(q['valid_evidence_excluded']) or '–'} |")
        lines.append("")
    lines += ["## Failure categories across corpora (unchanged runtime, composed-default)", "",
              "| Category | Halcyon v1.1 | Cedarline v1.1 |", "|---|---|---|"]
    for cat in ("stale_exposure", "no_answer_context", "historical_target", "why_target",
                "multi_fact_incomplete", "unconfirmed_first", "current_top1_miss"):
        row = cat_counts.get(cat, {})
        lines.append(f"| {cat} | {', '.join(row.get('halcyon-v1.1', [])) or '–'} | {', '.join(row.get('cedarline-v1.1', [])) or '–'} |")
    (HERE / "PHASE_BD.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
