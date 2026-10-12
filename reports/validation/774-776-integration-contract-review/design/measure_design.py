"""#774 follow-on measurement (validation-only; never imported by the runtime).

Runtimes: v7 parent, #774 ce1fdfc (no guard), #774 follow-on head (guard + router).
Modes:
  composed     unchanged multi_route_recall (current questions carry the declared instant)
  declared     caller-declared predecessor questions -> historical_predecessor_context
  auto         routed_historical_context (automatic routing; follow-on head only)
  over-routed  sensitivity: every historical-intent question -> historical_predecessor_context
Declared routing: Brightwater/Halcyon/Cedarline from the frozen routing-declarations.json
of the first #774 validation; Fenmoor = every stratum that asks for a predecessor
(predecessor-* and wrong-subject-*), derived from the frozen strata file.
"""
from __future__ import annotations

import argparse, copy, json, subprocess, sys, tempfile
from pathlib import Path

HERE = Path("/tmp/claude-0/wt5/v774b/reports/validation/774-anchor-guard-and-routing")
OUT = Path(__file__).resolve().parent
EVAL = Path("/tmp/claude-0/wt5/ev")          # adopted evaluator 9961067
REPO = Path("/home/user/agent-memory")
PRIOR = HERE.parent / "774-predecessor-quality"
V3H = Path("/tmp/claude-0/wt4/prov/reports/validation/771-lifecycle-v3-provenance/holdouts")
CORPORA = {
    "halcyon-v1.1": (V3H / "halcyon-v1.1-at-20261012T12Z.v3.json",
                     ("04543a79dbf3774e2d3381690fe4212cfe955614",
                      "reports/validation/771-cloud-qualification/holdout/halcyon-holdout-v1-gold.json")),
    "cedarline-v1.1": (V3H / "cedarline-v1.1-at-20261012T12Z.v3.json",
                       ("32404f7e0c800110cf7a72ba128479afc8bf0d83",
                        "reference/fixtures/evaluation/cedarline-independent-v1.1-gold.json")),
    "brightwater-v1": (PRIOR / "holdout/brightwater-v1-input.v3.json", (None, PRIOR / "holdout/brightwater-v1-gold.json")),
    "fenmoor-v1": (HERE / "holdout/fenmoor-v1-input.v3.json", (None, HERE / "holdout/fenmoor-v1-gold.json")),
}
RUNTIMES = {"v7-9b025f9": Path("/tmp/claude-0/wt3/v7"), "774-ce1fdfc": Path("/tmp/claude-0/wt4/s774"),
            "774b-head": Path("/tmp/claude-0/wt5/s774b"), "design-b367b76": Path("/tmp/claude-0/wt6/design")}
PLAN = [("v7-9b025f9", "composed"), ("774b-head", "declared"), ("774b-head", "auto"), ("design-b367b76", "composed"), ("design-b367b76", "declared"), ("design-b367b76", "auto")]


def declared(corpus):
    if corpus == "fenmoor-v1":
        strata = json.loads((HERE / "holdout/fenmoor-v1-strata.json").read_text())
        return {q for q, s in strata.items() if s.startswith(("predecessor", "wrong-subject"))}
    return set(json.loads((PRIOR / "holdout/routing-declarations.json").read_text())[corpus])


