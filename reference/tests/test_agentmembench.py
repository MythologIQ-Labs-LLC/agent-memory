from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "reference"
RUNNER = REFERENCE / "run_agentmembench.py"
FIXTURE = REFERENCE / "fixtures" / "benchmarks" / "agentmembench" / "synthetic.jsonl"
if str(REFERENCE) not in sys.path:
    sys.path.insert(0, str(REFERENCE))


def _module():
    spec = importlib.util.spec_from_file_location("run_agentmembench", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


M = _module()
HAS_NUMPY = M._numpy() is not None
SMALL = dict(
    conflict_pairs=10,
    isolation_users=4,
    isolation_facts=2,
    deletion_records=5,
    concurrency_records=6,
    workers=(1, 2),
    scales=(10, 30),
    scale_read_queries=5,
)
NON_RETRIEVAL = ("conflict", "isolation", "deletion", "concurrency", "scale")


class PhaseSemanticsTests(unittest.TestCase):
    def test_percentile_matches_numpy_linear_interpolation(self) -> None:
        values = [5.0, 1.0, 9.0, 3.0]
        self.assertEqual(M.percentile(values, 50), 4.0)
        self.assertAlmostEqual(M.percentile(values, 95), 8.4)
        self.assertIsNone(M.percentile([], 50))

    def test_lexical_baseline_is_partitioned_by_user(self) -> None:
        adapter = M.LexicalOverlapAdapter()
        adapter.add("The user's private project code is A.", "alice")
        adapter.add("The user's private project code is B.", "bob")
        self.assertEqual(adapter.search("private project code", "alice", 5), ["The user's private project code is A."])

    def test_agent_memory_isolation_is_enforced_by_governed_admission(self) -> None:
        adapter = M.AgentMemoryAdapter()
        try:
            adapter.add("The user's private project code is CANARY_A.", "alice")
            adapter.add("The user's private project code is CANARY_B.", "bob")
            self.assertEqual(
                adapter.search("What is the private project code?", "alice", 5),
                ["The user's private project code is CANARY_A."],
            )
            governance = adapter.governance()
        finally:
            adapter.close()
        # Contract 1.3.0 (#548): bob's canary is outside alice's domain, so it never becomes
        # alice's candidate. Isolation holds before admission, and admission rechecks it.
        self.assertEqual(governance["candidate_count"], 1)
        self.assertEqual(governance["admitted_count"], 1)
        self.assertEqual(governance["refusal_reasons"], {})
        self.assertEqual(governance["candidate_scopes"], {"domain_eligible": 1})

    def test_agent_memory_deletion_is_governed_tombstone(self) -> None:
        adapter = M.AgentMemoryAdapter()
        try:
            ids = adapter.add("The user's private erasure test code is ERASE_1.", "carol")
            adapter.delete(ids)
            self.assertEqual(adapter.search("What is the erasure test code?", "carol", 5), [])
            governance = adapter.governance()
        finally:
            adapter.close()
        self.assertEqual(governance["forget_committed"], 1)
        self.assertIn("tombstoned", governance["refusal_reasons"])

    def test_phase_errors_are_recorded_not_hidden(self) -> None:
        def broken(adapter, pairs):
            raise RuntimeError("boom")

        with mock.patch.object(M, "run_conflict", broken):
            report = M.run(FIXTURE, corpus_class="synthetic", backends=("lexical_overlap",), phases=("conflict",), **SMALL)
        backend = report["backends"]["lexical_overlap"]
        self.assertEqual(backend["phase_errors"], {"conflict": "RuntimeError: boom"})
        self.assertNotIn("conflict", backend["phases"])


class ProfileReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = M.run(FIXTURE, corpus_class="synthetic", phases=NON_RETRIEVAL, **SMALL)

    def test_all_backends_run_every_phase_under_same_parameters(self) -> None:
        for name in M.BACKENDS:
            backend = self.report["backends"][name]
            self.assertEqual(set(backend["phases"]), set(NON_RETRIEVAL), name)
            self.assertEqual(backend["authority_effect"], "none")
        self.assertEqual(self.report["parameters"]["conflict_pairs"], 10)

    def test_baselines_behave_as_controls(self) -> None:
        no_memory = self.report["backends"]["no_memory"]["phases"]
        self.assertEqual(no_memory["scale"]["10"]["recall_at_3"], 0.0)
        self.assertEqual(no_memory["isolation"]["cross_user_leak_rate"], 0.0)
        lexical = self.report["backends"]["lexical_overlap"]["phases"]
        self.assertEqual(lexical["scale"]["30"]["recall_at_3"], 1.0)
        self.assertEqual(lexical["deletion"]["audited_deletion_rate"], 1.0)

    def test_agent_memory_operational_dimensions_stay_separate(self) -> None:
        backend = self.report["backends"]["agent_memory"]
        phases = backend["phases"]
        self.assertEqual(phases["isolation"]["cross_user_leak_rate"], 0.0)
        self.assertEqual(phases["deletion"]["audited_deletion_rate"], 1.0)
        self.assertEqual(phases["scale"]["30"]["recall_at_3"], 1.0)
        self.assertNotIn("required_isolation_domain_missing", backend["governance"]["isolation"]["refusal_reasons"])
        self.assertEqual(set(backend["governance"]["isolation"]["candidate_scopes"]), {"domain_eligible"})
        for key in ("new_fact_rate", "staleness_rate", "dual_version_rate"):
            self.assertIn(key, phases["conflict"])
        self.assertIn("boundary", backend)

    def test_provenance_and_claim_boundaries(self) -> None:
        report = self.report
        self.assertEqual(report["upstream"]["revision"], M.UPSTREAM_REVISION)
        self.assertEqual(report["upstream"]["data_license"], "ODC-By-1.0")
        self.assertIn("WildChat-4.8M", report["upstream"]["data_attribution"])
        self.assertFalse(report["input"]["matches_upstream_release"])
        self.assertEqual(report["comparability"]["status"], "synthetic-smoke-only")
        self.assertEqual(report["comparability"]["upstream_llm_judged_retrieval"], "not_run")
        self.assertEqual(report["claim_boundary"]["aggregate_memory_health_score"], "not_defined")
        self.assertTrue(report["dimensions"]["llm_portability"].startswith("not_exercised"))
        for key in ("agent_memory_revision", "python", "started_at", "finished_at"):
            self.assertIn(key, report["execution"])


@unittest.skipUnless(HAS_NUMPY, "upstream-compatible record sampling requires numpy")
class RetrievalPhaseTests(unittest.TestCase):
    def test_exact_source_recall_and_upstream_sampling(self) -> None:
        report = M.run(
            FIXTURE,
            corpus_class="synthetic",
            phases=("retrieval",),
            retrieval_records=12,
            group_size=3,
            **{key: value for key, value in SMALL.items()},
        )
        for name, expected in (("no_memory", 0.0), ("lexical_overlap", 1.0), ("agent_memory", 1.0)):
            retrieval = report["backends"][name]["phases"]["retrieval"]
            self.assertEqual(retrieval["records"], 12)
            self.assertEqual(retrieval["exact_source_recall_at_k"], expected, name)
            self.assertEqual(retrieval["upstream_llm_judged_recall_at_k"], "not_run")
        self.assertEqual(report["input"]["selection"]["records"], 12)

    def test_load_records_is_seeded_stratified_and_source_unique(self) -> None:
        first = M.load_records(FIXTURE, 6, 2027)
        self.assertEqual(first, M.load_records(FIXTURE, 6, 2027))
        self.assertEqual(len({row["source_id"] for row in first}), 6)
        self.assertEqual(sorted(row["event_type"] for row in first).count("PERSONAL_FACT"), 3)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "dup.jsonl"
            rows = FIXTURE.read_text(encoding="utf-8").splitlines()
            path.write_text("\n".join(rows + rows[:2]) + "\n", encoding="utf-8")
            self.assertEqual(len(M.load_records(path, 12, 2027)), 12)
            with self.assertRaisesRegex(ValueError, "source-unique"):
                M.load_records(path, 13, 2027)


if __name__ == "__main__":
    unittest.main()
