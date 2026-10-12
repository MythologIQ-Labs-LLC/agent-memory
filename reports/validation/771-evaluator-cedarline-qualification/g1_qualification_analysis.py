"""Phase E evidence (validation-only, offline): would discriminative-term qualification help G1?

Rule under study (NOT implemented in any runtime): a served memory "qualifies"
only if it shares at least one query token whose document frequency within
the caller's admissible scope is at most 1/2 (a majority rule, not tuned).
Tokens use the runtime's own lexical tokenizer. Applied post hoc to the
unchanged runtime's served lists from phase-d-results.json; reports what
would be withheld, split into distractors, no-answer context and LOST
critical/relevant evidence.
"""
import json, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
EVAL = HERE.parents[2]
sys.path.insert(0, str(EVAL / "reference")); sys.path.insert(0, str(EVAL / "scripts"))
from agentmem_ref.state.sqlite_substrate import _tokens as _raw_tokens
NORMALIZE = "--normalize" in sys.argv


def _tokens(text):
    """Runtime tokenizer; with --normalize also folds possessive 's / s' (still no stopword list)."""
    toks = _raw_tokens(text)
    if not NORMALIZE:
        return toks
    return {t[:-2] if t.endswith("'s") else t[:-1] if t.endswith("s'") else t for t in toks}
import run_served_memory_lifecycle_scenarios as L
D = json.loads((HERE / "phase-d-results.json").read_text())
SRC = {"halcyon-v1.1": ("reports/validation/771-cloud-qualification/holdout/halcyon-holdout-v1.1-input.json",
                        "reports/validation/771-cloud-qualification/holdout/halcyon-holdout-v1-gold.json"),
       "cedarline-v1.1": ("reference/fixtures/evaluation/cedarline-independent-v1.1-input.json",
                          "reference/fixtures/evaluation/cedarline-independent-v1.1-gold.json")}
out = {}
for corpus, entry in D["corpora"].items():
    show = lambda p: json.loads(subprocess.run(["git", "-C", str(EVAL), "show", f"{entry['source_commit']}:{p}"], check=True, capture_output=True).stdout)
    inputs, gold = show(SRC[corpus][0]), {c["id"]: c for c in show(SRC[corpus][1])["cases"]}
    facts = L.lifecycle_facts(inputs)
    text = {e["id"]: e["text"] for e in inputs["events"] if "text" in e}
    scope = [f for f in facts["fact_ids"] if f not in set(facts["deleted"]) | set(facts["out_of_scope"])]
    df = {}
    for f in scope:
        for tok in _tokens(text[f]): df[tok] = df.get(tok, 0) + 1
    limit = len(scope) / 2
    withheld = {"distractor": [], "no_answer_context": [], "lost_critical": [], "lost_relevant": [], "other": []}
    emptied_no_answer, emptied_answerable = [], []
    for row in entry["variants"]["v7-9b025f9/composed-default"]["run"]["rows"]:
        case, q = gold[row["id"]], next(x for x in inputs["queries"] if x["id"] == row["id"])
        qt = _tokens(q["query"])
        crit = {r for g in case["critical_groups"] for r in g}
        kept = []
        for ref in row["returned"]:
            if any(df.get(t, 0) <= limit for t in (qt & _tokens(text[ref]))):
                kept.append(ref); continue
            key = ("no_answer_context" if not case["safe_answer_exists"] else
                   "lost_critical" if ref in crit else
                   "lost_relevant" if case["relevance"][ref] >= 1 else "distractor")
            withheld[key].append(f"{row['id']}:{ref}")
        if row["returned"] and not kept:
            (emptied_answerable if case["safe_answer_exists"] else emptied_no_answer).append(row["id"])
    out[corpus] = {"scope_size": len(scope), "non_discriminative_tokens": sorted(t for t, n in df.items() if n > limit),
                   "withheld": withheld, "no_answer_questions_emptied": emptied_no_answer,
                   "answerable_questions_emptied": emptied_answerable}
(HERE / ("g1-qualification-analysis" + ("-normalized" if NORMALIZE else "") + ".json")).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
for c, r in out.items():
    print(c, "scope", r["scope_size"], "non-discriminative:", r["non_discriminative_tokens"])
    print("  ", {k: len(v) for k, v in r["withheld"].items()}, "lost:", r["withheld"]["lost_critical"] + r["withheld"]["lost_relevant"])
    print("   no-answer emptied", r["no_answer_questions_emptied"], "answerable emptied", r["answerable_questions_emptied"])
