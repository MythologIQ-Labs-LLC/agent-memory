"""Sensitivity of the #786 store-open contract tests to injected regressions.

``tests.test_786_store_open_contract`` claims two things: 1.x envelopes stay compatible on
every authorized store, and no declaration restores multi-project access. Each regression
below breaks one of those claims, and a *behavioural* test (one that opens real SQLite
stores) must fail under every regression marked ``must_detect``. Failures of the pure
version-table tests alone do not count as detection.

    PYTHONPATH=reference python reference/security_falsifiers/store_open_contract_sensitivity.py
"""
from __future__ import annotations

import io
import sys
import unittest
from unittest import mock

from agentmem_ref.api import contract, store_contract, surface
from agentmem_ref.runtime.adapter import GovernedMemoryAdapter

from tests import test_786_store_open_contract as subject

BEHAVIOURAL = (
    "EnvelopeCompatibilityOnAuthorizedStoresTests",
    "UnauthorizedAccessFailsClosedTests",
)

REGRESSIONS = [
    # name, patcher factory, must_detect
    ("envelope contract promoted to 2.0.0 (1.x envelopes become incompatible)",
     lambda: mock.patch.object(contract, "CONTRACT_VERSION", "2.0.0"), True),
    ("envelope contract coupled to the store-open version",
     lambda: mock.patch.object(contract, "CONTRACT_VERSION", store_contract.STORE_OPEN_CONTRACT_VERSION), True),
    ("host store-open declaration ignored",
     lambda: mock.patch.object(store_contract, "compatibility", lambda version: store_contract.CURRENT), True),
    ("newer identity record accepted",
     lambda: mock.patch.object(store_contract, "RECORD_VERSION", 2), True),
    ("newer identity record reported as malformed (forward-version diagnosis lost)",
     lambda: mock.patch.object(store_contract, "record_compatibility", lambda version: store_contract.UNKNOWN), True),
    ("single-project binding ignored",
     lambda: mock.patch.object(surface, "_check_store_identity", lambda record, **kw: None), True),
    ("legacy restriction removed",
     lambda: mock.patch.object(GovernedMemoryAdapter, "canonical_project_refs", lambda self: frozenset()), True),
]


def _run() -> unittest.TestResult:
    suite = unittest.defaultTestLoader.loadTestsFromModule(subject)
    return unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)


def _failing(result: unittest.TestResult) -> list[str]:
    return sorted({test.id().split(".", 2)[-1] for test, _ in result.failures + result.errors})


def main() -> int:
    baseline = _run()
    print(f"baseline: {baseline.testsRun} tests, {len(baseline.failures)} failures, {len(baseline.errors)} errors")
    if not baseline.wasSuccessful():
        print("tests are not green on the unmodified runtime; sensitivity is meaningless")
        return 2
    missed = []
    for name, patcher, must_detect in REGRESSIONS:
        with patcher():
            result = _run()
        failing = _failing(result)
        behavioural = [test for test in failing if test.split(".", 1)[0] in BEHAVIOURAL]
        detected = bool(behavioural)
        status = "DETECTED" if detected else ("MISSED" if must_detect else "not in scope")
        print(f"{status:9} {name}: {len(behavioural)} behavioural of {len(failing)} failing {behavioural[:3]}")
        if must_detect and not detected:
            missed.append(name)
    if missed:
        print("missed regressions:", missed)
        return 1
    print(f"every must-detect regression was detected ({len(REGRESSIONS)}/{len(REGRESSIONS)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
