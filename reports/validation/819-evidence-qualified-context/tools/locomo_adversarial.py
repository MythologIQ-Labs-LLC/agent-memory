"""LoCoMo category-5 (adversarial, unanswerable) questions: unseen no-answer controls.

AMB excludes category 5. These 446 questions were never loaded before this run (raw
snap-research/locomo locomo10.json, fetched after policy 0.3.0 was frozen). Each has a
plausible but wrong "adversarial_answer" and cites the dialogue turns it is built from; the
conversation holds no answer. Measured: delivered burden per arm, how often the selector
delivers nothing, and the assessment distribution. k = 10 over the same AMB session export.
usage: locomo_adversarial.py <raw locomo10.json> <amb locomo10 export dir> <runtime> <out_dir>
"""
import gzip, json, platform, subprocess, sys, tempfile, time
from pathlib import Path
from collections import Counter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paired  # noqa: E402

raw_path, data, runtime, out = map(Path, sys.argv[1:5]); out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(runtime / "reference"))
from agentmem_ref import AgentMemory

ARMS = ("raw", "default", "lexical", "eq", "fts5")
K = 10
raw = json.loads(raw_path.read_text(encoding="utf-8"))
documents = json.loads(gzip.open(data / "documents.json.gz", "rt", encoding="utf-8").read())
questions = []
for item in raw:
    conv = item["conversation"]
    keys = sorted(k for k in conv if k.startswith("session_") and not k.endswith("_date_time") and isinstance(conv[k], list))
    dia_to_session = {turn["dia_id"]: sk for sk in keys for turn in conv[sk]}
    for qi, qa in enumerate(item["qa"]):
        if qa.get("category") != 5:
            continue
        cited = sorted({f"{item['sample_id']}_{dia_to_session[e]}" for e in qa.get("evidence") or [] if e in dia_to_session})
        questions.append({"id": f"{item['sample_id']}_q{qi}", "conversation": item["sample_id"], "query": qa["question"], "cited": cited})
rows = []
started = time.time()
with tempfile.TemporaryDirectory(prefix="locomo-adv-819-") as tmp:
    for conv in sorted({d["user_id"] for d in documents}):
        docs = [d for d in documents if d["user_id"] == conv]
        mapping = {}
        with AgentMemory.open(tmp, tenant="tenant:locomo", actor_id="agent:eval", scope=f"conversation:{conv}", purpose="LoCoMo adversarial check") as m:
            for d in docs:
                r = m.remember(f"memory:locomo:{d['id']}", d["content"])
                assert r["committed"], (d["id"], r)
                mapping[r["fact_uuid"]] = d["id"]
            fts = paired.FTS5Index([(d["id"], d["content"]) for d in docs])
            for q in [x for x in questions if x["conversation"] == conv]:
                am = paired.am_arms(m, q["query"], K)
                ids = {arm: [mapping[u] for u in am[arm]] for arm in ("raw", "default", "lexical", "eq")}
                ids["fts5"] = fts.search(q["query"], K)
                rows.append({"id": q["id"], "conversation": conv, "cited_sessions": q["cited"], "ids": ids,
                             "delivered": {arm: len(ids[arm]) for arm in ARMS},
                             "cited_delivered": {arm: len(set(ids[arm]) & set(q["cited"])) for arm in ARMS},
                             "eq_selection": {k: v for k, v in am["eq_selection"].items() if k != "decisions"},
                             "eq_evidence": Counter(d.get("evidence") or d.get("reason") for d in am["eq_selection"]["decisions"].values())})
            fts.close()
        print(conv, len(rows), f"{time.time()-started:.0f}s", flush=True)
summary = {arm: {"questions": len(rows), "delivered_total": sum(r["delivered"][arm] for r in rows),
                 "empty": sum(1 for r in rows if r["delivered"][arm] == 0),
                 "cited_session_delivered": sum(r["cited_delivered"][arm] for r in rows),
                 "cited_session_total": sum(len(r["cited_sessions"]) for r in rows)} for arm in ARMS}
summary["eq"]["assessments"] = dict(Counter(r["eq_selection"]["assessment"] for r in rows))
summary["eq"]["uncertain_total"] = sum(r["eq_selection"]["uncertain_count"] for r in rows)
summary["eq"]["omitted_reasons"] = dict(sum((Counter(r["eq_selection"]["omitted_reasons"]) for r in rows), Counter()))
summary["eq"]["evidence_kinds"] = dict(sum((Counter(r["eq_evidence"]) for r in rows), Counter()))
report = {"kind": "locomo_category5_adversarial_unanswerable_unseen_no_answer_controls",
          "runtime_sha": subprocess.check_output(["git", "-C", str(runtime), "rev-parse", "HEAD"], text=True).strip(),
          "selector_blob": subprocess.check_output(["git", "-C", str(runtime), "hash-object", "reference/agentmem_ref/api/context_selection.py"], text=True).strip(),
          "raw_sha256": subprocess.check_output(["sha256sum", str(raw_path)], text=True).split()[0],
          "python": sys.version, "platform": platform.platform(), "k": K, "questions": len(rows), "summary": summary,
          "note": "A cited session is the dialogue the adversarial question was written from; it holds no answer, so delivering it is neither right nor wrong by itself. The honest signal is burden and the assessment the consumer receives."}
(out / "summary.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
(out / "rows.json").write_text(json.dumps(rows, indent=1, sort_keys=True) + "\n")
print(json.dumps(summary, indent=1))
