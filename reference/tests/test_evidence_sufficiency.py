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
