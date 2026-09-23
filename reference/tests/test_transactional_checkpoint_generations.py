"""Issue #414: checkpoint generations are serialized, compare-and-commit, and replay resistant.

The transaction protocol deliberately wraps the existing
``reference_file_checkpoint_v1`` state shape. These tests exercise the durable
files and public restart wrapper rather than reaching into component-private
memory state.
"""

from __future__ import annotations

import json
import multiprocessing
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from agentmem_ref import policy
from agentmem_ref.restart_runtime import (
    CapabilityBinding,
    RestartSafeRuntime,
    RuntimeCheckpointConflict,
    RuntimeProfile,
    RuntimeRecoveryError,
    TRANSACTION_PROTOCOL,
)
import agentmem_ref.restart_runtime as restart_runtime


def _profile() -> RuntimeProfile:
    return RuntimeProfile(
        runtime_version="0.1.0-reference",
        profile_id="reference-project-memory",
        profile_version="1.0.0",
        bindings=(
            CapabilityBinding(
                component_id="reference-governed-memory",
                component_version="1.0.0",
                capability_id="governed-memory-core",
                capability_version="1.0.0",
                maturity="reference_qualified",
                evidence_ref="evidence:reference-runtime-core-v1",
            ),
        ),
    )


def _proposal(proposal_id: str, memory_id: str = "memory:checkpoint-race") -> policy.Proposal:
    return policy.Proposal(
        proposal_id=proposal_id,
        actor_id="agent:test",
        charter_version="charter-v1",
        target_reference=memory_id,
        target_class=policy.M1,
        scope="tenant-acme",
        operation="runtime_assembly",
        current_strength="observed",
        proposed_strength="tentative",
        downstream_authority=policy.A1,
        reversibility="reversible",
        risk_class="low",
        evidence_refs=(f"evidence:{proposal_id}",),
        tenant_ref="tenant-acme",
        isolation_domain_refs=("tenant-acme",),
    )


def _race_writer(root: str, name: str, ready, start, output) -> None:
    """Process entry point: observe one generation, then race another writer."""
    try:
        runtime = RestartSafeRuntime.recover(Path(root), profile=_profile())
        runtime.visibility_snapshots[name] = {"writer": name}
        ready.put(name)
        start.wait(10)
        evidence = runtime.checkpoint()
        output.put((name, "committed", evidence.generation))
    except RuntimeCheckpointConflict as exc:
        output.put((name, "conflict", str(exc)))
    except Exception as exc:  # pragma: no cover - emitted to make race failures diagnosable.
        output.put((name, "unexpected", repr(exc)))


class TransactionalCheckpointGenerationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.profile = _profile()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_same_runtime_advances_generation_monotonically(self) -> None:
        runtime = RestartSafeRuntime.create(
            self.root, tenant="tenant-acme", profile=self.profile
        )
        self.assertEqual(runtime.recovery_evidence.generation, 1)
        second = runtime.checkpoint()
        third = runtime.checkpoint()
        self.assertEqual((second.generation, third.generation), (2, 3))

        journal = (self.root / "runtime-generation-journal.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        self.assertEqual(len(journal), 3)
        self.assertEqual([json.loads(row)["generation"] for row in journal], [1, 2, 3])

    def test_two_recovered_writers_cannot_publish_the_same_next_generation(self) -> None:
        RestartSafeRuntime.create(self.root, tenant="tenant-acme", profile=self.profile)
        writer_a = RestartSafeRuntime.recover(self.root, profile=self.profile)
        writer_b = RestartSafeRuntime.recover(self.root, profile=self.profile)
        writer_a.visibility_snapshots["writer-a"] = {"writer": "a"}
        writer_b.visibility_snapshots["writer-b"] = {"writer": "b"}

        committed = writer_a.checkpoint()
        self.assertEqual(committed.generation, 2)
        with self.assertRaisesRegex(RuntimeCheckpointConflict, "observed 1, current 2"):
            writer_b.checkpoint()

        recovered = RestartSafeRuntime.recover(self.root, profile=self.profile)
        self.assertIn("writer-a", recovered.visibility_snapshots)
        self.assertNotIn("writer-b", recovered.visibility_snapshots)
        self.assertEqual(recovered.recovery_evidence.generation, 2)

    @unittest.skipIf(restart_runtime.fcntl is None, "POSIX file locking is required")
    def test_two_processes_racing_from_one_generation_yield_one_commit_one_conflict(self) -> None:
        RestartSafeRuntime.create(self.root, tenant="tenant-acme", profile=self.profile)
        context = multiprocessing.get_context("fork")
        ready = context.Queue()
        start = context.Event()
        output = context.Queue()
        processes = [
            context.Process(
                target=_race_writer,
                args=(str(self.root), name, ready, start, output),
            )
            for name in ("process-a", "process-b")
        ]
        for process in processes:
            process.start()
        self.assertEqual({ready.get(timeout=10), ready.get(timeout=10)}, {"process-a", "process-b"})
        start.set()
        results = [output.get(timeout=15), output.get(timeout=15)]
        for process in processes:
            process.join(timeout=15)
            self.assertEqual(process.exitcode, 0)

        outcomes = sorted(result[1] for result in results)
        self.assertEqual(outcomes, ["committed", "conflict"])
        recovered = RestartSafeRuntime.recover(self.root, profile=self.profile)
        self.assertEqual(recovered.recovery_evidence.generation, 2)
        committed_names = [name for name, outcome, _ in results if outcome == "committed"]
        self.assertEqual(len(committed_names), 1)
        self.assertIn(committed_names[0], recovered.visibility_snapshots)

    def test_fresh_store_cannot_write_over_existing_state_without_observing_it(self) -> None:
        runtime = RestartSafeRuntime.create(
            self.root, tenant="tenant-acme", profile=self.profile
        )
        fresh = restart_runtime.JsonRuntimeStateStore(self.root)
        with self.assertRaisesRegex(RuntimeCheckpointConflict, "recover before writing"):
            fresh.checkpoint(
                runtime.adapter,
                profile=self.profile,
                visibility_snapshots={},
            )

    def test_payload_write_crash_never_recovers_a_mixed_generation(self) -> None:
        runtime = RestartSafeRuntime.create(
            self.root, tenant="tenant-acme", profile=self.profile
        )
        committed = runtime.adapter.commit_proposal(
            _proposal("proposal-new-value"), "new durable value"
        )
        self.assertTrue(committed.committed)

        real_write = restart_runtime._atomic_json_write

        def fail_before_governance(path, value):
            if path.name == "governance.json":
                raise OSError("simulated crash between component writes")
            return real_write(path, value)

        with mock.patch(
            "agentmem_ref.restart_runtime._atomic_json_write",
            side_effect=fail_before_governance,
        ):
            with self.assertRaisesRegex(OSError, "simulated crash"):
                runtime.checkpoint()

        with self.assertRaisesRegex(
            RuntimeRecoveryError, "substrate checkpoint digest mismatch"
        ):
            RestartSafeRuntime.recover(self.root, profile=self.profile)

    def test_manifest_without_matching_commit_journal_fails_closed(self) -> None:
        runtime = RestartSafeRuntime.create(
            self.root, tenant="tenant-acme", profile=self.profile
        )
        runtime.visibility_snapshots["uncommitted-journal"] = {"state": "new"}
        real_append = restart_runtime._append_json_line

        def fail_new_generation(path, value):
            if value.get("generation") == 2:
                raise OSError("simulated crash before commit journal append")
            return real_append(path, value)

        with mock.patch(
            "agentmem_ref.restart_runtime._append_json_line",
            side_effect=fail_new_generation,
        ):
            with self.assertRaisesRegex(OSError, "simulated crash"):
                runtime.checkpoint()

        with self.assertRaisesRegex(RuntimeRecoveryError, "journal mismatch"):
            RestartSafeRuntime.recover(self.root, profile=self.profile)

    def test_replaying_older_payloads_and_manifest_is_detected_by_journal_head(self) -> None:
        runtime = RestartSafeRuntime.create(
            self.root, tenant="tenant-acme", profile=self.profile
        )
        old = {
            name: (self.root / name).read_bytes()
            for name in ("substrate.json", "governance.json", "runtime-manifest.json")
        }
        runtime.visibility_snapshots["new-generation"] = {"state": "new"}
        runtime.checkpoint()

        for name, payload in old.items():
            (self.root / name).write_bytes(payload)

        with self.assertRaisesRegex(RuntimeRecoveryError, "rollback or torn commit"):
            RestartSafeRuntime.recover(self.root, profile=self.profile)

    def test_missing_journal_for_transactional_manifest_fails_closed(self) -> None:
        RestartSafeRuntime.create(self.root, tenant="tenant-acme", profile=self.profile)
        (self.root / "runtime-generation-journal.jsonl").unlink()
        with self.assertRaisesRegex(RuntimeRecoveryError, "missing its generation journal"):
            RestartSafeRuntime.recover(self.root, profile=self.profile)

    def test_journal_digest_tampering_fails_closed(self) -> None:
        RestartSafeRuntime.create(self.root, tenant="tenant-acme", profile=self.profile)
        path = self.root / "runtime-generation-journal.jsonl"
        records = [json.loads(row) for row in path.read_text(encoding="utf-8").splitlines()]
        records[-1]["record_digest"] = "sha256:" + "0" * 64
        path.write_text("\n".join(json.dumps(row) for row in records) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeRecoveryError, "digest mismatch"):
            RestartSafeRuntime.recover(self.root, profile=self.profile)

    def test_pre_transaction_v1_checkpoint_recovers_and_is_baselined_on_next_commit(self) -> None:
        runtime = RestartSafeRuntime.create(
            self.root, tenant="tenant-acme", profile=self.profile
        )
        journal = self.root / "runtime-generation-journal.jsonl"
        journal.unlink()
        manifest_path = self.root / "runtime-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest.pop("transaction_protocol")
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        recovered = RestartSafeRuntime.recover(self.root, profile=self.profile)
        self.assertEqual(recovered.recovery_evidence.generation, 1)
        second = recovered.checkpoint()
        self.assertEqual(second.generation, 2)

        records = [
            json.loads(row)
            for row in journal.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual([row["generation"] for row in records], [1, 2])
        current = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(current["transaction_protocol"], TRANSACTION_PROTOCOL)


if __name__ == "__main__":
    unittest.main()
