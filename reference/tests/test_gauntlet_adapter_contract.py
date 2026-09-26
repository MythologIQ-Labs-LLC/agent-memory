from __future__ import annotations

import unittest

from agentmem_ref.evaluation import (
    GauntletContractError,
    capability_support,
    manifest_digest,
    negotiate_capabilities,
    validate_manifest,
    validate_operation_envelope,
    validate_profile_requirements,
)


CONFIG = "a" * 64


def _manifest(*, capabilities=None, transport=None):
    declared = {
        "describe": {"support": "native"},
        "reset": {"support": "native"},
        "remember": {"support": "native"},
        "recall": {"support": "native"},
        "correct": {"support": "unsupported"},
    }
    if capabilities:
        declared.update(capabilities)
    return {
        "contract_family": "agent-memory-gauntlet-system-adapter",
        "contract_version": "0.1.0",
        "system": {
            "id": "example-memory",
            "kind": "external_memory",
            "version": "1.2.3",
            "revision": "system-rev-1",
            "configuration_digest": CONFIG,
        },
        "adapter": {
            "id": "example-memory-gauntlet",
            "version": "0.1.0",
            "revision": "adapter-rev-1",
        },
        "transport": transport or {"kind": "stdio", "startup": ["python", "adapter.py"]},
        "capabilities": declared,
        "benchmark_isolation": {"strategy": "disposable_instance"},
        "metadata": {},
        "authority_effect": "none",
    }


def _profile(*, required=None, optional=None):
    return {
        "contract_family": "agent-memory-gauntlet-profile-requirements",
        "contract_version": "0.1.0",
        "profile_id": "retrieval-v1",
        "requires": required
        or {
            "reset": ["native", "mapped"],
            "remember": ["native", "mapped"],
            "recall": ["native", "mapped"],
        },
        "optional": optional or {},
        "notes": [],
        "authority_effect": "none",
    }


class GauntletAdapterContractTests(unittest.TestCase):
    def test_retrieval_only_manifest_validates_without_governance_capabilities(self):
        manifest = validate_manifest(_manifest())
        self.assertEqual(manifest["system"]["id"], "example-memory")
        self.assertEqual(capability_support(manifest, "recall"), "native")
        self.assertIsNone(capability_support(manifest, "tenant_isolation"))

    def test_manifest_requires_available_describe(self):
        manifest = _manifest(capabilities={"describe": {"support": "unknown"}})
        with self.assertRaises(GauntletContractError):
            validate_manifest(manifest)

    def test_transport_specific_fields_are_enforced(self):
        with self.assertRaises(GauntletContractError):
            validate_manifest(_manifest(transport={"kind": "stdio"}))
        http = validate_manifest(
            _manifest(transport={"kind": "http", "endpoint": "https://memory.example.test/gauntlet"})
        )
        self.assertEqual(http["transport"]["kind"], "http")

    def test_manifest_authority_effect_is_always_none(self):
        manifest = _manifest()
        manifest["authority_effect"] = "advisory"
        with self.assertRaises(GauntletContractError):
            validate_manifest(manifest)

    def test_manifest_digest_is_deterministic(self):
        manifest = _manifest()
        self.assertEqual(manifest_digest(manifest), manifest_digest(dict(reversed(list(manifest.items())))))
        self.assertEqual(len(manifest_digest(manifest)), 64)

    def test_native_only_profile_rejects_derived_capability_as_unsupported(self):
        manifest = _manifest(capabilities={"tenant_isolation": {"support": "derived"}})
        profile = _profile(required={"tenant_isolation": ["native"]})
        result = negotiate_capabilities(manifest, profile)
        self.assertEqual(result["outcome"], "unsupported")
        self.assertEqual(result["required"][0]["state"], "support_class_not_accepted")
        self.assertEqual(result["authority_effect"], "none")

    def test_declared_unsupported_required_capability_is_not_execution_failure(self):
        manifest = _manifest(capabilities={"history": {"support": "unsupported"}})
        result = negotiate_capabilities(manifest, _profile(required={"history": ["native", "mapped"]}))
        self.assertEqual(result["outcome"], "unsupported")
        self.assertEqual(result["required"][0]["state"], "unsupported")

    def test_unknown_required_capability_fails_closed_as_invalid(self):
        manifest = _manifest(capabilities={"history": {"support": "unknown"}})
        result = negotiate_capabilities(manifest, _profile(required={"history": ["native", "mapped"]}))
        self.assertEqual(result["outcome"], "invalid")
        self.assertEqual(result["required"][0]["state"], "unknown_required")

    def test_undeclared_required_capability_fails_closed_as_invalid(self):
        result = negotiate_capabilities(_manifest(), _profile(required={"history": ["native"]}))
        self.assertEqual(result["outcome"], "invalid")
        self.assertEqual(result["required"][0]["state"], "undeclared_required")

    def test_optional_capability_miss_yields_eligible_with_limitations(self):
        result = negotiate_capabilities(
            _manifest(),
            _profile(optional={"history": ["native", "mapped"]}),
        )
        self.assertEqual(result["outcome"], "eligible_with_limitations")
        self.assertEqual(result["optional"][0]["state"], "undeclared_optional")

    def test_all_accepted_capabilities_yield_eligible(self):
        result = negotiate_capabilities(_manifest(), _profile())
        self.assertEqual(result["outcome"], "eligible")

    def test_negotiation_is_deterministic(self):
        manifest = _manifest(capabilities={"history": {"support": "mapped"}})
        profile = _profile(
            required={"recall": ["mapped", "native"], "remember": ["native", "mapped"]},
            optional={"history": ["mapped"]},
        )
        self.assertEqual(negotiate_capabilities(manifest, profile), negotiate_capabilities(manifest, profile))

    def test_profile_rejects_same_capability_as_required_and_optional(self):
        profile = _profile(required={"recall": ["native"]}, optional={"recall": ["native"]})
        with self.assertRaises(GauntletContractError):
            validate_profile_requirements(profile)

    def test_operation_request_and_response_envelopes_validate(self):
        request = {
            "contract_family": "agent-memory-gauntlet-operation",
            "contract_version": "0.1.0",
            "direction": "request",
            "operation": "recall",
            "request_id": "req-1",
            "payload": {"query": "where is the memory?", "limit": 5},
            "authority_effect": "none",
        }
        response = {
            "contract_family": "agent-memory-gauntlet-operation",
            "contract_version": "0.1.0",
            "direction": "response",
            "operation": "recall",
            "request_id": "req-1",
            "status": "ok",
            "result": {"items": []},
            "error": None,
            "timing": {"elapsed_ms": 1.25},
            "adapter_evidence": {},
            "authority_effect": "none",
        }
        self.assertEqual(validate_operation_envelope(request)["direction"], "request")
        self.assertEqual(validate_operation_envelope(response)["status"], "ok")

    def test_request_may_not_smuggle_response_status(self):
        request = {
            "contract_family": "agent-memory-gauntlet-operation",
            "contract_version": "0.1.0",
            "direction": "request",
            "operation": "recall",
            "request_id": "req-2",
            "payload": {},
            "status": "ok",
            "authority_effect": "none",
        }
        with self.assertRaises(GauntletContractError):
            validate_operation_envelope(request)


if __name__ == "__main__":
    unittest.main()
