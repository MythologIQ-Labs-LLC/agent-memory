"""#576: admitted-set BM25 evidence and order must not depend on the process string-hash seed.

Before policy 3.0.1, ``admitted_set_bm25`` summed per-term contributions in ``set``
iteration order, which follows ``PYTHONHASHSEED``. Float addition is not associative,
so the same revision, store and query produced last-bit-different
``lexical_relevance_score`` values in different processes, and mathematically tied
candidates could change order. The fixture below is such a near-tie: m0, m3 and m5
score identically in exact arithmetic, and at ``8dba9eb`` seeds 0, 1 and 2 ranked them
three different ways.

Scope of the guarantee: 3.0.1 made the accumulation order a function of the inputs
alone, and policy 3.0.2 preserves that guarantee while separating consumed temporal
intent cues from lexical relevance (#583). It does **not** make every mathematically
tied pair bit-equal. Two texts whose addends are the same multiset can still round 1
ulp apart when the distinguishing term sorts at a different position (``RESIDUAL_ULP``
below; AgentMemBench record 149 is a live instance). That residual order is
deterministic, and is pinned here so a later change to it is visible.

The cross-process tests run fresh interpreters with explicit seeds because a single
process cannot change its own string-hash seed.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.runtime import ranking_policy  # noqa: E402

QUERY = "alpha bravo charlie delta echo"
TEXTS = {
    "m0": "delta hotel echo charlie",
    "m1": "foxtrot golf delta alpha echo alpha foxtrot",
    "m2": "hotel delta foxtrot hotel golf charlie",
    "m3": "delta echo foxtrot alpha",
    "m4": "echo alpha",
    "m5": "echo delta hotel charlie",
}
NEAR_TIE = ("m0", "m3", "m5")

# Same addend multiset ({the, user, for} plus one query term unique to each text), same
# length; "zulu" sorts after every shared term and "apple" before, so under sorted
# accumulation the sums round 1 ulp apart, identically in every process.
RESIDUAL_QUERY = "which tool does the user zulu for apple"
RESIDUAL_TEXTS = {
    "a": "the user zulu for x0 x1 x2 x3",
    "b": "the user apple for y0 y1 y2 y3",
    "o0": "the user for o0w0 o0w1",
    "o1": "the user for o1w0 o1w1",
    "o2": "the user for o2w0 o2w1",
    "o3": "the user p0w0 p0w1",
    "o4": "the user p1w0 p1w1",
    "o5": "the user p2w0 p2w1",
    "o6": "the user p3w0 p3w1",
    "o7": "the user p4w0 p4w1",
}
SEEDS = ("0", "1", "2")

_CHILD = textwrap.dedent(
    """
    import json, sys, tempfile
    sys.path.insert(0, sys.argv[1])
    from agentmem_ref import AgentMemory
    from agentmem_ref.runtime import ranking_policy
    query, texts = json.loads(sys.argv[2])
    scores = ranking_policy.admitted_set_bm25(query, texts)
    with tempfile.TemporaryDirectory() as root:
        memory = AgentMemory.open(root, tenant="tenant:576", actor_id="agent:576", scope="project:576", purpose="576")
        refs = {memory.remember("memory:" + key, text)["fact_uuid"]: key for key, text in texts.items()}
        forgotten = memory.remember("memory:forgotten", query + " forgotten")["fact_uuid"]
        refs[forgotten] = "forgotten"
        memory.forget("memory:forgotten")
        recalled = memory.recall(query)
        memory.close()
    admissions = {
        refs[uuid]: [adm["outcome"], adm["reason_code"],
                     repr(adm.get("ranking_evidence", {}).get("lexical_relevance_score")),
                     adm.get("ranking_evidence", {}).get("ordered_before_next_by")]
        for uuid, adm in recalled["admissions"].items()
    }
    print(json.dumps({
        "scores": {ref: score.hex() for ref, score in sorted(scores.items())},
        "admitted": [refs[uuid] for uuid in recalled["admitted"]],
        "candidates": sorted(refs[uuid] for uuid in recalled["candidates"]),
        "admissions": admissions,
    }, sort_keys=True))
    """
)


def _run_under_seed(seed: str, query: str = QUERY, texts: dict[str, str] = TEXTS) -> dict:
    env = {**os.environ, "PYTHONHASHSEED": seed}
    payload = json.dumps([query, texts])
    completed = subprocess.run(
        [sys.executable, "-c", _CHILD, str(ROOT / "reference"), payload],
        env=env, capture_output=True, text=True, check=True,
    )
    return json.loads(completed.stdout)


def _sorted_order_reference(query: str, texts: dict[str, str]) -> dict[str, float]:
    """Independent restatement of the sorted BM25 accumulation used since 3.0.1."""

    documents = {ref: ranking_policy.relevance_tokens(text) for ref, text in texts.items()}
    count = len(documents)
    average = sum(len(tokens) for tokens in documents.values()) / count or 1.0
    frequency = Counter(token for tokens in documents.values() for token in set(tokens))
    k1, b = ranking_policy.BM25_K1, ranking_policy.BM25_B
    scores = {}
    for ref, tokens in documents.items():
        counts = Counter(tokens)
        score = 0.0
        for term in sorted(set(ranking_policy.relevance_tokens(query))):
            tf = counts.get(term, 0)
            if tf:
                idf = math.log(1.0 + (count - frequency[term] + 0.5) / (frequency[term] + 0.5))
                score += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * len(tokens) / average))
        scores[ref] = score
    return scores


class BM25HashSeedDeterminismTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runs = {seed: _run_under_seed(seed) for seed in SEEDS}

    def test_bm25_score_bits_identical_across_hash_seeds(self):
        baseline = self.runs[SEEDS[0]]["scores"]
        for seed in SEEDS[1:]:
            self.assertEqual(self.runs[seed]["scores"], baseline, f"PYTHONHASHSEED={seed}")

    def test_near_tie_is_an_exact_tie_in_every_process(self):
        for seed, run in self.runs.items():
            self.assertEqual(len({run["scores"][ref] for ref in NEAR_TIE}), 1, f"PYTHONHASHSEED={seed}")

    def test_governed_order_and_evidence_identical_across_hash_seeds(self):
        baseline = self.runs[SEEDS[0]]
        for seed in SEEDS[1:]:
            self.assertEqual(self.runs[seed]["admitted"], baseline["admitted"], f"PYTHONHASHSEED={seed}")
            self.assertEqual(self.runs[seed]["admissions"], baseline["admissions"], f"PYTHONHASHSEED={seed}")

    def test_restart_under_same_seed_is_identical(self):
        self.assertEqual(_run_under_seed(SEEDS[1]), self.runs[SEEDS[1]])

    def test_admission_and_refusal_unchanged(self):
        for seed, run in self.runs.items():
            self.assertEqual(run["candidates"], sorted([*TEXTS, "forgotten"]), seed)
            self.assertEqual(sorted(run["admitted"]), sorted(TEXTS), seed)
            outcome, reason, score, _ = run["admissions"]["forgotten"]
            self.assertEqual((outcome, reason, score), ("block", "tombstoned", "None"), seed)

    def test_score_equals_sorted_order_accumulation_bit_for_bit(self):
        actual = ranking_policy.admitted_set_bm25(QUERY, TEXTS)
        expected = _sorted_order_reference(QUERY, TEXTS)
        self.assertEqual({k: v.hex() for k, v in actual.items()}, {k: v.hex() for k, v in expected.items()})

    def test_near_tie_resolved_by_stable_fallback_not_by_float_noise(self):
        with tempfile.TemporaryDirectory() as root:
            memory = AgentMemory.open(root, tenant="tenant:576", actor_id="agent:576", scope="project:576", purpose="576")
            refs = {memory.remember(f"memory:{key}", text)["fact_uuid"]: key for key, text in TEXTS.items()}
            recalled = memory.recall(QUERY)
            memory.close()
        tied = [uuid for uuid in recalled["admitted"] if refs[uuid] in NEAR_TIE]
        self.assertEqual([refs[uuid] for uuid in recalled["admitted"][:3]], [refs[uuid] for uuid in tied])
        # The first two tied candidates are separated by the declared time-neutral digest
        # fallback, not by a last-ulp lexical difference.
        for uuid in tied[:2]:
            self.assertEqual(
                recalled["admissions"][uuid]["ranking_evidence"]["ordered_before_next_by"], "candidate_ref_neutral_digest"
            )

    def test_residual_one_ulp_tie_order_is_deterministic_across_hash_seeds(self):
        runs = [_run_under_seed(seed, RESIDUAL_QUERY, RESIDUAL_TEXTS) for seed in SEEDS]
        self.assertEqual([run["scores"] for run in runs[1:]], [runs[0]["scores"]] * (len(runs) - 1))
        self.assertEqual([run["admitted"] for run in runs[1:]], [runs[0]["admitted"]] * (len(runs) - 1))
        a, b = (float.fromhex(runs[0]["scores"][ref]) for ref in ("a", "b"))
        self.assertEqual(a, math.nextafter(b, math.inf))

    def test_policy_version_records_the_patch(self):
        self.assertEqual(ranking_policy.POLICY_VERSION, "3.0.2")


if __name__ == "__main__":
    unittest.main()
