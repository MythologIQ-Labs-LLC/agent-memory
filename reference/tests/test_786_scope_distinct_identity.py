"""#786 scoped identity candidate contract; full SQLite replay still required."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from agentmem_ref.api.scoped_identity import ScopeDistinctMemory, scope_distinct_key

class FakeMemory:
    def __init__(self, tenant, scope, actor, store):
        self.tenant, self.scope, self.actor_id = tenant, scope, actor
        self.store, self.calls, self.closed = store, [], False
    def remember(self, key, text):
        self.calls.append(("remember", key))
        self.store[key] = text
        return {"committed": True, "fact_uuid": "fact:" + hashlib.sha256(key.encode()).hexdigest()[:16], "outcome": "allow_with_ledger"}
    def history(self, key):
        self.calls.append(("history", key))
        return {"history": {"current_fact_uuid": ("fact:" + hashlib.sha256(key.encode()).hexdigest()[:16]) if key in self.store else None,
                "state_version": 1 if key in self.store else 0, "tombstoned": False,
                "events": [{"private": "forbidden"}]}}
    def correct(self, key, text, **kw):
        self.calls.append(("correct", key))
        return {"committed": False, "outcome": "require_review", "refusal": key}
    def forget(self, key, **kw):
        self.calls.append(("forget", key))
        return {"committed": False, "outcome": "require_review", "refusal": key}
    def close(self): self.closed = True

def scoped(scope, store, tenant="tenant:one", actor="agent:one"):
    fake = FakeMemory(tenant, scope, actor, store)
    return ScopeDistinctMemory(fake, tenant=tenant, scope=scope, actor_id=actor)

class ScopedIdentityTests(unittest.TestCase):
    def test_open_uses_dedicated_child_not_existing_legacy_root(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            (parent / "legacy-state.db").write_text("legacy state", encoding="utf-8")
            fake = FakeMemory("tenant:one", "project:a", "agent:one", {})
            with patch("agentmem_ref.api.scoped_identity.AgentMemory.open",
                       return_value=fake) as underlying:
                with ScopeDistinctMemory.open(
                    parent, tenant="tenant:one", scope="project:a",
                    actor_id="agent:one",
                ) as memory:
                    self.assertTrue(memory.remember("memory:key", "Oslo")["committed"])
                self.assertEqual(
                    underlying.call_args.args[0],
                    parent / ".agent-memory-scoped-v1",
                )
            self.assertEqual(
                (parent / "legacy-state.db").read_text(encoding="utf-8"),
                "legacy state",
            )
            self.assertTrue(fake.closed)

    def test_reopen_uses_same_durable_child_path_across_scopes(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            paths = []
            for scope in ("project:a", "project:b", "project:a"):
                fake = FakeMemory("tenant:one", scope, "agent:one", {})
                with patch("agentmem_ref.api.scoped_identity.AgentMemory.open",
                           return_value=fake) as underlying:
                    with ScopeDistinctMemory.open(
                        parent, tenant="tenant:one", scope=scope,
                        actor_id="agent:one",
                    ):
                        pass
                    paths.append(underlying.call_args.args[0])
            self.assertEqual(
                paths, [parent / ".agent-memory-scoped-v1"] * 3,
            )

    def test_symlinked_scoped_child_refused_before_runtime_open(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            legacy = parent / "legacy"
            legacy.mkdir()
            link = parent / ".agent-memory-scoped-v1"
            try:
                link.symlink_to(legacy, target_is_directory=True)
            except (OSError, NotImplementedError) as error:
                self.skipTest(f"symlink capability unavailable: {error}")
            with patch("agentmem_ref.api.scoped_identity.AgentMemory.open") as opener:
                with self.assertRaisesRegex(ValueError, "symlink"):
                    ScopeDistinctMemory.open(
                        parent, tenant="tenant:one", scope="project:a",
                        actor_id="agent:one",
                    )
                opener.assert_not_called()
            self.assertEqual(list(legacy.iterdir()), [])

    def test_symlinked_ancestor_refused_before_runtime_open(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            real = parent / "real"
            real.mkdir()
            alias = parent / "alias"
            try:
                alias.symlink_to(real, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlinks unavailable: {exc}")
            with patch("agentmem_ref.api.scoped_identity.AgentMemory.open") as opener:
                with self.assertRaisesRegex(ValueError, "symlink"):
                    ScopeDistinctMemory.open(alias, tenant="tenant:one", actor_id="agent:one", scope="project:a")
                opener.assert_not_called()

    def test_relative_and_traversal_roots_refused_before_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            candidates = [Path("relative-host-root"), Path(directory) / "missing" / ".." / "other"]
            with patch("agentmem_ref.api.scoped_identity.AgentMemory.open") as opener:
                for root in candidates:
                    with self.subTest(root=root), self.assertRaises(ValueError):
                        ScopeDistinctMemory.open(root, tenant="tenant:one", actor_id="agent:one", scope="project:a")
                opener.assert_not_called()

    def test_existing_non_directory_child_refused_before_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            (parent / ".agent-memory-scoped-v1").write_text("unrelated store", encoding="utf-8")
            with patch("agentmem_ref.api.scoped_identity.AgentMemory.open") as opener:
                with self.assertRaisesRegex(ValueError, "must be a directory"):
                    ScopeDistinctMemory.open(parent, tenant="tenant:one", actor_id="agent:one", scope="project:a")
                opener.assert_not_called()
            self.assertEqual((parent / ".agent-memory-scoped-v1").read_text(), "unrelated store")

    def test_invalid_host_identity_refused_before_store_open(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("agentmem_ref.api.scoped_identity.AgentMemory.open") as opener:
                with self.assertRaisesRegex(ValueError, "NFC"):
                    ScopeDistinctMemory.open(Path(directory), tenant="tenant:one", actor_id="agent:one", scope="project:e\u0301")
                opener.assert_not_called()

    def test_invalid_actor_rejected_before_runtime_or_implicit_store_init(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("agentmem_ref.api.scoped_identity.AgentMemory.open") as opener:
                for actor in ("", " ", "agent:e\u0301", None):
                    with self.subTest(actor=actor), self.assertRaisesRegex(ValueError, "actor_id"):
                        ScopeDistinctMemory.open(Path(directory), tenant="tenant:one", scope="project:a", actor_id=actor)
                opener.assert_not_called()
            self.assertFalse((Path(directory) / ".agent-memory-scoped-v1").exists())

    def test_direct_facade_constructor_rejects_noncanonical_actor(self):
        fake = FakeMemory("tenant:one", "project:a", "actor: ", {})
        with self.assertRaisesRegex(ValueError, "actor_id"):
            ScopeDistinctMemory(fake, tenant="tenant:one", scope="project:a", actor_id="actor: ")
        self.assertEqual(fake.calls, [])

    def test_two_projects_same_public_key_create_separate_heads(self):
        store = {}
        a, b = scoped("project:a", store), scoped("project:b", store)
        first = a.remember("memory:key", "Oslo")
        second = b.remember("memory:key", "Turku")
        self.assertTrue(first["committed"])
        self.assertTrue(second["committed"])
        self.assertEqual(len(store), 2)
        self.assertNotEqual(first["fact_ref"], second["fact_ref"])
        self.assertNotEqual(a.history("memory:key")["current_fact_ref"],
                            b.history("memory:key")["current_fact_ref"])

    def test_stable_tuple_identity_separates_scope_tenant_and_delimiters(self):
        f = scope_distinct_key
        self.assertEqual(f("a", "b", "c"), f("a", "b", "c"))
        self.assertNotEqual(f("a", "b", "c"), f("a", "c", "b"))
        self.assertNotEqual(f("a:b", "c", "d"), f("a", "b:c", "d"))

    def test_noncanonical_unicode_identity_is_refused(self):
        f = scope_distinct_key
        with self.assertRaisesRegex(ValueError, "NFC"):
            f("tenant:one", "project:a", "memory:e\u0301")
        with self.assertRaisesRegex(ValueError, "NFC"):
            f("tenant:e\u0301", "project:a", "memory:key")
        self.assertTrue(f("tenant:one", "project:a", "memory:é"))

    def test_internal_and_invalid_keys_refused_before_runtime(self):
        api = scoped("project:a", {})
        for key in ("", " ", "scope-key-v1:forged", "a" * 513, None):
            with self.subTest(key=key), self.assertRaises(ValueError):
                api.remember(key, "no write")
        self.assertEqual(api._memory.calls, [])

    def test_bad_host_binding_refused_before_mutation(self):
        fake = FakeMemory("tenant:one", "project:a", "agent:one", {})
        with self.assertRaisesRegex(ValueError, "trusted host binding"):
            ScopeDistinctMemory(fake, tenant="tenant:one", scope="project:b", actor_id="agent:one")
        self.assertEqual(fake.calls, [])

    def test_changed_host_identity_and_close_fail_closed(self):
        api = scoped("project:a", {})
        api._memory.actor_id = "agent:foreign"
        with self.assertRaises(RuntimeError):
            api.remember("memory:key", "no write")
        api._memory.actor_id = "agent:one"
        api.close()
        with self.assertRaises(RuntimeError):
            api.remember("memory:key", "no write")

    def test_history_projection_hides_internal_audit_details(self):
        api = scoped("project:a", {})
        api.remember("memory:key", "Oslo")
        shown = api.history("memory:key")
        self.assertEqual(shown["public_key"], "memory:key")
        self.assertNotIn("forbidden", repr(shown))
        self.assertNotIn("scope-key-v1:", repr(shown))

    def test_governed_correction_and_forget_preserve_same_identity(self):
        api = scoped("project:a", {})
        api.remember("memory:key", "Oslo")
        self.assertTrue(api.correct("memory:key", "Berlin")["review_required"])
        self.assertTrue(api.forget("memory:key")["review_required"])
        self.assertEqual(len({entry[1] for entry in api._memory.calls}), 1)

if __name__ == "__main__": unittest.main()
