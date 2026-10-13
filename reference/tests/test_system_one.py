"""Offline contract tests for a shared System One provider. No network calls."""
from __future__ import annotations
import unittest

from agentmem_ref.decision_context import DecisionContextPort, ResolvedEvidence
from agentmem_ref.decision_gateway import DecisionGateway, DecisionContractError, EgressDecision
from agentmem_ref.system_one import ENDPOINTS, SystemOneProvider


class MemoryStub:
    tenant = "tenant:one"
    scope = "project:one"

    def recall(self, query, *, budget, purpose):
        return {
            "stage": "recall",
            "returned": ["fact:one"],
            "admitted": ["fact:one"],
            "return_policy": {"requested_k": budget, "authority_effect": "none", "applied": False},
        }


class HostPolicyStub:
    def authorize(self, request):
        return EgressDecision(request.request_ref, request.provider_ref, True, "fixture:approved")


class TransportStub:
    def __init__(self):
        self.calls = []

    def post_json(self, endpoint, body):
        self.calls.append((endpoint, body))
        return {
            "model": body["model"],
            "answers": {
                "decision": {
                    "type": "choice",
                    "choice": "defer",
                    "probabilities": {"defer": 0.75, "apply": 0.25},
                }
            },
        }


def context_port():
    return DecisionContextPort(
        MemoryStub(),
        lambda ref: ResolvedEvidence(
            ref, "Release requires an approval", "tenant:one", "project:one", "source:private"
        ),
    )


class SystemOneContractTests(unittest.TestCase):
    def test_shared_wire_protocol_for_both_vendors(self):
        for vendor, model in (("fastino", "fastino/glide"), ("typesafe", "jev-1.13.0")):
            with self.subTest(vendor=vendor):
                transport = TransportStub()
                provider = SystemOneProvider(vendor, model, transport)
                gateway = DecisionGateway(context_port(), provider, HostPolicyStub())
                result = gateway.decide(
                    "Choose a release option", choices=("defer", "apply"), purpose="release"
                )
                self.assertEqual(result["choice"], "defer")
                self.assertEqual(result["authority_effect"], "none")
                endpoint, body = transport.calls[0]
                self.assertEqual(endpoint, ENDPOINTS[vendor])
                self.assertEqual(body["questions"]["decision"]["type"], "choice")
                self.assertEqual(body["state"]["evidence"][0]["text"], "Release requires an approval")
                self.assertNotIn("fact:one", str(body))
                self.assertNotIn("tenant:one", str(body))
                self.assertNotIn("source:private", str(body))

    def test_missing_host_policy_blocks_transport(self):
        transport = TransportStub()
        provider = SystemOneProvider("fastino", "fastino/glide", transport)
        gateway = DecisionGateway(context_port(), provider)
        with self.assertRaises(DecisionContractError):
            gateway.decide("q", choices=("defer", "apply"), purpose="test")
        self.assertEqual(transport.calls, [])

    def test_mismatched_model_and_malformed_response_are_rejected(self):
        class WrongModelTransport:
            def post_json(self, endpoint, body):
                return {"model": "unexpected-checkpoint", "answers": {}}
        class MissingAnswerTransport:
            def post_json(self, endpoint, body):
                return {"model": body["model"], "answers": {}}
        for transport in (WrongModelTransport(), MissingAnswerTransport()):
            gateway = DecisionGateway(
                context_port(),
                SystemOneProvider("fastino", "fastino/glide", transport),
                HostPolicyStub(),
            )
            with self.subTest(transport=type(transport).__name__), self.assertRaises(DecisionContractError):
                gateway.decide("q", choices=("defer", "apply"), purpose="test")

    def test_invalid_vendor_refused(self):
        with self.assertRaises(ValueError):
            SystemOneProvider("unlisted", "model", TransportStub())


if __name__ == "__main__":
    unittest.main()
