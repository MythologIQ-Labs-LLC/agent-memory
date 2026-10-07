"""Agent Memory provider bridge for vectorize-io/agent-memory-benchmark (AMB).

The bridge deliberately lives outside AMB. It pins and verifies an external AMB
checkout, then registers Agent Memory as one additional ``MemoryProvider`` at
runtime. AMB continues to own dataset loading, prompts, answer generation, judging,
and output formatting. This module only translates AMB's neutral document/retrieval
surface into the public AgentMemory facade.

External benchmark output remains evidence, never memory authority.

Since bridge 0.2.0 (contract 1.4.0, #670) the bridge asks the facade for the case budget
(``memory.recall(query, budget=k)``) and returns the facade's ``returned`` prefix: truncation
is the runtime's ``ranked-prefix-return-budget`` policy, never a bridge-side cap. ``admitted``
stays the full ranked admitted set and is counted in the raw response.

Since bridge 0.3.0 (contract 1.5.0, #644 plan-644-lanes-v4 L9) the bridge also registers
``agent-memory-shadow``: the same provider with ``recall_control="shadow"`` on retrieve. The
frozen AMB runner stores no provider raw response, so the shadow provider appends one JSON line
per ``retrieve()`` call to the sidecar named by ``AGENT_MEMORY_AMB_RECALL_CONTROL_SIDECAR``
(refusing to retrieve when it is unset). Shadow telemetry is evidence, never authority; the
``agent-memory`` provider is unchanged and writes no sidecar.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from agentmem_ref import AgentMemory

AMB_REPOSITORY = "vectorize-io/agent-memory-benchmark"
AMB_REVISION = "03c1d0f1d27da63034f0931121c858faba512383"
AMB_PROVIDER_KEY = "agent-memory"
AMB_SHADOW_PROVIDER_KEY = "agent-memory-shadow"
BRIDGE_VERSION = "0.3.0"
SIDECAR_ENV = "AGENT_MEMORY_AMB_RECALL_CONTROL_SIDECAR"

_TENANT = "tenant:amb-competitive"
_ACTOR = "agent:amb-competitive"
_PURPOSE = "Independent Agent Memory Benchmark competitive evaluation"


def _git_head(root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(f"unable to resolve git revision for {root}") from exc
    return completed.stdout.strip().lower()


def verify_amb_checkout(root: str | Path, expected_revision: str = AMB_REVISION) -> str:
    """Fail closed unless ``root`` is the exact frozen AMB revision."""

    checkout = Path(root).resolve()
    if not (checkout / "src" / "memory_bench").is_dir():
        raise RuntimeError(f"AMB checkout missing src/memory_bench: {checkout}")
    actual = _git_head(checkout)
    expected = expected_revision.lower()
    if actual != expected:
        raise RuntimeError(f"AMB revision mismatch: expected {expected}, found {actual}")
    return actual


def _scope(user_id: str | None) -> str:
    material = "global" if user_id is None else str(user_id)
    return "amb:scope:" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]


def _logical_id(document_id: str, user_id: str | None) -> str:
    material = f"{user_id or 'global'}\x00{document_id}"
    return "memory:amb:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


def _index_document(document: Any) -> dict[str, Any]:
    return {
        "id": str(document.id),
        "content": str(document.content),
        "user_id": None if document.user_id is None else str(document.user_id),
        "timestamp": None if document.timestamp is None else str(document.timestamp),
        "context": None if getattr(document, "context", None) is None else str(document.context),
        "source_ids": list(getattr(document, "source_ids", None) or [str(document.id)]),
        "tags": list(getattr(document, "tags", None) or []),
    }


def install_amb_agent_memory_provider(
    amb_root: str | Path,
    *,
    agent_memory_revision: str,
) -> type:
    """Register Agent Memory in a loaded-or-loadable pinned AMB checkout.

    ``verify_amb_checkout`` is intentionally separate so tests can exercise the
    translation contract with a tiny synthetic ``memory_bench`` module while the
    production runner always verifies the real external revision first.
    """

    checkout = Path(amb_root).resolve()
    src = str(checkout / "src")
    if src not in sys.path:
        sys.path.insert(0, src)

    from memory_bench.memory import REGISTRY  # type: ignore[import-not-found]
    from memory_bench.memory.base import MemoryProvider  # type: ignore[import-not-found]
    from memory_bench.models import Document  # type: ignore[import-not-found]

    revision = agent_memory_revision.lower()
    if len(revision) != 40 or any(char not in "0123456789abcdef" for char in revision):
        raise ValueError("agent_memory_revision must be an exact 40-hex commit")

    class AgentMemoryAMBProvider(MemoryProvider):
        name = AMB_PROVIDER_KEY
        description = (
            "Agent Memory public facade through a revision-bound external AMB bridge. "
            "AMB owns benchmark ingestion/query/scoring semantics."
        )
        kind = "local"
        provider = "agent-memory"
        variant = "public-facade"
        link = "https://github.com/MythologIQ-Labs-LLC/agent-memory"
        logo = None
        # Separate handles over one durable runtime are intentionally not treated as a
        # multi-writer contract. Keep AMB query fan-out serialized until that contract
        # is independently qualified.
        concurrency = 1
        supports_filters = False

        def __init__(self) -> None:
            self._store_dir: Path | None = None
            self._runtime_root: Path | None = None
            self._index_path: Path | None = None
            self._by_fact: dict[str, dict[str, Any]] = {}
            self._call_index = 0

        def prepare(self, store_dir: Path, unit_ids: set[str] | None = None, reset: bool = True) -> None:
            self._store_dir = Path(store_dir)
            self._runtime_root = self._store_dir / "agent-memory-runtime"
            self._index_path = self._store_dir / "agent-memory-amb-index.json"
            if reset:
                shutil.rmtree(self._runtime_root, ignore_errors=True)
                self._index_path.unlink(missing_ok=True)
            self._runtime_root.mkdir(parents=True, exist_ok=True)
            self._by_fact = {}
            if self._index_path.is_file():
                payload = json.loads(self._index_path.read_text(encoding="utf-8"))
                if payload.get("bridge_version") != BRIDGE_VERSION:
                    raise RuntimeError("Agent Memory AMB sidecar bridge version mismatch")
                if payload.get("agent_memory_revision") != revision:
                    raise RuntimeError("Agent Memory AMB sidecar revision mismatch")
                records = payload.get("records")
                if not isinstance(records, dict):
                    raise RuntimeError("Agent Memory AMB sidecar records are malformed")
                self._by_fact = {str(key): dict(value) for key, value in records.items()}

        recall_control = "off"

        def _sidecar_path(self) -> Path | None:
            if self.recall_control != "shadow":
                return None
            value = os.environ.get(SIDECAR_ENV)
            if not value:
                raise RuntimeError(f"{AMB_SHADOW_PROVIDER_KEY} requires {SIDECAR_ENV}: shadow telemetry must reach evidence")
            return Path(value)

        def _append_sidecar(self, path: Path, query: str, scope: str, budget: int, outcome: dict) -> None:
            record = dict(outcome.get("recall_control") or {})
            usage = dict(record.get("usage") or {})
            usage.pop("elapsed_ms", None)
            record["usage"] = usage
            line = {
                "call_index": self._call_index,
                "scope": scope,
                "query_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
                "budget": budget,
                "recall_control": record,
            }
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(line, sort_keys=True, separators=(",", ":")) + "\n")
            self._call_index += 1

        def _require_prepared(self) -> Path:
            if self._runtime_root is None or self._index_path is None:
                raise RuntimeError("Agent Memory AMB provider must be prepared before use")
            return self._runtime_root

        def _save_index(self) -> None:
            self._require_prepared()
            assert self._index_path is not None
            payload = {
                "bridge_version": BRIDGE_VERSION,
                "agent_memory_revision": revision,
                "amb_revision": AMB_REVISION,
                "records": self._by_fact,
            }
            self._index_path.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

        def ingest(self, documents: list[Document]) -> None:
            root = self._require_prepared()
            grouped: dict[str, list[Document]] = {}
            for document in documents:
                grouped.setdefault(_scope(document.user_id), []).append(document)

            for scope, scoped_documents in grouped.items():
                with AgentMemory.open(
                    root,
                    tenant=_TENANT,
                    actor_id=_ACTOR,
                    scope=scope,
                    purpose=_PURPOSE,
                ) as memory:
                    for document in scoped_documents:
                        outcome = memory.remember(
                            _logical_id(str(document.id), document.user_id),
                            str(document.content),
                            observed_at=None if document.timestamp is None else str(document.timestamp),
                        )
                        if not outcome.get("committed") or not outcome.get("fact_uuid"):
                            raise RuntimeError(
                                f"Agent Memory refused AMB document {document.id!r}: "
                                f"{outcome.get('refusal') or outcome.get('outcome')}"
                            )
                        self._by_fact[str(outcome["fact_uuid"])] = _index_document(document)
            self._save_index()

        def retrieve(
            self,
            query: str,
            k: int = 10,
            user_id: str | None = None,
            query_timestamp: str | None = None,
        ) -> tuple[list[Document], dict | None]:
            root = self._require_prepared()
            budget = int(k)
            if budget < 1:
                raise ValueError("AMB case budget must be at least 1")
            sidecar = self._sidecar_path()
            open_kwargs = {"recall_control": "shadow"} if self.recall_control == "shadow" else {}
            with AgentMemory.open(
                root,
                tenant=_TENANT,
                actor_id=_ACTOR,
                scope=_scope(user_id),
                purpose=_PURPOSE,
                **open_kwargs,
            ) as memory:
                outcome = memory.recall(str(query), budget=budget)
            if sidecar is not None:
                self._append_sidecar(sidecar, str(query), _scope(user_id), budget, outcome)

            admitted = [str(item) for item in outcome.get("admitted") or []]
            returned = [str(item) for item in outcome.get("returned") or []]
            documents: list[Document] = []
            unmapped: list[str] = []
            for fact_uuid in returned:
                record = self._by_fact.get(fact_uuid)
                if record is None:
                    unmapped.append(fact_uuid)
                    continue
                documents.append(
                    Document(
                        id=record["id"],
                        content=record["content"],
                        user_id=record["user_id"],
                        timestamp=record["timestamp"],
                        context=record["context"],
                        source_ids=list(record["source_ids"]),
                        tags=list(record["tags"]),
                    )
                )

            raw = {
                "provider": self.name,
                "bridge_version": BRIDGE_VERSION,
                "agent_memory_revision": revision,
                "amb_revision": AMB_REVISION,
                "candidate_count": len(outcome.get("candidates") or []),
                "admitted_count": len(admitted),
                "returned_count": len(documents),
                "return_policy": dict(outcome.get("return_policy") or {}),
                "unmapped_admitted": unmapped,
                "query_timestamp_received": query_timestamp,
                "query_timestamp_used_as_memory_authority": False,
                "authority_effect": "none",
            }
            return documents, raw

    class AgentMemoryShadowAMBProvider(AgentMemoryAMBProvider):
        name = AMB_SHADOW_PROVIDER_KEY
        description = (
            "Agent Memory public facade with shadow recall control (contract 1.5.0): retrieval "
            "identical to agent-memory; controller telemetry to a sidecar, never authority."
        )
        variant = "public-facade-shadow-recall-control"
        concurrency = 1
        recall_control = "shadow"

    REGISTRY[AMB_PROVIDER_KEY] = AgentMemoryAMBProvider
    REGISTRY[AMB_SHADOW_PROVIDER_KEY] = AgentMemoryShadowAMBProvider
    # The control class stays the single return value (run_amb_external.py and the tests use it).
    return AgentMemoryAMBProvider


__all__ = [
    "AMB_REPOSITORY",
    "AMB_REVISION",
    "AMB_PROVIDER_KEY",
    "AMB_SHADOW_PROVIDER_KEY",
    "BRIDGE_VERSION",
    "SIDECAR_ENV",
    "verify_amb_checkout",
    "install_amb_agent_memory_provider",
]
