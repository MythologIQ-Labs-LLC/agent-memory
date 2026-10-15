"""Gate metrics and per-case comparison of the development runs (runs/*.json, same runner file)."""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SETS = ("diag", "c5-dev")
LABELS = {"A": "A-off", "C4": "C4-off", "C4+sem": "C4-sem", "C6": "C6-sem", "C6-off": "C6-off"}
expect = {}
kind = {}
for name in SETS:
    for s in json.load(open(HERE / f"{name}-scenarios.json"))["scenarios"]:
        for q in s["queries"]:
            expect[f"{name}:{q['id']}"] = q["expect"]
            kind[f"{name}:{q['id']}"] = q.get("kind", "c5-dev")


def load(label):
    rows = {}
    for name in SETS:
        for s in json.load(open(HERE / "runs" / f"{LABELS[label]}-{name}.json"))["scenarios"]:
            for q in s["queries"]:
                rows[f"{name}:{q['id']}"] = q
    return rows


def metrics(rows):
    needed = sum(len(expect[i]["must_include"]) for i in rows)
    got = sum(len(set(r["returned"]) & set(expect[i]["must_include"])) for i, r in rows.items())
    allowed = {i: set(expect[i]["must_include"]) | set(expect[i]["may_include"]) for i in rows}
    extra = sum(len([x for x in r["returned"] if x not in allowed[i]]) for i, r in rows.items())
    no_answer = sum(1 for i, r in rows.items() if not expect[i]["must_include"] and set(r["returned"]) - allowed[i])
    prec = [r["precision"] for r in rows.values() if r["precision"] is not None]
    return {"strict": sum(r["passed"] for r in rows.values()), "needed_recall": round(got / needed, 4),
            "extra": extra, "no_answer_returning": no_answer, "mean_precision": round(sum(prec) / len(prec), 4),
            "mean_returned": round(sum(r["returned_count"] for r in rows.values()) / len(rows), 3),
            "safety_violations": sum(len(r["safety_violations"]) for r in rows.values())}


def mcnemar(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


runs = {label: load(label) for label in LABELS}
out = {"metrics": {label: metrics(rows) for label, rows in runs.items()}}
m = out["metrics"]
out["gate"] = {
    "G1 needed recall >= C4 + 0.20": [m["C6"]["needed_recall"], round(m["C4"]["needed_recall"] + 0.20, 4), m["C6"]["needed_recall"] >= m["C4"]["needed_recall"] + 0.20],
    "G2 strict >= C4+sem + 3": [m["C6"]["strict"], m["C4+sem"]["strict"] + 3, m["C6"]["strict"] >= m["C4+sem"]["strict"] + 3],
    "G3 extra <= 0.75 x C4+sem": [m["C6"]["extra"], 0.75 * m["C4+sem"]["extra"], m["C6"]["extra"] <= 0.75 * m["C4+sem"]["extra"]],
    "G4 no-answer returning <= C4+sem": [m["C6"]["no_answer_returning"], m["C4+sem"]["no_answer_returning"], m["C6"]["no_answer_returning"] <= m["C4+sem"]["no_answer_returning"]],
    "G5 safety violations == 0": [m["C6"]["safety_violations"], 0, m["C6"]["safety_violations"] == 0],
    "G6 C6 off lists == C4 lists": [None, None, all(runs["C6-off"][i]["returned"] == runs["C4"][i]["returned"] for i in runs["C4"])],
}
out["paired_strict"] = {}
for other in ("A", "C4", "C4+sem"):
    gain = sorted(i for i in runs["C6"] if runs["C6"][i]["passed"] and not runs[other][i]["passed"])
    loss = sorted(i for i in runs["C6"] if not runs["C6"][i]["passed"] and runs[other][i]["passed"])
    out["paired_strict"][f"C6 vs {other}"] = {"improved": gain, "regressed": loss, "mcnemar_p": round(mcnemar(len(gain), len(loss)), 4)}
by_kind = {}
for i in runs["C6"]:
    k = kind[i]
    row = by_kind.setdefault(k, {label: 0 for label in LABELS} | {"n": 0})
    row["n"] += 1
    for label in LABELS:
        row[label] += runs[label][i]["passed"]
out["strict_by_kind"] = by_kind
(HERE / "comparison.json").write_text(json.dumps(out, indent=1) + "\n")
print(json.dumps({"metrics": m, "gate": out["gate"], "strict_by_kind": by_kind}, indent=1))
for key, v in out["paired_strict"].items():
    print(key, f"+{len(v['improved'])}/-{len(v['regressed'])} p={v['mcnemar_p']}", "regressed:", v["regressed"])
