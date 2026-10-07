"""The dogfood semantic replay compares probe semantics, not the runner's interpreter."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN = REPO_ROOT / "reports" / "gauntlet" / "external-contestant-v1" / "golden-evidence.json"


def _load():
    spec = importlib.util.spec_from_file_location("dogfood_equivalence", REPO_ROOT / "scripts" / "validate_gauntlet_dogfood_equivalence.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class StableNormalizedTests(unittest.TestCase):
    def test_execution_environment_is_execution_volatile(self):
        module = _load()
        golden = json.loads(GOLDEN.read_text(encoding="utf-8"))["normalized_run"]
        replay = json.loads(json.dumps(golden))
        replay["run_id"] = "gauntlet-replay-000000000000"
        replay["execution"]["environment"] = {"platform": "linux", "python": f"{sys.version_info[0]}.{sys.version_info[1]}.99"}
        replay["execution"]["started_at"] = "2026-01-01T00:00:00Z"
        first = {"manifest": None, "native": {}, "normalized": replay, "qualification": {}}
        checks = module._golden_checks(first, GOLDEN)
        self.assertTrue(checks["golden_normalized_semantics_equal"])

    def test_semantic_fields_still_compared(self):
        module = _load()
        golden = json.loads(GOLDEN.read_text(encoding="utf-8"))["normalized_run"]
        replay = json.loads(json.dumps(golden))
        replay["execution"]["selection_id"] = "all:0000000000000000"
        first = {"manifest": None, "native": {}, "normalized": replay, "qualification": {}}
        self.assertFalse(module._golden_checks(first, GOLDEN)["golden_normalized_semantics_equal"])


if __name__ == "__main__":
    unittest.main()
