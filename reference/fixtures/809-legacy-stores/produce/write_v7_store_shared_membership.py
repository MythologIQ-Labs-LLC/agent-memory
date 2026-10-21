"""v7-origin store with shared-domain legacy edges: owner O writes s1 into shared:x alone (host override);
member M (member at write time) and stranger C (not a member at write time) each cite s1; a later-granted
member L cites s1 before being granted; O prunes memory:s. Membership at write time is NOT durably recorded
by the v7 runtime (set_shared_domain_members is an in-memory seam persisted as current state only)."""
import json, sys
sys.path.insert(0, sys.argv[1])
from agentmem_ref import AgentMemory
import agentmem_ref
root = sys.argv[2]
T, Q = "tenant:legacy", "Quillon ferry berth"
SH = {"isolation_domain_refs": ["shared:x"], "required_isolation_domain_refs": ["shared:x"]}
def open_(actor):
    return AgentMemory.open(root, tenant=T, actor_id=actor, scope="shared:x", purpose="legacy")
o = open_("agent:o")
o.runtime.adapter.set_shared_domain_members("shared:x", ("agent:o", "agent:m"))
s1 = o.remember("memory:s", f"{Q} is Thursday", overrides=SH)["fact_uuid"]
o.close()
m = open_("agent:m"); sm = m.remember("memory:sm", f"{Q} digest member", evidence_refs=(s1,), overrides=SH)["fact_uuid"]; m.close()
c = open_("agent:c"); sc = c.remember("memory:sc", f"{Q} digest stranger", evidence_refs=(s1,), overrides=SH)["fact_uuid"]; c.close()
l = open_("agent:l"); sl = l.remember("memory:sl", f"{Q} digest later", evidence_refs=(s1,), overrides=SH)["fact_uuid"]; l.close()
o = open_("agent:o")
o.runtime.adapter.set_shared_domain_members("shared:x", ("agent:o", "agent:m", "agent:l"))  # grant l after its write
out = o.forget("memory:s"); assert out["committed"], out  # the governed act persists the membership change
o.close()
print(json.dumps({"package": agentmem_ref.__file__, "s1": s1, "sm": sm, "sc": sc, "sl": sl,
                  "members_at_write": {"agent:o": True, "agent:m": True, "agent:c": False, "agent:l": False},
                  "members_now": ["agent:o", "agent:m", "agent:l"]}))
