#!/usr/bin/env python3
"""Reproduce #808 validator defects: run identical inputs through two validator revisions.

Usage: probe_execution_manifest_defects.py ORIGINAL_VALIDATOR.py [CANDIDATE_VALIDATOR.py]

Each probe is a manifest (synthetic fixture with one change) that must be refused. The
original is called the way its CLI calls it (normalized identity dict, no file re-hashing);
the candidate is called with the evidence root and no review authority, which is what a
caller holding only the manifest can supply. Output is JSON: probe -> {original, candidate}.
"""
from __future__ import annotations

import copy
import importlib.util
import inspect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "reference/fixtures/benchmarks"


def load(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.SCHEMA = ROOT / "schemas/benchmark-execution-manifest.schema.json"
    return module


def outcome(module, manifest: dict, normalized: dict) -> str:
    kwargs = {"evidence_root": ROOT} if "evidence_root" in inspect.signature(module.validate).parameters else {}
    try:
        module.validate(copy.deepcopy(manifest), copy.deepcopy(normalized), **kwargs)
    except Exception as exc:  # noqa: BLE001 - the probe records any refusal
        return f"REFUSED: {str(exc).splitlines()[0][:120]}"
    return "PASSED"


def probes(accepted: dict, example: dict) -> dict[str, dict]:
    def edit(base, fn):
        value = copy.deepcopy(base)
        fn(value)
        return value
    hosted = {"purpose": "generation", "provider": "p", "model_id": "m", "model_revision": "r1", "model_digest": None,
              "endpoint_class": "hosted", "parameters": {"temperature": 0, "top_p": 1, "seed": 1,
              "context_window_tokens": 8, "max_output_tokens": 8}, "prompt_sha256": "d" * 64, "count": 1}
    return {
        "self_declared_acceptance_without_authority": accepted,
        "forged_artifact_digest": edit(accepted, lambda x: x["artifacts"][1].update(sha256="0" * 64)),
        "artifact_file_absent": edit(accepted, lambda x: x["artifacts"][1].update(uri="reference/fixtures/benchmarks/absent.jsonl")),
        "non_rfc3339_timestamp": edit(example, lambda x: x["timing"].update(started_at="20261014T120000Z", finished_at="20261014T120012Z")),
        "hosted_inference_cost_not_applicable": edit(example, lambda x: x["inference"].update(used=True, calls=[hosted])),
        "backslash_traversal_pointer": edit(example, lambda x: x["artifacts"][0].update(uri="a\\..\\..\\secret")),
        "drive_letter_pointer": edit(example, lambda x: x["artifacts"][0].update(uri="C:/secret")),
        "percent_encoded_traversal": edit(example, lambda x: x["artifacts"][0].update(uri="a/%2e%2e/%2e%2e/secret")),
        "token_flag_in_argv": edit(example, lambda x: x["execution"]["argv_redacted"].append("--token=abc")),
        "api_key_value_in_argv": edit(example, lambda x: x["execution"]["argv_redacted"].append("sk-ABCDEFGHIJKLMNOPQRSTUV")),
        "floating_model_revision_accepted": edit(accepted, lambda x: x["inference"].update(used=True, calls=[dict(
            hosted, purpose="embedding", endpoint_class="local", model_revision="latest", prompt_sha256=None)])),
    }


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print(__doc__, file=sys.stderr)
        return 2
    original = load(argv[1], "original_validator")
    candidate = load(argv[2] if len(argv) == 3 else str(ROOT / "scripts/validate_benchmark_execution_manifest.py"), "candidate_validator")
    accepted = json.loads((FIXTURES / "execution-manifest-accepted/manifest.json").read_text())
    normalized = json.loads((FIXTURES / "execution-manifest-accepted/normalized.json").read_text())
    example = json.loads((FIXTURES / "benchmark-execution-manifest-example.json").read_text())
    report = {}
    for name, manifest in probes(accepted, example).items():
        identity = normalized if manifest["run_id"] == normalized["run_id"] else None
        report[name] = {"original": outcome(original, manifest, identity), "candidate": outcome(candidate, manifest, identity)}
    print(json.dumps(report, indent=2))
    return 0 if all(r["candidate"].startswith("REFUSED") for r in report.values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
