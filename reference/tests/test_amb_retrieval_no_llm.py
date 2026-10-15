"""Retrieval-only no-LLM guard for the frozen AMB CLI.

The unit tests run everywhere. The ``RealFrozenAMB`` tests run only when ``AMB_ROOT`` names a
checkout of the frozen revision whose dependencies are installed; they exercise the actual
``memory_bench`` package, not a synthetic one. Setup: the Reproduce section of
reports/benchmarks/amb-local-execution/2026-10-15-precisionmembench-single-turn/README.md.
"""

from __future__ import annotations

import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

import amb_agent_memory_bridge as bridge
import amb_retrieval_no_llm as guard
import run_amb_external

AMB_ROOT = os.environ.get("AMB_ROOT")
LLM_ENV = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY")


class RetrievalNoLLMGuardTests(unittest.TestCase):
    def test_requested_mode_reads_the_amb_mode_option(self):
        cases = [
            (["run", "--mode", "retrieval", "--split", "single-turn"], "retrieval"),
            (["run", "--mode=retrieval"], "retrieval"),
            (["run", "--mode", "rag"], "rag"),
            (["run", "--split", "s"], None),
            (["run", "--mode"], None),
        ]
        for args, expected in cases:
            with self.subTest(args=args):
                self.assertEqual(guard.requested_mode(args), expected)

    def test_guard_patches_exactly_the_three_construction_points(self):
        cli = types.SimpleNamespace(_resolve_gemini_key="original", get_answer_llm="original", other="kept")
        runner = types.SimpleNamespace(GeminiJudge="original", EvalRunner="kept")
        record = guard.install_retrieval_no_llm_guard(cli, runner)
        self.assertIsNone(cli._resolve_gemini_key())
        self.assertIsNone(cli.get_answer_llm())
        self.assertIs(runner.GeminiJudge, guard.RefusingJudge)
        self.assertEqual((cli.other, runner.EvalRunner), ("kept", "kept"))
        self.assertEqual(record["patched_symbols"], list(guard.PATCHED_SYMBOLS))
        self.assertEqual(record["llm_clients_constructed"], 0)

    def test_refusing_judge_refuses_every_use(self):
        judge = guard.RefusingJudge()
        with self.assertRaises(guard.LLMUseRefused):
            judge.score("q", "a", ["g"], None)
        with self.assertRaises(guard.LLMUseRefused):
            _ = judge._llm.model_id
        with self.assertRaises(guard.LLMUseRefused):
            judge._llm.generate("prompt", None)

    def test_runner_flag_opts_out_of_the_guard(self):
        args = run_amb_external.parse_args(["--amb-root", "x", "--no-retrieval-guard", "--", "run", "--mode", "retrieval"])
        self.assertTrue(args.no_retrieval_guard)
        self.assertEqual(args.amb_args, ["run", "--mode", "retrieval"])
        self.assertFalse(run_amb_external.parse_args(["--amb-root", "x", "--", "run"]).no_retrieval_guard)


@unittest.skipUnless(AMB_ROOT, "AMB_ROOT not set: real frozen AMB checkout unavailable")
class RealFrozenAMBTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(AMB_ROOT).resolve()
        bridge.verify_amb_checkout(self.root)
        saved_env = {key: os.environ.pop(key) for key in LLM_ENV if key in os.environ}
        self.addCleanup(os.environ.update, saved_env)
        src = str(self.root / "src")
        if src not in sys.path:
            sys.path.insert(0, src)
        from memory_bench import cli, runner  # noqa: PLC0415

        self.cli, self.runner = cli, runner
        originals = (cli._resolve_gemini_key, cli.get_answer_llm, runner.GeminiJudge)

        def restore() -> None:
            cli._resolve_gemini_key, cli.get_answer_llm, runner.GeminiJudge = originals

        self.addCleanup(restore)

    def test_frozen_cli_requires_llm_clients_for_retrieval_without_the_guard(self):
        import click  # noqa: PLC0415

        with self.assertRaises(click.exceptions.Exit):
            self.cli._resolve_gemini_key()
        with self.assertRaises(Exception):  # GroqError: no GROQ_API_KEY
            self.cli.get_answer_llm()
        with self.assertRaises(Exception):  # genai.Client(): no API key
            self.runner.EvalRunner()

    def test_frozen_runner_scores_agent_memory_retrieval_under_the_guard(self):
        if not (self.root / ".datasets" / "precisionmembench" / "retrieval.cases.json").is_file():
            self.skipTest("PrecisionMemBench fixtures are not cached in the AMB checkout")
        guard.install_retrieval_no_llm_guard(self.cli, self.runner)
        from memory_bench.dataset import get_dataset  # noqa: PLC0415
        from memory_bench.memory import get_memory_provider  # noqa: PLC0415
        from memory_bench.modes import get_mode  # noqa: PLC0415
        from memory_bench.modes.retrieval import RetrievalMode  # noqa: PLC0415

        bridge.install_amb_agent_memory_provider(self.root, agent_memory_revision="e" * 40)
        mode = get_mode("retrieval", llm=self.cli.get_answer_llm())
        self.assertIsInstance(mode, RetrievalMode)
        self.assertIsNone(mode.llm_id)
        with tempfile.TemporaryDirectory() as output:
            summary = self.runner.EvalRunner(output_dir=Path(output)).run(
                dataset=get_dataset("precisionmembench"),
                split="single-turn",
                memory=get_memory_provider(bridge.AMB_PROVIDER_KEY),
                mode=mode,
                query_limit=3,
            )
        self.assertEqual(summary.total_queries, 3)
        self.assertIsNone(summary.judge_llm)
        self.assertIsNone(summary.answer_llm)


if __name__ == "__main__":
    unittest.main()
