"""Paired LongMemEval_S retrieval check of the #819 selector (regression/diagnostic, not a holdout).

Mirrors the frozen lane's control row posture (one tenant and scope per question, opaque
memory refs, no observed_at, recall(question, budget=50), no reference_time) and adds, on the
same store and recall, the context arms and an FTS5 comparator. Gold is joined after retrieval.

usage: lme_paired.py --plane session|turn --input FILE --out DIR [--limit N] [--start N]
"""
from __future__ import annotations

import argparse, json, os, platform, subprocess, sys, tempfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paired  # noqa: E402

ARMS = ("raw", "default", "lexical", "eq", "fts5")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plane", required=True, choices=("session", "turn"))
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--runtime", default="/home/user/agent-memory")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--start", type=int, default=0)
    args = ap.parse_args()
    sys.path.insert(0, str(Path(args.runtime) / "reference"))
    from agentmem_ref import AgentMemory
    import run_longmemeval as lme

    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    rows_path = out / "rows.jsonl"
    done = set()
    if rows_path.exists():
        for line in rows_path.read_text().splitlines():
            if line.strip():
                done.add(json.loads(line)["id"])
    dataset = json.loads(Path(args.input).read_text(encoding="utf-8"))
    sha = subprocess.check_output(["git", "-C", args.runtime, "rev-parse", "HEAD"], text=True).strip()
    selector_blob = subprocess.check_output(["git", "-C", args.runtime, "hash-object", "reference/agentmem_ref/api/context_selection.py"], text=True).strip()
    started = time.time()
    with rows_path.open("a") as sink:
        for index, row in enumerate(dataset):
            if index < args.start:
                continue
            if args.limit and index >= args.start + args.limit:
                break
            qid = row["question_id"]
            if qid in done:
                continue
            items, gold = lme.corpus(row, args.plane)
            question = row["question"]
            with tempfile.TemporaryDirectory(prefix="lme-819-") as tmp:
                t = time.perf_counter()
                with AgentMemory.open(tmp, tenant=f"tenant:longmemeval:{index}", actor_id="agent:benchmark",
                                      scope=f"benchmark:longmemeval:{index}", purpose="LongMemEval retrieval evaluation") as memory:
                    uuid_to_item = {}
                    for item_index, item in enumerate(items):
                        r = memory.remember(f"memory:longmemeval:{index}:{item_index}", item["text"])
                        assert r.get("committed") and r.get("fact_uuid"), (qid, item_index, r)
                        uuid_to_item[r["fact_uuid"]] = item["id"]
                    ingest_ms = (time.perf_counter() - t) * 1000
                    t = time.perf_counter()
                    arms = paired.am_arms(memory, question, 50)
                    arms_ms = (time.perf_counter() - t) * 1000
            fts = paired.FTS5Index([(i["id"], i["text"]) for i in items])
            t = time.perf_counter()
            fts_ids = fts.search(question, 50)
            fts_ms = (time.perf_counter() - t) * 1000
            fts_build_ms = fts.build_ms
            fts.close()
            ids = {arm: [uuid_to_item[u] for u in arms[arm]] for arm in ("raw", "default", "lexical", "eq")}
            ids["fts5"] = fts_ids
            corpus_ids = [i["id"] for i in items]
            record = {
                "id": qid, "index": index, "question_type": row["question_type"], "plane": args.plane,
                "gold": gold, "items": len(items),
                "ids": ids,
                "scores": {arm: paired.score(ids[arm], gold) for arm in ARMS},
                "upstream_raw": lme._score_row(ids["raw"], gold, corpus_ids, args.plane),
                "eq_selection": {
                    **{k: v for k, v in arms["eq_selection"].items() if k != "decisions"},
                    "decisions": {uuid_to_item[u]: d for u, d in arms["eq_selection"]["decisions"].items()},
                },
                "ms": {"am_ingest": ingest_ms, "am_arms_total": arms_ms, **arms["ms"], "fts5_build": fts_build_ms, "fts5_search": fts_ms},
            }
            sink.write(json.dumps(record, sort_keys=True) + "\n"); sink.flush()
            if index % 25 == 0:
                print(f"[{args.plane}] {index} {qid} eq={len(ids['eq'])}/{len(ids['default'])} gold={len(gold)} elapsed={time.time()-started:.0f}s", flush=True)
    rows = [json.loads(l) for l in rows_path.read_text().splitlines() if l.strip()]
    rows.sort(key=lambda r: r["index"])
    summary = paired.summarize(rows, ARMS)
    by_type = {}
    for qt in sorted({r["question_type"] for r in rows}):
        by_type[qt] = paired.summarize([r for r in rows if r["question_type"] == qt], ARMS)
    report = {
        "kind": "paired_longmemeval_s_context_arms_regression_not_holdout",
        "plane": args.plane, "questions": len(rows), "runtime_sha": sha, "selector_blob": selector_blob,
        "input_sha256": subprocess.check_output(["sha256sum", args.input], text=True).split()[0],
        "python": sys.version, "platform": platform.platform(),
        "budget_k": 50, "context_budgets": paired.CHARS,
        "summary": summary, "by_question_type": by_type,
        "upstream_raw_recall_all_at_50": sum(1 for r in rows if r["gold"] and r["upstream_raw"][args.plane]["recall_all@50"] == 1.0),
        "latency_ms": {k: {"p50": _p(rows, k, .5), "p95": _p(rows, k, .95)} for k in ("am_ingest", "default_context", "eq_context", "fts5_build", "fts5_search")},
        "limitations": [
            "post-freeze public dataset: regression evidence, not a blinded holdout",
            "retrieval only; no answer generation or judging",
            "shared store, fixed call order, warm caches; latency descriptive only",
        ],
    }
    (out / "summary.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if not kk.startswith("questions_")} for k, v in summary.items()}, indent=1))
    for arm in ("lexical", "eq", "fts5"):
        print(arm, "lost vs default:", summary[arm]["questions_losing_required_evidence_vs_default"])


def _p(rows, key, q):
    vals = sorted(r["ms"][key] for r in rows if key in r["ms"])
    return vals[min(len(vals) - 1, int((len(vals) - 1) * q))] if vals else None


if __name__ == "__main__":
    main()
