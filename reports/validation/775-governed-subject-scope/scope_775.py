"""#775 evaluation-only prototype: governed subject identity + caller-declared entity scope.

Never imported by a runtime. Baseline served lists: UNCHANGED v7 composed recall
(v3 runner of adopted evaluator 9961067, instant T). Rules only REMOVE items (no
backfill). An item is withheld only when its memory has a declared subject AND the
caller declared a scope AND the subject is not in the scope. Missing identity on
either side is uncertainty, never exclusion.

Variants
  E1 caller scope         frozen pass-2 scopes against frozen pass-1 subjects
  E1-wrong                wrong-subject control: each declared scope replaced by the
                          next registry subject (sorted) of the same corpus
  E1-half                 coverage control: every other memory (sorted) loses its subject
  E2 lexical resolver     scope = registry subjects whose normalized name occurs in the
                          question (no frequency or capitalization signal); none -> no scope
  paraphrase              E2 resolution on reviewer paraphrases vs the caller scope
"""
from __future__ import annotations

import json, re, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVAL = Path("/tmp/claude-0/wt5/ev")
REPO = Path("/home/user/agent-memory")
V7 = Path("/tmp/claude-0/wt3/v7")
V3H = Path("/tmp/claude-0/wt4/prov/reports/validation/771-lifecycle-v3-provenance/holdouts")
CORPORA = {
    "northgate": (HERE.parent / "775-relevance-qualification/holdout/northgate-v1-input.v3.json",
                  (None, HERE.parent / "775-relevance-qualification/holdout/northgate-v1-gold.json")),
    "halcyon": (V3H / "halcyon-v1.1-at-20261012T12Z.v3.json", ("04543a79dbf3774e2d3381690fe4212cfe955614",
                "reports/validation/771-cloud-qualification/holdout/halcyon-holdout-v1-gold.json")),
    "cedarline": (V3H / "cedarline-v1.1-at-20261012T12Z.v3.json", ("32404f7e0c800110cf7a72ba128479afc8bf0d83",
                  "reference/fixtures/evaluation/cedarline-independent-v1.1-gold.json")),
    "brightwater": (Path("/tmp/claude-0/wt4/v774/reports/validation/774-predecessor-quality/holdout/brightwater-v1-input.v3.json"),
                    (None, Path("/tmp/claude-0/wt4/v774/reports/validation/774-predecessor-quality/holdout/brightwater-v1-gold.json"))),
    "fenmoor": (Path("/tmp/claude-0/wt5/v774b/reports/validation/774-anchor-guard-and-routing/holdout/fenmoor-v1-input.v3.json"),
                (None, Path("/tmp/claude-0/wt5/v774b/reports/validation/774-anchor-guard-and-routing/holdout/fenmoor-v1-gold.json"))),
}
SUBJECTS = json.loads((HERE / "declarations/memory-subjects.json").read_text())
SCOPES = json.loads((HERE / "declarations/query-scopes.json").read_text())
norm = lambda s: re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def gold(spec):
    sha, path = spec
    return json.loads(Path(path).read_text()) if sha is None else json.loads(
        subprocess.run(["git", "-C", str(REPO), "show", f"{sha}:{path}"], check=True, capture_output=True).stdout)


def served(inp, corpus):
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "run.json"
        subprocess.run([sys.executable, str(EVAL / "scripts/served_memory_v3.py"), "run", "--runtime-root", str(V7),
                        "--inputs", str(inp), "--store", str(Path(tmp) / "s"), "--output", str(out),
                        "--lane-id", f"775-scope-{corpus}"], check=True, capture_output=True)
        return json.loads(out.read_text())


def resolve(query, registry):
    q = f" {norm(query)} "
    return [s for s in registry if f" {norm(s)} " in q] or None


