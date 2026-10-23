import json, sys
from pathlib import Path
sys.path.insert(0, "/home/user/eval/g2/wt-exp/reference")
from agentmem_ref.core.content_terms import content_terms
off, on, plane = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
rows = lambda d: {r["id"]: r for r in map(json.loads, (d / "rows.jsonl").read_text().splitlines()) if r}
ro, rn = rows(off), rows(on)
data = {q["question_id"]: q for q in json.load(open("/home/user/eval/data/longmemeval_s_cleaned.json"))}
r0 = next(iter(ro.values())); print({k: (type(v).__name__, str(v)[:120]) for k, v in r0.items() if k in ("gold", "ids", "scores", "items")})
def session_text(q, sid):
    for s_id, sess in zip(q["haystack_session_ids"], q["haystack_sessions"]):
        if s_id == sid:
            return " ".join(t["content"] for t in sess if t.get("role") == "user")
    return None
lost = []
for i, a in ro.items():
    b = rn[i]
    missing = [g for g in a["gold"] if g in a["ids"]["default"] and g not in b["ids"]["default"]]
    if missing:
        lost.append((i, missing))
print("questions losing required items ON vs OFF (default arm):", len(lost), "items:", sum(len(m) for _, m in lost))
kinds = {}
for i, missing in lost[:40]:
    q = data[i]; qt = content_terms(q["question"])
    for g in missing:
        text = session_text(q, g)
        shared = sorted(qt & content_terms(text)) if text else None
        kinds.setdefault(q["question_type"], 0); kinds[q["question_type"]] += 1
        if text is not None and len(lost) <= 40:
            print(f"  {i} [{q['question_type']}] Q={q['question'][:80]!r} shared_content={shared} gold_len={len(text.split())}")
print("by type:", kinds)
