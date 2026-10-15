#!/usr/bin/env python3
"""Run the frozen LongMemEval runner with an explicit facade ``return_selection`` (#819).

``reference/run_longmemeval.py`` is pinned by blob in the frozen LongMemEval lanes, so it is not
edited. This wrapper fixes the ``return_selection`` keyword of every ``AgentMemory.recall`` in
the process (contract 1.9.0) and records the choice in the report's
``execution.agent_memory_configuration``, then runs the unmodified runner's ``main``. With
``ranked_prefix`` the facade returns the contract 1.4.0 ranked prefix, so a run must reproduce a
pre-1.9.0 ranking exactly. Every other runner argument is passed through.

    python scripts/run_longmemeval_return_selection.py ranked_prefix -- --input ... --output ...
"""

from __future__ import annotations

import functools
import sys
from pathlib import Path

REFERENCE = Path(__file__).resolve().parents[1] / "reference"
sys.path.insert(0, str(REFERENCE))

import run_longmemeval  # noqa: E402
from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.runtime.return_selection import RETURN_SELECTIONS  # noqa: E402


def install(selection: str) -> None:
    if selection not in RETURN_SELECTIONS:
        raise SystemExit(f"return_selection must be one of {RETURN_SELECTIONS}")
    original = AgentMemory.recall
    if getattr(original, "_return_selection_fixed", None) is not None:
        raise SystemExit("return_selection already fixed in this process")

    @functools.wraps(original)
    def recall(self, query, **kwargs):
        if "return_selection" in kwargs:
            raise RuntimeError("the runner must not pass return_selection itself")
        return original(self, query, return_selection=selection, **kwargs)

    recall._return_selection_fixed = selection
    AgentMemory.recall = recall
    configure = run_longmemeval.configure_agent_memory

    @functools.wraps(configure)
    def configure_recording(**kwargs):
        configuration = configure(**kwargs)
        run_longmemeval._AGENT_MEMORY_CONFIGURATION["return_selection"] = selection
        configuration["return_selection"] = selection
        return configuration

    run_longmemeval.configure_agent_memory = configure_recording


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] != "--":
        raise SystemExit(__doc__)
    install(argv[0])
    sys.argv = ["run_longmemeval.py", *argv[2:]]
    return run_longmemeval.main()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
