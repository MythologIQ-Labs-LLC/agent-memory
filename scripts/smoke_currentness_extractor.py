#!/usr/bin/env python3
"""One synthetic subscription-OAuth provider smoke for #732 R6.

Connectivity/protocol evidence only. It never authors or scores the R6 holdout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
FREEZE_DEFAULT = (
    REPO_ROOT
    / "reports/benchmarks/currentness-generalization/provider-freeze/provider-v2.json"
)

SYNTHETIC_NEW_TEXT = (
    "The Atlas demo endpoint changed from https://old.example.test "
    "to https://new.example.test."
)
SYNTHETIC_CANDIDATES = [
    {
        "fact_uuid": "smoke-fact-old",
        "text": "The Atlas demo endpoint is https://old.example.test.",
    }
]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def _git_revision() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
    ).strip()


def _baseline_line() -> str:
    return subprocess.check_output(
        [
            "python",
            "scripts/check_runtime_baseline_equivalence.py",
            "--candidate",
            "HEAD",
        ],
        cwd=REPO_ROOT,
        text=True,
    ).strip()


def load_and_verify_freeze(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    freeze = json.loads(raw)

    from agentmem_ref.evaluation.claude_code_proposition_extractor import (
        CLI_VERSION,
        EFFORT,
        EXTRACTOR_VERSION,
        MODEL,
    )
    from agentmem_ref.runtime import proposition_extraction as px

    if freeze["runtime"]["baseline"] != "agent-memory-runtime-baseline-v6":
        raise SystemExit("provider freeze is not bound to Runtime Baseline v6")
    if freeze["provider"]["id"] != "claude-code-cli":
        raise SystemExit("provider freeze is not the Claude Code provider")
    if freeze["provider"]["cli_version"] != CLI_VERSION:
        raise SystemExit("Claude Code CLI version drift")
    if freeze["provider"]["model"] != MODEL:
        raise SystemExit("Claude Code model drift")
    if freeze["configuration"]["effort"] != EFFORT:
        raise SystemExit("Claude Code effort drift")
    if freeze["extractor"]["extractor_version"] != EXTRACTOR_VERSION:
        raise SystemExit("evaluation extractor version drift")
    if freeze["extractor"]["prompt_sha256"] != px.PROMPT_SHA256:
        raise SystemExit("frozen prompt sha256 no longer matches runtime source")
    if px.MAX_CANDIDATES != freeze["configuration"]["max_candidates"]:
        raise SystemExit("candidate budget drift")
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        raise SystemExit("direct Anthropic API credentials are forbidden for #732 R6")
    return freeze, raw


def build_record(
    freeze: dict[str, Any],
    freeze_raw: bytes,
    answer: Any | None,
    *,
    dry_run: bool,
) -> dict[str, Any]:
    from agentmem_ref.runtime import proposition_extraction as px
    from agentmem_ref.runtime import typed_proposition as typed

    if dry_run:
        response = {"status": "not_executed", "reason": "dry_run"}
    else:
        if not answer.request_id:
            raise SystemExit("Claude Code response did not include session provenance")
        if answer.prompt_sha256 != px.PROMPT_SHA256:
            raise SystemExit("provider answer prompt identity mismatch")
        if answer.extractor_version != freeze["extractor"]["extractor_version"]:
            raise SystemExit("provider answer extractor identity mismatch")
        valid_ids = {item["fact_uuid"] for item in SYNTHETIC_CANDIDATES}
        if (
            answer.updates_fact_uuid is not None
            and answer.updates_fact_uuid not in valid_ids
        ):
            raise SystemExit(
                "provider returned an updates_fact_uuid outside the synthetic candidate set"
            )
        if answer.proposition is not None:
            typed.validate(answer.proposition)
        response = {
            "status": "pass",
            "session_provenance": answer.request_id,
            "raw_output_sha256": sha256_text(answer.raw_output),
            "proposition_present": answer.proposition is not None,
            "updates_candidate": answer.updates_fact_uuid in valid_ids,
        }

    return {
        "schema_version": "1.0.0",
        "smoke_id": "currentness-generalization-732-r6-provider-smoke-v2",
        "evidence_class": "provider_connectivity_smoke",
        "authority_effect": "none",
        "generalization_score": None,
        "executed_at": None if dry_run else datetime.now(timezone.utc).isoformat(),
        "system_revision": _git_revision(),
        # Offline tests run in shallow CI checkouts where the historical frozen
        # runtime commit may not be available. Dry-run never claims equivalence.
        # The live provider smoke always runs the strict comparison and fails
        # closed if the frozen commit is absent or protected bytes changed.
        "runtime_baseline_line": (
            "NOT_VERIFIED_DRY_RUN" if dry_run else _baseline_line()
        ),
        "provider_freeze": {
            "path": str(FREEZE_DEFAULT.relative_to(REPO_ROOT)),
            "sha256": sha256_bytes(freeze_raw),
            "freeze_id": freeze["freeze_id"],
        },
        "extractor": {
            "provider": freeze["provider"]["id"],
            "cli_version": freeze["provider"]["cli_version"],
            "model": freeze["provider"]["model"],
            "authentication": freeze["provider"]["authentication"],
            "extractor_version": freeze["extractor"]["extractor_version"],
            "prompt_sha256": freeze["extractor"]["prompt_sha256"],
            "effort": freeze["configuration"]["effort"],
        },
        "billing_safety": {
            "platform_api_key_used": False,
            "subscription_oauth_only": True,
        },
        "synthetic_fixture": {
            "id": "atlas-demo-endpoint-change-v1",
            "new_text_sha256": sha256_text(SYNTHETIC_NEW_TEXT),
            "candidate_count": len(SYNTHETIC_CANDIDATES),
            "candidate_text_sha256": [
                sha256_text(item["text"]) for item in SYNTHETIC_CANDIDATES
            ],
            "contains_user_data": False,
        },
        "response": response,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", type=Path, default=FREEZE_DEFAULT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    freeze, raw = load_and_verify_freeze(args.freeze)
    answer = None
    if not args.dry_run:
        if not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
            raise SystemExit(
                "CLAUDE_CODE_OAUTH_TOKEN is required for the frozen smoke; "
                "generate it with claude setup-token from the owner's subscription"
            )
        from agentmem_ref.evaluation.claude_code_proposition_extractor import (
            ClaudeCodeCLIExtractor,
        )

        extractor = ClaudeCodeCLIExtractor(egress_policy=lambda _text: True)
        answer = extractor.extract(SYNTHETIC_NEW_TEXT, SYNTHETIC_CANDIDATES)

    record = build_record(freeze, raw, answer, dry_run=args.dry_run)
    rendered = json.dumps(record, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
