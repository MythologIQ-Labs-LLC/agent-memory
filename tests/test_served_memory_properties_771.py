"""#771 evaluator qualification: seeded property checks of the adopted E1-E5 repairs.

The E1-E5 example tests were written by the same reviewer who wrote the
repairs, so they are not independent evidence on their own. These checks
generate random graded cases and runs (fixed seed, stdlib only) and assert
the invariants the repairs are supposed to guarantee, against the scorer at
the adopted SHA.
"""
from __future__ import annotations

import copy
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from score_served_memory_quality import score  # noqa: E402

TRIALS = 300


def _random_case(rng, cid, *, answerable):
    refs = [f"{cid}-m{i}" for i in range(rng.randint(3, 9))]
    relevance = {r: rng.choice((0, 0, 1, 2, 3)) for r in refs}
    prohibited = [r for r in refs if rng.random() < 0.15]
    stale = [r for r in refs if r not in prohibited and rng.random() < 0.15]
    eligible = [r for r, g in relevance.items() if g >= 2 and r not in prohibited and r not in stale]
    if answerable:
        if not eligible:
            pick = next(r for r in refs if r not in prohibited and r not in stale) if any(
                r not in prohibited and r not in stale for r in refs) else None
            if pick is None:
                return None
            relevance[pick] = 3
            eligible = [pick]
        groups = [[r] for r in rng.sample(eligible, rng.randint(1, min(3, len(eligible))))]
    else:
        for r in eligible:
            relevance[r] = rng.choice((0, 1))
        groups = []
    return {"id": cid, "scenario": "property " + cid, "intent": rng.choice(("current", "historical", "timeless")),
            "budget": rng.randint(1, 5), "relevance": relevance, "critical_groups": groups,
            "prohibited": prohibited, "stale": stale, "safe_answer_exists": answerable}


def _random_served(rng, case):
    refs = list(case["relevance"])
    rng.shuffle(refs)
    return refs[:rng.randint(0, case["budget"])]


def _doc(cases):
    return {"schema": "served-memory-quality-v1", "cases": cases}


def _run(rows):
    return {"schema": "served-memory-run-v1", "runtime_revision": "property", "lane_id": "property",
            "rows": [{"id": k, "returned": v} for k, v in rows.items()]}


