"""Evaluation-only Claude Code implementation of the public PropositionExtractor seam.

This module lives under agentmem_ref.evaluation and is not part of Runtime
Baseline v6 protected bytes. It exists only to qualify #732 R6 with the owner's
Claude subscription instead of a paid Platform API key.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Mapping, Sequence

from agentmem_ref.runtime import proposition_extraction as px

CLI_VERSION = "2.1.294"
MODEL = "claude-sonnet-5-5"
EFFORT = "high"
MAX_TURNS = 3
EXTRACTOR_ID = "claude-code-cli"
EXTRACTOR_VERSION = f"1.0.0/claude-code-{CLI_VERSION}/{MODEL}/{EFFORT}/{px.PROMPT_SHA256[:12]}"


class ClaudeCodeCLIExtractor:
    """Frozen Claude Code -p provider for synthetic evaluation text."""

    extractor_id = EXTRACTOR_ID
    extractor_version = EXTRACTOR_VERSION

    def __init__(
        self,
        *,
        egress_policy: Callable[[str], bool],
        cli_path: str = "claude",
        timeout_seconds: float = px.EXTRACTION_TIMEOUT_SECONDS,
    ) -> None:
        if not callable(egress_policy):
            raise TypeError("egress_policy must be callable")
        self.egress_policy = egress_policy
        self.cli_path = cli_path
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _clean_env(config_dir: Path) -> dict[str, str]:
        env = os.environ.copy()
        if env.get("ANTHROPIC_API_KEY") or env.get("ANTHROPIC_AUTH_TOKEN"):
            raise RuntimeError("direct Anthropic API credentials are forbidden for #732 R6")
        if not env.get("CLAUDE_CODE_OAUTH_TOKEN"):
            raise RuntimeError(
                "CLAUDE_CODE_OAUTH_TOKEN is required; generate it with claude setup-token "
                "from the owner's Claude subscription"
            )
        env["CLAUDE_CONFIG_DIR"] = str(config_dir)
        env["CLAUDE_CODE_SKIP_PROMPT_HISTORY"] = "1"
        env["MCP_CONNECTION_NONBLOCKING"] = "true"
        return env

    def _verify_cli(self, env: Mapping[str, str], cwd: Path) -> dict[str, str]:
        version = subprocess.run(
            [self.cli_path, "--version"],
            cwd=cwd,
            env=dict(env),
            text=True,
            capture_output=True,
            check=True,
            timeout=10,
        ).stdout.strip()
        if CLI_VERSION not in version:
            raise RuntimeError(f"Claude Code version drift: {version!r}; expected {CLI_VERSION}")

        auth = subprocess.run(
            [self.cli_path, "auth", "status"],
            cwd=cwd,
            env=dict(env),
            text=True,
            capture_output=True,
            timeout=10,
        )
        if auth.returncode != 0:
            raise RuntimeError(f"Claude Code OAuth status failed: {auth.stderr.strip()}")
        try:
            parsed = json.loads(auth.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Claude Code auth status was not JSON") from exc
        if parsed.get("authMethod") not in ("oauth_token", "claudeai", "subscription"):
            raise RuntimeError(f"unexpected Claude Code auth method: {parsed.get('authMethod')!r}")
        return {"version": version, "auth_method": str(parsed.get("authMethod"))}

    def extract(self, new_text: str, candidates: Sequence[Mapping[str, str]]) -> px.TypedExtraction:
        payload = json.dumps(
            {"new_text": new_text, "candidates": [dict(item) for item in candidates]},
            ensure_ascii=False,
            sort_keys=True,
        )
        schema = json.dumps(
            px.WIRE_OUTPUT_SCHEMA,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

        with tempfile.TemporaryDirectory(prefix="agent-memory-claude-code-") as tmp:
            root = Path(tmp)
            config = root / "config"
            config.mkdir()
            prompt_file = root / "system-prompt.txt"
            prompt_file.write_text(px.FROZEN_PROMPT, encoding="utf-8")
            env = self._clean_env(config)
            self._verify_cli(env, root)

            command = [
                self.cli_path,
                "-p",
                "--model", MODEL,
                "--effort", EFFORT,
                "--system-prompt-file", str(prompt_file),
                "--output-format", "json",
                "--json-schema", schema,
                "--tools", "",
                "--strict-mcp-config",
                "--mcp-config", '{"mcpServers":{}}',
                "--permission-mode", "dontAsk",
                "--no-session-persistence",
                "--max-turns", str(MAX_TURNS),
                payload,
            ]
            proc = subprocess.run(
                command,
                cwd=root,
                env=env,
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
            )
            if proc.returncode != 0:
                detail = (proc.stderr or proc.stdout).strip()
                raise RuntimeError(
                    f"Claude Code extraction failed ({proc.returncode}): {detail[:500]}"
                )

            try:
                envelope = json.loads(proc.stdout)
            except json.JSONDecodeError as exc:
                raise px.ExtractionOutputError(
                    "claude_code_envelope_json", raw_output=proc.stdout
                ) from exc
            output = envelope.get("structured_output")
            if not isinstance(output, dict) or set(output) != {
                "proposition",
                "updates_fact_uuid",
            }:
                raise px.ExtractionOutputError(
                    "claude_code_structured_output_shape",
                    raw_output=json.dumps(output, sort_keys=True)
                    if output is not None
                    else "",
                    request_id=envelope.get("session_id"),
                )
            raw = json.dumps(output, ensure_ascii=False, sort_keys=True)
            request_id = envelope.get("session_id")
            if request_id:
                request_id = f"claude-code-session:{request_id}"
            return px.TypedExtraction(
                proposition=output["proposition"],
                updates_fact_uuid=output["updates_fact_uuid"],
                extractor_id=self.extractor_id,
                extractor_version=self.extractor_version,
                raw_output=raw,
                request_id=request_id,
                prompt_sha256=px.PROMPT_SHA256,
            )


__all__ = [
    "CLI_VERSION",
    "ClaudeCodeCLIExtractor",
    "EFFORT",
    "EXTRACTOR_ID",
    "EXTRACTOR_VERSION",
    "MAX_TURNS",
    "MODEL",
]
