"""Restricted internal-alpha pilot: a real Claude Code agent over the five-tool stdio MCP server.

Each session of ``scenario.json`` is one non-interactive Claude Code run (``claude -p``):

* built-in tools disabled (``--tools ""``), only this repository's stdio server configured
  (``--strict-mcp-config``), only the five memory tools allowed, the evidence contract appended to
  its system prompt, no settings files, an empty working directory;
* a fresh MCP server process per session, so every session after the first is a restart;
* the server's tenant, actor, scope and store root are host environment values; lifecycle
  authority (a forget grant or a correction record) is added only to the sessions the scenario
  marks, and the harness strips any such variable from its own environment first.

The host seeds the fixtures through the same MCP tools before the agent sessions, and reads every
watched key through ``memory_get`` before and after each session (store bytes change on every
open, so logical state is the mutation signal). It records the real tool calls, the structured
results, the agent's final text, the host evidence check (``evidence_check.py``) and what the
restricted host would display. Checks and rubric never reach the agent.

usage: agent_pilot.py --run-dir ABS_DIR --out RECEIPTS_DIR [--sessions S01,S02,...] [--scenario FILE]
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

from mcp import Client, StdioServerParameters

HERE = Path(__file__).resolve().parent
MCP_DIR = HERE.parent
SERVER = MCP_DIR / "server.py"
SCENARIO = HERE / "scenario.json"
CONTRACT = HERE / "evidence_contract.md"
ACTOR = "agent:pilot"
TOOLS = ("memory_remember", "memory_get", "memory_find", "memory_forget", "memory_correct")
ALLOWED = " ".join(f"mcp__agent-memory__{name}" for name in TOOLS)
HOST_ONLY = ("AGENT_MEMORY_MCP_", "AGENT_MEMORY_REPRESENTATION_DIR")

sys.path.insert(0, str(MCP_DIR))
sys.path.insert(0, str(HERE))
import evidence_check  # noqa: E402
from bridge import HostConfig  # noqa: E402


def private_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)
    return path


def server_env(root: Path, scope: str, tenant: str, extra: dict | None = None) -> dict:
    env = {"AGENT_MEMORY_MCP_ROOT": str(root), "AGENT_MEMORY_MCP_TENANT": tenant,
           "AGENT_MEMORY_MCP_ACTOR": ACTOR, "AGENT_MEMORY_MCP_SCOPE": scope, "PATH": "/usr/bin:/bin"}
    env.update(extra or {})
    return env


def assert_safe_root(env: dict) -> None:
    """The bridge's own preflight: absolute, no parent traversal, no symlinked or junction ancestor."""
    saved = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    try:
        HostConfig.from_environment()
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


async def host_calls(env: dict, calls: list[tuple[str, dict]]) -> list[dict]:
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)], env=env)
    out = []
    async with Client(params) as client:
        for name, args in calls:
            result = await client.call_tool(name, args)
            out.append({"is_error": result.is_error, "body": result.structured_content or {}})
    return out


async def seed(scenario: dict, root: Path) -> None:
    main = server_env(root, scenario["scope"], scenario["tenant"])
    for (r, args) in zip(await host_calls(main, [("memory_remember", f) for f in scenario["fixtures"]]), scenario["fixtures"]):
        if r["is_error"] or r["body"].get("committed") is not True:
            raise RuntimeError(f"fixture write not committed: {args['key']}")
    other = scenario["other_project_fixtures"]
    env = server_env(root, other["scope"], scenario["tenant"])
    for r in await host_calls(env, [("memory_remember", f) for f in other["records"]]):
        if r["is_error"] or r["body"].get("committed") is not True:
            raise RuntimeError("other-project fixture write not committed")


async def snapshot(scenario: dict, root: Path) -> dict:
    env = server_env(root, scenario["scope"], scenario["tenant"])
    results = await host_calls(env, [("memory_get", {"key": k}) for k in scenario["watched_keys"]])
    return {key: {"lookup_status": r["body"].get("lookup_status"),
                  "facts": [(e.get("fact_ref"), e.get("content")) for e in r["body"].get("evidence") or []],
                  "key_state_version": r["body"].get("key_state_version")}
            for key, r in zip(scenario["watched_keys"], results)}


