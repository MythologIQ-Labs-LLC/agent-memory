"""#771/#773 Phase B+D driver: run every runtime x serving mode, qualify, compare.

Corpora are read from their frozen commits with ``git show`` (never copied
into a runtime checkout). Each (runtime, mode, corpus) runs in its own
process through phase_d_adapter.py. The same explicit reference instant T is
given to the unchanged v7 composed path and to the #773 selector.

Writes phase-d-results.json and PHASE_D.md next to this script.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVAL_ROOT = HERE.parents[2]
sys.path.insert(0, str(EVAL_ROOT / "scripts"))
from qualify_served_memory_run import qualify  # noqa: E402

PY = sys.executable
T = "2026-10-12T12:00:00Z"
CORPORA = {
    "halcyon-v1.1": ("04543a79dbf3774e2d3381690fe4212cfe955614",
                     "reports/validation/771-cloud-qualification/holdout/halcyon-holdout-v1.1-input.json",
                     "reports/validation/771-cloud-qualification/holdout/halcyon-holdout-v1-gold.json",
                     "reports/validation/771-cloud-qualification/holdout/halcyon-holdout-v1-strata.json"),
    "cedarline-v1.1": ("32404f7e0c800110cf7a72ba128479afc8bf0d83",
                       "reference/fixtures/evaluation/cedarline-independent-v1.1-input.json",
                       "reference/fixtures/evaluation/cedarline-independent-v1.1-gold.json",
                       "reference/fixtures/evaluation/cedarline-independent-v1-strata.json"),
}
WT = Path("/tmp/claude-0/wt3")
RUNTIMES = {
    "main-3eebb6d": (WT / "cedar", ("composed-default",)),
    "v7-9b025f9": (WT / "v7", ("composed-default", "composed-T")),
    "773-candidate-9c9bf4d": (WT / "selcand", ("composed-default", "composed-T", "selector-T")),
    "773-repaired": (WT / "sel", ("composed-T", "selector-T")),
}
BASE, AFTER = ("v7-9b025f9", "composed-T"), ("773-candidate-9c9bf4d", "selector-T")


def _show(sha, path):
    return subprocess.run(["git", "-C", str(EVAL_ROOT), "show", f"{sha}:{path}"], check=True,
                          capture_output=True).stdout


def _row(case, served):
    unsafe = set(case["stale"]) | set(case["prohibited"])
    crit = {r for g in case["critical_groups"] for r in g}
    return {"served": served, "top1_critical": bool(served) and served[0] in crit,
            "critical": f'{sum(any(r in served for r in g) for g in case["critical_groups"])}/{len(case["critical_groups"])}',
            "stale": [r for r in served if r in case["stale"]],
            "prohibited": [r for r in served if r in case["prohibited"]],
            "distractors": [r for r in served if case["relevance"][r] == 0 and r not in unsafe]}


def main():
    work = Path(tempfile.mkdtemp())
    results = {"reference_time": T, "corpora": {}}
    for corpus, (sha, inp, gold_path, strata_path) in CORPORA.items():
        inputs_raw, gold = _show(sha, inp), json.loads(_show(sha, gold_path))
        strata = json.loads(_show(sha, strata_path))
        (work / f"{corpus}.json").write_bytes(inputs_raw)
        inputs = json.loads(inputs_raw)
        cases = {c["id"]: c for c in gold["cases"]}
        entry = {"source_commit": sha, "variants": {}}
        for name, (root, modes) in RUNTIMES.items():
            for mode in modes:
                out = work / f"{corpus}-{name}-{mode}.json"
                subprocess.run([PY, str(HERE / "phase_d_adapter.py"), "--runtime-root", str(root),
                                "--inputs", str(work / f"{corpus}.json"), "--mode", mode,
                                "--reference-time", T, "--out", str(out)], check=True)
                doc = json.loads(out.read_text())
                report = qualify(copy.deepcopy(inputs), copy.deepcopy(gold), copy.deepcopy(doc["run"]))
                entry["variants"][f"{name}/{mode}"] = {
                    "identity": doc["identity"], "run": doc["run"], "per_query": doc["per_query"],
                    "P0": report["P0_safety"], "P1": report["P1_served_correctness"],
                    "P2": report["P2_context_utility"]}
        # Before/after per query on the SAME explicit instant.
        before = entry["variants"]["/".join(BASE)]
        after = entry["variants"]["/".join(AFTER)]
        repaired = entry["variants"]["773-repaired/selector-T"]
        comparison = []
        for b_row, a_row, r_row, side in zip(before["run"]["rows"], after["run"]["rows"],
                                             repaired["run"]["rows"], after["per_query"]):
            case = cases[b_row["id"]]
            b, a = _row(case, b_row["returned"]), _row(case, a_row["returned"])
            excluded = side.get("excluded_known_inapplicable", [])
            unsafe = set(case["stale"]) | set(case["prohibited"])
            valid_excluded = [r for r in excluded if case["relevance"][r] >= 1 and r not in unsafe]
            changes = []
            if len(a["stale"]) < len(b["stale"]): changes.append("improved:stale")
            if len(a["stale"]) > len(b["stale"]): changes.append("regressed:stale")
            if a["top1_critical"] and not b["top1_critical"]: changes.append("improved:top1")
            if b["top1_critical"] and not a["top1_critical"]: changes.append("regressed:top1")
            bc, ac = int(b["critical"].split("/")[0]), int(a["critical"].split("/")[0])
            if ac > bc: changes.append("improved:critical")
            if ac < bc: changes.append("regressed:critical")
            if len(a["distractors"]) < len(b["distractors"]): changes.append("improved:distractors")
            if len(a["distractors"]) > len(b["distractors"]): changes.append("regressed:distractors")
            comparison.append({"id": b_row["id"], "stratum": strata.get(b_row["id"]), "intent": case["intent"],
                               "safely_answerable": case["safe_answer_exists"], "before": b, "after": a,
                               "repaired_served_identical": r_row["returned"] == a_row["returned"],
                               "selector_status": side.get("selector"),
                               "excluded_known_inapplicable": excluded,
                               "valid_evidence_excluded": valid_excluded,
                               "changes": changes or ["unchanged"]})
        entry["before_after"] = comparison
        stability = {}
        for left, right in (("v7-9b025f9/composed-default", "773-candidate-9c9bf4d/composed-default"),
                            ("v7-9b025f9/composed-T", "773-candidate-9c9bf4d/composed-T"),
                            ("v7-9b025f9/composed-T", "773-repaired/composed-T"),
                            ("main-3eebb6d/composed-default", "v7-9b025f9/composed-default"),
                            ("v7-9b025f9/composed-default", "v7-9b025f9/composed-T")):
            l, r = entry["variants"][left], entry["variants"][right]
            diff = [x["id"] for x, y in zip(l["run"]["rows"], r["run"]["rows"]) if x["returned"] != y["returned"]]
            ranked_diff = [x["id"] for x, y in zip(l["per_query"], r["per_query"])
                           if x["ranked_admitted"] != y["ranked_admitted"]]
            stability[f"{left} vs {right}"] = {"served_rows_differ": diff, "ranked_admitted_differ": ranked_diff}
        entry["stability"] = stability
        results["corpora"][corpus] = entry
    (HERE / "phase-d-results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print(json.dumps({c: {"stability": e["stability"]} for c, e in results["corpora"].items()}, indent=1))


if __name__ == "__main__":
    main()
