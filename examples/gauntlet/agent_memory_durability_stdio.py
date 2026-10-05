#!/usr/bin/env python3
"""stdio transport wrapper for the Agent Memory public durability contestant.

The memory behavior remains in the dedicated durability adapter module, which translates
neutral Gauntlet operations only into the supported public ``AgentMemory`` facade. This
file contributes transport framing and repository-local import bootstrap only, not memory
semantics.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Public Gauntlet runs may execute this file directly from a repository checkout where
# the editable package is not installed. Add only the repository's reference package root,
# matching other repo-local executable harnesses. No benchmark behavior is added here.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_REFERENCE_ROOT = _REPO_ROOT / "reference"
if str(_REFERENCE_ROOT) not in sys.path:
    sys.path.insert(0, str(_REFERENCE_ROOT))

from agentmem_ref.evaluation.gauntlet_agent_memory_durability import (  # noqa: E402
    agent_memory_durability_adapter,
)
from agentmem_ref.evaluation.gauntlet_contract import CONTRACT_VERSION  # noqa: E402


def _transport_error(request: dict[str, Any], exc: Exception) -> dict[str, Any]:
    return {
        "contract_family": "agent-memory-gauntlet-operation",
        "contract_version": CONTRACT_VERSION,
        "direction": "response",
        "operation": str(request.get("operation", "health")),
        "request_id": str(request.get("request_id", "transport-parse-error")),
        "status": "adapter_error",
        "result": None,
        "error": {
            "source": "system_adapter",
            "code": "adapter_transport_error",
            "message": f"{type(exc).__name__}: {exc}",
        },
        "timing": {"elapsed_ms": 0.0},
        "adapter_evidence": {
            "adapter_kind": "agent_memory_public_durability_stdio",
            "transport_only": True,
        },
        "authority_effect": "none",
    }


def main() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        request: dict[str, Any] = {}
        try:
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError("request must decode to an object")
            request = value
            response = agent_memory_durability_adapter(request)
        except Exception as exc:  # noqa: BLE001 - transport must convert failures into evidence
            response = _transport_error(request, exc)
        print(json.dumps(response, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
