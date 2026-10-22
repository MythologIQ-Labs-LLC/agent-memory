"""LoCoMo (snap-research, AMB export locomo10) as a frozen-before-exposure external cohort.

The selector was implemented and committed before any LoCoMo content was read; this run is the
first exposure. It is independently authored (not by this project) but not owner-controlled, so
it is reported as a generalization check, not a sealed holdout. Gold = session documents cited
as evidence; the 9 questions with no gold session are no-answer controls. k = 10.
usage: locomo_paired.py <amb_data_dir/locomo/locomo10> <runtime> <out_dir>
"""
import gzip, json, platform, subprocess, sys, tempfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paired  # noqa: E402

data, runtime, out = map(Path, sys.argv[1:4]); out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(runtime / "reference"))
from agentmem_ref import AgentMemory

ARMS = ("raw", "default", "lexical", "eq", "fts5")
K = 10
queries = json.loads(gzip.open(data / "queries.json.gz", "rt", encoding="utf-8").read())
documents = json.loads(gzip.open(data / "documents.json.gz", "rt", encoding="utf-8").read())
rows = []
started = time.time()
with tempfile.TemporaryDirectory(prefix="locomo-819-") as tmp:
    for conv in sorted({d["user_id"] for d in documents}):
        docs = [d for d in documents if d["user_id"] == conv]
        mapping = {}
        t = time.perf_counter()
        with AgentMemory.open(tmp, tenant="tenant:locomo", actor_id="agent:eval", scope=f"conversation:{conv}", purpose="LoCoMo retrieval check") as m:
            for d in docs:
                r = m.remember(f"memory:locomo:{d['id']}", d["content"])
                assert r["committed"], (d["id"], r)
                mapping[r["fact_uuid"]] = d["id"]
            ingest_ms = (time.perf_counter() - t) * 1000
            fts = paired.FTS5Index([(d["id"], d["content"]) for d in docs])
            for q in [x for x in queries if x["user_id"] == conv]:
                am = paired.am_arms(m, q["query"], K)
                ids = {arm: [mapping[u] for u in am[arm]] for arm in ("raw", "default", "lexical", "eq")}
                t = time.perf_counter(); ids["fts5"] = fts.search(q["query"], K); fts_ms = (time.perf_counter() - t) * 1000
                gold = list(q["gold_ids"])
                rows.append({"id": q["id"], "conversation": conv, "category": q["meta"]["category"], "gold": gold, "ids": ids,
                             "scores": {arm: paired.score(ids[arm], gold) for arm in ARMS},
                             "eq_selection": {**{k: v for k, v in am["eq_selection"].items() if k != "decisions"},
                                              "decisions": {mapping[u]: d for u, d in am["eq_selection"]["decisions"].items()}},
                             "ms": {**am["ms"], "fts5_search": fts_ms, "am_ingest_conversation": ingest_ms, "fts5_build_conversation": fts.build_ms}})
            fts.close()
        print(conv, len(rows), f"{time.time()-started:.0f}s", flush=True)
summary = paired.summarize(rows, ARMS)
by_cat = {c: paired.summarize([r for r in rows if r["category"] == c], ARMS) for c in sorted({r["category"] for r in rows})}
report = {"kind": "locomo10_frozen_before_exposure_external_generalization_check_not_sealed_holdout",
          "runtime_sha": subprocess.check_output(["git", "-C", str(runtime), "rev-parse", "HEAD"], text=True).strip(),
          "selector_blob": subprocess.check_output(["git", "-C", str(runtime), "hash-object", "reference/agentmem_ref/api/context_selection.py"], text=True).strip(),
          "data_sha256": {p.name: subprocess.check_output(["sha256sum", str(p)], text=True).split()[0] for p in sorted(data.glob("*.gz"))},
          "python": sys.version, "platform": platform.platform(), "k": K, "questions": len(rows), "summary": summary, "by_category": by_cat}
(out / "summary.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
(out / "rows.json").write_text(json.dumps(rows, indent=1, sort_keys=True) + "\n")
print(json.dumps({a: {k: v for k, v in s.items() if not k.startswith("questions_")} for a, s in summary.items()}, indent=1))
for arm in ("lexical", "eq", "fts5"):
    print(arm, "lost vs default:", len(summary[arm]["questions_losing_required_evidence_vs_default"]))
