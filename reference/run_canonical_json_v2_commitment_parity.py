from __future__ import annotations

import argparse
import json
from pathlib import Path

from canonical_json_v2_migration_preflight import compute_candidate_commitments


DEFAULT_FIXTURE = Path("reference/fixtures/runtime/canonical-json-v2-commitment-parity-input-v1.json")


def run(path: Path) -> dict[str, dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("fixture_id") != "agent-memory-canonical-json-v2-commitment-parity-input-v1":
        raise ValueError("unexpected commitment parity fixture")
    if payload.get("status") != "FROZEN_INPUT_ONLY_NO_EXPECTED_ROOTS":
        raise ValueError("commitment parity input must remain output-free")

    results: dict[str, dict[str, str]] = {}
    for case in payload["cases"]:
        commitments = compute_candidate_commitments(
            substrate_state=case["substrate"],
            governance_maps=case["governance"]["maps"],
            governance_logs=case["governance"]["logs"],
            governance_residual=case["governance"]["residual"],
        )
        results[str(case["id"])] = {
            "governance_commitment": commitments.governance_commitment,
            "logical_state_digest": commitments.logical_state_digest,
            "substrate_commitment": commitments.substrate_commitment,
        }
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rendered = json.dumps(run(args.fixture), sort_keys=True, separators=(",", ":")) + "\n"
    if args.output is not None:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
