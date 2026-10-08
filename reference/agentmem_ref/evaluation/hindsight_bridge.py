"""Benchmark-neutral Hindsight v0.10.2 retrieval adapter (#640 H2).

This adapter calls only documented retain/recall client methods and never
implements memory semantics on Hindsight's behalf. It maps returned *native*
document_id values to exact previously ingested corpus IDs. Unknown identities,
missing document IDs and malformed responses are adapter failures, not misses.

No product is imported or instantiated at module import; no model/API call
occurs in offline tests. The real-product smoke and score remain separate gates.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

HINDSIGHT_SOURCE_REVISION = "5fc4ce20917b916240cef27c212c387a177f115b"
HINDSIGHT_RELEASE = "0.10.2"
BRIDGE_VERSION = "0.2.0"
EXPECTED_BANK_CONFIG = {
    "retain_extraction_mode": "chunks",
    "enable_observations": False,
    "enable_text_search": True,
    "enable_temporal_retrieval": False,
    "enable_graph_retrieval": False,
    "enable_reranking": False,
}
# A namespace avoids treating the benchmark/gold ID as a native provider ID.
DOC_PREFIX = "agent-memory-comparator-"


class HindsightBridgeError(RuntimeError):
    """The adapter cannot faithfully express or map the product's output."""


class IdentityMappingError(HindsightBridgeError):
    """A product result cannot be traced to a supplied corpus input."""

    def __init__(self, message: str, raw_results: tuple[dict[str, Any], ...]) -> None:
        super().__init__(message)
        self.raw_results = raw_results


class HindsightClientContract(Protocol):
    def get_bank_config(self, bank_id: str) -> Any: ...
    def retain(self, *, bank_id: str, content: str, document_id: str, retain_async: bool) -> Any: ...
    def recall(self, *, bank_id: str, query: str, max_tokens: int, budget: str) -> Any: ...


@dataclass(frozen=True)
class CorpusDocument:
    corpus_id: str
    text: str


@dataclass(frozen=True)
class RecallEnvelope:
    mapped_corpus_ids: tuple[str, ...]
    raw_native_results: tuple[dict[str, Any], ...]
    repeated_native_document_ids: tuple[str, ...]
    requested_top_k: int
    provider_max_tokens: int
    provider_budget: str
    authority_effect: str = "none"


def _mapping(value: Any, *, label: str) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "model_dump"):
        obj = value.model_dump(mode="json", exclude_none=True)
        if isinstance(obj, dict):
            return obj
    raise HindsightBridgeError(f"{label} is not a mapping or supported model")


def _native_document_id(corpus_id: str) -> str:
    # The corpus reference never appears in the retained text or as a gold label.
    return DOC_PREFIX + hashlib.sha256(corpus_id.encode("utf-8")).hexdigest()


