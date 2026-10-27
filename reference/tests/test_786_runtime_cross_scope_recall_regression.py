"""Real SQLite adversarial checks for a host-bound facade (#786)."""
import tempfile
import unittest
from pathlib import Path

from agentmem_ref import AgentMemory  # noqa: F401

from tests._tenant_wide_fixture import open_tenant_wide


class CrossScopeRuntimeRegression(unittest.TestCase):
    def test_caller_context_cannot_read_another_projects_fact(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            identity = {"tenant": "tenant:scope-test", "actor_id": "agent:scope-test"}
            with open_tenant_wide(root, scope="project:a", **identity) as owner:
                written = owner.remember("memory:private", "Orrin gateway is Oslo")
                self.assertTrue(written["committed"])
                ref = written["fact_uuid"]
            with open_tenant_wide(root, scope="project:b", **identity) as other:
                self.assertNotIn(ref, other.recall("Orrin gateway")["admitted"])
                try:
                    result = other.recall("Orrin gateway", project_ref="project:a",
                        target_domain_refs=("tenant:scope-test", "project:a"))
                except ValueError:
                    return
                self.assertNotIn(ref, result["admitted"])

    def test_history_hides_foreign_head_and_events(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            identity = {"tenant": "tenant:scope-test", "actor_id": "agent:scope-test"}
            with open_tenant_wide(root, scope="project:a", **identity) as owner:
                self.assertTrue(owner.remember("memory:private", "Orrin gateway is Oslo")["committed"])
            with open_tenant_wide(root, scope="project:b", **identity) as other:
                self.assertEqual(other.history("memory:private")["history"],
                                 other.history("memory:absent")["history"])
