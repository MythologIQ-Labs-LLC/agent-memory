"""Self-hosted, no-LLM H3 product smoke against a pinned Hindsight checkout.

The real product is started in this process and configured explicitly with
llm_provider='none' and verified local ONNX files. It never contacts a paid
model endpoint and never scores a benchmark. Product imports are deferred
until environment and immutable-source preflight are complete.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any

from .hindsight_bridge import HINDSIGHT_RELEASE, HINDSIGHT_SOURCE_REVISION
from .hindsight_model_snapshot import resolve_snapshot_dir, snapshot_identity
from .hindsight_product_smoke import run_smoke


class SelfHostedSmokeError(RuntimeError):
    """Self-hosted product or non-billed execution identity not established."""


FORBIDDEN_CREDENTIAL_ENV = (
    "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "OPENAI_API_KEY",
    "GOOGLE_API_KEY", "GEMINI_API_KEY", "HINDSIGHT_API_LLM_API_KEY",
    "CLAUDE_CODE_OAUTH_TOKEN", "AWS_ACCESS_KEY_ID",
)


def verify_pinned_checkout(source: Path) -> Path:
    """Refuse an unpinned or dirty Hindsight source tree."""

    root = source.resolve(strict=True)
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    )
    if result.stdout.strip() != HINDSIGHT_SOURCE_REVISION:
        raise SelfHostedSmokeError("Hindsight checkout is not pinned to the H3 source commit")
    dirty = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"],
        capture_output=True, text=True, check=True,
    )
    if dirty.stdout.strip():
        raise SelfHostedSmokeError("Hindsight source checkout is modified")
    return root


def isolated_environment(model_root: Path) -> dict[str, str]:
    """Explicitly set every retrieval/model route needed by this smoke."""

    for key in FORBIDDEN_CREDENTIAL_ENV:
        if os.environ.get(key):
            raise SelfHostedSmokeError(
                "ambient paid inference credential detected; isolate before H3"
            )
    return {
        "HINDSIGHT_API_LLM_PROVIDER": "none",
        "HINDSIGHT_API_LLM_API_KEY": "",
        "HINDSIGHT_API_EMBEDDINGS_PROVIDER": "onnx",
        "HINDSIGHT_API_EMBEDDINGS_ONNX_MODEL_ID": "intfloat/multilingual-e5-small",
        "HINDSIGHT_API_EMBEDDINGS_ONNX_MODEL_PATH": str(model_root / "onnx/model.onnx"),
        "HINDSIGHT_API_EMBEDDINGS_ONNX_TOKENIZER_NAME_OR_PATH": str(model_root),
        "HINDSIGHT_API_ENABLE_OBSERVATIONS": "false",
        "HINDSIGHT_API_ENABLE_TEXT_SEARCH": "true",
        "HINDSIGHT_API_ENABLE_TEMPORAL_RETRIEVAL": "false",
        "HINDSIGHT_API_ENABLE_GRAPH_RETRIEVAL": "false",
        "HINDSIGHT_API_ENABLE_RERANKING": "false",
    }


def run_selfhosted_smoke(
    *,
    model_dir: Path,
    source_dir: Path,
    server_factory: Any = None,
    client_factory: Any = None,
) -> dict[str, Any]:
    source = verify_pinned_checkout(source_dir)
    model_root = model_dir.resolve(strict=True)
    model_identity = snapshot_identity(model_root)
    updates = isolated_environment(model_root)

    # This function runs in a dedicated process. Save and restore the
    # temporary environment so even fake-client tests cannot leak settings.
    original = {key: os.environ.get(key) for key in updates}
    try:
        os.environ.update(updates)
        if server_factory is None or client_factory is None:
            if importlib.metadata.version("hindsight-all") != HINDSIGHT_RELEASE:
                raise SelfHostedSmokeError("installed Hindsight release differs from pinned 0.10.2")
            import hindsight
            product_location = Path(hindsight.__file__).resolve()
            try:
                product_location.relative_to(source)
            except ValueError as exc:
                raise SelfHostedSmokeError(
                    "installed Hindsight product is not sourced from the pinned checkout"
                ) from exc
            from hindsight import HindsightServer
            from hindsight_client import Hindsight
            server_factory = HindsightServer
            client_factory = Hindsight

        # An explicit constructor argument takes priority over inherited
        # defaults, and no API credentials are passed to the product.
        with tempfile.TemporaryDirectory(prefix="agent-memory-h3-pg0-") as work:
            old_cwd = Path.cwd()
            os.chdir(work)
            try:
                server = server_factory(
                    db_url="pg0", llm_provider="none", llm_api_key="",
                    host="127.0.0.1", mcp_enabled=False, log_level="warning",
                )
                if server.llm_provider != "none" or server.llm_api_key != "":
                    raise SelfHostedSmokeError("server has a non-frozen LLM provider or credential")
                try:
                    server.start()
                    client = client_factory(base_url=server.url, max_attempts=1)
                    try:
                        deployment = {
                            "product_release": HINDSIGHT_RELEASE,
                            "product_source_revision": HINDSIGHT_SOURCE_REVISION,
                            "llm_provider": "none",
                            "embedding_provider": "onnx",
                            "model_revision": model_identity["revision"],
                            "paid_llm_credentials_present": False,
                        }
                        record = run_smoke(
                            client=client, bank_id=f"agent-memory-h3-{uuid.uuid4().hex}",
                            model_dir=model_root, deployment_attestation=deployment,
                        )
                    finally:
                        close = getattr(client, "close", None)
                        if callable(close):
                            close()
                finally:
                    server.stop()
            finally:
                os.chdir(old_cwd)

        record["status"] = "selfhosted_product_smoke_pass"
        record["product"]["attestation_verification"] = (
            "pinned clean source checkout; installed editable product path; "
            "same-process HindsightServer constructed with llm_provider=none "
            "and no API key; pre/post effective bank config confirmed"
        )
        record["product"]["server_isolation"] = "temporary embedded local PostgreSQL; loopback only"
        record["product"]["network_model_calls"] = 0
        record["model_snapshot"] = model_identity
        return record
    finally:
        for key, old in original.items():
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old


def main() -> int:
    parser = argparse.ArgumentParser(description="Self-hosted non-scoring Hindsight H3 smoke")
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    record = run_selfhosted_smoke(
        model_dir=resolve_snapshot_dir(args.model_dir),
        source_dir=args.source_dir,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("Self-hosted Hindsight H3 synthetic smoke: PASS (not a benchmark score)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
