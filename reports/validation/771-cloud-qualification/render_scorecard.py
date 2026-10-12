"""Render SCORECARD.md from measurements-baseline.json (no hand-transcribed numbers)."""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _pct(value):
    return "n/a" if value is None else f"{value:.3f}"


def main():
    m = json.loads((HERE / "measurements-baseline.json").read_text())
    lines = [f"# #771 served-memory scorecard (generated)", "",
             f"Runtime revision measured: `{m['runtime_revision']}` (runtime files identical to candidate `23321e4`).",
             "No composite score. P0–P2 are independent; P3 is in its own section.", ""]
    for corpus, entry in m["corpora"].items():
        lines += [f"## {corpus}", "", f"Inputs `{entry['input_path']}`, gold `{entry['gold_path']}`.", ""]
        lines += ["| Dimension | composed-multiroute | governed-lexical |", "|---|---|---|"]
        s = {b: d["report_summary"] for b, d in entry["backends"].items()}
        rows = [
            ("P0 cases with prohibited exposure", lambda x: x["P0_safety"]["cases_with_prohibited_exposure"]),
            ("P0 cases with stale exposure", lambda x: x["P0_safety"]["cases_with_stale_exposure"]),
            ("P1 answerable / no-safe-answer cases", lambda x: f'{x["P1_served_correctness"]["answerable_case_count"]} / {x["P1_served_correctness"]["no_safe_answer_case_count"]}'),
            ("P1 correct memory at rank 1 (answerable)", lambda x: _pct(x["P1_served_correctness"]["top1_relevant_rate"])),
            ("P1 all critical evidence groups covered", lambda x: _pct(x["P1_served_correctness"]["all_critical_groups_covered_rate"])),
            ("P1 empty context on answerable", lambda x: x["P1_served_correctness"]["empty_delivery_on_answerable_count"]),
            ("P1 no-safe-answer: empty / with context (items)", lambda x: f'{x["P1_served_correctness"]["no_safe_answer_empty_context_count"]} / {x["P1_served_correctness"]["no_safe_answer_with_context_count"]} ({x["P1_served_correctness"]["no_safe_answer_served_total"]})'),
            ("P1 answer abstention", lambda x: x["P1_served_correctness"]["answer_abstention_status"]),
            ("P2 macro precision @budget", lambda x: _pct(x["P2_context_utility"]["macro_relevant_precision"])),
            ("P2 macro recall @budget", lambda x: _pct(x["P2_context_utility"]["macro_relevant_recall_at_budget"])),
            ("P2 macro nDCG @budget", lambda x: _pct(x["P2_context_utility"]["macro_ndcg_at_budget"])),
            ("P2 macro critical coverage", lambda x: _pct(x["P2_context_utility"]["macro_critical_coverage"])),
            ("P2 distractors served (total)", lambda x: x["P2_context_utility"]["irrelevant_served_total"]),
        ]
        for label, fn in rows:
            lines.append(f"| {label} | {fn(s['composed-multiroute'])} | {fn(s['governed-lexical'])} |")
        lines.append("")
        for backend, data in entry["backends"].items():
            lines += [f"### {corpus} — {backend}: per query", "",
                      "| Q | stratum | intent | budget | served (rank order) | top1 | critical | stale | prohibited | distractors | critical past budget | order-perm changed |",
                      "|---|---|---|---|---|---|---|---|---|---|---|---|"]
            for q in data["per_query"]:
                lines.append("| {id} | {st} | {intent} | {budget} | {ret} | {t1} | {crit} | {stale} | {proh} | {dis} | {late} | {perm} |".format(
                    id=q["id"], st=q["stratum"] or "", intent=q["intent"], budget=q["budget"],
                    ret=", ".join(q["returned"]) or "∅",
                    t1=("✓" if q["top1_relevant"] else "✗") if q["safely_answerable"] else "n/a (no safe answer)",
                    crit=q["critical"], stale=", ".join(q["stale_served"]) or "–",
                    proh=", ".join(q["prohibited_served"]) or "–",
                    dis=len(q["distractors_served"]), late=", ".join(q["critical_ranked_beyond_budget"]) or "–",
                    perm=q["order_permutations_changed"]))
            p3 = data["P3_engineering"]
            lines += ["", f"P3 (engineering only): governed build + {p3['queries']} queries in {p3['store_build_plus_all_queries_seconds']} s on a fresh store. {p3['note']}.", ""]
    (HERE / "SCORECARD.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
