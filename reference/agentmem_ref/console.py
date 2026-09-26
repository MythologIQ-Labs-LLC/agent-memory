"""Installed ``agent-memory`` entry point.

Routes evaluation and Gauntlet commands outside the runtime package. Keeping dispatch at
the package top level preserves the architectural boundary: evaluation/qualification may
observe a runtime or external system, but the runtime layer never imports those systems.
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["benchmark"]:
        from .evaluation.cli import main as evaluation_main

        return evaluation_main(args[1:])
    if args[:1] == ["gauntlet"]:
        from .evaluation.gauntlet_cli import main as gauntlet_main

        return gauntlet_main(args[1:])
    from .runtime.cli import main as runtime_main

    return runtime_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
