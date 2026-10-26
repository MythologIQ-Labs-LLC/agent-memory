"""v7-origin store with legacy self-references (#809 qualification gap raised on #815, 2026-10-20).

A, in project:a, writes:
- memory:a = a1 (the source; deleted at the end);
- memory:prior citing a1 (prior-id control: a genuine dependency);
- memory:self citing its OWN id (learned from a discovery pass with the same deterministic ids);
- memory:mixed citing a1 AND its own id;
- memory:fwd citing the id memory:next receives later (next-id control);
- memory:next.

Then A forgets memory:a. B, in project:b, writes memory:b citing nothing (a scope-isolation
control). Under the #809 ruling only a1 can be a dependency: a self-reference names no fact that
existed when the citing fact was written."""
import json, sys, tempfile
sys.path.insert(0, sys.argv[1])
from agentmem_ref import AgentMemory
import agentmem_ref
T, Q = "tenant:legacy", "Quillon ferry berth"


def scenario(root, self_id, mixed_id, next_id):
    m = AgentMemory.open(root, tenant=T, actor_id="agent:legacy", scope="project:a", purpose="legacy")
    a1 = m.remember("memory:a", f"{Q} is Oslo")["fact_uuid"]
    prior = m.remember("memory:prior", f"{Q} digest prior", evidence_refs=(a1,))["fact_uuid"]
    self_ = m.remember("memory:self", f"{Q} digest self", evidence_refs=(self_id,))["fact_uuid"]
    mixed = m.remember("memory:mixed", f"{Q} digest mixed", evidence_refs=(a1, mixed_id))["fact_uuid"]
    fwd = m.remember("memory:fwd", f"{Q} digest fwd", evidence_refs=(next_id,))["fact_uuid"]
    nxt = m.remember("memory:next", f"{Q} digest next")["fact_uuid"]
    assert m.forget("memory:a")["committed"]
    m.close()
    b = AgentMemory.open(root, tenant=T, actor_id="agent:other", scope="project:b", purpose="legacy")
    other = b.remember("memory:b", f"{Q} digest other")["fact_uuid"]
    b.close()
    return {"a1": a1, "prior": prior, "self": self_, "mixed": mixed, "fwd": fwd, "next": nxt, "other": other}


with tempfile.TemporaryDirectory() as d:
    found = scenario(d + "/m", "external:placeholder-self", "external:placeholder-mixed", "external:placeholder-next")
ids = scenario(sys.argv[2], found["self"], found["mixed"], found["next"])
assert ids == found, (ids, found)
print(json.dumps(ids))
