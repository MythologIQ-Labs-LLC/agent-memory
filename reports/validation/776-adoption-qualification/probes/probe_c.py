import sys, json, tempfile, subprocess
sys.path.insert(0, sys.argv[1])
from agentmem_ref import AgentMemory
from tests.test_644_combined_independent import _prop, _evidence
from tests.test_typed_propositions import TEXT, PROP
Q = "Orrin gateway region"
def opn(root, scope="project:a"):
    return AgentMemory.open(root, tenant="tenant:c644", actor_id="agent:c644", scope=scope, purpose="c644")
def grep(root, s):
    return subprocess.run(["grep", "-rlaF", s, root], capture_output=True, text=True).stdout.split()
d = tempfile.mkdtemp(); root = d + "/m"; m = opn(root)
old = m.remember("memory:a", f"{Q} is Oslo", proposition=_prop("Oslo"))["fact_uuid"]
new = m.correct("memory:a", f"{Q} is Bergen", evidence=_evidence(), risk_class="low", replacement_kind="state_change")["fact_uuid"]
# transitive derivation
d1 = m.remember("memory:d1", "Digest one: the gateway region used to be Oslo", evidence_refs=(old,))["fact_uuid"]
d2 = m.remember("memory:d2", "Digest two: earlier the gateway region was Oslo", evidence_refs=(d1,))["fact_uuid"]
# relation on surviving fact: typed pair, then delete the target memory
a1 = m.remember("memory:ra", TEXT["room_old"], proposition=PROP["room_old"])["fact_uuid"]
b1 = m.remember("memory:rb", TEXT["room_new"], proposition=PROP["room_new"])["fact_uuid"]
print("forget a", m.forget("memory:a")["committed"], "forget ra", m.forget("memory:ra")["committed"])
r = m.recall("gateway region Oslo digest", temporal_intent={"mode": "historical"})
print("C3 transitive: d1 admitted", d1 in r["admitted"], "d2 admitted", d2 in r["admitted"], "| d2 semantics visible", m.write_semantics(d2) is not None)
blob = json.dumps(r)
print("C1 recall output mentions deleted ids:", {x: x in blob for x in (old, new)}, "mentions 'Oslo' outside admitted d2:", "Oslo" in json.dumps({k: v for k, v in r.items() if k != "admitted"}))
print("   recall keys", sorted(r)[:20])
ws = m.write_semantics(b1); rel = ws.get("relations", [])
print("C2 surviving relation:", [(x.get("other_fact_uuid"), x.get("other_memory_ref"), x.get("classification")) for x in rel], "| deleted value 'Aurora' in b1 semantics:", "Aurora" in json.dumps(ws), "(b1 declared replaces_value Aurora itself)")
print("   semantic_proposals:", [(p["target_fact_uuid"], p["target_reference"]) for p in m.semantic_proposals()])
print("   history(memory:a) keys:", list(m.history("memory:a")["history"]), "tombstoned", m.history("memory:a")["history"]["tombstoned"])
m.close()
print("C5 pruned text on disk (expected: recoverable):", bool(grep(root, "is Oslo")))
m = opn(root); print("C4 after reopen: write_semantics(old)", m.write_semantics(old), "d1 recall", d1 in m.recall("gateway region Oslo digest", temporal_intent={"mode":"historical"})["admitted"]); m.close()
