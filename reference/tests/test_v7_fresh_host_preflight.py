"""Host-side v7 fresh-store enrollment controls, outside the protected runtime.

Security tests never claim an actual consuming application adopted the example.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from agentmem_ref import AgentMemory
from examples.v7_fresh_host import (
    ENROLLMENT_SCHEMA,
    HostAdmissionRefused,
    HostIdentity,
    _receipt_path,
    _state_identity,
    open_registered_root,
    provision_new_root,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "reference/fixtures/809-legacy-stores"


@unittest.skipUnless(os.name == "posix", "v7 host enrollment is POSIX-only until OS qualification")
class FreshV7HostBoundary(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.registry = self.base / "host-owned-registry"
        self.registry.mkdir(mode=0o700)
        self.state = self.base / "state"
        self.state.mkdir(mode=0o700)
        self.root = self.state / "root"
        self.identity = HostIdentity(
            tenant="tenant:host", actor_id="agent:host", scope="project:host"
        )

    def enroll(self):
        return provision_new_root(self.root, registry=self.registry, identity=self.identity)

    def open(self, identity=None):
        return open_registered_root(
            self.root, registry=self.registry, identity=identity or self.identity
        )

    def seed_untrusted_enrollment(self, identity):
        # Adversarial fixture: a misconfigured operator has written a marker for
        # an old store. The *live* status gate still must reject the store.
        device, inode = _state_identity(self.root)
        report = {
            "schema": ENROLLMENT_SCHEMA, "root": str(self.root),
            "device": device, "inode": inode,
            "tenant": identity.tenant, "scope": identity.scope,
        }
        _receipt_path(self.registry, self.root).write_text(
            json.dumps(report), encoding="utf-8"
        )

    def test_host_provisions_absent_root_and_reopens_after_write(self):
        receipt = self.enroll()
        self.assertTrue(receipt.is_file())
        self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)
        with self.open() as memory:
            report = memory.legacy_upgrade_status()
            self.assertEqual((report["status"], report["legacy_facts"], report["record"]),
                             ("fresh", 0, None))
            self.assertTrue(memory.remember("memory:host", "Known fresh memory")["committed"])
        with self.open() as memory:
            self.assertEqual(memory.legacy_upgrade_status()["status"], "fresh")
            self.assertTrue(memory.recall("Known fresh memory")["returned"])

    def test_existing_empty_root_is_not_enrollable_or_operational(self):
        self.root.mkdir(mode=0o700)
        with self.assertRaises(HostAdmissionRefused):
            self.enroll()
        with patch.object(AgentMemory, "open", side_effect=AssertionError("opened")) as raw:
            with self.assertRaises(HostAdmissionRefused):
                with self.open():
                    self.fail("unregistered existing root was served")
            raw.assert_not_called()

    def test_status_fresh_alone_does_not_register_an_existing_store(self):
        with AgentMemory.open(
            self.root, tenant=self.identity.tenant, actor_id=self.identity.actor_id,
            scope=self.identity.scope,
        ) as existing:
            self.assertEqual(existing.legacy_upgrade_status()["status"], "fresh")
        with self.assertRaises(HostAdmissionRefused):
            with self.open():
                self.fail("old-but-currently-fresh store was served without registration")

    def test_historical_pending_fixture_rejected_even_if_registry_was_misissued(self):
        self.root = self.state / "legacy"
        shutil.copytree(FIXTURES / "cross-scope", self.root)
        self.root.chmod(0o700)
        ident = HostIdentity(tenant="tenant:legacy", actor_id="agent:legacy", scope="project:b")
        self.seed_untrusted_enrollment(ident)
        with self.assertRaises(HostAdmissionRefused):
            with self.open(ident):
                self.fail("pending legacy store was handed to consumer")

    def test_explicitly_upgraded_legacy_store_is_still_excluded_from_v7(self):
        self.root = self.state / "legacy-upgraded"
        shutil.copytree(FIXTURES / "cross-scope", self.root)
        self.root.chmod(0o700)
        ident = HostIdentity(tenant="tenant:legacy", actor_id="agent:legacy", scope="project:b")
        with AgentMemory.open(
            self.root, tenant=ident.tenant, actor_id=ident.actor_id, scope=ident.scope
        ) as maintenance:
            report = maintenance.upgrade_canonical_derivation()
            self.assertEqual(report["status"], "legacy_qualified")
        self.seed_untrusted_enrollment(ident)
        with self.assertRaises(HostAdmissionRefused):
            with self.open(ident):
                self.fail("administratively migrated older store was admitted as new")

    def test_replaced_root_inode_refused_before_runtime_access(self):
        self.enroll()
        self.root.rename(self.state / "original")
        self.root.mkdir(mode=0o700)
        with patch.object(AgentMemory, "open", side_effect=AssertionError("opened")) as raw:
            with self.assertRaises(HostAdmissionRefused):
                with self.open():
                    self.fail("replacement root was accepted")
            raw.assert_not_called()

    def test_wrong_tenant_and_scope_refused_before_runtime_access(self):
        self.enroll()
        for bad in (
            HostIdentity(tenant="tenant:wrong", actor_id="agent:host", scope="project:host"),
            HostIdentity(tenant="tenant:host", actor_id="agent:host", scope="project:wrong"),
        ):
            with self.subTest(bad=bad):
                with patch.object(AgentMemory, "open", side_effect=AssertionError("opened")) as raw:
                    with self.assertRaises(HostAdmissionRefused):
                        with self.open(bad):
                            self.fail("foreign identity admitted")
                    raw.assert_not_called()

    def test_untrusted_registry_and_symlinked_root_refused(self):
        self.registry.chmod(0o755)
        with self.assertRaises(HostAdmissionRefused):
            self.enroll()
        self.registry.chmod(0o700)
        real = self.state / "other"
        real.mkdir(mode=0o700)
        self.root.symlink_to(real, target_is_directory=True)
        with self.assertRaises(HostAdmissionRefused):
            self.enroll()

    def test_blank_host_claims_rejected(self):
        with self.assertRaises(HostAdmissionRefused):
            HostIdentity(tenant=" ", actor_id="agent:good", scope="project:good")

    def test_posture_label_with_upgrade_record_is_refused_and_handle_closed(self):
        self.enroll()

        class Fake:
            closed = False

            def legacy_upgrade_status(self):
                return {"status": "fresh", "legacy_facts": 0, "record": {"from": "legacy"}}

            def close(self):
                self.closed = True

        fake = Fake()
        with patch.object(AgentMemory, "open", return_value=fake):
            with self.assertRaises(HostAdmissionRefused):
                with self.open():
                    self.fail("forged post-upgrade fresh record was admitted")
        self.assertTrue(fake.closed)

    def test_posture_inspection_exception_closes_handle(self):
        self.enroll()

        class Fake:
            closed = False

            def legacy_upgrade_status(self):
                raise OSError("unreadable lineage")

            def close(self):
                self.closed = True

        fake = Fake()
        with patch.object(AgentMemory, "open", return_value=fake):
            with self.assertRaisesRegex(OSError, "unreadable lineage"):
                with self.open():
                    self.fail("unverified posture reached user")
        self.assertTrue(fake.closed)

    def test_failed_initialization_never_writes_host_enrollment(self):
        with patch.object(AgentMemory, "open", side_effect=OSError("create failed")):
            with self.assertRaisesRegex(OSError, "create failed"):
                self.enroll()
        self.assertEqual(list(self.registry.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
