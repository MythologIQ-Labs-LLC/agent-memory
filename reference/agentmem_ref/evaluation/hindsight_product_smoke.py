"""H3 qualification harness for pinned Hindsight chunk-retrieval composition.

This module is evaluation-only. It never runs a benchmark or updates a
scorecard. The real-product entrypoint is intentionally separate from its
offline fake-client tests. H3 is eligible only after the #750 plan gate and
H1/H2 qualification; preparing this harness is not an H3 acceptance.

A live service must be independently provisioned at the frozen v0.10.2
source with HINDSIGHT_API_LLM_PROVIDER=none, pinned ONNX/tokenizer files,
and no paid LLM credentials. The observed product config and output IDs
are checked; the server's process environment is NOT attested by the
HTTP client, so no run may claim paid-provider isolation on HTTP evidence
alone.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol

from .hindsight_bridge import (
    CorpusDocument,
    EXPECTED_BANK_CONFIG,
    HINDSIGHT_RELEASE,
    HINDSIGHT_SOURCE_REVISION,
    HindsightRetrievalBridge,
    HindsightBridgeError,
)
from .hindsight_model_snapshot import resolve_snapshot_dir, snapshot_identity


class BankCreator(Protocol):
    def create_bank(self, *, bank_id: str, **kwargs: Any) -> Any: ...


PROBE_A = "The fjord observatory catalogues violet basalt on western cliffs."
PROBE_B = "The south station inventories brass compasses used by the mapping team."
QUERY = "Which station inventories the brass compasses?"
PROBE_VERSION = "hindsight-product-smoke-v1"


class SmokeQualificationError(RuntimeError):
    """A product or deployment property required for H3 is not established."""


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _semantic_probe(client: BankCreator, bank_id: str) -> dict[str, Any]:
    # Exactly the planned chunk retrieval posture. The client must report
    # these back through the resolved GET /banks/{id}/config endpoint.
    client.create_bank(bank_id=bank_id, **EXPECTED_BANK_CONFIG)
    bridge = HindsightRetrievalBridge(client=client, bank_id=bank_id)
    first_config_hash = bridge.qualify_bank()

    source_a = bridge.retain(CorpusDocument("smoke-doc-a", PROBE_A))
    source_b = bridge.retain(CorpusDocument("smoke-doc-b", PROBE_B))
    retrieval = bridge.recall(QUERY, top_k=2, max_tokens=4096, budget="mid")

    # H3 is a connectivity + identity smoke, not an evaluation score. An
    # empty result cannot establish that the memory product's recall works.
    # Do not demand a particular order or infer gold recall accuracy.
    if not retrieval.mapped_corpus_ids:
        raise SmokeQualificationError("real-product recall returned no document identities")
    if source_a == source_b or bridge.ingest_count != 2:
        raise SmokeQualificationError("real-product retain did not preserve two distinct documents")

    # Detect configuration drift across the complete smoke, without claiming
    # anything about user score or executing the benchmark itself.
    after = HindsightRetrievalBridge(client=client, bank_id=bank_id)
    second_config_hash = after.qualify_bank()
    if first_config_hash != second_config_hash:
        raise SmokeQualificationError("Hindsight bank configuration drifted during H3")

    return {
        "bridge_version": bridge.identity()["bridge_version"],
        "bank_config_sha256": first_config_hash,
        "pre_post_config_sha256_equal": True,
        "probe_documents": [
            {"synthetic_id": "smoke-doc-a", "text_sha256": _hash(PROBE_A), "native_id_sha256": _hash(source_a)},
            {"synthetic_id": "smoke-doc-b", "text_sha256": _hash(PROBE_B), "native_id_sha256": _hash(source_b)},
        ],
        "query_sha256": _hash(QUERY),
        "returned_corpus_ids": list(retrieval.mapped_corpus_ids),
        "provider_result_count": len(retrieval.raw_native_results),
        "repeated_document_id_count": len(retrieval.repeated_native_document_ids),
        "unmapped_result_count": 0,
        "ingest_count": bridge.ingest_count,
        "authority_effect": "none",
    }


def run_smoke(
    *,
    client: BankCreator,
    bank_id: str,
    model_dir: Path,
    deployment_attestation: Mapping[str, Any],
) -> dict[str, Any]:
    """Qualify synthetic retain/recall and explicit deployment provenance.

    The attestation comes from the separately controlled process-launch
    environment, not from a client assertion. This harness records it as
    operator-attested data, never as independently verified remote truth.
    """
    required = {
        "product_release": HINDSIGHT_RELEASE,
        "product_source_revision": HINDSIGHT_SOURCE_REVISION,
        "llm_provider": "none",
        "embedding_provider": "onnx",
        "model_revision": "03415a4be176a1620747c692ed433219fabc3def",
        "paid_llm_credentials_present": False,
    }
    for key, expected in required.items():
        actual = deployment_attestation.get(key)
        if type(actual) is not type(expected) or actual != expected:
            raise SmokeQualificationError(f"invalid deployment attestation: {key}")

    model = snapshot_identity(model_dir)
    result = _semantic_probe(client, bank_id)
    return {
        "schema_version": "1.0.0",
        "smoke_id": PROBE_VERSION,
        "evidence_class": "product_connectivity_and_identity_smoke",
        "benchmark_score": None,
        "benchmark_lane": None,
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "product": {
            "release": HINDSIGHT_RELEASE,
            "source_revision": HINDSIGHT_SOURCE_REVISION,
            "configuration": dict(EXPECTED_BANK_CONFIG),
            "deployment_attestation": dict(deployment_attestation),
            "attestation_verification": "operator-provided; must be corroborated by pinned local process evidence before H3 acceptance",
        },
        "model_snapshot": model,
        "probe": result,
        "status": "connectivity_pass_attestation_pending",
        "next_gate": "H3 independent deployment verification, then freeze H4 lane before scoring",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthetic, non-scoring Hindsight v0.10.2 H3 smoke")
    parser.add_argument("--base-url", required=True, help="Local Hindsight HTTP endpoint")
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--deployment-attestation", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--bank-id", default=None, help="Fresh unique synthetic bank; omit for auto-generation")
    args = parser.parse_args()

    # Keep the live path local; this is not permission to connect to a hosted,
    # possibly paid Hindsight or a mixed-tenant production system.
    from urllib.parse import urlparse
    parsed = urlparse(args.base_url)
    if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise SystemExit("H3 smoke only permits a local, non-billed HTTP Hindsight service")

    attestation = json.loads(args.deployment_attestation.read_text(encoding="utf-8"))
    if not isinstance(attestation, dict):
        raise SystemExit("deployment attestation must be an object")
    bank_id = args.bank_id or f"agent-memory-h3-{uuid.uuid4().hex}"
    from hindsight_client import Hindsight  # import only for an explicitly requested real-product run
    client = Hindsight(base_url=args.base_url, max_attempts=1)
    try:
        record = run_smoke(
            client=client,
            bank_id=bank_id,
            model_dir=resolve_snapshot_dir(args.model_dir),
            deployment_attestation=attestation,
        )
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            close()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, sort_keys=True, indent=2)+"\n", encoding="utf-8")
    print("H3 synthetic product smoke recorded. Deployment provenance remains operator-attested.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
