import json
gold = json.load(open("scen3-gold.json"))
for key in ("c4-off", "cand-off", "c4-required", "cand-required"):
    rows = json.load(open(f"out3-{key}.json"))
    ab = [r for r in rows if r["scenario"] == "abstain"]; an = [r for r in rows if r["scenario"] == "answerable"]
    abst = sum(1 for r in ab if not r["returned"])
    tp = sum(len(set(r["returned"]) & set(gold[r["query"]])) for r in an)
    ret = sum(len(r["returned"]) for r in an); need = sum(len(gold[r["query"]]) for r in an)
    strict = sum(1 for r in an if set(gold[r["query"]]) <= set(r["returned"]) and set(r["returned"]) <= set(gold[r["query"]]))
    print(f"{key:14s} abstained {abst}/{len(ab)} (wrong facts returned on unanswerable: {sum(len(r['returned']) for r in ab)}) | "
          f"answerable: exact {strict}/{len(an)}, recall {tp}/{need}, precision {tp}/{ret}")
