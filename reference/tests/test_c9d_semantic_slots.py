"""#819 C9-D: the semantic route's bounded slots exclude memories admission refuses.

Preregistered in ``reports/benchmarks/memory-quality/819-c9-discovery/PREREGISTRATION-C9D.md``.
C4 ranks every domain-eligible fact, keeps the top ``SEMANTIC_CANDIDATE_LIMIT`` above the floor,
and only then lets admission refuse superseded, forgotten or disputed ones, so refused versions can
take every slot and hide an admissible memory. C9-D applies admission's own refusal, in the
recall's admission mode, before the cut (``relevance_sufficient`` only).

A table representation fixes every cosine, and no memory shares a token with the query, so only
the semantic route can discover anything. Tests marked FAIL-FIRST fail on C4 ``bc2be631``.
"""

from __future__ import annotations

import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.api.surface import SEMANTIC_CANDIDATE_LIMIT  # noqa: E402
from agentmem_ref.memory import procedural_memory as pm  # noqa: E402
from agentmem_ref.runtime import representation_onnx  # noqa: E402
from agentmem_ref.runtime.adapter import GovernedMemoryAdapter  # noqa: E402
from agentmem_ref.runtime.vector_retrieval import VectorRepresentationSpec  # noqa: E402

TENANT = "tenant:c9d"
SCOPE = "user:c9d"
QUERY = "Which harbour light flashes green?"
TARGET = "The lighthouse on Pell Point blinks emerald."
DECOYS = [f"Archived jotting {i} concerning zephyr{i}." for i in range(SEMANTIC_CANDIDATE_LIMIT)]


class _TableRepresentation:
    """Cosine with ``QUERY`` is ``TABLE[text]``; every other text is orthogonal to it."""

    TABLE: dict[str, float] = {}
    spec = VectorRepresentationSpec(
        representation_ref="test:c9d-table", representation_version="1.0.0",
        config_digest="sha256:" + "c9" * 32, dimensions=4, deterministic_rebuild=True,
    )

    def __init__(self, model_dir=None) -> None:
        pass

    def embed(self, text: str) -> tuple[float, ...]:
        if text == QUERY:
            return (1.0, 0.0, 0.0, 0.0)
        cosine = self.TABLE.get(text, 0.0)
        return (cosine, math.sqrt(1.0 - cosine * cosine), 0.0, 0.0)


def _evidence():
    skill = pm.SkillArtifact(skill_id="skill:c9d", version=1, purpose="apply a lifecycle change", scope=SCOPE,
                             isolation_domain_refs=(TENANT, SCOPE), required_isolation_domain_refs=(TENANT, SCOPE),
                             procedure_markdown="# verify\nConfirm.", provenance_refs=("evidence:c9d",))
    return pm.evidence_for(skill)


