"""#819 C10: answerability-gated semantic proposals.

Preregistered in ``reports/benchmarks/memory-quality/819-c10/PREREGISTRATION-C10.md``. C4 proposes
every semantic hit above cosine 0.30 among the dense top 16, and every proposal is sufficient for
return; below the floor it reaches nothing. With ``semantic_answerability`` on, the route reads the
dense top 8 with no floor and proposes the best match above the floor plus each fact whose
answerability logit clears the scorer's floor.

A table representation fixes every cosine and a table scorer fixes every logit; no memory shares a
token with the query, so only the semantic route can discover anything. Tests marked FAIL-FIRST
fail (or error: the option does not exist) on C4 ``bc2be631``.
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
from agentmem_ref.memory import procedural_memory as pm  # noqa: E402
from agentmem_ref.runtime import representation_onnx  # noqa: E402
from agentmem_ref.runtime.vector_retrieval import VectorRepresentationSpec  # noqa: E402

TENANT = "tenant:c10"
SCOPE = "user:c10"
QUERY = "Which harbour light flashes green?"
ANSWER = "The lighthouse on Pell Point blinks emerald."
SIMILAR = "Ferry pilots keep lamps aboard their vessels."
UNRELATED = "Quinoa salad recipe uses lemon zest."


class _TableRepresentation:
    """Cosine with ``QUERY`` is ``TABLE[text]``; every other text is orthogonal to it."""

    TABLE: dict[str, float] = {}
    spec = VectorRepresentationSpec(
        representation_ref="test:c10-table", representation_version="1.0.0",
        config_digest="sha256:" + "c1" * 32, dimensions=4, deterministic_rebuild=True,
    )

    def __init__(self, model_dir=None) -> None:
        pass

    def embed(self, text: str) -> tuple[float, ...]:
        if text == QUERY:
            return (1.0, 0.0, 0.0, 0.0)
        cosine = self.TABLE.get(text, 0.0)
        return (cosine, math.sqrt(1.0 - cosine * cosine), 0.0, 0.0)


class _Spec:
    answerability_ref = "test:c10-scorer"
    answerability_version = "1.0.0"
    config_digest = "sha256:" + "a1" * 32
    logit_floor = 0.0
    authority_effect = "none"

    def to_dict(self) -> dict:
        return {"answerability_ref": self.answerability_ref, "logit_floor": self.logit_floor,
                "authority_effect": self.authority_effect}


class _TableScorer:
    """Logit for ``(QUERY, text)`` is ``TABLE[text]`` (default -5); records every scored batch."""

    TABLE: dict[str, float] = {}
    calls: list[tuple[str, tuple[str, ...]]] = []
    spec = _Spec()

    def __init__(self, model_dir=None, **_kwargs) -> None:
        pass

    def score(self, question, texts):
        _TableScorer.calls.append((question, tuple(texts)))
        return tuple(self.TABLE.get(text, -5.0) for text in texts)


def _evidence():
    skill = pm.SkillArtifact(skill_id="skill:c10", version=1, purpose="apply a lifecycle change", scope=SCOPE,
                             isolation_domain_refs=(TENANT, SCOPE), required_isolation_domain_refs=(TENANT, SCOPE),
                             procedure_markdown="# verify\nConfirm.", provenance_refs=("evidence:c10",))
    return pm.evidence_for(skill)


class _Base(unittest.TestCase):
    answerability = "qnli-electra-base"

    def setUp(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        for patcher in (mock.patch.object(representation_onnx, "OnnxSentenceEmbeddingProvider", _TableRepresentation),):
            patcher.start()
            self.addCleanup(patcher.stop)
        try:
            from agentmem_ref.runtime import answerability_onnx
        except ImportError:  # C4 has no answerability module: the gate's tests error there
            answerability_onnx = None
        if answerability_onnx is not None:
            patcher = mock.patch.object(answerability_onnx, "OnnxAnswerabilityScorer", _TableScorer)
            patcher.start()
            self.addCleanup(patcher.stop)
        _TableRepresentation.TABLE = {}
        _TableScorer.TABLE = {}
        _TableScorer.calls = []

    def open(self, scope: str = SCOPE, **options) -> AgentMemory:
        kwargs = {"semantic_retrieval": "required"}
        if self.answerability != "off":
            kwargs["semantic_answerability"] = self.answerability
        kwargs.update(options)
        memory = AgentMemory.open(self.root, tenant=TENANT, actor_id="agent:c10", scope=scope,
                                  purpose="c10 qualification", **kwargs)
        self.addCleanup(memory.close)
        return memory

    @staticmethod
    def remember(memory: AgentMemory, ref: str, text: str, cosine: float, logit: float | None = None) -> str:
        _TableRepresentation.TABLE[text] = cosine
        if logit is not None:
            _TableScorer.TABLE[text] = logit
        outcome = memory.remember(ref, text)
        assert outcome["committed"], outcome
        return outcome["fact_uuid"]


class AnswerabilityGateTests(_Base):
    def test_below_floor_answer_is_reached(self) -> None:  # FAIL-FIRST
        memory = self.open()
        answer = self.remember(memory, "memory:answer", ANSWER, cosine=0.2, logit=3.0)
        self.remember(memory, "memory:similar", SIMILAR, cosine=0.6, logit=-4.0)
        result = memory.recall(QUERY, budget=5)
        self.assertIn(answer, result["returned"])

    def test_similar_non_answer_beyond_best_match_is_not_proposed(self) -> None:  # FAIL-FIRST
        memory = self.open()
        best = self.remember(memory, "memory:best", ANSWER, cosine=0.7, logit=2.0)
        similar = self.remember(memory, "memory:similar", SIMILAR, cosine=0.6, logit=-4.0)
        result = memory.recall(QUERY, budget=5)
        self.assertEqual(result["returned"], [best])
        self.assertNotIn(similar, result["candidates"])

    def test_best_match_above_floor_keeps_the_ungated_rule(self) -> None:
        memory = self.open()
        best = self.remember(memory, "memory:best", SIMILAR, cosine=0.7, logit=-6.0)
        result = memory.recall(QUERY, budget=5)
        self.assertEqual(result["returned"], [best])

    def test_no_answer_abstains(self) -> None:  # FAIL-FIRST
        memory = self.open()
        self.remember(memory, "memory:a", SIMILAR, cosine=0.25, logit=-3.0)
        self.remember(memory, "memory:b", UNRELATED, cosine=0.1, logit=-7.0)
        result = memory.recall(QUERY, budget=5)
        self.assertEqual(result["returned"], [])

    def test_pool_is_the_dense_top_eight_in_order(self) -> None:  # FAIL-FIRST
        memory = self.open()
        texts = [f"Archived jotting {i} concerning zephyr{i}." for i in range(12)]
        for i, text in enumerate(texts):
            self.remember(memory, f"memory:j{i}", text, cosine=0.9 - 0.05 * i)
        far = self.remember(memory, "memory:far", ANSWER, cosine=0.05, logit=9.0)
        _TableScorer.calls = []
        result = memory.recall(QUERY, budget=5)
        scored = [batch for question, batch in _TableScorer.calls if question == QUERY]
        self.assertEqual(len(scored), 1)
        self.assertEqual(scored[0], tuple(texts[:8]))
        self.assertNotIn(far, result["candidates"])

    def test_provenance_carries_the_logit_without_authority(self) -> None:  # FAIL-FIRST
        memory = self.open()
        answer = self.remember(memory, "memory:answer", ANSWER, cosine=0.2, logit=3.0)
        result = memory.recall(QUERY, budget=5)
        hits = [hit for hit in result["admissions"][answer]["route_provenance"] if hit["route_id"] == "semantic_vector"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["answerability_logit"], 3.0)
        self.assertEqual(hits[0]["authority_effect"], "none")
        posture = memory.semantic_retrieval_posture()["answerability"]
        self.assertEqual(posture["pool"], 8)
        self.assertEqual(posture["authority_effect"], "none")

    def test_forgotten_answer_is_never_returned(self) -> None:
        memory = self.open()
        self.remember(memory, "memory:answer", ANSWER, cosine=0.2, logit=3.0)
        self.assertTrue(memory.forget("memory:answer", evidence=_evidence())["committed"])
        self.assertEqual(memory.recall(QUERY, budget=5)["returned"], [])

    def test_superseded_answer_is_not_returned_as_current(self) -> None:
        memory = self.open()
        old = self.remember(memory, "memory:light", ANSWER, cosine=0.2, logit=3.0)
        newer = "The Pell Point lighthouse now shows a steady white beam."
        _TableRepresentation.TABLE[newer] = 0.15
        _TableScorer.TABLE[newer] = 1.0
        outcome = memory.correct("memory:light", newer, evidence=_evidence())
        self.assertTrue(outcome["committed"])
        returned = memory.recall(QUERY, budget=5)["returned"]
        self.assertNotIn(old, returned)
        self.assertIn(outcome["fact_uuid"], returned)

    def test_other_scope_answer_is_not_returned(self) -> None:
        other = self.open(scope="user:c10-other")
        foreign = self.remember(other, "memory:answer", ANSWER, cosine=0.2, logit=3.0)
        other.close()
        memory = self.open()
        result = memory.recall(QUERY, budget=5)
        self.assertNotIn(foreign, result["returned"])

    def test_requires_a_required_semantic_route(self) -> None:
        with self.assertRaises(ValueError):
            self.open(semantic_retrieval="auto")
        with self.assertRaises(ValueError):
            self.open(semantic_retrieval="off")
        with self.assertRaises(ValueError):
            self.open(semantic_answerability="cosine-only")


class UnverifiedModelFailsClosedTests(unittest.TestCase):
    def test_missing_model_refuses_open(self) -> None:  # FAIL-FIRST
        from agentmem_ref.runtime import answerability_onnx

        with tempfile.TemporaryDirectory() as folder, \
                mock.patch.object(representation_onnx, "OnnxSentenceEmbeddingProvider", _TableRepresentation):
            with self.assertRaises(answerability_onnx.AnswerabilityUnavailable):
                AgentMemory.open(Path(folder) / "store", tenant=TENANT, actor_id="agent:c10", scope=SCOPE,
                                 purpose="c10", semantic_retrieval="required",
                                 semantic_answerability="qnli-electra-base",
                                 answerability_dir=Path(folder) / "absent")

    def test_tampered_model_file_refuses_open(self) -> None:  # FAIL-FIRST
        from agentmem_ref.runtime import answerability_onnx

        with tempfile.TemporaryDirectory() as folder:
            model = Path(folder) / "model"
            (model / "onnx").mkdir(parents=True)
            for relative in answerability_onnx.PINNED_FILES:
                (model / relative).write_bytes(b"not the pinned bytes")
            with self.assertRaises(answerability_onnx.AnswerabilityUnavailable):
                answerability_onnx.verify_model_dir(model)


class GateOffIsC4Tests(_Base):
    """With the option off, C4's rule holds: every hit above the floor is proposed, none below."""

    answerability = "off"

    def test_off_proposes_every_hit_above_the_floor_and_none_below(self) -> None:
        memory = self.open()
        above = self.remember(memory, "memory:similar", SIMILAR, cosine=0.6)
        best = self.remember(memory, "memory:best", ANSWER, cosine=0.7)
        below = self.remember(memory, "memory:below", UNRELATED, cosine=0.2)
        result = memory.recall(QUERY, budget=5)
        self.assertEqual(set(result["returned"]), {above, best})
        self.assertNotIn(below, result["candidates"])
        for decision in result["admissions"].values():
            for hit in decision["route_provenance"]:
                self.assertNotIn("answerability_logit", hit)
        self.assertIsNone(memory.semantic_retrieval_posture().get("answerability"))
        self.assertEqual(_TableScorer.calls, [])


if __name__ == "__main__":
    unittest.main()
