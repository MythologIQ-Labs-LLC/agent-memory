import json, sys, re
from pathlib import Path
sys.path.insert(0, "/tmp/claude-0/wt/c4/reference")
from agentmem_ref.state.substrate import _tokens
from agentmem_ref.runtime.lexical_normalization import normalized_text, _key
from agentmem_ref.runtime.return_selection import interpret_query
tot = {}
for b in sys.argv[2:]:
    data = json.loads(Path(f"fx/{b}.json").read_text()); scen = data["scenarios"] if isinstance(data, dict) else data
    run = {r["id"]: r for r in json.loads(Path(f"runs{sys.argv[1]}").read_text().replace("", "") if False else Path(sys.argv[1].replace("BASE", b)).read_text())["rows"]}
    for s in scen:
        for q in s["queries"]:
            texts = {}
            for op in s["operations"]:
                if op["scope"] != q["scope"]: continue
                if op["op"] in ("remember", "correct"): texts[op["ref"]] = op["text"]
                else: texts.pop(op["ref"], None)
            r = run[q["id"]]
            qw = set(_tokens(q["query"])); qk = {_key(t) for t in qw}
            qn = set(normalized_text(q["query"]).split())
            topical = set(normalized_text(" ".join(interpret_query(q["query"]).topical_terms)).split())
            for need, st in r["stages"].items():
                if st["stage"] != "never_discovered" or need not in texts: continue
                t = texts[need]
                ws = qw & set(_tokens(t)); ks = qk & {_key(x) for x in _tokens(t)}
                rn = qn & set(normalized_text(t).split()); rt = topical & set(normalized_text(t).split())
                cls = "ws-overlap?" if ws else ("key-overlap(C3)" if ks else ("regex-only:topical" if rt else ("regex-only:function" if rn else "no-overlap")))
                tot[cls] = tot.get(cls, 0) + 1
                if cls.startswith("regex"): print(b, q["query"], "|", t, "|", sorted(rn))
print(tot)
