"""Installed ``agent-memory`` entry point.

Routes ``agent-memory benchmark ...`` to the Memory Evaluation subsystem and every other
command to the runtime CLI. Keeping this dispatch at the package top level preserves the
boundary documented in ``docs/53-memory-evaluation-subsystem.md``: evaluation may observe
the runtime, but the runtime layer never imports evaluation.
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["benchmark"]:
        from .evaluation.cli import main as evaluation_main

        return evaluation_main(args[1:])
    from .runtime.cli import main as runtime_main

    return runtime_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
