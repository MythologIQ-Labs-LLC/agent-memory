"""#786 store-open contract version separation.

Store identity profiles are versioned by the store-open contract
(``agentmem_ref.api.store_contract``), not by the public envelope contract. This module
shows both halves of that decision on real SQLite stores:

* valid ``1.0.0``-``1.6.0`` envelopes keep their ADR-030 state (``current``) and run on
  every authorized store -- ``single_project_v1``, ``scope_distinct_v1`` and a restricted
  single-project legacy store -- through both the facade and the envelope surface;
* unauthorized multi-project access still fails closed, with the store left
  byte-identical, whatever store-open or envelope version the host declares.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from agentmem_ref import AgentMemory
from agentmem_ref.api import contract, store_contract, surface
from agentmem_ref.api.surface import (
    STORE_PROFILE_FILE,
    STORE_PROFILE_LEGACY,
    STORE_PROFILE_SCOPE_DISTINCT,
    STORE_PROFILE_SINGLE_PROJECT,
    StoreIdentityError,
)
from agentmem_ref.runtime.restart_runtime import RuntimeRecoveryError

from tests._tenant_wide_fixture import open_tenant_wide

REFERENCE = Path(__file__).resolve().parents[1]
FIXTURES = REFERENCE / "fixtures" / "api"
TENANT = "org:example"
PROJECT = "project:example"
OTHER = "project:other"
ENVELOPE_VERSIONS = ("1.0.0", "1.1.0", "1.2.0", "1.3.0", "1.4.0", "1.5.0", "1.6.0")
DATABASE = "agent-memory.sqlite3"


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _state(root) -> dict:
    """Every durable byte a refused open must leave untouched."""
    root = Path(root)
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.iterdir())
        if path.is_file() and path.name in (DATABASE, STORE_PROFILE_FILE, "configuration-binding.json")
    }


def _open(root, scope=PROJECT, **kwargs) -> AgentMemory:
    return AgentMemory.open(root, tenant=TENANT, actor_id="agent:release-planner", scope=scope, **kwargs)


def _legacy_single_project(root) -> None:
    with _open(root) as memory:
        memory.remember("memory:k", "legacy value")
    (Path(root) / STORE_PROFILE_FILE).unlink()


def _authorized_stores():
    """(label, opener) for every store this runtime admits for PROJECT."""
    def single(root):
        _open(root).close()
        return lambda **kw: _open(root, **kw)

    def scope_distinct(root):
        _open(root, store_profile=STORE_PROFILE_SCOPE_DISTINCT).close()
        return lambda **kw: _open(root, **kw)

    def legacy(root):
        _legacy_single_project(root)
        return lambda **kw: _open(root, **kw)

    return (("single_project_v1", single), ("scope_distinct_v1", scope_distinct), ("legacy_unprofiled", legacy))


class VersionSeparationTests(unittest.TestCase):
    def test_the_two_contracts_have_distinct_identities_and_versions(self):
        self.assertEqual(contract.CONTRACT_VERSION, "1.6.0")
        self.assertEqual(store_contract.STORE_OPEN_CONTRACT_ID, "agent-memory-store-open")
        self.assertEqual(store_contract.STORE_OPEN_CONTRACT_VERSION, "1.0.0")
        self.assertEqual(store_contract.RECORD_VERSION, 1)

    def test_store_contract_does_not_depend_on_the_envelope_contract(self):
        tree = ast.parse((REFERENCE / "agentmem_ref" / "api" / "store_contract.py").read_text(encoding="utf-8"))
        imported = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        imported |= {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        self.assertEqual(imported, {"__future__", "typing"})

    def test_envelope_compatibility_is_unchanged(self):
        for version in ENVELOPE_VERSIONS:
            self.assertEqual(contract.compatibility({"contract_version": version}), contract.CURRENT, version)
        self.assertEqual(contract.compatibility({"contract_version": "1.7.0"}), contract.MIGRATION_REQUIRED)
        self.assertEqual(contract.compatibility({"contract_version": "2.0.0"}), contract.INCOMPATIBLE)
        self.assertEqual(contract.compatibility({}), contract.UNKNOWN)

    def test_store_open_compatibility_states(self):
        cases = {
            "1.0.0": store_contract.CURRENT,
            "1.0.7": store_contract.CURRENT,
            "1.1.0": store_contract.MIGRATION_REQUIRED,
            "2.0.0": store_contract.INCOMPATIBLE,
            "0.9.0": store_contract.INCOMPATIBLE,
            "1.0": store_contract.UNKNOWN,
            "-1.0.0": store_contract.UNKNOWN,
            "one": store_contract.UNKNOWN,
            None: store_contract.UNKNOWN,
            100: store_contract.UNKNOWN,
        }
        for version, state in cases.items():
            self.assertEqual(store_contract.compatibility(version), state, version)
        for record_version, state in ((1, store_contract.CURRENT), (2, store_contract.MIGRATION_REQUIRED),
                                      (0, store_contract.UNKNOWN), ("1", store_contract.UNKNOWN),
                                      (True, store_contract.UNKNOWN), (None, store_contract.UNKNOWN)):
            self.assertEqual(store_contract.record_compatibility(record_version), state, record_version)

    def test_handles_report_both_versions_separately(self):
        for label, prepare in _authorized_stores():
            with self.subTest(store=label), tempfile.TemporaryDirectory() as temp:
                with prepare(temp)() as memory:
                    self.assertEqual(memory.contract_version, "1.6.0")
                    self.assertEqual(memory.store_open_contract, {
                        "contract_id": "agent-memory-store-open",
                        "contract_version": "1.0.0",
                        "record_version": 1,
                        "store_profile": label,
                        "envelope_contract_version": "1.6.0",
                    })

    def test_new_records_carry_the_store_open_record_version(self):
        with tempfile.TemporaryDirectory() as temp:
            _open(temp, store_open_contract="1.0.0").close()
            record = json.loads((Path(temp) / STORE_PROFILE_FILE).read_text(encoding="utf-8"))
        self.assertEqual(record["version"], store_contract.RECORD_VERSION)
        self.assertEqual(record["profile"], STORE_PROFILE_SINGLE_PROJECT)


class EnvelopeCompatibilityOnAuthorizedStoresTests(unittest.TestCase):
    """Valid 1.x envelopes stay ``current`` and run on every authorized store."""

    def test_facade_results_are_current_on_every_authorized_store(self):
        for label, prepare in _authorized_stores():
            for pinned in (None, "1.0.0"):
                with self.subTest(store=label, store_open_contract=pinned), tempfile.TemporaryDirectory() as temp:
                    with prepare(temp)(store_open_contract=pinned) as memory:
                        written = memory.remember("memory:release", "release branch is cut on Fridays")
                        self.assertTrue(written["committed"], written)
                        recalled = memory.recall("release branch")
                        history = memory.history("memory:release")
                    for result in (written, recalled, history):
                        self.assertEqual(result["contract_version"], "1.6.0")
                        self.assertEqual(result["compatibility"], contract.CURRENT)
                    self.assertEqual(len(recalled["returned"]), 1, recalled)
                    self.assertEqual(recalled["admitted"], recalled["returned"])

    def test_every_1x_envelope_runs_through_the_surface_on_every_authorized_store(self):
        proposal = _fixture("proposal-envelope.example.json")
        context = _fixture("recall-context.example.json")
        target = _fixture("target-envelope.example.json")
        for label, prepare in _authorized_stores():
            with self.subTest(store=label), tempfile.TemporaryDirectory() as temp:
                with prepare(temp)() as memory:
                    adapter = memory.runtime.adapter
                    for version in ENVELOPE_VERSIONS:
                        stamped = [dict(envelope, contract_version=version)
                                   for envelope in (proposal, context, target)]
                        results = (
                            surface.propose(adapter, stamped[0]),
                            surface.recall(adapter, "release", stamped[1]),
                            surface.history(adapter, stamped[2]),
                        )
                        for stage, result in zip(("proposal", "recall", "history"), results):
                            self.assertEqual(result["compatibility"], contract.CURRENT, (version, stage))
                            self.assertEqual(result["stage"], stage, (version, stage))
                            self.assertNotIn("validation_error", result, (version, stage))

    def test_envelope_states_outside_1x_are_unchanged_on_an_authorized_store(self):
        proposal = _fixture("proposal-envelope.example.json")
        with tempfile.TemporaryDirectory() as temp, _open(temp, store_open_contract="1.0.0") as memory:
            adapter = memory.runtime.adapter
            for version, state in (("1.7.0", contract.MIGRATION_REQUIRED), ("2.0.0", contract.INCOMPATIBLE),
                                   ("x", contract.UNKNOWN)):
                result = surface.propose(adapter, dict(proposal, contract_version=version))
                self.assertEqual((result["compatibility"], result["stage"]), (state, "none"), version)

    def test_a_1x_proposal_envelope_commits_durably_on_an_authorized_store(self):
        # The durable composition, not the bare adapter (a host object), is the write path
        # for an opened store; the envelope is gated and converted exactly as the surface does.
        proposal = copy.deepcopy(_fixture("proposal-envelope.example.json"))
        proposal["contract_version"] = "1.0.0"
        self.assertEqual(contract.compatibility(proposal), contract.CURRENT)
        validated = contract.validate_proposal_envelope(proposal)
        target = proposal["target_reference"]
        with tempfile.TemporaryDirectory() as temp:
            with _open(temp) as memory:
                outcome = memory.runtime.retain(contract.proposal_from_envelope(validated),
                                                "release branch is cut on Fridays")
                self.assertTrue(outcome.committed, outcome)
                written = outcome.fact_uuid
            with _open(temp) as reopened:
                self.assertEqual(reopened.runtime.adapter.current_fact_uuid(target), written)
                self.assertEqual(reopened.history(target)["compatibility"], contract.CURRENT)
            with self.assertRaises(StoreIdentityError):
                _open(temp, scope=OTHER)


class UnauthorizedAccessFailsClosedTests(unittest.TestCase):
    """No store-open or envelope version restores multi-project access to a store."""

    def assert_refused(self, temp, scopes, **kwargs) -> None:
        before = _state(temp)
        for scope in scopes:
            with self.subTest(scope=scope, **{k: str(v) for k, v in kwargs.items()}):
                with self.assertRaises(StoreIdentityError):
                    _open(temp, scope=scope, **kwargs)
        self.assertEqual(_state(temp), before, "a refused open mutated the store")

    def test_single_project_store_refuses_other_projects_under_every_accepted_declaration(self):
        with tempfile.TemporaryDirectory() as temp:
            with _open(temp) as owner:
                owner.remember("memory:k", "owner value")
            for pinned in (None, "1.0.0", "1.0.3"):
                self.assert_refused(temp, (OTHER, "project:third"), store_open_contract=pinned)
            self.assert_refused(temp, (OTHER,), store_profile=STORE_PROFILE_SCOPE_DISTINCT)

    def test_legacy_multi_project_store_is_refused_for_every_project_and_left_untouched(self):
        with tempfile.TemporaryDirectory() as temp:
            for scope in (PROJECT, OTHER):
                with open_tenant_wide(temp, tenant=TENANT, scope=scope) as handle:
                    self.assertTrue(handle.remember(f"memory:{scope}", f"{scope} value")["committed"])
            self.assertFalse((Path(temp) / STORE_PROFILE_FILE).exists())
            for pinned in (None, "1.0.0"):
                self.assert_refused(temp, (PROJECT, OTHER, "project:third"), store_open_contract=pinned)
            for profile in (STORE_PROFILE_SINGLE_PROJECT, STORE_PROFILE_SCOPE_DISTINCT):
                self.assert_refused(temp, (PROJECT, OTHER), store_profile=profile)
            self.assertFalse((Path(temp) / STORE_PROFILE_FILE).exists(), "a legacy store was migrated")

    def test_legacy_single_project_store_stays_restricted(self):
        with tempfile.TemporaryDirectory() as temp:
            _legacy_single_project(temp)
            with _open(temp, store_open_contract="1.0.0") as memory:
                self.assertEqual(memory.store_profile, STORE_PROFILE_LEGACY)
            self.assert_refused(temp, (OTHER,))
            self.assert_refused(temp, (PROJECT,), store_profile=STORE_PROFILE_SCOPE_DISTINCT)
            self.assertFalse((Path(temp) / STORE_PROFILE_FILE).exists(), "a legacy store was migrated")

    def test_non_current_host_declarations_are_refused_before_the_filesystem_is_touched(self):
        for pinned in ("1.1.0", "2.0.0", "0.9.0", "1.0", "latest", ""):
            with self.subTest(store_open_contract=pinned), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "never-created"
                with self.assertRaises(StoreIdentityError):
                    _open(root, store_open_contract=pinned)
                self.assertFalse(root.exists())

    def test_non_current_declarations_are_refused_on_an_existing_store_without_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            with _open(temp) as owner:
                owner.remember("memory:k", "owner value")
            self.assert_refused(temp, (PROJECT, OTHER), store_open_contract="2.0.0")
            self.assert_refused(temp, (PROJECT, OTHER), store_open_contract="1.1.0")
            _open(temp).close()  # the owner is unaffected

    def test_a_record_from_a_newer_store_open_contract_is_never_opened_or_rewritten(self):
        with tempfile.TemporaryDirectory() as temp:
            with _open(temp) as owner:
                owner.remember("memory:k", "owner value")
            path = Path(temp) / STORE_PROFILE_FILE
            record = json.loads(path.read_text(encoding="utf-8"))
            record["version"] = 2
            path.write_text(json.dumps(record), encoding="utf-8")
            before = path.read_bytes()
            for scope in (PROJECT, OTHER):
                with self.subTest(scope=scope):
                    with self.assertRaisesRegex(StoreIdentityError, "newer store-open contract"):
                        _open(temp, scope=scope)
            self.assert_refused(temp, (PROJECT, OTHER))
            self.assertEqual(path.read_bytes(), before)

    def test_records_with_unknown_versions_are_malformed(self):
        for version in (0, "1", None, True, 1.0001):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as temp:
                _open(temp).close()
                path = Path(temp) / STORE_PROFILE_FILE
                record = json.loads(path.read_text(encoding="utf-8"))
                record["version"] = version
                path.write_text(json.dumps(record), encoding="utf-8")
                with self.assertRaisesRegex(StoreIdentityError, "malformed"):
                    _open(temp)

    def test_refusals_are_recovery_errors_hosts_already_handle(self):
        self.assertTrue(issubclass(StoreIdentityError, RuntimeRecoveryError))


if __name__ == "__main__":
    unittest.main()
