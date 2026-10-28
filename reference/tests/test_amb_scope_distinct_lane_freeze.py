"""Pre-score freeze and protocol equivalence guards for the v7 AMB successor.

No external benchmark execution happens here. The original blocked v7 lane is
immutable, and the new lane may execute only after independent pre-score review.
"""
from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


REFERENCE = Path(__file__).resolve().parents[1]
ROOT = REFERENCE.parent
LANES = REFERENCE / "agentmem_ref" / "evaluation" / "lanes"
OLD_PATH = LANES / "amb-precisionmembench-retrieval-v7.json"
NEW_PATH = ROOT / "reports/validation/v7-integration/amb-scope-distinct-successor/amb-precisionmembench-retrieval-v7-scope-distinct-v1.json"
OLD_BRIDGE = "reference/amb_agent_memory_bridge.py"
NEW_BRIDGE = "reference/amb_agent_memory_bridge_scope_distinct.py"
NEW_RUNNER = "reference/run_amb_external_scope_distinct.py"
DECLARATION_BLOB = "981108866e45a46b9e96ab283517324d6349e586"


def _blob(path: Path) -> str:
    return subprocess.run(
        ["git", "hash-object", "--no-filters", str(path)],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.strip()


class AmbScopeDistinctLaneFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = json.loads(OLD_PATH.read_text(encoding="utf-8"))
        cls.new = json.loads(NEW_PATH.read_text(encoding="utf-8"))

    def test_distinct_frozen_identity_and_no_prior_accepted_score(self):
        self.assertEqual(self.old["lane_id"], "amb-precisionmembench-retrieval-v7")
        self.assertEqual(self.old["status"], "frozen")
        self.assertEqual(self.new["lane_id"], "amb-precisionmembench-retrieval-v7-scope-distinct-v1")
        self.assertEqual(self.new["status"], "frozen")
        self.assertTrue(self.new["frozen_before_any_score"])
        self.assertEqual(self.new["frozen_on"], "2026-10-28")
        self.assertEqual(
            {row["row_id"]: row["status"] for row in self.new["systems"]},
            {row["row_id"]: row["status"] for row in self.old["systems"]},
        )

    def test_no_dataset_selection_budget_gold_or_scorer_changes(self):
        for key in ("contract_family", "contract_version", "owning_issue",
                    "benchmark_integration", "dataset", "selection", "budget",
                    "gold_identity", "evaluator", "deferred_lanes"):
            with self.subTest(key=key):
                if key == "dataset":
                    before = dict(self.old[key])
                    after = dict(self.new[key])
                    # Additional disclosure only; preserve every frozen dataset field.
                    before.pop("notes", None)
                    after.pop("notes", None)
                    self.assertEqual(before, after)
                else:
                    self.assertEqual(self.old[key], self.new[key])
        for key in ("repository", "url", "revision", "package", "license_spdx", "entry"):
            self.assertEqual(self.old["harness"][key], self.new["harness"][key], key)
        for key in ("concurrency", "timeout", "failure_handling"):
            self.assertEqual(self.old["execution"][key], self.new["execution"][key], key)

    def test_old_bridge_and_lane_unmodified_and_new_adapter_pinned(self):
        self.assertEqual(_blob(ROOT / OLD_BRIDGE), "3d9ccb31587b55edf4ddb714d6e8ff41d5b03228")
        source = self.new["harness"]["source_blobs"]
        self.assertNotIn(OLD_BRIDGE, source)
        self.assertEqual(source[NEW_BRIDGE], _blob(ROOT / NEW_BRIDGE))
        self.assertEqual(source[NEW_RUNNER], _blob(ROOT / NEW_RUNNER))
        for name, sha in self.old["harness"]["source_blobs"].items():
            if name != OLD_BRIDGE:
                self.assertEqual(source[name], sha, name)
        control = next(row for row in self.new["systems"] if row["row_id"] == "agent-memory-public-facade")
        self.assertEqual(control["adapter"]["module"], NEW_BRIDGE)
        self.assertEqual(control["adapter"]["install_entry"],
                         "amb_agent_memory_bridge_scope_distinct.install_amb_agent_memory_provider")
        self.assertEqual(control["configuration"]["store_open_profile"].split()[0],
                         "scope_distinct_v1")

    def test_both_lanes_bind_same_integrated_v7_declaration(self):
        for lane in (self.old, self.new):
            control = next(row for row in lane["systems"] if row["row_id"] == "agent-memory-public-facade")
            self.assertEqual(control["configuration"]["runtime_baseline_posture"]["declaration_blob"],
                             DECLARATION_BLOB)
        self.assertEqual(_blob(ROOT / "reports/runtime/baseline-v7-declaration.json"), DECLARATION_BLOB)

    def test_candidate_lane_preserves_mesa_v5_exact_package_tree(self):
        self.assertTrue(NEW_PATH.is_file())
        self.assertFalse((LANES / NEW_PATH.name).exists(),
                         "candidate lane must not mutate agentmem_ref before MESA-v5 execution")
        freeze = json.loads((
            ROOT / "reference/fixtures/benchmarks/agentmembench/mesa-formal-v5-freeze.json"
        ).read_text(encoding="utf-8"))
        tree = subprocess.run(
            ["git", "rev-parse", "HEAD:reference/agentmem_ref"], cwd=ROOT,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        self.assertEqual(freeze["agent_memory"]["runtime_tree"], tree)
        self.assertEqual(tree, "975b09412b096a9eac4a92478e7d3a39700ba5d9")

    def test_successor_bridge_only_changes_explicit_store_profile_and_version(self):
        old = (ROOT / OLD_BRIDGE).read_text(encoding="utf-8")
        new = (ROOT / NEW_BRIDGE).read_text(encoding="utf-8")
        expected = old.replace(
            '"""Agent Memory provider bridge for vectorize-io/agent-memory-benchmark (AMB).',
            '"""Scope-distinct successor of the frozen 0.4.0 Agent Memory AMB bridge.\n\n'
            'This is a NEW, separately pinned benchmark adapter. Do not replace the historical\n'
            'reference/amb_agent_memory_bridge.py or its frozen lane. Store-open contract 1.0.0\n'
            'requires one explicit scope_distinct_v1 root for the benchmark\'s multiple project\n'
            'scopes. Ingestion and retrieval use the same bound profile. No tenant-wide opener,\n'
            'per-case scope override or per-user independent SQLite root is introduced.\n\n'
            'Original bridge: Agent Memory provider bridge for vectorize-io/agent-memory-benchmark (AMB).',
            1,
        )
        expected = expected.replace(
            "from agentmem_ref import AgentMemory\n",
            "from agentmem_ref import AgentMemory\n"
            "from agentmem_ref.api.surface import STORE_PROFILE_SCOPE_DISTINCT\n", 1,
        )
        expected = expected.replace('BRIDGE_VERSION = "0.4.0"',
                                    'BRIDGE_VERSION = "0.5.0"', 1)
        expected = expected.replace(
            "                    purpose=_PURPOSE,\n                ) as memory:",
            "                    purpose=_PURPOSE,\n"
            "                    store_profile=STORE_PROFILE_SCOPE_DISTINCT,\n"
            "                ) as memory:", 1,
        )
        expected = expected.replace(
            "                purpose=_PURPOSE,\n                **open_kwargs,\n            ) as memory:",
            "                purpose=_PURPOSE,\n"
            "                store_profile=STORE_PROFILE_SCOPE_DISTINCT,\n"
            "                **open_kwargs,\n            ) as memory:", 1,
        )
        self.assertEqual(new, expected)


if __name__ == "__main__":
    unittest.main()
