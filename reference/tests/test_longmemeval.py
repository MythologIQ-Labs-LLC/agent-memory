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
RUNNER = REFERENCE / "run_longmemeval.py"
FIXTURE = REFERENCE / "fixtures" / "benchmarks" / "longmemeval" / "synthetic.json"
if str(REFERENCE) not in sys.path:
    sys.path.insert(0, str(REFERENCE))


def _module():
    spec = importlib.util.spec_from_file_location("run_longmemeval", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


M = _module()


def _row(question_id: str) -> dict:
    return next(row for row in json.loads(FIXTURE.read_text(encoding="utf-8")) if row["question_id"] == question_id)


class UpstreamSemanticsTests(unittest.TestCase):
    """Pin the replicated upstream LongMemEval retrieval semantics."""

    def test_corpus_indexes_user_turns_only(self) -> None:
        items, _ = M.corpus(_row("syn_single_editor"), "session")
        self.assertNotIn("I will keep the VS Code preference", items[0]["text"])
        self.assertIn("I prefer VS Code", items[0]["text"])
        turns, gold = M.corpus(_row("syn_single_editor"), "turn")
        self.assertEqual([item["id"] for item in turns], ["answer_syn_editor_1_1", "syn_filler_lunch_1", "syn_filler_music_1"])
        self.assertEqual(gold, ["answer_syn_editor_1_1"])

    def test_answer_session_without_user_answer_is_relabelled_noans(self) -> None:
        items, gold = M.corpus(_row("syn_multi_pets"), "session")
        self.assertIn("noans_syn_pets_3", [item["id"] for item in items])
        self.assertEqual(gold, ["answer_syn_pets_1", "answer_syn_pets_2"])

    def test_abstention_is_identified_by_question_id_not_empty_gold(self) -> None:
        row = _row("syn_bicycle_abs")
        self.assertTrue(row["answer_session_ids"])
        self.assertTrue(M.is_abstention(row))
        self.assertTrue(M.corpus(row, "session")[1])

    def test_assistant_only_evidence_has_no_user_target(self) -> None:
        self.assertFalse(M.has_user_target(_row("syn_assistant_recipe")))
        self.assertTrue(M.has_user_target(_row("syn_single_editor")))

    def test_ndcg_matches_upstream_dcg_convention(self) -> None:
        corpus_ids = ["answer_a_1", "answer_b_1", "noans_c_1"]
        gold = ["answer_a_1", "answer_b_1"]
        # upstream dcg: rel[0] + sum(rel[i] / log2(i + 1)) for i >= 1 (1-based position i + 1)
        _, recall_all, ndcg = M.evaluate_retrieval(["noans_c_1", "answer_a_1", "answer_b_1"], gold, corpus_ids, 5)
        self.assertEqual(recall_all, 1.0)
        self.assertAlmostEqual(ndcg, (1.0 + 1.0 / 1.584962500721156) / 2.0)
        _, recall_all, ndcg = M.evaluate_retrieval(["answer_b_1"], gold, corpus_ids, 5)
        self.assertEqual(recall_all, 0.0)
        self.assertAlmostEqual(ndcg, 0.5)

    def test_turn_to_session_expands_k_to_distinct_sessions(self) -> None:
        corpus_ids = ["answer_s1_1", "answer_s1_3", "x_s2_1", "x_s3_1"]
        ranked = ["answer_s1_1", "answer_s1_3", "x_s2_1", "x_s3_1"]
        recall_any, recall_all, _ = M.evaluate_retrieval_turn2session(ranked, ["answer_s1_1"], corpus_ids, 2)
        self.assertEqual((recall_any, recall_all), (1.0, 1.0))


class LongMemEvalProfileTests(unittest.TestCase):
    def test_denominators_exclude_abstention_and_no_target_questions(self) -> None:
        report = M.run(FIXTURE, corpus_class="synthetic", include_agent_memory=False)
        self.assertEqual(report["input"]["question_count"], 5)
        self.assertEqual(report["input"]["abstention_question_count"], 1)
        self.assertEqual(report["input"]["no_user_target_question_count"], 1)
        for granularity in ("session", "turn"):
            for backend in report["planes"][granularity]["backends"].values():
                aggregate = backend["aggregate"]
                self.assertEqual(aggregate["evaluated_question_count"], 3)
                self.assertEqual(aggregate["excluded_abstention_count"], 1)
                self.assertEqual(aggregate["excluded_no_user_target_count"], 1)
                self.assertFalse(aggregate["abstention_diagnostic"]["upstream_metric"])
                self.assertEqual(set(aggregate["headline"]), set(M.HEADLINE[granularity]))
        session = report["planes"]["session"]["backends"]
        self.assertEqual(session["no_memory"]["aggregate"]["headline"]["recall_all@5"], 0.0)
        self.assertGreater(session["lexical_overlap"]["aggregate"]["headline"]["recall_all@5"], 0.0)
        self.assertIn("turn_to_session", report["planes"]["turn"]["backends"]["lexical_overlap"]["aggregate"]["metrics"])

    def test_claim_boundaries_and_provenance_are_recorded(self) -> None:
        report = M.run(FIXTURE, corpus_class="synthetic", include_agent_memory=False)
        self.assertEqual(report["comparability"]["status"], "synthetic-smoke-only")
        self.assertEqual(report["comparability"]["official_longmemeval_qa_score"], "not_computed")
        self.assertFalse(report["claim_boundary"]["answer_generation_quality_measured"])
        self.assertEqual(report["claim_boundary"]["aggregate_memory_health_score"], "not_defined")
        self.assertEqual(report["upstream"]["revision"], M.UPSTREAM_REVISION)
        self.assertEqual(len(report["input"]["sha256"]), 64)
        execution = report["execution"]
        for key in ("agent_memory_revision", "python", "started_at", "finished_at", "wall_seconds"):
            self.assertIn(key, execution)
        self.assertIsInstance(execution["resource_consumption"]["peak_rss_mb_process"], (float, type(None)))

    def test_knowledge_update_currentness_slice_is_separate(self) -> None:
        report = M.run(FIXTURE, corpus_class="synthetic", include_agent_memory=False)
        backend = report["planes"]["session"]["backends"]["lexical_overlap"]
        self.assertIn("knowledge-update", backend["by_question_type"])
        currentness = backend["currentness"]
        self.assertEqual(currentness["knowledge_update"]["evaluated_question_count"], 1)
        self.assertFalse(currentness["latest_gold_ranked_first"]["upstream_metric"])
        self.assertEqual(currentness["latest_gold_ranked_first"]["applicable_question_count"], 1)

    def test_latest_gold_first_diagnostic(self) -> None:
        dates = {"answer_old": "2026/08/10 (Mon) 09:00", "answer_new": "2026/09/09 (Wed) 09:00"}
        gold = ["answer_new", "answer_old"]
        self.assertTrue(M._latest_gold_first(["answer_new", "answer_old"], gold, dates))
        self.assertFalse(M._latest_gold_first(["answer_old", "answer_new"], gold, dates))
        self.assertFalse(M._latest_gold_first(["answer_old"], gold, dates))
        self.assertIsNone(M._latest_gold_first(["answer_new"], ["answer_new"], dates))

    def test_subset_is_deterministic_seeded_and_order_preserving(self) -> None:
        first = M.run(FIXTURE, corpus_class="synthetic", subset_size=3, include_agent_memory=False)
        second = M.run(FIXTURE, corpus_class="synthetic", subset_size=3, include_agent_memory=False)
        other = M.run(FIXTURE, corpus_class="synthetic", subset_size=3, subset_seed="other", include_agent_memory=False)
        self.assertEqual(first["input"]["selection"], second["input"]["selection"])
        self.assertEqual(first["input"]["selection"]["size"], 3)
        ids = [row["question_id"] for row in first["planes"]["session"]["backends"]["no_memory"]["rows"]]
        source = [row["question_id"] for row in json.loads(FIXTURE.read_text(encoding="utf-8"))]
        self.assertEqual(ids, [value for value in source if value in ids])
        self.assertNotEqual(
            first["input"]["selection"]["question_ids_sha256"], other["input"]["selection"]["question_ids_sha256"]
        )
        with self.assertRaises(ValueError):
            M.run(FIXTURE, corpus_class="synthetic", subset_size=2, max_questions=2, include_agent_memory=False)

    def test_runtime_failures_are_recorded_not_hidden(self) -> None:
        def broken(question, items, row_index, row=None):
            raise RuntimeError("boom")

        with mock.patch.dict(M.RETRIEVERS, {"lexical_overlap": broken}):
            report = M.run(FIXTURE, corpus_class="synthetic", backends=("lexical_overlap",), granularities=("session",))
        backend = report["planes"]["session"]["backends"]["lexical_overlap"]
        self.assertEqual(backend["failures"]["runtime_failure_count"], 5)
        self.assertEqual(backend["aggregate"]["evaluated_question_count"], 3)
        self.assertEqual(backend["aggregate"]["headline"]["recall_all@5"], 0.0)
        self.assertTrue(all(row["runtime_error"] == "RuntimeError: boom" for row in backend["rows"]))

    def test_agent_memory_backend_uses_public_facade_and_governed_admission(self) -> None:
        from agentmem_ref import AgentMemory

        seen: list[tuple[str, str]] = []
        original = AgentMemory.remember

        def spy(self, target_reference, fact_text, **kwargs):
            seen.append((target_reference, fact_text))
            return original(self, target_reference, fact_text, **kwargs)

        with mock.patch.object(AgentMemory, "remember", spy):
            report = M.run(FIXTURE, corpus_class="synthetic", backends=("agent_memory",))
        corpus_ids = {
            item["id"]
            for row in json.loads(FIXTURE.read_text(encoding="utf-8"))
            for granularity in ("session", "turn")
            for item in M.corpus(row, granularity)[0]
        }
        for target_reference, fact_text in seen:
            self.assertTrue(target_reference.startswith("memory:longmemeval:"))
            self.assertFalse(any(item_id in target_reference or item_id in fact_text for item_id in corpus_ids))
        for granularity in ("session", "turn"):
            backend = report["planes"][granularity]["backends"]["agent_memory"]
            self.assertEqual(backend["authority_effect"], "none")
            self.assertIn("governed admission", backend["boundary"])
            self.assertEqual(
                backend["failures"],
                {"runtime_failure_count": 0, "ingestion_failure_count": 0, "out_of_corpus_returned_count": 0},
            )
            governance = backend["governance"]
            self.assertGreaterEqual(governance["candidate_count_total"], governance["admitted_count_total"])
            self.assertEqual(governance["unmapped_admitted_count_total"], 0)
            for row in backend["rows"]:
                self.assertEqual(len(row["ranked_top"]), min(row["admitted_count"], M.REPORTED_RANK_DEPTH))
            self.assertGreater(backend["aggregate"]["headline"]["recall_all@5"], 0.0)

    def test_declared_budget_ranks_the_facade_prefix(self) -> None:
        # Contract 1.4.0 (#670): budget=k ranks `returned`; unbudgeted runs are unchanged.
        self.assertEqual(M._AGENT_MEMORY_CONFIGURATION["budget"], "none")
        unbudgeted = M.run(FIXTURE, corpus_class="synthetic", backends=("agent_memory",))
        try:
            configuration = M.configure_agent_memory(budget=2)
            self.assertEqual(configuration["budget"], "2")
            budgeted = M.run(FIXTURE, corpus_class="synthetic", backends=("agent_memory",))
        finally:
            M.configure_agent_memory()
        self.assertEqual(budgeted["execution"]["agent_memory_configuration"]["budget"], "2")
        self.assertEqual(unbudgeted["execution"]["agent_memory_configuration"]["budget"], "none")
        for granularity in ("session", "turn"):
            free = unbudgeted["planes"][granularity]["backends"]["agent_memory"]
            capped = budgeted["planes"][granularity]["backends"]["agent_memory"]
            self.assertEqual(len(free["rows"]), len(capped["rows"]))
            for row_free, row_capped in zip(free["rows"], capped["rows"]):
                self.assertEqual(row_free["return_policy"]["applied"], False)
                self.assertEqual(row_free["return_policy"]["requested_k"], None)
                self.assertEqual(row_capped["return_policy"]["requested_k"], 2)
                self.assertLessEqual(row_capped["returned_count"], 2)
                self.assertEqual(row_capped["ranked_top"], row_free["ranked_top"][:2])
                self.assertEqual(row_capped["admitted_count"], row_free["admitted_count"])
            self.assertEqual(
                capped["governance"]["return_budget_applied_total"],
                sum(1 for row in free["rows"] if row["admitted_count"] > 2),
            )
            self.assertEqual(free["governance"]["return_budget_applied_total"], 0)
        with self.assertRaises(ValueError):
            M.configure_agent_memory(budget=0)
        M.configure_agent_memory()

    def test_temporal_metadata_modes_declare_only_their_fields(self) -> None:
        """#594: ``source_observed_at`` adds the session date as ``observed_at`` and nothing else."""
        from agentmem_ref import AgentMemory

        row = json.loads(FIXTURE.read_text(encoding="utf-8"))[0]
        items, _ = M.corpus(row, "turn")
        writes: list[dict] = []
        recalls: list[dict] = []
        original_remember, original_recall = AgentMemory.remember, AgentMemory.recall

        def remember(self, target_reference, fact_text, **kwargs):
            writes.append(kwargs)
            return original_remember(self, target_reference, fact_text, **kwargs)

        def recall(self, query, **kwargs):
            recalls.append(kwargs)
            return original_recall(self, query, **kwargs)

        expected = {
            "none": (False, None),
            "source_observed_at": (True, None),
            "host_declared": (True, M._iso_date(row["question_date"])),
        }
        try:
            with mock.patch.object(AgentMemory, "remember", remember), mock.patch.object(AgentMemory, "recall", recall):
                for mode, (observed, reference_time) in expected.items():
                    writes.clear()
                    recalls.clear()
                    M.configure_agent_memory(temporal_metadata=mode)
                    outcome = M._agent_memory(row["question"], items, 0, row)
                    self.assertEqual(len(writes), len(items))
                    for item, kwargs in zip(items, writes):
                        self.assertEqual(kwargs, {"observed_at": M._iso_date(item["date"])} if observed else {})
                    self.assertEqual(recalls, [{"reference_time": reference_time}])
                    if observed:
                        self.assertEqual(outcome["observed_at_mapped_count"], len(items))
                        self.assertEqual(outcome["observed_at_unmapped_count"], 0)
                    else:
                        self.assertNotIn("observed_at_mapped_count", outcome)
        finally:
            M.configure_agent_memory()

    def test_unparseable_session_date_is_unmapped_not_invented(self) -> None:
        M.configure_agent_memory(temporal_metadata="source_observed_at")
        try:
            items = [{"id": "s_1", "text": "I live in Lisbon.", "date": "sometime in May"}]
            outcome = M._agent_memory("Where do I live?", items, 0, {"question_date": "2023/05/30 (Tue) 23:40"})
        finally:
            M.configure_agent_memory()
        self.assertEqual((outcome["observed_at_mapped_count"], outcome["observed_at_unmapped_count"]), (0, 1))

    def test_invalid_haystack_lengths_fail_closed(self) -> None:
        value = json.loads(FIXTURE.read_text(encoding="utf-8"))
        value[0]["haystack_dates"] = []
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "haystack arrays"):
                M.run(path, corpus_class="synthetic", include_agent_memory=False)

    def test_repeated_identical_sessions_are_indexed_like_upstream(self) -> None:
        value = json.loads(FIXTURE.read_text(encoding="utf-8"))
        row = value[0]
        row["haystack_session_ids"].append(row["haystack_session_ids"][1])
        row["haystack_dates"].append("2026/08/20 (Thu) 09:00")
        row["haystack_sessions"].append(row["haystack_sessions"][1])
        items, gold = M.corpus(row, "session")
        self.assertEqual([item["id"] for item in items].count("syn_filler_lunch"), 2)
        self.assertEqual(gold, ["answer_syn_editor_1"])
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "repeat.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            report = M.run(path, corpus_class="synthetic", include_agent_memory=False)
            self.assertEqual(report["input"]["duplicate_session_id_question_count"], 1)
            row["haystack_sessions"][-1] = [{"role": "user", "content": "different content"}]
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "different content"):
                M.run(path, corpus_class="synthetic", include_agent_memory=False)

    def test_duplicate_question_ids_fail_closed(self) -> None:
        value = json.loads(FIXTURE.read_text(encoding="utf-8"))
        value.append(value[0])
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "dup.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicates question_id"):
                M.run(path, corpus_class="synthetic", include_agent_memory=False)


