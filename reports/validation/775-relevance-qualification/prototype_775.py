"""#775 research prototype: post-admission relevance qualification (evaluation-only).

Never imported by a runtime. Takes the UNCHANGED v7 composed served lists
(v3 runs with separated provenance) and applies candidate qualification rules
that may only REMOVE served items (no backfill, so nothing is broadened).
Measures, per rule and corpus:
  withheld_irrelevant   distractors (grade 0), stale or prohibited items removed
  lost_context          grade-1 context removed
  lost_legitimate       grade>=2 eligible evidence removed (FALSE NEGATIVES)
  critical_lost / top1_critical change / answerable emptied / no-answer emptied

Rules (no rule was tuned on any listed corpus; thresholds are structural):
  R1 discriminative-term: keep if the candidate shares >=1 query token that
     occurs in at most half of the admissible scope (possessive-folded)
  R2 anchored coverage: keep if the candidate contains the query's rarest
     in-scope token(s); if no query token occurs in scope, keep nothing
  R3 entity anchors: query tokens written with an initial capital (not the
     first word) are subject anchors; keep only candidates containing every
     anchor that exists in scope; if an anchor exists nowhere in scope, keep nothing
  R4 R1 and R3 together
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVAL = HERE.parents[2]
REPO = Path("/home/user/agent-memory")
V7 = Path("/tmp/claude-0/wt3/v7")
V3H = EVAL / "reports/validation/771-lifecycle-v3-provenance/holdouts"
CORPORA = {
    "northgate-v1 (frozen collision set)": (HERE / "holdout/northgate-v1-input.v3.json", None, HERE / "holdout/northgate-v1-gold.json"),
    "halcyon-v1.1": (V3H / "halcyon-v1.1-at-20261012T12Z.v3.json", "04543a79dbf3774e2d3381690fe4212cfe955614",
                     "reports/validation/771-cloud-qualification/holdout/halcyon-holdout-v1-gold.json"),
    "cedarline-v1.1": (V3H / "cedarline-v1.1-at-20261012T12Z.v3.json", "32404f7e0c800110cf7a72ba128479afc8bf0d83",
                       "reference/fixtures/evaluation/cedarline-independent-v1.1-gold.json"),
}
_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'\-]*")


def tokens(text):
    out = set()
    for w in _WORD.findall(text):
        w = w.lower()
        w = w[:-2] if w.endswith("'s") else w[:-1] if w.endswith("'") else w
        out.add(w)
    return out


def entity_anchors(query):
    words = _WORD.findall(query)
    return {w.lower().rstrip("'s").rstrip("'") if w.endswith("'s") else w.lower()
            for i, w in enumerate(words) if i > 0 and w[:1].isupper()}


def make_rules(scope_texts):
    df = {}
    for text in scope_texts.values():
        for t in tokens(text):
            df[t] = df.get(t, 0) + 1
    n = len(scope_texts)

    def r1(q, text):
        return any(df.get(t, 0) <= n / 2 for t in tokens(q) & tokens(text))

    def r2(q, text):
        present = {t: df[t] for t in tokens(q) if t in df}
        if not present:
            return False
        rarest = min(present.values())
        return any(t in tokens(text) for t, c in present.items() if c == rarest)

    def r3(q, text):
        anchors = entity_anchors(q)
        if any(a not in df for a in anchors):
            return False
        return all(a in tokens(text) for a in anchors)

    return {"R0 none": lambda q, t: True, "R1 discriminative-term": r1, "R2 anchored-coverage": r2,
            "R3 entity-anchors": r3, "R4 R1+R3": lambda q, t: r1(q, t) and r3(q, t)}


def baseline_runs(inp):
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "run.json"
        subprocess.run([sys.executable, str(EVAL / "scripts/served_memory_v3.py"), "run", "--runtime-root", str(V7),
                        "--inputs", str(inp), "--store", str(Path(tmp) / "store"), "--output", str(out),
                        "--lane-id", "775-baseline"], check=True)
        return json.loads(out.read_text())


def main():
    sys.path.insert(0, str(EVAL / "scripts"))
    import run_served_memory_lifecycle_scenarios as L
    import served_memory_v3 as v3
    results = {}
    for corpus, (inp, sha, gold_path) in CORPORA.items():
        data = json.loads(Path(inp).read_text())
        gold = (json.loads(Path(gold_path).read_text()) if sha is None else
                json.loads(subprocess.run(["git", "-C", str(REPO), "show", f"{sha}:{gold_path}"], check=True,
                                          capture_output=True).stdout))
        cases = {c["id"]: c for c in gold["cases"]}
        manifest = baseline_runs(inp)
        facts = L.lifecycle_facts(v3._v2_view(data))
        text = {e["id"]: e["text"] for e in data["events"] if "text" in e}
        scope = {f: text[f] for f in facts["fact_ids"] if f not in set(facts["deleted"]) | set(facts["out_of_scope"])}
        queries = {q["id"]: q["query"] for q in data["queries"]}
        rules = make_rules(scope)
        per_rule = {}
        for name, keep in rules.items():
            agg = {"withheld_irrelevant": 0, "lost_context": 0, "lost_legitimate": [], "critical_lost": [],
                   "top1_critical_before": 0, "top1_critical_after": 0, "all_critical_before": 0,
                   "all_critical_after": 0, "answerable_emptied": [], "no_answer_emptied": [],
                   "no_answer_items_before": 0, "no_answer_items_after": 0, "answerable": 0}
            for row in manifest["rows"]:
                c, q = cases[row["id"]], queries[row["id"]]
                before = row["returned"]
                after = [r for r in before if keep(q, text[r])]
                unsafe = set(c["stale"]) | set(c["prohibited"])
                crit = {r for g in c["critical_groups"] for r in g}
                for r in set(before) - set(after):
                    g = c["relevance"][r]
                    if r in unsafe or g == 0:
                        agg["withheld_irrelevant"] += 1
                    elif g == 1:
                        agg["lost_context"] += 1
                    else:
                        agg["lost_legitimate"].append(f"{row['id']}:{r}")
                if c["safe_answer_exists"]:
                    agg["answerable"] += 1
                    agg["top1_critical_before"] += bool(before) and before[0] in crit
                    agg["top1_critical_after"] += bool(after) and after[0] in crit
                    cov = lambda s: all(any(r in s for r in g) for g in c["critical_groups"])
                    agg["all_critical_before"] += cov(before)
                    agg["all_critical_after"] += cov(after)
                    if cov(before) and not cov(after):
                        agg["critical_lost"].append(row["id"])
                    if before and not after:
                        agg["answerable_emptied"].append(row["id"])
                else:
                    agg["no_answer_items_before"] += len(before)
                    agg["no_answer_items_after"] += len(after)
                    if before and not after:
                        agg["no_answer_emptied"].append(row["id"])
            per_rule[name] = agg
        results[corpus] = {"baseline_runtime": manifest["provenance"]["runtime"], "rules": per_rule}
    (HERE / "results-775.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    for corpus, r in results.items():
        print("=====", corpus)
        for name, a in r["rules"].items():
            print(f"  {name:24s} withheld_irrelevant {a['withheld_irrelevant']:2d} lost_ctx {a['lost_context']:2d} "
                  f"LOST_LEGIT {len(a['lost_legitimate']):2d} critical_lost {a['critical_lost']} "
                  f"t1c {a['top1_critical_before']}->{a['top1_critical_after']}/{a['answerable']} "
                  f"no-answer items {a['no_answer_items_before']}->{a['no_answer_items_after']} "
                  f"emptied ans {a['answerable_emptied']} noans {a['no_answer_emptied']}")


if __name__ == "__main__":
    main()
