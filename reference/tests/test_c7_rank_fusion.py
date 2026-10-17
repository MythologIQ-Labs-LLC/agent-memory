"""#819 C7: bounded reciprocal-rank fusion of admitted evidence (ranking policy 3.5.0).

Fail-first tests, preregistered in ``reports/benchmarks/memory-quality/819-c7/PREREGISTRATION-C7.md``.

Under ranking policy 3.4.0, admitted memories are ordered lexicographically:
- route corroboration count;
- then per-route scores and admitted-set BM25;
- the optional semantic route only after every relevance and temporal stage, as a tie-break.

A memory found only by the semantic route therefore ranks below every lexically found memory,
and a dense signal can never outweigh a BM25 difference.

C7 replaces those relevance stages with a reciprocal-rank fusion (k = 60) of each admitted
memory's lexical, shared-evidence and dense ranks, but only when the provider is enabled. It
changes nothing else:
- discovery and admission;
- selection's sufficiency decisions;
- the route-off ranking.

A deterministic table representation fixes every cosine. Tests marked FAIL-FIRST fail on C6
``171e67db``; the others hold on both heads.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.memory import procedural_memory as pm  # noqa: E402
from agentmem_ref.runtime import representation_onnx, runtime_composition, vector_retrieval  # noqa: E402
from agentmem_ref.runtime.vector_retrieval import VectorRepresentationSpec  # noqa: E402

TENANT = "tenant:c7"
SCOPE = "user:c7"
DIMENSIONS = 8


class _TableRepresentation:
    """``TABLE[query][fact_text]`` is the exact cosine between that query and that fact text."""

    TABLE: dict[str, dict[str, float]] = {}
    spec = VectorRepresentationSpec(
        representation_ref="test:c7-table",
        representation_version="1.0.0",
        config_digest="sha256:" + "c7" * 32,
        dimensions=DIMENSIONS,
        deterministic_rebuild=True,
    )

    def __init__(self, model_dir=None) -> None:
        pass

    def embed(self, text: str) -> tuple[float, ...]:
        queries = sorted(self.TABLE)
        assert len(queries) < DIMENSIONS
        vector = ([1.0 if query == text else 0.0 for query in queries] if text in self.TABLE
                  else [self.TABLE[query].get(text, 0.0) for query in queries])
        remainder = 1.0 - sum(c * c for c in vector)
        assert remainder >= -1e-9, text
        return tuple(vector + [0.0] * (DIMENSIONS - 1 - len(vector)) + [math.sqrt(max(remainder, 0.0))])


def _evidence(scope: str = SCOPE):
    skill = pm.SkillArtifact(skill_id="skill:c7", version=1, purpose="apply a lifecycle change", scope=scope,
                             isolation_domain_refs=(TENANT, scope), required_isolation_domain_refs=(TENANT, scope),
                             procedure_markdown="# verify\nConfirm.", provenance_refs=("evidence:c7",))
    return pm.evidence_for(skill)


class _Store(unittest.TestCase):
    semantic = "required"

    def setUp(self) -> None:
        self._folder = tempfile.TemporaryDirectory()
        self.addCleanup(self._folder.cleanup)
        self.root = Path(self._folder.name)
        patcher = mock.patch.object(representation_onnx, "OnnxSentenceEmbeddingProvider", _TableRepresentation)
        patcher.start()
        self.addCleanup(patcher.stop)
        _TableRepresentation.TABLE = {}
        self.refs: dict[str, str] = {}

    def open(self, scope: str = SCOPE, root: Path | None = None) -> AgentMemory:
        memory = AgentMemory.open(root or self.root, tenant=TENANT, actor_id="agent:c7", scope=scope,
                                  purpose="c7 qualification", semantic_retrieval=self.semantic)
        self.addCleanup(memory.close)
        return memory

    def seed(self, memory: AgentMemory, facts: dict[str, str]) -> None:
        for ref, text in facts.items():
            outcome = memory.remember(ref, text)
            self.assertTrue(outcome["committed"], outcome)
            self.refs[outcome["fact_uuid"]] = ref

    def ids(self, uuids) -> list[str]:
        return [self.refs.get(uuid, uuid) for uuid in uuids]

    def ranked(self, memory: AgentMemory, query: str, **kwargs) -> tuple[list[str], dict]:
        result = memory.recall(query, budget=10, return_selection="ranked_prefix", **kwargs)
        return self.ids(result["admitted"]), result


TRIPS = "Which trips did I take this year?"
TRIP_FACTS = {
    "memory:highlands": "Drove up to the Highlands for a long weekend in August.",   # no shared word
    "memory:plumber": "Did the plumber ever call back?",                             # shares "did"
    "memory:bins": "Did we take the bins out on Tuesday?",                           # shares "did", "take"
    "memory:year": "This year the garden flooded twice.",                            # shares "this", "year"
}

BOILER = "When is the boiler service due?"
BOILER_FACTS = {
    "memory:manual": "Boiler manual and boiler warranty for the boiler service are in the drawer.",
    "memory:serviced": "The boiler was serviced in September by HeatRight.",
    "memory:f1": "The kettle needs descaling.",
    "memory:f2": "The hallway light flickers.",
}
BOILER_SIMS = {"memory:serviced": 0.80, "memory:f1": 0.30, "memory:f2": 0.25, "memory:manual": 0.10}


class C9SelectionFunnelDiagnostics(_Store):
    """C9 observes evidence withheld by selection without changing ranking or return."""

    def test_selection_funnel_matches_top_k_and_never_promotes_evidence(self):
        _TableRepresentation.TABLE = {
            BOILER: {BOILER_FACTS[ref]: value for ref, value in BOILER_SIMS.items()}
        }
        memory = self.open()
        self.seed(memory, BOILER_FACTS)
        default = memory.recall(BOILER, budget=2, return_selection="relevance_sufficient")
        prefix = memory.recall(BOILER, budget=2, return_selection="ranked_prefix")
        policy = default["return_policy"]
        funnel = policy["selection_funnel"]
        self.assertEqual(default["admitted"], prefix["admitted"])
        self.assertEqual(funnel["admitted_count"], len(default["admitted"]))
        self.assertEqual(funnel["candidate_count"], len(default["candidates"]))
        self.assertEqual(funnel["refused_count"], sum(
            bool(v.get("refusal")) for v in default["admissions"].values()
        ))
        self.assertEqual(funnel["sufficient_count"], policy["sufficient_count"])
        self.assertEqual(funnel["returned_count"], len(default["returned"]))
        self.assertEqual(funnel["budget"], 2)
        self.assertEqual(funnel["authority_effect"], "none")
        withheld = [
            ref for ref in prefix["returned"]
            if default["admissions"][ref]["return_selection"]["ranked_prefix_withheld"]
        ]
        self.assertEqual(funnel["ranked_prefix_withheld_count"], len(withheld))
        self.assertEqual(sum(funnel["ranked_prefix_withheld_bases"].values()), len(withheld))
        self.assertTrue(set(default["returned"]).issubset(set(default["admitted"])))
        for ref in default["returned"]:
            self.assertFalse(default["admissions"][ref]["return_selection"]["ranked_prefix_withheld"])

    def test_unbudgeted_selection_accounting_and_determinism(self):
        _TableRepresentation.TABLE = {
            BOILER: {BOILER_FACTS[ref]: value for ref, value in BOILER_SIMS.items()}
        }
        # Each recall mints counter-based decision ids and clock readings, so repeat recalls on one
        # store differ there by design; determinism is compared across identically seeded stores.
        results = []
        for index in range(2):
            root = self.root / f"store-{index}"
            root.mkdir()
            memory = self.open(root=root)
            self.seed(memory, BOILER_FACTS)
            results.append(memory.recall(BOILER, return_selection="relevance_sufficient"))
        first, second = results
        self.assertEqual(first, second)
        repeat = memory.recall(BOILER, return_selection="relevance_sufficient")
        for key in ("candidates", "admitted", "returned", "return_policy"):
            self.assertEqual(repeat[key], second[key])
        self.assertEqual(
            {ref: d["return_selection"] for ref, d in repeat["admissions"].items()},
            {ref: d["return_selection"] for ref, d in second["admissions"].items()},
        )
        funnel = first["return_policy"]["selection_funnel"]
        self.assertIsNone(funnel["budget"])
        self.assertEqual(funnel["returned_count"], len(first["returned"]))
        self.assertEqual(
            funnel["ranked_prefix_withheld_count"],
            len(first["admitted"]) - funnel["sufficient_count"],
        )

    def test_refused_candidates_are_counted_and_never_marked_withheld(self):
        # A corrected memory's superseded statement is still discovered but refused admission,
        # so the funnel must count it as a refusal, not as admitted or withheld evidence.
        query = "Where do I work?"
        old, corrected = "I work for Contoso Retail.", "I work for Fabrikam Logistics now."
        _TableRepresentation.TABLE = {query: {old: 0.90, corrected: 0.80}}
        memory = self.open()
        self.seed(memory, {"memory:job": old})
        self.assertTrue(memory.correct("memory:job", corrected, evidence=_evidence())["committed"])
        for budget in (None, 1):
            kwargs = {} if budget is None else {"budget": budget}
            result = memory.recall(query, return_selection="relevance_sufficient", **kwargs)
            funnel = result["return_policy"]["selection_funnel"]
            refused = [ref for ref in result["candidates"] if result["admissions"][ref].get("refusal")]
            self.assertGreaterEqual(len(refused), 1, result["admissions"])
            self.assertEqual(funnel["refused_count"], len(refused))
            self.assertEqual(funnel["candidate_count"], funnel["refused_count"] + funnel["admitted_count"])
            self.assertFalse(set(refused) & set(result["admitted"]))
            for ref in refused:
                self.assertNotIn("ranked_prefix_withheld", result["admissions"][ref].get("return_selection", {}))
            self.assertEqual(funnel["budget"], budget)
            self.assertEqual(funnel["returned_count"], len(result["returned"]))


class FusedRanking(_Store):
    # Erratum (recorded after implementation; the preregistered mechanism is unchanged): this
    # preregistered expectation is false for the preregistered fusion. Every admitted memory has a
    # dense rank, so a memory found only by the semantic route is in one list (1/61 at best),
    # while lexically found filler is in two lists (1/63 + 1/64 even at weak ranks). RRF
    # therefore keeps semantic-only evidence below lexical candidates unless their ranks are
    # very deep. The prediction failed; it stays here as an expected failure so the property is
    # visible and any change to it is noticed.
    @unittest.expectedFailure
    def test_a_semantic_only_memory_with_the_top_cosine_outranks_weak_lexical_filler(self):  # FAIL-FIRST
        _TableRepresentation.TABLE = {TRIPS: {TRIP_FACTS["memory:highlands"]: 0.70, TRIP_FACTS["memory:year"]: 0.20,
                                              TRIP_FACTS["memory:bins"]: 0.10, TRIP_FACTS["memory:plumber"]: 0.05}}
        memory = self.open()
        self.seed(memory, TRIP_FACTS)
        ranked, _ = self.ranked(memory, TRIPS)
        self.assertIn("memory:highlands", ranked)
        self.assertLess(ranked.index("memory:highlands"), ranked.index("memory:plumber"))
        self.assertLess(ranked.index("memory:highlands"), 2)

    def test_dense_agreement_outweighs_a_small_bm25_lead(self):  # FAIL-FIRST
        _TableRepresentation.TABLE = {BOILER: {BOILER_FACTS[ref]: value for ref, value in BOILER_SIMS.items()}}
        memory = self.open()
        self.seed(memory, BOILER_FACTS)
        ranked, result = self.ranked(memory, BOILER)
        by_ref = {self.refs[u]: d for u, d in result["admissions"].items() if u in self.refs}
        bm25 = {ref: (by_ref[ref].get("ranking_evidence") or {}).get("lexical_relevance_score") for ref in ("memory:manual", "memory:serviced")}
        self.assertGreater(bm25["memory:manual"], bm25["memory:serviced"])  # the manual leads on BM25
        self.assertLess(ranked.index("memory:serviced"), ranked.index("memory:manual"))

    def test_policy_identity_and_per_memory_fusion_evidence(self):  # FAIL-FIRST
        _TableRepresentation.TABLE = {BOILER: {BOILER_FACTS[ref]: value for ref, value in BOILER_SIMS.items()}}
        memory = self.open()
        self.seed(memory, BOILER_FACTS)
        _, result = self.ranked(memory, BOILER)
        for decision in (d for d in result["admissions"].values() if "rank_position" in d):
            evidence = decision["ranking_evidence"]
            self.assertEqual(evidence["policy_version"], "3.5.0")
            fusion = evidence["fusion"]
            self.assertEqual((fusion["status"], fusion["k"], fusion["authority_effect"]), ("applied", 60, "none"))
            self.assertIn("dense_rank", fusion)
            self.assertIn("fused_score", fusion)

    def test_dense_scoring_failure_falls_back_to_the_base_order(self):  # FAIL-FIRST
        _TableRepresentation.TABLE = {BOILER: {BOILER_FACTS[ref]: value for ref, value in BOILER_SIMS.items()}}
        memory = self.open()
        self.seed(memory, BOILER_FACTS)
        with mock.patch.object(vector_retrieval.NativeVectorCandidateRetriever, "similarities", create=True,
                               side_effect=representation_onnx.RepresentationUnavailable("down")):
            ranked, result = self.ranked(memory, BOILER)
        self.assertLess(ranked.index("memory:manual"), ranked.index("memory:serviced"))  # 3.4.0 order
        statuses = {d["ranking_evidence"].get("fusion", {}).get("status")
                    for d in result["admissions"].values() if "rank_position" in d}
        self.assertEqual(statuses, {"unavailable"})

    def test_more_admitted_memories_than_the_limit_skips_fusion(self):  # FAIL-FIRST
        _TableRepresentation.TABLE = {BOILER: {BOILER_FACTS[ref]: value for ref, value in BOILER_SIMS.items()}}
        memory = self.open()
        self.seed(memory, BOILER_FACTS)
        with mock.patch.object(runtime_composition, "FUSION_MAX_ADMITTED", 1, create=True):
            ranked, result = self.ranked(memory, BOILER)
        self.assertLess(ranked.index("memory:manual"), ranked.index("memory:serviced"))
        statuses = {d["ranking_evidence"].get("fusion", {}).get("status")
                    for d in result["admissions"].values() if "rank_position" in d}
        self.assertEqual(statuses, {"skipped_over_limit"})


class Invariants(_Store):
    def test_forgotten_other_scope_and_superseded_memories_never_rank(self):
        query = "Which animal is scared of storms?"
        texts = {"memory:old": "Our old beagle used to hide from thunder.",
                 "memory:a": "Biscuit, our beagle, hides from thunder.",
                 "memory:job": "I work for Contoso Retail."}
        corrected = "Biscuit now sleeps through storms after training."
        theirs = "The neighbours' ferret is scared of storms."
        _TableRepresentation.TABLE = {query: {texts["memory:old"]: 0.95, theirs: 0.94, texts["memory:a"]: 0.60,
                                              texts["memory:job"]: 0.90, corrected: 0.50}}
        other = self.open("user:c7-other")
        self.seed(other, {"memory:theirs": theirs})
        other.close()
        memory = self.open()
        self.seed(memory, texts)
        self.assertTrue(memory.forget("memory:old", evidence=_evidence())["committed"])
        outcome = memory.correct("memory:job", corrected, evidence=_evidence())
        self.assertTrue(outcome["committed"], outcome)
        for selection in ("ranked_prefix", "relevance_sufficient"):
            result = memory.recall(query, budget=10, return_selection=selection)
            listed = set(self.ids(result["admitted"])) | set(self.ids(result["returned"]))
            self.assertFalse(listed & {"memory:old", "memory:theirs", "memory:job"}, (selection, listed))
            blob = json.dumps(result)
            self.assertNotIn("used to hide", blob)
            self.assertNotIn("ferret", blob)

    def test_fusion_does_not_make_a_below_floor_memory_sufficient(self):
        # 'serviced' is below the relevance floor on BM25 and its cosine is under the C6 proposal
        # threshold, so no route makes it sufficient. Fusion may lift it above the best
        # primary-evidence fact, but sufficiency is decided on the base order.
        sims = {"memory:serviced": 0.35, "memory:f1": 0.30, "memory:f2": 0.25, "memory:manual": 0.10}
        _TableRepresentation.TABLE = {BOILER: {BOILER_FACTS[ref]: value for ref, value in sims.items()}}
        memory = self.open()
        self.seed(memory, BOILER_FACTS)
        result = memory.recall(BOILER, budget=10)
        decisions = {self.refs[u]: d.get("return_selection", {}) for u, d in result["admissions"].items() if u in self.refs}
        self.assertEqual(decisions["memory:serviced"].get("basis"), "below_relative_floor")
        self.assertNotIn("memory:serviced", self.ids(result["returned"]))
        self.assertIn("memory:manual", self.ids(result["returned"]))

    def test_exact_ties_order_identically_across_fresh_stores_and_hash_seeds(self):
        script = r'''
import json, math, sys, tempfile
from pathlib import Path
from unittest import mock
sys.path.insert(0, sys.argv[1])
sys.path.insert(0, sys.argv[2])
import test_c7_rank_fusion as t
from agentmem_ref import AgentMemory
from agentmem_ref.runtime import representation_onnx
q = "Who looks after the garden?"
facts = {"memory:a": "Priya mows the lawn on Saturdays.", "memory:b": "Tomasz prunes the roses each spring.",
         "memory:c": "Ines weeds the beds every week."}
t._TableRepresentation.TABLE = {q: {text: 0.70 for text in facts.values()}}
with mock.patch.object(representation_onnx, "OnnxSentenceEmbeddingProvider", t._TableRepresentation):
    with tempfile.TemporaryDirectory() as tmp, AgentMemory.open(tmp, tenant="tenant:c7", actor_id="agent:c7",
            scope="user:c7", purpose="c7", semantic_retrieval="required") as m:
        refs = {m.remember(r, x)["fact_uuid"]: r for r, x in facts.items()}
        print(json.dumps([refs.get(u, u) for u in m.recall(q, budget=10, return_selection="ranked_prefix")["admitted"]]))
'''
        here = Path(__file__).resolve()
        orders = set()
        for seed in ("0", "1", "12345"):
            env = {**os.environ, "PYTHONHASHSEED": seed}
            out = subprocess.run([sys.executable, "-c", script, str(here.parents[1]), str(here.parent)],
                                 capture_output=True, text=True, env=env, check=True).stdout.strip()
            orders.add(out)
        self.assertEqual(len(orders), 1, orders)


class RouteOff(_Store):
    semantic = "off"

    def test_without_the_provider_the_ranking_is_340(self):
        memory = self.open()
        self.seed(memory, BOILER_FACTS)
        ranked, result = self.ranked(memory, BOILER)
        evidence = [d["ranking_evidence"] for d in result["admissions"].values() if "rank_position" in d]
        self.assertTrue(evidence)
        self.assertEqual({e["policy_version"] for e in evidence}, {"3.4.0"})
        self.assertFalse(any("fusion" in e for e in evidence))
        self.assertLess(ranked.index("memory:manual"), ranked.index("memory:serviced"))


if __name__ == "__main__":
    unittest.main()
