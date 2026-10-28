#!/usr/bin/env python3
"""Execute frozen #644 v7 replay fixtures on a ``scope_distinct_v1`` store (v7 integration).

    python reference/run_644_v7_replays_sd.py --replay <replay_id> --output-dir <dir>

The byte-frozen ``run_644_v7_replays.py`` opens a second project in the same root for the
cross-project cases of ``governed-persisted-typed-slot-sufficiency-admission-recheck-v1`` (A4,
A6, A9). The integrated v7 candidate's default ``single_project_v1`` profile refuses that
(store-open contract 1.0.0). This runner executes the same frozen fixture, grammar
``644-v7-replay-dsl/1``, unchanged, on the supported multi-project profile. Its expectations are
unchanged because the two projects' keys never coincide in that fixture.

It differs from the frozen runner in exactly three places:

1. every handle is opened with ``store_profile="scope_distinct_v1"``;
2. ``retain_extracted``, a host-level proposal, names the handle's canonical memory for its key,
   as the facade's own ``remember`` does;
3. ``apply_open_proposal`` maps the proposal's canonical target back to the public key, so heads
   keep their fixture labels.

Everything else is the frozen runner's own ``run_case``, with its ``Scenario`` replaced for the
duration of a case. The provenance records this module's hash and the frozen runner's hash.
Verdict: PASS, FAIL or BLOCKED (dirty source tree). Exit 0 PASS, 1 FAIL, 2 BLOCKED.
"""
from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from pathlib import Path
from unittest import mock

REFERENCE = Path(__file__).resolve().parent
ROOT = REFERENCE.parent
sys.path.insert(0, str(REFERENCE))

import run_644_v7_replays as base  # noqa: E402
from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.api.surface import STORE_PROFILE_SCOPE_DISTINCT  # noqa: E402

RUNNER_VERSION = "644-v7-replay-runner/1+scope-distinct"
DSL_VERSION = base.DSL_VERSION
FIXTURE_DIR = base.FIXTURE_DIR
DEFAULT_OUTPUT = ROOT / "reports" / "validation" / "v7-integration" / "644-v7-replays-sd"
OUTPUT_REL = "reports/validation/v7-integration/644-v7-replays-sd/"
REPLAYS = ("governed-persisted-typed-slot-sufficiency-admission-recheck-v1",)

sha256_bytes, sha256_file, canonical, match = base.sha256_bytes, base.sha256_file, base.canonical, base.match
ReplayError = base.ReplayError
_BASE_RUN_CASE, _BASE_PROVENANCE = base.run_case, base.provenance  # bound before ``run_replay`` patches the names


class Scenario(base.Scenario):
    """The frozen scenario on a ``scope_distinct_v1`` store."""

    def _open(self, scope: str) -> AgentMemory:
        return AgentMemory.open(self.root, tenant=base.TENANT, actor_id=base.ACTOR, scope=scope, purpose=base.PURPOSE,
                                store_profile=STORE_PROFILE_SCOPE_DISTINCT)

    def apply(self, op: Mapping) -> None:
        kind = op["op"]
        if kind == "retain_extracted":
            super().apply({**op, "ref": self.memory._target(op["ref"])})
            # the frozen operation bound the label to the key it was given; bind the public key instead
            canonical_key = self.memory._target(op["ref"])
            self.heads.setdefault(op["ref"], self.heads.pop(canonical_key, 1))
            self._bind(op["ref"], self.labels.pop(canonical_key))
            return
        if kind == "apply_open_proposal":
            public = {self.memory._target(ref): ref for ref in list(self.heads)}
            before = dict(self.heads)
            super().apply(op)
            for key in [k for k in self.heads if k in public]:
                count = self.heads.pop(key)
                ref = public[key]
                self.heads[ref] = max(count, before.get(ref, 1) + 1)
                label = f"{key}@{count}"
                self._bind(f"{ref}@{self.heads[ref]}", self.labels.pop(label))
            return
        super().apply(op)


def run_case(case: Mapping, workdir: Path) -> dict:
    with mock.patch.object(base, "Scenario", Scenario):
        return _BASE_RUN_CASE(case, workdir)


def provenance(fixture_path: Path) -> dict:
    status = [line for line in base.git("status", "--porcelain", "--untracked-files=all").splitlines()
              if line[3:].strip('"') and not line[3:].strip('"').startswith(OUTPUT_REL)]
    prov = _BASE_PROVENANCE(fixture_path)
    prov["dirty_paths"] = sorted(line[3:] for line in status)
    prov["dirty_exclusion"] = OUTPUT_REL
    prov["runner"] = {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": sha256_file(Path(__file__).resolve()),
                      "version": RUNNER_VERSION}
    prov["runner_base"] = {"path": str(Path(base.__file__).resolve().relative_to(ROOT)),
                           "sha256": sha256_file(Path(base.__file__).resolve()), "version": base.RUNNER_VERSION}
    prov["store_profile"] = STORE_PROFILE_SCOPE_DISTINCT
    return prov


def run_replay(replay_id: str, *, fixture_dir: Path = FIXTURE_DIR, allow_dirty: bool = False) -> dict:
    if replay_id not in REPLAYS:
        raise ValueError(f"{replay_id} is not executed on a scope-distinct store by this runner")
    with mock.patch.object(base, "run_case", run_case), mock.patch.object(base, "provenance", provenance):
        report = base.run_replay(replay_id, fixture_dir=fixture_dir, allow_dirty=allow_dirty)
    report["store_profile"] = STORE_PROFILE_SCOPE_DISTINCT
    return report


def write_outputs(report: dict, output_dir: Path, command: str) -> dict:
    import json

    manifest = base.write_outputs(report, output_dir, command)
    manifest["runner_base"] = report["provenance"]["runner_base"]
    manifest["store_profile"] = STORE_PROFILE_SCOPE_DISTINCT
    (output_dir / report["replay_id"] / "manifest.json").write_bytes(
        json.dumps(manifest, indent=1, sort_keys=True).encode() + b"\n")
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--replay", choices=REPLAYS, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--fixture-dir", type=Path, default=FIXTURE_DIR)
    parser.add_argument("--allow-dirty", action="store_true", help="development only; the verdict is then BLOCKED")
    args = parser.parse_args(argv)
    report = run_replay(args.replay, fixture_dir=args.fixture_dir, allow_dirty=args.allow_dirty)
    manifest = write_outputs(report, args.output_dir, f"python reference/run_644_v7_replays_sd.py --replay {args.replay}")
    s = report["summary"]
    print(f"{args.replay}: {report['verdict']} ({s['passed']}/{s['cases']} cases) report sha256 {manifest['report']['sha256']}")
    for reason in report["verdict_reasons"]:
        print(f"  - {reason}")
    for c in report["cases"]:
        if c["outcome"] != "pass":
            print(f"  {c['id']}: {c['outcome']} {c['error'] or ''}")
    return {"PASS": 0, "FAIL": 1, "BLOCKED": 2}[report["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
