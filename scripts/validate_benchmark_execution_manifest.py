#!/usr/bin/env python3
"""Validate supplemental execution provenance without granting benchmark authority."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath

import jsonschema

SCHEMA = Path(__file__).resolve().parents[1] / "schemas/benchmark-execution-manifest.schema.json"


def _safe_pointer(value: str) -> None:
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("..", ".") for part in value.split("/")) or "://" in value:
        raise ValueError("unsafe evidence pointer")


def validate(manifest: dict, normalized: dict | None = None) -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(manifest)
    _safe_pointer(manifest["normalized_run"]["uri"])
    for artifact in manifest["artifacts"]:
        _safe_pointer(artifact["uri"])

    timing = manifest["timing"]
    start = datetime.fromisoformat(timing["started_at"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(timing["finished_at"].replace("Z", "+00:00"))
    if end < start:
        raise ValueError("finished_at is earlier than started_at")
    expected_ms = (end - start).total_seconds() * 1000
    if abs(expected_ms - timing["elapsed_ms"]) > max(5000, expected_ms * 0.05):
        raise ValueError("wall-clock timing inconsistent with elapsed_ms")
    calls = manifest["inference"]["calls"]
    if manifest["inference"]["used"] != bool(calls):
        raise ValueError("inference.used and model calls disagree")
    if len({(x["kind"], x["uri"]) for x in manifest["artifacts"]}) != len(manifest["artifacts"]):
        raise ValueError("duplicate evidence artifact identity")
    if len({x["uri"] for x in manifest["artifacts"]}) != len(manifest["artifacts"]):
        raise ValueError("multiple evidence artifacts claim the same path")
    sensitive = ("--api-key", "--api_key", "--auth-token", "--password", "--secret", "bearer ")
    if any(any(term in arg.lower() for term in sensitive) for arg in manifest["execution"]["argv_redacted"]):
        raise ValueError("command arguments must not expose sensitive credential flags or bearer values")
    if any(any(term in key.lower() for term in ("api_key", "api-key", "secret", "password", "authorization", "access_token"))
           for call in calls for key in call["parameters"]):
        raise ValueError("model parameters must not contain credential fields")
    costs = manifest["costs"]
    if (costs["status"] == "measured") != (costs["amount"] is not None):
        raise ValueError("cost status and amount disagree")

    status = manifest["review"]["status"]
    if status == "accepted":
        review = manifest["review"]
        if not review["reviewer"] or not review["decision_ref"]:
            raise ValueError("accepted evidence requires independent reviewer and decision reference")
        if not manifest["redaction"]["reviewed"] or not manifest["system"]["worktree_clean"]:
            raise ValueError("accepted evidence requires redaction review and clean source")
        if any(not item["model_revision"] and not item["model_digest"] for item in calls):
            raise ValueError("accepted inference requires immutable model version or digest")
        if costs["status"] == "not_measured":
            raise ValueError("accepted evidence requires explicit measured or not-applicable costs")
        if any(call["endpoint_class"] == "hosted" for call in calls) and costs["status"] != "measured":
            raise ValueError("accepted hosted inference requires a measured cost, including explicit zero if free")
        for call in calls:
            if call["purpose"] in ("generation", "judge"):
                if not call["prompt_sha256"]:
                    raise ValueError("accepted generative inference requires exact prompt digest")
                required_settings = {"temperature", "top_p", "seed", "context_window_tokens", "max_output_tokens"}
                if not required_settings.issubset(call["parameters"]):
                    raise ValueError("accepted generation/judge requires explicitly recorded inference settings")
        kinds = {artifact["kind"] for artifact in manifest["artifacts"]}
        if not {"native_result", "row_level_results"}.issubset(kinds):
            raise ValueError("accepted evidence requires native and per-row artifacts")
        if normalized is None:
            raise ValueError("accepted evidence requires normalized run verification")

    if manifest["review"]["comparison_eligibility"] == "eligible_on_profile":
        if status != "accepted" or normalized is None:
            raise ValueError("comparison eligibility requires accepted evidence and verified normalized run")

    if normalized is not None:
        matches = (
            (manifest["run_id"], normalized.get("run_id"), "run_id"),
            (manifest["system"]["id"], normalized.get("system", {}).get("id"), "system.id"),
            (manifest["system"]["revision"], normalized.get("system", {}).get("revision"), "system.revision"),
            (manifest["benchmark"]["id"], normalized.get("benchmark", {}).get("id"), "benchmark.id"),
            (manifest["benchmark"]["task_profile"], normalized.get("benchmark", {}).get("task_profile"), "benchmark.task_profile"),
            (manifest["benchmark"]["input_sha256"], normalized.get("benchmark", {}).get("input_sha256"), "benchmark.input_sha256"),
            (manifest["benchmark"]["selection_id"], normalized.get("execution", {}).get("selection_id"), "execution.selection_id"),
            (manifest["benchmark"]["sample_count"], normalized.get("execution", {}).get("sample_count"), "execution.sample_count"),
        )
        for left, right, field in matches:
            if left != right:
                raise ValueError(f"normalized run disagrees on {field}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--normalized-run", type=Path)
    args = parser.parse_args()
    try:
        source = args.manifest.read_bytes()
        obj = json.loads(source)
        normalized = None
        if args.normalized_run:
            data = args.normalized_run.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if digest != obj["normalized_run"]["sha256"]:
                raise ValueError("normalized run SHA-256 does not match recorded digest")
            normalized = json.loads(data)
        validate(obj, normalized)
    except (OSError, ValueError, KeyError, json.JSONDecodeError, jsonschema.ValidationError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 1
    print("PASS: execution envelope validated, without conferring acceptance")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
