"""#771 independent measurement: per-query served-memory quality on both backends.

Run from a CLEAN checkout (the revision is read from git and refused if dirty):

  python reports/validation/771-cloud-qualification/measure.py --label <name>

For each corpus (frozen v1 integration fixture, frozen Halcyon holdout) and each
backend (composed-multiroute, governed-lexical) this:
  1. executes the governed runner into a fresh empty SQLite store,
  2. qualifies the run against the separately held gold,
  3. records per-query outcomes, including critical evidence that was ranked
     and admitted but cut by the served budget (runner diagnostics),
  4. replays 5 history-preserving write-order permutations to measure how
     stable each per-query outcome is (lexical ties are order-sensitive),
  5. records latency as a SEPARATE P3 engineering observation.
No composite score is produced.
"""
from __future__ import annotations

import argparse
import copy
import json
import random
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
import run_served_memory_lifecycle_scenarios as lifecycle  # noqa: E402
import run_served_memory_scenarios as v1runner  # noqa: E402
from qualify_served_memory_run import qualify  # noqa: E402

BACKENDS = ("composed-multiroute", "governed-lexical")
FIX = ROOT / "reference/fixtures/evaluation"
CORPORA = {
    "v1-integration": (FIX / "served-memory-integration-v1-input.json",
                       FIX / "served-memory-integration-v1-gold.json", None),
    "halcyon-holdout": (HERE / "holdout/halcyon-holdout-v1-input.json",
                        HERE / "holdout/halcyon-holdout-v1-gold.json",
                        HERE / "holdout/halcyon-holdout-v1-strata.json"),
}


def _execute(inputs, backend, revision):
    with tempfile.TemporaryDirectory() as tmp:
        started = time.perf_counter()
        if inputs["schema"] == lifecycle.SCHEMA:
            run, diag = lifecycle.run_scenarios(copy.deepcopy(inputs), Path(tmp), revision=revision,
                                                lane_id="independent-771-" + backend, backend=backend)
        else:
            run = v1runner.run_scenarios(copy.deepcopy(inputs), Path(tmp), revision=revision,
                                         lane_id="independent-771-" + backend, backend=backend)
            diag = None
        return run, diag, time.perf_counter() - started


def _permute(inputs, seed):
    """Shuffle independent memories while keeping each memory's own history order."""
    data = copy.deepcopy(inputs)
    rng = random.Random(seed)
    if data["schema"] != lifecycle.SCHEMA:
        rng.shuffle(data["writes"])
        return data
    chains: dict[str, list] = {}
    for event in data["events"]:
        chains.setdefault(event["memory"], []).append(event)
    keys = list(chains)
    rng.shuffle(keys)
    data["events"] = [event for key in keys for event in chains[key]]
    return data


def measure(label, revision):
    out = {"label": label, "runtime_revision": revision, "corpora": {}}
    for corpus, (inp_path, gold_path, strata_path) in CORPORA.items():
        inputs = json.loads(inp_path.read_text(encoding="utf-8"))
        gold = json.loads(gold_path.read_text(encoding="utf-8"))
        strata = json.loads(strata_path.read_text(encoding="utf-8")) if strata_path else {}
        cases = {c["id"]: c for c in gold["cases"]}
        entry = {"input_path": str(inp_path.relative_to(ROOT)), "gold_path": str(gold_path.relative_to(ROOT)),
                 "backends": {}}
        for backend in BACKENDS:
            run, diag, seconds = _execute(inputs, backend, revision)
            report = qualify(copy.deepcopy(inputs), copy.deepcopy(gold), copy.deepcopy(run))
            per_query = []
            for row, scored in zip(run["rows"], report["per_case"]):
                case = cases[row["id"]]
                critical = {ref for group in case["critical_groups"] for ref in group}
                late = [] if diag is None else [r for r in next(d for d in diag if d["id"] == row["id"])["beyond_budget"]
                                                if r in critical]
                per_query.append({
                    "id": row["id"], "stratum": strata.get(row["id"]), "intent": case["intent"],
                    "budget": case["budget"], "returned": row["returned"],
                    "top1_relevant": scored["top1_relevant"],
                    "critical": f'{scored["critical_groups_met"]}/{scored["critical_groups_total"]}',
                    "critical_ranked_beyond_budget": late,
                    "prohibited_served": [r for r in row["returned"] if r in case["prohibited"]],
                    "stale_served": [r for r in row["returned"] if r in case["stale"]],
                    "distractors_served": [r for r in row["returned"] if case["relevance"][r] == 0
                                           and r not in case["prohibited"] and r not in case["stale"]],
                    "context_only_served": [r for r in row["returned"] if case["relevance"][r] == 1
                                            and r not in case["prohibited"] and r not in case["stale"]],
                    "precision": scored["relevant_precision"],
                    "recall_at_budget": scored["relevant_recall_at_budget"],
                    "ndcg": scored["ndcg_at_budget"],
                    "safely_answerable": scored["safely_answerable"],
                    "empty_delivery": scored["empty_delivery"],
                })
            stability = {}
            for seed in range(5):
                prun, _pdiag, _ = _execute(_permute(inputs, seed), backend, revision)
                preport = qualify(_permute(inputs, seed), copy.deepcopy(gold), copy.deepcopy(prun)) \
                    if inputs["schema"] == lifecycle.SCHEMA else None
                for prow in prun["rows"]:
                    base = next(r for r in run["rows"] if r["id"] == prow["id"])
                    stability.setdefault(prow["id"], 0)
                    stability[prow["id"]] += prow["returned"] != base["returned"]
                del preport
            for row in per_query:
                row["order_permutations_changed"] = f'{stability[row["id"]]}/5'
            entry["backends"][backend] = {
                "run": run, "diagnostics": diag, "report_summary": {
                    k: report[k] for k in ("P0_safety", "P1_served_correctness", "P2_context_utility")},
                "per_query": per_query,
                "P3_engineering": {"store_build_plus_all_queries_seconds": round(seconds, 3),
                                   "queries": len(run["rows"]),
                                   "note": "single cold run incl. governed writes; tiny corpora, not a scalability result"},
            }
        out["corpora"][corpus] = entry
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    revision = v1runner._verified_revision()
    report = measure(args.label, revision)
    path = HERE / f"measurements-{args.label}.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for corpus, entry in report["corpora"].items():
        for backend, data in entry["backends"].items():
            s = data["report_summary"]
            print(corpus, backend, json.dumps({"P0": s["P0_safety"],
                  "top1": s["P1_served_correctness"]["top1_relevant_rate"],
                  "allcrit": s["P1_served_correctness"]["all_critical_groups_covered_rate"]}))


if __name__ == "__main__":
    main()