def measure(manifest, cases, fact_subject, scope_of):
    agg = {"withheld_irrelevant": 0, "lost_context": 0, "lost_legitimate": [], "critical_lost": [], "answerable": 0,
           "top1_before": 0, "top1_after": 0, "allcrit_before": 0, "allcrit_after": 0, "no_answer_items_before": 0,
           "no_answer_items_after": 0, "no_qualified_evidence_answerable": [], "no_qualified_evidence_no_answer": []}
    for row in manifest["rows"]:
        c, scope = cases[row["id"]], scope_of.get(row["id"])
        allowed = None if scope is None else {norm(s) for s in scope}
        before = row["returned"]
        keep = lambda r: allowed is None or fact_subject.get(r) is None or norm(fact_subject[r]) in allowed
        after = [r for r in before if keep(r)]
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
            cov = lambda s: all(any(r in s for r in g) for g in c["critical_groups"])
            agg["answerable"] += 1
            agg["top1_before"] += bool(before) and before[0] in crit
            agg["top1_after"] += bool(after) and after[0] in crit
            agg["allcrit_before"] += cov(before)
            agg["allcrit_after"] += cov(after)
            if cov(before) and not cov(after):
                agg["critical_lost"].append(row["id"])
            if before and not after:
                agg["no_qualified_evidence_answerable"].append(row["id"])
        else:
            agg["no_answer_items_before"] += len(before)
            agg["no_answer_items_after"] += len(after)
            if before and not after:
                agg["no_qualified_evidence_no_answer"].append(row["id"])
    return agg


def main():
    results = {}
    for corpus, (inp, gspec) in CORPORA.items():
        data = json.loads(Path(inp).read_text())
        cases = {c["id"]: c for c in gold(gspec)["cases"]}
        manifest = served(inp, corpus)
        mem_of = {e["id"]: e["memory"] for e in data["events"] if "text" in e}
        subj = SUBJECTS[corpus]
        registry = sorted({s for s in subj.values() if s})
        fact_subject = {f: subj.get(m) for f, m in mem_of.items()}
        half_mem = sorted(subj)[::2]
        fact_half = {f: (None if mem_of[f] in half_mem else s) for f, s in fact_subject.items()}
        scopes = SCOPES["scopes"][corpus]
        nxt = {s: registry[(i + 1) % len(registry)] for i, s in enumerate(registry)}
        wrong = {q: (None if s is None else [nxt.get(x, registry[0]) for x in s]) for q, s in scopes.items()}
        queries = {q["id"]: q["query"] for q in data["queries"]}
        resolved = {q: resolve(t, registry) for q, t in queries.items()}
        variants = {"E1 caller scope": (fact_subject, scopes), "E1-wrong scope": (fact_subject, wrong),
                    "E1-half identity": (fact_half, scopes), "E2 lexical resolver": (fact_subject, resolved)}
        res = {name: measure(manifest, cases, fs, sc) for name, (fs, sc) in variants.items()}
        agree = sum(1 for q in queries if resolved[q] is not None and scopes[q] is not None
                    and {norm(x) for x in resolved[q]} == {norm(x) for x in scopes[q]})
        para = {q: {"caller": scopes[q], "original": resolved.get(q), "paraphrase": resolve(p, registry)}
                for q, p in SCOPES["paraphrases"].items() if q in queries}
        results[corpus] = {"runtime": manifest["provenance"]["runtime"], "evaluator": manifest["provenance"]["evaluator"],
                           "variants": res, "resolver_exact_agreement": f"{agree}/{sum(s is not None for s in scopes.values())}",
                           "resolver_unresolved": sorted(q for q in queries if resolved[q] is None and scopes[q] is not None),
                           "paraphrase_resolution": para}
    (HERE / "results-775-scope.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    for corpus, r in results.items():
        print("=====", corpus, "resolver agreement", r["resolver_exact_agreement"], "unresolved", r["resolver_unresolved"])
        for name, a in r["variants"].items():
            print(f"  {name:20s} irrelevant_withheld {a['withheld_irrelevant']:2d} ctx_lost {a['lost_context']:2d} "
                  f"LEGIT_LOST {len(a['lost_legitimate']):2d} {a['lost_legitimate'][:6]} crit_lost {a['critical_lost']} "
                  f"ans@1 {a['top1_before']}->{a['top1_after']}/{a['answerable']} allcrit {a['allcrit_before']}->{a['allcrit_after']} "
                  f"no-answer items {a['no_answer_items_before']}->{a['no_answer_items_after']} "
                  f"NQE ans {a['no_qualified_evidence_answerable']} noans {a['no_qualified_evidence_no_answer']}")
        print("  paraphrase:", {q: (v["original"] is not None, v["paraphrase"] is not None) for q, v in r["paraphrase_resolution"].items()})


if __name__ == "__main__":
    main()
