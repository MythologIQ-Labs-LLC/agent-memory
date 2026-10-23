import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "integrations/agent-memory-mcp"))
import answer_support as a
s = a.AnswerSupport(Path(sys.argv[1]))
out = [s.span_found(p["question"], p["context"]) for p in json.load(open("pairs.json"))]
json.dump(out, open("ours.json", "w"))
print(sum(out), len(out))