class ScorerProperties(unittest.TestCase):
    def _cases(self, rng, n_answerable, n_unanswerable):
        cases = []
        while len(cases) < n_answerable:
            case = _random_case(rng, f"A{len(cases)}", answerable=True)
            if case:
                cases.append(case)
        for i in range(n_unanswerable):
            cases.append(_random_case(rng, f"N{i}", answerable=False))
        return cases

    def test_E2_emptying_an_answerable_case_never_raises_macro_precision(self):
        rng = random.Random(7711)
        for _ in range(TRIALS):
            cases = self._cases(rng, rng.randint(1, 4), rng.randint(0, 2))
            rows = {c["id"]: _random_served(rng, c) for c in cases}
            target = rng.choice([c for c in cases if c["safe_answer_exists"]])
            emptied = dict(rows, **{target["id"]: []})
            base = score(_doc(copy.deepcopy(cases)), _run(rows))["P2_context_utility"]["macro_relevant_precision"]
            after = score(_doc(copy.deepcopy(cases)), _run(emptied))["P2_context_utility"]["macro_relevant_precision"]
            self.assertLessEqual(after, base + 1e-9, (rows, emptied))

    def test_E3_no_safe_answer_cases_never_change_answerable_utility(self):
        rng = random.Random(7712)
        for _ in range(TRIALS):
            cases = self._cases(rng, rng.randint(1, 4), rng.randint(1, 3))
            rows = {c["id"]: _random_served(rng, c) for c in cases}
            answerable = [c for c in cases if c["safe_answer_exists"]]
            full = score(_doc(copy.deepcopy(cases)), _run(rows))
            only = score(_doc(copy.deepcopy(answerable)), _run({c["id"]: rows[c["id"]] for c in answerable}))
            for key, value in only["P2_context_utility"].items():
                if key == "irrelevant_served_total":
                    continue  # documented as an all-case total
                self.assertEqual(value, full["P2_context_utility"][key], key)
            for key in ("top1_critical_rate", "top1_relevant_rate", "all_critical_groups_covered_rate"):
                self.assertEqual(only["P1_served_correctness"][key], full["P1_served_correctness"][key], key)

    def test_E4_recall_at_budget_is_bounded_and_reaches_one_for_an_ideal_context(self):
        rng = random.Random(7713)
        for _ in range(TRIALS):
            case = None
            while case is None:
                case = _random_case(rng, "A", answerable=True)
            safe = [r for r, g in case["relevance"].items()
                    if g >= 2 and r not in case["prohibited"] and r not in case["stale"]]
            served = _random_served(rng, case)
            row = score(_doc([copy.deepcopy(case)]), _run({"A": served}))["per_case"][0]
            self.assertGreaterEqual(row["relevant_recall_at_budget"], 0.0)
            self.assertLessEqual(row["relevant_recall_at_budget"], 1.0)
            ideal = safe[:case["budget"]]
            row = score(_doc([copy.deepcopy(case)]), _run({"A": ideal}))["per_case"][0]
            self.assertEqual(row["relevant_recall_at_budget"], 1.0)

    def test_E5_top1_critical_implies_top1_relevant_and_requires_a_critical_ref(self):
        rng = random.Random(7714)
        seen_support_only = False
        for _ in range(TRIALS):
            case = None
            while case is None:
                case = _random_case(rng, "A", answerable=True)
            served = _random_served(rng, case)
            row = score(_doc([copy.deepcopy(case)]), _run({"A": served}))["per_case"][0]
            critical = {r for g in case["critical_groups"] for r in g}
            self.assertEqual(row["top1_critical"], bool(served) and served[0] in critical)
            if row["top1_critical"]:
                self.assertTrue(row["top1_relevant"])
            seen_support_only |= row["top1_relevant"] and not row["top1_critical"]
        self.assertTrue(seen_support_only, "property generator never exercised support-only rank 1")

    def test_no_abstention_claim_is_ever_inferred(self):
        rng = random.Random(7715)
        for _ in range(TRIALS):
            cases = self._cases(rng, rng.randint(0, 3), rng.randint(1, 3))
            rows = {c["id"]: (_random_served(rng, c) if rng.random() < 0.5 else []) for c in cases}
            report = score(_doc(cases), _run(rows))
            p1 = report["P1_served_correctness"]
            self.assertIsNone(p1["answer_abstention_verified"])
            self.assertEqual(p1["answer_abstention_status"], "not_measured_without_answering_layer")
            self.assertTrue(all(r["answer_abstention_verified"] is None for r in report["per_case"]))
            self.assertFalse(any("abstention" in k and k not in ("answer_abstention_verified", "answer_abstention_status")
                                 for k in p1))

    def test_prohibited_or_stale_memories_never_earn_relevance_credit(self):
        rng = random.Random(7716)
        for _ in range(TRIALS):
            case = None
            while case is None:
                case = _random_case(rng, "A", answerable=True)
            served = _random_served(rng, case)
            row = score(_doc([copy.deepcopy(case)]), _run({"A": served}))["per_case"][0]
            unsafe = set(case["prohibited"]) | set(case["stale"])
            clean = [r for r in served if r not in unsafe]
            hits = sum(case["relevance"][r] >= 2 for r in clean)
            expected = round(hits / len(served), 6) if served else 0.0
            self.assertEqual(row["relevant_precision"], expected)
            if served and served[0] in unsafe:
                self.assertFalse(row["top1_relevant"])
                self.assertFalse(row["top1_critical"])


if __name__ == "__main__":
    unittest.main()
