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
        # Fail closed when the invoking process carries API credentials, and
        # pass only the explicitly allowed OS/transport environment to Claude.
        # This prevents ambient Bedrock/Vertex/Foundry/gateway routing and
        # arbitrary user/project Claude settings from altering billing or model.
        if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
            raise RuntimeError("direct Anthropic API credentials are forbidden for #732 R6")
        token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
        if not token:
            raise RuntimeError(
                "CLAUDE_CODE_OAUTH_TOKEN is required; generate it with claude setup-token "
                "from the owner's Claude subscription"
            )
        allow = {
            "PATH", "HOME", "USERPROFILE", "SYSTEMROOT", "WINDIR",
            "TMP", "TEMP", "TMPDIR", "LANG", "LC_ALL",
            "SSL_CERT_FILE", "SSL_CERT_DIR", "HTTPS_PROXY", "HTTP_PROXY",
            "NO_PROXY", "NODE_EXTRA_CA_CERTS",
        }
        env = {key: val for key, val in os.environ.items() if key in allow}
        env["CLAUDE_CODE_OAUTH_TOKEN"] = token
        env["CLAUDE_CONFIG_DIR"] = str(config_dir)
        env["CLAUDE_CODE_SKIP_PROMPT_HISTORY"] = "1"
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
            raise RuntimeError("Claude Code subscription OAuth status failed")
        try:
            parsed = json.loads(auth.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Claude Code auth status was not JSON") from exc
        if parsed.get("authMethod") not in ("oauth_token", "claude.ai"):
            raise RuntimeError(f"unexpected Claude Code auth method: {parsed.get('authMethod')!r}")
        if parsed.get("apiProvider") not in (None, "firstParty"):
            raise RuntimeError("Claude Code did not select first-party subscription auth")
        return {"version": version, "auth_method": str(parsed.get("authMethod"))}

    def extract(self, new_text: str, candidates: Sequence[Mapping[str, str]]) -> px.TypedExtraction:
        # The policy must approve the complete outbound request, not only the
        # new text. Candidate memories can contain protected information too.
        if len(candidates) > px.MAX_CANDIDATES:
            raise ValueError("candidate count exceeds frozen extractor budget")
        payload = json.dumps(
            {"new_text": new_text, "candidates": [dict(item) for item in candidates]},
            ensure_ascii=False,
            sort_keys=True,
        )
        if self.egress_policy(payload) is not True:
            raise PermissionError("Claude Code extraction egress refused by caller policy")
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
                # Do not echo the CLI's stderr/stdout into CI or issue logs.
                raise RuntimeError(f"Claude Code extraction failed (exit {proc.returncode})")

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
