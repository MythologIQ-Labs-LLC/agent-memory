"""Diagnostic trace of AgentMemory.recall selection on LongMemEval-S (session or turn plane).

Usage: python lme_trace.py <reference_dir> <longmemeval_s_cleaned.json> <plane> <out.jsonl> [shard] [nshards]
Gold labels are used ONLY to annotate the trace; they never reach the runtime.
"""
import json, math, sys, tempfile
from pathlib import Path

ref, data, plane, out = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4])
shard, nshards = (int(sys.argv[5]), int(sys.argv[6])) if len(sys.argv) > 6 else (0, 1)
sys.path.insert(0, str(ref))
import run_longmemeval as M  # noqa: E402
from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.runtime import return_selection as RS  # noqa: E402
from agentmem_ref.runtime.ranking_policy import relevance_tokens  # noqa: E402

rows = json.loads(data.read_text())
with out.open("w") as fh:
    for index, row in enumerate(rows):
        if index % nshards != shard:
            continue
        if row["question_id"].endswith("_abs"):
            qtype = "abstention"
        else:
            qtype = row["question_type"]
        items, gold = M.corpus(row, plane)
        question = row["question"]
        with tempfile.TemporaryDirectory() as tmp:
            with AgentMemory.open(tmp, tenant=f"tenant:t{index}", actor_id="agent:b", scope=f"s:{index}", purpose="diag") as m:
                u2i, texts = {}, {}
                for k, item in enumerate(items):
                    r = m.remember(f"memory:{index}:{k}", item["text"])
                    if r.get("fact_uuid"):
                        u2i[r["fact_uuid"]] = item["id"]
                        texts[r["fact_uuid"]] = item["text"]
                res = m.recall(question, budget=50)
        terms = set(RS.informative_terms(question))
        adm = res["admissions"]
        n = len(res["admitted"])
        docs = {u: set(relevance_tokens(RS.normalize_contractions(texts[u]))) for u in res["admitted"]}
        df = {t: sum(1 for u in docs if t in docs[u]) for t in terms}
        idf = {t: math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5)) for t in terms if df[t]}
        rec = []
        for u in res["admitted"]:
            sel = adm[u].get("return_selection") or {}
            matched = sorted(t for t in terms if t in docs[u])
            rec.append({"id": u2i[u], "gold": u2i[u] in set(gold), "rank": adm[u].get("rank_position"),
                        "bm25": (adm[u].get("ranking_evidence") or {}).get("lexical_relevance_score"),
                        "content": sel.get("content_relevance"), "rel": sel.get("relative_to_best"),
                        "basis": sel.get("basis"), "returned": u in res["returned"], "len": len(texts[u].split()),
                        "matched": matched})
        fh.write(json.dumps({"qid": row["question_id"], "qtype": qtype, "question": question, "gold": gold,
                             "terms": sorted(terms), "idf": idf, "n_items": len(items), "admitted": rec}) + "\n")
        fh.flush()