class SemanticSlotTests(unittest.TestCase):
    semantic = "required"

    def setUp(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        patcher = mock.patch.object(representation_onnx, "OnnxSentenceEmbeddingProvider", _TableRepresentation)
        patcher.start()
        self.addCleanup(patcher.stop)
        _TableRepresentation.TABLE = {TARGET: 0.5, **{text: 0.9 for text in DECOYS}}
        self.memory = AgentMemory.open(self.root, tenant=TENANT, actor_id="agent:c9d", scope=SCOPE,
                                       purpose="c9d qualification", semantic_retrieval=self.semantic)
        self.addCleanup(self.memory.close)

    def remember(self, ref: str, text: str) -> str:
        outcome = self.memory.remember(ref, text)
        self.assertTrue(outcome["committed"], outcome)
        return outcome["fact_uuid"]

    def forget_decoys(self) -> list[str]:
        uuids = [self.remember(f"memory:decoy-{i}", text) for i, text in enumerate(DECOYS)]
        for i in range(len(DECOYS)):
            self.assertTrue(self.memory.forget(f"memory:decoy-{i}", evidence=_evidence())["committed"])
        return uuids

    def supersede_decoys(self) -> None:
        """Four memories corrected four times: 16 superseded versions above the target, current ones below."""
        for i in range(4):
            texts = DECOYS[4 * i:4 * i + 4] + [f"Current jotting {i} concerning quokka{i}."]
            _TableRepresentation.TABLE[texts[-1]] = 0.1
            self.remember(f"memory:living-{i}", texts[0])
            for text in texts[1:]:
                self.assertTrue(self.memory.correct(f"memory:living-{i}", text, evidence=_evidence())["committed"])

    def test_forgotten_memories_do_not_take_the_targets_slot(self) -> None:  # FAIL-FIRST
        forgotten = self.forget_decoys()
        target = self.remember("memory:target", TARGET)
        result = self.memory.recall(QUERY, budget=5)
        self.assertIn(target, result["candidates"])
        self.assertEqual(result["returned"], [target])
        self.assertFalse(set(forgotten) & set(result["candidates"]))

    def test_superseded_versions_do_not_take_the_targets_slot(self) -> None:  # FAIL-FIRST
        self.supersede_decoys()
        target = self.remember("memory:target", TARGET)
        result = self.memory.recall(QUERY, budget=5)
        self.assertIn(target, result["returned"])
        texts = {self.memory.runtime.adapter.checkpoint_substrate().get_fact(u).fact_text for u in result["returned"]}
        self.assertFalse(texts & set(DECOYS), "a superseded version was returned")

    def test_historical_recall_keeps_superseded_state_changes(self) -> None:  # FAIL-FIRST
        # Forgotten decoys squat in both modes; a state change superseded below them is historical evidence.
        self.forget_decoys()
        _TableRepresentation.TABLE["Old jotting concerning wombat."] = 0.6
        self.remember("memory:state", "Old jotting concerning wombat.")
        _TableRepresentation.TABLE["New jotting concerning numbat."] = 0.1
        self.assertTrue(self.memory.correct("memory:state", "New jotting concerning numbat.", evidence=_evidence(),
                                            replacement_kind="state_change")["committed"])
        substrate = self.memory.runtime.adapter.checkpoint_substrate()
        historical = self.memory.recall(QUERY, temporal_intent={"mode": "historical"})
        found = {substrate.get_fact(u).fact_text for u in historical["admitted"]}
        self.assertIn("Old jotting concerning wombat.", found)
        current = self.memory.recall(QUERY)
        self.assertNotIn("Old jotting concerning wombat.",
                         {substrate.get_fact(u).fact_text for u in current["candidates"]})

    def test_refusal_is_evaluated_in_the_recalls_admission_mode(self) -> None:
        self.remember("memory:target", TARGET)
        modes = []
        original = GovernedMemoryAdapter.discovery_refusal

        def spy(adapter, fact, context, mode="current_state", target_seconds=None):
            modes.append(mode)
            return original(adapter, fact, context, mode, target_seconds)

        with mock.patch.object(GovernedMemoryAdapter, "discovery_refusal", spy):
            self.memory.recall(QUERY)
            current = set(modes)
            modes.clear()
            self.memory.recall(QUERY, temporal_intent={"mode": "historical"})
        self.assertEqual(current, {"current_state"})
        self.assertEqual(set(modes), {"historical_evidence"})

    def test_ranked_prefix_keeps_the_pre_c9_route(self) -> None:
        forgotten = self.forget_decoys()
        target = self.remember("memory:target", TARGET)
        result = self.memory.recall(QUERY, return_selection="ranked_prefix")
        self.assertNotIn(target, result["candidates"])
        refused = {u for u, d in result["admissions"].items() if d.get("refusal")}
        self.assertEqual(refused, set(forgotten))
        self.assertEqual(result["returned"], [])

    def test_no_slot_change_without_refusable_memories(self) -> None:
        uuids = [self.remember(f"memory:live-{i}", text) for i, text in enumerate(DECOYS)]
        target = self.remember("memory:target", TARGET)
        default = self.memory.recall(QUERY)
        prefix = self.memory.recall(QUERY, return_selection="ranked_prefix")
        self.assertEqual(set(default["candidates"]), set(uuids))
        self.assertEqual(default["candidates"], prefix["candidates"])
        self.assertNotIn(target, default["candidates"])


class RouteOffTests(unittest.TestCase):
    def test_route_off_never_reads_discovery_refusal(self) -> None:
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(
                GovernedMemoryAdapter, "discovery_refusal", side_effect=AssertionError("read")):
            with AgentMemory.open(Path(folder), tenant=TENANT, actor_id="agent:c9d", scope=SCOPE,
                                  purpose="c9d qualification") as memory:
                memory.remember("memory:target", TARGET)
                self.assertEqual(memory.recall(QUERY)["returned"], [])


if __name__ == "__main__":
    unittest.main()
