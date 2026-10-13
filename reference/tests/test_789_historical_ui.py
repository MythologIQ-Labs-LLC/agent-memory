"""Historical v6 UI source projection is deterministic and non-promoted."""
import unittest

from scripts.build_789_historical_ui import build

class HistoricalUIProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=build()

    def test_contract_non_promoted(self):
        d=self.data
        self.assertFalse(d["eligible_for_frontier_rankings"])
        self.assertEqual(d["authority_effect"], "none")
        self.assertEqual(d["evidence_status"], "historical_source_bound_not_promoted")

    def test_exact_native_case_denominators(self):
        d=self.data
        self.assertEqual(len(d["cases"]),77)
        self.assertEqual(d["systems"]["agent_memory"]["precision_denominator"],67)
        self.assertEqual(d["systems"]["mem0_oss"]["precision_denominator"],68)
        self.assertEqual(d["systems"]["bm25_control"]["precision_denominator"],70)
        self.assertEqual([d["systems"][x]["recall_denominator"] for x in ("agent_memory","mem0_oss","bm25_control")],[43]*3)

    def test_case_population_and_zero_pass_categories(self):
        d=self.data
        self.assertEqual(len({row["case_id"] for row in d["cases"]}),77)
        for name,n in (("Scope disambiguation",12),("Supersession chain exclusion",3),("Counter-signal retrieval",2),("Relation expansion",4)):
            cat=next(x for x in d["categories"] if x["category"]==name)
            self.assertEqual(cat["total"],n)
            for system in ("agent_memory","mem0_oss","bm25_control"):
                self.assertEqual(cat[system],0)

    def test_paired_matrix_and_no_human_evaluations(self):
        d=self.data
        self.assertEqual(d["pair_outcomes"],{"agent_only":6,"mem0_only":1,"both_pass":9,"both_fail":61})
        self.assertEqual((d["review"]["completed_forms"],d["review"]["required_forms"]),(0,96))
        self.assertEqual(d["agent_failure_diagnostics"]["unexpected_only"],60)
        self.assertEqual(d["agent_failure_diagnostics"]["missing_only"],2)

    def test_no_raw_query_gold_context_leak(self):
        for row in self.data["cases"]:
            self.assertEqual(set(row),{"case_id","category","outcome","systems"})
            for sys in row["systems"].values():
                self.assertEqual(set(sys),{"pass","unexpected","missing","context_tokens"})

if __name__ == "__main__":
    unittest.main()
