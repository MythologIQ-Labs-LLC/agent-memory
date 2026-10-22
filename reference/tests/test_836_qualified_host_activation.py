"""Security acceptance controls for the host-side legacy activation gate (#809).

Do not alter the existing frozen migration fixtures or historical oracle proof.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.host_activation import (  # noqa: E402
    UnqualifiedLegacyStoreError, open_qualified_memory,
)

LEGACY = ROOT / "reference/fixtures/809-legacy-stores"
IDENTITY = dict(tenant="tenant:legacy", actor_id="agent:legacy",
                scope="project:b", purpose="legacy-test")


class QualifiedHostActivation(unittest.TestCase):
    def _copy(self, directory: str, store: str) -> Path:
        target = Path(directory) / "store"
        shutil.copytree(LEGACY / store, target)
        return target

    def test_fresh_store_is_operational(self):
        with tempfile.TemporaryDirectory() as directory:
            with open_qualified_memory(Path(directory) / "new", **IDENTITY) as memory:
                self.assertEqual(memory.legacy_upgrade_status()["status"], "fresh")
                self.assertTrue(memory.remember("memory:first", "ready")["committed"])

    def test_legacy_pending_store_never_reaches_consumer(self):
        with tempfile.TemporaryDirectory() as directory:
            target = self._copy(directory, "cross-scope")
            with patch.object(AgentMemory, "recall", side_effect=AssertionError("unsafe read")):
                with self.assertRaises(UnqualifiedLegacyStoreError):
                    with open_qualified_memory(target, **IDENTITY):
                        self.fail("host exposed a legacy_pending store")

    def test_explicitly_qualified_migration_can_activate(self):
        with tempfile.TemporaryDirectory() as directory:
            target = self._copy(directory, "cross-scope")
            with AgentMemory.open(target, **IDENTITY) as maintenance:
                report = maintenance.upgrade_canonical_derivation()
                self.assertEqual(report["status"], "legacy_qualified")
            with open_qualified_memory(target, **IDENTITY) as memory:
                self.assertEqual(memory.legacy_upgrade_status()["status"], "legacy_qualified")
                self.assertIsInstance(memory.recall("Quillon ferry berth"), dict)

    def test_unknown_status_fails_closed_and_closes_handle(self):
        class UnknownStatus:
            closed = False

            def legacy_upgrade_status(self):
                return {"status": "future_or_corrupt"}

            def close(self):
                self.closed = True

        handle = UnknownStatus()
        with patch.object(AgentMemory, "open", return_value=handle):
            with self.assertRaises(UnqualifiedLegacyStoreError):
                with open_qualified_memory("ignored", **IDENTITY):
                    self.fail("unknown status reached consumer")
        self.assertTrue(handle.closed)

    def test_status_inspection_failure_does_not_leak_handle(self):
        class FailingStatus:
            closed = False

            def legacy_upgrade_status(self):
                raise RuntimeError("status read refused")

            def close(self):
                self.closed = True

        handle = FailingStatus()
        with patch.object(AgentMemory, "open", return_value=handle):
            with self.assertRaisesRegex(RuntimeError, "status read refused"):
                with open_qualified_memory("ignored", **IDENTITY):
                    self.fail("unverified status reached consumer")
        self.assertTrue(handle.closed)

    def test_missing_host_identity_never_opens_runtime(self):
        # The package helper must not silently inherit the facade's local
        # tenant/actor/scope defaults for an operational consumer.
        with patch.object(AgentMemory, "open", side_effect=AssertionError("opened")) as raw_open:
            with self.assertRaises(TypeError):
                with open_qualified_memory("ignored"):
                    self.fail("missing identity accepted")
            raw_open.assert_not_called()

    def test_blank_host_identity_never_opens_runtime(self):
        with patch.object(AgentMemory, "open", side_effect=AssertionError("opened")) as raw_open:
            with self.assertRaises(ValueError):
                with open_qualified_memory("ignored", tenant="  ", actor_id="agent:x",
                                           scope="project:x"):
                    self.fail("blank identity accepted")
            raw_open.assert_not_called()

    def test_quarantined_upgrade_remains_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            target = self._copy(directory, "shared-membership")
            identity = {**IDENTITY, "scope": "shared:x", "actor_id": "agent:o"}
            with AgentMemory.open(target, **identity) as maintenance:
                report = maintenance.upgrade_canonical_derivation()
                self.assertEqual(report["status"], "legacy_unqualified")
            with self.assertRaises(UnqualifiedLegacyStoreError):
                with open_qualified_memory(target, **identity):
                    self.fail("host exposed a legacy_unqualified store")


if __name__ == "__main__":
    unittest.main()
