import sys, json, tempfile
sys.path.insert(0, sys.argv[1])
from agentmem_ref import AgentMemory
from tests.test_644_combined_independent import _prop, _evidence
d = tempfile.mkdtemp(); root = d + "/m"
op = lambda scope: AgentMemory.open(root, tenant="tenant:c644", actor_id="agent:c644", scope=scope, purpose="c644")
m = op("project:a")
old = m.remember("memory:a", "Orrin gateway region is Oslo", proposition=_prop("Oslo"))["fact_uuid"]
new = m.correct("memory:a", "Orrin gateway region is Bergen", evidence=_evidence(), risk_class="low", replacement_kind="state_change")["fact_uuid"]
print("forget", m.forget("memory:a")["committed"]); m.close()
b = op("project:b")
h = b.history("memory:a")["history"]
s = json.dumps(h)
print("project:b history of project:a memory -> tombstoned:", h["tombstoned"], "events:", len(h["events"]), "has timestamps:", "timestamp" in s, "deleted ids:", old in s or new in s)
print("event types:", sorted({e["event_type"] for e in h["events"]}))
print("nonexistent memory ->", b.history("memory:nope")["history"])
r = b.recall("Orrin gateway region Oslo", temporal_intent={"mode": "historical"})
print("project:b recall exposes project:a ids:", old in json.dumps(r) or new in json.dumps(r))
b.close()
