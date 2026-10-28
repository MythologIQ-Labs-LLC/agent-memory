"""#786 public contract 2.0.0 candidate: isolation, and every claimed change executed live."""
from __future__ import annotations

import ast
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from agentmem_ref import AgentMemory
from agentmem_ref.api import contract
from agentmem_ref.api.scoped_identity import ScopeDistinctMemory, scope_distinct_key
from agentmem_ref.api.surface import STORE_PROFILE_FILE, StoreIdentityError

REFERENCE = Path(__file__).resolve().parents[1]
CANDIDATE = REFERENCE / "contract_candidates" / "public_contract_v2_candidate.py"
_spec = importlib.util.spec_from_file_location("public_contract_v2_candidate", CANDIDATE)
candidate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(candidate)


class IsolationTests(unittest.TestCase):
    def test_runtime_contract_is_not_the_candidate(self):
        # Integration (#674 x #786): the runtime carries the owner-accepted 1.8.0; the candidate was
        # measured against its predecessor 1.6.0 and is not promoted.
        self.assertEqual(contract.CONTRACT_VERSION, "1.8.0")
        self.assertEqual(candidate.PREDECESSOR_VERSION, "1.6.0")
        self.assertNotEqual(contract.CONTRACT_VERSION, candidate.CANDIDATE_VERSION)

    def test_no_runtime_module_imports_the_candidate(self):
        package = REFERENCE / "agentmem_ref"
        for path in package.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("contract_candidates", source, path)
            self.assertNotIn("public_contract_v2_candidate", source, path)
        self.assertFalse(CANDIDATE.is_relative_to(package))

    def test_record_is_an_unaccepted_candidate(self):
        record = candidate.load_record()
        self.assertEqual(record["candidate_version"], "2.0.0")
        self.assertIn("unaccepted", record["status"])
        self.assertIn("explicit owner approval", record["promotion_requires"])

    def test_disposition_is_the_separately_versioned_store_open_contract(self):
        from agentmem_ref.api import store_contract

        disposition = candidate.load_record()["disposition"]
        self.assertTrue(disposition.startswith("not promoted"))
        self.assertIn(f"{store_contract.STORE_OPEN_CONTRACT_ID} {store_contract.STORE_OPEN_CONTRACT_VERSION}", disposition)
        self.assertIn("envelope contract stays 1.6.0", disposition)  # the decision as recorded at the time
        note = candidate.load_record()["integration_note"]
        self.assertIn(f"owner-accepted {contract.CONTRACT_VERSION}", note)
        self.assertIn(f"{store_contract.STORE_OPEN_CONTRACT_ID} {store_contract.STORE_OPEN_CONTRACT_VERSION}", note)


class AdrCompatibilityTests(unittest.TestCase):
    def test_every_1x_envelope_is_incompatible_against_the_candidate(self):
        for version in ("1.0.0", "1.5.0", "1.6.0"):
            self.assertEqual(contract.compatibility({"contract_version": version}), contract.CURRENT)
            self.assertEqual(candidate.compatibility({"contract_version": version}), candidate.INCOMPATIBLE)
        self.assertEqual(candidate.compatibility({"contract_version": "2.0.0"}), candidate.CURRENT)
        self.assertEqual(candidate.compatibility({"contract_version": "2.1.0"}), candidate.MIGRATION_REQUIRED)
        self.assertEqual(candidate.compatibility({"contract_version": "two"}), candidate.UNKNOWN)


class BreakingChangesExecutedTests(unittest.TestCase):
    """Each breaking change the record claims is demonstrated against the live runtime."""

    def setUp(self):
        self.claims = {item["id"] for item in candidate.load_record()["breaking_changes"]}

    def test_bc1_default_single_project_store(self):
        self.assertIn("BC1-default-single-project-store", self.claims)
        with tempfile.TemporaryDirectory() as temp:
            with AgentMemory.open(temp, scope="project:a") as owner:
                self.assertEqual(owner.store_profile, "single_project_v1")
            self.assertEqual(json.loads((Path(temp) / STORE_PROFILE_FILE).read_text())["bound_project"], "project:a")
            with self.assertRaises(StoreIdentityError):
                AgentMemory.open(temp, scope="project:b")

    def test_bc2_scope_distinct_canonical_keys(self):
        self.assertIn("BC2-scope-distinct-canonical-keys", self.claims)
        with tempfile.TemporaryDirectory() as temp:
            with AgentMemory.open(temp, tenant="tenant:c", scope="project:a", store_profile="scope_distinct_v1") as memory:
                written = memory.remember("memory:k", "value")
                self.assertEqual(written["receipt"]["memory_id"], scope_distinct_key("tenant:c", "project:a", "memory:k"))
                with self.assertRaises(ValueError):
                    memory.remember("scope-key-v1:" + "0" * 64, "alias")

    def test_bc3_legacy_stores_restricted(self):
        self.assertIn("BC3-legacy-stores-restricted", self.claims)
        with tempfile.TemporaryDirectory() as temp:
            with AgentMemory.open(temp, scope="project:a") as owner:
                owner.remember("memory:k", "value")
            (Path(temp) / STORE_PROFILE_FILE).unlink()
            self.assertEqual(candidate.classify_existing_store(None, {"project:a"}),
                             "legacy_unprofiled_single_project_restricted")
            with AgentMemory.open(temp, scope="project:a") as owner:
                self.assertEqual(owner.store_profile, "legacy_unprofiled")
            with self.assertRaises(StoreIdentityError):
                AgentMemory.open(temp, scope="project:b")
        self.assertEqual(candidate.classify_existing_store(None, {"project:a", "project:b"}),
                         "legacy_unprofiled_multi_project_requires_governed_migration")

    def test_bc4_foreign_fact_refusal_code(self):
        self.assertIn("BC4-foreign-fact-refusal-code", self.claims)
        with tempfile.TemporaryDirectory() as temp:
            with AgentMemory.open(temp, scope="project:a", store_profile="scope_distinct_v1") as owner:
                foreign_fact = owner.remember("memory:k", "value")["fact_uuid"]
            with AgentMemory.open(temp, scope="project:b") as other:
                other.remember("memory:k", "other value")
                aimed = other.dispute("memory:k", fact_uuid=foreign_fact)
        # contract 1.8.0: the bare fact_not_found result, byte-identical to an id nobody wrote
        self.assertEqual((aimed["committed"], aimed["refusal"]), (False, "fact_not_found"))
        self.assertIn(aimed.get("outcome"), (None, "block"))

    def test_bc5_scope_distinct_wrapper_backing(self):
        self.assertIn("BC5-scope-distinct-wrapper-backing", self.claims)
        with tempfile.TemporaryDirectory() as temp:
            with AgentMemory.open(temp, tenant="tenant:w", actor_id="agent:w", scope="project:a") as tenant_wide:
                with self.assertRaisesRegex(ValueError, "scope_distinct_v1"):
                    ScopeDistinctMemory(tenant_wide, tenant="tenant:w", scope="project:a", actor_id="agent:w")

    def test_every_claim_has_a_test(self):
        tested = {node.name for node in ast.walk(ast.parse(Path(__file__).read_text(encoding="utf-8")))
                  if isinstance(node, ast.FunctionDef) and node.name.startswith("test_bc")}
        self.assertEqual(len(tested), len(self.claims))


if __name__ == "__main__":
    unittest.main()
