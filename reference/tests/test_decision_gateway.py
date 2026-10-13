"""Offline, fixture-backed decision gateway conformance tests. Not outcome benchmarks."""
from __future__ import annotations
import unittest
from agentmem_ref.decision_context import DecisionContextPort, ResolvedEvidence
from agentmem_ref.decision_gateway import DecisionGateway, DecisionContractError, EgressDecision

class Memory:
    tenant = 'tenant:a'
    scope = 'project:a'
    def __init__(self, returned=('f1',), admitted=('f1',)):
        self.returned, self.admitted = list(returned), list(admitted)
        self.calls = 0
    def recall(self, query, *, budget, purpose):
        self.calls += 1
        return {'stage':'recall', 'admitted':self.admitted, 'returned':self.returned,
                'return_policy':{'authority_effect':'none','requested_k':budget,'applied':False}}

class Provider:
    provider_ref='fixture:decision-model-v1'
    def __init__(self, remote=False, response=None):
        self.remote, self.response, self.calls = remote, response, 0
    def decide(self, request):
        self.calls += 1
        if self.response is not None:
            return self.response(request)
        return {'request_ref':request.request_ref, 'status':'complete', 'choice':request.choices[0],
                'probabilities':{request.choices[0]:0.8, request.choices[1]:0.2}}

def gateway(memory=None, provider=None, resolver=None):
    memory = memory or Memory()
    provider = provider or Provider()
    reader = resolver or (lambda ref: ResolvedEvidence(ref,'release policy is active','tenant:a','project:a','evidence:host'))
    return DecisionGateway(DecisionContextPort(memory, reader), provider), memory, provider

def execute(g, **kwargs):
    return g.decide('What is the release policy?', choices=('apply','defer'), purpose='release', **kwargs)

class DecisionGatewayTests(unittest.TestCase):
    def test_credential_free_local_decision(self):
        g,m,p = gateway()
        outcome=execute(g)
        self.assertEqual(outcome['choice'],'apply')
        self.assertEqual(outcome['authority_effect'],'none')
        self.assertEqual(m.calls,1)
        self.assertEqual(p.calls,1)
        self.assertEqual(len(outcome['request_ref']),71)

    def test_no_remote_egress_without_explicit_permission(self):
        g,m,p=gateway(provider=Provider(remote=True))
        with self.assertRaisesRegex(DecisionContractError,'egress'):
            execute(g)
        self.assertEqual(m.calls,0)
        self.assertEqual(p.calls,0)
        class AllowPolicy:
            def authorize(self, req):
                return EgressDecision(req.request_ref, req.provider_ref, True, 'approval:fixture')
        authorized = DecisionGateway(g.context_port, p, AllowPolicy())
        self.assertEqual(execute(authorized)['status'], 'complete')

    def test_remote_host_egress_policy_must_bind_exact_request(self):
        class WrongPolicy:
            def authorize(self, req):
                return EgressDecision('another-request', req.provider_ref, True, 'approval:fake')
        g,m,p=gateway(provider=Provider(remote=True))
        g=DecisionGateway(g.context_port,p,WrongPolicy())
        with self.assertRaisesRegex(DecisionContractError, 'egress authorization'):
            execute(g)
        self.assertEqual(p.calls,0)

    def test_missing_context_does_not_call_provider(self):
        g,m,p=gateway(resolver=lambda _:None)
        r=execute(g)
        self.assertEqual(r['status'],'context_unavailable')
        self.assertFalse(r['provider_called'])
        self.assertEqual(p.calls,0)

    def test_zero_memory_baseline_still_permits_decision(self):
        g,m,p=gateway(memory=Memory((), ()))
        outcome=execute(g)
        self.assertEqual(outcome["context_status"], "no_evidence")
        self.assertEqual(outcome["status"], "complete")
        self.assertEqual(p.calls, 1)

    def test_disallowed_candidates_do_not_enter_provider(self):
        m=Memory(returned=('f1',),admitted=('f1','private'))
        seen=[]
        p=Provider(response=lambda req:(seen.append(req.context),{
            'request_ref':req.request_ref,'status':'abstained'})[1])
        g,_,_=gateway(m,p)
        self.assertEqual(execute(g)['status'],'abstained')
        self.assertEqual([v['fact_ref'] for v in seen[0]['evidence']],['f1'])

    def test_rejects_unauthorized_provider_fields(self):
        p=Provider(response=lambda req:{'request_ref':req.request_ref, 'status':'complete',
           'choice':'apply','probabilities':{'apply':0.8,'defer':0.2},'authorize_deletion':True})
        g,_,_=gateway(provider=p)
        with self.assertRaisesRegex(DecisionContractError,'undeclared'):
            execute(g)

    def test_rejects_invalid_calibration_and_binding(self):
        for factory in [
            lambda req:{'request_ref':'wrong','status':'complete','choice':'apply','probabilities':{'apply':0.8,'defer':0.2}},
            lambda req:{'request_ref':req.request_ref,'status':'complete','choice':'apply','probabilities':{'apply':float('nan'),'defer':0.2}},
            lambda req:{'request_ref':req.request_ref,'status':'complete','choice':'apply','probabilities':{'apply':0.6,'defer':0.1}},
            lambda req:{'request_ref':req.request_ref,'status':'complete','choice':'defer','probabilities':{'apply':0.8,'defer':0.2}},
            lambda req:{'request_ref':req.request_ref,'status':'complete','choice':'delete','probabilities':{'apply':0.8,'defer':0.2}},
        ]:
            g,_,_=gateway(provider=Provider(response=factory))
            with self.subTest(factory=factory), self.assertRaises(DecisionContractError):
                execute(g)

    def test_rejects_bad_options(self):
        g,_,_=gateway()
        with self.assertRaises(DecisionContractError):
            g.decide('q',choices=('apply','apply'),purpose='release')
        with self.assertRaises(DecisionContractError):
            g.decide('q',choices=('apply',),purpose='release')

if __name__=='__main__':unittest.main()
