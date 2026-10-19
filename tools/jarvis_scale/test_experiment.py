"""Focused, fully offline test suite for #825 synthetic development harness."""
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

from experiment import AgentMemoryArm, IndexedArm, ScanArm, digest, evaluate, run, workload


class WorkloadTests(unittest.TestCase):
    def test_identical_seed_is_identical_and_different_seed_differs(self):
        first = workload(700, 825)
        same = workload(700, 825)
        other = workload(700, 826)
        self.assertEqual(digest(*first), digest(*same))
        self.assertNotEqual(digest(*first), digest(*other))
        self.assertEqual(len(first[0]), 714)
        self.assertEqual(len(first[1]), 14)
        self.assertEqual(len({r.id for r in first[0]}), len(first[0]))
        self.assertTrue(all(set(c.required) <= {r.id for r in first[0]} for c in first[1]))

    def test_no_private_data_and_known_isolation(self):
        records, cases = workload(80)
        target = next(c for c in cases if c.family == 'scope_isolation')
        self.assertIn('fact:foreign-editor', target.prohibited)
        self.assertNotIn('user:guest', {r.scope for r in records if r.id == 'fact:editor'})
        self.assertEqual({r.trust for r in records if r.id == 'episode:injected'}, {'untrusted'})

    def test_indexed_scope_is_not_bypassed(self):
        records, _ = workload(0)
        for arm in (ScanArm(records), IndexedArm(records)):
            try:
                result = arm.recall('Mira prefers Vim for writing Python', 'user:owner', 5)
                self.assertNotIn('fact:foreign-editor', result)
                self.assertEqual(arm.recall('Mira prefers Vim for writing Python', 'user:guest', 5), ['fact:foreign-editor'])
            finally:
                arm.close()

    def test_empty_and_hostile_queries_cannot_inject_sql(self):
        arm = IndexedArm(workload(10)[0])
        try:
            self.assertEqual(arm.recall('!', 'user:owner', 5), [])
            self.assertEqual(arm.recall('" OR DROP TABLE memories; --', 'user:owner', 0), [])
            self.assertIsInstance(arm.recall('editor', 'user:owner', 3), list)
        finally:
            arm.close()

    def test_invalid_configuration(self):
        with self.assertRaises(ValueError):
            workload(-1)
        with self.assertRaises(ValueError):
            run(10, budget=0)
        with self.assertRaises(ValueError):
            run(10, arms=('unknown',))

    def test_both_baselines_report_separate_quality_and_cost(self):
        result = run(200, repeats=2)
        self.assertEqual(result['evidence_class'], 'synthetic_development_only')
        self.assertFalse(result['external_jarvis_data'])
        self.assertEqual(len(result['results']), 2)
        for arm in result['results']:
            self.assertEqual(arm['cases_total'], 14)
            self.assertEqual(arm['primary_cases'], 13)
            self.assertGreaterEqual(arm['primary_extras'], 0)
            self.assertIn('scope_isolation', arm['by_family'])
            self.assertIn('temporal_diagnostic', arm['by_family'])
            self.assertGreaterEqual(arm['ingest_ms'], 0)
            self.assertGreaterEqual(arm['latency_ms']['p95'], arm['latency_ms']['p50'])
        self.assertEqual(result['corpus_sha256'], run(200, repeats=1, arms=('indexed',))['corpus_sha256'])


class FakeHandle:
    def __init__(self, store, scope):
        self.store = store
        self.scope = scope

    def remember(self, key, text):
        self.store[key] = (text, self.scope)
        return {'committed': True, 'fact_uuid': key + ':uuid'}

    def recall(self, query, budget):
        ids = [key + ':uuid' for key, (text, scope) in self.store.items() if scope == self.scope and query.lower() in text.lower()]
        return {'returned': ids[:budget]}

    def close(self):
        pass


class FacadeWiringTests(unittest.TestCase):
    def test_facade_id_mapping_and_scope_without_claiming_quality(self):
        state = {}
        class FakeAgentMemory:
            @staticmethod
            def open(root, tenant, actor_id, scope, purpose):
                return FakeHandle(state, scope)
        existing = sys.modules.get('agentmem_ref')
        sys.modules['agentmem_ref'] = types.SimpleNamespace(AgentMemory=FakeAgentMemory)
        try:
            records, _ = workload(0)
            with tempfile.TemporaryDirectory() as folder:
                arm = AgentMemoryArm(records, Path(folder))
                try:
                    self.assertEqual(arm.recall('Vim', 'user:owner', 3), [])
                    self.assertIn('fact:foreign-editor', arm.recall('Vim', 'user:guest', 3))
                finally:
                    arm.close()
        finally:
            if existing is None:
                del sys.modules['agentmem_ref']
            else:
                sys.modules['agentmem_ref'] = existing


if __name__ == '__main__':
    unittest.main()