if __name__ == "__main__":
    unittest.main()


class ExternalBackendSeamTests(unittest.TestCase):
    """System-neutral backend registration for same-harness lanes (#640)."""

    def setUp(self) -> None:
        self._retrievers = dict(M.RETRIEVERS)
        self._external = dict(M.EXTERNAL_BACKENDS)

    def tearDown(self) -> None:
        M.RETRIEVERS.clear()
        M.RETRIEVERS.update(self._retrievers)
        M.EXTERNAL_BACKENDS.clear()
        M.EXTERNAL_BACKENDS.update(self._external)

    @staticmethod
    def _identity(**overrides: object) -> dict:
        identity = {
            "system_id": "ext-system",
            "system_kind": "external_memory",
            "system_revision": "a" * 40,
            "adapter_id": "reference/example_bridge.py",
            "adapter_revision": "b" * 40,
            "configuration": {"mode": "explicit"},
        }
        identity.update(overrides)
        return identity

    @staticmethod
    def _echo_lexical(question, items, row_index, row=None):
        return {
            "ranked": M._lexical_rank(question, items),
            "ingest_seconds": 0.01,
            "recall_seconds": 0.002,
            "unmapped_result_count": 1,
            "ext_namespace": f"ns-{row_index}",
        }

    def test_registration_validates_name_identity_and_kind(self) -> None:
        with self.assertRaisesRegex(ValueError, "already registered"):
            M.register_external_backend("agent_memory", self._echo_lexical, identity=self._identity())
        for bad in ("", "Ext", "ext system", "1ext", "x" * 70):
            with self.assertRaisesRegex(ValueError, "name must match"):
                M.register_external_backend(bad, self._echo_lexical, identity=self._identity())
        with self.assertRaisesRegex(ValueError, "missing \\['system_revision'\\]"):
            identity = self._identity()
            del identity["system_revision"]
            M.register_external_backend("ext_system", self._echo_lexical, identity=identity)
        with self.assertRaisesRegex(ValueError, "system_kind must be one of"):
            M.register_external_backend("ext_system", self._echo_lexical, identity=self._identity(system_kind="agent_memory"))
        with self.assertRaisesRegex(ValueError, "identity.system_revision must be a non-empty string"):
            M.register_external_backend("ext_system", self._echo_lexical, identity=self._identity(system_revision=""))
        with self.assertRaisesRegex(ValueError, "configuration must be an object"):
            M.register_external_backend("ext_system", self._echo_lexical, identity=self._identity(configuration="explicit"))
        with self.assertRaises(TypeError):
            M.register_external_backend("ext_system", "not-callable", identity=self._identity())
        recorded = M.register_external_backend("ext_system", self._echo_lexical, identity=self._identity())
        self.assertEqual(recorded["backend"], "ext_system")
        self.assertEqual(recorded["authority_effect"], "none")
        with self.assertRaisesRegex(ValueError, "already registered"):
            M.register_external_backend("ext_system", self._echo_lexical, identity=self._identity())
        self.assertNotIn("ext_system", M.BACKENDS, "built-in backend tuple is untouched")

    def test_external_backend_is_scored_by_the_same_evaluator_and_bound_in_the_report(self) -> None:
        identity = self._identity()
        M.register_external_backend("ext_system", self._echo_lexical, identity=identity)
        identity["configuration"]["mode"] = "mutated after registration"
        report = M.run(FIXTURE, corpus_class="synthetic", backends=("lexical_overlap", "ext_system"), granularities=("session", "turn"))
        self.assertEqual(report["execution"]["backends"], ["lexical_overlap", "ext_system"])
        recorded = report["execution"]["external_backends"]
        self.assertEqual(list(recorded), ["ext_system"])
        self.assertEqual(recorded["ext_system"]["system_id"], "ext-system")
        self.assertEqual(recorded["ext_system"]["configuration"], {"mode": "explicit"}, "identity is copied at registration")
        self.assertEqual(recorded["ext_system"]["authority_effect"], "none")
        for plane in ("session", "turn"):
            backends = report["planes"][plane]["backends"]
            external = backends["ext_system"]
            self.assertEqual(external["aggregate"], backends["lexical_overlap"]["aggregate"], "same ranking, same evaluator, same numbers")
            self.assertEqual(external["external_system"], {"system_id": "ext-system", "system_revision": "a" * 40, "unmapped_result_count_total": len(external["rows"])})
            self.assertIn("external system ext-system", external["boundary"])
            self.assertNotIn("governance", external, "no governed admission path is invented for an external system")
            self.assertAlmostEqual(external["timing"]["ingest_seconds_total"], 0.01 * len(external["rows"]), places=6)
            self.assertAlmostEqual(external["timing"]["recall_seconds_max"], 0.002, places=6)
            self.assertNotIn("ingest_seconds_total", backends["lexical_overlap"]["timing"])
            for index, row in enumerate(external["rows"]):
                self.assertEqual(row["ext_namespace"], f"ns-{index}")
                self.assertEqual(row["unmapped_result_count"], 1)
        with self.assertRaisesRegex(ValueError, "unknown backend"):
            M.run(FIXTURE, corpus_class="synthetic", backends=("never_registered",), granularities=("session",))

    def test_load_external_backends_imports_module_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            module_path = Path(temporary) / "seam_probe_bridge.py"
            module_path.write_text(
                "def install(register):\n"
                "    register('probe_system', lambda q, items, i, row=None: {'ranked': [item['id'] for item in items]},\n"
                "             identity={'system_id': 'probe', 'system_kind': 'other', 'system_revision': 'c' * 40,\n"
                "                       'adapter_id': 'probe.py', 'adapter_revision': 'd' * 40, 'configuration': {}})\n"
                "    return 'probe_system'\n"
                "def liar(register):\n"
                "    return ['never_registered']\n"
                "not_callable = 1\n",
                encoding="utf-8",
            )
            sys.path.insert(0, temporary)
            try:
                self.assertEqual(M.load_external_backends(["seam_probe_bridge:install"]), ["probe_system"])
                self.assertIn("probe_system", M.EXTERNAL_BACKENDS)
                with self.assertRaisesRegex(ValueError, "did not register it"):
                    M.load_external_backends(["seam_probe_bridge:liar"])
                with self.assertRaisesRegex(ValueError, "callable install entry"):
                    M.load_external_backends(["seam_probe_bridge:not_callable"])
                with self.assertRaisesRegex(ValueError, "MODULE:ENTRY"):
                    M.load_external_backends(["seam_probe_bridge"])
                output = Path(temporary) / "report.json"
                M.RETRIEVERS.pop("probe_system")
                M.EXTERNAL_BACKENDS.pop("probe_system")
                argv = [
                    "run_longmemeval.py",
                    "--input", str(FIXTURE),
                    "--external-backend", "seam_probe_bridge:install",
                    "--backend", "probe_system",
                    "--granularity", "session",
                    "--omit-rows",
                    "--output", str(output),
                ]
                with mock.patch.object(sys, "argv", argv):
                    self.assertEqual(M.main(), 0)
                report = json.loads(output.read_text(encoding="utf-8"))
                self.assertEqual(report["execution"]["backends"], ["probe_system"])
                self.assertEqual(report["execution"]["external_backends"]["probe_system"]["system_id"], "probe")
                self.assertNotIn("rows", report["planes"]["session"]["backends"]["probe_system"])
            finally:
                sys.path.remove(temporary)
                sys.modules.pop("seam_probe_bridge", None)
