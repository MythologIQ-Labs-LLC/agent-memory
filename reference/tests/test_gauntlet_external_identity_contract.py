from __future__ import annotations

import json
import unittest
from pathlib import Path

from agentmem_ref._paths import REPO_ROOT
from agentmem_ref.evaluation.gauntlet_contract import (
    GauntletContractError,
    negotiate_capabilities,
    validate_manifest,
)


MANIFEST_PATH = REPO_ROOT / "examples" / "gauntlet" / "minimal-stdio-adapter.json"


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _profile(*, optional=None) -> dict:
    return {
        "contract_family": "agent-memory-gauntlet-profile-requirements",
        "contract_version": "0.1.0",
        "profile_id": "external-identity-test-v1",
        "requires": {
            "describe": ["native", "mapped", "derived"],
            "remember": ["native", "mapped", "derived"],
            "recall": ["native", "mapped", "derived"],
            "reset": ["native", "mapped", "derived"],
        },
        "optional": optional or {},
        "notes": [],
        "authority_effect": "none",
    }


class GauntletExternalIdentityContractTests(unittest.TestCase):
    def test_system_revision_is_required(self):
        manifest = _manifest()
        del manifest["system"]["revision"]
        with self.assertRaises(GauntletContractError):
            validate_manifest(manifest)

    def test_adapter_revision_is_required(self):
        manifest = _manifest()
        del manifest["adapter"]["revision"]
        with self.assertRaises(GauntletContractError):
            validate_manifest(manifest)

    def test_declared_configuration_digest_must_be_exact_sha256_shape(self):
        manifest = _manifest()
        manifest["system"]["configuration_digest"] = "floating-config-name"
        with self.assertRaises(GauntletContractError):
            validate_manifest(manifest)

    def test_optional_unsupported_capability_is_limitation_not_failure(self):
        manifest = _manifest()
        manifest["capabilities"]["history"] = {"support": "unsupported"}
        result = negotiate_capabilities(
            manifest,
            _profile(optional={"history": ["native", "mapped", "derived"]}),
        )
        self.assertEqual(result["outcome"], "eligible_with_limitations")
        self.assertEqual(result["optional"][0]["state"], "unsupported_optional")
        self.assertEqual(result["authority_effect"], "none")


if __name__ == "__main__":
    unittest.main()
