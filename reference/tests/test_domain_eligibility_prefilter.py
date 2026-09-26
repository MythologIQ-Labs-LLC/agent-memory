"""#548 (#522 Part B): privacy-preserving domain-eligibility prefilter, contract 1.3.0.

    raw discovery matches -> domain-eligibility prefilter -> candidates
        -> full canonical governed admission -> admitted

The prefilter is a minimisation boundary, never permission. These tests prove:

* no domain-ineligible identifier reaches candidates, admissions, ranking evidence,
  route provenance, or the recall audit event, whatever route discovered it;
* no count of excluded matches is observable: adding foreign matching memories leaves
  the caller-visible recall result structurally identical;
* the prefilter never changes an admission outcome: admitted sets are identical with
  and without it, and admission still refuses everything the prefilter would exclude.
"""

from __future__ import annotations

import random
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.api import contract  # noqa: E402
from agentmem_ref.runtime.adapter import PREFILTER_POLICY_ID, PREFILTER_POLICY_VERSION  # noqa: E402
from agentmem_ref.runtime.contextual_recall_adapter import admit_preselected_candidates  # noqa: E402
from tests.prefilter_bypass import admission_only  # noqa: E402

TENANT = "tenant:prefilter"


def _open(root: str, scope: str) -> AgentMemory:
    return AgentMemory.open(root, tenant=TENANT, actor_id="agent:prefilter", scope=scope, purpose="prefilter tests")


def _write(root: str, scope: str, items: list[tuple[str, str]]) -> dict[str, str]:
    with _open(root, scope) as memory:
        return {key: memory.remember(key, text)["fact_uuid"] for key, text in items}


def _structure(result: dict, texts: dict[str, str]) -> dict:
    """Caller-visible recall shape with identifiers replaced by their memory text."""

    def name(ref: str) -> str:
        return texts.get(ref, "<unknown>")

    return {
        "candidates": sorted(name(ref) for ref in result["candidates"]),
        "admitted": [name(ref) for ref in result["admitted"]],
        "outcomes": sorted((name(ref), decision.get("outcome"), decision.get("reason_code")) for ref, decision in result["admissions"].items()),
        "candidate_policy": result.get("candidate_policy"),
    }


class PrefilterPrivacyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.root = self._temp.name
        self.own = _write(self.root, "project:own", [("memory:own:plan", "The release plan is Alder."), ("memory:own:note", "Release notes live in the wiki.")])
        self.foreign = _write(self.root, "project:foreign", [("memory:foreign:plan", "The release plan is Zelkova."), ("memory:foreign:secret", "Release secret plan codename Quartz.")])

    def tearDown(self) -> None:
        self._temp.cleanup()

    def _recall(self, **kwargs) -> dict:
        with _open(self.root, "project:own") as memory:
            result = memory.recall("release plan", **kwargs)
            events = [event for event in memory.runtime.adapter.events if event.get("event_type") == "memory.recall"]
        return result, events[-1]

    def test_foreign_lexical_matches_leave_no_trace(self):
        result, event = self._recall()
        foreign_ids = set(self.foreign.values())
        visible = set(result["candidates"]) | set(result["admitted"]) | set(result["admissions"])
        self.assertFalse(foreign_ids & visible)
        self.assertEqual(set(result["admitted"]), set(self.own.values()))
        for decision in result["admissions"].values():
            for hit in decision.get("route_provenance", ()):
                self.assertNotIn(hit.get("candidate_ref"), foreign_ids)
        self.assertFalse(foreign_ids & set(event["payload"]["outcomes"]))
        self.assertEqual(event["payload"]["candidate_count"], len(result["candidates"]))
        self.assertEqual(event["payload"]["candidate_policy"], result["candidate_policy"])
        self.assertEqual(
            result["candidate_policy"],
            {
                "candidate_scope": "domain_eligible",
                "prefilter_policy_id": PREFILTER_POLICY_ID,
                "prefilter_policy_version": PREFILTER_POLICY_VERSION,
                "prefilter_authority": "none",
                "admission": "full_canonical_admission_on_every_candidate",
            },
        )
        self.assertEqual(result["contract_version"], contract.CONTRACT_VERSION)

    def test_exact_logical_reference_to_foreign_memory_is_not_a_candidate(self):
        result, _ = self._recall(logical_memory_refs=("memory:foreign:plan", "memory:foreign:secret"))
        self.assertFalse(set(self.foreign.values()) & set(result["candidates"]))

    def test_any_route_is_prefiltered_at_the_preselected_admission_seam(self):
        # Vector, graph, shared-evidence, and exact-identity routes all converge here.
        with _open(self.root, "project:own") as memory:
            adapter = memory.runtime.adapter
            context = contract.recall_context_from_envelope(
                {
                    "contract_version": contract.CONTRACT_VERSION,
                    "target_domain_refs": [TENANT, "project:own"],
                    "principal_ref": "agent:prefilter",
                    "project_ref": "project:own",
                    "purpose": "prefilter tests",
                }
            )
            refs = list(self.foreign.values()) + list(self.own.values()) + ["ref-does-not-exist"]
            result = admit_preselected_candidates(adapter, refs, context, query_label="injected")
        self.assertFalse(set(self.foreign.values()) & set(result.candidates))
        self.assertEqual(set(result.admitted), set(self.own.values()))
        self.assertEqual(result.refusals, {"ref-does-not-exist": "candidate_not_found"})

    def test_foreign_match_cardinality_is_not_observable(self):
        shapes = []
        for foreign_count in (0, 5):
            with tempfile.TemporaryDirectory() as root:
                own = _write(root, "project:own", [("memory:own:plan", "The release plan is Alder.")])
                _write(root, "project:foreign", [(f"memory:foreign:{i}", f"The release plan variant {i}.") for i in range(foreign_count)])
                with _open(root, "project:own") as memory:
                    shapes.append(_structure(memory.recall("release plan"), {ref: key for key, ref in own.items()}))
        # Identifiers differ between the two stores; the caller-visible structure must not.
        self.assertEqual(shapes[0], shapes[1])


class PrefilterNeverChangesAdmissionTests(unittest.TestCase):
    def test_admitted_sets_are_identical_with_and_without_the_prefilter(self):
        rng = random.Random(548)
        words = ["release", "plan", "deploy", "window", "owner", "budget", "policy", "notes"]
        scopes = [f"project:{i}" for i in range(4)]
        with tempfile.TemporaryDirectory() as root:
            for scope in scopes:
                _write(root, scope, [(f"memory:{scope}:{i}", " ".join(rng.choices(words, k=5))) for i in range(12)])
            for scope in scopes[:2]:
                with _open(root, scope) as memory:
                    for _ in range(10):
                        query = " ".join(rng.choices(words, k=2))
                        default = memory.recall(query)
                        with admission_only():
                            bypassed = memory.recall(query)
                        self.assertEqual(default["admitted"], bypassed["admitted"], query)
                        # Everything the prefilter excluded is refused by admission itself.
                        excluded = set(bypassed["candidates"]) - set(default["candidates"])
                        self.assertTrue(excluded.isdisjoint(bypassed["admitted"]))
                        for ref in excluded:
                            self.assertIn(
                                bypassed["admissions"][ref]["refusal"],
                                {"isolation_domain_mismatch", "required_isolation_domain_missing", "project_scope_mismatch",
                                 "task_scope_mismatch", "shared_space_non_member", "shared_space_membership_unresolved",
                                 "unknown_scope", "out_of_scope"},
                            )


if __name__ == "__main__":
    unittest.main()
