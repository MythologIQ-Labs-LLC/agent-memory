"""#786 scoped identity candidate contract; full SQLite replay still required."""
import hashlib
import unittest
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
