"""Persistent stdio fixture adapter for Agent Memory Gauntlet transport conformance."""

from __future__ import annotations

import json
import sys

from .gauntlet_baselines import lexical_adapter


def main() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            response = lexical_adapter(request)
        except Exception as exc:
            print(json.dumps({"fixture_error": f"{type(exc).__name__}: {exc}"}), flush=True)
            continue
        print(json.dumps(response, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
