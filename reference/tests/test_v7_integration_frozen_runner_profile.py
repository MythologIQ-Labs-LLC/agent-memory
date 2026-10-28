"""v7 integration: why frozen replay evidence needs fresh qualification on the integrated tree.

The frozen #786/#809 security replay runners and the #644 replay runner open several projects in
one SQLite root through ``AgentMemory.open``. Under the integrated store-open contract 1.0.0 the
default ``single_project_v1`` profile refuses the second project before a case runs, so those
runners cannot re-record their committed evidence unchanged. A runner whose cases stay inside one
project is unaffected. The same case passes once only the runner's opener is routed to the
tenant-wide fixture, so the stop is the store profile, not a regression of the canonical guards.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import run_644_v7_replays as replay_runner  # noqa: E402  (reference/ is the test top-level directory)
import run_786_security_replays as security_root  # noqa: E402
import run_786_security_replays_dsl2 as security_runner  # noqa: E402
from tests._tenant_wide_fixture import FrozenRunnerOpener  # noqa: E402


def _case(runner, replay_id: str, case_id: str) -> dict:
    fixture = json.loads((runner.FIXTURE_DIR / f"{replay_id}.json").read_text(encoding="utf-8"))
    return next(case for case in fixture["cases"] if case["id"] == case_id)


def _run(runner, case: dict, opener_module=None) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        if opener_module is None:
            return runner.run_case(case, Path(tmp))
        with mock.patch.object(opener_module, "AgentMemory", FrozenRunnerOpener):
            return runner.run_case(case, Path(tmp))


class FrozenRunnerStoreProfileTests(unittest.TestCase):
    def test_default_profile_stops_a_multi_project_security_runner_before_the_case_runs(self):
        case = _case(security_runner, "cross-scope-write-authority-denial-v3", "W1-remember-over-live-head")
        result = _run(security_runner, case)
        self.assertEqual(result["outcome"], "error")
        self.assertIn("StoreIdentityError", json.dumps(result))

    def test_the_same_case_passes_when_only_the_opener_is_tenant_wide(self):
        case = _case(security_runner, "cross-scope-write-authority-denial-v3", "W1-remember-over-live-head")
        self.assertEqual(_run(security_runner, case, security_root)["outcome"], "pass")

    def test_default_profile_stops_the_multi_project_644_admission_case(self):
        case = _case(replay_runner, "governed-persisted-typed-slot-sufficiency-admission-recheck-v1",
                     "A6-hidden-admissible-competitor-counted")
        self.assertNotEqual(_run(replay_runner, case)["outcome"], "pass")
        self.assertEqual(_run(replay_runner, case, replay_runner)["outcome"], "pass")

    def test_a_single_project_644_case_is_unaffected_by_the_profile(self):
        case = _case(replay_runner, "committed-governed-transition-witness-v1", "T1-asserted-change-only")
        self.assertEqual(_run(replay_runner, case)["outcome"], "pass")


if __name__ == "__main__":
    unittest.main()
