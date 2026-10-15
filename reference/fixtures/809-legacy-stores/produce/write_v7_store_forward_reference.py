"""v7-origin store with a forward reference: A deletes memory:a (old generation a1), writes memory:fwd citing
the id that memory:late will receive (learned from a discovery pass with the same deterministic ids), then
writes memory:late citing a1. Under v7 the forward note became refused once 'late' existed (late binding);
under the #809 ruling it never binds."""
import json, sys, tempfile
sys.path.insert(0, sys.argv[1])
from agentmem_ref import AgentMemory
import agentmem_ref
T, Q = "tenant:legacy", "Quillon ferry berth"
def scenario(root, future):
    m = AgentMemory.open(root, tenant=T, actor_id="agent:legacy", scope="project:a", purpose="legacy")
    a1 = m.remember("memory:a", f"{Q} is Oslo")["fact_uuid"]
    assert m.forget("memory:a")["committed"]
    fwd = m.remember("memory:fwd", f"{Q} digest forward", evidence_refs=(future,))["fact_uuid"]
    late = m.remember("memory:late", f"{Q} digest late", evidence_refs=(a1,))["fact_uuid"]
    m.close()
    return a1, fwd, late
with tempfile.TemporaryDirectory() as d:
    _, _, late_id = scenario(d + "/m", "external:placeholder")
a1, fwd, late = scenario(sys.argv[2], late_id)
assert late == late_id
print(json.dumps({"package": agentmem_ref.__file__, "a1": a1, "fwd": fwd, "late": late}))
