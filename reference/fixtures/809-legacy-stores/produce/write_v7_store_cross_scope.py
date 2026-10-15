"""Write a store with the published v7 runtime: A seeds a1 and its own derivation d1; B cites a1 (foreign); A prunes memory:a."""
import json, sys
sys.path.insert(0, sys.argv[1])
from agentmem_ref import AgentMemory
import agentmem_ref
root = sys.argv[2]
T, Q = "tenant:legacy", "Quillon ferry berth"
def open_(scope, actor="agent:legacy"):
    return AgentMemory.open(root, tenant=T, actor_id=actor, scope=scope, purpose="legacy")
a = open_("project:a")
a1 = a.remember("memory:a", f"{Q} is Oslo")["fact_uuid"]
a2 = a.remember("memory:a2", f"{Q} is Bergen")["fact_uuid"]
d1 = a.remember("memory:d1", f"{Q} digest own", evidence_refs=(a1,))["fact_uuid"]
ctl = a.remember("memory:ctl", f"{Q} digest control", evidence_refs=("evidence:ticket-7",))["fact_uuid"]
a.close()
b = open_("project:b")
bd = b.remember("memory:bd", f"{Q} digest foreign deleted", evidence_refs=(a1,))["fact_uuid"]
bl = b.remember("memory:bl", f"{Q} digest foreign live", evidence_refs=(a2,))["fact_uuid"]
bu = b.remember("memory:bu", f"{Q} digest unknown", evidence_refs=("fact-guess-999999999999",))["fact_uuid"]
b.close()
a = open_("project:a")
out = a.forget("memory:a"); assert out["committed"], out
a.close()
print(json.dumps({"package": agentmem_ref.__file__, "a1": a1, "a2": a2, "d1": d1, "ctl": ctl, "bd": bd, "bl": bl, "bu": bu}))
