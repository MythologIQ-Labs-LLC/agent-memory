"""Retrieval-only, no-LLM compatibility guard for the frozen AMB CLI.

At the frozen AMB revision, ``amb run --mode retrieval`` constructs three LLM clients that
RetrievalMode never calls:

1. ``memory_bench.cli._resolve_gemini_key()`` exits unless ``GEMINI_API_KEY`` is set;
2. ``memory_bench.cli.get_answer_llm()`` builds the answer client (Groq by default, which
   raises without ``GROQ_API_KEY``) and hands it to ``get_mode``, which RetrievalMode ignores;
3. ``memory_bench.runner.EvalRunner.__init__`` builds ``GeminiJudge()`` (``genai.Client()``,
   which raises without a key), used only for judged, non-retrieval task types.

The guard replaces exactly those three construction points in the loaded modules with
objects that refuse every use, so a retrieval run needs no credential and can never reach
an inference API. AMB's datasets, ``RetrievalMode``, ``EvalRunner.run`` and
``PrecisionMemBenchDataset.score_retrieval`` are not touched: scoring stays AMB's own.
If anything on a run's path does reach an LLM, the run fails loudly instead of scoring.
"""

from __future__ import annotations

from typing import Any

GUARD_VERSION = "1.0.0"
PATCHED_SYMBOLS = (
    "memory_bench.cli._resolve_gemini_key",
    "memory_bench.cli.get_answer_llm",
    "memory_bench.runner.GeminiJudge",
)


class LLMUseRefused(RuntimeError):
    """Raised when a retrieval-only run touches an LLM."""


class _RefusingLLM:
    def __getattr__(self, name: str) -> Any:
        raise LLMUseRefused(f"retrieval-only AMB run attempted LLM use: {name}")


class RefusingJudge:
    """Stands in for ``GeminiJudge``; never constructs a client and refuses every use."""

    def __init__(self, llm: Any = None) -> None:
        self._llm = _RefusingLLM()

    def score(self, *args: Any, **kwargs: Any) -> Any:
        raise LLMUseRefused("retrieval-only AMB run attempted to judge an answer")


def requested_mode(amb_args: list[str]) -> str | None:
    """Return the ``--mode`` value from AMB CLI arguments (AMB's default is ``rag``)."""

    for index, arg in enumerate(amb_args):
        if arg == "--mode" and index + 1 < len(amb_args):
            return amb_args[index + 1]
        if arg.startswith("--mode="):
            return arg.split("=", 1)[1]
    return None


def install_retrieval_no_llm_guard(cli_module: Any, runner_module: Any) -> dict[str, Any]:
    """Patch the three construction points; return a record for the execution identity."""

    cli_module._resolve_gemini_key = lambda: None
    cli_module.get_answer_llm = lambda: None
    runner_module.GeminiJudge = RefusingJudge
    return {
        "guard": "amb_retrieval_no_llm",
        "guard_version": GUARD_VERSION,
        "patched_symbols": list(PATCHED_SYMBOLS),
        "llm_clients_constructed": 0,
        "authority_effect": "none",
    }


__all__ = [
    "GUARD_VERSION",
    "PATCHED_SYMBOLS",
    "LLMUseRefused",
    "RefusingJudge",
    "requested_mode",
    "install_retrieval_no_llm_guard",
]
