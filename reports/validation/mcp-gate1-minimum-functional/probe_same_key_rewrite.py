import json, tempfile
from pathlib import Path
from agentmem_ref import AgentMemory
d = tempfile.TemporaryDirectory(); root = Path(d.name)/"s"
m = AgentMemory.open(root, tenant="tenant:p", actor_id="agent:p", scope="project:p", purpose="probe")
a = m.remember("memory:editor", "The owner writes Python in Neovim.", source_ref="mcp:agent-observation")
b = m.remember("memory:editor", "The owner writes Python in VS Code.", source_ref="mcp:agent-observation")
print("first", a["committed"], a["fact_uuid"], a["outcome"]); print("second", b["committed"], b["fact_uuid"], b["outcome"], b.get("refusal"))
ad = m.runtime.adapter
print("memory_ref_of first", ad.memory_ref_of(a["fact_uuid"]), "| second", ad.memory_ref_of(b["fact_uuid"]))
r = m.recall("Which editor does the owner use for Python?", budget=5)
for ref in r["returned"]: print(" find returned", ref, r["admissions"][ref]["admission_basis"])
g = m.recall("memory:editor", logical_memory_refs=("memory:editor",), budget=8)
print("exact-route returned", g["returned"], [r2 for r2 in g["admissions"] ])
h = m.history("memory:editor") if hasattr(m, "history") else None
print("history", json.dumps(h, default=str)[:600] if h else "n/a")
m.close()
