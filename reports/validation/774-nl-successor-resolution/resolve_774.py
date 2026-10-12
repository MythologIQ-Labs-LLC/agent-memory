"""#774 research (evaluation-only, never imported by a runtime): natural-language successor
resolution strategies, measured against independent gold on a frozen blind corpus.

Every strategy sees only: the question text, the governed historical recall ranking for that
question (canonical admission), and the admitted facts' texts and logical-memory lineage
(versions in write order). Output: a successor fact or ABSTAIN.

  R0 never resolve (strict untargeted baseline)
  R1 legacy implicit: current head of the top-ranked lineage memory (what #774 v0.1 did)
  R2 distinctive value mention: a question token that occurs in exactly ONE version of exactly
     ONE candidate lineage (among lineages with admitted versions in the ranked top-k) names the
     successor; with no such token, the head of the single lineage in the top-k; any tie -> ABSTAIN
  R3 R2 but ABSTAIN unless exactly one lineage appears in the top-k (wrong-subject guard)
Then the strict selector (selection 0.2.0) is called with the resolved successor_ref.
"""
import json, re, subprocess, sys, tempfile, copy
from pathlib import Path
EVAL = Path("/tmp/claude-0/wt5/ev"); REPO = Path("/home/user/agent-memory")
STRICT = Path("/tmp/claude-0/wt7/s774"); V7 = Path("/tmp/claude-0/wt3/v7")
STOP = set("the a an of to in on at for was were is are did do does what which who when where how before after we our us it its by with from that this than then been be use used using".split())
tok = lambda s: {w for w in re.findall(r"[a-z0-9][a-z0-9'.:-]*", s.lower().replace("’", "'")) if w not in STOP and len(w) > 1}


def strategies(question, ranked, texts, lineage_of, head_of, k=3):
    top = ranked[:k]
    lineages = []
    for r in top:
        m = lineage_of.get(r)
        if m and m not in lineages and len(head_of[m]["versions"]) >= 2:
            lineages.append(m)
    out = {"R0": None, "R1": None, "R2": None, "R3": None}
    out["R1"] = head_of[lineages[0]]["head"] if lineages else None
    q = tok(question)
    hits = []
    for m in lineages:
        vers = head_of[m]["versions"]
        for v in vers:
            own = tok(texts[v]) - set().union(*(tok(texts[o]) for o in vers if o != v))
            if q & own:
                hits.append(v)
    if len(hits) == 1:
        r2 = hits[0]
    elif not hits and len(lineages) == 1:
        r2 = head_of[lineages[0]]["head"]
    else:
        r2 = None
    out["R2"] = r2
    out["R3"] = r2 if len(lineages) == 1 else None
    return out


def run(runtime_root, inp, succ_gold, out_path):
    sys.path.insert(0, str(EVAL / "scripts")); import served_memory_v3 as v3
    lifecycle, loaded = v3.load_runtime(runtime_root)
    data = json.loads(Path(inp).read_text()); gold = json.loads(Path(succ_gold).read_text())["annotations"]
    prov = {"evaluator": v3._checkout(EVAL), "runtime": v3.runtime_provenance(runtime_root, loaded)}
    rows = {s: [] for s in ("R0", "R1", "R2", "R3", "ORACLE")}; decisions = {}
    with tempfile.TemporaryDirectory() as tmp:
        rt, labels = lifecycle.build_store(v3._v2_view(data), Path(tmp) / "s")
        uuid_of = {v: k for k, v in labels.items()}
        ad = rt.adapter
        ctx = lifecycle.RecallContext(target_domain_refs=(data["tenant"], data["project"]), principal_ref="agent:quality-evaluation",
                                      project_ref=data["project"], purpose=data["purpose"])
        texts = {f.uuid: f.fact_text for f in ad._substrate.all_facts()}
        lineage_of = dict(ad._fact_memory)
        head_of = {}
        for m in set(lineage_of.values()):
            vers = sorted((f for f in ad._substrate.all_facts() if lineage_of.get(f.uuid) == m), key=lambda f: f.created_at)
            vis = [f.uuid for f in vers if ad.lineage_visible(f.uuid, ctx) and not ad.memory_deleted(f.uuid)]
            head_of[m] = {"versions": vis, "head": ad.current_fact_uuid(m) if ad.current_fact_uuid(m) in vis else None}
        for q in data["queries"]:
            g = gold.get(q["id"], {})
            mode = {"current": "current", "historical": "historical", "timeless": "atemporal_or_unspecified"}[q["intent"]]
            intent = {"mode": mode, **({"reference_time": data["reference_time"]} if mode == "current" else {})}
            plain = list(rt.multi_route_recall(q["query"], ctx, temporal_intent=intent).ranked_admitted)
            if not g.get("asks_predecessor"):
                for s in rows: rows[s].append({"id": q["id"], "returned": [labels[r] for r in plain[:q["budget"]]]})
                continue
            hist = list(rt.multi_route_recall(q["query"], ctx, temporal_intent={"mode": "historical"}).ranked_admitted)
            hist = [r for r in hist if not ad.memory_deleted(r)]
            choice = strategies(q["query"], hist, texts, lineage_of, head_of)
            choice["ORACLE"] = uuid_of.get(g.get("successor")) if g.get("successor") else None
            decisions[q["id"]] = {s: labels.get(v) for s, v in choice.items()} | {"gold": g.get("successor"), "gold_resolution": g.get("resolution")}
            for s, succ in choice.items():
                if succ is not None and head_of.get(lineage_of.get(succ)) is not None and succ in head_of[lineage_of[succ]]["versions"]:
                    sel = rt.historical_predecessor_context(q["query"], ctx, budget=q["budget"], successor_ref=succ)
                else:
                    sel = rt.historical_predecessor_context(q["query"], ctx, budget=q["budget"])
                rows[s].append({"id": q["id"], "returned": [labels[r] for r in sel.served_refs]})
    base = {"schema": v3.RUN_SCHEMA_V2, "execution_backend": "composed-multiroute", "input_sha256": v3.canonical_input_digest_v3(data, lifecycle),
            "reference_time": data["reference_time"], "reference_time_utc": v3.parse_reference_time(data["reference_time"]).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "reference_time_applied_to": [q["id"] for q in data["queries"] if q["intent"] == "current"], "provenance": prov}
    Path(out_path).write_text(json.dumps({"manifests": {s: {**base, "lane_id": f"774-nlres-{s}", "rows": r} for s, r in rows.items()},
                                          "decisions": decisions}, indent=2, sort_keys=True))


if __name__ == "__main__":
    run(Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4])
