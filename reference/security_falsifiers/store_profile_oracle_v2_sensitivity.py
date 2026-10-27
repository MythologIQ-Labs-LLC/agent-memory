"""Sensitivity of the #786 store-profile oracle v2 to injected regressions.

An oracle that cannot fail is decoration. Each regression below disables one defence the
oracle claims to cover; the oracle must fail under every one marked ``must_detect``.
Regressions outside the oracle's matched-control method are listed with the suite that
covers them instead, and reported rather than counted as detections.

    PYTHONPATH=reference python reference/security_falsifiers/store_profile_oracle_v2_sensitivity.py
"""
from __future__ import annotations

import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

from agentmem_ref.api import surface
from agentmem_ref.runtime import adapter as adapter_module
from agentmem_ref.runtime.adapter import GovernedMemoryAdapter
from agentmem_ref.runtime.sqlite_composition import SQLiteConfiguredCompositionRuntime

ORACLE = Path(__file__).with_name("test_786_store_profile_oracle_v2.py")


def _non_exclusive_claim(path, record):
    path.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")  # last writer wins
    return record


def _create_refuses_existing_file(original):
    def create(cls, root, **kwargs):
        if (Path(root) / "agent-memory.sqlite3").exists():
            raise surface.RuntimeRecoveryError("required SQLite runtime state is missing")
        return original.__func__(cls, root, **kwargs)
    return classmethod(create)


def _canonical_keys_pass_through(self, target_reference):
    if isinstance(target_reference, str) and target_reference.startswith("scope-key-v1:"):
        return target_reference
    return REAL_TARGET(self, target_reference)


REAL_TARGET = surface.AgentMemory._target

REGRESSIONS = [
    # name, patcher factory, must_detect, note
    ("key binding disabled", lambda: mock.patch.object(surface.AgentMemory, "_target", lambda self, t: str(t)), True, ""),
    ("single-project binding ignored", lambda: mock.patch.object(surface, "_check_store_identity", lambda record, **kw: None), True, ""),
    ("non-exclusive identity claim", lambda: mock.patch.object(surface, "_claim_store_identity", _non_exclusive_claim), True, ""),
    ("record not checked against canonical state",
     lambda: mock.patch.object(GovernedMemoryAdapter, "canonical_project_refs", lambda self: frozenset()), True, ""),
    ("gate eligibility after binding detail",
     lambda: mock.patch.object(GovernedMemoryAdapter, "_proposal_scope_eligible", lambda self, p, u, g: True), True, ""),
    ("override validation removed",
     lambda: mock.patch.object(surface.AgentMemory, "_check_overrides", lambda self, o: None), True, ""),
    ("canonical keys accepted as public keys",
     lambda: mock.patch.object(surface.AgentMemory, "_target", _canonical_keys_pass_through), True, ""),
    ("interrupted creation not completed",
     lambda: mock.patch.object(SQLiteConfiguredCompositionRuntime, "create",
                               _create_refuses_existing_file(SQLiteConfiguredCompositionRuntime.create)), True, ""),
    ("unavailable-target composition reverted",
     lambda: mock.patch.object(adapter_module, "_UNAVAILABLE_TARGET_REFUSALS", frozenset({"write_target_unavailable"})),
     False, "foreign and absent ids both refuse as fact_not_found either way; receipt state hiding is covered by "
            "tests.test_786_runtime_identity_security"),
    ("history eligibility disabled",
     lambda: mock.patch.object(GovernedMemoryAdapter, "history_eligible", lambda self, m, c: True),
     False, "scope-distinct keys already confine history to the caller's namespace; tenant-wide history isolation is "
            "covered by tests.test_786_runtime_identity_security and tests.test_786_runtime_cross_scope_recall_regression"),
]


def _load_oracle():
    spec = importlib.util.spec_from_file_location("store_profile_oracle_v2", ORACLE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_oracle() -> unittest.TestResult:
    suite = unittest.defaultTestLoader.loadTestsFromModule(_load_oracle())
    return unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)


def main() -> int:
    baseline = _run_oracle()
    print(f"baseline: {baseline.testsRun} tests, {len(baseline.failures)} failures, {len(baseline.errors)} errors")
    if not baseline.wasSuccessful():
        print("oracle is not green on the unmodified runtime; sensitivity is meaningless")
        return 2
    missed = []
    for name, patcher, must_detect, note in REGRESSIONS:
        with patcher():
            result = _run_oracle()
        detected = not result.wasSuccessful()
        failing = sorted({test.id().rsplit(".", 1)[-1] for test, _ in result.failures + result.errors})
        status = "DETECTED" if detected else ("MISSED" if must_detect else "not in scope")
        print(f"{status:13} {name}: {len(result.failures)}F/{len(result.errors)}E {failing[:4]}{' ' + note if note else ''}")
        if must_detect and not detected:
            missed.append(name)
    if missed:
        print("oracle missed regressions:", missed)
        return 1
    print("every must-detect regression was detected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
