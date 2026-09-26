from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentmem_ref._paths import REPO_ROOT
from agentmem_ref.evaluation.contract import load_run
from agentmem_ref.evaluation.gauntlet_orchestrator import run_gauntlet
from agentmem_ref.evaluation.gauntlet_profiles import GOVERNANCE_ALPHA_PROFILE_ID


FIXTURE = REPO_ROOT / "fixtures" / "gauntlet" / "agent-memory-public-governance-adapter.json"


def _cases(run: dict) -> dict[str, dict]:
    return {case["case_id"]: case for case in run["native_results"]["cases"]}


class AgentMemoryGovernanceGauntletTests(unittest.TestCase):
    def test_public_facade_is_evaluated_as_real_system_without_adapter_side_tenant_claim(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = run_gauntlet(
                FIXTURE,
                GOVERNANCE_ALPHA_PROFILE_ID,
                output_dir=Path(temporary) / "runs",
            )
            self.assertEqual(result["status"], "complete", result)

            run = load_run(result["artifacts"]["normalized_run"]["path"])
            cases = _cases(run)

            # This local public composition is deliberately not credited with claims
            # whose current alpha cases require a cross-tenant population. Adapter-side
            # tenant routing would manufacture the tested property.
            self.assertEqual(cases["GOV-ISO-001"]["result"], "unsupported")
            self.assertEqual(cases["GOV-ISO-005"]["result"], "unsupported")
            self.assertEqual(cases["GOV-AUTH-002"]["result"], "unsupported")
            self.assertEqual(cases["GOV-AUTH-003"]["result"], "unsupported")

            # These properties are exercised through the actual public facade and
            # canonical runtime, not implemented by the adapter.
            self.assertEqual(cases["GOV-ISO-002"]["result"], "pass", cases["GOV-ISO-002"])
            self.assertEqual(cases["GOV-DEL-001"]["result"], "pass", cases["GOV-DEL-001"])

            # Agent Memory claims restart-safe deletion, but the alpha is honest about
            # not yet having a neutral restart lifecycle operation to exercise it.
            self.assertEqual(cases["GOV-DEL-002"]["result"], "blocked")
            self.assertIn("restart/recovery lifecycle", cases["GOV-DEL-002"]["note"])

            self.assertEqual(run["system"]["kind"], "agent_memory")
            self.assertEqual(run["native_results"]["profile_kind"], "gauntlet_native_gap")
            self.assertEqual(run["authority_effect"], "none")
            self.assertEqual(run["dimensions"]["governance"]["status"], "partial")

            manifest = run["native_results"].get("manifest_capability_posture")
            if manifest is not None:
                self.assertEqual(manifest.get("tenant_isolation"), "unsupported")
                self.assertEqual(
                    manifest.get("foreign_cardinality_non_disclosure"), "unsupported"
                )


if __name__ == "__main__":
    unittest.main()
