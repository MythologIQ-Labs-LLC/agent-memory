"""#802: public-facade semantic-vector sidecar erasure probes.

The first three tests are the original fail-first reproducer (branch
``tests/802-semantic-cache-erasure-reproducer-no-ci`` at ``490c284d``), kept
verbatim: the first two fail on ``main`` ``3eebb6d`` and pass once authorized
permanent deletion reconciles the derived sidecars. The remaining tests are the
adversarial lifecycle, authority and durability cases for that reconciliation.

Every assertion about stored bytes reads the SQLite files through independent
connections, never through the governed read path. The offline representation
provider makes the derived cache reproducible without a model or inference.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentmem_ref import AgentMemory, policy  # noqa: E402
from agentmem_ref.memory import procedural_memory as pm  # noqa: E402
from agentmem_ref.runtime import representation_cache, representation_onnx  # noqa: E402
from agentmem_ref.runtime.representation_cache import (  # noqa: E402
    DerivedCacheReconciliationError,
    DerivedVectorStore,
)
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


class _RotatedRepresentation(_OfflineRepresentation):
    """A second representation identity: its own persistent sidecar file."""

    spec = VectorRepresentationSpec(
        representation_ref="test:802-offline-embedding-rotated",
        representation_version="2.0.0",
        config_digest="sha256:" + "ef" * 32,
        dimensions=3,
        deterministic_rebuild=True,
    )


def _stored_fact_refs(path: str) -> set[str]:
    """Inspect physical cache state independently of the governed read path."""

    with sqlite3.connect(path) as connection:
        return {str(row[0]) for row in connection.execute("SELECT fact_uuid FROM vectors")}


def _canonical_fact_refs(root: Path) -> set[str]:
    """Physical canonical ``facts`` rows, through an independent connection."""

    with sqlite3.connect(root / "agent-memory.sqlite3") as connection:
        return {str(row[0]) for row in connection.execute("SELECT uuid FROM facts")}


def _open(root: Path, *, semantic_retrieval: str = "required", scope: str = SCOPE, store_profile=None) -> AgentMemory:
    return AgentMemory.open(
        root,
        tenant=TENANT,
        actor_id="agent:802-test",
        scope=scope,
        purpose="deterministic semantic erasure qualification",
        semantic_retrieval=semantic_retrieval,
        store_profile=store_profile,
    )


def _provider(provider=_OfflineRepresentation):
    return mock.patch.object(representation_onnx, "OnnxSentenceEmbeddingProvider", provider)


def _seed_cached_facts(memory: AgentMemory) -> tuple[str, str, str]:
    deleted = memory.remember(TARGET, "The dog is Biscuit.")
    retained = memory.remember(CONTROL, "The budget has been approved.")
    assert deleted["committed"] and retained["committed"]
    # Force both physical derived rows through the supported facade's route.
    memory.recall("dog budget")
    cache_path = memory.semantic_retrieval_posture()["store"]["path"]
    assert _stored_fact_refs(cache_path) == {deleted["fact_uuid"], retained["fact_uuid"]}
    return str(deleted["fact_uuid"]), str(retained["fact_uuid"]), cache_path


def _authorized_permanent_forget(memory: AgentMemory, target: str = TARGET) -> dict:
    """Bind a test-host attestation to precisely the facade's delete proposal.

    _proposal is consulted only to obtain the exact protected proposal identity
    for this test authority fixture. Production callers must not self-ratify.
    """
    proposal = memory._proposal(
        # #786: bind the canonical target the facade resolves (scope_distinct_v1 maps public keys)
        target_reference=memory._target(target),
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
    result = memory.forget(target, permanent=True, risk_class="high", attestation=attestation)
    if not result["committed"]:
        raise AssertionError(
            f"test setup did not achieve an authorized permanent deletion: {result!r}"
        )
    return result


def _correction_evidence():
    skill = pm.SkillArtifact(
        skill_id="skill:802-correction",
        version=1,
        purpose="correct retained test memory",
        scope=SCOPE,
        isolation_domain_refs=(TENANT, SCOPE),
        required_isolation_domain_refs=(TENANT, SCOPE),
        procedure_markdown="# verify\nConfirm the correction against the current source.",
        provenance_refs=("evidence:802-correction-source",),
    )
    return pm.evidence_for(skill)


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


class SemanticSidecarLifecycleTests(unittest.TestCase):
    """Adversarial lifecycle, authority, multi-sidecar and durability cases."""

    def test_canonical_commit_is_durable_and_sidecar_bytes_are_scrubbed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with _provider(), _open(root) as memory:
                deleted_ref, control_ref, cache_path = _seed_cached_facts(memory)
                self.assertEqual(_canonical_fact_refs(root), {deleted_ref, control_ref})
                result = _authorized_permanent_forget(memory)
                self.assertEqual(result["fact_uuid"], deleted_ref)
                # The canonical deletion is visible to an independent connection: the
                # sidecar cleanup ran strictly after a committed canonical generation.
                self.assertEqual(_canonical_fact_refs(root), {control_ref})
                self.assertEqual(_stored_fact_refs(cache_path), {control_ref})
                # secure_delete: the erased identifier is not left in freed sidecar pages.
                self.assertNotIn(deleted_ref.encode("utf-8"), Path(cache_path).read_bytes())
                self.assertIn(control_ref.encode("utf-8"), Path(cache_path).read_bytes())
                self.assertFalse(Path(cache_path + "-wal").exists())

    def test_forget_with_semantic_retrieval_off_still_scrubs_persistent_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with _provider(), _open(root) as memory:
                deleted_ref, control_ref, cache_path = _seed_cached_facts(memory)
            # No provider is importable here and the route is off: the sidecar is still
            # persistent state under this root and must follow the canonical deletion.
            with _open(root, semantic_retrieval="off") as memory:
                self.assertEqual(memory.semantic_retrieval_posture()["status"], "disabled")
                _authorized_permanent_forget(memory)
                self.assertEqual(_canonical_fact_refs(root), {control_ref})
                self.assertEqual(_stored_fact_refs(cache_path), {control_ref})

    def test_every_sidecar_identity_is_reconciled_including_inactive_ones(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with _provider(), _open(root) as memory:
                deleted_ref, control_ref, first_path = _seed_cached_facts(memory)
            with _provider(_RotatedRepresentation), _open(root) as memory:
                memory.recall("dog budget")
                second_path = memory.semantic_retrieval_posture()["store"]["path"]
                self.assertNotEqual(first_path, second_path)
                self.assertEqual(_stored_fact_refs(second_path), {deleted_ref, control_ref})
                self.assertEqual(_stored_fact_refs(first_path), {deleted_ref, control_ref})
                _authorized_permanent_forget(memory)
                # The active sidecar and the older configuration's sidecar both lose the row.
                self.assertEqual(_stored_fact_refs(second_path), {control_ref})
                self.assertEqual(_stored_fact_refs(first_path), {control_ref})
                self.assertEqual(_canonical_fact_refs(root), {control_ref})
            with _provider(), _open(root) as memory:
                self.assertNotIn(deleted_ref, memory.recall("dog")["candidates"])
                self.assertIn(control_ref, memory.recall("budget")["admitted"])

    def test_reversible_pruning_never_becomes_sidecar_erasure(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with _provider(), _open(root) as memory:
                pruned_ref, control_ref, cache_path = _seed_cached_facts(memory)
                pruned = memory.forget(TARGET, permanent=False)
                self.assertTrue(pruned["committed"], pruned)
                self.assertTrue(memory.history(TARGET)["history"]["tombstoned"])
                # Pruning is reversible: canonical content and its derived rows both stay.
                self.assertEqual(_canonical_fact_refs(root), {pruned_ref, control_ref})
                self.assertEqual(_stored_fact_refs(cache_path), {pruned_ref, control_ref})
                self.assertNotIn(pruned_ref, memory.recall("dog")["admitted"])
            # Recovery-time reconciliation must not treat a pruned fact as an orphan.
            with _provider(), _open(root):
                self.assertEqual(_stored_fact_refs(cache_path), {pruned_ref, control_ref})
            with _open(root, semantic_retrieval="off"):
                self.assertEqual(_stored_fact_refs(cache_path), {pruned_ref, control_ref})

    def test_corrected_lineage_sidecar_mirrors_canonical_retention(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with _provider(), _open(root) as memory:
                first_ref, control_ref, cache_path = _seed_cached_facts(memory)
                corrected = memory.correct(TARGET, "The dog is Waffles.", evidence=_correction_evidence())
                self.assertTrue(corrected["committed"], corrected)
                second_ref = str(corrected["fact_uuid"])
                self.assertNotEqual(first_ref, second_ref)
                memory.recall("dog")
                self.assertEqual(_stored_fact_refs(cache_path), {first_ref, second_ref, control_ref})
                self.assertEqual(_canonical_fact_refs(root), {first_ref, second_ref, control_ref})
                _authorized_permanent_forget(memory)
                canonical = _canonical_fact_refs(root)
                sidecar = _stored_fact_refs(cache_path)
                # Policy boundary: the sidecar retains exactly what canonical physically retains.
                # Whether the superseded version is erased with the head is decided by the
                # canonical deletion lineage (#776), never by the derived cache.
                self.assertNotIn(second_ref, canonical)
                self.assertNotIn(second_ref, sidecar)
                self.assertIn(control_ref, canonical)
                self.assertEqual(sidecar, canonical)
            with _provider(), _open(root) as memory:
                self.assertEqual(_stored_fact_refs(cache_path), _canonical_fact_refs(root))
                historical = memory.recall("dog", temporal_intent={"mode": "historical"})
                self.assertNotIn(second_ref, historical["candidates"])
                self.assertNotIn(second_ref, historical["admitted"])

    def test_sidecar_failure_after_canonical_commit_is_explicit_and_retried_on_reopen(self) -> None:
        real_connect = sqlite3.connect

        def failing_connect(database, *args, **kwargs):
            if isinstance(database, str) and database.startswith("file:"):
                raise sqlite3.OperationalError("disk I/O error")
            return real_connect(database, *args, **kwargs)

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with _provider(), _open(root) as memory:
                deleted_ref, control_ref, cache_path = _seed_cached_facts(memory)
                with mock.patch.object(representation_cache.sqlite3, "connect", failing_connect):
                    with self.assertRaises(DerivedCacheReconciliationError) as raised:
                        _authorized_permanent_forget(memory)
                # Partial success is explicit: canonical committed, residue remains, not full erasure.
                self.assertTrue(raised.exception.canonical_committed)
                self.assertEqual(raised.exception.fact_uuid, deleted_ref)
                report = raised.exception.report
                self.assertEqual(report["status"], "incomplete")
                self.assertIn("OperationalError: disk I/O error", report["failed"][0][1])
                self.assertEqual(report["pending"], [deleted_ref])
                # The canonical receipt is not lost to the caller.
                self.assertTrue(raised.exception.result["committed"])
                self.assertEqual(raised.exception.result["fact_uuid"], deleted_ref)
                self.assertIn("receipt", raised.exception.result)
                self.assertEqual(_canonical_fact_refs(root), {control_ref})
                self.assertEqual(_stored_fact_refs(cache_path), {deleted_ref, control_ref})
                self.assertIn(deleted_ref, memory.semantic_retrieval_posture()["derived_reconciliation"]["pending"])
                # The handle is still usable; the deletion is not re-authorized or repeated.
                self.assertEqual(memory.forget(TARGET, permanent=True)["refusal"], "fact_not_found")
                self.assertIn(control_ref, memory.recall("budget")["admitted"])
            # Deterministic restart reconciliation, with no provider and the route off.
            with _open(root, semantic_retrieval="off") as recovered:
                self.assertEqual(_stored_fact_refs(cache_path), {control_ref})
                self.assertEqual(
                    recovered.semantic_retrieval_posture()["derived_reconciliation"]["status"], "complete"
                )

    def test_crash_between_canonical_delete_and_sidecar_cleanup_reconciles_on_restart(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            memory = None
            with _provider():
                memory = _open(root)
                deleted_ref, control_ref, cache_path = _seed_cached_facts(memory)
                with mock.patch.object(
                    AgentMemory, "_reconcile_cached_representations",
                    side_effect=RuntimeError("simulated process loss"),
                ):
                    with self.assertRaises(DerivedCacheReconciliationError):
                        _authorized_permanent_forget(memory)
                # No clean close: the process is gone with the residue on disk.
                del memory
                self.assertEqual(_canonical_fact_refs(root), {control_ref})
                self.assertEqual(_stored_fact_refs(cache_path), {deleted_ref, control_ref})
                with _open(root) as recovered:
                    self.assertEqual(_stored_fact_refs(cache_path), {control_ref})
                    self.assertNotIn(deleted_ref, recovered.recall("dog")["candidates"])
                    self.assertIn(control_ref, recovered.recall("budget")["admitted"])

    def test_corrupt_or_stray_inactive_sidecars_do_not_block_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with _provider(), _open(root) as memory:
                deleted_ref, control_ref, cache_path = _seed_cached_facts(memory)
            derived = root / "derived"
            garbage = derived / ("vectors-" + "11" * 8 + ".sqlite")
            garbage.write_bytes(b"not a sqlite database " * 64)
            stale = DerivedVectorStore(root, "sha256:" + "22" * 32, 3)
            stale.vector_for(deleted_ref, "The dog is Biscuit.", _OfflineRepresentation().embed)
            stale._connection.execute("UPDATE meta SET value = 'sha256:' || ? WHERE key = 'config_digest'",
                                      ("99" * 32,))
            stale._connection.commit()
            stale.close()
            stray = derived / "vectors-not-a-digest.sqlite"
            stray.write_bytes(b"stray")
            # An unrelated derived file must never block the canonical runtime.
            with _provider(), _open(root) as recovered:
                self.assertIn(control_ref, recovered.recall("budget")["admitted"])
                report = recovered.semantic_retrieval_posture()["derived_reconciliation"]
                self.assertEqual(report["status"], "complete")
                self.assertEqual(report["foreign"], [])
                _authorized_permanent_forget(recovered)
                self.assertEqual(_stored_fact_refs(cache_path), {control_ref})
            # Unreadable or mis-identified stores of our own format are discarded: they are
            # rebuildable, never authority, and discarding them removes their residue.
            self.assertFalse(garbage.exists())
            self.assertFalse(stale.path.exists())
            # A stray file that is not a derived store of ours is left alone.
            self.assertEqual(stray.read_bytes(), b"stray")

    def test_another_versions_sidecar_is_kept_and_permanent_deletion_is_loud(self) -> None:
        """A readable store of another ``agent-memory-derived-vectors`` version (or any
        foreign format) under our name is never discarded or reconciled: recovery stays
        available and reports it, and an authorized permanent forget raises because
        residue in that file cannot be ruled out. Nothing in it changes."""
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with _provider(), _open(root) as memory:
                deleted_ref, control_ref, cache_path = _seed_cached_facts(memory)
            newer = DerivedVectorStore(root, "sha256:" + "22" * 32, 3)
            newer.vector_for(deleted_ref, "The dog is Biscuit.", _OfflineRepresentation().embed)
            newer._connection.execute("UPDATE meta SET value = 'agent-memory-derived-vectors/2.0.0' WHERE key = 'format'")
            newer._connection.commit()
            newer.close()
            before = newer.path.read_bytes()
            with _provider(), _open(root) as recovered:
                self.assertIn(control_ref, recovered.recall("budget")["admitted"])
                report = recovered.semantic_retrieval_posture()["derived_reconciliation"]
                self.assertEqual(report["status"], "incomplete")
                self.assertEqual(report["foreign"], [[str(newer.path),
                                 "store format 'agent-memory-derived-vectors/2.0.0' of another runtime version"]])
                with self.assertRaises(DerivedCacheReconciliationError) as caught:
                    _authorized_permanent_forget(recovered)
                self.assertTrue(caught.exception.canonical_committed)
                self.assertEqual(caught.exception.report["foreign"][0][0], str(newer.path))
                self.assertEqual(_canonical_fact_refs(root), {control_ref})
                self.assertEqual(_stored_fact_refs(cache_path), {control_ref})
            self.assertEqual(newer.path.read_bytes(), before)

    def test_symlinked_derived_directory_degrades_auto_and_refuses_required_before_external_io(self) -> None:
        """The active route constructs the store before recovery reconciliation. A linked
        ``derived`` directory is refused at construction, before any chmod, open or write
        in the external directory: ``auto`` keeps the canonical runtime on the lexical route
        and records why; ``required`` raises, as it does for a missing model."""
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as other:
            root, other_root = Path(folder), Path(other)
            with _provider(), _open(other_root) as external:
                _seed_cached_facts(external)
                external_path = Path(external.semantic_retrieval_posture()["store"]["path"])
            external_bytes = external_path.read_bytes()
            external_mode = os.stat(external_path).st_mode
            with _provider(), _open(root, semantic_retrieval="off") as memory:
                memory.remember(TARGET, "The dog is Biscuit.")
                control_ref = memory.remember(CONTROL, "The budget has been approved.")["fact_uuid"]
            (root / "derived").symlink_to(other_root / "derived", target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlinked derived vector cache directory"), _provider():
                _open(root, semantic_retrieval="required")
            with _provider(), _open(root, semantic_retrieval="auto") as degraded:
                posture = degraded.semantic_retrieval_posture()
                self.assertEqual(posture["status"], "disabled")
                self.assertIn("derived store refused", posture["reason"])
                self.assertIn("symlinked derived vector cache directory", posture["reason"])
                self.assertIn(control_ref, degraded.recall("budget")["admitted"])
                self.assertEqual(posture["derived_reconciliation"]["status"], "incomplete")
                self.assertEqual(posture["derived_reconciliation"]["unsafe"], [str(root / "derived")])
            self.assertEqual(external_path.read_bytes(), external_bytes)
            self.assertEqual(os.stat(external_path).st_mode, external_mode)
            self.assertEqual(sorted(p.name for p in (other_root / "derived").iterdir()), [external_path.name])

    def test_symlinked_sidecar_is_never_followed_and_deletion_reports_residue(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with _provider(), _open(root) as memory:
                deleted_ref, control_ref, cache_path = _seed_cached_facts(memory)
            outside = root / "outside.sqlite"
            outside.write_bytes(b"outside the derived store boundary")
            link = root / "derived" / ("vectors-" + "33" * 8 + ".sqlite")
            link.symlink_to(outside)
            with _provider(), _open(root) as recovered:
                report = recovered.semantic_retrieval_posture()["derived_reconciliation"]
                self.assertEqual(report["status"], "incomplete")
                self.assertEqual(report["unsafe"], [str(link)])
                with self.assertRaises(DerivedCacheReconciliationError) as raised:
                    _authorized_permanent_forget(recovered)
                self.assertTrue(raised.exception.canonical_committed)
                # The active sidecar was still scrubbed; only the unsafe entry is residue.
                self.assertEqual(_stored_fact_refs(cache_path), {control_ref})
                self.assertEqual(_canonical_fact_refs(root), {control_ref})
            self.assertTrue(link.is_symlink())
            self.assertEqual(outside.read_bytes(), b"outside the derived store boundary")

    @unittest.skipIf(os.geteuid() == 0, "file permissions are not enforced for root")
    def test_read_only_sidecar_reports_incomplete_cleanup_without_blocking_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with _provider(), _open(root) as memory:
                deleted_ref, control_ref, first_path = _seed_cached_facts(memory)
            os.chmod(first_path, 0o400)
            try:
                with _provider(_RotatedRepresentation), _open(root) as memory:
                    with self.assertRaises(DerivedCacheReconciliationError):
                        _authorized_permanent_forget(memory)
                    self.assertEqual(_canonical_fact_refs(root), {control_ref})
                with _open(root, semantic_retrieval="off") as recovered:
                    self.assertEqual(
                        recovered.semantic_retrieval_posture()["derived_reconciliation"]["status"],
                        "incomplete",
                    )
            finally:
                os.chmod(first_path, 0o600)
            with _open(root, semantic_retrieval="off"):
                self.assertEqual(_stored_fact_refs(first_path), {control_ref})

    def test_other_scope_and_other_root_vectors_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as other_folder:
            root, other_root = Path(folder), Path(other_folder)
            with _provider(), _open(other_root) as other:
                other_deleted, other_control, other_path = _seed_cached_facts(other)
            # #786: two projects share this root, so it is a scope_distinct_v1 store.
            with _provider(), _open(root, scope="project:unrelated", store_profile="scope_distinct_v1") as unrelated:
                kept = unrelated.remember("memory:unrelated-dog", "The dog next door barks.")
                unrelated.recall("dog")
                kept_ref = str(kept["fact_uuid"])
            with _provider(), _open(root, store_profile="scope_distinct_v1") as memory:
                deleted_ref, control_ref, cache_path = self._seed_with_extra(memory, kept_ref)
                _authorized_permanent_forget(memory)
                self.assertEqual(_stored_fact_refs(cache_path), {control_ref, kept_ref})
                self.assertEqual(_canonical_fact_refs(root), {control_ref, kept_ref})
            self.assertEqual(_stored_fact_refs(other_path), {other_deleted, other_control})
            self.assertEqual(_canonical_fact_refs(other_root), {other_deleted, other_control})

    def _seed_with_extra(self, memory: AgentMemory, extra_ref: str) -> tuple[str, str, str]:
        deleted = memory.remember(TARGET, "The dog is Biscuit.")
        retained = memory.remember(CONTROL, "The budget has been approved.")
        memory.recall("dog budget")
        cache_path = memory.semantic_retrieval_posture()["store"]["path"]
        self.assertEqual(
            _stored_fact_refs(cache_path), {deleted["fact_uuid"], retained["fact_uuid"], extra_ref}
        )
        return str(deleted["fact_uuid"]), str(retained["fact_uuid"]), cache_path


if __name__ == "__main__":
    unittest.main()