def session_host(scenario: dict, session: dict, run: Path, root: Path) -> tuple[dict, dict]:
    host = session.get("host") or {}
    extra, summary = {}, {"scope": host.get("scope", scenario["scope"]),
                          "tenant": host.get("tenant", scenario["tenant"]), "lifecycle_authority": None}
    if "forget_grant" in host:
        extra["AGENT_MEMORY_MCP_PRUNE_APPROVED_KEY"] = host["forget_grant"]["key"]
        extra["AGENT_MEMORY_MCP_PRUNE_EVIDENCE_REF"] = host["forget_grant"]["evidence_ref"]
        summary["lifecycle_authority"] = {"forget_grant_key": host["forget_grant"]["key"]}
    if "correction_record" in host:
        records = private_dir(run / "records")
        record = records / f"{session['id']}-correction.json"
        record.write_text(json.dumps(host["correction_record"]), encoding="utf-8")
        os.chmod(record, 0o600)
        extra["AGENT_MEMORY_MCP_CORRECTION_RECORD"] = str(record)
        summary["lifecycle_authority"] = {"correction_record_key": host["correction_record"]["key"],
                                          "record_sha256": hashlib.sha256(record.read_bytes()).hexdigest()}
    return server_env(root, summary["scope"], summary["tenant"], extra), summary


def run_agent(session: dict, env: dict, run: Path) -> tuple[list[dict], float]:
    config = run / f"{session['id']}-mcp.json"
    config.write_text(json.dumps({"mcpServers": {"agent-memory": {
        "type": "stdio", "command": sys.executable, "args": [str(SERVER)], "env": env}}}), encoding="utf-8")
    os.chmod(config, 0o600)
    cwd = private_dir(run / "agent-cwd")
    parent = {k: v for k, v in os.environ.items() if not k.startswith(HOST_ONLY)}
    command = ["claude", "-p", session["prompt"], "--output-format", "stream-json", "--verbose",
               "--tools", "", "--strict-mcp-config", "--mcp-config", str(config),
               "--allowedTools", ALLOWED, "--append-system-prompt", CONTRACT.read_text(encoding="utf-8"),
               "--no-session-persistence", "--setting-sources", "project", "--session-id", str(uuid.uuid4())]
    started = time.perf_counter()
    done = subprocess.run(command, cwd=cwd, env=parent, stdin=subprocess.DEVNULL,
                          capture_output=True, text=True, timeout=900)
    elapsed = time.perf_counter() - started
    config.unlink()
    events = [json.loads(line) for line in done.stdout.splitlines() if line.strip().startswith("{")]
    if done.returncode != 0 or not any(e.get("type") == "result" for e in events):
        raise RuntimeError(f"agent run failed for {session['id']}: rc={done.returncode} {done.stderr[-500:]}")
    return events, elapsed


def _tool_body(content) -> dict | None:
    text = content if isinstance(content, str) else "".join(
        c.get("text", "") for c in content or [] if isinstance(c, dict) and c.get("type") == "text")
    try:
        body = json.loads(text)
    except (TypeError, ValueError):
        return None
    return body.get("result", body) if isinstance(body, dict) else None


def transcript(events: list[dict]) -> dict:
    init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), {})
    final = next(e for e in events if e.get("type") == "result")
    calls, results, texts = [], {}, []
    for event in events:
        content = (event.get("message") or {}).get("content") or []
        for block in content if isinstance(content, list) else []:
            if event.get("type") == "assistant" and block.get("type") == "tool_use":
                calls.append({"id": block["id"], "tool": block["name"].removeprefix("mcp__agent-memory__"),
                              "input": block.get("input")})
            elif event.get("type") == "assistant" and block.get("type") == "text":
                texts.append(block["text"])
            elif event.get("type") == "user" and block.get("type") == "tool_result":
                results[block["tool_use_id"]] = {"is_error": bool(block.get("is_error")),
                                                 "body": _tool_body(block.get("content")),
                                                 "raw": block.get("content") if _tool_body(block.get("content")) is None else None}
    for call in calls:
        call.update(results.get(call.pop("id"), {"is_error": None, "body": None, "raw": None}))
    return {"model": init.get("model"), "tools_available": init.get("tools"),
            "mcp_servers": init.get("mcp_servers"), "tool_calls": calls,
            "final_text": final.get("result") or "\n".join(texts), "num_turns": final.get("num_turns"),
            "cost_usd": final.get("total_cost_usd"), "is_error": final.get("is_error")}


def delivered(calls: list[dict]) -> list[dict]:
    return [item for c in calls if c["tool"] in ("memory_get", "memory_find") and isinstance(c.get("body"), dict)
            for item in c["body"].get("evidence") or []]


