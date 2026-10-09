"""General capability and negative-control tests, not benchmark phrase fixtures."""
import importlib.util
import json
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'agentmem_ref/runtime/evidence_sufficiency.py'
spec = importlib.util.spec_from_file_location('evidence_sufficiency', MODULE)
s = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = s
spec.loader.exec_module(s)


def obs(*, admitted=('e:1',), needs=(), coverage=(), contradictions=(),
        routes=(), count=1):
    return s.SufficiencyObservation(tuple(admitted), tuple(needs), tuple(coverage),
                                    tuple(contradictions), tuple(routes), count)


class EvidenceSufficiencyTests(unittest.TestCase):
    def test_count_is_not_quality(self):
        r = s.assess_sufficiency(obs(admitted=('a','b','c'), count=2))
        self.assertTrue(r.count_target_met)
        self.assertFalse(r.mechanical_coverage_met)
        self.assertEqual(r.diagnosis, 'coverage_undetermined')
        self.assertEqual(r.continuation_proposal, 'continue_if_permitted')
        self.assertFalse(r.answer_quality_verified)
        self.assertFalse(r.can_admit)
        self.assertFalse(r.can_mutate)

    def test_typed_coverage_is_mechanical_only(self):
        needs=(s.CoverageNeed('requested-software-version'),)
        coverage=(s.CoverageObservation('a',('requested-software-version',),s.TYPED_OBSERVATION),)
        r=s.assess_sufficiency(obs(admitted=('a',),needs=needs,coverage=coverage))
        self.assertTrue(r.mechanical_coverage_met)
        self.assertEqual(r.need_support_refs,(('requested-software-version',('a',)),))
        self.assertEqual(r.to_dict()['need_support_refs'],{'requested-software-version':['a']})
        self.assertEqual(r.diagnosis,'mechanical_coverage_observed')
        self.assertEqual(r.continuation_proposal,'review_stop')
        self.assertFalse(r.answer_quality_verified)
        self.assertFalse(r.can_admit)

    def test_controller_estimate_cannot_satisfy_need(self):
        need=s.CoverageNeed('status')
        r=s.assess_sufficiency(obs(needs=(need,),coverage=(s.CoverageObservation('e:1',('status',)),)))
        self.assertEqual(r.missing_needs,('status',))
        self.assertEqual(r.need_support_counts,(('status',0),))
        self.assertEqual(r.diagnosis,'missing_declared_evidence')

    def test_per_need_multiplicity_dedupes_same_fact(self):
        n=s.CoverageNeed('independent-claims',2)
        evidence=(s.CoverageObservation('a',('independent-claims',),s.TYPED_OBSERVATION),
                  s.CoverageObservation('a',('independent-claims',),s.TYPED_OBSERVATION))
        r=s.assess_sufficiency(obs(admitted=('a','b'),needs=(n,),coverage=evidence))
        self.assertFalse(r.mechanical_coverage_met)
        self.assertEqual(r.need_support_counts,(('independent-claims',1),))

    def test_multiple_needs_with_distinct_admitted_support(self):
        n=(s.CoverageNeed('provider'),s.CoverageNeed('quota'))
        c=(s.CoverageObservation('a',('quota','provider'),s.TYPED_OBSERVATION),)
        r=s.assess_sufficiency(obs(admitted=('a',),needs=n,coverage=c))
        self.assertTrue(r.mechanical_coverage_met)
        self.assertEqual(dict(r.need_support_counts),{'provider':1,'quota':1})

    def test_contradiction_blocks_stop_even_with_coverage(self):
        n=(s.CoverageNeed('active-owner'),)
        c=(s.CoverageObservation('a',('active-owner',),s.TYPED_OBSERVATION),)
        r=s.assess_sufficiency(obs(admitted=('b','a'),needs=n,coverage=c,
                                   contradictions=(('b','a'),('a','b'))))
        self.assertEqual(r.contradiction_pairs,(('a','b'),))
        self.assertEqual(r.diagnosis,'unresolved_contradiction')
        self.assertEqual(r.continuation_proposal,'continue_if_permitted')

    def test_bound_missing_is_not_frontier_exhausted(self):
        route=s.RouteWorkObservation('semantic',16,16,True)
        r=s.assess_sufficiency(obs(needs=(s.CoverageNeed('ownership'),),routes=(route,)))
        self.assertEqual(r.diagnosis,'budget_bound_missing_evidence')
        self.assertEqual(r.budget_bound_routes,('semantic',))

    def test_bound_with_coverage_does_not_qualify_quality(self):
        route=s.RouteWorkObservation('graph',8,8,True)
        n=(s.CoverageNeed('source'),)
        c=(s.CoverageObservation('a',('source',),s.TYPED_OBSERVATION),)
        r=s.assess_sufficiency(obs(admitted=('a',),needs=n,coverage=c,routes=(route,)))
        self.assertEqual(r.diagnosis,'coverage_observed_resource_bound')
        self.assertEqual(r.continuation_proposal,'continue_if_permitted')

    def test_unexecuted_route_is_not_exhaustion(self):
        r=s.assess_sufficiency(obs(needs=(s.CoverageNeed('source'),),
                                  coverage=(s.CoverageObservation('e:1',('source',),s.TYPED_OBSERVATION),),
                                  routes=(s.RouteWorkObservation('graph',4,0,False),)))
        self.assertEqual(r.unexecuted_routes,('graph',))
        self.assertEqual(r.diagnosis,'planned_routes_not_executed')

    def test_no_admitted_evidence_even_if_route_cap_zero(self):
        r=s.assess_sufficiency(obs(admitted=(),needs=(s.CoverageNeed('x'),),routes=(s.RouteWorkObservation('lexical',0,0,False),)))
        self.assertEqual(r.diagnosis,'no_admitted_evidence')
        self.assertFalse(r.count_target_met)

    def test_unadmitted_support_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'governed admitted'):
            obs(coverage=(s.CoverageObservation('foreign',('secret',)),),needs=(s.CoverageNeed('secret'),))

    def test_unadmitted_contradiction_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'distinct admitted'):
            obs(admitted=('a','b'),contradictions=(('a','outsider'),))

    def test_same_fact_contradiction_rejected(self):
        with self.assertRaisesRegex(ValueError,'distinct admitted'):
            obs(contradictions=(('e:1','e:1'),))

    def test_duplicate_need_route_and_admitted_rejected(self):
        with self.assertRaisesRegex(ValueError,'repeat'):
            obs(admitted=('a','a'))
        with self.assertRaisesRegex(ValueError,'duplicate requested need'):
            obs(needs=(s.CoverageNeed('x'),s.CoverageNeed('x')))
        with self.assertRaisesRegex(ValueError,'duplicate route-work'):
            obs(routes=(s.RouteWorkObservation('r',0,0,False),s.RouteWorkObservation('r',0,0,False)))

    def test_malformed_counters_and_booleans_rejected(self):
        for cap,returned,executed in [(1,2,True),(-1,0,True),(1,1,False),(True,0,True),(1,True,True)]:
            with self.subTest(cap=cap,returned=returned,executed=executed),self.assertRaises((ValueError,TypeError)):
                s.RouteWorkObservation('r',cap,returned,executed)
        with self.assertRaises(ValueError):
            s.CoverageNeed('x',True)
        with self.assertRaises(ValueError):
            obs(count=0)

    def test_origin_must_be_typed_and_recognized(self):
        with self.assertRaisesRegex(ValueError,'unsupported'):
            s.CoverageObservation('a',('need',),'invented_truth')
        with self.assertRaisesRegex(ValueError,'undeclared need'):
            obs(coverage=(s.CoverageObservation('e:1',('need',),s.TYPED_OBSERVATION),))

    def test_report_constructor_cannot_spoof_authority(self):
        base=s.assess_sufficiency(obs())
        from dataclasses import replace
        for patch in ({'can_admit':True}, {'can_mutate':True},
                      {'answer_quality_verified':True}, {'authority_effect':'allow'},
                      {'continuation_proposal':'execute_stop'}):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                replace(base, **patch)

    def test_competing_single_values_block_mechanical_review_stop(self):
        need=s.CoverageNeed('typed:engine|owner')
        coverage=tuple(s.CoverageObservation(ref,(need.key,),s.TYPED_OBSERVATION) for ref in ('old','new'))
        claims=(s.TypedValueClaim('old',need.key,'Alice','single'),
                s.TypedValueClaim('new',need.key,'Bob','single'))
        observation=s.SufficiencyObservation(('new','old'),(need,),coverage,
                                             count_target=1,typed_value_claims=claims)
        result=s.assess_sufficiency(observation)
        self.assertTrue(result.mechanical_coverage_met)
        self.assertTrue(result.count_target_met)
        self.assertEqual(result.diagnosis,'value_coherence_unresolved')
        self.assertEqual(result.continuation_proposal,'continue_if_permitted')
        self.assertEqual(result.value_coherence[0].status,'competing_values_unresolved')
        self.assertEqual(result.value_coherence[0].fact_groups,(('new',),('old',)))
        self.assertFalse(result.answer_quality_verified)

    def test_change_assertion_is_not_proof_of_governed_transition(self):
        need=s.CoverageNeed('typed:app|endpoint')
        coverage=(s.CoverageObservation('v2',(need.key,),s.TYPED_OBSERVATION),)
        claim=(s.TypedValueClaim('v2',need.key,'https://new.example','single','change'),)
        result=s.assess_sufficiency(s.SufficiencyObservation(
            ('v2',),(need,),coverage,count_target=1,typed_value_claims=claim))
        self.assertEqual(result.value_coherence[0].status,'change_assertion_unresolved')
        self.assertEqual(result.diagnosis,'value_coherence_unresolved')
        self.assertNotEqual(result.continuation_proposal,'review_stop')

    def test_coexistence_and_unknown_cardinality_are_not_contradiction_certificates(self):
        need=s.CoverageNeed('typed:team|maintainer')
        coverage=tuple(s.CoverageObservation(ref,(need.key,),s.TYPED_OBSERVATION) for ref in ('a','b'))
        for cardinality,status in (('multi','coexistence_possible'),(None,'cardinality_unresolved')):
            with self.subTest(cardinality=cardinality):
                claims=(s.TypedValueClaim('a',need.key,'Dawn','single'),
                        s.TypedValueClaim('b',need.key,'Eve',cardinality))
                result=s.assess_sufficiency(s.SufficiencyObservation(
                    ('a','b'),(need,),coverage,count_target=1,typed_value_claims=claims))
                self.assertEqual(result.value_coherence[0].status,status)
                self.assertEqual(result.diagnosis,'value_coherence_unresolved')
                self.assertEqual(result.contradiction_pairs,())

    def test_identical_values_group_references_without_claiming_independence(self):
        need=s.CoverageNeed('typed:system|version',2)
        coverage=tuple(s.CoverageObservation(ref,(need.key,),s.TYPED_OBSERVATION) for ref in ('a','b'))
        claims=(s.TypedValueClaim('b',need.key,'3.1','single'),
                s.TypedValueClaim('a',need.key,'3.1','single'))
        result=s.assess_sufficiency(s.SufficiencyObservation(
            ('b','a'),(need,),coverage,count_target=1,typed_value_claims=claims))
        self.assertEqual(result.value_coherence[0].status,'same_value_observed')
        self.assertEqual(result.value_coherence[0].fact_groups,(('a','b'),))
        self.assertEqual(result.diagnosis,'mechanical_coverage_observed')
        self.assertFalse(result.answer_quality_verified)

    def test_single_multi_value_or_unknown_slot_cannot_signal_complete(self):
        need=s.CoverageNeed('typed:docs|contributors')
        support=(s.CoverageObservation('one',(need.key,),s.TYPED_OBSERVATION),)
        for cardinality,status in (('multi','coexistence_possible'),
                                   (None,'cardinality_unresolved')):
            with self.subTest(cardinality=cardinality):
                claim=(s.TypedValueClaim('one',need.key,'Jo',cardinality),)
                report=s.assess_sufficiency(s.SufficiencyObservation(
                    ('one',),(need,),support,typed_value_claims=claim))
                self.assertEqual(report.value_coherence[0].status,status)
                self.assertEqual(report.diagnosis,'value_coherence_unresolved')
                self.assertEqual(report.continuation_proposal,'continue_if_permitted')

    def test_cannot_forge_stop_on_unresolved_competition(self):
        from dataclasses import replace
        need=s.CoverageNeed('typed:server|owner')
        support=(s.CoverageObservation('a',(need.key,),s.TYPED_OBSERVATION),
                 s.CoverageObservation('b',(need.key,),s.TYPED_OBSERVATION))
        claims=(s.TypedValueClaim('a',need.key,'A','single'),
                s.TypedValueClaim('b',need.key,'B','single'))
        report=s.assess_sufficiency(s.SufficiencyObservation(
            ('a','b'),(need,),support,typed_value_claims=claims))
        with self.assertRaisesRegex(ValueError,'cannot recommend stopping'):
            replace(report, continuation_proposal='review_stop')

    def test_value_comparison_never_emits_private_literal(self):
        need=s.CoverageNeed('typed:tenant|secret')
        literal='Sensitive internal value'
        coverage=(s.CoverageObservation('private',(need.key,),s.TYPED_OBSERVATION),)
        claim=(s.TypedValueClaim('private',need.key,literal,'single'),)
        result=s.assess_sufficiency(s.SufficiencyObservation(
            ('private',),(need,),coverage,typed_value_claims=claim))
        self.assertNotIn(literal,json.dumps(result.to_dict()))
        self.assertEqual(result.to_dict()['value_coherence'][0]['fact_groups'],[['private']])

    def test_fake_or_unadmitted_typed_value_claims_fail_closed(self):
        need=s.CoverageNeed('typed:repo|license')
        good=s.CoverageObservation('a',(need.key,),s.TYPED_OBSERVATION)
        for candidate in ('outsider','a'):
            with self.subTest(candidate=candidate):
                with self.assertRaisesRegex(ValueError,'typed value claim'):
                    s.SufficiencyObservation(('a',),(need,),(),typed_value_claims=(
                        s.TypedValueClaim(candidate,need.key,'MIT'),))
        with self.assertRaisesRegex(ValueError,'duplicate value claim'):
            s.assess_value_coherence((need,),(
                s.TypedValueClaim('a',need.key,'MIT'),
                s.TypedValueClaim('a',need.key,'GPL')))
        with self.assertRaisesRegex(ValueError,'cardinality'):
            s.TypedValueClaim('a',need.key,'MIT','invented')
        with self.assertRaisesRegex(ValueError,'assertion'):
            s.TypedValueClaim('a',need.key,'MIT','single','definitive')
        with self.assertRaisesRegex(ValueError,'control'):
            s.TypedValueClaim('a',need.key,'secret\nleak')

    def test_value_assessment_order_independent_and_no_raw_values(self):
        need=s.CoverageNeed('typed:product|price')
        coverage=tuple(s.CoverageObservation(ref,(need.key,),s.TYPED_OBSERVATION) for ref in ('a','b','c'))
        claims=(s.TypedValueClaim('a',need.key,'10','single'),
                s.TypedValueClaim('b',need.key,'12','single'),
                s.TypedValueClaim('c',need.key,'10','single'))
        def invoke(refs,claim_order):
            return s.assess_sufficiency(s.SufficiencyObservation(
                refs,(need,),coverage,typed_value_claims=claim_order)).to_dict()
        self.assertEqual(invoke(('a','b','c'),claims),
                         invoke(('c','a','b'),claims[::-1]))
        self.assertEqual(invoke(('a','b','c'),claims)['value_coherence'][0]['fact_groups'],
                         [['a','c'],['b']])

    def test_determinism_independent_of_evidence_and_route_order(self):
        needs=(s.CoverageNeed('one'),s.CoverageNeed('two'))
        c=(s.CoverageObservation('a',('one',),s.TYPED_OBSERVATION),
           s.CoverageObservation('b',('two',),s.TYPED_OBSERVATION))
        routes=(s.RouteWorkObservation('g',3,3,True),s.RouteWorkObservation('v',5,2,True))
        a=s.assess_sufficiency(obs(admitted=('a','b'),needs=needs,coverage=c,routes=routes))
        b=s.assess_sufficiency(obs(admitted=('b','a'),needs=needs[::-1],coverage=c[::-1],routes=routes[::-1]))
        self.assertEqual(a.to_dict(),b.to_dict())
        self.assertEqual(json.dumps(a.to_dict(),sort_keys=True),json.dumps(b.to_dict(),sort_keys=True))
        self.assertEqual(a.authority_effect,'none')


if __name__ == '__main__':
    unittest.main()
