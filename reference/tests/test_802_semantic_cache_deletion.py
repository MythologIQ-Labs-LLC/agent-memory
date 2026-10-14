"""#802: fail-first public facade semantic-vector sidecar erasure probes.

This is a test-only reproduction candidate on an isolated branch. It does not
change canonical runtime or claim policy discharge beyond an explicit, bound
test-host attestation. The first two tests should fail against the unmodified
base if the cache retains bytes after successful physical canonical deletion.
"""

from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentmem_ref import AgentMemory, policy  # noqa: E402
from agentmem_ref.runtime import representation_onnx  # noqa: E402
from agentmem_ref.runtime.vector_retrieval import VectorRepresentationSpec  # noqa: E402


TENANT = "tenant:semantic-delete-repro"
SCOPE = "project:semantic-delete-repro"
TARGET = "memory:deleted-pet"
CONTROL = "memory:kept-budget"


class _OfflineRepresentation:
    """Model-free provider to make the derived SQLite cache reproducible."""

    spec = VectorRepresentationSpec(
        representation_ref="test:802-offline-embedding",
        representation_version="1.0.0",
        config_digest="sha256:" + "de" * 32,
        dimensions=3,
        deterministic_rebuild=True,
    )

    def __init__(self, model_dir=None) -> None:
        pass

    def embed(self, text: str) -> tuple[float, ...]:
        lower = text.lower()
        return (1.0 if "dog" in lower else 0.0, 1.0 if "budget" in lower else 0.0, 0.1)


def _stored_fact_refs(path: str) -> set[str]:
    """Inspect physical cache state independently of the governed read path."""

    with sqlite3.connect(path) as connection:
        return {str(row[0]) for row in connection.execute("SELECT fact_uuid FROM vectors")}


def _open(root: Path) -> AgentMemory:
    return AgentMemory.open(
        root,
        tenant=TENANT,
        actor_id="agent:802-test",
        scope=SCOPE,
        purpose="deterministic semantic erasure qualification",
        semantic_retrieval="required",
    )


def _seed_cached_facts(memory: AgentMemory) -> tuple[str, str, str]:
    deleted = memory.remember(TARGET, "The dog is Biscuit.")
    retained = memory.remember(CONTROL, "The budget has been approved.")
    assert deleted["committed"] and retained["committed"]
    # Force both physical derived rows through the supported facade's route.
    memory.recall("dog budget")
    cache_path = memory.semantic_retrieval_posture()["store"]["path"]
    assert _stored_fact_refs(cache_path) == {deleted["fact_uuid"], retained["fact_uuid"]}
    return str(deleted["fact_uuid"]), str(retained["fact_uuid"]), cache_path


def _authorized_permanent_forget(memory: AgentMemory) -> dict:
    """Bind a test-host attestation to precisely the facade's delete proposal.

    _proposal is consulted only to obtain the exact protected proposal identity
    for this test authority fixture. Production callers must not self-ratify.
    """
    proposal = memory._proposal(
        target_reference=TARGET,
        operation="permanent_deletion",
        current_strength="reinforced",
        proposed_strength="not_applicable",
        reversibility="irreversible",
        risk_class="high",
    )
    attestation = policy.ExternalVerification(
        bound_proposal_id=str(proposal["proposal_id"]),
        verifier_principal_id="human:802-independent-reviewer",
        authority_kind=policy.HUMAN_CONFIRMATION,
        max_risk_class="critical",
    )
    result = memory.forget(TARGET, permanent=True, risk_class="high", attestation=attestation)
    if not result["committed"]:
        raise AssertionError(
            f"test setup did not achieve an authorized permanent deletion: {result!r}"
        )
    return result


class SemanticSidecarErasureContractTests(unittest.TestCase):
    def test_authorized_permanent_forget_removes_cached_embedding(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            with mock.patch.object(
                representation_onnx, "OnnxSentenceEmbeddingProvider", _OfflineRepresentation
            ):
                with _open(Path(folder)) as memory:
                    deleted_ref, control_ref, cache_path = _seed_cached_facts(memory)
                    _authorized_permanent_forget(memory)
                    self.assertIsNone(memory.runtime.adapter.checkpoint_substrate().get_fact(deleted_ref))
                    self.assertEqual(
                        _stored_fact_refs(cache_path),
                        {control_ref},
                        "permanent forgetting reported a canonical commit but retained a "
                        "derived vector-cache row for the erased fact",
                    )

    def test_permanent_delete_residue_does_not_survive_reopen(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with mock.patch.object(
                representation_onnx, "OnnxSentenceEmbeddingProvider", _OfflineRepresentation
            ):
                with _open(root) as memory:
                    deleted_ref, control_ref, cache_path = _seed_cached_facts(memory)
                    _authorized_permanent_forget(memory)
                with _open(root) as recovered:
                    self.assertNotIn(deleted_ref, recovered.recall("dog")["admitted"])
                    self.assertEqual(
                        _stored_fact_refs(cache_path),
                        {control_ref},
                        "recovery retained a derived vector row for a permanently deleted fact",
                    )

    def test_denied_permanent_forget_does_not_scrub_a_live_fact(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            with mock.patch.object(
                representation_onnx, "OnnxSentenceEmbeddingProvider", _OfflineRepresentation
            ):
                with _open(Path(folder)) as memory:
                    deleted_ref, control_ref, cache_path = _seed_cached_facts(memory)
                    denied = memory.forget(TARGET, permanent=True)
                    self.assertFalse(denied["committed"])
                    self.assertIsNotNone(
                        memory.runtime.adapter.checkpoint_substrate().get_fact(deleted_ref)
                    )
                    self.assertEqual(_stored_fact_refs(cache_path), {deleted_ref, control_ref})


if __name__ == "__main__":
    unittest.main()
