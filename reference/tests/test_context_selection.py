"""Public consumer-profile tests. No benchmark fixtures or gold enter runtime."""
import json
import tempfile
import unittest
from unittest.mock import patch
from agentmem_ref import AgentMemory
from agentmem_ref.core import receipts
from agentmem_ref.api import context_package as cp


class ContextSelectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.memory = AgentMemory.open(self.tmp.name, tenant='tenant:select', actor_id='agent:select',
                                       scope='project:select', purpose='task evidence')

    def tearDown(self):
        self.memory.close()
        self.tmp.cleanup()

    def put(self, key, text):
        r = self.memory.remember(key, text)
        self.assertTrue(r['committed'])
        return r['fact_uuid']

    def selected(self, query, **kw):
        return self.memory.recall_context(query, consumer_profile='lexical_content', **kw)

    def test_selective_content_preserves_raw_recall_and_default_package(self):
        camera = self.put('m:camera', 'The streaming camera uses a wide angle lens.')
        printer = self.put('m:printer', 'The printer uses recycled paper.')
        query = 'What is the streaming camera?'
        before = self.memory.recall(query)
        default = self.memory.recall_context(query)
        selected = self.selected(query)
        after = self.memory.recall(query)
        self.assertEqual(before['returned'], after['returned'])
        self.assertEqual(before['admitted'], after['admitted'])
        self.assertEqual(before['candidates'], after['candidates'])
        self.assertEqual(default['recall']['returned'], selected['recall']['returned'])
        self.assertEqual(default['recall']['return_policy'], selected['recall']['return_policy'])
        self.assertEqual([i['fact_ref'] for i in selected['items']], [camera])
        self.assertIn(printer, selected['selection']['omitted_refs'])
        self.assertNotIn('recycled paper', json.dumps(selected))
        self.assertNotIn('selection', default)
        self.assertEqual(default['package_version'], 'agent-memory-context/0.1.0')
        self.assertEqual(selected['package_version'], 'agent-memory-context/0.2.0')
        receipts.validate(cp.PACKAGE_SCHEMA, selected)

    def test_no_content_overlap_abstains_without_claiming_no_fact_exists(self):
        self.put('m:printer', 'The printer uses recycled paper.')
        r = self.selected('What is the telescope?')
        self.assertEqual(r['status'], 'empty')
        self.assertEqual(r['items'], [])
        self.assertTrue(r['recall']['returned'])
        self.assertEqual(r['selection']['authority_effect'], 'none')
        self.assertEqual(r['selection']['omitted_count'], 1)

    def test_exact_identity_route_survives_no_lexical_overlap(self):
        ref = self.put('m:camera', 'The streaming camera uses a wide angle lens.')
        r = self.selected('telescope', logical_memory_refs=('m:camera',))
        self.assertEqual([i['fact_ref'] for i in r['items']], [ref])
        self.assertEqual(r['selection']['omitted_count'], 0)

    def test_excluded_items_do_not_consume_content_budget(self):
        self.put('m:printer', 'The printer uses recycled paper.')
        self.put('m:camera', 'The streaming camera uses a wide angle lens.')
        r = self.selected('What is the streaming camera?', max_total_chars=200)
        self.assertEqual(r['budget']['used_chars'], len(r['items'][0]['content']))
        self.assertEqual(r['status'], 'complete')

    def test_invalid_profile_fails_before_recall(self):
        with patch.object(self.memory, '_recall_document_and_context') as recall:
            with self.assertRaises(ValueError):
                self.memory.recall_context('camera', consumer_profile='typo')
            recall.assert_not_called()

    def test_selected_context_never_exposes_foreign_scope(self):
        self.put('m:local', 'The camera is silver.')
        self.memory.close()
        with AgentMemory.open(self.tmp.name, tenant='tenant:select', actor_id='agent:select',
                              scope='project:foreign', purpose='task evidence') as foreign:
            hidden = foreign.remember('m:hidden', 'The camera secret is NEVERDISCLOSE')['fact_uuid']
        self.memory = AgentMemory.open(self.tmp.name, tenant='tenant:select', actor_id='agent:select',
                                       scope='project:select', purpose='task evidence')
        r = self.selected('What is the camera?')
        self.assertNotIn(hidden, json.dumps(r))
        self.assertNotIn('NEVERDISCLOSE', json.dumps(r))

    def test_default_profile_is_byte_equivalent_to_implicit_default(self):
        self.put('m:local', 'The camera is silver.')
        a = self.memory.recall_context('camera')
        b = self.memory.recall_context('camera', consumer_profile='all_returned')
        for package in (a, b):
            for item in package['items']:
                item.get('provenance', {}).pop('admission_decision_id', None)
        self.assertEqual(a, b)

    def test_negation_is_content_evidence(self):
        ref = self.put('m:negative', 'Do not ship without review.')
        r = self.selected('not')
        self.assertIn(ref, [i['fact_ref'] for i in r['items']])

    def test_profile_survives_reopen_without_persistent_configuration(self):
        ref = self.put('m:camera', 'The camera is silver.')
        self.memory.close()
        self.memory = AgentMemory.open(self.tmp.name, tenant='tenant:select', actor_id='agent:select',
                                       scope='project:select', purpose='task evidence')
        r = self.selected('What is the camera?')
        self.assertEqual([i['fact_ref'] for i in r['items']], [ref])
        self.assertNotIn('selection', self.memory.recall_context('camera'))

    def lifecycle_evidence(self):
        from tests.test_context_package import _evidence
        return _evidence(scope='project:select', tenant='tenant:select')

    def test_correction_forgetting_and_restart_stay_governed(self):
        old = self.put('m:camera', 'The camera is silver.')
        changed = self.memory.correct('m:camera', 'The camera is black.', evidence=self.lifecycle_evidence())
        self.assertTrue(changed['committed'])
        r = self.selected('What is the camera?')
        self.assertNotIn(old, json.dumps(r))
        self.assertIn('black', json.dumps(r))
        self.assertTrue(self.memory.forget('m:camera', evidence=self.lifecycle_evidence())['committed'])
        self.assertEqual(self.selected('What is the camera?')['items'], [])
        self.memory.close()
        self.memory = AgentMemory.open(self.tmp.name, tenant='tenant:select', actor_id='agent:select',
                                       scope='project:select', purpose='task evidence')
        self.assertNotIn('black', json.dumps(self.selected('What is the camera?')))

    def test_historical_profile_keeps_distinct_currentness_receipts(self):
        self.put('m:home', 'Alice lives in Paris on Rue Cler.')
        r = self.memory.correct('m:home', 'Alice lives in Berlin on Torstrasse.',
                                evidence=self.lifecycle_evidence(), replacement_kind='state_change')
        self.assertTrue(r['committed'])
        package = self.selected('Where does Alice live?', temporal_intent={'mode':'historical'})
        by_text = {i['content']:i['provenance'] for i in package['items'] if i.get('content')}
        self.assertEqual(by_text['Alice lives in Paris on Rue Cler.']['currentness'],
                         'historical_evidence_not_current')
        self.assertEqual(by_text['Alice lives in Berlin on Torstrasse.']['currentness'], 'current_state')
        self.assertEqual(by_text['Alice lives in Paris on Rue Cler.']['replacement_kind'], 'state_change')

    def test_failed_resolution_remains_unknown_instead_of_abstention(self):
        document = {'returned':['visible-ref'], 'admissions':{}, 'contract_version':'1.8.0'}
        r = cp.build_package(document, lambda ref: ('unresolved','no_longer_admissible',None),
                             max_chars_per_item=100, max_total_chars=100, max_tokens=None,
                             query='camera', consumer_profile='lexical_content')
        self.assertEqual(r['status'], 'partial_unresolved')
        self.assertEqual(r['selection']['omitted_refs'], [])
        self.assertNotIn('content', r['items'][0])

    def test_selected_schema_requires_explicit_policy_identity(self):
        self.put('m:camera', 'The camera is silver.')
        package = self.selected('camera')
        del package['selection']
        with self.assertRaises(ValueError):
            receipts.validate(cp.PACKAGE_SCHEMA, package)
