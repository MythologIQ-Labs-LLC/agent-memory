"""Stage C held-out adversarial run through real stdio MCP and governed SQLite.

``quality_cases_adversarial.json`` was frozen in its own commit before any answer-support model
was run on it. This driver seeds its records, applies its lifecycle steps through the real tools
(governed correction with a host record, a same-key rewrite, a host-granted reversible forget),
restarts the server, asks every question, restarts again and asks every question again. It runs
arms over the same store at the same retrieval budget: the host's answer-support check disabled
(the prior behavior), then one arm per ``--support-model-dir`` in the order given; ``DIR@METHOD``
pins a method version the directory's model serves (host setting AGENT_MEMORY_MCP_SUPPORT_METHOD). The last one
is the candidate under qualification; the others are reported for comparison. Labels are joined
after the MCP calls; they are never tool arguments.

Criterion, fixed in this file before its first run: with the check enabled,
* no answerable task whose required memory was fully delivered is marked insufficient
  (false abstentions = 0), and
* at least 9 of the 12 unanswerable tasks are marked insufficient (three quarters, rounded up;
  ``--cases`` applies the same fraction to another cohort, e.g. all 3 of the development set),
* with identical assessments before and after a restart, no generated answer, the default
  ``all_returned`` profile, the forgotten memory never delivered, the corrected-away text never
  delivered as current, and the same delivered evidence with the check enabled or disabled.
This is a small author-written holdout, not a calibrated benchmark.

usage: stage_c_adversarial.py --support-model-dir DIR [--support-model-dir DIR ...] --out OUT.json [--cases CASES.json]
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time
from typing import Any

from mcp import Client, StdioServerParameters

HERE = Path(__file__).resolve().parent
SERVER = HERE / "server.py"
CASES = HERE / "quality_cases_adversarial.json"
SCHEMA = "agent-memory-stage-c-adversarial/0.1.0"
MIN_UNANSWERABLE_FRACTION = 0.75  # 9 of the frozen cohort's 12


def params(cases: dict, root: Path, **extra: str) -> StdioServerParameters:
    env = {"AGENT_MEMORY_MCP_ROOT": str(root), "AGENT_MEMORY_MCP_TENANT": cases["tenant"],
           "AGENT_MEMORY_MCP_ACTOR": "agent:stage-c-adversarial", "AGENT_MEMORY_MCP_SCOPE": cases["scope"],
           "PATH": os.environ.get("PATH", ""), **extra}
    return StdioServerParameters(command=sys.executable, args=[str(SERVER)], env=env)


async def tool(client: Client, name: str, args: dict) -> dict:
    result = await client.call_tool(name, args)
    if result.is_error or not isinstance(result.structured_content, dict):
        raise RuntimeError(f"{name} failed: {result!r}")
    return result.structured_content


async def seed(cases: dict, root: Path, temp: Path) -> list[dict]:
    """Writes every record, then the lifecycle steps; returns their receipts."""
    receipts = []
    async with Client(params(cases, root)) as client:
        for record in cases["records"]:
            saved = await tool(client, "memory_remember", {"key": record["key"], "text": record["text"]})
            if saved.get("committed") is not True:
                raise RuntimeError(f"seed write not committed: {record['key']}")
    for step in cases.get("lifecycle", []):
        extra: dict[str, str] = {}
        if step["op"] == "correct":
            authority = temp / f"correction-{len(receipts)}.json"
            authority.write_text(json.dumps({"key": step["key"], "text": step["text"]}), encoding="utf-8")
            extra["AGENT_MEMORY_MCP_CORRECTION_RECORD"] = str(authority)
        elif step["op"] == "forget":
            extra["AGENT_MEMORY_MCP_PRUNE_APPROVED_KEY"] = step["key"]
            extra["AGENT_MEMORY_MCP_PRUNE_EVIDENCE_REF"] = "operator-record:stage-c-adversarial-forget"
        async with Client(params(cases, root, **extra)) as client:
            if step["op"] == "correct":
                out = await tool(client, "memory_correct", {"key": step["key"], "text": step["text"]})
                ok = out.get("status") == "corrected" and out.get("operation") == "correction"
            elif step["op"] == "rewrite":
                out = await tool(client, "memory_remember", {"key": step["key"], "text": step["text"]})
                ok = out.get("committed") is True
            elif step["op"] == "forget":
                out = await tool(client, "memory_forget", {"key": step["key"]})
                ok = out.get("status") == "forgotten" and out.get("operation") == "pruning"
            else:
                raise ValueError(f"unknown lifecycle op {step['op']}")
        if not ok:
            raise RuntimeError(f"lifecycle step did not commit: {step['op']} {step['key']}: {out}")
        receipts.append({"op": step["op"], "key": step["key"], "operation": out.get("operation"),
                         "receipt_id": out.get("receipt_id"), "status": out.get("status"),
                         "committed": out.get("committed")})
    return receipts


async def ask_all(cases: dict, root: Path, support_dir: str | None) -> list[dict]:
    extra = {}
    if support_dir:
        directory, _, method = support_dir.partition("@")
        extra["AGENT_MEMORY_MCP_SUPPORT_MODEL_DIR"] = directory
        if method:
            extra["AGENT_MEMORY_MCP_SUPPORT_METHOD"] = method
    by_key = {r["key"]: r["text"] for r in cases["records"]}
    lifecycle = cases.get("lifecycle", [])
    for step in lifecycle:
        if step["op"] in ("correct", "rewrite"):
            by_key[step["key"]] = step["text"]
    superseded = {step["superseded_text"] for step in lifecycle if "superseded_text" in step}
    forgotten = {step["key"] for step in lifecycle if step["op"] == "forget"}
    rows = []
    async with Client(params(cases, root, **extra)) as client:
        for task in cases["tasks"]:
            started = time.perf_counter()
            out = await tool(client, "memory_find", {"question": task["question"], "max_items": 5})
            elapsed_ms = (time.perf_counter() - started) * 1000
            evidence = out.get("evidence") or []
            keys = [e.get("memory_ref") for e in evidence]
            current_full = [e.get("memory_ref") for e in evidence
                            if e.get("state") == "resolved" and e.get("latest_for_key") is not False
                            and by_key.get(e.get("memory_ref")) == e.get("content")]
            support = out.get("answer_support") or {}
            supported_refs = set(support.get("supported_fact_refs") or [])
            by_ref = {e.get("fact_ref"): e.get("memory_ref") for e in evidence}
            rows.append({
                "id": task["id"], "category": task.get("category"), "question": task["question"],
                "answerable": bool(task["required"]), "required": task["required"],
                "keys": keys, "current_full_text_keys": current_full,
                "required_complete": set(task["required"]).issubset(current_full) if task["required"] else None,
                "assessment": out.get("evidence_assessment"), "reason": out.get("evidence_assessment_reason"),
                "support_status": support.get("status"), "support_method": support.get("method"),
                "joint_supported": support.get("joint_supported"),
                "cross_memory_candidates": [[by_ref.get(f) for f in c["facts"]]
                                            for c in support.get("cross_memory_candidates") or []],
                "supported_keys": [e.get("memory_ref") for e in evidence if e.get("fact_ref") in supported_refs],
                "superseded_text_as_current": any(e.get("content") in superseded and e.get("latest_for_key") is not False
                                                  for e in evidence),
                "superseded_text_disclosed": any(e.get("content") in superseded for e in evidence),
                "forgotten_delivered": bool(forgotten & set(keys)),
                "profile": out.get("profile"), "answer_generated": out.get("answer_generated"),
                "answerability_verified": out.get("answerability_verified"),
                "elapsed_ms": round(elapsed_ms, 1),
            })
    return rows


def summarise(rows: list[dict]) -> dict[str, Any]:
    answerable = [r for r in rows if r["answerable"]]
    unanswerable = [r for r in rows if not r["answerable"]]
    delivered = [r for r in answerable if r["required_complete"]]
    return {
        "answerable": len(answerable), "unanswerable": len(unanswerable),
        "answerable_required_delivered": len(delivered),
        "false_abstentions": sorted(r["id"] for r in delivered if r["assessment"] == "insufficient_evidence"),
        "abstentions_on_undelivered_answerable": sorted(r["id"] for r in answerable if not r["required_complete"]
                                                        and r["assessment"] == "insufficient_evidence"),
        "support_in_required": sum(bool(set(r["supported_keys"]) & set(r["required"])) for r in delivered),
        "unanswerable_abstained": sum(r["assessment"] == "insufficient_evidence" for r in unanswerable),
        "retrieval_misses": sorted(r["id"] for r in answerable if not r["required_complete"]),
        "unsupported_candidate_support": sorted(
            [r["id"] for r in unanswerable if r["supported_keys"]]
            + [r["id"] for r in answerable if not set(r["supported_keys"]) <= set(r["required"])]),
        "cross_memory_candidate_tasks": sorted(r["id"] for r in rows if r.get("cross_memory_candidates")),
        "false_sufficiency": sorted(r["id"] for r in unanswerable if r["assessment"] != "insufficient_evidence"),
        "invariants_hold": all(r["profile"] == "all_returned" and r["answer_generated"] is False
                               and r["answerability_verified"] is False and not r["forgotten_delivered"]
                               and not r["superseded_text_as_current"] for r in rows),
    }


def arm_passes(arm: dict, minimum: int) -> bool:
    summary = arm["summary"]
    return (not summary["false_abstentions"] and summary["unanswerable_abstained"] >= minimum
            and summary["invariants_hold"] and arm["stable_across_restart"])


async def run(support_dirs: list[str], cases_path: Path = CASES) -> dict:
    manifest = cases_path.read_bytes()
    cases = json.loads(manifest)
    with tempfile.TemporaryDirectory(prefix="am-stage-c-adv-") as temp:
        root = Path(temp) / "store"
        lifecycle = await seed(cases, root, Path(temp))
        arms = {}
        for directory in [None, *support_dirs]:
            first = await ask_all(cases, root, directory)
            again = await ask_all(cases, root, directory)  # a fresh server process: restart
            stable = [(r["assessment"], r["reason"], r["keys"]) for r in first] == \
                     [(r["assessment"], r["reason"], r["keys"]) for r in again]
            if directory and any(r["support_status"] == "unavailable" for r in first + again):
                raise RuntimeError(f"support check unavailable for {directory}")
            methods = {r["support_method"] for r in first if r["support_method"]}
            name = methods.pop() if directory and len(methods) == 1 else "support_check_disabled"
            if directory and name == "support_check_disabled":
                raise RuntimeError(f"no single support method reported for {directory}")
            later = [r["elapsed_ms"] for r in first[1:] + again[1:]]
            arms[name] = {"model_dir": directory, "summary": summarise(first), "stable_across_restart": stable,
                          "latency_ms": {"first_call": first[0]["elapsed_ms"],
                                         "later_median": round(statistics.median(later), 1),
                                         "later_max": max(later)},
                          "rows": first}
    unanswerable = arms["support_check_disabled"]["summary"]["unanswerable"]
    minimum = math.ceil(MIN_UNANSWERABLE_FRACTION * unanswerable)
    baseline_keys = [r["keys"] for r in arms["support_check_disabled"]["rows"]]
    same_evidence = all([r["keys"] for r in arm["rows"]] == baseline_keys for arm in arms.values())
    for arm in arms.values():
        arm["meets_criterion"] = arm_passes(arm, minimum) and same_evidence
    qualified = list(arms)[-1]
    passed = (len(arms) > 1 and arms[qualified]["meets_criterion"]
              and arms["support_check_disabled"]["summary"]["invariants_hold"])
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=HERE, capture_output=True, text=True).stdout.strip()
    return {"schema": SCHEMA, "status": "PASS" if passed else "BLOCKED", "head": head,
            "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
            "cases": cases_path.name, "qualified_arm": qualified,
            "criterion": {"false_abstentions": 0, "min_unanswerable_abstained": minimum},
            "delivered_evidence_identical_across_arms": same_evidence,
            "provider": "real stdio MCP / governed SQLite / memory_find all_returned, max_items=5",
            "qualification": "small author-written held-out cohort; not calibrated or blinded",
            "lifecycle": lifecycle, "arms": arms}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--support-model-dir", action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cases", type=Path, default=CASES)
    options = parser.parse_args()
    dirs = [str(Path(d.partition("@")[0]).resolve()) + ("@" + d.partition("@")[2] if "@" in d else "")
            for d in options.support_model_dir]
    report = asyncio.run(run(dirs, options.cases))
    options.out.parent.mkdir(parents=True, exist_ok=True)
    options.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "cases": report["cases"], "qualified_arm": report["qualified_arm"],
                      "delivered_evidence_identical_across_arms": report["delivered_evidence_identical_across_arms"],
                      **{name: {**arm["summary"], "stable_across_restart": arm["stable_across_restart"],
                                "meets_criterion": arm["meets_criterion"], "latency_ms": arm["latency_ms"]}
                         for name, arm in report["arms"].items()}}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
