import json, sys
A = str(__import__("pathlib").Path(__file__).resolve().parents[4] / "integrations/agent-memory-mcp") + "/"
pairs = []
for name in ("quality_cases_dev.json", "quality_cases_adversarial.json"):
    d = json.load(open(A + name))
    texts = {r["key"]: r["text"] for r in d["records"]}
    for step in d.get("lifecycle", []):
        if step["op"] in ("correct", "rewrite"): texts[step["key"]] = step["text"]
        if step["op"] == "forget": texts.pop(step["key"])
    for t in d["tasks"]:
        for k, v in texts.items():
            pairs.append({"cohort": name, "id": t["id"], "question": t["question"], "key": k, "context": v})
json.dump(pairs, open("pairs.json", "w"))
print(len(pairs))
