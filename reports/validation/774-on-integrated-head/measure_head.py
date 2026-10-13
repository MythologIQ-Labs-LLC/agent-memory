"""#774 strict-target measurement (validation only). Caller intent comes from an independent
annotator's successor annotations (asks_predecessor + successor label), identical for every runtime.

Modes
  composed          unchanged multi_route_recall (all questions)
  legacy-declared   annotated predecessor questions -> legacy selector WITHOUT a target (implicit anchoring)
  strict-target     annotated predecessor questions -> strict selector with the annotated successor
                    (successor null -> no target -> unresolved, ranking unchanged)
  strict-untargeted annotated predecessor questions -> strict selector with no target
"""
import argparse, copy, json, subprocess, sys, tempfile
from pathlib import Path
EVAL = Path("<scratch>/ev"); REPO = Path("/home/user/agent-memory")
RUNTIMES = {"783-ec811f9": "<scratch>/wt-783", "774-on-783-500acfa": "/home/user/agent-memory"}
PLAN = [("783-ec811f9", "composed"), ("774-on-783-500acfa", "composed"),
        ("774-on-783-500acfa", "strict-target"), ("774-on-783-500acfa", "strict-untargeted")]


def run_one(root, inp, ann, mode, out):
    sys.path.insert(0, str(EVAL / "scripts")); import served_memory_v3 as v3
    lifecycle, loaded = v3.load_runtime(Path(root))
    data = json.loads(Path(inp).read_text()); notes = json.loads(Path(ann).read_text())["annotations"]
    prov = {"evaluator": v3._checkout(EVAL), "runtime": v3.runtime_provenance(Path(root), loaded)}
    with tempfile.TemporaryDirectory() as tmp:
        rt, labels = lifecycle.build_store(v3._v2_view(data), Path(tmp) / "s")
        uuid_of = {v: k for k, v in labels.items()}
        ctx = lifecycle.RecallContext(target_domain_refs=(data["tenant"], data["project"]), principal_ref="agent:quality-evaluation",
                                      project_ref=data["project"], purpose=data["purpose"])
        rows, side, applied = [], [], []
        for q in data["queries"]:
            m = {"current": "current", "historical": "historical", "timeless": "atemporal_or_unspecified"}[q["intent"]]
            intent = {"mode": m}
            if m == "current":
                intent["reference_time"] = data["reference_time"]
            note = notes.get(q["id"], {}); extra = {"id": q["id"], "routed": False}
            if mode != "composed" and note.get("asks_predecessor"):
                kw = {}
                if mode == "strict-target" and note.get("successor"):
                    kw["successor_ref"] = uuid_of.get(note["successor"])
                try:
                    sel = rt.historical_predecessor_context(q["query"], ctx, budget=q["budget"], **kw)
                    extra.update(routed=True, predecessor=labels.get(sel.predecessor_ref), successor=labels.get(sel.successor_ref),
                                 resolution=getattr(sel, "target_resolution", "legacy"))
                    served = list(sel.served_refs)
                except ValueError as exc:  # annotated successor not visible (deleted / other scope)
                    extra.update(routed=False, error=str(exc))
                    served = list(rt.multi_route_recall(q["query"], ctx, temporal_intent=intent).ranked_admitted)[:q["budget"]]
            else:
                if m == "current":
                    applied.append(q["id"])
                served = list(rt.multi_route_recall(q["query"], ctx, temporal_intent=intent).ranked_admitted)[:q["budget"]]
            rows.append({"id": q["id"], "returned": [labels[r] for r in served]}); side.append(extra)
    man = {"schema": v3.RUN_SCHEMA_V2, "lane_id": f"774-strict-{mode}", "execution_backend": "composed-multiroute",
           "input_sha256": v3.canonical_input_digest_v3(data, lifecycle), "reference_time": data["reference_time"],
           "reference_time_utc": v3.parse_reference_time(data["reference_time"]).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
           "reference_time_applied_to": applied, "provenance": prov, "rows": rows}
    Path(out).write_text(json.dumps({"manifest": man, "sidecar": side}, indent=2, sort_keys=True))


def compare(corpora, out):
    sys.path.insert(0, str(EVAL / "scripts")); import served_memory_v3 as v3
    work = Path(tempfile.mkdtemp()); results = {}
    for name, (inp, gold, ann) in corpora.items():
        g = json.loads(Path(gold).read_text()); d = json.loads(Path(inp).read_text()); entry = {}
        for rtn, mode in PLAN:
            o = work / f"{name}-{rtn}-{mode}.json"
            subprocess.run([sys.executable, __file__, "run", RUNTIMES[rtn], inp, ann, mode, str(o)], check=True)
            doc = json.loads(o.read_text())
            rep = v3.qualify_v3(copy.deepcopy(d), copy.deepcopy(g), copy.deepcopy(doc["manifest"]), repo=REPO)
            entry[f"{rtn}/{mode}"] = {"manifest": doc["manifest"], "sidecar": doc["sidecar"], "report": rep}
        results[name] = entry
    Path(out).write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run_one(*sys.argv[2:7])
    else:
        compare(json.loads(sys.argv[2]), sys.argv[3])
