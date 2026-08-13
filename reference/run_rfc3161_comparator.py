#!/usr/bin/env python3
"""Run a pinned OpenSSL RFC 3161 verification comparator for #265.

The comparator validates a real timestamp response against an explicit trust
root and proves negative-path rejection with a mismatched trust root. The
result is external time evidence only; it does not establish event occurrence,
Agent Memory currentness, or PAMA authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

OPENSSL_VERSION = "3.6.3"
OPENSSL_COMMIT = "aae016bfd52fcad2bc9657c2c782cfdf73b1ed5f"
FIXTURE_SOURCE = "openssl/openssl:test/recipes/80-test_tsa_data"
AUTHORITY_EFFECT = "none"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--openssl-bin", required=True)
    parser.add_argument("--fixture-dir", required=True)
    parser.add_argument("--agent-memory-commit", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    openssl = str(Path(args.openssl_bin).resolve())
    fixtures = Path(args.fixture_dir).resolve()
    query = fixtures / "all-zero.tsq"
    response = fixtures / "sectigo-all-zero.tsr"
    trusted_root = fixtures / "user-trust-ca.pem"
    alternate_root = fixtures / "comodo-aaa.pem"

    for path in (query, response, trusted_root, alternate_root):
        if not path.is_file():
            raise SystemExit(f"missing comparator fixture: {path}")

    version = run([openssl, "version"])
    if version.returncode != 0 or f"OpenSSL {OPENSSL_VERSION}" not in version.stdout:
        raise SystemExit(f"unexpected OpenSSL version: {version.stdout.strip()} {version.stderr.strip()}")

    valid = run([
        openssl,
        "ts",
        "-verify",
        "-no_check_time",
        "-queryfile",
        str(query),
        "-in",
        str(response),
        "-CAfile",
        str(trusted_root),
    ])

    wrong_root = run([
        openssl,
        "ts",
        "-verify",
        "-no_check_time",
        "-queryfile",
        str(query),
        "-in",
        str(response),
        "-CAfile",
        str(alternate_root),
    ])

    inspected = run([openssl, "ts", "-reply", "-in", str(response), "-text"])

    result = {
        "schema_version": "1.0.0",
        "comparator": "openssl-rfc3161",
        "agent_memory_commit": args.agent_memory_commit,
        "external_source": {
            "repository": "openssl/openssl",
            "version": OPENSSL_VERSION,
            "commit": OPENSSL_COMMIT,
            "fixture_source": FIXTURE_SOURCE,
        },
        "fixture_digests": {
            "query": sha256_file(query),
            "response": sha256_file(response),
            "trusted_root": sha256_file(trusted_root),
            "alternate_root": sha256_file(alternate_root),
        },
        "checks": {
            "trusted_root_verifies": valid.returncode == 0,
            "wrong_root_rejected": wrong_root.returncode != 0,
            "response_inspectable": inspected.returncode == 0,
        },
        "verification": {
            "status": "verified" if valid.returncode == 0 else "invalid",
            "claim_kind": "existence_by_time",
            "trust_chain_verified": valid.returncode == 0,
            "wrong_trust_root_rejected": wrong_root.returncode != 0,
            "event_occurrence_time_proven": False,
            "currentness": "not_established",
            "authority_effect": AUTHORITY_EFFECT,
        },
    }

    result["status"] = "pass" if all(result["checks"].values()) else "fail"
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
