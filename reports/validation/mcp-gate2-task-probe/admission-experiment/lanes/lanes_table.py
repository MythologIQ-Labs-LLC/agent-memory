"""Tabulate the paired lanes: PR head (0.5.1), experiment flag off, experiment flag on; FTS5 from each.

usage: lanes_table.py LANES_DIR
"""
import json
import sys
from pathlib import Path

L = Path(sys.argv[1])
KEYS = ("complete", "scored_questions", "required_hits", "required_total", "delivered_total",
        "no_answer_delivered_total", "no_answer_abstained", "no_answer_questions")


def lme_totals(summary, arm):
    out = dict.fromkeys(KEYS, 0)
    for per_type in summary["by_question_type"].values():
        for key in KEYS:
            out[key] += per_type.get(arm, {}).get(key, 0) or 0
    return out


def row(label, t):
    return (f"| {label} | {t['complete']}/{t['scored_questions']} | {t['required_hits']}/{t['required_total']} | "
            f"{t['delivered_total']:,} | {t['no_answer_abstained']}/{t['no_answer_questions']} "
            f"({t['no_answer_delivered_total']:,} items) |")


def ids(directory, arm):
    rows = [json.loads(line) for line in (directory / "rows.jsonl").read_text().splitlines() if line.strip()]
    return {r["id"]: r["ids"][arm] for r in rows}


for plane in ("session", "turn"):
    runs = {"pr": L / f"pr-lme-{plane}", "off": L / f"lme-{plane}-off", "on": L / f"lme-{plane}-content_term"}
    if not all((d / "summary.json").exists() for d in runs.values()):
        print(f"\n(lme {plane}: incomplete)")
        continue
    s = {k: json.loads((d / "summary.json").read_text()) for k, d in runs.items()}
    print(f"\n### LongMemEval_S {plane}, 500 questions, k={s['pr']['budget_k']} (input {s['pr']['input_sha256'][:12]})\n")
    print("| arm | complete | required items | delivered items | no-answer abstained (items delivered) |")
    print("|---|---|---|---|---|")
    print(row("default `all_returned`, PR head `db81778c`", lme_totals(s["pr"], "default")))
    print(row("opt-in 0.5.1, PR head", lme_totals(s["pr"], "eq")))
    print(row("default, experiment flag off", lme_totals(s["off"], "default")))
    print(row("opt-in 0.5.2, experiment flag off", lme_totals(s["off"], "eq")))
    print(row("**default, content-term admission ON**", lme_totals(s["on"], "default")))
    print(row("**opt-in 0.5.2, content-term admission ON**", lme_totals(s["on"], "eq")))
    print(row("SQLite FTS5", lme_totals(s["pr"], "fts5")))
    same = ids(runs["pr"], "default") == ids(runs["off"], "default")
    print(f"\ndefault-arm returned ids, PR head vs experiment flag off, all {len(ids(runs['pr'], 'default'))} questions identical: {same}")

for name in ("locomo",):
    runs = {"pr": L / "pr-locomo", "off": L / "locomo-off", "on": L / "locomo-content_term"}
    if not all((d / "summary.json").exists() for d in runs.values()):
        print(f"\n({name}: incomplete)")
        continue
    s = {k: json.loads((d / "summary.json").read_text()) for k, d in runs.items()}
    print(f"\n### LoCoMo (AMB export locomo10 @ 03c1d0f1), {s['pr']['questions']} questions, k={s['pr']['k']}\n")
    print("| arm | complete | required items | delivered items | no-answer abstained (items delivered) |")
    print("|---|---|---|---|---|")
    for label, key, arm in (("default, PR head", "pr", "default"), ("opt-in 0.5.1, PR head", "pr", "eq"),
                            ("default, flag off", "off", "default"), ("opt-in 0.5.2, flag off", "off", "eq"),
                            ("**default, admission ON**", "on", "default"), ("**opt-in 0.5.2, admission ON**", "on", "eq"),
                            ("SQLite FTS5", "pr", "fts5")):
        print(row(label, s[key]["summary"][arm]))

print("\n### #825 synthetic workload (14 cases, single-sentence facts, k=5, 3 repeats)\n")
print("| size | arm | needed | strict | primary extras | forbidden | abstention |")
print("|---|---|---|---|---|---|---|")
for size in (1000, 19000):
    for flag in ("off", "content_term"):
        f = L / f"scale-{size}-{flag}" / "scale.json"
        if not f.exists():
            print(f"| {size} | ({flag}: incomplete) |")
            continue
        for r in json.loads(f.read_text())["results"]:
            if flag == "content_term" and r["arm"] == "sqlite_fts5_bm25":
                continue
            label = r["arm"] if r["arm"] == "sqlite_fts5_bm25" else f"{r['arm']} (flag {flag})"
            print(f"| {size} | {label} | {r['needed_returned']}/{r['needed_total']} | {r['primary_strict']} | "
                  f"{r['primary_extras']} | {r['forbidden_returned']} | {r['abstention_correct']}/{r['abstention_total']} |")