def evaluate(check: dict, calls: list[dict], evidence: list[dict], before: dict, after: dict) -> bool:
    if "tool_called" in check:
        args = check.get("args")
        return any(c["tool"] == check["tool_called"] and (args is None or c["input"] == args) for c in calls)
    if "tool_not_called" in check:
        return not any(c["tool"] == check["tool_not_called"] for c in calls)
    if "tool_result" in check:
        spec = check["tool_result"]
        bodies = [c["body"] for c in calls if c["tool"] == spec["tool"] and isinstance(c.get("body"), dict)]
        return bool(bodies) and all(b.get(spec["field"]) == spec["equals"] for b in bodies)
    if "delivered_key" in check:
        return any(e.get("memory_ref") == check["delivered_key"] and e.get("state") == "resolved" for e in evidence)
    if "not_delivered_key" in check:
        return not any(e.get("memory_ref") == check["not_delivered_key"] for e in evidence)
    if "not_delivered_text" in check:
        return not any(e.get("content") == check["not_delivered_text"] for e in evidence)
    if "logical_unchanged" in check:
        return all(before[k] == after[k] for k in check["logical_unchanged"])
    if "logical_after" in check:
        spec = check["logical_after"]
        state = after[spec["key"]]
        return state["lookup_status"] == spec["lookup_status"] and (
            "content" not in spec or [c for _, c in state["facts"]] == [spec["content"]])
    if "tool_error_seen" in check:
        return any(c.get("is_error") for c in calls) is check["tool_error_seen"]
    raise ValueError(f"unknown check {check}")


def redact(value, run: Path):
    """Local paths become labels; a path is matched only where one starts, not inside another."""
    text = json.dumps(value)
    for path, label in ((str(run), "<RUN>"), (str(MCP_DIR.parents[1]), "<REPO>"), (sys.prefix, "<VENV>"),
                        (str(Path.home()), "<HOME>")):
        text = re.sub(r"(?<![\w./-])" + re.escape(path) + r"(?![\w.-])", label, text)
    return json.loads(text)


async def main_async(run: Path, out: Path, only: set[str] | None, scenario_path: Path = SCENARIO) -> dict:
    scenario_bytes = scenario_path.read_bytes()
    scenario = json.loads(scenario_bytes)
    run = private_dir(run)
    root = private_dir(run / "store") / "root"
    assert_safe_root(server_env(root, scenario["scope"], scenario["tenant"]))
    await seed(scenario, root)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for session in scenario["sessions"]:
        if only and session["id"] not in only:
            continue
        env, host = session_host(scenario, session, run, root)
        before = await snapshot(scenario, root)
        events, elapsed = run_agent(session, env, run)
        after = await snapshot(scenario, root)
        record = transcript(events)
        evidence = delivered(record["tool_calls"])
        named = [session["prompt"]] + [str(v) for c in record["tool_calls"] for v in (c.get("input") or {}).values()]
        flags = evidence_check.check(record["final_text"], delivered_contents=[e.get("content", "") for e in evidence],
                                     delivered_keys=[e.get("memory_ref") for e in evidence], named=named)
        checks = [{"check": c, "passed": evaluate(c, record["tool_calls"], evidence, before, after)}
                  for c in session["checks"]]
        receipt = {"id": session["id"], "workflow": session["workflow"], "title": session["title"],
                   "host": host, "prompt": session["prompt"], **record, "elapsed_s": round(elapsed, 1),
                   "delivered_evidence": evidence, "host_check_flags": flags,
                   "displayed_output": evidence_check.displayed(record["final_text"], flags, evidence),
                   "checks": checks, "logical_before": before, "logical_after": after}
        receipt = redact(receipt, run)
        (out / f"{session['id']}.json").write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
        (out / f"{session['id']}.stream.jsonl").write_text(
            "\n".join(json.dumps(redact(e, run)) for e in events) + "\n", encoding="utf-8")
        rows.append({"id": session["id"], "workflow": session["workflow"], "checks_passed": all(c["passed"] for c in checks),
                     "failed_checks": [c["check"] for c in checks if not c["passed"]],
                     "host_check_flags": sorted({f["flag"] for f in flags}),
                     "tools": [c["tool"] for c in record["tool_calls"]], "model": record["model"]})
        print(json.dumps(rows[-1]), flush=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=HERE, capture_output=True, text=True).stdout.strip()
    agent = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip()
    summary = {"schema": "agent-memory-mcp-agent-pilot-receipt/0.1.0", "head": head, "scenario": scenario_path.name,
               "scenario_sha256": hashlib.sha256(scenario_bytes).hexdigest(),
               "contract_sha256": hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
               "agent": {"harness": "Claude Code non-interactive (claude -p)", "version": agent,
                         "models": sorted({r["model"] for r in rows if r["model"]}),
                         "flags": "--tools '' --strict-mcp-config --allowedTools <five memory tools> "
                                  "--append-system-prompt <evidence contract> --no-session-persistence --setting-sources project"},
               "sessions": rows}
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--sessions")
    parser.add_argument("--scenario", type=Path, default=SCENARIO)
    options = parser.parse_args()
    if not options.run_dir.is_absolute():
        raise SystemExit("--run-dir must be absolute")
    if options.run_dir.exists() and any(options.run_dir.iterdir()):
        raise SystemExit("--run-dir must be new or empty: a pilot uses a dedicated store")
    only = set(options.sessions.split(",")) if options.sessions else None
    summary = asyncio.run(main_async(options.run_dir, options.out, only, options.scenario.resolve()))
    return 0 if all(r["checks_passed"] for r in summary["sessions"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
