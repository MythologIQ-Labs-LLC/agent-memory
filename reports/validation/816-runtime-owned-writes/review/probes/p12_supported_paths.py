"""P12: supported and read-only paths must not be refused by the guarded clock or token.

Facade methods (semantic retrieval on, #802 offline provider), module-level docs/44 READERS on the durable
adapter, runtime-level read and lifecycle helpers. Prints one line per call: ok / refusal envelope / EXCEPTION.
Then reopen.
"""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import *  # noqa: F401,F403
sys.path.insert(0, str(Path(REF)))
from unittest import mock
from agentmem_ref.api import surface
from agentmem_ref.runtime import representation_onnx
from agentmem_ref.runtime.runtime_composition import AsOfTarget
from tests.test_802_semantic_cache_deletion import _OfflineRepresentation, _authorized_permanent_forget

bad = []


def call(name, fn):
    try:
        r = fn()
        s = "ok"
        if isinstance(r, dict) and r.get("refusal"):
            s = f"ok (refusal envelope: {r['refusal']})"
    except Exception as exc:  # noqa: BLE001
        s = f"EXCEPTION {type(exc).__name__}: {str(exc)[:80]}"
        if type(exc).__name__ == "UngovernedDurableWrite":
            bad.append(name)
    print(f"  {name:48s} {s}")


root = tempfile.mkdtemp(prefix="816sp-")
with mock.patch.object(representation_onnx, "OnnxSentenceEmbeddingProvider", _OfflineRepresentation):
    m = AgentMemory.open(root, tenant=TENANT, actor_id="agent:a", scope=SCOPE, purpose="probe",
                         semantic_retrieval="required", recall_control="shadow")
    a = m.runtime.adapter
    ctxenv = {"contract_version": "1.3.0", "target_domain_refs": list(m._domain_refs()),
              "principal_ref": m.actor_id, "project_ref": m.scope, "purpose": m.purpose}
    call("remember", lambda: m.remember("memory:d", "The dog is Biscuit."))
    call("remember 2", lambda: m.remember("memory:b", "The budget has been approved."))
    call("correct", lambda: m.correct("memory:d", "The dog is Rex.", evidence_refs=("evidence:x",)))
    call("recall", lambda: m.recall("dog budget"))
    call("recall historical", lambda: m.recall("dog", temporal_intent={"mode": "historical"}))
    call("history", lambda: m.history("memory:d"))
    call("history with fact_text", lambda: m.history("memory:d", fact_text="The dog is Biscuit."))
    call("posture", m.posture)
    call("semantic_retrieval_posture", m.semantic_retrieval_posture)
    call("verify_semantic_store", m.verify_semantic_store)
    call("verify_semantic_store(rebuild=True)", lambda: m.verify_semantic_store(rebuild=True))
    call("legacy_upgrade_status", m.legacy_upgrade_status)
    call("upgrade_canonical_derivation", m.upgrade_canonical_derivation)
    fact = a.current_fact_uuid("memory:d")
    call("write_semantics", lambda: m.write_semantics(fact))
    call("semantic_proposals", m.semantic_proposals)
    call("dispute", lambda: m.dispute("memory:b"))
    call("forget", lambda: m.forget("memory:b"))
    call("permanent forget (attested)", lambda: _authorized_permanent_forget(m, "memory:d"))
    call("surface.propose (reader) on durable adapter",
         lambda: surface.propose(a, m._proposal(target_reference="memory:z", operation="promotion", fact_text="x")))
    call("surface.approve (reader) on durable adapter",
         lambda: surface.approve(a, m._proposal(target_reference="memory:z", operation="promotion", fact_text="x")))
    call("surface.history (reader) on durable adapter",
         lambda: surface.history(a, {"contract_version": "1.3.0", "target_reference": "memory:d"}))
    rt = m.runtime
    ctx = m._handle_recall_context()
    call("runtime.historical_predecessor_context",
         lambda: rt.historical_predecessor_context("dog", ctx, budget=3,
                                                    as_of_target=AsOfTarget(memory_ref="memory:d", instant="2026-01-01T00:00:30Z")))
    call("runtime.routed_historical_context", lambda: rt.routed_historical_context("dog", ctx, budget=3))
    call("runtime.projection_admission", rt.projection_admission)
    call("runtime.rebuild_projection", rt.rebuild_projection)
    call("runtime.disable_projection_component", lambda: rt.disable_projection_component("memory:d"))
    call("runtime.restore_and_rebuild_projection_component",
         lambda: rt.restore_and_rebuild_projection_component("memory:d", scope=SCOPE))
    call("durable.persist_visibility_snapshot",
         lambda: rt.durable_runtime.persist_visibility_snapshot("op:p", {"operation": {"required_projection_ids": []}}))
    call("durable.checkpoint", rt.durable_runtime.checkpoint)
    call("durable.base.backup_to", lambda: rt.durable_runtime.base.backup_to(Path(root) / "backup.sqlite3"))
    m.close()
    print("  reopen:", try_reopen(root))
    m2 = AgentMemory.open(root, tenant=TENANT, actor_id="agent:a", scope=SCOPE, purpose="probe",
                          semantic_retrieval="required")
    call("after reopen: recall", lambda: m2.recall("budget"))
    call("after reopen: history", lambda: m2.history("memory:b"))
    m2.close()
print("UngovernedDurableWrite on supported paths:", bad or "none")