class HindsightRetrievalBridge:
    """One explicit-memory Hindsight bank with a strict corpus-identity map."""

    def __init__(self, *, client: HindsightClientContract, bank_id: str) -> None:
        if not isinstance(bank_id, str) or not bank_id:
            raise ValueError("bank_id must be non-empty")
        self.client = client
        self.bank_id = bank_id
        self._corpus_to_native: dict[str, str] = {}
        self._native_to_corpus: dict[str, str] = {}
        self._qualified_bank_config_sha256: str | None = None

    def qualify_bank(self) -> str:
        """Verify the product's effective bank settings before any ingest.

        Refuse a different bank, omitted switches, or config drift. This is an
        offline-testable product API preflight, not a scored benchmark result.
        """
        if self._corpus_to_native:
            raise HindsightBridgeError("cannot qualify bank after ingest")
        view = _mapping(self.client.get_bank_config(self.bank_id), label="bank config")
        if view.get("bank_id") != self.bank_id:
            raise HindsightBridgeError("bank config belongs to a different bank")
        config = view.get("config")
        if not isinstance(config, dict):
            raise HindsightBridgeError("effective Hindsight bank config unavailable")
        for key, expected in EXPECTED_BANK_CONFIG.items():
            observed = config.get(key)
            if type(observed) is not type(expected) or observed != expected:
                raise HindsightBridgeError(f"unqualified Hindsight bank config: {key}")
        evidence = {key: config[key] for key in sorted(EXPECTED_BANK_CONFIG)}
        digest = hashlib.sha256(
            json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self._qualified_bank_config_sha256 = digest
        return digest

    def _require_qualified_bank(self) -> None:
        if self._qualified_bank_config_sha256 is None:
            raise HindsightBridgeError(
                "Hindsight bank not qualified: call qualify_bank before retain/recall"
            )

    @property
    def ingest_count(self) -> int:
        return len(self._corpus_to_native)

    def retain(self, document: CorpusDocument) -> str:
        """Insert unchanged content synchronously; refuse ambiguous repeat IDs."""

        self._require_qualified_bank()
        if not isinstance(document.corpus_id, str) or not document.corpus_id:
            raise ValueError("corpus_id must be non-empty")
        if not isinstance(document.text, str) or not document.text:
            raise ValueError("document text must be non-empty")
        if document.corpus_id in self._corpus_to_native:
            raise HindsightBridgeError("duplicate corpus_id; ambiguous retained identity")
        native_id = _native_document_id(document.corpus_id)
        if native_id in self._native_to_corpus:
            raise HindsightBridgeError("native document identity collision")

        answer = self.client.retain(
            bank_id=self.bank_id,
            content=document.text,
            document_id=native_id,
            retain_async=False,
        )
        result = _mapping(answer, label="retain response")
        if (result.get("success") is not True
                or result.get("bank_id") != self.bank_id
                or type(result.get("items_count")) is not int
                or result["items_count"] != 1
                or result.get("var_async", result.get("async")) is not False):
            raise HindsightBridgeError("retain did not confirm one synchronous item")

        self._corpus_to_native[document.corpus_id] = native_id
        self._native_to_corpus[native_id] = document.corpus_id
        return native_id

    def recall(self, query: str, *, top_k: int, max_tokens: int, budget: str = "mid") -> RecallEnvelope:
        self._require_qualified_bank()
        if not isinstance(query, str) or not query:
            raise ValueError("query must be non-empty")
        if type(top_k) is not int or top_k < 1:
            raise ValueError("top_k must be a positive integer")
        if type(max_tokens) is not int or max_tokens < 1:
            raise ValueError("max_tokens must be a positive integer")
        if budget not in ("low", "mid", "high"):
            raise ValueError("unsupported Hindsight recall budget")

        answer = self.client.recall(
            bank_id=self.bank_id,
            query=query,
            max_tokens=max_tokens,
            budget=budget,
        )
        view = _mapping(answer, label="recall response")
        if not isinstance(view.get("results"), list):
            raise HindsightBridgeError("recall response has no native result list")
        raw: list[dict[str, Any]] = []
        for index, item in enumerate(view["results"]):
            result = _mapping(item, label=f"recall result {index}")
            raw.append(result)
        raw_tuple = tuple(raw)

        mapped: list[str] = []
        repeated: list[str] = []
        seen: set[str] = set()
        for index, result in enumerate(raw):
            native_id = result.get("document_id")
            if not isinstance(native_id, str) or not native_id:
                raise IdentityMappingError(f"recall result {index} has no native document_id", raw_tuple)
            if native_id not in self._native_to_corpus:
                raise IdentityMappingError(f"recall result {index} is outside the inserted corpus", raw_tuple)
            if native_id in seen:
                repeated.append(native_id)
                continue
            seen.add(native_id)
            mapped.append(self._native_to_corpus[native_id])

        # Preserve provider order; top_k is a projection only, not a way to
        # manufacture missing candidates. The H4 lane must separately qualify
        # Hindsight's provider token budget against the shared retrieval budget.
        return RecallEnvelope(
            mapped_corpus_ids=tuple(mapped[:top_k]),
            raw_native_results=raw_tuple,
            repeated_native_document_ids=tuple(repeated),
            requested_top_k=top_k,
            provider_max_tokens=max_tokens,
            provider_budget=budget,
        )

    def identity(self) -> dict[str, Any]:
        return {
            "system": "hindsight-oss-chunk-retrieval",
            "product_revision": HINDSIGHT_SOURCE_REVISION,
            "release": HINDSIGHT_RELEASE,
            "bridge_version": BRIDGE_VERSION,
            "bank_id": self.bank_id,
            "retained_count": self.ingest_count,
            "inference": "none",
            "authority_effect": "none",
            "product_configuration_verified": self._qualified_bank_config_sha256 is not None,
            "verified_bank_config_sha256": self._qualified_bank_config_sha256,
            "status": "config preflight only; H3 real-product smoke and H4 lane freeze required",
        }
