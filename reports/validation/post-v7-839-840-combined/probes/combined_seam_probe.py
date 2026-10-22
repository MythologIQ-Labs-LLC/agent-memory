"""Adversarial probes of the composed #839 + #840 seam (PYTHONPATH=reference, repo root)."""
import json, shutil, tempfile, os, threading
from pathlib import Path
from agentmem_ref import AgentMemory
from agentmem_ref.api import surface
from agentmem_ref.host_activation import open_qualified_memory, UnqualifiedLegacyStoreError
from agentmem_ref.memory import procedural_memory as pm
T, P, TEXT, SRC = "tenant:c", "project:c", "The orchard gate code is 4471.", "private:owner-ref"
def ident(actor, scope=P, tenant=T): return dict(tenant=tenant, actor_id=actor, scope=scope, purpose="probe")
def receipts_of(m): return [e for e in m.runtime.adapter.events if e.get("event_type") == "memory.context_delivery"]
d = Path(tempfile.mkdtemp()); root = d / "store"
# P1 cross-actor privacy through the gate: writer, same-project colleague, other project, other tenant, spoofed actor
with open_qualified_memory(root, **ident("agent:writer")) as w:
    fact = w.remember("memory:gate", TEXT, source_ref=SRC)["fact_uuid"]
    pw = w.recall_context("orchard gate code")["items"][0]["provenance"]
print("P1 writer sees memory_ref/source_ref:", "memory_ref" in pw, pw.get("source_ref") == SRC)
with open_qualified_memory(root, **ident("agent:colleague")) as c:
    pkg = c.recall_context("orchard gate code"); it = pkg["items"][0]
    print("P1 colleague: text", it["content"] == TEXT, "| private refs hidden", "memory_ref" not in it["provenance"] and "source_ref" not in it["provenance"], "| receipt mentions private ref/text:", any(s in json.dumps(receipts_of(c)[-1]) for s in (SRC, "4471", "memory:gate")))
with open_qualified_memory(root, **ident("agent:other", scope="project:other")) as o:
    pkg = o.recall_context("orchard gate code"); print("P1 other project:", pkg["status"], "items", len(pkg["items"]), "| receipt names fact id:", fact in json.dumps(receipts_of(o)[-1]))
try:
    with open_qualified_memory(root, **ident("agent:x", tenant="tenant:other")) as o: print("P1 FAIL other tenant opened")
except Exception as exc: print("P1 other tenant refused by runtime:", type(exc).__name__)
with open_qualified_memory(root, **ident("agent:writer")) as spoof:
    print("P1 spoofed host-declared actor_id gets writer provenance (documented host-binding limit):", "memory_ref" in spoof.recall_context("orchard gate code")["items"][0]["provenance"])
# P2 deletion + restart through the gate: deleted content never redelivered; deleted ids never in receipts
skill = pm.SkillArtifact(skill_id="skill:p", version=1, purpose="p", scope=P, isolation_domain_refs=(T, P), required_isolation_domain_refs=(T, P), procedure_markdown="# v\nok", provenance_refs=("evidence:p",))
with open_qualified_memory(root, **ident("agent:writer")) as w:
    print("P2 forget committed:", w.forget("memory:gate", evidence=pm.evidence_for(skill))["committed"])
    w.remember("memory:other", "The orchard gate is painted green.")
    pkg = w.recall_context("orchard gate")
    print("P2 after forget (same handle): deleted text absent", all("4471" not in i["content"] for i in pkg["items"]), "| deleted id in package/receipts:", fact in json.dumps(pkg), any(fact in json.dumps(e) for e in receipts_of(w)))
with open_qualified_memory(root, **ident("agent:writer")) as w:
    pkg = w.recall_context("orchard gate code 4471")
    print("P2 after restart: deleted text absent", all("4471" not in i["content"] for i in pkg["items"]), "| receipts durable:", len(receipts_of(w)), "| deleted id anywhere in events:", any(fact in json.dumps(e) for e in receipts_of(w)))
# P3 audit atomicity through the gate: persistence failure rolls back receipt; reopen clean; store usable
with open_qualified_memory(root, **ident("agent:writer")) as w:
    base = getattr(w.runtime.durable_runtime, "base", w.runtime.durable_runtime); before = len(receipts_of(w)); orig = base._persist_unlocked
    base._persist_unlocked = lambda: (_ for _ in ()).throw(OSError("disk full"))
    try: w.recall_context("orchard"); print("P3 NOT RAISED")
    except OSError: pass
    base._persist_unlocked = orig
    print("P3 receipts unchanged after persist failure:", len(receipts_of(w)) == before, "| store usable:", w.remember("memory:after", "The greenhouse reads 18 degrees.")["committed"])
with open_qualified_memory(root, **ident("agent:writer")) as w: print("P3 after reopen receipts:", len(receipts_of(w)), "unique ids:", len({e["event_id"] for e in receipts_of(w)}) == len(receipts_of(w)))
# P4 legacy activation x context delivery
fx = Path("reference/fixtures/809-legacy-stores"); pend = d / "pend"; shutil.copytree(fx / "cross-scope", pend); LID = dict(tenant="tenant:legacy", actor_id="agent:legacy", scope="project:b", purpose="probe")
try:
    with open_qualified_memory(pend, **LID): print("P4 FAIL")
except UnqualifiedLegacyStoreError: print("P4 pending store refused by gate before any recall_context")
with AgentMemory.open(pend, **LID) as plain: print("P4 plain open delivers context from the pending store (opt-in limit):", plain.recall_context("Quillon ferry berth")["status"], "receipt written:", len(receipts_of(plain)))
# P5 first open through the gate with a planted temp symlink; and the gate on a dangling-config root
r2 = d / "r2"; r2.mkdir(); victim = d / "victim"; victim.write_text("KEEP"); (r2 / ".runtime-config.json.tmp").symlink_to(victim)
with open_qualified_memory(r2, **ident("agent:w")) as m: print("P5 gate first open: victim intact", victim.read_text() == "KEEP", "status", m.legacy_upgrade_status()["status"])
# P6 recall() AST parity of the combined surface vs the v7 base
import ast, subprocess
def meth(src):
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.ClassDef) and n.name == "AgentMemory":
            return {i.name: ast.dump(i) for i in n.body if isinstance(i, ast.FunctionDef)}
base = meth(subprocess.check_output(["git", "show", "72d6a903:reference/agentmem_ref/api/surface.py"], text=True)); head = meth(open("reference/agentmem_ref/api/surface.py").read())
print("P6 recall() AST identical to v7 base:", base["recall"] == head["recall"], "| open() changed:", base["open"] != head["open"], "| methods changed:", [k for k in base if k in head and base[k] != head[k]])
