#!/usr/bin/env python3
"""Run pinned vectorize-io/agent-memory-benchmark with the repository-owned providers injected.

Usage example::

    python reference/run_amb_external.py \
      --amb-root /path/to/agent-memory-benchmark \
      -- run --dataset longmemeval --split s --memory agent-memory

Everything after ``--`` is passed to AMB's own Typer CLI. AMB remains responsible
for dataset loading, prompts, answer generation, judging, and result files.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from amb_agent_memory_bridge import AMB_REVISION, install_amb_agent_memory_provider, verify_amb_checkout
from amb_mem0_explicit_bridge import install_amb_mem0_explicit_provider

REPO_ROOT = Path(__file__).resolve().parents[1]


def _repo_revision(root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("Agent Memory benchmark bridge requires a git checkout") from exc
    revision = completed.stdout.strip().lower()
    if len(revision) != 40:
        raise RuntimeError(f"unexpected Agent Memory git revision: {revision!r}")
    return revision


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the pinned external AMB harness with Agent Memory registered as a provider."
    )
    parser.add_argument("--amb-root", type=Path, required=True, help="Checkout of vectorize-io/agent-memory-benchmark")
    parser.add_argument(
        "--amb-revision",
        default=AMB_REVISION,
        help="Exact allowed AMB revision; defaults to the repository-qualified pin.",
    )
    parser.add_argument(
        "amb_args",
        nargs=argparse.REMAINDER,
        help="AMB CLI arguments after '--', for example: -- run --dataset longmemeval --split s --memory agent-memory",
    )
    args = parser.parse_args(argv)
    if args.amb_args and args.amb_args[0] == "--":
        args.amb_args = args.amb_args[1:]
    if not args.amb_args:
        parser.error("AMB CLI arguments are required after '--'")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    amb_root = args.amb_root.resolve()
    amb_revision = verify_amb_checkout(amb_root, args.amb_revision)
    agent_memory_revision = _repo_revision(REPO_ROOT)

    os.environ["AGENT_MEMORY_AMB_REVISION"] = amb_revision
    os.environ["AGENT_MEMORY_EVALUATED_REVISION"] = agent_memory_revision

    install_amb_agent_memory_provider(
        amb_root,
        agent_memory_revision=agent_memory_revision,
    )
    # The Mem0 explicit-memory comparator (#640) registers alongside; it imports mem0 only
    # when prepared, so Agent Memory and BM25 runs never need the Mem0 package.
    install_amb_mem0_explicit_provider(amb_root)

    # Import after registration so CLI help and provider lookup both see Agent Memory.
    from memory_bench import cli as amb_cli  # type: ignore[import-not-found]  # noqa: PLC0415

    sys.argv = ["amb", *args.amb_args]
    amb_cli.app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