def run_one(runtime_root, inputs_path, corpus, mode, out):
    sys.path.insert(0, str(EVAL / "scripts"))
    import served_memory_v3 as v3
    lifecycle, loaded = v3.load_runtime(runtime_root)
    data = json.loads(Path(inputs_path).read_text())
    routed = declared(corpus) if mode == "declared" else set()
    if mode == "over-routed":
        routed = {q["id"] for q in data["queries"] if q["intent"] == "historical"}
    provenance = {"evaluator": v3._checkout(EVAL), "runtime": v3.runtime_provenance(runtime_root, loaded)}
    with tempfile.TemporaryDirectory() as tmp:
        rt, labels = lifecycle.build_store(v3._v2_view(data), Path(tmp) / "store")
        ctx = lifecycle.RecallContext(target_domain_refs=(data["tenant"], data["project"]),
                                      principal_ref="agent:quality-evaluation",
                                      project_ref=data["project"], purpose=data["purpose"])
        rows, side, applied = [], [], []
        for q in data["queries"]:
            mode_ = {"current": "current", "historical": "historical", "timeless": "atemporal_or_unspecified"}[q["intent"]]
            intent = {"mode": mode_}
            if mode_ == "current":
                intent["reference_time"] = data["reference_time"]
            extra = {"id": q["id"]}
            if mode == "auto":
                sel = rt.routed_historical_context(q["query"], ctx, budget=q["budget"], temporal_intent=intent)
                served = list(sel.served_refs)
                extra.update(routed=sel.routed, evidence=list(sel.routing_evidence),
                             predecessor=labels.get(sel.predecessor_ref), successor=labels.get(sel.successor_ref))
                if not sel.routed and mode_ == "current":
                    applied.append(q["id"])
            elif q["id"] in routed:
                sel = rt.historical_predecessor_context(q["query"], ctx, budget=q["budget"])
                served = list(sel.served_refs)
                extra.update(routed=True, predecessor=labels.get(sel.predecessor_ref), successor=labels.get(sel.successor_ref))
            else:
                extra["routed"] = False
                if mode_ == "current":
                    applied.append(q["id"])
                served = list(rt.multi_route_recall(q["query"], ctx, temporal_intent=intent).ranked_admitted)[:q["budget"]]
            rows.append({"id": q["id"], "returned": [labels[r] for r in served]})
            side.append(extra)
    manifest = {"schema": v3.RUN_SCHEMA_V2, "lane_id": f"774b-{mode}", "execution_backend": "composed-multiroute",
                "input_sha256": v3.canonical_input_digest_v3(data, lifecycle), "reference_time": data["reference_time"],
                "reference_time_utc": v3.parse_reference_time(data["reference_time"]).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "reference_time_applied_to": applied, "provenance": provenance, "rows": rows}
    Path(out).write_text(json.dumps({"manifest": manifest, "sidecar": side}, indent=2, sort_keys=True) + "\n")


def _gold(spec):
    sha, path = spec
    if sha is None:
        return json.loads(Path(path).read_text())
    return json.loads(subprocess.run(["git", "-C", str(REPO), "show", f"{sha}:{path}"], check=True,
                                     capture_output=True).stdout)


def compare():
    sys.path.insert(0, str(EVAL / "scripts"))
    import served_memory_v3 as v3
    work = Path(tempfile.mkdtemp())
    results = {}
    for corpus, (inp, gold_spec) in CORPORA.items():
        gold, inputs, entry = _gold(gold_spec), json.loads(Path(inp).read_text()), {}
        for runtime, mode in PLAN:
            out = work / f"{corpus}-{runtime}-{mode}.json"
            subprocess.run([sys.executable, __file__, "run", "--runtime-root", str(RUNTIMES[runtime]), "--inputs", str(inp),
                            "--corpus", corpus, "--mode", mode, "--out", str(out)], check=True)
            doc = json.loads(out.read_text())
            report = v3.qualify_v3(copy.deepcopy(inputs), copy.deepcopy(gold), copy.deepcopy(doc["manifest"]), repo=REPO)
            entry[f"{runtime}/{mode}"] = {"manifest": doc["manifest"], "sidecar": doc["sidecar"], "report": report}
        results[corpus] = entry
    (OUT / "results-design.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    for a in ("--runtime-root", "--inputs", "--corpus", "--mode", "--out"):
        r.add_argument(a, required=True)
    sub.add_parser("compare")
    args = p.parse_args()
    run_one(Path(args.runtime_root), args.inputs, args.corpus, args.mode, args.out) if args.cmd == "run" else compare()


if __name__ == "__main__":
    main()
