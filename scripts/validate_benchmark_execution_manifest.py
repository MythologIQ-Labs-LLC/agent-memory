#!/usr/bin/env python3
"""Validate supplemental execution provenance without granting benchmark authority.

Evidence pointers (``normalized_run.uri`` and every ``artifacts[].uri``) are POSIX paths
relative to the repository root at the evidence commit. ``--evidence-root`` names that root;
with it, every pointed-to file is re-hashed and must match its recorded SHA-256.

A manifest's own ``review`` block is a claim, not authority. ``accepted`` validates only
when an owner-controlled decision record (``--review-authority``) binds the same reviewer,
decision reference, run id and normalized-run digest, names an executor distinct from the
reviewer, and every evidence file has been re-hashed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath

import jsonschema

SCHEMA = Path(__file__).resolve().parents[1] / "schemas/benchmark-execution-manifest.schema.json"
# jsonschema checks "date-time" only when the optional rfc3339-validator package is
# installed. It is not in the pinned profile, so the format is enforced here.
RFC3339_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,9})?Z$")
FLOATING_MODEL_REVISIONS = {"", "latest", "main", "master", "head", "default", "stable", "current", "unknown"}
# Kept from the first checker revision: these substrings are refused anywhere in an argument.
SENSITIVE_SUBSTRINGS = ("--api-key", "--api_key", "--auth-token", "--password", "--secret", "bearer ")
CREDENTIAL_FLAG = re.compile(
    r"(?:^|[\s'\"=])--?[\w-]*(api[-_]?key|access[-_]?key|secret|password|passwd|auth[-_]?token|access[-_]?token"
    r"|hf[-_]?token|bearer|token)(?![a-z])", re.IGNORECASE)
CREDENTIAL_ASSIGNMENT = re.compile(r"(?:^|[\s'\"])[A-Z0-9_]*(API_KEY|SECRET|PASSWORD|TOKEN(?!S)|ACCESS_KEY)[A-Z0-9_]*=")
CREDENTIAL_VALUE = re.compile(
    r"(\bsk-[A-Za-z0-9_-]{16,}|\bghp_[A-Za-z0-9]{20,}|\bgithub_pat_[A-Za-z0-9_]{20,}|\bAKIA[0-9A-Z]{16}\b"
    r"|\bxox[abpr]-[A-Za-z0-9-]{10,}|\bhf_[A-Za-z0-9]{30,}|\bbearer\s+\S+)", re.IGNORECASE)
CREDENTIAL_PARAMETER = ("api_key", "api-key", "secret", "password", "authorization", "access_token", "token")
# Token *counts* are inference settings, not credentials; only these exact names are exempt.
TOKEN_COUNT_PARAMETERS = {"max_tokens", "max_output_tokens", "max_new_tokens", "context_window_tokens",
                          "max_input_tokens", "max_completion_tokens", "num_predict_tokens"}
DECISION_REF = re.compile(r"^https://[A-Za-z0-9.-]+\.[A-Za-z]{2,}/\S+$")


def _safe_pointer(value: str) -> None:
    if (not value or PurePosixPath(value).is_absolute() or "://" in value or "\\" in value or ":" in value
            or "%" in value or value.startswith("~") or any(not ch.isprintable() for ch in value)
            or any(part in ("", "..", ".") for part in value.split("/"))):
        raise ValueError(f"unsafe evidence pointer: {value!r}")


def _check_secrets(manifest: dict) -> None:
    for arg in manifest["execution"]["argv_redacted"]:
        if (any(term in arg.lower() for term in SENSITIVE_SUBSTRINGS) or CREDENTIAL_FLAG.search(arg)
                or CREDENTIAL_ASSIGNMENT.search(arg) or CREDENTIAL_VALUE.search(arg)):
            raise ValueError("command arguments must not expose sensitive credential flags or values")
    pointers = [manifest["normalized_run"]["uri"]] + [a["uri"] for a in manifest["artifacts"]]
    if any(CREDENTIAL_VALUE.search(p) or re.search(r"(token|key|secret|password)=", p, re.IGNORECASE) for p in pointers):
        raise ValueError("evidence pointers must not carry credential material")
    for call in manifest["inference"]["calls"]:
        for key, value in call["parameters"].items():
            if key.lower() not in TOKEN_COUNT_PARAMETERS and any(term in key.lower() for term in CREDENTIAL_PARAMETER):
                raise ValueError("model parameters must not contain credential fields")
            if isinstance(value, str) and CREDENTIAL_VALUE.search(value):
                raise ValueError("model parameters must not contain credential values")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_evidence(manifest: dict, evidence_root: Path) -> dict:
    """Re-hash the normalized run and every artifact under ``evidence_root``; return the parsed normalized run."""
    root = evidence_root.resolve()
    pointers = [("normalized_run", manifest["normalized_run"])] + [(a["kind"], a) for a in manifest["artifacts"]]
    for label, pointer in pointers:
        _safe_pointer(pointer["uri"])
        path = (root / pointer["uri"]).resolve()
        if root not in path.parents:
            raise ValueError(f"evidence pointer escapes the evidence root: {pointer['uri']}")
        if not path.is_file():
            raise ValueError(f"missing evidence file for {label}: {pointer['uri']}")
        if _sha256_file(path) != pointer["sha256"]:
            raise ValueError(f"SHA-256 mismatch for {label}: {pointer['uri']}")
    try:
        normalized = json.loads((root / manifest["normalized_run"]["uri"]).read_bytes())
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("normalized_run is not a JSON memory-benchmark-run record "
                         f"(compressed or non-JSON file: {manifest['normalized_run']['uri']})") from exc
    if not isinstance(normalized, dict):
        raise ValueError("normalized_run is not a JSON object")
    return normalized


def _identity(value) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("review authority identities must be non-empty strings")
    return " ".join(value.split()).casefold()


def _check_authority(manifest: dict, authority: dict | None, authority_sha256: str | None,
                     expected_authority_sha256: str | None) -> None:
    review = manifest["review"]
    if authority is None:
        raise ValueError("accepted evidence requires an owner-controlled review authority record; "
                         "a reviewer string in the manifest is a claim, not a decision")
    # Whoever writes a manifest can write an authority file too. The digest the owner publishes
    # (out of band, e.g. on the decision issue) is what binds the record to the owner.
    if not expected_authority_sha256 or authority_sha256 != expected_authority_sha256:
        raise ValueError("review authority digest does not match the owner-published digest")
    if not DECISION_REF.match(str(review["decision_ref"])):
        raise ValueError("decision_ref must be a stable https reference")
    decisions = authority.get("decisions") if isinstance(authority, dict) else None
    if not isinstance(decisions, list) or not all(isinstance(d, dict) for d in decisions):
        raise ValueError("review authority must be an object with a list of decision objects")
    matches = [d for d in decisions if d.get("decision_ref") == review["decision_ref"]]
    if len(matches) != 1:
        raise ValueError("review authority has no unique decision for this decision_ref")
    decision = matches[0]
    if decision.get("decision") != "accepted":
        raise ValueError("review authority decision is not accepted")
    if _identity(decision.get("reviewer")) != _identity(review["reviewer"]):
        raise ValueError("review authority names a different reviewer")
    try:
        independent = _identity(decision.get("executor")) != _identity(decision.get("reviewer"))
    except ValueError:
        independent = False
    if not independent:
        raise ValueError("accepted evidence requires a reviewer independent of the executor")
    if decision.get("run_id") != manifest["run_id"]:
        raise ValueError("review authority decision is bound to a different run_id")
    if decision.get("normalized_sha256") != manifest["normalized_run"]["sha256"]:
        raise ValueError("review authority decision is bound to a different normalized run")


def validate(manifest: dict, normalized: dict | None = None, *, evidence_root: Path | None = None,
             authority: dict | None = None, authority_sha256: str | None = None,
             expected_authority_sha256: str | None = None) -> None:
    """Raise on any defect. ``normalized`` alone is an identity check only; acceptance needs ``evidence_root``."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(manifest)
    _safe_pointer(manifest["normalized_run"]["uri"])
    for artifact in manifest["artifacts"]:
        _safe_pointer(artifact["uri"])

    timing = manifest["timing"]
    for field in ("started_at", "finished_at"):
        if not RFC3339_UTC.match(timing[field]):
            raise ValueError(f"{field} must be an RFC 3339 UTC timestamp")
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
    _check_secrets(manifest)
    costs = manifest["costs"]
    if (costs["status"] == "measured") != (costs["amount"] is not None):
        raise ValueError("cost status and amount disagree")
    if any(call["endpoint_class"] == "hosted" for call in calls) and costs["status"] == "not_applicable":
        raise ValueError("hosted inference requires a measured cost (or not_measured), never not_applicable")

    verified = False
    if evidence_root is not None:
        on_disk = verify_evidence(manifest, evidence_root)
        if normalized is not None and normalized != on_disk:
            raise ValueError("supplied normalized run differs from the hashed file")
        normalized, verified = on_disk, True

    status = manifest["review"]["status"]
    if status == "accepted":
        review = manifest["review"]
        if not review["reviewer"] or not review["decision_ref"]:
            raise ValueError("accepted evidence requires independent reviewer and decision reference")
        if not manifest["redaction"]["reviewed"] or not manifest["system"]["worktree_clean"]:
            raise ValueError("accepted evidence requires redaction review and clean source")
        if any(not item["model_revision"] and not item["model_digest"] for item in calls):
            raise ValueError("accepted inference requires immutable model version or digest")
        if any(not item["model_digest"] and str(item["model_revision"]).strip().lower() in FLOATING_MODEL_REVISIONS
               for item in calls):
            raise ValueError("accepted inference requires a pinned model revision, not a floating alias")
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
        if not verified:
            raise ValueError("accepted evidence requires every evidence file re-hashed under an evidence root")
        _check_authority(manifest, authority, authority_sha256, expected_authority_sha256)

    if manifest["review"]["comparison_eligibility"] == "eligible_on_profile":
        if status != "accepted":  # accepted already required a verified normalized run above
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
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--normalized-run", type=Path, help="normalized run file; its SHA-256 must match the manifest")
    parser.add_argument("--evidence-root", type=Path, help="repository root at the evidence commit; re-hashes every pointer")
    parser.add_argument("--review-authority", type=Path, help="owner-controlled decision record (required for accepted)")
    parser.add_argument("--review-authority-sha256", help="digest of that record as published by the owner (required for accepted)")
    args = parser.parse_args()
    try:
        obj = json.loads(args.manifest.read_bytes())
        normalized = None
        if args.normalized_run:
            data = args.normalized_run.read_bytes()
            if hashlib.sha256(data).hexdigest() != obj["normalized_run"]["sha256"]:
                raise ValueError("normalized run SHA-256 does not match recorded digest")
            normalized = json.loads(data)
        authority = authority_sha256 = None
        if args.review_authority:
            authority_bytes = args.review_authority.read_bytes()
            authority, authority_sha256 = json.loads(authority_bytes), hashlib.sha256(authority_bytes).hexdigest()
        validate(obj, normalized, evidence_root=args.evidence_root, authority=authority,
                 authority_sha256=authority_sha256, expected_authority_sha256=args.review_authority_sha256)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, json.JSONDecodeError,
            jsonschema.ValidationError) as exc:
        print(f"BLOCKED: {exc.message if isinstance(exc, jsonschema.ValidationError) else exc}", file=sys.stderr)
        return 1
    hashed = "evidence re-hashed" if args.evidence_root else "evidence NOT re-hashed"
    if obj["review"]["status"] == "accepted":
        print(f"PASS: execution envelope validated ({hashed}); acceptance bound to the supplied review authority")
    else:
        print(f"PASS: execution envelope validated, without conferring acceptance ({hashed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
