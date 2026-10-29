"""BM25 successor parity falsifiers; no hosted acceptance claimed."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/check_amb_scope_distinct_v7_bm25.py"
CANDIDATE = ROOT / (
    "reports/benchmarks/amb/amb-precisionmembench-retrieval-v7-scope-distinct-v1/"
    "bm25-2f4b8a1b103b"
)


def _load():
    spec = importlib.util.spec_from_file_location("amb_bm25_successor_gate_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Bm25SuccessorExactParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = _load()

    def test_controlled_timing_changes_do_not_mask_payload_equality(self):
        old = {"run_name": "v6", "ingestion_time_ms": 22.0,
               "avg_retrieve_time_ms": 5.1, "results": [
                   {"query_id": "a", "correct": True, "retrieve_time_ms": 5.0,
                    "meta": {"relevant_beliefs": ["fact:one"], "failures": []}}
               ]}
        new = {"run_name": "successor", "ingestion_time_ms": 33.0,
               "avg_retrieve_time_ms": 7.8, "results": [
                   {"query_id": "a", "correct": True, "retrieve_time_ms": 8.1,
                    "meta": {"relevant_beliefs": ["fact:one"], "failures": []}}
               ]}
        self.gate.compare_strict(old, new)

    def test_boolean_changed_to_integer_is_not_equal(self):
        with self.assertRaisesRegex(self.gate.control.ParityBlocked, "type changed"):
            self.gate.compare_strict({"correct": True}, {"correct": 1})

    def test_changed_result_or_reordered_documents_refuses(self):
        for old, new in (
            ({"context": "A"}, {"context": "B"}),
            ({"ids": ["a", "b"]}, {"ids": ["b", "a"]}),
            ({"meta": {"a": 1}}, {"meta": {"a": 1, "b": 2}}),
        ):
            with self.subTest(new=new), self.assertRaises(self.gate.control.ParityBlocked):
                self.gate.compare_strict(old, new)

    def test_unlisted_timing_field_cannot_be_silently_ignored(self):
        with self.assertRaisesRegex(self.gate.control.ParityBlocked, "value changed"):
            self.gate.compare_strict({"unlisted_time_ms": 1}, {"unlisted_time_ms": 2})

    def test_volatility_exceptions_are_not_global_wildcards(self):
        for left, right in (
            ({"meta": {"run_name": "a"}}, {"meta": {"run_name": "b"}}),
            ({"meta": {"ingestion_time_ms": 2}}, {"meta": {"ingestion_time_ms": 3}}),
            ({"results": [{"meta": {"retrieve_time_ms": 1}}]},
             {"results": [{"meta": {"retrieve_time_ms": 2}}]}),
        ):
            with self.subTest(right=right), self.assertRaises(self.gate.control.ParityBlocked):
                self.gate.compare_strict(left, right)

    def test_committed_local_bm25_is_exactly_equal_to_v6_not_accepted(self):
        # This is the existing local imported row, not a live hosted run.
        self.assertTrue(CANDIDATE.is_dir(), "local imported row missing")
        verdict = self.gate.verify(self.gate.BASELINE, CANDIDATE, root=ROOT)
        self.assertEqual(verdict["verdict"], "EQUAL")
        self.assertEqual(verdict["cases_equal"], 77)
        self.assertEqual(verdict["acceptance"], "not_granted")


if __name__ == "__main__":
    unittest.main()
